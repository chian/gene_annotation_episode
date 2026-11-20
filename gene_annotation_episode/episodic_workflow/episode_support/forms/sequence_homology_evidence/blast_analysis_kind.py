"""The analysis kind of a BLAST job: what the search is for, which decides how its result is graded.

A commission declares the kind (a value of ``ANALYSIS_KINDS``) and the kind is derived again from the validated job
itself, from what the job is; the two must agree. Only ``pairwise`` exists: one query sequence against one subject
sequence, whose result says which residues correspond and how many (a database search and an all-versus-all search
are other kinds and are not placed). A job that is not a validated A101 pairwise job has no kind, and a declared kind
that is not the derived one is an error: nothing is repaired and nothing falls back."""
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.blast_pairwise_job import (
    validate_pairwise_requested_job)

ANALYSIS_KINDS = ('pairwise',)


def derived_analysis_kind(requested_job):
    """The kind of the validated job: pairwise when it is a validated A101 pairwise job (exactly one query sequence
    operand and one subject sequence operand, which the contract enforces)."""
    if not isinstance(requested_job, dict) or 'blast_pairwise' not in requested_job:
        raise ValueError('analysis_kind_not_derivable:no_blast_pairwise_job')
    try:
        validate_pairwise_requested_job(requested_job)
    except (TypeError, KeyError, ValueError) as error:
        raise ValueError('analysis_kind_not_derivable:' + str(error)) from error
    return 'pairwise'


def checked_analysis_kind(declared, requested_job):
    """The derived kind of the job, after the declared one is shown to be it."""
    if declared not in ANALYSIS_KINDS:
        raise ValueError('analysis_kind_not_declared_or_unknown:' + repr(declared))
    derived = derived_analysis_kind(requested_job)
    if declared != derived:
        raise ValueError('analysis_kind_conflict:declared:' + declared + ':derived:' + derived)
    return derived


__all__ = ['ANALYSIS_KINDS', 'checked_analysis_kind', 'derived_analysis_kind']
