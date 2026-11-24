"""What the parts-discovery head reads from its commissioner: ``scope`` (the Store scope: ``subject_refs``, exactly one record, the
piece of DNA), ``scope_refs`` (the records the scope names, in custody: the piece and its sequence) and ``part_units``, the
commissioner's two positive numbers that make the credit of the two kinds of part comparable: ``protein_gene`` (credit per unit of a
reading's score, the sum of the gene finder's scores) and ``rna_gene`` (credit per bit of an RNA gene's score).

This is the only place the assignment is read. It checks what needs nothing but the value: the scope names exactly one subject, the
subject is among the records passed in custody, the part units are exactly the two kinds and positive. A wrong commission raises:
there is no repair. That the subject is an ``input`` record of a DNA molecule is checked where the records are read
(``internal_summary``). ``yield_task`` is the key of the head's declaration in ``yield_bindings`` (``yield_estimator.py``)."""
from method_loop import Field, RecordForm

YIELD_TASK = 'parts_discovery:parts_reading'
PART_UNIT_KINDS = ('protein_gene', 'rna_gene')

ASSIGNMENT_FORM = RecordForm({
    'scope': Field('record', 'The Store scope this episode investigates: subject_refs, exactly one reference: the piece of DNA'),
    'scope_refs': Field('record_refs', 'The records the scope names, passed in custody: the piece and its sequence'),
    'part_units': Field('record', 'The credit per unit of score of each kind of part: protein_gene (per unit of a reading\'s score) '
                                  'and rna_gene (per bit score), both positive numbers',
                        form=RecordForm({'protein_gene': Field('number', 'Credit per unit of a reading\'s score'),
                                         'rna_gene': Field('number', 'Credit per bit of an RNA gene\'s score')})),
})


def read_from_parent(assignment, message):
    """The validated assignment as the parent input."""
    scope = assignment['scope']
    if set(scope) != {'subject_refs'} or len(scope['subject_refs']) != 1:
        raise ValueError('parts_scope_must_name_exactly_one_subject')
    (piece,) = scope['subject_refs']
    if piece not in assignment['scope_refs']:
        raise ValueError('parts_subject_must_be_passed_in_custody:' + piece)
    units = assignment['part_units']
    if set(units) != set(PART_UNIT_KINDS) or any(units[kind] <= 0 for kind in PART_UNIT_KINDS):
        raise ValueError('parts_part_units_must_be_positive_numbers_for_protein_gene_and_rna_gene')
    return {'scope': {'subject_refs': [piece]}, 'scope_refs': list(assignment['scope_refs']), 'part_units': dict(units),
            'yield_task': YIELD_TASK, 'message': dict(message)}
