"""CP6: actual tiny native resource work, explicit engineering decisions/units.

No configured-model investigation, production policy, detached worker or new
timing source. Store-only provenance variations reuse the original export.
"""
import asyncio
from contextlib import contextmanager
from copy import deepcopy
import json
import sqlite3
from types import SimpleNamespace

import pytest

from gene_annotation_episode.homology_episodes import obj
from gene_annotation_episode.monitoring_credit import MonitoringInformationCredit
from gene_annotation_episode.native_lifecycle import cancel
from gene_annotation_episode.native_timing_information import NativeTimingInformation, read_measurement
from gene_annotation_episode.resource_episodes import LAUNCH_VERSION
from gene_annotation_episode.resource_service_setup import bind_resource_services
from gene_annotation_episode.runtime import ReleasingContext, TypedReportContract, Workflow
from test_homology_episode_runtime import Provider, action, prepared
from test_homology_jobs import wait_terminal
from test_runtime import FixtureController


UNIT = 7  # Explicit engineering fixture, never a production default.


def forbid_native_reads(monkeypatch, jobs):
    def forbidden(*args, **kwargs):
        pytest.fail('Timing receipt/recovery must use original saved work')
    for name in ('check_handoff', 'receive', 'status', 'handoff', '_handle',
                 'submit', 'sample', 'recover_statistics'):
        monkeypatch.setattr(jobs, name, forbidden)


