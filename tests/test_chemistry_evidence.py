"""Native-source replays/fixtures and an explicitly opted-in bounded live lookup."""
from copy import deepcopy
import gzip
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import threading

import pytest

from gene_annotation_episode.acquisition import AcquisitionError, PublicClients, SourceSnapshot
from gene_annotation_episode.chemistry import chebi_response, chemical_row, rhea_equation, rhea_response, rhea_row
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
    client=PublicClients(timeout=17,rhea_response_byte_limit=12345,chebi_response_byte_limit=23456)
    seen=[]
    def skill(skill,filename,payload,**kwargs):
        seen.append((skill,filename,payload,kwargs))
        return {'ok':True},b'{}',{'fixture':True}
    monkeypatch.setattr(client,'_skill',skill)
    snapshot=client.chebi_search('caffeine',size=2,page=3)
    assert snapshot.request=={'term':'caffeine','size':2,'page':3}
    assert seen[-1][2]['params']==snapshot.request and 'query' not in snapshot.request
    assert seen[-1][2]['timeout_sec']==17 and seen[-1][0]=='chebi-skill'
    assert seen[-1][3]['max_bytes']==23456
    assert client.chebi_compound('22982').request=={'accession':'CHEBI:22982'}
    assert seen[-1][2]['path']=='chebi/backend/api/public/compound/CHEBI:22982/'
    assert seen[-1][3]['max_bytes']==23456
    snapshot=client.rhea_reaction('11740')
    assert snapshot.request=={'query':'RHEA:11740','format':'json','limit':1}
    assert seen[-1][0]=='rhea-skill'
    assert seen[-1][3]['max_bytes']==12345


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


@pytest.mark.skipif(
    os.environ.get('HMMER_NATIVE_ORACLE_RHEA_LIVE') != '1' or 'HMMER529_ATTEMPT' not in os.environ,
    reason='requires explicit live Rhea selection within bounded529')
def test_live_selected_rhea_reaction_retains_native_records_and_replays_without_request(tmp_path, monkeypatch):
    """One caller-selected real lookup; no target annotation or model edit.

    Explicit environment operands select the exact accession and installed
    skill root/client digest. Missing matches remain failures of this declared
    verification case, never another query or a substituted reaction. Original
    HTTP bytes, typed records and reference joins remain in the retained Store.
    """
    from gene_annotation_episode.chemistry import accession as canonical_accession

    selected = canonical_accession(os.environ['HMMER_NATIVE_ORACLE_RHEA_ACCESSION'], 'RHEA')
    skill_root = Path(os.environ['HMMER_NATIVE_ORACLE_RHEA_SKILL_ROOT']).resolve(strict=True)
    script = skill_root / 'skills/rhea-skill/scripts/rest_request.py'
    expected_script_sha = os.environ['HMMER_NATIVE_ORACLE_RHEA_CLIENT_SHA256']
    assert hashlib.sha256(script.read_bytes()).hexdigest() == expected_script_sha
    client = PublicClients(ncbi_email=None, skill_root=skill_root)
    store_path = tmp_path / 'store'
    operation_key = 'selected-live-rhea-reaction'
    arguments = {'accession': selected}
    evidence_path = Path(os.environ['HMMER529_ATTEMPT']) / 'rhea-live-reaction.json'
    report = {'schema': 'rhea_live_reaction_acquisition_v1',
        'request': {'operation': 'public.rhea.reaction', 'arguments': arguments},
        'store_path': str(store_path), 'operation_key': operation_key,
        'selected_client': {'script': str(script), 'sha256': expected_script_sha},
        'outcome': None, 'source_record': None, 'native_body': None,
        'request_metadata': None, 'reaction_records': [], 'reaction_references': [],
        'chemical_references': [], 'replay_verified': False,
        'qualification': 'Actual selected Rhea lookup; source reaction facts, no target assignment, model edit or function-confidence score.'}

    def save_report():
        evidence_path.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')

    with Store(store_path) as store:
        # This scope is only registry test setup; the source reaction is not
        # asserted to describe this protein or transferred to its annotation.
        original_problem = store.create_problem(raw_sequence='MKWAA', molecule='protein')
        tools = ToolRegistry(store, clients=client)
        actual = tools.execute('public.rhea.reaction', arguments, operation_key=operation_key)
        report['outcome'] = actual
        save_report()  # Retain real provider/lookup failures before assertions.
        body = actual.get('result')
        if isinstance(body, dict) and body.get('source_ref') is not None:
            source = store.get(body['source_ref'])
            report['source_record'] = source
            raw = store.get_artifact(source['artifact_ref'])
            sha = hashlib.sha256(raw).hexdigest()
            report['native_body'] = {'artifact_ref': source['artifact_ref'],
                'path': str(store.path / 'artifacts' / sha[:2] / sha),
                'sha256': sha, 'size_bytes': len(raw)}
            report['request_metadata'] = json.loads(store.get_artifact(source['request_ref']))
            save_report()
            read = tools.execute('state.query', {'kind': 'reaction_record',
                'references': [source['id']], 'offset': 0, 'limit': 10},
                operation_key='read-selected-live-rhea-records')
            assert read['status'] == 'completed', read
            report['reaction_records'] = read['result']['records']
            report['reaction_references'] = [store.get(row['reference_ref']) for row in body['records']]
            chemical_ids = list(dict.fromkeys(participant['chemical_ref']
                for record in report['reaction_records'] for participant in record['participants']))
            report['chemical_references'] = [store.get(reference) for reference in chemical_ids]
            save_report()

        assert actual['status'] == 'completed', actual
        assert body['requested_accession'] == selected
        assert body['exact_accession_match'] is True, body
        assert body['returned_accessions'] == [selected], body
        assert body['target_annotation'] == 'not_performed'
        assert body['thermodynamics_or_physiological_flux'] == 'not_inferred'
        assert not body['projection_errors']
        assert len(report['reaction_records']) == len(report['reaction_references']) == 1
        native = rhea_response(raw)
        assert len(native['results']) == body['provider_returned_row_count'] == 1
        record, reference = report['reaction_records'][0], report['reaction_references'][0]
        assert record['accession'] == reference['accession'] == selected
        assert record['source_ref'] == reference['source_ref'] == source['id']
        assert reference['native_record_ref'] == record['id']
        assert record['source_equation'] == native['results'][0]['equation']
        for field, source_field in (('source_status', 'status'), ('source_balanced', 'balanced'),
                                   ('source_transport', 'transport'), ('source_comment', 'comment')):
            assert record[field] == native['results'][0].get(source_field)
        assert record['source_direction'] in {'undefined', 'left_to_right', 'right_to_left', 'bidirectional'}
        participants = record['participants']
        assert {row['side'] for row in participants} == {'left', 'right'}
        assert [row['ordinal'] for row in participants] == list(range(len(participants)))
        chemicals = {row['id']: row for row in report['chemical_references']}
        for row in participants:
            chemical = chemicals[row['chemical_ref']]
            assert chemical['reference_type'] == 'chemical'
            assert chemical['source_ref'] == source['id']
            assert chemical['accession'] == row['source_accession']
            assert row['coefficient_expression']
            if row['coefficient_basis'] == 'implicit_unit_rhea_notation':
                assert row['source_coefficient_text'] == '' and row['coefficient_expression'] == '1'
            else:
                assert row['coefficient_basis'] == 'source_explicit'
                assert row['coefficient_expression'] == row['source_coefficient_text']
        request = report['request_metadata']
        assert request['request'] == {'query': selected, 'format': 'json', 'limit': 1}
        assert request['transport']['script'] == str(script)
        assert request['transport']['script_sha256'] == expected_script_sha
        assert request['transport']['representation'] == 'http_entity_bytes_via_installed_client'
        assert request['transport']['response']['status'] == 200
        assert Path(report['native_body']['path']).read_bytes() == raw
        assert not store.list('observation') and not store.current_annotations()
        assert store.problem() == original_problem
        frozen = deepcopy(actual)

    def forbidden(*args, **kwargs):
        raise AssertionError('closed selected Rhea operation attempted another request')

    monkeypatch.setattr(client, 'rhea_reaction', forbidden)
    with Store(store_path) as reopened:
        replay = ToolRegistry(reopened, clients=client).execute('public.rhea.reaction', arguments,
            operation_key=operation_key)
        assert replay == frozen
        assert reopened.get(record['id']) == record
        assert reopened.get_artifact(source['artifact_ref']) == raw
        assert not reopened.list('observation') and not reopened.current_annotations()
    report['replay_verified'] = True
    save_report()


@pytest.mark.skipif(
    os.environ.get('HMMER_NATIVE_ORACLE_RHEA_SEARCH_LIVE') != '1' or 'HMMER529_ATTEMPT' not in os.environ,
    reason='requires explicit non-ID live Rhea search selection within bounded529')
