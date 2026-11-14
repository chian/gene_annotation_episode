"""Original figure selections, meanings and closed population contract."""
from copy import deepcopy
from gene_annotation_episode.domain import REF, obj
from ..literature_assay_inputs import SOURCE_KINDS, _nullable
from .literature_rate_unit_witness_schema import _witness_schema

VERSION = "a105_figure_inputs_v1"
DATA_VERSION = "literature_figure_selection_v1"
LITERAL_FIELDS = ("first_subject", "first_partner", "second_subject", "second_partner",
                  "experiment", "endpoint", "first_condition", "second_condition",
                  "normalization", "function")
COMPONENTS = ("first_ordinate", "second_ordinate", "ordinate_difference")
REASONS = ("no_bar_pixels", "ambiguous_bar_runs", "truncated_mean_edge",
           "numerical_model_range", "missing_ordinate", "second_ordinate_unreported",
           "ordinate_unit_mismatch")
ARRANGEMENTS = ("coexisting_sequential_catalysts", "coexisting_complex", "single_molecule", "unresolved")
CONTRAST_KINDS = ("source_representation", "partner_swap", "other", "unreported")
ENDPOINT_SCOPES = ("coupled_final_product", "direct_subject_step", "binding", "indirect_response", "unreported")
NORMALIZATION_BASES = ("reported_relative_turnover", "arbitrary_signal", "concentration", "unreported")
MEASUREMENT_RELATIONS = ("same_physical_measurement", "distinct_physical_measurements", "unresolved")
REPEAT_KINDS = ("biological", "technical", "unknown")
SPREAD_KINDS = ("SD", "SEM", "CI", "unspecified", "unreported")
IMAGE_ORIGINS = ("published", "synthetic")
_ARGS = ("source_ref", "data_source_ref", "source_kind", "literals", "interpretation_witnesses")
_DESIGN_ENUMS = {"arrangement": ARRANGEMENTS, "contrast_kind": CONTRAST_KINDS,
    "endpoint_scope": ENDPOINT_SCOPES, "normalization_basis": NORMALIZATION_BASES,
    "measurement_relation": MEASUREMENT_RELATIONS}


def figure_population_schema():
    """Closed selected arguments; pixels and selections come from retained bytes."""
    witness = _witness_schema()
    return obj({"source_ref": deepcopy(REF), "data_source_ref": deepcopy(REF),
        "source_kind": {"enum": list(SOURCE_KINDS)},
        "literals": obj({field: _nullable(deepcopy(witness)) for field in LITERAL_FIELDS}),
        "interpretation_witnesses": {"type": "array", "items": deepcopy(witness)}})


