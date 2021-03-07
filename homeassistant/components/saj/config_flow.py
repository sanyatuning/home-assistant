"""Config flow for saj integration."""
import logging

import pysaj
import voluptuous as vol

from homeassistant import config_entries, data_entry_flow
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_TYPE,
    CONF_USERNAME,
)

from .const import (  # pylint:disable=unused-import
    DOMAIN,
    ENABLED_SENSORS,
    INVERTER_TYPES,
)
from .sensor import CannotConnect, SAJInverter

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SAJ."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                inverter = SAJInverter(user_input)
                await inverter.connect()
                await self.async_set_unique_id(inverter.serialnumber)
                self._abort_if_unique_id_configured()
                user_input[ENABLED_SENSORS] = inverter.get_enabled_sensors()

                return self.async_create_entry(title=inverter.name, data=user_input)
            except pysaj.UnauthorizedException:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except data_entry_flow.FlowError as error:
                raise error
            except Exception as error:  # pylint: disable=broad-except
                _LOGGER.error("Unexpected exception: %s", error)
                errors["base"] = "unknown"
        else:
            user_input = {}

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=user_input.get(CONF_HOST, "")): str,
                    vol.Required(CONF_TYPE, default=user_input.get(CONF_TYPE)): vol.In(
                        INVERTER_TYPES
                    ),
                    vol.Optional(CONF_NAME, default=user_input.get(CONF_NAME, "")): str,
                    vol.Optional(
                        CONF_USERNAME,
                        "credentials",
                        default=user_input.get(CONF_USERNAME, ""),
                    ): str,
                    vol.Optional(
                        CONF_PASSWORD,
                        "credentials",
                        default=user_input.get(CONF_PASSWORD, ""),
                    ): str,
                }
            ),
            errors=errors,
        )
