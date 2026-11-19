"""The real records of an A106 grading run of this episode: a Store with the problem, one paper source that reports
an engineered intervention experiment (the synthetic operands of the library's ``intervention_fixtures.py`` and
``test_literature_intervention_storage.py``), the experiment's anchored assay reference, the proposed annotation and
its explicit alternative (hypotheses), passed in custody by the entry assignment. Nothing is faked: the records are
written to a real Store and read through the real runner's custody."""
from episode_runtime import BindingRegistry, RunJournal, link
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_intervention_grading import (
    CRITERIA)
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.literature_intervention_inputs import (
    DESIGN_FIELDS)

UNIT = 'fraction'
LINES = [
    'Experiment A: synthetic assay for one reference molecule. Scientific applicability and a known normal '
    'fixed-prediction model are explicitly stipulated for this synthetic fixture.',
    f'effect 0.8 {UNIT}; variance 0.04 {UNIT}_squared;',
    'recovery 0.9 fraction; attributed 0.6 fraction; total 0.8 fraction;',
    'condition test 0.8 fraction; condition reference 1 fraction;',
    f'assertion prediction 1 {UNIT}; alternative prediction 0 {UNIT}.',
]
TEXT = '\n'.join(LINES)
SETTINGS = {'cost': 0.0, 'parameters': {'uncertainty_alpha': 0.05}, 'literature_populations': [],
            'literature_evidence_origins': {}}


def held_world(directory, task_kind='verified_source_leads'):
    """The Store, the entry input and the arguments a model would give the intervention grader."""
    store = Store(directory / 'store')
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    scope = {'subject_refs': list(store.problem()['subject_refs'])}
    artifact = store.artifact(TEXT, 'text/plain')
    source = store.put('source', {'provider': 'synthetic_intervention_fixture', 'accession': None, 'uri': None,
                                  'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
                                  'version': None, 'retrieved_at': None, 'parent_source_refs': []},
                       origin='caller')['id']
    quote = LINES[0]
    experiment = store.put('reference', {'reference_type': 'assay', 'source_ref': source,
                                         'accession': 'synthetic_assay_a106', 'label': 'Experiment A',
                                         'sequence_ref': None, 'molecule': None, 'length': None, 'term_refs': [],
                                         'context_refs': [],
                                         'anchor': {'source_ref': source, 'artifact_ref': artifact, 'start': 0,
                                                    'end': len(quote.encode()), 'quote': quote}},
                           origin='caller')['id']
    terms = [store.put('term', {'namespace': 'synthetic', 'accession': accession, 'label': label,
                                'term_type': 'reaction', 'source_ref': source, 'anchor': None},
                       origin='caller')['id']
             for accession, label in (('reaction_a106', 'Synthetic reaction'),
                                      ('alternative_a106', 'Synthetic alternative'))]
    assertion, comparison = (store.put('hypothesis', {'subject_refs': [experiment], 'predicate': 'catalyzes',
                                                      'value': {'type': 'term_ref', 'ref': term},
                                                      'context_refs': []}, origin='reasoning')['id']
                             for term in terms)
    held = [*scope['subject_refs'], source, artifact, experiment, *terms, assertion, comparison]
    page = {'version': 'page_assignment_v1', 'source_ref': source, 'representation': 'original',
            'artifact_ref': artifact, 'question_context_refs': [experiment, assertion], 'prior_delivery_refs': []}
    task = {'version': 'literature_local_task_v1', 'evidence_axis': 'A106', 'kind': task_kind, 'credit_unit': 1.0}
    assignment = {'version': 'reading_assignment_v1', 'page': page,
                  'selection': {'source_ref': source, 'representation': 'original', 'offset': 0, 'limit': 200},
                  'literature_task': task, 'proposed_annotation_ref': assertion, 'scope': scope,
                  'received_record_refs': held}
    entry = {'assignment': assignment, 'message': {'objective': 'grade the intervention experiment'},
             'selection': []}

    def witness(fragment, start=0):
        offset = TEXT.index(fragment, start)
        return {'source_ref': source, 'representation': 'original', 'start': offset, 'end': offset + len(fragment)}

    def number(label, token, native_unit):
        fragment = label + ' ' + token + ' ' + native_unit
        start = TEXT.index(fragment)
        return {'kind': 'source_number', 'number': {'witness': witness(fragment), 'number_start': len(label) + 1,
                                                    'number_end': len(label) + 1 + len(token)},
                'unit': witness(native_unit, start + len(label) + 1 + len(token) + 1), 'origin': 'synthetic'}
    grading = {
        'source_ref': source, 'source_kind': 'synthetic_fixture', 'assay_type': 'intervention_response',
        'assertion_ref': assertion, 'comparison_ref': comparison, 'experiment_ref': experiment,
        'quantity_kind': 'endpoint_ratio',
        'interpretations': {name: {'status': 'supported', 'support_refs': [experiment]} for name in CRITERIA},
        'prediction_model': {'kind': 'fixed_predictions_known_normal', 'variance_interpretation': 'known',
                             'support_refs': [experiment]},
        'quantities': {
            'effect': number('effect', '0.8', UNIT), 'effect_variance': number('variance', '0.04', UNIT + '_squared'),
            'recovery': number('recovery', '0.9', 'fraction'),
            'attributed_signal': number('attributed', '0.6', 'fraction'),
            'total_signal': number('total', '0.8', 'fraction'),
            'condition_test': number('condition test', '0.8', 'fraction'),
            'condition_reference': number('condition reference', '1', 'fraction'),
            'assertion_prediction': number('assertion prediction', '1', UNIT),
            'alternative_prediction': number('alternative prediction', '0', UNIT)},
        'experimental_design': dict.fromkeys(DESIGN_FIELDS),
        'experiment_assessment': {'experiment_ref': experiment, 'experiment_type': 'intervention_response',
                                  'assessment_key': 'synthetic-contribution',
                                  'scientific_question': 'Synthetic contribution?',
                                  'conclusion': 'Synthetic engineered comparison only.',
                                  'limitations': ['No biological evidence.'], 'revision_reason': None,
                                  'revises_sheet_ref': None}}
    names = {'source': source, 'artifact': artifact, 'experiment': experiment, 'assertion': assertion,
             'comparison': comparison, 'subject': experiment, 'scope': scope, 'assignment': assignment}
    return store, entry, grading, names


