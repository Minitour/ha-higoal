"""Tests for get_related_entity — the cover close-button pairing logic.

Hardware pairs buttons in fixed pairs: (0,1), (2,3), (4,5), (6,7).
Within a pair the even-indexed button is "open" and the odd-indexed is "close".
"""

from client.device import Device, TYPE_SWITCH, TYPE_DIMMER, TYPE_SHUTTER
from conftest import make_device_dict, make_manager_stub


class TestGetRelatedEntity:
    """Verify that shutter open buttons correctly find their close button pair."""

    def test_valid_shutter_pair(self, four_button_device):
        """Open button (even id) paired with close button (odd id) in same hw pair."""
        open_button = four_button_device.entities[2]   # id=2, "Blinds Up", TYPE_SHUTTER
        close_button = four_button_device.entities[3]   # id=3, "", TYPE_SHUTTER

        assert open_button.name == "Blinds Up"
        assert open_button.type == TYPE_SHUTTER

        related = open_button.get_related_entity()
        assert related is close_button

    def test_close_button_returns_none(self, four_button_device):
        """The close button (odd id) should not pair with anything."""
        close_button = four_button_device.entities[3]  # id=3, "", TYPE_SHUTTER
        assert close_button.get_related_entity() is None

    def test_non_shutter_returns_none(self, four_button_device):
        """A regular switch should never return a related entity."""
        switch = four_button_device.entities[0]  # "Living Room", TYPE_SWITCH
        assert switch.get_related_entity() is None

    def test_shutter_is_last_entity(self, shutter_no_close):
        """Open button is the only/last entity — no close button exists."""
        open_button = shutter_no_close.entities[0]
        assert open_button.name == "Blinds Up"
        assert open_button.get_related_entity() is None

    def test_next_entity_is_not_shutter(self, shutter_next_is_switch):
        """Open button at even id, but partner at odd id is a switch — not a valid pair."""
        open_button = shutter_next_is_switch.entities[0]
        assert open_button.name == "Blinds Up"
        assert open_button.get_related_entity() is None

    def test_incomplete_hardware_pair(self, manager):
        """Partner slot is type-0 (skipped) so the hardware pair is incomplete."""
        data = make_device_dict(
            button_names="Open;;Close",
            button_types="3,0,3",
        )
        device = Device.init_from(data, manager)

        assert len(device.entities) == 2
        open_button = device.entities[0]  # id=0, "Open"

        # Partner id is 0^1 = 1, but id=1 was type-0 (skipped). No valid pair.
        assert open_button.get_related_entity() is None

    def test_multiple_shutter_pairs(self, manager):
        """Two independent shutter pairs on the same device."""
        data = make_device_dict(
            button_names="Pair1 Open;;Pair2 Open;",
            button_types="3,3,3,3",
        )
        device = Device.init_from(data, manager)

        assert len(device.entities) == 4

        pair1_open = device.entities[0]
        pair1_close = device.entities[1]
        pair2_open = device.entities[2]
        pair2_close = device.entities[3]

        assert pair1_open.get_related_entity() is pair1_close
        assert pair1_close.get_related_entity() is None
        assert pair2_open.get_related_entity() is pair2_close
        assert pair2_close.get_related_entity() is None

    def test_dimmer_returns_none(self, manager):
        """A dimmer entity should not return a related entity."""
        data = make_device_dict(
            button_names="Bedroom Light",
            button_types="2",
        )
        device = Device.init_from(data, manager)
        assert device.entities[0].get_related_entity() is None

    def test_cross_pair_shutter_does_not_match(self, manager):
        """Shutter buttons in different hw pairs must not be paired together."""
        data = make_device_dict(
            button_names="A;B;C;D",
            button_types="1,3,3,1",
        )
        device = Device.init_from(data, manager)

        shutter_at_1 = device.entities[1]  # id=1, odd → close button
        shutter_at_2 = device.entities[2]  # id=2, even → open button

        # id=1 is close → returns None regardless
        assert shutter_at_1.get_related_entity() is None
        # id=2 is open → partner id=3 is type 1 (switch) → None
        assert shutter_at_2.get_related_entity() is None

    def test_named_close_button_still_returns_none(self, manager):
        """A close button with a name should still return None (only open buttons pair)."""
        data = make_device_dict(
            button_names="Blinds Up;Blinds Down",
            button_types="3,3",
        )
        device = Device.init_from(data, manager)

        close_button = device.entities[1]  # id=1, "Blinds Down", odd → close
        assert close_button.name == "Blinds Down"
        assert close_button.get_related_entity() is None


class TestIsOpenCloseButton:
    """Verify the is_open_button / is_close_button helper properties."""

    def test_even_index_shutter_is_open(self, manager):
        data = make_device_dict(button_names="Up;Down", button_types="3,3")
        device = Device.init_from(data, manager)
        assert device.entities[0].is_open_button is True
        assert device.entities[0].is_close_button is False

    def test_odd_index_shutter_is_close(self, manager):
        data = make_device_dict(button_names="Up;Down", button_types="3,3")
        device = Device.init_from(data, manager)
        assert device.entities[1].is_open_button is False
        assert device.entities[1].is_close_button is True

    def test_non_shutter_is_neither(self, manager):
        data = make_device_dict(button_names="Light", button_types="1")
        device = Device.init_from(data, manager)
        assert device.entities[0].is_open_button is False
        assert device.entities[0].is_close_button is False

    def test_dimmer_at_even_index_is_not_open(self, manager):
        data = make_device_dict(button_names="Light", button_types="2")
        device = Device.init_from(data, manager)
        assert device.entities[0].is_open_button is False


class TestGetOnAction:
    """Verify _get_on_action uses index parity for shutters."""

    def test_open_button_sends_on_value(self, manager):
        data = make_device_dict(button_names="Up;Down", button_types="3,3")
        device = Device.init_from(data, manager)
        assert device.entities[0]._get_on_action() == 255  # _ON_VALUE

    def test_close_button_sends_off_value(self, manager):
        data = make_device_dict(button_names="Up;Down", button_types="3,3")
        device = Device.init_from(data, manager)
        assert device.entities[1]._get_on_action() == 240  # _OFF_VALUE

    def test_switch_always_sends_on_value(self, manager):
        data = make_device_dict(button_names="Light", button_types="1")
        device = Device.init_from(data, manager)
        assert device.entities[0]._get_on_action() == 255

    def test_named_close_button_still_sends_off(self, manager):
        """Even if the close button has a name, index parity determines the action."""
        data = make_device_dict(button_names="Up;Down", button_types="3,3")
        device = Device.init_from(data, manager)
        assert device.entities[1].name == "Down"
        assert device.entities[1]._get_on_action() == 240
