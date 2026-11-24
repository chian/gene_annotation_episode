"""Credit: the progress of the reading of the piece, earned by changes in the scores of its parts (never the annotation score
itself: a score is how well a reading is supported, a state recomputed from what is held; credit is what that state gained).

``credit(summary, records)`` is ``part_credit(part_units, readings, rna_scans)`` (library: ``grading/parts_discovery/held_sheets.py``):

    part_units['protein_gene'] x (the highest ``score_sum`` over the gene-finding sheets held, from zero)
    + part_units['rna_gene'] x (the sum of the bit scores of the RNA parts held)

A reading's score is its ``score_sum`` (the sum of the gene finder's own scores of its genes); an RNA gene's score is its bit score.
``part_units`` are the commissioner's two positive numbers that make the two kinds comparable. So the first reading earns its whole
score; a second reading under another genetic code earns only the amount by which it beats the best so far, and a wrong code earns
nothing: the credit and the choice of code agree. A repeat earns nothing. The sum has no fixed maximum; every action the head offers
has a ceiling, so the credit's controller is the forecast controller (``yield_estimator.py``). ``PartsDiscoveryCredit`` is its
definition record."""
from method_loop import UNBOUNDED

from gene_annotation_episode.episodic_workflow.episode_support.grading.parts_discovery.held_sheets import part_credit
from gene_annotation_episode.episodic_workflow.episode_support.tools.parts_discovery.describe_piece import (
    TOOL_NAME as DESCRIBE_TOOL)
from gene_annotation_episode.episodic_workflow.episode_support.tools.parts_discovery.find_genes import (
    TOOL_NAME as FIND_GENES_TOOL, offered_codes as library_offered_codes)
from gene_annotation_episode.episodic_workflow.episode_support.tools.parts_discovery.find_rna_genes import (
    TOOL_NAME as RNA_TOOL)

PART_UNIT_KINDS = ('protein_gene', 'rna_gene')


class PartsDiscoveryCredit:
    """The definition record of the head's credit and its estimator kind. It names the commission's ``part_units``: they set the
    scale of the credit, and the forecast's shares are learned on one scale only."""
    yield_method = 'forecast'

    def __init__(self, part_units):
        self.part_units = dict(part_units)

    def as_record(self):
        return {'kind': 'parts_discovery_credit', 'arm': 'parts', 'part_units': dict(self.part_units),
                'protein_gene_score': 'the_gene_finders_own_score_of_the_call',
                'reading': 'one_gene_finding_sheet_its_score_is_the_sum_of_the_scores_of_its_genes',
                'rna_gene_score': 'the_bit_score_of_the_hit_not_overlapped_by_a_better_hit_of_its_clan',
                'credit': ('part_units_protein_gene_times_the_highest_reading_score_held_from_zero_plus_part_units_rna_gene_times_'
                           'the_sum_of_the_bit_scores_of_the_rna_parts_held'),
                'maximum': 'none', 'repeat': 'earns_nothing'}


def held_codes(summary):
    """The genetic codes of the readings held."""
    return {row['code'] for row in summary['readings']}


def offered_codes(summary):
    """The codes a ``find_genes`` request may name now (``find_genes.offered_codes``)."""
    return library_offered_codes(summary['piece']['length'], held_codes(summary))


def rna_scanned(summary):
    """Whether the piece's RNA scan is held."""
    return bool(summary['rna_scans'])


def credit(summary, records):
    """The credit of the held readings and RNA scan: counted as soon as a graded sheet is held."""
    return part_credit(summary['part_units'], summary['readings'], summary['rna_scans'])


def best_arguments(summary, records, action_type, ctx):
    """The commission that reaches the ceiling asked with ``arguments`` ``None``, as the arguments a decision can name: for
    ``find_genes`` the first code still offered, else ``None``; the other actions take no choice."""
    if action_type != FIND_GENES_TOOL:
        return None
    codes = offered_codes(summary)
    return {'piece_ref': summary['piece']['ref'], 'code': codes[0]} if codes else None


# What ``ceiling`` means for each action type the head offers (the forecast controller learns an action's share of its ceiling only
# from ledger rows recorded under the same credit definition and the same name of that action's ceiling).
CEILINGS = {DESCRIBE_TOOL: 'parts_discovery_ceiling', FIND_GENES_TOOL: 'parts_discovery_ceiling',
            RNA_TOOL: 'parts_discovery_ceiling'}


def ceiling(summary, records, action_type, arguments, ctx):
    """The most the head's credit can rise if the action ``action_type`` with ``arguments`` is the next unit (with ``arguments``
    ``None``: the most over every arguments the action type can take now).

    * ``describe_piece``: composition facts only, no part and no score: 0.
    * ``find_genes``: the credit rises by ``part_units['protein_gene']`` times the amount by which the new reading's ``score_sum``
      beats the best held. A ``score_sum`` is a sum of the finder's scores of however many genes it calls, so the rise has no
      finite upper bound: ``UNBOUNDED``, while a request can name a code with no reading held (``offered_codes``); a request the
      check would refuse (a reading under the code held, a special code on a piece too short to apply it) earns 0, and with no code
      left the action's ceiling is 0.
    * ``find_rna_genes``: the credit rises by ``part_units['rna_gene']`` times the sum of the bit scores of the parts of one scan, a
      sum with no finite upper bound for the same reason: ``UNBOUNDED`` until the piece's scan is held (the check refuses a second
      scan), then 0."""
    if action_type == DESCRIBE_TOOL:
        return 0.0
    if action_type == FIND_GENES_TOOL:
        codes = offered_codes(summary)
        if arguments is None:
            return UNBOUNDED if codes else 0.0
        return UNBOUNDED if arguments['code'] in codes else 0.0
    if action_type == RNA_TOOL:
        return 0.0 if rna_scanned(summary) else UNBOUNDED
    raise ValueError('parts_discovery_ceiling_not_derived_for_action_type:' + action_type)
