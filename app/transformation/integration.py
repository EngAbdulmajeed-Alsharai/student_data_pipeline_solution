from __future__ import annotations

import pandas as pd


def integrate_data(
    csv_data: pd.DataFrame,
    api_data: pd.DataFrame,
    database_data: pd.DataFrame,
    html_data: pd.DataFrame | None = None,
    mongo_data: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Integrate CSV + API + SQLite and enrich matches from HTML/MongoDB by student_id."""
    db_summary = (
        database_data.groupby("student_id", as_index=False)
        .agg(
            course_count=("course_id", "nunique"),
            avg_score=("score", "mean"),
        )
    )

    integrated = csv_data.merge(api_data, on="student_id", how="inner")
    integrated = integrated.merge(db_summary, on="student_id", how="inner")
    integrated["source"] = "CSV+API+DATABASE"

    for source_name, source_data in (("html", html_data), ("mongo", mongo_data)):
        if source_data is None or source_data.empty:
            continue
        source = source_data.copy()
        source = source.rename(columns={"gpa": f"{source_name}_gpa", "attendance": f"{source_name}_attendance"})
        keep = [column for column in ["student_id", f"{source_name}_gpa", f"{source_name}_attendance"] if column in source.columns]
        source = source[keep].drop_duplicates(subset=["student_id"], keep="first")
        integrated = integrated.merge(source, on="student_id", how="left", validate="one_to_one")
        integrated["source"] = integrated["source"] + f"+{source_name.upper()}"

    return integrated
