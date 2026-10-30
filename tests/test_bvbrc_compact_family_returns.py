"""Compact/full BV-BRC family contracts through real custody and return readers.

Historical family records below are deliberately constructed communication
fixtures. The numerical examples use the existing family fixtures and real
saved-value projections. The separate Workflow case uses actual method_loop
commissions and preparation returns, with scripted choices and no live service.
None of these cases claims native BV-BRC scientific execution.
"""
from copy import deepcopy
from dataclasses import replace
import importlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import form_with_facts, plain
from gene_annotation_episode.composition_information import (
    CONTRACT_INFORMATION_OPERATIONS, CONTRACT_INFORMATION_PROFILE,
)
from gene_annotation_episode.episode_contract_information import expand_fact_form
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.runtime import TypedReportContract, Workflow
from gene_annotation_episode.state import Store
from test_bvbrc_appservice_custody import SavedRecords


FAMILIES = (
    ('alignment', 'BVBRCAlignmentReturns', 'alignment_fact_sources'),
    ('genome_alignment', 'BVBRCGenomeAlignmentReturns', 'genome_alignment_fact_sources'),
    ('homology', 'BVBRCHomologyReturns', 'homology_fact_sources'),
    ('phylogeny', 'BVBRCPhylogenyReturns', 'phylogeny_fact_sources'),
    ('proteome', 'BVBRCProteomeReturns', 'proteome_fact_sources'),
    ('comparative_systems', 'BVBRCComparativeSystemsReturns', 'comparative_systems_fact_sources'),
    ('fastqutils', 'BVBRCFastqUtilsReturns', 'fastqutils_fact_sources'),
)


def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties),
            'additionalProperties': False}


def forbidden(*args, **kwargs):
    raise AssertionError('Saved family return attempted current discovery or new external work')


def frame(selection, role, descriptors):
    """An explicitly authored complete decision schema, not Workflow evidence."""
    fields = {}
    for key, value in selection.items():
        if key == 'kind':
            fields[key] = {'type': 'string', 'const': value}
        elif isinstance(value, dict):
            fields[key] = {'type': 'object'}
        else:
            fields[key] = {'type': 'string'}
    schema = obj({'selection': {'anyOf': [obj(fields)]}, 'report_update': obj({})})
    lookups = [{'properties': {'view': {'const': 'child_options'},
                              'role': {'enum': [None, role]}}},
        *[{'properties': {'operation': {'const': name}}}
          for name in CONTRACT_INFORMATION_OPERATIONS]]
    selected = obj({'response_type': {'type': 'string', 'const': 'select_action'},
                    **schema['properties']})
    facts = {role: deepcopy(descriptors)}
    return {'context': {'tools': [], 'contract_information_profile': CONTRACT_INFORMATION_PROFILE},
        'schema': schema, 'contract_information': {
            'version': CONTRACT_INFORMATION_PROFILE, 'permitted_child_roles': [role],
            'fact_sources_by_role': facts, 'fact_sources_sha256': digest(facts),
            'catalog_sha256': digest([]), 'action_schema_sha256': digest(schema),
            'instructions': 'Constructed communication fixture; no scientific execution.',
            'exchange_schema': {'properties': {'response': {'anyOf': [
                {'properties': {'lookup': {'anyOf': lookups}}}, selected]}}}}}


