"""Private A102 literature received evidence."""
from __future__ import annotations
from .source_contracts import ContractError, ROLES, ReportBoundaryError, plain, replace

class SourceReceivedEvidence:

    def received_report_sources(self, role):
        return self._rate_fact_sources() if role not in ROLES else {}

    def received_report_facts(self, context):
        if not self.structure_population or context.role in ROLES:
            return {}
        result = {namespace: repository().received_cells(context) for namespace, _, _, _, repository in self._population_routes()}
        return self._complete_requested_received_arrays(context, result)

    def _complete_requested_received_arrays(self, context, result):
        contract = plain(context.request).get('report_contract') or {}
        schema = contract.get('measurements', {}).get('schema', {})
        declared = self.received_report_sources(context.role)
        for node in schema.get('properties', {}).values():
            source = node.get('x-source')
            if source in declared and source not in result:
                result[source] = []
        return result

    def received_form_references(self, context, form, schema, operation_key):
        if not self.structure_population:
            return []
        for namespace, _, _, _, repository in self._population_routes():
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == namespace for row in form[name]]
            if cells:
                repository().receive_cells(context, cells, operation_key)
        from gene_annotation_episode.episodic_workflow.root.a102.literature_sheet_updates import current_sheet_refs
        references = current_sheet_refs(self.services.workflow.store, context)
        return list(dict.fromkeys(references))

    def received_evidence_tokens(self, context):
        if not self.structure_population:
            return []
        from gene_annotation_episode.episodic_workflow.root.a102.method_loop.durable import content_digest
        return list(dict.fromkeys(('received_cell:' + namespace + ':' + content_digest(cell) for namespace, _, _, _, repository in self._population_routes() for cell in repository().received_cells(context))))

    def validate_received_report(self, context, form, schema):
        from gene_annotation_episode.episodic_workflow.root.a102.literature_task_credit import LEADS, SCREENING, lead_dispositions, screening_answers
        task = context.assignment.get('literature_task')
        if task is not None:
            for name, node in schema.get('properties', {}).items():
                source = node.get('x-source')
                if source in (LEADS, SCREENING):
                    reader = lead_dispositions if source == LEADS else screening_answers
                    if plain(form[name]) != reader(self.services.workflow.store, context):
                        raise ReportBoundaryError('Literature answer differs from its saved work', code='literature_task_answer_differs_from_saved', field=name)
        if not self.structure_population:
            return
        for namespace, requested_field, _, defaults, repository in self._population_routes():
            for name, node in schema.get('properties', {}).items():
                if node.get('x-source') != namespace:
                    continue
                rows = form[name]
                permitted = set(context.received_record_refs)
                if any((row['sheet_ref'] not in permitted for row in rows)):
                    selection = self.services.record_selection(context)
                    if selection.get('run_id') != context.run_id or selection.get('episode_id') != context.episode_id:
                        raise ReportBoundaryError('Literature return receiver differs', code='literature_structure_receiver_mismatch', field=name)
                    permitted.update(selection['known_record_refs'])
                try:
                    reporting = replace(context, received_record_refs=tuple(permitted))
                    repository().validate_fact_values(reporting, rows)
                    requested = context.assignment.get(requested_field, defaults)
                    if any((row['component'] not in requested for row in rows)):
                        raise ContractError('unrequested_literature_structure_component')
                except ContractError as error:
                    raise ReportBoundaryError(str(error), code=str(error), field=name) from error
