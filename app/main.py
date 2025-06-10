import asyncio
import base64
import os
from pathlib import Path
from urllib.parse import quote

import gradio as gr
# FastAPI imports for proper file serving
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from research_portal.app.utils.report_scanner import find_reports

# Try to import screenshot dependencies
try:
    from playwright.async_api import async_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    print("Warning: playwright not installed. Using fallback thumbnails.")
    print("Install with: pip install playwright && playwright install chromium")
    PLAYWRIGHT_AVAILABLE = False

# Configuration for the Smart Reports directory
REPORTS_DIR_CONFIG_KEY = "SMART_REPORTS_DIR_PATH"
DEFAULT_REPORTS_DIR = "./Smart Reports"

# Determine the actual reports directory path
reports_base_dir_abs = Path(os.getenv(REPORTS_DIR_CONFIG_KEY, DEFAULT_REPORTS_DIR)).resolve()

# Cache for thumbnails
thumbnail_cache = {}


def get_report_data():
    """
    Scans for reports and returns structured data for display.
    """
    if not reports_base_dir_abs.is_dir():
        print(f"Warning: Reports directory '{reports_base_dir_abs}' not found.")
        return []

    return find_reports(str(reports_base_dir_abs))


async def generate_screenshot(html_file_path, width=1200, height=800):
    """
    Generate a screenshot of an HTML file using Playwright.
    """
    if not PLAYWRIGHT_AVAILABLE:
        return None

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={'width': width, 'height': height})

            # Load the HTML file
            file_url = f"file://{html_file_path.resolve()}"
            await page.goto(file_url, wait_until='networkidle', timeout=10000)

            # Take screenshot
            screenshot_bytes = await page.screenshot(
                type='png',
                full_page=False,  # Just the viewport
                clip={'x': 0, 'y': 0, 'width': width, 'height': height}
            )

            await browser.close()
            return screenshot_bytes

    except Exception as e:
        print(f"Error generating screenshot for {html_file_path}: {e}")
        return None


def generate_thumbnail_for_report(report_path, report_name):
    """
    Generate a thumbnail for a report, with caching.
    """
    cache_key = str(report_path)
    if cache_key in thumbnail_cache:
        return thumbnail_cache[cache_key]

    full_path = reports_base_dir_abs / report_path

    if not full_path.exists():
        return None

    # Generate screenshot if playwright is available
    if PLAYWRIGHT_AVAILABLE:
        try:
            # Run async function in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            screenshot_bytes = loop.run_until_complete(generate_screenshot(full_path))
            loop.close()

            if screenshot_bytes:
                # Convert to base64 for embedding
                base64_image = base64.b64encode(screenshot_bytes).decode('utf-8')
                thumbnail_cache[cache_key] = base64_image
                return base64_image
        except Exception as e:
            print(f"Error in screenshot generation: {e}")

    return None


def create_thumbnail_html(report_path, report_name, index):
    """
    Creates a thumbnail card for a report.
    """
    # Generate or get cached thumbnail
    thumbnail_b64 = generate_thumbnail_for_report(report_path, report_name)

    # Create thumbnail content
    if thumbnail_b64:
        thumbnail_content = f'''
        <div class="thumbnail-image">
            <img src="data:image/png;base64,{thumbnail_b64}" alt="Report preview" />
        </div>
        '''
    else:
        # Fallback for when screenshot isn't available
        thumbnail_content = '''
        <div class="thumbnail-fallback">
            <div class="fallback-icon">📊</div>
            <div class="fallback-text">HTML Report</div>
        </div>
        '''

    # Create URL for FastAPI static file serving
    # Use URL-encoded path for proper handling of spaces and special characters
    encoded_path = quote(report_path)
    static_url = f"/reports/{encoded_path}"

    thumbnail_html = f'''
    <div class="report-card" data-report-path="{report_path}">
        <div class="card-header">
            <h3 class="report-title">{report_name}</h3>
            <div class="report-path">{report_path}</div>
        </div>
        <div class="card-thumbnail">
            {thumbnail_content}
        </div>
        <div class="card-footer">
            <a href="{static_url}" target="_blank" rel="noopener noreferrer" class="view-button primary link-button">
                View Report (New Tab)
            </a>
            <button class="view-button secondary" onclick="window.location.href='{static_url}'">
                View in Current Tab
            </button>
        </div>
    </div>
    '''

    return thumbnail_html


