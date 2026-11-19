"""The experiment assessments of the shared literature module and of the three axis copies keep what each sheet
saved as a row of a declared work table, and read the heads, the history and the saved-assessment check from the
rows the Episode holds. Real Store, journal and runner; the probe episode calls them through ``ctx.store``."""
import pytest

from gene_annotation_episode.episodic_workflow.episode_support.grading.tests.library_probe.harness import (
    calls, open_store, run_plan)

PREFIX = 'gene_annotation_episode.episodic_workflow.episode_support.literature.grading.'
MODULES = (PREFIX + 'literature_experiment_assessments',
           PREFIX + 'experimental_activity_evidence.literature_perturbation_assessments',
           PREFIX + 'evolutionary_history_evidence.literature_perturbation_assessments',
           PREFIX + 'perturbation_evidence.literature_perturbation_assessments')
CALLS = 'gene_annotation_episode.episodic_workflow.episode_support.literature.grading.tests.assessment_calls:'


@pytest.mark.parametrize('module', MODULES)
def test_an_assessment_is_a_row_of_the_episode_and_its_revision_replaces_it_as_head(tmp_path, module):
    world = open_store(tmp_path)
    plan = calls((CALLS + 'begin', {'module': module}), (CALLS + 'revise', {'module': module}),
                 (CALLS + 'inspect', {'module': module}))
    begun, revised, inspected = run_plan(world, 'assess', plan)
    assert [head['sheet_ref'] for head in begun['heads']] == [begun['sheet']]
    assert begun['row'].startswith('row_')
    assert revised['blind'].endswith('assessment_revision_required')
    assert revised['revises'] == begun['sheet']
    assert inspected['heads'] == [revised['sheet']]
    assert inspected['history'] == [begun['sheet'], revised['sheet']]
    assert inspected['first_row_unit'] < inspected['second_row_unit']
    assert inspected['wrong_assessment'].endswith('assessment_saved_mismatch')
    assert inspected['wrong_operation'].endswith('assessment_saved_mismatch')
    world['store'].close()
