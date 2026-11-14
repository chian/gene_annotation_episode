"""Received monitoring facts with saved records and a scripted C7 consumer.

These checks select fixture units/controllers.  They run no configured models,
native jobs or scientific investigation and install no production credit policy.
"""
import asyncio
from copy import deepcopy
import json

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_monitoring import MonitorEpisodes
from gene_annotation_episode.episode_progress_credit import ProgressInformationCredit, VERSION
from gene_annotation_episode.progress_records import job_status
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from method_loop.durable import DurableExecutionStore
from test_recursive_monitoring import assignment, durable_target
from test_runtime import FixtureController, ScriptedProvider


STAMP = '2026-10-21T12:00:00+00:00'
SCOPE = {'subject_refs': ['input_fixture']}


def context(*, scope=SCOPE, run_id='fixture-run', episode_id='receiver'):
    return BindingContext(run_id, episode_id, 'monitor', (('monitor', episode_id),),
                          scope, {}, {})


def selection(known=(), initial=(), **changes):
    return {'run_id': 'fixture-run', 'episode_id': 'receiver',
            'known_progress_refs': known, 'initial_progress_refs': initial, **changes}


def episode_status(target='target', *, state='executing', liveness='live', failure=None):
    returned = state in {'returned', 'admitted'}
    return {'version': 'execution_status_v1', 'handle': target,
        'commission_sha256': 'a' * 64, 'lifecycle_state': state, 'observed_at': STAMP,
        'execution_identity': None, 'liveness': liveness,
        'return_id': 'original-return' if returned else None, 'return_available': returned,
        'acknowledgment_id': 'original-ack' if state == 'admitted' else None,
        'failure': failure}


def snapshot(reference, *, target='target', status=None, committed=(), dependencies=()):
    status = deepcopy(status) if status is not None else episode_status(target)
    available = (status['return_available'] if status['version'] == 'execution_status_v1'
                 else status['result_available'])
    return {'version': 'progress_snapshot_v1', 'progress_ref': reference,
        'target_handle': target, 'observed_at': STAMP, 'provenance_refs': ['public-provenance'],
        'execution_status': status, 'measurements': [], 'log_windows': [],
        'committed_record_refs': list(committed), 'dependencies': list(dependencies),
        'result_available': available}


def native_status(target='job', *, state='running', outcome='pending', elapsed=1.,
                  available=True, closed=False, size=12, failure=None):
    return job_status(target, {'job_ref': target, 'registry_ref': 'execution_registry_fixture',
        'state': state, 'outcome': outcome, 'elapsed_seconds': elapsed,
        'duration_measure': 'systemd_service_wall_seconds', 'native_returncode': None,
        'failure_code': failure, 'resource': None,
        'progress_kind': 'native_execution_state_and_output_bytes_not_search_fraction',
        'outputs': [{'role': 'native_text', 'available': available,
                     'bytes': size if available else None, 'writer_closed': closed}]},
        observed_at=STAMP)


class SavedProgressReader:
    """Only the public read port is available; observations are immutable JSON."""

    def __init__(self, directory, values, *, scope=SCOPE):
        directory.mkdir()
        self.directory, self.scope, self.calls = directory, plain(scope), []
        for value in values:
            (directory / (value['progress_ref'] + '.json')).write_text(
                json.dumps(value, allow_nan=False))

    def read_progress(self, reference, scope):
        assert plain(scope) == self.scope
        self.calls.append(reference)
        return json.loads((self.directory / (reference + '.json')).read_text())


def project(tmp_path, values, *, known, initial=(), unit=.25):
    reader = SavedProgressReader(tmp_path / 'saved', values)
    binding = ProgressInformationCredit(reader, information_unit=unit)
    result = binding(context(), selection(known, initial))
    return result, reader, binding


@pytest.mark.parametrize('unit', [False, True, None, 0, -1, float('inf'),
                                 float('-inf'), float('nan'), '1', 10 ** 1000])
