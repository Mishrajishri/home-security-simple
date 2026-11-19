import pcbnew
import os
import sys

def miter_path(pts, delta=1.5):
    """Converts orthogonal track corners to 45-degree chamfers."""
    if len(pts) <= 2:
        return pts
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        p_prev = pts[i - 1]
        p_curr = pts[i]
        p_next = pts[i + 1]
        
        dx1 = p_curr[0] - p_prev[0]
        dy1 = p_curr[1] - p_prev[1]
        dx2 = p_next[0] - p_curr[0]
        dy2 = p_next[1] - p_curr[1]
        
        is_ortho = (dx1 == 0 and dy2 == 0 and dy1 != 0 and dx2 != 0) or \
                   (dy1 == 0 and dx2 == 0 and dx1 != 0 and dy2 != 0)
        
        l1 = (dx1**2 + dy1**2)**0.5
        l2 = (dx2**2 + dy2**2)**0.5
        
        d = min(delta, l1 * 0.40, l2 * 0.40)
        
        if is_ortho and d > 0.35:
            step1_x = - (dx1 / l1) * d
            step1_y = - (dy1 / l1) * d
            pt_a = (round(p_curr[0] + step1_x, 3), round(p_curr[1] + step1_y, 3))
            
            step2_x = (dx2 / l2) * d
            step2_y = (dy2 / l2) * d
            pt_b = (round(p_curr[0] + step2_x, 3), round(p_curr[1] + step2_y, 3))
            
            out.append(pt_a)
            out.append(pt_b)
        else:
            out.append(p_curr)
    out.append(pts[-1])
    return out

