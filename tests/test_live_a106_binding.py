"""The evaluation harness can bind the production roles without network work."""
from copy import deepcopy
import json
import os
from types import SimpleNamespace

import pytest

from live_a106_workflow import execution_factory, evaluation_tool_configuration
from audit_a106_workflow import returned_score_cells, latest_received_score_cells
from gene_annotation_episode import bvbrc_tnseq_bundle_adapter as tnseq
from gene_annotation_episode import bvbrc_rnaseq_bundle_adapter as rnaseq
from gene_annotation_episode.intervention_execution import analysis_children, contract_catalog
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_api_bvbrc_appservice import CONFIG


@pytest.mark.parametrize("field", ["a106_subscore", "literature_a106_subscore_cells"])
def test_evaluation_audit_uses_the_saved_return_contract(field):
    cell = {"value": None, "status": "unavailable", "selected_components": [{"sheet_ref": "assessment"}]}
    form = {field: [cell], "untyped_numbers": [{"value": 100}]}
    request = {"report_contract": {"measurements": {"schema": {"properties": {
        field: {"x-source": "literature_a106_subscore_cells"},
        "untyped_numbers": {"type": "array"}}}}}}
    assert returned_score_cells(form, request) == [cell]
    assert returned_score_cells(form, {"report_contract": None}) == []


def test_audit_distinguishes_received_revision_history_from_latest_results():
    original = {"sheet_ref": "original", "revises_subscore_ref": None, "value": None}
    revised = {"sheet_ref": "revised", "revises_subscore_ref": "original", "value": None}
    other_scope = {"sheet_ref": "other-scope", "revises_subscore_ref": None, "value": None}
    assert latest_received_score_cells([original, revised, original, other_scope, revised]) == [revised, other_scope]
    assert latest_received_score_cells([original]) == [original]


