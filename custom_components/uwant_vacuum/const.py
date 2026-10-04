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

# -------------------------------------------------------------------# ---------------------------------------------------------------------
# 擴充 DP code 名稱(第二十版,2026-10-04)
#
# ⚠️ 注意:這些命名是「推測」,需用 UWANT app 點設定後看 log 驗證。
# DP 數字 → 設定項對應 是根據 iOS app 介面推測的:
#   基站設定:清洗 / 烘乾 / 集塵 / 清潔液 / 回洗頻率
#   行為設定:童鎖 / 勿擾 / 無樓梯 / 按鍵燈 / 地毯
# ---------------------------------------------------------------------

# 拖布模組 / 水箱 / 耗材
DP_MOP_MODULE: Final = "mop_module"              # DP 11 bool — 拖布模組是否就位
DP_EDGE_BRUSH: Final = "edge_brush"             # DP 25 bool — 邊刷啟用
DP_AUTO_DOCK: Final = "auto_dock"               # DP 27 bool — 自動回充
DP_CISTERN: Final = "cistern"                   # DP 11 別名(同 mop_module)

# 耗材狀態感測器
DP_WATER_SHORTAGE: Final = "water_shortage"     # DP 37 1=缺水
DP_DIRTY_WATER_FULL: Final = "dirty_water_full" # DP 38 bool
DP_DUST_BAG_FULL: Final = "dust_bag_full"       # DP 39 bool
DP_FAST_CHARGE: Final = "fast_charge"           # DP 155 bool — 快充模式

# 基站動作(可寫的開關)
DP_AUTO_DUST_COLLECT: Final = "auto_dust_collect"   # DP 148 bool — 自動集塵開關
DP_HANDHELD_DUST_COLLECT: Final = "handheld_dust_collect" # DP 160 bool — 手動集塵觸發

# 基站動作(可寫的開關)
DP_DETOUR_WATER_CTRL: Final = "detergent_switch" # DP 19 — 投放清潔液
DP_WASH_WATER_TEMP_CTRL: Final = "wash_water_temp_ctrl" # DP 158 — 清洗水溫控制

# 地毯相關
DP_CARPET_CLEAN: Final = "carpet_clean"           # DP 139 bool — 地毯清潔啟用
DP_CARPET_MODE: Final = "carpet_mode"             # DP 140 str — boost/lift/avoid
DP_CARPET_STRATEGY: Final = "carpet_strategy"     # DP 44 str — adaptive/avoid/lift
DP_CARPET_BOOST: Final = "carpet_boost"           # DP 45 bool — 地毯增壓
DP_AUTO_BOOST_CARPET: Final = "auto_boost_carpet" # DP 157 bool — 自動地毯增壓

# 行為開關
DP_KEY_LED_ALWAYS_ON: Final = "key_led_always_on"   # DP 155 bool — 按鍵燈常亮
DP_STAIR_AVOID: Final = "stair_avoid_mode"         # DP 156 bool — 無樓梯模式
DP_NO_STAIR_MODE: Final = "no_stair_mode"           # DP 159 bool — 無樓梯模式(別名)
DP_HANDHELD_CLEAN: Final = "handheld_clean"         # DP 150 bool — 手動局部清掃

# 模式值選項
CARPET_STRATEGY_OPTIONS: Final[tuple[str, ...]] = ("adaptive", "avoid", "lift")
CARPET_STRATEGY_DEFAULT: Final = "adaptive"

CARPET_MODE_OPTIONS: Final[tuple[str, ...]] = ("boost", "lift", "avoid")
CARPET_MODE_DEFAULT: Final = "boost"

# 計數(烘乾/回洗時間,推測可寫)
DP_DRY_DURATION_MIN: Final = "dry_duration_min"     # DP 141 str(int)
DP_WASH_INTERVAL_MIN: Final = "wash_interval_min"   # DP 17 int
DP_DUST_COLLECT_FREQ: Final = "dust_collect_freq"   # DP 21 int
DP_WASH_COUNTDOWN: Final = "wash_countdown"         # DP 28 int
DP_WASH_EXTRA: Final = "wash_extra"                 # DP 142 int
DP_CLEAN_FINE: Final = "clean_fine"                 # DP 53 str
DP_VOLUME: Final = "volume"                       # DP 26 — 語音提示音量 0-100
DP_DO_NOT_DISTURB: Final = "do_not_disturb"     # DP 154 — 勿擾模式 bool
DP_WATER_TEMP: Final = "water_temp"              # DP 135 — water_temp cold/warm/hot
DP_FIND_DEVICE: Final = "find_device"            # DP 149 — 找吸塵器觸發指令
DP_KID_LOCK: Final = "kid_lock"                  # DP 47 — 兒童鎖

