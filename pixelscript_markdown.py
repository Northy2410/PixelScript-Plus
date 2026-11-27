import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit


_INLINE_PATTERN = re.compile(
    r"(?P<code>`[^`]+`)"
    r"|(?P<strong>\*\*.+?\*\*|__.+?__)"
    r"|(?P<strike>~~.+?~~)"
    r"|(?P<em>\*[^*\n]+\*|_[^_\n]+_)"
    r"|(?P<link>\[([^\]]+)\]\(([^)\s]+)(?:\s+\"([^\"]*)\")?\))"
)
_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")


def extract_headings(source):
    headings = []
    for line_number, line in enumerate(source.splitlines(), start=1):
        match = _HEADING_PATTERN.match(line)
        if match:
            headings.append((line_number, match.group(2), len(match.group(1))))
    return headings


def _inline_to_html(text):
    pieces = []
    previous_end = 0
    for match in _INLINE_PATTERN.finditer(text):
        pieces.append(html.escape(text[previous_end:match.start()]))
        token = match.group(0)
        if match.group("code") is not None:
            rendered = f"<code>{html.escape(token[1:-1])}</code>"
        elif match.group("strong") is not None:
            rendered = f"<strong>{html.escape(token[2:-2])}</strong>"
        elif match.group("strike") is not None:
            rendered = f"<del>{html.escape(token[2:-2])}</del>"
        elif match.group("em") is not None:
            rendered = f"<em>{html.escape(token[1:-1])}</em>"
        else:
            label, url, title = match.group(6), match.group(7), match.group(8)
            scheme = urlsplit(url).scheme.lower()
            if scheme in {"http", "https", "mailto"} or url.startswith("#"):
                title_attr = f' title="{html.escape(title, quote=True)}"' if title else ""
                rendered = (
                    f'<a href="{html.escape(url, quote=True)}"{title_attr}>'
                    f"{html.escape(label)}</a>"
                )
            else:
                rendered = html.escape(label)
        pieces.append(rendered)
        previous_end = match.end()
    pieces.append(html.escape(text[previous_end:]))
    return "".join(pieces)


def markdown_to_html(source, title="Markdown Preview"):
    output = []
    paragraph = []
    list_tag = None
    in_code = False
    code_lines = []

    def close_list():
        nonlocal list_tag
        if list_tag:
            output.append(f"</{list_tag}>")
            list_tag = None

    def flush_paragraph():
        if paragraph:
            output.append(f"<p>{_inline_to_html(' '.join(paragraph))}</p>")
            paragraph.clear()

    for line in source.splitlines():
        if line.strip().startswith("```"):
            flush_paragraph()
            close_list()
            if in_code:
                output.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
                code_lines.clear()
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue

        heading = _HEADING_PATTERN.match(line)
        if heading:
            flush_paragraph()
            close_list()
            level = len(heading.group(1))
            output.append(f"<h{level}>{_inline_to_html(heading.group(2))}</h{level}>")
            continue

        if not line.strip():
            flush_paragraph()
            close_list()
            continue

        if line.lstrip().startswith(">"):
            flush_paragraph()
            close_list()
            quote_text = line.lstrip()[1:].strip()
            output.append(f"<blockquote>{_inline_to_html(quote_text)}</blockquote>")
            continue

        list_match = re.match(r"^\s*(?:[-+*]\s+|\d+[.)]\s+)(.*)$", line)
        if list_match:
            flush_paragraph()
            list_type = "ol" if re.match(r"^\s*\d+[.)]\s+", line) else "ul"
            if list_tag != list_type:
                close_list()
                output.append(f"<{list_type}>")
                list_tag = list_type
            output.append(f"<li>{_inline_to_html(list_match.group(1))}</li>")
            continue

        close_list()
        paragraph.append(line.strip())

    if in_code:
        output.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
    flush_paragraph()
    close_list()

    safe_title = html.escape(title)
    body = "\n".join(output)
    return (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        f"<title>{safe_title}</title><style>"
        "body{font:16px/1.6 Segoe UI,Arial,sans-serif;max-width:900px;margin:40px auto;"
        "padding:0 24px;color:#24292f}h1,h2,h3{line-height:1.25;margin-top:1.5em}"
        "blockquote{border-left:4px solid #d0d7de;margin:1em 0;padding:.2em 1em;color:#57606a}"
        "pre,code{font-family:Consolas,monospace;background:#f6f8fa}pre{padding:16px;overflow:auto}"
        "a{color:#0969da}li{margin:.25em 0}</style></head>"
        f"<body>{body}</body></html>"
    )


def _find_browsers():
    candidates = []
    if sys.platform == "win32":
        for base in (os.environ.get("PROGRAMFILES(X86)"), os.environ.get("PROGRAMFILES")):
            if base:
                candidates.extend((
                    os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe"),
                    os.path.join(base, "Google", "Chrome", "Application", "chrome.exe"),
                ))
        local = os.environ.get("LOCALAPPDATA")
        if local:
            candidates.extend((
                os.path.join(local, "Microsoft", "Edge", "Application", "msedge.exe"),
                os.path.join(local, "Google", "Chrome", "Application", "chrome.exe"),
            ))
        names = ("msedge", "chrome")
    else:
        names = ("microsoft-edge", "microsoft-edge-stable", "google-chrome", "chromium", "chromium-browser")

    for name in names:
        executable = shutil.which(name)
        if executable:
            candidates.append(executable)
    available = []
    seen = set()
    for candidate in candidates:
        normalized = os.path.normcase(os.path.abspath(candidate))
        if normalized not in seen and os.path.isfile(candidate):
            available.append(candidate)
            seen.add(normalized)
    return available


def _find_browser():
    return next(iter(_find_browsers()), None)


def export_pdf(source, destination):
    browsers = _find_browsers()
    if not browsers:
        raise RuntimeError("Install Microsoft Edge or Google Chrome to export Markdown as PDF.")

    with tempfile.TemporaryDirectory(prefix="pixelscript-pdf-") as temp_dir:
        html_path = Path(temp_dir, "document.html")
        html_path.write_text(markdown_to_html(source), encoding="utf-8")
        failures = []
        for index, browser in enumerate(browsers):
            pdf_path = Path(temp_dir, f"result-{index}.pdf")
            profile_path = Path(temp_dir, f"profile-{index}")
            command = [
                browser,
                "--headless=new",
                "--disable-gpu",
                "--disable-extensions",
                "--no-first-run",
                f"--user-data-dir={profile_path}",
                f"--print-to-pdf={pdf_path}",
                html_path.as_uri(),
            ]
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if pdf_path.is_file() and pdf_path.stat().st_size:
                with pdf_path.open("rb") as stream:
                    if stream.read(5) == b"%PDF-":
                        destination_path = os.path.abspath(destination)
                        directory = os.path.dirname(destination_path) or "."
                        descriptor, staged_path = tempfile.mkstemp(
                            prefix=".pixelscript-", suffix=".pdf", dir=directory
                        )
                        os.close(descriptor)
                        try:
                            shutil.copyfile(pdf_path, staged_path)
                            os.replace(staged_path, destination_path)
                        finally:
                            if os.path.exists(staged_path):
                                os.remove(staged_path)
                        return
            detail = result.stderr.strip() or result.stdout.strip() or "The browser did not create a PDF."
            failures.append(f"{os.path.basename(browser)}: {detail}")
        raise RuntimeError(f"PDF export failed. {'; '.join(failures)}")
