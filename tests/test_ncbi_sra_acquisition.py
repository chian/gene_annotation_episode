"""Pure SRA advertisement/transfer controls; no archive or live GET is run.

The XML fixture is an authentic retained metadata response. Every transferred
body below is explicitly engineered opaque bytes, never actual SRA contents.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import io
import json
from email.message import Message
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit
import urllib.request
from xml.sax.saxutils import quoteattr

import pytest

from gene_annotation_episode.acquisition import PublicClients, SourceSnapshot
from gene_annotation_episode import ncbi_sra_acquisition as sra


FIXTURES = Path(__file__).parent / "fixtures/ncbi_sra"
SOURCE = "source_" + "a" * 24
URL = "https://sra-pub-run-odp.s3.amazonaws.com/sra/SRR6263255/SRR6263255"
LITE_URL = "https://sra-downloadb.be-md.ncbi.nlm.nih.gov/sos12/sra-pub-zq-1214/SRR006/263/SRR6263255.sralite.1"
ENGINEERED = b"\x00engineered opaque bytes; not an SRA archive\n"


def forbidden(*args, **kwargs):
    raise AssertionError("pure SRA contract attempted transport, execution or reparsing")


@pytest.fixture(autouse=True)
def no_transport(monkeypatch):
    monkeypatch.setattr("socket.create_connection", forbidden)
    monkeypatch.setattr("subprocess.Popen", forbidden)
    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    monkeypatch.setattr("urllib.request.build_opener", forbidden)


def arguments(xml, **changes):
    sha = hashlib.sha256(xml).hexdigest()
    value = dict(advertisement_file=dict(artifact_ref="artifact_" + sha, sha256=sha,
        size_bytes=len(xml), format=sra.ADVERTISEMENT_FORMAT), experiment_package_ordinal_0based=0,
        run_ordinal_0based=0, file_ordinal_0based=0, url_selection=dict(kind="file_url"),
        run_accession="SRR6263255", semantic_name="SRA Normalized", supertype="Primary ETL",
        file_name="SRR6263255", url=URL, max_bytes=4096)
    value.update(changes)
    return value


def element(attributes):
    return "<SRAFile" + "".join(" " + name + "=" + quoteattr(value)
        for name, value in attributes.items() if value is not None) + "/>"


def engineered(body=ENGINEERED, *, attributes=None, other_file="", run_size="777"):
    attrs = dict(filename="SRR6263255", semantic_name="SRA Normalized", supertype="Primary ETL",
        url=URL, size=str(len(body)), md5=hashlib.md5(body, usedforsecurity=False).hexdigest())
    attrs.update(attributes or {})
    xml = ("<EXPERIMENT_PACKAGE_SET><EXPERIMENT_PACKAGE><RUN_SET><RUN accession=\"SRR6263255\" size="
        + quoteattr(run_size) + "><SRAFiles>" + element(attrs) + other_file
        + "</SRAFiles></RUN></RUN_SET></EXPERIMENT_PACKAGE></EXPERIMENT_PACKAGE_SET>").encode()
    selected = arguments(xml)
    return xml, selected, sra.resolve_sra_file_selection(xml, arguments=selected)


def snapshot(body, selected, **changes):
    transport = dict(status=200, effective_url=selected["url"],
        headers={"content-type": "application/octet-stream"},
        header_items=[("Content-Type", "application/octet-stream")], body_complete=True,
        retained_body_bytes=len(body), observed_body_bytes=len(body), declared_body_bytes=len(body),
        response_byte_limit=selected["max_bytes"], request=dict(method="GET", url=selected["url"],
            headers={"Accept": "application/octet-stream", "Host": urlsplit(selected["url"]).netloc}),
        request_policy=dict(timeout_seconds=90, automatic_redirects=False))
    transport.update(changes)
    return SourceSnapshot(sra.SERVICE, selected["url"], {}, "2026-10-25T23:19:42Z",
        body, "application/octet-stream", transport)


def value(body=ENGINEERED, *, selected=None, selection=None, **changes):
    if selected is None:
        _, selected, selection = engineered(body)
    capture = snapshot(body, selected, **changes)
    return sra.sra_file_value(capture, arguments=selected, selection=selection,
        artifact_ref="artifact_" + hashlib.sha256(body).hexdigest())


def test_authentic_metadata_fixture_and_provenance_have_exact_original_bytes():
    raw = (FIXTURES / "experiment_package.xml").read_bytes()
    provenance = json.loads((FIXTURES / "provenance.json").read_bytes())
    assert len(raw) == 7802 and hashlib.sha256(raw).hexdigest() == "e2e72cc189d988194ef9ab9faff6b96132749afd7cdc3293f386902544e45b10"
    assert provenance["fixture"] == dict(file="experiment_package.xml", sha256=hashlib.sha256(raw).hexdigest(), size_bytes=7802)
    assert provenance["original_capture"]["http_status"] == 200
    assert provenance["original_capture"]["sha256"] == provenance["fixture"]["sha256"]
    assert provenance["qualification"] == dict(metadata_capture_only=True, read_download=False,
        archive_contents_verified=False, current_resource_availability_verified=False, fixture_bytes_unchanged=True)


@pytest.mark.parametrize("ordinal,name,url,size,md5", [
    (1, "SRA Normalized", URL, 937095532, "36d7ad948f9a82a4743a77a4bb9a5288"),
    (2, "SRA Lite", LITE_URL, 672505972, "a475eae71fc75c071158caa4e7b2969c"),
])
def test_actual_native_file_occurrences_keep_distinct_claims_without_a_transfer(ordinal, name, url, size, md5):
    raw = (FIXTURES / "experiment_package.xml").read_bytes()
    selected = arguments(raw, file_ordinal_0based=ordinal, semantic_name=name, url=url,
        file_name="SRR6263255" if ordinal == 1 else "SRR6263255.sralite", max_bytes=sra.MAX_BYTES)
    result = sra.resolve_sra_file_selection(raw, arguments=selected)
    assert result["claims"] == dict(size_token=str(size), size_bytes=size, md5_token=md5)
    assert {row["name"]: row["value"] for row in result["run_attributes"]}["size"] == "937094000"
    assert result["selected_url"] == url and result["alternative_attributes"] is None
    assert result["location"]["file_ordinal_0based"] == ordinal
    spec = sra.sra_file_request_spec(selected, selection=result)
    assert spec == dict(service="ncbi_sra", url=url, params={}, media_type="application/octet-stream",
        max_bytes=sra.MAX_BYTES, follow_redirects=False)
    assert "source_ref" not in selected and "source_ref" not in result


def test_actual_alternative_is_explicit_not_a_fallback_or_a_second_file():
    raw = (FIXTURES / "experiment_package.xml").read_bytes()
    selected = arguments(raw, file_ordinal_0based=1,
        url_selection=dict(kind="alternative_url", alternative_ordinal_0based=0))
    result = sra.resolve_sra_file_selection(raw, arguments=selected)
    assert {row["name"]: row["value"] for row in result["alternative_attributes"]} == dict(
        url=URL, free_egress="worldwide", access_type="anonymous", org="AWS")
    assert result["claims"]["size_bytes"] == 937095532


def test_original_fastq_s3_advertisement_has_no_synthesized_https_transfer():
    raw = (FIXTURES / "experiment_package.xml").read_bytes()
    selected = arguments(raw, file_ordinal_0based=0, semantic_name="fastq", supertype="Original",
        file_name="JK3187Ulep_S0_L002_R1_001.fastq.gz",
        url="s3://sra-pub-src-5/SRR6263255/JK3187Ulep_S0_L002_R1_001.fastq.gz")
    with pytest.raises(ValueError, match="sra_file_https_resource_unsupported"):
        sra.resolve_sra_file_selection(raw, arguments=selected)


@pytest.mark.parametrize("field,bad", [
    ("experiment_package_ordinal_0based", True), ("run_ordinal_0based", 0.0),
    ("file_ordinal_0based", -1), ("max_bytes", False), ("max_bytes", 0),
    ("max_bytes", sra.MAX_BYTES + 1), ("semantic_name", "guessed"), ("supertype", "Original"),
    ("run_accession", "SRR6263255\n"), ("file_name", ""),
    ("url_selection", {"kind": "alternative_url", "alternative_ordinal_0based": True}),
    ("url_selection", {"kind": "file_url", "alternative_ordinal_0based": 0}),
])
def test_closed_request_rejects_mistyped_or_unselected_operands(field, bad):
    xml, selected, _ = engineered()
    selected[field] = bad
    with pytest.raises(ValueError):
        sra.validate_sra_file_arguments(selected)


@pytest.mark.parametrize("change", ["extra_source", "artifact", "sha_newline", "size_bool", "size_limit", "format"])
def test_file_only_identity_is_closed_and_never_invents_a_source(change):
    _, selected, _ = engineered()
    if change == "extra_source": selected["source_ref"] = SOURCE
    elif change == "artifact": selected["advertisement_file"]["artifact_ref"] = "artifact_" + "0" * 64
    elif change == "sha_newline":
        selected["advertisement_file"]["sha256"] += "\n"
        selected["advertisement_file"]["artifact_ref"] += "\n"
    elif change == "size_bool": selected["advertisement_file"]["size_bytes"] = True
    elif change == "size_limit": selected["advertisement_file"]["size_bytes"] = sra.MAX_ADVERTISEMENT_BYTES + 1
    else: selected["advertisement_file"]["format"] = "guessed_gzip"
    with pytest.raises(ValueError, match="sra_file_arguments_invalid"):
        sra.validate_sra_file_arguments(selected)


@pytest.mark.parametrize("url", ["http://sra-pub-run-odp.s3.amazonaws.com/a", "s3://bucket/a",
    "https://example.invalid/a", "https://user@sra-pub-run-odp.s3.amazonaws.com/a",
    "https://sra-pub-run-odp.s3.amazonaws.com:444/a", URL + "#fragment", URL + "?token=unselected",
    URL + "\n", "https://sra-pub-run-odp.s3.amazonaws.com:notaport/a"])
def test_only_explicit_supported_anonymous_https_resources_are_exposed(url):
    _, selected, _ = engineered()
    selected["url"] = url
    with pytest.raises(ValueError): sra.validate_sra_file_arguments(selected)


@pytest.mark.parametrize("change", ["package", "run", "file", "alternative", "run_accession", "file_name", "url"])
def test_wrong_native_occurrence_or_literal_identity_cannot_choose_a_neighbour(change):
    xml, selected, _ = engineered()
    if change in {"package", "run", "file"}:
        selected[{"package": "experiment_package_ordinal_0based", "run": "run_ordinal_0based", "file": "file_ordinal_0based"}[change]] = 1
    elif change == "alternative": selected["url_selection"] = dict(kind="alternative_url", alternative_ordinal_0based=0)
    elif change == "run_accession": selected["run_accession"] = "SRX3369480"
    elif change == "file_name": selected["file_name"] = "different"
    else: selected["url"] = URL + "/different"
    with pytest.raises(ValueError): sra.resolve_sra_file_selection(xml, arguments=selected)


@pytest.mark.parametrize("raw", [b"", b"<EXPERIMENT_PACKAGE_SET>", b"\xff", b"<other/>",
    b'<!DOCTYPE EXPERIMENT_PACKAGE_SET SYSTEM "https://example.invalid/not-read"><EXPERIMENT_PACKAGE_SET/>'])
def test_unavailable_xml_is_a_finite_format_failure_without_external_reads(raw):
    with pytest.raises(ValueError, match="sra_file_advertisement_format_unavailable"):
        sra.resolve_sra_file_selection(raw, arguments=arguments(raw))


def test_advertisement_original_bytes_are_bound_before_native_parsing():
    xml, selected, _ = engineered()
    with pytest.raises(ValueError, match="sra_file_advertisement_identity_conflict"):
        sra.resolve_sra_file_selection(xml + b" ", arguments=selected)


@pytest.mark.parametrize("key,token", [("size", ""), ("size", "-1"), ("size", "1.0"),
    ("size", "true"), ("size", "１２"), ("md5", ""), ("md5", "g" * 32), ("md5", "a" * 31)])
def test_malformed_selected_native_claims_are_not_missing_or_zero(key, token):
    with pytest.raises(ValueError, match="sra_file_native_claim_invalid"):
        engineered(attributes={key: token})


def test_unselected_bad_claims_and_repeated_names_do_not_change_the_selected_occurrence():
    extra = element(dict(filename="SRR6263255", semantic_name="SRA Normalized", supertype="Primary ETL",
        url=URL, size="bad", md5="bad"))
    _, selected, selection = engineered(other_file=extra)
    assert sra.sra_file_receipt(value(selected=selected, selection=selection), source_ref=SOURCE)["acquired"]
    selected["file_ordinal_0based"] = 1
    xml, _, _ = engineered(other_file=extra)
    with pytest.raises(ValueError, match="sra_file_native_claim_invalid"):
        sra.resolve_sra_file_selection(xml, arguments=selected)


def test_repeated_run_accessions_remain_distinct_explicit_occurrences():
    xml, _, _ = engineered()
    extra = element(dict(filename="SRR6263255", semantic_name="SRA Normalized", supertype="Primary ETL",
        url=URL, size="0", md5=hashlib.md5(b"", usedforsecurity=False).hexdigest()))
    second = ("<RUN accession=\"SRR6263255\" alias=\"second occurrence\"><SRAFiles>" + extra
        + "</SRAFiles></RUN>").encode()
    xml = xml.replace(b"</RUN_SET>", second + b"</RUN_SET>")
    selected = arguments(xml, run_ordinal_0based=1)
    selection = sra.resolve_sra_file_selection(xml, arguments=selected)
    assert selection["claims"]["size_bytes"] == 0 and selection["location"]["run_ordinal_0based"] == 1
    assert {row["name"]: row["value"] for row in selection["run_attributes"]}["alias"] == "second occurrence"
    assert sra.sra_file_receipt(value(b"", selected=selected, selection=selection), source_ref=SOURCE)["acquired"]


def test_missing_native_file_claims_do_not_fall_back_to_run_size_or_infer_identity():
    _, selected, selection = engineered(attributes={"size": None, "md5": None}, run_size="937094000")
    result = value(selected=selected, selection=selection)
    assert selection["claims"] == dict(size_token=None, size_bytes=None, md5_token=None)
    assert result["checks"] == dict(request="matched", body_capture="complete", native_size="absent",
        native_md5="absent", archive_identity="not_parsed")
    assert sra.sra_file_receipt(result, source_ref=SOURCE)["acquired"]


def test_engineered_zero_length_and_uppercase_checksum_keep_literal_native_tokens():
    md5 = hashlib.md5(b"", usedforsecurity=False).hexdigest().upper()
    _, selected, selection = engineered(b"", attributes={"size": "000", "md5": md5})
    result = value(b"", selected=selected, selection=selection)
    assert selection["claims"] == dict(size_token="000", size_bytes=0, md5_token=md5)
    assert result["checks"]["native_size"] == result["checks"]["native_md5"] == "verified"
    assert result["checks"]["archive_identity"] == "not_parsed"


def test_engineered_complete_transfer_has_only_the_common_four_field_confirmation():
    result = value()
    expected = dict(acquired=True, source_ref=SOURCE,
        data_ref="artifact_" + hashlib.sha256(ENGINEERED).hexdigest(), failure_code=None)
    assert sra.sra_file_receipt(result, source_ref=SOURCE) == expected
    assert result["checks"]["archive_identity"] == "not_parsed"
    assert result["checks"]["native_size"] == result["checks"]["native_md5"] == "verified"
    assert result["raw_file"]["md5"] == hashlib.md5(ENGINEERED, usedforsecurity=False).hexdigest()
    assert "source_ref" not in result and "native_document" not in result and "content" not in result


@pytest.mark.parametrize("change", ["service", "url", "params", "method", "wire_url", "body", "accept",
    "redirect", "timeout", "limit", "effective_url", "range", "authorization", "cookie", "host"])
def test_observed_wire_and_policy_must_be_the_literal_selected_get(change):
    _, selected, selection = engineered()
    capture = snapshot(ENGINEERED, selected)
    if change == "service": capture = replace(capture, service="other")
    elif change == "url": capture = replace(capture, url=URL + "/different")
    elif change == "params": capture = replace(capture, request={"unselected": "value"})
    elif change == "method": capture.transport["request"]["method"] = "POST"
    elif change == "wire_url": capture.transport["request"]["url"] += "/different"
    elif change == "body": capture.transport["request"]["body_base64"] = ""
    elif change == "accept": capture.transport["request"]["headers"]["Accept"] = "application/json"
    elif change == "redirect": capture.transport["request_policy"]["automatic_redirects"] = True
    elif change == "timeout": capture.transport["request_policy"]["timeout_seconds"] = True
    elif change == "limit": capture.transport["response_byte_limit"] = True
    elif change == "effective_url": capture.transport["effective_url"] += "/different"
    else: capture.transport["request"]["headers"][change.title()] = "unselected"
    result = sra.sra_file_value(capture, arguments=selected, selection=selection,
        artifact_ref="artifact_" + hashlib.sha256(ENGINEERED).hexdigest())
    assert result["failure_code"] == "sra_file_request_conflict"
    assert result["checks"]["native_md5"] == "not_verified"
    assert sra.sra_file_receipt(result, source_ref=SOURCE) == dict(acquired=False,
        source_ref=SOURCE, data_ref=None, failure_code="sra_file_request_conflict")


@pytest.mark.parametrize("host", [None, "sra-pub-run-odp.s3.amazonaws.com", "SRA-PUB-RUN-ODP.S3.AMAZONAWS.COM"])
def test_optional_single_host_matches_selected_authority_without_rewriting(host):
    _, selected, selection = engineered()
    capture = snapshot(ENGINEERED, selected)
    headers = capture.transport["request"]["headers"]
    del headers["Host"]
    if host is not None:
        headers["hOsT"] = host
    result = sra.sra_file_value(capture, arguments=selected, selection=selection,
        artifact_ref="artifact_" + hashlib.sha256(ENGINEERED).hexdigest())
    assert result["failure_code"] is None and result["observed"]["transport"]["request"]["headers"] == headers


@pytest.mark.parametrize("headers", [
    {"Host": "other.invalid"}, {"Host": ""}, {"Host": " sra-pub-run-odp.s3.amazonaws.com"},
    {"Host": "sra-pub-run-odp.s3.amazonaws.com:80"},
    {"Host": "sra-pub-run-odp.s3.amazonaws.com:443"},
    {"Host": "sra-pub-run-odp.s3.amazonaws.com", "host": "sra-pub-run-odp.s3.amazonaws.com"},
    {"Host": "sra-pub-run-odp.s3.amazonaws.com", "HOST": "other.invalid"},
])
def test_wrong_duplicate_or_contradictory_host_is_not_the_selected_authority(headers):
    _, selected, selection = engineered()
    capture = snapshot(ENGINEERED, selected)
    capture.transport["request"]["headers"] = {"Accept": "application/octet-stream", **headers}
    result = sra.sra_file_value(capture, arguments=selected, selection=selection,
        artifact_ref="artifact_" + hashlib.sha256(ENGINEERED).hexdigest())
    assert result["failure_code"] == "sra_file_request_conflict"


def test_explicit_selected_https_port_is_preserved_in_native_url_and_host():
    xml, _, _ = engineered()
    explicit = URL.replace(".com/", ".com:443/")
    xml = xml.replace(URL.encode(), explicit.encode())
    selected = arguments(xml, url=explicit)
    selection = sra.resolve_sra_file_selection(xml, arguments=selected)
    result = value(selected=selected, selection=selection)
    assert result["failure_code"] is None
    assert result["observed"]["url"] == explicit
    assert result["observed"]["transport"]["request"]["headers"]["Host"] == "sra-pub-run-odp.s3.amazonaws.com:443"


def test_actual_http_capture_keeps_transport_added_host_with_engineered_https(monkeypatch):
    """Real HTTP capture owner and Host preparation; controlled bytes, no network."""
    _, selected, selection = engineered()
    calls = []

    class Reply(io.BytesIO):
        status = 200
        headers = Message()
        headers["Content-Type"] = "application/octet-stream"
        headers["Content-Length"] = str(len(ENGINEERED))

        def geturl(self):
            return selected["url"]

    def open_response(request, timeout):
        handler = urllib.request.AbstractHTTPHandler()
        handler.add_parent(SimpleNamespace(addheaders=[]))
        handler.do_request_(request)
        calls.append(dict(url=request.full_url, timeout=timeout, headers=dict(request.header_items())))
        return Reply(ENGINEERED)

    monkeypatch.setattr(urllib.request, "build_opener", lambda *_handlers: SimpleNamespace(open=open_response))
    capture = PublicClients(ncbi_email=None, timeout=3)._http(
        **sra.sra_file_request_spec(selected, selection=selection), timeout_seconds=3)
    assert len(calls) == 1 and calls[0]["headers"]["Host"] == urlsplit(selected["url"]).netloc
    result = sra.sra_file_value(capture, arguments=selected, selection=selection,
        artifact_ref="artifact_" + hashlib.sha256(ENGINEERED).hexdigest())
    assert result["failure_code"] is None and result["checks"]["archive_identity"] == "not_parsed"
    assert result["observed"]["transport"]["request"]["headers"] == calls[0]["headers"]


@pytest.mark.parametrize("status", [301, 403, 404, 429, 500])
def test_complete_http_error_body_is_retained_without_a_data_confirmation(status):
    _, selected, selection = engineered()
    capture = replace(snapshot(b"engineered error", selected, status=status), media_type="text/html")
    result = sra.sra_file_value(capture, arguments=selected, selection=selection,
        artifact_ref="artifact_" + hashlib.sha256(capture.content).hexdigest())
    assert result["failure_code"] == "sra_file_http_not_success"
    assert result["checks"]["body_capture"] == "complete" and result["checks"]["native_md5"] == "not_verified"
    assert sra.sra_file_receipt(result, source_ref=SOURCE)["data_ref"] is None


def test_real_http_error_capture_shape_does_not_invent_an_effective_url():
    _, selected, selection = engineered()
    capture = replace(snapshot(b"engineered HTTPError entity", selected, status=403), media_type="text/html")
    del capture.transport["effective_url"]
    result = sra.sra_file_value(capture, arguments=selected, selection=selection,
        artifact_ref="artifact_" + hashlib.sha256(capture.content).hexdigest())
    assert result["failure_code"] == "sra_file_http_not_success"
    assert "effective_url" not in result["observed"]["transport"]
    assert result["checks"]["native_md5"] == "not_verified"


@pytest.mark.parametrize("status", [None, True, 200.0, 99, 600])
def test_unknown_or_mistyped_status_is_not_a_success(status):
    assert value(status=status)["failure_code"] == "sra_file_http_status_unknown"


@pytest.mark.parametrize("status,items", [(206, []), (200, [["Content-Range", "bytes 0-3/4"]])])
def test_unrequested_range_cannot_be_promoted_to_the_complete_selected_file(status, items):
    assert value(status=status, header_items=items)["failure_code"] == "sra_file_unrequested_range"


@pytest.mark.parametrize("failure", ["provider_response_byte_limit", "provider_body_capture_failed"])
def test_capture_failure_keeps_its_cause_and_never_verifies_native_file_claims(failure):
    result = value(body_complete=False, body_capture_failure=failure, observed_body_bytes=len(ENGINEERED) + 1)
    assert result["failure_code"] == failure and result["checks"]["body_capture"] == "incomplete"
    assert result["checks"]["native_size"] == result["checks"]["native_md5"] == "not_verified"


@pytest.mark.parametrize("key,bad", [("body_complete", None), ("body_complete", 1),
    ("retained_body_bytes", True), ("observed_body_bytes", 1.0), ("observed_body_bytes", -1),
    ("declared_body_bytes", True), ("declared_body_bytes", -1), ("declared_body_bytes", "missing"),
    ("body_capture_failure", False), ("body_capture_failure", []), ("body_capture_failure", "unselected"),
    ("headers", None), ("header_items", [["broken"]])])
def test_malformed_capture_fields_are_not_normalized_to_legitimate_absence(key, bad):
    assert value(**{key: bad})["failure_code"] == "sra_file_capture_invalid"


@pytest.mark.parametrize("change", [dict(body_complete=False), dict(retained_body_bytes=0),
    dict(observed_body_bytes=0), dict(declared_body_bytes=0)])
def test_complete_capture_needs_exact_observed_and_retained_counts(change):
    assert value(**change)["failure_code"] == "sra_file_capture_incomplete"


def test_missing_declared_length_and_mime_only_qualification_do_not_invent_file_sizes():
    result = value(declared_body_bytes=None, headers={"content-type": "text/plain"},
        header_items=[["Content-Type", "text/plain"]])
    assert result["failure_code"] is None and result["observed"]["transport"]["declared_body_bytes"] is None
    assert result["checks"]["native_size"] == "verified"


@pytest.mark.parametrize("encoding", ["gzip", "br"])
def test_http_content_encoding_is_not_an_implicit_archive_conversion(encoding):
    assert value(header_items=[["Content-Encoding", encoding]])["failure_code"] == "sra_file_content_encoding_unsupported"


def test_declared_processing_mime_conflict_is_distinct_from_native_content_type():
    _, selected, selection = engineered()
    capture = replace(snapshot(ENGINEERED, selected), media_type="application/json")
    result = sra.sra_file_value(capture, arguments=selected, selection=selection,
        artifact_ref="artifact_" + hashlib.sha256(ENGINEERED).hexdigest())
    assert result["failure_code"] == "sra_file_request_conflict"


@pytest.mark.parametrize("claim,code", [(dict(size="0"), "sra_file_native_size_conflict"),
    (dict(md5="0" * 32), "sra_file_native_md5_conflict")])
def test_complete_transfer_still_needs_every_present_native_claim(claim, code):
    _, selected, selection = engineered(attributes=claim)
    result = value(selected=selected, selection=selection)
    assert result["failure_code"] == code
    assert sra.sra_file_receipt(result, source_ref=SOURCE) == dict(acquired=False,
        source_ref=SOURCE, data_ref=None, failure_code=code)


def test_actual_http_header_tuples_become_only_private_control_arrays_without_mutation():
    _, selected, selection = engineered()
    capture = snapshot(ENGINEERED, selected)
    before = deepcopy(capture.transport)
    result = sra.sra_file_value(capture, arguments=selected, selection=selection,
        artifact_ref="artifact_" + hashlib.sha256(ENGINEERED).hexdigest())
    assert result["observed"]["transport"]["header_items"] == [["Content-Type", "application/octet-stream"]]
    assert capture.transport == before and type(capture.transport["header_items"][0]) is tuple


@pytest.mark.parametrize("raw", [float("nan"), b"Python-only"])
def test_non_json_transport_controls_are_rejected_without_a_fabricated_value(raw):
    with pytest.raises(ValueError, match="sra_file_value_invalid"):
        value(declared_body_bytes=raw)


@pytest.mark.parametrize("target", ["ordinal_bool", "file_count_float", "check", "failure", "artifact", "sha_newline", "md5_newline", "claim", "selection_url", "extra"])
def test_saved_private_value_crossfields_and_strict_scalar_types_are_validated(target):
    result = value()
    if target == "ordinal_bool": result["selection"]["location"]["run_ordinal_0based"] = False
    elif target == "file_count_float": result["raw_file"]["size_bytes"] = float(result["raw_file"]["size_bytes"])
    elif target == "check": result["checks"]["native_md5"] = "absent"
    elif target == "failure": result["failure_code"] = "sra_file_native_size_conflict"
    elif target == "artifact": result["raw_file"]["artifact_ref"] = "artifact_" + "0" * 64
    elif target == "sha_newline":
        result["raw_file"]["sha256"] += "\n"
        result["raw_file"]["artifact_ref"] += "\n"
    elif target == "md5_newline": result["raw_file"]["md5"] += "\n"
    elif target == "claim": result["selection"]["claims"]["size_bytes"] = 0
    elif target == "selection_url": result["selection"]["selected_url"] += "/different"
    else: result["source_ref"] = SOURCE
    with pytest.raises(ValueError): sra.validate_sra_file_value(result)


def test_validation_and_receipt_projection_use_saved_value_without_parser_or_original_bytes(monkeypatch):
    result = value()
    expected = sra.sra_file_receipt(result, source_ref=SOURCE)
    monkeypatch.setattr(sra, "resolve_sra_file_selection", forbidden)
    monkeypatch.setattr(sra, "_xml", forbidden)
    monkeypatch.setattr(sra, "sra_file_value", forbidden)
    assert sra.validate_sra_file_value(result) == result
    assert sra.sra_file_receipt(result, source_ref=SOURCE) == expected


@pytest.mark.parametrize("reference", [None, SOURCE])
def test_finite_failure_receipt_never_invents_a_data_handle(reference):
    result = sra.failed_sra_file_receipt("provider_connection_failed", source_ref=reference)
    assert result == dict(acquired=False, source_ref=reference, data_ref=None,
        failure_code="provider_connection_failed")
    assert set(result) == {"acquired", "source_ref", "data_ref", "failure_code"}


@pytest.mark.parametrize("change", ["source", "data", "code", "acquired", "extra"])
def test_receipt_is_strict_common_four_with_no_hidden_reference_or_diagnostic(change):
    result = sra.failed_sra_file_receipt("provider_connection_failed")
    if change == "source": result["source_ref"] = SOURCE + "\n"
    elif change == "data": result["data_ref"] = "artifact_" + "0" * 64
    elif change == "code": result["failure_code"] = "arbitrary_failure"
    elif change == "acquired": result["acquired"] = 1
    else: result["diagnostic_ref"] = "artifact_" + "0" * 64
    with pytest.raises(ValueError): sra.validate_sra_file_receipt(result)


def test_no_source_cannot_be_used_to_construct_an_acquired_receipt():
    with pytest.raises(ValueError): sra.sra_file_receipt(value(), source_ref=None)


def test_schemas_and_validated_results_are_detached():
    result = value()
    checked = sra.validate_sra_file_value(result)
    checked["observed"]["transport"]["headers"].clear()
    assert result["observed"]["transport"]["headers"]
    for reader in (sra.sra_file_argument_schema, sra.sra_file_selection_schema,
            sra.sra_file_value_schema, sra.sra_file_receipt_schema):
        schema = reader()
        schema.clear()
        assert reader()
