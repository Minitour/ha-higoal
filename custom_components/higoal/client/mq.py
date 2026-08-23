"""
TCP Socket-based Message Queue System

This module provides a TCP socket-based message queue implementation
similar to the Tuya device sharing SDK but using TCP sockets instead.
"""

import logging
import queue
import socket
import threading
import time
from abc import ABC, abstractmethod
from typing import Optional

from .api import Api
from .utils import generate_auth_command

logger = logging.getLogger(__name__)

RETRY_INTERVAL = 5.0
SEND_MESSAGE_INTERVAL = 0.250  # 250 milliseconds

FRAME_SIZE = 48
# Frame-start markers the Higoal cloud relay uses: bb5b = status reply,
# cc5c = ping. (Outbound commands start with aa5a.) The relay does not frame
# its stream reliably — a single short write during the auth handshake leaves
# the byte stream offset by a few bytes — so run() resyncs to one of these
# markers before slicing each 48-byte frame.
FRAME_START_MARKERS = (b"\xbb\x5b", b"\xcc\x5c")


class Message:
    """Simple 48-byte message structure."""

    def __init__(self, data: bytes = None):
        if data is None:
            self.data = bytes(48)  # Initialize with 48 zero bytes
        else:
            if len(data) != 48:
                raise ValueError(f"Message must be exactly 48 bytes, got {len(data)}")
            self.data = data

    def __bytes__(self) -> bytes:
        """Return the message as bytes."""
        return self.data

    @classmethod
    def from_bytes(cls, data: bytes) -> 'Message':
        """Create a message from bytes."""
        return cls(data)

    def __repr__(self) -> str:
        """String representation of the message."""
        return f"Message({self.data.hex()})"

    @property
    def is_status(self):
        return self.data[0] == 187 and self.data[1] == 91

    @property
    def is_ping(self):
        return self.data[0] == 204 and self.data[1] == 92

    @property
    def device_identifier(self):
        if self.is_status:
            return self.data[9], self.data[10], self.data[11], self.data[12]
        elif self.is_ping:
            return self.data[3], self.data[4], self.data[5], self.data[6]
        else:
            return None


class MessageHandler(ABC):
    """Abstract base class for message handlers."""

    @abstractmethod
    def on_receive(self, message: Message) -> None:
        """Handle an incoming message."""
        pass


