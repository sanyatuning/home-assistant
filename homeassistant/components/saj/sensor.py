"""SAJ solar inverter interface."""
from datetime import date, timedelta
import logging
from typing import Callable

import pysaj
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
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
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    ENABLED_SENSORS,
    INVERTER_TYPES,
)

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
        vol.Optional(CONF_SCAN_INTERVAL): cv.positive_int,
        vol.Optional(CONF_TYPE, default=INVERTER_TYPES[0]): vol.In(INVERTER_TYPES),
        vol.Inclusive(CONF_USERNAME, "credentials"): cv.string,
        vol.Inclusive(CONF_PASSWORD, "credentials"): cv.string,
    }
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: Callable
):
    """Set up the SAJ sensors."""
    config = entry.data.copy()
    config.update(entry.options)
    inverter = SAJInverter(config)
    await inverter.setup(hass, async_add_entities)


async def async_setup_platform(
    hass: HomeAssistant, config, async_add_entities: Callable, discovery_info=None
):  # pragma: no cover
    """Set up the SAJ inverter with yaml."""
    _LOGGER.warning(
        "Loading SAJ Solar inverter integration via yaml is deprecated. "
        "Please remove it from your configuration"
    )
    inverter = SAJInverter(config)
    await inverter.setup(hass, async_add_entities)


def _init_pysaj(wifi, config):  # pragma: no cover
    kwargs = {"wifi": wifi}
    if config.get(CONF_USERNAME) and config.get(CONF_PASSWORD):
        kwargs["username"] = config[CONF_USERNAME]
        kwargs["password"] = config[CONF_PASSWORD]

    return pysaj.SAJ(config[CONF_HOST], **kwargs)


class SAJInverter:
    """Representation of a SAJ inverter."""

    def __init__(self, config, saj=None):
        """Init SAJ Inverter class."""
        self._name = config.get(CONF_NAME)
        wifi = config[CONF_TYPE] == INVERTER_TYPES[1]

        self._saj = saj or _init_pysaj(wifi, config)
        self._sensor_def = pysaj.Sensors(wifi)
        if CONF_DEVICE_ID in config:
            self._saj.serialnumber = config[CONF_DEVICE_ID]
        if ENABLED_SENSORS in config:
            for sensor in self._sensor_def:
                sensor.enabled = sensor.key in config[ENABLED_SENSORS]

        self.coordinator = None
        self._interval = config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    def get_enabled_sensors(self):
        """Return enabled sensors keys."""
        return [s.key for s in self._sensor_def if s.enabled]

    @property
    def available(self) -> bool:
        """Return True if device is available."""
        return self.coordinator and self.coordinator.last_update_success

    @property
    def name(self):
        """Return the name of the inverter."""
        return self._name or DEFAULT_NAME

    @property
    def serialnumber(self):
        """Return the serial number of the inverter."""
        return self._saj.serialnumber

    async def connect(self):
        """Try to connect to the inverter."""
        done = await self._saj.read(self._sensor_def)
        if done:
            return

        raise CannotConnect

    async def setup(self, hass, async_add_entities: Callable):
        """Add sensors to Core and get first state."""
        self.coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name=self.name,
            update_method=self.update,
            update_interval=timedelta(seconds=self._interval),
        )
        await self.coordinator.async_refresh()

        async_add_entities(
            SAJSensor(self, sensor) for sensor in self._sensor_def if sensor.enabled
        )

    async def update(self):
        """Fetch data from Inverter."""
        done = await self._saj.read(self._sensor_def)
        if done:
            return self._sensor_def

        raise UpdateFailed


class SAJSensor(CoordinatorEntity, SensorEntity):
    """Representation of a SAJ sensor."""

    def __init__(self, inverter: SAJInverter, pysaj_sensor: pysaj.Sensor):
        """Initialize the SAJ sensor."""
        super().__init__(inverter.coordinator)
        self._inverter = inverter
        self._sensor = pysaj_sensor

    @property
    def name(self):
        """Return the name of the sensor."""
        if self._inverter.name != DEFAULT_NAME:
            return f"saj_{self._inverter.name}_{self._sensor.name}"

        return f"saj_{self._sensor.name}"

    @property
    def state(self):
        """Return the state of the sensor."""
        if not self._inverter.available:
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
        return f"{self._inverter.serialnumber}_{self._sensor.name}"

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self._inverter.serialnumber)
            },
            "name": self._inverter.name,
            "manufacturer": "SAJ",
        }


class CannotConnect(PlatformNotReady):
    """Error to indicate we cannot connect."""
