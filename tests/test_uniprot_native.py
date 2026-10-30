"""Retained authentic record plus labelled controlled UniProtKB JSON fixtures.

No acquisition, model, tool execution, score or full episode is simulated as
scientific evidence by these parser checks. Run only in the bounded runner.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode.acquisition import SourceSnapshot, parse_uniprot, uniprot_pagination
from gene_annotation_episode.uniprot_native import (legacy_uniprot_records, normalize_query_uniprot,
    parse_uniprot_native, validate_uniprot_projection)
from gene_annotation_episode.uniprot_native_contracts import PARSED_PAGE_SCHEMA, PUBLICATION_SCHEMA


FIXTURES = Path(__file__).parent / "fixtures" / "uniprot_native"
RECORD = {"operation": "record", "accession": "P12345"}
SEARCH = {"operation": "search", "query": "gene:controlled AND organism_id:83333", "size": 3}


def controlled_record(accession="P12345"):
    return {"primaryAccession": accession, "secondaryAccessions": ["Q00001"],
        "sequence": {"value": "MACDEFGH", "length": 8},
        "organism": {"taxonId": 83333, "scientificName": "Controlled source organism"},
        "proteinDescription": {"recommendedName": {"fullName": {"value": "Controlled source label"}}}}


def native_bytes(body):
    return json.dumps(body, ensure_ascii=False).encode()


def project(body, *, request=RECORD, headers=None):
    return parse_uniprot_native(native_bytes(body), request=request, response_headers=headers)


def feature(start=1, end=8, modifier="EXACT", **location):
    return {"type": "Chain", "location": {"start": {"value": start, "modifier": modifier},
        "end": {"value": end, "modifier": "EXACT"}, **location}}


def next_link(query=SEARCH["query"], size=SEARCH["size"], cursor="opaque +/= token"):
    return '<https://rest.uniprot.org/uniprotkb/search?' + urlencode(
        {"query": query, "size": size, "cursor": cursor, "format": "json"}) + '>; rel="next"'


def resolve(body, pointer):
    for token in pointer.lstrip("/").split("/") if pointer else []:
        token = token.replace("~1", "/").replace("~0", "~")
        body = body[int(token)] if isinstance(body, list) else body[token]
    return body


@pytest.mark.parametrize("endpoint", ["uniprotkb/P01308", "/uniprotkb/P01308",
    "https://rest.uniprot.org/uniprotkb/P01308", "/uniprotkb/P01308.json",
    "https://rest.uniprot.org/uniprotkb/P01308.json?format=json"])
def test_record_alias_normalizes_only_explicit_selection(endpoint):
    assert normalize_query_uniprot(endpoint) == {"operation": "record", "accession": "P01308"}
    assert normalize_query_uniprot(endpoint, max_results=None) == normalize_query_uniprot(endpoint)


def test_search_alias_preserves_query_cursor_and_selected_page_size():
    query, cursor = "  gene:ybhP AND (organism_id:83333)  ", "a+b /==,opaque"
    endpoint = "/uniprotkb/search?" + urlencode({"query": query, "cursor": cursor})
    assert normalize_query_uniprot(endpoint) == {"operation": "search", "query": query,
                                                "cursor": cursor, "size": 10}
    assert normalize_query_uniprot(endpoint, max_results=500)["size"] == 500
    assert normalize_query_uniprot(endpoint + "&size=1", max_results=1)["size"] == 1
    assert normalize_query_uniprot("/uniprotkb/p01308")["accession"] == "p01308"
    with pytest.raises(ValueError, match="size_conflict"):
        normalize_query_uniprot(endpoint + "&size=1", max_results=2)


@pytest.mark.parametrize("size", [0, 501, True, False, 1.0, "1", -1])
def test_alias_rejects_invalid_max_results(size):
    with pytest.raises(ValueError):
        normalize_query_uniprot("/uniprotkb/search?query=x", max_results=size)


@pytest.mark.parametrize("endpoint", [
    "https://evil.example/uniprotkb/P01308", "http://rest.uniprot.org/uniprotkb/P01308",
    "https://user@rest.uniprot.org/uniprotkb/P01308", "https://rest.uniprot.org:443/uniprotkb/P01308",
    "//rest.uniprot.org/uniprotkb/P01308", "/uniprotkb/P01308#", "/uniprotkb/P01308#fragment",
    "/uniprotkb/P01308-2", "/uniprotkb/P01308.1", "/uniprotkb/P01308.xml",
    "/uniprotkb/P01308?format=fasta", "/uniprotkb/P01308?query=x", "/uniprotkb/P01308/",
    "/uniprotkb/stream?query=x", "/uniref/UniRef90_P01308", "/uniparc/UPI000001",
    "/uniprotkb/search", "/uniprotkb/search?query=", "/uniprotkb/search?query=%20",
    "/uniprotkb/search?query=x&query=y", "/uniprotkb/search?query=x&fields=accession",
    "/uniprotkb/search?query=x&sort=score", "/uniprotkb/search?query=x&cursor=",
    "/uniprotkb/search?query=x&size=0", "/uniprotkb/search?query=x&size=501",
    "/uniprotkb/search?query=x&size=1.0", "/uniprotkb/search?query=x&size=true",
    "/uniprotkb/search?query=%GG", "/uniprotkb/search?query=%FF", "/uniprotkb/P01308\n",
    "Find human insulin", "/uniprotkb/search?query=x&format=json&format=json",
])
def test_alias_rejects_unsupported_selection_without_silent_substitution(endpoint):
    with pytest.raises(ValueError):
        normalize_query_uniprot(endpoint)


def test_record_alias_rejects_search_size():
    with pytest.raises(ValueError, match="record_max_results"):
        normalize_query_uniprot("/uniprotkb/P01308", max_results=1)


@pytest.mark.parametrize("requested,relation", [("P0AAW1", "primary"), ("P75772", "secondary")])
def test_authentic_retained_record_sequence_feature_evidence_and_legacy(requested, relation):
    content = (FIXTURES / "P0AAW1.json").read_bytes()
    transport = json.loads((FIXTURES / "P0AAW1.transport.json").read_bytes())
    assert len(content) == 8650
    assert hashlib.sha256(content).hexdigest() == "dc1e11907d2d7a9ea423dd90e9f6bea7393cdf21669d139b1b04e1a8647d0e3e"
    parsed = parse_uniprot_native(content, request={"operation": "record", "accession": requested},
                                  response_headers=transport["transport"]["response"]["headers"])
    Draft202012Validator(PARSED_PAGE_SCHEMA).validate(parsed)
    native = json.loads(content)
    row = parsed["records"][0]
    assert row["identity"]["accession_relation"] == relation
    assert row["identity"]["primary_accession"] == "P0AAW1"
    assert row["identity"]["secondary_accessions"]["value"] == ["P75772"]
    assert row["sequence"]["value"]["value"] == native["sequence"]["value"]
    assert row["sequence"]["observed_length_aa"] == row["sequence"]["reported_length_aa"]["value"] == 253
    assert row["sequence"]["length_relation"] == "agree"
    assert row["taxon"]["taxon_id"]["value"] == 83333
    assert row["features"]["items"][0]["exact_interval_0based_half_open"] == [0, 253]
    assert len(row["cross_references"]["items"]) == 42
    xref = row["cross_references"]["items"][31]
    assert xref["identifier"]["value"] == "GO:0005886"
    assert xref["evidence_pointers"] == ["/uniProtKBCrossReferences/31/evidences/0"]
    ev = next(e for e in row["evidence"]["items"] if e["pointer"] == xref["evidence_pointers"][0])
    assert ev["owner_pointer"] == "/uniProtKBCrossReferences/31"
    assert [ev[k]["value"] for k in ("evidence_code", "source", "source_id")] == ["ECO:0007005", "PubMed", "32127419"]
    assert parsed["page"]["release"]["value"] == "2026_03"
    assert parsed["page"]["release_date"]["value"] == "02-September-2026"
    assert parsed["issues"] == []
    legacy = legacy_uniprot_records(parsed, content)[0]
    assert legacy["source_name"] == "Uncharacterized protein YbhP"
    assert legacy["source_ec_numbers"] == []
    assert len(legacy["source_references"]) == 3
    assert legacy["source_features"] == native["features"]
    assert legacy["source_cross_references"] == native["uniProtKBCrossReferences"]


def test_unknown_request_never_invents_accession_or_query():
    for body, operation in [(controlled_record(), "record"), ({"results": [controlled_record()]}, "search")]:
        parsed = project(body, request=None, headers={"x-total-results": "1"})
        assert parsed["page"]["operation"] == operation
        assert parsed["page"]["effective_request"] is None
        assert parsed["page"]["request_verification"] == "unknown"
        assert parsed["page"]["whole_query_complete"] is None
        assert parsed["records"][0]["identity"]["requested_accession"] is None
        assert parsed["records"][0]["identity"]["accession_relation"] == "unverified"
        assert parsed["issues"][0]["code"] == "native_request_unverified"


@pytest.mark.parametrize("canonical_request", [None, RECORD])
@pytest.mark.parametrize("content", [b"{", b"\xff", b'{"primaryAccession":NaN}'])
def test_invalid_json_preserves_unknown_counts_and_structured_failure(content, canonical_request):
    parsed = parse_uniprot_native(content, request=canonical_request, response_headers=None)
    assert parsed["page"]["response_body_state"] == "invalid_json"
    assert parsed["page"]["native_record_count"] is None
    assert parsed["page"]["projection_state"] == "invalid"
    assert parsed["page"]["operation"] == ("unknown" if canonical_request is None else "record")
    assert parsed["records"] == []
    assert parsed["content_sha256"] == hashlib.sha256(content).hexdigest()


def test_invalid_envelope_and_request_envelope_mismatch_are_explicit():
    unknown = project({}, request=None)
    assert unknown["page"]["operation"] == "unknown"
    assert unknown["page"]["selection_extent"] == "not_established"
    for body, request in [({"results": {}}, SEARCH), (controlled_record(), SEARCH),
                          ({"results": [controlled_record()]}, RECORD)]:
        parsed = project(body, request=request)
        assert parsed["page"]["projection_state"] == "invalid"
        assert parsed["records"] == []


def test_unmatched_accession_cannot_publish_and_secondary_is_not_globally_unique():
    unmatched = project(controlled_record(), request={"operation": "record", "accession": "P12345-2"})
    assert unmatched["records"] == []
    assert any(e["code"] == "accession_unmatched" for e in unmatched["issues"])
    rows = [controlled_record("P12345"), controlled_record("P54321")]
    parsed = project({"results": rows}, request=SEARCH)
    assert [r["identity"]["primary_accession"] for r in parsed["records"]] == ["P12345", "P54321"]
    assert [r["identity"]["record_ordinal"] for r in parsed["records"]] == [0, 1]
    assert all(r["identity"]["secondary_accessions"]["value"] == ["Q00001"] for r in parsed["records"])


def test_malformed_rows_and_fields_preserve_native_sibling_ordinals():
    first, last = controlled_record(), controlled_record("P54321")
    last.update(sequence={"value": "bad sequence", "length": False},
                organism={"taxonomyId": 999, "taxonId": "83333", "scientificName": "Still available"},
                features=[None, feature(2, 4)], uniProtKBCrossReferences=[None, {"database": "GO", "id": "GO:1"}])
    body = {"results": [first, None, {"primaryAccession": ""}, last]}
    parsed = project(body, request=SEARCH)
    assert parsed["page"]["native_record_count"] == 4
    assert parsed["page"]["publishable_record_count"] == 2
    assert parsed["page"]["projection_state"] == "partial"
    assert [r["identity"]["record_ordinal"] for r in parsed["records"]] == [0, 3]
    row = parsed["records"][1]
    assert row["identity"]["record_pointer"] == "/results/3"
    assert row["taxon"]["taxon_id"]["state"] == "invalid"
    assert row["taxon"]["scientific_name"]["value"] == "Still available"
    assert row["sequence"]["value"]["state"] == "invalid"
    assert row["features"]["items"][0]["ordinal"] == 1
    assert row["features"]["items"][0]["exact_interval_0based_half_open"] is None
    assert row["cross_references"]["items"][0]["ordinal"] == 1
    assert [r["accession"] for r in legacy_uniprot_records(parsed, native_bytes(body))] == ["P12345", "P54321"]


def test_missing_null_empty_invalid_and_zero_are_distinct():
    row = controlled_record()
    row.update(uniProtkbId="", proteinExistence=None, entryType=17,
               sequence={"value": "M", "length": 0, "md5": "", "crc64": None},
               organism={"taxonId": 0, "synonyms": [], "lineage": None},
               features=[], comments=None, references="invalid")
    projected = project(row)["records"][0]
    assert projected["metadata"]["uniprot_id"]["value"] == ""
    assert projected["metadata"]["protein_existence"]["state"] == "null"
    assert projected["metadata"]["entry_type"]["state"] == "invalid"
    assert projected["metadata"]["entry_version"]["state"] == "absent"
    assert projected["sequence"]["reported_length_aa"]["value"] == 0
    assert projected["sequence"]["length_relation"] == "conflict"
    assert projected["taxon"]["synonyms"]["value"] == []
    assert projected["taxon"]["lineage_names"]["state"] == "null"
    assert projected["taxon"]["taxon_id"]["state"] == "invalid"
    assert projected["features"] == {"state": "present", "items": []}
    assert projected["cross_references"] == {"state": "absent", "items": []}
    assert {s["name"]: s["state"] for s in projected["metadata"]["native_sections"]}["comments"] == "null"


@pytest.mark.parametrize("sequence", ["maCD", "M AC", "M*", "M-", "M\n", "MÅ", ""])
def test_invalid_native_sequence_is_never_trimmed_uppercased_or_padded(sequence):
    row = controlled_record()
    row["sequence"]["value"] = sequence
    row["features"] = [feature()]
    projected = project(row)["records"][0]
    assert projected["sequence"]["value"]["state"] == "invalid"
    assert projected["sequence"]["observed_length_aa"] is None
    assert projected["features"]["items"][0]["exact_interval_0based_half_open"] is None


def test_complete_long_native_data_and_reported_length_conflict_remain_available():
    row = controlled_record()
    sequence = "MACDEFGHIKLMNPQRSTVWYBXZJUO" * 1000
    text = "Native controlled text. " * 1000
    row["sequence"] = {"value": sequence, "length": 7}
    row["comments"] = [{"texts": [{"value": text}]}]
    row["proteinDescription"]["recommendedName"]["fullName"]["value"] = text
    row["features"] = [feature(1, len(sequence))]
    parsed = project(row)
    result = parsed["records"][0]
    assert result["sequence"]["value"]["value"] == sequence
    assert result["sequence"]["observed_length_aa"] == len(sequence) > 10000
    assert result["sequence"]["reported_length_aa"]["value"] == 7
    assert result["sequence"]["length_relation"] == "conflict"
    assert result["features"]["items"][0]["exact_interval_0based_half_open"] == [0, len(sequence)]
    legacy = legacy_uniprot_records(parsed, native_bytes(row))[0]
    assert legacy["source_name"] == text and legacy["source_comments"] == row["comments"]


def test_exact_fuzzy_other_sequence_and_invalid_feature_locations_are_distinct():
    row = controlled_record()
    row["features"] = [feature(2, 4), feature(2, 4, "LESS_THAN"), feature(1, 8, sequence="P12345-2"),
        feature(1, 8, sequence="P12345"), feature(-1, 8), feature(5, 2), feature(1, 9),
        {"location": {"start": {"modifier": "UNKNOWN"}, "end": {"value": 8, "modifier": "EXACT"}}}]
    features = project(row)["records"][0]["features"]["items"]
    assert [f["exact_interval_0based_half_open"] for f in features] == [[1, 4], None, None, [0, 8], None, None, None, None]
    assert features[1]["start"]["modifier"]["value"] == "LESS_THAN"
    assert features[2]["sequence_binding"] == "explicit_other_sequence"
    assert features[2]["native_sequence_id"]["value"] == "P12345-2"
    assert features[4]["start"]["value"]["state"] == "invalid"


def test_nested_evidence_owner_ordinals_escaped_pointers_and_xref_properties():
    row = controlled_record()
    evidence = {"evidenceCode": "ECO:0000269", "source": "PubMed", "id": "123"}
    row["proteinDescription"]["recommendedName"]["fullName"]["evidences"] = [deepcopy(evidence)]
    row["features"] = [{**feature(), "evidences": [None, deepcopy(evidence)]}]
    row["comments"] = [{"texts": [{"value": "Retained paragraph", "evidences": [deepcopy(evidence)]}]}]
    row["uniProtKBCrossReferences"] = [{"database": "GO", "id": "GO:1",
        "properties": [None, {"key": "GoTerm", "value": "F:controlled"}, {"key": "Zero", "value": "0"}],
        "evidences": [deepcopy(evidence)]}]
    row["extension/with~escape"] = {"evidences": [deepcopy(evidence)]}
    parsed = project(row)
    projected = parsed["records"][0]
    evidence_rows = projected["evidence"]["items"]
    assert len(evidence_rows) == 5
    assert {e["owner_pointer"] for e in evidence_rows} == {
        "/proteinDescription/recommendedName/fullName", "/features/0", "/comments/0/texts/0",
        "/uniProtKBCrossReferences/0", "/extension~1with~0escape"}
    for evidence_row in evidence_rows:
        assert resolve(row, evidence_row["pointer"]) == evidence
    assert projected["features"]["items"][0]["evidence_pointers"] == ["/features/0/evidences/1"]
    xref = projected["cross_references"]["items"][0]
    assert [p["ordinal"] for p in xref["properties"]] == [1, 2]
    assert [p["value"]["value"] for p in xref["properties"]] == ["F:controlled", "0"]
    assert xref["evidence_pointers"] == ["/uniProtKBCrossReferences/0/evidences/0"]


def test_legacy_first_candidate_and_native_ec_order_are_preserved():
    row = controlled_record()
    row["proteinDescription"] = {"recommendedName": {"ecNumbers": [{"value": "1.1.1.1"}, None, {"value": 7}]},
        "submissionNames": [{"fullName": {"value": "Must not replace missing first name"},
                             "ecNumbers": [{"value": "1.1.1.1"}, {"value": "2.2.2.2"}]}],
        "alternativeNames": [{"fullName": {"value": "Not legacy"}, "ecNumbers": [{"value": "9.9.9.9"}]}]}
    parsed = project(row)
    legacy = parsed["records"][0]["legacy_publication"]
    assert legacy["source_name"] is None
    assert legacy["source_name_pointer"] == "/proteinDescription/recommendedName/fullName/value"
    assert legacy["source_ec_numbers"] == ["1.1.1.1", "1.1.1.1", "2.2.2.2"]
    assert [resolve(row, pointer) for pointer in legacy["source_ec_number_pointers"]] == legacy["source_ec_numbers"]
    assert legacy_uniprot_records(parsed, native_bytes(row)) == parse_uniprot(native_bytes(row))
    with pytest.raises(ValueError, match="digest_conflict"):
        legacy_uniprot_records(parsed, native_bytes(controlled_record()))


@pytest.mark.parametrize("headers,next_state,complete", [
    (None, "unknown", None), ({}, "absent", None), ({"x-total-results": "1"}, "absent", True),
    ({"x-total-results": "2"}, "absent", False), ({"x-total-results": "0"}, "absent", None),
    ({"x-total-results": "-1"}, "absent", None),
    ({"x-total-results": None}, "absent", None), ({"x-total-results": 1}, "absent", None),
    ({"link": next_link(), "x-total-results": "2"}, "present", False),
])
def test_selected_page_continuation_and_completion_need_observed_headers(headers, next_state, complete):
    parsed = project({"results": [controlled_record()]}, request=SEARCH, headers=headers)
    page = parsed["page"]
    assert page["next_state"] == next_state
    assert page["whole_query_complete"] is complete
    if next_state == "present":
        assert page["next_cursor"] == "opaque +/= token"
    assert page["effective_request"] == SEARCH


def test_later_page_and_unknown_request_cannot_claim_whole_query_complete():
    body = {"results": []}
    assert project(body, request=SEARCH, headers={"x-total-results": "0"})["page"]["whole_query_complete"] is True
    later = project(body, request={**SEARCH, "cursor": "selected-later"}, headers={"x-total-results": "0"})
    assert later["page"]["whole_query_complete"] is False
    unknown = project(body, request=None, headers={"link": next_link(), "x-total-results": "0"})
    assert unknown["page"]["next_cursor"] == "opaque +/= token"
    assert unknown["page"]["whole_query_complete"] is None


@pytest.mark.parametrize("link,code", [
    ('<https://evil.example/uniprotkb/search?query=x&cursor=y>; rel="next"', "link_invalid"),
    ('<http://rest.uniprot.org/uniprotkb/search?query=x&cursor=y>; rel="next"', "link_invalid"),
    ('<https://rest.uniprot.org/uniprotkb/search?query=x>; rel="next"', "link_invalid"),
    ('<https://rest.uniprot.org/uniprotkb/search?query=x&cursor=y&cursor=z>; rel="next"', "link_invalid"),
    (next_link(query="different"), "link_query_conflict"),
    (next_link(size=4), "link_query_conflict"),
    ("broken", "link_invalid"), (None, "link_invalid"), ("", "link_invalid"),
    ('<https://rest.uniprot.org/uniprotkb/search?cursor=y>; rel=', "link_invalid"),
    ('<https://rest.uniprot.org/uniprotkb/search?cursor=y>; rel=""', "link_invalid"),
    ('<https://rest.uniprot.org/uniprotkb/search?cursor=y>; rel="next"; broken', "link_invalid"),
    (next_link() + ", " + next_link(), "link_invalid"),
])
def test_invalid_or_conflicting_link_never_becomes_a_cursor(link, code):
    parsed = project({"results": []}, request=SEARCH, headers={"link": link, "x-total-results": "0"})
    assert parsed["page"]["next_state"] == "invalid"
    assert parsed["page"]["next_cursor"] is None
    assert parsed["page"]["whole_query_complete"] is None
    assert code in {issue["code"] for issue in parsed["issues"]}


def test_header_case_conflicts_and_link_commas_do_not_silently_change_meaning():
    parsed = project({"results": []}, request=SEARCH, headers={"X-Total-Results": "0",
        "X-UniProt-Release": "first", "x-uniprot-release": "second"})
    assert parsed["page"]["release"]["state"] == "invalid"
    assert any(i["code"] == "release_conflict" for i in parsed["issues"])
    assert parsed["page"]["whole_query_complete"] is None
    link = next_link(cursor="a,b").replace("a%2Cb", "a,b") + '; title="a,b"'
    assert project({"results": []}, request=SEARCH, headers={"Link": link})["page"]["next_cursor"] == "a,b"


@pytest.mark.parametrize("parameters", [{"cursor": "native-only"},
    {"cursor": "native-only", "query": SEARCH["query"]}])
def test_native_link_omissions_preserve_selected_query_size_without_fabricated_link_defaults(parameters):
    link_url = "https://rest.uniprot.org/uniprotkb/search?" + urlencode(parameters)
    parsed = project({"results": []}, request=SEARCH, headers={"link": '<' + link_url + '>; rel="next"'})
    assert SEARCH["size"] != 10
    assert parsed["page"]["next_url"] == link_url
    assert parsed["page"]["next_cursor"] == "native-only"
    assert parsed["page"]["effective_request"] == SEARCH
    assert parsed["page"]["whole_query_complete"] is False
    assert parsed["issues"] == []


def test_compatibility_pagination_uses_shared_projection_without_fabricated_request():
    snapshot = SourceSnapshot("uniprot", "https://rest.uniprot.org/uniprotkb/search", {},
        "historical-controlled", b"{}", "application/json", {"response": {"headers": {
            "link": next_link(), "x-total-results": "21", "x-uniprot-release": "fixture"}}})
    assert uniprot_pagination(snapshot) == {"next_cursor": "opaque +/= token", "total_results": 21,
        "release": "fixture", "release_date": None, "pagination_metadata_available": True}


@pytest.mark.parametrize("mutation", [
    lambda p: p["page"].update(publishable_record_count=99),
    lambda p: p["page"].update(whole_query_complete=True),
    lambda p: p["records"][0]["identity"].update(record_ordinal=4),
    lambda p: p["records"][0]["identity"].update(accession_relation="secondary"),
    lambda p: p["records"][0]["sequence"].update(observed_length_aa=1),
    lambda p: p["records"][0]["sequence"]["value"].update(state="absent"),
    lambda p: p["records"][0]["features"]["items"][0].update(exact_interval_0based_half_open=[0, 1]),
    lambda p: p["records"][0]["evidence"]["items"][0].update(owner_pointer="/other"),
    lambda p: p["records"][0]["legacy_publication"].update(source_ec_numbers=["1.1.1.1"]),
])
def test_validator_rejects_inconsistent_projection_relationships(mutation):
    row = controlled_record()
    row["features"] = [{**feature(), "evidences": [{"evidenceCode": "ECO:0000269"}]}]
    parsed = project(row)
    mutation(parsed)
    with pytest.raises(ValueError):
        validate_uniprot_projection(parsed)


def test_internal_schema_constants_are_self_contained_and_do_not_define_parent_facts():
    for schema in (PARSED_PAGE_SCHEMA, PUBLICATION_SCHEMA):
        Draft202012Validator.check_schema(schema)
        assert "fact_source_schemas" not in schema
        assert "maxLength" not in json.dumps(schema)
    assert PARSED_PAGE_SCHEMA["$defs"] is not PUBLICATION_SCHEMA["$defs"]
