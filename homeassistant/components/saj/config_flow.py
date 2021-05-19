"""Config flow for saj integration."""
import logging

import pysaj
import voluptuous as vol

from homeassistant import config_entries, data_entry_flow
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_TYPE,
    CONF_USERNAME,
)
from homeassistant.core import callback

from .const import (  # pylint:disable=unused-import
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    ENABLED_SENSORS,
    INVERTER_TYPES,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .sensor import CannotConnect, SAJInverter

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SAJ."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        """Define the config flow to handle options."""
        return OptionsFlowHandler(config_entry)

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
                user_input[CONF_DEVICE_ID] = inverter.serialnumber

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


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry: ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage options."""

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=(
                vol.Schema(
                    {
                        vol.Optional(
                            CONF_SCAN_INTERVAL,
                            default=self.config_entry.options.get(
                                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                            ),
                        ): vol.All(
                            vol.Coerce(int),
                            vol.Clamp(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                        ),
                    }
                )
            ),
        )
