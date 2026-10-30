"""Identity contracts, not native execution or resource-deployment tests."""
import pytest

from gene_annotation_episode.blast_program_context import resolve_blast_program_context
from gene_annotation_episode.blast_search import PROGRAM_UNITS


def context(program="blastp", **changes):
    values = dict(execution_program=program, reported_program=None, scientific_mode="database",
                  query_kind="sequence", reference_kind="sequence", native_version=None)
    values.update(changes)
    return resolve_blast_program_context(**values)


@pytest.mark.parametrize("program,reference,geometry", [
    ("blastn", "sequence", "blastn"), ("blastp", "sequence", "blastp"),
    ("blastx", "sequence", "blastx"), ("tblastn", "sequence", "tblastn"),
    ("tblastx", "sequence", "tblastx"), ("psiblast", "sequence", "blastp"),
    ("deltablast", "sequence", "blastp"), ("rpsblast", "profile", "blastp"),
    ("rpstblastn", "profile", "blastx"), ("blastn_vdb", "vdb_read", "blastn"),
    ("tblastn_vdb", "vdb_mixed", "tblastn"),
])
def test_all_eleven_identities_keep_separate_geometry(program, reference, geometry):
    result = context(program, reference_kind=reference)
    assert result == {"execution_program": program, "reported_program": None,
        "scientific_mode": "database", "query_kind": "sequence", "reference_kind": reference,
        "native_version": None, "geometry_program": geometry}
    assert set(PROGRAM_UNITS) == {"blastn", "blastp", "blastx", "tblastn", "tblastx"}


@pytest.mark.parametrize("program,reported,query,reference", [
    ("tblastn", "psitblastn", "pssm", "sequence"),
    ("psiblast", "phiblastp", "sequence", "sequence"),
    ("psiblast", "psiblast", "msa", "sequence"),
    ("deltablast", "deltablast", "sequence", "sequence"),
    ("blastn_vdb", "blastn", "sequence", "vdb_reference"),
    ("tblastn_vdb", "psitblastn", "pssm", "vdb_read"),
    ("tblastn_vdb", "TBLASTN", "sequence", "vdb_mixed"),
])
def test_primary_formatter_qualified_tokens_preserve_originals(program, reported, query, reference):
    row = context(program, reported_program=reported, query_kind=query,
                  reference_kind=reference, native_version="future formatter version")
    assert row["reported_program"] == reported
    assert row["execution_program"] == program
    assert row["native_version"] == "future formatter version"


@pytest.mark.parametrize("program,changes,code", [
    ("unknown", {}, "execution_program_unsupported"),
    ("blastp", {"scientific_mode": "similarity"}, "scientific_mode_invalid"),
    ("psiblast", {"scientific_mode": "pairwise"}, "program_mode_unsupported"),
    ("blastp", {"query_kind": "msa"}, "program_query_kind_conflict"),
    ("deltablast", {"query_kind": "pssm"}, "program_query_kind_conflict"),
    ("rpsblast", {}, "program_reference_kind_conflict"),
    ("blastn_vdb", {}, "program_reference_kind_conflict"),
    ("blastp", {"reported_program": "psiblast"}, "reported_program_conflict"),
    ("rpsblast", {"reference_kind": "profile", "reported_program": "blastp"}, "reported_program_conflict"),
    ("psiblast", {"query_kind": "msa", "reported_program": "phiblastp"}, "reported_program_conflict"),
    ("blastp", {"reported_program": 1}, "reported_program_invalid"),
    ("blastp", {"native_version": []}, "native_version_invalid"),
])
def test_unestablished_or_conflicting_combinations_are_explicit(program, changes, code):
    with pytest.raises(ValueError, match="blast_" + code):
        context(program, **changes)
