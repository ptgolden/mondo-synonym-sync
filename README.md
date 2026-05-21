# mondo-synonym-sync

Scratch repo for developing the QC script (`synonym_sync_qc.py`) and the
GitHub Actions workflow (`.github/workflows/synonyms.yaml`) that will be
committed to the real Mondo ODK repo. The layout under `src/` mirrors
Mondo's so the workflow paths are copy-paste compatible.

## Layout

- `synonym_sync_qc.py` — the QC script. Checks that a pre-/post-sync diff
  of `mondo-edit.obo` only modifies attributes of existing synonyms (no
  adds, no deletes, no non-synonym line changes).
- `src/scripts/synonym_sync_qc.py` — symlink into the root, so the
  workflow can call `python ../scripts/synonym_sync_qc.py` from
  `src/ontology/` exactly the way real Mondo does.
- `src/ontology/mondo-edit.obo` — porcelain OBO; the workflow's
  `update-synonyms-sync` Makefile target is what mutates this in a real
  run.
- `src/ontology/Makefile` — stub of the Mondo target.
- `tests/` — pytest suite for the QC script.
- `mondo-edit.{original,synced}.obo` — full pre/post snapshots from a
  real Mondo sync run, kept for ad-hoc benchmarking.

## Run the tests

```
uv run pytest
```

## Test the workflow end-to-end

Push to a sandbox GitHub repo, then in Settings → Actions → General:
allow read/write workflow permissions and allow Actions to open PRs.
The workflow currently uses `GITHUB_TOKEN` for the sandbox (swap back to
`GH_TOKEN` before this lands in Mondo, or PRs won't trigger downstream
workflows). Then Actions → "Update Synonyms Evidence" → Run workflow.

The Makefile stub applies an idempotent `sed` that adds an `MGI:1` xref
to one synonym, mimicking what the real Mondo `update-synonyms-sync`
target does (mutate `mondo-edit.obo` in place). peter-evans then opens a
PR with that diff, body = QC summary, full report attached as artifact.
**Don't merge the PR** — if you do, the porcelain file gains the xref
and the sed becomes a no-op on subsequent dispatches.
