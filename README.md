# BIN temperature logger parser

Small Python script to extract temperature logs from proprietary `.BIN` files
produced by data loggers using `de c0 ba b0` record markers.

## Requirements

Python 3.9 or newer. Only the Python standard library is needed; no packages or
API keys are required. Keep both scripts alongside `temperature_parser.py`.

## Features

- Extracts UTC timestamps, sensor IDs and temperatures from binary logs.
- Filters candidates by type, timestamp and temperature range.
- Sorts measurements chronologically, retaining duplicate measurements.
- Exports UTF-8 CSV with a semicolon separator and a header row.
- Supports a single CSV or one CSV per sensor ID.
- Rejects output paths that would overwrite the input, including symbolic and
  hard links to the input file.

## Usage

```bash
python3 bin2csv.py DATA.BIN out.csv
python3 bin2csv_split.py DATA.BIN outprefix
```

The second command produces names such as `outprefix_sensor_0000002a.csv`.
The suffix is the sensor ID as eight lowercase hexadecimal digits; the ID in
the CSV is decimal. Use `--help` on either script for argument help. Quote paths
containing spaces. Output directories must already exist. Existing output CSVs
are overwritten.

Both commands use these columns:

```text
time_utc_iso;unix_ts;sensor_id_u32;u16_a;u16_b;raw_id_u32;temp_c;tail_u32
```

Timestamps use UTC with an explicit `+00:00` offset. Temperatures use a decimal
point; when importing into a spreadsheet, select `;` as the separator and a
locale that recognizes decimal points.

Exit codes: `0` for success, `1` for file/path errors, and `2` for no accepted
measurements or invalid command arguments. If no measurements pass the filters,
no output is written. File/path errors are reported to stderr without a traceback.
Split export can leave earlier CSVs in place if a later file cannot be written.

## Inferred record format and limitations

The layout is inferred from a hex dump, not a vendor specification. Each
candidate consists of the four-byte marker `de c0 ba b0` and a 24-byte payload.
All numeric fields are little-endian:

| Payload offset | Type | CSV field | Interpretation |
| --- | --- | --- | --- |
| 0 | uint32 | `sensor_id_u32` | Sensor ID |
| 4 | uint32 | `unix_ts` | Unix timestamp in seconds |
| 8 | uint16 | `u16_a` | Assumed type field; must equal 8 |
| 10 | uint16 | `u16_b` | Assumed format field; must equal 4 |
| 12 | uint32 | `raw_id_u32` | Unknown ID |
| 16 | float32 | `temp_c` | Assumed temperature in degrees Celsius |
| 20 | uint32 | `tail_u32` | Unknown trailing field; no checksum validation |

Accepted timestamps run from `2010-01-01T00:00:00+00:00` through
`2100-01-01T00:00:00+00:00`, inclusive. Accepted temperatures run from −50 to
150 °C, inclusive; NaN and infinity are rejected. These are fixed heuristic
filters, so legitimate readings outside these ranges will also be excluded.
Truncated final records and candidates that fail the filters are skipped.

The parser scans for markers, so coincidental byte sequences can produce false
positives. The unknown fields are exported without interpretation. Files and
accepted records are held in memory; very large logs may require substantial
RAM. No real BIN samples are included in this repository; tests use synthetic
records and cannot establish compatibility with every logger.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

## AI assistance

AI assistance was used for code review, fixes, regression tests and documentation.
The parser itself runs locally as ordinary Python code: it does not use an AI
model or send log data to an external service. AI assistance does not validate
the inferred binary format; check exported readings against known measurements
before relying on them.
