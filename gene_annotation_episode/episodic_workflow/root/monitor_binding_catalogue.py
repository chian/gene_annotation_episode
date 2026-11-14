"""Literal current Monitor parent families and exact saved source identities."""
from gene_annotation_episode.execution_contracts import canonical

PARENTS = (
    'annotation',
    'legacy_annotation',
    'scientific_process',
    'hpc_coordination',
    'hpc_coordination/hpc_allocation_execution',
    'legacy_annotation/hpc_coordination',
    'legacy_annotation/hpc_coordination/hpc_allocation_execution',
    'scientific_process/hpc_coordination',
    'scientific_process/hpc_coordination/hpc_allocation_execution',
)
ENTRIES = (
    ('annotation', 'execution_monitoring'),
    ('legacy_annotation', 'legacy_annotation/execution_monitoring'),
    ('scientific_process', 'scientific_process/execution_monitoring'),
    ('hpc_coordination', 'hpc_coordination/execution_monitoring'),
    ('hpc_coordination/hpc_allocation_execution', 'hpc_coordination/hpc_allocation_execution/execution_monitoring'),
    ('legacy_annotation/hpc_coordination', 'legacy_annotation/hpc_coordination/execution_monitoring'),
    ('legacy_annotation/hpc_coordination/hpc_allocation_execution', 'legacy_annotation/hpc_coordination/hpc_allocation_execution/execution_monitoring'),
    ('scientific_process/hpc_coordination', 'scientific_process/hpc_coordination/execution_monitoring'),
    ('scientific_process/hpc_coordination/hpc_allocation_execution', 'scientific_process/hpc_coordination/hpc_allocation_execution/execution_monitoring'),
)


def binding_class(parent):
    if parent == 'annotation':
        from .execution_monitoring.episode import MonitorEpisodes
        return MonitorEpisodes
    if parent == 'legacy_annotation':
        from .legacy_annotation.execution_monitoring.episode import MonitorEpisodes
        return MonitorEpisodes
    if parent == 'scientific_process':
        from .scientific_process.execution_monitoring.episode import MonitorEpisodes
        return MonitorEpisodes
    if parent == 'hpc_coordination':
        from .hpc_coordination.execution_monitoring.episode import MonitorEpisodes
        return MonitorEpisodes
    if parent == 'hpc_coordination/hpc_allocation_execution':
        from .hpc_coordination.hpc_allocation_execution.execution_monitoring.episode import MonitorEpisodes
        return MonitorEpisodes
    if parent == 'legacy_annotation/hpc_coordination':
        from .legacy_annotation.hpc_coordination.execution_monitoring.episode import MonitorEpisodes
        return MonitorEpisodes
    if parent == 'legacy_annotation/hpc_coordination/hpc_allocation_execution':
        from .legacy_annotation.hpc_coordination.hpc_allocation_execution.execution_monitoring.episode import MonitorEpisodes
        return MonitorEpisodes
    if parent == 'scientific_process/hpc_coordination':
        from .scientific_process.hpc_coordination.execution_monitoring.episode import MonitorEpisodes
        return MonitorEpisodes
    if parent == 'scientific_process/hpc_coordination/hpc_allocation_execution':
        from .scientific_process.hpc_coordination.hpc_allocation_execution.execution_monitoring.episode import MonitorEpisodes
        return MonitorEpisodes
    raise ValueError('root_monitor_unknown_commissioning_parent')


class MonitorDescriptorMismatch(ValueError):
    def __init__(self, code, reference='monitor'):
        super().__init__(code)
        self.reference = reference


def _parents(parents):
    parents = tuple(parents)
    if not parents or parents != tuple(parent for parent in PARENTS if parent in parents):
        raise ValueError('root_monitor_parent_selection_conflict')
    return parents


def validate_family(bindings):
    bindings = tuple(bindings)
    declarations = {path: (parent, binding_class(parent)) for parent, path in ENTRIES}
    paths = tuple(getattr(binding, 'binding_path', None) for binding in bindings)
    if (not bindings or len(set(paths)) != len(paths)
            or any(path not in declarations for path in paths)
            or paths != tuple(path for parent, path in ENTRIES if path in paths)):
        raise ValueError('root_monitor_fixed_family_required')
    for binding, path in zip(bindings, paths):
        parent, cls = declarations[path]
        if (type(binding) is not cls or binding.roles != ('monitor',)
                or binding.entry_roles != (('monitor',) if parent == 'annotation' else ())
                or binding.commissioning_parent != parent):
            raise ValueError('root_monitor_fixed_family_conflict')
    return bindings


def _match_records(bindings, descriptors):
    """Match literal current source identities, never infer a parent from role."""
    bindings = validate_family(bindings)
    selected = tuple(value for value in descriptors if value.get('binding_id') == 'monitor')
    if not selected:
        raise MonitorDescriptorMismatch('root_monitor_saved_family_required')
    records = tuple(binding.as_record() for binding in bindings)
    indices = []
    for record in selected:
        matches = [index for index, actual in enumerate(records)
                   if canonical(actual) == canonical(record)]
        if len(matches) != 1:
            raise MonitorDescriptorMismatch('root_monitor_saved_definition_conflict')
        indices.append(matches[0])
    if indices != sorted(set(indices)):
        raise MonitorDescriptorMismatch('root_monitor_saved_parent_order_conflict')
    return tuple(bindings[index] for index in indices)


def monitor_bindings(services, *, outcome_page_size=32, information_unit=None,
                     yield_settings=None, parents=PARENTS, descriptors=None):
    """Build explicit fixed parents; saved selection requires exact own hashes.

    The original constructors validate configuration only. When authenticating
    saved records, all explicitly supplied parent candidates are constructed
    and their actual descriptor functions are read; only exact recorded
    objects are returned for registration. No state, provider or work is run.
    """
    bindings = tuple(binding_class(parent)(services, outcome_page_size=outcome_page_size,
        information_unit=information_unit, yield_settings=yield_settings)
        for parent in _parents(parents))
    validate_family(bindings)
    return bindings if descriptors is None else _match_records(bindings, descriptors)


def construct_family(descriptors, services):
    """Restore exact recorded monitor parents and each original configuration."""
    selected = tuple(value for value in descriptors if value.get('binding_id') == 'monitor')
    if not selected:
        return ()
    bindings = []
    for descriptor in selected:
        configuration = descriptor.get('configuration')
        if type(configuration) is not dict:
            raise ValueError('root_monitor_saved_configuration_required')
        candidates = monitor_bindings(services, **configuration)
        bindings.extend(_match_records(candidates, (descriptor,)))
    validate_family(bindings)
    if canonical([binding.as_record() for binding in bindings]) != canonical(list(selected)):
        raise MonitorDescriptorMismatch('root_monitor_reconstructed_descriptor_conflict')
    return tuple(bindings)


def binding_for_descriptor(bindings, descriptor):
    return _match_records(bindings, (descriptor,))[0]
