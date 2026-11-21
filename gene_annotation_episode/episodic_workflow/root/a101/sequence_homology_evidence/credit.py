"""Credit: the owner's differential credit over the candidate annotations the head holds evidence for (2026-11-20).

``credit(summary, records)`` is ``candidate_table(...)['credit']`` (library: ``grading/sequence_homology_evidence/
candidate_measurements.py``, which reads the held graded sources in the order the head obtained them and calls
``differential_credit``): a candidate annotation with positive evidence is admitted and earns its score; applying a
test the candidates already on the list have all undergone earns the sizes of the differences of their moves; a
repeat changes nothing, so it earns nothing. The sum has no fixed maximum, so the credit's controller is the
accumulation controller (``yield_estimator.py``); ``A101DifferentialCredit`` is its definition record.

``A101SequenceCredit`` is no longer the credit. It stays as the reader of the residue-similarity index of the
target (``read_details``: the private copy of the old ``native_correspondence_credit.py`` projector, over the
library's ``NativeCorrespondenceScoring``), which the head still reports as a feature of each target
(``axis_findings`` of ``messages/internal_summary.py``). ``read_details`` scores the native BLAST and HMMER gradings
of the received observations inside the scope's target segments and reads only through the custody reader."""
from dataclasses import dataclass

from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_alignment.native_correspondence import (
    NativeCorrespondenceScoring)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.candidate_measurements import (
    candidate_table, held_sources)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.scoring import (
    SCALES, VERSION)


@dataclass(frozen=True)
class A101SequenceCredit(NativeCorrespondenceScoring):
    """One deterministic projection for normal actions, details and parents."""
    requires_episode_receipts = True
    requires_known_record_refs = True
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


class A101DifferentialCredit:
    """The definition record of the head's credit and its estimator kind."""
    yield_method = 'accumulation'

    def as_record(self):
        return {'kind': 'a101_differential_credit', 'version': 'a101_differential_credit_v1', 'axis': 'A101',
                'measurement': 'subscore_of_one_references_alignments_over_the_scope_regions',
                'subscore_version': VERSION,
                'candidates': 'product_from_database_search_functions_profile_family_reference_sequence',
                'test': 'one_graded_source_kind_with_its_program_and_database',
                'score': 'mean_over_tests_of_mean_value_in_test',
                'admission': 'first_value_above_zero',
                'entry': 'score_after_the_admitting_test_only',
                'differential': 'abs_difference_of_score_moves_of_two_listed_candidates_in_a_test_both_underwent',
                'credit': 'sum_of_entry_scores_and_differentials', 'maximum': 'none',
                'repeat': 'earns_nothing'}


def held_candidate_table(summary, records):
    """The table of candidates of the records this episode holds over the commissioned scope."""
    return candidate_table(records, summary['scope'], held_sources(records))


def credit(summary, records):
    """The differential credit of the held graded sources over the commissioned scope: counted as soon as a graded
    sheet is held. No assessment or reasoning commit switches it on or off, and no model step stands between a graded
    result and its being counted. A child's credit is information in the summary and is never added."""
    return held_candidate_table(summary, records)['credit']
