"""Private A104 received reports."""
from __future__ import annotations
from .contracts import ContractError, ROLES, ReportBoundaryError, plain, replace

from .received_evidence import LiteratureReceivedEvidence

from .received_report_admission import LiteratureReceivedReportAdmission

class LiteratureReceivedReports(LiteratureReceivedReportAdmission, LiteratureReceivedEvidence):

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

