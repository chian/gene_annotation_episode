"""Immutable evidence from selected resource work, without receiving checks.

The ordinary Store source is the publication boundary after a native check. Its
original outcome can recover that work before runtime has saved the outcome;
neither recovery nor admission asks the native receiver to do the work again.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
from typing import TypedDict

from .communication import plain
from .domain import identity
from .episode_bindings import BindingContext
from .homology_jobs import HomologyJobs, STATUS_SCHEMA, VERSION, normalize_query_fasta, ref
from .homology_results import _snapshot
from .materials import artifact_path
from .resource_records import HANDOFF_SCHEMA, LAUNCH_VERSION, RESULTS_VERSION, _validate


PROVIDER = 'episode.resource_handoff'
VERSION_INFORMATION = 'resource_handoff_information_v1'
CHECK_TOOLS = ('homology.check_handoff', 'resource.check_handoff')


class HandoffInformationV1(TypedDict):
    version: str
    run_id: str
    episode_id: str
    operation_key: str
    tool_name: str
    arguments: dict
    scope: dict
    assignment_sha256: str
    query_ref: str
    registry_ref: str
    job: dict
    execution_handoff: dict
    outcome: dict


class OwnResultRowV1(TypedDict):
    snapshot_ref: str
    query_ref: str
    execution_context: dict
    ordinal: int
    record_ref: str
    record_type: str
    source_byte_spans: list


def _json(value):
    return json.dumps(plain(value), sort_keys=True, separators=(',', ':'), allow_nan=False)


def _digest(value):
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _utc(value):
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.utcoffset() is None:
            raise ValueError
        return parsed.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError) as error:
        raise ValueError('resource_information_invalid_check_timestamp') from error


class ResourceInformation:
    def __init__(self, store, *, run_id: str, jobs: HomologyJobs):
        if type(run_id) is not str or not run_id or type(jobs) is not HomologyJobs:
            raise ValueError('resource_information_explicit_run_and_registry_required')
        self.store, self.run_id, self.jobs = store, run_id, jobs

    def as_record(self):
        return {'version': 'resource_information_reader_v1', 'run_id': self.run_id,
            'registry_ref': self.jobs.config['registry_ref']}

    def _context(self, context):
        if context.run_id != self.run_id:
            raise ValueError('resource_information_identity_conflict')

    def _accession(self, episode_id, operation_key):
        return 'resource_handoff_' + _digest([self.run_id, episode_id, operation_key])

    def _sources(self, *, accession=None):
        query = ("SELECT data FROM records WHERE record_type='source' "
            "AND json_extract(data,'$.provider')=?")
        arguments = [PROVIDER]
        if accession is not None:
            query += " AND json_extract(data,'$.accession')=?"
            arguments.append(accession)
        return [json.loads(row[0]) for row in self.store.db.execute(query + ' ORDER BY id', arguments)]

    def _body(self, source):
        try:
            body = json.loads(self.store.get_artifact(source['artifact_ref']))
        except json.JSONDecodeError as error:
            raise ValueError('resource_information_malformed_proof') from error
        if not isinstance(body, dict):
            raise ValueError('resource_information_malformed_proof')
        return body

    def _selected(self, episode_id, tool_name, arguments, operation_key):
        prefix = f'{self.run_id}:{episode_id}:'
        index = operation_key.removeprefix(prefix) if isinstance(operation_key, str) else ''
        if not isinstance(operation_key, str) or not operation_key.startswith(prefix) or not index.isdecimal() or str(int(index)) != index:
            raise ValueError('resource_information_identity_conflict')
        row = self.store.db.execute('SELECT action,result FROM runtime_actions '
            'WHERE run_id=? AND episode_id=? AND decision_index=?',
            (self.run_id, episode_id, int(index))).fetchone()
        if row is None:
            raise ValueError('resource_information_selected_check_missing')
        action = json.loads(row['action'])
        if (action.get('kind') != 'tool' or action.get('tool') != tool_name
                or action.get('arguments') != arguments):
            raise ValueError('resource_information_identity_conflict')
        return row

    @staticmethod
    def _with_reference(outcome, reference):
        value = deepcopy(outcome)
        for field in ('record_refs', 'resource_information_refs'):
            value[field] = list(dict.fromkeys([*value.get(field, []), reference]))
        return value

    def selected_handoff(self, context, tool_name, arguments, operation_key):
        self._context(context)
        if tool_name in CHECK_TOOLS:
            self._selected(context.episode_id, tool_name, plain(arguments), operation_key)
        sources = self._sources(accession=self._accession(context.episode_id, operation_key))
        if not sources:
            return None
        if len(sources) != 1:
            raise ValueError('resource_information_identity_conflict')
        body = self._body(sources[0])
        if (body.get('episode_id') != context.episode_id or body.get('operation_key') != operation_key
                or body.get('tool_name') != tool_name or body.get('arguments') != plain(arguments)
                or body.get('scope') != plain(context.scope)
                or body.get('assignment_sha256') != _digest(context.assignment)):
            raise ValueError('resource_information_identity_conflict')
        body = self.read_handoff_source(sources[0]['id'], scope=plain(context.scope))
        self._validate_assignment(context, body['execution_handoff'], body['job'])
        return self._with_reference(body['outcome'], sources[0]['id'])

    def _job(self, job_ref):
        row = self.jobs._row(job_ref)
        return {key: row[key] for key in ('job_ref', 'query_ref', 'cpu', 'search_mode')}

    def _query(self, query_ref, scope):
        try:
            self.store.validate_scope(scope)
        except ValueError as error:
            raise ValueError('resource_information_outside_scope') from error
        from .homology_query import protein_query
        return protein_query(self.store,scope,query_ref,error_code='resource_information_outside_scope')

    def _versions(self, versions, scope):
        for item in versions:
            record = self.store.get(item['reference'])
            if not self.store.reference_subset([item['reference']], scope):
                raise ValueError('resource_information_outside_scope')
            if item['version'] is not None and str(record.get('revision')) != item['version']:
                raise ValueError('resource_information_input_version_conflict')
            if item['content_sha256'] is not None:
                artifact = record['id'] if record['record_type'] == 'artifact' else record.get('sequence_ref')
                if artifact is None or hashlib.sha256(artifact_path(self.store, artifact).read_bytes()).hexdigest() != item['content_sha256']:
                    raise ValueError('resource_information_input_version_conflict')

    def _validate_assignment(self, context, handoff, job):
        self._context(context)
        assignment = plain(context.assignment)
        if assignment.get('version') == RESULTS_VERSION:
            assigned = assignment['handoff']
            if (assigned['execution_handle'] != job['job_ref']
                    or assigned['resource_selection'] != handoff['resource_selection']
                    or assigned['submitted_input_versions'] != handoff['submitted_input_versions']):
                raise ValueError('resource_information_assignment_conflict')
        elif assignment.get('version') == LAUNCH_VERSION:
            if assignment['immutable_input_versions'] != handoff['submitted_input_versions']:
                raise ValueError('resource_information_assignment_conflict')
            requested = assignment['job_request']
            for key in ('query_ref', 'cpu', 'search_mode'):
                if key in requested and requested[key] != job[key]:
                    raise ValueError('resource_information_assignment_conflict')
            if 'existing_job_ref' in requested and requested['existing_job_ref'] != job['job_ref']:
                raise ValueError('resource_information_assignment_conflict')
            selection = handoff['resource_selection']
            if assignment['resource_selection'] is not None and assignment['resource_selection'] != selection:
                raise ValueError('resource_information_assignment_conflict')
            constraints = assignment['constraints']
            for key, actual in (('resource_id', selection['resource_id']), ('kind', selection['kind']),
                    *selection['allocation'].items()):
                if key in constraints and constraints[key] != actual:
                    raise ValueError('resource_information_assignment_conflict')
            for key, actual in (('allowed_resource_ids', selection['resource_id']),
                    ('allowed_kinds', selection['kind'])):
                if key in constraints and actual not in constraints[key]:
                    raise ValueError('resource_information_assignment_conflict')
        else:
            raise ValueError('resource_information_assignment_conflict')
        adapter = assignment.get('adapter_assignment')
        if adapter is not None and any(adapter.get(key, 'native_defaults' if key == 'search_mode' else None) != job[key]
                for key in ('job_ref', 'query_ref', 'cpu', 'search_mode')):
            raise ValueError('resource_information_assignment_conflict')

    def _validate_proof(self, body, scope):
        expected = {'version', 'run_id', 'episode_id', 'operation_key', 'tool_name', 'arguments',
            'scope', 'assignment_sha256', 'query_ref', 'registry_ref', 'job', 'execution_handoff', 'outcome'}
        if (not isinstance(body, dict) or set(body) != expected or body['version'] != VERSION_INFORMATION
                or body['run_id'] != self.run_id or body['tool_name'] not in CHECK_TOOLS
                or not isinstance(body['arguments'], dict) or not isinstance(body['scope'], dict)
                or type(body['assignment_sha256']) is not str or len(body['assignment_sha256']) != 64
                or any(c not in '0123456789abcdef' for c in body['assignment_sha256'])):
            raise ValueError('resource_information_malformed_proof')
        handoff = _validate(body['execution_handoff'], HANDOFF_SCHEMA)
        job = self._job(handoff['execution_handle'])
        if body['job'] != job or body['query_ref'] != job['query_ref']:
            raise ValueError('resource_information_job_identity_conflict')
        registry = self.jobs.config['registry_ref']
        if body['registry_ref'] != registry:
            raise ValueError('resource_information_registry_conflict')
        query = self._query(job['query_ref'], scope)
        self._query(job['query_ref'], body['scope'])
        row = self.jobs._row(job['job_ref'])
        symbols = artifact_path(self.store, query['sequence_ref']).read_text()
        if row['query_fasta'] != normalize_query_fasta('>query\n' + symbols + '\n'):
            raise ValueError('resource_information_job_identity_conflict')
        self._versions(handoff['submitted_input_versions'], body['scope'])
        self._versions(handoff['submitted_input_versions'], scope)
        selection = handoff['resource_selection']
        if (selection['kind'] != 'local' or selection['capability_binding_ref'] != registry
                or selection['allocation'] != {'cpu': job['cpu'], **self.jobs.config['job_limits']}
                or handoff['state'] != 'usable' or handoff['failure'] is not None):
            raise ValueError('resource_information_invalid_handoff')
        native = {'job_ref': job['job_ref'], 'registry_ref': registry, 'backend': VERSION,
            'status_interface': 'homology.status.v1', 'progress_interface': 'homology.progress.v1',
            'results_interface': 'homology.results.v1'}
        for key, interface in (('monitoring', 'status_interface'), ('results', 'results_interface')):
            if handoff[key] != {'provider_id': selection['resource_id'], 'target_handle': job['job_ref'],
                    'contract_ref': native[interface]}:
                raise ValueError('resource_information_receiver_conflict')
        outcome = body['outcome']
        checked = outcome.get('result') if isinstance(outcome, dict) else None
        if (not isinstance(checked, dict) or outcome.get('status') != 'completed'
                or outcome.get('execution_handoff') != handoff or checked.get('handoff') != native
                or checked.get('receipt_ref') != ref('handoff_receipt', native)
                or handoff['check_record_refs'] != [checked['receipt_ref']]
                or not isinstance(outcome.get('record_refs'), list)):
            raise ValueError('resource_information_check_outcome_conflict')
        checked_at = checked.get('checked_at_unix_seconds')
        if (type(checked_at) not in (int, float) or not math.isfinite(checked_at) or checked_at < 0
                or handoff['checked_at'] != datetime.fromtimestamp(checked_at, timezone.utc).isoformat()):
            raise ValueError('resource_information_invalid_check_timestamp')
        _utc(handoff['checked_at'])
        sample = _validate(checked.get('sample'), STATUS_SCHEMA)
        if sample['job_ref'] != job['job_ref'] or sample['registry_ref'] != registry:
            raise ValueError('resource_information_check_outcome_conflict')
        receipt = self.jobs.db.execute('SELECT job_ref,body FROM handoffs WHERE receipt_ref=?',
            (checked['receipt_ref'],)).fetchone()
        receipt_body = json.loads(receipt['body']) if receipt is not None else None
        if receipt is None or receipt['job_ref'] != job['job_ref'] or receipt_body.get('handoff') != native:
            raise ValueError('resource_information_check_receipt_conflict')
        selected = self._selected(body['episode_id'], body['tool_name'], body['arguments'], body['operation_key'])
        if body['tool_name'] == 'homology.check_handoff' and body['arguments'] != {}:
            raise ValueError('resource_information_identity_conflict')
        if body['tool_name'] == 'resource.check_handoff':
            original = body['arguments'].get('handoff', {})
            if (set(body['arguments']) != {'handoff'} or original.get('execution_handle') != job['job_ref']
                    or original.get('resource_selection') != selection
                    or original.get('submitted_input_versions') != handoff['submitted_input_versions']):
                raise ValueError('resource_information_identity_conflict')
            _validate(original, HANDOFF_SCHEMA)
            # Validate the exact supplied original object from saved work;
            # a registered physical job cannot bless altered check operands.
            legacy = self.store.db.execute("SELECT json_extract(result,'$.execution_handoff') "
                "FROM runtime_actions WHERE run_id=? AND json_extract(result,'$.status')='completed' "
                "AND json_extract(action,'$.tool') IN ('homology.check_handoff','resource.check_handoff')",
                (self.run_id,))
            if not any(json.loads(row[0]) == original for row in legacy if row[0] is not None):
                matching = [source for source in self._sources()
                    if (candidate := self._body(source)).get('run_id') == self.run_id
                    and candidate.get('operation_key') != body['operation_key']
                    and candidate.get('execution_handoff') == original]
                if not matching:
                    raise ValueError('resource_information_original_handoff_proof_missing')
                for source in matching:
                    self.read_handoff_source(source['id'], scope=scope)
        # The original episode request is authoritative when it was persisted.
        episode = self.store.db.execute('SELECT path,request FROM runtime_episodes '
            'WHERE run_id=? AND episode_id=?', (self.run_id, body['episode_id'])).fetchone()
        if episode is not None:
            request = json.loads(episode['request'])
            message = request.get('message', {})
            assignment = message.get('episode_assignment', message.get('assignment'))
            if assignment is None or _digest(assignment) != body['assignment_sha256']:
                raise ValueError('resource_information_assignment_conflict')
            path = json.loads(episode['path'])
            original_context = BindingContext(self.run_id, body['episode_id'], path[-1][0],
                path, message.get('scope', body['scope']), assignment, request)
            if plain(original_context.scope) != body['scope']:
                raise ValueError('resource_information_identity_conflict')
            self._validate_assignment(original_context, handoff, job)
        return selected

    def publish_handoff(self, context, tool_name, arguments, outcome, operation_key):
        self._context(context)
        if tool_name not in CHECK_TOOLS or outcome.get('status') != 'completed':
            return deepcopy(outcome)
        if not isinstance(outcome.get('execution_handoff'), dict):
            raise ValueError('resource_information_invalid_handoff')
        body = {'version': VERSION_INFORMATION, 'run_id': self.run_id, 'episode_id': context.episode_id,
            'operation_key': operation_key, 'tool_name': tool_name, 'arguments': plain(arguments),
            'scope': plain(context.scope), 'assignment_sha256': _digest(context.assignment),
            'query_ref': self.jobs._row(outcome['execution_handoff']['execution_handle'])['query_ref'],
            'registry_ref': self.jobs.config['registry_ref'],
            'job': self._job(outcome['execution_handoff']['execution_handle']),
            'execution_handoff': deepcopy(outcome['execution_handoff']), 'outcome': deepcopy(outcome)}
        self._validate_assignment(context, body['execution_handoff'], body['job'])
        self._validate_proof(body, plain(context.scope))
        accession = self._accession(context.episode_id, operation_key)
        with self.store.transaction():
            old = self._sources(accession=accession)
            if old:
                if len(old) != 1 or self.read_handoff_source(old[0]['id'], scope=plain(context.scope)) != body:
                    raise ValueError('resource_information_identity_conflict')
                return self._with_reference(outcome, old[0]['id'])
            artifact = self.store.artifact(_json(body), 'application/json')
            source = self.store.put('source', {'provider': PROVIDER, 'accession': accession, 'uri': None,
                'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
                'version': VERSION_INFORMATION, 'retrieved_at': body['execution_handoff']['checked_at'],
                'operand_refs': [body['query_ref']]}, origin='tool')
            return self._with_reference(outcome, source['id'])

    def read_handoff_source(self, reference, *, scope):
        source = self.store.get(reference)
        if source.get('record_type') != 'source' or source.get('provider') != PROVIDER:
            return None
        try:
            raw = self.store.get_artifact(source['artifact_ref'])
            body = self._body(source)
            payload = {key: value for key, value in source.items() if key not in {'id', 'record_type', 'origin'}}
            if (reference != identity('source', {'origin': 'tool', 'record': payload})
                    or source.get('origin') != 'tool'
                    or raw != _json(body).encode() or source['text_ref'] != source['artifact_ref']
                    or source['request_ref'] is not None or source['uri'] is not None
                    or source['version'] != VERSION_INFORMATION
                    or source['accession'] != self._accession(body['episode_id'], body['operation_key'])
                    or source['retrieved_at'] != body['execution_handoff']['checked_at']
                    or source.get('operand_refs') != [body['query_ref']]):
                raise ValueError('resource_information_source_identity_conflict')
            selected = self._validate_proof(body, plain(scope))
            if selected['result'] is not None:
                saved = json.loads(selected['result'])
                expected = self._with_reference(body['outcome'], reference)
                if any(saved.get(key) != value for key, value in expected.items()):
                    raise ValueError('resource_information_saved_outcome_conflict')
            return body
        except (KeyError, TypeError, OverflowError) as error:
            raise ValueError('resource_information_malformed_proof') from error

    def _object_references(self, context, handoff):
        references = []
        for source in self._sources():
            # Foreign runs and other objects are not candidates; a matching
            # recognized proof is fully validated, never silently discarded.
            body = self._body(source)
            if body.get('run_id') != self.run_id or body.get('execution_handoff') != handoff:
                continue
            self.read_handoff_source(source['id'], scope=plain(context.scope))
            references.append(source['id'])
        if not references:
            raise ValueError('resource_information_handoff_proof_missing')
        return references

    def references_for_form(self, context, form, schema):
        self._context(context)
        references = []
        def visit(value, declared):
            source = declared.get('x-source')
            if source == 'execution_handoff':
                if value is not None:
                    references.extend(self._object_references(context, plain(value)))
            elif source == 'execution_handoffs':
                for item in value:
                    references.extend(self._object_references(context, plain(item)))
            elif isinstance(value, Mapping):
                for key, child in value.items():
                    if key in declared.get('properties', {}):
                        visit(child, declared['properties'][key])
            elif isinstance(value, (list, tuple)) and 'items' in declared:
                for child in value:
                    visit(child, declared['items'])
        visit(form, schema)
        return sorted(set(references))

    def references_for_initial(self, context):
        self._context(context)
        if context.role != 'results':
            return []
        return self._object_references(context, plain(context.assignment)['handoff'])

    def own_result_rows(self, context):
        self._context(context)
        if context.role != 'results':
            return []
        assignment = plain(context.assignment)
        handoff = assignment['handoff']
        self._object_references(context, handoff)
        job = self._job(handoff['execution_handle'])
        self._validate_assignment(context, handoff, job)
        self._query(job['query_ref'], plain(context.scope))
        start, count = self._selector(assignment['requested_data_selector'])
        rows = []
        outcomes = self.store.db.execute("SELECT action,result FROM runtime_actions WHERE run_id=? "
            "AND episode_id=? AND json_extract(action,'$.tool')='homology.extract' "
            "AND json_extract(result,'$.status') IN ('completed','partial') ORDER BY decision_index",
            (self.run_id, context.episode_id))
        execution = {'job_ref': job['job_ref'], 'registry_ref': self.jobs.config['registry_ref']}
        for saved in outcomes:
            action, outcome = json.loads(saved['action']), json.loads(saved['result'])
            args, result = action['arguments'], outcome['result']
            offset, limit = args.get('offset', 0), args['limit']
            if type(offset) is not int or type(limit) is not int or offset < 0 or limit < 0:
                raise ValueError('resource_information_result_selection_conflict')
            if limit and (offset < start or count is not None and offset + limit > start + count):
                raise ValueError('resource_information_result_selection_conflict')
            snapshot_ref = result['snapshot_ref']
            if ('snapshot_ref' in args and args['snapshot_ref'] != snapshot_ref
                    or result.get('offset') != offset or result.get('limit') != limit):
                raise ValueError('resource_information_result_selection_conflict')
            _, snapshot, actual_context = _snapshot(self.store, snapshot_ref, query_ref=job['query_ref'],
                scope=plain(context.scope), execution_context=execution)
            source = self.store.get(snapshot_ref)
            if (source.get('provider') != 'native.phmmer.parsed_snapshot'
                    or json.loads(self.store.get_artifact(source['artifact_ref'])) != snapshot
                    or snapshot.get('execution_context') != execution
                    or snapshot['database_sha256'] != self.jobs.config['reference_database']['sha256']
                    or snapshot['executable_sha256'] != self.jobs.config['executable']['sha256']):
                raise ValueError('resource_information_result_snapshot_conflict')
            for publication in result.get('publication_rows', []):
                if (set(publication) != {'ordinal', 'record_ref', 'record_type', 'source_byte_spans'}
                        or type(publication['ordinal']) is not int
                        or not offset < publication['ordinal'] <= offset + limit
                        or publication['record_ref'] not in outcome['record_refs']):
                    raise ValueError('resource_information_result_publication_conflict')
                witness = self.store.db.execute('SELECT record_ref,record_type,source_byte_spans '
                    'FROM homology_result_witnesses WHERE snapshot_ref=? AND ordinal=?',
                    (snapshot_ref, publication['ordinal'])).fetchone()
                if (witness is None or witness['record_ref'] != publication['record_ref']
                        or witness['record_type'] != publication['record_type']
                        or json.loads(witness['source_byte_spans']) != publication['source_byte_spans']
                        or self.store.get(publication['record_ref'])['record_type'] != publication['record_type']):
                    raise ValueError('resource_information_result_witness_conflict')
                for span in publication['source_byte_spans']:
                    artifact = {'native_text': snapshot['native_text_artifact'],
                        'hit_table': snapshot['hit_table_artifact']}.get(span.get('role'))
                    bounds = span.get('byte_span')
                    if (set(span) != {'role', 'artifact_ref', 'byte_span'} or artifact is None
                            or span['artifact_ref'] != artifact or not isinstance(bounds, list) or len(bounds) != 2
                            or any(type(n) is not int for n in bounds) or not 0 <= bounds[0] < bounds[1]
                            or bounds[1] > self.store.get(artifact)['size']):
                        raise ValueError('resource_information_result_span_conflict')
                rows.append({'snapshot_ref': snapshot_ref, 'query_ref': job['query_ref'],
                    'execution_context': actual_context, **deepcopy(publication)})
        return rows

    @staticmethod
    def _selector(value):
        if (not isinstance(value, dict) or set(value) - {'offset', 'limit'}
                or type(value.get('offset', 0)) is not int or value.get('offset', 0) < 0
                or value.get('limit') is not None and (type(value['limit']) is not int or value['limit'] < 0)):
            raise ValueError('invalid_resource_selector')
        return value.get('offset', 0), value.get('limit')


__all__ = ['ResourceInformation', 'HandoffInformationV1', 'OwnResultRowV1']
