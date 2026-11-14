"""Verify actual selected result acquisition and its saved action receipts."""
from __future__ import annotations
from .execution_contracts import ROLE_KINDS, canonical, digest, is_native_blast_database_target, is_standard_blast_database_target, json, plain, validate_completion_proof

class ResultsResultCompletion:

    def _native_results_complete(self, context, bodies):
        if self.local_file_sources.applies(context):
            return self.local_file_sources.complete(context, bodies)
        if self.native_blast_masking_results.applies(context):
            return False
        if self.native_blast_utility_results.applies(context):
            return False
        if is_standard_blast_database_target(self._target(context)):
            return False
        if is_native_blast_database_target(self._target(context)):
            return False
        if not bodies:
            return False
        closed = [body for body in bodies if body['observation']['state'] == 'completed' and body['observation']['returncode'] == 0]
        if not closed:
            return False
        target = self._target(context)
        requested = self._windows(self._selector(plain(context.assignment), target))
        for path, (start, length) in requested.items():
            windows = [window for body in closed for window in body['windows'] if window['path'] == path]
            if not windows:
                return False
            end = max((window['size_bytes'] for window in windows))
            if length is not None:
                end = min(end, start + length)
            cursor = start
            for window in sorted(windows, key=lambda item: item['offset']):
                if window['offset'] > cursor:
                    return False
                cursor = max(cursor, window['offset'] + window['returned_bytes'])
            if cursor < end:
                return False
        return True

    def _proof_for_action(self, context, operation_key):
        if self.native_blast_masking_results.applies(context):
            proof = self.native_blast_masking_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_blast_utility_results.applies(context):
            proof = self.native_blast_utility_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_blast_standard_database_results is not None and self.native_blast_standard_database_results.applies(context):
            proof = self.native_blast_standard_database_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_blast_database_results is not None and self.native_blast_database_results.applies(context):
            proof = self.native_blast_database_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        prefix = context.run_id + ':' + context.episode_id + ':'
        index = operation_key.removeprefix(prefix)
        if not operation_key.startswith(prefix) or not index.isdecimal() or str(int(index)) != index:
            return None
        row = self.store.db.execute('SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?', (context.run_id, context.episode_id, int(index))).fetchone()
        if row is None or row['result'] is None:
            return None
        result = json.loads(row['result'])
        if result.get('status') != 'completed':
            return None
        bodies = []
        rows = self.store.db.execute('SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index<=? AND result IS NOT NULL ORDER BY decision_index', (context.run_id, context.episode_id, int(index)))
        for earlier in rows:
            outcome = json.loads(earlier[0])
            if outcome.get('status') != 'completed':
                continue
            for reference in outcome.get('record_refs', []):
                body = self._read_result(reference, context.scope)
                if body is not None and body['assignment'] == plain(context.assignment):
                    bodies.append(body)
        complete = self._native_results_complete(context, bodies)
        keys = ['requested_filesystem_acquisition', 'successful_exact_attempt_observed', 'attempt_output_version_unverified']
        if self.local_file_sources.applies(context):
            keys = ['requested_complete_file_sources', 'exact_attempt_terminal_quiescent_observed', 'attempt_output_version_unverified']
        endpoint = 'usable_handoff'
        if not complete:
            return None
        receipt = {'action': json.loads(row['action']), 'outcome': result, 'endpoint': endpoint, 'validation_keys': keys}
        receipt['supporting_receipt_sha256s'] = [digest(body) for body in bodies]
        return {'version': 'practical_completion_v1', 'run_id': context.run_id, 'episode_id': context.episode_id, 'assignment_sha256': digest(context.assignment), 'endpoint': endpoint, 'operation_key': operation_key, 'receipt_sha256': digest(receipt), 'validation_keys': keys}

