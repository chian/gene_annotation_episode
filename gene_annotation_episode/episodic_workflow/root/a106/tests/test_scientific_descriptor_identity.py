"""Fresh private scientific descriptors preserve exact version and configuration identity."""
from copy import deepcopy
from importlib import import_module
from types import SimpleNamespace

import pytest

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


@pytest.mark.parametrize('changed',['configuration','implementation_sha256','binding_id','version'])
def test_scientific_descriptor_identity_never_accepts_changed_implementation(changed):
    actual=descriptor();other=deepcopy(actual)
    if changed=='configuration':other[changed]['original_operand']='different'
    elif changed=='implementation_sha256':other[changed]='0'*64
    elif changed=='binding_id':other[changed]='different'
    else:other[changed]='scientific_process_episodes_v10'
    assert not import_module(AXIS+'.episode_composition').scientific_binding_compatible(actual,other)


@pytest.mark.parametrize('version',[f'scientific_process_episodes_v{number}' for number in range(5,11)])
def test_original_historical_version_identity_is_retained(version):
    original={**descriptor(),'version':version}
    assert import_module(AXIS+'.episode_composition').scientific_binding_compatible(original,deepcopy(original))
