"""The source examination run with the real model (``-m model_run``): ``link(...).run()`` of this episode over the held
partner world of its ordered-reading child, with its three children registered and the standard ``ModelProvider``.
The model examines the paper, grades the partner experiment itself or commissions a child that does; the run ends
through the yield estimator; the credit and the controlled finding are what the parent receives; a resumed run
replays the recorded answers and asks the model nothing. Needs the owner's Codex sign-in."""
import asyncio
import importlib
import json

import pytest

from episode_runtime import BindingRegistry, resume

from ..source_coverage_improvement.tests.partner_world import held_world, linked

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(PACKAGE + '.episode').SourceEvidenceExamination
CHILDREN = [importlib.import_module(PACKAGE + '.' + name + '.episode') for name in
            ('table_evidence_extraction', 'source_coverage_improvement', 'passage_evidence_extraction')]
PATH = EPISODE.binding_path
SETTINGS = {'cost': 0.05, 'parameters': {'uncertainty_alpha': 0.05}}
RUN_ID = 'a107_examination_model_run'
JOURNAL_PATH = ((PATH.replace('/', '__'), RUN_ID),)


def episodes():
    children = [next(value for value in vars(module).values() if isinstance(value, type)
                     and value.__module__ == module.__name__)() for module in CHILDREN]
    return [EPISODE(), *children]


@pytest.mark.model_run
def test_the_examination_runs_with_the_real_model_and_its_children_and_resume_replays(tmp_path):
    store, leaf_entry, _, _ = held_world(tmp_path)
    leaf = leaf_entry['assignment']
    assignment = {**leaf['page'], 'scope': leaf['scope'], 'finding_unit': 1.0,
                  'received_record_refs': leaf['received_record_refs'],
                  'literature_partner_components': leaf['literature_partner_components']}
    entry = {'assignment': assignment, 'message': {'objective': 'examine the paper for the partner question'},
             'selection': []}
    continuation = {episode.binding_path: SETTINGS for episode in episodes()}
    run, journal, shared = linked(episodes(), PATH, entry, tmp_path, store, RUN_ID, continuation)
    result = asyncio.run(run.run())['result'].as_record()
    state, closing = journal.run_state(RUN_ID)
    assert state == 'closed' and closing['ended_by'] == 'yield_stop'
    EPISODE.return_form.select(()).admit(result, 'return')
    sheets = result['finding']['partner_sheets']
    assert result['credit'] == float(len(sheets))
    units = journal.units(RUN_ID, JOURNAL_PATH)
    assert units
    print('A107_PARENT_UNITS', json.dumps([[row[2]['kind'], row[2].get('tool', row[2].get('slot')),
                                             row[2]['outcome']['status'] if row[2]['kind'] == 'tool'
                                             else row[2]['result']['credit']] for row in units]))
    print('A107_PARENT_RESULT', json.dumps(result, sort_keys=True))
    for row in units:
        if row[2]['kind'] == 'child':
            assert set(row[2]['report']) == {'slot', 'credit', 'partner_sheets', 'matched_sheet_count',
                                             'matched_loss_sheet_count', 'distinct_experiment_count'}
    asked = len(list((tmp_path / 'model_calls').glob('call-*')))
    again = asyncio.run(resume(BindingRegistry(episodes()), run_id=RUN_ID, journal=journal,
                               collaborators=shared).run())
    assert again['result'].as_record() == result
    assert len(list((tmp_path / 'model_calls').glob('call-*'))) == asked
    store.close()
