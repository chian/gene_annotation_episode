"""Host-issued gene-context measurements and automatically attached graders."""
from __future__ import annotations

from copy import deepcopy
import json

from episode_runtime import TableDeclaration
from gene_annotation_episode.episodic_workflow.episode_support.grading.gene_context_evidence.scoring import VERSION, PROFILE, binding_summary, digest, require
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.domain import canonical
from gene_annotation_episode.episodic_workflow.episode_support.grading.gene_context_evidence.tool_grading_artifacts import retain_tool_grading, source_tool_grading_entries


PROVIDER = 'native.a103.measurement'
KINDS = {'a103_locus_binding_v1':'locus_binding', 'a103_neighborhood_v1':'organization',
    'a103_recurrence_v1':'recurrence', 'a103_fusion_v1':'fusion',
    'a103_cooccurrence_v1':'cooccurrence', 'a103_channel_v1':'native_channel',
    'a103_contrast_v1':'functional_contrast', 'a103_detection_v1':'component_detection'}


PUBLICATIONS = TableDeclaration(name='a103_publications',
    columns=('source_ref', 'target_ref', 'kind', 'body', 'grading_artifact_ref', 'permitted_use'),
    key=('source_ref',), record_refs=('source_ref', 'target_ref', 'grading_artifact_ref'))
BINDINGS = TableDeclaration(name='a103_bindings', columns=('source_ref', 'body'),
    key=('source_ref',), record_refs=('source_ref',))


def native_grade(body):
    schema = body['schema']
    require(schema in KINDS, 'a103_unbound_native_metric_schema')
    kind = KINDS[schema]
    value = (body['group_balanced_fraction'] if kind=='recurrence' else
             body['observed_link_fraction'] if kind=='fusion' else
             body['native_significance_index'] if kind=='cooccurrence' else
             body['native_value'] if kind=='native_channel' else None)
    require(value is None or type(value) in {int,float} and 0<=value<=1,
            'a103_native_index_outside_unit_interval')
    return {'schema':'a103_native_sheet_v1', 'version':VERSION, 'profile':PROFILE,
        'kind':kind,'producer_operation':body['producer_operation'],'target_ref':body['target_ref'],
        'raw_value':value,'native_measurement_sha256':digest(body),
        'target_attribution':'requires_its_measurement_specific_attachment',
        'interpretation':'measured_context_progress_not_function_probability'}


def publish(store, body, evidence_refs=()):
    body = deepcopy(body)
    grade = native_grade(body)
    with store.transaction():
        artifact = store.artifact(canonical(body), 'application/json')
        grading = retain_tool_grading(store,provider=PROVIDER,native_artifact_ref=artifact,
            grading={'grader':VERSION,'failure':None,'sheet':grade})
        operands = [r for r in sorted(set([body['target_ref'],*evidence_refs]))
            if store.get(r)['record_type'] in {'input','reference','read_subject','feature','product'}]
        ref = store.put('source',{'provider':PROVIDER,'accession':digest(body),'uri':None,
            'artifact_ref':artifact,'text_ref':artifact,'request_ref':None,'version':VERSION,
            'retrieved_at':None,'operand_refs':operands,'auxiliary_artifact_refs':[grading]},origin='tool')['id']
        store.table(PUBLICATIONS).put({'source_ref':ref,'target_ref':body['target_ref'],'kind':grade['kind'],
            'body':body,'grading_artifact_ref':grading,'permitted_use':'a103_scoring'})
    return ref


def received_measurement(store, reference):
    source = store.get(reference)
    if source['record_type']!='source' or source.get('provider')!=PROVIDER:
        return None
    rows = store.table(PUBLICATIONS).select({'source_ref':reference})
    row = rows[0] if rows else None
    require(row is not None and row['permitted_use']=='a103_scoring'
        and source['origin']=='tool' and source.get('version')==VERSION, 'a103_native_scoring_grant_unavailable')
    body = row['body']
    entries = source_tool_grading_entries(store,reference)
    require(json.loads(store.get_artifact(source['artifact_ref']))==body and len(entries)==1
        and entries[0]['artifact_ref']==row['grading_artifact_ref']
        and entries[0]['grading']=={'grader':VERSION,'failure':None,'sheet':native_grade(body)},
        'a103_native_grade_custody_conflict')
    return {'source_ref':reference,'body':body,'grade':entries[0]['grading']['sheet'],
            'grading_artifact_ref':row['grading_artifact_ref']}


def binding_body(store, reference, known):
    require(reference in known, 'a103_locus_binding_not_received')
    result = received_measurement(store,reference)
    require(result is not None and result['body']['schema']=='a103_locus_binding_v1',
            'a103_actual_locus_binding_required')
    rows = store.table(BINDINGS).select({'source_ref':reference})
    require(rows,'a103_private_locus_payload_unavailable')
    body = rows[0]['body']
    require(binding_summary(body)==result['body'],'a103_locus_payload_custody_conflict')
    return body
