"""Select platform for UWANT Vacuum (Tuya).

把「多選一」的可寫 DP 做成 HA 原生的 ``select`` entity,
讓使用者可以直接從 HA 儀表板上下拉選單改變設定。

對應的 DP:
  * 吸力   DP 9 (suction)
  * 水量   DP 10 (water_level)
  * 清掃模式 DP 132 (clean_mode)
  * 水溫   DP 135 (water_temp)
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CLEAN_MODE_DEFAULT,
    CLEAN_MODE_OPTIONS,
    DP_CLEAN_MODE,
    DP_SUCTION,
    DP_WATER_LEVEL,
    DP_WATER_TEMP,
    DOMAIN,
    SUCTION_DEFAULT,
    SUCTION_OPTIONS,
    WATER_LEVEL_DEFAULT,
    WATER_LEVEL_OPTIONS,
    WATER_TEMP_DEFAULT,
    WATER_TEMP_OPTIONS,
)
from .coordinator import UwantVacuumCoordinator


@dataclass(frozen=True, kw_only=True)
class UwantSelectDescription(SelectEntityDescription):
    """擴充 SelectEntityDescription,附帶取值與設定。"""

    dp_code: str
    options: tuple[str, ...]
    current_fn: Callable[[UwantVacuumCoordinator], str | None]


# 中央定義所有可選 entity(順序就是它在 HA 內出現的順序)
SELECT_DESCRIPTIONS: tuple[UwantSelectDescription, ...] = (
    UwantSelectDescription(
        key="suction",
        translation_key="suction",
        name="Suction",
        icon="mdi:fan",
        options=SUCTION_OPTIONS,
        dp_code=DP_SUCTION,
        current_fn=lambda coord: coord.get_dp(DP_SUCTION),
    ),
    UwantSelectDescription(
        key="water_level",
        translation_key="water_level",
        name="Water Level",
        icon="mdi:water",
        options=WATER_LEVEL_OPTIONS,
        dp_code=DP_WATER_LEVEL,
        current_fn=lambda coord: coord.get_dp(DP_WATER_LEVEL),
    ),
    UwantSelectDescription(
        key="clean_mode",
        translation_key="clean_mode",
        name="Clean Mode",
        icon="mdi:broom",
        options=CLEAN_MODE_OPTIONS,
        dp_code=DP_CLEAN_MODE,
        current_fn=lambda coord: coord.get_dp(DP_CLEAN_MODE),
    ),
    UwantSelectDescription(
        key="water_temp",
        translation_key="water_temp",
        name="Water Temperature",
        icon="mdi:thermometer-water",
        options=WATER_TEMP_OPTIONS,
        dp_code=DP_WATER_TEMP,
        current_fn=lambda coord: coord.get_dp(DP_WATER_TEMP),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up select entities from a config entry."""
    coordinator: UwantVacuumCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        UwantSelectEntity(coordinator, desc) for desc in SELECT_DESCRIPTIONS
    )


class UwantSelectEntity(CoordinatorEntity[UwantVacuumCoordinator], SelectEntity):
    """UWANT 單一可選 entity。"""

    _attr_has_entity_name = True
    entity_description: UwantSelectDescription

    def __init__(
        self,
        coordinator: UwantVacuumCoordinator,
        description: UwantSelectDescription,
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
    def current_option(self) -> str | None:
        """回傳目前裝置上對應的值。

        若裝置目前沒有給值,使用對應的預設值。
        """
        val = self.entity_description.current_fn(self.coordinator)
        if val in self.entity_description.options:
            return val
        # 預設值對應表
        defaults = {
            DP_SUCTION: SUCTION_DEFAULT,
            DP_WATER_LEVEL: WATER_LEVEL_DEFAULT,
            DP_CLEAN_MODE: CLEAN_MODE_DEFAULT,
            DP_WATER_TEMP: WATER_TEMP_DEFAULT,
        }
        return defaults.get(self.entity_description.dp_code)

    async def async_select_option(self, option: str) -> None:
        """使用者從 HA UI 選擇新值。"""
        if option not in self.entity_description.options:
            raise ValueError(
                f"{option} 不是有效的 {self.entity_description.dp_code} 值"
            )
        await self.coordinator.async_send_command(
            self.entity_description.dp_code, option
        )
        # 不呼叫 async_request_refresh,等下一次 coordinator tick 自動更新

    @property
    def available(self) -> bool:
        """有資料就視為可用。"""
        return self.coordinator.last_update_success
