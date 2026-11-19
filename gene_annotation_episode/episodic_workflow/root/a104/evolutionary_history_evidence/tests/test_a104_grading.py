"""The A104 grading of the head through the real runner on a real Store, without a model.

The head is linked with the public API (``link``) and stepped with ``EpisodeRun.next_decision`` (the Episode is
entered as ``run()`` enters it: its yield controller is built from ``credit`` of the initial summary; ``decide`` is
called; the model is not asked) and ``EpisodeRun.run_unit`` (one journaled tool unit with its controller step). The
measurement tools need a native phylogeny this Episode holds; a native result enters custody only through the HPC
import (``AXIS_WAVE_BLOCKERS_a104.md``), so the units here run the tools' own refusals on the records the world
holds, and the sheet builders' rules run on the retained native fixture of PBS job 9040517. Nothing is faked."""
import asyncio
import importlib
import json
from pathlib import Path

import pytest

from episode_runtime import ModelRequest, ToolCall
from gene_annotation_episode.episodic_workflow.episode_support.grading.evolutionary_history_evidence import (
    characterization, history_explanation, native_publications, scoring)

from .a104_world import linked, world as a104_world

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(PACKAGE + '.episode').EvolutionaryHistoryEvidence
TASK = importlib.import_module(PACKAGE + '.task')
FINAL = importlib.import_module(PACKAGE + '.messages.final_to_parent')
NATIVE = json.loads((Path(scoring.__file__).parent / 'tests' / 'fixtures' / 'a104' / 'real' / 'mj0044' /
                     'native-pbs-9040517.json').read_text())


def test_the_first_decision_offers_the_phylogeny_tools_with_the_owners_grading_instructions(tmp_path):
    state = a104_world(tmp_path)
    run = linked(state, 'a104-first-decision')
    request = asyncio.run(run.next_decision())
    view = run.view
    summary = EPISODE()._summary(view)
    assert summary['a104_sheets'] == [] and summary['credit_view']['credit'] == 0
    assert EPISODE.credit(summary, view.records) == 0
    assert view.controller_state is not None
    target, = summary['a104_targets']
    assert target['target_refs'] == [state['target']] and target['attribution_status'] == \
        'no_received_native_phylogeny_test'
    assert isinstance(request, ModelRequest) and request.role == 'REASONING'
    schema = json.dumps(request.output_schema)
    for library_name, _, _ in TASK.PHYLOGENY_TOOLS.values():
        assert '"' + library_name + '"' in schema
    assert '"report"' not in schema
    assert TASK.GRADING_SECTION in request.instructions and TASK.RETURN_GUIDANCE in request.instructions
    assert 'contradicted (0)' in request.instructions and 'never a weight on the native tree score' in \
        request.instructions
    assert request.context['a104_sheets'] == [] and 'reports' not in request.context
    result = EPISODE.final_to_parent(summary, {'ended_by': 'yield_stop', 'units_consumed': 0, 'credit': 0.0},
                                     ('committed_record_refs',))
    assert FINAL.RETURN_FORM.select(('committed_record_refs',)).admit(result, 'return') == result
    state['store'].close()


def test_a_measurement_of_an_unheld_phylogeny_is_a_returned_refusal_that_enters_the_iterator(tmp_path):
    state = a104_world(tmp_path)
    run = linked(state, 'a104-refusals')
    scope = state['assignment']['scope']
    placement = asyncio.run(run.run_unit(ToolCall('phylogeny_measure_placement', {
        'arguments': {'native_ref': 'source_' + 'a' * 24, 'analysis': 'family', 'split_index': 9},
        'scope': scope})))
    assert placement['outcome']['status'] == 'invalid'
    assert placement['outcome']['feedback']['code'] == 'a104_tool_input_not_received'
    cause = asyncio.run(run.run_unit(ToolCall('phylogeny_explain_history', {
        'arguments': {'measurement_ref': state['hypothesis'], 'grade': 'plausible_only', 'support_refs': []},
        'scope': scope})))
    assert cause['outcome']['status'] == 'invalid'
    assert cause['outcome']['feedback']['code'] == 'a104_history_explanation_requires_actual_phylogeny'
    assert [outcome['tool'] for outcome in run.view.outcomes] == ['phylogeny_measure_placement',
                                                                 'phylogeny_explain_history']
    assert EPISODE()._summary(run.view)['a104_sheets'] == []
    state['store'].close()


