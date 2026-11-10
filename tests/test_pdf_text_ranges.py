"""Selected PDF ranges remain searchable sources with their exact provenance."""
import json
import os

import pytest

from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_configuration import build_tools
from gene_annotation_episode.workflow_budget import ENV
from live_a106_workflow import evaluation_tool_configuration
from test_live_a106_binding import pdf_with_text


@pytest.fixture
def pdf_case(tmp_path, monkeypatch):
    if not os.environ.get(ENV):
        pytest.skip("Native document execution requires the owned workflow launcher")
    configuration = evaluation_tool_configuration(tmp_path)
    if configuration["local_tools"].get("pdftotext_executable") is None:
        pytest.skip("Poppler pdftotext is not installed")
    monkeypatch.setenv("GENE_EPISODE_LOCAL_RESOURCE_DIRECTORY", str(tmp_path / "local-resources"))
    document = tmp_path / "three-pages.pdf"
    pdf_with_text(document, texts=("Before selection", "Target table", "After target"))
    with Store(tmp_path / "state") as store:
        store.create_problem(raw_sequence="MACT", molecule="protein")
        material = store.register_material(data=document.read_bytes(), format="opaque", use="evidence")
        yield store, build_tools(store, configuration), material["source_ref"]


@pytest.mark.parametrize("selection,last_page", [
    ({"page": 2, "last_page": 3}, 3),
    ({"page": 2, "last_page": 2}, 2),
    ({"page": 2}, 2),
])
def test_selected_pages_can_be_located_without_losing_range_custody(pdf_case, monkeypatch, selection, last_page):
    store, tools, pdf = pdf_case
    arguments = {"source_ref": pdf, **selection}
    result = tools.execute("source.pdf.text", arguments, operation_key="selected-text")
    assert result["status"] == "completed", result
    value = result["result"]
    assert value["first_page"] == 2 and value["last_page"] == last_page
    assert value["page"] == (2 if last_page == 2 else None)
    assert value["coordinate_system"] == "normalized_utf8_bytes"
    source = store.get(value["source_ref"])
    raw = store.get_artifact(source["artifact_ref"])
    assert b"Before selection" not in raw and b"Target table" in raw
    assert (b"After target" in raw) == (last_page == 3)
    assert raw.count(b"\f") == last_page - 1
    derivative = store.get(value["derivation_ref"])
    assert derivative["parent_source_ref"] == pdf
    assert derivative["page"] == value["page"] and derivative["transformation"] == "pdf_text"
    retained = json.loads(store.get_artifact(source["request_ref"]))
    assert retained["selection"]["first_page"] == 2
    assert retained["selection"]["last_page"] == last_page
    assert retained["selection"]["page_breaks"] is True
    assert retained["input_artifact_ref"] == store.get(pdf)["artifact_ref"]
    located = tools.execute("source.locate", {"source_ref": source["id"],
        "representation": "original", "needle": "Target table", "offset": 0,
        "limit": 2, "context_bytes": 20})
    assert located["status"] == "completed", located
    witness = located["result"]["matches"][0]["witness"]
    assert raw[witness["start"]:witness["end"]] == witness["quote"].encode()

    def forbidden(*_args, **_kwargs):
        pytest.fail("Reading the saved operation must not execute PDF conversion again")

    monkeypatch.setattr("gene_annotation_episode.tools.pdf_native", forbidden)
    assert tools.execute("source.pdf.text", arguments, operation_key="selected-text") == result


@pytest.mark.parametrize("tool,selection,code", [
    ("source.pdf.text", {"page": 3, "last_page": 2}, "pdf_page_range_reversed"),
    ("source.pdf.text", {"last_page": 2}, None),
    ("source.pdf.text", {"page": 1, "last_page": 0}, None),
    ("source.pdf.page", {"page": 1, "last_page": 2}, None),
])
def test_invalid_ranges_and_image_range_requests_do_not_start_native_work(pdf_case, monkeypatch, tool, selection, code):
    store, tools, pdf = pdf_case

    def forbidden(*_args, **_kwargs):
        pytest.fail("Invalid page selection must be rejected before native work")

    monkeypatch.setattr("gene_annotation_episode.tools.pdf_native", forbidden)
    before = store.count("source_derivative")
    result = tools.execute(tool, {"source_ref": pdf, **selection})
    assert result["status"] == "invalid", result
    assert result["feedback"]["category"] == "arguments_or_reference"
    if code is not None:
        assert result["feedback"]["code"] == code
    assert store.count("source_derivative") == before