def test_explicit_finite_positive_units_are_required(unit):
    with pytest.raises(ValueError, match='explicit_positive_monitoring_information_unit_required'):
        ProgressInformationCredit(object(), information_unit=unit)


def test_no_unit_or_public_reader_is_inferred():
    with pytest.raises(TypeError):
        ProgressInformationCredit(object())
    with pytest.raises(TypeError, match='public_progress_reader_required'):
        ProgressInformationCredit(object(), information_unit=1)


def test_baseline_representations_and_repeated_delivery_do_not_earn_units(tmp_path):
    original = snapshot('initial')
    presented = deepcopy(original)
    presented.update(progress_ref='different-presentation', observed_at='2026-10-21T13:00:00Z',
                     provenance_refs=['different-source', 'different-opaque-observation-hash'])
    presented['execution_status'].update(observed_at=presented['observed_at'],
                                        commission_sha256='b' * 64)
    final = deepcopy(presented)
    final['progress_ref'] = 'final-return'
    result, reader, binding = project(tmp_path, [original, presented, final],
        initial=iter(['initial', 'initial']),
        known=iter(['initial', 'different-presentation', 'different-presentation', 'final-return']))
    assert result['credit'] == result['monitoring_information_credit'] == 0
    assert result['monitoring_information_contributions'] == []
    assert reader.calls == ['initial', 'different-presentation', 'final-return']
    assert result['known_progress_refs'] == ['initial', 'different-presentation', 'final-return']
    assert result['monitoring_information_binding'] == binding.as_record()
    assert binding.as_record()['version'] == VERSION
    json.dumps(binding.as_record(), allow_nan=False)


def test_one_snapshot_with_several_new_facts_earns_one_unit(tmp_path):
    base = snapshot('base', status=episode_status(state='pending', liveness='unknown'))
    active = snapshot('active', dependencies=[{'handle': 'dependent-job', 'kind': 'job',
        'relation_ref': 'source_actual_relationship', 'observed_at': STAMP, 'state': 'pending'}],
        committed=['source_requested_record'])
    result, _, _ = project(tmp_path, [base, active], initial=['base'], known=['active'], unit=3)
    assert result['credit'] == 3
    assert result['newly_informative_received_snapshot_count'] == 1
    assert result['monitoring_information_contributions'][0]['new_fact_count'] == 4


@pytest.mark.parametrize('known, expected', [(['combined', 'first'], 1),
                                            (['first', 'combined'], 2)])
def test_actual_receipt_order_controls_snapshot_contributions(tmp_path, known, expected):
    values = [snapshot('base'), snapshot('first', committed=['source_A']),
              snapshot('combined', committed=['source_B', 'source_A'])]
    result, reader, _ = project(tmp_path, values, known=known, initial=['base'], unit=2)
    assert result['credit'] == 2 * expected
    assert reader.calls == ['base', *known]


def test_seen_facts_are_per_target_and_baseline_does_not_require_known_prefix(tmp_path):
    values = [snapshot('inherited', target='other'), snapshot('received', target='target'),
              snapshot('inherited-later', target='other')]
    result, _, _ = project(tmp_path, values, initial=['inherited'],
                          known=['received', 'inherited-later'])
    assert result['credit'] == .25
    assert [row['target_handle'] for row in result['monitoring_information_contributions']] == ['target']


def test_failures_use_code_and_affected_relationships_not_diagnostic_ids_or_order(tmp_path):
    failure = {'code': 'execution_failed', 'affected_refs': ['job_A', 'job_B'],
               'diagnostic_ref': 'source_first_diagnostic', 'partial_record_refs': []}
    failed = snapshot('failed', status=episode_status(state='returned', liveness='not_live', failure=failure))
    changed = deepcopy(failed)
    changed['progress_ref'] = 'presentation'
    changed['execution_status']['failure'].update(affected_refs=['job_B', 'job_A'],
                                                 diagnostic_ref='source_second_diagnostic')
    novel = deepcopy(changed)
    novel['progress_ref'] = 'new-affected'
    novel['execution_status']['failure']['affected_refs'].append('job_C')
    result, _, _ = project(tmp_path, [failed, changed, novel], initial=['failed'],
                          known=['presentation', 'new-affected'])
    assert result['credit'] == .25
    assert result['monitoring_information_contributions'] == [
        {'progress_ref': 'new-affected', 'target_handle': 'target', 'new_fact_count': 1}]


