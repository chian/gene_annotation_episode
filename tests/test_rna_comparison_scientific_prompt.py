"""Published scientific text delivery from selected RNA returns; no live model/RNA run."""
import asyncio
import builtins
from copy import deepcopy
import importlib
import importlib.util
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.decision_context import state_frame
from gene_annotation_episode.rna_structure_comparison_presentation import render_rna_comparison_projections
from gene_annotation_episode.rna_structure_comparison_views import PROJECTION_SOURCE
import gene_annotation_episode.scientific_process_prompt as prompt
from test_scientific_process_prompt_delivery import (
    ScientificWire, INSTRUCTION_TEXT, OUTPUT_SCHEMA, complete, snapshot,
)
from test_rna_comparison_presentation import pair, scan, receipt, results_context


PACKET = Path(__file__).resolve().parents[1] / "verification/tool_graders_rna_scientific_text_integration_2026-10-27_379"
BASELINE_SPEC = importlib.util.spec_from_file_location(
    "gene_annotation_episode._scientific_prompt_baseline_379", PACKET / "baseline_scientific_process_prompt.py")
baseline = importlib.util.module_from_spec(BASELINE_SPEC)
BASELINE_SPEC.loader.exec_module(baseline)


def scientific_state(rows=()):
    """Synthetic assignment; the existing full TASK, including all slots, is supplied."""
    state = snapshot()
    state["goal"]["objective"] = "Determine what functional annotation the supplied RNA segment supports."
    state["goal"]["task_context"] = {"assignment": "Use the supplied segment and qualified received results."}
    state["scientific_process"]["assignment"]["context"] = {"snippet": "GGGAAACCC", "complete": True}
    state["working_state"]["subjects"][0].update(molecule="RNA", length=9, unit="nt")
    state["working_state"]["materials"][0]["name"] = "selected.fna"
    state["scope"]["segments"][0].update(start=0, end=9)
    state["received_rna_comparison_values"] = [{"fact_source": PROJECTION_SOURCE, "facts": deepcopy(list(rows))}]
    state["child_reports"] = [
        {"energetic_answer_or_other_parent_name": deepcopy(list(rows)), "result_state": "qualified",
            "mixed": [*deepcopy(list(rows)), {"measured_value": -0.125, "unit": "fraction"}]},
        {"another_chosen_field": deepcopy(list(rows)), "completed": True},
    ]
    state["current_report_update"] = {"conclusion": "unresolved", "qualification": "Further functional evidence is required."}
    state["action_yields"]["rows"].append({"category": "child/results", "completed_actions": 1,
        "total_yield": 0, "attempted_uncompleted": 0, "expected_yield": {"status": "unavailable",
            "unavailable_reason": "insufficient completed actions", "band": None}})
    return state


def steering(text):
    return text.split("\n\nSTEERING\n", 1)[1]


def assert_full_task(text, state, *, framed=True):
    # Frames reconstruct canonical JSON order before presentation. Compare the
    # original TASK with that exact provider input, not fixture insertion order.
    task_state = json.loads(json.dumps(state, sort_keys=True)) if framed else state
    assert text.split("\n\nSTEERING\n", 1)[0] == baseline._task(task_state, INSTRUCTION_TEXT)
    for value in (state["scientific_process"]["evidence_axis"]["investigation_instructions"],
            state["scientific_process"]["thought_pattern"]["description"],
            state["scientific_process"]["child_tool_info"][0]["instructions"]):
        assert value in text


def assert_comparison_keys_absent(text, rows):
    for name in ("result_receipt_key", "calculation_key", "input_paths", "selected_input_digests",
            "rna_comparison_projection_v1"):
        assert name not in text
    for row in rows:
        assert row["result_receipt_key"] not in text
        assert row["calculation_key"] not in text


