"""Native-source replays/fixtures and an explicitly opted-in bounded live lookup."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.acquisition import AcquisitionError, PublicClients
from gene_annotation_episode.chemistry import rhea_equation
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.tool_registry import ToolRegistry


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


@pytest.mark.parametrize('limit', [True, False, 0, -1, None, 1.5])
def test_chebi_response_byte_limit_requires_positive_integer(limit):
    with pytest.raises(ValueError, match='invalid_chebi_response_byte_limit'):
        PublicClients(ncbi_email=None, chebi_response_byte_limit=limit)


