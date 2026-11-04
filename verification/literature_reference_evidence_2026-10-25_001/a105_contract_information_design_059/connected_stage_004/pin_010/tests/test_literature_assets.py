"""Selected-source access tests; no unknown annotation/model/network claims.

Actual historical PMC bytes calibrate archive/PDF adapters. The HTTP client
below is explicitly saved replay, with a synthetic object-list protocol fixture.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile
import threading
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
import zipfile

import pytest

from gene_annotation_episode.acquisition import AcquisitionError, PublicClients, SourceSnapshot
from gene_annotation_episode.credit import project_credit
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.literature_assets import BASE_URL, PmcFiles, advertised_asset, parse_listing
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


def audit_directory():
    for parent in Path(__file__).resolve().parents:
        path = parent / "validation/cases/dataset_unknown_candidate/supplement-audit"
        if (path / "cloud-acquisition.json").is_file():
            return path
    pytest.skip("Historical PMC supplement calibration fixtures not installed")


def native_paths():
    found = {key + "_executable": shutil.which(key) for key in ("pdfinfo", "pdftotext", "pdftoppm")}
    if not all(found.values()):
        pytest.skip("Native Poppler calibration executables not installed")
    return found


class SavedPmc(PublicClients):
    """Actual saved article bytes; synthetic inventory is labeled explicitly."""
    def __init__(self, *, metadata_content=None, metadata_failure=False, asset_content=None):
        super().__init__()
        self.directory = audit_directory()
        self.acquisition = json.loads((self.directory / "cloud-acquisition.json").read_text())
        self.metadata_content, self.metadata_failure, self.asset_content = metadata_content, metadata_failure, asset_content
        self.calls, self.threads = [], []

    def _http(self, service, url, params, media_type, **kwargs):
        self.calls.append((service, url, params))
        self.threads.append(threading.get_ident())
        if service == "pmc_cloud_versions":
            content = (self.directory / "cloud-versions.xml").read_bytes()
            representation = "saved_actual_pmc_version_listing"
        elif service == "pmc_cloud_objects":
            # This object inventory was not retained by the old manual audit.
            # Construct a protocol fixture from its known files; do not call it
            # a new or saved actual HTTP inventory response.
            root = ET.Element("ListBucketResult", xmlns="http://s3.amazonaws.com/doc/2006-03-01/")
            ET.SubElement(root, "Prefix").text = "PMC12608037.1/"
            ET.SubElement(root, "IsTruncated").text = "false"
            for key, size in (("PMC12608037.1/PMC12608037.1.json", 1642),
                              ("PMC12608037.1/ijms-26-10351-s001.zip", 3332407)):
                entry = ET.SubElement(root, "Contents")
                ET.SubElement(entry, "Key").text = key
                ET.SubElement(entry, "Size").text = str(size)
                ET.SubElement(entry, "ETag").text = '"source-etag-is-not-assumed-md5"'
            content, representation = ET.tostring(root), "synthetic_selected_object_inventory_protocol_fixture"
        elif service == "pmc_cloud_metadata":
            if self.metadata_failure:
                raise AcquisitionError("provider_http_503", phase="http_response")
            content = self.metadata_content if self.metadata_content is not None else (self.directory / "PMC12608037.1.metadata.json").read_bytes()
            representation = "modified_malformed_metadata_fixture" if self.metadata_content is not None else "saved_actual_pmc_metadata"
        else:
            assert service == "pmc_cloud_asset" and "ijms-26-10351-s001.zip" in url
            content = self.asset_content if self.asset_content is not None else (self.directory / "ijms-26-10351-s001.zip").read_bytes()
            representation = "modified_checksum_fixture" if self.asset_content is not None else "saved_actual_supplement_http_body"
        return SourceSnapshot(service, url, params, "2026-10-20T02:15:41Z", content, media_type,
            {"representation": representation, "response": {"status": 200}, "fixture_network_call": False})


def setup_case(tmp_path, **client_options):
    store = Store(tmp_path)
    store.create_problem(raw_sequence="MACT", molecule="protein")
    client = SavedPmc(**client_options)
    return store, client, ToolRegistry(store, clients=client, **native_paths())


def catalog(tools):
    versions = tools.execute("public.pmc.versions", {"pmcid": "PMC12608037"}, operation_key="versions")
    assert versions["status"] == "completed", versions
    selected = versions["result"]["versions"][0]
    files = tools.execute("public.pmc.files", {"version_ref": selected["id"]}, operation_key="files")
    return versions, files


def supplement(tools):
    versions, files = catalog(tools)
    assert files["status"] == "completed", files
    selected = next(row for row in files["result"]["assets"] if row["object_key"].endswith(".zip"))
    acquired = tools.execute("public.pmc.asset", {"asset_ref": selected["id"]}, operation_key="supplement")
    assert acquired["status"] == "completed", acquired
    return versions, files, acquired


def test_catalog_selects_actual_version_and_advertisements_without_preferred_version(tmp_path):
    store, client, tools = setup_case(tmp_path)
    with store:
        problem, targets = store.problem(), store.targets()
        versions, files, acquired = supplement(tools)
        assert versions["result"]["version_preference"] == "not_assigned"
        assert files["result"]["article_metadata"]["version"] == 1
        assert files["result"]["article_metadata"]["is_manuscript"] is False
        advertised = acquired["result"]["original_advertisement"]
        assert advertised["original_uri"].startswith("s3://pmc-oa-opendata/PMC12608037.1/")
        assert acquired["result"]["advertised_md5"] == "04ee012f6b8f1bceb6390a5e15a6d11b"
        assert acquired["result"]["advertised_md5_matches"] is True
        assert acquired["result"]["actual_sha256"] == "02e9a1e80e723f9ce2cd840a9c7b7dfd5aee46f178e0b7504fc85289cc7f486c"
        assert client.calls[0][2]["prefix"] == "PMC12608037."
        assert client.calls[1][2]["prefix"] == "PMC12608037.1/"
        assert "PMC12608037.1.json" in client.calls[2][1]
        assert all(value != threading.get_ident() for value in client.threads)
        before = len(client.calls), store.count("source"), store.count("material")
        selected = advertised["id"]
        assert tools.execute("public.pmc.asset", {"asset_ref": selected}, operation_key="supplement") == acquired
        assert before == (len(client.calls), store.count("source"), store.count("material"))
        assert store.problem() == problem and store.targets() == targets
        assert project_credit(store).credit == 0 and not store.current_annotations()


@pytest.mark.parametrize("failure", ["transport", "malformed"])
def test_metadata_failure_retains_listed_objects_for_explicit_acquisition(tmp_path, failure):
    options = {"metadata_failure": True} if failure == "transport" else {"metadata_content": b'{"bad":'}
    store, client, tools = setup_case(tmp_path, **options)
    with store:
        versions, files = catalog(tools)
        assert files["status"] == "partial", files
        assert files["feedback"]["code"] == ("provider_http_503" if failure == "transport" else "pmc_metadata_invalid_json")
        objects = files["result"]["objects"]
        selected = next(row for row in objects if row["object_key"].endswith(".zip"))
        assert store.get(selected["id"])["record_type"] == "pmc_object"
        acquired = tools.execute("public.pmc.asset", {"asset_ref": selected["id"]})
        assert acquired["status"] == "completed", acquired
        assert acquired["result"]["advertised_md5"] is None
        assert acquired["result"]["original_advertisement"]["etag"] == '"source-etag-is-not-assumed-md5"'
        assert acquired["result"]["advertised_md5_matches"] is None


def test_checksum_change_preserves_actual_bytes_with_explicit_qualification(tmp_path):
    store, client, tools = setup_case(tmp_path, asset_content=b"different actual bytes, synthetic checksum fixture")
    with store:
        _, files = catalog(tools)
        selected = next(row for row in files["result"]["assets"] if row["object_key"].endswith(".zip"))
        result = tools.execute("public.pmc.asset", {"asset_ref": selected["id"]})
        assert result["status"] == "partial"
        assert result["feedback"]["code"] == "advertised_checksum_differs_from_actual_bytes"
        assert store.get_artifact(result["result"]["artifact_ref"]) == client.asset_content
        assert result["result"]["material_ref"] in result["record_refs"]
        assert project_credit(store).credit == 0 and not store.current_annotations()


def test_actual_archive_and_native_pdf_page_text_are_reusable_scientific_sources(tmp_path, monkeypatch):
    store, client, tools = setup_case(tmp_path)
    with store:
        problem, targets = store.problem(), store.targets()
        _, _, acquired = supplement(tools)
        archive_source = acquired["result"]["source_ref"]
        inventory = tools.execute("source.archive.members", {"source_ref": archive_source})
        assert inventory["status"] == "completed" and inventory["result"]["total"] == 1
        member = inventory["result"]["members"][0]
        assert member["name"] == "ijms-3902378-supplementary.pdf" and member["size"] == 3712700
        extracted = tools.execute("source.archive.extract", {"member_ref": member["id"]}, operation_key="extract")
        assert extracted["status"] == "completed", extracted
        assert extracted["result"]["media_type"] == "application/pdf"
        assert hashlib.sha256(store.get_artifact(extracted["result"]["artifact_ref"])).hexdigest() == "99c24646bc146e2e12cfb78a045b4167b3055da0057a1bd9cfa69b2e0d7e7480"
        pdf_source = extracted["result"]["source_ref"]
        import gene_annotation_episode.tools as module
        original_native, worker_threads = module.pdf_native, []
        owner = threading.get_ident()
        def observed(*args, **kwargs):
            worker_threads.append(threading.get_ident())
            assert not store.db.in_transaction
            return original_native(*args, **kwargs)
        monkeypatch.setattr(module, "pdf_native", observed)
        information = tools.execute("source.pdf.info", {"source_ref": pdf_source})
        assert information["status"] == "completed" and information["result"]["page_count"] == 40
        text = tools.execute("source.pdf.text", {"source_ref": pdf_source, "page": 7, "layout": "layout"}, operation_key="page-text")
        assert text["status"] == "completed", text
        assert text["result"]["coordinate_system"] == "normalized_utf8_bytes"
        text_source = store.get(text["result"]["source_ref"])
        text_bytes = store.get_artifact(text_source["artifact_ref"])
        assert text_source["text_ref"] == text_source["artifact_ref"]
        assert "Figure S6" in text_bytes.decode("utf-8")
        read = tools.execute("source.read", {"source_ref": text_source["id"], "limit": 10000})
        assert read["status"] == "completed" and read["result"]["text"].encode() == text_bytes
        image = tools.execute("source.pdf.page", {"source_ref": pdf_source, "page": 7, "dpi": 120}, operation_key="page-image")
        assert image["status"] == "completed" and image["result"]["media_type"] == "image/png", image
        assert "base64" not in json.dumps(image)
        image_source = store.get(image["result"]["image_source_ref"])
        png = store.get_artifact(image_source["artifact_ref"])
        assert png.startswith(b"\x89PNG\r\n\x1a\n")
        assert store.get(image_source["artifact_ref"])["media_type"] == "image/png"
        derivative = store.get(image["result"]["derivation_ref"])
        assert derivative["parent_source_ref"] == pdf_source and derivative["page"] == 7
        assert all(value != owner for value in worker_threads)
        old_count = len(worker_threads), store.count("source"), store.count("source_derivative")
        assert tools.execute("source.pdf.page", {"source_ref": pdf_source, "page": 7, "dpi": 120}, operation_key="page-image") == image
        assert old_count == (len(worker_threads), store.count("source"), store.count("source_derivative"))
        assert store.problem() == problem and store.targets() == targets
        assert not store.list("hypothesis") and not store.current_annotations() and project_credit(store).credit == 0
        # Native source parents give generic forward closure; exact source-bound
        # handles are included by the existing export's indexed provenance path.
        from gene_annotation_episode.export import export_annotation
        exported_path = tmp_path / "selected-evidence.annotation.json"
        export_annotation(store, exported_path, include_artifacts=True, page_size=2)
        exported = json.loads(exported_path.read_text())
        records = {row["id"]: row for row in exported["records"]}
        chain = [image_source["id"], pdf_source, acquired["result"]["source_ref"]]
        assert records[chain[0]]["parent_source_refs"] == [chain[1]]
        assert records[chain[1]]["parent_source_refs"] == [chain[2]]
        assert all(ref in records for ref in chain)
        assert derivative["id"] in records and member["id"] in records
        assert all(ref in exported["membership"]["source_only_record_refs"] for ref in (derivative["id"], member["id"]))
        advertised = acquired["result"]["original_advertisement"]
        assert advertised["id"] in records and advertised["catalog_ref"] in records and advertised["version_ref"] in records
        metadata_source = records[advertised["source_ref"]]
        listing_source = records[metadata_source["parent_source_refs"][0]]
        version_source = records[listing_source["parent_source_refs"][0]]
        assert version_source["provider"] == "pmc_cloud_versions"
        artifacts = {row["id"]: row for row in exported["artifacts"]}
        for source in [records[ref] for ref in chain] + [metadata_source, listing_source, version_source]:
            artifact = artifacts[source["artifact_ref"]]
            assert artifact["content_included"] is True
            assert (tmp_path / artifact["relative_path"]).is_file()
        for native_source in (records[image_source["id"]], records[text_source["id"]]):
            metadata = json.loads(store.get_artifact(native_source["request_ref"]))
            for key in ("stdout_ref", "stderr_ref"):
                assert native_source[key] == metadata[key]
                artifact = artifacts[native_source[key]]
                assert (tmp_path / artifact["relative_path"]).read_bytes() == store.get_artifact(native_source[key])
        assert exported["inputs"] == targets


def test_native_pdf_failures_preserve_original_and_return_specific_diagnostics(tmp_path):
    store, client, tools = setup_case(tmp_path)
    with store:
        material = store.register_material(data=b"Not actually a PDF; explicitly synthetic failure fixture", use="evidence", format="opaque")
        original = store.get(material["source_ref"])
        before = store.count("source_derivative")
        failed = tools.execute("source.pdf.info", {"source_ref": original["id"]})
        assert failed["status"] == "failed" and failed["feedback"]["code"] == "pdf_native_error", failed
        assert failed["feedback"]["native_returncode"] != 0 and failed["feedback"]["native_stderr_tail"]
        diagnostic = json.loads(store.get_artifact(failed["feedback"]["diagnostic_ref"]))
        assert store.get_artifact(diagnostic["stderr_ref"])
        assert store.count("source_derivative") == before and store.get(original["id"]) == original
        unavailable = ToolRegistry(store, clients=client).execute("source.pdf.text", {"source_ref": original["id"], "page": 1})
        assert unavailable["status"] == "unavailable" and unavailable["feedback"]["code"] == "pdftotext_not_configured"


def test_archive_duplicate_names_and_paths_are_identities_not_host_write_paths(tmp_path):
    store, client, tools = setup_case(tmp_path)
    with store:
        content = io.BytesIO()
        with zipfile.ZipFile(content, "w") as archive:
            archive.writestr("../../escape.txt", b"first selected source")
            with pytest.warns(UserWarning):
                archive.writestr("../../escape.txt", b"second selected source")
        material = store.register_material(data=content.getvalue(), use="evidence", format="opaque")
        first = tools.execute("source.archive.members", {"source_ref": material["source_ref"], "limit": 1})
        second = tools.execute("source.archive.members", first["result"]["next_query"])
        a, b = first["result"]["members"][0], second["result"]["members"][0]
        assert a["name"] == b["name"] and a["id"] != b["id"]
        result = tools.execute("source.archive.extract", {"member_ref": b["id"]})
        assert result["status"] == "completed", result
        assert store.get_artifact(result["result"]["artifact_ref"]) == b"second selected source"
        assert not (tmp_path.parent / "escape.txt").exists()


def test_catalog_boundaries_disallow_raw_urls_and_model_forged_catalogs(tmp_path):
    store, client, tools = setup_case(tmp_path)
    with store:
        invalid = tools.execute("public.pmc.asset", {"url": "file:///etc/passwd"})
        assert invalid["status"] == "invalid" and client.calls == []
        versions, files = catalog(tools)
        actual = versions["result"]["versions"][0]
        with pytest.raises(ContractError, match="origin_not_allowed"):
            store.put("pmc_version", {key: value for key, value in actual.items() if key not in {"id", "record_type", "origin"}}, origin="reasoning")
        with pytest.raises(ContractError, match="outside_public_bucket"):
            advertised_asset("https://unrelated.example/file.pdf", prefix="PMC12608037.1/")
        with pytest.raises(ContractError, match="version_mismatch"):
            advertised_asset("s3://pmc-oa-opendata/PMC999.1/file.pdf", prefix="PMC12608037.1/")


def test_public_listing_pagination_and_exact_advertised_encoding():
    listing = b'''<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
    <Prefix>PMC12608037.1%2F</Prefix><EncodingType>url</EncodingType><IsTruncated>true</IsTruncated>
    <NextContinuationToken>opaque+token/==</NextContinuationToken>
    <Contents><Key>PMC12608037.1%2Fsource%20file.pdf</Key><Size>42</Size><ETag>"multipart-2"</ETag></Contents>
    </ListBucketResult>'''
    page = parse_listing(listing)
    assert page["prefix"] == "PMC12608037.1/"
    assert page["objects"][0]["key"] == "PMC12608037.1/source file.pdf"
    assert page["next_continuation_token"] == "opaque+token/==" and page["truncated"] is True
    parsed = advertised_asset("s3://pmc-oa-opendata/PMC12608037.1/source%20file.pdf?md5=" + "a"*32, prefix=page["prefix"])
    assert parsed["https_uri"] == BASE_URL + "PMC12608037.1/source%20file.pdf?md5=" + "a"*32
    assert parsed["advertised_md5"] == "a"*32
    with pytest.raises(ContractError, match="invalid_xml"):
        parse_listing(b"<ListBucketResult>broken")


def test_native_pdf_out_of_bounds_page_creates_no_derivative(tmp_path):
    store, client, tools = setup_case(tmp_path)
    with store:
        _, _, acquired = supplement(tools)
        inventory = tools.execute("source.archive.members", {"source_ref": acquired["result"]["source_ref"]})
        extracted = tools.execute("source.archive.extract", {"member_ref": inventory["result"]["members"][0]["id"]})
        before = store.count("source_derivative")
        result = tools.execute("source.pdf.text", {"source_ref": extracted["result"]["source_ref"], "page": 41})
        assert result["status"] == "failed" and result["feedback"]["code"] == "pdf_native_error", result
        assert "page" in result["feedback"]["native_stderr_tail"].lower()
        assert store.count("source_derivative") == before


def test_tar_inventory_and_selected_regular_member_do_not_follow_links(tmp_path):
    store, client, tools = setup_case(tmp_path)
    with store:
        content = io.BytesIO()
        with tarfile.open(fileobj=content, mode="w:gz") as archive:
            entry = tarfile.TarInfo("data.txt")
            entry.size = 5
            archive.addfile(entry, io.BytesIO(b"facts"))
            link = tarfile.TarInfo("external")
            link.type = tarfile.SYMTYPE
            link.linkname = "/etc/passwd"
            archive.addfile(link)
        material = store.register_material(data=content.getvalue(), use="evidence", format="opaque")
        inventory = tools.execute("source.archive.members", {"source_ref": material["source_ref"]})
        assert inventory["status"] == "completed" and inventory["result"]["total"] == 2
        first, link = inventory["result"]["members"]
        assert link["entry_type"] == "symlink"
        extracted = tools.execute("source.archive.extract", {"member_ref": first["id"]})
        assert extracted["status"] == "completed" and store.get_artifact(extracted["result"]["artifact_ref"]) == b"facts"
        result = tools.execute("source.archive.extract", {"member_ref": link["id"]})
        assert result["status"] == "invalid" and result["feedback"]["code"] == "archive_member_not_regular_file"
        assert result["record_refs"] == []
