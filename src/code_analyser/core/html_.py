from __future__ import annotations
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

import html5lib
import httpx

from ..models import ExternalResource, HTMLMetrics, W3CError

_XHTML = "http://www.w3.org/1999/xhtml"

_SEMANTIC = {
    "header", "nav", "main", "footer", "article", "section", "aside",
    "figure", "figcaption", "time", "mark", "details", "summary", "address",
}

_CDN_HOSTS = {
    "cdnjs.cloudflare.com", "unpkg.com", "cdn.jsdelivr.net",
    "ajax.googleapis.com", "cdn.tailwindcss.com",
    "stackpath.bootstrapcdn.com", "maxcdn.bootstrapcdn.com", "code.jquery.com",
}

_LIBRARY_PATTERNS = {
    "jquery": re.compile(r"jquery", re.I),
    "bootstrap": re.compile(r"bootstrap", re.I),
    "react": re.compile(r"react(?:\.min)?\.js", re.I),
    "vue": re.compile(r"vue(?:\.min)?\.js", re.I),
    "angular": re.compile(r"angular", re.I),
    "tailwind": re.compile(r"tailwind", re.I),
    "font-awesome": re.compile(r"font.awesome", re.I),
}

_JS_FRAMEWORK_PATTERNS = [
    (re.compile(r"React\.createElement|from\s+['\"]react['\"]"), "react"),
    (re.compile(r"new\s+Vue\s*\(|from\s+['\"]vue['\"]"), "vue"),
    (re.compile(r"ng-app|ng-controller"), "angular"),
    (re.compile(r"\$\s*\(|jQuery\s*\("), "jquery"),
]

_AMBIGUOUS_LINK_TEXT = {"click here", "here", "read more", "more", "link", "this"}


def _detect_library(url: str) -> str | None:
    for lib, pat in _LIBRARY_PATTERNS.items():
        if pat.search(url):
            return lib
    return None


def _is_cdn(url: str) -> bool:
    try:
        host = urlparse(url).netloc
        return host in _CDN_HOSTS
    except Exception:
        return False


def _w3c_validate(source: str, timeout: float) -> list[W3CError]:
    resp = httpx.post(
        "https://validator.w3.org/nu/",
        params={"out": "json"},
        content=source.encode(),
        headers={"Content-Type": "text/html; charset=utf-8"},
        timeout=timeout,
    )
    resp.raise_for_status()
    return [
        W3CError(
            type=m.get("type", "error"),
            line=m.get("lastLine", 0),
            message=m.get("message", ""),
        )
        for m in resp.json().get("messages", [])
        if m.get("type") in ("error", "warning")
    ]


