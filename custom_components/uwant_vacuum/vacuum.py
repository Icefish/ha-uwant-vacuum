"""Vacuum platform for UWANT Vacuum (Tuya)."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.vacuum import (
    StateVacuumEntity,
    VacuumActivity,
    VacuumEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CLEAN_MODE_DEFAULT,
    CLEAN_MODE_OPTIONS,
    DP_BATTERY_NEW,
    DP_BATTERY_OLD,
    DP_CHARGE_SWITCH_NEW,
    DP_CHARGE_SWITCH_OLD,
    DP_CLEAN_MODE,
    DP_CLEAN_STATUS,
    DP_CLEAN_SWITCH_NEW,
    DP_CLEAN_SWITCH_OLD,
    DP_DO_NOT_DISTURB,
    DP_FAULT,
    DP_FIND_DEVICE,
    DP_SUCTION,
    DP_VOLUME,
    DP_WATER_LEVEL,
    DP_WATER_TEMP,
    DOMAIN,
    SUCTION_DEFAULT,
    SUCTION_OPTIONS,
    TUYA_STATUS_TO_HA,
    U300_WORK_STATUS_TO_HA,
    WATER_LEVEL_DEFAULT,
    WATER_LEVEL_OPTIONS,
    WATER_TEMP_DEFAULT,
    WATER_TEMP_OPTIONS,
)
from .coordinator import UwantVacuumCoordinator

# 本地模式的工作狀態 DP (U300 是 DP 5)
DP_WORK_STATUS = "work_status"

_LOGGER = logging.getLogger(__name__)

# 支援的標準 HA 內建功能旗標
SUPPORT_FLAGS = (
    VacuumEntityFeature.START
    | VacuumEntityFeature.PAUSE
    | VacuumEntityFeature.STOP
    | VacuumEntityFeature.RETURN_HOME
    | VacuumEntityFeature.FAN_SPEED
    | VacuumEntityFeature.SEND_COMMAND
    | VacuumEntityFeature.LOCATE
    | VacuumEntityFeature.CLEAN_SPOT
)

# 相容性旗標 (動態檢查 HA 版本是否具備該列舉項)
if hasattr(VacuumEntityFeature, "BATTERY"):
    SUPPORT_FLAGS |= getattr(VacuumEntityFeature, "BATTERY")
if hasattr(VacuumEntityFeature, "STATE"):
    SUPPORT_FLAGS |= getattr(VacuumEntityFeature, "STATE")
if hasattr(VacuumEntityFeature, "STATUS"):
    SUPPORT_FLAGS |= getattr(VacuumEntityFeature, "STATUS")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up vacuum entity from a config entry."""
    coordinator: UwantVacuumCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([UwantVacuumEntity(coordinator)], update_before_add=True)


