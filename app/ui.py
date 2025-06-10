from urllib.parse import quote

import gradio as gr

from research_portal.app.utils import thumbnails, report_scanner, config


def create_thumbnail_html(report):
    """Creates a thumbnail card for a single report."""
    thumbnail_b64 = thumbnails.get_thumbnail_for_report(report['path'])
    encoded_path = quote(report['path'])
    static_url = f"/reports/{encoded_path}"

    if thumbnail_b64:
        thumbnail_content = f'<div class="thumbnail-image"><img src="data:image/png;base64,{thumbnail_b64}" alt="Preview" /></div>'
    else:
        thumbnail_content = '<div class="thumbnail-fallback"><div class="fallback-icon">📊</div><div class="fallback-text">HTML Report</div></div>'

    return f'''
    <div class="report-card">
        <div class="card-thumbnail">{thumbnail_content}</div>
        <div class="card-content">
            <h3 class="report-title">{report['name']}</h3>
            <a href="{static_url}" target="_blank" rel="noopener noreferrer" class="view-button">
                View Report
            </a>
        </div>
    </div>
    '''


def create_report_gallery_html(reports):
    """Creates the complete HTML for the gallery of report thumbnails."""
    if not reports:
        return f'''
        <div class="no-reports-container">
            <div class="no-reports-icon">📂</div>
            <h3>No Reports Found</h3>
            <p>Place your HTML reports in the <code>{config.REPORTS_BASE_DIR.name}</code> directory.</p>
        </div>
        '''

    print(f"Generating thumbnails for {len(reports)} report(s)...")
    cards_html = "".join([create_thumbnail_html(report) for report in reports])
    return f'<div class="reports-gallery">{cards_html}</div>'


def create_gradio_interface():
    """Creates the main Gradio interface for the gallery."""
    reports = report_scanner.find_reports(str(config.REPORTS_BASE_DIR))

    with open(config.CSS_PATH, "r") as f:
        css = f.read()

    with gr.Blocks(css=css, theme=gr.themes.Base()) as demo:
        # Custom HTML for a cleaner header
        logo_svg = '''
        <svg width="43.5" height="34.5" viewBox="0 0 87 69" fill="none" xmlns="http://www.w3.org/2000/svg" class="logo">
            <path d="M68.069 26C68.069 26 63.1511 26 60 26H87H78.931C78.931 26 78.931 36.0563 78.931 42.5C78.931 48.9437 78.931 61 78.931 61C76.3448 64.3735 70.6552 66.3735 68.069 63C68.069 63 68.069 50.3342 68.069 43.5C68.069 36.6658 68.069 26 68.069 26Z" stroke="#174052" stroke-width="8"></path>
            <path d="M32 50C28.5 46.5 13 50 13 50C13 50 23.2753 39.42 30.5 32C37.7247 24.58 48 12 48 12V42M48 54C48 49.3137 48 42 48 42M48 42H44" stroke="#174052" stroke-width="8"></path>
            <path d="M73.5 2C73.5 3.95262 69.5 10 73.5 14" stroke="#008080" stroke-width="12"></path>
        </svg>
        '''
        header_html = f'''
        <div class="app-header">
            {logo_svg}
            <h1>Smart Report Portal</h1>
        </div>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&display=swap" rel="stylesheet">
        '''
        gr.HTML(header_html)

        # Display the gallery
        gallery_html = create_report_gallery_html(reports)
        gr.HTML(gallery_html)

    return demo
