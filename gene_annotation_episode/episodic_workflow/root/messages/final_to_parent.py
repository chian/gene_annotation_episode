"""The return of the annotation: controlled data only. Always returned: ``credit`` (the root's credit its controller
stopped on, which the system hands in ``completion``) and ``finding``: the root's scoring sheet in its two levels, the
level above (``feature_calls``: per sequence of the scope its feature calls, the highest score first, each with its
type, strand, positions, versions, score, claim count, rivals and the feature records that state it; a feature call
with no annotation is a line with its own score; with them the claims that wait for a feature call and the genetic code
held) and the level below (``annotations``: every candidate annotation the axis heads scored, with its score, the
hypervolume over the scores the axes give it multiplied by the factor ``(1 + k * s_o) ** w_o`` of the organism it is
reported with (a pure multiple: zero from the axes stays zero), that organism's taxon id and score, and the row of each
axis that scored it, the highest score first; no annotation is tied to a feature call yet), the best annotation
(``best_annotation``: the first of the annotation lines, present when its status is known), the organism (``organism``:
the candidate taxa of the root's scoring sheet of candidate taxa, the leading one first, and the placement), the claims
made from the annotations (``claims``), feature calling's credit and how often it was commissioned
(``feature_calling``), how many axis commissions the root made and, for each of the nine axes, its credit, how often it
was commissioned and how many job records its head left outstanding. Selectable, returned in custody: ``record_refs``
(the records the heads returned: the axis heads, feature calling and the organism identification head) and
``outstanding_job_refs`` (the records of the jobs still outstanding, with which a later run can return to them)."""
from method_loop import ChoiceField, Field, RecordForm

from ..credit import AXIS_WEIGHTS
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_features.feature_candidates import (
    KINDS, STRANDS)
from gene_annotation_episode.episodic_workflow.episode_support.tools.annotation_claims.claim_generation import (
    PARTNER_KINDS, PREDICATES as CLAIM_PREDICATES)
from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_features.prodigal_gene_calls import (
    MODE_CODES)

from .internal_summary import IDENTITY_FIELDS
from .read_from_child import FUNCTION_SOURCES, ROW_STATUS, VOCABULARIES

# The genetic codes a reading of the whole sequence can hold: those the gene finder can take.
GENETIC_CODES = tuple(sorted({*MODE_CODES['meta'], *MODE_CODES['single']}))

