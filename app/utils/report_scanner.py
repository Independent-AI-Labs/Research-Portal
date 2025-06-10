import os
from pathlib import Path

def find_reports(directory: str):
    """
    Scans the given directory recursively for HTML files.

    Args:
        directory: The absolute path to the directory to scan.

    Returns:
        A list of dictionaries, where each dictionary has:
            'name': The display name of the report (derived from filename, spaces replacing underscores/hyphens).
            'path': The path to the HTML file relative to the scanned 'directory' (the base_path).
                    For example, if scanning '/path/to/reports' and a report is at
                    '/path/to/reports/subdir/my_report.html', the 'path' will be
                    'subdir/my_report.html'.
    """
    report_files = []
    base_path = Path(directory)
    if not base_path.is_dir():
        print(f"Error: Directory '{directory}' not found.")
        return []

    for html_file in base_path.rglob('*.html'):
        # Determine the path for the report relative to the scanned directory (base_path).
        # This relative path is used by Gradio when serving files from an allowed directory.
        # For example, if base_path is "/data/Smart Reports" and html_file is
        # "/data/Smart Reports/Q1/Report.html", then report_relative_path will be "Q1/Report.html".
        report_relative_path = html_file.relative_to(base_path)

        report_files.append({
            'name': html_file.stem.replace('_', ' ').replace('-', ' '), # Also replace hyphens
            'path': str(report_relative_path) # Path relative to the scanned directory root
        })
    return report_files

if __name__ == '__main__':
    # Example Usage (assuming 'Smart Reports' directory exists at the root)
    # Create dummy files for testing
    Path("./Smart Reports/Test Report 1").mkdir(parents=True, exist_ok=True)
    Path("./Smart Reports/Test Report 1/Test_Report_One.html").touch()
    Path("./Smart Reports/Subfolder/Test Report 2").mkdir(parents=True, exist_ok=True)
    Path("./Smart Reports/Subfolder/Test Report 2/Another_Test_Report.html").touch()

    reports_dir = "./Smart Reports"
    found_reports = find_reports(reports_dir)
    if found_reports:
        print(f"Found reports in '{reports_dir}':")
        for report in found_reports:
            print(f"  Name: {report['name']}, Path: {report['path']}")
    else:
        print(f"No reports found in '{reports_dir}' or directory does not exist.")

    # Clean up dummy files
    Path("./Smart Reports/Test Report 1/Test_Report_One.html").unlink()
    Path("./Smart Reports/Test Report 1").rmdir()
    Path("./Smart Reports/Subfolder/Test Report 2/Another_Test_Report.html").unlink()
    Path("./Smart Reports/Subfolder/Test Report 2").rmdir()
    Path("./Smart Reports/Subfolder").rmdir()
    # Path("./Smart Reports").rmdir() # Only if it was created by this script
