"""Provenance representation fixtures, not biological annotation validation."""
import json
from pathlib import Path

import pytest

from gene_annotation_episode.communication import validate_form
from gene_annotation_episode.credit import project_credit
from gene_annotation_episode.document_tools import DocumentOutput
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.export import export_annotation
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_literature_assets import SavedPmc, supplement


def test_actual_custody_objects_remain_dependencies_and_forms_not_entity_values(tmp_path):
    manifest = tmp_path / "materials.json"
    manifest.write_text(json.dumps({"schema_version": 1, "entries": [
        {"sequence": "MACT", "name": "target", "use": "target", "molecule": "protein"},
        {"sequence": "ACGT", "name": "left", "use": "evidence", "role": "read",
         "links": [{"relation": "paired_with", "name": "right"}]},
        {"sequence": "TGCA", "name": "right", "use": "evidence", "role": "read"},
    ]}))
    with Store(tmp_path / "state") as store:
        problem = store.create_problem(manifest_path=manifest)
        tools = ToolRegistry(store, clients=SavedPmc())
        versions, files, acquired = supplement(tools)
        inventory = tools.execute("source.archive.members", {"source_ref": acquired["result"]["source_ref"]})
        member = inventory["result"]["members"][0]
        extracted = tools.execute("source.archive.extract", {"member_ref": member["id"]})
        assert inventory["status"] == extracted["status"] == "completed"
        objects = {
            "pmc_version": versions["result"]["versions"][0],
            "pmc_catalog": store.get(files["result"]["catalog_ref"]),
            "pmc_object": files["result"]["objects"][0],
            "pmc_asset": acquired["result"]["original_advertisement"],
            "archive_member": member,
            "source_derivative": store.get(extracted["result"]["derivation_ref"]),
            **{kind: store.list(kind)[0] for kind in ("material", "material_link", "collection", "parse_attempt")},
        }
        assert all(row["record_type"] == kind for kind, row in objects.items())
        payload = {key: [] for key in store.reasoning_schema()["properties"]}
        for kind, row in objects.items():
            for form, value in (("reference", {"type": "reference", "ref": row["id"]}),
                                ("relation", {"type": "relation", "roles": [{"role": "substrate", "ref": row["id"]}]})):
                payload["hypotheses"].append({"alias": kind + "_" + form,
                    "subject_refs": problem["subject_refs"], "predicate": "catalyzes",
                    "value": value, "context_refs": []})
        payload["hypotheses"].append({"alias": "retained", "subject_refs": problem["subject_refs"],
            "predicate": "sequence_integrity", "value": {"type": "enum", "value": "unknown"}, "context_refs": []})
        # The same actual handles are valid provenance dependencies. A source
        # inventory statement is not a catalytic or substrate assignment.
        source = store.get(files["result"]["metadata_source_ref"])
        quote = store.get_artifact(source["artifact_ref"]).decode("utf-8")
        payload["observations"].append({"alias": "inventory_content", "subject_refs": problem["subject_refs"],
            "source_subject_refs": [], "kind": "source_content", "source_ref": source["id"],
            "measurements": [], "dependencies": [row["id"] for row in objects.values()],
            "anchor": {"source_ref": source["id"], "artifact_ref": source["artifact_ref"],
                "start": 0, "end": len(quote.encode("utf-8")), "quote": quote}})
        result = store.commit_reasoning(payload, None, "synthetic-custody-contract")
        assert result["status"] == "partial", result
        assert set(result["aliases"]) == {"retained", "inventory_content"}
        assert len(result["errors"]) == 2 * len(objects)
        assert {error["code"] for error in result["errors"]} == {"semantic_value_requires_entity_reference"}
        assert len(store.list("hypothesis")) == 1
        assert store.get(result["aliases"]["inventory_content"])["dependencies"] == [row["id"] for row in objects.values()]
        query = tools.execute("state.query", {"refs": [row["id"] for row in objects.values()]})
        assert query["status"] == "completed"
        form = {kind: row["id"] for kind, row in objects.items()}
        schema = {"type": "object", "additionalProperties": False, "required": list(objects),
            "properties": {kind: {"type": "string", "format": "reference", "x-reference-namespace": kind} for kind in objects}}
        registry = store.references()
        assert validate_form(form, schema, lambda ref, namespace: ref in registry[namespace]) == form
        assert store.problem() == problem and not store.current_annotations() and project_credit(store).credit == 0


