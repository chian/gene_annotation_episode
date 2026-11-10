"""Authentic distributed HMMER2 files and a separately selected H3 profile run.

The original 585 acquisition failure is preserved: its verifier incorrectly
expected exact binary probability identity. No test here downloads or calibrates
anything. A genuine native profile case requires its own explicit gate.
"""
from copy import deepcopy
import asyncio
import hashlib
import json
import os
from pathlib import Path
import socket

import pytest

from gene_annotation_episode.hmmer_model_data import extract_hmmer_models
from gene_annotation_episode.hmmer_preparation_result_views import _hmmer2_evd_quantity
from test_hmmer2_upstream_fixtures import compare_native_pair


FIXTURES = Path(__file__).parent / "fixtures/hmmer2"
PINS = {
    "fn3-bin": ("d1d230743ecb250fbc75fa5d719d8217a17fc9b3b13b770fb8bbbe1130317add", 16930, "hmmer_binary"),
    "fn3-bin-swap": ("93e30121fe04413b503cccce3463535b202b9886cb8c08567df7f766e26f4f23", 16930, "hmmer_binary"),
    "rrm.hmm": ("053383f3c8aa4cea15ab546d4f529b99826d2de37b73f472b192ccceeb78985b", 29502, "hmmer2_ascii"),
}


def native_fixture(name):
    raw = (FIXTURES / name).read_bytes()
    sha256, size, format = PINS[name]
    assert hashlib.sha256(raw).hexdigest() == sha256 and len(raw) == size
    return raw, format


