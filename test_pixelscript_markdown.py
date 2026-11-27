import pytest

import pixelscript_markdown


def test_markdown_renders_blocks_and_inline_formatting():
    rendered = pixelscript_markdown.markdown_to_html(
        "# Heading\n\n**bold** and *italic*\n\n- first\n- second\n\n```py\nprint(1)\n```"
    )

    assert "<h1>Heading</h1>" in rendered
    assert "<strong>bold</strong>" in rendered
    assert "<em>italic</em>" in rendered
    assert "<ul>" in rendered
    assert "<li>first</li>" in rendered
    assert "<pre><code>print(1)</code></pre>" in rendered


def test_markdown_escapes_raw_html_and_unsafe_links():
    rendered = pixelscript_markdown.markdown_to_html(
        '<script>alert("x")</script>\n\n[bad](javascript:alert)'
    )

    assert "&lt;script&gt;" in rendered
    assert "<script>" not in rendered
    assert "javascript:" not in rendered


def test_heading_outline_includes_source_lines_and_levels():
    assert pixelscript_markdown.extract_headings("intro\n## Section\n\n### Detail") == [
        (2, "Section", 2),
        (4, "Detail", 3),
    ]


def test_pdf_export_reports_missing_browser(monkeypatch, tmp_path):
    monkeypatch.setattr(pixelscript_markdown, "_find_browsers", lambda: [])

    with pytest.raises(RuntimeError, match="Install Microsoft Edge or Google Chrome"):
        pixelscript_markdown.export_pdf("content", tmp_path / "output.pdf")
