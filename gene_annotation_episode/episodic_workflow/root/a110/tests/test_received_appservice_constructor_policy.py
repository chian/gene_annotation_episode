"""Real constructor policy with controlled adapter binding; no scientific call.

Adapter source identity has its own independent tests. This fixture records the
constructor's original adapter binding effect while exercising real contract,
endpoint, authorization, callback and saved-metadata validation.
"""
from copy import deepcopy

import pytest

from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies import api_bvbrc_appservice
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies import bvbrc_appservice_adapters


def configuration():
    return {'kind':'api','service':'bvbrc_appservice',
        'execution_contract':'bvbrc_appservice_execution_v1',
        'endpoints':{'AppService':'https://p3.theseed.org/services/app_service',
                     'Workspace':'https://p3.theseed.org/services/Workspace'},
        'scientific_adapters':[],'timeout':7}


def test_received_configuration_preserves_callback_metadata_and_binding(monkeypatch):
    config=configuration()
    before=deepcopy(config)
    calls=[]
    bound={}
    def bind(rows,**kwargs):
        calls.append((deepcopy(rows),kwargs))
        return bound
    monkeypatch.setattr(bvbrc_appservice_adapters,'bind_adapters',bind)
    callback=lambda *args:None
    service=api_bvbrc_appservice.BVBRCAppServiceService(None,configuration=config,
        publication_callback=callback,_received_configuration=True)
    assert service.configuration==before and config==before
    assert service.publication_callback is callback
    assert service.scientific_adapters is bound
    assert len(calls)==1 and calls[0][0]==[]
    assert not hasattr(service.client,'timeout')
    assert not hasattr(service.client,'timeout_seconds')


def test_direct_fresh_constructor_preserves_current_rejection_before_binding(monkeypatch):
    calls=[]
    monkeypatch.setattr(bvbrc_appservice_adapters,'bind_adapters',lambda *args,**kwargs:calls.append(args))
    config=configuration()
    before=deepcopy(config)
    with pytest.raises(ContractError,match='^transport_timeout_configuration_not_supported$'):
        api_bvbrc_appservice.BVBRCAppServiceService(None,configuration=config)
    assert not calls and config==before


def test_received_constructor_preserves_invalid_callback_failure_before_binding(monkeypatch):
    calls=[]
    monkeypatch.setattr(bvbrc_appservice_adapters,'bind_adapters',lambda *args,**kwargs:calls.append(args))
    with pytest.raises(ContractError,match='^appservice_publication_callback_invalid$'):
        api_bvbrc_appservice.BVBRCAppServiceService(None,configuration=configuration(),
            publication_callback=object(),_received_configuration=True)
    assert not calls