@pytest.mark.parametrize("family_index", range(8))
def test_actual_scientific_turn_delivers_each_selected_family_once(tmp_path, pair, scan, family_index):
    row = (pair + scan)[family_index]
    state = scientific_state([row])
    frame = state_frame(state)
    original = deepcopy((state, frame))
    wire = ScientificWire(tmp_path / "wire")
    asyncio.run(complete(wire, frame))
    turn = wire.turns_sent()[0]
    text = turn["input"][0]["text"]
    assert_full_task(text, state)
    supplied_text = render_rna_comparison_projections([row])
    assert text.count(supplied_text) == 1
    assert steering(text).count("Requested RNA ") == 1
    assert_comparison_keys_absent(steering(text), [row])
    assert "| [0].result_state | qualified |" in text
    assert "| [0].mixed[0].measured_value | -0.125 |" in text
    assert "| [1].completed | true |" in text
    assert "| child/results | 1 | 0 | unavailable | insufficient completed actions | 0 |" in text
    assert "| tool/source.read | 2 | -0.25 | unavailable | parameters_unbound | 1 |" in text
    assert "Further functional evidence is required." in text
    assert turn["outputSchema"] == OUTPUT_SCHEMA
    assert (state, frame) == original
    saved = json.loads((tmp_path / "wire/call-00001/request.json").read_text())
    assert saved["context"] == frame and saved["instructions"] == INSTRUCTION_TEXT
    assert saved["input"] == turn["input"]
    assert wire.scientific_prompt_states[("episode", "REASONING")] == state
    if row["family"] != "structures":
        assert "(((...)))" not in steering(text) and "GGGAAAUCC" not in steering(text)
    if row["family"] == "energy_comparison":
        assert "energy delta | -1.0 | kcal/mol" in text and "variant lower" in text
    if row["family"] == "structures":
        assert "| WT | Dot-bracket | (((...))) |" in text
        assert "| V | Dot-bracket | ((.....)) |" in text
        assert "| V | Original sequence | GGGAAAUCC |" in text
    if row["family"] == "position_changes":
        assert "| C | 6 | U | 6 | 6 | mapped; local index 2" in text
        assert "| unpaired | lost pairing | 1" in text
    if row["family"] == "scan_energy":
        assert "baseline rank start | 2" in text and "baseline rank end | 3" in text
        assert "| rank population count | 4 |" in text
        assert "Selected member" not in text and "native minimum free energy" not in text
    (tmp_path / (row["family"] + "_ACTUAL_TURN.txt")).write_text(text + "\n")


def test_full_task_recurs_across_update_lookup_and_fresh_restoration(tmp_path, pair):
    first = scientific_state()
    second = scientific_state([pair[0]])
    second["feedback"] = {"code": "selected_structure_not_requested"}
    first_frame, update = state_frame(first), state_frame(second, first)
    assert "scientific_process" not in update["fields"] and "goal" not in update["fields"]
    lookup_result = {"status": "completed", "result": [deepcopy(pair[1])]}
    lookup = {"version": "decision_context_v1", "kind": "decision_lookup_result",
        "decision_index": 8, "exchange_index": 1, "result": lookup_result}
    restored = state_frame(second)
    restored.update(restored_pending_decision_index=8, restored_public_exchanges=[{
        "exchange_index": 1, "response": {"private": "DO_NOT_RENDER_EXCHANGE_TRANSCRIPT"},
        "lookup_result": lookup_result}])
    original = deepcopy((first_frame, update, lookup, restored))
    wire, fresh = ScientificWire(tmp_path / "wire"), ScientificWire(tmp_path / "fresh")
    async def exercise():
        await complete(wire, first_frame)
        await complete(wire, update)
        await complete(wire, lookup)
        await complete(fresh, restored)
    asyncio.run(exercise())
    turns = wire.turns_sent() + fresh.turns_sent()
    assert len(turns) == 4
    for index, turn in enumerate(turns):
        text = turn["input"][0]["text"]
        assert_full_task(text, first if index == 0 else second)
        assert turn["outputSchema"] == OUTPUT_SCHEMA
        assert_comparison_keys_absent(steering(text), pair[:2])
        assert "DO_NOT_RENDER_EXCHANGE_TRANSCRIPT" not in text
        assert "base_revision" not in text and "removed_fields" not in text
    for turn in turns[1:]:
        assert steering(turn["input"][0]["text"]).count("Requested RNA energy comparison") == 1
        assert "selected_structure_not_requested" in turn["input"][0]["text"]
    for turn in turns[2:]:
        assert steering(turn["input"][0]["text"]).count("Requested RNA structures") == 1
        assert "(((...)))" in turn["input"][0]["text"]
    assert turns[2]["input"] == turns[3]["input"]
    assert (first_frame, update, lookup, restored) == original
    for connection in (wire, fresh):
        developer = next(p["developerInstructions"] for method, p in connection.sent if method == "thread/start")
        assert developer == prompt.text_instructions(INSTRUCTION_TEXT)
        assert "decision_bootstrap supplies" not in developer
    for connection_name, index, expected in (("wire", 1, first_frame), ("wire", 2, update),
            ("wire", 3, lookup), ("fresh", 1, restored)):
        saved = json.loads((tmp_path / connection_name / f"call-{index:05}/request.json").read_text())
        assert saved["context"] == expected
    (tmp_path / "RESTORED_ACTUAL_TURN.txt").write_text(turns[-1]["input"][0]["text"] + "\n")


