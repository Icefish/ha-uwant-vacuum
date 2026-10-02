"""Constants for the UWANT Vacuum (Tuya) integration."""
from __future__ import annotations

from typing import Final

DOMAIN: Final = "uwant_vacuum"

# config_flow / 設定項目使用的 key
CONF_REGION: Final = "region"
CONF_ACCESS_ID: Final = "access_id"
CONF_ACCESS_SECRET: Final = "access_secret"
CONF_DEVICE_ID: Final = "device_id"
CONF_COUNTRY_CODE: Final = "country_code"

# Tuya OpenAPI 區域端點(從 UWANT app 註冊地區對應)
REGION_ENDPOINTS: Final[dict[str, str]] = {
    "china": "https://openapi.tuyacn.com",
    "us": "https://openapi.tuyaus.com",
    "europe": "https://openapi.tuyaeu.com",
    "india": "https://openapi.tuyain.com",
    "singapore": "https://openapi.tuyaus.com",
    "japan": "https://openapi.tuyaus.com",
}

# ---------------------------------------------------------------------
# UWANT HOME 3.0.9 的 Tuya 應用憑證
# 來源:AndroidManifest.xml 的 <meta-data>
#   THING_SMART_APPKEY / THING_SMART_SECRET
# 這是「應用層」憑證(等同 app 本身的 client_id/secret),
# 可用使用者自己的 UWANT 帳密登入,不需要 iot.tuya.com 開發者帳號。
# ---------------------------------------------------------------------
UWANT_APP_KEY: Final = "p3wcknhtvtndnehys4at"
UWANT_APP_SECRET: Final = "yucegrfagq3yg5huptpfg9sfukv95aaj"
TUYA_SDK_VERSION: Final = "5.17.0"

# 國碼(手機註冊的中國帳號為 86,email 註冊可留空或用 86)
COUNTRY_CODE_CN: Final = "86"
COUNTRY_CODE_US: Final = "1"

# 候選登入端點。SDK 5.x 將 API 路徑加密,無法從靜態分析直接取得,
# 這裡列出公開已知的 Tuya app 登入路徑,由探測腳本逐一嘗試。
# {username} 與 {password} 會在呼叫時替換。
LOGIN_PATH_CANDIDATES: Final[tuple[str, ...]] = (
    "/v1.0/iot-02/users/{username}/password/login?password={password}",
    "/v1.0/iot-01/users/{username}/password/login?password={password}",
    "/v1.1/iot-01/users/{username}/password/login?password={password}",
    "/v1.0/users/{username}/password/login?password={password}",
)

# 使用者 token 可存取設備的路徑候選(拿到 uid 後列設備)
USER_DEVICE_LIST_CANDIDATES: Final[tuple[str, ...]] = (
    "/v1.0/iot-01/users/{uid}/devices",
    "/v1.0/iot-02/users/{uid}/devices",
    "/v1.0/iot-01/users/devices",
    "/v1.0/iot-02/users/devices",
)

# 設備 DP 讀寫(使用者 token 版本)
USER_DEVICE_STATUS_PATH: Final = "/v1.0/iot-01/devices/{device_id}/status"
USER_DEVICE_COMMAND_PATH: Final = "/v1.0/iot-01/devices/{device_id}/commands"
USER_DEVICE_INFO_PATH: Final = "/v1.0/iot-01/devices/{device_id}"

# 通用 DP(資料點)識別碼 — UWANT 兩大系列
# 舊版 (U200 / U200 Pro)
DP_CLEAN_SWITCH_OLD: Final = "clean_switch"        # 101
DP_CHARGE_SWITCH_OLD: Final = "charge_switch"      # 103
DP_BATTERY_OLD: Final = "battery"                  # 106

# 新版 (U300 / U260 / T300 / U400)
DP_CLEAN_SWITCH_NEW: Final = "switch_go"           # 1
DP_CHARGE_SWITCH_NEW: Final = "switch_charge"      # 3
DP_BATTERY_NEW: Final = "battery_percentage"      # 8

