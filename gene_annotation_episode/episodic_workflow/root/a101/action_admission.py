"""Substantive A101 policy definitions; original live runtime globals retained."""

def restricted_common_action(self, source, action):
    if action == 'wait' and len(source.path) == 1 and (source.path[0][0] == 'annotation') and (self.annotation_child_roles == ('literature',)) and ('literature' in self.episode_bindings.roles) and (not getattr(self.episode_bindings.for_child(source.path, 'literature'), 'supports_wait', True)):
        return False
    if restricted_root(self, source) and action == 'tool':
        return self.receipts is not None
    return None

def restrict_credit_child_roles(self, source, roles):
    if len(source.path) == 1 and getattr(self.project_credit, 'task_credit', False):
        roles = tuple((role for role in roles if role == 'sequence_homology_evidence'))
    return roles

def restrict_root_tool_actions(self, source, common_actions):
    if restricted_root(self, source):
        if self.receipts is None:
            common_actions = tuple((action for action in common_actions if action != 'tool'))
    return common_actions

def validate_annotation_child_choice(self, source, role, selection, original):
    annotation_axes = len(source.path) == 1 and getattr(self.project_credit, 'task_credit', False)
    if annotation_axes and role != 'sequence_homology_evidence':
        raise ValueError('annotation_root_commissions_evidence_axes')
    if annotation_axes and selection is not None and (not original):
        from .sequence_homology_evidence_records import selection_fields
        assignment = selection.get('assignment', {})
        process = assignment.get('selection', {})
        axis = process[selection_fields(process)[0]]['option_id']
        ref = assignment.get('proposed_annotation_ref')
        scope = self.store.validate_scope(selection['scope'], source.scope)
        arms = self.source_credit_view(source)['credit']['arms']
        if sum((arm['proposed_annotation_ref'] == ref and arm['axis'] == axis and (arm['scope'] == scope) for arm in arms)) != 1:
            raise ValueError('axis_assignment_requires_one_received_annotation_subject_scope')

def validate_root_tool_selection(self, source, selection, index):
    if restricted_root(self, source) and selection['kind'] == 'tool':
        recorded = self.journal.row('runtime_actions', source.episode_id, index)
        replay = recorded is not None and recorded['result'] is not None and (json.loads(recorded['action']) == selection)
        if not replay and selection.get('tool') not in {item['name'] for item in self.catalog(source.scope, source=source)}:
            raise ValueError('action_not_available_to_episode')

def root_tool_catalog(self, source):
    entries = self.shared_information_catalog(source)
    if self.receipts is not None and source is not None and self.permits_common_action(source, 'wait'):
        entries.append(_wait_estimate_operation())
    return entries

def root_tool_rejection(self, source, name):
    from .shared_information import TOOLS as shared_tools
    waiting_operation = name == 'episode.estimate_wait' and self.permits_common_action(source, 'wait')
    if self.receipts is None or (name not in shared_tools and (not waiting_operation)):
        return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'code': 'root_tool_requires_shared_coordination_operation'}}
    return None

def root_child_return_sources(self, source, role):
    """Ask this root's own binding what it needs from its child."""
    if not restricted_root(self, source):
        return ()
    bound = getattr(self.project_credit, 'child_return_sources', None)
    return tuple(bound(self.binding_context(source), role)) if bound is not None else ()

def _bind_original_runtime(namespace):
    from gene_annotation_episode.episodic_workflow.root.a101.library.live_runtime_functions import bind_functions
    selected = bind_functions(namespace, {name: globals()[name] for name in ('restricted_common_action', 'restrict_credit_child_roles', 'restrict_root_tool_actions', 'validate_annotation_child_choice', 'validate_root_tool_selection', 'root_tool_catalog', 'root_tool_rejection')}, runtime_module='gene_annotation_episode.episodic_workflow.root.a101.runtime', qualified_names={'restricted_common_action': 'restricted_common_action', 'restrict_credit_child_roles': 'restrict_credit_child_roles', 'restrict_root_tool_actions': 'restrict_root_tool_actions', 'validate_annotation_child_choice': 'validate_annotation_child_choice', 'validate_root_tool_selection': 'validate_root_tool_selection', 'root_tool_catalog': 'root_tool_catalog', 'root_tool_rejection': 'root_tool_rejection'}, defining_module='gene_annotation_episode.episodic_workflow.root.a101.action_admission')
    selected.update(bind_functions(namespace, {'root_child_return_sources': globals()['root_child_return_sources']}, runtime_module='gene_annotation_episode.episodic_workflow.root.a101.runtime', qualified_names={'root_child_return_sources': 'Workflow.root_child_return_sources'}, defining_module=None))
    globals().update(selected)

from gene_annotation_episode.episodic_workflow.root.a101 import runtime as _original_runtime
_bind_original_runtime(vars(_original_runtime))
