"""A real held world for the A105 grading of this episode (the commission of the A105 head): a Store with the problem, a
synthetic source (an assay's reported effect, variance, controls and fixed predictions, each a number followed by its
printed unit), the
assay reference anchored in it and a reaction term, all passed to the entry Episode in custody; and the reasoning
selection a model makes on it (the commit of the hypothesis, observation and assessment with its typed
investigation finding, and the grading arguments of the ``activity_rate`` grader for that assay)."""
import json

from gene_annotation_episode.state import Store

FLAGS = ('assay_grading_population', 'ratio_source_population', 'controlled_response_population', 'gel_population',
         'completion_time_population', 'product_partition_population', 'active_site_population',
         'parent_depletion_population', 'stoichiometric_balance_population', 'compiled_assay_population',
         'channel_population', 'ion_discrimination_population')
SETTINGS = {'cost': 0.0, 'parameters': {'uncertainty_alpha': 0.05}, 'rate_population': False,
            **{name: False for name in FLAGS},
            'tool_registry': {'pdfinfo_executable': None, 'pdftotext_executable': None, 'pdftoppm_executable': None,
                              'job_limits': {'memory_bytes': 1 << 30, 'scratch_bytes': 1 << 30}},
            'knowledge_library_directory': None, 'launch_instruction_directory': None}
LINES = ['Experiment A: purified enzyme hydrolysis rate assay with a known normal fixed-prediction model.',
         'effect 12.5 U/mg; variance 0.25 U/mg_squared;',
         'recovery 0.9 fraction; attributed 0.6 fraction; total 0.8 fraction;',
         'condition test 0.8 fraction; condition reference 1 fraction;',
         'assertion prediction 12 U/mg; alternative prediction 0 U/mg.']
TEXT = '\n'.join(LINES)
CRITERIA = ('measurement_identity', 'calibration_applicability', 'matrix_interference', 'background_alternatives',
            'attribution_supported', 'assertion_relevance', 'condition_scope', 'variance_correspondence',
            'sampling_basis', 'rate_regime', 'normalization_basis')


def held_world(directory, task_kind='a105_experiments'):
    """The Store, the entry input of the episode at ``assignment_version`` and the records the model would name."""
    store = Store(directory / 'store')
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    target = store.problem()['subject_refs'][0]
    scope = {'subject_refs': [target]}
    artifact = store.artifact(TEXT, 'text/plain')
    source = store.put('source', {'provider': 'synthetic_a105_table', 'accession': None, 'uri': None,
                                  'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
                                  'version': None, 'retrieved_at': None, 'parent_source_refs': []},
                       origin='caller')['id']
    quote = LINES[0]
    assay = store.put('reference', {'reference_type': 'assay', 'source_ref': source, 'accession': 'synthetic_assay_a',
                                    'label': 'Experiment A', 'sequence_ref': None, 'molecule': None, 'length': None,
                                    'term_refs': [], 'context_refs': [],
                                    'anchor': {'source_ref': source, 'artifact_ref': artifact, 'start': 0,
                                               'end': len(quote), 'quote': quote}}, origin='caller')['id']
    reaction = store.put('term', {'namespace': 'synthetic', 'accession': 'hydrolysis', 'label': 'Hydrolysis',
                                  'term_type': 'reaction', 'source_ref': source, 'anchor': None},
                         origin='caller')['id']
    proposed = store.put('hypothesis', {'subject_refs': [target], 'predicate': 'catalyzes',
                                        'value': {'type': 'term_ref', 'ref': reaction}, 'context_refs': []},
                         origin='reasoning')['id']
    task = ({'version': 'literature_local_task', 'kind': 'a105_experiments', 'evidence_axis': 'A105', 'credit_unit': 1.0,
             'experiments': [{'experiment_ref': assay, 'assay_type': 'activity_rate'}]}
            if task_kind == 'a105_experiments' else
            {'version': 'literature_local_task', 'kind': 'verified_source_leads', 'evidence_axis': 'A105',
             'credit_unit': 1.0})
    page = {'version': 'page_assignment', 'source_ref': source, 'representation': 'original',
            'artifact_ref': artifact, 'question_context_refs': [], 'prior_delivery_refs': []}
    held = [target, source, artifact, assay, reaction, proposed]
    option = {'version': 'experimental_activity_evidence_option_ref', 'library_id': 'a' * 64, 'entry_sha256': 'b' * 64}
    selection = {'version': 'experimental_activity_evidence_selection',
                 'evidence_axis': {**option, 'slot': 'evidence_axis', 'option_id': 'A105'},
                 'thought_pattern': {**option, 'slot': 'thought_pattern', 'option_id': 'P1'},
                 'child_tool_info': [{'name': 'source.read', 'resources': 'api'}]}
    assignment = {'selection': selection, 'proposed_annotation_ref': proposed, 'evidence_refs': held, 'constraints': {},
                  'context': {'evidence_task': {'version': 'evidence_axis_task', 'kind': 'whole_axis_findings',
                                                'evidence_axis': 'A105', 'credit_unit': 1.0}}, 'scope': scope}
    names = {'store': store, 'target': target, 'source': source, 'artifact': artifact, 'assay': assay,
             'reaction': reaction, 'proposed': proposed, 'scope': scope}
    return {**names, 'input': {'assignment': assignment, 'message': {'objective': 'grade the table'},
                               'selection': []}}


