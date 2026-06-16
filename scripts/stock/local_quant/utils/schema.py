"""Schema helpers for local_quant standard bars."""

from __future__ import annotations

from typing import Any

import pandas as pd

BARS_FIELDS_REQUIRED = [
    "datetime",
    "date",
    "instrument",
    "freq",
    "open",
    "high",
    "low",
    "close",
    "source",
]

BARS_FIELDS_OPTIONAL = [
    "volume",
    "amount",
    "adjust",
]

BARS_FIELDS_ALL = BARS_FIELDS_REQUIRED + BARS_FIELDS_OPTIONAL

FREQ_MAP = {
    "day": "1d",
    "lc5": "5m",
    "1d": "1d",
    "5m": "5m",
    "30m": "30m",
}

TARGET_30M_TIMES = [
    "10:00:00",
    "10:30:00",
    "11:00:00",
    "11:30:00",
    "13:30:00",
    "14:00:00",
    "14:30:00",
    "15:00:00",
]

STANDARD_5M_TIMES = [
    *[f"{h:02d}:{m:02d}:00" for h, minutes in [(9, range(35, 60, 5)), (10, range(0, 60, 5)), (11, range(0, 31, 5))] for m in minutes],
    *[f"{h:02d}:{m:02d}:00" for h, minutes in [(13, range(5, 60, 5)), (14, range(0, 60, 5)), (15, [0])] for m in minutes],
]


def order_bars_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return DataFrame with standard fields first."""
    cols = [c for c in BARS_FIELDS_ALL if c in df.columns]
    cols += [c for c in df.columns if c not in cols]
    return df[cols]


def validate_bars(df: pd.DataFrame) -> dict[str, Any]:
    """Validate standard bars DataFrame."""
    result: dict[str, Any] = {
        "valid": True,
        "missing_fields": [],
        "duplicate_keys": 0,
        "ohlc_issues": 0,
        "null_required": 0,
        "warnings": [],
    }

    for field in BARS_FIELDS_REQUIRED:
        if field not in df.columns:
            result["missing_fields"].append(field)
            result["valid"] = False

    if result["missing_fields"]:
        return result

    null_required = int(df[BARS_FIELDS_REQUIRED].isna().sum().sum())
    result["null_required"] = null_required
    if null_required:
        result["valid"] = False
        result["warnings"].append(f"Found {null_required} null values in required fields")

    duplicate_keys = int(df.duplicated(subset=["instrument", "freq", "datetime"], keep=False).sum())
    result["duplicate_keys"] = duplicate_keys
    if duplicate_keys:
        result["valid"] = False
        result["warnings"].append(f"Found {duplicate_keys} duplicate instrument/freq/datetime keys")

    ohlc_issues = int(((df["high"] < df["low"]) | (df["open"] < 0) | (df["close"] < 0)).sum())
    result["ohlc_issues"] = ohlc_issues
    if ohlc_issues:
        result["valid"] = False
        result["warnings"].append(f"Found {ohlc_issues} OHLC issues")

    return result


def meta_for_bars(df: pd.DataFrame, *, raw_path: str, normalized_path: str, warnings: list[str] | None = None) -> dict[str, Any]:
    """Build one metadata row for a bars DataFrame."""
    if df.empty:
        return {
            "source": "tdx",
            "freq": None,
            "instrument": None,
            "rows": 0,
            "start_datetime": None,
            "end_datetime": None,
            "adjust": None,
            "raw_path": raw_path,
            "normalized_path": normalized_path,
            "warnings": ";".join(warnings or ["empty dataframe"]),
        }

    validation = validate_bars(df)
    all_warnings = list(warnings or []) + validation.get("warnings", [])
    return {
        "source": df["source"].iloc[0],
        "freq": df["freq"].iloc[0],
        "instrument": df["instrument"].iloc[0],
        "rows": int(len(df)),
        "start_datetime": str(df["datetime"].min()),
        "end_datetime": str(df["datetime"].max()),
        "adjust": df["adjust"].iloc[0] if "adjust" in df.columns else None,
        "raw_path": raw_path,
        "normalized_path": normalized_path,
        "valid": validation["valid"],
        "duplicate_keys": validation["duplicate_keys"],
        "ohlc_issues": validation["ohlc_issues"],
        "warnings": ";".join(all_warnings),
    }
