"""Tuya MQTT 客戶端(選用):直接訂閱 Tuya 雲 MQTT broker。

與 OpenAPI(HTTPS REST)不同,這條路可以:
- 真正即時接收設備狀態變化(push,不用輪詢)
- 不需要每次打 token 簽章
- 但仍需要設備的 deviceSecret(從 Tuya IoT 平台取得)

broker 端點對應各區域:
- 中國:   m2.tuyacn.com   8883 / 8886
- 美國:   m2.tuyaus.com   8883 / 8886
- 歐洲:   m2.tuyaeu.com   8883 / 8886
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from typing import Any, Callable, Coroutine

import paho.mqtt.client as mqtt  # type: ignore[import]

_LOGGER = logging.getLogger(__name__)


REGION_BROKER: dict[str, tuple[str, int]] = {
    "china": ("m2.tuyacn.com", 8883),
    "us": ("m2.tuyaus.com", 8883),
    "europe": ("m2.tuyaeu.com", 8883),
    "india": ("m2.tuyain.com", 8883),
}


class TuyaMQTTClient:
    """薄包裝 Tuya MQTT 連線。

    Parameters
    ----------
    device_id:
        設備 ID。
    device_secret:
        設備 secret(從 Tuya IoT Platform 設備詳情取得)。
    region:
        地區代碼: china / us / europe / india。
    on_message:
        回呼 ``async def callback(payload: dict) -> None``。
    """

    def __init__(
        self,
        *,
        device_id: str,
        device_secret: str,
        region: str = "china",
        on_message: Callable[[dict[str, Any]], Coroutine[Any, Any, None]] | None = None,
    ) -> None:
        self.device_id = device_id
        self.device_secret = device_secret
        self.region = region
        self._on_message_cb = on_message

        broker, port = REGION_BROKER.get(region, REGION_BROKER["china"])
        self._broker = broker
        self._port = port

        self._client = mqtt.Client(
            client_id=f"tuya/{device_id}",
            protocol=mqtt.MQTTv311,
        )
        self._client.username_pw_set(
            username=device_id,
            password=self._make_password(),
        )
        self._client.tls_set()  # SSL/TLS
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._connected = False

    # ---------------- 密碼生成 ----------------

    def _make_password(self) -> str:
        """Tuya MQTT 密碼公式(2022+ 版本):

        password = HMAC-SHA256(clientId, "secret=...|t=...|signMethod=hmacSha256")
                  其中 clientId = "<device_id>"
        """
        # 雖然 HA 主程式已是 async,這裡 paho 是 blocking;在 executor 跑
        # 但產生密碼可在 sync 端做
        t = str(int(time.time() * 1000))
        # 公式來源: Tuya 文件(注意不同設備類型可能略不同,以官方為準)
        msg = f"clientId={self.device_id}deviceId={self.device_id}secureMode=1t={t}".encode()
        sign = hmac.new(self.device_secret.encode(), msg, hashlib.sha256).hexdigest()
        return sign  # 簡化版;實務可能還需 base64 編碼,視設備 firmware 而定

    # ---------------- 回呼 ----------------

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._connected = True
            _LOGGER.info("Tuya MQTT connected to %s:%s", self._broker, self._port)
            # 訂閱設備 topic(典型格式:tylink/{device_id}/device/status)
            topic = f"tylink/{self.device_id}/device/status"
            client.subscribe(topic, qos=1)
        else:
            _LOGGER.error("Tuya MQTT connect failed, rc=%s", rc)

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            _LOGGER.debug("MQTT msg %s: %s", msg.topic, payload)
            if self._on_message_cb:
                # 用 asyncio 在已運行的事件循環排程 callback
                import asyncio

                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._on_message_cb(payload))
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("MQTT message parse error: %s", err)

    # ---------------- 介面 ----------------

    def start(self) -> None:
        """啟動背景 loop(在 executor 中跑)。"""
        import asyncio

        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, self._client.connect, self._broker, self._port, 60)
        self._client.loop_start()

    def stop(self) -> None:
        """停止 loop 並斷線。"""
        self._client.loop_stop()
        self._client.disconnect()

    def publish_command(self, code: str, value: Any) -> None:
        """發送 DP 指令(若 broker 支援)。"""
        topic = f"tylink/{self.device_id}/device/command"
        payload = json.dumps({"code": code, "value": value})
        self._client.publish(topic, payload, qos=1)