SEGMENT_FORM = RecordForm({
    'start': Field('integer', 'The first position of the range on the sequence (zero-based)'),
    'end': Field('integer', 'The position after the last of the range'),
})
VERSION_FORM = RecordForm({
    'segments': Field('list', 'The position ranges a test called for the feature', items=SEGMENT_FORM),
    'start': Field('integer', 'The first position of this version (zero-based)'),
    'end': Field('integer', 'The position after the last of this version'),
    'support': Field('number', 'The weighted support of the calls that stated exactly these positions'),
})
RIVAL_FORM = RecordForm({
    'rank': Field('integer', 'The place of the rival in the feature calls of this sequence (the first is 0)'),
    'shared_letters': Field('integer', 'The letters the two feature calls both state'),
    'same_type': Field('boolean', 'Whether the two are of one type'),
    'same_strand': Field('boolean', 'Whether the two are on one named strand'),
    'same_frame': Field('boolean', 'Whether the two, on one strand and read in codons, read the shared letters in one frame'),
})
FEATURE_CALL_FORM = RecordForm({
    'kind': ChoiceField('text', 'The type of the feature, from the hierarchy of feature types', KINDS),
    'strand': ChoiceField('text', 'The strand the feature is read on (. when the call names none)', STRANDS),
    'segments': Field('list', 'The position ranges of the feature (those of its best supported version)',
                      items=SEGMENT_FORM),
    'versions': Field('list', 'Every position called for this feature', items=VERSION_FORM),
    'start': Field('integer', 'The first position of the feature on the sequence (zero-based)'),
    'end': Field('integer', 'The position after the last of the feature'),
    'score': Field('number', "The score of the feature call as feature calling returned it; a feature call with no "
                             "annotation is a line of the sheet with this score"),
    'claim_count': Field('integer', 'The claims that sit in this feature call'),
    'rivals': Field('list', 'The feature calls that compete with this one for letters', items=RIVAL_FORM),
    'feature_refs': Field('record_refs', 'The feature records that state this feature call'),
})
WAITING_FEATURE_CLAIM_FORM = RecordForm({
    'kind': ChoiceField('text', 'The type of feature the letters are claimed to lie inside', KINDS),
    'strand': ChoiceField('text', 'The strand of the claim (. when it names none)', STRANDS),
    'segments': Field('list', 'The position ranges claimed to lie inside a feature', items=SEGMENT_FORM),
    'start': Field('integer', 'The first position of the claim on the sequence (zero-based)'),
    'end': Field('integer', 'The position after the last of the claim'),
    'claims_start': Field('boolean', 'Whether the claim says the feature starts at its first position'),
    'claims_end': Field('boolean', 'Whether the claim says the feature ends at its last position'),
    'support': Field('number', 'The weighted support of the tests that made this claim'),
    'feature_refs': Field('record_refs', 'The feature records that state this claim'),
})
READING_VALUE_FORM = RecordForm({
    'value': ChoiceField('integer', 'A genetic code tests were made under', GENETIC_CODES),
    'support': Field('number', 'The weighted support of the tests made under that code'),
})
READING_FORM = RecordForm({
    'target_ref': Field('record_refs', 'The sequence the reading is of: exactly one record'),
    'dimension': ChoiceField('text', 'What is read of the whole sequence', ('genetic_code',)),
    'held': ChoiceField('integer', 'The genetic code held: the one whose tests carry the most weighted support',
                        GENETIC_CODES),
    'values': Field('list', 'Every code tests were made under, with its support', items=READING_VALUE_FORM),
})
FEATURE_TARGET_FORM = RecordForm({
    'target_ref': Field('record_refs', 'The sequence of the scope the feature calls are of: exactly one record'),
    'features': Field('list', 'Its feature calls, the highest score first', items=FEATURE_CALL_FORM),
    'rival_rank': Field('integer', 'The place of the leading rival of the first feature call', required=False),
    'test_count': Field('integer', 'The graded tests feature calling held for this sequence'),
    'waiting_claims': Field('list', 'The claims no feature call includes, the best supported first',
                            items=WAITING_FEATURE_CLAIM_FORM),
    'held_readings': Field('list', 'The genetic code held for this sequence (none when no gene finding was made)',
                           items=READING_FORM),
})
FEATURE_CALLING_FORM = RecordForm({
    'credit': Field('number', "Feature calling's credit at its latest return, 0 before the first: the base of the "
                              "root's credit"),
    'commissions': Field('integer', 'How often feature calling was commissioned'),
})
# Kraken 2's rank codes, as the scoring sheet of candidate taxa writes them: a rank letter, and a digit for a level
# between two ranks.
RANK_CODES = tuple(letter + digit for letter in 'RDKPCOFGSU' for digit in ('', *'123456789'))
TAXON_LINEAGE_FORM = RecordForm({
    'taxon_id': Field('integer', 'The taxon id (NCBI taxonomy)'),
})
TAXON_CANDIDATE_FORM = RecordForm({
    'taxon_id': Field('integer', 'The candidate taxon (NCBI taxonomy id)'),
    'name': Field('text', "The taxonomy's own name of the taxon"),
    'rank_code': ChoiceField('text', 'The rank code of the taxon', RANK_CODES),
    'lineage': Field('list', 'The taxa from below the root down to the candidate', items=TAXON_LINEAGE_FORM),
    'score': Field('number', "The candidate's score: the weighted support on its own lineage, summed over the "
                             'classifications and the taxon claims held'),
})
ORGANISM_FORM = RecordForm({
    'candidates': Field('list', 'The candidate taxa of the sequence, the leading one first', items=TAXON_CANDIDATE_FORM),
    'leader_taxon_id': Field('integer', 'The leading candidate', required=False),
    'rival_taxon_id': Field('integer', "The leading candidate that is not on the leader's lineage", required=False),
    'agreed_taxon_id': Field('integer', 'The deepest taxon the leader and its rival share', required=False),
    'test_count': Field('integer', 'The graded classifications and taxon claim sheets held'),
    'waiting_claim_count': Field('integer', 'The taxon claims no candidate is or lies inside'),
})

