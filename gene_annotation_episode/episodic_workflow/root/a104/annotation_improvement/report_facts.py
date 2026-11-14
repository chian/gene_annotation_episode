"""A104 original implicit improvement responsibility."""
from __future__ import annotations
from ..library.live_runtime_functions import bind_functions as _bind_functions

def facts(self, source, *, completion_record=None):
    with self.store.read_snapshot():

        def ordered_refs(field):
            rows = self.store.db.execute('SELECT refs.value FROM runtime_actions actions JOIN json_each(actions.result, ?) refs WHERE actions.run_id=? AND actions.episode_id=? AND actions.result IS NOT NULL ORDER BY actions.decision_index, refs.key', ('$.' + field, self.run_id, source.episode_id))
            return list(dict.fromkeys((row[0] for row in rows)))
        committed = ordered_refs('record_refs')
        changed = ordered_refs('changed_record_refs')
        changed_types = {ref: self.store.get(ref)['record_type'] for ref in changed}
        last = (source.last_outcome or {}).get('record_refs', [])
        unseen = []
        for ref in last:
            if ref not in source.report_basis:
                record = self.store.get(ref)
                if record.get('record_type') == 'observation':
                    unseen.append(ref)
        specialist = self.specialist(source)
        credit_snapshot = {} if callable(getattr(specialist, '_closed_credit_facts', None)) else None
        credit_view = self.source_credit_view(source) if credit_snapshot is None else self.source_credit_view(source, binding_snapshot=credit_snapshot)
        facts = {'credit': credit_view['credit'], 'subject_refs': source.scope['subject_refs'], 'committed_record_refs': committed, 'changed_record_refs': changed, 'changed_annotation_refs': [ref for ref in changed if changed_types[ref] == 'annotation'], 'changed_assessment_refs': [ref for ref in changed if changed_types[ref] == 'assessment'], 'changed_interpretation_account_refs': [ref for ref in changed if changed_types[ref] == 'interpretation_account'], 'last_outcome_refs': last, 'interpretation_basis_refs': source.report_basis, 'observations_after_report_basis': unseen, 'episode_yield': closing_yield(completion_record), 'pending_handles': self.pending_handles(source)}
        if self.native_event_information is not None:
            facts.update(self.native_event_information.facts(self.binding_context(source)))
        if self.is_job_source(source):
            facts.update(self.job_episodes.facts(source, credit_view=credit_view))
        else:
            if self.project_annotation_score is not None:
                annotation = self.annotation_context(source.scope, source=source)
                for key in ('annotation_score', 'proposed_annotations', 'annotation_comparisons'):
                    if key in annotation:
                        facts[key] = annotation[key]
            if self.resource_estimator is not None:
                facts['resource_tool_estimates'] = recorded_forecasts(self.store, run_id=self.run_id, episode_id=source.episode_id)
        if self.native_timing_information is not None:
            native = self.native_timing_information.read_details(self.store, source.scope, details_limit=None, details_offset=0, **self.native_timing_arguments(source))
            facts['monitoring_information_credit'] = credit_view['monitoring_information_credit']
            facts['native_execution_measurements'] = native['native_execution_measurements']
        snapshot = {'completion': None if completion_record is None else {'ended_by': completion_record.ended_by, 'end_reason': completion_record.end_reason, 'units_consumed': completion_record.units_consumed}, 'own_action_count': None if completion_record is None else completion_record.units_consumed, 'last_outcome_refs': last, 'committed_record_refs': committed, 'changed_record_refs': changed, 'report_basis_refs': source.report_basis}
        if specialist is not None:
            if credit_snapshot is not None:
                snapshot['operational_credit_snapshot'] = credit_snapshot
            context = self.binding_context(source)
            if specialist is self.scientific_process_binding:
                from .scientific_process.completion_snapshot import completion_snapshot as _scientific_completion_snapshot
                _scientific_completion_snapshot(self, source, context, snapshot, facts)
            facts.update(specialist.facts(context, snapshot))
        received_facts = self.episode_bindings.received_report_facts(self.binding_context(source), completion_snapshot=snapshot)
        if set(received_facts).intersection(facts):
            raise ValueError('received_report_fact_conflict')
        facts.update(received_facts)
        return facts

def _bind_original_runtime(namespace):
    definitions = {name: globals()[name] for name in ['facts']}
    globals().update(_bind_functions(namespace, definitions, runtime_module='gene_annotation_episode.episodic_workflow.root.a104.runtime', qualified_names={'facts': 'facts'}))

from .. import runtime as _original_namespace
_bind_original_runtime(vars(_original_namespace))
