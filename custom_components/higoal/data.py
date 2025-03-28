"""Custom types for higoal."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from . import Coordinator
from .higoal_client import HigoalApiClient

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

type HigoalConfigEntry = ConfigEntry[IntegrationData]


@dataclass
class IntegrationData:
    """Data for the Blueprint integration."""
    higoal_client: HigoalApiClient
    coordinator: Coordinator
    integration: Integration
