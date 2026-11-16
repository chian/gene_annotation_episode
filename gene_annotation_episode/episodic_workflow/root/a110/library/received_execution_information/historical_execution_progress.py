"""Scoped observations of original API/native executions, separate from launch.

This is a read-only resource adapter for the existing recursive monitor. It
owns observation custody, never an episode loop, retry, or continuation rule.
"""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a110.communication import plain
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import canonical, digest
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_api_contracts import validate_target
from gene_annotation_episode.episodic_workflow.root.a110.practical_execution_operations import LocalPracticalOperations
from gene_annotation_episode.episodic_workflow.root.a110.terminal_execution import TerminalExecution
from gene_annotation_episode.episodic_workflow.root.a110.practical_execution_records import terminal_job_matches
from gene_annotation_episode.episodic_workflow.root.a110.practical_receipt_information import PracticalReceiptInformation, PROVIDER
VERSION = 'execution_progress_provider_v1'

def _appservice_target(target):
    assignment = target['assignment']
    if target['resource_kind'] != 'api' or assignment.get('service') != 'bvbrc_appservice':
        return False
    request = assignment.get('request', {})
    if assignment.get('version') != 'api_service_assignment_v1' or request.get('version') != 'bvbrc_appservice_request_v1' or request.get('effect_contract') != 'selected_api_effects_v1':
        raise ContractError('bvbrc_appservice_execution_contract_required')
    return True

