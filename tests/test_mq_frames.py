"""Frame classification and handling of cloud control-plane frames.

The Higoal cloud sends bb5b-marked frames that are not status reports:
- f001: session/login ack (reply to the aa5a...f001 keepalive)
- f009: device announce/presence, emitted when a panel's cloud session
  (re)connects. Carries device id + device type and an all-zero payload.

Treating an announce as a status report reads every button as 0x00
(offline) and flips the whole panel Unavailable in HA.

Frames below were captured from a live session on 2026-07-10.
"""

from datetime import datetime

from unittest.mock import MagicMock

from client.device import Device
from client.manager import Manager
from client.mq import Message

from conftest import make_device_dict, make_manager_stub

# Device fe0a announcing itself (all-zero payload, device type 0x06 at byte 13).
ANNOUNCE_FRAME = bytes.fromhex(
    "bb5b96960101f00901fe0a0300060000000000000000000000000000000000"
    "0000000000000000000000000000000353"
)

# Real status report from device 4e0b (buttons 2,3 report 0x00 = offline).
STATUS_FRAME = bytes.fromhex(
    "bb5baaaa00030101014e0b03000305fff0f0f0f00000f0f0f0f004000a0000"
    "0000000000000000000000000000000921"
)

# Session/login ack (f001), reply to the aa5a...f001 keepalive.
SESSION_ACK_FRAME = bytes.fromhex(
    "bb5b0c0c0101f001011a070a050f00000000000000000000000000000000"
    "00000000000000000000000000000000ffff"
)


def test_announce_frame_is_not_status():
    assert Message(ANNOUNCE_FRAME).is_status is False


def test_announce_frame_is_announce():
    assert Message(ANNOUNCE_FRAME).is_announce is True


def test_status_frame_is_status_not_announce():
    message = Message(STATUS_FRAME)
    assert message.is_status is True
    assert message.is_announce is False


def test_session_ack_is_neither_status_nor_announce():
    message = Message(SESSION_ACK_FRAME)
    assert message.is_status is False
    assert message.is_announce is False


def test_announce_device_identifier():
    assert Message(ANNOUNCE_FRAME).device_identifier == (0xFE, 0x0A, 0x03, 0x00)


def _make_manager_with_device():
    manager = Manager(username="user", password="pass")
    manager.mq = MagicMock()
    manager.entity_listener = MagicMock()
    # Suppress the periodic poll-all cycle so sends observed in the test
    # come only from announce handling.
    manager._last_offline_check = datetime.now()

    device = Device.init_from(make_device_dict(), make_manager_stub())
    manager.device_map[device.identifier] = device
    return manager, device


def _announce_for(device: Device) -> bytes:
    frame = bytearray(ANNOUNCE_FRAME)
    frame[9:13] = bytes(device.identifier)
    frame[13] = device.type
    return bytes(frame)


def test_announce_does_not_clobber_entity_state():
    manager, device = _make_manager_with_device()
    status = bytearray(48)
    for entity in device.entities:
        status[18 + entity.id] = 0xFF  # all buttons on
    device.set_current_status_response(bytes(status))
    assert all(entity.is_online() for entity in device.entities)

    manager.on_receive(Message(_announce_for(device)))

    assert all(entity.is_online() for entity in device.entities)
    assert all(entity.is_turned_on() for entity in device.entities)


def test_announce_triggers_status_repoll():
    manager, device = _make_manager_with_device()

    manager.on_receive(Message(_announce_for(device)))

    sent = [call.args[0] for call in manager.mq.send_message.call_args_list]
    assert bytes(device.status_command()) in [bytes(m) for m in sent]
