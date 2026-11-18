"""Original own-axis received result and reference readers."""
from __future__ import annotations
KINDS = {'local': 'local', 'pbs_ssh': 'hpc', 'hmmer_api': 'api', 'api': 'api'}
from gene_annotation_episode.episodic_workflow.root.a107.local_file_capture_results import LocalFileSourceResults
from pathlib import Path
from .practical_receipt_reader import PracticalReceiptReader as TerminalExecutionBehavior
from gene_annotation_episode.episodic_workflow.root.a107.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.a107.a107_execution_bindings import install_preparation_result_readers
from gene_annotation_episode.episodic_workflow.root.a107.a107_execution_bindings import install_primary_result_readers
import json
import math
from gene_annotation_episode.episodic_workflow.root.a107.communication import plain
from gene_annotation_episode.episodic_workflow.root.a107.a107_execution_bindings import validate_preparation_resource_binding
from gene_annotation_episode.episodic_workflow.root.a107.a107_execution_bindings import validate_primary_resource_bindings
RESULTS_VERSION = 'execution_results_assignment_v1'
TEXT = {'type': 'string', 'minLength': 1}
from gene_annotation_episode.episodic_workflow.root.a107.execution_contracts import obj
RESULTS_SCHEMA = obj({'version': {'const': RESULTS_VERSION}, 'handoff_ref': TEXT, 'selector': {'type': 'object'}})
from gene_annotation_episode.episodic_workflow.root.a107.execution_contracts import checked
LIMIT = {'type': 'integer', 'minimum': 1}
OFFSET = {'type': 'integer', 'minimum': 0}
NATIVE_SELECTOR_SCHEMA = obj({'paths': {'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': TEXT}, 'path': TEXT, 'offset': OFFSET, 'limit': LIMIT}, [])
from gene_annotation_episode.episodic_workflow.root.a107.practical_execution_operations import confined
from gene_annotation_episode.episodic_workflow.root.a107.local_file_capture_results import is_file_source_selector
from gene_annotation_episode.episodic_workflow.root.a107.native_blast_database_acquisition import is_native_blast_database_target
from gene_annotation_episode.episodic_workflow.root.a107.native_blast_masking_acquisition import is_native_blast_masking_target
from gene_annotation_episode.episodic_workflow.root.a107.native_blast_acquisition import is_native_blast_target
from gene_annotation_episode.episodic_workflow.root.a107.native_blast_utility_acquisition import is_native_blast_utility_target
from gene_annotation_episode.episodic_workflow.root.a107.native_hmmer_preparation_acquisition import is_native_hmmer_preparation_target
from gene_annotation_episode.episodic_workflow.root.a107.native_hmmer_acquisition import is_native_hmmer_target
from gene_annotation_episode.episodic_workflow.root.a107.native_infernal_preparation_acquisition import is_native_infernal_preparation_target
from gene_annotation_episode.episodic_workflow.root.a107.native_infernal_acquisition import is_native_infernal_target
from gene_annotation_episode.episodic_workflow.root.a107.native_rna_structure_acquisition import is_native_rna_structure_target
from gene_annotation_episode.episodic_workflow.root.a107.native_blast_standard_database_acquisition import is_standard_blast_database_target
from gene_annotation_episode.episodic_workflow.root.a107.practical_execution_state import _immutable
from gene_annotation_episode.episodic_workflow.root.a107.practical_execution_state import _read
from gene_annotation_episode.episodic_workflow.root.a107.execution_contracts import digest
NATIVE_RESULT_ORIGIN = {'content_location': 'current_resource_filesystem', 'attempt_output_version': 'unverified', 'window_consistency': 'separate_reads_no_atomic_file_snapshot', 'completion_basis': 'requested_acquisition_and_observed_successful_attempt'}
import base64
from gene_annotation_episode.episodic_workflow.root.a107.local_file_capture_results import RECEIPT_VERSION as LOCAL_FILE_SOURCE_RECEIPT_VERSION
RESULT_PROVIDER = 'episode.execution_result'
from gene_annotation_episode.episodic_workflow.root.a107.domain import identity
from gene_annotation_episode.episodic_workflow.root.a107.practical_execution_records import validate_assignment
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a107.a107_blast_execution import BLAST_GRADED_RETURN_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a107.a107_blast_execution import BLAST_GRADED_RETURN_SOURCE
from gene_annotation_episode.episodic_workflow.root.a107.local_file_capture_results import FILE_PROVIDER as LOCAL_FILE_SOURCE_PROVIDER
from gene_annotation_episode.episodic_workflow.root.a107.practical_receipt_information import PracticalReceiptInformation
from ..received_execution_targets import is_expression_nmf_selector as _expression_nmf_selector, is_masking_selector as _masking_selector, retained_expression_nmf_target as _retained_expression_nmf_target, retained_masking_target as _retained_masking_target, retained_utility_target as _retained_utility_target, selected_result_action as _selected_result_action, received_execution_target as _target, is_utility_selector as _utility_selector
from ..blast_pairwise_return_schema import blast_pairwise_reference_source as _blast_reference_source

def _appservice_sources():
    from gene_annotation_episode.episodic_workflow.root.a107.bvbrc_homology_returns import homology_fact_sources
    return {**homology_fact_sources(), 'bvbrc_appservice_support_refs': {'type': 'array', 'meaning': 'Received homology service preparation receipts.', 'report_schema': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'bvbrc_appservice_support'}, 'x-source': 'bvbrc_appservice_support_refs'}}}

