import voluptuous as vol 
from homeassistant import config_entries
from homeassistant.const import (CONF_HOST, CONF_NAME, CONF_MAC)
from .const import (DOMAIN, PORT)
from .bht1000 import BHT1000
import logging

_LOGGER = logging.getLogger(__name__)

@config_entries.HANDLERS.register(DOMAIN)
class BHT1000ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1 

    async def async_step_user(self, info):
        errors = {}        
        if info is not None:
            await self.async_set_unique_id(info[CONF_NAME])
            self._abort_if_unique_id_configured()

            valid = False
            try:
                bht1000 = BHT1000(info[CONF_HOST], PORT)
                valid = bht1000.check_host()
                if (not valid):
                    errors["host"] = "invalid_host"
            except Exception as e:
                _LOGGER.error(str(e))
                valid = False
                errors["host"] = "invalid_host"            

            if (valid):
                data = { CONF_NAME: info[CONF_NAME], CONF_HOST: info[CONF_HOST], CONF_MAC: info[CONF_MAC] if CONF_MAC in info else None }
                return self.async_create_entry(title=f"BHT-1000 WiFi Thermostat ({info[CONF_NAME]})", data=data)
 
        return self.async_show_form(
            step_id="user", 
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_NAME): str,
                vol.Optional(CONF_MAC): str
            }),
            errors = errors
        )
