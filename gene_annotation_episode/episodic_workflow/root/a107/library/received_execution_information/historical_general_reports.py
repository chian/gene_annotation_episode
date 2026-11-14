"""Explicit registry surface; direct owner callbacks retain original API checks."""
from .historical_receiving_owner import HistoricalReceivedExecutionOwner

class HistoricalGeneralReceivedReports:
    def __init__(self, owner):
        if type(owner) is not HistoricalReceivedExecutionOwner:
            raise TypeError('actual_historical_receiving_owner_required')
        self.owner = owner
    def received_report_sources(self, role):
        return self.owner.received_report_sources(role, _include_separate_api=False)
    def received_report_facts(self, context):
        return self.owner.received_report_facts(context, _include_separate_api=False)
    def received_report_closure_facts(self, context):
        return self.owner.received_report_closure_facts(context)
    def resolve_received_reference(self, context, reference, namespace):
        return self.owner.resolve_received_reference(context, reference, namespace, _include_separate_api=False)
    def validate_received_report(self, context, form, schema):
        return self.owner.validate_received_report(context, form, schema, _include_separate_api=False)
    def received_form_references(self, context, form, schema, operation_key):
        return self.owner.received_form_references(context, form, schema, operation_key, _include_separate_api=False)
