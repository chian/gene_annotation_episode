"""Actual completed annotation arm and additional-credit continuation context."""

def annotation_axis_continuation(self, source, index, credit, value):
    value.update(self.episode_bindings.annotation_axis_yield_context(self.binding_context(source), credit))
    action = self.journal.row('runtime_actions', source.episode_id, index)
    selected = json.loads(action['action'])
    if selected.get('kind') == 'episode_child' and selected.get('role') == 'sequence_homology_evidence':
        assignment = selected['assignment']
        from .sequence_homology_evidence_records import selection_fields
        process = assignment['selection']
        axis = process[selection_fields(process)[0]]['option_id']
        ref = assignment.get('proposed_annotation_ref')
        arms = [arm for arm in credit['arms'] if arm['proposed_annotation_ref'] == ref and arm['axis'] == axis and (arm['scope'] == selected['scope'])]
        if len(arms) != 1:
            raise WorkflowError('completed_axis_requires_one_original_annotation_subject_scope')
        value['completed_annotation_axis'] = {name: arms[0][name] for name in ('proposed_annotation_ref', 'subject_ref', 'scope', 'axis')}
    return value

def _bind_original_runtime(namespace):
    from gene_annotation_episode.episodic_workflow.root.a101.library.live_runtime_functions import bind_functions
    selected = bind_functions(namespace, {name: globals()[name] for name in ('annotation_axis_continuation',)},
        runtime_module='gene_annotation_episode.episodic_workflow.root.a101.runtime', qualified_names={'annotation_axis_continuation': 'annotation_axis_continuation'},
        defining_module='gene_annotation_episode.episodic_workflow.root.a101.continuation')
    globals().update(selected)

from gene_annotation_episode.episodic_workflow.root.a101 import runtime as _original_runtime
_bind_original_runtime(vars(_original_runtime))
