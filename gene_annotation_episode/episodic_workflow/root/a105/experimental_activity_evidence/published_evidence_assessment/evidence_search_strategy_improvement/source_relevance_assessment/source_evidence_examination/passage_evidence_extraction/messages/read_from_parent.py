"""What the parent gives: the reading assignment ``reading_assignment_v1`` (the page of one source and the spans to
read), the commissioned literature task, the proposed annotation, the requested components of the cell families
this episode returns, the Store scope of the commission and the records passed in custody. This is the only place
the assignment is read.

``version``, ``page``, ``selection``, ``literature_task`` and ``proposed_annotation_ref`` are the old
assignment's properties under their names (old ``from_parent.py`` ``LiteratureAssignment.assignment_schema``),
and so are the ``requested_*`` arrays of the cell families this episode returns: the three of the task kinds
(``requested_assay_grading_components``, ``requested_a105_aggregation_components``,
``requested_quantity_components``) with their options, and the arrays of the other population families
(``OTHER_REQUESTED``) as lists whose components the family's library checks where it reads them. ``scope`` and
``received_record_refs`` are new fields: the old episode took the scope from its request and the records it
received from its binding context; the new commission names both.

Carried as episode functions (old ``prepare_assignment`` / ``_validate_assignment``): the span-against-page
agreement. Not carried (a wrong commission fails, rule 1): the page and parent-page checks against the Store, the
task-schema and requested-component cross-checks of ``commissioned_task`` / ``validate_commission``, and the
fill-in of ``credit_unit`` and ``yield_settings`` from the parent's yield binding (``credit_unit`` is a field of
the commissioned task now; the cutoff and alpha are this episode's settings)."""
import math

from method_loop import ChoiceField, DeclaredField, Field, RecordForm, SubsetField

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import (
    COMPONENTS as ASSAY_GRADING_COMPONENTS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_aggregation import (
    COMPONENTS as AGGREGATION_COMPONENTS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_quantity_storage import (
    COMPONENTS as QUANTITY_COMPONENTS)

REPRESENTATIONS = ('text', 'original', 'stdout', 'stderr')
REQUESTED_ASSAY_GRADING = 'requested_assay_grading_components'
REQUESTED_AGGREGATION = 'requested_a105_aggregation_components'
REQUESTED_QUANTITY = 'requested_quantity_components'
OTHER_REQUESTED = (
    'requested_concentration_window_components',
    'requested_measurement_comparison_components',
    'requested_kinetic_summary_precision_components',
    'requested_rate_grid_components',
    'requested_rate_observation_components',
    'requested_calibration_recovery_components',
    'requested_product_coupling_components',
    'requested_measurement_validation_components',
    'requested_rate_replicate_components',
    'requested_rate_components',
    'requested_assay_components',
    'requested_ratio_components',
    'requested_binding_components',
    'requested_binding_model_components',
    'requested_transport_components',
    'requested_endpoint_signal_components',
    'requested_figure_components',
    'requested_amount_components',
    'requested_optical_components',
    'requested_kinetic_components',
    'requested_kinetic_model_components',
    'requested_binding_interaction_model_components',
    'requested_binding_interaction_components',
    'requested_ion_discrimination_components',
    'requested_channel_components',
    'requested_compiled_assay_components',
    'requested_compiled_assay_components_v2',
    'requested_compiled_assay_components_v3',
    'requested_parent_depletion_components',
    'requested_stoichiometric_balance_components',
    'requested_product_partition_components',
    'requested_completion_time_components',
    'requested_active_site_components',
    'requested_ratio_source_components',
    'requested_controlled_response_components',
    'requested_controlled_response_views',
    'requested_controlled_response_component_keys',
    'requested_gel_components',
    'requested_gel_views',
    'requested_gel_component_keys',
)
REQUESTED = (REQUESTED_ASSAY_GRADING, REQUESTED_AGGREGATION, REQUESTED_QUANTITY, *OTHER_REQUESTED)

PAGE_FORM = RecordForm({
    'version': DeclaredField('text', 'The page assignment version', 'page_assignment_v1'),
    'source_ref': Field('text', 'The source being read'),
    'representation': ChoiceField('text', 'The representation of the source that is read', REPRESENTATIONS),
    'artifact_ref': Field('text', "The source's artifact for that representation"),
    'question_context_refs': Field('record_refs', 'Records giving the assigned question its context'),
    'prior_delivery_refs': Field('record_refs', 'Records delivered by earlier readings of this source'),
})
WINDOW_FORM = RecordForm({
    'source_ref': Field('text', 'The source of the passage; the page source'),
    'representation': ChoiceField('text', 'The representation the offsets count in', REPRESENTATIONS),
    'offset': Field('integer', 'First byte of the passage (0 or more)'),
    'limit': Field('integer', 'Bytes of the passage (1 or more)'),
})
SELECTION_FORM = RecordForm({
    'spans': Field('list', 'The passages to investigate: one or more windows', items=WINDOW_FORM),
})
ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The reading assignment version', 'reading_assignment_v1'),
    'page': Field('record', 'The source being read', form=PAGE_FORM),
    'selection': Field('record', 'The passages of that source to investigate', form=SELECTION_FORM),
    'literature_task': Field('record', 'The commissioned literature task: its kind (verified_source_leads, '
                             'source_answer, a105_experiments or a105_assembly), evidence_axis A105, credit_unit '
                             'and, for a source answer, answer_kind with its source_refs (assessment), examined '
                             'spans (screening) or selection and components (measurement); for a105_experiments '
                             'the experiments (experiment_ref, assay_type), for a105_assembly the experiment_refs '
                             'and metrics'),
    'proposed_annotation_ref': Field('text', 'The proposed annotation the commissioned question is about'),
    REQUESTED_ASSAY_GRADING: SubsetField('text', 'The assay-grading components the parent wants returned',
                                         ASSAY_GRADING_COMPONENTS, required=False),
    REQUESTED_AGGREGATION: SubsetField('text', 'The A105 aggregation components the parent wants returned',
                                       AGGREGATION_COMPONENTS, required=False),
    REQUESTED_QUANTITY: SubsetField('text', 'The quantity components the parent wants returned',
                                    QUANTITY_COMPONENTS, required=False),
    **{name: Field('list', 'The components of this cell family the parent wants returned (old assignment property; '
                   'the options are the family library\'s components, checked where the family is read)', required=False)
       for name in OTHER_REQUESTED},
    'scope': Field('record', 'The Store scope of the commission (new field: old request scope)'),
    'received_record_refs': Field('record_refs', 'The source, its artifact, the sources it derives from, the '
                                  'proposed annotation and the records of the commissioned task, passed in custody '
                                  '(new field: old binding-context received records)'),
})

