"""Credit for an explicitly commissioned literature result, not tool activity."""
from dataclasses import dataclass, replace
import json
import math
import heapq

from .communication import plain
from .domain import ContractError, REF, canonical, identity, obj, validate_schema

VERSION = 'literature_local_task_v1'
SCREENING = 'literature_screening_answers'
LEADS = 'literature_source_lead_dispositions'


def lead_schema():
    from .literature_assay_inputs import _witness_schema
    return obj({'proposed_annotation_ref': {**REF, 'x-reference-namespace': 'hypothesis'},
        'source_ref': {**REF, 'x-reference-namespace': 'source'},
        'subject_ref': {**REF, 'x-reference-namespace': 'reference'},
        'disposition': {'enum': ['relevant', 'not_relevant'], 'description':
            'Whether the inspected source is a useful lead for this commissioned question. '
            'This is not evidence supporting or opposing the proposed annotation.'},
        'relevance_rationale': {'type': 'string', 'minLength': 1, 'description':
            'Explain the specific connection between the witnessed source subject/result '
            'and the original question; a search hit or matching title alone is not verification.'},
        'witness': _witness_schema()})


def lead_return_schema():
    item = lead_schema()
    for name in ('proposed_annotation_ref', 'source_ref', 'subject_ref'):
        item['properties'][name]['format'] = 'reference'
    witness = item['properties']['witness']['properties']
    witness['source_ref'] = {**witness['source_ref'], 'format': 'reference'}
    return {'type': 'array', 'x-source': LEADS, 'items': item}


def validate_lead(store, context, value, outcome):
    """Check the original reasoning judgment's identity and exact source witness."""
    from .literature_required_grading import _resolve
    from .literature_assay_inputs import _Sources
    from .domain import source_location_inputs
    task, proposed = commissioned_task(context)
    if task['kind'] != 'verified_source_leads':
        raise ContractError('literature_lead_outside_original_search_task')
    value = _resolve(plain(value), outcome.get('aliases', {}))
    validate_schema(value, source_location_inputs(lead_schema(), allow_legacy_quote=True))
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
    # A result-list container is not the individual acquired publication.
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
    if (anchor['artifact_ref'] != witness['artifact_ref'] or
            not witness['start'] <= anchor['start'] < anchor['end'] <= witness['end']):
        raise ContractError('literature_lead_subject_outside_witness')
    return {**value, 'witness': {**value['witness'], 'quote': witness['quote']}}


def lead_dispositions(store, context):
    """Read original own results and actually admitted child forms, never child logs."""
    _, proposed = commissioned_task(context)
    if not store.db.execute("SELECT 1 FROM sqlite_master WHERE name='runtime_actions'").fetchone():
        return []
    def own():
        for row in store.db.execute("SELECT decision_index,json_extract(result,'$.literature_source_lead') AS lead "
                "FROM runtime_actions WHERE run_id=? AND episode_id=? "
                "AND json_extract(action,'$.kind')='reason' "
                "AND json_extract(result,'$.status') IN ('completed','partial') "
                "AND json_type(result,'$.literature_source_lead')='object' ORDER BY decision_index",
                (context.run_id, context.episode_id)):
            yield row['decision_index'], json.loads(row['lead'])
    def received():
        if not store.db.execute("SELECT 1 FROM sqlite_master WHERE name='runtime_report_attempts'").fetchone():
            return
        for row in store.db.execute('SELECT decision_index,contract,form FROM runtime_report_attempts '
                'WHERE run_id=? AND parent_episode_id=? AND failure IS NULL ORDER BY decision_index',
                (context.run_id, context.episode_id)):
            contract, form = json.loads(row['contract']), json.loads(row['form'])
            for name, declaration in contract.get('measurements', {}).get('schema', {}).get('properties', {}).items():
                if declaration.get('x-source') == LEADS:
                    for lead in form.get(name, []):
                        yield row['decision_index'], lead
    from .scientific_findings import FindingIdentity
    normalizer, current = FindingIdentity(store), {}
    for _, lead in heapq.merge(own(), received(), key=lambda item: item[0]):
        if lead['proposed_annotation_ref'] == proposed:
            current[canonical(normalizer.source(lead['source_ref']))] = lead
    return list(current.values())


