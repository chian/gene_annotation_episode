"""Synthetic A106 scoring and custody tests, not a live biological demonstration."""
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.state import Store
from gene_annotation_episode.literature_intervention_storage import LiteratureInterventionRepository
from gene_annotation_episode.literature_a106_subscore import (
    finalize_a106, SCORE_COMPONENT, REQUESTED, COMPONENTS, cells_schema,
)
from gene_annotation_episode.literature_a106_subscore_storage import LiteratureA106SubscoreRepository
from test_literature_intervention_storage import intervention_fixture


def final_arguments(store, args, sheet_ref):
    return dict(subject_ref=store.get(args["assertion_ref"])["subject_refs"][0],
        assertion_ref=args["assertion_ref"], comparison_ref=args["comparison_ref"],
        scope_statement="Synthetic stipulated model only.",
        experiments=[dict(experiment_ref=args["experiment_ref"], sheet_ref=sheet_ref, missing_reason=None)],
        dependence=dict(status="unknown", rationale="One experiment", witnesses=[]),
        conclusion="Engineered evidence favors the assertion.", limitations=["No biological evidence."],
        revises_subscore_ref=None, revision_reason=None)


def prepared(store):
    store.create_problem(raw_sequence="ATGGCT", molecule="dna")
    context, args = intervention_fixture(store)
    native = LiteratureInterventionRepository(store, context.run_id)
    first = native.populate(context, args, "assessment")
    ref = first["result"]["sheet_ref"]
    context = replace(context, received_record_refs=[*context.received_record_refs, ref],
        assignment={**context.assignment, REQUESTED: list(COMPONENTS)})
    rows = native.fact_cells(context, [ref], components=[SCORE_COMPONENT])
    return context, args, final_arguments(store, args, ref), rows


def test_final_score_is_the_existing_signed_ratio_and_is_not_a_probability(tmp_path):
    with Store(tmp_path) as store:
        _, _, args, rows = prepared(store)
        cell = finalize_a106(args, rows)
        assert cell["value"] == pytest.approx(7.5)
        assert cell["status"] == "complete" and cell["annotation_credit"] is None
        rows[0]["value"] = -7.5
        assert finalize_a106(args, rows)["value"] == -7.5


def test_unavailable_assessment_feedback_keeps_the_typed_sheet_selection(tmp_path):
    with Store(tmp_path) as store:
        _, _, args, rows = prepared(store)
        rows[0].update(value=None, status="unavailable")
        args["experiments"][0]["missing_reason"] = "The selected assessment has unresolved inputs."
        with pytest.raises(ContractError, match="existing_assessment_requires_null_missing_reason") as caught:
            finalize_a106(args, rows)
        assert caught.value.detail["field"] == "experiments.0.missing_reason"
        assert caught.value.detail["sheet_ref"] == rows[0]["sheet_ref"]
        args["experiments"][0]["missing_reason"] = None
        final = finalize_a106(args, rows)
        assert final["value"] is None and final["selected_components"] == rows
        assert final["experiments"][0]["sheet_ref"] == rows[0]["sheet_ref"]


def test_scope_change_reports_question_mismatch_without_rewriting_predecessor(tmp_path):
    with Store(tmp_path) as store:
        context, _, args, _ = prepared(store)
        repo = LiteratureA106SubscoreRepository(store, context.run_id)
        first = repo.populate(context, args, "first-scope")
        ref = first["result"]["sheet_ref"]
        context = replace(context, received_record_refs=[*context.received_record_refs, ref])
        proposed = deepcopy(args)
        proposed.update(scope_statement="A different synthetic biological scope.",
            revises_subscore_ref=ref, revision_reason="Attempted scope expansion")
        with pytest.raises(ContractError, match="revision_question_mismatch") as caught:
            repo.populate(context, proposed, "changed-scope")
        assert caught.value.detail["different_fields"] == ["scope_statement"]
        assert caught.value.detail["previous_question"]["scope_statement"] == args["scope_statement"]
        assert repo.read(ref)["selection"] == args
        # Keep the original question when the intended correction is its conclusion.
        proposed.update(scope_statement=args["scope_statement"], conclusion="Corrected conclusion within the original scope.")
        corrected = repo.populate(context, proposed, "corrected-conclusion")
        saved = repo.read(corrected["result"]["sheet_ref"])
        assert saved["selection"]["revises_subscore_ref"] == ref
        assert saved["selection"]["scope_statement"] == args["scope_statement"]


