"""Synthetic numerical fixtures only; no biological observation is claimed."""

import ast
import builtins
from copy import deepcopy
import hashlib
import inspect
import json

import pytest

from gene_annotation_episode import fluorescence_event_calculations as calculations
from gene_annotation_episode import fluorescence_result_views as views
from gene_annotation_episode.fluorescence_event_contracts import (
    PARSE_SCHEMA, FluorescenceContractError, canonical, issue, validate_components,
)
from gene_annotation_episode.fluorescence_event_sheet import populate_fluorescence_sheet


def _file(raw=b"synthetic evidence", format_name="synthetic_fixture"):
    sha = hashlib.sha256(raw).hexdigest()
    return dict(artifact_ref="artifact_" + sha, sha256=sha,
                size_bytes=len(raw), format=format_name)


def _location(ordinal=None):
    return dict(record_ordinal=ordinal, line_start=None, line_end=None,
                byte_start=None, byte_end=None)


def _basis():
    return dict(key="explicit synthetic comparison", evidence_file=_file())


def _batch(rows, *, sample="s", domain=None, extent="complete", width=None,
           correspondence=None, state="available"):
    domain = domain or sample + ".raw"
    width = len(rows[0]) if rows else (width or 1)
    sample_data = dict(key=sample, primary_domain_key=sample + ".raw",
                       label="duplicate sample label", condition=None,
                       biological_replicate=None, technical_replicate=None,
                       associations=[])
    source = dict(key=domain + ".source", file=_file(canonical(rows)), dataset_position=0,
                  format_profile="synthetic_fixture", extent=extent,
                  native_event_count=None, metadata=[dict(name="fixture", value="not measured biology")])
    if extent == "unavailable":
        source["file"] = None
    channels = [dict(key=domain + f".c{index}", domain_key=domain, ordinal=index,
                     native_name="duplicate", label="duplicate", unit="instrument_units",
                     analyte=dict(namespace="synthetic", identifier=f"analyte{index}",
                                  file=_file(), source_key=None, location=_location()))
                for index in range(width)]
    preparation = dict(state="not_applied", method=None, parameters_file=None)
    domain_data = dict(key=domain, sample_key=sample, source_key=source["key"],
                       parent_domain_key=None if correspondence is None else sample + ".raw",
                       state=state, scale_kind="as_supplied", compensation=deepcopy(preparation),
                       transformation=deepcopy(preparation), correspondence=correspondence,
                       comparison_basis=_basis())
    events = []
    mapping = {entry["source_ordinal"]: entry["event_ordinal"] for entry in correspondence or []}
    for ordinal, row in enumerate(rows):
        events.append(dict(sample_key=sample, domain_key=domain,
                           event_ordinal=mapping[ordinal] if correspondence is not None else ordinal,
                           source_ordinal=ordinal, location=_location(ordinal),
                           values=[dict(channel_key=channel["key"], measurement=dict(
                               value=value, state="missing" if value is None else "supplied_predicted",
                               raw=None if value is None else str(value)))
                                   for channel, value in zip(channels, row)]))
    issues = []
    if extent == "unavailable":
        issues.append(issue("source_unavailable", "input", source_key=source["key"],
                            sample_key=sample, domain_key=domain))
    if state != "available":
        issues.append(issue("measurement_domain_unavailable", "domain", source_key=source["key"],
                            sample_key=sample, domain_key=domain))
    return dict(schema=PARSE_SCHEMA, source=source, sample=sample_data,
                channels=channels, domain=domain_data, events=events, issues=issues)


def _gate(key="g", *, sample="s", parent=None, channel=0, domain=None,
          lower=100, upper=250, inclusive=True, kind="threshold"):
    domain = domain or sample + ".raw"
    return dict(key=key, sample_key=sample, parent=parent or dict(kind="population", key=sample + ".population"),
                kind=kind, domain_key=None if kind == "pass_all" else domain,
                channel_key=None if kind == "pass_all" else domain + f".c{channel}",
                lower=None if lower is None or kind == "pass_all" else dict(value=lower, inclusive=inclusive),
                upper=None if upper is None or kind == "pass_all" else dict(value=upper, inclusive=inclusive))


