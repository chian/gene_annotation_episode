"""Synthetic source/parsed-model tests only; no primary paper or model run."""
from copy import deepcopy
from fractions import Fraction
import errno
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re

from PIL import Image
import pytest

from gene_annotation_episode.domain import ContractError, identity
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode import literature_controlled_response_inputs as reader
from gene_annotation_episode.literature_controlled_response_calculations import populate_controlled_response


PIN = Path(__file__).resolve().parents[1] / "verification/literature_reference_evidence_2026-10-25_001/a105_controlled_response_design_056/reader_stage_007"


class Fixture:
    """Fresh invented source namespace, never a Store or scientific receipt."""
    def __init__(self, shared=False):
        original = json.loads((PIN / "COMPATIBILITY_RECEIPT_007.json").read_text())
        case = original["shared_control" if shared else "ordinary"]
        self.args = deepcopy(case["selection"])
        self.main_ref = self.args["source_ref"]
        self.cov_ref = self.args["covariance"]["source_ref"]
        self.doc = deepcopy(case["source_covariance"])
        self.data = {self.main_ref: (PIN / "SOURCE_TEXT_007.txt").read_bytes()}
        for name in ("ordinary", "shared_control"):
            selected = original[name]["selection"]
            self.data[selected["covariance"]["source_ref"]] = json.dumps(original[name]["source_covariance"], indent=2, ensure_ascii=False).encode()
        self.calls = []

    def source(self, reference, representation):
        self.calls.append((reference, representation))
        assert representation == "original"
        raw = self.data[reference]
        return {"artifact_ref": identity("artifact", hashlib.sha256(raw).hexdigest()), "content": raw}

    def witness(self, quote, reference=None, start=0, tagged=False):
        reference = reference or self.main_ref
        text = self.data[reference].decode()
        at = text.index(quote, start)
        value = {"source_ref": reference, "representation": "original", "start": len(text[:at].encode()),
                 "end": len(text[:at + len(quote)].encode()), "quote": quote}
        return {"kind": "text", **value} if tagged else value

    def number(self, quote, token):
        start = quote.index(token)
        return {"witness": self.witness(quote), "number_start": start, "number_end": start + len(token)}

    def reanchor(self, reference):
        def walk(value):
            if isinstance(value, dict):
                if value.get("source_ref") == reference and "quote" in value:
                    fresh = self.witness(value["quote"], reference)
                    value.update(fresh)
                for item in value.values(): walk(item)
            elif isinstance(value, list):
                for item in value: walk(item)
        walk(self.args)

    def covariance(self, *, ensure_ascii=False):
        self.data[self.cov_ref] = json.dumps(self.doc, indent=2, ensure_ascii=ensure_ascii).encode()
        # Independent fixture lexer: only variables have label keys. Use exact
        # ordered token positions, not the implementation parser or text equality.
        text = self.data[self.cov_ref].decode()
        labels = list(re.finditer(r'"label":\s*("(?:[^"\\]|\\.)*")', text))
        for role, binding in self.args["covariance"]["bindings"].items():
            if binding is None: continue
            token = labels[binding["variable_index"]]
            at, end = token.span(1)
            binding["label_witness"] = {"source_ref": self.cov_ref, "representation": "original",
                "start": len(text[:at].encode()), "end": len(text[:end].encode()), "quote": token[1]}
            binding["correspondence"]["witnesses"][0] = {"kind": "text", **binding["label_witness"]}
        for field in ("variance_status", "model_kind"):
            selected = self.args[field]
            if selected["witnesses"] and selected["witnesses"][0]["source_ref"] == self.cov_ref:
                quote = json.dumps(self.doc[field])
                selected["witnesses"] = [self.witness(quote, self.cov_ref, tagged=True)]

    def read(self):
        return reader.read_controlled_response_inputs(self.args, read_source=self.source)

    def replace_line(self, old, new):
        self.data[self.main_ref] = self.data[self.main_ref].replace(old.encode(), new.encode())
        def walk(value):
            if isinstance(value, dict):
                if "number_start" in value and value["witness"]["quote"] == old:
                    prefix = old[:value["number_start"]]
                    suffix = old[value["number_end"]:]
                    assert new.startswith(prefix) and new.endswith(suffix)
                    value["number_end"] = len(new) - len(suffix)
                if value.get("source_ref") == self.main_ref and "quote" in value:
                    value["quote"] = value["quote"].replace(old, new)
                for item in value.values(): walk(item)
            elif isinstance(value, list):
                for item in value: walk(item)
        walk(self.args)
        self.reanchor(self.main_ref)
        for variable in self.doc["variables"]:
            variable["description"] = variable["description"].replace(old, new)
        self.covariance()

    def append(self, text):
        self.data[self.main_ref] += ("<p>" + text + "</p>\n").encode()


def set_measurement(f, role, text, token, unit="nmol/min/mg"):
    f.append(text)
    arm = f.args["arms"][role]
    arm["measurement"] = {"kind": "source_literal", "literal": {"status": "exact",
        "candidates": [f.number(text, token)], "fragments": []},
        "unit": f.witness(unit, start=f.data[f.main_ref].decode().index(text))}


def interpretation(fixture, value, quote=None):
    return {"value": value, "witnesses": [] if quote is None else [fixture.witness(quote, tagged=True)]}


