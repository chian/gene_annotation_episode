"""Private A103 literature_strategy source references."""
from __future__ import annotations
from .source_contracts import ContractError, reference_in_context

class SourceReferences:

    def _require(self, reference, scope, namespace=None):
        if not self.services.reference_in_scope(reference, scope, namespace):
            raise ContractError('literature_reference_unavailable', detail={'reference': reference, 'namespace': namespace})
        return self.services.read_record(reference)

    def resolve(self, context, reference, namespace):
        self._role(context.role)
        return reference_in_context(self.services, context, reference, namespace)
