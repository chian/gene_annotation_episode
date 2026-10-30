"""Reconstruct one saved, parent-owned Episode in an independent process.

Only the ordinary shared loop executes the investigation. This binding restores
the caller's saved policy/resources and original communication boundary; it does
not resume a scientific root, choose work, or adopt newer parent information.
"""
from __future__ import annotations

from contextlib import AsyncExitStack, asynccontextmanager
from functools import partial
import asyncio
import hashlib
import json
from pathlib import Path
import sqlite3
import uuid

from method_loop import EpisodeCompletion, EpisodeGoal
from method_loop.durable import DurableExecutionError, canonical, content_digest, validate_commission

from .state import Store
from .domain import ContractError


VERSION = 'episode_runtime_binding_v1'
FACTORY_MODULE = 'gene_annotation_episode.independent_execution'
FACTORY_NAME = 'open_commission'


def implementation_sha256():
    """Identity of the implementation imported by this executable binding.

    Relative names participate so moving an unchanged pinned checkout is safe.
    Source in both the application and shared loop participates; mutable run
    data, histories, tests and bytecode do not redefine the implementation.
    """
    root = Path(__file__).resolve().parent.parent
    files = sorted(path for package in ('gene_annotation_episode', 'method_loop')
                   for path in (root/package).rglob('*.py'))
    digest = hashlib.sha256()
    for path in files:
        digest.update(str(path.relative_to(root)).encode('utf-8') + b'\0')
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def _read_json(path):
    try:
        return json.loads(Path(path).read_text())
    except FileNotFoundError as error:
        raise _failure('unavailable_binding', str(path)) from error
    except (ValueError, TypeError) as error:
        raise _failure('identity_conflict', str(path)) from error


def _failure(code, *references):
    return DurableExecutionError(code, affected_refs=references)


def _settings(store, directory):
    manifest = _read_json(directory/'run.json')
    row = store.db.execute('SELECT settings FROM runtime_runs WHERE run_id=?',
                           (manifest['run_id'],)).fetchone()
    if row is None:
        raise _failure('unavailable_binding', str(directory/'run.json'))
    settings = json.loads(row[0])
    if (manifest != {'run_id': manifest['run_id'], **settings}
            or settings['directory'] != str(directory)
            or settings['problem'] != store.problem()):
        raise _failure('identity_conflict', str(directory/'run.json'))
    return manifest['run_id'], settings


def make_runtime_binding(workspace, run_dir, *, kind='standard_default', tool_configuration=None):
    """Pin a supported caller reconstruction, without starting any Episode.

    Custom callables require the caller's own C1 factory instead. Supplying a
    tool configuration here records the caller's actual configuration; worker
    reopening also compares the resulting resource binding to the saved run.
    """
    workspace = Path(getattr(workspace, 'path', workspace)).expanduser().resolve()
    directory = Path(run_dir).expanduser().resolve()
    if kind not in {'fixed_case', 'standard_default'}:
        raise _failure('unavailable_binding', kind)
    if not (workspace/'state.sqlite3').is_file():
        raise _failure('unavailable_binding', str(workspace))
    with Store(workspace) as store:
        _, settings = _settings(store, directory)
        if kind == 'standard_default':
            # A declaration on the root credit alone cannot reconstruct the
            # caller's other executables. Use the worker's actual resolver and
            # comparison before publishing a capability to commission work.
            options = _standard_bindings(store, directory, settings)
            _check_bindings(options, settings)
    pins = {}
    if kind == 'fixed_case':
        for name in ('case-launch.json', 'policy-binding.json'):
            path = directory/name
            if not path.is_file():
                raise _failure('unavailable_binding', str(path))
            pins[name] = content_digest(_read_json(path))
        case = _read_json(directory/'case-launch.json')
        configuration = case['configuration']
        if Path(configuration['workspace']).resolve() != workspace:
            raise _failure('identity_conflict', str(workspace))
        if tool_configuration is not None and tool_configuration != configuration:
            raise _failure('identity_conflict', str(directory/'case-launch.json'))
        tool_configuration = configuration
    else:
        if tool_configuration is None:
            tool_configuration = settings.get('tool_configuration', {})
    arguments = {'version': VERSION, 'workspace': str(workspace), 'run_directory': str(directory),
        'kind': kind, 'tool_configuration': tool_configuration, 'caller_binding_pins': pins}
    # Finite JSON is the only persisted argument representation.
    arguments = json.loads(canonical(arguments))
    return {'factory_module': FACTORY_MODULE, 'factory_name': FACTORY_NAME, 'arguments': arguments,
        'implementation_sha256': implementation_sha256(), 'settings_sha256': content_digest(settings)}


