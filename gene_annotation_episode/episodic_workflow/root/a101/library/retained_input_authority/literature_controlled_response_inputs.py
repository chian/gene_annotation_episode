"""Source-bound four-arm inputs within A105; no scientific sheet calculation.

Selections assign scientific meanings. Exact bytes/geometry establish custody
only; original runtime authorization and outcome binding remain caller owned.
The v1 profile retains its original text/structured covariance semantics and
unimplemented graph nominations. Explicit HOST stages also serve full v2, whose
graph facade supplies actual063 measurements before shared science assembly.
"""
from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a101.domain import REF
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.literature_partner_defined_units import defined_rate_unit_schema

def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}

def ref(name):
    return {'$ref': '#/$defs/' + name}

def array(items, minimum=0):
    return {'type': 'array', 'items': items, 'minItems': minimum}

def nullable(value):
    return {'anyOf': [value, {'type': 'null'}]}

def enum(values):
    return {'enum': list(values)}
TEXT = {'type': 'string', 'minLength': 1}
OFFSET = {'type': 'integer', 'minimum': 0}
ROLES = ('protein_condition1', 'empty_condition1', 'protein_condition0', 'empty_condition0')

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
defs["GraphMeasurement"] = obj({"kind": {"const": "linear_bar"}, "image_id": TEXT,
    "bar_selection": ref("BarSelection"), "axis": obj({
        "first": obj({"pixel": {"type": "number", "minimum": 0}, "tick": ref("AxisLiteral")}),
        "second": obj({"pixel": {"type": "number", "minimum": 0}, "tick": ref("AxisLiteral")}),
        "unit": ref("AxisLiteral")})})
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
selection = obj({"version": {"const": "controlled_response_source_selection_v1"},
    "source_ref": deepcopy(REF), "images": array(ref("Image")),
    "arms": obj({role: nullable(ref("Arm")) for role in ROLES}), "relationships": ref("Relationships"),
    "covariance": nullable(obj({"source_ref": deepcopy(REF),
        "bindings": obj({role: nullable(ref("CovarianceBinding")) for role in ROLES})})),
    "variance_status": interpretation(("known", "estimated", "unknown")),
    "model_kind": interpretation(("none", "known_joint_normal_source_means"))})
selection["$defs"] = defs
selection["$schema"] = "https://json-schema.org/draft/2020-12/schema"
_SELECTION_SCHEMA = selection
DEPENDENCIES = {'literature_assay_inputs.py': '52069b7d974556631a18d132eaa8bd79b23efc5b7dc2a583b1fff73df4758b6e', 'literature_rate_native_inputs.py': '55244315a64d0940c09d0410a9d1e930f73609e7d0d34ef5ed751a5bbad71500', 'literature_partner_source_fields.py': '20fd7866318fff00d80dcf3109c3a2589c36a38e35329d1b63ca954f2c035a17', 'literature_partner_defined_units.py': 'cc6733d763ba494e3c4016a9a3be98ea6b7b6076b97dc8ef1aad5f43a8f856ca', 'literature_kinetic_inputs.py': '78e0c0094bbffa8306c26a6d134eec74f291c34177a87656ec09f925c2dd1960', 'literature_binding_visual_inputs.py': '8153f555699cd9b1dea63bd8ccc29869c70e127c205bdb10fd26c979b202b718', 'literature_binding_reader.py': 'e117105486773280edf1dba796ab2be10c61feb6a9c0ad407ba876e2332714a1', 'literature_controlled_response_calculations.py': 'a75b8f8ef4905d805be24e86236ef8303c97b5e4761acf0d849ca01aadaec023'}

def controlled_response_arguments_schema():
    """Closed nominations only; numerical scientific operands are never inputs."""
    return deepcopy(_SELECTION_SCHEMA)
