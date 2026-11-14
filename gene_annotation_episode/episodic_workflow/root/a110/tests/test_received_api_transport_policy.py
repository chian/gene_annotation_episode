"""Controlled real A110 constructors/transports; no provider request is sent.

Candidate tests only until the owning Fourth session stages the authenticated
source composition. Every network boundary in the transport cases is replaced
before invoking the real implementation. Saved inputs remain unchanged.
"""
from copy import deepcopy
from types import SimpleNamespace
import urllib.error

import pytest

from gene_annotation_episode.episodic_workflow.root.a110.acquisition import AcquisitionError
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies import api_bvbrc
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies import api_services
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies import bvbrc_analysis_transport
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies import rfam_batch_transport


@pytest.mark.parametrize('service,extra',[
    ('bvbrc_data',{'base_url':'https://www.bv-brc.org/api'}),
    ('bvbrc_minhash',{'endpoint':'https://p3.theseed.org/services/minhash_service'}),
    ('rfam_batch',{}),
])
def test_received_configuration_retains_literal_metadata_and_fresh_rejects(service,extra):
    original={'kind':'api','service':service,'timeout':7,**extra}
    before=deepcopy(original)
    tools=SimpleNamespace(clients=SimpleNamespace(timeout=19))
    received=api_services.build_received_service(service,original,tools)
    assert received.configuration==before
    assert original==before
    assert not hasattr(received.client,'timeout')
    assert not hasattr(received.client,'timeout_seconds')
    with pytest.raises(ValueError,match='^transport_timeout_configuration_not_supported$'):
        api_services.build_service(service,original,tools)
    assert original==before


@pytest.mark.parametrize('service,extra,error,code',[
    ('bvbrc_data',{},ContractError,'bvbrc_invalid_timeout'),
    ('bvbrc_minhash',{'endpoint':'https://p3.theseed.org/services/minhash_service'},ValueError,'bvbrc_native_timeout_invalid'),
    ('rfam_batch',{},ValueError,'api_service_configuration_invalid'),
])
@pytest.mark.parametrize('invalid',[0,True,'7'])
def test_received_invalid_timeout_metadata_keeps_original_failure(service,extra,error,code,invalid):
    original={'kind':'api','service':service,'timeout':invalid,**extra}
    before=deepcopy(original)
    with pytest.raises(error,match='^'+code+'$'):
        api_services.build_received_service(service,original,SimpleNamespace(clients=SimpleNamespace(timeout=19)))
    assert original==before


def test_received_native_metadata_does_not_reorder_endpoint_and_value_failures():
    metadata={'timeout':False}
    with pytest.raises(ValueError,match='^bvbrc_native_endpoints_required$'):
        bvbrc_analysis_transport.BVBRCAnalysisClient({},_saved_transport_metadata=metadata)
    with pytest.raises(ValueError,match='^bvbrc_native_timeout_invalid$'):
        bvbrc_analysis_transport.BVBRCAnalysisClient(
            {'Minhash':'https://p3.theseed.org/services/minhash_service'},
            authorization_env='invalid-env',_saved_transport_metadata=metadata)
    assert metadata=={'timeout':False}


@pytest.mark.parametrize('native_failure,expected_code',[
    (urllib.error.URLError('controlled_unavailable'),'provider_connection_failed'),
    (TimeoutError('native_provider_timeout'),'provider_request_timeout'),
])
def test_data_transport_keeps_native_failures_without_application_deadline(monkeypatch,native_failure,expected_code):
    calls=[]
    def opened(request,**kwargs):
        calls.append((request,kwargs))
        raise native_failure
    monkeypatch.setattr(api_bvbrc.urllib.request,'build_opener',lambda *handlers:SimpleNamespace(open=opened))
    client=api_bvbrc.BVBRCDataClient(_saved_transport_metadata={'timeout':7})
    with pytest.raises(AcquisitionError) as error:
        client._query_once({'controlled_operand':'unchanged'},'https://www.bv-brc.org/api/genome',{})
    assert error.value.code==expected_code
    assert len(calls)==1 and calls[0][1]=={}


def test_rfam_connection_preserves_fixed_origin_without_application_deadline(monkeypatch):
    calls=[]
    sentinel=object()
    def connected(*args,**kwargs):
        calls.append((args,kwargs))
        return sentinel
    monkeypatch.setattr(rfam_batch_transport.http.client,'HTTPSConnection',connected)
    client=rfam_batch_transport.RfamBatchHTTP(_saved_transport_metadata={'timeout_seconds':7})
    assert client._connection() is sentinel
    assert calls==[(('batch.rfam.org',),{})]


def test_received_rfam_metadata_keeps_original_constructor_failure():
    with pytest.raises(ValueError,match='^rfam_transport_timeout_invalid$'):
        rfam_batch_transport.RfamBatchHTTP(_saved_transport_metadata={'timeout_seconds':None})
