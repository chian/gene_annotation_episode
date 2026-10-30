"""Synthetic source selections; no actual scientific evidence is invented."""
from copy import deepcopy

import pytest

from gene_annotation_episode.literature_assay_inputs import _Sources
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_reaction_calculations import populate_reaction_constraints
from gene_annotation_episode.literature_reaction_native_inputs import (
    VERSION, native_direct_references, read_native_reaction_selection,
)


def witness(raw, quote, ref="source_report", occurrence=0):
    encoded = quote.encode()
    start = -1
    for _ in range(occurrence + 1):
        start = raw.index(encoded, start + 1)
    return {"source_ref": ref, "representation": "original", "start": start,
            "end": start + len(encoded), "quote": quote}


def number(raw, quote, token, ref="source_report", *, offset=0):
    start = quote.index(token, offset)
    return {"witness": witness(raw, quote, ref), "number_start": start, "number_end": start + len(token)}


def point(raw, quote, token):
    return {"kind": "point", "number": number(raw, quote, token)}


def declared(value, basis="conditional_assumption"):
    return {"kind": "declared", "value": value, "basis": basis, "evidence": []}


def meanings(ratio=True, budget=False):
    model = dict.fromkeys(("definition", "reaction", "function_relation", "prediction_evidence"))
    model["prediction_basis"] = "conditional_assumption"
    return {"ratio": {"claim": model, "alternatives": []} if ratio else None, "budget": None}


def recipe(raw=b"Reported ratio = 0.8."):
    return {"version": VERSION, "ratio": {"mode": "source_summary", "ratio_kind": "product_pair",
        "unit": "mol_per_mol", "measurement_basis": "reported_molar_ratio", "basis_witnesses": [],
        "observations": [], "summary": {"value": point(raw, raw.decode(), "0.8"),
            "uncertainty": {"kind": "unreported", "number": None, "basis_witnesses": []},
            "count": {"number": None, "basis": "unknown", "basis_witnesses": []}},
        "claim": declared(1), "alternatives": []}, "budget": None, "meanings": meanings()}


def read(selection, raw=b"Reported ratio = 0.8.", *, callback=None):
    sources = _Sources(callback or (lambda ref, representation: {"artifact_ref": "artifact_report", "content": raw}))
    normalized, trace = read_native_reaction_selection(selection, sources=sources)
    return normalized, trace


def test_actual_report_number_populates_existing_cells_without_supplied_measurement():
    selected = recipe()
    assert "mean" not in selected["ratio"]
    normalized, trace = read(selected)
    sheet = populate_reaction_constraints({k: normalized[k] for k in ("ratio", "budget")})
    assert sheet["cells"]["ratio_mean"]["value"] == .8
    assert sheet["cells"]["claim_nominal_squared_error"]["value"] == pytest.approx(.04)
    assert sheet["cells"]["claim_mean_squared_error"]["value"] is None
    assert normalized["ratio"]["independent_n"] is None
    assert trace["ratio"]["summary"]["ratio"]["form"] == "reported_point"
    assert native_direct_references(trace) == ["source_report"]


def test_reported_colon_ratio_retains_both_source_operands():
    raw = b"Product A : product B = 3:2."
    selected = recipe()
    selected["ratio"]["summary"]["value"] = {"kind": "reported_pair",
        "numerator": number(raw, raw.decode(), "3"), "denominator": number(raw, raw.decode(), "2")}
    normalized, trace = read(selected, raw)
    assert normalized["ratio"]["mean"] == 1.5
    expression = trace["ratio"]["summary"]["ratio"]
    assert expression["form"] == "normalized_reported_pair"
    assert expression["numerator"]["value"] == 3 and expression["denominator"]["value"] == 2


@pytest.mark.parametrize("basis,expected", [("technical_repeat", None), ("unknown", None),
    ("independent_experiment", 4), ("biological_preparation", 4)])
