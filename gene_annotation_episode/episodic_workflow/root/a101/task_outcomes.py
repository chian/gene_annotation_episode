"""Private annotation task_outcomes."""

async def execute(self, selection, index):
    journal = self.workflow.journal
    old = journal.row('runtime_actions', self.episode_id, index)
    if old and json.loads(old['action']) != selection:
        raise WorkflowError('reconstructed selected work changed')
    if old and old['result'] is not None:
        result, credit = (json.loads(old['result']), old['credit'])
    else:
        if self.path[-1][0] == 'scientific_process':
            self.workflow.scientific_process_binding.validate_execution_context(self.workflow.binding_context(self))
        journal.save('runtime_actions', {'episode_id': self.episode_id, 'decision_index': index, 'action': _json(selection), 'result': None, 'credit': None})
        key = f'{self.workflow.run_id}:{self.episode_id}:{index}'
        with journal.measure('runtime_actions', self.episode_id, index):
            if selection['kind'] == 'reason':
                payload = selection['commit']
                account_context = {'account_invocation': (self.workflow.run_id, self.episode_id)} if payload.get('interpretation_accounts') else {}
                specialist = self.workflow.specialist(self)
                execute_reasoning = getattr(specialist, 'execute_reasoning', None)
                result = execute_reasoning(self.workflow.binding_context(self), selection, key) if execute_reasoning is not None else None
                if result is None:
                    result = self.workflow.store.commit_reasoning(payload, self.scope, key, **account_context)
            elif selection['kind'] == 'wait':
                try:
                    result = await self.workflow.perform_selected_wait(self, selection['condition'], index)
                except EventTargetError as error:
                    result = {'status': 'failed', 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': _wait_target_feedback(error, status='failed')}
            else:
                result = self.workflow.execute(self, selection['tool'], selection['arguments'], decision_index=index, operation_key=key)
            if inspect.isawaitable(result):
                result = await result
        result = {**result, 'pending_work_after_action': self.workflow.pending_work(self)}
        with self.workflow.store.transaction() if self.workflow.execution_binding is not None else nullcontext():
            journal.save('runtime_actions', {'episode_id': self.episode_id, 'decision_index': index, 'action': _json(selection), 'result': _json(result), 'credit': None})
            self.last_outcome, self.last_outcome_index = (result, index)
            if result['status'] not in ('completed', 'partial'):
                self.feedback = result.get('feedback') or {'status': result['status'], 'category': result.get('error_code', 'work_failed')}
            self.checkpoint()
        credit = None
    observed_outcome = observes_action_outcome(selection['kind'], result['status'])
    with self.workflow.store.transaction() if self.workflow.execution_binding is not None else nullcontext():
        self.workflow.receive_native_outcome(self, result, index)
        if credit is None and observed_outcome:
            self.workflow.receive_outcome(self, selection, result, index)
    if credit is None and observed_outcome and (selection['kind'] != 'wait'):
        result = await self.workflow.automatic_score_updates(self, index, result)
    with self.workflow.store.transaction() if self.workflow.execution_binding is not None else nullcontext():
        if credit is None and observed_outcome:
            if selection['kind'] == 'wait':
                credit = self.workflow.last_observed_credit(self)
            else:
                credit_view = self.workflow.source_credit_view(self)
                credit = credit_view['credit']
                if selection.get('kind') == 'tool' and selection.get('tool') == 'shared.read_information':
                    self.workflow.retain_shared_grading_results(self, result, credit_view)
            journal.save('runtime_actions', {'episode_id': self.episode_id, 'decision_index': index, 'action': _json(selection), 'result': _json(result), 'credit': credit})
        if self.workflow.execution_binding is not None and observed_outcome:
            self.workflow.completions.stage(self.episode_id, index, label=f"{selection['kind']}:{index}", kind='own_action', controller_input=self.workflow.controller_value(self, index, credit), child_return=None)
            self.last_outcome, self.last_outcome_index = (result, index)
            self.checkpoint()
    self.last_outcome = result
    self.last_outcome_index = index
    if not observed_outcome:
        raise ActionFailure(result.get('feedback') or {'status': result['status'], 'category': result.get('error_code', 'work_failed')})
    return self.workflow.controller_value(self, index, credit)

def _bind_original_runtime(namespace):
    from gene_annotation_episode.episodic_workflow.root.a101.library.live_runtime_functions import bind_functions
    selected = bind_functions(namespace, {name: globals()[name] for name in ('execute',)},
        runtime_module='gene_annotation_episode.episodic_workflow.root.a101.runtime', qualified_names={'execute': 'AnnotationTask.execute'},
        defining_module='gene_annotation_episode.episodic_workflow.root.a101.task_outcomes')
    globals().update(selected)

from gene_annotation_episode.episodic_workflow.root.a101 import runtime as _original_runtime
_bind_original_runtime(vars(_original_runtime))
