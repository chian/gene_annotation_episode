"""Pure outcomes for explicitly paired, already retained nucleotide alignments.

The host authenticates every selected observation and supplies saved grading.
This module neither aligns sequences nor establishes custody. Existing saved
column counts and correspondence remain the numerical authority. Categories
describe observed sequence changes, never cleavage or a repair mechanism.
Substitution/deletion entries retain individual columns; insertions retain the
existing contiguous runs. These are not normalized biological variant calls.
"""
from __future__ import annotations

from copy import deepcopy
import re

from jsonschema import Draft202012Validator, validators

from .alignment_correspondence import COUNT_NAMES, _copy, _ratio, _same, _substituted, count_literal_alignment_columns, interval_length
from .alignment_site_inputs import _gapped_columns, _source
from .alignment_site_mapping import _validate_operand, map_operand_interval
from .biopython_pairwise_grader import _validate_sheet
from .sequence_extraction_grader import frozen_reverse_complement
from .tool_grading_artifacts import validate_tool_correspondence


REQUEST_VERSION = "reference_edit_outcome_request_v1"
SHEET_VERSION = "reference_edit_outcome_sheet_v1"
COMPONENT_VERSION = "reference_edit_outcome_components_v1"
RETURN_VERSION = "reference_edit_outcome_return_v1"
_SOURCE = re.compile(r"source_[a-f0-9]{24,64}\Z")
_SYMBOLS = frozenset("ACGTURYSWKMBDHVNacgturyswkmbdhvn")
_KINDS = ("unchanged", "substitution_only", "insertion_only", "deletion_only", "mixed")
_STATES = ("not_selected", "unavailable", "no_alignment", "partial", "complete", "conflicting")
_ISSUES = (
    "grading_not_retained", "saved_correspondence_unavailable", "grading_unavailable", "grading_failed",
    "retained_alignment_qualified", "alignment_geometry_unavailable", "alignment_geometry_conflict",
    "original_mapping_unavailable", "original_mapping_conflict", "comparison_input_unavailable",
    "comparison_bounds_conflict", "comparison_length_conflict", "comparison_symbols_unsupported",
    "comparison_empty",
)
_COUNT_UNITS = {name: "alignment_columns" if name.endswith("columns") else "nt" for name in COUNT_NAMES}


def _require(condition, code):
    if not condition:
        raise ValueError("reference_edit_outcome_" + code)


def _json(value):
    try:
        return _copy(value)
    except (ValueError, RecursionError) as error:
        raise ValueError("reference_edit_outcome_finite_json_required") from error


def _closed(value, fields):
    _require(type(value) is dict and set(value) == set(fields.split()), "closed_fields_required")


def _text(value):
    return type(value) is str and bool(value) and not any(c in value for c in "\0\r\n")


def _interval(value):
    _require(type(value) is list and len(value) == 2 and all(type(v) is int for v in value)
        and 0 <= value[0] <= value[1], "interval_invalid")


def _request(value):
    value = _json(value)
    _closed(value, "version population gap_bins guide_comparisons template_comparisons")
    _require(value["version"] == REQUEST_VERSION and type(value["population"]) is list, "request_invalid")
    for row in value["population"]:
        _closed(row, "reference_ref edited_ref alignment_ref group_label")
        _require(_text(row["reference_ref"]) and _text(row["edited_ref"])
            and (row["alignment_ref"] is None or _text(row["alignment_ref"]))
            and (row["group_label"] is None or type(row["group_label"]) is str), "population_invalid")
    bins = value["gap_bins"]
    if bins is not None:
        _closed(bins, "deletion_upper_bounds_nt insertion_upper_bounds_nt")
        for values in bins.values():
            _require(type(values) is list and all(type(v) is int and v > 0 for v in values)
                and all(a < b for a, b in zip(values, values[1:])), "gap_bins_invalid")
    for name in ("guide_comparisons", "template_comparisons"):
        _require(type(value[name]) is list, "comparisons_invalid")
        for row in value[name]:
            _closed(row, "pair_ordinal guide_ref reference_interval orientation molecule" if name == "guide_comparisons"
                else "pair_ordinal template_ref edited_interval reference_interval orientation molecule")
            _require(type(row["pair_ordinal"]) is int and 0 <= row["pair_ordinal"] < len(value["population"])
                and row["orientation"] in ("as_is", "reverse_complement") and row["molecule"] in ("dna", "rna"),
                "comparison_selection_invalid")
            _require(_text(row["guide_ref" if name == "guide_comparisons" else "template_ref"]), "comparison_selection_invalid")
            if name == "guide_comparisons" or row["reference_interval"] is not None:
                _interval(row["reference_interval"])
            if name == "template_comparisons":
                _interval(row["edited_interval"])
    return value


