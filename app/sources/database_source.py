from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


def extract_database(db_path: str | Path) -> pd.DataFrame:
    """Extract enrollment data and course information from SQLite."""
    path = Path(db_path)
    if not path.exists():
        raise FileNotFoundError(f"Database not found: {path}")

    query = """
        SELECT
            e.student_id,
            e.course_id,
            c.course_name,
            c.credit_hours,
            e.semester,
            e.score
        FROM enrollments AS e
        LEFT JOIN courses AS c
            ON e.course_id = c.course_id
        ORDER BY e.student_id, e.course_id;
    """

    with sqlite3.connect(path) as connection:
        df = pd.read_sql_query(query, connection)

    if df.empty:
        raise ValueError("Database query returned no records.")
    return df