_ABSENT = ' (absent when the status is unknown)'
AXIS_ROW_FORM = RecordForm({
    'axis': ChoiceField('text', 'The axis whose head scored the annotation', tuple(AXIS_WEIGHTS)),
    'status': ChoiceField('text', 'Whether that evidence is measured, measured as exactly zero, or unknown', ROW_STATUS),
    'score': Field('number', "The score that axis gives the annotation, on the axis's own scale; negative when its "
                             'evidence says the annotation does not hold' + _ABSENT, required=False),
    'support': Field('number', "The summed support of the annotation's claims, for an axis that checks claims",
                     required=False),
    'opposition': Field('number', "The summed opposition of the annotation's claims, for such an axis", required=False),
})
FUNCTION_IDENTIFIER_FORM = RecordForm({
    'source': ChoiceField('text', 'Where the identifier is from', FUNCTION_SOURCES),
    'identifier': Field('text', 'The function-level identifier exactly as its source gives it'),
    'hit_count': Field('integer', 'The proteins behind the annotation that carry it'),
})
IDENTIFIER_SOURCE_FORM = RecordForm({
    'source': ChoiceField('text', 'A source of function-level identifiers', FUNCTION_SOURCES),
    'protein_count': Field('integer', 'The proteins behind the annotation that carry any identifier of that source'),
})
MEMBER_FORM = RecordForm({
    'vocabulary': ChoiceField('text', 'The vocabulary of the annotation', VOCABULARIES),
    'name': Field('text', 'Its name exactly as its source gives it', required=False),
    'identifier': Field('text', 'Its own identifier: a family accession or a record reference', required=False),
    'axis': ChoiceField('text', 'The axis whose head named it', tuple(AXIS_WEIGHTS)),
    'score': Field('number', 'The score that axis gave it'),
})
ANNOTATION_FORM = RecordForm({
    'vocabulary': ChoiceField('text', 'The vocabulary of the candidate annotation: product (a database search\'s '
                                      'function), profile_family (a family of a profile database) or '
                                      'reference_sequence (a sequence record it was compared with)', VOCABULARIES),
    'name': Field('text', 'The name of the annotation exactly as its source gives it', required=False),
    'identifier': Field('text', 'The identifier of the annotation: a family accession or a record reference',
                        required=False),
    'status': ChoiceField('text', 'Whether the merged evidence is measured, measured as exactly zero, or unknown',
                          ROW_STATUS),
    'score': Field('number', 'The annotation score: (prod_i (1 + k * s_i) ** w_i - 1) * (1 + k * s_o) ** w_o: the '
                             'hypervolume over the scores s_i the axes give the annotation (0 for an axis that has '
                             'not scored it), multiplied by the factor of the score s_o of the organism it is '
                             'reported with (0 when no candidate taxon is held: the factor is 1)' + _ABSENT,
                   required=False),
    'organism_taxon_id': Field('integer', 'The organism the annotation is reported with, whose score entered the '
                                          'annotation score: the leading candidate taxon of the sequence (NCBI '
                                          'taxonomy id); absent when the annotation has no score or no candidate '
                                          'taxon is held', required=False),
    'organism_score': Field('number', "That taxon's score on the root's scoring sheet of candidate taxa: s_o of "
                                      'the annotation score; absent with the taxon', required=False),
    'function_identifiers': Field('list', 'The function-level identifiers of the proteins behind the annotation',
                                  items=FUNCTION_IDENTIFIER_FORM, required=False),
    'identifier_sources': Field('list', 'Per source of those identifiers, the proteins that carry any identifier of it',
                                items=IDENTIFIER_SOURCE_FORM, required=False),
    'hits_without_identifier': Field('integer', 'The proteins behind it that carry no such identifier', required=False),
    'rows': Field('list', 'One row per axis whose head scored the annotation', items=AXIS_ROW_FORM),
    'members': Field('list', 'Every annotation on this line (the names the heads gave this one function), with the axis '
                             'that named it and the score that axis gave it', items=MEMBER_FORM),
})
ANNOTATION_IDENTITY_FORM = RecordForm({name: ANNOTATION_FORM.fields[name] for name in IDENTITY_FIELDS})
CLAIM_FORM = RecordForm({
    'claim_ref': Field('text', 'The claim: a hypothesis record the root made from the annotation'),
    'annotation': Field('record', 'The candidate annotation the claim was made from', form=ANNOTATION_IDENTITY_FORM),
    'predicate': ChoiceField('text', 'What the claim says the protein does to the molecule', CLAIM_PREDICATES),
    'partner': Field('text', 'The molecule of the claim, by the name it was found under in a database'),
    'partner_kind': ChoiceField('text', 'Whether the molecule is a protein or a small molecule', PARTNER_KINDS),
    'commissions': Field('integer', 'How often a head was commissioned on the claim'),
})
AXIS_FORM = RecordForm({
    'credit': Field('number', 'The axis credit: what its head returned at its latest return, 0 before the first'),
    'commissions': Field('integer', 'How often the axis was commissioned'),
    'outstanding_jobs': Field('integer', 'How many job records its head left outstanding at its latest return'),
})
AXES_FORM = RecordForm({slot: Field('record', 'The state of the ' + slot + ' axis', form=AXIS_FORM)
                        for slot in AXIS_WEIGHTS})
