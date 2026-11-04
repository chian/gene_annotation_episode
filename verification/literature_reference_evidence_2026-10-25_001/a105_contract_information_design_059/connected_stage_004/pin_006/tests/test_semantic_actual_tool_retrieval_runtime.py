"""Selected FAST retrieval -> actual multi-tool child -> original form and replay.

The provider decisions/controllers and tiny A entry are engineering fixtures.
Store operations, callable contracts, workflow, receipts and forms are actual.
"""
import asyncio
from copy import deepcopy
import json
import shutil

import pytest

from gene_annotation_episode.episode_composition import reopen_scientific_binding
from gene_annotation_episode.providers import ModelRole
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.scientific_tool_retrieval import ScientificToolRetriever
from gene_annotation_episode.state import Store
from test_actual_tool_retriever_runtime import ActualToolCase, action, FORM, GOAL, INVESTIGATION
from test_runtime import ScriptedProvider
from test_semantic_actual_tool_retrieval import CONFIG


SELECTED = ["sequence.inspect", "translation.codes"]


class MixedProvider(ScriptedProvider):
    roles = {"FAST": ModelRole("gpt-6-luna", "none")}

    def __init__(self, script, selections=()):
        super().__init__(script)
        self.selections, self.retrieval_calls = iter(selections), []

    async def complete(self, episode_id, role, instructions, context, output_schema):
        if role == "REASONING":
            return await super().complete(episode_id, role, instructions, context, output_schema)
        assert role == "FAST" and episode_id.startswith("scientific_tool_retrieval_")
        self.retrieval_calls.append(deepcopy({"identity": episode_id, "context": context,
            "schema": output_schema, "instructions": instructions}))
        response = next(self.selections)
        return deepcopy(response)


def semantic_case(tmp_path, store, *, stops=None):
    case = ActualToolCase(tmp_path, store, stops=stops)
    assert case.descriptor["version"] == "scientific_process_episodes_v5"
    assert set(case.descriptor["configuration"]) == {"library", "tool_library", "child_roles"}
    case.descriptor = prepare_scientific_binding(run_directory=case.directory,
        source_directory=case.source, tool_catalog=case.tools.catalog(),
        child_roles=["scientific_process"], tool_retrieval=CONFIG)
    return case


def test_selected_semantic_multi_tool_child_dispatch_form_and_restore(tmp_path):
    with Store(tmp_path / "state") as store:
        case = semantic_case(tmp_path, store, stops={1: 3, 2: 2})
        selected_requests, forms = [], []

        def commission(context):
            result = context["last_local_outcome"]
            assert result["status"] == "completed"
            assert result["record_refs"] == result["changed_record_refs"] == []
            assert result["result"]["tools"] == SELECTED
            selection = case.commission(result["result"]["tools"])
            selected_requests.append(deepcopy(selection))
            return selection

        def dispatch(context):
            assert context["scientific_process"]["selection"] == case.selection(SELECTED)
            assert context["requested_form"] == FORM
            names = {entry["name"] for entry in context["tools"]}
            assert set(SELECTED) <= names and "public.pubmed.search" not in names
            return action("sequence.inspect", {"subject_ref": case.target}, "unresolved")

        def receive(context):
            forms.extend(deepcopy(context["child_reports"]))
            assert forms == [{"status": "measured", "records": forms[0]["records"]}]
            assert len(forms[0]["records"]) == 2
            return action("episode.history", {"view": "index"})

        provider = MixedProvider([
            action("process.tools", {"investigation": INVESTIGATION}), commission, dispatch,
            action("translation.codes", {}, "measured"), receive], [{"tools": SELECTED}])
        workflow = case.workflow(provider)
        root = workflow.build("annotation", "root", GOAL, case.scope)
        closed = asyncio.run(root.run_async(workflow.context))
        asyncio.run(root.build_result(closed))
        assert len(provider.retrieval_calls) == 1
        retrieval = provider.retrieval_calls[0]
        assert retrieval["context"]["catalog"] == workflow.scientific_process_binding.tool_library.catalog()
        assert retrieval["identity"] in provider.released
        assert retrieval["identity"] != root.source.episode_id
        assert [controller.scores for _, controller in case.controllers] == [[0, 0, 0], [0, 0]]
        assert store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == 5
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 5
        assert store.db.execute("SELECT count(*) FROM runtime_model_calls").fetchone()[0] == 5
        assert store.db.execute("SELECT count(*) FROM runtime_episodes").fetchone()[0] == 2
        assert [row[0] for row in store.db.execute("SELECT name FROM tool_operations ORDER BY name")] == SELECTED
        child = store.db.execute("SELECT * FROM runtime_episodes WHERE json_array_length(path)=2").fetchone()
        original_request = json.loads(child["request"])
        original_cache = tuple(store.db.execute("SELECT * FROM runtime_tool_retrievals").fetchone())
        assert json.loads(original_cache[4])["owner"]["episode_id"] == root.source.episode_id
        shutil.rmtree(case.source)
        restored_provider = MixedProvider([])
        restored = case.workflow(restored_provider)
        assert restored.scientific_process_binding.as_record() == case.descriptor
        assert restored.scientific_process_binding.tool_retrieval == CONFIG
        restored_root = restored.build("annotation", "root", GOAL, case.scope)
        restored_child = restored.selected(restored_root.source, selected_requests[0]["selection"], 1).child
        assert restored_child.request.as_record() == original_request
        assert restored_child.request.report_contract.schema == FORM
        assert asyncio.run(restored.execute(restored_root.source, "process.tools",
            {"investigation": INVESTIGATION}, decision_index=0,
            operation_key=f"{restored.run_id}:{restored_root.source.episode_id}:0"))["result"]["tools"] == SELECTED
        assert not restored_provider.retrieval_calls
        assert tuple(store.db.execute("SELECT * FROM runtime_tool_retrievals").fetchone()) == original_cache


