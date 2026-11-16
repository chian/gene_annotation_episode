"""A104 credit for an explicitly commissioned experimental result."""
from dataclasses import dataclass, replace
import json
import math
import heapq
from .communication import plain
from .domain import ContractError, REF, canonical, identity, obj, validate_schema
from .numerical import NumericBand, STATUS_NORMAL, YieldController, YieldEstimate, YieldParameters, estimate_score_yield
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
            YieldController('configuration', 0, declaration['cutoff'], YieldParameters(uncertainty_alpha=declaration['uncertainty_alpha']))
        except (TypeError, ValueError) as error:
            raise ContractError('literature_yield_settings_invalid:' + key) from error
        result[key] = dict(declaration)
    return result

def lead_schema():
    from .literature_assay_inputs import _witness_schema
    return obj({'proposed_annotation_ref': {**REF, 'x-reference-namespace': 'hypothesis'}, 'source_ref': {**REF, 'x-reference-namespace': 'source'}, 'subject_ref': {**REF, 'x-reference-namespace': 'reference'}, 'disposition': {'enum': ['relevant', 'not_relevant'], 'description': 'Whether the inspected source is a useful lead for this commissioned question. This is not evidence supporting or opposing the proposed annotation.'}, 'relevance_rationale': {'type': 'string', 'minLength': 1, 'description': 'Explain the specific connection between the witnessed source subject/result and the original question; a search hit or matching title alone is not verification.'}, 'witness': _witness_schema()})

def lead_return_schema():
    item = lead_schema()
    for name in ('proposed_annotation_ref', 'source_ref', 'subject_ref'):
        item['properties'][name]['format'] = 'reference'
    witness = item['properties']['witness']['properties']
    witness['source_ref'] = {**witness['source_ref'], 'format': 'reference'}
    return {'type': 'array', 'x-source': LEADS, 'items': item}

def validate_lead(store, context, value, outcome):
    """Check the original reasoning judgment's identity and exact source witness."""
    from .domain import source_location_inputs
    task, proposed = commissioned_task(context)
    from .literature_assay_inputs import _Sources
    if task['kind'] != 'verified_source_leads':
        raise ContractError('literature_lead_outside_original_search_task')
    value = _resolve(plain(value), outcome.get('aliases', {}))
    validate_schema(value, source_location_inputs(lead_schema()))
    if value['proposed_annotation_ref'] != proposed or value['witness']['source_ref'] != value['source_ref']:
        raise ContractError('literature_lead_question_or_source_mismatch')
    if not value['relevance_rationale'].strip():
        raise ContractError('literature_lead_relevance_rationale_required')
    known = {*context.received_record_refs, *outcome.get('record_refs', [])}
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
    if anchor['artifact_ref'] != witness['artifact_ref'] or not witness['start'] <= anchor['start'] < anchor['end'] <= witness['end']:
        raise ContractError('literature_lead_subject_outside_witness')
    return {**value, 'witness': {**value['witness'], 'quote': witness['quote']}}

def lead_dispositions(store, context):
    """Read original own results and actually admitted child forms, never child logs."""
    _, proposed = commissioned_task(context)
    if not store.db.execute("SELECT 1 FROM sqlite_master WHERE name='runtime_actions'").fetchone():
        return []

    def own():
        for row in store.db.execute("SELECT decision_index,json_extract(result,'$.literature_source_lead') AS lead FROM runtime_actions WHERE run_id=? AND episode_id=? AND json_extract(action,'$.kind')='reason' AND json_extract(result,'$.status') IN ('completed','partial') AND json_type(result,'$.literature_source_lead')='object' ORDER BY decision_index", (context.run_id, context.episode_id)):
            yield (row['decision_index'], json.loads(row['lead']))

    def received():
        if not store.db.execute("SELECT 1 FROM sqlite_master WHERE name='runtime_report_attempts'").fetchone():
            return
        for row in store.db.execute('SELECT decision_index,contract,form FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND failure IS NULL ORDER BY decision_index', (context.run_id, context.episode_id)):
            contract, form = (json.loads(row['contract']), json.loads(row['form']))
            for name, declaration in contract.get('measurements', {}).get('schema', {}).get('properties', {}).items():
                if declaration.get('x-source') == LEADS:
                    for lead in form.get(name, []):
                        yield (row['decision_index'], lead)
    from .scientific_findings import FindingIdentity
    normalizer, current = (FindingIdentity(store), {})
    for _, lead in heapq.merge(own(), received(), key=lambda item: item[0]):
        if lead['proposed_annotation_ref'] == proposed:
            current[canonical(normalizer.source(lead['source_ref']))] = lead
    return list(current.values())

