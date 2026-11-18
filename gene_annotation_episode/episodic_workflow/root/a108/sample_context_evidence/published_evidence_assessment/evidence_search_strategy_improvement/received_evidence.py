from __future__ import annotations
'received evidence for this private A108 episode.'
from gene_annotation_episode.episodic_workflow.root.a108.sample_context_evidence.published_evidence_assessment.evidence_search_strategy_improvement.source_contracts import ContractError, ROLES, ReportBoundaryError, plain, replace

class LiteratureReceivedEvidence:

    def received_report_sources(self, role):
        return self._a108_fact_sources() if role not in ROLES else {}

    def received_report_facts(self, context):
        if context.role in ROLES:
            return {}
        result = {}
        for namespace, _, _, repository in self._population_routes():
            cells = repository().received_cells(context)
            if cells:
                result[namespace] = cells
        return self._complete_requested_received_arrays(context, result)

    def _complete_requested_received_arrays(self, context, result):
        """Supply selected declared arrays even when no cells were delivered.

        Empty means no received cells of that requested type. It does not
        report an unavailable numerical component as zero, infer a biological
        absence or expose unrequested cells from a known sheet reference.
        """
        contract = plain(context.request).get('report_contract') or {}
        schema = contract.get('measurements', {}).get('schema', {})
        declared = self.received_report_sources(context.role)
        for node in schema.get('properties', {}).values():
            source = node.get('x-source')
            if source in declared and declared[source].get('type') == 'array' and (source not in result):
                result[source] = []
        return result

    def received_form_references(self, context, form, schema, operation_key):
        from gene_annotation_episode.episodic_workflow.root.a108.library.literature_sheet_updates import current_sheet_refs
        references = current_sheet_refs(self.services.workflow.store, context)
        for namespace, _, _, repository in self._population_routes():
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == namespace for row in form[name]]
            if cells:
                repository().receive_cells(context, cells, operation_key)
            references.extend(repository().cell_record_refs(cells))
        return list(dict.fromkeys(references))

    def received_evidence_tokens(self, context):
        from gene_annotation_episode.episodic_workflow.root.method_loop.durable import content_digest
        tokens = []
        for namespace, _, _, repository in self._population_routes():
            tokens.extend(('received_cell:' + namespace + ':' + content_digest(cell) for cell in repository().received_cells(context)))
        return list(dict.fromkeys(tokens))

    def validate_received_report(self, context, form, schema):
        from gene_annotation_episode.episodic_workflow.root.a108.sample_context_evidence.published_evidence_assessment.evidence_search_strategy_improvement.goal import LEADS
        from gene_annotation_episode.episodic_workflow.root.a108.sample_context_evidence.published_evidence_assessment.evidence_search_strategy_improvement.goal import SCREENING
        from gene_annotation_episode.episodic_workflow.root.a108.sample_context_evidence.published_evidence_assessment.evidence_search_strategy_improvement.credit import lead_dispositions
        from gene_annotation_episode.episodic_workflow.root.a108.sample_context_evidence.published_evidence_assessment.evidence_search_strategy_improvement.credit import screening_answers
        task = context.assignment.get('literature_task')
        if task is not None:
            for name, node in schema.get('properties', {}).items():
                source = node.get('x-source')
                if source in (LEADS, SCREENING):
                    reader = lead_dispositions if source == LEADS else screening_answers
                    if plain(form[name]) != reader(self.services.workflow.store, context):
                        raise ReportBoundaryError('Literature answer differs from its original saved work', code='literature_task_answer_differs_from_saved', field=name)
        from gene_annotation_episode.episodic_workflow.root.a108.domain import canonical
        for namespace, requested_field, _, repository in self._population_routes():
            for name, node in schema.get('properties', {}).items():
                if node.get('x-source') != namespace:
                    continue
                rows = form[name]
                permitted = set(context.received_record_refs)
                if any((row['sheet_ref'] not in permitted for row in rows)) or set(repository().selected_sheet_refs(context)) - permitted:
                    selection = self.services.record_selection(context)
                    if selection.get('run_id') != context.run_id or selection.get('episode_id') != context.episode_id:
                        raise ReportBoundaryError('Literature return receiver differs', code='a108_context_receiver_mismatch', field=name)
                    permitted.update(selection['known_record_refs'])
                try:
                    reporting = replace(context, received_record_refs=tuple(permitted))
                    repository().validate_fact_values(reporting, rows)
                    requested = context.assignment.get(requested_field, [])
                    if any((row['component'] not in requested for row in rows)):
                        raise ContractError('unrequested_a108_component')
                    owned = repository().available_sheet_refs(reporting)
                    selected = list(dict.fromkeys([*(row['sheet_ref'] for row in rows), *owned]))
                    expected = repository().fact_cells(reporting, selected, components=requested)
                    if canonical(rows) != canonical(expected):
                        raise ContractError('a108_requested_subset_mismatch')
                except ContractError as error:
                    raise ReportBoundaryError(str(error), code=str(error), field=name) from error
