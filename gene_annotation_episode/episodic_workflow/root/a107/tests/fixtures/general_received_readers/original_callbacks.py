def received_report_sources(self, role):
    result = {}
    if role in {'annotation', 'scientific_process'}:
        for source in ('execution_file_source_refs', 'execution_file_capture_outcomes'):
            definition = self.fact_sources('results').get(source)
            if definition is not None:
                result[source] = deepcopy(definition)
    if role in {'annotation', 'scientific_process'}:
        from gene_annotation_episode.episodic_workflow.root.a107.sequence_masking_result_views import masking_fact_sources
        result.update(masking_fact_sources())
        from gene_annotation_episode.episodic_workflow.root.a107.blast_utility_result_views import blast_utility_fact_sources
        result.update(blast_utility_fact_sources())
    if self._has_uniprot() and role in {'annotation', 'scientific_process'}:
        from gene_annotation_episode.episodic_workflow.root.a107.uniprot_return_contracts import uniprot_fact_sources
        result.update(uniprot_fact_sources())
    if self.rna_structure_comparison_returns is not None and role in {'annotation', 'scientific_process'}:
        from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_comparison_views import rna_comparison_fact_sources
        result.update(rna_comparison_fact_sources())
    if self.native_expression_nmf_returns is not None and role in {'annotation', 'scientific_process'}:
        from gene_annotation_episode.episodic_workflow.root.a107.expression_nmf_return_views import expression_nmf_fact_sources
        result.update(expression_nmf_fact_sources())
    if self.native_rna_structure_returns is not None and role in {'annotation', 'scientific_process'}:
        from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_result_views import rna_structure_fact_sources
        result.update(rna_structure_fact_sources())
    if self.native_infernal_preparation_returns is not None and role in {'annotation', 'scientific_process'}:
        from gene_annotation_episode.episodic_workflow.root.a107.infernal_preparation_result_views import preparation_fact_sources
        result.update(preparation_fact_sources())
    if self.native_infernal_returns is not None and role in {'annotation', 'scientific_process'}:
        from gene_annotation_episode.episodic_workflow.root.a107.infernal_native_result_views import native_infernal_fact_sources
        result.update(native_infernal_fact_sources())
        result['execution_infernal_result_refs'] = self._infernal_reference_source()
    if self.native_blast_standard_database_returns is not None and role in {'annotation', 'scientific_process'}:
        from gene_annotation_episode.episodic_workflow.root.a107.native_blast_standard_database_result_views import standard_blast_database_fact_sources
        result.update(standard_blast_database_fact_sources())
    if self.native_blast_database_returns is not None and role in {'annotation', 'scientific_process'}:
        from gene_annotation_episode.episodic_workflow.root.a107.native_blast_database_result_views import native_blast_database_fact_sources
        result.update(native_blast_database_fact_sources())
    if self.native_hmmer_preparation_returns is not None and role in {'annotation', 'scientific_process'}:
        from gene_annotation_episode.episodic_workflow.root.a107.hmmer_preparation_result_views import preparation_fact_sources
        result.update(preparation_fact_sources())
    if self.native_blast_returns is not None and role in {'annotation', 'scientific_process'}:
        from gene_annotation_episode.episodic_workflow.root.a107.blast_pairwise_result_views import native_blast_fact_sources
        result.update(native_blast_fact_sources())
        result['execution_blast_pairwise_result_refs'] = self._blast_reference_source()
    if self._has_rfam() and role in {'annotation', 'scientific_process'}:
        from gene_annotation_episode.episodic_workflow.root.a107.rfam_batch_returns import rfam_fact_sources
        result.update(rfam_fact_sources())
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
    if self._has_rfam() and context.role in {'annotation', 'scientific_process'}:
        result.update(self.api_execution.rfam_returns.received_facts(context, schema))
    if self._has_appservice() and context.role in {'annotation', 'scientific_process'}:
        if any((node.get('x-source') == 'bvbrc_appservice_support_refs' for node in schema.get('properties', {}).values())):
            result['bvbrc_appservice_support_refs'] = self.api_execution.appservice.received_support_refs(context)
        result.update(self.api_execution.homology_returns.received_facts(context, schema))
    if self.rna_structure_comparison_returns is not None and context.role in {'annotation', 'scientific_process'}:
        result.update(self.rna_structure_comparison_returns.received_facts(context, schema))
    if self.native_expression_nmf_returns is not None and context.role in {'annotation', 'scientific_process'} and (schema.get('properties') is not None):
        result.update(self.native_expression_nmf_returns.facts_for_closure(context, schema))
    if self.native_rna_structure_returns is not None and context.role in {'annotation', 'scientific_process'}:
        result.update(self.native_rna_structure_returns.received_facts(context, schema))
    if self.native_infernal_preparation_returns is not None and context.role in {'annotation', 'scientific_process'}:
        result.update(self.native_infernal_preparation_returns.received_facts(context, schema))
    if self.native_infernal_returns is not None and context.role in {'annotation', 'scientific_process'}:
        result.update(self.native_infernal_returns.received_facts(context, schema))
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
    nmf = self._expression_nmf_reference_access(context, reference, namespace)
    if nmf is not None:
        return nmf
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
    if self.rna_structure_comparison_results is not None:
        from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_comparison_results import IDENTIFIER_NAMESPACES as COMPARISON_NAMESPACES
        if namespace in COMPARISON_NAMESPACES:
            return self.rna_structure_comparison_results.resolve(context, reference, namespace) if context.role == 'results' else self.rna_structure_comparison_returns.resolve_received(context, reference, namespace)
        access = self.rna_structure_comparison_results.retained_reference_access(context, reference, namespace)
        if access is not None:
            return access
    if self.native_rna_structure_results is not None:
        access = self.native_rna_structure_results.retained_reference_access(context, reference, namespace)
        if access is not None:
            return access
        if context.role in {'annotation', 'scientific_process'}:
            resolved = self.native_rna_structure_returns.resolve_received(context, reference, namespace)
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
    if self.native_infernal_preparation_returns is not None and context.role in {'annotation', 'scientific_process'}:
        resolved = self.native_infernal_preparation_returns.resolve_received(context, reference, namespace)
        if resolved is not None:
            return resolved
    if self.native_infernal_returns is not None and context.role in {'annotation', 'scientific_process'}:
        resolved = self.native_infernal_returns.resolve_received(context, reference, namespace)
        if resolved is not None:
            return resolved
    if self.native_blast_returns is not None and context.role in {'annotation', 'scientific_process'}:
        resolved = self.native_blast_returns.resolve_received(context, reference, namespace)
        if resolved is not None:
            return resolved
    if self._has_rfam() and context.role in {'annotation', 'scientific_process'}:
        resolved = self.api_execution.rfam_returns.resolve_received(context, reference, namespace)
        if resolved is not None:
            return resolved
    if self._has_appservice():
        from gene_annotation_episode.episodic_workflow.root.a107.bvbrc_homology_returns import IDENTIFIER_NAMESPACES
        if namespace in IDENTIFIER_NAMESPACES:
            if context.role == 'results':
                return None
            return self.api_execution.homology_returns.resolve_received(context, reference, namespace)
        resolved = self.api_execution.appservice.resolve(context, reference, namespace)
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
    if self.rna_structure_comparison_returns is not None:
        self.rna_structure_comparison_returns.validate_received_report(context, form, schema)
    if self.native_expression_nmf_returns is not None:
        self.native_expression_nmf_returns.validate_received_report(context, form, schema)
    if self.native_rna_structure_returns is not None:
        self.native_rna_structure_returns.validate_received_report(context, form, schema)
    if self.native_infernal_preparation_returns is not None:
        self.native_infernal_preparation_returns.validate_received_report(context, form, schema)
    if self.native_infernal_returns is not None:
        self.native_infernal_returns.validate_received_report(context, form, schema)
    if self.native_blast_standard_database_returns is not None:
        self.native_blast_standard_database_returns.validate_received_report(context, form, schema)
    if self.native_blast_database_returns is not None:
        self.native_blast_database_returns.validate_received_report(context, form, schema)
    if self.native_hmmer_preparation_returns is not None:
        self.native_hmmer_preparation_returns.validate_received_report(context, form, schema)
    if self.native_blast_returns is not None:
        self.native_blast_returns.validate_received_report(context, form, schema)
    if self._has_rfam():
        self.api_execution.rfam_returns.validate_received_report(context, form, schema)
    if self._has_appservice():
        self.api_execution.homology_returns.validate_received_report(context, form, schema)

def received_form_references(self, context, form, schema, operation_key):
    from gene_annotation_episode.episodic_workflow.root.a107.hmmer_native_result_views import FAMILY_SOURCES
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
    for adapter in (self.rna_structure_comparison_returns, self.native_rna_structure_returns, self.native_expression_nmf_returns, self.native_infernal_preparation_returns, self.native_infernal_returns):
        if adapter is not None:
            admitted = adapter.record_admission(context, form, schema, operation_key)
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
    if self._has_rfam():
        references.extend(self.api_execution.rfam_returns.record_admission(context, form, schema, operation_key))
    if self._has_appservice():
        references.extend(self.api_execution.homology_returns.record_admission(context, form, schema, operation_key))
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
