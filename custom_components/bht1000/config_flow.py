""" The configuration flow for BHT1000 integration. """
import logging
from typing import Any, Dict

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_MAC, CONF_NAME
from homeassistant.data_entry_flow import FlowResult

from .bht1000 import BHT1000
from .const import DOMAIN, PORT

_LOGGER = logging.getLogger(__name__)


@config_entries.HANDLERS.register(DOMAIN)
class BHT1000ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """
    Configuration flow handler for BHT1000 integration.
    """
    VERSION = 1

    async def async_step_user(self, user_info: Dict[str, Any]) -> FlowResult:
        """
        Handles the step when integration added from the UI.

        Args:
            user_info: The data entered by the user from the UI.

        Returns:
            The configuration flow result.        
        """
        errors = {}
        if user_info is not None:
            await self.async_set_unique_id(user_info[CONF_NAME])
            self._abort_if_unique_id_configured()

            valid = False
            try:
                bht1000 = BHT1000(user_info[CONF_HOST], PORT)
                valid = bht1000.check_host()
                if not valid:
                    errors["host"] = "invalid_host"
            except Exception as e:
                _LOGGER.error(str(e))
                valid = False
                errors["host"] = "invalid_host"

            if valid:
                data = {
                    CONF_NAME: user_info[CONF_NAME],
                    CONF_HOST: user_info[CONF_HOST],
                    CONF_MAC: user_info[CONF_MAC] if CONF_MAC in user_info else None,
                }
                return self.async_create_entry(
                    title=f"BHT-1000 WiFi Thermostat ({user_info[CONF_NAME]})", data=data
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_NAME): str,
                    vol.Optional(CONF_MAC): str,
                }
            ),
            errors=errors,
        )
