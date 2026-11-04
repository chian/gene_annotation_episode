"""Original RNA text from explicit synthetic rows and unchanged retained returns.

No fixture computes a scientific value to make a renderer assertion pass.
Retained 360 returns were produced earlier; these tests run no native RNA work.
"""
from copy import deepcopy
import builtins
import html
import importlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.rna_structure_presentation import (
    has_rna_structure_receiver_context, is_rna_structure_results_context,
    render_rna_structure_groups, render_rna_structure_lookup,
    render_rna_structure_own_outcome, render_rna_structure_own_progress,
    rna_structure_return_schema_view, select_rna_structure_presentation,
)
from gene_annotation_episode.rna_structure_result_views import (
    FAMILY_SOURCES, REFERENCE_SOURCE, SAVED_SOURCE, rna_structure_fact_sources,
)

ROOT = Path(__file__).resolve().parents[1]
RETAINED = ROOT / "verification/tool_graders_rna_structure_integration_2026-10-26_360/NUMERICAL_EXAMPLES.json"
PARAMETERS = {"schema": "rna_calculation_parameters_v1",
    "topology": {"long_stem_min_pairs": 3, "include_exterior_in_loop_size_statistics": False},
    "pair_composition": {"accepted_ordered_pair_types": ["AU", "UA", "GC", "CG", "GU", "UG"],
        "denominator": "unambiguous_pairs"}, "energy": {"normalization": "per_nt"}}
ORIGIN = {"content_location": "retained_complete_producer_bundle",
    "attempt_output_version": "original_producer_manifest_and_verified_file_digests",
    "window_consistency": "complete_files_matched_to_original_manifest",
    "completion_basis": "requested_acquisition_and_observed_successful_attempt"}
OPERATIONS = {"mfe_prediction": "predict_rna_secondary_structure",
    "supplied_features": "analyze_rna_secondary_structure_features"}


def cell(name, value, unit, *, numerator=None, denominator=None, origin="derived_topology"):
    return dict(name=name, value=value, unit=unit, numerator=numerator, denominator=denominator, origin=origin)


def unavailable(name, unit, state, reason, *, numerator=None, denominator=None, origin="derived_topology"):
    return dict(name=name, unit=unit, numerator=numerator, denominator=denominator, origin=origin,
        state=state, reason=reason)


def numeric(family="summary", *, measurements=None, missing=None, **changes):
    row = dict(family=family, record_key="synthetic-rna", row_key="synthetic-rna:summary",
        source_ref="source_synthetic", operation=OPERATIONS["supplied_features"], mode="supplied_features",
        structure_key="synthetic-rna:structure", subject_ref=None, sequence_id="Synthetic RNA",
        structure_id="Supplied hairpin", structure_origin="supplied_unknown",
        coordinate_system="zero_based_sequence_indices_and_half_open_intervals", status="unbound",
        measurements=[cell("paired_fraction", 0.6666666666666666, "dimensionless", numerator=6, denominator=9)]
            if measurements is None else deepcopy(measurements),
        unavailable=[] if missing is None else deepcopy(missing), qualification_codes=[],
        calculation_key="rna_calculation:" + "1" * 64, calculation_parameters=deepcopy(PARAMETERS))
    row.update(changes)
    return row


def pair():
    return numeric("pair", row_key="synthetic-rna:pair:2:6", pair_key="pair:2:6", indices=[2, 6],
        symbol_i="G", symbol_j="C", ordered_pair="GC", measurements=[cell("pair_span_nt", 4, "nt")])


def stem():
    return numeric("stem", row_key="synthetic-rna:stem:0:8", stem_key="stem:0:8",
        pair_keys=["pair:0:8", "pair:1:7", "pair:2:6"], pair_indices=[[0, 8], [1, 7], [2, 6]],
        measurements=[cell("stem_length_pairs", 3, "pairs"), cell("stack_count", 2, "stacks")])


def region(kind="hairpin"):
    if kind == "exterior":
        local, closing, branches, intervals = "region:exterior", None, ["pair:0:8"], []
    elif kind == "hairpin":
        local, closing, branches, intervals = "region:2:6", "pair:2:6", [], [[3, 6]]
    else:
        local, closing = "region:0:20", "pair:0:20"
        branches = ["pair:3:7", "pair:11:15"] if kind == "multibranch" else ["pair:3:15"]
        intervals = [[1, 3], [16, 20]] if kind == "internal" else [[1, 3]] if kind == "bulge" else [[1, 3], [8, 11], [16, 20]]
    return numeric("region", row_key="synthetic-rna:" + local, region_key=local, region_kind=kind,
        closing_pair_key=closing, immediate_branch_pair_keys=branches, unpaired_intervals=intervals,
        measurements=[cell("loop_unpaired_nt", {"hairpin": 3, "exterior": 0, "bulge": 2,
            "internal": 6, "multibranch": 9}[kind], "nt")],
        missing=[unavailable("five_prime_unpaired_nt", "nt", "incompatible", "rna_region_side_not_defined")]
            if kind in {"hairpin", "exterior", "multibranch"} else [])


