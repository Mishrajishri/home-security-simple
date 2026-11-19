import os, sys
import math
import heapq
import pcbnew

class GridRouter:
    def __init__(self, width_mm=85.0, height_mm=95.0, res=0.25):
        self.res = res
        self.width_mm = width_mm
        self.height_mm = height_mm
        self.w = int(round(width_mm / res)) + 1
        self.h = int(round(height_mm / res)) + 1
        self.grid = {}

        # 2.0 mm margin from edges
        for gx in range(self.w):
            for gy in range(self.h):
                x = gx * res
                y = gy * res
                if x < 2.0 or x > width_mm - 2.0 or y < 2.0 or y > height_mm - 2.0:
                    self.grid[(gx, gy)] = "BORDER"

    def to_grid(self, x, y):
        return (int(round(x / self.res)), int(round(y / self.res)))

    def to_mm(self, gx, gy):
        return (round(gx * self.res, 3), round(gy * self.res, 3))

    def add_obstacle_circle(self, x, y, radius):
        r_grid = int(math.ceil(radius / self.res))
        cx, cy = self.to_grid(x, y)
        for dx in range(-r_grid, r_grid + 1):
            for dy in range(-r_grid, r_grid + 1):
                if dx*dx + dy*dy <= (radius / self.res)**2:
                    self.grid[(cx + dx, cy + dy)] = "OBSTACLE"

    def add_pad(self, x, y, net_name, pad_radius=0.925, clearance=0.40):
        total_r = pad_radius + clearance
        r_grid = int(math.ceil(total_r / self.res))
        cx, cy = self.to_grid(x, y)
        for dx in range(-r_grid, r_grid + 1):
            for dy in range(-r_grid, r_grid + 1):
                dist = math.hypot(dx * self.res, dy * self.res)
                pt = (cx + dx, cy + dy)
                if dist <= pad_radius:
                    self.grid[pt] = ("PAD", net_name, (round(x, 2), round(y, 2)))
                elif dist <= total_r:
                    # Clearance zone
                    self.grid[pt] = ("CLEARANCE", net_name, (round(x, 2), round(y, 2)))

    def route_net(self, net_name, start_pos, end_pos, track_width=0.85, clearance=0.40):
        start = self.to_grid(*start_pos)
        end = self.to_grid(*end_pos)

        def heuristic(a, b):
            # Octile distance
            dx = abs(a[0] - b[0])
            dy = abs(a[1] - b[1])
            return 1.0 * (dx + dy) + (1.414 - 2.0) * min(dx, dy)

        open_set = []
        heapq.heappush(open_set, (0, 0, start, [start]))
        visited = {start: 0}

        target_pad_pos = (round(end_pos[0], 2), round(end_pos[1], 2))
        start_pad_pos = (round(start_pos[0], 2), round(start_pos[1], 2))

        found_path = None
        while open_set:
            f, cost, current, path = heapq.heappop(open_set)

            if current == end:
                found_path = path
                break

            for dx, dy in [(1,0), (-1,0), (0,1), (0,-1), (1,1), (-1,1), (1,-1), (-1,-1)]:
                neighbor = (current[0] + dx, current[1] + dy)
                if neighbor[0] < 0 or neighbor[0] >= self.w or neighbor[1] < 0 or neighbor[1] >= self.h:
                    continue

                occ = self.grid.get(neighbor)
                if occ is not None:
                    if occ == "BORDER" or occ == "OBSTACLE":
                        continue
                    if isinstance(occ, tuple):
                        tag, occ_net, pad_p = occ
                        # We can traverse pads and clearance of our own net or endpoints
                        if occ_net != net_name:
                            continue
                    elif occ != net_name:
                        continue

                move_cost = 1.414 if (dx != 0 and dy != 0) else 1.0
                new_cost = cost + move_cost

                if neighbor not in visited or new_cost < visited[neighbor]:
                    visited[neighbor] = new_cost
                    priority = new_cost + heuristic(neighbor, end)
                    heapq.heappush(open_set, (priority, new_cost, neighbor, path + [neighbor]))

        if not found_path:
            print(f"FAILED TO ROUTE {net_name} from {start_pos} to {end_pos}")
            return None

        # Mark routed path in grid
        r_grid = int(math.ceil((track_width / 2.0 + clearance) / self.res))
        for pt in found_path:
            for dx in range(-r_grid, r_grid + 1):
                for dy in range(-r_grid, r_grid + 1):
                    if math.hypot(dx * self.res, dy * self.res) <= (track_width / 2.0 + clearance):
                        cell = (pt[0] + dx, pt[1] + dy)
                        # Don't overwrite endpoint pads
                        existing = self.grid.get(cell)
                        if existing != ("PAD", net_name, start_pad_pos) and existing != ("PAD", net_name, target_pad_pos):
                            self.grid[cell] = net_name

        # Simplify path into polyline corners
        points_mm = [self.to_mm(*pt) for pt in found_path]
        simplified = [points_mm[0]]
        for i in range(1, len(points_mm) - 1):
            p_prev = simplified[-1]
            p_curr = points_mm[i]
            p_next = points_mm[i+1]
            dx1, dy1 = p_curr[0] - p_prev[0], p_curr[1] - p_prev[1]
            dx2, dy2 = p_next[0] - p_curr[0], p_next[1] - p_curr[1]
            if abs(dx1 * dy2 - dy1 * dx2) > 1e-4:
                simplified.append(p_curr)
        simplified.append(points_mm[-1])
        return simplified