def _sheet(batches, *, gates=None, populations=None, controls=None, reports=None):
    if populations is None:
        samples = list(dict.fromkeys(batch["sample"]["key"] for batch in batches))
        populations = [dict(key=sample + ".population", sample_key=sample, kind="all", event_ordinals=None)
                       for sample in samples]
    return populate_fluorescence_sheet(batches, populations=populations,
                                       gates=gates if gates is not None else [_gate()],
                                       control_pairs=controls or [], native_reports=reports or [])


def _parameters(*, fractions=None, intensities=None, controls=None, native=None):
    return dict(fraction_requests=fractions or [], intensity_requests=intensities or [],
                control_requests=controls or [], native_comparison_requests=native or [])


def _standard_parameters():
    return _parameters(fractions=[dict(gate_key="g", denominator="parent")],
                       intensities=[dict(gate_key="g", domain_key="s.raw", channel_key="s.raw.c0")])


def _request(kind, metric, *, gate_key=None, domain_key=None, channel_key=None,
             control_key=None, native_report_key=None, denominator="none"):
    return dict(kind=kind, metric=metric, gate_key=gate_key, domain_key=domain_key,
                channel_key=channel_key, control_key=control_key,
                native_report_key=native_report_key, denominator=denominator)


def _cell(result, metric, *, gate="g", denominator=None, domain=None, control=None, report=None):
    matches = [cell for cell in result["cells"] if cell["request"]["metric"] == metric
               and (gate is None or cell["request"]["gate_key"] == gate)
               and (denominator is None or cell["request"]["denominator"] == denominator)
               and (domain is None or cell["request"]["domain_key"] == domain)
               and (control is None or cell["request"]["control_key"] == control)
               and (report is None or cell["request"]["native_report_key"] == report)]
    assert len(matches) == 1
    return matches[0]


def test_packet548_complete_numerical_cells_and_exact_operands():
    sheet = _sheet([_batch([[value] for value in [90, 100, 125, 150, 200, 250, 300, 350]])])
    before = canonical(sheet)
    parameters = _standard_parameters()
    result = calculations.calculate_fluorescence_sheet(sheet, parameters=parameters)
    assert result["memberships"][0]["selected"] == [1, 2, 3, 4, 5]
    expected = dict(retained_event_count=8, parent_event_count=8, parent_unknown_count=0,
                    evaluable_event_count=8, selected_event_count=5, rejected_event_count=3,
                    unknown_gate_event_count=0, selected_fraction=.625, selected_percent=62.5,
                    selected_intensity_count=5, selected_intensity_missing_count=0,
                    selected_intensity_sum=825, selected_intensity_mean=165,
                    selected_intensity_median=150)
    for metric, value in expected.items():
        assert _cell(result, metric)["value"] == value
        assert _cell(result, metric)["state"] == "present"
    assert _cell(result, "selected_fraction")["population"]["denominator"] == "parent"
    mean = _cell(result, "selected_intensity_mean")
    assert mean["unit"] == "instrument_units"
    assert mean["population"]["denominator"] == "selected_finite"
    assert any(reference.startswith("sheet:/events/") for reference in mean["operands"])
    assert validate_components(result, sheet=sheet) is result
    assert result["status"] == "calculated"
    assert canonical(sheet) == before
    assert result["parameters"] == parameters and result["parameters"] is not parameters


def test_missing_eighth_value_requires_explicit_evaluable_denominator():
    sheet = _sheet([_batch([[value] for value in [90, 100, 125, 150, 200, 250, 300, None]])])
    parameters = _standard_parameters()
    original = calculations.calculate_fluorescence_sheet(sheet, parameters=parameters)
    assert _cell(original, "selected_fraction")["value"] is None
    assert not any(cell["request"]["denominator"] == "evaluable" for cell in original["cells"])
    parameters["fraction_requests"].append(dict(gate_key="g", denominator="evaluable"))
    result = calculations.calculate_fluorescence_sheet(sheet, parameters=parameters)
    assert _cell(result, "selected_fraction", denominator="parent")["value"] is None
    assert _cell(result, "selected_fraction", denominator="evaluable")["value"] == 5 / 7
    assert _cell(result, "selected_percent", denominator="evaluable")["value"] == 100 * (5 / 7)
    assert _cell(result, "selected_intensity_mean")["value"] == 165
    assert _cell(result, "selected_intensity_median")["value"] == 150
    assert _cell(result, "selected_intensity_mean")["state"] == "qualified"
    for metric, state in [("retained_event_count", "present"), ("parent_event_count", "present"),
                          ("evaluable_event_count", "present"), ("selected_event_count", "qualified"),
                          ("rejected_event_count", "qualified"), ("unknown_gate_event_count", "present")]:
        assert _cell(result, metric)["state"] == state
    assert result["memberships"][0]["unknown"] == [7]