def test_live_selected_rhea_non_identifier_search_retains_bounded_native_response_and_replays(tmp_path, monkeypatch):
    """One fixed public query, with genuine selected script and bounded observer.

    An empty response is an actual limited-query result. No alternate query,
    exact-ID request, direction lookup, target annotation or model edit follows.
    Complete entity capture and the requested row limit are separate facts.
    """
    from urllib.parse import parse_qs, urlsplit
    from gene_annotation_episode import acquisition

    query = os.environ['HMMER_NATIVE_ORACLE_RHEA_SEARCH_QUERY']
    limit = int(os.environ['HMMER_NATIVE_ORACLE_RHEA_SEARCH_LIMIT'])
    budget = int(os.environ['HMMER_NATIVE_ORACLE_RHEA_RESPONSE_BYTE_LIMIT'])
    assert (query, limit, budget) == ('glutathione disulfide', 2, 8 * 1024 * 1024)
    skill_root = Path(os.environ['HMMER_NATIVE_ORACLE_RHEA_SKILL_ROOT']).resolve(strict=True)
    script = Path(os.environ['HMMER_NATIVE_ORACLE_RHEA_SEARCH_CLIENT']).resolve(strict=True)
    assert script == (skill_root / 'skills/rhea-skill/scripts/rest_request.py').resolve(strict=True)
    expected_script_sha = os.environ['HMMER_NATIVE_ORACLE_RHEA_CLIENT_SHA256']
    assert expected_script_sha == '78ddae6460e3dd701cda67df4454532899d20851f8212a74ec8d5b6e2988b690'
    assert hashlib.sha256(script.read_bytes()).hexdigest() == expected_script_sha
    adapter_sha = hashlib.sha256(Path(acquisition.__file__).read_bytes()).hexdigest()
    client = PublicClients(ncbi_email=None, skill_root=skill_root, rhea_response_byte_limit=budget)
    store_path = tmp_path / 'store'
    operation_key = 'selected-live-rhea-non-identifier-search'
    arguments = {'query': query, 'limit': limit}
    evidence_path = Path(os.environ['HMMER529_ATTEMPT']) / 'rhea-live-search.json'
    report = {'schema': 'rhea_live_search_acquisition_v1',
        'request': {'operation': 'public.rhea.search', 'arguments': arguments},
        'response_byte_limit': budget, 'store_path': str(store_path), 'operation_key': operation_key,
        'selected_client': {'script': str(script), 'sha256': expected_script_sha},
        'selected_observer': {'module': 'gene_annotation_episode.acquisition', 'sha256': adapter_sha},
        'outcome': None, 'source_record': None, 'native_body': None, 'diagnostic': None,
        'request_metadata': None, 'native_rows': None, 'native_count': None,
        'reaction_records': [], 'reaction_references': [], 'chemical_references': [],
        'record_reads': [], 'replay_verified': False,
        'qualification': 'Actual selected non-ID public Rhea search. The requested limit of two rows '
            'does not establish completeness of the database query. Complete-body means only that '
            'the selected HTTP entity was retained within the decoded-byte budget. Native count and '
            'all returned rows remain source facts; zero rows is not exhaustive absence. No paging, '
            'alternate query, exact lookup, directional-variant resolution, chemical-database lookup, '
            'gene correspondence, scientific measurement, target assignment or model edit is performed.'}

    def save_report():
        evidence_path.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')

    def retain_body(store, artifact_ref):
        raw = store.get_artifact(artifact_ref)
        sha = hashlib.sha256(raw).hexdigest()
        report['native_body'] = {'artifact_ref': artifact_ref,
            'path': str(store.path / 'artifacts' / sha[:2] / sha), 'sha256': sha, 'size_bytes': len(raw)}
        return raw

    with Store(store_path) as store:
        original_problem = store.create_problem(raw_sequence='MKWAA', molecule='protein')
        tools = ToolRegistry(store, clients=client)
        actual = tools.execute('public.rhea.search', arguments, operation_key=operation_key)
        report['outcome'] = actual
        save_report()
        body = actual.get('result')
        if isinstance(body, dict) and body.get('source_ref') is not None:
            source = store.get(body['source_ref'])
            report['source_record'] = source
            raw = retain_body(store, source['artifact_ref'])
            report['request_metadata'] = json.loads(store.get_artifact(source['request_ref']))
            save_report()
            native = rhea_response(raw)
            report['native_rows'] = native['results']
            report['native_count'] = native.get('count')
            save_report()

            def read_all(kind):
                selection = {'kind': kind, 'references': [source['id']], 'offset': 0, 'limit': 6}
                records = []
                page = 0
                while selection is not None:
                    read = tools.execute('state.query', selection,
                        operation_key=f'read-selected-live-rhea-search-{kind}-{page}')
                    report['record_reads'].append({'arguments': deepcopy(selection), 'outcome': read})
                    save_report()
                    assert read['status'] == 'completed', read
                    records.extend(read['result']['records'])
                    selection = read['result']['next_query']
                    page += 1
                return records

            report['reaction_records'] = read_all('reaction_record')
            references = read_all('reference')
            report['reaction_references'] = [row for row in references if row['reference_type'] == 'reaction']
            report['chemical_references'] = [row for row in references if row['reference_type'] == 'chemical']
            save_report()
        else:
            diagnostic_ref = (actual.get('feedback') or {}).get('diagnostic_ref')
            if diagnostic_ref is not None:
                diagnostic = json.loads(store.get_artifact(diagnostic_ref))
                report['diagnostic'] = diagnostic
                report['request_metadata'] = diagnostic
                retain_body(store, diagnostic['content_ref'])
                save_report()

        assert actual['status'] == 'completed', actual
        assert report['source_record'] is not None
        assert body['target_annotation'] == 'not_performed'
        assert body['thermodynamics_or_physiological_flux'] == 'not_inferred'
        assert body['result_scope'] == 'provider_limited_json_search_not_exhaustive_absence'
        assert body['direction_scope'] == 'json_search_master_records_directional_variants_not_resolved'
        assert body['projection_errors'] == []
        assert body['provider_returned_row_count'] == body['projected_record_count'] == len(native['results'])
        assert body.get('native_count') == native.get('count')

        expected = [rhea_row(row) for row in native['results']]
        projection_fields = set().union(*(row.keys() for row in expected)) - {'participants'}
        projected = []
        chemicals = {row['id']: row for row in report['chemical_references']}
        reaction_references = {row['native_record_ref']: row for row in report['reaction_references']}
        used_chemicals = set()
        for record in report['reaction_records']:
            assert record['source_ref'] == source['id']
            reference = reaction_references[record['id']]
            assert reference['source_ref'] == source['id']
            assert reference['accession'] == record['accession']
            projected.append({**{key: record[key] for key in projection_fields},
                'participants': [{key: value for key, value in part.items() if key != 'chemical_ref'}
                    for part in record['participants']]})
            for participant in record['participants']:
                chemical = chemicals[participant['chemical_ref']]
                used_chemicals.add(chemical['id'])
                assert chemical['source_ref'] == source['id']
                assert chemical['accession'] == participant['source_accession']
                assert store.coverage(chemical['id']) == []
        canonical = lambda value: json.dumps(value, sort_keys=True, allow_nan=False)
        assert {canonical(row) for row in projected} == {canonical(row) for row in expected}
        assert len(reaction_references) == len(report['reaction_records'])
        assert used_chemicals == set(chemicals)
        assert {row['id'] for row in references} == set(chemicals) | {
            row['id'] for row in reaction_references.values()}
        retained_refs = {source['id']} | {row['id'] for row in report['reaction_records']} | {
            row['id'] for row in references}
        assert set(actual['record_refs']) == retained_refs

        request = report['request_metadata']
        assert request['request'] == {'query': query, 'format': 'json', 'limit': limit}
        transport = request['transport']
        assert transport['script'] == str(script) and transport['script_sha256'] == expected_script_sha
        assert transport['representation'] == 'http_entity_bytes_via_installed_client'
        observer = transport['observer']
        assert observer == {'version': 'bounded_skill_http_entity_capture_v1',
            'adapter_module': 'gene_annotation_episode.acquisition', 'adapter_sha256': adapter_sha,
            'response_byte_limit': budget, 'byte_basis': 'requests_decoded_entity_bytes',
            'stream': True, 'automatic_redirects': False, 'redirect_preparation': False}
        response = transport['response']
        assert response['status'] == 200 and response['request_method'] == 'GET'
        assert response['headers'] and 'x-engineering-control' not in response['headers']
        url = urlsplit(response['url'])
        assert (url.scheme, url.netloc, url.path) == ('https', 'www.rhea-db.org', '/rhea')
        assert parse_qs(url.query) == {'query': [query], 'format': ['json'], 'limit': [str(limit)]}
        assert response['body_complete'] is response['body_capture_finalized'] is True
        assert response['response_byte_limit'] == budget
        assert response['observed_body_bytes'] == response['retained_body_bytes'] == response['total_body_bytes'] == len(raw)
        assert response.get('body_capture_failure') is None and 0 < len(raw) <= budget
        assert source['retrieved_at'] and source['version'] is None
        assert Path(report['native_body']['path']).read_bytes() == raw
        assert not store.list('observation') and not store.current_annotations()
        assert store.count('observation') == store.count('assessment') == store.count('annotation') == 0
        assert store.problem() == original_problem
        frozen = deepcopy(actual)
        frozen_records = deepcopy([source, *report['reaction_records'], *references])

    def forbidden(*args, **kwargs):
        raise AssertionError('closed selected Rhea search attempted another request')

    monkeypatch.setattr(client, 'rhea_search', forbidden)
    with Store(store_path) as reopened:
        replay = ToolRegistry(reopened, clients=client).execute('public.rhea.search', arguments,
            operation_key=operation_key)
        assert replay == frozen
        assert [reopened.get(row['id']) for row in frozen_records] == frozen_records
        assert reopened.get_artifact(source['artifact_ref']) == raw
        assert json.loads(reopened.get_artifact(source['request_ref'])) == request
        assert not reopened.list('observation') and not reopened.current_annotations()
        assert reopened.count('observation') == reopened.count('assessment') == reopened.count('annotation') == 0
    report['replay_verified'] = True
    save_report()


@pytest.mark.skipif(not os.environ.get('HMMER_NATIVE_ORACLE_RHEA_SEARCH_RETAINED_CAPTURE'),
    reason='requires explicit retained222 native search capture within bounded529')
