"""The commissioned A106 literature task, its credit and its continuation.

One implementation for all seven A106 literature bindings. A literature
episode is commissioned with exactly one
task (``literature_task``) about one proposed annotation:

- ``verified_source_leads``: one credit unit per source verified as a relevant
  lead (own reasoning with a witnessed ``source_lead``, or a lead a child
  returned in its typed answer);
- ``source_answer`` / ``assessment``: one credit unit once a current retained
  assessment of the proposed annotation, anchored in an assigned source, is
  held by the episode;
- ``source_answer`` / ``screening``: one credit unit once the episode's own
  screened reasoning established, over every requested span, that the examined
  material holds no applicable observation.

Credit is ``credit_unit * answers`` and is never clamped. The answer readers
read this episode's own recorded outcomes (``outcome.<position>``) and the
findings its children returned.

Continuation is the binding's own declaration for the task: the central
``AccumulationYieldController`` for leads, and for a finite answer the central
``CompletionYieldController`` whose completion target is the commission's
finite requested credit (the credit itself stays unclamped).
"""
from __future__ import annotations

import math

from yield_control import AccumulationYieldController, CompletionYieldController, YieldParameters

from gene_annotation_episode.episodic_workflow.episode_support.forms.perturbation_evidence.communication import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.domain import REF, ContractError, canonical, obj, source_location_inputs, validate_schema

VERSION = 'literature_local_task_v1'
YIELD_TASKS = frozenset('A106:' + task for task in
                        ('verified_source_leads', 'source_answer:assessment', 'source_answer:screening'))


def task_key(task):
    name = task['kind']
    if task['kind'] == 'source_answer':
        name += ':' + task['answer_kind']
    return task['evidence_axis'] + ':' + name


def yield_kind(task):
    return 'accumulation' if task['kind'] == 'verified_source_leads' else 'remaining_commissioned_credit'


def task_schema(*, commissioned):
    """The task schema; a commissioning parent omits the unit and settings the child binding declares."""
    yield_settings = obj({'kind': {'enum': ['accumulation', 'remaining_commissioned_credit']},
                          'cutoff': {'type': 'number', 'minimum': 0, 'description': 'This commissioned episode stops '
                                     'when its available next-credit upper estimate is at or below this cutoff, '
                                     'measured in this task credit unit.'},
                          'uncertainty_alpha': {'type': 'number', 'exclusiveMinimum': 0, 'exclusiveMaximum': 1}})
    base = {'version': {'const': VERSION}, 'evidence_axis': {'const': 'A106'},
            'credit_unit': {'type': 'number', 'exclusiveMinimum': 0}, 'yield_settings': yield_settings}

    def task_object(properties):
        optional = {'yield_settings'} if commissioned else {'yield_settings', 'credit_unit'}
        return obj(properties, required=[key for key in properties if key not in optional])
    refs = {'type': 'array', 'items': REF, 'minItems': 1, 'uniqueItems': True}
    span = obj({'source_ref': REF, 'artifact_ref': REF, 'start': {'type': 'integer', 'minimum': 0},
                'end': {'type': 'integer', 'minimum': 1}})
    return {'description': 'The commissioned A106 result. The child binding declares its credit unit and '
                           'continuation settings; A106 score computation is automatic work, not an episode-credit '
                           'task.',
            'anyOf': [task_object({**base, 'kind': {'const': 'verified_source_leads'}}),
                      task_object({**base, 'kind': {'const': 'source_answer'}, 'answer_kind': {'const': 'assessment'},
                                   'source_refs': refs}),
                      task_object({**base, 'kind': {'const': 'source_answer'}, 'answer_kind': {'const': 'screening'},
                                   'examined': {'type': 'array', 'minItems': 1, 'items': span}})]}


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
    return completed


