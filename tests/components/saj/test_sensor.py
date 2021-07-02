"""Tests for SAJ sensor."""
from unittest.mock import AsyncMock, Mock

import pysaj
import pytest

from homeassistant.components.saj.sensor import CannotConnect, SAJInverter, SAJSensor
from homeassistant.core import HomeAssistant


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


async def test_connect(saj):
    """Test connect calls mocked read."""
    inverter = SAJInverter(saj=saj)
    await inverter.connect()
    assert inverter.get_enabled_sensors() == ["p-ac", "state"]


async def test_cannot_connect(saj):
    """Test connect raises CannotConnect."""
    saj.read = AsyncMock()
    saj.read.return_value = False
    inverter = SAJInverter(saj=saj)
    with pytest.raises(CannotConnect):
        await inverter.connect()


async def test_add_sensors(hass, saj):
    """Test add entities on setup."""
    inverter = SAJInverter(saj=saj)
    add_fn = Mock()
    await inverter.setup(hass, add_fn)
    add_fn.assert_called()


async def test_available(hass: HomeAssistant, saj):
    """Test available."""
    inverter = SAJInverter(saj=saj)
    add_fn = Mock()
    await inverter.setup(hass, add_fn)
    assert inverter.available
    saj.read = AsyncMock()
    saj.read.return_value = False
    await inverter.coordinator.async_refresh()
    assert inverter.available is False


async def test_sensor(saj):
    """Test sensor class."""
    inverter = SAJInverter(saj=saj)
    pysaj_sensor = pysaj.Sensor("p-ac", 11, 23, "", "current_power", "W")
    sensor = SAJSensor(inverter, pysaj_sensor)
    assert sensor.name == "SAJ Inverter current_power"
    assert sensor.state is None
    assert sensor.available
    assert sensor.unit_of_measurement == "W"
    assert sensor.device_class == "power"
    assert sensor.unique_id == "123456789_current_power"
    assert sensor.device_info == {
        "identifiers": {("saj", "123456789")},
        "name": "SAJ Solar inverter",
        "manufacturer": "SAJ",
    }


async def test_sensor_temp(saj):
    """Test sensor class."""
    inverter = SAJInverter("Second inverter", saj=saj)
    pysaj_sensor = pysaj.Sensor("temp", 20, 32, "/10", "temperature", "°C")
    sensor = SAJSensor(inverter, pysaj_sensor)
    assert sensor.name == "Second inverter temperature"
    assert sensor.unit_of_measurement == "°C"
    assert sensor.device_class == "temperature"
