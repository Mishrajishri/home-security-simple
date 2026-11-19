import math

def dist_point_to_segment(p, a, b):
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    if dx == 0 and dy == 0:
        return math.hypot(p[0]-a[0], p[1]-a[1])
    t = ((p[0]-a[0])*dx + (p[1]-a[1])*dy) / (dx*dx + dy*dy)
    t = max(0.0, min(1.0, t))
    closest = (a[0] + t*dx, a[1] + t*dy)
    return math.hypot(p[0]-closest[0], p[1]-closest[1])

def ccw(A, B, C):
    return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])

def intersect(p1, p2, p3, p4):
    if p1 == p3 or p1 == p4 or p2 == p3 or p2 == p4: return False
    return (ccw(p1, p3, p4) != ccw(p2, p3, p4)) and (ccw(p1, p2, p3) != ccw(p1, p2, p4))

# Let's define the updated tracks:
tracks = {
    # 1. RFID SPI
    "RFID_MISO":   [((10.0, 36.16), (30.0, 36.16))],
    "RFID_MOSI":   [((10.0, 38.70), (30.0, 38.70))],
    "RFID_SCK":    [((10.0, 41.24), (30.0, 41.24))],
    "RFID_SDA_SS": [((10.0, 43.78), (30.0, 43.78))],

    # 2. +3.3V
    "+3.3V": [
        ((30.0, 26.0), (30.0, 24.0)),
        ((30.0, 24.0), (10.0, 24.0)),
        ((10.0, 24.0), (10.0, 26.0))
    ],

    # 3. RFID_RST
    "RFID_RST": [
        ((30.0, 46.32), (34.0, 46.32)),
        ((34.0, 46.32), (34.0, 21.0)),
        ((34.0, 21.0), (8.0, 21.0)),
        ((8.0, 21.0), (8.0, 28.54)),
        ((8.0, 28.54), (10.0, 28.54))
    ],

    # 4. Keypad 4x4
    "KEYPAD_R1": [((55.4, 26.0), (75.0, 26.0))],
    "KEYPAD_R2": [
        ((55.4, 38.70), (58.0, 38.70)),
        ((58.0, 38.70), (58.0, 28.54)),
        ((58.0, 28.54), (75.0, 28.54))
    ],
    "KEYPAD_R3": [
        ((55.4, 41.24), (60.5, 41.24)),
        ((60.5, 41.24), (60.5, 31.08)),
        ((60.5, 31.08), (75.0, 31.08))
    ],
    "KEYPAD_R4": [
        ((55.4, 43.78), (63.0, 43.78)),
        ((63.0, 43.78), (63.0, 33.62)),
        ((63.0, 33.62), (75.0, 33.62))
    ],
    "KEYPAD_C1": [
        ((55.4, 46.32), (65.5, 46.32)),
        ((65.5, 46.32), (65.5, 36.16)),
        ((65.5, 36.16), (75.0, 36.16))
    ],
    "KEYPAD_C2": [
        ((55.4, 48.86), (68.0, 48.86)),
        ((68.0, 48.86), (68.0, 38.70)),
        ((68.0, 38.70), (75.0, 38.70))
    ],
    "KEYPAD_C3": [
        ((55.4, 53.94), (70.5, 53.94)),
        ((70.5, 53.94), (70.5, 41.24)),
        ((70.5, 41.24), (75.0, 41.24))
    ],
    "KEYPAD_C4": [
        ((55.4, 56.48), (73.0, 56.48)),
        ((73.0, 56.48), (73.0, 43.78)),
        ((73.0, 43.78), (75.0, 43.78))
    ],

    # 5. LCD I2C
    "I2C_SCL": [
        ((48.0, 18.62), (48.0, 28.54)),
        ((48.0, 28.54), (55.4, 28.54))
    ],
    "I2C_SDA": [
        ((48.0, 16.08), (45.5, 16.08)),
        ((45.5, 16.08), (45.5, 36.16)),
        ((45.5, 36.16), (55.4, 36.16))
    ],

    # 6. Actuators
    "LED_GREEN": [
        ((30.0, 51.40), (11.0, 51.40)),
        ((11.0, 51.40), (11.0, 78.0))
    ],
    "LED_RED": [
        ((30.0, 53.94), (13.54, 53.94)),
        ((13.54, 53.94), (13.54, 78.0))
    ],
    "BUZZER": [
        ((30.0, 56.48), (21.0, 56.48)),
        ((21.0, 56.48), (21.0, 78.0))
    ],
    "DOOR_RELAY": [
        ((55.4, 51.40), (47.54, 51.40)),
        ((47.54, 51.40), (47.54, 78.0))
    ],

    # 7. +5V Distribution
    "+5V": [
        # From J_LCD Pad 2 down central corridor at X=43.0 to Y=74.0
        ((48.0, 13.54), (43.0, 13.54)),
        ((43.0, 13.54), (43.0, 74.0)),
        # +5V bus along Y=74.0 connecting ESP_L Pin 15 (30.0), J_POWER Pad 1 (33.0), and J_RELAY Pad 1 (45.0)
        ((30.0, 61.56), (30.0, 74.0)),
        ((30.0, 74.0), (45.0, 74.0)),
        ((33.0, 74.0), (33.0, 78.0)),
        ((45.0, 74.0), (45.0, 78.0))
    ],

    # 8. GND Distribution
    "GND": [
        # Main GND rail along Y=85.0 (well clear of H3 at (5, 90))
        ((6.0, 85.0), (53.0, 85.0)),
        # Left trunk up along X=6.0 from Y=85.0 to Y=12.0
        ((6.0, 85.0), (6.0, 12.0)),
        # Clear of H1 at (5, 5): turns to X=8.5, Y=8.5
        ((6.0, 12.0), (8.5, 9.5)),
        ((8.5, 9.5), (8.5, 6.0)),
        ((8.5, 6.0), (48.0, 6.0)),
        ((48.0, 6.0), (48.0, 11.0)),
        # RFID GND
        ((6.0, 31.08), (10.0, 31.08)),
        # Drops from bottom components into GND rail
        ((16.08, 78.0), (16.08, 85.0)),
        ((23.54, 78.0), (23.54, 85.0)),
        ((30.0, 59.02), (25.5, 59.02)),
        ((25.5, 59.02), (25.5, 85.0)),
        ((38.08, 78.0), (38.08, 85.0)),
        ((50.08, 78.0), (50.08, 85.0)),
        # ESP_R Pin 14 (55.4, 59.02) exits west to 53.0 (clearing Pin 15 at 55.4, 61.56) and drops to 85.0
        ((55.4, 59.02), (53.0, 59.02)),
        ((53.0, 59.02), (53.0, 85.0))
    ]
}

