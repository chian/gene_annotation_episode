"""Constructed native report points, distinct statistics and exact custody."""
from copy import deepcopy
from dataclasses import replace
import json
import pytest
from gene_annotation_episode.communication import validate_closed_schema
from gene_annotation_episode.domain import ContractError,obj,validate_schema
from gene_annotation_episode.literature_context_native_inputs import DATA_VERSION
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_context_native_storage import native_observations_schema
from gene_annotation_episode.literature_context_meanings import REQUIREMENT_FIELDS,ROUTE_FIELDS
from gene_annotation_episode.literature_context_storage import LiteratureContextRepository
from test_literature_context_storage import fixture,source
from test_literature_context_meanings import reopen_read_only


def native_fixture(path,*,mutate=None):
    store,context,args,records=fixture(path,page=True)
    text=('Glucose concentration. Culture A measured glucose 1 mM; SD 0.2 mM; n = 3. '
          'Culture B measured glucose 3 mM; SEM 0.1 mM; n = 4. Supported culture point 1 mM; incompatible culture point 3 mM. '
          'These source observations concern glucose availability in culture; Route glucose uses the glucose requirement.')
    src=source(store,text,parents=[records['root']['id']])
    def w(quote):
        i=text.index(quote)
        return dict(source_ref=src['id'],representation='original',start=len(text[:i].encode()),end=len(text[:i+len(quote)].encode()),quote=quote)
    def num(quote,token):return dict(witness=w(quote),number_start=quote.index(token),number_end=quote.index(token)+len(token))
    def q(quote,token):
        witness=w(quote);i=quote.index('mM')
        unit={**witness,'start':witness['start']+len(quote[:i].encode()),'end':witness['start']+len(quote[:i+2].encode()),'quote':'mM'}
        return dict(number=num(quote,token),unit_witness=unit)
    contexts=[]
    for label,value,count in [('A','1','3'),('B','3','4')]:
        quote=f'Culture {label} measured glucose {value} mM'
        contexts.append(dict(key='private-'+label,identity=w('Culture '+label),setting=w('Culture '+label),setting_kind='growth_condition',sample_unit=None,cluster=None,
            weight='equal_unit',scope_match='matched',observations=[dict(requirement_key='private-glucose',measurement_identity=None,unit='mM',
                value=q(quote,value),value_basis='source_reported_measurement',basis_witness=w(quote),
                reported_sd=q('SD 0.2 mM','0.2') if label=='A' else None,reported_sem=q('SEM 0.1 mM','0.1') if label=='B' else None,
                reported_plusminus=None,reported_count=num('n = '+count,count),count_relation='exact',replicate_kind='technical')]))
    data=dict(version=DATA_VERSION,selection=dict(question_kind='sample_context_coverage',origin='synthetic',scope_status='defined',frame_status='defined',
        pairing='paired',weight_basis='equal_units',sampling_design='unknown',alpha=None,permitted_remainder=True,
        requirements=[dict(key='private-glucose',unit='mM',supported=[q('Supported culture point 1 mM','1')],incompatible=[q('incompatible culture point 3 mM','3')])],
        routes=[dict(key='private-route',requirements=['private-glucose'],requirements_complete=True,joint_support='established')],contexts=contexts),
        meanings=dict(requirements=[dict(key='private-glucose',**dict.fromkeys(REQUIREMENT_FIELDS))],routes=[dict(key='private-route',**dict.fromkeys(ROUTE_FIELDS))]))
    data['meanings']['requirements'][0].update(definition=w('Glucose concentration'),entity=w('glucose'),property=w('concentration'),
        biological_setting=w('in culture'),function_relation=w('glucose availability'))
    data['meanings']['routes'][0].update(definition=w('Route glucose'),membership_evidence=w('Route glucose uses the glucose requirement'))
    if mutate:mutate(data)
    retained=source(store,json.dumps(data),parents=[records['root']['id']]);args['data_source_ref']=retained['id']
    context=replace(context,received_record_refs=(*context.received_record_refs,src['id'],retained['id']))
    return store,context,args,{**records,'native':src,'retained':retained},data


