"""What the parent gives: the source being read (a page), the window where document-order reading starts, the
commissioned task with its credit unit, the proposed annotation, the requested components of every result family,
the scope and the records passed in custody. This is the only place the assignment is read."""
import json
import math

from method_loop import DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import (
    ASSAY_TYPES)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_quantity_storage import (
    quantity_population_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import (
    ContractError, REF, obj, validate_schema)

VERSION = 'literature_local_task_v1'
SCREENING = 'literature_screening_answers'
LEADS = 'literature_source_lead_dispositions'
REPRESENTATIONS = ('text', 'original', 'stdout', 'stderr')
# The commissioner's objective (``message['objective']``): one value of this fixed vocabulary and nothing else
# (controlled messaging: no text of the commissioner's model reaches this episode's model). The value says what the
# commissioner knows about the source from the starting window on; the meaning beside it is this episode's own text,
# shown with the value.
OBJECTIVES = {
    'grade_reported_experiment': 'The source is known to report a commissioned experiment with its measurements from '
                                 'the starting window on: read in document order until you have it and grade that '
                                 'experiment, entering every quantity the source states for it.',
    'find_applicable_evidence': 'Whether the source holds an experiment or result applicable to the proposed '
                                'annotation is open: read in document order from the starting window, grade what is '
                                'applicable, and declare with the exact examined spans what holds no applicable '
                                'evidence.',
}

# The requested-component arrays of the old assignment schema, under their old names. Each is optional: a
# commissioner asks for the families it wants returned.
REQUESTED_FIELDS = (
    'requested_concentration_window_components', 'requested_measurement_comparison_components',
    'requested_kinetic_summary_precision_components', 'requested_endpoint_signal_components',
    'requested_product_coupling_components', 'requested_measurement_validation_components',
    'requested_calibration_recovery_components', 'requested_rate_observation_components',
    'requested_rate_grid_components', 'requested_rate_replicate_components', 'requested_rate_components',
    'requested_quantity_components', 'requested_assay_components', 'requested_ratio_components',
    'requested_binding_components', 'requested_binding_model_components', 'requested_transport_components',
    'requested_figure_components', 'requested_amount_components', 'requested_optical_components',
    'requested_kinetic_components', 'requested_kinetic_model_components',
    'requested_binding_interaction_components', 'requested_binding_interaction_model_components',
    'requested_ion_discrimination_components', 'requested_channel_components',
    'requested_compiled_assay_components', 'requested_compiled_assay_components_v2',
    'requested_compiled_assay_components_v3', 'requested_assay_grading_components',
    'requested_a105_aggregation_components', 'requested_product_partition_components',
    'requested_completion_time_components', 'requested_active_site_components',
    'requested_parent_depletion_components', 'requested_stoichiometric_balance_components',
    'requested_ratio_source_components', 'requested_controlled_response_components',
    'requested_controlled_response_views', 'requested_controlled_response_component_keys',
    'requested_gel_components', 'requested_gel_views', 'requested_gel_component_keys')

PAGE_FORM = RecordForm({
    'version': DeclaredField('text', 'The page assignment version', 'page_assignment_v1'),
    'source_ref': Field('text', 'The source being read'),
    'representation': Field('text', 'The representation of the source read: text, original, stdout or stderr'),
    'artifact_ref': Field('text', "The source's artifact of that representation"),
    'question_context_refs': Field('list', 'References to the question context records'),
    'prior_delivery_refs': Field('list', 'References to prior deliveries'),
})
WINDOW_FORM = RecordForm({
    'source_ref': Field('text', "The window's source: the page's source"),
    'representation': Field('text', "The window's representation: the page's representation"),
    'offset': Field('integer', 'The UTF-8 byte offset where document-order reading starts, at least 0'),
    'limit': Field('integer', 'The UTF-8 byte length of the first window, at least 1'),
})
ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The assignment version', 'reading_assignment_v1'),
    'page': Field('record', 'The source being read', form=PAGE_FORM),
    'selection': Field('record', 'The one window where document-order reading starts', form=WINDOW_FORM),
    'literature_task': Field('record', 'The commissioned task and its explicit credit unit (literature_local_task_v1)'),
    'proposed_annotation_ref': Field('text', 'The proposed annotation the task answers'),
    **{name: Field('list', 'The requested components of one result family', required=False)
       for name in REQUESTED_FIELDS},
    # New fields the final form needs (the old code read them from the commissioning request, not the assignment).
    'scope': Field('record', "The fixed scope of the investigation: the parent's fixed subject and optional segments"),
    'record_refs': Field('record_refs', 'Every record this episode reads: the source, its artifact, the question '
                                        'context and prior delivery records, the sources the source derives from '
                                        'and the hypothesis the task answers'),
})


