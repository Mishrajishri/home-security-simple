# VidyutRakshak (विद्युत रक्षक) ⚡
### Smart Home Automation & Door Security System — Vigyan Mela 2026

VidyutRakshak is an offline-first, dual-ESP32 smart home automation and access control security system. It combines local hardware actuation, energy conservation, power-cut state memory, RFID access, 4x4 keypad matrix entry, gas/motion safety monitoring, and an offline voice-enabled local web dashboard.

---

## 🌟 Key Features

### 1. 💡 Light & Fan Controller (ESP32-A)
* **4-Channel AC Appliance Switching:** 3 Lights + 1 Fan driven by heavy-duty relays with BC337 transistor drivers.
* **⚡ Power-Cut Last-State Memory (Flash NVS):** Inverter-like behavior — when mains power is cut and restored, appliances resume their exact previous ON/OFF states in **<50ms**, completely offline without waiting for WiFi or server boot.
* **🔥 Gas Leakage Safety (MQ Sensor):** Real-time gas PPM monitoring with alert thresholds and automatic buzzer alarms.
* **🚶 Motion Detection (PIR Sensor):** Smart occupancy detection to monitor activity and trigger energy-saving sequences.

### 2. 🚪 Door Access Security Controller (ESP32-B)
* **🔢 4x4 Membrane Keypad PIN Access:**
  * Password stored locally in ESP32 Flash memory (`Preferences`).
  * 100% offline verification — unlocks the door even if the network/server is completely down.
  * Real-time PIN update from mobile/laptop dashboard synced via MQTT.
* **💳 Offline RFID Access (MFRC522):**
  * Authorized card UIDs stored in ESP32 Flash memory.
  * Instant unlock (<10ms) without network latency.
  * Auto-synced when cards are added or removed from the web dashboard.
* **📟 16x4 I2C LCD Display:**
  * Displays brand status, network connection, IP address, masked PIN entry, and access prompts.
* **🔒 Auto-Lock:** Door automatically re-locks 5 seconds after authorized access.

### 3. 🏠 Local Hub Server & Web Dashboard
* **Embedded MQTT Broker:** High-performance Aedes broker on port 1883.
* **Responsive Dashboard:** Accessible over HTTP (`:3000`) and HTTPS (`:3443`) on PC, tablet, or smartphone.
* **🎙️ Offline Voice Assistant:** Voice control in Hindi & English powered by Vosk speech recognition models.
* **Live WebSockets:** Instant UI sync for device statuses, gas PPM levels, RFID logs, and activity logs.

### 4. 🖨️ Custom Hardware & Acid-Etched PCBs
* Single-layer acid-etched PCB layouts designed in KiCad with ultra-thick traces (2.8mm mains tracks, 1.8mm DC bus).
* Complete printable etch masks (`.pdf`, `.svg`), top assembly overlays, and automated Python layout generators (`build_clean_light_fan.py`, `build_door_security.py`).

---

## 📁 Repository Structure

```text
├── firmware/
│   ├── door_security/       # ESP32-B code (Keypad + RFID + 16x4 LCD + Relay)
│   └── light_controller/    # ESP32-A code (4 Relays + MQ Gas + PIR + Flash Memory)
├── hardware/
│   ├── door_security_pcb/   # KiCad schematics, PCB, and etch masks for ESP32-B
│   └── light_fan_pcb/       # KiCad schematics, PCB, and etch masks for ESP32-A
├── public/                  # Frontend dashboard (HTML5, CSS3, JavaScript, WebSockets)
├── server/
│   ├── certs/               # Self-signed SSL certificate generator for mobile mic
│   ├── config/              # Central configuration (ports, topics, board mappings)
│   ├── db/                  # SQLite database (sql.js)
│   ├── mqtt/                # Embedded Aedes MQTT broker & client
│   ├── routes/              # REST API routes (devices, logs, door PIN, RFID cards)
│   ├── voice/               # Voice engine (Vosk Hindi/English speech recognition)
│   └── server.js            # Main backend server entry point
├── start.sh                 # One-click startup script for macOS/Linux
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites
* **Node.js** (v18 or higher)
* **Arduino IDE / arduino-cli** with ESP32 board support (`esp32:esp32`)

### 1. Server Setup
```bash
# Navigate to the server directory and install dependencies
cd server
npm install

# (Optional) Generate self-signed SSL certs for phone mic access
node certs/generate-cert.js

# (Optional) Download offline voice recognition models (English & Hindi)
node voice/download-models.js
```

### 2. Start the Local Server
```bash
# From the project root:
./start.sh
# Or directly:
node server/server.js
```

Open the dashboard in your browser:
* **Local Web:** `http://localhost:3000`
* **Secure Web (Phone Voice):** `https://localhost:3443`
* **Mobile / Hotspot Access:** `http://<YOUR_LAPTOP_IP>:3000`

### 3. Flash ESP32 Firmware
* **ESP32-A (Lights & Sensors):** Upload `firmware/light_controller/light_controller.ino`
* **ESP32-B (Door Security):** Upload `firmware/door_security/door_security.ino`

---

## 🔒 Security & Offline Resilience
* **No Hardcoded Passwords:** No default backdoors. Passwords and authorized cards are securely managed through the dashboard and flashed into local NVS.
* **Autonomous Recovery:** Relays remember their state after blackouts. Keypads and RFID readers function continuously without network dependencies.
