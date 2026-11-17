"""Render the Markdown manuals in this directory as HTML for the website."""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

import markdown

DOCS_DIR = Path(__file__).resolve().parent
WEB_DIR = DOCS_DIR.parent / "web" / "src"

EXTENSIONS = ["extra", "toc", "sane_lists"]
MD_LINK = re.compile(r"\]\((?!https?://|mailto:|#)([^)\s]+?)\.md(#[^)\s]*)?\)")
MD_INLINE_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
BLOCK_PREFIXES = ("#", "|", "```", "~~~", "*", "-", "+", ">", "    ")

# The eJay wordmark: orange fill inside a black outline, underlined by the
# swoosh.  Copied from web/src/index.html so every page carries the logo
# unstretched and in the original colours (web/DesignGuidelines.md §4).
BRAND = (
    '<a class="brand" href="index.html" aria-label="eJay tools, home">',
    '    <span class="brand-word">',
    '        <span class="brand-word-outline" aria-hidden="true">eJayTools</span>',
    '        <span class="brand-word-fill" aria-hidden="true">eJayTools</span>',
    '    </span>',
    '    <svg class="brand-swoosh" viewBox="0 0 104 12" aria-hidden="true" focusable="false">',
    '        <path d="M2 9C22 2 58 1 102 5" fill="none" stroke="#111111" stroke-width="7" stroke-linecap="round"/>',
    '        <path d="M2 9C22 2 58 1 102 5" fill="none" stroke="#F58220" stroke-width="3" stroke-linecap="round"/>',
    '    </svg>',
    '</a>',
)

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title} &middot; eJay Tools manuals</title>
    <meta name="description" content="{description}">
    <meta name="theme-color" content="#111111">
    <meta property="og:type" content="article">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{description}">
    <link rel="icon" type="image/svg+xml" href="logo.svg">
    <link rel="stylesheet" href="index.css">
</head>
<body id="top">

<a class="skip" href="#main">Skip to content</a>

<header class="site-header">
    <nav class="nav" aria-label="Main">
        {brand}
        <ul class="nav-links">
            <li><a href="README.html">Manuals</a></li>
            <li><a href="pxd.html">PXD to WAV</a></li>
            <li><a href="index.html#download">Download</a></li>
            <li><a class="nav-cta" href="https://github.com/hatebit/emp">GitHub</a></li>
        </ul>
    </nav>
</header>

<main id="main">
    <div class="wrap">
        <article class="doc">
            <p class="eyebrow">Documentation</p>
{body}
            <p class="doc-source">Generated from <code>docs/{source}</code></p>
        </article>
    </div>
</main>

<footer class="site-footer">
    <div class="wrap">
        <div class="footer-top">
            <div class="footer-brand">
                {brand_footer}
                <p>Play, render and convert!</p>
            </div>

            <nav aria-label="Footer">
                <ul class="footer-links">
                    <li><a href="README.html">Manuals</a></li>
                    <li><a href="https://github.com/hatebit/emp">Source</a></li>
                    <li><a href="https://github.com/hatebit/emp/releases">Releases</a></li>
                </ul>
            </nav>
        </div>

        <div class="footer-bottom">
            <p>&copy; 2026 hatebit. Not affiliated with the original eJay publishers.</p>
            <p><a href="#top">Back to top</a></p>
        </div>
    </div>
</footer>

</body>
</html>
"""


def wordmark(indent: str) -> str:
    """Return the brand markup, with continuation lines set at the given depth."""
    head, *rest = BRAND
    return "\n".join([head, *(indent + line for line in rest)])


def title_of(source: str, text: str) -> str:
    """Return the first level-one heading, or the file stem as a fallback."""
    match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if match is None:
        return Path(source).stem
    heading = re.sub(r"[`*_]", "", match.group(1))
    return html.escape(heading.strip())


def description_of(text: str) -> str:
    """Return the first prose paragraph as plain text, for the meta description."""
    for block in re.split(r"\n\s*\n", text):
        line = block.strip()
        if not line or line.startswith(BLOCK_PREFIXES):
            continue
        plain = " ".join(line.split())
        plain = MD_INLINE_LINK.sub(r"\1", plain)
        plain = re.sub(r"[`*_]", "", plain)
        if len(plain) > 157:
            plain = plain[:157].rstrip() + "\u2026"
        return html.escape(plain)
    return ""


def render(source: Path, text: str) -> str:
    """Convert one Markdown document to a complete HTML page."""
    text = MD_LINK.sub(lambda m: f"]({m.group(1)}.html{m.group(2) or ''})", text)
    title = title_of(source.name, text)
    return PAGE.format(
        title=title,
        description=description_of(text) or title,
        body=markdown.markdown(text, extensions=EXTENSIONS),
        source=source.name,
        brand=wordmark("        "),
        brand_footer=wordmark("                "),
    )


def build(docs_dir: Path, web_dir: Path) -> int:
    """Write one HTML page per Markdown file and return how many were written."""
    web_dir.mkdir(parents=True, exist_ok=True)
    sources = sorted(docs_dir.glob("*.md"))
    for source in sources:
        text = source.read_text(encoding="utf-8")
        (web_dir / f"{source.stem}.html").write_text(render(source, text), encoding="utf-8")
        print(f"{source.name} -> web/src/{source.stem}.html")
    return len(sources)


def main(argv: list[str] | None = None) -> int:
    """Convert docs/*.md to web/src/*.html."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs-dir", type=Path, default=DOCS_DIR)
    parser.add_argument("--web-dir", type=Path, default=WEB_DIR)
    args = parser.parse_args(argv)
    build(args.docs_dir, args.web_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
