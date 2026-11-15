"""Deterministic A1 transformation/selection/index validation from saved sheets.

These are quantities and checks about supplied artifacts. They are neither a
biological-confidence model nor an assertion of authenticated producer custody.
The full per-cell comparisons remain available when the explicit tolerance or
expected revision changes; no analysis, acquisition or conversion is repeated.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import math

from .hmmer_artifact_data import (
    SCHEMA as SHEET_SCHEMA, SHEET_FIELDS, ROW_FIELDS as DATA_ROW_FIELDS,
    ISSUE_CODES as DATA_ISSUE_CODES, MODEL_ROLES, BUNDLE_ROLES, _operation_valid,
    _roles, _label, _pair_identity, _build_associations, _binding_errors,
)
from .hmmer_model_data import _occurrence_valid, ALPHABETS, TRANSITIONS
from .hmmer_model_calculations import (
    _identity_valid, _representation_encoding, _hmmer2,
    validate_hmmer_probability_cell, validate_hmmer_probability_vector,
)


SCHEMA = "hmmer_artifact_components_v1"
COMPONENT_STATES = frozenset({"present", "missing", "incomplete", "incompatible", "nonfinite", "failed"})
CHECK_STATES = frozenset({"pass", "fail", "unknown", "not_applicable"})
ISSUE_CODES = DATA_ISSUE_CODES | frozenset({"sheet_invalid", "saved_reference_invalid", "parameter_invalid",
    "saved_association_invalid", "model_component_invalid", "probability_difference_exceeds_tolerance",
    "native_conversion_basis_incompatible"})
CHECK_CODES = frozenset({"parameters_valid", "supplied_bytes_match_occurrence", "capture_complete",
    "model_population_complete", "conversion_population_equal", "model_relationship",
    "model_probability_equivalence", "expected_revision", "required_member_present", "member_nonempty",
    "binary_framing", "binary_internal_content", "supplied_artifact_binding", "authenticated_artifact_custody",
    "bundle_supplied_attempt_consistency", "bundle_revision_consistent", "native_model_count",
    "native_primary_name_count", "native_accession_count", "source_primary_names_unique",
    "source_accessions_unique", "requested_keys_unique", "all_requested_keys_resolved",
    "all_requested_keys_returned", "fetch_output_population", "native_diagnostics", "conversion_stdout_equal"})
ROW_FIELDS = {
    "population": frozenset({"kind", "row_key", "direction", "record_keys", "decoded_model_count",
        "complete_model_count", "primary_name_count", "accession_count", "distinct_primary_name_count",
        "distinct_accession_count", "model_artifact_bytes"}),
    "model_comparison": frozenset({"kind", "row_key", "association_id", "source_record_key", "output_record_key",
        "relationship_state", "source_length", "output_length", "length_difference", "cell_differences",
        "compared_cell_count", "source_cell_count", "output_cell_count", "max_absolute_probability_difference",
        "mean_absolute_probability_difference", "optional_fields", "retained_optional_field_count",
        "lost_optional_field_count", "changed_optional_field_count", "gained_optional_field_count"}),
    "key_population": frozenset({"kind", "row_key", "requested_key_count", "distinct_key_count",
        "resolved_key_count", "missing_key_count", "ambiguous_key_count", "unknown_key_count", "fulfilled_key_count",
        "duplicate_key_occurrence_count", "selected_source_occurrence_count", "returned_model_occurrence_count",
        "expected_returned_model_occurrence_count", "duplicate_representation_count"}),
    "artifact": frozenset({"kind", "row_key", "occurrence_id", "size_bytes", "format", "revision", "byte_order",
        "offset_width", "decoded_record_count", "supplied_binding_state", "authenticated_custody_state",
        "internal_content_state"}),
    "index_summary": frozenset({"kind", "row_key", "native_row_key", "native_model_count", "native_primary_name_count",
        "native_accession_count", "decoded_input_model_count", "decoded_input_primary_name_count",
        "decoded_input_accession_count", "model_count_difference", "primary_name_count_difference", "accession_count_difference"}),
    "bundle": frozenset({"kind", "row_key", "member_occurrence_ids", "member_count", "bundle_byte_sum"}),
}
CELL_FIELDS = frozenset({"field", "position", "cell_index", "symbol", "source_token", "output_token",
    "source_probability", "output_probability", "difference", "absolute_difference"})
OPTIONAL_FIELD_FIELDS = frozenset({"field", "source_present", "output_present", "source_value", "output_value", "state"})


def _finite(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _component(value=None, state="present", unit="count", inputs=()):
    assert state in COMPONENT_STATES
    return {"value": value, "state": state, "unit": unit, "inputs": deepcopy(list(inputs))}


def _state(states):
    return next((s for s in ("failed", "incompatible", "nonfinite", "incomplete", "missing") if s in states), "present")


def _operand(field, **kwargs):
    return {"field": field, **kwargs}


def _distributions(record):
    """Common core slots only; HMMER2 configured fields remain in legacy data."""
    if record is None:
        return {}
    values = {("composition", None): record.get("composition"),
        ("initial.insert", 0): record.get("initial", {}).get("insert"),
        ("initial.transitions", 0): record.get("initial", {}).get("transitions")}
    for index, position in enumerate(record.get("positions", [])):
        for field in ("match", "insert", "transitions"):
            values[("positions." + str(index) + "." + field, position.get("position"))] = position.get(field)
    return values


def _optional_values(record):
    """Retain actual values, omitting source line numbers from value equality."""
    values = {}
    if record is None:
        return values
    for header in record["headers"]:
        if _hmmer2(record) and header["tag"] == TRANSITIONS[0]:
            continue  # Retained body column labels, not optional model metadata.
        if header["tag"] not in {"NAME", "ACC", "LENG", "ALPH", "HMM"}:
            values.setdefault("header." + header["tag"], []).append(deepcopy(header["tokens"]))
    # ACC is optional, but is also a relationship operand. Preserve it here too.
    accession = [deepcopy(h["tokens"]) for h in record["headers"] if h["tag"] == "ACC"]
    if accession:
        values["header.ACC"] = accession
    for index, position in enumerate(record["positions"]):
        # JSON objects carry no scientific order. Keep the declared record and
        # position order, but order annotation names explicitly so calculation
        # lists are identical before and after canonical sheet storage.
        for field in sorted(position["annotations"]):
            values["positions." + str(index) + ".annotations." + field] = deepcopy(position["annotations"][field])
    return values


def _optional_meaning(record, field, raw):
    """Typed metadata equality while the comparison row keeps both raw views."""
    if field.startswith("positions."):
        parts = field.split(".")
        return record["positions"][int(parts[1])]["annotations"][parts[-1]]["value"]
    tag = field.removeprefix("header.")
    if tag == "COM":
        values = [h["value"] for h in record["headers"] if h["tag"] == "COM"]
        if _representation_encoding(record) == "hmmer3_binary_probability":
            return values[0] if len(values) == 1 else values
        if not _hmmer2(record):
            # H3 ASCII writes one numbered COM header per command-log line;
            # its reader discards the first (ordinal) token before joining.
            return "\n".join(value.split(None, 1)[1] if len(value.split(None, 1)) == 2 else "" for value in values)
    native = {"NSEQ": "sequence_count", "EFFN": "effective_sequence_count",
              "MAXL": "maximum_length", "CKSUM": "checksum"}.get(tag)
    if native is not None and len(raw) == 1 and not (_hmmer2(record) and tag == "CKSUM"):
        return record[native]
    if tag in record["flags"] and len(raw) == 1:
        return record["flags"][tag]
    if tag in record["cutoffs"] and len(raw) == 1:
        return record["cutoffs"][tag]["values"]
    if tag == "STATS":
        return [(row["mode"].upper(), row["statistic"].upper(),
                 [(p["name"], p["value"], p["unit"]) for p in row["parameters"]])
                for row in record["calibration"]]
    return raw


class _Calculator:
    def __init__(self, sheet, parameters, result):
        self.sheet, self.parameters, self.result = sheet, parameters, result
        self.occurrences = {o["occurrence_id"]: o for o in sheet["artifact_occurrences"]}
        self.metadata = {r["occurrence_id"]: r for r in sheet["native_rows"] if r["kind"] == "artifact_metadata"}
        self.extracts = {e["occurrence"]["occurrence_id"]: e for e in sheet["model_extractions"]}
        self.records = {r["record_key"]: r for r in sheet["input_records"] + sheet["output_records"]}
        self.tolerance = parameters["probability_tolerance"]
        self.tolerance_valid = _finite(self.tolerance) and self.tolerance >= 0

    def issue(self, code, *, row_key=None, occurrence_id=None, field=None, **details):
        assert code in ISSUE_CODES
        self.result["issues"].append({"code": code, "stage": "calculation", "occurrence_id": occurrence_id,
            "row_key": row_key, "field": field, "details": details})

    def check(self, code, state, *, row_key=None, field=None, inputs=()):
        assert code in CHECK_CODES and state in CHECK_STATES
        self.result["checks"].append({"code": code, "state": state, "row_key": row_key,
            "field": field, "inputs": deepcopy(list(inputs))})

    def bytes_match(self, oid):
        o, m = self.occurrences[oid], self.metadata.get(oid)
        return bool(m and m["measured_size_bytes"] == o["size_bytes"] and m["measured_sha256"] == o["sha256"].lower())

    def identity_usable(self, oid):
        occurrence = self.occurrences[oid]
        fatal = {"occurrence_id_duplicate", "model_extraction_duplicate", "model_extraction_mismatch"}
        return self.bytes_match(oid) and not any(
            i["code"] in fatal and i.get("occurrence_id") == oid or
            i["code"] == "occurrence_ordinal_invalid" and i.get("field") == occurrence["direction"]+"."+occurrence["role"]
            for i in self.sheet["issues"])

    def population(self, direction):
        occurrences = [o for o in self.occurrences.values() if o["direction"] == direction and o["role"] in MODEL_ROLES]
        extracts = [self.extracts[o["occurrence_id"]] for o in occurrences if o["occurrence_id"] in self.extracts]
        records = self.sheet[direction+"_records"]
        state = ("missing" if not occurrences or len(extracts) != len(occurrences) else
                 "incompatible" if any(e["population"]["decoded_count"] is None or e["population"]["state"] == "invalid" for e in extracts) else
                 "incomplete" if not all(e["population"]["complete"] for e in extracts) else "present")
        if any(not self.identity_usable(o["occurrence_id"]) for o in occurrences):
            state = "incompatible"
        inputs = [_operand("population", occurrence_id=o["occurrence_id"]) for o in occurrences]
        known = state in {"present", "incomplete"}
        names, accessions = [_label(r, "NAME") for r in records], [_label(r, "ACC") for r in records]
        names, accessions = [n for n in names if n is not None], [a for a in accessions if a is not None]
        complete = [r for r in records if r["terminated"] and not any(i["code"] != "probability_underflow" for i in r["issues"])]
        row = {"kind": "population", "row_key": direction+"_population", "direction": direction,
            "record_keys": [r["record_key"] for r in records],
            "decoded_model_count": _component(len(records) if known else None, state, "decoded_model_count", inputs),
            "complete_model_count": _component(len(complete) if known else None, state, "complete_decoded_model_count", inputs),
            "primary_name_count": _component(len(names) if known else None, state, "primary_name_occurrence_count", inputs),
            "accession_count": _component(len(accessions) if known else None, state, "accession_occurrence_count", inputs),
            "distinct_primary_name_count": _component(len(set(names)) if known else None, state, "distinct_name_count", inputs),
            "distinct_accession_count": _component(len(set(accessions)) if known else None, state, "distinct_accession_count", inputs),
            "model_artifact_bytes": _component(sum(self.metadata[o["occurrence_id"]]["measured_size_bytes"] for o in occurrences) if occurrences else None,
                "present" if occurrences else "missing", "byte", [_operand("measured_size_bytes", occurrence_id=o["occurrence_id"]) for o in occurrences])}
        self.result["rows"].append(row)
        self.check("model_population_complete", "pass" if state == "present" else "unknown", row_key=row["row_key"], inputs=inputs)
        if direction == "input":
            for code, values in (("source_primary_names_unique", names), ("source_accessions_unique", accessions)):
                self.check(code, "fail" if len(set(values)) != len(values) else "pass" if state == "present" else "unknown",
                           row_key=row["row_key"], inputs=inputs)
        return row

    def _length(self, record):
        value = record.get("length") if record else None
        return _component(value, "present" if type(value) is int and value > 0 else "missing" if record is None or value is None else "incompatible",
            "match_state_count", [_operand("length", record_key=record["record_key"])] if record else [])

    def _cell(self, distribution, index, record, field, position):
        if distribution is None or index >= len(distribution.get("cells", [])):
            return None, "incomplete", None, []
        symbols = TRANSITIONS if field.endswith("transitions") else ALPHABETS.get(record["alphabet"].get("kind"), [])
        if index >= len(symbols):
            return None, "incompatible", distribution["cells"][index].get("token"), []
        ordinal = int(field.split(".")[1]) if field.startswith("positions.") else None
        checked = validate_hmmer_probability_vector(distribution, record=record,
            symbols=symbols, indices=(index,), field=field, position_ordinal=ordinal)
        if checked["issue_code"]:
            self.issue("model_component_invalid", row_key=record["record_key"], field=field,
                       model_issue={"code": checked["issue_code"], "cell": index})
        values = checked["values"]
        return (values[0] if values is not None else None, checked["state"],
                distribution["cells"][index].get("token"), checked["inputs"])

    def comparison(self, association):
        source = self.records.get(next(iter(association["source_record_keys"]), None))
        output = self.records.get(next(iter(association["output_record_keys"]), None))
        key = association["association_id"]
        matched = bool(source and output and association["state"] == "matched" and _pair_identity(source, output))
        if matched:
            matched = all(self.identity_usable(r["record_key"].rsplit("#model/", 1)[0]) for r in (source, output))
        self.check("model_relationship", "pass" if matched else "fail" if source and output else "unknown", row_key=key,
                   inputs=[_operand("associations", association_id=key)])
        a, b = self._length(source), self._length(output)
        length_state = _state([a["state"], b["state"]])
        row = {"kind": "model_comparison", "row_key": key, "association_id": key,
            "source_record_key": source["record_key"] if source else None,
            "output_record_key": output["record_key"] if output else None, "relationship_state": association["state"],
            "source_length": a, "output_length": b,
            "length_difference": _component(b["value"]-a["value"] if length_state == "present" else None,
                length_state, "match_state_count", a["inputs"]+b["inputs"]), "cell_differences": [], "optional_fields": []}
        source_d, output_d = _distributions(source), _distributions(output)
        source_cells = sum(len(d.get("cells", [])) for d in source_d.values() if isinstance(d, dict))
        output_cells = sum(len(d.get("cells", [])) for d in output_d.values() if isinstance(d, dict))
        operands = [_operand("model_body", record_key=r["record_key"]) for r in (source, output) if r]
        if any(_hmmer2(r) for r in (source, output) if r):
            for operand in operands:
                operand.update(population="common_core_probability_slots",
                               qualification="hmmer2_native_conversion_changes_basis")
        row["source_cell_count"] = _component(source_cells if source else None, "present" if source else "missing", "decoded_probability_cell_count", operands[:1])
        row["output_cell_count"] = _component(output_cells if output else None, "present" if output else "missing", "decoded_probability_cell_count", operands[-1:])
        all_states, differences = [], []
        if matched:
            for field, position in dict.fromkeys(list(source_d) + list(output_d)):
                sd, od = source_d.get((field, position)), output_d.get((field, position))
                if sd is None and od is None:
                    if field != "composition":
                        all_states.append("incomplete")
                    continue
                symbols = (sd or od)["symbols"]
                compatible = sd is None or od is None or sd["symbols"] == od["symbols"]
                width = max(len(symbols), len(sd["cells"]) if sd else 0, len(od["cells"]) if od else 0)
                for i in range(width):
                    sp, ss, st, si = self._cell(sd, i, source, field, position)
                    op, os, ot, oi = self._cell(od, i, output, field, position)
                    state = _state([ss, os]) if compatible else "incompatible"
                    difference = op-sp if state == "present" else None
                    cell_inputs = [_operand(field, record_key=r["record_key"], position=position,
                        cell_index=i, role=role) for r, role in ((source, "source"), (output, "output"))]
                    source_inputs, output_inputs = cell_inputs[:1], cell_inputs[1:]
                    if "representation" in source:
                        source_inputs += si
                    if "representation" in output:
                        output_inputs += oi
                    row["cell_differences"].append({"field": field, "position": position, "cell_index": i,
                        "symbol": symbols[i] if i < len(symbols) else None, "source_token": st, "output_token": ot,
                        "source_probability": _component(sp, ss, "probability", source_inputs),
                        "output_probability": _component(op, os, "probability", output_inputs),
                        "difference": _component(difference, state, "probability_difference", source_inputs+output_inputs),
                        "absolute_difference": _component(abs(difference) if difference is not None else None,
                            state, "absolute_probability_difference", source_inputs+output_inputs)})
                    all_states.append(state)
                    if difference is not None:
                        differences.append(abs(difference))
            for record in (source, output):
                if not record["terminated"] or len(record["positions"]) != record["length"]:
                    all_states.append("incomplete")
                if any(p["position"] != i+1 for i,p in enumerate(record["positions"])):
                    all_states.append("incompatible")
        aggregate_state = _state(all_states) if matched else "incompatible" if source and output else "missing"
        if matched and any(_hmmer2(r) for r in (source, output)):
            aggregate_state = "incompatible"
            self.issue("native_conversion_basis_incompatible", row_key=key,
                       qualification="hmmer2_native_conversion_changes_basis")
        if matched and not differences and aggregate_state == "present":
            aggregate_state = "incomplete"
        # Mean/max describe ONLY the explicitly enumerated comparable cells.
        # Incomplete state prevents this partial summary asserting whole-body equality.
        row["compared_cell_count"] = _component(len(differences), "present" if matched else aggregate_state,
            "compared_probability_cell_count", operands)
        aggregate_inputs = operands + [_operand("compared_cell_count", row_key=key, role="denominator")]
        row["max_absolute_probability_difference"] = _component(max(differences) if differences else None,
            aggregate_state, "absolute_probability_difference", operands)
        row["mean_absolute_probability_difference"] = _component(math.fsum(differences)/len(differences) if differences else None,
            aggregate_state, "absolute_probability_difference_per_compared_cell", aggregate_inputs)
        equivalence = ("pass" if max(differences) <= self.tolerance else "fail") if aggregate_state == "present" and self.tolerance_valid else "unknown"
        self.check("model_probability_equivalence", equivalence, row_key=key, inputs=aggregate_inputs+[{"parameter": "probability_tolerance"}])
        if equivalence == "fail":
            self.issue("probability_difference_exceeds_tolerance", row_key=key)
        sv, ov = _optional_values(source), _optional_values(output)
        for field in dict.fromkeys(list(sv)+list(ov)):
            equal = sv.get(field) == ov.get(field)
            if (field in sv and field in ov and any(_representation_encoding(r) == "hmmer3_binary_probability"
                    for r in (source, output))):
                equal = _optional_meaning(source, field, sv[field]) == _optional_meaning(output, field, ov[field])
            status = ("retained" if equal else "changed") if field in sv and field in ov else (
                "lost" if field in sv else "gained")
            row["optional_fields"].append({"field": field, "source_present": field in sv, "output_present": field in ov,
                "source_value": deepcopy(sv.get(field)), "output_value": deepcopy(ov.get(field)),
                "state": status if source and output else "unknown"})
        counts = Counter(f["state"] for f in row["optional_fields"])
        for state in ("retained", "lost", "changed", "gained"):
            row[state+"_optional_field_count"] = _component(counts[state] if source and output else None,
                "present" if source and output else "missing", "optional_field_path_count", operands)
        self.result["rows"].append(row)

    def binary_content(self, oid):
        """Model-body status is distinct from binary framing, indexes and custody."""
        occurrence, metadata = self.occurrences[oid], self.metadata[oid]
        extraction = self.extracts.get(oid)
        if metadata["format"] != "hmmer_binary":
            return "unknown", "unknown"
        if occurrence["completeness"] != "complete":
            return "partial", "unknown"
        if not self.identity_usable(oid):
            return "unknown", "unknown"
        if extraction is None or extraction["population"]["decoded_count"] is None:
            return "unknown", "unknown"
        if any(i["code"] in {"decoder_unavailable", "revision_unsupported", "binary_stream_layout_changed", "binary_layout_unsupported"}
               for i in extraction["issues"]):
            return "unknown", "unknown"
        valid = extraction["population"]["complete"]
        for record in extraction["records"]:
            valid &= (_representation_encoding(record) in {"hmmer3_binary_probability", "hmmer2_binary_probability"}
                and record["terminated"] and type(record["length"]) is int
                and len(record["positions"]) == record["length"]
                and [p["position"] for p in record["positions"]] == list(range(1, record["length"] + 1)))
            for (field, _), distribution in _distributions(record).items():
                symbols = TRANSITIONS if field.endswith("transitions") else ALPHABETS.get(record["alphabet"]["kind"], [])
                ordinal = int(field.split(".")[1]) if field.startswith("positions.") else None
                checked = validate_hmmer_probability_vector(distribution, record=record, field=field,
                    position_ordinal=ordinal, symbols=symbols, indices=tuple(range(len(symbols))), required=field != "composition")
                valid &= (checked["state"] == "present" or field == "composition" and distribution is None
                    or _representation_encoding(record) == "hmmer2_binary_probability"
                    and checked["issue_code"] == "distribution_not_in_topology")
        return ("decoded", "pass") if valid else ("invalid", "fail")

    def artifacts(self):
        _, _, _, required = _roles(self.sheet["operation"])
        for role in sorted(required):
            members = [o for o in self.occurrences.values() if o["direction"] == "output" and o["role"] == role]
            self.check("required_member_present", "pass" if len(members) == 1 else "fail", field=role,
                       inputs=[_operand("artifact_occurrences", direction="output", role=role)])
        for oid, occurrence in self.occurrences.items():
            m = self.metadata[oid]
            source = [_operand("artifact_metadata", occurrence_id=oid)]
            self.check("supplied_bytes_match_occurrence", "pass" if self.bytes_match(oid) else "fail", row_key=oid, inputs=source)
            self.check("capture_complete", "pass" if occurrence["completeness"] == "complete" else "unknown", row_key=oid, inputs=source)
            binary_role = occurrence["role"] in {*BUNDLE_ROLES, "ssi"}
            binary_format = m["format"] in {"hmmer_binary", "ssi", "msv_profiles", "remaining_profiles"}
            bindings = [b for b in self.sheet["artifact_bindings"] if isinstance(b, dict) and b.get("artifact_occurrence_id") == oid]
            binding_state = "not_applicable" if not binary_role else "unknown" if not bindings else (
                "pass" if len(bindings) == 1 and not _binding_errors(bindings[0], self.occurrences) and
                self.bytes_match(oid) and self.bytes_match(bindings[0]["source_occurrence_id"]) else "fail")
            if binary_role:
                self.check("supplied_artifact_binding", binding_state, row_key=oid, inputs=source+[_operand("artifact_bindings", occurrence_id=oid)])
                self.check("authenticated_artifact_custody", "unknown", row_key=oid, inputs=source)
            expected_format = {"binary_models": "hmmer_binary", "ssi_index": "ssi", "ssi": "ssi",
                "msv_profiles": "msv_profiles", "remaining_profiles": "remaining_profiles"}.get(occurrence["role"])
            if occurrence["role"] == "converted_models":
                expected_format = {"ascii": "hmmer3_ascii", "binary": "hmmer_binary", "legacy_hmmer2": "hmmer2_ascii"}[self.sheet["operation"]["mode"]]
            if binary_role or binary_format or occurrence["role"] == "converted_models":
                frame = ("pass" if m["format"] == expected_format and m["framing_state"] in {"prefix_recognized", "prefix_and_terminal_marker"}
                         else "fail" if expected_format is not None else "unknown")
                self.check("binary_framing", frame, row_key=oid, inputs=source)
            internal, internal_check = self.binary_content(oid) if binary_role or binary_format else ("not_applicable", "unknown")
            if binary_role or binary_format:
                self.check("binary_internal_content", internal_check, row_key=oid, inputs=source)
            if occurrence["direction"] == "output" and occurrence["role"] in required:
                self.check("member_nonempty", "pass" if m["measured_size_bytes"] > 0 else "fail", row_key=oid, inputs=source)
            revision = self.parameters.get("expected_revision")
            if occurrence["direction"] == "output" and occurrence["role"] in MODEL_ROLES | {"msv_profiles", "remaining_profiles"}:
                self.check("expected_revision", "not_applicable" if revision is None else "unknown" if m["revision"] is None else
                    "pass" if revision == m["revision"] else "fail", row_key=oid, inputs=source+[{"parameter": "expected_revision"}])
            e = self.extracts.get(oid)
            count = e["population"]["decoded_count"] if e else None
            count_state = ("incompatible" if count is None and (binary_role or binary_format or e) else "missing" if e is None else
                           "present" if e["population"]["complete"] else "incomplete")
            self.result["rows"].append({"kind": "artifact", "row_key": oid, "occurrence_id": oid,
                "size_bytes": _component(m["measured_size_bytes"], "present", "byte", source),
                "format": m["format"], "revision": m["revision"], "byte_order": m["byte_order"], "offset_width": m["offset_width"],
                "decoded_record_count": _component(count, count_state, "decoded_model_count", source),
                "supplied_binding_state": binding_state, "authenticated_custody_state": "unknown" if binary_role else "not_applicable",
                "internal_content_state": internal})

    def key_population(self, source_population, output_population):
        keys = [r for r in self.sheet["native_rows"] if r["kind"] == "requested_key"]
        resolutions = [r for r in self.sheet["associations"] if r["kind"] == "key_resolution"]
        pairs = [r for r in self.sheet["associations"] if r["kind"] == "model_pair"]
        inputs = [_operand("native_rows", row_key=k["row_key"]) for k in keys]
        key_occurrences = [o for o in self.occurrences.values() if o["role"] == "keys"]
        complete = (bool(keys) if self.sheet["operation"]["mode"] == "single_key" else bool(key_occurrences) and
                    all(o["completeness"] == "complete" and self.bytes_match(o["occurrence_id"]) for o in key_occurrences))
        state = "present" if complete else "incomplete"
        states = Counter(r["state"] for r in resolutions)
        selected = {k for r in resolutions for k in r["selected_source_record_keys"]}
        returned_sources = [r["source_record_keys"][0] for r in pairs if r["state"] == "matched"]
        all_returned = all(r["state"] == "matched" for r in pairs)
        row = {"kind": "key_population", "row_key": "key_population"}
        counts = {"requested_key_count": len(keys), "distinct_key_count": len({k["key"] for k in keys}),
            "resolved_key_count": states["resolved"], "missing_key_count": states["missing"],
            "ambiguous_key_count": states["ambiguous"], "unknown_key_count": states["unknown"],
            "fulfilled_key_count": sum(bool(r["output_record_keys"]) for r in resolutions),
            "duplicate_key_occurrence_count": len(keys)-len({k["key"] for k in keys}),
            "selected_source_occurrence_count": len(selected),
            "expected_returned_model_occurrence_count": sum(bool(r["source_record_keys"]) for r in pairs),
            "duplicate_representation_count": len(returned_sources)-len(set(returned_sources))}
        for name, value in counts.items():
            row[name] = _component(value, state if name != "duplicate_representation_count" or all_returned else "incomplete", name, inputs)
        for name in ("selected_source_occurrence_count", "expected_returned_model_occurrence_count"):
            source_state = source_population["decoded_model_count"]["state"]
            if source_state != "present":
                row[name]["state"] = source_state
                if source_population["decoded_model_count"]["value"] is None:
                    row[name]["value"] = None
        row["returned_model_occurrence_count"] = deepcopy(output_population["decoded_model_count"])
        self.result["rows"].append(row)
        for code, condition in (("requested_keys_unique", counts["duplicate_key_occurrence_count"] == 0),
                ("all_requested_keys_resolved", states["resolved"] == len(keys)),
                ("all_requested_keys_returned", counts["fulfilled_key_count"] == len(keys))):
            self.check(code, "pass" if condition and complete else "fail" if not condition and complete else "unknown", row_key=row["row_key"], inputs=inputs)
        self.check("fetch_output_population", "pass" if all_returned and complete and output_population["decoded_model_count"]["state"] == "present"
                   else "fail" if any(r["state"] in {"mismatch", "unexpected_output"} for r in pairs) else "unknown", row_key=row["row_key"], inputs=inputs)

    def index_summary(self, source_population):
        rows = [r for r in self.sheet["native_rows"] if r["kind"] == "index_summary"]
        summary = rows[0] if len(rows) == 1 else None
        row = {"kind": "index_summary", "row_key": "index_summary", "native_row_key": summary["row_key"] if summary else None}
        for name, population_key in (("model_count", "decoded_model_count"), ("primary_name_count", "primary_name_count"), ("accession_count", "accession_count")):
            source = deepcopy(source_population[population_key])
            native = _component(summary[name] if summary else None, "present" if summary else "incompatible" if rows else "missing",
                name, [_operand(name, row_key=summary["row_key"])] if summary else [])
            row["native_"+name] = native
            row["decoded_input_"+name] = source
            state = _state([source["state"], native["state"]])
            difference = native["value"]-source["value"] if state == "present" else None
            row[name+"_difference"] = _component(difference, state, name, source["inputs"]+native["inputs"])
            self.check("native_"+name, "unknown" if state != "present" else "pass" if difference == 0 else "fail",
                       row_key=row["row_key"], inputs=source["inputs"]+native["inputs"])
        self.result["rows"].append(row)

    def bundle(self):
        members = [o for o in self.occurrences.values() if o["direction"] == "output" and o["role"] in BUNDLE_ROLES]
        complete = len(members) == 4 and {o["role"] for o in members} == set(BUNDLE_ROLES)
        operands = [_operand("measured_size_bytes", occurrence_id=o["occurrence_id"]) for o in members]
        self.result["rows"].append({"kind": "bundle", "row_key": "pressed_bundle",
            "member_occurrence_ids": [o["occurrence_id"] for o in members],
            "member_count": _component(len(members), "present", "present_bundle_member_count", operands),
            "bundle_byte_sum": _component(sum(self.metadata[o["occurrence_id"]]["measured_size_bytes"] for o in members),
                "present" if complete else "incomplete", "byte", operands)})
        groups, binding_ok = [], True
        for o in members:
            bindings = [b for b in self.sheet["artifact_bindings"] if isinstance(b, dict) and b.get("artifact_occurrence_id") == o["occurrence_id"]]
            if len(bindings) != 1 or _binding_errors(bindings[0], self.occurrences):
                binding_ok = False
                continue
            groups.append(tuple(bindings[0][f] for f in ("source_occurrence_id", "source_sha256", "producer_attempt_id", "staged_source_stem")))
        self.check("bundle_supplied_attempt_consistency", "fail" if len(set(groups)) > 1 else
                   "pass" if complete and binding_ok else "unknown", row_key="pressed_bundle", inputs=[_operand("artifact_bindings")])
        revisions = {self.metadata[o["occurrence_id"]]["revision"] for o in members if o["role"] != "ssi_index"}
        self.check("bundle_revision_consistent", "pass" if complete and len(revisions) == 1 and None not in revisions else
                   "fail" if len(revisions-{None}) > 1 else "unknown", row_key="pressed_bundle", inputs=operands)


def _validate_sheet(sheet):
    """Validate saved joins/record copies before interpreting them as operands."""
    if (not isinstance(sheet, dict) or set(sheet) != SHEET_FIELDS or sheet.get("schema") != SHEET_SCHEMA
            or not _operation_valid(sheet.get("operation"))):
        return "sheet_invalid"
    if any(not isinstance(sheet[field], list) for field in SHEET_FIELDS - {"schema", "operation"}):
        return "sheet_invalid"
    if any(not isinstance(i, dict) or set(i) != {"code", "stage", "occurrence_id", "row_key", "field", "details"}
            or i["code"] not in DATA_ISSUE_CODES or i["stage"] != "extraction" or not isinstance(i["details"], dict)
            for i in sheet["issues"]):
        return "sheet_invalid"
    occurrences = sheet["artifact_occurrences"]
    if any(not _occurrence_valid(o) for o in occurrences) or len({o["occurrence_id"] for o in occurrences}) != len(occurrences):
        return "saved_reference_invalid"
    lookup = {o["occurrence_id"]: o for o in occurrences}
    ids = set()
    records = {"input": [], "output": []}
    for e in sheet["model_extractions"]:
        if (not isinstance(e, dict) or set(e) != {"schema", "occurrence", "format", "records", "population", "issues"}
                or e["schema"] != "hmmer_model_extraction_v1" or not _occurrence_valid(e["occurrence"])
                or not isinstance(e["records"], list) or not isinstance(e["population"], dict)):
            return "saved_reference_invalid"
        oid = e["occurrence"]["occurrence_id"]
        if oid in ids or lookup.get(oid) != e["occurrence"] or e["occurrence"]["role"] not in MODEL_ROLES:
            return "saved_reference_invalid"
        ids.add(oid)
        population = e["population"]
        if (set(population) != {"decoded_count", "complete", "state"} or type(population["complete"]) is not bool
                or population["state"] not in {"decoded", "partial", "unsupported", "invalid"}
                or population["complete"] != (population["state"] == "decoded")
                or population["decoded_count"] is not None and (type(population["decoded_count"]) is not int or population["decoded_count"] != len(e["records"]))):
            return "saved_reference_invalid"
        for i, r in enumerate(e["records"]):
            if (not isinstance(r, dict) or not _identity_valid(r, e["occurrence"], i)
                    or _representation_encoding(r) is None
                    or not isinstance(r.get("headers"), list) or not isinstance(r.get("positions"), list)
                    or not isinstance(r.get("initial"), dict) or not isinstance(r.get("issues"), list)
                    or any(not isinstance(p, dict) or not isinstance(p.get("annotations"), dict) for p in r["positions"])):
                return "saved_reference_invalid"
            if any(not isinstance(h, dict) or set(h) != {"tag", "value", "tokens", "line"}
                    or not isinstance(h["tag"], str) or not isinstance(h["value"], str)
                    or not isinstance(h["tokens"], list) or any(not isinstance(t, str) for t in h["tokens"])
                    for h in r["headers"]):
                return "saved_reference_invalid"
            if not isinstance(r.get("alphabet"), dict) or not isinstance(r["alphabet"].get("symbols"), list):
                return "saved_reference_invalid"
            for distribution in _distributions(r).values():
                if distribution is None:
                    continue
                if (not isinstance(distribution, dict) or set(distribution) != {"symbols", "cells", "line"}
                        or not isinstance(distribution["symbols"], list) or not isinstance(distribution["cells"], list)
                        or any(not isinstance(s, str) for s in distribution["symbols"])
                        or any(not isinstance(c, dict) or set(c) != ({"token", "negative_log_probability", "probability", "state"}
                            | ({"source"} if "representation" in r else set()))
                            for c in distribution["cells"])):
                    return "saved_reference_invalid"
        records[e["occurrence"]["direction"]].extend(e["records"])
    if records["input"] != sheet["input_records"] or records["output"] != sheet["output_records"]:
        return "saved_reference_invalid"
    metadata, row_ids = [], set()
    for row in sheet["native_rows"]:
        if not isinstance(row, dict) or row.get("kind") not in DATA_ROW_FIELDS or set(row) != DATA_ROW_FIELDS[row["kind"]]:
            return "saved_reference_invalid"
        if row["row_key"] in row_ids:
            return "saved_reference_invalid"
        row_ids.add(row["row_key"])
        oid = row.get("occurrence_id")
        if oid is not None and oid not in lookup:
            return "saved_reference_invalid"
        if row["kind"] == "artifact_metadata":
            metadata.append(oid)
            if type(row["measured_size_bytes"]) is not int or row["measured_size_bytes"] < 0 or not isinstance(row["measured_sha256"], str):
                return "saved_reference_invalid"
        elif row["kind"] == "requested_key":
            if not isinstance(row["key"], str) or not row["key"] or type(row["request_ordinal"]) is not int:
                return "saved_reference_invalid"
        elif row["kind"] == "index_summary":
            if any(type(row[name]) is not int or row[name] < 0 for name in ("model_count", "primary_name_count", "accession_count")):
                return "saved_reference_invalid"
    if len(metadata) != len(occurrences) or set(metadata) != set(lookup):
        return "saved_reference_invalid"
    try:
        if sheet["associations"] != _build_associations(sheet):
            return "saved_association_invalid"
    except (TypeError, ValueError, KeyError, AttributeError):
        return "saved_reference_invalid"
    return None


def calculate_hmmer_artifact_components(sheet, *, parameters=None):
    """Calculate inspectable artifact checks, counts and full body differences.

    ``probability_tolerance`` defaults to 1e-4 and never rescales probabilities.
    ``expected_revision`` is optional, using actual tags ``3/a`` through ``3/f``
    (or ``2.0`` for HMMER2). Missing and unsupported populations
    stay unavailable; explicit decoded empty artifacts retain measured zero.
    """
    supplied = {} if parameters is None else deepcopy(parameters)
    effective = {"probability_tolerance": 1e-4, **supplied} if isinstance(supplied, dict) else supplied
    result = {"schema": SCHEMA, "operation": deepcopy(sheet.get("operation")) if isinstance(sheet, dict) else None,
        "parameters": effective, "rows": [], "checks": [], "issues": []}
    try:
        invalid = _validate_sheet(sheet)
    except (KeyError, TypeError, AttributeError, ValueError, IndexError):
        invalid = "saved_reference_invalid"
    if invalid:
        result["issues"].append({"code": invalid, "stage": "calculation", "occurrence_id": None,
            "row_key": None, "field": "sheet", "details": {}})
        return result
    result["issues"] = deepcopy(sheet["issues"])
    if not isinstance(effective, dict):
        effective = {"probability_tolerance": None}
    calculator = _Calculator(sheet, effective, result)
    revision = effective.get("expected_revision")
    parameters_ok = (set(effective) <= {"probability_tolerance", "expected_revision"} and calculator.tolerance_valid
                     and (revision is None or isinstance(revision, str) and revision in {"3/a", "3/b", "3/c", "3/d", "3/e", "3/f", "2.0"}))
    calculator.check("parameters_valid", "pass" if parameters_ok else "fail", inputs=[{"parameter": "probability_tolerance"}, {"parameter": "expected_revision"}])
    if not parameters_ok:
        calculator.issue("parameter_invalid", field="parameters")
    source = calculator.population("input")
    output = calculator.population("output")
    calculator.artifacts()
    for association in sheet["associations"]:
        if association["kind"] == "model_pair":
            calculator.comparison(association)
    program, mode = sheet["operation"]["program"], sheet["operation"]["mode"]
    if program == "hmmconvert":
        a, b = source["decoded_model_count"], output["decoded_model_count"]
        calculator.check("conversion_population_equal", "unknown" if _state([a["state"], b["state"]]) != "present" else
            "pass" if a["value"] == b["value"] else "fail", inputs=a["inputs"]+b["inputs"])
        stdouts = [o for o in sheet["artifact_occurrences"] if o["role"] == "stdout"]
        calculator.check("conversion_stdout_equal", "fail" if any(i["code"] == "conversion_stdout_mismatch" for i in sheet["issues"])
            else "pass" if stdouts else "unknown", inputs=[_operand("artifact_occurrences", role="stdout")])
    if program == "hmmfetch" and mode != "index":
        calculator.key_population(source, output)
    if mode == "index":
        calculator.index_summary(source)
    if program == "hmmpress":
        calculator.bundle()
    diagnostics = [r for r in sheet["native_rows"] if r["kind"] == "diagnostic"]
    calculator.check("native_diagnostics", "fail" if any(r["code"] != "native_message" for r in diagnostics) else
        "not_applicable" if not diagnostics else "unknown", inputs=[_operand("native_rows", row_key=r["row_key"]) for r in diagnostics])
    return result
