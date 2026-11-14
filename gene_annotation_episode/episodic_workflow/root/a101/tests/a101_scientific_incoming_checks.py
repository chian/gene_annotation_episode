"""Six genuine Scientific child bindings and their connected incoming owners.

Store, ToolRegistry, Workflow, registry, concrete binding descriptors, the root
Scientific task and child task constructors, Episode identities, Journal and
typed admission are real. Scientific context validation, child preparation,
receiving and execution remain explicit supplied ports. This controls actual
selected/saved/nonreceipt dispatch, not a filled Scientific investigation.
"""
import asyncio
from contextlib import contextmanager, ExitStack
from copy import deepcopy
from functools import partial
import json
from types import SimpleNamespace
from unittest.mock import patch

from .test_a101_implicit_parent_protocol import own, original_function, root

ROUTES = (
    ('execution_job_submission', 'episode_child', 'launch', 'ExecutionEpisode', 'execution'),
    ('execution_progress_assessment', 'episode_child', 'monitor', 'MonitorEpisode', 'monitor'),
    ('execution_result_acquisition', 'episode_child', 'results', 'ExecutionEpisode', 'execution'),
    ('published_evidence_assessment', 'episode_child', 'literature', 'LiteratureEpisode', 'literature'),
    ('resource_work_submission', 'episode_child', 'launch', 'ResourceEpisode', 'resource'),
    ('resource_result_acquisition', 'episode_child', 'results', 'ResourceEpisode', 'resource'),
)
SCHEMA = {'type': 'object', 'properties': {
    'qualification': {'type': 'string', 'const': 'unresolved'}},
    'required': ['qualification'], 'additionalProperties': False}
INITIAL = {'qualification': 'unresolved'}


def forbidden(*args, **kwargs):
    raise AssertionError('outside the controlled A101 parent boundary')


class EmptyCatalog:
    def as_record(self): return {'boundary_fixture': 'explicit empty supplied catalogue'}
    def headers(self): return ()
    resolve = staticmethod(forbidden)


@contextmanager
def genuine_host(directory, route):
    home, kind, role, class_name, family = route
    directory.mkdir(parents=True, exist_ok=True)
    runtime = own('runtime')
    with ExitStack() as cleanup, own('state').Store(directory / 'store') as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        tools = own('tools').ToolRegistry(store)
        factories = []
        run_id = 'a101-scientific-incoming'
        prefix = 'scientific_process.'
        if family == 'execution':
            homes = ('execution_job_submission', 'execution_result_acquisition',
                     'execution_job_submission.api_job_execution',
                     'execution_job_submission.local_job_execution',
                     'execution_job_submission.hpc_job_execution')
            for target in homes:
                factories.append(partial(own(prefix + target + '.episode').ExecutionEpisode,
                    store=store, directory=directory, run_id=run_id,
                    resources={'original-api': {'kind': 'api', 'service': 'bvbrc_appservice',
                        'execution_contract': 'bvbrc_appservice_execution_v1',
                        'endpoints': {'AppService': 'https://construction.invalid/app',
                                      'Workspace': 'https://construction.invalid/workspace'},
                        'scientific_adapters': []}},
                    initial_information={'original-api': {'recorded_inventory': 'original-caller-snapshot'}},
                    tool_registry=tools, handoff_unit=1, acquired_record_unit=1,
                    log_window_bytes=128, log_roles=('stdout', 'stderr')))
        elif family == 'resource':
            homes = ('resource_work_submission', 'resource_result_acquisition',
                     'resource_work_submission.api_resource_work_execution',
                     'resource_work_submission.local_resource_work_execution',
                     'resource_work_submission.hpc_resource_work_execution')
            factories = [own(prefix + target + '.episode').ResourceEpisode for target in homes]
        elif family == 'monitor':
            factories = [own(prefix + home + '.episode').MonitorEpisode]
        elif family == 'literature':
            strategy = home + '.evidence_search_strategy_improvement'
            search = strategy + '.source_relevance_assessment'
            page = search + '.source_evidence_examination'
            homes = (home, strategy, search, page, page + '.table_evidence_extraction',
                     page + '.source_coverage_improvement', page + '.passage_evidence_extraction')
            factories = [own(prefix + target + '.episode').LiteratureEpisode for target in homes]
        else:
            raise AssertionError(family)
        numerical = own('numerical')
        def controller(path, initial):
            return numerical.YieldController('parent-directional-control', initial, .5, numerical.YieldParameters())
        factories.insert(0, partial(own('scientific_process.episode').ScientificProcessEpisode,
            library=EmptyCatalog(), tool_library=EmptyCatalog(), child_roles=('scientific_process', role)))
        workflow = runtime.Workflow(store, tools, SimpleNamespace(complete=forbidden),
            directory / 'workflow', run_id, controller, lambda *args, **kwargs: 0.0,
            episode_binding_factories=tuple(factories), annotation_child_roles=('scientific_process',),
            decision_protocol=None)
        annotation = root(workflow).source
        parent = workflow.scientific_process_binding
        assert type(parent) is own('scientific_process.episode').ScientificProcessEpisode
        assert workflow.episode_bindings.for_child(annotation.path, 'scientific_process') is parent
        scope = store.validate_scope(annotation.scope, parent_scope=annotation.scope)
        path = annotation.path + (('scientific_process', 'supplied-context'),)
        request = runtime.EpisodeRequest(
            runtime.EpisodeGoal.child(annotation.request.goal,
                objective='Controlled original Scientific receiving boundary', result_contract=SCHEMA),
            runtime.Record({'scope': scope, 'initial_report': INITIAL, 'episode_assignment': {}}),
            runtime.TypedReportContract('Controlled original Scientific receiving boundary', SCHEMA,
                lambda *_args: True))
        source = parent.decision_source_type(workflow, path, request, scope)
        assert type(source) is own('scientific_process.task').ScientificInvestigationTask
        assert workflow.specialist(source) is parent
        binding = workflow.episode_bindings.for_child(source.path, role)
        assert type(binding) is getattr(own(prefix + home + '.episode'), class_name)
        assert binding.binding_path == 'scientific_process/' + home
        assert binding.commissioning_parent == 'scientific_process'
        yield workflow, source, binding
        assert store.db.execute('SELECT COUNT(*) FROM tool_operations').fetchone()[0] == 0
        assert store.db.execute('SELECT COUNT(*) FROM runtime_model_calls').fetchone()[0] == 0


