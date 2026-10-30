"""Actual selected source-rate work, closed domain returns and first RO replay.

Only constructed source bytes and scripted engineering providers/controllers.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import json
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
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.literature_rate_calculations import populate_rate_contrast
from gene_annotation_episode.literature_rate_domains import NAMESPACE, rate_source_domain_cells_schema
from gene_annotation_episode.literature_rate_storage import LiteratureRateRepository, rate_source_cells_schema
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_literature_rate_native_storage import setup_native_store
from test_literature_rate_source_semantic_integration import source_reason
from test_runtime import FixtureController, ScriptedProvider


@pytest.mark.parametrize("legacy_payload", [False, True])
@pytest.mark.parametrize("domain_return", [False, True])
def test_selected_native_action_own_next_decision_typed_subset_and_readonly_replay(tmp_path, monkeypatch, legacy_payload, domain_return):
    path = tmp_path / "state"
    store, template, args = setup_native_store(path, reference="> 12")
    if legacy_payload:
        def legacy_calculator(*args, **kwargs):
            kwargs.pop("native_bound_version", None)
            return populate_rate_contrast(*args, **kwargs)
        monkeypatch.setattr("gene_annotation_episode.literature_rate_storage.populate_rate_contrast", legacy_calculator)
    namespace = NAMESPACE if domain_return else "literature_rate_source_cells"
    schema = rate_source_domain_cells_schema() if domain_return else rate_source_cells_schema()
    form = obj({"caller_chosen_subset": schema})
    assignment = {**plain(template.assignment), "requested_rate_components": ["retained_fraction"]}
    captured = {}
    def child_next(inputs):
        display = inputs["literature_rate_source_domain_display"]
        captured["child_display"] = deepcopy(display)
        requested = next(row for row in display["cells"] if row["component"] == "retained_fraction")
        assert requested["reported_domain"]["kind"] == ("unavailable" if legacy_payload else "finite_interval")
        task, steering = render_literature_experimental_prompt(inputs, "Constructed child work").split("\n\nSTEERING\n", 1)
        assert "Reported-operand numerical domains" in steering
        assert "enzyme Alpha" in steering and "enzyme Beta" in steering
        assert "not sampling confidence intervals" in steering
        return source_reason(store, args["source_ref"])
    def parent_next(inputs):
        captured["parent"] = deepcopy(inputs)
        rows = inputs["child_reports"][0]["caller_chosen_subset"]
        assert len(rows) == 1 and rows[0]["component"] == "retained_fraction"
        own_domain = inputs["literature_rate_source_domain_display"]["cells"]
        assert own_domain == (rows if domain_return else [])
        task, steering = render_literature_experimental_prompt(inputs, "Constructed receiving work").split("\n\nSTEERING\n", 1)
        assert "enzyme Alpha" in steering and "enzyme Beta" in steering
        assert "0.012" not in steering and "0.003" not in steering
        assert "Reference rate |" not in steering and "Test rate |" not in steering
        if domain_return:
            assert "Reported-operand numerical domains" in steering
            if not legacy_payload:
                assert "finite_interval" in steering and "0.25" in steering
        else:
            assert "Reported-operand numerical domains" not in steering
        return source_reason(store, args["source_ref"])
    provider = ScriptedProvider([
        {"selection": {"kind": "episode_child", "role": "literature", "assignment": assignment,
            "goal": "Compare constructed source rates.", "scope": plain(template.scope),
            "purpose": "Return only the requested numerical component.", "schema_json": json.dumps(form),
            "initial_report_json": "{}"}, "report_update": {}},
        {"selection": {"kind": "tool", "tool": "literature.rate.source.populate", "arguments": args}, "report_update": {}},
        child_next, parent_next])
    scorer = ScientificFindingProgress(FindingProgressPolicy(1))
    result = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider,
        run_dir=tmp_path / "run", controller_factory=lambda path, initial: FixtureController(str(path), initial, 2),
        project_credit=scorer, initial_known_record_refs=[args["source_ref"]],
        episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
            reference_parent_sources=[args["source_ref"]]),), binding_definitions={"credit": scorer.as_record()}))
    assert result["credit"] == 0
    assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 4
    operation, = store.db.execute("SELECT * FROM literature_rate_operations").fetchall()
    actions = store.db.execute("SELECT result FROM runtime_actions WHERE json_extract(action,'$.tool')='literature.rate.source.populate'").fetchall()
    assert len(actions) == 1 and json.loads(actions[0]["result"])["status"] == "completed"
    attempt, = store.db.execute("SELECT * FROM runtime_report_attempts").fetchall()
    assert attempt["failure"] is None
    rows = json.loads(attempt["form"])["caller_chosen_subset"]
    parent_row, = store.db.execute("SELECT * FROM runtime_episodes WHERE json_array_length(path)=1").fetchall()
    child_row, = store.db.execute("SELECT * FROM runtime_episodes WHERE json_array_length(path)=2").fetchall()
    def context(row):
        request = json.loads(row["request"])
        role = json.loads(row["path"])[-1][0]
        return BindingContext(operation["run_id"], row["episode_id"], role,
            tuple(tuple(p) for p in json.loads(row["path"])), plain(template.scope),
            request["message"].get("episode_assignment", {}), request,
            tuple(EpisodeReceipts(store, operation["run_id"]).known(row["episode_id"])))
    owner, receiver = context(child_row), context(parent_row)
    outcome = json.loads(operation["outcome"])
    sheet_ref = outcome["result"]["sheet_ref"]
    saved = LiteratureRateRepository(store, operation["run_id"]).read(sheet_ref)
    artifacts = {store.get(args["source_ref"])[field] for field in ("artifact_ref", "text_ref")}
    expected_parent_domain = captured["parent"]["literature_rate_source_domain_display"]
    store.close()
    def forbidden(*args, **kwargs):
        raise AssertionError("RO replay reacquired scientific bytes, recalculated, modeled or mutated")
    monkeypatch.setattr("gene_annotation_episode.literature_rate_storage.populate_rate_contrast", forbidden)
    monkeypatch.setattr("gene_annotation_episode.literature_rate_native_inputs.read_rate_source_inputs", forbidden)
    monkeypatch.setattr("gene_annotation_episode.providers.ModelConnection", forbidden)
    reopened = Store.__new__(Store)
    reopened.path = path.resolve();reopened._savepoint = 0
    reopened.db = sqlite3.connect((path / "state.sqlite3").as_uri() + "?mode=ro", uri=True, isolation_level=None)
    reopened.db.row_factory = sqlite3.Row
    reopened.db.execute("PRAGMA query_only=ON")
    reopened.db.create_function("library_scope_record", 2, reopened._scope_filter_record)
    get_artifact = reopened.get_artifact
    def saved_only(ref):
        if ref in artifacts:
            forbidden()
        return get_artifact(ref)
    monkeypatch.setattr(reopened, "get_artifact", saved_only)
    for method in ("put", "artifact", "transaction", "register_material", "parse_material"):
        monkeypatch.setattr(reopened, method, forbidden)
    try:
        services = WorkflowServices(SimpleNamespace(store=reopened, run_id=operation["run_id"]))
        binding = LiteratureEpisodes(services, rate_population=True, reference_parent_sources=[args["source_ref"]])
        repo = services.literature_rate_repository()
        assert repo.populate_native(owner, args, operation["operation_key"]) == outcome
        assert repo.read(sheet_ref) == saved
        view = repo.source_domain_projection() if domain_return else repo.source_projection()
        assert view.received_cells(receiver) == rows
        assert view.fact_cells(receiver, [sheet_ref], components=["reference_rate"]) == []
        assert binding._native_rate_domain_display_context(receiver)["literature_rate_source_domain_display"] == expected_parent_domain
        for column, value in (("form", json.dumps({"caller_chosen_subset": []})),):
            # Query-only mode itself forbids forging the actual runtime receipt.
            with pytest.raises(sqlite3.OperationalError):
                reopened.db.execute("UPDATE runtime_report_attempts SET " + column + "=?", (value,))
        assert reopened.db.total_changes == 0
    finally:
        reopened.close()
