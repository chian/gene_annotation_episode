"""A104 credit for an explicitly commissioned experimental result."""
import math
from yield_control import AccumulationYieldController, CompletionYieldController, YieldParameters
from gene_annotation_episode.episodic_workflow.episode_support.forms.evolutionary_history_evidence.communication import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.domain import ContractError, REF, obj, validate_schema
VERSION = 'literature_local_task_v1'
SCREENING = 'literature_screening_answers'
LEADS = 'literature_source_lead_dispositions'
YIELD_TASKS = frozenset((f'{axis}:{task}' for axis in ('A105', 'A106', 'A108') for task in ('verified_source_leads', 'source_answer:assessment', 'source_answer:screening'))) | frozenset(('A105:source_answer:measurement', 'A105:experiments', 'A105:assembly'))

def _yield_kind(task):
    return 'accumulation' if task['kind'] == 'verified_source_leads' else 'remaining_commissioned_credit'

def _task_key(task):
    name = {'a105_experiments': 'experiments', 'a105_assembly': 'assembly'}.get(task['kind'], task['kind'])
    if task['kind'] == 'source_answer':
        name += ':' + task['answer_kind']
    return task['evidence_axis'] + ':' + name

def _resolve(value, aliases, reference_position=False):
    """Resolve original-action aliases in source-lead reference positions."""
    if reference_position and isinstance(value, str) and value.startswith('@'):
        if value[1:] not in aliases:
            raise ContractError('required_grading_unresolved_alias', detail={'reference': value})
        return aliases[value[1:]]
    if isinstance(value, dict):
        return {key: _resolve(child, aliases, key in ('ref', 'dependencies') or key.endswith('_ref') or key.endswith('_refs')) for key, child in value.items()}
    if isinstance(value, list):
        return [_resolve(child, aliases, reference_position) for child in value]
    return value

def validate_yield_bindings(bindings):
    """Validate this literature episode's exact task declarations before work."""
    if not isinstance(bindings, dict):
        raise ContractError('literature_yield_bindings_object_required')
    result = {}
    for key, declaration in bindings.items():
        if key not in YIELD_TASKS or not isinstance(declaration, dict) or set(declaration) != {'credit_unit', 'kind', 'cutoff', 'uncertainty_alpha'}:
            raise ContractError('literature_yield_task_binding_invalid:' + str(key))
        expected_kind = 'accumulation' if key.endswith(':verified_source_leads') else 'remaining_commissioned_credit'
        if declaration['kind'] != expected_kind:
            raise ContractError('literature_yield_task_kind_mismatch:' + key)
        unit = declaration['credit_unit']
        if type(unit) not in (int, float) or not math.isfinite(unit) or unit <= 0:
            raise ContractError('literature_yield_credit_unit_invalid:' + key)
        try:
            parameters = YieldParameters(uncertainty_alpha=declaration['uncertainty_alpha'])
            if expected_kind == 'accumulation':
                AccumulationYieldController('configuration', 0, declaration['cutoff'], parameters)
            else:
                CompletionYieldController('configuration', 0, declaration['cutoff'], unit, parameters)
        except (TypeError, ValueError) as error:
            raise ContractError('literature_yield_settings_invalid:' + key) from error
        result[key] = dict(declaration)
    return result

def lead_schema():
    from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.evolutionary_history_evidence.literature_assay_inputs import _witness_schema
    return obj({'proposed_annotation_ref': {**REF, 'x-reference-namespace': 'hypothesis'}, 'source_ref': {**REF, 'x-reference-namespace': 'source'}, 'subject_ref': {**REF, 'x-reference-namespace': 'reference'}, 'disposition': {'enum': ['relevant', 'not_relevant'], 'description': 'Whether the inspected source is a useful lead for this commissioned question. This is not evidence supporting or opposing the proposed annotation.'}, 'relevance_rationale': {'type': 'string', 'minLength': 1, 'description': 'Explain the specific connection between the witnessed source subject/result and the original question; a search hit or matching title alone is not verification.'}, 'witness': _witness_schema()})

def lead_return_schema():
    item = lead_schema()
    for name in ('proposed_annotation_ref', 'source_ref', 'subject_ref'):
        item['properties'][name]['format'] = 'reference'
    witness = item['properties']['witness']['properties']
    witness['source_ref'] = {**witness['source_ref'], 'format': 'reference'}
    return {'type': 'array', 'x-source': LEADS, 'items': item}

def screening_schema():
    return {'type': 'array', 'x-source': SCREENING, 'items': obj({'proposed_annotation_ref': {**REF, 'format': 'reference', 'x-reference-namespace': 'hypothesis'}, 'disposition': {'const': 'no_applicable_evidence'}, 'examined': {'type': 'array', 'items': obj({'source_ref': {**REF, 'format': 'reference', 'x-reference-namespace': 'source'}, 'artifact_ref': {**REF, 'format': 'reference', 'x-reference-namespace': 'artifact'}, 'start': {'type': 'integer', 'minimum': 0}, 'end': {'type': 'integer', 'minimum': 1}})}, 'annotation_support': {'const': 'not_assessed'}})}

