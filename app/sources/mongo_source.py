from __future__ import annotations

import pandas as pd
from pymongo import MongoClient
from pymongo.errors import PyMongoError


def extract_mongo(uri: str, database: str, collection: str, timeout_ms: int = 5000) -> pd.DataFrame:

    try:
        with MongoClient(uri, serverSelectionTimeoutMS=timeout_ms) as client:
            client.admin.command("ping")
            documents = list(client[database][collection].find({}, {"_id": 0}))
    except PyMongoError as exc:
        raise RuntimeError(f"Could not read MongoDB {database}.{collection}: {exc}") from exc

    if not documents:
        raise ValueError(f"MongoDB collection {database}.{collection} is empty.")
    return pd.DataFrame(documents)