def create_report_gallery_html(reports):
    """
    Creates HTML for a gallery of report thumbnails with proper Gradio theming.
    """
    if not reports:
        return '''
        <div class="no-reports">
            <div class="no-reports-icon">📂</div>
            <h3>No reports found</h3>
            <p>Please ensure HTML reports exist in the configured directory.</p>
        </div>
        '''

    # Generate thumbnails for all reports
    print("Generating thumbnails...")
    thumbnail_htmls = []
    for i, report in enumerate(reports):
        print(f"Processing {i + 1}/{len(reports)}: {report['name']}")
        thumbnail_html = create_thumbnail_html(report['path'], report['name'], i)
        thumbnail_htmls.append(thumbnail_html)

    gallery_html = f'''
    <style>
        /* Gallery Styles - Compatible with Gradio themes */
        .reports-gallery {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 1.5rem;
            padding: 1rem 0;
        }}

        .report-card {{
            background: var(--background-fill-primary, #ffffff);
            border: 1px solid var(--border-color-primary, #e5e7eb);
            border-radius: 8px;
            overflow: hidden;
            transition: all 0.2s ease;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}

        .report-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            border-color: var(--color-accent, #3b82f6);
        }}

        .card-header {{
            padding: 1rem;
            border-bottom: 1px solid var(--border-color-secondary, #f3f4f6);
        }}

        .report-title {{
            margin: 0 0 0.5rem 0;
            font-size: 1rem;
            font-weight: 600;
            color: var(--body-text-color, #374151);
            line-height: 1.4;
        }}

        .report-path {{
            font-size: 0.75rem;
            color: var(--body-text-color-subdued, #6b7280);
            font-family: ui-monospace, monospace;
            background: var(--background-fill-secondary, #f9fafb);
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            word-break: break-all;
        }}

        .card-thumbnail {{
            height: 160px;
            overflow: hidden;
            background: var(--background-fill-secondary, #f9fafb);
        }}

        .thumbnail-image {{
            width: 100%;
            height: 100%;
        }}

        .thumbnail-image img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            object-position: top left;
        }}

        .thumbnail-fallback {{
            width: 100%;
            height: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            color: var(--body-text-color-subdued, #6b7280);
        }}

        .fallback-icon {{
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }}

        .fallback-text {{
            font-size: 0.875rem;
            font-weight: 500;
        }}

        .card-footer {{
            padding: 1rem;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }}

        .view-button {{
            width: 100%;
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 6px;
            font-size: 0.875rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
            text-decoration: none;
            display: inline-block;
            text-align: center;
            box-sizing: border-box;
        }}

        .link-button {{
            display: block;
        }}

        .view-button.primary {{
            background: var(--button-primary-background-fill, #3b82f6);
            color: var(--button-primary-text-color, #ffffff);
        }}

        .view-button.primary:hover {{
            background: var(--button-primary-background-fill-hover, #2563eb);
            transform: translateY(-1px);
        }}

        .view-button.secondary {{
            background: var(--button-secondary-background-fill, #f3f4f6);
            color: var(--button-secondary-text-color, #374151);
            border: 1px solid var(--border-color-primary, #e5e7eb);
        }}

        .view-button.secondary:hover {{
            background: var(--button-secondary-background-fill-hover, #e5e7eb);
            transform: translateY(-1px);
        }}

        .gallery-header {{
            text-align: center;
            margin-bottom: 2rem;
            padding: 1.5rem;
            background: var(--background-fill-secondary, #f9fafb);
            border-radius: 8px;
            border-left: 4px solid var(--color-accent, #3b82f6);
        }}

        .gallery-header h2 {{
            margin: 0 0 0.5rem 0;
            color: var(--body-text-color, #374151);
            font-size: 1.5rem;
        }}

        .gallery-header p {{
            margin: 0;
            color: var(--body-text-color-subdued, #6b7280);
        }}

        .no-reports {{
            text-align: center;
            padding: 3rem;
            color: var(--body-text-color-subdued, #6b7280);
        }}

        .no-reports-icon {{
            font-size: 3rem;
            margin-bottom: 1rem;
        }}

        .no-reports h3 {{
            color: var(--body-text-color, #374151);
            margin-bottom: 0.5rem;
        }}
    </style>

    <div class="gallery-header">
        <h2>📊 Available Reports ({len(reports)})</h2>
        <p>Click to view reports - served via FastAPI static files</p>
    </div>

    <div class="reports-gallery">
        {"".join(thumbnail_htmls)}
    </div>
    '''

    return gallery_html


