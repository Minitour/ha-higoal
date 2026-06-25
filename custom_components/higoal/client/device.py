from dataclasses import dataclass, field
from typing import Optional

from .utils import generate_command, models

_OFF_VALUE = 240
_ON_VALUE = 255
_SET_PERCENTAGE = 241
_OFFLINE_VALUE = 0

TYPE_SWITCH = 1
TYPE_DIMMER = 2
TYPE_SHUTTER = 3


@dataclass
class Entity:
    """Entity corresponds to a button/switch."""

    id: int  # The index of the button
    name: str  # The name of the button
    type: int  # The type of button
    device: "Device" = field(repr=False)  # Reference to the containing device
    _response: bytes = field(repr=False, default=None)  # The current state

    @property
    def response(self):
        return self._response

    @property
    def display_name(self) -> str:
        """Return a stable Home Assistant display name for this entity."""
        name = (self.name or "").strip()
        if name:
            return name

        device_name = (self.device.name or "").strip() or self.device.id
        return f"{device_name} channel {self.id + 1}"

    def set_response(self, response: bytes):
        first_response = self._response is None
        old_value = self._response or bytes([0] * 48)
        old_status = old_value[18 + self.id]
        old_percentage = old_value[18 + self.id + 16]

        new_status = response[18 + self.id]
        new_percentage = response[18 + self.id + 16]
        self._response = response
        if first_response:
            return True
        if old_status != new_status or old_percentage != new_percentage:
            # something has changed in the entity
            return True
        return False

    @property
    def is_open_button(self) -> bool:
        """Shutter open buttons sit at even 0-based indices (1-based odd: 1,3,5,7)."""
        return self.type == TYPE_SHUTTER and self.id % 2 == 0

    @property
    def is_close_button(self) -> bool:
        """Shutter close buttons sit at odd 0-based indices (1-based even: 2,4,6,8)."""
        return self.type == TYPE_SHUTTER and self.id % 2 == 1

    def _get_on_action(self) -> int:
        if self.type == TYPE_SHUTTER:
            return _ON_VALUE if self.is_open_button else _OFF_VALUE
        return _ON_VALUE

    def _get_off_action(self) -> int:
        if self.type == TYPE_SHUTTER:
            return 0
        return _OFF_VALUE

    def turn_on(self):
        """
        Turn on the switch
        """
        action = self._get_on_action()
        cmd = generate_command(
            device_id=self.device.id,
            device_type=self.device.type,
            read_only=False,
            entity=self.id,
            entity_type=self.type,
            action=action,
        )
        self.device.manager.send_command(cmd)

    def turn_off(self):
        """
        Turn off the switch
        """
        if self.type == TYPE_SHUTTER:
            # for type 3 the turn-off command is the same as the turn-on command.
            self.turn_on()
            return
        action = self._get_off_action()
        cmd = generate_command(
            device_id=self.device.id,
            device_type=self.device.type,
            read_only=False,
            entity=self.id,
            entity_type=self.type,
            action=action,
        )
        self.device.manager.send_command(cmd)

    def set_percentage(self, percentage: float):
        if self.type != TYPE_DIMMER:
            return
        value = max(0, min(100, int(percentage * 100)))
        action = 241
        cmd = generate_command(
            device_id=self.device.id,
            device_type=self.device.type,
            read_only=False,
            entity=self.id,
            entity_type=self.type,
            action=action,
        )
        cmd = list(cmd)
        cmd[18 + self.id + 16] = value
        self.device.manager.send_command(bytes(cmd))

    def can_set_percentage(self) -> bool:
        return self.type == TYPE_DIMMER

    def status_command(self):
        return self.device.status_command()

    def is_turned_on(self) -> bool:
        """
        Check if the switch is turned on or not.
        """
        response = self._current_response()
        return response[18 + self.id] == _ON_VALUE

    def is_online(self):
        """
        Check if the switch is online.
        """
        response = self._current_response()
        return response[18 + self.id] != _OFFLINE_VALUE

    def percentage(self) -> float | None:
        """
        Get percentage of blinds 1.0 means fully closed while 0.0 means fully open.
        """
        if self.type not in {TYPE_SHUTTER, TYPE_DIMMER}:
            return None
        status = self._current_response()
        value = max(min(status[18 + self.id + 16], 100), 0)
        return value / 100

    def _current_response(self, use_cache: bool = True) -> bytes:
        if self.response:
            return self.response

        self.device.manager.send_command(self.status_command())

        return bytes([0] * 48)

    def get_related_entity(self) -> Optional["Entity"]:
        """
        Return the paired shutter entity using hardware index pairing.

        Shutter buttons are paired in fixed hardware pairs: (0,1), (2,3), (4,5), (6,7).
        Only the open button (even 0-based id) should request its partner (the close
        button at id ^ 1).  Returns None for non-shutter or close buttons.
        """
        if not self.is_open_button:
            return None
        partner_id = self.id ^ 1
        for entity in self.device.entities:
            if entity.id == partner_id and entity.type == TYPE_SHUTTER:
                return entity
        return None


