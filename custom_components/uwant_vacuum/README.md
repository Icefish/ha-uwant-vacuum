# UWANT Vacuum — Home Assistant 整合

控制 UWANT 掃地機(U300 等 Tuya OEM 機型)的 Home Assistant 自訂整合。

## ⭐ 推薦:本地區網模式

**不需要雲端、不需要帳號、不需要中國手機號、不需要拆機。**

只要 `device_id` + `local_key` + 區網 IP,就能直接控制。

### 為什麼選本地模式

原本的雲端方案全部失敗（因塗鴉雲端加密機制限制）:

| 路線 | 結果 |
|---|---|
| Tuya OpenAPI 帳密登入 | ❌ 路徑被加密 |
| Tuya 行動 API | ❌ 白盒密碼學 + APK 憑證綁定 |
| iot.tuya.com 開發者模式 | ⚠️ 需掃碼綁定裝置 |
| HA Tuya 整合 User Code | ⚠️ 需帳號內有該裝置 |
| 共用設備給 Smart Life | ❌ 跨資料中心 |

**本地區網模式全部繞過,而且不需要網路。**

---

## 安裝

1. 把 `custom_components/uwant_vacuum/` 複製到 HA 的 `/config/custom_components/`
2. 重啟 Home Assistant(HACS 會自動安裝 `tinytuya` 依賴)
3. 設定 → 裝置與服務 → 新增整合 → 搜尋「UWANT」

---

## 設定步驟

### 步驟 1: 取得 local_key 與 device_id (免 Root 教學)

UWANT HOME App 底層採用塗鴉（Tuya）SDK。Tuya SDK 預設開啟了 Debug Log，會在與雲端通訊時把**解密後的完整設備資訊（包含 localKey、devId、IP、MAC、DP 清單）寫入手機日誌檔案中**。
最關鍵的是：該日誌儲存於 **Android 外部應用專屬空間（`/sdcard/Android/data/`）**，**不需要 Root** 即可透過標準 `adb` 指令直接拉出！

#### 📁 關鍵日誌位置與檔案名稱
* **路徑**：`/sdcard/Android/data/com.uwant.smart/files/shareData/log/thingLog/`
* **目標檔案**：`thing.log.YYYY-MM-DD.txt`（以當天日期命名，例如 `thing.log.2026-10-01.txt`）

#### 💻 提取與搜尋步驟
1. **開啟手機 USB 偵錯**：
   * 在 Android 手機進入「設定」->「開發人員選項」-> 開啟「USB 偵錯」。
   * 使用傳輸線接上電腦（若尚未安裝 adb，Mac 用戶可執行 `brew install android-platform-tools`）。
   * 執行 `adb devices` 確認手機已連線。

2. **拉取日誌資料夾到電腦**：
   ```bash
   adb pull /sdcard/Android/data/com.uwant.smart/files/shareData/log/thingLog/ /tmp/uwant_logs/
   ```

3. **從日誌中搜尋金鑰與設備 ID**：
   * **取得 16 字元 `local_key`**（取最新日期的 log）：
     ```bash
     grep -oh '"localKey":"[^"]*"' /tmp/uwant_logs/*.txt | sort -u
     ```
   * **取得 `device_id` (devId)**：
     ```bash
     grep -oh '"devId":"[^"]*"' /tmp/uwant_logs/*.txt | sort -u
     ```
   * **查看掃地機完整資訊（包含設備名稱、區網 IP、MAC）**：
     ```bash
     grep -oh '"name":"U300".\{0,300\}' /tmp/uwant_logs/*.txt | head -1
     
     # 或解碼 log 內 DP 34 的 Base64 JSON 資訊：
     grep -oh 'eyJXaUZpX05hbWUi[^"]*' /tmp/uwant_logs/*.txt | base64 -d
     # 會輸出: {"WiFi_Name":"你的WiFi","IP":"192.168.x.x","Mac":"...","devId":"..."}
     ```

*(備用方法：若擁有 Tuya 開發者帳號，亦可在電腦上執行 `python3 -m tinytuya wizard` 取得憑證。)*

### 步驟 2: 取得裝置連線資訊彙整