def test_novel_dependencies_and_committed_availability_are_distinct_from_source_ids(tmp_path):
    dependency = {'handle': 'job_A', 'kind': 'job', 'relation_ref': 'source_relation_A',
                  'observed_at': STAMP, 'state': 'pending'}
    base = snapshot('base', dependencies=[dependency], committed=['source_permitted'])
    presentation = deepcopy(base)
    presentation['progress_ref'] = 'source-only'
    presentation['provenance_refs'] = ['source_new_provenance']
    presentation['log_windows'] = [{'source_ref': 'source_new_log', 'artifact_ref': 'artifact_new',
        'start_byte': 0, 'end_byte': 12, 'observed_at': STAMP, 'content_sha256': 'b' * 64}]
    presentation['dependencies'][0].update(observed_at='2026-10-21T13:00:00Z', state='executing')
    novel = deepcopy(presentation)
    novel.update(progress_ref='new-dependency', committed_record_refs=['source_permitted', 'source_new_permitted'])
    novel['dependencies'].append({**dependency, 'handle': 'job_B', 'relation_ref': 'source_relation_B'})
    result, _, _ = project(tmp_path, [base, presentation, novel], initial=['base'],
                          known=['source-only', 'new-dependency'])
    assert result['credit'] == .25
    assert result['monitoring_information_contributions'][0]['new_fact_count'] == 2


def test_native_byte_growth_unfinished_elapsed_logs_and_measurements_earn_nothing(tmp_path):
    base = snapshot('base', target='job', status=native_status())
    later = snapshot('later', target='job', status=native_status(elapsed=40, size=100))
    later['measurements'] = [{'name': 'elapsed_seconds', 'value': 40, 'unit': 'seconds',
                             'measured_at': STAMP, 'provenance_ref': 'source_new_status'}]
    later['log_windows'] = [{'source_ref': 'source_new_log', 'artifact_ref': 'artifact_new',
        'start_byte': 0, 'end_byte': 100, 'observed_at': STAMP, 'content_sha256': 'c' * 64}]
    result, _, _ = project(tmp_path, [base, later], initial=['base'], known=['later'])
    assert result['credit'] == 0


def test_native_terminal_duration_can_arrive_late_and_repeat_without_duplicate_credit(tmp_path):
    done = snapshot('terminal-no-duration', target='job', status=native_status(
        state='returned', outcome='succeeded', elapsed=None, closed=True))
    timed = snapshot('late-timing', target='job', status=native_status(
        state='returned', outcome='succeeded', elapsed=8.5, closed=True))
    repeated = deepcopy(timed)
    repeated.update(progress_ref='final-timing', provenance_refs=['source_final_status'])
    repeated['execution_status']['native']['outputs'][0]['bytes'] = 100
    result, _, _ = project(tmp_path, [done, timed, repeated], initial=['terminal-no-duration'],
                          known=['late-timing', 'final-timing'])
    assert result['credit'] == .25
    assert result['monitoring_information_contributions'] == [
        {'progress_ref': 'late-timing', 'target_handle': 'job', 'new_fact_count': 1}]


def test_inherited_completed_timing_is_known_and_terminal_durations_are_target_specific(tmp_path):
    timed = snapshot('inherited', target='job_A', status=native_status(
        'job_A', state='returned', outcome='succeeded', elapsed=8.5, closed=True))
    repeated = deepcopy(timed)
    repeated['progress_ref'] = 'received-again'
    other_before = snapshot('other-before', target='job_B', status=native_status(
        'job_B', state='returned', outcome='succeeded', elapsed=None, closed=True))
    other_timed = snapshot('other-timed', target='job_B', status=native_status(
        'job_B', state='returned', outcome='succeeded', elapsed=8.5, closed=True))
    result, _, _ = project(tmp_path, [timed, repeated, other_before, other_timed],
        initial=['inherited', 'other-before'], known=['received-again', 'other-timed'])
    assert result['credit'] == .25
    assert result['monitoring_information_contributions'] == [
        {'progress_ref': 'other-timed', 'target_handle': 'job_B', 'new_fact_count': 1}]


