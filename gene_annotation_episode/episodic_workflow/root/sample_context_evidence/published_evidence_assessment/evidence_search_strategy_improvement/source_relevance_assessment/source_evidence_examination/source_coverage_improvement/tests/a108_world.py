"""A real held world for the A108 grading route: a Store with the problem, one paper source whose text reports an
organism-level growth response, the target organism context, the contextual claim (hypothesis) and the original
observation (a ``literature_result`` reference anchored in the paper). The records are written as the run's caller
writes them (origin ``caller``) and passed to the entry Episode in custody. Nothing is faked."""
import json

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.sample_context_evidence.acquisition import (
    PublicClients)
from gene_annotation_episode.state import Store

PAPER = ('Methods. Strain QX-7 was isolated from a freshwater sediment. Results. Strain QX-7 grew with succinate as '
         'the sole carbon source, reaching an optical density of 1.2 after 48 h, and did not grow without succinate. '
         'Discussion. Succinate use by strain QX-7 is consistent with an active succinate transporter.')
ORGANISM = 'Strain QX-7'
# The settings of a literature episode (yield and tool registry) and the services the run's caller supplies.
SETTINGS = {'cost': 0.05, 'parameters': {'uncertainty_alpha': 0.05},
            'tool_registry': {'job_limits': {'memory_bytes': 1073741824, 'scratch_bytes': 1073741824}}}
SERVICES = {'public_clients': lambda: PublicClients(ncbi_email=None)}
RESULT = 'Strain QX-7 grew with succinate as the sole carbon source'
COMMON = ('source_subject_identity', 'original_observation_identity', 'context_applicability',
          'function_context_connection')
SPECIFIC = ('resource_role', 'response_endpoint', 'culture_circumstance', 'response_interpretation')


def span(text, quote):
    start = text.encode().index(quote.encode())
    return start, start + len(quote.encode())


def anchor(source, quote):
    start, end = span(PAPER, quote)
    return {'source_ref': source['id'], 'artifact_ref': source['artifact_ref'], 'start': start, 'end': end,
            'quote': quote}


def held_world(directory):
    """The Store, the records the entry passes, and the grading arguments the model would select."""
    store = Store(directory / 'store')
    store.create_problem(raw_sequence='MSTNPKPQRKTKRNTNRRPQDVKFPGG', molecule='protein')
    subjects = list(store.problem()['subject_refs'])
    scope = {'subject_refs': subjects}
    artifact = store.artifact(PAPER, 'text/plain')
    paper = store.put('source', {'provider': 'synthetic_literature_fixture', 'accession': None, 'uri': None,
                                 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': None,
                                 'retrieved_at': None, 'parent_source_refs': []}, origin='caller')
    organism = store.put('context', {'context_type': 'organism', 'name': ORGANISM, 'source_ref': paper['id'],
                                     'attributes': [], 'related_refs': [],
                                     'anchor': anchor(paper, ORGANISM)}, origin='caller')
    claim = store.put('hypothesis', {'subject_refs': subjects, 'predicate': 'uses',
                                     'value': {'type': 'reference', 'ref': organism['id']},
                                     'context_refs': [organism['id']]}, origin='caller')
    result = store.put('reference', {'reference_type': 'literature_result', 'source_ref': paper['id'],
                                     'accession': 'qx7-succinate-growth', 'label': RESULT, 'sequence_ref': None, 'molecule': None,
                                     'length': None, 'term_refs': [], 'context_refs': [organism['id']],
                                     'anchor': anchor(paper, RESULT)}, origin='caller')
    held = [*subjects, paper['id'], artifact, organism['id'], claim['id'], result['id']]
    return {'store': store, 'scope': scope, 'paper': paper, 'organism': organism, 'claim': claim, 'result': result,
            'held': held}


def passage(world, quote):
    start, end = span(PAPER, quote)
    return {'kind': 'literature_passage', 'witness': {'source_ref': world['paper']['id'], 'representation': 'original',
                                                      'start': start, 'end': end}}


def grading_arguments(world, relation='support'):
    """What the model selects for ``literature.a108_grading.populate``: the physiology_resource_response grader,
    one original observation of the target organism with every criterion supported by the observation."""
    supported = {'status': 'supported', 'support_refs': [world['result']['id']]}
    return {'assertion_ref': world['claim']['id'], 'target_context_ref': world['organism']['id'],
            'target_identity': {'status': 'supported', 'support_refs': [world['organism']['id']]},
            'grader_type': 'physiology_resource_response', 'source_ref': world['paper']['id'],
            'target_identity_evidence': [passage(world, ORGANISM)],
            'observations': [{'original_observation_ref': world['result']['id'],
                              'context_claim_ref': world['claim']['id'],
                              'source_subject_ref': world['organism']['id'],
                              'source_context_ref': world['organism']['id'],
                              'origin': 'organism_physiology_report', 'target_relationship': 'direct',
                              'relation': relation, 'criteria': {name: supported for name in (*COMMON, *SPECIFIC)},
                              'qualifications': [], 'evidence': [passage(world, RESULT)],
                              'origin_link_evidence': []}]}


