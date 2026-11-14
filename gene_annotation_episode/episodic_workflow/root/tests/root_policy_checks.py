"""Actual Root method/source/journal interfaces with explicit controlled ports.

The original functions come from permanent exact installed-source fixtures.
Store, Journal, typed contracts and private AnnotationTask remain real. Tool,
provider, scientific projection and native execution are not exercised here.
"""
import ast
import asyncio
from contextlib import contextmanager, ExitStack
from copy import deepcopy
import hashlib
from importlib import import_module
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.action_catalog import ActionCatalog
from gene_annotation_episode.episodic_workflow.root.action_execution import ActionExecution
from gene_annotation_episode.episodic_workflow.root.child_selection import ChildSelection
from gene_annotation_episode.episodic_workflow.root.contract_information import ContractInformation
from gene_annotation_episode.episodic_workflow.root.report_validation import ReportValidation
from gene_annotation_episode.episodic_workflow.root.episode_journal import Journal
from gene_annotation_episode.episodic_workflow.root.method_loop import Context, EpisodeGoal, EpisodeRequest, EpisodeTree, Grain
from gene_annotation_episode.episodic_workflow.root.task import AnnotationTask
from gene_annotation_episode.episodic_workflow.root.task_values import Record
from gene_annotation_episode.episodic_workflow.root.workflow_values import TypedReportContract

PACKAGE = 'gene_annotation_episode.episodic_workflow.root'
FIXTURES = Path(__file__).parent / 'fixtures' / 'root_policy_original'
SCHEMA = {'type': 'object', 'properties': {
    'credit': {'type': 'number', 'x-source': 'credit'}},
    'required': ['credit'], 'additionalProperties': False}
CLASSES = {'action_catalog': 'ActionCatalog', 'action_execution': 'ActionExecution',
    'child_selection': 'ChildSelection', 'contract_information': 'ContractInformation',
    'report_validation': 'ReportValidation', 'to_parent': 'AnnotationToParent',
    'internal_summary': 'AnnotationInternalSummary'}
METHOD_MODULE = {name: owner for owner, names in {
    'action_catalog': ('action_schema', 'reasoning_action_schema', 'catalog'),
    'report_validation': ('facts',),
    'child_selection': ('_default_scientific_child_roles', 'declared_child_roles',
        'available_child_roles', 'validate_child_choice', 'permits_common_action'),
    'contract_information': ('root_child_return_sources', 'child_form_input', 'child_initial_report_input'),
    'action_execution': ('execute', 'selected'), 'to_parent': ('finish',),
    'internal_summary': ('_decision_inputs',),
}.items() for name in names}


def module(name): return import_module(PACKAGE + '.' + name)


def forbidden(*args, **kwargs):
    raise AssertionError('execution outside the explicit Root policy boundary')


def original(name):
    owner = METHOD_MODULE[name]
    authority = json.loads((FIXTURES / 'PROVENANCE.json').read_text())['sources'][owner]
    raw = (FIXTURES / (owner + '.py.source')).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == authority['sha256']
    cls, = [node for node in ast.parse(raw).body if isinstance(node, ast.ClassDef)
            and node.name == CLASSES[owner]]
    function, = [node for node in cls.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and node.name == name]
    # Compile the untouched original node, including literal docstrings, with
    # the authentic current defining module dictionary. Late mutable globals
    # are read exactly as before; no candidate compiler supplies the oracle.
    namespace = {}
    code = compile(ast.Module(body=[function], type_ignores=[]),
                   str(FIXTURES / (owner + '.py.source')), 'exec')
    exec(code, vars(module(owner)), namespace)
    return namespace[name]


class WorkflowProbe(ActionCatalog, ReportValidation, ChildSelection,
                    ContractInformation, ActionExecution):
    """Controlled interface, not a claim of a complete Workflow constructor."""

    def __init__(self, **values): self.__dict__.update(values)


