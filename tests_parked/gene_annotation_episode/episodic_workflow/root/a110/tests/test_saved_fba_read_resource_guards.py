"""Controlled mutation guards; these cases do not qualify a real publication."""
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.saved_fba_resource_declaration import SavedFBAResourceDeclaration
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.saved_fba_read_resources import SavedFBAReadResources


def controlled_resources(monkeypatch):
    calls = []
    def qualified(value, ordinary, context, *, reader):
        calls.append(value.resource_id)
        return json.loads(value.qualified_json)
    monkeypatch.setattr(SavedFBAResourceDeclaration, 'requalify', qualified)
    store = object()
    context = SimpleNamespace(run_id='controlled-run', as_record=lambda: {'run_id': 'controlled-run'})
    ordinary = SimpleNamespace(store=store)
    configuration = {'controlled': 'read-guard-only'}
    declaration = SavedFBAResourceDeclaration('qualified', canonical(configuration),
        ('controlled-publication',), canonical({'controlled': 'qualification-port'}))
    value = SavedFBAReadResources(ordinary, context, reader=lambda *a, **k: None,
        declarations=(declaration,))
    return value, store, {'qualified': configuration}, calls


def test_unchanged_declaration_is_requalified_on_each_consuming_read(monkeypatch):
    value, store, resources, calls = controlled_resources(monkeypatch)
    assert calls == ['qualified']
    assert value.check(store=store, run_id='controlled-run', resources=resources) == frozenset({'qualified'})
    value.as_record(store=store, run_id='controlled-run', resources=resources)
    assert calls == ['qualified', 'qualified', 'qualified']


@pytest.mark.parametrize('mutation', ['append', 'remove', 'replace', 'qualification', 'truncate_ports'])
def test_unqualified_or_replaced_declaration_cannot_gain_a_receiving_resource_id(monkeypatch, mutation):
    value, store, resources, calls = controlled_resources(monkeypatch)
    extra = SavedFBAResourceDeclaration('unqualified', canonical({}), (), canonical({}))
    if mutation == 'append': value._declarations += (extra,)
    elif mutation == 'remove': value._declarations = ()
    elif mutation == 'replace': value._declarations = (extra,)
    elif mutation == 'qualification': value._qualified = ()
    else: value._original_ports = ()
    resources['unqualified'] = {}
    with pytest.raises(ValueError, match='^saved_fba_resource_(declarations|reader)_changed$'):
        value.check(store=store, run_id='controlled-run', resources=resources)
    assert calls == ['qualified']


def test_failed_requalification_is_not_replaced_by_stored_immutable_data(monkeypatch):
    value, store, resources, _ = controlled_resources(monkeypatch)
    def changed(*args, **kwargs):
        raise ValueError('actual_publication_no_longer_valid')
    monkeypatch.setattr(SavedFBAResourceDeclaration, 'requalify', changed)
    with pytest.raises(ValueError, match='^actual_publication_no_longer_valid$'):
        value.check(store=store, run_id='controlled-run', resources=resources)
