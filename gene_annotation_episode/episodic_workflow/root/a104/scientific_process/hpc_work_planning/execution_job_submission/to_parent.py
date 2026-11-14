"""Private A104 Launch to parent."""
from __future__ import annotations
from .contracts import BLAST_GRADED_RETURN_SCHEMA, BLAST_GRADED_RETURN_SOURCE, LOCAL_FILE_SOURCE_PROVIDER, NATIVE_RESULT_ORIGIN, PracticalReceiptInformation, RESULT_PROVIDER, TerminalExecutionBehavior, deepcopy, obj, plain, validate_form

from .report_fields import LaunchReportFields

from .report_reference_access import LaunchReportReferenceAccess

from .report_facts import LaunchReportFacts

class LaunchReport(LaunchReportFacts, LaunchReportReferenceAccess, LaunchReportFields):

    def validate_report(self, context, form, original_schema):
        self.native_blast_masking_returns.validate_received_report(context, form, original_schema)
        self.native_blast_utility_returns.validate_received_report(context, form, original_schema)
        frozen_facts = None
        if self._has_uniprot():
            from gene_annotation_episode.episodic_workflow.root.a104.uniprot_return_contracts import requested_uniprot_selection
            if requested_uniprot_selection(plain(original_schema)) is not None:
                host = self.api_execution.uniprot_returns
                host.validate_received_report(context, form, original_schema)
                if host._successful_closed(context):
                    frozen_facts = host._closed(context)['facts']
        validate_form(form, original_schema, lambda ref, ns: self.resolve(context, ref, ns))
        fact_fields = {name: declared['x-source'] for name, declared in plain(original_schema).get('properties', {}).items() if declared.get('x-source') is not None}
        if not fact_fields:
            return
        facts = self.facts(context, {}) if frozen_facts is None else frozen_facts
        for name, source in fact_fields.items():
            if source in facts and form[name] != facts[source]:
                raise ValueError('execution_report_disagrees_with_recorded_facts')
