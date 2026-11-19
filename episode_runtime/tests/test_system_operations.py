"""The system operations of the scoped store that replace what the library did on the raw Store: a scratch
directory and a worker thread on its files, an artifact from a file or a stream, a caller value as a source,
declared tables in place of statements and commits, a row withdrawn in place of a delete, the section of a call,
what a write created, the work cache, the Store's ownership rules over held records, the measures of a scope
and of a context mask, the reads of a read library (a page, a frozen selection, its reads) and the diagnostics
of tool outcomes. Real Store, journal, runner and probe episode; ``operations_library.py`` holds the
library functions the probe's tools call."""
import asyncio
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

import episode_runtime
from episode_runtime import CustodyError, ScopedStore, WorkCache, link
from episode_runtime.recording import Custody, UnitPosition
from episode_runtime.store_ledger import StoreLedger
from episode_runtime.store_scope import HeldStore
from episode_runtime.work_tables import WorkRows
from gene_annotation_episode import library_targets
from method_loop import EpisodeRef

from .probe.task import LEDGER
from .probe_world import (again, collaborators, entry, outcomes, probe_path, registry, run, tool,  # noqa: F401
                          world)
from .test_scoped_store import problem  # noqa: F401 - a fixture

REPOSITORY = Path(episode_runtime.__file__).parents[1]
REFUSED = 'CustodyError: record_not_held'
FASTQ = '@r1\nACGTACGTAC\n+\nIIIIIIIIII\n@r2\nGGGTTTAAACCC\n+\nIIIIIIIIIIII\n@r3\nACGT\n+\nIIII\n'


def produced_receipts(world, run_id):
    return [row['ref'] for row in world['journal'].receipts(run_id, probe_path(run_id)) if row['how'] == 'produced']


def scratch_left(world):
    """Every file or directory left below the scratch directories of the Store's Episodes."""
    root = world['tmp'] / 'store' / 'scratch'
    return sorted(str(path.relative_to(root)) for episode in root.iterdir() for path in episode.iterdir())


# -- the scratch directory and the worker thread ---------------------------------------------------------------
def test_a_worker_thread_computes_on_scratch_files_and_the_unit_writes_the_result(world):
    store = world['store']
    damaged = store.artifact('bytes as they were written', 'text/plain')
    stored = world['tmp'] / 'store' / 'artifacts' / damaged[9:11] / damaged[9:]
    stored.write_text('bytes as they are now')                 # the file no longer has the artifact's digest
    run(world, 'scratch', [tool('scratch_work', ref=world['subject'], unheld=world['unrelated'], damaged=damaged)],
        assignment={'held_refs': [damaged]})
    outcome = outcomes(world, 'scratch')[0]
    done, text = outcome['outcome'], store.get_artifact(world['subject']).decode()
    assert done['residues'] == len(text) and done['cancelled'] is False
    assert done['counts'] == {residue: text.count(residue) for residue in sorted(set(text))}
    assert json.loads(store.get_artifact(done['counts_ref'])) == done['counts']
    assert store.get(done['counts_ref'])['media_type'] == 'application/json'
    # The result is the unit's product, receipted; nothing of the scratch directory is left or held.
    assert outcome['produced'] == [done['counts_ref']] == produced_receipts(world, 'scratch')
    assert done['scratch_removed'] is True and done['empty_at_first'] is True and scratch_left(world) == []
    assert done['not_offered'] == []
    assert done['unheld']['raised'].startswith(REFUSED)
    assert done['outside']['raised'].startswith('ValueError: scratch_file_name_must_be_a_relative_path')
    # A copy that does not have the artifact's digest is refused and not left (the directory was empty after it).
    assert done['damaged']['raised'] == 'ValueError: artifact_digest_mismatch:' + damaged
    assert done['closed']['raised'].startswith('CustodyError: scratch_directory_is_closed')


def test_the_scoped_store_refuses_a_worker_thread(world):
    run(world, 'thread', [tool('thread_refused', ref=world['subject'])])
    outcome = outcomes(world, 'thread')[0]
    assert outcome['outcome'] == {'read': 'CustodyError: scoped_store_used_outside_the_thread_of_its_unit',
                                  'write': 'CustodyError: scoped_store_used_outside_the_thread_of_its_unit',
                                  'read_in_the_unit': 'GeneX'}
    assert outcome['produced'] == [] and scratch_left(world) == []


def test_a_cancelled_unit_waits_for_its_worker_thread_before_its_scratch_directory_is_removed(world):
    linked = link(registry(), 'probe', entry(world, [tool('scratch_cancel')]), run_id='cancel',
                  journal=world['journal'], collaborators=collaborators(world))
    switch = world['switch']

    async def cancel_when_the_thread_runs():
        task = asyncio.create_task(linked.run())
        await asyncio.to_thread(switch.started.wait)
        assert switch.seen == {}                          # the thread is working; it has not finished
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(cancel_when_the_thread_runs())
    # The thread was told, finished its file in the directory, and only then was the directory removed.
    assert switch.seen['directory_existed'] is True
    assert switch.seen['finished'] == 'finished after the cancellation'
    assert not Path(switch.seen['path']).exists() and scratch_left(world) == []
    assert world['journal'].run_failure('cancel').startswith('CancelledError')
    assert outcomes(world, 'cancel') == []


def test_a_cut_process_leaves_no_scratch_directory_for_the_rerun(world):
    """The run is started in a process of its own, which ends inside the tool's scratch block (``os._exit``: no
    cleanup runs, as when a process is killed). The directory is left on disk. Resuming the run removes it before
    the unit runs again; the rerun gets a new, empty directory."""
    log = world['tmp'] / 'scratch_path.txt'
    plan = [tool('scratch_cut', log=str(log), exit=7)]
    cut = subprocess.run([sys.executable, '-m', 'episode_runtime.tests.cut_run', str(world['tmp']), 'cut',
                          json.dumps(entry(world, plan))], cwd=REPOSITORY, capture_output=True, text=True)
    assert cut.returncode == 7, cut.stderr
    left = Path(log.read_text())
    assert (left / 'partial.bin').read_bytes() == b'half a download'
    assert [state for _, _, _, state in world['journal'].attempts('cut', probe_path('cut'))] == ['began']
    again(world, 'cut')
    assert outcomes(world, 'cut')[0]['outcome'] == {
        'resumed': True, 'left_exists': False, 'new_directory': True, 'directories_of_the_episode': 1,
        'same_episode_directory': True}
    assert not left.exists() and scratch_left(world) == []


