"""Private prediction operations for A103 prediction."""
from __future__ import annotations
import asyncio
from gene_annotation_episode.episodic_workflow.root.a103 import hpc_queue
import json
from gene_annotation_episode.episodic_workflow.root.a103.execution_contracts import obj
from gene_annotation_episode.episodic_workflow.root.a103.communication import plain
from gene_annotation_episode.episodic_workflow.root.a103.library import hpc_prediction as prediction
import shlex
import subprocess
import time
from gene_annotation_episode.episodic_workflow.root.a103.hpc_campaign import validate_commission
from gene_annotation_episode.episodic_workflow.root.a103.domain import validate_schema

TEXT = {'type': 'string', 'minLength': 1}
STRINGS = {'type': 'array', 'uniqueItems': True, 'items': TEXT}

class PredictionOperations:
    def catalog(self, context):
        shared = [
            ('hpc.read', 'Read retained HPC evidence by its exact identity.', obj({'reference': TEXT})),
            ('hpc.compare', 'Compare all approved portfolios; no work is selected or launched.',
                obj({'model_ref': TEXT, 'queue_ref': TEXT}))]
        if self.memory:
            shared.append(('hpc.history.refresh', 'Read age-weighted shared timing history once. '
                'No remote discovery, polling credit, or new scientific work.', obj({})))
        shared += [
                ('hpc.discovery.run', 'Run one lightweight remote inspection or documentation retrieval through the established SSH transport. No job submission, installation or scientific computation; those belong to Launch and the allocation.',
                    obj({'command': TEXT})),
                ('hpc.candidate.propose', 'Retain an executable portfolio selected by this episode. candidate_json is JSON with id, queue, nodes, wall_seconds (PBS allocation request), features (numeric map including worker_threads/workload sizes), optional resource_capacity {cpu_threads, memory_bytes} describing actual allocation capacity, units (unit_id, obligation_id, argv, environment, effort, optional reports_progress), optional files [{path: relative path, text: exact contents}], and preparation instructions for Launch. effort is a positive finite number expressing relative work, for example 1.0; workload sizes belong in features. No per-unit execution timers. Use {allocation_workspace} for the eventual directory. Existing candidate identities are immutable.',
                    obj({'candidate_json': TEXT})),
                ('hpc.queue.observe', 'Acquire PBS queue and ALCF score/status once and transform them.', obj({}))]
        entries = shared+[('hpc.model.fit', 'Fit selected measured history; validate on the fixed disjoint cases.',
                           obj({'training_ids': STRINGS}))]
        return [{'name': name, 'description': description, 'input_schema': schema}
                for name, description, schema in entries]

    async def execute(self, context, tool_name, arguments, operation_key):
        entries = {row['name']: row for row in self.catalog(context)}
        if tool_name not in entries:
            raise ValueError('tool_not_available_to_hpc_role')
        arguments = plain(arguments)
        validate_schema(arguments, entries[tool_name]['input_schema'])
        ledger = self.state(context)
        if not ledger.records('model'):
            self.initialize(context)
        selection = {'tool': tool_name, 'arguments': arguments, 'episode_id': context.episode_id}
        old = ledger.cached(operation_key, selection)
        if old is not None:
            return old
        ledger.put('action_intent', selection, identity='action:'+operation_key)
        references = []
        commission = ledger.commission
        configuration = self.resources[commission['resource_id']]
        if tool_name == 'hpc.read':
            try:
                result = self.read_evidence(context, ledger, arguments['reference'])
            except (ValueError, KeyError) as error:
                return ledger.save_action(operation_key, selection, {
                    'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                    'feedback': {'category': 'arguments_or_reference', 'code': str(error)}})
        elif tool_name == 'hpc.history.refresh':
            result = ledger.once('shared_history:'+operation_key, 'shared_history', lambda: self._shared_history(ledger))
        elif tool_name == 'hpc.discovery.run':
            # Read-only discovery can be repeated after interrupted observation;
            # all mutations and submissions use the durable Launch operations.
            command = ('cd '+shlex.quote('/lus/flare/projects/BioReason-Aurora-Test')+
                       ' && '+arguments['command'])
            def observe():
                from gene_annotation_episode.episodic_workflow.root.a103.execution_guidance import resource_identity
                cache_key = resource_identity(commission['resource_id'], configuration)+':'+hpc_queue.digest(command)
                if self.memory:
                    cached = self.memory.latest(cache_key, 'inventory')
                    if cached['state'] == 'fresh':
                        return cached['data']
                completed = subprocess.run([*configuration['ssh_argv'], command],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
                value = {'command': arguments['command'], 'returncode': completed.returncode,
                    'stdout': completed.stdout[:65536].decode('utf-8', 'replace'),
                    'stderr': completed.stderr[:8192].decode('utf-8', 'replace'),
                    'observed_at': time.time(), 'truncated': len(completed.stdout) > 65536}
                if self.memory and completed.returncode == 0:
                    self.memory.observe(cache_key, 'inventory', value, observed_at=value['observed_at'],
                                        provenance=[str(ledger.path), 'discovery:'+operation_key])
                return value
            result = await asyncio.to_thread(ledger.once, 'discovery:'+operation_key, 'discovery', observe)
        elif tool_name == 'hpc.candidate.propose':
            try:
                candidate = json.loads(arguments['candidate_json'])
                candidates = self._candidates(ledger)
                prior = next((row for row in candidates if row['id'] == candidate['id']), None)
                if prior is not None and prior != candidate:
                    raise ValueError('candidate_identity_is_immutable')
                validate_commission({**commission, 'candidates': candidates if prior else candidates+[candidate]}, self.resources)
            except (ValueError, KeyError, TypeError) as error:
                return ledger.save_action(operation_key, selection, {
                    'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                    'feedback': {'category': 'arguments_or_reference', 'code': str(error)}})
            reference = ('caller_candidate:'+candidate['id'] if candidate in commission['candidates'] else
                         ledger.put('candidate', candidate, identity='candidate:'+candidate['id']))
            result = {'candidate_ref': reference, 'candidate_id': candidate['id']}
        elif tool_name == 'hpc.queue.observe':
            reference = 'queue:'+hpc_queue.digest(operation_key)
            result = ledger.once(reference, 'queue', lambda: self._observe_queue(ledger, configuration))
            result = {'queue_ref': reference, 'features': [hpc_queue.features(result['snapshot'], candidate)
                                                         for candidate in self._candidates(ledger)],
                      'snapshot': result['snapshot']}
        elif tool_name == 'hpc.model.fit':
            selected = set(arguments['training_ids'])
            if self.memory is not None:
                ledger.once('shared_history:'+operation_key, 'shared_history', lambda: self._shared_history(ledger))
            cases = self._history(ledger)
            if not selected <= set(cases) or selected.intersection(commission['validation_ids']):
                raise ValueError('training_ids_must_be_original_nonvalidation_cases')
            heldout = [cases[key] for key in commission['validation_ids']]
            historical_selected = selected.intersection(row['id'] for row in commission['history'])
            if historical_selected and heldout and max(cases[key]['observed_at'] for key in historical_selected) >= min(row['observed_at'] for row in heldout):
                raise ValueError('training_must_precede_temporal_validation')
            model = prediction.fit(commission['model'], [cases[key] for key in selected])
            model_ref = ledger.put('model', model)
            # Fixed historical validation cannot measure a model trained on
            # later completed allocations. Those updates earn prospective
            # credit when the next real outcomes arrive, not retrospective Q.
            later_training = selected-set(row['id'] for row in commission['history'])
            quality = None if later_training else self._quality(ledger, model)
            baseline = self._quality(ledger, ledger.read('reference_model'))
            ledger.put('model_choice', {'operation_key': operation_key, 'model_ref': model_ref,
                                       'episode_id': context.episode_id})
            if quality is not None:
                ledger.model_credit(model_ref, quality-baseline)
            else:
                ledger.model_credit(model_ref, 0.)
            result = {'model_ref': model_ref, 'validation_quality': quality,
                      'reference_quality': baseline, 'credit': ledger.credit_view()}
        elif tool_name == 'hpc.compare':
            try:
                result = {'comparisons': self._comparisons(ledger, arguments['model_ref'], arguments['queue_ref'])}
            except (ValueError, KeyError) as error:
                return ledger.save_action(operation_key, selection, {
                    'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                    'feedback': {'category': 'arguments_or_reference', 'code': str(error),
                        'recovery': 'Use a model_ref from hpc.model.fit or hpc_model_ref and a queue_ref '
                            'from hpc.queue.observe or hpc_queue_refs; a resource identity is not a queue observation.'}})
            result['comparison_ref'] = ledger.put('comparison', {**result, **arguments,
                'episode_id': context.episode_id, 'operation_key': operation_key})
        outcome = {'status': 'completed', 'record_refs': references, 'changed_record_refs': references, 'result': result}
        return ledger.save_action(operation_key, selection, outcome)
