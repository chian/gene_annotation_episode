"""Bounded grading preparation, actual-context binding and selected RNA delivery.

The host validates custody and original authority. Scientific arithmetic remains
in the pure calculators. No Store observation, annotation score or retry is made.
"""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.root.library.native_rna_structure_contracts import POLICY

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from typing import TYPE_CHECKING
from gene_annotation_episode.episodic_workflow.root.method_loop.identities import EpisodeRef

from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.episodic_workflow.root.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episodic_workflow.root.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job
from gene_annotation_episode.materials import artifact_file
from gene_annotation_episode.episodic_workflow.root.library.native_rna_structure_acquisition import decode_json, require, retained, validate_capture, rna_structure_source_payload, publish_rna_structure_source
from gene_annotation_episode.immutable_json_records import _immutable, _read
from gene_annotation_episode.episodic_workflow.root.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.episodic_workflow.root.library.rna_structure_contracts import RNA_ISSUE_CODES, analyze_rna_input_sequence, issue, validate_rna_input, validate_rna_sheet, validate_rna_components, validate_rna_parameters
from gene_annotation_episode.episodic_workflow.root.library.rna_structure_result_views import merge_issues, project_rna_prepublication, validate_rna_structure_result_selector, validate_rna_structure_row, validate_saved_rna_input
from gene_annotation_episode.episodic_workflow.root.library.tool_grading_artifacts import retain_tool_grading, source_tool_gradings

if TYPE_CHECKING:
    from gene_annotation_episode.episodic_workflow.root.native_rna_structure_returns import NativeRNAStructureReturns

PREPARED_VERSION = "native_rna_structure_prepared_grading_v1"
PREPARED_FIELDS = {"version", "bundle_artifact_ref", "source_grading_artifact_ref", "grading_artifact_ref",
    "sheet_artifact_ref", "components_artifact_ref", "selected_rows_artifact_ref", "diagnostics_artifact_ref",
    "worker_receipt_artifact_ref", "sheet_schema", "components_schema", "selector", "requested_cells_accounted_for",
    "native_success", "failures"}
STABLE_FIELDS = {"schema", "sheet_artifact_ref", "sheet_schema", "components_artifact_ref", "components_schema", "captured_artifacts"}
SELECTED_FIELDS = {"schema", "stable", "selector", "parameters", "components_artifact_ref", "components_schema",
    "selected_rows_artifact_ref", "diagnostics_artifact_ref", "worker_receipt_artifact_ref", "requested_cells_accounted_for", "failures"}


def _policy(policy):
    require(isinstance(policy, LocalJobPolicy) and policy.to_dict() == POLICY, "rna_invalid_input_schema")


def _artifact_json(store, reference):
    retained(store, reference)
    value = decode_json(store.get_artifact(reference), canonical_bytes=True)
    require(type(value) is dict, "rna_invalid_component_schema")
    return value


def _envelope(store, reference, bundle_ref):
    # Shared retain_tool_grading uses canonical JSON without the worker newline.
    retained(store, reference)
    body = decode_json(store.get_artifact(reference))
    require(type(body) is dict and set(body) == {"schema", "provider", "native_artifact_ref", "grading"} and
        body["schema"] == "tool_grading_artifact_v1" and body["provider"] == "episode.execution_result" and
        body["native_artifact_ref"] == bundle_ref, "rna_invalid_component_schema")
    return body["grading"]


