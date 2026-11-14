"""Reconstruct the original literal supported saved caller bindings."""
from __future__ import annotations
from functools import partial
from .saved_run_records import _failure, _read_json

def _saved_episode_factories(settings, directory=None):
    """Restore known data-backed bindings; never infer a custom factory."""
    from .saved_private_binding_catalogue import saved_private_factories
    owned = saved_private_factories(settings)
    if owned is not None:
        return owned[0]
    factories = []
    for descriptor in settings.get('episode_bindings', []):
        if descriptor.get('binding_id') == 'literature':
            from .literature_families import factories as literature_factories
            factories.extend(literature_factories(**descriptor['configuration']))
        elif descriptor.get('binding_id') == 'scientific_process':
            from .episode_composition import reopen_scientific_binding
            factories.append(partial(reopen_scientific_binding,
                descriptor=descriptor, directory=directory))
        else:
            raise _failure('unavailable_binding', str(descriptor.get('binding_id', 'episode_binding')))
    # Missing descriptors preserve old saved runs' original two scientific roles.
    return tuple(factories)


def _standard_bindings(store, directory, settings):
    from .saved_private_binding_catalogue import validate_saved_catalogue, saved_private_factories
    owned = validate_saved_catalogue(settings)
    from .terminal_binding_catalogue import is_fixed_saved_catalogue
    terminal_owned = is_fixed_saved_catalogue(settings)
    if owned is not None and settings.get('episode_application_services') is not None and not terminal_owned:
        raise _failure('unavailable_binding', 'owned_private_service_reconstruction')
    from .default_scientific_binding import VERSION as DEFAULT_VERSION, bind_default_science
    from .episode_bindings import EpisodeBindingRegistry
    from .execution_expectations import ExecutionExpectations
    from .native_timing_information import NativeTimingInformation
    from .resource_estimation import ResourceToolEstimator
    from .saved_run_configuration import _effective_configuration, controller_from_settings
    practical_factory = None
    execution_factory = None
    supplied_services = settings.get('episode_application_services')
    if supplied_services is not None:
        # One explicitly supported, data-backed caller factory. This restores
        # its original snapshot/configuration; it performs no discovery or work.
        from gene_annotation_episode.practical_service_setup import PracticalServiceFactory
        definition = supplied_services.get('definition', {})
        factory_name = supplied_services.get('factory')
        if factory_name == 'gene_annotation_episode.execution_service_setup.ExecutionServiceFactory':
            raise _failure('unavailable_binding', 'historical_execution_service_factory_identity')
        if factory_name == 'gene_annotation_episode.episodic_workflow.root.execution_service_setup.ExecutionServiceFactory':
            from .execution_service_setup import ExecutionServiceFactory
            try:
                execution_factory = ExecutionServiceFactory.from_record(definition)
            except (TypeError, ValueError, KeyError) as error:
                raise _failure('unavailable_binding', 'episode_application_services') from error
            if (execution_factory.as_record() != definition
                    or supplied_services.get('inputs') != 'actual_tool_registry_v1'):
                raise _failure('identity_conflict', 'episode_application_services')
        elif (factory_name !=
                'gene_annotation_episode.practical_service_setup.PracticalServiceFactory'
                or set(definition) != {'version', 'resources', 'initial_information'}
                or definition['version'] != 'practical_service_factory_v1'):
            raise _failure('unavailable_binding', 'episode_application_services')
        else:
            practical_factory = PracticalServiceFactory(definition['resources'], definition['initial_information'])
    if settings.get('native_job_events') is not None:
        raise _failure('unavailable_binding', 'native_job_events')
    if settings['controller'] is None or settings.get('job_episodes') is not None:
        raise _failure('unavailable_binding', settings['bindings']['controller'])
    if settings.get('binding_definitions', {}).get('credit', {}).get('default_entrypoint') != DEFAULT_VERSION:
        raise _failure('unavailable_binding', settings['bindings']['credit'])
    # These constructors restore data-backed configuration only. In particular,
    # no controller factory, credit projector or specialist action is invoked.
    try:
        _, controller = _effective_configuration({'models': settings['models']}, settings['controller'])
        if controller != settings['controller']:
            raise _failure('unavailable_binding', 'controller')
        if execution_factory is not None:
            from .execution_family_composition import construct_family as construct_execution_family
            from .hpc_service_composition import construct_family as construct_hpc_family
            from .monitor_binding_catalogue import construct_family as construct_monitor_family
            from .tool_configuration import reopen_tools
            # Reopen the same data-backed client registry and original actual
            # family descriptors; no discovery or work is selected here.
            tools = reopen_tools(store, directory, settings.get('tool_configuration', {}))
            execution_factory.configure_tool_registry(tools)
            descriptors = settings.get('episode_bindings', [])
            run_id = _read_json(directory/'run.json')['run_id']
            execution_family = construct_execution_family(descriptors, None,
                store=store, run_id=run_id, directory=directory, tool_registry=tools)
            monitor_family = construct_monitor_family(descriptors, None)
            hpc_family = construct_hpc_family(descriptors, None,
                store=store, run_id=run_id, directory=directory)
            registry = EpisodeBindingRegistry((*execution_family, *monitor_family, *hpc_family))
        elif practical_factory is None:
            registry = EpisodeBindingRegistry((factory(None) for factory in _saved_episode_factories(settings, directory)),
                owners=None if owned is None else tuple(row['owner'] for row in owned[1]))
        elif terminal_owned:
            from .terminal_binding_catalogue import (construct_fixed_children,
                factory_configuration, descriptor_parents)
            configuration = factory_configuration(practical_factory, supplied_services)
            parents = descriptor_parents(configuration, settings['episode_bindings'])
            registry = EpisodeBindingRegistry(construct_fixed_children(None, store=store,
                directory=directory, configuration=configuration, parents=parents),
                owners=tuple(row['owner'] for row in owned[1]), terminal_configuration=configuration)
        else:
            raise _failure('unavailable_binding', 'historical_terminal_aggregate_identity')
        if owned is not None:
            from .method_loop.durable import canonical
            if canonical(registry.owner_records()) != canonical(settings['episode_binding_owners']):
                raise _failure('identity_conflict', 'episode_binding_owners')
        if registry.as_record() != settings.get('episode_bindings', []):
            raise _failure('identity_conflict', 'episode_bindings')
        # The standard resolver supplies scientific services to literature. It
        # cannot infer executable operational/monitoring projectors from names
        # or definitions, including extra caller-bound roles.
        if practical_factory is None and execution_factory is None and settings.get('episode_role_credit_bindings', {}) != {}:
            raise _failure('unavailable_binding', 'episode_role_credit_bindings')
        options = bind_default_science(store, run_dir=directory, resume=True, provider_config=None,
            credit_policy=None, initial_known_record_refs=None, project_child_credit=None,
            project_annotation_score=None, binding_definitions=None)
        restored = {name: options[name] for name in ('project_credit', 'project_child_credit',
            'project_annotation_score', 'initial_known_record_refs', 'binding_definitions')} | {
            'controller_factory': controller_from_settings(settings),
            'episode_record_receipts': settings.get('episode_record_receipts') is not None,
            'execution_expectations': (ExecutionExpectations.from_record(settings['execution_expectations'])
                if settings.get('execution_expectations') is not None else None),
            'native_timing_information': (NativeTimingInformation.from_record(settings['native_timing_information'])
                if settings.get('native_timing_information') is not None else None),
            'resource_estimator': (ResourceToolEstimator.from_record(settings['resource_tool_estimator'])
                if settings.get('resource_tool_estimator') is not None else None)}
        if 'annotation_child_roles' in settings:
            from .saved_run_configuration import _recorded_annotation_child_roles
            restored['annotation_child_roles'] = _recorded_annotation_child_roles(settings)
        if practical_factory is not None:
            restored.update(episode_service_factory=practical_factory,
                episode_service_binding=practical_factory.as_record())
        elif execution_factory is not None:
            restored.update(episode_service_factory=execution_factory,
                episode_service_binding=execution_factory.as_record(),
                episode_service_inputs='actual_tool_registry_v1')
        if terminal_owned:
            restored['episode_binding_owners'] = tuple(row['owner'] for row in owned[1])
        elif owned is not None:
            factories, owners = saved_private_factories(settings)
            restored.update(episode_binding_factories=factories, episode_binding_owners=owners)
        return restored
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        raise _failure('unavailable_binding', 'standard_default') from error


