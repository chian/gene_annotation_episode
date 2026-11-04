"""A contract helper exposes only the explicitly installed local adapter."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from gene_annotation_episode.bvbrc_appservice_adapters import bind_adapters
from gene_annotation_episode import bvbrc_rnaseq_bundle_adapter as rnaseq
from gene_annotation_episode.domain import ContractError, validate_schema
from gene_annotation_episode.intervention_execution import contract_catalog, prepare_analysis_contract
from test_intervention_analysis import arguments


def fixture():
    service = SimpleNamespace(service="bvbrc_appservice", scientific_adapters=bind_adapters([
        dict(adapter_id="bvbrc_rnaseq", adapter_version="1", implementation_sha256=rnaseq.implementation_sha256())]))
    binding = SimpleNamespace(api_execution=SimpleNamespace(services={"analysis":service}))
    registry = SimpleNamespace(roles=("launch", "results"), for_role=lambda _: binding)
    services = SimpleNamespace(workflow=SimpleNamespace(episode_bindings=registry))
    native = arguments("RNASeq")
    args = dict(resource_id="analysis", parameters=native["parameters"], fields=[dict(field=name,
        selection=node["x-bvbrc-intervention-selection"])
        for name, node in native["requested_form"]["properties"].items()])
    return services, args, native


def test_bound_contract_builds_native_selection_without_service_io(monkeypatch):
    monkeypatch.setattr("socket.create_connection", lambda *a, **k: pytest.fail("unexpected network"))
    services, args, native = fixture()
    validate_schema(args, contract_catalog(services)[0]["input_schema"])
    before = deepcopy(args)
    result = prepare_analysis_contract(services, args)
    assert result["requested_schema"] == native["requested_form"]
    assert result["adapter"]["parameters"] == native["parameters"]
    assert result["service_availability"] == "not_observed" and args == before


def test_unbound_resources_adapters_and_documents_remain_unavailable():
    assert contract_catalog(SimpleNamespace()) == []
    services, args, _ = fixture()
    with pytest.raises(ContractError, match="execution_unbound"):
        prepare_analysis_contract(services, {**args, "resource_id":"unconfigured"})
    args["parameters"]["application_id"] = "TnSeq"
    with pytest.raises(ContractError, match="adapter_unbound"):
        prepare_analysis_contract(services, args)
    args["parameters"]["application_id"] = "RNASeq"
    args["fields"][0]["selection"]["document_id"] = "undeclared"
    with pytest.raises(ContractError, match="selected_document_unbound"):
        prepare_analysis_contract(services, args)
