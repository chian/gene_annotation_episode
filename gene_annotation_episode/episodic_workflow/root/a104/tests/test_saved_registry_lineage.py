"""Real registry and real private owners."""
from pathlib import Path
import pytest
from .api_cases import HOMES, Responses, module
from .saved_binding_workflow import constructor_options


@pytest.fixture(scope='module')
def cases(tmp_path_factory):
    directory = tmp_path_factory.mktemp('private-registry-lineage')
    with module('state').Store(directory / 'store') as store:
        store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
        tools = module('tools').ToolRegistry(store, clients=Responses())
        result = {}
        for ordinal, home in enumerate(HOMES):
            parent_type = module(home.rsplit('/', 1)[0] + '/episode').ExecutionEpisode
            child_type = module(home + '/episode').ExecutionEpisode
            arguments = constructor_options(store, directory / str(ordinal), 'registry-lineage', tools)
            parent, child = parent_type(None, **arguments), child_type(None, **arguments)
            result[home] = (parent, child)
        yield result


@pytest.mark.parametrize('home', HOMES, ids=HOMES)
def test_exact_private_commissioning_parent(cases, home):
    parent, child = cases[home]
    registry = module('episode_bindings').EpisodeBindingRegistry((parent, child))
    parent_path = (('launch', 'runtime-key-is-not-owner-code'),)
    assert child.commissioning_parent == parent.binding_path
    assert registry.for_child(parent_path, 'launch_api') is child
    assert registry.for_path((*parent_path, ('launch_api', 'different-runtime-key'))) is child
    assert registry.for_binding_path(home) is child

