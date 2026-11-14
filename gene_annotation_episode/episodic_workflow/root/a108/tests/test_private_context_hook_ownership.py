"""Copied literature bindings expose each context hook through one private owner."""
from importlib import import_module
from types import SimpleNamespace
import pytest
from .test_private_literature_boundaries import AXIS,HOMES

@pytest.fixture(params=['standalone','scientific'])
def family_registry(request):
    services=SimpleNamespace(workflow=SimpleNamespace(store=object()))
    bindings=[import_module(AXIS+'.'+home+'.episode').LiteratureEpisode(services) for home in HOMES
        if home.startswith('scientific_process.')==(request.param=='scientific')]
    return import_module(AXIS+'.episode_bindings').EpisodeBindingRegistry(bindings),bindings


def test_current_report_has_one_private_owner(family_registry,monkeypatch):
    registry,bindings=family_registry
    sheets=import_module(AXIS+'.library.literature_sheet_updates');work=import_module(AXIS+'.library.literature_work_report')
    monkeypatch.setattr(sheets,'current_scoring_sheets',lambda *args:[])
    monkeypatch.setattr(work,'completed_work',lambda store,context:{'episode_id':context.episode_id})
    for binding in bindings:
        role=binding.roles[0]
        context=SimpleNamespace(role=role,path=((role,'owner'),),episode_id='original-owner')
        assert registry.current_report_facts(context)=={'literature_completed_work':{'episode_id':'original-owner'}}


def test_external_parent_receives_one_declared_contextual_result_schema(family_registry):
    registry,_=family_registry
    declared=registry.received_report_sources('annotation',path=(('annotation','original-root'),))
    assert set(declared)=={'literature_a108_grading_cells','literature_a108_aggregation_cells'}
