"""Sensor platform for UWANT Vacuum (Tuya).

提供標準電池電量感測器以及額外感測器:
已清掃時間/面積、故障碼、清掃模式、音量、勿擾、水量、吸力、累計。
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfArea, UnitOfTime, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DP_BATTERY_NEW,
    DP_BATTERY_OLD,
    DP_CLEAN_AREA,
    DP_CLEAN_MODE,
    DP_CLEAN_TIME,
    DP_DO_NOT_DISTURB,
    DP_FAULT,
    DP_KID_LOCK,
    DP_SUCTION,
    DP_VOLUME,
    DP_WATER_LEVEL,
    DOMAIN,
)
from .coordinator import UwantVacuumCoordinator


@dataclass(frozen=True, kw_only=True)
class UwantSensorDescription(SensorEntityDescription):
    """擴充 SensorEntityDescription,附帶取值函式。"""

    value_fn: Callable[[dict[str, Any]], Any]


def _get_battery_level(data: dict[str, Any]) -> int | None:
    """提取電量百分比 (0-100)。"""
    for k in (DP_BATTERY_NEW, DP_BATTERY_OLD, "battery_percentage", "battery", "8"):
        val = data.get(k)
        if val is not None:
            try:
                return max(0, min(100, int(val)))
            except (ValueError, TypeError):
                continue
    return None


# 中央定義所有 sensor
SENSORS: tuple[UwantSensorDescription, ...] = (
    # === 電池電量感測器 (HA 官方核心標準: 供卡片、頂部徽章與電池實體顯示) ===
    UwantSensorDescription(
        key="battery",
        translation_key="battery",
        name="Battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_get_battery_level,
    ),
    # === 統計(累計) ===
    UwantSensorDescription(
        key="clean_time",
        translation_key="clean_time",
        name="Clean Time",
        icon="mdi:timer-sand",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.get(DP_CLEAN_TIME, data.get("6")),
    ),
    UwantSensorDescription(
        key="clean_area",
        translation_key="clean_area",
        name="Clean Area",
        icon="mdi:texture-box",
        native_unit_of_measurement=UnitOfArea.SQUARE_METERS,
        device_class=SensorDeviceClass.AREA,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.get(DP_CLEAN_AREA, data.get("7")),
    ),
    # === 故障 ===
    UwantSensorDescription(
        key="fault",
        translation_key="fault",
        name="Fault Code",
        icon="mdi:alert-circle",
        value_fn=lambda data: data.get(DP_FAULT, 0),
    ),
    # === 模式顯示 ===
    UwantSensorDescription(
        key="clean_mode",
        translation_key="clean_mode",
        name="Clean Mode",
        icon="mdi:broom",
        device_class=SensorDeviceClass.ENUM,
        options=["smart", "spot", "edge", "mop", "clean_before_mop", "zone"],
        value_fn=lambda data: data.get(DP_CLEAN_MODE, data.get("132")),
    ),
    UwantSensorDescription(
        key="suction",
        translation_key="suction",
        name="Suction",
        icon="mdi:fan",
        device_class=SensorDeviceClass.ENUM,
        options=["quiet", "normal", "strong", "max"],
        value_fn=lambda data: data.get(DP_SUCTION, data.get("9")),
    ),
    UwantSensorDescription(
        key="water_level",
        translation_key="water_level",
        name="Water Level",
        icon="mdi:water",
        device_class=SensorDeviceClass.ENUM,
        options=["low", "medium", "high"],
        value_fn=lambda data: data.get(DP_WATER_LEVEL, data.get("10")),
    ),
    # === 設定值(可監看,需用 select entity 控制) ===
    UwantSensorDescription(
        key="volume",
        translation_key="volume",
        name="Volume",
        icon="mdi:volume-high",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(DP_VOLUME, data.get("26")),
    ),
    UwantSensorDescription(
        key="do_not_disturb",
        translation_key="do_not_disturb",
        name="Do Not Disturb",
        icon="mdi:bell-off",
        device_class=SensorDeviceClass.ENUM,
        options=["off", "on"],
        value_fn=lambda data: (
            "on" if data.get(DP_DO_NOT_DISTURB, data.get("154")) else "off"
        ),
    ),
    UwantSensorDescription(
        key="kid_lock",
        translation_key="kid_lock",
        name="Kid Lock",
        icon="mdi:lock-outline",
        device_class=SensorDeviceClass.ENUM,
        options=["off", "on"],
        value_fn=lambda data: (
            "on" if data.get(DP_KID_LOCK, data.get("47")) else "off"
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities from a config entry."""
    coordinator: UwantVacuumCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        UwantSensor(coordinator, desc) for desc in SENSORS
    )


class UwantSensor(CoordinatorEntity[UwantVacuumCoordinator], SensorEntity):
    """單一 sensor。"""

    _attr_has_entity_name = True
    entity_description: UwantSensorDescription

    def __init__(
        self,
        coordinator: UwantVacuumCoordinator,
        description: UwantSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.device_id)},
            "name": coordinator.device_name,
            "manufacturer": "UWANT",
            "model": "U300 Robot Vacuum",
        }

    @property
    def native_value(self) -> Any:
        if not self.coordinator.data:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def available(self) -> bool:
        """有資料就視為可用。"""
        return self.coordinator.last_update_success
