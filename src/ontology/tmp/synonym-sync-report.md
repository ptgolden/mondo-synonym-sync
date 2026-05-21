# Synonym sync QC report

`HEAD:mondo-edit.obo -> mondo-edit.obo`

- **Pass 1** (diff confined to `synonym:` lines): PASS
- **Pass 2** (`(term_id, literal)` set invariant): PASS
- **Number of modifications on existing synonyms**: 1

## Modifications by category

| Category | Count |
|---|---:|
| scope_change | 0 |
| modifier_change | 0 |
| provenance_change | 1 |

## Provenance xref changes by source prefix

| Prefix | Added | Dropped |
|---|---:|---:|
| `MGI` | 1 | 0 |

## Pass 1: non-synonym line changes

No non-synonym lines changed.

## Pass 2: synonym additions and deletions

No synonyms were added or removed.

<details>
<summary>provenance_change (1)</summary>

**`MONDO:0000001`** _alpha disease_
- `synonym: "alpha syn" EXACT [DOID:1, MGI:1, NCIT:C1]`

```diff
- xrefs=['DOID:1', 'NCIT:C1']
+ xrefs=['DOID:1', 'MGI:1', 'NCIT:C1']
```

</details>