@contextmanager
def original_rows(workflow):
    class RestoreRows(Exception): pass
    try:
        with workflow.store.transaction():
            yield
            raise RestoreRows()
    except RestoreRows:
        pass


def observe(workflow, source, binding, route, scenario, *, original):
    runtime = own('runtime')
    home, kind, role, _, _ = route
    events, owners = [], []
    index = 7
    selection = {'kind': kind, 'role': role, 'scope': deepcopy(source.scope),
        'goal': 'Preserve this actual parent edge', 'purpose': 'Typed unresolved qualification',
        'assignment': {'launch_instructions': None}, 'form_schema_json': json.dumps(SCHEMA),
        'initial_report_json': json.dumps({'qualification': 'invented'} if scenario == 'initial-invalid' else INITIAL)}
    if role == 'monitor':
        selection['assignment'] = {'version': 'monitor_assignment_v1',
            'target_handle': 'controlled-original-progress-target', 'requested_fields': ['execution_status'],
            'known_progress_refs': [], 'permitted_committed_record_types': []}
    expected_assignment = {'controlled_original_preparation': home}
    class PreparedFailure(Exception): pass
    class BuildBoundary(Exception): pass
    def expanded(*args, **kwargs):
        events.append('expanded_form')
        return deepcopy(SCHEMA), None
    def materialize(value):
        events.append(('materialize', value))
    def prepare(parent, actual_role, assignment, scope, key, **kwargs):
        assert parent.episode_id == source.episode_id and actual_role == role
        events.append(('prepare_assignment', actual_role, deepcopy(assignment), deepcopy(scope), key, deepcopy(kwargs)))
        if scenario == 'prepare-error': raise PreparedFailure('original preparation error')
        if role == 'scientific_process':
            return {'assignment': deepcopy(expected_assignment), 'scientific_process': {'controlled_process': home}}
        return deepcopy(expected_assignment)
    def assign(store, actual_role, selected, scope, *, operation_key):
        assert store is workflow.store and actual_role == role
        events.append(('assign', actual_role, deepcopy(selected), deepcopy(scope), operation_key))
        if scenario == 'prepare-error': raise PreparedFailure('original preparation error')
        return deepcopy(expected_assignment)
    def validate_report(form, scope, **kwargs):
        events.append(('validate_report', deepcopy(form), kwargs.get('grain')))
    def resolver(*args, **kwargs):
        return lambda *args, **kwargs: True
    built = []
    def build(actual_role, key, objective, scope, **kwargs):
        assert actual_role == role
        expected_slot = 'job_assignment' if kind == 'job_child' else 'episode_assignment'
        assert kwargs[expected_slot] == expected_assignment
        child_path = source.path + ((actual_role, key),)
        child_request = runtime.EpisodeRequest(
            runtime.EpisodeGoal.child(kwargs['parent'], objective=objective, result_contract=SCHEMA),
            runtime.Record({'scope': scope, 'initial_report': kwargs['initial'],
                            expected_slot: kwargs[expected_slot]}), kwargs['contract'])
        child_source = binding.decision_source_type(workflow, child_path, child_request, scope)
        assert type(child_source) is binding.decision_source_type
        assert child_source.episode_id == runtime.Episode.identity(workflow.context,
            workflow.grains[role], key, parent_path=source.path).episode_id
        events.append(('build', child_path, child_request.as_record()))
        built.append(child_source)
        if scenario in ('request-valid', 'initial-invalid', 'prepare-error'):
            raise BuildBoundary('actual child constructor reached before scientific/native initialization')
        return runtime.Episode(workflow.grains[role], key, child_source, child_request, forbidden)
    def receive(actual, form, schema, decision_index, **kwargs):
        assert actual is source
        events.append(('receive_form', deepcopy(form), decision_index, deepcopy(kwargs)))
        return []
    async def unresolved(actual, view, **kwargs):
        assert actual is source
        events.append(('original_resolution_port', kwargs))
        raise runtime.ReportDeliveryError(runtime.Record(source.feedback))
    actual_common = workflow.permits_common_action
    def common(actual, action):
        return actual_common(actual, action) if actual is source else False
    outgoing = own('scientific_process.to_child_' + home)
    preparer = outgoing.prepare_request if role == 'literature' else outgoing.prepare_commission
    incoming = own('scientific_process.from_child_' + home)
    exchange = own('scientific_process.incoming_message_owners').admission_for_prepared_request(workflow, source, preparer, role)
    assert exchange == (incoming.admit_return, incoming.admit_unowned_return)
    assert events == []
    error, returned, attempts = None, [], []
    with ExitStack() as changes:
        parent = workflow.scientific_process_binding
        def context_port(context):
            assert context.role == 'scientific_process' and context.path == source.path
            events.append(('supplied_scientific_context_validation', context.role))
        changes.enter_context(patch.object(parent, 'validate_context', context_port))
        changes.enter_context(patch.object(parent, 'validate_execution_context', context_port))
        for name, value in {'expanded_contract_form': expanded, 'build': build,
                'validate_report': validate_report, 'resolver': resolver, 'receive_form': receive,
                'resolve_pending_deliveries': unresolved, 'permits_common_action': common}.items():
            changes.enter_context(patch.object(workflow, name, value))
        changes.enter_context(patch.object(workflow.launch_instructions, 'materialize', materialize))
        if kind == 'job_child':
            changes.enter_context(patch.object(workflow.job_episodes, 'assign', assign))
        else:
            changes.enter_context(patch.object(binding,
                'prepare_invocation' if role == 'scientific_process' else 'prepare_assignment', prepare))
        endpoint_modules = (incoming, incoming)
        for module, callback in zip(endpoint_modules, exchange):
            assert getattr(module, callback.__name__) is callback
            assert callback.__module__ == module.__name__
            def observed(*args, _callback=callback, _module=module, **kwargs):
                owners.append((_module.__name__, _callback.__name__))
                return _callback(*args, **kwargs)
            changes.enter_context(patch.object(module, callback.__name__, observed))
        call = original_function('Workflow', 'selected') if original else runtime.Workflow.selected
        try:
            unit = call(workflow, source, deepcopy(selection), index)
            if scenario in ('return-valid', 'saved-failure', 'nonreceipt-valid'):
                if scenario == 'nonreceipt-valid':
                    # These are existing mutable runtime fields. The genuine
                    # constructor above still uses its accepted lifecycle; this
                    # control covers the retained original fallback callback,
                    # not a newly admitted constructor configuration.
                    changes.enter_context(patch.object(workflow, 'receipts', None))
                    changes.enter_context(patch.object(workflow, 'episode_branch_lifecycle', None))
                values = [{'qualification': 'invented'}, INITIAL] if scenario == 'saved-failure' else [INITIAL]
                for form in values:
                    try:
                        value = asyncio.run(unit.synthesize_report(runtime.Record({'form': form}), None, unit.child.request))
                        returned.append(('returned', value))
                    except runtime.ReportDeliveryError as failure:
                        returned.append(('failed', failure.feedback.as_record()))
                attempts = [dict(row) for row in workflow.store.db.execute(
                    'SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? ORDER BY decision_index',
                    (workflow.run_id, source.episode_id))]
        except Exception as failure:
            error = (type(failure).__module__, type(failure).__qualname__, str(failure))
        if scenario == 'request-valid':
            assert error is not None and error[1].endswith('BuildBoundary') and len(built) == 1
        elif scenario == 'initial-invalid':
            assert error is not None and 'BuildBoundary' not in error[1]
            assert not built and not any(isinstance(e, tuple) and e[0] in ('prepare_assignment', 'assign') for e in events)
        elif scenario == 'prepare-error':
            assert error is not None and error[1].endswith('PreparedFailure') and not built
        elif scenario in ('return-valid', 'nonreceipt-valid'):
            assert error is None and returned == [('returned', INITIAL)]
            assert len(attempts) == 1 and attempts[0]['failure'] is None
        elif scenario == 'saved-failure':
            assert error is None and len(returned) == 2 and all(item[0] == 'failed' for item in returned)
            assert returned[0] == returned[1]
            assert len(attempts) == 1 and attempts[0]['failure'] is not None
        if original:
            assert owners == []
        else:
            if scenario in ('return-valid', 'saved-failure'):
                assert (incoming.__name__, 'admit_return') in owners
            if scenario == 'nonreceipt-valid':
                assert (incoming.__name__, 'admit_unowned_return') in owners
                assert (incoming.__name__, 'admit_return') not in owners
        assert all(set(row) == {'run_id', 'parent_episode_id', 'decision_index',
            'delivery_ref', 'child_episode_id', 'contract', 'form', 'failure',
            'timing_receipts', 'report_contract_declaration'} for row in attempts)
        return {'events': events, 'error': error, 'returned': returned, 'attempts': attempts}
