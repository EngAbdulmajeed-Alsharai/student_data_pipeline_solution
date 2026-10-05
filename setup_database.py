from __future__ import annotations

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database" / "students.db"

COURSES = [
    (1, "Python Programming", 3),
    (2, "Database Systems", 3),
    (3, "Data Analysis", 3),
    (4, "AI Fundamentals", 4),
    (5, "Web Technologies", 3),
]

ENROLLMENTS = [
    (1001, 1, "2026-1", 90),
    (1001, 2, "2026-1", 85),
    (1002, 4, "2026-1", 88),
    (1002, 2, "2026-1", 91),
    (1002, 4, "2026-1", 88),
    (1003, 2, "2026-1", 76),
    (1003, 3, "2026-1", 82),
    (1004, 3, "2026-1", 95),
    (1005, 1, "2026-1", 89),
    (1005, 5, "2026-1", 93),
    (1006, 2, "2026-1", 105),
    (1007, 4, "2026-1", 70),
    (1008, 3, "2026-1", 84),
    (1009, 3, "2026-1", 90),
    (1010, 4, "2026-1", 60),
]


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("DROP TABLE IF EXISTS enrollments")
        connection.execute("DROP TABLE IF EXISTS courses")
        connection.execute(
            """
            CREATE TABLE courses (
                course_id INTEGER PRIMARY KEY,
                course_name TEXT NOT NULL,
                credit_hours INTEGER NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE enrollments (
                student_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                semester TEXT NOT NULL,
                score REAL
            )
            """
        )
        connection.executemany("INSERT INTO courses VALUES (?, ?, ?)", COURSES)
        connection.executemany("INSERT INTO enrollments VALUES (?, ?, ?, ?)", ENROLLMENTS)
        connection.commit()
    print(f"SQLite database created: {DB_PATH}")


if __name__ == "__main__":
    main()
