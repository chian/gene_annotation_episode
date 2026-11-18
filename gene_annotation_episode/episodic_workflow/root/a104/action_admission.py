'A104 original parent action-admission policy: literature-only root waiting, restricted-root tool receipt/replay gates, configured top-level task-credit role filter and received annotation-axis assignment validation. Generic/private binding dispatch remains in Workflow at its original positions.'
from __future__ import annotations
from .library.live_runtime_functions import bind_functions as _bind_functions

def parent_common_action_permission(self, source, action):
    if action == 'wait' and len(source.path) == 1 and (source.path[0][0] == 'annotation') and (self.annotation_child_roles == ('literature',)) and ('literature' in self.episode_bindings.roles) and (not getattr(self.episode_bindings.for_child(source.path, 'literature'), 'supports_wait', True)):
        return False
    if restricted_root(self, source) and action == 'tool':
        return self.receipts is not None
    return None

def filter_parent_task_credit_roles(self, source, roles):
    if len(source.path) == 1 and getattr(self.project_credit, 'task_credit', False):
        roles = tuple((role for role in roles if role == 'evolutionary_history_evidence'))
    return roles

def filter_parent_common_actions(self, source, common_actions):
    if restricted_root(self, source):
        if self.receipts is None:
            common_actions = tuple((action for action in common_actions if action != 'tool'))
    return common_actions

def validate_parent_axis_choice(self, source, role, *, selection=None, original=False):
    annotation_axes = len(source.path) == 1 and getattr(self.project_credit, 'task_credit', False)
    if annotation_axes and role != 'evolutionary_history_evidence':
        raise ValueError('annotation_root_commissions_evidence_axes')
    if annotation_axes and selection is not None and (not original):
        from .evolutionary_history_evidence_records import selection_fields
        assignment = selection.get('assignment', {})
        process = assignment.get('selection', {})
        axis = process[selection_fields(process)[0]]['option_id']
        ref = assignment.get('proposed_annotation_ref')
        scope = self.store.validate_scope(selection['scope'], source.scope)
        arms = self.source_credit_view(source)['credit']['arms']
        if sum((arm['proposed_annotation_ref'] == ref and arm['axis'] == axis and (arm['scope'] == scope) for arm in arms)) != 1:
            raise ValueError('axis_assignment_requires_one_received_annotation_subject_scope')

def validate_parent_tool_selection(self, source, selection, index):
    if restricted_root(self, source) and selection['kind'] == 'tool':
        recorded = self.journal.row('runtime_actions', source.episode_id, index)
        replay = recorded is not None and recorded['result'] is not None and (json.loads(recorded['action']) == selection)
        if not replay and selection.get('tool') not in {item['name'] for item in self.catalog(source.scope, source=source)}:
            raise ValueError('action_not_available_to_episode')

def parent_catalog(self, scope, source=None):
    if restricted_root(self, source):
        entries = self.shared_information_catalog(source)
        if self.receipts is not None and source is not None and self.permits_common_action(source, 'wait'):
            entries.append(_wait_estimate_operation())
        return (True, entries)
    return (False, None)

def parent_tool_admission(self, source, name, _composition_lookup):
    if restricted_root(self, source) and (not _composition_lookup):
        from .shared_information import TOOLS as shared_tools
        waiting_operation = name == 'episode.estimate_wait' and self.permits_common_action(source, 'wait')
        if self.receipts is None or (name not in shared_tools and (not waiting_operation)):
            return (True, {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'code': 'root_tool_requires_shared_coordination_operation'}})
    return (False, None)

def _bind_original_runtime(namespace):
    names = {'parent_common_action_permission': 'parent_common_action_permission', 'filter_parent_task_credit_roles': 'filter_parent_task_credit_roles', 'filter_parent_common_actions': 'filter_parent_common_actions', 'validate_parent_axis_choice': 'validate_parent_axis_choice', 'validate_parent_tool_selection': 'validate_parent_tool_selection', 'parent_catalog': 'parent_catalog', 'parent_tool_admission': 'parent_tool_admission'}
    globals().update(_bind_functions(namespace, {name: globals()[name] for name in names},
        runtime_module='gene_annotation_episode.episodic_workflow.root.a104.runtime', qualified_names=names,
        defining_module='gene_annotation_episode.episodic_workflow.root.a104.action_admission'))

from . import runtime as _original_namespace
_bind_original_runtime(vars(_original_namespace))
