#!/usr/bin/env python3
"""Parse Tongdaxin hq_cache metadata into local_quant meta tables.

This adapter extracts reusable dimension tables from TDX hq_cache.zip or an
extracted hq_cache directory. It does not modify raw data.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import struct
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable

import pandas as pd

if __package__ is None or __package__ == "":
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1]))

from utils.io import DEFAULT_STOCK_LOCAL_ROOT, ensure_dir  # noqa: E402

TNF_HEADER_SIZE = 50
TNF_RECORD_SIZE = 360


def decode_zstr(raw: bytes, encoding: str = "gb18030") -> str:
    """Decode null-terminated fixed-width string."""
    return raw.split(b"\x00", 1)[0].decode(encoding, errors="ignore").strip()


def market_flag_to_suffix(flag: str) -> str | None:
    """TDX market flag used by cfg/txt files to suffix."""
    flag = str(flag).strip()
    if flag == "0":
        return "SZ"
    if flag == "1":
        return "SH"
    if flag in {"2", "BJ"}:
        return "BJ"
    return None


def make_instrument(code: str, market: str) -> str:
    return f"{code}.{market}"


def guess_security_type(code: str, market: str, name: str = "") -> str:
    """Rough security type guess by market/code segment/name.

    This is deliberately conservative; downstream filters should refine it.
    """
    code = code.strip()
    name = name.strip()
    if market == "SH" and code.startswith("6"):
        return "stock"
    if market == "SZ" and code.startswith(("000", "001", "002", "003", "300", "301")):
        return "stock"
    if market == "BJ" and code.startswith(("8", "4", "9")) and not code.startswith("899"):
        return "stock_or_bond"
    if (market == "SH" and code.startswith("0")) or (market == "SZ" and code.startswith("399")) or code.startswith("899"):
        return "index"
    if code.startswith(("15", "16", "50", "51", "56", "58")) or any(x in name.upper() for x in ["ETF", "LOF", "REIT"]):
        return "fund_or_etf"
    if code.startswith(("10", "11", "12", "13", "18")) or "转债" in name or "债" in name:
        return "bond_or_convertible"
    if "期权" in name or "购" in name or "沽" in name:
        return "option"
    return "other"


def resolve_hq_cache_path(input_path: Path) -> tuple[Path, tempfile.TemporaryDirectory | None]:
    """Return extracted hq_cache directory and optional tempdir handle."""
    input_path = input_path.resolve()
    if input_path.is_dir():
        if input_path.name == "hq_cache":
            return input_path, None
        candidate = input_path / "hq_cache"
        if candidate.is_dir():
            return candidate, None
        return input_path, None

    if input_path.suffix.lower() != ".zip":
        raise ValueError(f"Unsupported input path: {input_path}")

    tempdir = tempfile.TemporaryDirectory(prefix="tdx_hq_cache_")
    out = Path(tempdir.name)
    with zipfile.ZipFile(input_path) as zf:
        zf.extractall(out)
    hq_dir = out / "hq_cache"
    if not hq_dir.is_dir():
        raise FileNotFoundError("hq_cache directory not found inside zip")
    return hq_dir, tempdir


def parse_tnf_file(path: Path, market: str, updated_at: str) -> pd.DataFrame:
    """Parse TDX .tnf security list."""
    data = path.read_bytes()
    rows: list[dict] = []
    for offset in range(TNF_HEADER_SIZE, len(data) - TNF_RECORD_SIZE + 1, TNF_RECORD_SIZE):
        record = data[offset : offset + TNF_RECORD_SIZE]
        code = decode_zstr(record[0:31])
        name = decode_zstr(record[31:80])
        if not (len(code) == 6 and code.isdigit() and name):
            continue
        rows.append(
            {
                "instrument": make_instrument(code, market),
                "code": code,
                "tdx_symbol": ("sh" if market == "SH" else "sz" if market == "SZ" else "bj") + code,
                "market": market,
                "name": name,
                "type_guess": guess_security_type(code, market, name),
                "source_file": path.name,
                "updated_at": updated_at,
            }
        )
    return pd.DataFrame(rows)


def parse_all_tnf(hq_dir: Path, updated_at: str) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    mapping = {"shs.tnf": "SH", "szs.tnf": "SZ", "bjs.tnf": "BJ"}
    for filename, market in mapping.items():
        path = hq_dir / filename
        if path.exists():
            parts.append(parse_tnf_file(path, market, updated_at))
    if not parts:
        return pd.DataFrame(columns=["instrument", "code", "market", "name", "type_guess", "source_file", "updated_at"])
    df = pd.concat(parts, ignore_index=True)
    return df.drop_duplicates(subset=["instrument", "name", "source_file"]).sort_values(["market", "code", "name"]).reset_index(drop=True)


def parse_tdxhy(path: Path, updated_at: str) -> pd.DataFrame:
    """Parse tdxhy.cfg industry map.

    Format observed: market_flag|code|tdx_industry_code|||tdx_industry_ext_code
    """
    rows: list[dict] = []
    if not path.exists():
        return pd.DataFrame()
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        parts = line.split("|")
        if len(parts) < 3:
            continue
        market = market_flag_to_suffix(parts[0])
        code = parts[1].strip()
        if not market or not (len(code) == 6 and code.isdigit()):
            continue
        rows.append(
            {
                "instrument": make_instrument(code, market),
                "code": code,
                "tdx_symbol": ("sh" if market == "SH" else "sz" if market == "SZ" else "bj") + code,
                "market": market,
                "tdx_industry_code": parts[2].strip(),
                "tdx_industry_ext_code": parts[5].strip() if len(parts) > 5 else "",
                "source_file": path.name,
                "updated_at": updated_at,
            }
        )
    return pd.DataFrame(rows).drop_duplicates(subset=["instrument"]).sort_values(["market", "code"]).reset_index(drop=True)


def parse_specgpext(path: Path, updated_at: str) -> pd.DataFrame:
    """Parse specgpext.txt business profile lines."""
    rows: list[dict] = []
    if not path.exists():
        return pd.DataFrame()
    for line in path.read_text(encoding="gb18030", errors="ignore").splitlines():
        if not line.strip():
            continue
        parts = line.split("|")
        if len(parts) < 3:
            continue
        market = market_flag_to_suffix(parts[0])
        code = parts[1].strip()
        if not market or not (len(code) == 6 and code.isdigit()):
            continue
        rows.append(
            {
                "instrument": make_instrument(code, market),
                "code": code,
                "tdx_symbol": ("sh" if market == "SH" else "sz" if market == "SZ" else "bj") + code,
                "market": market,
                "business_desc": parts[2].strip(),
                "field3": parts[3].strip() if len(parts) > 3 else "",
                "field4": parts[4].strip() if len(parts) > 4 else "",
                "raw_line": line,
                "source_file": path.name,
                "updated_at": updated_at,
            }
        )
    return pd.DataFrame(rows).drop_duplicates(subset=["instrument"]).sort_values(["market", "code"]).reset_index(drop=True)


def parse_dbf_base(path: Path, updated_at: str) -> pd.DataFrame:
    """Parse dBase III base.dbf using its header metadata.

    The fields are kept as original TDX names. Numeric parsing is best-effort.
    """
    if not path.exists():
        return pd.DataFrame()
    data = path.read_bytes()
    if len(data) < 32:
        raise ValueError(f"Invalid DBF: {path}")
    n_records = struct.unpack("<I", data[4:8])[0]
    header_len = struct.unpack("<H", data[8:10])[0]
    record_len = struct.unpack("<H", data[10:12])[0]

    fields: list[dict] = []
    offset = 32
    while offset + 32 <= header_len and data[offset] != 0x0D:
        raw = data[offset : offset + 32]
        name = raw[:11].split(b"\x00", 1)[0].decode("ascii", errors="ignore").strip()
        ftype = chr(raw[11])
        length = raw[16]
        decimals = raw[17]
        if name:
            fields.append({"name": name, "type": ftype, "length": length, "decimals": decimals})
        offset += 32

    rows: list[dict] = []
    pos = header_len
    for _ in range(n_records):
        rec = data[pos : pos + record_len]
        pos += record_len
        if not rec or rec[0:1] == b"*":
            continue
        cursor = 1
        row: dict = {}
        for field in fields:
            raw_value = rec[cursor : cursor + field["length"]]
            cursor += field["length"]
            text = raw_value.decode("gb18030", errors="ignore").strip()
            if field["type"] == "N":
                if text == "":
                    value = None
                else:
                    try:
                        value = float(text) if field["decimals"] else int(float(text))
                    except ValueError:
                        value = text
            else:
                value = text
            row[field["name"]] = value
        code = str(row.get("GPDM", "")).zfill(6)
        market = market_flag_to_suffix(str(row.get("SC", "")))
        if market and len(code) == 6 and code.isdigit():
            row["instrument"] = make_instrument(code, market)
            row["code"] = code
            row["tdx_symbol"] = ("sh" if market == "SH" else "sz" if market == "SZ" else "bj") + code
            row["market"] = market
            row["source_file"] = path.name
            row["updated_at"] = updated_at
            rows.append(row)
    if not rows:
        return pd.DataFrame()
    # Keep identity columns first.
    df = pd.DataFrame(rows)
    front = ["instrument", "code", "tdx_symbol", "market", "source_file", "updated_at"]
    cols = front + [c for c in df.columns if c not in front]
    return df[cols].drop_duplicates(subset=["instrument"]).sort_values(["market", "code"]).reset_index(drop=True)


def write_table(df: pd.DataFrame, csv_path: Path, parquet_path: Path | None = None) -> None:
    ensure_dir(csv_path.parent)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    if parquet_path is not None:
        ensure_dir(parquet_path.parent)
        df.to_parquet(parquet_path, index=False)


def build_summary(tables: dict[str, pd.DataFrame], updated_at: str) -> pd.DataFrame:
    rows = []
    for name, df in tables.items():
        rows.append(
            {
                "table": name,
                "rows": int(len(df)),
                "columns": int(len(df.columns)) if not df.empty else 0,
                "updated_at": updated_at,
            }
        )
    return pd.DataFrame(rows)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Parse TDX hq_cache metadata tables")
    parser.add_argument("--input", type=Path, default=DEFAULT_STOCK_LOCAL_ROOT / "raw" / "sample" / "hq_cache.zip")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_STOCK_LOCAL_ROOT / "meta")
    parser.add_argument("--no-parquet", action="store_true", help="Only write CSV outputs")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    updated_at = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hq_dir, tempdir = resolve_hq_cache_path(args.input)
    try:
        tables = {
            "instruments": parse_all_tnf(hq_dir, updated_at),
            "tdx_industry_map": parse_tdxhy(hq_dir / "tdxhy.cfg", updated_at),
            "tdx_business_profile": parse_specgpext(hq_dir / "specgpext.txt", updated_at),
            "tdx_base_fundamental": parse_dbf_base(hq_dir / "base.dbf", updated_at),
        }
        for table_name, df in tables.items():
            csv_path = args.output_dir / f"{table_name}.csv"
            parquet_path = None if args.no_parquet else args.output_dir / f"{table_name}.parquet"
            write_table(df, csv_path, parquet_path)
            print(f"[OK] {table_name}: rows={len(df)} cols={len(df.columns)} -> {csv_path}")

        summary = build_summary(tables, updated_at)
        write_table(summary, args.output_dir / "hq_cache_parse_summary.csv", None if args.no_parquet else args.output_dir / "hq_cache_parse_summary.parquet")
        print(f"[META] {args.output_dir / 'hq_cache_parse_summary.csv'}")
    finally:
        if tempdir is not None:
            tempdir.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
