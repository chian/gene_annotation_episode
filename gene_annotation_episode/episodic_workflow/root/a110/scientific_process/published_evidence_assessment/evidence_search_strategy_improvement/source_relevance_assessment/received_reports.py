"""Private A110 received reports."""
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
        from gene_annotation_episode.episodic_workflow.root.a110.library.reaction_native_observations import NAMESPACE
        native = self.literature_reaction_repository().native_observations_projection().received_rows(context)
        if native:
            result[NAMESPACE] = native
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
        references = []
        for namespace, _, _, _, repository in self._population_routes():
            cells = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == namespace for row in form[name]]
            if cells:
                repository().receive_cells(context, cells, operation_key)
        from gene_annotation_episode.episodic_workflow.root.a110.literature_sheet_updates import current_sheet_refs
        references.extend(current_sheet_refs(self.services.workflow.store, context))
        from gene_annotation_episode.episodic_workflow.root.a110.library.reaction_native_observations import NAMESPACE, native_row_references
        native = [row for name, node in schema.get('properties', {}).items() if node.get('x-source') == NAMESPACE for row in form[name]]
        if native:
            self.literature_reaction_repository().native_observations_projection().receive_rows(context, native, operation_key)
            references.extend(native_row_references(native))
        return list(dict.fromkeys(references))

    def received_evidence_tokens(self, context):
        from gene_annotation_episode.episodic_workflow.root.a110.method_loop.durable import content_digest
        tokens = []
        for namespace, _, _, _, repository in self._population_routes():
            tokens.extend(('received_cell:' + namespace + ':' + content_digest(cell) for cell in repository().received_cells(context)))
        from gene_annotation_episode.episodic_workflow.root.a110.library.reaction_native_observations import NAMESPACE
        tokens.extend(('received_cell:' + NAMESPACE + ':' + content_digest(cell) for cell in self.literature_reaction_repository().native_observations_projection().received_rows(context)))
        return list(dict.fromkeys(tokens))

    def validate_received_report(self, context, form, schema):
        from gene_annotation_episode.episodic_workflow.root.a110.library.reaction_native_observations import NAMESPACE, POSITIONS_FIELD
        requested_sources = {node.get('x-source') for node in schema.get('properties', {}).values() if node.get('x-source')}
        for namespace, requested_field, _, _, repository in self._population_routes():
            for name, node in schema.get('properties', {}).items():
                if node.get('x-source') != namespace:
                    continue
                rows = form[name]
                permitted = set(context.received_record_refs)
                if any((row['sheet_ref'] not in permitted for row in rows)):
                    selection = self.services.record_selection(context)
                    if selection.get('run_id') != context.run_id or selection.get('episode_id') != context.episode_id:
                        raise ReportBoundaryError('Literature return receiver differs', code='literature_reaction_receiver_mismatch', field=name)
                    permitted.update(selection['known_record_refs'])
                try:
                    reporting = replace(context, received_record_refs=tuple(permitted))
                    if not rows and context.assignment.get(requested_field) not in ([], ()):
                        other = 'literature_reaction_semantic_cells' if namespace == 'literature_reaction_cells' else 'literature_reaction_cells'
                        companion = any((other_node.get('x-source') == other and bool(form[other_name]) for other_name, other_node in schema.get('properties', {}).items()))
                        if not companion:
                            repository().validate_empty_return_family(context)
                    repository().validate_fact_values(reporting, rows)
                    requested = context.assignment.get(requested_field)
                    if requested is not None and any((row['component'] not in requested for row in rows)):
                        raise ContractError('unrequested_literature_reaction_component')
                except ContractError as error:
                    raise ReportBoundaryError(str(error), code=str(error), field=name) from error
        if NAMESPACE in requested_sources:
            adapter = self.literature_reaction_repository().native_observations_projection()
            for name, node in schema.get('properties', {}).items():
                if node.get('x-source') != NAMESPACE:
                    continue
                rows = form[name]
                permitted = set(context.received_record_refs)
                if any((row['sheet_ref'] not in permitted for row in rows)):
                    selection = self.services.record_selection(context)
                    if selection.get('run_id') != context.run_id or selection.get('episode_id') != context.episode_id:
                        raise ReportBoundaryError('Literature return receiver differs', code='literature_reaction_native_receiver_mismatch', field=name)
                    permitted.update(selection['known_record_refs'])
                try:
                    adapter.validate_fact_rows(replace(context, received_record_refs=tuple(permitted)), rows)
                    requested = adapter._positions(context.assignment.get(POSITIONS_FIELD, ['all']))
                    if requested != ('all',) and any((row['observation_position'] not in requested for row in rows)):
                        raise ContractError('unrequested_literature_reaction_native_observation')
                except ContractError as error:
                    raise ReportBoundaryError(str(error), code=str(error), field=name) from error
