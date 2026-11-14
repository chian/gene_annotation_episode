"""Original A107 API receiving behavior; no episode task or credit selection."""
from copy import deepcopy
from ...communication import plain
from ...api_service_execution import APIServiceExecution

class ReceivedAPIReports:

    def __init__(self, api_execution):
        if api_execution is not None and type(api_execution) is not APIServiceExecution:
            raise TypeError('actual_a107_api_reader_required')
        self.api_execution = api_execution

    def _forwards_bvbrc_reports(self, role):
        return _forwards_bvbrc_reports(self, role)

    def _forwards_minhash_reports(self, role):
        return _forwards_minhash_reports(self, role)

    def initial_minhash_information(self, context):
        value = {}
        initial_minhash_information_branch_0(self, context, value)
        return value

    def received_report_sources(self, role):
        result = {}
        received_report_sources_branch_0(self, role, result)
        received_report_sources_branch_1(self, role, result)
        return result

    def received_report_facts(self, context):
        schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
        result = {}
        received_report_facts_branch_0(self, context, schema, result)
        received_report_facts_branch_1(self, context, schema, result)
        return result

    def resolve_received_reference(self, context, reference, namespace):
        _original_api_branch_resolution = resolve_received_reference_branch_0(self, context, reference, namespace)
        if _original_api_branch_resolution is not None:
            return _original_api_branch_resolution
        _original_api_branch_resolution = resolve_received_reference_branch_1(self, context, reference, namespace)
        if _original_api_branch_resolution is not None:
            return _original_api_branch_resolution
        return None

    def validate_received_report(self, context, form, schema):
        validate_received_report_branch_0(self, context, form, schema)
        validate_received_report_branch_1(self, context, form, schema)

    def received_form_references(self, context, form, schema, operation_key):
        references = []
        if self.api_execution is not None:
            received_form_references_branch_0(self, context, form, schema, operation_key, references)
            received_form_references_branch_1(self, context, form, schema, operation_key, references)
        return list(dict.fromkeys(references))
from .original_received_branches import _forwards_bvbrc_reports, _forwards_minhash_reports, received_report_sources_branch_0, received_report_sources_branch_1, received_report_facts_branch_0, received_report_facts_branch_1, resolve_received_reference_branch_0, resolve_received_reference_branch_1, validate_received_report_branch_0, validate_received_report_branch_1, received_form_references_branch_0, received_form_references_branch_1, initial_minhash_information_branch_0
