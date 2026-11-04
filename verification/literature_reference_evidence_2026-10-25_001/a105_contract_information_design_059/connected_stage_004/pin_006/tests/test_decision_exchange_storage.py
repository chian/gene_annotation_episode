"""Real durable exchange records; no model, scientific operation or controller."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import subprocess
import sys
import threading

import pytest

from method_loop.durable import canonical

from gene_annotation_episode import execution_timing
from gene_annotation_episode.decision_exchanges import DecisionExchanges
from gene_annotation_episode.episode_completion import CompletionLedger
from gene_annotation_episode.episode_journal import Journal, WorkflowError
from gene_annotation_episode.state import Store


def setup(store, *, run="run", episode="owner", decision=3):
    journal = Journal(store, run)
    journal.save("runtime_model_calls", {"episode_id": episode,
        "call_index": decision, "purpose": "decision", "request": canonical({
            "context": {"raw_numerical_history": [0, -2, 4]}, "schema": {"original": True}}),
        "response": None})
    return journal, DecisionExchanges(journal)


def request(index=0):
    return {"frame": {"kind": "decision_bootstrap" if index == 0 else "lookup_result",
            "values": [index, {"unknown_duration": None}]},
        "schema": {"type": "object", "properties": {"response": {"type": "object"}}},
        "restoration": {"snapshot": {"record_refs": ["source_original"]},
            "public_exchange_indices": list(range(index))}}


def lookup_response(index=0):
    return {"response": {"response_type": "request_context", "lookup": {
        "view": "own_attempts", "category": None, "decision_indices": [index],
        "offset": 0, "limit": 2}}}


def logical_rows(store):
    tables = ("runtime_model_calls", "runtime_actions", "runtime_observations",
        "runtime_completion_slots", "runtime_decision_effects", "runtime_source_states")
    return {table: [dict(row) for row in store.db.execute("SELECT * FROM " + table)]
            for table in tables}


def test_multiple_exchanges_reopen_exactly_without_action_or_observation(tmp_path):
    path = tmp_path / "workspace"
    with Store(path) as store:
        journal, exchanges = setup(store)
        ledger = CompletionLedger(store, journal)
        original = logical_rows(store)
        for index in range(3):
            prepared = exchanges.prepare("owner", 3, index, request(index))
            assert prepared["request"] == request(index)
            assert prepared["response"] is None and not prepared["response_recorded"]
            assert prepared["lookup_result"] is None and not prepared["lookup_result_recorded"]
            exchanges.respond("owner", 3, index, lookup_response(index))
            exchanges.resolve_lookup("owner", 3, index, {"rows": [{"decision_index": index}],
                "source_range": {"before": 3}, "next_offset": None})
        exchanges.prepare("owner", 3, 3, request(3))
        exchanges.respond("owner", 3, 3, {"response": {"response_type": "select_action",
            "selection": {"kind": "tool", "tool_name": "source.read"}, "report_update": {}}})
        saved = exchanges.rows("owner", 3)
        assert [row["exchange_index"] for row in saved] == [0, 1, 2, 3]
        assert [row["lookup_result_recorded"] for row in saved] == [True, True, True, False]
        assert logical_rows(store) == original
        assert ledger.slot("owner", 0) is None
        assert ledger.restore_source("owner")["next_call_index"] == 3
    with Store(path) as store:
        journal = Journal(store, "run")
        exchanges = DecisionExchanges(journal)
        assert exchanges.rows("owner", 3) == saved
        for row in saved:
            assert exchanges.prepare("owner", 3, row["exchange_index"], row["request"]) == row
            assert exchanges.respond("owner", 3, row["exchange_index"], row["response"]) == row
            if row["lookup_result_recorded"]:
                assert exchanges.resolve_lookup("owner", 3, row["exchange_index"], row["lookup_result"]) == row
        assert logical_rows(store) == original


@pytest.mark.parametrize("phase", ["request", "response", "lookup_result"])
def test_each_committed_boundary_can_resume_and_rejects_changed_replay(tmp_path, phase):
    path = tmp_path / "workspace"
    phases = ["request", "response", "lookup_result"]
    values = {"request": request(), "response": lookup_response(),
        "lookup_result": {"rows": [], "observed_before": 3}}
    methods = {"request": "prepare", "response": "respond", "lookup_result": "resolve_lookup"}
    with Store(path) as store:
        _journal, exchanges = setup(store)
        for name in phases[:phases.index(phase) + 1]:
            getattr(exchanges, methods[name])("owner", 3, 0, values[name])
        saved = exchanges.rows("owner", 3)[0]
    with Store(path) as store:
        exchanges = DecisionExchanges(Journal(store, "run"))
        assert exchanges.rows("owner", 3) == [saved]
        for name in phases[:phases.index(phase) + 1]:
            assert getattr(exchanges, methods[name])("owner", 3, 0, values[name]) == saved
            with pytest.raises(WorkflowError, match="identity_conflict"):
                getattr(exchanges, methods[name])("owner", 3, 0, {"changed": name})
        for name in phases[phases.index(phase) + 1:]:
            getattr(exchanges, methods[name])("owner", 3, 0, values[name])
        completed = exchanges.rows("owner", 3)[0]
        assert all(completed[name] == values[name] for name in phases)
        assert store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0


def test_json_values_are_detached_finite_and_invalid_responses_remain_exact(tmp_path):
    with Store(tmp_path / "workspace") as store:
        _journal, exchanges = setup(store)
        original = request()
        prepared = exchanges.prepare("owner", 3, 0, original)
        original["frame"]["values"].append("changed original")
        prepared["request"]["frame"]["values"].append("changed return")
        assert exchanges.rows("owner", 3)[0]["request"] == request()
        # Persisted JSON null and absent SQL NULL are different states, even
        # though both public JSON values decode to Python None.
        null = exchanges.respond("owner", 3, 0, None)
        assert null["response"] is None and null["response_recorded"]
        assert null["lookup_result"] is None and not null["lookup_result_recorded"]
        null = exchanges.resolve_lookup("owner", 3, 0, None)
        assert null["lookup_result"] is None and null["lookup_result_recorded"]
        assert exchanges.respond("owner", 3, 0, None) == null
        exchanges.prepare("owner", 3, 1, request(1))
        response = ["malformed envelope", {"number": -1.25, "flag": False}]
        recorded = exchanges.respond("owner", 3, 1, response)
        response[1]["number"] = 99
        recorded["response"][1]["number"] = 100
        assert exchanges.rows("owner", 3)[1]["response"][1]["number"] == -1.25
        for value in (float("nan"), float("inf"), object(), {1: "non-string-key"}):
            with pytest.raises(ValueError):
                exchanges.respond("owner", 3, 1, value)
        with pytest.raises(TypeError, match="json_object"):
            exchanges.prepare("owner", 3, 2, ["request is not an object"])


def test_sequencing_requires_recorded_predecessor_but_does_not_interpret_response(tmp_path):
    with Store(tmp_path / "workspace") as store:
        _journal, exchanges = setup(store)
        with pytest.raises(WorkflowError, match="next_index"):
            exchanges.prepare("owner", 3, 1, request())
        with pytest.raises(WorkflowError, match="prepared_request"):
            exchanges.respond("owner", 3, 0, lookup_response())
        with pytest.raises(WorkflowError, match="prepared_request"):
            exchanges.resolve_lookup("owner", 3, 0, {"rows": []})
        exchanges.prepare("owner", 3, 0, request())
        with pytest.raises(WorkflowError, match="previous_response"):
            exchanges.prepare("owner", 3, 1, request(1))
        with pytest.raises(WorkflowError, match="lookup_requires_response"):
            exchanges.resolve_lookup("owner", 3, 0, {"rows": []})
        exchanges.respond("owner", 3, 0, {"invalid": "runtime interprets this"})
        exchanges.prepare("owner", 3, 1, request(1))
        with pytest.raises(WorkflowError, match="next_index"):
            exchanges.prepare("owner", 3, 3, request(3))
        assert len(exchanges.rows("owner", 3)) == 2


def test_explicit_restoration_retry_preserves_unanswered_request_and_timing(tmp_path):
    path = tmp_path / "workspace"
    with Store(path) as store:
        _journal, exchanges = setup(store)
        exchanges.prepare("owner", 3, 0, request())
        with pytest.raises(KeyboardInterrupt):
            with exchanges.measure("owner", 3, 0):
                raise KeyboardInterrupt("lost ephemeral conversation")
        original = exchanges.rows("owner", 3)[0]
    with Store(path) as store:
        exchanges = DecisionExchanges(Journal(store, "run"))
        retry = request(1) | {"retry_of_exchange_index": 0,
            "frame": {"kind": "decision_bootstrap", "frozen_pending_frames": [request()["frame"]]}}
        saved = exchanges.prepare("owner", 3, 1, retry)
        assert saved["request"] == retry
        assert exchanges.rows("owner", 3)[0] == original
        assert exchanges.prepare("owner", 3, 1, retry) == saved
        with pytest.raises(WorkflowError, match="identity_conflict"):
            exchanges.prepare("owner", 3, 1, retry | {"retry_of_exchange_index": None})
        exchanges.respond("owner", 3, 1, lookup_response())
        assert exchanges.rows("owner", 3)[0] == original
        assert exchanges.rows("owner", 3)[1]["response_recorded"]
        assert not exchanges.rows("owner", 3)[0]["response_recorded"]
        exchanges.prepare("owner", 3, 2, request(2))


def test_retry_link_requires_immediately_preceding_unanswered_exchange(tmp_path):
    with Store(tmp_path / "workspace") as store:
        _journal, exchanges = setup(store)
        for retry in (-1, True, None, "0", 1):
            with pytest.raises(WorkflowError, match="invalid_retry_reference"):
                exchanges.prepare("owner", 3, 0, request() | {"retry_of_exchange_index": retry})
        exchanges.prepare("owner", 3, 0, request())
        for retry in (-1, True, None, "0", 1):
            with pytest.raises(WorkflowError, match="invalid_retry_reference"):
                exchanges.prepare("owner", 3, 1, request(1) | {"retry_of_exchange_index": retry})
        exchanges.respond("owner", 3, 0, lookup_response())
        with pytest.raises(WorkflowError, match="invalid_retry_reference"):
            exchanges.prepare("owner", 3, 1, request(1) | {"retry_of_exchange_index": 0})
        exchanges.prepare("owner", 3, 1, request(1))
        with pytest.raises(WorkflowError, match="next_index"):
            exchanges.prepare("owner", 3, 3, request(3) | {"retry_of_exchange_index": 1})
        assert len(exchanges.rows("owner", 3)) == 2


def test_logical_decision_ownership_scopes_and_completed_replay(tmp_path):
    with Store(tmp_path / "workspace") as store:
        journal, exchanges = setup(store)
        original_call = journal.row("runtime_model_calls", "owner", 3)
        with pytest.raises(WorkflowError, match="logical_decision"):
            exchanges.prepare("other", 3, 0, request())
        other = DecisionExchanges(Journal(store, "other-run"))
        assert other.rows("owner", 3) == []
        with pytest.raises(WorkflowError, match="logical_decision"):
            other.prepare("owner", 3, 0, request())
        journal.save("runtime_model_calls", {"episode_id": "other", "call_index": 3,
            "purpose": "report", "request": "{}", "response": None})
        with pytest.raises(WorkflowError, match="logical_decision"):
            exchanges.prepare("other", 3, 0, request())
        exchanges.prepare("owner", 3, 0, request())
        exchanges.respond("owner", 3, 0, lookup_response())
        before_completion = exchanges.rows("owner", 3)[0]
        journal.save("runtime_model_calls", original_call | {
            "response": canonical({"selection": {"kind": "wait"}, "report_update": {}})})
        assert exchanges.prepare("owner", 3, 0, request()) == before_completion
        assert exchanges.respond("owner", 3, 0, lookup_response()) == before_completion
        with pytest.raises(WorkflowError, match="pending_decision"):
            exchanges.prepare("owner", 3, 1, request(1))
        assert journal.row("runtime_model_calls", "owner", 3)["request"] == original_call["request"]
        _journal, sibling = setup(store, episode="sibling")
        sibling.prepare("sibling", 3, 0, request())
        _journal, other_decision = setup(store, decision=4)
        other_decision.prepare("owner", 4, 0, request())
        assert len(exchanges.rows("owner", 3)) == 1


def test_indices_are_actual_nonnegative_integers(tmp_path):
    with Store(tmp_path / "workspace") as store:
        _journal, exchanges = setup(store)
        for method in ("rows", "prepare", "respond", "resolve_lookup", "measure"):
            for bad_index in (-1, True, 1.5, "0"):
                arguments = ["owner", bad_index]
                if method != "rows":
                    arguments.append(0)
                if method in {"prepare", "respond", "resolve_lookup"}:
                    arguments.append({})
                with pytest.raises(ValueError, match="nonnegative_integer"):
                    getattr(exchanges, method)(*arguments)


def test_writes_and_constructor_join_outer_store_rollback(tmp_path):
    with Store(tmp_path / "workspace") as store:
        journal = Journal(store, "run")
        with pytest.raises(RuntimeError, match="rollback schema"):
            with store.transaction():
                DecisionExchanges(journal)
                raise RuntimeError("rollback schema")
        assert store.db.execute("SELECT 1 FROM sqlite_master "
            "WHERE name='runtime_decision_exchanges'").fetchone() is None
        journal, exchanges = setup(store)
        with pytest.raises(KeyboardInterrupt):
            with store.transaction():
                exchanges.prepare("owner", 3, 0, request())
                exchanges.respond("owner", 3, 0, lookup_response())
                exchanges.resolve_lookup("owner", 3, 0, {"rows": []})
                raise KeyboardInterrupt("rollback values")
        assert exchanges.rows("owner", 3) == []
        assert journal.row("runtime_model_calls", "owner", 3)["response"] is None
        exchanges.prepare("owner", 3, 0, request())
        with pytest.raises(KeyboardInterrupt):
            with store.transaction():
                exchanges.respond("owner", 3, 0, lookup_response())
                raise KeyboardInterrupt("rollback response")
        assert not exchanges.rows("owner", 3)[0]["response_recorded"]


def test_concurrent_connections_freeze_one_exact_exchange(tmp_path):
    path = tmp_path / "workspace"
    with Store(path) as store:
        setup(store)
    barrier = threading.Barrier(3)

    def worker():
        with Store(path) as store:
            exchanges = DecisionExchanges(Journal(store, "run"))
            barrier.wait(timeout=10)
            exchanges.prepare("owner", 3, 0, request())
            return exchanges.respond("owner", 3, 0, lookup_response())

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda _: worker(), range(3)))
    assert results[0] == results[1] == results[2]
    with Store(path) as store:
        exchanges = DecisionExchanges(Journal(store, "run"))
        assert exchanges.rows("owner", 3) == [results[0]]


def test_timing_interruption_appends_spans_without_mutating_operands(tmp_path):
    path = tmp_path / "workspace"
    with Store(path) as store:
        journal, exchanges = setup(store)
        original_call = journal.row("runtime_model_calls", "owner", 3)
        with pytest.raises(WorkflowError, match="timing_requires_prepared_request"):
            with exchanges.measure("owner", 3, 0):
                pass
        exchanges.prepare("owner", 3, 0, request())
        with pytest.raises(KeyboardInterrupt):
            with exchanges.measure("owner", 3, 0):
                raise KeyboardInterrupt("physical dispatch interrupted")
        interrupted = exchanges.rows("owner", 3)[0]
        assert interrupted["timing"]["intervals"][0]["state"] == "interrupted"
        assert interrupted["timing"]["intervals"][0]["exception_type"] == "KeyboardInterrupt"
        assert not interrupted["response_recorded"]
    with Store(path) as store:
        journal = Journal(store, "run")
        exchanges = DecisionExchanges(journal)
        assert exchanges.prepare("owner", 3, 0, request()) == interrupted
        with exchanges.measure("owner", 3, 0):
            exchanges.respond("owner", 3, 0, lookup_response())
        measured = exchanges.rows("owner", 3)[0]
        spans = measured["timing"]["intervals"]
        assert [span["state"] for span in spans] == ["interrupted", "returned"]
        assert spans[0] == interrupted["timing"]["intervals"][0]
        assert measured["timing"]["measured_elapsed_seconds"] == sum(span["elapsed_seconds"] for span in spans)
        assert measured["request"] == request()
        assert journal.row("runtime_model_calls", "owner", 3) == original_call
        assert store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == 0


def test_abrupt_owner_loss_preserves_unknown_span_and_excludes_offline_gap(tmp_path):
    path = tmp_path / "workspace"
    with Store(path) as store:
        _journal, exchanges = setup(store)
        exchanges.prepare("owner", 3, 0, request())
    code = """
