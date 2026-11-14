"""Pure four-cell reported binding-parameter interaction, one A105 component.

Inputs are already interpreted source records, not acquired evidence. No label
matching, custody check, protein-input correction, independence assumption or
annotation-credit aggregation is performed here. IC50 and reported Hill Kd are
distinct definitions. Source-reported limits support printed-threshold arithmetic
only, never confidence/true-parameter bounds or known-normal point likelihoods.

Closed input shape (all fields mandatory, unknown fields explicitly null):
  {version: INPUT_VERSION, parameter_kind: ic50|reported_hill_kd, unit: nM,
   comparison_scope: reported_protocols|common_conditions,
   operands: {role: null|operand for role in ROLES},
   relationships: {name: {status, sources: [witness,...]} for name in RELATIONS}}
Operand: {value, relation, reported_spread, origin, context, canonical_ids,
          physical_fit_id, uncertainty, source, expression}.
Context and canonical_ids each contain exactly CONTEXT_FIELDS and ID_FIELDS,
respectively, with nonempty source labels/IDs or null. IDs are source-assigned
scientific mappings, not fuzzy-normalized spellings. Source is a witness:
  {source_ref, artifact_ref, kind: utf8_span, start, end}, or
  {source_ref, artifact_ref, kind: image_region, region: [x0,y0,x1,y1]}, or
  {source_ref, artifact_ref, kind: table_cell, table_id, row_index, column}.
Uncertainty is null (metadata unresolved/not supplied) or the closed object
{statistic, basis, interval, confidence_level, exact_count, minimum_count,
 repetition_basis}. Null is distinct from the supplied statistic unreported.
Reported_spread independently retains a finite nonnegative symmetric magnitude
or null. A known SD/SEM/unspecified statistic may have unavailable magnitude.
A confidence interval has no symmetric spread; its interval may be null or two
individually nullable endpoints, and its confidence level may independently be
null. Missing endpoints never mean infinity. Supplied pieces stay unaltered and
receive finite role-qualified partial meanings. None of these pieces supplies
the separate covariance/model required for statistical cells.

Core relationship statuses: supported|unknown|conflicting. common_conditions:
matched|not_matched|unknown|conflicting. Non-unknown claims need witnesses.
Pair mappings require equal, known canonical subject/construct/state/parameter
definition/readout/normalization IDs and distinct known ligand IDs. Full D also
requires cross-pair ligand correspondence and common parameter definition.
Preparations/experiments are retained, never interpreted as independence.

Optional model: {version: MODEL_VERSION, parameter_kind, measurement_order,
 measurement_keys, physical_fit_ids, log_basis: natural_log_nM,
 distribution: normal|unspecified, variance_status: known|estimated|unknown,
 log_covariance: null|4x4 matrix, source: witness,
 reporting_event: unknown|source_defined, reporting_event_source: null|witness}.
Known/estimated covariance requires actual physical owners and a full symmetric
positive-semidefinite matrix. Unknown status can retain but does not use a matrix.
S=e*abs(e)/(2V), B=tanh(S/2) require uncensored points and known-normal V>0.
The numerical cells are dependent representations, not independent evidence.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import hashlib
import json
import math

from .literature_experimental_contracts import ExperimentalContractError

INPUT_VERSION = "binding_interaction_inputs_v1"
MODEL_VERSION = "binding_interaction_log_model_v1"
SHEET_VERSION = "binding_interaction_sheet_v1"
ROLES = ("reference_subject_reference_ligand", "reference_subject_test_ligand",
         "test_subject_reference_ligand", "test_subject_test_ligand")
CONTEXT_FIELDS = ("subject", "construct", "state", "preparation", "experiment",
                  "ligand", "tracer", "readout", "normalization", "conditions")
ID_FIELDS = CONTEXT_FIELDS + ("parameter_definition",)
RELATIONS = ("within_reference_subject", "within_test_subject",
             "ligand_correspondence", "parameter_definition", "separate_assays",
             "common_conditions")
UNCERTAINTY_PARTIAL_CODES = (
    "uncertainty_metadata_unresolved", "reported_uncertainty_magnitude_unknown",
    "confidence_interval_endpoints_incomplete", "confidence_level_unknown",
)
_PAIR_IDS = ("subject", "construct", "state", "parameter_definition", "readout",
             "normalization")
_COEFFICIENTS = (-1, 1, 1, -1)


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _keys(value, fields, field):
    if not isinstance(value, dict) or set(value) != set(fields):
        _fail("closed_fields_required", field)


def _text(value, field, *, nullable=False):
    if value is None and nullable:
        return
    if not isinstance(value, str) or not value.strip():
        _fail("nonempty_source_token_required", field)


def _choice(value, choices, field):
    if not isinstance(value, str) or value not in choices:
        _fail("unsupported_value", field)


def _finite(value, field, *, nullable=False, positive=False, nonnegative=False):
    if value is None and nullable:
        return
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        _fail("finite_number_required", field)
    if positive and value <= 0:
        _fail("positive_number_required", field)
    if nonnegative and value < 0:
        _fail("nonnegative_number_required", field)


def _integer(value, field, *, minimum=0, nullable=False):
    if value is None and nullable:
        return
    if type(value) is not int or value < minimum:
        _fail("integer_range_required", field)


def _witness(value, field):
    if not isinstance(value, dict):
        _fail("source_witness_required", field)
    kind = value.get("kind")
    base = ("source_ref", "artifact_ref", "kind")
    if kind == "utf8_span":
        _keys(value, base + ("start", "end"), field)
        for name in ("start", "end"):
            _integer(value[name], field + "." + name)
        if value["end"] <= value["start"]:
            _fail("nonempty_byte_span_required", field)
    elif kind == "table_cell":
        _keys(value, base + ("table_id", "row_index", "column"), field)
        _text(value["table_id"], field + ".table_id")
        _text(value["column"], field + ".column")
        _integer(value["row_index"], field + ".row_index")
    elif kind == "image_region":
        _keys(value, base + ("region",), field)
        region = value["region"]
        if not isinstance(region, list) or len(region) != 4:
            _fail("four_pixel_coordinates_required", field + ".region")
        for index, coordinate in enumerate(region):
            _integer(coordinate, f"{field}.region[{index}]")
        if region[2] <= region[0] or region[3] <= region[1]:
            _fail("nonempty_image_region_required", field + ".region")
    else:
        _fail("unsupported_source_witness_kind", field + ".kind")
    for name in ("source_ref", "artifact_ref"):
        _text(value[name], field + "." + name)


def _uncertainty(operand, field):
    value = operand["uncertainty"]
    spread = operand["reported_spread"]
    _finite(spread, field.rsplit(".", 1)[0] + ".reported_spread", nullable=True, nonnegative=True)
    if value is None:
        if operand["relation"] == "unreported" and spread is not None:
            _fail("symmetric_spread_not_applicable", field)
        return
    _keys(value, ("statistic", "basis", "interval", "confidence_level",
                  "exact_count", "minimum_count", "repetition_basis"), field)
    statistic = value["statistic"]
    _choice(statistic, ("sd", "sem", "confidence_interval", "unspecified", "unreported"),
            field + ".statistic")
    _choice(value["basis"], ("fit_to_averaged_curve",
            "between_independent_fitted_parameters", "unknown"), field + ".basis")
    _choice(value["repetition_basis"], ("biological_preparations",
            "technical_measurements", "assay_occasions", "unspecified"),
            field + ".repetition_basis")
    if statistic in ("unreported", "confidence_interval"):
        if spread is not None:
            _fail("symmetric_spread_not_applicable", field)
    if statistic == "confidence_interval":
        interval = value["interval"]
        if interval is not None:
            if not isinstance(interval, list) or len(interval) != 2:
                _fail("confidence_interval_endpoints_required", field + ".interval")
            for endpoint in interval:
                # Retain source endpoints outside the positive parameter
                # domain, and preserve missing endpoints without infinity.
                _finite(endpoint, field + ".interval", nullable=True)
            if all(endpoint is not None for endpoint in interval) and interval[0] > interval[1]:
                _fail("ordered_interval_required", field + ".interval")
        _finite(value["confidence_level"], field + ".confidence_level", nullable=True, positive=True)
        if value["confidence_level"] is not None and value["confidence_level"] >= 1:
            _fail("confidence_probability_required", field + ".confidence_level")
    elif value["interval"] is not None or value["confidence_level"] is not None:
        _fail("confidence_interval_not_applicable", field)
    for name in ("exact_count", "minimum_count"):
        _integer(value[name], field + "." + name, minimum=1, nullable=True)
    if (value["exact_count"] is not None and value["minimum_count"] is not None
            and value["exact_count"] < value["minimum_count"]):
        _fail("exact_count_below_minimum", field)
    if operand["relation"] == "unreported" and statistic != "unreported":
        _fail("unreported_parameter_uncertainty", field)


def _uncertainty_qualifications(inputs):
    """Finite missing meanings, without changing numeric or model availability."""
    for role in ROLES:
        operand = inputs["operands"][role]
        if operand is None:
            continue
        uncertainty = operand["uncertainty"]
        if uncertainty is None:
            yield UNCERTAINTY_PARTIAL_CODES[0] + ":" + role
        elif uncertainty["statistic"] in ("sd", "sem", "unspecified"):
            if operand["reported_spread"] is None:
                yield UNCERTAINTY_PARTIAL_CODES[1] + ":" + role
        elif uncertainty["statistic"] == "confidence_interval":
            interval = uncertainty["interval"]
            if interval is None or any(endpoint is None for endpoint in interval):
                yield UNCERTAINTY_PARTIAL_CODES[2] + ":" + role
            if uncertainty["confidence_level"] is None:
                yield UNCERTAINTY_PARTIAL_CODES[3] + ":" + role


def validate_binding_interaction_inputs(inputs):
    """Check closed representations; source truth and custody remain external."""
    _keys(inputs, ("version", "parameter_kind", "unit", "comparison_scope",
                   "operands", "relationships"), "inputs")
    if inputs["version"] != INPUT_VERSION:
        _fail("unsupported_interaction_version", "inputs.version")
    _choice(inputs["parameter_kind"], ("ic50", "reported_hill_kd"), "inputs.parameter_kind")
    if inputs["unit"] != "nM":
        _fail("canonical_nM_required", "inputs.unit")
    _choice(inputs["comparison_scope"], ("reported_protocols", "common_conditions"),
            "inputs.comparison_scope")
    _keys(inputs["operands"], ROLES, "inputs.operands")
    for role, operand in inputs["operands"].items():
        path = "inputs.operands." + role
        if operand is None:
            continue
        _keys(operand, ("value", "relation", "reported_spread", "origin", "context",
                       "canonical_ids", "physical_fit_id", "uncertainty", "source",
                       "expression"), path)
        _choice(operand["relation"], ("eq", "lt", "le", "gt", "ge", "unreported"),
                path + ".relation")
        if operand["relation"] == "unreported":
            if operand["value"] is not None:
                _fail("unreported_value_must_be_null", path + ".value")
        else:
            _finite(operand["value"], path + ".value", positive=True)
        _choice(operand["origin"], ("reported", "visual_transcription", "synthetic"),
                path + ".origin")
        for block, fields in (("context", CONTEXT_FIELDS), ("canonical_ids", ID_FIELDS)):
            _keys(operand[block], fields, path + "." + block)
            for name in fields:
                _text(operand[block][name], path + "." + block + "." + name, nullable=True)
        _text(operand["physical_fit_id"], path + ".physical_fit_id", nullable=True)
        _text(operand["expression"], path + ".expression")
        _witness(operand["source"], path + ".source")
        _uncertainty(operand, path + ".uncertainty")
    _keys(inputs["relationships"], RELATIONS, "inputs.relationships")
    for name, relationship in inputs["relationships"].items():
        path = "inputs.relationships." + name
        _keys(relationship, ("status", "sources"), path)
        statuses = (("matched", "not_matched", "unknown", "conflicting")
                    if name == "common_conditions" else ("supported", "unknown", "conflicting"))
        _choice(relationship["status"], statuses, path + ".status")
        if not isinstance(relationship["sources"], list):
            _fail("source_witness_list_required", path + ".sources")
        if relationship["status"] != "unknown" and not relationship["sources"]:
            _fail("relationship_witness_required", path + ".sources")
        for index, source in enumerate(relationship["sources"]):
            _witness(source, f"{path}.sources[{index}]")
    return deepcopy(inputs)


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode("utf-8")).hexdigest()


def _operand_keys(inputs):
    return {role: (None if operand is None else _digest({"parameter_kind":
            inputs["parameter_kind"], "unit": inputs["unit"], "operand": operand}))
            for role, operand in inputs["operands"].items()}


def binding_interaction_operand_keys(inputs):
    """Exact complete estimate keys, distinct from physical-source identities."""
    return _operand_keys(validate_binding_interaction_inputs(inputs))


def _psd(matrix):
    """Exact rational Schur complements: PSD, including valid singular matrices."""
    work = [[Fraction(value) for value in row] for row in matrix]
    for pivot in range(4):
        diagonal = work[pivot][pivot]
        if diagonal < 0:
            return False
        if diagonal == 0:
            if any(work[pivot][j] != 0 for j in range(pivot + 1, 4)):
                return False
            continue
        for i in range(pivot + 1, 4):
            for j in range(i, 4):
                value = work[i][j] - work[i][pivot] * work[pivot][j] / diagonal
                work[i][j] = work[j][i] = value
    return True


def _validate_model(model, inputs, keys):
    if model is None:
        return None
    _keys(model, ("version", "parameter_kind", "measurement_order", "measurement_keys",
                  "physical_fit_ids", "log_basis", "distribution", "variance_status",
                  "log_covariance", "source", "reporting_event", "reporting_event_source"), "model")
    if model["version"] != MODEL_VERSION:
        _fail("unsupported_interaction_model_version", "model.version")
    if model["parameter_kind"] != inputs["parameter_kind"]:
        _fail("binding_parameter_kind_mismatch", "model.parameter_kind")
    if model["measurement_order"] != list(ROLES):
        _fail("model_measurement_order_mismatch", "model.measurement_order")
    if model["measurement_keys"] != [keys[role] for role in ROLES]:
        _fail("model_estimate_owner_mismatch", "model.measurement_keys")
    physical = [None if inputs["operands"][role] is None else
                inputs["operands"][role]["physical_fit_id"] for role in ROLES]
    if model["physical_fit_ids"] != physical:
        _fail("model_physical_owner_mismatch", "model.physical_fit_ids")
    if model["log_basis"] != "natural_log_nM":
        _fail("natural_log_nM_required", "model.log_basis")
    _choice(model["distribution"], ("normal", "unspecified"), "model.distribution")
    _choice(model["variance_status"], ("known", "estimated", "unknown"), "model.variance_status")
    _witness(model["source"], "model.source")
    _choice(model["reporting_event"], ("unknown", "source_defined"), "model.reporting_event")
    if model["reporting_event_source"] is not None:
        _witness(model["reporting_event_source"], "model.reporting_event_source")
    if (model["reporting_event"] == "source_defined") != (model["reporting_event_source"] is not None):
        _fail("reporting_event_source_mismatch", "model.reporting_event_source")
    matrix = model["log_covariance"]
    if model["variance_status"] != "unknown" and (matrix is None or any(x is None for x in physical)):
        _fail("actual_covariance_and_physical_owners_required", "model")
    if matrix is not None:
        if (not isinstance(matrix, list) or len(matrix) != 4 or
                any(not isinstance(row, list) or len(row) != 4 for row in matrix)):
            _fail("four_by_four_covariance_required", "model.log_covariance")
        for i, row in enumerate(matrix):
            for j, value in enumerate(row):
                _finite(value, f"model.log_covariance[{i}][{j}]")
                if matrix[j][i] != value:
                    _fail("symmetric_covariance_required", "model.log_covariance")
        if not _psd(matrix):
            _fail("positive_semidefinite_covariance_required", "model.log_covariance")
        for i in range(4):
            for j in range(i):
                if physical[i] is not None and physical[i] == physical[j] and matrix[i] != matrix[j]:
                    _fail("shared_physical_covariance_mismatch", "model.log_covariance")
    return deepcopy(model)


def _cell(operands, formula, unit="dimensionless", *, value=None, threshold=None,
          relation=None, status="unavailable", reason=None):
    return {"operands": list(operands), "formula": formula, "unit": unit,
            "value": value, "threshold": threshold, "relation": relation,
            "status": status, "reason": reason}


def _condition_reason(inputs, indices):
    status = inputs["relationships"]["common_conditions"]["status"]
    if inputs["comparison_scope"] == "common_conditions" and status != "matched":
        return "common_conditions_" + status
    if inputs["comparison_scope"] == "common_conditions":
        known = {inputs["operands"][ROLES[i]]["canonical_ids"]["conditions"] for i in indices}
        known.discard(None)
        if len(known) > 1:
            return "common_conditions_claim_conflicts_with_canonical_ids"
    return None


def _relation_reason(inputs, name):
    status = inputs["relationships"][name]["status"]
    return None if status == "supported" else name + "_" + status


def _mapping_reason(inputs, indices, fields):
    records = [inputs["operands"][ROLES[i]] for i in indices]
    for name in fields:
        values = [record["canonical_ids"][name] for record in records]
        if any(value is None for value in values):
            return "canonical_" + name + "_unknown"
        if any(value != values[0] for value in values[1:]):
            return "canonical_" + name + "_conflicting"
    return None


def _available_reason(inputs, indices):
    for index in indices:
        operand = inputs["operands"][ROLES[index]]
        if operand is None:
            return "missing_operand:" + ROLES[index]
        if operand["relation"] == "unreported":
            return "unreported_operand:" + ROLES[index]
    for position, index in enumerate(indices):
        operand = inputs["operands"][ROLES[index]]
        for other_index in indices[:position]:
            other = inputs["operands"][ROLES[other_index]]
            if _digest(operand["source"]) == _digest(other["source"]):
                return "reused_source_token"
            if (operand["physical_fit_id"] is not None
                    and operand["physical_fit_id"] == other["physical_fit_id"]):
                return "reused_physical_fit"
    return None


def _pair_reason(inputs, indices, relationship):
    reason = (_available_reason(inputs, indices) or _relation_reason(inputs, relationship)
              or _mapping_reason(inputs, indices, _PAIR_IDS))
    if reason:
        return reason
    ids = [inputs["operands"][ROLES[i]]["canonical_ids"]["ligand"] for i in indices]
    if None in ids:
        return "canonical_ligand_unknown"
    if ids[0] == ids[1]:
        return "ligand_roles_not_distinct"
    return _condition_reason(inputs, indices)


def _interaction_reason(inputs, pair_reasons):
    reason = next((reason for reason in pair_reasons if reason), None)
    if reason:
        return reason
    reason = (_available_reason(inputs, range(4))
              or _relation_reason(inputs, "ligand_correspondence")
              or _relation_reason(inputs, "parameter_definition")
              or _relation_reason(inputs, "separate_assays")
              or _mapping_reason(inputs, (0, 2), ("ligand",))
              or _mapping_reason(inputs, (1, 3), ("ligand",))
              or _mapping_reason(inputs, range(4), ("parameter_definition",))
              or _condition_reason(inputs, range(4)))
    if reason:
        return reason
    reference = inputs["operands"][ROLES[0]]["canonical_ids"]
    test = inputs["operands"][ROLES[2]]["canonical_ids"]
    if all(reference[name] == test[name] for name in ("subject", "construct", "state")):
        return "subject_roles_not_distinct"
    return None


def _weighted_logs(inputs, indices, coefficients):
    # Take the exact rational contrast before logging. This avoids cancellation
    # of separately rounded logs and still works when the ratio overflows float.
    exact = Fraction(1)
    for index, coefficient in zip(indices, coefficients):
        operand = Fraction(inputs["operands"][ROLES[index]]["value"])
        exact *= operand if coefficient == 1 else 1 / operand
    delta = exact - 1
    if abs(delta) < Fraction(1, 2):
        rounded_delta = float(delta)
        if rounded_delta == 0 and delta != 0:
            return None
        return math.log1p(rounded_delta)
    return math.log(exact.numerator) - math.log(exact.denominator)


def _arithmetic(inputs, indices, coefficients, *, log=False, reason=None):
    names = [ROLES[index] for index in indices]
    formula = ("sum(c_i * ln(p_i))" if log else "product(p_i ** c_i)")
    cell = _cell(names, {"expression": formula, "coefficients": list(coefficients)})
    if reason:
        cell["reason"] = reason
        return cell
    directions, strict = set(), False
    for index, coefficient in zip(indices, coefficients):
        relation = inputs["operands"][ROLES[index]]["relation"]
        if relation != "eq":
            direction = 1 if relation in ("gt", "ge") else -1
            directions.add(direction * coefficient)
            strict |= relation in ("gt", "lt")
    if len(directions) > 1:
        cell["reason"] = "opposing_reported_limits"
        return cell
    if log:
        value = _weighted_logs(inputs, indices, coefficients)
    else:
        exact = Fraction(1)
        for index, coefficient in zip(indices, coefficients):
            operand = Fraction(inputs["operands"][ROLES[index]]["value"])
            exact *= operand if coefficient == 1 else 1 / operand
        try:
            value = float(exact)
        except OverflowError:
            value = math.inf
    if value is None or not math.isfinite(value) or (not log and value == 0):
        cell["reason"] = "numerical_representation_range"
        return cell
    if directions:
        direction = next(iter(directions))
        relation = ("gt" if strict else "ge") if direction > 0 else ("lt" if strict else "le")
        cell.update(threshold=value, relation=relation, status="reported_limit_arithmetic")
    else:
        cell.update(value=value, relation="eq", status="computed")
    return cell


def _as_float(exact):
    try:
        value = float(exact)
    except OverflowError:
        return None
    if not math.isfinite(value) or (value == 0 and exact != 0):
        return None
    return value


def _sqrt_fraction(exact):
    if exact == 0:
        return 0.0
    # A variance outside binary64 can still have a representable square root.
    return math.exp((math.log(exact.numerator) - math.log(exact.denominator)) / 2)


def populate_binding_interaction(inputs, model=None):
    """Return twelve dependent numerical cells, with explicit partial failures.

    This does not count observations, select a model, establish source receipt or
    add evidence across comparisons. Across calls, shared controls keep their
    source and physical-fit IDs and must be handled as shared by any consumer.
    """
    inputs = validate_binding_interaction_inputs(inputs)
    keys = _operand_keys(inputs)
    model = _validate_model(model, inputs, keys)
    cells = {}
    for index, role in enumerate(ROLES):
        operand = inputs["operands"][role]
        cell = _cell((role,), "reported parameter", "nM")
        if operand is None:
            cell["reason"] = "missing_operand:" + role
        elif operand["relation"] == "unreported":
            cell["reason"] = "unreported_operand:" + role
        elif operand["relation"] == "eq":
            cell.update(value=operand["value"], relation="eq", status="reported")
        else:
            cell.update(threshold=operand["value"], relation=operand["relation"],
                        status="reported_limit")
        cells[("parameter_rr", "parameter_rt", "parameter_tr", "parameter_tt")[index]] = cell
    pair_reasons = [_pair_reason(inputs, (0, 1), "within_reference_subject"),
                    _pair_reason(inputs, (2, 3), "within_test_subject")]
    cells["reference_subject_ratio"] = _arithmetic(inputs, (0, 1), (-1, 1), reason=pair_reasons[0])
    cells["test_subject_ratio"] = _arithmetic(inputs, (2, 3), (-1, 1), reason=pair_reasons[1])
    reason = _interaction_reason(inputs, pair_reasons)
    cells["interaction_ratio"] = _arithmetic(inputs, range(4), _COEFFICIENTS, reason=reason)
    cells["log_interaction"] = _arithmetic(inputs, range(4), _COEFFICIENTS, log=True, reason=reason)
    for name, formula, unit in (
            ("log_interaction_variance", "c' C c; c=(-1,1,1,-1)", "dimensionless_squared"),
            ("log_interaction_standard_uncertainty", "sqrt(c' C c)", "dimensionless"),
            ("signed_profile_log_ratio", "e * abs(e) / (2 * V)", "dimensionless"),
            ("signed_index", "tanh(S / 2)", "dimensionless")):
        cells[name] = _cell(ROLES, formula, unit)
    log_cell = cells["log_interaction"]
    model_reason = (reason or ("observation_model_missing" if model is None else None))
    if model_reason is None and model["variance_status"] == "unknown":
        model_reason = "covariance_status_unknown"
    exact_variance = None
    if model_reason is None:
        matrix = model["log_covariance"]
        exact_variance = sum((Fraction(matrix[i][j]) * _COEFFICIENTS[i] * _COEFFICIENTS[j]
                              for i in range(4) for j in range(4)), Fraction(0))
        variance = _as_float(exact_variance)
        if variance is None:
            cells["log_interaction_variance"]["reason"] = "variance_representation_range"
        else:
            cells["log_interaction_variance"].update(value=variance, relation="eq", status="computed")
        standard_uncertainty = _sqrt_fraction(exact_variance)
        cells["log_interaction_standard_uncertainty"].update(
            value=standard_uncertainty, relation="eq", status="computed")
    for name in ("log_interaction_variance", "log_interaction_standard_uncertainty"):
        if cells[name]["status"] == "unavailable" and cells[name]["reason"] is None:
            cells[name]["reason"] = model_reason
    statistical_reason = reason
    if statistical_reason is None and log_cell["status"] != "computed":
        statistical_reason = (log_cell["reason"] if log_cell["status"] == "unavailable"
                              else "censored_joint_likelihood_unimplemented")
    statistical_reason = statistical_reason or model_reason
    if statistical_reason is None and model["variance_status"] != "known":
        statistical_reason = "covariance_estimated_not_known"
    if statistical_reason is None and model["distribution"] != "normal":
        statistical_reason = "normal_log_observation_model_unspecified"
    if statistical_reason is None and exact_variance == 0:
        statistical_reason = "zero_interaction_variance"
    if statistical_reason is None:
        e = log_cell["value"]
        exact_score = Fraction(e) * abs(Fraction(e)) / (2 * exact_variance)
        score = _as_float(exact_score)
        if score is None:
            cells["signed_profile_log_ratio"]["reason"] = "profile_log_ratio_representation_range"
            if abs(exact_score) > 1:
                # S overflowed binary64; tanh(S/2) still rounds unambiguously to
                # its signed endpoint. This is numerical saturation, not certainty.
                cells["signed_index"].update(value=1.0 if exact_score > 0 else -1.0,
                                             relation="eq", status="computed")
            else:
                cells["signed_index"]["reason"] = "signed_index_representation_range"
        else:
            cells["signed_profile_log_ratio"].update(value=score, relation="eq", status="computed")
            index = math.tanh(score / 2)
            if index == 0 and score != 0:
                cells["signed_index"]["reason"] = "signed_index_representation_range"
            else:
                cells["signed_index"].update(value=index, relation="eq", status="computed")
    for name in ("signed_profile_log_ratio", "signed_index"):
        if cells[name]["status"] == "unavailable" and cells[name]["reason"] is None:
            cells[name]["reason"] = statistical_reason
    qualifications = ["dependent_representations", "reported_parameter_not_intrinsic_affinity",
                      "physical_owners_do_not_establish_independence"]
    qualifications.extend(_uncertainty_qualifications(inputs))
    condition_status = inputs["relationships"]["common_conditions"]["status"]
    qualifications.append("common_conditions_" + condition_status)
    condition_ids = {operand["canonical_ids"]["conditions"]
                     for operand in inputs["operands"].values() if operand is not None}
    condition_ids.discard(None)
    if condition_status == "matched" and len(condition_ids) > 1:
        qualifications.append("common_conditions_claim_conflicts_with_canonical_ids")
    if cells["signed_index"]["value"] in (-1.0, 1.0):
        qualifications.append("signed_index_rounded_endpoint_not_certainty")
    for field in ("readout", "normalization", "preparation", "experiment", "conditions", "tracer"):
        known = [operand["canonical_ids"][field] for operand in inputs["operands"].values()
                 if operand is not None]
        if any(value is None for value in known):
            qualifications.append("canonical_" + field + "_partly_unknown")
        if len({value for value in known if value is not None}) > 1:
            qualifications.append("canonical_" + field + "_differs")
    if any(operand is not None and operand["relation"] in ("gt", "ge", "lt", "le")
           for operand in inputs["operands"].values()):
        qualifications.extend(("printed_limits_are_not_parameter_or_confidence_bounds",
                               "censored_joint_likelihood_unimplemented"))
        if model is None or model["reporting_event"] == "unknown":
            qualifications.append("censor_reporting_event_unknown")
    return {"version": SHEET_VERSION, "parameter_kind": inputs["parameter_kind"], "unit": "nM",
            "inputs": inputs, "operand_keys": keys,
            "physical_fit_ids": {role: None if operand is None else operand["physical_fit_id"]
                                 for role, operand in inputs["operands"].items()},
            "model": model, "cells": cells, "qualifications": qualifications}


__all__ = ["INPUT_VERSION", "MODEL_VERSION", "SHEET_VERSION", "ROLES", "CONTEXT_FIELDS",
           "ID_FIELDS", "RELATIONS", "UNCERTAINTY_PARTIAL_CODES", "validate_binding_interaction_inputs",
           "binding_interaction_operand_keys", "populate_binding_interaction"]
