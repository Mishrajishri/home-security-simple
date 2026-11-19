import sys

def ccw(A, B, C):
    return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])

def intersect(p1, p2, p3, p4):
    if p1 == p3 or p1 == p4 or p2 == p3 or p2 == p4: return False
    return (ccw(p1, p3, p4) != ccw(p2, p3, p4)) and (ccw(p1, p2, p3) != ccw(p1, p2, p4))

def check_all(tracks):
    segments = {}
    for name, path_list in tracks.items():
        segments[name] = []
        for pts in path_list:
            for i in range(len(pts)-1):
                segments[name].append((pts[i], pts[i+1]))

    crossings = []
    names = list(tracks.keys())
    for i in range(len(names)):
        for j in range(i+1, len(names)):
            n1, n2 = names[i], names[j]
            for s1 in segments[n1]:
                for s2 in segments[n2]:
                    if intersect(s1[0], s1[1], s2[0], s2[1]):
                        crossings.append((n1, s1, n2, s2))
    return crossings

# Let's test a complete layout:
def test_layout(relay_x, relay_order, pwr_x, pwr_order):
    tracks = {}
    # 1. RFID SPI
    tracks["RFID_MISO"] = [[(10.0, 36.16), (30.0, 36.16)]]
    tracks["RFID_MOSI"] = [[(10.0, 38.70), (30.0, 38.70)]]
    tracks["RFID_SCK"]  = [[(10.0, 41.24), (30.0, 41.24)]]
    tracks["RFID_SDA"]  = [[(10.0, 43.78), (30.0, 43.78)]]

    # 2. +3.3V & RFID_RST
    tracks["+3.3V"] = [[(30.0, 26.0), (30.0, 24.0), (10.0, 24.0), (10.0, 26.0)]]
    tracks["RFID_RST"] = [[(30.0, 46.32), (34.0, 46.32), (34.0, 21.0), (8.0, 21.0), (8.0, 28.54), (10.0, 28.54)]]

    # 3. Keypad 8 concentric lines
    tracks["KEYPAD_R1"] = [[(55.4, 26.0), (75.0, 26.0)]]
    tracks["KEYPAD_R2"] = [[(55.4, 38.70), (58.0, 38.70), (58.0, 28.54), (75.0, 28.54)]]
    tracks["KEYPAD_R3"] = [[(55.4, 41.24), (60.5, 41.24), (60.5, 31.08), (75.0, 31.08)]]
    tracks["KEYPAD_R4"] = [[(55.4, 43.78), (63.0, 43.78), (63.0, 33.62), (75.0, 33.62)]]
    tracks["KEYPAD_C1"] = [[(55.4, 46.32), (65.5, 46.32), (65.5, 36.16), (75.0, 36.16)]]
    tracks["KEYPAD_C2"] = [[(55.4, 48.86), (68.0, 48.86), (68.0, 38.70), (75.0, 38.70)]]
    tracks["KEYPAD_C3"] = [[(55.4, 53.94), (70.5, 53.94), (70.5, 41.24), (75.0, 41.24)]]
    tracks["KEYPAD_C4"] = [[(55.4, 56.48), (73.0, 56.48), (73.0, 43.78), (75.0, 43.78)]]

    # 4. LCD I2C
    tracks["I2C_SCL"] = [[(48.0, 18.62), (48.0, 28.54), (55.4, 28.54)]]
    tracks["I2C_SDA"] = [[(48.0, 16.08), (45.5, 16.08), (45.5, 36.16), (55.4, 36.16)]]

    # 5. LEDs & Buzzer
    tracks["LED_GREEN"] = [[(30.0, 51.40), (11.0, 51.40), (11.0, 78.0)]]
    tracks["LED_RED"]   = [[(30.0, 53.94), (13.54, 53.94), (13.54, 78.0)]]
    tracks["BUZZER"]    = [[(30.0, 56.48), (21.0, 56.48), (21.0, 78.0)]]

    # Let's map Relay pads:
    # relay_order is tuple of 3 names e.g. ('DOOR_RELAY', '+5V', 'GND')
    relay_pads = {}
    for i, sig in enumerate(relay_order):
        relay_pads[sig] = (relay_x + i * 2.54, 78.0)

    # Let's map Power pads:
    # pwr_order is tuple of 2 names e.g. ('+5V', 'GND')
    pwr_pads = {}
    for i, sig in enumerate(pwr_order):
        pwr_pads[sig] = (pwr_x + i * 5.08, 78.0)

    # DOOR_RELAY: from ESP_R Pin 11 (55.4, 51.40) to relay_pads['DOOR_RELAY']
    sig_x = relay_pads['DOOR_RELAY'][0]
    tracks["DOOR_RELAY"] = [[(55.4, 51.40), (sig_x, 51.40), (sig_x, 78.0)]]

    # +5V:
    # 1. ESP_L Pin 15 (30.0, 61.56) to relay_pads['+5V'] or pwr_pads['+5V']
    # 2. pwr_pads['+5V'] to relay_pads['+5V']
    # 3. LCD +5V via right perimeter to pwr_pads['+5V']
    v5_pwr_x = pwr_pads['+5V'][0]
    v5_relay_x = relay_pads['+5V'][0]

    # Route LCD +5V:
    tracks["+5V_LCD"] = [[(48.0, 13.54), (78.5, 13.54), (78.5, 72.0), (v5_pwr_x, 72.0), (v5_pwr_x, 78.0)]]

    # Connect ESP_L Pin 15 (+5V) and Relay +5V and Power +5V
    # We can connect them along Y=70.0
    tracks["+5V_BOARD"] = [
        [(30.0, 61.56), (30.0, 70.0), (v5_relay_x, 70.0), (v5_relay_x, 78.0)],
        [(v5_relay_x, 70.0), (v5_pwr_x, 70.0), (v5_pwr_x, 72.0)]
    ]

    # GND:
    # Bottom rail at Y=86.0 from X=6.0 to X=pwr_pads['GND'][0]
    gnd_pwr_x = pwr_pads['GND'][0]
    gnd_relay_x = relay_pads['GND'][0]
    tracks["GND"] = [
        # Left trunk to RFID & LCD
        [(16.08, 86.0), (6.0, 86.0), (6.0, 6.0), (48.0, 6.0), (48.0, 11.0)],
        [(6.0, 31.08), (10.0, 31.08)],
        # Bottom drops
        [(16.08, 78.0), (16.08, 86.0)],
        [(23.54, 78.0), (23.54, 86.0)],
        [(30.0, 59.02), (25.5, 59.02), (25.5, 86.0)],
        [(gnd_relay_x, 78.0), (gnd_relay_x, 86.0)],
        [(gnd_pwr_x, 78.0), (gnd_pwr_x, 86.0)],
        # Rail along 86.0
        [(16.08, 86.0), (max(gnd_relay_x, gnd_pwr_x), 86.0)],
        # ESP_R Pin 14 (55.4, 59.02)
        [(55.4, 59.02), (55.4, 86.0)]
    ]

    c = check_all(tracks)
    return len(c), c

# Combine +5V tracks for check
print("Testing permutations...")
from itertools import permutations
for r_order in permutations(['DOOR_RELAY', '+5V', 'GND']):
    for p_order in permutations(['+5V', 'GND']):
        for rx in [33.0, 36.0, 40.0, 42.0]:
            for px in [48.0, 50.0, 52.0]:
                if abs(rx - px) < 10.0: continue
                # We need +5V_LCD and +5V_BOARD to be treated as same net
                cnt, cr = test_layout(rx, r_order, px, p_order)
                if cnt == 0:
                    print(f"SUCCESS! rx={rx}, r_order={r_order}, px={px}, p_order={p_order}")
                    sys.exit(0)

print("No 0-crossing with these simple rules, let's see lowest:")