def leads_task():
    """The one commissioned task of the leaves: the verified source leads."""
    return {'version': 'literature_local_task', 'evidence_axis': 'A108', 'kind': 'verified_source_leads',
            'credit_unit': 1.0}


def window(world, first=0, last=None):
    """A window of the paper in the page's representation: bytes ``[first, last)`` (the whole paper by default)."""
    paper = world['paper']
    last = len(PAPER.encode()) if last is None else last
    return {'source_ref': paper['id'], 'representation': 'original', 'offset': first, 'limit': last - first}


def reading_assignment(world, selection, requested=('evidence_amount',)):
    """The ``reading_assignment`` of a leaf: the paper as the page and the leaf's ``selection`` (a leaf's own
    shape: ``{'spans': [windows]}`` for the chunk and report leaves, one window for the table leaf)."""
    paper = world['paper']
    page = {'version': 'page_assignment', 'source_ref': paper['id'], 'representation': 'original',
            'artifact_ref': paper['artifact_ref'], 'question_context_refs': [world['organism']['id']],
            'prior_delivery_refs': []}
    assignment = {'version': 'reading_assignment', 'page': page, 'selection': selection,
                  'literature_task': leads_task(), 'proposed_annotation_ref': world['claim']['id'],
                  'scope': world['scope'], 'received_record_refs': list(dict.fromkeys(world['held']))}
    if requested:
        assignment['requested_a108_grading_components'] = list(requested)
    return assignment


def saved(store, sheet_ref):
    return json.loads(store.get_artifact(store.get(sheet_ref)['artifact_ref']))


def graded_commit(world):
    """What the model selects for ``reason``: an observation of the reported growth response, the assessment of the
    contextual claim with its typed investigation finding, and the grading of that observation in the same action
    (``evidence_processing`` ``graded``: the grader arguments as JSON, the observation by its alias)."""
    subjects = world['scope']['subject_refs']
    start, end = span(PAPER, RESULT)
    commit = {'terms': [], 'source_subjects': [], 'hypotheses': [],
              'annotation_updates': [],
              'observations': [{'alias': 'growth', 'subject_refs': subjects,
                                'source_subject_refs': [world['organism']['id']], 'kind': 'growth_assay',
                                'source_ref': world['paper']['id'], 'measurements': [],
                                'dependencies': [world['result']['id']],
                                'anchor': {'source_ref': world['paper']['id'],
                                           'artifact_ref': world['paper']['artifact_ref'], 'start': start,
                                           'end': end}}],
              'assessments': [{'alias': 'fit', 'expected_revision': 0, 'hypothesis_ref': world['claim']['id'],
                               'observation_ref': '@growth', 'relation': 'strengthens',
                               'applicability': 'contextual', 'extent_basis': 'inferred_extent',
                               'condition_refs': [], 'assumption_refs': [],
                               'investigation_finding': {
                                   'source_claim': {'subject_refs': [world['organism']['id']], 'predicate': 'uses',
                                                    'value': {'type': 'reference', 'ref': world['organism']['id']},
                                                    'context_refs': [world['organism']['id']]},
                                   'qualification': {'kind': 'none', 'context_refs': [], 'assumption_refs': []},
                                   'status': 'retained', 'withdrawal_reason': 'not_withdrawn',
                                   'same_source_claim_as_ref': None, 'replaces_refs': []}}]}
    return {'kind': 'reason', 'commit': commit, 'evidence_processing': {
        'kind': 'graded', 'gradings': [{'arguments': json.dumps(grading_arguments(world))}]}}


def source_lead(world, disposition='relevant'):
    """The source lead of the verified-source-leads commission: the paper, its anchored result reference as the
    subject, and the exact interval of the result in the paper."""
    start, end = span(PAPER, RESULT)
    return {'proposed_annotation_ref': world['claim']['id'], 'source_ref': world['paper']['id'],
            'subject_ref': world['result']['id'], 'disposition': disposition,
            'relevance_rationale': 'the paper reports the growth response of the target organism on succinate',
            'witness': {'source_ref': world['paper']['id'], 'representation': 'original', 'start': start, 'end': end}}


def extraction(world):
    """What the model selects for the one ``extract`` action: the graded commit and the source lead."""
    return {**graded_commit(world), 'source_lead': source_lead(world)}
