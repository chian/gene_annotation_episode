"""Four original parent edges through real task/registry/message boundaries.

Scientific assignment and execution-context validation are explicit supplied
ports. No scientific process, provider, native job or model is executed. The
real selected action, task constructors, Store, Journal, typed contracts and
child unit remain active. The retained original selected method is the oracle.
"""
import asyncio
from contextlib import contextmanager, ExitStack
from copy import deepcopy
from importlib import import_module
import json
from types import SimpleNamespace
from unittest.mock import patch

from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.episode_journal import Journal
from gene_annotation_episode.episodic_workflow.root.episode_bindings import EpisodeBindingRegistry
from gene_annotation_episode.episodic_workflow.root.method_loop import (
    Context, Episode, EpisodeGoal, EpisodeRequest, EpisodeTree, Grain,
    ReportDeliveryError,
)
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
from gene_annotation_episode.episodic_workflow.root.task_values import Record
from gene_annotation_episode.episodic_workflow.root.report_redelivery import ReportRedelivery
from gene_annotation_episode.episodic_workflow.root.action_execution import ActionExecution
from operational_original_runtime import OriginalActionExecution
from operational_private_boundary_checks import isolated_rows

ROOT = 'gene_annotation_episode.episodic_workflow.root'
EDGES = ('annotation-improvement', 'improvement-improvement',
         'annotation-scientific', 'scientific-scientific')
SCHEMA = {'type': 'object', 'properties': {
    'qualification': {'type': 'string', 'const': 'unresolved'}},
    'required': ['qualification'], 'additionalProperties': False}
INITIAL = {'qualification': 'unresolved'}


def forbidden(*args, **kwargs):
    raise AssertionError('execution outside the parent message boundary')


class EmptyCatalog:
    def as_record(self):
        return {'boundary_fixture': 'no_scientific_options_or_tool_execution'}

    def headers(self):
        return ()

    resolve = staticmethod(forbidden)


@contextmanager
def parent_host(directory):
    from gene_annotation_episode.episodic_workflow.root.scientific_process.episode import ScientificProcessEpisodes
    store = Store(directory / 'store')
    try:
        subject, = store.create_problem(raw_sequence='ATGAAATAA', molecule='dna', role='gene')['subject_refs']
        journal = Journal(store, 'parent-directional-boundaries')
        services = SimpleNamespace(capabilities=lambda: (), model=forbidden)
        scientific = ScientificProcessEpisodes(services, library=EmptyCatalog(),
            tool_library=EmptyCatalog(), child_roles=('scientific_process',))
        grains = {role: Grain(role, 'one original decision', 'one typed return', forbidden)
                  for role in ('annotation', 'improvement', 'scientific_process')}
        tree = EpisodeTree(grains['annotation'], {
            grains['annotation']: (grains['improvement'], grains['scientific_process']),
            grains['improvement']: (grains['improvement'],),
            grains['scientific_process']: (grains['scientific_process'],)},
            self_nesting=('improvement', 'scientific_process'))
        yield SimpleNamespace(store=store, journal=journal, scientific=scientific,
            services=services, grains=grains, context=Context(tree=tree, run_id=journal.run_id),
            scope={'subject_refs': [subject]})
    finally:
        store.close()


def task_type(role):
    if role == 'annotation':
        return import_module(ROOT + '.task').AnnotationTask
    if role == 'improvement':
        return import_module(ROOT + '.legacy_annotation.task').LegacyAnnotationTask
    return import_module(ROOT + '.scientific_process.decision_source').ScientificDecisionSource


