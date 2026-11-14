from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.library.root_literature_contracts import (Mapping, deepcopy, replace, hashlib, inspect, json, Path, ReportBoundaryError, plain, validate_form, CONTRACT_INFORMATION_PROFILE, ContractError, REF, identity, obj, source_location_inputs, validate_schema, reference_in_context, VERSION, ROLES, _REFERENCES, _REPRESENTATION, _NATURAL, _POSITIVE, _TEXT, _WINDOW, _TABLE, _PAGE, _CHILDREN, EXPERIMENT_DATABASE_TOOLS, _ACCESS_TOOLS, _ACQUISITION_TOOLS, _A108_ACCESS_TOOLS, _A108_ACQUISITION_TOOLS, _A108_NAMESPACES, _READ_TOOLS, _ROLE_INSTRUCTIONS, _a108_population_catalog, _population_catalog)

from .received_record_custody import LiteratureReceivedRecordCustody

from .received_report_admission import LiteratureReceivedReportAdmission

from .foreign_report_projection import LiteratureForeignReportProjection

class LiteratureReceivedEvidence(LiteratureForeignReportProjection, LiteratureReceivedReportAdmission, LiteratureReceivedRecordCustody):
    def received_report_sources(self, role):
        return (self._rate_fact_sources() if (self.rate_population or self.a108_context_evidence) and role not in ROLES else {})

    def received_report_facts(self, context):
        if not (self.rate_population or self.a108_context_evidence) or context.role in ROLES:
            return {}
        return self._received_external_report_facts(context)

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
            if (source in declared and declared[source].get('type') == 'array'
                    and source not in result):
                result[source] = []
        return result

