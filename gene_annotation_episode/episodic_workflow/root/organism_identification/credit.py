"""The credit and the ceilings of the organism identification head.

The credit is the taxon credit of the graded classification sheets this episode holds over the commissioned scope
(``taxon_candidates.taxon_table``): the entries of the candidate taxa and the differentials of the two leading rivals,
counted as soon as a graded sheet is held. No model step stands between a graded result and its being counted. The
candidate's score is not the credit: the score is how well a candidate taxon is supported, the credit is what this
episode gained."""
import json
from pathlib import Path

from gene_annotation_episode.episodic_workflow.episode_support.grading.taxonomic_classification.genomad_grader import (
    CELLULAR, VIRUSES)
from gene_annotation_episode.episodic_workflow.episode_support.grading.taxonomic_classification.taxon_candidates import (
    SHEET_WEIGHT, held_sources, taxon_table, test_ceiling)
from gene_annotation_episode.episodic_workflow.episode_support.tools.taxonomic_classification.kraken2_classification import (
    QUERY_MOLECULES)

KRAKEN2_TOOL, GENOMAD_TOOL, VITAP_TOOL = 'kraken2_classify', 'genomad_classify', 'vitap_assign'
# The tools that run once for a sequence, each with the setting that names its database's manifest, the sheet its grading
# is read as (the name before the database's own, which the manifest gives) and the top taxa its database can speak of.
ONCE_TOOLS = {GENOMAD_TOOL: {'setting': 'genomad_database', 'sheet': 'genomad:', 'names': 'version',
                             'covers': [VIRUSES, CELLULAR]},
              VITAP_TOOL: {'setting': 'vitap_database', 'sheet': 'vitap:', 'names': 'name', 'covers': [VIRUSES]}}
KRAKEN2_SHEET = 'kraken2:'


class TaxonDifferentialCredit:
    """The definition record of the head's credit and its estimator kind."""
    yield_method = 'forecast'

    def as_record(self):
        return {'kind': 'taxon_differential_credit', 'episode': 'organism_identification',
                'candidates': 'taxon_that_a_graded_classification_called_with_support_of_its_own',
                'test': 'one_graded_sheet_of_one_sequence_from_one_tool_and_database',
                'bits': {'kraken2': 'share_of_the_sequences_kmers_the_index_maps_to_the_taxon_itself',
                         'genomad': 'chromosome_plus_plasmid_score_at_cellular_organisms_virus_score_at_the_genes_lineage_by_agreement_rest_at_viruses',
                         'vitap': 'lineage_score_over_one_plus_the_sum_of_the_taken_lineages_scores_at_the_finest_resolved_taxon'},
                'value': 'sum_of_the_tests_bits_along_the_candidates_lineage',
                'sheet_weights': dict(SHEET_WEIGHT),
                'score': 'sum_over_tests_of_sheet_weight_times_value',
                'nesting': 'a_taxon_and_its_ancestor_are_never_rivals_rivals_are_not_on_one_lineage',
                'measurable': 'the_tests_database_holds_the_candidates_part_of_the_taxonomy',
                'admission': 'first_bit_of_its_own_above_zero',
                'entry': 'new_possibility_its_score_finer_under_listed_what_it_adds_vaguer_above_listed_nothing',
                'differential': 'abs_difference_of_the_moves_of_the_two_leading_rivals_listed_before_the_test_that_it_can_measure',
                'claims': 'search_hit_taxa_placed_on_the_prepared_taxonomy_add_to_candidates_that_are_or_lie_inside_them_never_admit',
                'claim_bit': 'closeness_of_the_taxons_best_hit_times_share_of_the_searched_sequence_covered_divided_by_the_searchs_sum_above_one',
                'waiting': 'finer_than_a_listed_candidate_on_its_lineage_half_its_weighted_bit_once_off_lineage_or_not_in_taxonomy_nothing',
                'claim_in_entry': 'weighted_bit_less_what_it_earned_at_most_once',
                'credit': 'sum_of_entries_differentials_and_waiting_halves', 'maximum': 'none', 'repeat': 'earns_nothing'}


def held_table(summary, records):
    """The scoring sheet of the scope from the records this episode holds: its classifications and the taxon claims
    passed in (``evidence_refs``), whose taxa were placed on the prepared taxonomy when their sheets were made; with no
    claim test held the table is as before."""
    return taxon_table(records, summary['scope'], held_sources(records))


