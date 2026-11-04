"""Existing published-table reader to A106 custody; synthetic engineering data."""
from copy import deepcopy
from dataclasses import replace

import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.literature_intervention_inputs import (
    COMPARISON_NAMESPACE, read_comparison_operand,
)
from gene_annotation_episode.literature_intervention_storage import LiteratureInterventionRepository
from gene_annotation_episode.literature_a106_subscore import REQUESTED as FINAL_REQUESTED, COMPONENTS as FINAL_COMPONENTS
from gene_annotation_episode.literature_a106_subscore_storage import LiteratureA106SubscoreRepository
from gene_annotation_episode.state import Store
from test_literature_intervention_storage import intervention_fixture
from test_literature_a106_subscore import final_arguments
from test_literature_measurement_comparison_binding_268 import setup, selected


def operand(sheet_ref, component):
    return dict(kind="received_component", namespace=COMPARISON_NAMESPACE,
        sheet_ref=sheet_ref, component=component)


@pytest.mark.parametrize("variance_status", ["known", "estimated"])
def test_table_comparison_reaches_intervention_grader_with_custody_and_uncertainty(tmp_path, monkeypatch, variance_status):
    components = ["native_left", "protocol_difference", "protocol_ratio", "difference_variance"]
    store, reader_context, selection, binding, _ = setup(tmp_path, components=components,
        table=True, covariance=[[4, 1], [1, 9]], variance_status=variance_status)
    try:
        reader_context, outcome, rows = selected(store, reader_context, selection, binding)
        sheet_ref = outcome["result"]["sheet_ref"]
        context, args = intervention_fixture(store)
        context = replace(context, run_id=reader_context.run_id,
            received_record_refs=tuple(dict.fromkeys((*context.received_record_refs, *reader_context.received_record_refs))))
        comparison_repo = binding._measurement_comparison_repository()
        # Possessing the sheet ref alone does not authorize the child reader's cells.
        with pytest.raises(ContractError, match="component_not_received"):
            read_comparison_operand(operand(sheet_ref, "protocol_difference"), role="effect",
                quantity_kind="endpoint_difference", read_cells=lambda *args:
                    binding._assay_grading_source_cells(context, *args))
        comparison_repo.receive_cells(context, rows, "comparison-to-intervention")
        args.update(quantity_kind="endpoint_difference", prediction_model=None)
        args["quantities"].update(effect=operand(sheet_ref, "protocol_difference"),
            effect_variance=operand(sheet_ref, "difference_variance"), assertion_prediction=None, alternative_prediction=None)
        repo = LiteratureInterventionRepository(store, context.run_id,
            read_cells=binding._assay_grading_source_cells)
        result = repo.populate(context, args, "table-to-intervention")
        ref = result["result"]["sheet_ref"]
        saved = repo.read(ref)
        effect, variance = (saved["extraction"]["quantities"][name] for name in ("effect", "effect_variance"))
        assert effect["value"] == -2 and effect["unit"] == "umol/min/mg"
        assert variance["value"] == 11 and variance["unit"] == "(umol/min/mg)^2"
        assert ("estimated_covariance" in variance["qualifications"]) == (variance_status == "estimated")
        measurement_keys = [row["owner_key"] for row in rows[1]["dependencies"]]
        assert measurement_keys and set(measurement_keys) <= set(effect["measurement_keys"])
        assert effect["origin"] == variance["origin"] == "synthetic"
        assert saved["sheet"]["cells"]["measured_effect"]["value"] == -2
        assert saved["sheet"]["cells"]["effect_variance"]["value"] == 11
        assert saved["sheet"]["cells"]["source_log_evidence_ratio"]["value"] is None
        rejected = deepcopy(args)
        rejected["quantities"]["effect"] = operand(sheet_ref, "native_left")
        with pytest.raises(ContractError, match="quantity_role_mismatch"):
            repo.populate(context, rejected, "wrong-quantity")
        rejected = deepcopy(args)
        rejected["quantities"]["effect_variance"] = operand(sheet_ref, "protocol_ratio")
        with pytest.raises(ContractError, match="quantity_role_mismatch"):
            repo.populate(context, rejected, "ratio-is-not-variance")
        if variance_status == "estimated":
            rejected = deepcopy(args)
            rejected["prediction_model"] = dict(kind="fixed_predictions_known_normal", variance_interpretation="known",
                support_refs=[args["experiment_ref"]])
            with pytest.raises(ContractError, match="known_variance_conflicts_with_reader"):
                repo.populate(context, rejected, "estimated-is-not-known")
        context = replace(context, received_record_refs=(*context.received_record_refs, ref),
            assignment={**context.assignment, FINAL_REQUESTED: list(FINAL_COMPONENTS)})
        final_repo = LiteratureA106SubscoreRepository(store, context.run_id)
        final_args = final_arguments(store, args, ref)
        final_args["conclusion"] = "Synthetic measurements retained; independent predictions and model remain absent."
        final = final_repo.populate(context, final_args, "final-unavailable")
        final_ref = final["result"]["sheet_ref"]
        final_cell = final["result"]["cells"][0]
        assert final_cell["value"] is None and final_cell["status"] == "unavailable"
        assert final_cell["selected_components"][0]["sheet_ref"] == ref
        assert set(measurement_keys) <= set(final_cell["evidence_measurement_keys"])
        context = replace(context, received_record_refs=(*context.received_record_refs, final_ref))
        parent = replace(context, episode_id="parent", role="annotation", path=(("annotation", "parent"),))
        final_repo.receive_cells(parent, final["result"]["cells"], "final-to-parent")
        delivered = final_repo.fact_cells(parent, [final_ref], components=list(FINAL_COMPONENTS))
    finally:
        store.close()
    def forbidden(*args, **kwargs):
        raise AssertionError("Replay must not reread or recalculate measurements")
    monkeypatch.setattr(LiteratureInterventionRepository, "read_inputs", forbidden)
    monkeypatch.setattr(LiteratureInterventionRepository, "grade", forbidden)
    with Store(tmp_path) as store:
        store.db.execute("PRAGMA query_only=ON")
        assert LiteratureA106SubscoreRepository(store, context.run_id).fact_cells(
            parent, [final_ref], components=list(FINAL_COMPONENTS)) == delivered


@pytest.mark.parametrize("component", ["standardized_difference", "squared_standardized_difference", "weight_left",
    "combined_estimate", "required_interference_scenario", "difference_standard_uncertainty", "difference_variance"])
def test_comparison_statistics_and_scenarios_cannot_supply_intervention_effect(component):
    def forbidden(*args):
        raise AssertionError("Invalid quantity routes should fail before accessing cells")
    with pytest.raises(ContractError, match="quantity_role_mismatch"):
        read_comparison_operand(operand("source_synthetic", component), role="effect",
            quantity_kind="endpoint_difference", read_cells=forbidden)