def test_bounds_pass_all_and_duplicate_values_keep_original_occurrences():
    batch = _batch([[100], [100], [250], [250]])
    gates = [_gate("inclusive"), _gate("strict", inclusive=False), _gate("all", kind="pass_all")]
    sheet = _sheet([batch], gates=gates)
    memberships = calculations.evaluate_gate_membership(sheet)
    assert [entry["selected"] for entry in memberships] == [[0, 1, 2, 3], [], [0, 1, 2, 3]]
    gates[1]["upper"]["inclusive"] = True
    sheet = _sheet([batch], gates=gates)
    assert calculations.evaluate_gate_membership(sheet)[1]["selected"] == [2, 3]


def test_three_valued_ancestry_out_of_declaration_order_and_rejected_population():
    batch = _batch([[None, 0], [None, 2], [0, None], [2, None], [2, 2]])
    parent = _gate("parent", lower=1, upper=None, inclusive=False)
    child = _gate("child", parent=dict(kind="gate", key="parent"), channel=1,
                  lower=1, upper=None, inclusive=False)
    sheet = _sheet([batch], gates=[child, parent])
    result = calculations.calculate_fluorescence_sheet(sheet, parameters=_parameters())
    membership = result["memberships"][0]
    assert membership["selected"] == [4]
    assert membership["rejected"] == [0, 2]
    assert membership["unknown"] == [1, 3]
    assert membership["parent_unknown"] == [0, 1]
    assert membership["parent_evaluable"] == [4]
    assert membership["parent_nonevaluable"] == [3]
    assert _cell(result, "rejected_event_count", gate="child")["value"] == 0
    assert _cell(result, "parent_unknown_count", gate="child")["value"] == 2
    assert _cell(result, "parent_unknown_count", gate="child")["state"] == "present"


def test_false_child_resolves_unknown_ancestor_for_selected_count():
    gates = [_gate("parent", lower=1, upper=None),
             _gate("child", parent=dict(kind="gate", key="parent"), channel=1, lower=1, upper=None)]
    sheet = _sheet([_batch([[None, 0], [None, 0]])], gates=gates)
    result = calculations.calculate_fluorescence_sheet(sheet, parameters=_parameters())
    child = result["memberships"][1]
    assert child["parent_unknown"] == [0, 1] and child["unknown"] == []
    assert _cell(result, "selected_event_count", gate="child")["value"] == 0
    assert _cell(result, "selected_event_count", gate="child")["state"] == "present"
    assert _cell(result, "parent_event_count", gate="child")["state"] == "qualified"


@pytest.mark.parametrize("fault", ["cycle", "inverted", "nonfinite"])
def test_invalid_gate_contracts_reject(fault):
    sheet = _sheet([_batch([[150]])])
    if fault == "cycle":
        sheet["gate_definitions"][0]["parent"] = dict(kind="gate", key="g")
    elif fault == "inverted":
        sheet["gate_definitions"][0]["lower"]["value"] = 300
    else:
        sheet["gate_definitions"][0]["lower"]["value"] = float("inf")
    with pytest.raises(FluorescenceContractError) as error:
        calculations.calculate_fluorescence_sheet(sheet, parameters=_parameters())
    assert error.value.code == "invalid_gate"


@pytest.mark.parametrize("extent,state", [("unavailable", "available"), ("complete", "failed")])
def test_missing_primary_source_or_failed_domain_never_becomes_zero(extent, state):
    sheet = _sheet([_batch([], extent=extent, state=state)])
    result = calculations.calculate_fluorescence_sheet(sheet, parameters=_standard_parameters())
    assert all(cell["value"] is None and cell["state"] == "unavailable" for cell in result["cells"])
    assert result["status"] == "unavailable"


