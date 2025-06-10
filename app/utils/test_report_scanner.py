import unittest
from pathlib import Path
import shutil # For cleaning up test directories

from app.utils.report_scanner import find_reports

class TestReportScanner(unittest.TestCase):

    def setUp(self):
        # Create a temporary test directory structure for report scanning
        self.test_dir_path = Path("./temp_test_reports_dir_for_scanner")
        self.test_dir_path.mkdir(parents=True, exist_ok=True)

        # Create some dummy report files and folders
        (self.test_dir_path / "Report_Alpha.html").touch()
        (self.test_dir_path / "Report Beta With Spaces.html").touch()

        sub_folder = self.test_dir_path / "Subfolder"
        sub_folder.mkdir()
        (sub_folder / "Report_Gamma_In_Sub.html").touch()

        # Create a non-HTML file to ensure it's ignored
        (self.test_dir_path / "not_a_report.txt").touch()
        (sub_folder / "document.pdf").touch()

    def tearDown(self):
        # Remove the temporary test directory and its contents
        if self.test_dir_path.exists():
            shutil.rmtree(self.test_dir_path)

    def test_find_reports_successfully(self):
        reports = find_reports(str(self.test_dir_path))

        self.assertEqual(len(reports), 3, "Should find 3 HTML files.")

        # Check for specific report names and paths
        # Note: Paths from find_reports are relative to the scanned directory (self.test_dir_path)
        expected_reports = [
            {'name': 'Report Alpha', 'path': 'Report_Alpha.html'},
            {'name': 'Report Beta With Spaces', 'path': 'Report Beta With Spaces.html'},
            {'name': 'Report Gamma In Sub', 'path': str(Path('Subfolder') / 'Report_Gamma_In_Sub.html')},
        ]

        # Convert list of dicts to list of tuples of sorted items for easier comparison
        # This makes the test order-agnostic for the found reports
        reports_tuples = sorted([tuple(sorted(r.items())) for r in reports])
        expected_tuples = sorted([tuple(sorted(r.items())) for r in expected_reports])

        self.assertListEqual(reports_tuples, expected_tuples, "Report details (name, path) do not match expected.")

    def test_find_reports_empty_directory(self):
        empty_dir = self.test_dir_path / "EmptySubfolder"
        empty_dir.mkdir()
        reports = find_reports(str(empty_dir))
        self.assertEqual(len(reports), 0, "Should find 0 reports in an empty directory.")

    def test_find_reports_no_html_files(self):
        no_html_dir = self.test_dir_path / "NoHtmlSubfolder"
        no_html_dir.mkdir()
        (no_html_dir / "some_text.txt").touch()
        (no_html_dir / "another_file.dat").touch()
        reports = find_reports(str(no_html_dir))
        self.assertEqual(len(reports), 0, "Should find 0 reports if no HTML files are present.")

    def test_find_reports_nonexistent_directory(self):
        non_existent_dir = str(self.test_dir_path / "ThisFolderDoesNotExist")
        reports = find_reports(non_existent_dir)
        self.assertEqual(len(reports), 0, "Should return an empty list for a non-existent directory.")
        # Optionally, check for a printed error message if your find_reports function logs errors.
        # This might require capturing stdout/stderr, which can be more involved.

if __name__ == '__main__':
    unittest.main()
