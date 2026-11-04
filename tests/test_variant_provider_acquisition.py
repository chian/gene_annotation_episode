"""Engineered EVA/gnomAD controls, not live or deployed response evidence.

Native shape authorities read in full before these controls were authored:
https://github.com/EBIvariation/eva-ws/blob/master/eva-server/src/main/java/uk/ac/ebi/eva/server/ws/VariantWSServer.java
https://github.com/EBIvariation/eva-ws/blob/master/eva-server/src/main/java/uk/ac/ebi/eva/server/ws/RegionWSServer.java
https://github.com/EBIvariation/eva-ws/blob/master/eva-lib/src/main/java/uk/ac/ebi/eva/lib/utils/QueryUtils.java
https://github.com/broadinstitute/gnomad-browser/blob/main/graphql-api/src/graphql/types/query.graphql
https://github.com/broadinstitute/gnomad-browser/blob/main/graphql-api/src/graphql/types/variant.graphql
https://github.com/broadinstitute/gnomad-browser/blob/main/graphql-api/src/graphql/resolvers/aliases.ts
https://github.com/EBIvariation/eva-ws/blob/master/eva-lib/src/main/java/uk/ac/ebi/eva/lib/utils/QueryResult.java
https://github.com/EBIvariation/eva-ws/blob/master/eva-server/src/main/java/uk/ac/ebi/eva/server/ws/contigalias/ContigAliasService.java
https://github.com/EBIvariation/variation-commons/blob/master/variation-commons-mongodb/src/main/java/uk/ac/ebi/eva/commons/mongodb/repositories/VariantRepositoryImpl.java
https://github.com/EBIvariation/variation-commons/blob/master/variation-commons-core/src/main/java/uk/ac/ebi/eva/commons/core/models/AbstractVariant.java
"""
import base64
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from urllib.parse import urlencode

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.acquisition import PublicClients, SourceSnapshot
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from gene_annotation_episode import variant_provider_acquisition as provider


EVA, GNOMAD = provider.OPERATIONS
SOURCE = "source_" + "a" * 24  # Pure receipt shape control only; publishers use real Store Sources.
GENE = "ENSG00000000001"
ARGUMENTS = {
    "eva_variant": dict(request_type="variant", species="mmusculus_grcm38", variant_id="rs699", limit=2, skip=0, max_bytes=65536),
    "eva_region": dict(request_type="region", species="mmusculus_grcm38", chromosome="1", start=7, end=12, limit=2, skip=4, max_bytes=65536),
    "gnomad_variant": dict(request_type="variant", dataset="gnomad_r4", reference_genome="GRCh38",
        variant_id="1-7-A-G", fields=["rsids", "exome", "genome", "joint", "flags"], max_bytes=65536),
    "gnomad_search": dict(request_type="gene_search", query="Literal symbol prefix", reference_genome="GRCh38", max_bytes=65536),
    "gnomad_gene": dict(request_type="gene", gene_id=GENE, dataset="gnomad_r4", reference_genome="GRCh38",
        fields=["symbol", "gencode_symbol", "name", "chrom", "start", "stop", "strand", "variants"], max_bytes=65536),
}
CASES = tuple(ARGUMENTS)


def operation(case):
    return EVA if case.startswith("eva_") else GNOMAD


def sequencing(*, joint=False):
    value = dict(ac=0, an=0, homozygote_count=None, hemizygote_count=None, filters=["AC0"],
        populations=[None, dict(id="native-group", ac=0, an=0, homozygote_count=0, hemizygote_count=None)])
    if not joint: value["af"] = 0
    return value


def variant():
    return dict(variant_id="1-7-A-G", reference_genome="GRCh38", chrom="1", pos=7, ref="A", alt="G",
        rsids=["rs699", "rs328"], exome=sequencing(), genome=None, joint=sequencing(joint=True), flags=[])


def eva_row():
    return dict(chromosome="NC_000067.6", start=7, end=9, reference="", alternate="ATG", mainId="rs699", ids=["rs699"],
        sourceEntries=[dict(fileId="native-file", studyId="native-study", format="GT:AD", secondaryAlternates=["C"],
            samplesDataMap={"sample-A": {"GT": "0|1", "AD": "0,7"}, "sample-B": {"GT": "./.", "AD": "."}},
            cohortStats={"native-cohort": {"alleleCount": 0, "alleleNumber": 0, "alleleFrequency": None}})])


def eva_document(rows, *, skip=-1):
    return dict(apiVersion="v1", warning="", error="", queryOptions={"limit": 2, "skip": skip},
        response=[dict(id="", numResults=len(rows), numTotalResults=99, warningMsg="", errorMsg="", result=rows)])


