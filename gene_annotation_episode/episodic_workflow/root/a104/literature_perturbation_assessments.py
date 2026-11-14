"""A106 experiment identity and assessment revisions; no new scoring policy.

The existing point/summary readers and calculators own the numbers. This layer
links their saved results to one actual experiment and one revisable question.
It never treats a source format, report, or revised judgment as another assay.
"""
from copy import deepcopy
import hashlib
import json

from .domain import ContractError, REF, obj, validate_schema
from .communication import plain


EXPERIMENT_TYPES = {
    "intervention_response": {
        "question": "What does the intervention establish about the molecule's contribution to the observed outcome?",
        "designs": ("native_deletion_restoration", "selective_perturbation_restoration",
                    "cas_free_reconstitution", "variant_replacement", "other_explicit",
                    "unknown", "conflicting"),
        "considerations": (
            "actual molecule, recipient, donor, coexisting copies and required partners",
            "intended intervention, measured extent and unintended amount changes",
            "same endpoint, eligibility denominator, normalization, conditions and timing",
            "measurement calibration, detection limits and source uncertainty",
            "reference/intervention contrast and genuinely separate restoration arm if present",
            "nuisance amount comparability versus endpoint-scale alternative-effect bounds",
            "biological/preparation/technical units, pairing and shared controls",
        ),
        "reader": "read_perturbation_inputs",
        "calculators": ("populate_source_restoration", "populate_source_summary_restoration"),
        "combination": "Existing within-experiment source restoration product; no new cross-experiment rule.",
    },
}


def assessment_schema():
    reference = {**REF, "x-reference-namespace": "reference"}
    source = {**REF, "x-reference-namespace": "source"}
    text = {"type": "string", "minLength": 1}
    return obj({
        "experiment_ref": reference,
        "experiment_type": {"enum": list(EXPERIMENT_TYPES)},
        "assessment_key": text,
        "scientific_question": text,
        "conclusion": text,
        "limitations": {"type": "array", "items": text},
        "revision_reason": {"type": ["string", "null"], "minLength": 1},
        "revises_sheet_ref": {**source, "type": ["string", "null"]},
    })


def validate_assessment(value):
    validate_schema(value, assessment_schema())
    for key in ("assessment_key", "scientific_question", "conclusion"):
        if not value[key].strip():
            raise ContractError("perturbation_assessment_text_required")
    if any(not item.strip() for item in value["limitations"]):
        raise ContractError("perturbation_assessment_text_required")
    if (value["revises_sheet_ref"] is None) != (value["revision_reason"] is None):
        raise ContractError("perturbation_revision_reason_required")
    if value["revision_reason"] is not None and not value["revision_reason"].strip():
        raise ContractError("perturbation_revision_reason_required")


def authorize_assessment(repository, context, value):
    """Use an explicitly received, sourced assay identity; never infer identity."""
    validate_assessment(value)
    ref = value["experiment_ref"]
    if ref not in context.received_record_refs:
        raise ContractError("perturbation_experiment_not_received")
    record = repository.store.get(ref)
    if record["record_type"] != "reference" or record.get("reference_type") != "assay":
        raise ContractError("perturbation_experiment_reference_required")
    if not repository.store.reference_subset([ref], plain(context.scope)):
        raise ContractError("perturbation_experiment_outside_scope")
    repository._source(context, record["source_ref"])
    if value["revises_sheet_ref"] is not None:
        repository._source(context, value["revises_sheet_ref"])


def current_assessments(repository):
    """Read current assessments, retaining one head per experiment/question key.

    This is an inventory, not a numerical aggregate or an independence count.
    Historical unlinked sheets remain available through their original APIs.
    """
    histories, superseded = {}, set()
    for row in repository.store.db.execute(
        f"SELECT outcome FROM {repository.operations_table} WHERE run_id=?", (repository.run_id,)
    ):
        outcome = json.loads(row["outcome"])
        result = outcome.get("result") or {}
        assessment = result.get("experiment_assessment")
        if assessment is None:
            continue
        saved = repository.read(result["sheet_ref"])
        if saved.get("experiment_assessment") != assessment:
            raise ContractError("perturbation_assessment_saved_mismatch")
        histories[result["sheet_ref"]] = deepcopy(assessment)
        if assessment["revises_sheet_ref"] is not None:
            superseded.add(assessment["revises_sheet_ref"])
    heads = [{"sheet_ref": ref, **value} for ref, value in histories.items() if ref not in superseded]
    keys = [(v["experiment_ref"], v["assessment_key"]) for v in heads]
    if len(keys) != len(set(keys)):
        raise ContractError("perturbation_assessment_conflicting_heads")
    return sorted(heads, key=lambda v: (v["experiment_ref"], v["assessment_key"]))


def check_revision(repository, value):
    """Call inside the publication transaction so stale writers cannot branch."""
    heads = current_assessments(repository)
    head = next((v for v in heads if (v["experiment_ref"], v["assessment_key"]) ==
                 (value["experiment_ref"], value["assessment_key"])), None)
    expected = head["sheet_ref"] if head else None
    if expected != value["revises_sheet_ref"]:
        raise ContractError("perturbation_assessment_revision_required" if expected else
                            "perturbation_assessment_predecessor_mismatch")


def validate_saved_assessment(repository, saved, request):
    expected = request["arguments"].get("experiment_assessment")
    if saved.get("experiment_assessment") != expected:
        raise ContractError("perturbation_assessment_saved_mismatch")
    if expected is not None:
        validate_assessment(expected)
        # New assessment metadata is authenticated against the immutable
        # request, sheet bytes and selected outcome, not just matching labels.
        operation = repository.store.db.execute(
            f"SELECT outcome FROM {repository.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?",
            (repository.run_id, request["episode_id"], request["operation_key"]),
        ).fetchone()
        outcome = json.loads(operation["outcome"])
        source = repository.store.get(outcome["result"]["sheet_ref"])
        for field in ("artifact_ref", "request_ref"):
            raw = repository.store.get_artifact(source[field])
            if "artifact_" + hashlib.sha256(raw).hexdigest() != source[field]:
                raise ContractError("perturbation_assessment_artifact_mismatch")
        if outcome["result"].get("experiment_assessment") != expected:
            raise ContractError("perturbation_assessment_saved_mismatch")
        if saved["experimental_bindings"]["experiment_ref"] != expected["experiment_ref"]:
            raise ContractError("perturbation_assessment_experiment_mismatch")


def assessment_history(repository, sheet_ref):
    """Reconstruct revisions from saved results, without reading original data."""
    rows, seen, key = [], set(), None
    while sheet_ref is not None:
        if sheet_ref in seen:
            raise ContractError("perturbation_assessment_revision_cycle")
        seen.add(sheet_ref)
        saved = repository.read(sheet_ref)
        value = saved.get("experiment_assessment")
        if value is None:
            raise ContractError("perturbation_assessment_required")
        actual = (value["experiment_ref"], value["assessment_key"])
        if key is not None and actual != key:
            raise ContractError("perturbation_assessment_predecessor_mismatch")
        key = actual
        rows.append({"sheet_ref": sheet_ref, **deepcopy(value)})
        sheet_ref = value["revises_sheet_ref"]
    return list(reversed(rows))
