""" Module of BHT1000 climate entity. """
import logging

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_MAC, CONF_NAME
from homeassistant.helpers import device_registry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import HomeAssistantType

from .bht1000 import BHT1000
from .const import CONTROLLER, DOMAIN

_LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes
class Bht1000ChildLock(LockEntity):
    """
    Represents a BHT1000 thermostat child lock.
    """

    def __init__(self, controller: BHT1000, name: str, mac_address: str = None):
        """
        Initialize a new instance of `Bht1000Device` class.

        Args:
            controller: The `BHT1000` instance which is used to communicate with the thermostat.
            name: The name of the thermostat
            mac_address: The MAC address of the thermostat.
        """
        self._controller = controller
        self._mac_address = mac_address

        self._attr_name = f"{name} child lock"
        self._attr_unique_id = f"{self.name}_lock"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.unique_id)},
            connections={(device_registry.CONNECTION_NETWORK_MAC, self._mac_address)}
            if mac_address is not None
            else None,
        )

    async def async_lock(self, **kwargs) -> None:
        """Locks on the thermostat."""
        await self._controller.lock()

    async def async_unlock(self, **kwargs) -> None:
        """Unlocks on the thermostat."""
        await self._controller.unlock()

    async def async_update(self) -> None:
        """Updates the state of the climate."""
        if await self._controller.read_status():
            self._attr_is_locked = self._controller.locked

async def async_setup_entry(
    hass: HomeAssistantType,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """
    Setup of BHT1000 child lock entity for the specified config_entry.

    Args:
        hass: The Home Assistant instance.
        config_entry: The config entry which is used to create sensors.
        async_add_entities: The callback which can be used to add new entities to Home Assistant.

    Returns:
        The value indicates whether the setup succeeded.
    """
    _LOGGER.info("Setting up BHT1000 child lock.")
    controller = hass.data[DOMAIN][CONTROLLER][config_entry.data[CONF_HOST]]
    name = config_entry.data[CONF_NAME]
    mac_address = config_entry.data[CONF_MAC] if CONF_MAC in config_entry.data else None

    async_add_entities([Bht1000ChildLock(controller, name, mac_address)])

    _LOGGER.info("Setting up BHT1000 child lock completed.")