def test_a_unit_that_ends_with_its_scratch_directory_open_fails(world):
    with pytest.raises(CustodyError, match='unit_ended_with_an_open_scratch_directory'):
        run(world, 'open', [tool('scratch_left_open')])
    assert outcomes(world, 'open') == []
    assert world['journal'].run_failure('open').startswith('CustodyError: unit_ended_with_an_open_scratch_directory')
    assert Path(world['switch'].seen['path']).is_dir()
    world['switch'].seen.pop('manager').__exit__(None, None, None)     # the test closes what the tool left open
    assert not Path(world['switch'].seen['path']).exists()


# -- an artifact from a file or a stream; a caller value --------------------------------------------------------
def test_an_artifact_is_written_from_a_file_and_from_a_stream_without_loading_it(world):
    run(world, 'capture', [tool('capture', text='0123456789abcdef', times=200000)])       # 3.2 MB: several chunks
    outcome, store = outcomes(world, 'capture')[0], world['store']
    done, data = outcome['outcome'], b'0123456789abcdef' * 200000
    ref = 'artifact_' + hashlib.sha256(data).hexdigest()
    assert done['from_file'] == done['from_handle'] == done['from_chunks'] == ref
    assert (done['size'], done['media_type'], done['head']) == (len(data), 'application/x-probe', '0123456789abcdef')
    assert store.get_artifact(ref) == data and done['other_bytes'] == 'other bytes'
    # Receipted as produced by the unit; what a rolled-back transaction captured is neither held nor in the Store.
    assert outcome['produced'] == [ref, done['other']] == produced_receipts(world, 'capture')
    assert done['lost_held'] == [True, False]
    with pytest.raises(Exception, match='unknown'):
        store.get(done['lost'])
    assert done['text_chunks']['raised'] == 'TypeError: artifact_stream_requires_bytes'
    assert scratch_left(world) == []
    # Another Episode does not hold the artifact.
    run(world, 'other', [tool('follow', calls={'read': ['get', ref]})])
    assert outcomes(world, 'other')[0]['outcome']['read']['raised'].startswith(REFUSED)


def test_a_caller_value_becomes_a_source_record_the_episode_holds(world):
    value = {'organism': 'Escherichia coli', 'strain': 'K-12'}
    run(world, 'caller', [tool('caller_value', value=value, provider='caller_entry_context')])
    outcome, store = outcomes(world, 'caller')[0], world['store']
    done = outcome['outcome']
    assert (done['provider'], done['origin'], done['value'], done['held']) == (
        'caller_entry_context', 'caller', value, [True, True])
    # The Store's own rule made the record: the same value written by the Store itself is the same record.
    assert store._caller_source(value, 'caller_entry_context')['id'] == done['source']
    assert outcome['produced'] == [done['source'], done['artifact']] == produced_receipts(world, 'caller')


# -- declared tables in place of statements and commits; a withdrawn row in place of a delete -----------------------
def test_a_job_registry_is_kept_without_a_commit_and_a_cleared_failure_is_withdrawn_not_deleted(world):
    plan = [tool('job', job='j1', register={'query': 'MKT'}, fail='timeout'), tool('job', job='j1', clear=True),
            tool('job', job='j1', fail='timeout'), tool('job', job='j1', clear=True),
            tool('job', job='j1', fail='quota'), tool('job', job='j2', register={'query': 'AAA'})]
    run(world, 'jobs', plan)
    first, cleared, same, again_cleared, other, second = [item['outcome'] for item in outcomes(world, 'jobs')]
    row = first['failed'][0]
    assert first['before'] is None and first['failed'] == [row, False, 1] and first['current'] == 'timeout'
    assert first['history'] == [['timeout', False, 1]] and first['submitted'] == ['j1']
    assert first['in_transaction'] is False                   # each write committed by itself; nothing left open
    assert first['unwritten']['raised'].startswith(
        'WorkTableError: work_table_row_to_withdraw_was_not_written_by_this_episode')
    # Cleared: the row stays, marked, as its next revision; a select no longer returns it.
    assert cleared['before'] == 'timeout' and cleared['cleared'] == [row, True, 2, 1]
    assert cleared['current'] is None and cleared['history'] == [['timeout', True, 2]]
    # Written again with the same values: the same row, live again.
    assert same['failed'] == [row, False, 3] and same['current'] == 'timeout'
    assert again_cleared['cleared'] == [row, True, 4, 3] and again_cleared['current'] is None
    assert other['failed'] == [row, False, 5] and other['current'] == 'quota'
    assert second['submitted'] == ['j2', 'j1'] and second['current'] is None
    # The rows are in the Store and are the units' products.
    stored = WorkRows(world['store']).row(row)
    assert (stored['cause'], stored['withdrawn'], stored['revision'], stored['unit']) == ('quota', False, 5, 4)
    produced = [item['produced'] for item in outcomes(world, 'jobs')]
    assert produced[1] == produced[2] == produced[3] == produced[4] == [row]
    assert first['registered'] in produced[0] and row in produced[0] and len(produced[0]) == 3
    # Another Episode holds none of it.
    run(world, 'elsewhere', [tool('job', job='j1')])
    assert outcomes(world, 'elsewhere')[0]['outcome']['history'] == []
    assert outcomes(world, 'elsewhere')[0]['outcome']['submitted'] == []


