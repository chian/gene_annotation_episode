"""One saved-only host job from retained native data; no catalog installation."""
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path

import pytest
from method_loop.identities import EpisodeRef

from gene_annotation_episode.domain import ContractError, canonical
from gene_annotation_episode.episodic_workflow.root.episode_journal import Journal
from gene_annotation_episode.episodic_workflow.root.episode_receipts import EpisodeReceipts
from gene_annotation_episode.restriction_mapping_jobs import RestrictionMappingJobs
from gene_annotation_episode.restriction_mapping_publication import read_published_restriction_result
from gene_annotation_episode.restriction_mapping_returns import restriction_mapping_fact_sources
from gene_annotation_episode import restriction_mapping_registry as module
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.tool_registry import ToolRegistry
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
