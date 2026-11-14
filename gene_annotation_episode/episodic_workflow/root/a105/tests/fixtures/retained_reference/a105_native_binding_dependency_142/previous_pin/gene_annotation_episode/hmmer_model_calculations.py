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

from .hmmer_model_data import (
    ALPHABETS, SCHEMA as EXTRACTION_SCHEMA, TRANSITIONS, _numeric, _occurrence_valid,
)


SCHEMA = "hmmer_model_components_v1"
COMPONENT_STATES = frozenset({"present", "missing", "incomplete", "incompatible", "nonfinite"})
CHECK_STATES = frozenset({"pass", "fail", "unknown", "not_applicable"})
ISSUE_CODES = frozenset({"extraction_invalid", "record_invalid", "parameter_invalid",
    "background_invalid", "background_alphabet_mismatch", "background_mass_invalid",
    "background_support_zero", "distribution_invalid", "distribution_incomplete",
    "distribution_underflow", "probability_mass_outside_tolerance", "match_population_incomplete",
    "native_count_invalid", "ratio_denominator_zero"})
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

    def vector(self, distribution, symbols, indices, key, position, field, *, required=True):
        if distribution is None:
            return None, "incomplete" if required else "missing"
        if (not isinstance(distribution, dict) or distribution.get("symbols") != symbols
                or not isinstance(distribution.get("cells"), list)):
            self.issue("distribution_invalid", key, position, field)
            return None, "incompatible"
        cells = distribution["cells"]
        if len(cells) > len(symbols):
            self.issue("distribution_invalid", key, position, field)
            return None, "incompatible"
        if any(index >= len(cells) for index in indices):
            self.issue("distribution_incomplete", key, position, field)
            return None, "incomplete"
        vector = []
        for index in indices:
            cell = cells[index]
            if not isinstance(cell, dict) or set(cell) != {"token", "negative_log_probability", "probability", "state"}:
                self.issue("distribution_invalid", key, position, field, cell=index)
                return None, "incompatible"
            native, probability = cell["negative_log_probability"], cell["probability"]
            token_value = _numeric(cell["token"], minimum=0)
            if (cell["state"] == "underflow" and _finite(native) and native == token_value
                    and math.exp(-native) == 0 and probability is None):
                self.issue("distribution_underflow", key, position, field, cell=index)
                return None, "nonfinite"
            valid = (_finite(probability) and 0 <= probability <= 1 and (
                (cell["state"] == "structural_zero" and cell["token"] == "*"
                 and native is None and probability == 0)
                or (cell["state"] == "finite" and _finite(native) and native == token_value
                    and probability > 0 and math.exp(-native) == probability)))
            if not valid:
                self.issue("distribution_invalid", key, position, field, cell=index)
                return None, "incompatible"
            vector.append(probability)
        return vector, "present"

    def distribution(self, data, symbols, key, position, field, *, indices=None,
                     ordinal=None, required=True):
        indices = list(range(len(symbols))) if indices is None else list(indices)
        inputs = [{"record_key": key, "position": position, "position_ordinal": ordinal,
                   "field": field, "cell_indices": indices, "symbols": [symbols[i] for i in indices]}]
        vector, state = self.vector(data, symbols, indices, key, position, field, required=required)
        mass = math.fsum(vector) if vector is not None else None
        residual = mass - 1.0 if mass is not None else None
        result = {"mass": _component(mass, state=state, unit="probability_mass", inputs=inputs),
                  "mass_residual": _component(residual, state=state, unit="probability_mass", inputs=inputs)}
        check_inputs = inputs + [{"parameter": "probability_tolerance"}]
        if vector is None or not self.tolerance_valid:
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
        if number is None:
            header = {"sequence_count": "NSEQ", "effective_sequence_count": "EFFN", "length": "LENG"}[field]
            invalid_header = any(isinstance(issue, dict) and issue.get("field") == header
                and issue.get("code") in {"header_duplicate", "header_width_invalid", "header_number_invalid"}
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
        ratio_inputs = deepcopy(nseq["inputs"] + effn["inputs"])
        ratio_inputs[0]["role"] = "denominator"
        ratio_inputs[1]["role"] = "numerator"
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
    if any(type(locator.get(key)) is not int for key in ("byte_start", "byte_end", "line_start", "line_end")):
        return False
    return (0 <= locator["byte_start"] < locator["byte_end"] <= occurrence["size_bytes"]
            and 1 <= locator["line_start"] <= locator["line_end"])


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