@pytest.mark.parametrize('reclaim', [False, True])
def test_a_withdrawal_by_a_unit_that_did_not_finish_is_taken_back(world, reclaim):
    plan = [tool('job', job='j', fail='timeout'), tool('job', job='j', clear=True, cut=True, reclaim=reclaim)]
    world['switch'].fail = True
    with pytest.raises(RuntimeError, match='cut after the failure was cleared'):
        run(world, 'withdrawn', plan)
    world['switch'].fail = False
    row = outcomes(world, 'withdrawn')[0]['outcome']['failed'][0]
    assert WorkRows(world['store']).row(row)['withdrawn'] is True          # the abandoned attempt's write
    again(world, 'withdrawn')
    rerun = outcomes(world, 'withdrawn')[1]
    done = rerun['outcome']
    # Before the unit ran again the row stood as before the unit: live, at revision 1. The rerun was told.
    assert done['before'] == 'timeout' and done['told'] == [[True, 2, [False, 1]]]
    assert done['current'] is None and done['history'] == [['timeout', True, 2]]
    assert rerun['produced'] == [row]
    if not reclaim:
        assert done['cleared'] == [row, True, 2, 1]


# -- the section of a call; what a write created; the work cache -----------------------------------------------------
def test_a_function_that_calls_itself_knows_its_outermost_call(world):
    run(world, 'sections', [tool('sections', value=4, ref=world['subject'], dependents=['d1', 'd2']),
                            tool('sections', value=5, ref=world['subject'], dependents=['d1'])])
    first, second = [item['outcome'] for item in outcomes(world, 'sections')]
    assert first['trace'] == ['outer:main', 'inner:d1', 'inner:d2']    # the dependents did not refresh again
    assert first['cells'] == {'main': [['a1', 4]], 'd1': [['a1', 4]], 'd2': [['a1', 4]]}
    assert (first['outer_again'], first['inner'], first['other']) == (True, False, True)
    assert second['trace'] == ['outer:main', 'inner:d1']                # nothing is left set after a unit


def test_what_a_write_created_is_asked_of_custody(world):
    run(world, 'publish', [tool('publish_twice', accession='P1'), tool('publish_twice', accession='P1')])
    first, second = [item['outcome'] for item in outcomes(world, 'publish')]
    assert first['first'] == first['second'] and first['created'] == [first['first']]
    assert second['first'] == first['first'] and second['created'] == []       # held since the first unit
    # Another Episode writes the same content: the same record, new to it, held as its own product.
    assert world['store'].get(first['first'])['accession'] == 'P1'
    run(world, 'publish_b', [tool('publish_twice', accession='P1')])
    other = outcomes(world, 'publish_b')[0]
    assert other['outcome']['first'] == first['first'] and other['outcome']['created'] == [first['first']]
    assert first['first'] in other['produced']


def test_the_work_cache_serves_every_episode_and_each_holds_its_own_artifact(world):
    url = 'https://example.org/paper/1'
    run(world, 'fetch_a', [tool('cached_fetch', url=url), tool('cache_directory', directory='aligner')])
    run(world, 'fetch_b', [tool('cached_fetch', url=url), tool('cache_directory', directory='aligner')])
    first, directory = [item['outcome'] for item in outcomes(world, 'fetch_a')]
    second, directory_again = [item['outcome'] for item in outcomes(world, 'fetch_b')]
    assert (first['asked'], first['cached_before'], first['cached_after'], first['downloads']) == (True, False, True, 1)
    assert (second['asked'], second['cached_before'], second['downloads']) == (False, True, 1)   # not asked again
    assert first['ref'] == second['ref'] and second['content'] == 'content of ' + url
    assert first['receipt'] == second['receipt'] == 'produced'        # each Episode wrote the bytes itself
    assert outcomes(world, 'fetch_b')[0]['produced'] == [second['ref']]
    assert (directory['existed'], directory['entries']) == (False, 1)
    assert (directory_again['existed'], directory_again['entries']) == (True, 2)
    assert directory['bad_name']['raised'].startswith('ValueError: work_cache_directory_must_be')
    # The cache is a service: built per run on first use, recorded, and durable below its own directory.
    assert [build['name'] for build in world['journal'].service_builds('fetch_b')] == ['work_cache', 'counter']
    kept = WorkCache(world['tmp'] / 'work_cache')
    assert kept.get('fetched', {'url': url}) == ('content of ' + url).encode()
    assert kept.get('fetched', {'url': 'https://example.org/paper/2'}) is None
    assert not (world['tmp'] / 'store' / 'cache').exists()               # nothing of it is in the Store


def test_what_the_system_operations_refuse_besides_custody(world):
    run(world, 'refusals', [tool('refusals')])
    done = outcomes(world, 'refusals')[0]['outcome']
    assert {label: answer['raised'].split(':')[0] + ':' + answer['raised'].split(':')[1]
            for label, answer in done.items() if label != 'cancel_event'} == {
        'scratch_name': 'ValueError: scratch_directory_name_must_be_a_lowercase_label',
        'section_name': 'ValueError: section_name_must_be_non_empty_text',
        'references_of_a_row': 'ValueError: store_record_reference_required',
        'withdrawn_filter': 'WorkTableError: work_table_withdrawn_must_be_a_boolean',
        'withdrawal_key': 'WorkTableError: work_table_withdrawal_must_name_exactly_the_key',
        'positions_page': 'ValueError: invalid_page',
        'cache_data': 'TypeError: work_cache_data_must_be_bytes',
        'cache_namespace': 'ValueError: work_cache_namespace_must_be_a_lowercase_identifier',
        'cache_key': 'TypeError: work_cache_key_must_be_closed_json',
        'copy_of_a_row': 'ValueError: artifact_reference_required'}
    assert done['cancel_event'] == 'ValueError: scratch_computation_is_given_its_cancel_event_by_the_system'
    assert scratch_left(world) == []


