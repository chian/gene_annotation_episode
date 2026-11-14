"""Complete original synthetic-record helpers; no empirical interpretation."""
from gene_annotation_episode.domain import identity


def finding(subject, *, value='positive', qualification='none', equivalent=None, replaces=()):
    return {'source_claim': {'subject_refs': [subject], 'predicate': 'growth_capability',
                'value': {'type': 'enum', 'value': value}, 'context_refs': []},
        'qualification': {'kind': qualification, 'context_refs': [], 'assumption_refs': []},
        'status': 'retained', 'withdrawal_reason': 'not_withdrawn',
        'same_source_claim_as_ref': equivalent, 'replaces_refs': list(replaces)}


def target_question(store):
    target, = store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')['subject_refs']
    hypothesis = store.put('hypothesis', {'subject_refs': [target],
        'predicate': 'biological_role', 'value': {'type': 'enum', 'value': 'unresolved'},
        'context_refs': []}, origin='reasoning')['id']
    return target, hypothesis


def quoted_observation(store, *, accession, start, end, label='ConstructX'):
    text = 'ConstructX grows. The measured ConstructX grows under this condition.'
    artifact = store.artifact(text)
    source = store.put('source', {'provider': 'synthetic_fixture', 'accession': accession,
        'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
        'version': accession, 'retrieved_at': None,
        'publication_identifiers': [{'namespace': 'doi', 'value': '10.1234/synthetic'}]}, origin='external')
    anchor = {'source_ref': source['id'], 'artifact_ref': artifact,
        'start': start, 'end': end, 'quote': text[start:end]}
    subject_payload = {'reference_type': 'construct', 'source_ref': source['id'],
        'label': label, 'anchor': anchor}
    subject_payload.update(sequence_ref=None, length=None, molecule=None, term_refs=[], context_refs=[])
    # Native extracted-subject identity is source + label + exact anchor.
    subject_payload['accession'] = identity('source_entity',
        {key: subject_payload[key] for key in ('source_ref', 'label', 'anchor')})
    subject = store.put('reference', subject_payload, origin='extracted')['id']
    observation = store.put('observation', {'subject_refs': [subject],
        'source_subject_refs': [subject], 'kind': 'source_content', 'source_ref': source['id'],
        'measurements': [], 'dependencies': [], 'anchor': anchor}, origin='extracted')
    return subject, observation


def evidence(store, target, kind):
    artifact = store.artifact('SYNTHETIC runtime integration evidence: '+kind)
    source = store.put('source', {
        'provider': 'synthetic_fixture', 'accession': kind, 'uri': None,
        'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
        'version': 'fixture', 'retrieved_at': None}, origin='external')
    return store.put('observation', {
        'subject_refs': [target], 'source_subject_refs': [target], 'kind': kind,
        'source_ref': source['id'], 'measurements': [], 'dependencies': [],
        'anchor': None}, origin='external')


def assessment(hypothesis, observation, applicability, *, alias=None, revision=0):
    result = {'hypothesis_ref': hypothesis, 'observation_ref': observation,
        'relation': 'strengthens', 'applicability': applicability,
        'extent_basis': 'observed_extent', 'condition_refs': [], 'assumption_refs': [],
        'expected_revision': revision}
    if alias is not None:
        result['alias'] = alias
    return result


def source_fixture(store, label):
    artifact = store.artifact('Labelled synthetic fixture: '+label)
    return store.put('source', {'provider': 'synthetic_fixture', 'accession': label,
        'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
        'version': 'fixture', 'retrieved_at': None}, origin='external')


def put_finding(store, hypothesis, observed, subject, *, value='positive', qualification='none',
                replaces=(), revision=0, withdraw=False):
    payload = assessment(hypothesis, observed['id'], 'incomparable', revision=revision)
    payload['relation'] = 'does_not_discriminate'
    payload['investigation_finding'] = finding(subject, value=value, qualification=qualification,
                                                replaces=replaces)
    if withdraw:
        payload['investigation_finding'].update(status='withdrawn', withdrawal_reason='source_misread')
    return store.put('assessment', payload, origin='reasoning')


