"""The commissioned A105 literature task, its credit and its continuation.

One implementation for all seven A105 literature bindings. A literature episode
is commissioned with exactly one task (``literature_task``) about one proposed
annotation:

- ``verified_source_leads``: one credit unit per source verified as a relevant
  lead (own reasoning with a witnessed ``source_lead``, or a lead a child
  returned in its typed answer);
- ``source_answer`` / ``assessment``: one credit unit once a current retained
  assessment of the proposed annotation, anchored in an assigned source, is held;
- ``source_answer`` / ``screening``: one credit unit once the episode's own
  screened reasoning established, over every requested span, that the
  examined material holds no applicable experiment or result;
- ``source_answer`` / ``measurement``: one credit unit once a held quantity sheet
  for the selected source quantity populates every requested component;
- ``a105_experiments``: one credit unit per requested experiment graded with its
  purpose-specific assay-grading sheet and matched by a held retained assessment;
- ``a105_assembly``: one credit unit once a held main A105 sheet assembles the
  requested experiments' metrics from current grading sheets.

Credit is ``credit_unit * answers`` and is never clamped. The answer readers
read this episode's own recorded outcomes and the records it holds, never
another journal's tables. Continuation is the binding's own declaration for the
task: the central ``AccumulationYieldController`` for leads, and for a finite
answer the central ``CompletionYieldController`` whose completion target is the
commission's finite requested credit (the credit itself stays unclamped).
"""
from __future__ import annotations

import json
import math

from gene_annotation_episode.domain import ContractError
from yield_control import AccumulationYieldController, CompletionYieldController, YieldParameters

from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import REF, canonical, obj, plain, source_location_inputs, validate_schema

AXIS = 'A105'
VERSION = 'literature_local_task_v1'
YIELD_TASKS = frozenset(AXIS + ':' + task for task in
                        ('verified_source_leads', 'source_answer:assessment', 'source_answer:screening',
                         'source_answer:measurement', 'experiments', 'assembly'))
METRICS = ('reliability', 'validity', 'relevance', 'attribution', 'overall')
MEASUREMENT_COMPONENTS = ('reported_value', 'reported_spread', 'relative_reported_spread')


def task_key(task):
    name = {'a105_experiments': 'experiments', 'a105_assembly': 'assembly'}.get(task['kind'], task['kind'])
    if task['kind'] == 'source_answer':
        name += ':' + task['answer_kind']
    return task['evidence_axis'] + ':' + name


def yield_kind(task):
    return 'accumulation' if task['kind'] == 'verified_source_leads' else 'remaining_commissioned_credit'


def task_schema(*, commissioned):
    """The task schema; a commissioning parent omits the unit and settings the child binding declares."""
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_assay_grading import ASSAY_TYPES
    from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_quantity_storage import quantity_population_schema
    yield_settings = obj({'kind': {'enum': ['accumulation', 'remaining_commissioned_credit']},
                          'cutoff': {'type': 'number', 'minimum': 0, 'description': 'This commissioned episode stops '
                                     'when its available next-credit upper estimate is at or below this cutoff, '
                                     'measured in this task credit unit.'},
                          'uncertainty_alpha': {'type': 'number', 'exclusiveMinimum': 0, 'exclusiveMaximum': 1}})
    base = {'version': {'const': VERSION}, 'evidence_axis': {'const': AXIS},
            'credit_unit': {'type': 'number', 'exclusiveMinimum': 0}, 'yield_settings': yield_settings}

    def task_object(properties):
        optional = {'yield_settings'} if commissioned else {'yield_settings', 'credit_unit'}
        return obj(properties, required=[key for key in properties if key not in optional])
    refs = {'type': 'array', 'items': REF, 'minItems': 1, 'uniqueItems': True}
    span = obj({'source_ref': REF, 'artifact_ref': REF, 'start': {'type': 'integer', 'minimum': 0},
                'end': {'type': 'integer', 'minimum': 1}})
    return {'description': 'The commissioned A105 result. The child binding declares its credit unit and '
                           'continuation settings; A105 grading is automatic work within an interpretation, not an '
                           'episode-credit task.',
            'anyOf': [task_object({**base, 'kind': {'const': 'verified_source_leads'}}),
                      task_object({**base, 'kind': {'const': 'source_answer'}, 'answer_kind': {'const': 'assessment'},
                                   'source_refs': refs}),
                      task_object({**base, 'kind': {'const': 'source_answer'}, 'answer_kind': {'const': 'screening'},
                                   'examined': {'type': 'array', 'minItems': 1, 'items': span}}),
                      task_object({**base, 'kind': {'const': 'source_answer'},
                                   'answer_kind': {'const': 'measurement'}, 'selection': quantity_population_schema(),
                                   'components': {'type': 'array', 'minItems': 1, 'uniqueItems': True,
                                                  'items': {'enum': list(MEASUREMENT_COMPONENTS)}}}),
                      task_object({**base, 'kind': {'const': 'a105_experiments'},
                                   'experiments': {'type': 'array', 'minItems': 1, 'items': obj(
                                       {'experiment_ref': REF, 'assay_type': {'enum': list(ASSAY_TYPES)}})}}),
                      task_object({**base, 'kind': {'const': 'a105_assembly'}, 'experiment_refs': refs,
                                   'metrics': {'type': 'array', 'minItems': 1, 'uniqueItems': True,
                                               'items': {'enum': list(METRICS)}}})]}


