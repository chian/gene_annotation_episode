"""Saved native612 bytes in explicitly synthetic producer/capture fault fixtures.

No native masking executable runs here. One test exercises the actual bounded
Python result-worker services; the other workers run inside the outer bounded
verification process for focused custody/projection tests.
"""
from copy import deepcopy
import builtins
import hashlib
import json
from pathlib import Path
import shutil
import socket
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from gene_annotation_episode import native_blast_masking_result_publication as publication
from gene_annotation_episode import native_blast_masking_result_worker as worker
from gene_annotation_episode import sequence_masking_calculations as calculations
from gene_annotation_episode import sequence_masking_inputs as readers
from gene_annotation_episode.domain import ContractError, canonical
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_blast_masking_acquisition import publish_original_source
from gene_annotation_episode.native_blast_masking_contracts import (
    BUNDLE_VERSION, compile_native_blast_masking_job, generated_statistics_binding,
    masking_occurrence_id, native_blast_digest, native_environment, producer_failure,
    staged_relative, validate_original_bundle,
)
from gene_annotation_episode.sequence_masking_result_views import (
    FACT_SOURCES, QUANTITIES, SAVED_SCHEMAS, project_masking_result,
    validate_masking_fact_values, validate_masking_result_selector,
)
from gene_annotation_episode.state import Store
from test_native_blast_masking_invocation import FIXTURES, POLICY, plan_for, reseal


def selector(**changes):
    return {"version": "native_blast_masking_result_selector_v1", "mode": "native_result",
        "records": {"mode": "all"}, "quantities": [], "statistics_fields": [],
        "statistics_unit_codes": [], "include_checks": False, "artifacts": [],
        "saved_data": [], "saved_sheet_ref": None, **changes}


def position(ordinal):
    return {"operand_role": "sequences", "operand_ordinal": 0, "record_ordinal": ordinal}


def slot(role, direction="output"):
    return {"direction": direction, "role": role, "ordinal": 0}


def saved_bytes(pin):
    raw = (FIXTURES / pin["path"]).read_bytes()
    assert (hashlib.sha256(raw).hexdigest(), len(raw)) == (pin["sha256"], pin["size_bytes"])
    return raw


