"""Scoped observations of original API/native executions, separate from launch.

This is a read-only resource adapter for the existing recursive monitor. It
owns observation custody, never an episode loop, retry, or continuation rule.
"""
from __future__ import annotations
import base64
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from .communication import plain
from .domain import ContractError
from .episode_bindings import native_observation_options
from .execution_contracts import canonical, digest, validate_target
from .practical_execution_operations import LocalPracticalOperations
from .library.native_terminal_transport import TerminalExecution
from .practical_execution_records import terminal_job_matches
from .practical_receipt_information import PracticalReceiptInformation, PROVIDER
from .progress_records import resource_status, validate_resource_observation
VERSION = 'execution_progress_provider_v1'
_FIELDS = ('execution_status', 'measurements', 'log_windows', 'committed_record_refs', 'dependencies', 'result_available')
_APPSERVICE_OBSERVATION_SCHEMA = {'type': 'object', 'additionalProperties': False, 'properties': {'native_operation': {'type': 'string', 'enum': ['query_tasks', 'stdout', 'stderr']}}, 'required': ['native_operation']}

def _appservice_target(target):
    assignment = target['assignment']
    if target['resource_kind'] != 'api' or assignment.get('service') != 'bvbrc_appservice':
        return False
    request = assignment.get('request', {})
    if assignment.get('version') != 'api_service_assignment_v1' or request.get('version') != 'bvbrc_appservice_request_v1' or request.get('effect_contract') != 'selected_api_effects_v1':
        raise ContractError('bvbrc_appservice_execution_contract_required')
    return True

def _validate_native_observation(target, native_operation):
    if _appservice_target(target):
        if native_operation is None:
            raise ContractError('bvbrc_appservice_native_operation_required')
        if native_operation not in ('query_tasks', 'stdout', 'stderr'):
            raise ContractError('bvbrc_appservice_native_operation_invalid')
    elif native_operation is not None:
        raise ContractError('progress_native_operation_not_supported')

def _now():
    return datetime.now(timezone.utc).isoformat()

def _without_read_times(value):
    if isinstance(value, dict):
        return {key: _without_read_times(item) for key, item in value.items() if key not in {'observed_at', 'retrieved_at'}}
    if isinstance(value, list):
        return [_without_read_times(item) for item in value]
    return value

def describe_execution_target(target):
    """Describe a validated original target without a fresh status/file read."""
    assignment = target['assignment']
    if target['resource_kind'] == 'api':
        service = assignment['service']
        formats = {'ncbi_blast': 'blast_json2', 'uniprot': 'uniprot_json', 'bvbrc_data': 'bvbrc_json', 'ebi_hmmer': 'hmmer_json'}
        request = assignment.get('request', {})
        if _appservice_target(target):
            return {'resource_kind': 'api', 'service_or_program': service, 'operation': request['required_application_id'], 'required_application_id': request['required_application_id'], 'request_version': request['version'], 'output_format': None, 'submitted_parameters': deepcopy(request['parameters']), 'submitted_start_parameters': deepcopy(request['start_parameters']), 'selected_observation_schema': deepcopy(_APPSERVICE_OBSERVATION_SCHEMA)}
        if service == 'bvbrc_data' and request.get('version') == 'bvbrc_data_request_v2':
            return {'resource_kind': 'api', 'service_or_program': service, 'operation': request['mode'], 'collection': request['collection'], 'mode': request['mode'], 'request_version': request['version'], 'request_profile': 'solr_query_solr_json_v1', 'request_media_type': 'application/solrquery+x-www-form-urlencoded', 'expected_response_media_type': 'application/solr+json', 'output_format': 'solr_json_envelope_v1'}
        operation = request.get('program', request.get('operation', request.get('collection', assignment.get('algorithm'))))
        return {'resource_kind': 'api', 'service_or_program': service, 'operation': operation, 'output_format': formats.get(service)}
    utility = assignment['requested_job'].get('native_blast_utility')
    if utility is not None:
        from .native_blast_utility_contracts import JOB_VERSION_V3
        operation = utility['operation']
        value = {'resource_kind': target['resource_kind'], 'service_or_program': operation['program'], 'operation': operation['mode'], 'mode': operation['mode'], 'molecule': operation['molecule'], 'selected_outputs': deepcopy(utility['outputs']), 'output_format': 'native_blast_utility_bundle_v1'}
        if utility['version'] == JOB_VERSION_V3:
            value.update(native_job_version=utility['version'], native_output_format=operation['parameters']['output_format'])
        return value
    masking = assignment['requested_job'].get('native_blast_masking')
    if masking is not None:
        operation = masking['operation']
        return {'resource_kind': target['resource_kind'], 'service_or_program': operation['program'], 'operation': operation['mode'], 'mode': operation['mode'], 'input_format': operation['input_format'], 'native_output_format': operation['output_format'], 'masking_style': operation['masking_style'], 'selected_outputs': deepcopy(masking['outputs']), 'output_format': 'native_blast_masking_bundle_v1'}
    database = assignment['requested_job'].get('native_blast_standard_database')
    if database is not None:
        return {'resource_kind': target['resource_kind'], 'service_or_program': database['program'], 'operation': database['mode'], 'mode': database['mode'], 'output_format': 'native_blast_standard_database_bundle_v1'}
    database = assignment['requested_job'].get('native_blast_database')
    if database is not None:
        return {'resource_kind': target['resource_kind'], 'service_or_program': database['program'], 'operation': database['mode'], 'mode': database['mode'], 'output_format': 'native_blast_database_bundle_v1'}
    native_blast = assignment['requested_job'].get('native_blast')
    if native_blast is not None:
        return {'resource_kind': target['resource_kind'], 'service_or_program': native_blast['program'], 'operation': native_blast['mode'], 'mode': native_blast['mode'], 'output_format': 'native_blast_bundle_v1'}
    native_hmmer = assignment['requested_job'].get('native_hmmer')
    if native_hmmer is not None:
        return {'resource_kind': target['resource_kind'], 'service_or_program': native_hmmer['program'], 'operation': native_hmmer['mode'], 'output_format': 'native_hmmer_bundle_v1'}
    preparation = assignment['requested_job'].get('native_hmmer_preparation')
    if preparation is not None:
        return {'resource_kind': target['resource_kind'], 'service_or_program': preparation['program'], 'operation': preparation['mode'], 'output_format': 'native_hmmer_preparation_bundle_v1'}
    return {'resource_kind': target['resource_kind'], 'service_or_program': assignment['requested_job']['argv'][0], 'operation': None, 'output_format': None}
