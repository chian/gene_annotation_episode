"""Original own-axis received result and reference readers."""
from __future__ import annotations
KINDS = {'local': 'local', 'pbs_ssh': 'hpc'}
from gene_annotation_episode.episodic_workflow.root.a110.local_file_capture_results import LocalFileSourceResults
from pathlib import Path
from .practical_receipt_reader import PracticalReceiptReader as TerminalExecutionBehavior
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import canonical
import json
import math
from gene_annotation_episode.episodic_workflow.root.a110.communication import plain
RESULTS_VERSION = 'execution_results_assignment_v1'
TEXT = {'type': 'string', 'minLength': 1}
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import obj
RESULTS_SCHEMA = obj({'version': {'const': RESULTS_VERSION}, 'handoff_ref': TEXT, 'selector': {'type': 'object'}})
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import checked
LIMIT = {'type': 'integer', 'minimum': 1}
OFFSET = {'type': 'integer', 'minimum': 0}
NATIVE_SELECTOR_SCHEMA = obj({'paths': {'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': TEXT}, 'path': TEXT, 'offset': OFFSET, 'limit': LIMIT}, [])
from gene_annotation_episode.episodic_workflow.root.a110.practical_execution_operations import confined
from gene_annotation_episode.episodic_workflow.root.a110.local_file_capture_results import is_file_source_selector
from gene_annotation_episode.episodic_workflow.root.a110.practical_execution_state import _immutable
from gene_annotation_episode.episodic_workflow.root.a110.practical_execution_state import _read
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import digest
NATIVE_RESULT_ORIGIN = {'content_location': 'current_resource_filesystem', 'attempt_output_version': 'unverified', 'window_consistency': 'separate_reads_no_atomic_file_snapshot', 'completion_basis': 'requested_acquisition_and_observed_successful_attempt'}
import base64
from gene_annotation_episode.episodic_workflow.root.a110.local_file_capture_results import RECEIPT_VERSION as LOCAL_FILE_SOURCE_RECEIPT_VERSION
RESULT_PROVIDER = 'episode.execution_result'
from gene_annotation_episode.episodic_workflow.root.a110.domain import identity
from gene_annotation_episode.episodic_workflow.root.a110.practical_execution_records import validate_assignment
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a110.local_file_capture_results import FILE_PROVIDER as LOCAL_FILE_SOURCE_PROVIDER
from gene_annotation_episode.episodic_workflow.root.a110.practical_receipt_information import PracticalReceiptInformation

def _constraints(constraints):
    for key in ('allowed_resource_ids', 'allowed_kinds'):
        if key in constraints and (not isinstance(constraints[key], list) or any((not isinstance(item, str) or not item for item in constraints[key]))):
            raise ValueError('invalid_execution_resource_constraints')

def _delegate(self, context):
    assignment = self._validate_request(plain(context.assignment))
    return self._practical[assignment['resource_id']]

def _flux_balance_reference_access(self, context, reference, namespace):
    if self.native_flux_balance_returns is not None and self.native_flux_balance_returns.ordinary_backend is not None and (context.role in {'annotation', 'biochemical_feasibility_evidence'}) and (namespace in {None, 'artifact'}) and self.native_flux_balance_returns.resolve_received(context, reference, namespace):
        return True
    host = self.native_flux_balance_results
    if host is None or not host.owns_reference(reference):
        return None
    if namespace not in {None, 'artifact'}:
        return False
    if host.applies(context):
        if host.resolve_own(context, reference, namespace):
            return True
        selector = plain(context.assignment)['selector']
        supplied = selector.get('saved_sheet_file')
        if selector.get('mode') == 'saved_sheet_recalculation' and isinstance(supplied, dict) and (supplied.get('artifact_ref') == reference):
            self.native_flux_balance_returns.authenticate_received_saved_sheet(context, supplied)
            return True
    return self.native_flux_balance_returns.resolve_received(context, reference, namespace)

def _flux_balance_selector(assignment):
    return assignment.get('selector', {}).get('version') == 'flux_balance_result_selector_v1'

def _practical_context(self, context):
    """An internal execution view; the immutable episode request stays original."""
    from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_request_binding import is_compact_assignment, materialized_assignment
    if not is_compact_assignment(plain(context.assignment)):
        return context
    from gene_annotation_episode.episodic_workflow.root.a110.episode_bindings import BindingContext
    practical = BindingContext(context.run_id, context.episode_id, context.role, context.path, context.scope, materialized_assignment(self.store, context), context.request, context.received_record_refs)
    self.flux_balance_requests.validate_practical_history(context, practical, self._delegate(context))
    return practical

