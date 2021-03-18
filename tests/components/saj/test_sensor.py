"""Tests for SAJ sensor."""
from unittest.mock import AsyncMock, Mock

import pytest

from homeassistant.components.saj.const import ENABLED_SENSORS
from homeassistant.components.saj.sensor import SAJInverter


@pytest.fixture
def config():
    """Return default config."""
    return {
        "type": "wifi",
        ENABLED_SENSORS: ["p-ac", "e-total", "state"],
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
    assert ["p-ac", "e-total", "state"] == inverter.get_enabled_sensors()


async def test_connect(config, saj):
    """Test connect calls mocked read."""
    inverter = SAJInverter(config, saj)
    await inverter.connect()
    assert ["p-ac", "state"] == inverter.get_enabled_sensors()


async def test_setup_and_interval(hass, config, saj):
    """Test setup and update interval."""
    inverter = SAJInverter(config, saj)

    def add_fn(hass_sensors):
        for sensor in hass_sensors:
            sensor.entity_id = "sensor." + sensor.name
            sensor.hass = hass

    inverter.setup(hass, add_fn)
    await inverter._interval_listener(None)
    assert inverter.available
    saj.read = AsyncMock()
    saj.read.return_value = False
    await inverter._interval_listener(None)
    assert inverter.available is False