def envelope(names, arguments):
    """What ``action`` makes of a selection of a population tool."""
    return {'arguments': arguments, 'scope': names['scope'], 'page_source_ref': names['source'],
            'assignment': {'version': 'reading_assignment_v1', 'page': names['assignment']['page'],
                           'selection': names['assignment']['selection'],
                           'literature_task': names['assignment']['literature_task'],
                           'proposed_annotation_ref': names['assertion']},
            'proposed_annotation_ref': names['assertion']}


def finalize_arguments(names, sheet_ref):
    return {'subject_ref': names['subject'], 'assertion_ref': names['assertion'],
            'comparison_ref': names['comparison'], 'scope_statement': 'Synthetic stipulated model only.',
            'experiments': [{'experiment_ref': names['experiment'], 'sheet_ref': sheet_ref, 'missing_reason': None}],
            'dependence': {'status': 'unknown', 'rationale': 'One experiment', 'witnesses': []},
            'conclusion': 'Engineered evidence favors the assertion.', 'limitations': ['No biological evidence.'],
            'revises_subscore_ref': None, 'revision_reason': None}


def linked_run(directory, episodes, path, entry, store, run_id, settings):
    """The real runner over the real Store, journal and model provider."""
    collaborators = {'store': store, 'model_provider': ModelProvider(load_config(), directory / 'model_calls',
                                                                    directory),
                     'continuation': settings, 'services': {}}
    journal = RunJournal(directory / 'journal.sqlite3')
    return link(BindingRegistry(episodes), path, entry, run_id=run_id, journal=journal,
                collaborators=collaborators), journal, collaborators
