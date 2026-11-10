"""Original perturbation measurements through A106, with synthetic engineering data."""
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import ReportBoundaryError
from gene_annotation_episode.domain import ContractError, obj
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.episode_bindings import EpisodeBindingRegistry
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_perturbation_storage import LiteraturePerturbationRepository
from gene_annotation_episode.literature_perturbation_operands import (
    LiteraturePerturbationOperandProjection, NAMESPACE, REQUESTED, cells_schema, read_operand,
)
from gene_annotation_episode.literature_intervention_storage import LiteratureInterventionRepository
from gene_annotation_episode.literature_a106_subscore_storage import LiteratureA106SubscoreRepository
from gene_annotation_episode.literature_a106_subscore import REQUESTED as FINAL_REQUESTED, COMPONENTS as FINAL_COMPONENTS
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_literature_perturbation_summary_integration import fixture, source
from test_literature_perturbation_integration import setup_case
from test_literature_intervention_storage import intervention_fixture
from test_literature_a106_subscore import final_arguments


SELECTED = ["perturbation_difference", "perturbation_mean_variance"]


def select(sheet, component):
    return dict(kind="received_component", namespace=NAMESPACE, sheet_ref=sheet, component=component)


def prepare(path, *, paired=True):
    store, context, args = fixture(path, paired=paired)
    context = replace(context, assignment={**context.assignment, REQUESTED: SELECTED})
    writer = LiteraturePerturbationRepository(store, context.run_id)
    outcome = writer.populate(context, args, "original-measurement")
    context = replace(context, received_record_refs=(*context.received_record_refs, *outcome["record_refs"]))
    sheet = outcome["result"]["sheet_ref"]
    view = LiteraturePerturbationOperandProjection(store, context.run_id)
    rows = view.fact_cells(context, [sheet], components=SELECTED)
    return store, context, args, sheet, view, rows


@pytest.mark.parametrize("paired", [True, False])
def test_exact_measurements_and_covariance_reach_grader_and_final_receipt(tmp_path, monkeypatch, paired):
    store, reader, _, sheet, view, rows = prepare(tmp_path, paired=paired)
    with store:
        assert rows[0]["cell"]["value"] == 9
        assert rows[1]["cell"]["value"] == (pytest.approx(1/3) if paired else None)
        assert rows[0]["cell"]["measurement_keys"] == rows[1]["cell"]["measurement_keys"]
        assert len(rows[0]["cell"]["measurement_keys"]) == 4
        context, args = intervention_fixture(store)
        context = replace(context, run_id=reader.run_id,
            received_record_refs=tuple(dict.fromkeys((*context.received_record_refs, *reader.received_record_refs))))
        read = lambda ctx, namespace, ref, components: view.fact_cells(ctx, [ref], components=components)
        with pytest.raises(ContractError, match="component_not_received"):
            read_operand(select(sheet, SELECTED[0]), role="effect", quantity_kind="endpoint_difference",
                read_cells=lambda *a: read(context, *a))
        view.receive_cells(context, rows, "reader-to-grader")
        args.update(quantity_kind="endpoint_difference", prediction_model=None)
        args["quantities"].update(effect=select(sheet, SELECTED[0]), effect_variance=select(sheet, SELECTED[1]),
            assertion_prediction=None, alternative_prediction=None)
        repo = LiteratureInterventionRepository(store, context.run_id, read_cells=read)
        outcome = repo.populate(context, args, "grade-measurement")
        assessment = outcome["result"]["sheet_ref"]
        saved = repo.read(assessment)
        assert saved["sheet"]["cells"]["measured_effect"]["value"] == 9
        assert saved["sheet"]["cells"]["effect_variance"]["value"] == (pytest.approx(1/3) if paired else None)
        assert saved["sheet"]["cells"]["source_log_evidence_ratio"]["value"] is None
        if paired:
            bad = deepcopy(args)
            bad["prediction_model"] = dict(kind="fixed_predictions_known_normal", variance_interpretation="known",
                support_refs=[args["experiment_ref"]])
            with pytest.raises(ContractError, match="known_variance_conflicts_with_reader"):
                repo.populate(context, bad, "false-known-variance")
        context = replace(context, received_record_refs=(*context.received_record_refs, assessment),
            assignment={**context.assignment, FINAL_REQUESTED: list(FINAL_COMPONENTS)})
        final_repo = LiteratureA106SubscoreRepository(store, context.run_id)
        final = final_repo.populate(context, final_arguments(store, args, assessment), "final")
        cell = final["result"]["cells"][0]
        assert cell["value"] is None and len(cell["selected_components"]) == 1
        assert set(cell["evidence_measurement_keys"]) == set(rows[0]["cell"]["measurement_keys"])
        parent = replace(context, episode_id="parent", role="annotation", path=(("annotation", "root"),),
            received_record_refs=(*context.received_record_refs, final["result"]["sheet_ref"]))
        final_repo.receive_cells(parent, [cell], "final-to-parent")
        def forbidden(*_a, **_k):
            raise AssertionError("Cold replay must not recalculate science")
        monkeypatch.setattr(LiteratureInterventionRepository, "grade", forbidden)
        monkeypatch.setattr("gene_annotation_episode.literature_perturbation_storage.populate_source_summary_restoration", forbidden)
        store.db.execute("PRAGMA query_only=ON")
        assert view.fact_cells(context, [sheet], components=SELECTED) == rows
        assert final_repo.fact_cells(parent, [cell["sheet_ref"]], components=FINAL_COMPONENTS) == [cell]


