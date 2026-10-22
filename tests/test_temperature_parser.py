import csv
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

from temperature_parser import MAX_TS, MIN_TS, iter_records

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ("bin2csv.py", "bin2csv_split.py")
HEADER = [
    "time_utc_iso", "unix_ts", "sensor_id_u32", "u16_a", "u16_b",
    "raw_id_u32", "temp_c", "tail_u32",
]
TS = 1735689600  # 2025-01-01T00:00:00+00:00


def measurement(sensor=42, ts=TS, a=8, b=4, temp=21.5):
    return b"\xde\xc0\xba\xb0" + struct.pack(
        "<IIHHIfI", sensor, ts, a, b, 123, temp, 456,
    )


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as source:
        return list(csv.reader(source, delimiter=";"))


class ParserTests(unittest.TestCase):
    def test_valid_record_has_expected_fields_and_utc(self):
        records = list(iter_records(measurement()))
        self.assertEqual(records, [
            ("2025-01-01T00:00:00+00:00", TS, 42, 8, 4, 123, 21.5, 456),
        ])

    def test_filter_boundaries_are_inclusive(self):
        for ts in (MIN_TS, MAX_TS):
            for temp in (-50.0, 150.0):
                with self.subTest(ts=ts, temp=temp):
                    records = list(iter_records(measurement(ts=ts, temp=temp)))
                    self.assertEqual(len(records), 1)
                    self.assertEqual((records[0].unix_ts, records[0].temp_c), (ts, temp))

    def test_invalid_measurements_are_filtered(self):
        for fields in (
            {"ts": 0}, {"ts": 946684800}, {"ts": MIN_TS - 1}, {"ts": MAX_TS + 1},
            {"a": 7}, {"b": 3}, {"temp": -50.01}, {"temp": 150.01},
            {"temp": float("nan")}, {"temp": float("inf")}, {"temp": -float("inf")},
        ):
            with self.subTest(fields=fields):
                self.assertEqual(list(iter_records(measurement(**fields))), [])

    def test_noise_rejected_candidates_and_all_truncation_lengths(self):
        valid = measurement()
        for length in range(len(valid)):
            with self.subTest(length=length):
                data = b"header" + measurement(a=0) + b"noise" + valid + valid[:length]
                self.assertEqual(list(iter_records(data)), list(iter_records(valid)))

    def test_empty_or_unrecognized_input(self):
        for data in (b"", b"random data", b"\xde\xc0\xba"):
            with self.subTest(data=data):
                self.assertEqual(list(iter_records(data)), [])


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.source = self.directory / "input data.BIN"
        self.source.write_bytes(measurement())

    def run_script(self, script, *args):
        return subprocess.run(
            [sys.executable, str(ROOT / script), *map(str, args)],
            cwd=self.directory, capture_output=True, text=True, timeout=10,
        )

    def test_single_export_sorts_retains_duplicates_and_overwrites_csv(self):
        self.source.write_bytes(
            measurement(sensor=2, ts=TS + 10) + measurement() + measurement()
        )
        output = self.directory / "output data.csv"
        output.write_text("old CSV", encoding="utf-8")
        result = self.run_script("bin2csv.py", self.source, output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(read_csv(output), [
            HEADER,
            ["2025-01-01T00:00:00+00:00", str(TS), "42", "8", "4", "123", "21.5", "456"],
            ["2025-01-01T00:00:00+00:00", str(TS), "42", "8", "4", "123", "21.5", "456"],
            ["2025-01-01T00:00:10+00:00", str(TS + 10), "2", "8", "4", "123", "21.5", "456"],
        ])

    def test_split_exports_match_single_export(self):
        self.source.write_bytes(
            measurement(sensor=2, ts=TS + 20) + measurement(sensor=42, ts=TS + 10)
            + measurement(sensor=2) + measurement(sensor=42, ts=TS + 10)
        )
        combined = self.directory / "combined.csv"
        result = self.run_script("bin2csv.py", self.source, combined)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.run_script("bin2csv_split.py", self.source, self.directory / "out")
        self.assertEqual(result.returncode, 0, result.stderr)
        all_rows = read_csv(combined)
        for sensor in (2, 42):
            expected = [HEADER] + [row for row in all_rows[1:] if row[2] == str(sensor)]
            self.assertEqual(
                read_csv(self.directory / f"out_sensor_{sensor:08x}.csv"), expected,
            )
        self.assertEqual(len(list(self.directory.glob("out_sensor_*.csv"))), 2)

    def test_no_measurements_preserves_existing_output(self):
        for data in (b"", b"junk", measurement(a=0), measurement()[:-1]):
            self.source.write_bytes(data)
            for script in SCRIPTS:
                with self.subTest(script=script, data=data):
                    prefix = self.directory / "out"
                    output = prefix if script == "bin2csv.py" else self.directory / "out_sensor_0000002a.csv"
                    output.write_bytes(b"existing CSV")
                    result = self.run_script(script, self.source, prefix)
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertTrue(result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertEqual(output.read_bytes(), b"existing CSV")

    def test_missing_input_reports_error_without_creating_outputs(self):
        for script in SCRIPTS:
            with self.subTest(script=script):
                result = self.run_script(
                    script, self.directory / "missing.BIN", self.directory / "out",
                )
                self.assertEqual(result.returncode, 1)
                self.assertTrue(result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual(list(self.directory.glob("out*")), [])

    def test_unwritable_output_path_reports_error(self):
        for script in SCRIPTS:
            with self.subTest(script=script):
                result = self.run_script(script, self.source, self.directory / "missing" / "out")
                self.assertEqual(result.returncode, 1)
                self.assertTrue(result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_single_export_cannot_overwrite_input_or_its_aliases(self):
        original = self.source.read_bytes()
        symlink = self.directory / "symbolic.csv"
        symlink.symlink_to(self.source)
        hardlink = self.directory / "hard.csv"
        os.link(self.source, hardlink)
        for output in (self.source, symlink, hardlink):
            with self.subTest(output=output):
                result = self.run_script("bin2csv.py", self.source, output)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual(self.source.read_bytes(), original)

    def test_split_collision_is_detected_before_any_output_is_written(self):
        prefix = self.directory / "out"
        source = self.directory / "out_sensor_00000002.csv"
        original = measurement(sensor=1) + measurement(sensor=2, ts=TS + 10)
        source.write_bytes(original)
        result = self.run_script("bin2csv_split.py", source, prefix)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(source.read_bytes(), original)
        self.assertFalse((self.directory / "out_sensor_00000001.csv").exists())

    def test_split_cannot_overwrite_input_through_aliases(self):
        original = self.source.read_bytes()
        for kind in ("symbolic", "hard"):
            with self.subTest(kind=kind):
                prefix = self.directory / kind
                output = self.directory / f"{kind}_sensor_0000002a.csv"
                if kind == "symbolic":
                    output.symlink_to(self.source)
                else:
                    os.link(self.source, output)
                result = self.run_script("bin2csv_split.py", self.source, prefix)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(self.source.read_bytes(), original)

    def test_help_and_usage(self):
        for script in SCRIPTS:
            with self.subTest(script=script):
                result = self.run_script(script, "--help")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("usage:", result.stdout)
                result = self.run_script(script)
                self.assertEqual(result.returncode, 2)
                self.assertIn("usage:", result.stderr)


if __name__ == "__main__":
    unittest.main()
