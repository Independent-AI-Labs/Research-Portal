import asyncio
import base64

from .config import REPORTS_BASE_DIR

# Try to import screenshot dependencies
try:
    from playwright.async_api import async_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# Cache for thumbnails
thumbnail_cache = {}


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

            file_url = f"file://{html_file_path.resolve()}"
            await page.goto(file_url, wait_until='networkidle', timeout=10000)

            screenshot_bytes = await page.screenshot(
                type='png',
                full_page=False,
                clip={'x': 0, 'y': 0, 'width': width, 'height': height}
            )
            await browser.close()
            return screenshot_bytes
    except Exception as e:
        print(f"Error generating screenshot for {html_file_path}: {e}")
        return None


def get_thumbnail_for_report(report_path):
    """
    Generate or retrieve a cached thumbnail for a report.
    """
    cache_key = str(report_path)
    if cache_key in thumbnail_cache:
        return thumbnail_cache[cache_key]

    full_path = REPORTS_BASE_DIR / report_path
    if not full_path.exists():
        return None

    if PLAYWRIGHT_AVAILABLE:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            screenshot_bytes = loop.run_until_complete(generate_screenshot(full_path))
            loop.close()

            if screenshot_bytes:
                base64_image = base64.b64encode(screenshot_bytes).decode('utf-8')
                thumbnail_cache[cache_key] = base64_image
                return base64_image
        except Exception as e:
            print(f"Error in screenshot generation thread: {e}")

    return None