class FamilyRecords:
    def __init__(self, store, family):
        name, class_name, catalog_name = family
        self.module = importlib.import_module('gene_annotation_episode.bvbrc_' + name + '_returns')
        self.saved = SavedRecords(store)
        self.store = store
        available = getattr(self.module, catalog_name)()
        # This constructed parent is given two finite available fact sources.
        # The actual Workflow case below freezes the full application catalog.
        self.descriptors = {key: available[key] for key in tuple(available)[:2]}
        self.sources = tuple(self.descriptors)
        # No acquired publication means no scientific facts. This fixture is
        # for the full communication path, including valid empty information.
        publications = SimpleNamespace(own_results=lambda _: [],
            api=SimpleNamespace(_own_outcomes=lambda _: ()),
            host=SimpleNamespace(custody=self.saved.custody))
        self.api = SimpleNamespace(store=store, run_id=self.saved.run_id,
            configuration={}, appservice=SimpleNamespace(
                custody=self.saved.custody, publications=publications))
        self.host = getattr(self.module, class_name)(self.api)

    def schema(self, *, field='requested', source=None, compact=False):
        source = self.sources[0] if source is None else source
        node = {'$ref': 'episode-fact:' + source} if compact else self.descriptors[source]['report_schema']
        return obj({field: deepcopy(node)})

    def selected(self, parent, index):
        return json.loads(self.saved.journal.row('runtime_actions', parent.episode_id, index)['action'])

    def decision(self, parent, index, selection, role):
        self.saved.journal.save('runtime_model_calls', {'episode_id': parent.episode_id,
            'call_index': index, 'purpose': 'decision',
            'request': canonical(frame(selection, role, self.descriptors)),
            'response': canonical({'selection': selection, 'report_update': {}})})

    def child(self, parent, *, role='results', compact=True, index=0):
        full = self.schema()
        child = self.saved.child(parent, role, {}, index, schema=full, model=False)
        selected = self.selected(parent, index)
        selected['schema_json'] = canonical(self.schema(compact=compact))
        expanded = expand_fact_form(selected['schema_json'], child_role=role,
            facts_by_role={role: self.descriptors}, permitted_child_roles=[role])
        request = plain(child.request)
        request['message']['report_contract_declaration'] = expanded['declaration']
        child = replace(child, request=request)
        self.store.db.execute('UPDATE runtime_episodes SET request=? WHERE episode_id=?',
            (canonical(request), child.episode_id))
        self.store.db.execute('UPDATE runtime_actions SET action=? WHERE episode_id=? AND decision_index=?',
            (canonical(selected), parent.episode_id, index))
        self.decision(parent, index, selected, role)
        return child

    def save_return(self, parent, child, *, rows=None):
        contract = plain(child.request)['report_contract']
        schema = contract['measurements']['schema']
        facts = (self.host.facts(child, schema) if child.role == 'results'
                 else self.host.received_facts(child, schema)) if rows is None else {self.sources[0]: rows}
        form = form_with_facts({}, schema, facts)
        self.saved.journal.save('runtime_forms', {'episode_id': child.episode_id,
            'facts': canonical(facts), 'form': canonical(form)})
        index = int(child.path[-1][1].removeprefix('child_'))
        self.saved.journal.save('runtime_report_attempts', {'parent_episode_id': parent.episode_id,
            'decision_index': index, 'delivery_ref': 'delivery_' + digest([parent.episode_id, index])[:24],
            'child_episode_id': child.episode_id, 'contract': canonical(contract),
            'form': canonical(form), 'failure': None})
        return form, schema, f'{parent.run_id}:{parent.episode_id}:{index}:typed_form'

    def redelivery(self, parent, child, *, index=1, field='again', compact=True):
        original = self.store.db.execute('SELECT * FROM runtime_report_attempts WHERE run_id=? '
            'AND parent_episode_id=? AND decision_index=0', (parent.run_id, parent.episode_id)).fetchone()
        submitted = self.schema(field=field, compact=compact)
        selected = {'kind': 'redeliver_report', 'delivery_ref': original['delivery_ref'],
            'purpose': 'Read the same original requested family facts', 'schema_json': canonical(submitted)}
        self.decision(parent, index, selected, child.role)
        full = self.schema(field=field)
        facts = json.loads(self.saved.journal.row('runtime_forms', child.episode_id)['facts'])
        form = form_with_facts({}, full, facts)
        contract = TypedReportContract(selected['purpose'], full, lambda *_: True).as_record()
        self.saved.journal.save('runtime_report_attempts', {'parent_episode_id': parent.episode_id,
            'decision_index': index, 'delivery_ref': original['delivery_ref'],
            'child_episode_id': child.episode_id, 'contract': canonical(contract),
            'form': canonical(form), 'failure': None})
        return form, full, f'{parent.run_id}:{parent.episode_id}:{index}:typed_form'


@pytest.fixture(params=FAMILIES, ids=[row[0] for row in FAMILIES])
def family(request, tmp_path, monkeypatch):
    monkeypatch.setattr('socket.socket.connect', forbidden)
    monkeypatch.setattr('socket.create_connection', forbidden)
    monkeypatch.setattr('urllib.request.OpenerDirector.open', forbidden)
    monkeypatch.setattr('subprocess.Popen', forbidden)
    with Store(tmp_path / 'state') as store:
        yield FamilyRecords(store, request.param)


