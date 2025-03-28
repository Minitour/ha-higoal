"""Constants for higoal."""
import logging
from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)
LOGGER.setLevel(logging.DEBUG)
DOMAIN = "higoal"