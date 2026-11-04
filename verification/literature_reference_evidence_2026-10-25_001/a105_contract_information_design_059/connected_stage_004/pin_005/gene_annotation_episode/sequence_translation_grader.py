"""Retain and validate one supplied translation without translating it again.

The reader records native product symbols, requested nucleotide geometry and
codon/source operands. The calculator validates saved cells and computes counts
and a selection fraction. Codon compatibility uses only the frozen supplied
genetic code, including CDS start/stop context and dual-coding stops. Neither
function imports Biopython, reads files, acquires data or assigns confidence.
"""
from __future__ import annotations

from copy import deepcopy
from itertools import product
import json
import math

from .sequence_mapping import map_interval, reverse_path, validate_mapping


SHEET_SCHEMA = "sequence_translation_sheet_v1"
SCORES_SCHEMA = "sequence_translation_scores_v1"
_REQUEST_KEYS = {"code", "strand", "frame", "start", "end", "cds"}
_TABLE_KEYS = {"code", "names", "start_codons", "stop_codons", "forward_table", "biopython_version"}
_DNA = {"A": "A", "C": "C", "G": "G", "T": "T", "R": "AG", "Y": "CT",
        "S": "CG", "W": "AT", "K": "GT", "M": "AC", "B": "CGT", "D": "AGT",
        "H": "ACT", "V": "ACG", "N": "ACGT"}
_COMPLEMENT = str.maketrans("ACGTRYSWKMBDHVN", "TGCAYRSWMKVHDBN")
_AA = frozenset("ACDEFGHIKLMNPQRSTVWYOU")
_AMBIGUOUS_AA = frozenset("BXZJ")
_GEOMETRY_KEYS = ("input_interval", "translated_interval", "strand", "frame")


def _json_copy(value):
    def valid(item):
        if type(item) is dict:
            return all(type(k) is str and valid(v) for k, v in item.items())
        if type(item) is list:
            return all(valid(v) for v in item)
        if type(item) is float:
            return math.isfinite(item)
        return item is None or type(item) in (str, int, bool)
    try:
        if not valid(value):
            raise ValueError("non_json_value")
        return json.loads(json.dumps(value, allow_nan=False))
    except (ValueError, TypeError, RecursionError) as error:
        raise ValueError("translation_finite_json_required") from error


def _equal(left, right):
    return json.dumps(left, sort_keys=True) == json.dumps(right, sort_keys=True)


def _state(state="present", reason=None):
    return {"state": state, "reason": reason}


def _issue(issues, code, **details):
    row = {"code": code, **details}
    if row not in issues:
        issues.append(row)


def _validate_operands(native, sequence, subject_ref, request):
    if not isinstance(native, dict) or "schema" in native:
        raise ValueError("translation_native_result_object_required")
    if not isinstance(sequence, str):
        raise ValueError("translation_input_sequence_string_required")
    if not isinstance(subject_ref, str) or not subject_ref:
        raise ValueError("translation_subject_ref_required")
    if not isinstance(request, dict) or set(request) != _REQUEST_KEYS:
        raise ValueError("translation_effective_request_required")
    if (type(request["code"]) is not int or request["code"] <= 0
            or request["strand"] not in ("+", "-")
            or type(request["frame"]) is not int or request["frame"] not in (0, 1, 2)
            or type(request["start"]) is not int or type(request["end"]) is not int
            or not 0 <= request["start"] < request["end"] <= len(sequence)
            or type(request["cds"]) is not bool):
        raise ValueError("translation_effective_request_invalid")
    available = request["end"] - request["start"] - request["frame"]
    if available < 3 or (request["cds"] and (request["frame"] != 0 or available % 3)):
        raise ValueError("translation_effective_request_has_no_valid_codon_interval")


def _native_check(native, key, expected, issues):
    if key not in native or native[key] is None:
        state = _state("missing", "native_field_missing")
    elif not _equal(native[key], expected):
        state = _state("incompatible", "native_field_conflicts_with_supplied_operands")
    else:
        return _state()
    _issue(issues, state["reason"], field=key, expected=expected, actual=native.get(key))
    return state


