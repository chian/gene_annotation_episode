"""What the parent gives: the strategy assignment ``strategy_assignment_v1`` (the records that give the assigned
question its context and the earlier search results to build on), the commissioned literature task, the proposed
annotation, the requested components of the cell families this episode returns, the Store scope of the commission
and the records passed in custody. This is the only place the assignment is read.

The fields ``version``, ``question_context_refs`` and ``prior_search_refs`` are the old ``assignment_schema``
properties of the ``literature_strategy`` role (``strategy_assignment_v1`` with ``prior_search_refs``);
``literature_task``, ``proposed_annotation_ref`` and the ``requested_*`` arrays of the cell families are the old
properties of the same schema under their names. The three of the task kinds (``requested_assay_grading_components``,
``requested_a105_aggregation_components``, ``requested_quantity_components``) have their options; the arrays of the
other population families (``OTHER_REQUESTED``) are lists whose components the family's library checks where it
reads them. ``scope`` and ``received_record_refs`` are new fields: the old episode took the scope from its request
and the records it received from its binding context; the new commission names both.

Carried as episode functions (old ``goal.task_schema``, ``validate_commission``, ``commissioned_task`` and
``from_parent._validate_assignment``): the task schema, the finite credit unit, the distinct experiments, the
requested metrics and components, the screening spans. Not carried (a wrong commission fails, rule 1; the old report
contract and the Store checks are gone): the typed-return and return-component checks of ``commissioned_task``
against the parent's report contract, the reference checks against the Store (``_validate_assignment``: every
``*_refs`` field is held and ``prior_search_refs`` are sources), the proposed-annotation comparison with the
parent's, and the fill-in of ``credit_unit`` and ``yield_settings`` from the parent's yield binding (``credit_unit``
is a field of the commissioned task now; the cost and parameters are this episode's settings). The old page checks
(``assigned_page``) applied only where the assignment has a page, which a strategy assignment does not."""
import json
import math

from method_loop import DeclaredField, Field, RecordForm, SubsetField

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import (
    ASSAY_TYPES, COMPONENTS as ASSAY_GRADING_COMPONENTS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_aggregation import (
    COMPONENTS as AGGREGATION_COMPONENTS)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_quantity_storage import (
    COMPONENTS as QUANTITY_COMPONENTS, quantity_population_schema)
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import (
    ContractError, REF, obj, validate_schema)

VERSION = 'literature_local_task_v1'
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

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The strategy assignment version', 'strategy_assignment_v1'),
    'question_context_refs': Field('record_refs', 'Records giving the assigned question its context'),
    'prior_search_refs': Field('record_refs', 'The searches (provider search responses) earlier work returned, '
                               'which the search approach may build on'),
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
                   "the options are the family library's components, checked where the family is read)",
                   required=False) for name in OTHER_REQUESTED},
    'sheet_state_refs': Field('record_refs', 'The persisted subscoring-sheet states the commissioner holds before this '
                              'run (the whole sheet), passed on to the web search and its first page; absent for the '
                              'first run of a sheet', required=False),
    'examined_article_refs': Field('record_refs', 'The article sources a page of an earlier strategy run of this '
                                   'literature examination already examined, passed on to the web search so their hits '
                                   'are not offered again; absent when none was', required=False),
    'scope': Field('record', 'The Store scope of the commission (new field: old request scope)'),
    'received_record_refs': Field('record_refs', 'The earlier search-result sources and their artifacts, the proposed '
                                  'annotation and the records of the commissioned task, and every record the '
                                  'commissions to the child will name, passed in custody (new field: old '
                                  'binding-context received records)'),
})


def task_schema():
    """The commissioned result and its explicit local credit unit (the old ``goal.task_schema`` and
    ``task_schema_variants``, private copy)."""
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
    """The old ``goal._task_key``: ``<axis>:<name>`` where the name is the kind (``a105_experiments`` is
    ``experiments``, ``a105_assembly`` is ``assembly``) and, for a source answer, ``:<answer_kind>`` follows."""
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
            assignment.get(REQUESTED_AGGREGATION, ())):
        raise ContractError('literature_task_requested_metrics_mismatch')
    if task.get('answer_kind') == 'measurement' and not set(task['components']) <= set(
            assignment.get(REQUESTED_QUANTITY, ())):
        raise ContractError('literature_task_requested_measurement_mismatch')


def read_from_parent(assignment, message):
    """The parent input: the strategy assignment, the task, the proposed annotation, the requested components, the
    scope and the passed records. The old ``commissioned_task`` checks that need no Store and no report contract
    are made here."""
    task = json.loads(json.dumps(assignment['literature_task']))
    validate_schema(task, task_schema())
    if type(task['credit_unit']) not in (int, float) or not math.isfinite(task['credit_unit']):
        raise ContractError('literature_finite_task_credit_unit_required')
    validate_commission(task, assignment)
    for span in task.get('examined', ()):
        if span['end'] <= span['start']:
            raise ContractError('literature_task_screening_span_invalid')
    strategy = {name: assignment[name] for name in ('version', 'question_context_refs', 'prior_search_refs')}
    return {'strategy': strategy, 'task': task, 'task_key': task_key(task),
            'proposed_annotation_ref': assignment['proposed_annotation_ref'],
            'examined_article_refs': list(assignment['examined_article_refs'])
            if 'examined_article_refs' in assignment else [],
            'requested': {name: assignment[name] for name in REQUESTED if name in assignment},
            'scope': assignment['scope'], 'received_record_refs': assignment['received_record_refs'],
            'sheet_state_refs': list(assignment['sheet_state_refs']) if 'sheet_state_refs' in assignment else [],
            'message': message}
