"""Own-attempt projections over real Store records and synthetic completions.

These tests perform no model, scientific, native-service or external work.
"""
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json

import pytest
from real_time_credit_fixture import progress_time
from jsonschema import Draft202012Validator
from method_loop import ClosedRecord
from method_loop.durable import canonical
from method_loop.identities import UnitRef

from gene_annotation_episode import decision_history as history
from gene_annotation_episode.episode_completion import CompletionLedger
from gene_annotation_episode.episode_journal import Journal, WorkflowError
from gene_annotation_episode.numerical import YieldController, YieldParameters, estimate_score_yield
from gene_annotation_episode.state import Store


@dataclass(frozen=True)
class Value(ClosedRecord):
    credit: float

    def as_record(self):
        return {"credit": self.credit}


@pytest.fixture
def saved(tmp_path):
    with Store(tmp_path / "workspace") as store:
        journal = Journal(store, "run_A")
        journal.save("runtime_episodes", {"episode_id": "owner", "path": canonical([["annotation", "root"]]),
            "request": canonical({"never_expose_prompt": "private request"}), "initial_credit": 100,
            "state": "active", "completion": None, "archive": None})
        yield store, journal


def attempt(journal, index, selection, *, status="completed", credit=100, episode="owner", refs=None,
            body=None, action=True, response=True):
    journal.save("runtime_model_calls", {"episode_id": episode, "call_index": index,
        "purpose": "decision", "request": canonical({"context": {"private_prompt": "never expose"}}),
        "response": canonical({"selection": selection, "report_update": {}}) if response else None})
    if action:
        journal.save("runtime_actions", {"episode_id": episode, "decision_index": index,
            "action": canonical(selection), "result": None if status is None else canonical({
                "status": status, "record_refs": refs or [], "result": body}),
            "credit": credit})


def observe(journal, index, sequence, gain, *, credit=100, slot=False, episode="owner", legacy=False,
            time_point=None):
    label = f"tool:{index}"
    if slot:
        ledger = CompletionLedger(journal.store, journal)
        saved_slot = ledger.stage(episode, index, label=label, kind="own_action",
            controller_input=Value(credit), child_return=None)
        assert saved_slot["sequence"] == sequence
    record = {"label": label, "credit": {"credit": credit},
        "step": {"marginal_credit": gain}, "unit_ref": UnitRef(episode, sequence).as_record(),
        "decision_index": index}
    if legacy:
        record.pop("unit_ref")
    journal.save("runtime_observations", {"episode_id": episode, "unit_index": sequence,
        "observation": canonical(record)})
    if time_point is not None:
        journal.save("runtime_estimation_contexts", {"episode_id": episode,
            "decision_index": index, "data": canonical({"progress_time": time_point})})


def query(**values):
    return {"view": "own_attempts", "category": None, "decision_indices": None,
            "offset": 0, "limit": 20, **values}


@pytest.mark.parametrize("selection,category", [
    ({"kind": "tool", "tool": "sequence.align"}, "tool/sequence.align"),
    ({"kind": "tool", "tool": "sequence.inspect"}, "tool/sequence.inspect"),
    ({"kind": "child"}, "child/improvement"),
    ({"kind": "child", "role": "improvement"}, "child/improvement"),
    ({"kind": "job_child", "role": "job_launch"}, "job_child/job_launch"),
    ({"kind": "episode_child", "role": "local_compute"}, "episode_child/local_compute"),
    ({"kind": "reason"}, "reason"), ({"kind": "wait"}, "wait"),
])
def test_categories_follow_actual_selection_discriminators(selection, category):
    assert history.category_for(selection) == category