def observe(host, edge, scenario, *, original=False, custom_registry=False):
    """Exercise selected() and its actual returned child-unit callbacks."""
    parent_name, child_name = edge.split('-')
    parent_role = 'scientific_process' if parent_name == 'scientific' else parent_name
    role = 'scientific_process' if child_name == 'scientific' else 'improvement'
    events, owners, built = [], [], []
    bindings = (host.scientific,) if role == 'scientific_process' else ()

    class CustomRegistry(EpisodeBindingRegistry):
        @property
        def roles(self):
            events.append('custom_roles')
            return super().roles

    registry = (CustomRegistry if custom_registry else EpisodeBindingRegistry)(bindings)
    path = (('annotation', 'root'),)
    if parent_role != 'annotation':
        path += ((parent_role, 'original-parent'),)
    goal = EpisodeGoal.root(objective='Preserve the original parent edge', result_contract=SCHEMA)
    parent_request = EpisodeRequest(goal, Record({'scope': host.scope, 'initial_report': INITIAL}))
    workflow = SimpleNamespace(store=host.store, journal=host.journal, run_id=host.journal.run_id,
        services=host.services, grains=host.grains, context=host.context,
        episode_bindings=registry, annotation_child_roles=('improvement', 'scientific_process'),
        has_scientific_binding=role == 'scientific_process', execution_binding=None,
        inprocess_replay=None, root_action_boundary=None, receipts=None,
        episode_branch_lifecycle=None, job_episodes=SimpleNamespace(assign=forbidden),
        wait_inputs_version=None, completed_action_inputs_version=None)
    source = task_type(parent_role)(workflow, path, parent_request, host.scope)
    binding_context = lambda actual: BindingContext(host.journal.run_id, actual.episode_id,
        actual.path[-1][0], actual.path, actual.scope, {}, actual.request.as_record())
    injected = RuntimeError('controlled scientific preparation failure')
    expanded_failure = RuntimeError('controlled original expanded-form failure')
    prepared_assignment = {'boundary_assignment': 'unchanged opaque original port result'}
    prepared_process = {'boundary_process': 'unchanged opaque original port result'}
    def expanded(*args, **kwargs):
        events.append('expanded_form')
        if scenario == 'expanded-error':
            raise expanded_failure
        return deepcopy(SCHEMA), None
    def prepare(context, actual_role, assignment, scope, key, **kwargs):
        events.append(('prepare_invocation', actual_role, deepcopy(assignment), deepcopy(scope),
                       key, deepcopy(kwargs)))
        assert context.episode_id == source.episode_id
        if scenario == 'prepare-error':
            raise injected
        return {'assignment': prepared_assignment, 'scientific_process': prepared_process}
    def validate_report(value, scope, **kwargs):
        events.append(('validate_report', deepcopy(value), kwargs['grain']))
    def build(actual_role, key, objective, scope, **kwargs):
        events.append('build')
        assert actual_role == role
        if role == 'scientific_process':
            assert kwargs['episode_assignment'] is prepared_assignment
            assert kwargs['scientific_process'] is prepared_process
        else:
            assert kwargs['episode_assignment'] is None and kwargs['scientific_process'] is None
        assert kwargs['job_assignment'] is None
        request = EpisodeRequest(EpisodeGoal.child(kwargs['parent'], objective=objective,
            result_contract=SCHEMA), Record({'scope': scope, 'initial_report': kwargs['initial']}),
            kwargs['contract'])
        child_path = kwargs['parent_path'] + ((actual_role, key),)
        child_source = task_type(actual_role)(workflow, child_path, request, scope)
        built.append({'path': child_path, 'request': request.as_record(),
                      'assignment': kwargs['episode_assignment'], 'process': kwargs['scientific_process']})
        return Episode(host.grains[actual_role], key, child_source, request, forbidden)
    def receive(actual, form, schema, index, **kwargs):
        assert actual is source
        events.append(('receive_form', deepcopy(form), index, kwargs))
        return []
    def credit(actual):
        assert actual is source
        events.append('original_credit_port')
        return {'credit': 0.375}
    workflow.validate_child_choice = lambda *a, **kw: events.append('validate_child_choice')
    workflow.permits_common_action = lambda *a: False if a[-1] == 'wait' else True
    workflow._closed_child_commission = lambda *a: None
    workflow.binding_selection_for_child = lambda *a: None
    workflow.expanded_contract_form = expanded
    workflow.child_initial_report_input = lambda *a: json.dumps(
        {'qualification': 'invented'} if scenario == 'initial-invalid' else INITIAL)
    workflow.binding_context = binding_context
    workflow.specialist = lambda actual: host.scientific if parent_role == 'scientific_process' else None
    workflow.available_child_roles = lambda *a: ('scientific_process',)
    workflow.scientific_binding = lambda actual: host.scientific
    workflow.launch_instructions = SimpleNamespace(materialize=lambda value: events.append(('materialize', value)))
    workflow.build = build
    workflow.resolver = lambda *a, **kw: (lambda *a: True)
    workflow.validate_report = validate_report
    workflow.is_job_source = lambda *a: False
    workflow.receive_form = receive
    workflow.delivery_feedback = ReportRedelivery.delivery_feedback
    workflow.save_attempt = ReportRedelivery.save_attempt.__get__(workflow)
    workflow.source_credit_view = credit
    workflow.controller_value = lambda actual, index, value: Record({'original_credit': value})
    selection = {'kind': 'episode_child' if role == 'scientific_process' else 'child',
        'role': role, 'scope': deepcopy(host.scope), 'goal': 'Original child objective',
        'purpose': 'A typed unresolved qualification', 'assignment': {'launch_instructions': None}}
    from gene_annotation_episode.episodic_workflow.root import predefined_child_message_owners as selectors
    select = selectors.exchange_for_child if role == 'scientific_process' else selectors.exchange_for_improvement
    exchange = select(workflow, source, role)
    if custom_registry:
        assert exchange is None
    else:
        assert exchange is not None and len(exchange) == 3
    assert events == [], 'selection must not evaluate a registry roles/provider callback early'
    original_for_child, original_for_role = registry.for_child, registry.for_role
    def for_child(*args, **kwargs):
        events.append('for_child')
        return original_for_child(*args, **kwargs)
    def for_role(*args, **kwargs):
        events.append(('for_role', args[0]))
        return original_for_role(*args, **kwargs)
    with ExitStack() as stack:
        stack.enter_context(patch.object(registry, 'for_child', for_child))
        stack.enter_context(patch.object(registry, 'for_role', for_role))
        stack.enter_context(patch.object(host.scientific, 'prepare_invocation', prepare))
        stack.enter_context(patch.object(host.scientific, 'validate_execution_context',
            lambda context: events.append('validate_execution_context')))
        if exchange is not None:
            for callback in exchange:
                def observed(*args, _callback=callback, **kwargs):
                    owners.append((_callback.__module__, _callback.__name__))
                    return _callback(*args, **kwargs)
                stack.enter_context(patch.object(import_module(callback.__module__), callback.__name__, observed))
        error, returned, unit = None, None, None
        try:
            call = OriginalActionExecution.selected if original else ActionExecution.selected
            unit = call(workflow, source, deepcopy(selection), 7)
            if scenario.startswith('return-'):
                form = INITIAL if scenario == 'return-valid' else {'qualification': 'invented'}
                try:
                    returned = asyncio.run(unit.synthesize_report(Record({'form': form}), None, unit.child.request))
                except ReportDeliveryError as failed:
                    # Invoke the real selected unit's original failure receiver.
                    # The supplied controller value is not a scientific credit claim.
                    returned = unit.receive_failure(failed).as_record()
                    error = failed
        except Exception as caught:
            error = caught
        action = host.journal.row('runtime_actions', source.episode_id, 7)
        attempts = [dict(row) for row in host.store.db.execute(
            'SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? ORDER BY decision_index',
            (host.journal.run_id, source.episode_id))]
    return SimpleNamespace(events=events, owners=owners, built=built,
        error=None if error is None else (type(error).__name__, str(error)),
        injected=error is injected, expanded_failure=error is expanded_failure,
        result=returned, action=None if action is None else dict(action), attempts=attempts,
        source_outcome=source.last_outcome, source_index=source.last_outcome_index,
        feedback=source.feedback, selection=selection, has_unit=unit is not None)


def paired(host, edge, scenario, *, custom_registry=False):
    with isolated_rows(host):
        old = observe(host, edge, scenario, original=True, custom_registry=custom_registry)
    with isolated_rows(host):
        new = observe(host, edge, scenario, original=False, custom_registry=custom_registry)
    fields = ('events', 'built', 'error', 'injected', 'expanded_failure', 'result',
              'action', 'attempts', 'source_outcome', 'source_index', 'feedback', 'selection', 'has_unit')
    assert {name: getattr(old, name) for name in fields} == {name: getattr(new, name) for name in fields}
    assert old.owners == []
    if custom_registry:
        assert new.owners == []
    else:
        assert new.owners and new.owners[0][1] == 'prepare_request'
    return new
