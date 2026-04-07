import pytest
from unittest.mock import MagicMock

from client.device import Device, Entity, TYPE_SWITCH, TYPE_DIMMER, TYPE_SHUTTER


def make_manager_stub():
    """Create a minimal manager stub that records sent commands."""
    manager = MagicMock()
    manager.sent_commands = []
    manager.send_command = lambda data: manager.sent_commands.append(data)
    return manager


def make_device_dict(
    *,
    device_id="ABCD1234",
    device_type=5,
    name="Test Panel",
    button_names="Light;Open;",
    button_types="1,3,3",
    room_id="room1",
    home_id="home1",
    ssid="wifi",
    mac="AA:BB:CC:DD:EE:FF",
    version="1.0.0",
):
    """Build a dict matching the shape returned by the HIGOAL API."""
    return {
        "id": device_id,
        "type": device_type,
        "name": name,
        "buttonName": button_names,
        "buttonType": button_types,
        "roomId": room_id,
        "homeId": home_id,
        "ssid": ssid,
        "mac": mac,
        "version": version,
    }


@pytest.fixture
def manager():
    return make_manager_stub()


@pytest.fixture
def four_button_device(manager):
    """4B panel: buttons 0+1 = switches, buttons 2+3 = shutter pair (open, close)."""
    data = make_device_dict(
        button_names="Living Room;Hall;Blinds Up;",
        button_types="1,1,3,3",
    )
    return Device.init_from(data, manager)


@pytest.fixture
def shutter_no_close(manager):
    """Shutter open-button is the last entity — no close button available."""
    data = make_device_dict(
        button_names="Blinds Up",
        button_types="3",
    )
    return Device.init_from(data, manager)


@pytest.fixture
def shutter_next_is_switch(manager):
    """Shutter open-button followed by a regular switch — not a valid pair."""
    data = make_device_dict(
        button_names="Blinds Up;Hall Light",
        button_types="3,1",
    )
    return Device.init_from(data, manager)


def build_status_response(entity_statuses: dict[int, int], entity_percentages: dict[int, int] | None = None) -> bytes:
    """Build a 48-byte status response with given entity values.

    entity_statuses: {entity_id: status_byte}  (e.g. 255=ON, 240=OFF, 0=OFFLINE)
    entity_percentages: {entity_id: percentage_byte}  (0-100)

    The percentage() method reads from offset 18+id+19 only when the
    selector byte at 18+id+8 is non-zero; otherwise it reads 18+id+16.
    This helper sets the selector byte so the +19 path is used.
    """
    data = bytearray(48)
    for eid, val in entity_statuses.items():
        data[18 + eid] = val
    if entity_percentages:
        for eid, val in entity_percentages.items():
            data[18 + eid + 8] = 1    # selector byte → use +19 offset
            data[18 + eid + 19] = val
    return bytes(data)
