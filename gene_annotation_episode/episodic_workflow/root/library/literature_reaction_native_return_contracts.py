"""Original reaction native-observation declarations and return schema."""
from gene_annotation_episode.domain import obj
from .literature_reaction_return_contracts import BINDINGS
from .literature_reaction_native_inputs import RATIO_BASES, COUNT_BASES, UNCERTAINTY_KINDS

NAMESPACE = "literature_reaction_native_observations"
POSITIONS_FIELD = "requested_reaction_native_positions"


def positions_schema():
    return {"type": "array", "uniqueItems": True, "items": {"anyOf": [
        {"type": "integer", "minimum": 0}, {"type": "string", "const": "all"}]}}


def native_observations_schema():
    def ref(kind, nullable=False):
        return {"type": ["string", "null"] if nullable else "string", "format": "reference",
                "x-reference-namespace": kind}
    number = {"type": ["number", "null"]}
    return {"type": "array", "x-source": NAMESPACE, "items": obj({
        **{name: ref("source") for name in ("sheet_ref", "evidence_source_ref", "data_source_ref")},
        **{field: ref(kind, True) for field, (_, kind) in BINDINGS.items()},
        "observation_position": {"type": "integer", "minimum": 0},
        "measurement_ref": ref("reference"), "resource_ref": ref("reference", True),
        "source_number_refs": {"type": "array", "items": ref("reference")},
        "basis_refs": {"type": "array", "items": ref("reference")},
        "count_basis_refs": {"type": "array", "items": ref("reference")},
        "uncertainty_basis_refs": {"type": "array", "items": ref("reference")},
        "count_number_ref": ref("reference", True), "uncertainty_number_ref": ref("reference", True),
        "source_unit_ref": ref("reference", True),
        "operand_role": {"type": "string", "enum": ["ratio_summary", "ratio_observation",
            "resource_value", "resource_lower", "resource_upper"]},
        "value": dict(number), "reported_value": dict(number),
        "numerator_value": dict(number), "denominator_value": dict(number),
        "unit": {"type": "string", "enum": ["mol_per_mol", "signal_per_signal", "umol", "uM", "umol_per_min", "uM_per_min"]},
        "source_unit": {"type": ["string", "null"], "enum": [None, "pmol", "nmol", "umol", "mmol", "nM", "uM", "mM",
            *[u + "/" + t for u in ("pmol", "nmol", "umol", "mmol", "nM", "uM", "mM") for t in ("s", "min")]]},
        "ratio_kind": {"type": ["string", "null"], "enum": [None, "product_pair", "formed_per_consumed", "formed_per_supplied", "signal_ratio"]},
        "ratio_form": {"type": "string", "enum": ["reported_point", "normalized_reported_pair", "not_extracted", "not_ratio"]},
        "measurement_basis": {"type": ["string", "null"], "enum": [None, *RATIO_BASES]},
        "reported_count": {"type": ["integer", "null"], "minimum": 1},
        "count_basis": {"type": "string", "enum": list(COUNT_BASES)},
        "independent_n": {"type": ["integer", "null"], "minimum": 1},
        "uncertainty_kind": {"type": "string", "enum": list(UNCERTAINTY_KINDS)},
        "uncertainty_value": {**number, "minimum": 0},
        "transformation": {"type": "string", "enum": ["identity", "normalize_reported_pair", "unit_conversion", "not_extracted"]},
        "evaluation_scope": {"type": "string", "const": "native_reference_reaction_operands"},
        "measurement_corrections": {"type": "string", "const": "not_applied"},
        "origin": {"type": "string", "enum": ["reported", "graph_derived", "synthetic"]}})}