class UwantVacuumEntity(CoordinatorEntity[UwantVacuumCoordinator], StateVacuumEntity):
    """UWANT 掃地機 vacuum entity (完整支援 HA 原生內建控制卡片)。"""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = SUPPORT_FLAGS

    def __init__(self, coordinator: UwantVacuumCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = coordinator.device_id
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.device_id)},
            "name": coordinator.device_name,
            "manufacturer": "UWANT",
            "model": "U300 Robot Vacuum",
        }

    # ---------- 狀態與活動 ----------

    @property
    def activity(self) -> VacuumActivity | None:
        """回傳當前 HA 標準活動狀態 (供現代 HA StateVacuumEntity 使用)。"""
        if not self.coordinator.data:
            return None

        # 故障優先判斷
        fault = self.coordinator.get_dp(DP_FAULT, default=0)
        if fault and fault != 0:
            return VacuumActivity.ERROR

        # 本地模式: work_status 是最準確的狀態來源 (DP 5)
        work_status = self.coordinator.get_dp(DP_WORK_STATUS, "5")
        if isinstance(work_status, str):
            mapped = U300_WORK_STATUS_TO_HA.get(work_status.lower())
            if mapped:
                return _to_activity(mapped)

        # 檢查 clean_status (DP 130)
        status = self.coordinator.get_dp(DP_CLEAN_STATUS, "130")
        if isinstance(status, str):
            mapped = TUYA_STATUS_TO_HA.get(status.lower())
            if mapped:
                return _to_activity(mapped)

        # 否則從 clean_switch / charge_switch 推斷
        cleaning = bool(self.coordinator.get_dp(DP_CLEAN_SWITCH_NEW, DP_CLEAN_SWITCH_OLD, "1"))
        charging = bool(self.coordinator.get_dp(DP_CHARGE_SWITCH_NEW, DP_CHARGE_SWITCH_OLD, "3"))

        if charging:
            return VacuumActivity.RETURNING if not _is_full(self.coordinator) else VacuumActivity.DOCKED
        if cleaning:
            return VacuumActivity.CLEANING

        return VacuumActivity.DOCKED

    @property
    def state(self) -> str | None:
        """回傳當前文字狀態 (供前端卡片及歷史記錄顯示)。"""
        act = self.activity
        if act is not None:
            return act.value if hasattr(act, "value") else str(act)
        return "docked"

    @property
    def status(self) -> str | None:
        """回傳詳細狀態字串。"""
        raw_status = self.coordinator.get_dp(DP_WORK_STATUS, "5")
        if isinstance(raw_status, str):
            return raw_status
        return self.state

    # ---------- 電池與電量 ----------

    @property
    def battery_level(self) -> int | None:
        """電量百分比 (0-100)。"""
        if not self.coordinator.data:
            return None
        for k in (DP_BATTERY_NEW, DP_BATTERY_OLD, "battery_percentage", "battery", "8"):
            val = self.coordinator.data.get(k)
            if val is not None:
                try:
                    return max(0, min(100, int(val)))
                except (ValueError, TypeError):
                    continue
        return None

    @property
    def battery_icon(self) -> str:
        """動態電量圖示 (充電中 vs 運作中)。"""
        charging = self.activity in (VacuumActivity.DOCKED, VacuumActivity.RETURNING)
        level = self.battery_level or 0

        if charging:
            if level >= 95:
                return "mdi:battery-charging-100"
            if level >= 80:
                return "mdi:battery-charging-80"
            if level >= 60:
                return "mdi:battery-charging-60"
            if level >= 40:
                return "mdi:battery-charging-40"
            if level >= 20:
                return "mdi:battery-charging-20"
            return "mdi:battery-charging-outline"

        if level >= 95:
            return "mdi:battery"
        if level >= 80:
            return "mdi:battery-80"
        if level >= 60:
            return "mdi:battery-60"
        if level >= 40:
            return "mdi:battery-40"
        if level >= 20:
            return "mdi:battery-20"
        return "mdi:battery-alert"

    # ---------- 吸力與風速 ----------

    @property
    def fan_speed(self) -> str | None:
        """當前吸力等級 (HA 標準風速)。"""
        val = self.coordinator.get_dp(DP_SUCTION, "9")
        if isinstance(val, str):
            return val
        return None

    @property
    def fan_speed_list(self) -> list[str]:
        """吸力選項清單。"""
        return list(SUCTION_OPTIONS)

    async def async_set_fan_speed(self, fan_speed: str, **kwargs: Any) -> None:
        """設定吸力等級。"""
        if fan_speed not in SUCTION_OPTIONS:
            raise ValueError(
                f"不支援的吸力: {fan_speed}。有效值: {list(SUCTION_OPTIONS)}"
            )
        await self.coordinator.async_send_command(DP_SUCTION, fan_speed)

    # ---------- HA 標準控制指令 ----------

    async def async_start(self) -> None:
        """開始清掃 (HA 內建開始按鈕)。"""
        _LOGGER.info("發送開始清掃指令 (switch_go = True)")
        await self.coordinator.async_send_commands(
            [
                {"code": DP_CLEAN_SWITCH_NEW, "value": True},
                {"code": DP_CLEAN_SWITCH_OLD, "value": True},
                {"code": "1", "value": True},
            ]
        )

    async def async_pause(self) -> None:
        """暫停清掃 (HA 內建暫停按鈕)。"""
        _LOGGER.info("發送暫停清掃指令 (switch_go = False)")
        await self.coordinator.async_send_commands(
            [
                {"code": DP_CLEAN_SWITCH_NEW, "value": False},
                {"code": DP_CLEAN_SWITCH_OLD, "value": False},
                {"code": "1", "value": False},
            ]
        )

    async def async_stop(self, **kwargs: Any) -> None:
        """停止清掃 (HA 內建停止按鈕)。"""
        await self.async_pause()

    async def async_start_pause(self, **kwargs: Any) -> None:
        """開始/暫停切換 (HA 內建 Toggle 按鈕)。"""
        if self.activity == VacuumActivity.CLEANING:
            await self.async_pause()
        else:
            await self.async_start()

    async def async_return_to_base(self, **kwargs: Any) -> None:
        """返回充電座 (HA 內建回充按鈕)。"""
        _LOGGER.info("發送返回充電座指令 (switch_charge = True)")
        await self.coordinator.async_send_commands(
            [
                {"code": DP_CHARGE_SWITCH_NEW, "value": True},
                {"code": DP_CHARGE_SWITCH_OLD, "value": True},
                {"code": "3", "value": True},
            ]
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """開機/啟動。"""
        await self.async_start()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """關機/回充。"""
        await self.async_return_to_base()

    async def async_clean_spot(self, **kwargs: Any) -> None:
        """局部/定點清掃。"""
        await self.coordinator.async_send_commands(
            [
                {"code": DP_CLEAN_MODE, "value": "spot"},
                {"code": DP_CLEAN_SWITCH_NEW, "value": True},
                {"code": "1", "value": True},
            ]
        )

    async def async_locate(self, **kwargs: Any) -> None:
        """尋找吸塵器 (嗶嗶叫)。"""
        await self.coordinator.async_send_commands(
            [
                {"code": DP_FIND_DEVICE, "value": True},
                {"code": "149", "value": True},
            ]
        )

    # ---------- 額外狀態屬性 (供 Lovelace 卡片讀取) ----------

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """額外屬性。"""
        attrs: dict[str, Any] = {}
        if self.battery_level is not None:
            attrs["battery_level"] = self.battery_level
            attrs["battery"] = self.battery_level
            attrs["battery_percentage"] = self.battery_level
            attrs["battery_icon"] = self.battery_icon

        if (work_status := self.coordinator.get_dp(DP_WORK_STATUS, "5")) is not None:
            attrs["work_status"] = work_status

        if (clean_time := self.coordinator.get_dp("clean_time_min", "6")) is not None:
            attrs["clean_time"] = clean_time

        if (clean_area := self.coordinator.get_dp("clean_area_m2", "7")) is not None:
            attrs["clean_area"] = clean_area

        if (clean_mode := self.coordinator.get_dp(DP_CLEAN_MODE, "132")) is not None:
            attrs["clean_mode"] = clean_mode

        if (water_temp := self.coordinator.get_dp("water_temp", "135")) is not None:
            attrs["water_temp"] = water_temp

        attrs["raw_dps"] = self.coordinator.data
        return attrs

    # ---------- 擴充指令相容 ----------

    async def async_send_command(
        self,
        command: str,
        params: list[Any] | dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """自訂指令接收器。"""
        cmd = command.lower()

        if cmd == "start":
            await self.async_start()
            return
        if cmd == "stop":
            await self.async_stop()
            return
        if cmd == "pause":
            await self.async_pause()
            return
        if cmd in ("return_to_base", "dock", "home"):
            await self.async_return_to_base()
            return
        if cmd in ("locate", "find_device", "find"):
            await self.async_locate()
            return

        if cmd == "set_dp":
            if isinstance(params, dict):
                commands = [{"code": k, "value": v} for k, v in params.items()]
            elif isinstance(params, list) and len(params) == 2:
                commands = [{"code": params[0], "value": params[1]}]
            else:
                raise ValueError("set_dp 需傳 dict 或 [code, value]")
            await self.coordinator.async_send_commands(commands)
            return

        raise ValueError(f"未知指令: {command}")


# ---- 內部輔助方法 ----

def _to_activity(name: str) -> VacuumActivity:
    """字串轉 VacuumActivity 列舉。"""
    try:
        return VacuumActivity(name)
    except ValueError:
        return VacuumActivity.IDLE


def _is_full(coordinator: UwantVacuumCoordinator) -> bool:
    """判斷電量是否已滿。"""
    level = coordinator.get_dp(DP_BATTERY_NEW, DP_BATTERY_OLD, "8")
    return isinstance(level, (int, float)) and level >= 100
