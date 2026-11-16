"""A110 received execution information."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)

def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

class HistoricalTerminalAssignmentValidation:
    """One selected general shell command, through a configured transport."""

    def __init__(self, configuration, *, coordinator_workspace=None, artifact_selector=None):
        self.configuration = json.loads(canonical(configuration))
        self.coordinator_workspace = None if coordinator_workspace is None else str(Path(coordinator_workspace).resolve())
        self._validate_configuration()
        if artifact_selector is not None and (not callable(artifact_selector)):
            raise TypeError('execution_artifact_selector_must_be_callable')
        self.artifact_selector = artifact_selector

    def _validate_configuration(self):
        configuration = self.configuration
        if configuration.get('kind') not in {'local', 'pbs_ssh'}:
            raise ValueError('execution_resource_kind_invalid')
        workspace = configuration.get('workspace')
        if not isinstance(workspace, str) or not PurePosixPath(workspace).is_absolute() or '..' in PurePosixPath(workspace).parts or ('\x00' in workspace):
            raise ValueError('execution_resource_workspace_invalid')
        for key in ('launch_prompt_entry', 'launch_prompt_sections'):
            if key == 'launch_prompt_entry' and key in configuration and (not isinstance(configuration[key], str) or not configuration[key]):
                raise ValueError('execution_resource_prompt_invalid')
            if key == 'launch_prompt_sections' and key in configuration and (not isinstance(configuration[key], list) or not configuration[key] or any((not isinstance(value, str) or not value for value in configuration[key])) or (len(set(configuration[key])) != len(configuration[key]))):
                raise ValueError('execution_resource_prompt_sections_invalid')
        if configuration['kind'] == 'local':
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_local_assignment_validation import HistoricalLocalAssignmentValidation as LocalPracticalOperations
            LocalPracticalOperations({key: value for key, value in configuration.items() if key not in {'launch_prompt_entry', 'launch_prompt_sections', 'scheduler'}})
        else:
            expected = {'kind', 'workspace', 'ssh_argv', 'python_executable', 'account', 'scheduler'}
            allowed = expected | {'native_blast_database', 'native_blast_standard_database', 'launch_prompt_entry', 'launch_prompt_sections'}
            if not expected <= set(configuration) or set(configuration) - allowed:
                raise ValueError('explicit_execution_transport_configuration_required')
            command = configuration['ssh_argv']
            if not isinstance(command, list) or not command or any((not isinstance(value, str) or not value or '\x00' in value for value in command)) or (not isinstance(configuration['python_executable'], str)) or (not PurePosixPath(configuration['python_executable']).is_absolute()) or (not isinstance(configuration['account'], str)) or (re.fullmatch('[A-Za-z0-9_.-]+', configuration['account']) is None):
                raise ValueError('execution_transport_configuration_invalid')
            scheduler = configuration['scheduler']
            if not isinstance(scheduler, dict) or scheduler.get('kind') != 'pbs' or set(scheduler) - {'kind', 'required_resources'} or (not isinstance(scheduler.get('required_resources', []), list)) or any((not isinstance(value, str) or '=' not in value or '\x00' in value for value in scheduler.get('required_resources', []))):
                raise ValueError('execution_scheduler_configuration_invalid')
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_database_terminal_custody import validate_native_database_resource, PROFILES
            for key in PROFILES:
                if key in configuration:
                    validate_native_database_resource(configuration, key)

    def validate_assignment(self, assignment):
        workspace = PurePosixPath(assignment['workspace'])
        if not workspace.is_absolute() or not workspace.is_relative_to(self.configuration['workspace']):
            raise ValueError('execution_workspace_configuration_conflict')
        if self.configuration['kind'] == 'local':
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_local_assignment_validation import HistoricalLocalAssignmentValidation as LocalPracticalOperations
            LocalPracticalOperations({key: value for key, value in self.configuration.items() if key not in {'launch_prompt_entry', 'launch_prompt_sections', 'scheduler'}}).validate_assignment(assignment)
        else:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_database_terminal_custody import validate_native_database_assignment
            validate_native_database_assignment(self.configuration, assignment)
            constraints = assignment['constraints']
            if constraints.get('account', self.configuration['account']) != self.configuration['account']:
                raise ValueError('execution_account_constraint_conflict')
            if 'allowed_accounts' in constraints and self.configuration['account'] not in constraints['allowed_accounts']:
                raise ValueError('execution_account_constraint_conflict')
            if set(constraints) - {'account', 'queue', 'resources', 'allowed_accounts', 'allowed_queues', 'allocation'}:
                raise ValueError('execution_scheduler_constraint_unsupported')
            allocation = constraints.get('allocation', {})
            if not isinstance(allocation, dict) or set(allocation) - {'account', 'queue', 'resources'}:
                raise ValueError('execution_scheduler_allocation_invalid')
            if any((constraints.get(name, self.configuration.get(name)) != value for name, value in allocation.items())):
                raise ValueError('execution_scheduler_allocation_constraint_conflict')
        return assignment