def captured_fixture(tmp_path, case_id="dustmasker_interval", *, returncode=0,
                     missing_output=False, capture_error=None, primary_bytes=None):
    """Construct labelled synthetic custody around authentic immutable native bytes."""
    manifest = json.loads((FIXTURES / "ORACLE_MANIFEST.json").read_text())
    case = next(r for r in manifest["cases"] if r["case_id"] == case_id)
    mode = "create_counts" if case_id == "windowmasker_counts" else "mask"
    plan = plan_for(tmp_path / "fixture", case["program"], mode)
    job = plan["requested_job"]["native_blast_masking"]
    op = job["operation"]
    fmt = "ascii_statistics" if mode == "create_counts" else "fasta" if case_id.endswith(("soft", "hard")) else "interval"
    op.update(output_format=fmt, masking_style="not_applicable" if mode == "create_counts" else
              "hard" if case_id.endswith("hard") else "soft" if fmt == "fasta" else "interval",
              parse_seqids=case.get("parse_seqids") is True)
    job["outputs"][0]["format"] = fmt
    # Parameters are original oracle values, without interpreting native defaults.
    for name, value in case["selected_parameters"].items():
        name = name.lstrip("-")
        if name in op["requested_parameters"]:
            op["requested_parameters"][name] = (value if type(value) is not str else value == "true" if value in ("true", "false") else
                int(value) if str(value).isdigit() else float(value))
    selected_input = next(r for r in manifest["inputs"] if r["input_id"] == case["input_id"])
    operand = job["operands"][0]
    raw_input = saved_bytes(selected_input["retained"])
    Path(operand["path"]).write_bytes(raw_input)
    operand.update(sha256=hashlib.sha256(raw_input).hexdigest(), size_bytes=len(raw_input))
    reseal(plan)
    job = plan["requested_job"]["native_blast_masking"]
    store = Store(tmp_path / "store")
    inputs, retained = [], []
    for operand in job["operands"]:
        raw = Path(operand["path"]).read_bytes()
        ref = store.artifact(raw)
        sha = hashlib.sha256(raw).hexdigest()
        path = staged_relative(operand)
        inputs.append({"role": operand["role"], "ordinal": 0, "format": operand["format"],
            "original_path": operand["path"], "relative_path": path, "artifact_ref": operand["artifact_ref"],
            **{p + "sha256": sha for p in ("expected_", "staged_", "final_")},
            **{p + "size_bytes": len(raw) for p in ("expected_", "staged_", "final_")}})
        retained.append({"direction": "input", "role": operand["role"], "ordinal": 0, "format": operand["format"],
            "relative_path": path, "artifact_ref": ref, "sha256": sha, "size_bytes": len(raw)})
    outputs, failures, capture_failures = [], [], []
    for output in job["outputs"]:
        primary = output["role"] not in {"stdout", "stderr"}
        raw = primary_bytes if primary and primary_bytes is not None else saved_bytes(case["primary_output"] if primary else case[output["role"]])
        if primary and missing_output:
            outputs.append({**output, "ordinal": 0, "sha256": None, "size_bytes": None})
            failures.append(producer_failure("missing_output", output["role"]))
            continue
        sha = hashlib.sha256(raw).hexdigest()
        outputs.append({**output, "ordinal": 0, "sha256": sha, "size_bytes": len(raw)})
        if primary and capture_error:
            reference = store.artifact(b"synthetic changed bytes") if capture_error == "original_file_identity_mismatch" else None
            capture_failures.append({"stage": "custody", "code": capture_error, "direction": "output",
                "role": output["role"], "ordinal": 0, "relative_path": output["relative_path"],
                "diagnostic_artifact_ref": reference, "input_failures": []})
        else:
            retained.append({"direction": "output", **output, "ordinal": 0, "artifact_ref": store.artifact(raw),
                "sha256": sha, "size_bytes": len(raw)})
    if returncode != 0:
        failures.append(producer_failure("nonzero_returncode"))
    root = Path(plan["attempt_directory"])
    root.mkdir()
    # This fixture directory is disposable. No native executable is invoked.
    (root / "fixture-origin.txt").write_text("synthetic custody; authentic retained oracle612 native bytes\n")
    bundle = {"version": BUNDLE_VERSION, "identity": plan["identity"], "requested_job": plan["requested_job"],
        "operation": job["operation"], "software": {"executable": job["software"]["executable"],
            "expected_sha256": job["software"]["sha256"], "actual_sha256": job["software"]["sha256"],
            "declared_engine_version": job["software"]["engine_version"]},
        "realized_argv": compile_native_blast_masking_job(job,
            input_paths={r["role"]: str(root / staged_relative(r)) for r in job["operands"]}, output_directory=str(root)),
        "environment": native_environment(job, str(root)), "inputs": inputs, "operand_bindings": [],
        "statistics_binding": job["statistics_binding"], "returncode": returncode,
        "artifacts": outputs, "failures": failures,
        "started_at": "2026-10-28T00:00:00+00:00", "finished_at": "2026-10-28T00:00:01+00:00"}
    if mode == "create_counts" and returncode == 0 and not failures:
        bundle["statistics_binding"] = generated_statistics_binding(bundle)
    validate_original_bundle(bundle, plan)
    capture = {"version": "native_blast_masking_capture_v1", "bundle_artifact_ref": store.artifact(canonical(bundle), "application/json"),
        "bundle_validated": True, "artifacts": retained, "failures": capture_failures}
    return store, bundle, capture, root


def inline_workers(monkeypatch):
    calls = []
    def run(command, **kwargs):
        calls.append(command)
        plan = json.loads(Path(command[-1]).read_text())
        result = worker.run(plan)
        kwargs["stdout_path"].write_text(canonical(result))
        kwargs["stderr_path"].write_text("")
        return SimpleNamespace(returncode=0 if result["completed"] else 1,
                               metadata={"verification": "inprocess_inside_bounded_test_handle"})
    monkeypatch.setattr(publication, "run_local_job", run)
    return calls