def document(case):
    if case.startswith("eva_"):
        row = eva_row()
        if case == "eva_region": row["chromosome"] = "1"
        return eva_document([row], skip=4 if case == "eva_region" else -1)
    if case == "gnomad_variant": return {"data": {"variant": variant()}}
    if case == "gnomad_search": return {"data": {"gene_search": [dict(ensembl_id=GENE, ensembl_version="7", symbol=None)]}}
    return {"data": {"gene": dict(gene_id=GENE, gene_version="7", reference_genome="GRCh38", symbol="NATIVE",
        gencode_symbol="NATIVE", name=None, chrom="1", start=3, stop=15, strand="+", variants=[variant()])}}


def capture(case, *, arguments=None, raw=None, transport_changes=None):
    args = deepcopy(ARGUMENTS[case] if arguments is None else arguments)
    spec = provider.provider_request_spec(operation(case), args)
    raw = json.dumps(document(case), ensure_ascii=True, separators=(",", ":")).encode() if raw is None else raw
    address = spec["url"] + ("?" + urlencode(spec["params"], doseq=True) if spec["params"] else "")
    request = dict(url=address, method="GET" if spec["body"] is None else "POST", headers={"Accept": "application/json"})
    if spec["body"] is not None:
        request.update(body_base64=base64.b64encode(spec["body"]).decode(), body_sha256=hashlib.sha256(spec["body"]).hexdigest())
        request["headers"]["Content-Type"] = "application/json"
    transport = dict(request=request, effective_url=address, status=200,
        request_policy=dict(timeout_seconds=30, automatic_redirects=False), response_byte_limit=args["max_bytes"],
        body_complete=True, retained_body_bytes=len(raw), observed_body_bytes=len(raw), declared_body_bytes=len(raw),
        headers={"content-type": "application/json"}, header_items=[("Content-Type", "application/json")])
    transport.update(transport_changes or {})
    return SourceSnapshot(spec["service"], spec["url"], deepcopy(spec["params"]), "2026-11-01T00:00:00Z", raw,
        "application/json", transport)


def value(case, *, arguments=None, raw=None, transport_changes=None):
    saved = capture(case, arguments=arguments, raw=raw, transport_changes=transport_changes)
    return provider.provider_value(saved, operation=operation(case), arguments=ARGUMENTS[case] if arguments is None else arguments,
        artifact_ref="artifact_" + hashlib.sha256(saved.content).hexdigest())


def receipt(case, **kwargs):
    return provider.provider_receipt(value(case, **kwargs), source_ref=SOURCE)


def member(node, name):
    rows = [row["value"] for row in node["members"] if row["name"] == name]
    assert len(rows) == 1
    return rows[0]


def forbidden(*args, **kwargs):
    raise AssertionError("pure engineered variant acquisition control attempted unselected work")


@pytest.mark.parametrize("case", CASES)
def test_explicit_selected_protocol_has_one_fixed_request_and_no_native_call(case, monkeypatch):
    monkeypatch.setattr(PublicClients, "_http", forbidden)
    monkeypatch.setattr("socket.create_connection", forbidden)
    args = deepcopy(ARGUMENTS[case]); original = deepcopy(args)
    spec = provider.provider_request_spec(operation(case), args)
    assert args == original and provider.validate_provider_arguments(operation(case), args) == args
    assert spec["follow_redirects"] is False and spec["max_bytes"] == args["max_bytes"]
    Draft202012Validator(provider.provider_argument_schema(operation(case))).validate(args)
    if case.startswith("eva_"):
        assert spec["service"] == "eva" and spec["url"].startswith(provider.EVA_ROOT + "/")
        assert spec["params"] == dict(species=args["species"], limit=args["limit"], skip=args["skip"])
        assert spec["body"] is spec["content_type"] is None
    else:
        assert spec["service"] == "gnomad" and spec["url"] == provider.GNOMAD_ROOT and spec["params"] == {}
        body = json.loads(spec["body"])
        assert set(body) == {"query", "variables"} and "mutation" not in body["query"]
        assert body["variables"].get("dataset") == args.get("dataset")
        assert "offset" not in body["query"] and "limit" not in body["query"] and "cursor" not in body["query"]
    checked = value(case)
    assert provider.validate_provider_value(checked) == checked and checked["failure_code"] is None
    Draft202012Validator(provider.provider_value_schema()).validate(checked)


