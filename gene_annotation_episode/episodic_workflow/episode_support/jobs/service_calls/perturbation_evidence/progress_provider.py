"""A106 execution progress observations over the run's shared Store (the monitors' ``a106_progress_provider``).

A monitor target is an execution handle owned by A106's execution job provider
(``job_provider``: ``scope(handle)``, ``describe_target(handle, scope)``,
``observe(handle, requested_fields, scope, *, operation_key)`` and
``direct_dependencies(handle, scope)``). The provider records each delivered
progress observation once in the Store's transaction, gives an unchanged
observation its original identity (new read timestamps alone are not new
information), and replays a selected observation by its operation key.

Execution owners publish exposed facts (committed records, measured values,
source-bound log windows, job relations) with ``expose``; each is checked
against the Store before it is saved. Child Episodes are not progress targets:
under ``episode_runtime`` a parent receives its child's admitted return
directly, so an ``episode`` dependency raises. A106's progress records define resource
execution statuses only; an observation with any other status fails its snapshot schema.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json

from method_loop.jsonvalue import canonical, content_digest

from gene_annotation_episode.episodic_workflow.episode_support.forms.perturbation_evidence.communication import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.domain import ContractError, REF, RECORD_SCHEMAS, obj, validate_schema
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.progress_records import RESOURCE_STATUS_SCHEMA, validate_resource_status

PROGRESS_VERSION = 'progress_snapshot_v1'
FIELDS = ('execution_status', 'measurements', 'log_windows', 'committed_record_refs', 'dependencies',
          'result_available')
_STATES = ('pending', 'executing', 'returned', 'admitted')
_REFS = {'type': 'array', 'items': REF, 'uniqueItems': True}
_FIELDS = {'type': 'array', 'items': {'enum': list(FIELDS)}, 'uniqueItems': True}
_TEXT = {'type': 'string', 'minLength': 1}
_RUNTIME_REFS = {'type': 'array', 'items': _TEXT, 'uniqueItems': True}
_RECORD_TYPES = {'type': 'array', 'uniqueItems': True, 'items': {'enum': sorted(RECORD_SCHEMAS)}}
_DEPENDENCY = obj({'handle': _TEXT, 'kind': {'enum': ['episode', 'job']}, 'relation_ref': _TEXT,
                   'observed_at': _TEXT, 'state': {'enum': list(_STATES)}})
_MEASUREMENT = obj({'name': _TEXT, 'value': {'type': ['number', 'null']}, 'unit': _TEXT, 'measured_at': _TEXT,
                    'provenance_ref': _TEXT})
_LOG = obj({'source_ref': REF, 'artifact_ref': REF, 'start_byte': {'type': 'integer', 'minimum': 0},
            'end_byte': {'type': 'integer', 'minimum': 0}, 'observed_at': _TEXT,
            'content_sha256': {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}})
_SNAPSHOT = obj({'version': {'const': PROGRESS_VERSION}, 'progress_ref': _TEXT, 'target_handle': _TEXT,
                 'observed_at': _TEXT, 'provenance_refs': _RUNTIME_REFS,
                 'execution_status': RESOURCE_STATUS_SCHEMA,
                 'measurements': {'type': 'array', 'items': _MEASUREMENT},
                 'log_windows': {'type': 'array', 'items': _LOG}, 'committed_record_refs': _REFS,
                 'dependencies': {'type': 'array', 'items': _DEPENDENCY}, 'result_available': {'type': 'boolean'}})


def _now():
    return datetime.now(timezone.utc).isoformat()


def _timestamp(value):
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if result.tzinfo is None or result.utcoffset().total_seconds() != 0:
            raise ValueError
    except (ValueError, AttributeError) as error:
        raise ContractError('progress_utc_timestamp_required') from error
    return result


def _unique(values):
    return list(dict.fromkeys(values))


def _same_observation(value):
    """New read timestamps alone do not create a new observed contribution."""
    result = json.loads(json.dumps(value))
    result.pop('progress_ref', None)
    result.pop('observed_at', None)
    result['execution_status'].pop('observed_at', None)
    for field, stamp in (('dependencies', 'observed_at'), ('log_windows', 'observed_at'),
                         ('measurements', 'measured_at')):
        for row in result.get(field, ()):
            row.pop(stamp, None)
    return result


class ProgressProvider:
    """Progress observations of A106 execution targets, recorded in the run's shared Store."""

    def __init__(self, store, *, run_id, job_provider):
        if not isinstance(run_id, str) or not run_id:
            raise ContractError('progress_run_identity_required')
        for method in ('scope', 'describe_target', 'observe', 'direct_dependencies'):
            if not callable(getattr(job_provider, method, None)):
                raise ContractError('progress_job_provider_requires:' + method)
        self.store, self.run_id, self.job_provider = store, run_id, job_provider
        with store.transaction():
            store.db.execute("""CREATE TABLE IF NOT EXISTS a106_progress_exposures (
                run_id TEXT NOT NULL, target_handle TEXT NOT NULL, operation_key TEXT NOT NULL,
                signature TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(run_id,target_handle,operation_key))""")
            store.db.execute("""CREATE TABLE IF NOT EXISTS a106_progress_observations (
                run_id TEXT NOT NULL, progress_ref TEXT NOT NULL, target_handle TEXT NOT NULL,
                scope TEXT NOT NULL, signature TEXT NOT NULL, snapshot TEXT NOT NULL, observation_identity TEXT NOT NULL,
                PRIMARY KEY(run_id,progress_ref), UNIQUE(run_id,target_handle,scope,signature))""")
            store.db.execute("""CREATE TABLE IF NOT EXISTS a106_progress_selections (
                run_id TEXT NOT NULL, operation_key TEXT NOT NULL, signature TEXT NOT NULL,
                selection TEXT NOT NULL, progress_ref TEXT NOT NULL, PRIMARY KEY(run_id,operation_key))""")

    def _target_scope(self, handle, scope=None):
        if not isinstance(handle, str) or not handle:
            raise ContractError('progress_target_handle_required')
        try:
            target_scope = self.store.validate_scope(self.job_provider.scope(handle))
        except KeyError:
            raise ContractError('progress_target_unavailable') from None
        if scope is not None and not self.store.scope_contains(plain(scope), target_scope):
            raise ContractError('progress_target_outside_scope')
        return target_scope

    def _record(self, reference, scope, kind=None):
        if not self.store.reference_subset([reference], scope):
            raise ContractError('progress_reference_outside_scope')
        value = self.store.get(reference)
        if kind is not None and value['record_type'] != kind:
            raise ContractError('progress_reference_type_mismatch')
        return value

    def describe_target(self, handle, scope):
        """The execution owner's target description; observing it is a separate action."""
        return self.job_provider.describe_target(handle, self._target_scope(handle, scope))

    def _validate_dependency(self, dependency, scope):
        validate_schema(dependency, _DEPENDENCY)
        _timestamp(dependency['observed_at'])
        if dependency['kind'] == 'episode':
            raise ContractError('progress_episode_dependency_has_no_progress_target')
        self._target_scope(dependency['handle'], scope)
        # Job relationships are published by the owning execution binding with a committed relation record.
        self._record(dependency['relation_ref'], scope)

    def _validate_exposed(self, fields, scope):
        for reference in fields['committed_record_refs']:
            self._record(reference, scope)
        for dependency in fields['dependencies']:
            self._validate_dependency(dependency, scope)
        for measurement in fields['measurements']:
            validate_schema(measurement, _MEASUREMENT)
            _timestamp(measurement['measured_at'])
            if not self.resolve(measurement['provenance_ref'], scope, None):
                raise ContractError('progress_measurement_provenance_unavailable')
        for window in fields['log_windows']:
            validate_schema(window, _LOG)
            _timestamp(window['observed_at'])
            source = self._record(window['source_ref'], scope, 'source')
            self._record(window['artifact_ref'], scope, 'artifact')
            if window['artifact_ref'] not in {source.get(key) for key in
                                              ('artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref')}:
                raise ContractError('progress_log_source_artifact_mismatch')
            data = self.store.get_artifact(window['artifact_ref'])
            if not 0 <= window['start_byte'] <= window['end_byte'] <= len(data):
                raise ContractError('progress_log_window_out_of_bounds')
            if hashlib.sha256(data[window['start_byte']:window['end_byte']]).hexdigest() != window['content_sha256']:
                raise ContractError('progress_log_window_digest_mismatch')
        for reference in fields['provenance_refs']:
            if not self.resolve(reference, scope, None):
                raise ContractError('progress_provenance_unavailable')

    def expose(self, target_handle, *, operation_key, committed_record_refs=(), dependencies=(), measurements=(),
               log_windows=(), provenance_refs=()):
        """Publish actual committed exposed information for a target, under its operation identity."""
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError('progress_operation_key_required')
        scope = self._target_scope(target_handle)
        payload = {'version': 'progress_exposure_v1', 'target_handle': target_handle,
                   'committed_record_refs': _unique(committed_record_refs), 'dependencies': plain(dependencies),
                   'measurements': plain(measurements), 'log_windows': plain(log_windows),
                   'provenance_refs': _unique(provenance_refs)}
        signature = content_digest(payload)
        with self.store.transaction():
            row = self.store.db.execute('SELECT signature,payload FROM a106_progress_exposures WHERE run_id=? '
                                        'AND target_handle=? AND operation_key=?',
                                        (self.run_id, target_handle, operation_key)).fetchone()
            if row:
                if row['signature'] != signature:
                    raise ContractError('progress_operation_identity_conflict')
                return json.loads(row['payload'])
            self._validate_exposed(payload, scope)
            payload.update(observed_at=_now(), publication_ref='progress_publication_' + content_digest(
                {'run_id': self.run_id, 'target_handle': target_handle, 'operation_key': operation_key,
                 'signature': signature}))
            self.store.db.execute('INSERT INTO a106_progress_exposures VALUES(?,?,?,?,?)',
                                  (self.run_id, target_handle, operation_key, signature, canonical(payload)))
        return payload

    def _exposures(self, target):
        rows = self.store.db.execute('SELECT payload FROM a106_progress_exposures WHERE run_id=? AND target_handle=? '
                                     'ORDER BY rowid', (self.run_id, target))
        return [json.loads(row[0]) for row in rows]

    def direct_dependencies(self, target_handle, scope):
        target_scope = self._target_scope(target_handle, scope)
        values = [dependency for row in self._exposures(target_handle) for dependency in row['dependencies']]
        values.extend(plain(self.job_provider.direct_dependencies(target_handle, target_scope)))
        by_handle = {}
        for dependency in values:
            self._validate_dependency(dependency, target_scope)
            previous = by_handle.get(dependency['handle'])
            if previous is None or {k: v for k, v in previous.items() if k != 'observed_at'} != {
                    k: v for k, v in dependency.items() if k != 'observed_at'}:
                by_handle[dependency['handle']] = dependency
        return list(by_handle.values())

    def _selected_observation(self, operation_key, signature, scope):
        if operation_key is None:
            return None
        row = self.store.db.execute('SELECT signature,progress_ref FROM a106_progress_selections WHERE run_id=? '
                                    'AND operation_key=?', (self.run_id, operation_key)).fetchone()
        if row is None:
            return None
        if row['signature'] != signature:
            raise ContractError('progress_operation_identity_conflict')
        return self.read_progress(row['progress_ref'], scope)

    def observe(self, target_handle, requested_fields, scope, *, permitted_committed_record_types, operation_key):
        """One delivered observation of the target's requested fields; a selected observation replays by key."""
        requested_fields = plain(requested_fields)
        permitted = plain(permitted_committed_record_types)
        validate_schema(permitted, _RECORD_TYPES)
        validate_schema(requested_fields, _FIELDS)
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError('progress_operation_key_required')
        selection = {'target_handle': target_handle, 'requested_fields': requested_fields, 'scope': plain(scope),
                     'permitted_committed_record_types': permitted}
        selection_signature = content_digest(selection)
        replay = self._selected_observation(operation_key, selection_signature, scope)
        if replay is not None:
            return replay
        target_scope = self._target_scope(target_handle, scope)
        raw = plain(self.job_provider.observe(target_handle, requested_fields, target_scope,
                                              operation_key=operation_key))
        validate_schema(raw, _SNAPSHOT)
        if raw['target_handle'] != target_handle:
            raise ContractError('progress_job_target_mismatch')
        status = validate_resource_status(raw['execution_status'])
        if raw['result_available'] != status['result_available'] or status['handle'] != target_handle:
            raise ContractError('progress_job_status_relationship_mismatch')
        _timestamp(raw['observed_at'])
        _timestamp(status['observed_at'])
        base = {field: list(raw[field]) for field in
                ('provenance_refs', 'measurements', 'log_windows', 'committed_record_refs')}
        for exposed in self._exposures(target_handle):
            for field in base:
                base[field].extend(exposed[field])
        base['provenance_refs'] = _unique(base['provenance_refs'])
        base['committed_record_refs'] = _unique(base['committed_record_refs'])
        for field, stamp in (('measurements', 'measured_at'), ('log_windows', 'observed_at')):
            rows = {}
            for row in base[field]:
                rows.setdefault(canonical({k: v for k, v in row.items() if k != stamp}), row)
            base[field] = list(rows.values())
        dependencies = self.direct_dependencies(target_handle, target_scope)
        original = {'target_handle': target_handle, 'execution_status': status, **base, 'dependencies': dependencies,
                    'result_available': raw['result_available']}
        observation_identity = 'progress_observation_' + content_digest(_same_observation(original))
        base['committed_record_refs'] = [ref for ref in base['committed_record_refs']
                                         if self.store.get(ref)['record_type'] in permitted]
        self._validate_exposed({**base, 'dependencies': dependencies}, target_scope)
        value = {'version': PROGRESS_VERSION, 'target_handle': target_handle, 'observed_at': raw['observed_at'],
                 'execution_status': status,
                 **{field: rows if field == 'provenance_refs' or field in requested_fields else []
                    for field, rows in base.items()},
                 'dependencies': dependencies if 'dependencies' in requested_fields else [],
                 'result_available': raw['result_available']}
        value['provenance_refs'] = [*value['provenance_refs'], observation_identity]
        signature = content_digest(_same_observation(value))
        serialized_scope = canonical(target_scope)
        with self.store.transaction():
            replay = self._selected_observation(operation_key, selection_signature, scope)
            if replay is not None:
                return replay
            old = self.store.db.execute('SELECT snapshot FROM a106_progress_observations WHERE run_id=? AND '
                                        'target_handle=? AND scope=? AND signature=?',
                                        (self.run_id, target_handle, serialized_scope, signature)).fetchone()
            if old:
                value = json.loads(old[0])
            else:
                value['progress_ref'] = 'progress_' + content_digest(
                    {'run_id': self.run_id, 'target_handle': target_handle, 'scope': target_scope,
                     'signature': signature})
                validate_schema(value, _SNAPSHOT)
                self.store.db.execute('INSERT INTO a106_progress_observations VALUES(?,?,?,?,?,?,?)',
                                      (self.run_id, value['progress_ref'], target_handle, serialized_scope, signature,
                                       canonical(value), observation_identity))
            self.store.db.execute('INSERT INTO a106_progress_selections VALUES(?,?,?,?,?)',
                                  (self.run_id, operation_key, selection_signature, canonical(selection),
                                   value['progress_ref']))
        return value

    def read_progress(self, reference, scope=None):
        row = self.store.db.execute('SELECT scope,snapshot FROM a106_progress_observations WHERE run_id=? AND '
                                    'progress_ref=?', (self.run_id, reference)).fetchone()
        if row is None:
            raise ContractError('progress_reference_unavailable')
        if scope is not None and not self.store.scope_contains(plain(scope), json.loads(row['scope'])):
            raise ContractError('progress_reference_outside_scope')
        return json.loads(row['snapshot'])

    def resolve(self, reference, scope, namespace=None):
        """Whether ``reference`` names, within ``scope``, something of ``namespace`` this provider holds."""
        if namespace in (None, 'progress_provenance'):
            for row in self.store.db.execute("SELECT target_handle FROM a106_progress_exposures WHERE run_id=? "
                                             "AND json_extract(payload,'$.publication_ref')=?",
                                             (self.run_id, reference)):
                try:
                    self._target_scope(row[0], scope)
                except ContractError:
                    continue
                return True
        if namespace in (None, 'progress_observation', 'progress_provenance'):
            for row in self.store.db.execute('SELECT progress_ref FROM a106_progress_observations WHERE run_id=? '
                                             'AND observation_identity=?', (self.run_id, reference)):
                try:
                    self.read_progress(row[0], scope)
                except ContractError:
                    continue
                return True
        if namespace in (None, 'episode_progress', 'progress', 'progress_snapshot'):
            try:
                self.read_progress(reference, scope)
            except ContractError:
                pass
            else:
                return True
        if namespace in (None, 'execution_handle', 'execution', 'progress_provenance'):
            try:
                self._target_scope(reference, scope)
            except ContractError:
                pass
            else:
                return True
        if namespace in (None, 'progress_provenance'):
            return bool(self.store.reference_subset([reference], plain(scope)))
        return False


__all__ = ['FIELDS', 'PROGRESS_VERSION', 'ProgressProvider']
