"""Constructed A108 meanings through actual ordinary iteration and delivery."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import json
from types import SimpleNamespace

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_context_storage import context_semantic_cells_schema
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt, _steering
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.tools import ToolRegistry
from test_literature_context_meanings import semantic_fixture, reopen_read_only
from test_runtime import FixtureController, ScriptedProvider


def test_actual_own_parent_subset_and_first_readonly_scientific_reconstruction(tmp_path, monkeypatch):
    store, context, args, sources, _ = semantic_fixture(tmp_path / "state")
    with store:
        # Parent knows more than one working-state page of scientific records.
        # They remain irrelevant to the selected requirement/route display.
        extras = []
        for index in range(40):
            extras.append(store.put("reference", {"reference_type": "literature_result",
                "source_ref": sources["root"]["id"], "accession": "constructed_extra_" + str(index),
                "label": "Unselected constructed record " + str(index), "sequence_ref": None,
                "molecule": None, "length": None, "term_refs": [], "context_refs": [],
                "anchor": None}, origin="caller")["id"])
        assignment = {"version": "literature_assignment_v1", "question_context_refs": [],
            "source_refs": list(context.received_record_refs), "requested_context_components": ["selected_point"]}
        form = obj({"chosen_context": context_semantic_cells_schema()})
        captured = {}
        empty = {name: [] for name in store.reasoning_schema()["required"]}
        root = sources["root"]
        quote = store.get_artifact(root["artifact_ref"]).decode()
        def next_action(inputs, kind):
            captured[kind] = deepcopy(inputs)
            text = render_literature_experimental_prompt(inputs, "Constructed contextual investigation")
            task, steering = text.split("\n\nSTEERING\n", 1)
            assert "For every actual requirement" in task if kind == "own" else "actual caller question" in task
            for scientific in ("glucose", "nitrate", "cytosol", "periplasm", "Joint assimilation route", "Alternative acceptor route"):
                assert scientific in steering
            assert steering.count("Context operating requirements") == 1
            assert steering.count("Alternative biological routes") == 1
            for private in ("private-a", "private-b", "private-route", "context_literal_", "literature_measurement_"):
                assert private not in steering
            if kind == "parent":
                received, = inputs["child_reports"]
                assert [row["component"] for row in received["chosen_context"]] == ["selected_point"]
                assert received["chosen_context"][0]["value"] == .5
                assert inputs["working_state"]["pages"]["references"]["total"] > 24
                known = inputs["literature_received_fact_display"]["records"]
                working = {r["id"] for r in inputs["working_state"]["references"]}
                meanings = [r["route_ref"] for r in received["chosen_context"][0]["route_definitions"]]
                assert any(ref not in working and ref in known for ref in meanings)
            commit = deepcopy(empty)
            commit["source_subjects"] = [{"alias": kind, "reference_type": "assay", "source_ref": root["id"],
                "label": "context" if kind == "own" else "experiment", "anchor": {
                    "source_ref": root["id"], "artifact_ref": root["artifact_ref"],
                    "start": 0, "end": len(quote), "quote": quote}}]
            return {"selection": {"kind": "reason", "commit": commit}, "report_update": {}}
        provider = ScriptedProvider([
            {"selection": {"kind": "episode_child", "role": "literature", "assignment": assignment,
                "goal": "Evaluate the constructed context requirements and genuine alternatives",
                "scope": plain(context.scope), "purpose": "Return only selected contextual coverage with actual meanings",
                "schema_json": json.dumps(form), "initial_report_json": "{}"}, "report_update": {}},
            {"selection": {"kind": "tool", "tool": "literature.context.populate", "arguments": args}, "report_update": {}},
            lambda inputs: next_action(inputs, "own"), lambda inputs: next_action(inputs, "parent")])
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        result = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider, run_dir=tmp_path / "run",
            controller_factory=lambda path, initial: FixtureController(str(path), initial, 2),
            project_credit=scorer, initial_known_record_refs=[*context.received_record_refs, *extras],
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
                reference_parent_sources=[root["id"]]),), binding_definitions={"credit": scorer.as_record()}))
        assert set(captured) == {"own", "parent"}
        observation_rows = [dict(row) for row in store.db.execute("select * from runtime_observations")]
        assert len(observation_rows) == 4
        assert store.db.execute("select count(*) from literature_context_operations").fetchone()[0] == 1
        assert store.db.execute("select count(*) from literature_context_semantic_received").fetchone()[0] == 1
        assert not store.list("observation") and not store.list("assessment")
        attempt, = store.db.execute("select * from runtime_report_attempts").fetchall()
        assert json.loads(attempt["form"]) == captured["parent"]["child_reports"][0]
        parent_row = store.db.execute("select * from runtime_episodes where json_array_length(path)=1").fetchone()
        request = json.loads(parent_row["request"])
        parent = BindingContext(result["run_id"], parent_row["episode_id"], "annotation",
            tuple(tuple(p) for p in json.loads(parent_row["path"])), plain(context.scope), {}, request,
            tuple(captured["parent"]["literature_received_fact_display"]["received_refs"]))
        expected = captured["parent"]["literature_received_fact_display"]["records"]
        reopen_read_only(store)
        def forbidden(*args, **kwargs): raise AssertionError("read-only meaning reconstruction acquired or mutated data")
        for name in ("get_artifact", "artifact", "put", "transaction", "commit_reasoning"):
            monkeypatch.setattr(store, name, forbidden)
        monkeypatch.setattr("gene_annotation_episode.providers.ModelConnection", forbidden)
        monkeypatch.setattr("gene_annotation_episode.literature_context_storage.read_context_inputs", forbidden)
        monkeypatch.setattr("gene_annotation_episode.literature_context_storage.populate_context_compatibility", forbidden)
        binding = LiteratureEpisodes(WorkflowServices(SimpleNamespace(store=store, run_id=result["run_id"])), rate_population=True)
        restored = binding._received_fact_display_context(parent)
        assert restored["literature_received_fact_display"]["records"] == expected
        state = {**captured["parent"], **restored, "working_state": {}}
        text = _steering(state, ())
        assert "glucose" in text and "nitrate" in text and "Alternative acceptor route" in text
        missing = next(ref for ref, record in expected.items() if record.get("label") == "nitrate")
        lesser = binding._received_fact_display_context(replace(parent,
            received_record_refs=tuple(ref for ref in parent.received_record_refs if ref != missing)))
        assert missing not in lesser["literature_received_fact_display"]["records"]
        assert "meaning unavailable in the received scientific records" in _steering({**state, **lesser}, ())
        assert store.db.total_changes == 0
        assert [dict(row) for row in store.db.execute("select * from runtime_observations")] == observation_rows
        assert json.loads(store.db.execute("select form from runtime_report_attempts").fetchone()[0]) == captured["parent"]["child_reports"][0]
