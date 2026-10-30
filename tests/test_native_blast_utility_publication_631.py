"""Utility publication/custody fixtures; no native command is run here.

Producer histories and binary members below are controlled engineering fixtures.
Tests named retained_native_stream authenticate the original 084/085 stream bytes
from626, then use a controlled capture to verify this reader/publication boundary.
They establish native format handling, not an authentic new producer invocation.
All imports, fixture reads and worker processing run only inside runner529.
"""
from contextlib import redirect_stderr
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from gene_annotation_episode import blast_database_extraction as extraction
from gene_annotation_episode import blast_database_inspection as inspection
from gene_annotation_episode import blast_database_preparation as preparation
from gene_annotation_episode import native_blast_utility_acquisition as acquisition
from gene_annotation_episode import native_blast_utility_result_publication as publication
from gene_annotation_episode import native_blast_utility_result_worker as worker
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_blast_utility_contracts import (
    BUNDLE_VERSION, compile_native_blast_utility_job, database_file_selections,
    native_environment, producer_failure, staged_relative, validate_native_blast_utility_bundle,
)
from gene_annotation_episode.native_infernal_driver import _encoded
from gene_annotation_episode.practical_execution_state import _immutable
from gene_annotation_episode.state import Store
from test_native_blast_utility_producer_628 import FAMILY, POLICY, job_fixture, plan_fixture


READER_EVIDENCE = Path(__file__).resolve().parents[1] / "verification/tool_graders_blast_database_readers_2026-10-28_626"
EXTRACT = b"0\tlcl|ALPHA\tALPHA\t8\tACGTACGT\n"


def selector(**kwargs):
    return {"version": "native_blast_utility_result_selector_v1", "sequences": None,
        "database_fields": [], "integrity": None, "preparation": None,
        "prepared_database": False, "include_checks": False, "artifacts": [], "saved_data": [], **kwargs}


def retained_stream(name):
    provenance = json.loads((READER_EVIDENCE / "FIXTURE_PROVENANCE_001.json").read_text())
    row = next(row for row in provenance["cases"] if row["name"] == name)
    data = {}
    for key in ("stdout", "stderr"):
        data[key] = (READER_EVIDENCE / "fixtures" / name / (key + ".txt")).read_bytes()
        assert hashlib.sha256(data[key]).hexdigest() == row[key]["sha256"]
        assert len(data[key]) == row[key]["size_bytes"]
    return row, data