def issue(code="rna_native_failed", *, stage="native", field="/native_evaluation", index=None, role=None):
    return dict(stage=stage, code=code, record_key="synthetic-rna", field=field, index=index, artifact_role=role)


def failure():
    return dict(family="failure", record_key="synthetic-rna", row_key="synthetic-rna:failure:3",
        source_ref=None, operation=OPERATIONS["supplied_features"], mode="supplied_features",
        result_receipt_key="rna_result_receipt:" + "2" * 64, issue_ordinal=3,
        issue=issue("rna_output_truncated", stage="parse", field="/native_result", index=7, role="native_result"))


def saved():
    return dict(schema="rna_structure_saved_sheet_input_v1", result_receipt_key="rna_result_receipt:" + "2" * 64,
        handoff_ref="source_handoff", source_ref="source_synthetic", bundle_artifact_ref="artifact_bundle",
        sheet_artifact_ref="artifact_sheet", sheet_sha256="3" * 64, record_key="synthetic-rna",
        operation=OPERATIONS["supplied_features"], mode="supplied_features")


def group(family, facts):
    return dict(fact_source=FAMILY_SOURCES.get(family, family), facts=deepcopy(facts))


def receiver(groups):
    return dict(goal={"objective": "Annotate the supplied RNA"}, received_rna_structure_values=deepcopy(groups))


def receipt(rows=(), *, route="complete_bound_bundle", operation="execution.results.collect",
            family="summary", issues=(), mode="supplied_features"):
    selector = {"version": "native_rna_structure_result_selector_v1" if route == "complete_bound_bundle"
        else "native_rna_structure_saved_sheet_selector_v1", "acquisition": route,
        "projection": {"family": family, "rows": {"offset": 0, "limit": 1},
            "metrics": [] if family == "failure" else ["paired_fraction"]}}
    if route == "retained_sheet_only":
        selector.update(saved_input=saved(), parameters=deepcopy(PARAMETERS))
    return dict(version="native_rna_structure_acquired_result_v1", run_id="private-run", episode_id="private-child",
        scope={}, assignment=dict(version="execution_results_assignment_v1", handoff_ref="source_handoff", selector=selector),
        operation_key="private-operation", tool_name=operation, arguments={},
        target={"assignment": {"requested_job": {"native_rna_structure": {
            "mode": mode, "operation": OPERATIONS[mode], "record_key": "synthetic-rna"}}}},
        observation={"observed_at": "2026-10-26T14:02:03+00:00", "state": "completed", "returncode": 0,
            "failure_code": None, "result_available": True,
            "measurements": [{"measure": "systemd_service_wall_seconds", "seconds": 1.25}],
            "outputs": [{"role": "stdout", "available": True, "bytes": 0, "writer_closed": True},
                {"role": "requested_output:/private/producer/native-result.json", "available": False,
                    "bytes": None, "writer_closed": False}],
            "native": {"private": "native details"}, "logs": [{"path": "/private/log", "bytes_base64": "c2VjcmV0"}],
            "provenance_refs": ["private-observation-receipt"]},
        capture={"private": "capture manifest"}, prepared={"private": "prepared data"},
        source_ref="source_synthetic", record_refs=["source_synthetic"], rows=deepcopy(list(rows)),
        failures=deepcopy(list(issues)), failure_selection=None,
        native_success=route == "retained_sheet_only" or operation == "execution.results.collect",
        capture_complete=route == "retained_sheet_only" or operation == "execution.results.collect",
        delivery_complete=operation == "execution.results.collect")


def results(body, *, progress=None):
    return dict(execution_assignment=deepcopy(body["assignment"]),
        execution_progress={} if progress is None else deepcopy(progress),
        last_local_outcome=dict(status="completed", result=deepcopy(body), record_refs=["source_synthetic"],
            changed_record_refs=["source_synthetic"], feedback=None))


def read_operands(text):
    """Reconstruct the exact closed object from the copyable field/type table."""
    tables, current = [], None
    for line in text.splitlines():
        if line == "| Operand field | Type | Exact supplied value |":
            current = {}
            tables.append(current)
        elif current is not None and line.startswith("| ") and not line.startswith("| ---"):
            field, kind, literal = [html.unescape(part.strip()) for part in line[1:-1].split("|")]
            value = None if kind == "null" else int(literal) if kind == "integer" else literal
            if field.startswith("issue."):
                current.setdefault("issue", {})[field[len("issue."):]] = value
            else:
                current[field] = value
        elif line and not line.startswith("|"):
            current = None
    return tables


