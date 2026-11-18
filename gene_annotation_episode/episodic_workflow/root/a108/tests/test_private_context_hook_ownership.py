"""Copied literature bindings expose each context hook through one private owner."""
from importlib import import_module
from types import SimpleNamespace
import pytest
from .test_private_literature_boundaries import AXIS,HOMES

@pytest.fixture(params=['standalone','scientific'])
def family_registry(request):
    services=SimpleNamespace(workflow=SimpleNamespace(store=object()))
    bindings=[import_module(AXIS+'.'+home+'.episode').LiteratureEpisode(services) for home in HOMES
        if home.startswith('sample_context_evidence.')==(request.param=='scientific')]
    return import_module(AXIS+'.episode_bindings').EpisodeBindingRegistry(bindings),bindings




def test_external_parent_receives_one_declared_contextual_result_schema(family_registry):
    registry,_=family_registry
    declared=registry.received_report_sources('annotation',path=(('annotation','original-root'),))
    assert set(declared)=={'literature_a108_grading_cells','literature_a108_aggregation_cells'}
