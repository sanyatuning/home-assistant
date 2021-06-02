"""The saj component."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DATA_INVERTER, DATA_UNDO_UPDATE_LISTENER, DOMAIN
from .sensor import SAJInverter

PLATFORMS = ["sensor"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the saj component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up saj from a config entry."""

    config = entry.data.copy()
    config.update(entry.options)
    inverter = SAJInverter(config)
    undo_listener = entry.add_update_listener(update_listener)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        DATA_INVERTER: inverter,
        DATA_UNDO_UPDATE_LISTENER: undo_listener,
    }

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN][entry.entry_id][DATA_UNDO_UPDATE_LISTENER]()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    inverter: SAJInverter = hass.data[DOMAIN][entry.entry_id][DATA_INVERTER]
    inverter.update_options(entry.options)