def test_exact_closed_schema_and_both_accepted_source_label_projections():
    assert reader.controlled_response_arguments_schema() == json.loads((PIN / "SELECTION_SCHEMA_007.json").read_text())
    schema = reader.controlled_response_arguments_schema(); schema["properties"].clear()
    assert reader.controlled_response_arguments_schema()["properties"]
    for shared, e, variance in ((False, .006, .0000017), (True, .007, .00000136)):
        f = Fixture(shared)
        original = deepcopy(f.args)
        result = f.read()
        assert f.args == original
        assert result["selection"] == original
        assert result["covariance"]["source_validation"] == "valid"
        assert result["covariance"]["projection_state"] == "available"
        assert result["effective_model"]["variance_status"] == "known"
        assert result["calculation_inputs"]["arms"]["protein_condition1"]["value"] == 12
        assert result["calculation_inputs"]["arms"]["protein_condition1"]["unit"] == "nmol/min/mg"
        sheet = populate_controlled_response(result["calculation_inputs"])
        assert sheet["cells"]["controlled_response_difference"]["value"] == e
        assert sheet["cells"]["contrast_variance"]["value"] == variance
        assert sheet["cells"]["source_profile_log_ratio"]["value"] is None
        assert all(owner not in f.data[f.cov_ref].decode() for owner in result["calculation_inputs"]["covariance"]["physical_observation_ids"])
        assert len(f.calls) == len(set(f.calls))  # Prefetch once, helpers use cache.
        assert reader.validate_controlled_response_extraction(f.args, result) == result
        json.dumps(result, allow_nan=False)


def test_source_reader_cannot_call_a_sheet_calculator(monkeypatch):
    import gene_annotation_episode.literature_controlled_response_calculations as calculator
    def forbidden(*args, **kwargs): raise AssertionError("scientific sheet calculation")
    monkeypatch.setattr(calculator, "populate_controlled_response", forbidden)
    assert Fixture().read()["calculation_inputs"]["version"] == "controlled_response_inputs_v1"


def test_entire_callback_authorization_phase_precedes_any049_helper(monkeypatch):
    f = Fixture()
    calls = []
    closure = reader._reference_closure(f.args)
    denied = closure[-1]
    def callback(reference, representation):
        calls.append((reference, representation))
        if (reference, representation) == denied:
            raise ContractError("source_out_of_scope")
        return f.source(reference, representation)
    def forbidden(*args, **kwargs): raise AssertionError("049 constructed before authorization completed")
    monkeypatch.setattr(reader, "_Inputs", forbidden)
    with pytest.raises(ContractError, match="source_out_of_scope"):
        reader.read_controlled_response_inputs(f.args, read_source=callback)
    assert calls == closure


@pytest.mark.parametrize("loaded", [{"artifact_ref": "a", "content": "text"}, {"artifact_ref": "a", "content": b"", "extra": 1}])
def test_malformed_callback_success_is_not_a_source_partial(loaded, monkeypatch):
    f = Fixture()
    monkeypatch.setattr(reader, "_Inputs", lambda *a: (_ for _ in ()).throw(AssertionError("geometry")))
    with pytest.raises(ExperimentalContractError):
        reader.read_controlled_response_inputs(f.args, read_source=lambda *args: loaded)


def test_real_source_io_failure_retains_nominations_but_no_authenticated_identity():
    f = Fixture()
    def callback(reference, representation):
        if reference == f.main_ref: raise FileNotFoundError(errno.ENOENT, "synthetic unavailable source")
        return f.source(reference, representation)
    result = reader.read_controlled_response_inputs(f.args, read_source=callback)
    candidate = result["arms"]["protein_condition1"]["measurement"]["candidates"][0]
    assert candidate["selection"] == f.args["arms"]["protein_condition1"]["measurement"]["literal"]["candidates"][0]
    assert candidate["status"] == "dependency_unavailable"
    assert candidate["source_locator"] is candidate["raw_expression"] is candidate["native_value"] is None
    assert result["arms"]["protein_condition1"]["measurement"]["source_observation_id"] is None
    assert result["calculation_inputs"]["arms"]["protein_condition1"] is None
    assert result["covariance"]["source_validation"] == "valid"
    assert result["effective_model"]["variance_status"] == "unknown"
    assert reader.validate_controlled_response_extraction(f.args, result) == result


@pytest.mark.parametrize("mutation", [
    lambda a: a.update(value=12),
    lambda a: a["arms"]["protein_condition1"]["measurement"].update(value=12),
    lambda a: a["covariance"].update(matrix=[[1]]),
    lambda a: a["arms"]["protein_condition1"]["measurement"]["literal"]["candidates"][0].update(number_start=-1),
])
def test_selected_scientific_operands_and_malformed_shapes_reject_before_io(mutation):
    f = Fixture(); mutation(f.args)
    with pytest.raises(ExperimentalContractError):
        reader.read_controlled_response_inputs(f.args, read_source=lambda *a: (_ for _ in ()).throw(AssertionError("I/O")))


def test_utf8_offsets_and_clipped_or_forged_source_nomination():
    f = Fixture(); result = f.read()
    item = result["arms"]["protein_condition1"]["measurement"]["candidates"][0]
    assert "μ" in f.data[f.main_ref].decode()
    assert f.data[f.main_ref][item["source_locator"]["start"]:item["source_locator"]["end"]] == b"12"
    f = Fixture(); f.args["arms"]["protein_condition1"]["measurement"]["literal"]["candidates"][0]["number_start"] += 1
    with pytest.raises(ExperimentalContractError, match="partial_source_numeric_token"): f.read()
    f = Fixture(); f.args["arms"]["protein_condition1"]["measurement"]["literal"]["candidates"][0]["witness"]["quote"] = "forged"
    with pytest.raises(ExperimentalContractError): f.read()


def test_forged_covariance_witness_cannot_hide_behind_unsupported_data():
    f = Fixture(); f.data[f.cov_ref] = b"not a supported covariance format"
    with pytest.raises(ExperimentalContractError): f.read()


