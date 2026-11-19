"""The runner records, by itself, everything two real episodes do, and resumes from it.

The episodes are the test-only packages ``fact_collection`` (parent) and ``fact_collection/fact_extraction``
(child), laid out in the episode file structure. Neither contains any recording, replay or custody code: they
name the records they pass and read records through the readers and the tool context they are given.
Everything here is real: the ``RunJournal``, the run's ``Store``, the ``method_loop`` Episode loop,
``yield_control`` controllers and a ``ModelProvider`` (these episodes are commissioned with their field chosen, so
no model call is made here; ``test_model_run.py`` makes one).
"""
import ast
import asyncio
import importlib
import json
import os
from pathlib import Path
import stat

import pytest

import episode_runtime
from episode_runtime import EPISODE_API, BindingRegistry, CustodyError, RecordReader, RunJournal, link, resume
from episode_runtime.recording import Custody, UnitPosition
from episode_runtime.store_ledger import StoreLedger
from episode_runtime.work_tables import WorkRows
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store
from method_loop import EpisodeBindingDeclaration, EpisodeRef, RecordForm

from .fact_collection.episode import FactCollection
from .fact_collection.fact_extraction.episode import FactExtraction

PARENT, CHILD = 'fact_collection', 'fact_collection/fact_extraction'
SETTINGS = {'cost': 0.0, 'parameters': {'uncertainty_alpha': 0.05}}
CONTINUATION = {PARENT: SETTINGS, CHILD: SETTINGS}
EPISODES = (Path(__file__).parent / 'fact_collection', Path(__file__).parent / 'probe')


def parent_path(run_id):
    return (('fact_collection', run_id),)


def child_path(run_id):
    return (*parent_path(run_id), ('fact_collection__fact_extraction', 'extraction_0'))


def plain(path):
    return [list(part) for part in path]


@pytest.fixture
def world(tmp_path):
    store = Store(tmp_path / 'store')
    subject = store.artifact(json.dumps({'name': 'GeneX', 'function': 'kinase'}), 'application/json')
    unrelated = store.artifact(json.dumps({'name': 'GeneY', 'function': 'unknown'}), 'application/json')
    provider = ModelProvider(load_config(), tmp_path / 'model_calls', tmp_path)
    yield {'store': store, 'subject': subject, 'unrelated': unrelated, 'provider': provider,
           'journal': RunJournal(tmp_path / 'journal.sqlite3'), 'calls': tmp_path / 'model_calls'}
    store.close()


def collaborators(world, continuation=CONTINUATION):
    return {'store': world['store'], 'model_provider': world['provider'], 'continuation': continuation,
            'services': {}}


def entry(world, **assignment):
    return {'assignment': {'subject_refs': [world['subject']], **assignment}, 'selection': [],
            'message': {'fields': ['name', 'function']}}


def registry():
    return BindingRegistry([FactCollection(), FactExtraction()])


def tables(journal):
    return {name: journal.db.execute('SELECT * FROM ' + name + ' ORDER BY rowid').fetchall()
            for name in ('runs', 'episodes', 'units', 'attempts', 'settings', 'services', 'service_builds',
                         'parent_inputs', 'model_calls', 'receipts', 'abandoned_receipts', 'progress_points')}


def run(world, run_id, **assignment):
    linked = link(registry(), PARENT, entry(world, **assignment), run_id=run_id, journal=world['journal'],
                  collaborators=collaborators(world))
    return asyncio.run(linked.run())['result'].as_record()