def test_retained_native_rhea_non_identifier_search_finishes_checks_and_replays_without_http(tmp_path, monkeypatch):
    """Retain222 facts unchanged; never repeat its already-completed HTTP request.

    The original test failed after acquisition at a retired scoring assertion.
    This separate case checks authentic retained bytes and same-key Store replay;
    it does not repair the original test or establish its lifecycle completion.
    """
    assert os.environ.get('HMMER529_ATTEMPT'), 'requires the selected bounded529 runtime'
    capture_path = Path(os.environ['HMMER_NATIVE_ORACLE_RHEA_SEARCH_RETAINED_CAPTURE'])
    assert capture_path.is_absolute()
    capture_raw = capture_path.read_bytes()
    assert hashlib.sha256(capture_raw).hexdigest() == \
        '155e6367d3097c3ce7b0d87b23951c1d7529461ed5bc973f2c77d4acfe0eae9a'
    capture = json.loads(capture_raw)
    assert capture['schema'] == 'rhea_live_search_acquisition_v1' and capture['replay_verified'] is False
    assert capture['request'] == {'operation': 'public.rhea.search',
        'arguments': {'query': 'glutathione disulfide', 'limit': 2}}
    source = capture['source_record']
    metadata = capture['request_metadata']
    body_path = Path(capture['native_body']['path'])
    database_path = Path(capture['store_path']) / 'state.sqlite3'
    paths = {'selected_capture': capture_path, 'native_body': body_path, 'original_database': database_path}

    def pins():
        return {name: {'path': str(path), 'size_bytes': path.stat().st_size,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()} for name, path in paths.items()}

    original_pins = pins()
    assert original_pins['original_database']['sha256'] == \
        'd7726a719942e92dc43ed5991bb5ed2362cb3c50eadb80408c224841a09b143f'
    raw = body_path.read_bytes()
    body_sha = hashlib.sha256(raw).hexdigest()
    assert len(raw) == capture['native_body']['size_bytes'] == 13299
    assert body_sha == capture['native_body']['sha256'] == \
        'f1d30a0e4783dcf4e36a7dedf0f6f43279355363da1df473540b716f0be375d9'
    assert source['artifact_ref'] == capture['native_body']['artifact_ref'] == 'artifact_' + body_sha
    assert metadata['request'] == {'query': 'glutathione disulfide', 'format': 'json', 'limit': 2}
    assert metadata['transport']['script_sha256'] == capture['selected_client']['sha256'] == \
        '78ddae6460e3dd701cda67df4454532899d20851f8212a74ec8d5b6e2988b690'
    assert metadata['transport']['observer']['adapter_sha256'] == capture['selected_observer']['sha256'] == \
        '9bf11eee4a3b82df314911c364187e80bc15ddba2b3ac6ac26974baf666c208f'
    response = metadata['transport']['response']
    assert response['status'] == 200
    assert response['body_complete'] is response['body_capture_finalized'] is True
    assert response['observed_body_bytes'] == response['retained_body_bytes'] == response['total_body_bytes'] == len(raw)
    assert response['response_byte_limit'] == capture['response_byte_limit'] == 8388608
    assert source['retrieved_at'] == '2026-10-30T03:52:00.696349+00:00' and source['version'] is None
    native = rhea_response(raw)
    assert native['results'] == capture['native_rows']
    assert native['count'] == capture['native_count'] == 2
    assert [row['id'] for row in native['results']] == ['11740', '24424']
    expected = {row['id']: row for row in [source, *capture['reaction_records'],
        *capture['reaction_references'], *capture['chemical_references']]}
    assert len(expected) == 12 and set(capture['outcome']['record_refs']) == set(expected)

    class RetainedSearch:
        def __init__(self):
            self.calls = []

        def rhea_search(self, query, limit=10):
            assert (query, limit) == ('glutathione disulfide', 2)
            self.calls.append({'operation': 'public.rhea.search', 'arguments': {'query': query, 'limit': limit}})
            return SourceSnapshot('rhea', source['uri'], deepcopy(metadata['request']),
                source['retrieved_at'], raw, 'application/json', deepcopy(metadata['transport']))

    client = RetainedSearch()
    store_path = tmp_path / 'retained-search-store'
    operation_key = 'retained-rhea222-non-identifier-search'
    with Store(store_path) as store:
        original_problem = store.create_problem(raw_sequence='MKWAA', molecule='protein')
        tools = ToolRegistry(store, clients=client)
        actual = tools.execute('public.rhea.search', capture['request']['arguments'], operation_key=operation_key)
        assert client.calls == [capture['request']]
        assert actual['status'] == 'completed', actual
        # A new operation key belongs to this retained-only test. Scientific
        # records, source custody and semantic result retain their original IDs.
        assert {key: value for key, value in actual.items() if key != 'operation_ref'} == {
            key: value for key, value in capture['outcome'].items() if key != 'operation_ref'}
        assert {reference: store.get(reference) for reference in expected} == expected
        for index, read in enumerate(capture['record_reads']):
            current = tools.execute('state.query', read['arguments'],
                operation_key=f'retained-rhea222-read-{index}')
            assert current['status'] == 'completed' and current['result'] == read['outcome']['result']
        for record in capture['reaction_records']:
            assert record['source_ref'] == source['id']
            matching = [row for row in native['results'] if 'RHEA:' + row['id'] == record['accession']]
            assert len(matching) == 1
            parsed = rhea_row(matching[0])
            assert {key: record[key] for key in parsed if key != 'participants'} == {
                key: value for key, value in parsed.items() if key != 'participants'}
            assert [{key: value for key, value in participant.items() if key != 'chemical_ref'}
                for participant in record['participants']] == parsed['participants']
            for participant in record['participants']:
                chemical = store.get(participant['chemical_ref'])
                assert chemical['source_ref'] == source['id']
                assert chemical['accession'] == participant['source_accession']
                assert store.coverage(chemical['id']) == []
        assert store.get_artifact(source['artifact_ref']) == raw
        assert json.loads(store.get_artifact(source['request_ref'])) == metadata
        assert store.problem() == original_problem
        assert store.count('observation') == store.count('assessment') == store.count('annotation') == 0
        frozen = deepcopy(actual)

    def forbidden(*args, **kwargs):
        raise AssertionError('closed retained Rhea search attempted another acquisition')

    monkeypatch.setattr(client, 'rhea_search', forbidden)
    with Store(store_path) as reopened:
        replay = ToolRegistry(reopened, clients=client).execute('public.rhea.search', capture['request']['arguments'],
            operation_key=operation_key)
        assert replay == frozen
        assert {reference: reopened.get(reference) for reference in expected} == expected
        assert reopened.get_artifact(source['artifact_ref']) == raw
        assert json.loads(reopened.get_artifact(source['request_ref'])) == metadata
        assert reopened.problem() == original_problem
        assert reopened.count('observation') == reopened.count('assessment') == reopened.count('annotation') == 0
    assert pins() == original_pins
    verification = {'schema': 'retained_rhea_search_verification_v1',
        'qualification': 'Separate retained-only importer/typed-record and same-key replay verification of '
            'authentic222 search bytes, request, retrieval time and transport. No PublicClients, fresh HTTP, '
            'alternate query, scientific measurement, target annotation, model edit or score. The failed '
            'original222 test and its execution_unknown lifecycle remain unchanged.',
        'original_pins': original_pins, 'original_request': capture['request'],
        'original_request_metadata': metadata, 'original_retrieved_at': source['retrieved_at'],
        'original_operation_key': capture['operation_key'],
        'original_operation_ref': capture['outcome']['operation_ref'],
        'retained_operation_key': operation_key, 'retained_outcome': frozen,
        'retained_store_path': str(store_path), 'source_record': source,
        'reaction_records': capture['reaction_records'], 'reaction_references': capture['reaction_references'],
        'chemical_references': capture['chemical_references'], 'retained_snapshot_calls': client.calls,
        'originals_unchanged': True, 'replay_verified': True}
    (Path(os.environ['HMMER529_ATTEMPT']) / 'rhea-retained-search-verification.json').write_text(
        json.dumps(verification, indent=2, allow_nan=False) + '\n')


def _controlled_bounded_rhea_client(tmp_path, monkeypatch, body, *, budget, status=200,
                                    encoded=False, fragment=4096, fail_after=None,
                                    stall_after=None, timeout=90, provider='rhea'):
    """Unchanged selected client and real Session.send, controlled HTTP adapter.

    The adapter supplies engineering bytes without contacting a service. Its
    underlying urllib3 response still performs the actual incremental decoding.
    The test-only prelude is separate from the production capture observer.
    """
    from gene_annotation_episode import acquisition
    assert provider in {'rhea', 'chebi'}
    selected = Path(os.environ[f'HMMER_NATIVE_ORACLE_{provider.upper()}_CAPTURE_CLIENT'])
    assert selected.is_absolute()
    assert hashlib.sha256(selected.read_bytes()).hexdigest() == \
        '78ddae6460e3dd701cda67df4454532899d20851f8212a74ec8d5b6e2988b690'
    wire = gzip.compress(body) if encoded else body
    headers = {'content-type': 'application/json', 'content-length': str(len(wire)),
        'x-engineering-control': 'controlled-http-adapter-no-network'}
    if encoded:
        headers['content-encoding'] = 'gzip'
    if 300 <= status < 400:
        headers['location'] = 'https://example.invalid/must-not-be-requested'
    control_path = tmp_path / 'http-control.json'
    measurement_path = tmp_path / 'http-control-measurement.json'
    control_path.write_text(json.dumps({'wire_hex': wire.hex(), 'headers': headers, 'status': status,
        'fragment': fragment, 'fail_after': fail_after, 'stall_after': stall_after,
        'stall_seconds': timeout * 2, 'measurement_path': str(measurement_path)}))
    prelude = '''import io, json, pathlib, time, requests
from urllib3.response import HTTPResponse
control = json.loads(pathlib.Path(CONTROL_PATH).read_bytes())
measurement_path = pathlib.Path(control['measurement_path'])
measurements = {'send_calls': 0, 'wire_bytes_delivered': 0, 'read_amounts': [], 'stream_values': []}
def save_measurements():
    measurement_path.write_text(json.dumps(measurements))
class ControlledReader(io.BytesIO):
    def read1(self, amount):
        measurements['read_amounts'].append(amount)
        save_measurements()
        if control['stall_after'] is not None and self.tell() >= control['stall_after']:
            time.sleep(control['stall_seconds'])
        if control['fail_after'] is not None and self.tell() >= control['fail_after']:
            raise OSError('controlled interrupted HTTP body')
        block = super().read(min(amount, control['fragment']))
        measurements['wire_bytes_delivered'] += len(block)
        save_measurements()
        return block
def controlled_send(self, request, **kwargs):
    measurements['send_calls'] += 1
    measurements['stream_values'].append(kwargs.get('stream'))
    save_measurements()
    raw = HTTPResponse(body=ControlledReader(bytes.fromhex(control['wire_hex'])),
        headers=control['headers'], status=control['status'], reason='engineering control',
        preload_content=False, decode_content=False, request_method=request.method, request_url=request.url)
    return self.build_response(request, raw)
requests.adapters.HTTPAdapter.send = controlled_send
'''.replace('CONTROL_PATH', repr(str(control_path)))
    actual_run = acquisition.subprocess.run
    def controlled_run(command, **kwargs):
        assert command[1] == '-c' and str(selected) in command
        return actual_run([*command[:2], prelude + command[2], *command[3:]], **kwargs)
    def selected_script(root, skill, filename):
        assert (skill, filename) == (provider + '-skill', 'rest_request.py')
        return selected
    monkeypatch.setattr(acquisition, '_skill_script', selected_script)
    monkeypatch.setattr(acquisition.subprocess, 'run', controlled_run)
    return PublicClients(ncbi_email=None, timeout=timeout,
        **{provider + '_response_byte_limit': budget}), measurement_path, headers


@pytest.mark.parametrize('limit', [True, False, 0, -1, None, 1.5])
def test_rhea_response_byte_limit_requires_positive_integer(limit):
    with pytest.raises(ValueError, match='invalid_rhea_response_byte_limit'):
        PublicClients(ncbi_email=None, rhea_response_byte_limit=limit)


@pytest.mark.parametrize('body,limit,expected,failure', [
    (b'abcd', 4, b'abcd', None), (b'abcd', 3, b'abc', 'provider_response_byte_limit'),
    (b'abc', 8, b'abc', 'provider_body_capture_failed')])
def test_existing_unencoded_bounded_reader_keeps_original_metadata_contract(body, limit, expected, failure):
    import io
    response = io.BytesIO(body)
    response.headers = {'Content-Length': '4'}
    raw, metadata, actual_failure = PublicClients._read_bounded_response(response, limit)
    assert raw == expected and actual_failure == failure
    expected_metadata = {'body_complete': failure is None, 'response_byte_limit': limit,
        'observed_body_bytes': len(body), 'retained_body_bytes': len(expected), 'declared_body_bytes': 4}
    if failure is not None:
        expected_metadata['body_capture_failure'] = failure
    if failure == 'provider_body_capture_failed':
        expected_metadata['body_capture_error'] = 'IncompleteRead'
    assert metadata == expected_metadata


_BOUNDED_CLIENT = pytest.mark.skipif(not os.environ.get('HMMER_NATIVE_ORACLE_RHEA_CAPTURE_CLIENT'),
    reason='requires explicit selected immutable Rhea client within bounded529')


