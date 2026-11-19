"""Credit: the A101 native sequence-correspondence credit over the records this episode holds.

Carried from the old ``credit.py`` (``credit_view`` -> ``services.scientific_credit``), which projected the axis's
``A101SequenceCredit`` (``native_correspondence_credit.py`` of the axis head, read at 97308b94c). This is a private
copy of that projector, a thin subclass of the library's ``NativeCorrespondenceScoring``, called with this
episode's own scope and the references it holds. The scalar is the sheet's native correspondence component; it is
never bounded, clamped or rescaled here (the declared native maximum is the yield controller's maximum, kept in
``yield_estimator.py``).

The library's ``read_details`` reads only through the custody reader (``records``): the held sources, their
retained gradings and the declared search rows (``native_correspondence.SEARCHES``).
"""
from dataclasses import dataclass

from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_alignment.native_correspondence import (
    NativeCorrespondenceScoring)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.scoring import (
    SCALES, VERSION)

NATIVE_SCORE_MAXIMUM = 1.0


@dataclass(frozen=True)
class A101SequenceCredit(NativeCorrespondenceScoring):
    """One deterministic projection of the held native alignment evidence (private copy)."""
    yield_method = 'bounded_quality'
    native_score_maximum = NATIVE_SCORE_MAXIMUM

    def as_record(self):
        return {'kind': 'a101_native_sequence_correspondence', 'version': VERSION, 'axis': 'A101',
                'sheet': 'convention_015_native_correspondence',
                'supported_algorithms': ['blastp', 'phmmer', 'hmmsearch', 'hmmscan'],
                'inverse_bit_scales': dict(SCALES), 'receipt': 'explicit_known_record_refs',
                'target_aggregation': 'supplied_scope_length_weighted_mean',
                'function_specific_support': 'separate_unknown_without_grounded_inputs',
                'interpretation': 'dimensionless_native_correspondence_not_function_probability',
                'duplicate_handling': 'per_position_max_not_sum_of_hits_or_assertions'}


def credit(summary, records):
    """The native correspondence of the target regions of the commission's scope over the held records."""
    view = A101SequenceCredit().read_details(records, summary['scope'], known_record_refs=records.refs(),
                                             details_limit=0, details_offset=0)
    return view['credit']
