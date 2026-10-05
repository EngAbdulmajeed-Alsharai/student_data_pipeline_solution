# Student Data Pipeline

## 1. Project Overview
A Python ETL/data integration pipeline that extracts student data from CSV, REST API, SQLite, an HTML table, and MongoDB; validates and cleans the data; integrates matching student records using `student_id`; then writes the final dataset to both CSV and MongoDB.

## 2. Architecture
- `app/sources`: extraction layer
- `app/validation`: quality rules
- `app/transformation`: cleaning, integration, transformation
- `app/output`: output writers
- `app/utils`: logging
- `data/raw`: raw input data
- `data/processed`: final dataset
- `data/rejected`: invalid/rejected records
- `database`: SQLite database
- `tests`: automated tests

## 3. Data Sources
1. CSV: `data/raw/students.csv`
2. REST API: local mock endpoint `http://127.0.0.1:8000/students`
3. SQLite: `database/students.db`
4. HTML: `data/raw/students.html` (the extractor also accepts a public HTTP(S) URL)
5. MongoDB source: `student_pipeline.students` on `mongodb://localhost:27017`

The local REST API is used so the project remains reproducible without depending on an external service.

## 4. ETL Pipeline
Extract (CSV/API/SQLite/HTML/MongoDB) -> Validate -> Clean -> Integrate by `student_id` -> Transform -> Final Validation -> Load (CSV + MongoDB).

HTML and MongoDB `gpa`/`attendance` are kept as `html_gpa`, `html_attendance`, `mongo_gpa`, and `mongo_attendance` in the final result. The existing API GPA/attendance remain the main values for the original student-level pipeline. Records with invalid source-level GPA or attendance are rejected according to the existing quality rules.

## 5. Data Quality Rules
- `student_id` cannot be null.
- `student_id` must be unique for student-level sources and the final dataset; SQLite enrollment rows may contain multiple rows per student because enrollment is one-to-many.
- `age` must be between 16 and 80.
- `gpa` must be between 0 and 4.
- `attendance` must be between 0 and 100.
- `score` must be between 0 and 100.
- IDs from the sources must be compatible for integration.

## 6. Missing Value Strategy
- Missing `student_id`: reject record.
- Missing `age`: fill with median valid age from the CSV source.
- Missing `gpa`: fill with median valid GPA from the API source.
- Missing `attendance`: fill with mean valid attendance from the API source.
- Missing text: fill with `Unknown` after trimming/normalization.
- Missing database score: reject the enrollment record because it cannot contribute a reliable score average.

## 7. Transformation
- Normalize columns to snake_case.
- Convert numeric strings to numeric data types.
- Normalize text case and spaces.
- Aggregate SQLite enrollments to one row per student using `course_count` and `avg_score`.
- Create `performance_level` from GPA.
- Create `attendance_status` from attendance.
- Add `source` for data lineage.

## 8. Installation
```powershell
python -m pip install -r requirements.txt
python setup_database.py
```

Make sure MongoDB Server is running locally and that the source collection `student_pipeline.students` exists. Configure the MongoDB settings with environment variables if needed: `MONGO_URI`, `MONGO_DATABASE`, `MONGO_SOURCE_COLLECTION`, `MONGO_TARGET_DATABASE`, and `MONGO_TARGET_COLLECTION`. The default output collection is `student_pipeline.final_students`.

## 9. Running
Open two terminal tabs.

Terminal 1:
```bash
python api_server.py
```

Terminal 2:
```bash
python main.py
```

## 10. Testing
```bash
python -m unittest discover -s tests -v
```

## 11. Outputs
- `data/processed/final_dataset.csv`
- `data/rejected/rejected_records.csv`
- MongoDB destination: `student_pipeline.final_students` (replaced with the latest successful run)
- `logs/pipeline.log`

## 12. Answers to the required questions

### 1. Why do we need a data pipeline for multiple sources?
Because data is distributed across systems with different formats and quality problems. A pipeline provides a repeatable process for extraction, validation, cleaning, integration, and loading.

### 2. Raw Data vs Processed Data
Raw data is the original data as received. Processed data has been cleaned, validated, standardized, integrated, and transformed for downstream use.

### 3. Extract vs Transform vs Load
Extract reads data from sources. Transform changes structure, types, values, and derived fields. Load writes the prepared result to the target destination.

### 4. What problems occurred during integration?
Different formats, duplicate IDs, missing values, invalid values, inconsistent text, and one-to-many enrollment records had to be handled before producing one student-level record.

### 5. How were missing values handled?
Missing required IDs were rejected. Numeric values that can be reasonably imputed were filled using a documented median/mean strategy. Missing text was normalized and filled with `Unknown`.

### 6. How were duplicate records handled?
Duplicates were detected during validation and removed during cleaning. The removed records are also recorded as rejected records with a reason.

### 7. How were invalid records handled?
Records that violate hard quality rules are excluded from the processed dataset and written to `rejected_records.csv` with a reason.

### 8. Why separate Extraction from Transformation?
Separation keeps each layer focused on one responsibility and makes the system easier to test, maintain, and extend with new sources.

### 9. Why is data validation essential?
Because downstream analysis and machine learning depend on reliable inputs. Validation catches missing identifiers, invalid ranges, duplicates, and incompatibilities before they contaminate the final dataset.

### 10. How can the pipeline run automatically?
It can be scheduled with a task scheduler, cron, or an orchestration platform, with logging and monitoring for each run.

### 11. How can the pipeline handle millions of records?
Use chunked reads, database-side filtering/aggregation, incremental processing, efficient joins, partitioning, and distributed processing when required.

### 12. Batch vs Streaming
Batch processing handles a group of records periodically. Streaming processes records continuously or with very low latency as they arrive.