@_BOUNDED_CLIENT
@pytest.mark.parametrize('kind', ['exact_limit', 'multiple_chunks'])
def test_bounded_rhea_selected_client_preserves_complete_entity(tmp_path, monkeypatch, kind):
    body = b'{"control":1}' if kind == 'exact_limit' else b'{"control":"' + b'a' * 140000 + b'"}'
    client, measurement_path, _ = _controlled_bounded_rhea_client(tmp_path, monkeypatch, body,
        budget=len(body))
    snapshot = client.rhea_search('engineering controlled response', limit=2)
    assert snapshot.content == body
    assert snapshot.request == {'query': 'engineering controlled response', 'format': 'json', 'limit': 2}
    response = snapshot.transport['response']
    assert response['body_complete'] is True and response['body_capture_finalized'] is True
    assert response['observed_body_bytes'] == response['retained_body_bytes'] == len(body)
    assert response['total_body_bytes'] == response['declared_body_bytes'] == len(body)
    observer = snapshot.transport['observer']
    assert observer['response_byte_limit'] == len(body) and observer['stream'] is True
    assert observer['automatic_redirects'] is observer['redirect_preparation'] is False
    from gene_annotation_episode import acquisition
    assert observer['adapter_sha256'] == hashlib.sha256(Path(acquisition.__file__).read_bytes()).hexdigest()
    measurement = json.loads(measurement_path.read_bytes())
    assert measurement['send_calls'] == 1 and measurement['stream_values'] == [True]
    assert measurement['wire_bytes_delivered'] == len(body)
    assert max(measurement['read_amounts']) <= min(65536, len(body) + 1)


@_BOUNDED_CLIENT
def test_bounded_rhea_overflow_is_prefix_diagnostic_and_closed_failure_replays(tmp_path, monkeypatch):
    body = b'{"control":"' + b'a' * 10000 + b'"}'
    client, measurement_path, _ = _controlled_bounded_rhea_client(tmp_path, monkeypatch, body, budget=64)
    with Store(tmp_path / 'store') as store:
        store.create_problem(raw_sequence='MKWAA', molecule='protein')
        tools = ToolRegistry(store, clients=client)
        sources_before = store.list('source')
        result = tools.execute('public.rhea.search', {'query': 'engineering byte-limit control', 'limit': 2},
            operation_key='bounded-rhea-overflow')
        assert result['status'] == 'failed' and result['feedback']['code'] == 'provider_response_byte_limit'
        metadata = json.loads(store.get_artifact(result['feedback']['diagnostic_ref']))
        assert store.get_artifact(metadata['content_ref']) == body[:64]
        response = metadata['transport']['response']
        assert response['status'] == 200 and response['body_complete'] is False
        assert response['body_capture_failure'] == 'provider_response_byte_limit'
        assert response['observed_body_bytes'] == 65 and response['retained_body_bytes'] == 64
        assert response['total_body_bytes'] is None
        before = measurement_path.read_bytes()
        monkeypatch.setattr(client, 'rhea_search', lambda *args, **kwargs: pytest.fail('replayed failure requested HTTP'))
        assert tools.execute('public.rhea.search', {'query': 'engineering byte-limit control', 'limit': 2},
            operation_key='bounded-rhea-overflow') == result
        assert measurement_path.read_bytes() == before
        assert store.list('source') == sources_before and not store.list('reaction_record') and not store.list('observation')
    measurement = json.loads(measurement_path.read_bytes())
    assert measurement['send_calls'] == 1 and measurement['wire_bytes_delivered'] == 65


@_BOUNDED_CLIENT
def test_bounded_rhea_interruption_retains_actual_delivered_prefix(tmp_path, monkeypatch):
    body = b'{"control":"' + b'a' * 1000 + b'"}'
    client, measurement_path, _ = _controlled_bounded_rhea_client(tmp_path, monkeypatch, body,
        budget=256, fragment=16, fail_after=32)
    with pytest.raises(AcquisitionError) as failure:
        client.rhea_search('engineering interrupted response', limit=2)
    error = failure.value
    assert error.code == 'provider_body_capture_failed' and error.phase == 'http_response'
    assert error.snapshot.content == body[:32]
    response = error.snapshot.transport['response']
    assert response['status'] == 200 and response['body_complete'] is False
    assert response['observed_body_bytes'] == response['retained_body_bytes'] == 32
    assert response['total_body_bytes'] is None and response['body_capture_error']
    assert json.loads(measurement_path.read_bytes())['wire_bytes_delivered'] == 32


@_BOUNDED_CLIENT
@pytest.mark.parametrize('overflow', [False, True])
def test_bounded_rhea_gzip_limits_decoded_entity_and_preserves_wire_header(tmp_path, monkeypatch, overflow):
    body = b'{"control":"' + b'a' * 10000 + b'"}'
    budget = 64 if overflow else len(body)
    client, _, headers = _controlled_bounded_rhea_client(tmp_path, monkeypatch, body,
        budget=budget, encoded=True)
    if overflow:
        with pytest.raises(AcquisitionError) as failure:
            client.rhea_search('engineering gzip response', limit=2)
        assert failure.value.code == 'provider_response_byte_limit'
        snapshot = failure.value.snapshot
    else:
        snapshot = client.rhea_search('engineering gzip response', limit=2)
    response = snapshot.transport['response']
    assert snapshot.content == body[:budget]
    assert response['headers']['content-length'] == headers['content-length']
    assert int(headers['content-length']) != len(body) and response['declared_body_bytes'] is None
    assert response['body_complete'] is (not overflow)
    assert response['observed_body_bytes'] == (65 if overflow else len(body))
    assert response['total_body_bytes'] == (None if overflow else len(body))


@_BOUNDED_CLIENT
@pytest.mark.parametrize('status,overflow', [(503, False), (503, True), (302, False), (302, True)])
def test_bounded_rhea_http_status_and_capture_failure_are_separate(tmp_path, monkeypatch, status, overflow):
    body = b'{"control":"' + b'a' * 10000 + b'"}'
    budget = 64 if overflow else len(body)
    client, measurement_path, _ = _controlled_bounded_rhea_client(tmp_path, monkeypatch, body,
        budget=budget, status=status)
    with pytest.raises(AcquisitionError) as failure:
        client.rhea_search('engineering HTTP status control', limit=2)
    error = failure.value
    assert error.code == ('provider_http_503' if status == 503 else 'provider_redirect_not_followed')
    assert error.snapshot.content == body[:budget]
    response = error.snapshot.transport['response']
    assert response['status'] == status and response['body_complete'] is (not overflow)
    assert response.get('body_capture_failure') == ('provider_response_byte_limit' if overflow else None)
    measurement = json.loads(measurement_path.read_bytes())
    assert measurement['send_calls'] == 1 and measurement['stream_values'] == [True]
    assert measurement['wire_bytes_delivered'] <= budget + 1


@_BOUNDED_CLIENT
def test_bounded_rhea_outer_timeout_preserves_prefix_with_unknown_observed_total(tmp_path, monkeypatch):
    body = b'{"control":"' + b'a' * 1000 + b'"}'
    client, measurement_path, _ = _controlled_bounded_rhea_client(tmp_path, monkeypatch, body,
        budget=256, fragment=16, stall_after=32, timeout=5)
    with pytest.raises(AcquisitionError) as failure:
        client.rhea_search('engineering processing timeout', limit=2)
    error = failure.value
    assert error.code == 'provider_client_timeout' and error.phase == 'http_response'
    assert error.snapshot.content == body[:32]
    response = error.snapshot.transport['response']
    assert response['status'] == 200 and response['body_complete'] is False
    assert response['body_capture_finalized'] is False
    assert response['retained_body_bytes'] == response['observed_body_bytes_lower_bound'] == 32
    assert response['observed_body_bytes'] is response['total_body_bytes'] is None
    assert json.loads(measurement_path.read_bytes())['wire_bytes_delivered'] == 32


@pytest.mark.parametrize('limit', [True, False, 0, -1, None, 1.5])
def test_chebi_response_byte_limit_requires_positive_integer(limit):
    with pytest.raises(ValueError, match='invalid_chebi_response_byte_limit'):
        PublicClients(ncbi_email=None, chebi_response_byte_limit=limit)


_BOUNDED_CHEBI_CLIENT = pytest.mark.skipif(not os.environ.get('HMMER_NATIVE_ORACLE_CHEBI_CAPTURE_CLIENT'),
    reason='requires explicit selected immutable ChEBI client within bounded529')


@_BOUNDED_CHEBI_CLIENT
@pytest.mark.parametrize('entry', ['search', 'compound'])
@pytest.mark.parametrize('case', ['exact_limit', 'overflow', 'gzip_limit', 'gzip_overflow',
    'interruption', 'http_error_overflow', 'redirect_overflow'])
def test_bounded_chebi_both_native_entries_capture_selected_entity(tmp_path, monkeypatch, entry, case):
    """Engineering adapter bytes; actual selected client/Requests/urllib3 path."""
    from urllib.parse import parse_qs, urlsplit
    from gene_annotation_episode import acquisition

    body = b'{"engineering_control":"' + b'a' * 10000 + b'"}'
    encoded = case.startswith('gzip_')
    budget = len(body) if case in {'exact_limit', 'gzip_limit'} else 256 if case == 'interruption' else 64
    status = 503 if case == 'http_error_overflow' else 302 if case == 'redirect_overflow' else 200
    client, measurement_path, headers = _controlled_bounded_rhea_client(tmp_path, monkeypatch, body,
        provider='chebi', budget=budget, status=status, encoded=encoded,
        fragment=16 if case == 'interruption' else 4096,
        fail_after=32 if case == 'interruption' else None)
    arguments = {'term': 'engineering controlled chemical response', 'size': 2, 'page': 1} if entry == 'search' else {
        'accession': 'CHEBI:58297'}
    failure_code = {'overflow': 'provider_response_byte_limit', 'gzip_overflow': 'provider_response_byte_limit',
        'interruption': 'provider_body_capture_failed', 'http_error_overflow': 'provider_http_503',
        'redirect_overflow': 'provider_redirect_not_followed'}.get(case)
    if failure_code is not None:
        with pytest.raises(AcquisitionError) as caught:
            getattr(client, 'chebi_' + entry)(**arguments)
        assert caught.value.code == failure_code and caught.value.phase == 'http_response'
        snapshot = caught.value.snapshot
    else:
        snapshot = getattr(client, 'chebi_' + entry)(**arguments)
        assert snapshot.request == arguments
    response = snapshot.transport['response']
    complete = failure_code is None
    retained = len(body) if complete else 32 if case == 'interruption' else budget
    observed = retained if complete or case == 'interruption' else budget + 1
    assert snapshot.content == body[:retained] and snapshot.service == 'chebi'
    assert response['status'] == status and response['request_method'] == 'GET'
    assert response['body_capture_finalized'] is True and response['body_complete'] is complete
    assert response['retained_body_bytes'] == retained and response['observed_body_bytes'] == observed
    assert response['total_body_bytes'] == (len(body) if complete else None)
    expected_capture_failure = None if complete else 'provider_body_capture_failed' if case == 'interruption' else 'provider_response_byte_limit'
    assert response.get('body_capture_failure') == expected_capture_failure
    assert response['headers'] == headers
    assert response['declared_body_bytes'] == (None if encoded else len(body))
    observer = snapshot.transport['observer']
    assert observer['response_byte_limit'] == budget and observer['stream'] is True
    assert observer['automatic_redirects'] is observer['redirect_preparation'] is False
    assert observer['adapter_sha256'] == hashlib.sha256(Path(acquisition.__file__).read_bytes()).hexdigest()
    url = urlsplit(response['url'])
    assert (url.scheme, url.netloc) == ('https', 'www.ebi.ac.uk')
    if entry == 'search':
        assert url.path == '/chebi/backend/api/public/es_search/'
        assert parse_qs(url.query) == {key: [str(value)] for key, value in arguments.items()}
    else:
        assert url.path == '/chebi/backend/api/public/compound/CHEBI:58297/' and url.query == ''
    measurement = json.loads(measurement_path.read_bytes())
    assert measurement['send_calls'] == 1 and measurement['stream_values'] == [True]
    if encoded:
        full_wire_bytes = int(headers['content-length'])
        if complete:
            assert measurement['wire_bytes_delivered'] == full_wire_bytes
        else:
            # Decoded overflow can be detected before the compressed entity is
            # exhausted. Delivered wire bytes do not establish its completion.
            assert 0 < measurement['wire_bytes_delivered'] <= full_wire_bytes
    else:
        assert measurement['wire_bytes_delivered'] == observed
    assert max(measurement['read_amounts']) <= min(65536, budget + 1)


