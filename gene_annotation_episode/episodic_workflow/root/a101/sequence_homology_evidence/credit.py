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
import json
from pathlib import Path

from method_loop import UNBOUNDED

from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_alignment.native_correspondence import (
    NativeCorrespondenceScoring)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.candidate_measurements import (
    candidate_standing, candidate_table, held_sources)
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.differential_credit import (
    test_ceiling)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.database_blast_search import (
    HITLIST_RANGE)
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
        return {'kind': 'a101_differential_credit', 'version': 'a101_differential_credit_v2', 'axis': 'A101',
                'measurement': 'subscore_of_one_references_alignments_over_the_scope_regions',
                'subscore_version': VERSION,
                'candidates': 'product_from_database_search_functions_profile_family_reference_sequence',
                'test': 'one_graded_source_kind_with_its_program_and_database',
                'score': 'sum_over_subscoring_sheets_of_sum_of_mean_value_in_test_of_that_kind',
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


BVBRC_HOMOLOGY_SPEC = (Path(__file__).parents[3] / 'episode_support' / 'forms' / 'application_service_specs'
                       / 'original' / 'Homology.json')


def bvbrc_hit_bound():
    """The most hits a BV-BRC Homology search returns: the default of the application's parameter ``blast_max_hits`` in
    the retained application definition (the route sets no other value)."""
    (parameter,) = [item for item in json.loads(BVBRC_HOMOLOGY_SPEC.read_text())['parameters']
                    if item['id'] == 'blast_max_hits']
    return parameter['default']


def ceiling(summary, records, action_type, arguments, ctx):
    """The most the head's credit can rise if the action ``action_type`` with ``arguments`` is the next unit (with
    ``arguments`` ``None``: the most over every arguments the action type can take now).

    The credit is, per target, the sum of the entry scores of the candidates and of the differentials
    (``differential_credit``). A unit adds at most one graded source, which is one test appended after the earlier ones.
    A candidate's score is the sum of its values over the tests, each value in [0, 1], so that test moves a candidate's
    score by its value, between 0 and 1. ``differential_credit.test_ceiling`` then bounds what the one test can add to
    the target's credit: a pair of candidates on the list that the test measures earns at most 1 (the difference of two
    moves in [0, 1]); a candidate the test admits earns its entry, its first score, at most 1, and its pairs earn
    nothing in that test; a test that measures one candidate on the list and admits none earns 0. Per action type:

    * ``reason``: 0. A reasoning commit holds interpretations and writes no graded source, and the credit is read from
      graded sources only (``held_sources``).
    * ``pairwise_blast``: the one test measures one candidate, the reference sequence (``reference_sequence:<ref>``)
      of the target ``query_ref``. With no pair, a candidate already on the list earns 0; one not on the list can be
      admitted for at most 1.
    * ``database_blast``: a search of the target ``query_ref`` that returns at most ``hitlist_size`` hits, each naming
      at most one function (the reference metadata of a hit carries one function), so it measures at most
      ``hitlist_size`` product candidates, any of those on the list or new ones.
    * ``bvbrc_blast``: the same, with the hits bounded by the application's ``blast_max_hits`` default
      (``bvbrc_hit_bound``).
    * ``bvbrc_msa``: the alignment measures only the candidates named (``candidates``, product names) of the target
      ``query_ref``: one measurement each, a fraction of the new distinguishing sites in [0, 1], so at most 1 per pair
      of listed candidates and 1 per candidate it admits.
    * ``bvbrc_metacats``: 0. A MetaCATS report gives no measurement (``candidate_measurements``).
    * ``hmmer_profile_scan``: the scan of the target ``query_ref`` against the profile database ``database`` reports
      each family at most once, so it measures at most as many families as the database holds profiles (``model_count``
      of the manifest the setting ``profile_databases`` names; the family's own reporting threshold only lowers the
      number): at most that many candidates (``profile_family:<accession>``), any on the list or new.
    * ``execute_selected_tool``: ``UNBOUNDED``: a selected registry tool can import a search report of any size and its
      arguments fix no bound on the candidates it measures."""
    if action_type == 'reason' or action_type == 'bvbrc_metacats':
        return 0.0
    scope = summary['scope']
    standing = candidate_standing(records, scope, held_sources(records))
    sequences = [ref for ref in scope['subject_refs'] if ref in summary['held_sequences']]
    queries = sequences if arguments is None else [arguments['query_ref']]

    def products(target):
        return [candidate for candidate in standing.get(target, {}) if candidate.startswith('product:')]
    if action_type == 'pairwise_blast':
        references = list(summary['held_sequences']) if arguments is None else [arguments['reference_ref']]
        return max((test_ceiling(standing.get(query, {}), ['reference_sequence:' + reference])
                    for query in queries for reference in references), default=0.0)
    if action_type in ('database_blast', 'bvbrc_blast'):
        if action_type == 'bvbrc_blast':
            limit = bvbrc_hit_bound()
        else:
            limit = HITLIST_RANGE[1] if arguments is None else arguments['hitlist_size']
        return max((test_ceiling(standing.get(query, {}), products(query), unseen=limit, limit=limit)
                    for query in queries), default=0.0)
    if action_type == 'bvbrc_msa':
        options = ([(item['query_ref'], item['candidates']) for item in summary['msa_options']]
                   if arguments is None else [(arguments['query_ref'], arguments['candidates'])])
        return max((test_ceiling(standing.get(query, {}), ['product:' + name for name in names])
                    for query, names in options), default=0.0)
    if action_type == 'hmmer_profile_scan':
        databases = (ctx.settings['profile_databases'] if arguments is None
                     else {arguments['database']: ctx.settings['profile_databases'][arguments['database']]})
        sizes = [json.loads(Path(path).read_text())['model_count'] for path in databases.values()]
        families = lambda target: [candidate for candidate in standing.get(target, {})
                                   if candidate.startswith('profile_family:')]
        return max((test_ceiling(standing.get(query, {}), families(query), unseen=size, limit=size)
                    for query in queries for size in sizes), default=0.0)
    if action_type == 'execute_selected_tool':
        return UNBOUNDED
    raise ValueError('a101_ceiling_not_derived_for_action_type:' + action_type)
