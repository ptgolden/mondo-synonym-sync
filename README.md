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
allow read/write workflow permissions and allow Actions to open PRs. Set
a `GH_TOKEN` secret (or swap to `GITHUB_TOKEN` in the workflow). Then
Actions → "Update Synonyms Evidence" → Run workflow.

With the Makefile as a no-op stub the workflow will PASS but
peter-evans will skip the PR (no diff to ship). To exercise the full
PR + artifact-link path, edit the stub to produce a deterministic
change to `mondo-edit.obo` (e.g. a one-line `sed -i` that adds an xref
to one of the synonyms), push, and redispatch.