def test_empty_source_and_actual_zero_are_distinct_from_missing():
    empty = calculations.calculate_fluorescence_sheet(_sheet([_batch([])]), parameters=_standard_parameters())
    assert _cell(empty, "selected_event_count")["value"] == 0
    assert _cell(empty, "selected_event_count")["state"] == "present"
    assert _cell(empty, "selected_fraction")["value"] is None
    assert any(problem["code"] == "empty_parent_population" for problem in _cell(empty, "selected_fraction")["issues"])
    assert _cell(empty, "selected_intensity_count")["value"] == 0
    assert _cell(empty, "selected_intensity_sum")["value"] == 0
    assert _cell(empty, "selected_intensity_mean")["value"] is None
    assert _cell(empty, "selected_intensity_median")["value"] is None
    zero = calculations.calculate_fluorescence_sheet(_sheet([_batch([[0], [0]])]), parameters=_standard_parameters())
    assert _cell(zero, "selected_fraction")["value"] == 0
    assert _cell(zero, "selected_fraction")["state"] == "present"


def test_partial_tail_does_not_become_population_but_explicit_subset_is_finite():
    batch = _batch([[100], [150], [300], [250]], extent="partial")
    batch["source"]["native_event_count"] = 100
    sheet = _sheet([batch])
    all_result = calculations.calculate_fluorescence_sheet(sheet, parameters=_standard_parameters())
    assert all_result["memberships"][0]["universe_event_ordinals"] == [0, 1, 2, 3]
    assert all_result["memberships"][0]["unknown"] == []
    assert not all_result["memberships"][0]["population_complete"]
    assert _cell(all_result, "retained_event_count")["value"] == 4
    assert _cell(all_result, "retained_event_count")["state"] == "qualified"
    assert _cell(all_result, "selected_fraction")["value"] is None
    sheet["population_definitions"][0].update(kind="subset", event_ordinals=[3, 1])
    subset = calculations.calculate_fluorescence_sheet(sheet, parameters=_standard_parameters())
    assert subset["memberships"][0]["universe_event_ordinals"] == [1, 3]
    assert subset["memberships"][0]["population_complete"]
    assert _cell(subset, "selected_fraction")["value"] == 1
    assert _cell(subset, "retained_event_count")["value"] == 2
    assert _cell(subset, "retained_event_count")["state"] == "present"


def test_derived_domain_correspondence_absent_values_and_exact_intensity_domain():
    primary = _batch([[100], [200], [300]])
    derived = _batch([[40], [10]], domain="s.prepared", correspondence=[
        dict(source_ordinal=0, event_ordinal=2), dict(source_ordinal=1, event_ordinal=0)])
    derived["domain"]["compensation"] = dict(state="applied", method="supplied_matrix", parameters_file=_file())
    sheet = _sheet([primary, derived], gates=[_gate(domain="s.prepared", lower=20, upper=None)])
    parameters = _parameters(fractions=[dict(gate_key="g", denominator="evaluable")], intensities=[
        dict(gate_key="g", domain_key="s.raw", channel_key="s.raw.c0"),
        dict(gate_key="g", domain_key="s.prepared", channel_key="s.prepared.c0")])
    before = canonical(sheet)
    result = calculations.calculate_fluorescence_sheet(sheet, parameters=parameters)
    assert result["memberships"][0]["selected"] == [2]
    assert result["memberships"][0]["rejected"] == [0]
    assert result["memberships"][0]["unknown"] == [1]
    assert _cell(result, "selected_fraction")["value"] == .5
    assert _cell(result, "selected_intensity_mean", domain="s.raw")["value"] == 300
    assert _cell(result, "selected_intensity_mean", domain="s.prepared")["value"] == 40
    assert canonical(sheet) == before


def test_unavailable_derived_domain_preserves_known_primary_and_missing_intensities():
    primary = _batch([[100], [200], [300]])
    derived = _batch([], domain="s.prepared", extent="unavailable", correspondence=[])
    gates = [_gate(domain="s.prepared"), _gate("all", kind="pass_all")]
    sheet = _sheet([primary, derived], gates=gates)
    parameters = _parameters(intensities=[dict(gate_key="all", domain_key="s.prepared", channel_key="s.prepared.c0")])
    result = calculations.calculate_fluorescence_sheet(sheet, parameters=parameters)
    assert _cell(result, "retained_event_count")["value"] == 3
    assert _cell(result, "parent_event_count")["state"] == "present"
    assert result["memberships"][0]["unknown"] == [0, 1, 2]
    assert _cell(result, "selected_event_count")["state"] == "qualified"
    assert _cell(result, "selected_intensity_count", gate="all")["value"] == 0
    assert _cell(result, "selected_intensity_missing_count", gate="all")["value"] == 3
    assert _cell(result, "selected_intensity_sum", gate="all")["value"] == 0
    assert _cell(result, "selected_intensity_mean", gate="all")["value"] is None


