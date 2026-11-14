"""Recalculate inspectable HMMER model components from saved extraction data.

Emission mass/residual, entropy and explicit-background relative entropy use
the decoded probabilities without normalization. Transition mass has three
outgoing populations, M=(MM,MI,MD), I=(IM,II), D=(DM,DD). No single seven-cell
transition normalization is scientifically meaningful. These are model
quantities, not observations, annotation confidence or execution credit.
"""
from __future__ import annotations

from copy import deepcopy
import math
import re
import struct

from .hmmer_model_data import (
    ALPHABETS, SCHEMA as EXTRACTION_SCHEMA, TRANSITIONS, _numeric, _occurrence_valid,
)
from .hmmer_model_source_cells import binary_probability_cell, hmmer2_probability_cell


SCHEMA = "hmmer_model_components_v1"
COMPONENT_STATES = frozenset({"present", "missing", "incomplete", "incompatible", "nonfinite"})
CHECK_STATES = frozenset({"pass", "fail", "unknown", "not_applicable"})
ISSUE_CODES = frozenset({"extraction_invalid", "record_invalid", "parameter_invalid",
    "background_invalid", "background_alphabet_mismatch", "background_mass_invalid",
    "background_support_zero", "distribution_invalid", "distribution_incomplete",
    "distribution_underflow", "probability_mass_outside_tolerance", "match_population_incomplete",
    "native_count_invalid", "ratio_denominator_zero", "nominal_probability_out_of_range",
    "probability_reference_missing", "distribution_not_in_topology",
    "transition_population_excludes_exit", "native_conversion_basis_incompatible"})
CHECK_CODES = frozenset({"population_complete", "probability_tolerance_valid",
    "background_compatible", "probability_mass", "match_population_complete"})
TRANSITION_GROUPS = {"M": (0, 1, 2), "I": (3, 4), "D": (5, 6)}


def _component(value=None, *, state="present", unit="dimensionless", inputs=()):
    assert state in COMPONENT_STATES
    return {"value": value, "state": state, "unit": unit, "inputs": deepcopy(list(inputs))}