@pytest.mark.parametrize('compact', [True, False], ids=['compact', 'expanded'])
def test_first_family_return_forwarding_and_redelivery_preserve_original_contract(family, compact, monkeypatch):
    f = family
    parent = f.child(f.saved.root, role='scientific_process', compact=compact)
    child = f.child(parent, compact=compact)
    first = f.save_return(parent, child)
    assert f.host.record_admission(parent, *first) == []
    forwarded = f.save_return(f.saved.root, parent)
    assert f.host.record_admission(f.saved.root, *forwarded) == []
    repeated = f.redelivery(f.saved.root, parent)
    before = list(f.store.db.iterdump())
    for name in ('report_sources', 'catalog', 'action_schema', 'freeze_contract_information'):
        monkeypatch.setattr(Workflow, name, forbidden)
    f.store.db.execute('PRAGMA query_only=ON')
    assert f.host.record_admission(f.saved.root, *repeated) == []
    assert f.host.received_facts(f.saved.root, f.schema()) == {f.sources[0]: []}
    assert f.host._attempt(parent, 0)[1:] == first[:2]
    assert f.host._attempt(f.saved.root, 0)[1:] == forwarded[:2]
    assert f.host._attempt(f.saved.root, 1)[1:] == repeated[:2]
    assert list(f.store.db.iterdump()) == before


@pytest.mark.parametrize('change', [
    'scope', 'purpose', 'selection', 'substituted_child', 'expanded_schema',
    'extra_fact', 'frozen_form', 'declaration', 'catalog_digest', 'missing_frame',
])
def test_every_family_rejects_changed_original_authority(family, change):
    f = family
    child = f.child(f.saved.root)
    returned = f.save_return(f.saved.root, child)
    parent_id = f.saved.root.episode_id
    if change in {'scope', 'purpose', 'selection'}:
        selected = f.selected(f.saved.root, 0)
        if change == 'scope': selected['scope'] = {'subject_refs': []}
        elif change == 'purpose': selected['purpose'] = 'Substituted purpose'
        else: selected['schema_json'] = canonical(f.schema(field='other', compact=True))
        f.store.db.execute('UPDATE runtime_actions SET action=? WHERE episode_id=? AND decision_index=0',
                           (canonical(selected), parent_id))
    elif change == 'substituted_child':
        other = f.child(f.saved.root, index=2)
        f.save_return(f.saved.root, other)
        f.store.db.execute('UPDATE runtime_report_attempts SET child_episode_id=? WHERE parent_episode_id=? AND decision_index=0',
                           (other.episode_id, parent_id))
    elif change in {'expanded_schema', 'extra_fact'}:
        request = plain(child.request)
        declared = request['message']['report_contract_declaration']
        forged_catalog = deepcopy(f.descriptors)
        forged_catalog[f.sources[0]]['report_schema']['maxItems'] = 0
        if change == 'extra_fact':
            submitted = json.loads(declared['submitted_schema_json'])
            submitted['properties']['extra'] = {'$ref': 'episode-fact:' + f.sources[1]}
            submitted['required'].append('extra')
            declared['submitted_schema_json'] = canonical(submitted)
        expanded = expand_fact_form(declared['submitted_schema_json'], child_role=child.role,
            facts_by_role={child.role: forged_catalog}, permitted_child_roles=[child.role])
        request['message']['report_contract_declaration'] = expanded['declaration']
        request['report_contract']['measurements']['schema'] = expanded['expanded_schema']
        f.store.db.execute('UPDATE runtime_episodes SET request=? WHERE episode_id=?',
                           (canonical(request), child.episode_id))
    elif change == 'frozen_form':
        f.store.db.execute('UPDATE runtime_forms SET form=? WHERE episode_id=?', ('{}', child.episode_id))
    elif change == 'declaration':
        request = plain(child.request)
        request['message']['report_contract_declaration']['expanded_schema_sha256'] = '0' * 64
        f.store.db.execute('UPDATE runtime_episodes SET request=? WHERE episode_id=?',
                           (canonical(request), child.episode_id))
    elif change == 'missing_frame':
        f.store.db.execute('DELETE FROM runtime_model_calls WHERE episode_id=?', (parent_id,))
    else:
        sent = json.loads(f.saved.journal.row('runtime_model_calls', parent_id, 0)['request'])
        sent['contract_information']['fact_sources_sha256'] = '0' * 64
        f.store.db.execute('UPDATE runtime_model_calls SET request=? WHERE episode_id=? AND call_index=0',
                           (canonical(sent), parent_id))
    with pytest.raises(ValueError):
        f.host.record_admission(f.saved.root, *returned)


