"""DataUpdateCoordinator for UWANT Vacuum.

每 DEFAULT_SCAN_INTERVAL 秒輪詢一次 Tuya /status 端點,並把 DP 陣列整理成 dict。
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .tuya_client import TuyaError

_LOGGER = logging.getLogger(__name__)


class UwantVacuumCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """管理 UWANT 設備狀態。"""

    def __init__(
        self,
        *,
        hass: HomeAssistant,
        client,
        device_id: str,
        device_name: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}:{device_name}",
            update_interval=None,  # 用秒數,在下面指定
        )
        # HA 2024+ update_interval 接受 timedelta
        from datetime import timedelta

        self.update_interval = timedelta(seconds=DEFAULT_SCAN_INTERVAL)
        self.client = client
        self.device_id = device_id
        self.device_name = device_name

        # 最新狀態(DP dict): {"clean_switch": True, "battery": 80, ...}
        self.data: dict[str, Any] = {}

    async def _async_update_data(self) -> dict[str, Any]:
        """抓取設備狀態。"""
        try:
            if self.client.is_user_token:
                status_list = await self.client.get_device_status_u(self.device_id)
            else:
                status_list = await self.client.get_device_status(self.device_id)
        except TuyaError as err:
            raise UpdateFailed(f"Tuya error: {err}") from err

        result: dict[str, Any] = {}
        for dp in status_list:
            code = dp.get("code")
            value = dp.get("value")
            if code is not None:
                result[str(code)] = value
        return result

    async def async_shutdown(self) -> None:
        """關閉資源。"""
        await super().async_shutdown()
        await self.client.close()

    # ----- 指令快捷方法 -----
    async def async_send_command(self, code: str, value: Any) -> None:
        """發送 DP 指令,成功後立即觸發 refresh。"""
        if self.client.is_user_token:
            await self.client.send_command_u(self.device_id, code, value)
        else:
            await self.client.send_command(self.device_id, code, value)
        await self.async_request_refresh()

    async def async_send_commands(self, commands: list[dict[str, Any]]) -> None:
        """批次發送 DP 指令。"""
        if self.client.is_user_token:
            await self.client.send_commands_u(self.device_id, commands)
        else:
            await self.client.send_commands(self.device_id, commands)
        await self.async_request_refresh()

    # ----- 便利取值 -----
    def get_dp(self, *codes: str, default: Any = None) -> Any:
        """依序嘗試多個 DP 名,回傳第一個存在的值。"""
        for code in codes:
            if code in self.data:
                return self.data[code]
        return default