def capture_fixture(tmp_path, mode="extract_sequences", *, job=None, stdout=None, stderr=b"", returncode=0,
                    family=None, omit=()):
    """Explicit controlled original history; no producer or native invocation."""
    job = job_fixture(tmp_path, mode) if job is None else deepcopy(job)
    plan = plan_fixture(tmp_path, job)
    root = Path(plan["attempt_directory"])
    store = Store(tmp_path / "store")
    if stdout is None:
        stdout = EXTRACT if mode == "extract_sequences" else b"controlled utility fixture\n"
    family = deepcopy(FAMILY if family is None else family)
    if mode == "create_sequence_database" and family.get("njs") == FAMILY["njs"]:
        family["njs"] = json.dumps({"version": "1.2", "dbname": "tiny", "dbtype": "Nucleotide", "db-version": 5,
            "description": job["operation"]["parameters"]["title"], "last-updated": "fixture time",
            "number-of-sequences": 1, "number-of-letters": 8,
            "bytes-total": sum(len(v) for k, v in family.items() if k != "njs"),
            "files": ["tiny." + suffix for suffix in sorted(family) if suffix != "njs"]}).encode()
    bundle = {"version": BUNDLE_VERSION, "identity": plan["identity"], "requested_job": plan["requested_job"],
        "operation": job["operation"], "software": {"executable": job["software"]["executable"],
            "expected_sha256": job["software"]["sha256"], "actual_sha256": job["software"]["sha256"],
            "declared_engine_version": job["software"]["engine_version"]},
        "realized_argv": compile_native_blast_utility_job(job,
            input_paths={r["input_key"]: str(root / staged_relative(r)) for r in job["inputs"]},
            database_paths={r["database_key"]: r["native_paths"] for r in job["databases"]}, output_directory=str(root)),
        "environment": native_environment(job, root), "started": returncode is not None, "returncode": returncode,
        "writer_closed": True, "inventory_complete": True, "started_at": "2026-10-28T00:00:00+00:00",
        "finished_at": "2026-10-28T00:00:01+00:00", "inputs": [], "database_files": [], "artifacts": [],
        "failures": ([producer_failure("command_unavailable")] if returncode is None else
                     [producer_failure("nonzero_returncode")] if returncode else [])}
    raw_by_path = {}
    for row in job["inputs"]:
        data = Path(row["path"]).read_bytes()
        bundle["inputs"].append({"input_key": row["input_key"], "role": row["role"], "format": row["format"],
            "original_path": row["path"], "relative_path": staged_relative(row), "artifact_ref": row["artifact_ref"],
            **{prefix + "sha256": row["sha256"] for prefix in ("expected_", "staged_", "final_")},
            **{prefix + "size_bytes": row["size_bytes"] for prefix in ("expected_", "staged_", "final_")}})
        raw_by_path[row["path"]] = data
    for row in database_file_selections(job):
        bundle["database_files"].append({**row, "before_sha256": row["expected_sha256"], "final_sha256": row["expected_sha256"],
            "before_size_bytes": row["expected_size_bytes"], "final_size_bytes": row["expected_size_bytes"]})
        raw_by_path[row["original_path"]] = Path(row["original_path"]).read_bytes()
    native_outputs = [(r["role"], 0, r["relative_path"], r["format"], stdout if r["role"] == "stdout" else stderr)
                      for r in job["outputs"] if r["role"] != "database_family"]
    if mode == "create_sequence_database":
        prefix = job["operation"]["parameters"]["output_prefix"]
        native_outputs += [("database_metadata" if suffix in {"njs", "pjs"} else "database_file", ordinal,
            prefix + "." + suffix, "blastdb_metadata_json" if suffix in {"njs", "pjs"} else "blastdb_binary", data)
            for ordinal, (suffix, data) in enumerate(sorted(family.items()))]
    for role, ordinal, relative, fmt, data in native_outputs:
        bundle["artifacts"].append({"role": role, "ordinal": ordinal, "relative_path": relative, "format": fmt,
            "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data),
            "completeness": "complete" if returncode == 0 else "partial"})
        raw_by_path[str(root / relative)] = data
    bundle = validate_native_blast_utility_bundle(bundle, plan)
    capture = {"version": acquisition.VERSION, "source_ref": None, "plan": plan, "original_bundle": bundle,
        "bundle_artifact_ref": store.artifact(_encoded(bundle), "application/json"), "bundle_validated": True,
        "artifacts": [], "failures": []}
    for row in acquisition._selected_files(plan, bundle):
        if (row["direction"], row["role"], row["ordinal"]) in omit:
            capture["failures"].append(acquisition._failure("original_file_unavailable", row))
            continue
        data = raw_by_path[row["original_path"]]
        reference = store.artifact(data, "application/octet-stream")
        capture["artifacts"].append({k: row[k] for k in acquisition._ROW_FIELDS - {"artifact_ref"}} | {"artifact_ref": reference})
    capture["source_ref"] = store.put("source", acquisition._source_payload(capture), origin="tool")["id"]
    acquisition._validate_saved(store, capture)
    return store, capture


def inline_workers(monkeypatch):
    """Run deterministic worker code inside the already bounded529 test job."""
    calls = []
    def selected(command, **kwargs):
        assert command[1:3] == ["-m", "gene_annotation_episode.native_blast_utility_result_worker"]
        assert kwargs["policy"].to_dict() == POLICY
        plan = json.loads(Path(command[-1]).read_text())
        calls.append(deepcopy(plan))
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            result = worker.run(plan)
        kwargs["stdout_path"].write_text(json.dumps(result))
        kwargs["stderr_path"].write_text(stderr.getvalue())
        return SimpleNamespace(returncode=0 if result["completed"] else 1, metadata={"fixture": "bounded_inline_worker"})
    monkeypatch.setattr(publication, "run_local_job", selected)
    return calls


def prepare(store, capture, tmp_path):
    return publication.prepare_native_blast_utility_result(store, capture=capture,
        directory=tmp_path / "preparation", policy=LocalJobPolicy(**POLICY))


def publish(store, prepared, selected, tmp_path, *, name="projection"):
    return publication.publish_selected_utility_result(store, source_ref=prepared["source_ref"], prepared=prepared,
        selector=selected, directory=tmp_path / name, policy=LocalJobPolicy(**POLICY))