# 掃地機通用(兩個版本都常見)
DP_CLEAN_MODE: Final = "clean_mode"                # smart/edge/spot/single/mop 等
DP_CLEAN_STATUS: Final = "clean_status"            # standby/sweeping/paused/charging/...
DP_SUCTION: Final = "suction"                      # quiet/standard/strong/max
DP_WATER_LEVEL: Final = "water_level"              # low/middle/high
DP_FAULT: Final = "fault"                          # 故障碼
DP_CLEAN_TIME: Final = "clean_time"                # 已清掃時間(分)
DP_CLEAN_AREA: Final = "clean_area"                # 已清掃面積(m²)
DP_DIRECTION: Final = "direction_control"          # 手動控制方向

# 對應到舊/新版的 DP 別名(同一功能不同 ID)
DP_ALIASES: Final[dict[str, tuple[str, str]]] = {
    "clean_switch": (DP_CLEAN_SWITCH_OLD, DP_CLEAN_SWITCH_NEW),
    "charge_switch": (DP_CHARGE_SWITCH_OLD, DP_CHARGE_SWITCH_NEW),
    "battery": (DP_BATTERY_OLD, DP_BATTERY_NEW),
}

# 清掃狀態碼 -> HA vacuum state
TUYA_STATUS_TO_HA: Final[dict[str, str]] = {
    "standby": "idle",
    "smart": "cleaning",
    "smart_clean": "cleaning",
    "wall_follow": "cleaning",
    "spot": "cleaning",
    "mop": "cleaning",
    "sleep": "docked",
    "paused": "paused",
    "charging": "docked",
    "charge_done": "docked",
    "recharge": "returning",
    "fault": "error",
}

# 預設掃描間隔
DEFAULT_SCAN_INTERVAL: Final = 30  # 秒


# ---------------------------------------------------------------------
# 本地模式(區域網路直連,tinytuya)
#
# 這是 2026-10-01 實測驗證成功的方式:
#   用 local_key 走 TCP 6668 直接控制,完全不經過雲端。
#   local_key 取得方式請參考 README.md 的說明
# ---------------------------------------------------------------------

CONF_LOCAL_KEY: Final = "local_key"
CONF_LOCAL_IP: Final = "local_ip"
CONF_PROTOCOL_VERSION: Final = "protocol_version"

# Tuya 區網協議預設埠
DEFAULT_LOCAL_PORT: Final = 6668

# 支援的協議版本(U300 實測為 3.3)
PROTOCOL_VERSIONS: Final[tuple[str, ...]] = ("3.1", "3.2", "3.3", "3.4", "3.5")
DEFAULT_PROTOCOL_VERSION: Final = "3.3"

# 本地連線逾時(秒)
LOCAL_SOCKET_TIMEOUT: Final = 10

# ---------------------------------------------------------------------
# U300 的 DP ID → DP code 對照表
#
# 本地模式拿到的 DP 是「數字 ID」,但 entity 用的是「code 名稱」。
# 這個表讓本地客戶端把數字 ID 轉成既有的 code 名稱,
# 這樣 vacuum.py / sensor.py 完全不需要改。
#
# 對照來源:2026-10-01 實測 + product-configs-prod.json
# ---------------------------------------------------------------------
U300_DP_ID_TO_CODE: Final[dict[str, str]] = {
    "1": DP_CLEAN_SWITCH_NEW,       # switch_go        — 清掃開關
    "2": "pause_switch",            #                   — 暫停
    "3": DP_CHARGE_SWITCH_NEW,      # switch_charge    — 回充開關
    "4": "work_mode",               #                   — 模式(chargego / smart)
    "5": "work_status",             #                   — 工作狀態(關鍵!)
    "6": "clean_time_min",
    "7": "clean_area_m2",
    "8": DP_BATTERY_NEW,            # battery_percentage — 電量
    "9": DP_SUCTION,                # suction          — 吸力
    "10": DP_WATER_LEVEL,           # water_level      — 水量
    "17": "unknown_17",
    "19": "unknown_19",
    "21": "unknown_21",
    "26": "volume",
    "29": "total_area",
    "30": "total_time",
    "31": "total_count",
    "37": "unknown_37",
    "44": "unknown_44",
    "45": "unknown_45",
    "51": "unknown_51",
    "53": "clean_fine",
    "130": DP_CLEAN_STATUS,         # clean_status     — 清掃狀態
    "132": DP_CLEAN_MODE,           # clean_mode       — 清掃模式
    "135": "water_temp",
    "138": "clean_mode_quick",
    "139": "unknown_139",
    "140": "unknown_140",
    "141": "unknown_141",
    "149": "unknown_149",
    "150": "unknown_150",
    "160": "unknown_160",
}