def witness(world, quote, start=0):
    offset = TEXT.index(quote, start)
    return {'source_ref': world['source'], 'representation': 'original', 'start': offset, 'end': offset + len(quote)}


def number(world, label, token, unit):
    fragment = label + ' ' + token + ' ' + unit
    start = TEXT.index(fragment)
    return {'kind': 'source_number',
            'number': {'witness': witness(world, fragment), 'number_start': len(label) + 1,
                       'number_end': len(label) + 1 + len(token)},
            'unit': witness(world, unit, start + len(label) + len(token) + 2), 'origin': 'reported'}


def grading_arguments(world, assertion):
    """The ``activity_rate`` grader's arguments for the anchored assay, against ``assertion``."""
    return {'source_ref': world['source'], 'source_kind': 'synthetic_fixture', 'assay_type': 'activity_rate',
            'assertion_ref': assertion, 'experiment_ref': world['assay'], 'quantity_kind': 'rate',
            'interpretations': {name: {'status': 'supported', 'support_refs': [world['assay']]} for name in CRITERIA},
            'prediction_model': {'kind': 'fixed_predictions_known_normal', 'variance_interpretation': 'known',
                                 'support_refs': [world['assay']]},
            'quantities': {'effect': number(world, 'effect', '12.5', 'U/mg'),
                           'effect_variance': number(world, 'variance', '0.25', 'U/mg_squared'),
                           'recovery': number(world, 'recovery', '0.9', 'fraction'),
                           'attributed_signal': number(world, 'attributed', '0.6', 'fraction'),
                           'total_signal': number(world, 'total', '0.8', 'fraction'),
                           'condition_test': number(world, 'condition test', '0.8', 'fraction'),
                           'condition_reference': number(world, 'condition reference', '1', 'fraction'),
                           'assertion_prediction': number(world, 'assertion prediction', '12', 'U/mg'),
                           'alternative_prediction': number(world, 'alternative prediction', '0', 'U/mg')}}


def reasoning_selection(world):
    """What a model selects for ``reason``: the observation of the assay's reported rate, its assessment against the
    proposed annotation with a typed investigation finding, and the grading of the assay in the same action."""
    claim = {'subject_refs': [world['assay']], 'predicate': 'catalyzes',
             'value': {'type': 'term_ref', 'ref': world['reaction']}, 'context_refs': []}
    commit = {'structural_proposals': [], 'terms': [], 'source_subjects': [], 'hypotheses': [],
              'annotation_updates': [],
              'observations': [{'alias': 'rate', 'subject_refs': [world['target']],
                                'source_subject_refs': [world['assay']], 'kind': 'assay_report',
                                'source_ref': world['source'], 'measurements': [], 'dependencies': [],
                                'anchor': {'source_ref': world['source'], 'artifact_ref': world['artifact'],
                                           'start': TEXT.index(LINES[1]),
                                           'end': TEXT.index(LINES[1]) + len(LINES[1])}}],
              'assessments': [{'alias': 'graded', 'hypothesis_ref': world['proposed'], 'observation_ref': '@rate',
                               'relation': 'strengthens', 'applicability': 'transfer',
                               'extent_basis': 'observed_extent', 'condition_refs': [], 'assumption_refs': [],
                               'expected_revision': 0,
                               'investigation_finding': {
                                   'source_claim': claim,
                                   'qualification': {'kind': 'different_source_subject', 'context_refs': [],
                                                     'assumption_refs': []},
                                   'status': 'retained', 'withdrawal_reason': 'not_withdrawn',
                                   'same_source_claim_as_ref': None, 'replaces_refs': []}}]}
    return {'commit': commit, 'evidence_processing': {
        'kind': 'graded', 'gradings': [{'arguments': json.dumps(grading_arguments(world, world['proposed']))}]}}
# A real model run: each unit costs 0.1 credit, so the controller stops the Episode when its forecast yield of a
# further unit no longer exceeds that.
MODEL_SETTINGS = {**SETTINGS, 'cost': 0.1}
FLAGS_OFF = {name: False for name in FLAGS}
# The three reading children take the same settings; the population route is off for the examination run.
CHILD_PATHS = ('table', 'report', 'chunk')