def _control_sheet(*, prepared_control=False):
    target = _batch([[900, 900], [1000, 800], [1100, 500], [1300, 501],
                     [1200, 800], [1500, 100]], sample="target")
    control = _batch([[900, 900], [1000, 800], [1100, 600], [1300, 501],
                      [1200, 800], [1500, 100]], sample="control")
    gates = []
    for sample in ("target", "control"):
        domain = "control.prepared" if sample == "control" and prepared_control else None
        gates.extend([
            _gate(sample + ".parent", sample=sample, domain=domain, lower=1000, upper=None, inclusive=False),
            _gate(sample + ".marker", sample=sample, domain=domain, channel=1,
                  parent=dict(kind="gate", key=sample + ".parent"),
                  lower=500, upper=None, inclusive=False),
        ])
    pair = dict(key="pair", target_gate_key="target.marker", control_gate_key="control.marker",
                denominator="parent", comparison_basis=_basis())
    batches = [target, control]
    if prepared_control:
        batches.append(_batch([[900, 900], [1000, 800], [1100, 600], [1300, 501],
                               [1200, 800], [1500, 100]], sample="control", domain="control.prepared",
                              correspondence=[dict(source_ordinal=i, event_ordinal=i) for i in range(6)]))
    return _sheet(batches, gates=gates, controls=[pair])


def test_packet548_signed_control_difference_and_optional_clipping_are_distinct():
    sheet = _control_sheet()
    parameters = _parameters(controls=[dict(control_key="pair", include_legacy_clipping=True)])
    result = calculations.calculate_fluorescence_sheet(sheet, parameters=parameters)
    assert _cell(result, "selected_fraction", gate="target.marker")["value"] == 2 / 4
    assert _cell(result, "selected_fraction", gate="control.marker")["value"] == 3 / 4
    for metric, expected in [("control_difference_fraction", -.25),
                             ("control_difference_percentage_points", -25),
                             ("legacy_nonnegative_difference_percentage_points", 0)]:
        cell = _cell(result, metric, gate=None, control="pair")
        assert cell["value"] == expected
        assert cell["state"] == "present"
        assert cell["population"]["denominator"] == "paired_controls"
        assert cell["population"]["sample_key"] is None
    requests = [cell["request"] for cell in result["cells"] if cell["request"]["kind"] == "fraction"]
    assert [(request["gate_key"], request["metric"]) for request in requests] == [
        ("target.marker", "selected_fraction"), ("target.marker", "selected_percent"),
        ("control.marker", "selected_fraction"), ("control.marker", "selected_percent")]
    parameters["control_requests"][0]["include_legacy_clipping"] = False
    parameters["fraction_requests"] = [dict(gate_key="control.marker", denominator="parent")]
    without_clipping = calculations.calculate_fluorescence_sheet(sheet, parameters=parameters)
    assert not any(cell["request"]["metric"].startswith("legacy") for cell in without_clipping["cells"])
    assert len([cell for cell in without_clipping["cells"] if cell["request"]["kind"] == "fraction"]) == 4
    assert len({canonical(cell["request"]) for cell in without_clipping["cells"]}) == len(without_clipping["cells"])


@pytest.mark.parametrize("fault", ["analyte", "missing_analyte", "unit", "missing_unit", "domain_basis",
                                   "primary_basis", "operator", "ancestor", "subset"])
def test_control_comparison_requires_documented_same_meaning_at_every_level(fault):
    sheet = _control_sheet(prepared_control=fault in {"domain_basis", "primary_basis"})
    marker_channel = sheet["channels"][3]
    if fault == "analyte":
        marker_channel["analyte"]["identifier"] = "different supplied analyte"
    elif fault == "missing_analyte":
        marker_channel["analyte"] = None
    elif fault == "unit":
        marker_channel["unit"] = "different_units"
    elif fault == "missing_unit":
        marker_channel["unit"] = None
    elif fault == "domain_basis":
        sheet["measurement_domains"][2]["comparison_basis"] = None
    elif fault == "primary_basis":
        sheet["measurement_domains"][1]["comparison_basis"] = None
    elif fault == "operator":
        sheet["gate_definitions"][3]["lower"]["inclusive"] = True
    elif fault == "ancestor":
        sheet["gate_definitions"][2].update(kind="pass_all", domain_key=None, channel_key=None,
                                             lower=None, upper=None)
    else:
        sheet["population_definitions"][1].update(kind="subset", event_ordinals=list(range(6)))
    parameters = _parameters(controls=[dict(control_key="pair", include_legacy_clipping=False)])
    result = calculations.calculate_fluorescence_sheet(sheet, parameters=parameters)
    difference = _cell(result, "control_difference_fraction", gate=None, control="pair")
    assert difference["value"] is None
    assert any(problem["code"] == "control_pair_incompatible" for problem in difference["issues"])
    assert _cell(result, "selected_fraction", gate="target.marker")["value"] == .5
    assert _cell(result, "selected_fraction", gate="control.marker")["value"] is not None


