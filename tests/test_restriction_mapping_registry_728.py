"""One saved-only host job from retained native data; no catalog installation."""
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path

import pytest
from method_loop.identities import EpisodeRef

from gene_annotation_episode.domain import ContractError, canonical
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.restriction_mapping_jobs import RestrictionMappingJobs
from gene_annotation_episode.restriction_mapping_publication import read_published_restriction_result
from gene_annotation_episode.restriction_mapping_returns import restriction_mapping_fact_sources
from gene_annotation_episode import restriction_mapping_registry as module
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from gene_annotation_episode import tools as tools_module


pytestmark = pytest.mark.skipif("HMMER529_ATTEMPT" not in os.environ, reason="requires bounded529")


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def forbid(*args, **kwargs):
    raise AssertionError("retained operation must not dispatch, extract, or refresh software")


@pytest.fixture(scope="module")
def saved_job():
    selector_path = os.environ.get("HMMER_NATIVE_ORACLE_RESTRICTION728_SAVED_SELECTOR")
    if selector_path:
        selected = json.loads(Path(selector_path).read_bytes())
        store = Store(selected["store_path"])
        tools = ToolRegistry(store)
    else:
        native_selector = json.loads(Path(os.environ["HMMER_NATIVE_ORACLE_RESTRICTION728_NATIVE_SELECTOR"]).read_bytes())
        store = Store(native_selector["store_path"])
        tools = ToolRegistry(store)
        original = RestrictionMappingJobs(store).publication_state(native_selector["operation_key"])
        assert original["published_source_ref"] is not None, "725 publication handoff required"
        if store.db.execute("SELECT 1 FROM tool_operations WHERE operation_key=?",
                (native_selector["operation_key"],)).fetchone() is None:
            with store.transaction():
                original_outcome = module.publish_restriction_work(tools, native_selector["operation_key"])
                reserved = original["reservation"]
                tools._save(native_selector["operation_key"], reserved["tool_name"],
                    reserved["arguments"], reserved["scope"], original_outcome)
        prior = read_published_restriction_result(store, original["published_source_ref"],
            scope=original["reservation"]["scope"])
        run_id = "restriction728-host-boundary"
        path = (("root", "root"), ("scientific_process", "child_0"))
        episode_id = EpisodeRef(run_id, path).episode_id
        scope = original["reservation"]["scope"]
        fields = restriction_mapping_fact_sources()["restriction_mapping_results"]["report_schema"]
        fields["items"]["properties"]["selection_policy"] = {"type": "string", "const": "all_own_completed_results"}
        schema = {"type": "object", "properties": {"selected": fields},
            "required": ["selected"], "additionalProperties": False}
        request = {"message": {"scope": scope, "episode_assignment": {}},
            "report_contract": {"measurements": {"schema": schema}}}
        journal = Journal(store, run_id)
        journal.save("runtime_episodes", {"episode_id": episode_id, "path": canonical(path),
            "request": canonical(request), "initial_credit": 0., "state": "active"})
        receipts = EpisodeReceipts(store, run_id)
        receipts.bind(episode_id)
        permitted = [prior["witness"]["sequence_ref"], original["published_source_ref"]]
        receipts.receive(episode_id, permitted, kind="initial")
        key = f"{run_id}:{episode_id}:0"
        arguments = {"mode": "saved", "result_source_ref": original["published_source_ref"]}
        selected = {"store_path": str(store.path), "operation_key": key,
            "tool_name": "find_restriction_sites", "arguments": arguments, "scope": scope,
            "permitted": permitted, "run_id": run_id, "episode_id": episode_id,
            "path": [list(item) for item in path], "request": request, "decision_index": 0,
            "provenance": "engineering host-boundary context, real retained data and saved worker; no public catalog"}
        output = Path(os.environ["HMMER529_ATTEMPT"]) / "restriction728-saved"
        output.mkdir(exist_ok=False)
        selector_path = output / "selector.json"
        save(selector_path, selected)  # Recover same original key even if assertion fails.
        action = {"kind": "tool", "tool": selected["tool_name"], "arguments": arguments}
        journal.save("runtime_actions", {"episode_id": episode_id, "decision_index": 0,
            "action": canonical(action), "result": None, "credit": None})
        asyncio.run(module.prepare_restriction_work(tools, selected["tool_name"], arguments,
            scope=scope, operation_key=key, permitted_record_refs=permitted))
        with store.transaction():
            outcome = module.publish_restriction_work(tools, key)
            tools._save(key, selected["tool_name"], arguments, scope, outcome)
        journal.save("runtime_actions", {"episode_id": episode_id, "decision_index": 0,
            "action": canonical(action), "result": canonical(outcome), "credit": None})
        selected["outcome"] = outcome
        selected["source_ref"] = outcome["result"]["source_ref"]
        save(selector_path, selected)
        save(output / "published.json", read_published_restriction_result(store,
            selected["source_ref"], scope=scope))
        module.retire_restriction_work(tools, key)
    yield store, tools, selected, str(selector_path)
    store.close()


