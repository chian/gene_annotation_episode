"""Saved-native and controlled UniProt binding cases; no provider requests."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

import pytest

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.api_uniprot import UniProtService
from gene_annotation_episode.domain import identity
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from gene_annotation_episode.uniprot_native import parse_uniprot_native
from gene_annotation_episode.uniprot_publication import bind_uniprot_publication


def protein(accession="P12345", sequence="MACDEFGH", name="Native source name"):
    return {"primaryAccession": accession, "sequence": {"value": sequence, "length": len(sequence)},
        "organism": {"taxonId": 83333, "scientificName": "Escherichia coli"},
        "proteinDescription": {"recommendedName": {"fullName": {"value": name}}}}


def snapshot(body, request, *, headers=None):
    return SourceSnapshot("uniprot", "https://rest.uniprot.org/uniprotkb/" + request.get("accession", "search"),
        deepcopy(request), "2026-10-28T00:00:00+00:00", json.dumps(body).encode(), "application/json",
        {"response": {"status": 200, "headers": headers or {}, "request_method": "GET"},
         "representation": "controlled_native_service_response"})


class RecordedClient:
    def __init__(self, response):
        self.response, self.calls = response, []

    def uniprot_record(self, accession):
        self.calls.append(("record", {"accession": accession}))
        return self.response

    def uniprot_search(self, **arguments):
        self.calls.append(("search", arguments))
        return self.response


@pytest.fixture
def harness(tmp_path):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence="MACDEFGH", molecule="protein")
        yield store


def publish(store, native, operation, arguments, key="publication"):
    client = RecordedClient(native)
    tools = ToolRegistry(store, clients=client)
    outcome = tools.execute("public.uniprot." + operation, arguments, operation_key=key)
    return tools, client, outcome


def test_authentic_retained_record_publication_keeps_full_native_associations(harness):
    archive = (Path(__file__).parents[1] / "verification/api_service_expansion_2026-10-23_001/"
               "live_public_002/uniprot/state/artifacts")
    raw = (archive / "dc/dc1e11907d2d7a9ea423dd90e9f6bea7393cdf21669d139b1b04e1a8647d0e3e").read_bytes()
    custody = json.loads((archive / "c2/c2c89095b2d4c9662cf65535768b4720a8dc094ffa3426bb54e4d933ada1c952").read_text())
    native = replace(snapshot({}, custody["request"]), content=raw, transport=custody["transport"])
    tools, _, outcome = publish(harness, native, "record", {"accession": "P0AAW1"})
    assert outcome["status"] == "completed", outcome
    publication = outcome["result"]["uniprot_publication"]
    bound, = publication["records"]
    row = bound["record"]
    assert bound["anchor"]["record_ordinal"] == 0 and bound["anchor"]["record_pointer"] == ""
    assert row["identity"]["primary_accession"] == "P0AAW1"
    assert row["identity"]["secondary_accessions"]["value"] == ["P75772"]
    assert row["sequence"]["observed_length_aa"] == 253
    assert row["taxon"]["taxon_id"]["value"] == 83333
    assert row["features"]["items"][0]["exact_interval_0based_half_open"] == [0, 253]
    assert len(row["cross_references"]["items"]) == 42
    evidence = next(item for item in row["evidence"]["items"]
                    if item["owner_pointer"] == "/uniProtKBCrossReferences/31")
    assert evidence["evidence_code"]["value"] == "ECO:0007005"
    assert evidence["source_id"]["value"] == "32127419"
    assert harness.get_artifact(publication["native_artifact_ref"]) == raw
    assert tools._sequence(bound["anchor"]["reference_ref"]) == json.loads(raw)["sequence"]["value"]
    source = harness.get(publication["source_ref"])
    assert json.loads(harness.get_artifact(source["request_ref"])) == custody
    assert harness.count("observation") == 0 and harness.count("annotation") == 0


def test_partial_page_keeps_native_ordinals_and_existing_reference_identity(harness):
    body = {"results": [protein(), [], protein("Q12345"), protein()]}
    arguments = {"query": "controlled", "size": 4}
    native = snapshot(body, {**arguments, "format": "json"}, headers={"x-total-results": "4"})
    tools, client, direct = publish(harness, native, "search", arguments)
    assert direct["status"] == "partial", direct
    publication = direct["result"]["uniprot_publication"]
    assert [item["anchor"]["record_ordinal"] for item in publication["records"]] == [0, 2, 3]
    assert [item["anchor"]["record_pointer"] for item in publication["records"]] == [
        "/results/0", "/results/2", "/results/3"]
    assert publication["records"][0]["anchor"]["reference_ref"] == publication["records"][2]["anchor"]["reference_ref"]
    assert direct["result"]["count"] == publication["page"]["publishable_record_count"] == 3
    assert publication["page"]["native_record_count"] == 4
    assert any(issue["record_ordinal"] == 1 and issue["pointer"] == "/results/1"
               for issue in direct["result"]["projection_errors"])
    service = UniProtService(tools)
    selected = {"operation": "search", **arguments}
    assert service.decode(service.prepare("api.uniprot.search", selected, {}, scope=None,
        previous_events=[]), native)["handoff_ready"]
    acquired = service.publish(selected, {}, native, harness.validate_scope(None), "service-publication")
    assert acquired["status"] == "partial"
    assert acquired["result"] == direct["result"]
    assert len(client.calls) == 1


def test_full_sequence_conflict_and_invalid_sequence_siblings_are_distinct(harness):
    long_sequence = "MACDEFGH" * 1500
    one, two, three = protein(sequence=long_sequence), protein("Q12345", sequence="MA?"), protein("R12345")
    one["sequence"]["length"] = 7
    three.pop("sequence")
    body = {"results": [one, two, three]}
    args = {"query": "controlled", "size": 3}
    tools, _, result = publish(harness, snapshot(body, args), "search", args)
    assert result["status"] == "partial", result
    bound = result["result"]["uniprot_publication"]["records"]
    assert bound[0]["record"]["sequence"]["length_relation"] == "conflict"
    assert bound[0]["record"]["sequence"]["reported_length_aa"]["value"] == 7
    assert bound[0]["record"]["sequence"]["value"]["value"] == long_sequence
    assert harness.get_artifact(bound[0]["sequence_ref"]) == long_sequence.encode()
    assert tools._sequence(bound[0]["anchor"]["reference_ref"]) == long_sequence
    for item, state in zip(bound[1:], ("invalid", "absent"), strict=True):
        assert item["record"]["sequence"]["value"]["state"] == state
        assert item["sequence_ref"] is None
        assert harness.get(item["anchor"]["reference_ref"])["length"] is None


def test_legacy_name_order_and_ec_duplicates_come_only_from_parser(harness):
    row = protein()
    row["proteinDescription"] = {
        "recommendedName": {"ecNumbers": [{"value": "1.2.3.4"}, {"value": "1.2.3.4"}]},
        "submissionNames": [{"fullName": {"value": "Later source name"}, "ecNumbers": [{"value": "2.3.4.5"}]}],
        "alternativeNames": [{"fullName": {"value": "Alternative source name"}, "ecNumbers": [{"value": "3.4.5.6"}]}]}
    _, _, result = publish(harness, snapshot(row, {"accession": "P12345"}), "record", {"accession": "P12345"})
    assert result["status"] == "completed", result
    bound, = result["result"]["uniprot_publication"]["records"]
    legacy = bound["record"]["legacy_publication"]
    assert legacy["source_name"] is None
    assert legacy["source_ec_numbers"] == ["1.2.3.4", "1.2.3.4", "2.3.4.5"]
    reference = harness.get(bound["anchor"]["reference_ref"])
    assert reference["label"] == "P12345"
    terms = [harness.get(ref) for ref in reference["term_refs"]]
    assert [term["accession"] for term in terms if term["namespace"] == "EC"] == ["1.2.3.4", "2.3.4.5"]
    assert not any(term["namespace"] == "uniprot_source_name" for term in terms)


def test_legacy_limits_preserve_native_text_and_independent_valid_bindings(harness):
    long_name = "native source text " * 1000
    body = {"results": [protein(name=long_name), protein("identifier with spaces"), protein("Q12345")]}
    args = {"query": "controlled", "size": 3}
    native = snapshot(body, args)
    _, _, result = publish(harness, native, "search", args)
    assert result["status"] == "partial", result
    publication = result["result"]["uniprot_publication"]
    parsed = parse_uniprot_native(native.content, request={"operation": "search", **args},
                                 response_headers={})
    assert publication["page"] == parsed["page"]
    assert publication["page"]["publishable_record_count"] == 3  # Parser eligibility.
    assert result["result"]["count"] == len(publication["records"]) == 2  # Actual bindings.
    assert [row["anchor"]["record_ordinal"] for row in publication["records"]] == [0, 2]
    first = publication["records"][0]
    assert first["record"]["legacy_publication"]["source_name"] == long_name
    assert harness.get(first["anchor"]["reference_ref"])["label"] == "P12345"
    failure = next(issue for issue in result["result"]["projection_errors"]
                   if issue["code"] == "uniprot_legacy_reference_unrepresentable")
    assert (failure["record_ordinal"], failure["pointer"], failure["primary_accession"]) == (
        1, "/results/1/primaryAccession", "identifier with spaces")
    assert failure["effect"] == "record_unpublishable"
    assert not any(issue["code"] == "field_type_invalid" for issue in publication["issues"])
    assert harness.get_artifact(publication["native_artifact_ref"]) == native.content


def test_pure_binding_checks_actual_reference_source_identity_and_sequence(harness):
    native = snapshot(protein(), {"accession": "P12345"})
    _, _, result = publish(harness, native, "record", {"accession": "P12345"})
    publication = result["result"]["uniprot_publication"]
    parsed = parse_uniprot_native(native.content, request={"operation": "record", "accession": "P12345"},
                                 response_headers={})
    reference = result["result"]["records"][0]
    keywords = {"source_ref": publication["source_ref"], "native_artifact_ref": publication["native_artifact_ref"]}
    assert bind_uniprot_publication(parsed, references_by_ordinal={0: reference}, **keywords) == publication
    for key, value in (("source_ref", "source_" + "a" * 24), ("accession", "Q12345")):
        with pytest.raises(ValueError, match="reference_binding_conflict"):
            bind_uniprot_publication(parsed, references_by_ordinal={0: {**reference, key: value}}, **keywords)
    with pytest.raises(ValueError, match="ordinal_binding_conflict"):
        bind_uniprot_publication(parsed, references_by_ordinal={2: reference}, **keywords)
    with pytest.raises(ValueError, match="reference_identity_conflict"):
        bind_uniprot_publication(parsed, references_by_ordinal={0: {**reference, "id": "reference_"+"a"*24}}, **keywords)
    wrong = {**reference, "sequence_ref": harness.artifact("ACDEFGHM"), "length": 8}
    fields = {key: value for key, value in wrong.items() if key not in {"id", "record_type", "origin"}}
    wrong["id"] = identity("reference", {"origin": "external", "record": fields})
    with pytest.raises(ValueError, match="sequence_binding_conflict"):
        bind_uniprot_publication(parsed, references_by_ordinal={0: wrong}, **keywords)
    unknown = parse_uniprot_native(native.content, request=None, response_headers={})
    with pytest.raises(ValueError, match="request_unverified"):
        bind_uniprot_publication(unknown, references_by_ordinal={0: reference}, **keywords)


def test_actual_sequence_bytes_are_verified_before_binding(harness, monkeypatch):
    import gene_annotation_episode.uniprot_publication as binding
    native = snapshot(protein(), {"accession": "P12345"})
    original = harness.get_artifact
    sequence_ref = harness.artifact("MACDEFGH", "text/plain")
    monkeypatch.setattr(harness, "get_artifact", lambda ref: b"wrong" if ref == sequence_ref else original(ref))
    monkeypatch.setattr(binding, "bind_uniprot_publication", lambda *args, **kwargs: pytest.fail("unverified bytes reached binding"))
    _, _, result = publish(harness, native, "record", {"accession": "P12345"})
    assert result["status"] == "partial"
    assert result["feedback"]["code"] == "uniprot_sequence_artifact_content_conflict"
    assert harness.count("reference") == 0
    source = next(harness.get(ref) for ref in result["record_refs"] if harness.get(ref)["record_type"] == "source")
    assert original(source["artifact_ref"]) == native.content


def test_original_publication_replay_keeps_saved_outcome_and_one_request(harness):
    native = snapshot(protein(), {"accession": "P12345"})
    tools, client, original = publish(harness, native, "record", {"accession": "P12345"}, key="original")
    counts = (harness.count("source"), harness.count("reference"), harness.count("term"))
    client.response = snapshot(protein("Q12345"), {"accession": "Q12345"})
    assert tools.execute("public.uniprot.record", {"accession": "P12345"}, operation_key="original") == original
    assert (harness.count("source"), harness.count("reference"), harness.count("term")) == counts
    assert len(client.calls) == 1


@pytest.mark.parametrize("transport", [{}, {"response": None}, {"response": {"headers": None}}])
def test_missing_transport_metadata_does_not_prevent_native_source_custody(harness, transport):
    native = replace(snapshot(protein(), {"accession": "P12345"}), transport=transport)
    _, _, result = publish(harness, native, "record", {"accession": "P12345"})
    assert result["status"] == "completed", result
    publication = result["result"]["uniprot_publication"]
    assert publication["page"]["pagination_metadata_available"] is False
    source = harness.get(publication["source_ref"])
    assert source["version"] is None
    assert json.loads(harness.get_artifact(source["request_ref"]))["transport"] == transport


def test_long_release_retains_native_value_with_explicit_legacy_qualification(harness):
    release = "native release " * 1000
    args = {"query": "controlled", "size": 1}
    native = snapshot({"results": [protein()]}, args, headers={"x-uniprot-release": release,
                                                            "x-total-results": "1"})
    _, _, result = publish(harness, native, "search", args)
    assert result["status"] == "completed", result
    publication = result["result"]["uniprot_publication"]
    assert publication["page"]["release"]["state"] == "present"
    assert publication["page"]["release"]["value"] == result["result"]["release"] == release
    assert harness.get(publication["source_ref"])["version"] is None
    assert result["result"]["projection_qualifications"] == [{
        "code": "uniprot_legacy_source_version_omitted", "record_ordinal": None,
        "pointer": "/headers/x-uniprot-release", "field": "legacy_source", "effect": "qualification"}]


def test_new_page_facts_use_the_same_parsed_observed_transport_headers(harness):
    args = {"query": "controlled", "size": 1}
    native = replace(snapshot({"results": [protein()]}, args), transport={"status": 200,
        "headers": {"x-total-results": "2", "link":
            '<https://rest.uniprot.org/uniprotkb/search?query=controlled&size=1&cursor=next>; rel="next"'}})
    tools, _, result = publish(harness, native, "search", args)
    assert result["status"] == "completed", result
    page = result["result"]["uniprot_publication"]["page"]
    assert page["next_cursor"] == result["result"]["next_cursor"] == "next"
    service = UniProtService(tools)
    prepared = service.prepare("api.uniprot.search", {"operation": "search", **args}, {},
                               scope=None, previous_events=[])
    assert service.decode(prepared, native)["facts"]["next_cursor"] == "next"
