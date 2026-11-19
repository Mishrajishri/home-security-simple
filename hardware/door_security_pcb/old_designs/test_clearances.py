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

# All pads with net assignments:
pads = {}

# ESP_L
esp_l_nets = [
    (1, "+3.3V"), (2, "NC"), (3, "NC"), (4, "NC"),
    (5, "RFID_MISO"), (6, "RFID_MOSI"), (7, "RFID_SCK"), (8, "RFID_SDA_SS"),
    (9, "RFID_RST"), (10, "NC"), (11, "LED_GREEN"), (12, "LED_RED"),
    (13, "BUZZER"), (14, "GND"), (15, "+5V")
]
for pnum, net in esp_l_nets:
    pads[f"ESP_L_{pnum}"] = ((30.0, 26.0 + (pnum-1)*2.54), net)

# ESP_R
esp_r_nets = [
    (1, "KEYPAD_R1"), (2, "I2C_SCL"), (3, "NC"), (4, "NC"),
    (5, "I2C_SDA"), (6, "KEYPAD_R2"), (7, "KEYPAD_R3"), (8, "KEYPAD_R4"),
    (9, "KEYPAD_C1"), (10, "KEYPAD_C2"), (11, "DOOR_RELAY"), (12, "KEYPAD_C3"),
    (13, "KEYPAD_C4"), (14, "GND"), (15, "NC")
]
for pnum, net in esp_r_nets:
    pads[f"ESP_R_{pnum}"] = ((55.4, 26.0 + (pnum-1)*2.54), net)

# RFID
rfid_nets = [
    (1, "+3.3V"), (2, "RFID_RST"), (3, "GND"), (4, "NC"),
    (5, "RFID_MISO"), (6, "RFID_MOSI"), (7, "RFID_SCK"), (8, "RFID_SDA_SS")
]
for pnum, net in rfid_nets:
    pads[f"RFID_{pnum}"] = ((10.0, 26.0 + (pnum-1)*2.54), net)

# KEYPAD
keypad_nets = [
    (1, "KEYPAD_R1"), (2, "KEYPAD_R2"), (3, "KEYPAD_R3"), (4, "KEYPAD_R4"),
    (5, "KEYPAD_C1"), (6, "KEYPAD_C2"), (7, "KEYPAD_C3"), (8, "KEYPAD_C4")
]
for pnum, net in keypad_nets:
    pads[f"KEYPAD_{pnum}"] = ((75.0, 26.0 + (pnum-1)*2.54), net)

# LCD
lcd_nets = [(1, "GND"), (2, "+5V"), (3, "I2C_SDA"), (4, "I2C_SCL")]
for pnum, net in lcd_nets:
    pads[f"LCD_{pnum}"] = ((48.0, 11.0 + (pnum-1)*2.54), net)

# Bottom Connectors:
# J_LEDS at (11.0, 78.0)
pads["LEDS_1"] = ((11.0, 78.0), "LED_GREEN")
pads["LEDS_2"] = ((13.54, 78.0), "LED_RED")
pads["LEDS_3"] = ((16.08, 78.0), "GND")

# J_BUZZER at (21.0, 78.0)
pads["BUZZER_1"] = ((21.0, 78.0), "BUZZER")
pads["BUZZER_2"] = ((23.54, 78.0), "GND")

# J_POWER at (33.0, 78.0)
# Phoenix Terminal Block: Pad 1 (+5V at 33.0), Pad 2 (GND at 38.08)
pads["POWER_1"] = ((33.0, 78.0), "+5V")
pads["POWER_2"] = ((38.08, 78.0), "GND")

# J_RELAY at (45.0, 78.0)
# Pad 1 (+5V at 45.0), Pad 2 (DOOR_RELAY at 47.54), Pad 3 (GND at 50.08)
pads["RELAY_1"] = ((45.0, 78.0), "+5V")
pads["RELAY_2"] = ((47.54, 78.0), "DOOR_RELAY")
pads["RELAY_3"] = ((50.08, 78.0), "GND")

# Mounting holes M3 at (5, 5), (80, 5), (5, 90), (80, 90) - radius 1.6mm + margin
m_holes = [(5.0, 5.0), (80.0, 5.0), (5.0, 90.0), (80.0, 90.0)]

from test_full_zero_drc_champion import tracks

pad_radius = 1.85 / 2.0  # 0.925 mm
track_widths = {
    "GND": 1.2, "+5V": 1.2, "+3.3V": 1.0,
    "RFID_MISO": 0.85, "RFID_MOSI": 0.85, "RFID_SCK": 0.85, "RFID_SDA_SS": 0.85, "RFID_RST": 0.85,
    "I2C_SCL": 0.85, "I2C_SDA": 0.85,
    "DOOR_RELAY": 0.85, "BUZZER": 0.85, "LED_GREEN": 0.85, "LED_RED": 0.85,
    "KEYPAD_R1": 0.85, "KEYPAD_R2": 0.85, "KEYPAD_R3": 0.85, "KEYPAD_R4": 0.85,
    "KEYPAD_C1": 0.85, "KEYPAD_C2": 0.85, "KEYPAD_C3": 0.85, "KEYPAD_C4": 0.85
}

violations = []
for p_name, (pos, p_net) in pads.items():
    for t_net, segs in tracks.items():
        if p_net == t_net:
            continue  # same net can connect to pad
        tw = track_widths.get(t_net, 0.85)
        for s in segs:
            d = dist_point_to_segment(pos, s[0], s[1])
            clearance = d - pad_radius - (tw / 2.0)
            if clearance < 0.25:  # KiCad standard clearance limit is 0.25mm
                violations.append((p_name, pos, p_net, t_net, s, clearance))

print(f"==================================================")
print(f" PAD CLEARANCE VIOLATIONS (<0.25mm): {len(violations)}")
print(f"==================================================")
for v in violations:
    print(f"VIOLATION: Pad {v[0]} [{v[2]}] at {v[1]} too close to track {v[3]} {v[4]} (clearance: {v[5]:.3f} mm)")

hole_violations = []
for h in m_holes:
    for t_net, segs in tracks.items():
        tw = track_widths.get(t_net, 0.85)
        for s in segs:
            d = dist_point_to_segment(h, s[0], s[1])
            clearance = d - 1.6 - (tw / 2.0)  # 3.2mm hole radius = 1.6mm
            if clearance < 0.5:
                hole_violations.append((h, t_net, s, clearance))

print(f"MOUNTING HOLE CLEARANCE VIOLATIONS: {len(hole_violations)}")
for hv in hole_violations:
    print(f"HOLE VIOLATION at {hv[0]} near {hv[1]} {hv[2]}: {hv[3]:.3f} mm")
