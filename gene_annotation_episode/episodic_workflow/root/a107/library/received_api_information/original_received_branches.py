"""Single original A107 API receiving branches; callers retain their actual owner/state."""
from copy import deepcopy
from ...communication import plain

def _forwards_bvbrc_reports(self, role):
    return role in {'annotation', 'partner_presence_evidence'} and self.api_execution is not None and any((service.service == 'bvbrc_data' for service in self.api_execution.services.values()))

def _forwards_minhash_reports(self, role):
    return role in {'annotation', 'partner_presence_evidence'} and self.api_execution is not None and any((service.service == 'bvbrc_minhash' for service in self.api_execution.services.values()))

def received_report_sources_branch_0(self, role, result):
    if _forwards_bvbrc_reports(self, role):
        from gene_annotation_episode.episodic_workflow.root.a107.bvbrc_data_views import bvbrc_data_fact_sources
        result.update(bvbrc_data_fact_sources())

def received_report_sources_branch_1(self, role, result):
    if _forwards_minhash_reports(self, role):
        from gene_annotation_episode.episodic_workflow.root.a107.bvbrc_minhash_views import minhash_fact_sources
        result.update(minhash_fact_sources())

def received_report_facts_branch_0(self, context, schema, result):
    if _forwards_bvbrc_reports(self, context.role):
        result.update(self.api_execution.bvbrc_data.received_facts(context, schema))

def received_report_facts_branch_1(self, context, schema, result):
    if _forwards_minhash_reports(self, context.role):
        result.update(self.api_execution.minhash.received_facts(context, schema))

def resolve_received_reference_branch_0(self, context, reference, namespace):
    if _forwards_bvbrc_reports(self, context.role):
        resolved = self.api_execution.bvbrc_data.resolve_received(context, reference, namespace)
        if resolved is not None:
            return resolved

def resolve_received_reference_branch_1(self, context, reference, namespace):
    if _forwards_minhash_reports(self, context.role):
        resolved = self.api_execution.minhash.resolve_received(context, reference, namespace)
        if resolved is not None:
            return resolved

def validate_received_report_branch_0(self, context, form, schema):
    if _forwards_bvbrc_reports(self, context.role):
        self.api_execution.bvbrc_data.validate_received_report(context, form, schema)

def validate_received_report_branch_1(self, context, form, schema):
    if _forwards_minhash_reports(self, context.role):
        self.api_execution.minhash.validate_received_report(context, form, schema)

def received_form_references_branch_0(self, context, form, schema, operation_key, references):
    references.extend(self.api_execution.record_bvbrc_admission(context, form, schema, operation_key))

def received_form_references_branch_1(self, context, form, schema, operation_key, references):
    references.extend(self.api_execution.minhash.record_admission(context, form, schema, operation_key))

def initial_minhash_information_branch_0(self, context, value):
    if _forwards_minhash_reports(self, context.role):
        value['received_minhash_values'] = self.api_execution.minhash.received_context(context)
