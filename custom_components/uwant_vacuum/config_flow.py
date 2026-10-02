"""Config flow for UWANT Vacuum (Tuya) integration.

兩種認證模式:

* **帳號密碼**(預設)— 直接用 UWANT app 帳密,內建 AppKey/Secret
* **開發者憑證** — iot.tuya.com 的 Access ID / Access Secret
"""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_NAME, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_ACCESS_ID,
    CONF_ACCESS_SECRET,
    CONF_COUNTRY_CODE,
    CONF_DEVICE_ID,
    CONF_LOCAL_IP,
    CONF_LOCAL_KEY,
    CONF_PROTOCOL_VERSION,
    CONF_REGION,
    DEFAULT_LOCAL_PORT,
    DEFAULT_PROTOCOL_VERSION,
    DOMAIN,
    PROTOCOL_VERSIONS,
    REGION_ENDPOINTS,
    UWANT_APP_KEY,
    UWANT_APP_SECRET,
)
from .local_client import LocalTuyaAuthError, LocalTuyaClient, LocalTuyaError
from .tuya_client import TuyaAuthError, TuyaClient, TuyaError

_LOGGER = logging.getLogger(__name__)

CONF_AUTH_MODE = "auth_mode"
MODE_LOCAL = "local"          # 本地區網(推薦)
MODE_ACCOUNT = "account"      # 帳號密碼
MODE_DEVELOPER = "developer"  # 開發者憑證

REGION_LABELS = {
    "china": "China 中國",
    "us": "United States 美國",
    "europe": "Europe 歐洲",
    "india": "India 印度",
    "singapore": "Singapore 東南亞",
    "japan": "Japan 日本",
}


class UwantVacuumConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for UWANT Vacuum."""

    VERSION = 1

    def __init__(self) -> None:
        self._creds: dict[str, Any] = {}
        self._devices: list[dict[str, Any]] = []

    # ---------------- Step 1: 選擇認證方式 ----------------

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            mode = user_input[CONF_AUTH_MODE]
            if mode == MODE_LOCAL:
                return await self.async_step_local()
            if mode == MODE_ACCOUNT:
                return await self.async_step_account()
            return await self.async_step_developer()

        schema = vol.Schema(
            {vol.Required(CONF_AUTH_MODE, default=MODE_LOCAL): vol.In(
                {
                    MODE_LOCAL: "本地區網(推薦,不需雲端)",
                    MODE_ACCOUNT: "UWANT 帳號密碼",
                    MODE_DEVELOPER: "Tuya 開發者憑證",
                }
            )}
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    # ---------------- Step 2c: 本地區網(推薦) ----------------

    async def async_step_local(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """本地連線設定:device_id + local_key + IP + 協議版本。

        local_key 取得方式請參考 README.md 的說明。
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            device_id = user_input[CONF_DEVICE_ID].strip()
            local_key = user_input[CONF_LOCAL_KEY].strip()
            address = user_input[CONF_LOCAL_IP].strip()
            version = str(user_input.get(CONF_PROTOCOL_VERSION, DEFAULT_PROTOCOL_VERSION))

            client = LocalTuyaClient(
                self.hass, device_id, local_key, address, version=version
            )
            try:
                await client.async_test_connection()
            except LocalTuyaAuthError as err:
                _LOGGER.warning("本地驗證失敗: %s", err)
                errors["base"] = "invalid_auth"
            except LocalTuyaError as err:
                _LOGGER.warning("本地連線失敗: %s", err)
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("本地連線未預期錯誤")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(device_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME) or f"UWANT {device_id[-6:]}",
                    data={
                        CONF_AUTH_MODE: MODE_LOCAL,
                        CONF_DEVICE_ID: device_id,
                        CONF_LOCAL_KEY: local_key,
                        CONF_LOCAL_IP: address,
                        CONF_PROTOCOL_VERSION: version,
                        CONF_NAME: user_input.get(CONF_NAME, ""),
                    },
                )
            finally:
                await client.close()

        schema = vol.Schema(
            {
                vol.Required(CONF_DEVICE_ID): str,
                vol.Required(CONF_LOCAL_KEY): str,
                vol.Required(CONF_LOCAL_IP): str,
                vol.Required(
                    CONF_PROTOCOL_VERSION, default=DEFAULT_PROTOCOL_VERSION
                ): vol.In(list(PROTOCOL_VERSIONS)),
                vol.Optional(CONF_NAME, default=""): str,
            }
        )
        return self.async_show_form(
            step_id="local",
            data_schema=schema,
            errors=errors,
            description_placeholders={"port": str(DEFAULT_LOCAL_PORT)},
        )

    # ---------------- Step 2a: 帳號密碼 ----------------

    async def async_step_account(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            ok, err, devices = await self._try_account(user_input)
            if not ok:
                errors["base"] = err
            else:
                self._creds = user_input
                self._devices = devices
                return await self.async_step_device()

        schema = vol.Schema(
            {
                vol.Required(CONF_REGION, default="china"): vol.In(REGION_LABELS),
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_COUNTRY_CODE, default="86"): str,
            }
        )
        return self.async_show_form(
            step_id="account",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "appkey": UWANT_APP_KEY,
            },
        )

    async def _try_account(
        self, data: dict[str, Any]
    ) -> tuple[bool, str, list[dict[str, Any]]]:
        """嘗試用帳號密碼登入並列出設備。"""
        client = TuyaClient(
            endpoint=REGION_ENDPOINTS[data[CONF_REGION]],
            access_id=UWANT_APP_KEY,
            access_secret=UWANT_APP_SECRET,
            session=async_get_clientsession(self.hass),
        )
        try:
            result = await client.login_with_password(
                data[CONF_USERNAME],
                data[CONF_PASSWORD],
                country_code=data.get(CONF_COUNTRY_CODE, "86"),
            )
            _LOGGER.info("Login OK via %s", result.get("_login_path"))
            devices = await client.list_devices_by_user(result.get("uid"))
            return True, "", devices
        except TuyaAuthError as err:
            _LOGGER.warning("Account login failed: %s", err)
            return False, "invalid_auth", []
        except TuyaError as err:
            _LOGGER.warning("Account login tuya error: %s", err)
            return False, "cannot_connect", []
        except Exception as err:  # noqa: BLE001
            _LOGGER.exception("Unexpected error")
            return False, "unknown", []
        finally:
            await client.close()

    # ---------------- Step 2b: 開發者憑證 ----------------

    async def async_step_developer(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            client = TuyaClient(
                endpoint=REGION_ENDPOINTS[user_input[CONF_REGION]],
                access_id=user_input[CONF_ACCESS_ID],
                access_secret=user_input[CONF_ACCESS_SECRET],
                session=async_get_clientsession(self.hass),
            )
            try:
                await client._ensure_token()  # noqa: SLF001
                devices = await client.list_devices()
                self._creds = user_input
                self._devices = devices
                return await self.async_step_device()
            except TuyaAuthError:
                errors["base"] = "invalid_auth"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Developer credential error")
                errors["base"] = "cannot_connect"
            finally:
                await client.close()

        schema = vol.Schema(
            {
                vol.Required(CONF_REGION, default="china"): vol.In(REGION_LABELS),
                vol.Required(CONF_ACCESS_ID): str,
                vol.Required(CONF_ACCESS_SECRET): str,
            }
        )
        return self.async_show_form(
            step_id="developer", data_schema=schema, errors=errors
        )

    # ---------------- Step 3: 選設備 ----------------

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            device_id = user_input[CONF_DEVICE_ID]
            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input.get(CONF_NAME) or f"UWANT {device_id[-6:]}",
                data={**self._creds, CONF_DEVICE_ID: device_id},
            )

        options: dict[str, str] = {}
        for d in self._devices:
            did = d.get("id") or d.get("device_id")
            if not did:
                continue
            name = d.get("name") or d.get("product_name") or did
            options[str(did)] = f"{name}"

        if not options:
            return self.async_show_form(
                step_id="device",
                data_schema=vol.Schema({}),
                errors={"base": "no_device_found"},
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_DEVICE_ID): vol.In(options),
                vol.Optional(CONF_NAME, default=""): str,
            }
        )
        return self.async_show_form(step_id="device", data_schema=schema, errors=errors)

    # ---------------- 重新設定 ----------------

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        if user_input is not None:
            return self.async_update_reload_and_abort(entry, data_updates=user_input)
        return self.async_show_form(
            step_id="reconfigure_confirm", data_schema=vol.Schema({})
        )

    async def async_step_reconfigure_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return await self.async_step_user()