def test_control_fraction_missing_value_uses_same_explicit_denominator_rules():
    sheet = _control_sheet()
    sheet["events"][3]["values"][1]["measurement"].update(value=None, state="missing", raw=None)
    parameters = _parameters(controls=[dict(control_key="pair", include_legacy_clipping=False)])
    full = calculations.calculate_fluorescence_sheet(sheet, parameters=parameters)
    assert _cell(full, "control_difference_fraction", gate=None, control="pair")["value"] is None
    sheet["control_pairs"][0]["denominator"] = "evaluable"
    subset = calculations.calculate_fluorescence_sheet(sheet, parameters=parameters)
    assert _cell(subset, "selected_fraction", gate="target.marker")["value"] == 1 / 3
    difference = _cell(subset, "control_difference_fraction", gate=None, control="pair")
    assert difference["value"] == 1 / 3 - 3 / 4
    assert difference["state"] == "qualified"


def test_missing_invalid_selected_intensities_preserve_finite_subset_and_actual_zero():
    batch = _batch([[150, 0], [150, None], [150, 4], [150, None]])
    batch["events"][3]["values"][1]["measurement"].update(state="invalid", raw="not numeric")
    sheet = _sheet([batch])
    parameters = _parameters(intensities=[dict(gate_key="g", domain_key="s.raw", channel_key="s.raw.c1")])
    result = calculations.calculate_fluorescence_sheet(sheet, parameters=parameters)
    for metric, value in [("selected_intensity_count", 2), ("selected_intensity_missing_count", 2),
                          ("selected_intensity_sum", 4), ("selected_intensity_mean", 2),
                          ("selected_intensity_median", 2)]:
        cell = _cell(result, metric)
        assert cell["value"] == value and cell["state"] == "qualified"
        assert cell["population"]["extent"] == "confirmed_subset"
    assert any(problem["code"] == "invalid_numeric_token" and problem["event_ordinal"] == 3
               for problem in result["issues"])


@pytest.mark.parametrize("values,total,mean,median", [
    ([1e308, 1e308], None, 1e308, 1e308),
    ([1e308, -1e308], 0, 0, 0),
    ([10 ** 400], None, None, 10 ** 400),
    ([5e-324, 5e-324], 1e-323, 5e-324, 5e-324),
])
def test_intensity_overflow_does_not_suppress_representable_mean(values, total, mean, median):
    sheet = _sheet([_batch([[value] for value in values])], gates=[_gate(kind="pass_all")])
    result = calculations.calculate_fluorescence_sheet(sheet, parameters=_standard_parameters())
    assert _cell(result, "selected_intensity_sum")["value"] == total
    assert _cell(result, "selected_intensity_mean")["value"] == mean
    assert _cell(result, "selected_intensity_median")["value"] == median
    if total is None:
        assert any(problem["code"] == "derived_numeric_overflow" for problem in result["issues"])
        if mean is not None:
            assert _cell(result, "selected_intensity_mean")["state"] == "qualified"
    canonical(result)  # All emitted numbers have JSON-finite representation.


def _native_report(key, value, *, component=None, unit="percent", decimal_places=2):
    raw = None if value is None else str(value)
    return dict(key=key, file=_file((raw or "missing").encode()), source_key="s.raw.source",
                location=_location(0), label="synthetic rounded report", value=value,
                raw=raw, unit=unit, component_request=component, decimal_places=decimal_places)