def prepared_fixture(tmp_path, monkeypatch=None, case_id="dustmasker_interval", **kwargs):
    if monkeypatch is not None:
        inline_workers(monkeypatch)
    store, bundle, capture, root = captured_fixture(tmp_path, case_id, **kwargs)
    prepared = publication.prepare_native_blast_masking_result(store, bundle=bundle,
        bundle_artifact_ref=capture["bundle_artifact_ref"], artifacts=capture["artifacts"], capture=capture,
        directory=tmp_path / "results", policy=LocalJobPolicy(**POLICY))
    source = publish_original_source(store, bundle=bundle, capture=capture, prepared=prepared)
    return store, bundle, capture, root, prepared, source


def publish(tmp_path, store, prepared, source, choice, name="projection"):
    return publication.publish_selected_masking_result(store, source_ref=source, prepared=prepared,
        selector=choice, directory=tmp_path / name, policy=LocalJobPolicy(**POLICY))


@pytest.mark.parametrize("case_id,expected", [
    ("dustmasker_interval", [80, 0, 72]), ("dustmasker_soft", [80, 0, 72]),
    ("segmasker_interval", [64, 0, 32]), ("segmasker_soft", [64, 0, 32]),
    ("windowmasker_interval", [80, 0, 0]), ("windowmasker_soft", [80, 0, 0])])
def test_native_saved_formats_publish_exact_shared_components(tmp_path, monkeypatch, case_id, expected):
    store, bundle, _, _, prepared, source = prepared_fixture(tmp_path, monkeypatch, case_id)
    assert prepared["worker_completed"]
    sheet = json.loads(store.get_artifact(prepared["sheet_artifact_ref"]))
    scores = json.loads(store.get_artifact(prepared["calculations_artifact_ref"]))
    choice = selector(quantities=list(QUANTITIES), include_checks=True)
    with patch.object(calculations, "calculate_sequence_masking_components", side_effect=AssertionError("projection recalculated")):
        result = publish(tmp_path, store, prepared, source, choice)
    assert result["status"]["state"] == "complete"
    assert [r["value"]["value"] for r in result["quantities"] if r["quantity"] == "masked_positions"] == expected
    by_key = {r["record_key"]: r for r in scores["records"]}
    assert all(r["value"] == by_key[r["record_key"]][r["quantity"]] for r in result["quantities"])
    assert result["record_refs"] == [source]
    assert result["artifacts"] == result["saved_data"] == []
    assert sheet["operation"] == bundle["operation"]


def test_original_position_selection_checks_and_explicit_artifact_grants(tmp_path, monkeypatch):
    store, _, _, _, prepared, source = prepared_fixture(tmp_path, monkeypatch)
    choice = selector(records={"mode": "selected", "entries": [position(1)]},
        quantities=["masked_positions"], include_checks=True, artifacts=[slot("mask")], saved_data=["sheet"])
    result = publish(tmp_path, store, prepared, source, choice)
    row = result["quantities"][0]
    assert row["record_key"].endswith("#/records/1") and row["value"]["value"] == 0
    assert all(r["record_key"] in {None, row["record_key"]} for r in result["checks"])
    assert [r["role"] for r in result["artifacts"]] == ["mask"]
    assert result["record_refs"] == [source, result["artifacts"][0]["artifact_ref"], prepared["sheet_artifact_ref"]]
    assert result["saved_data"][0]["schema"] == "sequence_masking_sheet_v1"


def test_missing_original_record_is_not_replaced_or_silently_dropped(tmp_path, monkeypatch):
    store, _, _, _, prepared, source = prepared_fixture(tmp_path, monkeypatch)
    result = publish(tmp_path, store, prepared, source, selector(
        records={"mode": "selected", "entries": [position(1), position(8)]}, quantities=["masked_fraction"]))
    assert len(result["quantities"]) == 1
    assert result["status"]["state"] == "partial"
    missing = next(f for f in result["failures"] if f["code"] == "requested_input_record_absent")
    assert missing["record_key"].endswith("#/records/8")