class MessageBroker(threading.Thread):
    """TCP Socket-based Message Queue implementation that runs in a separate thread."""

    def __init__(self, api: Api, host: str = "server.higoal.net", port: int = 17670,
                 buffer_size: int = 8192, name: str = "TCPMessageQueue"):
        super().__init__(name=name, daemon=True)

        self.host = host
        self.port = port
        self.buffer_size = buffer_size

        self.socket: Optional[socket.socket] = None
        self.connected = False
        self.running = False
        self.api = api
        self.message_handlers: dict[int, Optional[MessageHandler]] = {}

        # Thread control
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        # Outbound message queue, drained by a dedicated sender thread that
        # paces sends at SEND_MESSAGE_INTERVAL. The Higoal cloud relay
        # silently drops all but the first 1-2 commands when they arrive in
        # a sub-millisecond burst; pacing fixes that without blocking either
        # HA's asyncio loop or this broker's receive loop.
        self._send_queue: "queue.Queue[Optional[Message]]" = queue.Queue()
        self._sender_thread = threading.Thread(
            target=self._sender_loop,
            daemon=True,
            name=f"{name}Sender",
        )
        self._sender_thread.start()

    def add_message_handler(self, handler: MessageHandler) -> None:
        """Set the message handler for incoming messages."""
        with self._lock:
            self.message_handlers[id(handler)] = handler

    def connect(self, retry_interval: float = RETRY_INTERVAL) -> bool:
        """Connect to the TCP server, retrying until successful or stop() is called.

        Returns True once the connection is established, or False if the
        broker was stopped (_stop_event set) before it could connect.
        """
        while not self._stop_event.is_set():
            try:
                with self._lock:
                    if self.connected:
                        logger.warning("Already connected")
                        return True

                    # Create a fresh socket each attempt
                    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.socket.settimeout(10.0)
                    # TCP keepalive + user-timeout: detect zombie connections.
                    # The Higoal cloud occasionally stops responding without
                    # closing the socket; without these the OS waits ~15 min
                    # before declaring the peer dead, leaving the integration
                    # stuck with entities unresponsive.
                    self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                    if hasattr(socket, "TCP_KEEPIDLE"):
                        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
                    if hasattr(socket, "TCP_KEEPINTVL"):
                        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
                    if hasattr(socket, "TCP_KEEPCNT"):
                        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5)
                    if hasattr(socket, "TCP_USER_TIMEOUT"):
                        # Force-fail the socket if data sits unacked >60s.
                        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_USER_TIMEOUT, 60_000)
                    self.socket.connect((self.host, self.port))
                    self.socket.settimeout(None)

                    self.connected = True
                    self.running = True
                    if not self.is_alive():
                        self.start()

                    logger.info("Connected to %s:%s", self.host, self.port)

                # Out of the lock: perform any post‑connect work
                try:
                    self.on_connect()
                except Exception as e:
                    # on_connect() failed (likely sign_in() SSL error)
                    # The error is already logged in on_connect(), just mark as disconnected
                    with self._lock:
                        self.connected = False
                        if self.socket:
                            try:
                                self.socket.close()
                            except Exception:
                                pass
                            self.socket = None
                    # Continue to retry loop
                    if self._stop_event.wait(retry_interval):
                        break
                    logger.debug("Retrying connection to %s:%s …", self.host, self.port)
                    continue
                
                return True

            except Exception as e:
                logger.error("Failed to connect TCP socket to %s:%s: %s", self.host, self.port, e)

                # Clean up the failed socket and mark as disconnected
                with self._lock:
                    self.connected = False
                    if self.socket:
                        try:
                            self.socket.close()
                        except Exception:
                            pass
                        self.socket = None

            # Wait before the next attempt (returns early if stop_event is set)
            if self._stop_event.wait(retry_interval):
                break  # stop() was called – give up

            logger.debug("Retrying connection to %s:%s …", self.host, self.port)

        return False

    def disconnect(self) -> None:
        """Disconnect from the TCP server."""
        with self._lock:

            self.connected = False
            self.running = False

            if self.socket:
                try:
                    self.socket.close()
                except Exception as e:
                    logger.error(f"Error during disconnect: {e}")
                finally:
                    self.socket = None

        logger.info("Disconnected from server")

    def send_message(self, message: Message) -> bool:
        """Enqueue a message for the sender thread to dispatch.

        Returns True if queued, False if the broker is disconnected. The
        actual socket write happens in the sender thread, paced at
        SEND_MESSAGE_INTERVAL — see _sender_loop().
        """
        if not self.connected:
            logger.warning("Not connected to server")
            return False

        self._send_queue.put(message)
        return True

    def _sender_loop(self) -> None:
        """Drain the outbound queue at SEND_MESSAGE_INTERVAL pace.

        Runs in its own daemon thread so neither HA's event loop (entity
        service calls) nor the broker's receive loop (Manager.on_receive →
        check_offline_devices) blocks while we wait between sends.
        """
        while not self._stop_event.is_set():
            try:
                message = self._send_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if message is None:
                break
            if not self.connected:
                continue
            self._send_message_internal(message)
            if self._stop_event.wait(SEND_MESSAGE_INTERVAL):
                break

    def _send_message_internal(self, message: Message) -> bool:
        """Internal method to send a message through the socket."""
        try:
            with self._lock:
                if not self.socket or not self.connected:
                    return False

                # Send the 48-byte message directly
                logger.debug("Sending socket command: %s", message.data.hex())
                self.socket.sendall(message.data)
                return True

        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False

    def on_receive(self, message: Message) -> None:
        """Handle an incoming message. Override this method or set a message handler."""
        if self.message_handlers:
            for handler in self.message_handlers.values():
                try:
                    handler.on_receive(message)
                except Exception as e:
                    logger.exception(f"Error in message handler: {e}")
        else:
            logger.info(f"Received message: {message.data.hex()}")

    def on_connect(self):
        # sign in if we haven't already
        try:
            self.api.sign_in()
        except Exception as e:
            logger.error("Failed to sign in via HTTPS (port 8143): %s", e)
            # Disconnect TCP connection since authentication failed
            self.disconnect()
            raise

        # Send auth command
        token = self.api.token
        if token is None:
            logger.error("No token available after sign in")
            self.disconnect()
            return
        
        auth_command = generate_auth_command(token)
        logger.debug("Sending auth command: %s", bytes(auth_command).hex())
        self.send_message(Message(auth_command))

    def on_disconnect(self):
        # reconnect
        self.disconnect()
        self.connect()

    def start(self):
        """Start mqtt.

        Start mqtt thread
        """
        logger.debug("start")
        super().start()

    def stop(self):
        """Stop mqtt.

        Stop mqtt thread
        """
        logger.debug("stop")
        self.message_handlers = {}
        try:
            self.disconnect()
        except Exception as e:
            logger.error("mq disconnect error %s", e)
        self._stop_event.set()
        # Wake the sender thread so it exits promptly.
        self._send_queue.put(None)

    def run(self) -> None:
        """Main thread method for receiving messages.

        Buffer incoming bytes and resync to a known frame-start marker before
        slicing each 48-byte frame. A blind 48-byte read loop assumed the
        stream was frame-aligned from connect; in practice the relay's auth
        handshake skews alignment by a few bytes, after which every frame is
        the tail of one real frame plus the head of the next. Such frames fail
        the is_status / is_ping marker check (markers live at byte 0), so state
        updates were silently dropped — commands kept working (independent send
        path) while HA never saw new state. Resyncing fixes the skew and
        self-heals on any future desync.
        """
        logger.info(f"Message queue thread started for {self.host}:{self.port}")
        recv_buffer = bytearray()
        while self.running and not self._stop_event.is_set():
            try:
                chunk = self.socket.recv(self.buffer_size)
                if not chunk:
                    logger.info("Server closed connection")
                    recv_buffer.clear()
                    self.on_disconnect()
                    continue
                recv_buffer.extend(chunk)

                # Drain every complete, frame-aligned message now buffered.
                while True:
                    start = self._find_frame_start(recv_buffer)
                    if start < 0:
                        # No marker yet. Keep a trailing byte in case a 2-byte
                        # marker straddles this recv and the next.
                        if len(recv_buffer) > 1:
                            del recv_buffer[:-1]
                        break
                    if start > 0:
                        logger.warning(
                            "Higoal stream misaligned; discarding %d bytes to resync",
                            start,
                        )
                        del recv_buffer[:start]
                    if len(recv_buffer) < FRAME_SIZE:
                        break  # wait for the rest of this frame
                    frame = bytes(recv_buffer[:FRAME_SIZE])
                    del recv_buffer[:FRAME_SIZE]
                    logger.debug("Received socket command: %s", frame.hex())
                    self.on_receive(Message(frame))

            except Exception as e:
                logger.error(f"Error in receive loop: {e}")
                recv_buffer.clear()
                self.api.reset()
                self.on_disconnect()
                continue

        # Clean up connection
        with self._lock:
            self.connected = False
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
                self.socket = None

        logger.info("Message queue thread ended")

    @staticmethod
    def _find_frame_start(buffer: bytearray) -> int:
        """Index of the earliest known frame-start marker, or -1 if none."""
        earliest = -1
        for marker in FRAME_START_MARKERS:
            idx = buffer.find(marker)
            if idx >= 0 and (earliest < 0 or idx < earliest):
                earliest = idx
        return earliest