def test_native_comparison_copies_actual_report_and_exact_difference_without_rounding_tolerance():
    link = _request("fraction", "selected_percent", gate_key="g", denominator="parent")
    reports = [_native_report("rounded", 33.33, component=link),
               _native_report("unlinked", 0, component=None),
               _native_report("unknown_unit", 33.33, component=link, unit=None),
               _native_report("wrong_unit", 33.33, component=link, unit="dimensionless"),
               _native_report("missing", None, component=link)]
    sheet = _sheet([_batch([[150], [0], [0]])], reports=reports)
    parameters = _parameters(fractions=[dict(gate_key="g", denominator="parent")],
                             native=[report["key"] for report in reports])
    result = calculations.calculate_fluorescence_sheet(sheet, parameters=parameters)
    assert _cell(result, "native_value", gate=None, report="rounded")["value"] == 33.33
    delta = _cell(result, "native_minus_calculated", gate=None, report="rounded")
    assert delta["value"] == 33.33 - (100 * (1 / 3)) and delta["value"] != 0
    assert delta["issues"] == []
    assert _cell(result, "native_value", gate=None, report="unlinked")["value"] == 0
    assert _cell(result, "native_value", gate=None, report="unknown_unit")["value"] == 33.33
    for key in ("unlinked", "unknown_unit", "wrong_unit", "missing"):
        assert _cell(result, "native_minus_calculated", gate=None, report=key)["value"] is None
    assert sheet["native_reports"][0]["decimal_places"] == 2


def test_native_link_does_not_commission_an_unrequested_calculation():
    link = _request("intensity", "selected_intensity_mean", gate_key="g",
                    domain_key="s.raw", channel_key="s.raw.c0")
    sheet = _sheet([_batch([[150]])], reports=[_native_report("r", 150, component=link, unit="instrument_units")])
    result = calculations.calculate_fluorescence_sheet(sheet, parameters=_parameters(native=["r"]))
    assert not any(cell["request"]["kind"] == "intensity" for cell in result["cells"])
    assert _cell(result, "native_value", gate=None, report="r")["value"] == 150
    assert _cell(result, "native_minus_calculated", gate=None, report="r")["value"] is None


def test_saved_only_recalculation_forbids_files_network_subprocess_and_llm(monkeypatch):
    sheet = _sheet([_batch([[90], [100], [125], [150], [200], [250], [300], [350]])])
    sheet["events"][0]["values"][0]["measurement"]["raw"] = " 090.00 "
    saved = json.loads(canonical(sheet))
    original_bytes = canonical(saved)
    parameters = _standard_parameters()
    parameter_bytes = canonical(parameters)
    real_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name.split(".")[0] in {"os", "pathlib", "socket", "subprocess", "urllib", "requests", "openai", "anthropic"}:
            raise AssertionError("External work during saved calculation: " + name)
        return real_import(name, *args, **kwargs)

    def forbidden(*args, **kwargs):
        raise AssertionError("File access during saved calculation")

    with monkeypatch.context() as context:
        context.setattr(builtins, "__import__", guarded_import)
        context.setattr(builtins, "open", forbidden)
        result = calculations.calculate_fluorescence_sheet(saved, parameters=parameters)
        changed = deepcopy(saved)
        changed["gate_definitions"][0]["lower"]["value"] = 150
        recalculated = calculations.calculate_fluorescence_sheet(changed, parameters=parameters)
    assert _cell(result, "selected_fraction")["value"] == .625
    assert _cell(recalculated, "selected_fraction")["value"] == 3 / 8
    assert result["sheet_sha256"] != recalculated["sheet_sha256"]
    assert canonical(saved) == original_bytes and canonical(parameters) == parameter_bytes
    assert saved["events"][0]["values"][0]["measurement"]["raw"] == " 090.00 "
    assert saved["events"][0]["values"][0]["measurement"]["state"] == "supplied_predicted"