def _comparison_refs(request):
    refs = []
    for name in ("guide_comparisons", "template_comparisons"):
        for row in request[name]:
            pair = request["population"][row["pair_ordinal"]]
            refs.extend((row["guide_ref"], pair["reference_ref"]) if name == "guide_comparisons"
                else (row["template_ref"], pair["edited_ref"]))
            if name == "template_comparisons" and row["reference_interval"] is not None:
                refs.append(pair["reference_ref"])
    return list(dict.fromkeys(refs))


def _sequences(value, request):
    value = _json(value)
    _closed(value, "sequences")
    _require(type(value["sequences"]) is list, "comparison_inputs_invalid")
    for row in value["sequences"]:
        _closed(row, "subject_ref sequence")
        _require(_text(row["subject_ref"]) and (row["sequence"] is None or type(row["sequence"]) is str),
            "comparison_inputs_invalid")
    _require([row["subject_ref"] for row in value["sequences"]] == _comparison_refs(request),
        "comparison_input_identity_conflict")
    return value, {row["subject_ref"]: row["sequence"] for row in value["sequences"]}


def _alignment(value, pair):
    if pair["alignment_ref"] is None:
        _require(value is None, "unselected_alignment_supplied")
        return
    _closed(value, "source operands grading correspondence original_mappings")
    _source(value["source"], "biopython.alignment", "biopython_pairwise_json")
    _require(value["source"]["alignment_ref"] == pair["alignment_ref"], "alignment_identity_conflict")
    _closed(value["operands"], "query reference")
    for role, reference in (("query", pair["edited_ref"]), ("reference", pair["reference_ref"])):
        operand = value["operands"][role]
        _validate_operand(operand)
        _require(operand["subject_ref"] == reference and operand["alignment_unit"] == "nt"
            and operand["unit"] in ("nt", "symbol") and operand["molecule"] in ("dna", "rna", "unknown"),
            "alignment_operand_conflict")
    mappings = value["original_mappings"]
    _require(mappings is None or type(mappings) is dict and set(mappings) == {"query", "reference"}
        and all(v is None or type(v) is dict for v in mappings.values()), "original_mappings_invalid")
    grading = value["grading"]
    if grading is None:
        _require(value["correspondence"] is None, "grading_conflict")
        return
    _closed(grading, "sheet scores failure")
    _require(grading["failure"] is None or type(grading["failure"]) is dict, "grading_conflict")
    sheet = grading["sheet"]
    if sheet is None:
        _require(grading["scores"] is None and value["correspondence"] is None, "grading_conflict")
        return
    _validate_sheet(sheet)
    _require(sheet["molecule"] in ("dna", "rna"), "nucleotide_alignment_required")
    native_version = sheet["native_result"].get("biopython_version")
    _require(native_version is None or value["source"]["native_version"] is None
        or native_version == value["source"]["native_version"], "alignment_version_conflict")
    for role, operand in value["operands"].items():
        length = sheet["lengths"][role]
        _require(length is None or operand["length"] is None or length == operand["length"], "alignment_operand_conflict")
        interval = sheet["geometry"].get(role + "_interval")
        _require(not sheet["geometry"]["available"] or operand["length"] is None or interval is None
            or interval[1] <= operand["length"], "alignment_operand_conflict")
    if grading["scores"] is not None:
        _require(type(grading["scores"]) is dict, "grading_conflict")
        if value["correspondence"] is not None:
            validate_tool_correspondence({"sheet": sheet, "scores": grading["scores"]}, value["correspondence"])
    else:
        _require(value["correspondence"] is None, "grading_conflict")


def _types(counts):
    values = [counts[key] for key in ("substituted_positions", "reference_gap_columns", "query_gap_columns")]
    return None if any(v is None for v in values) else [name for name, value in
        zip(("substitution", "insertion", "deletion"), values) if value > 0]


def _category(types):
    return None if types is None else "unchanged" if not types else types[0] + "_only" if len(types) == 1 else "mixed"


def _bin(value, bounds):
    if value is None or value == 0:
        return None
    ordinal = next((i for i, upper in enumerate(bounds) if value <= upper), len(bounds))
    return dict(bin_ordinal=ordinal, lower_exclusive_nt=0 if ordinal == 0 else bounds[ordinal - 1],
        upper_inclusive_nt=bounds[ordinal] if ordinal < len(bounds) else None)


def _mapped(event, capture, issues):
    for role in ("query", "reference"):
        mapping = map_operand_interval(capture["operands"][role],
            (capture["original_mappings"] or {}).get(role), event[role + "_interval"])
        event[role + "_mapping"] = mapping
        if mapping["status"] in ("unavailable", "incompatible"):
            code = "original_mapping_unavailable" if mapping["status"] == "unavailable" else "original_mapping_conflict"
            if code not in issues: issues.append(code)
    return event


