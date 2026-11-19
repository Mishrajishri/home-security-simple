/*
 * ═══════════════════════════════════════════════════════════
 *  VidyutRakshak — Door RFID & Keypad Security Controller (ESP32-B)
 *  RFID-RC522 + 4x4 Membrane Keypad + Relay via MQTT
 *  Vigyan Mela 2026
 * ═══════════════════════════════════════════════════════════
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <SPI.h>
#include <MFRC522.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Keypad.h>
#include <Preferences.h>

// ─── Configuration ─────────────────────────────────────────
const char* WIFI_SSID     = "Shri IOT";
const char* WIFI_PASSWORD = "12345678";

// Laptop IP on the "Shri IOT" WiFi — update if it changes
const char* MQTT_SERVER   = "10.90.241.31";
const int   MQTT_PORT     = 1883;
const char* MQTT_CLIENT   = "esp32-door";

// Door ID
const String DOOR_ID = "1";

// ─── Pin Assignments ─────────────────────────────────────────
const int DOOR_RELAY_PIN = 4;    // Door lock relay (active HIGH, GPIO 4)
const int RED_LED_PIN    = 12;   // Access denied LED (GPIO 12)
const int GREEN_LED_PIN  = 14;   // Access granted LED (GPIO 14)
const int BUZZER_PIN     = 13;   // Buzzer (GPIO 13)

// ─── RFID-RC522 Pins (Custom SPI) ───────────────────────────
//  SDA/SS  = GPIO25
//  SCK     = GPIO33
//  MOSI    = GPIO32
//  MISO    = GPIO35  (input-only pin — perfect for MISO)
//  RST     = GPIO26
const int SS_PIN   = 25;   // SDA/SS
const int RST_PIN  = 26;   // RST (GPIO 26)
const int SCK_PIN  = 33;
const int MOSI_PIN = 32;
const int MISO_PIN = 35;

// ─── 4x4 Keypad Configuration ──────────────────────────────
// Physical Keypad 8-pin ribbon cable (Pin 1 to Pin 8 from left to right):
// Pin 1: Row 1  (Keys 1, 2, 3, A) -> GPIO 23
// Pin 2: Row 2  (Keys 4, 5, 6, B) -> GPIO 19
// Pin 3: Row 3  (Keys 7, 8, 9, C) -> GPIO 18
// Pin 4: Row 4  (Keys *, 0, #, D) -> GPIO 5
// Pin 5: Col 1  (Keys 1, 4, 7, *) -> GPIO 17 (TX2)
// Pin 6: Col 2  (Keys 2, 5, 8, 0) -> GPIO 16 (RX2)
// Pin 7: Col 3  (Keys 3, 6, 9, #) -> GPIO 2
// Pin 8: Col 4  (Keys A, B, C, D) -> GPIO 15
const byte KEYPAD_ROWS = 4;
const byte KEYPAD_COLS = 4;

char keypadKeys[KEYPAD_ROWS][KEYPAD_COLS] = {
  {'1', '2', '3', 'A'},
  {'4', '5', '6', 'B'},
  {'7', '8', '9', 'C'},
  {'*', '0', '#', 'D'}
};

byte rowPins[KEYPAD_ROWS] = {23, 19, 18, 5};
byte colPins[KEYPAD_COLS] = {17, 16, 2, 15};

Keypad keypad = Keypad(makeKeymap(keypadKeys), rowPins, colPins, KEYPAD_ROWS, KEYPAD_COLS);

// Door Keypad PIN (stored in non-volatile flash, synced from server)
Preferences prefs;
String doorPin = ""; // Loaded from Flash memory (NVS). No hardcoded PIN!
String authorizedCards = ""; // Comma-separated authorized RFID UIDs stored in Flash (NVS)

String currentPinInput = "";
unsigned long lastKeyPressTime = 0;
const unsigned long PIN_TIMEOUT = 7000; // 7s inactivity clears PIN input

// ─── Timing ────────────────────────────────────────────────
const unsigned long UNLOCK_DURATION     = 5000;   // Door stays unlocked for 5 sec
const unsigned long HEARTBEAT_INTERVAL  = 30000;
const unsigned long SCAN_COOLDOWN       = 2000;   // Min time between scans
const unsigned long WIFI_RETRY_INTERVAL = 15000;  // Non-blocking WiFi retry every 15s

unsigned long lastWifiRetry = 0;

unsigned long lastHeartbeat = 0;
unsigned long lastScan = 0;
unsigned long lastMqttRetry = 0;
unsigned long lastLcdUpdate = 0;
bool doorLocked = true;
unsigned long unlockTime = 0;

// ─── Objects ───────────────────────────────────────────────
WiFiClient espClient;
PubSubClient mqtt(espClient);
MFRC522 rfid(SS_PIN, RST_PIN);

// ─── LCD I2C Display (SDA=21, SCL=22) ──────────────────────
#define LCD_COLS 16
#define LCD_ROWS  4  // 16x4 LCD Display
LiquidCrystal_I2C lcd27(0x27, LCD_COLS, LCD_ROWS);
LiquidCrystal_I2C lcd3F(0x3F, LCD_COLS, LCD_ROWS);
LiquidCrystal_I2C* lcd = &lcd27;
bool lcdFound = false;

// MQTT topics
String cmdTopic;
String statusTopic;
String rfidTopic;
String keypadTopic;
String pinConfigTopic;
String cardsConfigTopic;

// ─── LCD Helpers (Supports 16x4 Display) ───────────────────
void lcdPrint(const String& line1, const String& line2 = "", const String& line3 = "", const String& line4 = "") {
  if (!lcdFound || lcd == nullptr) return;
  lcd->clear();
  if (line1.length() > 0) {
    lcd->setCursor(0, 0);
    lcd->print(line1.substring(0, LCD_COLS));
  }
  if (line2.length() > 0) {
    lcd->setCursor(0, 1);
    lcd->print(line2.substring(0, LCD_COLS));
  }
  if (line3.length() > 0) {
    lcd->setCursor(0, 2);
    lcd->print(line3.substring(0, LCD_COLS));
  }
  if (line4.length() > 0) {
    lcd->setCursor(0, 3);
    lcd->print(line4.substring(0, LCD_COLS));
  }
}

void lcdStatus() {
  if (!lcdFound || lcd == nullptr) return;
  // If user is actively typing a PIN, do NOT overwrite the display
  if (currentPinInput.length() > 0) return;

  lcd->clear();

  // Row 0: Branding Header
  lcd->setCursor(0, 0);
  lcd->print("VidyutRakshak 26");

  // Row 1: Door Status
  lcd->setCursor(0, 1);
  String line1 = doorLocked ? "Door: [LOCKED]  " : "Door: [UNLOCKED]";
  lcd->print(line1.substring(0, LCD_COLS));

  // Row 2: Network / Cloud Status
  lcd->setCursor(0, 2);
  String line2;
  if (WiFi.status() == WL_CONNECTED) {
    line2 = mqtt.connected() ? "Net: Online OK  " : "WiFi OK (No MQTT)";
  } else {
    line2 = "Net: OFFLINE OK ";
  }
  lcd->print(line2.substring(0, LCD_COLS));

  // Row 3: Action Hint or IP Address
  lcd->setCursor(0, 3);
  String line3 = (WiFi.status() == WL_CONNECTED) ? ("IP:" + WiFi.localIP().toString()) : "Tap Card or PIN ";
  lcd->print(line3.substring(0, LCD_COLS));
}

// ─── WiFi Setup ────────────────────────────────────────────
void setupWiFi() {
  Serial.print("[WiFi] Connecting to ");
  Serial.println(WIFI_SSID);
  lcdPrint("WiFi: Shri IOT", "Connecting...");

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 25) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WiFi] Connected! IP: " + WiFi.localIP().toString());
    lcdPrint("WiFi Connected!", WiFi.localIP().toString());
    delay(1000);
  } else {
    Serial.println("\n[WiFi] Failed. Will retry non-blockingly.");
    lcdPrint("WiFi Disconnected", "Offline Mode OK");
    delay(1000);
  }
}

// ─── Door Control ──────────────────────────────────────────
void unlockDoor() {
  Serial.println("[Door] UNLOCKED");
  doorLocked = false;
  unlockTime = millis();
  digitalWrite(DOOR_RELAY_PIN, HIGH);
  digitalWrite(GREEN_LED_PIN, HIGH);
  digitalWrite(RED_LED_PIN, LOW);

  digitalWrite(BUZZER_PIN, HIGH);
  delay(100);
  digitalWrite(BUZZER_PIN, LOW);

  if (mqtt.connected()) {
    mqtt.publish(statusTopic.c_str(), "unlocked", true);
  }
  lcdPrint("ACCESS GRANTED", "Door Unlocked", "Hold Time: 5s", "Welcome In!");
  lastLcdUpdate = millis(); // Keep message visible for at least 3 seconds
}

void lockDoor() {
  Serial.println("[Door] LOCKED");
  doorLocked = true;
  unlockTime = 0;
  digitalWrite(DOOR_RELAY_PIN, LOW);
  digitalWrite(GREEN_LED_PIN, LOW);
  digitalWrite(RED_LED_PIN, LOW);
  if (mqtt.connected()) {
    mqtt.publish(statusTopic.c_str(), "locked", true);
  }
  lastLcdUpdate = millis();
  lcdStatus();
}

void accessDenied() {
  Serial.println("[Door] ACCESS DENIED");
  lcdPrint("ACCESS DENIED!", "Invalid Card/PIN", "Try Again", "Security Alert");
  lastLcdUpdate = millis();
  // Flash red LED and buzz 3 times
  for (int i = 0; i < 3; i++) {
    digitalWrite(RED_LED_PIN, HIGH);
    digitalWrite(BUZZER_PIN, HIGH);
    delay(150);
    digitalWrite(RED_LED_PIN, LOW);
    digitalWrite(BUZZER_PIN, LOW);
    delay(150);
  }
  if (mqtt.connected()) {
    mqtt.publish(statusTopic.c_str(), "denied", true);
  }
  lastLcdUpdate = millis();
}

// ─── Keypad Input Handler ──────────────────────────────────
void updatePinDisplay() {
  String masked = "";
  for (unsigned int i = 0; i < currentPinInput.length(); i++) {
    masked += "*";
  }
  lcdPrint("Enter Door PIN:", masked);
}

void verifyPinAndAct() {
  if (currentPinInput.length() == 0) return;

  Serial.printf("[Keypad] PIN submitted: '%s' (len=%d)\n", currentPinInput.c_str(), currentPinInput.length());
  Serial.printf("[Keypad] Stored PIN: '%s' (len=%d)\n", doorPin.c_str(), doorPin.length());

  if (doorPin.length() < 4) {
    Serial.println("[Keypad] ⚠️ Access Denied -> No PIN configured in Flash");
    lcdPrint("No PIN Set!", "Use Dashboard");
    accessDenied();
    currentPinInput = "";
    return;
  }

  bool isAuthorized = (currentPinInput == doorPin);
  Serial.printf("[Keypad] Comparison result: %s\n", isAuthorized ? "MATCH" : "MISMATCH");

  // Publish keypad event to MQTT for dashboard logging
  if (mqtt.connected()) {
    JsonDocument doc;
    doc["pin"] = currentPinInput;
    doc["authorized"] = isAuthorized;
    doc["timestamp"] = millis();
    String payload;
    serializeJson(doc, payload);
    mqtt.publish(keypadTopic.c_str(), payload.c_str());
  }

  if (isAuthorized) {
    Serial.println("[Keypad] PIN Verified -> Access Granted");
    lcdPrint("PIN Verified", "Access Granted");
    unlockDoor();
  } else {
    Serial.println("[Keypad] Invalid PIN -> Access Denied");
    accessDenied();
  }

  currentPinInput = "";
}

void handleKeypad() {
  char key = keypad.getKey();
  if (!key) {
    // Clear buffer if user started typing but walked away
    if (currentPinInput.length() > 0 && millis() - lastKeyPressTime > PIN_TIMEOUT) {
      currentPinInput = "";
      lastLcdUpdate = millis();
      lcdStatus();
    }
    return;
  }

  lastKeyPressTime = millis();

  // DEBUG: Log every keypress
  Serial.printf("[Keypad] Key pressed: '%c' (ASCII: %d)\n", key, (int)key);

  // Audio feedback: short chirp on keypress
  digitalWrite(BUZZER_PIN, HIGH);
  delay(25);
  digitalWrite(BUZZER_PIN, LOW);

  if (key == '#') {
    // '#' is MANUAL SUBMIT (fallback for variable-length PINs)
    verifyPinAndAct();
  } else if (key == '*') {
    // '*' is CLEAR / BACKSPACE
    if (currentPinInput.length() > 0) {
      currentPinInput.remove(currentPinInput.length() - 1);
    }
    if (currentPinInput.length() == 0) {
      lastLcdUpdate = millis();
      lcdStatus();
    } else {
      updatePinDisplay();
    }
  } else {
    // Append digit (max 8 digits)
    if (currentPinInput.length() < 8) {
      currentPinInput += key;
      updatePinDisplay();
    }

    // AUTO-SUBMIT: if entered length matches configured PIN length, verify immediately
    if (doorPin.length() >= 4 && currentPinInput.length() == doorPin.length()) {
      verifyPinAndAct();
    }
  }
}

// ─── RFID Scanning ─────────────────────────────────────────
// Normalize UID to standard format: XX:XX:XX:XX (uppercase with colons)
String normalizeUID(String uid) {
  uid.toUpperCase();
  uid.replace(" ", "");
  uid.replace("-", ":");
  // If no colons but 8+ hex chars, insert colons every 2 chars
  if (uid.indexOf(':') == -1 && uid.length() >= 8) {
    String normalized = "";
    for (int i = 0; i < uid.length(); i += 2) {
      if (i > 0) normalized += ":";
      normalized += uid.substring(i, i + 2);
    }
    return normalized;
  }
  return uid;
}

String getCardUID() {
  String uid = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    if (i > 0) uid += ":";
    if (rfid.uid.uidByte[i] < 0x10) uid += "0";
    uid += String(rfid.uid.uidByte[i], HEX);
  }
  uid.toUpperCase();
  return uid;
}

// ─── Local RFID Card Verification (Works 100% Offline) ─────
bool isCardAuthorizedLocally(const String& uid) {
  String normalizedScannedUID = normalizeUID(uid);
  if (normalizedScannedUID.length() == 0 || authorizedCards.length() == 0) {
    Serial.printf("[RFID Auth] FAIL: uid.empty=%d, cards.empty=%d\n", normalizedScannedUID.length() == 0, authorizedCards.length() == 0);
    return false;
  }

  Serial.printf("[RFID Auth] Checking UID: '%s' (normalized: '%s')\n", uid.c_str(), normalizedScannedUID.c_str());
  Serial.printf("[RFID Auth] Authorized list: '%s'\n", authorizedCards.c_str());

  int start = 0;
  while (start < authorizedCards.length()) {
    int end = authorizedCards.indexOf(',', start);
    if (end == -1) end = authorizedCards.length();
    String storedUid = authorizedCards.substring(start, end);
    storedUid.trim();
    String normalizedStoredUID = normalizeUID(storedUid);
    Serial.printf("[RFID Auth] Comparing with stored: '%s' (normalized: '%s')\n", storedUid.c_str(), normalizedStoredUID.c_str());
    if (normalizedStoredUID.length() > 0 && normalizedStoredUID.equalsIgnoreCase(normalizedScannedUID)) {
      Serial.println("[RFID Auth] MATCH FOUND!");
      return true;
    }
    start = end + 1;
  }
  Serial.println("[RFID Auth] NO MATCH");
  return false;
}

void handleRfidScan() {
  if (!rfid.PICC_IsNewCardPresent()) {
    // Debug: Check if antenna detects anything (uncomment for testing)
    // uint8_t irq = rfid.PCD_ReadRegister(MFRC522::ComIrqReg);
    // if (irq & 0x20) Serial.println("[RFID] Antenna IRQ triggered");
    return;
  }

  // Card detected at antenna level!
  Serial.println("[RFID] >>> Card presence detected <<<");

  if (!rfid.PICC_ReadCardSerial()) {
    Serial.println("[RFID] Card detected but failed to read serial - try moving card closer/slower");
    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();
    return;
  }

  if (millis() - lastScan < SCAN_COOLDOWN) {
    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();
    return;
  }
  lastScan = millis();

  String uid = getCardUID();
  Serial.printf("[RFID] Card scanned: %s (size=%d)\n", uid.c_str(), rfid.uid.size);

  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();

  // Debug: show authorized cards list
  if (authorizedCards.length() == 0) {
    Serial.println("[RFID] ⚠️ No authorized cards in flash!");
  }

  bool isAuthorized = isCardAuthorizedLocally(uid);

  // Publish RFID event to MQTT for dashboard logging
  if (mqtt.connected()) {
    JsonDocument doc;
    doc["uid"] = uid;
    doc["authorized"] = isAuthorized;
    doc["timestamp"] = millis();
    String payload;
    serializeJson(doc, payload);
    mqtt.publish(rfidTopic.c_str(), payload.c_str());
  } else {
    Serial.println("[RFID] MQTT offline — processed locally via Flash memory");
  }

  if (isAuthorized) {
    Serial.printf("[RFID] Local Verification: ACCESS GRANTED for %s\n", uid.c_str());
    unlockDoor();
  } else {
    Serial.printf("[RFID] Local Verification: ACCESS DENIED for %s\n", uid.c_str());
    accessDenied();
  }
}

// ─── MQTT Callback ─────────────────────────────────────────
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  message.trim();

  Serial.printf("[MQTT] %s -> %s\n", topic, message.c_str());
  String topicStr = String(topic);

  if (topicStr == cmdTopic) {
    if (message == "unlock") {
      unlockDoor();
    } else if (message == "lock") {
      lockDoor();
    } else if (message == "toggle_lock") {
      if (doorLocked) unlockDoor();
      else lockDoor();
    } else if (message == "deny") {
      accessDenied();
    }
  } else if (topicStr == pinConfigTopic) {
    message.trim();
    if (message.length() >= 4 && message.length() <= 8) {
      doorPin = message;
      prefs.putString("pin", doorPin);
      Serial.printf("[Security] 🔑 New Door PIN received from server: '%s'\n", doorPin.c_str());
      lcdPrint("PIN Synced!", "Code Updated");
      lastLcdUpdate = millis();
    }
  } else if (topicStr == cardsConfigTopic) {
    // Normalize each UID in the comma-separated list
    String normalizedList = "";
    int start = 0;
    while (start < message.length()) {
      int end = message.indexOf(',', start);
      if (end == -1) end = message.length();
      String uid = message.substring(start, end);
      uid.trim();
      if (uid.length() > 0) {
        if (normalizedList.length() > 0) normalizedList += ",";
        normalizedList += normalizeUID(uid);
      }
      start = end + 1;
    }
    authorizedCards = normalizedList;
    prefs.putString("cards", authorizedCards);
    Serial.printf("[Security] 💳 Authorized RFID Cards updated from server: %s\n", authorizedCards.c_str());
    lcdPrint("Cards Synced!", "Security Updated");
    lastLcdUpdate = millis();
  }
}

// ─── MQTT Connect (Non-blocking) ───────────────────────────
void connectMQTT() {
  if (WiFi.status() != WL_CONNECTED) return;
  if (mqtt.connected()) return;

  Serial.printf("[MQTT] Connecting to %s...\n", MQTT_SERVER);
  lcdPrint("MQTT Connecting", String(MQTT_SERVER));

  if (mqtt.connect(MQTT_CLIENT, NULL, NULL,
                   "home/esp32/door/online", 1, true, "false")) {
    Serial.println("[MQTT] Connected!");
    mqtt.publish("home/esp32/door/online", "true", true);
    mqtt.subscribe(cmdTopic.c_str());
    Serial.printf("[MQTT] Subscribed: %s\n", cmdTopic.c_str());
    mqtt.subscribe(pinConfigTopic.c_str());
    Serial.printf("[MQTT] Subscribed: %s\n", pinConfigTopic.c_str());
    mqtt.subscribe(cardsConfigTopic.c_str());
    Serial.printf("[MQTT] Subscribed: %s\n", cardsConfigTopic.c_str());

    String status = doorLocked ? "locked" : "unlocked";
    mqtt.publish(statusTopic.c_str(), status.c_str(), true);
    lcdPrint("MQTT Connected!", "VidyutRakshak OK");
    lastLcdUpdate = millis();
  } else {
    int state = mqtt.state();
    Serial.printf("[MQTT] failed (rc=%d). Retrying later...\n", state);
  }
}

// ─── Setup ─────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  delay(100);

  Serial.println();
  Serial.println("╔════════════════════════════════════════════════════╗");
  Serial.println("║  VidyutRakshak — Door RFID & Keypad (ESP32-B)       ║");
  Serial.println("║  RFID: SPI | Keypad: 4x4 Matrix | LCD: I2C         ║");
  Serial.println("║  WiFi: Shri IOT | Vigyan Mela 2026                 ║");
  Serial.println("╚════════════════════════════════════════════════════╝");

  // Build topic strings
  cmdTopic         = "home/door/" + DOOR_ID + "/command";
  statusTopic      = "home/door/" + DOOR_ID + "/status";
  rfidTopic        = "home/door/" + DOOR_ID + "/rfid";
  keypadTopic      = "home/door/" + DOOR_ID + "/keypad";
  pinConfigTopic   = "home/door/" + DOOR_ID + "/config/pin";
  cardsConfigTopic = "home/door/" + DOOR_ID + "/config/cards";

  // Load saved Door PIN & RFID cards from non-volatile flash memory (NVS)
  prefs.begin("door_sec", false);
  doorPin = prefs.getString("pin", "");
  doorPin.trim();
  if (doorPin.length() >= 4) {
    Serial.printf("[Security] 🔒 Loaded Door PIN from Flash: '%s'\n", doorPin.c_str());
  } else {
    Serial.println("[Security] ⚠️ No PIN configured in Flash. Waiting for sync from dashboard.");
  }

  authorizedCards = prefs.getString("cards", "");
  // Normalize stored cards on boot as well
  if (authorizedCards.length() > 0) {
    String normalizedList = "";
    int start = 0;
    while (start < authorizedCards.length()) {
      int end = authorizedCards.indexOf(',', start);
      if (end == -1) end = authorizedCards.length();
      String uid = authorizedCards.substring(start, end);
      uid.trim();
      if (uid.length() > 0) {
        if (normalizedList.length() > 0) normalizedList += ",";
        normalizedList += normalizeUID(uid);
      }
      start = end + 1;
    }
    authorizedCards = normalizedList;
    prefs.putString("cards", authorizedCards);
    Serial.printf("[Security] 💳 Loaded RFID Cards from Flash: %s\n", authorizedCards.c_str());
  } else {
    Serial.println("[Security] ⚠️ No RFID cards in Flash memory. Waiting for sync from dashboard.");
  }

  // Initialize output pins
  pinMode(DOOR_RELAY_PIN, OUTPUT);
  pinMode(RED_LED_PIN, OUTPUT);
  pinMode(GREEN_LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(DOOR_RELAY_PIN, LOW); // Locked
  digitalWrite(RED_LED_PIN, LOW);
  digitalWrite(GREEN_LED_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);

  // Initialize LCD I2C
  Wire.begin(21, 22);
  delay(100);

  byte detectedAddr = 0;
  for (byte address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    if (Wire.endTransmission() == 0) {
      if (address == 0x27 || address == 0x3F || detectedAddr == 0) {
        detectedAddr = address;
      }
    }
  }

  if (detectedAddr == 0x3F) {
    lcd = &lcd3F;
    lcdFound = true;
  } else {
    lcd = &lcd27;
    lcdFound = true;
  }

  lcd->init();
  lcd->backlight();
  lcdPrint("VidyutRakshak 26", "Door Security", "RFID + Keypad", "System Ready");
  delay(1200);

  // Keypad self-test: print keymap for verification
  Serial.println("[Keypad] Keymap configuration:");
  for (int r = 0; r < KEYPAD_ROWS; r++) {
    String rowStr = "";
    for (int c = 0; c < KEYPAD_COLS; c++) {
      rowStr += keypadKeys[r][c];
      rowStr += " ";
    }
    Serial.printf("[Keypad] Row %d (GPIO %d): %s\n", r, rowPins[r], rowStr.c_str());
  }
  for (int c = 0; c < KEYPAD_COLS; c++) {
    Serial.printf("[Keypad] Col %d -> GPIO %d\n", c, colPins[c]);
  }
  Serial.println("[Keypad] Press keys to test mapping...");

  // Initialize RFID SPI
  SPI.begin(SCK_PIN, MISO_PIN, MOSI_PIN);
  pinMode(RST_PIN, OUTPUT);
  digitalWrite(RST_PIN, LOW);
  delay(50);
  digitalWrite(RST_PIN, HIGH);
  delay(50);
  rfid.PCD_Init();
  delay(100);

  // RFID Debug: Dump version info to verify communication
  Serial.println("[RFID] PCD_Init complete. Dumping version info:");
  rfid.PCD_DumpVersionToSerial();

  // Optional: Self-test (uncomment if needed)
  // bool selfTest = rfid.PCD_PerformSelfTest();
  // Serial.printf("[RFID] Self-test: %s\n", selfTest ? "PASS" : "FAIL");

  setupWiFi();
  mqtt.setServer(MQTT_SERVER, MQTT_PORT);
  mqtt.setCallback(mqttCallback);
  mqtt.setBufferSize(512);
  connectMQTT();
  lcdStatus();
}

// ─── Loop ──────────────────────────────────────────────────
void loop() {
  // Reconnect Wi-Fi non-blockingly if lost (does not freeze keypad or RFID)
  if (WiFi.status() != WL_CONNECTED) {
    if (millis() - lastWifiRetry > WIFI_RETRY_INTERVAL) {
      lastWifiRetry = millis();
      Serial.println("[WiFi] Reconnecting in background...");
      WiFi.disconnect();
      WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    }
  }

  if (WiFi.status() == WL_CONNECTED && !mqtt.connected()) {
    if (millis() - lastMqttRetry > 6000) {
      lastMqttRetry = millis();
      connectMQTT();
    }
  } else if (mqtt.connected()) {
    mqtt.loop();
  }

  // 1. Scan for 4x4 Keypad input
  handleKeypad();

  // 2. Scan for RFID cards
  handleRfidScan();

  // 4. Auto-lock after unlock duration (5 seconds)
  if (!doorLocked && unlockTime > 0 && (millis() - unlockTime > UNLOCK_DURATION)) {
    Serial.println("[Door] Auto-locking...");
    lockDoor();
  }

  // 5. Refresh LCD periodically (only when idle / not typing a PIN)
  if (currentPinInput.length() == 0 && (millis() - lastLcdUpdate > 3000)) {
    lastLcdUpdate = millis();
    lcdStatus();
  }

  // 6. Heartbeat status publish
  if (millis() - lastHeartbeat > HEARTBEAT_INTERVAL) {
    lastHeartbeat = millis();
    String status = doorLocked ? "locked" : "unlocked";
    if (mqtt.connected()) {
      mqtt.publish(statusTopic.c_str(), status.c_str(), true);
    }
  }
}