def credit_policy(task):
    return {'kind': VERSION, 'task': task_key(task), 'credit_unit': task['credit_unit'],
            'unit': ('one_verified_source_for_original_question' if task['kind'] == 'verified_source_leads'
                     else 'one_answer_to_original_commission'),
            'revision_credit': False, 'activity_credit': False, 'annotation_support': 'separate'}


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
    from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.literature_commission_contracts import lead_schema as schema
    return schema()


def validate_lead(store, task, proposed, received_refs, value, outcome):
    """Check the reasoning judgment's identity and its exact source witness."""
    from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.perturbation_evidence.literature_assay_inputs import _Sources
    if task['kind'] != 'verified_source_leads':
        raise ContractError('literature_lead_outside_original_search_task')
    value = _resolve(plain(value), outcome.get('aliases', {}))
    validate_schema(value, source_location_inputs(lead_schema()))
    if value['proposed_annotation_ref'] != proposed or value['witness']['source_ref'] != value['source_ref']:
        raise ContractError('literature_lead_question_or_source_mismatch')
    if not value['relevance_rationale'].strip():
        raise ContractError('literature_lead_relevance_rationale_required')
    known = {*received_refs, *outcome.get('record_refs', [])}
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
    """The latest disposition per source, from own reasoning and children's returned findings, in unit order."""
    from gene_annotation_episode.episodic_workflow.episode_support.findings.perturbation_evidence.scientific_findings import FindingIdentity
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


# -- assessment ------------------------------------------------------------------------------------------------------
def assessment_answers(store, scope, task, proposed, known_refs):
    from gene_annotation_episode.episodic_workflow.episode_support.findings.perturbation_evidence.finding_validity import FindingValidity, target_eligible
    with FindingValidity(store, plain(scope)) as validity:
        for record in validity.current_records():
            if (record['id'] in known_refs and record['hypothesis_ref'] == proposed
                    and record.get('investigation_finding', {}).get('status') == 'retained'
                    and target_eligible(store, record, plain(scope))):
                observation = store.get(record['observation_ref'])
                if observation['source_ref'] in task['source_refs'] and (
                        observation.get('anchor') is not None or observation.get('visual_anchor') is not None):
                    return [{'assessment_ref': record['id'], 'source_ref': observation['source_ref']}]
    return []


def require_target_annotation(store, scope, proposed):
    """The proposed annotation is a hypothesis about this scope's subjects."""
    hypothesis = store._require(proposed, {'hypothesis'})
    if not store.reference_subset([proposed], plain(scope)):
        raise ContractError('literature_task_annotation_outside_scope')
    if not set(store._record_roots('hypothesis', hypothesis)).intersection(scope['subject_refs']):
        raise ContractError('literature_task_requires_target_annotation')


def task_credit(store, scope, task, proposed, outcomes, known_refs):
    """This episode's credit for its commissioned task: ``credit_unit * answers``, never clamped."""
    with store.read_snapshot():
        if task['kind'] == 'verified_source_leads':
            items = [lead for lead in lead_dispositions(store, proposed, outcomes) if lead['disposition'] == 'relevant']
        elif task['answer_kind'] == 'screening':
            items = screening_answers(store, task, proposed, outcomes)
        elif task['answer_kind'] == 'assessment':
            items = assessment_answers(store, scope, task, proposed, set(known_refs))
        else:
            raise ContractError('literature_a106_task_kind_unrecognized')
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
    maximum_credit = task['credit_unit']
    if not math.isfinite(maximum_credit) or initial_credit > maximum_credit:
        raise ContractError('literature_commissioned_credit_capacity_invalid')
    return CompletionYieldController(epoch, initial_credit, settings['cutoff'], maximum_credit, parameters)


__all__ = ['VERSION', 'YIELD_TASKS',
           'commissioned_task', 'credit_policy', 'lead_dispositions', 'lead_schema', 'require_target_annotation',
           'screening_answers', 'task_controller', 'task_credit', 'task_key', 'task_schema', 'validate_lead',
           'validate_yield_bindings', 'yield_kind']
