```
      _                 _  __
   __| | ___   ___ ___ (_)/ _|_   _
  / _` |/ _ \ / __/ __|| | |_| | | |
 | (_| | (_) | (__\__ \| |  _| |_| |
  \__,_|\___/ \___|___/|_|_|  \__, |
                               |___/
  Headless CMS on GitHub Pages
```

A minimal knowledge base powered by Markdown files, Python, and GitHub Actions.
No database. No server. Just files.

---

## How it works

```
  [you write .md]  -->  [git push]  -->  [GitHub Action runs]
                                                  |
                                                  v
                                         processor.py scans
                                         content/ directory
                                                  |
                                                  v
                                         public/index.json
                                         auto-committed
                                                  |
                                                  v
                                      [browser reads index.json]
                                      [fetches .md on demand]
```

---

## Project structure

```
docsify/
|
|-- content/                  # Articles (one folder per article)
|   |-- my-article/
|   |   |-- vi.md             # Vietnamese version
|   |   |-- en.md             # English version (optional)
|   |   `-- assets/           # Images for this article
|   `-- template/             # Blank template to copy from
|       |-- vi.md
|       `-- en.md
|
|-- scripts/
|   |-- processor.py          # Scans content/, builds index.json
|   `-- migrate_knowledge.py  # One-time migration utility
|
|-- public/
|   `-- index.json            # Auto-generated. Do not edit manually.
|
|-- .github/workflows/
|   `-- content-pipeline.yml  # Runs processor.py on every push
|
|-- index.html                # Frontend
|-- script.js                 # Frontend logic
`-- requirements.txt
```

---

## Adding a new article

### Step 1 — Create a folder

Folder name becomes the article ID. Use lowercase, hyphens only.

```
content/
`-- ten-bai-viet-cua-ban/
    `-- vi.md
```

### Step 2 — Write the article

Copy from `content/template/vi.md` or create from scratch.
The file **must** start with this front matter block:

```
---
title:   "Tiêu đề bài viết"
tags:
  - "tag1"
  - "tag2"
date:    "2026-03-04"          # YYYY-MM-DD
author:  "nathan.huynh"
summary: "Mô tả ngắn 1-2 câu hiển thị ở trang danh sách."
---

# Tiêu đề

Nội dung Markdown bình thường ở đây...
```

### Step 3 — Push

```
git add content/ten-bai-viet-cua-ban/
git commit -m "add: ten-bai-viet-cua-ban"
git push
```

GitHub Actions will automatically:
- Run `processor.py`
- Rebuild `public/index.json`
- Commit and push the updated index

### Step 4 — Done

Your article appears on the site within ~30 seconds.

---

## Adding a second language

Create `en.md` in the same folder with its own front matter:

```
content/
`-- ten-bai-viet-cua-ban/
    |-- vi.md
    `-- en.md              <-- same metadata fields, English content
```

The reader will see a `[vi] [en]` switcher on the article page.

---

## Required front matter fields

```
  Field    | Type            | Example
  ---------|-----------------|----------------------------------
  title    | string          | "Golang - Goroutine Leak"
  tags     | list of strings | ["golang", "concurrency"]
  date     | YYYY-MM-DD      | "2026-03-04"
  author   | string          | "nathan.huynh"
  summary  | string          | "Short description, 1-2 sentences"
```

Missing any field -> processor raises an error -> GitHub Action fails -> index.json is NOT updated.

---

## Git hooks (validation)

Hooks validate front matter before `commit` and `push`.
Run once after cloning:

```bash
bash scripts/install_hooks.sh
```

What each hook does:

```
  pre-commit   checks only STAGED content/*.md files
               -> fast, runs on every commit

  pre-push     checks ALL content/*.md files
               -> safety net before code reaches remote
```

Example output when a file is invalid:

```
  [FAIL] content/my-article/vi.md
    Missing or empty field: 'tags'
    Missing or empty field: 'summary'
    'date' must be YYYY-MM-DD format, got: '26-3-4'

  [hook] 3 error(s) found. Fix before committing.
```

To skip hooks in an emergency (not recommended):

```bash
git commit --no-verify
git push   --no-verify
```

---

## Running locally

```bash
# Install dependencies (one time)
pip3 install python-frontmatter PyYAML

# Rebuild index after adding articles
python3 scripts/processor.py

# Serve the site
python3 -m http.server 8000
```

Open: http://localhost:8000

---

## Supported languages (syntax highlight)

Go · Python · JavaScript · TypeScript · Bash · SQL · YAML · JSON · Dockerfile

---

## License

MIT