def screening_schema():
    return {'type': 'array', 'x-source': SCREENING, 'items': obj({'proposed_annotation_ref': {**REF, 'format': 'reference', 'x-reference-namespace': 'hypothesis'}, 'disposition': {'const': 'no_applicable_evidence'}, 'examined': {'type': 'array', 'items': obj({'source_ref': {**REF, 'format': 'reference', 'x-reference-namespace': 'source'}, 'artifact_ref': {**REF, 'format': 'reference', 'x-reference-namespace': 'artifact'}, 'start': {'type': 'integer', 'minimum': 0}, 'end': {'type': 'integer', 'minimum': 1}})}, 'annotation_support': {'const': 'not_assessed'}})}

def task_schema():
    from .literature_credit_policy import task_schema_variants
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
    from . import literature_credit_policy as a104_credit
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

@dataclass(frozen=True)
class _RemainingCommissionedCredit:
    """Forecast another action against this episode's finite requested answer."""
    maximum_credit: float
    initial_credit: float

    def __call__(self, raw_signed_history, parameters, aligned_original_contexts):
        history = tuple(raw_signed_history)
        contexts = tuple(aligned_original_contexts)
        if len(history) != len(contexts):
            raise ValueError('literature_yield_requires_aligned_actions')
        current_credit = math.fsum((self.initial_credit, *history))
        remaining = max(0.0, self.maximum_credit - current_credit)
        if remaining == 0.0:
            return YieldEstimate(len(history), NumericBand.exact(0.0), parameters, {'completed_acquisition_turns': len(history), 'history_used': len(history), 'remaining_commissioned_credit': 0.0, 'commissioned_credit_capacity': self.maximum_credit, 'completion': 'all_requested_answers_earned'}, self.as_record())
        estimate = estimate_score_yield(history, parameters, contexts=contexts)
        band = estimate.expected_next_gain
        if band.status_code == STATUS_NORMAL:
            band = type(band)(min(band.value, remaining), min(band.lower, remaining), min(band.upper, remaining), band.status_code, band.uncertainty_code, band.alpha)
        return replace(estimate, expected_next_gain=band, diagnostics={**estimate.diagnostics, 'remaining_commissioned_credit': remaining, 'commissioned_credit_capacity': self.maximum_credit}, estimator_binding=self.as_record())

    def as_record(self):
        return {'version': 'literature_remaining_commissioned_credit_v1', 'base_estimator': 'gene_annotation_episode.episodic_workflow.root.a104.numerical.estimate_score_yield', 'maximum_credit': self.maximum_credit, 'initial_credit': self.initial_credit, 'forecast': 'observed_next_action_yield_bounded_by_remaining_commissioned_credit', 'terminal_forecast': 'exact_zero_when_all_requested_answers_earned'}

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
        return YieldController(epoch, initial_credit, cutoff, parameters)
    maximum_credit = task['credit_unit'] * (len(task['experiments']) if task['kind'] == 'a105_experiments' else 1)
    if not math.isfinite(maximum_credit) or initial_credit > maximum_credit:
        raise ContractError('literature_commissioned_credit_capacity_invalid')
    return _FiniteLiteratureYieldController(epoch, initial_credit, cutoff, parameters, maximum_credit=maximum_credit)

class _FiniteLiteratureYieldController(YieldController):
    """An original finite commission with its own remaining-credit forecast."""

    def __init__(self, epoch, initial_credit, cutoff, parameters, *, maximum_credit):
        self.maximum_credit = maximum_credit
        super().__init__(epoch, initial_credit, cutoff, parameters, estimate_with_context=_RemainingCommissionedCredit(maximum_credit, initial_credit))

    def transitioned(self, epoch):
        if epoch == self.epoch:
            raise ValueError('explicit_new_epoch_required')
        return type(self)(epoch, self._current_credit, self.cost, self.settings, maximum_credit=self.maximum_credit)

def _current_assessments(store, context, proposed, known):
    from .finding_validity import FindingValidity, target_eligible
    with FindingValidity(store, plain(context.scope)) as validity:
        for record in validity.current_records():
            if record['id'] in known and record['hypothesis_ref'] == proposed and (record.get('investigation_finding', {}).get('status') == 'retained') and target_eligible(store, record, plain(context.scope)):
                yield record

