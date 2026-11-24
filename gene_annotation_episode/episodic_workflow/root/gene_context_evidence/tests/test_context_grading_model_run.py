"""The A103 head with the real model (``-m model_run``; it needs the owner's Codex sign-in).

Leaf: the head is linked with the public API on the real world (``a103_world``); its first units are the two lookups
and the native context measurements of the engineered panel (named by the test, run as real tool units), then
``run()`` goes on with the real ``ModelProvider``: the held measurements are graded and the model decides every
further unit until the head's yield controller stops it. The result is the credit and the controlled finding read
from the sheets; ``resume`` replays the closed run from the journal without asking the model again.

Parent: a head is linked on the same kind of world and the real model decides from its first model decision on; it
is asked (in its commission's message) to commission a narrower A103 head for the measurement and grading. What the
parent receives from that child is its credit and its controlled finding; the run ends through the parent's yield
controller, and resume replays it."""
import asyncio

import pytest

from episode_runtime import RunJournal, resume

from ..messages import final_to_parent
from .a103_world import PATH, linked, services, subtree, world  # noqa: F401
from .test_context_grading import measured_world, through_the_lookups

COST = 0.001


def priced(held):
    """The head's settings with a continuation cost: a unit that earns nothing brings the controller to stop."""
    settings = dict(held['settings'])
    bindings = {task: {**binding, 'cutoff': COST} for task, binding in settings['yield_bindings'].items()}
    return {**settings, 'yield_bindings': bindings}


def check_result(result, journal, run_id):
    assert journal.run_state(run_id)[1]['ended_by'] == 'yield_stop'
    form = final_to_parent.RETURN_FORM.select(('committed_record_refs',))
    assert form.admit(result, 'return') == result
    finding = result['finding']
    assert set(finding) == set(final_to_parent.RETURN_FORM.fields['finding'].form.fields)
    return finding


@pytest.mark.model_run
def test_the_model_grades_and_reasons_over_the_measured_panel_and_resume_replays_it(tmp_path):
    held = world(tmp_path)
    settings = priced(held)
    journal = RunJournal(tmp_path / 'journal.sqlite3')
    run = linked(held, 'a103-leaf-model', settings=settings, journal=journal)
    through_the_lookups(run)
    measured_world(held, run)
    closed = asyncio.run(run.run())
    result = closed['result'].as_record()
    finding = check_result(result, journal, 'a103-leaf-model')
    units = [row[2] for row in journal.units('a103-leaf-model', ((PATH, 'a103-leaf-model'),))]
    assert any(unit['kind'] == 'tool' and unit['tool'] == 'context_grade' for unit in units)
    assert finding['conserved_neighborhood_count'] == 1
    calls = journal.model_calls('a103-leaf-model', ((PATH, 'a103-leaf-model'),))
    assert calls
    print('LEAF credit', result['credit'], 'units', len(units), 'model calls', len(calls))
    print('LEAF decisions', [call['response'].get('operation') for call in calls])
    print('LEAF finding', {key: value for key, value in finding.items() if key not in ('attachments', 'sheet_refs')})
    asked = len(list((tmp_path / 'model_calls').glob('call-*')))
    resumed = asyncio.run(resume_run(held, journal, 'a103-leaf-model', settings)).as_record()
    assert resumed == result
    assert len(list((tmp_path / 'model_calls').glob('call-*'))) == asked
    assert not list((tmp_path / 'model_calls_resumed').glob('call-*'))
    held['store'].close()


async def resume_run(held, journal, run_id, settings):
    from episode_runtime import BindingRegistry
    from gene_annotation_episode.model_provider import ModelProvider, load_config
    bindings = subtree()
    continuation = {binding.binding_path: {} for binding in bindings}
    continuation[PATH] = settings
    collaborators = {'store': held['store'],
                     'model_provider': ModelProvider(load_config(), held['directory'] / 'model_calls_resumed',
                                                     held['directory']),
                     'continuation': continuation, 'services': services(held['directory'])}
    closed = await resume(BindingRegistry(bindings), run_id=run_id, journal=journal,
                          collaborators=collaborators).run()
    return closed['result']


PARENT_MESSAGE = (
    'Commission exactly one narrower gene_context_evidence child for your whole scope and hand it what it needs: '
    'selection "own" (your own selection), evidence_refs naming '
    'every record of your Parent-selected evidence operands, constraints {}, context {"a103_task": {"name": '
    '"gene_context"}}, your scope and scope_refs naming your scope_refs. The child binds the two genomes '
    '(context.bind_locus, selector locus_tag "anchor"), measures both neighborhoods, compares them, grades them and '
    'links the graded context observation to the proposed annotation; use what it returns.')


@pytest.mark.model_run
def test_a_parent_head_commissions_a_child_head_and_receives_its_credit_and_controlled_finding(tmp_path):
    held = world(tmp_path)
    settings = priced(held)
    held['assignment'] = {**held['assignment'], 'constraints': {'instruction': PARENT_MESSAGE}}
    journal = RunJournal(tmp_path / 'journal.sqlite3')
    run = linked(held, 'a103-parent-model', settings=settings, journal=journal)
    closed = asyncio.run(run.run())
    result = closed['result'].as_record()
    finding = check_result(result, journal, 'a103-parent-model')
    units = [row[2] for row in journal.units('a103-parent-model', ((PATH, 'a103-parent-model'),))]
    children = [unit for unit in units if unit['kind'] == 'child']
    print('PARENT credit', result['credit'], 'units', len(units), 'children', [unit['slot'] for unit in children])
    print('PARENT decisions', [call['response'].get('operation') for call in
                               journal.model_calls('a103-parent-model', ((PATH, 'a103-parent-model'),))])
    assert any(unit['slot'] == 'gene_context_evidence' for unit in children)
    for unit in children:
        if unit['slot'] == 'gene_context_evidence':
            report = unit['report']
            print('PARENT received', report['credit'], {key: value for key, value in report['finding'].items()
                                                         if key != 'attachments'})
            assert set(report) <= {'slot', 'credit', 'finding', 'selected_record_counts'}
            assert 'sheet_refs' not in report['finding']
    print('PARENT finding', {key: value for key, value in finding.items() if key not in ('attachments', 'sheet_refs')})
    asked = len(list((tmp_path / 'model_calls').glob('call-*')))
    resumed = asyncio.run(resume_run(held, journal, 'a103-parent-model', settings)).as_record()
    assert resumed == result
    assert len(list((tmp_path / 'model_calls').glob('call-*'))) == asked
    assert not list((tmp_path / 'model_calls_resumed').glob('call-*'))
    held['store'].close()
