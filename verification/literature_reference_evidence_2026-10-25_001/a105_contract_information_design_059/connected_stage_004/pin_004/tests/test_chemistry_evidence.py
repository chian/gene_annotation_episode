"""Native-source replays and labelled synthetic fixtures; no model/network tests."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import threading

import pytest

from gene_annotation_episode.acquisition import AcquisitionError, PublicClients, SourceSnapshot
from gene_annotation_episode.chemistry import chemical_row, rhea_equation, rhea_response, rhea_row
from gene_annotation_episode.credit import project_credit
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry

CALIBRATION = Path(__file__).parents[1] / 'validation/calibration'


def entity(name):
    return (CALIBRATION / (name+'.entity')).read_bytes()


class SavedChemistry:
    """Saved public bytes, not a live search or invented scientific observation."""
    def __init__(self):
        self.calls=[]
        self.thread_ids=[]
        self.rhea=entity('rhea-stoichiometry')
        self.chebi=entity('chebi-compound')
        self.search=entity('chebi-search-term')

    def snapshot(self, service, request, body):
        self.calls.append((service, request))
        self.thread_ids.append(threading.get_ident())
        return SourceSnapshot(service, 'https://example.invalid/explicit-saved-source-replay', request,
            '2026-10-20T04:00:00+00:00', body, 'application/json',
            {'representation':'explicit_saved_public_interface_calibration_no_network'})

    def rhea_search(self, query, limit=10):
        return self.snapshot('rhea', {'query':query,'limit':limit,'format':'json'}, self.rhea)

    def rhea_reaction(self, accession):
        return self.snapshot('rhea', {'query':accession,'limit':1,'format':'json'}, self.rhea)

    def chebi_compound(self, accession):
        return self.snapshot('chebi', {'accession':accession}, self.chebi)

    def chebi_search(self, term, size=10, page=1):
        return self.snapshot('chebi', {'term':term,'size':size,'page':page}, self.search)


def test_native_rhea_stoichiometry_preserves_sides_and_non_chebi_identity():
    parsed=rhea_row(rhea_response(entity('rhea-stoichiometry'))['results'][0])
    assert parsed['accession']=='RHEA:11740'
    assert parsed['source_direction']=='undefined' and parsed['source_arrow']=='='
    assert parsed['participants'][0]['source_name']=='glutathione'
    assert parsed['participants'][0]['coefficient_expression']=='2'
    assert parsed['participants'][0]['coefficient_basis']=='source_explicit'
    assert parsed['participants'][1]['source_name']=='NADP+'
    caffeine=rhea_row(rhea_response(entity('rhea-json-first'))['results'][0])
    assert any(p['source_accession'].startswith('rhea-comp:') for p in caffeine['participants'])
    assert {p['side'] for p in caffeine['participants']}=={'left','right'}
    assert all(p['coefficient_expression']=='1' for p in caffeine['participants'])


@pytest.mark.parametrize('arrow,direction',[('=','undefined'),('=>','left_to_right'),('<=','right_to_left'),('<=>','bidirectional')])
def test_synthetic_equation_direction_and_symbolic_coefficient_are_not_physiology(arrow,direction):
    # Synthetic markup exercises the notation parser, not a claim that the
    # current JSON search exposes directional-quartet entries.
    html=('<span class="participant"><span class="stoichiometry">n+1</span>'
          '<a data-molid="rhea-comp:7">a carrier+</a><span class="location">(out)</span></span>'
          ' '+arrow.replace('<','&lt;').replace('>','&gt;')+' '
          '<span class="participant"><span class="stoichiometry"> </span>'
          '<a data-molid="chebi:15377">H<sub>2</sub>O</a></span>')
    actual_arrow,actual_direction,parts=rhea_equation(html)
    assert (actual_arrow,actual_direction)==(arrow,direction)
    assert parts[0]['coefficient_expression']=='n+1' and parts[0]['source_name']=='a carrier+'
    assert parts[0]['source_location']=='(out)' and parts[0]['side']=='left'
    assert parts[1]['source_name']=='H2O' and parts[1]['side']=='right'
    assert parts[1]['coefficient_basis']=='implicit_unit_rhea_notation'


def test_actual_native_chemical_data_and_search_have_distinct_completeness():
    detail=chemical_row(json.loads(entity('chebi-compound')),search=False)
    summary=chemical_row(json.loads(entity('chebi-search-term'))['results'][0],search=True)
    assert detail['accession']==summary['accession']=='CHEBI:27732'
    assert detail['formula']==summary['formula']=='C8H10N4O2' and detail['charge']==0
    assert detail['mass']=='194.194' and detail['monoisotopic_mass']=='194.08038'
    assert detail['smiles']=='Cn1c(=O)c2c(ncn2C)n(C)c1=O'
    assert detail['inchikey']=='RYYVLZVUVIJVGH-UHFFFAOYSA-N'
    assert detail['ontology_relations'] and summary['ontology_relations']==[]
    assert detail['representation']=='compound_detail' and summary['representation']=='search_summary'
    assert 'CHEBI:22982' in detail['secondary_accessions']


def test_tools_publish_reusable_source_records_bounded_views_and_durable_replay(tmp_path,monkeypatch):
    path=tmp_path/'store'
    with Store(path) as store:
        problem=store.create_problem(raw_sequence='MKWAA',molecule='protein')
        clients=SavedChemistry();tools=ToolRegistry(store,clients=clients)
        original_thread=threading.get_ident()
        actual_put=store.put
        def own_thread(*args,**kwargs):
            assert threading.get_ident()==original_thread
            return actual_put(*args,**kwargs)
        monkeypatch.setattr(store,'put',own_thread)
        args={'query':'glutathione disulfide','limit':2}
        rhea=tools.execute('public.rhea.search',args,operation_key='saved-reaction')
        assert rhea['status']=='completed',rhea
        assert clients.thread_ids and all(t!=original_thread for t in clients.thread_ids)
        assert tools.execute('public.rhea.search',args,operation_key='saved-reaction')==rhea
        assert len(clients.calls)==1
        record=rhea['result']['records'][0]
        reference=store.get(record['reference_ref'])
        details=store.get(record['native_record_ref'])
        assert reference['native_record_ref']==details['id']
        assert reference['accession']==details['accession']=='RHEA:11740'
        assert details['participants'][0]['coefficient_expression']=='2'
        assert all(store.get(p['chemical_ref'])['source_ref']==details['source_ref'] for p in details['participants'])
        assert store.get_artifact(store.get(details['source_ref'])['artifact_ref'])==clients.rhea
        assert all(store.coverage(p['chemical_ref'])==[] for p in details['participants'])
        viewed=store.reasoning_view()
        assert 'reaction_records' not in viewed and 'participants' not in reference
        complete=tools.execute('state.query',{'refs':[details['id']]})
        assert complete['result']['records']==[details]
        assert tools.execute('state.query',rhea['result']['details_query'])['result']['total']==2
        compound=tools.execute('public.chebi.compound',{'accession':'CHEBI:22982'},operation_key='saved-compound')
        assert compound['status']=='completed'
        assert compound['result']['requested_accession']=='CHEBI:22982'
        assert compound['result']['returned_accessions']==['CHEBI:27732']
        assert compound['result']['exact_accession_match'] is False
        chemical=store.get(compound['result']['records'][0]['native_record_ref'])
        assert chemical['representation']=='compound_detail' and chemical['ontology_relations']
        search=tools.execute('public.chebi.search',{'term':'caffeine','size':2,'page':1})
        assert search['result']['native_total']==18
        assert search['result']['next_query']=={'term':'caffeine','size':2,'page':2}
        assert not store.list('observation') and not store.current_annotations()
        assert project_credit(store).credit==0 and store.problem()==problem
        frozen=deepcopy(rhea)
    with Store(path) as reopened:
        clients=SavedChemistry();again=ToolRegistry(reopened,clients=clients).execute('public.rhea.search',args,operation_key='saved-reaction')
        assert again==frozen and clients.calls==[]
        assert reopened.get(details['id'])==details


def test_bad_row_does_not_hide_later_valid_reaction_and_status_is_not_a_gate(tmp_path):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='MKWAA',molecule='protein')
        clients=SavedChemistry()
        original=json.loads(clients.rhea)
        first=deepcopy(original['results'][0]); first['status']='preliminary_source_status_fixture'
        clients.rhea=json.dumps({'count':3,'results':[first,{'id':'999','equation':'unparsed native row'},original['results'][1]]}).encode()
        result=ToolRegistry(store,clients=clients).execute('public.rhea.search',{'query':'fixture'})
        assert result['status']=='partial'
        assert result['result']['projected_record_count']==2 and result['result']['provider_returned_row_count']==3
        assert result['feedback']['rows'][0]=={'row_index':1,'code':'rhea_equation_markup_unavailable'}
        assert [store.get(r['native_record_ref'])['accession'] for r in result['result']['records']]==['RHEA:11740','RHEA:24424']
        assert store.get(result['result']['records'][0]['native_record_ref'])['source_status']=='preliminary_source_status_fixture'
        assert project_credit(store).credit==0


def test_no_json_match_for_directional_lookup_is_not_identifier_or_biological_absence(tmp_path):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='MKWAA',molecule='protein')
        clients=SavedChemistry();clients.rhea=entity('rhea-direction-variant')
        result=ToolRegistry(store,clients=clients).execute('public.rhea.reaction',{'accession':'RHEA:47149'})
        assert result['status']=='completed'
        assert result['result']['lookup_outcome']=='no_search_match'
        assert result['result']['requested_accession']=='RHEA:47149' and result['result']['returned_accessions']==[]
        assert result['result']['direction_scope']=='json_search_master_records_directional_variants_not_resolved'
        assert not store.list('reaction_record') and not store.list('observation')


def test_client_requests_use_current_term_parameter_and_selected_identifiers(monkeypatch):
    client=PublicClients(timeout=17)
    seen=[]
    def skill(skill,filename,payload,**kwargs):
        seen.append((skill,filename,payload,kwargs))
        return {'ok':True},b'{}',{'fixture':True}
    monkeypatch.setattr(client,'_skill',skill)
    snapshot=client.chebi_search('caffeine',size=2,page=3)
    assert snapshot.request=={'term':'caffeine','size':2,'page':3}
    assert seen[-1][2]['params']==snapshot.request and 'query' not in snapshot.request
    assert seen[-1][2]['timeout_sec']==17 and seen[-1][0]=='chebi-skill'
    assert client.chebi_compound('22982').request=={'accession':'CHEBI:22982'}
    snapshot=client.rhea_reaction('11740')
    assert snapshot.request=={'query':'RHEA:11740','format':'json','limit':1}
    assert seen[-1][0]=='rhea-skill'


@pytest.mark.parametrize("status,client_error,expected_code", [(503,"network_error","provider_http_503"),(200,"invalid_response","invalid_response")])
def test_skill_http_error_keeps_exact_entity_status_request_and_no_repost(tmp_path,monkeypatch,status,client_error,expected_code):
    from gene_annotation_episode import acquisition
    script=tmp_path/'fixture_client.py';script.write_text('# synthetic installed-client fixture\n')
    monkeypatch.setattr(acquisition,'_skill_script',lambda *args:script)
    calls=[]
    body=b'{"native_error":"fixture service unavailable"}'
    def execute(command,**kwargs):
        request=json.loads(kwargs['input']);calls.append(request)
        Path(command[-2]).write_text(json.dumps({'status':status,'url':'https://example.invalid/fixture',
            'request_method':'GET','headers':{'content-type':'application/json','retry-after':'1'}}))
        Path(command[-1]).write_bytes(body)
        return SimpleNamespace(stdout=json.dumps({'ok':False,'error':{'code':client_error,'message':'native/client fixture'}}))
    monkeypatch.setattr(acquisition.subprocess,'run',execute)
    client=PublicClients(timeout=17)
    with Store(tmp_path/'store') as store:
        store.create_problem(raw_sequence='MKWAA',molecule='protein')
        tools=ToolRegistry(store,clients=client)
        before_sources=store.list('source')
        first=tools.execute('public.chebi.search',{'term':'fixture'},operation_key='failed-source')
        assert first['status']=='failed' and first['feedback']['code']==expected_code
        assert first['feedback']['phase']=='http_response'
        metadata=json.loads(store.get_artifact(first['feedback']['diagnostic_ref']))
        assert store.get_artifact(metadata['content_ref'])==body
        assert metadata['transport']['response']['status']==status
        assert metadata['request']['term']=='fixture'
        assert tools.execute('public.chebi.search',{'term':'fixture'},operation_key='failed-source')==first
        assert len(calls)==1 and store.list('source')==before_sources and not store.list('observation')


def test_native_details_cannot_be_model_authored_or_retargeted(tmp_path):
    with Store(tmp_path) as store:
        target=store.create_problem(raw_sequence='MKWAA',molecule='protein')['subject_refs'][0]
        result=ToolRegistry(store,clients=SavedChemistry()).execute('public.chebi.compound',{'accession':'CHEBI:27732'})
        reference=store.get(result['result']['records'][0]['reference_ref'])
        native=store.get(reference['native_record_ref'])
        payload={k:v for k,v in native.items() if k not in {'id','record_type','origin'}}
        with pytest.raises(ContractError,match='origin_not_allowed'):
            store.put('chemical_record',payload,origin='reasoning')
        bad={k:v for k,v in reference.items() if k not in {'id','record_type','origin'}}
        bad['accession']='CHEBI:123'
        with pytest.raises(ContractError,match='native_chemistry_reference_mismatch'):
            store.put('reference',bad,origin='external')
        h=store.put('hypothesis',{'subject_refs':[target],'predicate':'binds',
            'value':{'type':'reference','ref':reference['id']},'context_refs':[]},origin='reasoning')
        assert h['value']['ref']==reference['id'] and project_credit(store).credit==0
        assert store.targets()[0]['id']==target and len(store.targets())==1
        assert 'ontology_relations' not in json.dumps(store.reasoning_view())
        from gene_annotation_episode.export import export_annotation
        exported=export_annotation(store,tmp_path/'current.json',include_credit=True)
        records={r['id']:r for r in json.loads(Path(exported['json']['path']).read_text())['records']}
        assert records[reference['id']]['native_record_ref']==native['id']
        assert records[native['id']]==native
        assert records[native['source_ref']]['provider']=='chebi'


@pytest.mark.parametrize('returned_http',[False,True])
def test_client_timeout_keeps_known_response_without_inventing_http(tmp_path,monkeypatch,returned_http):
    from gene_annotation_episode import acquisition
    script=tmp_path/'fixture_client.py';script.write_text('# processing-timeout fixture\n')
    monkeypatch.setattr(acquisition,'_skill_script',lambda *args:script)
    body=b'{"native":"returned before client timed out"}'
    def run(command,**kwargs):
        if returned_http:
            Path(command[-2]).write_text(json.dumps({'status':200,'url':'https://example.invalid/fixture',
                'headers':{'content-type':'application/json'},'request_method':'GET'}))
            Path(command[-1]).write_bytes(body)
        raise acquisition.subprocess.TimeoutExpired(command,kwargs['timeout'])
    monkeypatch.setattr(acquisition.subprocess,'run',run)
    with pytest.raises(AcquisitionError) as caught:
        PublicClients(timeout=17).rhea_search('fixture',limit=1)
    error=caught.value
    assert error.code=='provider_client_timeout'
    if returned_http:
        assert error.snapshot.content==body
        assert error.snapshot.transport['response']['status']==200
        assert error.snapshot.transport['script']==str(script)
        assert error.phase=='http_response'
    else:
        assert error.snapshot is None and error.phase=='client_response'


def test_synthetic_wide_page_preview_keeps_complete_selected_records(tmp_path):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='MKWAA',molecule='protein')
        client=SavedChemistry()
        template=json.loads(client.rhea)['results'][0]
        # Synthetic IDs are deliberately confined to this engineering fixture.
        rows=[{**deepcopy(template),'id':str(900000+i)} for i in range(8)]
        client.rhea=json.dumps({'count':8,'results':rows}).encode()
        result=ToolRegistry(store,clients=client).execute('public.rhea.search',{'query':'synthetic bounded-page fixture','limit':8})
        assert result['status']=='completed'
        assert result['result']['projected_record_count']==8
        assert len(result['result']['records'])==6
        assert result['result']['more_records_available_through_state_query'] is True
        page=store.query_records(**result['result']['details_query'])
        assert page['total']==8 and len(page['records'])==6
        following=store.query_records(**page['next_query'])
        assert len(following['records'])==2 and following['next_query'] is None
        assert project_credit(store).credit==0