def _events(sheet, capture, issues):
    if sheet["alignment_state"] == "no_alignment":
        return []
    if not sheet["geometry"]["available"]:
        return None
    found, insertions = _gapped_columns(sheet["residue_correspondence"],
        reference_start=sheet["geometry"]["reference_interval"][0], original_symbols=False)
    result = []
    for position, row in found.items():
        if row["relationship"] not in ("substituted", "query_gap"): continue
        qpos, column = row["query_position"], row["alignment_column"]
        result.append(dict(kind="substitution" if qpos is not None else "deletion",
            alignment_column_interval=[column, column + 1], reference_interval=[position, position + 1],
            reference_boundary=None, query_interval=None if qpos is None else [qpos, qpos + 1],
            reference_sequence=row["reference_symbol"], query_sequence=row["query_symbol"]))
    for row in insertions:
        result.append(dict(kind="insertion", alignment_column_interval=row["alignment_column_interval"],
            reference_interval=None, reference_boundary=row["reference_boundary"], query_interval=row["query_interval"],
            reference_sequence=None, query_sequence=row["query_sequence"]))
    result.sort(key=lambda row: row["alignment_column_interval"][0])
    return [_mapped(dict(event_ordinal=i, **row), capture, issues) for i, row in enumerate(result)]


def _pair(ordinal, pair, capture, bins):
    result = dict(pair_ordinal=ordinal, **deepcopy(pair), source_ref=None, state="not_selected",
        alignment_state=None, coverage_scope="not_selected", full_global_pair=False,
        native=None, counts=dict.fromkeys(COUNT_NAMES), count_units=dict(_COUNT_UNITS),
        observed_change_types=None, whole_pair_type=None, events=None, gap_bins=None, issue_codes=[])
    if capture is None: return result
    result.update(source_ref=capture["source"]["source_ref"], state="unavailable", coverage_scope="unavailable")
    grading, issues = capture["grading"], result["issue_codes"]
    if grading is None:
        issues.append("grading_not_retained"); return result
    if grading["failure"] is not None: issues.append("grading_failed")
    sheet = grading["sheet"]
    if sheet is None:
        issues.append("grading_unavailable"); return result
    if grading["scores"] is None: issues.append("grading_unavailable")
    elif capture["correspondence"] is None: issues.append("saved_correspondence_unavailable")
    if sheet["issues"]: issues.append("retained_alignment_qualified")
    result["native"] = dict(format=sheet["native_result"].get("native_format"),
        molecule=sheet["molecule"], mode=sheet["mode"], version=capture["source"]["native_version"],
        parameters=deepcopy(sheet["native_parameters"]), score=sheet["native_score"],
        score_unit="native_alignment_score",
        symbol_interpretation=deepcopy(sheet["symbol_interpretation"]))
    result["counts"] = deepcopy(sheet["measured_column_counts"])
    result["alignment_state"] = sheet["alignment_state"]
    geometry = sheet["geometry"]
    full = sheet["alignment_state"] == "alignment" and sheet["mode"] == "global" and geometry["available"] and all(
        capture["operands"][role]["length"] is not None
        and geometry[role + "_interval"] == [0, capture["operands"][role]["length"]]
        for role in ("query", "reference"))
    result["full_global_pair"] = full
    result["observed_change_types"] = _types(result["counts"])
    result["whole_pair_type"] = _category(result["observed_change_types"]) if full else None
    result["events"] = _events(sheet, capture, issues)
    if sheet["alignment_state"] == "no_alignment":
        result.update(state="no_alignment", coverage_scope="no_alignment")
    elif sheet["alignment_state"] == "conflicting":
        result["state"] = "conflicting"
    elif geometry["available"]:
        result.update(state="partial" if issues or not full else "complete",
            coverage_scope="full_global" if full else "selected_alignment")
    else:
        native = sheet["native_result"]
        # The existing reader also calls a one-sided missing traceback invalid.
        # Coordinates alone cannot prove a contradiction with missing symbols.
        both_supplied = all(native.get(key) is not None for key in ("aligned_query", "aligned_reference"))
        traceback_state = sheet["traceback"]["status"]
        conflict = both_supplied and (traceback_state == "invalid"
            or traceback_state == "valid" and native.get("coordinates") is not None)
        issues.append("alignment_geometry_conflict" if conflict else "alignment_geometry_unavailable")
        result["state"] = "conflicting" if conflict else "partial" if result["observed_change_types"] is not None else "unavailable"
    if bins is not None:
        result["gap_bins"] = dict(deletion=_bin(result["counts"]["query_gap_columns"], bins["deletion_upper_bounds_nt"]),
            insertion=_bin(result["counts"]["reference_gap_columns"], bins["insertion_upper_bounds_nt"]))
    return result