def test_projection_copies_exact_saved_cells_and_never_calls_calculator(monkeypatch):
    sheet = _sheet([_batch([[100], [125], [300]])])
    result = calculations.calculate_fluorescence_sheet(sheet, parameters=_standard_parameters())
    # Standalone shape validation cannot authenticate an artifact's numeric
    # truth. The view must copy this saved value, even when it differs from a
    # recomputation; the future result binding owns artifact authentication.
    _cell(result, "selected_intensity_mean")["value"] = 163.125
    saved_bytes = canonical(result)
    selected = [_cell(result, "selected_percent"), _cell(result, "selected_intensity_mean"),
                _cell(result, "selected_event_count")]
    selection = dict(requests=[deepcopy(cell["request"]) for cell in selected], offset=1, limit=1)

    def forbidden(*args, **kwargs):
        raise AssertionError("Calculator called during saved projection")

    monkeypatch.setattr(calculations, "calculate_fluorescence_sheet", forbidden)
    monkeypatch.setattr(calculations, "evaluate_gate_membership", forbidden)
    monkeypatch.setattr(calculations, "_Calculation", forbidden)
    view = views.project_fluorescence_result(sheet, result, selection=selection)
    assert len(view["rows"]) == 1
    assert canonical(view["rows"][0]) == canonical(selected[1])
    assert view["total_selected_rows"] == 3 and view["returned_row_count"] == 1
    assert view["has_more"] and view["status"] == "calculated"
    assert set(view) == {"schema", "selection", "rows", "total_selected_rows", "returned_row_count",
                         "has_more", "status", "issues"}
    view["rows"][0]["population"]["sample_key"] = "changed"
    view["selection"]["requests"][0]["metric"] = "changed"
    assert canonical(result) == saved_bytes
    assert selection["requests"][0]["metric"] == "selected_percent"
    tree = ast.parse(inspect.getsource(views))
    imports = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    assert all("calculation" not in name for name in imports)


def test_projection_scopes_status_and_issues_to_selected_requests_before_pagination():
    sheet = _sheet([_batch([[150]]), _batch([], sample="other", extent="unavailable")],
                   gates=[_gate(), _gate("other.g", sample="other")])
    result = calculations.calculate_fluorescence_sheet(sheet, parameters=_standard_parameters())
    assert result["status"] == "partial" and result["issues"]
    good = _cell(result, "selected_fraction")["request"]
    bad = _cell(result, "selected_event_count", gate="other.g")["request"]
    good_view = views.project_fluorescence_result(sheet, result,
                                                 selection=dict(requests=[good], offset=99, limit=1))
    assert good_view["rows"] == [] and good_view["status"] == "calculated" and good_view["issues"] == []
    mixed = views.project_fluorescence_result(sheet, result,
                                             selection=dict(requests=[good, bad], offset=0, limit=1))
    assert mixed["rows"][0]["state"] == "present" and mixed["status"] == "partial"
    assert mixed["issues"] == _cell(result, "selected_event_count", gate="other.g")["issues"]
    missing = views.project_fluorescence_result(sheet, result,
                                               selection=dict(requests=[bad], offset=99, limit=1))
    assert missing["status"] == "unavailable"
    empty = views.project_fluorescence_result(sheet, result,
                                             selection=dict(requests=[], offset=0, limit=1))
    assert empty["status"] == "calculated" and not empty["issues"]


@pytest.mark.parametrize("fault,code", [("sheet", "invalid_components"), ("parameters", "invalid_components"),
                                        ("operand", "invalid_components"), ("duplicate_cell", "invalid_components"),
                                        ("duplicate_request", "invalid_selection"), ("uncomputed", "invalid_selection"),
                                        ("unknown_field", "invalid_selection"), ("unit", "invalid_components")])
def test_projection_rejects_wrong_saved_contracts(fault, code):
    sheet = _sheet([_batch([[150]])])
    result = calculations.calculate_fluorescence_sheet(sheet, parameters=_standard_parameters())
    selection = dict(requests=[deepcopy(_cell(result, "selected_fraction")["request"])], offset=0, limit=1)
    if fault == "sheet":
        sheet["samples"][0]["label"] = "new saved input"
    elif fault == "parameters":
        result["parameters"]["fraction_requests"] = []
    elif fault == "operand":
        result["cells"][0]["operands"] = ["sheet:/events/9999999/values/0"]
    elif fault == "duplicate_cell":
        result["cells"].append(deepcopy(result["cells"][0]))
    elif fault == "duplicate_request":
        selection["requests"].append(deepcopy(selection["requests"][0]))
    elif fault == "uncomputed":
        selection["requests"][0]["denominator"] = "evaluable"
    elif fault == "unknown_field":
        selection["extra"] = True
    else:
        result["cells"][0]["unit"] = "percent"
    with pytest.raises(FluorescenceContractError) as error:
        views.project_fluorescence_result(sheet, result, selection=selection)
    assert error.value.code == code


def test_conflicting_duplicate_control_request_flags_reject():
    parameters = _parameters(controls=[dict(control_key="pair", include_legacy_clipping=True),
                                       dict(control_key="pair", include_legacy_clipping=False)])
    with pytest.raises(FluorescenceContractError) as error:
        calculations.calculate_fluorescence_sheet(_control_sheet(), parameters=parameters)
    assert error.value.code == "invalid_parameters"