def test_reported_count_is_not_automatically_independent_n(basis, expected):
    raw = b"Reported ratio = 0.8; SD = 0.2; n = 4."
    selected = recipe(raw)
    selected["ratio"]["summary"]["uncertainty"].update(kind="sample_sd", number=number(raw, raw.decode(), "0.2"))
    selected["ratio"]["summary"]["count"].update(basis=basis, number=number(raw, raw.decode(), "4"))
    normalized, trace = read(selected, raw)
    assert normalized["ratio"]["independent_n"] == expected
    assert trace["ratio"]["summary"]["count"]["reported_n"] == 4
    assert trace["ratio"]["summary"]["count"]["basis"] == basis
    cell = populate_reaction_constraints({k: normalized[k] for k in ("ratio", "budget")})["cells"]["claim_mean_squared_error"]
    assert cell["value"] == (None if expected is None else pytest.approx(.07))


@pytest.mark.parametrize("kind", ["sem", "unspecified"])
def test_other_spread_kind_is_retained_but_not_relabelled_sample_sd(kind):
    raw = b"Reported ratio = 0.8; uncertainty = 0.2; n = 4."
    selected = recipe(raw)
    selected["ratio"]["summary"]["uncertainty"].update(kind=kind, number=number(raw, raw.decode(), "0.2"))
    selected["ratio"]["summary"]["count"].update(basis="biological_preparation", number=number(raw, raw.decode(), "4"))
    normalized, trace = read(selected, raw)
    assert normalized["ratio"]["sample_sd"] is None
    assert trace["ratio"]["summary"]["uncertainty"]["kind"] == kind
    assert trace["ratio"]["summary"]["uncertainty"]["number"]["value"] == .2


@pytest.mark.parametrize("raw,token", [(b"Reported ratio < 0.8.", "0.8"),
    (b"Reported ratio about 0.8.", "0.8"), (b"Reported ratio = 10.8.", "0.8"),
    (b"Reported ratio = 0.8e2.", "0.8"), (b"Reported ratio = 0.8-1.0.", "0.8")])
def test_limits_approximation_and_clipped_numbers_never_become_exact_points(raw, token):
    selected = recipe()
    selected["ratio"]["summary"]["value"] = point(raw, raw.decode(), token)
    with pytest.raises(ExperimentalContractError):
        read(selected, raw)


def test_discovered_source_authorization_happens_before_bytes():
    selected = recipe()
    selected["ratio"]["summary"]["value"]["number"]["witness"]["source_ref"] = "source_forbidden"
    called = []
    def callback(ref, representation):
        called.append((ref, representation))
        raise PermissionError("source_not_received")
    with pytest.raises(PermissionError):
        read(selected, callback=callback)
    assert called == [("source_forbidden", "original")]


def test_wrong_quote_and_supplied_measured_values_are_rejected():
    selected = recipe()
    selected["ratio"]["summary"]["value"]["number"]["witness"]["quote"] = "Reported ratio = 0.7."
    with pytest.raises(ExperimentalContractError):
        read(selected)
    selected = recipe()
    selected["ratio"]["mean"] = 1
    with pytest.raises(ExperimentalContractError):
        read(selected)


def test_signal_integrals_do_not_silently_become_molar_ratios():
    selected = recipe()
    selected["ratio"]["measurement_basis"] = "signal_ratio"
    with pytest.raises(ExperimentalContractError):
        read(selected)
    selected["ratio"].update(ratio_kind="signal_ratio", unit="signal_per_signal")
    normalized, trace = read(selected)
    assert normalized["ratio"]["unit"] == "signal_per_signal"


def test_independent_units_preserve_distinct_equal_values_and_reject_same_span_twice():
    raw = b"Preparation A ratio = 0.8; preparation B ratio = 0.8."
    selected = recipe()
    selected["ratio"].update(mode="independent_units", summary=None)
    observations = []
    for i, offset in enumerate((0, raw.index(b"preparation B"))):
        item = point(raw, raw.decode(), "0.8")
        item["number"]["number_start"] = raw.decode().index("0.8", offset)
        item["number"]["number_end"] = item["number"]["number_start"] + 3
        observations.append({"measurement_key": str(i), "value": item, "basis_witnesses": []})
    selected["ratio"]["observations"] = observations
    normalized, trace = read(selected, raw)
    assert len(normalized["ratio"]["observations"]) == 2
    selected["ratio"]["observations"][1]["value"] = deepcopy(observations[0]["value"])
    with pytest.raises(ExperimentalContractError):
        read(selected, raw)


