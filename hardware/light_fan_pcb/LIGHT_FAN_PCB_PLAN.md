# VidyutRakshak — 4-Channel Relay, Fan & Sensors Controller PCB (ESP32-A)
## Master Engineering Plan: Real-Life DIY Acid Etch Edition (Ultra-Thick Traces & 45° Miters)

**Project:** VidyutRakshak Home Automation & Security (Vigyan Mela 2026)  
**Target Board:** ESP32-A (4-Channel Relays for 3 Lights + 1 Fan, MQ Gas & PIR Motion Sensors)  
**Fabrication Process:** Single-Layer DIY Acid Etch (`B.Cu` Bottom Copper + 2 Top Wire Jumpers)  
**Board Dimensions:** $92.0\text{ mm} \times 96.0\text{ mm}$ (Standard $4 \times 5\text{ inch}$ copper clad friendly)  
**Etching Goal:** Ultra-resilient against over-etching/undercutting, zero toner peeling, zero acid traps.

---

## 1. Practical Real-Life DIY Etching Rules (Strictly Enforced)

1. **Ultra-Thick Copper Traces (No Thin Tracks):**
   - **AC Mains Phase Tracks:** **$2.80\text{ mm}$ ($110\text{ mil}$)**. Can easily be tinned with thick solder to carry up to $10\text{ A}$ continuously without heating.
   - **DC +5V & GND Power Bus:** **$1.80\text{ mm}$ ($71\text{ mil}$)**. Ultra-low resistance, rock-solid ground reference, zero brownout sag.
   - **Logic & Control Signals (GPIO to Transistors):** **$1.00\text{ mm}$ ($40\text{ mil}$)**. Heavy-duty traces that will never break, peel, or dissolve even if ferric chloride is slightly over-concentrated.
   - **LED & Divider Branches:** **$0.80\text{ mm}$ ($31.5\text{ mil}$)** minimum (strictly no sub-0.8mm hair tracks).

2. **Zero Sharp 90° Right-Angle Turns (100% 45° Mitered Chamfers):**
   - **Toner Transfer Protection:** $90^\circ$ corners flake or lift off glossy paper during hot ironing. Every track direction change uses **two $45^\circ$ bends ($135^\circ$ obtuse corners)**.
   - **Acid Etch Protection:** Eliminates "acid traps" (where ferric chloride pools in sharp corners and eats away the track) and prevents corner erosion.

3. **Real-Life Mechanical & Hand-Drill Logic:**
   - **Hand-Drill Center Dimples:** All pads have **$0.40\text{ mm}$ pilot center holes**. The hand drill bit automatically centers itself and never wanders across the copper.
   - **Giant Annular Rings:**
     - Wire solder pads: **$3.60\text{ mm}$ outer pad**, **$1.40\text{ mm}$ drill hole** (fits 18–20 AWG Indian electrical wires like Finolex/Havells effortlessly with huge copper contact area).
     - Relay contact pads: **$3.20\text{ mm}$ outer pad**, **$1.40\text{ mm}$ drill** (perfect for Songle SRD flat rectangular metal pins).
     - Transistor, Resistor, Diode pads: **$2.20\text{ mm}$ outer pad**, **$1.00\text{ mm}$ drill**.
   - **Tear-Dropping / Fillets:** Smooth copper fillets where tracks enter round pads so pads never tear off under mechanical wire vibration.

4. **Real-Life Component & Enclosure Usability:**
   - **ESP32 Micro-USB Port Access:** The ESP32 is oriented with its Micro-USB port pointing directly at the bottom edge, with a $15\text{ mm}$ clear corridor so standard USB cables plug in without hitting other parts.
   - **Wi-Fi Antenna Keepout:** The ESP32 meandered PCB antenna sits at the top margin with a **$100\%$ copper keepout (zero copper underneath)**, preserving full 2.4GHz Wi-Fi range through walls.
   - **Soldering Iron Tip Clearance:** Resistors, diodes, and transistors maintain $\ge 3.0\text{ mm}$ physical clearance from relay plastic cases, so your soldering iron tip never accidentally melts a relay or header.
   - **Safe Screw Clearance:** Mounting hole `H4` $(85, 90)$ is **$>13\text{ mm}$ away** from the nearest AC mains pad (`OUT4` at $X=72, Y=88$), preventing metal mounting screws or washers from shorting 230V to chassis.
   - **Zip-Tie Strain Relief:** Two pairs of $2.5\text{ mm}$ holes anchor heavy mains and power wires with small cable ties.

