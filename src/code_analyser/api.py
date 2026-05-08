from __future__ import annotations
import tempfile
import time
from pathlib import Path

from importlib.metadata import version
from fastapi import FastAPI, File, HTTPException, UploadFile

from .models import CodeAnalysis
from .pipeline import CodeAnalyser

_start_time = time.time()

app = FastAPI(title="code-analyser", version=version("code-analyser"))

_analyser = CodeAnalyser()


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "uptime": round(time.time() - _start_time, 1),
        "version": version("code-analyser"),
    }


@app.post("/analyse", response_model=CodeAnalysis)
async def analyse(file: UploadFile = File(...)) -> CodeAnalysis:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="Empty file")

    suffix = Path(file.filename or "upload.py").suffix or ".py"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write(content)

    try:
        result = _analyser.analyse(tmp_path)
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        tmp_path.unlink(missing_ok=True)
