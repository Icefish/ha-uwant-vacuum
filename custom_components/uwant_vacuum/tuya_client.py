"""Tuya OpenAPI async client.

實作 HMAC-SHA256 簽章、token 管理、設備 DP 指令下發與狀態查詢。
API 規範參考 https://developer.tuya.com/en/docs/cloud/
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import ssl
import time
from typing import Any
from urllib.parse import urlencode

import aiohttp

_LOGGER = logging.getLogger(__name__)

# 一次刷新上限
TOKEN_REFRESH_SKEW = 60 * 60  # 提前 60 分鐘重新取 token

# 找不到根憑證時可退回使用的系統 CA bundle
_SYSTEM_CA_CANDIDATES = (
    "/etc/ssl/cert.pem",                       # macOS / LibreSSL
    "/etc/pki/tls/certs/ca-bundle.crt",        # RHEL/CentOS
    "/etc/ssl/certs/ca-certificates.crt",      # Debian/Ubuntu
)


def make_ssl_context() -> ssl.SSLContext:
    """建立 SSL context,必要時補上系統 CA bundle。

    macOS 上 python.org 版本的 Python,若安裝後沒執行過
    ``Install Certificates.command``,OpenSSL 的預設信任庫會是**空的**
    (0 個根憑證)。此時所有 HTTPS 連線都會失敗並出現::

        [SSL: CERTIFICATE_VERIFY_FAILED] self-signed certificate in
        certificate chain

    這個錯誤訊息很容易誤導成「被中間人攔截」,但其實只是本機沒有憑證。
    這裡偵測到信任庫為空時,自動退回載入系統的 CA bundle。
    """
    ctx = ssl.create_default_context()
    if ctx.cert_store_stats().get("x509_ca", 0) > 0:
        return ctx

    for candidate in _SYSTEM_CA_CANDIDATES:
        if not os.path.exists(candidate):
            continue
        try:
            ctx.load_verify_locations(cafile=candidate)
        except (ssl.SSLError, OSError):
            continue
        if ctx.cert_store_stats().get("x509_ca", 0) > 0:
            _LOGGER.debug("SSL 預設信任庫為空,已改用系統 CA bundle %s", candidate)
            return ctx

    # 找不到替代品就維持原狀,讓錯誤自然浮現
    _LOGGER.warning(
        "SSL 信任庫中沒有任何根憑證,且找不到系統 CA bundle。"
        "HTTPS 連線將會失敗。macOS 可執行 "
        "/Applications/Python*/Install\\ Certificates.command 修正。"
    )
    return ctx


class TuyaError(Exception):
    """Tuya API 回應錯誤。"""

    def __init__(self, code: int, msg: str, *, request_id: str | None = None) -> None:
        super().__init__(f"[{code}] {msg}" + (f" (req_id={request_id})" if request_id else ""))
        self.code = code
        self.msg = msg
        self.request_id = request_id


class TuyaAuthError(TuyaError):
    """認證錯誤(權杖無效、權限不足等)。"""


class TuyaClient:
    """非同步 Tuya OpenAPI 客戶端。

    Parameters
    ----------
    endpoint:
        區域端點 URL,例如 ``https://openapi.tuyaeu.com``。
    access_id:
        Tuya IoT 平台 Access ID (client_id)。
    access_secret:
        Tuya IoT 平台 Access Secret (client_secret)。
    session:
        共用的 ``aiohttp.ClientSession``(建議傳入以利連線池)。
    """

    def __init__(
        self,
        endpoint: str,
        access_id: str,
        access_secret: str,
        *,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        # 去掉尾斜線
        self.endpoint = endpoint.rstrip("/")
        self.access_id = access_id
        self.access_secret = access_secret
        self._session = session
        self._own_session = session is None

        self._token: str | None = None
        self._token_expire_at: float = 0.0
        self._lock = asyncio.Lock()

        # 若使用「帳號密碼」模式,記住憑證以便 token 過期時自動重新登入。
        # 元素為 (username, password, country_code) 或 None(IoT 平台模式)。
        self._login_creds: tuple[str, str, str] | None = None

        # True 表示目前的 token 是「使用者 token」,
        # 設備 API 需改走 *_u 系列方法(不同路徑)。
        self.is_user_token: bool = False

    # --------------------------- HTTP 包裝 ---------------------------

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            # 註:HA 會傳入自己的 session(已具備完整憑證),不會走到這裡。
            # 這裡只服務獨立執行(probe_login.py 等)的情境。
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=20),
                headers={"User-Agent": "ha-uwant-vacuum/1.0"},
                connector=aiohttp.TCPConnector(ssl=make_ssl_context()),
            )
        return self._session

    async def close(self) -> None:
        if self._own_session and self._session is not None:
            await self._session.close()
            self._session = None

    # --------------------------- 簽章 ---------------------------

    def _calc_sign(
        self,
        *,
        method: str,
        path: str,
        query: dict[str, Any] | None = None,
        body: Any | None = None,
        access_token: str | None = None,
        t: int | None = None,
    ) -> tuple[str, int]:
        """計算簽章,回傳 ``(sign, t)``。

        這是 Tuya 官方的簽章演算法,逐字對照官方 SDK 實作
        (``tuya-connector-python`` 的 ``TuyaOpenAPI._calculate_sign``)::

            StringToSign = METHOD + "\\n"
                         + sha256(body) + "\\n"
                         + "\\n"              # header 區段固定為空
                         + path + "?" + 依 key 排序的 query

            message = client_id [+ access_token] + str(t) + StringToSign
            sign    = upper(HMAC-SHA256(message, client_secret))

        重點(與常見誤解不同之處):

        * ``client_id``/``access_token``/``t`` 是**前綴**,串在 StringToSign 之前。
        * header 區段固定是**空的一行**,不是把 headers 排序列進去。
        * **沒有** nonce,也**沒有** ``Signature-Header`` 這種標頭。
        * query 不做事 URL 編碼,以 ``&`` 串接。

        ``t`` 為 13 位毫秒時間戳;未提供時自動產生。
        """
        body_str = "" if not body else json.dumps(body)

        str_to_sign = method.upper() + "\n"
        str_to_sign += hashlib.sha256(body_str.encode("utf-8")).hexdigest() + "\n"
        # header 區段:官方實作固定留空,只貢獻一個換行
        str_to_sign += "\n"
        str_to_sign += path
        if query:
            str_to_sign += "?" + "&".join(
                f"{k}={query[k]}" for k in sorted(query)
            )

        if t is None:
            t = int(time.time() * 1000)

        message = self.access_id
        if access_token:
            message += access_token
        message += str(t) + str_to_sign

        sign = hmac.new(
            self.access_secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest().upper()

        return sign, t

    def _build_headers(
        self,
        *,
        path: str,
        method: str,
        body: Any | None,
        query: dict[str, Any] | None,
        with_token: bool,
    ) -> tuple[dict[str, str], str]:
        """建立請求 headers(含簽章),回傳 ``(headers, sign)``。

        送出的 headers 與官方 SDK 一致:client_id / sign / sign_method / t /
        access_token / lang。``access_token`` 即使為空也會送出(官方行為)。
        """
        access_token = self._token if with_token else None

        sign, t = self._calc_sign(
            method=method,
            path=path,
            query=query,
            body=body,
            access_token=access_token,
        )

        headers: dict[str, str] = {
            "client_id": self.access_id,
            "sign": sign,
            "sign_method": "HMAC-SHA256",
            "t": str(t),
            "access_token": access_token or "",
            "lang": "en",
        }

        # Content-Type 只在有 body 時放
        if body:
            headers["Content-Type"] = "application/json"

        return headers, sign

    # --------------------------- 使用者帳密登入 ---------------------------

    async def login_with_password(
        self,
        username: str,
        password: str,
        *,
        country_code: str = "86",
        path_candidates: tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        """用 UWANT/Tuya 帳號密碼登入,取得使用者 access_token。

        密碼需先做 MD5(小寫 hex)。SDK 5.x 將 API 路徑加密,
        因此這裡會依序嘗試多組候選路徑,直到有一組回傳成功。

        Returns
        -------
        dict
            使用者 token 結果,含 ``access_token`` / ``uid`` 等欄位。
        """
        import hashlib as _hashlib

        pwd_md5 = _hashlib.md5(password.encode("utf-8")).hexdigest()

        # 記住憑證,供 token 過期時自動重新登入
        self._login_creds = (username, password, country_code)

        if path_candidates is None:
            from .const import LOGIN_PATH_CANDIDATES

            path_candidates = LOGIN_PATH_CANDIDATES

        last_error: Exception | None = None
        for template in path_candidates:
            path = template.format(username=username, password=pwd_md5)
            try:
                headers, _ = self._build_headers(
                    path=path,
                    method="GET",
                    body=None,
                    query=None,  # query 已內嵌在 path
                    with_token=False,
                )
                headers["countryCode"] = country_code
                headers["Content-Type"] = "application/json"

                session = await self._get_session()
                async with session.get(self.endpoint + path, headers=headers) as resp:
                    payload = await resp.json(content_type=None)

                if payload.get("success"):
                    result = payload.get("result", {})
                    self._token = result.get("access_token")
                    self._token_expire_at = time.time() + int(
                        result.get("expire_time", 7200)
                    )
                    self.is_user_token = True
                    _LOGGER.debug("Login succeeded via %s", template)
                    result["_login_path"] = template
                    return result

                code = payload.get("code", 0)
                last_error = TuyaError(code, payload.get("msg", "login failed"))
                _LOGGER.debug("Login path %s failed: %s", template, last_error)
            except (aiohttp.ClientError, ValueError) as err:
                last_error = err
                _LOGGER.debug("Login path %s error: %s", template, err)

        raise TuyaAuthError(
            getattr(last_error, "code", -1),
            f"所有候選登入路徑皆失敗。最後錯誤: {last_error}",
        )

    async def list_devices_by_user(
        self, uid: str | None = None
    ) -> list[dict[str, Any]]:
        """以使用者 token 列出該帳號下的設備。"""
        from .const import USER_DEVICE_LIST_CANDIDATES

        templates = USER_DEVICE_LIST_CANDIDATES
        if uid:
            templates = tuple(t.format(uid=uid) for t in templates)
        else:
            templates = tuple(t.format(uid="") for t in templates)

        last_error: Exception | None = None
        for path in templates:
            path = path.replace("//devices", "/devices")
            try:
                payload = await self.request("GET", path)
                result = payload.get("result", {})
                devices = result.get("devices", result) if isinstance(result, dict) else result
                if isinstance(devices, list):
                    return devices
                if isinstance(devices, dict):
                    return [devices]
            except TuyaError as err:
                last_error = err
                _LOGGER.debug("list devices via %s failed: %s", path, err)
        raise TuyaError(-1, f"無法列出設備: {last_error}")

    # --------------------------- Token 管理 ---------------------------

    async def _ensure_token(self) -> str:
        """確保 token 有效,必要時重新取得。"""
        async with self._lock:
            if self._token and time.time() < self._token_expire_at - TOKEN_REFRESH_SKEW:
                return self._token

            # 若是使用者帳密登入模式,改為重新登入
            if self._login_creds:
                username, password, country_code = self._login_creds
                _LOGGER.debug("User token expired, re-logging in as %s", username)
                result = await self.login_with_password(
                    username, password, country_code=country_code
                )
                assert self._token is not None
                return self._token

            path = "/v1.0/token"
            query = {"grant_type": "1"}
            headers, _ = self._build_headers(
                path=path, method="GET", body=None, query=query, with_token=False
            )

            session = await self._get_session()
            url = self.endpoint + path + "?" + urlencode(sorted(query.items()))
            async with session.get(url, headers=headers) as resp:
                payload = await resp.json()
            if not payload.get("success"):
                raise TuyaAuthError(
                    payload.get("code", -1),
                    payload.get("msg", "fetch token failed"),
                    request_id=resp.headers.get("X-Tuya-Request-Id"),
                )

            result = payload["result"]
            self._token = result["access_token"]
            self._token_expire_at = time.time() + int(result.get("expire_time", 7200))
            return self._token

    # --------------------------- 通用 request ---------------------------

    async def request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        body: Any | None = None,
        with_token: bool = True,
        retries: int = 2,
    ) -> dict[str, Any]:
        """通用 API 呼叫。

        失敗會自動重試一次(token 過期時會重新取)。
        """
        last_exc: Exception | None = None
        for attempt in range(retries + 1):
            try:
                if with_token:
                    await self._ensure_token()
                headers, _ = self._build_headers(
                    path=path,
                    method=method,
                    body=body,
                    query=query,
                    with_token=with_token,
                )
                session = await self._get_session()
                url = self.endpoint + path
                if query:
                    # 必須與簽章時的排序一致,否則簽章會對不上
                    url += "?" + urlencode(sorted(query.items()))
                # 必須與簽章時用的 json.dumps(body) 完全一致(含預設分隔符)
                body_str = None if body is None else json.dumps(body)
                async with session.request(
                    method, url, headers=headers, data=body_str
                ) as resp:
                    text = await resp.text()
                    try:
                        payload = json.loads(text)
                    except json.JSONDecodeError as err:
                        raise TuyaError(
                            -1, f"invalid JSON response: {text[:200]}"
                        ) from err

                if payload.get("success"):
                    return payload

                # 401 / token 失效 → 重試
                code = payload.get("code", 0)
                if code in (1004, 1010, 1011, 1012) and attempt < retries:
                    _LOGGER.debug("Tuya token invalid (code=%s), refreshing", code)
                    self._token = None
                    self._token_expire_at = 0
                    await asyncio.sleep(0.5)
                    continue

                if code in (1004, 1010, 1011, 1012):
                    raise TuyaAuthError(
                        code,
                        payload.get("msg", "auth failed"),
                        request_id=resp.headers.get("X-Tuya-Request-Id"),
                    )
                raise TuyaError(
                    code,
                    payload.get("msg", "unknown error"),
                    request_id=resp.headers.get("X-Tuya-Request-Id"),
                )
            except aiohttp.ClientError as err:
                last_exc = err
                if attempt < retries:
                    await asyncio.sleep(1 + attempt)
                    continue
                raise TuyaError(-1, f"network error: {err}") from err

        # 不會走到這
        raise TuyaError(-1, f"request failed: {last_exc}")

    # --------------------------- 設備 API ---------------------------

    async def get_device_info(self, device_id: str) -> dict[str, Any]:
        """取得設備基本資訊。"""
        return (
            await self.request("GET", f"/v1.0/iot-03/devices/{device_id}")
        )["result"]

    async def get_device_status(self, device_id: str) -> list[dict[str, Any]]:
        """取得設備所有 DP 當前值。回傳 ``[{code, value}, ...]``。"""
        return (
            await self.request("GET", f"/v1.0/iot-03/devices/{device_id}/status")
        )["result"]

    async def send_commands(
        self,
        device_id: str,
        commands: list[dict[str, Any]],
    ) -> bool:
        """發送多個 DP 指令。"""
        payload = {"commands": commands}
        result = await self.request(
            "POST",
            f"/v1.0/iot-03/devices/{device_id}/commands",
            body=payload,
        )
        return bool(result.get("result"))

    async def send_command(self, device_id: str, code: str, value: Any) -> bool:
        """發送單一 DP 指令(便利函式)。"""
        return await self.send_commands(device_id, [{"code": code, "value": value}])

    async def get_device_functions(self, device_id: str) -> dict[str, Any]:
        """取得設備可用的 DP schema(指令/狀態定義)。"""
        return (
            await self.request(
                "GET", f"/v1.0/iot-03/devices/{device_id}/functions"
            )
        ).get("result", {})

    async def list_devices(self) -> list[dict[str, Any]]:
        """列出該 Tuya 帳號下所有設備(IoT 平台 token 專用)。"""
        page_size = 100
        page_no = 1
        all_devices: list[dict[str, Any]] = []
        while True:
            payload = (
                await self.request(
                    "GET",
                    "/v1.0/iot-01/associated-users/devices",
                    query={"size": page_size, "page": page_no},
                )
            )["result"]
            devices = payload.get("devices", [])
            all_devices.extend(devices)
            total = payload.get("total", 0)
            if len(all_devices) >= total or not devices:
                break
            page_no += 1
        return all_devices

    # ---------------- 使用者 token 模式的設備 API ----------------
    # 使用者 access_token 走的路徑與 IoT 平台 token 不同,
    # 需用 USER_DEVICE_* 常數。方法名以 _u 結尾避免混淆。

    async def get_device_status_u(self, device_id: str) -> list[dict[str, Any]]:
        """(使用者 token)取得設備所有 DP 當前值。"""
        from .const import USER_DEVICE_STATUS_PATH

        result = (
            await self.request(
                "GET", USER_DEVICE_STATUS_PATH.format(device_id=device_id)
            )
        )["result"]
        # 使用者 token 的 status 回傳 { "1": true, "2": false, ... } 形式
        if isinstance(result, dict):
            return [{"code": k, "value": v} for k, v in result.items()]
        return result

    async def send_commands_u(
        self, device_id: str, commands: list[dict[str, Any]]
    ) -> bool:
        """(使用者 token)發送多個 DP 指令。"""
        from .const import USER_DEVICE_COMMAND_PATH

        payload = {
            "commands": [
                (
                    {"code": str(c["code"]), "value": c["value"]}
                    if not str(c["code"]).isdigit()
                    else {"dpId": int(c["code"]), "dpIdStr": str(c["code"]),
                          "value": c["value"]}
                )
                for c in commands
            ]
        }
        result = await self.request(
            "POST",
            USER_DEVICE_COMMAND_PATH.format(device_id=device_id),
            body=payload,
        )
        return bool(result.get("result"))

    async def send_command_u(self, device_id: str, code: str, value: Any) -> bool:
        """(使用者 token)發送單一 DP 指令。"""
        return await self.send_commands_u(device_id, [{"code": code, "value": value}])

    async def get_device_functions_u(self, device_id: str) -> dict[str, Any]:
        """(使用者 token)取得設備 DP schema。"""
        from .const import USER_DEVICE_INFO_PATH

        return (
            await self.request("GET", USER_DEVICE_INFO_PATH.format(device_id=device_id))
        ).get("result", {})
