"""Original/received notification metadata, with no native execution or model.

The Store and journal are real. Narrow registry/backend fixtures make private
history traversal, status polling, registration and export unavailable.
"""
from copy import deepcopy
from dataclasses import replace
import json
import sqlite3
from types import SimpleNamespace

import pytest

from method_loop import EpisodeGoal
from method_loop.durable import content_digest, native_target_descriptor, native_target_handle
from method_loop.identities import EpisodeRef
from gene_annotation_episode.communication import ReportBoundaryError, validate_closed_schema, validate_form
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.native_event_information import (NativeEventInformation,
    report_sources, validate_target_view)
from gene_annotation_episode.resource_records import LAUNCH_VERSION, RESULTS_VERSION
from gene_annotation_episode.state import Store


def encoded(value):
    return json.dumps(value, allow_nan=False)


class Backend:
    def __init__(self, root_directory):
        self.root_directory = root_directory
        self.registrations = {}

    def native_target(self, handle):
        return deepcopy(self.registrations[handle])


class Jobs:
    def __init__(self, backend):
        self.backend = backend
        self.config = {'registry_ref': 'execution_registry_fixture',
            'job_limits': {'memory_bytes': 2048, 'scratch_bytes': 1024, 'wall_seconds': None}}
        self.rows, self.targets = {}, {}

    def _row(self, job_ref):
        if job_ref not in self.rows:
            raise ValueError('job_not_registered_here')
        return deepcopy(self.rows[job_ref])

    def resolve(self, value, namespace):
        return namespace == 'homology_job' and value in self.rows

    def native_event_targets(self, job_ref):
        target = self.targets.get(job_ref)
        return ([deepcopy(target)] if target is not None
            and target['handle'] in self.backend.registrations else [])

    def native_event_binding(self, job_ref):
        target = self.targets.get(job_ref)
        if target is None:
            return None
        registration = self.backend.registrations.get(target['handle'])
        if registration is None:
            return None
        value = {'version': 'native_event_binding_v1',
            'execution_directory': str(self.backend.root_directory), **{key: registration[key]
                for key in ('run_id', 'owner_episode_id', 'job_ref', 'registry_ref', 'resource_id')}}
        return SimpleNamespace(as_record=lambda: deepcopy(value))