def test_gene_search_text_is_only_a_variable_and_never_selects_the_first_match():
    args = {**ARGUMENTS["gnomad_search"], "query": 'NATIVE") { mutation { forbidden } } #'}
    spec = provider.provider_request_spec(GNOMAD, args); body = json.loads(spec["body"])
    assert body["variables"]["query"] == args["query"] and args["query"] not in body["query"]
    raw = b'{"data":{"gene_search":[{"ensembl_id":"ENSG00000000002","ensembl_version":"1","symbol":"SECOND"},{"ensembl_id":"ENSG00000000001","ensembl_version":"7","symbol":null}]}}'
    checked = value("gnomad_search", arguments=args, raw=raw)
    rows = member(member(checked["native_document"], "data"), "gene_search")["items"]
    assert [member(row, "ensembl_id")["value"] for row in rows] == ["ENSG00000000002", GENE]
    assert checked["identity_state"] == "confirmed" and checked["population_scope"] == "returned_response_only"
    assert any(row["code"] == "native_gene_search_is_capped_not_complete_population" for row in checked["qualifications"])


@pytest.mark.parametrize("case,changes", [
    ("eva_variant", {"request_type": "species"}), ("eva_variant", {"request_type": "submitted_variant"}),
    ("eva_region", {"limit": 10001}), ("eva_region", {"limit": True}), ("eva_region", {"skip": 1.0}),
    ("eva_region", {"chromosome": "1,2"}), ("eva_region", {"start": True}), ("eva_region", {"end": 6}),
    ("eva_variant", {"species": "inferred-default"}), ("eva_variant", {"max_bytes": 0}),
    ("gnomad_variant", {"dataset": "gnomad_r4_genomes"}), ("gnomad_variant", {"reference_genome": "GRCh37"}),
    ("gnomad_variant", {"variant_id": "rs699"}), ("gnomad_variant", {"fields": ["af"]}),
    ("gnomad_variant", {"fields": ["genome", "genome"]}), ("gnomad_variant", {"fields": "genome"}),
    ("gnomad_search", {"query": "line\nbreak"}), ("gnomad_gene", {"gene_id": "NATIVE"}),
    ("gnomad_gene", {"dataset": None}), ("gnomad_variant", {"query": "arbitrary GraphQL"}),
    ("gnomad_variant", {"url": "https://elsewhere.invalid"}), ("gnomad_variant", {"headers": {}}),
])
def test_unverified_protocols_defaults_wrong_types_and_arbitrary_transport_are_unexposed(case, changes):
    with pytest.raises(ValueError): provider.validate_provider_arguments(operation(case), {**ARGUMENTS[case], **changes})


@pytest.mark.parametrize("dataset,reference", list(provider.DATASET_REFERENCES.items()))
def test_every_explicit_dataset_reference_pair_has_no_default_or_reference_conversion(dataset, reference):
    args = {**ARGUMENTS["gnomad_variant"], "dataset": dataset, "reference_genome": reference}
    assert provider.validate_provider_arguments(GNOMAD, args) == args
    body = json.loads(provider.provider_request_spec(GNOMAD, args)["body"])
    assert body["variables"]["dataset"] == dataset
    with pytest.raises(ValueError): provider.validate_provider_arguments(GNOMAD,
        {**args, "reference_genome": "GRCh37" if reference == "GRCh38" else "GRCh38"})


def test_gene_identity_only_selection_has_explicit_null_dataset_and_no_unrequested_values():
    args = {**ARGUMENTS["gnomad_gene"], "dataset": None, "fields": []}
    body = json.loads(provider.provider_request_spec(GNOMAD, args)["body"])
    assert body["variables"] == dict(reference="GRCh38", id=GENE) and "DatasetId" not in body["query"]
    raw = json.dumps({"data": {"gene": dict(gene_id=GENE, gene_version="7", reference_genome="GRCh38")}}).encode()
    assert receipt("gnomad_gene", arguments=args, raw=raw)["acquired"] is True
    with pytest.raises(ValueError): provider.validate_provider_arguments(GNOMAD, {**args, "dataset": "gnomad_r4"})


def test_eva_raw_alleles_study_file_sample_and_cohort_associations_are_not_vcf_or_assembly_inference():
    raw = json.dumps(eva_document([eva_row(), eva_row()]), separators=(",", ":")).encode()
    checked = value("eva_variant", raw=raw)
    assert base64.b64decode(checked["raw"]["data"]) == raw and checked["raw"]["sha256"] == hashlib.sha256(raw).hexdigest()
    result = member(member(checked["native_document"], "response")["items"][0], "result")["items"]
    assert len(result) == 2 and member(result[0], "reference") == dict(kind="string", value="")
    assert member(result[0], "alternate")["value"] == "ATG"
    source = member(result[0], "sourceEntries")["items"][0]
    assert member(source, "studyId")["value"] == "native-study" and member(source, "fileId")["value"] == "native-file"
    assert member(member(member(source, "samplesDataMap"), "sample-B"), "GT")["value"] == "./."
    assert any(row["code"] == "requested_species_assembly_not_independent_native_confirmation" for row in checked["qualifications"])
    assert checked["population_scope"] == "returned_response_only" and "source_ref" not in checked