class ExecutionTargetReader:
    """Validate source/run/scope/request first; observe exactly its native ID."""

    def __init__(self, store, *, run_id, directory, resources, api_execution):
        if not isinstance(run_id, str) or not run_id:
            raise ValueError('execution_progress_run_identity_required')
        self.store, self.run_id, self.directory = (store, run_id, Path(directory))
        self.resources = json.loads(canonical(resources))
        self.api_execution = api_execution
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
        if 'native_flux_balance' in assignment['requested_job']:
            from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_contracts import validate_flux_balance_record
            if assignment.get('resource_id') != resource_id or assignment['resource_kind'] != 'local':
                raise ValueError('native_flux_balance_resource_identity_conflict')
            self.operations[resource_id].validate_assignment(assignment)
            detail = receipt['outcome'].get('native_outcome') or {}
            file = validate_flux_balance_record('File', detail.get('native_flux_balance_input_binding_file'))
            if file['format'] != 'flux_balance_input_binding_receipt_v1' or file['artifact_ref'] != 'artifact_' + file['sha256']:
                raise ValueError('native_flux_balance_original_input_control_conflict')
            reference = receipt['arguments'].get('receipt_ref')
            if reference is not None:
                if receipt['tool_name'] not in {'practical.job.status', 'practical.job.collect'}:
                    raise ValueError('native_flux_balance_receipt_ancestry_conflict')
                original, prior = self._native(reference, body['scope'], _seen=(*_seen, handle), _receipt_reads=reads)
                prior_detail = prior['receipt']['outcome'].get('native_outcome') or {}
                if original['resource_id'] != resource_id or original['execution_id'] != job['execution_id'] or original['assignment']['workspace'] != assignment['workspace'] or (canonical(original['assignment']['requested_job']) != canonical(assignment['requested_job'])) or any((detail.get(key) != prior_detail.get(key) for key in ('attempt_id', 'attempt_operation_key', 'native_flux_balance_input_binding_file'))):
                    raise ValueError('native_flux_balance_receipt_ancestry_conflict')
                assignment = original['assignment']
                origin_episode_id = original['origin_episode_id']
            operation_key = detail.get('attempt_operation_key')
            attempt_id = detail.get('attempt_id')
            prefix = f'{self.run_id}:{origin_episode_id}:'
            index = operation_key.removeprefix(prefix) if isinstance(operation_key, str) else ''
            root = Path(assignment['workspace']) / '.episode-operations' / digest({'run': self.run_id, 'episode': origin_episode_id}) / digest(operation_key)
            observed = detail.get('observation', detail)
            if not isinstance(operation_key, str) or not operation_key.startswith(prefix) or (not index.isdecimal()) or (str(int(index)) != index) or (attempt_id != digest(operation_key)) or (job['execution_id'] != str(root / 'native.json')) or (observed.get('metadata', {}).get('policy') != self.operations[resource_id].policy.to_dict()):
                raise ValueError('native_flux_balance_original_attempt_mismatch')
            starts = self.receipts._sources(self.receipts._accession(origin_episode_id, operation_key))
            if len(starts) != 1:
                raise ValueError('native_flux_balance_original_start_receipt_missing')
            start = self._read_native_receipt(starts[0]['id'], body['scope'], reads)
            start_receipt = start['receipt']
            start_job = start_receipt['outcome'].get('facts', {}).get('requested_job', {})
            start_detail = start_receipt['outcome'].get('native_outcome') or {}
            if start['episode_id'] != origin_episode_id or start['assignment_sha256'] != digest(assignment) or start_receipt['tool_name'] != 'practical.job.start' or (start_receipt['operation_key'] != operation_key) or (start_job.get('execution_id') != job['execution_id']) or (start_job.get('resource_kind') != 'local') or (start_job.get('requested_job_sha256') != digest(assignment['requested_job'])) or (start_job.get('argv') != assignment['requested_job']['argv']) or (start_job.get('environment') != assignment['requested_job']['environment']) or any((start_detail.get(key) != detail.get(key) for key in ('attempt_id', 'attempt_operation_key', 'native_flux_balance_input_binding_file'))):
                raise ValueError('native_flux_balance_original_start_receipt_conflict')
        if 'native_blast_utility' in assignment['requested_job']:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_blast_utility_contracts import validate_native_blast_utility_plan
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
                raise ValueError('native_blast_utility_original_owner_conflict')
            expected = {'run_id': self.run_id, 'episode_id': origin_episode_id, 'resource_id': resource_id, 'execution_id': job['execution_id'], 'requested_job_sha256': digest(assignment['requested_job']), 'operation_key': detail.get('attempt_operation_key'), 'attempt_id': detail.get('attempt_id')}
            root = Path(assignment['workspace']) / '.episode-operations' / digest({'run': self.run_id, 'episode': origin_episode_id}) / owner['attempt_id']
            observed = detail.get('observation', detail)
            constraints = assignment['constraints']
            if owner != expected or plan['requested_job'] != assignment['requested_job'] or job['execution_id'] != str(root / 'native.json') or (plan['attempt_directory'] != str(root / 'blast-utility-attempt')) or (observed.get('metadata', {}).get('policy') != plan['policy']) or (self.operations[resource_id].policy.to_dict() != plan['policy']) or ('allocation' in constraints and constraints['allocation'] != plan['policy']) or any((key in constraints and constraints[key] != value for key, value in plan['policy'].items())):
                raise ValueError('native_blast_utility_original_attempt_mismatch')
        if 'native_blast_masking' in assignment['requested_job']:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_blast_masking_contracts import validate_native_blast_masking_plan
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
                raise ValueError('native_blast_masking_original_owner_conflict')
            expected = {'run_id': self.run_id, 'episode_id': origin_episode_id, 'resource_id': resource_id, 'execution_id': job['execution_id'], 'requested_job_sha256': digest(assignment['requested_job']), 'operation_key': detail.get('attempt_operation_key'), 'attempt_id': detail.get('attempt_id')}
            root = Path(assignment['workspace']) / '.episode-operations' / digest({'run': self.run_id, 'episode': origin_episode_id}) / owner['attempt_id']
            observed = detail.get('observation', detail)
            constraints = assignment['constraints']
            if owner != expected or plan['requested_job'] != assignment['requested_job'] or job['execution_id'] != str(root / 'native.json') or (plan['attempt_directory'] != str(root / 'blast-masking-attempt')) or (observed.get('metadata', {}).get('policy') != plan['policy']) or ('allocation' in constraints and constraints['allocation'] != plan['policy']) or any((key in constraints and constraints[key] != value for key, value in plan['policy'].items())):
                raise ValueError('native_blast_masking_original_attempt_mismatch')
        if 'native_fluorescence' in assignment['requested_job']:
            if assignment.get('resource_id') != resource_id or assignment['resource_kind'] != 'local':
                raise ValueError('native_fluorescence_resource_identity_conflict')
            detail = receipt['outcome'].get('native_outcome') or {}
            key, attempt_id = (detail.get('attempt_operation_key'), detail.get('attempt_id'))
            if not isinstance(key, str) or not key or digest(key) != attempt_id or (job['execution_id'] != str(Path(assignment['workspace']) / '.episode-operations' / digest({'run': self.run_id, 'episode': body['episode_id']}) / digest(key) / 'native.json')):
                raise ValueError('native_fluorescence_original_attempt_mismatch')
        if 'native_expression_nmf' in assignment['requested_job']:
            self.operations[resource_id].validate_assignment(assignment)
            detail = receipt['outcome'].get('native_outcome') or {}
            key = detail.get('attempt_operation_key')
            attempt_id = detail.get('attempt_id')
            if not isinstance(key, str) or not key or digest(key) != attempt_id or (job['execution_id'] != str(Path(assignment['workspace']) / '.episode-operations' / digest({'run': self.run_id, 'episode': body['episode_id']}) / digest(key) / 'native.json')):
                raise ValueError('native_expression_nmf_original_attempt_mismatch')
        if 'native_lumpy' in assignment['requested_job']:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_lumpy_execution import lumpy_plan, validate_lumpy_original_controls
            self.operations[resource_id].validate_assignment(assignment)
            detail = receipt['outcome'].get('native_outcome') or {}
            plan = detail.get('native_lumpy_plan')
            if type(plan) is not dict:
                raise ValueError('native_lumpy_original_controls_required')
            plan = validate_lumpy_original_controls(plan, detail.get('native_lumpy_handle'), detail.get('native_lumpy_request_raw'))
            expected_plan = lumpy_plan(assignment, plan['identity'], policy=plan['policy'])
            owner = plan['identity']
            reference = receipt['arguments'].get('receipt_ref')
            if reference is not None:
                if receipt['tool_name'] not in {'practical.job.status', 'practical.job.collect'}:
                    raise ValueError('native_lumpy_receipt_ancestry_conflict')
                original, prior = self._native(reference, body['scope'], _seen=(*_seen, handle), _receipt_reads=reads)
                prior_detail = prior['receipt']['outcome'].get('native_outcome') or {}
                if original['resource_id'] != resource_id or original['execution_id'] != job['execution_id'] or canonical(original['assignment']) != canonical(assignment) or any((canonical(detail.get(key)) != canonical(prior_detail.get(key)) for key in ('native_lumpy_plan', 'native_lumpy_handle', 'native_lumpy_request_raw'))):
                    raise ValueError('native_lumpy_receipt_ancestry_conflict')
                origin_episode_id = original['origin_episode_id']
            elif owner['episode_id'] != origin_episode_id:
                raise ValueError('native_lumpy_original_owner_conflict')
            observed = detail.get('observation', detail)
            if canonical(plan) != canonical(expected_plan) or owner['run_id'] != self.run_id or owner['resource_id'] != resource_id or (owner['episode_id'] != origin_episode_id) or (owner['execution_id'] != job['execution_id']) or (owner['requested_job_sha256'] != digest(assignment['requested_job'])) or (owner['operation_key'] != detail.get('attempt_operation_key')) or (owner['attempt_id'] != detail.get('attempt_id')) or (observed.get('metadata', {}).get('policy') != plan['policy']) or (self.operations[resource_id].policy.to_dict() != plan['policy']):
                raise ValueError('native_lumpy_original_attempt_mismatch')
            starts = self.receipts._sources(self.receipts._accession(origin_episode_id, owner['operation_key']))
            if len(starts) != 1:
                raise ValueError('native_lumpy_original_start_receipt_missing')
            start = self._read_native_receipt(starts[0]['id'], body['scope'], reads)
            start_receipt = start['receipt']
            start_job = start_receipt['outcome'].get('facts', {}).get('requested_job', {})
            start_detail = start_receipt['outcome'].get('native_outcome') or {}
            if start['episode_id'] != origin_episode_id or start['assignment_sha256'] != digest(assignment) or start_receipt['tool_name'] != 'practical.job.start' or (start_receipt['operation_key'] != owner['operation_key']) or any((start_job.get(key) != job.get(key) for key in ('execution_id', 'resource_kind', 'requested_job_sha256', 'argv', 'environment'))) or any((canonical(detail.get(key)) != canonical(start_detail.get(key)) for key in ('native_lumpy_plan', 'native_lumpy_handle', 'native_lumpy_request_raw'))):
                raise ValueError('native_lumpy_original_start_receipt_conflict')
        if 'native_macs2_peak' in assignment['requested_job']:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_macs2_peak_execution import macs2_peak_plan, validate_macs2_peak_original_controls
            self.operations[resource_id].validate_assignment(assignment)
            detail = receipt['outcome'].get('native_outcome') or {}
            plan = detail.get('native_macs2_peak_plan')
            if type(plan) is not dict:
                raise ValueError('native_macs2_peak_original_controls_required')
            plan = validate_macs2_peak_original_controls(plan, detail.get('native_macs2_peak_handle'), detail.get('native_macs2_peak_request_raw'))
            expected_plan = macs2_peak_plan(assignment, plan['identity'], policy=plan['policy'])
            owner = plan['identity']
            reference = receipt['arguments'].get('receipt_ref')
            if reference is not None:
                if receipt['tool_name'] not in {'practical.job.status', 'practical.job.collect'}:
                    raise ValueError('native_macs2_peak_receipt_ancestry_conflict')
                original, prior = self._native(reference, body['scope'], _seen=(*_seen, handle), _receipt_reads=reads)
                prior_detail = prior['receipt']['outcome'].get('native_outcome') or {}
                if original['resource_id'] != resource_id or original['execution_id'] != job['execution_id'] or canonical(original['assignment']) != canonical(assignment) or any((canonical(detail.get(key)) != canonical(prior_detail.get(key)) for key in ('native_macs2_peak_plan', 'native_macs2_peak_handle', 'native_macs2_peak_request_raw'))):
                    raise ValueError('native_macs2_peak_receipt_ancestry_conflict')
                origin_episode_id = original['origin_episode_id']
            elif owner['episode_id'] != origin_episode_id:
                raise ValueError('native_macs2_peak_original_owner_conflict')
            observed = detail.get('observation', detail)
            if canonical(plan) != canonical(expected_plan) or owner['run_id'] != self.run_id or owner['resource_id'] != resource_id or (owner['episode_id'] != origin_episode_id) or (owner['execution_id'] != job['execution_id']) or (owner['requested_job_sha256'] != digest(assignment['requested_job'])) or (owner['operation_key'] != detail.get('attempt_operation_key')) or (owner['attempt_id'] != detail.get('attempt_id')) or (observed.get('metadata', {}).get('policy') != plan['policy']) or (self.operations[resource_id].policy.to_dict() != plan['policy']):
                raise ValueError('native_macs2_peak_original_attempt_mismatch')
            starts = self.receipts._sources(self.receipts._accession(origin_episode_id, owner['operation_key']))
            if len(starts) != 1:
                raise ValueError('native_macs2_peak_original_start_receipt_missing')
            start = self._read_native_receipt(starts[0]['id'], body['scope'], reads)
            start_receipt = start['receipt']
            start_job = start_receipt['outcome'].get('facts', {}).get('requested_job', {})
            start_detail = start_receipt['outcome'].get('native_outcome') or {}
            if start['episode_id'] != origin_episode_id or start['assignment_sha256'] != digest(assignment) or start_receipt['tool_name'] != 'practical.job.start' or (start_receipt['operation_key'] != owner['operation_key']) or any((start_job.get(key) != job.get(key) for key in ('execution_id', 'resource_kind', 'requested_job_sha256', 'argv', 'environment'))) or any((canonical(detail.get(key)) != canonical(start_detail.get(key)) for key in ('native_macs2_peak_plan', 'native_macs2_peak_handle', 'native_macs2_peak_request_raw'))):
                raise ValueError('native_macs2_peak_original_start_receipt_conflict')
        if 'native_atac_differential' in assignment['requested_job']:
            self.operations[resource_id].validate_assignment(assignment)
            detail = receipt['outcome'].get('native_outcome') or {}
            key = detail.get('attempt_operation_key')
            attempt_id = detail.get('attempt_id')
            if not isinstance(key, str) or not key or digest(key) != attempt_id or (job['execution_id'] != str(Path(assignment['workspace']) / '.episode-operations' / digest({'run': self.run_id, 'episode': body['episode_id']}) / digest(key) / 'native.json')):
                raise ValueError('native_atac_differential_original_attempt_mismatch')
        if 'native_chromatin_interactions' in assignment['requested_job']:
            self.operations[resource_id].validate_assignment(assignment)
            detail = receipt['outcome'].get('native_outcome') or {}
            key = detail.get('attempt_operation_key')
            attempt_id = detail.get('attempt_id')
            if not isinstance(key, str) or not key or digest(key) != attempt_id or (job['execution_id'] != str(Path(assignment['workspace']) / '.episode-operations' / digest({'run': self.run_id, 'episode': body['episode_id']}) / digest(key) / 'native.json')):
                raise ValueError('native_chromatin_interactions_original_attempt_mismatch')
        if 'native_genomic_overlap' in assignment['requested_job']:
            self.operations[resource_id].validate_assignment(assignment)
            detail = receipt['outcome'].get('native_outcome') or {}
            key = detail.get('attempt_operation_key')
            attempt_id = detail.get('attempt_id')
            if not isinstance(key, str) or not key or digest(key) != attempt_id or (job['execution_id'] != str(Path(assignment['workspace']) / '.episode-operations' / digest({'run': self.run_id, 'episode': body['episode_id']}) / digest(key) / 'native.json')):
                raise ValueError('native_genomic_overlap_original_attempt_mismatch')
        if 'native_protein_structure' in assignment['requested_job']:
            self.operations[resource_id].validate_assignment(assignment)
            detail = receipt['outcome'].get('native_outcome') or {}
            key = detail.get('attempt_operation_key')
            attempt_id = detail.get('attempt_id')
            if not isinstance(key, str) or digest(key) != attempt_id or job['execution_id'] != str(Path(assignment['workspace']) / '.episode-operations' / digest({'run': self.run_id, 'episode': body['episode_id']}) / digest(key) / 'native.json'):
                raise ValueError('original_commission_mismatch')
        if 'native_rna_structure' in assignment['requested_job']:
            self.operations[resource_id].validate_assignment(assignment)
            detail = receipt['outcome'].get('native_outcome') or {}
            key = detail.get('attempt_operation_key')
            attempt_id = detail.get('attempt_id')
            if not isinstance(key, str) or digest(key) != attempt_id or job['execution_id'] != str(Path(assignment['workspace']) / '.episode-operations' / digest({'run': self.run_id, 'episode': body['episode_id']}) / digest(key) / 'native.json'):
                raise ValueError('rna_original_attempt_mismatch')
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

    def _qualified(self, target):
        target = validate_target(target)
        original = self.read_target(target['handle'], target['scope'])
        if canonical(target) != canonical(original):
            raise ContractError('execution_target_identity_conflict')
        return target

    @staticmethod
    def _failed_handoff_profile(target):
        if target['resource_kind'] == 'local':
            return bool({'native_rna_structure', 'native_protein_structure', 'native_genomic_overlap', 'native_chromatin_interactions', 'native_atac_differential', 'native_expression_nmf', 'native_fluorescence', 'native_blast_masking', 'native_blast_utility', 'native_flux_balance', 'native_lumpy'} & set(target['assignment']['requested_job']))
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

