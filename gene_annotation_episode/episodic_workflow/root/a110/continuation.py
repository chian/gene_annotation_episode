"""Private A110 annotation continuation responsibility."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110 import runtime as _original_runtime

def controller_value(workflow, source, index, credit):
    value = {'credit': credit, 'estimation_action_index': index}
    if isinstance(credit, _original_runtime.Mapping) and credit.get('mode') == 'annotation_axis_credit':
        value.update(workflow.episode_bindings.annotation_axis_yield_context(workflow.binding_context(source), credit))
        action = workflow.journal.row('runtime_actions', source.episode_id, index)
        selected = _original_runtime.json.loads(action['action'])
        if selected.get('kind') == 'episode_child' and selected.get('role') == 'biochemical_feasibility_evidence':
            assignment = selected['assignment']
            from .biochemical_feasibility_evidence_records import selection_fields
            process = assignment['selection']
            axis = process[selection_fields(process)[0]]['option_id']
            ref = assignment.get('proposed_annotation_ref')
            arms = [arm for arm in credit['arms'] if arm['proposed_annotation_ref'] == ref and arm['axis'] == axis and (arm['scope'] == selected['scope'])]
            if len(arms) != 1:
                raise _original_runtime.WorkflowError('completed_axis_requires_one_original_annotation_subject_scope')
            value['completed_annotation_axis'] = {name: arms[0][name] for name in ('proposed_annotation_ref', 'subject_ref', 'scope', 'axis')}
    binding = workflow.specialist(source)
    continuation = getattr(binding, 'continuation_for_action', None)
    if continuation is not None:
        pending_value = continuation(workflow.binding_context(source), f'{workflow.run_id}:{source.episode_id}:{index}')
        if pending_value is not None:
            value['hpc_continuation'] = pending_value
            value['estimation_action_index'] = index
    completion = getattr(binding, 'completion_for_action', None)
    if completion is not None:
        proof = completion(workflow.binding_context(source), f'{workflow.run_id}:{source.episode_id}:{index}')
        if proof is not None:
            value['practical_completion'] = proof
            value['estimation_action_index'] = index
    return _original_runtime.Record(value)
