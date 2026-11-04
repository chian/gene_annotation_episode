"""Check actual independent statistics and saved-data calculation boundaries."""
from copy import deepcopy
import builtins
import json
import math
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.hmmer_statistics_calculations import (
    calculate_hmmstat_components, native_hmmstat_parameters,
)
from tests.test_hmmer_statistics_data import NATIVE, make_sheet, native_case


@pytest.mark.parametrize("kind,alphabet", [("protein", "amino"), ("dna", "DNA"), ("rna", "RNA"), ("annotated", "amino")])
def test_all_four_native_model_statistic_pairs_match_at_native_precision(kind, alphabet):
    result = calculate_hmmstat_components(native_case(kind), **native_hmmstat_parameters("3.4", alphabet))
    comparisons = [c for c in result["checks"] if c["name"] == "native_rounding_agreement"]
    assert len(comparisons) == 4 and all(c["state"] == "pass" for c in comparisons)
    assert len(result["rows"][0]["positions"]) == 12
    assert result["rows"][0]["components"]["effective_sequence_ratio"]["value"] == 1
    assert not result["issues"]


def test_dna_independently_checked_full_precision_values_and_denominators():
    result = calculate_hmmstat_components(native_case(), **native_hmmstat_parameters("3.4", "DNA"))
    row = result["rows"][0]
    c = row["components"]
    expected = {"mean_match_entropy": .9925134248800135,
                "mean_match_information": 1.0074865751199864,
                "mean_match_relative_entropy": 1.0074921672642938,
                "position_relative_entropy": .8906422345697793,
                "composition_relative_entropy": .006355823477963574}
    for key, value in expected.items():
        assert c[key]["value"] == pytest.approx(value, abs=1e-12)
        assert c[key]["state"] == "present" and c[key]["inputs"]
    assert row["positions"][0]["occupancy"]["value"] == pytest.approx(.9807699880, abs=5e-11)
    assert row["positions"][-1]["occupancy"]["value"] == pytest.approx(.9457525653, abs=5e-11)
    assert c["occupancy_sum"]["value"] > c["entry_occupancy_sum"]["value"]
    assert c["occupancy_sum"]["value"] - c["entry_occupancy_sum"]["value"] == pytest.approx(row["positions"][0]["occupancy"]["value"])
    assert sum(x["component"]["value"] for x in row["composition"]["probabilities"]) == pytest.approx(1)
    assert c["composition_weight_sum"]["value"] != c["occupancy_sum"]["value"]
    assert result["rows"][0]["native_comparisons"][0]["native_value"] == 1.01


def test_missing_parameters_do_not_select_native_defaults():
    c = calculate_hmmstat_components(native_case())["rows"][0]["components"]
    assert c["mean_match_entropy"]["state"] == "present"
    assert c["occupancy_sum"]["state"] == "present"
    assert c["composition_weight_sum"]["state"] == "present"
    for name in ("mean_match_relative_entropy", "mean_match_information", "position_relative_entropy", "composition_relative_entropy"):
        assert c[name]["value"] is None and c[name]["state"] == "missing"


@pytest.mark.parametrize("p1", [0, -1, 2, True, "arbitrary"])
def test_invalid_length_probability_only_invalidates_its_dependent_components(p1):
    params = native_hmmstat_parameters("3.4", "DNA")
    params["length_probability"] = p1
    c = calculate_hmmstat_components(native_case(), **params)["rows"][0]["components"]
    assert c["position_relative_entropy"]["state"] == "incompatible"
    assert c["mean_match_relative_entropy"]["state"] == "present"
    assert c["composition_relative_entropy"]["state"] == "present"