def _saved_episode_factories(settings, directory=None):
    """Restore known data-backed bindings; never infer a custom factory."""
    factories = []
    for descriptor in settings.get('episode_bindings', []):
        if descriptor.get('binding_id') == 'literature':
            from .literature_episodes import LiteratureEpisodes
            factories.append(partial(LiteratureEpisodes, **descriptor['configuration']))
        elif descriptor.get('binding_id') == 'scientific_process':
            from .episode_composition import reopen_scientific_binding
            factories.append(partial(reopen_scientific_binding,
                descriptor=descriptor, directory=directory))
        else:
            raise _failure('unavailable_binding', str(descriptor.get('binding_id', 'episode_binding')))
    # Missing descriptors preserve old saved runs' original two scientific roles.
    return tuple(factories)


def _standard_bindings(store, directory, settings):
    from .default_scientific_binding import VERSION as DEFAULT_VERSION, bind_default_science
    from .episode_bindings import EpisodeBindingRegistry
    from .execution_expectations import ExecutionExpectations
    from .native_timing_information import NativeTimingInformation
    from .resource_estimation import ResourceToolEstimator
    from .runtime import _effective_configuration, controller_from_settings
    practical_factory = None
    execution_factory = None
    supplied_services = settings.get('episode_application_services')
    if supplied_services is not None:
        # One explicitly supported, data-backed caller factory. This restores
        # its original snapshot/configuration; it performs no discovery or work.
        from .practical_service_setup import PracticalServiceFactory
        definition = supplied_services.get('definition', {})
        factory_name = supplied_services.get('factory')
        if factory_name == 'gene_annotation_episode.execution_service_setup.ExecutionServiceFactory':
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
            from .execution_episodes import ExecutionEpisodes
            from .episode_monitoring import MonitorEpisodes
            from .tool_configuration import build_tools
            options = execution_factory.as_record()
            # Reopen the original data-backed client registry, without making
            # an HTTP call or discovering a resource. API bindings require the
            # real internal publication/client ports even during validation.
            tools = build_tools(store, settings.get('tool_configuration', {}))
            registry = EpisodeBindingRegistry([
                ExecutionEpisodes(None, store=store, directory=directory,
                    run_id=_read_json(directory/'run.json')['run_id'], tool_registry=tools,
                    **{key: options[key] for key in ('resources', 'initial_information',
                        'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles')}),
                MonitorEpisodes(None, outcome_page_size=options['monitor_outcome_page_size'])])
        elif practical_factory is None:
            registry = EpisodeBindingRegistry(factory(None) for factory in _saved_episode_factories(settings, directory))
        else:
            from .practical_resource_episodes import PracticalResourceEpisodes
            registry = EpisodeBindingRegistry([PracticalResourceEpisodes(None, directory=directory,
                resources=practical_factory.resources,
                initial_information=practical_factory.initial_information)])
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
            from .runtime import _recorded_annotation_child_roles
            restored['annotation_child_roles'] = _recorded_annotation_child_roles(settings)
        if practical_factory is not None:
            restored.update(episode_service_factory=practical_factory,
                episode_service_binding=practical_factory.as_record())
        elif execution_factory is not None:
            restored.update(episode_service_factory=execution_factory,
                episode_service_binding=execution_factory.as_record(),
                episode_service_inputs='actual_tool_registry_v1')
        return restored
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        raise _failure('unavailable_binding', 'standard_default') from error


def _check_bindings(options, settings):
    from .runtime import _binding_name, _annotation_child_roles, _recorded_annotation_child_roles
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
        if settings['controller'] is None else 'gene_annotation_episode.numerical.YieldController')
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


