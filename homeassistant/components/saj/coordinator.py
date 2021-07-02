"""Coordinator to fetch data from SAJ solar inverter."""
import logging
from typing import Callable

import pysaj

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from ...exceptions import ConfigEntryNotReady
from .const import DEFAULT_NAME, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


def _init_pysaj(wifi, host, username, password):  # pragma: no cover
    kwargs = {"wifi": wifi}
    if username and password:
        kwargs["username"] = username
        kwargs["password"] = password

    return pysaj.SAJ(host, **kwargs)


class SAJInverter(DataUpdateCoordinator):
    """Representation of a SAJ inverter."""

    def __init__(
        self, name="", wifi=True, host=None, username=None, password=None, saj=None
    ):
        """Init SAJ Inverter class."""
        super().__init__(
            None,
            _LOGGER,
            name=name or DEFAULT_NAME,
            update_interval=UPDATE_INTERVAL,
            update_method=self.update,
        )
        self.last_update_success = False
        self._saj = saj or _init_pysaj(wifi, host, username, password)
        self._sensor_def = pysaj.Sensors(wifi)

    def get_enabled_sensors(self):
        """Return enabled sensors keys."""
        return [s.key for s in self._sensor_def if s.enabled]

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
        from .sensor import SAJSensor

        self.hass = hass
        await self.async_refresh()

        async_add_entities(
            SAJSensor(self, sensor) for sensor in self._sensor_def if sensor.enabled
        )

    async def update(self):
        """Fetch data from Inverter."""
        done = await self._saj.read(self._sensor_def)
        if done:
            return self._sensor_def

        raise UpdateFailed


class CannotConnect(ConfigEntryNotReady):
    """Error to indicate we cannot connect."""