_NATIVE_RESULT_IMPLEMENTATIONS = {'execution_result_acquisition': {'native_hmmer_results': 'gene_annotation_episode.episodic_workflow.root.a104.execution_result_acquisition.native_hmmer_result_acquisition.NativeHMMERResultAcquisition.execute', 'native_blast_results': 'gene_annotation_episode.episodic_workflow.root.a104.execution_result_acquisition.native_blast_result_acquisition.NativeBLASTResultAcquisition.execute', 'native_blast_masking_results': 'gene_annotation_episode.episodic_workflow.root.a104.execution_result_acquisition.native_blast_masking_result_acquisition.NativeBLASTMaskingResultAcquisition.execute', 'native_blast_utility_results': 'gene_annotation_episode.episodic_workflow.root.a104.execution_result_acquisition.native_blast_utility_result_acquisition.NativeBLASTUtilityResultAcquisition.execute', 'native_blast_standard_database_results': 'gene_annotation_episode.episodic_workflow.root.a104.execution_result_acquisition.native_blast_standard_database_result_acquisition.StandardBLASTDatabaseResultAcquisition.execute', 'native_blast_database_results': 'gene_annotation_episode.episodic_workflow.root.a104.execution_result_acquisition.native_blast_database_result_acquisition.NativeBLASTDatabaseResultAcquisition.execute', 'native_hmmer_preparation_results': 'gene_annotation_episode.episodic_workflow.root.a104.execution_result_acquisition.native_hmmer_preparation_result_acquisition.NativeHmmerPreparationResultAcquisition.execute'}, 'evolutionary_history_evidence/execution_result_acquisition': {'native_hmmer_results': 'gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.execution_result_acquisition.native_hmmer_result_acquisition.NativeHMMERResultAcquisition.execute', 'native_blast_results': 'gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.execution_result_acquisition.native_blast_result_acquisition.NativeBLASTResultAcquisition.execute', 'native_blast_masking_results': 'gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.execution_result_acquisition.native_blast_masking_result_acquisition.NativeBLASTMaskingResultAcquisition.execute', 'native_blast_utility_results': 'gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.execution_result_acquisition.native_blast_utility_result_acquisition.NativeBLASTUtilityResultAcquisition.execute', 'native_blast_standard_database_results': 'gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.execution_result_acquisition.native_blast_standard_database_result_acquisition.StandardBLASTDatabaseResultAcquisition.execute', 'native_blast_database_results': 'gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.execution_result_acquisition.native_blast_database_result_acquisition.NativeBLASTDatabaseResultAcquisition.execute', 'native_hmmer_preparation_results': 'gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.execution_result_acquisition.native_hmmer_preparation_result_acquisition.NativeHmmerPreparationResultAcquisition.execute'}, 'hpc_work_planning/execution_result_acquisition': {'native_hmmer_results': 'gene_annotation_episode.episodic_workflow.root.a104.hpc_work_planning.execution_result_acquisition.native_hmmer_result_acquisition.NativeHMMERResultAcquisition.execute', 'native_blast_results': 'gene_annotation_episode.episodic_workflow.root.a104.hpc_work_planning.execution_result_acquisition.native_blast_result_acquisition.NativeBLASTResultAcquisition.execute', 'native_blast_masking_results': 'gene_annotation_episode.episodic_workflow.root.a104.hpc_work_planning.execution_result_acquisition.native_blast_masking_result_acquisition.NativeBLASTMaskingResultAcquisition.execute', 'native_blast_utility_results': 'gene_annotation_episode.episodic_workflow.root.a104.hpc_work_planning.execution_result_acquisition.native_blast_utility_result_acquisition.NativeBLASTUtilityResultAcquisition.execute', 'native_blast_standard_database_results': 'gene_annotation_episode.episodic_workflow.root.a104.hpc_work_planning.execution_result_acquisition.native_blast_standard_database_result_acquisition.StandardBLASTDatabaseResultAcquisition.execute', 'native_blast_database_results': 'gene_annotation_episode.episodic_workflow.root.a104.hpc_work_planning.execution_result_acquisition.native_blast_database_result_acquisition.NativeBLASTDatabaseResultAcquisition.execute', 'native_hmmer_preparation_results': 'gene_annotation_episode.episodic_workflow.root.a104.hpc_work_planning.execution_result_acquisition.native_hmmer_preparation_result_acquisition.NativeHmmerPreparationResultAcquisition.execute'}, 'hpc_work_planning/hpc_allocation_execution/execution_result_acquisition': {'native_hmmer_results': 'gene_annotation_episode.episodic_workflow.root.a104.hpc_work_planning.hpc_allocation_execution.execution_result_acquisition.native_hmmer_result_acquisition.NativeHMMERResultAcquisition.execute', 'native_blast_results': 'gene_annotation_episode.episodic_workflow.root.a104.hpc_work_planning.hpc_allocation_execution.execution_result_acquisition.native_blast_result_acquisition.NativeBLASTResultAcquisition.execute', 'native_blast_masking_results': 'gene_annotation_episode.episodic_workflow.root.a104.hpc_work_planning.hpc_allocation_execution.execution_result_acquisition.native_blast_masking_result_acquisition.NativeBLASTMaskingResultAcquisition.execute', 'native_blast_utility_results': 'gene_annotation_episode.episodic_workflow.root.a104.hpc_work_planning.hpc_allocation_execution.execution_result_acquisition.native_blast_utility_result_acquisition.NativeBLASTUtilityResultAcquisition.execute', 'native_blast_standard_database_results': 'gene_annotation_episode.episodic_workflow.root.a104.hpc_work_planning.hpc_allocation_execution.execution_result_acquisition.native_blast_standard_database_result_acquisition.StandardBLASTDatabaseResultAcquisition.execute', 'native_blast_database_results': 'gene_annotation_episode.episodic_workflow.root.a104.hpc_work_planning.hpc_allocation_execution.execution_result_acquisition.native_blast_database_result_acquisition.NativeBLASTDatabaseResultAcquisition.execute', 'native_hmmer_preparation_results': 'gene_annotation_episode.episodic_workflow.root.a104.hpc_work_planning.hpc_allocation_execution.execution_result_acquisition.native_hmmer_preparation_result_acquisition.NativeHmmerPreparationResultAcquisition.execute'}, 'evolutionary_history_evidence/hpc_work_planning/execution_result_acquisition': {'native_hmmer_results': 'gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.hpc_work_planning.execution_result_acquisition.native_hmmer_result_acquisition.NativeHMMERResultAcquisition.execute', 'native_blast_results': 'gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.hpc_work_planning.execution_result_acquisition.native_blast_result_acquisition.NativeBLASTResultAcquisition.execute', 'native_blast_masking_results': 'gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.hpc_work_planning.execution_result_acquisition.native_blast_masking_result_acquisition.NativeBLASTMaskingResultAcquisition.execute', 'native_blast_utility_results': 'gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.hpc_work_planning.execution_result_acquisition.native_blast_utility_result_acquisition.NativeBLASTUtilityResultAcquisition.execute', 'native_blast_standard_database_results': 'gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.hpc_work_planning.execution_result_acquisition.native_blast_standard_database_result_acquisition.StandardBLASTDatabaseResultAcquisition.execute', 'native_blast_database_results': 'gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.hpc_work_planning.execution_result_acquisition.native_blast_database_result_acquisition.NativeBLASTDatabaseResultAcquisition.execute', 'native_hmmer_preparation_results': 'gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.hpc_work_planning.execution_result_acquisition.native_hmmer_preparation_result_acquisition.NativeHmmerPreparationResultAcquisition.execute'}, 'evolutionary_history_evidence/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition': {'native_hmmer_results': 'gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.hpc_work_planning.hpc_allocation_execution.execution_result_acquisition.native_hmmer_result_acquisition.NativeHMMERResultAcquisition.execute', 'native_blast_results': 'gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.hpc_work_planning.hpc_allocation_execution.execution_result_acquisition.native_blast_result_acquisition.NativeBLASTResultAcquisition.execute', 'native_blast_masking_results': 'gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.hpc_work_planning.hpc_allocation_execution.execution_result_acquisition.native_blast_masking_result_acquisition.NativeBLASTMaskingResultAcquisition.execute', 'native_blast_utility_results': 'gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.hpc_work_planning.hpc_allocation_execution.execution_result_acquisition.native_blast_utility_result_acquisition.NativeBLASTUtilityResultAcquisition.execute', 'native_blast_standard_database_results': 'gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.hpc_work_planning.hpc_allocation_execution.execution_result_acquisition.native_blast_standard_database_result_acquisition.StandardBLASTDatabaseResultAcquisition.execute', 'native_blast_database_results': 'gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.hpc_work_planning.hpc_allocation_execution.execution_result_acquisition.native_blast_database_result_acquisition.NativeBLASTDatabaseResultAcquisition.execute', 'native_hmmer_preparation_results': 'gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.hpc_work_planning.hpc_allocation_execution.execution_result_acquisition.native_hmmer_preparation_result_acquisition.NativeHmmerPreparationResultAcquisition.execute'}}

