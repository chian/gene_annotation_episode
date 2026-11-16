"""Root host ports defined by WorkflowRecordAccess."""
from __future__ import annotations
import json

class WorkflowRecordAccess:

    def read_record(self, reference):
        return self.workflow.store.get(reference)

    def record_selection(self, context):
        if context.run_id != self.workflow.run_id:
            raise ValueError('record_selection_receiver_identity_mismatch')
        return self.workflow.record_selection(context.episode_id)

    def own_outcomes(self, episode_id, *, tools, offset, limit):
        if type(offset) is not int or offset < 0 or type(limit) is not int or (limit < 1) or (tools is not None and (not isinstance(tools, (tuple, list)) or any((not isinstance(name, str) for name in tools)))):
            raise ValueError('explicit_outcome_page_required')
        clauses = ['run_id=?', 'episode_id=?', 'result IS NOT NULL']
        arguments = [self.workflow.run_id, episode_id]
        if tools is not None:
            clauses.append("json_extract(action,'$.tool') IN (SELECT value FROM json_each(?))")
            arguments.append(json.dumps(list(tools)))
        rows = self.workflow.store.db.execute("SELECT decision_index, json_extract(action,'$.tool') AS selected_tool, json_extract(result,'$.status') AS status, json_extract(result,'$.record_refs') AS record_refs, json_extract(result,'$.changed_record_refs') AS changed_record_refs , json_extract(result,'$.progress_refs') AS progress_refs FROM runtime_actions WHERE " + ' AND '.join(clauses) + ' ORDER BY decision_index LIMIT ? OFFSET ?', (*arguments, limit + 1, offset))
        values = list(rows)
        records = [{'decision_index': row['decision_index'], 'selected_tool': row['selected_tool'], 'status': row['status'], 'record_refs': json.loads(row['record_refs'] or '[]'), 'changed_record_refs': json.loads(row['changed_record_refs'] or '[]'), 'progress_refs': json.loads(row['progress_refs'] or '[]'), 'result_ref': None} for row in values[:limit]]
        return {'records': records, 'offset': offset, 'limit': limit, 'next_offset': offset + limit if len(values) > limit else None}
