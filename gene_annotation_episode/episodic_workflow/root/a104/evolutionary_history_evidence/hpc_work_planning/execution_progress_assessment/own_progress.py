"""ReceivedProgress"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a104.domain import ContractError
from .progress_records import _unique

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
