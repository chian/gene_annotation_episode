"""Controlled ordinary episode amount return mechanics; no model inference."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import ReportBoundaryError, form_with_facts, plain
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.episode_bindings import EpisodeBindingRegistry
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_amount_prompt import AMOUNT_TASK
from gene_annotation_episode.literature_amount_storage import amount_cells_schema
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.tools import ToolRegistry
from test_literature_amount_storage import setup
from test_literature_amount_inputs import TEXT, fixture, witness
from test_runtime import FixtureController, ScriptedProvider


COMPONENTS = ["amount_ratio", "conditional_mass_denominator_factor", "amount_ratio_variance"]
FORM = obj({"requested_amounts": amount_cells_schema()})


def binding_for(store, context):
    host = SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store))
    binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True)
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    return binding


def test_c7_selected_amount_operation_exact_return_and_parent_subset(tmp_path):
    store, context, args = setup(tmp_path)
    try:
        context = replace(context, assignment={**plain(context.assignment), "requested_amount_components": COMPONENTS})
        binding = binding_for(store, context)
        outcome = asyncio.run(binding.execute(context, "literature.amount.populate", args, "selected"))
        assert outcome["status"] == "completed", outcome
        current = replace(context, received_record_refs=(*context.received_record_refs, *outcome["record_refs"]))
        facts = binding.facts(current, {"committed_record_refs": [outcome["result"]["sheet_ref"]]})
        form = form_with_facts({}, FORM, facts)
        binding.validate_report(current, form, FORM)
        rows = form["requested_amounts"]
        assert [row["component"] for row in rows] == COMPONENTS
        assert rows[0]["value"] == 5 / 7 and rows[1]["value"] == 1.4 and rows[2]["value"] is None
        wrong = deepcopy(form)
        wrong["requested_amounts"][0]["numerator"]["amount_role"] = "unknown"
        with pytest.raises(ReportBoundaryError, match="differs_from_saved"):
            binding.validate_report(current, wrong, FORM)
        parent = replace(current, role="annotation", episode_id="parent", path=(("annotation", "parent"),), assignment={})
        binding.received_form_references(parent, form, FORM, "admitted")
        assert binding.received_report_facts(parent)["literature_amount_cells"] == rows
        assert len(binding.services.literature_amount_repository().read(outcome["result"]["sheet_ref"])["sheet"]["cells"]) == 12
    finally:
        store.close()


def test_c7_unknown_unit_preserves_source_inequality_in_closed_parent_cell(tmp_path):
    text = "Stock target <5 arbitrary; total 7 mg/ml."
    arguments = fixture(text, first="5 arbitrary", nunit="arbitrary")[0]
    store, context, args = setup(tmp_path, text=text, arguments=arguments)
    try:
        context = replace(context, assignment={**plain(context.assignment), "requested_amount_components": ["numerator_amount"]})
        binding = binding_for(store, context)
        outcome = asyncio.run(binding.execute(context, "literature.amount.populate", args, "known-bound-unknown-unit"))
        assert outcome["status"] == "completed", outcome
        current = replace(context, received_record_refs=(*context.received_record_refs, *outcome["record_refs"]))
        form = form_with_facts({}, FORM, binding.facts(current, {"committed_record_refs": [outcome["result"]["sheet_ref"]]}))
        binding.validate_report(current, form, FORM)
        row, = form["requested_amounts"]
        assert row["bound"] == "lt" and row["status"] == "unavailable"
        assert row["value"] is row["threshold"] is row["unit"] is None
        assert row["unavailable_reason"] == "unsupported_source_amount_unit"
    finally:
        store.close()


@pytest.mark.parametrize("mode", ["requested_components", "ratio_only_unique_tokens", "numerator_requested_unique_tokens"])
def test_controlled_child_selected_amounts_return_once_with_no_internal_observations(tmp_path, mode):
    unique = mode != "requested_components"
    numerator_requested = mode == "numerator_requested_unique_tokens"
    n, d = (105.1234567, 207.7654321) if unique else (5, 7)
    text = TEXT.replace("7 mg/ml", f"{d} mg/ml").replace("5 mg/ml", f"{n} mg/ml") if unique else TEXT
    selected_args = fixture(text, first=f"{n} mg/ml", second=f"{d} mg/ml", n=str(n), d=str(d))[0] if unique else None
    if unique:
        for role, subject, method, number in (("numerator", "target", "band intensity", n),
                ("denominator", "total protein", "Bradford analysis", d)):
            selected_args["quantities"][role].update(subject=witness(text, subject), method=witness(text, method),
                reported_basis=witness(text, f"{number} mg/ml"),
                measurement_identity=witness(text, f"{subject} estimated by {method} at " +
                    (f"an approximate concentration of {number} mg/ml" if role == "numerator" else f"{number} mg/ml")))
    store, context, args = setup(tmp_path / "state", text=text, arguments=selected_args)
    received, controllers = [], []
    components = ["numerator_amount", "amount_ratio"] if numerator_requested else ["amount_ratio"] if unique else COMPONENTS
    form_schema = obj({"requested_amounts": amount_cells_schema()})
    assignment = {**plain(context.assignment), "requested_amount_components": components}
    child = {"selection": {"kind": "episode_child", "role": "literature", "assignment": assignment,
        "goal": "Compare the explicitly selected synthetic target/total stock estimates.",
        "scope": plain(context.scope), "purpose": "Return only the declared amount components and their source meanings.",
        "schema_json": json.dumps(form_schema), "initial_report_json": "{}"}, "report_update": {}}
    work = {"selection": {"kind": "tool", "tool": "literature.amount.populate", "arguments": args}, "report_update": {}}
    def receives(inputs):
        form, = inputs["child_reports"]
        assert [row["component"] for row in form["requested_amounts"]] == components
        assert form["requested_amounts"][0]["value"] == (n if numerator_requested else n / d)
        assert form["requested_amounts"][0]["numerator"]["amount_role"] == "target_mass_estimate"
        assert form["requested_amounts"][0]["denominator"]["amount_role"] == "total_protein_mass_estimate"
        received.append(form)
        prompt = render_literature_experimental_prompt(inputs, "Evaluate the synthetic source comparison.")
        task, steering = prompt.split("\n\nSTEERING\n")
        assert AMOUNT_TASK in task
        assert "Admitted requested amount components" in steering
        assert "target_mass_estimate" in steering and "total_protein_mass_estimate" in steering
        if not unique:
            assert "amount_covariance_unreported" in steering
        else:
            (tmp_path / "ratio_only_parent_prompt.txt").write_text(prompt)
            assert (str(n) in steering) is numerator_requested
            assert str(d) not in steering
            assert "band intensity" in steering and "Bradford analysis" in steering
            assert "target" in steering and "total protein" in steering
        assert ("numerator_amount" in steering) is numerator_requested
        commit = {field: [] for field in store.reasoning_schema()["required"]}
        source = store.get(args["source_ref"])
        commit["source_subjects"] = [{"alias": "synthetic_stock", "reference_type": "assay", "source_ref": args["source_ref"],
            "label": "same unnamed stock", "anchor": {"source_ref": args["source_ref"], "artifact_ref": source["artifact_ref"],
                "start": 0, "end": len(text.encode()), "quote": text}}]
        return {"selection": {"kind": "reason", "commit": commit}, "report_update": {}}
    def controller(path, initial):
        result = FixtureController(str(path), initial, 2 if len(path) == 1 else 1)
        controllers.append(result)
        return result
    try:
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=ScriptedProvider([child, work, receives]),
            run_dir=tmp_path / "run", controller_factory=controller, project_credit=scorer,
            initial_known_record_refs=list(context.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True, reference_parent_sources=[args["source_ref"]]),),
            binding_definitions={"credit": scorer.as_record()}))
        assert len(received) == 1
        assert summary["credit"] == 0
        assert [row.scores for row in controllers] == [[0, 0], [0]]
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 3
        assert store.db.execute("SELECT count(*) FROM literature_amount_operations").fetchone()[0] == 1
        assert len(store.db.execute("SELECT form FROM runtime_forms").fetchall()) == 1
        assert not store.list("observation") and not store.list("assessment")
    finally:
        store.close()