def test_the_units_operations_are_refused_outside_a_tool_unit_and_the_rules_reach_nothing_else(world):
    """The scoped store of an Episode whose unit has ended, built as the runner builds it: a scratch directory, a
    section, a stream and a withdrawal belong to a running tool unit. The Store's rules run over ``HeldStore``,
    which offers the custody-limited reads, the rules and nothing else."""
    run(world, 'ended', [tool('row_write', k='x', v=1)])
    path = probe_path('ended')
    rows = WorkRows(world['store'])
    episode_id = EpisodeRef('ended', path).episode_id
    custody = Custody(world['journal'], StoreLedger(world['store'], rows), 'ended', path, episode_id,
                      UnitPosition(world['journal'], 'ended', path))
    store = ScopedStore(world['store'], custody, rows, ('ended', episode_id))
    for call, code in ((lambda: store.scratch('late').__enter__(), 'scratch_directory_outside_a_tool_unit'),
                       (lambda: store.section('late').__enter__(), 'section_outside_a_tool_unit'),
                       (lambda: store.artifact_stream([b'late']), 'artifact_stream_outside_a_tool_unit'),
                       (lambda: store.table(LEDGER).withdraw({'k': 'x'}), 'record_written_outside_a_tool_unit'),
                       (lambda: store.artifact_file(REPOSITORY / 'pyproject.toml'),
                        'record_written_outside_a_tool_unit'),
                       (lambda: store.caller_source({'a': 1}, 'caller'), 'record_written_outside_a_tool_unit')):
        with pytest.raises(CustodyError, match=code):
            call()
    assert world['store'].list('source') == [] and not (world['tmp'] / 'store' / 'scratch').exists()
    assert [row['v'] for row in store.table(LEDGER).select()] == [1]          # reading stays possible
    rules = HeldStore(world['store'], store)
    assert sorted(vars(rules)) == sorted([*HeldStore.READS, *HeldStore.RULES, *HeldStore.PURE, '_db'])
    assert not hasattr(rules, 'put') and not hasattr(rules, 'path') and not hasattr(rules, 'get_artifact')
    with pytest.raises(CustodyError, match='store_rule_asked_the_connection_for_something_else'):
        rules._db.execute('SELECT data FROM records')
    with pytest.raises(CustodyError, match='record_not_held'):
        rules.get(world['unrelated'])


# -- the Store's ownership rules over held records -------------------------------------------------------------------
@pytest.fixture
def assessed(world, problem):  # noqa: F811
    """A hypothesis about the problem's target, an observation and the assessment that links them."""
    store, target = world['store'], problem['target']
    hypothesis = store.put('hypothesis', {'subject_refs': [target], 'predicate': 'sequence_integrity',
                                          'value': {'type': 'enum', 'value': 'intact'}, 'context_refs': []},
                           origin='reasoning')['id']
    observation = store.put('observation', {
        'subject_refs': [target], 'source_subject_refs': [], 'kind': 'source_content', 'source_ref': problem['source'],
        'measurements': [], 'dependencies': [], 'anchor': None}, origin='external')['id']
    assessment = store.put('assessment', {
        'hypothesis_ref': hypothesis, 'observation_ref': observation, 'relation': 'strengthens',
        'applicability': 'direct', 'extent_basis': 'observed_extent', 'condition_refs': [], 'assumption_refs': [],
        'expected_revision': 0}, origin='reasoning')['id']
    return {'target': target, 'hypothesis': hypothesis, 'observation': observation, 'assessment': assessment}


def followed(world, run_id, held, calls, inputs=()):
    run(world, run_id, [tool('follow', calls=calls)], assignment={'held_refs': held, 'input_refs': list(inputs)})
    return outcomes(world, run_id)[0]['outcome']


def test_the_stores_ownership_rules_answer_for_a_held_record_and_read_only_held_records(world, assessed):
    store, target, assessment = world['store'], assessed['target'], assessed['assessment']
    scope = {'subject_refs': [target]}
    calls = {'extent': ['assessment_write_extent', assessment],
             'owned': ['assert_library_write_scope', assessment, scope],
             'roots': ['roots', assessment], 'hypothesis_roots': ['roots', assessed['hypothesis']],
             'named': ['named_references', assessment],
             'not_an_assessment': ['assessment_write_extent', assessed['hypothesis']]}
    whole = followed(world, 'rules', [assessment, assessed['hypothesis'], assessed['observation']], calls,
                     inputs=[target])
    stored = store.get(assessment)
    # Each answer is the Store's own rule's answer for the stored record.
    assert whole['extent'] == {'ok': store._assessment_write_extent(stored)}
    assert whole['extent']['ok'] == [{'target_ref': target, 'unit': 'aa', 'start': 0, 'end': 33}]
    assert whole['owned'] == {'ok': None}
    assert whole['roots'] == {'ok': store._record_roots('assessment', stored)} == {'ok': [target]}
    assert whole['hypothesis_roots'] == {'ok': store._record_roots('hypothesis', store.get(assessed['hypothesis']))}
    assert whole['named'] == {'ok': list(store._refs(stored))}
    assert whole['named']['ok'] == [assessed['hypothesis'], assessed['observation']]
    assert whole['not_an_assessment']['raised'].startswith('ValueError: assessment_reference_required')
    # The assessment alone: the rules are refused at the first record they would follow (its hypothesis); what
    # the record itself says (its roots, the references it names) is answered.
    alone = followed(world, 'rules_alone', [assessment], calls)
    assert alone['extent']['raised'].startswith(REFUSED) and alone['extent']['raised'].endswith(assessed['hypothesis'])
    assert alone['owned']['raised'].startswith(REFUSED)
    assert alone['roots'] == whole['roots'] and alone['named'] == whole['named']
    # With the hypothesis but not the subject it names, and with both but not the observation.
    partly = followed(world, 'rules_partly', [assessment, assessed['hypothesis']], calls)
    assert partly['extent']['raised'].startswith(REFUSED) and partly['extent']['raised'].endswith(target)
    nearly = followed(world, 'rules_nearly', [assessment, assessed['hypothesis']], calls, inputs=[target])
    assert nearly['extent']['raised'].endswith(assessed['observation'])
    # Not held at all.
    nothing = followed(world, 'rules_nothing', [], calls)
    for label in calls:
        assert nothing[label]['raised'].startswith(REFUSED), (label, nothing[label])


