"""IO helpers for local_quant.

Keep storage boring and predictable:
- raw files stay untouched;
- normalized bars are written as Parquet partitioned by instrument;
- CSV is only for small human-readable samples/meta.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd


_REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_STOCK_LOCAL_ROOT = _REPO_ROOT / "data" / "stock_local"


def ensure_dir(path: str | os.PathLike) -> Path:
    """Create directory if needed and return it as Path."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def parse_instrument_from_filename(filename: str | os.PathLike) -> Optional[str]:
    """Parse TDX filename into standard instrument.

    Examples:
    - sh000001.day -> 000001.SH
    - sz000001.lc5 -> 000001.SZ
    """
    stem = Path(filename).stem.lower()
    m = re.fullmatch(r"(sh|sz)(\d{6})", stem)
    if not m:
        return None
    market, code = m.groups()
    suffix = "SH" if market == "sh" else "SZ"
    return f"{code}.{suffix}"


def instrument_to_tdx_stem(instrument: str) -> Optional[str]:
    """Convert 600000.SH / 000001.SZ to sh600000 / sz000001."""
    text = instrument.strip().upper()
    m = re.fullmatch(r"(\d{6})\.(SH|SZ)", text)
    if not m:
        return None
    code, market = m.groups()
    return ("sh" if market == "SH" else "sz") + code


def normalize_symbol_filter(symbols: str | Iterable[str] | None) -> set[str] | None:
    """Return acceptable lowercase stems and uppercase instruments for filtering."""
    if not symbols:
        return None
    if isinstance(symbols, str):
        raw = [s.strip() for s in symbols.split(",") if s.strip()]
    else:
        raw = [str(s).strip() for s in symbols if str(s).strip()]
    out: set[str] = set()
    for s in raw:
        low = s.lower()
        out.add(low)
        inst = parse_instrument_from_filename(low)
        if inst:
            out.add(inst.upper())
            continue
        stem = instrument_to_tdx_stem(s)
        if stem:
            out.add(stem.lower())
            out.add(s.upper())
    return out


def symbol_allowed(path: str | os.PathLike, allowed: set[str] | None) -> bool:
    """Whether a TDX file passes optional symbol filter."""
    if allowed is None:
        return True
    stem = Path(path).stem.lower()
    inst = parse_instrument_from_filename(path)
    return stem in allowed or (inst is not None and inst.upper() in allowed)


def write_bars_parquet(df: pd.DataFrame, output_dir: str | os.PathLike, instrument: str) -> Path:
    """Write bars DataFrame to partitioned Parquet.

    Path: {output_dir}/instrument={instrument}/part-000.parquet
    """
    partition_dir = ensure_dir(Path(output_dir) / f"instrument={instrument}")
    output_path = partition_dir / "part-000.parquet"
    df.to_parquet(output_path, index=False)
    return output_path


def write_sample_csv(df: pd.DataFrame, csv_path: str | os.PathLike, n: int = 100) -> Path:
    """Write a small CSV sample for human inspection."""
    csv_path = Path(csv_path)
    ensure_dir(csv_path.parent)
    df.head(n).to_csv(csv_path, index=False, encoding="utf-8-sig")
    return csv_path


def write_meta_summary(meta_list: list[dict], output_path: str | os.PathLike) -> Path:
    """Write metadata summary CSV."""
    output_path = Path(output_path)
    ensure_dir(output_path.parent)
    pd.DataFrame(meta_list).to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path


def read_partitioned_parquet(path: str | os.PathLike) -> pd.DataFrame:
    """Read all parquet files under a path or a single parquet file."""
    p = Path(path)
    if p.is_file():
        return pd.read_parquet(p)
    files = sorted(p.glob("**/*.parquet"))
    if not files:
        raise FileNotFoundError(f"No parquet files found under {p}")
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
