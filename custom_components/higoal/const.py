"""Constants for higoal."""
import logging
from logging import Logger, getLogger

logger: Logger = getLogger(__package__)
logger.setLevel(logging.DEBUG)
DOMAIN = "higoal"