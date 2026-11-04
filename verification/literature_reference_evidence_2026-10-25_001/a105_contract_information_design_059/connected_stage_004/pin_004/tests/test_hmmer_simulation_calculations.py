"""Native numerical answers, failure states, and offline recalculation."""
from copy import deepcopy
import json
import math
from pathlib import Path

import pytest

from gene_annotation_episode.hmmer_simulation_data import populate_hmmsim_sheet
from gene_annotation_episode.hmmer_simulation_calculations import calculate_hmmsim_components, _gumbel_survival
from test_hmmer_simulation_data import CASES, native_case, synthetic_case, payload


def rows(calculation, kind, variant=None):
    return [r for r in calculation["rows"] if r["kind"] == kind and (variant is None or r["details"].get("variant") == variant)]


def value(row, component):
    return row["components"][component]["value"]


@pytest.mark.parametrize("case", CASES)
def test_native_all_modes_numerical_fit_and_summary_rounding(case):
    sheet = populate_hmmsim_sheet(**native_case(case))
    calculated = calculate_hmmsim_components(sheet, parameters={"fit_tolerance": 1e-5})
    stats = rows(calculated, "score_statistics")[0]
    assert value(stats, "observed_count") == 1000
    assert value(stats, "sample_variance") > 0
    assert all(r["components"]["mu"]["state"] == "present" for r in rows(calculated, "fit", "independent"))
    assert not [c for c in calculated["checks"] if c["state"] == "fail"]
    assert not {"fit_failed", "fit_nonfinite", "native_rounding_difference", "alignment_score_difference"} & {i["code"] for i in calculated["issues"]}
    json.dumps(calculated, allow_nan=False)


def test_viterbi_concrete_independent_numeric_answer():
    sheet = populate_hmmsim_sheet(**native_case())
    calc = calculate_hmmsim_components(sheet)
    stats = rows(calc, "score_statistics")[0]
    fit = rows(calc, "fit", "independent")[0]
    assert value(stats, "mean") == pytest.approx(-5.619071923450204, abs=1e-13)
    assert value(stats, "x10") == pytest.approx(-0.6476082390605439, abs=1e-14)
    assert value(fit, "mu") == pytest.approx(-6.414576359999045, abs=1e-8)
    assert value(fit, "lambda") == pytest.approx(.7137499186051701, abs=1e-8)
    assert value(fit, "E10") == pytest.approx(16.174564750739254, abs=2e-7)
    native_filter = rows(calc, "native_filter")[0]
    assert value(native_filter, "count") == 368
    assert value(native_filter, "fraction") == .368
    assert value(rows(calc, "filter_recalculation")[0], "count") == 368
    alignment = rows(calc, "alignment_statistics")[0]
    assert value(alignment, "alignment_mean") == 4.439
    assert value(alignment, "alignment_sample_sd") == pytest.approx(1.8616510802899517, abs=1e-13)
    assert value(rows(calc, "native_summary")[0], "mu") == -6.4146
    residual = next(r for r in rows(calc, "native_rounding_residuals") if r["details"]["fit_record_key"] == fit["record_key"])
    assert value(residual, "mu") == pytest.approx(value(fit, "mu") + 6.4146, abs=1e-15)


def test_forward_concrete_tail_population_fits_and_full_population_calibration():
    calc = calculate_hmmsim_components(populate_hmmsim_sheet(**native_case("fwd_fs")))
    first, second = rows(calc, "fit", "independent")
    assert value(first, "tail_count") == 100
    assert value(first, "mu") == pytest.approx(1.2244937724332836, abs=1e-14)
    assert value(first, "lambda") == pytest.approx(.8836442251850544, abs=1e-14)
    assert value(first, "E10") == pytest.approx(12.511194245467216, abs=1e-12)
    assert value(second, "tail_count") == 200
    assert not rows(calc, "native_filter")
    assert all(r["details"]["expectation_population_mass"] == 1 for r in rows(calc, "fit", "native_calibration"))


def test_hybrid_native_undetermined_location_is_never_usable_calibration():
    calc = calculate_hmmsim_components(populate_hmmsim_sheet(**native_case("hyb_fs")))
    assert rows(calc, "fit", "native_calibration")[0]["components"]["mu"]["state"] == "incompatible"
    assert value(rows(calc, "fit", "native_calibration")[0], "E10") is None
    assert value(rows(calc, "native_summary")[0], "pmu") is None
    assert value(rows(calc, "native_filter")[0], "count") is not None
    assert value(rows(calc, "filter_recalculation")[0], "count") is None
    assert value(rows(calc, "native_experimental_filter_replay")[0], "count") == value(rows(calc, "native_filter")[0], "count")
    assert "calibration_undetermined" in {i["code"] for i in calc["issues"]}


