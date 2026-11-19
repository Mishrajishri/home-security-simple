const express = require('express');
const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');
const cors = require('cors');
const { WebSocketServer } = require('ws');
const config = require('./config/config');
const db = require('./db/database');
const mqttClient = require('./mqtt/mqttClient');

async function startServer() {
  // Initialize database (async for sql.js)
  await db.init();
  db.seedDefaultDevices();

  // ─── Express Setup ───────────────────────────────────────
  const app = express();
  app.use(cors());
  app.use(express.json());

  // Serve frontend static files
  app.use(express.static(path.join(__dirname, '..', 'public')));

  // Mount API routes
  const devicesRouter = require('./routes/devices');
  const commandsRouter = require('./routes/commands');
  const logsRouter = require('./routes/logs');

  app.use('/api/devices', devicesRouter);
  app.use('/api/devices', commandsRouter);
  app.use('/api/logs', logsRouter);

  // Health check
  app.get('/api/health', (req, res) => {
    res.json({ status: 'ok', uptime: process.uptime(), timestamp: new Date().toISOString() });
  });

  // Fallback: serve index.html for any non-API route
  app.get('*', (req, res) => {
    if (!req.path.startsWith('/api')) {
      res.sendFile(path.join(__dirname, '..', 'public', 'index.html'));
    }
  });

  // ─── HTTP Server ─────────────────────────────────────────
  const httpServer = http.createServer(app);

  // ─── HTTPS Server (for phone mic access) ─────────────────
  let httpsServer = null;
  if (fs.existsSync(config.CERT_PATH) && fs.existsSync(config.KEY_PATH)) {
    const sslOptions = {
      key: fs.readFileSync(config.KEY_PATH),
      cert: fs.readFileSync(config.CERT_PATH),
    };
    httpsServer = https.createServer(sslOptions, app);
    console.log('[Server] HTTPS enabled with self-signed certificate');
  } else {
    console.warn('[Server] ⚠️  No SSL cert found. Run: node server/certs/generate-cert.js');
    console.warn('[Server]    Phone mic access requires HTTPS.');
  }

  // ─── WebSocket Server (device updates) ───────────────────
  const wsClients = new Set();
  const deviceWss = new WebSocketServer({ noServer: true });

  deviceWss.on('connection', (ws) => {
    wsClients.add(ws);
    console.log(`[WS] Client connected (total: ${wsClients.size})`);
    const devices = db.getDevices();
    const espBoards = mqttClient.getEspStatus();
    ws.send(JSON.stringify({ type: 'init', data: { devices, espBoards } }));

    ws.on('close', () => {
      wsClients.delete(ws);
      console.log(`[WS] Client disconnected (total: ${wsClients.size})`);
    });
    ws.on('error', (err) => {
      console.error('[WS] Error:', err.message);
      wsClients.delete(ws);
    });
  });

  function broadcast(message) {
    const data = JSON.stringify(message);
    for (const client of wsClients) {
      if (client.readyState === 1) client.send(data);
    }
  }

  // Make broadcast available to route handlers
  app.set('broadcast', broadcast);

  // ─── Voice WebSocket ─────────────────────────────────────
  const voiceEngine = require('./voice/voiceEngine');
  const voiceHandler = require('./voice/voiceHandler');
  const voiceReady = voiceEngine.init();
  const voiceWss = new WebSocketServer({ noServer: true });

  if (voiceReady) {
    voiceHandler.setup(voiceWss, broadcast);
    console.log('[Voice] 🎙️  Voice assistant ready on /voice');
  } else {
    console.warn('[Voice] ⚠️  Voice assistant disabled (models not loaded)');
  }

  // ─── Setup HTTP Upgrades ─────────────────────────────────
  function handleUpgrade(request, socket, head) {
    if (request.url === '/ws') {
      deviceWss.handleUpgrade(request, socket, head, (ws) => {
        deviceWss.emit('connection', ws, request);
      });
    } else if (request.url === '/voice' && voiceReady) {
      voiceWss.handleUpgrade(request, socket, head, (ws) => {
        voiceWss.emit('connection', ws, request);
      });
    } else {
      socket.destroy();
    }
  }

  httpServer.on('upgrade', handleUpgrade);
  if (httpsServer) {
    httpsServer.on('upgrade', handleUpgrade);
  }

  // ─── Embedded MQTT Broker ───────────────────────────────
  const broker = require('./mqtt/broker');
  await broker.startBroker(1883);

  // ─── Connect MQTT ────────────────────────────────────────
  mqttClient.connect(broadcast);

  // ─── Start Listening ─────────────────────────────────────
  httpServer.listen(config.PORT, '0.0.0.0', () => {
    console.log('');
    console.log('  ╔══════════════════════════════════════════════╗');
    console.log('  ║     🏠 Home Automation Dashboard Server      ║');
    console.log('  ╠══════════════════════════════════════════════╣');
    console.log(`  ║  HTTP:       http://localhost:${config.PORT}          ║`);
    if (httpsServer) {
      console.log(`  ║  HTTPS:      https://localhost:${config.HTTPS_PORT}         ║`);
    }
    console.log(`  ║  WebSocket:  ws://localhost:${config.PORT}/ws         ║`);
    console.log(`  ║  Voice:      ws://localhost:${config.PORT}/voice      ║`);
    console.log('  ╚══════════════════════════════════════════════╝');
    console.log('');

    // Print network URLs for phone access
    const os = require('os');
    const ifaces = os.networkInterfaces();
    for (const name of Object.keys(ifaces)) {
      for (const iface of ifaces[name]) {
        if (iface.family === 'IPv4' && !iface.internal) {
          console.log(`  📱 Phone access (HTTP):  http://${iface.address}:${config.PORT}`);
          if (httpsServer) {
            console.log(`  📱 Phone access (HTTPS): https://${iface.address}:${config.HTTPS_PORT}  ← use this for voice`);
          }
        }
      }
    }
    console.log('');
  });

  if (httpsServer) {
    httpsServer.listen(config.HTTPS_PORT, '0.0.0.0');
  }

  // Graceful shutdown
  const shutdown = () => {
    console.log('\n[Server] Shutting down...');
    broker.stopBroker();
    db.close();
    httpServer.close();
    if (httpsServer) httpsServer.close();
    process.exit(0);
  };
  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
}

startServer().catch((err) => {
  console.error('[Server] Failed to start:', err);
  process.exit(1);
});
