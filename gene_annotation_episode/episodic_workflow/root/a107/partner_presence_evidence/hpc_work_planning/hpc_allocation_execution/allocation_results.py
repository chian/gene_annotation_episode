"""Private allocation results for A107 hpc_execution."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a107.hpc_campaign import accepts
import base64
from datetime import datetime
import hashlib
from gene_annotation_episode.episodic_workflow.root.a107 import hpc_queue
import json
from gene_annotation_episode.episodic_workflow.root.a107.communication import plain
import time
from datetime import timezone




class AllocationResults:
    @staticmethod
    def _collected_unit_ids(ledger, plan):
        return {row['body']['unit']['unit_id'] for row in ledger.records('result')
            if row['body'].get('plan_id') == plan['plan_id']
            and isinstance(row['body'].get('unit'), dict)
            and isinstance(row['body']['unit'].get('unit_id'), str)}

    def _uncollected_completed_unit_ids(self, ledger, plan, current):
        allowed = {unit['unit_id'] for unit in self._candidate(ledger, plan)['units']}
        observed = set(current.get('telemetry', {}).get('completed_unit_ids', ()))
        return (observed & allowed)-self._collected_unit_ids(ledger, plan)

    def _publish(self, context, body):
        artifact = self.store.artifact(hpc_queue.canonical(body), 'application/json')
        return self.store.put('source', {'provider': 'episode.hpc_result',
            'accession': 'hpc_'+hpc_queue.digest([self.run_id, context.episode_id, body]),
            'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
            'version': 'hpc_result_v1', 'retrieved_at': datetime.fromtimestamp(
                body['unit']['finished_at'], timezone.utc).isoformat()},
            origin='tool')['id']

    async def _collect_original_results(self, context, tool_name, arguments, operation_key, ledger, selection, references, commission, configuration, plan, target, candidate, observation, allocation, allocation_window, observation_ref, current, measured_ref):
        accepted, failures = ([], [])
        for row in (allocation or {}).get('units', []):
            if row['state'] not in {'complete', 'failed'}:
                continue
            unit = next((unit for unit in candidate['units'] if unit['unit_id'] == row['unit_id']))
            expected_path = plan['manifest']['workspace'] + '/units/' + unit['unit_id'] + '/result.json'
            if not row.get('result_path'):
                failures.append({'unit_id': unit['unit_id'], 'reason': 'missing_original_result_receipt', 'expected_path': expected_path, 'detail': 'The unit did not record this output at completion. Files found elsewhere cannot replace its missing completion hash. Future workers must write to HPC_UNIT_DIRECTORY.'})
                continue
            if row['result_path'] != expected_path or row['obligation_id'] != unit['obligation_id']:
                raise ValueError('result_not_owned_by_original_work_unit')
            window = ledger.once('result-window:' + operation_key + ':' + unit['unit_id'], 'result_window', lambda: self._window(target, expected_path, commission['limits']['result_limit_bytes'], operation_key + ':' + unit['unit_id'])[0])
            payload = base64.b64decode(window['bytes_base64'], validate=True)
            if hashlib.sha256(payload).hexdigest() != row['result_sha256']:
                raise ValueError('result_changed_since_unit_completion')
            document = json.loads(payload)
            receipt = {'run_id': self.run_id, 'episode_id': context.episode_id, 'scope': plain(context.scope), 'plan_id': plan['plan_id'], 'job_id': target['execution_id'], 'unit': row, 'document': document, 'window': window, 'observation_ref': observation_ref}
            source_ref = self._publish(context, receipt)
            references.append(source_ref)
            result_ref = ledger.put('result', {**receipt, 'source_ref': source_ref})
            if row['state'] == 'complete' and row.get('returncode') == 0 and accepts(document, commission['obligations'][unit['obligation_id']]):
                ledger.accept(unit['obligation_id'], result_ref)
                accepted.append({'obligation_id': unit['obligation_id'], 'result_ref': result_ref})
            else:
                failures.append({'unit_id': unit['unit_id'], 'reason': 'original_acceptance_predicate_not_met'})
        if current['state'] in ('complete', 'failed'):
            measured = ledger.read(measured_ref)
            if allocation is not None:
                measured['success'] = len(accepted) == len(candidate['units'])
                measured['observed_at'] = max(measured['observed_at'], time.time())
                ledger.put('measured', measured)
            ledger.put('closed', {'plan_id': plan['plan_id'], 'observation_ref': observation_ref})
            self.export_closed(ledger, plan)
        result = {'accepted': accepted, 'rejected': failures, 'observation_ref': observation_ref, 'credit': ledger.credit_view()}
        outcome = {'status': 'completed', 'record_refs': references, 'changed_record_refs': references, 'result': result}
        return ledger.save_action(operation_key, selection, outcome)