@pytest.mark.parametrize("values,expected", [([], "score_vector_incomplete"), ([0], "population_insufficient"),
    ([0]*10, "constant_population"), ([1, 2, float("inf")], "score_vector_invalid")])
def test_empty_constant_short_and_nonfinite_vectors(values, expected):
    calc = calculate_hmmsim_components(populate_hmmsim_sheet(**synthetic_case(values)))
    assert expected in {i["code"] for i in calc["issues"]}
    assert value(rows(calc, "fit", "independent")[0], "E10") is None
    assert value(rows(calc, "score_statistics")[0], "observed_count") == len(values)


def test_sample_variance_n_minus_one_ties_and_zero_mean_are_measured():
    calc = calculate_hmmsim_components(populate_hmmsim_sheet(**synthetic_case([-1, 1]*5)))
    stats = rows(calc, "score_statistics")[0]
    assert value(stats, "mean") == 0
    assert value(stats, "sample_variance") == pytest.approx(10/9)
    assert value(stats, "x10") == -1
    assert stats["components"]["mean"]["state"] == "present"


def test_forward_empty_and_constant_tail_invalid_no_zero_fit():
    sheet = populate_hmmsim_sheet(**synthetic_case([0]*19+[1], mode="forward"))
    calc = calculate_hmmsim_components(sheet, parameters={"tail_masses": [.01, .05, .1]})
    fits = rows(calc, "fit", "independent")
    assert [value(r, "tail_count") for r in fits] == [0, 1, 2]
    assert [r["components"]["mu"]["state"] for r in fits] == ["failed", "failed", "present"]
    assert value(fits[2], "lambda") == 2
    assert value(fits[2], "E10") == 2


def test_numerical_iteration_limit_is_visible_failure():
    calc = calculate_hmmsim_components(populate_hmmsim_sheet(**native_case()), parameters={"solver_iteration_limit": 1})
    fit = rows(calc, "fit", "independent")[0]
    assert fit["details"]["iterations"] == 1
    assert fit["components"]["mu"]["state"] == "failed"
    assert "fit_failed" in {i["code"] for i in calc["issues"]}


def test_changed_solver_tolerance_keeps_native_values_and_actual_residual():
    sheet = populate_hmmsim_sheet(**native_case("hyb_ls"))
    tight = calculate_hmmsim_components(sheet)
    native_tolerance = calculate_hmmsim_components(sheet, parameters={"fit_tolerance": 1e-5})
    assert value(rows(tight, "fit", "independent")[0], "E10") != value(rows(native_tolerance, "fit", "independent")[0], "E10")
    assert rows(tight, "native_summary") == rows(native_tolerance, "native_summary")
    checks = [c for c in tight["checks"] if c["name"] == "native_rounding.E10"]
    assert checks[0]["state"] == "unknown"
    assert checks[0]["details"]["residual"] == pytest.approx(-.00018463983576921805, abs=1e-12)


def test_stable_survival_and_shifted_gumbel_fit():
    assert _gumbel_survival(-1e300, 0, 1) == 1
    assert _gumbel_survival(1e300, 0, 1) == 0
    assert _gumbel_survival(40, 0, 1) == pytest.approx(math.exp(-40), rel=1e-14)
    values = list(range(20))
    first = calculate_hmmsim_components(populate_hmmsim_sheet(**synthetic_case(values)))
    second = calculate_hmmsim_components(populate_hmmsim_sheet(**synthetic_case([x+100000 for x in values])))
    a, b = rows(first, "fit", "independent")[0], rows(second, "fit", "independent")[0]
    assert value(a, "lambda") == pytest.approx(value(b, "lambda"), rel=1e-12)
    assert value(a, "mu") + 100000 == pytest.approx(value(b, "mu"), abs=1e-10)


@pytest.mark.parametrize("parameters", [{"fixed_lambda": 0}, {"fixed_lambda": float("nan")}, {"tail_masses": [2]},
    {"tail_masses": []}, {"fit_tolerance": -1}, {"solver_iteration_limit": 0}, {"rounding_tolerance": 0},
    {"filter_criterion": {"threshold": 1}}, {"extra": 2}])
def test_invalid_parameters_remain_explicit(parameters):
    calc = calculate_hmmsim_components(populate_hmmsim_sheet(**native_case()), parameters=parameters)
    assert calc["issues"]
    assert not calc["rows"]


