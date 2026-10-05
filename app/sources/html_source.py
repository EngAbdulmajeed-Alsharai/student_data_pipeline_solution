from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup


def extract_html(source: str | Path, timeout: int = 15) -> pd.DataFrame:
    """Extract student rows from an HTML table in a local file or HTTP(S) URL."""
    source_text = str(source)
    parsed = urlparse(source_text)
    if parsed.scheme in {"http", "https"}:
        try:
            response = requests.get(source_text, timeout=timeout, headers={"User-Agent": "StudentDataPipeline/1.0"})
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"Could not fetch HTML source {source_text}: {exc}") from exc
        html = response.text
    else:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"HTML file not found: {path}")
        html = path.read_text(encoding="utf-8")

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="students") or soup.find("table")
    if table is None:
        raise ValueError("No HTML table was found in the supplied source.")

    rows = []
    header_cells = table.find("tr")
    if header_cells is None:
        raise ValueError("The HTML table has no header row.")
    headers = [cell.get_text(" ", strip=True) for cell in header_cells.find_all(["th", "td"])]
    if not headers:
        raise ValueError("The HTML table header is empty.")

    for tr in table.find_all("tr")[1:]:
        cells = tr.find_all(["td", "th"])
        if not cells:
            continue
        values = [cell.get_text(" ", strip=True) for cell in cells]
        if len(values) != len(headers):
            continue
        rows.append(dict(zip(headers, values)))

    df = pd.DataFrame(rows)
    if df.empty:
        raise ValueError("The HTML table contains no data rows.")
    return df