def test_gnomad_zero_null_qualifiers_and_full_rsids_are_literal_provider_values():
    checked = value("gnomad_variant")
    native = member(member(checked["native_document"], "data"), "variant")
    exome = member(native, "exome")
    assert member(exome, "an") == dict(kind="number", token="0")
    assert member(exome, "af") == dict(kind="number", token="0")
    assert member(native, "genome") == dict(kind="null", value=None)
    assert [row["value"] for row in member(native, "rsids")["items"]] == ["rs699", "rs328"]
    assert member(exome, "populations")["items"][0] == dict(kind="null", value=None)
    query = json.loads(provider.provider_request_spec(GNOMAD, ARGUMENTS["gnomad_variant"])["body"])["query"]
    assert "rsid " not in query and "populations { id ac an homozygote_count hemizygote_count }" in query
    assert receipt("gnomad_variant")["acquired"] is True


@pytest.mark.parametrize("case", ["eva_variant", "gnomad_variant"])
def test_unknown_duplicate_fields_and_number_tokens_are_retained_without_a_first_winner(case):
    raw = json.dumps(document(case), separators=(",", ":")).encode()[:-1] + b',"opaque":1e-9999,"opaque":1e99999}'
    checked = value(case, raw=raw)
    assert base64.b64decode(checked["raw"]["data"]) == raw
    assert checked["native_document"]["members"][-2:] == [dict(name="opaque", value=dict(kind="number", token="1e-9999")),
        dict(name="opaque", value=dict(kind="number", token="1e99999"))]
    assert {"native_duplicate_member", "native_number_token_required"} <= {row["code"] for row in checked["qualifications"]}
    assert provider.provider_receipt(checked, source_ref=SOURCE)["acquired"] is True


@pytest.mark.parametrize("case", ["eva_variant", "eva_region", "gnomad_search", "gnomad_gene"])
def test_explicit_empty_population_is_data_without_a_found_item_or_exhaustiveness_claim(case):
    doc = document(case)
    if case.startswith("eva_"): doc = eva_document([], skip=4 if case == "eva_region" else -1)
    elif case == "gnomad_search": doc["data"]["gene_search"] = []
    else: doc["data"]["gene"]["variants"] = []
    checked = value(case, raw=json.dumps(doc).encode())
    assert provider.provider_receipt(checked, source_ref=SOURCE)["acquired"] is True
    assert checked["identity_state"] == ("confirmed" if case == "gnomad_gene" else "empty")
    assert checked["population_scope"] == "returned_response_only"


@pytest.mark.parametrize("raw,code", [
    (b'{"data":{"variant":null}}', "native_result_unavailable"),
    (b'{"data":{}}', "native_result_unavailable"), (b'{}', "native_result_unavailable"),
    (b'{"errors":[{"message":"Variant not found"}],"data":{"variant":null}}', "native_error"),
    (b'{"errors":[{"message":"Multiple variants found"}],"data":{"variant":{"partial":true}}}', "native_error"),
    (b'{"errors":null,"data":{"variant":null}}', "native_representation_invalid"),
    (b'[]', "native_result_unavailable"), (b'{"unfinished":', "native_representation_invalid"),
    (b'NaN', "native_representation_invalid"), (b'\xff', "native_representation_invalid"),
])
def test_missing_invalid_and_graphql_error_are_not_observed_empty_or_data_success(raw, code):
    assert receipt("gnomad_variant", raw=raw) == provider.failed_provider_receipt("variant_provider_" + code, source_ref=SOURCE)


@pytest.mark.parametrize("case,change", [("gnomad_variant", "identity"), ("gnomad_variant", "reference"),
    ("gnomad_variant", "number_type"), ("gnomad_variant", "missing_selected"),
    ("gnomad_gene", "identity"), ("gnomad_gene", "reference"), ("gnomad_gene", "number_type"),
    ("gnomad_search", "missing_selected"), ("eva_variant", "identity"), ("eva_variant", "number_type")])
def test_native_identity_reference_types_and_selected_field_presence_are_not_url_claims(case, change):
    doc = document(case)
    if case.startswith("eva_"):
        row = doc["response"][0]["result"][0]
        if change == "identity": row.update(mainId="rs999", ids=["rs999"])
        else: row["start"] = True
    elif case == "gnomad_search": del doc["data"]["gene_search"][0]["symbol"]
    else:
        row = doc["data"]["variant" if case == "gnomad_variant" else "gene"]
        if change == "identity": row["variant_id" if case == "gnomad_variant" else "gene_id"] = "unselected"
        elif change == "reference": row["reference_genome"] = "GRCh37"
        elif change == "number_type":
            if case == "gnomad_variant": row["exome"]["ac"] = False
            else: row["start"] = 3.5
        else: del row["genome"]
    result = receipt(case, raw=json.dumps(doc).encode())
    assert result["acquired"] is False and result["data_ref"] is None and result["failure_code"] is not None