def _comparison_selector(assignment):
    return assignment.get('selector', {}).get('version') == 'native_rna_structure_comparison_selector_v1'

def _delegate(self, context):
    assignment = self._validate_request(plain(context.assignment))
    return self.api_execution if context.role == 'launch_api' else self._practical[assignment['resource_id']]

def _expression_nmf_reference_access(self, context, reference, namespace):
    host = self.native_expression_nmf_results
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
            self.native_expression_nmf_returns.authenticate_received_saved_sheet(context, supplied)
            return True
    return self.native_expression_nmf_returns.resolve_received(context, reference, namespace)

def _has_appservice(self):
    return self.api_execution is not None and any((service.service == 'bvbrc_appservice' and ('bvbrc_homology', '1') in service.scientific_adapters for service in self.api_execution.services.values()))

def _has_rfam(self):
    return self.api_execution is not None and any((service.service == 'rfam_batch' for service in self.api_execution.services.values()))

def _has_uniprot(self):
    return self.api_execution is not None and any((service.service == 'uniprot' for service in self.api_execution.services.values()))

def _infernal_reference_source():
    return {'type': 'array', 'meaning': 'Infernal source, observation and model references actually returned through this episode boundary. These references alone do not deliver unrequested numerical rows.', 'report_schema': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'execution_result'}, 'x-source': 'execution_infernal_result_refs'}}

def _masking_reference_access(self, context, reference, namespace):
    access = self.native_blast_masking_results.retained_reference_access(context, reference, namespace)
    if access is not None:
        return access
    from gene_annotation_episode.episodic_workflow.root.a107.sequence_masking_result_views import IDENTIFIER_NAMESPACES
    if self.native_blast_masking_results.applies(context):
        resolved = self.native_blast_masking_results.resolve(context, reference, namespace)
    else:
        resolved = self.native_blast_masking_returns.resolve_received(context, reference, namespace)
    if resolved:
        return True
    return False if namespace in IDENTIFIER_NAMESPACES else None

def _practical_context(self, context):
    return context

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

def _selection(self, context, supplied=None):
    if supplied is None and self.services is not None:
        callback = getattr(self.services, 'record_selection', None)
        supplied = None if callback is None else callback(context)
    if supplied is None:
        from gene_annotation_episode.episodic_workflow.root.a107.episode_receipts import EpisodeReceipts
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
    if self._masking_selector(assignment) or is_native_blast_masking_target(target):
        if not is_native_blast_masking_target(target) or target.get('resource_kind') != 'local':
            raise ValueError('native_blast_masking_result_target_conflict')
        from gene_annotation_episode.episodic_workflow.root.a107.sequence_masking_result_views import validate_masking_result_selector
        return validate_masking_result_selector(assignment['selector'], operation=target['assignment']['requested_job']['native_blast_masking']['operation'])
    if self._utility_selector(assignment) or is_native_blast_utility_target(target):
        if not is_native_blast_utility_target(target) or target.get('resource_kind') != 'local':
            raise ValueError('native_blast_utility_result_target_conflict')
        from gene_annotation_episode.episodic_workflow.root.a107.blast_utility_result_views import validate_blast_utility_result_selector
        return validate_blast_utility_result_selector(assignment['selector'], operation=target['assignment']['requested_job']['native_blast_utility']['operation'])
    native_nmf = 'native_expression_nmf' in target.get('assignment', {}).get('requested_job', {})
    if self._expression_nmf_selector(assignment) or native_nmf:
        if self.native_expression_nmf_results is None:
            raise ValueError('native_expression_nmf_results_binding_unavailable')
        if not native_nmf or target.get('resource_kind') != 'local':
            raise ValueError('expression_nmf_result_target_conflict')
        from gene_annotation_episode.episodic_workflow.root.a107.expression_nmf_result_contracts import validate_expression_nmf_result_selector
        return validate_expression_nmf_result_selector(assignment['selector'], job=target['assignment']['requested_job']['native_expression_nmf'])
    if self._comparison_selector(assignment):
        if self.rna_structure_comparison_results is None:
            raise ValueError('rna_comparison_results_binding_unavailable')
        if not is_native_rna_structure_target(target):
            raise ValueError('rna_comparison_anchor_required')
        from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_comparison_contracts import validate_rna_comparison_selector
        return validate_rna_comparison_selector(assignment['selector'])
    if is_native_rna_structure_target(target):
        if self.native_rna_structure_results is None:
            raise ValueError('native_rna_structure_results_binding_unavailable')
        from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_result_views import validate_rna_structure_result_selector
        return validate_rna_structure_result_selector(assignment['selector'], mode=target['assignment']['requested_job']['native_rna_structure']['mode'])
    if target['resource_kind'] == 'api':
        return self.api_execution.validate_result_selector(target, assignment['selector'])
    if is_standard_blast_database_target(target):
        if self.native_blast_standard_database_results is None:
            raise ValueError('native_blast_standard_database_results_binding_unavailable')
        from gene_annotation_episode.episodic_workflow.root.a107.native_blast_standard_database_result_views import validate_standard_blast_database_selector
        return validate_standard_blast_database_selector(assignment['selector'], program=target['assignment']['requested_job']['native_blast_standard_database']['program'])
    if is_native_blast_database_target(target):
        if self.native_blast_database_results is None:
            raise ValueError('native_blast_database_results_binding_unavailable')
        from gene_annotation_episode.episodic_workflow.root.a107.native_blast_database_result_views import validate_native_blast_database_result_selector
        return validate_native_blast_database_result_selector(assignment['selector'], program=target['assignment']['requested_job']['native_blast_database']['program'])
    if is_native_hmmer_preparation_target(target):
        if self.native_hmmer_preparation_results is None:
            raise ValueError('native_hmmer_preparation_results_binding_unavailable')
        from gene_annotation_episode.episodic_workflow.root.a107.hmmer_preparation_result_views import validate_preparation_result_selector
        job = target['assignment']['requested_job']['native_hmmer_preparation']
        return validate_preparation_result_selector(assignment['selector'], program=job['program'], mode=job['mode'])
    if is_native_hmmer_target(target):
        from gene_annotation_episode.episodic_workflow.root.a107.hmmer_native_result_views import validate_native_hmmer_result_selector
        return validate_native_hmmer_result_selector(assignment['selector'], program=target['assignment']['requested_job']['native_hmmer']['program'])
    if is_native_blast_target(target):
        if self.native_blast_results is None:
            raise ValueError('native_blast_results_binding_unavailable')
        from gene_annotation_episode.episodic_workflow.root.a107.blast_pairwise_result_views import validate_native_blast_result_selector
        return validate_native_blast_result_selector(assignment['selector'], program=target['assignment']['requested_job']['native_blast']['program'])
    if is_native_infernal_target(target):
        if self.native_infernal_results is None:
            raise ValueError('native_infernal_results_binding_unavailable')
        from gene_annotation_episode.episodic_workflow.root.a107.infernal_native_result_views import validate_native_infernal_result_selector
        return validate_native_infernal_result_selector(assignment['selector'], program=target['assignment']['requested_job']['native_infernal']['program'])
    if is_native_infernal_preparation_target(target):
        if self.native_infernal_preparation_results is None:
            raise ValueError('native_infernal_preparation_results_binding_unavailable')
        from gene_annotation_episode.episodic_workflow.root.a107.infernal_preparation_result_views import validate_preparation_result_selector
        job = target['assignment']['requested_job']['native_infernal_preparation']
        return validate_preparation_result_selector(assignment['selector'], program=job['program'], mode=job['mode'])
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

