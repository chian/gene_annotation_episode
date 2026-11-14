"""Closed source selections and numerical input contracts for A105 amounts.

Scientific numbers in selected-operation arguments are source selectors only.
The source reader verifies byte custody and numerical syntax. Numerical
validation owns neither the truth of supplied experimental interpretations nor
experimental attribution. No acquisition, model call or state mutation occurs.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import html
import math
import re

import numpy as np

from .domain import REF, obj, identity, validate_schema
from .literature_assay_inputs import _Sources, _witness_schema, _nullable, _json_source
from .literature_experimental_contracts import ExperimentalContractError


VERSION = "a105_amount_inputs_v1"
ROLES = ("numerator", "denominator")
SOURCE_KINDS = ("primary_source", "retained_extraction", "synthetic_fixture")
COMPARISON_KINDS = ("stock_target_mass_estimate_over_total_mass_estimate",
                    "between_arm_nominal_molar_amount", "unknown", "conflicting")
AMOUNT_ROLES = ("target_mass_estimate", "total_protein_mass_estimate",
                "nominal_molecule_amount", "unknown", "conflicting")
AMOUNT_KINDS = ("measured", "estimated", "nominal", "unknown", "conflicting")
QUALIFICATIONS = ("reported_point", "source_qualified_approximate", "unknown", "conflicting")
RELATIONSHIPS = ("supported", "unknown", "conflicting")
STOCK_RELATIONSHIPS = ("same", "different", "not_applicable", "unknown", "conflicting")
LITERAL_FIELDS = ("subject", "construct", "preparation", "stock", "method",
                  "reported_basis", "condition", "measurement_identity")
UNITS = ("mg/ml", "uM")
QUANTITY_FIELDS = ("value", "unit", "status", "bound", "approximate", "qualification",
                   "amount_role", "amount_kind", "basis_status", "measurement_key",
                   "physical_observation_key", "origin", "unavailable_reason")
CALCULATION_FIELDS = ("quantities", "comparison_kind", "pair_relationship",
                      "stock_relationship", "covariance", "covariance_origin", "variance_status")
_RELEASED027_LEXICAL_DEPENDENCY = {"module": "gene_annotation_episode.literature_rate_native_inputs",
    "sha256_at_release": "264328313d32a8ed0315eb4a80388be775a8c7c2b51ad25041aad071a295dc67",
    "interface": "_number(selection,sources,role='rate'); _field_contexts"}
LEXICAL_DEPENDENCY = {"module": "gene_annotation_episode.literature_rate_native_inputs",
    "sha256_at_release": "55244315a64d0940c09d0410a9d1e930f73609e7d0d34ef5ed751a5bbad71500",
    "interface": "_number(selection,sources,role='rate'); _field_contexts",
    "scope_generation": "completed_allocation_addition_v1",
    "scope_module": "gene_annotation_episode.literature_partner_source_fields",
    "scope_sha256_at_release": "20fd7866318fff00d80dcf3109c3a2589c36a38e35329d1b63ca954f2c035a17"}
UNCERTAINTY_KINDS = ("sd", "sem", "ci", "untyped", "unreported", "unknown", "conflicting")
INPUT_REASONS = ("source_amount_unit_unreported", "unsupported_source_amount_unit")
_QUANTITY_RECORD_FIELDS = ("meanings", "number", "unit", "amount_role", "amount_kind",
    "qualification", "basis_status", "reported_uncertainty", "measurement_key",
    "physical_observation_key", "owner_key", "value", "status", "bound", "approximate", "origin", "source_origin", "unavailable_reason")
_EXTRACTION_FIELDS = ("version", "source_ref", "source_kind", "experiment", "intended_change",
    "comparison_kind", "pair_relationship", "stock_relationship", "quantities",
    "covariance_source", "calculation_inputs", "source_refs", "lexical_dependency")
_COVARIANCE_FIELDS = ("version", "quantity_order", "quantity_measurement_keys",
    "quantity_physical_observation_keys", "quantity_owner_keys", "quantity_units",
    "covariance", "origin", "variance_status")


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _keys(value, names, field):
    if not isinstance(value, dict) or set(value) != set(names):
        _fail("closed_fields_required", field)


def _finite(value, field, *, nullable=False):
    if nullable and value is None:
        return
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        _fail("finite_number_required", field)


def amount_arguments_schema():
    """Selected source meanings; every property is required, unknowns explicit.

    ``qualification`` describes source reporting, never measurement exactness.
    A point selection cannot override lexical censoring or approximation.
    The separate reader verifies the selected bytes and retains interpretations.
    """
    witness = _witness_schema()
    number = obj({"witness": deepcopy(witness),
        "number_start": {"type": "integer", "minimum": 0},
        "number_end": {"type": "integer", "minimum": 1}})

    def meaning(values):
        return obj({"value": {"enum": list(values)},
            "witnesses": {"type": "array", "items": deepcopy(witness)}})

    uncertainty = obj({"kind": meaning(UNCERTAINTY_KINDS),
        "statement": _nullable(deepcopy(witness))})
    quantity = obj({**{name: _nullable(deepcopy(witness)) for name in LITERAL_FIELDS},
        "measurement": _nullable(obj({"number": number, "unit": _nullable(deepcopy(witness))})),
        "amount_role": meaning(AMOUNT_ROLES), "amount_kind": meaning(AMOUNT_KINDS),
        "qualification": meaning(QUALIFICATIONS), "basis_status": meaning(RELATIONSHIPS),
        "reported_uncertainty": uncertainty})
    return obj({"source_ref": deepcopy(REF), "source_kind": {"enum": list(SOURCE_KINDS)},
        "experiment": _nullable(deepcopy(witness)),
        "comparison_kind": meaning(COMPARISON_KINDS), "pair_relationship": meaning(RELATIONSHIPS),
        "stock_relationship": meaning(STOCK_RELATIONSHIPS),
        "intended_change": _nullable(deepcopy(witness)),
        "quantities": obj({name: _nullable(deepcopy(quantity)) for name in ROLES}),
        "covariance_source_ref": _nullable(deepcopy(REF))})


def validate_amount_calculation_inputs(inputs):
    """Validate already source-owned operands and full ordered covariance.

    The separate source reader must establish scientific roles, basis, pairing and
    covariance ownership before this finite numerical boundary is called.
    Negative noisy/estimated source quantities remain permissible. Unknown
    covariance is never converted into an independent-observation model.
    """
    _keys(inputs, CALCULATION_FIELDS, "inputs")
    _keys(inputs["quantities"], ROLES, "quantities")
    choices = {"comparison_kind": COMPARISON_KINDS, "pair_relationship": RELATIONSHIPS,
        "stock_relationship": STOCK_RELATIONSHIPS, "variance_status": ("known", "estimated", "unknown"),
        "covariance_origin": (None, "reported", "derived", "synthetic")}
    for field, allowed in choices.items():
        if inputs[field] not in allowed:
            _fail("unsupported_amount_interpretation", field)
    quantities = inputs["quantities"]
    for role in ROLES:
        row = quantities[role]
        if row is None:
            continue
        _keys(row, QUANTITY_FIELDS, "quantities." + role)
        _finite(row["value"], role + ".value", nullable=True)
        fields = {"unit": (None, *UNITS), "status": ("observed", "censored", "unavailable", "conflicting"),
            "bound": ("none", "lt", "le", "gt", "ge"), "qualification": QUALIFICATIONS,
            "amount_role": AMOUNT_ROLES, "amount_kind": AMOUNT_KINDS, "basis_status": RELATIONSHIPS,
            "origin": ("reported", "derived", "synthetic")}
        for field, allowed in fields.items():
            if row[field] not in allowed:
                _fail("unsupported_amount_interpretation", role + "." + field)
        if type(row["approximate"]) is not bool:
            _fail("boolean_required", role + ".approximate")
        if row["qualification"] == "source_qualified_approximate" and not row["approximate"]:
            _fail("source_approximation_not_retained", role + ".approximate")
        # reported_point does not imply absence of a lexical approximation.
        if (row["status"] in ("observed", "censored")) != (row["value"] is not None):
            _fail("amount_status_value_mismatch", role)
        if ((row["status"] == "observed" and row["bound"] != "none")
                or (row["status"] == "censored" and row["bound"] == "none")
                or (row["status"] == "conflicting" and row["bound"] != "none")):
            _fail("amount_censor_status_mismatch", role)
        if row["value"] is not None and row["unit"] is None:
            _fail("converted_amount_unit_required", role + ".unit")
        for field in ("measurement_key", "physical_observation_key"):
            if row[field] is not None and (not isinstance(row[field], str) or not row[field]):
                _fail("measurement_owner_key_required", role + "." + field)
        if row["value"] is not None and row["measurement_key"] is None:
            _fail("measurement_owner_key_required", role + ".measurement_key")
        if row["unavailable_reason"] not in (None, *INPUT_REASONS):
            _fail("unsupported_amount_unavailable_reason", role + ".unavailable_reason")
        if row["unavailable_reason"] is not None and row["status"] != "unavailable":
            _fail("amount_unavailable_reason_status_mismatch", role)

    matrix = inputs["covariance"]
    if matrix is None:
        if inputs["covariance_origin"] is not None or inputs["variance_status"] != "unknown":
            _fail("covariance_status_without_matrix", "covariance")
        return deepcopy(inputs)
    if inputs["covariance_origin"] is None or inputs["variance_status"] == "unknown":
        _fail("covariance_meaning_required", "covariance")
    if any(quantities[role] is None or quantities[role]["value"] is None for role in ROLES):
        _fail("complete_covariance_owners_required", "covariance")
    if (not isinstance(matrix, list) or len(matrix) != 2
            or any(not isinstance(row, list) or len(row) != 2 for row in matrix)):
        _fail("two_by_two_covariance_required", "covariance")
    for i, row in enumerate(matrix):
        for j, value in enumerate(row):
            _finite(value, f"covariance[{i}][{j}]")
    array = np.asarray(matrix, dtype=float)
    if not np.array_equal(array, array.T):
        _fail("symmetric_covariance_required", "covariance")
    if np.any(np.diag(array) < 0):
        _fail("positive_semidefinite_covariance_required", "covariance")
    scale = float(np.max(np.abs(array)))
    try:
        eigenvalues = np.linalg.eigvalsh(array / scale) if scale else np.zeros(2)
    except np.linalg.LinAlgError:
        _fail("covariance_eigendecomposition_failed", "covariance")
    if not np.all(np.isfinite(eigenvalues)) or float(np.min(eigenvalues)) < -128 * np.finfo(float).eps:
        _fail("positive_semidefinite_covariance_required", "covariance")
    first, second = (quantities[role] for role in ROLES)
    same_token = first["measurement_key"] == second["measurement_key"]
    same_physical = (first["physical_observation_key"] is not None
        and first["physical_observation_key"] == second["physical_observation_key"])
    if same_token or same_physical:
        if (first["unit"] != second["unit"] or first["value"] != second["value"]
                or not np.array_equal(array[0], array[1])
                or not np.array_equal(array[:, 0], array[:, 1])):
            _fail("shared_measurement_covariance_mismatch", "covariance")
    return deepcopy(inputs)


def _interpret(value, allowed, sources, field):
    _keys(value, ("value", "witnesses"), field)
    if value["value"] not in allowed or not isinstance(value["witnesses"], list):
        _fail("unsupported_amount_interpretation", field)
    witnesses = [sources.witness(w, field + ".witnesses") for w in value["witnesses"]]
    distinct = {(w["source_ref"], w["artifact_ref"], w["start"], w["end"]) for w in witnesses}
    required = 2 if value["value"] == "conflicting" else 0 if value["value"] in ("unknown", "unreported") else 1
    if len(distinct) < required:
        _fail("interpretation_witness_required", field)
    return {"value": value["value"], "witnesses": witnesses}


def _amount_number(selection, sources):
    """Reuse released lexical guards only; no rate units or rate publication.

    The legacy keyword ``rate`` selects signed scalar bounds/approximation and
    uncertainty-as-point guards. It does not assign this quantity a rate role.
    Mass/molar units and all experimental meanings remain this module's work.
    """
    from .literature_rate_native_inputs import _number
    return _number(selection, sources, role="rate")


def _plain_amount_unit(raw):
    text = re.sub(r"</?[A-Za-z_][^<>]*>", "", raw)
    text = re.sub(r"\s+", "", html.unescape(text)).replace("µ", "u").replace("μ", "u")
    text = text.translate(str.maketrans({"−": "-", "⁻": "-", "¹": "1"})).replace("^", "")
    values = {"mg/ml": ("mg/ml", Fraction(1)), "mg/mL": ("mg/ml", Fraction(1)),
        "g/L": ("mg/ml", Fraction(1)), "ug/ml": ("mg/ml", Fraction(1, 1000)),
        "ug/mL": ("mg/ml", Fraction(1, 1000)), "mg/L": ("mg/ml", Fraction(1, 1000)),
        "g/ml": ("mg/ml", Fraction(1000)), "g/mL": ("mg/ml", Fraction(1000)),
        "uM": ("uM", Fraction(1)), "nM": ("uM", Fraction(1, 1000)),
        "mM": ("uM", Fraction(1000)), "M": ("uM", Fraction(1000000))}
    for mass in ("mg", "ug", "g"):
        for volume in ("ml", "mL", "L"):
            key = mass + "/" + volume
            if key in values:
                values[mass + volume + "-1"] = values[key]
    return values.get(text)


def _float_exact(value, field):
    try:
        result = float(value)
    except (ValueError, OverflowError):
        _fail("numerical_model_range", field)
    if not math.isfinite(result) or result == 0 and value != 0:
        _fail("numerical_model_range", field)
    return result


def _amount_unit(selection, sources):
    if selection is None:
        return None
    from .literature_rate_native_inputs import _field_contexts
    from .literature_partner_source_fields import _unit_continuation
    witness = sources.witness(selection, "amount.unit")
    before, after = _field_contexts(sources, witness, 0, len(witness["quote"]))
    if ((before[-1:] and (before[-1:].isalpha() or before[-1:] in "_µμ/^⁻¹"))
            or _unit_continuation(after) or _amount_per_continuation(after)):
        _fail("partial_source_amount_unit", "amount.unit")
    parsed = _plain_amount_unit(witness["quote"])
    return {"witness": witness, "raw_unit": witness["quote"],
        "canonical_unit": parsed[0] if parsed else None,
        "multiplier": _float_exact(parsed[1], "amount.unit") if parsed else None,
        "unavailable_reason": None if parsed else "unsupported_source_amount_unit"}


def _amount_per_continuation(suffix):
    # 'mg/ml per Bradford analysis' names a measurement method, not a further
    # physical denominator. A physical per-unit continuation must stay attached.
    return bool(re.match(r"\s+per\s+(?:[npkmuµμ]?g|[npkmuµμ]?mol|[npkmuµμ]?L|ml|mL|min|s|h)(?![A-Za-z_µμ])", suffix))


def _explicit_unit_consistency(number, unit, sources):
    if number is None or unit is None or unit["canonical_unit"] is None:
        return
    from .literature_rate_native_inputs import _field_contexts
    from .literature_partner_source_fields import _unit_continuation
    selector = number["selector"]
    _, suffix = _field_contexts(sources, selector["witness"], selector["number_start"], selector["number_end"])
    # Only an actually adjacent printed quantity is checked here. A separately
    # selected shared header remains an explicit source interpretation.
    match = re.match(r"\s*((?:[muµμ]?g\s*/\s*(?:ml|mL|L))|(?:[nmuµμ]?M)|(?:[muµμ]?g\s*(?:ml|mL|L)\s*\^?[-−⁻][1¹]))", suffix)
    if match is None:
        if re.match(r"\s*(?:%|percent\b|(?:[npkmuµμ]?mol|[npkmuµμ]?g|[npkmuµμ]?M|U|[npkmuµμ]?L)\b)", suffix):
            _fail("unsupported_explicit_amount_unit", "amount.number")
        return
    if _unit_continuation(suffix[match.end():]) or _amount_per_continuation(suffix[match.end():]):
        _fail("partial_source_amount_unit", "amount.number")
    if _plain_amount_unit(match.group(1)) != _plain_amount_unit(unit["raw_unit"]):
        _fail("source_amount_unit_mismatch", "amount.number")


def _measurement_key(number):
    if number is None:
        return None
    selection, witness = number["selector"], number["selector"]["witness"]
    return identity("literature_amount_measurement", {
        "source_ref": witness["source_ref"], "artifact_ref": witness["artifact_ref"],
        "start": witness["start"] + len(witness["quote"][:selection["number_start"]].encode()),
        "end": witness["start"] + len(witness["quote"][:selection["number_end"]].encode())})


def _physical_key(witness):
    return None if witness is None else identity("literature_amount_observation", {
        name: witness[name] for name in ("source_ref", "artifact_ref", "start", "end")})


def _owner_key(row):
    return None if row["number"] is None else identity("literature_amount_owner", {
        "measurement_key": row["measurement_key"], "meanings": row["meanings"],
        "amount_role": row["amount_role"], "amount_kind": row["amount_kind"], "basis_status": row["basis_status"]})


def _converted_amount(number, unit):
    if number is None or unit is None or unit["canonical_unit"] is None:
        return None
    return _float_exact(Fraction(number["raw_number"].replace("−", "-")) *
        _plain_amount_unit(unit["raw_unit"])[1], "amount.value")


def _calculation_quantity(row):
    if row is None:
        return None
    return {"value": row["value"], "unit": row["unit"]["canonical_unit"] if row["unit"] else None,
        **{field: row[field] for field in ("status", "bound", "approximate", "measurement_key",
            "physical_observation_key", "origin", "unavailable_reason")},
        **{field: row[field]["value"] for field in ("qualification", "amount_role", "amount_kind", "basis_status")}}


def _read_covariance(reference, quantities, sources):
    if reference is None:
        return None, None
    if any(row is None or row["value"] is None for row in quantities.values()):
        _fail("complete_covariance_owners_required", "covariance_source_ref")
    source = sources.source(reference, "original")
    data = _json_source(source["content"], "covariance_source_ref")
    converted = _covariance_values(data, quantities)
    return {"source_ref": reference, "artifact_ref": source["artifact_ref"], "data": data}, converted


def _covariance_values(data, quantities):
    _keys(data, _COVARIANCE_FIELDS, "covariance_source")
    expected = {"version": "a105_amount_covariance_v1", "quantity_order": list(ROLES),
        "quantity_measurement_keys": [quantities[role]["measurement_key"] for role in ROLES],
        "quantity_physical_observation_keys": [quantities[role]["physical_observation_key"] for role in ROLES],
        "quantity_owner_keys": [quantities[role]["owner_key"] for role in ROLES],
        "quantity_units": [quantities[role]["unit"]["raw_unit"] for role in ROLES]}
    for field, value in expected.items():
        if data[field] != value:
            _fail("amount_covariance_owner_or_unit_mismatch", "covariance_source." + field)
    matrix = data["covariance"]
    if (not isinstance(matrix, list) or len(matrix) != 2
            or any(not isinstance(row, list) or len(row) != 2 for row in matrix)):
        _fail("two_by_two_covariance_required", "covariance_source.covariance")
    scales = [_plain_amount_unit(quantities[role]["unit"]["raw_unit"])[1] for role in ROLES]
    converted = []
    for i, row in enumerate(matrix):
        converted_row = []
        for j, value in enumerate(row):
            _finite(value, f"covariance_source.covariance[{i}][{j}]")
            converted_row.append(_float_exact(Fraction(str(value)) * scales[i] * scales[j], "covariance_source.covariance"))
        converted.append(converted_row)
    return converted


def read_amount_inputs(arguments, *, read_source):
    """Read source-bound amounts and meanings; never infer purity or activity.

    Source quotes verify custody, not interpretation. A model selects meanings
    and exact spans; every scientific number is parsed from actual source bytes.
    A supported relationship can identify an unnamed stock or preparation.
    """
    validate_schema(arguments, amount_arguments_schema())
    sources = _Sources(read_source)
    sources.source(arguments["source_ref"], "original")
    witness = lambda value, field: None if value is None else sources.witness(value, field)
    result = {"version": VERSION, "source_ref": arguments["source_ref"], "source_kind": arguments["source_kind"],
        "experiment": witness(arguments["experiment"], "experiment"),
        "intended_change": witness(arguments["intended_change"], "intended_change"),
        **{field: _interpret(arguments[field], allowed, sources, field) for field, allowed in (
            ("comparison_kind", COMPARISON_KINDS), ("pair_relationship", RELATIONSHIPS),
            ("stock_relationship", STOCK_RELATIONSHIPS))}, "quantities": {}}
    for role in ROLES:
        selected = arguments["quantities"][role]
        if selected is None:
            result["quantities"][role] = None
            continue
        row = {"meanings": {name: witness(selected[name], role + "." + name) for name in LITERAL_FIELDS},
            **{field: _interpret(selected[field], allowed, sources, role + "." + field)
                for field, allowed in (("amount_role", AMOUNT_ROLES), ("amount_kind", AMOUNT_KINDS),
                    ("qualification", QUALIFICATIONS), ("basis_status", RELATIONSHIPS))}}
        measurement = selected["measurement"]
        number = _amount_number(measurement["number"], sources) if measurement else None
        unit = _amount_unit(measurement["unit"], sources) if measurement else None
        _explicit_unit_consistency(number, unit, sources)
        value = _converted_amount(number, unit)
        status = "unavailable" if value is None else "observed" if number["relation"] == "point" else "censored"
        uncertainty = selected["reported_uncertainty"]
        interpreted = _interpret(uncertainty["kind"], UNCERTAINTY_KINDS, sources, role + ".reported_uncertainty.kind")
        statement = witness(uncertainty["statement"], role + ".reported_uncertainty.statement")
        if interpreted["value"] not in ("unknown", "unreported") and statement is None:
            _fail("uncertainty_statement_required", role + ".reported_uncertainty.statement")
        row.update(number=number, unit=unit, value=value, status=status,
            unavailable_reason=("source_amount_unit_unreported" if number and unit is None else
                unit["unavailable_reason"] if number and unit else None),
            bound=number["relation"] if number and number["relation"] != "point" else "none",
            approximate=bool(number and number["approximate"] or row["qualification"]["value"] == "source_qualified_approximate"),
            source_origin="synthetic" if arguments["source_kind"] == "synthetic_fixture" else "reported",
            origin=("derived" if value is not None and unit["multiplier"] != 1 else
                "synthetic" if arguments["source_kind"] == "synthetic_fixture" else "reported"),
            measurement_key=_measurement_key(number),
            physical_observation_key=_physical_key(row["meanings"]["measurement_identity"]),
            reported_uncertainty={"kind": interpreted, "statement": statement})
        row["owner_key"] = _owner_key(row)
        result["quantities"][role] = row
    cov_source, cov = _read_covariance(arguments["covariance_source_ref"], result["quantities"], sources)
    result["covariance_source"] = cov_source
    result["calculation_inputs"] = {"quantities": {role: _calculation_quantity(result["quantities"][role]) for role in ROLES},
        **{field: result[field]["value"] for field in ("comparison_kind", "pair_relationship", "stock_relationship")},
        "covariance": cov, "covariance_origin": cov_source["data"]["origin"] if cov_source else None,
        "variance_status": cov_source["data"]["variance_status"] if cov_source else "unknown"}
    validate_amount_calculation_inputs(result["calculation_inputs"])
    result.update(source_refs=list(sources.references), lexical_dependency=deepcopy(LEXICAL_DEPENDENCY))
    return result


def _saved_interpretation(value, allowed, field):
    from .literature_rate_native_inputs import _saved_witness
    _keys(value, ("value", "witnesses"), field)
    if value["value"] not in allowed or not isinstance(value["witnesses"], list):
        _fail("unsupported_amount_interpretation", field)
    for witness in value["witnesses"]:
        _saved_witness(witness, field)
    distinct = {(w["source_ref"], w["artifact_ref"], w["start"], w["end"]) for w in value["witnesses"]}
    required = 2 if value["value"] == "conflicting" else 0 if value["value"] in ("unknown", "unreported") else 1
    if len(distinct) < required:
        _fail("interpretation_witness_required", field)


def validate_amount_extraction(extraction):
    """Validate saved associations without scientific-source IO or cell fitting."""
    from .literature_rate_native_inputs import _saved_witness, _saved_number
    _keys(extraction, _EXTRACTION_FIELDS, "extraction")
    if extraction["version"] != VERSION or extraction["source_kind"] not in SOURCE_KINDS:
        _fail("amount_extraction_version_or_origin_mismatch", "extraction")
    # Old selections retain their original classifications. Neither supported
    # generation is source-reparsed here; unknown identities are never aliases.
    if extraction["lexical_dependency"] not in (LEXICAL_DEPENDENCY, _RELEASED027_LEXICAL_DEPENDENCY):
        _fail("amount_lexical_dependency_mismatch", "lexical_dependency")
    for field in ("experiment", "intended_change"):
        if extraction[field] is not None:
            _saved_witness(extraction[field], field)
    for field, allowed in (("comparison_kind", COMPARISON_KINDS), ("pair_relationship", RELATIONSHIPS),
            ("stock_relationship", STOCK_RELATIONSHIPS)):
        _saved_interpretation(extraction[field], allowed, field)
    _keys(extraction["quantities"], ROLES, "quantities")
    for role in ROLES:
        row = extraction["quantities"][role]
        if row is None:
            continue
        _keys(row, _QUANTITY_RECORD_FIELDS, role)
        _keys(row["meanings"], LITERAL_FIELDS, role + ".meanings")
        for field, witness in row["meanings"].items():
            if witness is not None:
                _saved_witness(witness, role + ".meanings." + field)
        for field, allowed in (("amount_role", AMOUNT_ROLES), ("amount_kind", AMOUNT_KINDS),
                ("qualification", QUALIFICATIONS), ("basis_status", RELATIONSHIPS)):
            _saved_interpretation(row[field], allowed, role + "." + field)
        number, unit = row["number"], row["unit"]
        if number is not None:
            _saved_number(number, role + ".number")
        if unit is not None:
            _keys(unit, ("witness", "raw_unit", "canonical_unit", "multiplier", "unavailable_reason"), role + ".unit")
            _saved_witness(unit["witness"], role + ".unit")
            parsed = _plain_amount_unit(unit["raw_unit"])
            if (unit["raw_unit"] != unit["witness"]["quote"] or
                    (unit["canonical_unit"], unit["multiplier"], unit["unavailable_reason"]) != (
                        parsed[0] if parsed else None, float(parsed[1]) if parsed else None,
                        None if parsed else "unsupported_source_amount_unit")):
                _fail("amount_saved_unit_mismatch", role)
        value = _converted_amount(number, unit)
        expected = {"measurement_key": _measurement_key(number),
            "physical_observation_key": _physical_key(row["meanings"]["measurement_identity"]),
            "owner_key": _owner_key(row), "value": value,
            "status": "unavailable" if value is None else "observed" if number["relation"] == "point" else "censored",
            "bound": number["relation"] if number and number["relation"] != "point" else "none",
            "approximate": bool(number and number["approximate"] or row["qualification"]["value"] == "source_qualified_approximate"),
            "source_origin": "synthetic" if extraction["source_kind"] == "synthetic_fixture" else "reported",
            "origin": ("derived" if value is not None and unit["multiplier"] != 1 else
                "synthetic" if extraction["source_kind"] == "synthetic_fixture" else "reported"),
            "unavailable_reason": ("source_amount_unit_unreported" if number and unit is None else
                unit["unavailable_reason"] if number and unit else None)}
        if any(row[field] != value for field, value in expected.items()) or type(row["approximate"]) is not bool:
            _fail("amount_saved_quantity_mismatch", role)
        uncertainty = row["reported_uncertainty"]
        _keys(uncertainty, ("kind", "statement"), role + ".reported_uncertainty")
        _saved_interpretation(uncertainty["kind"], UNCERTAINTY_KINDS, role + ".reported_uncertainty.kind")
        if uncertainty["statement"] is not None:
            _saved_witness(uncertainty["statement"], role + ".reported_uncertainty.statement")
        elif uncertainty["kind"]["value"] not in ("unreported", "unknown"):
            _fail("uncertainty_statement_required", role + ".reported_uncertainty.statement")
    covariance = extraction["covariance_source"]
    if covariance is not None:
        _keys(covariance, ("source_ref", "artifact_ref", "data"), "covariance_source")
        if any(not isinstance(covariance[field], str) or not covariance[field] for field in ("source_ref", "artifact_ref")):
            _fail("amount_covariance_source_identity_required", "covariance_source")
        if any(row is None or row["value"] is None for row in extraction["quantities"].values()):
            _fail("complete_covariance_owners_required", "covariance_source")
    calculation = {"quantities": {role: _calculation_quantity(extraction["quantities"][role]) for role in ROLES},
        **{field: extraction[field]["value"] for field in ("comparison_kind", "pair_relationship", "stock_relationship")},
        "covariance": _covariance_values(covariance["data"], extraction["quantities"]) if covariance else None,
        "covariance_origin": covariance["data"]["origin"] if covariance else None,
        "variance_status": covariance["data"]["variance_status"] if covariance else "unknown"}
    validate_amount_calculation_inputs(calculation)
    if extraction["calculation_inputs"] != calculation:
        _fail("amount_saved_calculation_input_mismatch", "calculation_inputs")
    refs = extraction["source_refs"]
    if (not isinstance(refs, list) or len(refs) != len(set(refs))
            or any(not isinstance(ref, str) or not ref for ref in refs)):
        _fail("amount_source_roster_invalid", "source_refs")
    return deepcopy(extraction)


def amount_selection_from_extraction(extraction):
    """Recover only the original selected arguments from saved enriched facts."""
    def witness(value):
        return None if value is None else {name: value[name] for name in ("source_ref", "representation", "start", "end", "quote")}
    def meaning(value):
        return {"value": value["value"], "witnesses": [witness(w) for w in value["witnesses"]]}
    quantities = {}
    for role, row in extraction["quantities"].items():
        if row is None:
            quantities[role] = None
            continue
        number = row["number"]
        quantities[role] = {**{name: witness(row["meanings"][name]) for name in LITERAL_FIELDS},
            "measurement": None if number is None else {
                "number": {**number["selector"], "witness": witness(number["selector"]["witness"])},
                "unit": witness(row["unit"]["witness"]) if row["unit"] else None},
            **{name: meaning(row[name]) for name in ("amount_role", "amount_kind", "qualification", "basis_status")},
            "reported_uncertainty": {"kind": meaning(row["reported_uncertainty"]["kind"]),
                "statement": witness(row["reported_uncertainty"]["statement"])}}
    return {"source_ref": extraction["source_ref"], "source_kind": extraction["source_kind"],
        "experiment": witness(extraction["experiment"]), "intended_change": witness(extraction["intended_change"]),
        **{name: meaning(extraction[name]) for name in ("comparison_kind", "pair_relationship", "stock_relationship")},
        "quantities": quantities, "covariance_source_ref": extraction["covariance_source"]["source_ref"] if extraction["covariance_source"] else None}


def validate_amount_selection(arguments, extraction):
    """Check selection/source roster without rereading scientific bytes."""
    validate_schema(arguments, amount_arguments_schema())
    if arguments != amount_selection_from_extraction(extraction):
        _fail("amount_saved_selection_mismatch", "selection")
    def references(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in ("source_ref", "covariance_source_ref") and isinstance(child, str):
                    yield child
                else:
                    yield from references(child)
        elif isinstance(value, list):
            for child in value:
                yield from references(child)
    if set(extraction["source_refs"]) != set(references(arguments)):
        _fail("amount_source_roster_invalid", "source_refs")


__all__ = ["VERSION", "ROLES", "SOURCE_KINDS", "COMPARISON_KINDS", "AMOUNT_ROLES",
    "AMOUNT_KINDS", "QUALIFICATIONS", "RELATIONSHIPS", "STOCK_RELATIONSHIPS", "LITERAL_FIELDS",
    "UNITS", "QUANTITY_FIELDS", "CALCULATION_FIELDS", "amount_arguments_schema",
    "validate_amount_calculation_inputs", "read_amount_inputs", "validate_amount_extraction",
    "validate_amount_selection", "amount_selection_from_extraction", "LEXICAL_DEPENDENCY", "INPUT_REASONS",
    "UNCERTAINTY_KINDS"]
