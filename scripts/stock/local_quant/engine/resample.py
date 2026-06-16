#!/usr/bin/env python3
"""Resample standard 5m bars to 30m bars for A-share sessions."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

if __package__ is None or __package__ == "":
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1]))

from utils.io import DEFAULT_STOCK_LOCAL_ROOT, read_partitioned_parquet, write_bars_parquet, write_meta_summary  # noqa: E402
from utils.schema import TARGET_30M_TIMES, meta_for_bars, order_bars_columns, validate_bars  # noqa: E402

BUCKET_BY_TIME = {
    # Morning session, 24 bars -> 4 buckets
    "09:35:00": "10:00:00",
    "09:40:00": "10:00:00",
    "09:45:00": "10:00:00",
    "09:50:00": "10:00:00",
    "09:55:00": "10:00:00",
    "10:00:00": "10:00:00",
    "10:05:00": "10:30:00",
    "10:10:00": "10:30:00",
    "10:15:00": "10:30:00",
    "10:20:00": "10:30:00",
    "10:25:00": "10:30:00",
    "10:30:00": "10:30:00",
    "10:35:00": "11:00:00",
    "10:40:00": "11:00:00",
    "10:45:00": "11:00:00",
    "10:50:00": "11:00:00",
    "10:55:00": "11:00:00",
    "11:00:00": "11:00:00",
    "11:05:00": "11:30:00",
    "11:10:00": "11:30:00",
    "11:15:00": "11:30:00",
    "11:20:00": "11:30:00",
    "11:25:00": "11:30:00",
    "11:30:00": "11:30:00",
    # Afternoon session, 24 bars -> 4 buckets
    "13:05:00": "13:30:00",
    "13:10:00": "13:30:00",
    "13:15:00": "13:30:00",
    "13:20:00": "13:30:00",
    "13:25:00": "13:30:00",
    "13:30:00": "13:30:00",
    "13:35:00": "14:00:00",
    "13:40:00": "14:00:00",
    "13:45:00": "14:00:00",
    "13:50:00": "14:00:00",
    "13:55:00": "14:00:00",
    "14:00:00": "14:00:00",
    "14:05:00": "14:30:00",
    "14:10:00": "14:30:00",
    "14:15:00": "14:30:00",
    "14:20:00": "14:30:00",
    "14:25:00": "14:30:00",
    "14:30:00": "14:30:00",
    "14:35:00": "15:00:00",
    "14:40:00": "15:00:00",
    "14:45:00": "15:00:00",
    "14:50:00": "15:00:00",
    "14:55:00": "15:00:00",
    "15:00:00": "15:00:00",
}


def resample_5m_to_30m(df5: pd.DataFrame, *, require_complete: bool = True) -> pd.DataFrame:
    """Aggregate standard 5m bars into standard 30m bars.

    TDX timestamps are interval end times. One full A-share day has 48 5m bars,
    aggregated into 8 30m bars ending at TARGET_30M_TIMES.
    """
    if df5.empty:
        return df5.copy()

    df = df5.copy()
    df["_dt"] = pd.to_datetime(df["datetime"])
    df["_time"] = df["_dt"].dt.strftime("%H:%M:%S")
    df["_bucket_time"] = df["_time"].map(BUCKET_BY_TIME)
    unknown = sorted(df.loc[df["_bucket_time"].isna(), "_time"].unique().tolist())
    if unknown:
        raise ValueError(f"Unexpected 5m time labels: {unknown[:20]}")

    df["_bucket_datetime"] = pd.to_datetime(df["date"] + " " + df["_bucket_time"])
    df = df.sort_values(["instrument", "_dt"])

    rows: list[dict] = []
    for (instrument, date, bucket_dt), g in df.groupby(["instrument", "date", "_bucket_datetime"], sort=True):
        g = g.sort_values("_dt")
        if require_complete and len(g) != 6:
            continue
        rows.append(
            {
                "datetime": bucket_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "date": date,
                "instrument": instrument,
                "freq": "30m",
                "open": float(g["open"].iloc[0]),
                "high": float(g["high"].max()),
                "low": float(g["low"].min()),
                "close": float(g["close"].iloc[-1]),
                "volume": int(g["volume"].sum()) if "volume" in g else None,
                "amount": float(g["amount"].sum()) if "amount" in g else None,
                "source": str(g["source"].iloc[0]),
                "adjust": str(g["adjust"].iloc[0]) if "adjust" in g else "unknown",
                "source_freq": "5m",
                "bars_merged": int(len(g)),
            }
        )

    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(["instrument", "datetime"]).reset_index(drop=True)
    return order_bars_columns(out)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Resample standard 5m Parquet bars to 30m")
    parser.add_argument("--input", type=Path, default=DEFAULT_STOCK_LOCAL_ROOT / "normalized" / "bars_5m")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_STOCK_LOCAL_ROOT)
    parser.add_argument("--symbols", help="Comma-separated instruments, e.g. 000001.SZ,600585.SH")
    parser.add_argument("--allow-incomplete", action="store_true", help="Keep incomplete 30m buckets")
    parser.add_argument("--meta-out", type=Path, default=DEFAULT_STOCK_LOCAL_ROOT / "meta" / "resample_5m_to_30m_summary.csv")
    return parser


def _filter_symbols(df: pd.DataFrame, symbols: str | None) -> pd.DataFrame:
    if not symbols:
        return df
    allowed = {s.strip().upper() for s in symbols.split(",") if s.strip()}
    return df[df["instrument"].str.upper().isin(allowed)].copy()


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    df5 = read_partitioned_parquet(args.input)
    df5 = _filter_symbols(df5, args.symbols)
    if df5.empty:
        raise ValueError("No 5m bars to resample after filtering")

    df30 = resample_5m_to_30m(df5, require_complete=not args.allow_incomplete)
    validation = validate_bars(df30)
    if not validation["valid"]:
        raise ValueError(f"30m validation failed: {validation}")

    meta_rows: list[dict] = []
    output_dir = args.output_root / "normalized" / "bars_30m"
    for instrument, g in df30.groupby("instrument", sort=True):
        output_path = write_bars_parquet(g.reset_index(drop=True), output_dir, instrument)
        meta_rows.append(meta_for_bars(g, raw_path=str(args.input), normalized_path=str(output_path)))
        print(f"[OK] {instrument} 5m->{output_path} rows={len(g)}")

    meta_path = write_meta_summary(meta_rows, args.meta_out)
    print(f"[META] {meta_path} rows={len(meta_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
