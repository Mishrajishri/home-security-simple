import os, sys
import math

# We want to design a 100% planar, single-layer (B.Cu) KiCad PCB for Door Security Controller
# Dimensions: 85mm x 95mm

# All pads and components:
# J_ESP_L: X=30.0, Y=26.0 (pins 1 to 15, Y from 26.0 to 61.56, pitch 2.54)
# J_ESP_R: X=55.4, Y=26.0 (pins 1 to 15, Y from 26.0 to 61.56, pitch 2.54)
# J_RFID:  X=10.0, Y=26.0 (pins 1 to 8,  Y from 26.0 to 43.78, pitch 2.54)
# J_KEYPAD:X=75.0, Y=26.0 (pins 1 to 8,  Y from 26.0 to 43.78, pitch 2.54)
# J_LCD:   X=48.0, Y=11.0 (pins 1 to 4,  Y from 11.0 to 18.62, pitch 2.54)

# Bottom connectors at Y=78.0:
# J_LEDS:   X=11.0 (rot=90: Pads at 11.0, 13.54, 16.08)
# J_BUZZER: X=22.0 (rot=90: Pads at 22.0, 24.54)
# J_RELAY:  X=33.0 (rot=90: Pads at 33.0, 35.54, 38.08)
# J_POWER:  X=50.0 (rot=0:  Pads at 50.0, 55.08)

# Let's verify pad coordinates:
def get_pads():
    pads = {}
    # ESP_L
    for i in range(15):
        pads[f"ESP_L_{i+1}"] = (30.0, 26.0 + i * 2.54)
    # ESP_R
    for i in range(15):
        pads[f"ESP_R_{i+1}"] = (55.4, 26.0 + i * 2.54)
    # RFID
    for i in range(8):
        pads[f"RFID_{i+1}"] = (10.0, 26.0 + i * 2.54)
    # KEYPAD
    for i in range(8):
        pads[f"KEYPAD_{i+1}"] = (75.0, 26.0 + i * 2.54)
    # LCD
    for i in range(4):
        pads[f"LCD_{i+1}"] = (48.0, 11.0 + i * 2.54)
    # LEDS (rot=90: horizontal along X)
    for i in range(3):
        pads[f"LEDS_{i+1}"] = (11.0 + i * 2.54, 78.0)
    # BUZZER
    for i in range(2):
        pads[f"BUZZER_{i+1}"] = (22.0 + i * 2.54, 78.0)
    # RELAY (Pad 1: DOOR_RELAY at 33.0, Pad 2: +5V at 35.54, Pad 3: GND at 38.08)
    for i in range(3):
        pads[f"RELAY_{i+1}"] = (33.0 + i * 2.54, 78.0)
    # POWER (Pad 1: GND at 50.0, Pad 2: +5V at 55.08)
    pads["POWER_1"] = (50.0, 78.0)
    pads["POWER_2"] = (55.08, 78.0)
    return pads

pads = get_pads()
for k, v in pads.items():
    print(f"{k}: ({v[0]:.2f}, {v[1]:.2f})")