@pytest.mark.parametrize("shape", ["projection", "list", "receipt"])
def test_exact_rna_lookup_shapes_reach_actual_turn_text(tmp_path, pair, shape):
    state = scientific_state()
    content = {"projection": pair[0], "list": [pair[0]], "receipt": receipt([pair[0]])}[shape]
    reply = {"status": "completed", "result": content}
    wire = ScientificWire(tmp_path / "wire")
    async def exercise():
        await complete(wire, state_frame(state))
        await complete(wire, {"version": "decision_context_v1", "kind": "decision_lookup_result", "result": reply})
    asyncio.run(exercise())
    text = wire.turns_sent()[-1]["input"][0]["text"]
    assert_full_task(text, state)
    assert steering(text).count("Requested RNA energy comparison") == 1
    assert "energy delta | -1.0 | kcal/mol" in text
    assert_comparison_keys_absent(steering(text), [pair[0]])
    if shape == "receipt":
        assert "| execution.results.collect | completed | true |" in text
        assert "secret" not in text and "/hidden/retained/sheet" not in text


@pytest.mark.parametrize("reply", [None, [1, 2], {"text": "Exact selected instruction."},
    {"view": "own_attempt_detail", "decision_index": 3, "values": [2], "has_more": False},
    {"view": "own_attempts", "records": [], "total": 0, "offset": 0, "returned_count": 0},
    {"status": "completed", "result": {"unrelated": 42}},
    {"outer": {"result": {"unrelated": 42}}}])
def test_unrecognized_lookup_shapes_keep_original_text(reply):
    assert prompt._lookup(reply) == baseline._lookup(reply)


def test_nested_rna_lookalikes_are_not_a_new_recursive_lookup_path(pair):
    for reply in ({"outer": {"result": [pair[0]]}}, {"view": "own_attempt_detail", "values": [pair[0]]}):
        assert prompt._lookup(reply) == baseline._lookup(reply)


@pytest.mark.parametrize("variant", ["ordinary", "empty_rna", "other_source", "infernal", "manual", "own_outcome"])
def test_non_rna_scientific_text_is_identical_to_pre379_renderer(variant):
    state = snapshot()
    if variant == "empty_rna":
        state["received_rna_comparison_values"] = [{"fact_source": PROJECTION_SOURCE, "facts": []}]
    elif variant == "other_source":
        state["received_rna_comparison_values"] = [{"fact_source": "other", "facts": [1]}]
    elif variant == "infernal":
        state["working_state"]["observations"].append({"id": "automatic", "native_infernal": {
            "version": "native_infernal_observation_v1"}, "value": "DO_NOT_EXPAND_NATIVE_SOURCE"})
        state["child_reports"] = [{"references": ["automatic"]}]
    elif variant == "manual":
        state["selected_launch_instructions"] = {"sections": [{"entry_id": "selected",
            "section_id": "usage", "text": "Preserve the full selected resource instructions."}]}
    elif variant == "own_outcome":
        state["last_local_outcome"] = {"status": "partial", "record_refs": ["observation_received"],
            "result": {"measured": 7, "missing": None}, "feedback": {"code": "partial_source"}}
        state["feedback"] = {"code": "partial_source"}
    original = deepcopy(state)
    lookups = [{"status": "completed", "result": {"text": "An unchanged ordinary lookup."}}]
    assert prompt.render_scientific_process_prompt(state, INSTRUCTION_TEXT, lookup_results=lookups) == (
        baseline.render_scientific_process_prompt(state, INSTRUCTION_TEXT, lookup_results=lookups))
    assert state == original


def test_task_uses_original_state_and_received_records_uses_filtered_detached_state(pair, monkeypatch):
    state = scientific_state([pair[0]])
    original, task_calls, record_calls = deepcopy(state), [], []
    real_task, real_records = prompt._task, prompt._received_records
    def capture_task(value, instructions):
        task_calls.append(value)
        return real_task(value, instructions)
    def capture_records(value):
        record_calls.append(value)
        return real_records(value)
    monkeypatch.setattr(prompt, "_task", capture_task)
    monkeypatch.setattr(prompt, "_received_records", capture_records)
    text = prompt.render_scientific_process_prompt(state, INSTRUCTION_TEXT)
    assert task_calls == [state] and task_calls[0] is state
    assert len(record_calls) == 1 and record_calls[0] is not state
    assert record_calls[0]["child_reports"] == [
        {"result_state": "qualified", "mixed": [{"measured_value": -0.125, "unit": "fraction"}]},
        {"completed": True}]
    assert record_calls[0]["current_report_update"] == original["current_report_update"]
    assert state == original and "UNREQUESTED_OBSERVATION" not in text


def test_current_report_update_is_not_reclassified_or_rewritten(pair):
    state = scientific_state([pair[0]])
    state["current_report_update"] = {"conclusion": "unresolved", "nested_supplied_interpretation": deepcopy(pair[0])}
    before = deepcopy(state)
    text = prompt.render_scientific_process_prompt(state, INSTRUCTION_TEXT)
    expected = "Current return interpretation\n\n" + baseline._values(state["current_report_update"])
    assert expected in text and state == before


