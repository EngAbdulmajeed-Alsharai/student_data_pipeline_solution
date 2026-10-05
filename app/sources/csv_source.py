from __future__ import annotations

from pathlib import Path

import pandas as pd


def extract_csv(file_path: str | Path) -> pd.DataFrame:
    """Read the raw student CSV into a DataFrame."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    df = pd.read_csv(path)
    if df.empty:
        raise ValueError("CSV source is empty.")
    return df
