import os, sys
import pcbnew

def build_routed_pcb():
    board = pcbnew.BOARD()
    fp_dir = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"

    # Board size: 85mm wide x 95mm high
    W, H = 85.0, 95.0

    # 1. Edge.Cuts
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

    # 2. Mounting holes (M3) at (5, 5), (80, 5), (5, 90), (80, 90)
    hole_lib = os.path.join(fp_dir, "MountingHole.pretty")
    holes = [(5.0, 5.0), (80.0, 5.0), (5.0, 90.0), (80.0, 90.0)]
    for i, (hx, hy) in enumerate(holes):
        h = pcbnew.FootprintLoad(hole_lib, "MountingHole_3.2mm_M3")
        h.SetReference(f"H{i+1}")
        h.SetValue("M3_Hole")
        h.Reference().SetVisible(False)
        h.Value().SetVisible(False)
        h.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(hx), pcbnew.FromMM(hy)))
        board.Add(h)

    # 3. Nets
    net_list = [
        "GND", "+5V", "+3.3V",
        "RFID_MISO", "RFID_MOSI", "RFID_SCK", "RFID_SDA_SS", "RFID_RST",
        "I2C_SDA", "I2C_SCL",
        "DOOR_RELAY", "BUZZER", "LED_GREEN", "LED_RED",
        "KEYPAD_R1", "KEYPAD_R2", "KEYPAD_R3_IN", "KEYPAD_R3_OUT",
        "KEYPAD_R4_IN", "KEYPAD_R4_OUT", "KEYPAD_C1", "KEYPAD_C2",
        "KEYPAD_C3", "KEYPAD_C4"
    ]
    nets = {}
    for n in net_list:
        item = pcbnew.NETINFO_ITEM(board, n)
        board.Add(item)
        nets[n] = item
    board.BuildListOfNets()

    # 4. Helper for placing footprints with clean silkscreen
    def place_clean_fp(lib, name, ref, val, x, y, rot=0, ref_offset=(0, -4.5)):
        path = os.path.join(fp_dir, lib)
        fp = pcbnew.FootprintLoad(path, name)
        fp.SetReference(ref)
        fp.SetValue(val)
        fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        if rot != 0:
            fp.SetOrientation(pcbnew.EDA_ANGLE(rot, pcbnew.DEGREES_T))
        
        # Position reference text cleanly outside pad area
        ref_text = fp.Reference()
        ref_text.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x + ref_offset[0]), pcbnew.FromMM(y + ref_offset[1])))
        ref_text.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(1.2), pcbnew.FromMM(1.2)))
        ref_text.SetTextThickness(pcbnew.FromMM(0.15))
        ref_text.SetVisible(True)

        val_text = fp.Value()
        val_text.SetVisible(False)

        # Set pads to 1.9mm diameter with 1.0mm drill for robust DIY etching
        for pad in fp.Pads():
            pad.SetSize(pcbnew.VECTOR2I(pcbnew.FromMM(1.9), pcbnew.FromMM(1.9)))
            pad.SetDrillSize(pcbnew.VECTOR2I(pcbnew.FromMM(1.0), pcbnew.FromMM(1.0)))
        
        board.Add(fp)
        return fp

    # Placement
    j_esp_l = place_clean_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x15_P2.54mm_Vertical", 
                             "J_ESP_L", "ESP32_L", 30.0, 26.0, ref_offset=(0, -4.0))
    j_esp_r = place_clean_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x15_P2.54mm_Vertical", 
                             "J_ESP_R", "ESP32_R", 55.4, 26.0, ref_offset=(0, -4.0))

    j_rfid = place_clean_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x08_P2.54mm_Vertical", 
                            "J_RFID", "RFID_RC522", 10.0, 26.0, ref_offset=(0, -4.0))

    j_lcd = place_clean_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x04_P2.54mm_Vertical", 
                           "J_LCD", "I2C_LCD", 45.0, 12.0, rot=90, ref_offset=(3.0, -4.0))

    j_keypad = place_clean_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x08_P2.54mm_Vertical", 
                              "J_KEYPAD", "Keypad_4x4", 75.0, 26.0, ref_offset=(0, -4.0))

    # Jumpers bridging from middle corridor (X=48.0) to near Keypad (X=67.0)
    # JMP1 for Row 3
    jmp1 = place_clean_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x02_P2.54mm_Vertical", 
                          "JMP1", "JMP_R3", 65.0, 31.08, rot=90, ref_offset=(0, -3.0))
    # JMP2 for Row 4
    jmp2 = place_clean_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x02_P2.54mm_Vertical", 
                          "JMP2", "JMP_R4", 65.0, 34.00, rot=90, ref_offset=(0, -3.0))

    # Bottom Row Controls (Y = 82.0)
    j_power = place_clean_fp("TerminalBlock_Phoenix.pretty", "TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal", 
                             "J_POWER", "5V_Power", 10.0, 82.0, ref_offset=(0, -6.5))
    c1 = place_clean_fp("Capacitor_THT.pretty", "CP_Radial_D6.3mm_P2.50mm", 
                        "C1", "100uF", 24.0, 82.0, ref_offset=(0, -5.0))
    c2 = place_clean_fp("Capacitor_THT.pretty", "C_Disc_D4.3mm_W1.9mm_P5.00mm", 
                        "C2", "0.1uF", 32.0, 82.0, ref_offset=(0, -5.0))
    j_buzzer = place_clean_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x02_P2.54mm_Vertical", 
                              "J_BUZZER", "Buzzer", 41.0, 82.0, ref_offset=(0, -4.0))
    j_leds = place_clean_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x03_P2.54mm_Vertical", 
                            "J_LEDS", "Status_LEDs", 50.0, 82.0, ref_offset=(0, -4.0))
    j_relay = place_clean_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x03_P2.54mm_Vertical", 
                             "J_RELAY", "Relay_Lock", 62.0, 82.0, ref_offset=(0, -4.0))

    # 5. Assign Nets to Pads
    def set_net(fp, pnum, nname):
        pad = fp.FindPadByNumber(str(pnum))
        if pad and nname in nets:
            pad.SetNet(nets[nname])

    # Left ESP Header
    l_map = {5: "RFID_MISO", 6: "RFID_MOSI", 7: "RFID_SCK", 8: "RFID_SDA_SS",
             9: "KEYPAD_R3_IN", 10: "KEYPAD_R4_IN", 11: "LED_GREEN", 12: "LED_RED",
             13: "BUZZER", 14: "GND", 15: "+5V"}
    for p, n in l_map.items(): set_net(j_esp_l, p, n)

    # Right ESP Header
    r_map = {1: "KEYPAD_R1", 2: "I2C_SCL", 5: "I2C_SDA", 6: "KEYPAD_R2",
             7: "RFID_RST", 8: "KEYPAD_C1", 9: "KEYPAD_C2", 10: "KEYPAD_C3",
             11: "DOOR_RELAY", 13: "KEYPAD_C4", 14: "GND", 15: "+3.3V"}
    for p, n in r_map.items(): set_net(j_esp_r, p, n)

    # Peripherals
    for p, n in {1: "+3.3V", 2: "RFID_RST", 3: "GND", 5: "RFID_MISO", 6: "RFID_MOSI", 7: "RFID_SCK", 8: "RFID_SDA_SS"}.items():
        set_net(j_rfid, p, n)
    for p, n in {1: "GND", 2: "+5V", 3: "I2C_SDA", 4: "I2C_SCL"}.items():
        set_net(j_lcd, p, n)
    for p, n in {1: "KEYPAD_R1", 2: "KEYPAD_R2", 3: "KEYPAD_R3_OUT", 4: "KEYPAD_R4_OUT", 5: "KEYPAD_C1", 6: "KEYPAD_C2", 7: "KEYPAD_C3", 8: "KEYPAD_C4"}.items():
        set_net(j_keypad, p, n)

    set_net(jmp1, 1, "KEYPAD_R3_IN")
    set_net(jmp1, 2, "KEYPAD_R3_OUT")
    set_net(jmp2, 1, "KEYPAD_R4_IN")
    set_net(jmp2, 2, "KEYPAD_R4_OUT")

    set_net(j_power, 1, "+5V"); set_net(j_power, 2, "GND")
    set_net(c1, 1, "+5V"); set_net(c1, 2, "GND")
    set_net(c2, 1, "+5V"); set_net(c2, 2, "GND")
    set_net(j_buzzer, 1, "BUZZER"); set_net(j_buzzer, 2, "GND")
    set_net(j_leds, 1, "LED_GREEN"); set_net(j_leds, 2, "LED_RED"); set_net(j_leds, 3, "GND")
    set_net(j_relay, 1, "GND"); set_net(j_relay, 2, "+5V"); set_net(j_relay, 3, "DOOR_RELAY")

    # 6. Helper for routing tracks
    def route(net_name, pts, w_mm=0.9):
        net = nets.get(net_name)
        for i in range(len(pts) - 1):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(pts[i][0]), pcbnew.FromMM(pts[i][1])))
            t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(pts[i+1][0]), pcbnew.FromMM(pts[i+1][1])))
            t.SetWidth(pcbnew.FromMM(w_mm))
            t.SetLayer(pcbnew.B_Cu)
            if net: t.SetNet(net)
            board.Add(t)

    def ppos(fp, pnum):
        pad = fp.FindPadByNumber(str(pnum))
        pos = pad.GetPosition()
        return (round(pos.x / 1e6, 3), round(pos.y / 1e6, 3))

    # ─── ROUTING ON B.Cu (Bottom Copper) ─────────────────────

    # 1. RFID SPI Data Lines (Straight horizontal lines!)
    route("RFID_MISO", [ppos(j_rfid, 5), ppos(j_esp_l, 5)])
    route("RFID_MOSI", [ppos(j_rfid, 6), ppos(j_esp_l, 6)])
    route("RFID_SCK", [ppos(j_rfid, 7), ppos(j_esp_l, 7)])
    route("RFID_SDA_SS", [ppos(j_rfid, 8), ppos(j_esp_l, 8)])

    # 2. RFID RST (Pin 2) -> routes north, then east across top of ESP32 to ESP_R Pin 7
    route("RFID_RST", [ppos(j_rfid, 2), (ppos(j_rfid, 2)[0], 20.0), (42.0, 20.0), (42.0, ppos(j_esp_r, 7)[1]), ppos(j_esp_r, 7)])

    # 3. RFID +3.3V (Pin 1) -> routes north, east at Y=17.0, down in middle corridor at X=38.0 to ESP_R Pin 15
    route("+3.3V", [ppos(j_rfid, 1), (ppos(j_rfid, 1)[0], 17.0), (38.0, 17.0), (38.0, ppos(j_esp_r, 15)[1]), ppos(j_esp_r, 15)], w_mm=1.2)

    # 4. I2C LCD (Pins 3 SDA and 4 SCL)
    route("I2C_SCL", [ppos(j_lcd, 4), (ppos(j_lcd, 4)[0], ppos(j_esp_r, 2)[1]), ppos(j_esp_r, 2)])
    route("I2C_SDA", [ppos(j_lcd, 3), (ppos(j_lcd, 3)[0], ppos(j_esp_r, 5)[1]), ppos(j_esp_r, 5)])

    # 5. Keypad Lines on Right Side
    # R1: Straight horizontal line!
    route("KEYPAD_R1", [ppos(j_esp_r, 1), ppos(j_keypad, 1)])

    # R2: ESP_R Pin 6 at (55.4, 38.70) -> goes east, then north to Keypad Pin 2 (75.0, 28.54)
    route("KEYPAD_R2", [ppos(j_esp_r, 6), (71.5, ppos(j_esp_r, 6)[1]), (71.5, ppos(j_keypad, 2)[1]), ppos(j_keypad, 2)])

    # Columns (C1, C2, C3, C4)
    route("KEYPAD_C1", [ppos(j_esp_r, 8), (61.0, ppos(j_esp_r, 8)[1]), (61.0, ppos(j_keypad, 5)[1]), ppos(j_keypad, 5)])
    route("KEYPAD_C2", [ppos(j_esp_r, 9), (59.0, ppos(j_esp_r, 9)[1]), (59.0, ppos(j_keypad, 6)[1]), ppos(j_keypad, 6)])
    route("KEYPAD_C3", [ppos(j_esp_r, 10), (57.5, ppos(j_esp_r, 10)[1]), (57.5, ppos(j_keypad, 7)[1]), ppos(j_keypad, 7)])
    route("KEYPAD_C4", [ppos(j_esp_r, 13), (73.0, ppos(j_esp_r, 13)[1]), (73.0, ppos(j_keypad, 8)[1]), ppos(j_keypad, 8)])

    # 6. Keypad Row 3 & 4 Jumpers:
    # Row 3: ESP_L Pin 9 to JMP1 Pad 1; JMP1 Pad 2 to Keypad Pin 3
    route("KEYPAD_R3_IN", [ppos(j_esp_l, 9), (35.0, ppos(j_esp_l, 9)[1]), (35.0, ppos(jmp1, 1)[1]), ppos(jmp1, 1)])
    route("KEYPAD_R3_OUT", [ppos(jmp1, 2), (ppos(j_keypad, 3)[0], ppos(jmp1, 2)[1]), ppos(j_keypad, 3)])

    # Row 4: ESP_L Pin 10 to JMP2 Pad 1; JMP2 Pad 2 to Keypad Pin 4
    route("KEYPAD_R4_IN", [ppos(j_esp_l, 10), (33.5, ppos(j_esp_l, 10)[1]), (33.5, ppos(jmp2, 1)[1]), ppos(jmp2, 1)])
    route("KEYPAD_R4_OUT", [ppos(jmp2, 2), (ppos(j_keypad, 4)[0], ppos(jmp2, 2)[1]), ppos(j_keypad, 4)])

    # 7. Bottom Controls
    # Buzzer (ESP_L Pin 13 to Buzzer Pin 1)
    route("BUZZER", [ppos(j_esp_l, 13), (35.0, ppos(j_esp_l, 13)[1]), (35.0, 75.0), (ppos(j_buzzer, 1)[0], 75.0), ppos(j_buzzer, 1)])

    # Green LED (ESP_L Pin 11 to LEDs Pin 1)
    route("LED_GREEN", [ppos(j_esp_l, 11), (21.0, ppos(j_esp_l, 11)[1]), (21.0, 74.0), (ppos(j_leds, 1)[0], 74.0), ppos(j_leds, 1)])

    # Red LED (ESP_L Pin 12 to LEDs Pin 2)
    route("LED_RED", [ppos(j_esp_l, 12), (19.0, ppos(j_esp_l, 12)[1]), (19.0, 76.0), (ppos(j_leds, 2)[0], 76.0), ppos(j_leds, 2)])

    # Door Relay (ESP_R Pin 11 to Relay Pin 3)
    route("DOOR_RELAY", [ppos(j_esp_r, 11), (ppos(j_relay, 3)[0], ppos(j_esp_r, 11)[1]), ppos(j_relay, 3)])

    # 8. Power Rail (+5V) Heavy 1.5mm trace along bottom and perimeter
    route("+5V", [ppos(j_power, 1), (ppos(j_power, 1)[0], 89.0), (ppos(c1, 1)[0], 89.0), ppos(c1, 1)], w_mm=1.5)
    route("+5V", [(ppos(c1, 1)[0], 89.0), (ppos(c2, 1)[0], 89.0), ppos(c2, 1)], w_mm=1.5)
    # Feed VIN on ESP_L Pin 15 from C1/C2
    route("+5V", [(ppos(c1, 1)[0], 89.0), (28.0, 89.0), (28.0, ppos(j_esp_l, 15)[1]), ppos(j_esp_l, 15)], w_mm=1.5)
    # 5V across to Relay Pin 2
    route("+5V", [(ppos(c2, 1)[0], 89.0), (ppos(j_relay, 2)[0], 89.0), ppos(j_relay, 2)], w_mm=1.5)
    # 5V up the far right edge to LCD Pin 2
    route("+5V", [(ppos(j_relay, 2)[0], 89.0), (81.0, 89.0), (81.0, 8.0), (ppos(j_lcd, 2)[0], 8.0), ppos(j_lcd, 2)], w_mm=1.5)

    # 9. Ground (GND) Bus on Bottom
    # Connects Power Pin 2, C1 Pin 2, C2 Pin 2, Buzzer Pin 2, LEDs Pin 3, Relay Pin 1 along Y = 85.5
    route("GND", [ppos(j_power, 2), (ppos(j_power, 2)[0], 86.0), (ppos(c1, 2)[0], 86.0), ppos(c1, 2)], w_mm=1.5)
    route("GND", [(ppos(c1, 2)[0], 86.0), (ppos(c2, 2)[0], 86.0), ppos(c2, 2)], w_mm=1.5)
    route("GND", [(ppos(c2, 2)[0], 86.0), (ppos(j_buzzer, 2)[0], 86.0), ppos(j_buzzer, 2)], w_mm=1.5)
    route("GND", [(ppos(j_buzzer, 2)[0], 86.0), (ppos(j_leds, 3)[0], 86.0), ppos(j_leds, 3)], w_mm=1.5)
    route("GND", [(ppos(j_leds, 3)[0], 86.0), (ppos(j_relay, 1)[0], 86.0), ppos(j_relay, 1)], w_mm=1.5)
    # GND into ESP_L Pin 14 and ESP_R Pin 14
    route("GND", [(ppos(j_buzzer, 2)[0], 86.0), (32.0, 86.0), (32.0, ppos(j_esp_l, 14)[1]), ppos(j_esp_l, 14)], w_mm=1.5)
    route("GND", [ppos(j_esp_l, 14), ppos(j_esp_r, 14)], w_mm=1.5)
    # GND to RFID Pin 3 and LCD Pin 1
    route("GND", [ppos(j_rfid, 3), (4.0, ppos(j_rfid, 3)[1]), (4.0, 86.0), (ppos(j_power, 2)[0], 86.0)], w_mm=1.5)
    route("GND", [(4.0, ppos(j_rfid, 3)[1]), (4.0, 10.0), (ppos(j_lcd, 1)[0], 10.0), ppos(j_lcd, 1)], w_mm=1.5)

    # 10. Silkscreen Labels
    def add_label(txt, x, y, sz=1.2):
        t = pcbnew.PCB_TEXT(board)
        t.SetText(txt)
        t.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        t.SetLayer(pcbnew.F_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(sz), pcbnew.FromMM(sz)))
        t.SetTextThickness(pcbnew.FromMM(0.15))
        board.Add(t)

    add_label("VIDYUTRAKSHAK - DOOR SECURITY", 42.5, 3.5, sz=1.5)
    add_label("Vigyan Mela 2026 | Carrier Board", 42.5, 5.5, sz=1.0)
    add_label("ESP32 DevKit V1", 42.5, 48.0, sz=1.3)
    add_label("[USB at Bottom]", 42.5, 51.0, sz=1.0)

    # Save
    out_path = "/Users/shreyansh/@nirman/hardware/door_security_pcb/door_security.kicad_pcb"
    pcbnew.SaveBoard(out_path, board)
    print("Successfully generated fully-routed PCB!")

if __name__ == "__main__":
    build_routed_pcb()
