"""Source navigation must not repeat a previously admitted numerical result.

The retained A11038 context reproduces an actual transport rejection. These
checks reconstruct its completed-work presentation without a model or job;
they do not impose an episode budget or claim autonomous completion.
"""
from copy import deepcopy
import gzip
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest

from gene_annotation_episode import a107_work_report, a110_work_report
from gene_annotation_episode.component_axis_literature_prompt import with_fact_contract_instructions
from gene_annotation_episode.episode_work_report import completed_action_reports
from gene_annotation_episode.scientific_process_prompt import render_scientific_process_prompt


FIXTURE = Path(__file__).parent / 'fixtures/work_reports/a11038-source-navigation.json.gz'


def retained_trace():
    return json.loads(gzip.decompress(FIXTURE.read_bytes()))


def native_result(axis):
    if axis == 'A110':
        return retained_trace()['state']['received_partner_and_chemical_native_components']['scientific_results'][0]
    return {'axis': 'A107', 'source_ref': 'source_received_expression',
        'native_components': {'version': 'a107_expression_components_v2',
            'dataset_id': 'declared-expression', 'components': {'matched_sample_count': 3},
            'limitations': ['Expression does not demonstrate required partnership.']}}


@pytest.mark.parametrize('axis,adapter', [('A107', a107_work_report), ('A110', a110_work_report)])
@pytest.mark.parametrize('tool', ['source.read', 'source.locate'])
def test_navigation_source_identity_does_not_repeat_whole_native_result(axis, adapter, tool):
    native = native_result(axis)
    selection = {'kind': 'tool', 'tool': tool,
        'arguments': {'source_ref': native['source_ref']}}
    outcome = {'status': 'completed', 'result': {'source_ref': native['source_ref'],
        'offset': 0, 'total_bytes': 20450}, 'received_axis_results': {'scientific_results': [native]}}
    before = deepcopy(outcome)
    assert adapter.completed_work_result(selection, outcome, {}) is None
    assert outcome == before


@pytest.mark.parametrize('axis,adapter', [('A107', a107_work_report), ('A110', a110_work_report)])
def test_typed_native_delivery_still_presents_its_original_result(axis, adapter):
    native = native_result(axis)
    outcome = {'status': 'completed', 'admitted_child_return': {'native_components': [native['source_ref']]},
        'received_axis_results': {'scientific_results': [native]}}
    result = adapter.completed_work_result({'kind': 'episode_child', 'role': 'hpc'}, outcome, {})
    assert result['axis'] == axis
    assert result['results']
    assert any(row.get('source_ref') == native['source_ref'] for row in result['results'])


def rebuild_completed_work(trace):
    """Replay the real action/credit projection from its supplied receiver view."""
    with sqlite3.connect(':memory:') as db:
        db.row_factory = sqlite3.Row
        db.executescript('''
            CREATE TABLE runtime_actions(run_id,episode_id,decision_index,action,result);
            CREATE TABLE runtime_observations(run_id,episode_id,unit_index,observation);
            CREATE TABLE runtime_report_attempts(run_id,parent_episode_id,decision_index,form,failure);
        ''')
        db.executemany('INSERT INTO runtime_actions VALUES(?,?,?,?,?)', trace['actions'])
        db.executemany('INSERT INTO runtime_observations VALUES(?,?,?,?)', trace['credit_receipts'])
        db.executemany('INSERT INTO runtime_report_attempts VALUES(?,?,?,?,?)', trace['deliveries'])
        records = trace['meaning_records']

        def get(reference):
            if reference in trace['artifact_metadata_refs']:
                return {'id': reference, 'record_type': 'artifact'}
            return deepcopy(records[reference])

        workflow = SimpleNamespace(run_id=trace['run_id'],
            store=SimpleNamespace(db=db, get=get,
                reference_subset=lambda requested, scope: sorted(requested)),
            binding_context=lambda source: SimpleNamespace(received_record_refs=trace['known_record_refs']))
        source = SimpleNamespace(episode_id=trace['episode_id'], scope=trace['state']['scope'],
            path=tuple(tuple(part) for part in trace['episode_path']))
        return completed_action_reports(workflow, source, trace['state'], before=trace['before'])


def per_decision(reports):
    return {index: {**{key: value for key, value in row.items()
        if key not in {'original_decisions', 'credit_receipts'}},
        'credit_receipts': [receipt for receipt in row['credit_receipts']
            if receipt['original_decision'] == index]}
        for row in reports for index in row['original_decisions']}


def test_actual_failed_context_fits_transport_without_repeating_navigation_results():
    trace = retained_trace()
    state = deepcopy(trace['state'])
    state['completed_action_reports'] = rebuild_completed_work(trace)
    rendered = with_fact_contract_instructions(
        render_scientific_process_prompt(state, trace['instructions']), state)
    # This is the observed transport interface in the retained rejection,
    # not an application setting, truncation rule or research stopping limit.
    assert len(rendered) <= trace['transport_failure']['max_chars']
    assert trace['transport_failure']['actual_chars'] > trace['transport_failure']['max_chars']
    original = per_decision(trace['state']['completed_action_reports'])
    rebuilt = per_decision(state['completed_action_reports'])
    assert original.keys() == rebuilt.keys()
    actions = {row[2]: json.loads(row[3]) for row in trace['actions']}
    for index in original:
        assert rebuilt[index]['credit_receipts'] == original[index]['credit_receipts']
        if actions[index].get('tool') not in {'source.read', 'source.locate'}:
            assert rebuilt[index] == original[index]
    assert state['component_axis_scoring_sheets'] == trace['state']['component_axis_scoring_sheets']
    assert state['received_partner_and_chemical_native_components'] == trace['state']['received_partner_and_chemical_native_components']
    assert state['working_state'] == trace['state']['working_state']
    assert state['last_local_outcome'] == trace['state']['last_local_outcome']
    assert state['controller'] == trace['state']['controller']
    assert 'anchor_transcription_mismatch' in rendered
    assert json.dumps(state['component_axis_scoring_sheets'], ensure_ascii=False,
        separators=(',', ':')) in rendered
