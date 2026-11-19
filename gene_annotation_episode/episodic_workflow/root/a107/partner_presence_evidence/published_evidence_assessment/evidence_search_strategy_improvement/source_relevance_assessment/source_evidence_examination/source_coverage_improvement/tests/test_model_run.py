"""The leaf run with the real model (``-m model_run``): ``link(...).run()`` over the held partner world with the
standard ``ModelProvider``. The model reads the paper, locates the literal witnesses and selects the partner grader;
the run ends through the yield estimator; the credit and the controlled finding are what the parent would receive; a
resumed run replays the recorded answers and asks the model nothing. Needs the owner's Codex sign-in."""
import asyncio
import importlib
import json

import pytest

from episode_runtime import BindingRegistry, resume

from .partner_world import held_world, linked

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(PACKAGE + '.episode').SourceCoverageImprovement
PATH = EPISODE.binding_path
SETTINGS = {'cost': 0.05, 'parameters': {'uncertainty_alpha': 0.05}}
RUN_ID = 'a107_leaf_model_run'
JOURNAL_PATH = ((PATH.replace('/', '__'), RUN_ID),)


@pytest.mark.model_run
def test_the_leaf_grades_with_the_real_model_ends_by_its_estimator_and_resume_replays(tmp_path):
    store, entry, _, _ = held_world(tmp_path)
    run, journal, shared = linked([EPISODE()], PATH, entry, tmp_path, store, RUN_ID, {PATH: SETTINGS})
    first = asyncio.run(run.run())
    result = first['result'].as_record()
    state, closing = journal.run_state(RUN_ID)
    assert state == 'closed' and closing['ended_by'] == 'yield_stop'
    EPISODE.return_form.select(()).admit(result, 'return')
    sheets = result['finding']['partner_sheets']
    assert result['credit'] == float(len(sheets)) and closing['units'] > 0, closing
    units = journal.units(RUN_ID, JOURNAL_PATH)
    calls = journal.model_calls(RUN_ID, JOURNAL_PATH)
    print('A107_LEAF_UNITS', json.dumps([[row[2]['tool'], row[2]['outcome']['status']] for row in units]))
    print('A107_LEAF_RESULT', json.dumps(result, sort_keys=True))
    print('A107_LEAF_MODEL_CALLS', len(calls))
    asked = len(list((tmp_path / 'model_calls').glob('call-*')))
    again = asyncio.run(resume(BindingRegistry([EPISODE()]), run_id=RUN_ID, journal=journal,
                               collaborators=shared).run())
    assert again['result'].as_record() == result
    assert len(list((tmp_path / 'model_calls').glob('call-*'))) == asked
    assert journal.model_calls(RUN_ID, JOURNAL_PATH) == calls
    store.close()
