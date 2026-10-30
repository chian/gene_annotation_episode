"""Closed supplied-input contracts for calibrated retention-time measurements.

This is a pure measurement boundary. Source references are supplied provenance,
not proof of source authorization, calibration applicability or wet-lab work.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import json
import math

from .domain import ContractError, obj, validate_schema


SHEET_VERSION = "calibrated_signal_sheet_v1"
COMPONENTS_VERSION = "calibrated_signal_components_v1"
SELECTION_VERSION = "calibrated_signal_selection_v1"
TEXT = {"type": "string", "minLength": 1}
NUMBER = {"type": "number"}
SIGNAL_KINDS = ("sampled_signal", "peak_height", "integrated_area")
RELATIONS = ("point", "less_than", "less_or_equal", "greater_than", "greater_or_equal")
QUALIFICATIONS = ["supplied_sources_and_roles_are_not_authenticated_by_this_pure_calculator",
    "retention_time_association_does_not_establish_chemical_identity",
    "no_peak_picking_integration_or_calibration_fitting",
    "no_uncertainty_propagation_or_independence_assumption",
    "association_competitors_are_the_declared_analysis_population",
    "exact_declared_units_and_quantity_basis_required"]


class CalibratedSignalContractError(ValueError):
    def __init__(self, code, field):
        self.code, self.field = code, field
        super().__init__(code + ":" + field)


def nullable(schema):
    return {"anyOf": [deepcopy(schema), {"type": "null"}]}


def array(schema, *, unique=False):
    return {"type": "array", "items": deepcopy(schema), **({"uniqueItems": True} if unique else {})}


def provenance_schema():
    return obj({"source_ref": deepcopy(TEXT), "pointer": {"type": "string",
        "pattern": r"^(?:$|/(?:[^~]|~[01])*)$"}})


def basis_schema():
    return obj({"kind": {"enum": ["mass_of_element", "mass_of_analyte", "amount_of_analyte"]},
        "identity": deepcopy(TEXT)})


def uncertainty_schema():
    return obj({"representation": {"enum": ["plus_minus", "interval"]},
        "magnitude": nullable(NUMBER),
        "lower": nullable(NUMBER), "upper": nullable(NUMBER),
        "statistic": {"enum": ["SD", "SE", "standard_uncertainty", "CI", "unspecified"]},
        "coverage": nullable(NUMBER),
        "unit": nullable(TEXT), "source": provenance_schema()})


def quantity_schema():
    return obj({"value": nullable(NUMBER), "unit": nullable(TEXT),
        "relation": {"enum": list(RELATIONS)}, "uncertainty": nullable(uncertainty_schema()),
        "source": provenance_schema()})


def context_facts_schema():
    return array(obj({"name": deepcopy(TEXT), "value": {"type": ["string", "number", "boolean", "null"]},
        "unit": nullable(TEXT), "source": provenance_schema()}))


def sample_schema():
    dilution = obj({"factor": quantity_schema(),
        "applicability": {"enum": ["supported", "unknown", "conflicting", "unsupported"]},
        "source": provenance_schema()})
    measurement = obj({"measurement_id": deepcopy(TEXT), "retention_time": nullable(NUMBER),
        "signal": quantity_schema(), "source": provenance_schema()})
    return obj({"sample_id": deepcopy(TEXT), "source": provenance_schema(),
        "context_ref": nullable(TEXT), "context_facts": context_facts_schema(),
        "representation": {"enum": ["sampled_points", "declared_peaks"]},
        "signal_kind": {"enum": list(SIGNAL_KINDS)}, "retention_time_unit": nullable(TEXT),
        "signal_unit": nullable(TEXT), "measurements": array(measurement), "dilution": nullable(dilution)})


def species_schema():
    return obj({"species_id": deepcopy(TEXT), "label": deepcopy(TEXT),
        "reference_retention_time": nullable(NUMBER), "retention_time_unit": nullable(TEXT),
        "context_ref": nullable(TEXT), "quantity_basis": nullable(basis_schema()),
        "source": provenance_schema()})


def calibration_schema():
    signal_range = obj({"lower": nullable(NUMBER), "upper": nullable(NUMBER),
        "lower_inclusive": {"type": "boolean"}, "upper_inclusive": {"type": "boolean"},
        "unit": nullable(TEXT), "source": provenance_schema()})
    lower_bound = obj({"value": deepcopy(NUMBER), "inclusive": {"type": "boolean"},
        "unit": nullable(TEXT), "source": provenance_schema()})
    threshold = obj({"threshold_id": deepcopy(TEXT), "kind": {"enum": ["LOD", "LOQ"]},
        "value": nullable(NUMBER), "unit": nullable(TEXT), "quantity_basis": nullable(basis_schema()),
        "concentration_basis": {"enum": ["aliquot", "original_sample"]},
        "below_relation": {"enum": ["less_than", "less_or_equal"]},
        "lower_bound": nullable(lower_bound), "uncertainty": nullable(uncertainty_schema()),
        "source": provenance_schema()})
    factor = obj({"value": nullable(NUMBER), "signal_unit": nullable(TEXT),
        "concentration_unit": nullable(TEXT), "uncertainty": nullable(uncertainty_schema()),
        "source": provenance_schema()})
    return obj({"calibration_id": deepcopy(TEXT), "species_id": deepcopy(TEXT),
        "signal_kind": {"enum": list(SIGNAL_KINDS)}, "signal_unit": nullable(TEXT),
        "concentration_unit": nullable(TEXT), "quantity_basis": nullable(basis_schema()),
        "offset": quantity_schema(), "concentration_per_signal": factor,
        "applicability": {"enum": ["supported", "unknown", "conflicting", "unsupported"]},
        "context_ref": nullable(TEXT), "context_facts": context_facts_schema(),
        "signal_range": nullable(signal_range), "thresholds": array(threshold),
        "source": provenance_schema()})


def association_schema():
    return obj({"method": {"const": "unique_nearest"}, "tolerance": quantity_schema(),
        "analysis_species_ids": array(TEXT, unique=True),
        "edge": {"enum": ["inclusive", "exclusive"]},
        "collision_policy": {"const": "ambiguous"}, "source": provenance_schema()})


def calibrated_signal_sheet_schema():
    return obj({"version": {"const": SHEET_VERSION}, "samples": array(sample_schema()),
        "species": array(species_schema()), "calibrations": array(calibration_schema()),
        "association": association_schema()})


def calibrated_signal_selection_schema():
    return obj({"version": {"const": SELECTION_VERSION},
        **{name: array(TEXT, unique=True) for name in ("sample_ids", "species_ids", "calibration_ids")}})


def exact_schema():
    return obj({"numerator": {"type": "string", "pattern": "^-?[0-9]+$"},
        "denominator": {"type": "string", "pattern": "^[1-9][0-9]*$"}})


def cell_schema():
    return obj({"value": nullable(NUMBER), "exact_value": nullable(exact_schema()),
        "unit": nullable(TEXT), "quantity_basis": nullable(basis_schema()),
        "state": {"enum": ["present", "qualified", "unavailable"]}, "reason": nullable(TEXT),
        "formula": deepcopy(TEXT), "input_paths": array(TEXT), "qualifications": array(TEXT),
        "uncertainty": obj({"state": {"const": "not_propagated"},
            "reason": {"const": "no_selected_joint_uncertainty_model"}})})


def calibrated_signal_components_schema():
    exact = nullable(exact_schema())
    candidate = obj({"measurement_id": deepcopy(TEXT), "measurement_ordinal": {"type": "integer", "minimum": 0},
        "absolute_rt_difference": exact, "eligible": {"type": ["boolean", "null"]}, "reason": nullable(TEXT)})
    association = obj({"state": {"enum": ["assigned", "no_match", "unavailable", "ambiguous"]},
        "reason": nullable(TEXT), "measurement_id": nullable(TEXT), "measurement_ordinal": {"type": ["integer", "null"], "minimum": 0},
        "candidates": array(candidate), "competing_species_ids": array(TEXT), "qualifications": array(TEXT)})
    bound = obj({"lower": nullable(NUMBER), "lower_inclusive": {"type": ["boolean", "null"]},
        "upper": deepcopy(NUMBER), "upper_relation": {"enum": ["less_than", "less_or_equal"]},
        "unit": deepcopy(TEXT), "quantity_basis": basis_schema()})
    censor = obj({"threshold_id": deepcopy(TEXT), "kind": {"enum": ["LOD", "LOQ"]},
        "concentration_basis": {"enum": ["aliquot", "original_sample"]},
        "selected_relation": {"enum": ["less_than", "less_or_equal"]},
        "state": {"enum": ["below", "not_below", "unavailable"]}, "reason": nullable(TEXT),
        "estimate": cell_schema(), "reported_bound": nullable(bound), "input_paths": array(TEXT)})
    row = obj({"sample_id": deepcopy(TEXT), "species_id": deepcopy(TEXT),
        "sample_ordinal": {"type": "integer", "minimum": 0}, "species_ordinal": {"type": "integer", "minimum": 0},
        "representation": {"enum": ["sampled_points", "declared_peaks"]},
        "signal_kind": {"enum": list(SIGNAL_KINDS)}, "association": association,
        "selected_calibration_ids": array(TEXT), "calibration_id": nullable(TEXT),
        "calibration_range_state": {"enum": ["within", "outside", "unknown", "invalid", "unavailable"]},
        "linear_estimate": cell_schema(), "aliquot_concentration": cell_schema(),
        "original_sample_concentration": cell_schema(), "censoring": array(censor), "qualifications": array(TEXT)})
    uncertainty_assessment = obj({"input_path": deepcopy(TEXT),
        "representation_state": {"enum": ["consistent", "incomplete", "conflicting"]},
        "coverage_state": {"enum": ["not_supplied", "supplied_ci", "incomplete", "conflicting", "unassessed"]},
        "unit_state": {"enum": ["matched", "missing", "mismatched", "unknown", "unassessed"]},
        "issues": array(TEXT), "statistical_validity": {"const": "not_assessed"}})
    return obj({"version": {"const": COMPONENTS_VERSION}, "sheet": calibrated_signal_sheet_schema(),
        "selection": calibrated_signal_selection_schema(),
        "population": obj({**{name: {"type": "integer", "minimum": 0} for name in (
            "supplied_sample_count", "supplied_species_count", "selected_sample_count", "selected_species_count", "returned_row_count")},
            "association_species_ids": array(TEXT),
            "association_competitor_basis": {"const": "declared_analysis_population"},
            "replicate_pooling": {"const": False}}),
        "rows": array(row), "uncertainty_assessments": array(uncertainty_assessment),
        "unassigned_measurements": array(obj({"sample_id": deepcopy(TEXT),
            "measurement_ids": array(TEXT)})), "qualifications": array(TEXT)})


def copy_json(value):
    try:
        return json.loads(json.dumps(value, allow_nan=False))
    except (TypeError, ValueError, OverflowError) as error:
        raise CalibratedSignalContractError("finite_json_required", "/") from error


def _validate(value, schema):
    result = copy_json(value)
    try:
        validate_schema(result, schema)
    except ContractError as error:
        path = "/" + "/".join(str(p) for p in error.detail.get("field_path", []))
        raise CalibratedSignalContractError("closed_calibrated_signal_shape_required", path) from error
    return result


def _unique(rows, name, path):
    values = [row[name] for row in rows]
    if len(values) != len(set(values)):
        raise CalibratedSignalContractError("duplicate_identity", path)


def validate_calibrated_signal_sheet(sheet):
    value = _validate(sheet, calibrated_signal_sheet_schema())
    for name, key in (("samples", "sample_id"), ("species", "species_id"), ("calibrations", "calibration_id")):
        _unique(value[name], key, "/" + name)
    species_ids = {s["species_id"] for s in value["species"]}
    if not set(value["association"]["analysis_species_ids"]) <= species_ids:
        raise CalibratedSignalContractError("unknown_analysis_species_identity", "/association/analysis_species_ids")
    for i, sample in enumerate(value["samples"]):
        _unique(sample["measurements"], "measurement_id", f"/samples/{i}/measurements")
        if (sample["representation"] == "sampled_points") != (sample["signal_kind"] == "sampled_signal"):
            raise CalibratedSignalContractError("representation_signal_kind_conflict", f"/samples/{i}")
    for i, calibration in enumerate(value["calibrations"]):
        if calibration["species_id"] not in species_ids:
            raise CalibratedSignalContractError("unknown_species_identity", f"/calibrations/{i}/species_id")
        _unique(calibration["thresholds"], "threshold_id", f"/calibrations/{i}/thresholds")
    return value


def validate_calibrated_signal_selection(selection, sheet):
    value = _validate(selection, calibrated_signal_selection_schema())
    for name, key, selected in (("samples", "sample_id", "sample_ids"), ("species", "species_id", "species_ids"),
            ("calibrations", "calibration_id", "calibration_ids")):
        known = {row[key] for row in sheet[name]}
        if not set(value[selected]) <= known:
            raise CalibratedSignalContractError("unknown_selected_identity", "/" + selected)
    if not set(value["species_ids"]) <= set(sheet["association"]["analysis_species_ids"]):
        raise CalibratedSignalContractError("selected_species_outside_analysis_population", "/species_ids")
    return value


def exact_value(value):
    fraction = value if isinstance(value, Fraction) else Fraction(value)
    return {"numerator": str(fraction.numerator), "denominator": str(fraction.denominator)}


def calculated_cell(value, *, unit, basis, formula, paths, reason=None, qualifications=()):
    numeric = None
    if value is not None:
        try:
            numeric = float(value)
            if not math.isfinite(numeric):
                numeric, reason = None, "binary64_overflow"
            elif numeric == 0 and value != 0:
                numeric, reason = None, "binary64_nonzero_underflow"
        except (OverflowError, ValueError):
            numeric, reason = None, "binary64_overflow"
    return {"value": numeric, "exact_value": None if value is None else exact_value(value),
        "unit": unit, "quantity_basis": deepcopy(basis), "state": "unavailable" if numeric is None else
        "qualified" if qualifications else "present", "reason": reason,
        "formula": formula, "input_paths": list(paths), "qualifications": list(qualifications),
        "uncertainty": {"state": "not_propagated", "reason": "no_selected_joint_uncertainty_model"}}


def validate_calibrated_signal_components_shape(components):
    return _validate(components, calibrated_signal_components_schema())


__all__ = ["SHEET_VERSION", "COMPONENTS_VERSION", "SELECTION_VERSION", "CalibratedSignalContractError",
    "calibrated_signal_sheet_schema", "calibrated_signal_selection_schema", "calibrated_signal_components_schema",
    "validate_calibrated_signal_sheet", "validate_calibrated_signal_selection", "validate_calibrated_signal_components_shape"]
