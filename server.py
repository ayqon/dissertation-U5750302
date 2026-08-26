"""
FastAPI Server for Renbee Proposal Extractor Web Application
Serves the modern bespoke HTML/CSS/JS frontend and provides the extraction API endpoint.
"""

import os
import tempfile
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from extractor_engine import extract_proposal

app = FastAPI(title="Renbee Proposal Extractor API")

# Enable CORS for local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure static folder exists
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

# Mount static assets
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def read_index():
    return FileResponse(os.path.join(static_dir, "index.html"))

@app.post("/api/extract")
async def handle_extraction(
    file: UploadFile = File(...),
    model_choice: str = Form("gemini"),
    api_key: str = Form(""),
    epc_key: str = Form(""),
    ch_key: str = Form("")
):
    try:
        # Save uploaded PDF to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        # Execute extraction pipeline
        result_data = extract_proposal(
            pdf_source=tmp_path,
            model_choice=model_choice,
            api_key=api_key if api_key else None,
            epc_key=epc_key if epc_key else None,
            ch_key=ch_key if ch_key else None
        )

        return JSONResponse(content=result_data)

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
    finally:
        try:
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass

if __name__ == "__main__":
    import uvicorn
    print("Starting Renbee Proposal Extractor on http://localhost:8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