@_BOUNDED_CHEBI_CLIENT
@pytest.mark.parametrize('entry', ['search', 'compound'])
def test_bounded_chebi_error_retains_diagnostic_without_chemical_record_and_replays(tmp_path, monkeypatch, entry):
    body = b'{"engineering_control":"' + b'a' * 10000 + b'"}'
    client, measurement_path, _ = _controlled_bounded_rhea_client(tmp_path, monkeypatch, body,
        provider='chebi', budget=64)
    arguments = {'term': 'engineering byte-limit control', 'size': 2, 'page': 1} if entry == 'search' else {
        'accession': 'CHEBI:58297'}
    operation = 'public.chebi.' + entry
    store_path = tmp_path / 'store'
    with Store(store_path) as store:
        problem = store.create_problem(raw_sequence='MKWAA', molecule='protein')
        sources_before = store.list('source')
        result = ToolRegistry(store, clients=client).execute(operation, arguments, operation_key='chebi-byte-limit')
        assert result['status'] == 'failed' and result['feedback']['code'] == 'provider_response_byte_limit'
        diagnostic = json.loads(store.get_artifact(result['feedback']['diagnostic_ref']))
        assert diagnostic['service'] == 'chebi'
        assert store.get_artifact(diagnostic['content_ref']) == body[:64]
        response = diagnostic['transport']['response']
        assert response['status'] == 200 and response['body_complete'] is False
        assert response['body_capture_failure'] == 'provider_response_byte_limit'
        assert response['observed_body_bytes'] == 65 and response['retained_body_bytes'] == 64
        assert store.list('source') == sources_before and store.count('chemical_record') == 0
        assert store.count('observation') == store.count('assessment') == store.count('annotation') == 0
        assert store.problem() == problem
        measurement_before = measurement_path.read_bytes()
        frozen = deepcopy(result)
    def forbidden(*args, **kwargs):
        raise AssertionError('closed ChEBI byte-limit failure attempted another request')
    monkeypatch.setattr(client, 'chebi_' + entry, forbidden)
    with Store(store_path) as reopened:
        assert ToolRegistry(reopened, clients=client).execute(operation, arguments, operation_key='chebi-byte-limit') == frozen
        assert reopened.list('source') == sources_before and reopened.count('chemical_record') == 0
        assert measurement_path.read_bytes() == measurement_before
    measurement = json.loads(measurement_before)
    assert measurement['send_calls'] == 1 and measurement['wire_bytes_delivered'] == 65


@pytest.mark.skipif(os.environ.get('HMMER_NATIVE_ORACLE_CHEBI_LIVE') != '1',
    reason='requires explicit one-compound live ChEBI selection within bounded529')
def test_live_selected_chebi_compound_returns_actual_chemistry_through_scientific_child(tmp_path, monkeypatch):
    _selected_chebi_workflow_case(tmp_path, monkeypatch, operation='public.chebi.compound',
        arguments={'accession': os.environ['HMMER_NATIVE_ORACLE_CHEBI_ACCESSION']})


@pytest.mark.skipif(os.environ.get('HMMER_NATIVE_ORACLE_CHEBI_SEARCH_LIVE') != '1',
    reason='requires explicit one-page live ChEBI search selection within bounded529')
def test_live_selected_chebi_search_page_returns_source_summaries_through_scientific_child(tmp_path, monkeypatch):
    arguments = {'term': os.environ['HMMER_NATIVE_ORACLE_CHEBI_SEARCH_TERM'],
        'size': int(os.environ['HMMER_NATIVE_ORACLE_CHEBI_SEARCH_SIZE']),
        'page': int(os.environ['HMMER_NATIVE_ORACLE_CHEBI_SEARCH_PAGE'])}
    assert arguments == {'term': 'glutathione', 'size': 1, 'page': 1}
    _selected_chebi_workflow_case(tmp_path, monkeypatch, operation='public.chebi.search', arguments=arguments)


@pytest.mark.skipif(os.environ.get('HMMER_NATIVE_ORACLE_CHEBI_PAGE2_LIVE') != '1',
    reason='requires explicit caller-selected ChEBI page2 within bounded529')
def test_live_explicit_chebi_second_page_preserves_supplied_first_page(tmp_path, monkeypatch):
    arguments = {'term': os.environ['HMMER_NATIVE_ORACLE_CHEBI_SEARCH_TERM'],
        'size': int(os.environ['HMMER_NATIVE_ORACLE_CHEBI_SEARCH_SIZE']),
        'page': int(os.environ['HMMER_NATIVE_ORACLE_CHEBI_SEARCH_PAGE'])}
    assert arguments == {'term': 'glutathione', 'size': 1, 'page': 2}
    _selected_chebi_workflow_case(tmp_path, monkeypatch, operation='public.chebi.search', arguments=arguments,
        prior_search_capture=Path(os.environ['HMMER_NATIVE_ORACLE_CHEBI_PRIOR_SEARCH_CAPTURE']))


@pytest.mark.skipif(os.environ.get('HMMER_NATIVE_ORACLE_CHEBI_RETAINED_SEARCH_CONTROL') != '1',
    reason='requires explicit authentic231 supplied-and-returned identity control within bounded529')
def test_retained_chebi_search_preserves_supplied_record_ids_without_http(tmp_path, monkeypatch):
    prior = Path(os.environ['HMMER_NATIVE_ORACLE_CHEBI_PRIOR_SEARCH_CAPTURE'])
    _selected_chebi_workflow_case(tmp_path, monkeypatch, operation='public.chebi.search',
        arguments={'term': 'glutathione', 'size': 1, 'page': 1}, retained_capture=prior, prior_search_capture=prior)


@pytest.mark.skipif(not os.environ.get('HMMER_NATIVE_ORACLE_CHEBI_RETAINED_COMPOUND_CAPTURE'),
    reason='requires explicit authentic retained227 compound capture within bounded529')
def test_retained_chebi_compound_reuses_shared_workflow_without_http(tmp_path, monkeypatch):
    _selected_chebi_workflow_case(tmp_path, monkeypatch, operation='public.chebi.compound',
        arguments={'accession': 'CHEBI:58297'},
        retained_capture=Path(os.environ['HMMER_NATIVE_ORACLE_CHEBI_RETAINED_COMPOUND_CAPTURE']))


