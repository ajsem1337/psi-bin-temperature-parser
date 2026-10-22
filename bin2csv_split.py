#!/usr/bin/env python3
"""Export accepted temperature measurements to one CSV file per sensor."""

import argparse
import sys
from collections import defaultdict

from temperature_parser import (
    NoMeasurementsError,
    ensure_distinct_output,
    read_records,
    write_csv,
)


def safe_name(sensor_id: int) -> str:
    return f"{sensor_id:08x}"


def main(inp: str, out_prefix: str) -> None:
    by_sensor = defaultdict(list)
    for record in read_records(inp):
        by_sensor[record.sensor_id_u32].append(record)

    outputs = [
        (sid, rows, f"{out_prefix}_sensor_{safe_name(sid)}.csv")
        for sid, rows in by_sensor.items()
    ]
    # Check every path before writing any file, so a later collision is safe too.
    for _, _, outp in outputs:
        ensure_distinct_output(inp, outp)
    for sid, rows, outp in outputs:
        write_csv(outp, rows)
        print(f"{sid} ({safe_name(sid)}): {len(rows)} rekordów -> {outp}")


def cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", metavar="DATA.BIN", help="wejściowy plik BIN")
    parser.add_argument("prefix", metavar="outprefix", help="prefiks plików CSV")
    args = parser.parse_args()
    try:
        main(args.input, args.prefix)
    except NoMeasurementsError as error:
        print(str(error), file=sys.stderr)
        return 2
    except (OSError, ValueError) as error:
        print(f"Błąd: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(cli())