def test_exact_equal_numbers_in_distinct_calculations_are_not_lost(pair):
    another = deepcopy(pair[0])
    another["calculation_key"] = "rna_comparison_calculation:" + "3" * 64
    state = scientific_state([pair[0], another])
    text = prompt.render_scientific_process_prompt(state, INSTRUCTION_TEXT)
    assert steering(text).count("Requested RNA energy comparison") == 2
    assert_comparison_keys_absent(steering(text), [pair[0], another])


def test_reusable_steering_accepts_no_scientific_task_and_keeps_status_meaning(pair):
    state = results_context([pair[0]], status=True)
    state["child_reports"] = [{"other": False}]
    state["action_yields"] = {"rows": [{"category": "tool/execution.results.status", "completed_actions": 1,
        "total_yield": 0, "expected_yield": {"band": None}}]}
    state["last_local_outcome"]["feedback"] = {"code": "retained_input_notice"}
    original = deepcopy(state)
    text = prompt.render_episode_steering(state)
    assert text.startswith("STEERING\n") and "TASK" not in text
    assert "| execution.results.status | completed | false |" in text
    assert text.count("Requested RNA energy comparison") == 1
    assert "retained_input_notice" in text and "| [0].other | false |" in text
    assert "secret" not in text and state == original


def test_scientific_renderer_has_no_hidden_io_store_native_calculator_or_model_work(pair, scan, monkeypatch):
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.providers import _SessionConnection
    modules = [importlib.import_module(name) for name in (
        "gene_annotation_episode.rna_structure_comparison_calculations",
        "gene_annotation_episode.rna_structure_comparison_publication",
        "gene_annotation_episode.rna_structure_native")]
    state = scientific_state(pair + scan)
    original = deepcopy(state)
    def forbidden(*args, **kwargs):
        raise AssertionError("The renderer must use already supplied selected facts only.")
    with monkeypatch.context() as patch:
        for owner, name in ((builtins, "open"), (Path, "open"), (Path, "read_text"), (Path, "read_bytes"),
                (socket, "create_connection"), (subprocess, "run"), (subprocess, "Popen"),
                (Store, "get"), (_SessionConnection, "complete")):
            patch.setattr(owner, name, forbidden)
        patch.setattr(modules[0], "calculate_rna_comparison_components", forbidden)
        patch.setattr(modules[1], "prepare_rna_comparison_grading", forbidden)
        for name, value in tuple(vars(modules[2]).items()):
            if callable(value) and getattr(value, "__module__", None) == modules[2].__name__:
                patch.setattr(modules[2], name, forbidden)
        text = prompt.render_scientific_process_prompt(state, INSTRUCTION_TEXT,
            lookup_results=[{"status": "completed", "result": [pair[0]]}])
    assert len(text) > 100 and state == original
    assert_full_task(text, state, framed=False)


def test_retained_shared_workflow_scan_values_reach_actual_scientific_turn(tmp_path):
    source = Path(__file__).resolve().parents[1] / (
        "verification/tool_graders_rna_comparison_shared_integration_2026-10-26_372/FILLED_ACTUAL_SCAN_001.json")
    retained = json.loads(source.read_text())
    case = retained["workflow_case"]
    rows = case["returned"]["comparison"]
    assert rows == case["body"]["projection_rows"]
    state = scientific_state(rows)
    state["child_reports"] = [deepcopy(case["returned"])]
    wire = ScientificWire(tmp_path / "wire")
    asyncio.run(complete(wire, state_frame(state)))
    text = wire.turns_sent()[0]["input"][0]["text"]
    assert_full_task(text, state)
    assert steering(text).count("Requested RNA scan energy") == 1
    assert "baseline rank start | 2" in text and "baseline rank end | 3" in text
    assert "baseline energy above minimum | 1.0 | kcal/mol" in text
    assert "| rank population count | 4 |" in text
    for label in ("received failure variant count", "not supplied variant count", "not tested variant count"):
        assert "| " + label + " | 1 |" in text
    assert "| [0].completed | true |" in text
    assert "Dot-bracket" not in steering(text) and "Selected member" not in text
    assert_comparison_keys_absent(steering(text), rows)
    (tmp_path / "RETAINED_WORKFLOW_SCAN_ACTUAL_TURN.txt").write_text(text + "\n")
    (tmp_path / "RETAINED_WORKFLOW_SCAN_PROVENANCE.json").write_text(json.dumps({
        "source": str(source), "fixture_provenance": retained["fixture_provenance"],
        "selected_rows": rows, "new_scientific_execution": False}, indent=2) + "\n")