def test_missing_conflicting_and_duplicate_evidence_preserve_their_meaning(tmp_path):
    with Store(tmp_path) as store:
        _, _, args, rows = prepared(store)
        second = deepcopy(rows[0])
        second.update(sheet_ref="source_" + "b" * 24, experiment_ref="reference_" + "b" * 24,
            value=-2., evidence_measurement_keys=["independent_observed_measurement"])
        args["experiments"].append(dict(experiment_ref=second["experiment_ref"],
            sheet_ref=second["sheet_ref"], missing_reason=None))
        unknown = finalize_a106(args, [*rows, second])
        assert unknown["value"] is None and unknown["available_value"] is None
        args["dependence"] = dict(status="independent", rationale="Stipulated independent biological units",
            witnesses=[dict(source_ref=rows[0]["evidence_source_ref"], representation="original", start=0, end=1, quote="E")])
        assert finalize_a106(args, [*rows, second])["value"] == pytest.approx(5.5)
        second["evidence_measurement_keys"] = rows[0]["evidence_measurement_keys"]
        shared = finalize_a106(args, [*rows, second])
        assert shared["value"] is None and "shared_observed_measurement" in shared["unavailable_reasons"]
        second["evidence_measurement_keys"] = ["independent_observed_measurement"]
        second.update(value=None, status="unavailable")
        partial = finalize_a106(args, [*rows, second])
        assert partial["value"] is None and partial["available_value"] == pytest.approx(7.5)
        args["experiments"].append(deepcopy(args["experiments"][0]))
        with pytest.raises(ContractError, match="duplicate_experiment"):
            finalize_a106(args, [*rows, second])


def test_final_custody_revisions_missing_experiments_and_cold_replay(tmp_path, monkeypatch):
    with Store(tmp_path) as store:
        context, assessment, args, rows = prepared(store)
        repo = LiteratureA106SubscoreRepository(store, context.run_id)
        final = repo.populate(context, args, "final")
        ref = final["result"]["sheet_ref"]
        assert final["result"]["cells"][0]["value"] == pytest.approx(7.5)
        assert repo.populate(context, args, "final") == final
        with pytest.raises(ContractError, match="latest_subscore_revision"):
            repo.populate(context, args, "duplicate")
        parent = replace(context, episode_id="parent", role="annotation", path=(("annotation", "parent"),),
            received_record_refs=[*context.received_record_refs, ref])
        delivered = final["result"]["cells"]
        repo.receive_cells(parent, delivered, "delivery")
        assert repo.fact_cells(parent, [ref], components=list(COMPONENTS)) == delivered
        # A source handle does not give another episode a private numeric cell.
        stranger = replace(parent, episode_id="stranger", path=(("annotation", "stranger"),))
        with pytest.raises(ContractError, match="component_not_received"):
            repo.populate(stranger, args, "unreceived")
        revision = deepcopy(assessment)
        revision["experiment_assessment"].update(revises_sheet_ref=rows[0]["sheet_ref"], revision_reason="Resolve a conflict")
        revision["interpretations"]["attribution_supported"] = dict(status="unknown", support_refs=[])
        native = LiteratureInterventionRepository(store, context.run_id)
        changed = native.populate(context, revision, "changed")
        context = replace(context, received_record_refs=[*context.received_record_refs, ref, changed["result"]["sheet_ref"]])
        args.update(revises_subscore_ref=ref, revision_reason="Use the revised experiment assessment")
        with pytest.raises(ContractError, match="current_assessment_required"):
            repo.populate(context, args, "stale-assessment")
        args["experiments"][0]["sheet_ref"] = changed["result"]["sheet_ref"]
        updated = repo.populate(context, args, "updated")
        assert updated["result"]["cells"][0]["value"] is None
        assert repo.read(ref)["sheet"]["cells"][COMPONENTS[0]]["value"] == pytest.approx(7.5)
    def forbidden(*args, **kwargs):
        raise AssertionError("saved final replay recalculated science")
    monkeypatch.setattr("gene_annotation_episode.literature_a106_subscore_storage.finalize_a106", forbidden)
    monkeypatch.setattr(LiteratureInterventionRepository, "grade", forbidden)
    with Store(tmp_path) as store:
        store.db.execute("PRAGMA query_only=ON")
        repo = LiteratureA106SubscoreRepository(store, context.run_id)
        assert repo.fact_cells(parent, [ref], components=list(COMPONENTS)) == delivered


