"""Engineered pure Entrez controls; these perform no provider acquisition."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from urllib.parse import urlencode

import pytest

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.ncbi_entrez_acquisition import (
    ARGUMENTS_SCHEMA, DATABASES, FETCH_FORMATS, MAX_BYTES, entrez_request_spec,
    entrez_result, entrez_result_schema, validate_entrez_arguments, validate_entrez_result,
)


SOURCE = "source_" + "a" * 24


def arguments(operation="search", database="gds", **changes):
    value = dict(operation=operation, database=database, max_bytes=MAX_BYTES)
    value.update(dict(term='"literal tissue"[Title] AND gse[ETYP]', retstart=0, retmax=2, native_format="json")
        if operation == "search" else dict(ids=["1", "2"], native_format="json" if operation == "summary" else FETCH_FORMATS.get(database, "unsupported")))
    value.update(changes)
    return value


def snapshot(raw, selected, **transport_changes):
    raw = raw.encode("utf-8") if type(raw) is str else raw
    spec = entrez_request_spec(selected)
    transport = dict(status=200, headers={"content-type": spec["media_type"]},
        header_items=[("Content-Type", spec["media_type"])], body_complete=True,
        retained_body_bytes=len(raw), observed_body_bytes=len(raw), declared_body_bytes=len(raw),
        response_byte_limit=selected["max_bytes"], request=dict(method="GET",
            url=spec["url"] + "?" + urlencode(spec["params"]), headers={"Accept": spec["media_type"]}),
        request_policy=dict(timeout_seconds=30, automatic_redirects=False))
    transport.update(transport_changes)
    return SourceSnapshot(spec["service"], spec["url"], deepcopy(selected), "2026-10-31T00:00:00Z", raw, spec["media_type"], transport)


def result(raw, selected=None, **transport_changes):
    selected = arguments() if selected is None else selected
    saved = snapshot(raw, selected, **transport_changes)
    return entrez_result(saved, arguments=selected, source_ref=SOURCE,
        artifact_ref="artifact_" + hashlib.sha256(saved.content).hexdigest())


def codes(value):
    return [row["code"] for row in value["issues"]]


@pytest.mark.parametrize("database", DATABASES)
@pytest.mark.parametrize("operation", ["search", "summary"])
def test_only_literal_selected_request_is_prepared_without_chaining(database, operation):
    selected = arguments(operation, database)
    assert validate_entrez_arguments(selected) == selected
    spec = entrez_request_spec(selected)
    assert spec["url"] == "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/e" + operation + ".fcgi"
    assert spec["service"] == "ncbi_entrez" and spec["method"] == "GET"
    assert spec["follow_redirects"] is False and spec["max_bytes"] == MAX_BYTES
    assert spec["params"]["db"] == database and spec["params"]["retmode"] == "json"
    assert "query_key" not in spec["params"] and "WebEnv" not in spec["params"]
    if operation == "search": assert spec["params"]["term"] == selected["term"]
    else: assert spec["params"]["id"] == "1,2"


@pytest.mark.parametrize("database", list(FETCH_FORMATS))
def test_fetch_uses_only_existing_inspected_native_contracts(database):
    selected = arguments("fetch", database, **({"ids": ["SRR6263255"]} if database == "sra" else {}))
    spec = entrez_request_spec(selected)
    assert spec["url"].endswith("/efetch.fcgi")
    assert spec["params"]["retmode"] == ("text" if database in {"protein", "nuccore"} else "xml")
    if database in {"protein", "nuccore"}:
        assert spec["params"]["rettype"] == ("gp" if database == "protein" else "gbwithparts")
    elif database == "sra": assert spec["params"]["rettype"] == "docset"
    else: assert "rettype" not in spec["params"]


@pytest.mark.parametrize("selected", [arguments(max_bytes=True), arguments(max_bytes=0), arguments(retstart=True),
    arguments(retmax=101), arguments(url="https://elsewhere.invalid"), arguments(database="pubmed"),
    arguments(database="biosample"), arguments(database="bioproject"), arguments(database="pmc"),
    arguments("fetch", "gds"), arguments("fetch", "sra", ids=["SRR6263255"], native_format="unsupported"), arguments("fetch", "assembly"),
    arguments("summary", ids=["SRR1"]), arguments("summary", ids=["1\n"]),
    arguments("fetch", "gene", native_format="json"), arguments(native_format="xml"), arguments(term="line\nbreak"),
    arguments("fetch", "nuccore", start=0, end=4), arguments("fetch", "gene", ids=["1", "1"])])
def test_unestablished_formats_and_arbitrary_or_mistyped_operands_are_unexposed(selected):
    with pytest.raises(ValueError): validate_entrez_arguments(selected)


def test_search_preserves_native_tokens_duplicate_ids_unknown_fields_and_query_population():
    raw = '{"esearchresult":{"count":"00012","retstart":"0","retmax":"2","idlist":["7","7"],"querytranslation":"unchanged","unknown":1e-9999}}'
    value = result(raw)
    assert value["native_text"] == raw
    assert value["population"]["matching_count_native"] == "00012"
    assert value["population"]["returned_record_count"] == 2
    assert value["population"]["returned_id_order_native"] == ["7", "7"]
    assert value["population"]["coverage"] == "selected_response_only"
    assert [row["identifier"] for row in value["records"]] == ["7", "7"]
    fields = value["native_document"]["value"]["members"][0]["value"]["members"]
    assert fields[-1] == dict(name="unknown", value=dict(kind="number", token="1e-9999"))
    assert "native_number_token_required" in codes(value)
    assert next(row["native_locator"] for row in value["issues"] if row["code"] == "native_number_token_required").startswith("/native_document/value/")


def test_duplicate_native_count_has_no_first_or_last_winner_and_large_string_count_is_exact():
    value = result('{"esearchresult":{"count":"1","count":"2","retstart":"0","retmax":"2","idlist":[]}}')
    assert value["population"]["matching_count_native"] is None
    assert "native_duplicate_member" in codes(value)
    count = "9" * 5000
    value = result(json.dumps(dict(esearchresult=dict(count=count, retstart="0", retmax="2", idlist=[]))))
    assert value["population"]["matching_count_native"] == count


@pytest.mark.parametrize("body, expected", [('{"count":"0","retstart":"0","retmax":"2","idlist":[]}', 0),
    ('{"count":"0","retstart":"0","retmax":"2"}', None),
    ('{"count":"0","retstart":"0","retmax":"2","idlist":null}', None)])
def test_observed_empty_list_is_distinct_from_missing_or_null_records(body, expected):
    value = result('{"esearchresult":' + body + '}')
    assert value["population"]["returned_record_count"] == expected
    assert value["population"]["matching_count_native"] == "0"


def test_summary_preserves_native_uid_array_independently_of_object_member_order_and_repeats():
    raw = '{"result":{"uids":["2","1","2"],"1":{"uid":"1","title":"first"},"2":{"uid":"2","v":0},"2":{"uid":"2","v":null}}}'
    value = result(raw, arguments("summary"))
    assert value["population"]["returned_id_order_native"] == ["2", "1", "2"]
    assert [row["identifier"] for row in value["records"]] == ["1", "2", "2"]
    assert value["population"]["records_order"] == "native_representation_order"
    assert "native_duplicate_member" in codes(value)
    assert "native_uid_membership_conflict" not in codes(value)
    assert len({row["native_locator"] for row in value["records"]}) == 3


@pytest.mark.parametrize("body, expected", [('{}', None), ('{"uids":null}', None),
    ('{"uids":[]}', 0), ('{"uids":[],"metadata":{"unknown":"retained"}}', 0)])
def test_summary_missing_uid_inventory_is_not_an_observed_zero_and_unknown_objects_are_not_documents(body, expected):
    value = result('{"result":' + body + '}', arguments("summary"))
    assert value["population"]["returned_record_count"] == expected and value["records"] == []


def test_summary_record_error_retains_requested_record_and_failed_native_meaning():
    body = '{"result":{"uids":["1"],"1":{"uid":"1","error":"selected record unavailable"}}}'
    value = result(body, arguments("summary", ids=["1"]))
    assert value["native_response_state"] == "error" and value["population"]["returned_record_count"] == 1
    assert value["records"][0]["exact_requested_identifier"] is True and "native_record_error" in codes(value)
    assert value["native_text"] == body


@pytest.mark.parametrize("status, body, native_state", [(200, '{"error":"native failure"}', "error"),
    (503, '{"error":"native failure"}', "error"), (503, '<html>original failure</html>', "unknown")])
def test_http_and_native_errors_keep_complete_original_bodies_and_distinct_states(status, body, native_state):
    value = result(body, status=status)
    assert value["response"]["http_status"] == status and value["native_text"] == body
    assert value["native_response_state"] == native_state
    assert value["population"]["returned_record_count"] is None
    assert ("http_not_success" in codes(value)) == (status != 200)


def test_complete_valid_native_data_and_incomplete_capture_are_independent():
    body = '{"esearchresult":{"count":"0","retstart":"0","retmax":"2","idlist":[],"errorlist":{},"warninglist":{}}}'
    complete = result(body)
    assert complete["representation_state"] == "complete" and complete["native_response_state"] == "data"
    partial = result(body, body_complete=False, body_capture_failure="provider_response_byte_limit")
    assert partial["parse_state"] == "json" and partial["population"]["returned_record_count"] == 0
    assert partial["representation_state"] == "partial" and "capture_not_complete" in codes(partial)
    assert partial["population"]["coverage"] == "selected_response_only"


@pytest.mark.parametrize("change", ["selected", "url", "method", "redirect", "accept", "body", "limit", "source", "artifact", "timeout", "header_type"])
def test_selected_request_transport_and_closed_reference_associations_are_mandatory(change):
    selected = arguments()
    saved = snapshot('{"esearchresult":{}}', selected)
    source, artifact = SOURCE, "artifact_" + hashlib.sha256(saved.content).hexdigest()
    if change == "selected": saved.request["retmax"] = 1
    elif change == "url": saved.transport["request"]["url"] = "https://other.invalid/"
    elif change == "method": saved.transport["request"]["method"] = "POST"
    elif change == "redirect": saved.transport["request_policy"]["automatic_redirects"] = True
    elif change == "accept": saved.transport["request"]["headers"]["Accept"] = "text/plain"
    elif change == "body": saved.transport["request"]["body_sha256"] = "f" * 64
    elif change == "limit": saved.transport["response_byte_limit"] = True
    elif change == "source": source += "\n"
    elif change == "timeout": saved.transport["request_policy"]["timeout_seconds"] = 10 ** 1000
    elif change == "header_type": saved.transport["request"]["headers"] = {1: "application/json"}
    else: artifact = "artifact_" + "0" * 64
    with pytest.raises(ValueError): entrez_result(saved, arguments=selected, source_ref=source, artifact_ref=artifact)


def test_gene_xml_keeps_doctype_attributes_unknown_elements_and_record_identity_without_dereference(monkeypatch):
    def forbidden(*args, **kwargs): raise AssertionError("pure XML parser attempted network or execution")
    monkeypatch.setattr("socket.create_connection", forbidden)
    monkeypatch.setattr("subprocess.Popen", forbidden)
    raw = '<!DOCTYPE Entrezgene-Set SYSTEM "https://example.invalid/not-opened.dtd"><Entrezgene-Set><Entrezgene native="unknown"><Entrezgene_track-info><Gene-track><Gene-track_geneid>1</Gene-track_geneid></Gene-track></Entrezgene_track-info><unknown>original</unknown></Entrezgene></Entrezgene-Set>'
    value = result(raw, arguments("fetch", "gene"))
    assert value["records"][0]["identifier"] == "1"
    xml = value["native_document"]["value"]
    assert xml["doctype"]["system_id"] == "https://example.invalid/not-opened.dtd"
    assert xml["root"]["children"][0]["attributes"] == [dict(name="native", value="unknown")]
    assert value["native_text"] == raw


def test_taxonomy_identity_is_the_selected_taxon_not_an_ancestor_taxid():
    raw = '<TaxaSet><Taxon><TaxId>1</TaxId><LineageEx><Taxon><TaxId>2</TaxId></Taxon></LineageEx></Taxon></TaxaSet>'
    value = result(raw, arguments("fetch", "taxonomy"))
    assert [row["identifier"] for row in value["records"]] == ["1"]
    assert value["native_text"] == raw


def test_genbank_fetch_reuses_existing_record_feature_reader_and_retains_original_text():
    raw = ('LOCUS       TEST0001                   4 bp    DNA     linear   UNA 01-JAN-2000\n'
        'DEFINITION  Engineered supplied record.\nACCESSION   TEST0001\nVERSION     TEST0001.1\n'
        'KEYWORDS    .\nSOURCE      synthetic construct\n  ORGANISM  synthetic construct\n'
        'FEATURES             Location/Qualifiers\n     source          1..4\n'
        '     misc_feature    <2..>3\n                     /note="retained marker"\n'
        'ORIGIN\n        1 atgc\n//\n')
    value = result(raw, arguments("fetch", "nuccore", ids=["TEST0001.1"]))
    assert value["parse_state"] == "genbank" and value["records"][0]["identifier"] == "TEST0001.1"
    assert value["native_text"] == raw
    native = value["native_document"]["value"]["items"][0]["members"]
    assert next(row["value"]["value"] for row in native if row["name"] == "coordinate_system") == "zero_based_half_open"


def test_sra_record_and_embedded_native_objects_preserve_identity_levels_without_mate_or_count_inference():
    exp = '<Study acc="SRP1"/><Sample accession="SRS1"/><Experiment acc="SRX1"/><Run acc="SRR1" files="two names" total_spots="0"/>'
    body = json.dumps(dict(result=dict(uids=["1"], **{"1": dict(uid="1", expxml=exp, run_id="SRR2", unknown={"original": None})})))
    value = result(body, arguments("summary", "sra", ids=["1"]))
    assert {(row["namespace"], row["identifier"]) for row in value["associations"]} == {
        ("sra_study", "SRP1"), ("sra_sample", "SRS1"), ("sra_experiment", "SRX1"), ("sra_run", "SRR1"), ("sra_run", "SRR2")}
    assert value["population"]["returned_record_count"] == 1 and value["population"]["matching_count_native"] is None
    assert value["native_text"] == body and all(row["native_relation"] for row in value["associations"])
    assert "read_count" not in value and "mate" not in value
    assert value["embedded_xml"][0]["document"]["fragment_wrapper"] is True
    assert value["embedded_xml"][0]["document"]["root"]["tag"] == "#fragment"


def test_malformed_embedded_sra_xml_does_not_discard_its_valid_native_summary():
    body = json.dumps(dict(result=dict(uids=["1"], **{"1": dict(uid="1", expxml="<Study acc='SRP1'>")})))
    value = result(body, arguments("summary", "sra", ids=["1"]))
    assert value["parse_state"] == "json" and value["native_response_state"] == "data"
    assert value["population"]["returned_record_count"] == 1 and value["native_text"] == body
    assert value["embedded_xml"][0]["document"] is None and "invalid_native_xml_fragment" in codes(value)


def test_embedded_biosample_bioproject_identifiers_remain_native_metadata_without_database_bindings():
    body = '{"result":{"uids":["1"],"1":{"uid":"1","biosample":"SAMN00000001","bioproject":"PRJNA1"}}}'
    value = result(body, arguments("summary", "sra", ids=["1"]))
    assert value["native_text"] == body
    fields = value["native_document"]["value"]["members"][0]["value"]["members"][1]["value"]["members"]
    assert {item["name"]: item["value"]["value"] for item in fields} == {
        "uid": "1", "biosample": "SAMN00000001", "bioproject": "PRJNA1"}
    assert "biosample" not in DATABASES and "bioproject" not in DATABASES


@pytest.mark.parametrize("raw", [b'NaN', b'\xff', b'{"native":"\\ud800"}', b'{"unfinished":'])
def test_invalid_native_representations_remain_retained_and_unavailable(raw):
    value = result(raw)
    assert value["native_document"] is None and value["parse_state"] == "unavailable"
    assert value["population"]["returned_record_count"] is None


@pytest.mark.parametrize("change", ["reference", "count", "document", "extra", "native_population"])
def test_closed_result_validation_checks_reference_and_retained_document_meanings(change):
    value = result('{"esearchresult":{"count":"1","retstart":"0","retmax":"2","idlist":["1"]}}')
    if change == "reference": value["raw_artifact_ref"] += "\n"
    elif change == "count": value["population"]["returned_record_count"] = 0
    elif change == "document": value["native_document"]["value"]["members"][0]["value"]["members"][0]["value"]["value"] = "2"
    elif change == "native_population": value["population"]["matching_count_native"] = "999"
    else: value["extra"] = True
    with pytest.raises(ValueError): validate_entrez_result(value)
    schema = entrez_result_schema(); schema.clear()
    assert entrez_result_schema()["additionalProperties"] is False and ARGUMENTS_SCHEMA["oneOf"]


# NCBI documents SNP UIDs as rs numbers and ESearch/ESummary as shared Entrez
# operations. These are engineered JSON controls, not a live dbSNP response:
# https://www.ncbi.nlm.nih.gov/sites/books/NBK25497/pdf/Bookshelf_NBK25497.pdf
# https://www.ncbi.nlm.nih.gov/sites/books/NBK25499/pdf/Bookshelf_NBK25499.pdf
@pytest.mark.parametrize("operation", ["search", "summary"])
def test_snp_extension_preserves_literal_terms_decimal_uid_order_and_single_request(operation):
    selected = (arguments("search", "snp", term="rs328[RS] OR rs699[RS]", retstart=7, retmax=2)
        if operation == "search" else arguments("summary", "snp", ids=["699", "328", "699"]))
    before = deepcopy(selected)
    spec = entrez_request_spec(selected)
    assert selected == before and spec["params"]["db"] == "snp" and spec["params"]["retmode"] == "json"
    assert spec["method"] == "GET" and spec["follow_redirects"] is False
    assert not {"query_key", "WebEnv", "usehistory"}.intersection(spec["params"])
    if operation == "search":
        assert spec["params"]["term"] == selected["term"]
        assert (spec["params"]["retstart"], spec["params"]["retmax"]) == (7, 2)
    else:
        assert spec["params"]["id"] == "699,328,699"


def test_snp_addition_keeps_every_old_database_and_fetch_interpretation():
    assert DATABASES == ("protein", "nuccore", "gene", "taxonomy", "assembly", "gds", "sra", "snp")
    assert FETCH_FORMATS == dict(protein="genpept", nuccore="genbank", gene="gene_xml", taxonomy="taxonomy_xml",
        sra="sra_experiment_package_xml")
    assert [branch["properties"]["database"] for branch in ARGUMENTS_SCHEMA["oneOf"][:2]] == [
        {"enum": list(DATABASES)}, {"enum": list(DATABASES)}]
    assert all(branch["properties"]["database"].get("const") != "snp" for branch in ARGUMENTS_SCHEMA["oneOf"][2:])


@pytest.mark.parametrize("selected", [arguments("fetch", "snp", native_format="json"),
    arguments("fetch", "snp", native_format="snp_xml"), arguments("summary", "snp", ids=["rs699"]),
    arguments("summary", "snp", ids=["ss699"]), arguments("summary", "snp", ids=[699]),
    arguments("summary", "snp", ids=["699\n"]), arguments("summary", "snp", native_format="xml"),
    arguments("search", "snp", variant_id="rs699")])
def test_snp_fetch_rs_prefix_conversion_and_implicit_alternate_selectors_are_unexposed(selected):
    with pytest.raises(ValueError): validate_entrez_arguments(selected)


def test_snp_search_keeps_total_matches_window_native_id_occurrences_and_unknown_associations():
    raw = ('{"esearchresult":{"count":"00027","retstart":"7","retmax":"2",'
        '"idlist":["699","699"],"querytranslation":"literal native translation",'
        '"native_associations":{"gene_ids":["1","1"],"assembly":null,"frequency":0},"unknown":1e-9999}}')
    value = result(raw, arguments("search", "snp", term="rs699[RS]", retstart=7, retmax=2))
    assert value["native_text"] == raw
    assert value["population"] == dict(database="snp", unit="native_record_occurrences", coverage="selected_response_only",
        matching_count_native="00027", retstart_native="7", retmax_native="2", requested_id_count=None,
        returned_record_count=2, returned_id_order_native=["699", "699"], records_order="native_representation_order")
    assert [record["identifier"] for record in value["records"]] == ["699", "699"]
    assert value["associations"] == []  # Unknown native fields are retained, not mapped to inferred entities.
    assert value["native_document"]["value"]["members"][0]["value"]["members"][-1] == dict(
        name="unknown", value=dict(kind="number", token="1e-9999"))


@pytest.mark.parametrize("body,count", [('"idlist":[]', 0), ('"idlist":null', None), ('"unknown":[]', None)])
def test_snp_search_explicit_empty_and_missing_inventory_are_different_native_states(body, count):
    value = result('{"esearchresult":{"count":"0","retstart":"7","retmax":"2",' + body + '}}',
        arguments("search", "snp", retstart=7))
    assert value["population"]["returned_record_count"] == count
    assert value["population"]["matching_count_native"] == "0"


def test_snp_summary_preserves_ordered_native_documents_duplicates_and_lexical_data_without_rs_mapping():
    raw = ('{"result":{"uids":["699","328","699"],"328":{"uid":"328","snp_id":328},'
        '"699":{"uid":"699","alleles":"A/G","native_associations":{"assembly":null,"frequency":0}},'
        '"699":{"uid":"699","frequency":null,"unknown":1e-9999}}}')
    value = result(raw, arguments("summary", "snp", ids=["328", "699", "328"]))
    assert value["native_text"] == raw and value["population"]["requested_id_count"] == 3
    assert value["population"]["returned_id_order_native"] == ["699", "328", "699"]
    assert [record["identifier"] for record in value["records"]] == ["328", "699", "699"]
    assert value["population"]["returned_record_count"] == 3 and value["population"]["matching_count_native"] is None
    assert all(record["exact_requested_identifier"] for record in value["records"])
    assert {"native_duplicate_member", "native_number_token_required"} <= set(codes(value))
    assert value["associations"] == [] and validate_entrez_result(value) == value


@pytest.mark.parametrize("body,expected", [('"uids":[]', 0), ('"uids":null', None), ('"unknown":[]', None)])
def test_snp_summary_native_empty_inventory_never_replaces_missing_or_null_with_zero(body, expected):
    value = result('{"result":{' + body + '}}', arguments("summary", "snp", ids=["699"]))
    assert value["population"]["returned_record_count"] == expected
    assert value["population"]["requested_id_count"] == 1 and value["population"]["matching_count_native"] is None


def sra_fetch_arguments(**changes):
    return arguments("fetch", "sra", **{"ids": ["SRR6263255"], **changes})


def sra_native_xml():
    from pathlib import Path
    raw = (Path(__file__).parent / "fixtures" / "ncbi_sra" / "experiment_package.xml").read_bytes()
    assert len(raw) == 7802 and hashlib.sha256(raw).hexdigest() == "e2e72cc189d988194ef9ab9faff6b96132749afd7cdc3293f386902544e45b10"
    return raw


def sra_docset(runs, *, package=True):
    """Explicitly engineered XML, never a native transfer or archive witness."""
    middle = "<EXPERIMENT_PACKAGE><RUN_SET>" + runs + "</RUN_SET></EXPERIMENT_PACKAGE>" if package else runs
    return "<EXPERIMENT_PACKAGE_SET>" + middle + "</EXPERIMENT_PACKAGE_SET>"


@pytest.mark.parametrize("accession", ["SRR6263255", "ERR123", "DRR123"])
def test_sra_fetch_selects_one_literal_run_and_exact_docset_wire_without_uid_or_followup(accession):
    selected = arguments("fetch", "sra", ids=[accession])
    spec = entrez_request_spec(selected)
    assert validate_entrez_arguments(selected) == selected
    assert spec == dict(service="ncbi_entrez", url="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
        method="GET", params=dict(db="sra", tool="gene-annotation-episode", id=accession, retmode="xml", rettype="docset"),
        media_type="application/xml", max_bytes=MAX_BYTES, follow_redirects=False)


@pytest.mark.parametrize("changes", [dict(ids=[]), dict(ids=["1"]), dict(ids=["SRX3369480"]),
    dict(ids=["SRP124452"]), dict(ids=["srr6263255"]), dict(ids=["SRR6263255\n"]),
    dict(ids=["SRR6263255", "SRR6263255"]), dict(ids=["SRR6263255", "SRR2"]),
    dict(ids=[True]), dict(native_format="xml"), dict(rettype="docset"), dict(url="https://elsewhere.invalid")])
def test_sra_fetch_other_identity_roles_multiple_requests_and_unselected_options_are_unexposed(changes):
    selected = arguments("fetch", "sra", ids=["SRR6263255"])
    selected.update(changes)
    with pytest.raises(ValueError):
        validate_entrez_arguments(selected)


def test_sra_native_experiment_package_is_retained_exactly_without_read_or_archive_inference():
    from gene_annotation_episode import ncbi_entrez_acquisition as native
    raw = sra_native_xml()
    value = result(raw, sra_fetch_arguments())
    assert value["native_text"].encode() == raw and value["parse_state"] == "xml"
    assert value["native_response_state"] == "data" and value["representation_state"] == "complete"
    assert native.entrez_selected_identity_state(value) == "matched"
    assert value["population"]["requested_id_count"] == value["population"]["returned_record_count"] == 1
    assert value["population"]["returned_id_order_native"] == ["SRR6263255"]
    assert value["records"][0]["identifier"] == "SRR6263255" and value["records"][0]["reported_uid"] is None
    assert value["records"][0]["exact_requested_identifier"] is True
    nodes = list(native._walk_xml(value["native_document"]["value"]["root"], "/root"))
    advertised = [{item["name"]: item["value"] for item in node["attributes"]}
        for node, _ in nodes if node["tag"] == "SRAFile"]
    assert [row["semantic_name"] for row in advertised] == ["fastq", "SRA Normalized", "SRA Lite"]
    assert [row["size"] for row in advertised] == ["1210898407", "937095532", "672505972"]
    assert advertised[0].get("url") is None and advertised[1]["md5"] == "36d7ad948f9a82a4743a77a4bb9a5288"
    assert {"sra_run", "sra_experiment", "sra_sample", "sra_study"} <= {item["namespace"] for item in value["associations"]}
    assert any(node["tag"] == "SINGLE" for node, _ in nodes)
    assert any(node["tag"] == "Read" and dict((item["name"], item["value"]) for item in node["attributes"]).get("count") == "0"
        for node, _ in nodes)
    assert value["population"]["matching_count_native"] is None and value["embedded_xml"] == []


def test_sra_fetch_preserves_sibling_duplicate_runs_and_native_order_without_relabelling_the_request():
    from gene_annotation_episode.ncbi_entrez_acquisition import entrez_selected_identity_state
    raw = sra_docset('<RUN accession="SRR9" alias="sibling"/><RUN accession="SRR6263255"/>'
        '<RUN accession="SRR6263255" unknown="literal"/>')
    value = result(raw, sra_fetch_arguments())
    assert value["native_text"] == raw
    assert value["population"]["returned_record_count"] == 3
    assert value["population"]["returned_id_order_native"] == ["SRR9", "SRR6263255", "SRR6263255"]
    assert [row["exact_requested_identifier"] for row in value["records"]] == [False, True, True]
    assert all(row["reported_uid"] is None for row in value["records"])
    assert entrez_selected_identity_state(value) == "matched"


@pytest.mark.parametrize("body,count,order,state", [
    (sra_docset("", package=False), 0, [], "empty"),
    (sra_docset(""), 0, [], "empty"),
    (sra_docset("<EXPERIMENT_PACKAGE/>", package=False), None, None, "unavailable"),
    (sra_docset("<RUN/>"), 1, None, "unavailable"),
    (sra_docset('<RUN accession="SRR9"/>'), 1, ["SRR9"], "mismatch"),
    (sra_docset('<RUN accession="SRR9" alias="SRR6263255"/>'), 1, ["SRR9"], "mismatch"),
    (sra_docset('<RUN accession="SRR62632550"/>'), 1, ["SRR62632550"], "mismatch"),
    (sra_docset('<RUN accession="SRR6263255"><IDENTIFIERS><PRIMARY_ID>SRR9</PRIMARY_ID></IDENTIFIERS></RUN>'),
        1, ["SRR6263255"], "mismatch"),
])
def test_sra_native_empty_missing_and_conflicting_identity_are_distinct_without_alias_guessing(body, count, order, state):
    from gene_annotation_episode.ncbi_entrez_acquisition import entrez_selected_identity_state
    value = result(body, sra_fetch_arguments())
    assert value["population"]["returned_record_count"] == count
    assert value["population"]["returned_id_order_native"] == order
    assert value["population"]["requested_id_count"] == 1 and value["native_text"] == body
    assert entrez_selected_identity_state(value) == state


def test_sra_fetch_validation_rejects_changed_run_record_count_or_retained_native_document():
    value = result(sra_native_xml(), sra_fetch_arguments())
    for field in ("identity", "population", "tree"):
        changed = deepcopy(value)
        if field == "identity":
            changed["records"][0]["identifier"] = "SRR9"
        elif field == "population":
            changed["population"]["returned_record_count"] = 0
        else:
            changed["native_document"]["value"]["root"]["children"] = []
        with pytest.raises(ValueError, match="ncbi_entrez_native_result_conflict"):
            validate_entrez_result(changed)
