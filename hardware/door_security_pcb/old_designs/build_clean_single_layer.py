import os, sys
import pcbnew

def build_pcb():
    board = pcbnew.BOARD()
    fp_dir = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"

    # Board Dimensions: 85mm x 95mm (Fits on 4x5 inch board)
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
            pad.SetSize(pcbnew.VECTOR2I(pcbnew.FromMM(1.85), pcbnew.FromMM(1.85)))
            pad.SetDrillSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.95), pcbnew.FromMM(0.95)))

        r = fp.Reference()
        if ref_pos:
            r.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(ref_pos[0]), pcbnew.FromMM(ref_pos[1])))
        else:
            r.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y - 3.5)))
        r.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(1.2), pcbnew.FromMM(1.2)))
        r.SetTextThickness(pcbnew.FromMM(0.15))
        r.SetVisible(True)

        v = fp.Value()
        v.SetVisible(False)

        board.Add(fp)
        return fp

    # Placement
    # ESP32 Headers
    j_esp_l = place_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x15_P2.54mm_Vertical",
                       "J_ESP_L", "ESP32_L", 30.0, 26.0, ref_pos=(30.0, 22.0))
    j_esp_r = place_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x15_P2.54mm_Vertical",
                       "J_ESP_R", "ESP32_R", 55.4, 26.0, ref_pos=(55.4, 22.0))

    # RFID Module Header on Left (X = 10.0)
    j_rfid = place_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x08_P2.54mm_Vertical",
                      "J_RFID", "RFID_RC522", 10.0, 26.0, ref_pos=(10.0, 22.0))

    # I2C LCD at Top Center
    j_lcd = place_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x04_P2.54mm_Vertical",
                     "J_LCD", "I2C_LCD", 42.0, 11.0, rot=90, ref_pos=(45.0, 7.5))

    # 4x4 Keypad on Right (X = 75.0, Y = 26.0)
    j_keypad = place_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x08_P2.54mm_Vertical",
                        "J_KEYPAD", "Keypad_4x4", 75.0, 26.0, ref_pos=(75.0, 22.0))

    # Power & Peripherals at Bottom (Y = 80.0)
    # rot=180: Pad 1 (+5V) at (17.08, 80.0), Pad 2 (GND) at (12.0, 80.0)
    j_power = place_fp("TerminalBlock_Phoenix.pretty", "TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal",
                       "J_POWER", "5V_Power", 17.08, 80.0, rot=180, ref_pos=(14.5, 73.0))

    # Decoupling Caps C1 and C2 at bottom
    # rot=90: Pad 1 at Y=80.0, Pad 2 at Y=77.5
    c1 = place_fp("Capacitor_THT.pretty", "CP_Radial_D6.3mm_P2.50mm",
                  "C1", "100uF", 23.0, 80.0, rot=270, ref_pos=(23.0, 74.0))
    c2 = place_fp("Capacitor_THT.pretty", "C_Disc_D4.3mm_W1.9mm_P5.00mm",
                  "C2", "0.1uF", 29.0, 80.0, rot=270, ref_pos=(29.0, 74.0))

    # Buzzer (rot=90)
    j_buzzer = place_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x02_P2.54mm_Vertical",
                        "J_BUZZER", "Buzzer", 36.0, 80.0, rot=90, ref_pos=(37.0, 75.0))

    # Status LEDs (rot=90)
    j_leds = place_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x03_P2.54mm_Vertical",
                      "J_LEDS", "Status_LEDs", 45.0, 80.0, rot=90, ref_pos=(47.5, 75.0))

    # Relay Module (rot=90)
    j_relay = place_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x03_P2.54mm_Vertical",
                       "J_RELAY", "Relay_Lock", 58.0, 80.0, rot=90, ref_pos=(60.5, 75.0))

    # 5. Net Assignments
    def set_net(fp, pnum, net_name):
        pad = fp.FindPadByNumber(str(pnum))
        if pad and net_name in nets:
            pad.SetNet(nets[net_name])

    # Left ESP Header (ESP32-L)
    set_net(j_esp_l, 5, "RFID_MISO")
    set_net(j_esp_l, 6, "RFID_MOSI")
    set_net(j_esp_l, 7, "RFID_SCK")
    set_net(j_esp_l, 8, "RFID_SDA_SS")
    set_net(j_esp_l, 9, "RFID_RST")
    set_net(j_esp_l, 11, "LED_GREEN")
    set_net(j_esp_l, 12, "LED_RED")
    set_net(j_esp_l, 13, "BUZZER")
    set_net(j_esp_l, 14, "GND")
    set_net(j_esp_l, 15, "+5V")

    # Right ESP Header (ESP32-R)
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
    set_net(j_esp_r, 15, "+3.3V")

    # RFID RC522 Header
    set_net(j_rfid, 1, "+3.3V")
    set_net(j_rfid, 2, "RFID_RST")
    set_net(j_rfid, 3, "GND")
    set_net(j_rfid, 5, "RFID_MISO")
    set_net(j_rfid, 6, "RFID_MOSI")
    set_net(j_rfid, 7, "RFID_SCK")
    set_net(j_rfid, 8, "RFID_SDA_SS")

    # LCD Header
    set_net(j_lcd, 1, "GND")
    set_net(j_lcd, 2, "+5V")
    set_net(j_lcd, 3, "I2C_SDA")
    set_net(j_lcd, 4, "I2C_SCL")

    # Keypad Header
    set_net(j_keypad, 1, "KEYPAD_R1")
    set_net(j_keypad, 2, "KEYPAD_R2")
    set_net(j_keypad, 3, "KEYPAD_R3")
    set_net(j_keypad, 4, "KEYPAD_R4")
    set_net(j_keypad, 5, "KEYPAD_C1")
    set_net(j_keypad, 6, "KEYPAD_C2")
    set_net(j_keypad, 7, "KEYPAD_C3")
    set_net(j_keypad, 8, "KEYPAD_C4")

    # Bottom Connectors
    set_net(j_power, 1, "+5V")
    set_net(j_power, 2, "GND")

    set_net(c1, 1, "+5V")
    set_net(c1, 2, "GND")

    set_net(c2, 1, "+5V")
    set_net(c2, 2, "GND")

    set_net(j_buzzer, 1, "BUZZER")
    set_net(j_buzzer, 2, "GND")

    set_net(j_leds, 1, "LED_GREEN")
    set_net(j_leds, 2, "LED_RED")
    set_net(j_leds, 3, "GND")

    set_net(j_relay, 1, "GND")
    set_net(j_relay, 2, "+5V")
    set_net(j_relay, 3, "DOOR_RELAY")

    # 6. Route Helper
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

    # ─── ROUTING TRACES ──────────────────────────────────────────────

    # A. RFID SPI (Straight horizontal lines)
    route_track("RFID_MISO", [ppos(j_rfid, 5), ppos(j_esp_l, 5)])
    route_track("RFID_MOSI", [ppos(j_rfid, 6), ppos(j_esp_l, 6)])
    route_track("RFID_SCK", [ppos(j_rfid, 7), ppos(j_esp_l, 7)])
    route_track("RFID_SDA_SS", [ppos(j_rfid, 8), ppos(j_esp_l, 8)])

    # B. RFID RST: Exits ESP_L Pin 9 east into corridor to X=33.5, north to Y=16.0, west to X=7.0, south into J_RFID Pin 2
    route_track("RFID_RST", [ppos(j_esp_l, 9), (33.5, ppos(j_esp_l, 9)[1]), (33.5, 16.0), (7.0, 16.0), (7.0, ppos(j_rfid, 2)[1]), ppos(j_rfid, 2)])

    # C. RFID +3.3V: Exits ESP_R Pin 15 west into corridor to X=37.0, north to Y=18.5, west to J_RFID Pin 1 (10.0, 26.0)
    route_track("+3.3V", [ppos(j_esp_r, 15), (37.0, ppos(j_esp_r, 15)[1]), (37.0, 18.5), (ppos(j_rfid, 1)[0], 18.5), ppos(j_rfid, 1)], width=1.1)

    # D. I2C LCD (SDA and SCL)
    route_track("I2C_SCL", [ppos(j_lcd, 4), (ppos(j_lcd, 4)[0], ppos(j_esp_r, 2)[1]), ppos(j_esp_r, 2)])
    route_track("I2C_SDA", [ppos(j_lcd, 3), (ppos(j_lcd, 3)[0], ppos(j_esp_r, 5)[1]), ppos(j_esp_r, 5)])

    # E. 4x4 Keypad - 8 Direct Monotonic Concentric Traces
    route_track("KEYPAD_R1", [ppos(j_esp_r, 1), ppos(j_keypad, 1)])
    route_track("KEYPAD_R2", [ppos(j_esp_r, 6), (58.0, ppos(j_esp_r, 6)[1]), (58.0, ppos(j_keypad, 2)[1]), ppos(j_keypad, 2)])
    route_track("KEYPAD_R3", [ppos(j_esp_r, 7), (60.2, ppos(j_esp_r, 7)[1]), (60.2, ppos(j_keypad, 3)[1]), ppos(j_keypad, 3)])
    route_track("KEYPAD_R4", [ppos(j_esp_r, 8), (62.4, ppos(j_esp_r, 8)[1]), (62.4, ppos(j_keypad, 4)[1]), ppos(j_keypad, 4)])
    route_track("KEYPAD_C1", [ppos(j_esp_r, 9), (64.6, ppos(j_esp_r, 9)[1]), (64.6, ppos(j_keypad, 5)[1]), ppos(j_keypad, 5)])
    route_track("KEYPAD_C2", [ppos(j_esp_r, 10), (66.8, ppos(j_esp_r, 10)[1]), (66.8, ppos(j_keypad, 6)[1]), ppos(j_keypad, 6)])
    route_track("KEYPAD_C3", [ppos(j_esp_r, 12), (69.0, ppos(j_esp_r, 12)[1]), (69.0, ppos(j_keypad, 7)[1]), ppos(j_keypad, 7)])
    route_track("KEYPAD_C4", [ppos(j_esp_r, 13), (71.2, ppos(j_esp_r, 13)[1]), (71.2, ppos(j_keypad, 8)[1]), ppos(j_keypad, 8)])

    # F. Bottom Signals
    # DOOR_RELAY: ESP_R Pin 11 (55.4, 51.4) west to X=52.5, south to Y=71.0, east to J_RELAY Pin 3 (63.08, 71.0), south into Pin 3
    route_track("DOOR_RELAY", [ppos(j_esp_r, 11), (52.5, ppos(j_esp_r, 11)[1]), (52.5, 71.0), (ppos(j_relay, 3)[0], 71.0), ppos(j_relay, 3)])

    # BUZZER: ESP_L Pin 13 (30.0, 56.48) east to X=34.5, south to Y=77.0, east to J_BUZZER Pin 1 (36.0, 77.0), south into Pin 1
    route_track("BUZZER", [ppos(j_esp_l, 13), (34.5, ppos(j_esp_l, 13)[1]), (34.5, 77.0), (ppos(j_buzzer, 1)[0], 77.0), ppos(j_buzzer, 1)])

    # LED_RED: ESP_L Pin 12 (30.0, 53.94) west to X=23.0, south to Y=74.0, east to J_LEDS Pin 2 (47.54, 74.0), south into Pin 2
    route_track("LED_RED", [ppos(j_esp_l, 12), (23.0, ppos(j_esp_l, 12)[1]), (23.0, 74.0), (ppos(j_leds, 2)[0], 74.0), ppos(j_leds, 2)])

    # LED_GREEN: ESP_L Pin 11 (30.0, 51.40) west to X=20.0, south to Y=76.0, east to J_LEDS Pin 1 (45.0, 76.0), south into Pin 1
    route_track("LED_GREEN", [ppos(j_esp_l, 11), (20.0, ppos(j_esp_l, 11)[1]), (20.0, 76.0), (ppos(j_leds, 1)[0], 76.0), ppos(j_leds, 1)])

    # G. Ground (GND) Rail (Heavy 1.3mm)
    # Horizontal GND bus at Y=85.0 from X=12.0 to X=58.0:
    route_track("GND", [ppos(j_power, 2), (ppos(j_power, 2)[0], 85.0), (ppos(c1, 2)[0], 85.0), ppos(c1, 2)], width=1.3)
    route_track("GND", [(ppos(c1, 2)[0], 85.0), (ppos(c2, 2)[0], 85.0), ppos(c2, 2)], width=1.3)
    route_track("GND", [(ppos(c2, 2)[0], 85.0), (ppos(j_buzzer, 2)[0], 85.0), ppos(j_buzzer, 2)], width=1.3)
    route_track("GND", [(ppos(j_buzzer, 2)[0], 85.0), (ppos(j_leds, 3)[0], 85.0), ppos(j_leds, 3)], width=1.3)
    route_track("GND", [(ppos(j_leds, 3)[0], 85.0), (ppos(j_relay, 1)[0], 85.0), ppos(j_relay, 1)], width=1.3)

    # GND into ESP_L Pin 14 via corridor at X=17.5:
    route_track("GND", [ppos(j_esp_l, 14), (17.5, ppos(j_esp_l, 14)[1]), (17.5, 85.0)], width=1.3)

    # GND north along far left edge (X=4.0) to J_RFID Pin 3 and J_LCD Pin 1
    route_track("GND", [(ppos(j_power, 2)[0], 85.0), (4.0, 85.0), (4.0, ppos(j_rfid, 3)[1]), ppos(j_rfid, 3)], width=1.3)
    route_track("GND", [(4.0, ppos(j_rfid, 3)[1]), (4.0, 6.0), (ppos(j_lcd, 1)[0], 6.0), ppos(j_lcd, 1)], width=1.3)

    # H. +5V Rail (Heavy 1.3mm)
    # +5V bus runs at Y=89.0:
    # 1. From J_POWER Pin 1 (17.08, 80.0) south to Y=89.0:
    route_track("+5V", [ppos(j_power, 1), (ppos(j_power, 1)[0], 89.0)], width=1.3)
    # Feed C1 and C2 Pad 1:
    route_track("+5V", [(ppos(j_power, 1)[0], 89.0), (ppos(c1, 1)[0], 89.0), ppos(c1, 1)], width=1.3)
    route_track("+5V", [(ppos(c1, 1)[0], 89.0), (ppos(c2, 1)[0], 89.0), ppos(c2, 1)], width=1.3)
    # Feed ESP_L Pin 15 (VIN):
    route_track("+5V", [(ppos(c2, 1)[0], 89.0), (30.0, 89.0), ppos(j_esp_l, 15)], width=1.3)
    # Feed J_RELAY Pin 2:
    route_track("+5V", [(30.0, 89.0), (ppos(j_relay, 2)[0], 89.0), ppos(j_relay, 2)], width=1.3)
    # Feed J_LCD Pin 2 via far right edge (X=81.0):
    route_track("+5V", [(ppos(j_relay, 2)[0], 89.0), (81.0, 89.0), (81.0, 6.0), (ppos(j_lcd, 2)[0], 6.0), ppos(j_lcd, 2)], width=1.3)

    # 7. Labels
    def add_label(txt, x, y, sz=1.2):
        t = pcbnew.PCB_TEXT(board)
        t.SetText(txt)
        t.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        t.SetLayer(pcbnew.F_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(sz), pcbnew.FromMM(sz)))
        t.SetTextThickness(pcbnew.FromMM(0.15))
        board.Add(t)

    add_label("VIDYUTRAKSHAK - DOOR CONTROLLER", 42.5, 3.5, sz=1.4)
    add_label("Vigyan Mela 2026 | Carrier Board", 42.5, 5.5, sz=1.0)
    add_label("ESP32 DevKit V1", 42.5, 48.0, sz=1.3)
    add_label("[USB at Bottom]", 42.5, 51.0, sz=1.0)

    out_path = "/Users/shreyansh/@nirman/hardware/door_security_pcb/door_security.kicad_pcb"
    pcbnew.SaveBoard(out_path, board)
    print("Board successfully generated!")

if __name__ == "__main__":
    build_pcb()
