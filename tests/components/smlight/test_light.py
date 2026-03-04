"""Tests for SMLIGHT light entities."""

import json
from unittest.mock import MagicMock, patch

from pysmlight import Info
import pytest
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ATTR_RGB_COLOR,
    DOMAIN as LIGHT_DOMAIN,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.components.smlight.light import EFFECT_OFF, EFFECT_SOLID
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .conftest import setup_integration

from tests.common import MockConfigEntry, snapshot_platform
from tests.typing import MqttMockHAClient


@pytest.fixture
def platforms() -> Platform | list[Platform]:
    """Platforms, which should be loaded during the test."""
    return [Platform.LIGHT]


MOCK_ULTIMA = Info(
    MAC="AA:BB:CC:DD:EE:FF",
    model="SLZB-Ultima3",
    mqtt_base_topic="zhub",
)


async def test_light_setup_ultima(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    mock_config_entry: MockConfigEntry,
    mock_smlight_client: MagicMock,
    mqtt_mock: MqttMockHAClient,
    snapshot: SnapshotAssertion,
) -> None:
    """Test light entity is created for Ultima devices."""
    mock_smlight_client.get_info.side_effect = None
    mock_smlight_client.get_info.return_value = MOCK_ULTIMA
    entry = await setup_integration(hass, mock_config_entry)

    await snapshot_platform(hass, entity_registry, snapshot, entry.entry_id)

    await hass.config_entries.async_unload(entry.entry_id)


async def test_light_not_created_non_ultima(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_smlight_client: MagicMock,
    mqtt_mock: MqttMockHAClient,
) -> None:
    """Test light entity is not created for non-Ultima devices."""
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get("light.mock_title_ambilight")
    assert state is None


async def test_light_not_created_without_mqtt(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_smlight_client: MagicMock,
) -> None:
    """Test light entity is not created when MQTT is not available."""
    mock_smlight_client.get_info.side_effect = None
    mock_smlight_client.get_info.return_value = MOCK_ULTIMA

    with patch(
        "homeassistant.components.smlight.light.mqtt.async_wait_for_mqtt_client",
        return_value=False,
    ):
        await setup_integration(hass, mock_config_entry)

    state = hass.states.get("light.mock_title_ambilight")
    assert state is None


async def test_light_turn_on_off(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_smlight_client: MagicMock,
    mqtt_mock: MqttMockHAClient,
) -> None:
    """Test turning light on and off."""
    mock_smlight_client.get_info.side_effect = None
    mock_smlight_client.get_info.return_value = MOCK_ULTIMA
    await setup_integration(hass, mock_config_entry)

    entity_id = "light.mock_title_ambilight"

    mqtt_mock.async_publish.reset_mock()
    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )

    mqtt_mock.async_publish.assert_called_once_with(
        "zhub/api2/write/ambilight",
        json.dumps({"effect": EFFECT_SOLID}),
        0,
        False,
    )

    state = hass.states.get(entity_id)
    assert state.state == STATE_ON

    mqtt_mock.async_publish.reset_mock()
    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )

    mqtt_mock.async_publish.assert_called_once_with(
        "zhub/api2/write/ambilight",
        json.dumps({"effect": EFFECT_OFF}),
        0,
        False,
    )

    state = hass.states.get(entity_id)
    assert state.state == STATE_OFF


async def test_light_brightness(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_smlight_client: MagicMock,
    mqtt_mock: MqttMockHAClient,
) -> None:
    """Test setting brightness."""
    mock_smlight_client.get_info.side_effect = None
    mock_smlight_client.get_info.return_value = MOCK_ULTIMA
    await setup_integration(hass, mock_config_entry)

    entity_id = "light.mock_title_ambilight"

    mqtt_mock.async_publish.reset_mock()
    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity_id, ATTR_BRIGHTNESS: 200},
        blocking=True,
    )

    mqtt_mock.async_publish.assert_called_once_with(
        "zhub/api2/write/ambilight",
        json.dumps({"effect": EFFECT_SOLID, "bri": 200}),
        0,
        False,
    )

    state = hass.states.get(entity_id)
    assert state.state == STATE_ON
    assert state.attributes["brightness"] == 200


async def test_light_rgb_color(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_smlight_client: MagicMock,
    mqtt_mock: MqttMockHAClient,
) -> None:
    """Test setting RGB color."""
    mock_smlight_client.get_info.side_effect = None
    mock_smlight_client.get_info.return_value = MOCK_ULTIMA
    await setup_integration(hass, mock_config_entry)

    entity_id = "light.mock_title_ambilight"

    mqtt_mock.async_publish.reset_mock()
    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity_id, ATTR_RGB_COLOR: (255, 128, 64)},
        blocking=True,
    )

    mqtt_mock.async_publish.assert_called_once_with(
        "zhub/api2/write/ambilight",
        json.dumps({"effect": EFFECT_SOLID, "color": "#ff8040"}),
        0,
        False,
    )

    state = hass.states.get(entity_id)
    assert state.state == STATE_ON
    assert state.attributes["rgb_color"] == (255, 128, 64)


async def test_light_effect(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_smlight_client: MagicMock,
    mqtt_mock: MqttMockHAClient,
) -> None:
    """Test setting effect."""
    mock_smlight_client.get_info.side_effect = None
    mock_smlight_client.get_info.return_value = MOCK_ULTIMA
    await setup_integration(hass, mock_config_entry)

    entity_id = "light.mock_title_ambilight"

    # Test Rainbow effect
    mqtt_mock.async_publish.reset_mock()
    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity_id, ATTR_EFFECT: "Rainbow"},
        blocking=True,
    )

    mqtt_mock.async_publish.assert_called_once_with(
        "zhub/api2/write/ambilight",
        json.dumps({"effect": 2}),
        0,
        False,
    )

    # Test Blur effect
    mqtt_mock.async_publish.reset_mock()
    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity_id, ATTR_EFFECT: "Blur"},
        blocking=True,
    )

    mqtt_mock.async_publish.assert_called_once_with(
        "zhub/api2/write/ambilight",
        json.dumps({"effect": 1}),
        0,
        False,
    )

    state = hass.states.get(entity_id)
    assert state.state == STATE_ON
    assert state.attributes["effect"] == "Blur"


async def test_light_invalid_effect(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_smlight_client: MagicMock,
    mqtt_mock: MqttMockHAClient,
) -> None:
    """Test handling of invalid effect name falls back to EFFECT_OFF."""
    mock_smlight_client.get_info.side_effect = None
    mock_smlight_client.get_info.return_value = MOCK_ULTIMA
    await setup_integration(hass, mock_config_entry)

    entity_id = "light.mock_title_ambilight"

    mqtt_mock.async_publish.reset_mock()
    await hass.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity_id, ATTR_EFFECT: "InvalidEffect"},
        blocking=True,
    )

    mqtt_mock.async_publish.assert_called_once_with(
        "zhub/api2/write/ambilight",
        json.dumps({"effect": EFFECT_OFF}),
        0,
        False,
    )