def _literal(sequence, target, interval, orientation, molecule):
    result = dict(state="unavailable", model="literal_case_sensitive", symbol_unit="literal_symbols", compared_symbols=None,
        identical_symbols=None, substituted_symbols=None, identity=dict(value=None, numerator=None,
            denominator=None, unit="fraction"), issue_code=None)
    code = None
    if sequence is None or target is None: code = "comparison_input_unavailable"
    elif interval[1] > len(target): code = "comparison_bounds_conflict"
    elif set(sequence) - _SYMBOLS or set(target[slice(*interval)]) - _SYMBOLS: code = "comparison_symbols_unsupported"
    else:
        oriented = sequence if orientation == "as_is" else frozen_reverse_complement(sequence, molecule=molecule)
        window = target[slice(*interval)]
        if not oriented or not window: code = "comparison_empty"
        elif len(oriented) != len(window): code = "comparison_length_conflict"
        else:
            counts = count_literal_alignment_columns(oriented, window)
            numerator, denominator = counts["identical_positions"], counts["paired_positions"]
            result.update(state="available", compared_symbols=denominator, identical_symbols=numerator,
                substituted_symbols=counts["substituted_positions"],
                identity=dict(value=_ratio(numerator, denominator), numerator=numerator, denominator=denominator, unit="fraction"))
    if code is not None:
        result.update(state={"comparison_empty": "empty", "comparison_length_conflict": "length_conflict",
            "comparison_bounds_conflict": "bounds_conflict", "comparison_symbols_unsupported": "unsupported"}.get(code, "unavailable"), issue_code=code)
    return result


def _comparisons(request, pairs, sequences):
    guides, templates = [], []
    for ordinal, selected in enumerate(request["guide_comparisons"]):
        pair, interval = pairs[selected["pair_ordinal"]], selected["reference_interval"]
        compared = _literal(sequences[selected["guide_ref"]], sequences[pair["reference_ref"]], interval,
            selected["orientation"], selected["molecule"])
        guides.append(dict(comparison_ordinal=ordinal, **deepcopy(selected), placement_basis="caller_supplied",
            literal_comparison=compared, event_offsets=_guide_offsets(pair["events"], selected, compared), offset_unit="nt"))
    for ordinal, selected in enumerate(request["template_comparisons"]):
        pair = pairs[selected["pair_ordinal"]]
        template = sequences[selected["template_ref"]]
        def compare(role):
            return _literal(template, sequences[pair[role + "_ref"]], selected[role + "_interval"],
                selected["orientation"], selected["molecule"])
        templates.append(dict(comparison_ordinal=ordinal, **deepcopy(selected),
            edited_comparison=compare("edited"),
            reference_comparison=None if selected["reference_interval"] is None else compare("reference")))
    return guides, templates


def _guide_offsets(events, selected, compared):
    if events is None or compared["state"] == "bounds_conflict": return None
    result, interval = [], selected["reference_interval"]
    reverse = selected["orientation"] == "reverse_complement"
    for event in events:
        span, boundary = event["reference_interval"], event["reference_boundary"]
        result.append(dict(event_ordinal=event["event_ordinal"], reference_interval=(None if span is None else
            [interval[1] - span[1], interval[1] - span[0]] if reverse else [span[0] - interval[0], span[1] - interval[0]]),
            reference_boundary=None if boundary is None else interval[1] - boundary if reverse else boundary - interval[0]))
    return result


def _issue_codes(pairs, guides, templates):
    codes = [code for pair in pairs for code in pair["issue_codes"]]
    codes += [row["literal_comparison"]["issue_code"] for row in guides]
    codes += [row[key]["issue_code"] for row in templates for key in ("edited_comparison", "reference_comparison") if row[key] is not None]
    return list(dict.fromkeys(code for code in codes if code is not None))


def _status(pairs, issues):
    return "partial" if issues or any(row["state"] not in ("complete", "no_alignment") for row in pairs) else "complete"


def populate_reference_edit_outcome_sheet(request, *, alignment_inputs, comparison_inputs):
    """Copy selected saved authorities and project their original correspondence.

    Input captures are data, never evidence of receipt or producer authority.
    One parallel slot represents one declared occurrence, including duplicates.
    """
    request = _request(request)
    alignment_inputs = _json(alignment_inputs)
    _require(type(alignment_inputs) is list and len(alignment_inputs) == len(request["population"]), "alignment_population_conflict")
    comparison_inputs, sequences = _sequences(comparison_inputs, request)
    try:
        for pair, capture in zip(request["population"], alignment_inputs): _alignment(capture, pair)
        # A comparison capture of the same operand must not contradict known bounds.
        for pair, capture in zip(request["population"], alignment_inputs):
            if capture is None: continue
            for role, name in (("query", "edited_ref"), ("reference", "reference_ref")):
                sequence, length = sequences.get(pair[name]), capture["operands"][role]["length"]
                _require(sequence is None or length is None or len(sequence) == length, "comparison_operand_length_conflict")
        pairs = [_pair(i, pair, capture, request["gap_bins"]) for i, (pair, capture) in enumerate(zip(request["population"], alignment_inputs))]
        guides, templates = _comparisons(request, pairs, sequences)
    except (KeyError, TypeError, AttributeError, IndexError) as error:
        raise ValueError("reference_edit_outcome_alignment_inputs_invalid") from error
    _require(all(_STRICT(_PAIR).is_valid(row) for row in pairs)
        and all(_STRICT(_GUIDE).is_valid(row) for row in guides)
        and all(_STRICT(_TEMPLATE).is_valid(row) for row in templates), "saved_cells_invalid")
    issues = _issue_codes(pairs, guides, templates)
    return dict(version=SHEET_VERSION, status=_status(pairs, issues), request=request, alignment_inputs=alignment_inputs, comparison_inputs=comparison_inputs,
        pairs=pairs, guide_comparisons=guides, template_comparisons=templates, issue_codes=issues)