def _check_assignment(store, spec):
    child, parent = spec['child'], spec['parent']
    rows = {}
    for side in ('parent', 'child'):
        identity = spec[side]['episode_id']
        row = store.db.execute('SELECT path,request FROM runtime_episodes WHERE run_id=? AND episode_id=?',
            (spec['run_id'], identity)).fetchone()
        if row is None:
            raise _failure('identity_conflict', identity)
        rows[side] = {'path': json.loads(row['path']), 'request': json.loads(row['request'])}
        if rows[side]['path'] != spec[side]['path']:
            raise _failure('identity_conflict', identity)
    if rows['child']['request'] != child['request']:
        raise _failure('identity_conflict', child['episode_id'])
    parent_request = rows['parent']['request']
    parent_goal = EpisodeGoal.from_record(parent_request['goal'])
    if parent_goal.goal_id != parent['goal_id']:
        raise _failure('identity_conflict', parent['episode_id'])
    scope = store.validate_scope(child['scope'], parent_scope=parent_request['message']['scope'])
    if scope != child['scope'] or scope != child['request']['message']['scope']:
        raise _failure('identity_conflict', child['episode_id'])
    for operand in spec['input_versions']:
        try:
            record = store.get(operand['reference'])
        except ContractError as error:
            raise _failure('identity_conflict', operand['reference']) from error
        version = record.get('version')
        if operand['version'] is not None and operand['version'] != (None if version is None else str(version)):
            raise _failure('identity_conflict', operand['reference'])
        expected = operand['content_sha256']
        if expected is not None:
            try:
                actual = (hashlib.sha256(store.get_artifact(operand['reference'])).hexdigest()
                          if record['record_type'] == 'artifact' else content_digest(record))
            except ContractError as error:
                raise _failure('identity_conflict', operand['reference']) from error
            if expected != actual:
                raise _failure('identity_conflict', operand['reference'])
    return parent_goal, scope


def _partial_record_refs(store, run_id, episode_id):
    """References from this execution's actual recorded work, never its inputs."""
    references = []
    queries = [('runtime_actions', 'run_id=? AND episode_id=?', (run_id, episode_id))]
    prefix = run_id+':'+episode_id+':'
    for table in ('tool_operations', 'reasoning_commits'):
        if store.db.execute('SELECT 1 FROM sqlite_master WHERE type=? AND name=?', ('table', table)).fetchone():
            queries.append((table, 'substr(operation_key,1,?)=?', (len(prefix), prefix)))
    for table, predicate, parameters in queries:
        for field in ('record_refs', 'changed_record_refs', 'native_execution_refs'):
            rows = store.db.execute(f'SELECT refs.value FROM {table} work '
                f'JOIN json_each(work.result,?) refs WHERE {predicate}', ('$.'+field, *parameters))
            for row in rows:
                if row[0] not in references:
                    references.append(row[0])
    return references


