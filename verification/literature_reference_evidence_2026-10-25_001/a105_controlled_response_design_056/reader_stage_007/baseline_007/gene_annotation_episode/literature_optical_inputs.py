"""Source-bound optical operands, separate from science interpretation and credit.

Selections supply experimental meanings; verified quotes establish custody only.
No source acquisition, calculator execution, model, state mutation or episode
decision occurs here. Reuse refs are local calculator aliases, not global
physical identities or evidence of independence between sheets.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import html
import math
import re

import numpy as np

from .domain import REF, ContractError, identity, obj, validate_schema
from .literature_assay_inputs import _Sources, _json_source, _nullable, _witness_schema
from .literature_experimental_contracts import ExperimentalContractError
from .literature_rate_native_inputs import _number, _field_contexts


VERSION = "a105_optical_inputs_v1"
PRIMITIVE_ORDER = ("sample_slope", "blank_slope", "epsilon", "path_length")
SOURCE_KINDS = ("primary_source", "retained_extraction", "synthetic_fixture")
LITERAL_FIELDS = ("molecule", "construct", "preparation", "condition", "measured_entity")
QUANTITY_MEANINGS = ("measurement_identity", "condition", "measured_entity", "interval")
QUALIFICATIONS = ("reported_point", "source_qualified_approximate", "unknown", "conflicting")
INTERPRETATIONS = {
    "signal_kind": ("absorbance_slope", "absorbance_difference", "static_absorbance", "unknown"),
    "relation": ("applicable_extinction_relation", "not_applicable", "unknown", "conflicting"),
    "blank_role": ("matched_no_reaction_background", "condition_reference", "component_omission", "unknown", "conflicting"),
    "same_endpoint": ("same", "different", "unknown"),
    "matched_window": ("same", "different", "unknown"),
    "rate_window": ("source_supported_rate_interval", "interval_mean_only", "static_only", "unknown"),
}
LEXICAL_DEPENDENCY = {
    "module": "gene_annotation_episode.literature_rate_native_inputs",
    "sha256_at_release": "55244315a64d0940c09d0410a9d1e930f73609e7d0d34ef5ed751a5bbad71500",
    "interface": "_number(selection,sources,role='rate'); _field_contexts",
    "scope_module": "gene_annotation_episode.literature_partner_source_fields",
    "scope_sha256_at_release": "20fd7866318fff00d80dcf3109c3a2589c36a38e35329d1b63ca954f2c035a17",
    "custody_module": "gene_annotation_episode.literature_assay_inputs",
    "custody_sha256_at_release": "52069b7d974556631a18d132eaa8bd79b23efc5b7dc2a583b1fff73df4758b6e",
}
_COV_FIELDS = ("version", "primitive_order", "primitive_measurement_keys",
    "primitive_physical_observation_keys", "primitive_owner_keys", "primitive_units",
    "covariance", "origin", "covariance_status")
_TAGS = re.compile(r"</?[A-Za-z_][^<>]*>")
_TRANSLATE = str.maketrans({"−": "-", "⁻": "-", "¹": "1", "µ": "u", "μ": "u"})


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _keys(value, names, field):
    if not isinstance(value, dict) or set(value) != set(names):
        _fail("closed_fields_required", field)


def optical_arguments_schema():
    """Every number is selected from source bytes, never supplied as arithmetic."""
    witness = _witness_schema()
    number = obj({"witness": deepcopy(witness), "number_start": {"type": "integer", "minimum": 0},
        "number_end": {"type": "integer", "minimum": 1}})
    def meaning(values):
        return obj({"value": {"enum": list(values)}, "witnesses": {"type": "array", "items": deepcopy(witness)}})
    quantity = obj({**{field: _nullable(deepcopy(witness)) for field in QUANTITY_MEANINGS},
        "measurement": _nullable(obj({"number": number, "unit": _nullable(deepcopy(witness))})),
        "qualification": meaning(QUALIFICATIONS)})
    return obj({"source_ref": deepcopy(REF), "source_kind": {"enum": list(SOURCE_KINDS)},
        **{field: _nullable(deepcopy(witness)) for field in LITERAL_FIELDS},
        **{field: meaning(values) for field, values in INTERPRETATIONS.items()},
        "signals": obj({role: _nullable(deepcopy(quantity)) for role in ("sample", "blank")}),
        "calibration": obj({role: _nullable(deepcopy(quantity)) for role in ("epsilon", "path_length", "wavelength")}),
        "covariance_source_ref": _nullable(deepcopy(REF))})


def _interpret(value, allowed, sources, field):
    _keys(value, ("value", "witnesses"), field)
    if value["value"] not in allowed or not isinstance(value["witnesses"], list):
        _fail("unsupported_optical_interpretation", field)
    witnesses = [sources.witness(w, field + ".witnesses") for w in value["witnesses"]]
    distinct = {(w["source_ref"], w["artifact_ref"], w["start"], w["end"]) for w in witnesses}
    minimum = 0 if value["value"] == "unknown" else 2 if value["value"] == "conflicting" else 1
    if len(distinct) < minimum:
        _fail("interpretation_witness_required", field)
    return {"value": value["value"], "witnesses": witnesses}


def _normalize(raw):
    # Preserve case: mAU != MAU and M != mM. Custody/raw bytes stay untouched.
    visible = html.unescape(_TAGS.sub("", raw)).translate(_TRANSLATE).replace("^", "")
    return re.sub(r"\s+", "", visible)


def _unit_tables():
    signal = {}
    for name, signal_scale in (("absorbance", Fraction(1)), ("AU", Fraction(1)), ("mAU", Fraction(1, 1000))):
        signal[name] = ("absorbance", signal_scale)
        for time, time_scale in (("min", Fraction(1)), ("s", Fraction(60))):
            for spelling in (name + "/" + time, name + time + "-1"):
                signal[spelling] = ("absorbance/min", signal_scale * time_scale)
    epsilon = {}
    for molarity, amount, scale in (("mM", "mmol", Fraction(1)), ("M", "mol", Fraction(1, 1000)),
                                   ("uM", "umol", Fraction(1000))):
        for spelling in (molarity + "-1cm-1", "1/(" + molarity + "cm)", "L" + amount + "-1cm-1"):
            epsilon[spelling] = ("mM^-1cm^-1", scale)
    return {"signal": signal, "epsilon": epsilon,
        "path_length": {"cm": ("cm", Fraction(1)), "mm": ("cm", Fraction(1, 10)), "m": ("cm", Fraction(100))},
        "wavelength": {"nm": ("nm", Fraction(1)), "um": ("nm", Fraction(1000)), "m": ("nm", Fraction(1000000000))}}


_UNIT_TABLES = _unit_tables()
_ALL_UNITS = {key: value for table in _UNIT_TABLES.values() for key, value in table.items()}


def _tail_continues(suffix):
    first = suffix[:1]
    return bool(first and (first.isalnum() or first in "/_^−-⁻¹%")) or bool(re.match(
        r"\s+(?:[/^]|[A-Za-zµμ]+\s*\^?\s*[-−⁻]\s*[1¹]|per\s+(?:min|s|h|cm|mm|m|mg|g|mol|[munµμ]?M)\b)", suffix))


def _unit(selection, kind, sources):
    if selection is None:
        return None
    witness = sources.witness(selection, "optical.unit")
    before, after = _field_contexts(sources, witness, 0, len(witness["quote"]))
    edge = before[-1:]
    if (edge and (edge.isalpha() or edge in "_µμ/^⁻¹")) or _tail_continues(after):
        _fail("partial_source_optical_unit", "optical.unit")
    parsed = _UNIT_TABLES[kind].get(_normalize(witness["quote"]))
    return {"witness": witness, "raw_unit": witness["quote"],
        "canonical_unit": parsed[0] if parsed else None,
        "multiplier": float(parsed[1]) if parsed else None,
        "unavailable_reason": None if parsed else "unsupported_source_optical_unit"}


def _explicit_unit(number, selected, kind, sources):
    if number is None or selected is None or selected["canonical_unit"] is None:
        return
    ns = number["selector"]
    _, suffix = _field_contexts(sources, ns["witness"], ns["number_start"], ns["number_end"])
    # Build a character map solely to find the end of a visible unit prefix.
    # Literal custody was already checked; source bytes/witnesses are unmodified.
    visible = suffix.lstrip()
    compact, positions = "", []
    for i, char in enumerate(visible):
        translated = char.translate(_TRANSLATE)
        if translated.isspace() or translated == "^":
            continue
        compact += translated
        positions.append(i + 1)
    for candidate in sorted(_ALL_UNITS, key=len, reverse=True):
        if not compact.startswith(candidate):
            continue
        end = positions[len(candidate) - 1]
        # A known short symbol inside a longer word/unsupported symbol is not
        # a complete unit (nm inside nmol, m inside "measured").
        if visible[end:end + 1].isalnum():
            continue
        if _tail_continues(visible[end:]):
            _fail("partial_source_optical_unit", "optical.number")
        actual = _UNIT_TABLES[kind].get(candidate)
        expected = _UNIT_TABLES[kind].get(_normalize(selected["raw_unit"]))
        if actual != expected:
            _fail("source_optical_unit_mismatch", "optical.number")
        return
    # An unsupported printed physical/optical quantity cannot borrow a remote
    # compatible unit. A header unit is permitted when no adjacent unit exists.
    if re.match(r"(?:[A-Za-zµμ]*AU|absorbance|[nmuµμ]?M|[nmuµμ]?mol|[kmunµμ]?g|[kmunµμ]?L|[kmunµμ]?m|U|OD|A\d+)(?=\b|[/_^−⁻-])", visible):
        _fail("unsupported_explicit_optical_unit", "optical.number")


def _float(value, field):
    try:
        result = float(value)
    except (OverflowError, ValueError):
        _fail("numerical_model_range", field)
    if not math.isfinite(result) or result == 0 and value != 0:
        _fail("numerical_model_range", field)
    return result


def _location_key(witness, kind):
    return None if witness is None else identity(kind, {name: witness[name] for name in
        ("source_ref", "artifact_ref", "start", "end")})


def _quantity(selected, kind, role, context, sources, source_origin, signal_kind=None):
    if selected is None:
        return None
    meanings = {name: sources.witness(selected[name], role + "." + name) if selected[name] is not None else None
                for name in QUANTITY_MEANINGS}
    qualification = _interpret(selected["qualification"], QUALIFICATIONS, sources, role + ".qualification")
    measurement = selected["measurement"]
    # Legacy role='rate' requests the signed scalar lexical grammar only. No
    # existing native rate/amount unit parser is used for optical dimensions.
    number = _number(measurement["number"], sources, role="rate") if measurement else None
    unit = _unit(measurement["unit"], kind, sources) if measurement else None
    _explicit_unit(number, unit, kind, sources)
    value = None
    if number is not None and unit is not None and unit["canonical_unit"] is not None:
        scale = _UNIT_TABLES[kind][_normalize(unit["raw_unit"])][1]
        value = _float(Fraction(number["raw_number"].replace("−", "-")) * scale, role)
    approximate = bool(number and number["approximate"] or qualification["value"] == "source_qualified_approximate")
    reasons = []
    if number is None:
        reasons.append("source_measurement_unreported")
    elif unit is None:
        reasons.append("source_optical_unit_unreported")
    elif unit["unavailable_reason"]:
        reasons.append(unit["unavailable_reason"])
    if number is not None and number["relation"] != "point":
        reasons.append("censored_source_operand")
    if approximate:
        reasons.append("approximate_source_operand")
    if qualification["value"] in ("unknown", "conflicting"):
        reasons.append("source_operand_qualification_" + qualification["value"])
    if kind != "signal" and value is not None and number["relation"] == "point" and not approximate and value <= 0:
        _fail("positive_optical_operand_required", role)
    measurement_key = None
    if number is not None:
        ns, w = number["selector"], number["selector"]["witness"]
        measurement_key = identity("literature_optical_measurement", {"source_ref": w["source_ref"], "artifact_ref": w["artifact_ref"],
            "start": w["start"] + len(w["quote"][:ns["number_start"]].encode()),
            "end": w["start"] + len(w["quote"][:ns["number_end"]].encode())})
    physical_key = _location_key(meanings["measurement_identity"], "literature_optical_physical")
    owner = None if number is None else identity("literature_optical_owner", {
        "measurement_key": measurement_key, "meanings": meanings, "context": context,
        "role": role, "quantity_kind": kind, "signal_kind": signal_kind,
        "qualification": qualification})
    return {"meanings": meanings, "qualification": qualification, "number": number, "unit": unit, "value": value,
        "status": "unavailable" if value is None else "observed" if number["relation"] == "point" else "censored",
        "approximate": approximate, "measurement_key": measurement_key, "physical_observation_key": physical_key,
        "owner_key": owner, "source_origin": source_origin,
        "origin": "derived" if value is not None and unit["multiplier"] != 1 else source_origin,
        "unavailable_reasons": reasons}


def _groups(observations):
    # Connected groups handle same-token aliases even if only one occurrence
    # also has an explicit physical witness. Different groups imply no independence.
    groups = []
    for role, row in observations.items():
        if row is None or row["measurement_key"] is None:
            continue
        keys = {row["measurement_key"]}
        if row["physical_observation_key"] is not None:
            keys.add(row["physical_observation_key"])
        matches = [g for g in groups if keys & g["keys"]]
        roles = [role]
        for group in matches:
            keys |= group["keys"]
            roles += group["roles"]
            groups.remove(group)
        groups.append({"keys": keys, "roles": roles})
    output, refs = [], dict.fromkeys(PRIMITIVE_ORDER)
    for group in groups:
        roles = [role for role in PRIMITIVE_ORDER if role in group["roles"]]
        rows = [observations[role] for role in roles]
        expected_units = {"sample_slope": "absorbance/min", "blank_slope": "absorbance/min",
                          "epsilon": "mM^-1cm^-1", "path_length": "cm"}
        if len({expected_units[role] for role in roles}) != 1:
            _fail("reused_identity_dimension_mismatch", "primitive_observation_refs")
        known = [row for row in rows if row["value"] is not None]
        if known and any(row["unit"]["canonical_unit"] != known[0]["unit"]["canonical_unit"] for row in known):
            _fail("reused_identity_dimension_mismatch", "primitive_observation_refs")
        if known and any(row["value"] != known[0]["value"] for row in known):
            _fail("reused_identity_value_mismatch", "primitive_observation_refs")
        ref = identity("literature_optical_observation", sorted(group["keys"]))
        for role in roles:
            refs[role] = ref
        output.append({"primitive_roles": roles,
            "measurement_keys": sorted({r["measurement_key"] for r in rows}),
            "physical_observation_keys": sorted({r["physical_observation_key"] for r in rows if r["physical_observation_key"] is not None}),
            "primitive_observation_ref": ref})
    return output, [refs[role] for role in PRIMITIVE_ORDER]


def _finite(value, field):
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        _fail("finite_number_required", field)


def _matrix_valid(matrix):
    if not isinstance(matrix, list) or len(matrix) != 4 or any(not isinstance(row, list) or len(row) != 4 for row in matrix):
        _fail("four_by_four_covariance_required", "covariance")
    for i, row in enumerate(matrix):
        for j, value in enumerate(row):
            _finite(value, f"covariance[{i}][{j}]")
    if any(matrix[i][j] != matrix[j][i] for i in range(4) for j in range(i)):
        _fail("symmetric_covariance_required", "covariance")
    array = np.asarray(matrix, dtype=float)
    if np.any(np.diag(array) < 0):
        _fail("positive_semidefinite_covariance_required", "covariance")
    scale = float(np.max(np.abs(array)))
    try:
        eigenvalues = np.linalg.eigvalsh(array / scale) if scale else np.zeros(4)
    except np.linalg.LinAlgError:
        _fail("covariance_eigendecomposition_failed", "covariance")
    if not np.all(np.isfinite(eigenvalues)) or float(np.min(eigenvalues)) < -64 * np.finfo(float).eps * 4:
        _fail("positive_semidefinite_covariance_required", "covariance")


def _covariance(reference, observations, refs, sources):
    if reference is None:
        return None, None, "unknown"
    rows = [observations[role] for role in PRIMITIVE_ORDER]
    if any(row is None or row["number"] is None or row["unit"] is None or row["unit"]["canonical_unit"] is None for row in rows):
        _fail("complete_covariance_owners_required", "covariance_source_ref")
    source = sources.source(reference, "original")
    data = _json_source(source["content"], "covariance_source_ref")
    _keys(data, _COV_FIELDS, "covariance_source")
    expected = {"version": "a105_optical_covariance_v1", "primitive_order": list(PRIMITIVE_ORDER),
        "primitive_measurement_keys": [r["measurement_key"] for r in rows],
        "primitive_physical_observation_keys": [r["physical_observation_key"] for r in rows],
        "primitive_owner_keys": [r["owner_key"] for r in rows], "primitive_units": [r["unit"]["raw_unit"] for r in rows]}
    for field, value in expected.items():
        if data[field] != value:
            _fail("optical_covariance_owner_or_unit_mismatch", "covariance_source." + field)
    if data["origin"] not in ("reported", "derived", "synthetic") or data["covariance_status"] not in ("known", "estimated", "unknown"):
        _fail("unsupported_covariance_meaning", "covariance_source")
    _matrix_valid(data["covariance"])
    scales = [_UNIT_TABLES["signal" if i < 2 else PRIMITIVE_ORDER[i]][_normalize(row["unit"]["raw_unit"])][1] for i, row in enumerate(rows)]
    matrix = [[_float(Fraction(str(v)) * scales[i] * scales[j], "covariance") for j, v in enumerate(row)]
              for i, row in enumerate(data["covariance"])]
    _matrix_valid(matrix)
    for i, ref in enumerate(refs):
        for j in range(i):
            if ref is not None and ref == refs[j] and (matrix[i] != matrix[j] or any(row[i] != row[j] for row in matrix)):
                _fail("reused_identity_covariance_mismatch", "covariance")
    return {"source_ref": reference, "artifact_ref": source["artifact_ref"], "data": data}, matrix, data["covariance_status"]


def read_optical_rate_operands(selection, *, read_source):
    """Preserve source observations and project only supported point operands.

    reported_point denotes a reported point estimate, never zero physical
    uncertainty. Lexical or selected approximation and censoring remain visible.
    Covariance is separately source-owned; unknown covariance never means zero.
    """
    try:
        validate_schema(selection, optical_arguments_schema())
    except ContractError as error:
        raise ExperimentalContractError("optical_selection_schema_invalid", "selection", detail=error.detail) from error
    sources = _Sources(read_source)
    sources.source(selection["source_ref"], "original")
    context = {name: sources.witness(selection[name], name) if selection[name] is not None else None for name in LITERAL_FIELDS}
    interpretations = {name: _interpret(selection[name], values, sources, name) for name, values in INTERPRETATIONS.items()}
    source_origin = {"primary_source": "reported", "retained_extraction": "derived", "synthetic_fixture": "synthetic"}[selection["source_kind"]]
    signals = {role: _quantity(selection["signals"][role], "signal", role, context, sources, source_origin,
                              interpretations["signal_kind"]) for role in ("sample", "blank")}
    calibration = {role: _quantity(selection["calibration"][role], role, role, context, sources, source_origin)
                   for role in ("epsilon", "path_length", "wavelength")}
    observations = {"sample_slope": signals["sample"], "blank_slope": signals["blank"],
        "epsilon": calibration["epsilon"], "path_length": calibration["path_length"]}
    dependencies, refs = _groups(observations)
    cov_source, covariance, cov_status = _covariance(selection["covariance_source_ref"], observations, refs, sources)
    reasons, values = {}, {}
    for role, row in observations.items():
        reasons[role] = list(row["unavailable_reasons"]) if row else ["source_measurement_unreported"]
        if role in ("sample_slope", "blank_slope"):
            kind = interpretations["signal_kind"]["value"]
            if kind != "absorbance_slope":
                reasons[role].append("optical_signal_kind_unknown" if kind == "unknown" else "optical_signal_not_slope")
            if row and row["unit"] and row["unit"]["canonical_unit"] not in (None, "absorbance/min"):
                reasons[role].append("optical_signal_unit_mismatch")
        values[role] = row["value"] if row and not reasons[role] else None
    reasons["covariance"] = ["covariance_unreported"] if covariance is None else ["covariance_status_unknown"] if cov_status == "unknown" else []
    calculation = {"version": "a105_nadh_optical_rate_operands_v1", **values,
        "covariance": covariance, "covariance_status": cov_status,
        **{name: interpretations[name]["value"] for name in INTERPRETATIONS if name != "signal_kind"},
        "primitive_observation_refs": refs}
    return deepcopy({"version": VERSION, "source_ref": selection["source_ref"], "source_kind": selection["source_kind"],
        "context": context, **interpretations, "signals": signals, "calibration": calibration,
        "covariance_source": cov_source, "calculation_inputs": calculation,
        "input_unavailable_reasons": reasons, "dependencies": dependencies,
        "source_refs": list(sources.references), "lexical_dependency": LEXICAL_DEPENDENCY})


__all__ = ["VERSION", "PRIMITIVE_ORDER", "SOURCE_KINDS", "QUALIFICATIONS", "LEXICAL_DEPENDENCY",
           "optical_arguments_schema", "read_optical_rate_operands"]