class ExecutionProgressProvider:
    """Durable capture and replay for one selected resource observation."""

    def __init__(self, store, *, run_id, directory, resources, api_execution, log_window_bytes, log_roles):
        if type(log_window_bytes) is not int or log_window_bytes <= 0:
            raise ValueError('execution_progress_log_window_bytes_required')
        allowed_logs = {'stdout', 'stderr'}
        for configuration in resources.values():
            if configuration.get('kind') == 'local' and configuration.get('native_flux_balance'):
                from gene_annotation_episode.episodic_workflow.root.a110.native_flux_balance_bindings import validate_flux_balance_bindings
                if validate_flux_balance_bindings(configuration['native_flux_balance']):
                    allowed_logs.add('native_log')
        if not isinstance(log_roles, (tuple, list)) or any((role not in allowed_logs for role in log_roles)) or len(set(log_roles)) != len(log_roles):
            raise ValueError('execution_progress_log_roles_required')
        self.store, self.run_id = (store, run_id)
        self.resources = json.loads(canonical(resources))
        self.directory = Path(directory)
        self.log_window_bytes, self.log_roles = (log_window_bytes, tuple(log_roles))
        self.targets = ExecutionTargetReader(store, run_id=run_id, directory=directory, resources=resources, api_execution=api_execution)
        self.targets.log_window_bytes, self.targets.log_roles = (log_window_bytes, self.log_roles)
        with store.transaction():
            store.db.execute('CREATE TABLE IF NOT EXISTS runtime_execution_progress_operations (\n                run_id TEXT NOT NULL, operation_key TEXT NOT NULL, signature TEXT NOT NULL,\n                result TEXT NOT NULL, PRIMARY KEY(run_id,operation_key))')
            store.db.execute('CREATE TABLE IF NOT EXISTS runtime_execution_progress_custody (\n                run_id TEXT NOT NULL, target_handle TEXT NOT NULL, kind TEXT NOT NULL,\n                signature TEXT NOT NULL, source_ref TEXT NOT NULL REFERENCES records(id),\n                observed_at TEXT NOT NULL, PRIMARY KEY(run_id,target_handle,kind,signature))')
            store.db.execute('CREATE TABLE IF NOT EXISTS runtime_execution_progress_snapshots (\n                run_id TEXT NOT NULL, target_handle TEXT NOT NULL, scope TEXT NOT NULL,\n                signature TEXT NOT NULL, progress_ref TEXT NOT NULL REFERENCES records(id),\n                snapshot TEXT NOT NULL, PRIMARY KEY(run_id,target_handle,scope,signature))')
            store.db.execute('CREATE TABLE IF NOT EXISTS runtime_execution_progress_dependencies (\n                run_id TEXT NOT NULL, physical_identity TEXT NOT NULL,\n                target_handle TEXT NOT NULL, relationship TEXT NOT NULL,\n                PRIMARY KEY(run_id,physical_identity))')

    def as_record(self):
        return {'version': VERSION, 'configuration': {'resources': deepcopy(self.resources), 'log_window_bytes': self.log_window_bytes, 'log_roles': list(self.log_roles)}}

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