def _population(rows):
    declared, classified = len(rows), sum(row["whole_pair_type"] is not None for row in rows)
    selected = sum(row["alignment_ref"] is not None for row in rows)
    counts = {kind: sum(row["whole_pair_type"] == kind for row in rows) for kind in _KINDS}
    def fraction(numerator, denominator):
        return dict(value=_ratio(numerator, denominator), numerator=numerator, denominator=denominator, unit="fraction")
    return dict(unit="pair_occurrences", declared_pair_count=declared, selected_alignment_count=selected,
        not_selected_pair_count=declared - selected, classified_pair_count=classified,
        unclassified_pair_count=declared - classified,
        state_counts={state: sum(row["state"] == state for row in rows) for state in _STATES},
        categories=[dict(kind=kind, count=counts[kind],
            fraction_of_classified=fraction(counts[kind], classified),
            observed_fraction_of_declared=fraction(counts[kind], declared)) for kind in _KINDS])


def _populations(pairs):
    references = list(dict.fromkeys(row["reference_ref"] for row in pairs))
    groups = list(dict.fromkeys(row["group_label"] for row in pairs))
    return dict(overall=_population(pairs),
        by_reference=[dict(reference_ref=ref, population=_population([row for row in pairs if row["reference_ref"] == ref])) for ref in references],
        by_group=[dict(group_label=group, population=_population([row for row in pairs if row["group_label"] == group])) for group in groups])


def calculate_reference_edit_outcome_components(sheet):
    """Validate saved inputs/rows and calculate only outcome-population quantities."""
    sheet = _json(sheet)
    _closed(sheet, "version status request alignment_inputs comparison_inputs pairs guide_comparisons template_comparisons issue_codes")
    _require(sheet["version"] == SHEET_VERSION, "saved_sheet_required")
    expected = populate_reference_edit_outcome_sheet(sheet["request"], alignment_inputs=sheet["alignment_inputs"],
        comparison_inputs=sheet["comparison_inputs"])
    _require(_same(sheet, expected), "saved_sheet_conflict")
    return dict(version=COMPONENT_VERSION, status=sheet["status"], request=deepcopy(sheet["request"]), pairs=deepcopy(sheet["pairs"]),
        populations=_populations(sheet["pairs"]), guide_comparisons=deepcopy(sheet["guide_comparisons"]),
        template_comparisons=deepcopy(sheet["template_comparisons"]), issue_codes=list(sheet["issue_codes"]))


def _object(properties):
    return dict(type="object", properties=properties, required=list(properties), additionalProperties=False)


def _array(items):
    return dict(type="array", items=items)


def _nullable(node):
    return {**node, "type": [node["type"], "null"], **({"enum": [*node["enum"], None]} if "enum" in node else {})}


def _enum(values):
    return dict(type="string", enum=list(values))


_INT = dict(type="integer", minimum=0)
_TEXT = dict(type="string")
_REF = dict(type="string", minLength=1)  # Opaque provenance: no semantic reference format.
_INTERVAL = dict(type="array", items=_INT, minItems=2, maxItems=2)
_RATIO = _object(dict(value=_nullable(dict(type="number", minimum=0, maximum=1)), numerator=_INT,
    denominator=_INT, unit=dict(type="string", const="fraction")))
_SEGMENT = _object(dict(subject_ref=_REF, start=_INT, end=_INT, unit=_enum(("nt", "aa", "symbol")), strand=_enum(("+", "-"))))
_MAPPING = _object(dict(status=_enum(("available", "unavailable", "incompatible", "not_applicable")),
    intervals=_nullable(_array(_SEGMENT)), reason=_nullable(_enum(("site_original_mapping_unavailable", "site_original_mapping_conflict")))))
_EVENT = _object(dict(event_ordinal=_INT, kind=_enum(("substitution", "insertion", "deletion")),
    alignment_column_interval=_INTERVAL, reference_interval=_nullable(_INTERVAL), reference_boundary=_nullable(_INT),
    query_interval=_nullable(_INTERVAL), reference_sequence=_nullable(_TEXT), query_sequence=_nullable(_TEXT),
    query_mapping=_MAPPING, reference_mapping=_MAPPING))
