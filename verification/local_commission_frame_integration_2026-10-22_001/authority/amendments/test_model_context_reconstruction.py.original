"""Actual detached fixed-case worker with a scripted model transport.

The inherited API reconstruction fixture selects no HTTP/native work. Its full
assertions run unchanged; this wrapper adds the opt-in presentation boundary.
Zero preview and fixture continuation counts are test inputs, not runtime caps.
"""
import hashlib
import json
import sqlite3

import test_api_execution_planning_reconstruction as original


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def test_opt_in_actual_worker_keeps_raw_history_and_original_handoff(tmp_path, monkeypatch):
    prepare_original = original.prepared

    def prepared_with_presentation(directory):
        case, configuration, policy = prepare_original(directory)
        configuration["restoration"] = {
            "preview_size": 0, "model_presentation": "bounded_wait_history_v1"}
        return case, configuration, policy

    monkeypatch.setattr(original, "prepared", prepared_with_presentation)
    original.test_actual_scientific_worker_restores_planning_map_original_proposal_and_caller(
        tmp_path, monkeypatch)

    run = json.loads((tmp_path / "run/run.json").read_text())
    assert run["restoration"] == {
        "preview_size": 0, "model_presentation": "bounded_wait_history_v1"}
    sent = [json.loads(line) for line in (tmp_path / "turns.jsonl").read_text().splitlines()]
    database = tmp_path / "case/workspace/state.sqlite3"
    with sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        requests = [json.loads(row[0]) for row in db.execute(
            "SELECT request FROM runtime_model_calls WHERE run_id=? "
            "ORDER BY episode_id,call_index", (run["run_id"],))]
    child = [r for r in requests if "scientific_process" in r["context"]]
    assert len(child) == len(sent) == 2
    for request, actual in zip(child, sent):
        assert request["version"] == "runtime_model_call_request_v2"
        presentation = request["model_presentation"]
        assert presentation["version"] == "episode_model_presentation_v1"
        assert encoded(presentation["context"]) == encoded(actual)
        text = json.dumps(actual, allow_nan=False)
        assert hashlib.sha256(text.encode()).hexdigest() == presentation["model_input_text_sha256"]
        assert len(text) == presentation["model_input_char_count"]
        assert len(text.encode()) == presentation["model_input_utf8_byte_count"]
        assert "own_completed_action_history_page" not in request["context"]["waiting_support"]
        restored = json.loads(encoded(actual))
        restored["waiting_support"].pop("own_completed_action_history_page")
        restored["waiting_support"]["own_completed_action_history"] = request[
            "context"]["waiting_support"]["own_completed_action_history"]
        assert encoded(restored) == encoded(request["context"])

    raw_history = child[1]["context"]["waiting_support"]["own_completed_action_history"]
    model_waiting = sent[1]["waiting_support"]
    assert len(raw_history) == 1
    assert model_waiting["own_completed_action_history"] == []
    page = model_waiting["own_completed_action_history_page"]
    assert (page["total_rows"], page["included_rows"], page["omitted_rows"]) == (1, 0, 1)
    assert page["history_is_complete"] is False
    assert page["history_lookup"]["availability"] == "available"
    assert page["discover_older_decisions"] == {
        "tool": "episode.history", "arguments": {"view": "index", "offset": 0, "limit": 1}}
