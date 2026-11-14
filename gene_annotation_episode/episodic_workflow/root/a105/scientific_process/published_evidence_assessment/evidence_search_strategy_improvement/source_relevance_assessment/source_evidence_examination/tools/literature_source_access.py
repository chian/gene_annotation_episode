"""Private A105 source-assignment rejection feedback."""
from __future__ import annotations
VERSION = 'component_axis_source_access_v1'
ERROR = 'literature_reading_outside_assigned_source'
RECOVERY = 'This reader can use its assigned source and derived sources. A received sibling dataset needs an assignment that includes it. Report the missing source access to the parent; a rejected read does not establish scientific absence or opposition.'

def rejection_detail(workflow, context, root, blocked):
    if workflow is None or not hasattr(getattr(workflow, 'store', None), 'db'):
        return None
    return {'version': VERSION, 'assigned_source_ref': root, 'blocked_source_refs': sorted(set(blocked)), 'scientific_inference_authorized': False, 'recovery': RECOVERY}
