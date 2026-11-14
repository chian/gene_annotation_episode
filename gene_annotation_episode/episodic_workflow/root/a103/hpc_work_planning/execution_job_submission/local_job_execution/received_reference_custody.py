"""Original receiving-context reference access, typed report admission and receipt custody callbacks."""
from __future__ import annotations
from .contracts import BLAST_GRADED_RETURN_SOURCE, RESULT_PROVIDER, deepcopy, plain

class ReceivedReferenceCustody:

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
        if self.native_blast_standard_database_returns is not None and context.role in {'annotation', 'scientific_process'}:
            resolved = self.native_blast_standard_database_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self.native_blast_database_returns is not None and context.role in {'annotation', 'scientific_process'}:
            resolved = self.native_blast_database_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self.native_hmmer_preparation_returns is not None and context.role in {'annotation', 'scientific_process'}:
            resolved = self.native_hmmer_preparation_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self.native_blast_returns is not None and context.role in {'annotation', 'scientific_process'}:
            resolved = self.native_blast_returns.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self._has_appservice():
            from gene_annotation_episode.episodic_workflow.root.a103.bvbrc_homology_returns import IDENTIFIER_NAMESPACES
            if namespace in IDENTIFIER_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.homology_returns.resolve_received(context, reference, namespace)
            resolved = self.api_execution.appservice.resolve(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self._forwards_bvbrc_reports(context.role):
            resolved = self.api_execution.bvbrc_data.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        if self._forwards_minhash_reports(context.role):
            resolved = self.api_execution.minhash.resolve_received(context, reference, namespace)
            if resolved is not None:
                return resolved
        for results in (self.native_hmmer_preparation_results,):
            if results is not None:
                resolved = results.retained_reference_access(context, reference, namespace)
                if resolved is not None:
                    return resolved
        return None

    def validate_received_report(self, context, form, schema):
        self.local_file_sources.validate_received_report(context, form, schema)
        self.native_blast_masking_returns.validate_received_report(context, form, schema)
        self.native_blast_utility_returns.validate_received_report(context, form, schema)
        if self._has_uniprot():
            self.api_execution.uniprot_returns.validate_received_report(context, form, schema)
        if self.native_blast_standard_database_returns is not None:
            self.native_blast_standard_database_returns.validate_received_report(context, form, schema)
        if self.native_blast_database_returns is not None:
            self.native_blast_database_returns.validate_received_report(context, form, schema)
        if self.native_hmmer_preparation_returns is not None:
            self.native_hmmer_preparation_returns.validate_received_report(context, form, schema)
        if self.native_blast_returns is not None:
            self.native_blast_returns.validate_received_report(context, form, schema)
        if self._has_appservice():
            self.api_execution.appservice.validate_received_report(context, form, schema)
            self.api_execution.homology_returns.validate_received_report(context, form, schema)
            self.api_execution.phylogeny_returns.validate_received_report(context, form, schema)
            self.api_execution.alignment_returns.validate_received_report(context, form, schema)
            self.api_execution.genome_alignment_returns.validate_received_report(context, form, schema)
            self.api_execution.proteome_returns.validate_received_report(context, form, schema)
            self.api_execution.comparative_systems_returns.validate_received_report(context, form, schema)
            self.api_execution.fastqutils_returns.validate_received_report(context, form, schema)
            self.api_execution.application_returns.validate_received_report(context, form, schema)
        if self._forwards_bvbrc_reports(context.role):
            self.api_execution.bvbrc_data.validate_received_report(context, form, schema)
        if self._forwards_minhash_reports(context.role):
            self.api_execution.minhash.validate_received_report(context, form, schema)

    def received_form_references(self, context, form, schema, operation_key):
        from gene_annotation_episode.episodic_workflow.root.a103.hmmer_native_result_views import FAMILY_SOURCES
        references = []
        native_references = set()
        references.extend(self.local_file_sources.admit_return(context, form, schema, operation_key))
        if self._has_uniprot():
            references.extend(self.api_execution.uniprot_returns.record_admission(context, form, schema, operation_key))
        admitted = self.native_blast_masking_returns.record_admission(context, form, schema, operation_key)
        native_references.update(admitted)
        references.extend(admitted)
        admitted = self.native_blast_utility_returns.record_admission(context, form, schema, operation_key)
        native_references.update(admitted)
        references.extend(admitted)
        if self.native_blast_standard_database_returns is not None:
            admitted = self.native_blast_standard_database_returns.record_admission(context, form, schema, operation_key)
            native_references.update(admitted)
            references.extend(admitted)
        if self.native_blast_database_returns is not None:
            admitted = self.native_blast_database_returns.record_admission(context, form, schema, operation_key)
            native_references.update(admitted)
            references.extend(admitted)
        if self.native_hmmer_preparation_returns is not None:
            admitted = self.native_hmmer_preparation_returns.record_admission(context, form, schema, operation_key)
            native_references.update(admitted)
            references.extend(admitted)
        if self.native_blast_returns is not None:
            admitted = self.native_blast_returns.record_admission(context, form, schema, operation_key)
            native_references.update(admitted)
            references.extend(admitted)
        if self.api_execution is not None:
            references.extend(self.api_execution.record_bvbrc_admission(context, form, schema, operation_key))
            references.extend(self.api_execution.minhash.record_admission(context, form, schema, operation_key))
            references.extend(self.api_execution.homology_returns.record_admission(context, form, schema, operation_key))
            references.extend(self.api_execution.phylogeny_returns.record_admission(context, form, schema, operation_key))
            references.extend(self.api_execution.alignment_returns.record_admission(context, form, schema, operation_key))
            references.extend(self.api_execution.genome_alignment_returns.record_admission(context, form, schema, operation_key))
            references.extend(self.api_execution.proteome_returns.record_admission(context, form, schema, operation_key))
            references.extend(self.api_execution.comparative_systems_returns.record_admission(context, form, schema, operation_key))
            references.extend(self.api_execution.fastqutils_returns.record_admission(context, form, schema, operation_key))
            admitted = self.api_execution.application_returns.record_admission(context, form, schema, operation_key)
            references.extend(admitted)
            native_references.update(admitted)
        for name, declared in plain(schema).get('properties', {}).items():
            if declared.get('x-source') in FAMILY_SOURCES.values():
                for row in form[name]:
                    for reference in [row['source_ref'], row['observation_ref'], *row['reference_refs']]:
                        if reference is None:
                            continue
                        if not self.resolve(context, reference, 'execution_result'):
                            raise ValueError('execution_received_reference_unqualified')
                        references.append(reference)
            if declared.get('x-source') == 'execution_blast_hsps':
                for row in form[name]:
                    for field in ('hsp_ref', 'reference_ref'):
                        reference = row[field]
                        if not self.resolve(context, reference, 'execution_result'):
                            raise ValueError('execution_received_reference_unqualified')
                        references.append(reference)
            if declared.get('x-source') == BLAST_GRADED_RETURN_SOURCE:
                for row in form[name]:
                    if not self.resolve(context, row['result_ref'], 'execution_result'):
                        raise ValueError('blast_grader_result_reference_unqualified')
                    references.append(row['result_ref'])
            if declared.get('x-source') in {'execution_handoff_refs', 'execution_result_refs', 'practical_receipt_refs', 'bvbrc_appservice_support_refs'}:
                for reference in form[name]:
                    namespace = declared['items'].get('x-reference-namespace')
                    already_admitted = namespace == 'execution_result' and reference in native_references
                    if not already_admitted and (not self.resolve(context, reference, namespace)):
                        raise ValueError('execution_received_reference_unqualified')
                    references.append(reference)
        return list(dict.fromkeys(references))
