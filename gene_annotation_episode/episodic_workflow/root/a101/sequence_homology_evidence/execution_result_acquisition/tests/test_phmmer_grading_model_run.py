"""The graded local phmmer return with the real model: ``link(...).run()`` of the result acquisition episode through
the standard ``ModelProvider``. The model is offered the phmmer grader with its instructions and the first line of
each fetched file, and names the files' roles; the run ends through the episode's completion controller; the credit
and the controlled finding are what a parent receives; a resume of the closed run replays the recorded answers
without asking the model again.

Selected only with ``-m model_run``; it needs the owner's Codex sign-in."""
import asyncio

import pytest

from episode_runtime import resume

from ..messages.final_to_parent import RETURN_FORM
from .phmmer_world import PATH, held_world, linked

RUN_ID = 'a101-phmmer-grading-model-run'
JOURNAL_PATH = ((PATH.replace('/', '__'), RUN_ID),)


@pytest.mark.model_run
def test_the_model_grades_the_fetched_phmmer_output_and_resume_replays_it(tmp_path):
    world = held_world(tmp_path)
    registry, journal, run = linked(tmp_path, world, RUN_ID)
    closed = asyncio.run(run.run())
    result = closed['result'].as_record()
    calls = journal.model_calls(RUN_ID, JOURNAL_PATH)
    assert calls, 'the model was asked'
    units = journal.units(RUN_ID, JOURNAL_PATH)
    assert units[-1][2]['tool'] == 'phmmer_grade' and units[-1][2]['outcome']['status'] == 'completed'
    assert journal.run_state(RUN_ID)[1]['ended_by'] == 'yield_stop'
    assert result['credit'] == 1.0
    assert [row['domain_count'] for row in result['finding']['profile_sheets']] == [1, 1]
    selected = RETURN_FORM.select(['execution_phmmer_graded_refs'])
    assert selected.admit(result, 'return') == result
    asked = len(list((tmp_path / 'model_calls').glob('call-*')))

    again = asyncio.run(resume(registry, run_id=RUN_ID, journal=journal,
                               collaborators=world['collaborators']).run())
    assert again['result'].as_record() == result
    assert journal.model_calls(RUN_ID, JOURNAL_PATH) == calls
    assert len(list((tmp_path / 'model_calls').glob('call-*'))) == asked
    world['store'].close()
