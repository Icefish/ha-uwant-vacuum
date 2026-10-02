"""Button platform for UWANT Vacuum (Tuya).

把「按下就觸發」的指令做成 HA 原生的 ``button`` entity,
讓使用者可以在儀表板上放一個按鈕,按下去就觸發。

目前提供的按鈕:
  * Find Device —— 觸發吸塵器嗶嗶叫(用 DP 149)
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import UwantVacuumCoordinator


@dataclass(frozen=True, kw_only=True)
class UwantButtonDescription(ButtonEntityDescription):
    """擴充 ButtonEntityDescription,附帶按下時的動作。"""

    press_fn: Callable[[UwantVacuumCoordinator], Any]


BUTTON_DESCRIPTIONS: tuple[UwantButtonDescription, ...] = (
    UwantButtonDescription(
        key="find_device",
        translation_key="find_device",
        name="Find Device",
        icon="mdi:map-marker-radius",
        press_fn=lambda coord: coord.async_send_command("find_device", True),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button entities from a config entry."""
    coordinator: UwantVacuumCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        UwantButtonEntity(coordinator, desc) for desc in BUTTON_DESCRIPTIONS
    )


class UwantButtonEntity(CoordinatorEntity[UwantVacuumCoordinator], ButtonEntity):
    """UWANT 單一按鈕 entity。"""

    _attr_has_entity_name = True
    entity_description: UwantButtonDescription

    def __init__(
        self,
        coordinator: UwantVacuumCoordinator,
        description: UwantButtonDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.device_id)},
            "name": coordinator.device_name,
            "manufacturer": "UWANT",
            "model": "Vacuum (Tuya-based)",
        }

    async def async_press(self) -> None:
        """使用者按下按鈕。"""
        await self.entity_description.press_fn(self.coordinator)
