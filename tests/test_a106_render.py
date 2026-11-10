"""Present actual saved A106 cells directly with their experimental context."""
from copy import deepcopy
from types import MappingProxyType

from gene_annotation_episode.literature_a106_render import assessment_groups, split_reports
from gene_annotation_episode.literature_a106_subscore_storage import LiteratureA106SubscoreRepository
from gene_annotation_episode.literature_intervention_storage import LiteratureInterventionRepository
from gene_annotation_episode.state import Store
from test_a106_paper_dataset_identity import fixture, received
from test_literature_a106_subscore import final_arguments
from test_literature_reference_parent_prompt import state, render, split


def saved_reports(tmp_path):
    with Store(tmp_path) as store:
        context, args, _, _, _ = fixture(store)
        assessments = LiteratureInterventionRepository(store, context.run_id)
        first = assessments.populate(context, args, "first")
        sheet = first["result"]["sheet_ref"]
        context = received(context, sheet)
        finals = LiteratureA106SubscoreRepository(store, context.run_id)
        final = finals.populate(context, final_arguments(store, args, sheet), "final")
        revised = deepcopy(args)
        revised["experiment_assessment"].update(revises_sheet_ref=sheet,
            revision_reason="Clarify the experimental condition.",
            conclusion="Revised conclusion keeps the original measured result.")
        second = assessments.populate(context, revised, "revision")
    return [{"assessment_cells": first["result"]["cells"], "final_cells": final["result"]["cells"]},
            {"assessment_cells": second["result"]["cells"]}]


def test_actual_saved_cells_and_final_selections_remain_exact(tmp_path):
    reports = saved_reports(tmp_path)
    before = deepcopy(reports)
    ordinary, shown = split_reports(reports)
    assert ordinary == []
    assert shown == [
        {'return_field': 'assessment_cells', 'rows': before[0]['assessment_cells']},
        {'return_field': 'final_cells', 'rows': before[0]['final_cells']},
        {'return_field': 'assessment_cells', 'rows': before[1]['assessment_cells']}]
    assert reports == before
    selected = shown[1]['rows'][0]['selected_components'][0]
    assert selected in shown[0]['rows']
    assert shown[2]['rows'][0]['experiment_assessment']['revises_sheet_ref'] == selected['sheet_ref']


def test_final_only_return_retains_selected_cells_and_unknown_extensions(tmp_path):
    reports = saved_reports(tmp_path)
    final = reports[0]["final_cells"][0]
    final["selected_components"][0]["future_qualification"] = {"reason": "Retain this condition."}
    reports = [{"score_only": [final], "empty_field": [], "interpretation": "Independent note."}]
    ordinary, shown = split_reports(reports)
    assert ordinary == [{'empty_field': [], 'interpretation': 'Independent note.'}]
    assert shown == [{'return_field': 'score_only', 'rows': [final]}]
    assert shown[0]['rows'][0]['selected_components'][0]['future_qualification'] == {
        'reason': 'Retain this condition.'}


def test_conflicting_payloads_with_same_sheet_and_component_remain_distinct(tmp_path):
    row = saved_reports(tmp_path)[0]["assessment_cells"][0]
    changed_value = {**row, "value": -101}
    changed_design = {**row, "experimental_design": {"conflict": "Different condition."}}
    reports = [{"cells": [row, changed_value, changed_design, row]}]
    _, shown = split_reports(reports)
    assert shown[0]['rows'] == reports[0]['cells']
    groups = assessment_groups(shown[0]['rows'])
    assert len(groups) == 2
    assert len(groups[0]['components']) == 2
    assert groups[0]['components'][1]['value'] == -101
    assert groups[1]['experiment']['experimental_design'] == {'conflict': 'Different condition.'}


def test_other_axes_and_partial_or_mixed_payloads_remain_untouched():
    reports = [MappingProxyType({"a105": [{"evaluation_scope": "assay", "value": 2}],
        "partial_a106": [{"axis": "A106", "component": "experimental_subscore", "value": None}],
        "mixed": [{"evaluation_scope": "intervention_experimental_evidence"}, "unknown"],
        "empty": []})]
    ordinary, shown = split_reports(reports)
    assert ordinary == reports and shown == []


def test_parent_renders_values_with_context_and_keeps_both_revisions(tmp_path):
    reports = saved_reports(tmp_path)
    value = state()
    value["reference_evidence_parent"]["evidence_axis"] = "A106"
    value["child_reports"] = reports
    value["literature_received_fact_display"] = {"received_refs": [
        row["sheet_ref"] for report in reports for rows in report.values() for row in rows]}
    before = deepcopy(value)
    _, steering = split(render(value))
    assert 'A106 saved results requested in assessment_cells' in steering
    assert 'Saved numerical components for this experiment' in steering
    assert 'Historical saved version' in steering
    assert "Revised conclusion keeps the original measured result." in steering
    for report in reports:
        for row in report["assessment_cells"]:
            assert row["sheet_ref"] in steering
    assert 'displayed_assessment_cell' not in steering
    assert 'A106 assessment 1' not in steering
    assert 'Experiment actually selected by this saved main sheet' in steering
    assert value == before