def test_optional_native_stream_fields_require_artifacts_and_are_not_model_authored(tmp_path):
    with Store(tmp_path / "state") as store:
        target = store.create_problem(raw_sequence="MACT")["subject_refs"][0]
        material = store.register_material(data=b"synthetic source content")
        source = store.get(material["source_ref"])
        body = {key: value for key, value in source.items() if key not in {"id", "record_type", "origin"}}
        stream = store.artifact(b"synthetic native stream\x00\xff", "application/octet-stream")
        recorded = store.put("source", {**body, "stdout_ref": stream, "stderr_ref": stream}, origin="tool")
        assert recorded["stdout_ref"] == recorded["stderr_ref"] == stream
        unreadable = ToolRegistry(store).execute("source.read", {"source_ref": recorded["id"], "representation": "stdout"})
        assert unreadable["status"] == "invalid" and unreadable["feedback"]["code"] == "source_not_utf8_text"
        missing = ToolRegistry(store).execute("source.read", {"source_ref": source["id"], "representation": "stderr"})
        assert missing["status"] == "invalid"
        assert missing["feedback"]["code"] == "source_representation_unavailable"
        assert missing["feedback"]["detail"] == {"representation": "stderr", "available_representations": ["original", "text"]}
        for field in ("stdout_ref", "stderr_ref"):
            with pytest.raises(ContractError, match="wrong_reference_type"):
                store.put("source", {**body, field: target}, origin="tool")
        with pytest.raises(ContractError, match="origin_not_allowed"):
            store.put("source", {**body, "stdout_ref": stream}, origin="reasoning")
        assert "source" not in store.reasoning_schema()["properties"]


def test_successful_native_warning_stream_survives_paged_read_and_portable_export(tmp_path, monkeypatch):
    """Synthetic successful native protocol output, not an actual Poppler warning."""
    with Store(tmp_path / "state") as store:
        problem = store.create_problem(raw_sequence="MACT")
        material = store.register_material(data=b"%PDF-synthetic-worker-input", use="evidence")
        stdout, stderr = b"synthetic normalized page text\n", "synthetic native warning caf\u00e9\n".encode("utf-8")
        calls = []
        def native_fixture(path, **kwargs):
            assert not store.db.in_transaction
            calls.append((path, kwargs))
            return DocumentOutput({"operation": "pdf_text", "adapter_version": "synthetic_native_warning_fixture",
                "software": "synthetic_pdftotext", "software_version": "fixture1", "returncode": 0,
                "selection": {"first_page": 1, "last_page": 1},
                "transformation": "synthetic_utf8_page_protocol_fixture"}, stdout, "text/plain", stdout, stderr)
        monkeypatch.setattr("gene_annotation_episode.tools.pdf_native", native_fixture)
        tools = ToolRegistry(store)
        args = {"source_ref": material["source_ref"], "page": 1}
        result = tools.execute("source.pdf.text", args, operation_key="successful-warning")
        assert result["status"] == "completed", result
        source = store.get(result["result"]["source_ref"])
        assert store.get_artifact(source["stdout_ref"]) == stdout
        assert store.get_artifact(source["stderr_ref"]) == stderr
        assert tools.execute("source.pdf.text", args, operation_key="successful-warning") == result
        assert len(calls) == 1
        query = {"source_ref": source["id"], "representation": "stderr", "limit": 5}
        chunks = []
        last = None
        while query is not None:
            read = tools.execute("source.read", query)
            assert read["status"] == "completed", read
            last = read["result"]
            assert last["artifact_ref"] == source["stderr_ref"] and last["representation"] == "stderr"
            assert last["end"] - last["start"] <= 5
            chunks.append(last["text"])
            query = last["next_query"]
        assert "".join(chunks).encode("utf-8") == stderr
        # The same actual stream has exact source anchors; reading it does not
        # itself create an interpretation or a scientific observation.
        anchor = {"source_ref": source["id"], "artifact_ref": source["stderr_ref"],
            "start": 0, "end": len(stderr), "quote": stderr.decode("utf-8")}
        store._anchor(anchor, source["id"])
        assert not store.list("observation")
        exported = export_annotation(store, tmp_path / "portable.json", include_artifacts=True, page_size=1)
        document = json.loads(Path(exported["json"]["path"]).read_text())
        records = {row["id"]: row for row in document["records"]}
        artifacts = {row["id"]: row for row in document["artifacts"]}
        assert records[source["id"]]["stderr_ref"] == source["stderr_ref"]
        for key, expected in (("stdout_ref", stdout), ("stderr_ref", stderr)):
            artifact = artifacts[source[key]]
            assert artifact["content_included"] is True
            assert (Path(exported["json"]["path"]).parent / artifact["relative_path"]).read_bytes() == expected
        assert store.problem() == problem and project_credit(store).credit == 0 and not store.current_annotations()
