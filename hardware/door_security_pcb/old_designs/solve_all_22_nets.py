import math

def ccw(A, B, C):
    return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])

def intersect(p1, p2, p3, p4):
    if p1 == p3 or p1 == p4 or p2 == p3 or p2 == p4:
        return False
    return (ccw(p1, p3, p4) != ccw(p2, p3, p4)) and (ccw(p1, p2, p3) != ccw(p1, p2, p4))

def check_netlist(tracks):
    segments = {}
    for name, path_list in tracks.items():
        segments[name] = []
        for pts in path_list:
            for i in range(len(pts)-1):
                segments[name].append((pts[i], pts[i+1]))

    crossings = []
    names = list(tracks.keys())
    for i in range(len(names)):
        for j in range(i+1, len(names)):
            n1, n2 = names[i], names[j]
            for s1 in segments[n1]:
                for s2 in segments[n2]:
                    if intersect(s1[0], s1[1], s2[0], s2[1]):
                        crossings.append((n1, s1, n2, s2))
    return crossings

print("Checker ready")