def test_all_saved_gain_stays_on_reason_without_inherited_or_redistributed_credit(saved):
    store, journal = saved
    for index in range(8):
        selection = {"kind": "reason", "commit": {"inherited_evidence": ["source_A"]}} if index == 4 else {
            "kind": "tool", "tool": "source.read", "arguments": {"source": "source_A"}}
        attempt(journal, index, selection, credit=108 if index >= 4 else 100)
        observe(journal, index, index, 8 if index == 4 else 0, credit=108 if index >= 4 else 100)
    attempt(journal, 8, {"kind": "tool", "tool": "source.read"}, status="failed", credit=108)
    observe(journal, 8, 8, 0, credit=108)
    before = store.db.total_changes
    result = history.yield_table(journal, "owner", before=9)
    rows = {row["category"]: row for row in result["rows"]}
    assert rows["reason"]["completed_actions"] == 1
    assert rows["reason"]["total_yield"] == 8
    assert rows["tool/source.read"]["completed_actions"] == 8
    assert rows["tool/source.read"]["total_yield"] == 0
    assert rows["tool/source.read"]["attempted_uncompleted"] == 0
    assert all(row["expected_yield"]["unavailable_reason"] == "parameters_unbound" for row in rows.values())
    assert store.db.total_changes == before


def test_category_fit_uses_signed_completion_order_and_only_explicit_binding(saved, monkeypatch):
    _, journal = saved
    for index in (8, 2, 5):
        attempt(journal, index, {"kind": "tool", "tool": "same.operation"})
    for sequence, (index, gain) in enumerate(((8, 4), (2, -3), (5, 0))):
        observe(journal, index, sequence, gain, slot=True,
            time_point=progress_time(10. * (sequence + 1), run_id="run_A",
                episode_id="owner", decision_index=index))
    query_time = progress_time(100., run_id="run_A", episode_id="owner", query=True)
    monkeypatch.setattr(history, "capture_progress_time", lambda *_: query_time)
    calls, fitted = [], []
    original = history.estimate_score_yield

    def capture(scores, parameters, **operands):
        calls.append(tuple(scores))
        assert operands["evaluation_time"] == query_time
        assert [c["progress_time"]["original_decision_index"] for c in operands["contexts"]] == [8, 2, 5]
        result = original(scores, parameters, **operands)
        fitted.append(result.expected_next_gain.as_record())
        return result

    monkeypatch.setattr(history, "estimate_score_yield", capture)
    unbound = history.yield_table(journal, "owner", before=9)
    assert calls == [] and unbound["rows"][0]["total_yield"] == 1
    parameters = YieldParameters(2, 1)
    bound = history.yield_table(journal, "owner", before=9, parameters=parameters)
    assert calls == [(4, -3, 0)]
    row = bound["rows"][0]
    assert row["completed_actions"] == 3
    assert row["expected_yield"]["band"] == fitted[0]
    assert set(row["expected_yield"]) == {"status", "unavailable_reason", "band", "completed_occurrences"}
    binding = bound["expectation_model"]
    assert binding["version"] == "category_real_time_credit_mark_yield_v2"
    assert binding["conditional_on"] == "category_acquisition_at_recorded_query_time" and binding["scope"] == "table_only"
    assert binding["evaluation_time"] == query_time
    assert binding["controller_effect"] == "none" and binding["calibrated_confidence_interval"] is False
    assert "provenance" not in json.dumps(bound) and "diagnostics" not in json.dumps(bound)
    assert history.lookup_attempts(journal, "owner", before=9, query=query())["records"][0]["completion"] == {
        "observation_index": 1, "completion_sequence": 1, "unit_ref": UnitRef("owner", 1).as_record(),
        "kind": "own_action", "child_return": None}


def test_missing_time_and_unidentifiable_expectations_stay_unavailable(saved, monkeypatch):
    _, journal = saved
    attempt(journal, 0, {"kind": "reason"})
    observe(journal, 0, 0, 0)
    sparse = history.yield_table(journal, "owner", before=1, parameters=YieldParameters())
    assert sparse["rows"][0]["expected_yield"]["unavailable_reason"] == "progress_time_unavailable"
    assert sparse["rows"][0]["total_yield"] == 0
    from dataclasses import replace
    from gene_annotation_episode.numerical import NumericBand, STATUS_UNIDENTIFIABLE
    original = estimate_score_yield([], YieldParameters())
    monkeypatch.setattr(history, "estimate_score_yield", lambda *_, **__: replace(original,
        expected_next_gain=NumericBand.coded(STATUS_UNIDENTIFIABLE)))
    unavailable = history.yield_table(journal, "owner", before=1, parameters=YieldParameters())
    assert unavailable["rows"][0]["expected_yield"]["unavailable_reason"] == "unidentifiable"


