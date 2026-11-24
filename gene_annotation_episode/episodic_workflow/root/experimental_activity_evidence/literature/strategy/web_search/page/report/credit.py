"""Credit: the leaf's own progress, the share of the asked fields the held leaf records of all the windows newly state (the
library's ``literature_leaf_extraction.newly_stated_share`` over ``field_counts``: a field counts once, at the first record
that states it). Reading a window earns nothing by itself (owner, 2026-11-21: credit comes from filling out the grading
sheet and nothing else). Never clamped or rescaled. The page's row resolution change stays the authoritative credit."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_leaf_extraction import (
    newly_stated_share)


def credit(summary, records):
    return newly_stated_share(summary['counts'])


def ceiling(summary, records, action_type, arguments, ctx):
    """The most the credit can rise if ``action_type`` is the next unit: the share never exceeds 1, so an ``extract`` (of the
    next window) can add at most what is not yet earned (1 - credit, no less than 0) whatever its arguments; any other action
    type is not offered and cannot earn: 0."""
    if action_type != 'extract':
        return 0.0
    return max(0.0, 1.0 - credit(summary, records))
