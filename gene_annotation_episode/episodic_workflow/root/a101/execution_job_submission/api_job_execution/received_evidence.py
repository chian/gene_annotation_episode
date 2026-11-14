"""Private A101 launch_api received evidence."""
from __future__ import annotations
from .execution_contracts import BLAST_GRADED_RETURN_SOURCE, RESULT_PROVIDER, deepcopy, plain

class ReceivedOperationalEvidence:

    def _received(self, context, selection=None, *, _handoff_read=None):
        with self.store.read_snapshot():
            selection = self._selection(context, selection)
            read = self.job_progress_provider.targets._handoff_reader() if _handoff_read is None else _handoff_read
            handoffs, results = ({}, {})
            for reference in dict.fromkeys(selection['known_record_refs']):
                source = self.store.get(reference)
                if source.get('provider') == RESULT_PROVIDER:
                    if source.get('version') in {'native_blast_utility_bundle_v1', 'native_blast_masking_bundle_v1', 'native_hmmer_bundle_v1', 'native_blast_bundle_v1', 'native_blast_database_bundle_v1', 'native_blast_standard_database_bundle_v1', 'native_hmmer_preparation_bundle_v1'}:
                        continue
                    body = self._read_result(reference, context.scope)
                    if context.role == 'results' and body['assignment'] != plain(context.assignment):
                        continue
                    results[reference] = body
                    continue
                if source.get('provider') != 'episode.practical_receipt' and (not (self.api_execution is not None and self.api_execution.is_handoff_source(reference))):
                    continue
                try:
                    target, _, returnable = read(reference, context.scope)
                except (ValueError, KeyError):
                    continue
                try:
                    self._context_target(context, target)
                except ValueError:
                    continue
                if returnable:
                    handoffs[reference] = target
            return (selection, handoffs, results)

    def received_report_sources(self, role):
        result = {}
        if role in {'annotation', 'scientific_process'}:
            for source in ('execution_file_source_refs', 'execution_file_capture_outcomes'):
                definition = self.fact_sources('results').get(source)
                if definition is not None:
                    result[source] = deepcopy(definition)
        if role in {'annotation', 'scientific_process'}:
            from gene_annotation_episode.episodic_workflow.root.a101.library.sequence_masking_result_views import masking_fact_sources
            result.update(masking_fact_sources())
            from gene_annotation_episode.episodic_workflow.root.a101.library.blast_utility_result_views import blast_utility_fact_sources
            result.update(blast_utility_fact_sources())
        if self._has_uniprot() and role in {'annotation', 'scientific_process'}:
            from gene_annotation_episode.episodic_workflow.root.a101.library.uniprot_return_contracts import uniprot_fact_sources
            result.update(uniprot_fact_sources())
        if self.native_blast_standard_database_returns is not None and role in {'annotation', 'scientific_process'}:
            from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_standard_database_result_views import standard_blast_database_fact_sources
            result.update(standard_blast_database_fact_sources())
        if self.native_blast_database_returns is not None and role in {'annotation', 'scientific_process'}:
            from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_database_result_views import native_blast_database_fact_sources
            result.update(native_blast_database_fact_sources())
        if self.native_hmmer_preparation_returns is not None and role in {'annotation', 'scientific_process'}:
            from gene_annotation_episode.episodic_workflow.root.a101.library.hmmer_preparation_result_views import preparation_fact_sources
            result.update(preparation_fact_sources())
        if self.native_blast_returns is not None and role in {'annotation', 'scientific_process'}:
            from gene_annotation_episode.episodic_workflow.root.a101.library.blast_pairwise_result_views import native_blast_fact_sources
            result.update(native_blast_fact_sources())
            result['execution_blast_pairwise_result_refs'] = self._blast_reference_source()
        if self._forwards_bvbrc_reports(role):
            from gene_annotation_episode.episodic_workflow.root.a101.library.bvbrc_data_views import bvbrc_data_fact_sources
            result.update(bvbrc_data_fact_sources())
        if self._forwards_minhash_reports(role):
            from gene_annotation_episode.episodic_workflow.root.a101.library.bvbrc_minhash_views import minhash_fact_sources
            result.update(minhash_fact_sources())
        if self._has_appservice() and role in {'annotation', 'scientific_process'}:
            result.update(self._appservice_sources())
        return result

    def received_report_facts(self, context):
        schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
        result = {}
        if context.role in {'annotation', 'scientific_process'}:
            requested = {node.get('x-source') for node in schema.get('properties', {}).values()}
            if 'execution_file_source_refs' in requested:
                result['execution_file_source_refs'] = self.local_file_sources.received_sources(context)
            if 'execution_file_capture_outcomes' in requested:
                result['execution_file_capture_outcomes'] = self.local_file_sources.received_outcomes(context)
        if context.role in {'annotation', 'scientific_process'}:
            result.update(self.native_blast_masking_returns.received_facts(context, schema))
            result.update(self.native_blast_utility_returns.received_facts(context, schema))
        if self._has_uniprot() and context.role in {'annotation', 'scientific_process'}:
            result.update(self.api_execution.uniprot_returns.facts_for_closure(context, schema))
        if self.native_blast_standard_database_returns is not None and context.role in {'annotation', 'scientific_process'}:
            result.update(self.native_blast_standard_database_returns.received_facts(context, schema))
        if self.native_blast_database_returns is not None and context.role in {'annotation', 'scientific_process'}:
            result.update(self.native_blast_database_returns.received_facts(context, schema))
        if self.native_hmmer_preparation_returns is not None and context.role in {'annotation', 'scientific_process'}:
            result.update(self.native_hmmer_preparation_returns.received_facts(context, schema))
        if self.native_blast_returns is not None and context.role in {'annotation', 'scientific_process'}:
            result.update(self.native_blast_returns.received_facts(context, schema))
        if self._forwards_bvbrc_reports(context.role):
            result.update(self.api_execution.bvbrc_data.received_facts(context, schema))
        if self._forwards_minhash_reports(context.role):
            result.update(self.api_execution.minhash.received_facts(context, schema))
        if self._has_appservice() and context.role in {'annotation', 'scientific_process'}:
            if any((node.get('x-source') == 'bvbrc_appservice_support_refs' for node in schema.get('properties', {}).values())):
                result['bvbrc_appservice_support_refs'] = self.api_execution.appservice.received_support_refs(context)
            result.update(self.api_execution.homology_returns.received_facts(context, schema))
            result.update(self.api_execution.phylogeny_returns.received_facts(context, schema))
            result.update(self.api_execution.alignment_returns.received_facts(context, schema))
            result.update(self.api_execution.genome_alignment_returns.received_facts(context, schema))
            proteome = self.api_execution.proteome_returns.received_facts(context, schema)
            if set(result).intersection(proteome):
                raise ValueError('received_report_fact_conflict')
            result.update(proteome)
            comparative = self.api_execution.comparative_systems_returns.received_facts(context, schema)
            if set(result).intersection(comparative):
                raise ValueError('received_report_fact_conflict')
            result.update(comparative)
            fastqutils = self.api_execution.fastqutils_returns.received_facts(context, schema)
            if set(result).intersection(fastqutils):
                raise ValueError('received_report_fact_conflict')
            result.update(fastqutils)
            application = self.api_execution.application_returns.received_facts(context, schema)
            if set(result).intersection(application):
                raise ValueError('received_report_fact_conflict')
            result.update(application)
        return result

    def received_report_closure_facts(self, context):
        """Private return bindings, called only by the registry at episode closure."""
        if context.role not in {'annotation', 'scientific_process'}:
            return {}
        schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
        result = {}
        return result

    def resolve_received_reference(self, context, reference, namespace):
        captured = self.local_file_sources.reference_access(context, reference, namespace)
        if captured is not None:
            return captured
        fba = self._flux_balance_reference_access(context, reference, namespace)

        if fba is not None:
            return fba

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
            from gene_annotation_episode.episodic_workflow.root.a101.library.bvbrc_homology_return_values import IDENTIFIER_NAMESPACES
            if namespace in IDENTIFIER_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.homology_returns.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.bvbrc_phylogeny_returns import IDENTIFIER_NAMESPACES as PHYLOGENY_NAMESPACES
            if namespace in PHYLOGENY_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.phylogeny_returns.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.bvbrc_alignment_returns import IDENTIFIER_NAMESPACES as ALIGNMENT_NAMESPACES
            if namespace in ALIGNMENT_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.alignment_returns.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.bvbrc_genome_alignment_returns import IDENTIFIER_NAMESPACES as GENOME_ALIGNMENT_NAMESPACES
            if namespace in GENOME_ALIGNMENT_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.genome_alignment_returns.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.a101.library.bvbrc_proteome_return_values import IDENTIFIER_NAMESPACES as PROTEOME_NAMESPACES
            if namespace in PROTEOME_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.proteome_returns.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.bvbrc_comparative_systems_returns import IDENTIFIER_NAMESPACES as COMPARATIVE_NAMESPACES
            if namespace in COMPARATIVE_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.comparative_systems_returns.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.bvbrc_fastqutils_returns import IDENTIFIER_NAMESPACES as FASTQUTILS_NAMESPACES
            if namespace in FASTQUTILS_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.fastqutils_returns.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.bvbrc_application_returns import IDENTIFIER_NAMESPACES as APPLICATION_NAMESPACES
            if namespace in APPLICATION_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.application_returns.resolve_received(context, reference, namespace)
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
        from gene_annotation_episode.episodic_workflow.root.a101.library.hmmer_native_result_views import FAMILY_SOURCES
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
