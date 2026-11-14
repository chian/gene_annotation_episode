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
