const aedes = require('aedes')();
const net = require('net');

let brokerServer = null;

function startBroker(port = 1883) {
  return new Promise((resolve) => {
    brokerServer = net.createServer(aedes.handle);

    brokerServer.once('error', (err) => {
      if (err.code === 'EADDRINUSE') {
        console.log(`[MQTT Broker] Port ${port} in use — using existing MQTT broker.`);
        resolve(false);
      } else {
        console.error('[MQTT Broker] Error:', err.message);
        resolve(false);
      }
    });

    brokerServer.listen(port, '0.0.0.0', () => {
      console.log(`[MQTT Broker] 🚀 Embedded Aedes broker listening on port ${port}`);
      resolve(true);
    });

    aedes.on('client', (client) => {
      console.log(`[MQTT Broker] 📡 Client connected: ${client ? client.id : 'unknown'}`);
    });

    aedes.on('clientDisconnect', (client) => {
      console.log(`[MQTT Broker] 🔌 Client disconnected: ${client ? client.id : 'unknown'}`);
    });
  });
}

function stopBroker() {
  if (brokerServer) {
    brokerServer.close();
  }
}

module.exports = { startBroker, stopBroker };
