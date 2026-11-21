"""How close the sequence a paper's experiment used is to the sequence of the annotation's target (A105, owner 2026-11-21:
"The goal is to find the exact sequence associated with the experimental data so we know how close the real evidence is";
"Measure closeness likely needs pairwise blast to be here"; "No gate").

``subject_closeness`` is a tool call, not an episode: it calls A105's own pairwise BLAST library function
(``pairwise_blast_comparison``) with the two held records, which runs the one comparison on the local resource, grades
the report into the pairwise sheet and stores the graded result through custody (its source, the grading artifact and
its data-product row). Nothing is graded here a second time: the closeness is read from the controlled
features of that graded result (paired identity, paired coverage of each sequence) by one smooth formula.

The unit that calls it (the A105 page's automatic sheet update) declares the service ``job_access`` and holds the settings
``blast_executable_directory`` (the directory that holds the BLAST programs, as A101 names it) and ``blast_resource_id`` (the
bound local resource that runs the program). The query of the comparison is the paper's resolved subject (a ``reference``
record, with the sequence the paper's protein has); the reference of the comparison is the target's input record.

CLOSENESS (gradual, never a step; 1.0 only for the identical full-length sequence, 0.0 only when nothing aligns):

    closeness = identity_term(paired identity) x subject paired coverage x target paired coverage

    identity_term(x) = (S(x) - S(0)) / (S(1) - S(0)),   S(x) = 1 / (1 + exp(-(x - IDENTITY_MIDPOINT) / IDENTITY_WIDTH))

``S`` is a logistic and the rescaling puts it exactly at 0 for identity 0 and at 1 for identity 1, so identical sequences
give exactly 1.0 and the curve has no step anywhere. The paired identity is the identical residue pairs over the aligned
residue pairs (the alignment's own region). The two coverages are the fractions of each sequence that the alignment pairs
(a half-length alignment is half the standing: the experiment then used a part of the target, or the target holds more
than the experiment's protein). Their product is smooth and is 1 only when both sequences are covered."""
import math

from gene_annotation_episode.episodic_workflow.episode_support.tools.experimental_activity_evidence.literature_pairwise_blast import (
    PROGRAM_MOLECULES, pairwise_blast_comparison)

# EXPERT_REVIEW (owner to confirm): the paired identity at which the identity term is one half, 0.40. Reason: enzyme function
# is usually kept above about 40% sequence identity and becomes unreliable below it. Tian and Skolnick 2003 (J Mol Biol
# 333:863) found that pairs above about 40% identity mostly share the first three EC digits, and Rost 2002 (J Mol Biol
# 318:595) found that the full function is conserved much less than assumed below about that identity; both are cited from
# memory and not re-checked. Below roughly 25-30% identity over a long alignment is the "twilight zone" of homology
# (Rost 1999, Protein Eng 12:85, from memory) where a shared fold no longer implies a shared function.
IDENTITY_MIDPOINT = 0.40
# EXPERT_REVIEW (owner to confirm): the width of the logistic of the identity term, 0.12. Reason: with the midpoint at 0.40
# it puts the term at about 0.13 at 20% identity (twilight), about 0.49 at 40%, about 0.84 at 60% (functions of close
# homologues mostly kept) and about 0.99 at 90%, so no identity range is flat or a step. A narrower width approaches a gate,
# which the owner's rule ("No gate") rules out.
IDENTITY_WIDTH = 0.12


def _logistic(identity):
    return 1.0 / (1.0 + math.exp(-(identity - IDENTITY_MIDPOINT) / IDENTITY_WIDTH))


def identity_term(identity):
    """The identity term in 0..1: the logistic of the paired identity rescaled to 0 at identity 0 and 1 at identity 1."""
    low, high = _logistic(0.0), _logistic(1.0)
    return (_logistic(identity) - low) / (high - low)


def closeness_of_features(features):
    """``{'closeness', 'identity', 'query_coverage', 'target_coverage', 'comparison_ref'}`` read from the controlled features
    of one graded pairwise result (``literature_pairwise_grading.grading_features``). A graded result without any aligned residue
    pair has no ``paired_identity`` and is closeness 0.0: nothing aligns."""
    identity = features.get('paired_identity', 0.0)
    query_coverage, target_coverage = features['query_paired_coverage'], features['reference_paired_coverage']
    (comparison_ref,) = features['sheet_refs']
    return {'closeness': identity_term(identity) * query_coverage * target_coverage, 'identity': identity,
            'query_coverage': query_coverage, 'target_coverage': target_coverage, 'comparison_ref': comparison_ref}


class _Comparison:
    """The unit's context with the operation key of one comparison: every other attribute is the unit's own."""

    def __init__(self, ctx, operation_key):
        self._ctx, self.operation_key = ctx, operation_key

    def __getattr__(self, name):
        return getattr(self._ctx, name)


def _program(store, subject_record_ref, target_record_ref):
    """The first BLAST program that compares the subject's molecule (query) with the target's (reference)."""
    queries, references = store.get(subject_record_ref)['molecule'], store.get(target_record_ref)['molecule']
    return next(name for name, (takes, against) in PROGRAM_MOLECULES.items() if queries in takes and references in against)


async def subject_closeness(ctx, *, subject_record_ref, target_record_ref):
    """Compare the resolved subject's reference record (the query) with the target's input record (the reference) by
    pairwise BLAST and return its closeness (see the module). ``ctx`` is the unit's context of an episode that declares the
    service ``job_access`` and holds the settings ``blast_executable_directory`` and ``blast_resource_id``. A comparison
    that did not complete raises with its code: the page does not repair it.

    Each comparison gets its own job: the job's handle derives from the unit's ``operation_key``, and one unit can compare
    several pairs (a name with several candidates), so the pair is part of the key the comparison runs under (only the job
    handle reads it; the store, the services and the settings are the unit's own)."""
    comparison = _Comparison(ctx, f'{ctx.operation_key}/closeness/{subject_record_ref}/{target_record_ref}')
    outcome = await pairwise_blast_comparison(
        comparison, program=_program(ctx.store, subject_record_ref, target_record_ref), query_ref=subject_record_ref,
        reference_ref=target_record_ref, resource_id=ctx.settings['blast_resource_id'],
        executable_directory=ctx.settings['blast_executable_directory'])
    if outcome['status'] != 'completed':
        raise RuntimeError('subject_closeness_comparison_failed: ' + outcome['feedback']['code'])
    return closeness_of_features(outcome['result'])


__all__ = ['IDENTITY_MIDPOINT', 'IDENTITY_WIDTH', 'closeness_of_features', 'identity_term', 'subject_closeness']
