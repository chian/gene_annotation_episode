"""Durable ordinary retrieval: actual maps, scripted FAST, no scientific score."""
import asyncio
from copy import deepcopy
import json

import pytest

from gene_annotation_episode.providers import ModelRole
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.scientific_tool_retrieval import (
    ScientificToolRetriever, configuration, output_schema)
from gene_annotation_episode.state import Store
from method_loop.durable import canonical


CONFIG = {"version": "scientific_tool_retrieval_v1", "mode": "semantic_fast_v1",
    "model": {"model": "gpt-6-luna", "reasoning_effort": "none"}}
ACTUAL = [
    {"name": "actual.inspect", "description": "Inspect actual input symbols",
        "input_schema": {"type": "object", "properties": {"subject_ref": {"type": "string"}},
            "required": ["subject_ref"], "additionalProperties": False}},
    {"name": "actual.compare", "description": "Compare selected real records",
        "input_schema": {"type": "object", "properties": {}, "required": [],
            "additionalProperties": False}},
    {"name": "actual.unrelated", "description": "An unrelated available operation",
        "input_schema": {"type": "object", "properties": {}, "required": [],
            "additionalProperties": False}},
]


class RetrievalProvider:
    roles = {"FAST": ModelRole("gpt-6-luna", "none")}

    def __init__(self, responses):
        self.responses, self.calls, self.released = iter(responses), [], []

    async def complete(self, call_id, role, instructions, context, output_schema):
        self.calls.append(deepcopy({"call_id": call_id, "role": role,
            "instructions": instructions, "context": context, "output_schema": output_schema}))
        response = next(self.responses)
        if isinstance(response, BaseException):
            raise response
        return await response() if callable(response) else deepcopy(response)

    async def release(self, identity):
        self.released.append(identity)


def retriever(tmp_path, store, provider, *, catalog=ACTUAL, config=CONFIG):
    library = ScientificToolLibrary.freeze(tmp_path / "tools", catalog=catalog)
    return ScientificToolRetriever(store, run_id="run-fixture", provider=provider,
        library=library, configuration=config)


def retrieve(value, investigation="Inspect and compare", *, episode_id="episode-fixture",
             key="run-fixture:episode-fixture:0", available=ACTUAL):
    return value.retrieve(investigation, episode_id=episode_id, operation_key=key,
        available_catalog=available)


def test_one_fast_request_receives_complete_map_and_original_contracts(tmp_path):
    provider = RetrievalProvider([{"tools": ["actual.compare", "actual.inspect"]}])
    with Store(tmp_path / "state") as store:
        value = retriever(tmp_path, store, provider)
        original = deepcopy(ACTUAL)
        outcome = asyncio.run(retrieve(value))
        assert outcome["status"] == "completed"
        assert outcome["record_refs"] == outcome["changed_record_refs"] == []
        assert set(outcome["result"]) == {"investigation", "tools", "catalog"}
        assert outcome["result"]["catalog"] == [ACTUAL[1], ACTUAL[0]]
        call, = provider.calls
        assert call["role"] == "FAST"
        assert call["context"] == {"investigation": "Inspect and compare",
            "catalog": sorted(ACTUAL, key=lambda row: row["name"])}
        assert set(call["output_schema"]["properties"]["tools"]["items"]["enum"]) == {
            row["name"] for row in ACTUAL}
        assert "maxItems" not in call["output_schema"]["properties"]["tools"]
        assert provider.released == [call["call_id"]]
        assert call["call_id"].startswith("scientific_tool_retrieval_")
        assert call["call_id"] != "episode-fixture"
        saved = dict(store.db.execute("SELECT * FROM runtime_tool_retrievals").fetchone())
        assert saved["response"] == canonical({"tools": ["actual.compare", "actual.inspect"]})
        assert json.loads(saved["request"])["context"] == call["context"]
        assert not store.list("source") and not store.list("observation")
        outcome["result"]["catalog"][0]["description"] = "mutated caller copy"
        assert asyncio.run(retrieve(value))["result"]["catalog"] == [ACTUAL[1], ACTUAL[0]]
        assert len(provider.calls) == 1 and ACTUAL == original


@pytest.mark.parametrize("response", [
    {"tools": ["invented.operation"]}, {"tools": ["actual.inspect", "actual.inspect"]},
    {"tools": ["actual.inspect"], "findings": "not requested"}, {"tools": "actual.inspect"},
])
def test_invalid_model_selection_is_cached_without_records_or_retry(tmp_path, response):
    provider = RetrievalProvider([response])
    with Store(tmp_path / "state") as store:
        value = retriever(tmp_path, store, provider)
        outcome = asyncio.run(retrieve(value))
        assert outcome["status"] == "invalid"
        assert outcome["feedback"]["code"] == "scientific_tool_retrieval_output_invalid"
        assert asyncio.run(retrieve(value)) == outcome
        assert len(provider.calls) == len(provider.released) == 1
        assert json.loads(store.db.execute("SELECT response FROM runtime_tool_retrievals").fetchone()[0]) == response
        assert not store.list("source") and not store.list("observation")


