"""BHT-1000 thermostat integration."""
from .const import (DOMAIN, CONTROLLER, PORT)
from homeassistant.const import CONF_HOST
from .bht1000 import BHT1000

async def async_setup(hass, config):
    hass.data[DOMAIN] = { CONTROLLER: {} }
    return True

async def async_setup_entry(hass, config_entry):
    if not (config_entry.data[CONF_HOST] in hass.data[DOMAIN][CONTROLLER]):
        hass.data[DOMAIN][CONTROLLER][config_entry.data[CONF_HOST]] = BHT1000(config_entry.data[CONF_HOST], PORT)

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(config_entry, "climate")
    )
    return True
