"""One retained primary paper: finite nominal culture witness versus host unknown.

This is scripted engineering validation with original report bytes. The tiny
problem sequence is a fixture, and no target annotation inference is made.
"""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import hashlib
import json

from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.literature_context_inputs import LITERAL_FIELDS
from gene_annotation_episode.literature_context_native_inputs import DATA_VERSION
from gene_annotation_episode.literature_context_storage import LiteratureContextRepository
from gene_annotation_episode.literature_context_meanings import REQUIREMENT_FIELDS,ROUTE_FIELDS
from gene_annotation_episode.state import Store
from test_literature_context_meanings import reopen_read_only

PAPER=Path(__file__).resolve().parents[1]/'research/experimental_scoring_review_2026-10-23/a108_plausibility_sheet_014/ttr_2010_primary.xml'
PAPER_HASH='c4ab72273813f510ea6bcf7b7bd62dd1e4a9738adf8ccc4accc8a1faf89274e5'


def primary_fixture(path,*,host=False):
    raw=PAPER.read_bytes();assert hashlib.sha256(raw).hexdigest()==PAPER_HASH
    text=raw.decode();store=Store(path);store.create_problem(raw_sequence='ATGGCT',molecule='dna')
    art=store.artifact(raw,'application/xml')
    paper=store.put('source',dict(provider='retained_primary_jats',accession='PMC2946174',uri='https://pmc.ncbi.nlm.nih.gov/articles/PMC2946174/',
        artifact_ref=art,text_ref=None,request_ref=None,version=None,retrieved_at=None,parent_source_refs=[]),origin='caller')
    def w(quote):
        i=text.index(quote)
        return dict(source_ref=paper['id'],representation='original',start=len(text[:i].encode()),end=len(text[:i+len(quote)].encode()),quote=quote)
    nominal='40 mM sodium tetrathionate as indicated'
    q=dict(number=dict(witness=w(nominal),number_start=0,number_end=2),unit_witness={**w(nominal),'start':w(nominal)['start']+3,'end':w(nominal)['start']+5,'quote':'mM'})
    caption='anaerobic growth in mucin broth with (+) or without (-) tetrathionate'
    p6_start=text.index('<p id="P6">')
    p6=text[p6_start+len('<p id="P6">'):text.index('</p>',p6_start)]
    obs=dict(requirement_key='nominal-electron-acceptor',measurement_identity=None if host else w(nominal),unit='mM',
        value=None if host else q,value_basis='source_value_not_extracted' if host else 'source_reported_setting',
        basis_witness=w('cecal contents') if host else w(nominal),reported_sd=None,reported_sem=None,reported_plusminus=None,
        reported_count=None,count_relation='unknown',replicate_kind='unknown')
    context=dict(key='cecal' if host else 'anaerobic-mucin',identity=w('cecal contents' if host else caption),
        setting=w('cecal contents' if host else 'mucin broth'),setting_kind='sample' if host else 'growth_condition',sample_unit=None,
        cluster=None,weight=None,scope_match='unresolved' if host else 'matched',observations=[obs])
    data=dict(version=DATA_VERSION,selection=dict(question_kind='organism_capability',origin='reported',scope_status='defined',frame_status='unreported',
        pairing='unknown' if host else 'paired',weight_basis='equal_units',sampling_design='unknown',alpha=None,permitted_remainder=True,
        requirements=[dict(key='nominal-electron-acceptor',unit='mM',supported=[q],incompatible=[])],
        routes=[dict(key='conditional-tetrathionate-growth',requirements=['nominal-electron-acceptor'],requirements_complete=True,joint_support='established')],
        contexts=[context]),meanings=dict(requirements=[dict(key='nominal-electron-acceptor',**dict.fromkeys(REQUIREMENT_FIELDS))],
        routes=[dict(key='conditional-tetrathionate-growth',**dict.fromkeys(ROUTE_FIELDS))]))
    data['meanings']['requirements'][0].update(definition=w(nominal),entity=w('sodium tetrathionate'),property=w('concentration'),
        biological_setting=w('mucin broth'),function_relation=w('tetrathionate respiration might provide a benefit'))
    data['meanings']['routes'][0].update(definition=w('tetrathionate respiration'),biological_setting=w(caption),function_relation=w('tetrathionate respiration might provide a benefit'),
        membership_evidence=w('mucin broth resulted in enrichment for the wild type only in the presence of tetrathionate'),joint_scope_evidence=w(caption))
    recipe_art=store.artifact(json.dumps(data),'application/json')
    recipe=store.put('source',dict(provider='retained_source_selectors',accession=None,uri=None,artifact_ref=recipe_art,text_ref=None,request_ref=None,
        version=DATA_VERSION,retrieved_at=None,parent_source_refs=[paper['id']]),origin='caller')
    literals=dict.fromkeys(LITERAL_FIELDS)
    for field,quote in dict(organism='Typhimurium',experiment=caption,function='tetrathionate respiration',
            biological_context='cecal contents' if host else 'mucin broth',endpoint='outgrowth',condition='anaerobic growth').items():literals[field]=w(quote)
    args=dict(source_ref=paper['id'],data_source_ref=recipe['id'],source_kind='primary_source',literals=literals,
        interpretation_witnesses=[w(p6),w(caption),w(nominal)])
    binding=BindingContext('primary-126','primary-literature','literature',(('literature','primary'),),store.validate_scope(),
        {'page':{'source_ref':paper['id']}},{},(paper['id'],recipe['id']))
    return store,binding,args,dict(root=paper,recipe=recipe),data