@pytest.mark.parametrize("field,replacement", [("chrom", "2"), ("pos", 8), ("ref", "C"), ("alt", "T")])
def test_gnomad_native_variant_id_cannot_detach_its_actual_coordinate_or_allele_fields(field, replacement):
    doc = document("gnomad_variant"); doc["data"]["variant"][field] = replacement
    assert receipt("gnomad_variant", raw=json.dumps(doc).encode())["acquired"] is False


@pytest.mark.parametrize("start,end", [(-1, 9), (7, -1), (10, 9)])
def test_eva_native_geometry_contradiction_is_retained_without_confirming_data(start, end):
    doc = document("eva_region"); doc["response"][0]["result"][0].update(start=start, end=end)
    checked = value("eva_region", raw=json.dumps(doc).encode())
    assert checked["native_document"] is not None
    assert provider.provider_receipt(checked, source_ref=SOURCE)["failure_code"] == "variant_provider_native_representation_invalid"


@pytest.mark.parametrize("field,replacement", [("limit", 1), ("skip", -1), ("skip", True)])
def test_eva_explicit_native_page_cannot_claim_a_different_selected_page(field, replacement):
    doc = document("eva_region"); doc["queryOptions"][field] = replacement
    result = receipt("eva_region", raw=json.dumps(doc).encode())
    assert result["acquired"] is False and result["data_ref"] is None


def test_eva_native_returned_and_total_counts_are_retained_distinct_from_unknown_and_requested_scope():
    doc = document("eva_region"); doc["response"][0]["numTotalResults"] = -1
    checked = value("eva_region", raw=json.dumps(doc).encode())
    native = member(checked["native_document"], "response")["items"][0]
    assert member(native, "numResults") == dict(kind="number", token="1")
    assert member(native, "numTotalResults") == dict(kind="number", token="-1")
    assert provider.provider_receipt(checked, source_ref=SOURCE)["acquired"] is True
    assert checked["population_scope"] == "returned_response_only"


@pytest.mark.parametrize("change", ["url", "service", "params", "method", "wire_url", "wire_body", "headers", "policy", "limit"])
def test_selected_capture_requires_exact_native_request_and_wire_material(change):
    saved = capture("gnomad_variant"); transport = deepcopy(saved.transport)
    if change == "url": saved = replace(saved, url=saved.url + "/other")
    elif change == "service": saved = replace(saved, service="other")
    elif change == "params": saved = replace(saved, request={"arbitrary": True})
    elif change == "method": transport["request"]["method"] = "GET"
    elif change == "wire_url": transport["request"]["url"] += "?arbitrary=1"
    elif change == "wire_body": transport["request"]["body_base64"] = base64.b64encode(b'{"query":"other"}').decode()
    elif change == "headers": transport["request"]["headers"]["Host"] = "elsewhere.invalid"
    elif change == "policy": transport["request_policy"]["automatic_redirects"] = True
    else: transport["response_byte_limit"] = True
    saved = replace(saved, transport=transport)
    with pytest.raises(ValueError): provider.provider_value(saved, operation=GNOMAD, arguments=ARGUMENTS["gnomad_variant"],
        artifact_ref="artifact_" + hashlib.sha256(saved.content).hexdigest())


@pytest.mark.parametrize("changes,code", [
    ({"status": None}, "http_status_unavailable"), ({"status": True}, "http_status_unavailable"),
    ({"status": 404}, "http_not_successful"), ({"status": 429}, "http_not_successful"),
    ({"status": 206}, "partial_response"), ({"header_items": [["Content-Range", "bytes 0-7/9"]]}, "partial_response"),
    ({"header_items": [["Content-Encoding", "gzip"]]}, "content_encoding_unsupported"),
    ({"body_complete": None}, "capture_incomplete"), ({"body_complete": False}, "capture_incomplete"),
    ({"body_capture_failure": "provider_response_byte_limit"}, "capture_incomplete"),
    ({"body_capture_error": "IncompleteRead"}, "capture_incomplete"),
    ({"retained_body_bytes": True}, "capture_identity_conflict"), ({"observed_body_bytes": 0}, "capture_identity_conflict"),
    ({"declared_body_bytes": "unknown"}, "capture_identity_conflict"), ({"declared_body_bytes": 1.0}, "capture_identity_conflict"),
])
def test_complete_capture_is_required_separately_from_native_data_and_population(changes, code):
    checked = value("gnomad_variant", transport_changes=changes)
    assert checked["native_document"] is not None and checked["identity_state"] == "confirmed"
    assert provider.provider_receipt(checked, source_ref=SOURCE) == provider.failed_provider_receipt("variant_provider_" + code, source_ref=SOURCE)