def test_unknown_unit_keeps_native_number_and_independent_pair():
    f = Fixture(); arm = f.args["arms"]["empty_condition0"]
    arm["measurement"] = {"kind": "source_literal", "literal": {"status": "exact", "candidates": [f.number("Unsupported response: 7 widgets/min.", "7")], "fragments": []}, "unit": f.witness("widgets/min")}
    result = f.read()
    assert result["arms"]["empty_condition0"]["measurement"]["candidates"][0]["native_value"] == 7
    assert result["calculation_inputs"]["arms"]["empty_condition0"]["value"] == 7
    assert result["calculation_inputs"]["arms"]["empty_condition0"]["unit"] is None
    sheet = populate_controlled_response(result["calculation_inputs"])
    assert sheet["cells"]["condition1_controlled_response"]["value"] == .010
    assert sheet["cells"]["controlled_response_difference"]["value"] is None


def test_authentic_confidence_sentence_period_is_capability_not_absent_source():
    f = Fixture(); selected = f.args["arms"]["protein_condition1"]["reported_uncertainty"]
    selected.update(statistic=interpretation(f, "ci", "Reported CI"), magnitude=f.number("Reported SD: 0.6 nmol/min/mg.", "0.6"),
        interval={"witness": f.witness("[9, 15]"), "lower_start": 1, "lower_end": 2, "upper_start": 4, "upper_end": 6},
        confidence_level=f.witness("95%"), count=f.number("three technical measurements", "three"),
        unit_relationship=interpretation(f, "same_as_response", "nmol/min/mg"))
    result = f.read(); uncertainty = result["arms"]["protein_condition1"]["reported_uncertainty"]
    assert uncertainty["canonical"]["magnitude"] == .0006
    assert uncertainty["canonical"]["interval"] == [.009, .015]
    assert uncertainty["canonical"]["count"] == 3
    assert uncertainty["canonical"]["confidence_level"] is None
    assert uncertainty["canonical"]["statistic"] == "conflicting"
    assert any(d["code"] == "source_confidence_sentence_stop_unsupported" and d["domain"] == "reader_capability" for d in uncertainty["diagnostics"])
    assert result["covariance"]["calculation_covariance"]["matrix"][0][0] == 1


def test_duplicate_and_escaped_labels_bind_structural_token_positions_not_strings():
    f = Fixture(); f.doc["variables"][0]["label"] = f.doc["variables"][1]["label"] = "repeat μ"
    f.covariance(ensure_ascii=True)
    result = f.read()
    assert result["covariance"]["variables"][0]["label"] == "repeat μ"
    assert result["covariance"]["projection_state"] == "available"
    f.args["covariance"]["bindings"]["protein_condition1"]["label_witness"] = deepcopy(f.args["covariance"]["bindings"]["empty_condition1"]["label_witness"])
    with pytest.raises(ExperimentalContractError, match="source_label_token_binding_mismatch"): f.read()


def test_full_unselected_source_covariance_dimension_is_validated_and_retained():
    f = Fixture(); f.doc["variables"].append({"label": "extra", "unit": "unknown extra unit", "description": "unselected source variable"})
    for row in f.doc["covariance"]: row.append(0)
    f.doc["covariance"].append([0, 0, 0, 0, 1]); f.covariance()
    result = f.read()
    assert len(result["covariance"]["exact_matrix"]) == 5
    assert result["covariance"]["projection_state"] == "available"
    f.doc["covariance"][4][4] = -1; f.covariance()
    result = f.read()
    assert result["covariance"]["source_validation"] == "invalid"
    assert result["effective_model"]["variance_status"] == "unknown"
    assert populate_controlled_response(result["calculation_inputs"])["cells"]["controlled_response_difference"]["value"] == .006


@pytest.mark.parametrize("status,model,expected", [("known", "none", "known"), ("estimated", "none", "estimated"), ("unknown", "none", "unknown")])
def test_actual_requested_and_effective_covariance_status_remain_distinct(status, model, expected):
    f = Fixture(); f.doc.update(variance_status=status, model_kind=model)
    f.args["variance_status"]["value"] = status; f.covariance()
    result = f.read()
    assert result["covariance"]["source_model"]["variance_status"] == status
    assert result["requested_model"]["variance_status"]["selection"]["value"] == status
    assert result["effective_model"]["variance_status"] == expected


def test_variance_mismatch_preserves_source_matrix_and_magnitude_without_fallback():
    f = Fixture(); f.doc["variance_status"] = "estimated"; f.covariance()
    result = f.read()
    assert result["covariance"]["source_model"]["variance_status"] == "estimated"
    assert result["requested_model"]["variance_status"]["selection"]["value"] == "known"
    assert result["effective_model"]["variance_status"] == "unknown"
    assert result["calculation_inputs"]["covariance"] is None
    assert populate_controlled_response(result["calculation_inputs"])["cells"]["controlled_response_difference"]["value"] == .006


def test_saved_only_validation_uses_no_source_callback_reader_or_decoder(monkeypatch):
    f = Fixture(); result = f.read()
    def forbidden(*a, **k): raise AssertionError("source/decode/calculation in saved validation")
    monkeypatch.setattr(reader, "_Context", forbidden)
    monkeypatch.setattr(reader, "_native_number", forbidden)
    monkeypatch.setattr(reader, "_native_unit", forbidden)
    monkeypatch.setattr(reader, "_Inputs", forbidden)
    assert reader.validate_controlled_response_extraction(f.args, result) == result


