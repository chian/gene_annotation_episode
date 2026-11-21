"""What the parent gives: the commission of one BV-BRC alignment, controlled values and record references only. This is the
only place the assignment is read. A wrong commission raises and the run fails; nothing repairs it.

``query_refs``: exactly one protein subject record of the parent's scope (the target), and ``input_refs``: the records its
sequence is read from, both passed in custody. ``search_ref``: exactly one record, the held graded BV-BRC search whose
candidates are aligned (with the records it names, in ``input_refs``); ``candidates``: the product candidates that take
part, each ``{name}`` exactly as the search's source gives the product (at least two, chosen by the parent from the
candidates it admitted from that search); ``per_candidate``: how many sequences of each (2 to 20; code chooses which);
``resource_id``: the bound BV-BRC resource; ``until`` and the three credit units and, on a resuming commission, the
handoff, status and closure records passed back with ``known_ended`` (the shared ``bvbrc_job_child.read_common``)."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.bvbrc_job_child import (
    COMMON_ASSIGNMENT, read_common)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.bvbrc_msa_alignment import (
    MINIMUM_CANDIDATES, PER_CANDIDATE_RANGE)

CANDIDATE_FORM = RecordForm({'name': Field('text', 'A product candidate\'s name exactly as the search gives it')})
ASSIGNMENT_FORM = RecordForm({
    'query_refs': Field('record_refs', 'The target: exactly one protein subject record of the parent\'s scope, passed in '
                                       'custody'),
    'input_refs': Field('record_refs', 'The records the target\'s sequence and the search are read from, passed in custody'),
    'search_refs': Field('record_refs', 'The held graded BV-BRC database search whose candidates are aligned: exactly one '
                                        'source record, passed in custody'),
    'candidates': Field('list', 'The product candidates of that search that take part (at least two)', items=CANDIDATE_FORM),
    'per_candidate': Field('integer', 'How many sequences of each candidate are aligned (' + str(PER_CANDIDATE_RANGE[0])
                           + ' to ' + str(PER_CANDIDATE_RANGE[1]) + '); code chooses which'),
    'resource_id': Field('text', 'The bound BV-BRC resource of the job service the alignment is launched on'),
    **COMMON_ASSIGNMENT,
})


def read_from_parent(assignment, message):
    (query,) = assignment['query_refs']
    (search,) = assignment['search_refs']
    names = [row['name'] for row in assignment['candidates']]
    if len(set(names)) != len(names) or len(names) < MINIMUM_CANDIDATES:
        raise ValueError('bvbrc_msa_two_or_more_distinct_candidates_required')
    if not PER_CANDIDATE_RANGE[0] <= assignment['per_candidate'] <= PER_CANDIDATE_RANGE[1]:
        raise ValueError('bvbrc_msa_per_candidate_out_of_range')
    common = read_common(assignment, 'bvbrc_msa')
    fields = {'per_candidate': assignment['per_candidate'], 'resource_id': assignment['resource_id']}
    return {'fields': fields, 'query_ref': query, 'search_ref': search, 'candidates': names, **common}