def task_schema():
    """The commissioned result and its explicit local credit unit (the old ``goal.task_schema``)."""
    yield_settings = obj({'kind': {'enum': ['accumulation', 'remaining_commissioned_credit']},
                          'cutoff': {'type': 'number', 'minimum': 0},
                          'uncertainty_alpha': {'type': 'number', 'exclusiveMinimum': 0, 'exclusiveMaximum': 1}})
    base = {'version': {'const': VERSION}, 'evidence_axis': {'const': 'A105'},
            'credit_unit': {'type': 'number', 'exclusiveMinimum': 0}, 'yield_settings': yield_settings}

    def task_object(properties):
        return obj(properties, required=[key for key in properties if key != 'yield_settings'])
    refs = {'type': 'array', 'items': REF, 'minItems': 1, 'uniqueItems': True}
    span = obj({'source_ref': REF, 'artifact_ref': REF, 'start': {'type': 'integer', 'minimum': 0},
                'end': {'type': 'integer', 'minimum': 1}})
    return {'anyOf': [
        task_object({**base, 'kind': {'const': 'verified_source_leads'}}),
        task_object({**base, 'kind': {'const': 'source_answer'}, 'answer_kind': {'const': 'assessment'},
                     'source_refs': refs}),
        task_object({**base, 'kind': {'const': 'source_answer'}, 'answer_kind': {'const': 'screening'},
                     'examined': {'type': 'array', 'minItems': 1, 'items': span}}),
        task_object({**base, 'kind': {'const': 'source_answer'}, 'answer_kind': {'const': 'measurement'},
                     'selection': quantity_population_schema(),
                     'components': {'type': 'array', 'minItems': 1, 'uniqueItems': True,
                                    'items': {'enum': ['reported_value', 'reported_spread',
                                                       'relative_reported_spread']}}}),
        task_object({**base, 'kind': {'const': 'a105_experiments'},
                     'experiments': {'type': 'array', 'minItems': 1,
                                     'items': obj({'experiment_ref': REF, 'assay_type': {'enum': list(ASSAY_TYPES)}})}}),
        task_object({**base, 'kind': {'const': 'a105_assembly'}, 'experiment_refs': refs,
                     'metrics': {'type': 'array', 'minItems': 1, 'uniqueItems': True,
                                 'items': {'enum': ['reliability', 'validity', 'relevance', 'attribution',
                                                    'overall']}}})]}


def task_key(task):
    """The key of the commissioned task: ``A105:<kind>[:<answer kind>]`` (the old ``goal._task_key``)."""
    name = {'a105_experiments': 'experiments', 'a105_assembly': 'assembly'}.get(task['kind'], task['kind'])
    if task['kind'] == 'source_answer':
        name += ':' + task['answer_kind']
    return task['evidence_axis'] + ':' + name


def validate_commission(task, assignment):
    """The old ``goal.validate_commission``: the task's experiments are distinct and its requested metrics and
    measurement components are among those the assignment requests."""
    if task['kind'] == 'a105_experiments':
        experiments = [item['experiment_ref'] for item in task['experiments']]
        if len(set(experiments)) != len(experiments):
            raise ContractError('literature_task_duplicate_experiment')
    if task['kind'] == 'a105_assembly' and not set(task['metrics']) <= set(
            assignment.get('requested_a105_aggregation_components', ())):
        raise ContractError('literature_task_requested_metrics_mismatch')
    if task.get('answer_kind') == 'measurement' and not set(task['components']) <= set(
            assignment.get('requested_quantity_components', ())):
        raise ContractError('literature_task_requested_measurement_mismatch')


def read_from_parent(assignment, message):
    """The assignment as the parent input, with the commissioner's objective (its vocabulary value and this
    episode's meaning of it; a value outside ``OBJECTIVES`` is a wrong commission and fails here). The old
    assignment's own checks are made here, where it is read: the
    page and window constraints, the task schema, the credit unit and the commission rules of the task."""
    page, window = assignment['page'], assignment['selection']
    for name, representation in (('page', page['representation']), ('window', window['representation'])):
        if representation not in REPRESENTATIONS:
            raise ValueError('a105_' + name + '_representation_unknown:' + repr(representation))
    if window['source_ref'] != page['source_ref']:
        raise ContractError('literature_reading_source_mismatch')
    if window['representation'] != page['representation']:
        raise ContractError('literature_reading_representation_mismatch')
    if window['offset'] < 0:
        raise ContractError('window_offset_must_be_a_natural_number')
    if window['limit'] < 1:
        raise ContractError('window_limit_must_be_positive')
    task = json.loads(json.dumps(assignment['literature_task']))
    validate_schema(task, task_schema())
    if type(task['credit_unit']) not in (int, float) or not math.isfinite(task['credit_unit']):
        raise ContractError('literature_finite_task_credit_unit_required')
    validate_commission(task, assignment)
    for span in task.get('examined', ()):
        if span['end'] <= span['start']:
            raise ContractError('literature_task_screening_span_invalid')
    answer = task.get('answer_kind')
    selected = (task.get('source_refs', []) + [span['source_ref'] for span in task.get('examined', [])]
                + ([task['selection']['source_ref']] if answer == 'measurement' else []))
    if any(ref != page['source_ref'] for ref in selected):
        raise ContractError('literature_task_outside_assigned_source')
    if answer == 'screening' and any(span['artifact_ref'] != page['artifact_ref'] for span in task['examined']):
        raise ContractError('literature_task_screening_artifact_mismatch')
    # The finite target of a completion controller: the commissioned credit unit per requested answer.
    answers = len(task['experiments']) if task['kind'] == 'a105_experiments' else 1
    parent_input = {'objective': {'value': message['objective'], 'meaning': OBJECTIVES[message['objective']]},
                    'version': assignment['version'], 'page': dict(page), 'selection': dict(window),
                    'literature_task': task, 'task_key': task_key(task),
                    'proposed_annotation_ref': assignment['proposed_annotation_ref'],
                    'scope': assignment['scope'], 'record_refs': list(assignment['record_refs']),
                    'completion_target': task['credit_unit'] * answers}
    parent_input['requested'] = {name: list(assignment[name]) for name in REQUESTED_FIELDS if name in assignment}
    return parent_input