def fixture_run(directory, *, fact='job_checked_status', history_available=True,
                interrupt=False, missing_assignment=False):
    store, tools, query, scope, jobs, homology = prepared(directory, statistics=True,
        monitoring_credit=MonitoringInformationCredit(information_unit=UNIT, include_handoff_checks=True))
    if not history_available:
        homology.statistics.history_path.unlink()
    controllers = {}

    def factory(path, initial):
        controller = FixtureController(str(path), initial,
            {'annotation': 1, 'launch': 2, 'launch_local': 5}[path[-1][0]])
        controllers[path] = controller
        return controller

    def services(store, **kwargs):
        return bind_resource_services(store, **kwargs, handoff_unit=2.75,
            acquired_record_unit=0.125)

    timing = NativeTimingInformation(UNIT)
    provider = Provider([])
    workflow = Workflow(store, tools, provider, directory/'run', 'resource-timing-fixture',
        controller_factory=factory, project_credit=lambda *_: 0, job_episodes=homology,
        episode_service_factory=services, episode_service_binding={'kind': 'CP6_fixture_only'},
        episode_record_receipts=True, initial_known_record_refs=[], native_timing_information=timing)
    owner = workflow.build('annotation', 'unexecuted_owner', 'Receive the original fixture form', scope)
    launch_assignment = {'version': LAUNCH_VERSION, 'job_request': {'query_ref': query, 'cpu': 1},
        'immutable_input_versions': [{'reference': query, 'version': None, 'content_sha256': None}],
        'constraints': {'allowed_kinds': ['local'], 'cpu': 1}, 'resource_selection': None,
        'software_knowledge_refs': [], 'resource_knowledge_refs': []}
    parent_schema = obj({'measurements': timing.report_sources()['native_execution_measurements']['report_schema']})
    launch = workflow.build('launch', 'launch', 'Investigate the assigned fixture work', scope,
        parent=owner.goal, parent_path=owner.source.path,
        contract=TypedReportContract('Return the original received measurements', parent_schema,
            workflow.resolver(scope, grain='launch')), initial={}, episode_assignment=launch_assignment)
    adapter, = workflow.episode_bindings.for_role('launch_local').adapters.values()
    fields = {'finding_state': {'type': 'string', 'enum': ['unknown', 'checked']}}
    if fact is not None:
        fields['requested_timing'] = homology.fact_sources('job_launch')[fact]['report_schema']
    child_schema = obj(fields)
    selection = {'selection': {'kind': 'episode_child', 'role': 'launch_local',
        'goal': 'Establish the actual original receiving interface', 'scope': scope,
        'purpose': 'Return only the parent requested original facts',
        'schema_json': json.dumps(child_schema), 'initial_report_json': '{"finding_state":"unknown"}',
        'assignment': {**deepcopy(launch_assignment), 'resource_selection': adapter._selection(1)}},
        'report_update': {}}

    def completed_check(context):
        assigned = context['working_state']['assignment']['adapter_assignment']
        wait_terminal(jobs, assigned['job_ref'])
        checked = action('homology.check_handoff')
        checked['report_update'] = {'finding_state': 'checked'}
        return checked

    def redelivery(context):
        returned, = context['child_reports']
        assert returned['finding_state'] == 'checked'
        return {'selection': {'kind': 'redeliver_report',
            'delivery_ref': context['report_deliveries'][0]['delivery_ref'],
            'purpose': 'Receive the same original facts again',
            'schema_json': json.dumps(child_schema)}, 'report_update': {}}

    boundary = ReleasingContext.from_commission(tree=workflow.tree, run_id=workflow.run_id,
        parent_path=owner.source.path, parent_goal_id=owner.goal.goal_id,
        child_goal_id=launch.goal.goal_id, grain='launch', key=launch.key)
    original_consumer = homology.received_timing_records

    def omit_carrier(store, value, schema, scope):
        child = store.db.execute("SELECT episode_id,request FROM runtime_episodes "
            "WHERE json_extract(path,'$[#-1][0]')='launch_local'").fetchone()
        saved = json.loads(child['request'])
        del saved['message']['episode_assignment']['adapter_assignment']
        store.db.execute('UPDATE runtime_episodes SET request=? WHERE episode_id=?',
            (json.dumps(saved), child['episode_id']))
        try:
            return original_consumer(store, value, schema, scope)
        finally:
            store.db.execute('UPDATE runtime_episodes SET request=? WHERE episode_id=?',
                (child['request'], child['episode_id']))

    if missing_assignment:
        homology.received_timing_records = omit_carrier
    operations = [action(name) for name in ('homology.environment',
        'homology.configure', 'homology.stage', 'homology.submit')]
    for operation in operations:
        operation['report_update'] = {'finding_state': 'unknown'}
    prefix = [selection, *operations, completed_check]
    suffix = [redelivery, action('episode.monitoring_information', {'offset': 0, 'limit': 5})]
    provider.script = iter(prefix + ([asyncio.CancelledError()] if interrupt else suffix))
    if interrupt:
        with pytest.raises(asyncio.CancelledError):
            asyncio.run(launch.run_async(boundary))
        actions_before = [tuple(row) for row in store.db.execute('SELECT * FROM runtime_actions ORDER BY rowid')]
        observations_before = [tuple(row) for row in store.db.execute('SELECT * FROM runtime_observations ORDER BY rowid')]
        provider.script = iter(suffix)
        launch = workflow.build('launch', 'launch', 'Investigate the assigned fixture work', scope,
            parent=owner.goal, parent_path=owner.source.path,
            contract=TypedReportContract('Return the original received measurements', parent_schema,
                workflow.resolver(scope, grain='launch')), initial={}, episode_assignment=launch_assignment)
        boundary = ReleasingContext.from_commission(tree=workflow.tree, run_id=workflow.run_id,
            parent_path=owner.source.path, parent_goal_id=owner.goal.goal_id,
            child_goal_id=launch.goal.goal_id, grain='launch', key=launch.key)
        with pytest.MonkeyPatch.context() as patched:
            forbid_native_reads(patched, jobs)
            record = asyncio.run(launch.run_async(boundary))
        assert [tuple(row) for row in store.db.execute('SELECT * FROM runtime_actions ORDER BY rowid LIMIT ?',
            (len(actions_before),))] == actions_before
        assert [tuple(row) for row in store.db.execute('SELECT * FROM runtime_observations ORDER BY rowid LIMIT ?',
            (len(observations_before),))] == observations_before
    else:
        record = asyncio.run(launch.run_async(boundary))
    asyncio.run(launch.build_result(record))
    child = store.db.execute("SELECT * FROM runtime_episodes "
        "WHERE json_extract(path,'$[#-1][0]')='launch_local'").fetchone()
    child_form = json.loads(workflow.journal.row('runtime_forms', child['episode_id'])['form'])
    return SimpleNamespace(store=store, jobs=jobs, homology=homology, workflow=workflow,
        timing=timing, query=query, scope=scope, launch=launch, record=record, controllers=controllers,
        child_id=child['episode_id'], child_form=child_form, child_schema=child_schema,
        directory=directory)


def close_fixture(r):
    for row in r.jobs.db.execute('SELECT job_ref FROM orders'):
        handle = r.jobs._handle(row[0])
        if handle.path.exists():
            cancel(handle)
    r.jobs.close()
    r.store.close()


@pytest.fixture(scope='module')
def returned_resource(tmp_path_factory):
    r = fixture_run(tmp_path_factory.mktemp('resource-returned-timing'))
    try:
        yield r
    finally:
        close_fixture(r)


