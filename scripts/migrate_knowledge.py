#!/usr/bin/env python3
"""
One-time migration script: normalize all .md files in knowledge/ to
standard front matter (title, tags, date, author, summary).

Rules:
- Strip existing Obsidian front matter (--- ... ---)
- Strip inline **Tags:** / **Source:** / **Related:** lines
- Build new front matter from filename + extracted tags + first paragraph
- Write output to content/<slug>/vi.md  (folder-per-article structure)
"""

import os
import re
import sys
import shutil
from pathlib import Path
from datetime import date

# ── Config ───────────────────────────────────────────────────────────────────

KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"
CONTENT_DIR   = Path(__file__).parent.parent / "content"
DEFAULT_AUTHOR = "Admin"
TODAY = date.today().strftime("%Y-%m-%d")

# Inline metadata patterns to strip from body
STRIP_PATTERNS = [
    re.compile(r"^\*\*Tags:\*\*.*$",    re.MULTILINE | re.IGNORECASE),
    re.compile(r"^\*\*Tag:\*\*.*$",     re.MULTILINE | re.IGNORECASE),
    re.compile(r"^\*\*Source[s]?:\*\*.*$", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^\*\*Related:\*\*.*$", re.MULTILINE | re.IGNORECASE),
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def slugify(name: str) -> str:
    """Convert filename (without .md) to a folder slug."""
    s = name.lower()
    s = re.sub(r"[^\w\s\-àáâãèéêìíòóôõùúýăđơư]", "", s, flags=re.UNICODE)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")


def extract_inline_tags(text: str) -> list[str]:
    """Find #tag patterns from **Tags:** line."""
    tags = []
    m = re.search(r"\*\*Tags?:\*\*\s*(.*)", text, re.IGNORECASE)
    if m:
        raw = m.group(1)
        found = re.findall(r"#([\w\-]+)", raw)
        tags = [t.lower().replace("_", "-") for t in found]
    return tags


def extract_title(filename_stem: str, body: str) -> str:
    """Use first H1 if exists, else derive from filename."""
    m = re.search(r"^#{1,2}\s+(.+)", body, re.MULTILINE)
    if m:
        return m.group(1).strip()
    # Clean up filename like "Golang - GC" → "Golang - GC"
    return filename_stem.strip()


def extract_summary(body: str) -> str:
    """
    Extract first meaningful paragraph (not heading, not empty, not code fence).
    Max 200 chars.
    """
    lines = body.splitlines()
    para_lines = []
    in_code = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if not stripped:
            if para_lines:
                break
            continue
        if stripped.startswith("#"):
            continue
        # Skip Obsidian callout openers
        if stripped.startswith(">") and "SUMMARY" in stripped.upper():
            continue
        # Skip checklist items
        if re.match(r"^-\s*\[[ x]\]", stripped):
            continue
        para_lines.append(stripped)

    summary = " ".join(para_lines)
    # Strip markdown bold/italic
    summary = re.sub(r"\*{1,2}(.*?)\*{1,2}", r"\1", summary)
    # Strip links [text](url)
    summary = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", summary)
    # Strip inline code
    summary = re.sub(r"`[^`]+`", "", summary)
    summary = re.sub(r"\s+", " ", summary).strip()

    if len(summary) > 200:
        summary = summary[:197].rsplit(" ", 1)[0] + "..."

    return summary or "Ghi chú kỹ thuật."


def strip_old_metadata(text: str) -> str:
    """Remove Obsidian front matter block and inline metadata lines."""
    # Remove YAML front matter
    text = re.sub(r"^---\s*\n.*?\n---\s*\n", "", text, flags=re.DOTALL)
    # Remove inline metadata lines
    for pat in STRIP_PATTERNS:
        text = pat.sub("", text)
    # Collapse 3+ blank lines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.lstrip("\n")


def infer_tags_from_filename(stem: str) -> list[str]:
    """Derive base tags from the filename prefix like 'Golang -', 'Database -'."""
    prefix_map = {
        "golang":        ["golang", "backend"],
        "database":      ["database", "backend"],
        "system design": ["system-design", "architecture"],
        "security":      ["security", "backend"],
        "devops":        ["devops", "aws"],
        "aws":           ["aws", "cloud"],
        "kafka":         ["kafka", "messaging"],
        "microservices": ["microservices", "architecture"],
        "cloud":         ["cloud", "architecture"],
        "behavioral":    ["interview", "career"],
        "software":      ["principles", "architecture"],
        "clean":         ["architecture", "design-patterns"],
        "s3":            ["aws", "storage"],
        "roadmap":       ["roadmap", "learning"],
    }
    stem_lower = stem.lower()
    for key, tags in prefix_map.items():
        if stem_lower.startswith(key):
            return tags
    return ["backend"]


def build_front_matter(title: str, tags: list[str], summary: str) -> str:
    tag_list = "\n".join(f'  - "{t}"' for t in tags)
    # Escape quotes in title/summary
    safe_title   = title.replace('"', '\\"')
    safe_summary = summary.replace('"', '\\"')
    return (
        "---\n"
        f'title: "{safe_title}"\n'
        f"tags:\n{tag_list}\n"
        f'date: "{TODAY}"\n'
        f'author: "{DEFAULT_AUTHOR}"\n'
        f'summary: "{safe_summary}"\n'
        "---\n\n"
    )

# ── Main ──────────────────────────────────────────────────────────────────────

def migrate_file(md_path: Path):
    raw = md_path.read_text(encoding="utf-8")

    # 1. Extract tags before stripping
    inline_tags = extract_inline_tags(raw)

    # 2. Strip old metadata
    body = strip_old_metadata(raw)

    # 3. Derive fields
    stem  = md_path.stem
    title = extract_title(stem, body)
    tags  = inline_tags or infer_tags_from_filename(stem)
    # Deduplicate, keep order
    seen = set()
    tags = [t for t in tags if not (t in seen or seen.add(t))]

    summary = extract_summary(body)

    # 4. Build destination: content/<slug>/vi.md
    slug = slugify(stem)
    dest_dir = CONTENT_DIR / slug
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest_file = dest_dir / "vi.md"

    # 5. Write
    front = build_front_matter(title, tags, summary)
    dest_file.write_text(front + body, encoding="utf-8")

    return slug, title, tags


def main():
    md_files = sorted(KNOWLEDGE_DIR.glob("*.md"))
    if not md_files:
        print(f"No .md files found in {KNOWLEDGE_DIR}", file=sys.stderr)
        sys.exit(1)

    print(f"Migrating {len(md_files)} files from knowledge/ → content/\n")

    ok = []
    for f in md_files:
        try:
            slug, title, tags = migrate_file(f)
            tag_str = ", ".join(tags[:4])
            print(f"  [OK] {slug}\n       title: {title[:60]}\n       tags:  {tag_str}\n")
            ok.append(slug)
        except Exception as e:
            print(f"  [ERR] {f.name}: {e}", file=sys.stderr)

    print(f"Done. {len(ok)}/{len(md_files)} files migrated.")


if __name__ == "__main__":
    main()
