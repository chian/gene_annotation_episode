"""Root-owned decision_information.py"""
from __future__ import annotations
from gene_annotation_episode.run_statistics import ExecutionClass
from collections.abc import Mapping
from .task_values import _plain
from .execution_expectations import capture_execution_scopes
from dataclasses import field
from .native_timing_information import read_measurement
import sqlite3

class DecisionInformation:

    def working_state(self, source):
        if self.is_job_source(source):
            return self.job_episodes.working_state(source)
        if not self.is_scientific_source(source):
            return {'assignment': source.request.message.as_record().get('episode_assignment', {})}
        arguments = {'record_selection': self.receipts.selection(source.episode_id)} if self.uses_received_record_context(source) else {}
        return self.store.reasoning_view(source.scope, limit=24, **arguments)

    def resource_context(self, source):
        """Fresh host capacity for parents and children before each new choice.

        Saved decisions retain their original snapshot. Capacity is checked
        atomically again at native dispatch; a planning view grants no slot.
        """
        resources = getattr(self.tools, 'local_resources', None)
        if resources is None:
            return None
        capabilities = []
        if 'launch' in self.episode_bindings.roles:
            read = getattr(self.episode_bindings.for_role('launch'), 'capabilities', None)
            if callable(read):
                capabilities = list(read())
        from gene_annotation_episode.workflow_budget import active_budget
        budget = active_budget()
        whole = {key: budget[key] for key in ('version', 'window_id', 'run_directory', 'environment_bounds') if key in budget}
        whole.update(coverage='Python coordinator, provider, native workers, and all descendants', ownership='One workflow per Codex window; other windows have independent slots.')
        local_snapshot = resources.snapshot()
        from .execution_planning import planning_context
        import sqlite3
        try:
            shared_planning = planning_context(self, local_snapshot)
        except (OSError, sqlite3.Error) as error:
            shared_planning = {'state': 'unavailable', 'reason': type(error).__name__, 'planning': 'Shared observations are unavailable. Do not infer remote availability.'}
        return {'version': 'episode_resource_context_v1', 'local': local_snapshot, 'execution_planning': shared_planning, 'whole_workflow': whole, 'ordinary_tool_job_limits': self.tools.local_job_policy.to_dict(), **({'operation_limits': self.tools.operation_resource_limits()} if callable(getattr(self.tools, 'operation_resource_limits', None)) else {}), 'execution_capabilities': capabilities, 'planning': 'Account for Python, providers and native workers when estimating local capacity. One workflow may run locally in this Codex window; other windows have independent slots. Use observed capacity and the actual configured execution contract. A busy result preserves prepared work for a later retry. Only host admission reserves capacity.'}

    def shared_information_repository(self):
        if self.receipts is None or not hasattr(self.store, 'db'):
            return None
        if not hasattr(self, '_shared_information'):
            from .shared_information import SharedInformation
            self._shared_information = SharedInformation(self.store, self.run_id)
        return self._shared_information

    def shared_information_context(self, source):
        from .shared_information import PARTICIPANT_ROLES
        if source.path[-1][0] not in PARTICIPANT_ROLES:
            return None
        repository = self.shared_information_repository()
        if repository is None:
            return None
        view = repository.context_view(self.binding_context(source))
        if view['upward_recipient'] is None and (not any((view[name] for name in ('needs', 'information_available', 'dispositions')))):
            return None
        return view

    def shared_information_catalog(self, source):
        from .shared_information import PARTICIPANT_ROLES
        if source is None or source.path[-1][0] not in PARTICIPANT_ROLES:
            return []
        repository = self.shared_information_repository()
        return [] if repository is None else repository.catalog(self.binding_context(source))

    def retain_shared_grading_results(self, source, outcome, credit_view):
        """Retain existing saved grading after this original shared read's receipt.

        Normal receipt, attribution and credit projection have already run.
        This copies their authorized results; it neither grades again nor adds
        a credit event or a separate decision. Later versions cannot replace
        this original action's saved numerical payload.
        """
        body = outcome.get('result')
        if outcome.get('status') not in {'completed', 'partial'} or not isinstance(body, Mapping) or body.get('kind') not in {'information', 'disposition'} or ('saved_grading_results' in body):
            return
        context = self.binding_context(source)
        selected = [ref for ref in body.get('evidence_refs', ()) if ref in context.received_record_refs]
        if not selected:
            return
        from .shared_information_results import saved_grading_results
        from .literature_sheet_updates import current_scoring_sheets
        grading_context = self.episode_bindings.initial_decision_context(context)
        delivered_cells = self.episode_bindings.received_report_facts(context)
        literature_sheets = current_scoring_sheets(self.store, context)
        details = credit_view
        total = credit_view.get('detail_pages', {}).get('source_contributions_total')
        projector = self.scientific_projector_for_context(context)
        reader = getattr(projector, 'read_details', None)
        arguments = self.projector_receipt_arguments(projector, context.episode_id)
        if callable(reader) and 'known_record_refs' in arguments and (type(total) is int) and (total > len(credit_view.get('source_contributions', []))):
            details = reader(self.store, _plain(context.scope), **arguments, details_limit=total, details_offset=0)
        saved = saved_grading_results(selected, details, grading_context, delivered_cells, {'literature_current_scoring_sheets': literature_sheets})
        body['saved_grading_results'] = saved
        body['grading_delivery'] = 'Exact saved results from the received grading or scoring sheets.' if saved else 'No saved grading was delivered for these selected records; this message supplies material only.'

    def native_timing_arguments(self, source):
        return {'known_execution_refs': self.receipts.known(source.episode_id, record_type='native_execution'), 'initial_execution_refs': self.receipts.known(source.episode_id, record_type='native_execution', baseline=True)}

    def native_estimation_context(self, source, context):
        binding = getattr(self.tools, 'native_statistics', None)
        available = {item['name'] for item in context.get('tools', [])}
        if binding is None:
            return None
        scopes = {}
        if self.receipts is not None:
            for reference in self.receipts.known(source.episode_id, record_type='native_execution'):
                scope = read_measurement(self.store, reference).execution_class
                scopes[scope.ref] = scope
        previous = context.get('last_local_outcome') or {}
        for value in (previous.get('native_execution_expectations') or {}).get('execution_classes', []):
            scope = ExecutionClass(**value)
            scopes[scope.ref] = scope
        supplied = {ExecutionClass(**value).ref for value in (context.get('execution_expectations') or {}).get('execution_classes', [])}
        scopes = [scope for ref, scope in scopes.items() if ref not in supplied and binding.available_phase(scope.phase, available) and (scope.resource_id == binding.resource_id)]
        if not scopes:
            return None
        recovery = binding.recover_pending_statistics()
        return {**capture_execution_scopes(binding.history_path, scopes), 'statistics_recovery': recovery}

    def annotation_context(self, scope, *, source=None):
        """Separately bound annotation support; never a controller observation."""
        if self.project_annotation_score is None:
            return {}
        arguments = {}
        if getattr(self.project_annotation_score, 'requires_episode_receipts', False):
            if source is None:
                raise ValueError('annotation_support_actual_receiver_required')
            arguments = self.projector_receipt_arguments(self.project_annotation_score, source.episode_id)
        view = self.projection_view(self.project_annotation_score, scope, annotation_collection=True, **arguments)
        if view.get('mode') == 'proposed_annotation_collection':
            return {'proposed_annotations': view['proposed_annotations'], 'annotation_comparisons': view['comparisons'], 'annotation_score_binding': self.annotation_score_binding}
        return {'annotation_score': view['credit'], 'annotation_evidence_vector': view.get('axis_components'), **({'annotation_evidence_status': view['axis_status']} if 'axis_status' in view else {}), **({'annotation_support': view['support']} if 'support' in view else {}), **({'annotation_opposition': view['opposition']} if 'opposition' in view else {}), 'annotation_score_binding': self.annotation_score_binding}

    def local_outcome_preview(self, outcome, *, decision_index=None):
        """Present host-declared generated batches at this one boundary.

        The saved outcome, fact arrays, exact reads and admitted child forms
        remain complete. Fixed publication/failure fields are presentation,
        never work bounds or recursively inferred payload instructions.
        """
        if not isinstance(outcome, Mapping):
            return outcome
        from .shared_information_results import outcome_view as shared_outcome_view
        outcome = shared_outcome_view(outcome)
        from .execution_operand_presentation import plan_outcome_view
        outcome = plan_outcome_view(outcome)
        from gene_annotation_episode.ensembl_acquisition import ensembl_outcome_view
        ensembl_view = ensembl_outcome_view(outcome)
        if ensembl_view is not None:
            return ensembl_view
        batch = outcome.get('published_batch')
        if not isinstance(batch, Mapping) or batch.get('representation') != 'native_publications_v1':
            return outcome
        size = self.restoration_settings['preview_size']

        def counts(total, included):
            return {'total': total, 'included': included, 'truncated': included < total if total is not None else None}
        refs = outcome.get('record_refs', [])
        shown = {**outcome, 'record_refs': refs[:size]}
        preview = {'kind': 'native_publication_batch', 'preview_size': size, 'record_refs': counts(len(refs), len(shown['record_refs'])), 'complete_result_preserved': True}
        body = outcome.get('result')
        if isinstance(body, Mapping):
            body = dict(body)
            if isinstance(body.get('records'), list):
                body['records'] = body['records'][:size]
            preview['rows'] = counts(batch['published_rows_total'], len(body.get('records', [])))
            if isinstance(body.get('retained_record_refs'), list):
                retained = body['retained_record_refs']
                body['retained_record_refs'] = retained[:size]
                preview['retained_record_refs'] = counts(len(retained), len(body['retained_record_refs']))
            body['record_refs_are_preview'] = len(shown['record_refs']) < len(refs)
            if batch['failure_rows_total'] is not None:
                included = max((len(body[field]) for field in ('errors', 'projection_errors') if isinstance(body.get(field), list)), default=0)
                preview['failures'] = counts(batch['failure_rows_total'], included)
            shown['result'] = body
        feedback = outcome.get('feedback')
        if batch['failure_rows_total'] is not None and isinstance(feedback, Mapping) and isinstance(feedback.get('rows'), list):
            shown['feedback'] = feedback
            preview['failures'] = counts(batch['failure_rows_total'], len(shown['feedback']['rows']))
        if batch.get('observation_query') is not None:
            preview['observation_query'] = {**batch['observation_query'], 'limit': max(1, size)}
        if decision_index is not None:
            preview['publication_query'] = {'view': 'publications', 'decision_index': decision_index, 'offset': 0, 'limit': max(1, size)}
        shown['automatic_preview'] = preview
        return shown
