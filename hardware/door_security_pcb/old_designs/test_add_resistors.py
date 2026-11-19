import os, sys
import pcbnew

def build_pcb():
    board = pcbnew.BOARD()
    fp_dir = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"

    # Board Dimensions: 85mm x 95mm (DIY Single Layer Acid Etch)
    W, H = 85.0, 95.0

    # 1. Edge Cuts
    corners = [(0.0, 0.0), (W, 0.0), (W, H), (0.0, H)]
    for i in range(4):
        p1, p2 = corners[i], corners[(i + 1) % 4]
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(p1[0]), pcbnew.FromMM(p1[1])))
        seg.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(p2[0]), pcbnew.FromMM(p2[1])))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(pcbnew.FromMM(0.15))
        board.Add(seg)

    # 2. Mounting Holes M3 at (5, 5), (80, 5), (5, 90), (80, 90)
    hole_lib = os.path.join(fp_dir, "MountingHole.pretty")
    for i, (hx, hy) in enumerate([(5.0, 5.0), (80.0, 5.0), (5.0, 90.0), (80.0, 90.0)]):
        h = pcbnew.FootprintLoad(hole_lib, "MountingHole_3.2mm_M3")
        h.SetReference(f"H{i+1}")
        h.SetValue("M3_Hole")
        h.Reference().SetVisible(False)
        h.Value().SetVisible(False)
        h.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(hx), pcbnew.FromMM(hy)))
        board.Add(h)

    # 3. Nets - added ESP_LED_GREEN and ESP_LED_RED for the resistor segments
    net_names = [
        "GND", "+5V", "+3.3V",
        "RFID_MISO", "RFID_MOSI", "RFID_SCK", "RFID_SDA_SS", "RFID_RST",
        "I2C_SDA", "I2C_SCL",
        "DOOR_RELAY", "BUZZER",
        "ESP_LED_GREEN", "LED_GREEN",
        "ESP_LED_RED", "LED_RED",
        "KEYPAD_R1", "KEYPAD_R2", "KEYPAD_R3", "KEYPAD_R4",
        "KEYPAD_C1", "KEYPAD_C2", "KEYPAD_C3", "KEYPAD_C4"
    ]
    nets = {}
    for name in net_names:
        item = pcbnew.NETINFO_ITEM(board, name)
        board.Add(item)
        nets[name] = item
    board.BuildListOfNets()

    # 4. Footprint Placement Helper
    def place_fp(lib, name, ref, val, x, y, rot=0, ref_pos=None):
        path = os.path.join(fp_dir, lib)
        fp = pcbnew.FootprintLoad(path, name)
        fp.SetReference(ref)
        fp.SetValue(val)
        fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        if rot != 0:
            fp.SetOrientation(pcbnew.EDA_ANGLE(rot, pcbnew.DEGREES_T))

        for pad in fp.Pads():
            pad.SetSize(pcbnew.VECTOR2I(pcbnew.FromMM(1.85), pcbnew.FromMM(1.85)))
            pad.SetDrillSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.95), pcbnew.FromMM(0.95)))

        r = fp.Reference()
        r.SetVisible(False)

        v = fp.Value()
        v.SetVisible(False)

        board.Add(fp)
        return fp

    # Placement:
    j_esp_l = place_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x15_P2.54mm_Vertical",
                       "J_ESP_L", "ESP32_L", 30.0, 26.0)
    j_esp_r = place_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x15_P2.54mm_Vertical",
                       "J_ESP_R", "ESP32_R", 55.4, 26.0)

    j_rfid = place_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x08_P2.54mm_Vertical",
                      "J_RFID", "RFID_RC522", 10.0, 26.0)

    j_keypad = place_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x08_P2.54mm_Vertical",
                        "J_KEYPAD", "Keypad_4x4", 75.0, 26.0)

    j_lcd = place_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x04_P2.54mm_Vertical",
                     "J_LCD", "I2C_LCD", 48.0, 11.0, rot=0)

    # Resistors: R1 (100R for Green LED) and R2 (100R for Red LED)
    r_green = place_fp("Resistor_THT.pretty", "R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
                       "R1", "100R", 11.0, 59.0, rot=270)
    r_red   = place_fp("Resistor_THT.pretty", "R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
                       "R2", "100R", 13.54, 63.0, rot=270)

    # Bottom Connectors at Y=78.0:
    j_leds = place_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x03_P2.54mm_Vertical",
                      "J_LEDS", "Status_LEDs", 11.0, 78.0, rot=90)

    j_buzzer = place_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x02_P2.54mm_Vertical",
                        "J_BUZZER", "Buzzer", 21.0, 78.0, rot=90)

    j_power = place_fp("TerminalBlock_Phoenix.pretty", "TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal",
                       "J_POWER", "5V_Power", 33.0, 78.0, rot=0)

    j_relay = place_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x03_P2.54mm_Vertical",
                       "J_RELAY", "Relay_Lock", 45.0, 78.0, rot=90)

    # Net Mapping Helper
    def set_net(fp, pnum, net_name):
        pad = fp.FindPadByNumber(str(pnum))
        if pad and net_name in nets:
            pad.SetNet(nets[net_name])

    # Left ESP Header
    set_net(j_esp_l, 1, "+3.3V")
    set_net(j_esp_l, 5, "RFID_MISO")
    set_net(j_esp_l, 6, "RFID_MOSI")
    set_net(j_esp_l, 7, "RFID_SCK")
    set_net(j_esp_l, 8, "RFID_SDA_SS")
    set_net(j_esp_l, 9, "RFID_RST")
    set_net(j_esp_l, 11, "ESP_LED_GREEN")  # Pin 11: GPIO14 connects to R1
    set_net(j_esp_l, 12, "ESP_LED_RED")    # Pin 12: GPIO12 connects to R2
    set_net(j_esp_l, 13, "BUZZER")
    set_net(j_esp_l, 14, "GND")
    set_net(j_esp_l, 15, "+5V")

    # Right ESP Header
    set_net(j_esp_r, 1, "KEYPAD_R1")
    set_net(j_esp_r, 2, "I2C_SCL")
    set_net(j_esp_r, 5, "I2C_SDA")
    set_net(j_esp_r, 6, "KEYPAD_R2")
    set_net(j_esp_r, 7, "KEYPAD_R3")
    set_net(j_esp_r, 8, "KEYPAD_R4")
    set_net(j_esp_r, 9, "KEYPAD_C1")
    set_net(j_esp_r, 10, "KEYPAD_C2")
    set_net(j_esp_r, 11, "DOOR_RELAY")
    set_net(j_esp_r, 12, "KEYPAD_C3")
    set_net(j_esp_r, 13, "KEYPAD_C4")
    set_net(j_esp_r, 14, "GND")

    # Resistors
    set_net(r_green, 1, "ESP_LED_GREEN")
    set_net(r_green, 2, "LED_GREEN")

    set_net(r_red, 1, "ESP_LED_RED")
    set_net(r_red, 2, "LED_RED")

    # RFID RC522
    set_net(j_rfid, 1, "+3.3V")
    set_net(j_rfid, 2, "RFID_RST")
    set_net(j_rfid, 3, "GND")
    set_net(j_rfid, 5, "RFID_MISO")
    set_net(j_rfid, 6, "RFID_MOSI")
    set_net(j_rfid, 7, "RFID_SCK")
    set_net(j_rfid, 8, "RFID_SDA_SS")

    # LCD
    set_net(j_lcd, 1, "GND")
    set_net(j_lcd, 2, "+5V")
    set_net(j_lcd, 3, "I2C_SDA")
    set_net(j_lcd, 4, "I2C_SCL")

    # Keypad
    for i in range(1, 5):
        set_net(j_keypad, i, f"KEYPAD_R{i}")
        set_net(j_keypad, i + 4, f"KEYPAD_C{i}")

    # Bottom Connectors
    set_net(j_leds, 1, "LED_GREEN")
    set_net(j_leds, 2, "LED_RED")
    set_net(j_leds, 3, "GND")

    set_net(j_buzzer, 1, "BUZZER")
    set_net(j_buzzer, 2, "GND")

    set_net(j_power, 1, "+5V")
    set_net(j_power, 2, "GND")

    set_net(j_relay, 1, "+5V")
    set_net(j_relay, 2, "DOOR_RELAY")
    set_net(j_relay, 3, "GND")

    def route_track(net_name, points, width=0.85):
        net = nets.get(net_name)
        for i in range(len(points) - 1):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(points[i][0]), pcbnew.FromMM(points[i][1])))
            t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(points[i+1][0]), pcbnew.FromMM(points[i+1][1])))
            t.SetWidth(pcbnew.FromMM(width))
            t.SetLayer(pcbnew.B_Cu)
            if net: t.SetNet(net)
            board.Add(t)

    # ─── 100% PLANAR ZERO-CROSSING ROUTING ON B.CU ────────────────────

    # 1. RFID SPI Lines (MISO, MOSI, SCK, SDA)
    route_track("RFID_MISO", [(10.0, 36.16), (30.0, 36.16)])
    route_track("RFID_MOSI", [(10.0, 38.70), (30.0, 38.70)])
    route_track("RFID_SCK",  [(10.0, 41.24), (30.0, 41.24)])
    route_track("RFID_SDA_SS", [(10.0, 43.78), (30.0, 43.78)])

    # 2. +3.3V to RFID
    route_track("+3.3V", [(30.0, 26.0), (30.0, 24.0), (10.0, 24.0), (10.0, 26.0)], width=1.0)

    # 3. RFID_RST
    route_track("RFID_RST", [(30.0, 46.32), (34.0, 46.32), (34.0, 21.0), (8.0, 21.0), (8.0, 28.54), (10.0, 28.54)])

    # 4. Keypad (8 Monotonic non-crossing concentric traces on right)
    route_track("KEYPAD_R1", [(55.4, 26.0), (75.0, 26.0)])
    route_track("KEYPAD_R2", [(55.4, 38.70), (58.0, 38.70), (58.0, 28.54), (75.0, 28.54)])
    route_track("KEYPAD_R3", [(55.4, 41.24), (60.5, 41.24), (60.5, 31.08), (75.0, 31.08)])
    route_track("KEYPAD_R4", [(55.4, 43.78), (63.0, 43.78), (63.0, 33.62), (75.0, 33.62)])
    route_track("KEYPAD_C1", [(55.4, 46.32), (65.5, 46.32), (65.5, 36.16), (75.0, 36.16)])
    route_track("KEYPAD_C2", [(55.4, 48.86), (68.0, 48.86), (68.0, 38.70), (75.0, 38.70)])
    route_track("KEYPAD_C3", [(55.4, 53.94), (70.5, 53.94), (70.5, 41.24), (75.0, 41.24)])
    route_track("KEYPAD_C4", [(55.4, 56.48), (73.0, 56.48), (73.0, 43.78), (75.0, 43.78)])

    # 5. I2C LCD (SCL & SDA)
    route_track("I2C_SCL", [(48.0, 18.62), (48.0, 28.54), (55.4, 28.54)])
    route_track("I2C_SDA", [(48.0, 16.08), (45.5, 16.08), (45.5, 36.16), (55.4, 36.16)])

    # 6. Actuators with Resistors R1 & R2
    # Green LED: ESP -> R1 -> J_LEDS Pad 1
    route_track("ESP_LED_GREEN", [(30.0, 51.40), (11.0, 51.40), (11.0, 59.0)])
    route_track("LED_GREEN",     [(11.0, 66.62), (11.0, 78.0)])

    # Red LED: ESP -> R2 -> J_LEDS Pad 2
    route_track("ESP_LED_RED", [(30.0, 53.94), (13.54, 53.94), (13.54, 63.0)])
    route_track("LED_RED",     [(13.54, 70.62), (13.54, 78.0)])

    # Buzzer
    route_track("BUZZER", [(30.0, 56.48), (21.0, 56.48), (21.0, 78.0)])

    # 7. DOOR_RELAY from ESP_R Pin 11 to J_RELAY Pad 2
    route_track("DOOR_RELAY", [(55.4, 51.40), (47.54, 51.40), (47.54, 78.0)])

    # 8. +5V Distribution
    route_track("+5V", [(48.0, 13.54), (43.0, 13.54), (43.0, 74.0)], width=1.1)
    route_track("+5V", [(30.0, 61.56), (30.0, 74.0), (45.0, 74.0)], width=1.1)
    route_track("+5V", [(33.0, 74.0), (33.0, 78.0)], width=1.1)
    route_track("+5V", [(45.0, 74.0), (45.0, 78.0)], width=1.1)

    # 9. Ground (GND) Distribution:
    route_track("GND", [(6.0, 85.0), (53.0, 85.0)], width=1.2)
    route_track("GND", [(6.0, 85.0), (6.0, 12.0), (8.5, 9.5), (8.5, 6.0), (48.0, 6.0), (48.0, 11.0)], width=1.2)
    route_track("GND", [(6.0, 31.08), (10.0, 31.08)], width=1.2)
    route_track("GND", [(16.08, 78.0), (16.08, 85.0)], width=1.2)
    route_track("GND", [(23.54, 78.0), (23.54, 85.0)], width=1.2)
    route_track("GND", [(30.0, 59.02), (25.5, 59.02), (25.5, 85.0)], width=1.2)
    route_track("GND", [(38.08, 78.0), (38.08, 85.0)], width=1.2)
    route_track("GND", [(50.08, 78.0), (50.08, 85.0)], width=1.2)
    route_track("GND", [(55.4, 59.02), (53.0, 59.02), (53.0, 85.0)], width=1.2)

    # 10. Clean Silkscreen Labels
    def add_label(txt, x, y, sz=0.9, rot=0):
        t = pcbnew.PCB_TEXT(board)
        t.SetText(txt)
        t.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        t.SetLayer(pcbnew.F_SilkS)
        if rot != 0:
            t.SetTextAngle(pcbnew.EDA_ANGLE(rot, pcbnew.DEGREES_T))
        t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(sz), pcbnew.FromMM(sz)))
        t.SetTextThickness(pcbnew.FromMM(0.16))
        board.Add(t)

    # Titles
    add_label("VIDYUTRAKSHAK - DOOR SECURITY", 42.5, 2.5, sz=1.3)
    add_label("Vigyan Mela 2026 | Carrier Breakout", 42.5, 4.2, sz=0.9)
    add_label("ESP32 DEVKIT V1", 42.5, 48.0, sz=1.2)
    add_label("[Micro-USB at Bottom]", 42.5, 51.0, sz=0.9)

    # Connector Port Labels
    add_label("RC522", 10.0, 22.5, sz=0.9)
    add_label("KEYPAD 4x4", 75.0, 22.5, sz=0.9)
    add_label("I2C LCD", 48.0, 7.5, sz=0.9)
    add_label("STATUS", 13.5, 74.0, sz=0.85)
    add_label("BUZZER", 22.0, 73.0, sz=0.85)
    add_label("5V POWER", 35.5, 70.0, sz=0.85)
    add_label("RELAY", 47.5, 73.0, sz=0.85)

    # Resistor Labels
    add_label("R1: 100R", 8.0, 62.8, sz=0.85, rot=90)
    add_label("R2: 100R", 16.5, 66.8, sz=0.85, rot=90)

    # Pin Function Labels
    add_label("G R -", 13.5, 81.5, sz=0.85)
    add_label("+ -", 22.0, 81.5, sz=0.85)
    add_label("+5V GND", 35.5, 87.0, sz=0.85)
    add_label("+ S -", 47.5, 81.5, sz=0.85)

    out_path = "/Users/shreyansh/@nirman/hardware/door_security_pcb/door_security.kicad_pcb"
    pcbnew.SaveBoard(out_path, board)
    print("PCB with 100R Resistors generated successfully!")

if __name__ == "__main__":
    build_pcb()