def test_parent_passes_records_child_returns_them_and_the_runner_records_everything(world):
    journal, subject = world['journal'], world['subject']
    result = run(world, 'pass', field='function')
    child_receipts = journal.receipts('pass', child_path('pass'))
    fact_ref = child_receipts[1]['ref']
    assert result == {'credit': 2.0, 'finding': {'facts': ['kinase'], 'confirmed': 1}, 'fact_refs': [fact_ref]}
    assert json.loads(world['store'].get_artifact(fact_ref)) == {'field': 'function', 'value': 'kinase',
                                                                 'source_ref': subject}
    assert journal.receipts('pass', parent_path('pass'))[0] == {
        'ref': subject, 'how': 'entry', 'from': None, 'to': parent_path('pass'), 'unit': None, 'producer': None,
        'producer_unit': None}
    assert child_receipts == [
        {'ref': subject, 'how': 'commissioned', 'from': parent_path('pass'), 'to': child_path('pass'), 'unit': 0,
         'producer': None, 'producer_unit': None},
        {'ref': fact_ref, 'how': 'produced', 'from': child_path('pass'), 'to': child_path('pass'), 'unit': 0,
         'producer': child_path('pass'), 'producer_unit': 0}]
    assert journal.receipts('pass', parent_path('pass'))[1] == {
        'ref': fact_ref, 'how': 'returned', 'from': child_path('pass'), 'to': parent_path('pass'), 'unit': 0,
        'producer': child_path('pass'), 'producer_unit': 0}
    child_units = journal.units('pass', child_path('pass'))
    assert [label for label, *_ in child_units] == ['tool:extract_field:0']
    assert child_units[0][2]['produced'] == [fact_ref]
    units = journal.units('pass', parent_path('pass'))
    assert [label for label, *_ in units] == ['extraction_0', 'tool:confirm_fact:1']
    child_outcome = units[0][2]
    assert child_outcome['kind'] == 'child' and child_outcome['result']['fact_refs'] == [fact_ref]
    assert child_outcome['result']['field'] == 'function' and 'records_read' not in child_outcome['result']
    # Credit and finding are in every return; the credit is the one the child's controller stopped on.
    assert child_outcome['result']['credit'] == 1.0
    assert journal.controller_steps('pass', child_path('pass'))[-1]['credit'] == 1.0
    assert child_outcome['result']['finding'] == {'field': 'function', 'found': True, 'value': 'kinase',
                                                  'source_ref': subject}
    assert child_outcome['completion'] == {'ended_by': 'yield_stop', 'units_consumed': 1}
    assert child_outcome['slot'] == 'extraction' and child_outcome['arguments'] == {'field': 'function'}
    assert child_outcome['message']['assignment'] == {'source_refs': [subject], 'field': 'function'}
    assert child_outcome['report'] == {'fact': 'kinase'}
    assert units[0][3]['report'] == {'report': {'fact': 'kinase'}}
    assert units[1][3] is None
    assert units[1][2]['outcome']['produced_by'] == plain(child_path('pass'))
    assert [value['credit'] for _, value, _, _ in units] == [1.0, 2.0]
    for _, value, _, _ in units + child_units:
        assert value['estimation_context']['progress_time']['point_kind'] == 'progress_receipt'
    assert [row['state'] for row in journal.episodes('pass')] == ['closed', 'closed']
    # Each Episode ended because its yield controller stopped it; the closure records the credit it stopped on.
    assert [row['completion'] for row in journal.episodes('pass')] == [
        {'ended_by': 'yield_stop', 'units': 2, 'credit': 2.0},
        {'ended_by': 'yield_stop', 'units': 1, 'credit': 1.0}]
    steps = journal.controller_steps('pass', parent_path('pass'))
    assert [(step['unit_label'], step['credit'], step['marginal_credit'], step['stop']) for step in steps] == [
        ('extraction_0', 1.0, 1.0, False), ('tool:confirm_fact:1', 2.0, 1.0, True)]
    assert all('expected_next_gain' in step['estimate'] and 'continuation_cost' in step['decision'] for step in steps)
    assert journal.services('pass') == {PARENT: [], CHILD: []} and journal.service_builds('pass') == []
    assert journal.run_state('pass')[1]['ended_by'] == 'yield_stop'
    assert journal.run_state('pass')[0] == 'closed'
    assert [state for *_, state in journal.attempts('pass', parent_path('pass'))] == ['finished', 'finished']
    assert journal.settings('pass') == CONTINUATION
    assert journal.model_calls('pass', parent_path('pass')) == []
    assert not list(world['calls'].glob('call-*'))