def _finite(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


_ASCII_CELL_FIELDS = {"token", "negative_log_probability", "probability", "state"}
_REPRESENTATION_FIELDS = {"schema", "encoding", "topology", "byte_order", "binary_layout",
                          "header_semantics", "native_fields", "legacy"}
_LEGACY_FIELDS = {"null_emissions", "special_transitions", "null_transitions",
                  "begin_transitions", "entry_exit", "checksum", "evd"}


def _representation_encoding(record):
    """Return the declared supported encoding, never infer it from cell values."""
    if not isinstance(record, dict):
        return None
    if "representation" not in record:
        return ("hmmer3_ascii_negative_log_probability" if isinstance(record.get("format_tag"), str)
                and re.fullmatch(r"HMMER3/[a-f]", record["format_tag"]) else None)
    rep = record["representation"]
    if (type(rep) is not dict or set(rep) != _REPRESENTATION_FIELDS
            or rep["schema"] != "hmmer_model_representation_v1"
            or type(rep["encoding"]) is not str
            or type(rep["native_fields"]) is not list):
        return None
    if rep["encoding"] in {"hmmer3_binary_probability", "hmmer2_binary_probability"}:
        h2 = rep["encoding"] == "hmmer2_binary_probability"
        legacy_valid = (type(rep["legacy"]) is dict and set(rep["legacy"]) == _LEGACY_FIELDS
            if h2 else rep["legacy"] is None)
        if (rep["topology"] != ("hmmer2_configured" if h2 else "hmmer3_core") or rep["byte_order"] not in ("little", "big")
                or rep["binary_layout"] != "i32_u32_ieee754_binary32"
                or rep["header_semantics"] != "binary_field_projection" or not legacy_valid):
            return None
        if (not isinstance(record.get("format_tag"), str)
                or (record["format_tag"] != "HMMER2.0" if h2 else not re.fullmatch(r"HMMER3/[a-f]", record["format_tag"]))):
            return None
        for native in rep["native_fields"]:
            if (type(native) is not dict or set(native) != {
                    "field", "byte_start", "byte_end", "raw_hex", "value", "state"}
                    or not isinstance(native["field"], str) or type(native["raw_hex"]) is not str
                    or type(native["state"]) is not str
                    or native["state"] not in {"present", "unused", "native_missing_sentinel", "invalid", "truncated"}
                    or any(type(native[k]) is not int for k in ("byte_start", "byte_end"))):
                return None
            loc = record.get("locator", {})
            if not (type(loc.get("byte_start")) is int and type(loc.get("byte_end")) is int
                    and loc["byte_start"] <= native["byte_start"] <= native["byte_end"] <= loc["byte_end"]
                    and len(native["raw_hex"]) == 2 * (native["byte_end"] - native["byte_start"])
                    and re.fullmatch(r"[0-9a-f]*", native["raw_hex"])):
                return None
        return rep["encoding"]
    if rep["encoding"] == "hmmer2_ascii_millibit_log_odds":
        if (rep["topology"] == "hmmer2_configured" and rep["byte_order"] is None
                and rep["binary_layout"] is None and rep["header_semantics"] == "original_ascii_headers"
                and rep["native_fields"] == [] and type(rep["legacy"]) is dict
                and set(rep["legacy"]) == _LEGACY_FIELDS and record.get("format_tag") == "HMMER2.0"):
            return rep["encoding"]
    return None


def _hmmer2(record):
    return _representation_encoding(record) in {"hmmer2_ascii_millibit_log_odds", "hmmer2_binary_probability"}


def _field_name(field):
    if field.startswith("positions."):
        return field.rsplit(".", 1)[-1]
    return field


def _binary_scalar_value(record, field, kind, *, minimum=0, sentinel=-1):
    """Validate a retained native scalar before using its common projection."""
    encoding = _representation_encoding(record)
    matches = [n for n in record["representation"]["native_fields"] if n["field"] == field]
    operand = {"record_key": record["record_key"], "native_field": field,
               "source_encoding": encoding, "qualification": "binary_layout_interpretation"}
    if encoding == "hmmer2_binary_probability":
        if field == "EFFN":
            return None, "missing", [operand]
        from .hmmer_model_binary2 import binary2_header
        header = binary2_header(record)
        if header is None or len(matches) != 1 or matches[0] != header["fields"].get(field):
            return None, "incompatible", [operand]
        sentinel = None
    if len(matches) != 1:
        return None, "incompatible", [operand]
    native = matches[0]
    operand.update(byte_start=native["byte_start"], byte_end=native["byte_end"], raw_hex=native["raw_hex"])
    if native["byte_end"] - native["byte_start"] != 4 or len(native["raw_hex"]) != 8:
        return None, "incompatible", [operand]
    fixed_offset = ({"magic": 0, "flags": 4} if encoding == "hmmer2_binary_probability" else
        {"magic": 0, "flags": 4, "M": 8, "alphabet_type": 12}).get(field)
    if fixed_offset is not None and native["byte_start"] != record["locator"]["byte_start"] + fixed_offset:
        return None, "incompatible", [operand]
    raw = struct.unpack(("<" if record["representation"]["byte_order"] == "little" else ">") + kind,
                        bytes.fromhex(native["raw_hex"]))[0]
    finite = _finite(raw)
    if (finite and (not _finite(native["value"]) or native["value"] != raw)
            or not finite and native["value"] is not None):
        return None, "incompatible", [operand]
    state = ("native_missing_sentinel" if sentinel is not None and raw == sentinel
             else "invalid" if not finite or raw < minimum else "present")
    if native["state"] != state:
        return None, "incompatible", [operand]
    return (raw, "present", [operand]) if state == "present" else (
        None, "missing" if state == "native_missing_sentinel" else "incompatible", [operand])


def _binary_probability_start(record, field, position_ordinal, cell_index):
    """Source slot relationship for the declared fixed-layout probability arrays."""
    alphabet = record.get("alphabet", {})
    kind, symbols, length = alphabet.get("kind"), alphabet.get("symbols"), record.get("length")
    if kind not in ALPHABETS or symbols != ALPHABETS[kind] or type(length) is not int or length <= 0:
        return None
    if _representation_encoding(record) == "hmmer2_binary_probability":
        from .hmmer_model_binary2 import binary2_header, binary2_probability_start
        header = binary2_header(record)
        if (header is None or header["length"] != length
                or header["fields"]["alphabet_type"]["value"] != {"DNA": 2, "amino": 3}.get(kind)):
            return None
        return binary2_probability_start(record, field, position_ordinal, cell_index)
    native_length, length_state, _ = _binary_scalar_value(record, "M", "i", minimum=1, sentinel=None)
    native_alphabet, alphabet_state, _ = _binary_scalar_value(record, "alphabet_type", "i", minimum=1, sentinel=None)
    if (length_state != "present" or native_length != length or alphabet_state != "present"
            or native_alphabet != {"RNA": 1, "DNA": 2, "amino": 3}[kind]):
        return None
    width, base, name = len(symbols), record["locator"]["byte_start"] + 16, _field_name(field)
    if name in {"match", "insert", "transitions"}:
        if type(position_ordinal) is not int or not 0 <= position_ordinal < length:
            return None
        node = position_ordinal + 1
    else:
        node = 0
    if name == "match" and cell_index < width:
        return base + 4 * (position_ordinal * width + cell_index)
    if name in {"initial.insert", "insert"} and cell_index < width:
        return base + 4 * (length * width + node * width + cell_index)
    if name in {"initial.transitions", "transitions"} and cell_index < len(TRANSITIONS):
        return base + 4 * (length * width + (length + 1) * width + node * len(TRANSITIONS) + cell_index)
    if name == "composition" and cell_index < width:
        fields = record["representation"]["native_fields"]
        if fields and fields[-1]["field"] == "NC2" and fields[-1]["byte_end"] - fields[-1]["byte_start"] == 4:
            if record.get("terminated") is True and fields[-1]["byte_end"] + 4 * width != record["locator"]["byte_end"]:
                return None
            return fields[-1]["byte_end"] + 4 * cell_index
    return None


def validate_hmmer_probability_cell(cell: dict, *, record: dict, field: str,
        position_ordinal: int | None, cell_index: int) -> dict:
    """Validate one retained native source union; perform no acquisition.

    The scalar decoder also reconstructs saved binary/HMMER2 values. A changed
    token, integer, reference, byte locator or probability cannot acquire the
    meaning of a different encoding on recalculation.
    """
    encoding = _representation_encoding(record)
    qualification = ("hmmer2_quantized_nominal" if encoding == "hmmer2_ascii_millibit_log_odds"
        else "binary_layout_interpretation" if encoding in {"hmmer3_binary_probability", "hmmer2_binary_probability"} else None)
    operand = {"record_key": record.get("record_key"), "field": field,
               "position_ordinal": position_ordinal, "cell_index": cell_index}
    if encoding is not None:
        operand["source_encoding"] = encoding
    if qualification:
        operand["qualification"] = qualification
    result = {"probability": None, "state": "incompatible", "issue_code": "distribution_invalid",
              "qualification": qualification, "inputs": [operand]}
    if type(cell_index) is not int or cell_index < 0 or encoding is None or type(cell) is not dict:
        return result
    if encoding == "hmmer3_ascii_negative_log_probability":
        if set(cell) != _ASCII_CELL_FIELDS:
            return result
        native, probability = cell["negative_log_probability"], cell["probability"]
        token_value = _numeric(cell["token"], minimum=0)
        if (cell["state"] == "underflow" and _finite(native) and native == token_value
                and math.exp(-native) == 0 and probability is None):
            result.update(state="nonfinite", issue_code="distribution_underflow")
            return result
        valid = (_finite(probability) and 0 <= probability <= 1 and (
            (cell["state"] == "structural_zero" and cell["token"] == "*" and native is None and probability == 0)
            or (cell["state"] == "finite" and _finite(native) and native == token_value
                and probability > 0 and math.exp(-native) == probability)))
        if valid:
            result.update(probability=probability, state="present", issue_code=None)
        return result
    if set(cell) != _ASCII_CELL_FIELDS | {"source"} or type(cell["source"]) is not dict:
        return result
    source = cell["source"]
    if encoding in {"hmmer3_binary_probability", "hmmer2_binary_probability"}:
        if (set(source) != {"encoding", "raw_hex", "byte_start", "byte_end"}
                or source["encoding"] != "ieee754_binary32_probability"
                or type(source["raw_hex"]) is not str or not re.fullmatch(r"[0-9a-f]{8}", source["raw_hex"])
                or any(type(source[k]) is not int for k in ("byte_start", "byte_end"))):
            return result
        loc = record.get("locator", {})
        if not (type(loc.get("byte_start")) is int and type(loc.get("byte_end")) is int
                and loc["byte_start"] <= source["byte_start"] < source["byte_end"] <= loc["byte_end"]
                and source["byte_end"] - source["byte_start"] == 4
                and source["byte_start"] == _binary_probability_start(record, field, position_ordinal, cell_index)):
            return result
        expected = binary_probability_cell(bytes.fromhex(source["raw_hex"]), byte_start=source["byte_start"],
                                           byte_order=record["representation"]["byte_order"])
        operand.update(byte_start=source["byte_start"], byte_end=source["byte_end"], raw_hex=source["raw_hex"])
    else:
        if (set(source) != {"encoding", "score", "reference", "nominal_probability"}
                or source["encoding"] != "hmmer2_millibit_log_odds"
                or source["score"] is not None and type(source["score"]) is not int
                or source["nominal_probability"] is not None and not _finite(source["nominal_probability"])):
            return result
        name, ref_cell = _field_name(field), None
        symbols = record.get("alphabet", {}).get("symbols", [])
        wanted = ({"kind": "nule", "cell_index": cell_index} if name in {"match", "insert"}
            else {"kind": "uniform_alphabet", "denominator": len(symbols)} if name == "legacy.null_emissions"
            else {"kind": "unit"})
        if source["reference"] != wanted:
            return result
        operand.update(score=source["score"], reference=deepcopy(source["reference"]))
        if wanted["kind"] == "nule" and cell.get("token") != "*":
            nulls = record["representation"]["legacy"]["null_emissions"]
            if nulls is None and any(issue.get("field") == "NULE" and issue.get("code") in
                    {"header_duplicate", "header_width_invalid", "header_number_invalid"}
                    for issue in record.get("issues", []) if isinstance(issue, dict)):
                operand.update(reference_state="incompatible", reference_reason="malformed_or_ambiguous_nule")
                return result
            if nulls is not None:
                if (type(nulls) is not dict or set(nulls) != {"symbols", "cells", "line"}
                        or nulls["symbols"] != symbols or type(nulls["cells"]) is not list
                        or len(nulls["cells"]) > len(symbols)):
                    return result
                if cell_index < len(nulls["cells"]):
                    ref_cell = nulls["cells"][cell_index]
                    checked = validate_hmmer_probability_cell(ref_cell, record=record,
                        field="legacy.null_emissions", position_ordinal=None, cell_index=cell_index)
                    result["inputs"].extend(checked["inputs"])
                    if checked["state"] == "present" and checked["probability"] == 0:
                        operand.update(reference_state="structural_zero", reference_probability=0.0,
                            reference_reason="finite_log_odds_against_zero_null")
                    if checked["state"] != "present" and cell.get("token") != "*":
                        # Still verify the stored dependent cell below. The shared
                        # decoder preserves invalid/missing reference distinctions.
                        operand["reference_state"] = checked["state"]
                        if checked["state"] == "incompatible":
                            # Source self-consistency cannot override this
                            # record's actual alphabet/reference relationship.
                            return result
        expected = hmmer2_probability_cell(cell["token"], reference=source["reference"], reference_cell=ref_cell)
    if expected != cell:
        return result
    probability = expected["probability"]
    if probability is not None and not _finite(cell["probability"]):
        return result
    if probability == 0 and math.copysign(1, probability) != math.copysign(1, cell["probability"]):
        return result
    state = expected["state"]
    if state in {"finite", "structural_zero"}:
        result.update(probability=probability, state="present", issue_code=None)
    elif state == "underflow":
        result.update(state="nonfinite", issue_code="distribution_underflow")
    elif state == "quantized_out_of_range":
        result["issue_code"] = "nominal_probability_out_of_range"
    elif state == "reference_missing":
        result.update(state="missing", issue_code="probability_reference_missing")
    return result


def validate_hmmer_probability_vector(distribution: dict | None, *, record: dict,
        field: str, position_ordinal: int | None, symbols: list[str],
        indices: tuple[int, ...], required: bool = True) -> dict:
    """One vector authority for native encodings and actual source topology."""
    result = {"values": None, "state": "incompatible", "issue_code": "distribution_invalid",
              "qualification": None, "inputs": []}
    encoding = _representation_encoding(record)
    if encoding is None:
        return result
    h2 = encoding in {"hmmer2_ascii_millibit_log_odds", "hmmer2_binary_probability"}
    result["qualification"] = ("hmmer2_quantized_nominal" if encoding == "hmmer2_ascii_millibit_log_odds" else
        "binary_layout_interpretation" if encoding in {"hmmer3_binary_probability", "hmmer2_binary_probability"} else None)
    name = _field_name(field)
    if h2 and (name in {"initial.insert", "initial.transitions"} or
            name in {"insert", "transitions"} and type(record.get("length")) is int
            and position_ordinal == record["length"] - 1):
        result.update(issue_code="distribution_not_in_topology", qualification="hmmer2_state_absent")
        result["inputs"] = [{"record_key": record["record_key"], "field": field,
            "position_ordinal": position_ordinal, "source_encoding": encoding, "qualification": "hmmer2_state_absent"}]
        return result
    if distribution is None:
        result.update(state="incomplete" if required else "missing", issue_code=None)
        return result
    if (type(distribution) is not dict or set(distribution) != {"symbols", "cells", "line"}
            or distribution["symbols"] != symbols or type(distribution["cells"]) is not list
            or any(type(index) is not int or not 0 <= index < len(symbols) for index in indices)):
        return result
    cells = distribution["cells"]
    if len(cells) > len(symbols):
        return result
    if any(index >= len(cells) for index in indices):
        result.update(state="incomplete", issue_code="distribution_incomplete")
        return result
    values = []
    for index in indices:
        checked = validate_hmmer_probability_cell(cells[index], record=record,
            field=field, position_ordinal=position_ordinal, cell_index=index)
        result["inputs"].extend(checked["inputs"])
        if checked["state"] != "present":
            result.update(state=checked["state"], issue_code=checked["issue_code"])
            return result
        values.append(checked["probability"])
    result.update(values=values, state="present", issue_code=None)
    if h2 and name == "transitions" and tuple(indices) == TRANSITION_GROUPS["M"]:
        exits = record["representation"]["legacy"]["entry_exit"]
        exit_cell = None
        if (type(exits) is list and type(position_ordinal) is int and 0 <= position_ordinal < len(exits)):
            row = exits[position_ordinal]
            if (type(row) is dict and set(row) == {"position", "cells", "line"}
                    and row["position"] == position_ordinal + 1 and type(row["cells"]) is list
                    and len(row["cells"]) == 2):
                exit_cell = row["cells"][1]
        checked = validate_hmmer_probability_cell(exit_cell, record=record,
            field="legacy.entry_exit", position_ordinal=position_ordinal, cell_index=1)
        result["inputs"].extend(checked["inputs"])
        labels_valid = not any(issue.get("code") == "transition_labels_invalid"
                               for issue in record.get("issues", []) if isinstance(issue, dict))
        if not labels_valid or checked["state"] != "present" or checked["probability"] != 0:
            result.update(qualification="hmmer2_core_subvector", issue_code="transition_population_excludes_exit")
    return result


class _Calculator:
    def __init__(self, background, tolerance, result):
        self.background, self.tolerance, self.result = background, tolerance, result
        self.tolerance_valid = _finite(tolerance) and tolerance >= 0

    def issue(self, code, key=None, position=None, field=None, **details):
        assert code in ISSUE_CODES
        self.result["issues"].append({"code": code, "stage": "calculation",
            "record_key": key, "position": position, "field": field, "details": details})

    def check(self, code, state, *, key=None, position=None, field=None, inputs=()):
        assert code in CHECK_CODES and state in CHECK_STATES
        self.result["checks"].append({"code": code, "state": state, "record_key": key,
            "position": position, "field": field, "inputs": deepcopy(list(inputs))})

    def background_for(self, key, symbols):
        source = [{"parameter": "background", "symbols": symbols},
                  {"parameter": "probability_tolerance"}]
        if self.background is None:
            state = "missing"
            check = "not_applicable"
        elif not isinstance(self.background, dict) or any(
                not isinstance(symbol, str) or not _finite(value) or not 0 <= value <= 1
                for symbol, value in self.background.items()):
            state, check = "incompatible", "fail"
            self.issue("background_invalid", key, field="background")
        elif len(symbols) != len(set(symbols)) or set(self.background) != set(symbols):
            state, check = "incompatible", "fail"
            self.issue("background_alphabet_mismatch", key, field="background",
                       expected=symbols, supplied=list(self.background))
        elif not self.tolerance_valid:
            state, check = "incompatible", "unknown"
        elif abs(math.fsum(self.background.values()) - 1.0) > self.tolerance:
            state, check = "incompatible", "fail"
            self.issue("background_mass_invalid", key, field="background",
                       mass=math.fsum(self.background.values()))
        else:
            state, check = "present", "pass"
        self.check("background_compatible", check, key=key, field="background", inputs=source)
        return state

    def distribution(self, data, symbols, key, position, field, *, indices=None,
                     ordinal=None, required=True):
        indices = list(range(len(symbols))) if indices is None else list(indices)
        inputs = [{"record_key": key, "position": position, "position_ordinal": ordinal,
                   "field": field, "cell_indices": indices, "symbols": [symbols[i] for i in indices]}]
        checked = validate_hmmer_probability_vector(data, record=self.record, field=field,
            position_ordinal=ordinal, symbols=symbols, indices=tuple(indices), required=required)
        vector, state = checked["values"], checked["state"]
        if checked["issue_code"]:
            details = {}
            if checked["inputs"]:
                details["cell"] = checked["inputs"][-1].get("cell_index")
            self.issue(checked["issue_code"], key, position, field, **details)
        if "representation" in self.record:
            inputs[0].update(source_encoding=self.record["representation"]["encoding"],
                             qualification=checked["qualification"])
            inputs += checked["inputs"]
        mass = math.fsum(vector) if vector is not None else None
        residual = mass - 1.0 if mass is not None else None
        result = {"mass": _component(mass, state=state, unit="probability_mass", inputs=inputs),
                  "mass_residual": _component(residual, state=state, unit="probability_mass", inputs=inputs)}
        check_inputs = inputs + [{"parameter": "probability_tolerance"}]
        if checked["qualification"] in {"hmmer2_state_absent", "hmmer2_core_subvector"}:
            check = "not_applicable"
        elif vector is None or not self.tolerance_valid:
            check = "not_applicable" if not required and data is None else "unknown"
        else:
            check = "pass" if abs(residual) <= self.tolerance else "fail"
            if check == "fail":
                self.issue("probability_mass_outside_tolerance", key, position, field,
                           residual=residual, cell_indices=indices)
        self.check("probability_mass", check, key=key, position=position, field=field, inputs=check_inputs)
        return result, vector, state, inputs

    def transitions(self, data, key, position, field, *, ordinal=None):
        return {group: self.distribution(data, TRANSITIONS, key, position, field,
                    indices=indices, ordinal=ordinal)[0]
                for group, indices in TRANSITION_GROUPS.items()}

    def count(self, record, field, *, integer=False, unit="sequence_count"):
        number = record.get(field)
        inputs = [{"record_key": record["record_key"], "field": field}]
        if _representation_encoding(record) in {"hmmer3_binary_probability", "hmmer2_binary_probability"}:
            native_field = {"sequence_count": "NSEQ", "effective_sequence_count": "EFFN", "length": "M"}[field]
            expected, state, source = _binary_scalar_value(record, native_field, "i" if integer else "f",
                minimum=1 if field == "length" else 0, sentinel=None if field == "length" else -1)
            inputs += source
            if number != expected or number is not None and not _finite(number) or integer and number is not None and type(number) is not int:
                number, state = None, "incompatible"
            if state == "incompatible":
                self.issue("native_count_invalid", record["record_key"], field=field)
            return _component(number, state=state, unit=unit, inputs=inputs)
        if number is None:
            header = {"sequence_count": "NSEQ", "effective_sequence_count": "EFFN", "length": "LENG"}[field]
            invalid_header = any(isinstance(issue, dict) and issue.get("field") == header
                and issue.get("code") in {"header_duplicate", "header_width_invalid", "header_number_invalid",
                                          "binary_native_value_invalid"}
                for issue in record.get("issues", []))
            state = "incompatible" if invalid_header else "missing"
            if invalid_header:
                self.issue("native_count_invalid", record["record_key"], field=field)
        elif not _finite(number) or number < 0 or (integer and type(number) is not int):
            self.issue("native_count_invalid", record["record_key"], field=field)
            number, state = None, "incompatible"
        else:
            state = "present"
        return _component(number, state=state, unit=unit, inputs=inputs)

    def row(self, record):
        key = record["record_key"]
        if _representation_encoding(record) is None:
            self.issue("record_invalid", key, field="representation")
            return None
        self.record = record
        alphabet = record.get("alphabet")
        if (not isinstance(alphabet, dict) or not isinstance(alphabet.get("kind"), str)
                or alphabet["kind"] not in ALPHABETS):
            self.issue("record_invalid", key, field="alphabet")
            return None
        symbols = ALPHABETS[alphabet["kind"]]
        # A relabeled or reordered symbol header must not silently redefine native cells.
        if alphabet.get("symbols") != symbols:
            self.issue("record_invalid", key, field="alphabet.symbols")
            return None
        positions, initial = record.get("positions"), record.get("initial")
        if not isinstance(positions, list) or not isinstance(initial, dict):
            self.issue("record_invalid", key, field="positions/initial")
            return None
        background_state = self.background_for(key, symbols)
        nseq = self.count(record, "sequence_count", integer=True)
        effn = self.count(record, "effective_sequence_count", unit="effective_sequence_count")
        ratio_inputs = [{**deepcopy(operand), "role": role}
            for component, role in ((nseq, "denominator"), (effn, "numerator")) for operand in component["inputs"]]
        ratio_state = _combined_state([nseq, effn])
        ratio = None
        if ratio_state == "present":
            if nseq["value"] == 0:
                ratio_state = "nonfinite"
                self.issue("ratio_denominator_zero", key, field="effective_sequence_ratio")
            else:
                ratio = effn["value"] / nseq["value"]
        result = {"record_key": key, "alphabet": deepcopy(alphabet),
            "composition": self.distribution(record.get("composition"), symbols, key, None,
                                               "composition", required=False)[0],
            "initial": {"insert": self.distribution(initial.get("insert"), symbols, key, 0,
                                                       "initial.insert")[0],
                        "transitions": self.transitions(initial.get("transitions"), key, 0,
                                                        "initial.transitions")},
            "positions": [], "sequence_count": nseq, "effective_sequence_count": effn,
            "effective_sequence_ratio": _component(ratio, state=ratio_state,
                unit="effective_sequences_per_input_sequence", inputs=ratio_inputs),
            "declared_length": self.count(record, "length", integer=True, unit="match_state_count"),
            "match_state_count": _component(len(positions), unit="decoded_match_row_count",
                inputs=[{"record_key": key, "field": "positions", "population": "decoded_match_rows"}]),
        }
        valid_positions = True
        for ordinal, position in enumerate(positions):
            if not isinstance(position, dict):
                self.issue("record_invalid", key, field="positions", position_ordinal=ordinal)
                valid_positions = False
                result["positions"].append({"position": None, "position_ordinal": ordinal,
                    "entropy": _component(state="incompatible", unit="bit"),
                    "relative_entropy": _component(state="incompatible", unit="bit")})
                continue
            native_position = position.get("position")
            if type(native_position) is not int or native_position != ordinal + 1:
                valid_positions = False
            match, vector, state, inputs = self.distribution(position.get("match"), symbols,
                key, native_position, "match", ordinal=ordinal)
            entropy = math.fsum(-p * math.log2(p) for p in vector if p) if vector is not None else None
            entropy_component = _component(entropy, state=state, unit="bit", inputs=inputs)
            relative, relative_state = None, state if state != "present" else background_state
            relative_inputs = inputs + [{"parameter": "background", "symbols": symbols}]
            if relative_state == "present":
                if any(p > 0 and self.background[symbol] == 0 for p, symbol in zip(vector, symbols)):
                    relative_state = "nonfinite"
                    self.issue("background_support_zero", key, native_position, "relative_entropy")
                else:
                    relative = math.fsum(p * (math.log2(p) - math.log2(self.background[symbol]))
                                         for p, symbol in zip(vector, symbols) if p)
            result["positions"].append({"position": native_position, "position_ordinal": ordinal,
                "match": match,
                "insert": self.distribution(position.get("insert"), symbols, key, native_position,
                                             "insert", ordinal=ordinal)[0],
                "transitions": self.transitions(position.get("transitions"), key, native_position,
                                                "transitions", ordinal=ordinal),
                "entropy": entropy_component,
                "relative_entropy": _component(relative, state=relative_state, unit="bit", inputs=relative_inputs)})
        complete = (valid_positions and type(record.get("length")) is int and record["length"] > 0
                    and len(positions) == record["length"] and record.get("terminated") is True)
        mean_inputs = [{"record_key": key, "field": "length", "role": "denominator"},
                       {"record_key": key, "field": "positions", "population": "all_declared_match_positions"}]
        if "representation" in record:
            mean_inputs[1].update(source_encoding=record["representation"]["encoding"],
                qualification="hmmer2_quantized_nominal" if _representation_encoding(record) == "hmmer2_ascii_millibit_log_odds" else "binary_layout_interpretation")
        self.check("match_population_complete", "pass" if complete else "fail", key=key,
                   field="positions", inputs=mean_inputs)
        if not complete:
            self.issue("match_population_incomplete", key, field="positions")
        for name in ("entropy", "relative_entropy"):
            components = [position[name] for position in result["positions"]]
            state = _combined_state(components) if complete else "incomplete"
            value = (math.fsum(component["value"] for component in components) / record["length"]
                     if state == "present" else None)
            inputs = mean_inputs + [{"record_key": key, "field": "positions." + name}]
            if name == "relative_entropy":
                inputs += [{"parameter": "background", "symbols": symbols}]
            result["mean_match_" + name] = _component(value, state=state, unit="bit_per_match_position", inputs=inputs)
        return result


def _combined_state(components):
    for state in ("incompatible", "nonfinite", "incomplete", "missing"):
        if any(component["state"] == state for component in components):
            return state
    return "present"


def _identity_valid(record, occurrence, ordinal):
    """Saved JSON cannot silently redirect operands to another occurrence."""
    if (record.get("record_key") != occurrence["occurrence_id"] + "#model/" + str(ordinal)
            or not isinstance(record.get("locator"), dict)):
        return False
    locator = record["locator"]
    if (locator.get("artifact_ref") != occurrence["artifact_ref"]
            or type(locator.get("record_ordinal")) is not int or locator["record_ordinal"] != ordinal):
        return False
    if any(type(locator.get(key)) is not int for key in ("byte_start", "byte_end")):
        return False
    if _representation_encoding(record) in {"hmmer3_binary_probability", "hmmer2_binary_probability"}:
        lines_valid = locator.get("line_start") is None and locator.get("line_end") is None
    else:
        lines_valid = (type(locator.get("line_start")) is int and type(locator.get("line_end")) is int
                       and 1 <= locator["line_start"] <= locator["line_end"])
    return 0 <= locator["byte_start"] < locator["byte_end"] <= occurrence["size_bytes"] and lines_valid


def calculate_hmmer_model_components(extraction: dict, *, background=None,
                                     probability_tolerance=1e-4) -> dict:
    """Calculate from saved arrays and exact explicit parameters, with no I/O.

    Tolerance controls mass checks and background compatibility, never silently
    normalizes or rounds values. Means require every declared match position and
    a terminated record; complete prefix models remain calculable even when the
    enclosing capture is partial. The match-state count is explicitly the number
    of decoded match rows, alongside the separately retained declared length.
    """
    result = {"schema": SCHEMA, "parameters": {"background": deepcopy(background),
              "probability_tolerance": deepcopy(probability_tolerance)},
              "rows": [], "checks": [], "issues": []}
    calculator = _Calculator(background, probability_tolerance, result)
    calculator.check("probability_tolerance_valid", "pass" if calculator.tolerance_valid else "fail",
                     field="probability_tolerance", inputs=[{"parameter": "probability_tolerance"}])
    if not calculator.tolerance_valid:
        calculator.issue("parameter_invalid", field="probability_tolerance")
    if (not isinstance(extraction, dict) or extraction.get("schema") != EXTRACTION_SCHEMA
            or not isinstance(extraction.get("records"), list)
            or not isinstance(extraction.get("population"), dict)
            or not _occurrence_valid(extraction.get("occurrence"))):
        calculator.issue("extraction_invalid", field="extraction")
        return result
    population = extraction["population"]
    calculator.check("population_complete",
        "pass" if population.get("complete") is True else
        "not_applicable" if population.get("state") == "unsupported" else "unknown",
        field="population", inputs=[{"field": "population"}])
    for ordinal, record in enumerate(extraction["records"]):
        if not isinstance(record, dict) or not _identity_valid(record, extraction["occurrence"], ordinal):
            calculator.issue("record_invalid", field="record_key")
            continue
        row = calculator.row(record)
        if row is not None:
            result["rows"].append(row)
    return result
