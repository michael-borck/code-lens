from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile
from lens_contract import add_contract_routes, add_cors, upload_tempfile

from .manifest import MANIFEST
from .models import CodeAnalysis
from .pipeline import CodeAnalyser

app = FastAPI(title="code-analyser", version=MANIFEST["version"])

# GET /health and GET /manifest (the family contract, via lens-contract).
add_contract_routes(app, MANIFEST)
# CORS — env-driven: CODE_ANALYSER_MODE=desktop (Electron) or CODE_ANALYSER_ALLOWED_ORIGINS.
add_cors(app, env_prefix="CODE_ANALYSER")

_analyser = CodeAnalyser()


@app.post("/analyse", response_model=CodeAnalysis)
async def analyse(file: UploadFile = File(...)) -> CodeAnalysis:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="Empty file")

    with upload_tempfile(content, file.filename) as tmp_path:
        try:
            return _analyser.analyse(tmp_path)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e