def populated(path):
    store,context,args,records,data=native_fixture(path)
    repo=LiteratureContextRepository(store,context.run_id);outcome=repo.populate(context,args,'selected');view=repo.native_observations()
    rows=view.fact_rows(replace(context,received_record_refs=tuple(outcome['record_refs'])),[outcome['result']['sheet_ref']])
    return store,context,args,records,repo,outcome,view,rows


def test_points_statistics_identities_and_sampling_meanings(tmp_path):
    store,context,args,records,repo,outcome,view,rows=populated(tmp_path)
    with store:
        assert outcome['result']['cells']['selected_point']['value']==.5
        assert [r['lower'] for r in rows]==[1,3] and [r['upper'] for r in rows]==[1,3]
        assert rows[0]['reported_sd']==.2 and rows[0]['reported_sem'] is None
        assert rows[1]['reported_sem']==.1 and rows[1]['reported_sd'] is None
        assert [r['reported_count'] for r in rows]==[3,4] and all(r['replicate_kind']=='technical' for r in rows)
        assert outcome['result']['actual_sampling_n'] is None and outcome['result']['context_units']==2
        assert outcome['result']['cells']['sampling_lower']['value'] is None
        assert rows[0]['context_ref']!=rows[1]['context_ref'] and rows[0]['measurement_ref']!=rows[1]['measurement_ref']
        saved=repo.read(rows[0]['sheet_ref']);assert records['native']['id'] in saved['direct_input_source_refs']
        assert saved['extraction']['native_evidence']['recipe']['version']==DATA_VERSION
        validate_closed_schema(obj({'observations':native_observations_schema()}));validate_schema(rows,native_observations_schema())
        assert not store.list('observation') and not store.list('assessment')


def test_missing_values_and_nominal_setting_not_hidden_by_missing_meaning(tmp_path):
    def mutate(data):
        data['meanings']['requirements'][0].update(dict.fromkeys(REQUIREMENT_FIELDS))
        data['selection']['contexts'][0]['observations'][0]['value_basis']='source_reported_setting'
        data['selection']['contexts'][1]['observations'][0].update(value=None,reported_sem=None,reported_count=None,count_relation='unknown')
    store,context,args,records,data=native_fixture(tmp_path,mutate=mutate)
    with store:
        repo=LiteratureContextRepository(store,context.run_id);out=repo.populate(context,args,'selected')
        rows=repo.native_observations().project_rows([out['result']['sheet_ref']],permitted_record_refs=out['record_refs'])
        assert rows[0]['lower']==1 and rows[0]['value_basis']=='source_reported_setting'
        assert rows[1]['lower'] is None and rows[1]['reported_relation']=='unknown' and rows[1]['reported_count'] is None
        assert out['result']['cells']['coverage_lower']['value']==.5 and out['result']['cells']['coverage_upper']['value']==1


def test_new_numeric_source_is_authorized_before_bytes(tmp_path,monkeypatch):
    store,context,args,records,data=native_fixture(tmp_path)
    with store:
        repo=LiteratureContextRepository(store,context.run_id)
        denied=replace(context,received_record_refs=tuple(r for r in context.received_record_refs if r!=records['native']['id']))
        read=store.get_artifact
        def checked(ref):
            assert ref!=records['native']['artifact_ref'];return read(ref)
        monkeypatch.setattr(store,'get_artifact',checked)
        with pytest.raises(ContractError,match='not_received'):repo.populate(denied,args,'selected')
        assert store.db.execute('select count(*) from literature_context_operations').fetchone()[0]==0