def validate_yield_bindings(bindings):
    """The literature binding's exact task declarations, validated before any work."""
    if not isinstance(bindings, dict):
        raise ContractError('literature_yield_bindings_object_required')
    result = {}
    for key, declaration in bindings.items():
        if (key not in YIELD_TASKS or not isinstance(declaration, dict)
                or set(declaration) != {'credit_unit', 'kind', 'cutoff', 'uncertainty_alpha'}):
            raise ContractError('literature_yield_task_binding_invalid:' + str(key))
        expected = 'accumulation' if key.endswith(':verified_source_leads') else 'remaining_commissioned_credit'
        if declaration['kind'] != expected:
            raise ContractError('literature_yield_task_kind_mismatch:' + key)
        unit = declaration['credit_unit']
        if type(unit) not in (int, float) or not math.isfinite(unit) or unit <= 0:
            raise ContractError('literature_yield_credit_unit_invalid:' + key)
        try:
            parameters = YieldParameters(uncertainty_alpha=declaration['uncertainty_alpha'])
            if expected == 'accumulation':
                AccumulationYieldController('configuration', 0, declaration['cutoff'], parameters)
            else:
                CompletionYieldController('configuration', 0, declaration['cutoff'], unit, parameters)
        except (TypeError, ValueError) as error:
            raise ContractError('literature_yield_settings_invalid:' + key) from error
        result[key] = dict(declaration)
    return result


def commissioned_task(task, yield_bindings):
    """The commissioned task completed with this binding's declared unit and continuation settings."""
    if not isinstance(task, dict):
        raise ContractError('literature_original_task_required')
    validate_schema(task, task_schema(commissioned=False))
    key = task_key(task)
    declaration = yield_bindings.get(key)
    if declaration is None:
        raise ContractError('literature_yield_binding_missing_for_task:' + key)
    settings = {name: declaration[name] for name in ('kind', 'cutoff', 'uncertainty_alpha')}
    if ('credit_unit' in task and task['credit_unit'] != declaration['credit_unit']) or (
            'yield_settings' in task and task['yield_settings'] != settings):
        raise ContractError('literature_task_supplied_yield_binding_mismatch:' + key)
    completed = {**task, 'credit_unit': declaration['credit_unit'], 'yield_settings': settings}
    validate_schema(completed, task_schema(commissioned=True))
    for span in completed.get('examined', ()):
        if span['end'] <= span['start']:
            raise ContractError('literature_task_screening_span_invalid')
    if completed['kind'] == 'a105_experiments':
        experiments = [item['experiment_ref'] for item in completed['experiments']]
        if len(set(experiments)) != len(experiments):
            raise ContractError('literature_task_duplicate_experiment')
    return completed


def validate_commission(task, assignment):
    """A task whose typed answer is a requested sheet must request the components it answers with."""
    if task['kind'] == 'a105_assembly' and not set(task['metrics']) <= set(
            assignment.get('requested_a105_aggregation_components', ())):
        raise ContractError('literature_task_requested_metrics_mismatch')
    if task.get('answer_kind') == 'measurement' and not set(task['components']) <= set(
            assignment.get('requested_quantity_components', ())):
        raise ContractError('literature_task_requested_measurement_mismatch')


def task_sources(task):
    """The sources a task names (checked against an assigned page)."""
    return [*task.get('source_refs', []), *(span['source_ref'] for span in task.get('examined', [])),
            *([task['selection']['source_ref']] if task.get('answer_kind') == 'measurement' else [])]


