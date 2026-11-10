"""Read-only native target visibility through original and received information.

A native event target is notification metadata, not an episode commission or a
scientific contribution. This adapter never registers, exports, polls or runs
native work, and never discovers relationships by walking a child history.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import json
import math
from pathlib import Path

from method_loop import EpisodeGoal
from method_loop.durable import (EventTargetError, canonical, content_digest, native_target_descriptor,
    validate_native_registration)
from method_loop.identities import EpisodeRef, normalize_structural_path

from .communication import ReportBoundaryError, plain
from .homology_jobs import HANDOFF_SCHEMA as LEGACY_HANDOFF_SCHEMA, normalize_query_fasta
from .materials import artifact_path
from .resource_records import HANDOFF_SCHEMA, LAUNCH_VERSION, RESULTS_VERSION, _validate
from .waiting import validate_condition, _validate_wake


SOURCE = 'native_event_targets'
NAMESPACES = frozenset({'native_event_target', 'homology_job', 'execution_registry', 'resource_binding'})
def _detached(value):
    return json.loads(canonical(plain(value)))


def _object(fields):
    return {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}


def _reference(namespace):
    return {'type': 'string', 'format': 'reference', 'x-reference-namespace': namespace}


TARGET_SCHEMA = _object({
    'version': {'type': 'string', 'const': 'native_event_target_v1'},
    'handle': _reference('native_event_target'),
    'job_ref': _reference('homology_job'),
    'registry_ref': _reference('execution_registry'),
    'resource_id': _reference('resource_binding'),
    'event': {'type': 'string', 'const': 'state_changed'},
    'cause': {'type': 'string', 'const': 'service_exit_receipt_committed'}})
VIEW_SCHEMA = _object({'target': TARGET_SCHEMA,
    'after_cursor': {'type': 'integer', 'minimum': 0}})


def _target(value):
    value = _detached(value)
    if (not isinstance(value, dict) or set(value) != set(TARGET_SCHEMA['properties'])
            or value['version'] != 'native_event_target_v1'
            or value['event'] != 'state_changed'
            or value['cause'] != 'service_exit_receipt_committed'
            or any(type(value[key]) is not str or not value[key] for key in
                ('handle', 'job_ref', 'registry_ref', 'resource_id'))
            or not value['handle'].startswith('native_event_target_')
            or len(value['handle']) != len('native_event_target_') + 24
            or any(c not in '0123456789abcdef' for c in value['handle'][-24:])):
        raise ValueError('native_event_target_invalid')
    return value


def validate_target_view(value):
    """Validate one complete finite row without giving it visibility."""
    value = _detached(value)
    if (not isinstance(value, dict) or set(value) != {'target', 'after_cursor'}
            or type(value['after_cursor']) is not int or value['after_cursor'] < 0):
        raise ValueError('native_event_target_view_invalid')
    value['target'] = _target(value['target'])
    return value


def report_sources():
    return {SOURCE: {'type': 'array', 'meaning': (
        'Native notification targets actually assigned or received by this episode, with '
        'the latest event cursor actually received. Registration and service exit receipts '
        'establish neither readiness, scientific success nor an episode return. This '
        'metadata creates no scientific credit or completed action.'),
        'report_schema': {'type': 'array', 'items': deepcopy(VIEW_SCHEMA), 'x-source': SOURCE}}}


class NativeEventInformation:
    def __init__(self, store, journal, execution_backend, *, jobs, resource_id):
        if journal.db is not store.db:
            raise ValueError('native_event_information_requires_same_store_connection')
        if (type(journal.run_id) is not str or not journal.run_id
                or type(resource_id) is not str or not resource_id):
            raise ValueError('native_event_information_explicit_binding_required')
        self.store, self.journal = store, journal
        self.backend, self.jobs, self.resource_id = execution_backend, jobs, resource_id

    @staticmethod
    def report_sources():
        return report_sources()

    def _saved(self, path, *, request=None):
        episode_id = EpisodeRef(self.journal.run_id, path).episode_id
        fields = "path, json_extract(request,'$.goal') AS goal, json_extract(request,'$.message.scope') AS scope"
        arguments = []
        if request is not None:
            # Compare every original request value in SQLite without loading
            # model contexts, private forms or even a second request body.
            fields += """, NOT EXISTS (SELECT fullkey,type,atom FROM json_tree(request)
                EXCEPT SELECT fullkey,type,atom FROM json_tree(?)) AND NOT EXISTS (
                SELECT fullkey,type,atom FROM json_tree(?)
                EXCEPT SELECT fullkey,type,atom FROM json_tree(request)) AS request_matches"""
            encoded = canonical(request)
            arguments.extend((encoded, encoded))
        row = self.store.db.execute('SELECT ' + fields +
            ' FROM runtime_episodes WHERE run_id=? AND episode_id=?',
            (*arguments, self.journal.run_id, episode_id)).fetchone()
        if row is None:
            return None
        if json.loads(row['path']) != plain(path) or request is not None and not row['request_matches']:
            raise ValueError('native_event_information_original_request_mismatch')
        return {'goal': json.loads(row['goal']), 'scope': json.loads(row['scope'])}

    def _authenticate(self, context):
        path = normalize_structural_path(context.path)
        request = _detached(context.request)
        scope, assignment = _detached(context.scope), _detached(context.assignment)
        message = request.get('message', {})
        if (context.run_id != self.journal.run_id or path[-1][0] != context.role
                or EpisodeRef(context.run_id, path).episode_id != context.episode_id
                or message.get('scope') != scope
                or message.get('episode_assignment', {}) != assignment):
            raise ValueError('native_event_information_context_mismatch')
        goal = EpisodeGoal.from_record(request['goal']).as_record()
        self.store.validate_scope(scope)
        saved = self._saved(path, request=request)
        if len(path) == 1:
            if saved is None or goal['parent_goal_id']:
                raise ValueError('native_event_information_saved_owner_required')
        else:
            parent = self._saved(path[:-1])
            if (parent is None or goal['parent_goal_id'] != parent['goal']['goal_id']
                    or goal['task_context'] != parent['goal']['task_context']):
                raise ValueError('native_event_information_parent_mismatch')
            self.store.validate_scope(scope, parent['scope'])
        return request, saved is not None

    def _job(self, job_ref, scope):
        row = self.jobs._row(job_ref)
        query = self.store.get(row['query_ref'])
        if (self.store.subject_unit(row['query_ref']) != 'aa' or not query.get('sequence_ref')
                or not self.store.roots(row['query_ref'])
                or not self.store.scope_covers(self.store.coverage(row['query_ref']), scope)):
            raise ValueError('native_event_information_job_outside_scope')
        symbols = artifact_path(self.store, query['sequence_ref']).read_text()
        if row['query_fasta'] != normalize_query_fasta('>query\n' + symbols + '\n'):
            raise ValueError('native_event_information_query_identity_conflict')
        return row

    def _selection(self, value, row):
        expected = {'resource_id': self.resource_id, 'kind': 'local',
            'allocation': {'cpu': row['cpu'], **self.jobs.config['job_limits']},
            'capability_binding_ref': self.jobs.config['registry_ref']}
        if value != expected:
            raise ValueError('native_event_information_resource_conflict')

    def _legacy_assignment(self, assigned, row):
        if not isinstance(assigned, dict) or assigned.get('job_ref') != row['job_ref']:
            raise ValueError('native_event_information_assignment_conflict')
        for key in ('query_ref', 'cpu', 'search_mode'):
            if key in assigned and assigned[key] != row.get(key, 'native_defaults'):
                raise ValueError('native_event_information_assignment_conflict')
        if 'handoff' in assigned:
            handoff = _validate(assigned['handoff'], LEGACY_HANDOFF_SCHEMA)
            if (handoff['job_ref'] != row['job_ref']
                    or handoff['registry_ref'] != self.jobs.config['registry_ref']):
                raise ValueError('native_event_information_assignment_conflict')

    def _assigned(self, context, request):
        message, assignment = request['message'], plain(context.assignment)
        candidates = []
        legacy = None
        version = assignment.get('version')
        if context.role in ('job_launch', 'job_monitor', 'job_results'):
            legacy = message.get('job_assignment')
            if not isinstance(legacy, dict) or not legacy.get('job_ref'):
                raise ValueError('native_event_information_assignment_conflict')
            candidates.append(legacy['job_ref'])
        elif version == LAUNCH_VERSION:
            adapter = assignment.get('adapter_assignment')
            requested = assignment.get('job_request', {})
            if adapter is not None:
                if not isinstance(adapter, dict) or not adapter.get('job_ref'):
                    raise ValueError('native_event_information_assignment_conflict')
                candidates.append(adapter['job_ref'])
                legacy = adapter
            if 'existing_job_ref' in requested:
                candidates.append(requested['existing_job_ref'])
        elif version == RESULTS_VERSION:
            handoff = _validate(assignment['handoff'], HANDOFF_SCHEMA)
            candidates.append(handoff['execution_handle'])
            legacy = assignment.get('adapter_assignment')
            if legacy is not None:
                candidates.append(legacy.get('job_ref'))
        elif context.role == 'monitor' and version == 'monitor_assignment_v1':
            target = assignment.get('target_handle')
            if not self.jobs.resolve(target, 'homology_job'):
                return []  # Episode targets reveal no dependent job identities.
            candidates.append(target)
        if not candidates:
            return []
        if any(type(ref) is not str or not ref or ref != candidates[0] for ref in candidates):
            raise ValueError('native_event_information_assignment_conflict')
        row = self._job(candidates[0], plain(context.scope))
        if legacy is not None:
            self._legacy_assignment(legacy, row)
        if version == LAUNCH_VERSION:
            requested = assignment['job_request']
            for key in ('query_ref', 'cpu', 'search_mode'):
                if key in requested and requested[key] != row.get(key, 'native_defaults'):
                    raise ValueError('native_event_information_assignment_conflict')
            selection = assignment.get('resource_selection')
            if selection is not None:
                self._selection(selection, row)
            constraints = assignment.get('constraints', {})
            actual = {'resource_id': self.resource_id, 'kind': 'local', 'cpu': row['cpu'],
                **self.jobs.config['job_limits']}
            if (any(key in constraints and constraints[key] != value for key, value in actual.items())
                    or 'allowed_resource_ids' in constraints and self.resource_id not in constraints['allowed_resource_ids']
                    or 'allowed_kinds' in constraints and 'local' not in constraints['allowed_kinds']):
                raise ValueError('native_event_information_resource_conflict')
        if version == RESULTS_VERSION:
            handoff = assignment['handoff']
            self._selection(handoff['resource_selection'], row)
            for field, contract in (('monitoring', 'homology.status.v1'), ('results', 'homology.results.v1')):
                if handoff[field] != {'provider_id': self.resource_id,
                        'target_handle': row['job_ref'], 'contract_ref': contract}:
                    raise ValueError('native_event_information_assignment_conflict')
        return [row['job_ref']]

    def _actual_target(self, context, target):
        target = _target(target)
        registration = validate_native_registration(self.backend.native_target(target['handle']))
        if (target != native_target_descriptor(registration)
                or registration['run_id'] != self.journal.run_id
                or registration['registry_ref'] != self.jobs.config['registry_ref']
                or registration['resource_id'] != self.resource_id):
            raise ValueError('native_event_information_target_identity_conflict')
        self._job(registration['job_ref'], plain(context.scope))
        binding = self.jobs.native_event_binding(registration['job_ref'])
        if binding is None:
            # Registration remains durable authority after native control-file
            # cleanup. An extant unbound reservation, however, is a conflict.
            directory = getattr(self.jobs, 'directory', None)
            if directory is not None and (Path(directory) / registration['job_ref'] / 'native.handle.json').is_file():
                raise ValueError('native_event_information_target_identity_conflict')
            return target
        original = binding.as_record()
        if (any(original.get(key) != registration[key] for key in
                ('run_id', 'owner_episode_id', 'job_ref', 'registry_ref', 'resource_id'))
                or Path(original['execution_directory']).resolve() != self.backend.root_directory):
            raise ValueError('native_event_information_target_identity_conflict')
        # This read-only registry port authenticates the actual original
        # handle/unit/request bytes against that reservation and registration.
        # Backend existence alone cannot bless a stale or copied descriptor.
        if target not in self.jobs.native_event_targets(registration['job_ref']):
            raise ValueError('native_event_information_original_target_unavailable')
        return target

    def _received(self, episode_id):
        rows = self.store.db.execute("""SELECT
            json_extract(attempts.form, '$.' || json_quote(fields.key)) AS targets,
            json_type(attempts.form, '$.' || json_quote(fields.key)) AS target_type
            FROM runtime_report_attempts attempts
            JOIN json_each(attempts.contract,'$.measurements.schema.properties') fields
            WHERE attempts.run_id=? AND attempts.parent_episode_id=?
            AND attempts.failure IS NULL AND attempts.form IS NOT NULL
            AND json_extract(fields.value,'$.x-source')='native_event_targets'
            ORDER BY attempts.decision_index,fields.id""", (self.journal.run_id, episode_id))
        for row in rows:
            if row['target_type'] != 'array':
                raise ValueError('native_event_information_received_targets_invalid')
            yield from json.loads(row['targets'])

    def _wait_cursors(self, context, visible):
        installed = self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='episode_waits'").fetchone()
        if installed is None:
            return
        rows = self.store.db.execute("""SELECT waits.wait_id,waits.original_decision_index,
            waits.request_sha256,waits.request,waits.wake,waits.outcome,
            json_extract(actions.action,'$.condition') AS selected,
            json_extract(actions.result,'$.wait_outcome') AS received
            FROM episode_waits waits JOIN runtime_actions actions
            ON actions.run_id=waits.run_id AND actions.episode_id=waits.parent_episode_id
            AND actions.decision_index=waits.original_decision_index
            WHERE waits.run_id=? AND waits.parent_episode_id=? AND waits.outcome IS NOT NULL
            AND json_extract(actions.action,'$.kind')='wait'
            AND json_extract(actions.result,'$.status')='completed'
            ORDER BY waits.original_decision_index""", (self.journal.run_id, context.episode_id))
        for row in rows:
            outcome = json.loads(row['outcome'])
            trigger = outcome.get('trigger')
            if not isinstance(trigger, dict) or trigger.get('handle') not in visible:
                continue
            request = json.loads(row['request'])
            condition = validate_condition(request['condition'])
            wake = _validate_wake(json.loads(row['wake']), condition)
            matching = next((event for event in wake['events'] if event['event'] == wake['reason']), None)
            if (request.get('version') != 'wait_request_v1' or request.get('wait_id') != row['wait_id']
                    or request.get('parent_episode_id') != context.episode_id
                    or request.get('original_decision_index') != row['original_decision_index']
                    or content_digest(request) != row['request_sha256']
                    or outcome.get('version') != 'wait_outcome_v1' or outcome.get('wait_id') != row['wait_id']
                    or outcome.get('condition_sha256') != content_digest(condition)
                    or outcome.get('duration_measure') != 'measured_wait_intervals'
                    or type(outcome.get('unmeasured_interruption')) is not bool
                    or outcome.get('measured_duration_seconds') is not None and (
                        type(outcome['measured_duration_seconds']) not in (int, float)
                        or not math.isfinite(outcome['measured_duration_seconds'])
                        or outcome['measured_duration_seconds'] < 0)
                    or row['selected'] is None or json.loads(row['selected']) != condition
                    or row['received'] is None or json.loads(row['received']) != outcome
                    or wake['reason'] != 'state_changed' or outcome.get('wake_reason') != wake['reason']
                    or matching is None or trigger != {'handle': matching['handle'], 'cursor': matching['cursor']}):
                raise ValueError('native_event_information_wait_identity_conflict')
            yield trigger['handle'], trigger['cursor']

    def _read(self, context):
        request, saved = self._authenticate(context)
        assigned = self._assigned(context, request)
        visible, cursors = {}, {}

        def receive(value):
            row = validate_target_view(value)
            target = self._actual_target(context, row['target'])
            handle = target['handle']
            if handle in visible and visible[handle]['target'] != target:
                raise ValueError('native_event_information_target_conflict')
            if handle not in visible:
                visible[handle] = {'target': target, 'after_cursor': 0}
                cursors[handle] = {0}
            cursors[handle].add(row['after_cursor'])
            visible[handle]['after_cursor'] = max(visible[handle]['after_cursor'], row['after_cursor'])

        for job_ref in assigned:
            # These registry ports inspect original reservations only. A job
            # with no handle/binding or no registration supplies no target.
            for target in self.jobs.native_event_targets(job_ref):
                if target.get('job_ref') != job_ref:
                    raise ValueError('native_event_information_assignment_conflict')
                receive({'target': target, 'after_cursor': 0})
        if saved:
            rows = self.store.db.execute("""SELECT json_extract(action,'$.arguments') AS arguments,
                json_extract(result,'$.native_event_targets') AS targets,
                json_type(result,'$.native_event_targets') AS target_type
                FROM runtime_actions WHERE run_id=? AND episode_id=?
                AND json_extract(action,'$.kind')='tool'
                AND json_extract(action,'$.tool') IN ('homology.submit','homology.resume_start')
                AND json_extract(result,'$.status') IN ('completed','failed')
                AND json_type(result,'$.native_event_targets') IS NOT NULL ORDER BY decision_index""",
                (self.journal.run_id, context.episode_id))
            for row in rows:
                if row['target_type'] != 'array' or row['arguments'] is None or json.loads(row['arguments']) != {}:
                    raise ValueError('native_event_information_selected_targets_invalid')
                for target in json.loads(row['targets']):
                    if target.get('job_ref') not in assigned:
                        raise ValueError('native_event_information_assignment_conflict')
                    receive({'target': target, 'after_cursor': 0})
            for row in self._received(context.episode_id):
                receive(row)
            for handle, cursor in self._wait_cursors(context, visible):
                cursors[handle].add(cursor)
                visible[handle]['after_cursor'] = max(visible[handle]['after_cursor'], cursor)
        return list(visible.values()), cursors

    def read(self, context):
        with self.store.read_snapshot():
            return self._read(context)[0]

    def facts(self, context):
        return {SOURCE: self.read(context)}

    def resolve(self, context, reference, namespace):
        if namespace not in NAMESPACES | {None} or type(reference) is not str:
            return False
        field = {'native_event_target': 'handle', 'homology_job': 'job_ref',
            'execution_registry': 'registry_ref', 'resource_binding': 'resource_id'}
        rows = self.read(context)
        fields = field.values() if namespace is None else (field[namespace],)
        return any(reference == row['target'][key] for row in rows for key in fields)

    def validate_wait(self, context, condition):
        condition = validate_condition(plain(condition))
        visible = {row['target']['handle']: row['target'] for row in self.read(context)}
        for event in condition['events']:
            if event['handle'] in visible:
                job = self.jobs._row(visible[event['handle']]['job_ref'])
                if not self.jobs._has_intent(job):
                    raise EventTargetError('wait_target_unavailable', affected_refs=[event['handle']],
                        detail='native_job_has_no_submission_intent')
                if event['event'] != 'state_changed':
                    raise EventTargetError('unsupported_wait_event', affected_refs=[event['handle']],
                        detail='native_event_information_unsupported_event')
            elif event['handle'].startswith('native_event_target_'):
                raise EventTargetError('wait_target_not_visible', affected_refs=[event['handle']],
                    detail='native_event_information_target_not_visible')
            else:
                # A native registration cannot hide behind a nonstandard name.
                try:
                    self.backend.native_target(event['handle'])
                except KeyError:
                    continue
                raise EventTargetError('wait_target_not_visible', affected_refs=[event['handle']],
                    detail='native_event_information_target_not_visible')
        return condition

    def validate_report(self, context, form, schema):
        with self.store.read_snapshot():
            rows, cursors = self._read(context)
            visible = {row['target']['handle']: row['target'] for row in rows}
            for name, declared in plain(schema).get('properties', {}).items():
                if declared.get('x-source') != SOURCE:
                    continue
                value = plain(form).get(name)
                if not isinstance(value, list):
                    raise ReportBoundaryError('Native event source must be an array', code='native_event_target_fact_mismatch')
                seen = set()
                for candidate in value:
                    try:
                        row = validate_target_view(candidate)
                        handle = row['target']['handle']
                        if (handle in seen or visible.get(handle) != row['target']
                                or row['after_cursor'] not in cursors.get(handle, ())):
                            raise ValueError('native_event_target_fact_mismatch')
                        seen.add(handle)
                    except (ValueError, KeyError, TypeError) as error:
                        raise ReportBoundaryError('Native event fields differ from received facts',
                            code='native_event_target_fact_mismatch') from error


__all__ = ['NativeEventInformation', 'report_sources', 'validate_target_view', 'TARGET_SCHEMA', 'VIEW_SCHEMA']