def test_actual_saved_host_job(saved_job):
    store, _, selected, _ = saved_job
    state = RestrictionMappingJobs(store).publication_state(selected["operation_key"])
    assert state["reservation"]["work_mode"] == "saved"
    assert state["execution_proof"]["original_view"]["quiescent"] is True
    assert state["execution_proof"]["returncode"] == 0
    result = read_published_restriction_result(store, selected["source_ref"], scope=selected["scope"])
    assert result["body"]["status"] == "completed"
    assert result["mapping"]["status"] == "complete"
    assert result["mapping"]["population"]["recognition_match_count"] == 1
    row, = result["mapping"]["enzyme_rows"]
    assert row["name"] == "EcoRI" and row["native_search_positions_1based"] == [6]
    position, = row["positions"]
    assert position["watson_boundary_0based"] == 5 and position["crick_boundary_0based"] == 9
    prior = read_published_restriction_result(store, selected["arguments"]["result_source_ref"],
        scope=selected["scope"])
    assert result["native"] == prior["native"] and result["mapping"] == prior["mapping"]


def test_replay_uses_archived_identity_without_execution(saved_job, monkeypatch):
    store, tools, selected, _ = saved_job
    monkeypatch.setattr(module, "_software", forbid)
    monkeypatch.setattr(tools, "_sequence", forbid)
    monkeypatch.setattr(RestrictionMappingJobs, "run_async", forbid)
    monkeypatch.setattr(RestrictionMappingJobs, "reserve", forbid)
    before = store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0]
    result = module.replay_restriction_work(tools, selected["tool_name"], selected["arguments"],
        scope=selected["scope"], operation_key=selected["operation_key"],
        permitted_record_refs=selected["permitted"])
    assert result == selected["outcome"]
    reservation = asyncio.run(module.prepare_restriction_work(tools, selected["tool_name"],
        selected["arguments"], scope=selected["scope"], operation_key=selected["operation_key"],
        permitted_record_refs=selected["permitted"]))
    assert reservation["operation_key"] == selected["operation_key"]
    assert store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == before


def test_actual_registry_cache_replay_without_catalog_injection(saved_job, monkeypatch):
    store, tools, selected, _ = saved_job
    assert selected["tool_name"] not in tools.catalog(selected["scope"])
    monkeypatch.setattr(module, "_software", forbid)
    monkeypatch.setattr(tools, "_sequence", forbid)
    monkeypatch.setattr(RestrictionMappingJobs, "run_async", forbid)
    before = store.db.total_changes
    outcome = asyncio.run(tools.execute_async(selected["tool_name"], selected["arguments"],
        scope=selected["scope"], operation_key=selected["operation_key"],
        permitted_record_refs=selected["permitted"]))
    assert outcome == selected["outcome"] and store.db.total_changes == before


def test_actual_registry_cache_denial_keeps_original_result(saved_job, monkeypatch):
    store, tools, selected, _ = saved_job
    before = store.db.execute("SELECT result FROM tool_operations WHERE operation_key=?",
        (selected["operation_key"],)).fetchone()[0]
    monkeypatch.setattr(module, "_software", forbid)
    monkeypatch.setattr(RestrictionMappingJobs, "run_async", forbid)
    changes = store.db.total_changes
    outcome = asyncio.run(tools.execute_async(selected["tool_name"], selected["arguments"],
        scope=selected["scope"], operation_key=selected["operation_key"], permitted_record_refs=[]))
    assert outcome["status"] == "invalid" and outcome["result"] is None
    assert outcome["record_refs"] == []
    assert outcome["feedback"]["code"] == "restriction_operand_not_received"
    assert store.db.execute("SELECT result FROM tool_operations WHERE operation_key=?",
        (selected["operation_key"],)).fetchone()[0] == before
    assert store.db.total_changes == changes