@pytest.mark.parametrize("mutation", [
    lambda r: r["arms"]["protein_condition1"]["measurement"]["candidates"][0].update(native_value=999),
    lambda r: r["calculation_inputs"]["arms"]["protein_condition1"].update(value=999),
    lambda r: r["covariance"]["source_model"].update(variance_status="estimated"),
    lambda r: r["covariance"]["calculation_covariance"]["matrix"][0].__setitem__(0, 999),
    lambda r: r["sources"][0].update(byte_sha256="0"*64),
    lambda r: r["arms"]["protein_condition1"].update(extra="unbounded finding"),
])
def test_saved_record_relationship_tampering_rejected(mutation):
    f = Fixture(); result = f.read(); mutation(result)
    with pytest.raises(ExperimentalContractError): reader.validate_controlled_response_extraction(f.args, result)


def test_complete_unsupported_expression_is_local_but_clipped_mantissa_rejects():
    f = Fixture()
    text = "A complete alternate response was 1.2 × 10^3 nmol/min/mg."
    set_measurement(f, "empty_condition0", text, "1.2 × 10^3")
    result = f.read()
    arm = result["arms"]["empty_condition0"]
    assert arm["measurement"]["reading_status"] == "unsupported"
    assert arm["measurement"]["candidates"][0]["raw_expression"] == "1.2 × 10^3"
    assert populate_controlled_response(result["calculation_inputs"])["cells"]["condition1_controlled_response"]["value"] == .010
    f.args["arms"]["empty_condition0"]["measurement"]["literal"]["candidates"] = [f.number(text, "1.2")]
    with pytest.raises(ExperimentalContractError): f.read()


@pytest.mark.parametrize("token,relation,approximate", [("-2", "point", False), ("< -2", "lt", False), ("about -2", "point", True)])
def test_signed_censored_and_approximate_actual_contexts(token, relation, approximate):
    f = Fixture(); text = "Alternate reported response: " + token + " nmol/min/mg."
    set_measurement(f, "protein_condition1", text, "-2")
    result = f.read(); item = result["arms"]["protein_condition1"]["measurement"]["candidates"][0]
    assert item["native_value"] == -2 and item["relation"] == relation and item["approximate"] == approximate
    parsed = result["calculation_inputs"]["arms"]["protein_condition1"]
    assert parsed["value"] == (-2 if relation == "point" else None)
    assert parsed["threshold"] == (-2 if relation != "point" else None)


def test_exact_source_alias_conflict_survives_identical_rounded_floats():
    f = Fixture(shared=True)
    first = "0.10000000000000000001"; second = "0.10000000000000000002"
    line = f.args["arms"]["empty_condition1"]["measurement"]["literal"]["candidates"][0]["witness"]["quote"]
    f.replace_line(line, line.replace(", 2 ", ", " + first + " "))
    set_measurement(f, "empty_condition0", "A second rendering of actual E1: " + second + " nmol/min/mg.", second)
    result = f.read()
    for role in ("empty_condition1", "empty_condition0"):
        candidate = result["arms"][role]["measurement"]["candidates"][0]
        assert candidate["status"] == "parsed" and candidate["native_value"] == .1
        assert result["calculation_inputs"]["arms"][role]["approximate"] is True
    assert result["relationships"]["control_reference_reuse"]["selection"]["value"] == "same_reference_with_stated_invariance"
    assert result["relationships"]["control_reference_reuse"]["effective_value"] == "conflicting"
    assert result["covariance"]["source_validation"] == "valid"
    assert result["covariance"]["projection_state"] == "binding_conflicting"
    assert result["calculation_inputs"]["covariance"] is None
    sheet = populate_controlled_response(result["calculation_inputs"])
    assert sheet["cells"]["condition1_controlled_response"]["value"] is not None
    assert sheet["cells"]["condition0_controlled_response"]["value"] is not None
    assert sheet["cells"]["controlled_response_difference"]["value"] is None
    assert any(d["code"] == "source_literal_conflicting" and d["domain"] == "source_binding" for d in result["diagnostics"])
    assert reader.validate_controlled_response_extraction(f.args, result) == result


@pytest.mark.parametrize("value,unit", [("2.000", "nmol/min/mg"), ("0.002", "umol/min/mg")])
def test_equivalent_source_alias_spellings_and_units_stay_consistent(value, unit):
    f = Fixture(shared=True)
    set_measurement(f, "empty_condition0", "A second exact rendering of E1: " + value + " " + unit + ".", value, unit)
    result = f.read()
    assert result["relationships"]["control_reference_reuse"]["effective_value"] == "same_reference_with_stated_invariance"
    assert result["covariance"]["projection_state"] == "available"
    assert populate_controlled_response(result["calculation_inputs"])["cells"]["controlled_response_difference"]["value"] == .007


def test_shared_source_index_cannot_manufacture_an_unknown_or_distinct_owner():
    f = Fixture()
    f.args["covariance"]["bindings"]["empty_condition0"]["variable_index"] = 1
    f.covariance()
    result = f.read()
    assert result["covariance"]["projection_state"] == "binding_conflicting"
    f = Fixture(); physical = f.args["arms"]["empty_condition0"]["physical_observation"]
    physical.update(status="unknown", canonical_witness=None,
        canonical_correspondence={"value": "unknown", "witnesses": []})
    f.args["relationships"]["control_reference_reuse"] = interpretation(f, "unknown")
    result = f.read()
    assert result["calculation_inputs"]["arms"]["empty_condition0"]["physical_observation_id"] is None
    assert result["covariance"]["projection_state"] == "binding_unresolved"
    assert populate_controlled_response(result["calculation_inputs"])["cells"]["controlled_response_difference"]["value"] == .006