def screening_schema():
    return {'type': 'array', 'x-source': SCREENING, 'items': obj({
        'proposed_annotation_ref': {**REF, 'format': 'reference', 'x-reference-namespace': 'hypothesis'},
        'disposition': {'const': 'no_applicable_evidence'},
        'examined': {'type': 'array', 'items': obj({
            'source_ref': {**REF, 'format': 'reference', 'x-reference-namespace': 'source'},
            'artifact_ref': {**REF, 'format': 'reference', 'x-reference-namespace': 'artifact'},
            'start': {'type': 'integer', 'minimum': 0}, 'end': {'type': 'integer', 'minimum': 1}})},
        'annotation_support': {'const': 'not_assessed'}})}


def task_schema():
    from .literature_quantity_storage import quantity_population_schema
    from .literature_assay_grading import ASSAY_TYPES
    base = {'version': {'const': VERSION}, 'evidence_axis': {'enum': ['A105', 'A106', 'A108']},
        'credit_unit': {'type': 'number', 'exclusiveMinimum': 0}}
    refs = {'type': 'array', 'items': REF, 'minItems': 1, 'uniqueItems': True}
    span = obj({'source_ref': REF, 'artifact_ref': REF,
        'start': {'type': 'integer', 'minimum': 0}, 'end': {'type': 'integer', 'minimum': 1}})
    return {'description': 'The original commissioned result and its explicit local credit unit. '
        'Select only a task whose typed result is requested by the original return contract. '
        'A106/A108 score computation is automatic work, not an episode-credit task.', 'anyOf': [
        obj({**base, 'kind': {'const': 'verified_source_leads'}}),
        obj({**base, 'kind': {'const': 'source_answer'}, 'answer_kind': {'const': 'assessment'},
            'source_refs': refs}),
        obj({**base, 'kind': {'const': 'source_answer'}, 'answer_kind': {'const': 'screening'},
            'examined': {'type': 'array', 'minItems': 1, 'items': span}}),
        obj({**base, 'evidence_axis': {'const': 'A105'}, 'kind': {'const': 'source_answer'},
            'answer_kind': {'const': 'measurement'}, 'selection': quantity_population_schema(),
            'components': {'type': 'array', 'minItems': 1, 'uniqueItems': True,
                'items': {'enum': ['reported_value', 'reported_spread', 'relative_reported_spread']}}}),
        obj({**base, 'evidence_axis': {'const': 'A105'}, 'kind': {'const': 'a105_experiments'},
            'experiments': {'type': 'array', 'minItems': 1, 'items': obj({
                'experiment_ref': REF, 'assay_type': {'enum': list(ASSAY_TYPES)}})}}),
        obj({**base, 'evidence_axis': {'const': 'A105'}, 'kind': {'const': 'a105_assembly'},
            'experiment_refs': refs, 'metrics': {'type': 'array', 'minItems': 1, 'uniqueItems': True,
                'items': {'enum': ['reliability', 'validity', 'relevance', 'attribution', 'overall']}}}),
    ]}


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
    assignment, request = plain(context.assignment), plain(context.request)
    task = assignment.get('literature_task')
    if task is None:
        raise ContractError('literature_original_task_credit_required')
    validate_schema(task, task_schema())
    if type(task['credit_unit']) not in (int, float) or not math.isfinite(task['credit_unit']):
        raise ContractError('literature_finite_task_credit_unit_required')
    proposed = assignment.get('proposed_annotation_ref')
    if not isinstance(proposed, str):
        raise ContractError('literature_original_proposed_annotation_required')
    if (not request.get('goal') or not request.get('report_contract')
            or request.get('message', {}).get('episode_assignment') != assignment):
        raise ContractError('literature_task_original_commission_mismatch')
    schema = request['report_contract']['measurements']['schema']
    sources = set(_return_sources(schema))
    kind, answer = task['kind'], task.get('answer_kind')
    required = (LEADS if kind == 'verified_source_leads' else 'changed_assessment_refs' if answer == 'assessment' else
        SCREENING if answer == 'screening' else 'literature_quantity_cells' if answer == 'measurement' else
        'literature_assay_grading_cells' if kind == 'a105_experiments' else
        'literature_a105_aggregation_cells' if kind == 'a105_assembly' else None)
    if required is not None and required not in sources:
        raise ContractError('literature_task_typed_return_mismatch')
    selected = task.get('metrics', task.get('components'))
    if selected is not None and not any(set(selected) <= values
            for values in _return_components(schema, required)):
        raise ContractError('literature_task_return_components_mismatch')
    if kind == 'a105_experiments':
        experiments = [item['experiment_ref'] for item in task['experiments']]
        if len(set(experiments)) != len(experiments):
            raise ContractError('literature_task_duplicate_experiment')
    if kind == 'a105_assembly' and not set(task['metrics']) <= set(
            assignment.get('requested_a105_aggregation_components', ())):
        raise ContractError('literature_task_requested_metrics_mismatch')
    if answer == 'measurement' and not set(task['components']) <= set(
            assignment.get('requested_quantity_components', ())):
        raise ContractError('literature_task_requested_measurement_mismatch')
    for span in task.get('examined', ()):
        if span['end'] <= span['start']:
            raise ContractError('literature_task_screening_span_invalid')
    assigned_page = assignment.get('page', assignment if context.role == 'literature_page' else None)
    selected_sources = (task.get('source_refs', []) + [span['source_ref'] for span in task.get('examined', [])]
        + ([task['selection']['source_ref']] if answer == 'measurement' else []))
    if assigned_page is not None and any(ref != assigned_page['source_ref'] for ref in selected_sources):
        raise ContractError('literature_task_outside_assigned_source')
    if assigned_page is not None and answer == 'screening' and any(
            span['artifact_ref'] != assigned_page['artifact_ref'] for span in task['examined']):
        raise ContractError('literature_task_screening_artifact_mismatch')
    return task, proposed


