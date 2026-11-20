"""Credit: A101's native sequence correspondence over the commissioned scope and the records this episode holds.

``A101SequenceCredit`` is the private copy of the old ``native_correspondence_credit.py`` projector (episode file at
97308b94c): a frozen projector over the library's ``NativeCorrespondenceScoring`` (``read_details`` scores the
native BLAST and HMMER gradings of the received observations inside the scope's target segments), its
``as_record()`` credit definition, ``yield_method = 'bounded_quality'`` and ``native_score_maximum = 1.0``.

``credit(summary, records)`` is the old ``credit_view`` over custody: the known record references of the old
receipts ledger are the references this episode holds (``records.refs()``: records passed to it, returned to it or
produced by its units; the rows of declared work tables are not Store records and are not scored). The credit
is the projection's ``credit`` as measured, never bounded or rescaled; a child's credit is information in the
summary and is never added. The old services' ``scientific_credit`` asked a provider nothing this projection
needs. ``NativeCorrespondenceScoring.read_details`` reads only through the custody reader: the held sources,
their retained gradings and the declared search rows (``native_correspondence.SEARCHES``)."""
from dataclasses import dataclass

from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_alignment.native_correspondence import (
    NativeCorrespondenceScoring)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.scoring import (
    SCALES, VERSION)


@dataclass(frozen=True)
class A101SequenceCredit(NativeCorrespondenceScoring):
    """One deterministic projection for normal actions, details and parents."""
    requires_episode_receipts = True
    requires_known_record_refs = True
    yield_method = 'bounded_quality'
    native_score_maximum = 1.0

    def as_record(self):
        return {'kind': 'a101_native_sequence_correspondence', 'version': VERSION, 'axis': 'A101',
                'sheet': 'convention_015_native_correspondence',
                'supported_algorithms': ['blastp', 'phmmer', 'hmmsearch', 'hmmscan'],
                'inverse_bit_scales': dict(SCALES), 'receipt': 'explicit_known_record_refs',
                'target_aggregation': 'supplied_scope_length_weighted_mean',
                'function_specific_support': 'separate_unknown_without_grounded_inputs',
                'interpretation': 'dimensionless_native_correspondence_not_function_probability',
                'duplicate_handling': 'per_position_max_not_sum_of_hits_or_assertions'}

    def __call__(self, store, scope, *, known_record_refs, assignment=None, episode_id=None, run_id=None):
        return self.read_details(store, scope, known_record_refs=known_record_refs, assignment=assignment,
                                 episode_id=episode_id, run_id=run_id, details_limit=0, details_offset=0)


def credit(summary, records):
    """The native-correspondence credit of the held records over the commissioned scope: every graded comparison
    this episode holds counts as soon as its sheet is saved. No assessment or reasoning commit switches it on or
    off: the measure is the correspondence of the scope's sequence with what it was compared with, independent of
    a functional hypothesis (``scoring.py``), so the projection is not given the proposed annotation (given it,
    ``read_details`` scores only the observations an assessment relates to that annotation)."""
    known = [ref for ref in records.refs() if not ref.startswith('row_')]
    return A101SequenceCredit()(records, summary['scope'], known_record_refs=known)['credit']
