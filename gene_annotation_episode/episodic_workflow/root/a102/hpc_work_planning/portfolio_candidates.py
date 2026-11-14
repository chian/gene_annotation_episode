"""Private portfolio candidates for A102 hpc."""
from __future__ import annotations
import json
from gene_annotation_episode.episodic_workflow.root.a102.hpc_campaign import validate_commission




class PortfolioCandidates:
    async def _propose_portfolio(self, context, tool_name, arguments, operation_key, ledger, selection, references, commission, configuration):
        try:
            candidate = json.loads(arguments['candidate_json'])
            candidates = self._candidates(ledger)
            prior = next((row for row in candidates if row['id'] == candidate['id']), None)
            if prior is not None and prior != candidate:
                raise ValueError('candidate_identity_is_immutable')
            validate_commission({**commission, 'candidates': candidates if prior else candidates + [candidate]}, self.resources)
        except (ValueError, KeyError, TypeError) as error:
            return ledger.save_action(operation_key, selection, {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'category': 'arguments_or_reference', 'code': str(error)}})
        reference = 'caller_candidate:' + candidate['id'] if candidate in commission['candidates'] else ledger.put('candidate', candidate, identity='candidate:' + candidate['id'])
        result = {'candidate_ref': reference, 'candidate_id': candidate['id']}
        outcome = {'status': 'completed', 'record_refs': references, 'changed_record_refs': references, 'result': result}
        return ledger.save_action(operation_key, selection, outcome)