@pytest.mark.parametrize("repair_support", [False, True])
def test_runtime_delivers_final_a106_subscore_to_parent(tmp_path, repair_support):
    import asyncio
    from functools import partial
    from gene_annotation_episode.communication import plain
    from gene_annotation_episode.domain import obj
    from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
    from gene_annotation_episode.literature_episodes import LiteratureEpisodes
    from gene_annotation_episode.runtime import run_workflow
    from gene_annotation_episode.tools import ToolRegistry
    from test_runtime import FixtureController, ScriptedProvider

    with Store(tmp_path / "state") as store:
        store.create_problem(raw_sequence="ATGGCT", molecule="dna")
        context, args = intervention_fixture(store)
        assignment = {**plain(context.assignment), REQUESTED: list(COMPONENTS)}
        def finalize(_):
            ref = json.loads(store.db.execute("SELECT outcome FROM literature_intervention_grading_operations").fetchone()[0])["result"]["sheet_ref"]
            return dict(selection=dict(kind="tool", tool="literature.a106.finalize",
                arguments=final_arguments(store, args, ref)), report_update={})
        invalid_support = deepcopy(args)
        invalid_support["interpretations"]["measurement_identity"]["support_refs"] = [args["source_ref"]]
        provider = ScriptedProvider([
            dict(selection=dict(kind="episode_child", role="literature", assignment=assignment,
                goal="Assess this synthetic intervention", scope=plain(context.scope), purpose="Return final conditional evidence",
                schema_json=json.dumps(obj({"subscore":cells_schema()})), initial_report_json="{}"), report_update={}),
            *([dict(selection=dict(kind="tool", tool="literature.intervention_grading.populate",
                arguments=invalid_support), report_update={})] if repair_support else []),
            dict(selection=dict(kind="tool", tool="literature.intervention_grading.populate", arguments=args), report_update={}),
            finalize])
        controllers = []
        def controller(path, initial):
            result = FixtureController(str(path), initial, 1 if not controllers else 2)
            controllers.append(result)
            return result
        credit = ScientificFindingProgress(FindingProgressPolicy(1))
        result = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider,
            run_dir=tmp_path / "workflow", controller_factory=controller,
            project_credit=credit, initial_known_record_refs=list(context.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True, a106_intervention=True),),
            binding_definitions={"credit":credit.as_record()}))
        receipt = store.db.execute("SELECT cells FROM literature_a106_subscore_received").fetchone()
        assert receipt is not None
        assert json.loads(receipt[0])[0]["value"] == pytest.approx(7.5)
        assert result["credit"] == 0
        if repair_support:
            outcomes = [json.loads(row[0]) for row in store.db.execute("SELECT result FROM runtime_actions")]
            failure = next(row["feedback"] for row in outcomes if row.get("status") == "invalid")
            assert failure["code"] == "assay_grading_anchored_support_required"
            assert failure["detail"]["field"] == "interpretations.measurement_identity.support_refs"
            assert failure["detail"]["reference"] == args["source_ref"]
            assert failure["detail"]["expected_record_type"] == "reference"
