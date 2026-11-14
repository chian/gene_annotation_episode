"""Detached integrity checks for frozen A105 optical reader records.

This module checks saved fields and their relationships, never source bytes or
scientific truth. The lexical relation/approximation classifications were made
at population time: unseen neighbours, omitted units and source boundaries cannot
be re-proved here. Original operation authenticity and artifact custody belong to
storage. No population reader, source parser, calculator or episode is invoked.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import html
import math
import re

import numpy as np

from .domain import identity
from .literature_experimental_contracts import ExperimentalContractError

VERSION = "a105_optical_saved_validation_v1"
ERROR_CODES = (
    "optical_validation_closed_fields", "optical_validation_text",
    "optical_validation_enum", "optical_validation_witness",
    "optical_validation_witness_binding", "optical_validation_witness_overlap",
    "optical_validation_interpretation", "optical_validation_number",
    "optical_validation_finite", "optical_validation_range",
    "optical_validation_unit", "optical_validation_quantity",
    "optical_validation_positive_operand", "optical_validation_dependency",
    "optical_validation_reuse", "optical_validation_covariance",
    "optical_validation_covariance_owner", "optical_validation_calculation_inputs",
    "optical_validation_reasons", "optical_validation_source_roster",
    "optical_validation_selection",
)
_ORDER = ("sample_slope", "blank_slope", "epsilon", "path_length")
_CONTEXT = ("molecule", "construct", "preparation", "condition", "measured_entity")
_MEANINGS = ("measurement_identity", "condition", "measured_entity", "interval")
_QUALIFICATIONS = ("reported_point", "source_qualified_approximate", "unknown", "conflicting")
_INTERPRETATIONS = {
    "signal_kind": ("absorbance_slope", "absorbance_difference", "static_absorbance", "unknown"),
    "relation": ("applicable_extinction_relation", "not_applicable", "unknown", "conflicting"),
    "blank_role": ("matched_no_reaction_background", "condition_reference", "component_omission", "unknown", "conflicting"),
    "same_endpoint": ("same", "different", "unknown"),
    "matched_window": ("same", "different", "unknown"),
    "rate_window": ("source_supported_rate_interval", "interval_mean_only", "static_only", "unknown"),
}
_LEXICAL_DEPENDENCY = {
    "module": "gene_annotation_episode.literature_rate_native_inputs",
    "sha256_at_release": "55244315a64d0940c09d0410a9d1e930f73609e7d0d34ef5ed751a5bbad71500",
    "interface": "_number(selection,sources,role='rate'); _field_contexts",
    "scope_module": "gene_annotation_episode.literature_partner_source_fields",
    "scope_sha256_at_release": "20fd7866318fff00d80dcf3109c3a2589c36a38e35329d1b63ca954f2c035a17",
    "custody_module": "gene_annotation_episode.literature_assay_inputs",
    "custody_sha256_at_release": "52069b7d974556631a18d132eaa8bd79b23efc5b7dc2a583b1fff73df4758b6e",
}
_WITNESS = ("source_ref", "representation", "start", "end", "quote", "artifact_ref")
_NUMBER = re.compile(r"[+−-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+−-]?[0-9]+)?\Z")
_REF = re.compile(r"(?:[a-z][a-z_]*_[a-f0-9]{24,64}|@[A-Za-z][A-Za-z0-9_]*)\Z")
_TAGS = re.compile(r"</?[A-Za-z_][^<>]*>")
_TRANSLATE = str.maketrans({"−": "-", "⁻": "-", "¹": "1", "µ": "u", "μ": "u"})


def _fail(code, field):
    raise ExperimentalContractError("optical_validation_" + code, field)


def _keys(value, names, field):
    if type(value) is not dict or set(value) != set(names):
        _fail("closed_fields", field)


def _text(value, field, *, reference=False):
    if type(value) is not str or not value.strip():
        _fail("text", field)
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        _fail("text", field)
    if reference and not _REF.fullmatch(value):
        _fail("text", field)


def _enum(value, allowed, field):
    if type(value) is not str or value not in allowed:
        _fail("enum", field)


def _finite(value, field):
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        _fail("finite", field)


def _float(value, field):
    try:
        result = float(value)
    except (OverflowError, ValueError):
        _fail("range", field)
    if not math.isfinite(result) or result == 0 and value != 0:
        _fail("range", field)
    return result


def _equal(actual, expected):
    """JSON equality with bool distinct from numeric zero/one."""
    if type(expected) is dict:
        return (type(actual) is dict and set(actual) == set(expected)
                and all(_equal(actual[k], v) for k, v in expected.items()))
    if type(expected) is list:
        return (type(actual) is list and len(actual) == len(expected)
                and all(_equal(a, b) for a, b in zip(actual, expected)))
    if type(expected) in (int, float):
        return type(actual) in (int, float) and actual == expected
    return type(actual) is type(expected) and actual == expected


def _same(actual, expected, code, field):
    if not _equal(actual, expected):
        _fail(code, field)


def _units():
    """Frozen035 finite unit vocabulary; no source context/parser calls."""
    signal, epsilon = {}, {}
    for name, scale in (("absorbance", Fraction(1)), ("AU", Fraction(1)), ("mAU", Fraction(1, 1000))):
        signal[name] = ("absorbance", scale)
        for time, factor in (("min", Fraction(1)), ("s", Fraction(60))):
            for spelling in (name + "/" + time, name + time + "-1"):
                signal[spelling] = ("absorbance/min", scale * factor)
    for molarity, amount, scale in (("mM", "mmol", Fraction(1)), ("M", "mol", Fraction(1, 1000)), ("uM", "umol", Fraction(1000))):
        for spelling in (molarity + "-1cm-1", "1/(" + molarity + "cm)", "L" + amount + "-1cm-1"):
            epsilon[spelling] = ("mM^-1cm^-1", scale)
    return {"signal": signal, "epsilon": epsilon,
        "path_length": {"cm": ("cm", Fraction(1)), "mm": ("cm", Fraction(1, 10)), "m": ("cm", Fraction(100))},
        "wavelength": {"nm": ("nm", Fraction(1)), "um": ("nm", Fraction(1000)), "m": ("nm", Fraction(1000000000))}}


_UNITS = _units()


class _Witnesses:
    """Check saved custody relationships and reproduce source first-use order."""
    def __init__(self, root):
        self.refs = [root]
        self.bindings = {}
        self.windows = {}

    def source(self, source, artifact, representation):
        _text(source, "source_ref", reference=True)
        _text(artifact, "artifact_ref")
        key = (source, representation)
        if key in self.bindings and self.bindings[key] != artifact:
            _fail("witness_binding", "artifact_ref")
        self.bindings[key] = artifact
        if source not in self.refs:
            self.refs.append(source)

    def witness(self, value, field):
        if value is None:
            return
        _keys(value, _WITNESS, field)
        _text(value["quote"], field + ".quote")
        _enum(value["representation"], ("original", "text"), field + ".representation")
        first, last = value["start"], value["end"]
        raw = value["quote"].encode("utf-8")
        if (type(first) is not int or type(last) is not int
                or not 0 <= first < last or last - first != len(raw)):
            _fail("witness", field)
        self.source(value["source_ref"], value["artifact_ref"], value["representation"])
        windows = self.windows.setdefault(value["artifact_ref"], [])
        for start, end, data in windows:
            lo, hi = max(start, first), min(end, last)
            if lo < hi and data[lo-start:hi-start] != raw[lo-first:hi-first]:
                _fail("witness_overlap", field)
        windows.append((first, last, raw))

    def interpretation(self, value, allowed, field):
        _keys(value, ("value", "witnesses"), field)
        _enum(value["value"], allowed, field)
        if type(value["witnesses"]) is not list:
            _fail("interpretation", field)
        for witness in value["witnesses"]:
            if witness is None:
                _fail("interpretation", field)
            self.witness(witness, field)
        distinct = {(w["source_ref"], w["artifact_ref"], w["start"], w["end"]) for w in value["witnesses"]}
        minimum = 0 if value["value"] == "unknown" else 2 if value["value"] == "conflicting" else 1
        if len(distinct) < minimum:
            _fail("interpretation", field)


def _saved_number(value, witnesses, field):
    _keys(value, ("selector", "raw_number", "value", "relation", "approximate"), field)
    selector = value["selector"]
    _keys(selector, ("witness", "number_start", "number_end"), field + ".selector")
    if selector["witness"] is None:
        _fail("number", field)
    witnesses.witness(selector["witness"], field + ".witness")
    start, end = selector["number_start"], selector["number_end"]
    quote = selector["witness"]["quote"]
    if (type(start) is not int or type(end) is not int or not 0 <= start < end <= len(quote)
            or type(value["raw_number"]) is not str or quote[start:end] != value["raw_number"]
            or not _NUMBER.fullmatch(value["raw_number"]) or type(value["approximate"]) is not bool):
        _fail("number", field)
    _enum(value["relation"], ("point", "lt", "le", "gt", "ge"), field + ".relation")
    _finite(value["value"], field + ".value")
    expected = _float(Fraction(value["raw_number"].replace("−", "-")), field)
    _same(value["value"], expected, "number", field)


def _saved_unit(value, kind, witnesses, field):
    _keys(value, ("witness", "raw_unit", "canonical_unit", "multiplier", "unavailable_reason"), field)
    if value["witness"] is None:
        _fail("unit", field)
    witnesses.witness(value["witness"], field + ".witness")
    _same(value["raw_unit"], value["witness"]["quote"], "unit", field)
    normalized = re.sub(r"\s+", "", html.unescape(_TAGS.sub("", value["raw_unit"])).translate(_TRANSLATE).replace("^", ""))
    parsed = _UNITS[kind].get(normalized)
    expected = (parsed[0], float(parsed[1]), None) if parsed else (None, None, "unsupported_source_optical_unit")
    _same([value[k] for k in ("canonical_unit", "multiplier", "unavailable_reason")], list(expected), "unit", field)
    return parsed[1] if parsed else None


def _quantity(row, kind, role, extraction, witnesses):
    if row is None:
        return None
    _keys(row, ("meanings", "qualification", "number", "unit", "value", "status", "approximate", "measurement_key", "physical_observation_key", "owner_key", "source_origin", "origin", "unavailable_reasons"), role)
    _keys(row["meanings"], _MEANINGS, role + ".meanings")
    for name in _MEANINGS:
        witnesses.witness(row["meanings"][name], role + ".meanings." + name)
    witnesses.interpretation(row["qualification"], _QUALIFICATIONS, role + ".qualification")
    number, unit = row["number"], row["unit"]
    if number is not None:
        _saved_number(number, witnesses, role + ".number")
    scale = _saved_unit(unit, kind, witnesses, role + ".unit") if unit is not None else None
    if number is None and unit is not None:
        _fail("quantity", role + ".unit")
    value = _float(Fraction(number["raw_number"].replace("−", "-")) * scale, role) if number is not None and scale is not None else None
    approximate = bool(number and number["approximate"] or row["qualification"]["value"] == "source_qualified_approximate")
    if kind != "signal" and value is not None and number["relation"] == "point" and not approximate and value <= 0:
        _fail("positive_operand", role)
    measurement_key = None
    if number is not None:
        selector, w = number["selector"], number["selector"]["witness"]
        measurement_key = identity("literature_optical_measurement", {"source_ref": w["source_ref"], "artifact_ref": w["artifact_ref"],
            "start": w["start"] + len(w["quote"][:selector["number_start"]].encode("utf-8")),
            "end": w["start"] + len(w["quote"][:selector["number_end"]].encode("utf-8"))})
    physical = row["meanings"]["measurement_identity"]
    physical_key = None if physical is None else identity("literature_optical_physical", {k: physical[k] for k in ("source_ref", "artifact_ref", "start", "end")})
    owner_key = None if number is None else identity("literature_optical_owner", {
        "measurement_key": measurement_key, "meanings": row["meanings"], "context": extraction["context"], "role": role,
        "quantity_kind": kind, "signal_kind": extraction["signal_kind"] if kind == "signal" else None, "qualification": row["qualification"]})
    source_origin = {"primary_source": "reported", "retained_extraction": "derived", "synthetic_fixture": "synthetic"}[extraction["source_kind"]]
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
    if row["qualification"]["value"] in ("unknown", "conflicting"):
        reasons.append("source_operand_qualification_" + row["qualification"]["value"])
    expected = {"value": value, "status": "unavailable" if value is None else "observed" if number["relation"] == "point" else "censored",
        "approximate": approximate, "measurement_key": measurement_key, "physical_observation_key": physical_key,
        "owner_key": owner_key, "source_origin": source_origin,
        "origin": "derived" if value is not None and unit["multiplier"] != 1 else source_origin,
        "unavailable_reasons": reasons}
    _same({k: row[k] for k in expected}, expected, "quantity", role)
    return scale


def _dependencies(observations):
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
    output, refs = [], dict.fromkeys(_ORDER)
    dimensions = dict(zip(_ORDER, ("absorbance/min", "absorbance/min", "mM^-1cm^-1", "cm")))
    for group in groups:
        roles = [r for r in _ORDER if r in group["roles"]]
        rows = [observations[r] for r in roles]
        known = [r for r in rows if r["value"] is not None]
        if (len({dimensions[r] for r in roles}) != 1
                or known and any(r["unit"]["canonical_unit"] != known[0]["unit"]["canonical_unit"] or r["value"] != known[0]["value"] for r in known)):
            _fail("reuse", "dependencies")
        ref = identity("literature_optical_observation", sorted(group["keys"]))
        for role in roles:
            refs[role] = ref
        output.append({"primitive_roles": roles, "measurement_keys": sorted({r["measurement_key"] for r in rows}),
            "physical_observation_keys": sorted({r["physical_observation_key"] for r in rows if r["physical_observation_key"] is not None}),
            "primitive_observation_ref": ref})
    return output, [refs[r] for r in _ORDER]


def _matrix(matrix):
    if type(matrix) is not list or len(matrix) != 4 or any(type(row) is not list or len(row) != 4 for row in matrix):
        _fail("covariance", "covariance")
    for row in matrix:
        for value in row:
            _finite(value, "covariance")
    if any(matrix[i][j] != matrix[j][i] for i in range(4) for j in range(i)):
        _fail("covariance", "covariance.symmetry")
    array = np.asarray(matrix, dtype=float)
    if np.any(np.diag(array) < 0):
        _fail("covariance", "covariance.diagonal")
    scale = float(np.max(np.abs(array)))
    try:
        eigenvalues = np.linalg.eigvalsh(array / scale) if scale else np.zeros(4)
    except np.linalg.LinAlgError:
        _fail("covariance", "covariance.eigenvalues")
    if not np.all(np.isfinite(eigenvalues)) or float(np.min(eigenvalues)) < -64 * np.finfo(float).eps * 4:
        _fail("covariance", "covariance.eigenvalues")


def _covariance(source, observations, scales, refs, witnesses):
    if source is None:
        return None, "unknown"
    _keys(source, ("source_ref", "artifact_ref", "data"), "covariance_source")
    witnesses.source(source["source_ref"], source["artifact_ref"], "original")
    rows = [observations[r] for r in _ORDER]
    if any(row is None or row["number"] is None or scales[r] is None for r, row in zip(_ORDER, rows)):
        _fail("covariance_owner", "covariance_source")
    data = source["data"]
    _keys(data, ("version", "primitive_order", "primitive_measurement_keys", "primitive_physical_observation_keys", "primitive_owner_keys", "primitive_units", "covariance", "origin", "covariance_status"), "covariance_source.data")
    expected = {"version": "a105_optical_covariance_v1", "primitive_order": list(_ORDER),
        "primitive_measurement_keys": [r["measurement_key"] for r in rows],
        "primitive_physical_observation_keys": [r["physical_observation_key"] for r in rows],
        "primitive_owner_keys": [r["owner_key"] for r in rows], "primitive_units": [r["unit"]["raw_unit"] for r in rows]}
    _same({k: data[k] for k in expected}, expected, "covariance_owner", "covariance_source.data")
    _enum(data["origin"], ("reported", "derived", "synthetic"), "covariance_source.origin")
    _enum(data["covariance_status"], ("known", "estimated", "unknown"), "covariance_source.status")
    _matrix(data["covariance"])
    matrix = [[_float(Fraction(str(v)) * scales[_ORDER[i]] * scales[_ORDER[j]], "covariance")
               for j, v in enumerate(row)] for i, row in enumerate(data["covariance"])]
    _matrix(matrix)
    for i, ref in enumerate(refs):
        for j in range(i):
            if ref is not None and ref == refs[j] and (matrix[i] != matrix[j] or any(row[i] != row[j] for row in matrix)):
                _fail("reuse", "covariance")
    return matrix, data["covariance_status"]


def validate_optical_extraction(extraction):
    """Validate saved035 relationships; return an independent, unchanged copy."""
    _keys(extraction, ("version", "source_ref", "source_kind", "context", *_INTERPRETATIONS,
        "signals", "calibration", "covariance_source", "calculation_inputs", "input_unavailable_reasons", "dependencies", "source_refs", "lexical_dependency"), "extraction")
    _enum(extraction["version"], ("a105_optical_inputs_v1",), "version")
    _enum(extraction["source_kind"], ("primary_source", "retained_extraction", "synthetic_fixture"), "source_kind")
    _text(extraction["source_ref"], "source_ref", reference=True)
    _same(extraction["lexical_dependency"], _LEXICAL_DEPENDENCY, "dependency", "lexical_dependency")
    witnesses = _Witnesses(extraction["source_ref"])
    _keys(extraction["context"], _CONTEXT, "context")
    for name in _CONTEXT:
        witnesses.witness(extraction["context"][name], "context." + name)
    for name, allowed in _INTERPRETATIONS.items():
        witnesses.interpretation(extraction[name], allowed, name)
    _keys(extraction["signals"], ("sample", "blank"), "signals")
    _keys(extraction["calibration"], ("epsilon", "path_length", "wavelength"), "calibration")
    scales = {}
    for role in ("sample", "blank"):
        scales[role + "_slope"] = _quantity(extraction["signals"][role], "signal", role, extraction, witnesses)
    for role in ("epsilon", "path_length", "wavelength"):
        scales[role] = _quantity(extraction["calibration"][role], role, role, extraction, witnesses)
    observations = {"sample_slope": extraction["signals"]["sample"], "blank_slope": extraction["signals"]["blank"],
        "epsilon": extraction["calibration"]["epsilon"], "path_length": extraction["calibration"]["path_length"]}
    groups, refs = _dependencies(observations)
    _same(extraction["dependencies"], groups, "dependency", "dependencies")
    covariance, status = _covariance(extraction["covariance_source"], observations, scales, refs, witnesses)
    reasons, values = {}, {}
    for role, row in observations.items():
        reasons[role] = list(row["unavailable_reasons"]) if row else ["source_measurement_unreported"]
        if role in ("sample_slope", "blank_slope"):
            kind = extraction["signal_kind"]["value"]
            if kind != "absorbance_slope":
                reasons[role].append("optical_signal_kind_unknown" if kind == "unknown" else "optical_signal_not_slope")
            if row and row["unit"] and row["unit"]["canonical_unit"] not in (None, "absorbance/min"):
                reasons[role].append("optical_signal_unit_mismatch")
        values[role] = row["value"] if row and not reasons[role] else None
    reasons["covariance"] = ["covariance_unreported"] if covariance is None else ["covariance_status_unknown"] if status == "unknown" else []
    expected = {"version": "a105_nadh_optical_rate_operands_v1", **values, "covariance": covariance,
        "covariance_status": status, **{name: extraction[name]["value"] for name in _INTERPRETATIONS if name != "signal_kind"}, "primitive_observation_refs": refs}
    _same(extraction["calculation_inputs"], expected, "calculation_inputs", "calculation_inputs")
    _same(extraction["input_unavailable_reasons"], reasons, "reasons", "input_unavailable_reasons")
    _same(extraction["source_refs"], witnesses.refs, "source_roster", "source_refs")
    return deepcopy(extraction)


def validate_optical_selection(selection, extraction):
    """Validate full selected↔enriched linkage, with no IO or re-population."""
    extraction = validate_optical_extraction(extraction)
    def witness(w):
        return None if w is None else {k: w[k] for k in _WITNESS if k != "artifact_ref"}
    def interpretation(item):
        return {"value": item["value"], "witnesses": [witness(w) for w in item["witnesses"]]}
    def quantity(row):
        if row is None:
            return None
        number = row["number"]
        return {**{name: witness(row["meanings"][name]) for name in _MEANINGS},
            "qualification": interpretation(row["qualification"]),
            "measurement": None if number is None else {"number": {**number["selector"], "witness": witness(number["selector"]["witness"])},
                "unit": witness(row["unit"]["witness"]) if row["unit"] else None}}
    expected = {"source_ref": extraction["source_ref"], "source_kind": extraction["source_kind"],
        **{name: witness(extraction["context"][name]) for name in _CONTEXT},
        **{name: interpretation(extraction[name]) for name in _INTERPRETATIONS},
        "signals": {role: quantity(extraction["signals"][role]) for role in ("sample", "blank")},
        "calibration": {role: quantity(extraction["calibration"][role]) for role in ("epsilon", "path_length", "wavelength")},
        "covariance_source_ref": extraction["covariance_source"]["source_ref"] if extraction["covariance_source"] else None}
    _same(selection, expected, "selection", "selection")
    return deepcopy(selection)


__all__ = ["VERSION", "ERROR_CODES", "validate_optical_extraction", "validate_optical_selection"]
