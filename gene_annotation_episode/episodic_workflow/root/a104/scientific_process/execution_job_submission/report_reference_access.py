"""Private A104 Launch to parent."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.a104_homology_execution import BLAST_GRADED_RETURN_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a104.a104_homology_execution import BLAST_GRADED_RETURN_SOURCE
from gene_annotation_episode.episodic_workflow.root.a104.local_file_capture_results import FILE_PROVIDER as LOCAL_FILE_SOURCE_PROVIDER
from .result_records import NATIVE_RESULT_ORIGIN
from gene_annotation_episode.episodic_workflow.root.a104.practical_receipt_information import PracticalReceiptInformation
from .result_records import RESULT_PROVIDER
from gene_annotation_episode.episodic_workflow.root.a104.scientific_process.execution_job_submission.terminal_validation import TerminalExecutionBehavior
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import obj
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain
from gene_annotation_episode.episodic_workflow.root.a104.communication import validate_form


class LaunchToParentReferenceAccess:

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
            if self.native_blast_standard_database_results is not None:
                from gene_annotation_episode.episodic_workflow.root.a104.library.native_blast_standard_database_result_records import IDENTIFIER_NAMESPACES as DATABASE_NAMESPACES
                if namespace in DATABASE_NAMESPACES:
                    return self.native_blast_standard_database_results.resolve(context, reference, namespace) if context.role == 'results' else self.native_blast_standard_database_returns.resolve_received(context, reference, namespace)
                if self.native_blast_standard_database_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'scientific_process'}:
                    resolved = self.native_blast_standard_database_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self.native_blast_database_results is not None:
                from gene_annotation_episode.episodic_workflow.root.a104.library.native_blast_database_result_records import IDENTIFIER_NAMESPACES as DATABASE_NAMESPACES
                if namespace in DATABASE_NAMESPACES:
                    return self.native_blast_database_results.resolve(context, reference, namespace) if context.role == 'results' else self.native_blast_database_returns.resolve_received(context, reference, namespace)
                if self.native_blast_database_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'scientific_process'}:
                    resolved = self.native_blast_database_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self.native_hmmer_preparation_results is not None:
                from gene_annotation_episode.episodic_workflow.root.a104.hmmer_preparation_result_views import IDENTIFIER_NAMESPACES as HMMER_PREPARATION_NAMESPACES
                if namespace in HMMER_PREPARATION_NAMESPACES:
                    return self.native_hmmer_preparation_results.resolve(context, reference, namespace) if context.role == 'results' else self.native_hmmer_preparation_returns.resolve_received(context, reference, namespace)
                if self.native_hmmer_preparation_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'scientific_process'}:
                    resolved = self.native_hmmer_preparation_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self.native_blast_results is not None:
                if namespace in {'native_blast_pairwise_row', 'native_blast_artifact_key', 'native_blast_search_pointer'}:
                    return self.native_blast_results.resolve(context, reference, namespace) if context.role == 'results' else self.native_blast_returns.resolve_received(context, reference, namespace)
                if self.native_blast_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'scientific_process'}:
                    resolved = self.native_blast_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self._has_appservice():
                from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_homology_returns import IDENTIFIER_NAMESPACES
                if namespace in IDENTIFIER_NAMESPACES:
                    return self.api_execution.homology_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.homology_returns.resolve_received(context, reference, namespace)
                from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_phylogeny_returns import IDENTIFIER_NAMESPACES as PHYLOGENY_NAMESPACES
                if namespace in PHYLOGENY_NAMESPACES:
                    return self.api_execution.phylogeny_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.phylogeny_returns.resolve_received(context, reference, namespace)
                from gene_annotation_episode.episodic_workflow.root.a104.library.bvbrc_proteome_returns import IDENTIFIER_NAMESPACES as PROTEOME_NAMESPACES
                if namespace in PROTEOME_NAMESPACES:
                    return self.api_execution.proteome_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.proteome_returns.resolve_received(context, reference, namespace)
                resolved = self.api_execution.appservice.resolve(context, reference, namespace)
                if resolved is not None:
                    return resolved
            from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_data_views import IDENTIFIER_NAMESPACES
            if namespace in IDENTIFIER_NAMESPACES:
                return self.api_execution is not None and self.api_execution.bvbrc_data.resolve(context, reference, namespace)
            if namespace in {'execution_handle', 'execution'}:
                from gene_annotation_episode.episodic_workflow.root.a104.episode_bindings import reference_in_context
                return bool(self.services is not None and reference_in_context(self.services, context, reference, namespace))
            if context.role in {'launch_local', 'launch_hpc'} and namespace == 'practical_receipt' and (not reference.startswith('source_')):
                return self._delegate(context).resolve(self._practical_context(context), reference, namespace)
            if self.native_hmmer_results.resolve(context, reference, namespace):
                return True
            source = self.store.get(reference)
            if source.get('provider') == LOCAL_FILE_SOURCE_PROVIDER:
                return namespace in {None, 'source'} and self.local_file_sources.read_source(reference, context.scope) is not None
            if source.get('provider') == RESULT_PROVIDER:
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
                from gene_annotation_episode.episodic_workflow.root.a104.episode_bindings import reference_in_context
                return bool(reference_in_context(self.services, context, reference, namespace))
            kind = source['record_type']
            return bool(self.store.reference_subset([reference], plain(context.scope)) and (namespace in {None, kind} or (namespace == 'subject' and kind in {'input', 'feature', 'product', 'read_subject'})))
        except (ValueError, KeyError, OSError):
            return False