@pytest.mark.parametrize('change', ['purpose', 'delivery', 'schema', 'catalog', 'form', 'frozen'])
def test_every_family_redelivery_requires_its_original_request_and_frozen_values(family, change):
    f = family
    child = f.child(f.saved.root)
    f.save_return(f.saved.root, child)
    returned = f.redelivery(f.saved.root, child)
    parent = f.saved.root.episode_id
    row = f.saved.journal.row('runtime_model_calls', parent, 1)
    if change in {'purpose', 'delivery', 'schema'}:
        response = json.loads(row['response'])
        key = {'purpose': 'purpose', 'delivery': 'delivery_ref', 'schema': 'schema_json'}[change]
        response['selection'][key] = canonical(f.schema(field='forged', compact=True)) if change == 'schema' else 'forged'
        f.store.db.execute('UPDATE runtime_model_calls SET response=? WHERE episode_id=? AND call_index=1',
                           (canonical(response), parent))
    elif change == 'catalog':
        sent = json.loads(row['request'])
        sent['contract_information']['fact_sources_sha256'] = '0' * 64
        f.store.db.execute('UPDATE runtime_model_calls SET request=? WHERE episode_id=? AND call_index=1',
                           (canonical(sent), parent))
    elif change == 'form':
        f.store.db.execute('UPDATE runtime_report_attempts SET form=? WHERE parent_episode_id=? AND decision_index=1',
                           ('{}', parent))
    else:
        f.store.db.execute('UPDATE runtime_forms SET facts=? WHERE episode_id=?', ('{}', child.episode_id))
    with pytest.raises(ValueError):
        f.host.record_admission(f.saved.root, *returned)


def numerical_fixture(name):
    """Use the existing explicitly synthetic/native-format fixtures unchanged."""
    fixture = importlib.import_module('test_bvbrc_' + name + '_returns')
    if name == 'homology':
        return fixture.all_facts(fixture.projection())
    if name == 'phylogeny':
        return fixture.all_facts(*fixture.projection())
    if name == 'alignment':
        return fixture.projected(fixture.projection())
    if name in {'genome_alignment', 'proteome'}:
        return fixture.project(fixture.example())
    if name == 'comparative_systems':
        return fixture.projected(fixture.retained.__wrapped__())
    return fixture.projected(fixture.saved_fixture())


def test_nonempty_original_numerical_rows_survive_compact_and_repeated_contract_reads(family, monkeypatch):
    f = family
    name = f.module.__name__.split('bvbrc_', 1)[1].removesuffix('_returns')
    facts = numerical_fixture(name)
    rows = facts[f.sources[0]]
    assert rows, 'The existing numerical fixture must exercise a nonempty family.'
    child = f.child(f.saved.root)
    original = f.save_return(f.saved.root, child, rows=rows)
    repeated = f.redelivery(f.saved.root, child)
    before = list(f.store.db.iterdump())
    for method in ('report_sources', 'catalog', 'action_schema', 'freeze_contract_information'):
        monkeypatch.setattr(Workflow, method, forbidden)
    f.store.db.execute('PRAGMA query_only=ON')
    assert f.host._attempt(f.saved.root, 0)[1:] == original[:2]
    assert f.host._attempt(f.saved.root, 1)[1:] == repeated[:2]
    assert f.host._attempt(f.saved.root, 0)[1]['requested'] == rows
    assert list(f.store.db.iterdump()) == before
    if os.environ.get('BVBRC480_ATTEMPT'):
        path = Path(os.environ['BVBRC480_ATTEMPT']) / ('numerical_' + name + '.json')
        path.write_text(json.dumps({'evidence': 'existing constructed numerical fixture; compact contract custody only',
            'family': name, 'rows': rows}, indent=2, allow_nan=False) + '\n')


@pytest.mark.parametrize('compact', [True, False], ids=['compact', 'expanded'])
def test_all_consumers_accept_actual_workflow_original_contract_and_explicit_redelivery(tmp_path, compact, monkeypatch):
    # These actual Workflow records carry preparation receipt references.
    # Family-specific numerical/semantic fixtures above remain separate evidence.
    from test_bvbrc_appservice_compact_custody import build_run
    case = build_run(tmp_path, compact=compact)
    try:
        api = case.workflow.episode_bindings.for_role('results').api_execution
        custody = api.appservice.custody
        parent = custody.context(case.root.source.episode_id)
        expected = ({'support': [case.reference]}, case.full)
        before = list(case.store.db.iterdump())
        for method in ('report_sources', 'catalog', 'action_schema', 'freeze_contract_information'):
            monkeypatch.setattr(Workflow, method, forbidden)
        case.store.db.execute('PRAGMA query_only=ON')
        for name, class_name, _ in FAMILIES:
            module = importlib.import_module('gene_annotation_episode.bvbrc_' + name + '_returns')
            host = getattr(module, class_name)(api)
            assert host._attempt(parent, 0)[1:] == expected
            assert host._attempt(parent, case.redelivery_index)[1] == {'again': [case.reference]}
        assert list(case.store.db.iterdump()) == before
    finally:
        case.store.close()
