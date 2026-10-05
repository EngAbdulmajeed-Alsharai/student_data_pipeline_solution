from __future__ import annotations

import math
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from pymongo import MongoClient
from pymongo.errors import PyMongoError


def _mongo_safe(value: Any) -> Any:
    """Convert pandas/numpy missing values and scalars to BSON-safe Python values."""
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if hasattr(value, "item") and callable(value.item):
        try:
            value = value.item()
        except (ValueError, TypeError):
            pass
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, (date, datetime)):
        return value
    return value


def save_dataframe_to_mongo(
    df: pd.DataFrame, uri: str, database: str, collection: str, timeout_ms: int = 5000
) -> int:

    records = []
    for row in df.to_dict(orient="records"):
        record = {str(key): _mongo_safe(value) for key, value in row.items()}
        records.append(record)

    try:
        with MongoClient(uri, serverSelectionTimeoutMS=timeout_ms) as client:
            client.admin.command("ping")
            target = client[database][collection]
            target.delete_many({})
            if records:
                target.insert_many(records)
            return len(records)
    except PyMongoError as exc:
        raise RuntimeError(f"Could not write final data to MongoDB {database}.{collection}: {exc}") from exc