def test_reserved_publication_error_preserves_original_result_for_restore(saved_job, monkeypatch):
    store, tools, selected, _ = saved_job
    before = store.db.execute("SELECT result FROM tool_operations WHERE operation_key=?",
        (selected["operation_key"],)).fetchone()[0]
    def publication_error(*args, **kwargs):
        raise ContractError("engineering_publication_interruption")
    monkeypatch.setattr(tools_module, "publish_restriction_work", publication_error)
    monkeypatch.setattr(tools, "_save", forbid)
    monkeypatch.setattr(RestrictionMappingJobs, "run_async", forbid)
    token = tools._permitted_record_refs.set(tuple(selected["permitted"]))
    try:
        with pytest.raises(module.RestrictionOperationUnpublished, match="engineering_publication_interruption"):
            asyncio.run(tools._restriction_operation_async(selected["tool_name"],
                selected["arguments"], selected["scope"], selected["operation_key"]))
    finally:
        tools._permitted_record_refs.reset(token)
    assert store.db.execute("SELECT result FROM tool_operations WHERE operation_key=?",
        (selected["operation_key"],)).fetchone()[0] == before


@pytest.mark.parametrize("which", ["sequence", "prior", "all"])
def test_replay_requires_explicit_received_operands(saved_job, which):
    _, tools, selected, _ = saved_job
    permitted = [] if which == "all" else [selected["permitted"][1 if which == "sequence" else 0]]
    with pytest.raises(ContractError, match="restriction_operand_not_received"):
        module.replay_restriction_work(tools, selected["tool_name"], selected["arguments"],
            scope=selected["scope"], operation_key=selected["operation_key"], permitted_record_refs=permitted)


@pytest.mark.parametrize("field", ["alias", "arguments"])
def test_replay_cannot_rebind_an_original_operation(saved_job, field):
    _, tools, selected, _ = saved_job
    name, arguments = selected["tool_name"], deepcopy(selected["arguments"])
    if field == "alias":
        name = "find_restriction_enzymes"
    else:
        arguments["result_source_ref"] = selected["source_ref"]
    with pytest.raises(ContractError, match="restriction_operation_conflict"):
        module.replay_restriction_work(tools, name, arguments, scope=selected["scope"],
            operation_key=selected["operation_key"], permitted_record_refs=selected["permitted"])


def test_selected_saved_software_needs_no_current_bio(saved_job, monkeypatch):
    store, _, selected, _ = saved_job
    prior = read_published_restriction_result(store, selected["source_ref"], scope=selected["scope"])
    monkeypatch.setattr(module, "distribution", forbid)
    monkeypatch.setenv("UNRELATED_CREDENTIAL", "must-not-copy")
    software = module._software(store, "restriction728-unexecuted-metadata-only", mode="saved", prior=prior)
    assert "UNRELATED_CREDENTIAL" not in software["environment"]
    assert software["biopython_version"] == prior["native"]["software"]["biopython_version"]
    assert software["dictionary_file"] == prior["native"]["software"]["dictionary_file"]
    assert software["native_source_file"] == prior["native"]["software"]["native_source_file"]


def test_restriction_sources_grant_only_explicit_handles(saved_job):
    store, _, selected, _ = saved_job
    receipts = EpisodeReceipts(store, "restriction728-custody")
    receipts.bind("parent")
    source = store.get(selected["source_ref"])
    receipts.receive("parent", [source["id"]], kind="child_form", source_index=0)
    assert set(receipts.known("parent")) == {source["id"]}
    receipts.bind("child", "parent")
    artifact = source["text_ref"]
    receipts.receive("parent", [artifact], kind="own_action", source_index=1)
    assert set(receipts.known("parent")) == {source["id"], artifact}
    assert set(receipts.known("child")) == {source["id"]}


def test_both_custody_pairs_are_exact_and_rollback(tmp_path):
    with Store(tmp_path / "engineering") as store:
        store.create_problem(raw_sequence="ACGT", molecule="dna")
        receipts = EpisodeReceipts(store, "restriction728-exact-custody")
        for index, (provider, version, restricted) in enumerate([
            ("episode.restriction_input", "restriction_input_source_v1", True),
            ("episode.restriction_result", "restriction_published_result_v1", True),
            ("episode.restriction_input", "other_version", False),
            ("another_provider", "restriction_published_result_v1", False),
        ]):
            artifact = store.artifact(f"engineering source bytes {index}")
            source = store.put("source", {"provider": provider, "accession": None, "uri": None,
                "artifact_ref": artifact, "text_ref": None, "request_ref": None,
                "version": version, "retrieved_at": None}, origin="tool")
            episode = str(index)
            receipts.bind(episode)
            with pytest.raises(RuntimeError, match="rollback"):
                with store.transaction():
                    receipts.receive(episode, [source["id"]], kind="initial")
                    raise RuntimeError("rollback")
            assert set(receipts.known(episode)) == set()
            receipts.receive(episode, [source["id"]], kind="initial")
            assert set(receipts.known(episode)) == ({source["id"]} if restricted else {source["id"], artifact})
