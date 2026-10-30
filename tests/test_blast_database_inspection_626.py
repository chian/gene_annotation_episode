"""Saved native info/metadata/check diagnostics and synthetic adverse cases."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.blast_database_inspection import (
    parse_blast_database_inspection, parse_blastdbcheck_diagnostics,
)
from gene_annotation_episode.blast_utility_contracts import validate_blast_utility_record
from gene_annotation_episode.domain import ContractError


EVIDENCE = Path(__file__).resolve().parents[1] / "verification/tool_graders_blast_database_readers_2026-10-28_626"


def occurrence(data, fmt, *, role="stdout", complete="complete"):
    return {"occurrence_id": role, "direction": "output", "role": role, "ordinal": 0,
        "artifact_ref": "fixture:" + role, "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data), "native_format": fmt, "completeness": complete, "native_path": None}


def context(mode, *, molecule="dna", database_path="/explicit/database", returncode=0, full=True):
    parameters = ({"exact_length": True} if mode == "info" else {} if mode == "metadata" else
        {"full": full, "stride": None if full else 2, "random_count": None, "ends_count": None,
         "no_isam": False, "legacy_file_checks": False, "require_taxids": False, "cdd_delta": False})
    return {
        "operation": {"version": "blast_utility_operation_v1", "program": "blastdbcheck" if mode == "integrity" else "blastdbcmd",
            "mode": mode, "input_occurrence_ids": ["db-file"], "database_key": "db", "molecule": molecule, "parameters": parameters},
        "database_binding": {"database_key": "db", "kind": "blast_nucleotide_sequence" if molecule == "dna" else "blast_protein_sequence",
            "molecule": molecule, "identity": {"namespace": "explicit_fixture", "value": "db", "version": None, "release": None},
            "source_ref": "fixture:database", "native_paths": [database_path], "occurrence_ids": ["db-file"], "inventory_complete": True},
        "outcome": {"started": True, "returncode": returncode, "state": "succeeded" if returncode == 0 else "failed",
            "writer_closed": True, "inventory_complete": True},
    }


def native_case(name, mode):
    provenance = json.loads((EVIDENCE / "FIXTURE_PROVENANCE_001.json").read_text())
    row = next(row for row in provenance["cases"] if row["name"] == name)
    data = {}
    for stream in ("stdout", "stderr"):
        data[stream] = (EVIDENCE / "fixtures" / name / (stream + ".txt")).read_bytes()
        assert hashlib.sha256(data[stream]).hexdigest() == row[stream]["sha256"]
        assert len(data[stream]) == row[stream]["size_bytes"]
    argv = row["argv"]
    ctx = context(mode, molecule="dna" if argv[argv.index("-dbtype") + 1] == "nucl" else "protein",
                  database_path=argv[argv.index("-db") + 1], returncode=row["returncode"], full="-full" in argv)
    return data, ctx


def inspect(data, ctx):
    fmt = "blastdb_info_text" if ctx["operation"]["mode"] == "info" else "blastdb_metadata_json"
    return parse_blast_database_inspection(data, occurrence=occurrence(data, fmt), **ctx)


def integrity(stdout, stderr=b"", ctx=None):
    ctx = context("integrity") if ctx is None else ctx
    return parse_blastdbcheck_diagnostics(stdout, stderr,
        stdout_occurrence=occurrence(stdout, "blastdbcheck_text"),
        stderr_occurrence=occurrence(stderr, "text", role="stderr"), **ctx)


def fields(result):
    return {f["field_name"]: f for f in result["native_fields"]}


@pytest.mark.parametrize("database,version,count,residues,unit", [
    ("dna_v4", 4, 3, 31, "nt"), ("dna_v5", 5, 3, 31, "nt"), ("protein_v5", 5, 2, 35, "aa"),
])
@pytest.mark.parametrize("mode", ["info", "metadata"])
def test_authentic_native_database_information_retains_counts_units_locators(database, version, count, residues, unit, mode):
    native, ctx = native_case(mode + "_" + database, mode)
    result = inspect(native["stdout"], ctx)
    assert result["completeness"] == "complete" and result["failures"] == []
    values = fields(result)
    assert values["database_format_version"]["value"] == version
    assert values["database_sequence_count"]["value"] == count
    assert values["database_residue_count"]["value"] == residues
    assert values["database_residue_count"]["unit"] == unit
    if mode == "info":
        assert values["database_sequence_count"]["line_number"] == 2
        assert values["database_residue_count"]["value_basis"] == "native_reported_exact"
        assert values["database_volume_names"]["value"] == ctx["database_binding"]["native_paths"]
    else:
        assert values["database_residue_count"]["json_pointer"] == "/number-of-letters"
        assert values["database_bytes"]["value"] == {"dna_v4": 900, "dna_v5": 50114, "protein_v5": 50024}[database]
        assert all(not p.startswith("/") for p in values["database_file_names"]["value"])
    saved = json.loads(json.dumps(result))
    assert validate_blast_utility_record("DatabaseInspection", saved) == result
    copied = validate_blast_utility_record("DatabaseInspection", saved)
    copied["native_fields"][0]["value"] = "changed"
    assert saved == result


def test_synthetic_info_without_exact_length_does_not_claim_exact_residue_total():
    native, ctx = native_case("info_dna_v5", "info")
    ctx["operation"]["parameters"]["exact_length"] = False
    result = inspect(native["stdout"], ctx)
    assert fields(result)["database_residue_count"]["value_basis"] == "native_reported"


def test_synthetic_duplicate_conflicting_json_members_are_preserved():
    native, ctx = native_case("metadata_dna_v5", "metadata")
    data = native["stdout"].rstrip()[:-1] + b', "number-of-sequences": 999 }'
    result = inspect(data, ctx)
    rows = [f for f in result["native_fields"] if f["field_name"] == "database_sequence_count"]
    assert [f["value"] for f in rows] == [3, 999]
    assert all(f["json_pointer"] == "/number-of-sequences" for f in rows)
    assert "database_metadata_conflict" in {f["code"] for f in result["failures"]}
    assert result["completeness"] == "partial"


@pytest.mark.parametrize("value", [b"true", b"-1", b'"three"', b"NaN"])
def test_synthetic_invalid_metadata_count_keeps_prior_valid_members(value):
    native, ctx = native_case("metadata_dna_v5", "metadata")
    data = native["stdout"].replace(b'"number-of-sequences": 3', b'"number-of-sequences": ' + value)
    result = inspect(data, ctx)
    assert fields(result)["database_residue_count"]["value"] == 31
    count = fields(result).get("database_sequence_count")
    assert count is None or (count["value"] is None and count["missing_reason"] == "native_field_invalid")
    assert result["completeness"] == "partial"


def test_synthetic_truncated_json_keeps_complete_preceding_fields():
    native, ctx = native_case("metadata_dna_v4", "metadata")
    data = native["stdout"].split(b'"files"')[0] + b'"files": ["database.nhr",'
    result = inspect(data, ctx)
    assert fields(result)["database_sequence_count"]["value"] == 3
    assert fields(result)["database_residue_count"]["value"] == 31
    assert "database_file_names" not in fields(result)
    assert result["completeness"] == "partial"


@pytest.mark.parametrize("mode", ["info", "metadata"])
def test_synthetic_molecule_conflict_keeps_native_units(mode):
    native, ctx = native_case(mode + "_protein_v5", mode)
    wrong = context(mode)
    result = inspect(native["stdout"], wrong)
    assert fields(result)["database_residue_count"]["unit"] == "aa"
    assert fields(result)["database_residue_count"]["value"] == 35
    assert "database_kind_conflict" in {f["code"] for f in result["failures"]}


def test_synthetic_conflicting_info_counts_have_original_line_positions():
    native, ctx = native_case("info_dna_v5", "info")
    result = inspect(native["stdout"] + b"\t9 sequences; 90 total bases\n", ctx)
    rows = [f for f in result["native_fields"] if f["field_name"] == "database_sequence_count"]
    assert [r["value"] for r in rows] == [3, 9]
    assert [r["line_number"] for r in rows] == [2, 10]
    assert result["completeness"] == "partial"


def test_synthetic_unrecognized_or_prepared_manifest_is_not_native_metadata():
    result = inspect(b'{"prepared_manifest":true,"database_sequence_count":7}', context("metadata"))
    assert result["native_fields"] == [] and result["completeness"] == "unknown"


@pytest.mark.parametrize("name", ["integrity_full", "integrity_stride"])
def test_authentic_summary_exception_does_not_prove_database_corruption_or_counts(name):
    native, ctx = native_case(name, "integrity")
    result = integrity(native["stdout"], native["stderr"], ctx)
    assert result["scope"] == "unknown"
    assert result["observed_checked_count"] is None
    assert result["observed_population_count"] is None
    assert result["observed_sampled_oids"] is None and result["realized_seed"] is None
    assert not any(d["category"] == "check_failure" for d in result["diagnostics"])
    check = next(c for c in result["checks"] if c["name"] == "native_integrity")
    assert check["status"] == "unknown"


@pytest.mark.parametrize("name", ["v4_integrity_full", "v5_integrity_diagnostic"])
def test_authentic_detailed_checks_preserve_three_passes_and_dependency_failure(name):
    native, ctx = native_case(name, "integrity")
    result = integrity(native["stdout"], native["stderr"], ctx)
    assert result["scope"] == "unknown"
    assert result["observed_checked_count"] == 3
    assert result["observed_population_count"] is None
    assert [d["native_oid"] for d in result["diagnostics"] if d["category"] == "check_pass" and d["native_oid"] is not None] == [0, 1, 2]
    assert "dependency_unavailable" in {f["code"] for f in result["failures"]}
    check = next(c for c in result["checks"] if c["name"] == "native_integrity")
    assert check["status"] == "unknown" and check["reason"] == "dependency_unavailable"
    assert validate_blast_utility_record("DatabaseIntegrity", json.loads(json.dumps(result))) == result


def synthetic_summary(policy, *, volume_count=1):
    """Source-grammar counterexample, never an actual successful native check."""
    return (f"{policy}\nTesting {volume_count} volume(s).\n"
            f" Result=SUCCESS. No errors reported for {volume_count} volume(s).\n"
            "Testing 0 alias(es).\n Result=SUCCESS. No errors reported for 0 alias(es).\n").encode()


def test_synthetic_full_success_requires_native_full_report_and_leaves_count_unknown():
    result = integrity(synthetic_summary("Using `full' mode: every OID will be tested."))
    assert result["scope"] == "all_sequences"
    assert result["observed_checked_count"] is None
    assert result["observed_population_count"] is None
    assert next(c for c in result["checks"] if c["name"] == "native_integrity")["status"] == "pass"


@pytest.mark.parametrize("data", [b"", b"Using `full' mode: every OID will be tested.\n",
    synthetic_summary("Using `full' mode: every OID will be tested.", volume_count=0)])
def test_synthetic_zero_exit_or_requested_full_alone_is_not_full_integrity(data):
    result = integrity(data)
    assert result["scope"] == "unknown"
    assert next(c for c in result["checks"] if c["name"] == "native_integrity")["status"] == "unknown"


def test_synthetic_sample_summary_does_not_use_requested_count_as_observed_count():
    ctx = context("integrity", full=False)
    ctx["operation"]["parameters"].update(stride=None, random_count=100)
    result = integrity(synthetic_summary("Testing 100 randomly sampled OIDs."), ctx=ctx)
    assert result["scope"] == "selected_sample"
    assert result["observed_checked_count"] is None
    assert result["observed_sampled_oids"] is None and result["realized_seed"] is None


def test_synthetic_sample_oid_statuses_report_actual_distinct_observed_rows():
    data = synthetic_summary("Testing every 2-th OID.") + (
        b" /explicit/database / Stride: Status for OID 0: PASS\n"
        b" /explicit/database / Stride: Status for OID 2: PASS\n")
    result = integrity(data, ctx=context("integrity", full=False))
    assert result["scope"] == "selected_sample"
    assert result["observed_checked_count"] == 2
    assert result["observed_sampled_oids"] == [0, 2]


def test_synthetic_sequence_failure_is_distinct_from_missing_input_failure():
    data = (b"Using `full' mode: every OID will be tested.\nTesting 1 volume(s).\n"
            b"/explicit/database / Stride: Status for OID 0: FAIL\n"
            b"Result=FAILURE. 1 errors reported in 1 volume(s).\n")
    result = integrity(data, ctx=context("integrity", returncode=1))
    assert result["observed_checked_count"] == 1 and result["scope"] == "unknown"
    assert next(c for c in result["checks"] if c["name"] == "native_integrity")["status"] == "fail"
    assert "native_integrity_failure" in {f["code"] for f in result["failures"]}
    missing = integrity(b"", b"BLAST Database error: No alias or index file found\n", context("integrity", returncode=2))
    assert not any(d["category"] == "check_failure" for d in missing["diagnostics"])
    assert next(c for c in missing["checks"] if c["name"] == "native_integrity")["status"] == "unknown"


def test_synthetic_unknown_or_wrong_database_diagnostic_prevents_full_pass():
    data = synthetic_summary("Using `full' mode: every OID will be tested.") + b"unrecognized native warning\n"
    assert integrity(data)["scope"] == "unknown"
    wrong = synthetic_summary("Using `full' mode: every OID will be tested.") + b"/wrong/database / Stride: Status for OID 0: PASS\n"
    assert integrity(wrong)["scope"] == "unknown"


def test_synthetic_partial_capture_never_claims_completed_integrity():
    data = synthetic_summary("Using `full' mode: every OID will be tested.")
    ctx = context("integrity")
    ctx["outcome"] = {"started": True, "returncode": None, "state": "incomplete", "writer_closed": False, "inventory_complete": False}
    result = parse_blastdbcheck_diagnostics(data, b"", stdout_occurrence=occurrence(data, "blastdbcheck_text", complete="partial"),
        stderr_occurrence=occurrence(b"", "text", role="stderr", complete="partial"), **ctx)
    assert result["scope"] == "unknown"


def test_inspection_custody_rejects_changed_bytes_and_never_opens_database_paths():
    native, ctx = native_case("metadata_dna_v5", "metadata")
    ctx["database_binding"]["native_paths"] = ["/does/not/exist"]
    assert inspect(native["stdout"], ctx)["completeness"] == "complete"
    descriptor = occurrence(native["stdout"], "blastdb_metadata_json")
    with pytest.raises(ContractError, match="input_identity_mismatch"):
        parse_blast_database_inspection(native["stdout"] + b"x", occurrence=descriptor, **ctx)
