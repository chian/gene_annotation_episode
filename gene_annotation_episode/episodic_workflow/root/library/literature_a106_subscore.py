"""Claim-bound A106 log evidence ratios with explicit experiment dependence."""
from copy import deepcopy
import math

from gene_annotation_episode.domain import REF, ContractError, obj, validate_schema
from .literature_rate_unit_witness_schema import _witness_schema
from ..literature_intervention_storage import intervention_cells_schema

VERSION = "a106_experimental_subscore_v1"
NAMESPACE = "literature_a106_subscore_cells"
REQUESTED = "requested_a106_subscore_components"
COMPONENTS = ("experimental_subscore",)
SCOPE = "a106_intervention_experimental_evidence"
SCORE_COMPONENT = "source_log_evidence_ratio"
from gene_annotation_episode.episodic_workflow.root.library.literature_a106_task_declaration import TASK


def population_schema():
    text = {"type": "string", "minLength": 1}
    source = {**REF, "x-reference-namespace": "source"}
    return obj({"subject_ref": deepcopy(REF),
        "assertion_ref": {**REF, "x-reference-namespace": "hypothesis"},
        "comparison_ref": {**REF, "x-reference-namespace": "hypothesis"},
        "scope_statement": text,
        "experiments": {"type": "array", "items": obj({
            "experiment_ref": {**REF, "x-reference-namespace": "reference"},
            "sheet_ref": {**source, "type": ["string", "null"],
                "description": "Current assessment sheet, including an unavailable score. Null only when no applicable assessment sheet exists."},
            "missing_reason": {"type": ["string", "null"], "minLength": 1,
                "description": "Null whenever sheet_ref is supplied, including an unavailable score. Explain a missing assessment only when sheet_ref is null; numerical limitations remain in the selected assessment and final limitations."}})},
        "dependence": obj({"status": {"enum": ["independent", "shared", "unknown"]},
            "rationale": text, "witnesses": {"type": "array", "items": _witness_schema()}}),
        "conclusion": text, "limitations": {"type": "array", "items": text},
        "revises_subscore_ref": {**source, "type": ["string", "null"]},
        "revision_reason": {"type": ["string", "null"], "minLength": 1}})


def cell_schema():
    fields = population_schema()["properties"]
    contributors = deepcopy(intervention_cells_schema())
    contributors.pop("x-source")
    strings = {"type": "array", "items": {"type": "string"}, "uniqueItems": True}
    return obj({**fields, "component": {"enum": list(COMPONENTS)}, "axis": {"const": "A106"},
        "evaluation_scope": {"const": SCOPE}, "score_meaning": {"const": "conditional_signed_log_evidence_ratio"},
        "value": {"type": ["number", "null"]}, "available_value": {"type": ["number", "null"]},
        "status": {"enum": ["complete", "partial", "unavailable"]}, "unit": {"const": "natural_log_ratio"},
        "unavailable_reasons": strings, "conditions": strings,
        "selected_components": contributors,
        "source_refs": {"type": "array", "items": {**REF, "x-reference-namespace": "source"}, "uniqueItems": True},
        "evidence_measurement_keys": strings, "input_origins": strings,
        "annotation_credit": {"type": "null"}})


def cells_schema():
    fields = deepcopy(cell_schema()["properties"])
    fields["sheet_ref"] = {**REF, "x-reference-namespace": "source"}
    return {"type": "array", "x-source": NAMESPACE, "items": obj(fields)}


