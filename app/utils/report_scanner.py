from pathlib import Path


def find_reports(directory: str):
    """
    Scans the given directory recursively for HTML files.

    Args:
        directory: The absolute path to the directory to scan.

    Returns:
        A list of dictionaries, where each dictionary has:
            'name': The display name of the report (from filename).
            'path': The path to the HTML file relative to the scanned 'directory'.
    """
    report_files = []
    base_path = Path(directory)
    if not base_path.is_dir():
        return []

    for html_file in base_path.rglob('*.html'):
        report_relative_path = html_file.relative_to(base_path)
        report_files.append({
            'name': html_file.stem.replace('_', ' ').replace('-', ' '),
            'path': str(report_relative_path)
        })
    return report_files