def test_a_child_reads_only_the_records_it_holds(world):
    run(world, 'reads', field='name')
    path = child_path('reads')
    rows = WorkRows(world['store'])
    custody = Custody(world['journal'], StoreLedger(world['store'], rows), 'reads', path,
                      EpisodeRef('reads', path).episode_id, UnitPosition(world['journal'], 'reads', path))
    records = RecordReader(world['store'], custody, rows)
    assert json.loads(records.get_artifact(world['subject']))['name'] == 'GeneX'
    assert records.receipt(world['subject'])['from'] == parent_path('reads')
    with pytest.raises(CustodyError, match='record_not_held'):
        records.get_artifact(world['unrelated'])
    with pytest.raises(CustodyError, match='record_not_held'):
        records.receipt(world['unrelated'])


def test_a_parent_cannot_pass_a_record_it_does_not_hold(world):
    with pytest.raises(CustodyError, match='record_not_held_by_commissioner'):
        run(world, 'refused', field='name', context_refs=[world['unrelated']])
    assert world['journal'].receipts('refused', child_path('refused')) == []
    assert world['journal'].units('refused', child_path('refused')) == []
    # The wrong commission fails: the error ends the run and is recorded as its failure. No child Episode exists;
    # the unit that began stays begun, and a resume fails the same way.
    journal = world['journal']
    assert [row['binding_path'] for row in journal.episodes('refused')] == [PARENT]
    assert 'CustodyError: record_not_held_by_commissioner' in journal.run_failure('refused')
    assert [(index, label, state) for index, label, _, state in journal.attempts('refused', parent_path('refused'))] \
        == [(0, 'extraction_0', 'began')]
    assert journal.run_state('refused')[0] == 'active' and journal.model_calls('refused', parent_path('refused')) == []
    with pytest.raises(CustodyError, match='record_not_held_by_commissioner'):
        asyncio.run(resume(registry(), run_id='refused', journal=journal, collaborators=collaborators(world)).run())


def _artifact_directories(store):
    root = Path(store.path) / 'artifacts'
    return [root, *(path for path in root.iterdir() if path.is_dir())]


def test_an_interrupted_run_resumes_from_its_receipts_and_outcomes(world):
    journal, store = world['journal'], world['store']
    directories = _artifact_directories(store)
    for directory in directories:
        os.chmod(directory, stat.S_IRUSR | stat.S_IXUSR)
    try:
        if os.access(directories[0], os.W_OK):
            pytest.fail('the store artifact directory stayed writable; this process cannot be interrupted this way')
        with pytest.raises(PermissionError):
            run(world, 'interrupted', field='function')
    finally:
        for directory in directories:
            os.chmod(directory, stat.S_IRWXU)
    assert journal.receipts('interrupted', child_path('interrupted'))[0]['how'] == 'commissioned'
    assert journal.units('interrupted', child_path('interrupted')) == []
    assert journal.attempts('interrupted', child_path('interrupted')) == [(0, 'tool:extract_field:0', journal.attempts(
        'interrupted', child_path('interrupted'))[0][2], 'began')]
    assert journal.units('interrupted', parent_path('interrupted')) == []
    assert 'PermissionError' in journal.run_failure('interrupted')
    resumed = resume(registry(), run_id='interrupted', journal=journal, collaborators=collaborators(world))
    result = asyncio.run(resumed.run())['result'].as_record()
    assert result['finding']['facts'] == ['kinase'] and result['credit'] == 2.0
    receipts = journal.receipts('interrupted', child_path('interrupted'))
    assert [(row['how'], row['unit']) for row in receipts] == [('commissioned', 0), ('produced', 0)]
    assert [row['how'] for row in journal.receipts('interrupted', parent_path('interrupted'))] == ['entry',
                                                                                                    'returned']
    assert len(journal.units('interrupted', parent_path('interrupted'))) == 2
    assert {state for *_, state in journal.attempts('interrupted', child_path('interrupted'))} == {'finished'}


def test_resuming_a_closed_run_replays_it_without_recording_anything_new(world):
    journal = world['journal']
    first = run(world, 'closed', field='function')
    before = tables(journal)
    resumed = resume(registry(), run_id='closed', journal=journal, collaborators=collaborators(world))
    assert asyncio.run(resumed.run())['result'].as_record() == first
    assert tables(journal) == before


