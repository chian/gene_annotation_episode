"""Native UniProt protocol fixtures; no model or network requests."""
import json

import pytest

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.api_services import build_service
from gene_annotation_episode.api_uniprot import UniProtService
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


def response(body, request, *, next_cursor=None):
    headers = {"x-total-results": "2", "x-uniprot-release": "fixture-release"}
    if next_cursor is not None:
        headers["link"] = '<https://rest.uniprot.org/uniprotkb/search?cursor=' + next_cursor + '>; rel="next"'
    return SourceSnapshot("uniprot", "https://rest.uniprot.org/uniprotkb/search", request,
        "2026-10-23T00:00:00+00:00", json.dumps(body).encode(), "application/json",
        {"response": {"status": 200, "headers": headers}})


def protein(accession="P12345"):
    return {"primaryAccession": accession, "sequence": {"value": "MACDEFGH"},
        "organism": {"taxonId": 83333, "scientificName": "Reference organism"},
        "proteinDescription": {"recommendedName": {"fullName": {"value": "Source annotation"}}}}


class Client:
    def __init__(self):
        self.calls = []

    def uniprot_record(self, accession):
        self.calls.append(("record", {"accession": accession}))
        return response(protein(accession), {"accession": accession})

    def uniprot_search(self, **arguments):
        self.calls.append(("search", arguments))
        return response({"results": [protein()]}, arguments,
                        next_cursor=None if "cursor" in arguments else "actual-next")


@pytest.fixture
def harness(tmp_path):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence="MACDEFGH", molecule="protein")
        client = Client()
        tools = ToolRegistry(store, clients=client)
        yield store, tools, client, store.validate_scope(None)


def test_single_response_handoff_and_publication_reuse_without_http(harness):
    store, tools, client, scope = harness
    service = build_service("uniprot", {"kind": "api", "service": "uniprot"}, tools)
    assert {row["name"] for row in service.capabilities()} == {"api.uniprot.record", "api.uniprot.search"}
    request = {"operation": "record", "accession": "P12345"}
    assert service.validate_request(request, scope) == request
    prepared = service.prepare("api.uniprot.record", request, {}, scope=scope, previous_events=[])
    native = service.invoke(prepared)
    result = service.decode(prepared, native)
    assert result["state"] == "completed" and result["native_handle"] == {}
    assert result["handoff_ready"] and result["result_available"]
    cached = service.prepare("api.uniprot.collect", request, {}, scope=scope,
                             previous_events=[], selector={})
    assert cached["cache_original"]
    published = service.publish(request, {}, native, scope, "same-publication")
    assert published["status"] == "completed"
    assert published["result"]["records"][0]["accession"] == "P12345"
    assert store.get(published["result"]["source_ref"])["provider"] == "uniprot"
    assert service.publish(request, {}, native, scope, "same-publication") == published
    assert len(client.calls) == 1
    assert len(store.targets()) == 1
    assert service.prepare_observation(request, {}, scope=scope) is None


def test_pagination_is_one_selected_page_and_keeps_original_query(harness):
    store, tools, client, scope = harness
    service = UniProtService(tools)
    request = {"operation": "search", "query": "gene:example AND organism_id:83333"}
    assert service.validate_request(request, None) == request  # No inserted defaults.
    first = service.prepare("api.uniprot.search", request, {}, scope=scope, previous_events=[])
    assert first["native_arguments"]["size"] == 10
    snapshot = service.invoke(first)
    facts = service.decode(first, snapshot)["facts"]
    assert facts["next_cursor"] == "actual-next" and facts["total_results"] == 2
    selector = {"cursor": facts["next_cursor"], "size": 1}
    following = service.prepare("api.uniprot.collect", request, {}, scope=scope,
        previous_events=[], selector=selector)
    assert not following["cache_original"]
    assert following["native_arguments"] == {"query": request["query"], **selector}
    second = service.invoke(following)
    assert service.decode(following, second)["facts"]["next_cursor"] is None
    assert len(client.calls) == 2
    assert service.publish(request, selector, second, scope, "second-page")["status"] == "completed"
    assert len(client.calls) == 2


def test_source_request_conflict_and_invalid_request_are_rejected(harness):
    _, tools, _, scope = harness
    service = UniProtService(tools)
    with pytest.raises(ValueError, match="fields_conflict"):
        service.validate_request({"operation": "record", "accession": "P12345", "query": "other"}, None)
    with pytest.raises(ValueError, match="record_selector"):
        service.result_catalog({"operation": "record", "accession": "P12345"}, {"cursor": "x"})
    prepared = service.prepare("api.uniprot.search", {"operation": "search", "query": "assigned"}, {},
                               scope=scope, previous_events=[])
    with pytest.raises(ValueError, match="request_conflict_query"):
        service.decode(prepared, response({"results": []}, {"query": "different"}))
    empty = response({"results": []}, {"query": "assigned"})
    assert service.decode(prepared, empty)["facts"]["returned_count"] == 0