def test_lookup_failure_is_null_and_separate_from_zero_negative_and_unobserved_completions(saved):
    _, journal = saved
    for index, status in enumerate(("failed", "completed", "partial", "completed")):
        attempt(journal, index, {"kind": "tool", "tool": "fixture.operation"}, status=status,
                credit=None if index == 0 else 100)
    observe(journal, 1, 0, 0, legacy=True)
    observe(journal, 2, 1, -2)
    records = history.lookup_attempts(journal, "owner", before=4, query=query())["records"]
    assert [row["status"] for row in records] == ["failed", "completed", "partial", "completed"]
    assert [row["completed_gain"] for row in records] == [None, 0, -2, None]
    assert records[1]["completion"]["completion_sequence"] is None
    assert records[1]["completion"]["unit_ref"] is None
    assert records[3]["completion"] is None


def test_lookup_is_own_prior_attempts_with_category_filter_and_deterministic_pages(saved):
    store, journal = saved
    for index in range(5):
        attempt(journal, index, {"kind": "reason"} if index % 2 else {"kind": "wait"})
    attempt(journal, 5, {"kind": "tool", "tool": "unfinished"}, action=False, response=False)
    attempt(journal, 0, {"kind": "tool", "tool": "child.private"}, episode="child")
    other = Journal(store, "other_run")
    attempt(other, 0, {"kind": "tool", "tool": "other.run"})
    before = store.db.total_changes
    page = history.lookup_attempts(journal, "owner", before=4, query=query(limit=2))
    assert page["total"] == 4 and page["next_offset"] == 2
    assert [row["decision_index"] for row in page["records"]] == [0, 1]
    page = history.lookup_attempts(journal, "owner", before=4, query=query(limit=2, offset=2))
    assert page["next_offset"] is None and [row["decision_index"] for row in page["records"]] == [2, 3]
    filtered = history.lookup_attempts(journal, "owner", before=5,
        query=query(category="wait", decision_indices=[4, 1, 0], limit=1, offset=1))
    assert filtered["total"] == 2 and filtered["records"][0]["decision_index"] == 4
    assert store.db.total_changes == before
    for index in (5, 99):
        with pytest.raises(ValueError, match="own_attempt_decision_unavailable"):
            history.lookup_attempts(journal, "owner", before=5, query=query(decision_indices=[index]))


@pytest.mark.parametrize("change", [
    {"episode_id": "child"}, {"run_id": "other_run"}, {"before": 999}, {"view": "prompts"},
    {"limit": 0}, {"offset": -1}, {"offset": True}, {"decision_indices": [0, 0]},
    {"decision_indices": [-1]}, {"decision_indices": [True]}, {"category": []},
])
def test_query_is_closed_and_rejects_other_owner_private_views_and_invalid_pages(saved, change):
    _, journal = saved
    value = query(**change)
    assert not Draft202012Validator(history.lookup_schema()).is_valid(value)
    with pytest.raises(ValueError, match="invalid_own_attempt_query"):
        history.lookup_attempts(journal, "owner", before=5, query=value)


def test_missing_required_query_operands_are_not_invented(saved):
    _, journal = saved
    for name in query():
        value = query()
        value.pop(name)
        with pytest.raises(ValueError, match="invalid_own_attempt_query"):
            history.lookup_attempts(journal, "owner", before=5, query=value)


