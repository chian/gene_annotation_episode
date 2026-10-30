"""Exact source-span scalar readers for experimental partner components.

The selected spans and their experimental roles are supplied interpretations.
This module verifies bytes, lexical boundaries and supported unit arithmetic;
it establishes no measurement identity, sampling model or biological truth.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import html
import math
import re

from .domain import obj
from .literature_assay_inputs import _index, _keys, _witness_schema
from .literature_experimental_contracts import ExperimentalContractError


_NUMBER = re.compile(r"[+−-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+−-]?[0-9]+)?\Z")
_TAG = r"</?[A-Za-z_][^<>]*>"
_TERMINAL_TAGS = re.compile(r"(?:" + _TAG + r"\s*)+$")
_INITIAL_TAGS = re.compile(r"^(?:\s*" + _TAG + r")+")
_ALL_TAGS = re.compile(_TAG)
_PM = re.compile(r"(?:±|\+\s*/\s*-|\+\s*−)\s*$")
_LOWER = re.compile(r"(?:>=?|≥|\b(?:greater\s+than(?:\s+or\s+equal\s+to)?|above|at\s+least|no\s+less\s+than))\s*$", re.I)
_UPPER = re.compile(r"(<=?|≤|\b(?:less\s+than(?:\s+or\s+equal\s+to)?|below|at\s+most|no\s+more\s+than))\s*$", re.I)
_APPROX = re.compile(r"(?:[~≈≃≅∼]|\b(?:approximately|about|circa|approx\.?))\s*$", re.I)
_POWER_MINUS_ONE = r"\s*\^?\s*[-−⁻]\s*[1¹]"
_PRINTED_RATE_UNIT = re.compile(
    r"(?:[pnuµμ]mol\s*(?:/\s*min\s*/\s*mg|\s*min" + _POWER_MINUS_ONE + r"\s*mg" + _POWER_MINUS_ONE + r")"
    r"|[unµμ]M\s*(?:/\s*min|\s*min" + _POWER_MINUS_ONE + r")"
    r"|per_?\s*(?:min|s)|(?:min|s)" + _POWER_MINUS_ONE + r"|1\s*/\s*(?:min|s))")
_RATE_UNIT_START = re.compile(r"(?:[pnumµμ]?mol|[unmµμ]?M|kg|mg|g|per_?\s*(?:min|s)|min|s|1\s*/)(?=\b|min|[/_^−⁻-])")
_SCALE = {
    "pmol/min/mg": ("pmol/min/mg", 1),
    "nmol/min/mg": ("pmol/min/mg", 1000),
    "umol/min/mg": ("pmol/min/mg", 1000000),
    "per_min": ("per_min", 1),
    "per_s": ("per_min", 60),
    "uM/min": ("uM/min", 1),
    "nM/min": ("uM/min", .001),
}


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def number_selector_schema():
    """Selectors contain offsets, never a supplied scientific number."""
    return obj({"witness": deepcopy(_witness_schema()),
        "number_start": {"type": "integer", "minimum": 0},
        "number_end": {"type": "integer", "minimum": 1}})


def _contexts(sources, witness, start, end):
    raw = sources.source(witness["source_ref"], witness["representation"])["content"]
    quote = witness["quote"]
    absolute_start = witness["start"] + len(quote[:start].encode("utf-8"))
    absolute_end = witness["start"] + len(quote[:end].encode("utf-8"))
    prefix = raw[:absolute_start].decode("utf-8", errors="ignore")
    suffix = raw[absolute_end:].decode("utf-8", errors="ignore")
    # Remove only real terminal/initial markup, before decoding comparator
    # entities. Encoded '<' is a comparator, not a fabricated XML element.
    return (html.unescape(_TERMINAL_TAGS.sub("", prefix)),
            html.unescape(_INITIAL_TAGS.sub("", suffix)))


def _relation(prefix, suffix, *, role):
    relative = r"(?:CV|RSD|coefficient\s+of\s+variation|relative\s+(?:standard\s+)?(?:error|uncertainty|deviation))"
    if role == "spread" and (re.match(r"\s*\(?\s*(?:%|percent\b|per\s+cent\b|" + relative + r"\b)", suffix, re.I)
            or re.search(r"(?:%|\bpercent|\bper\s+cent)\s*\)?\s*[:=]?\s*$", prefix, re.I)
            or re.search(r"\b" + relative + r"\s*(?:was|is|of|[:=])?\s*$", prefix, re.I)):
        _fail("relative_spread_unit_unsupported", "number")
    if re.search(r"\bnot\s+(?:(?:significantly|substantially|clearly)\s+)?(?:[<>]=?|[≤≥]|less\s+than(?:\s+or\s+equal\s+to)?|more\s+than|greater\s+than(?:\s+or\s+equal\s+to)?|below|above|at\s+(?:most|least))\s*$", prefix, re.I):
        _fail("negated_source_comparator_unsupported", "number")
    if _APPROX.search(prefix) or re.match(r"\s*(?:approximately|approx\.?|circa)\b", suffix, re.I):
        _fail("approximate_source_number_unsupported", "number")
    if (_LOWER.search(prefix) or re.match(r"\s*(?:or\s+(?:more|greater)|and\s+above)\b", suffix, re.I)):
        _fail("lower_bound_source_number_unsupported", "number")
    if (re.search(r"\b(?:between|from|range|interval|CI|confidence\s+interval)\s*[:=]?\s*[\[(]?\s*$", prefix, re.I)
            or re.search(r"\bbetween\b[^;\n]*\band\s*$", prefix, re.I)
            or re.search(r"\d\s*(?:[–—−-]|\bto)\s*$", prefix)
            or re.match(r"\s*(?:[–—−-]|\bto\b)\s*[+−-]?(?:\d|\.\d)", suffix)):
        _fail("interval_source_number_unsupported", "number")
    if re.search(r"\b(?:LOD|LOQ|limit\s+of\s+(?:detection|quantification)|detection\s+limit|upper\s+limit)\s*(?:was|is|of|[:=])?\s*$", prefix, re.I):
        _fail("untyped_limit_source_number", "number")
    plus_minus = bool(_PM.search(prefix))
    if role == "rate" and (plus_minus or re.search(
            r"\b(?:SD|SEM|standard\s+deviation|standard\s+error)\s*[:=]?\s*$", prefix, re.I)):
        _fail("uncertainty_is_not_rate_point", "number")
    upper = _UPPER.search(prefix)
    if upper:
        if role != "rate":
            _fail("plain_source_point_required", "number")
        marker = re.sub(r"\s+", " ", upper.group(1).lower())
        return "le" if marker in ("<=", "≤", "at most", "no more than") or "equal" in marker else "lt"
    if re.match(r"\s*(?:or\s+less|and\s+below)\b", suffix, re.I):
        _fail("postfix_source_bound_unsupported", "number")
    if re.match(r"\s*\.?\s*(?:[×⋅·*]|\bx\b)\s*10(?:\b|\^)", suffix):
        _fail("nonliteral_scientific_expression", "number")
    return "point"


def read_source_number(selector, *, sources, role):
    """Read one full point/upper-limit token and its exact source provenance.

    ``value`` is the finite native float; ``raw_number`` remains the exact token
    for decimal-rational conversion. Source offsets are bytes while selector
    offsets within a verified UTF8 quote are Unicode character positions.
    """
    _keys(selector, ("witness", "number_start", "number_end"), "number_selector")
    if role not in ("rate", "spread", "condition"):
        _fail("unsupported_source_number_role", "role")
    witness = sources.witness(selector["witness"], "number_selector.witness")
    for field in ("number_start", "number_end"):
        _index(selector[field], "number_selector." + field)
    start, end = selector["number_start"], selector["number_end"]
    quote = witness["quote"]
    if not 0 <= start < end <= len(quote):
        _fail("source_number_span_order_invalid", "number_selector")
    token = quote[start:end]
    if not _NUMBER.fullmatch(token):
        _fail("literal_source_number_required", "number_selector")
    prefix, suffix = _contexts(sources, witness, start, end)
    relation = _relation(prefix, suffix, role=role)
    before, after = prefix[-1:], suffix[:1]
    marker = _PM.search(prefix)
    # A minus sign belonging to a plus/minus marker is not a clipped numeric
    # sign for an explicitly selected spread. Everything else remains lexical.
    pm_spread = role == "spread" and marker is not None
    bad_prefix = before and (before in ".eE+−-" or before.isdigit() or before.isalpha() or before == "_") and not pm_spread
    # A permitted sentence stop applies only to the trailing edge. It must
    # never excuse a clipped digit/sign on the leading edge.
    sentence_stop = after == "." and (len(suffix) == 1 or suffix[1].isspace() or suffix[1] in ")]};:")
    bad_suffix = after and (after in ".eE+−-" or after.isdigit()) and not sentence_stop
    if bad_prefix or bad_suffix:
        _fail("partial_source_numeric_token", "number_selector")
    if (re.search(r"\d,\s*$", prefix) or re.match(r",\s*\d", suffix)):
        _fail("comma_source_number_unsupported", "number_selector")
    try:
        value = float(token.replace("−", "-"))
    except (OverflowError, ValueError) as error:
        raise ExperimentalContractError("numerical_model_range", "number_selector") from error
    if not math.isfinite(value) or value == 0 and any(c in "123456789" for c in token.lower().split("e", 1)[0]):
        _fail("numerical_model_range", "number_selector")
    if role == "spread" and value < 0:
        _fail("nonnegative_source_number_required", "number_selector")
    return {"selector": {**deepcopy(selector), "witness": witness},
        "raw_number": token, "value": value, "relation": relation}


def _rate_unit(raw):
    text = html.unescape(_ALL_TAGS.sub("", raw))
    text = re.sub(r"\s+", "", text).replace("µ", "u").replace("μ", "u")
    text = text.translate(str.maketrans({"−": "-", "⁻": "-", "¹": "1"})).replace("^", "")
    aliases = {key: key for key in _SCALE}
    for amount in ("pmol", "nmol", "umol"):
        aliases[amount + "min-1mg-1"] = amount + "/min/mg"
    for amount in ("uM", "nM"):
        aliases[amount + "min-1"] = amount + "/min"
    for unit, time in (("per_min", "min"), ("per_s", "s")):
        for alias in ("per" + time, time + "-1", "1/" + time):
            aliases[alias] = unit
    if text not in aliases:
        _fail("unsupported_source_rate_unit", "unit_witness")
    return _SCALE[aliases[text]]


def _unit_continuation(suffix):
    after = suffix[:1]
    return bool(after and (after.isalnum() or after in "/_^−-⁻¹%")) or bool(re.match(
        r"\s+(?:[/^]|[A-Za-zµμ]+\s*(?:\^?\s*[-−⁻]\s*[1¹]|/))", suffix))


def read_source_rate_unit(witness, *, sources):
    """Read one complete supported rate unit without assigning its denominator."""
    enriched = sources.witness(witness, "unit_witness")
    raw = enriched["quote"]
    prefix, suffix = _contexts(sources, enriched, 0, len(raw))
    before = prefix[-1:]
    if (before and (before.isalpha() or before in "_µμ/⁻¹^")) or _unit_continuation(suffix):
        _fail("partial_source_rate_unit", "unit_witness")
    canonical, multiplier = _rate_unit(raw)
    return {"witness": enriched, "raw_unit": raw,
        "canonical_unit": canonical, "multiplier": multiplier}


def _selected_witness(witness):
    """Remove only the host-added artifact identity before revalidating bytes."""
    return {name: witness[name] for name in ("source_ref", "representation", "start", "end", "quote")}


def validate_source_spread_unit(number, unit, *, sources):
    """Require any explicitly printed spread unit to match its supplied scale.

    No adjacent unit means the caller's supplied common-unit interpretation is
    retained. An explicitly printed supported rate unit is checked independently
    of that interpretation, including its multiplier. A percentage is never an
    absolute rate uncertainty. This function returns ``None`` on success.
    """
    _keys(number, ("selector", "raw_number", "value", "relation"), "source_number")
    _keys(unit, ("witness", "raw_unit", "canonical_unit", "multiplier"), "source_unit")
    selected = deepcopy(number["selector"])
    selected["witness"] = _selected_witness(selected["witness"])
    actual = read_source_number(selected, sources=sources, role="spread")
    if actual != number:
        _fail("source_number_record_mismatch", "source_number")
    actual_unit = read_source_rate_unit(_selected_witness(unit["witness"]), sources=sources)
    if actual_unit != unit:
        _fail("source_unit_record_mismatch", "source_unit")
    selected = actual["selector"]
    _, suffix = _contexts(sources, selected["witness"], selected["number_start"], selected["number_end"])
    visible = html.unescape(_ALL_TAGS.sub("", suffix)).lstrip()
    match = _PRINTED_RATE_UNIT.match(visible)
    if match is None:
        if _RATE_UNIT_START.match(visible):
            _fail("unsupported_explicit_spread_unit", "source_number")
        return None
    if _unit_continuation(visible[match.end():]):
        _fail("partial_source_rate_unit", "source_number")
    canonical, multiplier = _rate_unit(match.group())
    if (canonical, multiplier) != (unit["canonical_unit"], unit["multiplier"]):
        _fail("source_spread_unit_mismatch", "source_number")
    return None


def convert_source_number(number, unit):
    """Convert decimal source token exactly before its final float rounding."""
    _keys(number, ("selector", "raw_number", "value", "relation"), "source_number")
    _keys(unit, ("witness", "raw_unit", "canonical_unit", "multiplier"), "source_unit")
    if (not isinstance(number["raw_number"], str) or not _NUMBER.fullmatch(number["raw_number"])
            or number["relation"] not in ("point", "lt", "le")):
        _fail("invalid_source_number_record", "source_number")
    try:
        finite_value = type(number["value"]) in (int, float) and math.isfinite(number["value"])
    except OverflowError:
        finite_value = False
    if not finite_value:
        _fail("finite_number_required", "source_number.value")
    try:
        native_value = float(number["raw_number"].replace("−", "-"))
    except (OverflowError, ValueError) as error:
        raise ExperimentalContractError("numerical_model_range", "source_number") from error
    if not math.isfinite(native_value) or number["value"] != native_value:
        _fail("source_number_value_mismatch", "source_number.value")
    if native_value == 0 and any(c in "123456789" for c in number["raw_number"].lower().split("e", 1)[0]):
        _fail("numerical_model_range", "source_number")
    if not isinstance(unit["raw_unit"], str) or type(unit["multiplier"]) not in (int, float):
        _fail("invalid_source_unit_record", "source_unit")
    canonical, multiplier = _rate_unit(unit["raw_unit"])
    if (unit["canonical_unit"], unit["multiplier"]) != (canonical, multiplier):
        _fail("source_unit_conversion_mismatch", "source_unit")
    try:
        exact = Fraction(number["raw_number"].replace("−", "-")) * Fraction(str(multiplier))
        value = float(exact)
    except (OverflowError, ValueError, ZeroDivisionError) as error:
        raise ExperimentalContractError("numerical_model_range", "source_unit") from error
    if not math.isfinite(value) or value == 0 and exact != 0:
        _fail("numerical_model_range", "source_unit")
    return value


__all__ = ["number_selector_schema", "read_source_number", "read_source_rate_unit",
           "convert_source_number", "validate_source_spread_unit"]