_EVENT["description"] = "One retained substitution/deletion column or existing contiguous insertion run; not a normalized variant or repair event."
_BIN = _nullable(_object(dict(bin_ordinal=_INT, lower_exclusive_nt=_INT, upper_inclusive_nt=_nullable(_INT))))
_BINS = _nullable(_object(dict(deletion_upper_bounds_nt=_array(dict(type="integer", minimum=1)),
    insertion_upper_bounds_nt=_array(dict(type="integer", minimum=1)))))
_LITERAL = _object(dict(state=_enum(("available", "unavailable", "empty", "length_conflict", "bounds_conflict", "unsupported")),
    model=dict(type="string", const="literal_case_sensitive"), symbol_unit=dict(type="string", const="literal_symbols"),
    compared_symbols=_nullable(_INT), identical_symbols=_nullable(_INT),
    substituted_symbols=_nullable(_INT), identity=_object(dict(value=_nullable(dict(type="number", minimum=0, maximum=1)),
        numerator=_nullable(_INT), denominator=_nullable(_INT), unit=dict(type="string", const="fraction"))),
    issue_code=_nullable(_enum(_ISSUES))))
_COMPARISON_SELECTION = dict(pair_ordinal=_INT, orientation=_enum(("as_is", "reverse_complement")), molecule=_enum(("dna", "rna")))
_GUIDE = _object(dict(comparison_ordinal=_INT, **_COMPARISON_SELECTION, guide_ref=_REF, reference_interval=_INTERVAL,
    placement_basis=dict(type="string", const="caller_supplied"), literal_comparison=_LITERAL,
    event_offsets=_nullable(_array(_object(dict(event_ordinal=_INT,
        reference_interval=_nullable(dict(type="array", items=dict(type="integer"), minItems=2, maxItems=2)),
        reference_boundary=_nullable(dict(type="integer")))))), offset_unit=dict(type="string", const="nt")))
_TEMPLATE = _object(dict(comparison_ordinal=_INT, **_COMPARISON_SELECTION, template_ref=_REF,
    edited_interval=_INTERVAL, reference_interval=_nullable(_INTERVAL), edited_comparison=_LITERAL, reference_comparison=_nullable(_LITERAL)))
_PAIR = _object(dict(pair_ordinal=_INT, reference_ref=_REF, edited_ref=_REF, alignment_ref=_nullable(_REF), group_label=_nullable(_TEXT),
    source_ref=_nullable(_REF), state=_enum(_STATES), alignment_state=_nullable(_enum(("alignment", "no_alignment", "conflicting"))),
    coverage_scope=_enum(("not_selected", "unavailable", "no_alignment", "full_global", "selected_alignment")),
    full_global_pair=dict(type="boolean"), native=_nullable(_object(dict(format=_nullable(_enum(("biopython_pairwise_native_v2",))),
        molecule=_enum(("dna", "rna")), mode=_enum(("local", "global")), version=_nullable(_TEXT),
        parameters=_object(dict(matrix=_nullable(_TEXT), gap_open=_nullable(dict(type="number")), gap_extend=_nullable(dict(type="number")))),
        score=_nullable(dict(type="number")), score_unit=dict(type="string", const="native_alignment_score"),
        symbol_interpretation=_object(dict(reader_normalization=_TEXT,
            native_nucleotide_normalization=_nullable(_TEXT), identity=_TEXT))))),
    counts=_object({key: _nullable(_INT) for key in COUNT_NAMES}),
    count_units=_object({key: dict(type="string", const=unit) for key, unit in _COUNT_UNITS.items()}),
    observed_change_types=_nullable(_array(_enum(("substitution", "insertion", "deletion")))), whole_pair_type=_nullable(_enum(_KINDS)),
    events=_nullable(_array(_EVENT)), gap_bins=_nullable(_object(dict(deletion=_BIN, insertion=_BIN))), issue_codes=_array(_enum(_ISSUES))))
_POPULATION = _object(dict(unit=dict(type="string", const="pair_occurrences"), declared_pair_count=_INT, selected_alignment_count=_INT,
    not_selected_pair_count=_INT, classified_pair_count=_INT, unclassified_pair_count=_INT,
    state_counts=_object({state: _INT for state in _STATES}), categories=_array(_object(dict(kind=_enum(_KINDS), count=_INT,
        fraction_of_classified=deepcopy(_RATIO), observed_fraction_of_declared=deepcopy(_RATIO))))))
_POPULATION["properties"]["categories"]["items"]["properties"]["fraction_of_classified"]["description"] = (
    "Category occurrences divided by full-global classified pair occurrences; zero denominator remains null.")
_POPULATION["properties"]["categories"]["items"]["properties"]["observed_fraction_of_declared"]["description"] = (
    "Observed category occurrences divided by all declared pair occurrences; unclassified occurrences contribute only to the denominator, not inferred absence.")