def test_unknown_episode_liveness_does_not_create_a_state_fact(tmp_path):
    values = [snapshot('live'), snapshot('unknown', status=episode_status(liveness='unknown')),
              snapshot('not-live', status=episode_status(liveness='not_live'))]
    result, _, _ = project(tmp_path, values, initial=['live'], known=['unknown', 'not-live'])
    assert result['credit'] == .25
    assert result['known_progress_refs'] == ['unknown', 'not-live']
    assert result['monitoring_information_contributions'] == [
        {'progress_ref': 'not-live', 'target_handle': 'target', 'new_fact_count': 1}]


def test_native_output_availability_and_writer_closure_are_actual_facts(tmp_path):
    values = [snapshot('missing', target='job', status=native_status(available=False)),
        snapshot('available', target='job', status=native_status(available=True)),
        snapshot('closed', target='job', status=native_status(
            state='returned', outcome='failed', elapsed=4, closed=True, failure='native_nonzero_exit'))]
    result, _, _ = project(tmp_path, values, initial=['missing'], known=['available', 'closed'])
    assert result['credit'] == .5
    assert [row['new_fact_count'] for row in result['monitoring_information_contributions']] == [2, 6]


def test_unknown_native_states_are_preserved_without_known_state_or_outcome_credit(tmp_path):
    unconfirmed = snapshot('unconfirmed', target='job', status=native_status(
        state='submission_unconfirmed', outcome='unknown', available=False))
    unknown = snapshot('unknown', target='job', status=native_status(
        state='execution_unknown', outcome='unknown', available=False, elapsed=120))
    result, reader, _ = project(tmp_path, [unconfirmed, unknown], initial=['unconfirmed'], known=['unknown'])
    assert result['credit'] == 0
    assert result['known_progress_refs'] == ['unknown']
    saved = reader.read_progress('unknown', SCOPE)
    assert saved['execution_status']['lifecycle_state'] is None
    assert saved['execution_status']['native']['state'] == 'execution_unknown'


@pytest.mark.parametrize('changes', [{'run_id': 'other-run'}, {'episode_id': 'other-episode'},
                                     {'run_id': None}, {'episode_id': None}])
def test_receiver_identity_is_checked_before_any_read(tmp_path, changes):
    reader = SavedProgressReader(tmp_path / 'saved', [snapshot('ref')])
    credit = ProgressInformationCredit(reader, information_unit=1)
    with pytest.raises(ValueError, match='receiver_identity_mismatch'):
        credit(context(), selection(['ref'], **changes))
    assert reader.calls == []


def test_only_supplied_progress_references_are_read_and_reader_scope_errors_survive(tmp_path):
    reader = SavedProgressReader(tmp_path / 'saved', [snapshot('supplied'), snapshot('unreceived')])
    credit = ProgressInformationCredit(reader, information_unit=1)

    class Unreadable:
        def __iter__(self):
            pytest.fail('scientific references must not be consulted')

    result = credit(context(), selection(['supplied'], known_record_refs=Unreadable(),
                                        initial_known_record_refs=Unreadable()))
    assert result['credit'] == 1 and reader.calls == ['supplied']
    with pytest.raises(AssertionError):
        credit(context(scope={'subject_refs': ['other']}), selection(['supplied']))


