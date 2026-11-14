"""Inspectable hmmbuild/alimask calculations from saved B1 sheets only.

Counts have their literal sequence/column/interval populations. Fractions use
actual input alignment width or sequence count, never the sum of range lengths.
Source, resaved and model positions are one-based inclusive coordinate systems.
Per-sequence residue ordinal correspondence is kept even when Plan7 moves sites;
a source column may map to several resaved columns. Model probability arrays and
their entropy/KL/mass checks use M1 unchanged, with an explicit background.

The alimask reconstruction mirrors HMMER 3.4 digital semantics for hand, wnone,
wgiven and nonsampled PB. PB's fixed span/.5 rule precedes selected residue-count
fragment marking; the final occupancy accumulators and threshold are float32.
GSC, BLOSUM and PB sampling stay explicit missing calculations. Reconstructing
an established map is a calculation on saved data, never another native run.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import math
import struct

from .hmmalign_inputs import stockholm_digital_checksum
from .hmmer_model_calculations import calculate_hmmer_model_components
from .hmmer_alignment_preparation_data import (
    SCHEMA as SHEET_SCHEMA, MODES, ROW_FIELDS as NATIVE_ROW_FIELDS, annotation, finite, gf_value, model_header,
    selected_alphabet, valid_alignment, _model_map,
)
from .hmmer_model_data import _occurrence_valid

SCHEMA = "hmmer_alignment_preparation_components_v1"
COMPONENT_STATES = frozenset({"present", "missing", "incomplete", "incompatible", "nonfinite", "failed"})
CHECK_STATES = frozenset({"pass", "fail", "unknown", "not_applicable"})
ISSUE_CODES = frozenset({"sheet_invalid", "parameter_invalid", "record_invalid", "association_invalid",
    "input_unavailable", "output_unavailable", "model_components_issue", "rf_missing", "map_unavailable",
    "weighting_unsupported", "pb_sampling_unsupported", "alphabet_missing", "alphabet_incompatible",
    "weight_invalid", "settings_invalid", "alignment_invalid", "range_out_of_bounds", "range_invalid",
    "range_capacity_exceeded", "unsafe_native_range", "mapping_mismatch", "mask_mismatch",
    "mm_invalid", "sequence_membership_mismatch", "sequence_content_mismatch", "source_checksum_mismatch",
    "summary_mismatch", "source_binding_invalid", "resaved_unavailable", "model_map_invalid"})
CHECK_CODES = frozenset({"artifact_binding", "source_geometry", "output_geometry", "association",
    "summary_counts", "summary_eff_nseq", "summary_relative_entropy", "source_checksum", "model_map",
    "rf_model_length", "sequence_membership", "sequence_content", "alignment_width", "mask_annotation",
    "requested_ranges", "range_capacity", "native_mapping", "model_components", "parameter_valid",
    "input_population_processed", "output_symbol_changes", "fragment_marking", "alphabet"})
COMPONENT_FIELDS = frozenset({"input_sequence_count", "input_column_count", "rf_consensus_count",
    "resaved_sequence_count", "resaved_column_count", "model_length", "model_alignment_fraction",
    "effective_sequence_count", "effective_input_sequence_ratio", "native_relative_entropy",
    "mean_match_entropy", "mean_match_relative_entropy", "requested_interval_count", "requested_union_count",
    "actual_masked_count", "newly_masked_count", "removed_masked_count", "retained_masked_count",
    "masked_fraction", "input_masked_count", "input_alignment_count", "processed_alignment_count",
    "unprocessed_alignment_count", "mapped_model_position_count", "native_mapping_row_count"})
ROW_FIELDS = frozenset({"record_key", "kind", "source_record_key", "output_record_key", "model_record_key",
    "summary_record_key", "components", "coordinates", "model_components", "source_symbol_counts", "intervals",
    "input_mm", "output_mm", "reconstruction", "native_mappings"})
DEFAULT_PARAMETERS = {"background": None, "probability_tolerance": 1e-4,
                      "summary_rounding_tolerance": {"eff_nseq": 0.005001, "re_per_position": 0.0006}}
_GAPS = frozenset("-._")


def _component(value=None, *, state=None, unit="dimensionless", inputs=()):
    state = state or ("missing" if value is None else "present")
    assert state in COMPONENT_STATES
    return {"value": value, "state": state, "unit": unit, "inputs": deepcopy(list(inputs))}


def _problem(code, *, record_key=None, field=None, **details):
    assert code in ISSUE_CODES
    return {"code": code, "stage": "calculation", "record_key": record_key, "field": field, "details": details}


def _check(result, code, state, *, record_key=None, inputs=(), **details):
    assert code in CHECK_CODES and state in CHECK_STATES
    result["checks"].append({"code": code, "state": state, "record_key": record_key,
                             "inputs": deepcopy(list(inputs)), "details": details})


def _f32(number):
    return struct.unpack("=f", struct.pack("=f", number))[0]


def _digitize(sequence, alphabet):
    text = sequence.upper()
    if alphabet in {"DNA", "RNA"}:
        text = text.replace("X", "N").replace("I", "A")
        text = text.replace("T", "U") if alphabet == "RNA" else text.replace("U", "T")
    return "".join("-" if symbol in _GAPS else symbol for symbol in text)


def reconstruct_alimask_model_map(alignment, *, settings):
    """Return full deterministic map, weights, fragment strings and occupancy.

    ``alignment`` is one B1 kind=alignment record with occurrence-keyed rows,
    or a shape-compatible record produced from the same pure Stockholm reader.
    ``settings`` contains actual native flags/resolved values. State is present,
    missing, incomplete or incompatible; a missing map is None, an observed
    empty map is []. Issue codes are closed. Output does not authorize execution.
    This public port is usable by a producer without importing driver internals.
    """
    key = alignment.get("record_key") if isinstance(alignment, dict) else None
    result = {"state": "missing", "map": None, "basis": None, "weights": None,
              "marked_sequences": None, "column_occupancy": None, "pb_consensus_columns": None, "issues": []}
    def fail(code, state="missing", **details):
        result["state"] = state
        result["issues"].append(_problem(code, record_key=key, **details))
        return result
    if not valid_alignment(alignment):
        return fail("alignment_invalid", "incomplete")
    if not isinstance(settings, dict):
        return fail("settings_invalid", "incompatible")
    rows, width = alignment["rows"], alignment["column_count"]
    if settings.get("--hand"):
        rf = annotation(alignment, "RF")
        if rf is None:
            return fail("rf_missing")
        result.update(state="present", map=[i + 1 for i, symbol in enumerate(rf) if symbol not in _GAPS], basis="hand_RF_nongap")
        # Hand MAP is independent of relative weights and fragment symbols.
        return result
    alphabet = selected_alphabet(settings)
    if alphabet is None:
        return fail("alphabet_missing")
    canonical = "ACDEFGHIKLMNPQRSTVWY" if alphabet == "amino" else "ACGU" if alphabet == "RNA" else "ACGT"
    residues = set(canonical + ("BJZOUX" if alphabet == "amino" else "RYMKSWHBVDN"))
    sequences = [_digitize(row["aligned_sequence"], alphabet) for row in rows]
    if any(set(sequence) - residues - {"-", "~", "*"} for sequence in sequences):
        return fail("alphabet_incompatible", "incompatible")
    threshold, fragment_threshold = settings.get("--symfrac", .5), settings.get("--fragthresh", .5)
    if any(not finite(value) or not 0 <= value <= 1 for value in (threshold, fragment_threshold)):
        return fail("settings_invalid", "incompatible")
    weight_modes = [flag for flag in ("--wnone", "--wgiven", "--wpb", "--wgsc", "--wblosum") if settings.get(flag)]
    if len(weight_modes) > 1:
        return fail("settings_invalid", "incompatible")
    method = weight_modes[0] if weight_modes else "--wpb"
    if method in {"--wgsc", "--wblosum"}:
        return fail("weighting_unsupported", weighting=method)
    if method == "--wnone":
        weights = [1.] * len(rows)
    elif method == "--wgiven":
        supplied = [row.get("weight", {}) for row in rows]
        if all(weight.get("state") == "missing" for weight in supplied):
            weights = [1.] * len(rows)  # Easel's actual default when no WT lines exist.
        elif any(weight.get("state") != "present" or not finite(weight.get("value")) or weight["value"] < 0 for weight in supplied):
            return fail("weight_invalid", "incompatible")
        else:
            weights = [weight["value"] for weight in supplied]
    elif len(rows) == 1:
        weights = [1.]
    else:
        if len(rows) > 50000:
            return fail("pb_sampling_unsupported", sequence_count=len(rows))
        # esl_msaweight_PB_adv uses its own defaults, not --fragthresh/--symfrac.
        counts = [Counter() for _ in range(width)]
        minspan = math.ceil(_f32(.5 * _f32(width)))
        for sequence in sequences:
            positions = [i for i, symbol in enumerate(sequence) if symbol in residues]
            left, right = (positions[0], positions[-1]) if positions else (width, -1)
            if right - left + 1 >= minspan:
                left, right = 0, width - 1
            for column in range(left, right + 1):
                counts[column][sequence[column]] += 1
        consensus = []
        for column, counts_at_column in enumerate(counts):
            total = sum(count for symbol, count in counts_at_column.items() if symbol in residues or symbol == "-")
            if total and _f32(_f32(counts_at_column["-"]) / _f32(total)) < .5:
                consensus.append(column)
        if not consensus:
            consensus = list(range(width))
        result["pb_consensus_columns"] = [column + 1 for column in consensus]
        weights = []
        for sequence in sequences:
            value, count = 0., 0
            for column in consensus:
                if sequence[column] in canonical:
                    distinct = sum(counts[column][symbol] > 0 for symbol in canonical)
                    value += 1. / (distinct * counts[column][sequence[column]])
                    count += 1
            weights.append(value / count if count else 0.)
        total = sum(weights)  # Same ordered double accumulation as esl_vec_DSum.
        weights = [weight / total * len(rows) for weight in weights] if total else [1.] * len(rows)
    if any(not finite(weight) or weight < 0 for weight in weights):
        return fail("weight_invalid", "incompatible")
    marked = []
    for sequence in sequences:
        positions = [i for i, symbol in enumerate(sequence) if symbol in residues]
        if len(positions) <= fragment_threshold * width:
            left, right = (positions[0], positions[-1]) if positions else (width, -1)
            sequence = "".join(symbol if left <= i <= right else "~" for i, symbol in enumerate(sequence))
        marked.append(sequence)
    mapping, occupancy = [], []
    for column in range(width):
        r = total = 0.
        try:
            for sequence, weight in zip(marked, weights):
                if sequence[column] in residues:
                    r = _f32(r + weight)
                    total = _f32(total + weight)
                elif sequence[column] == "-":
                    total = _f32(total + weight)
            fraction = _f32(r / total) if total else None
        except (OverflowError, ZeroDivisionError):
            return fail("weight_invalid", "incompatible", field="float32_occupancy")
        is_match = r > 0 and fraction is not None and fraction >= _f32(threshold)
        occupancy.append({"alignment_position": column + 1, "weighted_residue_count": r,
            "weighted_residue_gap_count": total, "weighted_occupancy": fraction,
            "threshold_float32": _f32(threshold), "is_model_position": is_match})
        if is_match:
            mapping.append(column + 1)
    result.update(state="present", map=mapping, basis="fast_" + method[2:],
        weights=[{"record_key": row["record_key"], "weight": weight} for row, weight in zip(rows, weights)],
        marked_sequences=[{"record_key": row["record_key"], "sequence": text} for row, text in zip(rows, marked)],
        column_occupancy=occupancy)
    return result


def _operand(record, field, **extra):
    return {"record_key": record["record_key"], "field": field, **extra}


def _count(record, field, unit):
    if record is None:
        return _component(unit=unit)
    value = len(record["rows"]) if field == "rows" else record.get(field)
    state = "present" if valid_alignment(record) else "incomplete"
    return _component(value if state == "present" else None, state=state, unit=unit, inputs=[_operand(record, field)])


def _ratio(numerator, denominator, *, unit, association=True):
    state = ("incompatible" if not association else "incomplete" if "incomplete" in {numerator["state"], denominator["state"]}
             else "missing" if "missing" in {numerator["state"], denominator["state"]} else "present")
    if any(value["state"] in {"incompatible", "nonfinite", "failed"} for value in (numerator, denominator)):
        state = "incompatible"
    value = None
    if state == "present":
        if denominator["value"] == 0:
            state = "nonfinite"
        else:
            value = numerator["value"] / denominator["value"]
    inputs = [{**item, "role": "numerator"} for item in numerator["inputs"]]
    inputs += [{**item, "role": "denominator"} for item in denominator["inputs"]]
    return _component(value, state=state, unit=unit, inputs=inputs)


def _rf_count(record):
    rf = annotation(record, "RF") if record else None
    return _component(sum(c not in _GAPS for c in rf) if rf is not None else None, unit="RF_consensus_column_count",
                      inputs=[_operand(record, "column_annotations.RF")] if record else [])


def _coordinate_correspondence(source, target, alphabet, result):
    output = {"sequence_membership": "unknown", "sequence_content": "unknown", "sequences": [], "source_to_resaved_columns": None}
    if not valid_alignment(source) or not valid_alignment(target):
        return output
    source_members = [(row["name"], row["occurrence"]) for row in source["rows"]]
    target_members = [(row["name"], row["occurrence"]) for row in target["rows"]]
    membership = source_members == target_members
    output["sequence_membership"] = "pass" if membership else "fail"
    if not membership:
        result["issues"].append(_problem("sequence_membership_mismatch", record_key=source["record_key"]))
        return output
    column_targets = [set() for _ in range(source["column_count"])]
    compatible = True
    for first, second in zip(source["rows"], target["rows"]):
        a, b = first["aligned_sequence"], second["aligned_sequence"]
        positions_a = [i for i, symbol in enumerate(a, 1) if symbol.isascii() and symbol.isalpha()]
        positions_b = [i for i, symbol in enumerate(b, 1) if symbol.isascii() and symbol.isalpha()]
        residues_a = _digitize("".join(a[i - 1] for i in positions_a), alphabet)
        residues_b = _digitize("".join(b[i - 1] for i in positions_b), alphabet)
        same = residues_a == residues_b
        compatible = compatible and same
        correspondence = [{"residue_position": i + 1, "source_alignment_position": x, "resaved_alignment_position": y}
                          for i, (x, y) in enumerate(zip(positions_a, positions_b))] if same else None
        if same:
            for x, y in zip(positions_a, positions_b):
                column_targets[x - 1].add(y)
        output["sequences"].append({"source_record_key": first["record_key"], "output_record_key": second["record_key"],
            "source_sequence": a, "output_sequence": b, "content_state": "pass" if same else "fail",
            "correspondence": correspondence,
            "symbol_changes": [{"alignment_position": i + 1, "input": x, "output": y} for i, (x, y) in enumerate(zip(a, b)) if x != y] if len(a) == len(b) else None})
    output["sequence_content"] = "pass" if compatible else "fail"
    if compatible:
        output["source_to_resaved_columns"] = [{"source_alignment_position": i + 1,
            "resaved_alignment_positions": sorted(values), "state": "unique" if len(values) == 1 else "multiple" if values else "no_residue_correspondence"}
            for i, values in enumerate(column_targets)]
    else:
        result["issues"].append(_problem("sequence_content_mismatch", record_key=source["record_key"]))
    return output


def _base_row(key, kind, source=None):
    return {"record_key": key, "kind": kind, "source_record_key": source["record_key"] if source else None,
        "output_record_key": None, "model_record_key": None, "summary_record_key": None,
        "components": {}, "coordinates": None, "model_components": None, "source_symbol_counts": None,
        "intervals": None, "input_mm": None, "output_mm": None, "reconstruction": None, "native_mappings": None}


def _build(sheet, result, parameters):
    sources = {record["record_key"]: record for record in sheet["input_records"] if record.get("kind") == "alignment"}
    outputs = {record["record_key"]: record for record in sheet["output_records"] if record.get("kind") == "alignment"}
    summaries = {record["record_key"]: record for record in sheet["native_rows"] if record.get("kind") == "build_summary"}
    extraction = sheet["model_extraction"]
    models = {record["record_key"]: record for record in (extraction or {}).get("records", [])}
    calculated = calculate_hmmer_model_components(extraction, background=parameters["background"],
        probability_tolerance=parameters["probability_tolerance"]) if extraction else None
    model_rows = {row["record_key"]: row for row in (calculated or {}).get("rows", [])}
    if calculated:
        for problem in calculated["issues"]:
            result["issues"].append(_problem("model_components_issue", record_key=problem.get("record_key"), cause=problem))
        for check in calculated["checks"]:
            _check(result, "model_components", check["state"], record_key=check.get("record_key"), inputs=check["inputs"], native_check=check)
    settings = sheet["operation"]["settings"]
    for association in sheet["associations"]:
        if association.get("relation") != "build":
            continue
        source, model = sources.get(association.get("source_record_key")), models.get(association.get("model_record_key"))
        summary, transformed = summaries.get(association.get("summary_record_key")), outputs.get(association.get("resaved_record_key"))
        key = association["record_key"]
        row = _base_row(key, "build", source)
        row.update(model_record_key=model["record_key"] if model else None, summary_record_key=summary["record_key"] if summary else None,
                   output_record_key=transformed["record_key"] if transformed else None)
        components = row["components"]
        components.update(input_sequence_count=_count(source, "rows", "sequence_count"),
                          input_column_count=_count(source, "column_count", "alignment_column_count"), rf_consensus_count=_rf_count(source),
                          resaved_sequence_count=_count(transformed, "rows", "sequence_count"),
                          resaved_column_count=_count(transformed, "column_count", "resaved_alignment_column_count"))
        model_values = model_rows.get(model["record_key"]) if model else None
        row["model_components"] = deepcopy(model_values)
        for name, model_name, unit in (("model_length", "declared_length", "match_state_count"),
                ("effective_sequence_count", "effective_sequence_count", "effective_sequence_count"),
                ("mean_match_entropy", "mean_match_entropy", "bit_per_match_position"),
                ("mean_match_relative_entropy", "mean_match_relative_entropy", "bit_per_match_position")):
            components[name] = deepcopy(model_values[model_name]) if model_values else _component(unit=unit)
        compatible = association.get("status") != "conflicting"
        components["model_alignment_fraction"] = _ratio(components["model_length"], components["input_column_count"],
            unit="match_states_per_input_alignment_column", association=compatible)
        components["effective_input_sequence_ratio"] = _ratio(components["effective_sequence_count"], components["input_sequence_count"],
            unit="effective_sequences_per_input_sequence", association=compatible)
        components["native_relative_entropy"] = _component(summary["re_per_position"] if summary and summary["valid"] else None,
            unit="bit_per_match_position", inputs=[_operand(summary, "re_per_position")] if summary else [])
        _check(result, "association", "pass" if association["status"] == "validated" else "fail" if not compatible else "unknown",
               record_key=key, qualifications=deepcopy(association.get("qualifications", {})))
        _check(result, "source_geometry", "pass" if source and valid_alignment(source) else "unknown", record_key=key)
        if source and valid_alignment(source):
            row["source_symbol_counts"] = [{"alignment_position": position + 1, "counts": dict(Counter(r["aligned_sequence"][position] for r in source["rows"])),
                "denominator": len(source["rows"]), "population": "all_source_sequence_rows",
                "record_keys": [r["record_key"] for r in source["rows"]]} for position in range(source["column_count"])]
        native_map = _model_map(model, source["column_count"]) if source and source["column_count"] is not None and model else None
        resaved_rf = annotation(transformed, "RF") if transformed else None
        resaved_map = [i + 1 for i, symbol in enumerate(resaved_rf) if symbol not in _GAPS] if resaved_rf is not None else None
        row["coordinates"] = {"convention": "one_based_inclusive", "model_to_source_alignment": native_map,
                              "model_to_resaved_alignment": resaved_map, "source_resaved": None}
        if source and transformed:
            correspondence = _coordinate_correspondence(source, transformed, model["alphabet"]["kind"] if model else selected_alphabet(settings), result)
            row["coordinates"]["source_resaved"] = correspondence
            _check(result, "sequence_membership", correspondence["sequence_membership"], record_key=key)
            _check(result, "sequence_content", correspondence["sequence_content"], record_key=key)
        elif settings.get("-O") and not association.get("native_single_sequence_matrix"):
            result["issues"].append(_problem("resaved_unavailable", record_key=key))
        map_state = "pass" if native_map is not None else "fail" if model and model["flags"].get("MAP") else "not_applicable"
        _check(result, "model_map", map_state, record_key=key)
        rf = annotation(source, "RF") if source else None
        hand_map = [i + 1 for i, symbol in enumerate(rf) if symbol not in _GAPS] if rf is not None else None
        if settings.get("--hand") and model and not association.get("native_single_sequence_matrix"):
            _check(result, "rf_model_length", "unknown" if hand_map is None else "pass" if native_map == hand_map else "fail", record_key=key)
            if hand_map is None:
                result["issues"].append(_problem("rf_missing", record_key=key))
        if source and model and valid_alignment(source) and model.get("checksum") is not None:
            try:
                checksum = stockholm_digital_checksum([r["aligned_sequence"] for r in source["rows"]], alphabet=model["alphabet"]["kind"])
                equal = checksum == model["checksum"]
                _check(result, "source_checksum", "pass" if equal else "fail", record_key=key, calculated=checksum, native=model["checksum"])
                if not equal:
                    result["issues"].append(_problem("source_checksum_mismatch", record_key=key))
            except ValueError:
                _check(result, "source_checksum", "unknown", record_key=key)
        else:
            _check(result, "source_checksum", "not_applicable" if model and association.get("native_single_sequence_matrix") else "unknown", record_key=key)
        if summary and model and source:
            equal = summary["valid"] and summary["nseq"] == len(source["rows"]) == model["sequence_count"] and summary["alen"] == source["column_count"] and summary["mlen"] == model["length"]
            _check(result, "summary_counts", "pass" if equal else "fail", record_key=key)
            for name, native_field, calculated_field in (("summary_eff_nseq", "eff_nseq", "effective_sequence_count"),
                    ("summary_relative_entropy", "re_per_position", "mean_match_relative_entropy")):
                tolerance = parameters["summary_rounding_tolerance"].get(native_field) if isinstance(parameters["summary_rounding_tolerance"], dict) else None
                component = components[calculated_field]
                native_value = summary[native_field]
                state = "unknown"
                difference = None
                if component["state"] == "present" and finite(native_value) and finite(tolerance) and tolerance >= 0:
                    difference = component["value"] - native_value
                    state = "pass" if abs(difference) <= tolerance else "fail"
                    if state == "fail":
                        result["issues"].append(_problem("summary_mismatch", record_key=key, field=native_field))
                _check(result, name, state, record_key=key, difference=difference, tolerance=tolerance,
                       inputs=component["inputs"] + [_operand(summary, native_field)])
        result["rows"].append(row)


def _mm(record, *, absent_is_empty=False):
    if record is None:
        return None, "missing"
    if not valid_alignment(record):
        return None, "incomplete"
    raw = annotation(record, "MM")
    if raw is None:
        return (set(), "present") if absent_is_empty and "MM" not in record["column_annotations"] else (None, "missing")
    if any(symbol not in "m." for symbol in raw) or len(raw) != record["column_count"]:
        return None, "incompatible"
    return {i + 1 for i, symbol in enumerate(raw) if symbol == "m"}, "present"


def _mask(sheet, result):
    sources = [record for record in sheet["input_records"] if record.get("kind") == "alignment"]
    associations = [item for item in sheet["associations"] if item.get("relation") == "mask"]
    source = next((record for record in sources if associations and record["record_key"] == associations[0]["source_record_key"]), None)
    outputs = [record for record in sheet["output_records"] if record.get("kind") == "alignment"]
    target = next((record for record in outputs if associations and record["record_key"] == associations[0]["output_record_key"]), None)
    key = source["record_key"] if source else "unavailable#alignment/0"
    row = _base_row(key, "mask" if sheet["operation"]["mode"] in {"mask_alignment", "mask_model"} else "mapping", source)
    row["output_record_key"] = target["record_key"] if target else None
    components, settings, mode = row["components"], sheet["operation"]["settings"], sheet["operation"]["mode"]
    components.update(input_sequence_count=_count(source, "rows", "sequence_count"),
        input_column_count=_count(source, "column_count", "alignment_column_count"), rf_consensus_count=_rf_count(source))
    populations = [p for p in sheet["native_rows"] if p.get("kind") == "population" and any(
        a["occurrence_id"] == p["occurrence_id"] and a["direction"] == "input" and a["role"] == "alignment" for a in sheet["artifact_occurrences"])]
    count = populations[0]["decoded_count"] if len(populations) == 1 else None
    population_inputs = [_operand(populations[0], "decoded_count")] if len(populations) == 1 else []
    components["input_alignment_count"] = _component(count, state="missing" if count is None else "present" if populations[0]["complete"] else "incomplete",
        unit="decoded_alignment_record_count", inputs=population_inputs)
    _check(result, "source_geometry", "pass" if valid_alignment(source) else "unknown", record_key=key)
    requests = [deepcopy(record) for record in sheet["native_rows"] if record.get("kind") == "requested_interval"]
    mappings = [deepcopy(record) for record in sheet["native_rows"] if record.get("kind") == "mapping"]
    processed = source is not None and (valid_alignment(target) or bool(mappings) and all(item["valid"] for item in mappings))
    processed_inputs = ([{"record_key": target["record_key"], "field": "complete"}] if target else
                        [{"record_key": item["record_key"], "field": "valid"} for item in mappings])
    components["processed_alignment_count"] = _component(1 if processed else None, unit="output_validated_alignment_record_count", inputs=processed_inputs)
    components["unprocessed_alignment_count"] = _component(max(0, count - 1) if count is not None and processed else None,
        state="incomplete" if count is not None and processed and populations[0]["state"] == "partial" else None,
        unit="decoded_unprocessed_alignment_record_count", inputs=population_inputs + processed_inputs)
    _check(result, "input_population_processed", "unknown" if count is None or not processed else "pass" if count == 1 else "fail", record_key=key)
    row["native_mappings"] = mappings
    components["requested_interval_count"] = _component(len(requests), unit="request_interval_count", inputs=[{"field": "native_rows.requested_interval"}])
    mapping_artifacts = [a for a in sheet["artifact_occurrences"] if a["direction"] == "output" and a["role"] == "stdout"]
    mapping_present = len(mapping_artifacts) == 1 and mode in {"model_to_alignment", "alignment_to_model"}
    mapping_invalid = any(i["code"] in {"mapping_header_missing", "mapping_header_invalid", "mapping_row_invalid"} for i in sheet["issues"])
    components["native_mapping_row_count"] = _component(len(mappings) if mapping_present else None,
        state="incomplete" if mapping_present and mapping_invalid else None, unit="decoded_mapping_row_count",
        inputs=[{"occurrence_id": a["occurrence_id"], "field": "native_rows.mapping"} for a in mapping_artifacts])
    reconstruction = reconstruct_alimask_model_map(source, settings=settings) if mode != "mask_alignment" else None
    row["reconstruction"] = reconstruction
    if reconstruction:
        result["issues"].extend(reconstruction["issues"])
    mapping = reconstruction["map"] if reconstruction else None
    components["mapped_model_position_count"] = _component(len(mapping) if mapping is not None else None,
        state=reconstruction["state"] if reconstruction else "missing", unit="model_position_count",
        inputs=([_operand(source, "rows"), _operand(source, "column_annotations.RF"), {"field": "operation.settings"}] if source else []))
    width = source["column_count"] if valid_alignment(source) else None
    intervals, union, ranges_valid = [], set(), bool(requests) and len(requests) <= 100
    capacity_state = "pass" if len(requests) <= 100 else "fail"
    _check(result, "range_capacity", capacity_state, record_key=key, capacity=100, actual=len(requests))
    if len(requests) > 100:
        result["issues"].append(_problem("range_capacity_exceeded", record_key=key))
    unknown_range = width is None or mode in {"mask_model", "model_to_alignment"} and mapping is None
    for request in requests:
        start, end = request["start"], request["end"]
        bound = len(mapping) if mode in {"mask_model", "model_to_alignment"} and mapping is not None else width if mode in {"mask_alignment", "alignment_to_model"} else None
        state, first, last = "missing", None, None
        if not request["valid"]:
            state, ranges_valid = "incompatible", False
            result["issues"].append(_problem("range_invalid", record_key=request["record_key"]))
        elif bound is not None and end > bound:
            state, ranges_valid = "incompatible", False
            result["issues"].append(_problem("range_out_of_bounds", record_key=request["record_key"], bound=bound))
        elif bound is not None:
            state = "present"
            if mode in {"mask_model", "model_to_alignment"}:
                first, last = mapping[start - 1], mapping[end - 1]
            else:
                first, last = start, end
            if mode == "alignment_to_model" and mapping is not None and (not mapping or start > mapping[-1]):
                result["issues"].append(_problem("unsafe_native_range", record_key=request["record_key"], last_match=mapping[-1] if mapping else None))
        if first is not None and mode in {"mask_alignment", "mask_model"}:
            union.update(range(first, last + 1))
        interval = {"request_record_key": request["record_key"], "request_ordinal": request["request_ordinal"],
            "requested_start": start, "requested_end": end, "requested_coordinate_system": request["coordinate_system"],
            "alignment_start": first, "alignment_end": last, "state": state,
            "inclusive_span": _component(last - first + 1 if first is not None else None, state=state, unit="alignment_column_count",
                inputs=[_operand(request, "start"), _operand(request, "end"), {"record_key": key, "field": "reconstruction.map"}])}
        native = next((item for item in mappings if item["request_ordinal"] == request["request_ordinal"]), None)
        for label, first_field, last_field, coordinate in (
                ("returned_source_span", "returned_source_start", "returned_source_end", request["coordinate_system"]),
                ("returned_target_span", "target_start", "target_end", "alignment" if request["coordinate_system"] == "model" else "model")):
            known = native is not None and native["valid"] and native[first_field] is not None and native[last_field] is not None
            interval[label] = _component(native[last_field] - native[first_field] + 1 if known else None,
                state="incompatible" if native is not None and not native["valid"] else None,
                unit="alignment_column_count" if coordinate == "alignment" else "model_position_count",
                inputs=[_operand(native, first_field), _operand(native, last_field), _operand(native, "native_state")] if native else [])
        intervals.append(interval)
    row["intervals"] = intervals
    _check(result, "requested_ranges", "fail" if not ranges_valid else "unknown" if unknown_range else "pass", record_key=key)
    if mode in {"model_to_alignment", "alignment_to_model"}:
        _verify_mapping(requests, mappings, mapping, mode, ranges_valid, result, key)
        components["requested_union_count"] = _component(unit="alignment_column_count")
        result["rows"].append(row)
        return
    union_state = "incompatible" if not ranges_valid else "missing" if unknown_range else "present"
    components["requested_union_count"] = _component(len(union) if union_state == "present" else None,
        state=union_state, unit="distinct_alignment_column_count", inputs=[{"field": "intervals", "population": "union_inclusive_alignment_spans"}])
    old, old_state = _mm(source, absent_is_empty=True)
    actual, actual_state = _mm(target)
    row["input_mm"], row["output_mm"] = annotation(source, "MM") if source else None, annotation(target, "MM") if target else None
    old_inputs = [_operand(source, "column_annotations.MM", absent_annotation_means="empty_mask")] if source else []
    actual_inputs = [_operand(target, "column_annotations.MM")] if target else []
    components["input_masked_count"] = _component(len(old) if old is not None else None, state=old_state, unit="alignment_column_count", inputs=old_inputs)
    components["actual_masked_count"] = _component(len(actual) if actual is not None else None, state=actual_state, unit="alignment_column_count", inputs=actual_inputs)
    joint_state = "present" if old is not None and actual is not None else "incompatible" if "incompatible" in {old_state, actual_state} else "incomplete" if "incomplete" in {old_state, actual_state} else "missing"
    if source and target and source["column_count"] != target["column_count"]:
        joint_state = "incompatible"
    for name, values in (("newly_masked_count", actual - old if joint_state == "present" else None),
                         ("removed_masked_count", old - actual if joint_state == "present" else None),
                         ("retained_masked_count", actual & old if joint_state == "present" else None)):
        components[name] = _component(len(values) if values is not None else None, state=joint_state, unit="alignment_column_count",
                                     inputs=old_inputs + actual_inputs)
    components["masked_fraction"] = _ratio(components["actual_masked_count"], components["input_column_count"],
        unit="masked_columns_per_input_alignment_column", association=joint_state != "incompatible")
    expected = union | old if old is not None and settings.get("--appendmask") else union
    mask_check = "unknown"
    if union_state == "present" and actual is not None and (not settings.get("--appendmask") or old is not None):
        mask_check = "pass" if actual == expected and joint_state == "present" else "fail"
        if mask_check == "fail":
            result["issues"].append(_problem("mask_mismatch", record_key=key))
    _check(result, "mask_annotation", mask_check, record_key=key,
        actual_columns=sorted(actual) if actual is not None else None, expected_columns=sorted(expected) if union_state == "present" else None)
    if source and target:
        equal_width = source["column_count"] == target["column_count"]
        _check(result, "alignment_width", "pass" if equal_width else "fail", record_key=key)
        coordinates = _coordinate_correspondence(source, target, selected_alphabet(settings), result)
        row["coordinates"] = {"convention": "one_based_inclusive", "model_to_source_alignment": mapping, "source_output": coordinates}
        _check(result, "sequence_membership", coordinates["sequence_membership"], record_key=key)
        _check(result, "sequence_content", coordinates["sequence_content"], record_key=key)
        _check(result, "output_geometry", "pass" if valid_alignment(target) else "fail", record_key=key)
        # Native case/gap normalization and actual fragment changes remain visible.
        changed = any(item["source_sequence"] != item["output_sequence"] for item in coordinates["sequences"])
        _check(result, "output_symbol_changes", "pass" if not changed else "fail", record_key=key, changed=changed)
        if reconstruction and reconstruction["marked_sequences"] is not None and coordinates["sequence_membership"] == "pass":
            expected_strings = [item["sequence"] for item in reconstruction["marked_sequences"]]
            observed_strings = [_digitize(item["aligned_sequence"], selected_alphabet(settings)) for item in target["rows"]]
            _check(result, "fragment_marking", "pass" if expected_strings == observed_strings else "fail", record_key=key)
    result["rows"].append(row)


def _verify_mapping(requests, rows, mapping, mode, valid, result, key):
    if mapping is None:
        _check(result, "native_mapping", "unknown", record_key=key)
        return
    correct = valid and len(rows) == len(requests)
    for request, row in zip(requests, rows):
        start, end = request["start"], request["end"]
        if not request["valid"] or not row["valid"]:
            correct = False
            continue
        if mode == "model_to_alignment":
            if end > len(mapping):
                correct = False
                continue
            expected = (start, end, mapping[start - 1], mapping[end - 1], "mapped")
        else:
            positions = [(index + 1, column) for index, column in enumerate(mapping) if start <= column <= end]
            expected = (positions[0][1], positions[-1][1], positions[0][0], positions[-1][0], "mapped") if positions else (start, end, None, None, "no_map")
            if not mapping or start > mapping[-1]:
                correct = False  # Native memory overrun has no validated no-map result.
        observed = tuple(row[field] for field in ("returned_source_start", "returned_source_end", "target_start", "target_end", "native_state"))
        correct = correct and expected == observed
    _check(result, "native_mapping", "pass" if correct else "fail", record_key=key)
    if not correct:
        result["issues"].append(_problem("mapping_mismatch", record_key=key))


def _saved_sheet_shape(sheet):
    """Check saved operand identities and relationships without resolving refs."""
    if (not isinstance(sheet, dict) or sheet.get("schema") != SHEET_SCHEMA
            or any(not isinstance(sheet.get(field), list) for field in ("artifact_occurrences", "input_records", "output_records", "native_rows", "associations", "issues"))
            or not isinstance(sheet.get("operation"), dict)):
        return False
    operation = sheet["operation"]
    if (set(operation) != {"program", "mode", "engine_version", "settings"}
            or not isinstance(operation["program"], str) or operation["program"] not in MODES
            or not isinstance(operation["mode"], str) or operation["mode"] not in MODES[operation["program"]]
            or not isinstance(operation["settings"], dict)):
        return False
    occurrences = {}
    for occurrence in sheet["artifact_occurrences"]:
        if not _occurrence_valid(occurrence) or occurrence["occurrence_id"] in occurrences:
            return False
        occurrences[occurrence["occurrence_id"]] = occurrence
    keys, typed_keys = set(), {"input_alignment": set(), "output_alignment": set(), "model": set(), "build_summary": set()}
    for direction, records in (("input", sheet["input_records"]), ("output", sheet["output_records"])):
        for record in records:
            if not isinstance(record, dict) or record.get("kind") not in {"alignment", "model"}:
                return False
            key, oid = record.get("record_key"), record.get("occurrence_id")
            if not isinstance(key, str) or key in keys or oid not in occurrences:
                return False
            keys.add(key)
            typed_keys[direction + "_alignment" if record["kind"] == "alignment" else "model"].add(key)
            occurrence = occurrences[oid]
            if occurrence["direction"] != direction and not any(i.get("code") == "occurrence_role_mismatch" and i.get("occurrence_id") == oid for i in sheet["issues"]):
                return False
            locator = record.get("locator")
            if not isinstance(locator, dict) or locator.get("artifact_ref") != occurrence["artifact_ref"]:
                return False
            ordinal = locator.get("record_ordinal")
            if type(ordinal) is not int or key != oid + "#" + record["kind"] + "/" + str(ordinal):
                return False
            if record["kind"] == "alignment":
                if (not isinstance(record.get("rows"), list) or not isinstance(record.get("column_annotations"), dict)
                        or not isinstance(record.get("original_events"), list) or not isinstance(record.get("issues"), list)
                        or type(record.get("complete")) is not bool or type(record.get("header_valid")) is not bool
                        or record.get("column_count") is not None and (type(record["column_count"]) is not int or record["column_count"] < 0)):
                    return False
                for index, row in enumerate(record["rows"]):
                    if (not isinstance(row, dict) or row.get("record_key") != key + "/sequence/" + str(index)
                            or not isinstance(row.get("aligned_sequence"), str) or not isinstance(row.get("name"), str)
                            or type(row.get("occurrence")) is not int
                            or any(type(row.get(flag)) is not bool for flag in ("geometry_valid", "symbols_valid", "identity_unambiguous"))
                            or row["geometry_valid"] and len(row["aligned_sequence"]) != record["column_count"]):
                        return False
                for item in record["column_annotations"].values():
                    if (not isinstance(item, dict) or not isinstance(item.get("text"), str) or type(item.get("valid")) is not bool
                            or item["valid"] and len(item["text"]) != record["column_count"]):
                        return False
    for row in sheet["native_rows"]:
        if not isinstance(row, dict) or row.get("kind") not in NATIVE_ROW_FIELDS or set(row) != NATIVE_ROW_FIELDS[row["kind"]]:
            return False
        if row["kind"] != "requested_interval" and row.get("occurrence_id") not in occurrences:
            return False
        if row["record_key"] in keys:
            return False
        keys.add(row["record_key"])
        if row["kind"] == "build_summary":
            typed_keys["build_summary"].add(row["record_key"])
    extraction = sheet.get("model_extraction")
    if extraction is not None:
        if not isinstance(extraction, dict) or not isinstance(extraction.get("occurrence"), dict):
            return False
        if occurrences.get(extraction["occurrence"].get("occurrence_id")) != extraction["occurrence"]:
            return False
    for association in sheet["associations"]:
        if not isinstance(association, dict) or association.get("relation") not in {"build", "mask", "unprocessed"}:
            return False
        if association.get("record_key") not in typed_keys["input_alignment"] | typed_keys["model"]:
            return False
        if association["relation"] == "build":
            if (association.get("status") not in {"validated", "conflicting", "unresolved"}
                    or not isinstance(association.get("qualifications"), dict)
                    or type(association.get("native_single_sequence_matrix")) is not bool):
                return False
        elif association.get("status") not in {"selected_first_record", "unprocessed"}:
            return False
        for field, kind in (("source_record_key", "input_alignment"), ("summary_record_key", "build_summary"),
                ("model_record_key", "model"), ("resaved_record_key", "output_alignment"), ("output_record_key", "output_alignment")):
            if association.get(field) is not None and association[field] not in typed_keys[kind]:
                return False
    return all(isinstance(problem, dict) and isinstance(problem.get("code"), str) for problem in sheet["issues"])


def calculate_hmmer_alignment_preparation_components(sheet, *, parameters=None):
    """Recalculate a saved sheet with explicit tolerances/background; no I/O."""
    selected = deepcopy(DEFAULT_PARAMETERS)
    invalid_parameters = parameters is not None and (not isinstance(parameters, dict) or bool(set(parameters) - set(selected)))
    if isinstance(parameters, dict):
        selected.update(deepcopy(parameters))
    result = {"schema": SCHEMA, "operation": deepcopy(sheet.get("operation")) if isinstance(sheet, dict) else None,
              "parameters": selected, "rows": [], "checks": [], "issues": []}
    tolerance = selected["summary_rounding_tolerance"]
    valid = (not invalid_parameters and finite(selected["probability_tolerance"]) and selected["probability_tolerance"] >= 0
             and isinstance(tolerance, dict) and set(tolerance) == {"eff_nseq", "re_per_position"}
             and all(finite(value) and value >= 0 for value in tolerance.values()))
    _check(result, "parameter_valid", "pass" if valid else "fail")
    if not valid:
        result["issues"].append(_problem("parameter_invalid"))
    if not _saved_sheet_shape(sheet):
        result["issues"].append(_problem("sheet_invalid"))
        return result
    for occurrence in sheet["artifact_occurrences"]:
        invalid = any(problem.get("occurrence_id") == occurrence["occurrence_id"] and problem["code"] in
                      {"occurrence_size_mismatch", "occurrence_digest_mismatch", "occurrence_role_mismatch"} for problem in sheet["issues"])
        _check(result, "artifact_binding", "fail" if invalid else "pass", inputs=[{"occurrence_id": occurrence["occurrence_id"]}])
        if invalid:
            result["issues"].append(_problem("source_binding_invalid", occurrence_id=occurrence["occurrence_id"]))
    if sheet["operation"]["program"] == "hmmbuild":
        _build(sheet, result, selected)
    else:
        _mask(sheet, result)
    return result


__all__ = ["calculate_hmmer_alignment_preparation_components", "reconstruct_alimask_model_map",
           "SCHEMA", "ROW_FIELDS", "COMPONENT_FIELDS", "COMPONENT_STATES", "CHECK_CODES", "CHECK_STATES", "ISSUE_CODES"]
