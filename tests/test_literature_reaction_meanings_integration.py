"""Constructed A110 source meanings in ordinary child/parent iteration and replay."""
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
from gene_annotation_episode.literature_reaction_storage import reaction_semantic_cells_schema
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt, _steering
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.tools import ToolRegistry
from test_literature_reaction_meanings import semantic_fixture, reopen_read_only
from test_runtime import FixtureController, ScriptedProvider


def test_actual_selected_delivery_named_models_resources_and_first_readonly_display(tmp_path, monkeypatch):
    store, context, args, sources, _ = semantic_fixture(tmp_path / "state")
    with store:
        extras = []
        for index in range(40):
            extras.append(store.put("reference", {"reference_type": "literature_result",
                "source_ref": sources["root"]["id"], "accession": "constructed_extra_" + str(index),
                "label": "Unselected constructed record " + str(index), "sequence_ref": None,
                "molecule": None, "length": None, "term_refs": [], "context_refs": [],
                "anchor": None}, origin="caller")["id"])
        assignment = {"version": "literature_assignment_v1", "question_context_refs": [],
            "source_refs": list(context.received_record_refs), "requested_reaction_components": ["reaction_comparison"]}
        form = obj({"chosen_reaction": reaction_semantic_cells_schema()})
        captured = {}
        empty = {name: [] for name in store.reasoning_schema()["required"]}
        root = sources["root"]
        quote = store.get_artifact(root["artifact_ref"]).decode()
        def next_action(inputs, kind):
            captured[kind] = deepcopy(inputs)
            rendered = render_literature_experimental_prompt(inputs, "Constructed reaction investigation")
            task, steering = rendered.split("\n\nSTEERING\n", 1)
            if kind == "own": assert "For the actual claim and each genuine alternative" in task
            for scientific in ("Balanced reaction model", "Alternative bypass model", "Alternative side reaction",
                               "Alternative coupled reaction", "glucose", "NADH", "P formation", "one-minute assay"):
                assert scientific in steering
            for heading in ("Reaction models and predictions", "Reaction comparison membership",
                            "Reaction resource demand", "Reaction resource constraints"):
                assert steering.count(heading) == 1
            for private in ("private-second", "private-near", "reaction_literal_", "literature_measurement_"):
                assert private not in steering
            if kind == "parent":
                received, = inputs["child_reports"]
                rows = received["chosen_reaction"]
                assert [r["component"] for r in rows] == ["reaction_comparison"]
                assert abs(rows[0]["value"] + 3 / 7) < 1e-12
                assert inputs["working_state"]["pages"]["references"]["total"] > 24
                known = inputs["literature_received_fact_display"]["records"]
                working = {r["id"] for r in inputs["working_state"]["references"]}
                meanings = [r["model_ref"] for r in rows[0]["model_definitions"]]
                assert any(ref not in working and ref in known for ref in meanings)
                assert all(r["coefficient_demand_ref"] == rows[0]["demand_definition"]["demand_ref"]
                    for r in rows[0]["resource_definitions"])
            commit = deepcopy(empty)
            commit["source_subjects"] = [{"alias": kind, "reference_type": "assay", "source_ref": root["id"],
                "label": "reaction" if kind == "own" else "experiment", "anchor": {
                    "source_ref": root["id"], "artifact_ref": root["artifact_ref"],
                    "start": 0, "end": len(quote.encode()), "quote": quote}}]
            return {"selection": {"kind": "reason", "commit": commit}, "report_update": {}}
        provider = ScriptedProvider([
            {"selection": {"kind": "episode_child", "role": "literature", "assignment": assignment,
                "goal": "Evaluate the constructed reaction alternatives and resource constraints",
                "scope": plain(context.scope), "purpose": "Return selected comparison with its actual scientific meanings",
                "schema_json": json.dumps(form), "initial_report_json": "{}"}, "report_update": {}},
            {"selection": {"kind": "tool", "tool": "literature.reaction.populate", "arguments": args}, "report_update": {}},
            lambda inputs: next_action(inputs, "own"), lambda inputs: next_action(inputs, "parent")])
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        result = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider, run_dir=tmp_path / "run",
            controller_factory=lambda path, initial: FixtureController(str(path), initial, 2),
            project_credit=scorer, initial_known_record_refs=[*context.received_record_refs, *extras],
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
                reference_parent_sources=[root["id"]]),), binding_definitions={"credit": scorer.as_record()}))
        assert set(captured) == {"own", "parent"}
        observed = [dict(row) for row in store.db.execute("select * from runtime_observations")]
        assert len(observed) == 4
        assert store.db.execute("select count(*) from literature_reaction_operations").fetchone()[0] == 1
        assert store.db.execute("select count(*) from literature_reaction_semantic_received").fetchone()[0] == 1
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
        def forbidden(*args, **kwargs): raise AssertionError("readonly display reacquired or mutated scientific data")
        for name in ("get_artifact", "artifact", "put", "transaction", "commit_reasoning"): monkeypatch.setattr(store, name, forbidden)
        monkeypatch.setattr("gene_annotation_episode.providers.ModelConnection", forbidden)
        monkeypatch.setattr("gene_annotation_episode.literature_reaction_storage.read_reaction_inputs", forbidden)
        monkeypatch.setattr("gene_annotation_episode.literature_reaction_storage.populate_reaction_constraints", forbidden)
        binding = LiteratureEpisodes(WorkflowServices(SimpleNamespace(store=store, run_id=result["run_id"])), rate_population=True)
        restored = binding._received_fact_display_context(parent)
        assert restored["literature_received_fact_display"]["records"] == expected
        state = {**captured["parent"], **restored, "working_state": {}}
        text = _steering(state, ())
        assert "Alternative bypass model" in text and "NADH" in text and "P formation" in text
        missing = next(ref for ref, record in expected.items() if record.get("label") == "NADH")
        lesser = binding._received_fact_display_context(replace(parent,
            received_record_refs=tuple(ref for ref in parent.received_record_refs if ref != missing)))
        assert missing not in lesser["literature_received_fact_display"]["records"]
        assert "meaning unavailable in the received scientific records" in _steering({**state, **lesser}, ())
        assert store.db.total_changes == 0
        assert [dict(row) for row in store.db.execute("select * from runtime_observations")] == observed
        assert json.loads(store.db.execute("select form from runtime_report_attempts").fetchone()[0]) == captured["parent"]["child_reports"][0]