def test_independent_exact_subset_forwarding_and_first_readonly_replay(tmp_path,monkeypatch):
    store,context,args,records,repo,out,view,rows=populated(tmp_path)
    with store:
        parent=replace(context,episode_id='parent',received_record_refs=tuple(out['record_refs']))
        assert view.fact_rows(parent,[rows[0]['sheet_ref']])==[]
        sem=repo.semantic_projection();sem.receive_cells(parent,sem.project_cells([rows[0]['sheet_ref']],permitted_record_refs=out['record_refs'],components=['selected_point']),'aggregate-only')
        assert view.received_rows(parent)==[]
        view.receive_rows(parent,rows[:1],'native-subset');assert view.fact_rows(parent,[rows[0]['sheet_ref']])==rows[:1]
        forged=deepcopy(rows[:1]);forged[0]['value_basis']='conditional_assumption'
        with pytest.raises(ContractError,match='differs_from_saved'):view.receive_rows(parent,forged,'forged')
        with pytest.raises(ContractError,match='not_received'):view.validate_fact_rows(parent,rows)
        forward=replace(parent,episode_id='grandparent');view.receive_rows(forward,view.received_rows(parent),'forward');assert view.received_rows(forward)==rows[:1]
        saved=store.get(rows[0]['sheet_ref']);allowed={saved['artifact_ref'],saved['request_ref']};read=store.get_artifact
        def only_saved(ref):
            assert ref in allowed;return read(ref)
        def forbidden(*a,**kw):raise AssertionError('source/parser/calculator/model during replay')
        monkeypatch.setattr(store,'get_artifact',only_saved)
        monkeypatch.setattr('gene_annotation_episode.literature_context_storage.read_context_inputs',forbidden)
        monkeypatch.setattr('gene_annotation_episode.literature_context_storage.populate_context_compatibility',forbidden)
        reopen_read_only(store);restored=LiteratureContextRepository(store,context.run_id)
        assert restored.populate(context,args,'selected')==out and restored.native_observations().received_rows(parent)==rows[:1]
        assert store.db.total_changes==0


def test_prepared_sheet_cannot_upgrade_to_native_view(tmp_path):
    store,context,args,records=fixture(tmp_path)
    with store:
        repo=LiteratureContextRepository(store,context.run_id);out=repo.populate(context,args,'selected')
        reopen_read_only(store);view=LiteratureContextRepository(store,context.run_id).native_observations()
        assert view.received_rows(context)==[]
        with pytest.raises(ContractError,match='native_observations_unavailable|version_mismatch'):
            view.project_rows([out['result']['sheet_ref']],permitted_record_refs=out['record_refs'])
        assert store.db.total_changes==0


@pytest.mark.parametrize('positions',[[True],[-1],[0,0],['all',0],[{}]])
def test_positions_fail_structurally(tmp_path,positions):
    store,context,args,records,repo,out,view,rows=populated(tmp_path)
    with store:
        with pytest.raises(ContractError,match='positions_invalid'):view.project_rows([],permitted_record_refs=(),positions=positions)


def native_with_observation(path,text,quote,token,unit_quote,*,count=False,spread=False):
    store,context,args,records,data=native_fixture(path)
    extra=source(store,text,parents=[records['root']['id']])
    def witness(q):
        i=text.index(q)
        return dict(source_ref=extra['id'],representation='original',start=len(text[:i].encode()),end=len(text[:i+len(q)].encode()),quote=q)
    selector=dict(witness=witness(quote),number_start=quote.index(token),number_end=quote.index(token)+len(token))
    obs=data['selection']['contexts'][0]['observations'][0]
    if count:obs['reported_count']=selector
    else:obs['reported_sd' if spread else 'value']=dict(number=selector,unit_witness=witness(unit_quote))
    retained=source(store,json.dumps(data),parents=[records['root']['id']]);args['data_source_ref']=retained['id']
    context=replace(context,received_record_refs=(*context.received_record_refs,extra['id'],retained['id']))
    return store,context,args


def test_exact_micro_to_milli_conversion_and_source_token_retention(tmp_path):
    store,context,args=native_with_observation(tmp_path,'Measured glucose 10 µM.','10 µM','10','µM')
    with store:
        repo=LiteratureContextRepository(store,context.run_id);out=repo.populate(context,args,'selected')
        rows=repo.native_observations().project_rows([out['result']['sheet_ref']],permitted_record_refs=out['record_refs'])
        assert rows[0]['lower']==.01 and rows[0]['unit']=='mM'
        trace=repo.read(out['result']['sheet_ref'])['extraction']['native_evidence']['contexts'][0]['observations'][0]['value']
        assert trace['number']['raw_number']=='10' and trace['unit']['raw_unit']=='uM'


