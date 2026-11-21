"""Credit: the leaf's progress in lessening the uncertainty of the commissioned reading. Reading a window resolves whether it
holds the evidence, so half the credit is the coverage, the share of the commission's windows read (distinct windows: the
standing records ``record_refs``, one per window, over ``windows_total``, ``messages/internal_summary.py``; a re-extraction of
the last window past the end adds no coverage), and half is the share of the asked fields the held leaf records of all the
windows newly state (the library's ``literature_leaf_extraction.newly_stated_share`` over ``field_counts``: a field counts
once, at the first record that states it). Never clamped or rescaled; each half is at most 1, so the credit is at most 1. The
page's row resolution change stays the authoritative credit."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_leaf_extraction import (
    newly_stated_share)


def coverage(summary):
    """The share of the commission's distinct windows read: one standing record per window read."""
    return len(summary['record_refs']) / summary['windows_total']


def credit(summary, records):
    return 0.5 * coverage(summary) + 0.5 * newly_stated_share(summary['counts'])


def ceiling(summary, records, action_type, arguments, ctx):
    """The most the credit can rise if ``action_type`` is the next unit: the credit never exceeds 1 (each half is a share), so
    an ``extract`` (of the next window) can add at most what is not yet earned (1 - credit, no less than 0) whatever its
    arguments; any other action type is not offered and cannot earn: 0."""
    if action_type != 'extract':
        return 0.0
    return max(0.0, 1.0 - credit(summary, records))