@contextmanager
def host(directory):
    directory.mkdir(parents=True, exist_ok=True)
    store = Store(directory / 'store')
    try:
        subject, = store.create_problem(raw_sequence='ATGAAATAA', molecule='dna', role='gene')['subject_refs']
        journal = Journal(store, 'root-policy-boundary')
        grain = Grain('annotation', 'controlled policy selection', 'typed credit return', forbidden)
        workflow = WorkflowProbe(store=store, journal=journal, run_id=journal.run_id,
            grains={'annotation': grain}, grain_names=('annotation', 'improvement'),
            context=Context(tree=EpisodeTree(grain, {grain: ()}), run_id=journal.run_id),
            services=SimpleNamespace(capabilities=lambda: (), model=forbidden),
            episode_bindings=SimpleNamespace(roles=(), entry_roles=(),
                current_report_facts=lambda context: {}, received_report_facts=lambda context, **kw: {}),
            annotation_child_roles=None, _legacy_scientific_process_binding=None,
            job_episodes=None, receipts=None,
            native_event_information=None, native_timing_information=None,
            project_annotation_score=None, resource_estimator=None,
            project_credit=SimpleNamespace(task_credit=False), root_action_boundary=None,
            execution_binding=None, inprocess_replay=None, controller_binding={},
            tools=SimpleNamespace(), knowledge=SimpleNamespace(context=lambda: {}))
        scope = {'subject_refs': [subject]}
        request = EpisodeRequest(EpisodeGoal.root(objective='Preserve Root policy', result_contract=SCHEMA),
            Record({'scope': scope, 'initial_report': {}}),
            TypedReportContract('Actual typed return interface', SCHEMA, lambda *a: True))
        source = AnnotationTask(workflow, (('annotation', 'original'),), request, scope)
        journal.save('runtime_episodes', {'episode_id': source.episode_id,
            'path': json.dumps(source.path), 'request': json.dumps(request.as_record()),
            'initial_credit': 0.125, 'state': 'active', 'completion': None, 'archive': None})
        workflow.source_credit_view = lambda actual, **kw: {'credit': 0.375}
        workflow.pending_handles = lambda actual: []
        workflow.specialist = lambda actual: None
        workflow.is_job_source = lambda actual: False
        async def release(episode_id): assert episode_id == source.episode_id
        workflow.release = release
        yield workflow, source
    finally:
        store.close()


def call(workflow, name, old, *args, **kwargs):
    method = original(name) if old else getattr(WorkflowProbe, name)
    value = method(workflow, *args, **kwargs)
    return asyncio.run(value) if asyncio.iscoroutine(value) else value