def create_gradio_interface():
    """
    Creates the Gradio interface for the Smart Reports Gallery.
    """
    # Use a clean, accessible theme
    theme = gr.themes.Default(
        primary_hue="blue",
        secondary_hue="gray",
        neutral_hue="gray",
    ).set(
        body_background_fill="*neutral_50",
        block_background_fill="white",
    )

    with gr.Blocks(
            title="Smart Reports Gallery",
            theme=theme,
            css="""
        .gradio-container {
            max-width: 1200px !important;
            margin: 0 auto !important;
        }
        """
    ) as demo:
        gr.Markdown("# 📊 Smart Reports Gallery")
        gr.Markdown("Discover and view interactive HTML reports from your Smart Reports directory.")

        # Get report data
        reports = get_report_data()

        if not reports:
            with gr.Column():
                gr.Markdown("## ⚠️ No reports found")
                gr.Markdown(f"**Configured directory:** `{reports_base_dir_abs}`")
                gr.Markdown("""
                **To add reports:**
                1. Create the Smart Reports directory if it doesn't exist
                2. Add your HTML files to the directory (can be in subdirectories)
                3. Restart this application

                **Example structure:**
                ```
                Smart Reports/
                ├── Q1_Report/
                │   └── quarterly_summary.html
                ├── Sales_Analysis/
                │   └── sales_dashboard.html
                └── monthly_report.html
                ```
                """)
        else:
            # Display directory info
            gr.Markdown(f"**📁 Reports directory:** `{reports_base_dir_abs}`")

            # Custom HTML gallery with thumbnails
            gallery_html = create_report_gallery_html(reports)
            gr.HTML(gallery_html)

            # Instructions
            gr.Markdown("""
            ### 💡 Tips:
            - Click **"View Report (New Tab)"** to open the full report in a new tab
            - Click **"View in Current Tab"** to navigate to the report in the same window
            - Reports are served as static files via FastAPI - secure and efficient
            - Thumbnails show actual screenshots of your reports (when available)
            - Use **Ctrl+click** or **middle-click** for additional browser options
            """)

    return demo


def create_fastapi_app():
    """
    Creates the main FastAPI application with static file serving.
    """
    # Create FastAPI app
    fastapi_app = FastAPI(title="Smart Reports Gallery")

    # Mount static files for reports if directory exists
    if reports_base_dir_abs.is_dir():
        print(f"📂 Mounting static files from: {reports_base_dir_abs}")
        fastapi_app.mount(
            "/reports",
            StaticFiles(directory=str(reports_base_dir_abs)),
            name="reports"
        )
        print("✅ Static file serving configured successfully")
    else:
        print(f"⚠️  Reports directory not found: {reports_base_dir_abs}")

    # Create Gradio interface
    gradio_demo = create_gradio_interface()

    # Mount Gradio app to FastAPI
    fastapi_app = gr.mount_gradio_app(fastapi_app, gradio_demo, path="/")

    return fastapi_app


if __name__ == "__main__":
    print(f"🚀 Starting Smart Reports Gallery")
    print(f"📁 Reports directory: {reports_base_dir_abs}")

    if PLAYWRIGHT_AVAILABLE:
        print("✅ Playwright available - will generate screenshot thumbnails")
    else:
        print("⚠️  Playwright not available - using fallback thumbnails")
        print("   Install with: pip install playwright && playwright install chromium")

    if not reports_base_dir_abs.is_dir():
        print(f"⚠️  Directory does not exist: {reports_base_dir_abs}")
        print(f"   Please create this directory or set the '{REPORTS_DIR_CONFIG_KEY}' environment variable.")
    else:
        reports = get_report_data()
        print(f"📊 Found {len(reports)} HTML report(s)")
        for i, report in enumerate(reports[:5], 1):
            print(f"   {i:2d}. {report['name']}")
            print(f"       Path: {report['path']}")
            print(f"       URL: /reports/{quote(report['path'])}")
        if len(reports) > 5:
            print(f"   ... and {len(reports) - 5} more")

    print("\n" + "=" * 50)

    # Create FastAPI app with mounted Gradio interface
    app = create_fastapi_app()

    # Launch using uvicorn
    print(f"🚀 Launching Smart Reports Gallery on http://127.0.0.1:7860")
    print(f"🔗 Reports accessible at: http://127.0.0.1:7860/reports/<report_path>")

    import uvicorn

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=7860,
        log_level="info"
    )
