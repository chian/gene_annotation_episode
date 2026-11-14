"""Private A101 results to parent."""
from __future__ import annotations
from .execution_contracts import BLAST_GRADED_RETURN_SCHEMA, BLAST_GRADED_RETURN_SOURCE, LOCAL_FILE_SOURCE_PROVIDER, NATIVE_RESULT_ORIGIN, PracticalReceiptInformation, RESULT_PROVIDER, ROLE_KINDS, TerminalExecutionBehavior, deepcopy, obj, plain, validate_form

class OperationalReport:

    def required_return_sources(self, parent, role):
        """Preserve the original job identity across a scientific owner return."""
        self.credit_kind(role)
        if parent is not None and parent.path[-1][0] == 'scientific_process' and getattr(self.services, 'annotation_task_required', lambda: False)():
            return ('execution_result_refs',)
        return ()

    def _forwards_bvbrc_reports(self, role):
        return role in {'annotation', 'scientific_process'} and self.api_execution is not None and any((service.service == 'bvbrc_data' for service in self.api_execution.services.values()))

    def _forwards_minhash_reports(self, role):
        return role in {'annotation', 'scientific_process'} and self.api_execution is not None and any((service.service == 'bvbrc_minhash' for service in self.api_execution.services.values()))

    def fact_sources(self, role):
        from gene_annotation_episode.episodic_workflow.root.a101.library.hmmer_native_result_views import native_hmmer_fact_sources
        values = native_hmmer_fact_sources()
        if role == 'results':
            from gene_annotation_episode.episodic_workflow.root.a101.local_file_capture_results import SOURCE_REFS_SCHEMA, OUTCOMES_SCHEMA
            for source, schema, meaning in (('execution_file_source_refs', SOURCE_REFS_SCHEMA, 'Source references for selected local file streams actually retained by this results episode; no producing-execution or atomic-version identity is established.'), ('execution_file_capture_outcomes', OUTCOMES_SCHEMA, 'Recorded selected-file availability, original job status and file-custody qualifications; successful byte retention alone does not establish execution success or closed writers.')):
                values[source] = {'type': 'array', 'meaning': meaning, 'report_schema': deepcopy(schema)}
        from gene_annotation_episode.episodic_workflow.root.a101.library.sequence_masking_result_views import masking_fact_sources
        values.update(masking_fact_sources())
        from gene_annotation_episode.episodic_workflow.root.a101.library.blast_utility_result_views import blast_utility_fact_sources
        values.update(blast_utility_fact_sources())
        if self._has_uniprot() and role == 'results':
            from gene_annotation_episode.episodic_workflow.root.a101.library.uniprot_return_contracts import uniprot_fact_sources
            values.update(uniprot_fact_sources())
        if self.native_blast_standard_database_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_standard_database_result_views import standard_blast_database_fact_sources
            values.update(standard_blast_database_fact_sources())
        if self.native_blast_database_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_database_result_views import native_blast_database_fact_sources
            values.update(native_blast_database_fact_sources())
        if self.native_hmmer_preparation_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a101.library.hmmer_preparation_result_views import preparation_fact_sources
            values.update(preparation_fact_sources())
        if self.native_blast_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a101.library.blast_pairwise_result_views import native_blast_fact_sources
            values.update(native_blast_fact_sources())
            values['execution_blast_pairwise_result_refs'] = self._blast_reference_source()
        if self._has_appservice():
            values.update(self._appservice_sources())
        from gene_annotation_episode.episodic_workflow.root.a101.library.bvbrc_data_views import bvbrc_data_fact_sources
        values.update(bvbrc_data_fact_sources())
        if self.api_execution is not None and any((service.service == 'bvbrc_minhash' for service in self.api_execution.services.values())):
            from gene_annotation_episode.episodic_workflow.root.a101.library.bvbrc_minhash_views import minhash_fact_sources
            values.update(minhash_fact_sources())
        if role in {'launch_local', 'launch_hpc'}:
            values.update(TerminalExecutionBehavior.fact_sources(None, role))
        for key, namespace, meaning in (('execution_handoff_refs', 'execution_handoff', 'Qualified original handoff sources actually available to this episode, including authenticated original failed native database attempts for partial-output acquisition; failed attempts do not establish a successful endpoint.'), ('execution_result_refs', 'execution_result', 'Qualified actual requested result acquisitions available to this episode. Generic native windows retain current-filesystem observations. Explicit BLAST/HMMER producer bundles retain original attempt outputs matched by digest and requested numerical facts.')):
            values[key] = {'type': 'array', 'meaning': meaning, 'report_schema': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': namespace}, 'x-source': key}}
        values['execution_completed'] = {'type': 'boolean', 'meaning': 'Whether this assignment has actual verified endpoint information. Generic native results mean requested current-filesystem acquisition plus independently observed successful exact execution, without a producing-attempt or atomic-version claim. Yielding alone is false.'}
        from gene_annotation_episode.episodic_workflow.root.a101.native_hmmer_acquisition import ORIGIN as hmmer_origin
        origins = [NATIVE_RESULT_ORIGIN, hmmer_origin]
        values['execution_result_origin'] = {'type': ['object', 'null'], 'meaning': 'Actual acquisition semantics of retained results: current-file windows, original producer output, or explicitly received saved numerical data. No qualified retained data yields null.', 'report_schema': {**obj({key: {'type': 'string', 'enum': list(dict.fromkeys((origin[key] for origin in origins)))} for key in NATIVE_RESULT_ORIGIN}), 'type': ['object', 'null'], 'x-source': 'execution_result_origin'}}
        from gene_annotation_episode.episodic_workflow.root.a101.library.blast_result_views import BLAST_HSP_FACT_SCHEMA
        values['execution_blast_hsps'] = {'type': 'array', 'meaning': 'Optional explicitly requested native measurements for all published HSPs of this acquired result. No automatic ranking, top-N or significance filter. target_coverage is native reference/hit coverage, not original gene-target coverage. HSP/reference records support later scoped reads; selected HSP references can instead be returned through a parent-chosen typed field. No functional assignment or annotation score.', 'report_schema': {**deepcopy(BLAST_HSP_FACT_SCHEMA), 'x-source': 'execution_blast_hsps'}}
        if role == 'results' and self.api_execution is not None and any((service.service == 'ncbi_blast' for service in self.api_execution.services.values())):
            values[BLAST_GRADED_RETURN_SOURCE] = {'type': 'array', 'meaning': 'Retained output of the original BLAST database grader. Each artifact contains the full grader sheet and probabilities; query and any parent database constraint are checked against the original submission and native report.', 'report_schema': deepcopy(BLAST_GRADED_RETURN_SCHEMA)}
        return values

    def facts(self, context, completion_snapshot):
        return {**self._live_facts(context, completion_snapshot), **self._closed_credit_facts(context, completion_snapshot)}

    def _live_facts(self, context, completion_snapshot):
        from gene_annotation_episode.episodic_workflow.root.a101.library.hmmer_native_result_views import FAMILY_SOURCES
        native_empty = {source: [] for source in FAMILY_SOURCES.values()}
        from gene_annotation_episode.episodic_workflow.root.a101.library.sequence_masking_result_views import masking_fact_sources
        native_empty.update({source: [] for source in masking_fact_sources()})
        from gene_annotation_episode.episodic_workflow.root.a101.library.blast_utility_result_views import blast_utility_fact_sources
        native_empty.update({source: [] for source in blast_utility_fact_sources()})
        if self.native_blast_masking_results.applies(context):
            return {**native_empty, **self.native_blast_masking_results.facts(context)}
        if self.native_blast_utility_results.applies(context):
            return {**native_empty, **self.native_blast_utility_results.facts(context)}
        if self.native_blast_standard_database_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a101.native_blast_standard_database_results import empty_facts
            native_empty.update(empty_facts())
            if self.native_blast_standard_database_results.applies(context):
                return {**native_empty, **self.native_blast_standard_database_results.facts(context)}
        if self.native_blast_database_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a101.native_blast_database_results import empty_facts
            native_empty.update(empty_facts())
            if self.native_blast_database_results.applies(context):
                return {**native_empty, **self.native_blast_database_results.facts(context)}
        if self.native_hmmer_preparation_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a101.library.hmmer_preparation_result_views import preparation_fact_sources
            native_empty.update({source: [] for source in preparation_fact_sources()})
            if self.native_hmmer_preparation_results.applies(context):
                return {**native_empty, **self.native_hmmer_preparation_results.facts(context)}
        if self.native_blast_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a101.library.blast_pairwise_result_views import FAMILY_SOURCES as BLAST_SOURCES
            native_empty.update({source: [] for source in BLAST_SOURCES.values()})
            native_empty['execution_blast_pairwise_result_refs'] = []
            if self.native_blast_results.applies(context):
                return {**native_empty, **self.native_blast_results.facts(context)}
        if self.native_hmmer_results.applies(context):
            return {**native_empty, **self.native_hmmer_results.facts(context)}
        if self._target(context)['resource_kind'] == 'api':
            facts = self.api_execution.facts(context, completion_snapshot)
            required = self._blast_target_requirement(self._target(context), context.scope)
            if required is not None:
                facts[BLAST_GRADED_RETURN_SOURCE] = self._blast_grader_rows(context, facts['execution_result_refs'], required)
            return {**native_empty, **facts, 'execution_result_origin': None}
        extra = {}
        with self.store.read_snapshot():
            read = self.job_progress_provider.targets._handoff_reader()
            _, handoffs, results = self._received(context, _handoff_read=read)
            completed = extra.get('practical_completed', False) if 'results' in ROLE_KINDS else self._native_results_complete(context, list(results.values()))
            return {**native_empty, **extra, 'execution_handoff_refs': sorted(handoffs), **({'bvbrc_appservice_support_refs': self.api_execution.appservice.received_support_refs(context)} if self._has_appservice() else {}), 'execution_blast_hsps': [], 'execution_result_refs': sorted((ref for ref, body in results.items() if body['windows'])), 'execution_file_source_refs': sorted({row['source_ref'] for body in results.values() for row in body.get('captured_files', []) if row['source_ref'] is not None}), 'execution_file_capture_outcomes': self.local_file_sources.outcomes_for_context(context) if self.local_file_sources.applies(context) else [], 'execution_result_origin': deepcopy(NATIVE_RESULT_ORIGIN) if any((body['windows'] for body in results.values())) else None, 'execution_completed': completed}

    def resolve(self, context, reference, namespace):
        try:
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

            if self.native_blast_standard_database_results is not None:
                from gene_annotation_episode.episodic_workflow.root.a101.native_blast_standard_database_results import IDENTIFIER_NAMESPACES as DATABASE_NAMESPACES
                if namespace in DATABASE_NAMESPACES:
                    return self.native_blast_standard_database_results.resolve(context, reference, namespace) if context.role == 'results' else self.native_blast_standard_database_returns.resolve_received(context, reference, namespace)
                if self.native_blast_standard_database_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'scientific_process'}:
                    resolved = self.native_blast_standard_database_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self.native_blast_database_results is not None:
                from gene_annotation_episode.episodic_workflow.root.a101.native_blast_database_results import IDENTIFIER_NAMESPACES as DATABASE_NAMESPACES
                if namespace in DATABASE_NAMESPACES:
                    return self.native_blast_database_results.resolve(context, reference, namespace) if context.role == 'results' else self.native_blast_database_returns.resolve_received(context, reference, namespace)
                if self.native_blast_database_results.resolve(context, reference, namespace):
                    return True
                if context.role in {'annotation', 'scientific_process'}:
                    resolved = self.native_blast_database_returns.resolve_received(context, reference, namespace)
                    if resolved is not None:
                        return resolved
            if self.native_hmmer_preparation_results is not None:
                from gene_annotation_episode.episodic_workflow.root.a101.library.hmmer_preparation_result_views import IDENTIFIER_NAMESPACES as HMMER_PREPARATION_NAMESPACES
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
                from gene_annotation_episode.episodic_workflow.root.a101.library.bvbrc_homology_return_values import IDENTIFIER_NAMESPACES
                if namespace in IDENTIFIER_NAMESPACES:
                    return self.api_execution.homology_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.homology_returns.resolve_received(context, reference, namespace)
                from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.bvbrc_phylogeny_returns import IDENTIFIER_NAMESPACES as PHYLOGENY_NAMESPACES
                if namespace in PHYLOGENY_NAMESPACES:
                    return self.api_execution.phylogeny_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.phylogeny_returns.resolve_received(context, reference, namespace)
                from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.bvbrc_alignment_returns import IDENTIFIER_NAMESPACES as ALIGNMENT_NAMESPACES
                if namespace in ALIGNMENT_NAMESPACES:
                    return self.api_execution.alignment_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.alignment_returns.resolve_received(context, reference, namespace)
                from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.bvbrc_genome_alignment_returns import IDENTIFIER_NAMESPACES as GENOME_ALIGNMENT_NAMESPACES
                if namespace in GENOME_ALIGNMENT_NAMESPACES:
                    return self.api_execution.genome_alignment_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.genome_alignment_returns.resolve_received(context, reference, namespace)
                from gene_annotation_episode.episodic_workflow.root.a101.library.bvbrc_proteome_return_values import IDENTIFIER_NAMESPACES as PROTEOME_NAMESPACES
                if namespace in PROTEOME_NAMESPACES:
                    return self.api_execution.proteome_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.proteome_returns.resolve_received(context, reference, namespace)
                from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.bvbrc_comparative_systems_returns import IDENTIFIER_NAMESPACES as COMPARATIVE_NAMESPACES
                if namespace in COMPARATIVE_NAMESPACES:
                    return self.api_execution.comparative_systems_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.comparative_systems_returns.resolve_received(context, reference, namespace)
                from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.bvbrc_fastqutils_returns import IDENTIFIER_NAMESPACES as FASTQUTILS_NAMESPACES
                if namespace in FASTQUTILS_NAMESPACES:
                    return self.api_execution.fastqutils_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.fastqutils_returns.resolve_received(context, reference, namespace)
                from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.bvbrc_application_returns import IDENTIFIER_NAMESPACES as APPLICATION_NAMESPACES
                if namespace in APPLICATION_NAMESPACES:
                    return self.api_execution.application_returns.resolve_own(context, reference, namespace) if context.role == 'results' else self.api_execution.application_returns.resolve_received(context, reference, namespace)
                resolved = self.api_execution.appservice.resolve(context, reference, namespace)
                if resolved is not None:
                    return resolved
            if namespace == 'bvbrc_minhash_genome':
                if self.api_execution is None:
                    return False
                if context.role == 'results':
                    return self.api_execution.minhash.resolve_own(context, reference, namespace)
                return self.api_execution.minhash.resolve_received(context, reference, namespace)
            from gene_annotation_episode.episodic_workflow.root.a101.library.bvbrc_data_views import IDENTIFIER_NAMESPACES
            if namespace in IDENTIFIER_NAMESPACES:
                return self.api_execution is not None and self.api_execution.bvbrc_data.resolve(context, reference, namespace)
            if namespace in {'execution_handle', 'execution'}:
                from gene_annotation_episode.episodic_workflow.root.a101.episode_bindings import reference_in_context
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
                from gene_annotation_episode.episodic_workflow.root.a101.episode_bindings import reference_in_context
                return bool(reference_in_context(self.services, context, reference, namespace))
            kind = source['record_type']
            return bool(self.store.reference_subset([reference], plain(context.scope)) and (namespace in {None, kind} or (namespace == 'subject' and kind in {'input', 'feature', 'product', 'read_subject'})))
        except (ValueError, KeyError, OSError):
            return False

    def validate_report(self, context, form, original_schema):
        self.native_blast_masking_returns.validate_received_report(context, form, original_schema)
        self.native_blast_utility_returns.validate_received_report(context, form, original_schema)
        frozen_facts = None
        if self._has_uniprot():
            from gene_annotation_episode.episodic_workflow.root.a101.library.uniprot_return_contracts import requested_uniprot_selection
            if requested_uniprot_selection(plain(original_schema)) is not None:
                host = self.api_execution.uniprot_returns
                host.validate_received_report(context, form, original_schema)
                if host._successful_closed(context):
                    frozen_facts = host._closed(context)['facts']
        validate_form(form, original_schema, lambda ref, ns: self.resolve(context, ref, ns))
        fact_fields = {name: declared['x-source'] for name, declared in plain(original_schema).get('properties', {}).items() if declared.get('x-source') is not None}
        if not fact_fields:
            return
        facts = self.facts(context, {}) if frozen_facts is None else frozen_facts
        for name, source in fact_fields.items():
            if source in facts and form[name] != facts[source]:
                raise ValueError('execution_report_disagrees_with_recorded_facts')
