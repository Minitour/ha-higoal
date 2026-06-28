"""Tests for the Home Assistant entity wrapper."""

# ruff: noqa: ANN001, ANN201, ARG005, D103, INP001, S101, SLF001

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

from client.device import Device
from conftest import build_status_response, make_device_dict


def load_entity_module(monkeypatch):
    """Load the entity module with minimal Home Assistant stubs."""
    package_name = "_higoal_test"
    component_path = (
        Path(__file__).resolve().parents[1] / "custom_components" / "higoal"
    )

    homeassistant = types.ModuleType("homeassistant")
    helpers = types.ModuleType("homeassistant.helpers")
    dispatcher = types.ModuleType("homeassistant.helpers.dispatcher")
    helper_entity = types.ModuleType("homeassistant.helpers.entity")
    higoal_package = types.ModuleType(package_name)

    class HomeAssistantEntity:
        pass

    dispatcher.async_dispatcher_connect = lambda *args, **kwargs: None
    helper_entity.Entity = HomeAssistantEntity
    higoal_package.__path__ = [str(component_path)]

    monkeypatch.setitem(sys.modules, "homeassistant", homeassistant)
    monkeypatch.setitem(sys.modules, "homeassistant.helpers", helpers)
    monkeypatch.setitem(sys.modules, "homeassistant.helpers.dispatcher", dispatcher)
    monkeypatch.setitem(sys.modules, "homeassistant.helpers.entity", helper_entity)
    monkeypatch.setitem(sys.modules, package_name, higoal_package)

    sys.modules.pop(f"{package_name}.entity", None)
    return importlib.import_module(f"{package_name}.entity")


def test_entity_uses_display_name(monkeypatch, manager):
    entity_module = load_entity_module(monkeypatch)
    data = make_device_dict(
        name="Study Lights",
        button_names="",
        button_types="1",
    )
    device = Device.init_from(data, manager)

    ha_entity = entity_module.BaseHigoalEntity(device.entities[0])

    assert ha_entity._attr_name == "Study Lights channel 1"


def test_entity_available_before_first_status_response(monkeypatch, manager):
    entity_module = load_entity_module(monkeypatch)
    data = make_device_dict(button_names="Light", button_types="1")
    device = Device.init_from(data, manager)

    ha_entity = entity_module.BaseHigoalEntity(device.entities[0])

    assert ha_entity.available is True
    assert manager.sent_commands == []


def test_entity_unavailable_after_offline_status_response(monkeypatch, manager):
    entity_module = load_entity_module(monkeypatch)
    data = make_device_dict(button_names="Light", button_types="1")
    device = Device.init_from(data, manager)
    device.set_current_status_response(build_status_response({0: 0}))

    ha_entity = entity_module.BaseHigoalEntity(device.entities[0])

    assert ha_entity.available is False
