def ccw(A, B, C):
    return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])

def intersect(p1, p2, p3, p4):
    if p1 == p3 or p1 == p4 or p2 == p3 or p2 == p4:
        return False
    return (ccw(p1, p3, p4) != ccw(p2, p3, p4)) and (ccw(p1, p2, p3) != ccw(p1, p2, p4))

tracks = {
    "RFID_MISO": [(10.0, 36.16), (30.0, 36.16)],
    "RFID_MOSI": [(10.0, 38.70), (30.0, 38.70)],
    "RFID_SCK":  [(10.0, 41.24), (30.0, 41.24)],
    "RFID_SDA_SS": [(10.0, 43.78), (30.0, 43.78)],
    "+3.3V": [(30.0, 26.0), (30.0, 21.0), (10.0, 21.0), (10.0, 26.0)],
    "RFID_RST": [(30.0, 46.32), (34.0, 46.32), (34.0, 23.5), (13.5, 23.5), (13.5, 28.54), (10.0, 28.54)],
    "KEYPAD_R1": [(55.4, 26.0), (75.0, 26.0)],
    "KEYPAD_R2": [(55.4, 38.70), (58.0, 38.70), (58.0, 28.54), (75.0, 28.54)],
    "KEYPAD_R3": [(55.4, 41.24), (60.5, 41.24), (60.5, 31.08), (75.0, 31.08)],
    "KEYPAD_R4": [(55.4, 43.78), (63.0, 43.78), (63.0, 33.62), (75.0, 33.62)],
    "KEYPAD_C1": [(55.4, 46.32), (65.5, 46.32), (65.5, 36.16), (75.0, 36.16)],
    "KEYPAD_C2": [(55.4, 48.86), (68.0, 48.86), (68.0, 38.70), (75.0, 38.70)],
    "KEYPAD_C3": [(55.4, 53.94), (70.5, 53.94), (70.5, 41.24), (75.0, 41.24)],
    "KEYPAD_C4": [(55.4, 56.48), (73.0, 56.48), (73.0, 43.78), (75.0, 43.78)],
    "I2C_SCL": [(48.0, 18.62), (48.0, 28.54), (55.4, 28.54)],
    "I2C_SDA": [(48.0, 16.08), (45.5, 16.08), (45.5, 36.16), (55.4, 36.16)],
    "LED_GREEN": [(30.0, 51.40), (11.0, 51.40), (11.0, 78.0)],
    "LED_RED":   [(30.0, 53.94), (13.54, 53.94), (13.54, 78.0)],
    "BUZZER":    [(30.0, 56.48), (21.0, 56.48), (21.0, 78.0)],
}

# Convert each track to segments:
segments = {}
for name, pts in tracks.items():
    segments[name] = [(pts[i], pts[i+1]) for i in range(len(pts)-1)]

crossings = 0
names = list(tracks.keys())
for i in range(len(names)):
    for j in range(i+1, len(names)):
        n1, n2 = names[i], names[j]
        for s1 in segments[n1]:
            for s2 in segments[n2]:
                if intersect(s1[0], s1[1], s2[0], s2[1]):
                    print(f"CROSSING between {n1} ({s1}) and {n2} ({s2})")
                    crossings += 1

print(f"Total crossings among 19 fixed tracks: {crossings}")
