#!/usr/bin/env python3
"""Convert Tongdaxin .day/.lc5 files to local_quant standard Parquet bars.

This adapter is intentionally source-only: it parses raw TDX files and writes
standard bars. Strategy logic must live elsewhere.
"""

from __future__ import annotations

import argparse
import datetime as dt
import struct
from pathlib import Path
from typing import Iterable

import pandas as pd

# Allow running as a script from this directory or repo root.
if __package__ is None or __package__ == "":
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1]))

from utils.io import (  # noqa: E402
    DEFAULT_STOCK_LOCAL_ROOT,
    normalize_symbol_filter,
    parse_instrument_from_filename,
    symbol_allowed,
    write_bars_parquet,
    write_meta_summary,
    write_sample_csv,
)
from utils.schema import meta_for_bars, order_bars_columns, validate_bars  # noqa: E402

DAY_STRUCT = struct.Struct("<IIIIIfII")
LC5_STRUCT = struct.Struct("<HHfffffII")


def decode_lc_date(date_code: int) -> dt.date:
    """Decode TDX minute-line compressed date."""
    year = date_code // 2048 + 2004
    rem = date_code % 2048
    month = rem // 100
    day = rem % 100
    return dt.date(year, month, day)


def decode_lc_time(time_code: int) -> dt.time:
    """Decode TDX minute-line time code as HH:MM."""
    hour = time_code // 60
    minute = time_code % 60
    return dt.time(hour, minute)


def _check_record_size(path: Path, record_size: int = 32) -> None:
    size = path.stat().st_size
    if size % record_size != 0:
        raise ValueError(f"{path} size {size} is not divisible by {record_size}")


def parse_day_file(path: str | Path) -> pd.DataFrame:
    """Parse a TDX .day file into standard 1d bars."""
    path = Path(path)
    instrument = parse_instrument_from_filename(path)
    if not instrument:
        raise ValueError(f"Cannot parse instrument from filename: {path.name}")
    _check_record_size(path, DAY_STRUCT.size)

    rows: list[dict] = []
    data = path.read_bytes()
    for offset in range(0, len(data), DAY_STRUCT.size):
        raw_date, open_raw, high_raw, low_raw, close_raw, amount, volume, reserved = DAY_STRUCT.unpack_from(data, offset)
        text = str(raw_date)
        if len(text) != 8:
            raise ValueError(f"Invalid day date {raw_date} in {path} at offset {offset}")
        date = dt.date(int(text[:4]), int(text[4:6]), int(text[6:8]))
        rows.append(
            {
                "datetime": f"{date.isoformat()} 15:00:00",
                "date": date.isoformat(),
                "instrument": instrument,
                "freq": "1d",
                "open": open_raw / 100.0,
                "high": high_raw / 100.0,
                "low": low_raw / 100.0,
                "close": close_raw / 100.0,
                "volume": int(volume),
                "amount": float(amount),
                "source": "tdx",
                "adjust": "unknown",
                "tdx_reserved": int(reserved),
            }
        )

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(["instrument", "datetime"]).reset_index(drop=True)
    return order_bars_columns(df)


def parse_lc5_file(path: str | Path) -> pd.DataFrame:
    """Parse a TDX .lc5 file into standard 5m bars.

    TDX minute timestamps are interval end times: 09:35, ..., 15:00.
    """
    path = Path(path)
    instrument = parse_instrument_from_filename(path)
    if not instrument:
        raise ValueError(f"Cannot parse instrument from filename: {path.name}")
    _check_record_size(path, LC5_STRUCT.size)

    rows: list[dict] = []
    data = path.read_bytes()
    for offset in range(0, len(data), LC5_STRUCT.size):
        date_code, time_code, open_, high, low, close, amount, volume, reserved = LC5_STRUCT.unpack_from(data, offset)
        date = decode_lc_date(date_code)
        time = decode_lc_time(time_code)
        rows.append(
            {
                "datetime": f"{date.isoformat()} {time.isoformat()}",
                "date": date.isoformat(),
                "instrument": instrument,
                "freq": "5m",
                "open": float(open_),
                "high": float(high),
                "low": float(low),
                "close": float(close),
                "volume": int(volume),
                "amount": float(amount),
                "source": "tdx",
                "adjust": "unknown",
                "tdx_reserved": int(reserved),
                "tdx_date_code": int(date_code),
                "tdx_time_code": int(time_code),
            }
        )

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(["instrument", "datetime"]).reset_index(drop=True)
    return order_bars_columns(df)


def discover_files(input_dir: Path, freq: str, allowed: set[str] | None, limit_files: int | None = None) -> list[Path]:
    """Find TDX files matching requested frequency."""
    suffixes = []
    if freq in {"day", "all"}:
        suffixes.append("*.day")
    if freq in {"lc5", "all"}:
        suffixes.append("*.lc5")

    files: list[Path] = []
    for suffix in suffixes:
        files.extend(sorted(input_dir.glob(suffix)))
    files = [p for p in files if symbol_allowed(p, allowed)]
    if limit_files is not None:
        files = files[:limit_files]
    return files


def convert_files(
    files: Iterable[Path],
    output_root: Path,
    sample_csv: Path | None = None,
    sample_rows: int = 100,
) -> list[dict]:
    """Convert files and return metadata rows."""
    meta_rows: list[dict] = []
    for file_path in files:
        if file_path.suffix == ".day":
            df = parse_day_file(file_path)
            output_dir = output_root / "normalized" / "bars_1d"
        elif file_path.suffix == ".lc5":
            df = parse_lc5_file(file_path)
            output_dir = output_root / "normalized" / "bars_5m"
        else:
            continue

        validation = validate_bars(df)
        if not validation["valid"]:
            raise ValueError(f"Validation failed for {file_path}: {validation}")

        instrument = df["instrument"].iloc[0] if not df.empty else parse_instrument_from_filename(file_path)
        output_path = write_bars_parquet(df, output_dir, instrument)
        if sample_csv:
            sample_name = f"{file_path.stem}_{df['freq'].iloc[0]}.csv" if not df.empty else f"{file_path.stem}.csv"
            write_sample_csv(df, sample_csv / sample_name, sample_rows)

        meta_rows.append(meta_for_bars(df, raw_path=str(file_path), normalized_path=str(output_path)))
        print(f"[OK] {file_path.name} -> {output_path} rows={len(df)}")
    return meta_rows


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert TDX .day/.lc5 files to standard Parquet bars")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_STOCK_LOCAL_ROOT / "raw" / "sample")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_STOCK_LOCAL_ROOT)
    parser.add_argument("--freq", choices=["day", "lc5", "all"], default="all")
    parser.add_argument("--symbols", help="Comma-separated symbols, e.g. sh000001,sz000001,000001.SZ")
    parser.add_argument("--sample-csv", type=Path, help="Optional directory for small CSV samples")
    parser.add_argument("--sample-rows", type=int, default=100)
    parser.add_argument("--limit-files", type=int, help="Limit number of files for smoke tests")
    parser.add_argument("--meta-out", type=Path, default=DEFAULT_STOCK_LOCAL_ROOT / "meta" / "tdx_convert_summary.csv")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    allowed = normalize_symbol_filter(args.symbols)
    files = discover_files(args.input_dir, args.freq, allowed, args.limit_files)
    if not files:
        raise FileNotFoundError(f"No TDX files found in {args.input_dir} for freq={args.freq}")

    meta_rows = convert_files(files, args.output_root, args.sample_csv, args.sample_rows)
    meta_path = write_meta_summary(meta_rows, args.meta_out)
    print(f"[META] {meta_path} rows={len(meta_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
