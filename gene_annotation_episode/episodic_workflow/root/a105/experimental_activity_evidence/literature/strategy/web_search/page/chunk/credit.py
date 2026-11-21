"""Credit: the leaf's own progress in lessening uncertainty, the share of the fields the form asked that this Episode's
records newly state (the library's ``literature_leaf_extraction.field_counts`` and ``newly_stated_share``; the field rule is
``literature_identity_extraction.stated_fields``). A field is stated when a held record states it (a quantity or operand
with status 'point', a fact whose answer is neither 'unknown' nor 'not_applicable', a choice that is not None, an asked
identity key that is not None); it is newly stated by the first held record that states it, and a record held twice (the
same ref) is one record. Never bounded, clamped or rescaled. The judgement of the stated fields belongs to the page, never
to this leaf.

The page's row resolution change stays the authoritative credit; this share is only the leaf's own progress."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_leaf_extraction import (
    newly_stated_share)


def credit(summary, records):
    return newly_stated_share(summary['counts'])


def ceiling(summary, records, action_type, arguments, ctx):
    """The most the credit can rise if ``action_type`` with ``arguments`` is taken as the next unit.

    The episode has one action, ``extract``, whatever its arguments: it holds one record of the commissioned experiment type,
    and the credit is newly_stated / asked, the share of the asked fields that the held records state. That share is a
    fraction of the fields the form asked, so it never exceeds 1 (a field is counted once however many records state it, and
    the asked count of a record is at least the fields it states). A new record can therefore raise it only up to 1, so the
    most it can add is what is not yet earned, 1 - credit(summary, records), and no less than 0 once every asked field is
    stated. The bound is the same for every arguments (the answer is the model's, so no argument narrows it). Any other
    action type is not one this episode offers and cannot earn: 0."""
    if action_type != 'extract':
        return 0.0
    return max(0.0, 1.0 - credit(summary, records))