# -- the measures of a scope and of a context mask ---------------------------------------------------------------
def test_the_measures_of_a_scope_and_of_a_context_mask_over_a_held_target(world, problem):  # noqa: F811
    store, target = world['store'], problem['target']
    scope = {'subject_refs': [target]}
    part = {'subject_refs': [target], 'segments': [{'target_ref': target, 'start': 2, 'end': 12, 'unit': 'aa'}]}
    calls = {'scope_measure': ['scope_measure', scope, target], 'part_measure': ['scope_measure', part, target],
             'mask_measure': ['context_mask_measure', part, target],
             'mask_full': ['context_mask_target_full', scope, target],
             'part_full': ['context_mask_target_full', part, target],
             'mask_segments': ['context_mask_dimension_segments', part, target],
             'positions': ['context_mask_positions', part, target],
             'second_position': ['context_mask_positions', scope, target, 1, 1]}
    run(world, 'measures', [tool('follow', calls=calls), tool('spans', scope=part),
                            tool('spans', scope=scope, target_ref=target)], assignment={'input_refs': [target]})
    done, part_spans, whole_spans = [item['outcome'] for item in outcomes(world, 'measures')]
    for label, (operation, *arguments) in calls.items():
        if not label.endswith('position') and label != 'positions':
            assert done[label] == {'ok': json.loads(json.dumps(getattr(store, operation)(*arguments)))}, label
    assert (done['scope_measure'], done['part_measure'], done['mask_measure']) == ({'ok': 33}, {'ok': 10}, {'ok': 10})
    assert (done['mask_full'], done['part_full']) == ({'ok': True}, {'ok': False})
    assert done['mask_segments'] == {'ok': [{'start': 2, 'end': 12}]}
    # The positions are the rows of the Store's own query, which is not handed out.
    sql, parameters = store.context_mask_target_query(part, target)
    assert done['positions'] == {'ok': [dict(row) for row in store._db.execute(sql, parameters)]}
    assert done['positions']['ok'] == [{'target_ref': target, 'member_ref': None, 'dimension_ref': target,
                                        'read_ref': target, 'length': 33, 'unit': 'aa', 'start': 2, 'end': 12}]
    assert done['second_position'] == {'ok': []}
    assert part_spans == {'ok': list(store.iter_scope_coverage(part))} == {'ok': part['segments']}
    assert whole_spans == {'ok': [{'target_ref': target, 'start': 0, 'end': 33, 'unit': 'aa'}]}
    # An Episode that does not hold the target is refused every one of them.
    run(world, 'unheld_measures', [tool('follow', calls=calls), tool('spans', scope=scope)])
    refused, spans = [item['outcome'] for item in outcomes(world, 'unheld_measures')]
    for label in calls:
        assert refused[label]['raised'].startswith(REFUSED), (label, refused[label])
    assert spans['raised'].startswith(REFUSED)


@pytest.fixture
def reads(world):
    """A problem whose target is a read library of three reads, and a hypothesis about the second read."""
    store = world['store']
    path = world['tmp'] / 'reads.fastq'
    path.write_text(FASTQ)
    library, = store.create_problem(str(path), molecule='dna', role='read')['subject_refs']
    members = [row['id'] for row in store.material_members(store.get_input(library)['collection_refs'][0])['members']]
    subjects = [store.read_subject_ref(library, member) for member in members]
    hypothesis = store.put('hypothesis', {'subject_refs': [subjects[1]], 'predicate': 'sequence_integrity',
                                          'value': {'type': 'enum', 'value': 'intact'}, 'context_refs': []},
                           origin='reasoning')['id']
    # A frozen selection of the second read, and a context record about that selection.
    selection = library_targets.select(store, library, scope={'subject_refs': [library]},
                                       member_refs=[members[1]])['id']
    note = store.artifact('The second read was selected.', 'text/plain')
    source = store.put('source', {'provider': 'test', 'accession': 'S1', 'uri': None, 'artifact_ref': note,
                                  'text_ref': note, 'request_ref': None, 'version': None, 'retrieved_at': None},
                       origin='external')['id']
    context = store.put('context', {'context_type': 'sample', 'name': 'selected reads', 'source_ref': source,
                                    'attributes': [], 'related_refs': [selection], 'anchor': None},
                        origin='external')['id']
    return {'library': library, 'members': members, 'subjects': subjects, 'hypothesis': hypothesis,
            'selection': selection, 'context': context}


def member_scope(reads, index, length):
    return {'subject_refs': [reads['library']], 'segments': [{
        'target_ref': reads['library'], 'member_ref': reads['members'][index], 'start': 0, 'end': length,
        'unit': 'nt'}]}


