"""A110 received execution information."""
from __future__ import annotations
import json
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a110.local_jobs import LocalJobPolicy
from gene_annotation_episode.workflow_budget import ENVIRONMENT_BOUNDS

def confined(path, workspace):
    path = Path(path)
    if not path.is_absolute() or not path.resolve().is_relative_to(Path(workspace).resolve()):
        raise ValueError('practical_write_outside_workspace')
    return path.resolve()

class HistoricalLocalAssignmentValidation:
    """Local preparation commands and detached requested computation are distinct."""

    def __init__(self, configuration, *, flux_balance_input_reader=None):
        if isinstance(configuration, dict) and 'native_protease_kinetics' in configuration:
            configuration = {key: value for key, value in configuration.items() if key != 'native_protease_kinetics'}
        if not {'kind', 'workspace', 'policy'} <= set(configuration) or set(configuration) - {'kind', 'workspace', 'policy', 'native_hmmer', 'native_infernal', 'native_infernal_preparation', 'native_hmmer_preparation', 'native_blast', 'native_rna_structure', 'native_protein_structure', 'native_genomic_overlap', 'native_chromatin_interactions', 'native_atac_differential', 'native_macs2_peak', 'native_lumpy', 'native_expression_nmf', 'native_fluorescence', 'native_blast_masking', 'native_blast_utility', 'native_flux_balance', 'native_molecular_sequence', 'native_homer_motif'} or configuration['kind'] != 'local':
            raise ValueError('explicit_local_practical_configuration_required')
        if flux_balance_input_reader is not None and (not callable(flux_balance_input_reader)):
            raise ValueError('native_flux_balance_input_reader_invalid')
        self.flux_balance_input_reader = flux_balance_input_reader
        self.configuration = json.loads(json.dumps(configuration, allow_nan=False))
        self.policy = LocalJobPolicy(**configuration['policy'])
        if 'native_molecular_sequence' in configuration:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.molecular_sequence_tools import validate_native_molecular_sequence_bindings
            validate_native_molecular_sequence_bindings(configuration['native_molecular_sequence'])
        if 'native_flux_balance' in configuration:
            from gene_annotation_episode.episodic_workflow.root.a110.native_flux_balance_bindings import validate_flux_balance_bindings
            validate_flux_balance_bindings(configuration['native_flux_balance'])
        if 'native_blast_utility' in configuration:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_blast_utility_tool_info import validate_native_blast_utility_bindings
            validate_native_blast_utility_bindings(configuration['native_blast_utility'])
        if 'native_blast_masking' in configuration:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_blast_masking_tool_info import validate_native_blast_masking_bindings
            validate_native_blast_masking_bindings(configuration['native_blast_masking'])
        if 'native_fluorescence' in configuration:
            from gene_annotation_episode.episodic_workflow.root.a110.native_fluorescence_contracts import validate_fluorescence_bindings
            validate_fluorescence_bindings(configuration['native_fluorescence'])
        if 'native_expression_nmf' in configuration:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_expression_nmf_contracts import validate_expression_nmf_bindings
            validate_expression_nmf_bindings(configuration['native_expression_nmf'])
        if 'native_macs2_peak' in configuration:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_macs2_peak_execution import validate_macs2_peak_bindings
            validate_macs2_peak_bindings(configuration['native_macs2_peak'])
        if 'native_lumpy' in configuration:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_lumpy_execution import validate_lumpy_bindings
            validate_lumpy_bindings(configuration['native_lumpy'])
        if 'native_homer_motif' in configuration:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_homer_execution import validate_homer_bindings
            validate_homer_bindings(configuration['native_homer_motif'])
        if 'native_atac_differential' in configuration:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_atac_differential_contracts import validate_atac_bindings
            validate_atac_bindings(configuration['native_atac_differential'])
        if 'native_chromatin_interactions' in configuration:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_chromatin_interaction_contracts import validate_chromatin_bindings
            validate_chromatin_bindings(configuration['native_chromatin_interactions'])
        if 'native_genomic_overlap' in configuration:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_genomic_overlap_contracts import validate_genomic_overlap_bindings
            validate_genomic_overlap_bindings(configuration['native_genomic_overlap'])
        if 'native_protein_structure' in configuration:
            from gene_annotation_episode.episodic_workflow.root.a110.native_protein_structure_contracts import validate_protein_structure_bindings
            validate_protein_structure_bindings(configuration['native_protein_structure'])
        if 'native_rna_structure' in configuration:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_rna_structure_contracts import validate_rna_structure_bindings
            validate_rna_structure_bindings(configuration['native_rna_structure'])
        if 'native_blast' in configuration:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_blast_tool_info import validate_native_blast_bindings
            validate_native_blast_bindings(configuration['native_blast'])
        if 'native_hmmer' in configuration:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_hmmer_tool_info import validate_native_hmmer_bindings
            validate_native_hmmer_bindings(configuration['native_hmmer'])
        if 'native_hmmer_preparation' in configuration:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_hmmer_preparation_tool_info import validate_native_hmmer_preparation_bindings
            validate_native_hmmer_preparation_bindings(configuration['native_hmmer_preparation'])
        if 'native_infernal' in configuration:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_infernal_tool_info import validate_native_infernal_bindings
            validate_native_infernal_bindings(configuration['native_infernal'])
        if 'native_infernal_preparation' in configuration:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_infernal_preparation_tool_info import validate_native_infernal_preparation_bindings
            validate_native_infernal_preparation_bindings(configuration['native_infernal_preparation'])

    def validate_assignment(self, assignment):
        if 'native_flux_balance' in assignment['requested_job']:
            from gene_annotation_episode.episodic_workflow.root.a110.native_flux_balance_contracts import POLICY, validate_flux_balance_requested_job
            from gene_annotation_episode.episodic_workflow.root.a110.native_flux_balance_bindings import flux_balance_binding_accepts_job
            job = validate_flux_balance_requested_job(assignment['requested_job'])['native_flux_balance']
            if not any((flux_balance_binding_accepts_job(row, job) for row in self.configuration.get('native_flux_balance', []))):
                raise ValueError('native_flux_balance_operation_mode_software_format_not_bound')
            if assignment.get('resource_kind') != 'local':
                raise ValueError('native_flux_balance_local_resource_required')
            if not isinstance(assignment.get('resource_id'), str) or not assignment['resource_id']:
                raise ValueError('native_flux_balance_resource_identity_required')
            confined(assignment['workspace'], self.configuration['workspace'])
            if self.policy.to_dict() != POLICY:
                raise ValueError('native_flux_balance_local_policy_conflict')
        if 'native_blast_utility' in assignment['requested_job']:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_blast_utility_contracts import validate_native_blast_utility_requested_job
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_blast_utility_tool_info import native_blast_utility_binding_accepts_job
            job = validate_native_blast_utility_requested_job(assignment['requested_job'])['native_blast_utility']
            if not any((native_blast_utility_binding_accepts_job(row, job) for row in self.configuration.get('native_blast_utility', []))):
                suffix = '_variant' if job['version'] in {'native_blast_utility_job_v2', 'native_blast_utility_job_v3'} else ''
                raise ValueError('native_blast_utility_program_mode_software_molecule' + suffix + '_not_bound')
            if assignment.get('resource_kind') != 'local':
                raise ValueError('native_blast_utility_local_resource_required')
            if not assignment.get('resource_id'):
                raise ValueError('native_blast_utility_resource_identity_required')
            confined(assignment['workspace'], self.configuration['workspace'])
            if self.policy.memory_bytes > ENVIRONMENT_BOUNDS['memory_bytes'] or self.policy.scratch_bytes > 4 * 1024 ** 3:
                raise ValueError('native_blast_utility_local_policy_conflict')
        if 'native_blast_masking' in assignment['requested_job']:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_blast_masking_contracts import validate_native_blast_masking_requested_job
            job = validate_native_blast_masking_requested_job(assignment['requested_job'])['native_blast_masking']
            operation = job['operation']
            if not any((row['program'] == operation['program'] and row['mode'] == operation['mode'] and (row['software'] == job['software']) and (operation['output_format'] in row['output_formats']) and (operation['masking_style'] in row['masking_styles']) for row in self.configuration.get('native_blast_masking', []))):
                raise ValueError('native_blast_masking_program_mode_software_format_style_not_bound')
            if assignment.get('resource_kind') != 'local':
                raise ValueError('native_blast_masking_local_resource_required')
            if not assignment.get('resource_id'):
                raise ValueError('native_blast_masking_resource_identity_required')
            confined(assignment['workspace'], self.configuration['workspace'])
            if self.policy.memory_bytes > ENVIRONMENT_BOUNDS['memory_bytes'] or self.policy.scratch_bytes > 4 * 1024 ** 3:
                raise ValueError('native_blast_masking_local_policy_conflict')
        if 'native_fluorescence' in assignment['requested_job']:
            from gene_annotation_episode.episodic_workflow.root.a110.native_fluorescence_contracts import POLICY, validate_fluorescence_requested_job
            job = validate_fluorescence_requested_job(assignment['requested_job'])['native_fluorescence']
            matching = [row for row in self.configuration.get('native_fluorescence', []) if all((row[key] == job[key] for key in ('operation', 'mode', 'software')))]
            if not matching:
                raise ValueError('native_fluorescence_operation_mode_software_not_bound')
            parsers = {row['parser'] for row in job['inputs']}
            if not any((parsers <= set(row['parsers']) for row in matching)):
                raise ValueError('native_fluorescence_parser_not_bound')
            if job['version'] == 'native_fluorescence_job_v2':
                methods = {row['recipe']['method'] for row in job['preparations']}
                profiles = {row['profile'] for row in job['report_inputs']}
                if not any((row.get('version') == 'native_fluorescence_binding_v2' and parsers <= set(row['parsers']) and (methods <= set(row['preparation_methods'])) and (profiles <= set(row['report_profiles'])) for row in matching)):
                    raise ValueError('native_fluorescence_prepared_capabilities_not_bound')
            if assignment.get('resource_kind') != 'local':
                raise ValueError('native_fluorescence_local_resource_required')
            if not assignment.get('resource_id'):
                raise ValueError('native_fluorescence_resource_identity_required')
            confined(assignment['workspace'], self.configuration['workspace'])
            if self.policy.to_dict() != POLICY:
                raise ValueError('native_fluorescence_local_policy_conflict')
        if 'native_expression_nmf' in assignment['requested_job']:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_expression_nmf_contracts import POLICY, validate_expression_nmf_requested_job
            job = validate_expression_nmf_requested_job(assignment['requested_job'])['native_expression_nmf']
            selection = {key: job[key] for key in ('operation', 'mode', 'software')}
            if selection not in self.configuration.get('native_expression_nmf', []):
                raise ValueError('native_expression_nmf_operation_mode_software_not_bound')
            if assignment.get('resource_kind') != 'local':
                raise ValueError('native_expression_nmf_local_resource_required')
            if not assignment.get('resource_id'):
                raise ValueError('native_expression_nmf_resource_identity_required')
            confined(assignment['workspace'], self.configuration['workspace'])
            if self.policy.to_dict() != POLICY:
                raise ValueError('native_expression_nmf_local_policy_conflict')
        if 'native_lumpy' in assignment['requested_job']:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_lumpy_execution import POLICY, validate_lumpy_requested_job
            job = validate_lumpy_requested_job(assignment['requested_job'])['native_lumpy']
            selection = {'operation': job['request']['operation'], 'mode': job['request']['mode'], 'software': job['software']}
            if selection not in self.configuration.get('native_lumpy', []):
                raise ValueError('native_lumpy_operation_mode_software_not_bound')
            if assignment.get('resource_kind') != 'local':
                raise ValueError('native_lumpy_local_resource_required')
            if not assignment.get('resource_id'):
                raise ValueError('native_lumpy_resource_identity_required')
            confined(assignment['workspace'], self.configuration['workspace'])
            if self.policy.to_dict() != POLICY:
                raise ValueError('native_lumpy_local_policy_conflict')
        if 'native_macs2_peak' in assignment['requested_job']:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_macs2_peak_execution import POLICY, validate_macs2_peak_requested_job
            job = validate_macs2_peak_requested_job(assignment['requested_job'])['native_macs2_peak']
            selection = {'operation': job['request']['operation'], 'mode': job['request']['mode'], 'software': job['software']}
            if selection not in self.configuration.get('native_macs2_peak', []):
                raise ValueError('native_macs2_peak_operation_mode_software_not_bound')
            if assignment.get('resource_kind') != 'local':
                raise ValueError('native_macs2_peak_execution_resource_required')
            if not assignment.get('resource_id'):
                raise ValueError('native_macs2_peak_resource_identity_required')
            confined(assignment['workspace'], self.configuration['workspace'])
            if self.policy.to_dict() != POLICY:
                raise ValueError('native_macs2_peak_execution_policy_conflict')
        if 'native_atac_differential' in assignment['requested_job']:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_atac_differential_contracts import POLICY, validate_atac_requested_job
            job = validate_atac_requested_job(assignment['requested_job'])['native_atac_differential']
            selection = {'operation': job['request']['operation'], 'mode': job['request']['mode'], 'software': job['software']}
            if selection not in self.configuration.get('native_atac_differential', []):
                raise ValueError('native_atac_differential_operation_mode_software_not_bound')
            if assignment.get('resource_kind') != 'local':
                raise ValueError('native_atac_differential_local_resource_required')
            if not assignment.get('resource_id'):
                raise ValueError('native_atac_differential_resource_identity_required')
            confined(assignment['workspace'], self.configuration['workspace'])
            if self.policy.to_dict() != POLICY:
                raise ValueError('native_atac_differential_local_policy_conflict')
        if 'native_chromatin_interactions' in assignment['requested_job']:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_chromatin_interaction_contracts import POLICY, validate_chromatin_requested_job
            job = validate_chromatin_requested_job(assignment['requested_job'])['native_chromatin_interactions']
            request = job['request']
            if not any((row['software'] == job['software'] and request['contact']['format'] in row['supported_formats'] and (set(request['analysis_modes']) <= set(row['analysis_modes'])) for row in self.configuration.get('native_chromatin_interactions', []))):
                raise ValueError('native_chromatin_interactions_format_modes_software_not_bound')
            if assignment.get('resource_kind') != 'local':
                raise ValueError('native_chromatin_interactions_local_resource_required')
            if not assignment.get('resource_id'):
                raise ValueError('native_chromatin_interactions_resource_identity_required')
            confined(assignment['workspace'], self.configuration['workspace'])
            if self.policy.to_dict() != POLICY:
                raise ValueError('native_chromatin_interactions_local_policy_conflict')
        if 'native_genomic_overlap' in assignment['requested_job']:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_genomic_overlap_contracts import POLICY, validate_genomic_overlap_requested_job
            job = validate_genomic_overlap_requested_job(assignment['requested_job'])['native_genomic_overlap']
            selection = {'operation': job['request']['operation'], 'mode': job['request']['mode'], 'software': job['software']}
            if selection not in self.configuration.get('native_genomic_overlap', []):
                raise ValueError('native_genomic_overlap_operation_mode_software_not_bound')
            if assignment.get('resource_kind') != 'local':
                raise ValueError('native_genomic_overlap_local_resource_required')
            if not assignment.get('resource_id'):
                raise ValueError('native_genomic_overlap_resource_identity_required')
            confined(assignment['workspace'], self.configuration['workspace'])
            if self.policy.to_dict() != POLICY:
                raise ValueError('native_genomic_overlap_local_policy_conflict')
        if 'native_protein_structure' in assignment['requested_job']:
            from gene_annotation_episode.episodic_workflow.root.a110.native_protein_structure_contracts import POLICY, validate_protein_structure_requested_job
            job = validate_protein_structure_requested_job(assignment['requested_job'])['native_protein_structure']
            request = job['request']
            selection = {'operation': request['operation'], 'scientific_mode': request['parameters']['mode'] if request['operation'] == 'compare' else None, 'software': job['software']}
            if selection not in self.configuration.get('native_protein_structure', []):
                raise ValueError('native_protein_structure_operation_mode_software_not_bound')
            if assignment.get('resource_kind') != 'local':
                raise ValueError('native_protein_structure_local_resource_required')
            if not assignment.get('resource_id'):
                raise ValueError('native_protein_structure_resource_identity_required')
            confined(assignment['workspace'], self.configuration['workspace'])
            if self.policy.to_dict() != POLICY:
                raise ValueError('native_protein_structure_local_policy_conflict')
        if 'native_rna_structure' in assignment['requested_job']:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_rna_structure_contracts import POLICY, validate_rna_structure_requested_job
            job = validate_rna_structure_requested_job(assignment['requested_job'])['native_rna_structure']
            selection = {key: job[key] for key in ('operation', 'mode', 'software')}
            if selection not in self.configuration.get('native_rna_structure', []):
                raise ValueError('native_rna_structure_operation_mode_software_not_bound')
            if assignment.get('resource_kind') != 'local':
                raise ValueError('native_rna_structure_local_resource_required')
            if not assignment.get('resource_id'):
                raise ValueError('native_rna_structure_resource_identity_required')
            confined(assignment['workspace'], self.configuration['workspace'])
            if self.policy.to_dict() != POLICY:
                raise ValueError('native_rna_structure_local_policy_conflict')
        if 'native_blast_standard_database' in assignment['requested_job']:
            raise ValueError('native_blast_standard_database_hpc_resource_required')
        if 'native_blast_database' in assignment['requested_job']:
            raise ValueError('native_blast_database_hpc_resource_required')
        if 'native_blast' in assignment['requested_job']:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_blast_contracts import validate_native_blast_requested_job
            job = validate_native_blast_requested_job(assignment['requested_job'])['native_blast']
            selection = {key: job[key] for key in ('program', 'mode', 'software')}
            if selection not in self.configuration.get('native_blast', []):
                raise ValueError('native_blast_program_mode_software_not_bound')
            if assignment.get('resource_kind') != 'local':
                raise ValueError('native_blast_local_resource_required')
            if not assignment.get('resource_id'):
                raise ValueError('native_blast_resource_identity_required')
        if 'native_hmmer_preparation' in assignment['requested_job']:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_hmmer_preparation_contracts import validate_native_hmmer_preparation_requested_job
            job = validate_native_hmmer_preparation_requested_job(assignment['requested_job'])['native_hmmer_preparation']
            selection = {key: job[key] for key in ('program', 'mode', 'software')}
            if selection not in self.configuration.get('native_hmmer_preparation', []):
                raise ValueError('native_hmmer_preparation_program_mode_software_not_bound')
            if assignment.get('resource_kind') != 'local':
                raise ValueError('native_hmmer_preparation_local_resource_required')
            if not assignment.get('resource_id'):
                raise ValueError('native_hmmer_preparation_resource_identity_required')
        if 'native_hmmer' in assignment['requested_job']:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_hmmer_contracts import validate_native_hmmer_requested_job
            job = validate_native_hmmer_requested_job(assignment['requested_job'])['native_hmmer']
            selection = {key: job[key] for key in ('program', 'mode', 'software')}
            if selection not in self.configuration.get('native_hmmer', []):
                raise ValueError('native_hmmer_program_mode_software_not_bound')
            if not assignment.get('resource_id'):
                raise ValueError('native_hmmer_resource_identity_required')
        if 'native_infernal' in assignment['requested_job']:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_native_infernal_contracts import validate_native_infernal_requested_job
            job = validate_native_infernal_requested_job(assignment['requested_job'])['native_infernal']
            selection = {key: job[key] for key in ('program', 'software')}
            if selection not in self.configuration.get('native_infernal', []):
                raise ValueError('native_infernal_program_software_not_bound')
            if not assignment.get('resource_id'):
                raise ValueError('native_infernal_resource_identity_required')
        if 'native_infernal_preparation' in assignment['requested_job']:
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_infernal_preparation_contracts import validate_native_infernal_preparation_requested_job
            job = validate_native_infernal_preparation_requested_job(assignment['requested_job'])['native_infernal_preparation']
            selection = {key: job[key] for key in ('program', 'mode', 'software')}
            if selection not in self.configuration.get('native_infernal_preparation', []):
                raise ValueError('native_infernal_preparation_program_mode_software_not_bound')
            if assignment.get('resource_kind') != 'local':
                raise ValueError('native_infernal_preparation_local_resource_required')
            if not assignment.get('resource_id'):
                raise ValueError('native_infernal_preparation_resource_identity_required')
        constraints = assignment['constraints']
        allowed = {'allocation', 'memory_bytes', 'scratch_bytes'}
        if set(constraints) - allowed:
            raise ValueError('unsupported_explicit_local_constraint')
        policy = self.configuration['policy']
        for key in allowed - {'allocation'}:
            if key in constraints and constraints[key] != policy[key]:
                raise ValueError('practical_local_allocation_constraint_mismatch')
        if 'allocation' in constraints and constraints['allocation'] != policy:
            raise ValueError('practical_local_allocation_constraint_mismatch')