def test_native_hard_mask_known_ambiguity_is_a_qualified_complete_result(tmp_path, monkeypatch):
    store, _, _, _, prepared, source = prepared_fixture(tmp_path, monkeypatch, "dustmasker_hard")
    result = publish(tmp_path, store, prepared, source, selector(records={"mode": "selected", "entries": [position(2)]},
        quantities=["masked_fraction", "changed_positions"]))
    assert result["status"]["state"] == "complete"
    assert result["quantities"][0]["value"] == {"numerator": None, "denominator": 72, "value": None, "missing_reason": "hard_mask_ambiguous"}
    assert result["quantities"][1]["value"]["value"] == 64


@pytest.mark.parametrize("case_id", ["windowmasker_counts", "windowmasker_interval"])
def test_statistics_preserve_original_reference_rows_thresholds_and_absent_codes(tmp_path, monkeypatch, case_id):
    store, bundle, _, _, prepared, source = prepared_fixture(tmp_path, monkeypatch, case_id)
    stats = json.loads(store.get_artifact(prepared["statistics_artifact_ref"]))
    result = publish(tmp_path, store, prepared, source, selector(statistics_fields=["thresholds", "unit_length"],
        statistics_unit_codes=[stats["unit_counts"][0]["unit_code"], 999], saved_data=["parsed_statistics"]))
    row = result["statistics"][0]
    assert row["fields"] == {"unit_length": 3, "thresholds": {"t_low": 3, "t_extend": 126, "t_threshold": 126, "t_high": 126}}
    assert row["unit_counts"] == [stats["unit_counts"][0]] and row["missing_unit_codes"] == [999]
    assert len(stats["unit_counts"]) == 21 and len(stats["percentiles"]) == 501
    assert min(r["native_count"] for r in stats["unit_counts"]) == 1
    assert max(r["native_count"] for r in stats["unit_counts"]) == 64
    assert bundle["operation"]["requested_parameters"]["t_low"] == 1
    assert row["reference_binding"] == bundle["statistics_binding"]
    if case_id.endswith("counts"):
        assert prepared["sheet_artifact_ref"] is None
        assert row["reference_binding"]["reference_occurrence_ids"] == [masking_occurrence_id(bundle["identity"], "input", "reference_sequences")]
    else:
        assert row["occurrence_id"] == "supplied:reference:statistics:0"
        assert row["reference_binding"]["provenance"] == "unknown"


def test_failed_native_partial_files_are_retained_not_zero_or_associated_by_guess(tmp_path, monkeypatch):
    store, _, _, _, prepared, source = prepared_fixture(tmp_path, monkeypatch, returncode=3)
    assert prepared["worker_completed"] and prepared["native_outcome"]["state"] == "failed"
    sheet = json.loads(store.get_artifact(prepared["sheet_artifact_ref"]))
    assert not sheet["parsed_output"]["records"] and len(sheet["parsed_output"]["unassigned_records"]) == 3
    result = publish(tmp_path, store, prepared, source, selector(quantities=["masked_positions"], artifacts=[slot("mask")]))
    assert all(r["value"]["value"] is None for r in result["quantities"])
    assert result["status"]["state"] == "partial" and result["status"]["native_state"] == "failed"
    diagnostics = publish(tmp_path, store, prepared, source, selector(artifacts=[slot("stderr")]), name="diagnostics")
    assert diagnostics["status"] == {"source_ref": source, "state": "complete", "native_state": "failed", "output_complete": False}
    assert any(f["code"] == "native_blast_masking_nonzero_returncode" for f in diagnostics["failures"])


@pytest.mark.parametrize("capture_error", ["original_file_unavailable", "original_file_identity_mismatch"])
def test_original_capture_failure_code_and_diagnostic_survive(tmp_path, monkeypatch, capture_error):
    store, _, capture, _, prepared, source = prepared_fixture(tmp_path, monkeypatch, capture_error=capture_error)
    assert prepared["sheet_artifact_ref"] is None
    stable = json.loads(store.get_artifact(prepared["source_grading_artifact_ref"]))["grading"]
    assert stable["capture"] == capture
    assert any(f["code"] == capture_error for f in prepared["failures"])
    result = publish(tmp_path, store, prepared, source, selector(artifacts=[slot("mask")], saved_data=["sheet"]))
    assert result["artifacts"] == result["saved_data"] == [] and result["record_refs"] == [source]
    assert result["status"]["state"] == "unavailable"
    assert {"requested_artifact_unavailable", "requested_saved_sheet_unavailable", capture_error} <= {f["code"] for f in result["failures"]}