# 1. Check crossings
crossings = []
names = list(tracks.keys())
for i in range(len(names)):
    for j in range(i+1, len(names)):
        n1, n2 = names[i], names[j]
        for s1 in tracks[n1]:
            for s2 in tracks[n2]:
                if intersect(s1[0], s1[1], s2[0], s2[1]):
                    crossings.append((n1, s1, n2, s2))

print(f"TOTAL CROSSINGS: {len(crossings)}")
for c in crossings:
    print(f"CROSSING: {c[0]} vs {c[2]}")

# 2. Check pad clearances
from test_clearances import pads, m_holes, pad_radius, track_widths
violations = []
for p_name, (pos, p_net) in pads.items():
    for t_net, segs in tracks.items():
        if p_net == t_net: continue
        tw = track_widths.get(t_net, 0.85)
        for s in segs:
            d = dist_point_to_segment(pos, s[0], s[1])
            clearance = d - pad_radius - (tw / 2.0)
            if clearance < 0.25:
                violations.append((p_name, pos, p_net, t_net, s, clearance))

print(f"PAD CLEARANCE VIOLATIONS: {len(violations)}")
for v in violations:
    print(f"VIOLATION: {v[0]} [{v[2]}] near {v[3]} (clearance: {v[5]:.3f} mm)")

hole_violations = []
for h in m_holes:
    for t_net, segs in tracks.items():
        tw = track_widths.get(t_net, 0.85)
        for s in segs:
            d = dist_point_to_segment(h, s[0], s[1])
            clearance = d - 1.6 - (tw / 2.0)
            if clearance < 0.5:
                hole_violations.append((h, t_net, s, clearance))

print(f"MOUNTING HOLE CLEARANCE VIOLATIONS: {len(hole_violations)}")
for hv in hole_violations:
    print(f"HOLE VIOLATION at {hv[0]} near {hv[1]}: {hv[3]:.3f} mm")
