# UWANT Vacuum (Tuya) for Home Assistant

<p align="center">
  <img src="https://raw.githubusercontent.com/Icefish/ha-uwant-vacuum/main/logo.png" alt="UWANT Logo" width="300">
</p>

<p align="center">
  <a href="https://hacs.xyz"><img src="https://img.shields.io/badge/HACS-Custom-orange.svg" alt="HACS Custom"></a>
  <a href="https://github.com/Icefish/ha-uwant-vacuum/releases"><img src="https://img.shields.io/badge/version-v2.1.0-blue.svg" alt="Version"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
</p>

<p align="center">
  <a href="#english">English</a> • <a href="#繁體中文">繁體中文</a>
</p>

---

<a name="english"></a>
## English

Home Assistant custom integration for **UWANT U300 / U300 Pro Max / U300 Max** and other Tuya-based OEM robot vacuums.

Operates via **100% Local LAN Control** using `tinytuya` (Protocol 3.3). Commands communicate directly with the vacuum on your local network with **< 50ms latency**, requiring **no cloud connection, no user accounts, and works completely offline**!

### ✨ Features

* 🚀 **Pure Local LAN Control**: Direct TCP socket communication (Port 6668) with zero cloud latency.
* 🧹 **Native Home Assistant Vacuum Card Support**:
  * Start cleaning (`async_start`)
  * Pause cleaning (`async_pause`)
  * Stop cleaning (`async_stop`)
  * Return to dock / charging base (`async_return_to_base`)
  * Real-time battery percentage (%) with dynamic charging icons
* 🎛️ **Rich Entity Controls (14 Entities Total)**:
  * **4 Select Entities**:
    * **Suction Power**: `quiet`, `normal`, `strong`, `max`
    * **Water Level**: `low`, `medium`, `high`
    * **Clean Mode**: `smart`, `spot`, `edge`, `mop`, `clean_before_mop`
    * **Mop Washing Water Temp**: `cold`, `warm`, `hot`
  * **1 Button Entity**:
    * **Find Device**: Triggers the robot vacuum to beep and speak its location.
  * **Sensors**:
    * Battery percentage, clean time (minutes), clean area (m²), fault code, operational work status.
* 🎨 **Official Brand Assets**: Built-in official high-resolution transparent UWANT orange logo and icon compliant with Home Assistant Brands Proxy specifications.

### 📦 Installation

#### Option 1: Via HACS (Recommended)

1. Open Home Assistant and navigate to **HACS** in the sidebar.
2. Click the three dots **「⋮」** in the top right corner -> Select **Custom repositories**.
3. Fill in the following details:
   * **Repository**: `https://github.com/Icefish/ha-uwant-vacuum`
   * **Type**: Select **Integration**
4. Click **Add**.
5. Search for **UWANT Vacuum (Tuya)** in HACS and click **Download**.
6. **Restart Home Assistant**.

#### Option 2: Manual Installation

1. Download the latest release from the repository.
2. Copy the `custom_components/uwant_vacuum` directory into your Home Assistant `/config/custom_components/` directory.
3. **Restart Home Assistant**.

### ⚙️ How to Obtain `local_key` and `device_id` (No Root Required)

This integration connects directly over your local network and requires your vacuum's **`device_id`**, **`local_key`**, and **`LAN IP`**.

The Tuya SDK on Android enables debug logging by default, writing decrypted device details into external application storage (`/sdcard/Android/data/`). **No root access is required**—you can pull the log with a simple `adb` command:

#### Step 1: Pull Logs from Your Android Phone

1. Enable **Developer Options** and **USB Debugging** on your Android phone.
2. Connect your phone to your computer via USB and verify connection (`adb devices`).
3. Run the following command to pull the logs to your computer:
   ```bash
   adb pull /sdcard/Android/data/com.uwant.smart/files/shareData/log/thingLog/ /tmp/uwant_logs/
   ```

#### Step 2: Extract Key and Device Information

* **Find the 16-character `local_key`** (use the log with the latest date):
  ```bash
  grep -oh '"localKey":"[^"]*"' /tmp/uwant_logs/*.txt | sort -u
  ```
* **Find the `device_id` (`devId`)**:
  ```bash
  grep -oh '"devId":"[^"]*"' /tmp/uwant_logs/*.txt | sort -u
  ```