def test_cache_publication_then_action_journal_interruption_restores_without_fast_call(tmp_path, monkeypatch):
    with Store(tmp_path / "state") as store:
        case = semantic_case(tmp_path, store, stops={1: 1, 2: 2})
        initial_records = [tuple(row) for row in store.db.execute("SELECT * FROM records ORDER BY id")]
        first = MixedProvider([action("process.tools", {"investigation": INVESTIGATION})],
            [{"tools": SELECTED}])
        publish = ScientificToolRetriever._publish
        with monkeypatch.context() as interruption:
            def publish_then_interrupt(*args, **kwargs):
                publish(*args, **kwargs)
                raise KeyboardInterrupt()
            interruption.setattr(ScientificToolRetriever, "_publish", publish_then_interrupt)
            with pytest.raises(KeyboardInterrupt):
                case.run(first)
        cache = tuple(store.db.execute("SELECT * FROM runtime_tool_retrievals").fetchone())
        assert json.loads(cache[-1])["status"] == "completed"
        assert store.db.execute("SELECT result FROM runtime_actions").fetchone()[0] is None
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0
        resumed = MixedProvider([])
        result = case.run(resumed, resume=True)
        assert result["completed_actions"] == 1 and result["credit"] == 0
        assert not resumed.retrieval_calls and not resumed.contexts
        assert store.db.execute("SELECT count(*) FROM runtime_model_calls").fetchone()[0] == 1
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 1
        assert tuple(store.db.execute("SELECT * FROM runtime_tool_retrievals").fetchone()) == cache
        assert [tuple(row) for row in store.db.execute("SELECT * FROM records ORDER BY id")] == initial_records
        assert not store.list("observation")


def test_invalid_fast_output_does_not_complete_an_action_or_construct_child(tmp_path):
    with Store(tmp_path / "state") as store:
        case = semantic_case(tmp_path, store, stops={1: 1, 2: 2})

        def repair(context):
            assert context["last_local_outcome"]["status"] == "invalid"
            assert context["feedback"]["code"] == "scientific_tool_retrieval_output_invalid"
            return action("episode.history", {"view": "index"})

        result = case.run(MixedProvider([
            action("process.tools", {"investigation": INVESTIGATION}), repair],
            [{"tools": ["hallucinated.tool"]}]))
        assert result["completed_actions"] == 1
        assert store.db.execute("SELECT count(*) FROM runtime_episodes").fetchone()[0] == 1
        assert store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == 2
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 1
        assert store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 0
        assert not store.list("observation") and not store.list("assessment")