def _combined(states, reason):
    for kind in ("incompatible", "incomplete", "missing"):
        if any(state["state"] == kind for state in states):
            return _state(kind, reason)
    return _state()


def _table_operands(table, native, request, issues):
    """Validate supplied reference fields independently; do not fill missing data."""
    if table is None:
        _issue(issues, "genetic_code_snapshot_missing")
        return None, _state("missing", "genetic_code_snapshot_missing")
    if not isinstance(table, dict) or set(table) - _TABLE_KEYS:
        _issue(issues, "genetic_code_snapshot_incompatible")
        return None, _state("incompatible", "genetic_code_snapshot_incompatible")
    if not _equal(table.get("code"), request["code"]):
        _issue(issues, "genetic_code_identity_conflict")
        return None, _state("incompatible", "genetic_code_identity_conflict")
    version = table.get("biopython_version")
    if not isinstance(version, str) or not version:
        _issue(issues, "genetic_code_version_missing")
        return None, _state("missing", "genetic_code_version_missing")
    if native.get("biopython_version") is not None and native["biopython_version"] != version:
        _issue(issues, "genetic_code_version_conflict")
        return None, _state("incompatible", "genetic_code_version_conflict")
    if "genetic_code_snapshot" in native and not _equal(native["genetic_code_snapshot"], table):
        _issue(issues, "native_genetic_code_snapshot_conflict")
        return None, _state("incompatible", "native_genetic_code_snapshot_conflict")
    clean, states = {"code": table["code"], "biopython_version": version}, []
    for key in ("start_codons", "stop_codons", "forward_table"):
        value = table.get(key)
        is_codon = lambda c: isinstance(c, str) and len(c) == 3 and set(c) <= set("ACGT")
        if value is None:
            clean[key] = None
            states.append(_state("missing", "genetic_code_field_missing"))
            _issue(issues, "genetic_code_field_missing", field=key)
        elif ((key == "forward_table" and isinstance(value, dict)
               and all(is_codon(c) and isinstance(a, str) and len(a) == 1 and a in _AA
                       for c, a in value.items()))
              or (key != "forward_table" and isinstance(value, list)
                  and all(is_codon(c) for c in value) and len(set(value)) == len(value))):
            clean[key] = value
        else:
            clean[key] = None
            states.append(_state("incompatible", "genetic_code_field_incompatible"))
            _issue(issues, "genetic_code_field_incompatible", field=key)
    names = table.get("names")
    if not isinstance(names, list) or not all(v is None or isinstance(v, str) for v in names):
        states.append(_state("missing" if names is None else "incompatible", "genetic_code_names_unavailable"))
        _issue(issues, "genetic_code_names_unavailable")
    if clean["forward_table"] is not None and clean["stop_codons"] is not None:
        known = set(clean["forward_table"]) | set(clean["stop_codons"])
        if len(known) != 64:
            states.append(_state("incomplete", "genetic_code_codon_entries_missing"))
            _issue(issues, "genetic_code_codon_entries_missing", known_codon_count=len(known))
    return clean, _combined(states, "genetic_code_snapshot_partial")


