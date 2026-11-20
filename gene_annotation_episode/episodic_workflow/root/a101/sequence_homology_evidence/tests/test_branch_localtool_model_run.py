"""Branch runs of the A101 head on a LOCAL tool (no network, no job) with the real model.

World (``a101_world``): a held target protein and a held reference protein differing at one residue, both created as
the run's caller. Branch 1: the head's tool set is ``sequence.align`` alone and the instruction is to measure the
similarity: the obvious step is that tool. Branch 2: the same world with ``sequence.align`` and ``sequence.inspect``
(composition of one sequence), the model must pick. Public API only: ``link(...).run()`` with the real
``ModelProvider``, a real Store and journal, then ``resume`` with a second provider (no new model call). The
invalid-call test (no model) runs a unit with an unheld operand through ``EpisodeRun.run_unit`` and reads it back from
the journal. Real-model tests are selected only with ``-m model_run``."""
import asyncio

import pytest

from episode_runtime import BindingRegistry, ChildCall, RunJournal, ToolCall, resume

from ..messages.final_to_parent import RETURN_FORM
from .a101_world import PATH, collaborators, linked, report_children, subtree, world

ALIGN = 'sequence.align'
INSPECT = 'sequence.inspect'


def units(journal, run_id):
    return [row[2] for row in journal.units(run_id, ((PATH, run_id),))]


def report(journal, run_id, result):
    rows = units(journal, run_id)
    calls = journal.model_calls(run_id, ((PATH, run_id),))
    print('RESULT', result)
    print('ENDED', journal.run_state(run_id)[1])
    for index, unit in enumerate(rows):
        outcome = unit.get('outcome') or {}
        print('UNIT', index, unit['kind'], unit.get('tool'), unit.get('arguments'), '->', outcome.get('status'),
              'credit', unit.get('credit'), 'feedback', outcome.get('feedback'))
    print('DECISIONS', [call['response'] for call in calls])
    return rows, calls


async def resumed(held, journal, run_id):
    bindings = subtree()
    closed = await resume(BindingRegistry(bindings), run_id=run_id, journal=journal,
                          collaborators=collaborators(held, bindings, 'model_calls_resumed')).run()
    return closed['result']


def run_branch(tmp_path, tools, run_id):
    held = world(tmp_path, tools)
    journal = RunJournal(tmp_path / 'journal.sqlite3')
    run = linked(held, run_id, journal=journal)
    closed = asyncio.run(run.run())
    result = closed['result'].as_record()
    rows, calls = report(journal, run_id, result)
    assert journal.run_state(run_id)[1]['ended_by'] == 'yield_stop'
    assert RETURN_FORM.select(('committed_record_refs',)).admit(result, 'return') == result
    asked = len(list((tmp_path / 'model_calls').glob('call-*')))
    again = asyncio.run(resumed(held, journal, run_id)).as_record()
    assert again == result
    assert len(list((tmp_path / 'model_calls').glob('call-*'))) == asked
    assert not list((tmp_path / 'model_calls_resumed').glob('call-*'))
    return held, rows, result


def tool_units(rows):
    return [row for row in rows if row['kind'] == 'tool' and row['tool'] == 'execute_selected_tool']


@pytest.mark.model_run
def test_branch1_the_model_aligns_the_target_with_the_held_reference(tmp_path):
    held, rows, result = run_branch(tmp_path, [ALIGN], 'a101-localtool-1')
    aligned = [row for row in tool_units(rows) if row['arguments']['tool'] == ALIGN]
    assert aligned, 'the model never called sequence.align'
    completed = [row for row in aligned if row['outcome']['status'] == 'completed']
    assert completed, 'no sequence.align completed'
    assert completed[0]['outcome']['record_refs']
    held['store'].close()


