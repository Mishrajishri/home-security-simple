import heapq
import math

class GridRouter:
    def __init__(self, width_mm=85.0, height_mm=95.0, res=0.5):
        self.res = res
        self.w = int(round(width_mm / res)) + 1
        self.h = int(round(height_mm / res)) + 1
        self.grid = {} # (gx, gy) -> net_name or "OBSTACLE"
        
        # Margins (keep away from board edges by 2mm)
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

    def add_pad_obstacle(self, x, y, net_name, clearance=0.4, pad_radius=0.925):
        total_r = pad_radius + clearance
        r_grid = int(math.ceil(total_r / self.res))
        cx, cy = self.to_grid(x, y)
        for dx in range(-r_grid, r_grid + 1):
            for dy in range(-r_grid, r_grid + 1):
                dist = math.hypot(dx * self.res, dy * self.res)
                if dist <= total_r:
                    # Pad center belongs to net_name, buffer zone is obstacle
                    if dist <= pad_radius:
                        self.grid[(cx + dx, cy + dy)] = ("PAD", net_name, (x, y))
                    else:
                        self.grid[(cx + dx, cy + dy)] = ("CLEARANCE", net_name, (x, y))

    def route_net(self, net_name, start_pos, end_pos, track_width=0.85, clearance=0.4):
        # A* pathfinding from start_pos to end_pos
        start = self.to_grid(*start_pos)
        end = self.to_grid(*end_pos)

        def heuristic(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        open_set = []
        heapq.heappush(open_set, (0, 0, start, [start]))
        visited = {start: 0}

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

                # Check cell occupancy
                occ = self.grid.get(neighbor)
                if occ is not None:
                    if occ == "BORDER" or occ == "OBSTACLE":
                        continue
                    if isinstance(occ, tuple):
                        tag, occ_net, pos = occ
                        if occ_net != net_name:
                            continue
                    elif occ != net_name:
                        continue

                # Movement cost (diagonal = 1.414)
                move_cost = 1.414 if (dx != 0 and dy != 0) else 1.0
                new_cost = cost + move_cost

                if neighbor not in visited or new_cost < visited[neighbor]:
                    visited[neighbor] = new_cost
                    priority = new_cost + heuristic(neighbor, end)
                    heapq.heappush(open_set, (priority, new_cost, neighbor, path + [neighbor]))

        if not found_path:
            return None

        # Mark routed path in grid
        r_grid = int(math.ceil((track_width/2.0 + clearance) / self.res))
        for pt in found_path:
            for dx in range(-r_grid, r_grid + 1):
                for dy in range(-r_grid, r_grid + 1):
                    if math.hypot(dx * self.res, dy * self.res) <= (track_width/2.0 + clearance):
                        cell = (pt[0] + dx, pt[1] + dy)
                        if cell not in self.grid or self.grid[cell] != ("PAD", net_name, start_pos):
                            self.grid[cell] = net_name

        # Simplify path into polyline corners
        points_mm = [self.to_mm(*pt) for pt in found_path]
        simplified = [points_mm[0]]
        for i in range(1, len(points_mm) - 1):
            p_prev = simplified[-1]
            p_curr = points_mm[i]
            p_next = points_mm[i+1]
            # Check collinearity
            dx1, dy1 = p_curr[0] - p_prev[0], p_curr[1] - p_prev[1]
            dx2, dy2 = p_next[0] - p_curr[0], p_next[1] - p_curr[1]
            if abs(dx1 * dy2 - dy1 * dx2) > 1e-4:
                simplified.append(p_curr)
        simplified.append(points_mm[-1])
        return simplified

print("GridRouter class defined successfully!")