def _utility_reference_access(self, context, reference, namespace):
    access = self.native_blast_utility_results.retained_reference_access(context, reference, namespace)
    if access is not None:
        return access
    from gene_annotation_episode.episodic_workflow.root.a107.blast_utility_result_views import IDENTIFIER_NAMESPACES
    if self.native_blast_utility_results.applies(context):
        resolved = self.native_blast_utility_results.resolve(context, reference, namespace)
    else:
        resolved = self.native_blast_utility_returns.resolve_received(context, reference, namespace)
    if resolved:
        return True
    return False if namespace in IDENTIFIER_NAMESPACES else None

def _validate_request(self, value, *, resource_id=None):
    resource_id = resource_id or value.get('resource_id')
    if resource_id not in self.resources:
        raise ValueError('execution_resource_not_bound')
    config = self.resources[resource_id]
    kind = KINDS[config['kind']]
    value = self.api_execution.validate_assignment(value) if kind == 'api' else validate_assignment(value)
    if value.get('resource_id', resource_id) != resource_id:
        raise ValueError('execution_resource_identity_conflict')
    if kind != 'api':
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
    from gene_annotation_episode.episodic_workflow.root.a107.hmmer_native_result_views import native_hmmer_fact_sources
    values = native_hmmer_fact_sources()
    if role == 'results':
        from gene_annotation_episode.episodic_workflow.root.a107.local_file_capture_results import SOURCE_REFS_SCHEMA, OUTCOMES_SCHEMA
        for source, schema, meaning in (('execution_file_source_refs', SOURCE_REFS_SCHEMA, 'Source references for selected local file streams actually retained by this results episode; no producing-execution or atomic-version identity is established.'), ('execution_file_capture_outcomes', OUTCOMES_SCHEMA, 'Recorded selected-file availability, original job status and file-custody qualifications; successful byte retention alone does not establish execution success or closed writers.')):
            values[source] = {'type': 'array', 'meaning': meaning, 'report_schema': deepcopy(schema)}
    from gene_annotation_episode.episodic_workflow.root.a107.sequence_masking_result_views import masking_fact_sources
    values.update(masking_fact_sources())
    from gene_annotation_episode.episodic_workflow.root.a107.blast_utility_result_views import blast_utility_fact_sources
    values.update(blast_utility_fact_sources())
    if self._has_uniprot() and role == 'results':
        from gene_annotation_episode.episodic_workflow.root.a107.uniprot_return_contracts import uniprot_fact_sources
        values.update(uniprot_fact_sources())
    if self.rna_structure_comparison_results is not None and role == 'results':
        from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_comparison_views import rna_comparison_fact_sources
        values.update(rna_comparison_fact_sources())
    if self.native_expression_nmf_results is not None and role == 'results':
        from gene_annotation_episode.episodic_workflow.root.a107.expression_nmf_return_views import expression_nmf_fact_sources
        values.update(expression_nmf_fact_sources())
    if self.native_rna_structure_results is not None:
        from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_result_views import rna_structure_fact_sources
        values.update(rna_structure_fact_sources())
    if self.native_infernal_preparation_results is not None:
        from gene_annotation_episode.episodic_workflow.root.a107.infernal_preparation_result_views import preparation_fact_sources
        values.update(preparation_fact_sources())
    if self.native_infernal_results is not None:
        from gene_annotation_episode.episodic_workflow.root.a107.infernal_native_result_views import native_infernal_fact_sources
        values.update(native_infernal_fact_sources())
        values['execution_infernal_result_refs'] = self._infernal_reference_source()
    if self.native_blast_standard_database_results is not None:
        from gene_annotation_episode.episodic_workflow.root.a107.native_blast_standard_database_result_views import standard_blast_database_fact_sources
        values.update(standard_blast_database_fact_sources())
    if self.native_blast_database_results is not None:
        from gene_annotation_episode.episodic_workflow.root.a107.native_blast_database_result_views import native_blast_database_fact_sources
        values.update(native_blast_database_fact_sources())
    if self.native_hmmer_preparation_results is not None:
        from gene_annotation_episode.episodic_workflow.root.a107.hmmer_preparation_result_views import preparation_fact_sources
        values.update(preparation_fact_sources())
    if self.native_blast_results is not None:
        from gene_annotation_episode.episodic_workflow.root.a107.blast_pairwise_result_views import native_blast_fact_sources
        values.update(native_blast_fact_sources())
        values['execution_blast_pairwise_result_refs'] = self._blast_reference_source()
    if self._has_rfam() and role == 'results':
        from gene_annotation_episode.episodic_workflow.root.a107.rfam_batch_returns import rfam_fact_sources
        values.update(rfam_fact_sources())
    if self._has_appservice():
        values.update(self._appservice_sources())
    if role in {'launch_local', 'launch_hpc'}:
        values.update(TerminalExecutionBehavior.fact_sources(None, role))
    for key, namespace, meaning in (('execution_handoff_refs', 'execution_handoff', 'Qualified original handoff sources actually available to this episode, including authenticated original failed native database attempts for partial-output acquisition; failed attempts do not establish a successful endpoint.'), ('execution_result_refs', 'execution_result', 'Qualified actual requested result acquisitions available to this episode. Generic native windows retain current-filesystem observations. Explicit BLAST/HMMER producer bundles retain original attempt outputs matched by digest and requested numerical facts.')):
        values[key] = {'type': 'array', 'meaning': meaning, 'report_schema': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': namespace}, 'x-source': key}}
    values['execution_completed'] = {'type': 'boolean', 'meaning': 'Whether this assignment has actual verified endpoint information. Generic native results mean requested current-filesystem acquisition plus independently observed successful exact execution, without a producing-attempt or atomic-version claim. Yielding alone is false.'}
    from gene_annotation_episode.episodic_workflow.root.a107.native_hmmer_acquisition import ORIGIN as hmmer_origin
    origins = [NATIVE_RESULT_ORIGIN, hmmer_origin]
    if self.native_expression_nmf_results is not None:
        from gene_annotation_episode.episodic_workflow.root.a107.native_expression_nmf_results import ORIGIN as nmf_origin
        origins.append(nmf_origin)
    values['execution_result_origin'] = {'type': ['object', 'null'], 'meaning': 'Actual acquisition semantics of retained results: current-file windows, original producer output, or explicitly received saved numerical data. No qualified retained data yields null.', 'report_schema': {**obj({key: {'type': 'string', 'enum': list(dict.fromkeys((origin[key] for origin in origins)))} for key in NATIVE_RESULT_ORIGIN}), 'type': ['object', 'null'], 'x-source': 'execution_result_origin'}}
    from gene_annotation_episode.episodic_workflow.root.a107.blast_result_views import BLAST_HSP_FACT_SCHEMA
    values['execution_blast_hsps'] = {'type': 'array', 'meaning': 'Optional explicitly requested native measurements for all published HSPs of this acquired result. No automatic ranking, top-N or significance filter. target_coverage is native reference/hit coverage, not original gene-target coverage. HSP/reference records support later scoped reads; selected HSP references can instead be returned through a parent-chosen typed field. No functional assignment or annotation score.', 'report_schema': {**deepcopy(BLAST_HSP_FACT_SCHEMA), 'x-source': 'execution_blast_hsps'}}
    if role == 'results' and self.api_execution is not None and any((service.service == 'ncbi_blast' for service in self.api_execution.services.values())):
        values[BLAST_GRADED_RETURN_SOURCE] = {'type': 'array', 'meaning': 'Retained output of the original BLAST database grader. Each artifact contains the full grader sheet and probabilities; query and any parent database constraint are checked against the original submission and native report.', 'report_schema': deepcopy(BLAST_GRADED_RETURN_SCHEMA)}
    return values

def received_execution_form_references(self, context, form, schema, operation_key):
    from gene_annotation_episode.episodic_workflow.root.a107.hmmer_native_result_views import FAMILY_SOURCES
    references = []
    native_references = set()
    references.extend(self.local_file_sources.admit_return(context, form, schema, operation_key))
    if self._has_uniprot():
        references.extend(self.api_execution.uniprot_returns.record_admission(context, form, schema, operation_key))
    admitted = self.native_blast_masking_returns.record_admission(context, form, schema, operation_key)
    native_references.update(admitted)
    references.extend(admitted)
    admitted = self.native_blast_utility_returns.record_admission(context, form, schema, operation_key)
    native_references.update(admitted)
    references.extend(admitted)
    for adapter in (self.rna_structure_comparison_returns, self.native_rna_structure_returns, self.native_expression_nmf_returns, self.native_infernal_preparation_returns, self.native_infernal_returns):
        if adapter is not None:
            admitted = adapter.record_admission(context, form, schema, operation_key)
            native_references.update(admitted)
            references.extend(admitted)
    if self.native_blast_standard_database_returns is not None:
        admitted = self.native_blast_standard_database_returns.record_admission(context, form, schema, operation_key)
        native_references.update(admitted)
        references.extend(admitted)
    if self.native_blast_database_returns is not None:
        admitted = self.native_blast_database_returns.record_admission(context, form, schema, operation_key)
        native_references.update(admitted)
        references.extend(admitted)
    if self.native_hmmer_preparation_returns is not None:
        admitted = self.native_hmmer_preparation_returns.record_admission(context, form, schema, operation_key)
        native_references.update(admitted)
        references.extend(admitted)
    if self.native_blast_returns is not None:
        admitted = self.native_blast_returns.record_admission(context, form, schema, operation_key)
        native_references.update(admitted)
        references.extend(admitted)
    if self._has_rfam():
        references.extend(self.api_execution.rfam_returns.record_admission(context, form, schema, operation_key))
    if self._has_appservice():
        references.extend(self.api_execution.homology_returns.record_admission(context, form, schema, operation_key))
    for name, declared in plain(schema).get('properties', {}).items():
        if declared.get('x-source') in FAMILY_SOURCES.values():
            for row in form[name]:
                for reference in [row['source_ref'], row['observation_ref'], *row['reference_refs']]:
                    if reference is None:
                        continue
                    if not self.resolve(context, reference, 'execution_result'):
                        raise ValueError('execution_received_reference_unqualified')
                    references.append(reference)
        if declared.get('x-source') == 'execution_blast_hsps':
            for row in form[name]:
                for field in ('hsp_ref', 'reference_ref'):
                    reference = row[field]
                    if not self.resolve(context, reference, 'execution_result'):
                        raise ValueError('execution_received_reference_unqualified')
                    references.append(reference)
        if declared.get('x-source') == BLAST_GRADED_RETURN_SOURCE:
            for row in form[name]:
                if not self.resolve(context, row['result_ref'], 'execution_result'):
                    raise ValueError('blast_grader_result_reference_unqualified')
                references.append(row['result_ref'])
        if declared.get('x-source') in {'execution_handoff_refs', 'execution_result_refs', 'practical_receipt_refs', 'bvbrc_appservice_support_refs'}:
            for reference in form[name]:
                namespace = declared['items'].get('x-reference-namespace')
                already_admitted = namespace == 'execution_result' and reference in native_references
                if not already_admitted and (not self.resolve(context, reference, namespace)):
                    raise ValueError('execution_received_reference_unqualified')
                references.append(reference)
    return list(dict.fromkeys(references))

def received_execution_closure_facts(self, context):
    """Private return bindings, called only by the registry at episode closure."""
    if context.role not in {'annotation', 'partner_presence_evidence'}:
        return {}
    schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
    result = {}
    return result

def received_execution_facts(self, context):
    schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
    result = {}
    if context.role in {'annotation', 'partner_presence_evidence'}:
        requested = {node.get('x-source') for node in schema.get('properties', {}).values()}
        if 'execution_file_source_refs' in requested:
            result['execution_file_source_refs'] = self.local_file_sources.received_sources(context)
        if 'execution_file_capture_outcomes' in requested:
            result['execution_file_capture_outcomes'] = self.local_file_sources.received_outcomes(context)
    if context.role in {'annotation', 'partner_presence_evidence'}:
        result.update(self.native_blast_masking_returns.received_facts(context, schema))
        result.update(self.native_blast_utility_returns.received_facts(context, schema))
    if self._has_uniprot() and context.role in {'annotation', 'partner_presence_evidence'}:
        result.update(self.api_execution.uniprot_returns.facts_for_closure(context, schema))
    if self.native_blast_standard_database_returns is not None and context.role in {'annotation', 'partner_presence_evidence'}:
        result.update(self.native_blast_standard_database_returns.received_facts(context, schema))
    if self.native_blast_database_returns is not None and context.role in {'annotation', 'partner_presence_evidence'}:
        result.update(self.native_blast_database_returns.received_facts(context, schema))
    if self.native_hmmer_preparation_returns is not None and context.role in {'annotation', 'partner_presence_evidence'}:
        result.update(self.native_hmmer_preparation_returns.received_facts(context, schema))
    if self.native_blast_returns is not None and context.role in {'annotation', 'partner_presence_evidence'}:
        result.update(self.native_blast_returns.received_facts(context, schema))
    if self._has_rfam() and context.role in {'annotation', 'partner_presence_evidence'}:
        result.update(self.api_execution.rfam_returns.received_facts(context, schema))
    if self._has_appservice() and context.role in {'annotation', 'partner_presence_evidence'}:
        if any((node.get('x-source') == 'bvbrc_appservice_support_refs' for node in schema.get('properties', {}).values())):
            result['bvbrc_appservice_support_refs'] = self.api_execution.appservice.received_support_refs(context)
        result.update(self.api_execution.homology_returns.received_facts(context, schema))
    if self.rna_structure_comparison_returns is not None and context.role in {'annotation', 'partner_presence_evidence'}:
        result.update(self.rna_structure_comparison_returns.received_facts(context, schema))
    if self.native_expression_nmf_returns is not None and context.role in {'annotation', 'partner_presence_evidence'} and (schema.get('properties') is not None):
        result.update(self.native_expression_nmf_returns.facts_for_closure(context, schema))
    if self.native_rna_structure_returns is not None and context.role in {'annotation', 'partner_presence_evidence'}:
        result.update(self.native_rna_structure_returns.received_facts(context, schema))
    if self.native_infernal_preparation_returns is not None and context.role in {'annotation', 'partner_presence_evidence'}:
        result.update(self.native_infernal_preparation_returns.received_facts(context, schema))
    if self.native_infernal_returns is not None and context.role in {'annotation', 'partner_presence_evidence'}:
        result.update(self.native_infernal_returns.received_facts(context, schema))
    return result

def received_execution_sources(self, role):
    result = {}
    if role in {'annotation', 'partner_presence_evidence'}:
        for source in ('execution_file_source_refs', 'execution_file_capture_outcomes'):
            definition = self.fact_sources('results').get(source)
            if definition is not None:
                result[source] = deepcopy(definition)
    if role in {'annotation', 'partner_presence_evidence'}:
        from gene_annotation_episode.episodic_workflow.root.a107.sequence_masking_result_views import masking_fact_sources
        result.update(masking_fact_sources())
        from gene_annotation_episode.episodic_workflow.root.a107.blast_utility_result_views import blast_utility_fact_sources
        result.update(blast_utility_fact_sources())
    if self._has_uniprot() and role in {'annotation', 'partner_presence_evidence'}:
        from gene_annotation_episode.episodic_workflow.root.a107.uniprot_return_contracts import uniprot_fact_sources
        result.update(uniprot_fact_sources())
    if self.rna_structure_comparison_returns is not None and role in {'annotation', 'partner_presence_evidence'}:
        from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_comparison_views import rna_comparison_fact_sources
        result.update(rna_comparison_fact_sources())
    if self.native_expression_nmf_returns is not None and role in {'annotation', 'partner_presence_evidence'}:
        from gene_annotation_episode.episodic_workflow.root.a107.expression_nmf_return_views import expression_nmf_fact_sources
        result.update(expression_nmf_fact_sources())
    if self.native_rna_structure_returns is not None and role in {'annotation', 'partner_presence_evidence'}:
        from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_result_views import rna_structure_fact_sources
        result.update(rna_structure_fact_sources())
    if self.native_infernal_preparation_returns is not None and role in {'annotation', 'partner_presence_evidence'}:
        from gene_annotation_episode.episodic_workflow.root.a107.infernal_preparation_result_views import preparation_fact_sources
        result.update(preparation_fact_sources())
    if self.native_infernal_returns is not None and role in {'annotation', 'partner_presence_evidence'}:
        from gene_annotation_episode.episodic_workflow.root.a107.infernal_native_result_views import native_infernal_fact_sources
        result.update(native_infernal_fact_sources())
        result['execution_infernal_result_refs'] = self._infernal_reference_source()
    if self.native_blast_standard_database_returns is not None and role in {'annotation', 'partner_presence_evidence'}:
        from gene_annotation_episode.episodic_workflow.root.a107.native_blast_standard_database_result_views import standard_blast_database_fact_sources
        result.update(standard_blast_database_fact_sources())
    if self.native_blast_database_returns is not None and role in {'annotation', 'partner_presence_evidence'}:
        from gene_annotation_episode.episodic_workflow.root.a107.native_blast_database_result_views import native_blast_database_fact_sources
        result.update(native_blast_database_fact_sources())
    if self.native_hmmer_preparation_returns is not None and role in {'annotation', 'partner_presence_evidence'}:
        from gene_annotation_episode.episodic_workflow.root.a107.hmmer_preparation_result_views import preparation_fact_sources
        result.update(preparation_fact_sources())
    if self.native_blast_returns is not None and role in {'annotation', 'partner_presence_evidence'}:
        from gene_annotation_episode.episodic_workflow.root.a107.blast_pairwise_result_views import native_blast_fact_sources
        result.update(native_blast_fact_sources())
        result['execution_blast_pairwise_result_refs'] = self._blast_reference_source()
    if self._has_rfam() and role in {'annotation', 'partner_presence_evidence'}:
        from gene_annotation_episode.episodic_workflow.root.a107.rfam_batch_returns import rfam_fact_sources
        result.update(rfam_fact_sources())
    if self._has_appservice() and role in {'annotation', 'partner_presence_evidence'}:
        result.update(self._appservice_sources())
    return result

def resolve(self, context, reference, namespace):
    try:
        admitted = resolve_received_execution_reference(self, context, reference, namespace)
        if admitted is not None:
            return admitted
        masking = self._masking_reference_access(context, reference, namespace)
        if masking is not None:
            return masking
        utility = self._utility_reference_access(context, reference, namespace)
        if utility is not None:
            return utility
        if self._has_uniprot():
            resolved = self.api_execution.uniprot_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.uniprot_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self.native_blast_standard_database_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.native_blast_standard_database_results import IDENTIFIER_NAMESPACES as DATABASE_NAMESPACES
            if namespace in DATABASE_NAMESPACES:
                return self.native_blast_standard_database_results.resolve(context, reference, namespace) if context.role == 'results' else self.native_blast_standard_database_returns.resolve_received(context, reference, namespace)
            if self.native_blast_standard_database_results.resolve(context, reference, namespace):
                return True
            if context.role in {'annotation', 'partner_presence_evidence'}:
                resolved = self.native_blast_standard_database_returns.resolve_received(context, reference, namespace)
                if resolved is not None:
                    return resolved
        if self.native_blast_database_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.native_blast_database_results import IDENTIFIER_NAMESPACES as DATABASE_NAMESPACES
            if namespace in DATABASE_NAMESPACES:
                return self.native_blast_database_results.resolve(context, reference, namespace) if context.role == 'results' else self.native_blast_database_returns.resolve_received(context, reference, namespace)
            if self.native_blast_database_results.resolve(context, reference, namespace):
                return True
            if context.role in {'annotation', 'partner_presence_evidence'}:
                resolved = self.native_blast_database_returns.resolve_received(context, reference, namespace)
                if resolved is not None:
                    return resolved
        if self.native_hmmer_preparation_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.hmmer_preparation_result_views import IDENTIFIER_NAMESPACES as HMMER_PREPARATION_NAMESPACES
            if namespace in HMMER_PREPARATION_NAMESPACES:
                return self.native_hmmer_preparation_results.resolve(context, reference, namespace) if context.role == 'results' else self.native_hmmer_preparation_returns.resolve_received(context, reference, namespace)
            if self.native_hmmer_preparation_results.resolve(context, reference, namespace):
                return True
            if context.role in {'annotation', 'partner_presence_evidence'}:
                resolved = self.native_hmmer_preparation_returns.resolve_received(context, reference, namespace)
                if resolved is not None:
                    return resolved
        if self.native_blast_results is not None:
            if namespace in {'native_blast_pairwise_row', 'native_blast_artifact_key', 'native_blast_search_pointer'}:
                return self.native_blast_results.resolve(context, reference, namespace) if context.role == 'results' else self.native_blast_returns.resolve_received(context, reference, namespace)
            if self.native_blast_results.resolve(context, reference, namespace):
                return True
            if context.role in {'annotation', 'partner_presence_evidence'}:
                resolved = self.native_blast_returns.resolve_received(context, reference, namespace)
                if resolved is not None:
                    return resolved
        if self._has_rfam():
            resolved = self.api_execution.rfam_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.rfam_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self._has_appservice():
            from gene_annotation_episode.episodic_workflow.root.a107.bvbrc_homology_returns import IDENTIFIER_NAMESPACES
            if namespace in IDENTIFIER_NAMESPACES and context.role != 'results':
                return self.api_execution.homology_returns.resolve_received(context, reference, namespace)
        if namespace == 'bvbrc_minhash_genome':
            if self.api_execution is None:
                return False
            if context.role == 'results':
                return self.api_execution.minhash.resolve_own(context, reference, namespace)
            return self.api_execution.minhash.resolve_received(context, reference, namespace)
        from gene_annotation_episode.episodic_workflow.root.a107.bvbrc_data_views import IDENTIFIER_NAMESPACES
        if namespace in IDENTIFIER_NAMESPACES:
            return self.api_execution is not None and self.api_execution.bvbrc_data.resolve(context, reference, namespace)
        if namespace in {'execution_handle', 'execution'}:
            from gene_annotation_episode.episodic_workflow.root.a107.episode_bindings import reference_in_context
            return bool(self.services is not None and reference_in_context(self.services, context, reference, namespace))
        if context.role in {'launch_local', 'launch_hpc'} and namespace == 'practical_receipt' and (not reference.startswith('source_')):
            return self._delegate(context).resolve(self._practical_context(context), reference, namespace)
        if self.native_hmmer_results.resolve(context, reference, namespace):
            return True
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
        if self.api_execution is not None and self.api_execution.resolve(context, reference, namespace):
            return True
        if self.native_hmmer_preparation_results is not None:
            access = self.native_hmmer_preparation_results.retained_reference_access(context, reference, namespace)
            if access is not None:
                return access
        if source.get('provider') == 'episode.practical_receipt' or (self.api_execution is not None and self.api_execution.is_handoff_source(reference)):
            return False
        if self.services is not None:
            from gene_annotation_episode.episodic_workflow.root.a107.episode_bindings import reference_in_context
            return bool(reference_in_context(self.services, context, reference, namespace))
        kind = source['record_type']
        return bool(self.store.reference_subset([reference], plain(context.scope)) and (namespace in {None, kind} or (namespace == 'subject' and kind in {'input', 'feature', 'product', 'read_subject'})))
    except (ValueError, KeyError, OSError):
        return False

def resolve_received_execution_reference(self, context, reference, namespace):
    captured = self.local_file_sources.reference_access(context, reference, namespace)
    if captured is not None:
        return captured
    nmf = self._expression_nmf_reference_access(context, reference, namespace)
    if nmf is not None:
        return nmf
    masking = self._masking_reference_access(context, reference, namespace)
    if masking is not None:
        return masking
    utility = self._utility_reference_access(context, reference, namespace)
    if utility is not None:
        return utility
    if self._has_uniprot():
        resolved = self.api_execution.uniprot_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.uniprot_returns.resolve_received(context, reference, namespace)
        if resolved is not None:
            return resolved
    if self.rna_structure_comparison_results is not None:
        from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_comparison_results import IDENTIFIER_NAMESPACES as COMPARISON_NAMESPACES
        if namespace in COMPARISON_NAMESPACES:
            return self.rna_structure_comparison_results.resolve(context, reference, namespace) if context.role == 'results' else self.rna_structure_comparison_returns.resolve_received(context, reference, namespace)
        access = self.rna_structure_comparison_results.retained_reference_access(context, reference, namespace)
        if access is not None:
            return access
    if self.native_rna_structure_results is not None:
        access = self.native_rna_structure_results.retained_reference_access(context, reference, namespace)
        if access is not None:
            return access
        if context.role in {'annotation', 'partner_presence_evidence'}:
            resolved = self.native_rna_structure_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
    if self.native_blast_standard_database_returns is not None and context.role in {'annotation', 'partner_presence_evidence'}:
        resolved = self.native_blast_standard_database_returns.resolve_received(context, reference, namespace)
        if resolved is not None:
            return resolved
    if self.native_blast_database_returns is not None and context.role in {'annotation', 'partner_presence_evidence'}:
        resolved = self.native_blast_database_returns.resolve_received(context, reference, namespace)
        if resolved is not None:
            return resolved
    if self.native_hmmer_preparation_returns is not None and context.role in {'annotation', 'partner_presence_evidence'}:
        resolved = self.native_hmmer_preparation_returns.resolve_received(context, reference, namespace)
        if resolved is not None:
            return resolved
    if self.native_infernal_preparation_returns is not None and context.role in {'annotation', 'partner_presence_evidence'}:
        resolved = self.native_infernal_preparation_returns.resolve_received(context, reference, namespace)
        if resolved is not None:
            return resolved
    if self.native_infernal_returns is not None and context.role in {'annotation', 'partner_presence_evidence'}:
        resolved = self.native_infernal_returns.resolve_received(context, reference, namespace)
        if resolved is not None:
            return resolved
    if self.native_blast_returns is not None and context.role in {'annotation', 'partner_presence_evidence'}:
        resolved = self.native_blast_returns.resolve_received(context, reference, namespace)
        if resolved is not None:
            return resolved
    if self._has_rfam() and context.role in {'annotation', 'partner_presence_evidence'}:
        resolved = self.api_execution.rfam_returns.resolve_received(context, reference, namespace)
        if resolved is not None:
            return resolved
    if self._has_appservice():
        from gene_annotation_episode.episodic_workflow.root.a107.bvbrc_homology_returns import IDENTIFIER_NAMESPACES
        if namespace in IDENTIFIER_NAMESPACES:
            if context.role == 'results':
                return None
            return self.api_execution.homology_returns.resolve_received(context, reference, namespace)
        resolved = self.api_execution.appservice.resolve(context, reference, namespace)
        if resolved is not None:
            return resolved
    for results in (self.native_hmmer_preparation_results,):
        if results is not None:
            resolved = results.retained_reference_access(context, reference, namespace)
            if resolved is not None:
                return resolved
    return None

def validate_received_execution_report(self, context, form, schema):
    self.local_file_sources.validate_received_report(context, form, schema)
    self.native_blast_masking_returns.validate_received_report(context, form, schema)
    self.native_blast_utility_returns.validate_received_report(context, form, schema)
    if self._has_uniprot():
        self.api_execution.uniprot_returns.validate_received_report(context, form, schema)
    if self.rna_structure_comparison_returns is not None:
        self.rna_structure_comparison_returns.validate_received_report(context, form, schema)
    if self.native_expression_nmf_returns is not None:
        self.native_expression_nmf_returns.validate_received_report(context, form, schema)
    if self.native_rna_structure_returns is not None:
        self.native_rna_structure_returns.validate_received_report(context, form, schema)
    if self.native_infernal_preparation_returns is not None:
        self.native_infernal_preparation_returns.validate_received_report(context, form, schema)
    if self.native_infernal_returns is not None:
        self.native_infernal_returns.validate_received_report(context, form, schema)
    if self.native_blast_standard_database_returns is not None:
        self.native_blast_standard_database_returns.validate_received_report(context, form, schema)
    if self.native_blast_database_returns is not None:
        self.native_blast_database_returns.validate_received_report(context, form, schema)
    if self.native_hmmer_preparation_returns is not None:
        self.native_hmmer_preparation_returns.validate_received_report(context, form, schema)
    if self.native_blast_returns is not None:
        self.native_blast_returns.validate_received_report(context, form, schema)
    if self._has_rfam():
        self.api_execution.rfam_returns.validate_received_report(context, form, schema)
    if self._has_appservice():
        self.api_execution.homology_returns.validate_received_report(context, form, schema)
