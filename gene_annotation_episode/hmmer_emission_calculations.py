"""Deterministic numerical components of generated hmmemit data (261/E1).

Lengths count ASCII residue letters, excluding alignment gaps (-._), stop (*),
and missing-data (~) symbols. Ambiguity means BJZX in amino or RYMKSWBDHVN in
DNA/RNA; amino O/U are retained separately as noncanonical, unambiguous symbols.
All statistics describe captured generated records, never biological samples.

Consensus uses the shared validated native probability view without normalization. The explicit
absolute probability tolerance defines intervals around finite saved cells;
structural '*' zeros remain exact. Nominal mismatch counts are distinguished
from checks that become unknown when the native unrounded choice is ambiguous.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import math

from .hmmer_model_data import ALPHABETS, _occurrence_valid
from .hmmer_model_calculations import (
    _hmmer2, validate_hmmer_probability_cell, validate_hmmer_probability_vector,
)
from .hmmer_emission_data import SCHEMA as SHEET_SCHEMA, MODES, _name


SCHEMA = "hmmer_emission_components_v1"
STATES = frozenset({"present", "missing", "incomplete", "incompatible", "nonfinite", "failed"})
ISSUE_CODES = frozenset({"sheet_invalid", "parameters_invalid", "occurrence_invalid",
    "record_invalid", "association_invalid", "alphabet_incompatible", "model_invalid",
    "probability_invalid", "consensus_ambiguous", "thresholds_missing",
    "native_conversion_basis_incompatible"})
_AMBIGUOUS = {"amino": set("BJZX"), "DNA": set("RYMKSWBDHVN"), "RNA": set("RYMKSWBDHVN")}


def _component(value=None, *, state="present", unit="count", inputs=()):
    assert state in STATES
    return {"value": value, "state": state, "unit": unit, "inputs": deepcopy(list(inputs))}


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def _operand(key, field, **context):
    return {"record_key": key, "field": field, **context}


class _Calculator:
    def __init__(self, sheet, parameters):
        self.sheet = sheet
        self.result = {"schema": SCHEMA, "operation": deepcopy(sheet.get("operation")),
                       "parameters": deepcopy(parameters), "rows": [], "checks": [],
                       "issues": deepcopy(sheet.get("issues", []))}
        self.parameters = parameters
        self.records = sheet.get("output_records", [])
        self.models = sheet.get("model_extraction", {}).get("records", [])
        self.by_record = {r["record_key"]: r for r in self.records}
        self.by_model = {m["record_key"]: m for m in self.models}
        self.record_components = {}
        self.invalid_records = set()
        self.invalid_occurrences = set()

    def issue(self, code, *, record_key=None, field=None, details=None):
        assert code in ISSUE_CODES
        self.result["issues"].append({"code": code, "stage": "calculation",
            "record_key": record_key, "field": field, "details": details or {}})

    def check(self, code, state, key=None, inputs=()):
        self.result["checks"].append({"code": code, "state": state,
                                     "record_key": key, "inputs": deepcopy(list(inputs))})

    def validate(self):
        occurrences = self.sheet["artifact_occurrences"]
        counts = Counter(o.get("occurrence_id") for o in occurrences)
        by_occurrence = {o.get("occurrence_id"): o for o in occurrences}
        native = self.sheet["native_rows"]
        native_keys = Counter(row.get("record_key") for row in native)
        by_native = {row.get("record_key"): row for row in native}
        for occurrence in occurrences:
            identity = occurrence.get("occurrence_id")
            valid = _occurrence_valid(occurrence) and counts[identity] == 1
            if valid and occurrence["direction"] == "output":
                lines = [r for r in native if r.get("occurrence_id") == identity]
                try:
                    raw = "".join(r["raw"] for r in lines).encode("utf-8", errors="surrogateescape")
                    offset = 0
                    for index, row in enumerate(lines):
                        loc = row["locator"]
                        end = offset + len(row["raw"].encode("utf-8", errors="surrogateescape"))
                        valid &= (row["record_key"] == f"{identity}#native/{index}" and
                                  native_keys[row["record_key"]] == 1 and
                                  loc["byte_start"] == offset and loc["byte_end"] == end and
                                  loc["line_start"] == index+1 and loc["line_end"] == index+1)
                        if row["kind"] == "fasta_sequence":
                            valid &= row["value"] == "".join(row["raw"].split())
                        elif row["kind"] in {"sequence", "GC", "GR", "GS", "GF"}:
                            parts = row["raw"].strip().split(None, 3 if row["kind"] in {"GR", "GS"} else 2 if row["kind"] in {"GC", "GF"} else 1)
                            valid &= parts[-1] == row["value"]
                            if row["kind"] == "sequence":
                                valid &= parts[0] == row["name"]
                            else:
                                valid &= parts[-2] == row["tag"]
                                if row["kind"] in {"GR", "GS"}:
                                    valid &= parts[1] == row["name"]
                        offset = end
                    valid &= len(raw) == occurrence["size_bytes"] and hashlib.sha256(raw).hexdigest() == occurrence["sha256"].lower()
                except (KeyError, TypeError, UnicodeError):
                    valid = False
            if not valid:
                self.invalid_occurrences.add(identity)
                self.issue("occurrence_invalid", field="artifact_occurrences", details={"occurrence_id": identity})
        record_counts = Counter(r.get("record_key") for r in self.records)
        def annotations_valid(annotations, occurrence_id):
            for tag, annotation in annotations.items():
                fragments = annotation["fragments"]
                if annotation["text"] != "".join(piece["value"] for piece in fragments):
                    return False
                for piece in fragments:
                    matches = [source for source in native if
                        source["occurrence_id"] == occurrence_id and
                        source["locator"]["artifact_ref"] == piece["locator"]["artifact_ref"] and
                        source["locator"]["line_start"] == piece["locator"]["line"]]
                    if len(matches) != 1 or matches[0].get("tag") != tag or matches[0].get("value") != piece["value"]:
                        return False
            return True
        for row in self.records:
            key, loc = row.get("record_key"), row.get("locator", {})
            occurrence = by_occurrence.get(row.get("occurrence_id"), {})
            try:
                valid = (row["occurrence_id"] not in self.invalid_occurrences and record_counts[key] == 1
                    and key == f'{row["occurrence_id"]}#{row["kind"]}/{loc["record_ordinal"]}'
                    and type(loc["record_ordinal"]) is int and loc["record_ordinal"] >= 0
                    and loc["artifact_ref"] == occurrence["artifact_ref"]
                    and 0 <= loc["byte_start"] <= loc["byte_end"] <= occurrence["size_bytes"]
                    and 1 <= loc["line_start"] <= loc["line_end"])
                if row["kind"] != "alignment":
                    valid &= row["sequence"] == "".join(p["value"] for p in row["fragments"])
                    for piece in row["fragments"]:
                        source = by_native[piece["native_row_key"]]
                        valid &= (source.get("value") == piece["value"] and source["locator"] == piece["locator"]
                                  and source["occurrence_id"] == row["occurrence_id"])
                        if row["kind"] == "alignment_row":
                            valid &= source.get("name") == row["name"]
                    if row["kind"] == "fasta":
                        header = next((source for source in native if source["occurrence_id"] == row["occurrence_id"]
                                       and source["locator"]["byte_start"] == loc["byte_start"]), None)
                        parts = header["raw"].rstrip("\r\n")[1:].split(None, 1) if header else []
                        valid &= (row["name"] == (parts[0] if parts else None)
                                  and row["description"] == (parts[1] if len(parts) == 2 else None))
                    if row["kind"] == "alignment_row":
                        parent = self.by_record.get(row["alignment_record_key"], {})
                        valid &= key in parent.get("native", {}).get("row_record_keys", [])
                        valid &= annotations_valid(row["native"]["column_annotations"], row["occurrence_id"])
                else:
                    valid &= row["native"]["row_record_keys"] == [child["record_key"] for child in self.records
                        if child["kind"] == "alignment_row" and child["alignment_record_key"] == key]
                    valid &= annotations_valid(row["native"]["column_annotations"], row["occurrence_id"])
                if row.get("model_record_key") is not None:
                    model = self.by_model[row["model_record_key"]]
                    valid &= row["alphabet"] == model["alphabet"]
                    if row["kind"] != "alignment":
                        name = _name(model)
                        expected = (f"{name}-consensus" if self.sheet["operation"]["mode"].startswith("consensus_")
                                    else f'{name}-sample{row["sample_ordinal"]}')
                        valid &= row["name"] == expected
            except (KeyError, TypeError, ValueError):
                valid = False
            if not valid:
                self.invalid_records.add(key)
                self.issue("record_invalid", record_key=key)
        associations = [a for a in self.sheet["associations"] if a.get("kind") == "record"]
        for row in self.records:
            matched = [a for a in associations if a.get("record_key") == row["record_key"]]
            valid = len(matched) == 1 and matched[0].get("model_record_key") == row["model_record_key"]
            if not valid:
                self.invalid_records.add(row["record_key"])
                self.issue("association_invalid", record_key=row["record_key"])
        extraction = self.sheet["model_extraction"]
        model_occurrence = extraction.get("occurrence", {})
        model_occurrences = [o for o in occurrences if o.get("direction") == "input" and o.get("role") == "models"]
        self.models_valid = (len(model_occurrences) == 1 and model_occurrences[0] == model_occurrence
            and model_occurrence.get("occurrence_id") not in self.invalid_occurrences
            and extraction.get("schema") == "hmmer_model_extraction_v1"
            and not any(i.get("code") == "model_extraction_mismatch" for i in self.sheet["issues"]))
        for ordinal, model in enumerate(self.models):
            loc = model.get("locator", {})
            valid = (model.get("record_key") == f'{model_occurrence.get("occurrence_id")}#model/{ordinal}'
                     and loc.get("record_ordinal") == ordinal
                     and loc.get("artifact_ref") == model_occurrence.get("artifact_ref"))
            if not valid:
                self.models_valid = False
                self.issue("model_invalid", record_key=model.get("record_key"))

    def sequence(self, row):
        key, sequence = row["record_key"], row["sequence"]
        inputs = [_operand(key, "sequence"), _operand(key, "alphabet")]
        kind = (row["alphabet"] or {}).get("kind")
        canonical = set(ALPHABETS.get(kind, []))
        ambiguity = _AMBIGUOUS.get(kind, set())
        allowed = canonical | ambiguity | ({"O", "U"} if kind == "amino" else set())
        counts = Counter(sequence)
        residues = [c for c in sequence if c.isascii() and c.isalpha()]
        invalid = [c for c in sequence if c.upper() not in allowed and c not in "-._*~"]
        state = ("incompatible" if key in self.invalid_records or kind not in ALPHABETS or invalid
                 else "incomplete" if row["state"] != "complete" else "present")
        if invalid or kind not in ALPHABETS:
            self.issue("alphabet_incompatible", record_key=key, field="sequence")
        residue_count = len(residues)
        ambiguous = sum(c.upper() in ambiguity for c in residues)
        component = lambda value, unit="residue_count", state=state: _component(value, state=state, unit=unit, inputs=inputs)
        result = {"kind": "generated_record", "record_key": key, "basis": row["basis"],
            "model_record_key": row["model_record_key"], "alphabet": deepcopy(row["alphabet"]),
            "sequence": sequence, "length": component(residue_count),
            "symbol_counts": {c: _component(n, unit="symbol_count", inputs=[_operand(key, "sequence", symbol=c)])
                              for c, n in sorted(counts.items())},
            "canonical_residue_count": component(sum(c.upper() in canonical for c in residues)),
            "ambiguous_residue_count": component(ambiguous),
            "noncanonical_unambiguous_residue_count": component(sum(c.upper() in {"O", "U"} for c in residues) if kind == "amino" else 0),
            "ambiguous_fraction": component(ambiguous/residue_count if residue_count and state == "present" else None,
                                               "fraction_of_ungapped_residues",
                                               state if residue_count else "missing"),
            "gap_count": _component(sum(counts[c] for c in "-._"), unit="gap_count", inputs=inputs),
            "stop_count": _component(counts["*"], unit="stop_symbol_count", inputs=inputs),
            "missing_symbol_count": _component(counts["~"], unit="missing_data_symbol_count", inputs=inputs),
            "invalid_symbol_count": _component(len(invalid), unit="symbol_count", inputs=inputs),
            "model_alignment": {"state": "missing", "reason": "no_native_trace_in_fasta"} if row["kind"] == "fasta"
                               else {"state": "present", "alignment_record_key": row["alignment_record_key"]}}
        self.record_components[key] = result
        self.result["rows"].append(result)

    def model(self, model):
        key = model["record_key"]
        populations = [a for a in self.sheet["associations"] if a.get("kind") == "model_population" and a.get("model_record_key") == key]
        population = populations[0] if len(populations) == 1 else {}
        records = [r for r in self.records if r["kind"] != "alignment" and r["model_record_key"] == key]
        keys = [r["record_key"] for r in records]
        valid = (self.models_valid and population.get("record_keys") == keys
                 and not any(k in self.invalid_records for k in keys))
        state = ("incompatible" if not valid or population.get("state") == "conflicting" else
                 "missing" if not population.get("output_available") else "present")
        inputs = [_operand(key, "associations.model_population.record_keys", record_keys=keys)]
        count = len(keys) if state == "present" else None
        length_values = [self.record_components[k]["length"] for k in keys]
        length_state = state if state != "present" else ("incomplete" if any(c["state"] != "present" for c in length_values) else "present")
        lengths = [c["value"] for c in length_values]
        settings = self.sheet["operation"]["settings"]
        n = settings.get("-N")
        selected_n = _component(n if type(n) is int and n > 0 else None,
            state="missing" if n is None else "present" if type(n) is int and n > 0 else "incompatible",
            unit="requested_sample_count", inputs=[{"field": "operation.settings.-N"}])
        expected = 1 if self.sheet["operation"]["mode"].startswith("consensus_") else selected_n["value"]
        difference = count-expected if count is not None and expected is not None else None
        summary = {"kind": "model", "model_record_key": key,
            "basis": "model_derived" if self.sheet["operation"]["mode"].startswith("consensus_") else "generated",
            "record_keys": keys, "input_model_length": _component(model.get("length"),
                state="present" if type(model.get("length")) is int else "missing", unit="model_match_state_count",
                inputs=[_operand(key, "length")]),
            "selected_N": selected_n,
            "configured_expected_length": _component(settings.get("-L") if type(settings.get("-L")) is int else None,
                state="present" if type(settings.get("-L")) is int else "missing", unit="configured_expected_residue_count",
                inputs=[{"field": "operation.settings.-L"}]),
            "captured_sample_count": _component(count, state=state, unit="captured_generated_record_count", inputs=inputs),
            "expected_output_count": _component(expected, state="present" if expected is not None else selected_n["state"],
                unit="expected_generated_record_count", inputs=[{"field": "operation.mode"}, {"field": "operation.settings.-N"}]),
            "count_difference": _component(difference, state="present" if difference is not None else state if state != "present" else "missing",
                unit="captured_minus_expected_record_count", inputs=inputs+[{"field": "expected_output_count"}])}
        for field, value in (("total_length", sum(lengths) if all(v is not None for v in lengths) else None),
                             ("minimum_length", min(lengths) if lengths and all(v is not None for v in lengths) else None),
                             ("maximum_length", max(lengths) if lengths and all(v is not None for v in lengths) else None),
                             ("mean_length", sum(lengths)/len(lengths) if lengths and all(v is not None for v in lengths) else None)):
            unavailable = length_state != "present" or (not lengths and field != "total_length")
            summary[field] = _component(None if unavailable else value,
                state=length_state if length_state != "present" else "missing" if unavailable else "present",
                unit="residue_count" if field != "mean_length" else "residues_per_captured_record",
                inputs=[_operand(k, "length") for k in keys] + [{"denominator": len(keys), "population": "captured_generated_records"}])
        self.result["rows"].append(summary)
        self.check("sample_population_count", "unknown" if difference is None or not population.get("output_complete")
                   else "pass" if difference == 0 else "fail", key, inputs)

    def alignment(self, alignment):
        key, native = alignment["record_key"], alignment["native"]
        keys = native["row_record_keys"]
        rows = [self.by_record[k] for k in keys if k in self.by_record]
        width = native.get("column_count")
        rf = native.get("column_annotations", {}).get("RF")
        geometry = (key not in self.invalid_records and len(rows) == len(keys)
                    and type(width) is int and width >= 0 and alignment["state"] == "complete"
                    and all(len(r["sequence"]) == width and r["native"].get("geometry_valid")
                            and r["record_key"] not in self.invalid_records for r in rows))
        rf_valid = geometry and isinstance(rf, dict) and rf.get("valid") and len(rf.get("text", "")) == width
        match_columns = [i+1 for i, char in enumerate(rf["text"]) if char not in ".-_~ "] if rf_valid else []
        inputs = [_operand(key, "native.column_count"), _operand(key, "native.column_annotations.RF")]
        m = self.by_model.get(alignment["model_record_key"], {}).get("length")
        match_mapping = rf_valid and type(m) is int and len(match_columns) == m
        components = {"kind": "alignment", "record_key": key, "basis": "generated",
            "model_record_key": alignment["model_record_key"],
            "alignment_width": _component(width if geometry else None, state="present" if geometry else "incomplete", unit="alignment_column_count", inputs=inputs),
            "rf_match_column_count": _component(len(match_columns) if rf_valid else None, state="present" if rf_valid else "missing" if rf is None else "incomplete", unit="rf_match_column_count", inputs=inputs),
            "captured_row_count": _component(len(rows), unit="captured_generated_record_count", inputs=[_operand(key, "native.row_record_keys")]),
            "match_columns": [], "row_coordinates": []}
        for match_ordinal, column in enumerate(match_columns, 1):
            occupied = sum(r["sequence"][column-1].isascii() and r["sequence"][column-1].isalpha() for r in rows)
            column_inputs = [_operand(k, "sequence", alignment_column=column) for k in keys]
            components["match_columns"].append({"alignment_column": _component(column, unit="one_based_alignment_column", inputs=inputs),
                "rf_match_ordinal": _component(match_ordinal, unit="one_based_rf_match_ordinal", inputs=inputs),
                "model_position": _component(match_ordinal if match_mapping else None, state="present" if match_mapping else "incompatible", unit="one_based_model_position", inputs=inputs+[_operand(alignment["model_record_key"], "length")]),
                "occupancy": _component(occupied, unit="generated_residue_count", inputs=column_inputs),
                "sample_denominator": _component(len(rows), unit="captured_generated_record_count", inputs=[_operand(key, "native.row_record_keys")]),
                "occupancy_fraction": _component(occupied/len(rows) if rows else None, state="present" if rows else "missing", unit="fraction_of_captured_rows", inputs=column_inputs+[_operand(key, "native.row_record_keys")])})
        if geometry:
            for row in rows:
                position, coordinates = 0, []
                for column, char in enumerate(row["sequence"], 1):
                    residue = char.isascii() and char.isalpha()
                    position += int(residue)
                    coordinates.append({"symbol": char,
                        "alignment_column": _component(column, unit="one_based_alignment_column", inputs=[_operand(row["record_key"], "sequence")]),
                        "residue_position": _component(position if residue else None, state="present" if residue else "missing", unit="one_based_ungapped_residue", inputs=[_operand(row["record_key"], "sequence")])})
                components["row_coordinates"].append({"record_key": row["record_key"], "columns": coordinates})
        self.result["rows"].append(components)
        self.check("alignment_geometry", "pass" if geometry else "fail", key, inputs)
        self.check("rf_matches_model_length", "unknown" if not rf_valid or m is None else "pass" if match_mapping else "fail", key, inputs)

    def consensus(self, model):
        key, mode = model["record_key"], self.sheet["operation"]["mode"]
        h2 = _hmmer2(model)
        alphabet = model.get("alphabet", {})
        symbols, kind = alphabet.get("symbols", []), alphabet.get("kind")
        supported = kind in ALPHABETS and symbols == ALPHABETS[kind] and self.models_valid
        tolerance = self.parameters["probability_rounding_tolerance"]
        thresholds = self.parameters["consensus_thresholds"]
        thresholded = mode == "consensus_thresholded"
        threshold_valid = (isinstance(thresholds, dict) and set(thresholds) == {"minl", "minu"}
                           and all(_finite(x) and 0 <= x <= 1 for x in thresholds.values()))
        records = [r for r in self.records if r["kind"] != "alignment" and r["model_record_key"] == key]
        actual = records[0]["sequence"] if len(records) == 1 and records[0]["record_key"] not in self.invalid_records else None
        actual_complete = actual is not None and records[0]["state"] == "complete"
        positions = []
        for ordinal, position in enumerate(model.get("positions", [])):
            native_position = position.get("position")
            distribution = position.get("match")
            cells = distribution.get("cells", []) if isinstance(distribution, dict) else []
            operands = [_operand(key, "positions.match", position=native_position, position_ordinal=ordinal),
                        {"field": "parameters.probability_rounding_tolerance"}]
            checked = validate_hmmer_probability_vector(distribution, record=model, field="match",
                position_ordinal=ordinal, symbols=symbols, indices=tuple(range(len(symbols))))
            validations = [validate_hmmer_probability_cell(cell, record=model, field="match",
                position_ordinal=ordinal, cell_index=i) for i, cell in enumerate(cells)]
            probabilities = [c["probability"] for c in validations]
            cell_states = [c["state"] for c in validations]
            valid = supported and checked["state"] == "present"
            if "representation" in model:
                operands += checked["inputs"]
            mask = position.get("annotations", {}).get("MM", {}).get("value")
            mask_known = (model.get("flags", {}).get("MM") is not True or mask in {"m", "-"})
            masked = mask == "m" and model.get("flags", {}).get("MM") is True
            valid &= mask_known and native_position == ordinal+1
            max_probability = max(probabilities) if valid and probabilities else None
            winners = [symbols[i] for i, p in enumerate(probabilities) if p == max_probability] if valid else []
            nominal = None
            possible = []
            near_tie = near_threshold = False
            if valid:
                unknown = "X" if kind == "amino" else "N"
                bounds = [(max(0, p-tolerance), min(1, p+tolerance)) if cell["state"] != "structural_zero" else (0, 0)
                          for p, cell in zip(probabilities, cells)]
                lower, upper = max(x[0] for x in bounds), max(x[1] for x in bounds)
                candidates = [symbol for symbol, (_, high) in zip(symbols, bounds) if high >= lower]
                near_tie = len(candidates) > 1
                if thresholded and threshold_valid:
                    minl, minu = thresholds["minl"], thresholds["minu"]
                    nominal = unknown.lower() if masked or max_probability < minl else winners[0].upper() if max_probability >= minu else winners[0].lower()
                    near_threshold = lower <= minl <= upper or lower <= minu <= upper
                    if masked:
                        possible = [unknown.lower()]
                    else:
                        if lower < minl:
                            possible.append(unknown.lower())
                        if upper >= max(minl, minu):
                            possible.extend(s.upper() for s in candidates)
                        if minl < minu and upper >= minl and lower < minu:
                            possible.extend(s.lower() for s in candidates)
                elif not thresholded:
                    nominal = unknown if masked else winners[0]
                    possible = [unknown] if masked else candidates
            ambiguous = len(set(possible)) > 1
            positions.append({"position": _component(native_position, state="present" if native_position == ordinal+1 else "incompatible", unit="one_based_model_position", inputs=[_operand(key, "positions.position", position_ordinal=ordinal)]),
                "probabilities": [{"symbol": symbol, "probability": _component(p, state=state, unit="probability", inputs=
                    validations[i]["inputs"] if "representation" in model else [_operand(key, "positions.match.cells", position_ordinal=ordinal, cell_index=i)])}
                                  for i, (symbol, p, state) in enumerate(zip(symbols, probabilities, cell_states))],
                "maximum_probability": _component(max_probability, state="present" if valid else
                    checked["state"] if "representation" in model and checked["state"] != "present" else "incomplete", unit="probability", inputs=operands),
                "maximum_symbols": winners, "mask": mask, "masked": masked,
                "thresholds": {name: _component(thresholds[name] if threshold_valid else None,
                    state="present" if threshold_valid else "missing", unit="probability", inputs=[{"field": "parameters.consensus_thresholds."+name}]) for name in ("minl", "minu")},
                "expected_symbol": nominal, "possible_symbols": sorted(set(possible)),
                "near_tie": near_tie, "near_threshold": near_threshold, "ambiguous": ambiguous})
            if not valid:
                details = {"position_ordinal": ordinal}
                if "representation" in model:
                    details["model_issue"] = checked["issue_code"]
                self.issue("probability_invalid", record_key=key, field="positions.match", details=details)
        full = (model.get("terminated") is True and type(model.get("length")) is int and len(positions) == model["length"]
                and all(p["expected_symbol"] is not None for p in positions))
        expected = "".join(p["expected_symbol"] for p in positions) if full else None
        ambiguous_count = sum(p["ambiguous"] for p in positions)
        mismatch = (sum(a != b for a, b in zip(actual, expected))+abs(len(actual)-len(expected))
                    if actual is not None and expected is not None else None)
        certain_mismatch = (sum(a not in p["possible_symbols"] for a, p in zip(actual, positions)) + abs(len(actual)-len(positions))
                            if mismatch is not None and actual_complete else None)
        missing_state = "missing" if actual is None or thresholded and not threshold_valid else "incomplete"
        inputs = [_operand(key, "positions"), {"field": "parameters.consensus_thresholds"}]
        if h2:
            inputs[0].update(source_encoding=model["representation"]["encoding"],
                             qualification="hmmer2_native_conversion_changes_basis")
        self.result["rows"].append({"kind": "consensus", "model_record_key": key, "basis": "model_derived",
            "actual_record_keys": [r["record_key"] for r in records], "expected_sequence": expected,
            "actual_sequence": actual, "positions": positions,
            "mismatch_count": _component(mismatch, state="present" if mismatch is not None and actual_complete else "incomplete" if mismatch is not None else missing_state, unit="nominal_consensus_mismatch_count", inputs=inputs),
            "certain_mismatch_count": _component(None if h2 else certain_mismatch,
                state="incompatible" if h2 else "present" if certain_mismatch is not None else missing_state,
                unit="certain_consensus_mismatch_count", inputs=inputs),
            "ambiguous_position_count": _component(ambiguous_count, unit="decoded_ambiguous_position_count", inputs=inputs)})
        check = "unknown" if mismatch is None or ambiguous_count or not actual_complete else "pass" if mismatch == 0 else "fail"
        if certain_mismatch:
            check = "fail"
        if h2:
            check = "unknown"
            self.issue("native_conversion_basis_incompatible", record_key=key,
                       field="consensus", details={"qualification": "hmmer2_native_conversion_changes_basis"})
        self.check("consensus_agreement", check, key, inputs)
        self.check("consensus_length", "unknown" if not actual_complete or model.get("length") is None
                   else "pass" if len(actual) == model["length"] else "fail", key, inputs)
        if ambiguous_count:
            self.issue("consensus_ambiguous", record_key=key)
        if thresholded and not threshold_valid:
            self.issue("thresholds_missing", record_key=key, field="parameters.consensus_thresholds")


def calculate_hmmemit_components(sheet, *, parameters=None):
    """Recalculate saved generated data; no I/O or native invocation.

    Omitted thresholds use explicitly supplied --minl/--minu settings only;
    explicitly passing consensus_thresholds=None keeps them unavailable.
    The default absolute rounding tolerance is 1e-5, recorded in parameters.
    It never changes model probabilities, output data, or historical credit.
    """
    fallback = {"schema": SCHEMA, "operation": deepcopy(sheet.get("operation")) if isinstance(sheet, dict) else None,
                "parameters": deepcopy(parameters), "rows": [], "checks": [], "issues": []}
    def invalid(code, field):
        fallback["issues"].append({"code": code, "stage": "calculation", "record_key": None, "field": field, "details": {}})
        return fallback
    if not isinstance(sheet, dict) or sheet.get("schema") != SHEET_SCHEMA:
        return invalid("sheet_invalid", "schema")
    operation = sheet.get("operation")
    if not isinstance(operation, dict) or operation.get("program") != "hmmemit" or not isinstance(operation.get("mode"), str) or operation.get("mode") not in MODES or not isinstance(operation.get("settings"), dict):
        return invalid("sheet_invalid", "operation")
    if any(not isinstance(sheet.get(field), list) for field in ("artifact_occurrences", "output_records", "native_rows", "associations", "issues")) or not isinstance(sheet.get("model_extraction"), dict):
        return invalid("sheet_invalid", "fields")
    if parameters is not None and (not isinstance(parameters, dict) or set(parameters) - {"consensus_thresholds", "probability_rounding_tolerance"}):
        return invalid("parameters_invalid", "parameters")
    supplied = parameters or {}
    settings = operation["settings"]
    thresholds = ({"minl": settings["--minl"], "minu": settings["--minu"]}
                  if "--minl" in settings and "--minu" in settings else None)
    resolved = {"consensus_thresholds": deepcopy(supplied.get("consensus_thresholds", thresholds)),
                "probability_rounding_tolerance": supplied.get("probability_rounding_tolerance", 1e-5)}
    fallback["parameters"] = deepcopy(resolved)
    if not _finite(resolved["probability_rounding_tolerance"]) or not 0 <= resolved["probability_rounding_tolerance"] <= 1:
        return invalid("parameters_invalid", "probability_rounding_tolerance")
    threshold = resolved["consensus_thresholds"]
    if threshold is not None and (not isinstance(threshold, dict) or set(threshold) != {"minl", "minu"} or any(not _finite(x) or not 0 <= x <= 1 for x in threshold.values())):
        return invalid("parameters_invalid", "consensus_thresholds")
    try:
        calculator = _Calculator(sheet, resolved)
        calculator.validate()
        for row in calculator.records:
            if row["kind"] != "alignment":
                calculator.sequence(row)
        for model in calculator.models:
            calculator.model(model)
        for row in calculator.records:
            if row["kind"] == "alignment":
                calculator.alignment(row)
        if operation["mode"].startswith("consensus_"):
            for model in calculator.models:
                calculator.consensus(model)
        return calculator.result
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        return invalid("sheet_invalid", "nested_shape")
