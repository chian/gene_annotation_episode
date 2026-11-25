"""The credit and the ceilings of the organism identification head.

The credit is the taxon credit of the graded classification sheets this episode holds over the commissioned scope
(``taxon_candidates.taxon_table``): the entries of the candidate taxa and the differentials of the two leading rivals,
counted as soon as a graded sheet is held. No model step stands between a graded result and its being counted. The
candidate's score is not the credit: the score is how well a candidate taxon is supported, the credit is what this
episode gained."""
import json
from pathlib import Path

from gene_annotation_episode.episodic_workflow.episode_support.grading.taxonomic_classification.taxon_candidates import (
    SHEET_WEIGHT, held_sources, taxon_table, test_ceiling)
from gene_annotation_episode.episodic_workflow.episode_support.tools.taxonomic_classification.kraken2_classification import (
    QUERY_MOLECULES)

KRAKEN2_TOOL = 'kraken2_classify'
KRAKEN2_SHEET = 'kraken2:'


class TaxonDifferentialCredit:
    """The definition record of the head's credit and its estimator kind."""
    yield_method = 'forecast'

    def as_record(self):
        return {'kind': 'taxon_differential_credit', 'episode': 'organism_identification',
                'candidates': 'taxon_that_a_graded_classification_called_with_support_of_its_own',
                'test': 'one_graded_classification_sheet_of_one_sequence_against_one_index',
                'bit': 'kraken2_share_of_the_sequences_kmers_the_index_maps_to_the_taxon_itself',
                'value': 'sum_of_the_tests_bits_along_the_candidates_lineage',
                'sheet_weights': dict(SHEET_WEIGHT),
                'score': 'sum_over_tests_of_sheet_weight_times_value',
                'nesting': 'a_taxon_and_its_ancestor_are_never_rivals_rivals_are_not_on_one_lineage',
                'measurable': 'the_tests_database_holds_the_candidates_part_of_the_taxonomy',
                'admission': 'first_bit_of_its_own_above_zero',
                'entry': 'new_possibility_its_score_finer_under_listed_what_it_adds_vaguer_above_listed_nothing',
                'differential': 'abs_difference_of_the_moves_of_the_two_leading_rivals_listed_before_the_test_that_it_can_measure',
                'credit': 'sum_of_entries_and_differentials', 'maximum': 'none', 'repeat': 'earns_nothing'}


def held_table(summary, records):
    """The scoring sheet of the scope from the records this episode holds."""
    return taxon_table(records, summary['scope'], held_sources(records))


def credit(summary, records):
    """The taxon credit of the held graded classifications over the commissioned scope."""
    return held_table(summary, records)['credit']


def made(summary):
    """The classifications this episode holds (``completed``) or saw fail (``failed``), by query and index: what the
    request check refuses to run again."""
    done = {(row['classification']['query_ref'], row['classification']['index']): 'failed'
            for row in summary['units'] if row['tool'] == KRAKEN2_TOOL and row['status'] != 'completed'}
    done.update({(row['query_ref'], row['index']): 'completed' for row in summary['held_classifications']})
    return done


def index_manifests(ctx):
    """``{index name: its manifest}`` of the indexes the run's settings name (``kraken2_indexes``: name to manifest path)."""
    return {name: json.loads(Path(path).read_text()) for name, path in ctx.settings.get('kraken2_indexes', {}).items()}


def kraken2_ceilings(summary, records, ctx):
    """``{(query, index): ceiling}`` of every classification not yet made of a DNA sequence of the scope: the test
    ceiling of the index's sheet from that sequence's table (``taxon_candidates.test_ceiling``)."""
    table, done, manifests = held_table(summary, records), made(summary), index_manifests(ctx)
    return {(query, index): test_ceiling(table['targets'][query], KRAKEN2_SHEET + index, manifest['covers_taxon_ids'])
            for query in summary['scope']['subject_refs'] if summary['held_sequences'].get(query) in QUERY_MOLECULES
            for index, manifest in manifests.items() if (query, index) not in done}


# What ``ceiling`` means for each action type the head offers. The forecast controller learns each action's share of its
# ceiling only from ledger rows recorded under the same credit definition and the same name of that action's ceiling
# (``yield_estimator.py``). Every offered action has one.
CEILINGS = {KRAKEN2_TOOL: 'organism_identification_ceiling'}


def ceiling(summary, records, action_type, arguments, ctx):
    """The most the head's credit can rise if the action ``action_type`` with ``arguments`` is the next unit.

    * ``kraken2_classify``: one new test of the index's sheet on one sequence. Its entries are at most the sheet's weight
      and its one differential at most the weight, the differential only with two listed rivals the index can measure
      (the proof is in ``taxon_candidates.test_ceiling``). A classification already held or already failed is refused by
      the request check and earns nothing: 0. With no arguments: the largest over the classifications not yet made, 0
      when none is left."""
    if action_type != KRAKEN2_TOOL:
        raise ValueError('organism_identification_ceiling_of_unknown_action:' + str(action_type))
    ceilings = kraken2_ceilings(summary, records, ctx)
    if arguments is None:
        return max(ceilings.values(), default=0.0)
    return ceilings.get((arguments['query_ref'], arguments['index']), 0.0)


def best_arguments(summary, records, action_type, ctx):
    """The query and the index of the classification with the largest ceiling (the first by query then index on a tie), or
    ``None`` when none is left. The resource is the model's choice among the local resources."""
    ceilings = kraken2_ceilings(summary, records, ctx)
    if not ceilings:
        return None
    query, index = min(ceilings, key=lambda pair: (-ceilings[pair], pair))
    return {'query_ref': query, 'index': index}
