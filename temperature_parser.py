"""Shared parser for the inferred temperature logger record layout."""

import csv
import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, NamedTuple

MAGIC = b"\xDE\xC0\xBA\xB0"
PAYLOAD = struct.Struct("<IIHHIfI")
MIN_TS = int(datetime(2010, 1, 1, tzinfo=timezone.utc).timestamp())
MAX_TS = int(datetime(2100, 1, 1, tzinfo=timezone.utc).timestamp())


class Record(NamedTuple):
    time_utc_iso: str
    unix_ts: int
    sensor_id_u32: int
    u16_a: int
    u16_b: int
    raw_id_u32: int
    temp_c: float
    tail_u32: int


class NoMeasurementsError(ValueError):
    pass


def iter_records(data: bytes) -> Iterator[Record]:
    offset = 0
    while True:
        pos = data.find(MAGIC, offset)
        if pos < 0 or pos + len(MAGIC) + PAYLOAD.size > len(data):
            return
        # Continue searching after the marker, even for rejected candidates.
        offset = pos + len(MAGIC)
        sensor_id, ts, a, b, raw_id, temp_c, tail = PAYLOAD.unpack_from(data, offset)
        # The range check also rejects NaN and positive/negative infinity.
        if a == 8 and b == 4 and MIN_TS <= ts <= MAX_TS and -50.0 <= temp_c <= 150.0:
            yield Record(
                datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
                ts, sensor_id, a, b, raw_id, temp_c, tail,
            )


def read_records(path: str) -> list[Record]:
    with open(path, "rb") as source:
        records = list(iter_records(source.read()))
    if not records:
        raise NoMeasurementsError("Nie znaleziono rekordów pomiarowych (a==8, b==4).")
    records.sort(key=lambda record: record.unix_ts)
    return records


def ensure_distinct_output(inp: str, outp: str) -> None:
    """Protect the input, including aliases through symlinks and hard links."""
    source = Path(inp)
    target = Path(outp)
    if source.resolve() == target.resolve() or (
        target.exists() and source.samefile(target)
    ):
        raise ValueError(f"Plik wyjściowy wskazuje na plik wejściowy: {outp}")


def write_csv(path: str, records: list[Record]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as destination:
        writer = csv.writer(destination, delimiter=";")
        writer.writerow(Record._fields)
        writer.writerows(records)
