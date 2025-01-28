"""BHT-1000 thermostat integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .bht1000 import BHT1000
from .const import CONTROLLER, DOMAIN, PORT


# pylint: disable=unused-argument
async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """
    Set up the BHT1000 component.

    Args:
        hass: The Home Assistant instance.
        config: The configuration.

    Returns:
        The value indicates whether the setup succeeded.
    """
    hass.data[DOMAIN] = {CONTROLLER: {}}
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """
    Initialize the climates based on the config entry.

    Args:
        hass: The Home Assistant instance.
        config_entry: The config entry which contains information gathered by the config flow.

    Returns:
        The value indicates whether the setup succeeded.
    """
    if config_entry.data[CONF_HOST] not in hass.data[DOMAIN][CONTROLLER]:
        hass.data[DOMAIN][CONTROLLER][config_entry.data[CONF_HOST]] = BHT1000(
            config_entry.data[CONF_HOST], PORT
        )

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setups(
            config_entry,
            (
                "climate",
                "lock",
            ),
        )
    )

    return True