def test_exact_public_ports_and_context_capability_are_separate_from_facts():
    module = importlib.import_module("gene_annotation_episode.rna_structure_presentation")
    assert set(module.__all__) == {"is_rna_structure_results_context", "has_rna_structure_receiver_context",
        "select_rna_structure_presentation", "render_rna_structure_groups", "render_rna_structure_own_outcome",
        "render_rna_structure_own_progress", "render_rna_structure_lookup", "rna_structure_return_schema_view"}
    assert has_rna_structure_receiver_context(receiver([]))
    assert has_rna_structure_receiver_context(receiver([group("summary", [])]))
    for state in (None, {}, {"received_rna_structure_values": None},
            receiver([{"fact_source": "unrelated", "facts": []}]),
            receiver([{**group("summary", []), "extra": True}])):
        assert not has_rna_structure_receiver_context(state)
    for route in ("complete_bound_bundle", "retained_sheet_only"):
        assert is_rna_structure_results_context(results(receipt(route=route)))
    comparison = results(receipt())
    comparison["execution_assignment"]["selector"]["version"] = "native_rna_structure_comparison_selector_v1"
    assert not is_rna_structure_results_context(comparison)


def test_received_exact_deduplication_preserves_order_mixed_reports_and_state():
    first = numeric()
    other = numeric(measurements=[cell("paired_fraction", 0.5, "dimensionless", numerator=6, denominator=12)])
    other["calculation_parameters"]["topology"]["long_stem_min_pairs"] = 4
    state = receiver([group("summary", [first, first, other]), group("pair", [pair()]),
        group("summary", [first]), group(REFERENCE_SOURCE, ["source_synthetic", "source_synthetic"])])
    state["child_reports"] = [{"parent_name": [first, {"unrelated": 1}], "interpret": "uncertain"},
        {"other_parent_name": [first]}, {}, {"nested": {"keep": [first]}},
        {"unreceived": [numeric(measurements=[cell("pair_count", 3, "pairs")])]},
        {"references": ["source_synthetic", "source_other"]}]
    state["current_report_update"] = {"interpretation": "literal", "values": [first]}
    state["frame_sha256"] = "preserve-exactly"
    before = deepcopy(state)
    selected = select_rna_structure_presentation(state)
    assert set(selected) == {"context", "groups", "own_outcome", "own_progress"}
    assert state == before
    assert selected["groups"] == [group("summary", [first, other]), group("pair", [pair()]),
        group(REFERENCE_SOURCE, ["source_synthetic"])]
    assert selected["context"]["child_reports"] == [{"parent_name": [{"unrelated": 1}], "interpret": "uncertain"},
        {}, {"nested": {"keep": [first]}}, state["child_reports"][4], {"references": ["source_other"]}]
    assert selected["context"]["current_report_update"] == before["current_report_update"]
    assert selected["context"]["frame_sha256"] == before["frame_sha256"]
    text = render_rna_structure_groups(selected["groups"])
    assert text.count("Selected summary row: synthetic-rna:summary") == 2
    assert "Calculation parameters — set 1" in text and "Calculation parameters — set 2" in text
    assert "| paired_fraction | 0.5 | dimensionless | 6 | 12 |" in text


def test_same_row_different_stored_calculation_is_not_coalesced():
    first, other = numeric(), numeric()
    other["calculation_key"] = "rna_calculation:" + "9" * 64
    selected = select_rna_structure_presentation(receiver([group("summary", [first, other])]))
    text = render_rna_structure_groups(selected["groups"])
    assert len(selected["groups"][0]["facts"]) == 2
    assert text.count("Selected summary row:") == 2 and text.count("topology.long_stem_min_pairs") == 1
    assert first["calculation_key"] not in text and other["calculation_key"] not in text


@pytest.mark.parametrize("state,reason", [
    ("not_requested", "normalization_not_requested"),
    ("not_produced", "selected_algorithm_does_not_produce_uncertainty"),
    ("missing_input", "rna_native_result_missing"), ("invalid_input", "rna_unbalanced_structure"),
    ("incompatible", "rna_zero_length_denominator"), ("failed", "rna_native_failed"),
    ("truncated", "rna_output_truncated"),
])
def test_zero_and_all_unavailable_states_keep_known_operands(state, reason):
    row = numeric(measurements=[cell("pair_count", 0, "pairs")],
        missing=[unavailable("mfe_per_nt", "kcal/mol/nt", state, reason, numerator=-1.2,
            denominator=None, origin="native_prediction")], status="partial")
    text = render_rna_structure_groups([group("summary", [row])])
    assert "| pair_count | 0 | pairs | unavailable | present | none | derived_topology |" in text
    assert f"| mfe_per_nt | unavailable | kcal/mol/nt | -1.2 | {state} | {reason} | native_prediction |" in text
    assert "Numerator" in text and "Denominator" not in text
    assert "uncertainty estimate" not in text and "confidence" not in text


