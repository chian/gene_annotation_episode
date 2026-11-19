"""Original A101 native correspondence progress binding."""
from __future__ import annotations
from dataclasses import dataclass
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.scoring import VERSION, SCALES
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_alignment.native_correspondence import NativeCorrespondenceScoring

@dataclass(frozen=True)
class A101SequenceCredit(NativeCorrespondenceScoring):
    """One deterministic projection for normal actions, details and parents."""
    requires_episode_receipts = True
    requires_known_record_refs = True
    yield_method = 'bounded_quality'
    native_score_maximum = 1.0

    def as_record(self):
        return {'kind': 'a101_native_sequence_correspondence', 'version': VERSION, 'axis': 'A101', 'sheet': 'convention_015_native_correspondence', 'supported_algorithms': ['blastp', 'phmmer', 'hmmsearch', 'hmmscan'], 'inverse_bit_scales': dict(SCALES), 'receipt': 'explicit_known_record_refs', 'target_aggregation': 'supplied_scope_length_weighted_mean', 'function_specific_support': 'separate_unknown_without_grounded_inputs', 'interpretation': 'dimensionless_native_correspondence_not_function_probability', 'duplicate_handling': 'per_position_max_not_sum_of_hits_or_assertions'}

    def __call__(self, store, scope, *, known_record_refs, assignment=None, episode_id=None, run_id=None):
        return self.read_details(store, scope, known_record_refs=known_record_refs, assignment=assignment, episode_id=episode_id, run_id=run_id, details_limit=0, details_offset=0)