---

## 2. Complete Circuit Diagram

### A. Channel Relay Driver Architecture (Channels 1–4)

```
                            +5V DC Power Rail
                                  │
                                  ├──[+] C1 (470µF 25V Bulk Electrolytic)
                                  ├──[+] C2 (100nF Ceramic Decoupling)
                                  │
                      ┌───────────┴───────────┐
                      │                       │
               ┌──────┴──────┐         ┌──────┴──────┐
               │ 1N4007 (D1) │         │ Relay Coil  │
               │   Cathode   │         │ (SRD-05VDC) │
               │      ▲      │         │             │
               │   Anode     │         │   Pin 2     │
               └──────┬──────┘         └──────┬──────┘
                      │                       │
                      ├───────────────────────┤
                      │                       │
                 ┌────┴────┐                  │
                 │ 1kΩ R5  │                  │
                 └────┬────┘                  │
                      │                       │
                 ┌────┴────┐                  │
                 │ LED1    │                  │
                 │ (Red)   │                  │
                 └────┬────┘                  │
                      │                       │
                      └───────────┬───────────┘
                                  │
                                  ▼ Collector (Pin 1)
ESP32 GPIO ────[ 1kΩ R1 ]───┬───► BC337-40 (Q1)
 (23,22,19,18)              │     │ Emitter (Pin 3)
                            │     ▼
                        ┌───┴───┐ GND
                        │ 10kΩ  │
                        │ R_pd1 │ (Anti-Chatter Pull-down)
                        └───┬───┘
                            │
                           GND

════════════════════════════════════════════════════════════════════════
            GALVANIC SAFETY ISOLATION BARRIER (≥ 4.5 mm CREEPAGE)
════════════════════════════════════════════════════════════════════════

AC Mains Phase In (AC_IN) ───────► [ COM ]
                                      \
                                       \──► [ NO ] ───────► OUT1..OUT4 (To Appliance)
```

### B. Signal Conditioning (Gas Sensor & PIR Sensor)

1. **MQ-2 Gas Sensor Input (Safe 3.3V Scaling):**
   ```
   MQ-2 Analog Output (A0: 0 - 5.0V) ─────[ 10kΩ ]─────┬─────► ESP32 GPIO 34 (0 - 3.33V)
                                                       │
                                                   ┌───┴───┐
                                                   │ 20kΩ  │
                                                   └───┬───┘
                                                       ▼
                                                      GND
   ```
2. **PIR Sensor Input:** HC-SR501 `OUT` $\to$ ESP32 GPIO 27 (native 3.3V logic).

---

## 3. Complete Bill of Materials (BOM)