# 反向對照(code → DP ID),給下指令用
U300_CODE_TO_DP_ID: Final[dict[str, str]] = {
    code: dp_id for dp_id, code in U300_DP_ID_TO_CODE.items()
}

# ---------------------------------------------------------------------
# 本地模式的狀態判斷(實測 2026-10-01)
#
# DP 5 (work_status) 是判斷掃地機在做什麼的主要依據:
#   charge_done  = 充電完成,在座上待機
#   charging     = 充電中
#   smart        = 清掃中
#   goto_charge  = 正在回基站
#   paused       = 已暫停
# ---------------------------------------------------------------------
U300_WORK_STATUS_TO_HA: Final[dict[str, str]] = {
    "charge_done": "docked",
    "charging": "docked",
    "chargego": "docked",
    "goto_charge": "returning",
    "smart": "cleaning",
    "cleaning": "cleaning",
    "spot": "cleaning",
    "zone": "cleaning",
    "paused": "paused",
    "pause": "paused",
    "idle": "idle",
    "standby": "idle",
    "sleep": "docked",
    "fault": "error",
    "error": "error",
}


# ---------------------------------------------------------------------
# 擴充 DP(本地控制已驗證可用)
# 來源:2026-10-02 從 UWANT app log + 實測確認
# ---------------------------------------------------------------------
DP_VOLUME: Final = "volume"                       # DP 26 — 語音提示音量 0-100
DP_DO_NOT_DISTURB: Final = "do_not_disturb"     # DP 154 — 勿擾模式 bool
DP_WATER_TEMP: Final = "water_temp"              # DP 135 — water_temp cold/warm/hot
DP_FAULT_V2: Final = "fault_v2"                  # DP 102/103 — 故障碼變體
DP_FIND_DEVICE: Final = "find_device"            # DP 149 — 找吸塵器觸發指令
DP_EDGE_BRUSH: Final = "edge_brush"              # DP 2 — 邊刷
DP_CISTERN: Final = "cistern"                    # DP 11 — 水箱
DP_MOP: Final = "mop"                            # DP 25 — 拖地
DP_AUTO_DOCK: Final = "auto_dock"                # DP 27 — 自動回充
DP_DIRTY_NOTIFY: Final = "dirty_notify"          # DP 38 — 污水提醒
DP_KID_LOCK: Final = "kid_lock"                  # DP 47 — 兒童鎖
DP_FAST_CHARGE: Final = "fast_charge"            # DP 155 — 快充

# DP 2, 11, 25, 27, 38, 47 在 U300_DP_ID_TO_CODE 表中對應的數字 ID
# (在 local_client.py 已對應,但這裡加正式常數供 sensor 使用)

# ---------------------------------------------------------------------
# 吸力 / 水量 / 模式的可選值清單
# ---------------------------------------------------------------------
SUCTION_OPTIONS: Final[tuple[str, ...]] = ("quiet", "normal", "strong", "max")
SUCTION_DEFAULT: Final = "normal"

WATER_LEVEL_OPTIONS: Final[tuple[str, ...]] = ("low", "medium", "high")
WATER_LEVEL_DEFAULT: Final = "low"

CLEAN_MODE_OPTIONS: Final[tuple[str, ...]] = (
    "smart",          # 自動/智能
    "spot",           # 定點
    "edge",           # 沿邊
    "mop",            # 拖地
    "clean_before_mop",  # 掃拖
    "zone",           # 區域
)
CLEAN_MODE_DEFAULT: Final = "smart"

WATER_TEMP_OPTIONS: Final[tuple[str, ...]] = ("cold", "warm", "hot")
WATER_TEMP_DEFAULT: Final = "warm"

# ---------------------------------------------------------------------
# HA Vacuum fan_speed 用的標準化字串(<-> SUCTION_OPTIONS)
# 標準值:silent/quiet、auto、normal、high、max、min、medium
# 我們用 Tuya 原生字串,讓 HA 自動對應 silent/quiet 等
# ---------------------------------------------------------------------
