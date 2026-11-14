"""Real registry, real private owners; explicit legacy identity protocol fixtures."""
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
            # Only these two declared protocol attributes differ. All actual
            # scientific methods and constructors remain the private classes.
            legacy_type = type('ExplicitLegacyParent', (parent_type,), {'binding_path': None})
            legacy = legacy_type(None, **arguments)
            legacy_child_type = type('ExplicitLegacyChild', (child_type,), {'binding_path': None})
            legacy_child = legacy_child_type(None, **arguments)
            result[home] = (parent, child, legacy, legacy_child)
        yield result


@pytest.mark.parametrize('home', HOMES, ids=HOMES)
def test_exact_private_commissioning_parent(cases, home):
    parent, child, _, _ = cases[home]
    registry = module('episode_bindings').EpisodeBindingRegistry((parent, child))
    parent_path = (('launch', 'runtime-key-is-not-owner-code'),)
    assert child.commissioning_parent == parent.binding_path
    assert registry.for_child(parent_path, 'launch_api') is child
    assert registry.for_path((*parent_path, ('launch_api', 'different-runtime-key'))) is child
    assert registry.for_binding_path(home) is child


@pytest.mark.parametrize('home', HOMES, ids=HOMES)
@pytest.mark.parametrize('boundary', ('direct', 'for_child', 'for_path'))
def test_legacy_parent_cannot_select_unique_unrelated_private_child(cases, home, boundary):
    _, child, legacy, _ = cases[home]
    registry = module('episode_bindings').EpisodeBindingRegistry((legacy, child))
    with pytest.raises(LookupError, match='episode_child_not_bound:None:launch_api'):
        if boundary == 'direct': registry._child_binding(legacy, 'launch_api')
        elif boundary == 'for_child': registry.for_child((('launch', 'legacy'),), 'launch_api')
        else: registry.for_path((('launch', 'legacy'), ('launch_api', 'child')))


@pytest.mark.parametrize('boundary', ('direct', 'for_child', 'for_path'))
def test_unique_legacy_child_compatibility_remains(cases, boundary):
    _, _, parent, child = cases[HOMES[0]]
    registry = module('episode_bindings').EpisodeBindingRegistry((parent, child))
    if boundary == 'direct': value = registry._child_binding(parent, 'launch_api')
    elif boundary == 'for_child': value = registry.for_child((('launch', 'legacy'),), 'launch_api')
    else: value = registry.for_path((('launch', 'legacy'), ('launch_api', 'child')))
    assert value is child
