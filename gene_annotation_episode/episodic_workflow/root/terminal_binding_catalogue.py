"""Literal parent-private terminal construction, saved families and credit routing.

New construction selects the six predefined children. Saved descriptors retain
their exact parent families; historical source identity remains literal.
"""
from copy import deepcopy
import json
from gene_annotation_episode.episodic_workflow.root.communication import plain
from .method_loop.durable import canonical
from .episode_application_services import EpisodeApplicationServices

OWNER = 'root.terminal_execution'
LEGACY_VERSION = 'terminal_execution_episodes_v1'
ENTRIES = (
    ('local', 'launch_local', 'local_job_execution', 'root_local_terminal_execution'),
    ('hpc', 'launch_hpc', 'hpc_job_execution', 'root_hpc_terminal_execution'),
)


PARENTS = ('annotation', 'legacy_annotation', 'scientific_process')
PARENT_ENTRIES = (
    ('annotation', 'local', 'launch_local', 'local_job_execution', 'root_local_terminal_execution'),
    ('annotation', 'hpc', 'launch_hpc', 'hpc_job_execution', 'root_hpc_terminal_execution'),
    ('legacy_annotation', 'local', 'launch_local', 'legacy_annotation/local_job_execution', 'root_legacy_annotation_local_terminal_execution'),
    ('legacy_annotation', 'hpc', 'launch_hpc', 'legacy_annotation/hpc_job_execution', 'root_legacy_annotation_hpc_terminal_execution'),
    ('scientific_process', 'local', 'launch_local', 'scientific_process/local_job_execution', 'root_scientific_process_local_terminal_execution'),
    ('scientific_process', 'hpc', 'launch_hpc', 'scientific_process/hpc_job_execution', 'root_scientific_process_hpc_terminal_execution'),
)


def selected_entries(configuration, parents):
    parents = tuple(parents)
    if (not parents or len(set(parents)) != len(parents)
            or parents != tuple(parent for parent in PARENTS if parent in parents)):
        raise ValueError('root_terminal_parent_selection_conflict')
    return tuple(entry for entry in PARENT_ENTRIES
                 if entry[0] in parents and entry[1] in configuration['resources'])


def binding_class(binding_path):
    """Select an existing, literal private class; never construct a role adapter."""
    if binding_path == 'local_job_execution':
        from .local_job_execution.episode import LocalEpisodeBinding
        return LocalEpisodeBinding
    elif binding_path == 'hpc_job_execution':
        from .hpc_job_execution.episode import HPCEpisodeBinding
        return HPCEpisodeBinding
    elif binding_path == 'legacy_annotation/local_job_execution':
        from .legacy_annotation.local_job_execution.episode import LocalEpisodeBinding
        return LocalEpisodeBinding
    elif binding_path == 'legacy_annotation/hpc_job_execution':
        from .legacy_annotation.hpc_job_execution.episode import HPCEpisodeBinding
        return HPCEpisodeBinding
    elif binding_path == 'scientific_process/local_job_execution':
        from .scientific_process.local_job_execution.episode import LocalEpisodeBinding
        return LocalEpisodeBinding
    elif binding_path == 'scientific_process/hpc_job_execution':
        from .scientific_process.hpc_job_execution.episode import HPCEpisodeBinding
        return HPCEpisodeBinding
    raise ValueError('root_terminal_binding_path_required')


def descriptor_parents(configuration, descriptors):
    """Retain the exact saved parent families, including annotation-only records."""
    configuration = original_configuration(configuration)
    descriptors = list(descriptors)
    identifiers = {row.get('binding_id') for row in descriptors if type(row) is dict}
    parents = tuple(parent for parent in PARENTS
                    if any(entry[0] == parent and entry[4] in identifiers for entry in PARENT_ENTRIES))
    if not parents or canonical(descriptors) != canonical(list(fixed_descriptors(configuration, parents=parents))):
        raise ValueError('root_terminal_fixed_group_conflict')
    return parents


