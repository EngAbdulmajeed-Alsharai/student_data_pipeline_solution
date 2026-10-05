from __future__ import annotations

import pandas as pd


def validate_source(df: pd.DataFrame, source: str, require_unique_id: bool = True) -> pd.DataFrame:
    """Run the assignment's quality rules before integration."""
    from app.transformation.cleaner import normalize_column_names

    result = normalize_column_names(df)
    result.index = range(len(result))
    issues: list[dict] = []

    if "student_id" in result.columns:
        ids = result["student_id"].astype("string").str.strip()
        missing_id = ids.isna() | (ids == "")
        for idx in result.index[missing_id]:
            issues.append({
                "source": source,
                "row_index": int(idx),
                "student_id": result.at[idx, "student_id"],
                "error_reason": "Missing student_id",
            })

        if require_unique_id:
            valid_ids = ids[~missing_id]
            duplicates = valid_ids.duplicated(keep="first")
            for idx in valid_ids.index[duplicates]:
                issues.append({
                    "source": source,
                    "row_index": int(idx),
                    "student_id": result.at[idx, "student_id"],
                    "error_reason": "Duplicate student_id",
                })
    else:
        issues.append({
            "source": source,
            "row_index": -1,
            "student_id": pd.NA,
            "error_reason": "Missing student_id column",
        })

    numeric_rules = {
        "age": (16, 80, "Invalid Age"),
        "gpa": (0, 4, "Invalid GPA"),
        "attendance": (0, 100, "Invalid Attendance"),
        "score": (0, 100, "Invalid Score"),
    }

    for column, (minimum, maximum, reason) in numeric_rules.items():
        if column not in result.columns:
            continue
        values = pd.to_numeric(result[column], errors="coerce")
        invalid = values.notna() & ((values < minimum) | (values > maximum))
        for idx in result.index[invalid]:
            issues.append({
                "source": source,
                "row_index": int(idx),
                "student_id": result.at[idx, "student_id"] if "student_id" in result.columns else pd.NA,
                "error_reason": reason,
            })

    return pd.DataFrame(issues, columns=["source", "row_index", "student_id", "error_reason"])


def validate_final_data(df: pd.DataFrame) -> pd.DataFrame:
    """Validate the final student-level dataset."""
    result = df.copy()
    issues: list[dict] = []

    if "student_id" not in result.columns:
        issues.append({"row_index": -1, "student_id": pd.NA, "error_reason": "Missing student_id column"})
        return pd.DataFrame(issues)

    missing_id = result["student_id"].isna()
    for idx in result.index[missing_id]:
        issues.append({"row_index": int(idx), "student_id": pd.NA, "error_reason": "Missing student_id"})

    duplicate_id = result["student_id"].duplicated(keep="first")
    for idx in result.index[duplicate_id]:
        issues.append({"row_index": int(idx), "student_id": result.at[idx, "student_id"], "error_reason": "Duplicate student_id"})

    rules = {
        "age": (16, 80, "Invalid Age"),
        "gpa": (0, 4, "Invalid GPA"),
        "attendance": (0, 100, "Invalid Attendance"),
        "avg_score": (0, 100, "Invalid Average Score"),
    }
    for column, (minimum, maximum, reason) in rules.items():
        if column not in result.columns:
            continue
        values = pd.to_numeric(result[column], errors="coerce")
        invalid = values.isna() | (values < minimum) | (values > maximum)
        for idx in result.index[invalid]:
            issues.append({
                "row_index": int(idx),
                "student_id": result.at[idx, "student_id"],
                "error_reason": reason,
            })

    required = ["student_name", "major", "city", "gpa", "attendance", "status", "course_count", "avg_score"]
    for column in required:
        if column not in result.columns:
            continue
        missing = result[column].isna()
        for idx in result.index[missing]:
            issues.append({
                "row_index": int(idx),
                "student_id": result.at[idx, "student_id"],
                "error_reason": f"Missing {column}",
            })

    return pd.DataFrame(issues, columns=["row_index", "student_id", "error_reason"])
