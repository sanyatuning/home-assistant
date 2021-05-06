"""Tests for SAJ sensor."""
from unittest.mock import AsyncMock, Mock

import pytest

from homeassistant.components.saj.const import ENABLED_SENSORS
from homeassistant.components.saj.sensor import CannotConnect, SAJInverter
from homeassistant.core import CoreState, HomeAssistant


@pytest.fixture
def config():
    """Return default config."""
    return {
        "type": "wifi",
        ENABLED_SENSORS: ["p-ac", "temp", "state"],
    }


@pytest.fixture
def saj():
    """Mock pysaj library."""

    async def mock_read(sensors):
        for sensor in sensors:
            sensor.enabled = sensor.name == "current_power" or sensor.name == "state"
            if sensor.name == "current_power":
                sensor.value = 1500
        return True

    mock = Mock()
    mock.read = mock_read
    return mock


async def test_enabled_sensors_from_config(config, saj):
    """Test enabled sensors."""
    inverter = SAJInverter(config, saj)
    assert ["p-ac", "temp", "state"] == inverter.get_enabled_sensors()


async def test_connect(config, saj):
    """Test connect calls mocked read."""
    inverter = SAJInverter(config, saj)
    await inverter.connect()
    assert ["p-ac", "state"] == inverter.get_enabled_sensors()


async def test_cannot_connect(config, saj):
    """Test connect raises CannotConnect."""
    saj.read = AsyncMock()
    saj.read.return_value = False
    inverter = SAJInverter(config, saj)
    with pytest.raises(CannotConnect):
        await inverter.connect()


def test_hass_starting(hass, config, saj):
    """Test add callback when core is starting."""
    hass.state = CoreState.starting
    hass.bus.async_listen_once = Mock()
    inverter = SAJInverter(config, saj)
    add_fn = Mock()
    inverter.setup(hass, add_fn)
    hass.bus.async_listen_once.assert_called_once()


async def test_setup_and_interval(hass: HomeAssistant, config, saj):
    """Test setup and update interval."""
    inverter = SAJInverter(config, saj)

    def add_fn(hass_sensors):
        for sensor in hass_sensors:
            sensor.entity_id = "sensor." + sensor.name
            sensor.hass = hass

    inverter.setup(hass, add_fn)
    await hass.async_block_till_done()
    assert inverter.available
    saj.read = AsyncMock()
    saj.read.return_value = False
    await inverter._interval_listener(None)
    assert inverter.available is False
    for sensor in inverter._hass_sensors:
        await sensor.async_will_remove_from_hass()
