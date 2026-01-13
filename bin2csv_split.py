#!/usr/bin/env python3
import struct
import csv
import sys
from collections import defaultdict
from datetime import datetime, timezone

MAGIC = b"\xDE\xC0\xBA\xB0"

MIN_TS = int(datetime(2010, 1, 1, tzinfo=timezone.utc).timestamp())
MAX_TS = int(datetime(2100, 1, 1, tzinfo=timezone.utc).timestamp())

def u32le(b): return struct.unpack("<I", b)[0]
def u16le(b): return struct.unpack("<H", b)[0]
def f32le(b): return struct.unpack("<f", b)[0]

def safe_name(x: int) -> str:
    return f"{x:08x}"  # hex fajniej wygląda w nazwie pliku

def main(inp: str, out_prefix: str) -> None:
    data = open(inp, "rb").read()
    by_sensor = defaultdict(list)

    i = 0
    while True:
        pos = data.find(MAGIC, i)
        if pos < 0:
            break

        if pos + 28 <= len(data):
            payload = data[pos+4:pos+28]
            sensor_id = u32le(payload[0:4])
            ts        = u32le(payload[4:8])
            a         = u16le(payload[8:10])
            b         = u16le(payload[10:12])
            raw_id    = u32le(payload[12:16])
            temp_c    = f32le(payload[16:20])
            tail      = u32le(payload[20:24])

            if (
                a == 8 and b == 4 and
                MIN_TS <= ts <= MAX_TS and
                -50.0 <= temp_c <= 150.0
            ):
                t_iso = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
                by_sensor[sensor_id].append((t_iso, ts, sensor_id, a, b, raw_id, temp_c, tail))

        i = pos + 4

    if not by_sensor:
        print("Nie znaleziono rekordów pomiarowych.", file=sys.stderr)
        sys.exit(2)

    for sid, rows in by_sensor.items():
        rows.sort(key=lambda r: r[1])
        outp = f"{out_prefix}_sensor_{safe_name(sid)}.csv"
        with open(outp, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter=';')
            w.writerow(["time_utc_iso","unix_ts","sensor_id_u32","u16_a","u16_b","raw_id_u32","temp_c","tail_u32"])
            w.writerows(rows)
        print(f"{sid} ({safe_name(sid)}): {len(rows)} rekordów -> {outp}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Użycie: {sys.argv[0]} DATA.BIN outprefix")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