def snapshots(r):
    return {table: [tuple(row) for row in r.store.db.execute(f'SELECT * FROM {table} ORDER BY rowid')]
        for table in ('runtime_actions', 'runtime_observations', 'runtime_estimation_contexts')}


def test_real_resource_child_original_form_one_measurement_once(returned_resource, monkeypatch):
    r = returned_resource
    parent_id = r.launch.source.episode_id
    assert r.record.units_consumed == 2
    assert r.store.db.execute('SELECT count(*) FROM runtime_observations WHERE episode_id=?',
        (parent_id,)).fetchone()[0] == 2
    assert r.store.db.execute('SELECT count(*) FROM runtime_observations WHERE episode_id=?',
        (r.child_id,)).fetchone()[0] == 5
    assert r.store.count('native_execution') == 1
    assert r.jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 1
    assert r.jobs.db.execute('SELECT sum(submission_requested) FROM orders').fetchone()[0] == 1
    request = json.loads(r.workflow.journal.row('runtime_episodes', r.child_id)['request'])
    assert 'job_assignment' not in request['message']
    assert request['message']['episode_assignment']['adapter_assignment']['query_ref'] == r.query
    saved = json.loads(r.workflow.journal.row('runtime_actions', r.child_id, 4)['result'])
    export, = saved['execution_statistics_export']
    native, = r.store.list('native_execution')
    assert read_measurement(r.store, native['id']).as_record() == export['measurement']
    assert native['operands'] == [{'role': 'query', 'subject_ref': r.query}]
    assert export['measurement']['statistic']['elapsed_seconds'] == r.child_form['requested_timing']['elapsed_seconds']
    assert r.workflow.source_credit_view(r.launch.source)['credit'] == 0
    assert r.workflow.source_credit_view(r.launch.source)['monitoring_information_credit'] == UNIT
    attempts = [json.loads(row[0]) for row in r.store.db.execute(
        'SELECT timing_receipts FROM runtime_report_attempts ORDER BY decision_index')]
    assert attempts == [attempts[0], attempts[0]]
    assert attempts[0]['native_execution_refs'] == [native['id']] and attempts[0]['issues'] == []
    assert r.store.count('assessment') == r.store.count('annotation') == 0
    with sqlite3.connect(r.homology.statistics.history_path) as db:
        statistics_before = db.execute('SELECT * FROM run_statistics').fetchall()
        assert len(statistics_before) == 1
    before = snapshots(r)
    with monkeypatch.context() as patched:
        forbid_native_reads(patched, r.jobs)
        # Original receipt projection is reused even if the normalizer becomes
        # unavailable after the delivery transaction committed.
        patched.setattr(r.homology, 'received_timing_records', lambda *_: pytest.fail('renormalized saved attempt'))
        r.workflow.receive_form(r.launch.source, r.child_form, r.child_schema, 0)
        r.workflow.receive_form(r.launch.source, r.child_form, r.child_schema, 1, redelivery=True)
    assert snapshots(r) == before
    assert r.store.count('native_execution') == 1
    with sqlite3.connect(r.homology.statistics.history_path) as db:
        assert db.execute('SELECT * FROM run_statistics').fetchall() == statistics_before


@contextmanager
def changed_source(r, change):
    original = r.workflow.journal.row('runtime_episodes', r.child_id)['request']
    request = json.loads(original)
    outcome_original = r.workflow.journal.row('runtime_actions', r.child_id, 4)['result']
    outcome = json.loads(outcome_original)
    change(request['message'], outcome)
    with r.store.transaction():
        r.store.db.execute('UPDATE runtime_episodes SET request=? WHERE episode_id=?',
            (json.dumps(request), r.child_id))
        r.store.db.execute('UPDATE runtime_actions SET result=? WHERE episode_id=? AND decision_index=4',
            (json.dumps(outcome), r.child_id))
    try:
        yield
    finally:
        with r.store.transaction():
            r.store.db.execute('UPDATE runtime_episodes SET request=? WHERE episode_id=?',
                (original, r.child_id))
            r.store.db.execute('UPDATE runtime_actions SET result=? WHERE episode_id=? AND decision_index=4',
                (outcome_original, r.child_id))


@pytest.mark.parametrize('changed', ['missing_carrier', 'malformed_carrier', 'query', 'cpu', 'job',
    'registry', 'scope', 'missing_measurement', 'measurement_cpu', 'measurement_identity', 'duration', 'both_conflict'])