def original_configuration(value):
    """Validate the original constructor's data contract, not machine capacity."""
    value = json.loads(canonical(plain(value)))
    if type(value) is not dict or set(value) != {'resources', 'initial_information'}:
        raise ValueError('root_terminal_configuration_required')
    resources, information = value['resources'], value['initial_information']
    if not resources or not set(resources) <= {'local', 'hpc'}:
        raise ValueError('explicit_execution_resources_required')
    if not set(information) <= set(resources):
        raise ValueError('initial_inventory_resource_not_bound')
    return value


def legacy_descriptor(configuration):
    return {'binding_id': 'terminal_execution', 'version': LEGACY_VERSION,
            'configuration': original_configuration(configuration)}


def fixed_descriptors(configuration, *, parents=PARENTS):
    configuration = original_configuration(configuration)
    return tuple({'binding_id': identifier, 'version': identifier + '_v1',
                  'configuration': deepcopy(configuration)}
                 for parent, kind, role, path, identifier in selected_entries(configuration, parents))


def construct_fixed_children(services, *, store, directory, configuration, parents=PARENTS):
    """Construct the caller's explicit predefined parent families."""
    configuration = original_configuration(configuration)
    bindings = tuple(binding_class(path)(services, store=store, directory=directory, **configuration)
                     for parent, kind, role, path, identifier in selected_entries(configuration, parents))
    validate_fixed_group(bindings, configuration)
    return bindings


def expand_original_descriptor(descriptor, services, *, store, directory):
    """Retain exact historical data separately from the current child records."""
    if (type(descriptor) is not dict or set(descriptor) != {'binding_id', 'version', 'configuration'}
            or descriptor['binding_id'] != 'terminal_execution' or descriptor['version'] != LEGACY_VERSION):
        raise ValueError('root_terminal_original_descriptor_required')
    configuration = original_configuration(descriptor['configuration'])
    if canonical(descriptor) != canonical(legacy_descriptor(configuration)):
        raise ValueError('root_terminal_original_descriptor_conflict')
    bindings = construct_fixed_children(services, store=store, directory=directory, configuration=configuration)
    return bindings, {'original_descriptor': deepcopy(descriptor),
                      'current_descriptors': [b.as_record() for b in bindings],
                      'owner': OWNER, 'binding_paths': [b.binding_path for b in bindings]}


def _project(bindings):
    from .predefined_parent_routes import binding_for_context
    def project(context, receiver_selection):
        binding = binding_for_context(bindings, context)
        if binding is None:
            raise LookupError('root_terminal_context_not_bound')
        return binding.state(context).credit_view()
    return project


def application_from_original_factory(factory, *, directory, descriptors=None):
    """Select actual private parents; saved families are never silently expanded."""
    from gene_annotation_episode.practical_service_setup import PracticalServiceFactory
    if type(factory) is not PracticalServiceFactory:
        raise TypeError('canonical_practical_service_factory_required')
    record = factory.as_record()
    if set(record) != {'version', 'resources', 'initial_information'} or record['version'] != 'practical_service_factory_v1':
        raise ValueError('original_practical_factory_definition_required')
    configuration = original_configuration({k: record[k] for k in ('resources', 'initial_information')})
    parents = PARENTS if descriptors is None else descriptor_parents(configuration, descriptors)
    bindings = construct_fixed_children(None, store=None, directory=directory,
                                       configuration=configuration, parents=parents)
    project = _project(bindings)
    credits = {role: {'definition': {'version': 'practical_required_facts_credit_v1',
        'units': 'original_assignment_progress_requirement_credits',
        'baseline': 'original_initial_validations', 'repeated_fact_gain': 0},
        'project': project} for kind, role, path, identifier in ENTRIES
        if kind in configuration['resources']}
    return EpisodeApplicationServices([b.as_record() for b in bindings], credits)


def authenticated_initial_information(bindings, configuration, context):
    """One original inventory field after every actual saved family agrees."""
    bindings = tuple(bindings)
    configuration = validate_fixed_group(bindings, configuration)
    expected_information = {'execution_resource_information': deepcopy(configuration['initial_information'])}
    for binding in bindings:
        if canonical(binding.initial_decision_context(context)) != canonical(expected_information):
            raise ValueError('root_terminal_initial_group_information_conflict')
    return expected_information


