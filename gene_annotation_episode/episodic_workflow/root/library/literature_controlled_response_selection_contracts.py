from __future__ import annotations

from copy import deepcopy
from gene_annotation_episode.domain import REF
from .literature_partner_defined_units import defined_rate_unit_schema

def obj(properties):
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}


def ref(name):
    return {"$ref": "#/$defs/" + name}


def array(items, minimum=0):
    return {"type": "array", "items": items, "minItems": minimum}


def nullable(value):
    return {"anyOf": [value, {"type": "null"}]}


def enum(values):
    return {"enum": list(values)}


TEXT = {"type": "string", "minLength": 1}
OFFSET = {"type": "integer", "minimum": 0}
ROLES = ("protein_condition1", "empty_condition1", "protein_condition0", "empty_condition0")
WITNESS_FIELDS = {"source_ref": deepcopy(REF), "representation": enum(("original", "text")),
    "start": OFFSET, "end": {"type": "integer", "minimum": 1}, "quote": TEXT}
defs = {"NativeTextWitness": obj(WITNESS_FIELDS),
    "TextWitness": obj({"kind": {"const": "text"}, **WITNESS_FIELDS}),
    "Box": {"type": "array", "minItems": 4, "maxItems": 4, "items": OFFSET}}
defs["ImageWitness"] = obj({"kind": {"const": "image"}, "image_id": TEXT,
    "region": ref("Box"), "quote": TEXT})
defs["Witness"] = {"oneOf": [ref("TextWitness"), ref("ImageWitness")]}
defs["NumberSelector"] = obj({"witness": ref("NativeTextWitness"),
    "number_start": OFFSET, "number_end": {"type": "integer", "minimum": 1}})
defs["UnitSelection"] = {"anyOf": [ref("NativeTextWitness"), defined_rate_unit_schema()]}


def interpretation(values):
    return obj({"value": enum(values), "witnesses": array(ref("Witness"))})


defs["Correspondence"] = interpretation(("same", "unknown", "conflicting"))
defs["Meaning"] = obj({"status": enum(("known", "unknown", "conflicting")),
    "label": nullable(TEXT), "witnesses": array(ref("Witness")),
    "canonical_witness": nullable(ref("Witness")), "canonical_correspondence": ref("Correspondence")})
defs["Literal"] = obj({"status": enum(("exact", "ambiguous", "unreadable", "conflicting")),
    "candidates": array(ref("NumberSelector")), "fragments": array(ref("Witness"))})
defs["AxisLiteral"] = obj({"status": enum(("exact", "ambiguous", "unreadable", "conflicting")),
    "candidates": array(ref("Witness")), "fragments": array(ref("Witness"))})
defs["Image"] = obj({"image_id": TEXT, "source_ref": deepcopy(REF),
    "original_source_ref": deepcopy(REF), "mapping": nullable(obj({"original_region": ref("Box"),
        "colour_conversion": enum(("preserve", "rgb"))}))})
defs["TextMeasurement"] = obj({"kind": {"const": "source_literal"},
    "literal": ref("Literal"), "unit": nullable(ref("UnitSelection"))})
defs["BarSelection"] = obj({
    "roi": obj({name: OFFSET for name in ("left", "top", "right", "bottom")}),
    "rgb_min": {"type": "array", "items": {"type": "integer", "minimum": 0, "maximum": 255}, "minItems": 3, "maxItems": 3},
    "rgb_max": {"type": "array", "items": {"type": "integer", "minimum": 0, "maximum": 255}, "minItems": 3, "maxItems": 3},
    "minimum_row_fraction": {"type": "number", "exclusiveMinimum": 0, "maximum": 1},
    "minimum_run_rows": {"type": "integer", "minimum": 1},
    "edge_tolerance_pixels": {"type": "number", "minimum": 0}})
defs['GraphMeasurement'] = obj({'kind': {'const': 'linear_bar'}, 'image_id': TEXT, 'bar_selection': ref('BarSelection'), 'axis': obj({'first': obj({'pixel': {'type': 'number', 'minimum': 0}, 'tick': ref('AxisLiteral')}), 'second': obj({'pixel': {'type': 'number', 'minimum': 0}, 'tick': ref('AxisLiteral')}), 'unit': ref('AxisLiteral'), 'scale': ref('AxisScale')}), 'terminal_edge': enum(('upper', 'lower'))})
defs["CISelector"] = obj({"witness": ref("NativeTextWitness"),
    **{name: OFFSET for name in ("lower_start", "lower_end", "upper_start", "upper_end")}})