def task_schema():
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_credit_policy import task_schema_variants
    yield_settings = obj({'kind': {'enum': ['accumulation', 'remaining_commissioned_credit']}, 'cutoff': {'type': 'number', 'minimum': 0, 'description': 'This commissioned episode stops when its available next-credit upper estimate is at or below this cutoff, measured in this task credit unit.'}, 'uncertainty_alpha': {'type': 'number', 'exclusiveMinimum': 0, 'exclusiveMaximum': 1}})
    base = {'version': {'const': VERSION}, 'evidence_axis': {'enum': ['A105', 'A106', 'A108']}, 'credit_unit': {'type': 'number', 'exclusiveMinimum': 0}, 'yield_settings': yield_settings}

    def task_object(properties):
        return obj(properties, required=[key for key in properties if key != 'yield_settings'])
    refs = {'type': 'array', 'items': REF, 'minItems': 1, 'uniqueItems': True}
    span = obj({'source_ref': REF, 'artifact_ref': REF, 'start': {'type': 'integer', 'minimum': 0}, 'end': {'type': 'integer', 'minimum': 1}})
    return {'description': 'The original commissioned result and its explicit local credit unit. Select only a task whose typed result is requested by the original return contract. A106/A108 score computation is automatic work, not an episode-credit task.', 'anyOf': [task_object({**base, 'kind': {'const': 'verified_source_leads'}}), task_object({**base, 'kind': {'const': 'source_answer'}, 'answer_kind': {'const': 'assessment'}, 'source_refs': refs}), task_object({**base, 'kind': {'const': 'source_answer'}, 'answer_kind': {'const': 'screening'}, 'examined': {'type': 'array', 'minItems': 1, 'items': span}}), *task_schema_variants(base, task_object, refs)]}

def _return_sources(schema):
    if isinstance(schema, dict):
        if isinstance(schema.get('x-source'), str):
            yield schema['x-source']
        for value in schema.values():
            yield from _return_sources(value)
    elif isinstance(schema, list):
        for value in schema:
            yield from _return_sources(value)

def _return_components(schema, namespace):
    if isinstance(schema, dict):
        if schema.get('x-source') == namespace:
            component = schema.get('items', {}).get('properties', {}).get('component', {})
            yield set(component.get('enum', [component['const']] if 'const' in component else []))
        for value in schema.values():
            yield from _return_components(value, namespace)
    elif isinstance(schema, list):
        for value in schema:
            yield from _return_components(value, namespace)

def commissioned_task(context):
    assignment, request = (plain(context.assignment), plain(context.request))
    task = assignment.get('literature_task')
    if task is None:
        raise ContractError('literature_original_task_credit_required')
    validate_schema(task, task_schema())
    if type(task['credit_unit']) not in (int, float) or not math.isfinite(task['credit_unit']):
        raise ContractError('literature_finite_task_credit_unit_required')
    proposed = assignment.get('proposed_annotation_ref')
    if not isinstance(proposed, str):
        raise ContractError('literature_original_proposed_annotation_required')
    if not request.get('goal') or not request.get('report_contract') or request.get('message', {}).get('episode_assignment') != assignment:
        raise ContractError('literature_task_original_commission_mismatch')
    schema = request['report_contract']['measurements']['schema']
    sources = set(_return_sources(schema))
    kind, answer = (task['kind'], task.get('answer_kind'))
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading import literature_credit_policy as a104_credit
    required = LEADS if kind == 'verified_source_leads' else 'changed_assessment_refs' if answer == 'assessment' else SCREENING if answer == 'screening' else a104_credit.required_source(task)
    if required is not None and required not in sources:
        raise ContractError('literature_task_typed_return_mismatch')
    selected = task.get('metrics', task.get('components'))
    if selected is not None and (not any((set(selected) <= values for values in _return_components(schema, required)))):
        raise ContractError('literature_task_return_components_mismatch')
    a104_credit.validate_commission(task, assignment)
    for span in task.get('examined', ()):
        if span['end'] <= span['start']:
            raise ContractError('literature_task_screening_span_invalid')
    assigned_page = assignment.get('page', assignment if context.role == 'literature_page' else None)
    selected_sources = task.get('source_refs', []) + [span['source_ref'] for span in task.get('examined', [])] + ([task['selection']['source_ref']] if answer == 'measurement' else [])
    if assigned_page is not None and any((ref != assigned_page['source_ref'] for ref in selected_sources)):
        raise ContractError('literature_task_outside_assigned_source')
    if assigned_page is not None and answer == 'screening' and any((span['artifact_ref'] != assigned_page['artifact_ref'] for span in task['examined'])):
        raise ContractError('literature_task_screening_artifact_mismatch')
    return (task, proposed)

def continuation_task(context):
    task, _ = commissioned_task(context)
    return _task_key(task)

def _private_yield_controller(context, initial_credit, epoch, declaration):
    task, _ = commissioned_task(context)
    settings = task.get('yield_settings')
    if settings is None:
        raise ContractError('literature_original_task_yield_settings_required')
    if task['credit_unit'] != declaration['credit_unit'] or settings != {key: declaration[key] for key in ('kind', 'cutoff', 'uncertainty_alpha')} or settings['kind'] != _yield_kind(task):
        raise ContractError('literature_original_task_yield_binding_mismatch:' + _task_key(task))
    cutoff = settings['cutoff']
    parameters = YieldParameters(uncertainty_alpha=settings['uncertainty_alpha'])
    if task['kind'] == 'verified_source_leads':
        return AccumulationYieldController(epoch, initial_credit, cutoff, parameters)
    maximum_credit = task['credit_unit'] * (len(task['experiments']) if task['kind'] == 'a105_experiments' else 1)
    if not math.isfinite(maximum_credit) or initial_credit > maximum_credit:
        raise ContractError('literature_commissioned_credit_capacity_invalid')
    return CompletionYieldController(epoch, initial_credit, cutoff, maximum_credit, parameters)