def test_actual_saved_sheet_recalculation_and_frozen_replay_after_paths_disappear(tmp_path, monkeypatch):
    store, bundle, capture, native_root, prepared, source = prepared_fixture(tmp_path, monkeypatch)
    choice = selector(mode="saved_recalculation", saved_sheet_ref=prepared["sheet_artifact_ref"], quantities=["masked_fraction"])
    with patch.object(calculations, "calculate_sequence_masking_components", wraps=calculations.calculate_sequence_masking_components) as calculate:
        result = publish(tmp_path, store, prepared, source, choice)
        assert calculate.call_count == 1
        assert calculate.call_args.args[0] == json.loads(store.get_artifact(prepared["sheet_artifact_ref"]))
    envelope = json.loads(store.get_artifact(result["projection_artifact_ref"]))
    assert json.loads(store.get_artifact(envelope["recalculations_artifact_ref"])) == json.loads(store.get_artifact(prepared["calculations_artifact_ref"]))
    shutil.rmtree(native_root.parent.parent.parent.parent)
    with patch.object(publication, "run_local_job", side_effect=AssertionError("replayed worker")), \
         patch.object(readers, "parse_sequence_masking_output", side_effect=AssertionError("reparsed native")), \
         patch.object(calculations, "calculate_sequence_masking_components", side_effect=AssertionError("recalculated replay")), \
         patch.object(store, "artifact", side_effect=AssertionError("replay wrote artifact")):
        assert publication.validate_masking_publication(store, source_ref=source, prepared=prepared, selector=choice, publication=result) == result
        assert publish(tmp_path, store, prepared, source, choice) == result
        assert publication.prepare_native_blast_masking_result(store, bundle=bundle, bundle_artifact_ref=capture["bundle_artifact_ref"],
            artifacts=capture["artifacts"], capture=capture, directory=tmp_path / "results", policy=LocalJobPolicy(**POLICY)) == prepared


def test_changed_prepared_selector_publication_and_source_are_rejected(tmp_path, monkeypatch):
    store, _, _, _, prepared, source = prepared_fixture(tmp_path, monkeypatch)
    choice = selector(quantities=["masked_positions"])
    result = publish(tmp_path, store, prepared, source, choice)
    for key, value in [("worker_completed", False), ("sheet_artifact_ref", prepared["calculations_artifact_ref"]), ("failures", [])]:
        changed = deepcopy(prepared); changed[key] = value
        if changed == prepared:
            changed["native_outcome"]["output_complete"] = False
        with pytest.raises(ContractError):
            publication.validate_prepared_masking_result(store, changed)
    changed = deepcopy(result); changed["quantities"][0]["value"]["value"] = 79
    with pytest.raises(ContractError, match="frozen_values"):
        publication.validate_masking_publication(store, source_ref=source, prepared=prepared, selector=choice, publication=changed)
    with pytest.raises(ContractError, match="selection"):
        publication.validate_masking_publication(store, source_ref=source, prepared=prepared, selector=selector(quantities=["input_length"]), publication=result)
    with pytest.raises(ContractError):
        publication.validate_masking_publication(store, source_ref=prepared["sheet_artifact_ref"], prepared=prepared, selector=choice, publication=result)
    with pytest.raises(ContractError, match="saved_sheet_original"):
        publish(tmp_path, store, prepared, source, selector(mode="saved_recalculation", saved_sheet_ref=prepared["calculations_artifact_ref"]), name="wrong")


