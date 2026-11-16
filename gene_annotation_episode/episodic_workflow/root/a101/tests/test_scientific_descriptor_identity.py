"""Fresh private scientific descriptors preserve exact version and configuration identity."""
from copy import deepcopy
from importlib import import_module
from types import SimpleNamespace


AXIS=__package__.rsplit('.tests',1)[0]


def descriptor():
    Binding=import_module(AXIS+'.scientific_process.episode').ScientificProcessEpisode
    library=SimpleNamespace(as_record=lambda:{'version':'original-library'},headers=lambda:[])
    tools=SimpleNamespace(as_record=lambda:{'version':'original-tools'})
    return Binding(SimpleNamespace(),library=library,tool_library=tools,
                   child_roles=('scientific_process',)).as_record()


def test_actual_fresh_scientific_descriptor_is_compatible_with_itself():
    actual=descriptor()
    assert actual['version']=='scientific_process_episode_v10'
    assert import_module(AXIS+'.episode_composition').scientific_binding_compatible(actual,deepcopy(actual))