def test_v6_reconstruction_requires_explicit_mode_and_preserves_model_identity(tmp_path):
    with Store(tmp_path / "state") as store:
        case = semantic_case(tmp_path, store)
        assert case.descriptor["version"] == "scientific_process_episodes_v6"
        reopened = reopen_scientific_binding(None, descriptor=case.descriptor,
            directory=case.directory)
        assert reopened.tool_retrieval == CONFIG and reopened.as_record() == case.descriptor
        from method_loop.durable import DurableExecutionError
        changed_model = deepcopy(case.descriptor)
        changed_model["configuration"]["tool_retrieval"]["model"]["model"] = "other"
        # An isolated caller may explicitly construct another valid binding.
        # It has a different descriptor; the saved run/commission pin below
        # prevents substituting it into an existing investigation.
        other = reopen_scientific_binding(None, descriptor=changed_model, directory=case.directory)
        assert other.as_record() != reopened.as_record()
        for mutate in (lambda value: value["configuration"].pop("tool_retrieval"),
                       lambda value: value.update(version="scientific_process_episodes_v5")):
            changed = deepcopy(case.descriptor)
            mutate(changed)
            with pytest.raises(DurableExecutionError):
                reopen_scientific_binding(None, descriptor=changed, directory=case.directory)


def test_actual_worker_factory_reconstructs_semantic_binding_without_retrieval(tmp_path, monkeypatch):
    import test_scientific_process_reconstruction as reconstruction
    prepare = reconstruction.prepare_scientific_binding
    monkeypatch.setattr(reconstruction, "prepare_scientific_binding",
        lambda **kwargs: prepare(**kwargs, tool_retrieval=CONFIG))
    saved = reconstruction.persist_scientific_run(tmp_path, monkeypatch)
    spec = reconstruction.commission_fixture(saved)
    shutil.rmtree(saved["source"])
    events = reconstruction.provider_fixture(monkeypatch)

    async def reopen():
        async with reconstruction.independent.open_commission(spec) as actual:
            child = actual["episode"]
            workflow = child.source.workflow
            assert child.request.as_record() == spec["child"]["request"]
            assert workflow.scientific_process_binding.tool_retrieval == CONFIG
            assert workflow.scientific_tool_retriever.configuration == CONFIG
            assert workflow.episode_bindings.as_record() == [saved["descriptor"]]
            assert workflow.journal.db.execute("SELECT count(*) FROM runtime_tool_retrievals").fetchone()[0] == 0
            assert workflow.journal.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0
    asyncio.run(reopen())
    assert [kind for kind, _ in events] == ["constructed", "entered", "released", "exited"]


def test_actual_worker_rejects_replacement_model_against_original_commission_pin(tmp_path, monkeypatch):
    import test_scientific_process_reconstruction as reconstruction
    prepare = reconstruction.prepare_scientific_binding
    monkeypatch.setattr(reconstruction, "prepare_scientific_binding",
        lambda **kwargs: prepare(**kwargs, tool_retrieval=CONFIG))
    saved = reconstruction.persist_scientific_run(tmp_path, monkeypatch)
    spec = reconstruction.commission_fixture(saved)
    manifest = json.loads((saved["directory"] / "run.json").read_text())
    manifest["episode_bindings"][0]["configuration"]["tool_retrieval"]["model"]["model"] = "other"
    with Store(saved["workspace"]) as store:
        store.db.execute("UPDATE runtime_runs SET settings=? WHERE run_id=?", (
            json.dumps({key: value for key, value in manifest.items() if key != "run_id"}),
            manifest["run_id"]))
    (saved["directory"] / "run.json").write_text(json.dumps(manifest))
    events = reconstruction.provider_fixture(monkeypatch)

    async def reopen():
        async with reconstruction.independent.open_commission(spec):
            pytest.fail("the original settings pin must reject a replacement model")
    from method_loop.durable import DurableExecutionError
    with pytest.raises(DurableExecutionError) as error:
        asyncio.run(reopen())
    assert error.value.failure["code"] == "identity_conflict"
    assert not events