# This is new root composition metadata, not an alias for the old aggregate.
CATALOGUE_VERSION = 'root_saved_terminal_binding_catalogue_v1'
FACTORY = 'gene_annotation_episode.practical_service_setup.PracticalServiceFactory'


def owner_records(configuration, *, parents=PARENTS):
    from .private_episode_selection import SELECTION_VERSION
    configuration = original_configuration(configuration)
    descriptors = fixed_descriptors(configuration, parents=parents)
    paths = [entry[3] for entry in selected_entries(configuration, parents)]
    return [{'version': SELECTION_VERSION, 'owner': OWNER, 'binding_path': path,
             'descriptor': descriptor} for path, descriptor in zip(paths, descriptors)]


def construct_fixed_binding(descriptor, services, *, store, directory, configuration):
    """Authenticate one actual descriptor and invoke its literal private class."""
    configuration = original_configuration(configuration)
    matches = [entry for entry in selected_entries(configuration, PARENTS)
               if entry[4] == descriptor.get('binding_id')]
    if len(matches) != 1 or descriptor not in fixed_descriptors(configuration):
        raise ValueError('root_terminal_fixed_descriptor_conflict')
    binding = binding_class(matches[0][3])(services, store=store, directory=directory, **configuration)
    if canonical(binding.as_record()) != canonical(descriptor):
        raise ValueError('root_terminal_constructor_descriptor_conflict')
    return binding


def validate_fixed_group(bindings, configuration):
    """Actual private classes and exact recorded parent families, never duck types."""
    configuration = original_configuration(configuration)
    bindings = tuple(bindings)
    parents = descriptor_parents(configuration, [binding.as_record() for binding in bindings])
    expected = owner_records(configuration, parents=parents)
    for binding, row in zip(bindings, expected):
        cls = binding_class(row['binding_path'])
        if (type(binding) is not cls or binding.binding_path != row['binding_path']
                or canonical(binding.as_record()) != canonical(row['descriptor'])):
            raise ValueError('root_terminal_fixed_group_conflict')
    return configuration


def factory_configuration(factory, recorded):
    """Check actual caller type and its original saved data definition."""
    from gene_annotation_episode.practical_service_setup import PracticalServiceFactory
    from .episode_application_services import service_binding
    if type(factory) is not PracticalServiceFactory:
        raise TypeError('canonical_practical_service_factory_required')
    actual = factory.as_record()
    if canonical(service_binding(factory, actual)) != canonical(recorded):
        raise ValueError('root_terminal_actual_factory_definition_conflict')
    return original_configuration({key: actual[key] for key in ('resources', 'initial_information')})