def test_unsupported_source_format_is_unassessed_not_invalid_scientific_covariance():
    f = Fixture(); f.args["covariance"]["bindings"] = dict.fromkeys(reader.PRIMITIVE_ORDER)
    f.args["variance_status"] = interpretation(f, "unknown"); f.args["model_kind"] = interpretation(f, "none")
    f.data[f.cov_ref] = b"row1,row2\n1,2\n"
    result = f.read()
    assert result["covariance"]["source_validation"] == "unassessed"
    assert result["covariance"]["projection_state"] == "unsupported_format"
    assert reader.validate_controlled_response_extraction(f.args, result) == result


def test_exact_finite_source_underflow_is_not_zero_or_a_bad_psd_model():
    f = Fixture(); f.doc["covariance"] = [[1 if i == j else 0 for j in range(4)]for i in range(4)]
    f.covariance()
    raw = f.data[f.cov_ref].decode()
    # Matrix integer tokens are unambiguously in this exact suffix.
    matrix_start = raw.index('"covariance"')
    raw = raw[:matrix_start] + raw[matrix_start:].replace("1,", "1e-500,", 1)
    f.data[f.cov_ref] = raw.encode()
    f.reanchor(f.cov_ref)
    result = f.read()
    assert result["covariance"]["source_validation"] == "valid"
    assert result["covariance"]["projection_state"] == "numeric_range"
    assert result["covariance"]["exact_matrix"][0][0] == {"numerator": "1", "denominator": "1" + "0"*500}
    assert result["effective_model"]["variance_status"] == "unknown"
    assert populate_controlled_response(result["calculation_inputs"])["cells"]["controlled_response_difference"]["value"] == .006


def test_native_registered_overflow_preserves_exact_cancelled_effect():
    f = Fixture()
    f.args["covariance"] = None
    f.args["variance_status"] = interpretation(f, "unknown"); f.args["model_kind"] = interpretation(f, "none")
    for role in reader.PRIMITIVE_ORDER:
        set_measurement(f, role, "New unscaled native response " + role + ": 1e308 mmol/min.", "1e308", "mmol/min")
    result = f.read()
    for arm in result["arms"].values():
        assert arm["measurement"]["canonical_display"]["value"] is None
        assert arm["calculation_operand"]["value"] == 1e308 and arm["calculation_operand"]["unit"] == "mmol/min"
        assert arm["calculation_operand"]["approximate"] is False
    assert populate_controlled_response(result["calculation_inputs"])["cells"]["controlled_response_difference"]["value"] == 0


def defined_unit_fixture():
    f = Fixture()
    endpoint = "oxidation of NADH"
    bridge = "One unit was defined as 2 nmol of NADH per min."
    clause = "2 nmol of NADH per min"
    f.append("Definition endpoint: " + endpoint + "."); f.append(bridge)
    text = "Actual alternate P1 optical response: 2 U/mg."
    set_measurement(f, "protein_condition1", text, "2", "U/mg")
    arm = f.args["arms"]["protein_condition1"]
    def meaning(w):
        return {"status": "known", "label": w["quote"], "witnesses": [w], "canonical_witness": w,
            "canonical_correspondence": {"value": "same", "witnesses": [w]}}
    arm["endpoint"] = meaning(f.witness(endpoint, tagged=True))
    arm["physical_observation"] = meaning(f.witness(text, tagged=True))
    binding = f.args["covariance"]["bindings"]["protein_condition1"]
    binding["owner_witness"] = deepcopy(arm["physical_observation"]["canonical_witness"])
    binding["correspondence"]["witnesses"][1] = deepcopy(binding["owner_witness"])
    f.doc["variables"][0]["description"] = text; f.covariance()
    source = f.data[f.main_ref].decode()
    definition = {"bridge": f.witness(bridge), "clause": f.witness(clause), "amount": f.number(clause, "2"),
        "amount_unit": f.witness("nmol", start=source.index(bridge)), "time_unit": f.witness("min", start=source.index(bridge)),
        "endpoint": f.witness(endpoint), "endpoint_entity": f.witness("NADH", start=source.index(endpoint)),
        "definition_entity": f.witness("NADH", start=source.index(bridge))}
    arm["measurement"]["unit"] = {"kind": "source_defined_rate_unit", "witness": f.witness("U/mg"), "definition": definition}
    return f


def test_source_defined_units_are_endpoint_bound_and_converted_once():
    f = defined_unit_fixture()
    arm = f.args["arms"]["protein_condition1"]
    result = f.read(); quantity = result["arms"]["protein_condition1"]
    assert quantity["measurement"]["unit"]["status"] == "supported"
    assert quantity["measurement"]["candidates"][0]["native_value"] == 2
    assert quantity["calculation_operand"]["value"] == .004
    assert quantity["calculation_operand"]["unit"] == "umol/min/mg"
    assert reader.validate_controlled_response_extraction(f.args, result) == result
    arm["endpoint"] = deepcopy(f.args["arms"]["empty_condition1"]["endpoint"])
    result = f.read()
    assert result["arms"]["protein_condition1"]["measurement"]["unit"]["status"] == "endpoint_correspondence_unknown"
    assert result["arms"]["protein_condition1"]["calculation_operand"]["unit"] is None


def test_unavailable_defined_unit_valid_partial_roundtrips_without_source_access(monkeypatch):
    f = defined_unit_fixture(); missing = identity("source", "invented_missing_defined_unit_witness")
    f.args["arms"]["protein_condition1"]["measurement"]["unit"]["witness"] = {
        "source_ref": missing, "representation": "original", "start": 0, "end": 4, "quote": "U/mg"}
    def callback(ref, rep):
        if ref == missing: raise FileNotFoundError(errno.ENOENT, "invented missing unit")
        return f.source(ref, rep)
    result = reader.read_controlled_response_inputs(f.args, read_source=callback)
    unit = result["arms"]["protein_condition1"]["measurement"]["unit"]
    assert unit["status"] == "dependency_unavailable" and unit["definition_witnesses"] is None
    assert result["calculation_inputs"]["arms"]["empty_condition1"]["value"] == 2
    def forbidden(*a, **k): raise AssertionError("saved source access")
    monkeypatch.setattr(reader, "_Sources", forbidden); monkeypatch.setattr(reader, "_Inputs", forbidden)
    assert reader.validate_controlled_response_extraction(f.args, result) == result
    unit["status"] = "supported"
    with pytest.raises(ExperimentalContractError, match="saved_unavailable_definition_mismatch"):
        reader.validate_controlled_response_extraction(f.args, result)