import os, sys
from gene_annotation_episode.state import Store
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.decision_exchanges import DecisionExchanges
with Store(sys.argv[1]) as store:
    exchanges = DecisionExchanges(Journal(store, 'run'))
    with exchanges.measure('owner', 3, 0):
        os._exit(17)
"""
    child = subprocess.run([sys.executable, "-c", code, str(path)], capture_output=True, timeout=20)
    assert child.returncode == 17, child.stderr.decode()
    with Store(path) as store:
        exchanges = DecisionExchanges(Journal(store, "run"))
        lost = deepcopy(exchanges.rows("owner", 3)[0]["timing"])
        assert lost["intervals"][0]["state"] == "running"
        assert execution_timing.snapshot(lost)["unmeasured_ended_intervals"] == 1
        assert lost["measured_elapsed_seconds"] == 0
        with exchanges.measure("owner", 3, 0):
            pass
        measured = exchanges.rows("owner", 3)[0]["timing"]
        assert [span["state"] for span in measured["intervals"]] == ["end_unobserved", "returned"]
        assert measured["unmeasured_ended_intervals"] == 1
        assert measured["intervals"][0] == lost["intervals"][0] | {"state": "end_unobserved"}
        assert measured["intervals"][0]["elapsed_seconds"] is None
        assert measured["intervals"][0]["ended_at"] is None
        assert measured["measured_elapsed_seconds"] == measured["intervals"][1]["elapsed_seconds"]
