"""The return: controlled data only; no path and no free text. Always: ``credit`` and the ``finding``: for each sequence
of the scope its candidate taxa (taxon id of the NCBI taxonomy, the taxonomy's own name for it, rank code, lineage, score,
the leading candidate first), the leading candidate, its leading rival and the deepest taxon the two share, and the number
of classifications held. Selectable: ``record_refs`` (the records this episode committed: each classification's source,
its grading artifact, its data-product rows, and the taxon references and observations)."""
from method_loop import ChoiceField, Field, RecordForm

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
TARGET_FORM = RecordForm({
    'target_ref': Field('record_refs', 'The sequence of the scope the candidates are of: exactly one record'),
    'candidates': Field('list', 'The candidate taxa, the leading one first', items=CANDIDATE_FORM),
    'candidate_count': Field('integer', 'The candidate taxa'),
    'test_count': Field('integer', 'The graded classifications held for this sequence'),
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
