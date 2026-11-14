"""Immutable physical exchanges within one pending logical decision.

These records retain exact dispatched requests, model responses and lookup
replies. They neither select work nor advance action, completion or credit state.
Only timing is appendable, through the shared execution-interval recorder.
"""
from __future__ import annotations

from collections.abc import Mapping
import json
from typing import TypedDict

from method_loop.durable import canonical

from . import execution_timing
from .episode_journal import WorkflowError


class DecisionExchange(TypedDict):
    run_id: str
    episode_id: str
    decision_index: int
    exchange_index: int
    request: dict
    response: object
    lookup_result: object
    timing: dict | None
    response_recorded: bool
    lookup_result_recorded: bool


def _text(value, name):
    if not isinstance(value, str) or not value:
        raise ValueError(name + "_required")
    return value


def _index(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(name + "_requires_nonnegative_integer")
    return value


def _decoded(row) -> DecisionExchange:
    value = dict(row)
    # A malformed model response may itself be JSON null. Its persisted value
    # must remain distinguishable from an exchange awaiting a response.
    value["response_recorded"] = row["response"] is not None
    value["lookup_result_recorded"] = row["lookup_result"] is not None
    for name in ("request", "response", "lookup_result", "timing"):
        value[name] = None if row[name] is None else json.loads(row[name])
    return value


class DecisionExchanges:
    """Run-scoped physical exchanges, using the Journal's Store transaction."""

    def __init__(self, journal):
        self.journal, self.store, self.db = journal, journal.store, journal.db
        self.run_id = _text(journal.run_id, "run_id")
        with self.store.transaction():
            self.db.execute("""CREATE TABLE IF NOT EXISTS runtime_decision_exchanges (
                run_id TEXT NOT NULL, episode_id TEXT NOT NULL,
                decision_index INTEGER NOT NULL, exchange_index INTEGER NOT NULL,
                request TEXT NOT NULL, response TEXT, lookup_result TEXT, timing TEXT,
                PRIMARY KEY(run_id,episode_id,decision_index,exchange_index))""")

    def _key(self, episode_id, decision_index, exchange_index):
        return (self.run_id, _text(episode_id, "episode_id"),
                _index(decision_index, "decision_index"),
                _index(exchange_index, "exchange_index"))

    def _row(self, key):
        return self.db.execute("SELECT * FROM runtime_decision_exchanges "
            "WHERE run_id=? AND episode_id=? AND decision_index=? AND exchange_index=?",
            key).fetchone()

    def rows(self, episode_id, decision_index) -> list[DecisionExchange]:
        """Read ordered detached JSON records without replaying any work."""
        key = (self.run_id, _text(episode_id, "episode_id"),
               _index(decision_index, "decision_index"))
        return [_decoded(row) for row in self.db.execute(
            "SELECT * FROM runtime_decision_exchanges WHERE run_id=? AND episode_id=? "
            "AND decision_index=? ORDER BY exchange_index", key)]

    def prepare(self, episode_id, decision_index, exchange_index, request) -> DecisionExchange:
        """Freeze the complete request before dispatch; exact replay is inert."""
        key = self._key(episode_id, decision_index, exchange_index)
        if not isinstance(request, Mapping):
            raise TypeError("decision_exchange_request_requires_json_object")
        encoded = canonical(request)
        with self.store.transaction():
            old = self._row(key)
            if old is not None:
                if old["request"] != encoded:
                    raise WorkflowError("decision_exchange_request_identity_conflict")
                return _decoded(old)
            previous = self.db.execute("SELECT exchange_index,response "
                "FROM runtime_decision_exchanges WHERE run_id=? AND episode_id=? "
                "AND decision_index=? ORDER BY exchange_index DESC LIMIT 1", key[:3]).fetchone()
            expected = 0 if previous is None else previous["exchange_index"] + 1
            if exchange_index != expected:
                raise WorkflowError("decision_exchange_requires_next_index")
            if "retry_of_exchange_index" in request:
                retry = request["retry_of_exchange_index"]
                if (type(retry) is not int or previous is None
                        or retry != previous["exchange_index"]
                        or previous["response"] is not None):
                    raise WorkflowError("decision_exchange_invalid_retry_reference")
            elif previous is not None and previous["response"] is None:
                raise WorkflowError("decision_exchange_requires_previous_response")
            call = self.journal.row("runtime_model_calls", episode_id, decision_index)
            if call is None or call["purpose"] != "decision":
                raise WorkflowError("decision_exchange_requires_logical_decision")
            if call["response"] is not None:
                raise WorkflowError("decision_exchange_requires_pending_decision")
            self.db.execute("INSERT INTO runtime_decision_exchanges "
                "(run_id,episode_id,decision_index,exchange_index,request) VALUES(?,?,?,?,?)",
                (*key, encoded))
            return _decoded(self._row(key))

    def _freeze(self, episode_id, decision_index, exchange_index, column, value):
        key = self._key(episode_id, decision_index, exchange_index)
        encoded = canonical(value)
        with self.store.transaction():
            old = self._row(key)
            if old is None:
                raise WorkflowError("decision_exchange_requires_prepared_request")
            if old[column] is not None:
                if old[column] != encoded:
                    raise WorkflowError("decision_exchange_" + column + "_identity_conflict")
                return _decoded(old)
            if column == "lookup_result" and old["response"] is None:
                raise WorkflowError("decision_exchange_lookup_requires_response")
            # column is a private fixed discriminator, never caller SQL.
            self.db.execute("UPDATE runtime_decision_exchanges SET " + column + "=? "
                "WHERE run_id=? AND episode_id=? AND decision_index=? AND exchange_index=?",
                (encoded, *key))
            return _decoded(self._row(key))

    def respond(self, episode_id, decision_index, exchange_index, response) -> DecisionExchange:
        """Freeze the exact model value, including a malformed finite JSON value."""
        return self._freeze(episode_id, decision_index, exchange_index, "response", response)

    def resolve_lookup(self, episode_id, decision_index, exchange_index, result) -> DecisionExchange:
        """Freeze the runtime's lookup result or structured exchange feedback."""
        return self._freeze(episode_id, decision_index, exchange_index, "lookup_result", result)

    def measure(self, episode_id, decision_index, exchange_index):
        """Record physical dispatch intervals separately from logical/action state."""
        key = self._key(episode_id, decision_index, exchange_index)

        def read():
            row = self._row(key)
            if row is None:
                raise WorkflowError("decision_exchange_timing_requires_prepared_request")
            return row["timing"]

        def write(timing):
            with self.store.transaction():
                self.db.execute("UPDATE runtime_decision_exchanges SET timing=? "
                    "WHERE run_id=? AND episode_id=? AND decision_index=? AND exchange_index=?",
                    (timing, *key))

        return execution_timing.measure(read, write)