def test_unavailable_known_denominator_and_normalization_not_requested_are_retained():
    row = numeric(measurements=[], missing=[unavailable("evaluated_energy_per_nt", "kcal/mol/nt",
        "not_requested", "normalization_not_requested", denominator=9, origin="native_evaluation")], status="partial")
    row["calculation_parameters"]["energy"]["normalization"] = "none"
    text = render_rna_structure_groups([group("summary", [row])])
    assert "Numerator" not in text and "Denominator" in text
    assert "| evaluated_energy_per_nt | unavailable | kcal/mol/nt | 9 | not_requested | normalization_not_requested | native_evaluation |" in text
    assert "| energy.normalization | none |" in text


def test_selected_pair_symbols_endpoints_and_complete_stem_membership():
    text = render_rna_structure_groups([group("pair", [pair()]), group("stem", [stem()])])
    assert "| pair:2:6 | (2, 6) | G | C | GC |" in text
    assert "| pair_span_nt | 4 | nt | present | none | derived_topology |" in text
    for key, endpoints in (("pair:0:8", "(0, 8)"), ("pair:1:7", "(1, 7)"), ("pair:2:6", "(2, 6)")):
        assert f"| {key} | {endpoints} |" in text
    assert "| stem_length_pairs | 3 | pairs |" in text and "| stack_count | 2 | stacks |" in text
    assert "(((...)))" not in text and "GGGAAACCC" not in text


@pytest.mark.parametrize("kind", ["exterior", "hairpin", "bulge", "internal", "multibranch"])
def test_every_selected_region_kind_keeps_exact_boundaries_and_branches(kind):
    row = region(kind)
    text = render_rna_structure_groups([group("region", [row])])
    assert f"| {row['region_key']} | {kind} |" in text
    for start, end in row["unpaired_intervals"]:
        assert f"[{start}, {end})" in text
    for key in row["immediate_branch_pair_keys"]:
        assert key in text
    assert "intervals are half open" in text
    if row["unavailable"]:
        assert "incompatible | rna_region_side_not_defined |" in text
    if kind == "exterior":
        assert "| unavailable | pair:0:8 | empty |" in text


@pytest.mark.parametrize("status", ["unbound", "partial", "invalid", "bound"])
def test_row_status_and_supplied_origin_are_not_reinterpreted(status):
    row = numeric(status=status, subject_ref="subject_exact" if status == "bound" else None,
        qualification_codes=["rna_subject_binding_conflict"] if status == "partial" else [])
    text = render_rna_structure_groups([group("summary", [row])])
    assert "status: " + status in text and "structure_origin: supplied_unknown" in text
    assert "supplied_observation" not in text and "supplied_prediction" not in text
    if status == "partial":
        assert "Qualification codes: rna_subject_binding_conflict." in text


def test_full_saved_and_received_failure_operands_are_reconstructable():
    descriptor, failed = saved(), failure()
    descriptor["record_key"] = "Exact | record\nwith <br> text"
    text = render_rna_structure_groups([group(SAVED_SOURCE, [descriptor]), group("failure", [failed])])
    assert read_operands(text) == [descriptor, failed]
    assert descriptor["sheet_sha256"] in text and descriptor["result_receipt_key"] in text
    assert "issue.stage | string | parse" in text and "issue.index | integer | 7" in text
    assert "issue.artifact_role | string | native_result" in text
    assert "no numerical score" in text


def test_reference_only_groups_and_generic_grants_do_not_grow_facts_or_access():
    state = receiver([group(REFERENCE_SOURCE, ["source_exact"]), group(SAVED_SOURCE, [])])
    state["execution_progress"] = {"execution_result_refs": ["source_generic"]}
    selected = select_rna_structure_presentation(state)
    text = render_rna_structure_groups(selected["groups"])
    assert "| source_exact |" in text and "no numerical rows or auxiliary bytes supplied" in text
    assert "Selected summary row" not in text and "sheet_sha256" not in text
    assert selected["context"]["execution_progress"] == state["execution_progress"]
    assert render_rna_structure_lookup(["source_exact"]) is None