class Case:
    def __init__(self, tmp_path):
        self.store = Store(tmp_path / 'state')
        self.journal = Journal(self.store, 'native-visibility-fixture')
        target = tmp_path / 'target.faa'
        target.write_text('>one\nMKWAA\n>two\nMKEEE\n')
        problem = self.store.create_problem(target, molecule='protein')
        self.query, self.foreign_query = problem['subject_refs']
        self.scope = {'subject_refs': [self.query]}
        self.backend = Backend(tmp_path / 'executions')
        self.jobs = Jobs(self.backend)
        self.reader = NativeEventInformation(self.store, self.journal, self.backend,
            jobs=self.jobs, resource_id='local-fixture')
        self.root = self.context('annotation', 'root')
        self.job = self.add_job('own', self.query, 'MKWAA')
        self.other_job = self.add_job('other', self.query, 'MKWAA')
        self.foreign_job = self.add_job('foreign', self.foreign_query, 'MKEEE')
        self.launch = self.context('job_launch', 'launch', parent=self.root,
            message={'job_assignment': self.assigned(self.job)})

    def add_job(self, name, query, sequence):
        job = 'homology_job_' + name
        self.jobs.rows[job] = {'job_ref': job, 'query_ref': query, 'cpu': 1,
            'search_mode': 'native_defaults', 'query_fasta': '>query\n' + sequence + '\n'}
        return job

    def assigned(self, job):
        row = self.jobs.rows[job]
        return {key: row[key] for key in ('job_ref', 'query_ref', 'cpu')}

    def context(self, role, key, *, parent=None, assignment=None, message=None, saved=True):
        path = (() if parent is None else parent.path) + ((role, key),)
        if parent is None:
            goal = EpisodeGoal.root(objective='Fixture target', result_contract={'role': role})
        else:
            goal = EpisodeGoal.child(EpisodeGoal.from_record(parent.as_record()['request']['goal']),
                objective='Fixture child', result_contract={'role': role})
        assignment = {} if assignment is None else assignment
        message = {'scope': self.scope, **({} if message is None else message)}
        if assignment:
            message['episode_assignment'] = assignment
        request = {'goal': goal.as_record(), 'message': message, 'report_contract': None}
        context = BindingContext(self.journal.run_id, EpisodeRef(self.journal.run_id, path).episode_id,
            role, path, self.scope, assignment, request)
        if saved:
            self.save(context)
        return context

    def save(self, context):
        self.journal.save('runtime_episodes', {'episode_id': context.episode_id,
            'path': encoded(context.as_record()['path']), 'request': encoded(context.as_record()['request']),
            'initial_credit': 0, 'state': 'active', 'completion': None, 'archive': None})

    def register(self, job=None, *, run_id=None, resource_id=None, registry_ref=None):
        job = self.job if job is None else job
        native = {'kind': 'systemd_user_service', 'unit': job + '.service', 'request_sha256': 'a' * 64}
        registration = {'version': 'native_event_registration_v1', 'handle': native_target_handle(native),
            'run_id': self.journal.run_id if run_id is None else run_id,
            'owner_episode_id': self.launch.episode_id, 'job_ref': job,
            'registry_ref': self.jobs.config['registry_ref'] if registry_ref is None else registry_ref,
            'resource_id': 'local-fixture' if resource_id is None else resource_id,
            'native_identity': native}
        self.backend.registrations[registration['handle']] = registration
        target = native_target_descriptor(registration)
        self.jobs.targets[job] = target
        return target

    def source(self, target, cursor=0):
        return {'target': deepcopy(target), 'after_cursor': cursor}

    def selected(self, context, target, *, index=0, status='completed', tool='homology.submit', arguments=None):
        self.journal.save('runtime_actions', {'episode_id': context.episode_id, 'decision_index': index,
            'action': encoded({'kind': 'tool', 'tool': tool, 'arguments': {} if arguments is None else arguments}),
            'result': encoded({'status': status, 'result': None, 'native_event_targets': [target]}), 'credit': None})

    def attempt(self, parent, rows, *, field='parent.chosen', index=0, source=True, failure=None):
        declared = {'type': 'array', **({'x-source': 'native_event_targets'} if source else {})}
        self.journal.save('runtime_report_attempts', {'parent_episode_id': parent.episode_id,
            'child_episode_id': self.launch.episode_id, 'decision_index': index,
            'delivery_ref': 'delivery_' + str(index),
            'contract': encoded({'measurements': {'schema': {'properties': {field: declared}}}}),
            'form': encoded({field: rows}), 'failure': None if failure is None else encoded(failure)})

    def wait(self, context, target, *, index=1, cursor=7, selected_cursor=0, complete=True):
        self.store.db.execute('''CREATE TABLE IF NOT EXISTS episode_waits (
            run_id TEXT, wait_id TEXT, parent_episode_id TEXT, original_decision_index INTEGER,
            request_sha256 TEXT, request TEXT, wake TEXT, outcome TEXT)''')
        handle = target['handle']
        condition = {'version': 'event_condition_v1', 'events': [
            {'handle': handle, 'event': 'state_changed', 'after_cursor': selected_cursor}], 'reconsider_at': None}
        request = {'version': 'wait_request_v1', 'wait_id': 'wait_' + str(index),
            'parent_episode_id': context.episode_id, 'original_decision_index': index,
            'condition': condition, 'estimate_snapshot': {}}
        wake = {'version': 'event_wake_v1', 'reason': 'state_changed', 'reconsider_at': None,
            'observed_at': '2026-10-21T00:00:01+00:00', 'events': [
                {'handle': handle, 'event': 'state_changed', 'cursor': cursor,
                    'record_ref': 'native_event_record_' + 'b' * 24}]}
        outcome = {'version': 'wait_outcome_v1', 'wait_id': request['wait_id'],
            'condition_sha256': content_digest(condition), 'started_at': '2026-10-21T00:00:00+00:00',
            'woke_at': '2026-10-21T00:00:01+00:00', 'measured_duration_seconds': 1,
            'duration_measure': 'measured_wait_intervals', 'wake_reason': 'state_changed',
            'trigger': {'handle': handle, 'cursor': cursor}, 'unmeasured_interruption': False}
        self.store.db.execute('INSERT INTO episode_waits VALUES(?,?,?,?,?,?,?,?)',
            (context.run_id, request['wait_id'], context.episode_id, index,
                content_digest(request), encoded(request), encoded(wake), encoded(outcome)))
        self.journal.save('runtime_actions', {'episode_id': context.episode_id, 'decision_index': index,
            'action': encoded({'kind': 'wait', 'condition': condition}), 'result': encoded({
                'status': 'completed', 'result': outcome, 'wait_outcome': outcome}) if complete else None,
            'credit': None})
        return condition


