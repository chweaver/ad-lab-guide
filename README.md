# AD Lab Foundations

A reproducible Active Directory home lab guide, built for CompTIA A+ 220-1202 (Core 2) prep and as a portfolio piece. The site lives in `docs/` and is rendered with MkDocs + Material.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install mkdocs-material
mkdocs serve
```

Open `http://127.0.0.1:8000`. Edits to files under `docs/` hot-reload.

To build a static site without serving:

```powershell
mkdocs build --strict
```

The `--strict` flag fails on missing nav entries or broken internal links. The CI workflow runs with `--strict`, so build cleanly before pushing.

## Deploy

Pushes to `main` trigger `.github/workflows/deploy.yml`, which builds the site and publishes it to GitHub Pages via `actions/deploy-pages`. Enable Pages once in the repo settings (Source: GitHub Actions) and the workflow handles the rest.

## Add a new phase page

1. Create `docs/build-out/phase-XX-name.md`, `docs/planned/phase-XX-name.md` for planned phases, or `docs/stretch/phase-XX-name.md` for stretch phases. The directory sets the `track` in `lab-status.json`.
2. Add a nav entry in `mkdocs.yml` under the matching section. If a page moves or merges, add its old path to the `redirects` plugin map in `mkdocs.yml`.
3. Follow the content template every phase page uses:
   1. **Status** line (`**Status:** Done.` / `In progress.` / `Not started.`; the status generator parses this)
   2. **Goal** (one line)
   3. **What this proves** (one sentence; add the SY0-701 objective mapping for planned phases)
   4. **Prerequisites**
   5. **Steps** (every command copy-pasteable; deep dives go in `??? info` collapsibles)
   6. **Screenshot** (one slot: what to capture and the `img/` filename)
   7. **Verify** (use a `!!! success` admonition)
   8. **Snapshot** (only if a rollback point is useful here)
   9. **Gotchas** (use `!!! warning` or `!!! danger`)
4. Use the exact lab values from [`docs/reference.md`](docs/reference.md). No placeholders.
5. Run `mkdocs serve` and confirm the page renders cleanly with no warnings.

## Writing style

- Direct, instructional, mentor tone. No filler.
- No em dashes. Use commas, periods, colons, or parentheses.
- Concise by default. Push long deep-dives into collapsible `??? info` blocks so the main flow stays scannable.
- All command blocks use the real lab values (DC01, corp.lab, 192.168.100.x, etc.) and are copy-pasteable.
