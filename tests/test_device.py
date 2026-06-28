"""Tests for Device.init_from and entity construction."""

from client.device import TYPE_DIMMER, TYPE_SHUTTER, TYPE_SWITCH, Device
from conftest import make_device_dict


class TestDeviceInitFrom:
    def test_basic_construction(self, manager):
        data = make_device_dict(
            button_names="Light;Dimmer",
            button_types="1,2",
        )
        device = Device.init_from(data, manager)

        assert device.name == "Test Panel"
        assert device.type == 5
        assert device.version == "1.0.0"
        assert len(device.entities) == 2

    def test_entity_ids_match_button_index(self, manager):
        data = make_device_dict(
            button_names="A;B;C",
            button_types="1,1,1",
        )
        device = Device.init_from(data, manager)

        assert [e.id for e in device.entities] == [0, 1, 2]

    def test_entity_names_and_types(self, manager):
        data = make_device_dict(
            button_names="Kitchen;Bedroom;Blinds Up;",
            button_types="1,2,3,3",
        )
        device = Device.init_from(data, manager)

        assert device.entities[0].name == "Kitchen"
        assert device.entities[0].type == TYPE_SWITCH

        assert device.entities[1].name == "Bedroom"
        assert device.entities[1].type == TYPE_DIMMER

        assert device.entities[2].name == "Blinds Up"
        assert device.entities[2].type == TYPE_SHUTTER

        assert device.entities[3].name == ""
        assert device.entities[3].type == TYPE_SHUTTER

    def test_blank_entity_name_uses_device_channel_fallback(self, manager):
        data = make_device_dict(
            name="Study Lights",
            button_names=";;",
            button_types="0,1,1",
        )
        device = Device.init_from(data, manager)

        assert device.entities[0].display_name == "Study Lights channel 2"
        assert device.entities[1].display_name == "Study Lights channel 3"

    def test_blank_entity_name_uses_device_id_when_device_name_is_blank(self, manager):
        data = make_device_dict(
            device_id="ZCLCBZ",
            name=" ",
            button_names="",
            button_types="1",
        )
        device = Device.init_from(data, manager)

        assert device.entities[0].display_name == "ZCLCBZ channel 1"

    def test_type_zero_buttons_are_skipped(self, manager):
        data = make_device_dict(
            button_names="A;;B",
            button_types="1,0,1",
        )
        device = Device.init_from(data, manager)

        assert len(device.entities) == 2
        assert device.entities[0].id == 0
        assert device.entities[1].id == 2

    def test_entities_hold_reference_to_device(self, manager):
        data = make_device_dict(button_names="A", button_types="1")
        device = Device.init_from(data, manager)

        assert device.entities[0].device is device

    def test_button_lookup_by_name(self, manager):
        data = make_device_dict(
            button_names="Kitchen;Bedroom",
            button_types="1,2",
        )
        device = Device.init_from(data, manager)

        assert device.button("Kitchen") is device.entities[0]
        assert device.button("Bedroom") is device.entities[1]
        assert device.button("Nonexistent") is None


class TestDeviceStatusResponse:
    def test_set_current_status_response_returns_changed_entities(
        self, four_button_device, manager
    ):
        from conftest import build_status_response

        response = build_status_response({0: 255})
        changed = four_button_device.set_current_status_response(response)

        assert [entity.id for entity in changed] == [0, 1, 2, 3]

        response = build_status_response({0: 240, 1: 255})
        changed = four_button_device.set_current_status_response(response)

        assert [entity.id for entity in changed] == [0, 1]

    def test_identical_response_returns_empty(self, four_button_device, manager):
        from conftest import build_status_response

        response = build_status_response({0: 255})
        four_button_device.set_current_status_response(response)
        changed = four_button_device.set_current_status_response(response)

        assert changed == []

    def test_offline_detection(self, four_button_device, manager):
        from conftest import build_status_response

        response = build_status_response({0: 0, 1: 0, 2: 0, 3: 0})
        four_button_device.set_current_status_response(response)

        assert four_button_device.offline is True

    def test_online_detection(self, four_button_device, manager):
        from conftest import build_status_response

        response = build_status_response({0: 255, 1: 240, 2: 240, 3: 240})
        four_button_device.set_current_status_response(response)

        assert four_button_device.offline is False
