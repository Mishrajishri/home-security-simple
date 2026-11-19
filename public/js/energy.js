/*
 * ═══════════════════════════════════════════════════════════
 *  VidyutRakshak — Theme Manager (Day / Night)
 * ═══════════════════════════════════════════════════════════
 */
const Theme = (() => {
  const KEY = 'vr-theme'; // localStorage key
  let current = localStorage.getItem(KEY) || 'dark';

  function apply(theme, animate = false) {
    current = theme;
    const root = document.documentElement;

    if (animate) {
      // Ripple-like flash for satisfying switch feel
      root.style.transition = 'none';
      root.setAttribute('data-theme', theme);
      requestAnimationFrame(() => { root.style.transition = ''; });
    } else {
      root.setAttribute('data-theme', theme);
    }

    // Update button UI
    const icon  = document.getElementById('theme-icon');
    const label = document.getElementById('theme-label');
    if (icon && label) {
      if (theme === 'light') {
        icon.textContent  = '🌙';
        label.textContent = 'Night';
      } else {
        icon.textContent  = '☀️';
        label.textContent = 'Day';
      }
    }

    localStorage.setItem(KEY, theme);
  }

  function toggle() {
    apply(current === 'dark' ? 'light' : 'dark', true);
  }

  function init() {
    // Apply saved theme immediately (no animation on first load)
    apply(current, false);

    // Wire up button
    const btn = document.getElementById('theme-toggle');
    if (btn) btn.addEventListener('click', toggle);
  }

  return { init, toggle, apply };
})();

// Init theme ASAP (before DOMContentLoaded to avoid flash)
document.addEventListener('DOMContentLoaded', () => Theme.init());

/*
 * ═══════════════════════════════════════════════════════════
 *  VidyutRakshak — Energy Tracker
 *  Computes live energy savings metrics from device states
 *  Vigyan Mela 2026
 * ═══════════════════════════════════════════════════════════
 */