@pytest.fixture
def case(tmp_path):
    case = Case(tmp_path)
    try:
        yield case
    finally:
        case.store.close()


def test_original_job_is_visible_at_zero_and_registration_never_grants_root_visibility(case):
    assert case.reader.read(case.launch) == []
    target = case.register()
    assert case.reader.read(case.launch) == [case.source(target)]
    assert case.reader.read(case.root) == []
    result = case.reader.read(case.launch)
    result[0]['target']['resource_id'] = 'changed'
    assert case.reader.facts(case.launch) == {'native_event_targets': [case.source(target)]}
    del case.backend.registrations[target['handle']]
    assert case.reader.read(case.launch) == []


@pytest.mark.parametrize('status', ['completed', 'failed'])
def test_actual_submit_and_resume_keep_partial_identity_without_success_claim(case, status):
    target = case.register()
    case.selected(case.launch, target, status=status)
    case.selected(case.launch, target, status=status, tool='homology.resume_start', index=1)
    case.jobs.targets.clear()  # Released original files do not erase recorded identity.
    assert case.reader.read(case.launch) == [case.source(target)]
    case.selected(case.root, target, index=2)
    with pytest.raises(ValueError, match='assignment_conflict'):
        case.reader.read(case.root)


def test_received_only_original_top_level_source_fields_and_no_private_form_discovery(case):
    target, other = case.register(), case.register(case.other_job)
    case.attempt(case.root, [case.source(target, 4)])
    case.attempt(case.root, [case.source(other, 8)], source=False, index=1, field='native_event_targets')
    case.attempt(case.root, [case.source(other, 9)], failure={'code': 'failed'}, index=2)
    case.journal.save('runtime_forms', {'episode_id': case.launch.episode_id,
        'facts': 'private non-JSON must never be loaded', 'form': None})
    assert case.reader.read(case.root) == [case.source(target, 4)]
    case.attempt(case.root, [case.source(target, 7)], index=3)
    assert case.reader.read(case.root) == [case.source(target, 7)]
    assert not case.reader.resolve(case.root, other['handle'], 'native_event_target')


def test_received_target_survives_original_control_file_cleanup_and_closed_history(case):
    target = case.register()
    case.attempt(case.root, [case.source(target, 4)])
    case.jobs.targets.clear()
    case.store.db.execute("UPDATE runtime_episodes SET state='yielded',archive='private archive' WHERE episode_id=?",
        (case.root.episode_id,))
    assert case.reader.read(case.root) == [case.source(target, 4)]
    assert case.reader.read(case.launch) == []