| RefDes | Component Description | Footprint / Package | Qty | Real-Life Function |
| :--- | :--- | :--- | :---: | :--- |
| **U1** | 2x 1x15 Female Socket Headers | `PinHeader_1x15_P2.54mm_Vertical` | 2 | ESP32 DevKit V1 Sockets ($25.4\text{ mm}$ pitch) |
| **K1 - K4** | 5V SPDT Sugar Cube Relay | `Relay_SPDT_SANYOU_SRD_Series_Form_C` | 4 | Songle SRD-05VDC-SL-C ($1.4\text{ mm}$ drill contact pads) |
| **Q1 - Q4** | NPN Bipolar Transistor | `TO-92_Inline` (Pinout: 1=C, 2=B, 3=E) | 4 | **BC337-40** ($800\text{ mA}$ rating, runs cool) |
| **D1 - D4** | 1A 1000V Rectifier Diode | `D_DO-41_SOD81_P10.16mm_Horizontal`| 4 | **1N4007** Back-EMF flyback clamp |
| **R1 - R4** | $1\,\text{k}\Omega$ Resistor ($0.25\text{W}$) | `R_Axial_DIN0207_P7.62mm_Horizontal` | 4 | Transistor base drive current limiter |
| **R_pd1 - R_pd4**| $10\,\text{k}\Omega$ Resistor ($0.25\text{W}$) | `R_Axial_DIN0207_P7.62mm_Horizontal` | 4 | Base pull-down to GND (stops boot chattering) |
| **LED1 - LED4** | 3mm Red LEDs | `LED_D3.0mm` | 4 | Active channel indicators |
| **R5 - R8** | $1\,\text{k}\Omega$ Resistor ($0.25\text{W}$) | `R_Axial_DIN0207_P7.62mm_Horizontal` | 4 | Channel indicator LED resistors |
| **C1** | $470\,\mu\text{F} / 25\text{V}$ Radial Electrolytic | `CP_Radial_D8.0mm_P3.50mm` | 1 | Bulk power reservoir; eliminates brownout reboots |
| **C2** | $100\,\text{nF}$ Ceramic Disc Cap | `C_Disc_D5.0mm_W2.5mm_P5.00mm` | 1 | High-frequency logic decoupling |
| **R_div1** | $10\,\text{k}\Omega$ Resistor ($0.25\text{W}$) | `R_Axial_DIN0207_P7.62mm_Horizontal` | 1 | Voltage divider upper leg |
| **R_div2** | $20\,\text{k}\Omega$ Resistor ($0.25\text{W}$) | `R_Axial_DIN0207_P7.62mm_Horizontal` | 1 | Voltage divider lower leg |
| **LED_PWR** | 3mm Green LED + $1\,\text{k}\Omega$ | `LED_D3.0mm` + `R_Axial_DIN0207` | 1+1 | 5V DC Power indicator |
| **LED_STAT**| 3mm Blue LED + $470\,\Omega$ | `LED_D3.0mm` + `R_Axial_DIN0207` | 1+1 | Wi-Fi / MQTT Status indicator (GPIO 2) |
| **PAD_AC_IN** | Heavy-Duty Solder Pad | Pad: $\varnothing 3.6\text{ mm}$, Drill: $1.4\text{ mm}$ | 1 | 230V AC Mains Phase Input |
| **PAD_OUT1-4**| Heavy-Duty Solder Pads | Pad: $\varnothing 3.6\text{ mm}$, Drill: $1.4\text{ mm}$ | 4 | Switched Outputs (Light 1, 2, 3, Fan) |
| **PAD_5V, GND**| Heavy-Duty Solder Pads | Pad: $\varnothing 3.6\text{ mm}$, Drill: $1.4\text{ mm}$ | 2 | 5V DC Power Input (+5V, GND) |
| **J_GAS** | 1x4 Male Header | `PinHeader_1x04_P2.54mm_Vertical` | 1 | MQ Gas Sensor (`VCC`, `GND`, `A0`, `NC`) |
| **J_PIR** | 1x3 Male Header | `PinHeader_1x03_P2.54mm_Vertical` | 1 | PIR Sensor (`VCC`, `OUT`, `GND`) |
| **JMP_5V, JMP_GND**| Top-Side Wire Jumpers | `Jumper_P10.16mm` or solid wire | 2 | Top wire links for wide, straight bottom copper |
| **H1 - H4** | 4x M3 Mounting Holes | `MountingHole_3.2mm_M3` | 4 | Corner mounting holes ($3.2\text{ mm}$ drill) |
| **ST1 - ST4** | Zip-Tie Strain Relief Holes | $2.5\text{ mm}$ unplated drill holes | 4 | Mechanically clamps wires to PCB |

---

## 4. Physical Floorplan & Zoning

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ [H1] (5,5)          [ Wi-Fi Antenna Keepout Zone ]               [H2] (87,5)│
│                                              │                              │
│   [J_GAS] (Top-Left)                         │  [Relay 1] (SRD-05VDC)       │
│   ├── 5V, GND, GPIO 34                       │  ├── Driven by GPIO 23       │
│   └── (R_div1/R_div2)                        │  └── Switched Output: OUT1   │
│                                              │                              │
│   [J_PIR] (Mid-Left)                         │  [Relay 2] (SRD-05VDC)       │
│   └── 5V, GND, GPIO 27                       │  ├── Driven by GPIO 22       │
│                                              │  └── Switched Output: OUT2   │
│           ┌──────────────────────┐  [Q1..Q4] │                              │
│           │                      │  [D1..D4] │  [Relay 3] (SRD-05VDC)       │
│           │   ESP32 DevKit V1    │  [R1..R8] │  ├── Driven by GPIO 19       │
│           │       (30-pin)       │  [LED1-4] │  └── Switched Output: OUT3   │
│           │                      │           │                              │
│           │                      │  (Driver  │  [Relay 4] (SRD-05VDC)       │
│           │                      │   Zone)   │  ├── Driven by GPIO 18       │
│           │                      │           │  └── Switched Output: OUT4   │
│           │  [Micro-USB Port]    │           │      (Ceiling Fan)           │
│           └──────────┬───────────┘           │                              │
│                      ▼                       │ ══════ SAFETY BARRIER ══════ │
│             (Open Cable Access)              │                              │
│   [C1: 470µF] [C2: 100nF]                    │                              │
│   [LED_PWR]   [LED_STAT]                     │                              │
│                                              │                              │
│   [+5V_IN] [GND_IN]                          │ [AC_IN] [OUT1] [OUT2][OUT3][OUT4]
│   (5V DC Adapter)                            │ (X=46)  (X=52.5)  (X=59)  (X=65.5) (X=72)
│   (X=14, Y=88)  (X=20, Y=88)                 │ (Clearance to H4 > 13mm!)
│   (Strain Relief: ST1, ST2)                  │ (Strain Relief: ST3, ST4)
│ [H3] (5,91)                                                      [H4] (87,91)│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Trace Routing & DIY Etching Specifications

