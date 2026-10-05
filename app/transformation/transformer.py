from __future__ import annotations

import pandas as pd


def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """Perform type conversions and create derived analytical columns."""
    result = df.copy()

    result["student_id"] = pd.to_numeric(result["student_id"], errors="coerce").astype("Int64")
    result["age"] = pd.to_numeric(result["age"], errors="coerce").astype("Int64")
    result["gpa"] = pd.to_numeric(result["gpa"], errors="coerce").round(2)
    result["attendance"] = pd.to_numeric(result["attendance"], errors="coerce").round(2)
    result["course_count"] = pd.to_numeric(result["course_count"], errors="coerce").astype("Int64")
    result["avg_score"] = pd.to_numeric(result["avg_score"], errors="coerce").round(2)

    result["performance_level"] = pd.cut(
        result["gpa"],
        bins=[-float("inf"), 2.0, 2.5, 3.0, 3.5, float("inf")],
        labels=["At Risk", "Acceptable", "Good", "Very Good", "Excellent"],
        right=False,
    ).astype("string")

    result["attendance_status"] = result["attendance"].apply(
        lambda value: "Good" if pd.notna(value) and value >= 75 else "Low"
    )

    columns = [
        "student_id",
        "student_name",
        "age",
        "major",
        "city",
        "gpa",
        "attendance",
        "status",
        "course_count",
        "avg_score",
        "performance_level",
        "attendance_status",
        "source",
    ]
    optional_source_columns = [
        column for column in ["html_gpa", "html_attendance", "mongo_gpa", "mongo_attendance"]
        if column in result.columns
    ]
    return result[columns + optional_source_columns].sort_values("student_id").reset_index(drop=True)
