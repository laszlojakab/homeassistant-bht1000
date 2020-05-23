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
    TEMP_CELSIUS,
    ATTR_TEMPERATURE,
    STATE_UNKNOWN
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
    config_validation as cv, 
    entity_platform, 
    service
)

from datetime import datetime
import voluptuous as vol

from .const import ( SERVICE_SYNC_TIME )

from .bht1000 import ( STATE_OFF, STATE_ON, WEEKLY_MODE )

_LOGGER = logging.getLogger(__name__)

class Bht1000Device(ClimateEntity):
    def __init__(self, controller, name):
        self._controller = controller
        self._name = name

    @property
    def name(self):
        return self._name
 
    @property
    def unique_id(self):
        return self._name

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self._name,
            "manufacturer": "Beca Energy",
            "model": "BHT 1000"
        }

    @property
    def hvac_mode(self):
        if (self._controller.power == STATE_OFF):
            return HVAC_MODE_OFF

        if (self._controller.mode == WEEKLY_MODE):
            return HVAC_MODE_AUTO

        return HVAC_MODE_HEAT

    @property
    def hvac_action(self):
        # The current operation (e.g. heat, cool, idle). Used to determine state.
        if (self._controller.power == STATE_OFF):
            return CURRENT_HVAC_OFF

        if ((self._controller.setpoint is None) or (self._controller.current_temperature is None)):
            return None

        if (self._controller.idle is True):
            return CURRENT_HVAC_IDLE
        
        return CURRENT_HVAC_HEAT            

    @property
    def hvac_modes(self):
        return [HVAC_MODE_OFF, HVAC_MODE_HEAT, HVAC_MODE_AUTO]

    @property
    def supported_features(self):
        return SUPPORT_TARGET_TEMPERATURE

    @property
    def current_temperature(self):
        return self._controller.current_temperature

    @property
    def temperature_unit(self):
        return TEMP_CELSIUS

    @property
    def target_temperature(self):
        return self._controller.setpoint  

    @property
    def precision(self):
        return 0.5

    @property
    def max_temp(self):
        return 35        
    
    @property
    def min_temp(self):
        return 0        

    def set_hvac_mode(self, mode):
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

    async def async_update(self):
        self._controller.read_status()

async def async_setup_entry(hass, entry, async_add_entities):
    _LOGGER.info("Setting up BHT1000 platform.")
    controller = hass.data[DOMAIN][CONTROLLER][entry.data[CONF_HOST]]
    name = entry.data[CONF_NAME]

    platform = entity_platform.current_platform.get()

    platform.async_register_entity_service(
        SERVICE_SYNC_TIME, 
        {},
        SERVICE_SYNC_TIME
    )

    async_add_entities([Bht1000Device(controller, name)])

    _LOGGER.info("Setting up BHT1000 platform completed.")

  