def test_empty_received_and_own_selections_do_not_imply_population_or_failure():
    selected = select_rna_structure_presentation(receiver([group("pair", [])]))
    text = render_rna_structure_groups(selected["groups"])
    assert "No selected rows supplied" in text and "full population size" in text
    body = receipt(family="pair")
    selected = select_rna_structure_presentation(results(body))
    assert selected["groups"] == [group("pair", [])] and selected["own_outcome"]["issues"] == []
    missing = issue("rna_requested_row_missing", stage="selection", field="/selector/projection/rows/record_keys/0", index=0)
    body["failures"] = [missing]
    selected = select_rna_structure_presentation(results(body))
    text = render_rna_structure_own_outcome(selected["own_outcome"])
    assert "rna_requested_row_missing" in text and "/selector/projection/rows/record_keys/0" in text
    assert not any(g["fact_source"] == FAMILY_SOURCES["failure"] for g in selected["groups"])


@pytest.mark.parametrize("route", ["complete_bound_bundle", "retained_sheet_only"])
@pytest.mark.parametrize("operation", ["execution.results.status", "execution.results.collect"])
def test_status_collect_and_original_observation_flags_remain_distinct(route, operation):
    body = receipt(route=route, operation=operation)
    state = results(body)
    state["last_local_outcome"].update(feedback={"repair": "retained bytes unavailable"}, unrelated=None)
    before = deepcopy(state)
    selected = select_rna_structure_presentation(state)
    own = selected["own_outcome"]
    assert state == before and set(own) == {"status", "operation", "acquisition", "mode", "native_success",
        "capture_complete", "delivery_complete", "observation_basis", "observation", "issues"}
    assert selected["context"]["last_local_outcome"] == {"feedback": {"repair": "retained bytes unavailable"}, "unrelated": None}
    assert own["observation"]["outputs"][1]["role"] == body["observation"]["outputs"][1]["role"]
    text = render_rna_structure_own_outcome(own)
    assert "2026-10-26T14:02:03+00:00" in text and "systemd_service_wall_seconds | 1.25" in text
    assert "requested output 2 (native-result.json) | false | unavailable | false" in text
    for private in ("/private/", "private-run", "private-child", "capture manifest", "prepared data", "c2VjcmV0"):
        assert private not in text
    if route == "retained_sheet_only":
        assert "Retained original observation; no fresh native observation." in text
        assert "retained original native success" in text and own["observation_basis"] == "retained_original_observation"
    elif operation == "execution.results.status":
        assert "native_success | false | not established by this status action" in text
        assert "capture_complete | false | not established by this status action" in text
        assert "failed native" not in text and not selected["groups"]


def test_own_progress_sources_are_filtered_and_completion_has_its_own_meaning():
    row = numeric()
    progress = {source: [] for source in [*FAMILY_SOURCES.values(), SAVED_SOURCE]}
    progress.update({FAMILY_SOURCES["summary"]: [row], REFERENCE_SOURCE: ["source_synthetic"],
        "execution_result_refs": ["source_synthetic"], "execution_completed": True,
        "execution_result_origin": ORIGIN, "execution_blast_hsps": [], "unrelated": "keep"})
    selected = select_rna_structure_presentation(results(receipt([row]), progress=progress))
    assert selected["groups"] == [group("summary", [row]), group(REFERENCE_SOURCE, ["source_synthetic"])]
    assert selected["context"]["execution_progress"] == {"execution_blast_hsps": [], "unrelated": "keep"}
    assert selected["own_progress"] == {"execution_completed": True, "execution_result_origin": ORIGIN}
    assert "Own requested RNA delivery complete" in render_rna_structure_own_progress(selected["own_progress"])
    assert "Recorded original acquisition basis" in render_rna_structure_own_progress(selected["own_progress"])
    initial = {source: [] for source in [*FAMILY_SOURCES.values(), REFERENCE_SOURCE, SAVED_SOURCE]}
    initial.update(execution_result_refs=[], execution_completed=False, execution_result_origin=None)
    state = results(receipt(operation="execution.results.status"), progress=initial)
    assert select_rna_structure_presentation(state)["groups"] == []


def test_failure_family_obeys_recorded_selection_and_never_constructs_received_operand():
    issues = [issue(), issue("rna_capture_unavailable", stage="capture", field="/capture", role="native_result"),
        issue("rna_requested_row_missing", stage="selection", field="/selector/projection/rows/record_keys/1", index=1)]
    body = receipt(family="failure", issues=issues)
    body["failure_selection"] = dict(version="rna_structure_failure_selection_v1", population_count=2,
        selected_ordinals=[1], supplemental_issue_ordinals=[2], requested_rows_accounted_for=True)
    selected = select_rna_structure_presentation(results(body))
    assert selected["own_outcome"]["issues"] == issues[1:] and selected["groups"] == []
    text = render_rna_structure_own_outcome(selected["own_outcome"])
    assert "rna_capture_unavailable" in text and "rna_requested_row_missing" in text
    assert "rna_native_failed" not in text and "result_receipt_key" not in text


