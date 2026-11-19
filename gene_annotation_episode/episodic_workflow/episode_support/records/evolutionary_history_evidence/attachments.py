"""Receipt-triggered attribution of each A104 test to its original target part."""
from __future__ import annotations

import json

from episode_runtime import TableDeclaration
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.evolutionary_history_evidence.hpc import require
from gene_annotation_episode.episodic_workflow.episode_support.grading.evolutionary_history_evidence.scoring import VERSION
from gene_annotation_episode.episodic_workflow.episode_support.grading.evolutionary_history_evidence.tool_grading_artifacts import source_tool_grading_entries


PROVIDER = 'native.a104.tool_attachment'
ATTACHMENTS = TableDeclaration(name='a104_attachments', columns=('source_ref', 'body', 'grading_artifact_ref'),
    key=('source_ref',), record_refs=('source_ref', 'grading_artifact_ref'))


def received_attachments(store, known):
    result = []
    for reference in sorted(known):
        source = store.get(reference)
        if source['record_type'] != 'source' or source.get('provider') != PROVIDER:
            continue
        rows = store.table(ATTACHMENTS).select({'source_ref': reference})
        row = rows[0] if rows else None
        require(row is not None and source['origin'] == 'tool', 'a104_attachment_host_grant_required')
        body = row['body']
        entries = source_tool_grading_entries(store, reference)
        require(json.loads(store.get_artifact(source['artifact_ref'])) == body and len(entries) == 1
                and entries[0]['artifact_ref'] == row['grading_artifact_ref']
                and entries[0]['grading'] == {'grader': VERSION, 'failure': None, 'sheet': body},
                'a104_attachment_custody_conflict')
        result.append({**body, 'source_ref': reference, 'grading_artifact_ref': row['grading_artifact_ref']})
    return result