def test_nested_job_mentions_and_other_selected_tools_do_not_grant_visibility(case):
    target = case.register()
    root = case.context('annotation', 'mentions', assignment={
        'context': {'arbitrary': {'job_ref': case.job}}})
    case.selected(root, target, tool='fixture.unrelated')
    assert case.reader.read(root) == []
    case.attempt(root, {'nested': [case.source(target)]})
    with pytest.raises(ValueError, match='received_targets_invalid'):
        case.reader.read(root)


def test_legacy_supplied_handoff_and_resource_selection_must_agree(case):
    case.register()
    assigned = case.assigned(case.job)
    assigned['handoff'] = {'job_ref': case.other_job, 'registry_ref': case.jobs.config['registry_ref'],
        'backend': 'single_query_phmmer_jobs_v2', 'status_interface': 'homology.status.v1',
        'progress_interface': 'homology.progress.v1', 'results_interface': 'homology.results.v1'}
    with pytest.raises(ValueError, match='assignment_conflict'):
        case.reader.read(case.context('job_monitor', 'wrong-handoff', parent=case.root,
            message={'job_assignment': assigned}))


def test_present_reservation_cannot_replace_original_binding_or_identity(case, tmp_path):
    target = case.register()
    case.attempt(case.root, [case.source(target)])
    original = case.jobs.native_event_binding
    binding = original(case.job).as_record()
    binding['owner_episode_id'] = 'different-owner'
    case.jobs.native_event_binding = lambda ref: SimpleNamespace(as_record=lambda: binding)
    with pytest.raises(ValueError, match='target_identity_conflict'):
        case.reader.read(case.root)
    case.jobs.native_event_binding = original
    case.jobs.native_event_targets = lambda ref: []
    with pytest.raises(ValueError, match='original_target_unavailable'):
        case.reader.read(case.root)
    case.jobs.native_event_binding = lambda ref: None
    case.jobs.directory = tmp_path / 'jobs'
    directory = case.jobs.directory / case.job
    directory.mkdir(parents=True)
    (directory / 'native.handle.json').write_text('{}')
    with pytest.raises(ValueError, match='target_identity_conflict'):
        case.reader.read(case.root)


def test_completed_wait_uses_exact_received_trigger_not_selected_threshold_or_backend_head(case):
    target = case.register()
    condition = case.wait(case.launch, target, cursor=7, selected_cursor=3)
    assert case.reader.read(case.launch) == [case.source(target, 7)]
    arbitrary = deepcopy(condition)
    arbitrary['events'][0]['after_cursor'] = 1000000
    assert case.reader.validate_wait(case.launch, arbitrary) == arbitrary
    assert case.reader.read(case.launch)[0]['after_cursor'] == 7
    case.wait(case.launch, target, index=2, cursor=20, complete=False)
    assert case.reader.read(case.launch)[0]['after_cursor'] == 7
    case.store.db.execute("UPDATE runtime_actions SET result=json_set(result,'$.wait_outcome.trigger.cursor',99) WHERE decision_index=1")
    with pytest.raises(ValueError, match='wait_identity_conflict'):
        case.reader.read(case.launch)


@pytest.mark.parametrize('namespace,field', [('native_event_target', 'handle'), ('homology_job', 'job_ref'),
    ('execution_registry', 'registry_ref'), ('resource_binding', 'resource_id')])
def test_related_references_require_actual_context_visibility(case, namespace, field):
    target = case.register()
    assert case.reader.resolve(case.launch, target[field], namespace)
    assert not case.reader.resolve(case.root, target[field], namespace)
    assert case.reader.resolve(case.launch, target[field], None)


