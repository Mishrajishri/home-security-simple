const mqtt = require('mqtt');
const config = require('../config/config');
const db = require('../db/database');

let client = null;
let wsBroadcast = null; // Will be set by server.js

// ─── ESP32 online/offline tracking ─────────────────────────
const espStatus = {};  // { boardId: { online: bool, lastSeen: Date, name: string } }

// Snapshot of light states captured the moment ESP32 goes OFFLINE.
// Used to restore on the next power-on, preventing the race where
// the ESP32's own boot-up "all off" status reports overwrite the DB
// before the restore command fires.
const lightStateSnapshot = {};  // { 'light-1': 'on', 'light-2': 'off', ... }

function initEspTracking() {
  for (const [boardId, board] of Object.entries(config.ESP_BOARDS || {})) {
    espStatus[boardId] = { online: false, lastSeen: null, name: board.name };
  }
}

function connect(broadcastFn) {
  wsBroadcast = broadcastFn;

  client = mqtt.connect(config.MQTT_BROKER, config.MQTT_OPTIONS);

  client.on('connect', () => {
    console.log('[MQTT] Connected to broker at', config.MQTT_BROKER);

    // Subscribe to all device status and RFID topics
    const subs = [
      config.TOPICS.SUB_LIGHT_STATUS,
      config.TOPICS.SUB_DOOR_STATUS,
      config.TOPICS.SUB_RFID_EVENT,
      config.TOPICS.SUB_KEYPAD_EVENT,
      config.TOPICS.SUB_SENSOR_DATA,
      config.TOPICS.SUB_ESP_ONLINE,
    ];
    client.subscribe(subs, (err) => {
      if (err) {
        console.error('[MQTT] Subscribe error:', err);
      } else {
        console.log('[MQTT] Subscribed to:', subs.join(', '));
        // After subscribing, restore light states in case ESP32 was already
        // online before the server started (e.g. server restarted mid-session)
        restoreLightStates('server_connect');
        syncDoorPinToMqtt();
        syncRfidCardsToMqtt();
      }
    });

    // Broadcast MQTT connection status to frontend
    if (wsBroadcast) {
      wsBroadcast({ type: 'mqtt_status', data: { connected: true } });
    }
  });

  client.on('message', (topic, message) => {
    const payload = message.toString();
    console.log(`[MQTT] ${topic} → ${payload}`);

    // Parse topic: home/<type>/<id>/<action>
    const parts = topic.split('/');
    if (parts.length < 4) return;

    const deviceType = parts[1]; // 'light', 'door', 'sensor', or 'esp32'
    const deviceId = `${deviceType}-${parts[2]}`; // e.g. 'light-1'
    const action = parts[3]; // 'status', 'rfid', 'data', or 'online'

    // Handle ESP32 board online/offline messages
    if (deviceType === 'esp32' && action === 'online') {
      handleEspOnline(parts[2], payload);
      return;
    }

    // Any message from a device → mark its ESP32 board as alive
    touchEspBoard(deviceId);

    if (action === 'status') {
      handleStatusUpdate(deviceId, payload);
    } else if (action === 'rfid') {
      handleRfidEvent(deviceId, payload);
    } else if (action === 'keypad') {
      handleKeypadEvent(deviceId, payload);
    } else if (action === 'data') {
      handleSensorData(deviceId, payload);
    }
  });

  // Start ESP32 timeout checker
  initEspTracking();
  setInterval(checkEspTimeouts, 15000);

  client.on('error', (err) => {
    console.error('[MQTT] Error:', err.message);
  });

  client.on('offline', () => {
    console.log('[MQTT] Client went offline');
    if (wsBroadcast) {
      wsBroadcast({ type: 'mqtt_status', data: { connected: false } });
    }
  });

  client.on('reconnect', () => {
    console.log('[MQTT] Reconnecting...');
  });

  return client;
}

// ─── Handle device status updates ──────────────────────────────────
function handleStatusUpdate(deviceId, status) {
  // Update database
  const result = db.updateDeviceStatus(deviceId, status);

  // Log the event
  db.addLogEntry(deviceId, 'status_change', { status });

  // Get full device info for broadcast
  const device = db.getDevice(deviceId);

  // Broadcast to all connected WebSocket clients
  if (wsBroadcast) {
    wsBroadcast({
      type: 'device_update',
      data: device || { id: deviceId, status },
    });

    wsBroadcast({
      type: 'log',
      data: {
        device_id: deviceId,
        event_type: 'status_change',
        details: JSON.stringify({ status }),
        timestamp: new Date().toISOString(),
      },
    });
  }
}