def pdf_with_text(path, texts=("A106 document fixture",)):
    font_ref = 3 + 2 * len(texts)
    kids = " ".join(f"{3 + 2 * index} 0 R" for index in range(len(texts)))
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {len(texts)} >>".encode(),
    ]
    for index, text in enumerate(texts):
        literal = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").encode("ascii")
        content = b"BT /F1 12 Tf 10 40 Td (" + literal + b") Tj ET\n"
        objects.extend([
            ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 80] "
             f"/Resources << /Font << /F1 {font_ref} 0 R >> >> /Contents {4 + 2 * index} 0 R >>").encode(),
            b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"endstream",
        ])
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    body, offsets = bytearray(b"%PDF-1.4\n"), [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(body))
        body.extend(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(body)
    body.extend(f"xref\n0 {len(offsets)}\n".encode() + b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        body.extend(f"{offset:010d} 00000 n \n".encode())
    body.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    path.write_bytes(body)


@pytest.mark.parametrize("operation,executable_name", [
    ("info", "pdfinfo"), ("page", "pdftoppm"), ("text", "pdftotext"),
])
def test_native_document_read_uses_the_actual_workflow_memory_bound(
        tmp_path, monkeypatch, operation, executable_name):
    from gene_annotation_episode.document_tools import pdf_native
    from gene_annotation_episode.tool_configuration import build_tools
    from gene_annotation_episode.workflow_budget import ENV, active_budget
    if not os.environ.get(ENV):
        pytest.skip("Native document execution requires the owned workflow launcher")
    configuration = evaluation_tool_configuration(tmp_path)
    executable = configuration["local_tools"].get(executable_name + "_executable")
    if executable is None:
        pytest.skip(f"Poppler {executable_name} is not installed")
    monkeypatch.setenv("GENE_EPISODE_LOCAL_RESOURCE_DIRECTORY", str(tmp_path / "local-resources"))
    document = tmp_path / "one-page.pdf"
    pdf_with_text(document)
    bounds = active_budget()["environment_bounds"]
    with Store(tmp_path / "state") as store:
        tools = build_tools(store, configuration)
        assert tools.local_job_policy.memory_bytes == bounds["memory_bytes"]
        limits = tools.local_resources.as_record()["limits"]
        assert limits["memory_bytes"] == bounds["memory_bytes"]
        assert limits["cpu_threads"] * 100 == bounds["cpu_percent"]
        selection = {"page": 1, "dpi": 72} if operation == "page" else (
            {"first_page": 1, "last_page": 1, "layout": "reading_order"} if operation == "text" else {})
        result = pdf_native(document, operation=operation, executables={executable_name: executable},
            job_limits=tools.local_job_policy.to_dict(),
            **selection)
        assert result.metadata["returncode"] == 0
        if operation == "info":
            assert result.metadata["page_count"] == 1
        elif operation == "page":
            assert result.content.startswith(b"\x89PNG\r\n\x1a\n")
        else:
            assert b"A106 document fixture" in result.content
            assert result.metadata["selection"]["first_page"] == result.metadata["selection"]["last_page"] == 1
        assert result.metadata["job_limits"]["memory_bytes"] == bounds["memory_bytes"]


def test_resume_preserves_original_tool_configuration(tmp_path, monkeypatch):
    original = {"public": {"provider_access_dir": str(tmp_path / "old-access")},
        "local_jobs": {"memory_bytes": 256 * 1024**2},
        "local_tools": {"pdfinfo_executable": "/original/bin/pdfinfo"}}
    workflow = tmp_path / "workflow"
    workflow.mkdir()
    (workflow / "run.json").write_text(json.dumps({"tool_configuration": original}))
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Resume must use the original saved tool configuration")
    monkeypatch.setattr("gene_annotation_episode.workflow_budget.active_budget", forbidden)
    monkeypatch.setattr("live_a106_workflow.shutil.which", forbidden)
    assert evaluation_tool_configuration(tmp_path, resume=True) == original


def test_native_spreadsheet_read_uses_the_actual_workflow_memory_bound(tmp_path, monkeypatch):
    from gene_annotation_episode.spreadsheet_tools import xlsx_native
    from gene_annotation_episode.tool_configuration import build_tools
    from gene_annotation_episode.workflow_budget import active_budget
    from test_spreadsheet_tools import workbook
    monkeypatch.setenv("GENE_EPISODE_LOCAL_RESOURCE_DIRECTORY", str(tmp_path / "local-resources"))
    document, _ = workbook(tmp_path)
    configuration = evaluation_tool_configuration(tmp_path)
    with Store(tmp_path / "state") as store:
        tools = build_tools(store, configuration)
        result = xlsx_native(document, operation="sheets", arguments={},
            job_limits=tools.local_job_policy.to_dict())
    assert result.metadata["returncode"] == 0
    assert result.metadata["job_limits"]["memory_bytes"] == active_budget()["environment_bounds"]["memory_bytes"]
    sheet, = json.loads(result.content)["sheets"]
    assert sheet["name"] == "Evidence" and sheet["available"]


def test_explicit_analysis_binding_preserves_anonymous_input_boundary(tmp_path, monkeypatch):
    monkeypatch.setattr("socket.create_connection", lambda *a, **k: pytest.fail("unexpected network work"))
    monkeypatch.setenv("GENE_EPISODE_LOCAL_RESOURCE_DIRECTORY", str(tmp_path / "local-resources"))
    resource = deepcopy(CONFIG)
    resource["scientific_adapters"] = [dict(adapter_id=module.ADAPTER_ID, adapter_version=module.ADAPTER_VERSION,
        implementation_sha256=module.implementation_sha256()) for module in (tnseq, rnaseq)]
    config = dict(resources={"analysis":resource}, initial_information={}, handoff_unit=1,
        acquired_record_unit=1, log_window_bytes=1024, log_roles=["stdout", "stderr"])
    with Store(tmp_path / "state") as store:
        tools = ToolRegistry(store)
        services = SimpleNamespace(workflow=SimpleNamespace(run_id="controlled-run"))
        factory = execution_factory(config, store=store, directory=tmp_path / "execution", tool_registry=tools)
        config["resources"].clear()
        family = factory(services)
        services.workflow.episode_bindings = SimpleNamespace(roles=family.roles, for_role=lambda _:family)
        assert analysis_children(services) == ("launch", "results")
        assert contract_catalog(services)[0]["input_schema"]["properties"]["resource_id"] == {"enum":["analysis"]}
        assert set(family.api_execution.services["analysis"].scientific_adapters) == {("bvbrc_tnseq", "1"), ("bvbrc_rnaseq", "1")}
        config["initial_information"] = {"analysis":{"expected_findings":"must not preload"}}
        with pytest.raises(ValueError, match="empty_initial_information"):
            execution_factory(config, store=store, directory=tmp_path / "execution", tool_registry=tools)
