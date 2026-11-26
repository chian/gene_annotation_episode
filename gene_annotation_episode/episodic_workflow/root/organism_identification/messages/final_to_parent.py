"""The return: controlled data only; no path and no free text. Always: ``credit`` and the ``finding``: for each sequence
of the scope its candidate taxa (taxon id of the NCBI taxonomy, the taxonomy's own name for it, rank code, lineage, score,
the leading candidate first), the leading candidate, its leading rival and the deepest taxon the two share, the number
of tests held, and the taxon claims passed in that wait for a candidate (the claimed taxon id and lineage, its bit and
support, the candidate it is consistent with, why it waits from a fixed list, what it earned, and the source of its claim
sheet). Selectable: ``record_refs`` (the records this episode committed: each classification's source, its grading
artifact, its data-product rows, and the taxon references and observations)."""
from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.grading.taxonomic_classification.taxon_candidates import (
    WAITING_REASONS)

# Kraken 2's rank codes: a rank letter, and a digit for a level between two ranks.
RANK_CODES = tuple(letter + digit for letter in 'RDKPCOFGSU' for digit in ('', *'123456789'))

LINEAGE_FORM = RecordForm({
    'taxon_id': Field('integer', 'The taxon id (NCBI taxonomy)'),
})
CANDIDATE_FORM = RecordForm({
    'taxon_id': Field('integer', 'The candidate taxon (NCBI taxonomy id)'),
    'name': Field('text', 'The taxonomy\'s own name of the taxon'),
    'rank_code': ChoiceField('text', 'The rank code of the taxon', RANK_CODES),
    'lineage': Field('list', 'The taxa from below the root down to the candidate', items=LINEAGE_FORM),
    'score': Field('number', 'The candidate\'s score: the weighted support on its own lineage, summed over the classifications'),
})
WAITING_FORM = RecordForm({
    'taxon_id': Field('integer', 'The taxon the claim names (NCBI taxonomy id)'),
    'lineage': Field('list', 'The taxa from below the root down to the claimed taxon on the prepared taxonomy (empty when '
                             'the taxonomy does not hold it)', items=LINEAGE_FORM),
    'bit': Field('number', 'The value the claim carries, from 0 to 1'),
    'support': Field('number', 'The bit times the weight of its sheet'),
    'consistent_taxon_id': Field('integer', 'The deepest listed candidate on the claim\'s lineage', required=False),
    'reason': ChoiceField('text', 'Why the claim waits', WAITING_REASONS),
    'credit': Field('number', 'What the claim earned while it waited'),
    'source_ref': Field('record_refs', 'The source of the claim sheet: exactly one record'),
})
TARGET_FORM = RecordForm({
    'target_ref': Field('record_refs', 'The sequence of the scope the candidates are of: exactly one record'),
    'candidates': Field('list', 'The candidate taxa, the leading one first', items=CANDIDATE_FORM),
    'candidate_count': Field('integer', 'The candidate taxa'),
    'test_count': Field('integer', 'The graded classifications and claim sheets held for this sequence'),
    'waiting_claims': Field('list', 'The taxon claims no candidate is or lies inside, the best supported first',
                            items=WAITING_FORM),
    'waiting_claim_count': Field('integer', 'The waiting taxon claims'),
    'leader_taxon_id': Field('integer', 'The leading candidate', required=False),
    'rival_taxon_id': Field('integer', 'The leading candidate that is not on the leader\'s lineage', required=False),
    'agreed_taxon_id': Field('integer', 'The deepest taxon the leader and its rival share', required=False),
})
FINDING_FORM = RecordForm({
    'targets': Field('list', 'One row per sequence of the scope', items=TARGET_FORM),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The candidate taxa of each sequence of the scope', form=FINDING_FORM),
    'record_refs': Field('record_refs', 'The records this episode committed, closed under naming', required=False),
})


def final_to_parent(summary, completion, selection):
    facts = {'record_refs': list(summary['returned_refs'])}
    return {'credit': completion['credit'], 'finding': {'targets': summary['target_findings']},
            **{name: facts[name] for name in selection}}