def credit_policy(task):
    return {'kind': VERSION, 'task': task_key(task), 'credit_unit': task['credit_unit'],
            'unit': ('one_verified_source_for_original_question' if task['kind'] == 'verified_source_leads'
                     else 'one_graded_experiment' if task['kind'] == 'a105_experiments'
                     else 'one_answer_to_original_commission'),
            'revision_credit': False, 'activity_credit': False, 'annotation_support': 'separate'}


def maximum_credit(task):
    """The finite commissioned credit of an answer task."""
    return task['credit_unit'] * (len(task['experiments']) if task['kind'] == 'a105_experiments' else 1)


# -- source leads ---------------------------------------------------------------------------------------------------
def _resolve(value, aliases, reference_position=False):
    """Resolve same-action aliases in source-lead reference positions."""
    if reference_position and isinstance(value, str) and value.startswith('@'):
        if value[1:] not in aliases:
            raise ContractError('required_grading_unresolved_alias', detail={'reference': value})
        return aliases[value[1:]]
    if isinstance(value, dict):
        return {key: _resolve(child, aliases, key in ('ref', 'dependencies') or key.endswith('_ref')
                              or key.endswith('_refs')) for key, child in value.items()}
    if isinstance(value, list):
        return [_resolve(child, aliases, reference_position) for child in value]
    return value


def lead_schema():
    from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence.literature_assay_inputs import _witness_schema
    return obj({'proposed_annotation_ref': {**REF, 'x-reference-namespace': 'hypothesis'},
                'source_ref': {**REF, 'x-reference-namespace': 'source'},
                'subject_ref': {**REF, 'x-reference-namespace': 'reference'},
                'disposition': {'enum': ['relevant', 'not_relevant'],
                                'description': 'Whether the inspected source is a useful lead for this commissioned '
                                               'question. This is not evidence supporting or opposing the proposed '
                                               'annotation.'},
                'relevance_rationale': {'type': 'string', 'minLength': 1,
                                        'description': 'Explain the specific connection between the witnessed source '
                                                       'subject/result and the original question; a search hit or '
                                                       'matching title alone is not verification.'},
                'witness': _witness_schema()})


def validate_lead(store, task, proposed, received_refs, value, outcome):
    """Check the reasoning judgment's identity and its exact source witness."""
    from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence.literature_assay_inputs import _Sources
    if task['kind'] != 'verified_source_leads':
        raise ContractError('literature_lead_outside_original_search_task')
    value = _resolve(plain(value), outcome['aliases'])
    validate_schema(value, source_location_inputs(lead_schema()))
    if value['proposed_annotation_ref'] != proposed or value['witness']['source_ref'] != value['source_ref']:
        raise ContractError('literature_lead_question_or_source_mismatch')
    if not value['relevance_rationale'].strip():
        raise ContractError('literature_lead_relevance_rationale_required')
    known = {*received_refs, *outcome['record_refs']}
    if not {value['source_ref'], value['subject_ref'], proposed} <= known:
        raise ContractError('literature_lead_original_inputs_not_received')
    source = store._require(value['source_ref'], {'source'})
    subject = store._require(value['subject_ref'], {'reference'})
    if subject['source_ref'] != value['source_ref'] or not subject.get('anchor'):
        raise ContractError('literature_lead_subject_not_anchored_in_source')
    uri = (source.get('uri') or '').split('?', 1)[0].rstrip('/')
    if uri.endswith(('/search', '/esearch.fcgi')):
        raise ContractError('literature_lead_requires_acquired_source_not_search_page')

    def read_source(ref, representation):
        if ref != value['source_ref']:
            raise ContractError('literature_lead_source_mismatch')
        artifact = source.get('artifact_ref' if representation == 'original' else 'text_ref')
        if artifact is None:
            raise ContractError('literature_lead_source_representation_unavailable')
        return {'artifact_ref': artifact, 'content': store.get_artifact(artifact)}
    witness = _Sources(read_source).witness(value['witness'], 'source_lead.witness')
    anchor = subject['anchor']
    if anchor['artifact_ref'] != witness['artifact_ref'] or not (
            witness['start'] <= anchor['start'] < anchor['end'] <= witness['end']):
        raise ContractError('literature_lead_subject_outside_witness')
    return {**value, 'witness': {**value['witness'], 'quote': witness['quote']}}