_PUBLIC = dict(status=_enum(("complete", "partial")), alignment_unit=dict(type="string", const="nt"),
    coordinate_system=dict(type="string", const="zero_based_half_open_local_operands"),
    gap_bins=_BINS, pairs=_array(_PAIR), populations=_object(dict(overall=_POPULATION,
    by_reference=_array(_object(dict(reference_ref=_REF, population=_POPULATION))),
    by_group=_array(_object(dict(group_label=_nullable(_TEXT), population=_POPULATION))))),
    guide_comparisons=_array(_GUIDE), template_comparisons=_array(_TEMPLATE), issue_codes=_array(_enum(_ISSUES)))
_RETURN_SCHEMA = _object(dict(version=dict(type="string", const=RETURN_VERSION),
    source_ref=dict(type="string", pattern=r"^source_[a-f0-9]{24,64}$", format="reference", **{"x-reference-namespace": "source"}), **_PUBLIC))
RETURN_SCHEMA = deepcopy(_RETURN_SCHEMA)
_STRICT = validators.extend(Draft202012Validator, type_checker=Draft202012Validator.TYPE_CHECKER.redefine(
    "integer", lambda _checker, value: type(value) is int))


def _public(components):
    return dict(alignment_unit="nt", coordinate_system="zero_based_half_open_local_operands",
        gap_bins=deepcopy(components["request"]["gap_bins"]), **{key: deepcopy(components[key]) for key in
        ("status", "pairs", "populations", "guide_comparisons", "template_comparisons", "issue_codes")})


def validate_reference_edit_outcome_return(value):
    """Validate the closed public DTO; this establishes no producer or receipt."""
    value = _json(value)
    _require(_STRICT(_RETURN_SCHEMA).is_valid(value), "return_invalid")
    bins = value["gap_bins"]
    request = dict(version=REQUEST_VERSION, population=[{key: row[key] for key in ("reference_ref", "edited_ref", "alignment_ref", "group_label")}
        for row in value["pairs"]], gap_bins=bins,
        guide_comparisons=[{key: row[key] for key in ("pair_ordinal", "guide_ref", "reference_interval", "orientation", "molecule")}
            for row in value["guide_comparisons"]],
        template_comparisons=[{key: row[key] for key in ("pair_ordinal", "template_ref", "edited_interval", "reference_interval", "orientation", "molecule")}
            for row in value["template_comparisons"]])
    _request(request)
    for i, row in enumerate(value["pairs"]):
        _require(all(v is None for v in row["counts"].values()) or all(v is not None for v in row["counts"].values()),
            "return_pair_conflict")
        _require(row["pair_ordinal"] == i and row["observed_change_types"] == _types(row["counts"]), "return_pair_conflict")
        _require(row["whole_pair_type"] == (_category(row["observed_change_types"]) if row["full_global_pair"] else None), "return_pair_conflict")
        if row["full_global_pair"]:
            _require(row["native"] is not None and row["native"]["mode"] == "global" and row["alignment_state"] == "alignment"
                and row["coverage_scope"] == "full_global" and row["events"] is not None
                and row["whole_pair_type"] is not None and row["state"] in ("complete", "partial"), "return_pair_conflict")
        else:
            _require(row["coverage_scope"] != "full_global", "return_pair_conflict")
        if row["native"] is None:
            _require(row["alignment_state"] is None and row["events"] is None and not row["full_global_pair"]
                and all(v is None for v in row["counts"].values()), "return_pair_conflict")
        if row["coverage_scope"] == "selected_alignment":
            _require(row["alignment_state"] == "alignment" and row["events"] is not None and not row["full_global_pair"],
                "return_pair_conflict")
        if row["coverage_scope"] == "unavailable":
            _require(row["events"] is None, "return_pair_conflict")
        if row["state"] == "complete":
            _require(row["full_global_pair"] and not row["issue_codes"], "return_pair_conflict")
        if row["state"] == "no_alignment":
            _require(row["alignment_state"] == "no_alignment" and row["coverage_scope"] == "no_alignment"
                and not row["full_global_pair"] and all(v == 0 for v in row["counts"].values()) and row["events"] == [], "return_pair_conflict")
        if row["alignment_ref"] is None:
            _require(row["state"] == "not_selected" and row["source_ref"] is row["native"] is row["events"] is None
                and row["alignment_state"] is None and row["coverage_scope"] == "not_selected" and not row["issue_codes"]
                and all(v is None for v in row["counts"].values()), "return_pair_conflict")
        else:
            _require(row["state"] != "not_selected" and row["source_ref"] is not None, "return_pair_conflict")
        expected_bins = None if bins is None or row["native"] is None else dict(
            deletion=_bin(row["counts"]["query_gap_columns"], bins["deletion_upper_bounds_nt"]),
            insertion=_bin(row["counts"]["reference_gap_columns"], bins["insertion_upper_bounds_nt"]))
        _require(_same(row["gap_bins"], expected_bins), "return_bin_conflict")
        for j, event in enumerate(row["events"] or []):
            _require(event["event_ordinal"] == j, "return_event_conflict")
            _require(j == 0 or row["events"][j - 1]["alignment_column_interval"][1] <= event["alignment_column_interval"][0],
                "return_event_conflict")
            for key in ("alignment_column_interval", "reference_interval", "query_interval"):
                if event[key] is not None:
                    _interval(event[key]); _require(event[key][0] < event[key][1], "return_event_conflict")
            _require((event["reference_interval"] is None) == (event["kind"] == "insertion")
                and (event["reference_boundary"] is not None) == (event["kind"] == "insertion")
                and (event["query_interval"] is None) == (event["kind"] == "deletion"), "return_event_conflict")
            for role in ("query", "reference"):
                span, sequence, mapping = event[role + "_interval"], event[role + "_sequence"], event[role + "_mapping"]
                _require((span is None) == (sequence is None), "return_event_conflict")
                if span is not None:
                    _require(len(sequence) == interval_length(span), "return_event_conflict")
                if mapping["status"] == "not_applicable":
                    _require(span is None and mapping["intervals"] == [] and mapping["reason"] is None, "return_mapping_conflict")
                elif mapping["status"] == "available":
                    _require(span is not None and bool(mapping["intervals"]) and mapping["reason"] is None, "return_mapping_conflict")
                    for segment in mapping["intervals"]:
                        _require(segment["start"] < segment["end"], "return_mapping_conflict")
                else:
                    _require(span is not None and mapping["intervals"] is None and mapping["reason"] == (
                        "site_original_mapping_unavailable" if mapping["status"] == "unavailable" else "site_original_mapping_conflict"),
                        "return_mapping_conflict")
    _require(_same(value["populations"], _populations(value["pairs"])), "return_population_conflict")
    for name in ("guide_comparisons", "template_comparisons"):
        for i, row in enumerate(value[name]):
            _require(row["comparison_ordinal"] == i, "return_comparison_conflict")
            if name == "guide_comparisons":
                _require(_same(row["event_offsets"], _guide_offsets(value["pairs"][row["pair_ordinal"]]["events"], row,
                    row["literal_comparison"])), "return_comparison_conflict")
            else:
                _require((row["reference_interval"] is None) == (row["reference_comparison"] is None), "return_comparison_conflict")
            comparisons = [row["literal_comparison"]] if name == "guide_comparisons" else [row["edited_comparison"], row["reference_comparison"]]
            for compared in comparisons:
                if compared is None: continue
                n, d = compared["identity"]["numerator"], compared["identity"]["denominator"]
                if compared["state"] == "available":
                    _require(compared["issue_code"] is None and d == compared["compared_symbols"] and n == compared["identical_symbols"]
                        and n is not None and d is not None and 0 <= n <= d and d > 0
                        and compared["substituted_symbols"] == _substituted(d, n), "return_comparison_conflict")
                    _require(compared["identity"]["value"] == _ratio(n, d), "return_comparison_conflict")
                else:
                    expected_code = {"empty": "comparison_empty", "length_conflict": "comparison_length_conflict",
                        "bounds_conflict": "comparison_bounds_conflict", "unsupported": "comparison_symbols_unsupported",
                        "unavailable": "comparison_input_unavailable"}[compared["state"]]
                    _require(compared["issue_code"] == expected_code and n is d is compared["compared_symbols"] is compared["identical_symbols"]
                        is compared["substituted_symbols"] is compared["identity"]["value"] is None, "return_comparison_conflict")
    _require(value["issue_codes"] == _issue_codes(value["pairs"], value["guide_comparisons"], value["template_comparisons"]), "return_issue_conflict")
    _require(value["status"] == _status(value["pairs"], value["issue_codes"]), "return_status_conflict")
    return value


