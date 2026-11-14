"""Private A107 Launch work operations"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a107.library.execution_resource_information import execution_capability_information
from .binding_roles import ROLE_KINDS
from .action_outcome import _outcome
from gene_annotation_episode.episodic_workflow.root.a107.execution_contracts import checked
from gene_annotation_episode.episodic_workflow.root.a107.native_blast_database_acquisition import is_native_blast_database_target
from gene_annotation_episode.episodic_workflow.root.a107.native_blast_acquisition import is_native_blast_target
from gene_annotation_episode.episodic_workflow.root.a107.native_hmmer_preparation_acquisition import is_native_hmmer_preparation_target
from gene_annotation_episode.episodic_workflow.root.a107.native_hmmer_acquisition import is_native_hmmer_target
from gene_annotation_episode.episodic_workflow.root.a107.native_infernal_preparation_acquisition import is_native_infernal_preparation_target
from gene_annotation_episode.episodic_workflow.root.a107.native_infernal_acquisition import is_native_infernal_target
from gene_annotation_episode.episodic_workflow.root.a107.native_rna_structure_acquisition import is_native_rna_structure_target
from gene_annotation_episode.episodic_workflow.root.a107.native_blast_standard_database_acquisition import is_standard_blast_database_target
from .resource_information import launch_operation_catalog
from .received_result_records import native_result_operation_catalog
from gene_annotation_episode.episodic_workflow.root.a107.communication import plain

class LaunchWorkOperations:

    def catalog(self, context):
        return launch_operation_catalog()

    async def execute(self, context, tool_name, arguments, operation_key):
        try:
            catalog = {entry['name']: entry for entry in self.catalog(context)}
            if tool_name not in catalog:
                raise ValueError('execution_operation_not_available')
            arguments = checked(arguments, catalog[tool_name]['input_schema'], 'invalid_execution_operation_arguments')
            return _outcome(execution_capability_information(self, context))
        except (ValueError, TypeError) as error:
            from gene_annotation_episode.episodic_workflow.root.a107.native_file_capture import NativeFileCaptureError
            if isinstance(error, NativeFileCaptureError) and self.local_file_sources.applies(context) and (error.code in {'retained_artifact_unavailable', 'retained_artifact_mismatch'}):
                raise
            return _outcome(code=str(error))