@pytest.mark.parametrize('change', ['run', 'episode', 'path', 'scope', 'assignment', 'request', 'goal'])
def test_full_original_context_is_authenticated(case, change):
    context = case.launch
    request = context.as_record()['request']
    if change == 'run':
        context = replace(context, run_id='foreign')
    elif change == 'episode':
        context = replace(context, episode_id=case.root.episode_id)
    elif change == 'path':
        context = replace(context, path=case.root.path + (('job_launch', 'other'),))
    elif change == 'scope':
        context = replace(context, scope={'subject_refs': [case.foreign_query]})
    elif change == 'assignment':
        context = replace(context, assignment={'forged': True})
    elif change == 'goal':
        request['goal']['objective'] = 'forged'
        context = replace(context, request=request)
    else:
        request['message']['extra'] = 'forged'
        context = replace(context, request=request)
    with pytest.raises(ValueError):
        case.reader.read(context)


def test_exact_unsaved_child_can_receive_original_assignment_but_unsaved_root_cannot(case):
    target = case.register()
    child = case.context('job_monitor', 'unsaved', parent=case.root, saved=False,
        message={'job_assignment': case.assigned(case.job)})
    assert case.reader.read(child) == [case.source(target)]
    root = case.context('annotation', 'unsaved-root', saved=False)
    with pytest.raises(ValueError, match='saved_owner_required'):
        case.reader.read(root)
    request = child.as_record()['request']
    request['goal']['parent_goal_id'] = 'goal_foreign'
    with pytest.raises(ValueError):
        case.reader.read(replace(child, request=request))


@pytest.mark.parametrize('change', ['run', 'resource', 'registry', 'query_bytes', 'foreign_scope'])
def test_registered_descriptor_must_match_run_resource_registry_and_actual_query(case, change):
    target = case.register(**({'run_id': 'foreign'} if change == 'run' else
        {'resource_id': 'foreign'} if change == 'resource' else
        {'registry_ref': 'foreign'} if change == 'registry' else {}))
    if change == 'query_bytes':
        case.jobs.rows[case.job]['query_fasta'] = '>query\nALTERED\n'
    if change == 'foreign_scope':
        target = case.register(case.foreign_job)
    case.attempt(case.root, [case.source(target)])
    with pytest.raises(ValueError):
        case.reader.read(case.root)


def test_resource_launch_results_and_job_monitor_paths_match_original_job_and_selection(case):
    target = case.register()
    selection = {'resource_id': 'local-fixture', 'kind': 'local', 'allocation': {
        'cpu': 1, **case.jobs.config['job_limits']}, 'capability_binding_ref': case.jobs.config['registry_ref']}
    assignment = {'version': LAUNCH_VERSION, 'adapter_assignment': case.assigned(case.job),
        'job_request': {'existing_job_ref': case.job}, 'resource_selection': selection, 'constraints': {}}
    launch = case.context('launch_local', 'local', parent=case.root, assignment=assignment)
    assert case.reader.read(launch) == [case.source(target)]
    handoff = {'version': 'execution_handoff_v1', 'execution_handle': case.job,
        'resource_selection': selection, 'submitted_input_versions': [],
        'monitoring': {'provider_id': 'local-fixture', 'target_handle': case.job, 'contract_ref': 'homology.status.v1'},
        'results': {'provider_id': 'local-fixture', 'target_handle': case.job, 'contract_ref': 'homology.results.v1'},
        'checked_at': '2026-10-21T00:00:00+00:00', 'check_record_refs': [], 'state': 'usable', 'failure': None}
    results = case.context('results', 'results', parent=case.root, assignment={
        'version': RESULTS_VERSION, 'handoff': handoff, 'adapter_assignment': case.assigned(case.job)})
    assert case.reader.read(results) == [case.source(target)]
    monitor = case.context('monitor', 'monitor', parent=case.root, assignment={
        'version': 'monitor_assignment_v1', 'target_handle': case.job})
    assert case.reader.read(monitor) == [case.source(target)]
    episode_monitor = case.context('monitor', 'episode', parent=case.root, assignment={
        'version': 'monitor_assignment_v1', 'target_handle': 'episode_handle_fixture'})
    assert case.reader.read(episode_monitor) == []
    changed = deepcopy(assignment)
    changed['job_request']['existing_job_ref'] = case.other_job
    with pytest.raises(ValueError, match='assignment_conflict'):
        case.reader.read(case.context('launch_local', 'bad', parent=case.root, assignment=changed))