@pytest.mark.parametrize("value", [lambda: pair(), lambda: [pair(), pair()],
    lambda: saved(), lambda: [saved()], lambda: failure(), lambda: group("pair", []),
    lambda: [group("pair", [pair()]), group(SAVED_SOURCE, [saved()])], lambda: receipt([numeric()])])
def test_exact_lookup_boundaries_and_one_level_envelopes(value):
    supplied = value()
    direct = render_rna_structure_lookup(supplied)
    assert direct and render_rna_structure_lookup({"result": supplied}) == direct
    assert render_rna_structure_lookup({"result": {"result": supplied}}) is None
    assert render_rna_structure_lookup({"nested": supplied}) is None


def test_unrelated_lookups_and_mixed_unlabelled_lists_remain_owned_by_other_renderers():
    for value in ({"view": "own_attempt_detail", "values": [pair()]}, [], ["source_synthetic"],
            [pair(), saved()], [pair(), {"other": True}], {"family": "summary", "value": 7},
            {"version": "rna_structure_comparison_result_receipt_v1", "projection_rows": []}):
        assert render_rna_structure_lookup(value) is None


@pytest.mark.parametrize("mutate", [lambda r: r.update(extra="reject"),
    lambda r: r["measurements"][0].update(value=float("nan")),
    lambda r: r["measurements"][0].update(value=float("inf")),
    lambda r: r["measurements"][0].update(value=True),
    lambda r: r["measurements"][0].update(unit="wrong"),
    lambda r: r.update(indices=[6, 2]),
    lambda r: r.update(ordered_pair="CG"),
])
def test_recognized_invalid_rows_fail_explicitly_instead_of_generic_dump(mutate):
    row = pair(); mutate(row)
    with pytest.raises(ValueError, match="rna_structure_fact_shape_invalid"):
        render_rna_structure_lookup(row)
    with pytest.raises(ValueError, match="rna_structure_fact_shape_invalid"):
        select_rna_structure_presentation(receiver([group("pair", [row])]))


def test_malformed_recognized_receipt_descriptor_or_group_is_an_explicit_error():
    body = receipt(); body.pop("capture_complete")
    descriptor = saved(); descriptor["sheet_sha256"] = "short"
    for value in (body, descriptor, {**group("pair", [pair()]), "extra": True}):
        with pytest.raises(ValueError, match="rna_structure_.*shape_invalid"):
            render_rna_structure_lookup(value)


def test_schema_view_preserves_arbitrary_names_and_every_other_constraint():
    descriptors = rna_structure_fact_sources()
    node = deepcopy(descriptors[FAMILY_SOURCES["summary"]]["report_schema"])
    node.update(description="Parent's exact meaning", minItems=0, maxItems=2, uniqueItems=True,
        title="Keep this title", deprecated=False)
    interpretation = {"type": "string", "enum": ["supports", "limits"], "description": "Parent judgment"}
    form = {"type": "object", "additionalProperties": False, "required": ["any.parent-name", "judgment"],
        "properties": {"any.parent-name": node, "judgment": interpretation,
            "looks_like_rna_summary": {"type": "array", "items": {"type": "number"}},
            "nested": {"type": "object", "properties": {"exact_source": node}},
            "near_source": {"type": "array", "x-source": FAMILY_SOURCES["summary"] + "_later", "items": node}},
        "allOf": [{"if": {"required": ["judgment"]}, "then": {"required": ["any.parent-name"]}}]}
    before = deepcopy(form)
    view = rna_structure_return_schema_view(form)
    assert form == before and view is not form
    compact = view["properties"]["any.parent-name"]
    assert "items" not in compact and "Parent's exact meaning; Automatically supplied" in compact["description"]
    for key in node.keys() - {"items", "description"}:
        assert compact[key] == node[key]
    for key in form.keys() - {"properties"}:
        assert view[key] == form[key]
    for key in form["properties"].keys() - {"any.parent-name"}:
        assert view["properties"][key] == form["properties"][key]


def test_all_seven_original_sources_have_distinct_compact_meanings():
    form = {"type": "object", "properties": {str(index): deepcopy(value["report_schema"])
        for index, value in enumerate(rna_structure_fact_sources().values())}}
    view = rna_structure_return_schema_view(form)
    descriptions = [node["description"] for node in view["properties"].values()]
    assert len(set(descriptions)) == 7 and all("Automatically supplied" in text for text in descriptions)
    assert all("items" not in node for node in view["properties"].values())


