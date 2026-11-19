"""The calls the native-publication credit tests make inside the probe episode."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.evolutionary_history_evidence.credit import (
    A104AlignmentSuitabilityCredit, A104PanelIdentityCredit)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.evolutionary_history_evidence.hpc import (
    NATIVE_REQUESTS, NATIVE_RESULTS)


def commission(store):
    """An annotation hypothesis on the problem's subject, and the assignment that names it."""
    subject = store.problem()['subject_refs'][0]
    source = store.put('source', {'provider': 'probe_papers', 'accession': None, 'uri': None,
                                  'artifact_ref': store.artifact('probe', 'text/plain'), 'text_ref': None,
                                  'request_ref': None, 'version': None, 'retrieved_at': None}, origin='caller')['id']
    term = store.put('term', {'namespace': 'probe', 'accession': 'reaction1', 'label': 'A reaction',
                              'term_type': 'reaction', 'source_ref': source, 'anchor': None}, origin='caller')['id']
    annotation = store.put('hypothesis', {'subject_refs': [subject], 'predicate': 'catalyzes',
                                          'value': {'type': 'term_ref', 'ref': term}, 'context_refs': []},
                           origin='reasoning')['id']
    scope = {'subject_refs': [subject]}
    return scope, {'scope': scope, 'proposed_annotation_ref': annotation}, [subject, annotation]


def credit_without_registrations(ctx):
    """Neither a native request nor a native result has been registered: both credits are zero."""
    store = ctx.store
    scope, assignment, known = commission(store)
    panel = A104PanelIdentityCredit()(store, scope, known_record_refs=known, assignment=assignment)
    alignment = A104AlignmentSuitabilityCredit()(store, scope, known_record_refs=known, assignment=assignment)
    return {'panel': panel['credit'], 'alignment': alignment['credit'],
            'requests': len(store.table(NATIVE_REQUESTS).select()), 'results': len(store.table(NATIVE_RESULTS).select())}
