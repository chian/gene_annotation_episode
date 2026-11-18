"""Private A104 Launch received reports."""
from __future__ import annotations
from .contracts import BLAST_GRADED_RETURN_SOURCE, deepcopy, is_native_blast_database_target, is_standard_blast_database_target, plain

class LaunchReceivedReportsReferenceAccess:

    def resolve_received_reference(self, context, reference, namespace):
        captured = self.local_file_sources.reference_access(context, reference, namespace)
        if captured is not None:
            return captured
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
        fluorescence = self._fluorescence_reference_access(context, reference, namespace)
        if fluorescence is not None:
            return fluorescence
        nmf = self._expression_nmf_reference_access(context, reference, namespace)
        if nmf is not None:
            return nmf
        atac = self._atac_reference_access(context, reference, namespace)
        if atac is not None:
            return atac
        chromatin = self._chromatin_reference_access(context, reference, namespace)
        if chromatin is not None:
            return chromatin
        access = self._protein_reference_access(context, reference, namespace)
        if access is not None:
            return access
        if self.native_blast_standard_database_returns is not None and context.role in {'annotation', 'evolutionary_history_evidence'}:
            resolved = self.native_blast_standard_database_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self.native_blast_database_returns is not None and context.role in {'annotation', 'evolutionary_history_evidence'}:
            resolved = self.native_blast_database_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self.native_hmmer_preparation_returns is not None and context.role in {'annotation', 'evolutionary_history_evidence'}:
            resolved = self.native_hmmer_preparation_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self.native_blast_returns is not None and context.role in {'annotation', 'evolutionary_history_evidence'}:
            resolved = self.native_blast_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self._has_appservice():
            from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_homology_returns import IDENTIFIER_NAMESPACES
            if namespace in IDENTIFIER_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.homology_returns.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_phylogeny_returns import IDENTIFIER_NAMESPACES as PHYLOGENY_NAMESPACES
            if namespace in PHYLOGENY_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.phylogeny_returns.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.a104.library.bvbrc_proteome_returns import IDENTIFIER_NAMESPACES as PROTEOME_NAMESPACES
            if namespace in PROTEOME_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.proteome_returns.resolve_received(context, reference, namespace)
            resolved = self.api_execution.appservice.resolve(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self._forwards_bvbrc_reports(context.role):
            resolved = self.api_execution.bvbrc_data.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        for results in (self.native_hmmer_preparation_results,):
            if results is not None:
                resolved = results.retained_reference_access(context, reference, namespace)
                if resolved is not None:
                    return resolved
        return None