def _read_result(self, reference, scope):
    source = self.store.get(reference)
    if source.get('provider') != RESULT_PROVIDER:
        return None
    if source.get('version') == LOCAL_FILE_SOURCE_RECEIPT_VERSION:
        return self.local_file_sources.read_wrapper(reference, scope)
    raw = self.store.get_artifact(source['artifact_ref'])
    body = json.loads(raw)
    row = self._validate_result_body(body, scope)
    payload = {'provider': RESULT_PROVIDER, 'accession': 'execution_result_' + digest([body['run_id'], body['episode_id'], body['operation_key']]), 'uri': None, 'artifact_ref': source['artifact_ref'], 'text_ref': source['artifact_ref'], 'request_ref': None, 'version': body['version'], 'retrieved_at': body['observation']['observed_at']}
    expected = identity('source', {'origin': 'tool', 'record': payload})
    if reference != expected or raw != canonical(body).encode() or {key: value for key, value in source.items() if key not in {'id', 'record_type', 'origin'}} != payload:
        raise ValueError('execution_result_source_identity_conflict')
    if row['result'] is not None:
        outcome = json.loads(row['result'])
        if outcome.get('status') != 'completed' or outcome.get('result') != body or reference not in outcome.get('record_refs', []):
            raise ValueError('execution_result_saved_outcome_conflict')
    return body

def _result_directory(self, context, *, create=True):
    if type(create) is not bool:
        raise TypeError('execution_results_directory_create_boolean_required')
    directory = self.directory / 'execution-results' / digest([context.run_id, context.episode_id])
    manifest = {'run_id': context.run_id, 'episode_id': context.episode_id, 'assignment': plain(context.assignment), 'scope': plain(context.scope)}
    if create:
        directory.mkdir(parents=True, exist_ok=True)
        _immutable(directory / 'assignment.json', manifest)
    else:
        try:
            existing = _read(directory / 'assignment.json')
        except FileNotFoundError as error:
            raise ValueError('execution_results_assignment_control_missing') from error
        if canonical(existing) != canonical(manifest):
            raise ValueError('practical_immutable_record_conflict')
    return directory

def _retained_flux_balance_target(self, context, assignment, scope):
    if not self._flux_balance_selector(assignment):
        return None
    if self.native_flux_balance_results is None:
        raise ValueError('native_flux_balance_results_binding_unavailable')
    return self.native_flux_balance_results.retained_target(context, assignment, scope)

def _selected_result_action(self, episode_id, key, name, arguments):
    prefix = self.run_id + ':' + episode_id + ':'
    suffix = key.removeprefix(prefix)
    if not key.startswith(prefix) or not suffix.isdecimal() or str(int(suffix)) != suffix:
        raise ValueError('execution_result_selected_action_missing')
    row = self.store.db.execute('SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?', (self.run_id, episode_id, int(suffix))).fetchone()
    if row is None:
        raise ValueError('execution_result_selected_action_missing')
    action = json.loads(row['action'])
    if action.get('kind') != 'tool' or action.get('tool') != name or action.get('arguments') != arguments:
        raise ValueError('execution_result_selected_action_conflict')
    return row

def _selection(self, context, supplied=None):
    if supplied is None and self.services is not None:
        callback = getattr(self.services, 'record_selection', None)
        supplied = None if callback is None else callback(context)
    if supplied is None:
        from gene_annotation_episode.episodic_workflow.root.a110.episode_receipts import EpisodeReceipts
        table = self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_receipt_inheritance'").fetchone()
        if table and self.store.db.execute('SELECT 1 FROM runtime_receipt_inheritance WHERE run_id=? AND episode_id=?', (self.run_id, context.episode_id)).fetchone():
            receipts = EpisodeReceipts(self.store, self.run_id)
            supplied = {'run_id': self.run_id, 'episode_id': context.episode_id, 'known_record_refs': list(receipts.known(context.episode_id)), 'initial_known_record_refs': list(receipts.known(context.episode_id, baseline=True))}
        else:
            rows = self.store.db.execute('SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? AND result IS NOT NULL ORDER BY decision_index', (self.run_id, context.episode_id))
            supplied = {'run_id': self.run_id, 'episode_id': context.episode_id, 'known_record_refs': list(dict.fromkeys((ref for row in rows for ref in json.loads(row[0]).get('record_refs', [])))), 'initial_known_record_refs': []}
    supplied = plain(supplied)
    if supplied.get('run_id') != self.run_id or supplied.get('episode_id') != context.episode_id:
        raise ValueError('execution_receiver_identity_conflict')
    for key in ('known_record_refs', 'initial_known_record_refs'):
        if not isinstance(supplied.get(key), list) or any((not isinstance(ref, str) or not ref for ref in supplied[key])):
            raise ValueError('execution_receiver_references_required')
    if not set(supplied['initial_known_record_refs']) <= set(supplied['known_record_refs']):
        raise ValueError('execution_initial_references_must_be_known')
    return supplied