@dataclass
class Device:
    """
    A device (or sometimes host) refers to a physical switch.
    One device can have many entities (buttons).
    """

    id: str
    type: int
    name: str
    room_id: str
    home_id: str
    ssid: str
    mac: str
    version: str
    entities: list[Entity] = field(repr=False)
    manager: "Manager" = field(repr=False)
    _status: bytes = field(repr=False, default=None)

    @property
    def model_name(self):
        return models.get(self.type) or "UNKNOWN"

    @classmethod
    def init_from(cls, device: dict, manager) -> "Device":
        """
        Create an instance of device from dictionary object and api client.
        """
        button_names = device.get("buttonName").split(";")
        button_types = device.get("buttonType").split(",")
        entities = []
        device = Device(
            id=device.get("id"),
            type=device.get("type"),
            name=device.get("name"),
            room_id=device.get("roomId"),
            home_id=device.get("homeId"),
            ssid=device.get("ssid"),
            mac=device.get("mac"),
            version=device.get("version"),
            entities=entities,
            manager=manager,
        )
        for i, (button_name, button_type) in enumerate(
            zip(button_names, button_types, strict=False)
        ):
            button_type = int(button_type)
            if button_type == 0:
                continue
            entities.append(
                Entity(id=i, name=button_name, type=button_type, device=device)
            )

        return device

    @property
    def identifier(self):
        status_command = self.status_command()
        return (
            status_command[9],
            status_command[10],
            status_command[11],
            status_command[12],
        )

    def status_command(self) -> bytes:
        """
        Generates the status command.
        """
        return generate_command(
            device_id=self.id, device_type=self.type, read_only=True
        )

    def button(self, name: str) -> Entity | None:
        """
        Get button by name.
        """
        for entity in self.entities:
            if entity.name == name:
                return entity

    def set_current_status_response(self, response: bytes) -> list[Entity]:
        if list(self._status or []) == list(response):
            return []

        self._status = response
        entities = []
        for entity in self.entities:
            did_change = entity.set_response(response)
            if did_change:
                entities.append(entity)

        return entities

    @property
    def offline(self):
        return any([not entity.is_online() for entity in self.entities])


class DeviceRepository:
    def __init__(self, manager):
        self.manager = manager

    def get_devices(self) -> list[Device]:
        """
        Get devices (hosts) assigned to the account.
        """
        if not self.manager.api.is_signed_in:
            self.manager.api.sign_in()

        devices = []
        for home in self.manager.api.home_ids:
            payload = f"homeId={home}&token={self.manager.api.token}&uid={self.manager.api.user_id}"
            headers = {
                "content-type": "application/x-www-form-urlencoded; charset=utf-8"
            }
            response = self.manager.api.session.request(
                "POST",
                f"{self.manager.api.url}/get_host_list",
                data=payload,
                headers=headers,
            )
            body = response.json()
            devices.extend(body.get("repData", []))
        devices = [Device.init_from(device, self.manager) for device in devices]
        return devices
