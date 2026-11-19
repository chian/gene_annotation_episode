"""The calls the A107 qualification test makes inside the probe episode."""
from gene_annotation_episode.episodic_workflow.episode_support.grading import qualification


def body(subjects):
    return {'version': qualification.VERSION, 'operation': 'probe_operation', 'arguments': {}, 'run_id': 'probe',
            'scope': {'subject_refs': list(subjects)}, 'target_ref': subjects[0], 'target_regions': [[0, 6]],
            'operand_refs': sorted(subjects), 'scientific_credit': None}


def publish(ctx, subjects):
    """A frozen request, then a graded qualification: each is published, then read back from the Episode's rows."""
    store, content = ctx.store, body(subjects)
    request = qualification._publish(store, qualification.REQUEST_PROVIDER, content)
    graded = qualification._publish(store, qualification.PROVIDER, content, graded=True)
    return {'request': request, 'graded': graded,
            'request_rows': [row['source_ref'] for row in store.table(qualification.REQUESTS).select()],
            'graded_rows': [row['source_ref'] for row in store.table(qualification.QUALIFICATIONS).select()],
            'request_read': qualification._read(store, request) == content,
            'graded_read': qualification._read(store, graded, graded=True) == content,
            'other_provider': qualification._read(store, request, graded=True)}