def _selector(self, assignment, target):
    if is_file_source_selector(assignment.get('selector')):
        return self.local_file_sources.selector(assignment, target)
    native_fba = 'native_flux_balance' in target.get('assignment', {}).get('requested_job', {})
    if self._flux_balance_selector(assignment) or native_fba:
        if self.native_flux_balance_results is None:
            raise ValueError('native_flux_balance_results_binding_unavailable')
        if not native_fba or target.get('resource_kind') != 'local':
            raise ValueError('flux_balance_result_target_conflict')
        from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_result_selection import validate_flux_balance_result_selector
        selector = validate_flux_balance_result_selector(assignment['selector'])
        return validate_flux_balance_result_selector(selector, job=target['assignment']['requested_job']) if selector['mode'] == 'native_result' else selector
    value = checked(assignment['selector'], NATIVE_SELECTOR_SCHEMA, 'invalid_execution_native_selector')
    paths = list(value.get('paths', []))
    if 'path' in value:
        if value['path'] in paths:
            raise ValueError('ambiguous_execution_results_selector')
        paths.append(value['path'])
    if not paths or (('offset' in value or 'limit' in value) and 'path' not in value):
        raise ValueError('execution_results_paths_required')
    for path in paths:
        confined(path, target['assignment']['workspace'])
    return value

def _target(self, context):
    assignment = checked(context.assignment, RESULTS_SCHEMA, 'invalid_execution_results_assignment')
    fba = self._retained_flux_balance_target(context, assignment, context.scope)
    if fba is not None:
        return fba
    return self.job_progress_provider.targets.read_target(assignment['handoff_ref'], context.scope)

def _validate_request(self, value, *, resource_id=None):
    resource_id = resource_id or value.get('resource_id')
    if resource_id not in self.resources:
        raise ValueError('execution_resource_not_bound')
    config = self.resources[resource_id]
    kind = KINDS[config['kind']]
    from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_request_binding import is_compact_assignment, validate_compact_assignment
    if is_compact_assignment(value):
        if kind != 'local' or not config.get('native_flux_balance'):
            raise ValueError('flux_balance_request_binding_unavailable')
        return validate_compact_assignment(value, resource_id)
    value = validate_assignment(value)
    if value.get('resource_id', resource_id) != resource_id:
        raise ValueError('execution_resource_identity_conflict')
    if value['resource_kind'] != kind:
        raise ValueError('execution_resource_kind_conflict')
    confined(value['workspace'], config['workspace'])
    operations = self._practical[resource_id]._operations(kind)
    validator = getattr(operations, 'validate_assignment', None)
    if validator is not None:
        validator({**value, 'resource_id': resource_id})
    return value

