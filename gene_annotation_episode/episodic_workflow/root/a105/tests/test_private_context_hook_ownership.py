"""Whole-family context composition selects actual private hook owners."""
from importlib import import_module
from types import SimpleNamespace
import pytest
from .test_private_literature_bindings import AXIS, HOMES

@pytest.fixture(params=['standalone', 'scientific'])
def family_registry(request):
    services = SimpleNamespace(workflow=SimpleNamespace(store=object()))
    bindings = [import_module(AXIS + '.' + home + '.episode').LiteratureEpisode(services, rate_population=True, assay_grading_population=True) for home in HOMES if home.startswith('scientific_process.') == (request.param == 'scientific')]
    return (import_module(AXIS + '.episode_bindings').EpisodeBindingRegistry(bindings), bindings)

def test_current_report_has_one_private_owner(family_registry, monkeypatch):
    registry, bindings = family_registry
    sheets = import_module(AXIS + '.library.literature_sheet_updates')
    work = import_module(AXIS + '.library.literature_work_report')
    monkeypatch.setattr(sheets, 'current_scoring_sheets', lambda *args: [])
    monkeypatch.setattr(work, 'completed_work', lambda store, context: {'episode_id': context.episode_id})
    pilot = AXIS + '.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination'
    monkeypatch.setattr(import_module(pilot + '.scoring.literature_sheet_updates'), 'current_scoring_sheets', lambda *args: [])
    monkeypatch.setattr(import_module(pilot + '.prompts.literature_work_report'), 'completed_work', lambda store, context: {'episode_id': context.episode_id})
    for binding in bindings:
        role = binding.roles[0]
        context = SimpleNamespace(role=role, path=((role, 'owner'),), episode_id='original-owner')
        assert registry.current_report_facts(context) == {'literature_completed_work': {'episode_id': 'original-owner'}}

def test_external_parent_receives_one_declared_assay_schema(family_registry):
    registry, bindings = family_registry
    owner = next((binding for binding in bindings if binding.roles == ('literature',)))
    expected = owner.received_report_sources('annotation')
    assert expected
    assert registry.received_report_sources('annotation', path=(('annotation', 'original-root'),)) == expected

def test_literature_receivers_do_not_advertise_external_family_arrays(family_registry):
    registry, bindings = family_registry
    for binding in bindings:
        role = binding.roles[0]
        assert registry.received_report_sources(role, path=((role, 'owner'),)) == {}

def test_context_receipt_uses_only_original_owner(family_registry, monkeypatch):
    registry, bindings = family_registry
    calls = []
    for binding in bindings:
        role = binding.roles[0]
        monkeypatch.setattr(binding, 'received_evidence_tokens', lambda context, owner=role: calls.append(owner) or ['saved:' + owner])
    for binding in bindings:
        role = binding.roles[0]
        calls.clear()
        context = SimpleNamespace(role=role, path=((role, 'original-operation'),))
        assert registry.received_evidence_tokens(context) == ['saved:' + role]
        assert calls == [role]