def test_a_read_library_is_measured_and_its_ownership_checked_over_held_records(world, reads):
    store, library = world['store'], reads['library']
    scope = {'subject_refs': [library]}
    second, third = member_scope(reads, 1, 12), member_scope(reads, 2, 4)
    calls = {'measure': ['scope_measure', scope, library], 'member_measure': ['scope_measure', second, library],
             'read_subject': ['read_subject_ref', library, reads['members'][1]],
             'mask_measure': ['context_mask_measure', second, library],
             'mask_full': ['context_mask_target_full', scope, library],
             'mask_segments': ['context_mask_dimension_segments', second, reads['subjects'][1]],
             'other_segments': ['context_mask_dimension_segments', second, reads['subjects'][0]],
             'positions': ['context_mask_positions', scope, library],
             'one_position': ['context_mask_positions', scope, library, 1, 1],
             'owned': ['assert_library_write_scope', reads['hypothesis'], scope],
             'owned_by_its_read': ['assert_library_write_scope', reads['hypothesis'], second],
             'owned_by_another_read': ['assert_library_write_scope', reads['hypothesis'], third]}
    held = [reads['hypothesis'], reads['subjects'][1]]
    run(world, 'library', [tool('follow', calls=calls), tool('spans', scope=scope)],
        assignment={'input_refs': [library], 'held_refs': held})
    done, spans = [item['outcome'] for item in outcomes(world, 'library')]
    for label in ('measure', 'member_measure', 'read_subject', 'mask_measure', 'mask_full', 'mask_segments',
                  'other_segments'):
        operation, *arguments = calls[label]
        assert done[label] == {'ok': json.loads(json.dumps(getattr(store, operation)(*arguments)))}, label
    assert (done['measure'], done['member_measure'], done['mask_measure']) == ({'ok': 26}, {'ok': 12}, {'ok': 12})
    assert done['read_subject'] == {'ok': reads['subjects'][1]} and done['mask_full'] == {'ok': True}
    assert done['mask_segments'] == {'ok': [{'start': 0, 'end': 12}]} and done['other_segments'] == {'ok': []}
    positions = done['positions']['ok']
    assert sorted((row['member_ref'], row['read_ref'], row['start'], row['end']) for row in positions) == sorted(
        zip(reads['members'], reads['subjects'], [0, 0, 0], [10, 12, 4]))
    assert done['one_position'] == {'ok': positions[1:2]}
    assert spans == {'ok': list(store.iter_scope_coverage(scope))} and len(spans['ok']) == 3
    # Ownership: the hypothesis is about the second read. A scope of the whole library or of that read owns it;
    # a scope of another read does not (the Store's own refusal).
    assert done['owned'] == done['owned_by_its_read'] == {'ok': None}
    assert done['owned_by_another_read']['raised'].startswith('ContractError: record_subject_member_outside_scope')
    for wanted in (second, third):
        try:
            store._assert_library_write_scope('hypothesis', store.get(reads['hypothesis']), wanted)
            answer = {'ok': None}
        except Exception as error:      # noqa: BLE001 - compared with what the Episode was told
            answer = {'raised': type(error).__name__ + ': ' + str(error)}
        assert done['owned_by_its_read' if wanted is second else 'owned_by_another_read'] == answer
    # A context record about a frozen selection of reads: owned by a scope of that selection (the Store compares
    # the selection's members), not by a scope of another read. The selection must be held to be followed.
    selected = {'subject_refs': [library], 'read_selection_refs': [reads['selection']]}
    about = {'by_its_selection': ['assert_library_write_scope', reads['context'], selected],
             'by_another_read': ['assert_library_write_scope', reads['context'], third],
             'selected_measure': ['scope_measure', selected, library]}
    context = followed(world, 'library_selection', [reads['context'], reads['selection']], about, inputs=[library])
    assert context['by_its_selection'] == {'ok': None} and context['selected_measure'] == {'ok': 12}
    assert context['by_another_read']['raised'].startswith('ContractError: record_subject_member_outside_scope')
    with pytest.raises(Exception, match='record_subject_member_outside_scope'):
        store._assert_library_write_scope('context', store.get(reads['context']), third)
    unselected = followed(world, 'library_unselected', [reads['context']], {'owned': about['by_another_read']},
                          inputs=[library])
    assert unselected['owned']['raised'].startswith(REFUSED)
    assert unselected['owned']['raised'].endswith(reads['selection'])
    # Without the read the hypothesis is about, the rule is refused where it would follow it; without the library
    # nothing is answered.
    lone = followed(world, 'library_lone', [reads['hypothesis']], {'owned': calls['owned_by_its_read']},
                    inputs=[library])
    assert lone['owned']['raised'].startswith(REFUSED) and lone['owned']['raised'].endswith(reads['subjects'][1])
    nothing = followed(world, 'library_nothing', [], calls)
    for label in calls:
        assert nothing[label]['raised'].startswith(REFUSED), (label, nothing[label])


# -- the original reads of a read library: a page of them, a frozen selection, the selection's reads ----------------
SEQUENCES = ['ACGTACGTAC', 'GGGTTTAAACCC', 'ACGT']


def selection_rows(store, selection):
    """The reads of a selection as the Store keeps them."""
    return [row[0] for row in store._db.execute(
        'SELECT read_ref FROM library_selection_members WHERE selection_ref=? ORDER BY read_ref', (selection,))]


def test_a_selection_of_a_librarys_reads_is_frozen_listed_paged_and_written_out_under_custody(world, reads):
    """The Episode holds the library and its collection, not one read. It freezes a selection of the first and
    third read, holds the selection as produced, lists its reads, pages them and writes them as FASTA; credit
    reads the same through the read-only reader."""
    store, library, members, subjects = world['store'], reads['library'], reads['members'], reads['subjects']
    collection, = store.get_input(library)['collection_refs']
    plan = [tool('select_reads', library=library, choose={'member_refs': [members[0], members[2]]},
                 lose={'ordinal_ranges': [{'start': 0, 'end': 2}]})]
    run(world, 'select', plan, assignment={'input_refs': [library], 'held_refs': [collection]},
        credit={'rule': 'selected_reads'}, controller={'kind': 'completion', 'target': 2})
    outcome = outcomes(world, 'select')[0]
    done, chosen = outcome['outcome'], sorted([subjects[0], subjects[2]])
    selection = done['selection']
    # The record is the Store's own read selection, written with its rows; the Episode holds it as its product.
    assert (selection['record_type'], selection['library_ref'], selection['origin']) == ('read_selection', library,
                                                                                         'tool')
    assert (selection['member_count'], selection['position_mass']) == (2, 14)
    assert json.loads(json.dumps(store.get(selection['id']))) == selection
    assert done['held'] is True and done['receipt'] == 'produced' and done['same_again'] is True
    assert outcome['produced'] == [selection['id']] == produced_receipts(world, 'select')
    assert done['members'] == chosen == selection_rows(store, selection['id'])
    # The Store itself freezes the same reads as the same record.
    assert library_targets.select(store, library, scope={'subject_refs': [library]},
                                  member_refs=[members[2], members[0]])['id'] == selection['id']
    # The page is the Store's own page of the selection, in the library's order.
    assert done['page'] == json.loads(json.dumps(library_targets.member_page(
        store, library, scope={'subject_refs': [library]}, selection_ref=selection['id'])))
    assert [row['id'] for row in done['page']['members']] == [subjects[0], subjects[2]]
    assert (done['page']['total'], done['page']['next_offset'], done['page']['selection_ref']) == (
        2, None, selection['id'])
    assert done['measure'] == 14
    # No read is held: each was read through the held library, selection and collection.
    assert not any(row['ref'] in subjects for row in world['journal'].receipts('select', probe_path('select')))
    sequence = dict(zip(subjects, SEQUENCES))
    assert done['fasta'] == ''.join('>' + ref + '\n' + sequence[ref] + '\n' for ref in chosen)
    # A selection frozen in a transaction that rolled back: held and listed inside, then neither held nor stored.
    assert done['lost_inside'] == [True, sorted(subjects[:2])] and done['lost_held'] is False
    assert done['lost_members']['raised'].startswith(REFUSED)
    assert selection_rows(store, done['lost']) == []
    with pytest.raises(Exception, match='unknown'):
        store.get(done['lost'])
    # Credit counted the selected reads through the read-only reader (list and page agreed).
    assert [unit[1]['credit'] for unit in world['journal'].units('select', probe_path('select'))] == [2.0]


