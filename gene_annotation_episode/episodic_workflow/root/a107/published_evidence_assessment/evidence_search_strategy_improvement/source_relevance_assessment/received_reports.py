"""Private A107 received reports."""
from __future__ import annotations
from .contracts import ContractError, ROLES, ReportBoundaryError, plain, replace

class LiteratureReceivedReports:

    def received_report_sources(self, role):
        return self._rate_fact_sources() if role not in ROLES else {}

    def received_report_facts(self, context):
        if context.role in ROLES:
            return {}
        result = {}
        for namespace, _, _, _, repository in self._population_routes():
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
        for namespace, _, _, _, repository in self._population_routes():
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == namespace for row in form[name]]
            if cells:
                repository().receive_cells(context, cells, operation_key)
        from gene_annotation_episode.episodic_workflow.root.a107.library.literature_sheet_updates import current_sheet_refs
        return list(dict.fromkeys(current_sheet_refs(self.services.workflow.store, context)))

    def received_evidence_tokens(self, context):
        from gene_annotation_episode.episodic_workflow.root.a107.method_loop.durable import content_digest
        tokens = []
        for namespace, _, _, _, repository in self._population_routes():
            tokens.extend(('received_cell:' + namespace + ':' + content_digest(cell) for cell in repository().received_cells(context)))
        return list(dict.fromkeys(tokens))

    def validate_received_report(self, context, form, schema):
        for namespace, requested_field, _, _, repository in self._population_routes():
            for name, node in schema.get('properties', {}).items():
                if node.get('x-source') != namespace:
                    continue
                rows = form[name]
                permitted = set(context.received_record_refs)
                if any((row['sheet_ref'] not in permitted for row in rows)):
                    selection = self.services.record_selection(context)
                    if selection.get('run_id') != context.run_id or selection.get('episode_id') != context.episode_id:
                        raise ReportBoundaryError('Literature return receiver differs', code='literature_partner_receiver_mismatch', field=name)
                    permitted.update(selection['known_record_refs'])
                try:
                    if not rows and context.assignment.get(requested_field) not in ([], ()):
                        repository().validate_empty_return_family(context)
                    repository().validate_fact_values(replace(context, received_record_refs=tuple(permitted)), rows)
                    requested = context.assignment.get(requested_field)
                    if requested is not None and any((row['component'] not in requested for row in rows)):
                        raise ContractError('unrequested_literature_partner_component')
                except ContractError as error:
                    raise ReportBoundaryError(str(error), code=str(error), field=name) from error
