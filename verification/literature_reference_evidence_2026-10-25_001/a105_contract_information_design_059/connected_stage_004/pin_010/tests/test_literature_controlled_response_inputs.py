"""Synthetic source/parsed-model tests only; no primary paper or model run."""
from copy import deepcopy
from fractions import Fraction
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
        if reference == f.main_ref: raise FileNotFoundError("synthetic unavailable source")
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
