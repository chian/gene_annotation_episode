"""Private A102 API received records."""
from __future__ import annotations
from .execution_contracts import RESULT_PROVIDER, deepcopy, plain

from .received_record_selection import APIReceivedRecordSelection

from .received_reference_custody import APIReceivedReferenceCustody

class APIReceivedRecords(APIReceivedReferenceCustody, APIReceivedRecordSelection):

    def received_report_sources(self, role):
        if role not in {'annotation', 'scientific_process'}:
            return {}
        from gene_annotation_episode.episodic_workflow.root.a102.protein_structure_result_views import protein_structure_fact_sources
        result = protein_structure_fact_sources()
        for source in ('execution_file_source_refs', 'execution_file_capture_outcomes'):
            definition = self.fact_sources('results').get(source)
            if definition is not None:
                result[source] = deepcopy(definition)
        return result

    def received_report_facts(self, context):
        if context.role not in {'annotation', 'scientific_process'}:
            return {}
        schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
        requested = {node.get('x-source') for node in schema.get('properties', {}).values()}
        result = {}
        if 'execution_file_source_refs' in requested:
            result['execution_file_source_refs'] = self.local_file_sources.received_sources(context)
        if 'execution_file_capture_outcomes' in requested:
            result['execution_file_capture_outcomes'] = self.local_file_sources.received_outcomes(context)
        result.update(self.native_protein_structure_returns.received_facts(context, schema))
        return result

    def received_report_closure_facts(self, context):
        return {}

