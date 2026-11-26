"""The return: controlled data only; no path and no free text. Always: ``credit`` and the ``finding``: for each sequence
of the scope its candidate feature calls, the highest score first, and the claims that wait for one.

A feature call (``features``) is a type and a location together: its ``kind`` (a type of the hierarchy of feature
types), its position ranges (``segments``; ``start`` and ``end`` are the outer positions; zero-based, the end not
included; they are those of its best supported version, and ``versions`` lists every position called for it), its
``strand``, its ``score``, the number of claims that sit in it, its ``rivals`` (the rows that compete with it for letters,
each with the facts of the letters shared) and the feature records that state it. ``rival_rank`` is the place of the
leading rival of the first row. A rival is a competitor, not a verdict: no row is removed or lowered for having one.

A waiting claim (``waiting_claims``) is a statement that letters lie inside a feature of a type and reading, which no
feature call so far includes: its kind, strand, position ranges, which end it claims, its support and the feature records
that state it. It is not a feature call and has no score.

Selectable: ``record_refs`` (the records this episode committed: each test's source, its grading and the feature
records) and ``held_readings`` (per sequence of the scope, each reading of the whole sequence held: the dimension, from a
fixed list, the value held and the weighted support of every value tested; ``feature_candidates``, "ONE READING OF THE
WHOLE SEQUENCE". The one dimension is the genetic code, whose values are the codes this head's gene finder can take. A
sequence on which no test was made under a reading has no row)."""
from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_features.feature_candidates import (
    KINDS, STRANDS)

from ..task import GENETIC_CODES

# The dimensions of a reading of the whole sequence, as the converters name them (``prodigal_calls.ALTERNATIVES``), and
# the values each can take.
READING_VALUES = {'genetic_code': GENETIC_CODES}

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
    'rank': Field('integer', 'The place of the rival in the rows of this sequence (the first row is 0)'),
    'shared_letters': Field('integer', 'The letters the two feature calls both state'),
    'same_type': Field('boolean', 'Whether the two are of one type'),
    'same_strand': Field('boolean', 'Whether the two are on one named strand'),
    'same_frame': Field('boolean', 'Whether the two, on one strand and read in codons, read the shared letters in one frame'),
})
FEATURE_FORM = RecordForm({
    'kind': ChoiceField('text', 'The type of the feature, from the hierarchy of feature types', KINDS),
    'strand': ChoiceField('text', 'The strand the feature is read on (. when the call names none)', STRANDS),
    'segments': Field('list', 'The position ranges of the feature (those of its best supported version)',
                      items=SEGMENT_FORM),
    'versions': Field('list', 'Every position called for this feature', items=VERSION_FORM),
    'start': Field('integer', 'The first position of the feature on the sequence (zero-based)'),
    'end': Field('integer', 'The position after the last of the feature'),
    'score': Field('number', 'The score of the feature call: the weighted support of the tests at its calls, at the '
                             'claims that sit in it and at every feature call it lies within by type'),
    'claim_count': Field('integer', 'The claims that sit in this feature call'),
    'rivals': Field('list', 'The rows that compete with this one for letters, each with the facts of the letters shared',
                    items=RIVAL_FORM),
    'feature_refs': Field('record_refs', 'The feature record of this feature call'),
})
CLAIM_FORM = RecordForm({
    'kind': ChoiceField('text', 'The type of feature the letters are claimed to lie inside', KINDS),
    'strand': ChoiceField('text', 'The strand of the claim (. when it names none)', STRANDS),
    'segments': Field('list', 'The position ranges claimed to lie inside a feature', items=SEGMENT_FORM),
    'start': Field('integer', 'The first position of the claim on the sequence (zero-based)'),
    'end': Field('integer', 'The position after the last of the claim'),
    'claims_start': Field('boolean', 'Whether the claim says the feature starts at its first position'),
    'claims_end': Field('boolean', 'Whether the claim says the feature ends at its last position'),
    'support': Field('number', 'The weighted support of the tests that made this claim'),
})
TARGET_FORM = RecordForm({
    'target_ref': Field('record_refs', 'The sequence of the scope the rows are of: exactly one record'),
    'features': Field('list', 'The candidate feature calls, the highest score first', items=FEATURE_FORM),
    'feature_count': Field('integer', 'The candidate feature calls'),
    'waiting_claims': Field('list', 'The claims no feature call includes, the best supported first', items=CLAIM_FORM),
    'waiting_claim_count': Field('integer', 'The waiting claims'),
    'test_count': Field('integer', 'The graded tests held for this sequence'),
    'rival_rank': Field('integer', 'The place of the leading rival of the first row', required=False),
})
FINDING_FORM = RecordForm({
    'targets': Field('list', 'One row per sequence of the scope', items=TARGET_FORM),
})
READING_VALUE_FORM = RecordForm({
    'value': ChoiceField('integer', 'A value of the dimension that tests were made under: a genetic code',
                         READING_VALUES['genetic_code']),
    'support': Field('number', 'The weighted support of the tests made under that value'),
})
READING_FORM = RecordForm({
    'target_ref': Field('record_refs', 'The sequence of the scope the reading is of: exactly one record'),
    'dimension': ChoiceField('text', 'What is read of the whole sequence', tuple(READING_VALUES)),
    'held': ChoiceField('integer', 'The value held: the one whose tests carry the most weighted support (the first made '
                                   'on a tie); the tests under any other value add to no score',
                        READING_VALUES['genetic_code']),
    'values': Field('list', 'Every value tests were made under, with its support', items=READING_VALUE_FORM),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The feature calls and waiting claims of each sequence of the scope', form=FINDING_FORM),
    'record_refs': Field('record_refs', 'The records this episode committed, closed under naming', required=False),
    'held_readings': Field('list', 'Per sequence of the scope, each reading of the whole sequence held (its genetic '
                                   'code), with the support of every value tested', items=READING_FORM, required=False),
})


def held_readings(summary):
    """The readings of the whole sequence held (``internal_summary``'s ``held_readings``: per sequence, per dimension, the
    value held and the support of each value, the values as the converter writes them) as controlled rows, the values as
    integers, in the order of the scope's sequences and then of the values."""
    return [{'target_ref': [target], 'dimension': dimension, 'held': int(reading['held']),
             'values': [{'value': int(value), 'support': support}
                        for value, support in sorted(reading['support'].items(), key=lambda item: int(item[0]))]}
            for target in summary['scope']['subject_refs']
            for dimension, reading in summary['held_readings'][target].items()]


def final_to_parent(summary, completion, selection):
    facts = {'record_refs': list(summary['returned_refs']), 'held_readings': held_readings(summary)}
    return {'credit': completion['credit'], 'finding': {'targets': summary['target_findings']},
            **{name: facts[name] for name in selection}}