def read_calls(world, run_id, held, calls, inputs=()):
    run(world, run_id, [tool('reads', calls=calls)], assignment={'held_refs': held, 'input_refs': list(inputs)})
    return outcomes(world, run_id)[0]


def test_the_reads_of_a_library_are_paged_and_frozen_only_by_an_episode_that_holds_what_is_read(world, reads):
    store, library, members, subjects = world['store'], reads['library'], reads['members'], reads['subjects']
    selection, whole = reads['selection'], {'subject_refs': [library]}          # the selection: the second read
    collection, = store.get_input(library)['collection_refs']
    selected = {'subject_refs': [library], 'read_selection_refs': [selection]}
    calls = {'page': ['page', [library], {}],
             'second': ['page', [library], {'offset': 1, 'limit': 1}],
             'of_the_selection': ['page', [library], {'selection_ref': selection}],
             'within_the_third_read': ['page', [library], {'scope': member_scope(reads, 2, 4)}],
             'within_the_selection': ['page', [library], {'scope': selected}],
             'selected': ['selected', [selection], {}],
             'fasta': ['fasta', [selection], {}],
             'by_ordinal': ['freeze', [library], {'ordinal_ranges': [{'start': 1, 'end': 3}]}],
             'outside_its_scope': ['freeze', [library], {'member_refs': [members[0]],
                                                         'scope': member_scope(reads, 2, 4)}],
             'both_ways': ['freeze', [library], {'member_refs': [members[0]],
                                                 'ordinal_ranges': [{'start': 0, 'end': 1}]}],
             'page_size': ['page', [library], {'limit': 0}],
             'not_a_selection': ['selected', [library], {}]}
    outcome = read_calls(world, 'reads', [collection, selection], calls, inputs=[library])
    done = outcome['outcome']
    for label in ('page', 'second', 'of_the_selection', 'within_the_third_read', 'within_the_selection'):
        keywords = {'scope': whole, **calls[label][2]}
        assert done[label] == {'ok': json.loads(json.dumps(library_targets.member_page(store, library, **keywords)))}
    listed = {label: [row['id'] for row in done[label]['ok']['members']]
              for label in ('page', 'second', 'of_the_selection', 'within_the_third_read', 'within_the_selection')}
    assert listed == {'page': subjects, 'second': [subjects[1]], 'of_the_selection': [subjects[1]],
                      'within_the_third_read': [subjects[2]], 'within_the_selection': [subjects[1]]}
    assert (done['page']['ok']['total'], done['second']['ok']['next_offset']) == (3, 2)
    assert done['selected'] == {'ok': [subjects[1]]} == {'ok': selection_rows(store, selection)}
    assert done['fasta'] == {'ok': '>' + subjects[1] + '\n' + SEQUENCES[1] + '\n'}
    frozen = done['by_ordinal']['ok']
    assert (frozen['member_count'], frozen['position_mass']) == (2, 16)
    assert selection_rows(store, frozen['id']) == sorted(subjects[1:]) and outcome['produced'] == [frozen['id']]
    # What the Store's own rules refuse is the Store's refusal.
    assert {label: done[label]['raised'].split(':')[1].strip() for label in (
        'outside_its_scope', 'both_ways', 'page_size', 'not_a_selection')} == {
        'outside_its_scope': 'selected_member_outside_assigned_scope',
        'both_ways': 'choose_original_members_or_ordinal_ranges', 'page_size': 'invalid_page',
        'not_a_selection': 'wrong_reference_type'}
    # Without the library's collection no read of the library is read or frozen; the held selection still names
    # its reads.
    bare = read_calls(world, 'reads_bare', [selection], calls, inputs=[library])
    for label in ('page', 'second', 'of_the_selection', 'within_the_selection', 'fasta', 'by_ordinal', 'page_size'):
        assert bare['outcome'][label]['raised'].startswith(REFUSED), (label, bare['outcome'][label])
        assert bare['outcome'][label]['raised'].endswith(collection), (label, bare['outcome'][label])
    assert bare['outcome']['selected'] == done['selected'] and bare['produced'] == []
    # Without the selection: the whole library is paged, nothing of the selection is.
    unselected = read_calls(world, 'reads_unselected', [collection], calls, inputs=[library])['outcome']
    assert unselected['page'] == done['page']
    for label in ('of_the_selection', 'within_the_selection', 'selected', 'fasta'):
        assert unselected[label]['raised'].startswith(REFUSED) and unselected[label]['raised'].endswith(selection)
    # Without the library itself.
    apart = read_calls(world, 'reads_apart', [collection, selection], calls)['outcome']
    for label in ('page', 'of_the_selection', 'by_ordinal', 'fasta'):
        assert apart[label]['raised'].startswith(REFUSED) and apart[label]['raised'].endswith(library)
    assert apart['selected'] == done['selected']
    # A member the Episode does not hold cannot be named; something that is no library is the Store's refusal.
    stray = read_calls(world, 'reads_stray', [collection], {
        'stray_member': ['freeze', [library], {'member_refs': [members[0], 'member_' + '0' * 24]}],
        'not_a_library': ['page', [world['subject']], {}]}, inputs=[library])
    assert stray['outcome']['stray_member']['raised'].startswith(REFUSED) and stray['produced'] == []
    assert stray['outcome']['not_a_library']['raised'].startswith('ContractError: unknown_input')
    nothing = read_calls(world, 'reads_nothing', [], calls)['outcome']
    for label in calls:
        assert nothing[label]['raised'].startswith(REFUSED), (label, nothing[label])


