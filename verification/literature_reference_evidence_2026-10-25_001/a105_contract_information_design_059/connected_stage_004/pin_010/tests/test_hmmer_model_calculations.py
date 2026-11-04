"""Independent numerical checks on retained native models and saved-sheet reruns."""
import builtins
from copy import deepcopy
from decimal import Decimal, localcontext
import hashlib
import json
import math
import os
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.hmmer_model_data import extract_hmmer_models
from gene_annotation_episode.hmmer_model_calculations import (
    CHECK_CODES, CHECK_STATES, COMPONENT_STATES, ISSUE_CODES,
    calculate_hmmer_model_components,
)


NATIVE = Path(__file__).resolve().parents[1] / "verification/tool_graders_hmmer_preparation_contracts_2026-10-26_259/native"


def model(data=None, suffix="protein", **occurrence_changes):
    if data is None:
        data = (NATIVE / ("hmmbuild_" + suffix) / "profile.hmm").read_bytes()
    occurrence = {"occurrence_id": "native/" + suffix, "direction": "output", "role": "models", "ordinal": 0,
                  "artifact_ref": "retained:" + suffix, "sha256": hashlib.sha256(data).hexdigest(),
                  "size_bytes": len(data), "completeness": "complete", **occurrence_changes}
    return extract_hmmer_models(data, occurrence=occurrence, format="hmmer3_ascii")


def background(symbols="ACDEFGHIKLMNPQRSTVWY"):
    return {symbol: 1 / len(symbols) for symbol in symbols}


def decimal_expectations(tokens, probabilities):
    with localcontext() as context:
        context.prec = 60
        p = [(-Decimal(token)).exp() if token != "*" else Decimal(0) for token in tokens]
        entropy = -sum(value * value.ln() / Decimal(2).ln() for value in p if value)
        kl = sum(value * (value.ln() - Decimal(str(q)).ln()) / Decimal(2).ln()
                 for value, q in zip(p, probabilities) if value)
        return float(sum(p)), float(entropy), float(kl)


def test_independent_native_position_five_and_mean_numbers():
    extraction = model()
    record = extraction["records"][0]
    result = calculate_hmmer_model_components(extraction, background=background())
    row = result["rows"][0]
    tokens = [cell["token"] for cell in record["positions"][4]["match"]["cells"]]
    mass, entropy, kl = decimal_expectations(tokens, [0.05] * 20)
    position = row["positions"][4]
    assert position["match"]["mass"]["value"] == pytest.approx(mass, abs=1e-15)
    assert position["match"]["mass_residual"]["value"] == pytest.approx(mass-1, abs=1e-15)
    assert position["entropy"]["value"] == pytest.approx(entropy, abs=1e-15)
    assert position["relative_entropy"]["value"] == pytest.approx(kl, abs=2e-15)
    assert row["mean_match_entropy"]["value"] == pytest.approx(entropy/12, abs=1e-15)
    expected_mean_kl = (11 * math.log2(20) + kl) / 12
    assert row["mean_match_relative_entropy"]["value"] == pytest.approx(expected_mean_kl, abs=2e-15)
    assert row["match_state_count"]["value"] == row["declared_length"]["value"] == 12
    assert row["sequence_count"]["value"] == row["effective_sequence_count"]["value"] == 3
    ratio = row["effective_sequence_ratio"]
    assert ratio["value"] == 1 and ratio["state"] == "present"
    denominator = next(source for source in ratio["inputs"] if source["role"] == "denominator")
    assert denominator == {"record_key": "native/protein#model/0", "field": "sequence_count", "role": "denominator"}
    assert row["sequence_count"]["inputs"] == [{"record_key": "native/protein#model/0", "field": "sequence_count"}]
    assert result["parameters"] == {"background": background(), "probability_tolerance": 1e-4}
    assert result["issues"] == []
    assert json.loads(json.dumps(result, allow_nan=False)) == result


