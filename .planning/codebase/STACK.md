# Technology Stack

**Analysis Date:** 2026-06-04

## Languages

**Primary:**
- Python 3.9+ (venv pinned to 3.9; CI runs on 3.11) — all automation scripts in `scripts/`
- Ruby — Jekyll static site generation in `docs/`

**Secondary:**
- Liquid (Jekyll templating) — `docs/_layouts/`, `docs/_includes/`
- YAML — data files, frontmatter, workflow config
- JavaScript — browser-side Mermaid rendering in `docs/_layouts/default.html`
- Bash — inline CI steps in `.github/workflows/aggregate.yml`

## Runtime

**Python:**
- Minimum: 3.9 (local venv at `venv/lib/python3.9`)
- CI: 3.11 (set via `actions/setup-python@v5` in workflows)

**Ruby:**
- Managed by `github-pages` gem (pins Jekyll 3.10.0)
- Lockfile: `docs/Gemfile.lock` (present, bundled with Bundler 2.4.10)

**JavaScript:**
- No build step; ESM module loaded directly from CDN at runtime

**Package Manager (Python):**
- pip (no lockfile — `requirements.txt` uses `>=` bounds only)
- Local venv: `venv/`

**Package Manager (Ruby):**
- Bundler 2.4.10
- Lockfile: `docs/Gemfile.lock`

## Frameworks

**Static Site:**
- Jekyll 3.10.0 (via `github-pages` gem 232) — builds `docs/` into GitHub Pages
- Config: `docs/_config.yml`
- Collections: `_projects` (auto-output enabled, permalink `/projects/:name/`)

**Markdown Rendering:**
- kramdown 2.4.0 (Jekyll default parser)

**CSS Framework:**
- Pico CSS v2 — loaded from CDN (`https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css`)
- Custom overrides: `docs/assets/css/custom.css`

**Diagramming:**
- Mermaid v11 — loaded from CDN (`https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs`)
- Supports: kanban, gantt, pie, graph LR diagrams
- Theme: `forest`, securityLevel: `loose`

**Jekyll Plugins (via github-pages):**
- `jekyll-feed` — RSS feed
- `jekyll-seo-tag` — SEO metadata

## Key Dependencies

**Critical (Python — `requirements.txt`):**
- `pyyaml>=6.0` — YAML parsing for kanban.md frontmatter and `_data/*.yml` files
- `google-auth>=2.0` — Service account credentials for Google Sheets API
- `google-api-python-client>=2.0` — Google Sheets v4 API client
- `requests>=2.28` — GitHub REST API calls in `scripts/discover.py` and chat webhooks

**CI-installed (not in lockfile — installed via `pip install` in workflows):**
- Same four packages above installed directly in CI steps

**Critical (Ruby — `docs/Gemfile.lock`):**
- `github-pages 232` — meta-gem that pins all Jekyll dependencies for GitHub Pages compatibility
- `jekyll 3.10.0` — static site builder
- `kramdown 2.4.0` — Markdown parser
- `liquid 4.0.4` — Liquid templating engine
- `mermaid` — not a gem; loaded client-side from CDN

## Configuration

**Environment (CI secrets required):**
- `KF_PAT` — GitHub Personal Access Token; used by `discover.py` for org API calls and git push
- `GSHEET_ID` — Google Spreadsheet ID for LOE export
- `GSHEET_CLIENT_EMAIL` — Service account email for Sheets API auth
- `GSHEET_PRIVATE_KEY` — RSA private key for service account (newlines escaped as `\n`)
- `GOOGLE_CHAT_WEBHOOK` — Incoming webhook URL for Google Chat notifications
- `GITHUB_TOKEN` — Standard Actions token; used for GitHub Pages deploy

**Data files (committed, drive site content):**
- `docs/_data/calendar.yml` — Migration project calendar config (start date, total weeks, phases)
- `docs/_data/loe.yml` — Canonical LOE intermediate written by `scripts/aggregator.py`
- `docs/_data/sync_status.yml` — Aggregator and Sheets export health state

**Jekyll site config:**
- `docs/_config.yml` — title, baseurl, markdown engine, plugins, collection definitions

## Platform Requirements

**Development:**
- Python 3.9+ with pip
- Ruby + Bundler 2.x (for local Jekyll preview: `bundle exec jekyll serve` from `docs/`)
- GitHub CLI (`gh`) — used by `scripts/sheets_sync.py` for filing failure issues

**Production:**
- GitHub Actions (ubuntu-latest runners) — all CI/CD
- GitHub Pages (`gh-pages` branch) — static site hosting at `https://katty-fashion.github.io/kf-cpto/`
- Google Workspace — Sheets API (service account required)

---

*Stack analysis: 2026-06-04*
