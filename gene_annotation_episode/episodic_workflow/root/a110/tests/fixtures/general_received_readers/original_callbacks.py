def received_report_sources(self, role):
    result = {}
    if role in {'annotation', 'scientific_process'}:
        for source in ('execution_file_source_refs', 'execution_file_capture_outcomes'):
            definition = self.fact_sources('results').get(source)
            if definition is not None:
                result[source] = deepcopy(definition)
        if self.native_flux_balance_returns is not None:
            from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_return_views import fba_fact_sources
            sources = fba_fact_sources()
            if self.native_flux_balance_returns.ordinary_backend is None:
                sources = {name: sources[name] for name in ('flux_balance_measurements', 'flux_balance_saved_sheets', 'flux_balance_failures')}
            result.update(sources)
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
        if self.native_flux_balance_returns is not None and schema.get('properties') is not None:
            result.update(self.native_flux_balance_returns.facts_for_closure(context, schema))
    return result

def received_report_closure_facts(self, context):
    if context.role not in {'annotation', 'scientific_process'}:
        return {}
    schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
    if self.native_flux_balance_returns is not None and schema.get('properties') is not None:
        return self.native_flux_balance_returns.ordinary_closure_facts(context, schema)
    return {}

def resolve_received_reference(self, context, reference, namespace):
    captured = self.local_file_sources.reference_access(context, reference, namespace)
    if captured is not None:
        return captured
    return self._flux_balance_reference_access(context, reference, namespace)

def validate_received_report(self, context, form, schema):
    self.local_file_sources.validate_received_report(context, form, schema)
    if self.native_flux_balance_returns is not None:
        self.native_flux_balance_returns.validate_received_report(context, form, schema)

def received_form_references(self, context, form, schema, operation_key):
    references = self.local_file_sources.admit_return(context, form, schema, operation_key)
    if self.native_flux_balance_returns is not None:
        references.extend(self.native_flux_balance_returns.record_admission(context, form, schema, operation_key))
    for name, declared in plain(schema).get('properties', {}).items():
        if declared.get('x-source') in {'execution_handoff_refs', 'execution_result_refs', 'practical_receipt_refs'}:
            for reference in form[name]:
                namespace = declared['items'].get('x-reference-namespace')
                if not self.resolve(context, reference, namespace):
                    raise ValueError('execution_received_reference_unqualified')
                references.append(reference)
    return list(dict.fromkeys(references))
