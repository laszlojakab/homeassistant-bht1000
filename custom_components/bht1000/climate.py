""" Module of BHT1000 climate entity. """

import logging
from datetime import datetime

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry

from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_HOST,
    CONF_MAC,
    CONF_NAME,
    STATE_UNAVAILABLE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant

from homeassistant.helpers import device_registry, entity_platform
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .bht1000 import BHT1000, WEEKLY_MODE
from .const import CONTROLLER, DOMAIN, SERVICE_SYNC_TIME

_LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes
class Bht1000Device(ClimateEntity):
    """
    Represents a BHT1000 thermostat climate entity.
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

        self._attr_name = name
        self._attr_hvac_mode = None
        self._attr_min_temp = 0
        self._attr_max_temp = 35
        self._attr_precision = 0.5
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.AUTO]
        self._attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
        self._attr_current_temperature = None
        self._attr_hvac_action = None
        self._attr_unique_id = self.name

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.unique_id)},
            manufacturer="Beca Energy",
            model="BHT 1000",
            name=self.name,
            connections=(
                {(device_registry.CONNECTION_NETWORK_MAC, self._mac_address)}
                if mac_address is not None
                else None
            ),
        )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """
        Sets the current HVAC mode.

        Args:
            hvac_mode: The HVAC mode to set.
        """
        if hvac_mode == HVACMode.HEAT:
            await self._controller.turn_on()
            await self._controller.set_manual_mode()
            return
        if hvac_mode == HVACMode.OFF:
            await self._controller.turn_off()
            return
        if hvac_mode == HVACMode.AUTO:
            await self._controller.turn_on()
            await self._controller.set_weekly_mode()

    async def async_set_temperature(self, **kwargs) -> None:
        """Sets the target temperature."""
        if kwargs.get(ATTR_TEMPERATURE) is not None:
            await self._controller.set_temperature(kwargs.get(ATTR_TEMPERATURE))

    async def turn_on(self) -> None:
        """Turns on the thermostat."""
        await self._controller.turn_on()

    async def turn_off(self) -> None:
        """Turns off the thermostat."""
        await self._controller.turn_off()

    async def sync_time(self) -> None:
        """Synchronizes the time on the thermostat."""
        await self._controller.set_time(datetime.now(tz=None))

    async def async_update(self) -> None:
        """Updates the state of the climate."""
        if await self._controller.read_status():
            if self._controller.power is False:
                self._attr_hvac_mode = HVACMode.OFF
            elif self._controller.mode == WEEKLY_MODE:
                self._attr_hvac_mode = HVACMode.AUTO
            else:
                self._attr_hvac_mode = HVACMode.HEAT

            self._attr_current_temperature = self._controller.current_temperature
            self._attr_target_temperature = self._controller.setpoint

            if self._controller.power is False:
                self._attr_hvac_action = HVACAction.OFF
            elif (self._controller.setpoint is None) or (
                self._controller.current_temperature is None
            ):
                self._attr_hvac_action = None
            elif self._controller.idle is True:
                self._attr_hvac_action = HVACAction.IDLE
            else:
                self._attr_hvac_action = HVACAction.HEATING
        else:
            self._attr_hvac_mode = STATE_UNAVAILABLE
        return


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """
    Setup of BHT1000 climate entity for the specified config_entry.

    Args:
        hass: The Home Assistant instance.
        config_entry: The config entry which is used to create sensors.
        async_add_entities: The callback which can be used to add new entities to Home Assistant.

    Returns:
        The value indicates whether the setup succeeded.
    """
    _LOGGER.info("Setting up BHT1000 climate entity.")
    controller = hass.data[DOMAIN][CONTROLLER][config_entry.data[CONF_HOST]]
    name = config_entry.data[CONF_NAME]
    mac_address = config_entry.data[CONF_MAC] if CONF_MAC in config_entry.data else None

    platform = entity_platform.current_platform.get()

    platform.async_register_entity_service(SERVICE_SYNC_TIME, {}, SERVICE_SYNC_TIME)

    async_add_entities([Bht1000Device(controller, name, mac_address)])

    _LOGGER.info("Setting up BHT1000 climate entity completed.")