@pytest.mark.model_run
def test_branch2_the_model_picks_between_align_and_inspect(tmp_path):
    held, rows, result = run_branch(tmp_path, [ALIGN, INSPECT], 'a101-localtool-2')
    names = [row['arguments']['tool'] for row in tool_units(rows)]
    print('TOOLS', names)
    assert ALIGN in names
    held['store'].close()


def test_an_invalid_local_call_is_a_returned_outcome_that_enters_the_iterator(tmp_path):
    held = world(tmp_path, [ALIGN])
    run = linked(held, 'a101-localtool-invalid')
    scope = held['assignment']['scope']

    def call(query, reference):
        return asyncio.run(run.run_unit(ToolCall('execute_selected_tool', {
            'tool': ALIGN, 'arguments': {'query_ref': query, 'reference_ref': reference, 'molecule': 'protein',
                                         'mode': 'local'}, 'scope': scope, 'permitted_record_refs': None})))
    # a held record that is not a sequence: a contract error of the tool
    wrong = call(held['hypothesis'], held['reference'])
    print('WRONG_TYPE', wrong['outcome'])
    assert wrong['outcome']['status'] == 'invalid'
    # a record the episode does not hold: custody
    unheld = call(held['target'], 'input_' + 'a' * 24)
    print('UNHELD', unheld['outcome'])
    assert unheld['outcome']['status'] in ('invalid', 'failed')
    assert [row['outcome']['status'] for row in units(run.journal, 'a101-localtool-invalid')] == \
        [wrong['outcome']['status'], unheld['outcome']['status']] if hasattr(run, 'journal') else True
    held['store'].close()


@pytest.mark.model_run
def test_branch3_a_commissioned_run_runs_and_reports(tmp_path):
    """The commission the head's model chose in the earlier runs, made here as a stepped unit so that it is always
    exercised: after a real alignment the head commissions the published evidence assessment with controlled
    fields (the hypothesis and the target as the question's context, the alignment's source); ``msg_to_child``
    builds the child's assignment, the child runs by its own real-model decisions to its controller's stop, its
    return is admitted and reported, and the head runs on by its own decisions to its own stop."""
    held = world(tmp_path, [ALIGN])
    journal = RunJournal(tmp_path / 'journal.sqlite3')
    run = linked(held, 'a101-localtool-3', journal=journal)
    aligned = asyncio.run(run.run_unit(ToolCall('execute_selected_tool', {
        'tool': ALIGN, 'arguments': {'query_ref': held['target'], 'reference_ref': held['reference'],
                                     'molecule': 'protein', 'mode': 'global'},
        'scope': held['assignment']['scope'], 'permitted_record_refs': None})))
    source, = (ref for ref in aligned['outcome']['record_refs'] if ref.startswith('source_'))
    child = asyncio.run(run.run_unit(ChildCall('literature', {
        'objective': 'evidence_in_supplied_sources',
        'question_context_refs': [held['hypothesis'], held['target']], 'source_refs': [source]})))
    print('CHILD', child['completion'], child['report'])
    report_children(journal, 'a101-localtool-3')
    assert child['message']['message'] == {'objective': 'evidence_in_supplied_sources'}
    assert child['completion']['ended_by'] == 'yield_stop'
    assert set(child['report']) == {'credit', 'finding', 'record_refs', 'handoff_refs'}
    closed = asyncio.run(run.run())
    result = closed['result'].as_record()
    rows, calls = report(journal, 'a101-localtool-3', result)
    assert journal.run_state('a101-localtool-3')[1]['ended_by'] == 'yield_stop'
    assert RETURN_FORM.select(('committed_record_refs',)).admit(result, 'return') == result
    asked = len(list((tmp_path / 'model_calls').glob('call-*')))
    again = asyncio.run(resumed(held, journal, 'a101-localtool-3')).as_record()
    assert again == result
    assert len(list((tmp_path / 'model_calls').glob('call-*'))) == asked
    assert not list((tmp_path / 'model_calls_resumed').glob('call-*'))
    held['store'].close()