def test_source_reported_model_parameter_requires_number_selector():
    selected = recipe()
    selected["ratio"]["claim"]["basis"] = "source_reported"
    with pytest.raises(ExperimentalContractError):
        read(selected)
    selected["ratio"]["claim"] = {"kind": "source_number", "number": number(
        b"Reported ratio = 0.8.", "Reported ratio = 0.8.", "0.8"), "evidence": []}
    normalized, trace = read(selected)
    assert normalized["ratio"]["claim"] == .8
    assert trace["ratio"]["claim"]["basis"] == "source_reported"


@pytest.mark.parametrize("native,canonical,expected", [("mM", "uM", 2000),
    ("nmol", "umol", .002), ("uM/s", "uM_per_min", 120)])
def test_selected_resource_units_are_converted_with_dimensions(native, canonical, expected):
    raw = ("Supply = 2 " + native + ".").encode()
    selected = {"version": VERSION, "ratio": None, "meanings": meanings(False),
        "budget": {"basis": "usable_rate" if "per_min" in canonical else "supplied_reagent_batch",
            "unit": canonical, "resources_complete": True, "resources": [{"resource_key": "supplied",
                "value": {"number": number(raw, raw.decode(), "2"), "unit": witness(raw, native)},
                "lower": None, "upper": None, "coefficient": declared(1)}], "demand": declared(10)}}
    normalized, trace = read(selected, raw)
    assert normalized["budget"]["resources"][0]["value"] == expected
    assert trace["budget"]["resources"][0]["value"]["unit"]["raw_unit"] == native
    assert trace["budget"]["demand"]["basis"] == "conditional_assumption"


def test_partial_or_dimensionally_different_resource_unit_is_rejected():
    raw = b"Supply = 2 uM/min."
    selected = {"version": VERSION, "ratio": None, "meanings": meanings(False),
        "budget": {"basis": "supplied_reagent_batch", "unit": "umol", "resources_complete": True,
            "resources": [{"resource_key": "x", "value": {"number": number(raw, raw.decode(), "2"),
                "unit": witness(raw, "uM")}, "lower": None, "upper": None, "coefficient": declared(1)}],
            "demand": declared(10)}}
    with pytest.raises(ExperimentalContractError):
        read(selected, raw)
    selected["budget"]["resources"][0]["value"]["unit"] = witness(raw, "uM/min")
    with pytest.raises(ExperimentalContractError):
        read(selected, raw)


def test_confidence_interval_requires_its_own_endpoint_contract():
    selected = recipe()
    selected["ratio"]["summary"]["uncertainty"]["kind"] = "confidence_interval"
    with pytest.raises(ExperimentalContractError):
        read(selected)


def test_explicit_sem_label_cannot_be_relabelled_sample_sd():
    raw = b"Reported ratio = 0.8; SEM = 0.2; n = 4."
    selected = recipe(raw)
    selected["ratio"]["summary"]["uncertainty"].update(kind="sample_sd", number=number(raw, raw.decode(), "0.2"))
    with pytest.raises(ExperimentalContractError):
        read(selected, raw)
    selected["ratio"]["summary"]["uncertainty"]["kind"] = "sem"
    normalized, trace = read(selected, raw)
    assert normalized["ratio"]["sample_sd"] is None
    assert trace["ratio"]["summary"]["uncertainty"]["kind"] == "sem"


@pytest.mark.parametrize("case,expected", [("mismatch", None), ("correct", 2000), ("header", 2)])
def test_explicit_cell_unit_conflict_and_legitimate_shared_header(case, expected):
    raw = (b"Supplied amount 2 mM. Reference unit uM." if case != "header" else
           b"Table header: uM. Supply row: 2; no adjacent printed unit.")
    chosen = "mM" if case == "correct" else "uM"
    selected = {"version": VERSION, "ratio": None, "meanings": meanings(False),
        "budget": {"basis": "supplied_reagent_batch", "unit": "uM", "resources_complete": True,
            "resources": [{"resource_key": "supply", "value": {"number": number(raw, raw.decode(), "2"),
                "unit": witness(raw, chosen)}, "lower": None, "upper": None, "coefficient": declared(1)}],
            "demand": declared(10)}}
    if expected is None:
        with pytest.raises(ExperimentalContractError, match="native_reaction_explicit_unit_conflict"):
            read(selected, raw)
    else:
        normalized, trace = read(selected, raw)
        assert normalized["budget"]["resources"][0]["value"] == expected
