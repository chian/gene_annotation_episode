"""Captured-byte reporting and unchanged legacy replay for BLAST utilities.

No BLAST executable or database build runs here. Producer calls are explicit
engineering fixtures; the check096 diagnostic bytes and saved publication are
retained native evidence, authenticated against their original hashes.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from gene_annotation_episode import blast_database_extraction as extraction
from gene_annotation_episode import native_blast_utility_acquisition as acquisition
from gene_annotation_episode import native_blast_utility_driver as driver
from gene_annotation_episode import native_blast_utility_result_publication as publication
from gene_annotation_episode import native_blast_utility_result_worker as worker
from gene_annotation_episode.blast_utility_contracts import validate_blast_utility_record
from gene_annotation_episode.native_blast_utility_contracts import (
    native_blast_utility_output_completeness, producer_failure,
    validate_native_blast_utility_bundle,
)
from gene_annotation_episode.state import Store
from test_blast_utility_contracts_625 import binding, occurrence, operation, outcome
from test_native_blast_utility_producer_628 import (
    FAMILY, controlled_native, job_fixture, plan_fixture, reserved_fixture,
)
from test_native_blast_utility_publication_631 import (
    capture_fixture, forbid_readers, inline_workers, payload, prepare, publish, selector,
)


PACKET = Path(__file__).resolve().parents[1] / "verification/tool_graders_blast_utility_capture_semantics_2026-10-28_638"
FIXTURE = PACKET / "fixtures/check096-integrity"


def retained_case():
    provenance = json.loads((PACKET / "FIXTURE_PROVENANCE_001.json").read_text())
    for row in provenance["files"]:
        raw = (PACKET / row["retained_path"]).read_bytes()
        assert len(raw) == row["size_bytes"]
        assert hashlib.sha256(raw).hexdigest() == row["sha256"]
    return {name: json.loads((FIXTURE / (name + ".json")).read_text())
            for name in ("capture", "prepared", "publication")}


def failure_codes(result):
    return {row["code"] for row in result["failures"]}


@pytest.mark.parametrize("basis,returncode,closed,measured,expected", [
    ("captured_bytes", 7, True, True, "complete"),
    ("captured_bytes", 0, True, True, "complete"),
    ("captured_bytes", None, True, True, "complete"),
    ("captured_bytes", 7, True, False, "unknown"),
    ("captured_bytes", None, False, True, "unknown"),
    (None, 7, True, True, "partial"),
    (None, 0, True, True, "complete"),
    (None, None, True, True, "partial"),
    (None, 0, True, False, "unknown"),
    (None, None, False, True, "unknown"),
])
def test_completeness_means_captured_bytes_only_with_explicit_basis(
        basis, returncode, closed, measured, expected):
    bundle = {"writer_closed": closed, "returncode": returncode}
    if basis is not None:
        bundle["output_completeness_basis"] = basis
    before = deepcopy(bundle)
    assert native_blast_utility_output_completeness(bundle, measured) == expected
    assert bundle == before


@pytest.mark.parametrize("returncode", [0, 7, None])
def test_legacy_bundle_keeps_exact_missing_discriminator_semantics(tmp_path, returncode):
    _, capture = capture_fixture(tmp_path, returncode=returncode)
    bundle = capture["original_bundle"]
    before = deepcopy(bundle)
    assert "output_completeness_basis" not in bundle
    assert validate_native_blast_utility_bundle(bundle, capture["plan"]) == before
    assert bundle == before
    expected = "complete" if returncode == 0 else "partial"
    assert {row["completeness"] for row in bundle["artifacts"]} == {expected}
    if returncode != 0:
        forged = deepcopy(bundle)
        forged["artifacts"][0]["completeness"] = "complete"
        with pytest.raises(ValueError, match="bundle_output_completeness_conflict"):
            validate_native_blast_utility_bundle(forged, capture["plan"])


@pytest.mark.parametrize("basis", [None, "", "native_exit", 0, [], {}])
def test_unknown_discriminator_is_rejected_without_upgrading_legacy(tmp_path, basis):
    _, capture = capture_fixture(tmp_path)
    bundle = deepcopy(capture["original_bundle"])
    bundle["output_completeness_basis"] = basis
    with pytest.raises(ValueError, match="output_completeness_basis_invalid"):
        validate_native_blast_utility_bundle(bundle, capture["plan"])


def test_new_failed_bundle_cannot_forge_capture_or_lose_its_basis(tmp_path, monkeypatch):
    plan = plan_fixture(tmp_path)
    controlled_native(monkeypatch, returncode=7)
    bundle = driver.run_native_blast_utility(plan)
    assert bundle["output_completeness_basis"] == "captured_bytes"
    for change in (lambda b: b.pop("output_completeness_basis"),
                   lambda b: b["artifacts"][0].update(completeness="partial"),
                   lambda b: b["artifacts"][0].update(completeness="unknown")):
        forged = deepcopy(bundle)
        change(forged)
        with pytest.raises(ValueError, match="bundle_output_completeness_conflict"):
            validate_native_blast_utility_bundle(forged, plan)


def test_missing_stream_remains_unknown_with_complete_inventory(tmp_path, monkeypatch):
    plan = plan_fixture(tmp_path)
    def remove_stderr(argv, kwargs):
        Path(kwargs["stderr"].name).unlink()
    controlled_native(monkeypatch, returncode=7, after=remove_stderr)
    bundle = driver.run_native_blast_utility(plan)
    assert bundle["inventory_complete"] and bundle["writer_closed"]
    missing = next(row for row in bundle["artifacts"] if row["role"] == "stderr")
    assert missing["completeness"] == "unknown"
    assert missing["size_bytes"] is None and missing["sha256"] is None
    assert failure_codes(bundle) == {"nonzero_returncode", "missing_output"}
    assert all(row["completeness"] == "complete" for row in bundle["artifacts"] if row is not missing)
    missing["completeness"] = "complete"
    with pytest.raises(ValueError, match="bundle_output_completeness_conflict"):
        validate_native_blast_utility_bundle(bundle, plan)


def test_unclosed_writer_cannot_claim_complete_measured_output(tmp_path):
    _, capture = capture_fixture(tmp_path, "create_sequence_database")
    bundle = deepcopy(capture["original_bundle"])
    bundle.update(output_completeness_basis="captured_bytes", returncode=None,
                  writer_closed=False, inventory_complete=False, finished_at=None,
                  failures=[producer_failure("output_inventory_incomplete", relative_path="db/tiny")])
    for row in bundle["artifacts"]:
        row["completeness"] = "unknown"
    assert validate_native_blast_utility_bundle(bundle, capture["plan"]) == bundle
    bundle["artifacts"][0]["completeness"] = "complete"
    with pytest.raises(ValueError, match="bundle_output_completeness_conflict"):
        validate_native_blast_utility_bundle(bundle, capture["plan"])


@pytest.mark.parametrize("changes,completeness,expected", [
    ({"state": "failed", "returncode": 7}, "complete", {"native_nonzero_exit"}),
    ({"state": "failed", "returncode": None, "started": False}, "complete", {"native_start_failed"}),
    ({"state": "unknown", "returncode": None}, "complete", {"native_outcome_unavailable"}),
    ({}, "partial", {"output_completeness_unestablished"}),
    ({}, "unknown", {"output_completeness_unestablished"}),
    ({"inventory_complete": False}, "complete", {"output_inventory_incomplete"}),
    ({"state": "incomplete", "returncode": None, "inventory_complete": False}, "complete",
     {"native_outcome_unavailable", "output_inventory_incomplete"}),
    ({"state": "incomplete", "returncode": None, "writer_closed": False, "inventory_complete": False}, "unknown",
     {"native_outcome_unavailable", "output_inventory_incomplete", "output_writer_not_closed", "output_completeness_unestablished"}),
])
def test_native_inventory_writer_and_occurrence_qualifications_are_independent(changes, completeness, expected):
    native = validate_blast_utility_record("NativeOutcome", outcome(**changes))
    row = occurrence()
    row["completeness"] = completeness
    checks, failures = extraction._outcome_observations(native, [row], "tiny")
    assert {failure["code"] for failure in failures} == expected
    for failure in failures:
        validate_blast_utility_record("UtilityFailure", failure)
        assert failure["stage"] == ("native" if failure["code"].startswith("native_") else "capture")
    assert checks[0]["reason"] == ("native_outcome_unavailable" if native["state"] in {"unknown", "incomplete"}
        else "native_nonzero_exit" if native["state"] == "failed" and native["started"]
        else "native_start_failed" if native["state"] == "failed" else None)


def test_occurrence_qualification_identifies_the_actual_partial_stream():
    first, second = occurrence("stdout"), occurrence("stderr", role="stderr")
    second["completeness"] = "partial"
    _, failures = extraction._outcome_observations(outcome(), [first, second], "tiny")
    assert [(r["code"], r["occurrence_id"]) for r in failures] == [
        ("output_completeness_unestablished", "stderr")]


@pytest.mark.parametrize("completeness,newline,row_complete", [
    ("partial", False, False), ("unknown", False, False),
    ("partial", True, True), ("complete", False, True),
])
def test_partial_final_rows_preserve_symbols_without_false_inventory_failure(completeness, newline, row_complete):
    raw = b"0\tlcl|ALPHA\tALPHA\t8\tACGTACGT" + (b"\n" if newline else b"")
    row = occurrence(fmt="blastdbcmd_tabular_v1", data=raw)
    row["completeness"] = completeness
    result = extraction.parse_blastdbcmd_sequences(raw, occurrence=row, operation=operation(),
        database_binding=binding(), outcome=outcome(state="failed", returncode=7))
    record, = result["records"]
    assert record["original_sequence"] == "ACGTACGT" and record["returned_symbol_count"] == 8
    assert (record["completeness"] == "complete") == row_complete
    assert (record["effective_range"] is not None) == row_complete
    assert result["population_completeness"] == "partial_selection"
    assert "native_nonzero_exit" in failure_codes(result)
    assert "output_inventory_incomplete" not in failure_codes(result)
    if not row_complete:
        assert failure_codes(record) == {"output_completeness_unestablished"}


def test_new_captured_native_failure_reaches_publication_and_replays(tmp_path, monkeypatch):
    retained = retained_case()["capture"]
    streams = {r["role"]: (FIXTURE / "artifacts" / r["sha256"]).read_bytes()
               for r in retained["artifacts"] if r["direction"] == "output"}
    job = job_fixture(tmp_path, "integrity")
    _, handle, plan, target = reserved_fixture(tmp_path, monkeypatch, job=job)
    def use_retained_diagnostics(argv, kwargs):
        for role, raw in streams.items():
            kwargs[role].seek(0)
            kwargs[role].truncate()
            kwargs[role].write(raw)
    native_calls = controlled_native(monkeypatch, returncode=1, after=use_retained_diagnostics)
    bundle = driver.run_native_blast_utility(plan)
    assert len(native_calls) == 1 and bundle["returncode"] == 1
    assert {r["completeness"] for r in bundle["artifacts"]} == {"complete"}
    store = Store(tmp_path / "store")
    capture = acquisition.capture_local_utility_bundle(store, target=target, directory=tmp_path / "capture")
    assert capture["original_bundle"] == bundle and not capture["failures"]
    workers = inline_workers(monkeypatch)
    prepared = prepare(store, capture, tmp_path)
    result = payload(store, prepared)
    assert result["scope"] == "unknown" and result["observed_checked_count"] is None
    assert result["observed_population_count"] is None
    assert "native_nonzero_exit" in failure_codes(result)
    assert not {"output_inventory_incomplete", "output_writer_not_closed", "output_completeness_unestablished"} & failure_codes(result)
    assert any(r["category"] == "execution_failure" for r in result["diagnostics"])
    assert next(r for r in result["checks"] if r["name"] == "native_integrity")["status"] == "unknown"
    selected = selector(integrity={"fields": ["diagnostics", "observed_checked_count", "observed_population_count"]},
        include_checks=True, artifacts=[{"direction": "output", "role": role, "ordinal": 0} for role in ("stdout", "stderr")],
        saved_data=["result"])
    output = publish(store, prepared, selected, tmp_path)
    assert output["status"]["native_state"] == "failed" and output["status"]["inventory_complete"]
    assert output["integrity"][0]["fields"]["diagnostics"] == result["diagnostics"]
    assert all(r["completeness"] == "complete" for r in output["artifacts"])
    assert "output_inventory_incomplete" not in failure_codes(output)
    assert len(workers) == 2
    forbid_readers(monkeypatch)
    monkeypatch.setattr(publication, "run_local_job", lambda *a, **k: pytest.fail("replay started work"))
    shutil.rmtree(handle.path.parent)
    shutil.rmtree(tmp_path / "selected")
    assert prepare(store, capture, tmp_path) == prepared
    assert publish(store, prepared, selected, tmp_path) == output
    assert acquisition.capture_local_utility_bundle(store, target=target, directory=tmp_path / "capture") == capture


def test_complete_captured_failed_database_products_never_become_prepared_database(tmp_path, monkeypatch):
    _, _, plan, target = reserved_fixture(tmp_path, monkeypatch)
    controlled_native(monkeypatch, returncode=7, family={key: value for key, value in FAMILY.items() if key != "njs"})
    bundle = driver.run_native_blast_utility(plan)
    assert bundle["inventory_complete"] and all(r["completeness"] == "complete" for r in bundle["artifacts"])
    store = Store(tmp_path / "store")
    capture = acquisition.capture_local_utility_bundle(store, target=target, directory=tmp_path / "capture")
    inline_workers(monkeypatch)
    prepared = prepare(store, capture, tmp_path)
    result = payload(store, prepared)
    assert result["inventory_complete"] and result["original_outcome"]["state"] == "failed"
    assert result["compatibility"] == "unverified"
    assert failure_codes(result) == {"native_nonzero_exit"}
    projection = json.loads(store.get_artifact(prepared["prepared_database_projection_artifact_ref"]))
    assert projection["status"] == "unavailable" and projection["manifest"] is None
    assert "preparation_not_successful" in failure_codes(projection)
    assert prepared["prepared_database_manifest_artifact_ref"] is None
    output = publish(store, prepared, selector(prepared_database=True,
        preparation={"fields": ["inventory_complete", "compatibility"]}), tmp_path)
    assert output["prepared_database"][0]["status"] == "unavailable"
    assert output["preparation"][0]["fields"] == {"inventory_complete": True, "compatibility": "unverified"}


def test_check096_exact_saved_failed_publication_replays_without_reparsing(tmp_path, monkeypatch):
    retained = retained_case()
    capture, prepared, output = (retained[k] for k in ("capture", "prepared", "publication"))
    assert "output_completeness_basis" not in capture["original_bundle"]
    assert "output_inventory_incomplete" in failure_codes(output)  # Historical observation is preserved.
    assert {r["completeness"] for r in capture["original_bundle"]["artifacts"]} == {"partial"}
    store = Store(tmp_path / "saved-only-store")
    for path in (FIXTURE / "artifacts").iterdir():
        assert store.artifact(path.read_bytes()) == "artifact_" + path.name
    assert store.put("source", acquisition._source_payload(capture), origin="tool")["id"] == capture["source_ref"]
    forbid_readers(monkeypatch)
    def forbidden(*args, **kwargs):
        pytest.fail("saved replay executed work or reopened original native paths")
    for owner, name in ((publication, "run_local_job"), (worker, "run"), (driver, "run_native_blast_utility"),
                        (acquisition, "_capture_file"), (acquisition, "local_blast_utility_plan")):
        monkeypatch.setattr(owner, name, forbidden)
    before = deepcopy(retained)
    assert acquisition._validate_saved(store, capture) == capture
    assert publication.validate_prepared_utility_result(store, prepared) == prepared
    assert publication.validate_utility_publication(store, source_ref=capture["source_ref"], prepared=prepared,
        selector=output["selector"], publication=output) == output
    assert retained == before
    assert json.loads(store.get_artifact(capture["bundle_artifact_ref"])) == capture["original_bundle"]
    assert json.loads(store.get_artifact(prepared["result_artifact_ref"]))["original_outcome"]["returncode"] == 1