def test_large_publications_and_outcome_prose_have_counts_hashes_and_explicit_detail_references(saved):
    store, journal = saved
    marker = "LARGE_OUTCOME_BODY_NOT_PRESENT_IN_LOOKUP"
    refs = [f"record_{index}" for index in range(150)]
    selection = {"kind": "tool", "tool": "source.read", "arguments": {"query": marker * 2000}}
    attempt(journal, 0, selection, refs=refs, body={"paragraph": marker * 3000})
    observe(journal, 0, 0, 0)
    raw_action = journal.row("runtime_actions", "owner", 0)
    before = store.db.total_changes
    record = history.lookup_attempts(journal, "owner", before=1, query=query())["records"][0]
    assert marker not in json.dumps(record)
    assert record["selection"] == {"kind": "tool", "tool": "source.read", "role": None}
    published = record["published_references"]
    assert published["values"] == refs[:history.REFERENCE_PREVIEW_SIZE]
    assert published["total"] == 150 and published["complete"] is False
    assert published["detail_reference"]["field"] == "result.record_refs"
    for field, raw in (("selection_summary", raw_action["action"]), ("outcome_summary", raw_action["result"])):
        assert record[field]["sha256"] == hashlib.sha256(raw.encode()).hexdigest()
        assert record[field]["bytes"] == len(raw.encode())
    assert record["selection_summary"]["detail_reference"]["lookup"] == {
        "view": "own_attempt_detail", "decision_index": 0, "pointer": "", "offset": 0,
        "limit": history.DETAIL_CONTAINER_PAGE}
    assert record["outcome_summary"]["detail_reference"]["field"] == "result"
    assert "episode.history" not in json.dumps(record)
    assert len(json.dumps(record)) < 8000
    assert store.db.total_changes == before and journal.row("runtime_actions", "owner", 0) == raw_action


def test_malformed_and_custom_controller_records_do_not_create_inferred_gain(saved):
    _, journal = saved
    attempt(journal, 0, "not_a_selection", action=False)
    attempt(journal, 1, {"kind": "reason"}, credit=108)
    observe(journal, 1, 0, 8)
    saved_observation = journal.row("runtime_observations", "owner", 0)
    record = json.loads(saved_observation["observation"])
    record["step"] = {"custom_delta": 8}
    journal.save("runtime_observations", {"episode_id": "owner", "unit_index": 0,
        "observation": canonical(record)})
    table = history.yield_table(journal, "owner", before=2, parameters=YieldParameters())
    assert table["uncategorized_attempts"] == 1
    assert table["rows"][0]["completed_actions"] == 1 and table["rows"][0]["total_yield"] is None
    assert table["rows"][0]["expected_yield"]["unavailable_reason"] == "saved_marginal_credit_unavailable"
    records = history.lookup_attempts(journal, "owner", before=2, query=query())["records"]
    assert records[0]["category"] is None and records[0]["status"] == "unexecuted"
    assert records[1]["completed_gain"] is None


def test_completion_identity_conflicts_fail_instead_of_reassigning_gain(saved):
    _, journal = saved
    attempt(journal, 0, {"kind": "tool", "tool": "fixture.operation"})
    attempt(journal, 1, {"kind": "reason"})
    observe(journal, 0, 0, 2, slot=True)
    value = json.loads(journal.row("runtime_observations", "owner", 0)["observation"])
    value["decision_index"] = 1
    journal.save("runtime_observations", {"episode_id": "owner", "unit_index": 0,
        "observation": canonical(value)})
    with pytest.raises(WorkflowError, match="decision_history_completion_identity_conflict"):
        history.yield_table(journal, "owner", before=2)