def test_filter_operators_and_custom_threshold_are_not_native_criterion():
    sheet = populate_hmmsim_sheet(**synthetic_case([-1, 0, 1]*4))
    counts = []
    for comparison in ("<", "<=", ">", ">="):
        calc = calculate_hmmsim_components(sheet, parameters={"filter_criterion": {
            "threshold": 0, "meaning": "score", "comparison": comparison, "fit_variant": "independent"}})
        counts.append(value(rows(calc, "filter_recalculation")[0], "count"))
        assert not [c for c in calc["checks"] if c["name"] == "native_filter_count"]
    assert counts == [4, 8, 4, 8]


def test_missing_scores_do_not_refit_rounded_summary():
    args = native_case()
    del args["outputs"]["scores"]
    calc = calculate_hmmsim_components(populate_hmmsim_sheet(**args))
    assert value(rows(calc, "native_summary")[0], "mu") == -6.4146
    assert not rows(calc, "fit")
    assert rows(calc, "score_statistics")[0]["components"]["mean"]["state"] == "missing"


def test_verbose_rounded_vector_is_retained_but_never_independently_fitted():
    args = synthetic_case()
    del args["outputs"]["scores"]
    args["operation"]["settings"].update({"-v": True, "-o": "summary.txt"})
    args["outputs"]["stdout"] = [payload(b"1.235\n"*20, "stdout")]
    calc = calculate_hmmsim_components(populate_hmmsim_sheet(**args))
    assert "score_vector_rounded" in {i["code"] for i in calc["issues"]}
    assert value(rows(calc, "fit", "independent")[0], "mu") is None
    assert rows(calc, "fit", "independent")[0]["components"]["mu"]["state"] == "incompatible"


def test_partial_final_model_does_not_destroy_complete_earlier_fit():
    args = synthetic_case(models=2)
    raw = args["outputs"]["scores"][0]["content"][:-13]
    args["outputs"]["scores"] = [payload(raw, "scores", completeness="partial")]
    calc = calculate_hmmsim_components(populate_hmmsim_sheet(**args))
    first, second = rows(calc, "fit", "independent")
    assert first["components"]["mu"]["state"] == "present"
    assert second["components"]["mu"]["state"] == "incomplete"


def test_no_unique_authority_for_duplicate_summary_artifacts():
    args = native_case()
    raw = args["outputs"]["stdout"][0]["content"]
    args["outputs"]["summary"] = [payload(raw, "summary"), payload(raw, "summary", ordinal=1)]
    calc = calculate_hmmsim_components(populate_hmmsim_sheet(**args))
    assert "calibration_ambiguous" in {i["code"] for i in calc["issues"]}
    assert value(rows(calc, "fit", "native_calibration")[0], "E10") is None
    assert value(rows(calc, "fit", "independent")[0], "E10") is not None


def test_native_calibration_and_fixed_slope_operands_are_exact():
    calc = calculate_hmmsim_components(populate_hmmsim_sheet(**native_case()))
    calibrated = rows(calc, "fit", "native_calibration")[0]
    fixed = rows(calc, "fit", "fixed_lambda")[0]
    assert calibrated["components"]["mu"]["inputs"] == [{"record_key": "output:stdout:0#summary/0", "field": "payload.values.pmu"}]
    assert calibrated["components"]["lambda"]["inputs"] == [{"record_key": "output:stdout:0#summary/0", "field": "payload.values.plambda"}]
    assert fixed["components"]["lambda"]["inputs"] == [{"record_key": None, "field": "parameters.fixed_lambda"}]


def test_json_saved_sheet_changed_parameters_offline_without_files_native_or_network(monkeypatch):
    import builtins
    import socket
    import subprocess
    from gene_annotation_episode.state import Store
    sheet = json.loads(json.dumps(populate_hmmsim_sheet(**native_case("fwd_fs")), allow_nan=False))
    before = deepcopy(sheet)
    baseline = calculate_hmmsim_components(sheet)
    def forbidden(*a, **k):
        raise AssertionError("calculator attempted I/O or execution")
    with monkeypatch.context() as patch:
        for obj, name in ((builtins, "open"), (Path, "open"), (socket, "socket"), (subprocess, "Popen"), (Store, "__init__")):
            patch.setattr(obj, name, forbidden)
        changed = calculate_hmmsim_components(sheet, parameters={"tail_masses": [.15], "fixed_lambda": .8,
            "filter_criterion": {"threshold": .05, "meaning": "survival_probability", "comparison": "<=", "fit_variant": "independent"}})
    assert sheet == before
    assert value(rows(changed, "fit", "independent")[0], "tail_count") == 150
    assert value(rows(changed, "fit", "independent")[0], "lambda") != value(rows(baseline, "fit", "independent")[0], "lambda")
    assert value(rows(changed, "fit", "fixed_lambda")[0], "lambda") == .8
    assert value(rows(changed, "filter_recalculation")[0], "count") is not None