// ─── Handle RFID scan events ───────────────────────────────────────
function handleRfidEvent(deviceId, payload) {
  let data;
  try {
    data = JSON.parse(payload);
  } catch {
    data = { uid: payload };
  }

  const uid = data.uid || 'unknown';
  console.log(`[RFID] Card scanned: ${uid} at device ${deviceId}`);

  // Check if the card is authorized in DB (or verified locally on ESP32)
  const card = db.getRfidCard(uid);
  const isAuthorized = card ? (card.is_authorized === 1) : !!data.authorized;

  // Log the RFID event
  db.addLogEntry(deviceId, 'rfid_scan', {
    uid,
    owner: card ? card.owner_name : 'Unknown',
    authorized: isAuthorized,
  });

  if (isAuthorized) {
    console.log(`[RFID] Access GRANTED for ${card ? card.owner_name : 'Authorized Card'} (${uid})`);
    db.updateDeviceStatus(deviceId, 'unlocked');
  } else {
    console.log(`[RFID] Access DENIED for uid ${uid}`);
  }

  // Broadcast to frontend
  if (wsBroadcast) {
    wsBroadcast({
      type: 'rfid_event',
      data: {
        device_id: deviceId,
        uid,
        owner: card ? card.owner_name : 'Unknown',
        authorized: isAuthorized,
        timestamp: new Date().toISOString(),
      },
    });

    wsBroadcast({
      type: 'device_update',
      data: db.getDevice(deviceId),
    });

    wsBroadcast({
      type: 'log',
      data: {
        device_id: deviceId,
        event_type: 'rfid_scan',
        details: JSON.stringify({
          uid,
          owner: card ? card.owner_name : 'Unknown',
          authorized: isAuthorized,
        }),
        timestamp: new Date().toISOString(),
      },
    });
  }
}

// ─── Handle Keypad PIN entry events ────────────────────────────────
function handleKeypadEvent(deviceId, payload) {
  let data;
  try {
    data = JSON.parse(payload);
  } catch {
    data = { pin: payload, authorized: false };
  }

  const isAuthorized = !!data.authorized;
  console.log(`[Keypad] Door ${deviceId} PIN entered: ${isAuthorized ? 'ACCESS GRANTED' : 'ACCESS DENIED'}`);

  // Log to database
  db.addLogEntry(deviceId, 'keypad_entry', {
    authorized: isAuthorized,
    status: isAuthorized ? 'Granted' : 'Denied',
  });

  if (isAuthorized) {
    db.updateDeviceStatus(deviceId, 'unlocked');
  }

  // Broadcast to frontend
  if (wsBroadcast) {
    wsBroadcast({
      type: 'log',
      data: {
        device_id: deviceId,
        event_type: 'keypad_entry',
        details: JSON.stringify({ action: isAuthorized ? 'PIN Access Granted' : 'PIN Access Denied' }),
        timestamp: new Date().toISOString(),
      },
    });

    if (isAuthorized) {
      wsBroadcast({
        type: 'device_update',
        data: db.getDevice(deviceId),
      });
    }
  }
}

// ─── Handle sensor data (gas, motion) ──────────────────────────────
function handleSensorData(deviceId, payload) {
  let data;
  try {
    data = JSON.parse(payload);
  } catch {
    data = { raw: payload };
  }

  console.log(`[Sensor] ${deviceId} data:`, data);

  // Determine status string for the device
  let status = 'normal';
  if (data.gas_ppm !== undefined) {
    // Gas sensor
    status = data.alert ? 'alert' : 'normal';
  } else if (data.motion !== undefined) {
    // Motion sensor
    status = data.motion ? 'detected' : 'clear';
  }

  // Update device status in DB
  db.updateDeviceStatus(deviceId, status);

  // Log sensor reading
  db.addLogEntry(deviceId, 'sensor_data', data);

  // Broadcast to frontend
  if (wsBroadcast) {
    wsBroadcast({
      type: 'device_update',
      data: db.getDevice(deviceId),
    });

    // Send the raw sensor data for live display
    wsBroadcast({
      type: 'sensor_data',
      data: { device_id: deviceId, ...data, timestamp: new Date().toISOString() },
    });

    // If gas alert, send a special alert message
    if (data.alert) {
      wsBroadcast({
        type: 'alert',
        data: {
          device_id: deviceId,
          level: 'danger',
          message: `⚠️ Gas level critical: ${data.gas_ppm} PPM!`,
          timestamp: new Date().toISOString(),
        },
      });
    }

    // If motion detected, send alert
    if (data.motion) {
      wsBroadcast({
        type: 'alert',
        data: {
          device_id: deviceId,
          level: 'warning',
          message: `🚶 Motion detected!`,
          timestamp: new Date().toISOString(),
        },
      });
    }

    wsBroadcast({
      type: 'log',
      data: {
        device_id: deviceId,
        event_type: 'sensor_data',
        details: JSON.stringify(data),
        timestamp: new Date().toISOString(),
      },
    });
  }
}

