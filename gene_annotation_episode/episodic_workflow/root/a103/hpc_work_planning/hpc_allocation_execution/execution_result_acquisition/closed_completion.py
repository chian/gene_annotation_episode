"""Authenticate the original saved completion verdict without repricing closed history."""
from __future__ import annotations
from .execution_contracts import ROLE_KINDS, canonical, digest, is_native_blast_database_target, is_standard_blast_database_target, json, plain, validate_completion_proof

class ResultsClosedCompletion:

    def _closed_completion_verdict(self, context, proof):
        """Reuse only an endpoint verification actually recorded in history."""
        if self._closed_operational_credit_view(context, None) is None:
            return None
        from gene_annotation_episode.episodic_workflow.root.a103.method_loop.identities import UnitRef
        from gene_annotation_episode.episodic_workflow.root.a103.episode_return_records import _same
        from gene_annotation_episode.episodic_workflow.root.a103.numerical import NumericBand
        from gene_annotation_episode.episodic_workflow.root.a103.practical_yield import ESTIMATOR_VERSION
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

