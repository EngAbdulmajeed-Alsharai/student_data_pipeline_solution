from __future__ import annotations

from typing import Any

import requests
import pandas as pd


def extract_api(url: str, timeout: int = 10) -> pd.DataFrame:
    """Fetch student records from a REST API and return a DataFrame."""
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
    except requests.exceptions.Timeout as exc:
        raise RuntimeError("API request timed out.") from exc
    except requests.exceptions.ConnectionError as exc:
        raise RuntimeError("Could not connect to API.") from exc
    except requests.exceptions.HTTPError as exc:
        raise RuntimeError(f"API returned HTTP error: {response.status_code}") from exc
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"API request failed: {exc}") from exc

    try:
        payload: Any = response.json()
    except ValueError as exc:
        raise RuntimeError("API returned invalid JSON.") from exc

    if not payload:
        raise RuntimeError("API returned an empty response.")

    if isinstance(payload, dict) and "students" in payload:
        records = payload["students"]
    elif isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        records = [payload]
    else:
        raise RuntimeError("API JSON structure is not supported.")

    df = pd.DataFrame(records)
    if df.empty:
        raise RuntimeError("API returned no records.")
    return df
