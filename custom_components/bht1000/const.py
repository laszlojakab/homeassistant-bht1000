"""Define BHT-1000 thermostat constants."""

from typing import Final


CONTROLLER: Final[str] = "controller"
DOMAIN: Final[str] = "bht1000"
PORT: Final[int] = 8899

SERVICE_SYNC_TIME: Final[str] = "sync_time"
LOCK: Final[str] = "lock"
UNLOCK: Final[str] = "unlock"
