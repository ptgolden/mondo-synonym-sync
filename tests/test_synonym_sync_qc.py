from pathlib import Path

from click.testing import CliRunner

from synonym_sync_qc import (
    SynonymKey,
    SynonymRecord,
    extract_synonyms,
    main,
    pass1_diff_confined,
    pass2_structural,
    provenance_breakdown,
)

FIXTURES = Path(__file__).parent / "fixtures"
ORIGINAL = FIXTURES / "original.obo"


def run(post_name: str):
    """Load original + a variant fixture and run both passes."""
    post = FIXTURES / post_name
    pre_synonyms, _ = extract_synonyms(str(ORIGINAL))
    post_synonyms, _ = extract_synonyms(str(post))
    non_synonym_changes = pass1_diff_confined(str(ORIGINAL), str(post))
    violations, modifications = pass2_structural(pre_synonyms, post_synonyms)
    return non_synonym_changes, violations, modifications


def test_identical():
    non_synonym_changes, violations, modifications = run("identical.obo")
    assert non_synonym_changes == []
    assert violations == []
    assert modifications == {}


def test_scope_change():
    non_synonym_changes, violations, modifications = run("scope_changed.obo")
    assert non_synonym_changes == []
    assert violations == []
    assert len(modifications["scope_change"]) == 1
    (key, pre, post), = modifications["scope_change"]
    assert key.term_id == "MONDO:0000001"
    assert key.literal == "alpha syn"
    assert pre.scope == "EXACT"
    assert post.scope == "BROAD"


def test_modifier_change():
    _, violations, modifications = run("modifier_changed.obo")
    assert violations == []
    (key, pre, post), = modifications["modifier_change"]
    assert key.term_id == "MONDO:0000002"
    assert pre.type == "ABBREVIATION"
    assert post.type is None


def test_provenance_change():
    _, violations, modifications = run("provenance_changed.obo")
    assert violations == []
    (key, pre, post), = modifications["provenance_change"]
    assert key.term_id == "MONDO:0000003"
    assert pre.xrefs == ("Orphanet:3",)
    assert post.xrefs == ("DOID:7", "Orphanet:3")


def test_synonym_added():
    _, violations, _ = run("synonym_added.obo")
    assert len(violations) == 1
    action, key, _ = violations[0]
    assert action == "added"
    assert key == ("MONDO:0000001", "alpha syn extra")


def test_synonym_deleted():
    _, violations, _ = run("synonym_deleted.obo")
    assert len(violations) == 1
    action, key, _ = violations[0]
    assert action == "deleted"
    assert key == ("MONDO:0000003", "gamma syn")


def test_non_synonym_change():
    non_synonym_changes, violations, modifications = run("non_synonym_changed.obo")
    assert violations == []
    assert modifications == {}
    # the changed `def:` line shows up as one '-' and one '+'
    assert len(non_synonym_changes) == 2
    assert any(ln.startswith("-def: ") for ln in non_synonym_changes)
    assert any(ln.startswith("+def: ") for ln in non_synonym_changes)


def test_combined_scope_and_modifier_change():
    """A single synonym changing both scope and modifier must land in both buckets."""
    _, violations, modifications = run("scope_and_modifier_changed.obo")
    assert violations == []
    expected_key = SynonymKey("MONDO:0000002", "beta syn")
    (scope_key, _, _), = modifications["scope_change"]
    (modifier_key, _, _), = modifications["modifier_change"]
    assert scope_key == expected_key
    assert modifier_key == expected_key


def test_provenance_breakdown_counts_adds_drops_by_prefix():
    key = SynonymKey("MONDO:0000001", "alpha syn")
    pre = SynonymRecord(scope="EXACT", type=None, xrefs=("DOID:1", "OMIM:1"))
    post = SynonymRecord(
        scope="EXACT",
        type=None,
        xrefs=("DOID:1", "NCIT:C1", "https://orcid.org/0000-0000-0000-0001"),
    )
    added, dropped = provenance_breakdown([(key, pre, post)])
    assert added == {"NCIT": 1, "https": 1}
    assert dropped == {"OMIM": 1}


def test_cli_pass_on_identical(tmp_path):
    summary = tmp_path / "summary.md"
    report = tmp_path / "report.md"
    result = CliRunner().invoke(
        main,
        [str(ORIGINAL), str(FIXTURES / "identical.obo"),
         "-s", str(summary), "-r", str(report)],
    )
    assert result.exit_code == 0, result.output
    assert summary.exists()
    assert report.exists()
    assert "PASS" in summary.read_text()


def test_cli_fail_on_added_synonym():
    result = CliRunner().invoke(
        main,
        [str(ORIGINAL), str(FIXTURES / "synonym_added.obo")],
    )
    assert result.exit_code == 1
    assert "FAIL" in result.output


def test_cli_ref_with_two_files_is_an_error():
    result = CliRunner().invoke(
        main,
        [str(ORIGINAL), str(FIXTURES / "identical.obo"), "--ref", "HEAD"],
    )
    assert result.exit_code != 0
    assert "--ref cannot be combined" in result.output
