"""Authenticate actual Terminal parent/child identity against saved private owners.

The caller authenticates the parent and the original selection/action/scope.
Fresh and replay paths supply their actual child identity; this selector does
not fabricate an invocation or replace the ordinary child admission checks.
"""
import json
from .method_loop.durable import canonical
from .method_loop.identities import normalize_structural_path
from .terminal_binding_catalogue import (
    OWNER, ENTRIES, PARENT_ENTRIES, original_configuration, descriptor_parents,
    owner_records, validate_fixed_group)
from .predefined_parent_routes import binding_for_path

FACTORY = 'gene_annotation_episode.practical_service_setup.PracticalServiceFactory'


def original_operational_owner(workflow, selection, *, parent_path, child_path):
    role = selection.get('role') if type(selection) is dict else None
    entries = [entry for entry in ENTRIES if entry[1] == role]
    if not entries:
        return None
    if selection.get('kind') != 'episode_child':
        raise ValueError('root_terminal_original_child_selection_required')
    parent_path = normalize_structural_path(parent_path)
    child_path = normalize_structural_path(child_path)
    if child_path[:-1] != parent_path or child_path[-1][0] != role:
        raise ValueError('root_terminal_original_child_path_conflict')
    row = workflow.journal.row('runtime_runs')
    if row is None:
        raise ValueError('root_terminal_original_run_settings_required')
    settings = json.loads(row['settings'])
    service = settings.get('episode_application_services')
    if (type(service) is not dict or set(service) != {'version', 'factory', 'definition'}
            or service['version'] != 'episode_application_services_v1' or service['factory'] != FACTORY):
        raise ValueError('root_terminal_recorded_factory_required')
    definition = service['definition']
    if (type(definition) is not dict or set(definition) != {'version', 'resources', 'initial_information'}
            or definition['version'] != 'practical_service_factory_v1'):
        raise ValueError('root_terminal_recorded_factory_definition_required')
    configuration = original_configuration({k: definition[k] for k in ('resources', 'initial_information')})
    kind = entries[0][0]
    if kind not in configuration['resources']:
        raise ValueError('root_terminal_selected_resource_not_declared')
    assignment = selection.get('assignment')
    if type(assignment) is not dict or assignment.get('resource_kind') != kind:
        raise ValueError('execution_resource_assignment_mismatch')
    recorded = settings.get('episode_binding_owners')
    descriptors = settings.get('episode_bindings')
    if type(recorded) is not list or type(descriptors) is not list:
        raise ValueError('root_terminal_saved_catalogue_conflict')
    records = [record for record in recorded if type(record) is dict and record.get('owner') == OWNER]
    parents = descriptor_parents(configuration, [record.get('descriptor') for record in records])
    expected = owner_records(configuration, parents=parents)
    identifiers = {entry[4] for entry in PARENT_ENTRIES}
    actual_descriptors = [descriptor for descriptor in descriptors
                          if type(descriptor) is dict and descriptor.get('binding_id') in identifiers]
    if (canonical(records) != canonical(expected)
            or canonical(actual_descriptors) != canonical([record['descriptor'] for record in expected])):
        raise ValueError('root_terminal_saved_catalogue_conflict')
    registry = workflow.episode_bindings
    actual_records = [record for record in registry.owner_records() if record['owner'] == OWNER]
    if OWNER not in registry.private_owners or canonical(actual_records) != canonical(expected):
        raise ValueError('root_terminal_actual_catalogue_conflict')
    bindings = tuple(registry.for_binding_path(record['binding_path'], owner=OWNER) for record in expected)
    validate_fixed_group(bindings, configuration)
    selected = binding_for_path(bindings, child_path)
    if selected is None or selected.resource_kind != kind:
        raise ValueError('root_terminal_actual_parent_child_not_bound')
    return OWNER