@pytest.mark.parametrize("error", [OSError(errno.EINVAL, "invalid callback"), OSError(errno.EBADF, "bad descriptor"),
    OSError("no explicit errno"), PermissionError(errno.EACCES, "denied"), RuntimeError("provider bug")])
def test_callback_programming_and_authorization_errors_never_become_source_findings(error, monkeypatch):
    f = Fixture()
    monkeypatch.setattr(reader, "_Inputs", lambda *a: (_ for _ in ()).throw(AssertionError("geometry before callback")))
    with pytest.raises(type(error)):
        reader.read_controlled_response_inputs(f.args, read_source=lambda *a: (_ for _ in ()).throw(error))


@pytest.mark.parametrize("error", [FileNotFoundError(errno.ENOENT, "missing retained bytes"),
    OSError(errno.EIO, "retained storage I/O"), TimeoutError(errno.ETIMEDOUT, "retained storage timeout"),
    EOFError("explicit truncated retained bytes")])
def test_only_explicit_availability_contract_creates_dependency_partial(error):
    f = Fixture()
    def callback(ref, rep):
        if ref == f.main_ref: raise error
        return f.source(ref, rep)
    result = reader.read_controlled_response_inputs(f.args, read_source=callback)
    assert result["calculation_inputs"]["arms"]["protein_condition1"] is None
    assert any(d["code"] == "source_dependency_unavailable" for d in result["diagnostics"])


@pytest.mark.parametrize("variance,source_model,selected_model,expected", [
    ("known", "known_joint_normal_source_means", "known_joint_normal_source_means", True),
    ("estimated", "known_joint_normal_source_means", "known_joint_normal_source_means", False),
    ("known", "known_joint_normal_source_means", "none", False),
    ("known", "none", "known_joint_normal_source_means", False)])
def test_model_family_never_inferred_or_silently_selected(variance, source_model, selected_model, expected):
    f = Fixture(); f.doc.update(variance_status=variance, model_kind=source_model)
    f.args["variance_status"]["value"] = variance
    f.args["model_kind"]["value"] = selected_model
    f.covariance()
    result = f.read()
    assert result["covariance"]["source_model"]["model_kind"] == source_model
    assert result["requested_model"]["model_kind"]["selection"]["value"] == selected_model
    sheet = populate_controlled_response(result["calculation_inputs"])
    assert (sheet["cells"]["source_profile_log_ratio"]["value"] is not None) == expected
    assert sheet["cells"]["contrast_variance"]["value"] == .0000017


