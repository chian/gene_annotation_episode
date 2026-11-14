"""Host-owned A102 result custody and narrow numerical delivery grants.

An auxiliary artifact or a model's prose cannot mint a grade. Publication is
atomic with the native producer's retained input, graded cells and use grant.
The grant covers A102 arithmetic; it grants no access to raw coordinates.
"""
from __future__ import annotations

import json

from .a102_scoring import GRADE_SCHEMA, VERSION, digest, grade_comparison, require
from .domain import canonical, identity
from .tool_grading_artifacts import retain_tool_grading, source_tool_grading_entries


PROVIDER='native.a102.structural_comparison'


def install(store):
    store.db.execute('''CREATE TABLE IF NOT EXISTS a102_native_publications (
        source_ref TEXT PRIMARY KEY, native_artifact_ref TEXT NOT NULL,
        grading_artifact_ref TEXT NOT NULL, target_ref TEXT NOT NULL,
        grade_sha256 TEXT NOT NULL, producer TEXT NOT NULL, permitted_use TEXT NOT NULL)''')


def publish_comparison(store, native):
    """Called by a qualified host producer before returning any native result."""
    install(store)
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
        values=(source,artifact,grading,native['target_ref'],digest(grade),native['producer'],'a102_scoring')
        old=store.db.execute('SELECT * FROM a102_native_publications WHERE source_ref=?',(source,)).fetchone()
        require(old is None or tuple(old)==values,'a102_native_publication_conflict')
        store.db.execute('INSERT OR IGNORE INTO a102_native_publications VALUES(?,?,?,?,?,?,?)',values)
    return {'source_ref':source,'grading_artifact_ref':grading,'grade':grade}


def received_grade(store, reference):
    """Resolve only an authenticated published numerical receipt, never coords."""
    source=store.get(reference)
    if source['record_type']!='source' or source.get('provider')!=PROVIDER:return None
    exists=store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='a102_native_publications'").fetchone()
    row=(store.db.execute('SELECT * FROM a102_native_publications WHERE source_ref=?',(reference,)).fetchone()
        if exists else None)
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
