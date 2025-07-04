"""
TCP Socket-based Message Queue System

This module provides a TCP socket-based message queue implementation
similar to the Tuya device sharing SDK but using TCP sockets instead.
"""

import logging
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
                    self.socket.connect((self.host, self.port))
                    self.socket.settimeout(None)

                    self.connected = True
                    self.running = True
                    if not self.is_alive():
                        self.start()

                    logger.info("Connected to %s:%s", self.host, self.port)

                # Out of the lock: perform any post‑connect work
                self.on_connect()
                return True

            except Exception as e:
                logger.error("Failed to connect to %s:%s: %s", self.host, self.port, e)

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
        """Send a message through the socket."""
        if not self.connected:
            logger.warning("Not connected to server")
            return False

        return self._send_message_internal(message)

    def _send_message_internal(self, message: Message) -> bool:
        """Internal method to send a message through the socket."""
        try:
            with self._lock:
                if not self.socket or not self.connected:
                    return False

                # Send the 48-byte message directly
                self.socket.sendall(message.data)
                # wait a little bit to avoid spamming the server.
                time.sleep(SEND_MESSAGE_INTERVAL)
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
                    logger.error(f"Error in message handler: {e}")
        else:
            logger.info(f"Received message: {message.data.hex()}")

    def on_connect(self):
        # sign in if we haven't already
        self.api.sign_in()

        # Send auth command
        token = self.api.token
        auth_command = generate_auth_command(token)
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

    def run(self) -> None:
        """Main thread method for receiving messages."""
        logger.info(f"Message queue thread started for {self.host}:{self.port}")
        while self.running and not self._stop_event.is_set():
            try:
                # Read exactly 48 bytes
                message_data = b''
                while len(message_data) < 48:
                    chunk = self.socket.recv(min(48 - len(message_data), self.buffer_size))
                    if not chunk:
                        logger.info("Server closed connection")
                        break
                    message_data += chunk

                if len(message_data) == 48:
                    message = Message(message_data)
                    self.on_receive(message)
                else:
                    self.on_disconnect()
                    continue

            except Exception as e:
                logger.error(f"Error in receive loop: {e}")
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
