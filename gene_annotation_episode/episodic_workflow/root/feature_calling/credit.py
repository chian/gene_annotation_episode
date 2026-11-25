"""The credit of the feature calling head.

The credit is the feature credit of the graded sheets this episode holds over the commissioned scope
(``feature_candidates.feature_table``): the entries of the slots (the candidate feature calls), what the claims earned
while no slot included them, and the differentials of the two leading rival slots, counted as soon as a graded sheet is
held. No model step stands between a graded result and its being counted. A slot's score is not the credit: the score is
how well a type at a location is supported (and is part of the scoring of the annotations that belong to that feature),
the credit is what this episode gained.

What a search can still earn has no finite bound that can be stated before it is read: a search can find claims at any
number of places on the sequence. Its ceiling is therefore ``UNBOUNDED``, deliberately, and the forecast controller
forecasts it from what such searches earned before. A search that is already extracted earns nothing if commissioned
again: 0."""
from method_loop import UNBOUNDED

# importing the converter enters its reader and its families' weights into the sheet of feature calls
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_features import blast_claims  # noqa: F401
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_features.feature_candidates import (
    ABOVE, COMPETING, RIVAL_LETTERS, SAME_SHARE, SHEET_WEIGHT, feature_table, held_sources)

from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.blast_search import (
    PROGRAM_UNITS)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence import (
    bvbrc_blast_search as bvbrc)

from .task import DATABASES, PROGRAMS, SEARCH


class FeatureDifferentialCredit:
    """The definition record of the head's credit and its estimator kind."""
    yield_method = 'forecast'

    def as_record(self):
        return {'kind': 'feature_differential_credit', 'episode': 'feature_calling',
                'feature_call': 'a_statement_of_a_feature_with_its_start_and_its_end_type_position_ranges_strand',
                'claim': 'a_statement_that_letters_lie_inside_a_feature_of_a_type_and_reading_with_at_most_one_end',
                'slot': 'the_feature_calls_that_are_the_same_one_type_strands_agree_coding_calls_share_letters_in_one_frame_other_types_share_same_share_of_the_longer_call',
                'same_share': SAME_SHARE,
                'claim_in_slot': 'same_type_strands_agree_letters_wholly_inside_one_version_with_every_end_it_claims_and_in_the_slots_frame',
                'waiting_claim': 'a_claim_no_slot_includes_kept_as_stated_adds_to_no_score',
                'within': 'type_under_the_others_in_the_hierarchy_strands_agree_letters_wholly_inside_and_a_part_of_a_protein_in_its_coding_sequences_frame',
                'types_above': {kind: list(above) for kind, above in ABOVE.items()},
                'test': 'one_graded_sheet_of_one_sequence_from_one_source',
                'score': 'sum_over_tests_of_sheet_weight_times_the_tests_bits_at_the_slots_calls_and_claims_and_at_every_slot_it_is_within',
                'sheet_weights': dict(SHEET_WEIGHT),
                'rivals': 'two_slots_of_a_competing_type_that_share_rival_letters_or_more_and_are_neither_one_slot_nor_nested',
                'competing_types': list(COMPETING), 'rival_letters': RIVAL_LETTERS,
                'rival_is': 'a_competitor_for_letters_not_a_verdict_nothing_is_removed_or_lowered',
                'measurable': 'the_test_can_speak_of_the_slots_kind',
                'settling': 'slots_claims_in_them_and_waiting_claims_follow_from_all_the_records_held_whatever_their_order',
                'counting': 'tests_in_the_order_they_came_over_what_all_held_records_settle',
                'entry': 'new_possibility_its_score_finer_within_listed_what_it_adds_one_that_only_holds_listed_ones_nothing',
                'waiting_credit': 'a_claim_no_slot_called_so_far_includes_earns_its_weighted_bit_when_first_of_its_type_and_reading_on_its_letters_and_that_is_taken_off_the_entry_of_the_slot_it_comes_to_sit_in',
                'differential': 'abs_difference_of_the_moves_of_the_two_leading_rival_slots_listed_before_the_test_that_it_can_measure',
                'credit': 'sum_of_entries_waiting_credits_and_differentials', 'maximum': 'none', 'repeat': 'earns_nothing',
                'can_step_down': 'when_a_later_call_joins_two_slots_the_seconds_entry_is_no_longer_counted'}