def finalize_a106(arguments, source_cells):
    """Combine possessed current assessments without inventing missing scores."""
    validate_schema(arguments, population_schema())
    validate_schema(source_cells, intervention_cells_schema())
    args, rows = deepcopy(arguments), deepcopy(source_cells)
    experiments = [row["experiment_ref"] for row in args["experiments"]]
    if len(experiments) != len(set(experiments)):
        raise ContractError("a106_duplicate_experiment")
    if args["assertion_ref"] == args["comparison_ref"]:
        raise ContractError("a106_distinct_comparison_required")
    if (args["revises_subscore_ref"] is None) != (args["revision_reason"] is None):
        raise ContractError("a106_revision_reason_required")
    by_sheet = {row["sheet_ref"]: row for row in rows}
    selected = [entry["sheet_ref"] for entry in args["experiments"] if entry["sheet_ref"] is not None]
    if len(by_sheet) != len(rows) or len(set(selected)) != len(selected) or set(by_sheet) != set(selected):
        raise ContractError("a106_selected_components_not_received")
    reasons, available, owners = [], [], {}
    for index, entry in enumerate(args["experiments"]):
        ref = entry["sheet_ref"]
        if ref is not None and entry["missing_reason"] is not None:
            raise ContractError("a106_existing_assessment_requires_null_missing_reason", detail={
                "field": "experiments." + str(index) + ".missing_reason", "sheet_ref": ref,
                "requirement": "Keep the selected assessment sheet and set missing_reason to null, even when its score is unavailable. Its unresolved criteria remain in the selected assessment."})
        if ref is None and entry["missing_reason"] is None:
            raise ContractError("a106_missing_experiment_reason_required")
        if ref is None:
            reasons.append("experiment_score_missing:" + entry["experiment_ref"])
            continue
        row = by_sheet[ref]
        if (row["component"] != SCORE_COMPONENT or row["unit"] != "dimensionless" or row["experiment_ref"] != entry["experiment_ref"]
                or row["assertion_ref"] != args["assertion_ref"] or row["comparison_ref"] != args["comparison_ref"]):
            raise ContractError("a106_assessment_binding_mismatch")
        for key in row["evidence_measurement_keys"]:
            if key in owners and owners[key] != entry["experiment_ref"]:
                reasons.append("shared_observed_measurement")
            owners[key] = entry["experiment_ref"]
        if row["value"] is None or row["status"] not in {"populated", "conditional"}:
            reasons.append("experiment_score_unavailable:" + entry["experiment_ref"])
        elif type(row["value"]) not in (int, float) or not math.isfinite(row["value"]):
            raise ContractError("a106_finite_score_required")
        else:
            available.append(row)
    dependence = args["dependence"]
    if len(experiments) > 1 and (dependence["status"] != "independent" or not dependence["witnesses"]):
        reasons.append("between_experiment_independence_unresolved")
    if not experiments:
        reasons.append("no_experiments_selected")
    subtotal = None
    combinable = not {"shared_observed_measurement", "between_experiment_independence_unresolved"}.intersection(reasons)
    if available and (combinable or len(available) == 1):
        try:
            subtotal = math.fsum(row["value"] for row in available)
            if not math.isfinite(subtotal):
                raise OverflowError
        except (OverflowError, ValueError):
            subtotal = None
            reasons.append("numerical_range")
    unique = lambda values: list(dict.fromkeys(values))
    result = {**args, "component": COMPONENTS[0], "axis": "A106", "evaluation_scope": SCOPE,
        "score_meaning": "conditional_signed_log_evidence_ratio", "value": subtotal if not reasons else None,
        "available_value": subtotal, "status": "complete" if not reasons else "partial" if subtotal is not None else "unavailable",
        "unit": "natural_log_ratio", "unavailable_reasons": unique(reasons),
        "conditions": unique(["fixed_assertion_and_alternative_predictions", "current_assessment_per_original_experiment",
            *(["conditional_independence_between_experiments"] if len(experiments) > 1 else []),
            *(condition for row in rows for condition in row["conditions"])]),
        "selected_components": rows,
        "source_refs": unique([*(ref for row in rows for ref in [row["sheet_ref"], *row["source_refs"]]),
            *(w["source_ref"] for w in dependence["witnesses"])]),
        "evidence_measurement_keys": list(owners),
        "input_origins": unique(origin for row in rows for origin in row["input_origins"]), "annotation_credit": None}
    validate_schema(result, cell_schema())
    return result


def annotation_scalar(cell):
    """Reuse the existing tanh-half-log-ratio convention after axis aggregation."""
    from collections.abc import Mapping
    from ..root_axis_scalars import _number, _result
    axis = 'A106'
    if not isinstance(cell, Mapping):
        raise ValueError('root_scalar_log_evidence_input_required')
    expected = 'overall' if axis == 'A105' else 'experimental_subscore'
    if cell.get('component') != expected:
        raise ValueError('root_scalar_final_axis_component_required')
    value = cell.get('value')
    if value is not None:
        _number(value)
    complete = cell.get('status') == 'complete' and value is not None
    if complete and (cell.get('unit') != ('dimensionless' if axis == 'A105' else 'natural_log_ratio')
            or axis == 'A105' and cell.get('source_component_names') != ['source_log_evidence_ratio']):
        raise ValueError('root_scalar_natural_log_ratio_required')
    return _result(axis, math.tanh(value / 2) if complete else None,
        formula='tanh(current_complete_axis_log_evidence_ratio/2)', inputs=cell,
        reasons=() if complete else ('complete_axis_log_evidence_ratio_unavailable',))