def credit(summary, records):
    """The taxon credit of the held graded sheets over the commissioned scope."""
    return held_table(summary, records)['credit']


def made(summary, tool):
    """What this episode holds (``completed``) or saw fail (``failed``) of ``tool``, as its request check reads it: by
    (query, index) for ``kraken2_classify``, by query for a tool that runs once for a sequence."""
    key = (lambda row: (row['query_ref'], row['index'])) if tool == KRAKEN2_TOOL else (lambda row: row['query_ref'])
    done = {key(row['request']): 'failed' for row in summary['units'] if row['tool'] == tool and row['status'] != 'completed'}
    done.update({key(row): 'completed' for row in summary['held_runs'] if row['tool'] == tool})
    return done


def index_manifests(ctx):
    """``{index name: its manifest}`` of the Kraken 2 indexes the run's settings name (``kraken2_indexes``)."""
    return {name: json.loads(Path(path).read_text()) for name, path in ctx.settings.get('kraken2_indexes', {}).items()}


def database_manifest(ctx, tool):
    """The manifest of the database of a tool that runs once for a sequence, or ``None`` when the run's settings name none."""
    path = ctx.settings.get(ONCE_TOOLS[tool]['setting'])
    return None if path is None else json.loads(Path(path).read_text())


def dna_subjects(summary):
    return [ref for ref in summary['scope']['subject_refs'] if summary['held_sequences'].get(ref) in QUERY_MOLECULES]


def ceilings(summary, records, action_type, ctx):
    """``{request key: ceiling}`` of every run of ``action_type`` not yet made on a DNA sequence of the scope: the test
    ceiling of that run's sheet from the sequence's table (``taxon_candidates.test_ceiling``). The key is (query, index)
    for ``kraken2_classify`` and the query for a tool that runs once for a sequence."""
    table, done = held_table(summary, records), made(summary, action_type)
    if action_type == KRAKEN2_TOOL:
        return {(query, index): test_ceiling(table['targets'][query], KRAKEN2_SHEET + index, manifest['covers_taxon_ids'])
                for query in dna_subjects(summary) for index, manifest in index_manifests(ctx).items()
                if (query, index) not in done}
    spec, manifest = ONCE_TOOLS[action_type], database_manifest(ctx, action_type)
    if manifest is None:
        return {}
    return {query: test_ceiling(table['targets'][query], spec['sheet'] + manifest[spec['names']], spec['covers'])
            for query in dna_subjects(summary) if query not in done}


# What ``ceiling`` means for each action type the head offers. The forecast controller learns each action's share of its
# ceiling only from ledger rows recorded under the same credit definition and the same name of that action's ceiling
# (``yield_estimator.py``). Every offered action has one.
CEILINGS = {KRAKEN2_TOOL: 'organism_identification_ceiling', GENOMAD_TOOL: 'organism_identification_ceiling',
            VITAP_TOOL: 'organism_identification_ceiling'}


def ceiling(summary, records, action_type, arguments, ctx):
    """The most the head's credit can rise if the action ``action_type`` with ``arguments`` is the next unit.

    Every action is one new test of one sheet on one sequence. The bits of one test sum to at most 1, so its entries are at
    most the sheet's weight and its one differential at most the weight, the differential only with two listed rivals the
    tool's database can measure (the proof is in ``taxon_candidates.test_ceiling``). A run already held or already failed
    is refused by the request check and earns nothing: 0. With no arguments: the largest over the runs not yet made, 0 when
    none is left."""
    if action_type not in CEILINGS:
        raise ValueError('organism_identification_ceiling_of_unknown_action:' + str(action_type))
    found = ceilings(summary, records, action_type, ctx)
    if arguments is None:
        return max(found.values(), default=0.0)
    key = (arguments['query_ref'], arguments['index']) if action_type == KRAKEN2_TOOL else arguments['query_ref']
    return found.get(key, 0.0)


def best_arguments(summary, records, action_type, ctx):
    """The request of the run with the largest ceiling (the first by its key on a tie), without the resource (the model's
    choice among the local resources), or ``None`` when none is left."""
    found = ceilings(summary, records, action_type, ctx)
    if not found:
        return None
    key = min(found, key=lambda item: (-found[item], item))
    return {'query_ref': key[0], 'index': key[1]} if action_type == KRAKEN2_TOOL else {'query_ref': key}