@pytest.mark.parametrize('text,quote,token,unit,options,code',[
    ('Measured glucose < 2 mM.','2 mM','2','mM',{},'exact_point_required'),
    ('Measured glucose approximately 2 mM.','2 mM','2','mM',{},'approximate_source_number'),
    ('Measured glucose 12 mM.','12 mM','2','mM',{},'partial_source_numeric_token'),
    ('Measured glucose 2 uM. Reference unit mM.','2 uM','2','mM',{},'explicit_unit_mismatch'),
    ('Glucose turnover 2 mM/min.','2 mM/min','2','mM',{},'partial_context_native_unit'),
    ('Glucose turnover 2 mM/min. Reference mM.','2 mM/min','2','mM.',{},'unsupported_context_native_unit'),
    ('Uncertainty SD 2%. Reference mM.','SD 2%','2','mM',{'spread':True},'relative_spread_unit_unsupported'),
    ('Replicate count n < 3.','n < 3','3','',{'count':True},'plain_source_point_required'),
    ('Replicate count n = 3.5.','n = 3.5','3.5','',{'count':True},'integer_count_required'),
])
def test_native_operands_do_not_lose_censoring_units_or_count_kind(tmp_path,text,quote,token,unit,options,code):
    store,context,args=native_with_observation(tmp_path,text,quote,token,unit,**options)
    with store:
        with pytest.raises(ExperimentalContractError,match=code):LiteratureContextRepository(store,context.run_id).populate(context,args,'selected')
        assert store.db.execute('select count(*) from literature_context_operations').fetchone()[0]==0


def test_same_physical_number_survives_recipe_and_excerpt_changes(tmp_path):
    store,context,args,records,data=native_fixture(tmp_path)
    with store:
        repo=LiteratureContextRepository(store,context.run_id);one=repo.populate(context,args,'first-recipe')
        first=repo.native_observations().project_rows([one['result']['sheet_ref']],permitted_record_refs=one['record_refs'])
        original=data['selection']['contexts'][0]['observations'][0]['value']['number']
        raw=store.get_artifact(records['native']['artifact_ref']).decode();quote=raw[:raw.index('Culture B')]
        extended={**original['witness'],'start':0,'end':len(quote.encode()),'quote':quote}
        original.update(witness=extended,number_start=quote.index('1 mM'),number_end=quote.index('1 mM')+1)
        data['selection']['routes'][0]['key']='second-route';data['meanings']['routes'][0]['key']='second-route'
        data['selection']['requirements'][0]['unit']='uM'
        for ctx in data['selection']['contexts']:
            for obs in ctx['observations']:obs['unit']='uM'
        retained=source(store,json.dumps(data),parents=[records['root']['id']]);second_args={**args,'data_source_ref':retained['id']}
        second_context=replace(context,received_record_refs=(*context.received_record_refs,retained['id']))
        two=repo.populate(second_context,second_args,'second-recipe')
        second=repo.native_observations().project_rows([two['result']['sheet_ref']],permitted_record_refs=two['record_refs'])
        assert first[0]['sheet_ref']!=second[0]['sheet_ref']
        assert first[0]['lower']==1 and first[0]['unit']=='mM' and second[0]['lower']==1000 and second[0]['unit']=='uM'
        assert first[0]['measurement_ref']==second[0]['measurement_ref'] and first[0]['context_ref']==second[0]['context_ref']
        assert store.get(first[0]['measurement_ref'])['anchor']['quote']=='1'
        assert not store.list('observation') and not store.list('assessment')


def test_distinct_source_contexts_can_share_one_reported_setting(tmp_path):
    def mutate(data):
        shared=data['selection']['contexts'][0]['setting']
        data['selection']['contexts'][1]['setting']=deepcopy(shared)
    store,context,args,records,data=native_fixture(tmp_path,mutate=mutate)
    with store:
        repo=LiteratureContextRepository(store,context.run_id);out=repo.populate(context,args,'shared-setting')
        rows=repo.native_observations().project_rows([out['result']['sheet_ref']],permitted_record_refs=out['record_refs'])
        assert rows[0]['context_ref']!=rows[1]['context_ref'] and rows[0]['setting_ref']==rows[1]['setting_ref']
        assert out['result']['context_units']==2


def test_not_extracted_basis_cannot_carry_an_extracted_numeric_value(tmp_path):
    def mutate(data):data['selection']['contexts'][0]['observations'][0]['value_basis']='source_value_not_extracted'
    store,context,args,records,data=native_fixture(tmp_path,mutate=mutate)
    with store:
        with pytest.raises(ExperimentalContractError,match='unextracted_value_present'):
            LiteratureContextRepository(store,context.run_id).populate(context,args,'contradictory-basis')
