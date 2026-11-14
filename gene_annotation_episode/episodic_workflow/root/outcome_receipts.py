"""Root-owned outcome_receipts.py"""
from __future__ import annotations
from collections.abc import Mapping
from .episode_journal import WorkflowError
from .task_values import _digest
from .task_values import _json
from .task_values import _plain
from .reference_selection import _references_in
from gene_annotation_episode.episodic_workflow.root.method_loop.durable import canonical
from dataclasses import field
import json

class OutcomeReceipts:

    def uses_received_record_context(self, source):
        """Scientific visibility follows custody, not the chosen credit scalar."""
        return self.receipts is not None and self.is_scientific_source(source)

    def receipt_projection(self, source):
        if not self.is_scientific_source(source):
            return False
        projector = self.scientific_projector_for_context(self.binding_context(source))
        return bool(getattr(projector, 'requires_episode_receipts', False))

    def scientific_projector_for_context(self, context):
        if len(context.path) == 1:
            return self.project_credit
        binding = self.episode_bindings.for_path(context.path) if context.role in self.episode_bindings.roles else None
        select = getattr(binding, 'credit_projector', None)
        declared = select(context) if select is not None else None
        if declared is None:
            raise ValueError('scientific_task_credit_not_declared:' + context.role)
        return declared

    def projector_receipt_arguments(self, projector, episode_id):
        if not getattr(projector, 'requires_episode_receipts', False):
            return {}
        if self.receipts is None:
            raise ValueError('numerical_credit_requires_episode_receipts')
        arguments = {'known_record_refs': self.receipts.known(episode_id)} if getattr(projector, 'requires_known_record_refs', False) else {'known_assessment_refs': self.receipts.known(episode_id, record_type='assessment')}
        if getattr(projector, 'requires_receiver_context', False):
            arguments.update(run_id=self.run_id, episode_id=episode_id)
        return arguments

    def projection_arguments(self, source):
        arguments = self.child_credit_arguments(source) if len(source.path) > 1 else {}
        projector = self.scientific_projector_for_context(self.binding_context(source))
        arguments.update(self.projector_receipt_arguments(projector, source.episode_id))
        return arguments

    def receive_outcome(self, source, selection, result, index):
        if self.progress_provider is not None and self.progress_receipt_order == 'received_progress_order_v1':
            self.progress_provider.receive_outcome(source.episode_id, result, source.scope, f'{self.run_id}:{source.episode_id}:{index}:own_progress')
        if self.receipts is not None and (not self.is_job_source(source)):
            references = list(result.get('record_refs', []))
            if selection.get('kind') == 'tool' and selection.get('tool') == 'state.query':
                references.extend((row['id'] for row in (result.get('result') or {}).get('records', [])))
            self.receipts.receive(source.episode_id, references, kind='own_action', source_index=index)
            projection_read = selection.get('kind') == 'tool' and selection.get('tool') in {'episode.credit', 'episode.annotation_score', 'episode.monitoring_information'}
            derived = [] if projection_read else self.receive_tool_attributions(source, index, kind='own_action')
            if derived:
                result['record_refs'] = list(dict.fromkeys([*result.get('record_refs', []), *derived]))
                references.extend((ref for ref in derived if ref not in references))

    async def automatic_score_updates(self, source, index, result):
        """Run owner-declared score judgments once, outside a write transaction."""
        binding = self.specialist(source)
        prepare = getattr(binding, 'automatic_score_judgments', None)
        if prepare is None:
            return result
        complete = getattr(binding, 'complete_score_judgment', None)
        if complete is None:
            raise ValueError('automatic_score_judgment_completion_owner_required')
        if self.store.db.in_transaction:
            raise ValueError('automatic_score_judgment_requires_committed_inputs')
        context = self.binding_context(source)
        judgments = prepare(context)
        if not judgments:
            return result
        updated = _plain(result)
        for judgment in judgments:
            if 'completed_outcome' in judgment:
                outcome = judgment['completed_outcome']
                original = judgment.get('completed_provenance', {})
                if original.get('episode_id') == source.episode_id and original.get('decision_index') != index and (set(outcome.get('record_refs', [])) <= set(context.received_record_refs)):
                    continue
            else:
                judgment_ref = judgment['judgment_ref']
                if self.store.db.in_transaction:
                    raise ValueError('automatic_score_judgment_requires_committed_inputs')
                provenance = {'version': 'automatic_score_judgment_call_v1', 'episode_id': source.episode_id, 'decision_index': index, 'session_key': judgment_ref, 'phase': 'REASONING', 'provider': type(self.provider).__module__ + '.' + type(self.provider).__qualname__}
                model = getattr(self.provider, 'roles', {}).get('REASONING')
                if isinstance(getattr(model, 'model', None), str):
                    provenance['model'] = model.model
                if isinstance(getattr(model, 'reasoning_effort', None), str):
                    provenance['reasoning_effort'] = model.reasoning_effort
                try:
                    response = await self.provider.complete(judgment_ref, 'REASONING', judgment['instructions'], judgment['context'], judgment['output_schema'])
                except Exception as error:
                    outcome = complete(context, judgment_ref, provenance=provenance, failure={'code': 'automatic_score_judgment_call_failed', 'exception_type': type(error).__name__})
                else:
                    outcome = complete(context, judgment_ref, response, provenance=provenance)
            for field in ('record_refs', 'changed_record_refs'):
                updated[field] = list(dict.fromkeys([*updated.get(field, []), *outcome.get(field, [])]))
            if self.receipts is not None:
                self.receipts.receive(source.episode_id, outcome.get('record_refs', []), kind='own_action', source_index=index)
        return updated

    def receive_tool_attributions(self, source, index, *, kind):
        """Derive tool-specific numeric/trait evidence from actual receipts.

        This runs before projection, including after a late sibling delivery.
        It neither widens the child's typed form nor reads unreceived evidence.
        The receiver's host derivations are recorded in its action outcome.
        """
        callback = getattr(self.tools, 'received_attributions', None)
        if callback is None or self.receipts is None or source.path[-1][0] not in {'annotation', 'scientific_process', 'improvement'}:
            return []
        context = self.binding_context(source)
        known = set(self.receipts.known(source.episode_id))
        structural = getattr(self.tools, 'received_structural_attributions', None)
        generated, needs = structural(context, known, input_authority=self.services.protein_structure_input_authority(), hpc_result_reader=self.services.read_received_hpc_result) if callable(structural) else ([], [])
        hpc = getattr(self.tools, 'received_hpc_attributions', None)
        if callable(hpc):
            received, pending = hpc(context, known | set(generated), hpc_result_reader=self.services.read_received_hpc_result)
            generated.extend(received)
            needs.extend(pending)
        attributed, attribution_needs = callback(context, known | set(generated))
        generated.extend(attributed)
        needs.extend(attribution_needs)
        generated = [ref for ref in generated if ref not in known]
        repository = self.shared_information_repository()
        if context.role == 'scientific_process' and repository is not None and (repository.parent(context, require_active=True) is not None):
            for request_ref, need in needs:
                args = {'target_ref': need['target_ref'], 'question': 'Supply the specific attribution inputs for this measurement or local trait.', 'required_information': canonical({'measurement_or_request_ref': request_ref, 'policy': need['policy'], 'physical_feature_key': need.get('physical_feature_key'), 'missing': need['missing'], **({'required_operands': need['required_operands']} if need.get('required_operands') else {})}), 'reason': 'Only this measurement/use is unresolved; native evidence and other traits retain their own scores.', 'blocking': False, 'available_record_refs': [request_ref]}
                published = repository.execute(context, 'shared.request_information', args, known_record_refs=known, operation_key=f'{self.run_id}:{source.episode_id}:tool_attribution_need:{_digest(args)}')
                generated.extend((ref for ref in published['record_refs'] if ref not in known))
        generated = list(dict.fromkeys(generated))
        if generated:
            self.receipts.receive(source.episode_id, generated, kind=kind, source_index=index)
        return generated

    def receive_native_outcome(self, source, result, index):
        if self.native_timing_information is not None:
            references = list(result.get('native_execution_refs', []))
            references.extend((row['id'] for row in (result.get('result') or {}).get('records', []) if row.get('record_type') == 'native_execution' and 'measurement' in row))
            self.receipts.receive(source.episode_id, references, kind='own_action', source_index=index)

    def receive_form(self, source, admitted, schema, index, *, redelivery=False):
        with self.store.transaction():
            return self._receive_form(source, admitted, schema, index, redelivery=redelivery)

    def _receive_form(self, source, admitted, schema, index, *, redelivery=False):
        if self.receipts is not None and (not redelivery) and (not self.is_job_source(source)):
            from .episode_return_records import EpisodeReturnRecords
            references = EpisodeReturnRecords(self.store, self.run_id, failure_prefix='recorded_admission_').recorded_admission_references(self.binding_context(source), admitted, schema, index)
            if references is not None:
                return references
        if self.progress_provider is not None:
            self.progress_provider.receive_form(source.episode_id, admitted, schema, source.scope, f'{self.run_id}:{source.episode_id}:{index}:typed_form')
        if self.receipts is None or self.is_job_source(source):
            return []
        references = _references_in({}, self.store.get, forms=[(admitted, schema)], reference_subset=lambda refs: self.store.reference_subset(refs, source.scope))
        references.extend(self.episode_bindings.received_form_references(self.binding_context(source), admitted, schema, f'{self.run_id}:{source.episode_id}:{index}:typed_form'))
        references = list(dict.fromkeys(references))
        if self.native_timing_information is not None and self.job_episodes is not None:
            with self.store.transaction():
                key = (self.run_id, source.episode_id, index)
                row = self.store.db.execute('SELECT timing_receipts FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=?', key).fetchone()
                if row is None:
                    raise WorkflowError('received_form_requires_recorded_attempt')
                if row[0] is None:
                    received = self.job_episodes.received_timing_records(self.store, admitted, schema, source.scope)
                    self.store.db.execute('UPDATE runtime_report_attempts SET timing_receipts=? WHERE run_id=? AND parent_episode_id=? AND decision_index=?', (_json(received), *key))
                else:
                    received = json.loads(row[0])
            references.extend((ref for ref in received['native_execution_refs'] if ref not in references))
        self.receipts.receive(source.episode_id, references, kind='report_redelivery' if redelivery else 'child_form', source_index=index)
        references.extend((ref for ref in self.receive_tool_attributions(source, index, kind='report_redelivery' if redelivery else 'child_form') if ref not in references))
        return references

    def record_selection(self, episode_id):
        return {'run_id': self.run_id, 'episode_id': episode_id, 'known_record_refs': [] if self.receipts is None else list(self.receipts.known(episode_id)), 'initial_known_record_refs': [] if self.receipts is None else list(self.receipts.known(episode_id, baseline=True))}

    def progress_selection(self, source):
        message = source.request['message'] if isinstance(source.request, Mapping) else source.request.message.as_record()
        initial = list(message.get('episode_assignment', {}).get('known_progress_refs', []))
        references = [*initial, *self.services.received_progress_refs(source.episode_id)]
        if self.progress_receipt_order == 'received_progress_order_v1':
            return {'known_progress_refs': list(dict.fromkeys(references)), 'initial_progress_refs': list(initial)}
        rows = self.store.db.execute("SELECT refs.value FROM runtime_actions actions JOIN json_each(actions.result,'$.progress_refs') refs WHERE actions.run_id=? AND actions.episode_id=? AND (json_extract(actions.result,'$.status') IN ('completed','partial') OR (json_extract(actions.action,'$.kind') IN ('tool','reason') AND json_extract(actions.result,'$.status') IN ('failed','unavailable'))) ORDER BY actions.decision_index, refs.key", (self.run_id, source.episode_id))
        references.extend((row[0] for row in rows))
        return {'known_progress_refs': list(dict.fromkeys(references)), 'initial_progress_refs': list(initial)}