def _codon_operands(codon, table, *, role, cds):
    """Inspect a codon's finite possibilities, not a new translation operation."""
    operands = {"context": role, "cds": cds, "expanded_codons": None,
        "forward_symbols": None, "stop_membership": None, "start_membership": None,
        "dual_coding_codons": None, "expected_symbol": None,
        "expected_terminal_omission": None, "reason": None}
    if set(codon) - _DNA.keys():
        operands["reason"] = "invalid_nucleotide_symbol"
        return operands
    expanded = ["".join(parts) for parts in product(*(_DNA[c] for c in codon))]
    operands["expanded_codons"] = expanded
    if table is None:
        operands["reason"] = "genetic_code_unavailable"
        return operands
    forward, stops, starts = table["forward_table"], table["stop_codons"], table["start_codons"]
    operands.update(code=table["code"], biopython_version=table["biopython_version"],
        forward_symbols=[forward.get(c) for c in expanded] if forward is not None else None,
        stop_membership=[c in stops for c in expanded] if stops is not None else None,
        start_membership=[c in starts for c in expanded] if starts is not None else None,
        dual_coding_codons=[c for c in expanded if c in stops and c in forward]
            if stops is not None and forward is not None else None)
    if role == "omitted_terminal_stop":
        if stops is None:
            operands["reason"] = "stop_codons_unavailable"
        else:
            operands["expected_terminal_omission"] = all(c in stops for c in expanded)
            if not operands["expected_terminal_omission"]:
                operands["reason"] = "cds_terminal_codon_is_not_a_stop"
        return operands
    if cds and role == "cds_start":
        if starts is None:
            operands["reason"] = "start_codons_unavailable"
        elif all(c in starts for c in expanded):
            operands["expected_symbol"] = "M"
        else:
            operands["reason"] = "cds_first_codon_is_not_a_start"
        return operands
    if forward is None:
        operands["reason"] = "forward_table_unavailable"
        return operands
    symbols = set()
    for triplet in expanded:
        if triplet in forward:
            symbols.add(forward[triplet])  # Dual-coding stops use this entry internally.
        elif stops is not None and triplet in stops:
            symbols.add("*")
        else:
            operands["reason"] = "codon_reference_entry_unavailable"
            return operands
    if len(symbols) == 1:
        expected = next(iter(symbols))
    else:
        expected = {frozenset("DN"): "B", frozenset("EQ"): "Z", frozenset("IL"): "J"}.get(frozenset(symbols), "X")
    operands["expected_symbol"] = expected
    if cds and expected == "*":
        operands["reason"] = "cds_internal_stop_forbidden"
    return operands