def validate_prepared_rna_grading(store, prepared, *, bundle, capture, selector):
    require(type(prepared) is dict and set(prepared) == PREPARED_FIELDS and prepared["version"] == PREPARED_VERSION,
        "rna_invalid_component_schema")
    require(type(prepared["requested_cells_accounted_for"]) is bool and type(prepared["native_success"]) is bool,
        "rna_invalid_component_schema")
    require(all((prepared[reference] is None) == (prepared[schema] is None) for reference, schema in
        (("sheet_artifact_ref", "sheet_schema"), ("components_artifact_ref", "components_schema"))), "rna_invalid_component_schema")
    require(prepared["selector"] == selector and prepared["bundle_artifact_ref"] == capture["bundle_artifact_ref"])
    stable = _envelope(store, prepared["source_grading_artifact_ref"], prepared["bundle_artifact_ref"])
    selected = _envelope(store, prepared["grading_artifact_ref"], prepared["bundle_artifact_ref"])
    require(set(stable) == STABLE_FIELDS and stable["schema"] == "native_rna_structure_retained_grading_v1" and
        set(selected) == SELECTED_FIELDS and selected["schema"] == "native_rna_structure_selected_grading_v1" and
        selected["stable"] == stable and selected["selector"] == selector, "rna_invalid_component_schema")
    require(stable["captured_artifacts"] == capture["artifacts"], "rna_original_attempt_mismatch")
    for name in ("components_artifact_ref", "components_schema", "selected_rows_artifact_ref", "diagnostics_artifact_ref",
            "worker_receipt_artifact_ref", "requested_cells_accounted_for", "failures"):
        require(selected[name] == prepared[name], "rna_invalid_component_schema")
    parameters = selector["parameters"] if selector["acquisition"] == "retained_sheet_only" else bundle["requested_job"]["native_rna_structure"]["grading_parameters"]
    require(selected["parameters"] == parameters and prepared["native_success"] ==
        (bundle["returncode"] == 0 and bundle["native_status"] == "complete"), "rna_invalid_component_schema")
    if selector["acquisition"] == "complete_bound_bundle":
        require(all(prepared[name] == stable[name] for name in ("sheet_artifact_ref", "sheet_schema", "components_artifact_ref", "components_schema")),
            "rna_invalid_component_schema")
    elif prepared["sheet_artifact_ref"] is not None:
        require(prepared["sheet_artifact_ref"] == stable["sheet_artifact_ref"] == selector["saved_input"]["sheet_artifact_ref"])
    sheet = components = document = None
    if prepared["sheet_artifact_ref"] is not None:
        sheet = validate_rna_sheet(_artifact_json(store, prepared["sheet_artifact_ref"]))
        require(sheet["schema"] == prepared["sheet_schema"] and all(sheet[name] == bundle[name]
            for name in ("operation", "mode", "record_key")), "rna_input_identity_mismatch")
    if prepared["components_artifact_ref"] is not None:
        require(sheet is not None, "rna_invalid_component_schema")
        components = validate_rna_components(_artifact_json(store, prepared["components_artifact_ref"]), sheet=sheet)
        require(components["parameters"] == parameters and components["schema"] == prepared["components_schema"], "rna_invalid_component_schema")
    for name in ("diagnostics_artifact_ref", "worker_receipt_artifact_ref"):
        if prepared[name] is not None:
            retained(store, prepared[name])
    if prepared["selected_rows_artifact_ref"] is not None:
        document = _artifact_json(store, prepared["selected_rows_artifact_ref"])
        diagnostics = _artifact_json(store, prepared["diagnostics_artifact_ref"])
        require(set(diagnostics) == {"schema", "record_key", "capture_failures", "parse_issues", "sheet_issues", "calculation_issues", "selection_issues"}
            and diagnostics["schema"] == "rna_structure_grading_diagnostics_v1" and diagnostics["record_key"] == bundle["record_key"], "rna_invalid_component_schema")
        require(diagnostics["capture_failures"] == (capture["failures"] if selector["acquisition"] == "complete_bound_bundle" else []),
            "rna_invalid_component_schema")
        failures = merge_issues(bundle["failures"] if selector["acquisition"] == "complete_bound_bundle" else [],
            diagnostics["capture_failures"], diagnostics["parse_issues"], diagnostics["sheet_issues"], diagnostics["calculation_issues"])
        if components is not None:
            expected, selection = project_rna_prepublication(sheet, components, selector=selector,
                components_sha256=store.get(prepared["components_artifact_ref"])["sha256"], failures=failures)
            require(document == expected and diagnostics["selection_issues"] == selection, "rna_invalid_component_schema")
        else:
            selection = []
            projection = selector["projection"]
            if projection["family"] != "failure":
                choices = projection["rows"]
                for index in range(len(choices["record_keys"])) if "record_keys" in choices else [None]:
                    selection.append(issue("rna_requested_row_missing", stage="selection", record_key=bundle["record_key"],
                        field="/selector/projection/rows" if index is None else f"/selector/projection/rows/record_keys/{index}", index=index))
            expected = {"schema": "rna_structure_prepublication_v1", **{key: bundle[key] for key in ("record_key", "operation", "mode")},
                "selector": selector, "sheet_schema": prepared["sheet_schema"], "components_sha256": None, "parameters": parameters,
                "population_count": None, "rows": [], "failures": merge_issues(failures, selection),
                "requested_cells_accounted_for": projection["family"] != "failure"}
            require(document == expected and diagnostics["selection_issues"] == selection, "rna_invalid_component_schema")
        require(document["failures"] == prepared["failures"] and document["requested_cells_accounted_for"] == prepared["requested_cells_accounted_for"],
            "rna_invalid_component_schema")
    else:
        require(not prepared["requested_cells_accounted_for"], "rna_invalid_component_schema")
    return {"stable": stable, "selected": selected, "sheet": sheet, "components": components, "document": document}


