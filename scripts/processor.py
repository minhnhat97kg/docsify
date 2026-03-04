#!/usr/bin/env python3
"""
Content Processor - Scans content/ directory, validates metadata,
and generates public/index.json for the Headless CMS.
"""

import os
import json
import sys
import re
from pathlib import Path
from datetime import datetime, timezone

try:
    import frontmatter
except ImportError:
    print("ERROR: 'python-frontmatter' is not installed. Run: pip install python-frontmatter", file=sys.stderr)
    sys.exit(1)

# ── Configuration ────────────────────────────────────────────────────────────

CONTENT_DIR = Path(__file__).parent.parent / "public" / "content"
OUTPUT_FILE = Path(__file__).parent.parent / "public" / "index.json"
REQUIRED_FIELDS = ["title", "tags", "date", "author", "summary"]
DATE_FORMAT = "%Y-%m-%d"
SUPPORTED_LANGS = ["vi", "en", "ja", "zh", "ko", "fr", "de", "es"]
SKIP_DIRS = {"template"}

# ── Helpers ──────────────────────────────────────────────────────────────────

def validate_date(date_str: str, filepath: str) -> str:
    """Validate and normalize date string to YYYY-MM-DD."""
    if not isinstance(date_str, str):
        date_str = str(date_str)
    date_str = date_str.strip()
    try:
        parsed = datetime.strptime(date_str, DATE_FORMAT)
        return parsed.strftime(DATE_FORMAT)
    except ValueError:
        raise ValueError(
            f"Invalid date format in '{filepath}': '{date_str}'. "
            f"Expected YYYY-MM-DD (e.g. 2026-01-15)."
        )


def validate_tags(tags, filepath: str) -> list:
    """Ensure tags is a non-empty list of strings."""
    if not isinstance(tags, list) or len(tags) == 0:
        raise ValueError(
            f"Field 'tags' in '{filepath}' must be a non-empty list. "
            f"Got: {repr(tags)}"
        )
    return [str(t).strip() for t in tags]


def validate_metadata(post, filepath: str) -> dict:
    """Validate all required fields and return cleaned metadata dict."""
    errors = []
    for field in REQUIRED_FIELDS:
        if field not in post.metadata or not post.metadata[field]:
            errors.append(f"  - Missing or empty field: '{field}'")

    if errors:
        raise ValueError(
            f"Metadata validation failed for '{filepath}':\n" + "\n".join(errors)
        )

    meta = dict(post.metadata)
    meta["date"] = validate_date(meta["date"], filepath)
    meta["tags"] = validate_tags(meta["tags"], filepath)
    meta["title"] = str(meta["title"]).strip()
    meta["author"] = str(meta["author"]).strip()
    meta["summary"] = str(meta["summary"]).strip()

    return meta


def detect_language(filename: str) -> str | None:
    """Extract language code from filename like 'vi.md' -> 'vi'."""
    stem = Path(filename).stem.lower()
    if stem in SUPPORTED_LANGS:
        return stem
    return None


def build_article_path(folder_name: str, lang: str) -> str:
    """Path relative to site root (public/ is served as /)."""
    return f"content/{folder_name}/{lang}.md"

# ── Core Processing ──────────────────────────────────────────────────────────

def process_content_dir() -> list:
    """Scan all article folders and return aggregated article list."""
    if not CONTENT_DIR.exists():
        raise FileNotFoundError(f"Content directory not found: {CONTENT_DIR}")

    articles = []
    errors = []

    folders = sorted([
        d for d in CONTENT_DIR.iterdir()
        if d.is_dir() and d.name not in SKIP_DIRS
    ])

    if not folders:
        print("Warning: No article folders found in content/.", file=sys.stderr)
        return []

    for folder in folders:
        md_files = [f for f in folder.iterdir() if f.suffix == ".md"]

        if not md_files:
            print(f"  [SKIP] '{folder.name}': no .md files found.", file=sys.stderr)
            continue

        lang_versions = {}

        for md_file in sorted(md_files):
            lang = detect_language(md_file.name)
            if lang is None:
                print(f"  [SKIP] '{md_file}': unrecognized language filename.", file=sys.stderr)
                continue

            filepath_str = str(md_file.relative_to(CONTENT_DIR.parent))

            try:
                post = frontmatter.load(str(md_file))
                meta = validate_metadata(post, filepath_str)
            except (ValueError, Exception) as e:
                errors.append(str(e))
                continue

            lang_versions[lang] = {
                "title": meta["title"],
                "summary": meta["summary"],
                "author": meta["author"],
                "path": build_article_path(folder.name, lang),
            }
            # Use first encountered lang for top-level fields (prefer 'vi' then 'en')
            if "primary_meta" not in locals() or lang in ("vi", "en"):
                primary_lang = lang
                primary_meta = meta

        if not lang_versions:
            continue

        # Determine primary metadata (prefer 'vi' > 'en' > first available)
        primary_lang = next(
            (l for l in ["vi", "en"] if l in lang_versions),
            next(iter(lang_versions))
        )
        primary = lang_versions[primary_lang]

        article = {
            "id": folder.name,
            "title": primary["title"],
            "author": primary["author"],
            "summary": primary["summary"],
            "tags": next(
                fm.metadata["tags"]
                for fm_path in [folder / f"{primary_lang}.md"]
                if fm_path.exists()
                for fm in [frontmatter.load(str(fm_path))]
            ),
            "date": next(
                str(fm.metadata.get("date", ""))
                for fm_path in [folder / f"{primary_lang}.md"]
                if fm_path.exists()
                for fm in [frontmatter.load(str(fm_path))]
            ),
            "languages": lang_versions,
        }
        articles.append(article)
        print(f"  [OK]   '{folder.name}' ({', '.join(lang_versions.keys())})")

    if errors:
        print("\n── VALIDATION ERRORS (" + str(len(errors)) + ") ──────────────────", file=sys.stderr)
        for err in errors:
            print(err, file=sys.stderr)
        print("─" * 50, file=sys.stderr)
        sys.exit(1)

    return articles

# ── Output ───────────────────────────────────────────────────────────────────

def write_output(articles: list):
    """Write articles list to public/index.json."""
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total": len(articles),
        "articles": sorted(articles, key=lambda a: a["date"], reverse=True),
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Output: {OUTPUT_FILE} ({len(articles)} article(s))")

# ── Entry Point ───────────────────────────────────────────────────────────────

def main():
    print(f"Scanning: {CONTENT_DIR}")
    articles = process_content_dir()
    write_output(articles)
    print("Done.")


if __name__ == "__main__":
    main()