def test_transition_three_outgoing_groups_not_total_of_seven():
    result = calculate_hmmer_model_components(model())
    row = result["rows"][0]
    groups = row["initial"]["transitions"]
    assert set(groups) == {"M", "I", "D"}
    assert groups["M"]["mass"]["value"] == 1
    for name in ("I", "D"):
        assert groups[name]["mass"]["value"] == pytest.approx(2 * math.exp(-0.69315), abs=1e-15)
        assert groups[name]["mass_residual"]["value"] == pytest.approx(2 * math.exp(-0.69315) - 1, abs=1e-15)
    assert groups["M"]["mass"]["inputs"][0]["symbols"] == ["m->m", "m->i", "m->d"]
    assert groups["I"]["mass"]["inputs"][0]["cell_indices"] == [3, 4]
    assert row["positions"][-1]["transitions"]["D"]["mass"]["value"] == 1
    transition_checks = [check for check in result["checks"] if check["field"] == "initial.transitions"]
    assert len(transition_checks) == 3 and all(check["state"] == "pass" for check in transition_checks)


@pytest.mark.parametrize("suffix,alphabet", [("dna", "ACGT"), ("rna", "ACGU")])
def test_independent_complete_nucleotide_arrays(suffix, alphabet):
    extraction = model(suffix=suffix)
    result = calculate_hmmer_model_components(extraction, background=background(alphabet))
    row = result["rows"][0]
    assert len(row["positions"]) == 12
    expected_entropies, expected_kls = [], []
    for native_position, position in zip(extraction["records"][0]["positions"], row["positions"]):
        tokens = [cell["token"] for cell in native_position["match"]["cells"]]
        mass, entropy, kl = decimal_expectations(tokens, [0.25] * 4)
        assert position["match"]["mass"]["value"] == pytest.approx(mass, abs=1e-15)
        assert position["entropy"]["value"] == pytest.approx(entropy, abs=2e-15)
        assert position["relative_entropy"]["value"] == pytest.approx(kl, abs=2e-15)
        expected_entropies.append(entropy)
        expected_kls.append(kl)
    assert row["mean_match_entropy"]["value"] == pytest.approx(sum(expected_entropies)/12, abs=2e-15)
    assert row["mean_match_relative_entropy"]["value"] == pytest.approx(sum(expected_kls)/12, abs=2e-15)


def test_recalculation_with_changed_parameters_is_pure_and_does_not_mutate_saved_data(monkeypatch):
    extraction = json.loads(json.dumps(model()))
    data = (NATIVE / "hmmbuild_protein/profile.hmm").read_bytes()
    supplied = deepcopy(extraction["occurrence"])
    original = deepcopy(extraction)
    baseline = calculate_hmmer_model_components(extraction, background=background())
    previous = deepcopy(baseline)
    changed_background = {symbol: 0.1 if symbol in {"F", "Y"} else 0.8/18
                          for symbol in "ACDEFGHIKLMNPQRSTVWY"}
    def forbidden(*args, **kwargs):
        raise AssertionError("recalculation/extraction attempted I/O or native execution")
    with monkeypatch.context() as context:
        context.setattr(builtins, "open", forbidden)
        context.setattr(Path, "open", forbidden)
        context.setattr(subprocess, "Popen", forbidden)
        context.setattr(subprocess, "run", forbidden)
        context.setattr(socket, "socket", forbidden)
        context.setattr(socket, "create_connection", forbidden)
        context.setattr(os, "system", forbidden)
        reparsed = extract_hmmer_models(data, occurrence=supplied, format="hmmer3_ascii")
        changed = calculate_hmmer_model_components(extraction,
            background=changed_background, probability_tolerance=1e-8)
    assert reparsed == extraction
    assert extraction == original and baseline == previous
    assert changed["parameters"] == {"background": changed_background, "probability_tolerance": 1e-8}
    old_position = baseline["rows"][0]["positions"][4]
    new_position = changed["rows"][0]["positions"][4]
    assert new_position["entropy"] == old_position["entropy"]
    # Doubling q(F) and q(Y) subtracts exactly their native mass in bits.
    assert old_position["relative_entropy"]["value"] - new_position["relative_entropy"]["value"] == pytest.approx(
        old_position["match"]["mass"]["value"], abs=1e-15)
    assert all(check["state"] != "fail" for check in baseline["checks"])
    assert any(check["state"] == "fail" and check["code"] == "probability_mass" for check in changed["checks"])
    assert new_position["match"] == old_position["match"]