def paired_facts(directory, scenario):
    outcomes = []
    # Import before late replacement: frozen defining-global aliases must fail.
    projection = module('scientific_process.report_snapshot')
    module('library.report_fact_assembly')
    for old in (True, False):
        with host(directory / str(old)) as (workflow, source), ExitStack() as stack:
            events, enrichments = [], []
            completion = SimpleNamespace(ended_by='controller', end_reason='controlled', units_consumed=2)
            if scenario == 'saved':
                workflow.journal.save('runtime_forms', {'episode_id': source.episode_id,
                    'facts': json.dumps({'credit': 0.25, 'interpretations': {'prior': 'unresolved'}}), 'form': None})
                workflow.episode_bindings.current_report_facts = lambda context: events.append('current') or {'current_marker': True}
                workflow.source_credit_view = workflow.pending_handles = forbidden
            else:
                workflow.pending_handles = lambda actual: events.append('pending') or ['owned-pending']
                def credit(actual, **kwargs):
                    events.append('credit')
                    if scenario == 'late_job':
                        workflow.is_job_source = lambda actual: True
                    return {'credit': 0.375}
                workflow.source_credit_view = credit
                workflow.project_annotation_score = object()
                workflow.annotation_context = lambda scope, **kw: events.append('annotation') or {'annotation_score': 0.5}
                workflow.resource_estimator = object()
                stack.enter_context(patch.object(module('report_validation'), 'recorded_forecasts',
                    lambda *a, **kw: events.append('forecasts') or ['controlled_forecast']))
                workflow.job_implementation = lambda **kw: SimpleNamespace(facts=lambda *a, **kw:
                    events.append('late_job') or {'job_marker': True})
                prior_yield = module('report_validation').closing_yield
                def live_yield(record):
                    events.append('live_yield')
                    return prior_yield(record)
                stack.enter_context(patch.object(module('report_validation'), 'closing_yield', live_yield))
                workflow.episode_bindings.received_report_facts = lambda context, **kw: events.append('received') or (
                    {'credit': -1} if scenario == 'received_conflict' else {'received_marker': True})
                if scenario == 'late_scientific':
                    private = projection.complete_scientific_snapshot
                    def observed(*args):
                        enrichments.append('scientific_private')
                        return private(*args)
                    stack.enter_context(patch.object(projection, 'complete_scientific_snapshot', observed))
                    workflow.source_controller_credit = lambda actual: events.append('controller_credit') or 0.0625
                    workflow.services.scientific_parent_invocation = lambda context: events.append('parent_invocation') or 'original_invocation'
                    def project(context, snapshot):
                        events.append(('scientific_facts', deepcopy(snapshot)))
                        assert snapshot['initial_credit'] == 0.125
                        assert snapshot['controller_credit'] == 0.0625
                        assert snapshot['parent_invocation_ref'] == 'original_invocation'
                        return {'scientific_marker': True}
                    binding = SimpleNamespace(facts=project)
                    previous = workflow.store.read_snapshot
                    @contextmanager
                    def late_snapshot():
                        events.append('snapshot')
                        with previous():
                            workflow.scientific_process_binding = binding
                            workflow.specialist = lambda actual: binding
                            yield
                    workflow.store.read_snapshot = late_snapshot
            try:
                result = call(workflow, 'facts', old, source, completion_record=completion)
            except ValueError as error:
                assert scenario == 'received_conflict'
                assert str(error) == 'received_report_fact_conflict'
                result = (type(error).__name__, str(error))
            else:
                assert scenario != 'received_conflict' and 'interpretations' not in result
                if scenario == 'saved':
                    assert result == {'credit': 0.25, 'current_marker': True} and events == ['current']
                elif scenario == 'late_job':
                    assert result['job_marker'] and 'annotation_score' not in result
                    assert events.index('credit') < events.index('late_job') < events.index('received')
                else:
                    assert result['annotation_score'] == 0.5 and result['resource_tool_estimates'] == ['controlled_forecast']
                    assert events.index('annotation') < events.index('forecasts') < events.index('received')
                    if scenario == 'late_scientific':
                        assert result['scientific_marker'] and enrichments == ([] if old else ['scientific_private'])
                        assert events.index('snapshot') < events.index('controller_credit') < events.index('parent_invocation')
            outcomes.append((result, events))
    assert outcomes[0] == outcomes[1]


def paired_schema(directory, scenario):
    outcomes = []
    module('library.action_contracts'); module('library.scientific_child_contracts')
    for old in (True, False):
        with host(directory / str(old)) as (workflow, source), ExitStack() as stack:
            events = []
            workflow.permits_common_action = lambda actual, action: events.append(('permits', action)) or False
            workflow.reasoning_action_schema = lambda actual: events.append('reasoning') or {'kind': 'controlled_reasoning'}
            workflow.root_child_return_sources = lambda actual, role: ()
            workflow.is_job_source = lambda actual: events.append('job_before') or False
            def catalog(scope, *, source):
                events.append('catalog')
                if scenario == 'late_job':
                    workflow.is_job_source = lambda actual: events.append('job_after') or True
                return ()
            workflow.catalog = catalog
            base_object = module('action_catalog')._object
            def live_object(*args, **kwargs):
                events.append('live_object')
                result = base_object(*args, **kwargs)
                result['x-live-provider'] = True
                return result
            stack.enter_context(patch.object(module('action_catalog'), '_object', live_object))
            stack.enter_context(patch.object(module('action_catalog'), 'restricted_root',
                lambda actual, source: events.append('root_classifier') or scenario == 'root_no_receipt'))
            result = call(workflow, 'action_schema', old, source)
            assert result['x-live-provider'] is True
            if scenario == 'late_job':
                assert events.index('catalog') < events.index('job_after')
                assert not any(branch.get('properties', {}).get('kind', {}).get('const') in
                    {'child', 'episode_child', 'redeliver_report'} for branch in result['properties']['selection']['anyOf'])
            if scenario == 'root_no_receipt': assert 'catalog' not in events
            outcomes.append((result, events))
    assert outcomes[0] == outcomes[1]


class BoundaryStop(Exception): pass


