"""Switch platform for UWANT Vacuum (Tuya).

把「boolean 開關」的可寫 DP 做成 HA 原生的 ``switch`` entity,
讓使用者可以在儀表板上直接點選切換。

v2.2.0 已驗證的開關(2026-10-04 實測):
  ✅ 童鎖           → DP 47   (用戶測試有聲音指示)
  ✅ 勿擾模式       → DP 154  (diff 從 False 變 True)
  ✅ 無樓梯模式     → DP 159  (diff 從 False 變 True)
  ✅ 邊刷啟用       → DP 25   (從清洗拖布動作確認)
  ✅ 地毯清潔啟用   → DP 139
  ✅ 地毯增壓       → DP 45
  ✅ 自動集塵       → DP 148
  ✅ 按鍵燈長亮     → DP 155
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DP_AUTO_DUST_COLLECT,
    DP_CARPET_BOOST,
    DP_CARPET_CLEAN,
    DP_DO_NOT_DISTURB,
    DP_EDGE_BRUSH,
    DP_KEY_LED_ALWAYS_ON,
    DP_KID_LOCK,
    DP_NO_STAIR_MODE,
    DOMAIN,
)
from .coordinator import UwantVacuumCoordinator


@dataclass(frozen=True, kw_only=True)
class UwantSwitchDescription(SwitchEntityDescription):
    """擴充 SwitchEntityDescription。"""

    dp_code: str
    is_on_fn: Callable[[UwantVacuumCoordinator], bool | None]


# v2.2.0 已驗證的開關
SWITCH_DESCRIPTIONS: tuple[UwantSwitchDescription, ...] = (
    UwantSwitchDescription(
        key="do_not_disturb",
        translation_key="do_not_disturb",
        name="Do Not Disturb",
        icon="mdi:bell-off",
        dp_code=DP_DO_NOT_DISTURB,
        is_on_fn=lambda c: c.get_dp(DP_DO_NOT_DISTURB),
    ),
    UwantSwitchDescription(
        key="kid_lock",
        translation_key="kid_lock",
        name="Kid Lock",
        icon="mdi:lock-outline",
        dp_code=DP_KID_LOCK,
        is_on_fn=lambda c: c.get_dp(DP_KID_LOCK),
    ),
    UwantSwitchDescription(
        key="edge_brush",
        translation_key="edge_brush",
        name="Edge Brush",
        icon="mdi:broom",
        dp_code=DP_EDGE_BRUSH,
        is_on_fn=lambda c: c.get_dp(DP_EDGE_BRUSH),
    ),
    UwantSwitchDescription(
        key="carpet_clean",
        translation_key="carpet_clean",
        name="Carpet Clean",
        icon="mdi:rug",
        dp_code=DP_CARPET_CLEAN,
        is_on_fn=lambda c: c.get_dp(DP_CARPET_CLEAN),
    ),
    UwantSwitchDescription(
        key="carpet_boost",
        translation_key="carpet_boost",
        name="Carpet Boost",
        icon="mdi:flash",
        dp_code=DP_CARPET_BOOST,
        is_on_fn=lambda c: c.get_dp(DP_CARPET_BOOST),
    ),
    UwantSwitchDescription(
        key="no_stair_mode",
        translation_key="no_stair_mode",
        name="No-Stair Mode",
        icon="mdi:stairs",
        dp_code=DP_NO_STAIR_MODE,
        is_on_fn=lambda c: c.get_dp(DP_NO_STAIR_MODE),
    ),
    UwantSwitchDescription(
        key="auto_dust_collect",
        translation_key="auto_dust_collect",
        name="Auto Dust Collect",
        icon="mdi:robot-vacuum",
        dp_code=DP_AUTO_DUST_COLLECT,
        is_on_fn=lambda c: c.get_dp(DP_AUTO_DUST_COLLECT),
    ),
    UwantSwitchDescription(
        key="key_led_always_on",
        translation_key="key_led_always_on",
        name="Key LED Always On",
        icon="mdi:led-outline",
        dp_code=DP_KEY_LED_ALWAYS_ON,
        is_on_fn=lambda c: c.get_dp(DP_KEY_LED_ALWAYS_ON),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch entities from a config entry.

    只新增裝置**有回報**的開關(避免無效的 entity)。
    """
    coordinator: UwantVacuumCoordinator = hass.data[DOMAIN][entry.entry_id]
    added: list[SwitchEntity] = []
    for desc in SWITCH_DESCRIPTIONS:
        if desc.is_on_fn(coordinator) is not None:
            added.append(UwantSwitchEntity(coordinator, desc))
    async_add_entities(added, update_before_add=True)


class UwantSwitchEntity(CoordinatorEntity[UwantVacuumCoordinator], SwitchEntity):
    """UWANT 單一開關 entity。"""

    _attr_has_entity_name = True
    entity_description: UwantSwitchDescription

    def __init__(
        self,
        coordinator: UwantVacuumCoordinator,
        description: UwantSwitchDescription,
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

    @property
    def is_on(self) -> bool | None:
        """回報開關狀態。"""
        return self.entity_description.is_on_fn(self.coordinator)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """開啟。"""
        await self.coordinator.async_send_command(
            self.entity_description.dp_code, True
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """關閉。"""
        await self.coordinator.async_send_command(
            self.entity_description.dp_code, False
        )

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success
