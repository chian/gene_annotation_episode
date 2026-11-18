"""Actual owned resolver/registry boundaries; guard verdict ports are controlled."""
from importlib import import_module
from types import SimpleNamespace
import pytest

PACKAGE=__package__.rsplit('.tests',1)[0]


def module(name):
    return import_module(PACKAGE+'.'+name)


@pytest.mark.parametrize('family',['molecular','protein'])
@pytest.mark.parametrize('verdict',[False,True])
def test_original_protected_verdict_precedes_generic_scope_resolution(monkeypatch,family,verdict):
    runtime=module('runtime')
    context=module('episode_bindings').BindingContext(run_id='original-run',episode_id='original-owner',
        role='sequence_homology_evidence',path=(('sequence_homology_evidence','original'),),scope={},assignment={},
        request={'message':{'scope':{},'episode_assignment':{}}})
    monkeypatch.setattr(runtime.Episode,'identity',lambda *args,**kwargs:SimpleNamespace(episode_id=context.episode_id))
    calls=[]
    def guard(owner,reference,namespace,**kwargs):
        calls.append((owner,reference,namespace))
        return verdict
    def unrelated(*args,**kwargs):return None
    tools=SimpleNamespace(retained_molecular_reference_access=guard if family=='molecular' else unrelated)
    services=SimpleNamespace(protein_structure_reference_access=guard if family=='protein' else unrelated)
    workflow=SimpleNamespace(run_id=context.run_id,grains={context.role:object()},context=object(),tools=tools,
        services=services,journal=SimpleNamespace(row=lambda *args:None),
        episode_bindings=SimpleNamespace(roles=(),resolve_received_reference=unrelated),
        native_event_information=None,scientific_provenance=None,progress_provider=None,
        store=SimpleNamespace(reference_subset=lambda *args:pytest.fail('protected verdict must precede Store scope fallback')))
    resolve=runtime.Workflow.resolver(workflow,{},context=context)
    assert resolve('artifact_original-protected','artifact') is verdict
    assert calls==[(context,'artifact_original-protected','artifact')]


def test_actual_tool_registry_retains_metadata_guard_without_a_producer(tmp_path):
    with module('state').Store(tmp_path/'state') as store:
        registry=module('tools').ToolRegistry(store,clients=SimpleNamespace())
        guard=getattr(registry,'retained_molecular_reference_access',None)
        assert callable(guard),'original metadata receipt guard is missing'
        assert guard(None,'unrelated-original-reference',None,initial_record_refs=()) is None
        assert store.db.execute('SELECT COUNT(*) FROM tool_operations').fetchone()[0]==0