// ─── Publish a command to a device ─────────────────────────────────
function publishCommand(topic, payload) {
  if (!client || !client.connected) {
    console.error('[MQTT] Cannot publish — not connected');
    return false;
  }
  const payloadStr = typeof payload === 'string' ? payload : JSON.stringify(payload);
  client.publish(topic, payloadStr, { qos: 1 }, (err) => {
    if (err) {
      console.error('[MQTT] Publish error:', err);
    } else {
      console.log(`[MQTT] Published: ${topic} → ${payloadStr}`);
    }
  });
  return true;
}

// ─── ESP32 board online/offline handling ───────────────────
function handleEspOnline(boardId, payload) {
  const isOnline = payload.toLowerCase() === 'true' || payload === '1';
  if (!espStatus[boardId]) {
    espStatus[boardId] = { online: false, lastSeen: null, name: boardId };
  }

  const prev = espStatus[boardId].online;
  espStatus[boardId].online = isOnline;
  espStatus[boardId].lastSeen = new Date();

  if (prev !== isOnline) {
    const label = espStatus[boardId].name || boardId;
    console.log(`[ESP32] ${label}: ${isOnline ? '🟢 ONLINE' : '🔴 OFFLINE'}`);
    broadcastEspStatus();

    if (boardId === 'lights') {
      if (!isOnline) {
        // ESP32 just went OFFLINE — take a snapshot of current light states
        // from DB NOW, before the ESP32 has a chance to overwrite them.
        captureLightSnapshot();
      } else {
        // ESP32 came back ONLINE — restore from snapshot (not DB)
        restoreLightStates('esp_online');
      }
    }
  }
}

// ─── Capture a snapshot of current light states from DB ────
function captureLightSnapshot() {
  const board = config.ESP_BOARDS['lights'];
  if (!board) return;
  const lightDevices = board.devices.filter(id => id.startsWith('light-'));
  for (const deviceId of lightDevices) {
    const device = db.getDevice(deviceId);
    if (device) {
      lightStateSnapshot[deviceId] = device.status === 'on' ? 'on' : 'off';
    }
  }
  console.log('[ESP32] 📸 Light state snapshot saved:', lightStateSnapshot);
}

// ─── Re-push saved light states to the ESP32 ───────────────
function restoreLightStates(reason = 'server_connect') {
  // Delay lets the ESP32 finish its MQTT subscription setup before we publish.
  // Commands are published with retain=true so even if ESP32 subscribes
  // slightly late, the broker will deliver the retained message immediately.
  setTimeout(() => {
    if (!client || !client.connected) {
      console.warn('[ESP32] ⚠️  Cannot restore — server not connected to broker');
      return;
    }

    const board = config.ESP_BOARDS['lights'];
    if (!board) return;

    const lightDevices = board.devices.filter(id => id.startsWith('light-'));
    let restored = 0;

    for (const deviceId of lightDevices) {
      let state;

      if (reason === 'esp_online' && lightStateSnapshot[deviceId] !== undefined) {
        // Use the pre-captured snapshot (taken when ESP32 went offline)
        // so that the ESP32's own boot "all off" reports don't corrupt it.
        state = lightStateSnapshot[deviceId];
      } else {
        // Fallback: read from DB (used on server_connect)
        const device = db.getDevice(deviceId);
        if (!device) continue;
        state = device.status === 'on' ? 'on' : 'off';
      }

      const lightNum = deviceId.replace('light-', '');
      const commandTopic = `home/light/${lightNum}/command`;

      // retain:true — broker holds the message so ESP32 receives it
      // the moment it subscribes, regardless of exact timing
      client.publish(commandTopic, state, { qos: 1, retain: true }, (err) => {
        if (err) console.error(`[ESP32] Restore publish error for ${deviceId}:`, err);
      });
      console.log(`[ESP32] 🔄 Restored ${deviceId} → ${state} (reason: ${reason})`);
      restored++;
    }

    // Clear snapshot after use
    for (const key of Object.keys(lightStateSnapshot)) delete lightStateSnapshot[key];

    if (restored > 0) {
      console.log(`[ESP32] ✅ State restore complete: ${restored} light(s) re-synced`);
      db.addLogEntry('system', 'state_restore', { board: 'lights', restored, reason });
    }
  }, 2000);
}