def held_table(summary, records):
    """The sheet of the scope from the graded sources this episode holds: those of its own searches, and any graded
    source it was given with the commission. A feature record given without a graded source is shown to the model and
    adds to no score."""
    return feature_table(records, summary['scope'], held_sources(records))


def credit(summary, records):
    """The feature credit of the held graded sheets over the commissioned scope."""
    return held_table(summary, records)['credit']


def _searched(arguments):
    """The (searched sequence, program, database) of a commission of the search child."""
    return (arguments['searched_ref'], arguments['program'], arguments['database'])


def extracted_searches(summary):
    """The (searched sequence, program, database) of the searches whose result this episode holds."""
    return [(search['query_ref'], search['program'], search['database']) for search in summary['searches']
            if search['closed']]


def open_searches(summary):
    """The searches that can still be sent, as (searched sequence, program, database): every held sequence, with every
    program that takes its letters and every database of this head that holds what that program searches, that has not
    been sent yet (no commission of it and no search of it held). Which program takes which letters is the search
    library's own table."""
    sent = {_searched(row['arguments']) for row in summary['units']}
    sent |= {(search['query_ref'], search['program'], search['database']) for search in summary['searches']}
    return [(ref, program, database)
            for ref, letters in summary['held_sequences'].items() if letters in bvbrc.MOLECULE_UNITS
            for program in PROGRAMS if PROGRAM_UNITS[program][0] == bvbrc.MOLECULE_UNITS[letters]
            for database, entry in DATABASES.items() if entry['unit'] == PROGRAM_UNITS[program][1]
            and (ref, program, database) not in sent]


# What ``ceiling`` means for each action type the head offers. The forecast controller learns each action's typical gain
# only from ledger rows recorded under the same credit definition and the same name of that action's ceiling
# (``yield_estimator.py``). Every offered action has one.
CEILINGS = {SEARCH: 'feature_calling_ceiling'}


def ceiling(summary, records, action_type, arguments, ctx):
    """The most the head's credit can rise if the action ``action_type`` with ``arguments`` is the next unit (the
    module's description). With arguments: 0 for a search already extracted, else ``UNBOUNDED``. With no arguments:
    ``UNBOUNDED`` while a search is left running or a search can still be sent (``open_searches``), else 0: every search
    this head can state has been made, nothing more can be earned, and the forecast of 0 lets the episode stop."""
    if action_type not in CEILINGS:
        raise ValueError('feature_calling_ceiling_of_unknown_action:' + str(action_type))
    if arguments is not None:
        return 0.0 if _searched(arguments) in extracted_searches(summary) else UNBOUNDED
    running = any(search['outstanding'] for search in summary['searches'])
    return UNBOUNDED if running or open_searches(summary) else 0.0


def best_arguments(summary, records, action_type, ctx):
    """The commission the ceiling with no arguments stands for: the continuation of a search left running (its own
    commission again, followed to its result), or ``None`` when none is running (a new search: its fields are the
    model's)."""
    running = [search for search in summary['searches'] if search['outstanding']]
    if not running:
        return None
    search = min(running, key=lambda item: item['launched_at'])
    return {'searched_ref': search['query_ref'], 'program': search['program'], 'database': search['database'],
            'resource_id': search['resource_id'], 'until': 'extracted'}


def outcome_pending(summary, records, position):
    """Whether the outcome of unit ``position`` is pending: a commission of the search child that came back with the
    search launched and not extracted. Its rise (nothing is extracted yet) does not measure the search and its seconds
    cover only the launch, so the forecast controller learns from neither; the commission that continues the search is
    the observation."""
    return summary['units'][position]['parked']