@asynccontextmanager
async def open_commission(spec):
    """C1 factory consumed by method_loop.durable_worker, with owned cleanup."""
    spec = validate_commission(spec)
    binding, handle = spec['runtime_binding'], spec['handle']
    args = binding['arguments']
    if (binding['factory_module'] != FACTORY_MODULE or binding['factory_name'] != FACTORY_NAME
            or set(args) != {'version', 'workspace', 'run_directory', 'kind',
                             'tool_configuration', 'caller_binding_pins'}
            or args['version'] != VERSION or args['kind'] not in {'fixed_case', 'standard_default'}):
        raise _failure('unavailable_binding', handle)
    if binding['implementation_sha256'] != implementation_sha256():
        raise _failure('identity_conflict', handle)
    workspace, directory = (Path(args[name]).expanduser().resolve() for name in ('workspace', 'run_directory'))
    if not (workspace/'state.sqlite3').is_file():
        raise _failure('unavailable_binding', str(workspace))
    async with AsyncExitStack() as resources:
        store = resources.enter_context(Store(workspace))
        run_id, settings = _settings(store, directory)
        if run_id != spec['run_id'] or content_digest(settings) != binding['settings_sha256']:
            raise _failure('identity_conflict', handle)
        for name, expected in args['caller_binding_pins'].items():
            if name not in {'case-launch.json', 'policy-binding.json'} or content_digest(_read_json(directory/name)) != expected:
                raise _failure('identity_conflict', handle)
        parent_goal, scope = _check_assignment(store, spec)
        if args['kind'] == 'fixed_case':
            from .case_execution import prepared_case_bindings
            try:
                manifest, options = resources.enter_context(prepared_case_bindings(store, directory, resume=True))
            except (ValueError, TypeError, KeyError) as error:
                raise _failure('identity_conflict', handle) from error
            if manifest['configuration'] != args['tool_configuration']:
                raise _failure('identity_conflict', handle)
        else:
            options = _standard_bindings(store, directory, settings)
        _check_bindings(options, settings)
        from .tool_configuration import build_tools
        from .providers import ModelConnection
        from .runtime import ReleasingContext, assemble_workflow
        tools = build_tools(store, args['tool_configuration'])
        if tools.resource_binding() != settings['initial_tool_resources']:
            raise _failure('unavailable_binding', 'initial_tool_resources')
        transports = directory/'providers'
        transports.mkdir(exist_ok=True)
        provider = ModelConnection(settings['models'], transports/uuid.uuid4().hex, directory,
            image_resolver=getattr(tools, 'resolve_image_input', None))
        resources.push_async_exit(provider)
        executable_options = {key: value for key, value in options.items() if key != 'binding_definitions'}
        specialist_options = ({} if options.get('episode_service_factory') is not None else
            {'episode_binding_descriptors': settings.get('episode_bindings', [])})
        workflow = assemble_workflow(store, tools, provider, directory, run_id, settings,
            **specialist_options, **executable_options)
        workflow.configure_execution(binding, execution_handle=spec['handle'])
        if workflow.episode_application_services_binding != settings.get('episode_application_services'):
            raise _failure('identity_conflict', 'episode_application_services')
        if (options.get('episode_service_factory') is not None and
                workflow.episode_job_progress_provider_binding != settings.get('episode_job_progress_provider')):
            raise _failure('identity_conflict', 'episode_job_progress_provider')
        if workflow.episode_bindings.as_record() != settings.get('episode_bindings', []):
            raise _failure('identity_conflict', 'episode_bindings')
        from .runtime import _binding_name, _plain
        role_definitions = {role: {'definition': _plain(definition),
            'projector': _binding_name(workflow.role_credit_projectors[role], 'caller_injected')}
            for role, definition in workflow.role_credit_definitions.items()}
        if role_definitions != settings.get('episode_role_credit_bindings', {}):
            raise _failure('unavailable_binding', 'episode_role_credit_bindings')
        child, message = spec['child'], spec['child']['request']['message']
        inheritance = message.get('knowledge_inheritance')
        if workflow.receipts is not None:
            try:
                frozen = workflow.receipts.manifest(child['episode_id'])
            except ValueError as error:
                raise _failure('identity_conflict', child['episode_id']) from error
            if inheritance != frozen or frozen['parent_episode_id'] != spec['parent']['episode_id']:
                raise _failure('identity_conflict', child['episode_id'])
        elif inheritance is not None:
            raise _failure('identity_conflict', child['episode_id'])
        assignment = message.get('job_assignment')
        contract = workflow.returned_request(spec).report_contract
        episode = workflow.build(child['role'], child['key'], spec['child']['request']['goal']['objective'], scope,
            parent=parent_goal, parent_path=tuple(tuple(part) for part in spec['parent']['path']),
            contract=contract, initial=message['initial_report'], job_assignment=assignment,
            episode_assignment=message.get('episode_assignment'),
            scientific_process=message.get('scientific_process'),
            **({'report_contract_declaration': message['report_contract_declaration']}
               if 'report_contract_declaration' in message else {}))
        if episode.request.as_record() != spec['child']['request']:
            raise _failure('identity_conflict', child['episode_id'])
        context = ReleasingContext.from_commission(tree=workflow.tree, run_id=run_id,
            parent_path=spec['parent']['path'], parent_goal_id=parent_goal.goal_id,
            child_goal_id=episode.goal.goal_id, grain=child['role'], key=child['key'])
        workflow.context = context

        def pack_result(record, result):
            saved = workflow.journal.row('runtime_forms', child['episode_id'])
            if saved is None:
                raise _failure('invalid_return', child['episode_id'])
            facts = json.loads(saved['facts'])
            facts.pop('interpretations', None)
            return {'completion': EpisodeCompletion.from_record(record).as_record(),
                'episode_archive': (record.archived_record or workflow.archive.store(record)).descriptor(),
                'result_archive': workflow.archive.store(result).descriptor(),
                'form': result.as_record()['form'],
                'facts_archive': workflow.archive.store(facts).descriptor(),
                'pending_handles': workflow.pending_handles(episode.source)}

        await provider.__aenter__()
        try:
            yield {'episode': episode, 'context': context, 'pack_result': pack_result}
        except BaseException as error:
            # Valid committed work survives an interrupted later decision or
            # representation. These refs are recovery information, not a form
            # interpretation, successful completion or new parent observation.
            try:
                references = _partial_record_refs(store, run_id, child['episode_id'])
            except (sqlite3.Error, ValueError):
                references = []
            if references:
                failure = (dict(error.failure) if isinstance(error, DurableExecutionError) else {
                    'code': ('interrupted_execution' if isinstance(error, (KeyboardInterrupt, asyncio.CancelledError))
                             else 'execution_failed'),
                    'affected_refs': [handle], 'diagnostic_ref': None, 'partial_record_refs': []})
                failure['partial_record_refs'] = list(dict.fromkeys([*failure['partial_record_refs'], *references]))
                raise DurableExecutionError(**failure) from error
            raise
        finally:
            await workflow.release(child['episode_id'])


__all__ = ['make_runtime_binding', 'open_commission', 'implementation_sha256', 'VERSION']