def test_declared_length_unknown_and_mime_qualification_do_not_discard_complete_native_data():
    checked = value("gnomad_variant", transport_changes={"declared_body_bytes": None,
        "header_items": [["Content-Type", "text/plain"]]})
    assert provider.provider_receipt(checked, source_ref=SOURCE)["acquired"] is True
    assert any(row["code"] == "native_content_type_qualification" for row in checked["qualifications"])


@pytest.mark.parametrize("change", ["raw_hash", "raw_size", "raw_size_bool", "base64", "version", "source_ref",
    "native_identity", "failure", "population", "qualifications", "selected", "transfer"])
def test_private_value_crossfield_validation_rejects_tampering_without_sources(change):
    checked = value("gnomad_variant")
    if change == "raw_hash": checked["raw"]["sha256"] = "0" * 64
    elif change == "raw_size": checked["raw"]["size_bytes"] += 1
    elif change == "raw_size_bool": checked["raw"]["size_bytes"] = True
    elif change == "base64": checked["raw"]["data"] += "\n"
    elif change == "version": checked["version"] = "other"
    elif change == "source_ref": checked["source_ref"] = SOURCE
    elif change == "native_identity": member(member(checked["native_document"], "data"), "variant")["members"][0]["value"]["value"] = "other"
    elif change == "failure": checked["failure_code"] = "variant_provider_native_error"
    elif change == "population": checked["population_scope"] = "all_variants"
    elif change == "qualifications": checked["qualifications"] = []
    elif change == "selected": checked["requested"]["dataset"] = "gnomad_r3"
    else: checked["observed"]["transport"]["declared_body_bytes"] = False
    with pytest.raises(ValueError): provider.validate_provider_value(checked)


@pytest.mark.parametrize("changes", [{"acquired": 1}, {"source_ref": None}, {"data_ref": None},
    {"data_ref": "artifact_bad"}, {"failure_code": "invented"}, {"extra": True}])
def test_common_four_receipt_has_closed_references_and_crossfield_meanings(changes):
    original = receipt("gnomad_variant")
    with pytest.raises(ValueError): provider.validate_provider_receipt({**original, **changes})
    assert provider.failed_provider_receipt("provider_connection_failed") == dict(
        acquired=False, source_ref=None, data_ref=None, failure_code="provider_connection_failed")


@pytest.fixture
def publisher(tmp_path, monkeypatch):
    monkeypatch.setattr(PublicClients, "_http", forbidden)
    monkeypatch.setattr("socket.create_connection", forbidden)
    monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", forbidden)
    with Store(tmp_path / "store") as store:
        yield store, ToolRegistry(store)


def publish(registry, case, saved):
    token = registry._publications.set([])
    try: return provider.publish_provider_request(registry, operation(case), ARGUMENTS[case], saved)
    finally: registry._publications.reset(token)