def _selected_chebi_workflow_case(tmp_path, monkeypatch, *, operation, arguments, retained_capture=None,
                                  prior_search_capture=None):
    """One shared ordinary Workflow and custody path for existing ChEBI requests.

    Previously acquired Rhea222 evidence is explicitly supplied to this fixture.
    That setup replays authentic bytes; it performs no new Rhea HTTP request.
    Retained modes replay227/231 rather than constructing PublicClients.
    Search summaries are not compound details or control-protein measurements.
    A supplied231 page is initial evidence, never new page2 acquisition credit.
    """
    import asyncio
    from importlib import import_module
    from urllib.parse import parse_qs, urlsplit
    from jsonschema import Draft202012Validator
    from method_loop.archive import iter_json
    from gene_annotation_episode import acquisition
    from gene_annotation_episode.chemistry import accession as canonical_accession
    from gene_annotation_episode.communication import plain, validate_closed_schema
    from gene_annotation_episode.episode_receipts import EpisodeReceipts
    from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
    from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
    from gene_annotation_episode.runtime import FACT_MEANINGS, FACT_SOURCES, Workflow
    from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
    from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding

    assert os.environ.get('HMMER529_ATTEMPT'), 'requires the selected bounded529 runtime'
    assert operation in {'public.chebi.compound', 'public.chebi.search'}
    search = operation == 'public.chebi.search'
    selected = None if search else canonical_accession(arguments['accession'], 'CHEBI')
    if not search:
        assert selected == 'CHEBI:58297'
        arguments = {'accession': selected}
    current_adapter_sha = hashlib.sha256(Path(acquisition.__file__).read_bytes()).hexdigest()
    prior_original = None
    if prior_search_capture is not None:
        assert search and prior_search_capture.is_absolute()
        prior_capture_bytes = prior_search_capture.read_bytes()
        assert hashlib.sha256(prior_capture_bytes).hexdigest() == \
            'bc80056259814a00d2316510bfd9d80bdd6b652cb3dd9838d6ddd3eb8841020d'
        prior_original = json.loads(prior_capture_bytes)
        assert prior_original['schema'] == 'chebi_live_search_workflow_verification_v1'
        assert prior_original['native_acquisition_verified'] and prior_original['typed_custody_verified']
        assert prior_original['replay_verified']
        assert prior_original['request'] == {'operation': 'public.chebi.search',
            'arguments': {'term': 'glutathione', 'size': 1, 'page': 1}}
        prior_body_path = Path(prior_original['native_body']['path'])
        prior_raw = prior_body_path.read_bytes()
        assert len(prior_raw) == prior_original['native_body']['size_bytes'] == 763
        assert hashlib.sha256(prior_raw).hexdigest() == prior_original['native_body']['sha256'] == \
            'b1ff0f43e06ae43aa1ed8ce303f21a127b2ff925ecff93ea7f2cc29d5176ec04'
        prior_records = {row['id']: row for row in [prior_original['source_record'],
            *prior_original['chemical_records'], *prior_original['chemical_references']]}
        assert set(prior_records) == set(prior_original['outcome']['record_refs'])
        assert len(prior_records) == 3
        if retained_capture is None:
            # This literal caller choice is independent of any prior host hint.
            assert arguments == {'term': 'glutathione', 'size': 1, 'page': 2}
    retained_original = None
    if retained_capture is not None:
        assert retained_capture.is_absolute()
        retained_capture_bytes = retained_capture.read_bytes()
        expected_capture_sha = ('bc80056259814a00d2316510bfd9d80bdd6b652cb3dd9838d6ddd3eb8841020d' if search else
            '32297152112a145a0afe3e5677f60615fd28195974e50a03420131616cee09d4')
        assert hashlib.sha256(retained_capture_bytes).hexdigest() == expected_capture_sha
        retained_original = json.loads(retained_capture_bytes)
        assert retained_original['schema'] == f'chebi_live_{"search" if search else "compound"}_workflow_verification_v1'
        assert retained_original['native_acquisition_verified'] and retained_original['typed_custody_verified']
        assert retained_original['replay_verified']
        assert retained_original['request'] == {'operation': operation, 'arguments': arguments}
        retained_body_path = Path(retained_original['native_body']['path'])
        retained_body = retained_body_path.read_bytes()
        expected_body_size = 763 if search else 4154
        expected_body_sha = ('b1ff0f43e06ae43aa1ed8ce303f21a127b2ff925ecff93ea7f2cc29d5176ec04' if search else
            '3faab919c1fd906796e8cb19078a8f0ab706cc7ffbd605b3469e6c8ce34b3f46')
        assert len(retained_body) == retained_original['native_body']['size_bytes'] == expected_body_size
        assert hashlib.sha256(retained_body).hexdigest() == retained_original['native_body']['sha256'] == expected_body_sha
        budget = retained_original['response_byte_limit']
        script = Path(retained_original['selected_client']['script'])
        script_sha = retained_original['selected_client']['sha256']
        adapter_sha = retained_original['selected_observer']['sha256']
    else:
        budget = int(os.environ['HMMER_NATIVE_ORACLE_CHEBI_RESPONSE_BYTE_LIMIT'])
        skill_root = Path(os.environ['HMMER_NATIVE_ORACLE_CHEBI_SKILL_ROOT']).resolve(strict=True)
        script = Path(os.environ['HMMER_NATIVE_ORACLE_CHEBI_CLIENT']).resolve(strict=True)
        assert script == (skill_root / 'skills/chebi-skill/scripts/rest_request.py').resolve(strict=True)
        script_sha = hashlib.sha256(script.read_bytes()).hexdigest()
        assert script_sha == os.environ['HMMER_NATIVE_ORACLE_CHEBI_CLIENT_SHA256']
        adapter_sha = current_adapter_sha
    assert budget == 8388608
    assert script_sha == '78ddae6460e3dd701cda67df4454532899d20851f8212a74ec8d5b6e2988b690'
    rhea_path = Path(os.environ['HMMER_NATIVE_ORACLE_CHEBI_RHEA_CAPTURE'])
    assert rhea_path.is_absolute()
    rhea_bytes = rhea_path.read_bytes()
    rhea_sha = hashlib.sha256(rhea_bytes).hexdigest()
    assert rhea_sha == '155e6367d3097c3ce7b0d87b23951c1d7529461ed5bc973f2c77d4acfe0eae9a'
    rhea = json.loads(rhea_bytes)
    rhea_body_path = Path(rhea['native_body']['path'])
    rhea_raw = rhea_body_path.read_bytes()
    assert hashlib.sha256(rhea_raw).hexdigest() == rhea['native_body']['sha256'] == \
        'f1d30a0e4783dcf4e36a7dedf0f6f43279355363da1df473540b716f0be375d9'
    selected_reference, = [row for row in rhea['chemical_references']
        if row['id'] == 'reference_00a46bd670fa7e93a87f187c']
    assert selected_reference['source_ref'] == rhea['source_record']['id']
    assert canonical_accession(selected_reference['accession'], 'CHEBI') == 'CHEBI:58297'
    associations = [{'reaction_ref': row['id'], 'reaction_accession': row['accession'],
        'source_ref': row['source_ref'], 'participant': participant}
        for row in rhea['reaction_records'] for participant in row['participants']
        if participant['chemical_ref'] == selected_reference['id']]
    assert len(associations) == 2
    assert {row['reaction_accession'] for row in associations} == {'RHEA:11740', 'RHEA:24424'}
    assert all(row['source_ref'] == rhea['source_record']['id']
        and row['participant']['source_accession'] == selected_reference['accession'] for row in associations)
    initial_records = {row['id']: row for row in [rhea['source_record'], *rhea['reaction_records'],
        *rhea['reaction_references'], *rhea['chemical_references']]}
    assert set(initial_records) == set(rhea['outcome']['record_refs'])
    G = import_module('verification.tool_graders_expression_nmf_episode_path_2026-10-27_490.fixture_helpers')
    publication = Path(__file__).resolve().parents[1] / 'research/slotted_process_library/publications/2026-10-24-001'
    mode = 'retained' if retained_original is not None else 'live'
    resource = 'search-page2' if prior_original is not None and retained_original is None else 'search' if search else 'compound'
    directory = tmp_path / f'{mode}-chebi-{resource}-workflow'
    directory.mkdir()
    store_path = directory / 'state'
    run_id = f'selected-{mode}-chebi-{resource}-workflow'
    evidence_path = Path(os.environ['HMMER529_ATTEMPT']) / f'chebi-{mode}-{resource}-workflow.json'
    qualification = (('Authentic retained ChEBI bytes/request/time/transport replay, without PublicClients or fresh '
        'ChEBI HTTP. ' if retained_original is not None else
        'One actual caller-selected public ChEBI request. ') +
        'Scripted ordinary nested scientific Workflow; caller-supplied Rhea222 mapping is retained-native '
        'replay only. Source chemistry and search summaries are distinct representations, not target '
        'measurements or confidence. Complete-body means only the selected HTTP entity, not a complete '
        'query population. Raw total/number_pages meanings and ranking semantics are not established here. '
        'No additional query/page, first-hit selection, ID substitution, target assignment or model edit.')
    report = {'schema': f'chebi_{mode}_{resource.replace("-", "_")}_workflow_verification_v1', 'qualification': qualification,
        'request': {'operation': operation, 'arguments': deepcopy(arguments)},
        'selected_client': {'script': str(script), 'sha256': script_sha}, 'response_byte_limit': budget,
        'selected_observer': {'module': 'gene_annotation_episode.acquisition', 'sha256': adapter_sha},
        'initial_rhea_capture': {'path': str(rhea_path), 'sha256': rhea_sha},
        'initial_rhea_native_body': deepcopy(rhea['native_body']),
        'selected_rhea_chemical_reference': selected_reference, 'selected_rhea_associations': associations,
        'initial_evidence_qualification': 'Explicit caller-supplied authentic222 retained mapping, '
            'not automatic runtime discovery, a fresh Rhea request or repair of its failed original harness/lifecycle.',
        'store_path': str(store_path), 'lookup_operation_key': None, 'outcome': None,
        'source_record': None, 'native_body': None, 'request_metadata': None, 'diagnostic': None,
        'chemical_records': [], 'chemical_references': [], 'model_calls': [],
        'native_acquisition_verified': False, 'retained_native_verified': False,
        'fresh_http_requested': retained_original is None, 'current_adapter_sha256': current_adapter_sha,
        'typed_custody_verified': False, 'replay_verified': False}
    if retained_original is not None:
        report['retained_lookup_input'] = {'path': str(retained_capture),
            'sha256': hashlib.sha256(retained_capture_bytes).hexdigest(),
            'original_operation_key': retained_original['lookup_operation_key'],
            'original_outcome_operation_ref': retained_original['outcome']['operation_ref']}
    if prior_original is not None:
        report['supplied_prior_search'] = {'path': str(prior_search_capture),
            'sha256': hashlib.sha256(prior_capture_bytes).hexdigest(),
            'request': prior_original['request'], 'source_record': prior_original['source_record'],
            'request_metadata': prior_original['request_metadata'], 'native_body': prior_original['native_body'],
            'chemical_records': prior_original['chemical_records'],
            'chemical_references': prior_original['chemical_references'],
            'qualification': 'Explicit supplied initial evidence from231; no page1 HTTP or new page2 contribution.'}

    def save_report():
        evidence_path.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')

    class RetainedRhea:
        def __init__(self):
            self.calls = []

        def rhea_search(self, query, limit=10):
            assert {'query': query, 'limit': limit} == rhea['request']['arguments']
            self.calls.append(deepcopy(rhea['request']))
            original = rhea['source_record']
            metadata = rhea['request_metadata']
            return SourceSnapshot('rhea', original['uri'], deepcopy(metadata['request']),
                original['retrieved_at'], rhea_raw, 'application/json', deepcopy(metadata['transport']))

    def controller(path, initial):
        # A fixture horizon chooses four scripted decisions, not a production
        # action limit, scientific stopping rule or measure of annotation value.
        horizon = 2 if len(path) == 2 else 1
        def estimate(raw, parameters, contexts):
            return YieldEstimate(len(raw), NumericBand.exact(0 if len(raw) >= horizon else 1),
                parameters, {'fixture': 'selected_chebi_source_custody_only'})
        return YieldController(str(path), initial, 0, YieldParameters(100, 50), estimate_with_context=estimate)

    class RetainedChebi:
        def __init__(self, captured, content):
            self.captured, self.content = captured, content
            self.calls = []

        def snapshot(self, selected_operation, selected_arguments):
            assert self.captured['request'] == {'operation': selected_operation, 'arguments': selected_arguments}
            self.calls.append({'operation': selected_operation, 'arguments': deepcopy(selected_arguments)})
            original = self.captured['source_record']
            metadata = self.captured['request_metadata']
            return SourceSnapshot('chebi', original['uri'], deepcopy(metadata['request']),
                original['retrieved_at'], self.content, 'application/json', deepcopy(metadata['transport']))

        def chebi_compound(self, accession):
            return self.snapshot('public.chebi.compound', {'accession': accession})

        def chebi_search(self, term, size=10, page=1):
            return self.snapshot('public.chebi.search', {'term': term, 'size': size, 'page': page})

    client = (RetainedChebi(retained_original, retained_body) if retained_original is not None else
        PublicClients(ncbi_email=None, skill_root=skill_root, chebi_response_byte_limit=budget))
    save_report()
    with Store(store_path) as store:
        problem = store.create_problem(raw_sequence='MKWAA', molecule='protein')
        scope = store.validate_scope()
        retained = RetainedRhea()
        setup = ToolRegistry(store, clients=retained).execute('public.rhea.search', rhea['request']['arguments'],
            operation_key='caller-supplied-retained-rhea222-for-chebi')
        assert setup['status'] == 'completed' and retained.calls == [rhea['request']]
        assert {ref: store.get(ref) for ref in initial_records} == initial_records
        assert store.count('chemical_record') == 0
        report['retained_rhea_setup'] = {'outcome': setup, 'snapshot_calls': retained.calls,
            'original_request_metadata': rhea['request_metadata'],
            'original_retrieved_at': rhea['source_record']['retrieved_at']}
        if prior_original is not None:
            supplied = RetainedChebi(prior_original, prior_raw)
            prior_setup = ToolRegistry(store, clients=supplied).execute('public.chebi.search',
                deepcopy(prior_original['request']['arguments']), operation_key='caller-supplied-retained-chebi231-page1')
            assert prior_setup['status'] == 'completed' and supplied.calls == [prior_original['request']]
            assert {ref: store.get(ref) for ref in prior_records} == prior_records
            initial_records.update(prior_records)
            assert len(initial_records) == 15
            report['supplied_prior_search']['setup_outcome'] = prior_setup
            report['supplied_prior_search']['retained_snapshot_calls'] = supplied.calls
        else:
            assert len(initial_records) == 12
        baseline_chemicals = {row['id'] for row in initial_records.values() if row['record_type'] == 'chemical_record'}
        assert store.count('chemical_record') == len(baseline_chemicals)
        assert {ref: store.get(ref) for ref in initial_records} == initial_records
        report['initial_evidence_refs'] = list(initial_records)
        save_report()
        tools = ToolRegistry(store, clients=client)
        binding = prepare_scientific_binding(run_directory=directory / 'run', source_directory=publication,
            tool_catalog=tools.catalog(), child_roles=('scientific_process',))
        library = ScientificProcessLibrary(directory / 'run/scientific-process-library')
        axis, pattern = library.reference('A110'), library.reference('P10')
        assert library.resolve(axis)['name'] == 'Biochemical feasibility and chemical/resource accounting'
        assert library.resolve(pattern)['name'] == 'Account for the coupled chemical system'
        assert 'committed_record_refs' in FACT_SOURCES
        assert FACT_MEANINGS['committed_record_refs'] == \
            'Semantic records returned by completed own work and completed child investigations.'
        form = validate_closed_schema({'type': 'object', 'additionalProperties': False,
            'required': ['chemical_detail_refs'], 'properties': {'chemical_detail_refs': {
                'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference'},
                'x-source': 'committed_record_refs'}}})

        def assignment(owner, selected_tools):
            return {'selection': {'version': 'scientific_process_selection_v3', 'evidence_axis': axis,
                'thought_pattern': pattern, 'child_tool_info': selected_tools},
                'evidence_refs': [*scope['subject_refs'], selected_reference['id']], 'constraints': {},
                'context': {'fixture_owner': owner, 'acquisition_qualification': qualification,
                    'retained_rhea_source_ref': rhea['source_record']['id'],
                    'selected_chemical_reference': selected_reference['id'],
                    'selected_resource_request': {'operation': operation, 'arguments': deepcopy(arguments)},
                    **({'supplied_prior_search_source_ref': prior_original['source_record']['id'],
                        'page_selection_qualification': 'The caller explicitly selects the supplied request; '
                            'a prior host hint does not dispatch it. Prior-page evidence is already supplied.'}
                        if prior_original is not None else {}),
                    'chemical_question': 'What chemical source records does the explicitly selected request '
                        'return for investigating the supplied reaction account? Preserve search summaries '
                        'as summaries, reported page metadata as source values and unresolved identity.',
                    'control_material_interpretation': 'Engineering scope only; no function or reaction '
                        'correspondence of the control protein MKWAA is asserted.'}}

        parent_assignment = assignment('chemical_parent', [{'name': 'state.query', 'resources': 'local'}])
        child_assignment = assignment('chemical_lookup', [{'name': name, 'resources': resource}
            for name, resource in ((operation, 'api'), ('state.query', 'local'), ('source.read', 'local'))])

        def capture_lookup(episode_id):
            row = flow.journal.row('runtime_actions', episode_id, 0)
            assert row is not None and row['result'] is not None
            actual = json.loads(row['result'])
            report['lookup_operation_key'] = f'{run_id}:{episode_id}:0'
            report['outcome'] = actual
            save_report()
            records = [store.get(ref) for ref in actual.get('record_refs', [])]
            sources = [record for record in records if record['record_type'] == 'source' and record['provider'] == 'chebi']
            report['chemical_records'] = [record for record in records if record['record_type'] == 'chemical_record']
            report['chemical_references'] = [record for record in records if record['record_type'] == 'reference']
            if sources:
                assert len(sources) == 1
                source = sources[0]
                report['source_record'] = source
                raw = store.get_artifact(source['artifact_ref'])
                sha = hashlib.sha256(raw).hexdigest()
                report['native_body'] = {'artifact_ref': source['artifact_ref'],
                    'path': str(store.path / 'artifacts' / sha[:2] / sha), 'sha256': sha, 'size_bytes': len(raw)}
                report['request_metadata'] = json.loads(store.get_artifact(source['request_ref']))
                if search:
                    try:
                        document = json.loads(raw)
                    except (ValueError, UnicodeError) as error:
                        report['native_search_metadata'] = {'native_json_parse_error': type(error).__name__,
                            'qualification': 'Native bytes retained; page/population meanings unknown.'}
                    else:
                        report['native_search_metadata'] = {
                            'total': document.get('total') if isinstance(document, dict) else None,
                            'number_pages': document.get('number_pages') if isinstance(document, dict) else None,
                            'field_presence': {key: key in document if isinstance(document, dict) else None
                                for key in ('total', 'number_pages')},
                            'qualification': 'Raw native field values only; population and continuation meanings unknown.'}
            else:
                diagnostic_ref = (actual.get('feedback') or {}).get('diagnostic_ref')
                if diagnostic_ref is not None:
                    diagnostic = json.loads(store.get_artifact(diagnostic_ref))
                    report['diagnostic'] = diagnostic
                    if diagnostic.get('content_ref') is not None:
                        raw = store.get_artifact(diagnostic['content_ref'])
                        sha = hashlib.sha256(raw).hexdigest()
                        report['native_body'] = {'artifact_ref': diagnostic['content_ref'],
                            'path': str(store.path / 'artifacts' / sha[:2] / sha), 'sha256': sha,
                            'size_bytes': len(raw), 'qualification': 'diagnostic_only_not_a_chemical_record'}
                    report['request_metadata'] = diagnostic
            if prior_original is not None:
                prior_document = chebi_response(prior_raw, search=True)
                selected_document = None
                if report['native_body'] is not None:
                    selected_bytes = store.get_artifact(report['native_body']['artifact_ref'])
                    try:
                        selected_document = json.loads(selected_bytes)
                    except (ValueError, UnicodeError):
                        pass  # Exact failure bytes and diagnostic remain retained.
                prior_arguments = prior_original['request']['arguments']
                request_delta = {key: {'prior': prior_arguments.get(key), 'selected': arguments.get(key)}
                    for key in prior_arguments.keys() | arguments.keys() if prior_arguments.get(key) != arguments.get(key)}
                report['host_page_comparison'] = {
                    'qualification': 'Host verification metadata only, not selected-action evidence or credit. '
                        'Each page retains its own source/time/transport and ordered native rows, including '
                        'duplicates. No distinct-ID, equal-total, stable-order, disjointness, exhaustive-query '
                        'or unspecified population/rank interpretation is required. The new request is a '
                        'literal caller selection, never automatic dispatch of an earlier host hint.',
                    'literal_request_delta': request_delta,
                    'prior_page': {'request': prior_original['request'],
                        'source_record': prior_original['source_record'],
                        'request_metadata': prior_original['request_metadata'],
                        'native_body': prior_original['native_body'],
                        'ordered_native_rows': prior_document['results'],
                        'raw_total': prior_document.get('total'), 'raw_number_pages': prior_document.get('number_pages'),
                        'chemical_records': prior_original['chemical_records'],
                        'chemical_references': prior_original['chemical_references']},
                    'selected_page': {'request': {'operation': operation, 'arguments': deepcopy(arguments)},
                        'source_record': report['source_record'], 'request_metadata': report['request_metadata'],
                        'native_body': report['native_body'],
                        'ordered_native_rows': selected_document.get('results') if isinstance(selected_document, dict) else None,
                        'raw_total': selected_document.get('total') if isinstance(selected_document, dict) else None,
                        'raw_number_pages': selected_document.get('number_pages') if isinstance(selected_document, dict) else None,
                        'chemical_records': report['chemical_records'], 'chemical_references': report['chemical_references']}}
            save_report()  # Preserve actual provider/parser failure before further assertions.
            return actual

        class Choices:
            def __init__(self):
                self.calls, self.turns, self.episodes = [], {}, {}
                self.returned = None
                self.baseline_receipts = {}

            async def complete(self, episode_id, role, instructions, current, schema):
                self.turns[episode_id] = self.turns.get(episode_id, 0) + 1
                turn = self.turns[episode_id]
                scientific = current.get('scientific_process')
                owner = 'annotation' if scientific is None else scientific['assignment']['context']['fixture_owner']
                self.episodes[owner] = episode_id
                if turn == 1:
                    self.baseline_receipts[owner] = {row['record_ref']: dict(row) for row in store.db.execute(
                        'SELECT record_ref,receipt_kind,source_index FROM runtime_record_receipts '
                        'WHERE run_id=? AND episode_id=?', (run_id, episode_id))}
                self.calls.append({'episode_id': episode_id, 'owner': owner,
                    'instructions': instructions, 'context': deepcopy(plain(current))})
                report['model_calls'] = self.calls
                save_report()
                if owner == 'chemical_parent' and turn == 2:
                    actual = capture_lookup(self.episodes['chemical_lookup'])
                    assert actual['status'] == 'completed', actual
                assert not current.get('feedback'), current.get('feedback')
                if owner == 'annotation':
                    assert turn == 1
                    answer = G.commission('scientific_process', parent_assignment, scope, form,
                        objective='Investigate the caller-selected chemical resource question and retain '
                            'actual source records, query scope and unknowns without assigning target activity.')
                elif owner == 'chemical_parent' and turn == 1:
                    assert selected_reference['id'] in set(flow.receipts.known(episode_id))
                    answer = G.commission('scientific_process', child_assignment, scope, form,
                        objective='Investigate chemical source information using the supplied resource '
                            'request; preserve all returned records and the limited meaning of search summaries.')
                elif owner == 'chemical_lookup':
                    assert turn == 1 and {row['id'] for row in store.list('chemical_record', limit=2**31 - 1)} == baseline_chemicals
                    info = {row['name']: row for row in scientific['child_tool_info']}[operation]
                    assert info['resources'] == 'api' and info['description'] and info['instructions']
                    assert operation in {row['name'] for row in current['tools']}
                    answer = G.action(operation, deepcopy(arguments))
                else:
                    assert owner == 'chemical_parent' and turn == 2
                    self.returned = deepcopy(plain(current['child_reports'][-1]))
                    assert self.returned == {'chemical_detail_refs': report['outcome']['record_refs']}
                    assert set(self.returned['chemical_detail_refs']) <= set(flow.receipts.known(episode_id))
                    assert not (set(self.returned['chemical_detail_refs']) - set(initial_records)).intersection(
                        flow.receipts.known(self.episodes['annotation']))
                    answer = G.action('state.query', {'refs': self.returned['chemical_detail_refs']})
                if answer['selection']['kind'] == 'episode_child':
                    answer['selection']['purpose'] = ('Return the actual acquired chemical source, structured '
                        'detail and reference identities. Custody is not target activity, physiological use or a score.')
                assert answer['report_update'] == {}
                answer = G.provider_value(plain(answer), plain(schema))
                Draft202012Validator(plain(schema)).validate(answer)
                return answer

            async def release(self, episode_id):
                pass

        provider = Choices()
        flow = Workflow(store, tools, provider, directory / 'run', run_id,
            controller_factory=controller, project_credit=lambda *_args, **_kwargs: 0,
            annotation_child_roles=('scientific_process',), episode_record_receipts=True,
            initial_known_record_refs=list(initial_records), episode_binding_descriptors=(binding,))

        async def run():
            root = flow.build('annotation', 'root', 'Retain source chemistry for the selected participant '
                'of the supplied reaction account without inferring control-protein function', scope)
            record = await root.run_async(flow.context)
            await root.build_result(record)
            return record

        record = asyncio.run(run())
        archive = json.loads(''.join(iter_json(record.as_record())))
        assert len(provider.calls) == 4 and provider.turns == {
            provider.episodes['annotation']: 1, provider.episodes['chemical_parent']: 2,
            provider.episodes['chemical_lookup']: 1}
        actual = report['outcome']
        assert actual['status'] == 'completed' and actual['result']['projection_errors'] == []
        if not search:
            assert actual['result']['requested_accession'] == selected
            assert actual['result']['returned_accessions'] == [selected] and actual['result']['exact_accession_match'] is True
        assert actual['result']['target_annotation'] == 'not_performed'
        assert actual['result']['thermodynamics_or_physiological_flux'] == 'not_inferred'
        source = report['source_record']
        chemicals = report['chemical_records']
        references = report['chemical_references']
        if not search:
            assert len(chemicals) == len(references) == 1 and chemicals[0]['accession'] == selected
        by_native = {reference['native_record_ref']: reference for reference in references}
        assert len(by_native) == len(references) == len(chemicals)
        for chemical in chemicals:
            reference = by_native[chemical['id']]
            assert reference['reference_type'] == 'chemical' and reference['accession'] == chemical['accession']
            assert chemical['source_ref'] == reference['source_ref'] == source['id']
            assert reference['id'] != selected_reference['id'] and store.coverage(reference['id']) == []
            assert chemical['representation'] == ('search_summary' if search else 'compound_detail')
        assert source['id'] != rhea['source_record']['id']
        raw = store.get_artifact(source['artifact_ref'])
        native = chebi_response(raw, search=search)
        native_rows = native['results'] if search else [native]
        expected_rows = [chemical_row(row, search=search) for row in native_rows]
        fields = set().union(*(row.keys() for row in expected_rows))
        serialized = lambda value: json.dumps(value, sort_keys=True, allow_nan=False)
        projected = [{key: row[key] for key in fields} for row in chemicals]
        assert {serialized(row) for row in projected} == {serialized(row) for row in expected_rows}
        assert actual['result']['provider_returned_row_count'] == len(native_rows)
        assert actual['result']['projected_record_count'] == len(expected_rows)
        for row, expected_row in zip(native_rows, expected_rows):
            source_row = row['_source'] if search else row
            matching = [chemical for chemical in chemicals if all(chemical[key] == value for key, value in expected_row.items())]
            assert len(matching) == 1
            chemical = matching[0]
            assert chemical['accession'] == canonical_accession(source_row['chebi_accession'], 'CHEBI')
            data = source_row if search else source_row.get('chemical_data') or {}
            for field, source_field in (('formula', 'formula'), ('charge', 'charge'), ('mass', 'mass'),
                    ('monoisotopic_mass', 'monoisotopicmass' if search else 'monoisotopic_mass')):
                assert chemical[field] == data.get(source_field)
            assert chemical['source_name'] == source_row['name']
            assert chemical['source_definition'] == source_row.get('definition')
            if search:
                assert chemical['ontology_relations'] == []
        if search:
            # These are raw native field values. No primary contract supplied
            # their population, bound, sorting or cross-page version meanings.
            report['native_search_metadata'] = {'total': native.get('total'),
                'number_pages': native.get('number_pages'),
                'field_presence': {key: key in native for key in ('total', 'number_pages')},
                'requested_window': deepcopy(arguments), 'returned_row_count': len(native_rows),
                'unprojected_hit_fields': [{key: value for key, value in row.items() if key != '_source'} for row in native_rows],
                'host_next_query': deepcopy(actual['result']['next_query']),
                'qualification': 'Raw total/number_pages population meanings are not established. '
                    'The existing importer derives a host hint from caller.page and exact-int number_pages; '
                    'this is not validated provider continuation. No next page/query is executed. '
                    'Ranking fields are source metadata, not annotation confidence. Complete HTTP entity '
                    'capture is separate from query-population completeness or exhaustive absence.'}
            save_report()
            assert actual['result']['native_total'] == native.get('total')
            assert actual['result']['native_page_count'] == native.get('number_pages')
            assert actual['result']['page'] == arguments['page']
            pages = native.get('number_pages')
            host_hint = {**arguments, 'page': arguments['page'] + 1} if type(pages) is int and arguments['page'] < pages else None
            assert actual['result']['next_query'] == host_hint
        metadata = report['request_metadata']
        assert metadata['request'] == arguments
        transport = metadata['transport']
        assert transport['script'] == str(script) and transport['script_sha256'] == script_sha
        assert transport['representation'] == 'http_entity_bytes_via_installed_client'
        observer = transport['observer']
        assert observer['adapter_sha256'] == adapter_sha and observer['response_byte_limit'] == budget
        assert observer['stream'] is True and observer['automatic_redirects'] is observer['redirect_preparation'] is False
        response = transport['response']
        assert response['status'] == 200 and response['request_method'] == 'GET'
        assert response['headers'] and 'x-engineering-control' not in response['headers']
        url = urlsplit(response['url'])
        assert (url.scheme, url.netloc) == ('https', 'www.ebi.ac.uk')
        if search:
            assert url.path == '/chebi/backend/api/public/es_search/'
            assert parse_qs(url.query) == {key: [str(value)] for key, value in arguments.items()}
        else:
            assert (url.path, url.query) == ('/chebi/backend/api/public/compound/CHEBI:58297/', '')
        assert response['body_complete'] is response['body_capture_finalized'] is True
        assert response['observed_body_bytes'] == response['retained_body_bytes'] == response['total_body_bytes'] == len(raw)
        assert response['response_byte_limit'] == budget and 0 < len(raw) <= budget
        assert response.get('body_capture_failure') is None
        assert source['retrieved_at'] and source['version'] is None
        assert Path(report['native_body']['path']).read_bytes() == raw
        if retained_original is None:
            assert hashlib.sha256(script.read_bytes()).hexdigest() == script_sha
        report['native_acquisition_verified'] = retained_original is None
        report['retained_native_verified'] = retained_original is not None
        save_report()

        returns = EpisodeReturnRecords(store, run_id, failure_prefix='chebi_workflow_')
        root_context = returns.context(record.episode_id)
        parent_context, parent_form, parent_schema = returns._attempt(root_context, 0)
        child_context, child_form, child_schema = returns._attempt(parent_context, 0)
        assert parent_schema == child_schema == form
        assert parent_form == child_form == provider.returned == {'chemical_detail_refs': actual['record_refs']}
        assert parent_context.episode_id == provider.episodes['chemical_parent']
        assert child_context.episode_id == provider.episodes['chemical_lookup']
        for owner, context, count, kind in (('annotation', root_context, 1, 'child_form'),
                ('chemical_parent', parent_context, 2, 'child_form'), ('chemical_lookup', child_context, 1, 'own_action')):
            delivered = set(actual['record_refs'])
            assert delivered <= set(flow.receipts.known(context.episode_id))
            rows = list(store.db.execute('SELECT record_ref,receipt_kind,source_index FROM runtime_record_receipts '
                'WHERE run_id=? AND episode_id=? AND record_ref IN (SELECT value FROM json_each(?))',
                (run_id, context.episode_id, json.dumps(actual['record_refs']))))
            assert len(rows) == len(delivered)
            for row in rows:
                baseline = provider.baseline_receipts[owner].get(row['record_ref'])
                if baseline is not None:
                    assert dict(row) == baseline
                else:
                    assert row['receipt_kind'] == kind and row['source_index'] == 0
            observed = list(store.db.execute('SELECT observation FROM runtime_observations WHERE run_id=? '
                'AND episode_id=?', (run_id, context.episode_id)))
            assert len(observed) == count
            assert all(json.loads(row['observation'])['credit']['credit'] == 0 for row in observed)
        for context in (parent_context, child_context):
            saved = flow.journal.row('runtime_forms', context.episode_id)
            assert json.loads(saved['facts'])['committed_record_refs'] == actual['record_refs']
            assert json.loads(saved['facts'])['interpretations'] == {}
            assert json.loads(saved['form']) == parent_form
        read = json.loads(flow.journal.row('runtime_actions', parent_context.episode_id, 1)['result'])
        acquired = {row['id']: row for row in [source, *chemicals, *references]}
        assert read['status'] == 'completed' and {row['id']: row for row in read['result']['records']} == acquired
        assert set(actual['record_refs']) == set(acquired)
        if retained_original is not None:
            original_records = {row['id']: row for row in [retained_original['source_record'],
                *retained_original['chemical_records'], *retained_original['chemical_references']]}
            assert acquired == original_records
            assert metadata == retained_original['request_metadata'] and raw == retained_body
            assert client.calls == [{'operation': operation, 'arguments': arguments}]
            assert report['lookup_operation_key'] != retained_original['lookup_operation_key']
            assert actual['operation_ref'] != retained_original['outcome']['operation_ref']
            report['retained_snapshot_calls'] = client.calls
        assert {ref: store.get(ref) for ref in initial_records} == initial_records
        assert store.problem() == problem
        assert store.count('observation') == store.count('assessment') == store.count('annotation') == 0
        known_before = {owner: list(flow.receipts.known(episode)) for owner, episode in provider.episodes.items()}
        report.update(typed_custody_verified=True, episodes=provider.episodes, automatic_return=parent_form,
            parent_selected_read=read, known_record_refs=known_before, archive=archive,
            evidence_axis={'reference': axis, 'name': library.resolve(axis)['name']},
            thought_pattern={'reference': pattern, 'name': library.resolve(pattern)['name']})
        frozen = deepcopy(actual)
        save_report()

    def forbidden(*args, **kwargs):
        raise AssertionError('closed selected ChEBI operation attempted another request')

    monkeypatch.setattr(client, 'chebi_search' if search else 'chebi_compound', forbidden)
    with Store(store_path) as reopened:
        replay = ToolRegistry(reopened, clients=client).execute(operation, deepcopy(arguments),
            scope=scope, operation_key=report['lookup_operation_key'])
        assert replay == {key: value for key, value in frozen.items() if key != 'pending_work_after_action'}
        assert {ref: reopened.get(ref) for ref in acquired} == acquired
        assert reopened.get_artifact(source['artifact_ref']) == raw
        assert json.loads(reopened.get_artifact(source['request_ref'])) == metadata
        receipts = EpisodeReceipts(reopened, run_id)
        assert {owner: list(receipts.known(episode)) for owner, episode in provider.episodes.items()} == known_before
        assert reopened.count('observation') == reopened.count('assessment') == reopened.count('annotation') == 0
    assert rhea_path.read_bytes() == rhea_bytes and rhea_body_path.read_bytes() == rhea_raw
    if retained_original is not None:
        assert retained_capture.read_bytes() == retained_capture_bytes and retained_body_path.read_bytes() == retained_body
    if prior_original is not None:
        assert prior_search_capture.read_bytes() == prior_capture_bytes and prior_body_path.read_bytes() == prior_raw
    report['replay_verified'] = True
    save_report()