def test_non_rna_and_comparison_inputs_are_exact_presentation_noops():
    from gene_annotation_episode.rna_structure_comparison_presentation import select_rna_comparison_presentation
    from gene_annotation_episode.scientific_process_prompt import _steering, render_episode_steering
    from gene_annotation_episode.rna_structure_comparison_views import PROJECTION_SOURCE
    state = {"goal": {"objective": "Other task"}, "child_reports": [{"unrelated": [1, 2]}],
        "last_local_outcome": {"result": {"other": 3}}, "current_report_update": {"decision": "keep"}}
    before = deepcopy(state)
    selected = select_rna_structure_presentation(state)
    assert selected == dict(context=state, groups=[], own_outcome=None, own_progress=None)
    assert render_episode_steering(state) == _steering(state, ()) and state == before
    comparison_state = {"execution_assignment": {"version": "execution_results_assignment_v1",
        "selector": {"version": "native_rna_structure_comparison_selector_v1"}},
        "execution_progress": {PROJECTION_SOURCE: [], "execution_completed": False},
        "last_local_outcome": {"result": {"version": "rna_structure_comparison_result_receipt_v1",
            "tool_name": "execution.results.status", "projection_rows": [], "delivery_complete": False,
            "issues": [], "preparation_failure": None}}}
    assert select_rna_structure_presentation(comparison_state)["context"] == comparison_state
    assert select_rna_comparison_presentation(comparison_state) == select_rna_comparison_presentation(
        select_rna_structure_presentation(comparison_state)["context"])
    for form in ({"properties": {"x": {"type": "array", "x-source": PROJECTION_SOURCE,
            "items": {"type": "object"}}}}, {"properties": {"x": {"type": "string", "enum": ["a", "b"]}}}):
        assert rna_structure_return_schema_view(form) == form


def test_renderers_cannot_reach_io_parsing_calculation_capture_or_authority(monkeypatch):
    modules = {name: importlib.import_module("gene_annotation_episode." + name) for name in (
        "store", "rna_structure_native", "rna_structure_topology", "rna_structure_contracts",
        "rna_structure_calculations", "rna_structure_result_views", "native_rna_structure_acquisition",
        "native_rna_structure_result_publication", "native_rna_structure_returns", "native_rna_structure_results")}
    all_groups = [group("summary", [numeric()]), group("pair", [pair()]), group("stem", [stem()]),
        group("region", [region()]), group("failure", [failure()]), group(SAVED_SOURCE, [saved()]),
        group(REFERENCE_SOURCE, ["source_synthetic"])]
    state = results(receipt([numeric()]))
    state.update(receiver(all_groups))
    before = json.dumps(state, sort_keys=True)
    form = {"properties": {"selected": rna_structure_fact_sources()[SAVED_SOURCE]["report_schema"]}}
    def forbidden(*args, **kwargs):
        raise AssertionError("pure presentation reached forbidden evidence work")
    for owner, names in ((builtins, ("open",)), (Path, ("open", "read_text", "read_bytes")),
            (socket, ("create_connection", "socket")), (subprocess, ("run", "Popen")),
            (modules["store"].Store, ("get", "get_artifact")),
            (modules["rna_structure_native"], ("parse_rna_native_record", "populate_rna_prediction_sheet", "populate_rna_feature_sheet")),
            (modules["rna_structure_topology"], ("parse_rna_topology",)),
            (modules["rna_structure_contracts"], ("validate_rna_sheet", "validate_rna_components")),
            (modules["rna_structure_calculations"], ("calculate_rna_prediction_components", "calculate_rna_feature_components")),
            (modules["rna_structure_result_views"], ("validate_rna_sheet", "validate_rna_components", "project_rna_prepublication")),
            (modules["native_rna_structure_acquisition"], ("capture_local_rna_structure_bundle", "retained")),
            (modules["native_rna_structure_result_publication"], ("prepare_rna_structure_grading", "prepare_saved_rna_structure_grading",
                "publish_selected_rna_structure_rows", "authenticate_rna_results_commission")),
            (modules["native_rna_structure_returns"].NativeRNAStructureReturns,
                ("authenticate", "authenticate_received_saved_input", "resolve_saved_rna_input", "received_context")),
            (modules["native_rna_structure_results"].NativeRNAStructureResults, ("read_result", "read_receipt_key"))):
        for name in names:
            monkeypatch.setattr(owner, name, forbidden)
    selected = select_rna_structure_presentation(state)
    assert render_rna_structure_groups(selected["groups"])
    assert render_rna_structure_own_outcome(selected["own_outcome"])
    assert render_rna_structure_own_progress(dict(execution_completed=True, execution_result_origin=ORIGIN))
    assert render_rna_structure_lookup({"result": all_groups})
    assert render_rna_structure_lookup(state["last_local_outcome"])
    assert rna_structure_return_schema_view(form)
    assert json.dumps(state, sort_keys=True) == before


