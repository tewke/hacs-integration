"""Constants for the Tewke integration."""

from datetime import timedelta
from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "tewke"
SENSOR_SCAN_INTERVAL = timedelta(seconds=10)
