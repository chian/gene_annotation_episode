"""Private monitor assignment and report contracts."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.domain import REF, RECORD_SCHEMAS, obj
VERSION = 'monitor_episode_binding_v1'
FIELDS = ('execution_status', 'measurements', 'log_windows', 'committed_record_refs', 'dependencies', 'result_available')
_STATES = ('pending', 'executing', 'returned', 'admitted')
_REFS = {'type': 'array', 'items': REF, 'uniqueItems': True}
_FIELDS = {'type': 'array', 'items': {'enum': list(FIELDS)}, 'uniqueItems': True}
_TEXT = {'type': 'string', 'minLength': 1}
_ASSIGNMENT = obj({'version': {'const': 'monitor_assignment_v1'}, 'target_handle': _TEXT, 'requested_fields': _FIELDS, 'known_progress_refs': _REFS, 'permitted_committed_record_types': {'type': 'array', 'uniqueItems': True, 'items': {'enum': sorted(RECORD_SCHEMAS)}}})
