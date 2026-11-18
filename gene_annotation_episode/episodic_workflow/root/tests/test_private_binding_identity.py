"""Parent-specific routing infrastructure; no autonomous scientific run."""
from importlib import import_module
from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from .axis_roles import HEAD as AXIS_ROLE


AXES = ('a101', 'a102', 'a103', 'a104', 'a105', 'a106', 'a107', 'a108', 'a110')


@pytest.fixture(params=AXES)
def registry_type(request):
    return import_module(
        f'gene_annotation_episode.episodic_workflow.root.{request.param}.episode_bindings'
    ).EpisodeBindingRegistry


class Binding:
    """Explicit fixture graph with two parents commissioning the same role."""
    def __init__(self, role, path=None, parent=None, children=(), entry=True):
        self.roles = (role,)
        self.entry_roles = (role,) if entry else ()
        self.children = children
        if path is not None:
            self.binding_path = path
            self.commissioning_parent = parent

    def child_roles(self, role):
        return self.children

    def as_record(self):
        return {'binding_id': getattr(self, 'binding_path', self.roles[0])}

    def credit_kind(self, role):
        return 'scientific'

    def assignment_schema(self, role):
        return {}

    def permitted_common_actions(self, context):
        return ()

    def allowed_children(self, parent, caller_capabilities):
        return self.children

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        return selection

    def instructions(self, context):
        return ''

    def decision_context(self, context, current_view):
        return {}

    def catalog(self, context):
        return {}

    def execute(self, context, tool_name, arguments, operation_key):
        raise AssertionError('routing must not execute work')

    def fact_sources(self, role):
        return {}

    def facts(self, context, completion_snapshot):
        return {}

    def resolve(self, context, reference, namespace):
        return False

    def validate_report(self, context, form, original_schema):
        pass

    def credit_view(self, context, receiver_selection):
        return {}


def graph(registry_type):
    first = Binding('investigate', 'investigation', 'legacy_annotation', ('monitor',))
    second = Binding('allocate', 'allocation', 'legacy_annotation', ('monitor',))
    first_child = Binding('monitor', 'investigation/monitoring', 'investigation',
                          ('monitor',), entry=False)
    second_child = Binding('monitor', 'allocation/monitoring', 'allocation',
                           ('monitor',), entry=False)
    return registry_type((first, second, first_child, second_child)), first_child, second_child


def test_distinct_parents_register_and_dispatch(registry_type):
    registry, first, second = graph(registry_type)
    root = (('annotation', 'root'),)
    assert registry.for_path((*root, ('investigate', 'a'), ('monitor', 'one'))) is first
    assert registry.for_path((*root, ('allocate', 'b'), ('monitor', 'two'))) is second
    assert registry.for_child((*root, ('allocate', 'b')), 'monitor') is second
    assert registry.for_binding_path('investigation/monitoring') is first
    assert registry.for_binding_path('allocation/monitoring') is second
    with pytest.raises(LookupError, match='episode_role_requires_parent:monitor'):
        registry.for_role('monitor')


def test_recursion_and_saved_path_ignore_invocation_keys(registry_type):
    registry, first, second = graph(registry_type)
    path = (('annotation', 'saved'), ('allocate', 'child_27'),
            ('monitor', 'child_18'), ('monitor', 'child_3'))
    assert registry.for_path(path) is second
    restored = registry_type(tuple(reversed(registry._bindings)))
    assert restored.for_path(tuple(tuple(item) for item in path)) is second
    assert restored.for_path((('annotation', 'other'), ('investigate', 'x'),
                              ('monitor', 'y'))) is first


def test_missing_counterpart_never_uses_other_parent(registry_type):
    first = Binding('investigate', 'investigation', 'legacy_annotation', ('monitor',))
    second = Binding('allocate', 'allocation', 'legacy_annotation', ('monitor',))
    child = Binding('monitor', 'investigation/monitoring', 'investigation', entry=False)
    registry = registry_type((first, second, child))
    with pytest.raises(LookupError, match='episode_child_not_bound'):
        registry.for_child((('annotation', 'root'), ('allocate', 'a')), 'monitor')


def test_real_literature_branches_retain_private_identity(registry_type):
    package = registry_type.__module__.rsplit('.', 1)[0]
    head = AXIS_ROLE[package.rsplit('.', 1)[1]]
    standalone = import_module(package + '.published_evidence_assessment.episode').LiteratureEpisode(object())
    nested = import_module(package + '.' + head + '.published_evidence_assessment.episode').LiteratureEpisode(object())
    parent = Binding(head, head, 'legacy_annotation', ('literature',))
    registry = registry_type((parent, standalone, nested))
    root = (('annotation', 'root'),)
    assert registry.for_child(root, 'literature') is standalone
    assert registry.for_child((*root, (head, 'child')), 'literature') is nested
    records = registry.as_record()
    assert {item['binding_id'] for item in records} == {
        head, standalone.binding_path, nested.binding_path}


