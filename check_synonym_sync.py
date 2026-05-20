#!/usr/bin/env python3
"""QC check for Mondo update-synonyms-sync output.

Verifies that a diff modifies only attributes of *existing* synonyms — no
synonyms were added or removed, no quoted literals mutated, no non-synonym
lines changed. Allowed modifications: scope flip, synonym-type modifier
change, xref provenance change, trailing axiom-annotation change.

Usage:
  check_synonym_sync.py [-v] FILE             # git diff -U0 FILE
  check_synonym_sync.py [-v] FILE_A FILE_B    # git diff --no-index -U0 FILE_A FILE_B

Options:
  -v, --verbose   Print paired -/+ lines for every violation and every
                  allowed modification (default: counts only, plus the first
                  10 violations).

Exit status: 0 if the invariant holds, 1 otherwise.
"""

import re
import subprocess
import sys
from collections import Counter

SCOPES = ("EXACT", "NARROW", "BROAD", "RELATED")

# Synonym line: synonym: "LITERAL" SCOPE [MODIFIER] [XREFS] [{ANNO}]
# Anchored to the SCOPE keyword to find the closing quote of the literal,
# even if the literal contains escaped quotes.
SYN_RE = re.compile(
    r'^synonym: "(.*)" (' + "|".join(SCOPES) + r')(?: (.*))?$'
)
# Tail after SCOPE: optional MODIFIER, required [xrefs], optional {anno}.
REST_RE = re.compile(r'^(?:(\S+) )?(\[.*\])(?: (\{.*\}))?$')
# Hunk header: @@ -OLD_START[,OLD_COUNT] +NEW_START[,NEW_COUNT] @@ ...
HUNK_RE = re.compile(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')


def hunk_start(header):
    """Return the old-side starting line number of a hunk header."""
    m = HUNK_RE.match(header)
    return int(m.group(1)) if m else None


def run_git_diff(args):
    if len(args) == 1:
        cmd = ["git", "diff", "-U0", "--", args[0]]
    elif len(args) == 2:
        cmd = ["git", "diff", "--no-index", "-U0", args[0], args[1]]
    else:
        sys.exit("usage: check_synonym_sync.py FILE | FILE_A FILE_B")
    r = subprocess.run(cmd, capture_output=True, text=True)
    # `git diff --no-index` returns 1 when files differ; not an error.
    if r.returncode not in (0, 1):
        sys.exit(f"git diff failed: {r.stderr.strip()}")
    return r.stdout


def parse_hunks(diff_text):
    """Yield (header, minus_lines, plus_lines) for each @@ hunk."""
    header = None
    minus, plus = [], []
    in_hunk = False
    for ln in diff_text.splitlines():
        if ln.startswith("@@"):
            if in_hunk:
                yield header, minus, plus
            header = ln
            minus, plus = [], []
            in_hunk = True
        elif not in_hunk or ln.startswith(("---", "+++")):
            continue
        elif ln.startswith("-"):
            minus.append(ln[1:])
        elif ln.startswith("+"):
            plus.append(ln[1:])
    if in_hunk:
        yield header, minus, plus


def parse_synonym(line):
    m = SYN_RE.match(line)
    if not m:
        return None
    literal, scope, rest = m.group(1), m.group(2), m.group(3) or ""
    r = REST_RE.match(rest) if rest else None
    if rest and not r:
        return {"literal": literal, "scope": scope, "modifier": None,
                "xrefs": None, "anno": None, "_rest_unparsed": rest}
    return {
        "literal": literal,
        "scope": scope,
        "modifier": r.group(1) if r else None,
        "xrefs": r.group(2) if r else None,
        "anno": r.group(3) if r else None,
    }


def main():
    argv = sys.argv[1:]
    verbose = False
    args = []
    for a in argv:
        if a in ("-v", "--verbose"):
            verbose = True
        else:
            args.append(a)

    diff_text = run_git_diff(args)

    label = args[0] if len(args) == 1 else f"{args[0]} -> {args[1]}"
    if not diff_text.strip():
        print(f"QC report: {label}")
        print("  no differences. [PASS]")
        return 0

    violations = []                                  # (category, lineno, detail)
    mod_examples = {                                 # category -> [(lineno, m_line, p_line)]
        "scope_flip": [],
        "modifier_change": [],
        "provenance_change": [],
        "trailing_annotation_change": [],
    }
    n_hunks = n_minus = n_plus = 0

    for header, minus, plus in parse_hunks(diff_text):
        n_hunks += 1
        n_minus += len(minus)
        n_plus += len(plus)
        start = hunk_start(header)

        # Rule 1: every changed line must be a synonym line.
        non_syn = [("-", l) for l in minus if not l.startswith("synonym: ")] \
                + [("+", l) for l in plus if not l.startswith("synonym: ")]
        if non_syn:
            for sign, ln in non_syn:
                violations.append(("non_synonym_change", start, f"{sign}{ln}"))
            continue

        # Rule 2: minus-count must equal plus-count within a hunk.
        if len(minus) != len(plus):
            violations.append(
                ("count_mismatch", start,
                 f"{len(minus)} removed vs {len(plus)} added synonym lines")
            )
            # Don't try to pair; the imbalance is itself the violation.
            continue

        # Rule 3: pair positionally, compare.
        for i, (m_line, p_line) in enumerate(zip(minus, plus)):
            lineno = (start + i) if start is not None else None
            m_p = parse_synonym(m_line)
            p_p = parse_synonym(p_line)
            if m_p is None or p_p is None:
                violations.append(("unparseable", lineno,
                                   f"-{m_line}\n+{p_line}"))
                continue
            if m_p["literal"] != p_p["literal"]:
                violations.append(
                    ("literal_changed", lineno,
                     f'-{m_line}\n+{p_line}')
                )
                continue
            buckets = []
            if m_p["scope"] != p_p["scope"]:
                buckets.append("scope_flip")
            if m_p["modifier"] != p_p["modifier"]:
                buckets.append("modifier_change")
            if m_p["xrefs"] != p_p["xrefs"]:
                buckets.append("provenance_change")
            if m_p["anno"] != p_p["anno"]:
                buckets.append("trailing_annotation_change")
            if not buckets:
                # Line is in the diff but parses identically — shouldn't happen.
                violations.append(("identical_after_parse", lineno,
                                   f"-{m_line}\n+{p_line}"))
                continue
            for b in buckets:
                mod_examples[b].append((lineno, m_line, p_line))

    print(f"QC report: {label}")
    print(f"  hunks:           {n_hunks}")
    print(f"  changed lines:   -{n_minus} / +{n_plus}")
    print()

    if violations:
        print(f"VIOLATIONS: {len(violations)}  [FAIL]")
        v_cats = Counter(v[0] for v in violations)
        for cat, n in sorted(v_cats.items()):
            print(f"  {cat:30s} {n}")
        print()
        show = violations if verbose else violations[:10]
        label_show = "All" if verbose else f"First {len(show)}"
        print(f"{label_show} violation detail(s):")
        for cat, lineno, detail in show:
            loc = f"line {lineno}" if lineno is not None else "?"
            print(f"  [{cat}] {loc}")
            for line in detail.splitlines():
                print(f"    {line}")
        if not verbose and len(violations) > len(show):
            print(f"  ... ({len(violations) - len(show)} more; rerun with -v)")
    else:
        print("VIOLATIONS: 0  [PASS]")

    print()
    print("Allowed modifications:")
    for cat in ("scope_flip", "modifier_change",
                "provenance_change", "trailing_annotation_change"):
        print(f"  {cat:30s} {len(mod_examples[cat])}")

    if verbose:
        for cat in ("scope_flip", "modifier_change",
                    "provenance_change", "trailing_annotation_change"):
            examples = mod_examples[cat]
            if not examples:
                continue
            print()
            print(f"{cat} ({len(examples)}):")
            for lineno, m_line, p_line in examples:
                loc = f"line {lineno}" if lineno is not None else "?"
                print(f"  {loc}:")
                print(f"    -{m_line}")
                print(f"    +{p_line}")

    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
