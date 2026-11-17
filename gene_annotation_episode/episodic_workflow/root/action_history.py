"""Root-owned action_history.py"""
from __future__ import annotations
from .receiving_context import BindingContext
from .episode_completion import EFFECT_VERSION
from gene_annotation_episode.episodic_workflow.root.method_loop import Episode
from .workflow_values import TypedReportContract
from . import execution_timing
import json

class ActionHistory:

    def _decision_rejection(self, source, index, *, include_feedback=False):
        """Read an actual own rejection; older journals may have no effects table."""
        if self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_decision_effects'").fetchone() is None:
            return None
        projection = "json_extract(effect,'$.feedback')" if include_feedback else 'NULL'
        row = self.store.db.execute('SELECT ' + projection + " AS feedback FROM runtime_decision_effects WHERE run_id=? AND episode_id=? AND decision_index=? AND json_extract(effect,'$.version')=? AND json_extract(effect,'$.state')='rejected'", (self.run_id, source.episode_id, index, EFFECT_VERSION)).fetchone()
        if row is None:
            return None
        result = {'state': 'rejected'}
        if include_feedback:
            result['feedback'] = json.loads(row['feedback']) if row['feedback'] is not None else None
        return result

    def _history_rows(self, source, before, *, offset=0, limit=None, indices=None, newest=False):
        child_roles = (*(() if self.job_episodes is None else self.job_episodes.roles), *self.episode_bindings.roles)
        clauses = ['calls.run_id=?', 'calls.episode_id=?', 'calls.call_index<?', 'calls.response IS NOT NULL']
        parameters = [self.run_id, source.episode_id, before]
        if indices is not None:
            clauses.append('calls.call_index IN (' + ','.join(('?' for _ in indices)) + ')')
            parameters.extend(indices)
        query = "SELECT calls.call_index AS decision_index, CASE WHEN json_extract(calls.response,'$.selection.kind') IN ('tool','reason','job_child','episode_child','wait','redeliver_report') THEN json_extract(calls.response,'$.selection.kind') ELSE 'unrecognized' END AS kind, CASE WHEN json_extract(calls.response,'$.selection.role') IN (" + ','.join(('?' for _ in child_roles)) + ") THEN json_extract(calls.response,'$.selection.role') ELSE NULL END AS child_role, CASE WHEN EXISTS (SELECT 1 FROM json_each(calls.request,'$.context.tools') saved_tool WHERE json_extract(saved_tool.value,'$.name')=json_extract(calls.response,'$.selection.tool')) THEN json_extract(calls.response,'$.selection.tool') ELSE NULL END AS tool, actions.decision_index AS action_index, actions.credit, actions.result IS NOT NULL AS result_recorded, CASE WHEN json_extract(actions.result,'$.status') IN ('completed','partial','failed','invalid','unavailable') THEN json_extract(actions.result,'$.status') ELSE 'unrecognized' END AS status, attempts.decision_index AS attempt_index, attempts.form IS NOT NULL AS report_admitted, attempts.failure IS NOT NULL AS report_failed FROM runtime_model_calls calls LEFT JOIN runtime_actions actions ON actions.run_id=calls.run_id AND actions.episode_id=calls.episode_id AND actions.decision_index=calls.call_index LEFT JOIN runtime_report_attempts attempts ON attempts.run_id=calls.run_id AND attempts.parent_episode_id=calls.episode_id AND attempts.decision_index=calls.call_index WHERE " + ' AND '.join(clauses) + ' ORDER BY calls.call_index ' + ('DESC' if newest else 'ASC')
        parameters = [*child_roles, *parameters]
        if limit is not None:
            query += ' LIMIT ? OFFSET ?'
            parameters.extend([limit, offset])
        rows = list(self.store.db.execute(query, parameters))
        if newest:
            rows.reverse()
        result = []
        for row in rows:
            kind = row['kind']
            if row['result_recorded']:
                status = row['status']
            elif row['action_index'] is not None:
                status = 'pending'
            elif row['attempt_index'] is not None:
                status = 'report_delivered' if row['report_admitted'] else 'report_delivery_failed'
            elif self._decision_rejection(source, row['decision_index']) is not None:
                status = 'rejected'
            elif kind in {'job_child', 'episode_child'} and row['child_role'] in self.grains and (self.store.db.execute('SELECT 1 FROM runtime_episodes WHERE run_id=? AND episode_id=?', (self.run_id, Episode.identity(self.context, self.grains[row['child_role']], f"child_{row['decision_index']}", parent_path=source.path).episode_id)).fetchone() is not None):
                status = 'pending'
            else:
                status = 'unexecuted'
            result.append({'decision_index': row['decision_index'], 'kind': kind, 'tool': row['tool'] if kind == 'tool' else None, 'status': status, 'credit': row['credit']})
        return result

    def history_preview(self, source, *, before):
        total = self.store.db.execute('SELECT count(*) FROM runtime_model_calls WHERE run_id=? AND episode_id=? AND call_index<? AND response IS NOT NULL', (self.run_id, source.episode_id, before)).fetchone()[0]
        size = self.restoration_settings['preview_size']
        entries = self._history_rows(source, before, limit=size, newest=True)
        return {'total_prior_decisions': total, 'preview_size': size, 'omitted_prior_decisions': total - len(entries), 'entries': entries, 'exact_read_tool': 'episode.history'}

    @staticmethod
    def _history_outcome_view(action):
        if action is None or action['result'] is None:
            return None
        outcome = json.loads(action['result'])
        selection = json.loads(action['action'])
        body = outcome.get('result')
        if selection.get('kind') == 'tool' and selection.get('tool') == 'episode.history' and isinstance(body, dict) and (body.get('view') == 'records') and isinstance(body.get('records'), list) and body['records']:
            indices = [record['decision_index'] for record in body['records']]
            shown = {key: value for key, value in body.items() if key != 'records'}
            shown['records_reference'] = {'tool': 'episode.history', 'arguments': {'view': 'records', 'decision_indices': indices}}
            outcome = {**outcome, 'result': shown}
        return outcome

    def history_read(self, source, args, *, before):
        if args['view'] == 'publications':
            return self.publication_history_read(source, args, before=before)
        if 'decision_indices' in args and ('offset' in args or 'limit' in args):
            return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'feedback': {'code': 'history_selection_conflict'}}
        indices = args.get('decision_indices')
        if indices is not None:
            present = {row[0] for row in self.store.db.execute('SELECT call_index FROM runtime_model_calls WHERE run_id=? AND episode_id=? AND call_index<? AND response IS NOT NULL AND call_index IN (' + ','.join(('?' for _ in indices)) + ')', [self.run_id, source.episode_id, before, *indices])}
            if present != set(indices):
                return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'feedback': {'code': 'history_decision_not_available', 'decision_indices': [index for index in indices if index not in present]}}
        offset = args.get('offset', 0)
        limit = None if indices is not None else args.get('limit', max(1, self.restoration_settings['preview_size']))
        entries = self._history_rows(source, before, offset=offset, limit=limit, indices=indices)
        total = self.store.db.execute('SELECT count(*) FROM runtime_model_calls WHERE run_id=? AND episode_id=? AND call_index<? AND response IS NOT NULL', (self.run_id, source.episode_id, before)).fetchone()[0]
        result = {'view': args['view'], 'total_prior_decisions': total, 'offset': offset, 'limit': limit, 'next_offset': offset + len(entries) if indices is None and offset + len(entries) < total else None}
        if args['view'] == 'index':
            result['entries'] = entries
        else:
            records = []
            for entry in entries:
                index = entry['decision_index']
                row = self.store.db.execute("SELECT response -> '$.selection' FROM runtime_model_calls WHERE run_id=? AND episode_id=? AND call_index=?", (self.run_id, source.episode_id, index)).fetchone()
                action = self.journal.row('runtime_actions', source.episode_id, index)
                progress = self.store.db.execute("SELECT observation FROM runtime_observations WHERE run_id=? AND episode_id=? AND json_extract(observation,'$.decision_index')=?", (self.run_id, source.episode_id, index)).fetchone()
                attempt = self.store.db.execute('SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=?', (self.run_id, source.episode_id, index)).fetchone()
                admitted = None
                if attempt is not None and attempt['form'] is not None:
                    child_row = self.journal.row('runtime_episodes', attempt['child_episode_id'])
                    request = json.loads(child_row['request'])
                    contract = json.loads(attempt['contract'])
                    scope, path = (request['message']['scope'], json.loads(child_row['path']))
                    role = path[-1][0]
                    assignment = request['message'].get('job_assignment')
                    binding_context = BindingContext(self.run_id, attempt['child_episode_id'], role, path, scope, request['message'].get('episode_assignment', {}), request)
                    saved_schema = contract['measurements']['schema']
                    admitted = TypedReportContract(contract['decision'], contract['measurements']['schema'], self.resolver(scope, assignment=assignment, grain=role, context=binding_context), lambda value: self.validate_report(value, scope, assignment=assignment, grain=role, schema=saved_schema, context=binding_context)).admit(json.loads(attempt['form']), audit_identifiers=(attempt['child_episode_id'], request['goal']['goal_id'])).as_record()
                rejection = self._decision_rejection(source, index, include_feedback=True) if entry['status'] == 'rejected' else None
                records.append({**entry, 'selection': json.loads(row[0]) if row[0] is not None else None, 'outcome': self._history_outcome_view(action), **({'rejection_feedback': rejection['feedback']} if rejection is not None else {}), 'admitted_report': admitted, 'report_delivery_failure': json.loads(attempt['failure']) if attempt and attempt['failure'] else None, 'execution_timing': {'decision': execution_timing.snapshot(self.journal.row('runtime_model_calls', source.episode_id, index)['timing']), 'work': execution_timing.snapshot(action['timing']) if action else None}, 'controller_observation': json.loads(progress[0]) if progress else None})
            result['records'] = records
        return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'result': result}

    def publication_history_read(self, source, args, *, before):
        """Page one own prior action's recorded IDs without decoding its body."""
        index = args.get('decision_index')
        offset = args.get('offset', 0)
        limit = args.get('limit', max(1, self.restoration_settings['preview_size']))
        if set(args) - {'view', 'decision_index', 'offset', 'limit'} or type(index) is not int or index < 0 or (type(offset) is not int) or (offset < 0) or (type(limit) is not int) or (limit < 1):
            return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'feedback': {'code': 'invalid_publication_history_selection'}}
        with self.store.read_snapshot():
            entries = self._history_rows(source, before, indices=[index])
            if not entries:
                return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'feedback': {'code': 'history_decision_not_available', 'decision_indices': [index]}}
            entry = entries[0]
            selected = self.store.db.execute("SELECT result IS NOT NULL AS recorded, json_array_length(result,'$.record_refs') AS total FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?", (self.run_id, source.episode_id, index)).fetchone()
            recorded = bool(selected and selected['recorded'])
            total = selected['total'] if recorded else None
            rows = self.store.db.execute("SELECT CAST(ids.key AS INTEGER) AS publication_index, ids.value AS record_ref FROM runtime_actions actions JOIN json_each(actions.result,'$.record_refs') ids WHERE actions.run_id=? AND actions.episode_id=? AND actions.decision_index=? ORDER BY CAST(ids.key AS INTEGER) LIMIT ? OFFSET ?", (self.run_id, source.episode_id, index, limit, offset)) if recorded else ()
            records = [dict(row) for row in rows]
        next_offset = offset + len(records) if total is not None and offset + len(records) < total else None
        result = {'view': 'publications', 'decision_index': index, 'action_status': entry['status'], 'result_recorded': recorded, 'total': total, 'offset': offset, 'limit': limit, 'records': records, 'next_offset': next_offset, 'next_query': {'view': 'publications', 'decision_index': index, 'offset': next_offset, 'limit': limit} if next_offset is not None else None}
        return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'result': result}
