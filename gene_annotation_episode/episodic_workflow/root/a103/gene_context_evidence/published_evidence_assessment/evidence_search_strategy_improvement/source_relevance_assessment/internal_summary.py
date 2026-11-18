"""Private A103 literature_search internal summary."""
from __future__ import annotations
from .source_contracts import _ACQUISITION_TOOLS, _READ_TOOLS, plain

class SourceInvestigationSummary:

    def initial_decision_context(self, context):
        return {}

    def decision_context(self, context, current_view):
        assignment = self._validate_assignment('literature_search', context.assignment, context.scope, context=context)
        sources = assignment.get('source_refs', [])
        custody = []
        for reference in sources:
            source = self._require(reference, context.scope, 'source')
            custody.append({'source_ref': reference, **{key: source.get(key) for key in ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref', 'parent_source_refs')}})
        return {'literature_assignment': assignment, 'literature_source_custody': custody, 'own_literature_outcomes': plain(self.services.own_outcomes(context.episode_id, tools=(*_ACQUISITION_TOOLS, *_READ_TOOLS), offset=0, limit=self.outcome_page_size)), 'literature_history_meaning': 'Read exact prior outcomes through episode.history; source discovery alone is not A103 evidence.'}