def test_context_hooks_do_not_read_other_parents_state(registry_type):
    registry, first, second = graph(registry_type)
    first.current_report_facts = lambda context: {'owner': 'investigation'}
    second.current_report_facts = lambda context: {'owner': 'allocation'}
    context = SimpleNamespace(path=(('annotation', 'root'), ('allocate', 'a'), ('monitor', 'saved')))
    assert registry.current_report_facts(context) == {'owner': 'allocation'}
    first.received_report_sources = lambda role: {'owner': {'meaning': 'investigation'}}
    second.received_report_sources = lambda role: {'owner': {'meaning': 'allocation'}}
    assert registry.received_report_sources('monitor', path=context.path) == {
        'owner': {'meaning': 'allocation'}}


def test_runtime_specialist_and_credit_use_original_path(registry_type):
    runtime = import_module(registry_type.__module__.rsplit('.', 1)[0] + '.runtime')
    registry, first, second = graph(registry_type)
    first.credit_projector = lambda context: 'investigation-credit'
    second.credit_projector = lambda context: 'allocation-credit'
    context = SimpleNamespace(role='monitor', path=(('annotation', 'root'), ('allocate', 'a'), ('monitor', 'saved')))
    workflow = SimpleNamespace(episode_bindings=registry)
    assert runtime.Workflow.specialist(workflow, context) is second
    assert runtime.Workflow.scientific_projector_for_context(workflow, context) == 'allocation-credit'
    assert runtime.Workflow.declared_child_roles(workflow, 'monitor', path=context.path) == ('monitor',)


def test_runtime_return_contract_discovery_uses_commissioning_parent(registry_type):
    runtime = import_module(registry_type.__module__.rsplit('.', 1)[0] + '.runtime')
    registry, first, second = graph(registry_type)
    first.fact_sources = lambda role: {'private_owner': {'meaning': 'investigation'}}
    second.fact_sources = lambda role: {'private_owner': {'meaning': 'allocation'}}
    workflow = SimpleNamespace(episode_bindings=registry, job_episodes=None,
        native_timing_information=None,
        native_event_information=None, project_annotation_score=None, resource_estimator=None)
    facts = runtime.Workflow.report_sources(workflow, 'monitor',
        parent_path=(('annotation', 'root'), ('allocate', 'saved')))
    assert facts['private_owner'] == {'meaning': 'allocation'}


def test_build_connects_correct_private_task_and_preserves_default(registry_type, monkeypatch):
    runtime = import_module(registry_type.__module__.rsplit('.', 1)[0] + '.runtime')
    registry, first, second = graph(registry_type)

    class InvestigationTask(runtime.DecisionSource):
        pass

    class AllocationTask(runtime.DecisionSource):
        pass

    first.decision_source_type = InvestigationTask
    second.decision_source_type = AllocationTask
    monkeypatch.setattr(runtime.Episode, 'identity', lambda *args, **kwargs: SimpleNamespace(episode_id='saved'))
    monkeypatch.setattr(runtime, 'FeedbackEpisode', lambda grain, key, source, *args, **kwargs: source)
    workflow = SimpleNamespace(
        context=object(), grains={'monitor': object()}, inprocess_completion_order=None,
        receipts=None, episode_bindings=registry,
        contract_information_profile=lambda source: None,
        journal=SimpleNamespace(row=lambda *args: None, save=lambda *args: None), run_id='routing',
        store=SimpleNamespace(transaction=nullcontext, db=SimpleNamespace(execute=lambda *args: None)),
        source_credit_view=lambda source: {'credit': 0}, expose_assigned_job=lambda source: None,
        receive_tool_attributions=lambda *args, **kwargs: None,
        archive=SimpleNamespace(store=lambda value: value))
    setattr(workflow, AXIS_ROLE[runtime.__name__.split('.')[-2]] + '_binding', None)
    workflow.specialist = lambda source: runtime.Workflow.specialist(workflow, source)
    parent_path = (('annotation', 'root'), ('allocate', 'saved_parent'))
    source = runtime.Workflow.build(workflow, 'monitor', 'saved_child', 'Observe', {}, parent_path=parent_path)
    assert type(source) is AllocationTask
    assert source.path == (*parent_path, ('monitor', 'saved_child'))
    workflow.episode_bindings = registry_type(tuple(reversed(registry._bindings)))
    rebuilt = runtime.Workflow.build(workflow, 'monitor', 'saved_child', 'Observe', {}, parent_path=parent_path)
    assert type(rebuilt) is AllocationTask
    del second.decision_source_type
    default = runtime.Workflow.build(workflow, 'monitor', 'saved_child', 'Observe', {}, parent_path=parent_path)
    assert type(default) is runtime.DecisionSource
