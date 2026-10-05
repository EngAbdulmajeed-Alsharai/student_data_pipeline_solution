from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import main
from app.sources.api_source import extract_api
from app.sources.csv_source import extract_csv
from app.sources.database_source import extract_database
from app.transformation.cleaner import clean_source
from app.transformation.integration import integrate_data
from app.transformation.transformer import transform_data
from app.validation.quality import validate_source


class PipelineTests(unittest.TestCase):
    def test_csv_can_be_loaded(self):
        df = extract_csv(main.CSV_PATH)
        self.assertGreater(len(df), 0)

    @patch("app.sources.api_source.requests.get")
    def test_api_can_be_connected(self, mock_get):
        response = mock_get.return_value
        response.status_code = 200
        response.json.return_value = [{"student_id": 1, "gpa": 3.0, "attendance": 80, "status": "Active"}]
        response.raise_for_status.return_value = None
        df = extract_api("http://example.test/students")
        self.assertEqual(len(df), 1)
        self.assertIn("gpa", df.columns)

    def test_sqlite_can_be_extracted(self):
        df = extract_database(main.DB_PATH)
        self.assertGreater(len(df), 0)
        self.assertIn("course_name", df.columns)

    def test_duplicates_are_detected_and_removed(self):
        df = pd.DataFrame({"student_id": [1, 1, 2], "age": [20, 20, 21]})
        issues = validate_source(df, "CSV")
        cleaned, rejected, stats = clean_source(df, issues, "CSV")
        self.assertEqual(cleaned["student_id"].tolist(), [1, 2])
        self.assertGreaterEqual(len(rejected), 1)
        self.assertGreaterEqual(stats["duplicates"], 1)

    def test_missing_values_are_processed(self):
        df = pd.DataFrame({"student_id": [1, 2], "age": [20, None], "student_name": ["A", "B"], "major": ["CS", "AI"], "city": ["Sanaa", None]})
        issues = validate_source(df, "CSV")
        cleaned, _, _ = clean_source(df, issues, "CSV")
        self.assertFalse(cleaned["age"].isna().any())
        self.assertFalse(cleaned["city"].isna().any())

    def test_invalid_records_are_rejected(self):
        df = pd.DataFrame({"student_id": [1, 2], "age": [20, 10]})
        issues = validate_source(df, "CSV")
        cleaned, rejected, _ = clean_source(df, issues, "CSV")
        self.assertEqual(len(cleaned), 1)
        self.assertTrue(rejected["error_reason"].str.contains("Invalid Age").any())

    def test_three_sources_integrate(self):
        csv_df = pd.DataFrame({"student_id": [1], "student_name": ["A"], "age": [20], "major": ["CS"], "city": ["Sanaa"]})
        api_df = pd.DataFrame({"student_id": [1], "gpa": [3.0], "attendance": [90], "status": ["Active"]})
        db_df = pd.DataFrame({"student_id": [1, 1], "course_id": [10, 11], "course_name": ["Python", "DB"], "credit_hours": [3, 3], "semester": ["2026-1", "2026-1"], "score": [80, 90]})
        integrated = integrate_data(csv_df, api_df, db_df)
        transformed = transform_data(integrated)
        self.assertEqual(len(transformed), 1)
        self.assertIn("performance_level", transformed.columns)

    def test_final_dataset_is_created(self):
        self.assertTrue(main.FINAL_PATH.exists())


if __name__ == "__main__":
    unittest.main()
