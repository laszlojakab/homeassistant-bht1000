import voluptuous as vol 
from homeassistant import config_entries
from homeassistant.const import (CONF_HOST, CONF_NAME)
from .const import (DOMAIN, PORT)
from .bht1000 import BHT1000

@config_entries.HANDLERS.register(DOMAIN)
class BHT1000ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1 

    async def async_step_user(self, info):
        if info is not None:
            await self.async_set_unique_id(info[CONF_NAME])
            self._abort_if_unique_id_configured()

            try:
                bht1000 = BHT1000(info[CONF_HOST], PORT)
                if (not bht1000.check_host()):                
                    return await self._show_form(
                        errors = {CONF_HOST: "invalid_host"}
                    )
            except:
                return await self._show_form(
                    errors = {CONF_HOST: "invalid_host"}
                )

            data = { CONF_NAME: info[CONF_NAME], CONF_HOST: info[CONF_HOST] }
            return self.async_create_entry(title=f"BHT-1000 WiFi Thermostat ({info[CONF_NAME]})", data=data)
 
        return self.async_show_form(
            step_id="user", 
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_NAME): str
            })
        )
