"""Tests for SAJ sensor."""
from unittest.mock import AsyncMock, Mock

import pytest

from homeassistant.components.saj.const import ENABLED_SENSORS
from homeassistant.components.saj.sensor import CannotConnect, SAJInverter
from homeassistant.core import HomeAssistant


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


async def test_enabled_sensors_from_config(hass, config, saj):
    """Test enabled sensors."""
    inverter = SAJInverter(hass, config, saj)
    assert ["p-ac", "temp", "state"] == inverter.get_enabled_sensors()


async def test_connect(hass, config, saj):
    """Test connect calls mocked read."""
    inverter = SAJInverter(hass, config, saj)
    await inverter.connect()
    assert ["p-ac", "state"] == inverter.get_enabled_sensors()


async def test_cannot_connect(hass, config, saj):
    """Test connect raises CannotConnect."""
    saj.read = AsyncMock()
    saj.read.return_value = False
    inverter = SAJInverter(hass, config, saj)
    with pytest.raises(CannotConnect):
        await inverter.connect()


async def test_add_sensors(hass, config, saj):
    """Test add entities on setup."""
    inverter = SAJInverter(hass, config, saj)
    add_fn = Mock()
    await inverter.setup(add_fn)
    add_fn.assert_called()


async def test_available(hass: HomeAssistant, config, saj):
    """Test available."""
    inverter = SAJInverter(hass, config, saj)
    add_fn = Mock()
    await inverter.setup(add_fn)
    assert inverter.available
    saj.read = AsyncMock()
    saj.read.return_value = False
    await inverter.coordinator.async_refresh()
    assert inverter.available is False
