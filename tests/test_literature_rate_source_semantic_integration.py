"""Actual selected synthetic rate work and saved-only semantic presentation.

Scripted providers/controllers verify engineering boundaries, not model science.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import json
from pathlib import Path
import re
import sqlite3
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import ContractError, obj
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_experimental_prompt import _steering, render_literature_experimental_prompt
from gene_annotation_episode.literature_rate_source_render import MEANING_FIELDS
from gene_annotation_episode.literature_rate_storage import LiteratureRateRepository, rate_source_cells_schema
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_literature_rate_episode_integration import service_binding
from test_literature_rate_native_storage import setup_native_store
from test_runtime import FixtureController, ScriptedProvider


def source_reason(store, source_ref):
    """One explicit constructed source assertion, not a completion shortcut."""
    source = store.get(source_ref)
    raw = store.get_artifact(source["artifact_ref"])
    commit = {name: [] for name in store.reasoning_schema()["required"]}
    commit["source_subjects"] = [{"alias": "examined_constructed_reference", "reference_type": "assay",
        "source_ref": source_ref, "label": "enzyme Alpha", "anchor": {
            "source_ref": source_ref, "artifact_ref": source["artifact_ref"],
            "start": 0, "end": len(raw), "quote": raw.decode()}}]
    return {"selection": {"kind": "reason", "commit": commit}, "report_update": {}}


@pytest.mark.parametrize("bounded", [False, True])
def test_actual_selected_own_and_parent_decisions_then_first_readonly_display_preserve_exact_subset(tmp_path, monkeypatch, bounded):
    state_path = tmp_path / "state"
    store, template, args = setup_native_store(state_path,
        reference="< approximately 12" if bounded else None)
    requested = ["reference_rate"] if bounded else ["rate_difference", "difference_se"]
    form = obj({"parent_chosen_values": rate_source_cells_schema()})
    captured = {}
    assignment = {**plain(template.assignment), "requested_rate_components": requested}
    def child_next(inputs):
        captured["child_display"] = deepcopy(inputs["literature_rate_source_display"])
        task, steering = render_literature_experimental_prompt(inputs, "Constructed child TASK").split("\n\nSTEERING\n", 1)
        assert "enzyme Alpha" in steering and "enzyme Beta" in steering
        assert "Reference − test rate" in steering
        assert not re.search(r"\b(?:source|reference|term|context)_[a-f0-9]{24,64}\b", steering)
        if bounded:
            assert "zero_reference_rate" in steering
        assert "Establish the actual organism" in task
        return source_reason(store, args["source_ref"])
    def parent_next(inputs):
        captured["parent_state"] = deepcopy(inputs)
        rows = inputs["child_reports"][0]["parent_chosen_values"]
        display = inputs["literature_rate_source_display"]
        assert display["cells"] == rows
        assert [row["component"] for row in rows] == requested
        # The host hook, not generic24-record pagination, carries every label.
        paged = deepcopy(inputs)
        paged["working_state"]["references"] = [
            {"id": "reference_constructed_filler_" + str(i), "record_type": "reference", "label": "unrelated page entry"}
            for i in range(24)]
        paged["working_state"]["contexts"] = []
        paged["working_state"]["terms"] = []
        task, steering = render_literature_experimental_prompt(paged, "Constructed parent TASK").split("\n\nSTEERING\n", 1)
        assert "enzyme Alpha" in steering and "enzyme Beta" in steering
        assert "WT" in steering and "variant" in steering
        assert "NADH oxidation" in steering and "per mg preparation" in steering
        assert "prepR" in steering and "prepT" in steering
        assert not re.search(r"\b(?:source|reference|term|context)_[a-f0-9]{24,64}\b", steering)
        if bounded:
            assert "< | 0.012 | true | censored_measurement" in steering
            assert "0.003" not in steering and "Reference − test rate" not in steering
        else:
            assert "Reference − test rate | 0.009" in steering
            assert "mean_uncertainty_unreported" in steering or "dependence_unknown" in steering
            assert "0.012" not in steering and "0.003" not in steering
        assert "Keep the actual caller question" in task
        return source_reason(store, args["source_ref"])
    provider = ScriptedProvider([
        {"selection": {"kind": "episode_child", "role": "literature", "assignment": assignment,
            "goal": "Examine the constructed source comparison.", "scope": plain(template.scope),
            "purpose": "Return only requested native numerical components.",
            "schema_json": json.dumps(form), "initial_report_json": "{}"}, "report_update": {}},
        {"selection": {"kind": "tool", "tool": "literature.rate.source.populate", "arguments": args}, "report_update": {}},
        child_next, parent_next])
    scorer = ScientificFindingProgress(FindingProgressPolicy(1))
    run_dir = tmp_path / "run"
    result = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider,
        run_dir=run_dir, controller_factory=lambda path, initial:
            FixtureController(str(path), initial, 2), project_credit=scorer,
        initial_known_record_refs=[args["source_ref"]],
        episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
            reference_parent_sources=[args["source_ref"]]),),
        binding_definitions={"credit": scorer.as_record()}))
    assert result["credit"] == 0
    assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 4
    assert store.db.execute("SELECT count(*) FROM literature_rate_operations").fetchone()[0] == 1
    attempt, = store.db.execute("SELECT * FROM runtime_report_attempts").fetchall()
    returned = json.loads(attempt["form"])
    assert returned == captured["parent_state"]["child_reports"][0]
    manifest = json.loads((run_dir / "run.json").read_text())
    run = manifest["run_id"]
    parent_row, = store.db.execute("SELECT * FROM runtime_episodes WHERE json_array_length(path)=1").fetchall()
    request = json.loads(parent_row["request"])
    parent = BindingContext(run, parent_row["episode_id"], "annotation",
        tuple(tuple(p) for p in json.loads(parent_row["path"])), plain(template.scope),
        request["message"].get("episode_assignment", {}), request,
        tuple(EpisodeReceipts(store, run).known(parent_row["episode_id"])))
    expected = captured["parent_state"]["literature_rate_source_display"]
    source_artifacts = {store.get(args["source_ref"])[name] for name in ("artifact_ref", "text_ref")}
    store.close()

    def forbidden(*args, **kwargs):
        raise AssertionError("saved presentation acquired, parsed, calculated, modeled or mutated")
    monkeypatch.setattr("gene_annotation_episode.literature_rate_native_inputs.read_rate_source_inputs", forbidden)
    monkeypatch.setattr("gene_annotation_episode.literature_rate_storage.populate_rate_contrast", forbidden)
    monkeypatch.setattr("gene_annotation_episode.providers.ModelConnection", forbidden)
    reopened = Store.__new__(Store)
    reopened.path = state_path.resolve();reopened._savepoint = 0
    reopened.db = sqlite3.connect((reopened.path / "state.sqlite3").as_uri() + "?mode=ro", uri=True, isolation_level=None)
    reopened.db.row_factory = sqlite3.Row
    reopened.db.execute("PRAGMA query_only=ON")
    reopened.db.create_function("library_scope_record", 2, reopened._scope_filter_record)
    original_get = reopened.get_artifact
    def saved_only(reference):
        if reference in source_artifacts:
            raise AssertionError("original scientific source bytes reopened")
        return original_get(reference)
    monkeypatch.setattr(reopened, "get_artifact", saved_only)
    for name in ("put", "artifact", "transaction", "register_material", "parse_material"):
        monkeypatch.setattr(reopened, name, forbidden)
    try:
        services = WorkflowServices(SimpleNamespace(store=reopened, run_id=run))
        binding = LiteratureEpisodes(services, rate_population=True, reference_parent_sources=[args["source_ref"]])
        assert reopened.db.total_changes == 0
        display = binding._native_rate_display_context(parent)["literature_rate_source_display"]
        assert display == expected
        projection = services.literature_rate_repository().source_projection()
        assert projection.received_cells(parent) == returned["parent_chosen_values"]
        assert projection.fact_cells(parent, [display["cells"][0]["sheet_ref"]], components=["test_rate"]) == []
        for row in display["cells"]:
            for field in MEANING_FIELDS:
                if row[field] is not None:
                    assert display["records"][row[field]] == reopened.get(row[field])
        saved_state = {"child_reports": [returned], "literature_rate_source_display": display, "working_state": {}}
        text = _steering(saved_state, ())
        assert "enzyme Alpha" in text and "enzyme Beta" in text
        missing = next(iter(display["records"]))
        with pytest.raises(ContractError, match="display_record_not_received"):
            binding._native_rate_display_context(replace(parent,
                received_record_refs=tuple(r for r in parent.received_record_refs if r != missing)))
        assert reopened.db.total_changes == 0
        assert reopened.db.execute("PRAGMA query_only").fetchone()[0] == 1
    finally:
        reopened.close()


def test_other_known_sheet_and_unreceived_meaning_records_cannot_expand_receiver_display(tmp_path):
    store, owner, args = setup_native_store(tmp_path)
    try:
        services, binding = service_binding(store, owner)
        repo = services.literature_rate_repository().source_projection()
        first = repo.populate_native(owner, args, "original")
        permitted = (*owner.received_record_refs, *first["record_refs"])
        owner = replace(owner, received_record_refs=permitted)
        rows = repo.fact_cells(owner, [first["result"]["sheet_ref"]], components=["rate_difference"])
        parent = replace(owner, episode_id="receiver", role="annotation", path=(("annotation", "parent"),), assignment={})
        repo.receive_cells(parent, rows, "constructed-admission")
        private_args = deepcopy(args)
        private_args["experiment"] = args["arms"]["reference"]["subject"]
        private_owner = replace(owner, episode_id="other-owner")
        private = repo.populate_native(private_owner, private_args, "private-output")
        private_sheet = private["result"]["sheet_ref"]
        parent = replace(parent, received_record_refs=(*parent.received_record_refs, private_sheet))
        display = binding._native_rate_display_context(parent)["literature_rate_source_display"]
        assert display["cells"] == rows
        assert all(row["sheet_ref"] != private_sheet for row in display["cells"])
        own_display = binding._native_rate_display_context(replace(private_owner,
            received_record_refs=(*private_owner.received_record_refs, *private["record_refs"])))
        private_refs = set(own_display["literature_rate_source_display"]["records"]) - set(display["records"])
        assert private_refs and private_refs.isdisjoint(display["records"])
        missing = rows[0]["test_construct_ref"]
        with pytest.raises(ContractError, match="display_record_not_received"):
            binding._native_rate_display_context(replace(parent,
                received_record_refs=tuple(r for r in parent.received_record_refs if r != missing)))
        assert store.db.execute("SELECT count(*) FROM literature_rate_source_received").fetchone()[0] == 1
    finally:
        store.close()
