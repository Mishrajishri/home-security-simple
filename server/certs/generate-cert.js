/*
 * Generate a self-signed HTTPS certificate for local network access.
 * Run once:  node server/certs/generate-cert.js
 */
const selfsigned = require('selfsigned');
const fs = require('fs');
const path = require('path');
const os = require('os');

// Auto-detect local IP addresses for SubjectAltName
function getLocalIPs() {
  const ips = ['127.0.0.1'];
  const interfaces = os.networkInterfaces();
  for (const name of Object.keys(interfaces)) {
    for (const iface of interfaces[name]) {
      if (iface.family === 'IPv4' && !iface.internal) {
        ips.push(iface.address);
      }
    }
  }
  return ips;
}

async function main() {
  const localIPs = getLocalIPs();
  console.log('[Cert] Detected local IPs:', localIPs.join(', '));

  const altNames = [
    { type: 2, value: 'localhost' },
    ...localIPs.map(ip => ({ type: 7, ip })),
  ];

  const attrs = [{ name: 'commonName', value: 'Home-Auto-Server' }];
  const opts = {
    keySize: 2048,
    days: 365 * 10,
    algorithm: 'sha256',
    extensions: [{ name: 'subjectAltName', altNames }],
  };

  console.log('[Cert] Generating self-signed certificate...');
  const pems = await selfsigned.generate(attrs, opts);

  const certDir = __dirname;
  fs.writeFileSync(path.join(certDir, 'server.cert'), pems.cert);
  fs.writeFileSync(path.join(certDir, 'server.key'), pems.private);

  console.log('[Cert] ✅ Certificate generated!');
  console.log(`  → ${path.join(certDir, 'server.cert')}`);
  console.log(`  → ${path.join(certDir, 'server.key')}`);
  console.log('[Cert] On your phone, open the HTTPS URL and tap "Advanced → Proceed" to accept.');
}

main().catch(err => {
  console.error('[Cert] ❌ Error:', err.message);
  process.exit(1);
});
