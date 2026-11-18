"""Actual Store-backed whole-family callbacks independent of optional tool construction."""
from importlib import import_module
from types import SimpleNamespace

import pytest

AXIS=__package__.rsplit('.tests',1)[0]


def module(name):
    return import_module(AXIS+'.'+name)


@pytest.fixture(params=['published_evidence_assessment', 'perturbation_evidence.published_evidence_assessment'])
def family(request,tmp_path):
    with module('state').Store(tmp_path/'state') as store:
        journal=module('episode_journal').Journal(store,'family-original')
        host=SimpleNamespace(store=store,journal=journal,run_id='family-original')
        services=module('episode_services').WorkflowServices(host)
        bindings=module(request.param+'.episode').create_binding_tree(services)
        registry=module('episode_bindings').EpisodeBindingRegistry(bindings)
        host.episode_bindings=registry
        yield store,registry,bindings


def test_family_external_typed_schema_has_one_applicable_owner(family):
    _,registry,bindings=family
    actual=registry.received_report_sources('annotation',path=(('annotation','original'),))
    expected={} if AXIS.endswith('a101') else bindings[0].received_report_sources('annotation')
    assert actual==expected


def test_family_current_work_is_read_from_each_original_episode(family):
    store,registry,bindings=family
    Context=module('episode_bindings').BindingContext
    for binding in bindings:
        role,=binding.roles
        context=Context(run_id='family-original',episode_id='original-'+role,role=role,
            path=((role,'owner'),),scope={},assignment={},request={},received_record_refs=())
        assert registry.current_report_facts(context)==binding.current_report_facts(context)
    assert store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0]==0
