"""Explicit public application-return ports and their original custody instance.

An actual private operational owner supplies the seven directional callbacks and
the original API own/received reference selector.
No role, path, adapter availability or runtime request selects an implementation.
"""
from __future__ import annotations
from .bvbrc_application_return_records import BVBRCApplicationReturnRecords


class BVBRCApplicationReturns:
    def __init__(self, execution, *, owner=None):
        self.records = BVBRCApplicationReturnRecords(execution)
        if owner is None:
            from .standalone_application_returns import StandaloneApplicationReturns
            owner = StandaloneApplicationReturns()
        callbacks = (owner._application_facts, owner._application_received_context,
            owner._application_received_facts, owner._application_validate_received_report,
            owner._application_record_admission, owner._application_resolve_own,
            owner._application_resolve_received, owner._application_resolve_reference)
        if not all(callable(callback) for callback in callbacks):
            raise ValueError('bvbrc_application_return_callbacks_required')
        (self._facts, self._received_context, self._received_facts, self._validate_received_report,
            self._record_admission, self._resolve_own, self._resolve_received, self._resolve_reference) = callbacks

    def facts(self, context, schema):
        return self._facts(self, context, schema)

    def received_context(self, context):
        return self._received_context(self, context)

    def received_facts(self, context, schema):
        return self._received_facts(self, context, schema)

    def validate_received_report(self, context, form, schema):
        return self._validate_received_report(self, context, form, schema)

    def record_admission(self, context, form, schema, operation_key):
        return self._record_admission(self, context, form, schema, operation_key)

    def resolve_own(self, context, reference, namespace):
        return self._resolve_own(self, context, reference, namespace)

    def resolve_received(self, context, reference, namespace):
        return self._resolve_received(self, context, reference, namespace)

    def resolve(self, context, reference, namespace):
        return self._resolve_reference(self, context, reference, namespace)
