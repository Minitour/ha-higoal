"""Constants for higoal."""

from logging import Logger, getLogger

logger: Logger = getLogger(__package__)
DOMAIN = "higoal"
HIGOAL_HA_SIGNAL_UPDATE_ENTITY = "higoal_entry_update"
HIGOAL_DISCOVERY_NEW = 'higoal_discovery_new'