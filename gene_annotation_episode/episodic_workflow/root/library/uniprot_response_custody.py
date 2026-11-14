"""Original UniProt response custody and page metadata, without a service host."""
from __future__ import annotations
from gene_annotation_episode.uniprot_native import parse_uniprot_native


def uniprot_page_metadata(parsed):
    """Existing page-result keys projected from the already parsed page."""
    page = parsed["page"]
    return {"next_cursor": page["next_cursor"], "total_results": page["total_results"]["value"],
            "release": page["release"]["value"], "release_date": page["release_date"]["value"],
            "pagination_metadata_available": page["pagination_metadata_available"]}


def parse_uniprot_snapshot(snapshot, *, request):
    """Validate actual response custody before applying the pure native reader.

    The native parser receives a caller-supplied request. It cannot establish
    that the transport actually used that request; this adapter checks that
    separate relationship, without guessing missing request operands/status.
    """
    if snapshot is None or snapshot.service != "uniprot":
        raise ValueError("uniprot_response_required")
    if not isinstance(snapshot.request, dict):
        raise ValueError("uniprot_response_request_required")
    expected = {key: value for key, value in request.items() if key != "operation"}
    for key in ("accession", "query", "size", "cursor"):
        if key in expected and key not in snapshot.request:
            raise ValueError("uniprot_response_request_missing_" + key)
        if key in snapshot.request and (key not in expected or
                type(snapshot.request[key]) is not type(expected[key]) or
                snapshot.request[key] != expected[key]):
            raise ValueError("uniprot_response_request_conflict_" + key)
    if (set(snapshot.request) - (set(expected) | {"format"}) or
            snapshot.request.get("format", "json") != "json"):
        raise ValueError("uniprot_response_request_invalid")
    transport = snapshot.transport
    if not isinstance(transport, dict):
        raise ValueError("uniprot_response_transport_invalid")
    response = transport.get("response")
    if response is not None and not isinstance(response, dict):
        raise ValueError("uniprot_response_transport_invalid")
    response = response or {}
    for status in (transport.get("status"), response.get("status")):
        if status is not None and (type(status) is not int or not 200 <= status < 300):
            raise ValueError("uniprot_http_response_not_successful")
    if response.get("request_method") not in (None, "GET"):
        raise ValueError("uniprot_response_request_method_conflict")
    headers = response.get("headers", transport.get("headers"))
    if headers is not None and not isinstance(headers, dict):
        raise ValueError("uniprot_response_headers_invalid")
    return parse_uniprot_native(snapshot.content, request=request, response_headers=headers)


