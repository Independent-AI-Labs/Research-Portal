import uvicorn

from research_portal.app import ui, server
from research_portal.app.utils.config import REPORTS_BASE_DIR
from research_portal.app.utils.thumbnails import PLAYWRIGHT_AVAILABLE


def main():
    """Main function to set up and run the application."""
    print("🚀 Launching Smart Report Portal...")
    print(f"📁 Serving reports from: {REPORTS_BASE_DIR}")

    if PLAYWRIGHT_AVAILABLE:
        print("✅ Playwright available - will generate high-quality thumbnails.")
    else:
        print("⚠️ Playwright not installed. Using fallback thumbnails.")
        print("   For better previews, run: pip install playwright && playwright install chromium")

    if not REPORTS_BASE_DIR.is_dir():
        print(f"❌ Directory not found. Please create it or set the SMART_REPORTS_DIR_PATH environment variable.")

    # 1. Create the Gradio interface
    gradio_interface = ui.create_gradio_interface()

    # 2. Create the FastAPI app and mount the Gradio interface
    app = server.create_fastapi_app(gradio_interface)

    # 3. Launch with Uvicorn
    print("\n" + "=" * 50)
    print(f"🔗 Portal available at: http://127.0.0.1:7860")
    print("=" * 50 + "\n")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=7860,
        log_level="info"
    )


if __name__ == "__main__":
    main()