def test_no_background_has_missing_not_default_relative_entropy():
    row = calculate_hmmer_model_components(model())["rows"][0]
    assert row["mean_match_relative_entropy"]["state"] == "missing"
    assert row["mean_match_relative_entropy"]["value"] is None
    assert all(p["relative_entropy"]["state"] == "missing" for p in row["positions"])
    assert all(p["entropy"]["state"] == "present" for p in row["positions"])


def test_zero_background_support_is_nonfinite_only_for_positive_model_terms():
    q = {symbol: float(symbol == "A") for symbol in "ACDEFGHIKLMNPQRSTVWY"}
    result = calculate_hmmer_model_components(model(), background=q)
    row = result["rows"][0]
    assert row["positions"][0]["relative_entropy"]["value"] == 0
    assert row["positions"][0]["relative_entropy"]["state"] == "present"
    assert row["positions"][1]["relative_entropy"]["value"] is None
    assert row["positions"][1]["relative_entropy"]["state"] == "nonfinite"
    assert row["mean_match_relative_entropy"]["state"] == "nonfinite"
    assert "background_support_zero" in {issue["code"] for issue in result["issues"]}


@pytest.mark.parametrize("q,code", [
    ({"A": 1}, "background_alphabet_mismatch"),
    ({**background(), "A": -0.1}, "background_invalid"),
    ({**background(), "A": float("nan")}, "background_invalid"),
    ({**background(), "A": True}, "background_invalid"),
    ({**background(), "A": 0.2}, "background_mass_invalid"),
    ([0.05] * 20, "background_invalid"),
])
def test_incompatible_backgrounds_remain_explicit(q, code):
    result = calculate_hmmer_model_components(model(), background=q)
    row = result["rows"][0]
    assert row["mean_match_relative_entropy"]["state"] == "incompatible"
    assert row["mean_match_relative_entropy"]["value"] is None
    assert row["mean_match_entropy"]["state"] == "present"
    assert code in {issue["code"] for issue in result["issues"]}


@pytest.mark.parametrize("tolerance", [-1, True, float("nan"), float("inf"), "0.01"])
def test_invalid_tolerance_cannot_pass_checks(tolerance):
    result = calculate_hmmer_model_components(model(), background=background(), probability_tolerance=tolerance)
    assert "parameter_invalid" in {issue["code"] for issue in result["issues"]}
    assert all(check["state"] == "unknown" for check in result["checks"] if check["code"] == "probability_mass")
    assert result["rows"][0]["mean_match_entropy"]["state"] == "present"
    assert result["rows"][0]["mean_match_relative_entropy"]["state"] == "incompatible"


def test_underflow_and_invalid_cells_do_not_supply_zero_information():
    data = (NATIVE / "hmmbuild_protein/profile.hmm").read_bytes()
    for token, state in ((b"1000", "nonfinite"), (b"bad", "incompatible")):
        result = calculate_hmmer_model_components(model(data.replace(b"0.40547", token)), background=background())
        row = result["rows"][0]
        assert row["positions"][4]["entropy"]["state"] == state
        assert row["positions"][4]["entropy"]["value"] is None
        assert row["positions"][4]["match"]["mass"]["state"] == state
        assert row["positions"][0]["entropy"]["state"] == "present"
        assert row["mean_match_entropy"]["state"] == state


def test_partial_transition_distribution_preserves_complete_outgoing_groups():
    extraction = model()
    extraction["records"][0]["positions"][-1]["transitions"]["cells"].pop()
    result = calculate_hmmer_model_components(extraction)
    transition = result["rows"][0]["positions"][-1]["transitions"]
    assert transition["M"]["mass"]["state"] == transition["I"]["mass"]["state"] == "present"
    assert transition["D"]["mass"]["state"] == "incomplete"
    assert transition["D"]["mass"]["value"] is None


def test_truncated_match_population_retains_positions_but_no_partial_mean():
    data = (NATIVE / "hmmbuild_protein/profile.hmm").read_bytes()
    result = calculate_hmmer_model_components(model(data[:data.index(b"      5")]), background=background())
    row = result["rows"][0]
    assert len(row["positions"]) == row["match_state_count"]["value"] == 4
    assert row["declared_length"]["value"] == 12
    assert row["mean_match_entropy"]["state"] == row["mean_match_relative_entropy"]["state"] == "incomplete"
    assert row["positions"][0]["entropy"]["value"] == 0


