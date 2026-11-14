"""Read and validate original receipt-qualified literature task answers."""
import heapq
import json
from gene_annotation_episode.domain import ContractError, canonical, validate_schema
from gene_annotation_episode.episodic_workflow.root.communication import plain
from .commission_contract import commissioned_task
from gene_annotation_episode.episodic_workflow.root.library.literature_task_answer_schemas import LEADS, lead_schema

def validate_lead(store, context, value, outcome):
    """Check the original reasoning judgment's identity and exact source witness."""
    from gene_annotation_episode.episodic_workflow.root.literature_required_grading import _resolve
    from gene_annotation_episode.episodic_workflow.root.literature_assay_inputs import _Sources
    from gene_annotation_episode.domain import source_location_inputs
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
    from gene_annotation_episode.scientific_findings import FindingIdentity
    normalizer, current = FindingIdentity(store), {}
    for _, lead in heapq.merge(own(), received(), key=lambda item: item[0]):
        if lead['proposed_annotation_ref'] == proposed:
            current[canonical(normalizer.source(lead['source_ref']))] = lead
    return list(current.values())


def _current_assessments(store, context, proposed, known):
    from gene_annotation_episode.finding_validity import FindingValidity, target_eligible
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


