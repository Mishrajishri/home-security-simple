import os, sys
import pcbnew

def generate_clean_pcb():
    board = pcbnew.BOARD()
    fp_dir = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"

    # Board size: 85mm wide x 95mm high (fits easily on 101.6 x 127mm copper blank)
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
        ref_text.SetVisible(True)

        # Hide value text to avoid clutter on PCB
        val_text = fp.Value()
        val_text.SetVisible(False)

        # Set pads to 1.8mm diameter with 1.0mm drill (standard for 2.54mm pitch)
        for pad in fp.Pads():
            pad.SetSize(pcbnew.VECTOR2I(pcbnew.FromMM(1.9), pcbnew.FromMM(1.9)))
            pad.SetDrillSize(pcbnew.VECTOR2I(pcbnew.FromMM(1.0), pcbnew.FromMM(1.0)))
        
        board.Add(fp)
        return fp

    # Placement
    # ESP32 Headers centered at X=30.0 and X=55.4 (25.4mm spacing)
    j_esp_l = place_clean_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x15_P2.54mm_Vertical", 
                             "J_ESP_L", "ESP32_L", 30.0, 26.0, ref_offset=(0, -4.0))
    j_esp_r = place_clean_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x15_P2.54mm_Vertical", 
                             "J_ESP_R", "ESP32_R", 55.4, 26.0, ref_offset=(0, -4.0))

    # RFID Header placed along left edge: X=10.0, Y=26.0 to 43.78
    j_rfid = place_clean_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x08_P2.54mm_Vertical", 
                            "J_RFID", "RFID_RC522", 10.0, 26.0, ref_offset=(0, -4.0))

    # LCD Header placed along top edge: X=45.0, Y=12.0
    j_lcd = place_clean_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x04_P2.54mm_Vertical", 
                           "J_LCD", "I2C_LCD", 45.0, 12.0, rot=90, ref_offset=(0, -4.0))

    # Keypad Header placed along right edge: X=75.0, Y=26.0 to 43.78
    j_keypad = place_clean_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x08_P2.54mm_Vertical", 
                              "J_KEYPAD", "Keypad_4x4", 75.0, 26.0, ref_offset=(0, -4.0))

    # Jumpers well spaced: JMP1 at Y=30.0, JMP2 at Y=37.0
    jmp1 = place_clean_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x02_P2.54mm_Vertical", 
                          "JMP1", "JMP_R3", 65.0, 30.0, rot=90, ref_offset=(0, -3.0))
    jmp2 = place_clean_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x02_P2.54mm_Vertical", 
                          "JMP2", "JMP_R4", 65.0, 37.0, rot=90, ref_offset=(0, -3.0))

    # Bottom Row Controls (Y = 82.0) with generous spacing
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

    # 6. Add clean, non-overlapping silkscreen text
    def add_label(txt, x, y, sz=1.2):
        t = pcbnew.PCB_TEXT(board)
        t.SetText(txt)
        t.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        t.SetLayer(pcbnew.F_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(sz), pcbnew.FromMM(sz)))
        board.Add(t)

    add_label("VIDYUTRAKSHAK - DOOR SECURITY", 42.5, 3.5, sz=1.5)
    add_label("Vigyan Mela 2026 | Carrier Board", 42.5, 6.0, sz=1.0)
    add_label("ESP32 DevKit V1", 42.5, 42.0, sz=1.3)
    add_label("[USB at Bottom]", 42.5, 45.0, sz=1.0)

    # Save
    out_path = "/Users/shreyansh/@nirman/hardware/door_security_pcb/door_security.kicad_pcb"
    pcbnew.SaveBoard(out_path, board)
    print("Saved clean board v2")

if __name__ == "__main__":
    generate_clean_pcb()
