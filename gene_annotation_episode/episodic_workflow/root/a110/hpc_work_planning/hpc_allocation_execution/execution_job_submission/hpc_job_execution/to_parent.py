from __future__ import annotations
from .execution_contracts import NATIVE_RESULT_ORIGIN
from .execution_contracts import ROLE_KINDS
from .execution_contracts import deepcopy
from .execution_contracts import plain
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import fact_sources
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import resolve
from .execution_contracts import validate_form

class NativeParentReturns:

    def required_return_sources(self, parent, role):
        """Preserve the original job identity across a scientific return."""
        if parent is not None and parent.path[-1][0] == 'scientific_process' and getattr(self.services, 'annotation_task_required', lambda: False)():
            pass
        return ()
    fact_sources = fact_sources
    resolve = resolve

    def facts(self, context, completion_snapshot):
        return {**self._live_facts(context, completion_snapshot), **self._closed_credit_facts(context, completion_snapshot)}

    def _live_facts(self, context, completion_snapshot):
        native_empty = {}
        if self.native_flux_balance_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_return_views import fba_fact_sources
            native_empty.update({source: [] for source in fba_fact_sources()})
        extra = self._delegate(context).facts(self._practical_context(context), completion_snapshot)
        with self.store.read_snapshot():
            read = self.job_progress_provider.targets._handoff_reader()
            _, handoffs, results = self._received(context, _handoff_read=read)
            for reference in extra['practical_receipt_refs']:
                try:
                    target, _, returnable = read(reference, context.scope)
                    target = self._context_target(context, target)
                    if returnable:
                        handoffs[reference] = target
                except ValueError:
                    pass
            completed = extra.get('practical_completed', False)
            return {**native_empty, **extra, 'execution_handoff_refs': sorted(handoffs), 'execution_result_refs': sorted((ref for ref, body in results.items() if body['windows'])), 'execution_file_source_refs': sorted({row['source_ref'] for body in results.values() for row in body.get('captured_files', []) if row['source_ref'] is not None}), 'execution_file_capture_outcomes': self.local_file_sources.outcomes_for_context(context) if self.local_file_sources.applies(context) else [], 'execution_result_origin': deepcopy(NATIVE_RESULT_ORIGIN) if any((body['windows'] for body in results.values())) else None, 'execution_completed': completed}

    def validate_report(self, context, form, original_schema):
        if self.native_flux_balance_returns is not None:
            self.native_flux_balance_returns.validate_received_report(context, form, original_schema)
        validate_form(form, original_schema, lambda ref, ns: self.resolve(context, ref, ns))
        fact_fields = {name: declared['x-source'] for name, declared in plain(original_schema).get('properties', {}).items() if declared.get('x-source') is not None}
        if not fact_fields:
            return
        facts = self.facts(context, {})
        for name, source in fact_fields.items():
            if source in facts and form[name] != facts[source]:
                raise ValueError('execution_report_disagrees_with_recorded_facts')
