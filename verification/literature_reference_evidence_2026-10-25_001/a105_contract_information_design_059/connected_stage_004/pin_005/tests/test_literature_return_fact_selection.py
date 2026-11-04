"""Synthetic controlled providers exercise saved fact selection, not model science.

No primary paper or retained paper-specific packet is read by these checks.
The existing matched partner fixture and rate table are explicitly synthetic.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import json

import pytest

from gene_annotation_episode.communication import (
    ReportBoundaryError, form_with_facts, interpretation_schema, plain,
)
from gene_annotation_episode.decision_context import state_frame
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_experimental_prompt import (
    EXPERIMENTAL_TASK, SAVED_NUMERICAL_RETURN_TASK,
)
from gene_annotation_episode.literature_partner_storage import partner_cells_schema
from gene_annotation_episode.literature_rate_storage import rate_cells_schema
from gene_annotation_episode.literature_reference_parent_prompt import REFERENCE_PARENT_TASK
from gene_annotation_episode.runtime import _compile_form, run_workflow
from gene_annotation_episode.tools import ToolRegistry
from test_literature_experimental_prompt_delivery import LiteratureWire, complete, snapshot
from test_literature_partner_integration import setup_case, binding_for
from test_literature_rate_episode_integration import service_binding
from test_literature_rate_storage import setup_store
from test_runtime import FixtureController, ScriptedProvider


EXPECTED_TASK = (
    "When requesting saved numerical experimental components from a child, copy the "
    "declared projection schema into your chosen top-level return field, including "
    "its exact `x-source` selector. Choose the needed components through the child "
    "assignment. Keep bound fact fields out of `initial_report_json`; the runtime "
    "fills them from saved results. Use separate constrained fields for interpretations "
    "and unresolved questions. Do not ask the child to rewrite saved numerical cells "
    "as model-authored report values."
)
INTERPRETATIONS = {
    "interpretation": {"type": "string", "enum": ["unresolved", "conditional_source_effect"]},
    "remaining_question": {"type": "string", "enum": ["controls_pending", "target_correspondence_separate"]},
}
INITIAL = {"interpretation": "unresolved", "remaining_question": "controls_pending"}
UPDATED = {"interpretation": "conditional_source_effect",
           "remaining_question": "target_correspondence_separate"}


def chosen_form(field, projection):
    return obj({field: projection, **deepcopy(INTERPRETATIONS)})


@pytest.mark.parametrize("parent", [False, True], ids=["literature-child", "reference-parent"])
def test_provider_task_keeps_exact_fact_instruction_and_forms_across_frames(tmp_path, parent):
    """Actual provider presentation/RPC path, with controlled wire responses."""
    first = snapshot()
    first["requested_form"] = chosen_form("caller_selected_cells", partner_cells_schema())
    first["available_report_facts"] = LiteratureEpisodes._rate_fact_sources()
    first["literature_assignment"]["requested_partner_components"] = ["partner_loss_fraction"]
    if parent:
        first.pop("literature_assignment")
        first.pop("literature_source_custody")
        first["literature_experimental_work"]["aspect"] = "reference_evidence_parent"
        first["reference_evidence_parent"] = {
            "version": "reference_evidence_parent_v1", "source_refs": ["source_selected"],
        }
    second = deepcopy(first)
    second["current_report_update"] = UPDATED
    # Distinct sentinels demonstrate that returns/lookups stay in STEERING.
    second["child_reports"] = [{"interpretation": "RECEIVED_SYNTHETIC_QUALIFICATION"}]
    lookup = {"version": "decision_context_v1", "kind": "decision_lookup_result",
              "decision_index": 2, "exchange_index": 1,
              "result": {"status": "completed", "text": "LOOKED_UP_SYNTHETIC_LIMITATION"}}
    restored = state_frame(second)
    restored.update(restored_pending_decision_index=2, restored_public_exchanges=[{
        "exchange_index": 1, "lookup_result": lookup["result"],
    }])
    original = deepcopy((first, second, restored))
    wire, reopened = LiteratureWire(tmp_path / "wire"), LiteratureWire(tmp_path / "reopened")

    async def exercise():
        await complete(wire, state_frame(first))
        await complete(wire, state_frame(second, first))
        await complete(wire, lookup)
        await complete(reopened, restored)

    asyncio.run(exercise())
    tasks = []
    for transport in (wire, reopened):
        for turn in transport.turns_sent():
            task, steering = turn["input"][0]["text"].split("\n\nSTEERING\n", 1)
            assert SAVED_NUMERICAL_RETURN_TASK == EXPECTED_TASK
            assert task.count(EXPECTED_TASK) == 1
            assert EXPECTED_TASK not in steering
            assert (REFERENCE_PARENT_TASK if parent else EXPERIMENTAL_TASK) in task
            assert "return.caller_selected_cells" in task
            assert "recorded fact from literature_partner_cells" in task
            # Exact projection fields, including qualifications and custody,
            # remain represented; no shortened numerical report is substituted.
            for name in partner_cells_schema()["items"]["properties"]:
                assert "return.caller_selected_cells[]." + name in task
            assert "RECEIVED_SYNTHETIC_QUALIFICATION" not in task
            assert "LOOKED_UP_SYNTHETIC_LIMITATION" not in task
            tasks.append(task)
    assert all(task == tasks[0] for task in tasks)
    for turn in (*wire.turns_sent()[1:], *reopened.turns_sent()):
        assert "RECEIVED_SYNTHETIC_QUALIFICATION" in turn["input"][0]["text"]
    assert "LOOKED_UP_SYNTHETIC_LIMITATION" in wire.turns_sent()[-1]["input"][0]["text"]
    assert "LOOKED_UP_SYNTHETIC_LIMITATION" in reopened.turns_sent()[0]["input"][0]["text"]
    assert (first, second, restored) == original


@pytest.mark.parametrize("family,field", [("partner", "chosen_partner_numbers"), ("rate", "other_family_subset")])
def test_selected_child_population_exact_return_admission_and_saved_reconstruction(tmp_path, monkeypatch, family, field):
    """Ordinary selected child/population/admission; synthetic script/controller."""
    if family == "partner":
        components = ["partner_loss_fraction", "addback_fraction"]
        store, context, args = setup_case(tmp_path / "state", case="matched", components=components)
        projection, namespace = partner_cells_schema(), "literature_partner_cells"
        tool, table = "literature.partner.populate", "literature_partner"
        expected_values = [.8, .875]
    else:
        components = ["rate_difference", "difference_se"]
        store, context, args = setup_store(tmp_path / "state")
        context = replace(context, assignment={"version": "literature_assignment_v1",
            "question_context_refs": [], "source_refs": [args["source_ref"]],
            "requested_rate_components": components})
        projection, namespace = rate_cells_schema(), "literature_rate_cells"
        tool, table = "literature.rate.populate", "literature_rate"
        expected_values = [1, None]
    with store:
        form_schema = chosen_form(field, projection)
        compiled = _compile_form(json.dumps(form_schema), LiteratureEpisodes._rate_fact_sources())
        assert compiled == form_schema
        assert compiled["properties"][field] == projection
        assert interpretation_schema(compiled) == obj(INTERPRETATIONS)
        received, controllers = [], []

        def choose_population(inputs):
            assert inputs["literature_assignment"] == plain(context.assignment)
            assert inputs["requested_form"] == form_schema
            assert inputs["current_report_update"] == INITIAL
            assert inputs["available_report_facts"][namespace]["report_schema"] == projection
            return {"selection": {"kind": "tool", "tool": tool, "arguments": args},
                    "report_update": UPDATED}

        def use_received(inputs):
            report, = inputs["child_reports"]
            rows = report[field]
            assert {name: report[name] for name in UPDATED} == UPDATED
            assert [row["component"] for row in rows] == components
            assert [row["value"] for row in rows] == expected_values
            assert all(set(row) == set(projection["items"]["properties"]) for row in rows)
            assert all(row["evidence_source_ref"] == args["source_ref"] for row in rows)
            # Receipt projection supplies scientific identities to this parent.
            references = {row["id"] for row in inputs["working_state"]["references"]}
            identity = "subject_ref" if family == "partner" else "assayed_subject_ref"
            assert rows[0][identity] in references
            received.append(deepcopy(report))
            source = store.get(args["source_ref"])
            raw = store.get_artifact(source["artifact_ref"])
            label = "Synthetic subject" if family == "partner" else "source construct"
            start = raw.index(label.encode())
            commit = {name: [] for name in store.reasoning_schema()["required"]}
            commit["source_subjects"] = [{"alias": "received_synthetic_subject",
                "reference_type": "assay", "source_ref": source["id"], "label": label,
                "anchor": {"source_ref": source["id"], "artifact_ref": source["artifact_ref"],
                    "start": start, "end": start + len(label.encode()), "quote": label}}]
            return {"selection": {"kind": "reason", "commit": commit}, "report_update": {}}

        commission = {"selection": {"kind": "episode_child", "role": "literature",
            "assignment": plain(context.assignment), "goal": "Evaluate the synthetic source comparison",
            "scope": plain(context.scope), "purpose": "Return selected saved components and separate interpretations",
            "schema_json": json.dumps(form_schema), "initial_report_json": json.dumps(INITIAL)},
            "report_update": {}}
        provider = ScriptedProvider([commission, choose_population, use_received])

        def controller(path, initial):
            result = FixtureController(str(path), initial, 2 if len(path) == 1 else 1)
            controllers.append(result)
            return result

        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider,
            run_dir=tmp_path / "run", controller_factory=controller, project_credit=scorer,
            initial_known_record_refs=list(context.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
                reference_parent_sources=[args["source_ref"]]),),
            binding_definitions={"credit": scorer.as_record()}))
        assert len(received) == 1 and summary["credit"] == 0
        assert [item.scores for item in controllers] == [[0, 0], [0]]
        assert len(provider.contexts) == 3
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 3
        assert store.db.execute(f"SELECT count(*) FROM {table}_operations").fetchone()[0] == 1
        operation = store.db.execute(f"SELECT * FROM {table}_operations").fetchone()
        saved_form = store.db.execute("SELECT * FROM runtime_forms").fetchone()
        assert json.loads(saved_form["form"]) == received[0]
        assert json.loads(saved_form["facts"])["interpretations"] == UPDATED
        attempt = store.db.execute("SELECT * FROM runtime_report_attempts").fetchone()
        assert json.loads(attempt["contract"])["measurements"]["schema"] == form_schema
        assert json.loads(attempt["form"]) == received[0] and attempt["failure"] is None
        assert json.loads(store.db.execute(f"SELECT cells FROM {table}_received").fetchone()[0]) == received[0][field]
        assert not store.list("observation") and not store.list("assessment")

        # Reconstruct the real binding and consume only immutable saved output.
        current = replace(context, run_id=operation["run_id"], episode_id=operation["episode_id"],
            role="literature", path=(("literature", "synthetic-child"),),
            received_record_refs=tuple(dict.fromkeys([*context.received_record_refs,
                *json.loads(operation["outcome"])["record_refs"]])))
        binding = binding_for(store, current) if family == "partner" else service_binding(store, current)[1]
        rebuilt, = compose_episode_bindings(binding.services, store=store,
            journal=Journal(store, current.run_id), execution_backend=None,
            descriptors=[binding.as_record()], job_episodes=None, resource_estimator=None,
            role_credit_bindings={}).bindings

        def forbidden(*_args, **_kwargs):
            raise AssertionError("saved projection must not reread or recalculate source evidence")

        if family == "partner":
            monkeypatch.setattr("gene_annotation_episode.literature_partner_storage.read_partner_inputs", forbidden)
        else:
            monkeypatch.setattr("gene_annotation_episode.literature_rate_storage.read_rate_table", forbidden)
            monkeypatch.setattr("gene_annotation_episode.literature_rate_storage.populate_rate_contrast", forbidden)
        sheet_ref = received[0][field][0]["sheet_ref"]
        facts = rebuilt.facts(current, {"committed_record_refs": [sheet_ref]})
        assert form_with_facts(UPDATED, compiled, facts) == received[0]
        rebuilt.validate_report(current, received[0], compiled)
        bad = deepcopy(received[0])
        bad[field][0]["value"] += 1
        with pytest.raises(ReportBoundaryError, match="differs_from_saved"):
            rebuilt.validate_report(current, bad, compiled)
        parent = replace(current, role="annotation", episode_id=attempt["parent_episode_id"],
                         path=(("annotation", "root"),), assignment={})
        assert rebuilt.received_report_facts(parent)[namespace] == received[0][field]
        assert all(row["component"] in components for row in rebuilt.received_report_facts(parent)[namespace])
        # An omitted selector remains parent-authored interpretation even if
        # its fields resemble the exact projection. It creates no saved-cell
        # admission; neither rendering nor receipt machinery installs a binder.
        unbound = deepcopy(compiled)
        unbound["properties"][field].pop("x-source")
        assert _compile_form(json.dumps(unbound), LiteratureEpisodes._rate_fact_sources()) == unbound
        unbound_receiver = replace(parent, episode_id="synthetic-unbound-receiver")
        assert rebuilt.received_form_references(unbound_receiver, received[0], unbound,
            "unbound-interpretation") == []
        assert rebuilt.received_report_facts(unbound_receiver).get(namespace, []) == []
        with pytest.raises(ReportBoundaryError) as mistaken_initial:
            form_with_facts({**INITIAL, field: []}, compiled, facts)
        assert mistaken_initial.value.diagnostic["code"] == "interpretation_fields"
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 3
        assert store.db.execute(f"SELECT count(*) FROM {table}_received").fetchone()[0] == 1


def test_omitted_selector_stays_interpretive_and_invalid_selectors_are_not_repaired():
    sources = LiteratureEpisodes._rate_fact_sources()
    unbound_projection = partner_cells_schema()
    unbound_projection.pop("x-source")
    schema = obj({"parent_chosen_unbound": unbound_projection})
    compiled = _compile_form(json.dumps(schema), sources)
    assert compiled == schema and interpretation_schema(compiled) == schema
    assert form_with_facts({"parent_chosen_unbound": []}, compiled,
        {"literature_partner_cells": [{"value": 99}]}) == {"parent_chosen_unbound": []}
    for selector in ("literature_partner_cell", "literature_partner_cells "):
        malformed = obj({"parent_chosen_unbound": {**deepcopy(unbound_projection), "x-source": selector}})
        with pytest.raises(ValueError):
            _compile_form(json.dumps(malformed), sources)
        assert malformed["properties"]["parent_chosen_unbound"]["x-source"] == selector
    nested = obj({"wrapper": obj({"numbers": partner_cells_schema()})})
    with pytest.raises(ReportBoundaryError):
        _compile_form(json.dumps(nested), sources)