defs["Uncertainty"] = obj({
    "statistic": interpretation(("sd", "sem", "ci", "unspecified", "unreported", "unknown", "conflicting")),
    "magnitude": nullable(ref("NumberSelector")), "interval": nullable(ref("CISelector")),
    "unit": nullable(ref("UnitSelection")),
    "unit_relationship": interpretation(("same_as_response", "explicit_unit", "unknown", "conflicting")),
    "confidence_level": nullable(ref("NativeTextWitness")), "count": nullable(ref("NumberSelector")),
    "repetition_basis": interpretation(("biological_preparations", "technical_measurements", "unspecified", "unknown", "conflicting")),
    "estimate_basis": interpretation(("fit_to_averaged_curve", "between_fitted_parameters", "unknown", "conflicting"))})
defs["Arm"] = obj({"source_kind": enum(("primary_source", "retained_extraction", "synthetic_fixture")),
    "context": obj({name: nullable(ref("Witness")) for name in
        ("subject", "organism", "genotype", "construct", "preparation", "experimental_system")}),
    "protein_arrangement": interpretation(("protein_present", "protein_free_control", "empty_vector_control", "other_specified", "unknown", "conflicting")),
    **{name: ref("Meaning") for name in ("subject_construct", "condition", "endpoint", "normalization", "physical_observation")},
    "intended_factor_level": nullable(ref("Witness")),
    "measurement": nullable({"oneOf": [ref("TextMeasurement"), ref("GraphMeasurement")]}),
    "reported_uncertainty": ref("Uncertainty")})
defs["Relationships"] = obj({"condition1_target": ref("Meaning"), "condition0_target": ref("Meaning"),
    "condition_levels_relation": interpretation(("same", "different", "unknown", "conflicting")),
    "subject_construct_across_conditions": interpretation(("same", "different", "unknown", "conflicting")),
    **{name: interpretation(("matched_condition_control", "shared_reference_assumption", "unknown", "conflicting"))
        for name in ("condition1_control_application", "condition0_control_application")},
    "control_reference_reuse": interpretation(("distinct_observations", "same_reference_with_stated_invariance", "unknown", "conflicting")),
    "nonintended_conditions": interpretation(("matched", "different", "unknown", "conflicting")),
    "intended_factor": nullable(ref("Witness"))})
defs["CovarianceBinding"] = obj({"variable_index": OFFSET, "label_witness": ref("NativeTextWitness"),
    "owner_witness": ref("Witness"), "correspondence": ref("Correspondence")})
defs['AxisScale'] = obj({'status': enum(('known', 'unknown', 'conflicting')), 'kind': nullable(enum(('linear', 'logarithmic', 'nonlinear'))), 'basis': enum(('source_text_literal', 'image_episode_interpretation', 'unresolved')), 'witnesses': {'type': 'array', 'items': ref('Witness')}})
defs['AxisScale']['allOf'] = [{'if': {'properties': {'status': {'const': 'known'}}}, 'then': {'properties': {'kind': enum(('linear', 'logarithmic', 'nonlinear')), 'basis': enum(('source_text_literal', 'image_episode_interpretation')), 'witnesses': {'minItems': 1}}}, 'else': {'properties': {'kind': {'type': 'null'}, 'basis': {'const': 'unresolved'}}}}]
selection = obj({'version': {'const': 'controlled_response_source_selection_v3'}, 'source_ref': deepcopy(REF), 'images': array(ref('Image')), 'arms': obj({role: nullable(ref('Arm')) for role in ROLES}), 'relationships': ref('Relationships'), 'covariance': nullable(obj({'source_ref': deepcopy(REF), 'bindings': obj({role: nullable(ref('CovarianceBinding')) for role in ROLES})})), 'variance_status': interpretation(('known', 'estimated', 'unknown')), 'model_kind': interpretation(('none', 'known_joint_normal_source_means'))})
selection["$defs"] = defs
selection["$schema"] = "https://json-schema.org/draft/2020-12/schema"

_SELECTION_SCHEMA = selection


def _selection_core_schema():
    """Closed arm, relationship and covariance nominations; numerical scientific operands are never inputs."""
    return deepcopy(_SELECTION_SCHEMA)