def paired_commissioning(directory, scenario):
    outcomes = []
    records = module('scientific_process_records')
    for old in (True, False):
        with host(directory / str(old)) as (workflow, source), ExitStack() as stack:
            events = []
            def invoke(name, *args, **kwargs): return call(workflow, name, old, *args, **kwargs)
            def restricted(actual, item):
                assert actual is workflow and item is source
                events.append('root_classifier'); return True
            for name in ('child_selection', 'action_catalog', 'contract_information', 'action_execution'):
                stack.enter_context(patch.object(module(name), 'restricted_root', restricted))
            if scenario == 'wait':
                workflow.annotation_child_roles = ('literature',)
                workflow.episode_bindings = SimpleNamespace(roles=('literature',),
                    for_child=lambda *a: events.append('child_wait') or SimpleNamespace(supports_wait=False))
                workflow.specialist = forbidden
                value = invoke('permits_common_action', source, 'wait')
                assert value is False and events == ['child_wait']
            elif scenario == 'receipt':
                workflow.specialist = forbidden
                absent = invoke('permits_common_action', source, 'tool')
                workflow.receipts = object()
                present = invoke('permits_common_action', source, 'tool')
                value = absent, present
                assert value == (False, True) and events == ['root_classifier', 'root_classifier']
            elif scenario == 'declarations':
                workflow.job_episodes = SimpleNamespace(roles=('declared_job',))
                workflow.episode_bindings = SimpleNamespace(roles=(), entry_roles=('declared_private',))
                assert workflow.has_scientific_binding is False
                first = invoke('_default_scientific_child_roles')
                workflow.annotation_child_roles = ('declared_private',)
                annotation = invoke('declared_child_roles', 'annotation')
                nested = invoke('declared_child_roles', 'improvement')
                binding = SimpleNamespace(boundary_fixture='non_none_scientific_binding_marker')
                workflow.scientific_process_binding = binding
                assert workflow.scientific_process_binding is binding and workflow.has_scientific_binding is True
                last = invoke('_default_scientific_child_roles')
                value = first, annotation, nested, last
                assert value == (('improvement', 'declared_job', 'declared_private'), ('declared_private',),
                    ('improvement', 'declared_job', 'declared_private'), ('declared_job', 'declared_private'))
            elif scenario == 'declaration_none':
                values = iter((('first_read',), None))
                def getter(actual):
                    assert actual is workflow; events.append('declaration_read'); return next(values)
                stack.enter_context(patch.object(WorkflowProbe, 'annotation_child_roles', property(getter), create=True))
                workflow._default_scientific_child_roles = forbidden
                value = invoke('declared_child_roles', 'annotation')
                assert value is None and events == ['declaration_read', 'declaration_read']
            elif scenario == 'late_filter':
                workflow.declared_child_roles = lambda role: events.append('declared') or ('improvement', 'scientific_process')
                def allowed(context, capabilities):
                    events.append('allowed'); workflow.project_credit.task_credit = True
                    return ('improvement', 'scientific_process')
                workflow.specialist = lambda actual: events.append('specialist') or SimpleNamespace(allowed_children=allowed)
                workflow.services.capabilities = lambda: events.append('capabilities') or ()
                value = invoke('available_child_roles', source)
                assert value == ('scientific_process',) and events == ['declared', 'specialist', 'capabilities', 'allowed']
            elif scenario in ('fresh_arm', 'replay_arm', 'wrong_arm', 'wrong_role'):
                workflow.project_credit.task_credit = True
                selection = {'kind': 'episode_child', 'role': 'scientific_process', 'scope': deepcopy(source.scope),
                    'assignment': {'proposed_annotation_ref': 'original_annotation', 'selection': {
                        'version': records.SELECTION_VERSION, 'evidence_axis': {'option_id': 'original_axis'}}}}
                arm = {'proposed_annotation_ref': 'original_annotation', 'axis': 'original_axis', 'scope': deepcopy(source.scope)}
                workflow.source_credit_view = (forbidden if scenario in ('replay_arm', 'wrong_role') else
                    lambda actual: events.append('credit_arms') or {'credit': {'arms': [] if scenario == 'wrong_arm' else [arm]}})
                try:
                    value = invoke('validate_child_choice', source,
                        'improvement' if scenario == 'wrong_role' else 'scientific_process', selection=selection,
                        original=scenario == 'replay_arm')
                except ValueError as error:
                    assert scenario in ('wrong_role', 'wrong_arm')
                    value = type(error).__name__, str(error)
                    assert str(error) == ('annotation_root_commissions_evidence_axes' if scenario == 'wrong_role'
                        else 'axis_assignment_requires_one_received_annotation_subject_scope')
                else: assert scenario not in ('wrong_role', 'wrong_arm') and value is None
                assert events == ([] if scenario in ('replay_arm', 'wrong_role') else ['credit_arms'])
            elif scenario in ('catalog_none', 'catalog_wait'):
                workflow.receipts = None if scenario == 'catalog_none' else object()
                workflow.shared_information_catalog = lambda actual: events.append('shared_catalog') or (
                    None if scenario == 'catalog_none' else [{'name': 'information'}])
                workflow.permits_common_action = lambda *a: events.append('permission') or True
                stack.enter_context(patch.object(module('action_catalog'), '_wait_estimate_operation',
                    lambda: events.append('wait_operation') or {'name': 'controlled_wait'}))
                value = invoke('catalog', source.scope, source)
                assert value == (None if scenario == 'catalog_none' else [{'name': 'information'}, {'name': 'controlled_wait'}])
            elif scenario in ('execute_rejection', 'execute_lookup'):
                def pending(*args): events.append('lookup'); raise BoundaryStop('composition_lookup')
                workflow.pending_contract_information = pending
                try:
                    value = invoke('execute', source, module('action_execution').CONTRACT_INFORMATION_OPERATIONS[0], {},
                        decision_index=3, operation_key='controlled', _composition_lookup=scenario == 'execute_lookup')
                except BoundaryStop as error:
                    assert scenario == 'execute_lookup'; value = str(error)
                else:
                    assert scenario == 'execute_rejection'
                    assert value == {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [],
                        'result': None, 'feedback': {'code': 'root_tool_requires_shared_coordination_operation'}}
                assert events == (['root_classifier', 'lookup'] if scenario == 'execute_lookup' else ['root_classifier'])
            elif scenario in ('selected_fresh', 'selected_replay'):
                selection = {'kind': 'tool', 'tool': 'unavailable', 'arguments': {}}
                workflow.permits_common_action = lambda *a: True
                workflow.catalog = (forbidden if scenario == 'selected_replay' else
                    lambda *a, **kw: events.append('fresh_catalog') or [])
                def closed(*args): events.append('after_guard'); raise BoundaryStop('saved_guard_passed')
                workflow._closed_child_commission = closed
                if scenario == 'selected_replay':
                    workflow.journal.save('runtime_actions', {'episode_id': source.episode_id, 'decision_index': 3,
                        'action': json.dumps(selection), 'result': json.dumps({'status': 'completed'}), 'credit': None})
                try: invoke('selected', source, deepcopy(selection), 3)
                except ValueError as error:
                    assert scenario == 'selected_fresh' and str(error) == 'action_not_available_to_episode'
                    value = type(error).__name__, str(error)
                except BoundaryStop as error:
                    assert scenario == 'selected_replay'; value = str(error)
                else: raise AssertionError('control must stop before actual selected execution')
                assert events == (['root_classifier', 'fresh_catalog'] if scenario == 'selected_fresh' else ['root_classifier', 'after_guard'])
            elif scenario == 'return_form':
                workflow.project_credit.child_return_sources = lambda context, role: events.append('return_sources') or ('credit',)
                workflow.project_credit.child_return_form = lambda context, role: events.append('return_form') or deepcopy(SCHEMA)
                value = (invoke('root_child_return_sources', source, 'scientific_process'),
                    json.loads(invoke('child_form_input', source, {}, 'scientific_process')),
                    invoke('child_initial_report_input', source, {}, 'scientific_process'))
                assert value == (('credit',), SCHEMA, '{}')
                before = list(events)
                assert invoke('child_form_input', source, {'schema_json': 'supplied'}, 'scientific_process') == 'supplied'
                assert invoke('child_initial_report_input', source, {'initial_report_json': 'original'}, 'scientific_process') == 'original'
                assert before == events
            else: raise AssertionError(scenario)
            outcomes.append((value, events))
    assert outcomes[0] == outcomes[1]


