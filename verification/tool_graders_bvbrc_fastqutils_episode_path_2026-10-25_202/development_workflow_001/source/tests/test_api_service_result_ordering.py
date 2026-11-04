"""Binding regressions; full native custody and Workflow tests are separate.

These fixtures exercise the real disk enumeration and role-dispatch methods.
The stored outcomes and forwarded receipts are deliberately synthetic values.
"""
from types import SimpleNamespace

import pytest

from gene_annotation_episode.api_service_execution import APIServiceExecution
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.practical_execution_state import _immutable


def test_actual_operation_order_survives_hashed_paths_and_incomplete_actions(tmp_path):
    api = object.__new__(APIServiceExecution)
    api.directory, api.run_id = tmp_path, "order-regression"
    episode_id = "results-episode"
    indexes = [0, 1, 2, 3, 6, 10, 11]
    finished = {0, 3, 6, 10}
    for index in reversed(indexes):
        key = f"{api.run_id}:{episode_id}:{index}"
        directory = api._episode_directory(episode_id) / "actions" / digest(key)
        directory.mkdir(parents=True)
        _immutable(directory / "intent.json", {
            "run_id": api.run_id, "episode_id": episode_id,
            "operation_key": key, "name": "fixture.operation",
            "prepared": {}, "started_at": f"fixture-reversed-time-{99-index}"})
        if index in finished:
            _immutable(directory / "outcome.json", {
                "status": "partial" if index < 10 else "completed",
                "result": {"actual_decision_index": index}})
    before = {path.relative_to(tmp_path): path.read_bytes()
              for path in tmp_path.rglob("*.json")}
    paths = list((api._episode_directory(episode_id) / "actions").glob("*/intent.json"))
    assert sorted(path.parent.name for path in paths) != [
        digest(f"{api.run_id}:{episode_id}:{index}") for index in indexes]
    context = SimpleNamespace(episode_id=episode_id)
    outcomes = list(api._own_outcomes(context))
    assert [row["result"]["actual_decision_index"] for _, row in outcomes] == [0, 3, 6, 10]
    assert outcomes[-1][1]["status"] == "completed"
    assert before == {path.relative_to(tmp_path): path.read_bytes()
                      for path in tmp_path.rglob("*.json")}


@pytest.mark.parametrize("role", [
    "annotation", "scientific_process", "launch", "launch_api", "results",
])
def test_received_support_hook_does_not_duplicate_execution_owned_facts(role):
    calls = []
    binding = object.__new__(ExecutionEpisodes)
    binding.api_execution = SimpleNamespace(
        services={"fixture": SimpleNamespace(service="bvbrc_appservice")},
        appservice=SimpleNamespace(received_support_refs=lambda context:
            calls.append(context.role) or ["synthetic-received-receipt"]),
        homology_returns=SimpleNamespace(received_facts=lambda context, schema: {}),
        phylogeny_returns=SimpleNamespace(received_facts=lambda context, schema: {}),
        alignment_returns=SimpleNamespace(received_facts=lambda context, schema: {}))
    context = SimpleNamespace(role=role, request={"report_contract": {"measurements": {
        "schema": {"properties": {"support": {
            "x-source": "bvbrc_appservice_support_refs"}}}}}})
    actual = binding.received_report_facts(context)
    forwards = role in {"annotation", "scientific_process"}
    assert actual == ({"bvbrc_appservice_support_refs": ["synthetic-received-receipt"]}
                      if forwards else {})
    assert calls == ([role] if forwards else [])
