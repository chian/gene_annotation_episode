"""Original default evaluation and custom cached-object fallback boundaries."""
import builtins
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from .. import runtime
from ..task import AnnotationTask
from .. import child_message_owners
from ..episode_bindings import EpisodeBindingRegistry
from ..episode import selects_annotation_parent
from .annotation_parent_exchange_checks import parent_host, isolated_rows
from .annotation_host_checks import host_workflow
from .annotation_parent_original_boundaries import original_method


@pytest.mark.parametrize('replace_default', (False, True))
def test_original_default_resolution_precedes_private_constructor(tmp_path, replace_default):
    observations = []
    with parent_host(tmp_path) as host:
        for original in (True, False):
            with isolated_rows(host):
                events = []
                workflow = host_workflow(host, events)
                class Jobs:
                    @property
                    def roles(self):
                        raise AssertionError('build added a job roles callback')
                workflow.job_episodes = Jobs()
                default = runtime.DecisionSource
                class SuppliedDefault(default):
                    def __init__(self, *args, **kwargs):
                        events.append('supplied_default_constructor')
                        super().__init__(*args, **kwargs)
                def tracked_getattr(value, name, *fallback):
                    if name == 'decision_source_type':
                        assert value is None
                        events.append(('original_getattr', fallback[0] is
                            (SuppliedDefault if replace_default else default)))
                    return builtins.getattr(value, name, *fallback)
                with patch.object(runtime, 'DecisionSource', SuppliedDefault if replace_default else default), \
                     patch.object(runtime, 'getattr', tracked_getattr, create=True):
                    call = original_method('build') if original else runtime.Workflow.build
                    episode = call(workflow, 'annotation', 'parent', 'Actual default selection', host.scope,
                        initial={'qualification': 'unresolved'})
                    assert type(episode.source) is (SuppliedDefault if replace_default else
                        default if original else AnnotationTask)
                assert events[0] == ('original_getattr', True)
                assert events.count(('original_getattr', True)) == 1
                observations.append((events, episode.request.as_record()))
    assert observations[0] == observations[1]


@pytest.mark.parametrize('field', ('_by_role', '_by_path'))
def test_custom_cached_keys_do_not_gain_nominal_callbacks(tmp_path, field):
    with parent_host(tmp_path) as host:
        events = []
        workflow = host_workflow(host, events)
        class CustomKey(str):
            def __hash__(self):
                events.append('hash')
                return hash('annotation')
            def __eq__(self, other):
                events.append('equality')
                return str.__eq__(self, other)
        setattr(workflow.episode_bindings, field, {CustomKey('annotation'): []})
        events.clear()
        assert not selects_annotation_parent(workflow, 'annotation', (), None)
        assert events == []


def test_custom_role_is_not_hashed_by_nominal_exchange_selector(tmp_path):
    with parent_host(tmp_path) as host:
        events = []
        workflow = host_workflow(host, events)
        request = runtime.EpisodeRequest(runtime.EpisodeGoal.root(objective='Original selection',
            result_contract={}), runtime.Record({'scope': host.scope, 'initial_report': {}}))
        source = AnnotationTask(workflow, (('annotation', 'parent'),), request, host.scope)
        class CustomRole(str):
            def __hash__(self):
                raise AssertionError('nominal selector hashed custom role')
            def __eq__(self, other):
                raise AssertionError('nominal selector compared custom role')
        assert child_message_owners.exchange_for_child(workflow, source, CustomRole('launch')) is None

def test_custom_metaclass_does_not_enter_nominal_type_guards(tmp_path):
    from ..episode import safe_cached_registry, plain_path
    with parent_host(tmp_path) as host:
        events = []
        workflow = host_workflow(host, events)
        class EqualityTrap(type):
            def __eq__(cls, other):
                raise AssertionError('nominal type guard called metaclass equality')
        class ForeignContainer(metaclass=EqualityTrap):
            pass
        foreign = ForeignContainer()
        workflow.episode_bindings._by_role['unregistered'] = foreign
        assert not safe_cached_registry(workflow)
        assert not plain_path(foreign)
        assert not plain_path((foreign,))
        assert not selects_annotation_parent(workflow, 'annotation', foreign, None)
