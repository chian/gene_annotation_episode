"""Constructed native operands, scientific bindings and historical replay."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import ContractError, canonical, obj
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_experimental_prompt import _steering, render_literature_experimental_prompt
from gene_annotation_episode.literature_partner_storage import LiteraturePartnerRepository, partner_cells_schema
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_literature_experimental_prompt_delivery import snapshot
from test_literature_partner_native_storage import fixture, source, witness
from test_runtime import FixtureController, ScriptedProvider


BASE = Path(__file__).resolve().parents[1] / 'verification/literature_reference_evidence_2026-10-25_001/partner_subject_binding_repair_121'


def rows_for(store, context, args, key='new'):
    repo = LiteraturePartnerRepository(store, context.run_id)
    outcome = repo.populate(context, args, key)
    rows = repo.project_cells([outcome['result']['sheet_ref']], permitted_record_refs=outcome['record_refs'])
    return repo, outcome, rows


def label(store, reference):
    return store.get(reference)['label'] if reference is not None else None


@pytest.mark.parametrize('field,mislabel,expected', [
    ('subject', 'PartnerP', 'SubjectS'), ('partner', 'SubjectS', 'PartnerP'),
    ('endpoint', 'PLP assay', 'product formation'), ('normalization', 'product formation', 'per mg SubjectS'),
])
def test_global_scope_literal_cannot_relabel_numeric_operand(field, mislabel, expected, tmp_path):
    store, context, args, records = fixture(tmp_path)
    with store:
        raw = store.get_artifact(records['data']['artifact_ref'])
        args['literals'][field] = witness(records['data'], raw, mislabel)
        repo, outcome, rows = rows_for(store, context, args)
        assert [row['value'] for row in rows] == [100, 20, 90, 80, .8, 70, .875, .7]
        assert {label(store, row[field + '_ref']) for row in rows} == {expected}
        actual = outcome['result']['assay_interpretation']
        assert actual[field]['value'] == expected
        assert actual['selected_scope_' + field]['value'] == mislabel
        saved = repo.read(outcome['result']['sheet_ref'])
        assert saved['extraction']['literals'][field]['value'] == mislabel
        assert saved['native_operand_bindings']['version'] == 'partner_native_operand_bindings_v1'
        assert not store.list('observation') and not store.list('assessment')


@pytest.mark.parametrize('field,other', [
    ('subject', 'PartnerP'), ('partner', 'SubjectS'),
    ('endpoint', 'PLP assay'), ('normalization', 'product formation'),
])
def test_distinct_operand_meanings_keep_each_raw_arm_and_unknown_shared_binding(tmp_path, field, other):
    store, context, args, records = fixture(tmp_path)
    with store:
        raw = store.get_artifact(records['data']['artifact_ref'])
        args['arms']['omitted'][field] = witness(records['data'], raw, other)
        _, outcome, rows = rows_for(store, context, args)
        assert rows[0]['value'] == 100 and rows[1]['value'] == 20
        assert label(store, rows[1][field + '_ref']) == other
        assert rows[3][field + '_ref'] is None
        assert rows[3]['unavailable_reason'] == field + '_mismatch'
        assert outcome['result']['assay_interpretation']['omitted_' + field]['value'] == other
        state = snapshot()
        state['child_reports'] = [{'selected': rows[:2]}]
        state['literature_received_fact_display'] = {'records': {
            r['id']: r for kind in ('reference', 'term', 'context') for r in store.list(kind)}}
        text = _steering(state, ())
        assert 'Partner operand meaning groups' in text
        assert 'not independent experiments' in text
        assert text.count('Received experimental partner bindings') == 2


def test_selected_scope_alias_does_not_become_a_new_identity_gate(tmp_path):
    store, context, args, records = fixture(tmp_path)
    with store:
        raw = b'SubjectS is also called AliasS in this constructed record.'
        alias = source(store, raw, parents=[records['root']['id']])
        args['literals']['subject'] = witness(alias, raw, 'AliasS')
        context = replace(context, received_record_refs=(*context.received_record_refs, alias['id']))
        _, outcome, rows = rows_for(store, context, args)
        assert rows[4]['value'] == .8 and label(store, rows[4]['subject_ref']) == 'SubjectS'
        assert outcome['result']['assay_interpretation']['selected_scope_subject']['value'] == 'AliasS'


def test_condition_context_uses_native_factors_and_preserves_unknown_identity(tmp_path):
    store, context, args, records = fixture(tmp_path)
    with store:
        raw = store.get_artifact(records['data']['artifact_ref'])
        args['literals']['reference_condition'] = witness(records['data'], raw, 'ammonium_sulfate')
        for arm in args['arms'].values():
            arm['normalization'] = None
        _, outcome, rows = rows_for(store, context, args)
        assert rows[0]['normalization_ref'] is None
        assert rows[4]['unavailable_reason'] == 'normalization_unreported'
        group = store.get(rows[0]['reference_condition_ref'])
        factors = [store.get(ref) for ref in group['related_refs'] if store.get(ref)['record_type'] == 'context']
        nitrogen = next(row for row in factors if row['name'] == 'condition factor nitrogen_source level')
        assert label(store, nitrogen['attributes'][0]['value']['ref']) == 'glutamine'
        temperature = next(row for row in factors if row['name'] == 'condition factor temperature level')
        assert temperature['attributes'][0]['value']['value'] == 37
        assert label(store, temperature['attributes'][0]['value']['unit_ref']) == 'degC'
        assert 'glutamine' in outcome['result']['assay_interpretation']['reference_condition']['value']
        assert outcome['result']['assay_interpretation']['selected_scope_reference_condition']['value'] == 'ammonium_sulfate'


def test_missing_arms_do_not_borrow_global_subject_or_conditions(tmp_path):
    store, context, args, _ = fixture(tmp_path, mode='all_missing')
    with store:
        _, outcome, rows = rows_for(store, context, args)
        assert all(row['subject_ref'] is None and row['reference_condition_ref'] is None for row in rows)
        assert outcome['result']['assay_interpretation']['subject'] is None
        assert outcome['result']['assay_interpretation']['selected_scope_subject']['value'] == 'SubjectS'


@pytest.mark.parametrize('missing', [False, True])
def test_valid_two_arm_contrast_keeps_its_subject_when_third_arm_cannot_share_it(tmp_path, missing):
    store, context, args, records = fixture(tmp_path)
    with store:
        raw = store.get_artifact(records['data']['artifact_ref'])
        if missing:
            args['arms']['addback'] = None
        else:
            args['arms']['addback']['subject'] = witness(records['data'], raw, 'PartnerP')
        _, outcome, rows = rows_for(store, context, args)
        assert rows[4]['value'] == .8 and label(store, rows[4]['subject_ref']) == 'SubjectS'
        assert rows[5]['value'] is None and rows[5]['subject_ref'] is None
        assert rows[5]['unavailable_reason'] == ('arm_unreported' if missing else 'subject_mismatch')
        assert label(store, rows[2]['subject_ref']) == (None if missing else 'PartnerP')
        assert outcome['result']['assay_interpretation']['subject'] is None if not missing else True


def test_markerless_historical_selection_replays_exactly_without_rebinding(tmp_path, monkeypatch):
    # A .before source needs an explicit source loader.
    from importlib.machinery import SourceFileLoader
    loader = SourceFileLoader('gene_annotation_episode._partner_storage_before121', str(BASE/'literature_partner_storage.py.before'))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec);loader.exec_module(module)
    assert module.partner_cells_schema() == partner_cells_schema()
    store, context, args, records = fixture(tmp_path)
    with store:
        raw = store.get_artifact(records['data']['artifact_ref'])
        args['literals']['subject'] = witness(records['data'], raw, 'PartnerP')
        historical_repo = module.LiteraturePartnerRepository(store, context.run_id)
        old = historical_repo.populate(context, args, 'historical')
        old_saved = historical_repo.read(old['result']['sheet_ref'])
        old_rows = historical_repo.project_cells([old['result']['sheet_ref']], permitted_record_refs=old['record_refs'])
        repo = LiteraturePartnerRepository(store, context.run_id)
        assert 'native_operand_bindings' not in old_saved
        assert repo.populate(context, args, 'historical') == old
        assert repo.read(old['result']['sheet_ref']) == old_saved
        assert repo.project_cells([old['result']['sheet_ref']], permitted_record_refs=old['record_refs']) == old_rows
        new = repo.populate(context, args, 'fresh')
        new_rows = repo.project_cells([new['result']['sheet_ref']], permitted_record_refs=new['record_refs'])
        assert label(store, old_rows[0]['subject_ref']) == 'PartnerP'
        assert label(store, new_rows[0]['subject_ref']) == 'SubjectS'
        def forbidden(*a, **kw):raise AssertionError('historical replay reread or recalculated')
        monkeypatch.setattr('gene_annotation_episode.literature_partner_storage.read_partner_inputs', forbidden)
        assert repo.populate(context, args, 'historical') == old


@pytest.mark.parametrize('change', ['subject', 'condition', 'version'])
def test_saved_operand_projection_is_validated_beyond_repeated_metadata_hash(tmp_path, monkeypatch, change):
    store, context, args, _ = fixture(tmp_path)
    with store:
        repo, outcome, rows = rows_for(store, context, args)
        reference = outcome['result']['sheet_ref'];saved = repo.read(reference)
        if change == 'subject':
            saved['native_operand_bindings']['component_bindings']['partner_loss']['subject_ref'] = rows[0]['partner_ref']
        elif change == 'condition':
            saved['native_operand_bindings']['condition_refs']['reference_condition_ref'] = rows[0]['omitted_condition_ref']
        else:
            saved['native_operand_bindings']['version'] = 'unknown_generation'
        encoded = canonical(saved).encode();artifact = store.get(reference)['artifact_ref']
        get, get_artifact = store.get, store.get_artifact
        monkeypatch.setattr(store, 'get_artifact', lambda ref: encoded if ref == artifact else get_artifact(ref))
        monkeypatch.setattr(store, 'get', lambda ref: {**get(ref), 'sha256': hashlib.sha256(encoded).hexdigest()}
            if ref == artifact else get(ref))
        with pytest.raises(ContractError, match='sheet_source_mismatch'):
            repo.read(reference)


def test_actual_typed_subset_next_decisions_and_first_readonly_reconstruction(tmp_path, monkeypatch):
    path = tmp_path/'state';store, template, args, records = fixture(path)
    raw = store.get_artifact(records['data']['artifact_ref'])
    args['literals']['subject'] = witness(records['data'], raw, 'PartnerP')
    assignment = {**plain(template.assignment), 'version':'literature_assignment_v1',
        'question_context_refs':[], 'source_refs':list(template.received_record_refs),
        'requested_partner_components':['partner_loss_fraction']}
    assignment.pop('page', None)
    form = obj({'only_requested':partner_cells_schema()});captured = {}
    def reason():
        selected = witness(records['data'], raw, 'SubjectS');selected.pop('representation')
        selected['artifact_ref'] = records['data']['artifact_ref']
        commit = {name:[] for name in store.reasoning_schema()['required']}
        commit['source_subjects'] = [{'alias':'examined', 'reference_type':'assay',
            'source_ref':records['data']['id'], 'label':'SubjectS', 'anchor':selected}]
        return {'selection':{'kind':'reason','commit':commit}, 'report_update':{}}
    def own(inputs):
        captured['own'] = deepcopy(inputs)
        result = inputs['last_local_outcome']['result']['assay_interpretation']
        assert result['subject']['value'] == 'SubjectS'
        assert result['selected_scope_subject']['value'] == 'PartnerP'
        return reason()
    def parent(inputs):
        captured['parent'] = deepcopy(inputs)
        rows = inputs['child_reports'][0]['only_requested']
        assert len(rows) == 1 and rows[0]['component'] == 'partner_loss_fraction'
        assert rows[0]['value'] == .8 and label(store, rows[0]['subject_ref']) == 'SubjectS'
        text = render_literature_experimental_prompt(inputs, 'Constructed scientific assignment').split('\n\nSTEERING\n')[1]
        assert 'SubjectS' in text and 'glutamine' in text
        assert '0.1 nmol' not in text and '0.02 nmol' not in text
        return reason()
    provider = ScriptedProvider([
        {'selection':{'kind':'episode_child','role':'literature','assignment':assignment,
            'goal':'Examine constructed partner operands','scope':plain(template.scope),
            'purpose':'Return only source-bound requested partner loss',
            'schema_json':json.dumps(form),'initial_report_json':'{}'}, 'report_update':{}},
        {'selection':{'kind':'tool','tool':'literature.partner.source.populate','arguments':args}, 'report_update':{}}, own, parent])
    scorer = ScientificFindingProgress(FindingProgressPolicy(1))
    with store:
        result = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider, run_dir=tmp_path/'run',
            controller_factory=lambda path, initial:FixtureController(str(path), initial, 2),
            project_credit=scorer, initial_known_record_refs=list(template.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes,rate_population=True,
                reference_parent_sources=[args['source_ref']]),), binding_definitions={'credit':scorer.as_record()}))
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 4
        assert store.db.execute('SELECT count(*) FROM literature_partner_operations').fetchone()[0] == 1
        attempt, = store.db.execute('SELECT * FROM runtime_report_attempts').fetchall()
        admitted = json.loads(attempt['form'])['only_requested']
        root = store.db.execute('SELECT * FROM runtime_episodes WHERE json_array_length(path)=1').fetchone()
        request = json.loads(root['request'])
        receiver = BindingContext(result['run_id'], root['episode_id'], 'annotation',
            tuple(tuple(p) for p in json.loads(root['path'])), plain(template.scope), {}, request,
            tuple(EpisodeReceipts(store, result['run_id']).known(root['episode_id'])))
        observations = [dict(row) for row in store.db.execute('SELECT * FROM runtime_observations')]
    reopened = Store.__new__(Store);reopened.path=path.resolve();reopened._savepoint=0
    reopened.db=sqlite3.connect((path/'state.sqlite3').resolve().as_uri()+'?mode=ro',uri=True,isolation_level=None)
    reopened.db.row_factory=sqlite3.Row;reopened.db.execute('PRAGMA query_only=ON')
    reopened.db.create_function('library_scope_record',2,reopened._scope_filter_record)
    def forbidden(*a, **kw):raise AssertionError('read-only reconstruction acquired or mutated source data')
    get_artifact = reopened.get_artifact
    original_artifacts = {row['artifact_ref'] for row in records.values()}
    monkeypatch.setattr(reopened, 'get_artifact', lambda ref: forbidden() if ref in original_artifacts else get_artifact(ref))
    for name in ('put','artifact','transaction','commit_reasoning'):
        monkeypatch.setattr(reopened,name,forbidden)
    monkeypatch.setattr('gene_annotation_episode.literature_partner_storage.read_partner_inputs',forbidden)
    monkeypatch.setattr('gene_annotation_episode.providers.ModelConnection',forbidden)
    try:
        repo=LiteraturePartnerRepository(reopened,result['run_id'])
        assert repo.received_cells(receiver)==admitted
        assert repo.fact_cells(receiver,[admitted[0]['sheet_ref']],components=['reference_rate'])==[]
        assert repo.fact_cells(receiver,[admitted[0]['sheet_ref']],components=['partner_loss_fraction'])==admitted
        assert label(reopened,admitted[0]['subject_ref'])=='SubjectS'
        assert reopened.db.total_changes==0
        assert [dict(row) for row in reopened.db.execute('SELECT * FROM runtime_observations')]==observations
    finally:reopened.close()