@pytest.mark.parametrize(('grade', 'score'), [('contradicted', 0), ('plausible_only', 1), ('corroborated', 2)])
def test_the_history_explanation_is_an_ordinal_judged_cell(grade, score):
    cell = history_explanation.explanation_cell(grade)
    assert cell['score'] == score and cell['score_bounds'] == {'lower': score, 'upper': score}
    assert cell['score_unit'] == 'ordinal_evidence_level'


def test_an_unknown_history_explanation_keeps_the_possible_levels_without_a_zero():
    cell = history_explanation.explanation_cell('unknown')
    assert cell['score'] is None and cell['status'] == 'partial' and cell['score_bounds'] == {'lower': 0, 'upper': 2}
    with pytest.raises(ValueError):
        history_explanation.explanation_cell('likely')


def test_a_native_sheet_grades_four_kinds_on_the_unit_interval_and_keeps_an_unevaluable_value_unknown():
    body = {'schema': 'a104_robustness_v1', 'version': scoring.VERSION, 'producer_operation': 'phylogeny.x',
            'target_ref': 'input_x', 'raw_value': None}
    assert native_publications.native_grade(body)['raw_value'] is None
    assert native_publications.native_grade({**body, 'raw_value': 0.9})['kind'] == 'robustness'
    with pytest.raises(ValueError, match='a104_native_value_outside_unit_interval'):
        native_publications.native_grade({**body, 'raw_value': 92})
    with pytest.raises(ValueError, match='a104_native_metric_schema_not_bound'):
        native_publications.native_grade({**body, 'schema': 'a104_posterior_v1'})
    assert set(native_publications.KINDS.values()) == {'placement', 'history_comparison', 'clade_composition',
                                                      'robustness'}


def test_the_clade_sheet_counts_characterized_members_and_keeps_the_target_activity_separate():
    links = [{'reference_ref': 'reference_a', 'function_key': 'k1', 'function_identity_status': 'received_term_identifier',
              'observation_ref': 'observation_1', 'hypothesis_ref': 'h', 'assessment_ref': 'a', 'sheet_ref': 's',
              'evidence_source_ref': 'src'}]
    sheet = characterization.clade_sheet({'reference_a', 'reference_b'}, links)
    assert sheet['characterized_subject_refs'] == ['reference_a'] and sheet['unknown_subject_refs'] == ['reference_b']
    assert sheet['characterized_fraction'] == 0.5 and sheet['independent_assay_observation_count'] == 1
    assert sheet['status'] == 'partially_characterized'
    assert sheet['interpretation'].endswith('target_activity_separate')
    mixed = characterization.clade_sheet({'reference_a', 'reference_b'}, [
        *links, {**links[0], 'reference_ref': 'reference_b', 'function_key': 'k2',
                 'function_identity_status': 'source_local_assertion', 'observation_ref': 'observation_2'}])
    assert mixed['status'] == 'function_identity_mapping_unresolved'


def test_the_same_physical_relationship_is_found_across_native_analyses_of_the_real_fixture():
    inventory = scoring.relationship_inventory(NATIVE)
    agreeing = [row for row in inventory if any(item['analysis'] == 'family' and item['split_index'] == 9
                                                for item in row['occurrences'])]
    assert len({item['analysis'] for item in agreeing[0]['occurrences']}) == 2
    assert scoring.SUPPORT_KINDS[NATIVE['result']['analyses'][0]['support_method']] == 'bootstrap_fraction'