def lead_dispositions(store, proposed, outcomes):
    """The latest disposition per source, from own reasoning and children's returned answers, in unit order."""
    from gene_annotation_episode.episodic_workflow.episode_support.findings.experimental_activity_evidence.scientific_findings import FindingIdentity
    normalizer, current = FindingIdentity(store), {}
    for outcome in outcomes:
        if outcome['status'] not in ('completed', 'partial'):
            continue
        if outcome['kind'] == 'reason':
            leads = [outcome['result']['literature_source_lead']] if 'literature_source_lead' in outcome['result'] else []
        elif outcome['kind'] == 'child':
            leads = outcome['answer'].get('source_lead_dispositions', [])
        else:
            leads = []
        for lead in leads:
            if lead['proposed_annotation_ref'] == proposed:
                current[canonical(normalizer.source(lead['source_ref']))] = lead
    return list(current.values())


# -- screening -------------------------------------------------------------------------------------------------------
def screening_answers(store, task, proposed, outcomes):
    """The no-applicable-evidence answer, once own screened reasoning covered every requested span."""
    if task.get('answer_kind') != 'screening':
        return []
    spans = []
    for outcome in outcomes:
        processing = outcome['result'].get('evidence_processing') if outcome['kind'] == 'reason' else None
        if (outcome['status'] not in ('completed', 'partial') or not isinstance(processing, dict)
                or processing.get('kind') != 'no_applicable_evidence' or not processing.get('reason')):
            continue
        for witness in processing['examined']:
            source = store.get(witness['source_ref'])
            artifact = source.get('artifact_ref' if witness['representation'] == 'original' else 'text_ref')
            spans.append({**witness, 'artifact_ref': artifact})
    for requested in task['examined']:
        covered = requested['start']
        intervals = sorted((span['start'], span['end']) for span in spans
                           if (span['source_ref'], span['artifact_ref']) == (requested['source_ref'],
                                                                             requested['artifact_ref']))
        for start, end in intervals:
            if start <= covered:
                covered = max(covered, end)
        if covered < requested['end']:
            return []
    return [{'proposed_annotation_ref': proposed, 'disposition': 'no_applicable_evidence',
             'examined': task['examined'], 'annotation_support': 'not_assessed'}]


# -- assessments, measurements, graded experiments and assembly ------------------------------------------------------
def _current_assessments(store, scope, proposed, known_refs):
    from gene_annotation_episode.episodic_workflow.episode_support.findings.experimental_activity_evidence.finding_validity import FindingValidity, target_eligible
    with FindingValidity(store, plain(scope)) as validity:
        return [record for record in validity.current_records()
                if record['id'] in known_refs and record['hypothesis_ref'] == proposed
                and record.get('investigation_finding', {}).get('status') == 'retained'
                and target_eligible(store, record, plain(scope))]


def assessment_answers(store, scope, task, proposed, known_refs):
    for record in _current_assessments(store, scope, proposed, known_refs):
        observation = store.get(record['observation_ref'])
        if observation['source_ref'] in task['source_refs'] and (
                observation.get('anchor') is not None or observation.get('visual_anchor') is not None):
            return [{'assessment_ref': record['id'], 'source_ref': observation['source_ref']}]
    return []


def measured_answers(populations, context, task, known_refs):
    repository = populations.repository('quantity')
    for ref in known_refs:
        source = populations.store.get(ref)
        if source.get('provider') != repository.provider:
            continue
        request = json.loads(populations.store.get_artifact(source['request_ref']))
        if request.get('arguments') != task['selection']:
            continue
        repository.read(ref)
        rows = repository.fact_cells(context, [ref], components=task['components'])
        if {row['component'] for row in rows} != set(task['components']):
            continue
        if all(row['status'] == 'populated'
               or row.get('unavailable_reason') in {'reported_spread_unavailable', 'zero_reported_value'}
               for row in rows):
            return [{'sheet_ref': ref, 'source_ref': task['selection']['source_ref'], 'components': task['components']}]
    return []


def graded_experiment_answers(populations, context, scope, task, proposed, known_refs):
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_required_grading import _matches_grading
    from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_sheet_updates import current_sheet_refs
    store, repository = populations.store, populations.repository('grading')
    assessments = _current_assessments(store, scope, proposed, known_refs)
    wanted = {item['experiment_ref']: item['assay_type'] for item in task['experiments']}
    completed = {}
    for ref in current_sheet_refs(store, context, repository.provider):
        if ref not in known_refs:
            continue
        arguments = repository.read(ref)['selection']
        experiment = arguments.get('experiment_ref')
        if arguments['assertion_ref'] != proposed or wanted.get(experiment) != arguments['assay_type']:
            continue
        if not repository.fact_cells(context, [ref], components=repository.components):
            continue
        for assessment in assessments:
            if _matches_grading(store, assessment['id'], arguments):
                completed[experiment] = {'experiment_ref': experiment, 'assessment_ref': assessment['id'],
                                         'sheet_ref': ref}
    return list(completed.values())


