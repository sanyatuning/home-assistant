"""The tests for Netatmo camera."""
from unittest.mock import patch

from homeassistant.components import camera
from homeassistant.components.camera import STATE_STREAMING
from homeassistant.components.netatmo.const import (
    SERVICE_SET_CAMERA_LIGHT,
    SERVICE_SET_PERSON_AWAY,
    SERVICE_SET_PERSONS_HOME,
)
from homeassistant.const import CONF_WEBHOOK_ID

from .common import simulate_webhook


async def test_setup_component_with_webhook(hass, camera_entry):
    """Test setup with webhook."""
    webhook_id = camera_entry.data[CONF_WEBHOOK_ID]
    await hass.async_block_till_done()

    camera_entity_indoor = "camera.netatmo_hall"
    camera_entity_outdoor = "camera.netatmo_garden"
    assert hass.states.get(camera_entity_indoor).state == "streaming"
    response = {
        "event_type": "off",
        "device_id": "12:34:56:00:f1:62",
        "camera_id": "12:34:56:00:f1:62",
        "event_id": "601dce1560abca1ebad9b723",
        "push_type": "NACamera-off",
    }
    await simulate_webhook(hass, webhook_id, response)

    assert hass.states.get(camera_entity_indoor).state == "idle"

    response = {
        "event_type": "on",
        "device_id": "12:34:56:00:f1:62",
        "camera_id": "12:34:56:00:f1:62",
        "event_id": "646227f1dc0dfa000ec5f350",
        "push_type": "NACamera-on",
    }
    await simulate_webhook(hass, webhook_id, response)

    assert hass.states.get(camera_entity_indoor).state == "streaming"

    response = {
        "event_type": "light_mode",
        "device_id": "12:34:56:00:a5:a4",
        "camera_id": "12:34:56:00:a5:a4",
        "event_id": "601dce1560abca1ebad9b723",
        "push_type": "NOC-light_mode",
        "sub_type": "on",
    }
    await simulate_webhook(hass, webhook_id, response)

    assert hass.states.get(camera_entity_indoor).state == "streaming"
    assert hass.states.get(camera_entity_outdoor).attributes["light_state"] == "on"

    response = {
        "event_type": "light_mode",
        "device_id": "12:34:56:00:a5:a4",
        "camera_id": "12:34:56:00:a5:a4",
        "event_id": "601dce1560abca1ebad9b723",
        "push_type": "NOC-light_mode",
        "sub_type": "auto",
    }
    await simulate_webhook(hass, webhook_id, response)

    assert hass.states.get(camera_entity_outdoor).attributes["light_state"] == "auto"

    response = {
        "event_type": "light_mode",
        "device_id": "12:34:56:00:a5:a4",
        "event_id": "601dce1560abca1ebad9b723",
        "push_type": "NOC-light_mode",
    }
    await simulate_webhook(hass, webhook_id, response)

    assert hass.states.get(camera_entity_indoor).state == "streaming"
    assert hass.states.get(camera_entity_outdoor).attributes["light_state"] == "auto"


IMAGE_BYTES_FROM_STREAM = b"test stream image bytes"


async def test_camera_image_local(hass, camera_entry, requests_mock):
    """Test retrieval or local camera image."""
    await hass.async_block_till_done()

    uri = "http://192.168.0.123/678460a0d47e5618699fb31169e2b47d"
    stream_uri = uri + "/live/files/high/index.m3u8"
    camera_entity_indoor = "camera.netatmo_hall"
    cam = hass.states.get(camera_entity_indoor)

    assert cam is not None
    assert cam.state == STATE_STREAMING

    stream_source = await camera.async_get_stream_source(hass, camera_entity_indoor)
    assert stream_source == stream_uri

    requests_mock.get(
        uri + "/live/snapshot_720.jpg",
        content=IMAGE_BYTES_FROM_STREAM,
    )
    image = await camera.async_get_image(hass, camera_entity_indoor)
    assert image.content == IMAGE_BYTES_FROM_STREAM


async def test_camera_image_vpn(hass, camera_entry, requests_mock):
    """Test retrieval of remote camera image."""
    await hass.async_block_till_done()

    uri = (
        "https://prodvpn-eu-2.netatmo.net/restricted/10.255.248.91/"
        "6d278460699e56180d47ab47169efb31/MpEylTU2MDYzNjRVD-LJxUnIndumKzLboeAwMDqTTw,,"
    )
    stream_uri = uri + "/live/files/high/index.m3u8"
    camera_entity_indoor = "camera.netatmo_garden"
    cam = hass.states.get(camera_entity_indoor)

    assert cam is not None
    assert cam.state == STATE_STREAMING

    stream_source = await camera.async_get_stream_source(hass, camera_entity_indoor)
    assert stream_source == stream_uri

    requests_mock.get(
        uri + "/live/snapshot_720.jpg",
        content=IMAGE_BYTES_FROM_STREAM,
    )
    image = await camera.async_get_image(hass, camera_entity_indoor)
    assert image.content == IMAGE_BYTES_FROM_STREAM


async def test_service_set_person_away(hass, camera_entry):
    """Test service to set person as away."""
    await hass.async_block_till_done()

    data = {
        "entity_id": "camera.netatmo_hall",
        "person": "Richard Doe",
    }

    with patch("pyatmo.camera.CameraData.set_persons_away") as mock_set_persons_away:
        await hass.services.async_call(
            "netatmo", SERVICE_SET_PERSON_AWAY, service_data=data
        )
        await hass.async_block_till_done()
        mock_set_persons_away.assert_called_once_with(
            person_id="91827376-7e04-5298-83af-a0cb8372dff3",
            home_id="91763b24c43d3e344f424e8b",
        )

    data = {
        "entity_id": "camera.netatmo_hall",
    }

    with patch("pyatmo.camera.CameraData.set_persons_away") as mock_set_persons_away:
        await hass.services.async_call(
            "netatmo", SERVICE_SET_PERSON_AWAY, service_data=data
        )
        await hass.async_block_till_done()
        mock_set_persons_away.assert_called_once_with(
            person_id=None,
            home_id="91763b24c43d3e344f424e8b",
        )


async def test_service_set_persons_home(hass, camera_entry):
    """Test service to set persons as home."""
    await hass.async_block_till_done()

    data = {
        "entity_id": "camera.netatmo_hall",
        "persons": "John Doe",
    }

    with patch("pyatmo.camera.CameraData.set_persons_home") as mock_set_persons_home:
        await hass.services.async_call(
            "netatmo", SERVICE_SET_PERSONS_HOME, service_data=data
        )
        await hass.async_block_till_done()
        mock_set_persons_home.assert_called_once_with(
            person_ids=["91827374-7e04-5298-83ad-a0cb8372dff1"],
            home_id="91763b24c43d3e344f424e8b",
        )


async def test_service_set_camera_light(hass, camera_entry):
    """Test service to set the outdoor camera light mode."""
    await hass.async_block_till_done()

    data = {
        "entity_id": "camera.netatmo_garden",
        "camera_light_mode": "on",
    }

    with patch("pyatmo.camera.CameraData.set_state") as mock_set_state:
        await hass.services.async_call(
            "netatmo", SERVICE_SET_CAMERA_LIGHT, service_data=data
        )
        await hass.async_block_till_done()
        mock_set_state.assert_called_once_with(
            home_id="91763b24c43d3e344f424e8b",
            camera_id="12:34:56:00:a5:a4",
            floodlight="on",
        )
