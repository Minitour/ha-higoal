"""Custom types for higoal."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .client.manager import Manager, EntityListener

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

type HigoalConfigEntry = ConfigEntry[IntegrationData]


@dataclass
class IntegrationData:
    """Data for the Blueprint integration."""

    manager: Manager
    listener: EntityListener