def test_exact_source_rank_one_psd_can_have_an_invalid_finite_projection():
    from decimal import Decimal, localcontext
    f = Fixture()
    a, b = Fraction("0.100000000000000003"), Fraction("0.3")
    matrix = [[a*a, a*b, 0, 0], [a*b, b*b, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    assert matrix[0][0]*matrix[1][1] - matrix[0][1]**2 == 0
    finite = [[Fraction(str(float(v))) for v in row] for row in matrix]
    assert finite[0][0]*finite[1][1] - finite[0][1]**2 < 0
    with localcontext() as context:
        context.prec = 100
        text_matrix = "[" + ",".join("[" + ",".join(str(Decimal(Fraction(v).numerator)/Decimal(Fraction(v).denominator)) for v in row) + "]" for row in matrix) + "]"
    f.doc["covariance"] = "SOURCE_EXACT_MATRIX"
    f.data[f.cov_ref] = json.dumps(f.doc, indent=2).replace('"SOURCE_EXACT_MATRIX"', text_matrix).encode()
    f.reanchor(f.cov_ref)
    result = f.read()
    assert result["covariance"]["source_validation"] == "valid"
    assert result["covariance"]["projection_state"] == "precision_invalid"
    assert any(d["code"] == "covariance_projection_precision_invalid" and d["domain"] == "reader_capability" for d in result["covariance"]["diagnostics"])
    assert result["covariance"]["source_model"]["variance_status"] == "known"
    assert result["calculation_inputs"]["covariance"] is None
    assert reader.validate_controlled_response_extraction(f.args, result) == result


def graph_fixture():
    f = Fixture(); image_ref = identity("source", "invented_no_measured_ordinate_image")
    stream = BytesIO(); Image.new("RGB", (12, 12), "white").save(stream, format="PNG")
    f.data[image_ref] = stream.getvalue()
    f.args["images"] = [{"image_id": "invented_image", "source_ref": image_ref, "original_source_ref": image_ref, "mapping": None}]
    literal = lambda quote: {"status": "exact", "candidates": [f.witness(quote, tagged=True)], "fragments": []}
    f.args["arms"]["protein_condition1"]["measurement"] = {"kind": "linear_bar", "image_id": "invented_image",
        "bar_selection": {"roi": {"left": 1, "top": 1, "right": 10, "bottom": 10},
            "rgb_min": [0, 0, 0], "rgb_max": [10, 10, 10], "minimum_row_fraction": .5,
            "minimum_run_rows": 1, "edge_tolerance_pixels": 0},
        "axis": {"first": {"pixel": 1, "tick": literal("12")}, "second": {"pixel": 10, "tick": literal("5")},
            "unit": literal("nmol/min/mg")}}
    return f, image_ref


def test_graph_nomination_authenticates_bytes_geometry_and_stays_unimplemented():
    f, ref = graph_fixture(); result = f.read()
    measured = result["arms"]["protein_condition1"]["measurement"]
    assert measured["reading_status"] == "graph_unimplemented" and measured["pixel_result"] is None
    assert result["images"][0]["byte_sha256"] == hashlib.sha256(f.data[ref]).hexdigest()
    assert all(w["authentication"] == "exact_utf8_byte_span" for w in measured["graph_witnesses"])
    assert result["calculation_inputs"]["arms"]["protein_condition1"]["value"] is None
    assert result["calculation_inputs"]["arms"]["protein_condition0"]["value"] == 5
    assert reader.validate_controlled_response_extraction(f.args, result) == result


def test_image_authorization_cannot_be_swallowed_by049_broad_catch(monkeypatch):
    f, image_ref = graph_fixture()
    def callback(ref, rep):
        if ref == image_ref: raise ContractError("image_source_out_of_scope")
        return f.source(ref, rep)
    monkeypatch.setattr(reader, "_Inputs", lambda *a: (_ for _ in ()).throw(AssertionError("constructed before source authorization")))
    with pytest.raises(ContractError, match="image_source_out_of_scope"):
        reader.read_controlled_response_inputs(f.args, read_source=callback)


def test_wrong_crop_pixels_are_repairable_nomination_not_source_science_partial():
    f, image_ref = graph_fixture()
    crop_ref = identity("source", "invented_wrong_crop")
    stream = BytesIO(); Image.new("RGB", (4, 4), "black").save(stream, format="PNG")
    f.data[crop_ref] = stream.getvalue()
    f.args["images"][0].update(source_ref=crop_ref, mapping={"original_region": [0, 0, 4, 4], "colour_conversion": "preserve"})
    with pytest.raises(ExperimentalContractError, match="image_mapping_pixels_mismatch"): f.read()


def test_bad_matrix_shape_does_not_erase_literal_actual_source_model_status():
    f = Fixture(); f.doc["covariance"] = [[1]]; f.covariance()
    result = f.read()
    assert result["covariance"]["source_validation"] == "invalid"
    assert result["covariance"]["source_model"] == {"origin": "synthetic", "variance_status": "known", "model_kind": "none"}
    assert result["effective_model"] == {"variance_status": "unknown", "model_kind": "none", "diagnostics": []}
    assert populate_controlled_response(result["calculation_inputs"])["cells"]["controlled_response_difference"]["value"] == .006


def test_prefetch_snapshots_success_dictionary_before_callback_can_reuse_it():
    f = Fixture(); reused = {}
    def callback(ref, rep):
        reused.clear(); reused.update(f.source(ref, rep)); return reused
    result = reader.read_controlled_response_inputs(f.args, read_source=callback)
    assert result["calculation_inputs"]["arms"]["protein_condition1"]["value"] == 12
    assert result["covariance"]["projection_state"] == "available"


@pytest.mark.parametrize("token,code", [("NaN", "source_json_nonfinite"), ("true", "source_covariance_shape_invalid")])
def test_actual_invalid_source_numeric_tokens_never_become_covariance_numbers(token, code):
    f = Fixture(); f.doc["covariance"] = "NUMERIC_SOURCE_MATRIX"; f.covariance()
    f.data[f.cov_ref] = f.data[f.cov_ref].replace(b'"NUMERIC_SOURCE_MATRIX"', ('[[' + token + ',0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]').encode())
    f.reanchor(f.cov_ref)
    result = f.read()
    assert any(d["code"] == code for d in result["covariance"]["diagnostics"])
    assert result["calculation_inputs"]["covariance"] is None
    assert populate_controlled_response(result["calculation_inputs"])["cells"]["controlled_response_difference"]["value"] == .006


def test_duplicate_json_key_is_a_retained_source_error_not_hidden_last_value():
    f = Fixture(); f.data[f.cov_ref] = f.data[f.cov_ref].replace(b'"covariance":', b'"covariance":[], "covariance":', 1)
    f.reanchor(f.cov_ref)
    result = f.read()
    assert result["covariance"]["raw_text"] == f.data[f.cov_ref].decode()
    assert result["covariance"]["diagnostics"][0]["code"] == "source_json_duplicate_key"
    assert result["calculation_inputs"]["covariance"] is None


def test_known_normal_family_is_disabled_by_covariance_digit_loss_without_mislabeling_source_psd():
    f = Fixture(); f.doc["model_kind"] = "known_joint_normal_source_means"
    f.args["model_kind"]["value"] = "known_joint_normal_source_means"
    f.doc["covariance"] = "EXACT_SOURCE_MATRIX"; f.covariance()
    f.data[f.cov_ref] = f.data[f.cov_ref].replace(b'"EXACT_SOURCE_MATRIX"',
        b'[[1.00000000000000000001,0,0,0],[0,0.25,0,0],[0,0,0.36,0],[0,0,0,0.09]]')
    f.reanchor(f.cov_ref)
    result = f.read()
    assert result["covariance"]["source_validation"] == "valid"
    assert result["covariance"]["projection_state"] == "available"
    assert result["effective_model"]["variance_status"] == "known"
    assert result["effective_model"]["model_kind"] == "none"
    assert result["covariance"]["source_model"]["model_kind"] == "known_joint_normal_source_means"
    assert any(d["code"] == "source_model_projection_rounding" for d in result["effective_model"]["diagnostics"])


def test_image_decode_failure_is_not_a_malformed_source_or_lost_valid_pair():
    f, image_ref = graph_fixture(); f.data[image_ref] = b"invented unsupported image bytes"
    result = f.read()
    assert result["images"][0]["error"] is not None
    assert result["arms"]["protein_condition1"]["measurement"]["reading_status"] == "graph_unimplemented"
    assert result["arms"]["protein_condition1"]["measurement"]["source_observation_id"] is None
    assert result["calculation_inputs"]["arms"]["protein_condition1"] is None
    assert populate_controlled_response(result["calculation_inputs"])["cells"]["condition0_controlled_response"]["value"] == .004


def test_counts_and_relative_spread_do_not_create_a_model_without_a_covariance_source():
    f = Fixture(); f.args["covariance"] = None; f.args["variance_status"] = interpretation(f, "unknown")
    uncertainty = f.args["arms"]["protein_condition1"]["reported_uncertainty"]
    uncertainty.update(statistic=interpretation(f, "sd", "Reported SD"), magnitude=f.number("Reported SD: 0.6 nmol/min/mg.", "0.6"),
        count=f.number("three technical measurements", "three"), unit_relationship=interpretation(f, "same_as_response", "nmol/min/mg"))
    result = f.read()
    assert result["arms"]["protein_condition1"]["reported_uncertainty"]["canonical"]["count"] == 3
    assert result["calculation_inputs"]["covariance"] is None
    assert result["calculation_inputs"]["model_kind"] == "none"
    sheet = populate_controlled_response(result["calculation_inputs"])
    assert sheet["cells"]["controlled_response_difference"]["value"] == .006
    assert sheet["cells"]["contrast_variance"]["value"] is None


def test_valid_confidence_and_qualified_count_pieces_remain_independent():
    f = Fixture(); f.append("An exact confidence label: 95% (reported)."); f.append("Repetition statement: at least three technical measurements.")
    uncertainty = f.args["arms"]["protein_condition1"]["reported_uncertainty"]
    uncertainty.update(statistic=interpretation(f, "ci", "Reported CI"),
        interval={"witness": f.witness("[9, 15]"), "lower_start": 1, "lower_end": 2, "upper_start": 4, "upper_end": 6},
        confidence_level=f.witness("95%", start=f.data[f.main_ref].decode().index("An exact confidence label")),
        count=f.number("at least three technical measurements", "three"),
        unit_relationship=interpretation(f, "same_as_response", "nmol/min/mg"))
    result = f.read(); uncertainty = result["arms"]["protein_condition1"]["reported_uncertainty"]
    assert uncertainty["canonical"]["confidence_level"] == .95
    assert uncertainty["count"]["reading"]["value"] == 3
    assert uncertainty["count"]["reading"]["status"] == "qualified"
    assert uncertainty["count"]["reading"]["relation"] == "ge"
    assert uncertainty["canonical"]["count"] is None
    assert result["covariance"]["calculation_covariance"]["matrix"][0][0] == 1


def test_explicit_wrong_spread_unit_is_partial_without_relabeling_the_source():
    f = Fixture(); f.append("Reported alternate SD: 0.6 uM/min.")
    selected = f.args["arms"]["protein_condition1"]["reported_uncertainty"]
    selected.update(statistic=interpretation(f, "sd", "Reported alternate SD"),
        magnitude=f.number("Reported alternate SD: 0.6 uM/min.", "0.6"),
        unit_relationship=interpretation(f, "same_as_response", "nmol/min/mg"))
    result = f.read(); uncertainty = result["arms"]["protein_condition1"]["reported_uncertainty"]
    assert uncertainty["magnitude"]["native_value"] == .6
    assert uncertainty["canonical"]["magnitude"] is None
    assert any(d["code"] == "source_uncertainty_unit_conflicting" for d in uncertainty["diagnostics"])
    assert result["calculation_inputs"]["arms"]["protein_condition1"]["value"] == 12


def test_image_witness_retains_geometry_only_attribution_not_ocr_truth():
    f, image_ref = graph_fixture()
    f.args["arms"]["protein_condition0"]["context"]["subject"] = {
        "kind": "image", "image_id": "invented_image", "region": [1, 1, 3, 3], "quote": "nominated synthetic label"}
    result = f.read(); witness = result["arms"]["protein_condition0"]["context"]["subject"]
    assert witness["authentication"] == "image_bytes_and_geometry_only"
    assert witness["attribution"] == "investigating_episode_interpretation"
    assert witness["canonical_locator"]["original_source_ref"] == image_ref
    assert witness["canonical_locator"]["region"] == [1, 1, 3, 3]


def test_narrow_exact_ci_does_not_turn_into_false_zero_width_after_projection():
    f = Fixture(); text = "[0.10000000000000000001, 0.10000000000000000002]"
    f.append("Reported narrow CI: " + text + " nmol/min/mg.")
    selected = f.args["arms"]["protein_condition1"]["reported_uncertainty"]
    selected.update(statistic=interpretation(f, "ci", "Reported narrow CI"),
        interval={"witness": f.witness(text), "lower_start": 1, "lower_end": text.index(","),
            "upper_start": text.index(",")+2, "upper_end": len(text)-1},
        unit_relationship=interpretation(f, "same_as_response", "nmol/min/mg"))
    result = f.read(); uncertainty = result["arms"]["protein_condition1"]["reported_uncertainty"]
    assert uncertainty["interval"]["raw_values"] == ["0.10000000000000000001", "0.10000000000000000002"]
    assert uncertainty["canonical"]["interval"] is None
    assert any(d["code"] == "source_numeric_range" for d in uncertainty["diagnostics"])
    assert reader.validate_controlled_response_extraction(f.args, result) == result