def _check_bindings(options, settings):
    from .saved_private_binding_catalogue import validate_saved_catalogue
    owned = validate_saved_catalogue(settings)
    if owned is not None and tuple(options.get('episode_binding_owners') or ()) != tuple(row['owner'] for row in owned[1]):
        raise _failure('identity_conflict', 'episode_binding_owners')
    from .workflow_values import _binding_name, _annotation_child_roles
    from .saved_run_configuration import _recorded_annotation_child_roles
    from .numerical import ESTIMATOR_VERSION, SOURCE_SHA256
    from .episode_application_services import service_binding
    from .episode_bindings import native_job_event_configuration
    try:
        services = service_binding(options.get('episode_service_factory'), options.get('episode_service_binding'),
            inputs=options.get('episode_service_inputs'))
    except (ValueError, TypeError) as error:
        raise _failure('unavailable_binding', 'episode_application_services') from error
    if services != settings.get('episode_application_services'):
        raise _failure('identity_conflict', 'episode_application_services')
    try:
        child_roles = _annotation_child_roles(options.get('annotation_child_roles'))
        saved_child_roles = _recorded_annotation_child_roles(settings)
    except (ValueError, TypeError) as error:
        raise _failure('unavailable_binding', 'annotation_child_roles') from error
    if child_roles != saved_child_roles:
        raise _failure('identity_conflict', 'annotation_child_roles')
    try:
        native_events = native_job_event_configuration(options.get('native_job_events'))
    except (ValueError, TypeError) as error:
        raise _failure('unavailable_binding', 'native_job_events') from error
    if native_events != settings.get('native_job_events'):
        raise _failure('identity_conflict', 'native_job_events')
    enabled = options.get('episode_record_receipts', False)
    expected_receipts = ({'version': 'explicit_store_record_receipts_v1', 'enabled': True}
                        if enabled is True else None)
    if type(enabled) is not bool or settings.get('episode_record_receipts') != expected_receipts:
        raise _failure('identity_conflict', 'episode_record_receipts')
    executable_names = {'credit': 'project_credit', 'scientific_child_credit': 'project_child_credit',
        'annotation_score': 'project_annotation_score'}
    actual = {key: _binding_name(options[name], 'caller_injected') for key, name in executable_names.items()
              if options.get(name) is not None}
    # The standard saved controller is described by the public YieldController
    # class; custom policies retain their original source-qualified factory name.
    actual['controller'] = (_binding_name(options['controller_factory'], 'caller_injected')
        if settings['controller'] is None else 'gene_annotation_episode.episodic_workflow.root.numerical.YieldController')
    if actual != settings['bindings'] or options['binding_definitions'] != settings.get('binding_definitions', {}):
        raise _failure('unavailable_binding', *settings['bindings'].values())
    expected_versions = {name: {'requirement': 'same_caller_injected_executable'} for name in actual}
    if settings['controller'] is not None:
        expected_versions['controller'] = {'estimator_version': ESTIMATOR_VERSION, 'template_sha256': SOURCE_SHA256}
    if settings['binding_versions'] != expected_versions:
        raise _failure('identity_conflict', 'binding_versions')
    for setting, option in (('job_episodes', 'job_episodes'), ('execution_expectations', 'execution_expectations'),
            ('native_timing_information', 'native_timing_information'), ('resource_tool_estimator', 'resource_estimator')):
        value = options.get(option)
        if (None if value is None else value.as_record()) != settings.get(setting):
            raise _failure('identity_conflict', setting)
    saved_known = settings.get('scientific_knowledge', {}).get('initial_known_record_refs')
    known = options.get('initial_known_record_refs')
    if (None if known is None else sorted(set(known))) != saved_known:
        raise _failure('identity_conflict', 'initial_known_record_refs')