def test_binding_exposes_only_requested_original_operands(tmp_path):
    store, context, _, sheet, view, rows = prepare(tmp_path)
    with store:
        host = SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store))
        binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True, a106_intervention=True)
        host.episode_bindings = EpisodeBindingRegistry((binding,))
        form, schema = {"measurements": rows}, obj({"measurements": cells_schema()})
        assert binding.facts(context, {"committed_record_refs": [sheet]})[NAMESPACE] == rows
        binding.validate_report(context, form, schema)
        changed_schema = deepcopy(schema)
        changed_schema["properties"]["measurements"]["items"]["properties"]["cell"]["required"].remove("measurement_keys")
        with pytest.raises(ReportBoundaryError, match="must match its registered source"):
            binding.validate_report(context, form, changed_schema)
        parent = replace(context, episode_id="parent", role="annotation", path=(("annotation", "root"),), assignment={})
        references = binding.received_form_references(parent, form, schema, "original-return")
        assert sheet in references
        assert binding.received_report_facts(parent)[NAMESPACE] == rows
        assert view.fact_cells(parent, [sheet], components=["restoration_difference"]) == []
        changed = deepcopy(rows)
        changed[0]["cell"]["measurement_keys"] = ["fabricated-independent-observation"]
        with pytest.raises(ContractError, match="differs_from_saved"):
            view.validate_returned_values(changed, permitted_record_refs=context.received_record_refs)


def test_original_point_sheet_keeps_missing_variance_and_separate_return_custody(tmp_path):
    store, context, args = setup_case(tmp_path)
    with store:
        writer = LiteraturePerturbationRepository(store, context.run_id)
        outcome = writer.populate(context, args, "point-measurement")
        sheet = outcome["result"]["sheet_ref"]
        context = replace(context, received_record_refs=(*context.received_record_refs, *outcome["record_refs"]))
        view = LiteraturePerturbationOperandProjection(store, context.run_id)
        rows = view.fact_cells(context, [sheet], components=SELECTED)
        assert [row["component"] for row in rows] == ["perturbation_difference"]
        assert rows[0]["cell"]["value"] == 80
        old_rows = writer.fact_cells(context, [sheet], components=["perturbation_difference"])
        parent = replace(context, episode_id="point-parent", role="annotation", path=(("annotation", "root"),))
        writer.receive_cells(parent, old_rows, "old-point-return")
        assert view.fact_cells(parent, [sheet], components=SELECTED) == []
        view.receive_cells(parent, rows, "new-point-return")
        assert view.fact_cells(parent, [sheet], components=SELECTED) == rows


@pytest.mark.parametrize("component", ["reference_restoration_index", "restoration_agreement",
    "perturbation_variance_upper", "W_reported_spread", "shared_contrast_covariance"])
def test_diagnostics_and_covariance_bounds_cannot_become_effect_variance(component):
    def forbidden(*_a):
        raise AssertionError("Invalid operand must be rejected before reading any sheet")
    with pytest.raises(ContractError, match="quantity_role_mismatch"):
        read_operand(select("source_test", component), role="effect_variance",
            quantity_kind="endpoint_difference", read_cells=forbidden)


def test_duplicate_acquisition_retains_common_physical_measurement_identity(tmp_path):
    store, context, args, _, view, rows = prepare(tmp_path)
    with store:
        raw = store.get_artifact(store.get(args["data_source_ref"])["artifact_ref"])
        duplicate = source(store, raw)  # distinct provenance, identical original bytes
        assert duplicate["id"] != args["data_source_ref"]
        context = replace(context, received_record_refs=(*context.received_record_refs, duplicate["id"]))
        args = {**args, "data_source_ref": duplicate["id"]}
        outcome = LiteraturePerturbationRepository(store, context.run_id).populate(context, args, "reacquired")
        context = replace(context, received_record_refs=(*context.received_record_refs, *outcome["record_refs"]))
        second = view.fact_cells(context, [outcome["result"]["sheet_ref"]], components=SELECTED)
        shared = set(rows[0]["cell"]["measurement_keys"]) & set(second[0]["cell"]["measurement_keys"])
        assert len(shared) == 2


def test_projection_discovery_is_read_only_without_receipt_tables(tmp_path):
    with Store(tmp_path) as store:
        store.db.execute("PRAGMA query_only=ON")
        view = LiteraturePerturbationOperandProjection(store, "original-run")
        assert not view._installed()
        assert view.project_cells([], permitted_record_refs=[], components=SELECTED) == []
