"""Tests for SAJ sensor."""
from datetime import timedelta
from unittest.mock import AsyncMock, Mock

import pysaj
import pytest

from homeassistant.components.saj.const import ENABLED_SENSORS
from homeassistant.components.saj.sensor import CannotConnect, SAJInverter, SAJSensor
from homeassistant.const import CONF_NAME, CONF_SCAN_INTERVAL
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
    mock.serialnumber = "123456789"
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


async def test_add_sensors(hass, config, saj):
    """Test add entities on setup."""
    inverter = SAJInverter(config, saj)
    add_fn = Mock()
    await inverter.setup(hass, add_fn)
    add_fn.assert_called()


async def test_available(hass: HomeAssistant, config, saj):
    """Test available."""
    inverter = SAJInverter(config, saj)
    add_fn = Mock()
    await inverter.setup(hass, add_fn)
    assert inverter.available
    saj.read = AsyncMock()
    saj.read.return_value = False
    await inverter.coordinator.async_refresh()
    assert inverter.available is False


async def test_sensor(config, saj):
    """Test sensor class."""
    inverter = SAJInverter(config, saj)
    pysaj_sensor = pysaj.Sensor("p-ac", 11, 23, "", "current_power", "W")
    sensor = SAJSensor(inverter, pysaj_sensor)
    assert "SAJ Inverter current_power" == sensor.name
    assert sensor.state is None
    assert sensor.available
    assert "W" == sensor.unit_of_measurement
    assert "power" == sensor.device_class
    assert "123456789_current_power" == sensor.unique_id
    assert {
        "identifiers": {("saj", "123456789")},
        "name": "SAJ Solar inverter",
        "manufacturer": "SAJ",
    } == sensor.device_info


async def test_sensor_temp(config, saj):
    """Test sensor class."""
    config[CONF_NAME] = "Second inverter"
    inverter = SAJInverter(config, saj)
    pysaj_sensor = pysaj.Sensor("temp", 20, 32, "/10", "temperature", "°C")
    sensor = SAJSensor(inverter, pysaj_sensor)
    assert "Second inverter temperature" == sensor.name
    assert "°C" == sensor.unit_of_measurement
    assert "temperature" == sensor.device_class


async def test_update_options(hass: HomeAssistant, config, saj):
    """Test update options."""
    inverter = SAJInverter(config, saj)
    add_fn = Mock()
    await inverter.setup(hass, add_fn)
    inverter.update_options(
        {
            CONF_SCAN_INTERVAL: 5,
        }
    )
    assert timedelta(seconds=5) == inverter.coordinator.update_interval