def test_saved_sheet_recalculation_changes_parameters_without_io(monkeypatch):
    sheet = json.loads(json.dumps(native_case()))
    original = deepcopy(sheet)
    params = native_hmmstat_parameters("3.4", "DNA")
    def forbidden(*args, **kwargs):
        raise AssertionError("No file, network, or native operation belongs in recalculation")
    with monkeypatch.context() as m:
        m.setattr(builtins, "open", forbidden)
        m.setattr(Path, "open", forbidden)
        m.setattr(subprocess, "run", forbidden)
        m.setattr(subprocess, "Popen", forbidden)
        m.setattr(socket, "socket", forbidden)
        native = calculate_hmmstat_components(sheet, **params)
        changed = calculate_hmmstat_components(sheet, **{**params,
            "background": {"A": .1, "C": .2, "G": .3, "T": .4}, "length_probability": .9})
    assert sheet == original
    assert changed["rows"][0]["components"]["composition_relative_entropy"]["value"] != native["rows"][0]["components"]["composition_relative_entropy"]["value"]
    assert all(c["state"] == "not_applicable" for c in changed["checks"])
    json.dumps(changed, allow_nan=False)


def test_single_match_state_has_no_entry_denominator_but_other_statistics_exist():
    text = (NATIVE / "hmmbuild_dna/profile.hmm").read_text()
    lines = text.splitlines()
    first = next(i for i, line in enumerate(lines) if line.split() and line.split()[0] == "1")
    model = "\n".join([line if not line.startswith("LENG") else "LENG 1"
                       for line in lines[:first + 3]] + ["//", ""]).encode()
    sheet = make_sheet(model, b"1 tiny_dna TINYDNA001 3 3.00 1 1.00 1.00 nan .01\n")
    result = calculate_hmmstat_components(sheet, **native_hmmstat_parameters("3.4", "DNA"))
    c = result["rows"][0]["components"]
    assert c["entry_occupancy_sum"]["value"] == 0
    assert c["position_relative_entropy"]["state"] == "nonfinite"
    assert c["mean_match_entropy"]["state"] == "present"
    assert c["composition_relative_entropy"]["state"] == "present"
    assert any(i["code"] == "zero_denominator" for i in result["issues"])


def test_positive_mi_weight_with_zero_mm_log_is_not_fabricated_finite():
    model = (NATIVE / "hmmbuild_dna/profile.hmm").read_text().splitlines()
    first = next(i for i, line in enumerate(model) if line.split() and line.split()[0] == "1")
    tokens = model[first + 2].split()
    tokens[0] = "*"
    model[first + 2] = " ".join(tokens)
    sheet = make_sheet(("\n".join(model) + "\n").encode(), (NATIVE / "hmmstat_dna/stdout.log").read_bytes())
    result = calculate_hmmstat_components(sheet, **native_hmmstat_parameters("3.4", "DNA"))
    c = result["rows"][0]["components"]
    assert c["position_relative_entropy"]["state"] == "nonfinite"
    assert c["mean_match_relative_entropy"]["state"] == "present"
    assert any(i["code"] == "logarithm_nonfinite" for i in result["issues"])
    json.dumps(result, allow_nan=False)


def test_incomplete_model_preserves_prefix_statistics_without_complete_mean():
    text = (NATIVE / "hmmbuild_dna/profile.hmm").read_text()
    sheet = make_sheet(text.rsplit("//", 1)[0].encode(), (NATIVE / "hmmstat_dna/stdout.log").read_bytes(), completeness="partial")
    result = calculate_hmmstat_components(sheet, **native_hmmstat_parameters("3.4", "DNA"))
    c = result["rows"][0]["components"]
    assert c["sequence_count"]["value"] == 3
    assert c["mean_match_entropy"]["state"] == "incomplete"
    assert c["occupancy_sum"]["state"] == "incomplete"


def test_unknown_native_version_does_not_assert_background_equivalence():
    sheet = native_case()
    sheet["operation"]["engine_version"] = "unknown"
    result = calculate_hmmstat_components(sheet, **native_hmmstat_parameters("3.4", "DNA"))
    assert all(c["state"] == "unknown" for c in result["checks"])


def test_nonfinite_configuration_is_not_saved_as_json_nan():
    with pytest.raises(ValueError):
        calculate_hmmstat_components(native_case(), length_probability=math.nan)