def test_closed_prefix_model_is_recalculable_when_capture_is_partial():
    extraction = model(completeness="partial")
    result = calculate_hmmer_model_components(extraction, background=background())
    assert result["rows"][0]["mean_match_entropy"]["state"] == "present"
    assert next(check for check in result["checks"] if check["code"] == "population_complete")["state"] == "unknown"


def test_missing_count_and_zero_denominator_are_distinct():
    extraction = model()
    extraction["records"][0]["sequence_count"] = None
    row = calculate_hmmer_model_components(extraction)["rows"][0]
    assert row["effective_sequence_ratio"]["state"] == "missing"
    extraction["records"][0]["sequence_count"] = 0  # explicit saved-data edge case, not native NSEQ validation
    row = calculate_hmmer_model_components(extraction)["rows"][0]
    assert row["sequence_count"]["value"] == 0
    assert row["effective_sequence_ratio"]["state"] == "nonfinite"


def test_invalid_native_count_does_not_become_missing_in_calculations():
    data = (NATIVE / "hmmbuild_protein/profile.hmm").read_bytes().replace(b"NSEQ  3", b"NSEQ  invalid")
    result = calculate_hmmer_model_components(model(data))
    assert result["rows"][0]["sequence_count"]["state"] == "incompatible"
    assert result["rows"][0]["effective_sequence_ratio"]["state"] == "incompatible"
    assert result["rows"][0]["mean_match_entropy"]["state"] == "present"


def test_changed_saved_cells_cannot_silently_contradict_the_native_logs():
    extraction = model()
    extraction["records"][0]["positions"][0]["match"]["cells"][0]["probability"] = 0.5
    result = calculate_hmmer_model_components(extraction)
    assert result["rows"][0]["positions"][0]["entropy"]["state"] == "incompatible"


def test_saved_token_log_disagreement_is_incompatible():
    extraction = model()
    extraction["records"][0]["positions"][0]["match"]["cells"][0]["token"] = "bad"
    result = calculate_hmmer_model_components(extraction)
    assert result["rows"][0]["positions"][0]["entropy"]["state"] == "incompatible"


@pytest.mark.parametrize("field,value", [("artifact_ref", "wrong:artifact"), ("record_ordinal", 1),
                                         ("byte_end", 10**9)])
def test_saved_record_references_are_checked(field, value):
    extraction = model()
    extraction["records"][0]["locator"][field] = value
    result = calculate_hmmer_model_components(extraction)
    assert result["rows"] == []
    assert result["issues"][0]["code"] == "record_invalid"


def test_duplicate_saved_identity_cannot_collapse_original_occurrences():
    extraction = model()
    extraction["records"].append(deepcopy(extraction["records"][0]))
    result = calculate_hmmer_model_components(extraction)
    assert len(result["rows"]) == 1
    assert result["issues"][0]["code"] == "record_invalid"


def test_no_renormalization_when_native_rounding_mass_fails_tolerance():
    extraction = model()
    result = calculate_hmmer_model_components(extraction, background=background(), probability_tolerance=0)
    position = result["rows"][0]["positions"][4]
    assert position["match"]["mass_residual"]["value"] != 0
    assert position["entropy"]["state"] == "present"
    assert position["relative_entropy"]["state"] == "present"
    assert any(check["state"] == "fail" and check["position"] == 5 for check in result["checks"])


def test_component_and_check_states_and_issue_codes_are_closed():
    result = calculate_hmmer_model_components(model(), background=background(), probability_tolerance=0)
    def visit(value):
        if isinstance(value, dict):
            if set(value) == {"value", "state", "unit", "inputs"}:
                assert value["state"] in COMPONENT_STATES
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)
    visit(result)
    assert {check["state"] for check in result["checks"]} <= CHECK_STATES
    assert {check["code"] for check in result["checks"]} <= CHECK_CODES
    assert {issue["code"] for issue in result["issues"]} <= ISSUE_CODES


def test_incompatible_saved_schema_is_explicit():
    result = calculate_hmmer_model_components({"schema": "other"})
    assert result["rows"] == []
    assert result["issues"][0]["code"] == "extraction_invalid"