def test_wait_scope_and_native_event_kind_are_explicit_and_arbitrary_cursor_is_allowed(case):
    target = case.register()
    condition = {'version': 'event_condition_v1', 'events': [{
        'handle': target['handle'], 'event': 'state_changed', 'after_cursor': 123}], 'reconsider_at': None}
    assert case.reader.validate_wait(case.launch, condition) == condition
    with pytest.raises(ValueError, match='not_visible'):
        case.reader.validate_wait(case.root, condition)
    for event in ('returned', 'progress_committed'):
        changed = deepcopy(condition)
        changed['events'][0]['event'] = event
        with pytest.raises(ValueError, match='unsupported_event'):
            case.reader.validate_wait(case.launch, changed)
    condition['events'][0]['handle'] = 'ordinary_episode_handle'
    assert case.reader.validate_wait(case.root, condition) == condition


def test_closed_source_schema_and_exact_received_rows_validate_without_new_cursor_claim(case):
    target = case.register()
    case.attempt(case.root, [case.source(target, 4)])
    case.attempt(case.root, [case.source(target, 8)], index=1)
    schema = {'type': 'object', 'properties': {'chosen': report_sources()['native_event_targets']['report_schema']},
        'required': ['chosen'], 'additionalProperties': False}
    validate_closed_schema(schema)
    form = {'chosen': [case.source(target, 8)]}
    validate_form(form, schema, lambda ref, ns: case.reader.resolve(case.root, ref, ns))
    case.reader.validate_report(case.root, form, schema)
    case.reader.validate_report(case.root, {'chosen': [case.source(target, 4)]}, schema)
    for mutation in (lambda row: row.update(after_cursor=6),
            lambda row: row['target'].update(resource_id='forged'),
            lambda row: row['target'].update(cause='ready')):
        forged = deepcopy(form)
        mutation(forged['chosen'][0])
        with pytest.raises(ReportBoundaryError):
            case.reader.validate_report(case.root, forged, schema)


@pytest.mark.parametrize('value', [None, {}, {'target': {}, 'after_cursor': 0},
    {'target': {}, 'after_cursor': True}, {'target': {}, 'after_cursor': -1}])
def test_target_views_are_closed_and_nonnegative(value):
    with pytest.raises(ValueError):
        validate_target_view(value)


def test_construction_and_reads_are_select_only_and_never_load_private_histories(case):
    target = case.register()
    case.attempt(case.root, [case.source(target, 3)])
    case.wait(case.launch, target)
    statements = []
    denied = {sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE,
        sqlite3.SQLITE_CREATE_TABLE, sqlite3.SQLITE_ALTER_TABLE, sqlite3.SQLITE_DROP_TABLE,
        sqlite3.SQLITE_PRAGMA, sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH}

    def authorize(action, table, column, database, trigger):
        if action in denied or action == sqlite3.SQLITE_READ and table in {
                'runtime_forms', 'runtime_model_calls', 'runtime_observations', 'runtime_return_admissions'}:
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    case.store.db.execute('PRAGMA query_only=ON')
    case.store.db.set_authorizer(authorize)
    case.store.db.set_trace_callback(statements.append)
    reader = NativeEventInformation(case.store, case.journal, case.backend, jobs=case.jobs, resource_id='local-fixture')
    assert statements == []
    assert reader.read(case.root) == [case.source(target, 3)]
    assert reader.read(case.launch) == [case.source(target, 7)]
    assert statements and all(statement.lstrip().upper().startswith(('SELECT', 'BEGIN', 'COMMIT'))
        for statement in statements)
    assert not any('SELECT * FROM RUNTIME_' in statement.upper() for statement in statements)