def test_retained_primary_nominal_condition_is_a_conditional_witness(tmp_path,monkeypatch):
    store,context,args,sources,data=primary_fixture(tmp_path)
    with store:
        repo=LiteratureContextRepository(store,context.run_id);out=repo.populate(context,args,'nominal-culture')
        sheet=repo.read(out['result']['sheet_ref']);cells=out['result']['cells']
        assert len(cells)==15 and cells['selected_point']['value']==1 and cells['capability_point']['value']==1
        assert cells['coverage_point']['value'] is None and cells['coverage_lower']['value']==0 and cells['coverage_upper']['value']==1
        assert cells['sampling_lower']['value'] is None and out['result']['actual_sampling_n'] is None
        row,=repo.native_observations().project_rows([out['result']['sheet_ref']],permitted_record_refs=out['record_refs'])
        assert row['lower']==row['upper']==40 and row['unit']=='mM' and row['value_basis']=='source_reported_setting'
        assert row['reported_count'] is None and row['reported_sd'] is None and row['reported_sem'] is None
        assert row['sample_unit_ref'] is None and row['cluster_ref'] is None and row['context_kind']=='growth_condition'
        assert sheet['sheet']['inputs']['requirements'][0]['supported']==[dict(lower=40,upper=40,lower_closed=True,upper_closed=True)]
        trace=sheet['extraction']['native_evidence']['contexts'][0]['observations'][0]['value']['number']
        assert trace['raw_number']=='40' and trace['selector']['witness']['quote']=='40 mM sodium tetrathionate as indicated'
        assert set(sheet['direct_input_source_refs'])=={sources['root']['id'],sources['recipe']['id']}
        parent=replace(context,episode_id='parent',received_record_refs=tuple(out['record_refs']))
        repo.native_observations().receive_rows(parent,[row],'requested-primary-native')
        saved=store.get(out['result']['sheet_ref']);allowed={saved['artifact_ref'],saved['request_ref']};read=store.get_artifact
        def saved_only(ref):assert ref in allowed;return read(ref)
        def forbidden(*a,**kw):raise AssertionError('original paper or calculator used during reconstruction')
        reopen_read_only(store);monkeypatch.setattr(store,'get_artifact',saved_only)
        monkeypatch.setattr('gene_annotation_episode.literature_context_storage.read_context_inputs',forbidden)
        monkeypatch.setattr('gene_annotation_episode.literature_context_storage.populate_context_compatibility',forbidden)
        restored=LiteratureContextRepository(store,context.run_id)
        assert restored.populate(context,args,'nominal-culture')==out and restored.native_observations().received_rows(parent)==[row]
        assert store.db.total_changes==0


def test_retained_primary_does_not_make_nominal_culture_a_host_exposure(tmp_path):
    store,context,args,sources,data=primary_fixture(tmp_path,host=True)
    with store:
        repo=LiteratureContextRepository(store,context.run_id);out=repo.populate(context,args,'host-mapping')
        assert out['result']['cells']['selected_point']['value'] is None
        assert out['result']['cells']['selected_lower']['value']==0 and out['result']['cells']['selected_upper']['value']==1
        row,=repo.native_observations().project_rows([out['result']['sheet_ref']],permitted_record_refs=out['record_refs'])
        assert row['lower'] is None and row['reported_relation']=='not_extracted' and row['value_basis']=='source_value_not_extracted'
        assert row['context_kind']=='sample' and row['scope_match']=='unresolved'
        assert not store.list('observation') and not store.list('assessment')