def paired_private(directory, kind, placement):
    outcomes = []
    for old in (True, False):
        with host(directory / str(old)) as (workflow, source), ExitStack() as stack:
            events = []
            name = 'facts' if kind == 'finish' else 'action_schema'
            result_marker = {'credit': 0.75} if kind == 'finish' else {'controlled_schema': placement}
            def override(actual, **kwargs):
                assert actual is source; events.append('override'); return deepcopy(result_marker)
            if placement == 'instance': workflow.__dict__[name] = override
            else:
                assert placement == 'class'
                def class_override(actual_workflow, actual, **kwargs):
                    assert actual_workflow is workflow; return override(actual, **kwargs)
                stack.enter_context(patch.object(WorkflowProbe, name, class_override))
            if kind == 'finish':
                async def release(episode_id):
                    assert episode_id == source.episode_id; events.append('release')
                workflow.release = release
                function = original('finish') if old else type(source).finish
                value = asyncio.run(function(source, SimpleNamespace(units_consumed=2)))
                result = value.as_record()
                saved = workflow.journal.row('runtime_forms', source.episode_id)
                assert result == {'form': {'credit': 0.75}}
                assert json.loads(saved['form']) == {'credit': 0.75}
                assert json.loads(saved['facts']) == {'credit': 0.75, 'interpretations': {}}
                assert events == ['override', 'release']
            else:
                workflow.working_state = lambda actual: {}
                workflow.local_outcome_preview = lambda actual, **kwargs: None
                workflow.source_credit_binding = lambda actual: {}
                workflow.pending_work = lambda actual: []
                workflow.delivery_status = lambda episode: []
                workflow.catalog = lambda *args, **kwargs: []
                workflow.job_episode_options = lambda actual: None
                workflow.extra_report_sources = lambda actual: {}
                workflow.is_scientific_source = lambda actual: False
                workflow.receipt_projection = lambda actual: False
                view = SimpleNamespace(child_reports=(), controller_state={},
                    model_inputs=lambda value, **kwargs: value)
                function = original('_decision_inputs') if old else type(source)._decision_inputs
                context, result = function(source, view)
                assert context['scope'] == source.scope and result == result_marker
                assert events == ['override']
            outcomes.append((result, events))
    assert outcomes[0] == outcomes[1]


