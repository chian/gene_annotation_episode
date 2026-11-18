"""Private A104 Launch credit."""
from __future__ import annotations
from .contracts import ROLES, _CLOSED_CREDIT, canonical, digest, json, math, plain, validate_completion_proof


class ExecutionEpisodeCreditCompletion:

    def _proof_for_action(self, context, operation_key):
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
        qualified = []
        for reference in result.get('record_refs', []):
            try:
                target = self.job_progress_provider.targets.read_target(reference, context.scope)
                self._context_target(context, target)
                if self.job_progress_provider.targets.usable_handoff(target):
                    qualified.append(reference)
            except (ValueError, KeyError):
                pass
        complete = bool(qualified)
        keys, endpoint = (['received_usable_handoff'], 'usable_handoff')
        if not complete:
            return None
        receipt = {'action': json.loads(row['action']), 'outcome': result, 'endpoint': endpoint, 'validation_keys': keys}
        return {'version': 'practical_completion_v1', 'run_id': context.run_id, 'episode_id': context.episode_id, 'assignment_sha256': digest(context.assignment), 'endpoint': endpoint, 'operation_key': operation_key, 'receipt_sha256': digest(receipt), 'validation_keys': keys}

    def completion_for_action(self, context, operation_key):
        return self._proof_for_action(context, operation_key)

    def _closed_completion_verdict(self, context, proof):
        """Reuse only an endpoint verification actually recorded in history."""
        if self._closed_operational_credit_view(context, None) is None:
            return None
        from gene_annotation_episode.episodic_workflow.root.a104.method_loop.identities import UnitRef
        from gene_annotation_episode.episodic_workflow.root.a104.episode_return_records import _same
        from gene_annotation_episode.episodic_workflow.root.a104.numerical import NumericBand
        from gene_annotation_episode.episodic_workflow.root.a104.practical_yield import ESTIMATOR_VERSION
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
        return bool(proof and canonical(proof) == canonical(self._proof_for_action(context, proof.get('operation_key', ''))))
