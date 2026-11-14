"""A104 original continuation defining responsibilities."""
from __future__ import annotations
from .library.live_runtime_functions import bind_functions as _bind_functions

def controller_value(self, source, index, credit):
    value = {'credit': credit, 'estimation_action_index': index}
    if isinstance(credit, Mapping) and credit.get('mode') == 'annotation_axis_credit':
        value.update(self.episode_bindings.annotation_axis_yield_context(self.binding_context(source), credit))
        action = self.journal.row('runtime_actions', source.episode_id, index)
        selected = json.loads(action['action'])
        if selected.get('kind') == 'episode_child' and selected.get('role') == 'scientific_process':
            assignment = selected['assignment']
            from .scientific_process_records import selection_fields
            process = assignment['selection']
            axis = process[selection_fields(process)[0]]['option_id']
            ref = assignment.get('proposed_annotation_ref')
            arms = [arm for arm in credit['arms'] if arm['proposed_annotation_ref'] == ref and arm['axis'] == axis and (arm['scope'] == selected['scope'])]
            if len(arms) != 1:
                raise WorkflowError('completed_axis_requires_one_original_annotation_subject_scope')
            value['completed_annotation_axis'] = {name: arms[0][name] for name in ('proposed_annotation_ref', 'subject_ref', 'scope', 'axis')}
    binding = self.specialist(source)
    continuation = getattr(binding, 'continuation_for_action', None)
    if continuation is not None:
        pending_value = continuation(self.binding_context(source), f'{self.run_id}:{source.episode_id}:{index}')
        if pending_value is not None:
            value['hpc_continuation'] = pending_value
            value['estimation_action_index'] = index
    completion = getattr(binding, 'completion_for_action', None)
    if completion is not None:
        proof = completion(self.binding_context(source), f'{self.run_id}:{source.episode_id}:{index}')
        if proof is not None:
            value['practical_completion'] = proof
            value['estimation_action_index'] = index
    return Record(value)


def _bind_original_runtime(namespace):
    definitions = {name: globals()[name] for name in ['controller_value']}
    globals().update(_bind_functions(namespace, definitions, runtime_module='gene_annotation_episode.episodic_workflow.root.a104.runtime', qualified_names={'controller_value': 'controller_value'}))

from . import runtime as _original_namespace
_bind_original_runtime(vars(_original_namespace))
