"""Light platform for SLZB-Ultima Ambilight."""

from dataclasses import dataclass
import json
from typing import Any

from homeassistant.components import mqtt
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
    LightEntityDescription,
    LightEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SmConfigEntry, SmDataUpdateCoordinator
from .entity import SmEntity

PARALLEL_UPDATES = 1

EFFECT_SOLID = 0
EFFECT_OFF = 1


@dataclass(kw_only=True, frozen=True)
class SmLightEntityDescription(LightEntityDescription):
    """Class describing Smlight light entities."""

    effect_list: list[str]


AMBILIGHT = SmLightEntityDescription(
    key="ambilight",
    translation_key="ambilight",
    icon="mdi:led-strip",
    effect_list=["Solid", "Blur", "Rainbow"],
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Initialize light for SLZB-Ultima device."""
    coordinator = entry.runtime_data.data
    model = coordinator.data.info.model or ""

    if "ULTIMA" in model.upper():
        if not await mqtt.async_wait_for_mqtt_client(hass):
            return
        async_add_entities([SmLightEntity(coordinator, AMBILIGHT)])


class SmLightEntity(SmEntity, LightEntity):
    """Representation of light entity for SLZB-Ultima Ambilight."""

    coordinator: SmDataUpdateCoordinator
    entity_description: SmLightEntityDescription
    _attr_color_mode = ColorMode.RGB
    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_supported_features = LightEntityFeature.EFFECT

    def __init__(
        self,
        coordinator: SmDataUpdateCoordinator,
        description: SmLightEntityDescription,
    ) -> None:
        """Initialize light entity."""
        super().__init__(coordinator)
        mqtt_base_topic = coordinator.data.info.mqtt_base_topic or "zhub"
        self._command_topic = f"{mqtt_base_topic}/api2/write/ambilight"

        self.entity_description = description
        self._attr_unique_id = f"{coordinator.unique_id}-{description.key}"
        self._attr_is_on = False
        self._attr_rgb_color = (255, 255, 255)
        self._attr_brightness = 128
        self._attr_effect = "Solid"
        self._attr_effect_list = description.effect_list

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Format kwargs into the specific schema for SLZB-OS and publish via MQTT."""
        payload: dict[str, Any] = {"effect": EFFECT_SOLID}

        if ATTR_EFFECT in kwargs:
            effect_name: str = kwargs[ATTR_EFFECT]
            self._attr_effect = effect_name
            payload["effect"] = self._map_effect(effect_name)
        if ATTR_BRIGHTNESS in kwargs:
            self._attr_brightness = kwargs[ATTR_BRIGHTNESS]
            payload["bri"] = self._attr_brightness
        if ATTR_RGB_COLOR in kwargs:
            self._attr_rgb_color = kwargs[ATTR_RGB_COLOR]
            payload["color"] = f"#{''.join(f'{c:02x}' for c in self._attr_rgb_color)}"

        self._attr_is_on = True

        await mqtt.async_publish(
            self.hass, self._command_topic, json.dumps(payload), qos=0, retain=False
        )
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the Ambilight off using effect OFF."""
        payload = {"effect": EFFECT_OFF}
        self._attr_is_on = False

        await mqtt.async_publish(
            self.hass, self._command_topic, json.dumps(payload), qos=0, retain=False
        )
        self.async_write_ha_state()

    def _map_effect(self, effect: str) -> int:
        """Map effect string to SLZB effect index."""
        try:
            return self.entity_description.effect_list.index(effect)
        except ValueError:
            return EFFECT_OFF
