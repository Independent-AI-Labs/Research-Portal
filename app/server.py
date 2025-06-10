import json

import gradio as gr
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse

from research_portal.app.utils.config import REPORTS_BASE_DIR


def create_fastapi_app(gradio_demo: gr.Blocks):
    """Creates the FastAPI app, defines static routes, and mounts the Gradio UI."""
    fastapi_app = FastAPI(title="Smart Reports Gallery")

    if REPORTS_BASE_DIR.is_dir():
        print(f"✅ Reports directory found. Setting up static routes for: {REPORTS_BASE_DIR}")

        @fastapi_app.get("/reports/{file_path:path}")
        async def serve_report_html(file_path: str):
            """Serves the main HTML file for a report."""
            try:
                full_path = REPORTS_BASE_DIR / file_path
                if not str(full_path.resolve()).startswith(str(REPORTS_BASE_DIR.resolve())):
                    raise HTTPException(status_code=403, detail="Access denied")
                if not full_path.exists() or not file_path.lower().endswith('.html'):
                    raise HTTPException(status_code=404, detail="HTML Report not found")

                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return HTMLResponse(content=content)
            except HTTPException:
                raise
            except Exception as e:
                print(f"Error serving report {file_path}: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")

        @fastapi_app.get("/report-resource/{resource_path:path}")
        async def serve_report_resource(resource_path: str):
            """Serves supplementary resources for reports (e.g., audio, data)."""
            try:
                full_resource_path = REPORTS_BASE_DIR / resource_path
                if not str(full_resource_path.resolve()).startswith(str(REPORTS_BASE_DIR.resolve())):
                    raise HTTPException(status_code=403, detail="Access denied")
                if not full_resource_path.exists():
                    raise HTTPException(status_code=404, detail="Resource not found")

                # Special handling for different file types can go here if needed
                if resource_path.endswith('.linkres'):
                    with open(full_resource_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    return JSONResponse(content=data)

                return FileResponse(full_resource_path)
            except HTTPException:
                raise
            except Exception as e:
                print(f"Error serving resource {resource_path}: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
    else:
        print(f"⚠️ Reports directory not found: {REPORTS_BASE_DIR}")

    # Mount the Gradio app as the root
    app = gr.mount_gradio_app(fastapi_app, gradio_demo, path="/")
    return app
