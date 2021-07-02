"""SAJ solar inverter interface."""
from __future__ import annotations

from datetime import date
import logging
from typing import Callable

import pysaj
import voluptuous as vol

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    STATE_CLASS_MEASUREMENT,
    SensorEntity,
)
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_TYPE,
    CONF_USERNAME,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_TEMPERATURE,
    ENERGY_KILO_WATT_HOUR,
    MASS_KILOGRAMS,
    POWER_WATT,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
    TIME_HOURS,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DEFAULT_NAME, DOMAIN, INVERTER_TYPES
from .coordinator import SAJInverter

_LOGGER = logging.getLogger(__name__)

SAJ_UNIT_MAPPINGS = {
    "": None,
    "h": TIME_HOURS,
    "kg": MASS_KILOGRAMS,
    "kWh": ENERGY_KILO_WATT_HOUR,
    "W": POWER_WATT,
    "°C": TEMP_CELSIUS,
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(CONF_TYPE, default=INVERTER_TYPES[0]): vol.In(INVERTER_TYPES),
        vol.Inclusive(CONF_USERNAME, "credentials"): cv.string,
        vol.Inclusive(CONF_PASSWORD, "credentials"): cv.string,
    }
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: Callable
):  # pragma: no cover
    """Set up the SAJ sensors."""
    inverter: SAJInverter = hass.data[DOMAIN][entry.entry_id]
    await inverter.setup(hass, async_add_entities)


async def async_setup_platform(
    hass: HomeAssistant, config, async_add_entities: Callable, discovery_info=None
):  # pragma: no cover
    """Set up the SAJ inverter with yaml."""
    _LOGGER.warning(
        "Loading SAJ Solar inverter integration via yaml is deprecated. "
        "Please remove it from your configuration"
    )
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data=config,
        )
    )


class SAJSensor(CoordinatorEntity, SensorEntity):
    """Representation of a SAJ sensor."""

    def __init__(self, coordinator: SAJInverter, pysaj_sensor: pysaj.Sensor) -> None:
        """Initialize the SAJ sensor."""
        super().__init__(coordinator)
        self._serialnumber = coordinator.serialnumber
        self._sensor = pysaj_sensor

        if pysaj_sensor.name in ("current_power", "total_yield", "temperature"):
            self._attr_state_class = STATE_CLASS_MEASUREMENT
        if pysaj_sensor.name == "total_yield":
            self._attr_last_reset = dt_util.utc_from_timestamp(0)

    @property
    def name(self):
        """Return the name of the sensor."""
        if self.coordinator.name != DEFAULT_NAME:
            return f"{self.coordinator.name} {self._sensor.name}"

        return f"SAJ Inverter {self._sensor.name}"

    @property
    def state(self):
        """Return the state of the sensor."""
        if not self.coordinator.last_update_success:
            # SAJ inverters are powered by DC via solar panels and thus are
            # offline after the sun has set. If a sensor resets on a daily
            # basis like "today_yield", this reset won't happen automatically.
            # Code below checks if today > day when sensor was last updated
            # and if so: set state to None.
            # Sensors with live values like "temperature" or "current_power"
            # will also be reset to None.
            if (
                date.today() > self._sensor.date
                if self._sensor.per_day_basis
                else not self._sensor.per_total_basis
            ):
                return None

        return self._sensor.value

    @property
    def available(self) -> bool:
        """Return True if device is available."""
        if self._sensor.name != "state":
            return True
        return super().available

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return SAJ_UNIT_MAPPINGS[self._sensor.unit]

    @property
    def device_class(self):
        """Return the device class the sensor belongs to."""
        if self.unit_of_measurement == POWER_WATT:
            return DEVICE_CLASS_POWER
        if (
            self.unit_of_measurement == TEMP_CELSIUS
            or self._sensor.unit == TEMP_FAHRENHEIT
        ):
            return DEVICE_CLASS_TEMPERATURE

    @property
    def unique_id(self):
        """Return a unique identifier for this sensor."""
        return f"{self._serialnumber}_{self._sensor.name}"

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self._serialnumber)
            },
            "name": self.coordinator.name,
            "manufacturer": "SAJ",
        }