# 故障碼(可能有兩個 DP)
DP_FAULT_STUCK: Final = "fault_stuck"               # DP 102
DP_FAULT_LIFT: Final = "fault_lift"                 # DP 103

# 默認值
DEFAULT_DRY_MINUTES: Final = 120
DEFAULT_WASH_INTERVAL_MIN: Final = 15
DEFAULT_DUST_FREQ_MINUTES: Final = 30

# U300 的 DP ID → DP code 對照表
#
# 本地模式拿到的 DP 是「數字 ID」,但 entity 用的是「code 名稱」。
# 這個表讓本地客戶端把數字 ID 轉成既有的 code 名稱,
# 這樣 vacuum.py / sensor.py 完全不需要改。
#
# 對照來源:2026-10-01 實測 + product-configs-prod.json
# ---------------------------------------------------------------------

# 拖布模組 / 水箱 / 耗材
DP_MOP_MODULE: Final = "mop_module"              # DP 11 bool — 拖布模組是否就位
DP_EDGE_BRUSH: Final = "edge_brush"             # DP 25 bool — 邊刷啟用
DP_AUTO_DOCK: Final = "auto_dock"               # DP 27 bool — 自動回充
DP_CISTERN: Final = "cistern"                   # DP 11 別名(同 mop_module)

# 耗材狀態感測器
DP_WATER_SHORTAGE: Final = "water_shortage"     # DP 37 1=缺水
DP_DIRTY_WATER_FULL: Final = "dirty_water_full" # DP 38 bool
DP_DUST_BAG_FULL: Final = "dust_bag_full"       # DP 39 bool
DP_FAST_CHARGE: Final = "fast_charge"           # DP 155 bool — 快充模式

# 基站動作(可寫的開關)
DP_AUTO_DUST_COLLECT: Final = "auto_dust_collect"   # DP 148 bool — 自動集塵開關
DP_HANDHELD_DUST_COLLECT: Final = "handheld_dust_collect" # DP 160 bool — 手動集塵觸發

# 基站動作(可寫的開關)
DP_DETOUR_WATER_CTRL: Final = "detergent_switch" # DP 19 — 投放清潔液
DP_WASH_WATER_TEMP_CTRL: Final = "wash_water_temp_ctrl" # DP 158 — 清洗水溫控制

# 地毯相關
DP_CARPET_CLEAN: Final = "carpet_clean"           # DP 139 bool — 地毯清潔啟用
DP_CARPET_MODE: Final = "carpet_mode"             # DP 140 str — boost/lift/avoid
DP_CARPET_STRATEGY: Final = "carpet_strategy"     # DP 44 str — adaptive/avoid/lift
DP_CARPET_BOOST: Final = "carpet_boost"           # DP 45 bool — 地毯增壓
DP_AUTO_BOOST_CARPET: Final = "auto_boost_carpet" # DP 157 bool — 自動地毯增壓

# 行為開關
DP_KEY_LED_ALWAYS_ON: Final = "key_led_always_on"   # DP 155 bool — 按鍵燈常亮
DP_STAIR_AVOID: Final = "stair_avoid_mode"         # DP 156 bool — 無樓梯模式
DP_NO_STAIR_MODE: Final = "no_stair_mode"           # DP 159 bool — 無樓梯模式(別名)
DP_HANDHELD_CLEAN: Final = "handheld_clean"         # DP 150 bool — 手動局部清掃

# 模式值選項
CARPET_STRATEGY_OPTIONS: Final[tuple[str, ...]] = ("adaptive", "avoid", "lift")
CARPET_STRATEGY_DEFAULT: Final = "adaptive"

CARPET_MODE_OPTIONS: Final[tuple[str, ...]] = ("boost", "lift", "avoid")
CARPET_MODE_DEFAULT: Final = "boost"

# 計數(烘乾/回洗時間,推測可寫)
DP_DRY_DURATION_MIN: Final = "dry_duration_min"     # DP 141 str(int)
DP_WASH_INTERVAL_MIN: Final = "wash_interval_min"   # DP 17 int
DP_DUST_COLLECT_FREQ: Final = "dust_collect_freq"   # DP 21 int
DP_WASH_COUNTDOWN: Final = "wash_countdown"         # DP 28 int
DP_WASH_EXTRA: Final = "wash_extra"                 # DP 142 int
DP_CLEAN_FINE: Final = "clean_fine"                 # DP 53 str