class ExecutionTargetReader:
    """Validate source/run/scope/request first; observe exactly its native ID."""

    def __init__(self, store, *, run_id, directory, resources, api_execution, api_observer=None, native_result_owner=None):
        if not isinstance(run_id, str) or not run_id:
            raise ValueError('execution_progress_run_identity_required')
        self.store, self.run_id, self.directory = (store, run_id, Path(directory))
        self.resources = json.loads(canonical(resources))
        self.api_execution = api_execution
        self.api_observer = api_observer
        self.receipts = PracticalReceiptInformation(store, run_id)
        self.operations = {}
        for resource_id, configuration in self.resources.items():
            kind = configuration.get('kind')
            if kind == 'local':
                self.operations[resource_id] = LocalPracticalOperations({key: value for key, value in configuration.items() if key not in {'launch_prompt_entry', 'launch_prompt_sections', 'scheduler'}})
            elif kind == 'pbs_ssh':
                self.operations[resource_id] = TerminalExecution(configuration)
            elif kind not in {'hmmer_api', 'api'}:
                raise ValueError('unsupported_execution_progress_resource')
        if native_result_owner is not None and (not isinstance(native_result_owner, str) or native_result_owner not in _NATIVE_RESULT_IMPLEMENTATIONS):
            raise ValueError('native_result_counterpart_owner_invalid')
        self.native_result_owner = native_result_owner

    def _original_scope(self, handle):
        source = self.store.get(handle)
        if source.get('provider') == 'episode.bvbrc_appservice_receipt':
            if self.api_execution is None:
                raise ValueError('execution_target_unavailable')
            return self.store.validate_scope(self.api_execution.scope(handle))
        for field in ('request_ref', 'artifact_ref'):
            reference = source.get(field)
            if reference is None:
                continue
            try:
                body = json.loads(self.store.get_artifact(reference))
                scope = body.get('scope')
                if scope is None and isinstance(body.get('target'), dict):
                    scope = body['target'].get('scope')
                if scope is not None:
                    return self.store.validate_scope(scope)
            except (ValueError, TypeError, AttributeError):
                continue
        raise ValueError('execution_target_original_scope_unavailable')

    def scope(self, handle):
        try:
            return self.read_target(handle, self._original_scope(handle))['scope']
        except (ValueError, KeyError, OSError) as error:
            raise ContractError('execution_target_unavailable_or_outside_scope', detail={'reason': str(error)}) from error

    def _read_native_receipt(self, reference, scope, reads):
        """Reuse only successful immutable receipt reads in one metadata operation."""
        try:
            key = (self.run_id, reference, canonical(plain(scope)))
        except (ValueError, TypeError, OverflowError, RecursionError):
            return self.receipts.read(reference, scope)
        if key not in reads:
            reads[key] = deepcopy(self.receipts.read(reference, scope))
        return deepcopy(reads[key])

    def _native(self, handle, scope, *, _seen=(), _receipt_reads=None):
        if handle in _seen:
            raise ValueError('native_blast_masking_receipt_ancestry_cycle')
        reads = {} if _receipt_reads is None else _receipt_reads
        body = self._read_native_receipt(handle, scope, reads)
        source = self.store.get(handle)
        snapshot = json.loads(self.store.get_artifact(source['request_ref']))
        assignment, receipt = (snapshot['assignment'], body['receipt'])
        job = receipt['outcome'].get('facts', {}).get('requested_job')
        terminal = receipt['tool_name'] == 'exec_command'
        if terminal:
            if not terminal_job_matches(assignment, receipt['outcome']):
                raise ValueError('execution_command_native_job_identity_conflict')
        elif receipt['tool_name'] not in {'practical.job.start', 'practical.job.status', 'practical.job.collect'} or not isinstance(job, dict) or (not isinstance(job.get('handoff'), dict)) or (job.get('requested_job_sha256') != digest(assignment['requested_job'])) or (job.get('argv') != assignment['requested_job']['argv']) or (job.get('environment') != assignment['requested_job']['environment']) or (job.get('resource_kind') != assignment['resource_kind']) or (job.get('execution_id') != job['handoff'].get('execution_id')) or (job['handoff'].get('monitor_operation') != 'practical.job.status') or (job['handoff'].get('results_operation') != 'practical.job.collect'):
            raise ValueError('practical_execution_handoff_identity_conflict')
        resource_id = assignment.get('resource_id')
        if resource_id is None:
            candidates = [key for key, config in self.resources.items() if config['kind'] == ('local' if assignment['resource_kind'] == 'local' else 'pbs_ssh') and Path(assignment['workspace']).is_relative_to(config['workspace'])]
            if len(candidates) != 1:
                raise ValueError('practical_execution_resource_identity_required')
            resource_id = candidates[0]
        config = self.resources.get(resource_id)
        if config is None or config['kind'] != ('local' if assignment['resource_kind'] == 'local' else 'pbs_ssh') or (not Path(assignment['workspace']).is_relative_to(config['workspace'])):
            raise ValueError('practical_execution_resource_identity_conflict')
        origin_episode_id = body['episode_id']
        if terminal:
            self.operations[resource_id].validate_assignment(assignment)
            target = validate_target({'version': 'execution_target_v1', 'handle': handle, 'run_id': self.run_id, 'resource_id': resource_id, 'resource_kind': assignment['resource_kind'], 'execution_id': job['execution_id'], 'request_sha256': digest(assignment['requested_job']), 'origin_episode_id': origin_episode_id, 'assignment': assignment, 'scope': body['scope']})
            return (target, body)
        if 'native_blast_utility' in assignment['requested_job']:
            from .native_blast_utility_contracts import validate_native_blast_utility_plan
            if assignment.get('resource_id') != resource_id or assignment['resource_kind'] != 'local':
                raise ValueError('native_blast_utility_resource_identity_conflict')
            self.operations[resource_id].validate_assignment(assignment)
            detail = receipt['outcome'].get('native_outcome') or {}
            plan = validate_native_blast_utility_plan(detail.get('native_blast_utility_plan'))
            owner = plan['identity']
            reference = receipt['arguments'].get('receipt_ref')
            if reference is not None:
                if receipt['tool_name'] not in {'practical.job.status', 'practical.job.collect'}:
                    raise ValueError('native_blast_utility_receipt_ancestry_conflict')
                original, prior = self._native(reference, body['scope'], _seen=(*_seen, handle), _receipt_reads=reads)
                prior_plan = (prior['receipt']['outcome'].get('native_outcome') or {}).get('native_blast_utility_plan')
                if canonical(plan) != canonical(prior_plan) or original['resource_id'] != resource_id or original['execution_id'] != job['execution_id'] or (original['assignment']['workspace'] != assignment['workspace']) or (canonical(original['assignment']['requested_job']) != canonical(assignment['requested_job'])):
                    raise ValueError('native_blast_utility_receipt_ancestry_conflict')
                assignment = original['assignment']
                origin_episode_id = original['origin_episode_id']
            elif owner['episode_id'] != origin_episode_id:
                raise ValueError('native_blast_utility_original_context_conflict')
            expected = {'run_id': self.run_id, 'episode_id': origin_episode_id, 'resource_id': resource_id, 'execution_id': job['execution_id'], 'requested_job_sha256': digest(assignment['requested_job']), 'operation_key': detail.get('attempt_operation_key'), 'attempt_id': detail.get('attempt_id')}
            root = Path(assignment['workspace']) / '.episode-operations' / digest({'run': self.run_id, 'episode': origin_episode_id}) / owner['attempt_id']
            observed = detail.get('observation', detail)
            constraints = assignment['constraints']
            if owner != expected or plan['requested_job'] != assignment['requested_job'] or job['execution_id'] != str(root / 'native.json') or (plan['attempt_directory'] != str(root / 'blast-utility-attempt')) or (observed.get('metadata', {}).get('policy') != plan['policy']) or (self.operations[resource_id].policy.to_dict() != plan['policy']) or ('allocation' in constraints and constraints['allocation'] != plan['policy']) or any((key in constraints and constraints[key] != value for key, value in plan['policy'].items())):
                raise ValueError('native_blast_utility_original_attempt_mismatch')
        if 'native_blast_masking' in assignment['requested_job']:
            from .native_blast_masking_contracts import validate_native_blast_masking_plan
            if assignment.get('resource_id') != resource_id or assignment['resource_kind'] != 'local':
                raise ValueError('native_blast_masking_resource_identity_conflict')
            detail = receipt['outcome'].get('native_outcome') or {}
            plan = validate_native_blast_masking_plan(detail.get('native_blast_masking_plan'))
            owner = plan['identity']
            reference = receipt['arguments'].get('receipt_ref')
            if reference is not None:
                if receipt['tool_name'] not in {'practical.job.status', 'practical.job.collect'}:
                    raise ValueError('native_blast_masking_receipt_ancestry_conflict')
                original, prior = self._native(reference, body['scope'], _seen=(*_seen, handle), _receipt_reads=reads)
                prior_plan = (prior['receipt']['outcome'].get('native_outcome') or {}).get('native_blast_masking_plan')
                if canonical(plan) != canonical(prior_plan) or original['resource_id'] != resource_id or original['execution_id'] != job['execution_id'] or (canonical(original['assignment']['requested_job']) != canonical(assignment['requested_job'])):
                    raise ValueError('native_blast_masking_receipt_ancestry_conflict')
                assignment = original['assignment']
                origin_episode_id = original['origin_episode_id']
            elif owner['episode_id'] != origin_episode_id:
                raise ValueError('native_blast_masking_original_context_conflict')
            expected = {'run_id': self.run_id, 'episode_id': origin_episode_id, 'resource_id': resource_id, 'execution_id': job['execution_id'], 'requested_job_sha256': digest(assignment['requested_job']), 'operation_key': detail.get('attempt_operation_key'), 'attempt_id': detail.get('attempt_id')}
            root = Path(assignment['workspace']) / '.episode-operations' / digest({'run': self.run_id, 'episode': origin_episode_id}) / owner['attempt_id']
            observed = detail.get('observation', detail)
            constraints = assignment['constraints']
            if owner != expected or plan['requested_job'] != assignment['requested_job'] or job['execution_id'] != str(root / 'native.json') or (plan['attempt_directory'] != str(root / 'blast-masking-attempt')) or (observed.get('metadata', {}).get('policy') != plan['policy']) or ('allocation' in constraints and constraints['allocation'] != plan['policy']) or any((key in constraints and constraints[key] != value for key, value in plan['policy'].items())):
                raise ValueError('native_blast_masking_original_attempt_mismatch')
        if assignment['resource_kind'] == 'hpc':
            original_ref = receipt['arguments'].get('receipt_ref') or receipt['outcome'].get('recovered_original_handoff_ref')
            if original_ref:
                original = self.read_target(original_ref, scope)
                if original['assignment'] != assignment or original['execution_id'] != job['execution_id'] or original['resource_id'] != resource_id:
                    raise ValueError('hpc_recovered_original_execution_conflict')
                origin_episode_id = original['origin_episode_id']
            detail = receipt['outcome'].get('native_outcome')
            if not isinstance(detail, dict) or detail.get('pbs_job_id') != job['execution_id'] or (not isinstance(detail.get('attempt_id'), str)) or (len(detail['attempt_id']) != 64) or (detail.get('account') != config['account']):
                raise ValueError('practical_execution_original_attempt_required')
            if 'native_blast_standard_database' in assignment['requested_job']:
                if config.get('native_blast_standard_database') is None:
                    raise ValueError('native_blast_standard_database_hpc_binding_required')
                self.operations[resource_id].validate_assignment(assignment)
                key = detail.get('attempt_operation_key')
                root = Path(assignment['workspace']) / '.episode-jobs' / digest({'run_id': self.run_id, 'episode_id': body['episode_id']}) / digest(assignment) / 'attempts' / detail['attempt_id']
                sha = detail.get('native_blast_standard_database_plan_sha256')
                if type(key) is not str or digest(key) != detail['attempt_id'] or detail.get('native_blast_standard_database_plan_path') != str(root / 'native-blast-standard-database-plan.json') or (type(sha) is not str) or (len(sha) != 64) or any((c not in '0123456789abcdef' for c in sha)):
                    raise ValueError('native_blast_standard_database_original_plan_required')
            if 'native_blast_database' in assignment['requested_job']:
                if config.get('native_blast_database') is None:
                    raise ValueError('native_blast_database_hpc_binding_required')
                self.operations[resource_id].validate_assignment(assignment)
                key = detail.get('attempt_operation_key')
                root = Path(assignment['workspace']) / '.episode-jobs' / digest({'run_id': self.run_id, 'episode_id': body['episode_id']}) / digest(assignment) / 'attempts' / detail['attempt_id']
                sha = detail.get('native_blast_database_plan_sha256')
                if type(key) is not str or digest(key) != detail['attempt_id'] or detail.get('native_blast_database_plan_path') != str(root / 'native-blast-database-plan.json') or (type(sha) is not str) or (len(sha) != 64) or any((c not in '0123456789abcdef' for c in sha)):
                    raise ValueError('native_blast_database_original_plan_required')
        target = validate_target({'version': 'execution_target_v1', 'handle': handle, 'run_id': self.run_id, 'resource_id': resource_id, 'resource_kind': assignment['resource_kind'], 'execution_id': job['execution_id'], 'request_sha256': digest(assignment['requested_job']), 'origin_episode_id': origin_episode_id, 'assignment': assignment, 'scope': body['scope']})
        return (target, body)

    def read_target(self, handle, scope, *, include_native_receipt=False):
        return self._read_target(handle, scope, include_native_receipt=include_native_receipt)

    def _read_target(self, handle, scope, *, include_native_receipt=False, _receipt_reads=None):
        try:
            if type(include_native_receipt) is not bool:
                raise ValueError('execution_target_receipt_selection_invalid')
            source = self.store.get(handle)
            if source.get('provider') == PROVIDER:
                target, receipt = self._native(handle, scope) if _receipt_reads is None else self._native(handle, scope, _receipt_reads=_receipt_reads)
                return (target, receipt) if include_native_receipt else target
            if self.api_execution is None:
                raise ValueError('execution_target_unavailable')
            target = validate_target(self.api_execution.read_target(handle, scope))
            configuration = self.resources.get(target['resource_id'])
            if target['handle'] != handle or target['run_id'] != self.run_id or target['resource_kind'] != 'api' or (configuration is None) or (configuration['kind'] not in {'hmmer_api', 'api'}) or (target['assignment'].get('service') != configuration.get('service', 'ebi_hmmer' if configuration['kind'] == 'hmmer_api' else None)):
                raise ValueError('api_execution_target_resource_conflict')
            if _appservice_target(target) and configuration.get('execution_contract') != 'bvbrc_appservice_execution_v1':
                raise ValueError('bvbrc_appservice_execution_contract_required')
            return (target, None) if include_native_receipt else target
        except (ValueError, KeyError, OSError) as error:
            raise ContractError('execution_target_unavailable_or_outside_scope', detail={'reason': str(error)}) from error

    def describe_target(self, handle, scope, *, selector=None):
        """Actual called-operation identity and available deterministic readers.

        This is information about already selected work and bound implementations,
        not task instructions, an observation, a parser choice or a new library.
        """
        target = self.read_target(handle, scope)
        value = describe_execution_target(target)
        source = self.store.get(handle)
        body = self.api_execution._read_handoff(handle, scope) if _appservice_target(target) else json.loads(self.store.get_artifact(source['artifact_ref']))
        receipt = body.get('receipt', {})
        called = receipt.get('tool_name', receipt.get('name'))
        if not isinstance(called, str) or not called:
            raise ContractError('execution_called_operation_unavailable')
        value.update(called_operation=called, status_operations=[], acquisition_operations=[], extractors=[])
        if target['resource_kind'] != 'api':
            implementation = type(self.operations[target['resource_id']])
            value['status_operations'] = ['progress.observe']
            value['acquisition_operations'] = ['execution.results.status', 'execution.results.collect', 'execution.results.read']
            value['extractors'] = [{'operation': 'progress.observe', 'implementation': implementation.__module__ + '.' + implementation.__qualname__ + '.observe_execution', 'return_fields': ['state', 'returncode', 'failure_code', 'result_available', 'measurements', 'outputs', 'logs'], 'return_fact_sources': ['monitoring_progress_refs', 'monitoring_execution_state', 'monitoring_result_available']}, {'operation': 'execution.results.read', 'implementation': implementation.__module__ + '.' + implementation.__qualname__ + '.read_output', 'return_fields': ['path', 'offset', 'returned_bytes', 'size_bytes', 'bytes_base64', 'text_utf8'], 'return_fact_sources': ['execution_result_refs', 'execution_result_origin']}]
            if 'native_blast_utility' in target['assignment']['requested_job']:
                from .blast_utility_result_views import NATIVE_BLAST_UTILITY_RESULT_SELECTOR_V2_SCHEMA, PROJECTION_V2_FIELDS, blast_utility_fact_sources, validate_blast_utility_result_selector
                from .native_blast_utility_contracts import JOB_VERSION_V3
                job = target['assignment']['requested_job']['native_blast_utility']
                vdb = job['version'] == JOB_VERSION_V3
                value['status_meanings'] = {'observed_state': 'original_selected_local_attempt', 'logs': 'selected_original_stdout_stderr_windows', 'result_available': 'observed_sealed_bundle_path_availability', 'result_validation': 'original_bundle_and_retained_file_identity_checks', 'native_success_capture_complete_delivery_complete_are_separate': True, 'process_liveness_establishes_productive_work': False}
                value['acquisition_operations'] = ['execution.results.status', 'execution.results.collect']
                value['extractors'][1] = {'operation': 'execution.results.collect', 'implementation': _NATIVE_RESULT_IMPLEMENTATIONS.get(getattr(self, 'native_result_owner', None), {}).get('native_blast_utility_results'), 'scientific_annotation_score': False}
                if vdb:
                    value['result_selector_schema'] = deepcopy(NATIVE_BLAST_UTILITY_RESULT_SELECTOR_V2_SCHEMA)
                    value['extractors'][1].update(parser='gene_annotation_episode.episodic_workflow.root.a104.blast_vdb_utility_inputs.' + ('parse_blast_vdb_extraction' if job['operation']['mode'] == 'extract_sequences' else 'parse_blast_vdb_inspection'), native_format=job['operation']['parameters']['output_format'], projection_implementation='gene_annotation_episode.episodic_workflow.root.a104.blast_utility_result_views.project_blast_utility_result', return_fields=list(PROJECTION_V2_FIELDS), return_fact_sources=list(blast_utility_fact_sources()))
                if selector is not None:
                    selected = validate_blast_utility_result_selector(plain(selector), operation=job['operation'])
                    if vdb:
                        value['result_selection'] = selected
            if 'native_blast_masking' in target['assignment']['requested_job']:
                from .sequence_masking_result_views import NATIVE_BLAST_MASKING_RESULT_SELECTOR_SCHEMA, masking_fact_sources, validate_masking_result_selector
                job = target['assignment']['requested_job']['native_blast_masking']
                value['result_selector_schema'] = deepcopy(NATIVE_BLAST_MASKING_RESULT_SELECTOR_SCHEMA)
                value['status_meanings'] = {'observed_state': 'original_selected_local_attempt', 'logs': 'selected_original_stdout_stderr_windows', 'result_available': 'observed_sealed_bundle_path_availability', 'result_validation': 'authenticated_capture_and_requested_qualified_projection', 'native_success_capture_complete_delivery_complete_are_separate': True, 'process_liveness_establishes_productive_work': False}
                value['acquisition_operations'] = ['execution.results.status', 'execution.results.collect']
                extractor = {'operation': 'execution.results.collect', 'implementation': _NATIVE_RESULT_IMPLEMENTATIONS.get(getattr(self, 'native_result_owner', None), {}).get('native_blast_masking_results'), 'parsers': ['gene_annotation_episode.episodic_workflow.root.a104.sequence_masking_inputs.parse_masking_input_fasta', 'gene_annotation_episode.episodic_workflow.root.a104.sequence_masking_inputs.parse_sequence_masking_output'], 'sheet_population': 'gene_annotation_episode.episodic_workflow.root.a104.sequence_masking_inputs.populate_sequence_masking_sheet', 'calculators': ['gene_annotation_episode.episodic_workflow.root.a104.library.sequence_masking_calculations.calculate_sequence_masking_components'], 'projection_implementation': 'gene_annotation_episode.episodic_workflow.root.a104.sequence_masking_result_views.project_masking_result', 'return_fields': ['source_ref', 'record_refs', 'status', 'artifacts', 'quantities', 'checks', 'statistics', 'failures', 'saved_data'], 'return_fact_sources': list(masking_fact_sources()), 'scientific_annotation_score': False}
                if job['operation']['program'] == 'windowmasker':
                    extractor['parsers'].append('gene_annotation_episode.episodic_workflow.root.a104.library.windowmasker_statistics.parse_windowmasker_statistics')
                if job['operation']['mode'] == 'convert_mask':
                    extractor['parsers'] = ['gene_annotation_episode.episodic_workflow.root.a104.sequence_masking_inputs.parse_masking_input_fasta', 'gene_annotation_episode.episodic_workflow.root.a104.blast_maskinfo_inputs.parse_blast_maskinfo']
                    extractor['sheet_population'] = 'gene_annotation_episode.episodic_workflow.root.a104.blast_maskinfo_inputs.populate_mask_conversion'
                if job['operation']['mode'] == 'create_counts':
                    extractor['parsers'] = ['gene_annotation_episode.episodic_workflow.root.a104.library.windowmasker_statistics.parse_windowmasker_statistics']
                    del extractor['sheet_population']
                    extractor['calculators'] = []
                value['extractors'][1] = extractor
                if selector is not None:
                    selected = validate_masking_result_selector(plain(selector), operation=job['operation'])
                    value['result_selection'] = deepcopy(selected)
                    if selected['mode'] == 'saved_recalculation':
                        del extractor['parsers']
                        extractor.pop('sheet_population', None)
                        extractor['calculation_basis'] = 'authenticated_saved_sheet_and_original_receipt'
                        value['status_operations'] = ['execution.results.status']
                        value['extractors'][0] = {'operation': 'execution.results.status', 'implementation': _NATIVE_RESULT_IMPLEMENTATIONS.get(getattr(self, 'native_result_owner', None), {}).get('native_blast_masking_results'), 'observation_basis': 'original_recorded_observation_and_retained_sheet_custody', 'fresh_native_observation': False}
            if 'native_blast_standard_database' in target['assignment']['requested_job']:
                from .native_blast_standard_database_result_views import standard_blast_database_fact_sources, standard_blast_database_metric_definitions, validate_standard_blast_database_selector
                job = target['assignment']['requested_job']['native_blast_standard_database']
                value['selected_outputs'] = deepcopy(job['outputs'])
                value['database_manifests'] = [deepcopy(row['manifest_file']) for row in job['databases']]
                value['status_meanings'] = {'observed_state': 'original_selected_pbs_attempt', 'logs': 'selected_original_stdout_stderr_windows', 'result_available': 'observed_attempt_availability', 'scientific_result_validation': 'complete_authenticated_capture_and_requested_frozen_projection', 'process_liveness_establishes_productive_work': False}
                value['numerical_metric_catalog'] = standard_blast_database_metric_definitions()
                if selector is not None:
                    value['result_selection'] = validate_standard_blast_database_selector(plain(selector), program=job['program'])
                value['acquisition_operations'] = ['execution.results.status', 'execution.results.collect']
                value['extractors'][1] = {'operation': 'execution.results.collect', 'implementation': _NATIVE_RESULT_IMPLEMENTATIONS.get(getattr(self, 'native_result_owner', None), {}).get('native_blast_standard_database_results'), 'parser': 'gene_annotation_episode.episodic_workflow.root.a104.blast_report_collection.parse_blast_report_collection', 'input_population': 'gene_annotation_episode.episodic_workflow.root.a104.native_blast_standard_database_metadata.prepare_standard_blast_database_inputs', 'sheet_population': 'gene_annotation_episode.episodic_workflow.root.a104.native_blast_standard_database_metadata.populate_standard_blast_database_sheets', 'calculators': ['gene_annotation_episode.episodic_workflow.root.a104.native_blast_standard_database_calculators.calculate_standard_blast_database_sheets'], 'return_fields': ['capture', 'preparation', 'publication', 'record_refs', 'failures', 'complete'], 'return_fact_sources': list(standard_blast_database_fact_sources()), 'scientific_publication': ['qualified_query_hsp', 'source_only'], 'observation_validator': 'gene_annotation_episode.episodic_workflow.root.a104.native_blast_standard_database_result_publication.validate_standard_blast_database_observation'}
            if 'native_blast_database' in target['assignment']['requested_job']:
                from .native_blast_database_result_views import native_blast_database_fact_sources, native_blast_database_metric_definitions, validate_native_blast_database_result_selector, FUNCTION_SELECTOR, FUNCTION_FAMILIES, SAVED_INPUT_SOURCE
                job = target['assignment']['requested_job']['native_blast_database']
                value['selected_outputs'] = deepcopy(job['outputs'])
                value['database_manifests'] = [deepcopy(row['manifest_file']) for row in job['databases']]
                value['status_meanings'] = {'observed_state': 'original_selected_pbs_attempt', 'logs': 'selected_original_stdout_stderr_windows', 'result_available': 'observed_attempt_availability', 'scientific_result_validation': 'complete_authenticated_capture_and_requested_frozen_projection', 'process_liveness_establishes_productive_work': False}
                value['numerical_metric_catalog'] = native_blast_database_metric_definitions()
                if selector is not None:
                    value['result_selection'] = validate_native_blast_database_result_selector(plain(selector), program=job['program'])
                value['acquisition_operations'] = ['execution.results.status', 'execution.results.collect']
                value['extractors'][1] = {'operation': 'execution.results.collect', 'implementation': _NATIVE_RESULT_IMPLEMENTATIONS.get(getattr(self, 'native_result_owner', None), {}).get('native_blast_database_results'), 'parser': 'gene_annotation_episode.episodic_workflow.root.a104.blast_report_collection.parse_blast_report_collection', 'input_population': 'gene_annotation_episode.episodic_workflow.root.a104.native_blast_database_metadata.prepare_native_blast_database_inputs', 'sheet_population': 'gene_annotation_episode.episodic_workflow.root.a104.native_blast_database_metadata.populate_native_blast_database_sheets', 'calculators': ['gene_annotation_episode.episodic_workflow.root.a104.native_blast_database_result_worker.calculate_native_blast_database_sheets'], 'return_fields': ['capture', 'preparation', 'publication', 'record_refs', 'failures', 'complete'], 'return_fact_sources': list(native_blast_database_fact_sources()), 'scientific_publication': ['qualified_query_hsp', 'source_only'], 'observation_validator': 'gene_annotation_episode.episodic_workflow.root.a104.native_blast_database_result_publication.validate_native_blast_database_observation'}
                selected = value.get('result_selection')
                if selected is not None and selected['version'] != FUNCTION_SELECTOR:
                    value['numerical_metric_catalog'] = native_blast_database_metric_definitions(include_vdb_function=False)
                    new_sources = {SAVED_INPUT_SOURCE, *('execution_blast_database_' + f + '_rows' for f in FUNCTION_FAMILIES)}
                    value['extractors'][1]['return_fact_sources'] = [s for s in value['extractors'][1]['return_fact_sources'] if s not in new_sources]
                if selected is not None and selected['version'] == FUNCTION_SELECTOR:
                    extractor = value['extractors'][1]
                    extractor['return_fields'] += ['calculation_input', 'reused_result_receipt']
                    extractor['calculators'].append('gene_annotation_episode.episodic_workflow.root.a104.blast_vdb_function_calculators.calculate_blast_vdb_function_components')
                    extractor['calculation_input'] = deepcopy(selected['calculation_input'])
                    extractor['calculator_parameters'] = deepcopy(selected['vdb_function_model'])
                    if selected['calculation_input']['mode'] == 'saved_function_sheet':
                        for key in ('parser', 'input_population', 'sheet_population'):
                            del extractor[key]
                        extractor['saved_input_validation'] = 'gene_annotation_episode.episodic_workflow.root.a104.native_blast_database_returns.NativeBLASTDatabaseReturns.resolve_saved_function_input'
                        extractor['calculation_basis'] = 'authenticated_saved_function_sheet_and_original_receipt'
                        extractor['scientific_publication'] = ['source_only']
                        del extractor['observation_validator']
                        value['status_operations'] = []
                        value['acquisition_operations'] = ['execution.results.collect']
                        value['extractors'] = [extractor]
                    else:
                        extractor['function_sheet_population'] = 'gene_annotation_episode.episodic_workflow.root.a104.native_blast_vdb_function_metadata.populate_native_blast_vdb_function_sheets'
            if 'native_blast' in target['assignment']['requested_job']:
                from .blast_pairwise_result_views import FAMILY_SOURCES, NATIVE_BLAST_RESULT_SELECTOR_SCHEMA, validate_native_blast_result_selector
                program = target['assignment']['requested_job']['native_blast']['program']
                families = tuple(FAMILY_SOURCES)
                value['selected_outputs'] = deepcopy(target['assignment']['requested_job']['native_blast']['outputs'])
                value['status_meanings'] = {'observed_state': 'original_selected_local_attempt', 'logs': 'selected_original_stdout_stderr_windows', 'result_available': 'observed_report_or_bundle_availability', 'scientific_result_validation': 'complete_capture_and_requested_numerical_projection', 'process_liveness_establishes_productive_work': False}
                value['result_selector_schema'] = deepcopy(NATIVE_BLAST_RESULT_SELECTOR_SCHEMA)
                if selector is not None:
                    selected = validate_native_blast_result_selector(selector, program=program)
                    value['projection'] = deepcopy(selected['projection'])
                    families = (selected['projection']['family'],)
                value['acquisition_operations'] = ['execution.results.status', 'execution.results.collect']
                value['extractors'][1] = {'operation': 'execution.results.collect', 'implementation': _NATIVE_RESULT_IMPLEMENTATIONS.get(getattr(self, 'native_result_owner', None), {}).get('native_blast_results'), 'parser': 'gene_annotation_episode.episodic_workflow.root.a104.blast_report_collection.parse_blast_report_collection', 'sheet_population': 'gene_annotation_episode.episodic_workflow.root.a104.blast_pairwise_results.populate_blast_pairwise_sheet', 'calculators': ['gene_annotation_episode.episodic_workflow.root.a104.blast_pairwise_results.calculate_blast_pairwise_components'], 'return_fields': ['source_ref', 'record_refs', 'rows', 'failures', 'complete'], 'return_fact_sources': ['execution_result_refs', 'execution_result_origin', *(FAMILY_SOURCES[family] for family in families)]}
            if 'native_hmmer' in target['assignment']['requested_job']:
                from .hmmer_native_result_views import FAMILY_SOURCES, family_for_program
                program = target['assignment']['requested_job']['native_hmmer']['program']
                value['acquisition_operations'] = ['execution.results.status', 'execution.results.collect']
                value['extractors'][1] = {'operation': 'execution.results.collect', 'implementation': _NATIVE_RESULT_IMPLEMENTATIONS.get(getattr(self, 'native_result_owner', None), {}).get('native_hmmer_results'), 'return_fields': ['source_ref', 'record_refs', 'rows', 'failures', 'complete'], 'return_fact_sources': ['execution_result_refs', 'execution_result_origin', FAMILY_SOURCES[family_for_program(program)]]}
            if 'native_hmmer_preparation' in target['assignment']['requested_job']:
                from .hmmer_preparation_result_views import preparation_fact_sources, preparation_projection_catalog, validate_preparation_result_selector
                job = target['assignment']['requested_job']['native_hmmer_preparation']
                value['projection_catalog'] = preparation_projection_catalog(job['program'], job['mode'])
                if selector is not None:
                    value['result_selection'] = validate_preparation_result_selector(plain(selector), program=job['program'], mode=job['mode'])
                value['acquisition_operations'] = ['execution.results.status', 'execution.results.collect']
                value['extractors'][1] = {'operation': 'execution.results.collect', 'implementation': _NATIVE_RESULT_IMPLEMENTATIONS.get(getattr(self, 'native_result_owner', None), {}).get('native_hmmer_preparation_results'), 'return_fields': ['source_ref', 'record_refs', 'rows', 'artifacts', 'population', 'failures', 'complete'], 'return_fact_sources': ['execution_result_refs', 'execution_result_origin', *preparation_fact_sources()], 'scientific_annotation_score': False}
            for extractor in value['extractors']:
                if extractor.get('implementation') is None:
                    extractor['implementation_status'] = 'private_results_counterpart_unbound'
            return value
        resource_id = target['resource_id']
        services = getattr(self.api_execution, 'services', {})
        if resource_id not in services:
            if _appservice_target(target):
                raise ContractError('bvbrc_appservice_service_not_bound')
            value['status_operations'] = ['api.hmmer.status']
            value['acquisition_operations'] = ['api.hmmer.result']
            value['extractors'] = [{'operation': 'api.hmmer.status', 'implementation': 'gene_annotation_episode.episodic_workflow.root.a104.library.hmmer_record_values._native_status', 'return_fields': ['native_status', 'state'], 'return_fact_sources': ['monitoring_progress_refs', 'monitoring_execution_state', 'monitoring_result_available']}, {'operation': 'api.hmmer.result', 'implementation': 'gene_annotation_episode.episodic_workflow.root.a104.tools.ToolRegistry.publish_hmmer_result', 'return_fields': ['source_ref', 'records', 'projection_errors'], 'return_fact_sources': ['execution_result_refs']}]
            return value
        service = services[resource_id]
        request = target['assignment']['request']
        if _appservice_target(target):
            return self._describe_appservice(value, target, body, service, selector)
        value['status_operations'] = [row['name'] for row in service.capabilities() if row['name'].endswith('.status')]
        try:
            acquisition = service.result_catalog(request, selector or {})
        except ValueError:
            acquisition = []
        value['acquisition_operations'] = [row['name'] for row in acquisition]
        implementation = type(service).__module__ + '.' + type(service).__qualname__
        for operation in value['status_operations']:
            value['extractors'].append({'operation': operation, 'implementation': implementation + '.decode', 'return_fields': ['state', 'native_handle', 'result_available', 'facts', 'failure_code'], 'return_fact_sources': ['monitoring_progress_refs', 'monitoring_execution_state', 'monitoring_result_available']})
        for operation in value['acquisition_operations']:
            if operation in value['status_operations']:
                continue
            value['extractors'].append({'operation': operation, 'implementation': implementation + '.publish', 'return_fields': ['source_ref', 'records'], 'return_fact_sources': ['execution_result_refs']})
        if service.service == 'bvbrc_data' and request.get('version') == 'bvbrc_data_request_v2':
            from .bvbrc_data_publication import publish_bvbrc_data
            from .bvbrc_data_readers import parse_data_snapshot
            from .bvbrc_data_calculators import calculate_page_counts, calculate_facet_fractions, calculate_feature_sequence_counts
            from .bvbrc_data_feature_sequences import extract_feature_sequence_join
            from .bvbrc_data_molecular import extract_molecular_experiment_rows
            from .bvbrc_data_views import project_bvbrc_data_facts, validate_data_result_selector

            def function_name(function):
                return function.__module__ + '.' + function.__qualname__
            value.update(request=deepcopy(request), observed_response_media_type=body['snapshot']['media_type'], projection=None, page_selector=None, observation_basis='original_retained_response')
            if not acquisition:
                return value
            selected = validate_data_result_selector(selector, request=request)
            projection = selected['projection']
            value.update(projection=deepcopy(projection), page_selector=deepcopy(selected['page']))
            fact_sources = ['execution_bvbrc_pages', 'execution_bvbrc_counts']
            calculators = [calculate_page_counts]
            metadata_extractors = []
            parameters = {}
            if request['mode'] == 'facet':
                fact_sources.append('execution_bvbrc_facets')
                calculators.append(calculate_facet_fractions)
                parameters[function_name(calculate_facet_fractions)] = {'denominator_policy': 'same_response_exact_document_count'}
            if projection['family'] == 'collection_rows':
                fact_sources.append('execution_bvbrc_numeric_rows')
            elif projection['family'] == 'feature_sequence':
                fact_sources.append('execution_bvbrc_feature_sequence_rows')
                metadata_extractors.append(extract_feature_sequence_join)
                calculators.append(calculate_feature_sequence_counts)
            elif projection['family'] == 'molecular_experiment':
                fact_sources.append('execution_bvbrc_expression_rows')
                metadata_extractors.append(extract_molecular_experiment_rows)
            for extractor in value['extractors']:
                if extractor['operation'] == 'api.bvbrc.data.result':
                    extractor.update(implementation=function_name(publish_bvbrc_data), service_implementation=implementation + '.publish', parser=function_name(parse_data_snapshot), metadata_extractors=[function_name(function) for function in metadata_extractors], calculators=[function_name(function) for function in calculators], calculator_parameters=parameters, projection_implementation=function_name(project_bvbrc_data_facts), return_fields=['source_ref', 'raw_artifact_ref', 'grading_artifact_ref', 'collection', 'mode', 'parse_status', 'qualification', 'requested_projection_complete', 'projection_failures'], return_fact_sources=['execution_result_refs', *fact_sources])
            return value
        if service.service == 'ncbi_blast':
            from .blast_result_views import BLAST_HSP_FACT_SCHEMA
            for extractor in value['extractors']:
                if extractor['operation'] == 'api.blast.status':
                    extractor['implementation'] = 'gene_annotation_episode.episodic_workflow.root.a104.blast_search.status'
                    extractor['native_return_schema'] = {'type': 'object', 'additionalProperties': False, 'required': ['status', 'has_hits'], 'properties': {'status': {'type': 'string', 'enum': ['WAITING', 'READY', 'FAILED', 'UNKNOWN']}, 'has_hits': {'type': ['boolean', 'null']}}}
                elif extractor['operation'] == 'api.blast.fetch':
                    extractor['implementation'] = 'gene_annotation_episode.episodic_workflow.root.a104.tools.ToolRegistry._import_blast'
                    extractor['return_fact_sources'].append('execution_blast_hsps')
                    extractor['recorded_return_schema'] = deepcopy(BLAST_HSP_FACT_SCHEMA)
        return value

    def _describe_appservice(self, value, target, body, service, selector):
        """Describe exact saved task operands and installed support readers."""
        from .api_bvbrc_appservice import _NATIVE_STATES, _RAW_STATES
        prefix = 'api.bvbrc_appservice.'
        handoff = body['task_handoff']
        original = handoff['original_task']
        implementation = type(service).__module__ + '.' + type(service).__qualname__
        available = [row['name'] for row in service.result_capabilities()]
        acquisition = [] if selector is None else [row['name'] for row in service.result_catalog(target['assignment']['request'], selector)]
        value.update(native_application_id=original['native_application_id'], definition_evidence=deepcopy(handoff['definition_evidence']), submitted_parameters=deepcopy(original['submitted_parameters']), submitted_start_parameters=deepcopy(original['submitted_start_parameters']), native_observation_methods={'query_tasks': {'operation': prefix + 'status', 'method': 'AppService.query_tasks'}, 'stdout': {'operation': prefix + 'task_info', 'method': 'GET task_info/{task_id}/stdout'}, 'stderr': {'operation': prefix + 'task_info', 'method': 'GET task_info/{task_id}/stderr'}}, status_operations=[name for name in (prefix + 'status', prefix + 'task_info') if name in available], acquisition_operations=acquisition, available_result_operations=available, native_states={'query_tasks_field': 'status', 'query_tasks_mapping': deepcopy(_NATIVE_STATES), 'submission_field': 'state_code', 'submission_mapping': deepcopy(_RAW_STATES), 'unrecognized_state': 'unknown', 'log_observation_state': 'unknown'}, progress_measurements={'native_timing_fields': ['submit_time', 'start_time', 'completed_time', 'elapsed_time'], 'native_timing_representation': 'unconverted_native_strings', 'elapsed_time_format': 'SQL_TIMEDIFF', 'timezone': None, 'derived_duration_seconds': [], 'derived_log_throughput': None}, log_format={'representation': 'signature_redacted_http_bytes', 'offset_basis': 'retained_response_bytes', 'state_observed': False}, output_association={'task_info_fields': ['job_result_id', 'job_result_folder'], 'manifest': 'job_result', 'member_selection': 'explicit_output_files_ordinal', 'immutable_producer_bytes_established_by_path_or_uuid': False}, configured_scientific_adapters=deepcopy(self.resources[target['resource_id']].get('scientific_adapters', [])))
        common = ['monitoring_progress_refs', 'monitoring_execution_state', 'monitoring_result_available']
        value['extractors'] = [{'operation': 'progress.observe', 'native_operation': native_operation, 'implementation': implementation + '.decode', 'parser': 'gene_annotation_episode.episodic_workflow.root.a104.bvbrc_analysis_protocol.parse_task_records' if native_operation == 'query_tasks' else 'gene_annotation_episode.episodic_workflow.root.a104.bvbrc_appservice_readers.decode_task_info', 'parser_signature': 'parse_task_records(value, *, operation, requested_task_ids=None)' if native_operation == 'query_tasks' else 'decode_task_info(content, *, task_id, file)', 'return_fields': ['state', 'native_handle', 'result_available', 'facts', 'failure_code'], 'return_fact_sources': list(common)} for native_operation in ('query_tasks', 'stdout', 'stderr')]
        for operation in acquisition:
            download = operation == prefix + 'download'
            value['extractors'].append({'operation': operation, 'implementation': implementation + ('.publish' if download else '.decode'), 'purpose': 'selected_artifact_publication' if download else 'support', 'return_fact_sources': ['execution_result_refs'] if download else [], 'return_fields': ['source_ref', 'records'] if download else ['state', 'native_handle', 'result_available', 'facts', 'failure_code'], **({'parser': 'gene_annotation_episode.episodic_workflow.root.a104.bvbrc_appservice_readers.qualify_download', 'parser_signature': 'qualify_download(snapshot, *, capability, object_binding)', 'scientific_parser': None, 'scientific_publication_requires_explicit_bound_adapter': True} if download else {})})
        return value

    def _qualified(self, target):
        target = validate_target(target)
        original = self.read_target(target['handle'], target['scope'])
        if canonical(target) != canonical(original):
            raise ContractError('execution_target_identity_conflict')
        return target

    def _native_identity(self, target):
        _, body = self._native(target['handle'], target['scope'])
        receipt = body['receipt']
        detail = receipt['outcome'].get('native_outcome') or {}
        if target['resource_kind'] == 'hpc' and receipt['tool_name'] == 'exec_command':
            return {'run_id': self.run_id, 'origin_episode_id': target['origin_episode_id'], 'resource_id': target['resource_id'], 'requested_job_sha256': target['request_sha256'], 'actual_job': deepcopy(detail['actual_job'])}
        value = {'run_id': self.run_id, 'origin_episode_id': target['origin_episode_id'], 'attempt_id': detail.get('attempt_id'), 'original_operation_key': detail.get('attempt_operation_key') or (receipt['operation_key'] if digest(receipt['operation_key']) == detail.get('attempt_id') else None)}
        if {'native_blast_masking', 'native_blast_utility'} & set(target['assignment']['requested_job']):
            value.update(resource_id=target['resource_id'], requested_job_sha256=target['request_sha256'])
        return value

    @staticmethod
    def _failed_handoff_profile(target):
        if target['resource_kind'] == 'local':
            return bool({'native_blast_masking', 'native_blast_utility'} & set(target['assignment']['requested_job']))
        return target['resource_kind'] == 'hpc' and bool({'native_blast_database', 'native_blast_standard_database'} & set(target['assignment']['requested_job']))

    @classmethod
    def _handoff_values(cls, target, body):
        """Decide only from an already qualified original stored receipt."""
        if target['resource_kind'] == 'api':
            return (True, True)
        status = body['receipt']['outcome']['facts']['requested_job']['status']
        usable = status in {'submitted', 'running', 'completed'}
        return (usable, usable or (status == 'failed' and cls._failed_handoff_profile(target)))

    def _handoff_reader(self):
        """Return a detached metadata reader whose reuse ends with its caller."""
        receipts, targets = ({}, {})

        def read(handle, scope):
            try:
                key = (self.run_id, handle, canonical(plain(scope)))
            except (ValueError, TypeError, OverflowError, RecursionError):
                target, body = self._read_target(handle, scope, include_native_receipt=True)
                return deepcopy((target, *self._handoff_values(target, body)))
            if key not in targets:
                candidate_receipts = dict(receipts)
                target, body = self._read_target(handle, scope, include_native_receipt=True, _receipt_reads=candidate_receipts)
                usable, returnable = self._handoff_values(target, body)
                receipts.update(candidate_receipts)
                targets[key] = (deepcopy(target), usable, returnable)
            return deepcopy(targets[key])
        return read

    def usable_handoff(self, target):
        """Original endpoint evidence; a later failure cannot rewrite it."""
        target = self._qualified(target)
        if target['resource_kind'] == 'api':
            return True
        _, body = self._native(target['handle'], target['scope'])
        return self._handoff_values(target, body)[0]

    def returnable_handoff(self, target):
        """An authenticated failed native attempt can own qualified partial work."""
        target = self._qualified(target)
        if self.usable_handoff(target):
            return True
        if not self._failed_handoff_profile(target):
            return False
        _, body = self._native(target['handle'], target['scope'])
        return self._handoff_values(target, body)[1]

    def observe_target(self, target, *, operation_key, native_operation=None, observation_context=None):
        target = self._qualified(target)
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError('execution_progress_operation_key_required')
        _validate_native_observation(target, native_operation)
        native_options = native_observation_options(native_operation, observation_context)
        from .terminal_scientific_evidence import is_terminal_target, terminal_observation
        if is_terminal_target(target):
            _, body = self._native(target['handle'], target['scope'])
            proof = body['receipt']['outcome']['native_outcome']['scientific_command_proof']
            return validate_resource_observation(terminal_observation(target, proof))
        try:
            if target['resource_kind'] == 'api':
                observation = (self.api_execution if self.api_observer is None else self.api_observer).observe_target(target, operation_key=operation_key, **native_options)
            else:
                observation = self.operations[target['resource_id']].observe_execution(target['assignment'], target['execution_id'], **self._native_identity(target), log_window_bytes=getattr(self, 'log_window_bytes', 8192), log_roles=getattr(self, 'log_roles', ('stdout', 'stderr')))
        except (ValueError, OSError) as error:
            raise ContractError('execution_target_observation_failed', detail={'reason': str(error)}) from error
        return validate_resource_observation(observation)

    def read_file(self, target, *, path, offset, limit, operation_key=None):
        target = self._qualified(target)
        if target['resource_kind'] == 'api':
            raise ContractError('native_output_target_required')
        from .terminal_scientific_evidence import is_terminal_target, verified_snapshot_path
        if is_terminal_target(target):
            _, body = self._native(target['handle'], target['scope'])
            proof = body['receipt']['outcome']['native_outcome']['scientific_command_proof']
            matches = [row for row in proof['output_snapshots'] if row['path'] == path]
            if not matches:
                matches = [row for row in proof['input_snapshots'] if row['path'] == path]
            if len(matches) != 1 or not matches[0]['available']:
                raise FileNotFoundError(path)
            if type(offset) is not int or offset < 0 or type(limit) is not int or (limit < 1):
                raise ValueError('native_output_window_invalid')
            actual = matches[0]
            with verified_snapshot_path(actual).open('rb') as stream:
                stream.seek(offset)
                raw = stream.read(limit)
            import base64
            return {'path': path, 'offset': offset, 'returned_bytes': len(raw), 'size_bytes': actual['size_bytes'], 'bytes_base64': base64.b64encode(raw).decode('ascii')}
        manifest = target['assignment'].get('scientific_manifest')
        if target['resource_kind'] == 'hpc' and isinstance(manifest, dict) and (manifest['path'] == path):
            _, body = self._native(target['handle'], target['scope'])
            detail = body['receipt']['outcome']['native_outcome']
            snapshots = [row for row in detail.get('input_snapshots', []) if row['path'] == path]
            if len(snapshots) != 1 or not snapshots[0]['available'] or (not snapshots[0]['source_stable_during_read']) or (snapshots[0]['sha256'] != manifest['sha256']) or (snapshots[0]['size_bytes'] != manifest['size_bytes']):
                raise ValueError('native_database_original_manifest_snapshot_unavailable')
            value = self.operations[target['resource_id']].read_output(target['assignment'], target['execution_id'], path=snapshots[0]['captured_path'], offset=offset, limit=limit, **self._native_identity(target))
            return {**value, 'path': path}
        return self.operations[target['resource_id']].read_output(target['assignment'], target['execution_id'], path=path, offset=offset, limit=limit, **self._native_identity(target))

    def authenticate_standard_blast_database_attempt(self, target):
        """Authenticate the original remote ledger before interpreting its bundle."""
        target = self._qualified(target)
        if target['resource_kind'] != 'hpc' or 'native_blast_standard_database' not in target['assignment']['requested_job']:
            raise ContractError('native_blast_standard_database_target_required')
        _, current = self._native(target['handle'], target['scope'])
        if current['receipt']['tool_name'] == 'exec_command':
            return self._terminal_database_attempt(target, current['receipt'])
        witness = self.operations[target['resource_id']].authenticate_standard_blast_database_attempt(target['assignment'], target['execution_id'], **self._native_identity(target))
        _, body = self._native(target['handle'], target['scope'])
        detail = body['receipt']['outcome']['native_outcome']
        attempt = witness['authenticated_attempt']
        if witness['plan_path'] != detail.get('native_blast_standard_database_plan_path') or attempt['plan_sha256'] != detail.get('native_blast_standard_database_plan_sha256'):
            raise ContractError('native_blast_standard_database_original_receipt_plan_conflict')
        return witness

    def authenticate_native_blast_database_attempt(self, target):
        """Authenticate the original remote ledger before interpreting its bundle."""
        target = self._qualified(target)
        if target['resource_kind'] != 'hpc' or 'native_blast_database' not in target['assignment']['requested_job']:
            raise ContractError('native_blast_database_target_required')
        _, current = self._native(target['handle'], target['scope'])
        if current['receipt']['tool_name'] == 'exec_command':
            return self._terminal_database_attempt(target, current['receipt'])
        witness = self.operations[target['resource_id']].authenticate_native_blast_database_attempt(target['assignment'], target['execution_id'], **self._native_identity(target))
        _, body = self._native(target['handle'], target['scope'])
        detail = body['receipt']['outcome']['native_outcome']
        attempt = witness['authenticated_attempt']
        if witness['plan_path'] != detail.get('native_blast_database_plan_path') or attempt['plan_sha256'] != detail.get('native_blast_database_plan_sha256'):
            raise ContractError('native_blast_database_original_receipt_plan_conflict')
        return witness

    def _terminal_database_attempt(self, target, receipt):
        from .native_database_terminal_custody import qualify_manifest
        manifest = target['assignment'].get('scientific_manifest')
        if not isinstance(manifest, dict):
            raise ContractError('native_database_scientific_manifest_not_supplied')
        offset, chunks = (0, [])
        while offset < manifest['size_bytes']:
            row = self.read_file(target, path=manifest['path'], offset=offset, limit=min(1024 * 1024, manifest['size_bytes'] - offset))
            raw = base64.b64decode(row['bytes_base64'], validate=True)
            if row['offset'] != offset or row['size_bytes'] != manifest['size_bytes'] or row['returned_bytes'] != len(raw) or (not raw):
                raise ContractError('native_database_manifest_snapshot_read_conflict')
            chunks.append(raw)
            offset += len(raw)
        return qualify_manifest(target, receipt, b''.join(chunks), configuration=self.resources[target['resource_id']])

