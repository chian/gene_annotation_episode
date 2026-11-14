"""Own annotation-root waiting, receipt availability, credit scope and configured child policies. Original late predicates remain."""

def root_common_action(self, source, action):
    if action == 'wait' and len(source.path) == 1 and (source.path[0][0] == 'annotation') and (self.annotation_child_roles == ('literature',)) and ('literature' in self.episode_bindings.roles) and (not getattr(self.episode_bindings.for_child(source.path, 'literature'), 'supports_wait', True)):
        return False
    if _original_runtime.restricted_root(self, source) and action == 'tool':
        return self.receipts is not None
    return None

def filter_root_child_roles(self, source, roles):
    if len(source.path) == 1 and getattr(self.project_credit, 'task_credit', False):
        roles = tuple((role for role in roles if role == 'scientific_process'))
    return roles

def validate_root_child_choice(self, source, role, *, selection=None, original=False):
    """Enforce an explicit caller graph before commissioning side effects.

        Absent-marker runs retain their original selection/recovery semantics.
        These are role and receipt checks, not scientific suitability checks.
        """
    annotation_axes = len(source.path) == 1 and getattr(self.project_credit, 'task_credit', False)
    if annotation_axes and role != 'scientific_process':
        raise ValueError('annotation_root_commissions_evidence_axes')
    if annotation_axes and selection is not None and (not original):
        from .scientific_process_records import selection_fields
        assignment = selection.get('assignment', {})
        process = assignment.get('selection', {})
        axis = process[selection_fields(process)[0]]['option_id']
        ref = assignment.get('proposed_annotation_ref')
        scope = self.store.validate_scope(selection['scope'], source.scope)
        arms = self.source_credit_view(source)['credit']['arms']
        if sum((arm['proposed_annotation_ref'] == ref and arm['axis'] == axis and (arm['scope'] == scope) for arm in arms)) != 1:
            raise ValueError('axis_assignment_requires_one_received_annotation_subject_scope')

def configured_annotation_roles(self, role):
    if role == 'annotation' and self.annotation_child_roles is not None:
        return (True, self.annotation_child_roles)
    return (False, None)

def root_child_return_sources(self, source, role):
    """Ask this root's own binding what it needs from its child."""
    if not _original_runtime.restricted_root(self, source):
        return ()
    bound = getattr(self.project_credit, 'child_return_sources', None)
    return tuple(bound(self.binding_context(source), role)) if bound is not None else ()

def root_catalog(self, scope, source=None):
    if _original_runtime.restricted_root(self, source):
        entries = self.shared_information_catalog(source)
        if self.receipts is not None and source is not None and self.permits_common_action(source, 'wait'):
            entries.append(_original_runtime._wait_estimate_operation())
        return (True, entries)
    return (False, None)

def root_execute_gate(self, source, name, *, _composition_lookup=False):
    if _original_runtime.restricted_root(self, source) and (not _composition_lookup):
        from .shared_information import TOOLS as shared_tools
        waiting_operation = name == 'episode.estimate_wait' and self.permits_common_action(source, 'wait')
        if self.receipts is None or (name not in shared_tools and (not waiting_operation)):
            return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'code': 'root_tool_requires_shared_coordination_operation'}}
    return None

def validate_root_selected_tool(self, source, selection, index):
    if _original_runtime.restricted_root(self, source) and selection['kind'] == 'tool':
        recorded = self.journal.row('runtime_actions', source.episode_id, index)
        replay = recorded is not None and recorded['result'] is not None and (_original_runtime.json.loads(recorded['action']) == selection)
        if not replay and selection.get('tool') not in {item['name'] for item in self.catalog(source.scope, source=source)}:
            raise ValueError('action_not_available_to_episode')

def filter_root_common_actions(self, source, common_actions):
    if _original_runtime.restricted_root(self, source):
        if self.receipts is None:
            common_actions = tuple((action for action in common_actions if action != 'tool'))
    return common_actions
from . import runtime as _original_runtime