def _validate_result_body(self, body, scope):
    fields = {'version', 'run_id', 'episode_id', 'scope', 'assignment', 'operation_key', 'tool_name', 'arguments', 'target', 'observation', 'windows', 'failures', 'acquisition_origin'}
    if not isinstance(body, dict) or set(body) != fields or body['version'] != 'execution_result_information_v2' or (body['run_id'] != self.run_id) or (body['acquisition_origin'] != NATIVE_RESULT_ORIGIN):
        raise ValueError('invalid_execution_result_information')
    self.store.validate_scope(body['scope'], parent_scope=plain(scope))
    target = self.job_progress_provider.targets.read_target(body['assignment']['handoff_ref'], scope)
    if canonical(target) != canonical(body['target']):
        raise ValueError('execution_result_original_target_conflict')
    selector = self._selector(body['assignment'], target)
    requested = self._windows(selector)
    row = self._selected_result_action(body['episode_id'], body['operation_key'], body['tool_name'], body['arguments'])
    episode = self.store.db.execute('SELECT request,path FROM runtime_episodes WHERE run_id=? AND episode_id=?', (self.run_id, body['episode_id'])).fetchone()
    if episode is not None:
        message = json.loads(episode['request'])['message']
        if message.get('episode_assignment') != body['assignment'] or message['scope'] != body['scope'] or json.loads(episode['path'])[-1][0] != 'results':
            raise ValueError('execution_result_original_assignment_conflict')
    for window in body['windows']:
        if window['path'] not in requested:
            raise ValueError('execution_result_selector_conflict')
        raw = base64.b64decode(window['bytes_base64'], validate=True)
        start, length = requested[window['path']]
        if window['offset'] < start or window['returned_bytes'] != len(raw) or (length is not None and window['offset'] + len(raw) > start + length) or (window['size_bytes'] < 0):
            raise ValueError('execution_result_window_conflict')
    directory = self.directory / 'execution-results' / digest([self.run_id, body['episode_id']])
    path = directory / (digest(body['operation_key']) + '.receipt.json')
    if not path.exists() or canonical(_read(path)) != canonical(body):
        raise ValueError('execution_result_original_receipt_conflict')
    return row

def _windows(self, selector):
    values = {path: (0, None) for path in selector.get('paths', [])}
    if 'path' in selector:
        values[selector['path']] = (selector.get('offset', 0), selector.get('limit'))
    return values

