"""Controlled shared-loop native rate execution, typed repair and presentation."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import json

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.decision_context import state_frame
from gene_annotation_episode.domain import obj
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_rate_storage import rate_cells_schema, rate_source_cells_schema
from gene_annotation_episode.literature_experimental_contracts import HEADERS
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.tools import ToolRegistry
from test_literature_experimental_prompt_delivery import LiteratureWire, complete, snapshot
from test_literature_rate_episode_integration import service_binding
from test_literature_rate_native_storage import setup_native_store
from test_runtime import FixtureController, ScriptedProvider


COMPONENTS = ["rate_difference", "difference_se"]


def parent_reason(store, source_ref):
    source = store.get(source_ref)
    raw = store.get_artifact(source["artifact_ref"])
    commit = {name: [] for name in store.reasoning_schema()["required"]}
    commit["source_subjects"] = [{"alias": "examined_reference", "reference_type": "assay",
        "source_ref": source_ref, "label": "enzyme Alpha", "anchor": {
            "source_ref": source_ref, "artifact_ref": source["artifact_ref"],
            "start": 0, "end": len(raw), "quote": raw.decode()}}]
    return {"selection": {"kind": "reason", "commit": commit}, "report_update": {}}


@pytest.mark.parametrize("repair_legacy,defined,bounded", [(False, False, False), (True, False, False),
    (False, True, False), (True, True, False), (False, False, True)])
def test_selected_native_population_crosses_native_return_or_repairs_legacy_admission_without_repeating_work(tmp_path, repair_legacy, defined, bounded):
    store, context, args = setup_native_store(tmp_path / "state", defined=defined,
        reference="< approximately 12" if bounded else None)
    try:
        native_form = obj({"caller_chosen_native_results": rate_source_cells_schema()})
        first_form = obj({"legacy_request": rate_cells_schema()}) if repair_legacy else native_form
        requested = ["reference_rate"] if bounded else COMPONENTS
        assignment = {**plain(context.assignment), "requested_rate_components": requested}
        commissions = {"selection": {"kind": "episode_child", "role": "literature",
            "assignment": assignment, "goal": "Compare the source rates while retaining distinct constructs.",
            "scope": plain(context.scope), "purpose": "Return requested source-rate cells and limitations.",
            "schema_json": json.dumps(first_form), "initial_report_json": "{}"}, "report_update": {}}
        population = {"selection": {"kind": "tool", "tool": "literature.rate.source.populate", "arguments": args}, "report_update": {}}
        received, controllers, preserved = [], [], {}
        def repair(inputs):
            assert inputs["feedback"]["kind"] == "report_delivery_failure"
            assert inputs["feedback"]["reason"] == "literature_rate_projection_version_mismatch"
            assert inputs["child_reports"] == []
            assert store.db.execute("select count(*) from literature_rate_operations").fetchone()[0] == 1
            rows = store.db.execute("select * from runtime_actions where json_extract(action,'$.tool')='literature.rate.source.populate'").fetchall()
            assert len(rows) == 1 and json.loads(rows[0]["result"])["status"] == "completed"
            assert rows[0]["credit"] == 0
            preserved["action"] = tuple(rows[0])
            preserved["child"] = rows[0]["episode_id"]
            preserved["observations"] = [tuple(r) for r in store.db.execute("select * from runtime_observations where episode_id=?", (preserved["child"],))]
            assert len(preserved["observations"]) == 1
            return {"selection": {"kind": "redeliver_report", "delivery_ref": inputs["feedback"]["delivery_ref"],
                "purpose": "Read the original native source-rate projection with its arm identities.",
                "schema_json": json.dumps(native_form)}, "report_update": {}}
        def integrate(inputs):
            report, = inputs["child_reports"]
            cells = report["caller_chosen_native_results"]
            assert [row["component"] for row in cells] == requested
            if bounded:
                assert cells[0]["value"] is None and cells[0]["threshold"] == pytest.approx(.012)
                assert cells[0]["bound"] == "lt" and cells[0]["approximate"] is True
            else:
                assert cells[0]["value"] == pytest.approx(13.9 if defined else .009)
                assert cells[1]["value"] is None
                assert all(row["threshold"] is None and row["bound"] == "none" for row in cells)
            assert cells[0]["assayed_subject_ref"] is None
            assert store.get(cells[0]["reference_construct_ref"])["label"] == "WT"
            assert store.get(cells[0]["test_construct_ref"])["label"] == "variant"
            assert cells[0]["approximate"] is bounded
            received.append(report)
            return parent_reason(store, args["source_ref"])
        script = [commissions, population, *([repair] if repair_legacy else []), integrate]
        provider = ScriptedProvider(script)
        def controller(path, initial):
            value = FixtureController(str(path), initial, 2 if len(path) == 1 else 1)
            controllers.append(value)
            return value
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        result = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider,
            run_dir=tmp_path / "run", controller_factory=controller, project_credit=scorer,
            initial_known_record_refs=[args["source_ref"]],
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True),),
            binding_definitions={"credit": scorer.as_record()}))
        assert result["credit"] == 0 and len(received) == 1
        assert [c.scores for c in controllers] == [[0, 0], [0]]
        assert store.db.execute("select count(*) from runtime_observations").fetchone()[0] == 3
        assert store.db.execute("select count(*) from literature_rate_operations").fetchone()[0] == 1
        assert store.db.execute("select count(*) from literature_rate_source_received").fetchone()[0] == 1
        assert store.db.execute("select count(*) from literature_rate_received").fetchone()[0] == 0
        assert store.db.execute("select count(*) from runtime_report_attempts").fetchone()[0] == 1 + int(repair_legacy)
        assert not store.list("observation") and not store.list("assessment")
        if repair_legacy:
            row, = store.db.execute("select * from runtime_actions where json_extract(action,'$.tool')='literature.rate.source.populate'").fetchall()
            assert tuple(row) == preserved["action"]
            assert [tuple(r) for r in store.db.execute("select * from runtime_observations where episode_id=?", (preserved["child"],))] == preserved["observations"]
            facts, = store.db.execute("select facts from runtime_forms").fetchall()
            assert json.loads(facts[0])["literature_rate_cells"] == []
            assert json.loads(facts[0])["literature_rate_source_cells"] == received[0]["caller_chosen_native_results"]
    finally:
        store.close()


@pytest.mark.parametrize("bounded", [False, True])
def test_actual_provider_text_preserves_native_bindings_and_approximation_across_delta_and_restart(tmp_path, bounded):
    store, context, args = setup_native_store(tmp_path / "state", approximate=not bounded,
        reference="< approximately 12" if bounded else None)
    try:
        services, binding = service_binding(store, context)
        outcome = asyncio.run(binding.execute(context, "literature.rate.source.populate", args, "selected"))
        assert outcome["status"] == "completed"
        current = replace(context, received_record_refs=(*context.received_record_refs, *outcome["record_refs"]),
            assignment={**plain(context.assignment), "requested_rate_components": ["reference_rate"]})
        facts = binding.facts(current, {"committed_record_refs": outcome["record_refs"]})
        assert facts["literature_rate_cells"] == []
        cells = facts["literature_rate_source_cells"]
        first = snapshot()
        first["requested_form"] = obj({"native_components": rate_source_cells_schema()})
        first["available_report_facts"] = binding.fact_sources("literature")
        first["literature_assignment"] = plain(context.assignment)
        first["literature_source_custody"] = []
        first["last_local_outcome"] = outcome
        records = [store.get(ref) for ref in outcome["record_refs"]]
        first["working_state"].update(references=[r for r in records if r["record_type"] == "reference"],
            contexts=[r for r in records if r["record_type"] == "context"],
            terms=[r for r in records if r["record_type"] == "term"])
        second = deepcopy(first)
        second["last_local_outcome"] = None
        second["child_reports"] = [{"native_components": cells}]
        wire, restarted = LiteratureWire(tmp_path / "wire"), LiteratureWire(tmp_path / "restarted")
        async def exercise():
            await complete(wire, state_frame(first))
            await complete(wire, state_frame(second, first))
            await complete(restarted, state_frame(second))
        asyncio.run(exercise())
        for transport in (wire, restarted):
            for turn in transport.turns_sent():
                task, steering = turn["input"][0]["text"].split("\n\nSTEERING\n", 1)
                assert "recorded fact from literature_rate_source_cells" in task
                assert "enzyme Alpha" in steering and "enzyme Beta" in steering
                assert "WT" in steering and "variant" in steering
                assert "approximate" in steering and "true" in steering
                assert "native_rate_" not in task + steering
                for name in ("reference_subject_ref", "test_construct_ref", "reference_preparation_ref"):
                    assert name in task
        for turn in [wire.turns_sent()[-1], restarted.turns_sent()[0]]:
            steering = turn["input"][0]["text"].split("\n\nSTEERING\n", 1)[1]
            assert "Native source-rate comparison" in steering
            assert "Reference and test meanings" in steering
            assert "Arm | Subject | Construct | Preparation | Condition" in steering
            assert "Reference | enzyme Alpha | WT | prepR" in steering
            assert "Test | enzyme Beta | variant | prepT" in steering
        assert "native_rate_subject_" not in wire.turns_sent()[-1]["input"][0]["text"]
        if bounded:
            assert len(cells) == 1 and cells[0]["threshold"] == pytest.approx(.012)
            assert cells[0]["bound"] == "lt" and cells[0]["value"] is None
            for transport in (wire, restarted):
                for turn in transport.turns_sent():
                    steering = turn["input"][0]["text"].split("\n\nSTEERING\n", 1)[1]
                    assert "0.012" in steering
                    assert (("threshold" in steering and "bound" in steering and "lt" in steering)
                            or ("Bound | Threshold" in steering and "< | 0.012" in steering))
            for turn in (wire.turns_sent()[-1], restarted.turns_sent()[0]):
                text = turn["input"][0]["text"].split("\n\nSTEERING\n", 1)[1]
                assert "Bound | Threshold" in text and "< | 0.012" in text
                assert "0.003" not in text
    finally:
        store.close()


@pytest.mark.parametrize("numerical_none", [True, False])
def test_native_intermediate_work_survives_no_numeric_request_or_explicit_empty_component_request(tmp_path, numerical_none):
    store, context, args = setup_native_store(tmp_path / "state")
    try:
        form = (obj({"interpretation": {"type": "string", "enum": ["unresolved", "source_compared"]}})
                if numerical_none else obj({"empty_request": rate_cells_schema()}))
        initial = {"interpretation": "unresolved"} if numerical_none else {}
        assignment = plain(context.assignment)
        if not numerical_none:
            assignment["requested_rate_components"] = []
        def receive(inputs):
            report, = inputs["child_reports"]
            assert report == ({"interpretation": "source_compared"} if numerical_none else {"empty_request": []})
            return parent_reason(store, args["source_ref"])
        provider = ScriptedProvider([
            {"selection": {"kind": "episode_child", "role": "literature", "assignment": assignment,
                "goal": "Examine the synthetic rate comparison without requesting numerical delivery.",
                "scope": plain(context.scope), "purpose": "Return only the declared limited information.",
                "schema_json": json.dumps(form), "initial_report_json": json.dumps(initial)}, "report_update": {}},
            {"selection": {"kind": "tool", "tool": "literature.rate.source.populate", "arguments": args},
                "report_update": {"interpretation": "source_compared"} if numerical_none else {}}, receive])
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        result = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider,
            run_dir=tmp_path / "run", controller_factory=lambda path, initial:
                FixtureController(str(path), initial, 2 if len(path) == 1 else 1),
            project_credit=scorer, initial_known_record_refs=[args["source_ref"]],
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True),),
            binding_definitions={"credit": scorer.as_record()}))
        assert result["credit"] == 0
        assert store.db.execute("select count(*) from runtime_observations").fetchone()[0] == 3
        assert store.db.execute("select count(*) from literature_rate_operations").fetchone()[0] == 1
        assert store.db.execute("select count(*) from literature_rate_source_received").fetchone()[0] == 0
        assert store.db.execute("select count(*) from literature_rate_received").fetchone()[0] == 0
        assert store.db.execute("select count(*) from runtime_report_attempts").fetchone()[0] == 1
    finally:
        store.close()


def test_both_saved_input_families_keep_their_own_projection_and_received_subsets(tmp_path):
    store, context, args = setup_native_store(tmp_path)
    try:
        text = "\t".join(HEADERS) + "\n" + "\n".join("\t".join(row) for row in [
            ["legacy construct", "legacy experiment", "reference", "control", "oxygen_rate", "per_preparation",
             "2", "umol/min", "", "", "", "unspecified", "synthetic"],
            ["legacy construct", "legacy experiment", "test", "intervention", "oxygen_rate", "per_preparation",
             "1", "umol/min", "", "", "", "unspecified", "synthetic"]]) + "\n"
        artifact = store.artifact(text, "text/tab-separated-values")
        legacy = store.put("source", {"provider": "synthetic_legacy_rate_fixture", "accession": None,
            "uri": None, "artifact_ref": artifact, "text_ref": artifact, "request_ref": None,
            "version": None, "retrieved_at": None}, origin="caller")
        legacy_args = {"source_ref": legacy["id"], "source_representation": "original", "table_kind": "synthetic_fixture",
            "delimiter": "\t", "subject": "legacy construct", "experiment": "legacy experiment",
            "reference_arm": "reference", "test_arm": "test", "reference_condition": "control",
            "test_condition": "intervention", "dependence": "unknown", "observation_model": "none"}
        services, binding = service_binding(store, context)
        current = replace(context, received_record_refs=(*context.received_record_refs, legacy["id"]))
        native_out = asyncio.run(binding.execute(current, "literature.rate.source.populate", args, "native"))
        legacy_out = asyncio.run(binding.execute(current, "literature.rate.populate", legacy_args, "legacy"))
        assert native_out["status"] == legacy_out["status"] == "completed"
        refs = [*native_out["record_refs"], *legacy_out["record_refs"]]
        current = replace(current, received_record_refs=(*current.received_record_refs, *refs))
        facts = binding.facts(current, {"committed_record_refs": refs})
        assert {row["sheet_ref"] for row in facts["literature_rate_cells"]} == {legacy_out["result"]["sheet_ref"]}
        assert {row["sheet_ref"] for row in facts["literature_rate_source_cells"]} == {native_out["result"]["sheet_ref"]}
        assert all("approximate" not in row for row in facts["literature_rate_cells"])
        assert all("approximate" in row for row in facts["literature_rate_source_cells"])
        old_form = obj({"old_only": rate_cells_schema()})
        binding.validate_report(current, {"old_only": facts["literature_rate_cells"]}, old_form)
        parent = replace(current, role="annotation", episode_id="parent", path=(("annotation", "root"),), assignment={})
        binding.received_form_references(parent, {"old_only": facts["literature_rate_cells"]}, old_form, "old-subset")
        returned = binding.received_report_facts(parent)
        assert returned["literature_rate_cells"] == facts["literature_rate_cells"]
        assert "literature_rate_source_cells" not in returned
    finally:
        store.close()
