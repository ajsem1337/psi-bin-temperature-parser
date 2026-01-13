#!/usr/bin/env python3
import struct
import csv
import sys
from datetime import datetime, timezone

MAGIC = b"\xDE\xC0\xBA\xB0"  # de c0 ba b0

# Odcinamy śmieci typu 1970/2000 itp.
MIN_TS = int(datetime(2010, 1, 1, tzinfo=timezone.utc).timestamp())
MAX_TS = int(datetime(2100, 1, 1, tzinfo=timezone.utc).timestamp())

def u32le(b: bytes) -> int:
    return struct.unpack("<I", b)[0]

def u16le(b: bytes) -> int:
    return struct.unpack("<H", b)[0]

def f32le(b: bytes) -> float:
    return struct.unpack("<f", b)[0]

def main(inp: str, outp: str) -> None:
    data = open(inp, "rb").read()
    rows = []
    i = 0

    while True:
        pos = data.find(MAGIC, i)
        if pos < 0:
            break

        # Rekord: 4 magic + 24 payload (na podstawie twojego hexdumpa)
        if pos + 28 <= len(data):
            payload = data[pos+4:pos+28]

            sensor_id = u32le(payload[0:4])
            ts        = u32le(payload[4:8])          # unix epoch seconds
            a         = u16le(payload[8:10])         # wygląda na typ/format
            b         = u16le(payload[10:12])        # wygląda na typ/format
            raw_id    = u32le(payload[12:16])        # jakieś ID/losowe
            temp_c    = f32le(payload[16:20])        # temperatura (float32 LE)
            tail      = u32le(payload[20:24])        # checksum/flag?

            # Filtr: bierzemy tylko rekordy pomiarowe
            if (
                a == 8 and
                b == 4 and
                MIN_TS <= ts <= MAX_TS and
                -50.0 <= temp_c <= 150.0
            ):
                t_iso = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
                rows.append((t_iso, ts, sensor_id, a, b, raw_id, temp_c, tail))

        i = pos + 4

    if not rows:
        print("Nie znaleziono rekordów pomiarowych (a==8, b==4).", file=sys.stderr)
        sys.exit(2)

    # sort po czasie
    rows.sort(key=lambda r: r[1])

    with open(outp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(["time_utc_iso", "unix_ts", "sensor_id_u32", "u16_a", "u16_b", "raw_id_u32", "temp_c", "tail_u32"])
        w.writerows(rows)

    print(f"OK: {len(rows)} rekordów -> {outp}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Użycie: {sys.argv[0]} DATA.BIN out.csv")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])