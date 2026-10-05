from __future__ import annotations

import re
from typing import Iterable

import pandas as pd


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Convert column names to lower snake_case."""
    result = df.copy()
    normalized = []
    for column in result.columns:
        name = str(column).strip().lower()
        name = re.sub(r"[^a-z0-9]+", "_", name).strip("_")
        normalized.append(name)
    result.columns = normalized
    return result


def _normalize_text(value):
    if pd.isna(value):
        return value
    text = str(value).strip()
    if text == "":
        return pd.NA
    return text.title()


def _build_rejected(df: pd.DataFrame, indices: Iterable, reasons: dict[int, str], source: str) -> pd.DataFrame:
    rows = []
    for idx in indices:
        row = df.loc[idx]
        student_id = row.get("student_id", pd.NA)
        raw = "; ".join(f"{col}={row[col]}" for col in df.columns)
        rows.append({
            "source": source,
            "student_id": student_id,
            "error_reason": reasons.get(idx, "Quality rule failed"),
            "raw_data": raw,
        })
    return pd.DataFrame(rows, columns=["source", "student_id", "error_reason", "raw_data"])


def _merge_issue_reasons(issues: pd.DataFrame) -> dict[int, str]:
    result: dict[int, list[str]] = {}
    for _, issue in issues.iterrows():
        idx = int(issue["row_index"])
        result.setdefault(idx, []).append(str(issue["error_reason"]))
    return {idx: "; ".join(values) for idx, values in result.items()}


def clean_source(df: pd.DataFrame, issues: pd.DataFrame, source: str) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int]]:
    """Remove invalid records and repair recoverable quality problems."""
    result = normalize_column_names(df)
    result.index = range(len(result))

    issue_reasons = _merge_issue_reasons(issues)
    invalid_indices = sorted(issue_reasons.keys())

    rejected = _build_rejected(result, invalid_indices, issue_reasons, source)
    if invalid_indices:
        result = result.drop(index=invalid_indices)

    duplicate_issue_count = sum("Duplicate" in reason for reason in issue_reasons.values())
    duplicate_mask = result.duplicated(keep="first")
    duplicate_indices = result.index[duplicate_mask].tolist()
    if duplicate_indices:
        duplicate_reasons = {idx: "Duplicate record" for idx in duplicate_indices}
        duplicate_rejected = _build_rejected(result, duplicate_indices, duplicate_reasons, source)
        rejected = pd.concat([rejected, duplicate_rejected], ignore_index=True)
        result = result.drop(index=duplicate_indices)

    # Common type cleanup.
    if "student_id" in result.columns:
        result["student_id"] = pd.to_numeric(result["student_id"], errors="coerce").astype("Int64")

    if source == "CSV":
        if "age" in result.columns:
            result["age"] = pd.to_numeric(result["age"], errors="coerce")
            if result["age"].notna().any():
                result["age"] = result["age"].fillna(result["age"].median()).round().astype("Int64")

        for column in ["student_name", "major", "city"]:
            if column in result.columns:
                result[column] = result[column].map(_normalize_text).fillna("Unknown")

    elif source == "API":
        for column in ["gpa", "attendance"]:
            if column in result.columns:
                result[column] = pd.to_numeric(result[column], errors="coerce")

        if result["gpa"].notna().any():
            result["gpa"] = result["gpa"].fillna(result["gpa"].median())
        if result["attendance"].notna().any():
            result["attendance"] = result["attendance"].fillna(result["attendance"].mean())

        if "status" in result.columns:
            result["status"] = result["status"].map(_normalize_text).fillna("Unknown")

    elif source in {"HTML", "MONGO"}:
        for column in ["gpa", "attendance"]:
            if column in result.columns:
                result[column] = pd.to_numeric(result[column].astype("string").str.strip(), errors="coerce")

        # Invalid numeric values are handled explicitly rather than silently imputed.
        required_numeric = [column for column in ["gpa", "attendance"] if column in result.columns]
        missing_mask = result[required_numeric].isna().any(axis=1) if required_numeric else pd.Series(False, index=result.index)
        if missing_mask.any():
            missing_indices = result.index[missing_mask].tolist()
            missing_reasons = {idx: "Missing or non-numeric GPA/attendance" for idx in missing_indices}
            missing_rejected = _build_rejected(result, missing_indices, missing_reasons, source)
            rejected = pd.concat([rejected, missing_rejected], ignore_index=True)
            result = result.drop(index=missing_indices)

    elif source == "DATABASE":
        result["score"] = pd.to_numeric(result["score"], errors="coerce")
        missing_score = result["score"].isna()
        if missing_score.any():
            missing_indices = result.index[missing_score].tolist()
            missing_reasons = {idx: "Missing Score" for idx in missing_indices}
            missing_rejected = _build_rejected(result, missing_indices, missing_reasons, source)
            rejected = pd.concat([rejected, missing_rejected], ignore_index=True)
            result = result.drop(index=missing_indices)

        for column in ["course_name", "semester"]:
            if column in result.columns:
                result[column] = result[column].map(_normalize_text).fillna("Unknown")

    stats = {
        "rejected": len(rejected),
        "duplicates": duplicate_issue_count + len(duplicate_indices),
        "missing_values_after_cleaning": int(result.isna().sum().sum()),
    }
    return result.reset_index(drop=True), rejected.reset_index(drop=True), stats