def _prepare(store, *, bundle, capture, selector, parameters, directory, policy, plan, original=None):
    _policy(policy)
    directory = Path(directory).absolute()
    require(directory.resolve() == directory, "rna_output_path_conflict")
    directory.mkdir(parents=True, exist_ok=True)
    intent = {"bundle": bundle, "capture": capture, "selector": selector, "policy": policy.to_dict()}
    _immutable(directory / "intent.json", intent)
    if (directory / "prepared.json").exists():
        prepared = _read(directory / "prepared.json")
        validate_prepared_rna_grading(store, prepared, bundle=bundle, capture=capture, selector=selector)
        return prepared
    _immutable(directory / "plan.json", plan)
    prepared = {"version": PREPARED_VERSION, "bundle_artifact_ref": capture["bundle_artifact_ref"],
        **{key: None for key in ("source_grading_artifact_ref", "grading_artifact_ref", "sheet_artifact_ref", "components_artifact_ref",
            "selected_rows_artifact_ref", "diagnostics_artifact_ref", "worker_receipt_artifact_ref", "sheet_schema", "components_schema")},
        "selector": selector, "requested_cells_accounted_for": False,
        "native_success": bundle["returncode"] == 0 and bundle["native_status"] == "complete", "failures": []}
    for name in ("tmp", "cache"):
        (directory / name).mkdir(exist_ok=True)
    # The lifecycle runs this supplied calculation once; an existing incomplete
    # worker reservation is never silently retried by preparation replay.
    require(not (directory / "worker-started.json").exists(), "rna_capture_unavailable")
    _immutable(directory / "worker-started.json", {"plan": plan})
    try:
        result = run_local_job([sys.executable, "-B", "-m", "gene_annotation_episode.native_rna_structure_result_worker",
            str(directory / "plan.json")], cwd=directory, policy=policy,
            stdout_path=directory / "worker.stdout", stderr_path=directory / "worker.stderr",
            env={"PYTHONPATH": str(Path(__file__).resolve().parents[4]), "PYTHONDONTWRITEBYTECODE": "1",
                **{key: str(directory / "tmp") for key in ("TMPDIR", "TMP", "TEMP")}, "XDG_CACHE_HOME": str(directory / "cache")})
        receipt = {"returncode": result.returncode, "metadata": result.metadata,
            "stdout_artifact_ref": artifact_file(store, result.stdout_path),
            "stderr_artifact_ref": artifact_file(store, result.stderr_path)}
        require(result.returncode == 0, "rna_invalid_component_schema")
        manifest = _read(directory / "worker-result.json")
        require(type(manifest) is dict and set(manifest) == {"version", "sheet_schema", "components_schema", "sheet_file", "components_file", "projected_rows_file",
            "diagnostics_file", "requested_cells_accounted_for", "failures"} and
            manifest["version"] == "native_rna_structure_grading_worker_result_v1", "rna_invalid_component_schema")
        for field, name, schema_field in (("sheet_artifact_ref", "sheet.json", "sheet_schema"),
                ("components_artifact_ref", "components.json", "components_schema"),
                ("selected_rows_artifact_ref", "selected-rows.json", None), ("diagnostics_artifact_ref", "diagnostics.json", None)):
            manifest_field = {"sheet.json": "sheet_file", "components.json": "components_file", "selected-rows.json": "projected_rows_file", "diagnostics.json": "diagnostics_file"}[name]
            require(manifest[manifest_field] in (None, name), "rna_invalid_component_schema")
            if manifest[manifest_field] is not None:
                _read(directory / name)
                prepared[field] = artifact_file(store, directory / name, "application/json")
            if schema_field is not None:
                prepared[schema_field] = manifest[schema_field]
        prepared.update(failures=manifest["failures"], requested_cells_accounted_for=manifest["requested_cells_accounted_for"])
        receipt["worker_result_artifact_ref"] = artifact_file(store, directory / "worker-result.json", "application/json")
    except (ValueError, OSError, AcquisitionError) as error:
        receipt = locals().get("receipt", {"exception_type": type(error).__name__, "detail": str(error)})
        if isinstance(error, AcquisitionError):
            receipt.update(code=error.code, phase=error.phase, diagnostic=error.diagnostic, operational=error.operational)
        prepared["failures"] = merge_issues(bundle["failures"] if original is None else [], plan["capture_failures"],
            [issue(str(error) if str(error) in RNA_ISSUE_CODES else "rna_capture_unavailable", stage="calculate", record_key=bundle["record_key"])])
        prepared["requested_cells_accounted_for"] = False
    prepared["worker_receipt_artifact_ref"] = store.artifact(canonical(receipt) + "\n", "application/json")
    stable = ({"schema": "native_rna_structure_retained_grading_v1", **{key: prepared[key] for key in
        ("sheet_artifact_ref", "sheet_schema", "components_artifact_ref", "components_schema")}, "captured_artifacts": capture["artifacts"]}
        if original is None else _envelope(store, original["source_grading_artifact_ref"], capture["bundle_artifact_ref"]))
    prepared["source_grading_artifact_ref"] = (retain_tool_grading(store, provider="episode.execution_result", native_artifact_ref=capture["bundle_artifact_ref"], grading=stable)
        if original is None else original["source_grading_artifact_ref"])
    selected = {"schema": "native_rna_structure_selected_grading_v1", "stable": stable, "selector": selector,
        "parameters": parameters, **{key: prepared[key] for key in ("components_artifact_ref", "components_schema", "selected_rows_artifact_ref",
            "diagnostics_artifact_ref", "worker_receipt_artifact_ref", "requested_cells_accounted_for", "failures")}}
    prepared["grading_artifact_ref"] = retain_tool_grading(store, provider="episode.execution_result", native_artifact_ref=capture["bundle_artifact_ref"], grading=selected)
    validate_prepared_rna_grading(store, prepared, bundle=bundle, capture=capture, selector=selector)
    _immutable(directory / "prepared.json", prepared)
    return prepared


