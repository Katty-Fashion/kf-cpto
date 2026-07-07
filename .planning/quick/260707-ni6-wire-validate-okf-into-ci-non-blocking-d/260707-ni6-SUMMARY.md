---
id: 260707-ni6
title: Wire validate_okf into CI (non-blocking) + document OKF in README
phase: quick
plan: 260707-ni6
subsystem: ci/docs
tags: [ci, okf, documentation, non-blocking]
key-files:
  modified:
    - .github/workflows/aggregate.yml
    - README.md
decisions:
  - continue-on-error: true on OKF validate step — OKF is additive; Pages deploy must never depend on it
metrics:
  completed: "2026-07-07"
---

# Quick Task 260707-ni6: Wire validate_okf into CI (non-blocking) + README docs

**One-liner:** Added `continue-on-error: true` OKF validation step to CI pipeline and inserted a full OKF documentation section into README with overview bullet, bundle contents table, and process-value rationale using [LABEL] text pills.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Wire validate_okf into aggregate.yml as non-blocking step | `4841834` | `.github/workflows/aggregate.yml` |
| 2 | Document OKF in README (overview bullet + full section) | `171b3c0` | `README.md` |

## Verification

**validate_okf.py exit code (before and after):**
```
Checked 19 OKF markdown files (14 concepts, 5 exempt index/log).
OKF bundle is conformant.
EXIT: 0
```

**YAML parse of aggregate.yml after edit:**
```
YAML valid
```

## Deviations from Plan

None — plan executed exactly as specified.

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes introduced.

## Self-Check: PASSED

- [x] `.github/workflows/aggregate.yml` modified with non-blocking OKF step
- [x] `README.md` updated with OKF overview bullet and full section
- [x] Commit `4841834` exists (CI step)
- [x] Commit `171b3c0` exists (README docs)
- [x] `python scripts/validate_okf.py` exits 0
- [x] `python -c "import yaml; yaml.safe_load(...)"` returns YAML valid