def database_rows(store):
    tables = [row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    return {name: sorted([tuple(row) for row in store.db.execute('SELECT * FROM "' + name.replace('"', '""') + '"')], key=repr)
        for name in tables}


def test_actual_distributed_native_binary_conflict_and_saved_evd_view_without_network_or_calculation(tmp_path, monkeypatch):
    receipt_raw = (FIXTURES / "SOURCE_RECEIPT.json").read_bytes()
    assert hashlib.sha256(receipt_raw).hexdigest() == "264591dac5fb2ec67f54d30c1457e5716772df1d4ad5f88eaff5c7459eab6b57"
    receipt = json.loads(receipt_raw)
    assert len(receipt["wire_calls"]) == 3
    records, retained_pins = {}, {}
    for name in PINS:
        raw, format = native_fixture(name)
        entry = next(row for row in receipt["assets"] if row["filename"] == name)
        transport = entry["snapshot"]["transport"]
        assert entry["sha256"] == PINS[name][0] and entry["size_bytes"] == PINS[name][1]
        assert transport["status"] == 200 and transport["body_complete"] is True
        assert transport["observed_body_bytes"] == transport["retained_body_bytes"] == len(raw)
        occurrence = {"occurrence_id": "upstream/" + name, "direction": "input", "role": "models", "ordinal": 0,
            "artifact_ref": str((FIXTURES / name).resolve()), "sha256": PINS[name][0],
            "size_bytes": len(raw), "completeness": "complete"}
        extraction = extract_hmmer_models(raw, occurrence=occurrence, format=format)
        assert extraction["population"] == {"decoded_count": 1, "complete": True, "state": "decoded"}
        assert extraction["issues"] == [] and extraction["records"][0]["terminated"] is True
        records[name] = extraction["records"][0]
        retained_pins[name] = {"sha256": PINS[name][0], "size_bytes": len(raw)}
    conflicts = compare_native_pair(records["fn3-bin"], records["fn3-bin-swap"])
    assert {records[name]["representation"]["byte_order"] for name in ("fn3-bin", "fn3-bin-swap")} == {"little", "big"}
    rrm = records["rrm.hmm"]
    assert rrm["engine_text"] == "[2.2g]" and rrm["length"] == 77 and rrm["sequence_count"] == 90
    assert rrm["representation"]["legacy"]["evd"][0]["tokens"] == ["-44.976292", "0.254831"]
    saved = deepcopy(records)
    def forbidden(*args, **kwargs):
        raise AssertionError("saved EVD inspection attempted input bytes, parsing, math or network")
    with monkeypatch.context() as guard:
        guard.setattr("builtins.open", forbidden)
        guard.setattr("gene_annotation_episode.hmmer_model_data.extract_hmmer_models", forbidden)
        guard.setattr("gene_annotation_episode.hmmer_model_calculations.calculate_hmmer_model_components", forbidden)
        guard.setattr("socket.socket", forbidden)
        values = [_hmmer2_evd_quantity(rrm, path) for path in ("calibration.EVD.mu", "calibration.EVD.lambda")]
        absent = [_hmmer2_evd_quantity(records[name], "calibration.EVD.mu") for name in ("fn3-bin", "fn3-bin-swap")]
    assert records == saved
    assert [(row["value"], row["state"], row["unit"]) for row in values] == [
        (-44.976292, "present", "bit"), (0.254831, "present", "inverse_bit")]
    assert [(row["value"], row["state"]) for row in absent] == [(None, "missing")] * 2
    for name in PINS:
        native_fixture(name)
    (tmp_path / "HMMER2_RETAINED_NATIVE_VERIFICATION.json").write_text(json.dumps({
        "version": "hmmer2_retained_native_fixture_verification_v1", "fixture_pins": retained_pins,
        "binary_native_field_conflicts": conflicts, "remaining_native_fields_equal": True,
        "native_EVD_saved_values": values, "native_EVD_original_tokens": ["-44.976292", "0.254831"],
        "new_HTTP_requests": 0, "HMMER_execution_or_recalibration": False,
        "Store_custody_or_typed_Workflow_verified": False,
        "original_585_capture_failure_preserved": receipt["original_capture_proof"],
    }, indent=2, allow_nan=False) + "\n")


def test_opt_in_actual_admitted_rrm_h3_fetch_input_evd_typed_saved_and_closed_replay(tmp_path, monkeypatch):
    supplied = os.environ.get("HMMER_NATIVE_ORACLE_HMMER2_PROFILE_JSON")
    if supplied is None:
        pytest.skip("requires one explicitly selected native H3 fetch of the retained H2 input")
    assert json.loads(supplied) == {"enabled": True, "program": "hmmfetch", "mode": "single_key", "key": "rrm",
        "input_sha256": PINS["rrm.hmm"][0]}
    from gene_annotation_episode import native_lifecycle
    from gene_annotation_episode import native_hmmer_preparation_worker as worker
    from gene_annotation_episode.communication import plain
    from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
    from gene_annotation_episode.hmmer_preparation_result_views import project_preparation_result
    from gene_annotation_episode.native_file_capture import _metadata
    from gene_annotation_episode.native_infernal_contracts import native_infernal_digest
    from gene_annotation_episode.tools import ToolRegistry
    from gene_annotation_episode.native_hmmer_preparation_contracts import JOB_VERSION
    from test_native_hmmer_preparation_contracts import BIN
    from test_hmmer2_upstream_fixtures import checkpoint
    from test_native_hmmer_preparation_workflow import (
        run_case, assert_accounting, assert_native_custody, read_retained,
    )

    proof_path = tmp_path / "HMMER2_NATIVE_TYPED_PROFILE.json"
    proof = {"version": "hmmer2_input_native_h3_profile_proof_v1", "phase": "prepared",
        "scripted_model_decisions": True, "external_model_calls": 0,
        "native_H2_program_or_calibration_executed": False, "whole_model_basis_equivalence_asserted": False,
        "selected_input_format": "hmmer2_ascii", "selected_execution_engine": "HMMER3.4",
        "fixture_source_receipt_sha256": "264591dac5fb2ec67f54d30c1457e5716772df1d4ad5f88eaff5c7459eab6b57"}
    checkpoint(proof_path, proof)
    def make_job(store):
        raw, format = native_fixture("rrm.hmm")
        reference = store.artifact(raw, "text/plain")
        metadata = _metadata(store, reference)
        assert metadata["sha256"] == PINS["rrm.hmm"][0] and metadata["size"] == len(raw)
        file = {"artifact_ref": reference, "sha256": metadata["sha256"], "size_bytes": metadata["size"], "format": format}
        path = store.path / "artifacts" / metadata["sha256"][:2] / metadata["sha256"]
        executable = BIN / "hmmfetch"
        executable_sha256 = hashlib.sha256(executable.read_bytes()).hexdigest()
        assert executable_sha256 == "87a57888d9bb60fd4be66dc382c7f72d29f0fa1f87e10d012703e6b66da0afb0"
        job = {"version": JOB_VERSION, "program": "hmmfetch", "mode": "single_key",
            "software": {"executable": str(executable), "sha256": executable_sha256, "engine_version": "3.4"},
            "environment": {}, "operands": [{"role": "models", "ordinal": 0, "path": str(path), **file}],
            "options": [], "outputs": [
                {"role": "stdout", "format": "hmmer_stdout", "relative_path": "outputs/stdout"},
                {"role": "stderr", "format": "hmmer_stderr", "relative_path": "outputs/stderr"},
                {"role": "fetched_models", "format": "hmmer3_ascii", "relative_path": "outputs/fetched_models"}],
            "key": "rrm", "input_metadata": {}, "grading_parameters": {}}
        proof.update(phase="actual_supplied_File_registered_before_assignment", input_file=file,
            store_directory=str(store.path), selected_pending_job=deepcopy(job))
        checkpoint(proof_path, proof)
        return job, [reference]
    def before_collection(store, plan):
        # This callback runs only after the existing helper waited on the actual
        # original handle. Preserve it before any later verifier can fail.
        proof.update(phase="original_native_handle_returned_before_collection",
            original_native_plan=deepcopy(plan), original_execution_id=plan["identity"]["execution_id"])
        checkpoint(proof_path, proof)
    selector = {"version": "native_hmmer_preparation_result_selector_v1", "acquisition": "complete_bound_bundle",
        "projection": {"collection": "input_records", "rows": {"offset": 0, "limit": 1},
            "quantities": ["calibration.EVD.mu", "calibration.EVD.lambda"], "checks": []}, "artifacts": []}
    case = run_case(tmp_path, "hmmfetch", "single_key", selectors=[selector],
        job_factory=make_job, before_collection=before_collection, form_options={"references": True, "failures": True})
    try:
        body, bundle, sheet, calculations = read_retained(case)
        proof.update(phase="actual_profile_collected_before_postchecks", original_result=deepcopy(body),
            typed_return=deepcopy(case.returned[0]), selected_resource=deepcopy(case.job["software"]))
        checkpoint(proof_path, proof)
        parent, received = assert_accounting(case)
        assert_native_custody(case, bundle)
        assert body["complete"] is True and bundle["returncode"] == 0
        assert case.job["operands"][0]["artifact_ref"] == proof["input_file"]["artifact_ref"]
        assert bundle["requested_job"] == case.request
        records = EpisodeReturnRecords(case.store, case.owner.run_id, failure_prefix="hmmer2_profile_")
        admission = records.file_admission_before(parent, proof["input_file"]["artifact_ref"], "artifact",
            proof["input_file"]["artifact_ref"], 0)
        assert admission["baseline"] is True and admission["delivery"] is None
        row, = case.returned[0]["rows"]
        assert row["source_ref"] == body["source_ref"]
        assert [(q["value"], q["state"], q["unit"]) for q in row["quantities"]] == [
            (-44.976292, "present", "bit"), (0.254831, "present", "inverse_bit")]
        original_model, = sheet["input_records"]
        assert original_model["format_tag"] == "HMMER2.0" and original_model["engine_text"] == "[2.2g]"
        assert original_model["representation"]["legacy"]["evd"][0]["tokens"] == ["-44.976292", "0.254831"]
        assert sheet["output_records"] and all(model["format_tag"].startswith("HMMER3/") for model in sheet["output_records"])
        source = case.store.get(body["source_ref"])
        assert source["record_type"] == "source"
        assert case.owner.native_hmmer_preparation_returns.received_facts(parent, case.forms[0])[
            "execution_hmmer_preparation_rows"] == case.returned[0]["rows"]
        known = set(case.flow.receipts.known(parent.episode_id))
        for key in ("sheet_artifact_ref", "calculations_artifact_ref"):
            reference = body["prepared"][key]
            assert reference not in known and not case.flow.resolver(plain(parent.scope), context=parent)(reference, "artifact")
        # Save projection is a literal read of the authenticated original D1
        # grading, not another result worker, parser, model conversion or math.
        grading = json.loads(case.store.get_artifact(body["prepared"]["grading_artifact_ref"]))
        selected = deepcopy(selector)
        selected["projection"]["quantities"].reverse()
        original_grading = deepcopy(grading)
        def forbidden(*args, **kwargs):
            raise AssertionError("saved/closed proof attempted a new native action, parser, math or model decision")
        original_socket = socket.socket
        def local_socket(*args, **kwargs):
            family = args[0] if args else kwargs.get("family", socket.AF_INET)
            if family != socket.AF_UNIX:
                forbidden()
            return original_socket(*args, **kwargs)
        before_actions = [tuple(r) for r in case.store.db.execute("SELECT * FROM runtime_actions ORDER BY rowid")]
        before_observations = [tuple(r) for r in case.store.db.execute("SELECT * FROM runtime_observations ORDER BY rowid")]
        before_models = [tuple(r) for r in case.store.db.execute("SELECT * FROM runtime_model_calls ORDER BY rowid")]
        before_rows = database_rows(case.store)
        with monkeypatch.context() as guard:
            guard.setattr(worker, "grade_hmmer_preparation", forbidden)
            guard.setattr(worker, "recalculate_hmmer_preparation", forbidden)
            guard.setattr("gene_annotation_episode.hmmer_model_data.extract_hmmer_models", forbidden)
            for name in ("prepare_job", "resume_start", "start_job", "status", "collect", "wait_job"):
                guard.setattr(native_lifecycle, name, forbidden)
            guard.setattr("subprocess.Popen", forbidden)
            guard.setattr(socket, "socket", local_socket)
            saved = project_preparation_result(grading, selector=selected,
                source_ref=body["source_ref"], occurrences=body["prepared"]["occurrences"])
            cached = asyncio.run(case.owner.execute(case.contexts[0], "execution.results.collect", {}, body["operation_key"]))
            assert cached == {key: value for key, value in case.outcomes[0].items() if key != "pending_work_after_action"}
            guard.setattr(case.provider, "complete", forbidden)
            guard.setattr(ToolRegistry, "execute", forbidden)
            guard.setattr(ToolRegistry, "_execute_operation_async", forbidden)
            closed = asyncio.run(case.root.run_async(case.flow.context))
            asyncio.run(case.root.build_result(closed))
        assert grading == original_grading
        assert [q["value"] for q in saved["rows"][0]["quantities"]] == [0.254831, -44.976292]
        assert [tuple(r) for r in case.store.db.execute("SELECT * FROM runtime_actions ORDER BY rowid")] == before_actions
        assert [tuple(r) for r in case.store.db.execute("SELECT * FROM runtime_observations ORDER BY rowid")] == before_observations
        assert [tuple(r) for r in case.store.db.execute("SELECT * FROM runtime_model_calls ORDER BY rowid")] == before_models
        assert database_rows(case.store) == before_rows
        assert case.store.count("observation") == 0
        proof.update(phase="native_input_EVD_typed_saved_and_closed_verified", complete=True,
            original_source=source, source_record_sha256=native_infernal_digest(source), input_admission=admission,
            received_groups=received, saved_literal_projection=saved, cached_action_equal=True,
            closed_replay_created_actions=0, closed_replay_created_model_calls=0,
            saved_cache_and_closed_replay_all_logical_rows_unchanged=True,
            native_attempt_count=1, HMMER3_output_conversion_retained=True,
            original_H2_input_is_not_asserted_equivalent_to_H3_model=True)
        checkpoint(proof_path, proof)
    finally:
        checkpoint(proof_path, proof)
        case.store.close()


def _phase_validation_helpers(run_root):
    """Exercise the actual stdlib harness validators without its CLI or lifecycle.

    These are engineered control-document tests, with no Store, Source, native
    execution, or claim that their tiny fixture is an application deployment.
    """
    import ast
    filename = Path(__file__).parent / "bounded_execution/run_checks.py"
    module = ast.parse(filename.read_bytes(), filename=str(filename))
    names = {"pin", "authenticated_attempt", "selected_native_handle"}
    definitions = [node for node in module.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in definitions} == names
    namespace = {"Path": Path, "json": json, "hashlib": hashlib, "RUNS": run_root}
    exec(compile(ast.Module(body=definitions, type_ignores=[]), str(filename), "exec"), namespace)
    return namespace


def _phase_control_fixture(tmp_path):
    """Write literal engineering controls only; no lifecycle function is called."""
    run_root = tmp_path / "runs"
    attempt = run_root / "original"
    snapshot = attempt / "source_snapshot"
    snapshot.mkdir(parents=True)
    source = snapshot / "engineering.py"
    source.write_bytes(b"engineered bounded-harness pin input\n")
    helpers = _phase_validation_helpers(run_root)
    pin = helpers["pin"]
    def save(path, value):
        path.write_text(json.dumps(value, allow_nan=False) + "\n")
    outer_unit = "gene-local-job-engineering-outer.service"
    save(attempt / "handle.json", {"unit": outer_unit})
    receipt = {"terminal": True, "quiescent": True, "returncode": 1,
        "handle": str(attempt / "handle.json"), "unit": outer_unit,
        **{key + "_unchanged": True for key in (
            "source", "dependency", "stdlib", "binary", "selected_stdlib_source")}}
    audit = {"pytest_returncode": 1, "outside_modules": [], "unbound_mappings": [],
        "native_unchanged": True, "original_retained_fixtures_unchanged": True}
    save(attempt / "receipt.json", receipt)
    save(attempt / "execution_audit.json", audit)
    for name in ("source_pins_before", "dependency_pins_before", "stdlib_pins_before",
                 "binary_pins_before", "selected_stdlib_source_pins", "native_library_pins_before"):
        save(attempt / (name + ".json"), [pin(source)] if name == "source_pins_before" else [])
    directory = attempt / "native"
    directory.mkdir()
    paths = {name: str(directory / name) for name in ("request", "ready", "release", "status", "result", "launcher")}
    unit = "gene-local-job-engineering-inner.service"
    request = {"command": ["/explicit/engineering/python", "-c", "pass"], "cwd": str(directory),
        "file_bytes": 4294967296, "ready_path": paths["ready"], "release_path": paths["release"],
        "result_path": paths["result"], "stdin_path": None, "env": {}}
    save(Path(paths["request"]), request)
    request_sha256 = pin(paths["request"])["sha256"]
    body = {"version": "durable_systemd_native_job_v2", "unit": unit, "stage": "prepared",
        "command": request["command"], "cwd": str(directory), "stdout": str(directory / "stdout"),
        "stderr": str(directory / "stderr"), "paths": paths, "request_sha256": request_sha256,
        "metadata": {"policy": {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296}}}
    filename = directory / "native.json"
    save(filename, body)
    return helpers, attempt, filename, body, request, receipt, audit, save


def test_phase_harness_authenticates_failed_collected_run_and_selects_same_prepared_request_without_dispatch(tmp_path):
    helpers, attempt, filename, body, _, _, _, _ = _phase_control_fixture(tmp_path)
    original = filename.read_bytes(), Path(body["paths"]["request"]).read_bytes()
    authority = helpers["authenticated_attempt"](attempt)
    selected, retained, request = helpers["selected_native_handle"](
        attempt, filename, body["unit"], body["request_sha256"])
    assert authority["recorded_returncode"] == 1
    assert len(authority["validated_pin_records"]) == 6
    assert selected == filename and retained == body
    assert request == helpers["pin"](body["paths"]["request"])
    assert (filename.read_bytes(), Path(body["paths"]["request"]).read_bytes()) == original
    assert not Path(body["paths"]["ready"]).exists()
    assert not Path(body["paths"]["release"]).exists()


@pytest.mark.parametrize("change", ["source_bytes", "extra_source", "receipt_flag", "outer_unit",
    "not_terminal", "outside_module", "unbound_mapping", "native_changed", "returncode", "float_pin_size"])
def test_phase_harness_denies_unconfirmed_or_changed_retained_closure_before_lifecycle(tmp_path, change):
    helpers, attempt, _, body, _, receipt, audit, save = _phase_control_fixture(tmp_path)
    if change == "source_bytes":
        (attempt / "source_snapshot/engineering.py").write_bytes(b"changed")
    elif change == "extra_source":
        (attempt / "source_snapshot/unrecorded.py").write_bytes(b"extra")
    elif change in {"receipt_flag", "outer_unit", "not_terminal"}:
        receipt[{"receipt_flag": "source_unchanged", "outer_unit": "unit", "not_terminal": "terminal"}[change]] = (
            "different" if change == "outer_unit" else False)
        save(attempt / "receipt.json", receipt)
    elif change == "float_pin_size":
        path = attempt / "source_pins_before.json"
        rows = json.loads(path.read_bytes())
        rows[0]["size_bytes"] = float(rows[0]["size_bytes"])
        save(path, rows)
    else:
        key = {"outside_module": "outside_modules", "unbound_mapping": "unbound_mappings",
            "native_changed": "native_unchanged", "returncode": "pytest_returncode"}[change]
        audit[key] = False if change == "native_changed" else 0 if change == "returncode" else ["unbound"]
        save(attempt / "execution_audit.json", audit)
    with pytest.raises(ValueError, match="retained_attempt_"):
        helpers["authenticated_attempt"](attempt)
    assert not Path(body["paths"]["release"]).exists()


@pytest.mark.parametrize("change", ["unit", "request_identity", "command", "memory", "scratch", "wall",
    "control_escape", "outer_handle", "request_bytes", "unexpected_request_field"])
def test_phase_harness_denies_changed_native_selection_without_start_or_new_preparation(tmp_path, change):
    helpers, attempt, filename, body, request, _, _, save = _phase_control_fixture(tmp_path)
    unit, request_sha256 = body["unit"], body["request_sha256"]
    if change == "unit":
        unit += ".different"
    elif change == "request_identity":
        request_sha256 = "0" * 64
    elif change == "command":
        body["command"] = ["different-command"]
        save(filename, body)
    elif change in {"memory", "scratch", "wall"}:
        key = {"memory": "memory_bytes", "scratch": "scratch_bytes", "wall": "wall_seconds"}[change]
        body["metadata"]["policy"][key] = 1
        save(filename, body)
    elif change == "control_escape":
        body["paths"]["release"] = str(tmp_path / "escape")
        save(filename, body)
    elif change == "outer_handle":
        filename = attempt / "handle.json"
    elif change == "request_bytes":
        Path(body["paths"]["request"]).write_bytes(b"{}")
    else:
        request["unexpected"] = True
        save(Path(body["paths"]["request"]), request)
        body["request_sha256"] = request_sha256 = helpers["pin"](body["paths"]["request"])["sha256"]
        save(filename, body)
    with pytest.raises(ValueError, match="native_recovery_"):
        helpers["selected_native_handle"](attempt, filename, unit, request_sha256)
    assert not Path(body["paths"]["release"]).exists()
