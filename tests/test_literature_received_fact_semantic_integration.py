"""Constructed scientific records through actual own/parent and saved-only paths."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import json
import sqlite3
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_experimental_prompt import _steering, render_literature_experimental_prompt
from gene_annotation_episode.literature_rate_storage import LiteratureRateRepository
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_literature_rate_native_storage import setup_native_store
from test_literature_rate_episode_integration import service_binding
from test_runtime import FixtureController, ScriptedProvider


TEXT = 'enzyme X variant; reaction R; U/mg; pH 7.5. Activity was <0.2 U/mg; product was not identified.'


def constructed_commit(store, source):
    anchor = {'source_ref': source['id'], 'artifact_ref': source['artifact_ref'],
        'start': 0, 'end': len(TEXT.encode()), 'quote': TEXT}
    commit = {name: [] for name in store.reasoning_schema()['required']}
    commit['source_subjects'] = [{'alias': 'enzyme', 'reference_type': 'construct',
        'source_ref': source['id'], 'label': 'enzyme X variant', 'anchor': anchor}]
    commit['terms'] = [{'alias': name, 'source_ref': source['id'], 'label': label,
        'term_type': kind, 'anchor': anchor} for name, label, kind in
        [('unit', 'U/mg', 'unit'), ('reaction', 'reaction R', 'reaction')]]
    commit['contexts'] = [{'alias': 'condition', 'context_type': 'assay_condition', 'name': 'pH 7.5',
        'source_ref': source['id'], 'attributes': [{'name': 'ph', 'value': {
            'type': 'number', 'value': 7.5, 'unit_ref': None}}], 'related_refs': ['@enzyme'], 'anchor': anchor}]
    commit['observations'] = [{'alias': 'activity', 'subject_refs': ['@enzyme'],
        'source_subject_refs': ['@enzyme'], 'kind': 'biochemical_assay', 'source_ref': source['id'],
        'measurements': [{'name': 'activity', 'value': {'type': 'number', 'value': .2,
            'unit_ref': '@unit', 'bound': 'less_than'}}], 'dependencies': ['@condition'], 'anchor': anchor}]
    commit['hypotheses'] = [{'alias': 'claim', 'subject_refs': ['@enzyme'], 'predicate': 'catalyzes',
        'value': {'type': 'term_ref', 'ref': '@reaction'}, 'context_refs': ['@condition']}]
    commit['assessments'] = [{'alias': 'assessment', 'expected_revision': 0,
        'hypothesis_ref': '@claim', 'observation_ref': '@activity', 'relation': 'weakens',
        'applicability': 'direct', 'extent_basis': 'observed_extent',
        'condition_refs': ['@condition'], 'assumption_refs': []}]
    return commit


def test_actual_own_next_parent_next_and_first_readonly_restore_preserve_original_form_and_observations(tmp_path, monkeypatch):
    path=tmp_path/'state';store=Store(path)
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    artifact=store.artifact(TEXT.encode(), 'text/plain')
    source=store.put('source', {'provider':'constructed_received_fact_fixture', 'accession':None,
        'uri':None, 'artifact_ref':artifact, 'text_ref':artifact, 'request_ref':None,
        'version':None, 'retrieved_at':None}, origin='caller')
    commit=constructed_commit(store, source)
    empty={name:[] for name in store.reasoning_schema()['required']}
    form=obj({'chosen_assessments': {'type':'array', 'items': {'type':'string','format':'reference',
        'x-reference-namespace':'assessment'}, 'x-source':'changed_assessment_refs'},
        'chosen_basis': {'type':'array', 'items': {'type':'string','format':'reference'},
        'x-source':'interpretation_basis_refs'}})
    captured={}
    def check_science(inputs, key):
        captured[key]=deepcopy(inputs)
        text=render_literature_experimental_prompt(inputs,'Constructed iterative assignment').split('\n\nSTEERING\n')[1]
        assert 'enzyme X variant' in text and '<0.2' in text and 'weakens' in text
        assert 'pH 7.5' in text and 'product was not identified' in text
        assert text.count(TEXT)==1
        assert 'source_entity_' not in text and 'source_term_' not in text
        assert all(row['record_type'] in {'reference','term','context','observation','hypothesis','assessment'}
            for row in inputs['literature_received_fact_display']['records'].values())
        followup=deepcopy(empty)
        followup['source_subjects']=[{**commit['source_subjects'][0],
            'alias':'additional_selected_source_entity',
            'label':'enzyme X' if key=='own' else 'reaction R'}]
        return {'selection':{'kind':'reason','commit':followup},'report_update':{}}
    provider=ScriptedProvider([
        {'selection':{'kind':'episode_child','role':'literature', 'assignment':{
            'version':'literature_assignment_v1','question_context_refs':[],'source_refs':[source['id']]},
            'goal':'Examine the constructed source claim.', 'scope':store.validate_scope(),
            'purpose':'Return source-linked assessments and the actual interpretation basis.',
            'schema_json':json.dumps(form), 'initial_report_json':'{}'}, 'report_update':{}},
        {'selection':{'kind':'reason','commit':commit},'report_update':{}},
        lambda inputs:check_science(inputs,'own'), lambda inputs:check_science(inputs,'parent')])
    scorer=ScientificFindingProgress(FindingProgressPolicy(1))
    result=asyncio.run(run_workflow(store,ToolRegistry(store),provider=provider,run_dir=tmp_path/'run',
        controller_factory=lambda path,initial:FixtureController(str(path),initial,2),
        project_credit=scorer, initial_known_record_refs=[source['id']],
        episode_binding_factories=(partial(LiteratureEpisodes,rate_population=True,
            reference_parent_sources=[source['id']]),), binding_definitions={'credit':scorer.as_record()}))
    assert len(provider.contexts)==4
    observations=store.db.execute('SELECT * FROM runtime_observations').fetchall()
    assert len(observations)==4
    attempt,=store.db.execute('SELECT * FROM runtime_report_attempts').fetchall()
    admitted=json.loads(attempt['form'])
    assert admitted==captured['parent']['child_reports'][0]
    assert len(admitted['chosen_assessments'])==1
    assert json.loads(attempt['contract'])['measurements']['schema']==form
    records=deepcopy(captured['parent']['literature_received_fact_display']['records'])
    assert records and set(records) <= set(EpisodeReceipts(store,result['run_id']).known(attempt['parent_episode_id']))
    rootrow=store.db.execute('SELECT * FROM runtime_episodes WHERE json_array_length(path)=1').fetchone()
    request=json.loads(rootrow['request'])
    context=BindingContext(result['run_id'],rootrow['episode_id'],'annotation',
        tuple(tuple(part) for part in json.loads(rootrow['path'])),store.validate_scope(),{},request,
        tuple(captured['parent']['literature_received_fact_display']['received_refs']))
    observation_values=[dict(row) for row in observations]
    store.close()
    def forbidden(*args,**kwargs):raise AssertionError('saved-only display acquired, mutated, calculated or modeled')
    reopened=Store.__new__(Store);reopened.path=path.resolve();reopened._savepoint=0
    reopened.db=sqlite3.connect((path/'state.sqlite3').resolve().as_uri()+'?mode=ro',uri=True,isolation_level=None)
    reopened.db.row_factory=sqlite3.Row;reopened.db.execute('PRAGMA query_only=ON')
    reopened.db.create_function('library_scope_record',2,reopened._scope_filter_record)
    for name in ('get_artifact','artifact','put','transaction','commit_reasoning'):
        monkeypatch.setattr(reopened,name,forbidden)
    monkeypatch.setattr('gene_annotation_episode.providers.ModelConnection',forbidden)
    monkeypatch.setattr('gene_annotation_episode.literature_rate_storage.populate_rate_contrast',forbidden)
    try:
        binding=LiteratureEpisodes(WorkflowServices(SimpleNamespace(store=reopened,run_id=result['run_id'])),rate_population=True)
        restored=binding._received_fact_display_context(context)
        assert restored['literature_received_fact_display']['records']==records
        state={**captured['parent'],**restored,'working_state':{}}
        text=_steering(state,())
        assert TEXT in text and 'weakens' in text and 'enzyme X variant' in text
        missing=next(ref for ref,row in records.items() if row['record_type']=='term' and row['label']=='reaction R')
        lesser=binding._received_fact_display_context(replace(context,
            received_record_refs=tuple(ref for ref in context.received_record_refs if ref!=missing)))
        absent=_steering({**state,**lesser},())
        assert 'meaning unavailable in this scoped display' in absent
        assert all(row['id']!=missing for row in lesser['literature_received_fact_display']['records'].values())
        assert reopened.db.total_changes==0
        assert [dict(row) for row in reopened.db.execute('SELECT * FROM runtime_observations')]==observation_values
        assert json.loads(reopened.db.execute('SELECT form FROM runtime_report_attempts').fetchone()[0])==admitted
    finally:reopened.close()


def test_known_private_sheet_does_not_grant_unreceived_scientific_meaning_metadata(tmp_path):
    store,owner,args=setup_native_store(tmp_path)
    try:
        services,binding=service_binding(store,owner)
        repo=services.literature_rate_repository().source_projection()
        outcome=repo.populate_native(owner,args,'private-owned-calculation')
        private_sheet=outcome['result']['sheet_ref']
        # The receiver knows custody for a sheet but has received no native cells.
        receiver=replace(owner,role='annotation',episode_id='other-receiver',path=(('annotation','parent'),),
            assignment={},received_record_refs=(*owner.received_record_refs,private_sheet))
        display=binding._received_fact_display_context(receiver)
        assert display['literature_received_fact_display']['records']=={}
        assert binding._native_rate_display_context(receiver)['literature_rate_source_display']['cells']==[]
        assert store.list('reference') and store.list('term')
    finally:store.close()
