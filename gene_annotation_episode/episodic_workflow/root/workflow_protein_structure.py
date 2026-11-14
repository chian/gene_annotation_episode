"""Preserved root host ports defined by WorkflowProteinStructure."""
from __future__ import annotations
from .receiving_context import BindingContext

class WorkflowProteinStructure:

    def authenticate_structure_alignment_operands(self, context: BindingContext, arguments: dict) -> dict:
        """Check original received structure sequences before alignment preparation."""
        from gene_annotation_episode.episodic_workflow.root.library.protein_structure_authority import ProteinStructureOperandError
        from gene_annotation_episode.episodic_workflow.root.library.protein_structure_contracts import issue
        from .protein_structure_operands import authenticate_structure_sequence_reference, is_protein_structure_sequence_operand
        if context.run_id != self.workflow.run_id:
            raise ProteinStructureOperandError(issue('original_commission_mismatch', stage='authority', field='receipt'))
        returns = self.protein_structure_input_authority()
        descriptors = {'query': None, 'reference': None}
        for role in descriptors:
            reference = arguments[role + '_ref']
            if not is_protein_structure_sequence_operand(self.workflow.store, reference):
                continue
            descriptor = authenticate_structure_sequence_reference(self.workflow.store, context, reference, returns=returns)
            if 'sequence_align' not in descriptor['allowed_uses']:
                raise ProteinStructureOperandError(issue('sequence_not_received', stage='authority', field='descriptor'))
            descriptors[role] = descriptor
        return descriptors

    def protein_structure_input_authority(self):
        from .protein_structure_action_records import ProteinStructureActionRecords
        registry = getattr(self.workflow, 'episode_bindings', None)
        for_role = getattr(registry, 'for_role', None)
        try:
            owner = for_role('results') if callable(for_role) else None
        except LookupError:
            owner = None
        return ProteinStructureActionRecords(self.workflow.store, self.workflow.run_id, legacy_returns=getattr(owner, 'native_protein_structure_returns', None))

    def protein_structure_reference_access(self, context, reference, namespace):
        return self.protein_structure_input_authority().retained_reference_access(context, reference, namespace)