def _geometry(sequence, request):
    start, end, frame, strand = (request[k] for k in ("start", "end", "frame", "strand"))
    selected = end - start
    available = selected - frame
    used = available - available % 3
    translated = [start + frame, start + frame + used] if strand == "+" else [end-frame-used, end-frame]
    skipped = [start, start+frame] if strand == "+" else [end-frame, end]
    trailing = [translated[1], end] if strand == "+" else [start, translated[0]]
    return {"input_length_nt": len(sequence), "selected_length_nt": selected,
        "frame_skipped_nt": frame, "translated_length_nt": used,
        "trailing_untranslated_bases": available % 3, "translated_codon_count": used // 3,
        "input_interval": [start, end], "translated_interval": translated,
        "frame_skipped_interval": skipped, "trailing_interval": trailing,
        "expected_output_symbol_count": used // 3 - int(request["cds"])}


def _populate(native, sequence, subject_ref, mapping, request, genetic_code):
    _validate_operands(native, sequence, subject_ref, request)
    issues = []
    geometry = _geometry(sequence, request)
    checks = {key: _native_check(native, key, expected, issues) for key, expected in {
        "code": request["code"], "strand": request["strand"], "frame": request["frame"], "cds": request["cds"],
        "input_interval": geometry["input_interval"], "translated_interval": geometry["translated_interval"],
        "trailing_untranslated_bases": geometry["trailing_untranslated_bases"]}.items()}
    geometry_state = _combined([checks[k] for k in _GEOMETRY_KEYS], "native_geometry_unverified")
    settings_state = _combined([checks[k] for k in ("code", "cds", *_GEOMETRY_KEYS)], "native_settings_unverified")
    table, table_state = _table_operands(genetic_code, native, request, issues)
    mapping_state = _state()
    if mapping is None:
        mapping_state = _state("missing", "original_source_mapping_missing")
    else:
        try:
            validate_mapping(mapping)
            if (mapping["units_per_symbol"] != 1 or mapping["symbol_length"] != len(sequence)
                    or any(row["unit"] not in ("nt", "symbol") for row in mapping["path"])):
                raise ValueError("translation_parent_mapping_incompatible")
        except (ValueError, TypeError, KeyError) as error:
            mapping_state = _state("incompatible", str(error) if isinstance(error, ValueError)
                else "translation_parent_mapping_incompatible")
    if mapping_state["state"] != "present":
        _issue(issues, mapping_state["reason"])

    def source_intervals(interval):
        if mapping_state["state"] != "present":
            return None
        rows = map_interval(mapping, *interval)
        return reverse_path(rows) if rows and request["strand"] == "-" else rows

    product_sequence = native.get("sequence")
    product_state = _state()
    if product_sequence is None:
        product_state = _state("missing", "native_product_missing")
    elif not isinstance(product_sequence, str):
        product_state = _state("incompatible", "native_product_not_string")
        product_sequence = None
    elif len(product_sequence) != geometry["expected_output_symbol_count"]:
        product_state = _state("incomplete" if len(product_sequence) < geometry["expected_output_symbol_count"]
            else "incompatible", "native_product_length_conflict")
    if product_state["state"] != "present":
        _issue(issues, product_state["reason"])
    observed = {"output_symbol_count": None, "amino_acid_symbol_count": None,
        "internal_stop_count": None, "terminal_stop_symbol_count": None,
        "ambiguous_output_symbol_count": None, "invalid_output_symbol_count": None}
    if product_sequence is not None:
        observed.update(output_symbol_count=len(product_sequence),
            amino_acid_symbol_count=sum(c in _AA | _AMBIGUOUS_AA for c in product_sequence),
            internal_stop_count=product_sequence[:-1].count("*"),
            terminal_stop_symbol_count=int(product_sequence.endswith("*")),
            ambiguous_output_symbol_count=sum(c in _AMBIGUOUS_AA for c in product_sequence),
            invalid_output_symbol_count=sum(c not in _AA | _AMBIGUOUS_AA | {"*"} for c in product_sequence))
        checks["internal_stop_positions"] = _native_check(native, "internal_stop_positions",
            [i for i, c in enumerate(product_sequence[:-1]) if c == "*"], issues)
        checks["terminal_stop"] = _native_check(native, "terminal_stop", product_sequence.endswith("*"), issues)
        if observed["invalid_output_symbol_count"]:
            _issue(issues, "invalid_product_symbols", count=observed["invalid_output_symbol_count"])
    normalized = sequence[request["start"]:request["end"]].upper().replace("U", "T")
    if request["strand"] == "-":
        normalized = normalized.translate(_COMPLEMENT)[::-1]
    if set(sequence.upper().replace("U", "T")) - _DNA.keys():
        _issue(issues, "invalid_nucleotide_symbols_in_supplied_input")
    count = geometry["translated_codon_count"]
    rows = []
    for index in range(count):
        omitted = bool(request["cds"] and index == count - 1)
        role = "omitted_terminal_stop" if omitted else "cds_start" if request["cds"] and index == 0 else "ordinary"
        offset = request["frame"] + index * 3
        codon = normalized[offset:offset+3]
        interval = ([request["start"]+offset, request["start"]+offset+3] if request["strand"] == "+"
                    else [request["end"]-offset-3, request["end"]-offset])
        output_position = None if omitted else index
        symbol = (product_sequence[index] if not omitted and product_sequence is not None
                  and index < len(product_sequence) else None)
        operands = _codon_operands(codon, table, role=role, cds=request["cds"])
        reason = operands["reason"]
        if settings_state["state"] != "present":
            compatibility, reason = "unknown", "native_settings_unverified"
        elif product_state["state"] != "present":
            compatibility, reason = "unknown", "native_product_correspondence_unverified"
        elif reason in {"cds_first_codon_is_not_a_start", "cds_terminal_codon_is_not_a_stop", "cds_internal_stop_forbidden"}:
            compatibility = "incompatible"
        elif reason is not None:
            compatibility = "unknown"
        else:
            matches = operands["expected_terminal_omission"] if omitted else operands["expected_symbol"] == symbol
            compatibility = "compatible" if matches else "incompatible"
            if not matches:
                reason = "product_symbol_disagrees_with_codon"
        if compatibility != "compatible":
            _issue(issues, reason or "codon_compatibility_unknown", codon_index=index)
        rows.append({"codon_index": index, "output_position": output_position, "role": role,
            "codon": codon, "parent_symbols": sequence[interval[0]:interval[1]], "product_symbol": symbol,
            "parent_interval": interval, "parent_subject_ref": subject_ref, "strand": request["strand"],
            "original_source_intervals": source_intervals(interval),
            "ambiguous": bool(set(codon) - set("ACGT")) if not set(codon) - _DNA.keys() else None,
            "compatibility": compatibility, "compatibility_reason": reason, "table_operands": operands})
    geometry["frame_skipped_source_intervals"] = source_intervals(geometry["frame_skipped_interval"])
    geometry["trailing_source_intervals"] = source_intervals(geometry["trailing_interval"])
    return {"geometry": geometry, "observed": observed, "codons": rows,
        "native_checks": checks, "component_status": {"geometry": geometry_state,
        "settings": settings_state, "product": product_state, "genetic_code": table_state,
        "parent_mapping": mapping_state}, "issues": issues}


def build_translation_sheet(native, *, input_sequence, subject_ref, parent_mapping, request, genetic_code=None):
    """Retain exact supplied operands and populate source-bound numerical cells."""
    operands = _json_copy({"native_result": native, "input_sequence": input_sequence,
        "subject_ref": subject_ref, "parent_mapping": parent_mapping, "request": request, "genetic_code": genetic_code})
    populated = _populate(native=operands["native_result"], sequence=operands["input_sequence"],
        subject_ref=operands["subject_ref"], mapping=operands["parent_mapping"],
        request=operands["request"], genetic_code=operands["genetic_code"])
    return {"schema": SHEET_SCHEMA, **operands, **populated,
        "normalization": "uppercase_then_U_to_T_then_selected_reverse_complement_then_frame",
        "coordinate_system": "zero_based_half_open",
        "status": "partial" if populated["issues"] else "complete"}


def _definitions():
    fields = {
        "input_length_nt": ("input_sequence", "len(input_sequence)", "nt", "entire supplied nucleotide string"),
        "selected_length_nt": ("request.start,end", "end-start", "nt", "requested interval"),
        "frame_skipped_nt": ("request.frame; native frame/orientation/interval checks", "frame", "nt", "oriented interval prefix"),
        "translated_length_nt": ("geometry; native frame/orientation/interval checks", "3*floor((end-start-frame)/3)", "nt", "complete selected codons, including an omitted CDS terminal stop"),
        "trailing_untranslated_bases": ("geometry; native frame/orientation/interval checks", "(end-start-frame)%3", "nt", "oriented interval suffix"),
        "translated_codon_count": ("geometry; native frame/orientation/interval checks", "translated_length_nt/3", "codons", "complete selected codons, including omitted CDS terminal stop"),
        "output_symbol_count": ("native_result.sequence", "len(sequence)", "product_symbols", "all retained product symbols including '*'"),
        "amino_acid_symbol_count": ("native_result.sequence", "count uppercase standard, U, O, B, X, Z or J symbols", "aa_symbols", "retained product; '*' and invalid symbols excluded"),
        "internal_stop_count": ("native_result.sequence", "count '*' before final returned symbol", "stop_symbols", "retained product excluding its last symbol"),
        "terminal_stop_symbol_count": ("native_result.sequence", "1 if product ends with '*' else 0", "stop_symbols", "last retained product symbol"),
        "omitted_terminal_stop_codon_count": ("request.cds; native checks; codons[-1]; product length", "1 for a native CDS-declared omitted terminal codon; 0 for non-CDS; null for contradiction", "codons", "terminal selected codon; table validation separately reported"),
        "ambiguous_codon_count": ("codons[].codon", "count codons containing symbols outside A,C,G,T after U-to-T normalization", "codons", "all complete selected codons, including omitted stop"),
        "ambiguous_output_symbol_count": ("native_result.sequence", "count B,X,Z,J", "aa_symbols", "all retained product symbols"),
        "mapped_output_symbol_count": ("codons[].original_source_intervals; native geometry/CDS/product-length checks", "count observed output symbols with a complete declared source path", "product_symbols", "returned symbols; omitted stop excluded; null without valid explicit ancestry"),
        "compatible_codon_count": ("codons[].compatibility", "count compatible", "codons", "all complete selected codons including omitted terminal stop"),
        "incompatible_codon_count": ("codons[].compatibility", "count incompatible", "codons", "same complete selected codon population"),
        "unknown_codon_count": ("codons[].compatibility", "count unknown or missing/corrupt saved rows", "codons", "same complete selected codon population"),
        "selected_input_fraction": ("selected_length_nt,input_length_nt", "selected_length_nt/input_length_nt", "fraction", "entire supplied input nucleotide string"),
        "selected_input_fraction_denominator_nt": ("input_sequence", "len(input_sequence)", "nt", "entire supplied input nucleotide string"),
        "invalid_output_symbol_count": ("native_result.sequence", "count symbols outside uppercase amino-acid alphabet and '*'", "product_symbols", "all retained product symbols"),
    }
    result = {name: {"inputs": inputs, "calculation": formula, "unit": unit, "population": population,
        "range": "[0,1]" if name == "selected_input_fraction" else "nonnegative integer",
        "measurement_kind": "derived_fraction" if name == "selected_input_fraction" else "deterministic_count",
        "missing_behavior": "null with component_status; valid independent counts survive", "uncertainty": None}
        for name, (inputs, formula, unit, population) in fields.items()}
    result["codon_validation"] = {"calculation": "Finite IUPAC expansion of each retained codon against frozen reference entries; forward entries take precedence over stop membership internally; CDS first codon requires all expansions be starts and M; CDS last requires all expansions be stops and omission. Pure stop/AA ambiguity yields X; D/N -> B, E/Q -> Z, I/L -> J, otherwise X.",
        "meaning": "deterministic compatibility of transformation, not biological confidence",
        "coordinate_system": "zero_based_half_open", "uncertainty": None}
    result["combinations"] = {"selected_input_fraction": ["selected_length_nt", "input_length_nt"],
        "combined_annotation_score": None}
    return result


def calculate_translation_scores(sheet):
    """Compute numerical components from saved cells, rejecting changed operands.

    Saved normalization is checked by direct symbol/reference/coordinate
    inspection. No translation, present-day genetic table, I/O or Store lookup
    is used. Corrupt saved cells become unavailable, without repairing history.
    """
    saved = _json_copy(sheet)
    required = {"schema", "native_result", "input_sequence", "subject_ref", "parent_mapping", "request", "genetic_code"}
    if not isinstance(saved, dict) or saved.get("schema") != SHEET_SCHEMA or not required <= saved.keys():
        raise ValueError("translation_saved_sheet_required")
    expected = _populate(native=saved["native_result"], sequence=saved["input_sequence"],
        subject_ref=saved["subject_ref"], mapping=saved["parent_mapping"],
        request=saved["request"], genetic_code=saved["genetic_code"])
    issues = deepcopy(expected["issues"])
    statuses = deepcopy(expected["component_status"])
    for section in ("native_checks", "component_status", "issues"):
        if not _equal(saved.get(section), expected[section]):
            _issue(issues, "saved_metadata_conflicts_with_operands", field=section)
    geometry, observed = {}, {}
    for section, destination in (("geometry", geometry), ("observed", observed)):
        supplied = saved.get(section)
        for key, value in expected[section].items():
            valid = isinstance(supplied, dict) and key in supplied and _equal(supplied[key], value)
            destination[key] = supplied[key] if valid else None
            if not valid:
                _issue(issues, "saved_cell_conflicts_with_operands", field=f"{section}.{key}")
                statuses[key] = _state("incompatible", "saved_cell_conflicts_with_operands")
    rows, good_rows = [], []
    supplied_rows = saved.get("codons")
    for index, expected_row in enumerate(expected["codons"]):
        row = supplied_rows[index] if isinstance(supplied_rows, list) and index < len(supplied_rows) else None
        valid = _equal(row, expected_row)
        good_rows.append(valid)
        if valid:
            rows.append(deepcopy(row))
        else:
            # Retain actual saved data alongside explicit unavailable calculated
            # fields. Do not overwrite a corrupt row with a reconstructed answer.
            rows.append({"codon_index": index, "saved_row": row, "compatibility": "unknown",
                "compatibility_reason": "saved_codon_row_conflicts_with_operands",
                "original_source_intervals": None, "output_position": None})
            _issue(issues, "saved_codon_row_conflicts_with_operands", codon_index=index)
    if not isinstance(supplied_rows, list) or len(supplied_rows) != len(expected["codons"]):
        _issue(issues, "saved_codon_population_incomplete_or_incompatible")
    values = {key: geometry[key] for key in ("input_length_nt", "selected_length_nt", "frame_skipped_nt",
        "translated_length_nt", "trailing_untranslated_bases", "translated_codon_count")}
    values.update(observed)
    if statuses["geometry"]["state"] != "present":
        for key in ("frame_skipped_nt", "translated_length_nt", "trailing_untranslated_bases", "translated_codon_count"):
            values[key] = None
            statuses[key] = statuses["geometry"]
    if expected["native_checks"]["trailing_untranslated_bases"]["state"] != "present":
        values["trailing_untranslated_bases"] = None
        statuses["trailing_untranslated_bases"] = expected["native_checks"]["trailing_untranslated_bases"]
    # Native product symbols are observed even if their length or settings are
    # inconsistent. No prefix coordinate correspondence is guessed from length.
    ambiguity_available = all(good_rows) and all(type(row.get("ambiguous")) is bool for row in rows)
    values["ambiguous_codon_count"] = (sum(row["ambiguous"] for row in rows)
        if ambiguity_available and statuses["geometry"]["state"] == "present" else None)
    if not ambiguity_available:
        statuses["ambiguous_codon_count"] = _state("incompatible", "invalid_or_unavailable_codon_symbols")
    for state in ("compatible", "incompatible", "unknown"):
        values[f"{state}_codon_count"] = sum(row["compatibility"] == state for row in rows)
    mapping_usable = _combined([statuses[k] for k in ("geometry", "product", "parent_mapping")]
        + [expected["native_checks"]["cds"]], "output_source_correspondence_unverified")
    values["mapped_output_symbol_count"] = (sum(row["output_position"] is not None for row in rows)
        if mapping_usable["state"] == "present" and all(good_rows) else None)
    if not all(good_rows):
        mapping_usable = _state("incompatible", "saved_codon_row_conflicts_with_operands")
    statuses["mapped_output_symbol_count"] = mapping_usable
    omission = 0 if not saved["request"]["cds"] else 1
    omission_state = _combined([expected["native_checks"]["cds"], statuses["geometry"]], "terminal_omission_unverified")
    if saved["request"]["cds"]:
        omission_state = _combined([omission_state, statuses["product"]], "terminal_omission_unverified")
        if not good_rows[-1] or rows[-1]["compatibility"] == "incompatible":
            omission_state = _state("incompatible", "terminal_omission_conflicts_with_codon")
    values["omitted_terminal_stop_codon_count"] = omission if omission_state["state"] == "present" else None
    statuses["omitted_terminal_stop_codon_count"] = omission_state
    values["selected_input_fraction_denominator_nt"] = values["input_length_nt"]
    values["selected_input_fraction"] = (values["selected_length_nt"] / values["input_length_nt"]
        if values["selected_length_nt"] is not None and values["input_length_nt"] else None)
    for key, value in values.items():
        if key not in statuses:
            statuses[key] = (_state() if value is not None else
                _state("missing", "required_measurement_unavailable"))
    if not all(good_rows):
        statuses["ambiguous_codon_count"] = _state("incompatible", "saved_codon_row_conflicts_with_operands")
        for key in ("compatible_codon_count", "incompatible_codon_count", "unknown_codon_count"):
            statuses[key] = _state("incomplete", "some_saved_codon_rows_unavailable")
    return {"schema": SCORES_SCHEMA, "status": "partial" if issues else "complete", "summary": values,
        "codons": rows, "component_status": statuses, "issues": issues, "definitions": _definitions()}


def grade_translation(native, *, input_sequence, subject_ref, parent_mapping, request, genetic_code=None):
    sheet = build_translation_sheet(native, input_sequence=input_sequence, subject_ref=subject_ref,
        parent_mapping=parent_mapping, request=request, genetic_code=genetic_code)
    return {"sheet": sheet, "scores": calculate_translation_scores(sheet)}


__all__ = ["SHEET_SCHEMA", "SCORES_SCHEMA", "build_translation_sheet", "calculate_translation_scores", "grade_translation"]