def build():
    board = pcbnew.BOARD()
    fp_dir = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
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
    router = GridRouter(W, H, res=0.25)
    hole_lib = os.path.join(fp_dir, "MountingHole.pretty")
    for i, (hx, hy) in enumerate([(5.0, 5.0), (80.0, 5.0), (5.0, 90.0), (80.0, 90.0)]):
        h = pcbnew.FootprintLoad(hole_lib, "MountingHole_3.2mm_M3")
        h.SetReference(f"H{i+1}")
        h.SetValue("M3_Hole")
        h.Reference().SetVisible(False)
        h.Value().SetVisible(False)
        h.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(hx), pcbnew.FromMM(hy)))
        board.Add(h)
        # 3.2mm hole + 3.0mm annular pad + 0.5mm clearance = radius 3.5mm
        router.add_obstacle_circle(hx, hy, radius=3.5)

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

    j_lcd = place_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x04_P2.54mm_Vertical",
                     "J_LCD", "I2C_LCD", 48.0, 11.0, rot=0, ref_pos=(48.0, 5.5))

    # Bottom Connectors at Y=78.0:
    j_leds = place_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x03_P2.54mm_Vertical",
                      "J_LEDS", "Status_LEDs", 11.0, 78.0, rot=90, ref_pos=(13.5, 71.5))

    j_buzzer = place_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x02_P2.54mm_Vertical",
                        "J_BUZZER", "Buzzer", 22.0, 78.0, rot=90, ref_pos=(23.0, 71.5))

    j_relay = place_fp("Connector_PinHeader_2.54mm.pretty", "PinHeader_1x03_P2.54mm_Vertical",
                       "J_RELAY", "Relay_Lock", 33.0, 78.0, rot=90, ref_pos=(35.5, 71.5))

    j_power = place_fp("TerminalBlock_Phoenix.pretty", "TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal",
                       "J_POWER", "5V_Power", 50.0, 78.0, rot=0, ref_pos=(52.5, 71.0))

    # Net Mapping
    def set_net(fp, pnum, net_name):
        pad = fp.FindPadByNumber(str(pnum))
        if pad and net_name in nets:
            pad.SetNet(nets[net_name])

    # Left ESP Header
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
    set_net(j_esp_r, 15, "+3.3V")

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

    def ppos(fp, pnum):
        p = fp.FindPadByNumber(str(pnum))
        pos = p.GetPosition()
        return (round(pos.x / 1e6, 3), round(pos.y / 1e6, 3))

    # Add all footprint pads to router
    for fp in [j_esp_l, j_esp_r, j_rfid, j_keypad, j_lcd, j_leds, j_buzzer, j_relay, j_power]:
        for pad in fp.Pads():
            pos = pad.GetPosition()
            x = round(pos.x / 1e6, 3)
            y = round(pos.y / 1e6, 3)
            net_name = pad.GetNetname()
            router.add_pad(x, y, net_name)

    def draw_track(net_name, points, width=0.85):
        net = nets.get(net_name)
        for i in range(len(points) - 1):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(points[i][0]), pcbnew.FromMM(points[i][1])))
            t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(points[i+1][0]), pcbnew.FromMM(points[i+1][1])))
            t.SetWidth(pcbnew.FromMM(width))
            t.SetLayer(pcbnew.B_Cu)
            if net: t.SetNet(net)
            board.Add(t)

    # Route All Connections using GridRouter:
    # 1. RFID SPI (straight horizontal)
    for p, net in [(5, "RFID_MISO"), (6, "RFID_MOSI"), (7, "RFID_SCK"), (8, "RFID_SDA_SS")]:
        pts = router.route_net(net, ppos(j_rfid, p), ppos(j_esp_l, p))
        draw_track(net, pts)

    # 2. Keypad (8 Monotonic lines)
    pts = router.route_net("KEYPAD_R1", ppos(j_esp_r, 1), ppos(j_keypad, 1))
    draw_track("KEYPAD_R1", pts)
    for ep, kp, net in [
        (6, 2, "KEYPAD_R2"), (7, 3, "KEYPAD_R3"), (8, 4, "KEYPAD_R4"),
        (9, 5, "KEYPAD_C1"), (10, 6, "KEYPAD_C2"), (12, 7, "KEYPAD_C3"), (13, 8, "KEYPAD_C4")
    ]:
        pts = router.route_net(net, ppos(j_esp_r, ep), ppos(j_keypad, kp))
        draw_track(net, pts)

    # 3. I2C LCD
    pts = router.route_net("I2C_SCL", ppos(j_lcd, 4), ppos(j_esp_r, 2))
    draw_track("I2C_SCL", pts)
    pts = router.route_net("I2C_SDA", ppos(j_lcd, 3), ppos(j_esp_r, 5))
    draw_track("I2C_SDA", pts)

    # 4. RFID_RST
    pts = router.route_net("RFID_RST", ppos(j_esp_l, 9), ppos(j_rfid, 2))
    draw_track("RFID_RST", pts)

    # 5. DOOR_RELAY
    pts = router.route_net("DOOR_RELAY", ppos(j_esp_r, 11), ppos(j_relay, 1))
    draw_track("DOOR_RELAY", pts)

    # 6. BUZZER
    pts = router.route_net("BUZZER", ppos(j_esp_l, 13), ppos(j_buzzer, 1))
    draw_track("BUZZER", pts)

    # 7. LEDs
    pts = router.route_net("LED_GREEN", ppos(j_esp_l, 11), ppos(j_leds, 1))
    draw_track("LED_GREEN", pts)
    pts = router.route_net("LED_RED", ppos(j_esp_l, 12), ppos(j_leds, 2))
    draw_track("LED_RED", pts)

    # 8. +3.3V
    pts = router.route_net("+3.3V", ppos(j_esp_r, 15), ppos(j_rfid, 1), track_width=1.0)
    draw_track("+3.3V", pts, width=1.0)

    # 9. +5V Distribution:
    # J_POWER Pad 2 to J_RELAY Pad 2
    pts = router.route_net("+5V", ppos(j_power, 2), ppos(j_relay, 2), track_width=1.1)
    draw_track("+5V", pts, width=1.1)
    # J_RELAY Pad 2 to ESP_L Pin 15
    pts = router.route_net("+5V", ppos(j_relay, 2), ppos(j_esp_l, 15), track_width=1.1)
    draw_track("+5V", pts, width=1.1)
    # J_POWER Pad 2 to J_LCD Pad 2
    pts = router.route_net("+5V", ppos(j_power, 2), ppos(j_lcd, 2), track_width=1.1)
    draw_track("+5V", pts, width=1.1)

    # 10. GND Distribution:
    # J_POWER Pad 1 to J_RELAY Pad 3
    pts = router.route_net("GND", ppos(j_power, 1), ppos(j_relay, 3), track_width=1.1)
    draw_track("GND", pts, width=1.1)
    # J_RELAY Pad 3 to J_BUZZER Pad 2
    pts = router.route_net("GND", ppos(j_relay, 3), ppos(j_buzzer, 2), track_width=1.1)
    draw_track("GND", pts, width=1.1)
    # J_BUZZER Pad 2 to J_LEDS Pad 3
    pts = router.route_net("GND", ppos(j_buzzer, 2), ppos(j_leds, 3), track_width=1.1)
    draw_track("GND", pts, width=1.1)
    # J_POWER Pad 1 to ESP_R Pin 14
    pts = router.route_net("GND", ppos(j_power, 1), ppos(j_esp_r, 14), track_width=1.1)
    draw_track("GND", pts, width=1.1)
    # J_RELAY Pad 3 to ESP_L Pin 14
    pts = router.route_net("GND", ppos(j_relay, 3), ppos(j_esp_l, 14), track_width=1.1)
    draw_track("GND", pts, width=1.1)
    # J_LEDS Pad 3 to J_RFID Pad 3
    pts = router.route_net("GND", ppos(j_leds, 3), ppos(j_rfid, 3), track_width=1.1)
    draw_track("GND", pts, width=1.1)
    # J_RFID Pad 3 to J_LCD Pad 1
    pts = router.route_net("GND", ppos(j_rfid, 3), ppos(j_lcd, 1), track_width=1.1)
    draw_track("GND", pts, width=1.1)

    # 11. Clean Silkscreen Text
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
    print("Autorouted Master Board generated successfully!")

if __name__ == "__main__":
    build()
