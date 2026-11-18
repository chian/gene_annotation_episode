"""Private A102 Results completion."""
from __future__ import annotations
from .execution_contracts import ROLE_KINDS, canonical, digest, json, plain, validate_completion_proof

class ResultsCompletion:

    def _native_results_complete(self, context, bodies):
        if self.local_file_sources.applies(context):
            return self.local_file_sources.complete(context, bodies)
        if self.native_protein_structure_results.applies(context):
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
        if self.native_protein_structure_results.applies(context):
            proof = self.native_protein_structure_results.completion(context)
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

    def completion_for_action(self, context, operation_key):
        if self.native_protein_structure_results.applies(context):
            proof = self.native_protein_structure_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self._target(context)['resource_kind'] == 'api':
            return self.api_execution.completion_for_action(context, operation_key)
        return self._proof_for_action(context, operation_key)

    def _closed_completion_verdict(self, context, proof):
        """Reuse only an endpoint verification actually recorded in history."""
        if self._closed_operational_credit_view(context, None) is None:
            return None
        from gene_annotation_episode.episodic_workflow.root.a102.method_loop.identities import UnitRef
        from gene_annotation_episode.episodic_workflow.root.a102.episode_return_records import _same
        from gene_annotation_episode.episodic_workflow.root.a102.numerical import NumericBand
        from gene_annotation_episode.episodic_workflow.root.a102.practical_yield import ESTIMATOR_VERSION
        assignment = context.assignment
        matches = 0
        for row in self.store.db.execute('SELECT unit_index,observation FROM runtime_observations WHERE run_id=? AND episode_id=? ORDER BY unit_index', (self.run_id, context.episode_id)):
            try:
                observed = json.loads(row['observation'])
                supplied = observed['credit']
                if type(supplied) is not dict or not _same(supplied.get('practical_completion'), proof):
                    continue
                index = observed['decision_index']
                unit = UnitRef.from_record(observed['unit_ref'])
                estimate = observed['step']['estimate']
                diagnostics, provenance = (estimate['diagnostics'], estimate['provenance'])
                if type(index) is int and index >= 0 and (type(supplied.get('estimation_action_index')) is int) and (supplied['estimation_action_index'] == index) and (unit.episode_id == context.episode_id) and (unit.unit_index == row['unit_index']) and (proof['run_id'] == self.run_id) and (proof['episode_id'] == context.episode_id) and (proof['assignment_sha256'] == digest(assignment)) and (proof['operation_key'] == f'{self.run_id}:{context.episode_id}:{index}') and (type(estimate['turns']) is int) and (estimate['turns'] == unit.unit_index + 1) and (provenance['version'] == ESTIMATOR_VERSION) and (diagnostics['fitting_scope'] == 'verified_assignment_endpoint') and _same(diagnostics['completion_proof'], proof) and (type(diagnostics['completion_action_index']) is int) and (diagnostics['completion_action_index'] == index) and _same(diagnostics['completion_unit_ref'], unit.as_record()) and _same(estimate['expected_next_gain'], NumericBand.exact(0).as_record()):
                    matches += 1
            except (ValueError, TypeError, KeyError):
                continue
        return matches == 1

    def verify_completion(self, context, proof):
        try:
            proof = validate_completion_proof(plain(proof))
        except (ValueError, TypeError):
            return False
        historical = self._closed_completion_verdict(context, proof)
        if historical is not None:
            return historical
        if self.native_protein_structure_results.applies(context):
            return proof == self.native_protein_structure_results.completion(context)
        if self._target(context)['resource_kind'] == 'api':
            return self.api_execution.verify_completion(context, proof)
        return bool(proof and canonical(proof) == canonical(self._proof_for_action(context, proof.get('operation_key', ''))))
