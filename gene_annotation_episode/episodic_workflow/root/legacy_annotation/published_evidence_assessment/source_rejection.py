"""Source-access rejection metadata owned by the original Root literature family."""
from gene_annotation_episode.episodic_workflow.root.component_source_access import (
    VERSION, AXES, RECOVERY, _rows, _axes, _axis)


def rejection_detail(workflow, context, root, blocked):
    if workflow is None or not hasattr(getattr(workflow, 'store', None), 'db'):
        return None
    if _axis(_axes(_rows(workflow)), context.path) not in AXES:
        return None
    return {'version': VERSION, 'assigned_source_ref': root,
        'blocked_source_refs': sorted(set(blocked)),
        'scientific_inference_authorized': False, 'recovery': RECOVERY}