| Parameter | Value | Advantage for Hand Acid Etching |
| :--- | :--- | :--- |
| **AC Load Tracks** | **$2.80\text{ mm}$** ($110\text{ mil}$) | Extra beefy; can be tinned with solder for 10A current capacity |
| **DC Power / GND Tracks** | **$1.80\text{ mm}$** ($71\text{ mil}$) | Solid low-impedance bus, zero voltage drop |
| **Logic Signal Tracks** | **$1.00\text{ mm}$** ($40\text{ mil}$) | Ultra-durable; won't over-etch or break |
| **Corner Geometry** | **Strictly 45° Miters (No 90° turns)** | Eliminates toner lift during ironing and prevents acid traps |
| **Creepage (AC to DC)** | **$\ge 4.50\text{ mm}$** ($177\text{ mil}$)| Continuous galvanic isolation barrier |
| **Clearance (DC to DC)** | **$\ge 0.70\text{ mm}$** ($27.5\text{ mil}$)| Prevents solder and toner bridging |
| **Wire Solder Pads** | **$\varnothing 3.60\text{ mm}$ outer, $1.40\text{ mm}$ hole** | Large copper area prevents pad peeling; fits multi-strand wire |
| **Relay Contact Pads** | **$\varnothing 3.20\text{ mm}$ outer, $1.40\text{ mm}$ hole** | Accommodates flat rectangular relay pins |
| **Component Lead Pads** | **$\varnothing 2.20\text{ mm}$ outer, $1.00\text{ mm}$ hole** | Plenty of copper for hand-soldering resistors and diodes |
| **Drill Center Dimples** | **$0.40\text{ mm}$ pilot hole** | Prevents hand drill bits from wandering |

---

## 6. Firmware Pin Mapping (`light_controller.ino`)

The firmware array in [`firmware/light_controller/light_controller.ino`](file:///Users/shreyansh/@nirman/firmware/light_controller/light_controller.ino#L24) matches the physical top-to-bottom layout:

```cpp
// ─── Relay Pin Assignments ─────────────────────────────────
// Top-to-bottom physical order on ESP32 right-side header:
// Relay 1 (Light 1) = GPIO 23
// Relay 2 (Light 2) = GPIO 22
// Relay 3 (Light 3) = GPIO 19
// Relay 4 (Fan)     = GPIO 18
const int RELAY_PINS[] = {23, 22, 19, 18};
const int NUM_RELAYS   = 4;

const bool RELAY_ACTIVE_HIGH = true; // Active-HIGH for BC337 discrete driver

// ─── Sensor Pin Assignments ────────────────────────────────
const int GAS_SENSOR_PIN    = 34;  // MQ-2 analog input via 10k/20k voltage divider
const int MOTION_SENSOR_PIN = 27;  // PIR Motion sensor digital input
const int STATUS_LED_PIN    = 2;   // Status LED
```

---

## 7. External AC Mains Wiring Guide

> [!IMPORTANT]
> **Neutral Wire Notice:**  
> The PCB switches the **Phase (Line)** wire only (`AC_IN` to `OUT1..OUT4`).  
> The **Neutral wire from the 230V AC mains does NOT connect to this PCB**.  
> Connect the Neutral wire from mains directly to one terminal of each light bulb and the ceiling fan using an external wire junction / terminal block in your switchboard.
