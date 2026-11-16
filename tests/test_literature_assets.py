"""Selected-source access tests; no unknown annotation/model/network claims.

Actual historical PMC bytes calibrate archive/PDF adapters. The HTTP client
below is explicitly saved replay, with a synthetic object-list protocol fixture.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import threading
import xml.etree.ElementTree as ET

import pytest

from gene_annotation_episode.acquisition import AcquisitionError, PublicClients, SourceSnapshot
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.literature_assets import BASE_URL, advertised_asset, parse_listing
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.tool_registry import ToolRegistry


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