@pytest.mark.parametrize("case", CASES)
def test_real_source_publisher_keeps_exact_native_primary_and_one_private_value(publisher, monkeypatch, case):
    store, registry = publisher; saved = capture(case)
    actual_source = registry._source
    def source_after_private(*args, **kwargs):
        private, = kwargs["auxiliary_artifact_refs"]
        checked = json.loads(store.get_artifact(private))
        assert provider.validate_provider_value(checked) == value(case) and "source_ref" not in checked
        return actual_source(*args, **kwargs)
    monkeypatch.setattr(registry, "_source", source_after_private)
    result, refs = publish(registry, case, saved); source = store.get(result["source_ref"])
    assert result == dict(acquired=True, source_ref=source["id"], data_ref=source["artifact_ref"], failure_code=None)
    assert refs == [source["id"], source["artifact_ref"]] and store.get_artifact(source["artifact_ref"]) == saved.content
    assert source["provider"] == saved.service and source["uri"] == saved.transport["request"]["url"]
    private, = source["auxiliary_artifact_refs"]
    assert private not in refs and source["request_ref"] not in refs
    assert json.loads(store.get_artifact(source["request_ref"])) == json.loads(canonical({"request": saved.request, "transport": saved.transport}))
    assert store.db.execute("SELECT count(*) FROM records WHERE record_type='source'").fetchone()[0] == 1
    tables = {row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for table in ("tool_operations", "runtime_episodes", "runtime_actions", "runtime_model_calls", "runtime_observations"):
        if table in tables: assert store.db.execute("SELECT count(*) FROM " + table).fetchone()[0] == 0


@pytest.mark.parametrize("case", ["eva_variant", "gnomad_variant"])
def test_captured_native_failure_retains_source_only_and_exact_partial_or_error_bytes(publisher, case):
    store, registry = publisher
    raw = b'{"error":"native failure"}' if case.startswith("eva_") else b'{"errors":[{"message":"native failure"}],"data":{"variant":null}}'
    saved = capture(case, raw=raw); result, refs = publish(registry, case, saved)
    source = store.get(result["source_ref"])
    assert result["acquired"] is False and result["data_ref"] is None and result["failure_code"] is not None
    assert refs == [source["id"]] and store.get_artifact(source["artifact_ref"]) == raw
    private, = source["auxiliary_artifact_refs"]
    assert provider.validate_provider_value(json.loads(store.get_artifact(private)))["failure_code"] == result["failure_code"]


def test_real_source_publisher_retains_actual_prefix_with_no_data_file_delivery(publisher):
    store, registry = publisher
    raw = b'{"data":{"variant":'
    saved = capture("gnomad_variant", raw=raw, transport_changes={"body_complete": False,
        "body_capture_failure": "provider_response_byte_limit", "observed_body_bytes": len(raw) + 1,
        "declared_body_bytes": len(raw) + 100})
    result, refs = publish(registry, "gnomad_variant", saved); source = store.get(result["source_ref"])
    assert result == provider.failed_provider_receipt("variant_provider_capture_incomplete", source_ref=source["id"])
    assert refs == [source["id"]] and store.get_artifact(source["artifact_ref"]) == raw


@pytest.mark.parametrize("change", ["service", "url", "wire_body", "policy"])
def test_contradictory_capture_uses_finite_private_failure_witness_not_a_fake_value(publisher, change):
    store, registry = publisher; saved = capture("gnomad_variant"); transport = deepcopy(saved.transport)
    if change == "service": saved = replace(saved, service="observed_other")
    elif change == "url": saved = replace(saved, url="https://observed.invalid/original")
    elif change == "wire_body": transport["request"]["body_sha256"] = "0" * 64
    else: transport["request_policy"]["automatic_redirects"] = True
    saved = replace(saved, transport=transport)
    result, refs = publish(registry, "gnomad_variant", saved); source = store.get(result["source_ref"])
    assert result["acquired"] is False and result["data_ref"] is None and refs == [source["id"]]
    assert source["uri"] == saved.url and store.get_artifact(source["artifact_ref"]) == saved.content
    private, = source["auxiliary_artifact_refs"]
    assert json.loads(store.get_artifact(private)) == dict(version="variant_provider_failure_witness_v1",
        observed_snapshot_service=saved.service, observed_snapshot_url=saved.url, failure_code=result["failure_code"])


def test_no_response_and_invalid_selected_arguments_create_no_source_or_artifact(publisher, monkeypatch):
    store, registry = publisher
    monkeypatch.setattr(store, "artifact", forbidden); monkeypatch.setattr(registry, "_source", forbidden)
    assert provider.failed_provider_receipt("provider_connection_failed")["source_ref"] is None
    with pytest.raises(ValueError): provider.publish_provider_request(registry, GNOMAD, ARGUMENTS["gnomad_variant"], None)
    with pytest.raises(ValueError): provider.publish_provider_request(registry, GNOMAD,
        {**ARGUMENTS["gnomad_variant"], "max_bytes": True}, capture("gnomad_variant"))
    assert list(store.list("source")) == []


@pytest.mark.parametrize("case", ["eva_variant", "gnomad_variant"])
def test_processing_mime_contradiction_cannot_become_selected_json(publisher, case):
    store, registry = publisher
    saved = replace(capture(case), media_type="application/octet-stream")
    with pytest.raises(ValueError, match="variant_provider_selected_request_conflict"):
        provider.provider_value(saved, operation=operation(case), arguments=ARGUMENTS[case],
            artifact_ref="artifact_" + hashlib.sha256(saved.content).hexdigest())
    result, refs = publish(registry, case, saved)
    source = store.get(result["source_ref"])
    assert result == provider.failed_provider_receipt("variant_provider_selected_request_conflict", source_ref=source["id"])
    assert refs == [source["id"]] and store.get_artifact(source["artifact_ref"]) == saved.content


@pytest.mark.parametrize("rows", [[], [eva_row()]])
@pytest.mark.parametrize("identity", [None, "", "1:7-12", "2:100-200", "rs999"])
@pytest.mark.parametrize("case", ["eva_variant", "eva_region"])
def test_eva_query_result_id_is_required_carrier_metadata_not_an_invented_query_echo(rows, identity, case):
    # Current QueryUtils uses QueryResult() and never assigns its id. Neither
    # matching-looking nor conflicting nonempty strings establish a new echo
    # protocol. A missing field is not its authentic observed empty string.
    rows = deepcopy(rows)
    if case == "eva_region":
        for row in rows: row["chromosome"] = "1"
    doc = eva_document(rows, skip=4 if case == "eva_region" else -1)
    if identity is None: del doc["response"][0]["id"]
    else: doc["response"][0]["id"] = identity
    checked = value(case, raw=json.dumps(doc).encode())
    result = provider.provider_receipt(checked, source_ref=SOURCE)
    assert result["acquired"] is (identity == "")
    assert checked["identity_state"] == (("empty" if not rows else "confirmed") if identity == "" else "unavailable")
    assert any(row["code"] == "native_query_id_is_not_a_selected_query_echo" for row in checked["qualifications"])
    if identity != "": assert result["failure_code"] == "variant_provider_native_result_unavailable"


@pytest.mark.parametrize("start,end", [(7, 9), (6, 7), (12, 13), (6, 13)])
def test_eva_exact_contig_inclusive_overlap_does_not_require_variant_containment(start, end):
    doc = document("eva_region")
    doc["response"][0]["result"][0].update(chromosome="1", start=start, end=end)
    checked = value("eva_region", raw=json.dumps(doc).encode())
    assert provider.provider_receipt(checked, source_ref=SOURCE)["acquired"] is True
    row = member(member(checked["native_document"], "response")["items"][0], "result")["items"][0]
    assert member(row, "start")["token"] == str(start) and member(row, "end")["token"] == str(end)


@pytest.mark.parametrize("start,end", [(0, 6), (13, 14)])
def test_eva_disjoint_native_interval_cannot_be_confirmed_by_wire_uri(start, end):
    doc = document("eva_region"); doc["response"][0]["result"][0].update(start=start, end=end)
    checked = value("eva_region", raw=json.dumps(doc).encode())
    assert checked["identity_state"] == "conflict"
    assert provider.provider_receipt(checked, source_ref=SOURCE)["failure_code"] == "variant_provider_native_identity_conflict"


@pytest.mark.parametrize("chromosome", ["2", "chr1", "NC_000067.6"])
def test_eva_unverified_native_contig_cannot_gain_an_alias_from_request_custody(chromosome):
    doc = document("eva_region"); doc["response"][0]["result"][0].update(chromosome=chromosome, start=6, end=13)
    checked = value("eva_region", raw=json.dumps(doc).encode())
    assert checked["identity_state"] == "unavailable"
    assert provider.provider_receipt(checked, source_ref=SOURCE)["failure_code"] == "variant_provider_native_result_unavailable"
    assert any(row["code"] == "native_region_contig_alias_not_inferred" for row in checked["qualifications"])


@pytest.mark.parametrize("case", ["eva_variant", "eva_region"])
def test_eva_duplicate_query_result_ids_remain_ambiguous_instead_of_selecting_one(case):
    raw = json.dumps(document(case), separators=(",", ":")).encode().replace(b'"id":""', b'"id":"","id":""', 1)
    checked = value(case, raw=raw)
    assert base64.b64decode(checked["raw"]["data"]) == raw
    assert provider.provider_receipt(checked, source_ref=SOURCE)["acquired"] is False
    assert any(row["code"] == "native_duplicate_member" for row in checked["qualifications"])


@pytest.mark.parametrize("start,end", [(0, 7), (7, 5011)])
def test_eva_native_overlap_within_repository_margin_is_not_trimmed_or_contained(start, end):
    # Source predicate also requires start>7-5000 and end<12+5000; this
    # optimization restricts overlap, and never admits a disjoint interval.
    doc = document("eva_region"); doc["response"][0]["result"][0].update(start=start, end=end)
    checked = value("eva_region", raw=json.dumps(doc).encode())
    assert provider.provider_receipt(checked, source_ref=SOURCE)["acquired"] is True
    row = member(member(checked["native_document"], "response")["items"][0], "result")["items"][0]
    assert member(row, "start")["token"] == str(start) and member(row, "end")["token"] == str(end)


@pytest.mark.parametrize("start,end,alternate", [(6, 9, "ACGT"), (7, 7, "A")])
def test_eva_empty_reference_insertion_retains_the_returned_model_extent(start, end, alternate):
    # AbstractVariant documents the inserted-base extent (four bases between
    # positions5/6 => start6/end9). Constructor and renormalize preserve the
    # supplied extent and reject end<start; no VCF anchor/end is inferred.
    doc = document("eva_variant")
    doc["response"][0]["result"][0].update(start=start, end=end, reference="", alternate=alternate)
    checked = value("eva_variant", raw=json.dumps(doc).encode())
    assert provider.provider_receipt(checked, source_ref=SOURCE)["acquired"] is True
    row = member(member(checked["native_document"], "response")["items"][0], "result")["items"][0]
    assert member(row, "reference") == dict(kind="string", value="")
    assert member(row, "start")["token"] == str(start) and member(row, "end")["token"] == str(end)
