from __future__ import annotations
'Private received evidence responsibility for literature.'
from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.source_contracts import ROLES, plain

class LiteratureReceivedEvidence:

    def received_report_sources(self, role):
        return self._rate_fact_sources() if self.rate_population and role not in ROLES else {}

    def received_report_facts(self, context):
        if not self.rate_population or context.role in ROLES:
            return {}
        result = {}
        for namespace, _, _, _, repository in self._population_routes():
            cells = repository().received_cells(context)
            if cells or namespace == 'literature_rate_cells':
                result[namespace] = cells
        if not self.rate_population:
            return self._complete_requested_received_arrays(context, result)
        if self.controlled_response_population:
            cells = self._controlled_response_repository().received_cells(context)
            if cells:
                result['literature_controlled_response_component_cells'] = cells
        if self.gel_population:
            cells = self._gel_repository().received_cells(context)
            if cells:
                result['literature_gel_component_cells'] = cells
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

    def received_evidence_tokens(self, context):
        """Identify validated received component subsets, including zero-value cells.

        A sheet reference alone does not deliver its other components. These
        readers authenticate the original typed delivery before exposing each
        immutable cell; renamed form fields and repeated subsets add no token.
        """
        if not self.rate_population:
            return []
        from gene_annotation_episode.episodic_workflow.root.method_loop.durable import content_digest
        tokens = []

        def include(namespace, cells):
            tokens.extend(('received_cell:' + namespace + ':' + content_digest(cell) for cell in cells))
        for namespace, _, _, _, repository in self._population_routes():
            include(namespace, repository().received_cells(context))
        if self.rate_population:
            if self.controlled_response_population:
                include('literature_controlled_response_component_cells', self._controlled_response_repository().received_cells(context))
            if self.gel_population:
                include('literature_gel_component_cells', self._gel_repository().received_cells(context))
        return list(dict.fromkeys(tokens))
