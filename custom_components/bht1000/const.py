"""Define BHT-1000 thermostat constants."""

from typing import Final


CONTROLLER: Final[str] = "controller"
"""The key of the BHT1000 controller to store it in `hass.data`."""

DOMAIN: Final[str] = "bht1000"
"""The integration's domain."""

PORT: Final[int] = 8899
"""The port of the thermostat uses."""

SERVICE_SYNC_TIME: Final[str] = "sync_time"
"""The name of the time synchronization service."""
