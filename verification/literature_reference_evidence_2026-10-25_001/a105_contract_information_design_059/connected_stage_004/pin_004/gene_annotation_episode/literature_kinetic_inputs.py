"""Read selected kinetic parameter estimates; source meanings remain interpreted.

This finite source reader has no acquisition, Store, scoring, model or episode
behavior. Its caller authorizes each read. Exact quotes establish custody,
not scientific attribution or the applicability of a kinetic observation model.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import html
import math
import re

from .domain import REF, ContractError, identity, obj, validate_schema
from .literature_assay_inputs import _Sources, _nullable, _witness_schema, _index
from .literature_experimental_contracts import ExperimentalContractError
from .literature_partner_source_fields import number_selector_schema
from .literature_rate_native_inputs import (
    _number, _field_contexts, _PHYSICAL_UNIT, _APPROX, _UPPER, _LOWER,
)


VERSION = "a105_kinetic_source_extraction_v2"
SELECTION_VERSION = "a105_kinetic_source_selection_v1"
SOURCE_KINDS = ("primary_source", "synthetic_fixture")
PARAMETER_UNITS = {"Km": "uM", "kcat": "per_min", "catalytic_efficiency": "uM^-1min^-1"}
SUBJECT_FIELDS = ("organism", "genotype", "molecule", "construct")
CONTEXT_FIELDS = ("substrate", "preparation", "experiment", "experimental_system",
                  "conditions", "endpoint", "normalization")
QUALIFICATIONS = ("reported_point", "source_qualified_approximate", "unknown", "conflicting")
COUNT_STATUSES = ("not_selected", "exact", "qualified", "range_or_alternatives", "unsupported", "not_positive")
COUNT_REASONS = ("exact_count_qualified", "count_range_or_alternatives", "unsupported_count_literal", "positive_count_required")
COUNT_NOTATIONS = ("decimal_digits", "english_cardinal", "unsupported")
COUNT_RELATIONS = ("point", "lt", "le", "gt", "ge", "unresolved")
COMPARISON_VALUES = {
    "subject_relationship": ("same_molecule_and_construct", "different", "unknown", "conflicting"),
    "parameter_definition_relationship": ("same", "different", "unknown", "conflicting"),
    "substrate_arrangement": ("separate_assays", "mixed_substrates", "unknown", "conflicting"),
    "comparison_scope": ("reported_protocols", "common_conditions", "unknown", "conflicting"),
    "nonintended_conditions_relationship": ("matched", "different", "unknown", "conflicting"),
}
DEPENDENCIES = {
    "custody_module": "gene_annotation_episode.literature_assay_inputs",
    "custody_sha256": "52069b7d974556631a18d132eaa8bd79b23efc5b7dc2a583b1fff73df4758b6e",
    "scalar_module": "gene_annotation_episode.literature_rate_native_inputs",
    "scalar_sha256": "55244315a64d0940c09d0410a9d1e930f73609e7d0d34ef5ed751a5bbad71500",
    "scalar_scope_module": "gene_annotation_episode.literature_partner_source_fields",
    "scalar_scope_sha256": "20fd7866318fff00d80dcf3109c3a2589c36a38e35329d1b63ca954f2c035a17",
}
# These are expected release fingerprints, not a runtime attestation. The pure
# reader performs no implementation-file IO. A storage integrator must pin and
# authenticate actual dependencies; verification receipts record actual hashes.
_NUMBER = r"[+−-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+−-]?[0-9]+)?"
_TRANSLATE = str.maketrans({"−": "-", "⁻": "-", "¹": "1", "µ": "u", "μ": "u"})
_TAGS = re.compile(r"</?[A-Za-z_][^<>]*>")


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _meaning_schema(values):
    return obj({"value": {"enum": list(values)},
        "witnesses": {"type": "array", "items": _witness_schema()}})


def kinetic_arguments_schema():
    """All scientific numbers are selected spans, never supplied operands."""
    witness, number = _witness_schema(), number_selector_schema()
    count = deepcopy(number)
    count["description"] = ("Select the complete reported repetition numeral, which may be decimal digits or an English cardinal word expression. "
        "Outer witness offsets are UTF8 bytes; number_start and number_end are Unicode character positions inside that exact quote. "
        "Do not supply a converted number. Qualified or unsupported counts retain partial source information; repetition meaning is selected separately.")
    interval = obj({"witness": deepcopy(witness), **{name: {"type": "integer", "minimum": 0}
        for name in ("lower_start", "lower_end", "upper_start", "upper_end")}})
    uncertainty = obj({
        "statistic": _meaning_schema(("sd", "sem", "ci", "unspecified", "unreported")),
        "magnitude": _nullable(deepcopy(number)), "interval": _nullable(interval),
        "unit": _nullable(deepcopy(witness)),
        "unit_relationship": _meaning_schema(("same_as_parameter", "explicit_unit", "unknown")),
        "confidence_level": _nullable(deepcopy(witness)), "count": _nullable(count),
        "repetition_basis": _meaning_schema(("biological_preparations", "technical_measurements", "unspecified")),
        "estimate_basis": _meaning_schema(("fit_to_averaged_curve", "between_fitted_parameters", "unknown")),
    })
    operand = obj({
        "parameter_kind": _meaning_schema((*PARAMETER_UNITS, "unknown", "conflicting")),
        "subject": obj({name: _nullable(deepcopy(witness)) for name in SUBJECT_FIELDS}),
        "context": obj({name: _nullable(deepcopy(witness)) for name in CONTEXT_FIELDS}),
        "measurement_identity": _nullable(deepcopy(witness)),
        "measurement": _nullable(obj({"number": deepcopy(number), "unit": _nullable(deepcopy(witness))})),
        "qualification": _meaning_schema(QUALIFICATIONS), "uncertainty": uncertainty,
    })
    return obj({"version": {"const": SELECTION_VERSION}, "source_ref": deepcopy(REF),
        "source_kind": {"enum": list(SOURCE_KINDS)},
        "numerator": _nullable(deepcopy(operand)), "denominator": _nullable(deepcopy(operand)),
        "comparison": obj({name: _meaning_schema(values) for name, values in COMPARISON_VALUES.items()})})


def _interpret(selected, sources, field):
    witnesses = [sources.witness(w, field + ".witnesses") for w in selected["witnesses"]]
    unique = {_locator_key(w) for w in witnesses}
    value = selected["value"]
    minimum = (2 if value == "conflicting" else 0 if value in
               ("unknown", "unspecified", "unreported") else 1)
    if len(unique) < minimum:
        _fail("interpretation_witness_required", field)
    return {"value": value, "witnesses": witnesses}


def _locator(witness):
    return {name: witness[name] for name in ("source_ref", "artifact_ref", "representation", "start", "end")}


def _locator_key(witness):
    return tuple(_locator(witness).values())


def _normalize(raw):
    visible = html.unescape(_TAGS.sub("", raw)).translate(_TRANSLATE).replace("^", "")
    return re.sub(r"\s+", "", visible)


def _unit_tables():
    concentration = {"M": Fraction(1000000), "mM": Fraction(1000),
                     "uM": Fraction(1), "nM": Fraction(1, 1000)}
    time = {"min": Fraction(1), "s": Fraction(60)}
    tables = {"Km": {unit: ("uM", scale) for unit, scale in concentration.items()}, "kcat": {},
              "catalytic_efficiency": {}}
    for duration, scale in time.items():
        for spelling in (duration + "-1", "1/" + duration, "per_" + duration, "per" + duration):
            tables["kcat"][spelling] = ("per_min", scale)
        for molarity, amount_scale in concentration.items():
            for spelling in (molarity + "-1" + duration + "-1", duration + "-1" + molarity + "-1",
                             "1/(" + molarity + duration + ")", "1/" + molarity + "/" + duration,
                             molarity + "-1/" + duration, duration + "-1/" + molarity):
                tables["catalytic_efficiency"][spelling] = ("uM^-1min^-1", scale / amount_scale)
    return tables


_UNIT_TABLES = _unit_tables()
_ALL_UNITS = {name: value for table in _UNIT_TABLES.values() for name, value in table.items()}


def _tail_continues(after):
    first = after[:1]
    return bool(first and (first.isalnum() or first in "/_^−-⁻¹%")) or bool(re.match(
        r"\s+(?:[/^]|[A-Za-zµμ]+\s*\^?\s*[-−⁻]\s*[1¹]|per\s+(?:min|s|h|mg|g|mol|[munµμ]?M)\b)", after))


def _unit(selection, kind, sources):
    if selection is None:
        return None
    witness = sources.witness(selection, "kinetic.unit")
    before, after = _field_contexts(sources, witness, 0, len(witness["quote"]))
    compound_prefix = re.search(r"(?:[/^]\s*\(?\s*|\b(?:[nmuµμ]?M|mol|mg|g|min|s|h)\s*(?:\^?[-−⁻][1¹])?\s+)$", before)
    if ((before[-1:] and (before[-1:].isalpha() or before[-1:] in "_µμ/^⁻¹"))
            or compound_prefix or _tail_continues(after)):
        _fail("partial_source_kinetic_unit", "kinetic.unit")
    parsed = _UNIT_TABLES.get(kind, {}).get(_normalize(witness["quote"]))
    return {"witness": witness, "raw_unit": witness["quote"],
        "canonical_unit": parsed[0] if parsed else None,
        "multiplier": float(parsed[1]) if parsed else None,
        "unavailable_reason": None if parsed else "unsupported_source_kinetic_unit"}


def _explicit_unit(number, selected, kind, sources):
    if number is None or selected is None or selected["canonical_unit"] is None:
        return
    ns = number["selector"]
    _, after = _field_contexts(sources, ns["witness"], ns["number_start"], ns["number_end"])
    visible = after.lstrip()
    # One complete plus/minus value can precede the common explicit unit.
    plus_minus = re.match(r"(?:±|\+\s*/\s*-)\s*" + _NUMBER + r"\s*", visible)
    if plus_minus:
        visible = visible[plus_minus.end():]
    _explicit_unit_after(visible, selected, kind)


def _explicit_unit_after(visible, selected, kind):
    if selected is None or selected["canonical_unit"] is None:
        return
    compact, positions = "", []
    for i, char in enumerate(visible):
        translated = char.translate(_TRANSLATE)
        if translated.isspace() or translated == "^":
            continue
        compact += translated
        positions.append(i + 1)
    for spelling in sorted(_ALL_UNITS, key=len, reverse=True):
        if not compact.startswith(spelling):
            continue
        end = positions[len(spelling) - 1]
        if visible[end:end + 1].isalnum():
            _fail("unsupported_explicit_kinetic_unit", "kinetic.number")
        if _tail_continues(visible[end:]):
            _fail("partial_source_kinetic_unit", "kinetic.number")
        if _UNIT_TABLES.get(kind, {}).get(spelling) != _UNIT_TABLES[kind].get(_normalize(selected["raw_unit"])):
            _fail("source_kinetic_unit_mismatch", "kinetic.number")
        return
    if re.match(r"(?:[A-Za-zµμ]*M[A-Za-z0-9_]*|[A-Za-zµμ]*AU|[pnmuµμ]?mol|[kmunµμ]?g|[kmunµμ]?L|s|min|h|U)(?=\b|[/_^−⁻-])", visible):
        _fail("unsupported_explicit_kinetic_unit", "kinetic.number")


def _literal_fraction(raw):
    token = raw.replace("−", "-")
    return Fraction(token) if any(c in "123456789" for c in token.lower().split("e", 1)[0]) else Fraction(0)


def _converted(number, unit, field):
    if number is None or unit is None or unit["canonical_unit"] is None:
        return None, None
    scale = next(table[_normalize(unit["raw_unit"])][1] for table in _UNIT_TABLES.values()
                 if _normalize(unit["raw_unit"]) in table)
    try:
        exact = _literal_fraction(number["raw_number"]) * scale
        value = float(exact)
    except (ArithmeticError, ValueError):
        return None, "source_numeric_range"
    if not math.isfinite(value) or value == 0 and exact != 0:
        return None, "source_numeric_range"
    return value, None


def _interval(selection, sources):
    if selection is None:
        return None
    witness = sources.witness(selection["witness"], "uncertainty.interval")
    quote = witness["quote"]
    match = re.fullmatch(r"\s*[\[(]\s*(?P<lower>" + _NUMBER + r")\s*,\s*(?P<upper>" + _NUMBER + r")\s*[\])]\s*", quote)
    if match is None or (quote.strip()[0], quote.strip()[-1]) not in (("[", "]"), ("(", ")")):
        _fail("literal_ci_interval_required", "uncertainty.interval")
    for side in ("lower", "upper"):
        if (selection[side + "_start"], selection[side + "_end"]) != match.span(side):
            _fail("ci_interval_selector_mismatch", "uncertainty.interval")
    before, after = _field_contexts(sources, witness, 0, len(quote))
    if before[-1:] and (before[-1:].isdigit() or before[-1:] in ".eE+−-_") or after[:1] and (after[:1].isdigit() or after[:1] in ".eE+−-_"):
        _fail("partial_source_ci_interval", "uncertainty.interval")
    if re.search(r"(?:[<>≤≥~≈]|\b(?:about|approximately|below|above|at\s+least|at\s+most))\s*$", before, re.I):
        _fail("qualified_ci_interval_unsupported", "uncertainty.interval")
    raw_values = [match["lower"], match["upper"]]
    try:
        values = [float(v.replace("−", "-")) for v in raw_values]
    except (ValueError, OverflowError):
        _fail("numerical_model_range", "uncertainty.interval")
    if any(not math.isfinite(v) or v == 0 and any(c in "123456789" for c in raw.lower().split("e", 1)[0])
           for raw, v in zip(raw_values, values)):
        _fail("numerical_model_range", "uncertainty.interval")
    try:
        exact = [_literal_fraction(raw) for raw in raw_values]
    except ValueError:
        _fail("numerical_model_range", "uncertainty.interval")
    if exact[0] > exact[1]:
        _fail("ordered_ci_interval_required", "uncertainty.interval")
    return {"selector": {**deepcopy(selection), "witness": witness}, "raw_values": raw_values, "values": values}


def _confidence(selection, sources):
    if selection is None:
        return None
    witness = sources.witness(selection, "uncertainty.confidence_level")
    match = re.fullmatch(r"\s*(" + _NUMBER + r")\s*%\s*", witness["quote"])
    if match is None:
        _fail("literal_percent_confidence_required", "uncertainty.confidence_level")
    before, after = _field_contexts(sources, witness, 0, len(witness["quote"]))
    if before[-1:] and (before[-1:].isalnum() or before[-1:] in ".eE+−-_") or after[:1] and (after[:1].isalnum() or after[:1] in ".eE+−-_%"):
        _fail("partial_source_confidence_level", "uncertainty.confidence_level")
    qualifier = (r"(?:[<>≤≥~≈≃≅∼]|\b(?:less\s+than(?:\s+or\s+equal\s+to)?|greater\s+than(?:\s+or\s+equal\s+to)?"
        r"|more\s+than|below|above|at\s+(?:least|most)|no\s+(?:more|less)\s+than"
        r"|approximately|roughly|around|about|circa|approx\.?))\s*$")
    if (re.search(qualifier, before, re.I)
            or re.match(r"\s*(?:or\s+(?:more|less|greater)|and\s+(?:above|below)|approximately|roughly|around|about|circa)\b", after, re.I)):
        raise ExperimentalContractError("qualified_source_confidence_unsupported", "uncertainty.confidence_level",
            detail={"witness": deepcopy(witness)})
    try:
        native = float(match[1].replace("−", "-"))
    except (ValueError, OverflowError):
        _fail("numerical_model_range", "uncertainty.confidence_level")
    if not math.isfinite(native) or not 0 < native < 100:
        _fail("confidence_level_range", "uncertainty.confidence_level")
    exact = Fraction(match[1].replace("−", "-")) / 100
    if not 0 < exact < 1:
        _fail("confidence_level_range", "uncertainty.confidence_level")
    value = float(exact)
    if not 0 < value < 1:
        _fail("numerical_model_range", "uncertainty.confidence_level")
    return {"witness": witness, "value": value}


_COUNT_SMALL = dict(zip(("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen").split(), range(20)))
_COUNT_TENS = dict(zip("twenty thirty forty fifty sixty seventy eighty ninety".split(), range(20, 100, 10)))
_COUNT_WORDS = frozenset((*_COUNT_SMALL, *_COUNT_TENS, "hundred", "thousand", "million"))
_COUNT_START = r"(?:[+−-]?[0-9]+|" + "|".join(sorted((*_COUNT_SMALL, *_COUNT_TENS), key=len, reverse=True)) + r")\b"
_COUNT_PARTIAL_ERRORS = frozenset(("plain_source_point_required", "lower_bound_source_number_unsupported",
    "approximate_source_number_unsupported", "interval_source_number_unsupported", "postfix_source_bound_unsupported",
    "postfix_source_approximation_unsupported", "composite_source_comparator_unsupported", "negated_source_comparator_unsupported"))


def _cardinal_count(raw):
    """Recognize one finite cardinal grammar, never article/noun meanings."""
    token = raw.lower()
    if not re.fullmatch(r"[a-z]+(?:[\s-]+[a-z]+)*", token):
        return None
    # Only tens-unit pairs admit a hyphen; no preprocessing erases other dashes.
    for left, right in re.findall(r"([a-z]+)-([a-z]+)", token):
        if left not in _COUNT_TENS or _COUNT_SMALL.get(right, 0) not in range(1, 10):
            return None
    if "--" in token or re.search(r"\s-|-[\s]", token):
        return None
    words = token.replace("-", " ").split()
    def below_hundred(group):
        if len(group) == 1:
            return _COUNT_SMALL.get(group[0], _COUNT_TENS.get(group[0]))
        if len(group) == 2 and group[0] in _COUNT_TENS and _COUNT_SMALL.get(group[1], 0) in range(1, 10):
            return _COUNT_TENS[group[0]] + _COUNT_SMALL[group[1]]
        return None
    def group_value(group):
        if len(group) >= 2 and _COUNT_SMALL.get(group[0], 0) in range(1, 10) and group[1] == "hundred":
            rest = group[2:]
            if not rest:
                return 100 * _COUNT_SMALL[group[0]]
            if rest[0] == "and":
                rest = rest[1:]
            remainder = below_hundred(rest)
            return 100 * _COUNT_SMALL[group[0]] + remainder if remainder and remainder < 100 else None
        return below_hundred(group)
    total, position, previous_scale = 0, 0, 1000000000
    for index, word in enumerate(words):
        if word not in ("million", "thousand"):
            continue
        scale = 1000000 if word == "million" else 1000
        group = group_value(words[position:index])
        if scale >= previous_scale or group is None or not 1 <= group <= 999:
            return None
        total += group * scale
        previous_scale, position = scale, index + 1
    rest = words[position:]
    final_and = bool(rest and rest[0] == "and")
    if final_and:
        if not total:
            return None
        rest = rest[1:]
    if rest:
        group = group_value(rest)
        if group is None or total and group == 0 or final_and and not 1 <= group < 100:
            return None
        total += group
    elif not total or final_and:
        return None
    return total if 0 <= total <= 999999999 else None


def _count_scope(prefix, suffix, token):
    """Classify finite count qualification/range syntax in actual source text."""
    lower = r"\b(?:or\s+(?:more|greater|above)|and\s+above)\b"
    upper = r"\b(?:or\s+(?:less|fewer|below)|and\s+below)\b"
    remaining, relations, approximate, qualified = prefix, [], False, False
    while True:
        approx, high, low = _APPROX.search(remaining), _UPPER.search(remaining), _LOWER.search(remaining)
        if approx:
            approximate, qualified = True, True
            remaining = remaining[:approx.start()]
        elif high or low:
            marker = (high or low).group(1).lower()
            marker = re.sub(r"\s+", " ", marker)
            relations.append(("le" if marker in ("<=", "≤", "at most", "no more than") or "equal" in marker else "lt")
                if high else ("ge" if marker in (">=", "≥", "at least", "no less than") or "equal" in marker else "gt"))
            qualified = True
            remaining = remaining[:(high or low).start()]
        else:
            break
    postfix_lower = re.match(r"\s*" + lower, suffix, re.I)
    postfix_upper = re.match(r"\s*" + upper, suffix, re.I)
    if postfix_lower:
        relations.append("ge"); qualified = True
    if postfix_upper:
        relations.append("le"); qualified = True
    if re.match(r"\s*(?:approximately|roughly|around|about|circa|approx\.?)\b", suffix, re.I):
        approximate, qualified = True, True
    uncertain_qualifier = bool(re.search(r"\b(?:(?:no|not|never)(?:\s+(?:significantly|substantially|clearly))?|"
        r"(?:fewer|less|more)\s+than|up\s+to|at\s+(?:minimum|maximum)|under|over|nearly|almost)\s*$", remaining, re.I)
        or not (postfix_lower or postfix_upper) and re.match(r"\s*(?:or|and)\s+(?:no\b|(?:greater|less|fewer|more|above|below)\b|at\s+(?:least|most)\b)", suffix, re.I))
    qualified = qualified or uncertain_qualifier
    range_or_alternatives = bool(
        re.search(r"\b(?:between|from|range|interval|CI|confidence\s+interval)\s*[:=]?\s*[\[(]?\s*$", prefix, re.I)
        or re.search(r"\bbetween\b[^.;!?\n]*\band\s*$", prefix, re.I)
        or re.search(_COUNT_START + r"\s*(?:[–—−-]|\bto|\bor)\s*$", prefix, re.I)
        or re.match(r"\s*(?:[–—−-]|\bto\b|\bor\b)\s*" + _COUNT_START, suffix, re.I)
        or re.search(r"\bbetween\b[^.;!?\n]*$", prefix, re.I) and re.match(r"\s*and\s*" + _COUNT_START, suffix, re.I)
        or re.search(_COUNT_START + r"\s+(?:to|or)\s+" + _COUNT_START, token, re.I)
        or re.search(_COUNT_START + r"\s*[–—−-]\s*" + _COUNT_START, token, re.I) and _cardinal_count(token) is None
        or re.search(r"\bbetween\s+" + _COUNT_START + r"\s+and\s+" + _COUNT_START, token, re.I))
    if range_or_alternatives:
        return "range_or_alternatives", "unresolved", None
    if qualified:
        return "qualified", relations[0] if len(set(relations)) == 1 and not uncertain_qualifier else "point" if not relations and not uncertain_qualifier else "unresolved", approximate
    return "exact", "point", False


def _count_reading(selection, sources):
    """Read a reported numeral; qualifications never become an exact sample n."""
    if selection is None:
        return None
    witness = sources.witness(selection["witness"], "uncertainty.count")
    start, end = selection["number_start"], selection["number_end"]
    _index(start, "uncertainty.count.number_start"); _index(end, "uncertainty.count.number_end")
    if not 0 <= start < end <= len(witness["quote"]):
        _fail("source_number_span_order_invalid", "uncertainty.count")
    token = witness["quote"][start:end]
    prefix, suffix = _field_contexts(sources, witness, start, end)
    status, relation, approximate = _count_scope(prefix, suffix, token)
    before, after = prefix[-1:], suffix[:1]
    stop = after == "." and (len(suffix) == 1 or suffix[1].isspace() or suffix[1] in ")]};:")
    if (before and (before.isalnum() or before in ".eE+−-_‐‑–—")
            or after and (after.isalnum() or after in ".eE+−-_‐‑–—") and not stop):
        _fail("partial_source_count_token", "uncertainty.count")
    if (re.search(r"\b(?:minus|negative|plus|positive)\s*$", prefix, re.I)
            or re.match(r"\s+(?:point\b|(?:and\s+)?(?:a\s+)?(?:half|halves|quarters?|thirds?|fourths?|fifths?|tenths?|hundredths?)\b)", suffix, re.I)):
        _fail("partial_source_count_token", "uncertainty.count")
    preceding = re.search(r"([A-Za-z]+)(?:\s+and)?\s+$", prefix)
    following = re.match(r"\s+([A-Za-z]+)\b", suffix)
    if status != "range_or_alternatives" and ((preceding and preceding[1].lower() in _COUNT_WORDS and preceding[1].lower() != "zero")
            or following and following[1].lower() in _COUNT_WORDS
            or _cardinal_count(token) is not None and re.match(r"\s+and\s+" + _COUNT_START, suffix, re.I)
                and not re.search(r"\bbetween\b[^.;!?\n]*$", prefix, re.I)):
        _fail("partial_source_count_token", "uncertainty.count")
    if (_PHYSICAL_UNIT.match(suffix) or re.match(r"\s*\(?\s*(?:%|percent\b|per\s+cent\b)", suffix, re.I)
            or re.search(r"(?:%|\bpercent|\bper\s+cent)\s*\)?\s*[:=]?\s*$", prefix, re.I)
            or re.search(r"\b(?:retained\s+fraction|fraction(?:al\s+(?:change|decrease|increase))?|relative\s+(?:signal|activity|rate))\s*(?:was|is|of|[:=])?\s*$", prefix, re.I)):
        _fail("source_number_unit_role_mismatch", "uncertainty.count")
    if re.search(r"(?:±|\+\s*/\s*-|\b(?:SD|SEM|standard\s+deviation|standard\s+error)\s*[:=]?)\s*$", prefix, re.I):
        _fail("uncertainty_is_not_count", "uncertainty.count")
    operator = r"(?:[/×⋅·*+^]|\btimes\b|\bx\b)"
    if (re.search(_COUNT_START + r"\s*" + operator + r"\s*$", prefix, re.I)
            or re.match(r"\s*" + operator + r"\s*" + _COUNT_START, suffix, re.I)):
        _fail("source_arithmetic_expression_unsupported", "uncertainty.count")
    if re.fullmatch(_NUMBER, token):
        try:
            _number(selection, sources, "condition")
        except ExperimentalContractError as error:
            if error.code not in _COUNT_PARTIAL_ERRORS:
                raise
    if re.fullmatch(r"[-−]?[0-9]+", token):
        value, notation = int(token.replace("−", "-")), "decimal_digits"
    else:
        value = _cardinal_count(token)
        notation = "english_cardinal" if value is not None else "unsupported"
    reason = None
    if status == "range_or_alternatives":
        value, reason = None, "count_range_or_alternatives"
    elif value is None:
        status, relation, approximate, reason = "unsupported", "unresolved", None, "unsupported_count_literal"
    elif value <= 0:
        status, reason = "not_positive", "positive_count_required"
    elif status == "qualified":
        reason = "exact_count_qualified"
    return {"selector": {**deepcopy(selection), "witness": witness}, "raw_number": token,
        "value": value, "notation": notation, "relation": relation, "approximate": approximate,
        "status": status, "unavailable_reason": reason}


def _uncertainty(selected, parameter_unit, kind, sources):
    meanings = {name: _interpret(selected[name], sources, "uncertainty." + name)
        for name in ("statistic", "unit_relationship", "repetition_basis", "estimate_basis")}
    statistic = meanings["statistic"]["value"]
    magnitude = _number(selected["magnitude"], sources, "spread") if selected["magnitude"] is not None else None
    interval = _interval(selected["interval"], sources)
    confidence = _confidence(selected["confidence_level"], sources)
    if ((statistic == "unreported" and (magnitude is not None or interval is not None or confidence is not None))
            or statistic == "ci" and magnitude is not None
            or statistic != "ci" and (interval is not None or confidence is not None)):
        _fail("source_uncertainty_representation_mismatch", "uncertainty")
    explicit = _unit(selected["unit"], kind, sources)
    relationship = meanings["unit_relationship"]["value"]
    unit = explicit if relationship == "explicit_unit" else parameter_unit if relationship == "same_as_parameter" else None
    if explicit is not None and relationship == "same_as_parameter":
        if (parameter_unit is None or explicit["canonical_unit"] != parameter_unit["canonical_unit"]
                or explicit["multiplier"] != parameter_unit["multiplier"]):
            _fail("source_uncertainty_unit_mismatch", "uncertainty.unit")
    _explicit_unit(magnitude, unit, kind, sources)
    if interval is not None:
        witness = interval["selector"]["witness"]
        _, suffix = _field_contexts(sources, witness, 0, len(witness["quote"]))
        _explicit_unit_after(suffix.lstrip(), unit, kind)
    spread, spread_reason = _converted(magnitude, unit, "uncertainty.magnitude")
    bounds, interval_reason = None, None
    if interval is not None and unit is not None and unit["canonical_unit"] is not None:
        converted = [_converted({"raw_number": value}, unit, "uncertainty.interval") for value in interval["raw_values"]]
        interval_reason = next((reason for _, reason in converted if reason), None)
        if interval_reason is None:
            bounds = [value for value, _ in converted]
            if bounds[0] == bounds[1] and _literal_fraction(interval["raw_values"][0]) != _literal_fraction(interval["raw_values"][1]):
                bounds, interval_reason = None, "source_numeric_range"
    count = _count_reading(selected["count"], sources)
    reason = spread_reason or interval_reason
    if (magnitude is not None or interval is not None) and (unit is None or unit["canonical_unit"] is None):
        reason = "source_uncertainty_unit_unavailable"
    value = {"statistic": statistic, "magnitude": spread, "interval": bounds,
        "confidence_level": confidence["value"] if confidence else None,
        "count": count["value"] if count and count["status"] == "exact" else None,
        "repetition_basis": meanings["repetition_basis"]["value"],
        "estimate_basis": meanings["estimate_basis"]["value"]}
    return {"meanings": meanings, "magnitude": magnitude, "interval": interval,
        "unit": explicit, "effective_unit": deepcopy(unit), "confidence_level": confidence,
        "count": count, "canonical": value, "unavailable_reason": reason}


def _operand(selected, sources, source_origin):
    if selected is None:
        return None, None, ["source_measurement_unreported"]
    parameter = _interpret(selected["parameter_kind"], sources, "parameter_kind")
    kind = parameter["value"]
    subject = {name: sources.witness(w, "subject." + name) if w is not None else None for name, w in selected["subject"].items()}
    context = {name: sources.witness(w, "context." + name) if w is not None else None for name, w in selected["context"].items()}
    physical = sources.witness(selected["measurement_identity"], "measurement_identity") if selected["measurement_identity"] is not None else None
    qualification = _interpret(selected["qualification"], sources, "qualification")
    measurement = selected["measurement"]
    number = _number(measurement["number"], sources, "rate") if measurement else None
    if number is not None:
        ns = number["selector"]
        before, after = _field_contexts(sources, ns["witness"], ns["number_start"], ns["number_end"])
        if (re.search(r"(?:\bn|\bcount|\bnumber\s+of\s+(?:experiments|replicates|measurements|preparations))\s*[:=]\s*$", before, re.I)
                or re.match(r"\s*(?:independent\s+)?(?:experiments|replicates|measurements|preparations)\b", after, re.I)):
            _fail("count_is_not_kinetic_parameter", "parameter.number")
    unit = _unit(measurement["unit"], kind, sources) if measurement else None
    _explicit_unit(number, unit, kind, sources)
    value, conversion_reason = _converted(number, unit, "parameter")
    approximate = bool(number and number["approximate"] or qualification["value"] == "source_qualified_approximate")
    uncertainty = _uncertainty(selected["uncertainty"], unit, kind, sources)
    reasons = []
    if kind not in PARAMETER_UNITS:
        reasons.append("source_parameter_kind_" + kind)
    if number is None:
        reasons.append("source_measurement_unreported")
    elif unit is None:
        reasons.append("source_kinetic_unit_unreported")
    elif unit["unavailable_reason"]:
        reasons.append(unit["unavailable_reason"])
    if conversion_reason:
        reasons.append(conversion_reason)
    if qualification["value"] in ("unknown", "conflicting"):
        reasons.append("source_operand_qualification_" + qualification["value"])
    location = None
    if number is not None:
        ns, w = number["selector"], number["selector"]["witness"]
        location = _locator(w)
        location.update(start=w["start"] + len(w["quote"][:ns["number_start"]].encode()),
                        end=w["start"] + len(w["quote"][:ns["number_end"]].encode()))
    elif parameter["witnesses"]:
        location = _locator(parameter["witnesses"][0])
    canonical = None
    if kind in PARAMETER_UNITS and location is not None:
        unavailable = reasons[0] if reasons else None
        canonical = {"parameter_kind": kind, "unit": unit["canonical_unit"] if unit and value is not None else None,
            "value": value if not reasons else None,
            "status": "conflicting" if qualification["value"] == "conflicting" else "missing" if reasons else "point" if number["relation"] == "point" else "censored",
            "relation": "none" if reasons else "eq" if number["relation"] == "point" else number["relation"],
            "approximate": approximate, "origin": "calculated" if source_origin == "reported" and unit and unit["multiplier"] not in (None, 1) else source_origin,
            "measurement_id": identity("kinetic_source_token" if number else "kinetic_unavailable_record", location),
            "physical_measurement_id": identity("kinetic_physical_observation", _locator(physical)) if physical else None,
            "subject": {name: w["quote"] if w else None for name, w in subject.items()},
            "context": {name: w["quote"] if w else None for name, w in context.items()},
            "uncertainty": deepcopy(uncertainty["canonical"]), "source": location, "unavailable_reason": unavailable}
    retained = {"parameter_kind": parameter, "subject": subject, "context": context,
        "measurement_identity": physical, "number": number, "unit": unit,
        "qualification": qualification, "approximate": approximate, "source_origin": source_origin,
        "canonical_value": value, "uncertainty": uncertainty, "calculation_operand": canonical,
        "unavailable_reasons": reasons}
    return retained, canonical, reasons


def read_kinetic_inputs(selection, *, read_source):
    """Read exact source estimates into045 operands; unknowns remain unknown.

    This is a native literal reader, not an experiment grader. Covariance/model
    extraction and selected runtime storage/typed rendering are separate work.
    """
    try:
        validate_schema(selection, kinetic_arguments_schema())
    except ContractError as error:
        raise ExperimentalContractError("kinetic_selection_schema_invalid", "selection", detail=error.detail) from error
    sources = _Sources(read_source)
    sources.source(selection["source_ref"], "original")
    comparison = {name: _interpret(value, sources, "comparison." + name) for name, value in selection["comparison"].items()}
    source_origin = "synthetic" if selection["source_kind"] == "synthetic_fixture" else "reported"
    inputs = {"version": "a105_kinetic_contrast_inputs_v1", **{name: row["value"] for name, row in comparison.items()}}
    operands, reasons = {}, {}
    for role in ("numerator", "denominator"):
        operands[role], inputs[role], reasons[role] = _operand(selection[role], sources, source_origin)
    from .literature_kinetic_calculations import validate_kinetic_inputs
    inputs = validate_kinetic_inputs(inputs)
    return deepcopy({"version": VERSION, "source_ref": selection["source_ref"], "source_kind": selection["source_kind"],
        "operands": operands, "comparison": comparison, "calculation_inputs": inputs,
        "input_unavailable_reasons": reasons, "source_refs": list(sources.references),
        "implementation_dependencies": DEPENDENCIES})


__all__ = ["VERSION", "SELECTION_VERSION", "SOURCE_KINDS", "PARAMETER_UNITS",
           "SUBJECT_FIELDS", "CONTEXT_FIELDS", "QUALIFICATIONS", "COMPARISON_VALUES",
           "DEPENDENCIES", "COUNT_STATUSES", "COUNT_REASONS", "COUNT_NOTATIONS", "COUNT_RELATIONS",
           "kinetic_arguments_schema", "read_kinetic_inputs"]