| 欄位名稱 | 取得來源 | 說明 / 範例 |
|---|---|---|
| **device_id (devId)** | log 裡的 `"devId":"..."` | 20~22 字元字串 (如 `bf1234567890abcdef12`) |
| **local_key** | log 裡的 `"localKey":"..."` | 16 字元專屬通訊金鑰 |
| **區網 IP** | log 內的 DP 34，或路由器 DHCP 列表 | 例如 `192.168.1.100` (建議在路由器綁定靜態 IP) |
| **協議版本** | 固定填寫 | U300 實測為 **`3.3`** |

### 步驟 3:在 HA 新增整合

| 欄位 | 填什麼 |
|---|---|
| 連線方式 | **本地區網(推薦)** |
| 裝置 ID | `bf1234567890abcdef12`(你的裝置ID) |
| local_key | 16 字元 |
| 區網 IP | 例如 `192.168.1.100` |
| 協議版本 | `3.3` |

按送出 → 整合會**立即測試連線**,成功才會建立。

---

## ⚠️ 重要:local_key 會變

**每次重新配對裝置(刪除後重新加入),local_key 就會重新產生。**

若整合突然失效:
1. 重新從 log 提取 local_key
2. 刪除 HA 整合後重新新增
3. 或在整合上按「重新設定」

---

## 支援的功能

| 功能 | DP | 說明 |
|---|---|---|
| 開始清掃 | DP 1 (`switch_go`) = true | |
| 暫停 | DP 1 = false | |
| 回基站 | DP 3 (`switch_charge`) = true | |
| 電量 | DP 8 (`battery_percentage`) | 0-100 |
| 狀態 | DP 5 (`work_status`) | 見下表 |

### 狀態對照(DP 5)

| 值 | HA 狀態 | 意義 |
|---|---|---|
| `smart` | `cleaning` | 清掃中 |
| `goto_charge` | `returning` | 回充中 |
| `charge_done` | `docked` | 充電完成 |
| `charging` | `docked` | 充電中 |
| `paused` | `paused` | 已暫停 |
| `idle` | `idle` | 待機 |

---

## 服務:`set_dp`

可設定任意 Tuya DP:

```yaml
service: uwant_vacuum.set_dp
data:
  code: switch_go      # 或直接用數字 "1"
  value: true
```

---

## 疑難排解

| 症狀 | 原因 | 解法 |
|---|---|---|
| `invalid_auth` | local_key 或版本錯 | 重新提取 local_key(可能已因重新配對而改變) |
| `cannot_connect` | IP 錯 / 不同網段 / 裝置關機 | 確認 HA 與裝置在同一區網,且裝置已開機 |
| 連線常斷 | Tuya 裝置只允許**一個**連線 | 關閉手機上的 UWANT app |
| 重新配對後失效 | local_key 已變 | 重新提取 |

### 為什麼 Tuya 裝置只能一個連線?

Tuya 的區網協議設計上只允許單一 TCP 連線。若手機上的 UWANT app 正在連著,
HA 的連線可能被拒或行為異常。**建議:平常只讓 HA 連,要用 app 時再開。**

---

## 技術細節

### 檔案結構

| 檔案 | 用途 |
|---|---|
| `local_client.py` | ⭐ 本地客戶端(tinytuya 包裝,介面與雲端客戶端相同) |
| `tuya_client.py` | 雲端客戶端(保留,但已知不可行) |
| `coordinator.py` | 輪詢協調器(兩種模式共用) |
| `config_flow.py` | 設定流程(本地 / 帳號 / 開發者 三模式) |
| `vacuum.py` | vacuum entity |
| `sensor.py` | 電量 / 時間 / 面積 sensor |
| `const.py` | DP 對照表、常數 |

### 設計:客戶端介面統一

`LocalTuyaClient` 刻意與 `TuyaClient` 介面一致:

```python
is_user_token          # 屬性
async get_device_status(device_id) -> [{code, value}, ...]
async send_command(device_id, code, value) -> bool
async close()
```

所以 `coordinator.py` **完全不需要修改**就能支援本地模式。

差別只在於本地拿到的 DP 是**數字 ID**(如 `"1"`),
`local_client.py` 會用 `U300_DP_ID_TO_CODE` 轉成 code 名稱(如 `"switch_go"`),
讓上層 entity 無感。

### tinytuya 是同步的

tinytuya 是阻塞式函式庫,所有呼叫都透過 `hass.async_add_executor_job`
丢到 thread pool,不會擋住 HA 的事件迴圈。