TASK_KINDS = ('verified_source_leads', 'source_answer', 'a105_experiments', 'a105_assembly')
ANSWER_KINDS = ('assessment', 'screening', 'measurement')


def task_key(task):
    """The old ``_task_key``: ``<axis>:<name>`` where the name is the kind (``a105_experiments`` is
    ``experiments``, ``a105_assembly`` is ``assembly``) and, for a source answer, ``:<answer_kind>`` follows."""
    name = {'a105_experiments': 'experiments', 'a105_assembly': 'assembly'}.get(task['kind'], task['kind'])
    if task['kind'] == 'source_answer':
        name += ':' + task['answer_kind']
    return task['evidence_axis'] + ':' + name


def read_from_parent(assignment, message):
    """The parent input: the page, the spans, the task, the proposed annotation, the requested components, the
    scope and the passed records, each span checked against the page."""
    page, spans = assignment['page'], assignment['selection']['spans']
    if not spans:
        raise ValueError('reading_assignment_requires_a_span')
    for window in spans:
        if window['source_ref'] != page['source_ref']:
            raise ValueError('literature_reading_source_mismatch')
        if window['representation'] != page['representation']:
            raise ValueError('literature_reading_representation_mismatch')
        if window['offset'] < 0 or window['limit'] < 1:
            raise ValueError('literature_reading_window_out_of_range')
    task = assignment['literature_task']
    if task.get('kind') not in TASK_KINDS or (task['kind'] == 'source_answer'
                                              and task.get('answer_kind') not in ANSWER_KINDS):
        raise ValueError('literature_original_task_invalid')
    if task.get('evidence_axis') != 'A105':
        raise ValueError('literature_original_task_invalid')
    unit = task.get('credit_unit')
    if type(unit) not in (int, float) or not math.isfinite(unit) or not unit > 0:
        raise ValueError('literature_finite_task_credit_unit_required')
    if task['kind'] == 'a105_experiments':
        experiments = [item['experiment_ref'] for item in task['experiments']]
        if not experiments or len(set(experiments)) != len(experiments):
            raise ValueError('literature_task_duplicate_experiment')
    return {'page': page, 'spans': spans, 'task': task, 'task_key': task_key(task),
            'proposed_annotation_ref': assignment['proposed_annotation_ref'],
            'requested': {name: assignment[name] for name in REQUESTED if name in assignment},
            'scope': assignment['scope'], 'received_record_refs': assignment['received_record_refs'],
            'message': message}