def prepare_rna_structure_grading(store, *, bundle, capture, directory, policy, selector):
    capture = validate_capture(store, capture, bundle=bundle)
    require(capture["bundle_validated"])
    selector = validate_rna_structure_result_selector(selector, mode=bundle["mode"])
    require(selector["acquisition"] == "complete_bound_bundle", "rna_invalid_input_schema")
    paths = [{**row, "path": str(retained(store, row["artifact_ref"])[1])} for row in capture["artifacts"]]
    directory = Path(directory).absolute()
    plan = {"version": "native_rna_structure_grading_plan_v1", "bundle": bundle, "bundle_artifact_ref": capture["bundle_artifact_ref"],
        "artifacts": paths, "selector": selector, "directory": str(directory), "capture_failures": capture["failures"]}
    return _prepare(store, bundle=bundle, capture=capture, selector=selector,
        parameters=bundle["requested_job"]["native_rna_structure"]["grading_parameters"], directory=directory, policy=policy, plan=plan)


def prepare_saved_rna_structure_grading(store, context, *, saved_input, parameters, directory, policy, selector,
        returns: NativeRNAStructureReturns):
    original = returns.resolve_saved_rna_input(context, saved_input)
    selector = validate_rna_structure_result_selector(selector, mode=saved_input["mode"])
    parameters = validate_rna_parameters(parameters)
    require(selector["saved_input"] == saved_input and selector["parameters"] == parameters)
    capture = original["capture"]
    bundle = _artifact_json(store, capture["bundle_artifact_ref"])
    # A missing saved file is a specific retained-custody failure. Pass its
    # original content-addressed location, never an original producer operand.
    metadata = store.get(saved_input["sheet_artifact_ref"])
    require(metadata["record_type"] == "artifact" and metadata["sha256"] == saved_input["sheet_sha256"])
    sheet_path = store.path / "artifacts" / metadata["sha256"][:2] / metadata["sha256"]
    plan = {"version": "native_rna_structure_saved_grading_plan_v1", "sheet_path": str(sheet_path),
        "sheet_sha256": saved_input["sheet_sha256"], **{key: saved_input[key] for key in ("record_key", "operation", "mode")},
        "parameters": parameters, "selector": selector, "directory": str(Path(directory).absolute()), "capture_failures": []}
    return _prepare(store, bundle=bundle, capture=capture, selector=selector, parameters=parameters,
        directory=directory, policy=policy, plan=plan, original=original["prepared"])