U300_DP_ID_TO_CODE: Final[dict[str, str]] = {
    # === 已驗證(2026-10-01 / 2026-10-02 實測)===
    "1": DP_CLEAN_SWITCH_NEW,        # switch_go        — 清掃開關
    "3": DP_CHARGE_SWITCH_NEW,       # switch_charge    — 回充開關
    "4": "work_mode",                #                   — 模式(chargego / smart)
    "5": "work_status",              #                   — 工作狀態(關鍵!)
    "6": "clean_time_min",
    "7": "clean_area_m2",
    "8": DP_BATTERY_NEW,             # battery_percentage — 電量
    "9": DP_SUCTION,                 # suction          — 吸力
    "10": DP_WATER_LEVEL,            # water_level      — 水量
    "26": "volume",                  #                   — 音量 0-100
    "29": "total_area",              #                   — 累計面積
    "30": "total_time",              #                   — 累計時間(分)
    "31": "total_count",             #                   — 累計次數
    "53": "clean_fine",              #                   — 精細度 fine/standard
    "130": DP_CLEAN_STATUS,          # clean_status     — 清掃狀態
    "132": DP_CLEAN_MODE,            # clean_mode       — 清掃模式
    "135": "water_temp",             #                   — 水溫
    "138": "clean_mode_quick",       #                   — 快捷模式

    # === v2.2.0 新增推測(2026-10-04)===
    # ⚠️ 這些命名是根據 DP 值型別 + UWANT app 設定項推測,
    #    需要逐個在 UWANT app 切換後看 log 驗證。
    #    全部已收錄是為了讓 vacuum.py / sensor.py / switch.py
    #    能直接用 code 名稱引用,不需要再寫 "154"。
    "2": "pause_switch",             # 暫停開關
    "11": DP_MOP_MODULE,             # 拖布模組(已裝 True)
    "17": DP_WASH_INTERVAL_MIN,      # 拖布回洗頻率(分)
    "19": DP_DETOUR_WATER_CTRL,      # 是否投放清潔液
    "21": DP_DUST_COLLECT_FREQ,      # 集塵頻率
    "25": DP_EDGE_BRUSH,             # 邊刷啟用
    "27": DP_AUTO_DOCK,              # 自動回充
    "28": DP_WASH_COUNTDOWN,         # 下次回洗倒數
    "37": DP_WATER_SHORTAGE,         # 水箱缺水
    "38": DP_DIRTY_WATER_FULL,       # 污水箱滿
    "39": DP_DUST_BAG_FULL,          # 集塵袋滿
    "44": DP_CARPET_STRATEGY,        # 地毯策略 adaptive/avoid/lift
    "45": DP_CARPET_BOOST,           # 地毯增壓
    "47": DP_KID_LOCK,               # 兒童鎖
    "51": "base_volume",             # 基站音量(?)
    "102": DP_FAULT_STUCK,           # 故障:卡住
    "103": DP_FAULT_LIFT,            # 故障:抬起
    "139": DP_CARPET_CLEAN,          # 地毯清潔啟用
    "140": DP_CARPET_MODE,           # 地毯模式 boost/lift/avoid
    "141": DP_DRY_DURATION_MIN,      # 烘乾時長(分)
    "142": DP_WASH_EXTRA,            # 額外清洗
    "148": DP_AUTO_DUST_COLLECT,     # 自動集塵
    "149": "unknown_149",            # 尚未命名(keep)
    "150": DP_HANDHELD_CLEAN,        # 手動局部清掃
    "154": DP_DO_NOT_DISTURB,        # 勿擾模式
    "155": DP_KEY_LED_ALWAYS_ON,     # 按鍵燈常亮
    "156": DP_STAIR_AVOID,           # 無樓梯模式
    "157": DP_AUTO_BOOST_CARPET,     # 自動地毯增壓
    "158": DP_WASH_WATER_TEMP_CTRL,  # 清洗水溫控制
    "159": DP_NO_STAIR_MODE,         # 無樓梯模式(別名)
    "160": DP_HANDHELD_DUST_COLLECT, # 手動集塵
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


# 計數(烘乾/回洗時間,推測可寫)
DP_DRY_DURATION_MIN: Final = "dry_duration_min"     # DP 141 str(int)
DP_WASH_INTERVAL_MIN: Final = "wash_interval_min"   # DP 17 int
DP_DUST_COLLECT_FREQ: Final = "dust_collect_freq"   # DP 21 int
DP_WASH_COUNTDOWN: Final = "wash_countdown"         # DP 28 int
DP_WASH_EXTRA: Final = "wash_extra"                 # DP 142 int
DP_CLEAN_FINE: Final = "clean_fine"                 # DP 53 str

# 故障碼(可能有兩個 DP)
DP_FAULT_STUCK: Final = "fault_stuck"               # DP 102
DP_FAULT_LIFT: Final = "fault_lift"                 # DP 103

# 默認值
DEFAULT_DRY_MINUTES: Final = 120
DEFAULT_WASH_INTERVAL_MIN: Final = 15
DEFAULT_DUST_FREQ_MINUTES: Final = 30
