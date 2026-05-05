from pathlib import Path

_EXT_MAP: dict[str, str] = {
    ".py": "python",
    ".ipynb": "notebook",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".sql": "sql",
    ".zip": "zip",
}


def detect_language(path: Path) -> str | None:
    """Return language string for path, or None if unsupported."""
    return _EXT_MAP.get(path.suffix.lower())
