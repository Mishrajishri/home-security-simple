import sys, math

def ccw(A, B, C):
    return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])

def intersect(p1, p2, p3, p4):
    if p1 == p3 or p1 == p4 or p2 == p3 or p2 == p4:
        return False
    # Collinear check
    return (ccw(p1, p3, p4) != ccw(p2, p3, p4)) and (ccw(p1, p2, p3) != ccw(p1, p2, p4))

def segments_intersect(segs1, segs2):
    for s1 in segs1:
        for s2 in segs2:
            if intersect(s1[0], s1[1], s2[0], s2[1]):
                return True, s1, s2
    return False, None, None

print("Solver script template")