def test_original_resource_provenance_is_required(returned_resource, monkeypatch, changed):
    r = returned_resource
    def alter(message, outcome):
        resource = message['episode_assignment']
        assignment = resource['adapter_assignment']
        if changed == 'missing_carrier':
            del resource['adapter_assignment']
        elif changed == 'malformed_carrier':
            resource['adapter_assignment'] = None
        elif changed in {'query', 'job'}:
            assignment[changed + '_ref'] = changed + '_unknown'
        elif changed == 'cpu':
            assignment['cpu'] = 2
        elif changed == 'registry':
            resource['resource_selection']['capability_binding_ref'] = 'execution_registry_unknown'
        elif changed == 'scope':
            message['scope'] = {'subject_refs': []}
        elif changed == 'missing_measurement':
            del outcome['execution_statistics_export'][0]['measurement']
        elif changed == 'measurement_cpu':
            outcome['execution_statistics_export'][0]['measurement']['execution_class']['cpu_threads'] = 2
        elif changed == 'measurement_identity':
            outcome['execution_statistics_export'][0]['measurement']['statistic']['attempt_sha256'] = 'a' * 64
        elif changed == 'duration':
            outcome['execution_statistics_export'][0]['measurement']['statistic']['elapsed_seconds'] += 1
        else:
            message['job_assignment'] = {**assignment, 'cpu': 2}
    before = snapshots(r)
    with changed_source(r, alter), monkeypatch.context() as patched:
        forbid_native_reads(patched, r.jobs)
        received = r.homology.received_timing_records(r.store, r.child_form, r.child_schema, r.scope)
        assert received['native_execution_refs'] == []
        issue, = received['issues']
        assert issue['source'] == 'job_checked_status' and issue['field'] == ['requested_timing']
        assert issue['code'] in {'measurement_not_recorded', 'measurement_record_invalid', 'measurement_status_mismatch'}
    assert snapshots(r) == before
    assert r.store.count('native_execution') == 1


def test_equal_carriers_and_requested_only_boundary(returned_resource, monkeypatch):
    r = returned_resource
    def both(message, _):
        message['job_assignment'] = deepcopy(message['episode_assignment']['adapter_assignment'])
    before = snapshots(r)
    with changed_source(r, both), monkeypatch.context() as patched:
        forbid_native_reads(patched, r.jobs)
        facts = json.loads(r.workflow.journal.row('runtime_forms', r.child_id)['facts'])
        twice = {**r.child_form, 'same_timing': facts['monitoring_findings']}
        schema = deepcopy(r.child_schema)
        schema['properties']['same_timing'] = r.homology.fact_sources('job_launch')['monitoring_findings']['report_schema']
        schema['required'].append('same_timing')
        received = r.homology.received_timing_records(r.store, twice, schema, r.scope)
        assert received['issues'] == [] and len(received['native_execution_refs']) == 1
        # Identical data with no requested timing source carries no duration.
        schema = deepcopy(r.child_schema)
        del schema['properties']['requested_timing']['x-source']
        assert r.homology.received_timing_records(r.store, r.child_form, schema, r.scope) == {
            'version': 'received_job_timing_receipts_v1', 'native_execution_refs': [], 'issues': []}
    assert snapshots(r) == before
    assert r.store.count('native_execution') == 1


@pytest.mark.parametrize('options,expected', [({'fact': None}, 0),
    ({'fact': 'monitoring_findings', 'history_available': False}, UNIT),
    ({'missing_assignment': True}, 0), ({'interrupt': True}, UNIT)])
def test_original_resource_form_exclusion_partial_return_and_recovery(tmp_path, options, expected):
    r = fixture_run(tmp_path, **options)
    try:
        assert r.workflow.source_credit_view(r.launch.source)['monitoring_information_credit'] == expected
        assert r.workflow.source_credit_view(r.launch.source)['credit'] == 0
        assert r.child_form['finding_state'] == 'checked'
        assert r.record.units_consumed == 2
        assert r.store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 7
        assert r.store.count('native_execution') == int(expected > 0)
        attempts = list(r.store.db.execute('SELECT failure,timing_receipts FROM runtime_report_attempts'))
        assert len(attempts) == 2 and all(row['failure'] is None for row in attempts)
        if options.get('missing_assignment'):
            assert all(json.loads(row['timing_receipts'])['issues'][0]['code'] == 'measurement_record_invalid'
                for row in attempts)
        if options.get('history_available') is False:
            assert not r.homology.statistics.history_path.exists()
        assert r.jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 1
    finally:
        close_fixture(r)
