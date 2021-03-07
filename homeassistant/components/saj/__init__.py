"""The saj component."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

PLATFORMS = ["sensor"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the saj component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up saj from a config entry."""

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True