def project_reference_edit_outcome_return(components, *, source_ref):
    """Copy the complete original calculated group, without native or host I/O."""
    components = _json(components)
    _closed(components, "version status request pairs populations guide_comparisons template_comparisons issue_codes")
    _require(components["version"] == COMPONENT_VERSION and type(source_ref) is str and _SOURCE.fullmatch(source_ref) is not None,
        "components_or_source_invalid")
    request = _request(components["request"])
    value = validate_reference_edit_outcome_return(dict(version=RETURN_VERSION, source_ref=source_ref, **_public(components)))
    _require([{key: row[key] for key in ("reference_ref", "edited_ref", "alignment_ref", "group_label")} for row in value["pairs"]]
        == request["population"], "components_request_conflict")
    for name, keys in (("guide_comparisons", ("pair_ordinal", "guide_ref", "reference_interval", "orientation", "molecule")),
                       ("template_comparisons", ("pair_ordinal", "template_ref", "edited_interval", "reference_interval", "orientation", "molecule"))):
        _require(_same([{key: row[key] for key in keys} for row in value[name]], request[name]), "components_request_conflict")
    return value


__all__ = ["populate_reference_edit_outcome_sheet", "calculate_reference_edit_outcome_components",
    "project_reference_edit_outcome_return", "validate_reference_edit_outcome_return"]