* **Find Full Device Info (IP, MAC, Name)**:
  ```bash
  grep -oh '"name":"U300".\{0,300\}' /tmp/uwant_logs/*.txt | head -1

  # Or decode the Base64 JSON from Data Point 34:
  grep -oh 'eyJXaUZpX05hbWUi[^"]*' /tmp/uwant_logs/*.txt | base64 -d
  # Output includes: {"WiFi_Name":"...","IP":"192.168.x.x","Mac":"...","devId":"..."}
  ```

> ⚠️ **Important Notice**: If you ever delete and re-pair the robot vacuum in the official UWANT HOME app, Tuya's server will assign a new `local_key`. If the integration stops connecting after re-pairing, re-extract the latest key from the newest log file.

### 🚀 Setup in Home Assistant

1. In Home Assistant, go to **Settings** -> **Devices & Services**.
2. Click **Add Integration** in the bottom right corner and search for **UWANT**.
3. Select **Local network connection (Recommended)** and enter:
   * **Device ID (devId)**: Your 20~22 character device ID.
   * **local_key**: Your 16-character encryption key.
   * **LAN IP**: The local IP address of your vacuum cleaner (e.g., `192.168.1.100`, static DHCP reservation recommended).
   * **Protocol Version**: Default is **`3.3`**.
4. Click **Submit**. Home Assistant will perform a local handshake test and add your vacuum!

### 🛠️ Services

This integration provides the `uwant_vacuum.set_dp` service for advanced automations:

```yaml
service: uwant_vacuum.set_dp
data:
  code: switch_go      # Or use numeric DP ID "1"
  value: true
```

### ❓ FAQ & Troubleshooting

**Q: Why do I get `cannot_connect` when adding the integration?**  
A: Please check:
1. Ensure the vacuum is powered on and the IP address is correct.
2. Confirm Home Assistant and the vacuum cleaner are on the same local network subnet.

**Q: Why does the connection occasionally disconnect?**  
A: Tuya hardware firmware only supports **one active TCP connection at a time**. If the official UWANT HOME app is open on your mobile phone, it may compete with Home Assistant for the connection. It is recommended to close the mobile app when using Home Assistant.

---

<a name="繁體中文"></a>
## 繁體中文

支援 **友望（UWANT）U300 / U300 Pro Max / U300 Max** 等塗鴉（Tuya）OEM 掃拖機器人的 Home Assistant 自訂整合。

採用 **100% 區域網路本地控制（Local LAN）**，指令直連設備（延遲 < 50ms），**不依賴外網雲端、不需要帳號密碼、網路斷線照常運作**！

### ✨ 功能特色

* 🚀 **純區域網路直連**：基於 `tinytuya`（協議 3.3）直接與掃地機通訊，反應零延遲。
* 🧹 **完整支援 HA 原生 Vacuum 卡片**：
  * 開始清掃（Start）
  * 暫停清掃（Pause）
  * 停止清掃（Stop）
  * 返回基站充電（Return to Base / Dock）
  * 即時電量百分比（Battery %）與動態充電狀態圖示
* 🎛️ **豐富的擴充控制實體（共 14 個 Entity）**：
  * **4 組 Select 選單**：
    * 吸力檔位調整（靜音 / 標準 / 強力 / 最大）
    * 拖地水量切換（低 / 中 / 高）
    * 清掃模式選擇（自動 / 定點 / 沿邊 / 純拖 / 掃拖）
    * 洗布水溫控制（冷水 / 溫水 / 熱水）
  * **1 組 Button 按鈕**：
    * 尋找設備（觸發掃地機發出語音與嗶嗶聲提示）
  * **感測器（Sensors）**：
    * 即時電量、清掃時間、清掃面積、故障碼、運作狀態等。
* 🎨 **官方品牌視覺**：內建符合 HA Brands 規範的 UWANT 官方亮橘色透明圖標與橫幅。

### 📦 安裝方式

#### 方法一：透過 HACS 自訂儲存庫安裝（推薦）

1. 開啟 Home Assistant，進入左側選單的 **HACS**。
2. 點選右上角的 **「⋮」（三個點）** -> 選擇 **「自訂儲存庫 (Custom repositories)」**。
3. 填入以下資訊：
   * **儲存庫網址 (Repository)**：`https://github.com/Icefish/ha-uwant-vacuum`
   * **類別 (Type)**：選擇 **「整合 (Integration)」**
