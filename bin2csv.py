#!/usr/bin/env python3
"""Export accepted temperature measurements to a single CSV file."""

import argparse
import sys

from temperature_parser import (
    NoMeasurementsError,
    ensure_distinct_output,
    read_records,
    write_csv,
)


def main(inp: str, outp: str) -> None:
    ensure_distinct_output(inp, outp)
    rows = read_records(inp)
    write_csv(outp, rows)
    print(f"OK: {len(rows)} rekordów -> {outp}")


def cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", metavar="DATA.BIN", help="wejściowy plik BIN")
    parser.add_argument("output", metavar="out.csv", help="wyjściowy plik CSV")
    args = parser.parse_args()
    try:
        main(args.input, args.output)
    except NoMeasurementsError as error:
        print(str(error), file=sys.stderr)
        return 2
    except (OSError, ValueError) as error:
        print(f"Błąd: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(cli())