class ExecutionProgressProvider:
    """Durable capture and replay for one selected resource observation."""

    def __init__(self, store, *, run_id, directory, resources, api_execution, log_window_bytes, log_roles, api_observer=None, native_result_owner=None):
        if type(log_window_bytes) is not int or log_window_bytes <= 0:
            raise ValueError('execution_progress_log_window_bytes_required')
        allowed_logs = {'stdout', 'stderr'}
        if not isinstance(log_roles, (tuple, list)) or any((role not in allowed_logs for role in log_roles)) or len(set(log_roles)) != len(log_roles):
            raise ValueError('execution_progress_log_roles_required')
        self.store, self.run_id = (store, run_id)
        self.resources = json.loads(canonical(resources))
        self.directory = Path(directory)
        self.log_window_bytes, self.log_roles = (log_window_bytes, tuple(log_roles))
        self.targets = ExecutionTargetReader(store, run_id=run_id, directory=directory, resources=resources, api_execution=api_execution, **{} if api_observer is None else {'api_observer': api_observer}, **{} if native_result_owner is None else {'native_result_owner': native_result_owner})
        self.targets.log_window_bytes, self.targets.log_roles = (log_window_bytes, self.log_roles)
        with store.transaction():
            store.db.execute('CREATE TABLE IF NOT EXISTS runtime_execution_progress_operations (\n                run_id TEXT NOT NULL, operation_key TEXT NOT NULL, signature TEXT NOT NULL,\n                result TEXT NOT NULL, PRIMARY KEY(run_id,operation_key))')
            store.db.execute('CREATE TABLE IF NOT EXISTS runtime_execution_progress_custody (\n                run_id TEXT NOT NULL, target_handle TEXT NOT NULL, kind TEXT NOT NULL,\n                signature TEXT NOT NULL, source_ref TEXT NOT NULL REFERENCES records(id),\n                observed_at TEXT NOT NULL, PRIMARY KEY(run_id,target_handle,kind,signature))')
            store.db.execute('CREATE TABLE IF NOT EXISTS runtime_execution_progress_snapshots (\n                run_id TEXT NOT NULL, target_handle TEXT NOT NULL, scope TEXT NOT NULL,\n                signature TEXT NOT NULL, progress_ref TEXT NOT NULL REFERENCES records(id),\n                snapshot TEXT NOT NULL, PRIMARY KEY(run_id,target_handle,scope,signature))')
            store.db.execute('CREATE TABLE IF NOT EXISTS runtime_execution_progress_dependencies (\n                run_id TEXT NOT NULL, physical_identity TEXT NOT NULL,\n                target_handle TEXT NOT NULL, relationship TEXT NOT NULL,\n                PRIMARY KEY(run_id,physical_identity))')
        self.native_result_owner = native_result_owner

    def as_record(self):
        return {'version': VERSION, 'configuration': {'resources': deepcopy(self.resources), 'log_window_bytes': self.log_window_bytes, 'log_roles': list(self.log_roles), **({'native_result_owner': self.native_result_owner} if self.native_result_owner is not None else {})}}

    def scope(self, handle):
        return self.targets.scope(handle)

    def describe_target(self, handle, scope):
        return self.targets.describe_target(handle, scope)

    def latest_saved_observation(self, handle, scope, *, require_native_state=False):
        """Read saved progress, optionally only an actual native job state."""
        target = self.targets.read_target(handle, scope)
        row = self.store.db.execute('SELECT snapshot FROM runtime_execution_progress_snapshots WHERE run_id=? AND target_handle=? ' + ("AND json_extract(snapshot, '$.execution_status.native.native.facts.native_state') IS NOT NULL " if require_native_state else '') + "ORDER BY json_extract(snapshot,'$.observed_at') DESC LIMIT 1", (self.run_id, handle)).fetchone()
        if row is None:
            return None
        snapshot = json.loads(row['snapshot'])
        if snapshot.get('target_handle') != handle or snapshot.get('execution_status', {}).get('handle') != handle or target['resource_kind'] != 'api':
            raise ContractError('execution_saved_observation_identity_conflict')
        return snapshot

    def _operation(self, operation_key, selection):
        if operation_key is not None and (not isinstance(operation_key, str) or not operation_key):
            raise ContractError('execution_progress_operation_key_required')
        signature = digest({'selection': selection, 'provider': self.as_record()})
        row = None if operation_key is None else self.store.db.execute('SELECT signature,result FROM runtime_execution_progress_operations WHERE run_id=? AND operation_key=?', (self.run_id, operation_key)).fetchone()
        if row is not None and row['signature'] != signature:
            raise ContractError('execution_progress_operation_identity_conflict')
        return (signature, row)

    def _save_operation(self, operation_key, signature, result):
        if operation_key is not None:
            self.store.db.execute('INSERT INTO runtime_execution_progress_operations VALUES(?,?,?,?)', (self.run_id, operation_key, signature, canonical(result)))
        return result

    def _source(self, target, kind, body, *, captured, artifact=None, parents=()):
        signature = digest(_without_read_times(body))
        row = self.store.db.execute('SELECT source_ref,observed_at FROM runtime_execution_progress_custody WHERE run_id=? AND target_handle=? AND kind=? AND signature=?', (self.run_id, target['handle'], kind, signature)).fetchone()
        if row is not None:
            return (self.store.get(row['source_ref']), row['observed_at'])
        metadata = self.store.artifact(canonical(body), 'application/json')
        selected = metadata if artifact is None else artifact
        source = self.store.put('source', {'provider': 'execution.progress.' + kind, 'accession': None, 'uri': None, 'artifact_ref': selected, 'text_ref': selected, 'request_ref': metadata, 'version': VERSION, 'retrieved_at': captured, 'parent_source_refs': [reference for reference in dict.fromkeys([target['handle'], *parents]) if self.store.get(reference)['record_type'] == 'source']}, origin='tool')
        self.store.db.execute('INSERT INTO runtime_execution_progress_custody VALUES(?,?,?,?,?,?)', (self.run_id, target['handle'], kind, signature, source['id'], captured))
        return (source, captured)

    def observe(self, handle, requested_fields, scope, *, operation_key=None, native_operation=None, observation_context=None):
        fields = plain(requested_fields)
        if not isinstance(fields, list) or any((field not in _FIELDS for field in fields)) or len(set(fields)) != len(fields):
            raise ContractError('execution_progress_requested_fields_invalid')
        normalized = self.store.validate_scope(plain(scope))
        selection = {'operation': 'observe', 'handle': handle, 'fields': fields, 'scope': normalized}
        native_options = native_observation_options(native_operation, observation_context)
        if native_options:
            if operation_key is None:
                raise ContractError('execution_progress_operation_key_required')
            selection.update(native_operation=native_operation, observation_context=observation_context.as_record())
        signature, old = self._operation(operation_key, selection)
        if old is not None:
            return json.loads(old['result'])
        target = self.targets.read_target(handle, normalized)
        _validate_native_observation(target, native_operation)
        selected_key = operation_key or 'unkeyed-observation:' + digest([handle, _now()])
        if _appservice_target(target):
            prefix = f'{self.run_id}:{observation_context.episode_id}:'
            index = selected_key.removeprefix(prefix)
            if not selected_key.startswith(prefix) or not index.isdecimal() or str(int(index)) != index:
                raise ContractError('execution_progress_selected_action_required')
            selected = self.store.db.execute('SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?', (self.run_id, observation_context.episode_id, int(index))).fetchone()
            expected = {'kind': 'tool', 'tool': 'progress.observe', 'arguments': {'requested_fields': fields, 'native_operation': native_operation}}
            if selected is None or canonical(json.loads(selected['action'])) != canonical(expected):
                raise ContractError('execution_progress_selected_fields_conflict')
        observation = self.targets.observe_target(target, operation_key=selected_key, **native_options) if target['resource_kind'] == 'api' else None
        with self.store.transaction():
            signature, old = self._operation(operation_key, selection)
            if old is not None:
                return json.loads(old['result'])
            if observation is None:
                observation = self.targets.observe_target(target, operation_key=selected_key, **native_options)
            captured = observation['observed_at']
            status_source, original_time = self._source(target, 'status', {'version': 'execution_progress_observation_v1', 'target': target, 'observation': observation}, captured=captured)
            provenance = []
            for reference in observation['provenance_refs']:
                recorded = self.store.get(reference)
                if recorded['record_type'] == 'artifact':
                    source, _ = self._source(target, 'provenance', {'version': 'execution_progress_provenance_v1', 'target': target, 'original_provenance_ref': reference}, captured=captured, artifact=reference, parents=[status_source['id']])
                    provenance.append(source['id'])
                provenance.append(reference)
            observation['observed_at'] = original_time
            status_observation = observation
            if _appservice_target(target):
                status_observation = deepcopy(observation)
                status_observation['logs'] = []
                if 'log_windows' not in fields:
                    status_observation['outputs'] = [row for row in observation['outputs'] if row['role'] not in {'stdout', 'stderr'}]
                if 'measurements' not in fields:
                    status_observation['measurements'] = []
            status = resource_status(target, status_observation)
            measurements = []
            if 'measurements' in fields:
                measurements = [{'name': row['measure'], 'value': row['seconds'], 'unit': 'seconds', 'measured_at': original_time, 'provenance_ref': status_source['id']} for row in observation['measurements']]
            windows = []
            if 'log_windows' in fields:
                for row in observation['logs']:
                    if row['role'] not in self.log_roles:
                        continue
                    raw = base64.b64decode(row['bytes_base64'], validate=True)
                    offset = row['offset']
                    if _appservice_target(target):
                        removed = max(0, len(raw) - self.log_window_bytes)
                        raw, offset = (raw[removed:], offset + removed)
                    artifact = self.store.artifact(raw)
                    sha = hashlib.sha256(raw).hexdigest()
                    source, stamp = self._source(target, 'log', {'version': 'execution_progress_log_window_v1', 'target': target, 'role': row['role'], 'path': row['path'], 'original_start_byte': offset, 'original_end_byte': offset + len(raw), 'observed_file_size': row['observed_size'], 'content_sha256': sha, 'whole_file_atomic_snapshot': False}, captured=captured, artifact=artifact, parents=[status_source['id']])
                    windows.append({'source_ref': source['id'], 'artifact_ref': artifact, 'start_byte': 0, 'end_byte': len(raw), 'observed_at': stamp, 'content_sha256': sha})
            value = {'version': 'progress_snapshot_v1', 'target_handle': handle, 'observed_at': original_time, 'execution_status': status, 'measurements': measurements, 'log_windows': windows, 'committed_record_refs': [], 'dependencies': [], 'result_available': observation['result_available'], 'provenance_refs': list(dict.fromkeys([status_source['id'], *provenance, *(row['source_ref'] for row in windows)]))}
            snapshot_signature = digest(_without_read_times(value))
            row = self.store.db.execute('SELECT snapshot FROM runtime_execution_progress_snapshots WHERE run_id=? AND target_handle=? AND scope=? AND signature=?', (self.run_id, handle, canonical(normalized), snapshot_signature)).fetchone()
            if row is not None:
                value = json.loads(row['snapshot'])
            else:
                source, _ = self._source(target, 'snapshot', value, captured=original_time, parents=value['provenance_refs'])
                value['progress_ref'] = source['id']
                self.store.db.execute('INSERT INTO runtime_execution_progress_snapshots VALUES(?,?,?,?,?,?)', (self.run_id, handle, canonical(normalized), snapshot_signature, value['progress_ref'], canonical(value)))
            return self._save_operation(operation_key, signature, value)

    def direct_dependencies(self, handle, scope):
        self.targets.read_target(handle, scope)
        return []

    def dependency_from_outcome(self, source_context, outcome, operation_key):
        """Expose one actual episode→physical relationship after own commit."""
        if source_context.run_id != self.run_id:
            raise ContractError('execution_progress_dependency_outside_run')
        references = list(dict.fromkeys(plain(outcome).get('record_refs', [])))
        eligible = []
        for reference in references:
            try:
                target = self.targets.read_target(reference, source_context.scope)
            except (ValueError, KeyError):
                continue
            if target['origin_episode_id'] != source_context.episode_id:
                continue
            if target['resource_kind'] != 'api':
                _, body = self.targets._native(reference, source_context.scope)
            else:
                source = self.store.get(reference)
                body = self.targets.api_execution._read_handoff(reference, source_context.scope) if _appservice_target(target) else json.loads(self.store.get_artifact(source['artifact_ref']))
            if body['receipt']['operation_key'] != operation_key:
                continue
            prefix = f'{self.run_id}:{source_context.episode_id}:'
            index = operation_key.removeprefix(prefix)
            if not operation_key.startswith(prefix) or not index.isdecimal():
                raise ContractError('execution_dependency_selected_action_required')
            selected = self.store.db.execute('SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?', (self.run_id, source_context.episode_id, int(index))).fetchone()
            if selected is None or selected['result'] is None or reference not in json.loads(selected['result']).get('record_refs', []):
                raise ContractError('execution_dependency_outcome_not_committed')
            eligible.append(target)
        if not eligible:
            return None
        if len(eligible) != 1:
            raise ContractError('one_execution_dependency_per_selected_outcome_required')
        target = eligible[0]
        with self.store.transaction():
            signature, old = self._operation('dependency:' + operation_key, {'operation': 'dependency', 'target': target, 'episode_id': source_context.episode_id})
            if old is not None:
                return json.loads(old['result'])
            physical_identity = digest({key: target[key] for key in ('run_id', 'origin_episode_id', 'resource_id', 'resource_kind', 'execution_id', 'request_sha256')})
            existing = self.store.db.execute('SELECT relationship FROM runtime_execution_progress_dependencies WHERE run_id=? AND physical_identity=?', (self.run_id, physical_identity)).fetchone()
            if existing is not None:
                return self._save_operation('dependency:' + operation_key, signature, json.loads(existing['relationship']))
            stamp = _now()
            source, stamp = self._source(target, 'relationship', {'version': 'execution_resource_dependency_v1', 'run_id': self.run_id, 'owner_episode_id': source_context.episode_id, 'operation_key': operation_key, 'target': target}, captured=stamp)
            if target['resource_kind'] == 'api':
                original = self.store.get(target['handle'])
                body = self.targets.api_execution._read_handoff(target['handle'], target['scope']) if _appservice_target(target) else json.loads(self.store.get_artifact(original['artifact_ref']))
                state = {'submitted': 'pending', 'running': 'executing', 'completed': 'returned'}[body['receipt']['state']]
            else:
                _, body = self.targets._native(target['handle'], source_context.scope)
                state = {'submitted': 'pending', 'running': 'executing', 'completed': 'returned', 'failed': 'returned', 'unknown': 'pending'}[body['receipt']['outcome']['facts']['requested_job']['status']]
            result = {'handle': target['handle'], 'kind': 'job', 'relation_ref': source['id'], 'observed_at': stamp, 'state': state}
            self.store.db.execute('INSERT INTO runtime_execution_progress_dependencies VALUES(?,?,?,?)', (self.run_id, physical_identity, target['handle'], canonical(result)))
            return self._save_operation('dependency:' + operation_key, signature, result)
__all__ = ['ExecutionTargetReader', 'ExecutionProgressProvider', 'VERSION', 'describe_execution_target']