def continuation_task(context):
    task, _ = commissioned_task(context)
    name = {'a105_experiments': 'experiments', 'a105_assembly': 'assembly'}.get(task['kind'], task['kind'])
    if task['kind'] == 'source_answer':
        name += ':' + task['answer_kind']
    return task['evidence_axis'] + ':' + name


def _current_assessments(store, context, proposed, known):
    from .finding_validity import FindingValidity, target_eligible
    with FindingValidity(store, plain(context.scope)) as validity:
        for record in validity.current_records():
            if (record['id'] in known and record['hypothesis_ref'] == proposed
                    and record.get('investigation_finding', {}).get('status') == 'retained'
                    and target_eligible(store, record, plain(context.scope))):
                yield record


def screening_answers(store, context):
    task, proposed = commissioned_task(context)
    if task.get('answer_kind') != 'screening':
        return []
    if not store.db.execute("SELECT 1 FROM sqlite_master WHERE name='runtime_actions'").fetchone():
        return []
    spans = []
    for row in store.db.execute("SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? "
            "AND json_extract(action,'$.kind')='reason' "
            "AND json_extract(result,'$.status') IN ('completed','partial') "
            "AND json_extract(result,'$.evidence_processing.kind')='no_applicable_evidence'",
            (context.run_id, context.episode_id)):
        processing = json.loads(row['result'])['evidence_processing']
        if not processing.get('reason'):
            continue
        for witness in processing['examined']:
            source = store.get(witness['source_ref'])
            artifact = source.get('artifact_ref' if witness['representation'] == 'original' else 'text_ref')
            spans.append({**witness, 'artifact_ref': artifact})
    # A repeated/overlapping disposition is still one answer to this commission.
    for requested in task['examined']:
        covered = requested['start']
        intervals = sorted((span['start'], span['end']) for span in spans
            if (span['source_ref'], span['artifact_ref']) == (requested['source_ref'], requested['artifact_ref']))
        for start, end in intervals:
            if start <= covered:
                covered = max(covered, end)
        if covered < requested['end']:
            return []
    return [{'proposed_annotation_ref': proposed, 'disposition': 'no_applicable_evidence',
        'examined': task['examined'], 'annotation_support': 'not_assessed'}]