def analyse_html(source: str, *, timeout: float = 0.5) -> HTMLMetrics:
    w3c_errors: list[W3CError] = []
    validator = "local"
    try:
        w3c_errors = _w3c_validate(source, timeout)
        validator = "w3c"
    except Exception:
        pass

    parser = html5lib.HTMLParser(tree=html5lib.treebuilders.getTreeBuilder("etree"))
    tree = parser.parse(source)
    parse_errors = parser.errors
    syntax_valid = len(parse_errors) == 0

    divs = 0
    spans = 0
    semantic_found: dict[str, int] = {}
    inline_scripts = 0
    inline_styles = 0
    event_handlers = 0
    comments = 0
    imgs: list[ET.Element] = []
    inputs: list[ET.Element] = []
    labels: list[ET.Element] = []
    links: list[ET.Element] = []
    headings: list[int] = []
    aria_attrs = 0
    external_scripts: list[ExternalResource] = []
    external_stylesheets: list[ExternalResource] = []
    frameworks: set[str] = set()

    has_doctype = "<!DOCTYPE" in source[:200].upper()
    has_lang = False
    has_title = False

    for el in tree.iter():
        tag = el.tag
        if not isinstance(tag, str):
            continue
        local = tag.replace(f"{{{_XHTML}}}", "") if tag.startswith("{") else tag

        if local == "html":
            has_lang = bool(el.get("lang") or el.get(f"{{{_XHTML}}}lang"))
        elif local == "title":
            has_title = bool(el.text and el.text.strip())
        elif local == "div":
            divs += 1
        elif local == "span":
            spans += 1
        elif local in _SEMANTIC:
            semantic_found[local] = semantic_found.get(local, 0) + 1
        elif local == "script":
            src = el.get("src")
            if src:
                is_cdn = _is_cdn(src)
                lib = _detect_library(src)
                external_scripts.append(ExternalResource(src=src, is_cdn=is_cdn, library=lib))
                if lib:
                    frameworks.add(lib)
            else:
                inline_scripts += 1
        elif local == "link":
            rel = el.get("rel", "")
            if "stylesheet" in rel:
                href = el.get("href", "")
                is_cdn = _is_cdn(href)
                lib = _detect_library(href)
                external_stylesheets.append(ExternalResource(src=href, is_cdn=is_cdn, library=lib))
                if lib:
                    frameworks.add(lib)
        elif local == "img":
            imgs.append(el)
        elif local == "input":
            if el.get("type", "text").lower() != "hidden":
                inputs.append(el)
        elif local == "label":
            labels.append(el)
        elif local == "a":
            links.append(el)
        elif local in ("h1", "h2", "h3", "h4", "h5", "h6"):
            headings.append(int(local[1]))
        elif local == "style":
            inline_styles += 1

        for attr in el.attrib:
            local_attr = attr.split("}")[-1] if "}" in attr else attr
            if local_attr.startswith("on"):
                event_handlers += 1
            if local_attr.startswith("aria-"):
                aria_attrs += 1
            if local_attr == "style":
                inline_styles += 1

    # Framework fingerprinting via code patterns in the full source
    for pat, name in _JS_FRAMEWORK_PATTERNS:
        if pat.search(source):
            frameworks.add(name)

    # Accessibility signals
    img_alt_coverage = (
        sum(1 for img in imgs if img.get("alt", "").strip()) / len(imgs)
        if imgs else 1.0
    )
    label_fors = {lbl.get("for") for lbl in labels if lbl.get("for")}
    input_ids = {inp.get("id") for inp in inputs if inp.get("id")}
    form_label_coverage = (
        sum(1 for inp_id in input_ids if inp_id in label_fors) / len(inputs)
        if inputs else 1.0
    )

    ambiguous = sum(
        1 for a in links
        if (a.text or "").strip().lower() in _AMBIGUOUS_LINK_TEXT
    )

    heading_valid = _check_heading_hierarchy(headings)

    semantic_count = sum(semantic_found.values())
    semantic_used = sorted(semantic_found.keys())
    cdn_count = sum(1 for r in external_scripts + external_stylesheets if r.is_cdn)

    if divs == 0 and semantic_count == 0:
        ratio = None
    elif divs == 0:
        ratio = 0.0
    else:
        ratio = divs / (divs + semantic_count)

    return HTMLMetrics(
        syntax_valid=syntax_valid,
        parse_error_count=len(parse_errors),
        validator=validator,
        w3c_errors=w3c_errors,
        has_doctype=has_doctype,
        semantic_elements_used=semantic_used,
        semantic_element_count=semantic_count,
        div_count=divs,
        span_count=spans,
        div_to_semantic_ratio=ratio,
        inline_script_count=inline_scripts,
        inline_style_count=inline_styles,
        inline_event_handler_count=event_handlers,
        comment_count=comments,
        external_scripts=external_scripts,
        external_stylesheets=external_stylesheets,
        cdn_count=cdn_count,
        frameworks_detected=sorted(frameworks),
        img_alt_coverage=img_alt_coverage,
        form_label_coverage=form_label_coverage,
        has_lang_attr=has_lang,
        has_title=has_title,
        heading_hierarchy_valid=heading_valid,
        aria_attribute_count=aria_attrs,
        ambiguous_link_count=ambiguous,
    )


def _check_heading_hierarchy(levels: list[int]) -> bool:
    if not levels:
        return True
    if levels.count(1) > 1:
        return False
    for i in range(1, len(levels)):
        if levels[i] > levels[i - 1] + 1:
            return False
    return True