def test_standard_controller_signed_history_is_projected_without_mutating_saved_observations(saved):
    store, journal = saved
    controller = YieldController("fixture_epoch", 100, 0.001)
    for index, credit in enumerate((108, 108, 105, 106)):
        attempt(journal, index, {"kind": "reason"}, credit=credit)
        step = controller.observe(f"reason:{index}", Value(credit)).as_record()
        journal.save("runtime_observations", {"episode_id": "owner", "unit_index": index,
            "observation": canonical({"label": f"reason:{index}", "credit": {"credit": credit},
                "step": step, "unit_ref": UnitRef("owner", index).as_record(), "decision_index": index})})
    original = list(store.db.execute("SELECT observation FROM runtime_observations ORDER BY unit_index"))
    controller_state = deepcopy(controller.state().as_record())
    result = history.yield_table(journal, "owner", before=4, parameters=YieldParameters())
    assert result["rows"][0]["total_yield"] == 6
    assert [row["completed_gain"] for row in history.lookup_attempts(journal, "owner", before=4,
        query=query())["records"]] == [8, 0, -3, 1]
    assert controller.state().as_record() == controller_state
    assert [row[0] for row in store.db.execute("SELECT observation FROM runtime_observations ORDER BY unit_index")] == [row[0] for row in original]


def test_lookup_preserves_actual_search_queries_references_and_source_ranges(saved):
    _, journal = saved
    arguments = {"query": "ybhP structure activity metal binding", "source_ref": "source_1",
        "reference_refs": ["protein_A", "protein_B"], "start": 120, "end": 420,
        "unit": "characters", "selectors": {"table": 2, "column": "activity"}}
    attempt(journal, 0, {"kind": "tool", "tool": "literature.targeted_read", "arguments": arguments})
    record = history.lookup_attempts(journal, "owner", before=1, query=query())["records"][0]
    assert record["inputs"]["arguments"] == arguments
    assert record["input_fields"]["complete"] is True


def test_large_selected_string_detail_pages_reconstruct_exact_value_without_other_records(saved):
    store, journal = saved
    original = "query with \u03b1 and / ~ characters\n" * 400
    attempt(journal, 0, {"kind": "tool", "tool": "search", "arguments": {"query": original}},
            body={"text": "OUTCOME_NOT_A_SELECTED_INPUT"})
    attempt(journal, 0, {"kind": "tool", "tool": "private_child"}, episode="child")
    before = store.db.total_changes
    record = history.lookup_attempts(journal, "owner", before=1, query=query())["records"][0]
    summary = record["inputs"]["arguments"]["values"]["query"]
    assert summary["value_type"] == "string" and summary["total"] == len(original)
    detail_query = summary["detail_query"]
    parts = []
    while detail_query is not None:
        assert Draft202012Validator(history.lookup_schema()).is_valid(detail_query)
        detail = history.lookup_attempts(journal, "owner", before=1, query=detail_query)
        assert detail["view"] == "own_attempt_detail" and detail["slice_unit"] == "unicode_codepoints"
        assert "private_child" not in json.dumps(detail)
        assert detail["included"] <= history.DETAIL_STRING_PAGE
        parts.append(detail["values"])
        detail_query = detail["next_query"]
    assert "".join(parts) == original
    assert store.db.total_changes == before
    for pointer in ("/result/text", "/private_prompt", "/arguments/missing"):
        with pytest.raises(ValueError, match="own_attempt_input_pointer_unavailable"):
            history.lookup_attempts(journal, "owner", before=1, query={
                "view": "own_attempt_detail", "decision_index": 0, "pointer": pointer, "offset": 0, "limit": 20})
    with pytest.raises(ValueError, match="own_attempt_decision_unavailable"):
        history.lookup_attempts(journal, "owner", before=0, query={
            "view": "own_attempt_detail", "decision_index": 0, "pointer": "", "offset": 0, "limit": 20})


