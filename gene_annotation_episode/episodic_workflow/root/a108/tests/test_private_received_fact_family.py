"""Literature-family membership remains distinct from private role admission."""
from importlib import import_module
from types import SimpleNamespace
import pytest
from .test_private_literature_boundaries import AXIS,HOMES

@pytest.mark.parametrize('family',['standalone','scientific'])
def test_sibling_literature_bindings_do_not_advertise_duplicate_received_fact_arrays(family):
    bindings=[import_module(AXIS+'.'+home+'.episode').LiteratureEpisode(SimpleNamespace()) for home in HOMES
        if home.startswith('scientific_process.')==(family=='scientific')]
    Registry=import_module(AXIS+'.episode_bindings').EpisodeBindingRegistry
    registry=Registry(bindings)
    for binding in bindings:
        # Explicit single-role invocation is an established registry entry path.
        role=binding.roles[0]
        assert registry.received_report_sources(role,path=((role,'source'),))=={}
        for sibling in bindings:
            assert sibling.received_report_sources(role)=={}
            assert sibling.received_report_facts(SimpleNamespace(role=role))=={}
