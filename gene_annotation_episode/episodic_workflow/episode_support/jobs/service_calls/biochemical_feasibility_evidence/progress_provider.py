"""A110 execution progress observations.

A monitor target is an execution handle owned by A110's execution job provider
(``job_provider``: ``scope(handle)``, ``describe_target(handle, scope)``,
``observe(handle, requested_fields, scope)`` and
``direct_dependencies(handle, scope)``). The provider records each delivered
progress observation once as a row of the Episode, and gives an unchanged
observation its original identity (new read timestamps alone are not new
information).

Execution owners publish exposed facts (committed records, measured values,
source-bound log windows, job relations) with ``expose``; each is checked
against the Store before it is saved. Child Episodes are not progress targets:
under ``episode_runtime`` a parent receives its child's admitted return
directly, so an ``episode`` dependency raises. A110's progress records define resource
execution statuses only; an observation with any other status fails its snapshot schema.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json

from episode_runtime import TableDeclaration
from method_loop.jsonvalue import canonical, content_digest

from gene_annotation_episode.episodic_workflow.episode_support.forms.biochemical_feasibility_evidence.communication import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.biochemical_feasibility_evidence.domain import ContractError, REF, RECORD_SCHEMAS, obj, validate_schema
from gene_annotation_episode.episodic_workflow.episode_support.records.biochemical_feasibility_evidence.progress_records import RESOURCE_STATUS_SCHEMA, validate_resource_status

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


EXPOSURES = TableDeclaration(name='a110_progress_exposures',
                             columns=('target_handle', 'signature', 'publication_ref', 'payload', 'record_refs'),
                             key=('target_handle', 'signature'), record_refs=('record_refs',))
OBSERVATIONS = TableDeclaration(name='a110_progress_observations',
                                columns=('progress_ref', 'target_handle', 'scope', 'signature', 'snapshot',
                                         'observation_identity', 'record_refs'),
                                key=('target_handle', 'scope', 'signature'), record_refs=('record_refs',))


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
    """Progress observations of A110 execution targets, kept as work-table rows of the Episode.

    ``store`` is ``ctx.store`` of a tool (``observe`` and ``expose`` write) or the read-only reader (``read_progress``,
    ``resolve``, ``direct_dependencies`` and ``describe_target`` only read)."""

    def __init__(self, store, *, job_provider):
        for method in ('scope', 'describe_target', 'observe', 'direct_dependencies'):
            if not callable(getattr(job_provider, method, None)):
                raise ContractError('progress_job_provider_requires:' + method)
        self.store, self.job_provider = store, job_provider

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

    @staticmethod
    def _held_refs(fields):
        """The records a snapshot or exposure names, to be held with its row."""
        return _unique([*fields['committed_record_refs'], *(row['relation_ref'] for row in fields['dependencies']),
                        *(ref for row in fields['log_windows'] for ref in (row['source_ref'], row['artifact_ref']))])

    def expose(self, target_handle, *, committed_record_refs=(), dependencies=(), measurements=(),
               log_windows=(), provenance_refs=()):
        """Publish actual committed exposed information for a target; the same information again is the same
        publication."""
        scope = self._target_scope(target_handle)
        payload = {'version': 'progress_exposure_v1', 'target_handle': target_handle,
                   'committed_record_refs': _unique(committed_record_refs), 'dependencies': plain(dependencies),
                   'measurements': plain(measurements), 'log_windows': plain(log_windows),
                   'provenance_refs': _unique(provenance_refs)}
        signature = content_digest(payload)
        with self.store.transaction():
            held = self.store.table(EXPOSURES).select({'target_handle': target_handle, 'signature': signature})
            if held:
                return held[0]['payload']
            self._validate_exposed(payload, scope)
            payload.update(observed_at=_now(), publication_ref='progress_publication_' + content_digest(
                {'target_handle': target_handle, 'signature': signature}))
            self.store.table(EXPOSURES).put({
                'target_handle': target_handle, 'signature': signature,
                'publication_ref': payload['publication_ref'], 'payload': payload,
                'record_refs': self._held_refs(payload)})
        return payload

    def _exposures(self, target):
        return [row['payload'] for row in self.store.table(EXPOSURES).select({'target_handle': target})]

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

    def observe(self, target_handle, requested_fields, scope, *, permitted_committed_record_types):
        """One delivered observation of the target's requested fields; an observation unchanged since an earlier
        one is that earlier observation."""
        requested_fields = plain(requested_fields)
        permitted = plain(permitted_committed_record_types)
        validate_schema(permitted, _RECORD_TYPES)
        validate_schema(requested_fields, _FIELDS)
        target_scope = self._target_scope(target_handle, scope)
        raw = plain(self.job_provider.observe(target_handle, requested_fields, target_scope))
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
        with self.store.transaction():
            old = self.store.table(OBSERVATIONS).select({'target_handle': target_handle, 'scope': target_scope,
                                                         'signature': signature})
            if old:
                return old[0]['snapshot']
            value['progress_ref'] = 'progress_' + content_digest(
                {'target_handle': target_handle, 'scope': target_scope, 'signature': signature})
            validate_schema(value, _SNAPSHOT)
            self.store.table(OBSERVATIONS).put({
                'progress_ref': value['progress_ref'], 'target_handle': target_handle, 'scope': target_scope,
                'signature': signature, 'snapshot': value, 'observation_identity': observation_identity,
                'record_refs': self._held_refs(value)})
        return value

    def read_progress(self, reference, scope=None):
        rows = self.store.table(OBSERVATIONS).select({'progress_ref': reference})
        if not rows:
            raise ContractError('progress_reference_unavailable')
        if scope is not None and not self.store.scope_contains(plain(scope), rows[0]['scope']):
            raise ContractError('progress_reference_outside_scope')
        return rows[0]['snapshot']

    def resolve(self, reference, scope, namespace=None):
        """Whether ``reference`` names, within ``scope``, something of ``namespace`` the Episode holds."""
        if namespace in (None, 'progress_provenance'):
            for row in self.store.table(EXPOSURES).select({'publication_ref': reference}):
                try:
                    self._target_scope(row['target_handle'], scope)
                except ContractError:
                    continue
                return True
        if namespace in (None, 'progress_observation', 'progress_provenance'):
            for row in self.store.table(OBSERVATIONS).select({'observation_identity': reference}):
                try:
                    self.read_progress(row['progress_ref'], scope)
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
