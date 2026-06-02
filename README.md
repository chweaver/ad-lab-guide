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

1. Create `docs/build-out/phase-XX-name.md` (or `docs/stretch/phase-XX-name.md` for stretch phases).
2. Add a nav entry in `mkdocs.yml` under the matching section.
3. Follow the seven-section content template every phase page uses:
   1. **Goal**
   2. **Why it matters**
   3. **Prerequisites**
   4. **Steps**
   5. **Verify** (use a `!!! success` admonition)
   6. **Snapshot** (only if a rollback point is useful here)
   7. **Gotchas** (use `!!! warning` or `!!! danger`)
4. Use the exact lab values from [`docs/reference.md`](docs/reference.md). No placeholders.
5. Run `mkdocs serve` and confirm the page renders cleanly with no warnings.

## Writing style

- Direct, instructional, mentor tone. No filler.
- No em dashes. Use commas, periods, colons, or parentheses.
- Concise by default. Push long deep-dives into collapsible `??? info` blocks so the main flow stays scannable.
- All command blocks use the real lab values (DC01, corp.lab, 192.168.100.x, etc.) and are copy-pasteable.
