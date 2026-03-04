#!/usr/bin/env python3
"""
Validate front matter of staged/changed .md files in content/.
Used by git hooks (pre-commit, pre-push).

Exit codes:
  0 = all valid
  1 = validation errors found
"""

import sys
import re
from pathlib import Path

try:
    import frontmatter
except ImportError:
    print("[hook] ERROR: python-frontmatter not installed.")
    print("       Run: pip3 install python-frontmatter")
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────────────

REQUIRED_FIELDS  = ["title", "tags", "date", "author", "summary"]
DATE_RE          = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CONTENT_DIR_NAME = "content"
SKIP_DIRS        = {"template"}

# ── Helpers ───────────────────────────────────────────────────────────────────

def validate_file(path: Path) -> list[str]:
    """Return list of error strings, empty if valid."""
    errors = []

    try:
        post = frontmatter.load(str(path))
    except Exception as e:
        return [f"  Cannot parse front matter: {e}"]

    meta = post.metadata

    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in meta or not meta[field]:
            errors.append(f"  Missing or empty field: '{field}'")

    if errors:
        return errors

    # title
    if not isinstance(meta["title"], str) or not meta["title"].strip():
        errors.append("  'title' must be a non-empty string")

    # tags
    if not isinstance(meta["tags"], list) or len(meta["tags"]) == 0:
        errors.append("  'tags' must be a non-empty list, e.g: [\"golang\", \"backend\"]")
    else:
        for t in meta["tags"]:
            if not isinstance(t, str):
                errors.append(f"  Each tag must be a string, got: {repr(t)}")

    # date
    date_val = str(meta.get("date", "")).strip()
    if not DATE_RE.match(date_val):
        errors.append(f"  'date' must be YYYY-MM-DD format, got: '{date_val}'")

    # author
    if not isinstance(meta["author"], str) or not meta["author"].strip():
        errors.append("  'author' must be a non-empty string")

    # summary
    if not isinstance(meta["summary"], str) or not meta["summary"].strip():
        errors.append("  'summary' must be a non-empty string")

    return errors


def is_content_md(path_str: str) -> bool:
    """Return True if path is a .md file inside content/ (not template/)."""
    p = Path(path_str)
    if p.suffix != ".md":
        return False
    parts = p.parts
    try:
        idx = parts.index(CONTENT_DIR_NAME)
    except ValueError:
        return False
    # parts[idx+1] is the article folder name
    if len(parts) > idx + 1 and parts[idx + 1] in SKIP_DIRS:
        return False
    return True


# ── Entry ─────────────────────────────────────────────────────────────────────

def main(files: list[str]) -> int:
    md_files = [Path(f) for f in files if is_content_md(f)]

    if not md_files:
        return 0

    print(f"\n[hook] Validating {len(md_files)} article(s)...\n")

    total_errors = 0
    for path in md_files:
        if not path.exists():
            # file deleted — skip
            continue
        errors = validate_file(path)
        if errors:
            print(f"  [FAIL] {path}")
            for e in errors:
                print(e)
            print()
            total_errors += len(errors)
        else:
            print(f"  [ OK ] {path}")

    if total_errors:
        print(f"\n[hook] {total_errors} error(s) found. Fix before committing.\n")
        print("       Front matter template:")
        print("       ---")
        print('       title:   "Article Title"')
        print("       tags:")
        print('         - "tag1"')
        print('       date:    "YYYY-MM-DD"')
        print('       author:  "your-name"')
        print('       summary: "Short description."')
        print("       ---\n")
        return 1

    print(f"\n[hook] All articles valid.\n")
    return 0


if __name__ == "__main__":
    # Accept file list as args, or read from stdin (one path per line)
    if len(sys.argv) > 1:
        files = sys.argv[1:]
    else:
        files = [line.strip() for line in sys.stdin if line.strip()]

    sys.exit(main(files))
