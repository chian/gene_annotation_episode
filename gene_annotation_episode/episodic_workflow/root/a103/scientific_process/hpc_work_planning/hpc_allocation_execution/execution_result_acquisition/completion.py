"""Private A103 Results completion."""
from __future__ import annotations
from .execution_contracts import ROLE_KINDS, canonical, digest, is_native_blast_database_target, is_standard_blast_database_target, json, plain, validate_completion_proof

class ResultsCompletion:

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
        if self._target(context)['resource_kind'] == 'api':
            return self.api_execution.completion_for_action(context, operation_key)
        if self.native_hmmer_preparation_results is not None and self.native_hmmer_preparation_results.applies(context):
            proof = self.native_hmmer_preparation_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_blast_results is not None and self.native_blast_results.applies(context):
            proof = self.native_blast_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        if self.native_hmmer_results.applies(context):
            proof = self.native_hmmer_results.completion(context)
            return proof if proof is not None and proof['operation_key'] == operation_key else None
        return self._proof_for_action(context, operation_key)

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
        if self._target(context)['resource_kind'] == 'api':
            return self.api_execution.verify_completion(context, proof)
        if self.native_hmmer_preparation_results is not None and self.native_hmmer_preparation_results.applies(context):
            return proof == self.native_hmmer_preparation_results.completion(context)
        if self.native_blast_results is not None and self.native_blast_results.applies(context):
            return proof == self.native_blast_results.completion(context)
        if self.native_hmmer_results.applies(context):
            return proof == self.native_hmmer_results.completion(context)
        return bool(proof and canonical(proof) == canonical(self._proof_for_action(context, proof.get('operation_key', ''))))
