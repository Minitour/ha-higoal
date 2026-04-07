"""Tests for get_related_entity — the cover close-button pairing logic."""

from client.device import Device, TYPE_SWITCH, TYPE_DIMMER, TYPE_SHUTTER
from conftest import make_device_dict, make_manager_stub


class TestGetRelatedEntity:
    """Verify that shutter open buttons correctly find their close button pair."""

    def test_valid_shutter_pair(self, four_button_device):
        """Named shutter followed by unnamed shutter → valid pair."""
        open_button = four_button_device.entities[1]   # "Blinds Up", TYPE_SHUTTER
        close_button = four_button_device.entities[2]   # "", TYPE_SHUTTER

        assert open_button.name == "Blinds Up"
        assert open_button.type == TYPE_SHUTTER

        related = open_button.get_related_entity()
        assert related is close_button

    def test_close_button_returns_none(self, four_button_device):
        """The close button (unnamed shutter) should not pair with anything."""
        close_button = four_button_device.entities[2]  # "", TYPE_SHUTTER
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
        """Open button followed by a TYPE_SWITCH — not a valid pair."""
        open_button = shutter_next_is_switch.entities[0]
        assert open_button.name == "Blinds Up"
        assert open_button.get_related_entity() is None

    def test_shutter_pair_with_gap_due_to_type_zero(self, manager):
        """Type-0 buttons are skipped during init, so a gap can break the pair."""
        data = make_device_dict(
            button_names="Open;;Close",
            button_types="3,0,3",
        )
        device = Device.init_from(data, manager)

        assert len(device.entities) == 2
        open_button = device.entities[0]  # id=0, "Open"
        close_button = device.entities[1]  # id=2, ""  (name from "Close"... wait)

        # Type-0 is skipped, so entities are [id=0, id=2].
        # get_related_entity looks at index+1 in the entities list.
        related = open_button.get_related_entity()
        assert related is close_button

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