const Energy = (() => {
  const WATT_PER_LIGHT   = 10;   // watts per LED bulb
  const CO2_PER_WH       = 0.82; // grams CO2 per Wh (India grid avg)
  const RUPEES_PER_KWH   = 8;    // INR per kWh (avg India)
  const MAX_LIGHTS       = 4;    // total lights in project

  let sessionStartMs = Date.now();
  let savedWhAccum   = 0; // Wh saved (lights that are OFF contribute)
  let lastTickMs     = Date.now();
  let lastLightsOn   = 0;

  const TIPS = [
    "Smart home automation can reduce household electricity consumption by 20–40% by eliminating standby power waste and automating lights based on occupancy.",
    "Turning off just ONE 10W LED bulb for 6 hours saves 60 Wh — enough to charge your phone 5 times!",
    "India wastes ₹30,000+ crore per year on electricity from lights left on in empty rooms. Automation stops this completely.",
    "The average Indian household can save ₹3,000–₹6,000 per year using smart automation. That's free school books!",
    "RFID door security removes the need for keys — no more wasted power standing at the door, no locksmith fees.",
    "Voice control (आवाज़ नियंत्रण) means you never have to walk to a switch. This encourages turning off lights more.",
    "Gas sensor alerts prevent disasters before they happen — saving lives, property, and energy used in emergency services.",
    "Motion sensors ensure lights are ONLY on when someone is actually in the room — a simple change with huge impact.",
    "One ESP32 microcontroller controls 4 lights + 2 sensors using just 0.5W total. The smarts cost almost nothing.",
    "CO₂ emissions from India's electricity: every kWh saved reduces your carbon footprint by ~820 grams."
  ];

  let tipIndex = 0;

  function init() {
    document.getElementById('btn-next-tip')?.addEventListener('click', nextTip);
    document.getElementById('close-banner')?.addEventListener('click', () => {
      document.getElementById('energy-banner').style.display = 'none';
    });
    setInterval(tick, 5000);
    setInterval(updateClock, 1000);
    updateClock();
    updateDisplay();
  }

  function nextTip() {
    tipIndex = (tipIndex + 1) % TIPS.length;
    const el = document.getElementById('tip-text');
    if (el) {
      el.style.opacity = '0';
      setTimeout(() => {
        el.textContent = TIPS[tipIndex];
        el.style.opacity = '1';
      }, 200);
    }
  }

  function updateClock() {
    const el = document.getElementById('header-time');
    if (!el) return;
    const now = new Date();
    el.textContent = now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }

  function tick() {
    const devices = (typeof Devices !== 'undefined') ? Devices.devices : [];
    const lights = devices.filter(d => d.type === 'light');
    const lightsOnCount = lights.filter(d => d.status === 'on').length;
    const lightsOffCount = lights.filter(d => d.status !== 'on').length;

    // Update device counts
    const onEl  = document.getElementById('lights-on-count');
    const offEl = document.getElementById('lights-off-count');
    if (onEl)  onEl.textContent  = lightsOnCount;
    if (offEl) offEl.textContent = lightsOffCount;

    // Security status
    const doors = devices.filter(d => d.type === 'door');
    const anyUnlocked = doors.some(d => d.status === 'unlocked');
    const anyAlert = devices.some(d => d.status === 'alert' || d.status === 'detected');
    const secEl = document.getElementById('security-status-text');
    if (secEl) {
      if (anyAlert) { secEl.textContent = '⚠️ Alert'; secEl.style.color = 'var(--danger)'; }
      else if (anyUnlocked) { secEl.textContent = '🔓 Unlocked'; secEl.style.color = 'var(--warning)'; }
      else { secEl.textContent = '✓ Secure'; secEl.style.color = 'var(--energy)'; }
    }

    // Energy math — tick every 5 seconds
    const nowMs = Date.now();
    const deltaHours = (nowMs - lastTickMs) / 3600000;
    lastTickMs = nowMs;

    // Power consumed by active lights
    const activeW   = lightsOnCount * WATT_PER_LIGHT;
    const maxW      = MAX_LIGHTS * WATT_PER_LIGHT;
    const savedW    = maxW - activeW;              // watts saved vs all-on
    const whUsed    = activeW * deltaHours * 1000; // mWh → convert below
    const whSaved   = savedW * deltaHours;         // Wh saved this tick

    savedWhAccum += whSaved;
    lastLightsOn = lightsOnCount;

    updateDisplay();
  }

  function updateDisplay() {
    const devices = (typeof Devices !== 'undefined') ? Devices.devices : [];
    const lightsOn = devices.filter(d => d.type === 'light' && d.status === 'on').length;
    const activeW  = lightsOn * WATT_PER_LIGHT;
    const sessionHours = (Date.now() - sessionStartMs) / 3600000;
    const whConsumed   = activeW * sessionHours;
    const co2Saved     = Math.round(savedWhAccum * CO2_PER_WH);
    const moneySaved   = ((savedWhAccum / 1000) * RUPEES_PER_KWH).toFixed(2);

    // Header counter
    const savedEl = document.getElementById('energy-saved-val');
    if (savedEl) savedEl.textContent = savedWhAccum.toFixed(1);

    // Stats bar
    const co2StatEl = document.getElementById('co2-saved-val');
    if (co2StatEl) co2StatEl.textContent = co2Saved;

    // Impact cards
    const estPowerEl = document.getElementById('est-power');
    if (estPowerEl) estPowerEl.textContent = activeW;

    const whConsumedEl = document.getElementById('wh-consumed');
    if (whConsumedEl) whConsumedEl.textContent = whConsumed.toFixed(1);

    const co2El = document.getElementById('co2-not-emitted');
    if (co2El) co2El.textContent = co2Saved;

    const moneyEl = document.getElementById('money-saved');
    if (moneyEl) moneyEl.textContent = moneySaved;

    // Header CO2 badge
    const co2Header = document.getElementById('co2-saved-val');
    if (co2Header) co2Header.textContent = co2Saved;
  }

  return { init, nextTip, updateDisplay };
})();

// Init after DOM ready
document.addEventListener('DOMContentLoaded', () => {
  Energy.init();
});

// Also refresh whenever devices update
document.addEventListener('devices-updated', () => {
  Energy.updateDisplay();
});