def test_public_record_identity_must_match_selected_reference_and_target(tmp_path):
    reader = SavedProgressReader(tmp_path / 'saved', [snapshot('selected')])
    credit = ProgressInformationCredit(reader, information_unit=1)
    path = reader.directory / 'selected.json'
    changed = snapshot('other-ref')
    path.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match='reference_identity_mismatch'):
        credit(context(), selection(['selected']))
    changed['progress_ref'] = 'selected'
    changed['execution_status']['handle'] = 'other-target'
    path.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match='target_identity_mismatch'):
        credit(context(), selection(['selected']))


def test_actual_c7_consumer_uses_received_facts_and_emits_one_observation_per_action(tmp_path):
    with Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence='MKWAA', molecule='protein')
        directory = tmp_path / 'run'
        directory.mkdir()
        backend = DurableExecutionStore(directory / 'episode-execution')
        target = durable_target(tmp_path, store, backend)
        scope = target['child']['scope']
        holder, controllers, credited = {}, [], []

        class PublicReader:
            def read_progress(self, reference, scope):
                return holder['workflow'].progress_provider.read_progress(reference, scope)

        credit = ProgressInformationCredit(PublicReader(), information_unit=.5)

        def bound_credit(context, receiver_selection):
            before = store.db.total_changes
            view = credit(context, receiver_selection)
            assert store.db.total_changes == before
            credited.append((receiver_selection, view))
            return view

        def controller(path, initial):
            value = FixtureController(str(path), initial, 2)
            controllers.append(value)
            return value

        observe = {'selection': {'kind': 'tool', 'tool': 'progress.observe',
            'arguments': {'requested_fields': ['execution_status', 'committed_record_refs']}},
            'report_update': {}}
        report_schema = obj({'progress': {'type': 'array', 'items': {'type': 'string',
            'format': 'reference', 'x-reference-namespace': 'episode_progress'},
            'x-source': 'monitoring_progress_refs'}})

        def publish_and_observe(_):
            source = store._caller_source({'fixture': 'actually_committed'}, 'fixture')
            holder['workflow'].progress_provider.expose(target['handle'],
                operation_key='fixture-publication', committed_record_refs=[source['id']])
            return observe

        provider = ScriptedProvider([])
        workflow = Workflow(store, ToolRegistry(store), provider, directory, target['run_id'],
            controller, lambda store, scope: 0,
            episode_binding_descriptors=[MonitorEpisodes(None).as_record()],
            role_credit_bindings={'monitor': {'definition': credit.as_record(), 'project': bound_credit}})
        holder['workflow'] = workflow
        baseline = workflow.progress_provider.observe(target['handle'], ['execution_status'], scope)
        provider.script = iter([
            {'selection': {'kind': 'episode_child', 'role': 'monitor',
                'assignment': assignment(target['handle'], known=[baseline['progress_ref']],
                    fields=['execution_status', 'committed_record_refs'], permitted=['source']),
                'goal': 'Investigate which exposed fixture information is useful', 'scope': scope,
                'purpose': 'Return exact received progress references',
                'schema_json': json.dumps(report_schema), 'initial_report_json': '{}'}, 'report_update': {}},
            observe, publish_and_observe,
            {'selection': {'kind': 'tool', 'tool': 'episode.history',
                'arguments': {'view': 'records', 'decision_indices': [0]}}, 'report_update': {}}])
        root = workflow.build('annotation', 'root', 'Investigate the fixture question', scope)
        record = asyncio.run(root.run_async(workflow.context))
        asyncio.run(root.build_result(record))

        assert [value.scores for value in controllers] == [[0, 0], [0, .5]]
        assert all(view['credit'] == view['monitoring_information_credit'] for _, view in credited)
        assert all(view['monitoring_information_binding'] == credit.as_record() for _, view in credited)
        assert credited[-1][1]['newly_informative_received_snapshot_count'] == 1
        assert all(item['run_id'] == target['run_id'] for item, _ in credited)
        assert workflow.receipts is None
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 4
        assert not store.list('assessment') and not store.list('observation')
        returned = workflow.progress_provider.received_progress_refs(root.source.episode_id)
        assert baseline['progress_ref'] in returned and len(returned) == 2