def assembled_answers(populations, context, task, proposed, known_refs):
    from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_sheet_updates import current_sheet_refs
    store = populations.store
    repository, grading = populations.repository('aggregation'), populations.repository('grading')
    current_grades = set(current_sheet_refs(store, context, grading.provider))
    for ref in current_sheet_refs(store, context, repository.provider):
        if ref not in known_refs:
            continue
        arguments = repository.read(ref)['selection']
        if arguments['assertion_ref'] != proposed or set(task['experiment_refs']) != {
                item['experiment_ref'] for item in arguments['experiments']}:
            continue
        selected = [experiment['metrics'][metric] for experiment in arguments['experiments']
                    for metric in task['metrics']]
        if any(item is None or item['sheet_ref'] not in current_grades for item in selected):
            continue
        cells = repository.fact_cells(context, [ref], components=task['metrics'])
        if {row['component'] for row in cells} == set(task['metrics']):
            return [{'sheet_ref': ref, 'experiment_refs': task['experiment_refs'], 'metrics': task['metrics']}]
    return []


def require_target_annotation(store, scope, proposed):
    """The proposed annotation is a hypothesis about this scope's subjects."""
    hypothesis = store._require(proposed, {'hypothesis'})
    if not store.reference_subset([proposed], plain(scope)):
        raise ContractError('literature_task_annotation_outside_scope')
    if not set(store._record_roots('hypothesis', hypothesis)).intersection(scope['subject_refs']):
        raise ContractError('literature_task_requires_target_annotation')


def task_credit(populations, context, task, proposed, outcomes, known_refs):
    """This episode's credit for its commissioned task: ``credit_unit * answers``, never clamped."""
    store, scope, known = populations.store, context.scope, list(dict.fromkeys(known_refs))
    with store.read_snapshot():
        if task['kind'] == 'verified_source_leads':
            items = [lead for lead in lead_dispositions(store, proposed, outcomes) if lead['disposition'] == 'relevant']
        elif task['kind'] == 'a105_experiments':
            items = graded_experiment_answers(populations, context, scope, task, proposed, set(known))
        elif task['kind'] == 'a105_assembly':
            items = assembled_answers(populations, context, task, proposed, set(known))
        elif task['answer_kind'] == 'screening':
            items = screening_answers(store, task, proposed, outcomes)
        elif task['answer_kind'] == 'assessment':
            items = assessment_answers(store, scope, task, proposed, set(known))
        elif task['answer_kind'] == 'measurement':
            items = measured_answers(populations, context, task, known)
        else:
            raise ContractError('literature_a105_task_kind_unrecognized')
    credit = task['credit_unit'] * len(items)
    if not math.isfinite(credit):
        raise ContractError('literature_finite_task_credit_required')
    return {'credit': credit, 'proposed_annotation_ref': proposed, 'policy': credit_policy(task),
            'task_status': 'answered' if items else 'unanswered', 'source_contributions': items}


# -- continuation ----------------------------------------------------------------------------------------------------
def task_controller(task, epoch, initial_credit):
    """The central yield controller the completed task's declared settings select."""
    settings = task['yield_settings']
    if settings['kind'] != yield_kind(task):
        raise ContractError('literature_original_task_yield_binding_mismatch:' + task_key(task))
    parameters = YieldParameters(uncertainty_alpha=settings['uncertainty_alpha'])
    if task['kind'] == 'verified_source_leads':
        return AccumulationYieldController(epoch, initial_credit, settings['cutoff'], parameters)
    capacity = maximum_credit(task)
    if not math.isfinite(capacity) or initial_credit > capacity:
        raise ContractError('literature_commissioned_credit_capacity_invalid')
    return CompletionYieldController(epoch, initial_credit, settings['cutoff'], capacity, parameters)


__all__ = ['METRICS', 'VERSION', 'YIELD_TASKS',
           'commissioned_task', 'credit_policy', 'lead_dispositions', 'lead_schema', 'maximum_credit',
           'require_target_annotation', 'screening_answers', 'task_controller', 'task_credit', 'task_key',
           'task_schema', 'task_sources', 'validate_commission', 'validate_lead', 'validate_yield_bindings',
           'yield_kind']
