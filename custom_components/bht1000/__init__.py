"""BHT-1000 thermostat integration."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.helpers.typing import ConfigType, HomeAssistantType

from .bht1000 import BHT1000
from .const import CONTROLLER, DOMAIN, PORT


async def async_setup(hass: HomeAssistantType, config: ConfigType) -> bool:
    hass.data[DOMAIN] = {CONTROLLER: {}}
    return True


async def async_setup_entry(hass: HomeAssistantType, config_entry: ConfigEntry) -> bool:
    if not (config_entry.data[CONF_HOST] in hass.data[DOMAIN][CONTROLLER]):
        hass.data[DOMAIN][CONTROLLER][config_entry.data[CONF_HOST]] = BHT1000(
            config_entry.data[CONF_HOST], PORT
        )

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(config_entry, "climate")
    )
    return True
