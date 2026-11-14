"""ReceivedProgress"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a107.domain import ContractError
from .progress_records import _unique

class ReceivedProgress:

    def _received(self, context):
        value = self._assignment(context.assignment, context.scope)
        selection = getattr(self.services, 'progress_selection', None)
        if callable(selection):
            return _unique(selection(context)['known_progress_refs'])
        return _unique([*value['known_progress_refs'], *self._own_progress_refs(context), *self.services.received_progress_refs(context.episode_id)])

    def _snapshot(self, context, reference):
        if reference not in self._received(context):
            raise ContractError('monitor_progress_not_received')
        return self.services.read_progress(reference, context.scope)

class OwnProgress:

    def _own_progress_refs(self, context):
        refs, offset = ([], 0)
        while True:
            page = self.services.own_outcomes(context.episode_id, tools=None, offset=offset, limit=self.outcome_page_size)
            for row in page['records']:
                refs.extend(row.get('progress_refs', ()))
            if page['next_offset'] is None:
                return _unique(refs)
            offset = page['next_offset']