// Mark the ESP32 board that owns this device as alive
function touchEspBoard(deviceId) {
  for (const [boardId, board] of Object.entries(config.ESP_BOARDS || {})) {
    if (board.devices.includes(deviceId)) {
      if (!espStatus[boardId]) {
        espStatus[boardId] = { online: false, lastSeen: null, name: board.name };
      }
      const wasOffline = !espStatus[boardId].online;
      espStatus[boardId].online = true;
      espStatus[boardId].lastSeen = new Date();
      if (wasOffline) {
        console.log(`[ESP32] ${board.name}: 🟢 ONLINE (heartbeat)`);
        broadcastEspStatus();
      }
      break;
    }
  }
}

// Periodic check: mark boards offline if no message received within timeout
function checkEspTimeouts() {
  const timeout = config.ESP_TIMEOUT || 60000;
  const now = Date.now();
  for (const [boardId, status] of Object.entries(espStatus)) {
    if (status.online && status.lastSeen) {
      const elapsed = now - status.lastSeen.getTime();
      if (elapsed > timeout) {
        status.online = false;
        console.log(`[ESP32] ${status.name}: 🔴 OFFLINE (timeout: ${(elapsed/1000).toFixed(0)}s)`);
        broadcastEspStatus();
      }
    }
  }
}

// Broadcast ESP32 status to all WebSocket clients
function broadcastEspStatus() {
  if (!wsBroadcast) return;
  const boards = {};
  for (const [boardId, status] of Object.entries(espStatus)) {
    boards[boardId] = {
      name: status.name,
      online: status.online,
      lastSeen: status.lastSeen ? status.lastSeen.toISOString() : null,
    };
  }
  wsBroadcast({ type: 'esp_status', data: boards });
}

function getEspStatus() {
  const boards = {};
  for (const [boardId, status] of Object.entries(espStatus)) {
    boards[boardId] = {
      name: status.name,
      online: status.online,
      lastSeen: status.lastSeen ? status.lastSeen.toISOString() : null,
    };
  }
  return boards;
}

function publishPinConfig(pin) {
  if (!client || !client.connected) return false;
  client.publish('home/door/1/config/pin', pin.toString(), { qos: 1, retain: true }, (err) => {
    if (err) console.error('[MQTT] Failed to publish door PIN config:', err);
    else console.log('[MQTT] 🔑 Synced door PIN to ESP32:', pin);
  });
  return true;
}

function syncDoorPinToMqtt() {
  const pin = db.getDoorPin();
  if (pin) {
    publishPinConfig(pin);
  } else {
    console.log('[MQTT] ⚠️ No door PIN configured in database yet.');
  }
}

function publishRfidCardsConfig() {
  if (!client || !client.connected) return false;
  const cards = db.getRfidCards().filter(c => c.is_authorized === 1);
  const uids = cards.map(c => c.uid.trim()).join(',');
  client.publish('home/door/1/config/cards', uids, { qos: 1, retain: true }, (err) => {
    if (err) console.error('[MQTT] Failed to publish RFID cards config:', err);
    else console.log('[MQTT] 💳 Synced authorized RFID cards to ESP32:', uids || '(none)');
  });
  return true;
}

function syncRfidCardsToMqtt() {
  publishRfidCardsConfig();
}

module.exports = {
  connect,
  publishCommand,
  publishPinConfig,
  publishRfidCardsConfig,
  getEspStatus,
};
