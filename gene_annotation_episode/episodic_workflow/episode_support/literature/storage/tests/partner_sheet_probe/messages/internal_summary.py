"""The plan, the unit outcomes and the current partner sheets, read through the read-only reader."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.partner_presence_evidence.literature_sheet_updates import current_sheet_refs


def internal_summary(view):
    return {**view.parent_input, 'outcomes': list(view.outcomes), 'steps': len(view.outcomes),
            'current': current_sheet_refs(view.records)}
