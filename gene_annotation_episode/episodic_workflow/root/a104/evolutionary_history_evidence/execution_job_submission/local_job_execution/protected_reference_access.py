"""Original protected read authority private to this execution owner."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain

class ProtectedReferenceAccess:

    def _install_protected_reference_readers(self):
        from gene_annotation_episode.episodic_workflow.root.a104.library.native_protein_structure_results import NativeProteinStructureResults
        from gene_annotation_episode.episodic_workflow.root.a104.library.native_protein_structure_returns import NativeProteinStructureReturns
        self.native_protein_structure_results = NativeProteinStructureResults(self)
        self.native_protein_structure_returns = NativeProteinStructureReturns(self)
        from gene_annotation_episode.episodic_workflow.root.a104.library.native_fluorescence_results import NativeFluorescenceResults
        from gene_annotation_episode.episodic_workflow.root.a104.library.fluorescence_returns import FluorescenceReturns
        self.native_fluorescence_results = NativeFluorescenceResults(self)
        self.native_fluorescence_returns = FluorescenceReturns(self)
        self.native_expression_nmf_results = self.native_expression_nmf_returns = None
        self.atac_results = self.atac_returns = None
        self.native_chromatin_interaction_results = self.native_chromatin_interaction_returns = None

    def _protein_reference_access(self, context, reference, namespace):
        """Classify before ordinary resolution; a protected denial cannot fall through."""
        if isinstance(reference, str) and reference.startswith('protein_structure_result_receipt:') or (isinstance(namespace, str) and namespace.startswith('protein_structure_')):
            return False
        if namespace in {'execution', 'execution_handle'}:
            return None
        try:
            record = self.store.get(reference)
        except (ValueError, KeyError):
            return None
        if record['record_type'] in {'feature', 'product'}:
            from gene_annotation_episode.episodic_workflow.root.a104.library.protein_structure_operands import is_protein_structure_sequence_operand
            if is_protein_structure_sequence_operand(self.store, reference):
                return False
        if self.native_protein_structure_results.owns_reference(reference):
            return self.native_protein_structure_returns.resolve_received(context, reference, namespace)
        return None

    def _fluorescence_reference_access(self, context, reference, namespace):
        host = self.native_fluorescence_results
        if not host.owns_reference(reference):
            return None
        if namespace not in {None, 'artifact'}:
            return False
        if host.applies(context):
            if host.resolve_own(context, reference, namespace):
                return True
            selector = plain(context.assignment)['selector']
            supplied = selector.get('saved_sheet_file')
            if selector.get('mode') == 'saved_sheet_recalculation' and isinstance(supplied, dict) and (supplied.get('artifact_ref') == reference):
                self.native_fluorescence_returns.authenticate_received_saved_sheet(context, supplied)
                return True
        return self.native_fluorescence_returns.resolve_received(context, reference, namespace)

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

    def _atac_reference_access(self, context, reference, namespace):
        host = self.atac_results
        if host is None or not host.owns_reference(reference):
            return None
        if namespace not in {None, 'artifact'}:
            return False
        if host.applies(context):
            if host.resolve_own(context, reference, namespace):
                return True
            selector = plain(context.assignment)['selector']
            supplied = selector.get('saved_sheet_bundle')
            if selector.get('mode') == 'saved_sheet_recalculation' and isinstance(supplied, dict) and (reference in [supplied['sheet']['artifact_ref'], *(row['file']['artifact_ref'] for row in supplied['tables'])]):
                self.atac_returns.authenticate_received_saved_bundle(context, supplied)
                return True
        return self.atac_returns.resolve_received(context, reference, namespace)

    def _chromatin_reference_access(self, context, reference, namespace):
        host = self.native_chromatin_interaction_results
        if host is None or not host.owns_reference(reference):
            return None
        if namespace not in {None, 'artifact'}:
            return False
        if host.applies(context):
            if host.resolve_own(context, reference, namespace):
                return True
            selector = plain(context.assignment)['selector']
            supplied = selector.get('saved_sheet_bundle')
            if selector.get('mode') == 'saved_sheet_recalculation' and isinstance(supplied, dict) and any((file.get('artifact_ref') == reference for file in [supplied['sheet'], *supplied['tables']])):
                self.native_chromatin_interaction_returns.authenticate_received_saved_bundle(context, supplied)
                return True
        return self.native_chromatin_interaction_returns.resolve_received(context, reference, namespace)
