"""Original completion proof producers, action identity and retained proof validation."""
from __future__ import annotations
from .contracts import ROLES, ROLE_KINDS, _CLOSED_CREDIT, canonical, digest, json, math, plain, validate_completion_proof

class ExecutionCompletion:

    def completion_for_action(self, context, operation_key):
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
        return self._delegate(context).completion_for_action(self._practical_context(context), operation_key)

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

    def verify_completion(self, context, proof):
        try:
            proof = validate_completion_proof(plain(proof))
        except (ValueError, TypeError):
            return False
        historical = self._closed_completion_verdict(context, proof)
        if historical is not None:
            return historical
        if self.native_blast_masking_results.applies(context):
            return proof == self.native_blast_masking_results.completion(context)
        if self.native_blast_utility_results.applies(context):
            return proof == self.native_blast_utility_results.completion(context)
        if self.native_blast_standard_database_results is not None and self.native_blast_standard_database_results.applies(context):
            return proof == self.native_blast_standard_database_results.completion(context)
        if self.native_blast_database_results is not None and self.native_blast_database_results.applies(context):
            return proof == self.native_blast_database_results.completion(context)
        return self.api_execution.verify_completion(context, proof)

