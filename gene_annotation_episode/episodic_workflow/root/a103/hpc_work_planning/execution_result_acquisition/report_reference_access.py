"""Authenticate report references, preserving supported foreign receiving contexts."""
from __future__ import annotations
from .execution_contracts import BLAST_GRADED_RETURN_SCHEMA, BLAST_GRADED_RETURN_SOURCE, LOCAL_FILE_SOURCE_PROVIDER, NATIVE_RESULT_ORIGIN, PracticalReceiptInformation, RESULT_PROVIDER, ROLE_KINDS, TerminalExecutionBehavior, deepcopy, obj, plain, validate_form

class ResultsReportReferenceAccess:

    def resolve(self, context, reference, namespace):
        try:
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
                from gene_annotation_episode.episodic_workflow.root.a103.native_blast_standard_database_results import IDENTIFIER_NAMESPACES as DATABASE_NAMESPACES
                if namespace in DATABASE_NAMESPACES:
                    return self.native_blast_standard_database_results.resolve(context, reference, namespace) if context.role == 'results' else self.native_blast_standard_database_returns.resolve_received(context, reference, namespace)
                if self.native_blast_standard_database_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'gene_context_evidence'}:
                    resolved = self.native_blast_standard_database_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self.native_blast_database_results is not None:
                from gene_annotation_episode.episodic_workflow.root.a103.native_blast_database_results import IDENTIFIER_NAMESPACES as DATABASE_NAMESPACES
                if namespace in DATABASE_NAMESPACES:
                    return self.native_blast_database_results.resolve(context, reference, namespace) if context.role == 'results' else self.native_blast_database_returns.resolve_received(context, reference, namespace)
                if self.native_blast_database_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'gene_context_evidence'}:
                    resolved = self.native_blast_database_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self.native_hmmer_preparation_results is not None:
                from gene_annotation_episode.episodic_workflow.root.a103.hmmer_preparation_result_views import IDENTIFIER_NAMESPACES as HMMER_PREPARATION_NAMESPACES
                if namespace in HMMER_PREPARATION_NAMESPACES:
                    return self.native_hmmer_preparation_results.resolve(context, reference, namespace) if context.role == 'results' else self.native_hmmer_preparation_returns.resolve_received(context, reference, namespace)
                if self.native_hmmer_preparation_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'gene_context_evidence'}:
                    resolved = self.native_hmmer_preparation_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self.native_blast_results is not None:
                if namespace in {'native_blast_pairwise_row', 'native_blast_artifact_key', 'native_blast_search_pointer'}:
                    return self.native_blast_results.resolve(context, reference, namespace) if context.role == 'results' else self.native_blast_returns.resolve_received(context, reference, namespace)
                if self.native_blast_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'gene_context_evidence'}:
                    resolved = self.native_blast_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self._has_appservice():
                from gene_annotation_episode.episodic_workflow.root.a103.bvbrc_homology_returns import IDENTIFIER_NAMESPACES
                if namespace in IDENTIFIER_NAMESPACES:
                    return self.api_execution.homology_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.homology_returns.resolve_received(context, reference, namespace)
                resolved = self.api_execution.appservice.resolve(context, reference, namespace)
                if resolved is not None:
                    return resolved
            if namespace == 'bvbrc_minhash_genome':
                if self.api_execution is None:
                    return False
                if context.role == 'results':
                    return self.api_execution.minhash.resolve_own(context, reference, namespace)
                return self.api_execution.minhash.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.a103.bvbrc_data_views import IDENTIFIER_NAMESPACES
            if namespace in IDENTIFIER_NAMESPACES:
                return self.api_execution is not None and self.api_execution.bvbrc_data.resolve(context, reference, namespace)
            if namespace in {'execution_handle', 'execution'}:
                from gene_annotation_episode.episodic_workflow.root.a103.episode_bindings import reference_in_context
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
                from gene_annotation_episode.episodic_workflow.root.a103.episode_bindings import reference_in_context
                return bool(reference_in_context(self.services, context, reference, namespace))
            kind = source['record_type']
            return bool(self.store.reference_subset([reference], plain(context.scope)) and (namespace in {None, kind} or (namespace == 'subject' and kind in {'input', 'feature', 'product', 'read_subject'})))
        except (ValueError, KeyError, OSError):
            return False

