"""Witnessed native operands for the existing source-preparation rate sheet.

Selections assign scientific meanings; exact quotes establish custody only.
This reader performs no model call, acquisition, scoring or state mutation.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import html
import math
import re

from .domain import REF, obj
from .literature_assay_inputs import _Sources, _witness_schema, _nullable, _keys, _index
from .literature_experimental_contracts import (
    ExperimentalContractError, RATE_UNITS, SAMPLING_BASES, UNCERTAINTY_KINDS,
)
from .literature_partner_source_fields import (
    number_selector_schema, _NUMBER, _ALL_TAGS, _PM,
    _unit_continuation, _relation, _between_numeric_scope,
    _BETWEEN_AND, _BETWEEN_FIRST_PREFIX, _BETWEEN_FIRST_SUFFIX,
)
from .literature_partner_defined_units import (
    defined_rate_unit_schema, _definition_scale, _definition_selection,
    _DEFINITION_KEYS, _source_witness, _finite_float,
)


VERSION = "a105_rate_extraction_v2"
SOURCE_KINDS = ("primary_source", "retained_extraction", "synthetic_fixture")
ROLES = ("reference", "test")
MEANINGS = ("subject", "construct", "preparation", "experiment", "label",
            "condition", "endpoint", "normalization")
RELATIONS = ("subject", "endpoint", "normalization")
NATIVE_BINDINGS = tuple(role + "_" + field + "_ref" for role in ROLES
                        for field in ("subject", "construct", "preparation"))
NATIVE_REASONS = ("source_rate_unit_unreported", "unsupported_source_rate_unit",
    "source_defined_unit_definition_required", "source_spread_unit_unavailable",
    "source_endpoint_relationship_unknown", "source_endpoint_relationship_different",
    "source_normalization_relationship_unknown", "source_normalization_relationship_different",
    "incompatible_rate_dimensions", "reused_source_observation")
_BASE = {"amount_rate": "umol/min", "concentration_rate": "uM/min",
         "turnover_rate": "per_min", "specific_amount_rate": "umol/min/mg"}
_KEYS = ("input_mode", "source_ref", "source_kind", "experiment", "arms",
         "comparison", "dependence", "observation_model")
_UPPER = re.compile(r"(<=?|≤|\b(?:less\s+than(?:\s+or\s+equal\s+to)?|below|at\s+most|no\s+more\s+than))\s*$", re.I)
_LOWER = re.compile(r"(>=?|≥|\b(?:greater\s+than(?:\s+or\s+equal\s+to)?|more\s+than|above|at\s+least|no\s+less\s+than))\s*$", re.I)
_APPROX = re.compile(r"(?:[~≈≃≅∼]|\b(?:approximately|roughly|around|about|circa|approx\.?))\s*$", re.I)
_PRINTED_UNIT = re.compile(r"(?:[pnmuµμ]?mol\s*(?:/\s*(?:min|s)(?:\s*/\s*mg)?|\s*(?:min|s)\s*\^?\s*[-−⁻][1¹](?:\s*mg\s*\^?\s*[-−⁻][1¹])?)|[nmuµμ]M\s*/\s*min|U\s*/\s*mg|per_(?:min|s)|(?:min|s)\s*\^?\s*[-−⁻][1¹])")
_FIELD_BOUNDARY = re.compile(r"</?(?:td|th|tr|table|thead|tbody|tfoot|p|div|section|sec|title|caption|list|list-item|li|hr|disp-formula)(?=[\s/>])[^<>]*>", re.I)
_PHYSICAL_UNIT = re.compile(r"\s*\(?\s*(?:[pnmuµμ]?mol|[pnmuµμ]?M|[kmunpµμ]?g|[munpµμ]?L|s|min|h|sec(?:onds?)?|hours?|minutes?|[kmunpµμ]?m|U)(?![A-Za-z_µμ])")


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def rate_source_population_schema():
    witness = _witness_schema()
    number = number_selector_schema()
    unit = {"anyOf": [deepcopy(witness), defined_rate_unit_schema(), {"type": "null"}]}
    def interpreted(values):
        return obj({"value": {"enum": list(values)},
            "witnesses": {"type": "array", "items": deepcopy(witness)}})
    uncertainty = obj({"kind": {"enum": list(UNCERTAINTY_KINDS)},
        "magnitude": _nullable(deepcopy(number)), "unit": deepcopy(unit),
        "kind_witnesses": {"type": "array", "items": deepcopy(witness)},
        "count": _nullable(deepcopy(number)), "sampling_basis": interpreted(SAMPLING_BASES)})
    arm = obj({**{name: _nullable(deepcopy(witness)) for name in MEANINGS},
        "measurement_identity": _nullable(deepcopy(witness)),
        "rate": _nullable(obj({"number": deepcopy(number), "unit": deepcopy(unit)})),
        "uncertainty": uncertainty})
    comparison = obj({**{name + "_relation": interpreted(("same", "different", "unknown"))
        for name in RELATIONS}, "intended_change": _nullable(deepcopy(witness))})
    return obj({"input_mode": {"const": "native_source_spans"}, "source_ref": deepcopy(REF),
        "source_kind": {"enum": list(SOURCE_KINDS)}, "experiment": _nullable(deepcopy(witness)),
        "arms": obj({role: _nullable(deepcopy(arm)) for role in ROLES}),
        "comparison": comparison, "dependence": interpreted(("unknown", "independent")),
        "observation_model": interpreted(("none", "independent_normal_groups"))})


def _interpret(value, allowed, sources, field):
    _keys(value, ("value", "witnesses"), field)
    if value["value"] not in allowed or not isinstance(value["witnesses"], list):
        _fail("unsupported_native_interpretation", field)
    witnesses = [sources.witness(w, field + ".witnesses") for w in value["witnesses"]]
    if value["value"] not in ("unknown", "none", "unspecified") and not witnesses:
        _fail("interpretation_witness_required", field)
    return {"value": value["value"], "witnesses": witnesses}


def _field_contexts(sources, witness, start, end):
    """Read adjacent source text within its actual HTML/JATS field.

    Structural tags bound fields; inline tags expose real lexical neighbours.
    Witness bytes and absolute positions are never rewritten.
    """
    raw = sources.source(witness["source_ref"], witness["representation"])["content"]
    quote = witness["quote"]
    first = witness["start"] + len(quote[:start].encode("utf-8"))
    last = witness["start"] + len(quote[:end].encode("utf-8"))
    prefix = raw[:first].decode("utf-8", errors="ignore")
    suffix = raw[last:].decode("utf-8", errors="ignore")
    boundaries = list(_FIELD_BOUNDARY.finditer(prefix))
    if boundaries:
        prefix = prefix[boundaries[-1].end():]
    boundary = _FIELD_BOUNDARY.search(suffix)
    if boundary:
        suffix = suffix[:boundary.start()]
    return tuple(html.unescape(_ALL_TAGS.sub("", value)) for value in (prefix, suffix))


def _number(selection, sources, role, *, count_unit_guard=True):
    """Keep lower limits and approximations without accepting clipped numbers."""
    _keys(selection, ("witness", "number_start", "number_end"), "number_selector")
    if role not in ("rate", "spread", "condition"):
        _fail("unsupported_source_number_role", "role")
    witness = sources.witness(selection["witness"], "number_selector.witness")
    start, end = selection["number_start"], selection["number_end"]
    _index(start, "number_start"); _index(end, "number_end")
    if not 0 <= start < end <= len(witness["quote"]):
        _fail("source_number_span_order_invalid", "number_selector")
    token = witness["quote"][start:end]
    if not _NUMBER.fullmatch(token):
        _fail("literal_source_number_required", "number_selector")
    prefix, suffix = _field_contexts(sources, witness, start, end)
    # A selected literal is not the value of a surrounding arithmetic expression.
    # A unit denominator such as /min has no adjacent numeric operand.
    operator = r"(?:[/×⋅·*+^]|\btimes\b|\bx\b)"
    if (re.search(r"\d\s*" + operator + r"\s*$", prefix, re.I)
            or re.match(r"\s*" + operator + r"\s*[+−-]?(?:\d|\.\d)", suffix, re.I)):
        _fail("source_arithmetic_expression_unsupported", "number_selector")
    # Interpret recognized trailing qualifiers before accepting the shared
    # parser's point fast path. Their order can be "about >" or "> about".
    remaining, relations, approximate = prefix, [], False
    while True:
        approx, upper, lower = _APPROX.search(remaining), _UPPER.search(remaining), _LOWER.search(remaining)
        if approx:
            approximate = True
            remaining = remaining[:approx.start()]
        elif upper:
            marker = re.sub(r"\s+", " ", upper.group(1).lower())
            relations.append("le" if marker in ("<=", "≤", "at most", "no more than") or "equal" in marker else "lt")
            remaining = remaining[:upper.start()]
        elif lower:
            marker = re.sub(r"\s+", " ", lower.group(1).lower())
            relations.append("ge" if marker in (">=", "≥", "at least", "no less than") or "equal" in marker else "gt")
            remaining = remaining[:lower.start()]
        else:
            break
    relative_prefix = re.search(r"\b(?:retained\s+fraction|fraction(?:al\s+(?:change|decrease|increase))?|relative\s+(?:signal|activity|rate))\s*(?:was|is|of|[:=])?\s*$", remaining, re.I)
    relative = (relative_prefix or re.match(r"\s*\(?\s*(?:%|percent\b|per\s+cent\b)", suffix, re.I)
        or re.search(r"(?:%|\bpercent|\bper\s+cent)\s*\)?\s*[:=]?\s*$", remaining, re.I))
    if (role in ("rate", "condition") and relative or role == "spread" and relative_prefix
            or role == "condition" and count_unit_guard and _PHYSICAL_UNIT.match(suffix)):
        _fail("source_number_unit_role_mismatch", "number_selector")
    if re.match(r"\s*(?:roughly|around|about)\b", suffix, re.I):
        _fail("postfix_source_approximation_unsupported", "number_selector")
    if remaining != prefix and role != "rate":
        _fail("plain_source_point_required", "number_selector")
    if len(set(relations)) > 1:
        _fail("composite_source_comparator_unsupported", "number_selector")
    if re.search(r"\bnot\s*(?:(?:significantly|substantially|clearly)\s*)?$", remaining, re.I):
        _fail("negated_source_comparator_unsupported", "number_selector")
    # Removing only recognized qualifiers exposes rather than erases a
    # plus/minus marker, interval, relative spread or postfix comparator.
    relation = _relation(remaining, suffix, role=role)
    # Preserve every shared scalar guard using these field-aware contexts.
    before, after = prefix[-1:], suffix[:1]
    stop = after == "." and (len(suffix) == 1 or suffix[1].isspace() or suffix[1] in ")]};:")
    pm_spread = role == "spread" and _PM.search(prefix) is not None
    if (before and (before.isalnum() or before in ".eE+−-_") and not pm_spread
            or after and (after in ".eE+−-" or after.isdigit()) and not stop):
        _fail("partial_source_numeric_token", "number_selector")
    if re.search(r"\d,\s*$", prefix) or re.match(r",\s*\d", suffix):
        _fail("comma_source_number_unsupported", "number_selector")
    if (re.search(r"\b(?:between|from|range|interval|CI|confidence\s+interval)\s*[:=]?\s*[\[(]?\s*$", prefix, re.I)
            or ((_BETWEEN_AND.search(prefix) or (_BETWEEN_FIRST_PREFIX.search(prefix)
                    and _BETWEEN_FIRST_SUFFIX.match(suffix)))
                and _between_numeric_scope(prefix, suffix) != "non_numeric_coordination")
            or re.search(r"\d\s*(?:[–—−-]|\bto)\s*$", prefix)
            or re.match(r"\s*(?:[–—−-]|\bto\b)\s*[+−-]?(?:\d|\.\d)", suffix)):
        _fail("interval_source_number_unsupported", "number_selector")
    if re.match(r"\s*\.?\s*(?:[×⋅·*]|\bx\b)\s*10(?:\b|\^)", suffix):
        _fail("nonliteral_scientific_expression", "number_selector")
    relation = relations[0] if relations else relation
    try:
        value = float(token.replace("−", "-"))
    except (ValueError, OverflowError):
        _fail("numerical_model_range", "number_selector")
    if not math.isfinite(value) or value == 0 and any(c in "123456789" for c in token.lower().split("e", 1)[0]):
        _fail("numerical_model_range", "number_selector")
    if role == "spread" and value < 0:
        _fail("nonnegative_source_number_required", "number_selector")
    return {"selector": {**deepcopy(selection), "witness": witness},
        "raw_number": token, "value": value, "relation": relation, "approximate": approximate}


def _defined_unit(selection, sources, endpoint):
    """The existing definition semantics with native field-aware boundaries."""
    _keys(selection, ("kind", "witness", "definition"), "defined_unit")
    if selection["kind"] != "source_defined_rate_unit":
        _fail("defined_unit_kind_required", "defined_unit.kind")
    _keys(selection["definition"], _DEFINITION_KEYS, "defined_unit.definition")
    unit = sources.witness(selection["witness"], "defined_unit.witness")
    prefix, suffix = _field_contexts(sources, unit, 0, len(unit["quote"]))
    before = prefix[-1:]
    if ((before and (before.isalpha() or before in "_µμ/⁻¹^")) or _unit_continuation(suffix)
            or re.match(r"\s+per\b", suffix)):
        _fail("defined_unit_partial_rate_unit", "defined_unit.witness")
    if re.sub(r"\s+", "", unit["quote"]) != "U/mg":
        _fail("defined_unit_rate_unit_unsupported", "defined_unit.witness")
    definition = {name: sources.witness(value, "defined_unit.definition." + name)
        for name, value in selection["definition"].items() if name != "amount"}
    amount = _number(selection["definition"]["amount"], sources, "condition", count_unit_guard=False)
    definition["amount"] = {key: value for key, value in amount.items() if key != "approximate"}
    if endpoint is None:
        _fail("defined_unit_endpoint_required", "defined_unit.definition.endpoint")
    if _source_witness(endpoint, sources, "defined_unit.endpoint") != definition["endpoint"]:
        _fail("defined_unit_endpoint_mismatch", "defined_unit.definition.endpoint")
    bridge = definition["bridge"]
    bp, bs = _field_contexts(sources, bridge, 0, len(bridge["quote"]))
    if bp[-1:] and (bp[-1:].isalnum() or bp[-1:] == "_"):
        _fail("defined_unit_bridge_boundary_required", "defined_unit.definition.bridge")
    if not bridge["quote"].rstrip().endswith(".") and bs.strip() and not re.match(r"\s*[.;]", bs):
        _fail("defined_unit_bridge_boundary_required", "defined_unit.definition.bridge")
    scale = _definition_scale(definition)
    return {"witness": unit, "raw_unit": unit["quote"], "canonical_unit": "pmol/min/mg",
        "multiplier": _finite_float(scale, "defined_unit.multiplier"), "definition": deepcopy(definition)}


def _plain_unit(raw):
    text = re.sub(r"\s+", "", html.unescape(_ALL_TAGS.sub("", raw)))
    text = text.replace("µ", "u").replace("μ", "u")
    text = text.translate(str.maketrans({"−": "-", "⁻": "-", "¹": "1"})).replace("^", "")
    aliases = {name: name for name in RATE_UNITS}
    for amount in ("umol", "nmol", "mmol"):
        aliases[amount + "min-1"] = amount + "/min"
    for amount in ("umol", "nmol"):
        aliases[amount + "min-1mg-1"] = amount + "/min/mg"
    for amount in ("uM", "nM"):
        aliases[amount + "min-1"] = amount + "/min"
    for time in ("min", "s"):
        for spelling in (time + "-1", "1/" + time, "per" + time):
            aliases[spelling] = "per_" + time
    if text not in aliases:
        return None
    dimension, scale = RATE_UNITS[aliases[text]]
    return _BASE[dimension], Fraction(str(scale))


def _unit(selection, sources, endpoint):
    if selection is None:
        return None
    if isinstance(selection, dict) and selection.get("kind") == "source_defined_rate_unit":
        defined = _defined_unit(selection, sources, endpoint)
        scale = _definition_scale(defined["definition"]) / 1000000
        unit, witness, reason = "umol/min/mg", defined["witness"], None
    else:
        defined = None
        witness = sources.witness(selection, "unit_witness")
        prefix, suffix = _field_contexts(sources, witness, 0, len(witness["quote"]))
        before = prefix[-1:]
        if ((before and (before.isalpha() or before in "_µμ/⁻¹^"))
                or _unit_continuation(suffix) or re.match(r"\s+per\b", suffix)):
            _fail("partial_source_rate_unit", "unit_witness")
        parsed = _plain_unit(witness["quote"])
        if parsed is None:
            unit, scale = None, None
            reason = ("source_defined_unit_definition_required" if re.fullmatch(r"\s*U\s*/\s*mg\s*", witness["quote"])
                      else "unsupported_source_rate_unit")
        else:
            unit, scale = parsed
            reason = None
    multiplier = _finite_fraction(scale, "unit") if scale is not None else None
    return {"witness": witness, "raw_unit": witness["quote"], "canonical_unit": unit,
        "multiplier": multiplier, "source_defined_unit": defined, "unavailable_reason": reason}


def _finite_fraction(value, field):
    try:
        converted = float(value)
    except (ValueError, OverflowError):
        _fail("numerical_model_range", field)
    if not math.isfinite(converted) or converted == 0 and value != 0:
        _fail("numerical_model_range", field)
    return converted


def _scale(unit):
    if unit["source_defined_unit"] is not None:
        return _definition_scale(unit["source_defined_unit"]["definition"]) / 1000000
    parsed = _plain_unit(unit["raw_unit"])
    if parsed is None:
        _fail("unsupported_source_rate_unit", "unit")
    return parsed[1]


def _converted(number, unit):
    if number is None or unit is None or unit["canonical_unit"] is None:
        return None
    return _finite_fraction(Fraction(number["raw_number"].replace("−", "-")) * _scale(unit), "number")


def _check_explicit_unit(number, selected, sources):
    if number is None or selected is None or selected["canonical_unit"] is None:
        return
    ns = number["selector"]
    _, suffix = _field_contexts(sources, ns["witness"], ns["number_start"], ns["number_end"])
    visible = html.unescape(_ALL_TAGS.sub("", suffix)).lstrip()
    match = _PRINTED_UNIT.match(visible)
    if match is None:
        return
    token = match.group()
    if _unit_continuation(visible[match.end():]) or re.match(r"\s+per\b", visible[match.end():]):
        _fail("partial_source_rate_unit", "number")
    if re.fullmatch(r"U\s*/\s*mg", token):
        if selected["source_defined_unit"] is None:
            _fail("source_defined_unit_definition_required", "number")
    elif _plain_unit(token) != (selected["canonical_unit"], _scale(selected)):
        _fail("source_spread_unit_mismatch", "number")


def read_rate_source_inputs(arguments, *, read_source):
    """Read exactly selected source facts, retaining unknown meanings and units."""
    _keys(arguments, _KEYS, "arguments")
    if arguments["input_mode"] != "native_source_spans" or arguments["source_kind"] not in SOURCE_KINDS:
        _fail("unsupported_native_rate_input", "arguments")
    sources = _Sources(read_source)
    root = sources.source(arguments["source_ref"], "original")
    def witness(value, field):
        return None if value is None else sources.witness(value, field)
    experiment = witness(arguments["experiment"], "experiment")
    _keys(arguments["comparison"], tuple(name + "_relation" for name in RELATIONS) + ("intended_change",), "comparison")
    comparison = {name + "_relation": _interpret(arguments["comparison"][name + "_relation"],
        ("same", "different", "unknown"), sources, "comparison." + name) for name in RELATIONS}
    comparison["intended_change"] = witness(arguments["comparison"]["intended_change"], "intended_change")
    model = {"dependence": _interpret(arguments["dependence"], ("unknown", "independent"), sources, "dependence"),
        "observation_model": _interpret(arguments["observation_model"],
            ("none", "independent_normal_groups"), sources, "observation_model")}
    _keys(arguments["arms"], ROLES, "arms")
    rows = []
    for role in ROLES:
        selected = arguments["arms"][role]
        if selected is None:
            continue
        _keys(selected, (*MEANINGS, "measurement_identity", "rate", "uncertainty"), "arms." + role)
        meanings = {name: witness(selected[name], role + "." + name) for name in MEANINGS}
        physical = witness(selected["measurement_identity"], role + ".measurement_identity")
        rate = selected["rate"]
        if rate is not None:
            _keys(rate, ("number", "unit"), role + ".rate")
        number = _number(rate["number"], sources, "rate") if rate else None
        unit = _unit(rate["unit"], sources, meanings["endpoint"]) if rate else None
        _check_explicit_unit(number, unit, sources)
        value = _converted(number, unit)
        unc = selected["uncertainty"]
        _keys(unc, ("kind", "magnitude", "unit", "kind_witnesses", "count", "sampling_basis"), role + ".uncertainty")
        if unc["kind"] not in UNCERTAINTY_KINDS or not isinstance(unc["kind_witnesses"], list):
            _fail("unsupported_uncertainty_kind", role + ".uncertainty")
        kinds = [sources.witness(w, role + ".uncertainty.kind_witnesses") for w in unc["kind_witnesses"]]
        if unc["kind"] in ("sd", "sem") and not kinds:
            _fail("interpretation_witness_required", role + ".uncertainty.kind")
        magnitude = _number(unc["magnitude"], sources, "spread") if unc["magnitude"] is not None else None
        if (unc["kind"] == "unreported") != (magnitude is None):
            _fail("uncertainty_magnitude_kind_mismatch", role + ".uncertainty")
        spread_unit = _unit(unc["unit"], sources, meanings["endpoint"]) if unc["unit"] is not None else unit
        _check_explicit_unit(magnitude, spread_unit, sources)
        spread = _converted(magnitude, spread_unit)
        if magnitude is not None and unit and spread_unit and unit["canonical_unit"] and spread_unit["canonical_unit"]:
            if unit["canonical_unit"] != spread_unit["canonical_unit"]:
                _fail("incompatible_rate_dimensions", role + ".uncertainty.unit")
        count = _number(unc["count"], sources, "condition") if unc["count"] is not None else None
        if count is not None and not re.fullmatch(r"[0-9]+", count["raw_number"]):
            _fail("positive_integer_count_required", role + ".uncertainty.count")
        count_value = int(count["raw_number"]) if count else None
        if count_value is not None and count_value < 1:
            _fail("positive_integer_count_required", role + ".uncertainty.count")
        sampling = _interpret(unc["sampling_basis"], SAMPLING_BASES, sources, role + ".sampling_basis")
        nw = number["selector"]["witness"] if number else None
        location = None if nw is None else {key: nw[key] for key in ("source_ref", "artifact_ref", "representation")}
        if location is not None:
            ns = number["selector"]
            location.update(start=nw["start"] + len(nw["quote"][:ns["number_start"]].encode()),
                end=nw["start"] + len(nw["quote"][:ns["number_end"]].encode()))
        status = "unavailable" if value is None else "observed" if number["relation"] == "point" else "censored"
        row = {"arm": role, **{name: meanings[name]["quote"] if meanings[name] else None
            for name in ("condition", "endpoint", "normalization")},
            "value": value, "unit": unit["canonical_unit"] if unit else None,
            "status": status, "bound": number["relation"] if status == "censored" else "none",
            "approximate": number["approximate"] if number else False,
            "origin": "synthetic" if arguments["source_kind"] == "synthetic_fixture" else "reported",
            "uncertainty": {"kind": unc["kind"], "magnitude": spread, "count": count_value,
                "sampling_basis": sampling["value"], "unavailable_reason":
                    "source_spread_unit_unavailable" if magnitude is not None and spread is None else None},
            "source": {"source_ref": nw["source_ref"] if nw else arguments["source_ref"],
                "artifact_ref": nw["artifact_ref"] if nw else root["artifact_ref"],
                "representation": "native_source_spans", "location": location,
                "number": number, "unit": unit, "meanings": meanings,
                "measurement_identity": physical, "uncertainty": {
                    "magnitude": magnitude, "unit": spread_unit, "count": count,
                    "kind_witnesses": kinds, "sampling_witnesses": sampling["witnesses"]}}}
        rows.append(row)
    shared = comparison["subject_relation"]["value"] == "same"
    subject = next((row["source"]["meanings"]["subject"]["quote"] for row in rows
                    if row["source"]["meanings"]["subject"]), None) if shared else None
    return {"version": VERSION, "subject": subject, "experiment": experiment["quote"] if experiment else None,
        "rows": rows, "native_context": {"source_ref": arguments["source_ref"],
            "source_kind": arguments["source_kind"], "experiment": experiment,
            "comparison": comparison, "model": model, "source_refs": list(sources.references)}}


def native_pair_reason(extraction):
    comparison = extraction["native_context"]["comparison"]
    for field in ("endpoint", "normalization"):
        value = comparison[field + "_relation"]["value"]
        if value != "same":
            return "source_" + field + "_relationship_" + value
    rows = extraction["rows"]
    if len(rows) == 2:
        first, second = (row["source"] for row in rows)
        def byte_identity(witness):
            return None if witness is None else tuple(witness[k] for k in (
                "source_ref", "artifact_ref", "start", "end"))
        if first["location"] is not None and byte_identity(first["location"]) == byte_identity(second["location"]):
            return "reused_source_observation"
        if first["measurement_identity"] is not None and byte_identity(first["measurement_identity"]) == byte_identity(second["measurement_identity"]):
            return "reused_source_observation"
    return None


def _saved_witness(value, field):
    _keys(value, ("source_ref", "artifact_ref", "representation", "start", "end", "quote"), field)
    if (any(not isinstance(value[k], str) or not value[k] for k in ("source_ref", "artifact_ref", "quote"))
            or value["representation"] not in ("original", "text")
            or type(value["start"]) is not int or type(value["end"]) is not int
            or not 0 <= value["start"] < value["end"]
            or value["end"] - value["start"] != len(value["quote"].encode())):
        _fail("native_witness_record_mismatch", field)


def _saved_number(value, field):
    _keys(value, ("selector", "raw_number", "value", "relation", "approximate"), field)
    selection = value["selector"]
    _keys(selection, ("witness", "number_start", "number_end"), field + ".selector")
    _saved_witness(selection["witness"], field + ".witness")
    start, end = selection["number_start"], selection["number_end"]
    if (type(start) is not int or type(end) is not int
            or not 0 <= start < end <= len(selection["witness"]["quote"])
            or selection["witness"]["quote"][start:end] != value["raw_number"]
            or not isinstance(value["raw_number"], str) or not _NUMBER.fullmatch(value["raw_number"])
            or value["relation"] not in ("point", "lt", "le", "gt", "ge")
            or type(value["approximate"]) is not bool
            or type(value["value"]) not in (int, float)
            or not math.isfinite(value["value"])
            or float(value["raw_number"].replace("−", "-")) != value["value"]):
        _fail("native_number_record_mismatch", field)


def _saved_unit(value, field):
    _keys(value, ("witness", "raw_unit", "canonical_unit", "multiplier",
                  "source_defined_unit", "unavailable_reason"), field)
    _saved_witness(value["witness"], field + ".witness")
    if value["raw_unit"] != value["witness"]["quote"]:
        _fail("native_unit_record_mismatch", field)
    defined = value["source_defined_unit"]
    if defined is not None:
        _keys(defined, ("witness", "raw_unit", "canonical_unit", "multiplier", "definition"), field)
        scale = _definition_scale(defined["definition"])
        if (defined["witness"] != value["witness"] or defined["raw_unit"] != value["raw_unit"]
                or defined["canonical_unit"] != "pmol/min/mg"
                or defined["multiplier"] != _finite_fraction(scale, field)
                or value["canonical_unit"] != "umol/min/mg"
                or value["multiplier"] != _finite_fraction(scale / 1000000, field)
                or value["unavailable_reason"] is not None):
            _fail("native_unit_record_mismatch", field)
    else:
        actual = _plain_unit(value["raw_unit"])
        expected_reason = ("source_defined_unit_definition_required" if re.fullmatch(r"\s*U\s*/\s*mg\s*", value["raw_unit"])
                           else "unsupported_source_rate_unit")
        if actual is None:
            if value["canonical_unit"] is not None or value["multiplier"] is not None or value["unavailable_reason"] != expected_reason:
                _fail("native_unit_record_mismatch", field)
        elif (value["canonical_unit"], value["multiplier"], value["unavailable_reason"]) != (actual[0], _finite_fraction(actual[1], field), None):
            _fail("native_unit_record_mismatch", field)


def validate_native_extraction(value):
    """Validate saved operand relationships without acquiring source bytes."""
    _keys(value, ("version", "subject", "experiment", "rows", "native_context"), "extraction")
    if value["version"] != VERSION or not isinstance(value["rows"], list):
        _fail("unsupported_extraction_version", "version")
    context = value["native_context"]
    _keys(context, ("source_ref", "source_kind", "experiment", "comparison", "model", "source_refs"), "native_context")
    if context["source_kind"] not in SOURCE_KINDS:
        _fail("unknown_source_kind", "native_context.source_kind")
    if (not isinstance(context["source_refs"], list) or not context["source_refs"]
            or any(not isinstance(ref, str) or not ref for ref in context["source_refs"])
            or len(context["source_refs"]) != len(set(context["source_refs"]))
            or context["source_ref"] not in context["source_refs"]):
        _fail("native_source_roster_invalid", "native_context.source_refs")
    comparison = context["comparison"]
    _keys(comparison, tuple(name + "_relation" for name in RELATIONS) + ("intended_change",), "comparison")
    def interpretation(item, allowed, field):
        _keys(item, ("value", "witnesses"), field)
        if item["value"] not in allowed or not isinstance(item["witnesses"], list):
            _fail("unsupported_native_interpretation", field)
        for witness in item["witnesses"]:
            _saved_witness(witness, field)
        if item["value"] not in ("unknown", "none", "unspecified") and not item["witnesses"]:
            _fail("interpretation_witness_required", field)
    for name in RELATIONS:
        interpretation(comparison[name + "_relation"], ("same", "different", "unknown"), "comparison." + name)
    if comparison["intended_change"] is not None:
        _saved_witness(comparison["intended_change"], "intended_change")
    _keys(context["model"], ("dependence", "observation_model"), "model")
    interpretation(context["model"]["dependence"], ("unknown", "independent"), "dependence")
    interpretation(context["model"]["observation_model"], ("none", "independent_normal_groups"), "observation_model")
    if context["experiment"] is not None:
        _saved_witness(context["experiment"], "experiment")
    if value["experiment"] != (context["experiment"]["quote"] if context["experiment"] else None):
        _fail("native_meaning_record_mismatch", "experiment")
    seen_roles = set()
    for row in value["rows"]:
        _keys(row, ("arm", "condition", "endpoint", "normalization", "value", "unit", "status",
                   "bound", "approximate", "uncertainty", "origin", "source"), "row")
        if row["arm"] not in ROLES or row["origin"] not in ("reported", "synthetic"):
            _fail("native_row_role_or_origin_invalid", "row")
        if row["arm"] in seen_roles:
            _fail("native_duplicate_arm", "row.arm")
        seen_roles.add(row["arm"])
        if context["source_kind"] == "synthetic_fixture" and row["origin"] != "synthetic":
            _fail("synthetic_origin_required", "row.origin")
        source = row["source"]
        _keys(source, ("source_ref", "artifact_ref", "representation", "location", "number", "unit",
            "meanings", "measurement_identity", "uncertainty"), "row.source")
        if source["representation"] != "native_source_spans":
            _fail("unknown_source_representation", "row.source.representation")
        _keys(source["meanings"], MEANINGS, "row.source.meanings")
        for name, witness in source["meanings"].items():
            if witness is not None:
                _saved_witness(witness, "meanings." + name)
        if source["measurement_identity"] is not None:
            _saved_witness(source["measurement_identity"], "measurement_identity")
        for name in ("condition", "endpoint", "normalization"):
            if row[name] != (source["meanings"][name]["quote"] if source["meanings"][name] else None):
                _fail("native_meaning_record_mismatch", name)
        number, unit = source["number"], source["unit"]
        if number is not None:
            _saved_number(number, "number")
            selector, witness = number["selector"], number["selector"]["witness"]
            location = {k: witness[k] for k in ("source_ref", "artifact_ref", "representation")}
            location.update(start=witness["start"] + len(witness["quote"][:selector["number_start"]].encode()),
                end=witness["start"] + len(witness["quote"][:selector["number_end"]].encode()))
            if source["location"] != location or any(source[k] != witness[k] for k in ("source_ref", "artifact_ref")):
                _fail("native_number_location_mismatch", "location")
        elif source["location"] is not None:
            _fail("native_number_location_mismatch", "location")
        if unit is not None:
            _saved_unit(unit, "unit")
        expected = _converted(number, unit)
        status = "unavailable" if expected is None else "observed" if number["relation"] == "point" else "censored"
        if (row["value"] is not None and type(row["value"]) not in (int, float)
                or type(row["approximate"]) is not bool
                or row["value"] != expected or row["unit"] != (unit["canonical_unit"] if unit else None)
                or row["status"] != status
                or row["bound"] != (number["relation"] if status == "censored" else "none")
                or row["approximate"] != (number["approximate"] if number else False)):
            _fail("native_rate_record_mismatch", "row")
        raw = source["uncertainty"]
        _keys(raw, ("magnitude", "unit", "count", "kind_witnesses", "sampling_witnesses"), "source.uncertainty")
        for name in ("magnitude", "count"):
            if raw[name] is not None:
                _saved_number(raw[name], "uncertainty." + name)
                if raw[name]["relation"] != "point" or raw[name]["approximate"]:
                    _fail("plain_source_point_required", "uncertainty." + name)
        if raw["unit"] is not None:
            _saved_unit(raw["unit"], "uncertainty.unit")
        for name in ("kind_witnesses", "sampling_witnesses"):
            if not isinstance(raw[name], list):
                _fail("witness_list_required", name)
            for witness in raw[name]:
                _saved_witness(witness, name)
        unc = row["uncertainty"]
        _keys(unc, ("kind", "magnitude", "count", "sampling_basis", "unavailable_reason"), "uncertainty")
        spread = _converted(raw["magnitude"], raw["unit"])
        expected_count = int(raw["count"]["raw_number"]) if raw["count"] else None
        if (unc["kind"] not in UNCERTAINTY_KINDS or unc["sampling_basis"] not in SAMPLING_BASES
                or unc["magnitude"] is not None and type(unc["magnitude"]) not in (int, float)
                or unc["count"] is not None and type(unc["count"]) is not int
                or unc["magnitude"] != spread or spread is not None and spread < 0
                or unc["count"] != expected_count or expected_count is not None and expected_count < 1
                or (unc["kind"] == "unreported") != (raw["magnitude"] is None)
                or unc["kind"] in ("sd", "sem") and not raw["kind_witnesses"]
                or unc["unavailable_reason"] != ("source_spread_unit_unavailable" if raw["magnitude"] is not None and spread is None else None)):
            _fail("native_uncertainty_record_mismatch", "uncertainty")
    expected_subject = next((row["source"]["meanings"]["subject"]["quote"] for row in value["rows"]
                             if row["source"]["meanings"]["subject"]), None) if comparison["subject_relation"]["value"] == "same" else None
    if value["subject"] != expected_subject:
        _fail("native_meaning_record_mismatch", "subject")
    return deepcopy(value)


def validate_native_selection(arguments, extraction):
    """Compare saved enriched operands to their original, unmodified selection."""
    _keys(arguments, _KEYS, "arguments")
    context = extraction["native_context"]
    def selected_witness(w):
        return None if w is None else {k: w[k] for k in ("source_ref", "representation", "start", "end", "quote")}
    def selected_number(n):
        return None if n is None else {**n["selector"], "witness": selected_witness(n["selector"]["witness"])}
    def selected_unit(u):
        return (None if u is None else _definition_selection(u["source_defined_unit"])
                if u["source_defined_unit"] is not None else selected_witness(u["witness"]))
    def same(actual, expected, field):
        if actual != expected:
            _fail("native_saved_selection_mismatch", field)
    same(arguments["input_mode"], "native_source_spans", "input_mode")
    same(arguments["source_ref"], context["source_ref"], "source_ref")
    same(arguments["source_kind"], context["source_kind"], "source_kind")
    def selected_sources(value):
        if isinstance(value, dict):
            if set(value) == {"source_ref", "representation", "start", "end", "quote"}:
                yield value["source_ref"]
            else:
                for child in value.values():
                    yield from selected_sources(child)
        elif isinstance(value, list):
            for child in value:
                yield from selected_sources(child)
    same(set(context["source_refs"]), {arguments["source_ref"], *selected_sources(arguments)}, "source_refs")
    same(arguments["experiment"], selected_witness(context["experiment"]), "experiment")
    comparison = context["comparison"]
    same(arguments["comparison"], {**{name + "_relation": {
        "value": comparison[name + "_relation"]["value"],
        "witnesses": [selected_witness(w) for w in comparison[name + "_relation"]["witnesses"]]}
        for name in RELATIONS}, "intended_change": selected_witness(comparison["intended_change"])}, "comparison")
    for name in ("dependence", "observation_model"):
        model = context["model"][name]
        same(arguments[name], {"value": model["value"], "witnesses": [selected_witness(w) for w in model["witnesses"]]}, name)
    rows = {row["arm"]: row for row in extraction["rows"]}
    for role in ROLES:
        selected = arguments["arms"][role]
        row = rows.get(role)
        if selected is None:
            same(row, None, role)
            continue
        if row is None:
            _fail("native_saved_selection_mismatch", role)
        source = row["source"]
        for name in MEANINGS:
            same(selected[name], selected_witness(source["meanings"][name]), role + "." + name)
        same(selected["measurement_identity"], selected_witness(source["measurement_identity"]), role + ".measurement_identity")
        rate = selected["rate"]
        same(rate, None if source["number"] is None else {"number": selected_number(source["number"]),
            "unit": selected_unit(source["unit"])}, role + ".rate")
        unc, raw = selected["uncertainty"], source["uncertainty"]
        same(unc["kind"], row["uncertainty"]["kind"], role + ".uncertainty.kind")
        same(unc["magnitude"], selected_number(raw["magnitude"]), role + ".uncertainty.magnitude")
        same(unc["count"], selected_number(raw["count"]), role + ".uncertainty.count")
        same(unc["kind_witnesses"], [selected_witness(w) for w in raw["kind_witnesses"]], role + ".uncertainty.kind_witnesses")
        same(unc["sampling_basis"], {"value": row["uncertainty"]["sampling_basis"],
            "witnesses": [selected_witness(w) for w in raw["sampling_witnesses"]]}, role + ".uncertainty.sampling_basis")
        if unc["unit"] is None:
            same(raw["unit"], source["unit"], role + ".uncertainty.unit")
        else:
            same(unc["unit"], selected_unit(raw["unit"]), role + ".uncertainty.unit")


__all__ = ["VERSION", "NATIVE_BINDINGS", "NATIVE_REASONS", "rate_source_population_schema",
           "read_rate_source_inputs", "native_pair_reason", "validate_native_extraction", "validate_native_selection"]
