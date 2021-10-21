import logging

from .const import (
    DOMAIN,
    CONTROLLER
)

from homeassistant.components.climate import (
    ClimateEntity
)

from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_MAC,
    TEMP_CELSIUS,
    ATTR_TEMPERATURE,
    STATE_UNAVAILABLE
)

from homeassistant.components.climate.const import (
    SUPPORT_TARGET_TEMPERATURE,
    HVAC_MODE_OFF,
    HVAC_MODE_HEAT,
    HVAC_MODE_AUTO,
    CURRENT_HVAC_OFF,
    CURRENT_HVAC_IDLE,
    CURRENT_HVAC_HEAT
)

from homeassistant.helpers import (
    entity_platform,
    device_registry
)

from datetime import datetime

from .const import (SERVICE_SYNC_TIME, LOCK, UNLOCK)

from .bht1000 import (BHT1000, STATE_OFF, STATE_ON, WEEKLY_MODE)

_LOGGER = logging.getLogger(__name__)


class Bht1000Device(ClimateEntity):
    def __init__(self, controller: BHT1000, name: str, mac_address: str = None):
        self._controller = controller
        self._name = name
        self._mac_address = mac_address
        self._attr_hvac_mode = None
        self._attr_min_temp = 0
        self._attr_max_temp = 35
        self._attr_precision = 0.5
        self._attr_temperature_unit = TEMP_CELSIUS
        self._attr_hvac_modes = [HVAC_MODE_OFF, HVAC_MODE_HEAT, HVAC_MODE_AUTO]
        self._attr_supported_features = SUPPORT_TARGET_TEMPERATURE
        self._attr_current_temperature = None
        self._attr_hvac_action = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def unique_id(self) -> str:
        return self._name

    @property
    def device_info(self):
        device_info = {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self._name,
            "manufacturer": "Beca Energy",
            "model": "BHT 1000"
        }

        if (self._mac_address):
            device_info["connections"] = {
                (device_registry.CONNECTION_NETWORK_MAC, self._mac_address)
            }

        return device_info

    def set_hvac_mode(self, mode: str):
        if mode == HVAC_MODE_HEAT:
            self._controller.turn_on()
            self._controller.set_manual_mode()
            return
        if mode == HVAC_MODE_OFF:
            self._controller.turn_off()
            return
        if mode == HVAC_MODE_AUTO:
            self._controller.turn_on()
            self._controller.set_weekly_mode()
        return

    def set_temperature(self, **kwargs):
        if kwargs.get(ATTR_TEMPERATURE) is not None:
            self._controller.set_temperature(kwargs.get(ATTR_TEMPERATURE))
        return

    def turn_on(self):
        self._controller.turn_on()
        return

    def turn_off(self):
        self._controller.turn_off()
        return

    def lock(self):
        self._controller.lock()
        return

    def unlock(self):
        self._controller.unlock()
        return

    def sync_time(self):
        self._controller.set_time(datetime.now(tz=None))
        return
    
    async def async_update(self):
        if (self._controller.read_status()):
            if (self._controller.power == STATE_OFF):
                self._attr_hvac_mode = HVAC_MODE_OFF

            if (self._controller.mode == WEEKLY_MODE):
                self._attr_hvac_mode = HVAC_MODE_AUTO

            self._attr_hvac_mode = HVAC_MODE_HEAT
            self._attr_current_temperature = self._controller.current_temperature
            self._attr_target_temperature = self._controller.setpoint   
            
            if (self._controller.power == STATE_OFF):
                self._attr_hvac_action = CURRENT_HVAC_OFF
            elif ((self._controller.setpoint is None) or (self._controller.current_temperature is None)):
                self._attr_hvac_action = None
            elif (self._controller.idle is True):
                self._attr_hvac_action = CURRENT_HVAC_IDLE
            else:
                self._attr_hvac_action = CURRENT_HVAC_HEAT         
        else:
            self._attr_hvac_mode = STATE_UNAVAILABLE
        return
    
async def async_setup_entry(hass, entry, async_add_entities):
    _LOGGER.info("Setting up BHT1000 platform.")
    controller = hass.data[DOMAIN][CONTROLLER][entry.data[CONF_HOST]]
    name = entry.data[CONF_NAME]
    mac_address = entry.data[CONF_MAC] if CONF_MAC in entry.data else None

    platform = entity_platform.current_platform.get()

    platform.async_register_entity_service(
        SERVICE_SYNC_TIME,
        {},
        SERVICE_SYNC_TIME
    )

    platform.async_register_entity_service(
        LOCK,
        {},
        LOCK
    )

    platform.async_register_entity_service(
        UNLOCK,
        {},
        UNLOCK
    )

    async_add_entities([Bht1000Device(controller, name, mac_address)])

    _LOGGER.info("Setting up BHT1000 platform completed.")