def screening_answers(store, context):
    task, proposed = commissioned_task(context)
    if task.get('answer_kind') != 'screening':
        return []
    if not store.db.execute("SELECT 1 FROM sqlite_master WHERE name='runtime_actions'").fetchone():
        return []
    spans = []
    for row in store.db.execute("SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? AND json_extract(action,'$.kind')='reason' AND json_extract(result,'$.status') IN ('completed','partial') AND json_extract(result,'$.evidence_processing.kind')='no_applicable_evidence'", (context.run_id, context.episode_id)):
        processing = json.loads(row['result'])['evidence_processing']
        if not processing.get('reason'):
            continue
        for witness in processing['examined']:
            source = store.get(witness['source_ref'])
            artifact = source.get('artifact_ref' if witness['representation'] == 'original' else 'text_ref')
            spans.append({**witness, 'artifact_ref': artifact})
    for requested in task['examined']:
        covered = requested['start']
        intervals = sorted(((span['start'], span['end']) for span in spans if (span['source_ref'], span['artifact_ref']) == (requested['source_ref'], requested['artifact_ref'])))
        for start, end in intervals:
            if start <= covered:
                covered = max(covered, end)
        if covered < requested['end']:
            return []
    return [{'proposed_annotation_ref': proposed, 'disposition': 'no_applicable_evidence', 'examined': task['examined'], 'annotation_support': 'not_assessed'}]

@dataclass(frozen=True)
class LiteratureTaskCredit:
    binding: object
    context: object
    requires_episode_receipts = True
    requires_known_record_refs = True
    requires_receiver_context = True

    def as_record(self):
        task, _ = commissioned_task(self.context)
        return {'kind': VERSION, 'task': continuation_task(self.context), 'credit_unit': task['credit_unit'], 'unit': 'one_current_graded_assessment_per_original_experiment' if task['kind'] == 'a105_experiments' else 'one_verified_source_for_original_question' if task['kind'] == 'verified_source_leads' else 'one_answer_to_original_commission', 'revision_credit': False, 'activity_credit': False, 'annotation_support': 'separate'}

    def __call__(self, store, scope, *, known_record_refs, assignment, episode_id, run_id):
        task, proposed = commissioned_task(self.context)
        request = plain(self.context.request)
        expected = {'goal': request['goal'], 'scope': plain(self.context.scope), 'purpose': request['report_contract']['decision'], 'schema': request['report_contract']['measurements']['schema'], 'initial_report': request['message']['initial_report']}
        if run_id != self.context.run_id or episode_id != self.context.episode_id or store.validate_scope(scope) != store.validate_scope(plain(self.context.scope)) or any((plain(assignment).get(key) != value for key, value in expected.items())) or (assignment.get('proposed_annotation_ref', proposed) != proposed):
            raise ContractError('literature_task_credit_commission_mismatch')
        hypothesis = store._require(proposed, {'hypothesis'})
        if not store.reference_subset([proposed], plain(scope)):
            raise ContractError('literature_task_annotation_outside_scope')
        if not set(store._record_roots('hypothesis', hypothesis)).intersection(scope['subject_refs']):
            raise ContractError('literature_task_requires_target_annotation')
        known = set(known_record_refs)
        context = replace(self.context, received_record_refs=tuple(known))
        with store.read_snapshot():
            items, unresolved = self._answers(store, context, task, proposed, known)
        credit = task['credit_unit'] * len(items)
        if not math.isfinite(credit):
            raise ContractError('literature_finite_task_credit_required')
        return {'credit': credit, 'scope': plain(scope), 'proposed_annotation_ref': proposed, 'policy': self.as_record(), 'task_status': 'unresolved_contract' if unresolved else 'answered' if items else 'unanswered', 'unresolved': unresolved, 'source_contributions': items, 'commission_ref': identity('literature_task_commission', self.context.as_record())}

    def _answers(self, store, context, task, proposed, known):
        kind, answer = (task['kind'], task.get('answer_kind'))
        if kind == 'verified_source_leads':
            return ([lead for lead in lead_dispositions(store, context) if lead['disposition'] == 'relevant'], [])
        if answer == 'screening':
            return (screening_answers(store, context), [])
        if answer == 'assessment':
            for record in _current_assessments(store, context, proposed, known):
                observation = store.get(record['observation_ref'])
                if observation['source_ref'] in task['source_refs'] and (observation.get('anchor') is not None or observation.get('visual_anchor') is not None):
                    return ([{'assessment_ref': record['id'], 'source_ref': observation['source_ref']}], [])
            return ([], [])
        from . import literature_credit_policy as a104_credit
        if answer == 'measurement':
            return (a104_credit.measured_answers(self.binding, store, context, task, known), [])
        if kind == 'a105_experiments':
            return (a104_credit.graded_experiment_answers(store, context, task, proposed, known, _current_assessments), [])
        return (a104_credit.assembled_answers(store, context, task, proposed, known), [])
