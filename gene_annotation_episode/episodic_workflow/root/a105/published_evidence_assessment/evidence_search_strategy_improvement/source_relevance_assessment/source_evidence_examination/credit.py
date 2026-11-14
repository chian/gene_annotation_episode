"""Private credit for the original literature_page commission."""
from __future__ import annotations
from dataclasses import dataclass, replace
import json
import math
import heapq
from gene_annotation_episode.episodic_workflow.root.a105.communication import plain
from gene_annotation_episode.episodic_workflow.root.a105.domain import REF, canonical, identity, obj, validate_schema
from gene_annotation_episode.domain import ContractError
import json
from gene_annotation_episode.episodic_workflow.root.a105.domain import REF, obj
from gene_annotation_episode.domain import ContractError
VERSION = 'literature_local_task_v1'
SCREENING = 'literature_screening_answers'
LEADS = 'literature_source_lead_dispositions'
YIELD_TASKS = frozenset((f'A105:{task}' for task in ('verified_source_leads', 'source_answer:assessment', 'source_answer:screening'))) | frozenset(('A105:source_answer:measurement', 'A105:experiments', 'A105:assembly'))
from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.goal import LEADS, SCREENING, VERSION, commissioned_task, continuation_task

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

def lead_schema():
    from gene_annotation_episode.episodic_workflow.root.a105.library.literature_assay_inputs import _witness_schema
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
    from gene_annotation_episode.episodic_workflow.root.a105.domain import source_location_inputs
    task, proposed = commissioned_task(context)
    from gene_annotation_episode.episodic_workflow.root.a105.library.literature_assay_inputs import _Sources
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
    from gene_annotation_episode.episodic_workflow.root.a105.scientific_findings import FindingIdentity
    normalizer, current = (FindingIdentity(store), {})
    for _, lead in heapq.merge(own(), received(), key=lambda item: item[0]):
        if lead['proposed_annotation_ref'] == proposed:
            current[canonical(normalizer.source(lead['source_ref']))] = lead
    return list(current.values())

def screening_schema():
    return {'type': 'array', 'x-source': SCREENING, 'items': obj({'proposed_annotation_ref': {**REF, 'format': 'reference', 'x-reference-namespace': 'hypothesis'}, 'disposition': {'const': 'no_applicable_evidence'}, 'examined': {'type': 'array', 'items': obj({'source_ref': {**REF, 'format': 'reference', 'x-reference-namespace': 'source'}, 'artifact_ref': {**REF, 'format': 'reference', 'x-reference-namespace': 'artifact'}, 'start': {'type': 'integer', 'minimum': 0}, 'end': {'type': 'integer', 'minimum': 1}})}, 'annotation_support': {'const': 'not_assessed'}})}

def _current_assessments(store, context, proposed, known):
    from gene_annotation_episode.episodic_workflow.root.a105.finding_validity import FindingValidity, target_eligible
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

    def _scientific_credit_invocation(self, services, context, receiver_selection):
        workflow = services.workflow
        local = len(context.path) > 1
        projector = workflow.scientific_projector_for_context(context)
        arguments = {}
        if local:
            request = context.request
            contract = request['report_contract']
            arguments.update(assignment={'goal': plain(request['goal']), 'scope': plain(context.scope), 'purpose': contract['decision'], 'schema': plain(contract['measurements']['schema']), 'initial_report': plain(request['message']['initial_report'])}, episode_id=context.episode_id, run_id=context.run_id)
            annotation = services.proposed_annotation_for(context)
            if annotation is not None:
                arguments['assignment']['proposed_annotation_ref'] = annotation
            elif services.annotation_task_required():
                raise ValueError('scientific_task_requires_original_proposed_annotation')
        arguments.update(workflow.projector_receipt_arguments(projector, context.episode_id))
        result = workflow.projection_view(projector, plain(context.scope), **arguments)
        if local and arguments['assignment'].get('proposed_annotation_ref') is not None:
            result['proposed_annotation_ref'] = arguments['assignment']['proposed_annotation_ref']
        return result
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
        from gene_annotation_episode.episodic_workflow.root.a105.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination import credit as a105_credit
        if answer == 'measurement':
            return (a105_credit.measured_answers(self.binding, store, context, task, known), [])
        if kind == 'a105_experiments':
            return (a105_credit.graded_experiment_answers(store, context, task, proposed, known, _current_assessments), [])
        return (a105_credit.assembled_answers(store, context, task, proposed, known), [])

def measured_answers(binding, store, context, task, known):
    repository = binding.literature_quantity_repository()
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
        if all((row['status'] == 'populated' or row.get('unavailable_reason') in {'reported_spread_unavailable', 'zero_reported_value'} for row in rows)):
            return [{'sheet_ref': ref, 'source_ref': task['selection']['source_ref'], 'components': task['components']}]
    return []

def graded_experiment_answers(store, context, task, proposed, known, current_assessments):
    from gene_annotation_episode.episodic_workflow.root.a105.library.literature_sheet_updates import current_sheet_refs
    from gene_annotation_episode.episodic_workflow.root.a105.library.literature_assay_grading_storage import LiteratureAssayGradingRepository
    from gene_annotation_episode.episodic_workflow.root.a105.library.literature_required_grading import _matches_grading
    repository = LiteratureAssayGradingRepository(store, context.run_id)
    assessments = list(current_assessments(store, context, proposed, known))
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
        if not repository.fact_cells(context, [ref], components=repository.components):
            continue
        for assessment in assessments:
            if _matches_grading(store, assessment['id'], args):
                completed[experiment] = {'experiment_ref': experiment, 'assessment_ref': assessment['id'], 'sheet_ref': ref}
    return list(completed.values())

def assembled_answers(store, context, task, proposed, known):
    from gene_annotation_episode.episodic_workflow.root.a105.library.literature_sheet_updates import current_sheet_refs
    from gene_annotation_episode.episodic_workflow.root.a105.library.literature_a105_aggregation_storage import LiteratureA105AggregationRepository
    repository = LiteratureA105AggregationRepository(store, context.run_id)
    current_grades = set(current_sheet_refs(store, context, 'literature.a105.assay_grading'))
    for ref in current_sheet_refs(store, context, repository.provider):
        if ref not in known:
            continue
        saved = repository.read(ref)
        args = saved['selection']
        if args['assertion_ref'] != proposed or set(task['experiment_refs']) != {item['experiment_ref'] for item in args['experiments']}:
            continue
        selected = [experiment['metrics'][metric] for experiment in args['experiments'] for metric in task['metrics']]
        if any((item is None or item['sheet_ref'] not in current_grades for item in selected)):
            continue
        cells = repository.fact_cells(context, [ref], components=task['metrics'])
        if {row['component'] for row in cells} == set(task['metrics']):
            return [{'sheet_ref': ref, 'experiment_refs': task['experiment_refs'], 'metrics': task['metrics']}]
    return []
'Private literature_page credit behavior for A105.'

class LiteratureCredit:

    def credit_kind(self, role):
        self._role(role)
        return 'scientific'

    def credit_view(self, context, receiver_selection):
        self._role(context.role)
        invocation = getattr(self.services, 'scientific_credit_for', None)
        if callable(invocation):
            return invocation(self._scientific_credit_invocation, context, receiver_selection)
        return self.services.scientific_credit(context, receiver_selection)

    def credit_projector(self, context):
        self._role(context.role)
        return LiteratureTaskCredit(self, context)