def test_completed_request_rejects_changed_investigation_without_overwrite(tmp_path):
    provider = RetrievalProvider([{"tools": []}])
    with Store(tmp_path / "state") as store:
        value = retriever(tmp_path, store, provider)
        first = asyncio.run(retrieve(value))
        before = tuple(store.db.execute("SELECT * FROM runtime_tool_retrievals").fetchone())
        changed = asyncio.run(retrieve(value, "A different investigation"))
        assert changed["feedback"]["code"] == "scientific_tool_retrieval_request_conflict"
        assert tuple(store.db.execute("SELECT * FROM runtime_tool_retrievals").fetchone()) == before
        assert asyncio.run(retrieve(value)) == first
        assert len(provider.calls) == 1


def test_concurrent_same_key_reader_preserves_original_active_writer(tmp_path):
    async def exercise(store):
        async def competing_read():
            before = tuple(store.db.execute("SELECT * FROM runtime_tool_retrievals").fetchone())
            with Store(store.path) as other_store:
                other_provider = RetrievalProvider([])
                other = retriever(tmp_path, other_store, other_provider)
                outcome = await retrieve(other)
                assert outcome["feedback"]["code"] == "scientific_tool_retrieval_result_ambiguous"
                assert not other_provider.calls
            assert tuple(store.db.execute("SELECT * FROM runtime_tool_retrievals").fetchone()) == before
            return {"tools": ["actual.inspect"]}
        provider = RetrievalProvider([competing_read])
        value = retriever(tmp_path, store, provider)
        first = await retrieve(value)
        assert first["status"] == "completed"
        assert await retrieve(value) == first
        assert len(provider.calls) == 1
        assert json.loads(store.db.execute("SELECT response FROM runtime_tool_retrievals").fetchone()[0]) == {
            "tools": ["actual.inspect"]}
    with Store(tmp_path / "state") as store:
        asyncio.run(exercise(store))


def test_interrupted_call_is_retired_and_its_failure_replayed(tmp_path):
    provider = RetrievalProvider([asyncio.CancelledError()])
    with Store(tmp_path / "state") as store:
        value = retriever(tmp_path, store, provider)
        with pytest.raises(asyncio.CancelledError):
            asyncio.run(retrieve(value))
        result = asyncio.run(retrieve(value))
        assert result["feedback"]["code"] == "scientific_tool_retrieval_interrupted"
        assert len(provider.calls) == len(provider.released) == 1


def test_abrupt_unpublished_response_is_ambiguous_and_never_reretrieved(tmp_path, monkeypatch):
    provider = RetrievalProvider([{"tools": ["actual.inspect"]}])
    with Store(tmp_path / "state") as store:
        value = retriever(tmp_path, store, provider)
        with monkeypatch.context() as interrupted:
            def lose_publication(*args, **kwargs):
                raise KeyboardInterrupt()
            interrupted.setattr(value, "_publish", lose_publication)
            with pytest.raises(KeyboardInterrupt):
                asyncio.run(retrieve(value))
        outcome = asyncio.run(retrieve(value))
        assert outcome["feedback"]["code"] == "scientific_tool_retrieval_result_ambiguous"
        assert len(provider.calls) == len(provider.released) == 1
        assert store.db.execute("SELECT result FROM runtime_tool_retrievals").fetchone()[0] is None


def test_empty_map_returns_empty_without_provider_or_manufactured_enum(tmp_path):
    provider = RetrievalProvider([])
    with Store(tmp_path / "state") as store:
        value = retriever(tmp_path, store, provider, catalog=[])
        result = asyncio.run(retrieve(value, available=[]))
        assert result["result"] == {"investigation": "Inspect and compare", "tools": [], "catalog": []}
        assert provider.calls == provider.released == []
        from jsonschema import Draft202012Validator
        Draft202012Validator.check_schema(output_schema([]))
        Draft202012Validator(output_schema([])).validate({"tools": []})


def test_model_configuration_drift_fails_before_dispatch_and_stays_cached(tmp_path):
    provider = RetrievalProvider([])
    provider.roles = {"FAST": ModelRole("a-different-model", "none")}
    with Store(tmp_path / "state") as store:
        value = retriever(tmp_path, store, provider)
        first = asyncio.run(retrieve(value))
        assert first["feedback"]["code"] == "scientific_tool_retrieval_model_binding_mismatch"
        provider.roles = RetrievalProvider.roles
        assert asyncio.run(retrieve(value)) == first
        assert not provider.calls


def test_opt_in_configuration_is_exact_and_copies_caller_data():
    assert configuration(None) is None
    assert configuration(CONFIG) == CONFIG and configuration(CONFIG) is not CONFIG
    for invalid in ({}, {**CONFIG, "quota": 3}, {**CONFIG, "mode": "unknown"},
                    {**CONFIG, "model": {"model": "x"}}):
        with pytest.raises(ValueError):
            configuration(invalid)