FINDING_FORM = RecordForm({
    'feature_calls': Field('list', "The level above of the root's scoring sheet: per sequence of the scope its feature "
                                   'calls, the highest score first', items=FEATURE_TARGET_FORM),
    'annotations': Field('list', "The level below of the root's scoring sheet: every candidate annotation the axis "
                                 'heads scored, the highest score first, the ones of unknown status last; none is tied '
                                 'to a feature call yet', items=ANNOTATION_FORM),
    'claims': Field('list', 'The claims made from the candidate annotations', items=CLAIM_FORM),
    'best_annotation': Field('record', 'The best annotation: the first of the annotation lines (absent while no '
                                       'annotation has a known status)', form=ANNOTATION_FORM, required=False),
    'organism': Field('record', 'Which organism the sequence is from: the candidate taxa and the placement',
                      form=ORGANISM_FORM),
    'feature_calling': Field('record', 'The state of feature calling', form=FEATURE_CALLING_FORM),
    'commissions': Field('integer', 'How many axis commissions the root made'),
    'axes': Field('record', 'The state of each of the nine axes', form=AXES_FORM),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The root's credit when the Episode's controller stopped it"),
    'finding': Field('record', 'The feature calls, the annotations and the organism, and where each head stands',
                     form=FINDING_FORM),
    'record_refs': Field('record_refs', 'The records the heads returned', required=False),
    'outstanding_job_refs': Field('record_refs', 'The records of the jobs the axis heads left outstanding',
                                  required=False),
})


def organism_finding(organism):
    """The organism as the return carries it: the candidate taxa (their lineages as lists of taxon ids), the placement,
    the number of tests held and of waiting taxon claims."""
    return {'candidates': [{'taxon_id': row['taxon_id'], 'name': row['name'], 'rank_code': row['rank_code'],
                            'lineage': [{'taxon_id': taxon} for taxon in row['lineage_taxon_ids']],
                            'score': row['score']} for row in organism['candidates']],
            **organism['placement'], 'test_count': organism['test_count'],
            'waiting_claim_count': len(organism['waiting_claims'])}


def final_to_parent(summary, completion, selection):
    axes, annotations, features = summary['axes'], summary['annotations'], summary['features']
    result = {'credit': completion['credit'],
              'finding': {'feature_calls': summary['feature_calls'],
                          'annotations': annotations,
                          'claims': [{'claim_ref': claim['claim_ref'], 'annotation': claim['annotation'],
                                      'predicate': claim['predicate'], 'partner': claim['partner'],
                                      'partner_kind': claim['partner_kind'],
                                      'commissions': sum(axis['claim_commissions'].get(claim['claim_ref'], 0)
                                                         for axis in axes.values())}
                                     for claim in summary['claims']],
                          **({'best_annotation': annotations[0]}
                             if annotations and annotations[0]['status'] != 'unknown' else {}),
                          'organism': organism_finding(summary['organism']),
                          'feature_calling': {'credit': features['credit'],
                                              'commissions': len(features['credit_after_each_return'])},
                          'commissions': len(summary['commissions']),
                          'axes': {slot: {'credit': axis['credit'], 'commissions': len(axis['credit_after_each_return']),
                                          'outstanding_jobs': axis['outstanding_jobs']}
                                   for slot, axis in axes.items()}}}
    if 'record_refs' in selection:
        result['record_refs'] = list(dict.fromkeys([*features['record_refs'], *summary['organism']['record_refs'],
                                                    *(ref for axis in axes.values() for ref in axis['record_refs'])]))
    if 'outstanding_job_refs' in selection:
        result['outstanding_job_refs'] = list(dict.fromkeys(
            ref for axis in axes.values() for ref in axis['outstanding_job_refs']))
    return result