def cold_entry(directory, name):
    tree = Path(__file__).resolve().parents[4]
    assert (tree / 'gene_annotation_episode').is_dir()
    directory.mkdir(parents=True, exist_ok=True)
    code = '''import importlib, json, pathlib, sys
tree = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(tree))
package, name = sys.argv[2:]
owner = importlib.import_module(package + '.' + name)
catalog = importlib.import_module(package + '.action_catalog')
reports = importlib.import_module(package + '.report_validation')
roles = importlib.import_module(package + '.child_selection')
contracts = importlib.import_module(package + '.contract_information')
action = importlib.import_module(package + '.library.action_contracts')
facts = importlib.import_module(package + '.library.report_fact_assembly')
private = importlib.import_module(package + '.commissioning_policy')
assert catalog.ActionCatalog.action_schema is action.action_schema
assert reports.ReportValidation.facts is facts.facts
assert contracts.ContractInformation.root_child_return_sources is private.root_child_return_sources
assert private._original_child_selection is roles
assert private._original_action_catalog is catalog
imports = {}
for key, value in tuple(sys.modules.items()):
    if key == 'gene_annotation_episode' or key.startswith('gene_annotation_episode.') or key == 'method_loop' or key.startswith('method_loop.'):
        filename = getattr(value, '__file__', None)
        if filename:
            path = pathlib.Path(filename).resolve()
            assert path.is_relative_to(tree), (key, str(path))
            imports[key] = str(path.relative_to(tree))
print(json.dumps(imports, sort_keys=True))
'''
    # Keep the owning runner's authenticated dependency path. This is a fresh
    # process, not a claimed isolated-mode interpreter; every application
    # origin is still checked against the actual snapshot tree below.
    child = subprocess.run([sys.executable, '-B', '-c', code, str(tree), PACKAGE, name],
        cwd=directory, env=dict(os.environ), capture_output=True, text=True)
    (directory / 'cold.stdout').write_text(child.stdout)
    (directory / 'cold.stderr').write_text(child.stderr)
    assert child.returncode == 0, child.stderr
    imports = json.loads(child.stdout)
    assert PACKAGE + '.' + name in imports
    (directory / 'cold_imports.json').write_text(json.dumps(imports, indent=2, sort_keys=True) + '\n')