4. 點擊 **「新增 (Add)」**。
5. 在 HACS 整合列表中搜尋 **UWANT Vacuum (Tuya)** 並點擊 **「下載 (Download)」**。
6. **重新啟動 Home Assistant**。

#### 方法二：手動複製安裝

1. 下載本專案原始碼。
2. 將 `custom_components/uwant_vacuum` 資料夾完整複製到您的 Home Assistant 設定目錄中的 `/config/custom_components/uwant_vacuum/`。
3. **重新啟動 Home Assistant**。

### ⚙️ 取得設備金鑰（免 Root 教學）

本整合走純區網連線，需要填入設備的 **`device_id`**、**`local_key`** 與 **`區網 IP`**。

塗鴉（Tuya）SDK 預設會輸出除錯記錄，並把解密後的設備通訊資料存放在 Android 手機的外部應用儲存區（`/sdcard/Android/data/`）。**完全不需要 Root 手機**，只要一條 `adb` 指令就能拉出來：

#### 步驟 1：拉取 Android 手機內的 Log

1. 手機進入「設定」->「開發人員選項」-> 開啟「USB 偵錯」。
2. 使用傳輸線連接電腦，確認 ADB 已連線（`adb devices`）。
3. 執行指令將日誌目錄匯出至電腦：
   ```bash
   adb pull /sdcard/Android/data/com.uwant.smart/files/shareData/log/thingLog/ /tmp/uwant_logs/
   ```

#### 步驟 2：搜尋通訊金鑰與設備 ID

* **取得 16 碼 `local_key`**（請取最新日期的日誌）：
  ```bash
  grep -oh '"localKey":"[^"]*"' /tmp/uwant_logs/*.txt | sort -u
  ```
* **取得 `device_id` (devId)**：
  ```bash
  grep -oh '"devId":"[^"]*"' /tmp/uwant_logs/*.txt | sort -u
  ```
* **取得設備完整資訊（區網 IP、MAC、名稱）**：
  ```bash
  grep -oh '"name":"U300".\{0,300\}' /tmp/uwant_logs/*.txt | head -1
  
  # 或解碼 DP 34 的 Base64 JSON 資訊：
  grep -oh 'eyJXaUZpX05hbWUi[^"]*' /tmp/uwant_logs/*.txt | base64 -d
  # 輸出內容包含: {"WiFi_Name":"...","IP":"192.168.x.x","Mac":"...","devId":"..."}
  ```

> ⚠️ **重要提醒**：塗鴉設備如果在原廠 App 內被「刪除並重新配對」，`local_key` 就會被伺服器重新分配生成。如果日後連線失效，依上述步驟重新取得最新 Log 內的 Key 即可。

### 🚀 在 Home Assistant 中新增整合

1. 進入 Home Assistant -> **「設定」** -> **「裝置與服務」**。
2. 點擊右下角 **「新增整合」**，搜尋 **UWANT**。
3. 選擇 **「本地區網連線 (推薦)」** 模式，填入：
   * **裝置 ID (devId)**：剛才取得的 20~22 碼字串
   * **local_key**：16 碼專屬金鑰
   * **區網 IP**：掃地機在區網中的 IP（例如 `192.168.1.100`，建議在路由器中設定靜態 DHCP 綁定）
   * **協議版本**：預設填寫 **`3.3`**
4. 點擊送出，整合會立即進行區網握手測試，成功後即完成綁定！

### 🛠️ 自訂服務 (Services)

本整合提供 `uwant_vacuum.set_dp` 服務，供進階自動化使用者下發任意塗鴉 Data Point：

```yaml
service: uwant_vacuum.set_dp
data:
  code: switch_go      # 或直接填入數字 DP ID "1"
  value: true
```

### ❓ 常見問題與除錯 (FAQ)

**Q：為什麼新增整合時提示 `cannot_connect`（無法連線）？**  
A：請確認：
1. 填寫的區網 IP 是否正確，掃地機電源是否已開啟。
2. Home Assistant 主機與掃地機是否處於同一個網段（Subnet）。

**Q：為什麼連線會偶爾中斷？**  
A：塗鴉硬體協議設計上**只允許單一 TCP 連線**。如果您的手機正在開啟「UWANT HOME」App，App 與機器的連線可能會與 Home Assistant 產生競爭。平常建議關閉手機 App，交由 Home Assistant 全權接管。

---

## 📄 License / 授權條款

This project is licensed under the [MIT License](LICENSE).
