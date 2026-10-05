from __future__ import annotations

import time
from pathlib import Path

import os

from app.output.csv_writer import save_dataframe, save_rejected_data
from app.output.mongo_writer import save_dataframe_to_mongo
from app.sources.html_source import extract_html
from app.sources.mongo_source import extract_mongo
from app.sources.api_source import extract_api
from app.sources.csv_source import extract_csv
from app.sources.database_source import extract_database
from app.transformation.cleaner import clean_source
from app.transformation.integration import integrate_data
from app.transformation.transformer import transform_data
from app.utils.logger import setup_logger
from app.validation.quality import validate_final_data, validate_source

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "data" / "raw" / "students.csv"
API_URL = "http://127.0.0.1:8000/students"
DB_PATH = BASE_DIR / "database" / "students.db"
HTML_SOURCE = BASE_DIR / "data" / "raw" / "students.html"
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DATABASE = os.getenv("MONGO_DATABASE", "student_pipeline")
MONGO_SOURCE_COLLECTION = os.getenv("MONGO_SOURCE_COLLECTION", "students")
MONGO_TARGET_DATABASE = os.getenv("MONGO_TARGET_DATABASE", "student_pipeline")
MONGO_TARGET_COLLECTION = os.getenv("MONGO_TARGET_COLLECTION", "final_students")
FINAL_PATH = BASE_DIR / "data" / "processed" / "final_dataset.csv"
REJECTED_PATH = BASE_DIR / "data" / "rejected" / "rejected_records.csv"
LOG_PATH = BASE_DIR / "logs" / "pipeline.log"


def run_pipeline():
    logger = setup_logger(LOG_PATH)
    start = time.perf_counter()
    all_rejected = []

    logger.info("CSV extraction started")
    csv_raw = extract_csv(CSV_PATH)
    logger.info("CSV records: %s", len(csv_raw))

    logger.info("API extraction started")
    api_raw = extract_api(API_URL)
    logger.info("API records: %s", len(api_raw))

    logger.info("Database extraction started")
    db_raw = extract_database(DB_PATH)
    logger.info("Database records: %s", len(db_raw))

    logger.info("HTML extraction started")
    html_raw = extract_html(HTML_SOURCE)
    logger.info("HTML records: %s", len(html_raw))

    logger.info("MongoDB extraction started")
    mongo_raw = extract_mongo(MONGO_URI, MONGO_DATABASE, MONGO_SOURCE_COLLECTION)
    logger.info("MongoDB records: %s", len(mongo_raw))

    logger.info("Source validation started")
    csv_issues = validate_source(csv_raw, "CSV")
    api_issues = validate_source(api_raw, "API")
    db_issues = validate_source(db_raw, "DATABASE", require_unique_id=False)
    html_issues = validate_source(html_raw, "HTML")
    mongo_issues = validate_source(mongo_raw, "MONGO")
    logger.info("CSV validation issues: %s", len(csv_issues))
    logger.info("API validation issues: %s", len(api_issues))
    logger.info("Database validation issues: %s", len(db_issues))
    logger.info("HTML validation issues: %s", len(html_issues))
    logger.info("MongoDB validation issues: %s", len(mongo_issues))

    logger.info("Cleaning started")
    csv_clean, csv_rejected, csv_stats = clean_source(csv_raw, csv_issues, "CSV")
    api_clean, api_rejected, api_stats = clean_source(api_raw, api_issues, "API")
    db_clean, db_rejected, db_stats = clean_source(db_raw, db_issues, "DATABASE")
    html_clean, html_rejected, html_stats = clean_source(html_raw, html_issues, "HTML")
    mongo_clean, mongo_rejected, mongo_stats = clean_source(mongo_raw, mongo_issues, "MONGO")
    all_rejected.extend([csv_rejected, api_rejected, db_rejected, html_rejected, mongo_rejected])
    logger.info("CSV clean records: %s", len(csv_clean))
    logger.info("API clean records: %s", len(api_clean))
    logger.info("Database clean records: %s", len(db_clean))
    logger.info("HTML clean records: %s", len(html_clean))
    logger.info("MongoDB clean records: %s", len(mongo_clean))

    logger.info("Integration started")
    integrated_data = integrate_data(csv_clean, api_clean, db_clean, html_clean, mongo_clean)
    logger.info("Integrated records: %s", len(integrated_data))

    logger.info("Transformation started")
    transformed_data = transform_data(integrated_data)

    logger.info("Final validation started")
    final_issues = validate_final_data(transformed_data)
    final_rejected = []
    if not final_issues.empty:
        for idx, group in final_issues.groupby("row_index"):
            if idx == -1:
                continue
            reasons = "; ".join(group["error_reason"].astype(str).unique())
            row = transformed_data.loc[idx]
            final_rejected.append({
                "source": "FINAL_VALIDATION",
                "student_id": row.get("student_id"),
                "error_reason": reasons,
                "raw_data": "; ".join(f"{col}={row[col]}" for col in transformed_data.columns),
            })
        invalid_indices = final_issues["row_index"].unique().tolist()
        transformed_data = transformed_data.drop(index=[i for i in invalid_indices if i >= 0]).reset_index(drop=True)

    if final_rejected:
        import pandas as pd
        all_rejected.append(pd.DataFrame(final_rejected))

    logger.info("Final validation issues: %s", len(final_issues))
    logger.info("Valid records: %s", len(transformed_data))

    import pandas as pd
    rejected_data = pd.concat(all_rejected, ignore_index=True) if all_rejected else pd.DataFrame()
    save_dataframe(transformed_data, FINAL_PATH)
    save_rejected_data(rejected_data, REJECTED_PATH)
    mongo_saved = save_dataframe_to_mongo(
        transformed_data, MONGO_URI, MONGO_TARGET_DATABASE, MONGO_TARGET_COLLECTION
    )

    elapsed = time.perf_counter() - start
    logger.info("Final dataset created")
    logger.info("PIPELINE EXECUTION SUMMARY")
    logger.info("CSV Records: %s", len(csv_raw))
    logger.info("API Records: %s", len(api_raw))
    logger.info("Database Records: %s", len(db_raw))
    logger.info("HTML Records: %s", len(html_raw))
    logger.info("MongoDB Source Records: %s", len(mongo_raw))
    logger.info("MongoDB Final Records Saved: %s", mongo_saved)
    logger.info("Integrated Records: %s", len(integrated_data))
    logger.info("Valid Records: %s", len(transformed_data))
    logger.info("Rejected Records: %s", len(rejected_data))
    logger.info("Duplicate Records: %s", csv_stats["duplicates"] + api_stats["duplicates"] + db_stats["duplicates"])
    logger.info("Missing Values After Cleaning: %s", csv_stats["missing_values_after_cleaning"] + api_stats["missing_values_after_cleaning"] + db_stats["missing_values_after_cleaning"])
    logger.info("Processing Time: %.2f seconds", elapsed)

    print("\nPipeline completed successfully.")
    print(f"Final dataset : {FINAL_PATH}")
    print(f"Rejected data : {REJECTED_PATH}")
    print(f"MongoDB final : {MONGO_TARGET_DATABASE}.{MONGO_TARGET_COLLECTION}")
    print(f"Log file      : {LOG_PATH}")
    return transformed_data, rejected_data


if __name__ == "__main__":
    run_pipeline()
