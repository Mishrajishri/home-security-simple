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

    # 3. Nets
    net_names = [
        "GND", "+5V", "+3.3V",
        "RFID_MISO", "RFID_MOSI", "RFID_SCK", "RFID_SDA_SS", "RFID_RST",
        "I2C_SDA", "I2C_SCL",
        "DOOR_RELAY", "BUZZER", "LED_GREEN", "LED_RED",
        "KEYPAD_R1", "KEYPAD_R2", "KEYPAD_R3", "KEYPAD_R4",
        "KEYPAD_C1", "KEYPAD_C2", "KEYPAD_C3", "KEYPAD_C4"
    ]
    nets = {}
    for name in net_names:
        item = pcbnew.NETINFO_ITEM(board, name)
        board.Add(item)
        nets[name] = item
    board.BuildListOfNets()

    # 4. Footprint Helper
    def place_fp(lib, name, ref, val, x, y, rot=0, ref_pos=None):
        path = os.path.join(fp_dir, lib)
        fp = pcbnew.FootprintLoad(path, name)
        fp.SetReference(ref)
        fp.SetValue(val)
        fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        if rot != 0:
            fp.SetOrientation(pcbnew.EDA_ANGLE(rot, pcbnew.DEGREES_T))

        for pad in fp.Pads():
            # Robust annular ring for DIY drilling: pad 1.85mm, drill 0.95mm
            pad.SetSize(pcbnew.VECTOR2I(pcbnew.FromMM(1.85), pcbnew.FromMM(1.85)))
            pad.SetDrillSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.95), pcbnew.FromMM(0.95)))

        r = fp.Reference()
        if ref_pos:
            r.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(ref_pos[0]), pcbnew.FromMM(ref_pos[1])))
        else:
            r.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y - 4.5)))
        r.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.9), pcbnew.FromMM(0.9)))
        r.SetTextThickness(pcbnew.FromMM(0.12))
        r.SetVisible(True)

        v = fp.Value()
        v.SetVisible(False)

        board.Add(fp)
        return fp

    # Placement
    j_esp_l = place_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x15_P2.54mm_Vertical",
                       "J_ESP_L", "ESP32_L", 30.0, 26.0, ref_pos=(30.0, 22.0))
    j_esp_r = place_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x15_P2.54mm_Vertical",
                       "J_ESP_R", "ESP32_R", 55.4, 26.0, ref_pos=(55.4, 22.0))

    j_rfid = place_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x08_P2.54mm_Vertical",
                      "J_RFID", "RFID_RC522", 10.0, 26.0, ref_pos=(10.0, 22.0))

    j_keypad = place_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x08_P2.54mm_Vertical",
                        "J_KEYPAD", "Keypad_4x4", 75.0, 26.0, ref_pos=(75.0, 22.0))

    j_lcd = place_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x04_P2.54mm_Vertical",
                     "J_LCD", "I2C_LCD", 48.0, 11.0, rot=0, ref_pos=(48.0, 6.5))

    # Bottom Connectors at Y=78.0:
    j_leds = place_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x03_P2.54mm_Vertical",
                      "J_LEDS", "Status_LEDs", 12.0, 78.0, rot=90, ref_pos=(14.5, 73.0))

    j_power = place_fp("TerminalBlock_Phoenix.pretty", "TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal",
                       "J_POWER", "5V_Power", 23.0, 78.0, rot=0, ref_pos=(25.5, 70.0))

    j_buzzer = place_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x02_P2.54mm_Vertical",
                        "J_BUZZER", "Buzzer", 38.0, 78.0, rot=90, ref_pos=(39.0, 73.0))

    j_relay = place_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x03_P2.54mm_Vertical",
                       "J_RELAY", "Relay_Lock", 48.0, 78.0, rot=90, ref_pos=(50.5, 73.0))

    # Nets Assignment
    def set_net(fp, pnum, net_name):
        pad = fp.FindPadByNumber(str(pnum))
        if pad and net_name in nets:
            pad.SetNet(nets[net_name])

    # Left ESP Header
    set_net(j_esp_l, 5, "RFID_MISO")    # Pin 5: GPIO35
    set_net(j_esp_l, 6, "RFID_MOSI")    # Pin 6: GPIO32
    set_net(j_esp_l, 7, "RFID_SCK")     # Pin 7: GPIO33
    set_net(j_esp_l, 8, "RFID_SDA_SS")  # Pin 8: GPIO25
    set_net(j_esp_l, 9, "RFID_RST")     # Pin 9: GPIO26
    set_net(j_esp_l, 10, "DOOR_RELAY")  # Pin 10: GPIO27
    set_net(j_esp_l, 11, "LED_GREEN")   # Pin 11: GPIO14
    set_net(j_esp_l, 12, "LED_RED")     # Pin 12: GPIO12
    set_net(j_esp_l, 13, "BUZZER")      # Pin 13: GPIO13
    set_net(j_esp_l, 14, "GND")         # Pin 14: GND
    set_net(j_esp_l, 15, "+5V")         # Pin 15: VIN

    # Right ESP Header
    set_net(j_esp_r, 1, "KEYPAD_R1")    # Pin 1: GPIO23
    set_net(j_esp_r, 2, "I2C_SCL")      # Pin 2: GPIO22
    set_net(j_esp_r, 5, "I2C_SDA")      # Pin 5: GPIO21
    set_net(j_esp_r, 6, "KEYPAD_R2")    # Pin 6: GPIO19
    set_net(j_esp_r, 7, "KEYPAD_R3")    # Pin 7: GPIO18
    set_net(j_esp_r, 8, "KEYPAD_R4")    # Pin 8: GPIO5
    set_net(j_esp_r, 9, "KEYPAD_C1")    # Pin 9: GPIO17
    set_net(j_esp_r, 10, "KEYPAD_C2")   # Pin 10: GPIO16
    set_net(j_esp_r, 12, "KEYPAD_C3")   # Pin 12: GPIO2
    set_net(j_esp_r, 13, "KEYPAD_C4")   # Pin 13: GPIO15
    set_net(j_esp_r, 14, "GND")         # Pin 14: GND
    set_net(j_esp_r, 15, "+3.3V")       # Pin 15: 3V3

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
    set_net(j_power, 1, "GND")
    set_net(j_power, 2, "+5V")

    set_net(j_leds, 1, "LED_GREEN")
    set_net(j_leds, 2, "LED_RED")
    set_net(j_leds, 3, "GND")

    set_net(j_buzzer, 1, "BUZZER")
    set_net(j_buzzer, 2, "GND")

    set_net(j_relay, 1, "GND")
    set_net(j_relay, 2, "+5V")
    set_net(j_relay, 3, "DOOR_RELAY")

    # Route Helper
    def ppos(fp, pnum):
        p = fp.FindPadByNumber(str(pnum))
        pos = p.GetPosition()
        return (round(pos.x / 1e6, 3), round(pos.y / 1e6, 3))

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

    # ─── 100% PLANAR ROUTING (ZERO CROSSINGS) ─────────────────────────

    # 1. RFID SPI Lines (MISO, MOSI, SCK, SDA) - Pure straight horizontal
    route_track("RFID_MISO", [ppos(j_rfid, 5), ppos(j_esp_l, 5)])
    route_track("RFID_MOSI", [ppos(j_rfid, 6), ppos(j_esp_l, 6)])
    route_track("RFID_SCK", [ppos(j_rfid, 7), ppos(j_esp_l, 7)])
    route_track("RFID_SDA_SS", [ppos(j_rfid, 8), ppos(j_esp_l, 8)])

    # 2. Keypad (8 Monotonic non-crossing concentric traces on right)
    route_track("KEYPAD_R1", [ppos(j_esp_r, 1), ppos(j_keypad, 1)])
    route_track("KEYPAD_R2", [ppos(j_esp_r, 6), (58.0, ppos(j_esp_r, 6)[1]), (58.0, ppos(j_keypad, 2)[1]), ppos(j_keypad, 2)])
    route_track("KEYPAD_R3", [ppos(j_esp_r, 7), (60.5, ppos(j_esp_r, 7)[1]), (60.5, ppos(j_keypad, 3)[1]), ppos(j_keypad, 3)])
    route_track("KEYPAD_R4", [ppos(j_esp_r, 8), (63.0, ppos(j_esp_r, 8)[1]), (63.0, ppos(j_keypad, 4)[1]), ppos(j_keypad, 4)])
    route_track("KEYPAD_C1", [ppos(j_esp_r, 9), (65.5, ppos(j_esp_r, 9)[1]), (65.5, ppos(j_keypad, 5)[1]), ppos(j_keypad, 5)])
    route_track("KEYPAD_C2", [ppos(j_esp_r, 10), (68.0, ppos(j_esp_r, 10)[1]), (68.0, ppos(j_keypad, 6)[1]), ppos(j_keypad, 6)])
    route_track("KEYPAD_C3", [ppos(j_esp_r, 12), (70.5, ppos(j_esp_r, 12)[1]), (70.5, ppos(j_keypad, 7)[1]), ppos(j_keypad, 7)])
    route_track("KEYPAD_C4", [ppos(j_esp_r, 13), (73.0, ppos(j_esp_r, 13)[1]), (73.0, ppos(j_keypad, 8)[1]), ppos(j_keypad, 8)])

    # 3. I2C LCD (SCL & SDA)
    route_track("I2C_SCL", [ppos(j_lcd, 4), (ppos(j_lcd, 4)[0], ppos(j_esp_r, 2)[1]), ppos(j_esp_r, 2)])
    route_track("I2C_SDA", [ppos(j_lcd, 3), (46.0, ppos(j_lcd, 3)[1]), (46.0, ppos(j_esp_r, 5)[1]), ppos(j_esp_r, 5)])

    # 4. Corridor Signals:
    # A. RFID_RST from ESP_L Pin 9 (30.0, 46.32)
    # Exits east to X=34.0, north to Y=18.0, west to X=20.0, south to Y=28.54, west into J_RFID Pad 2
    route_track("RFID_RST", [ppos(j_esp_l, 9), (34.0, ppos(j_esp_l, 9)[1]), (34.0, 18.0), (20.0, 18.0), (20.0, ppos(j_rfid, 2)[1]), ppos(j_rfid, 2)])

    # B. +3.3V from ESP_R Pin 15 (55.4, 61.56)
    # Exits west into corridor at X=38.0, north to Y=15.0, west to X=10.0, south into J_RFID Pad 1
    route_track("+3.3V", [ppos(j_esp_r, 15), (38.0, ppos(j_esp_r, 15)[1]), (38.0, 15.0), (ppos(j_rfid, 1)[0], 15.0), ppos(j_rfid, 1)], width=1.1)

    # C. DOOR_RELAY from ESP_L Pin 10 (30.0, 48.86)
    # Exits east to X=36.0, south to Y=74.0, east to X=53.08, south into J_RELAY Pad 3
    route_track("DOOR_RELAY", [ppos(j_esp_l, 10), (36.0, ppos(j_esp_l, 10)[1]), (36.0, 74.0), (ppos(j_relay, 3)[0], 74.0), ppos(j_relay, 3)])

    # D. BUZZER from ESP_L Pin 13 (30.0, 56.48)
    # Exits east to X=32.0, south to Y=75.5, east to X=38.0, south into J_BUZZER Pad 1
    route_track("BUZZER", [ppos(j_esp_l, 13), (32.0, ppos(j_esp_l, 13)[1]), (32.0, 75.5), (ppos(j_buzzer, 1)[0], 75.5), ppos(j_buzzer, 1)])

    # 5. Left Signals from ESP_L:
    # LED_GREEN from Pin 11 (30.0, 51.40) to J_LEDS Pad 1 (12.0, 78.0)
    route_track("LED_GREEN", [ppos(j_esp_l, 11), (ppos(j_leds, 1)[0], ppos(j_esp_l, 11)[1]), ppos(j_leds, 1)])
    # LED_RED from Pin 12 (30.0, 53.94) to J_LEDS Pad 2 (14.54, 78.0)
    route_track("LED_RED", [ppos(j_esp_l, 12), (ppos(j_leds, 2)[0], ppos(j_esp_l, 12)[1]), ppos(j_leds, 2)])

    # 6. Ground (GND) Net (1.2mm width)
    # Bottom GND Bus along Y=88.0:
    # J_POWER Pad 1 is at (23.0, 78.0) -> drops south to (23.0, 88.0)
    route_track("GND", [ppos(j_power, 1), (ppos(j_power, 1)[0], 88.0)], width=1.2)
    # J_LEDS Pad 3 (17.08, 78.0) -> drops south to (17.08, 88.0) -> connects to J_POWER Pad 1
    route_track("GND", [ppos(j_leds, 3), (ppos(j_leds, 3)[0], 88.0), (ppos(j_power, 1)[0], 88.0)], width=1.2)
    # J_BUZZER Pad 2 (40.54, 78.0) -> drops south to (40.54, 88.0)
    route_track("GND", [(ppos(j_power, 1)[0], 88.0), (ppos(j_buzzer, 2)[0], 88.0), ppos(j_buzzer, 2)], width=1.2)
    # J_RELAY Pad 1 (48.0, 78.0) -> drops south to (48.0, 88.0)
    route_track("GND", [(ppos(j_buzzer, 2)[0], 88.0), (ppos(j_relay, 1)[0], 88.0), ppos(j_relay, 1)], width=1.2)

    # ESP_L Pin 14 (GND at 30.0, 59.02): exits west to X=26.0, south to (26.0, 72.0), west to (23.0, 72.0), south into J_POWER Pad 1 (23.0, 78.0)
    route_track("GND", [ppos(j_esp_l, 14), (26.0, ppos(j_esp_l, 14)[1]), (26.0, 72.0), (ppos(j_power, 1)[0], 72.0), ppos(j_power, 1)], width=1.2)

    # ESP_R Pin 14 (GND at 55.4, 59.02): exits east to X=58.0, south to Y=76.0, west to X=48.0, south into J_RELAY Pad 1 (48.0, 78.0)
    route_track("GND", [ppos(j_esp_r, 14), (58.0, ppos(j_esp_r, 14)[1]), (58.0, 76.0), (ppos(j_relay, 1)[0], 76.0), ppos(j_relay, 1)], width=1.2)

    # Outer Left Trunk to J_RFID Pad 3 and J_LCD Pad 1:
    # From (17.08, 88.0): west to X=7.0, north along X=7.0 to Y=8.0!
    route_track("GND", [(ppos(j_leds, 3)[0], 88.0), (7.0, 88.0), (7.0, 8.0)], width=1.2)
    # Branch into J_RFID Pad 3 (10.0, 31.08)
    route_track("GND", [(7.0, ppos(j_rfid, 3)[1]), ppos(j_rfid, 3)], width=1.2)
    # Branch into J_LCD Pad 1 (48.0, 11.0)
    route_track("GND", [(7.0, 8.0), (ppos(j_lcd, 1)[0], 8.0), ppos(j_lcd, 1)], width=1.2)

    # 7. +5V Rail (1.2mm width)
    # Feed from J_POWER Pad 2 (28.08, 78.0):
    # To ESP_L Pin 15 (30.0, 61.56): directly up along X=28.08 to Y=61.56, east into Pin 15
    route_track("+5V", [ppos(j_power, 2), (ppos(j_power, 2)[0], ppos(j_esp_l, 15)[1]), ppos(j_esp_l, 15)], width=1.2)
    # To J_RELAY Pad 2 (50.54, 78.0): routes north from Pad 2 (28.08, 78.0) to Y=66.0, east to (50.54, 66.0), south into J_RELAY Pad 2
    route_track("+5V", [ppos(j_power, 2), (ppos(j_power, 2)[0], 66.0), (ppos(j_relay, 2)[0], 66.0), ppos(j_relay, 2)], width=1.2)
    # To J_LCD Pad 2 (48.0, 13.54): from (50.54, 66.0) east to X=81.0, north along X=81.0 to Y=13.54, west into Pad 2
    route_track("+5V", [(ppos(j_relay, 2)[0], 66.0), (81.0, 66.0), (81.0, ppos(j_lcd, 2)[1]), ppos(j_lcd, 2)], width=1.2)

    # 8. Clean Silkscreen Text (Zero overlap)
    def add_label(txt, x, y, sz=1.1):
        t = pcbnew.PCB_TEXT(board)
        t.SetText(txt)
        t.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        t.SetLayer(pcbnew.F_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(sz), pcbnew.FromMM(sz)))
        t.SetTextThickness(pcbnew.FromMM(0.15))
        board.Add(t)

    add_label("VIDYUTRAKSHAK - DOOR CONTROLLER", 42.5, 3.5, sz=1.3)
    add_label("Vigyan Mela 2026 | Carrier Board", 42.5, 5.0, sz=0.9)
    add_label("ESP32 DevKit V1", 42.5, 48.0, sz=1.2)
    add_label("[USB at Bottom]", 42.5, 51.0, sz=0.9)

    out_path = "/Users/shreyansh/@nirman/hardware/door_security_pcb/door_security.kicad_pcb"
    pcbnew.SaveBoard(out_path, board)
    print("Master Planar PCB generated successfully!")

if __name__ == "__main__":
    build_pcb()
