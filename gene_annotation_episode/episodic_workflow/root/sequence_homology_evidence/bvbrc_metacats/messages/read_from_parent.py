"""What the parent gives: the commission of one MetaCATS analysis, controlled values and record references only. This is the
only place the assignment is read. A wrong commission raises and the run fails; nothing repairs it.

``query_refs``: exactly one protein subject record of the parent's scope (the target), ``input_refs``: every record the
child reads, passed in custody (the target's sequence, the alignment's source with its sheet and alignment artifact and the
data-product rows). ``alignment_refs``: exactly one record, the held data-product row of kind ``multiple_sequence_alignment``
(the requirement: the child's checks refuse a record that is not one); ``resource_id``: the bound
BV-BRC resource; ``until`` and the three credit units and, on a resuming commission, the handoff, status and closure records
passed back with ``known_ended`` (the shared ``bvbrc_job_child.read_common``). The groups are not a field: code builds them; the p-value is not a field: it is one fixed value (``P_VALUE``)."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.bvbrc_job_child import (
    COMMON_ASSIGNMENT, read_common)

ASSIGNMENT_FORM = RecordForm({
    'query_refs': Field('record_refs', 'The target: exactly one protein subject record of the parent\'s scope, passed in '
                                       'custody'),
    'input_refs': Field('record_refs', 'The records the alignment is read from (its source, sheet and alignment artifact, '
                                       'the data-product rows) and the target\'s sequence, passed in custody'),
    'alignment_refs': Field('record_refs', 'The held alignment: exactly one data-product row of kind '
                                           'multiple_sequence_alignment, passed in custody'),
    'resource_id': Field('text', 'The bound BV-BRC resource of the job service the analysis is launched on'),
    **COMMON_ASSIGNMENT,
})


def read_from_parent(assignment, message):
    (query,) = assignment['query_refs']
    (alignment,) = assignment['alignment_refs']
    common = read_common(assignment, 'bvbrc_metacats')
    fields = {'resource_id': assignment['resource_id']}
    return {'fields': fields, 'query_ref': query, 'alignment_ref': alignment, **common}
