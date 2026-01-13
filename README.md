# BIN temperature logger parser

Small Python script to extract temperature logs from proprietary `.BIN` files
produced by data loggers using `de c0 ba b0` record markers.

## Features
- parses binary `.BIN` log files
- extracts timestamp + temperature
- filters invalid records (1970/2000 epoch junk)
- exports to CSV (Excel/LibreOffice friendly)
- optional split per sensor ID

## Usage
```bash
python3 bin2csv.py DATA.BIN out.csv
python3 bin2csv_split.py DATA.BIN outprefix
