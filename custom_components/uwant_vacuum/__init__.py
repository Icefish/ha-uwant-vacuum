"""The UWANT Vacuum (Tuya) integration.

支援兩種認證模式:

1. **帳號密碼模式**(建議)— 用 UWANT app 的帳密直接登入,
   搭配 APK 內建的 Tuya AppKey/Secret,不需要 iot.tuya.com 開發者帳號。
2. **開發者憑證模式** — 用 iot.tuya.com 的 Access ID / Access Secret。
"""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_ACCESS_ID,
    CONF_ACCESS_SECRET,
    CONF_COUNTRY_CODE,
    CONF_LOCAL_IP,
    CONF_LOCAL_KEY,
    CONF_PROTOCOL_VERSION,
    CONF_REGION,
    DEFAULT_PROTOCOL_VERSION,
    DOMAIN,
    REGION_ENDPOINTS,
    UWANT_APP_KEY,
    UWANT_APP_SECRET,
)
from .coordinator import UwantVacuumCoordinator
from .local_client import LocalTuyaAuthError, LocalTuyaClient, LocalTuyaError
from .tuya_client import TuyaAuthError, TuyaClient, TuyaError

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.VACUUM, Platform.SENSOR, Platform.SELECT, Platform.BUTTON]

# 相容舊版 Python 的別名寫法(不用 `type` 關鍵字,需 Python 3.12+)
UwantConfigEntry = ConfigEntry

SET_DP_SCHEMA = vol.Schema(
    {
        vol.Required("code"): cv.string,
        vol.Required("value"): vol.Any(cv.string, int, float, bool),
        vol.Optional("device_id"): cv.string,
    }
)


async def _build_client(
    hass: HomeAssistant, entry: UwantConfigEntry
) -> TuyaClient | LocalTuyaClient:
    """依設定建立並驗證客戶端。

    支援三種模式:

    1. **本地區網**(推薦)— 用 local_key 走 TCP 6668,完全不經雲端
    2. 帳號密碼 — 用 UWANT app 帳密 + 內建 AppKey
    3. 開發者憑證 — iot.tuya.com 的 Access ID / Secret
    """
    data = entry.data
    session = async_get_clientsession(hass)

    # ----- 模式 0:本地區網(推薦)-----
    if data.get(CONF_LOCAL_KEY):
        client = LocalTuyaClient(
            hass,
            data["device_id"],
            data[CONF_LOCAL_KEY],
            data[CONF_LOCAL_IP],
            version=str(data.get(CONF_PROTOCOL_VERSION, DEFAULT_PROTOCOL_VERSION)),
        )
        await client.async_test_connection()
        return client

    username = data.get(CONF_USERNAME)
    if username:
        # 模式 1:帳號密碼(使用 UWANT 內建 AppKey/Secret)
        client = TuyaClient(
            endpoint=REGION_ENDPOINTS[data[CONF_REGION]],
            access_id=UWANT_APP_KEY,
            access_secret=UWANT_APP_SECRET,
            session=session,
        )
        await client.login_with_password(
            username,
            data[CONF_PASSWORD],
            country_code=data.get(CONF_COUNTRY_CODE, "86"),
        )
    else:
        # 模式 2:開發者憑證
        client = TuyaClient(
            endpoint=REGION_ENDPOINTS[data[CONF_REGION]],
            access_id=data[CONF_ACCESS_ID],
            access_secret=data[CONF_ACCESS_SECRET],
            session=session,
        )
        await client._ensure_token()  # noqa: SLF001

    return client


async def async_setup_entry(hass: HomeAssistant, entry: UwantConfigEntry) -> bool:
    """Set up UWANT Vacuum from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    try:
        client = await _build_client(hass, entry)
    except (TuyaAuthError, LocalTuyaAuthError) as err:
        raise ConfigEntryAuthFailed(f"認證失敗: {err}") from err
    except Exception as err:
        raise ConfigEntryNotReady(f"無法連線到裝置: {err}") from err

    device_id = entry.data["device_id"]
    coordinator = UwantVacuumCoordinator(
        hass=hass,
        client=client,
        device_id=device_id,
        device_name=entry.data.get(CONF_NAME) or f"UWANT {device_id[-6:]}",
    )
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        await client.close()
        raise ConfigEntryNotReady(f"無法取得設備狀態: {err}") from err

    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if not hass.services.has_service(DOMAIN, "set_dp"):

        async def handle_set_dp(call: ServiceCall) -> None:
            target_device_id = call.data.get("device_id")
            for coord in hass.data[DOMAIN].values():
                if target_device_id and coord.device_id != target_device_id:
                    continue
                await coord.async_send_command(
                    call.data["code"], call.data["value"]
                )

        hass.services.async_register(
            DOMAIN, "set_dp", handle_set_dp, schema=SET_DP_SCHEMA
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: UwantConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: UwantVacuumCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()
    if not hass.data[DOMAIN] and hass.services.has_service(DOMAIN, "set_dp"):
        hass.services.async_remove(DOMAIN, "set_dp")
    return unload_ok
