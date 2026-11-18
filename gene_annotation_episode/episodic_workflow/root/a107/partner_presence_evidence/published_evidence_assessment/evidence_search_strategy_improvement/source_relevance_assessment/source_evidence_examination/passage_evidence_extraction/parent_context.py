"""Private A107 parent context."""
from __future__ import annotations
from .contracts import ContractError, ROLES, _population_catalog

class LiteratureParentContext:

    def initial_decision_context(self, context):
        if self.reference_parent_sources is None or context.role != 'annotation' or len(context.path) != 1:
            return {}
        custody = []
        for reference in self.reference_parent_sources:
            if reference not in context.received_record_refs:
                raise ContractError('literature_parent_source_not_received')
            source = self._require(reference, context.scope, 'source')
            custody.append({'source_ref': reference, **{name: source.get(name) for name in ('artifact_ref', 'text_ref', 'version', 'parent_source_refs')}})
        return {'reference_evidence_parent': {'version': 'reference_evidence_parent_v1', 'source_refs': list(self.reference_parent_sources), 'source_custody': custody, 'child_population_operations': [{name: entry[name] for name in ('name', 'description')} for entry in _population_catalog()]}, 'literature_experimental_work': {'version': 'literature_experimental_task_v1', 'aspect': 'reference_evidence_parent'}, **self._population_task_context(context)}

    def contract_information_profile(self, context):
        if context.role in ROLES or (context.role == 'annotation' and len(context.path) == 1 and (self.reference_parent_sources is not None)):
            return self._contract_information_profile
        return None