@dataclass(frozen=True)
class LiteratureTaskCredit:
    binding: object
    context: object
    requires_episode_receipts = True
    requires_known_record_refs = True
    requires_receiver_context = True

    def as_record(self):
        task, _ = commissioned_task(self.context)
        return {'kind': VERSION, 'task': continuation_task(self.context),
            'credit_unit': task['credit_unit'], 'unit': (
                'one_current_graded_assessment_per_original_experiment' if task['kind'] == 'a105_experiments'
                else 'one_verified_source_for_original_question' if task['kind'] == 'verified_source_leads'
                else 'one_answer_to_original_commission'),
            'revision_credit': False, 'activity_credit': False,
            'annotation_support': 'separate'}

    def __call__(self, store, scope, *, known_record_refs, assignment, episode_id, run_id):
        task, proposed = commissioned_task(self.context)
        request = plain(self.context.request)
        expected = {'goal': request['goal'], 'scope': plain(self.context.scope),
            'purpose': request['report_contract']['decision'],
            'schema': request['report_contract']['measurements']['schema'],
            'initial_report': request['message']['initial_report']}
        if (run_id != self.context.run_id or episode_id != self.context.episode_id
                or store.validate_scope(scope) != store.validate_scope(plain(self.context.scope))
                or any(plain(assignment).get(key) != value for key, value in expected.items())
                or assignment.get('proposed_annotation_ref', proposed) != proposed):
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
        return {'credit': credit, 'scope': plain(scope),
            'proposed_annotation_ref': proposed, 'policy': self.as_record(),
            'task_status': 'unresolved_contract' if unresolved else 'answered' if items else 'unanswered',
            'unresolved': unresolved, 'source_contributions': items,
            'commission_ref': identity('literature_task_commission', self.context.as_record())}

    def _answers(self, store, context, task, proposed, known):
        kind, answer = task['kind'], task.get('answer_kind')
        if kind == 'verified_source_leads':
            return [lead for lead in lead_dispositions(store, context) if lead['disposition'] == 'relevant'], []
        if answer == 'screening':
            return screening_answers(store, context), []
        if answer == 'assessment':
            for record in _current_assessments(store, context, proposed, known):
                observation = store.get(record['observation_ref'])
                if observation['source_ref'] in task['source_refs'] and (
                        observation.get('anchor') is not None or observation.get('visual_anchor') is not None):
                    return [{'assessment_ref': record['id'], 'source_ref': observation['source_ref']}], []
            return [], []
        if answer == 'measurement':
            return self._measurement(store, context, task, known), []
        from .literature_sheet_updates import current_sheet_refs
        if kind == 'a105_experiments':
            from .literature_assay_grading_storage import LiteratureAssayGradingRepository
            from .literature_required_grading import _matches_grading
            repository = LiteratureAssayGradingRepository(store, context.run_id)
            assessments = list(_current_assessments(store, context, proposed, known))
            wanted = {item['experiment_ref']: item['assay_type'] for item in task['experiments']}
            completed = {}
            for ref in current_sheet_refs(store, context, repository.provider):
                if ref not in known:
                    continue
                saved = repository.read(ref)
                args = saved['selection']
                experiment = args.get('experiment_ref')
                if args['assertion_ref'] != proposed or wanted.get(experiment) != args['assay_type']:
                    continue
                # Owning a source handle alone does not grant another child's grade.
                if not repository.fact_cells(context, [ref], components=repository.components):
                    continue
                for assessment in assessments:
                    if _matches_grading(store, assessment['id'], args, contextual=False):
                        completed[experiment] = {'experiment_ref': experiment,
                            'assessment_ref': assessment['id'], 'sheet_ref': ref}
            return list(completed.values()), []
        from .literature_a105_aggregation_storage import LiteratureA105AggregationRepository
        repository = LiteratureA105AggregationRepository(store, context.run_id)
        current_grades = set(current_sheet_refs(store, context, 'literature.a105.assay_grading'))
        for ref in current_sheet_refs(store, context, repository.provider):
            if ref not in known:
                continue
            saved = repository.read(ref)
            args = saved['selection']
            if (args['assertion_ref'] != proposed or set(task['experiment_refs']) != {
                    item['experiment_ref'] for item in args['experiments']}):
                continue
            # Automatic discovery creates an unbound scaffold. Assembly needs
            # selected current inputs; a selected grader may explicitly report
            # an unavailable value, but an unselected input is not an answer.
            selected = [experiment['metrics'][metric] for experiment in args['experiments']
                for metric in task['metrics']]
            if any(item is None or item['sheet_ref'] not in current_grades for item in selected):
                continue
            cells = repository.fact_cells(context, [ref], components=task['metrics'])
            if {row['component'] for row in cells} == set(task['metrics']):
                return [{'sheet_ref': ref, 'experiment_refs': task['experiment_refs'],
                    'metrics': task['metrics']}], []
        return [], []

    def _measurement(self, store, context, task, known):
        repository = self.binding.services.literature_quantity_repository()
        for ref in known:
            source = store.get(ref)
            if source.get('provider') != repository.provider:
                continue
            request = json.loads(store.get_artifact(source['request_ref']))
            if request.get('arguments') != task['selection']:
                continue
            repository.read(ref)
            rows = repository.fact_cells(context, [ref], components=task['components'])
            if {row['component'] for row in rows} != set(task['components']):
                continue
            # This reader preserves an unreported spread as an explicit unknown.
            if all(row['status'] == 'populated' or row.get('unavailable_reason') in {
                    'reported_spread_unavailable', 'zero_reported_value'} for row in rows):
                return [{'sheet_ref': ref, 'source_ref': task['selection']['source_ref'],
                    'components': task['components']}]
        return []
