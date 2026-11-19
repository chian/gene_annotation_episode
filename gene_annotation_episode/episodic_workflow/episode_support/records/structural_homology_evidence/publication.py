"""Host-owned A102 result custody and narrow numerical delivery grants.

An auxiliary artifact or a model's prose cannot mint a grade. Publication is
atomic with the native producer's retained input, graded cells and use grant.
The grant covers A102 arithmetic; it grants no access to raw coordinates.
"""
from __future__ import annotations

import json

from episode_runtime import TableDeclaration
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.scoring import GRADE_SCHEMA, VERSION, digest, grade_comparison, require
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.domain import canonical, identity
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.tool_grading_artifacts import retain_tool_grading, source_tool_grading_entries


PROVIDER='native.a102.structural_comparison'


NATIVE_PUBLICATIONS = TableDeclaration(name='a102_native_publications',
    columns=('source_ref', 'native_artifact_ref', 'grading_artifact_ref', 'target_ref',
        'grade_sha256', 'producer', 'permitted_use'),
    key=('source_ref',), record_refs=('source_ref', 'native_artifact_ref', 'grading_artifact_ref', 'target_ref'))


def publish_comparison(store, native):
    """Called by a qualified host producer before returning any native result."""
    grade=grade_comparison(native)
    with store.transaction():
        artifact=store.artifact(canonical(native),'application/json')
        grading=retain_tool_grading(store,provider=PROVIDER,native_artifact_ref=artifact,
            grading={'grader':'a102_native_alignment_grader_v1','failure':None,'sheet':grade})
        source=store.put('source',{'provider':PROVIDER,'accession':identity('a102_comparison',native),
            'uri':None,'artifact_ref':artifact,'text_ref':artifact,'request_ref':None,
            'version':VERSION,'retrieved_at':None,'auxiliary_artifact_refs':[grading],
            'operand_refs':[native['target_ref']] if store.get(native['target_ref'])['record_type'] in {
                'input','reference','read_subject','feature','product'} else []},origin='tool')['id']
        values={'source_ref':source,'native_artifact_ref':artifact,'grading_artifact_ref':grading,
            'target_ref':native['target_ref'],'grade_sha256':digest(grade),'producer':native['producer'],
            'permitted_use':'a102_scoring'}
        old=store.table(NATIVE_PUBLICATIONS).select({'source_ref':source})
        require(not old or all(old[0][name]==value for name,value in values.items()),'a102_native_publication_conflict')
        store.table(NATIVE_PUBLICATIONS).put(values)
    return {'source_ref':source,'grading_artifact_ref':grading,'grade':grade}


def received_grade(store, reference):
    """Resolve only an authenticated published numerical receipt, never coords."""
    source=store.get(reference)
    if source['record_type']!='source' or source.get('provider')!=PROVIDER:return None
    rows=store.table(NATIVE_PUBLICATIONS).select({'source_ref':reference})
    row=rows[0] if rows else None
    require(row is not None and row['permitted_use']=='a102_scoring'
        and source['origin']=='tool' and source.get('version')==VERSION,
        'a102_native_scoring_grant_unavailable',source_ref=reference)
    require(source['artifact_ref']==row['native_artifact_ref'],'a102_native_receipt_conflict')
    entries=source_tool_grading_entries(store,reference)
    require(len(entries)==1 and entries[0]['artifact_ref']==row['grading_artifact_ref'],
        'a102_native_grader_not_attached',source_ref=reference)
    grading=entries[0]['grading']
    require(grading.get('failure') is None and grading.get('grader')=='a102_native_alignment_grader_v1',
        'a102_native_grader_failed')
    grade=grading.get('sheet')
    require(isinstance(grade,dict) and grade.get('schema')==GRADE_SCHEMA
        and digest(grade)==row['grade_sha256'] and grade['target_ref']==row['target_ref'],
        'a102_native_grade_custody_conflict')
    # Recalculation is arithmetic verification, never a deferred native grader.
    native=json.loads(store.get_artifact(source['artifact_ref']))
    require(grade_comparison(native)==grade,'a102_native_grade_recalculation_conflict')
    return {'source_ref':reference,'grading_artifact_ref':row['grading_artifact_ref'],'grade':grade}
