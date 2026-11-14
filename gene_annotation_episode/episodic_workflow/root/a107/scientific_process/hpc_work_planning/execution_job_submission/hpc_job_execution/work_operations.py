from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a107.library.execution_resource_information import execution_capability_information
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_targets import selected_result_action
from .execution_contracts import NATIVE_RESULT_ORIGIN
from .execution_contracts import RESULT_PROVIDER
from .execution_contracts import ROLE_KINDS
from .execution_contracts import _immutable
from .execution_contracts import _read
from .execution_contracts import canonical
from .execution_contracts import checked
from .execution_contracts import deepcopy
from .execution_contracts import digest
from .execution_contracts import is_native_blast_database_target
from .execution_contracts import is_native_blast_target
from .execution_contracts import is_native_hmmer_preparation_target
from .execution_contracts import is_native_hmmer_target
from .execution_contracts import is_native_infernal_preparation_target
from .execution_contracts import is_native_infernal_target
from .execution_contracts import is_native_rna_structure_target
from .execution_contracts import is_standard_blast_database_target
from .execution_contracts import native_result_operation_catalog
from .execution_contracts import plain

class NativeWorkOperations:
    _selected_result_action = selected_result_action

    def catalog(self, context):
        practical_context = self._practical_context(context)
        return self._delegate(context).catalog(practical_context)

    async def execute(self, context, tool_name, arguments, operation_key):
        self._check_parent_inputs(context)
        practical_context = self._practical_context(context)
        outcome = await self._delegate(context).execute(practical_context, tool_name, arguments, operation_key)
        return outcome
