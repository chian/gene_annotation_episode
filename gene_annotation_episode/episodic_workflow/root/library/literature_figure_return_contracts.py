"""Original figure return contracts and endpoint operation selection."""
from copy import deepcopy
from gene_annotation_episode.domain import obj
from ..literature_assay_inputs import SOURCE_KINDS
from .literature_figure_input_contracts import COMPONENTS, REASONS, figure_population_schema

PROVIDER = "literature.experimental.figure"
FORMULA_CODES = {
    "first_ordinate": "native_first_bar_linear_v1",
    "second_ordinate": "native_second_bar_linear_v1",
    "ordinate_difference": "native_first_minus_second_v1",
}
BINDINGS = {
    "first_subject_ref": ("first_subject", "reference"),
    "first_partner_ref": ("first_partner", "reference"),
    "second_subject_ref": ("second_subject", "reference"),
    "second_partner_ref": ("second_partner", "reference"),
    "experiment_ref": ("experiment", "reference"),
    "endpoint_ref": ("endpoint", "term"),
    "first_condition_ref": ("first_condition", "context"),
    "second_condition_ref": ("second_condition", "context"),
    "normalization_ref": ("normalization", "term"),
    "function_ref": ("function", "term"),
}
NATIVE_UNITS = ("relative_turnover_percent", "arbitrary_signal", "nanomolar")
BOUND_KIND = "conditional_digitization_not_confidence_interval"
_FIXED_METADATA = {
    "evaluation_scope": "reference_experimental_figure_ordinates",
    "statistical_uncertainty": "not_extracted",
    "measurement_corrections": "not_applied",
    "target_correspondence": "not_evaluated",
    "partner_necessity": "not_evaluated",
}


def _repeat_schema():
    return obj({"reported_n": {"type": ["integer", "null"], "minimum": 1},
        "repeat_kind": {"type": "string", "enum": ["biological", "technical", "unknown"]},
        "independent_preparation_count": {"type": ["integer", "null"], "minimum": 1},
        "spread_kind": {"type": "string", "enum": ["SD", "SEM", "CI", "unspecified", "unreported"]},
        "spread_numeric_status": {"type": "string", "enum": ["not_extracted", "unreported"]}})


def _design_schema():
    return obj({
        "arrangement": {"type": "string", "enum": ["coexisting_sequential_catalysts", "coexisting_complex",
            "single_molecule", "unresolved"]},
        "contrast_kind": {"type": "string", "enum": ["source_representation", "partner_swap", "other", "unreported"]},
        "endpoint_scope": {"type": "string", "enum": ["coupled_final_product", "direct_subject_step", "binding",
            "indirect_response", "unreported"]},
        "normalization_basis": {"type": "string", "enum": ["reported_relative_turnover", "arbitrary_signal",
            "concentration", "unreported"]},
        "measurement_relation": {"type": "string", "enum": ["same_physical_measurement",
            "distinct_physical_measurements", "unresolved"]},
        "first_repeat": _repeat_schema(),
        "second_repeat": {**_repeat_schema(), "type": ["object", "null"]}})


def _cell_schema():
    return obj({**{field: {"type": ["number", "null"]} for field in ("value", "lower", "upper")},
        "unit": {"type": ["string", "null"], "enum": [*NATIVE_UNITS, "relative_turnover_percentage_points", None]},
        "origin": {"type": "string", "enum": ["graph_derived", "derived"]},
        "bound_kind": {"type": "string", "enum": [BOUND_KIND]},
        "status": {"type": "string", "enum": ["populated", "unavailable"]},
        "unavailable_reason": {"type": ["string", "null"], "enum": [None, *REASONS]}})


def figure_cells_schema():
    """Closed scientific rows; pixel selections remain in saved custody only."""
    source = {"type": "string", "format": "reference", "x-reference-namespace": "source"}
    properties = {
        **{field: dict(source) for field in ("sheet_ref", "evidence_source_ref", "data_source_ref",
            "first_image_source_ref")},
        "second_image_source_ref": {**source, "type": ["string", "null"]},
        **{field: {"type": ["string", "null"], "format": "reference", "x-reference-namespace": kind}
            for field, (_, kind) in BINDINGS.items()},
        "component": {"type": "string", "enum": list(COMPONENTS)},
        **deepcopy(_cell_schema()["properties"]),
        "formula_code": {"type": "string", "enum": list(FORMULA_CODES.values())},
        "source_kind": {"type": "string", "enum": list(SOURCE_KINDS)},
        "first_image_origin": {"type": "string", "enum": ["published", "synthetic"]},
        "second_image_origin": {"type": ["string", "null"], "enum": ["published", "synthetic", None]},
        "design": _design_schema(),
        "first_axis_unit": {"type": "string", "enum": list(NATIVE_UNITS)},
        "second_axis_unit": {"type": ["string", "null"], "enum": [*NATIVE_UNITS, None]},
        **{field: {"type": "string", "enum": [value]} for field, value in _FIXED_METADATA.items()}}
    # Explicit types are required by the parent form's closed-schema checker.
    for field, schema in properties.items():
        if "type" not in schema and "enum" in schema:
            schema["type"] = ["string", "null"] if None in schema["enum"] else "string"
    return {"type": "array", "items": obj(properties), "x-source": "literature_figure_cells"}


def figure_operation_schema():
    """Explicit endpoint branch alongside the unchanged native bar contract."""
    from .literature_endpoint_signal_contracts import endpoint_signal_operation_schema
    return {"type": "object", "anyOf": [figure_population_schema(), endpoint_signal_operation_schema()]}


