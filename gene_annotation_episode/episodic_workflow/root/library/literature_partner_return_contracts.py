"""Original gel/partner declarations and return schemas; no source work or population."""
from __future__ import annotations

from copy import deepcopy
from gene_annotation_episode.domain import obj
from ..literature_assay_inputs import SOURCE_KINDS

COMPONENTS = (
    "reference_rate", "omitted_rate", "addback_rate", "partner_loss",
    "partner_loss_fraction", "addback_gain", "addback_fraction",
    "restored_reference_fraction",
)
FORMULA_CODES = dict(zip(COMPONENTS, (
    "native_partner_reference_v1", "native_partner_omitted_v1", "native_partner_addback_v1",
    "partner_reference_minus_omitted_v1", "partner_loss_over_reference_v1",
    "partner_addback_minus_omitted_v1", "partner_gain_over_loss_v1", "partner_gain_over_reference_v1")))
BINDINGS = {
    "subject_ref": ("subject", "reference"),
    "partner_ref": ("partner", "reference"),
    "experiment_ref": ("experiment", "reference"),
    "endpoint_ref": ("endpoint", "term"),
    "normalization_ref": ("normalization", "term"),
    "reference_condition_ref": ("reference_condition", "context"),
    "omitted_condition_ref": ("omitted_condition", "context"),
    "addback_condition_ref": ("addback_condition", "context"),
    "function_ref": ("function", "term"),
}
NATIVE_UNITS = ("pmol/min/mg", "nmol/min/mg", "umol/min/mg", "per_min", "per_s", "uM/min", "nM/min")
CHECK_REASONS = (
    "arm_unreported", "nonpartner_conditions_differ", "subject_unreported", "subject_mismatch",
    "partner_unreported", "partner_mismatch", "endpoint_unreported", "endpoint_mismatch",
    "normalization_unreported", "normalization_mismatch", "unit_unreported", "unit_mismatch",
    "partner_presence_not_established", "condition_factor_scope_unresolved", "conditions_incomplete",
    "measurement_identity_unreported", "role_measurement_not_distinct",
)
REASONS = (*CHECK_REASONS, "measurement_unreported", "censored_point_unreported",
    "nonpositive_reference_domain", "zero_or_straddling_loss_domain", "numerical_model_range")
_ROLES = ("reference", "omitted", "addback")
_FIXED_METADATA = {
    "evaluation_scope": "reference_experimental_partner_components",
    "target_correspondence": "not_evaluated", "partner_necessity": "not_inferred",
    "statistical_uncertainty": "not_evaluated", "measurement_corrections": "not_applied",
}
def _spread_schema():
    return obj({"kind": {"type": "string", "enum": ["SD", "SEM", "CI", "unspecified", "unreported"]},
        "magnitude": {"type": ["number", "null"], "minimum": 0}})


def _arm_metadata_schema():
    arm = obj({"partner_state": {"type": "string", "enum": ["present", "absent", "unreported"]},
        "condition_coverage": {"type": "string", "enum": ["complete", "partial", "unreported"]},
        "spread": _spread_schema()})
    return obj({role: {**deepcopy(arm), "type": ["object", "null"]} for role in _ROLES})


def _check_schema(*, raw=False):
    return obj({"status": {"type": "string", "enum": ["matched", "different", "unresolved"]},
        ("differing_factors" if raw else "differing_factor_refs"): {"type": "array", "items": ({"type": "string", "minLength": 1} if raw else {"type": "string", "format": "reference", "x-reference-namespace": "term"}), "uniqueItems": True},
        "unavailable_reason": {"type": ["string", "null"], "enum": [None, *CHECK_REASONS]}})


def _checks_schema(*, raw=False):
    return obj({name: _check_schema(raw=raw) for name in ("reference_omitted", "addback_omitted")})


def _cell_schema():
    return obj({**{field: {"type": ["number", "null"]} for field in ("value", "lower", "upper")},
        "unit": {"type": ["string", "null"], "enum": [*NATIVE_UNITS, "dimensionless", None]},
        "origin": {"type": ["string", "null"], "enum": ["reported", "graph_derived", "synthetic", "derived", None]},
        "bound_kind": {"type": "string", "enum": ["point_only_not_uncertainty", "conditional_input_domain_not_CI"]},
        "status": {"type": "string", "enum": ["populated", "bounded", "unavailable"]},
        "unavailable_reason": {"type": ["string", "null"], "enum": [None, *REASONS]}})


def partner_cells_schema():
    """Closed numerical and source-meaning rows, without raw numerical recipes."""
    source = {"type": "string", "format": "reference", "x-reference-namespace": "source"}
    properties = {
        **{field: dict(source) for field in ("sheet_ref", "evidence_source_ref", "data_source_ref")},
        **{field: {"type": ["string", "null"], "format": "reference", "x-reference-namespace": kind}
            for field, (_, kind) in BINDINGS.items()},
        "component": {"type": "string", "enum": list(COMPONENTS)},
        **deepcopy(_cell_schema()["properties"]),
        "formula_code": {"type": "string", "enum": list(FORMULA_CODES.values())},
        "source_kind": {"type": "string", "enum": list(SOURCE_KINDS)},
        "comparison_checks": _checks_schema(), "arm_metadata": _arm_metadata_schema(),
        **{field: {"type": "string", "enum": [value]} for field, value in _FIXED_METADATA.items()}}
    return {"type": "array", "items": obj(properties), "x-source": "literature_partner_cells"}


