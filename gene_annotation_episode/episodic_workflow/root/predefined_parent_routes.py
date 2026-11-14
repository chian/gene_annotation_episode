"""Select supplied private implementations through original Root parent paths.

This is a source-identity lookup for already authenticated contexts, not child
admission or configuration. It neither constructs an episode nor changes a
binding's role/path. Callers authenticate their finite concrete binding families.
"""
from .method_loop.identities import normalize_structural_path


HOST_PARENTS = ('annotation', 'legacy_annotation', 'scientific_process')
LITERATURE_HEAD = {
    'annotation': 'published_evidence_assessment',
    'legacy_annotation': 'legacy_annotation/published_evidence_assessment',
    'scientific_process': 'scientific_process/published_evidence_assessment',
}
HPC_COORDINATION = {
    'annotation': 'hpc_coordination',
    'legacy_annotation': 'legacy_annotation/hpc_coordination',
    'scientific_process': 'scientific_process/hpc_coordination',
}
HPC_ALLOCATION = {
    home: home + '/hpc_allocation_execution'
    for home in HPC_COORDINATION.values()
}
HPC_PREDICTION = {
    home: home + '/hpc_resource_prediction'
    for home in HPC_COORDINATION.values()
}


def _resolved_parent_path(bindings, path):
    """Return the actual supplied member and its resolved parent-source identity.

    Annotation is the original implicit first host. Unregistered improvement
    uses its actual legacy_annotation source identity; recursive scientific
    invocations reuse scientific_process. The three original Literature heads
    retain their authentic source identity for configured analysis children.
    HPC source identities follow their
    own original coordination/allocation/prediction edges. A known host marker
    alone never supplies a missing final episode binding.
    """
    bindings = tuple(bindings)
    path = normalize_structural_path(path)
    parent = 'annotation'
    selected = None
    for index, (role, _) in enumerate(path):
        if index == 0 and role == 'annotation':
            parent, selected = 'annotation', None
            continue
        matches = [binding for binding in bindings
                   if role in binding.roles
                   and getattr(binding, 'commissioning_parent', None) == parent
                   and (index != 0 or role in binding.entry_roles)]
        if len(matches) > 1:
            raise LookupError('episode_child_not_bound:' + str(parent) + ':' + str(role))
        if matches:
            selected = matches[0]
            parent = selected.binding_path
            continue
        selected = None
        if role == 'improvement':
            parent = 'legacy_annotation'
        elif role == 'scientific_process':
            parent = 'scientific_process'
        elif role == 'literature' and parent in LITERATURE_HEAD:
            parent = LITERATURE_HEAD[parent]
        elif role == 'hpc' and parent in HPC_COORDINATION:
            parent = HPC_COORDINATION[parent]
        elif role == 'hpc_execution' and parent in HPC_ALLOCATION:
            parent = HPC_ALLOCATION[parent]
        elif role == 'hpc_prediction' and parent in HPC_PREDICTION:
            parent = HPC_PREDICTION[parent]
        else:
            return None, None
    return selected, parent


def binding_for_path(bindings, path):
    """Return the actual supplied member; host-only paths remain unselected."""
    return _resolved_parent_path(bindings, path)[0]


def binding_for_child(bindings, parent_path, role):
    """Select an actual declared child beneath the authentic parent path.

    Implicit host ancestry can be resolved without inventing an EpisodeBinding
    for that host. The child itself must be one of the actual supplied objects;
    configured availability and assignment admission remain with the caller.
    """
    bindings = tuple(bindings)
    _, parent = _resolved_parent_path(bindings, parent_path)
    if parent is None:
        return None
    matches = [binding for binding in bindings if role in binding.roles
               and getattr(binding, 'commissioning_parent', None) == parent
               and (parent != 'annotation' or role in binding.entry_roles)]
    if len(matches) > 1:
        raise LookupError('episode_child_not_bound:' + str(parent) + ':' + str(role))
    return matches[0] if matches else None


def binding_for_context(bindings, context):
    """Use the immutable actual path; keep unrelated contexts unselected."""
    path = normalize_structural_path(context.path)
    if path[-1][0] != context.role:
        raise ValueError('binding_context_path_must_match_role')
    return binding_for_path(bindings, path)