def fact_sources(self, role):
    values = {}
    if role == 'results':
        from gene_annotation_episode.episodic_workflow.root.a110.local_file_capture_results import SOURCE_REFS_SCHEMA, OUTCOMES_SCHEMA
        for source, schema, meaning in (('execution_file_source_refs', SOURCE_REFS_SCHEMA, 'Source references for selected local file streams retained by this results episode.'), ('execution_file_capture_outcomes', OUTCOMES_SCHEMA, 'Recorded selected-file availability, original job status and file-custody qualifications.')):
            values[source] = {'type': 'array', 'meaning': meaning, 'report_schema': deepcopy(schema)}
        if self.native_flux_balance_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_return_views import fba_fact_sources
            sources = fba_fact_sources()
            values.update({name: sources[name] for name in ('flux_balance_measurements', 'flux_balance_saved_sheets', 'flux_balance_failures')})
    if role in {'launch_local', 'launch_hpc'}:
        values.update(TerminalExecutionBehavior.fact_sources(None, role))
    for key, namespace, meaning in (('execution_handoff_refs', 'execution_handoff', 'Qualified original handoff sources available to this episode.'), ('execution_result_refs', 'execution_result', 'Qualified requested result acquisitions available to this episode.')):
        values[key] = {'type': 'array', 'meaning': meaning, 'report_schema': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': namespace}, 'x-source': key}}
    values['execution_completed'] = {'type': 'boolean', 'meaning': 'Whether this assignment has actual verified endpoint information.'}
    origins = [NATIVE_RESULT_ORIGIN]
    if self.native_flux_balance_results is not None:
        from gene_annotation_episode.episodic_workflow.root.a110.native_flux_balance_results import ORIGIN as fba_origin
        origins.append(fba_origin)
    values['execution_result_origin'] = {'type': ['object', 'null'], 'meaning': 'Actual acquisition semantics of retained results.', 'report_schema': {**obj({key: {'type': 'string', 'enum': list(dict.fromkeys((origin[key] for origin in origins)))} for key in NATIVE_RESULT_ORIGIN}), 'type': ['object', 'null'], 'x-source': 'execution_result_origin'}}
    return values

def received_execution_form_references(self, context, form, schema, operation_key):
    references = self.local_file_sources.admit_return(context, form, schema, operation_key)
    if self.native_flux_balance_returns is not None:
        references.extend(self.native_flux_balance_returns.record_admission(context, form, schema, operation_key))
    for name, declared in plain(schema).get('properties', {}).items():
        if declared.get('x-source') in {'execution_handoff_refs', 'execution_result_refs', 'practical_receipt_refs'}:
            for reference in form[name]:
                namespace = declared['items'].get('x-reference-namespace')
                if not self.resolve(context, reference, namespace):
                    raise ValueError('execution_received_reference_unqualified')
                references.append(reference)
    return list(dict.fromkeys(references))

def received_execution_closure_facts(self, context):
    if context.role not in {'annotation', 'biochemical_feasibility_evidence'}:
        return {}
    schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
    if self.native_flux_balance_returns is not None and schema.get('properties') is not None:
        return self.native_flux_balance_returns.ordinary_closure_facts(context, schema)
    return {}

def received_execution_facts(self, context):
    schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
    result = {}
    if context.role in {'annotation', 'biochemical_feasibility_evidence'}:
        requested = {node.get('x-source') for node in schema.get('properties', {}).values()}
        if 'execution_file_source_refs' in requested:
            result['execution_file_source_refs'] = self.local_file_sources.received_sources(context)
        if 'execution_file_capture_outcomes' in requested:
            result['execution_file_capture_outcomes'] = self.local_file_sources.received_outcomes(context)
        if self.native_flux_balance_returns is not None and schema.get('properties') is not None:
            result.update(self.native_flux_balance_returns.facts_for_closure(context, schema))
    return result

def received_execution_sources(self, role):
    result = {}
    if role in {'annotation', 'biochemical_feasibility_evidence'}:
        for source in ('execution_file_source_refs', 'execution_file_capture_outcomes'):
            definition = self.fact_sources('results').get(source)
            if definition is not None:
                result[source] = deepcopy(definition)
        if self.native_flux_balance_returns is not None:
            from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_return_views import fba_fact_sources
            sources = fba_fact_sources()
            if self.native_flux_balance_returns.ordinary_backend is None:
                sources = {name: sources[name] for name in ('flux_balance_measurements', 'flux_balance_saved_sheets', 'flux_balance_failures')}
            result.update(sources)
    return result

def resolve(self, context, reference, namespace):
    try:
        fba = self._flux_balance_reference_access(context, reference, namespace)
        if fba is not None:
            return fba
        if namespace in {'execution_handle', 'execution'}:
            from gene_annotation_episode.episodic_workflow.root.a110.episode_bindings import reference_in_context
            return bool(self.services is not None and reference_in_context(self.services, context, reference, namespace))
        if context.role in {'launch_local', 'launch_hpc'} and namespace == 'practical_receipt' and (not reference.startswith('source_')):
            return self._delegate(context).resolve(self._practical_context(context), reference, namespace)
        source = self.store.get(reference)
        if source.get('provider') == LOCAL_FILE_SOURCE_PROVIDER:
            return namespace in {None, 'source'} and self.local_file_sources.read_source(reference, context.scope) is not None
        if source.get('provider') == RESULT_PROVIDER:
            if source.get('version') in {'native_blast_utility_bundle_v1', 'native_blast_masking_bundle_v1', 'native_hmmer_bundle_v1', 'native_blast_bundle_v1', 'native_blast_database_bundle_v1', 'native_blast_standard_database_bundle_v1', 'native_infernal_bundle_v1', 'native_infernal_preparation_bundle_v1', 'native_hmmer_preparation_bundle_v1', 'native_protein_structure_bundle_v1', 'native_rna_structure_bundle_v1'}:
                return False
            if namespace not in {None, 'source', 'execution_result'}:
                return False
            body = self._read_result(reference, context.scope)
            return bool(body['windows']) if namespace == 'execution_result' else True
        if namespace in {None, 'source', 'execution_handoff'}:
            try:
                target = self.job_progress_provider.targets.read_target(reference, context.scope)
                return namespace != 'execution_handoff' or self.job_progress_provider.targets.returnable_handoff(target)
            except ValueError:
                if namespace == 'execution_handoff':
                    return False
        if PracticalReceiptInformation(self.store, self.run_id).resolve(context, reference, namespace):
            return True
        if source.get('provider') == 'episode.practical_receipt':
            return False
        if self.services is not None:
            from gene_annotation_episode.episodic_workflow.root.a110.episode_bindings import reference_in_context
            return bool(reference_in_context(self.services, context, reference, namespace))
        kind = source['record_type']
        return bool(self.store.reference_subset([reference], plain(context.scope)) and (namespace in {None, kind} or (namespace == 'subject' and kind in {'input', 'feature', 'product', 'read_subject'})))
    except (ValueError, KeyError, OSError):
        return False

def resolve_received_execution_reference(self, context, reference, namespace):
    captured = self.local_file_sources.reference_access(context, reference, namespace)
    if captured is not None:
        return captured
    return self._flux_balance_reference_access(context, reference, namespace)

def validate_received_execution_report(self, context, form, schema):
    self.local_file_sources.validate_received_report(context, form, schema)
    if self.native_flux_balance_returns is not None:
        self.native_flux_balance_returns.validate_received_report(context, form, schema)
