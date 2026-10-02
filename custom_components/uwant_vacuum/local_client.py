"""本地(區域網路)Tuya 客戶端 — 用 tinytuya 直接走 TCP 6668。

為什麼需要這個?
───────────────
原本的 ``TuyaClient`` 走雲端 HTTP API,但 Tuya 在 SDK 5.x 用白盒密碼學
保護行動 API 的簽章，純外部無法直接計算。

後來發現:**只要拿到裝置的 local_key,就能走區域網路直接控制**,
完全不需要雲端。這個客戶端就是那條路。

設計
────
介面刻意與 ``TuyaClient`` 一致(``get_device_status`` / ``send_command`` /
``close``),所以 ``coordinator.py`` 完全不需要修改。

差別在於:
* 雲端客戶端回傳的 DP 是 ``code`` 名稱(如 ``switch_go``)
* 本地客戶端拿到的是**數字 DP ID**(如 ``"1"``)
  → 這裡會用 ``U300_DP_ID_TO_CODE`` 轉成 code 名稱,讓上層無感

tinytuya 是**同步阻塞**的函式庫,所以所有呼叫都丢到 executor 執行,
避免擋住 Home Assistant 的事件迴圈。
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - 只給型別檢查用
    from homeassistant.core import HomeAssistant

from .const import (
    DEFAULT_LOCAL_PORT,
    DEFAULT_PROTOCOL_VERSION,
    LOCAL_SOCKET_TIMEOUT,
    U300_CODE_TO_DP_ID,
    U300_DP_ID_TO_CODE,
)

_LOGGER = logging.getLogger(__name__)

# tinytuya 回傳錯誤時,錯誤訊息會放在這些 key
_ERROR_KEYS = ("Error", "Err")


class LocalTuyaError(Exception):
    """本地連線或通訊錯誤。"""


class LocalTuyaAuthError(LocalTuyaError):
    """local_key 或協議版本錯誤。"""


class LocalTuyaClient:
    """用 tinytuya 走區域網路的 Tuya 客戶端。

    Parameters
    ----------
    hass:
        Home Assistant 實例(用來取得 executor)。
    device_id:
        Tuya 裝置 ID(例如 ``bf1234567890abcdef12``)。
    local_key:
        裝置的 local_key(16 字元)。
    address:
        裝置的區網 IP。
    version:
        協議版本,預設 ``3.3``(U300 實測值)。
    port:
        TCP 埠,預設 6668。
    """

    # 與 TuyaClient 介面一致:本地模式永遠不是「使用者 token」
    is_user_token: bool = False

    def __init__(
        self,
        hass: "HomeAssistant",
        device_id: str,
        local_key: str,
        address: str,
        *,
        version: str = DEFAULT_PROTOCOL_VERSION,
        port: int = DEFAULT_LOCAL_PORT,
    ) -> None:
        self.hass = hass
        self.device_id = device_id
        self.address = address
        self.version = float(version)
        self.port = port
        self._local_key = local_key
        self._device: Any | None = None

    # --------------------------- 內部工具 ---------------------------

    def _get_device(self) -> Any:
        """延遲建立 tinytuya 物件(避免在事件迴圈中匯入)。"""
        if self._device is None:
            import tinytuya  # 延遲匯入:HA 載入時 tinytuya 還不一定要在

            self._device = tinytuya.Device(
                self.device_id,
                self.address,
                self._local_key,
                version=self.version,
                port=self.port,
            )
            self._device.set_socketTimeout(LOCAL_SOCKET_TIMEOUT)
        return self._device

    @staticmethod
    def _check_error(result: Any) -> None:
        """tinytuya 出錯時是「回傳 dict」而不是丟例外,這裡統一轉成例外。"""
        if not isinstance(result, dict):
            return
        if "Error" in result:
            err = str(result.get("Error", ""))
            err_code = str(result.get("Err", ""))
            # 914 = 金鑰/版本錯誤
            if err_code == "914" or "key" in err.lower() or "version" in err.lower():
                raise LocalTuyaAuthError(
                    f"local_key 或協議版本不正確({err} / {err_code})"
                )
            raise LocalTuyaError(f"{err}({err_code})")

    async def _call(self, func_name: str, *args: Any) -> Any:
        """在 executor 中呼叫 tinytuya 的同步方法。"""

        def _run() -> Any:
            device = self._get_device()
            method = getattr(device, func_name, None)
            if method is None:
                raise LocalTuyaError(f"tinytuya 物件沒有 {func_name} 方法")
            return method(*args)

        try:
            result = await self.hass.async_add_executor_job(_run)
        except LocalTuyaError:
            raise
        except Exception as err:  # noqa: BLE001
            raise LocalTuyaError(f"本地連線失敗: {err}") from err

        self._check_error(result)
        return result

    # --------------------------- 主要 API ---------------------------

    async def async_test_connection(self) -> dict[str, Any]:
        """測試連線並回傳原始 DP dict(給 config_flow 驗證用)。"""
        result = await self._call("status")
        return result.get("dps", {}) if isinstance(result, dict) else {}

    async def get_device_status(
        self, device_id: str | None = None
    ) -> list[dict[str, Any]]:
        """取得裝置所有 DP,回傳 ``[{code, value}, ...]``。

        注意:回傳的 ``code`` 已經從數字 DP ID 轉成可讀名稱
        (例如 ``"1"`` → ``"switch_go"``),與雲端模式一致。
        """
        result = await self._call("status")
        dps: dict[str, Any] = result.get("dps", {}) if isinstance(result, dict) else {}

        status_list: list[dict[str, Any]] = []
        for dp_id, value in dps.items():
            code = U300_DP_ID_TO_CODE.get(str(dp_id), str(dp_id))
            status_list.append({"code": code, "value": value})
        return status_list

    async def send_command(self, device_id: str, code: str, value: Any) -> bool:
        """發送單一 DP 指令(code 名稱會轉成數字 DP ID)。"""
        return await self.send_commands(device_id, [{"code": code, "value": value}])

    async def send_commands(
        self, device_id: str, commands: list[dict[str, Any]]
    ) -> bool:
        """發送多個 DP 指令,回傳是否至少送出一個。

        無法對應到 DP ID 的 code 會被**略過**(例如舊 schema 的
        ``clean_switch``/``charge_switch``,在 U300 上不存在)。
        """
        sent = 0
        for cmd in commands:
            code = str(cmd.get("code", ""))
            dp_id = U300_CODE_TO_DP_ID.get(code)

            # 若 code 本身已經是數字 DP ID,直接使用
            if dp_id is None and code.isdigit():
                dp_id = code

            if dp_id is None:
                _LOGGER.debug("略過未知的 DP code: %s", code)
                continue

            await self._call("set_value", int(dp_id), cmd.get("value"))
            sent += 1

        if sent == 0:
            raise LocalTuyaError(
                f"沒有任何可送出的 DP 指令:{[c.get('code') for c in commands]}"
            )
        return True

    async def close(self) -> None:
        """關閉連線。"""
        if self._device is None:
            return

        def _close() -> None:
            try:
                self._device.close()
            except Exception:  # noqa: BLE001
                pass

        try:
            await self.hass.async_add_executor_job(_close)
        finally:
            self._device = None

    # 相容別名:coordinator 在 user-token 模式會呼叫 *_u 系列
    async def get_device_status_u(self, device_id: str) -> list[dict[str, Any]]:
        return await self.get_device_status(device_id)

    async def send_command_u(self, device_id: str, code: str, value: Any) -> bool:
        return await self.send_command(device_id, code, value)

    async def send_commands_u(
        self, device_id: str, commands: list[dict[str, Any]]
    ) -> bool:
        return await self.send_commands(device_id, commands)


async def async_discover_device(
    hass: "HomeAssistant",
    device_id: str,
    local_key: str,
    address: str,
    *,
    version: str = DEFAULT_PROTOCOL_VERSION,
    port: int = DEFAULT_LOCAL_PORT,
) -> dict[str, Any]:
    """建立客戶端、測試連線、回傳 DP dict(供 config_flow 使用)。"""
    client = LocalTuyaClient(
        hass, device_id, local_key, address, version=version, port=port
    )
    try:
        return await client.async_test_connection()
    finally:
        await client.close()