def test_selected_detail_pages_array_object_scalar_and_json_pointer_escaping(saved):
    _, journal = saved
    arguments = {"a/b~c": list(range(100)), "enabled": False, "object": {"c": 3, "b": 2, "a": 1}}
    attempt(journal, 0, {"kind": "tool", "tool": "search", "arguments": arguments})
    base = {"view": "own_attempt_detail", "decision_index": 0, "offset": 1, "limit": 2}
    array = history.lookup_attempts(journal, "owner", before=1, query={**base, "pointer": "/arguments/a~1b~0c"})
    assert array["values"] == [1, 2] and array["slice_unit"] == "array_items"
    assert array["next_query"]["offset"] == 3
    obj = history.lookup_attempts(journal, "owner", before=1, query={**base, "pointer": "/arguments/object"})
    assert obj["values"] == {"b": 2, "c": 3} and obj["has_more"] is False
    scalar = history.lookup_attempts(journal, "owner", before=1,
        query={**base, "pointer": "/arguments/enabled", "offset": 0})
    assert scalar["values"] is False and scalar["slice_unit"] == "scalar_values"
    assert scalar["has_more"] is False
    assert not Draft202012Validator(history.lookup_schema()).is_valid({**base, "pointer": "/bad~2escape"})


def test_oversized_discriminators_and_reference_values_are_explicit_bounded_records(saved):
    _, journal = saved
    large = "LONG_RECORDED_VALUE_" * 1000
    attempt(journal, 0, {"kind": "tool", "tool": large}, refs=[large, "record_small"])
    record = history.lookup_attempts(journal, "owner", before=1, query=query())["records"][0]
    assert large not in json.dumps(record)
    assert record["category"] is None and record["selection"]["tool"] is None
    summary = record["selection_discriminator_summaries"]["tool"]
    assert summary["total"] == len(large) and summary["detail_query"]["pointer"] == "/tool"
    references = record["published_references"]
    assert references["values"] == ["record_small"]
    assert references["total"] == references["previewed"] == 2
    assert references["included"] == 1 and references["complete"] is False
    assert references["bounded_values"][0]["publication_index"] == 0
    assert history.yield_table(journal, "owner", before=1)["uncategorized_attempts"] == 1


def test_large_requested_page_has_byte_bounded_replies_and_every_record_remains_reachable(saved):
    store, journal = saved
    total = 180
    # Several individually short selected fields create about 4 KiB of public
    # attempt information per row, without requiring a large outcome payload.
    with store.transaction():
        for index in range(total):
            arguments = {"query": f"query_{index}_" + "\u03b1" * 300,
                "reference_refs": [f"source_{index}_{part}_" + "r" * 500 for part in range(3)],
                "start": index, "end": index + 100, "mode": "targeted"}
            attempt(journal, index, {"kind": "tool", "tool": "source.targeted_read", "arguments": arguments},
                refs=[f"published_{index}"])
            observe(journal, index, index, 0)
    changes_before = store.db.total_changes
    observations_before = store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0]
    actions_before = store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0]
    pending = query(limit=100000)
    covered, pages, sizes = [], [], []
    while pending is not None:
        page = history.lookup_attempts(journal, "owner", before=total, query=pending)
        size = len(json.dumps(page, ensure_ascii=True).encode("utf-8"))
        sizes.append(size)
        assert size <= history.OWN_ATTEMPTS_REPLY_BYTES == page["reply_byte_budget"]
        assert page["limit"] == 100000 and page["total"] == total
        assert 0 < page["returned_count"] == len(page["records"]) <= page["limit"]
        if page["next_query"] is not None:
            assert page["pagination_reason"] == "transport_byte_budget"
            assert page["next_offset"] == pending["offset"] + page["returned_count"]
            assert page["next_query"] == {**pending, "offset": page["next_offset"]}
        else:
            assert page["pagination_reason"] == "end_of_records" and page["next_offset"] is None
        for record in page["records"]:
            index = record["decision_index"]
            assert record["completed_gain"] == 0
            assert record["published_references"]["values"] == [f"published_{index}"]
        covered.extend(record["decision_index"] for record in page["records"])
        pages.append(page)
        pending = page["next_query"]
    assert len(pages) > 1 and covered == list(range(total))
    assert len(set(covered)) == total and max(sizes) > history.OWN_ATTEMPTS_REPLY_BYTES // 2
    assert store.db.total_changes == changes_before
    assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == observations_before == total
    assert store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == actions_before == total