def payload(store, prepared):
    return json.loads(store.get_artifact(prepared["result_artifact_ref"]))


def forbid_readers(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("saved projection/replay reran a native reader or preparation calculation")
    for owner, names in ((extraction, ("parse_blastdbcmd_sequences",)),
            (inspection, ("parse_blast_database_inspection", "parse_blastdbcheck_diagnostics", "_metadata_fields")),
            (preparation, ("populate_database_artifact_set", "project_prepared_blast_database"))):
        for name in names:
            monkeypatch.setattr(owner, name, forbidden)


def test_selected_sequence_saved_projection_and_frozen_replay(tmp_path, monkeypatch):
    calls = inline_workers(monkeypatch)
    job = job_fixture(tmp_path, "extract_sequences")
    job["operation"]["parameters"]["selectors"] = [{"ordinal": i, "value": v} for i, v in enumerate(("ALPHA", "ALPHA", "MISSING"))]
    raw = EXTRACT + b"malformed\n" + EXTRACT
    store, capture = capture_fixture(tmp_path, job=job, stdout=raw)
    source_before = deepcopy(store.get(capture["source_ref"]))
    prepared = prepare(store, capture, tmp_path)
    assert prepared["worker_completed"] and len(calls) == 1
    result = payload(store, prepared)
    assert [r["native_row_ordinal"] for r in result["records"]] == [0, 2]
    assert result["missing_selector_ordinals"] == [2]
    selected = selector(sequences={"selector_ordinals": [1, 2], "sequence_fields": ["normalized_sequence"]}, include_checks=True,
        artifacts=[{"direction": "output", "role": "stdout", "ordinal": 0}], saved_data=["result"])
    forbid_readers(monkeypatch)
    output = publish(store, prepared, selected, tmp_path)
    assert len(calls) == 2 and output["status"]["state"] == "partial"
    assert [r["native_row_ordinal"] for r in output["sequences"]] == [0, 2]
    assert all(r["selector_ordinals"] == [1] and r["sequences"] == {"normalized_sequence": "ACGTACGT"}
               and r["returned_symbol_count"] == 8 for r in output["sequences"])
    assert output["record_refs"] == [capture["source_ref"], output["artifacts"][0]["artifact_ref"], prepared["result_artifact_ref"]]
    assert store.get(capture["source_ref"]) == source_before
    shutil.rmtree(tmp_path / "selected")
    monkeypatch.setattr(publication, "run_local_job", lambda *a, **k: pytest.fail("frozen replay launched a worker"))
    assert prepare(store, capture, tmp_path) == prepared
    assert publish(store, prepared, selected, tmp_path) == output
    assert publication.validate_utility_publication(store, source_ref=capture["source_ref"], prepared=prepared,
        selector=selected, publication=output) == output


def test_builder_manifest_and_explicit_receipt_grant(tmp_path, monkeypatch):
    inline_workers(monkeypatch)
    store, capture = capture_fixture(tmp_path, "create_sequence_database")
    prepared = prepare(store, capture, tmp_path)
    assert prepared["worker_completed"] and prepared["prepared_database_manifest_artifact_ref"] is not None
    result = payload(store, prepared)
    assert len([r for r in result["outputs"] if r["role"] in {"database_file", "database_metadata"}]) == len(FAMILY)
    assert result["compatibility"] == "unverified"
    assert result["identity"]["source"]["source_ref"] == capture["source_ref"]
    assert result["inputs"][0]["occurrence_id"] == "source"
    values = {r["field_name"]: r["value"] for r in result["native_metadata"]}
    assert (values["database_sequence_count"], values["database_residue_count"]) == (1, 8)
    manifest = json.loads(store.get_artifact(prepared["prepared_database_manifest_artifact_ref"]))
    receipt, = [r for r in prepared["occurrences"] if r["role"] == "preparation_receipt"]
    assert manifest["preparation"]["receipt"] == {"path": receipt["native_path"],
        **{k: receipt[k] for k in ("artifact_ref", "sha256", "size_bytes")}}
    assert receipt["artifact_ref"] == capture["bundle_artifact_ref"]
    assert manifest["preparation"]["input_manifest"] is None
    forbid_readers(monkeypatch)
    selected = selector(prepared_database=True, database_fields=["database_sequence_count"])
    facts_only = publish(store, prepared, selected, tmp_path)
    assert facts_only["record_refs"] == [capture["source_ref"]]
    selected.update(saved_data=["prepared_database", "result"],
        artifacts=[{"direction": "output", "role": "preparation_receipt", "ordinal": 0}])
    with_files = publish(store, prepared, selected, tmp_path, name="explicit-artifacts")
    assert with_files["saved_data"][0]["artifact_ref"] == prepared["prepared_database_manifest_artifact_ref"]
    assert with_files["saved_data"][0]["schema"] == manifest["version"]
    assert capture["bundle_artifact_ref"] in with_files["record_refs"]
    assert prepared["prepared_database_projection_artifact_ref"] not in with_files["record_refs"]


@pytest.mark.parametrize("mode,omit", [("extract_sequences", ("output", "stdout", 0)),
    ("integrity", ("output", "stderr", 0)), ("create_sequence_database", ("input", "sequence_input", 0))])
def test_missing_essential_capture_is_processed_without_a_result(tmp_path, monkeypatch, mode, omit):
    inline_workers(monkeypatch)
    store, capture = capture_fixture(tmp_path, mode, omit=[omit])
    prepared = prepare(store, capture, tmp_path)
    assert prepared["worker_completed"] and prepared["result_artifact_ref"] is None
    assert prepared["native_outcome"]["state"] == "succeeded"
    assert prepared["native_outcome"]["inventory_complete"] is False
    assert capture["original_bundle"]["inventory_complete"] is True
    chosen = selector(include_checks=True, saved_data=["result"])
    output = publish(store, prepared, chosen, tmp_path)
    assert output["status"]["state"] == "unavailable"
    assert {row["request"]["type"] for row in output["missing"]} == {"checks", "saved_data"}
    assert output["failures"]


def test_missing_builder_family_capture_cannot_create_reusable_manifest(tmp_path, monkeypatch):
    inline_workers(monkeypatch)
    store, capture = capture_fixture(tmp_path, "create_sequence_database", omit=[("output", "database_file", 0)])
    prepared = prepare(store, capture, tmp_path)
    assert prepared["worker_completed"] and prepared["result_artifact_ref"] is not None
    assert prepared["prepared_database_projection_artifact_ref"] is not None
    assert prepared["prepared_database_manifest_artifact_ref"] is None
    assert payload(store, prepared)["inventory_complete"] is False
    output = publish(store, prepared, selector(prepared_database=True), tmp_path)
    assert output["prepared_database"][0]["status"] == "unavailable"
    assert any(r["code"] == "output_inventory_incomplete" for r in output["failures"])


@pytest.mark.parametrize("returncode", [3, None])
def test_failed_native_outcome_stays_separate_from_completed_reading(tmp_path, monkeypatch, returncode):
    inline_workers(monkeypatch)
    store, capture = capture_fixture(tmp_path, stdout=EXTRACT, returncode=returncode)
    prepared = prepare(store, capture, tmp_path)
    assert prepared["worker_completed"] and prepared["native_outcome"]["state"] == "failed"
    output = publish(store, prepared, selector(sequences={"selector_ordinals": [0], "sequence_fields": ["original_sequence"]}), tmp_path)
    assert output["status"]["native_state"] == "failed" and output["sequences"][0]["returned_symbol_count"] == 8
    assert any(r["code"] == ("native_start_failed" if returncode is None else "native_nonzero_exit") for r in output["failures"])


@pytest.mark.parametrize("name,mode,expected", [("extract_dna_v5", "extract_sequences", [12, 12, 7]),
    ("range_past_end", "extract_sequences", [5]), ("info_dna_v5", "info", [3, 31]),
    ("metadata_dna_v5", "metadata", [3, 31]), ("v5_integrity_diagnostic", "integrity", None)])
def test_retained_native_stream_through_controlled_capture(tmp_path, monkeypatch, name, mode, expected):
    inline_workers(monkeypatch)
    original, streams = retained_stream(name)
    job = job_fixture(tmp_path, mode)
    argv = original["argv"]
    if mode == "extract_sequences":
        params = job["operation"]["parameters"]
        params["selectors"] = [{"ordinal": i, "value": value} for i, value in enumerate(argv[argv.index("-entry") + 1].split(","))]
        if "-range" in argv:
            start, end = map(int, argv[argv.index("-range") + 1].split("-"))
            params["range"] = {"start_1based": start, "end_1based": end}
        chosen = selector(sequences={"selector_ordinals": list(range(len(params["selectors"]))), "sequence_fields": ["original_sequence"]})
    elif mode in {"info", "metadata"}:
        chosen = selector(database_fields=["database_sequence_count", "database_residue_count"])
    else:
        chosen = selector(integrity={"fields": ["diagnostics", "observed_checked_count", "observed_population_count"]}, include_checks=True)
    store, capture = capture_fixture(tmp_path, mode, job=job, stdout=streams["stdout"], stderr=streams["stderr"], returncode=original["returncode"])
    prepared = prepare(store, capture, tmp_path)
    assert prepared["worker_completed"]
    result = payload(store, prepared)
    forbid_readers(monkeypatch)
    output = publish(store, prepared, chosen, tmp_path)
    if mode == "extract_sequences":
        assert [row["returned_symbol_count"] for row in output["sequences"]] == expected
        assert [row["native_row_ordinal"] for row in output["sequences"]] == [row["native_row_ordinal"] for row in result["records"]]
    elif mode in {"info", "metadata"}:
        by_name = {row["field_name"]: row for row in output["database_fields"]}
        assert [by_name[name]["value"] for name in ("database_sequence_count", "database_residue_count")] == expected
        assert by_name["database_residue_count"]["unit"] == "nt"
        assert [row["field_name"] for row in output["database_fields"]] == [
            row["field_name"] for row in result["native_fields"] if row["field_name"] in chosen["database_fields"]]
    else:
        assert output["status"]["native_state"] == "failed"
        assert any(row["code"] == "dependency_unavailable" for row in output["failures"])
        assert not any(row["code"] == "native_integrity_failure" for row in output["failures"])
        assert output["integrity"][0]["fields"]["observed_population_count"] is None


def test_same_bytes_preserve_occurrences_and_original_ordinals(tmp_path):
    store, capture = capture_fixture(tmp_path, "create_sequence_database", stdout=b"", stderr=b"")
    context = worker.qualified_utility_context(capture)
    streams = [r for r in context["occurrences"] if r["role"] in {"stdout", "stderr"}]
    assert streams[0]["artifact_ref"] == streams[1]["artifact_ref"]
    assert streams[0]["occurrence_id"] != streams[1]["occurrence_id"]
    assert [r["ordinal"] for r in context["occurrences"] if r["role"] == "database_file"] == [0, 1, 2, 3, 5]


@pytest.mark.parametrize("mutation", [lambda c: c["artifacts"][0].update(original_path="/unselected/file"),
    lambda c: c["artifacts"][0].update(ordinal=91), lambda c: c["artifacts"][0].update(size_bytes=991),
    lambda c: c["original_bundle"]["identity"].update(run_id="forged"),
    lambda c: c["artifacts"].append(deepcopy(c["artifacts"][0])),
    lambda c: c["artifacts"].pop(0)])
def test_qualified_context_rejects_wrong_original_associations(tmp_path, mutation):
    _, capture = capture_fixture(tmp_path)
    mutation(capture)
    with pytest.raises(ValueError):
        worker.qualified_utility_context(capture)


def test_source_only_selection_never_grants_auxiliary_artifacts(tmp_path, monkeypatch):
    inline_workers(monkeypatch)
    store, capture = capture_fixture(tmp_path)
    prepared = prepare(store, capture, tmp_path)
    output = publish(store, prepared, selector(), tmp_path)
    assert output["record_refs"] == [capture["source_ref"]]
    assert output["artifacts"] == output["saved_data"] == []
    assert capture["bundle_artifact_ref"] not in output["record_refs"]


@pytest.mark.parametrize("target", ["prepared", "publication", "selector", "source"])
def test_frozen_values_or_original_selection_tampering_rejects(tmp_path, monkeypatch, target):
    inline_workers(monkeypatch)
    store, capture = capture_fixture(tmp_path)
    prepared = prepare(store, capture, tmp_path)
    selected = selector(sequences={"selector_ordinals": [0], "sequence_fields": ["normalized_sequence"]})
    output = publish(store, prepared, selected, tmp_path)
    source = capture["source_ref"]
    if target == "prepared":
        prepared["worker_completed"] = False
    elif target == "publication":
        output["sequences"][0]["returned_symbol_count"] = 7
    elif target == "selector":
        selected["sequences"]["sequence_fields"] = ["original_sequence"]
    else:
        source = "source_unrelated"
    with pytest.raises(ValueError):
        publication.validate_utility_publication(store, source_ref=source, prepared=prepared, selector=selected, publication=output)


@pytest.mark.parametrize("which", ["original", "result", "projection"])
def test_changed_retained_bytes_reject_without_reparsing(tmp_path, monkeypatch, which):
    inline_workers(monkeypatch)
    store, capture = capture_fixture(tmp_path)
    prepared = prepare(store, capture, tmp_path)
    selected = selector(saved_data=["result"])
    output = publish(store, prepared, selected, tmp_path)
    ref = capture["artifacts"][0]["artifact_ref"] if which == "original" else (
        prepared["result_artifact_ref"] if which == "result" else output["projection_artifact_ref"])
    path = Path(publication._file(store, ref)["path"])
    path.write_bytes(path.read_bytes() + b" ")
    forbid_readers(monkeypatch)
    with pytest.raises(ValueError):
        publication.validate_utility_publication(store, source_ref=capture["source_ref"], prepared=prepared, selector=selected, publication=output)


def test_worker_failure_preserves_original_native_state_and_diagnostics(tmp_path, monkeypatch):
    inline_workers(monkeypatch)
    store, capture = capture_fixture(tmp_path)
    monkeypatch.setattr(extraction, "parse_blastdbcmd_sequences", lambda *a, **k: (_ for _ in ()).throw(ValueError("controlled_reader_failure")))
    prepared = prepare(store, capture, tmp_path)
    assert not prepared["worker_completed"] and prepared["result_artifact_ref"] is None
    assert prepared["native_outcome"]["state"] == "succeeded"
    assert any(row["stage"] == "parse" and row["code"] == "semantic_validation_unavailable" for row in prepared["failures"])
    stable = publication._stable(store, prepared)
    receipt = publication._json(store, stable["worker_receipt_artifact_ref"])
    assert receipt["manifest"]["completed"] is False
    assert any(b"controlled_reader_failure" in store.get_artifact(ref) for ref in receipt["diagnostic_artifact_refs"])
    monkeypatch.setattr(publication, "run_local_job", lambda *a, **k: pytest.fail("replay repeated failed worker"))
    assert prepare(store, capture, tmp_path) == prepared


def test_unfinished_preparation_intent_is_not_restarted(tmp_path, monkeypatch):
    store, capture = capture_fixture(tmp_path)
    directory = tmp_path / "preparation" / "native-blast-utility-preparation"
    directory.mkdir(parents=True)
    _immutable(directory / "intent.json", {"capture": capture, "policy": POLICY})
    monkeypatch.setattr(publication, "run_local_job", lambda *a, **k: pytest.fail("uncertain work restarted"))
    with pytest.raises(ContractError, match="original_result_work_incomplete"):
        prepare(store, capture, tmp_path)


def test_binary_custody_is_streamed_without_read_bytes(tmp_path, monkeypatch):
    inline_workers(monkeypatch)
    store, capture = capture_fixture(tmp_path, "create_sequence_database")
    binary_hashes = {r["sha256"] for r in capture["artifacts"] if r["format"] == "blastdb_binary"}
    original = worker._read_bytes
    def checked(descriptor):
        assert descriptor["sha256"] not in binary_hashes
        return original(descriptor)
    monkeypatch.setattr(worker, "_read_bytes", checked)
    assert prepare(store, capture, tmp_path)["worker_completed"]


def test_qualified_context_is_detached_and_does_not_read_files(tmp_path, monkeypatch):
    _, capture = capture_fixture(tmp_path)
    expected = worker.qualified_utility_context(capture)
    monkeypatch.setattr(Path, "open", lambda *a, **k: pytest.fail("pure context read a file"))
    monkeypatch.setattr(Path, "resolve", lambda *a, **k: pytest.fail("pure context resolved a native path"))
    value = worker.qualified_utility_context(capture)
    assert value == expected and value is not expected
    value["occurrences"][0]["native_path"] = "/changed"
    assert worker.qualified_utility_context(capture) == expected