def test_actual_retained_prediction_evaluation_failure_and_recalculation_values(tmp_path):
    examples = json.loads(RETAINED.read_text())["examples"]
    retained_text = []
    for example in examples:
        sources = {name: node["x-source"] for name, node in example["requested_forms"]["results"]["properties"].items()
            if node.get("x-source") in rna_structure_fact_sources()}
        for result in example["results"]:
            supplied = result["requested_return"]
            groups = [group(source, supplied[name]) for name, source in sources.items()]
            state = receiver(groups)
            state["child_reports"] = [deepcopy(supplied)]
            before = deepcopy(state)
            selected = select_rna_structure_presentation(state)
            text = render_rna_structure_groups(selected["groups"])
            assert state == before
            assert read_operands(text) == [value for entry in selected["groups"]
                if entry["fact_source"] in (SAVED_SOURCE, FAMILY_SOURCES["failure"]) for value in entry["facts"]]
            assert "rna_calculation:" not in text and "GGGAAACCC" not in text
            retained_text.append(text)
    prediction = next(e for e in examples if e["mode"] == "mfe_prediction")["results"][0]
    prediction_text = render_rna_structure_groups([group("summary", prediction["requested_return"]["summary"])])
    assert "| mfe_kcal_mol | -1.2000000476837158 | kcal/mol | unavailable | unavailable | present | none | native_prediction |" in prediction_text
    evaluation = next(e for e in examples if any(c["name"] == "evaluated_energy_kcal_mol" for c in
        e["results"][0]["requested_return"]["summary"][0]["measurements"]))["results"][0]
    evaluation_text = render_rna_structure_groups([group("summary", evaluation["requested_return"]["summary"])])
    assert "| evaluated_energy_kcal_mol | -1.2000000476837158 | kcal/mol |" in evaluation_text
    assert "native_evaluation" in evaluation_text and "structure_origin: supplied_unknown" in evaluation_text
    failure_example = next(e for e in examples if e["results"][0]["requested_return"].get("failure"))["results"][0]
    failure_text = render_rna_structure_groups([group("summary", failure_example["requested_return"]["summary"])])
    assert "| pair_count | 1 | pairs |" in failure_text and "failed | rna_native_failed | native_evaluation" in failure_text
    recalc = next(e for e in examples if len(e["results"]) == 2)
    recalculated_text = render_rna_structure_groups([group("summary", [r["requested_return"]["summary"][0] for r in recalc["results"]])])
    assert "| long_stem_fraction | 1.0 | dimensionless | 1 | 1 |" in recalculated_text
    assert "| long_stem_fraction | 0.0 | dimensionless | 0 | 1 |" in recalculated_text
    assert "| accepted_pair_fraction | 0.0 | dimensionless | 0 | 3 |" in recalculated_text
    assert "| topology.long_stem_min_pairs | 4 |" in recalculated_text
    (tmp_path / "RETAINED_ORIGINAL_ROWS.txt").write_text("\n\n".join(retained_text) + "\n")
    (tmp_path / "RETAINED_RECALCULATION.txt").write_text(recalculated_text + "\n")
    (tmp_path / "RETAINED_OWN_OUTCOME.txt").write_text(render_rna_structure_lookup(prediction["original_result_receipt"]) + "\n")


def test_hand_checkable_selected_energy_pair_region_examples(tmp_path):
    # These explicitly labelled synthetic selections copy a retained native
    # energy value and hand-entered topology cells; no calculator is invoked.
    energy = numeric(measurements=[cell("mfe_kcal_mol", -1.2000000476837158, "kcal/mol", origin="native_prediction")],
        operation=OPERATIONS["mfe_prediction"], mode="mfe_prediction", structure_origin="native_prediction")
    examples = {"SYNTHETIC_SELECTED_ENERGY": [group("summary", [energy])],
        "SYNTHETIC_SELECTED_PAIR_REGION": [group("pair", [pair()]), group("region", [region()])],
        "SYNTHETIC_SELECTED_STEM": [group("stem", [stem()])]}
    for label, groups in examples.items():
        text = render_rna_structure_groups(groups)
        (tmp_path / (label + ".txt")).write_text(label + "\n\n" + text + "\n")
        (tmp_path / (label + ".json")).write_text(json.dumps(groups, indent=2) + "\n")
        assert "calculation_key" not in text
    assert "| mfe_kcal_mol | -1.2000000476837158 | kcal/mol | present | none | native_prediction |" in render_rna_structure_groups(examples["SYNTHETIC_SELECTED_ENERGY"])
    assert "[3, 6)" in render_rna_structure_groups(examples["SYNTHETIC_SELECTED_PAIR_REGION"])
