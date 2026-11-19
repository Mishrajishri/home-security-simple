import sys, math

def ccw(A, B, C):
    return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])

def intersect(p1, p2, p3, p4):
    if p1 == p3 or p1 == p4 or p2 == p3 or p2 == p4:
        return False
    return (ccw(p1, p3, p4) != ccw(p2, p3, p4)) and (ccw(p1, p2, p3) != ccw(p1, p2, p4))

def dist_point_to_segment(p, a, b):
    # vector ab
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    if dx == 0 and dy == 0:
        return math.hypot(p[0]-a[0], p[1]-a[1])
    t = ((p[0]-a[0])*dx + (p[1]-a[1])*dy) / (dx*dx + dy*dy)
    t = max(0.0, min(1.0, t))
    closest = (a[0] + t*dx, a[1] + t*dy)
    return math.hypot(p[0]-closest[0], p[1]-closest[1])

print("Topological verifier framework ready")