def source_record():
    """Real broad package stream including tests; not executed-closure proof."""
    import hashlib
    from pathlib import Path
    root = Path(__file__).resolve().parents[3]
    application = root / 'gene_annotation_episode'
    files = sorted(path for package in ('gene_annotation_episode', 'method_loop')
                   for path in (root / package).rglob('*.py'))
    owner = application / 'episodic_workflow/root'
    required = {Path(__file__).resolve(), owner / 'method_loop/__init__.py',
        owner / 'root_operational_selection.py', owner / 'root_binding_selection.py',
        owner / 'workflow_setup.py', owner / 'episode_bindings.py',
        owner / 'episode_composition.py', owner / 'run_execution.py',
        owner / 'saved_private_binding_catalogue.py', owner / 'saved_binding_reconstruction.py',
        owner / 'commissioned_reopening.py', application / 'practical_service_setup.py'}
    for home in (entry[3] for entry in PARENT_ENTRIES):
        required.update(owner / home / (name + '.py') for name in (
            'credit', 'decision_guidance', 'episode', 'execution_persistence', 'execution_state', 'from_parent', 'goal', 'instructions', 'internal_summary', 'operations', 'report_fields', 'report_references', 'task', 'task_action_outcomes', 'task_decision', 'task_instructions', 'task_protocol', 'task_state', 'to_parent', 'waiting', 'yield'))
    required.add(owner / 'library/terminal_command_contract.py')
    required.add(owner / 'predefined_parent_routes.py')
    if not application.is_dir() or not files or not required.issubset(set(files)):
        raise ValueError('root_terminal_catalogue_source_required')
    sources, stream = {}, hashlib.sha256()
    for path in files:
        relative = str(path.relative_to(root))
        digest = hashlib.sha256(path.read_bytes()).digest()
        sources[relative] = digest.hex()
        stream.update(relative.encode('utf-8') + b'\0')
        stream.update(digest)
    return {'version': CATALOGUE_VERSION, 'owner': OWNER,
        'constructors': [
            'gene_annotation_episode.episodic_workflow.root.local_job_execution.episode.LocalEpisodeBinding',
            'gene_annotation_episode.episodic_workflow.root.hpc_job_execution.episode.HPCEpisodeBinding',
            'gene_annotation_episode.episodic_workflow.root.legacy_annotation.local_job_execution.episode.LocalEpisodeBinding',
            'gene_annotation_episode.episodic_workflow.root.legacy_annotation.hpc_job_execution.episode.HPCEpisodeBinding',
            'gene_annotation_episode.episodic_workflow.root.scientific_process.local_job_execution.episode.LocalEpisodeBinding',
            'gene_annotation_episode.episodic_workflow.root.scientific_process.hpc_job_execution.episode.HPCEpisodeBinding'],
        'source_identity_kind': 'original_package_python_source_stream_including_tests',
        'sources': sources, 'implementation_sha256': stream.hexdigest()}


def catalogue_for_fixed_registry(registry):
    if registry.private_owners != (OWNER,):
        raise ValueError('root_terminal_declared_owner_required')
    descriptors = registry.as_record()
    if not descriptors:
        raise ValueError('root_terminal_fixed_group_required')
    configuration = original_configuration(descriptors[0]['configuration'])
    parents = descriptor_parents(configuration, descriptors)
    expected = owner_records(configuration, parents=parents)
    bindings = tuple(registry.for_binding_path(row['binding_path'], owner=OWNER) for row in expected)
    validate_fixed_group(bindings, configuration)
    if canonical(registry.owner_records()) != canonical(expected):
        raise ValueError('root_terminal_saved_catalogue_conflict')
    return {'source': source_record(), 'assets': {}}


def is_fixed_saved_catalogue(settings):
    catalogue = settings.get('episode_binding_catalogue')
    return (type(catalogue) is dict and type(catalogue.get('source')) is dict
            and catalogue['source'].get('version') == CATALOGUE_VERSION)


def validate_saved_fixed_catalogue(settings):
    """Authenticate new saved records; never upgrade an old aggregate record."""
    service = settings.get('episode_application_services')
    if (type(service) is not dict or set(service) != {'version', 'factory', 'definition'}
            or service['version'] != 'episode_application_services_v1'
            or service['factory'] != FACTORY):
        raise ValueError('root_terminal_recorded_factory_required')
    definition = service['definition']
    if (type(definition) is not dict or set(definition) != {'version', 'resources', 'initial_information'}
            or definition['version'] != 'practical_service_factory_v1'):
        raise ValueError('root_terminal_recorded_factory_definition_required')
    configuration = original_configuration({key: definition[key] for key in ('resources', 'initial_information')})
    parents = descriptor_parents(configuration, settings.get('episode_bindings', []))
    descriptors = list(fixed_descriptors(configuration, parents=parents))
    records = owner_records(configuration, parents=parents)
    if (canonical(settings.get('episode_bindings')) != canonical(descriptors)
            or canonical(settings.get('episode_binding_owners')) != canonical(records)
            or canonical(settings.get('episode_binding_catalogue')) != canonical(
                {'source': source_record(), 'assets': {}})):
        raise ValueError('root_terminal_saved_catalogue_conflict')
    return descriptors, records, {}
