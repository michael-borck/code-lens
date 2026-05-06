from __future__ import annotations
import zipfile
from pathlib import Path

from .detect import detect_language
from .models import (
    CodeAnalysis, CrossFileSignals, FileAnalysis,
    FileLLMSignals, TopLevelLLMSignals,
)
from .core.python_ import analyse_python
from .core.notebook_ import analyse_notebook
from .core.html_ import analyse_html
from .core.css_ import analyse_css
from .core.javascript_ import analyse_javascript
from .core.typescript_ import analyse_typescript
from .core.sql_ import analyse_sql


class CodeAnalyser:
    def analyse(self, path: Path, *, llm: bool = False) -> CodeAnalysis:
        lang = detect_language(path)
        if lang is None:
            raise ValueError(f"Unsupported file type: {path.suffix}")

        if lang == "zip":
            pairs = _unpack_zip(path)
        else:
            pairs = [(path.name, path.read_bytes())]

        files: list[FileAnalysis] = []
        unrecognised: list[str] = []
        has_package_json = False
        all_frameworks: set[str] = set()

        for filename, content in pairs:
            if filename.lower() == "package.json":
                has_package_json = True
                unrecognised.append(filename)
                continue

            file_lang = detect_language(Path(filename))
            if file_lang is None or file_lang == "zip":
                unrecognised.append(filename)
                continue

            metrics = _dispatch(filename, file_lang, content)
            files.append(FileAnalysis(filename=filename, language=file_lang, metrics=metrics))

            if metrics is not None and hasattr(metrics, "frameworks_detected"):
                all_frameworks.update(metrics.frameworks_detected)

        llm_file_signals: list[FileLLMSignals | None] = [None] * len(files)
        llm_top: TopLevelLLMSignals | None = None

        if llm:
            try:
                from .llm import analyse_llm
                pairs_map = dict(pairs)
                text_pairs = [
                    (f.filename, _decode(pairs_map[f.filename]))
                    for f in files
                    if f.filename in pairs_map
                ]
                llm_file_signals, llm_top = analyse_llm(text_pairs)
            except Exception:
                pass

        for i, f in enumerate(files):
            f.llm_signals = llm_file_signals[i] if i < len(llm_file_signals) else None

        langs_detected = sorted({f.language for f in files})

        cross = CrossFileSignals(
            file_count=len(files),
            languages_detected=langs_detected,
            import_graph={},
            unrecognised_files=unrecognised,
            has_package_json=has_package_json,
            frameworks_detected=sorted(all_frameworks),
        )

        return CodeAnalysis(
            input=path.name,
            file_count=len(files),
            languages_detected=langs_detected,
            files=files,
            cross_file=cross,
            llm_signals=llm_top,
        )


def _decode(content: bytes) -> str:
    return content.decode("utf-8", errors="replace")


def _unpack_zip(path: Path) -> list[tuple[str, bytes]]:
    pairs: list[tuple[str, bytes]] = []
    with zipfile.ZipFile(path) as zf:
        for name in zf.namelist():
            if name.endswith("/"):
                continue
            pairs.append((Path(name).name, zf.read(name)))
    return pairs


def _dispatch(filename: str, lang: str, content: bytes):
    src = _decode(content)
    try:
        if lang == "python":
            return analyse_python(src)
        elif lang == "notebook":
            return analyse_notebook(content)
        elif lang == "html":
            return analyse_html(src)
        elif lang == "css":
            return analyse_css(src)
        elif lang == "javascript":
            return analyse_javascript(src, jsx=filename.endswith(".jsx"))
        elif lang == "typescript":
            return analyse_typescript(src, tsx=filename.endswith(".tsx"))
        elif lang == "sql":
            return analyse_sql(src)
    except Exception:
        return None
    return None