def test_the_episode_type_is_a_method_loop_declaration():
    from yield_control import AccumulationYieldController
    controller = AccumulationYieldController('fact_collection', 0.0, 0.0, SETTINGS['parameters'])
    declaration = FactCollection().declaration(controller)
    assert isinstance(declaration, EpisodeBindingDeclaration)
    assert declaration.interface == PARENT and declaration.goal == FactCollection.goal
    assert declaration.internal_summary.function_id == 'internal_summary'
    assert declaration.controller.credit.library.endswith('fact_collection.credit')
    assert 'without a declared limit' in declaration.progress
    slot = declaration.child_slot('extraction')
    assert slot.accepted_interfaces == (CHILD,)
    assert slot.prepare_request.function_id == 'msg_to_child'
    assert slot.receive_result.function_id == 'read_from_child'
    assert [component.name for component in declaration.components] == ['action', 'tool.confirm_fact']
    assert isinstance(FactExtraction.return_form, RecordForm)


def test_the_stopping_text_follows_the_controller_kind():
    from yield_control import BoundedQualityYieldController, CompletionYieldController
    bounded = BoundedQualityYieldController('e', 0.0, 0.5, 4.0, SETTINGS['parameters'])
    completion = CompletionYieldController('e', 0.0, 0.5, 3.0, SETTINGS['parameters'])
    assert 'maximum 4.0' in FactExtraction().declaration(bounded).progress
    assert 'target 3.0' in FactExtraction().declaration(completion).progress
    assert 'before the target' in FactExtraction().declaration(completion).stopping
    assert 'below that maximum' in FactExtraction().declaration(bounded).stopping


def test_the_test_episodes_import_only_the_episode_api_of_the_system():
    """Recording, replay and custody are system-only: an episode file imports from ``episode_runtime`` only the
    names of ``EPISODE_API`` and never one of its modules."""
    seen = set()
    for folder in EPISODES:
        for path in folder.rglob('*.py'):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.Import):
                    assert not [name.name for name in node.names if name.name.startswith('episode_runtime')], path
                if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith('episode_runtime'):
                    assert node.module == 'episode_runtime', (path, node.module)
                    names = {name.name for name in node.names}
                    assert names <= set(EPISODE_API), (path, names - set(EPISODE_API))
                    seen |= names
    assert {'EpisodeBinding', 'ToolCall', 'ChildCall', 'ModelRequest', 'Rejected', 'ChildMessage'} <= seen


def test_nothing_but_the_yield_controller_ends_an_episode(world, episode_variant):
    """The system has no action that ends an Episode. A task that offers no unit (here ``decide`` returns ``None``
    once the fact is found, as an episode that wanted to end itself would) is an error: the run fails with it."""
    assert not hasattr(episode_runtime, 'Done') and 'Done' not in EPISODE_API
    assert not hasattr(importlib.import_module('method_loop'), 'END_EXHAUSTED')
    from method_loop.episode import EPISODE_END_KINDS
    assert EPISODE_END_KINDS == ('yield_stop',)
    # The kept episode at a cost its controller never meets before the target: it ends at the target, by the
    # controller's stop, and at no other point.
    assert [step['stop'] for step in _steps(world, 'kept')] == [True]
    ending = episode_variant(CHILD, {
        'task.py': [("    unread = [ref for ref in summary['source_refs'] if ref not in summary['read']]\n",
                     "    unread = [ref for ref in summary['source_refs'] if ref not in summary['read']]\n"
                     "    if summary['read']:\n        return None\n")],
        'yield_estimator.py': [('TARGET = 1.0', 'TARGET = 5.0')]}).FactExtraction
    linked = link(BindingRegistry([FactCollection(), ending()]), PARENT, entry(world, field='function'),
                  run_id='ends_itself', journal=world['journal'], collaborators=collaborators(world))
    with pytest.raises(TypeError, match='task_action_must_be_a_ToolCall_or_a_ChildCall:' + CHILD):
        asyncio.run(linked.run())
    journal = world['journal']
    assert 'task_action_must_be_a_ToolCall_or_a_ChildCall' in journal.run_failure('ends_itself')
    assert [row['state'] for row in journal.episodes('ends_itself')] == ['active', 'active']
    assert [step['stop'] for step in journal.controller_steps('ends_itself', child_path('ends_itself'))] == [False]


def _steps(world, run_id):
    run(world, run_id, field='function')
    return world['journal'].controller_steps(run_id, child_path(run_id))
