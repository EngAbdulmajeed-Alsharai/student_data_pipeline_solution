from pathlib import Path
import unittest

from app.sources.html_source import extract_html


class TestHTMLSource(unittest.TestCase):
    def test_extracts_student_table(self):
        base = Path(__file__).resolve().parents[1]
        df = extract_html(base / "data" / "raw" / "students.html")
        self.assertEqual(list(df.columns), ["student_id", "gpa", "attendance"])
        self.assertEqual(len(df), 6)
        self.assertEqual(str(df.iloc[0]["student_id"]), "1001")


if __name__ == "__main__":
    unittest.main()