def test_the_reads_of_a_selection_are_listed_in_order_whole_or_by_page(world, reads):
    store, library, members, subjects = world['store'], reads['library'], reads['members'], reads['subjects']
    pair = library_targets.select(store, library, scope={'subject_refs': [library]},
                                  member_refs=[members[0], members[2]])['id']
    ordered = sorted([subjects[0], subjects[2]])
    calls = {'all': ['selection_members', pair], 'first': ['selection_members', pair, 1],
             'rest': ['selection_members', pair, None, 1], 'none': ['selection_members', pair, 0],
             'page': ['selection_members', pair, -1], 'a_read': ['get', ordered[0]]}
    done = followed(world, 'listed', [pair], calls)
    assert done['all'] == {'ok': ordered} == {'ok': selection_rows(store, pair)}
    assert (done['first'], done['rest'], done['none']) == ({'ok': ordered[:1]}, {'ok': ordered[1:]}, {'ok': []})
    assert done['page']['raised'] == 'ValueError: invalid_page'
    # The references are names: a read is read by its reference only when that reference is held.
    assert done['a_read']['raised'].startswith(REFUSED) and done['a_read']['raised'].endswith(ordered[0])
    assert followed(world, 'listed_and_held', [pair, ordered[0]], calls)['a_read']['ok']['id'] == ordered[0]
    assert followed(world, 'unlisted', [], calls)['all']['raised'].startswith(REFUSED)


# -- the diagnostics of tool outcomes ------------------------------------------------------------------------------
def text_artifact(text):
    return 'artifact_' + hashlib.sha256(text.encode()).hexdigest()


def credits(world, run_id):
    return [unit[1]['credit'] for unit in world['journal'].units(run_id, probe_path(run_id))]


def test_the_diagnostic_of_a_tool_outcome_is_known_to_the_episode_whose_tool_returned_it(world):
    """Three tool units; the first and the second return a diagnostic beside the data they kept. Credit counts the
    produced records that may be read as a source."""
    failure, parser = 'the provider answered 503', 'the parser stopped at row 7'
    kept = [text_artifact('rows kept before the failure'), text_artifact('rows of the second request'),
            text_artifact('rows of the third request')]
    plan = [tool('diagnosed', data='rows kept before the failure', error=failure),
            tool('diagnosed', data='rows of the second request', nested_error=parser,
                 ask=[text_artifact(failure), kept[0], world['subject'], world['unrelated']]),
            tool('diagnosed', data='rows of the third request', ask=[text_artifact(parser), kept[1]])]
    run(world, 'diagnosed', plan, credit={'rule': 'sources'})
    first, second, third = outcomes(world, 'diagnosed')
    assert first['outcome']['feedback']['diagnostic_ref'] == text_artifact(failure)
    assert first['produced'] == [kept[0], text_artifact(failure)]
    assert second['outcome']['feedback']['acquisition_error']['diagnostic_ref'] == text_artifact(parser)
    # While its tool ran, the first unit had no outcome: nothing named its diagnostic yet.
    assert first['outcome']['while_running'] is True
    # Later units are told: the diagnostic of an earlier outcome (at any depth) is not read as a source; the data
    # an earlier unit kept and a record the Episode was passed are; a record it does not hold is refused.
    assert second['outcome']['asked'] == {
        text_artifact(failure): {'ok': False}, kept[0]: {'ok': True}, world['subject']: {'ok': True},
        world['unrelated']: second['outcome']['asked'][world['unrelated']]}
    assert second['outcome']['asked'][world['unrelated']]['raised'].startswith(REFUSED)
    assert third['outcome']['asked'] == {text_artifact(parser): {'ok': False}, kept[1]: {'ok': True}}
    # Credit, through the read-only reader, as each unit was priced: the unit's own diagnostic is known as soon
    # as its tool has returned, so it never counted.
    assert credits(world, 'diagnosed') == [1.0, 2.0, 3.0]
    # Another Episode that is passed the records: they are not diagnostics of its outcomes.
    passed = followed(world, 'passed_diagnostic', [text_artifact(failure)], {
        'passed': ['is_diagnostic_ref', text_artifact(failure)], 'unheld': ['is_diagnostic_ref', kept[0]]})
    assert passed['passed'] == {'ok': False} and passed['unheld']['raised'].startswith(REFUSED)


def test_the_diagnostics_of_recorded_outcomes_are_known_again_when_the_run_is_resumed(world):
    failure = 'the provider answered 503'
    plan = [tool('diagnosed', data='rows kept before the failure', error=failure),
            tool('diagnosed', data='rows of the second request', ask=[text_artifact(failure)], cut=True)]
    world['switch'].fail = True
    with pytest.raises(RuntimeError, match='cut after the diagnostic was written'):
        run(world, 'diagnosed_cut', plan, credit={'rule': 'sources'})
    world['switch'].fail = False
    assert credits(world, 'diagnosed_cut') == [1.0]
    again(world, 'diagnosed_cut')
    second = outcomes(world, 'diagnosed_cut')[1]['outcome']
    assert second['asked'] == {text_artifact(failure): {'ok': False}}
    assert credits(world, 'diagnosed_cut') == [1.0, 2.0]
