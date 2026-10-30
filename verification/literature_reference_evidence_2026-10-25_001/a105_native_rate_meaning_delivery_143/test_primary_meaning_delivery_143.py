"""Known primary Table2 reports through the new optional meaning return.

Published source values; controlled engineering choices/controller and target.
No live-model interpretation, new measurement or A105 completeness claim.
"""
import asyncio
from copy import deepcopy
from functools import partial
import json
from pathlib import Path
import runpy
import sqlite3
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.literature_rate_meaning_delivery import source_meaning_projection, rate_source_meaning_cells_schema
from gene_annotation_episode.literature_rate_meaning_render import base_rows
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController, ScriptedProvider


HERE = Path(__file__).resolve().parent
PACKET = runpy.run_path(str(HERE.parent / "a105_primary_control_delivery_139/test_primary_delivery_139.py"))
REQUESTED = PACKET["REQUESTED"]


def save(path, value):
    path.write_text(json.dumps(plain(value), indent=2, allow_nan=False) + "\n")


@pytest.mark.parametrize("case", ["h2_crotonyl_omission", "h2_methyl_viologen", "nadh_methyl_viologen"])
def test_primary_meaning_selected_return_and_query_only_reconstruction(tmp_path, monkeypatch, case):
    state = tmp_path / "state"
    store, template, args = PACKET["setup_primary"](state, case)
    schema = obj({"caller_requested_endpoint_components": rate_source_meaning_cells_schema()})
    captured = {}
    def child_next(inputs):
        captured["child"] = deepcopy(inputs)
        return PACKET["reason"](store, args["source_ref"])
    def parent_next(inputs):
        captured["parent"] = deepcopy(inputs)
        rows = inputs["child_reports"][0]["caller_requested_endpoint_components"]
        assert [row["component"] for row in rows] == REQUESTED
        assert inputs["literature_rate_source_meaning_display"]["cells"] == rows
        assert inputs["literature_rate_source_domain_display"]["cells"] == []
        prompt = render_literature_experimental_prompt(inputs, "Evaluate the source complex's actual experimental activity evidence.")
        (tmp_path / "parent_next_prompt.txt").write_text(prompt)
        steering = prompt.split("\n\nSTEERING\n", 1)[1]
        entity = "NADH" if case == "nadh_methyl_viologen" else "H2"
        clause = "1 μmol of " + entity + (" oxidized per min" if entity == "NADH" else " formed per min")
        assert "Recorded intended experimental change" in steering
        assert args["comparison"]["intended_change"]["quote"] in steering
        assert clause in steering and "Source-defined rate units" in steering
        assert ("25°C" if entity == "NADH" else "37°C") in steering
        assert ("0.01 mg" if entity == "NADH" else "0.05 mg") in steering
        assert "mean_uncertainty_unreported" in steering
        assert "Signed profile log ratio" not in steering
        assert rows[0]["comparison_intended_change"]["quote"] == args["comparison"]["intended_change"]["quote"]
        for row in rows:
            for meaning in row["rate_meanings"]:
                definition = meaning["rate_unit"]["source_defined_unit"]["definition"]
                assert definition["clause"]["quote"] == clause
                assert definition["amount"]["raw_number"] == "1"
                assert definition["endpoint_entity"]["quote"] == entity
                assert definition["definition_entity"]["quote"] == entity
                assert meaning["rate_unit"]["multiplier"] == 1
        return PACKET["reason"](store, args["source_ref"])
    provider = ScriptedProvider([
        {"selection": {"kind": "episode_child", "role": "literature", "assignment": plain(template.assignment),
            "goal": "Read the Table2 endpoint-specific comparison on the purified source complex.",
            "scope": plain(template.scope), "purpose": "Return the requested native numerical cells and recorded intended change and unit meanings.",
            "schema_json": json.dumps(schema), "initial_report_json": "{}"}, "report_update": {}},
        {"selection": {"kind": "tool", "tool": "literature.rate.source.populate", "arguments": args}, "report_update": {}},
        child_next, parent_next])
    scorer = ScientificFindingProgress(FindingProgressPolicy(1))
    result = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider, run_dir=tmp_path / "run",
        controller_factory=lambda path, initial: FixtureController(str(path), initial, 2),
        project_credit=scorer, initial_known_record_refs=[args["source_ref"]],
        episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
            reference_parent_sources=[args["source_ref"]]),), binding_definitions={"credit": scorer.as_record()}))
    assert result["credit"] == 0
    assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 4
    operation, = store.db.execute("SELECT * FROM literature_rate_operations").fetchall()
    attempt, = store.db.execute("SELECT * FROM runtime_report_attempts").fetchall()
    assert attempt["failure"] is None
    returned = json.loads(attempt["form"])["caller_requested_endpoint_components"]
    services = WorkflowServices(SimpleNamespace(store=store, run_id=operation["run_id"]))
    repository = services.literature_rate_repository()
    outcome = json.loads(operation["outcome"])
    sheet_ref = outcome["result"]["sheet_ref"]
    saved = repository.read(sheet_ref)
    assert base_rows(returned) == repository.source_domain_projection().project_cells([sheet_ref],
        permitted_record_refs=[sheet_ref], components=REQUESTED)
    by = {row["component"]: row for row in returned}
    if case == "h2_crotonyl_omission":
        assert by["rate_difference"]["reported_domain"]["upper"] is None
        assert by["fractional_decrease"]["reported_domain"]["upper"] is None
        assert by["test_rate"]["bound"] == "lt" and by["test_rate"]["threshold"] == .01
    else:
        assert by["retained_fraction"]["value"] == pytest.approx(5 / 7 if case == "nadh_methyl_viologen" else .004)
    rows = store.db.execute("SELECT * FROM runtime_episodes").fetchall()
    def context(row):
        request = json.loads(row["request"])
        role = json.loads(row["path"])[-1][0]
        return BindingContext(operation["run_id"], row["episode_id"], role,
            tuple(tuple(pair) for pair in json.loads(row["path"])), plain(template.scope),
            request["message"].get("episode_assignment", {}), request,
            tuple(EpisodeReceipts(store, operation["run_id"]).known(row["episode_id"])))
    owner = context(next(row for row in rows if len(json.loads(row["path"])) == 2))
    receiver = context(next(row for row in rows if len(json.loads(row["path"])) == 1))
    expected_display = captured["parent"]["literature_rate_source_meaning_display"]
    save(tmp_path / "original_selected_arguments.json", args)
    save(tmp_path / "saved_numerical_sheet.json", saved)
    save(tmp_path / "original_contract.json", json.loads(attempt["contract"]))
    save(tmp_path / "original_admitted_form.json", json.loads(attempt["form"]))
    save(tmp_path / "observations.json", [dict(row) for row in store.db.execute("SELECT * FROM runtime_observations")])
    paper_artifacts = {store.get(args["source_ref"])[name] for name in ("artifact_ref", "text_ref")}
    store.close()
    def forbidden(*args, **kwargs):
        raise AssertionError("reconstruction must not acquire, parse, fit, reinterpret, model or write")
    monkeypatch.setattr("gene_annotation_episode.literature_rate_native_inputs.read_rate_source_inputs", forbidden)
    monkeypatch.setattr("gene_annotation_episode.literature_rate_storage.populate_rate_contrast", forbidden)
    monkeypatch.setattr("gene_annotation_episode.providers.ModelConnection", forbidden)
    reopened = Store.__new__(Store)
    reopened.path = state.resolve(); reopened._savepoint = 0
    reopened.db = sqlite3.connect((state / "state.sqlite3").as_uri() + "?mode=ro", uri=True, isolation_level=None)
    reopened.db.row_factory = sqlite3.Row
    reopened.db.execute("PRAGMA query_only=ON")
    reopened.db.create_function("library_scope_record", 2, reopened._scope_filter_record)
    original_get = reopened.get_artifact
    def saved_only(reference):
        if reference in paper_artifacts:
            forbidden()
        return original_get(reference)
    monkeypatch.setattr(reopened, "get_artifact", saved_only)
    for method in ("put", "artifact", "transaction", "register_material", "parse_material"):
        monkeypatch.setattr(reopened, method, forbidden)
    try:
        restored_services = WorkflowServices(SimpleNamespace(store=reopened, run_id=operation["run_id"]))
        binding = LiteratureEpisodes(restored_services, rate_population=True, reference_parent_sources=[args["source_ref"]])
        restored_repository = restored_services.literature_rate_repository()
        restored = source_meaning_projection(restored_repository)
        assert restored_repository.populate_native(owner, args, operation["operation_key"]) == outcome
        assert restored.read(sheet_ref) == saved
        assert restored.received_cells(receiver) == returned
        assert restored.fact_cells(receiver, [sheet_ref], components=["signed_profile_log_ratio"]) == []
        assert binding._native_rate_meaning_display_context(receiver)["literature_rate_source_meaning_display"] == expected_display
        assert reopened.db.total_changes == 0
        save(tmp_path / "reconstruction.json", {"query_only": True, "database_changes": 0,
            "original_paper_and_render_denied": sorted(paper_artifacts), "reader_populator_model_mutation_denied": True,
            "exact_saved_cells_and_subset_reconstructed": True})
    finally:
        reopened.close()
