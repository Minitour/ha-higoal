"""Tests for entity state methods: is_turned_on, is_online, percentage, set_response."""

import pytest
from client.device import Device, Entity, TYPE_SWITCH, TYPE_DIMMER, TYPE_SHUTTER
from conftest import make_device_dict, make_manager_stub, build_status_response


class TestIsTurnedOn:
    def test_on_when_status_byte_is_255(self, four_button_device):
        response = build_status_response({0: 255})
        four_button_device.set_current_status_response(response)

        assert four_button_device.entities[0].is_turned_on() is True

    def test_off_when_status_byte_is_240(self, four_button_device):
        response = build_status_response({0: 240})
        four_button_device.set_current_status_response(response)

        assert four_button_device.entities[0].is_turned_on() is False

    def test_off_when_status_byte_is_zero(self, four_button_device):
        response = build_status_response({0: 0})
        four_button_device.set_current_status_response(response)

        assert four_button_device.entities[0].is_turned_on() is False

    def test_default_state_without_response(self, manager):
        """Entity with no response data should report off (default zeros)."""
        data = make_device_dict(button_names="A", button_types="1")
        device = Device.init_from(data, manager)

        assert device.entities[0].is_turned_on() is False


class TestIsOnline:
    def test_online_when_nonzero(self, four_button_device):
        response = build_status_response({0: 255})
        four_button_device.set_current_status_response(response)

        assert four_button_device.entities[0].is_online() is True

    def test_offline_when_zero(self, four_button_device):
        response = build_status_response({0: 0})
        four_button_device.set_current_status_response(response)

        assert four_button_device.entities[0].is_online() is False

    def test_online_with_off_value(self, four_button_device):
        """240 (OFF) is still online — just not turned on."""
        response = build_status_response({0: 240})
        four_button_device.set_current_status_response(response)

        assert four_button_device.entities[0].is_online() is True


class TestPercentage:
    def test_switch_returns_none(self, manager):
        data = make_device_dict(button_names="Light", button_types="1")
        device = Device.init_from(data, manager)
        response = build_status_response({0: 255})
        device.set_current_status_response(response)

        assert device.entities[0].percentage() is None

    def test_shutter_percentage_fully_closed(self, manager):
        data = make_device_dict(button_names="Blinds;", button_types="3,3")
        device = Device.init_from(data, manager)
        response = build_status_response({0: 240}, {0: 100})
        device.set_current_status_response(response)

        assert device.entities[0].percentage() == 1.0

    def test_shutter_percentage_fully_open(self, manager):
        data = make_device_dict(button_names="Blinds;", button_types="3,3")
        device = Device.init_from(data, manager)
        response = build_status_response({0: 240}, {0: 0})
        device.set_current_status_response(response)

        assert device.entities[0].percentage() == 0.0

    def test_shutter_percentage_half(self, manager):
        data = make_device_dict(button_names="Blinds;", button_types="3,3")
        device = Device.init_from(data, manager)
        response = build_status_response({0: 240}, {0: 50})
        device.set_current_status_response(response)

        assert device.entities[0].percentage() == 0.5

    def test_dimmer_percentage(self, manager):
        data = make_device_dict(button_names="Light", button_types="2")
        device = Device.init_from(data, manager)
        response = build_status_response({0: 255}, {0: 75})
        device.set_current_status_response(response)

        assert device.entities[0].percentage() == 0.75

    def test_percentage_clamped_above_100(self, manager):
        """Values above 100 should be clamped to 100."""
        data = make_device_dict(button_names="Blinds;", button_types="3,3")
        device = Device.init_from(data, manager)
        response = build_status_response({0: 240}, {0: 150})
        device.set_current_status_response(response)

        assert device.entities[0].percentage() == 1.0


class TestSetResponse:
    def test_change_detected(self, manager):
        data = make_device_dict(button_names="A", button_types="1")
        device = Device.init_from(data, manager)
        entity = device.entities[0]

        response1 = build_status_response({0: 240})
        assert entity.set_response(response1) is True

        response2 = build_status_response({0: 255})
        assert entity.set_response(response2) is True

    def test_no_change_detected(self, manager):
        data = make_device_dict(button_names="A", button_types="1")
        device = Device.init_from(data, manager)
        entity = device.entities[0]

        response = build_status_response({0: 240})
        entity.set_response(response)
        assert entity.set_response(response) is False