def build_board(filename="/Users/shreyansh/@nirman/hardware/light_fan_pcb/light_fan.kicad_pcb"):
    fp_dir = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints'
    pad_lib = 'TestPoint.pretty'
    pad_name = 'TestPoint_THTPad_D3.0mm_Drill1.5mm'

    board = pcbnew.BOARD()
    W, H = 100.0, 142.0

    ds = board.GetDesignSettings()
    ds.m_SolderMaskMinWidth = pcbnew.FromMM(0.10)
    ds.m_SolderMaskMargin = pcbnew.FromMM(0.08)

    # 1. Edge.Cuts (100mm x 142mm)
    for p1, p2 in [((0,0),(W,0)), ((W,0),(W,H)), ((W,H),(0,H)), ((0,H),(0,0))]:
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(p1[0]), pcbnew.FromMM(p1[1])))
        seg.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(p2[0]), pcbnew.FromMM(p2[1])))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(pcbnew.FromMM(0.20))
        board.Add(seg)

    # 2. Nets
    net_names = [
        'GND', '+5V',
        'RELAY_1', 'RELAY_2', 'RELAY_3', 'RELAY_4',
        'Q1_BASE', 'Q2_BASE', 'Q3_BASE', 'Q4_BASE',
        'Q1_COLL', 'Q2_COLL', 'Q3_COLL', 'Q4_COLL',
        'LED1_K', 'LED2_K', 'LED3_K', 'LED4_K',
        'AC_IN', 'OUT1', 'OUT2', 'OUT3', 'OUT4',
        'GAS_A0', 'ESP_GAS', 'PIR_OUT',
        'ESP_LED', 'STAT_LED_K', 'PWR_LED'
    ]
    nets = {}
    for name in net_names:
        item = pcbnew.NETINFO_ITEM(board, name)
        board.Add(item)
        nets[name] = item
    board.BuildListOfNets()

    def place_fp(lib, name, ref, val, x, y, rot=0, pad_sz=None, drill_sz=None, clear_graphics=False):
        path = os.path.join(fp_dir, lib)
        fp = pcbnew.FootprintLoad(path, name)
        fp.SetReference(ref)
        fp.SetValue(val)
        fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        if rot != 0:
            fp.SetOrientation(pcbnew.EDA_ANGLE(rot, pcbnew.DEGREES_T))
        for pad in fp.Pads():
            if pad_sz:
                pad.SetSize(pcbnew.VECTOR2I(pcbnew.FromMM(pad_sz[0]), pcbnew.FromMM(pad_sz[1])))
            if drill_sz:
                pad.SetDrillSize(pcbnew.VECTOR2I(pcbnew.FromMM(drill_sz[0]), pcbnew.FromMM(drill_sz[1])))
        if 'PAD_' in ref or 'J' in ref or clear_graphics:
            fp.GraphicalItems().clear()
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        board.Add(fp)
        return fp

    def set_net(fp, pnum, net_name):
        pad = fp.FindPadByNumber(str(pnum))
        if pad and net_name in nets:
            pad.SetNet(nets[net_name])

    def ppos(fp, pnum):
        p = fp.FindPadByNumber(str(pnum))
        pos = p.GetPosition()
        return (round(pos.x / 1e6, 3), round(pos.y / 1e6, 3))

    def route(net_name, pts, width=1.0, layer=pcbnew.B_Cu, miter=True, delta=1.5):
        if miter and len(pts) > 2:
            pts = miter_path(pts, delta=delta)
        net = nets.get(net_name)
        for i in range(len(pts) - 1):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(pts[i][0]), pcbnew.FromMM(pts[i][1])))
            t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(pts[i+1][0]), pcbnew.FromMM(pts[i+1][1])))
            t.SetWidth(pcbnew.FromMM(width))
            t.SetLayer(layer)
            if net: t.SetNet(net)
            board.Add(t)

    # 3. Mounting Holes
    place_fp('MountingHole.pretty', 'MountingHole_3.2mm_M3', 'H1', 'M3_Hole', 5.0, 5.0)
    place_fp('MountingHole.pretty', 'MountingHole_3.2mm_M3', 'H2', 'M3_Hole', 95.0, 5.0)
    place_fp('MountingHole.pretty', 'MountingHole_3.2mm_M3', 'H3', 'M3_Hole', 5.0, 137.0)
    place_fp('MountingHole.pretty', 'MountingHole_3.2mm_M3', 'H4', 'M3_Hole', 95.0, 137.0)

    pad_cfg_heavy = {'pad_sz': (3.6, 3.6), 'drill_sz': (1.4, 1.4)}
    r_cfg         = {'pad_sz': (2.2, 2.2), 'drill_sz': (1.0, 1.0)}
    d_cfg         = {'pad_sz': (2.4, 2.4), 'drill_sz': (1.1, 1.1)}
    q_cfg         = {'pad_sz': (2.0, 2.0), 'drill_sz': (0.90, 0.90)}
    led_cfg       = {'pad_sz': (2.0, 2.0), 'drill_sz': (0.9, 0.9)}
    hdr_cfg       = {'pad_sz': (1.9, 1.9), 'drill_sz': (1.0, 1.0)}
    jmp_cfg       = {'pad_sz': (2.3, 2.3), 'drill_sz': (1.0, 1.0)}

    # 4. Solder Terminal Wire Pads
    pad_ac_in = place_fp(pad_lib, pad_name, 'PAD_AC_IN', 'AC_LINE', 93.0, 14.0, **pad_cfg_heavy)
    pad_out1  = place_fp(pad_lib, pad_name, 'PAD_OUT1', 'OUT1', 93.0, 34.05, **pad_cfg_heavy)
    pad_out2  = place_fp(pad_lib, pad_name, 'PAD_OUT2', 'OUT2', 93.0, 62.05, **pad_cfg_heavy)
    pad_out3  = place_fp(pad_lib, pad_name, 'PAD_OUT3', 'OUT3', 93.0, 90.05, **pad_cfg_heavy)
    pad_out4  = place_fp(pad_lib, pad_name, 'PAD_OUT4', 'OUT4', 93.0, 118.05, **pad_cfg_heavy)

    pad_5v    = place_fp(pad_lib, pad_name, 'PAD_5V', '5V_IN', 35.0, 131.0, **pad_cfg_heavy)
    pad_gnd   = place_fp(pad_lib, pad_name, 'PAD_GND', 'GND_IN', 43.0, 131.0, **pad_cfg_heavy)

    set_net(pad_ac_in, 1, 'AC_IN')
    set_net(pad_out1, 1, 'OUT1')
    set_net(pad_out2, 1, 'OUT2')
    set_net(pad_out3, 1, 'OUT3')
    set_net(pad_out4, 1, 'OUT4')
    set_net(pad_5v, 1, '+5V')
    set_net(pad_gnd, 1, 'GND')

    # 5. ESP32 DevKit V1 Headers - EXACT 25.40mm (1.00 inch) Row Pitch!
    j_esp_l = place_fp('Connector_PinHeader_2.54mm.pretty', 'PinHeader_1x15_P2.54mm_Vertical', 'J_ESP_L', 'ESP32_L', 8.0, 40.0, **hdr_cfg)
    j_esp_r = place_fp('Connector_PinHeader_2.54mm.pretty', 'PinHeader_1x15_P2.54mm_Vertical', 'J_ESP_R', 'ESP32_R', 33.40, 40.0, **hdr_cfg)

    set_net(j_esp_l, 4, 'ESP_GAS')  # GPIO 34 (47.62)
    set_net(j_esp_l, 10, 'PIR_OUT') # GPIO 27 (62.86)
    set_net(j_esp_l, 14, 'GND')     # GND     (73.02)
    set_net(j_esp_l, 15, '+5V')     # VIN     (75.56)

    set_net(j_esp_r, 1, 'RELAY_1')  # GPIO 23 (40.00)
    set_net(j_esp_r, 2, 'RELAY_2')  # GPIO 22 (42.54)
    set_net(j_esp_r, 6, 'RELAY_3')  # GPIO 19 (52.70)
    set_net(j_esp_r, 7, 'RELAY_4')  # GPIO 18 (55.24)
    set_net(j_esp_r, 12, 'ESP_LED') # GPIO 2  (67.94)
    set_net(j_esp_r, 14, 'GND')     # GND     (73.02)

    # 6. Four Spacious Relay Channels (Y = 28, 56, 84, 112)
    y_relays = [28.0, 56.0, 84.0, 112.0]
    y_rbase = [18.0, 46.0, 78.0, 106.0]
    relays, diodes, transistors, r_base, r_pldn, leds, r_leds = [], [], [], [], [], [], []

    for i, yr in enumerate(y_relays):
        idx = i + 1
        # Relay Songle SRD-05VDC at X=66.0
        k = place_fp('Relay_THT.pretty', 'Relay_SPDT_SANYOU_SRD_Series_Form_C', f'K{idx}', 'SRD-05VDC', 66.0, yr)
        for p in k.Pads():
            p.SetSize(pcbnew.VECTOR2I(pcbnew.FromMM(3.0), pcbnew.FromMM(3.0)))
            p.SetDrillSize(pcbnew.VECTOR2I(pcbnew.FromMM(1.3), pcbnew.FromMM(1.3)))
        relays.append(k)

        # Diode DO-41 rot=90 at X=61.0: Pad 1 (+5V) at (61.0, yr+6.05); Pad 2 (COLL) at (61.0, yr-4.11)
        d = place_fp('Diode_THT.pretty', 'D_DO-41_SOD81_P10.16mm_Horizontal', f'D{idx}', '1N4007', 61.0, yr + 6.05, rot=90, clear_graphics=True, **d_cfg)
        diodes.append(d)

        # Transistor BC337 rot=180 at X=48.0: Pad 1 (COLL) at (48.0, yr-4.11); Pad 2 (Base) at (45.46, yr-4.11); Pad 3 (Emit) at (42.92, yr-4.11)
        q = place_fp('Package_TO_SOT_THT.pretty', 'TO-92_Wide', f'Q{idx}', 'BC337', 48.0, yr - 4.11, rot=180, clear_graphics=True, **q_cfg)
        transistors.append(q)

        # LED Resistor 1k rot=90 at X=55.0: Pad 1 at (55.0, yr+3.51); Pad 2 at (55.0, yr-4.11)
        rl = place_fp('Resistor_THT.pretty', 'R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal', f'R_LED{idx}', '1k', 55.0, yr + 3.51, rot=90, clear_graphics=True, **r_cfg)
        r_leds.append(rl)

        # Active LED rot=270 at (51.0, yr+3.51): Pad 1 (K) at (51.0, yr+3.51); Pad 2 (A) at (51.0, yr+6.05)
        led = place_fp('LED_THT.pretty', 'LED_D3.0mm', f'LED{idx}', 'Red', 51.0, yr + 3.51, rot=270, clear_graphics=True, **led_cfg)
        leds.append(led)

        # Base Resistor 1k rot=0 at (37.84, y_rbase[i]): Pad 1 at (37.84, y_rbase[i]); Pad 2 at (45.46, y_rbase[i])
        rb = place_fp('Resistor_THT.pretty', 'R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal', f'R{idx}', '1k', 37.84, y_rbase[i], clear_graphics=True, **r_cfg)
        r_base.append(rb)

        # Pull-down Resistor 10k rot=90 at (45.46, yr-14.0): Pad 1 at (45.46, yr-14.0); Pad 2 at (45.46, yr-21.62)
        rpd = place_fp('Resistor_THT.pretty', 'R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal', f'RPD{idx}', '10k', 45.46, yr - 14.0, rot=90, clear_graphics=True, **r_cfg)
        r_pldn.append(rpd)

        # Net Assignments
        set_net(k, 1, 'AC_IN'); set_net(k, 2, '+5V'); set_net(k, 3, f'OUT{idx}'); set_net(k, 5, f'Q{idx}_COLL')
        set_net(d, 1, '+5V'); set_net(d, 2, f'Q{idx}_COLL')
        set_net(q, 1, f'Q{idx}_COLL'); set_net(q, 2, f'Q{idx}_BASE'); set_net(q, 3, 'GND')
        set_net(led, 2, '+5V'); set_net(led, 1, f'LED{idx}_K')
        set_net(rl, 1, f'LED{idx}_K'); set_net(rl, 2, f'Q{idx}_COLL')
        set_net(rb, 1, f'RELAY_{idx}'); set_net(rb, 2, f'Q{idx}_BASE')
        set_net(rpd, 1, f'Q{idx}_BASE'); set_net(rpd, 2, 'GND')

    # 7. Wire Jumpers
    # J1: +5V Main Link from West across Driver GND trunk at Y=125.0
    jmp_5v = place_fp('Resistor_THT.pretty', 'R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal', 'J1', 'WIRE_JUMPER', 36.0, 125.0, clear_graphics=True, **jmp_cfg)
    set_net(jmp_5v, 1, '+5V'); set_net(jmp_5v, 2, '+5V')
    route('+5V', [ppos(jmp_5v, 1), ppos(jmp_5v, 2)], width=1.00, layer=pcbnew.F_Cu, miter=False)

    # 3 Relay Coil +5V bus jumpers across Collector lines at X=58.0 (Pitch 10.16mm)
    jmp_ch = []
    for i in range(1, 4):
        yr = y_relays[i]
        j = place_fp('Resistor_THT.pretty', 'R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal', f'J{i+1}', 'WIRE_JUMPER', 58.0, yr - 1.0, rot=90, clear_graphics=True, **jmp_cfg)
        set_net(j, 1, '+5V'); set_net(j, 2, '+5V')
        jmp_ch.append(j)
        route('+5V', [ppos(j, 1), ppos(j, 2)], width=1.00, layer=pcbnew.F_Cu, miter=False)

    # J5: GND Link from J_ESP_R Pin 14 across ESP_LED track at Y=73.02
    j_gnd = place_fp('Resistor_THT.pretty', 'R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal', 'J5', 'WIRE_JUMPER', 30.0, 73.02, rot=180, clear_graphics=True, **jmp_cfg)
    set_net(j_gnd, 1, 'GND'); set_net(j_gnd, 2, 'GND')
    route('GND', [ppos(j_esp_r, 14), ppos(j_gnd, 1)], width=1.00, miter=False)
    route('GND', [ppos(j_gnd, 1), ppos(j_gnd, 2)], width=1.00, layer=pcbnew.F_Cu, miter=False)
    route('GND', [ppos(j_gnd, 2), (21.0, 73.02)], width=1.00, miter=False)

    # J6: PIR_OUT Link across J_ESP_L GND connection at Y=73.02
    j_pir_out = place_fp('Resistor_THT.pretty', 'R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal', 'J6', 'WIRE_JUMPER', 12.54, 78.0, rot=90, clear_graphics=True, **jmp_cfg)
    set_net(j_pir_out, 1, 'PIR_OUT'); set_net(j_pir_out, 2, 'PIR_OUT')
    route('PIR_OUT', [ppos(j_pir_out, 1), ppos(j_pir_out, 2)], width=0.85, layer=pcbnew.F_Cu, miter=False)

    # 8. High-Voltage AC Mains Routing (2.80mm Ultra-Thick Traces)
    out_pads = [pad_out1, pad_out2, pad_out3, pad_out4]
    for i in range(4):
        route(f'OUT{i+1}', [ppos(relays[i], 3), ppos(out_pads[i], 1)], width=2.80, miter=False)

    # AC COM Live In: Vertical trunk at X=74.5mm from Y=14.0 to Y=112.0
    route('AC_IN', [ppos(pad_ac_in, 1), (74.5, 14.0), (74.5, y_relays[3])], width=2.80, delta=1.5)
    for i in range(4):
        route('AC_IN', [ppos(relays[i], 1), (74.5, y_relays[i])], width=2.80, miter=False)

    # 9. Low-Voltage Channel Connections
    for i in range(4):
        idx = i + 1
        yr = y_relays[i]

        # Collector Line at Y = yr - 4.11: Q Pin 1 -> R_LED Pad 2 -> D Pad 2 -> Relay Pad 5
        route(f'Q{idx}_COLL', [
            ppos(transistors[i], 1),
            ppos(r_leds[i], 2),
            ppos(diodes[i], 2),
            (67.95, yr - 4.11),
            ppos(relays[i], 5)
        ], width=1.20, miter=False)

        # LED Cathode: LED Pad 1 -> R_LED Pad 1
        route(f'LED{idx}_K', [ppos(leds[i], 1), ppos(r_leds[i], 1)], width=0.85, miter=False)

        # Channel +5V: LED Pad 2 -> Diode Pad 1 -> Relay Pad 2
        route('+5V', [ppos(leds[i], 2), (ppos(diodes[i], 1)[0], ppos(leds[i], 2)[1]), ppos(diodes[i], 1), ppos(relays[i], 2)], width=1.30, miter=False)

        # Base Line at X=45.46: R_base Pad 2 -> R_pldn Pad 1 -> Transistor Pin 2
        route(f'Q{idx}_BASE', [ppos(r_base[i], 2), ppos(r_pldn[i], 1), ppos(transistors[i], 2)], width=0.85, miter=False)

        # R_pldn Pad 2 to GND trunk at X=42.92
        route('GND', [ppos(r_pldn[i], 2), (42.92, ppos(r_pldn[i], 2)[1])], width=1.00, miter=False)

    # Main Driver GND Trunk at X=42.92: Starts at Y=6.0 and goes down to PAD_GND (Y=131.0)
    route('GND', [(42.92, 6.0), (42.92, 131.0), ppos(pad_gnd, 1)], width=1.40, miter=False)

    # Top GND crossbar at Y=6.0: Continuous from (42.92, 6.0) to (12.54, 6.0)
    route('GND', [(42.92, 6.0), (21.0, 6.0)], width=1.20, miter=False)
    route('GND', [(21.0, 6.0), (12.54, 6.0)], width=1.20, miter=False)

    # Vertical Relay Coil +5V Bus at X=58.0 using the 3 jumpers
    # CH1 to CH2
    route('+5V', [ppos(diodes[0], 1), (58.0, ppos(diodes[0], 1)[1]), ppos(jmp_ch[0], 2)], width=1.30, delta=0.5)
    route('+5V', [ppos(jmp_ch[0], 1), (58.0, ppos(diodes[1], 1)[1]), ppos(diodes[1], 1)], width=1.30, delta=0.5)

    # CH2 to CH3
    route('+5V', [ppos(diodes[1], 1), (58.0, ppos(diodes[1], 1)[1]), ppos(jmp_ch[1], 2)], width=1.30, delta=0.5)
    route('+5V', [ppos(jmp_ch[1], 1), (58.0, ppos(diodes[2], 1)[1]), ppos(diodes[2], 1)], width=1.30, delta=0.5)

    # CH3 to CH4
    route('+5V', [ppos(diodes[2], 1), (58.0, ppos(diodes[2], 1)[1]), ppos(jmp_ch[2], 2)], width=1.30, delta=0.5)
    route('+5V', [ppos(jmp_ch[2], 1), (58.0, ppos(diodes[3], 1)[1]), ppos(diodes[3], 1)], width=1.30, delta=0.5)

    # From Diode 4 Pad 1 south to J1 Pad 2 (46.16, 125.0)
    route('+5V', [ppos(diodes[3], 1), (58.0, ppos(diodes[3], 1)[1]), (58.0, 125.0), ppos(jmp_5v, 2)], width=1.40, delta=1.0)

    # 10. GPIO Connections from ESP32 Right Header to Base Resistors
    # Concentric Routing:
    # RELAY_1 (GPIO 23): North to CH1
    route('RELAY_1', [ppos(j_esp_r, 1), (35.0, ppos(j_esp_r, 1)[1]), (35.0, y_rbase[0]), ppos(r_base[0], 1)], width=0.85, delta=0.5)
    # RELAY_2 (GPIO 22): East to CH2
    route('RELAY_2', [ppos(j_esp_r, 2), (37.84, ppos(j_esp_r, 2)[1]), ppos(r_base[1], 1)], width=0.85, delta=0.5)

    # RELAY_3 (GPIO 19 at 33.40, 52.70): Out East to X=39.5, down to Y=78.0, into R3 Pad 1
    route('RELAY_3', [ppos(j_esp_r, 6), (39.5, ppos(j_esp_r, 6)[1]), (39.5, y_rbase[2]), ppos(r_base[2], 1)], width=0.85, delta=0.5)

    # RELAY_4 (GPIO 18 at 33.40, 55.24): Runs along X=35.0, down to Y=106.0, into R4 Pad 1
    route('RELAY_4', [ppos(j_esp_r, 7), (35.0, ppos(j_esp_r, 7)[1]), (35.0, y_rbase[3]), ppos(r_base[3], 1)], width=0.85, delta=0.5)

    # 11. Sensors (PIR and MQ-2)
    # Internal GND Spine runs down X=21.0 from top bar (21.0, 6.0) to C2 Pad 2 at (21.0, 115.0) - EXACT ENDPOINT!
    route('GND', [(21.0, 6.0), (21.0, 115.0)], width=1.20, miter=False)

    # J_ESP_L Pin 14 (GND at 8.0, 73.02) connects East to (21.0, 73.02) on the GND spine
    route('GND', [ppos(j_esp_l, 14), (21.0, 73.02)], width=1.20, miter=False)

    # Gas Sensor MQ-2 at X=10.0, Y=14.0 (Top-Left)
    j_gas = place_fp('Connector_PinHeader_2.54mm.pretty', 'PinHeader_1x04_P2.54mm_Vertical', 'J_GAS', 'MQ-2', 10.0, 14.0, rot=90, clear_graphics=True, **hdr_cfg)
    set_net(j_gas, 1, '+5V'); set_net(j_gas, 2, 'GND'); set_net(j_gas, 4, 'GAS_A0')

    # Gas GND connects North to top GND bar at (12.54, 6.0)
    route('GND', [ppos(j_gas, 2), (12.54, 6.0)], width=1.00, miter=False)

    # Voltage divider for Gas sensor: RDIV1 (10k) and RDIV2 (20k)
    rdiv1 = place_fp('Resistor_THT.pretty', 'R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal', 'RDIV1', '10k', 10.0, 22.0, clear_graphics=True, **r_cfg)
    rdiv2 = place_fp('Resistor_THT.pretty', 'R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal', 'RDIV2', '20k', 10.0, 28.0, clear_graphics=True, **r_cfg)
    set_net(rdiv1, 1, 'ESP_GAS'); set_net(rdiv1, 2, 'GAS_A0')
    set_net(rdiv2, 1, 'ESP_GAS'); set_net(rdiv2, 2, 'GND')

    route('GAS_A0', [ppos(j_gas, 4), ppos(rdiv1, 2)], width=0.85, miter=False)
    # RDIV2 Pad 2 (GND at 17.62, 28.0) connects East to GND spine at (21.0, 28.0)
    route('GND', [ppos(rdiv2, 2), (21.0, ppos(rdiv2, 2)[1])], width=0.85, miter=False)
    route('ESP_GAS', [ppos(rdiv1, 1), ppos(rdiv2, 1), (10.0, 47.62), ppos(j_esp_l, 4)], width=0.85, delta=1.0)

    # PIR Motion Sensor HORIZONTAL rot=90 at X=10.0, Y=90.0
    # Pad 1 (+5V) at (10.0, 90.0); Pad 2 (PIR_OUT) at (12.54, 90.0); Pad 3 (GND) at (15.08, 90.0)
    j_pir = place_fp('Connector_PinHeader_2.54mm.pretty', 'PinHeader_1x03_P2.54mm_Vertical', 'J_PIR', 'HC-SR501', 10.0, 90.0, rot=90, clear_graphics=True, **hdr_cfg)
    set_net(j_pir, 1, '+5V'); set_net(j_pir, 2, 'PIR_OUT'); set_net(j_pir, 3, 'GND')

    # PIR +5V connects straight West to (8.0, 90.0) on the +5V bus
    route('+5V', [ppos(j_pir, 1), (8.0, 90.0)], width=1.00, miter=False)
    # PIR GND connects straight East to GND spine at (21.0, 90.0)
    route('GND', [ppos(j_pir, 3), (21.0, 90.0)], width=1.00, miter=False)

    # PIR_OUT routes North from Pad 2 (12.54, 90.0) straight into J6 Pad 1 at (12.54, 78.0)
    route('PIR_OUT', [ppos(j_pir, 2), ppos(j_pir_out, 1)], width=0.85, miter=False)
    # From J6 Pad 2 at (12.54, 68.0) straight North to Y=62.86, into J_ESP_L Pin 10 (8.0, 62.86)
    route('PIR_OUT', [ppos(j_pir_out, 2), (12.54, 62.86), ppos(j_esp_l, 10)], width=0.85, delta=0.5)

    # 12. Status LED (GPIO 2) in wide open bottom-left area at Y=85.0
    led_stat = place_fp('LED_THT.pretty', 'LED_D3.0mm', 'LED_STAT', 'Blue', 28.0, 85.0, rot=90, clear_graphics=True, **led_cfg)
    r_stat   = place_fp('Resistor_THT.pretty', 'R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal', 'R_STAT', '470R', 24.0, 85.0, rot=180, clear_graphics=True, **r_cfg)

    set_net(led_stat, 2, 'ESP_LED'); set_net(led_stat, 1, 'STAT_LED_K')
    set_net(r_stat, 1, 'STAT_LED_K'); set_net(r_stat, 2, 'GND')

    # ESP_LED connects from J_ESP_R Pin 12 (33.40, 67.94) into socket at X=26.0, down to Y=82.46, into Pad 2 (28.0, 82.46)
    route('ESP_LED', [ppos(j_esp_r, 12), (26.0, ppos(j_esp_r, 12)[1]), (26.0, 82.46), ppos(led_stat, 2)], width=0.85, delta=0.5)
    # Cathode connects LED Pad 1 (28.0, 85.0) to R_STAT Pad 1 (24.0, 85.0)
    route('STAT_LED_K', [ppos(led_stat, 1), ppos(r_stat, 1)], width=0.85, miter=False)
    # R_STAT Pad 2 (16.38, 85.0) connects East to GND spine at (21.0, 85.0)
    route('GND', [ppos(r_stat, 2), (21.0, 85.0)], width=0.85, miter=False)

    # 13. DC Power Distribution
    # +5V Power In: from PAD_5V (35.0, 131.0) to J1 Pad 1 at (36.0, 125.0)
    route('+5V', [ppos(pad_5v, 1), (35.0, 125.0), ppos(jmp_5v, 1)], width=1.60, miter=False)
    # +5V branch West across open space at Y=125.0 to X=8.0, then straight North into ESP32 VIN at (8.0, 75.56)
    route('+5V', [(35.0, 125.0), (8.0, 125.0), ppos(j_esp_l, 15)], width=1.40, delta=1.0)

    # +5V extends West to X=2.0 at Y=125.0, and runs North along X=2.0 all the way to Y=14.0 for J_GAS
    route('+5V', [(8.0, 125.0), (2.0, 125.0), (2.0, 14.0), ppos(j_gas, 1)], width=1.20, delta=1.0)

    # 14. Bulk & Decoupling Capacitors (C1, C2) - Horizontal (rot=0)
    c1 = place_fp('Capacitor_THT.pretty', 'CP_Radial_D8.0mm_P3.50mm', 'C1', '470uF', 8.0, 105.0, rot=0, clear_graphics=True)
    set_net(c1, 1, '+5V'); set_net(c1, 2, 'GND')
    c2 = place_fp('Capacitor_THT.pretty', 'C_Disc_D5.0mm_W2.5mm_P5.00mm', 'C2', '100nF', 8.0, 115.0, rot=0, clear_graphics=True)
    set_net(c2, 1, '+5V'); set_net(c2, 2, 'GND')

    # C1, C2 Pad 1 (+5V at X=8.0) is directly on the +5V bus running along X=8.0!
    # C1, C2 Pad 2 (GND at X=11.5, 13.0) connects East to GND spine at X=21.0
    route('GND', [ppos(c1, 2), (21.0, ppos(c1, 2)[1])], width=1.20, miter=False)
    route('GND', [ppos(c2, 2), (21.0, ppos(c2, 2)[1])], width=1.20, miter=False)

    # 15. Power Indicator LED (Green) & Resistor - Placed SOUTH of Y=125.0!
    # R_PWR at (12.0, 136.0) rot=0 (Pad 1 at 12.0, Pad 2 at 19.62)
    # LED_PWR at (27.0, 136.0) rot=180 (Pad 1 at 27.0, Pad 2 at 24.46)
    r_pwr   = place_fp('Resistor_THT.pretty', 'R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal', 'R_PWR', '1k', 12.0, 136.0, clear_graphics=True, **r_cfg)
    led_pwr = place_fp('LED_THT.pretty', 'LED_D3.0mm', 'LED_PWR', 'Green', 27.0, 136.0, rot=180, clear_graphics=True, **led_cfg)
    set_net(r_pwr, 1, '+5V'); set_net(r_pwr, 2, 'PWR_LED')
    set_net(led_pwr, 2, 'PWR_LED'); set_net(led_pwr, 1, 'GND')

    # R_PWR Pad 1 at (12.0, 136.0) connects North to +5V at (12.0, 125.0)
    route('+5V', [ppos(r_pwr, 1), (12.0, 125.0)], width=0.85, miter=False)
    # Series connection between R_PWR Pad 2 (19.62, 136.0) and LED_PWR Pad 2 (24.46, 136.0)
    route('PWR_LED', [ppos(r_pwr, 2), ppos(led_pwr, 2)], width=0.85, miter=False)
    # LED_PWR Pad 1 (GND at 27.0, 136.0) connects East along Y=136.0 to (43.0, 136.0) -> PAD_GND
    route('GND', [ppos(led_pwr, 1), (43.0, 136.0), ppos(pad_gnd, 1)], width=1.00, miter=False)

    # 16. Silkscreen Labels - Placed in wide open areas!
    silkscreen_texts = [
        ("VIDYUTRAKSHAK 4CH CONTROLLER", 50.0, 3.0, 1.8),
        ("ESP32 DEVKIT V1 (30-PIN)", 20.7, 37.0, 1.0),
        ("ANTENNA KEEPOUT", 20.7, 30.0, 0.9),
        ("OPEN USB ACCESS", 20.7, 80.0, 0.9),
        ("230V AC LIVE IN", 84.0, 8.0, 1.2),
        ("OUT1: LIGHT 1", 93.0, 29.0, 1.0),
        ("OUT2: LIGHT 2", 93.0, 57.0, 1.0),
        ("OUT3: LIGHT 3", 93.0, 85.0, 1.0),
        ("OUT4: FAN", 93.0, 113.0, 1.0),
        ("+5V IN", 35.0, 137.0, 1.1),
        ("GND", 43.0, 137.0, 1.1),
        ("CH1 (GPIO 23)", 66.0, 18.0, 0.9),
        ("CH2 (GPIO 22)", 66.0, 46.0, 0.9),
        ("CH3 (GPIO 19)", 66.0, 74.0, 0.9),
        ("CH4 (GPIO 18)", 66.0, 102.0, 0.9),
        ("Q1", 45.46, 23.89, 0.85),
        ("B", 45.46, 29.20, 0.80),
        ("C", 48.0, 21.60, 0.80),
        ("E", 42.92, 21.60, 0.80),

        ("Q2", 45.46, 51.89, 0.85),
        ("B", 45.46, 57.20, 0.80),
        ("C", 48.0, 49.60, 0.80),
        ("E", 42.92, 49.60, 0.80),

        ("Q3", 45.46, 79.89, 0.85),
        ("B", 45.46, 85.20, 0.80),
        ("C", 48.0, 77.60, 0.80),
        ("E", 42.92, 77.60, 0.80),

        ("Q4", 45.46, 107.89, 0.85),
        ("B", 45.46, 113.20, 0.80),
        ("C", 48.0, 105.60, 0.80),
        ("E", 42.92, 105.60, 0.80),

        ("R1", 41.65, 15.5, 0.80),
        ("R2", 41.65, 43.5, 0.80),
        ("R3", 41.65, 75.5, 0.80),
        ("R4", 41.65, 103.5, 0.80),

        ("D1", 61.0, 29.0, 0.80),
        ("D2", 61.0, 57.0, 0.80),
        ("D3", 61.0, 85.0, 0.80),
        ("D4", 61.0, 113.0, 0.80),

        ("J1: +5V MAIN", 41.0, 122.0, 0.9),
        ("J2: CH2 5V", 60.5, 48.0, 0.8),
        ("J3: CH3 5V", 60.5, 76.0, 0.8),
        ("J4: CH4 5V", 60.5, 104.0, 0.8),
        ("J5: GND LINK", 26.0, 76.0, 0.8),
        ("J6: PIR LINK", 15.0, 73.0, 0.8),
        ("MQ-2 GAS", 14.0, 18.0, 0.9),
        ("PIR SENSOR", 12.0, 95.0, 0.9),
        ("STATUS LED", 28.0, 88.0, 0.9),
        ("PWR LED", 20.0, 139.0, 0.8),
    ]
    for text, x, y, size in silkscreen_texts:
        txt = pcbnew.PCB_TEXT(board)
        txt.SetText(text)
        txt.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        txt.SetLayer(pcbnew.F_SilkS)
        txt.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(size), pcbnew.FromMM(size)))
        txt.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
        board.Add(txt)

    board.Save(filename)
    print(f"Board successfully built and saved to {filename}")
    return board

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else '/Users/shreyansh/@nirman/hardware/light_fan_pcb/light_fan.kicad_pcb'
    build_board(target)
