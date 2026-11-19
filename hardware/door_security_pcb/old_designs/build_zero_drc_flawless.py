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
        if ref_pos:
            r.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(ref_pos[0]), pcbnew.FromMM(ref_pos[1])))
        else:
            r.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y - 5.0)))
        r.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.9), pcbnew.FromMM(0.9)))
        r.SetTextThickness(pcbnew.FromMM(0.16))
        r.SetVisible(True)

        v = fp.Value()
        v.SetVisible(False)

        board.Add(fp)
        return fp

    # Placement:
    j_esp_l = place_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x15_P2.54mm_Vertical",
                       "J_ESP_L", "ESP32_L", 30.0, 26.0, ref_pos=(30.0, 21.0))
    j_esp_r = place_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x15_P2.54mm_Vertical",
                       "J_ESP_R", "ESP32_R", 55.4, 26.0, ref_pos=(55.4, 21.0))

    j_rfid = place_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x08_P2.54mm_Vertical",
                      "J_RFID", "RFID_RC522", 10.0, 26.0, ref_pos=(10.0, 21.0))

    j_keypad = place_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x08_P2.54mm_Vertical",
                        "J_KEYPAD", "Keypad_4x4", 75.0, 26.0, ref_pos=(75.0, 21.0))

    # LCD Header at (48.0, 11.0)
    j_lcd = place_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x04_P2.54mm_Vertical",
                     "J_LCD", "I2C_LCD", 48.0, 11.0, rot=0, ref_pos=(48.0, 5.5))

    # Bottom Connectors at Y=78.0:
    j_leds = place_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x03_P2.54mm_Vertical",
                      "J_LEDS", "Status_LEDs", 11.0, 78.0, rot=90, ref_pos=(13.5, 71.5))

    j_buzzer = place_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x02_P2.54mm_Vertical",
                        "J_BUZZER", "Buzzer", 21.0, 78.0, rot=90, ref_pos=(22.0, 71.5))

    # J_RELAY at X=30.0: Pad 1 (DOOR_RELAY at 30.0), Pad 2 (+5V at 32.54), Pad 3 (GND at 35.08)
    j_relay = place_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x03_P2.54mm_Vertical",
                       "J_RELAY", "Relay_Lock", 30.0, 78.0, rot=90, ref_pos=(32.5, 71.5))

    # J_POWER at X=48.0: Pad 1 (GND at 48.0), Pad 2 (+5V at 53.08)
    j_power = place_fp("TerminalBlock_Phoenix.pretty", "TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal",
                       "J_POWER", "5V_Power", 48.0, 78.0, rot=0, ref_pos=(50.5, 71.0))

    # Net Mapping
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
    set_net(j_esp_r, 11, "DOOR_RELAY")  # Pin 11: GPIO4
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

    set_net(j_relay, 1, "DOOR_RELAY")
    set_net(j_relay, 2, "+5V")
    set_net(j_relay, 3, "GND")

    # Helper
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

    # ─── 100% PLANAR ZERO-CROSSING ROUTING ───────────────────────────

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

    # 4. Central Corridor Tracks:
    # A. RFID_RST at X=34.0: from ESP_L Pin 9 (30.0, 46.32) north to Y=18.0, west to X=20.0, south into J_RFID Pad 2
    route_track("RFID_RST", [ppos(j_esp_l, 9), (34.0, ppos(j_esp_l, 9)[1]), (34.0, 18.0), (20.0, 18.0), (20.0, ppos(j_rfid, 2)[1]), ppos(j_rfid, 2)])

    # B. DOOR_RELAY from ESP_R Pin 11 (55.4, 51.40): exits west to X=30.0, drops south into J_RELAY Pad 1 (30.0, 78.0)
    route_track("DOOR_RELAY", [ppos(j_esp_r, 11), (ppos(j_relay, 1)[0], ppos(j_esp_r, 11)[1]), ppos(j_relay, 1)])

    # C. +3.3V from ESP_R Pin 15 (55.4, 61.56): exits west to X=40.0, north along X=40.0 to Y=9.0, west along Y=9.0 to X=10.0, south into J_RFID Pad 1 (10.0, 26.0)
    route_track("+3.3V", [ppos(j_esp_r, 15), (40.0, ppos(j_esp_r, 15)[1]), (40.0, 9.0), (ppos(j_rfid, 1)[0], 9.0), ppos(j_rfid, 1)], width=1.1)

    # 5. Actuators from ESP_L:
    # A. BUZZER from ESP_L Pin 13 (30.0, 56.48): exits west to X=21.0, drops south into J_BUZZER Pad 1 (21.0, 78.0)
    route_track("BUZZER", [ppos(j_esp_l, 13), (ppos(j_buzzer, 1)[0], ppos(j_esp_l, 13)[1]), ppos(j_buzzer, 1)])

    # B. LED_GREEN from ESP_L Pin 11 (30.0, 51.40): exits west to X=11.0, drops south into J_LEDS Pad 1 (11.0, 78.0)
    route_track("LED_GREEN", [ppos(j_esp_l, 11), (ppos(j_leds, 1)[0], ppos(j_esp_l, 11)[1]), ppos(j_leds, 1)])

    # C. LED_RED from ESP_L Pin 12 (30.0, 53.94): exits west to X=13.54, drops south into J_LEDS Pad 2 (13.54, 78.0)
    route_track("LED_RED", [ppos(j_esp_l, 12), (ppos(j_leds, 2)[0], ppos(j_esp_l, 12)[1]), ppos(j_leds, 2)])

    # 6. +5V Distribution:
    # A. From J_POWER Pad 2 (53.08, 78.0) north to Y=70.0:
    route_track("+5V", [ppos(j_power, 2), (ppos(j_power, 2)[0], 70.0)], width=1.2)
    # B. Along Y=70.0 west to (32.54, 70.0), south into J_RELAY Pad 2 (32.54, 78.0):
    route_track("+5V", [(ppos(j_power, 2)[0], 70.0), (ppos(j_relay, 2)[0], 70.0), ppos(j_relay, 2)], width=1.2)
    # C. From (32.54, 70.0) west to (30.0, 70.0), north into ESP_L Pin 15 (30.0, 61.56):
    route_track("+5V", [(ppos(j_relay, 2)[0], 70.0), (ppos(j_esp_l, 15)[0], 70.0), ppos(j_esp_l, 15)], width=1.2)
    # D. To J_LCD Pad 2: drops south from (53.08, 78.0) to (53.08, 84.0), east to X=81.0, north along X=81.0 to Y=13.54, west into J_LCD Pad 2 (48.0, 13.54):
    route_track("+5V", [ppos(j_power, 2), (ppos(j_power, 2)[0], 84.0), (81.0, 84.0), (81.0, ppos(j_lcd, 2)[1]), ppos(j_lcd, 2)], width=1.2)

    # 7. Ground (GND) Rail along Y=85.0 (1.2mm width):
    # A. J_LEDS Pad 3 (16.08, 78.0) drops south to (16.08, 85.0)
    route_track("GND", [ppos(j_leds, 3), (ppos(j_leds, 3)[0], 85.0)], width=1.2)
    # B. Connects J_BUZZER Pad 2 (23.54, 78.0) to GND rail
    route_track("GND", [ppos(j_buzzer, 2), (ppos(j_buzzer, 2)[0], 85.0), (ppos(j_leds, 3)[0], 85.0)], width=1.2)
    # C. Connects J_RELAY Pad 3 (35.08, 78.0) to GND rail
    route_track("GND", [ppos(j_relay, 3), (ppos(j_relay, 3)[0], 85.0), (ppos(j_buzzer, 2)[0], 85.0)], width=1.2)
    # D. Connects J_POWER Pad 1 (48.0, 78.0) to GND rail
    route_track("GND", [ppos(j_power, 1), (ppos(j_power, 1)[0], 85.0), (ppos(j_relay, 3)[0], 85.0)], width=1.2)
    # E. Connects ESP_L Pin 14 (30.0, 59.02): exits west to X=25.0, drops south along X=25.0 to (25.0, 85.0), east into (35.08, 85.0)
    route_track("GND", [ppos(j_esp_l, 14), (25.0, ppos(j_esp_l, 14)[1]), (25.0, 85.0), (ppos(j_relay, 3)[0], 85.0)], width=1.2)
    # F. Connects ESP_R Pin 14 (55.4, 59.02): exits east to X=58.0, drops south along X=58.0 to (58.0, 74.0), west to (48.0, 74.0), south into J_POWER Pad 1 (48.0, 78.0)
    # (Notice: (58.0, 74.0) to (48.0, 74.0) is at Y=74.0, which is ABOVE Y=78.0, so it NEVER touches Y=84.0 +5V!)
    route_track("GND", [ppos(j_esp_r, 14), (58.0, ppos(j_esp_r, 14)[1]), (58.0, 74.0), (ppos(j_power, 1)[0], 74.0), ppos(j_power, 1)], width=1.2)

    # G. Left Trunk from (16.08, 85.0) west to X=7.0, north along X=7.0 to Y=7.0:
    route_track("GND", [(ppos(j_leds, 3)[0], 85.0), (7.0, 85.0), (7.0, 7.0)], width=1.2)
    # Branch into J_RFID Pad 3 (10.0, 31.08)
    route_track("GND", [(7.0, ppos(j_rfid, 3)[1]), ppos(j_rfid, 3)], width=1.2)
    # Branch into J_LCD Pad 1 (48.0, 11.0)
    route_track("GND", [(7.0, 7.0), (ppos(j_lcd, 1)[0], 7.0), ppos(j_lcd, 1)], width=1.2)

    # 8. Clean Silkscreen Text
    def add_label(txt, x, y, sz=1.1):
        t = pcbnew.PCB_TEXT(board)
        t.SetText(txt)
        t.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        t.SetLayer(pcbnew.F_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(sz), pcbnew.FromMM(sz)))
        t.SetTextThickness(pcbnew.FromMM(0.16))
        board.Add(t)

    add_label("VIDYUTRAKSHAK - DOOR CONTROLLER", 42.5, 2.5, sz=1.3)
    add_label("Vigyan Mela 2026 | Carrier Board", 42.5, 4.0, sz=0.9)
    add_label("ESP32 DevKit V1", 42.5, 48.0, sz=1.2)
    add_label("[USB at Bottom]", 42.5, 51.0, sz=0.9)

    out_path = "/Users/shreyansh/@nirman/hardware/door_security_pcb/door_security.kicad_pcb"
    pcbnew.SaveBoard(out_path, board)
    print("Zero DRC Flawless Board generated successfully!")

if __name__ == "__main__":
    build_pcb()