def test_worker_receipt_replay_does_not_parse_again_or_restart_incomplete_intent(tmp_path, monkeypatch):
    store, _, _, _, prepared, _ = prepared_fixture(tmp_path, monkeypatch)
    stable = json.loads(store.get_artifact(prepared["source_grading_artifact_ref"]))["grading"]
    receipt = json.loads(store.get_artifact(stable["worker_receipt_artifact_ref"]))
    with patch.object(readers, "parse_masking_input_fasta", side_effect=AssertionError("reparsed")):
        assert worker.run(receipt["plan"]) == receipt["manifest"]
    path = Path(receipt["plan"]["directory"]) / "worker-result.json"
    path.unlink()
    with pytest.raises(ContractError, match="original_work_incomplete"):
        worker.run(receipt["plan"])


def test_projection_has_no_io_or_calculation_and_returns_independent_values(tmp_path, monkeypatch):
    store, _, _, _, prepared, source = prepared_fixture(tmp_path, monkeypatch)
    sheet = json.loads(store.get_artifact(prepared["sheet_artifact_ref"]))
    scores = json.loads(store.get_artifact(prepared["calculations_artifact_ref"]))
    with patch.object(builtins, "open", side_effect=AssertionError("IO")), \
         patch.object(Path, "read_bytes", side_effect=AssertionError("IO")), \
         patch.object(subprocess, "run", side_effect=AssertionError("native")), \
         patch.object(socket, "socket", side_effect=AssertionError("network")), \
         patch.object(calculations, "calculate_sequence_masking_components", side_effect=AssertionError("recalculate")):
        result = project_masking_result(source_ref=source, operation=prepared["operation"], native_outcome=prepared["native_outcome"],
            sheet=sheet, calculations=scores, statistics=None, occurrences=prepared["occurrences"], selector=selector(quantities=["masked_positions"]),
            failures=prepared["failures"], saved_data=[])
    result["quantities"][0]["value"]["value"] = 999
    assert scores["records"][0]["masked_positions"]["value"] == 80


def test_closed_selector_and_fact_relationships(tmp_path, monkeypatch):
    store, _, _, _, prepared, source = prepared_fixture(tmp_path, monkeypatch)
    for choice in [selector(extra="not_allowed"), selector(records={"mode": "selected", "entries": [position(True)]}),
        selector(artifacts=[slot("statistics")]), selector(saved_data=["parsed_statistics"]),
        selector(statistics_unit_codes=[True]), selector(quantities=["masked_positions", "masked_positions"])]:
        with pytest.raises(ContractError):
            validate_masking_result_selector(choice, operation=prepared["operation"])
    result = publish(tmp_path, store, prepared, source, selector(quantities=["masked_fraction"], saved_data=["sheet"], artifacts=[slot("mask")]))
    assert set(FACT_SOURCES) == {"execution.masking_" + k for k in ("status", "artifacts", "quantities", "checks", "statistics", "failures", "saved_data")}
    for name in FACT_SOURCES:
        key = name.removeprefix("execution.masking_")
        values = [result[key]] if key == "status" else result[key]
        assert validate_masking_fact_values(name, values) == values
    bad = deepcopy(result["quantities"]); bad[0]["value"]["numerator"] = True
    with pytest.raises(ContractError):
        validate_masking_fact_values("execution.masking_quantities", bad)
    bad = deepcopy(result["saved_data"]); bad[0]["schema"] = SAVED_SCHEMAS["calculations"]
    with pytest.raises(ContractError):
        validate_masking_fact_values("execution.masking_saved_data", bad)


def test_actual_bounded_result_worker_process_and_publication(tmp_path):
    """Real Python worker processes, consuming retained bytes; zero native runs."""
    store, _, _, _, prepared, source = prepared_fixture(tmp_path)
    assert prepared["worker_completed"]
    result = publish(tmp_path, store, prepared, source, selector(quantities=["masked_positions"], saved_data=["sheet"]))
    assert [r["value"]["value"] for r in result["quantities"]] == [80, 0, 72]
    assert result["status"]["state"] == "complete"
    stable = json.loads(store.get_artifact(prepared["source_grading_artifact_ref"]))["grading"]
    receipt = json.loads(store.get_artifact(stable["worker_receipt_artifact_ref"]))
    assert receipt["returncode"] == 0
    assert receipt["manifest"]["task"] == "parse_calculate"
