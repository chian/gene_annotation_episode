"""Native title custody and bounded projections; no biological truth claims."""
import hashlib
import io
import json
from pathlib import Path

from Bio.SeqIO.QualityIO import FastqGeneralIterator
import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.export import export_annotation
from gene_annotation_episode.material_parsing import VERSION
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


def execute(tools, name, arguments, **kwargs):
    result = tools.execute(name, arguments, **kwargs)
    assert result["status"] in {"completed", "partial"}, result
    return result["result"]


def reconstructed(tools, member_ref, limit=12000):
    args, text, windows = {"member_ref": member_ref, "limit": limit}, [], []
    while args:
        page = execute(tools, "material.header", args)
        text.append(page["text"])
        windows.append(page)
        assert len(page["text"].encode("utf-8")) <= limit
        args = page["next_query"]
    return "".join(text), windows


def test_100k_identifier_and_description_are_bounded_previews_and_exact_native_title(tmp_path):
    name, description = "i" * 100000, "d" * 100000
    title = name + "  " + description
    content = (">" + title + "\nACGT\n").encode()
    with Store(tmp_path / "state") as store:
        initial = store.create_problem(raw_sequence="MKWV", molecule="protein")
        material = store.register_material(data=content, name="long-header")
        attempt = store.parse_material(material["id"])
        tools = ToolRegistry(store)
        page = execute(tools, "material.members", {"collection_ref": attempt["collection_ref"], "limit": 1})
        preview, = page["members"]
        assert "name" not in preview and "description" not in preview
        assert preview["name_preview"] == {"text": name[:256], "characters": 100000, "utf8_bytes": 100000, "complete": False}
        assert preview["description_preview"]["characters"] == 100000
        assert not preview["description_preview"]["complete"]
        assert len(json.dumps(page).encode()) < 4000
        selected = execute(tools, "material.member", {"member_ref": preview["id"], "limit": 1})
        assert selected["sequence"] == "A"
        assert len(json.dumps(selected).encode()) < 4000
        native = store.get(preview["id"])
        assert native["name"] == name and native["description"] == description
        assert store.get_artifact(native["header_ref"]).decode() == title
        actual, windows = reconstructed(tools, preview["id"])
        assert actual == title and len(windows) > 1
        assert all(page["source_ref"] == native["source_ref"] and page["parser_version"] == VERSION for page in windows)
        reference = store.get(selected["reference_ref"])
        assert reference["label_is_preview"] and reference["label_full_characters"] == 100000
        assert reference["label"] == name[:512]
        model_reference = next(row for row in store.reasoning_view()["references"] if row["id"] == reference["id"])
        assert "label" not in model_reference and not model_reference["label_preview"]["complete"]
        assert len(json.dumps(model_reference).encode()) < 3000
        assert store.problem() == initial
        assert store.count("source") == 2  # original target and evidence; no per-header source rows


def test_automatic_target_projection_preserves_ids_without_nested_identifier_bypass(tmp_path):
    name, description = "n" * 100000, "z" * 100000
    path = tmp_path / "target.fa"
    path.write_text(">" + name + " " + description + "\nACGT\n")
    with Store(tmp_path / "state") as store:
        problem = store.create_problem(path, molecule="dna")
        target, = store.targets()
        view = store.reasoning_view()
        projected, = view["subjects"]
        assert projected["id"] == target["id"] == problem["subject_refs"][0]
        assert "name" not in projected and "description" not in projected
        assert "identifier" not in projected["source_record"]
        assert projected["source_record"]["identifier_preview"]["characters"] == 100000
        assert len(json.dumps(view).encode()) < 20000
        assert target["name"] == target["source_record"]["identifier"] == name
        assert store.get(target["id"])["description"] == description
        assert store.scope_coverage() == [{"target_ref": target["id"], "start": 0, "end": 4, "unit": "nt"}]
        tools = ToolRegistry(store)
        title, _ = reconstructed(tools, projected["header"]["read_with"]["member_ref"])
        assert title == name + " " + description
        exact = execute(tools, "state.query", {"refs": [target["id"]]})["records"][0]
        assert exact == target  # explicit full-record access is unchanged


def test_unicode_header_windows_have_exact_utf8_boundaries_and_continuations(tmp_path):
    title = "αβ 🧬 exact native title"
    with Store(tmp_path / "state") as store:
        store.create_problem(raw_sequence="MKWV")
        material = store.register_material(data=(">" + title + "\nACGT\n").encode())
        attempt = store.parse_material(material["id"])
        member = store.material_members(attempt["collection_ref"])["members"][0]
        tools = ToolRegistry(store)
        too_small = tools.execute("material.header", {"member_ref": member["id"], "offset": 0, "limit": 1})
        assert too_small["feedback"]["code"] == "header_window_too_small_for_character"
        bad_offset = tools.execute("material.header", {"member_ref": member["id"], "offset": 1, "limit": 4})
        assert bad_offset["feedback"]["code"] == "header_offset_not_utf8_boundary"
        result, windows = reconstructed(tools, member["id"], limit=7)
        assert result == title
        assert windows[0]["start"] == 0
        assert all(a["end"] == b["start"] for a, b in zip(windows, windows[1:]))
        assert windows[-1]["end"] == len(title.encode())
        assert windows[-1]["next_query"] is None


@pytest.mark.parametrize("format,content,expected_title", [
    ("fasta", b"  >  actual  description \t\r\nACGT\r\n", "  actual  description"),
    ("fastq", b"@  actual  description \t\r\nACGT\r\n+\r\n!@+~\r\n", "  actual  description"),
])
def test_native_parser_title_is_distinct_from_original_header_bytes(tmp_path, format, content, expected_title):
    with Store(tmp_path / "state") as store:
        store.create_problem(raw_sequence="MKWV")
        material = store.register_material(data=content, format=format)
        attempt = store.parse_material(material["id"])
        assert attempt["status"] == "completed"
        member = store.material_members(attempt["collection_ref"])["members"][0]
        tools = ToolRegistry(store)
        title, windows = reconstructed(tools, member["id"])
        assert title == expected_title
        assert windows[0]["representation"] == "parser_returned_title"
        assert windows[0]["original_header_bytes"] is False
        assert "source_header_start" not in windows[0]
        assert store.get_artifact(store.get(material["source_ref"])["artifact_ref"]) == content
        if format == "fastq":
            assert title == next(FastqGeneralIterator(io.StringIO(content.decode())))[0]


def test_partial_native_title_and_errors_survive_export_reopen_without_source_rows(tmp_path):
    title = "α" * 100000 + " retained description"
    content = ("@" + title + " \t\r\nACGT\r\n+\r\n!@+~\r\n@bad\nACGT\n+\n!!\n").encode()
    workspace = tmp_path / "state"
    with Store(workspace) as store:
        original = store.create_problem(raw_sequence="MKWV")
        material = store.register_material(data=content)
        attempt = store.parse_material(material["id"])
        assert attempt["status"] == "partial" and attempt["valid_records"] == 1
        member = store.material_members(attempt["collection_ref"])["members"][0]
        native = store.get(member["id"])
        errors = store.material_errors(attempt["id"])["errors"]
    with Store(workspace) as store:
        assert store.problem() == original
        assert store.parse_material(material["id"]) == attempt
        selected = execute(ToolRegistry(store), "material.member", {"member_ref": member["id"], "limit": 2})
        assert selected["sequence"] == "AC" and selected["quality"] == "!@"
        assert len(json.dumps(selected).encode()) < 6000
        exported = export_annotation(store, tmp_path / "portable.json", include_artifacts=True, page_size=1)
        data = json.loads(Path(exported["json"]["path"]).read_text())
        row = next(row for row in data["records"] if row["id"] == member["id"])
        assert row["name"] == "α" * 100000 and row["description"] == "retained description"
        assert row["header_representation"] == "parser_returned_title" and row["parser_version"] == VERSION
        exported_errors = [row for row in data["parse_errors"] if row["parse_ref"] == attempt["id"]]
        assert [{key: row[key] for key in error} for error, row in zip(errors, exported_errors)] == errors
        exact_header_ref = "artifact_" + native["storage"]["components"]["header"]["sha256"]
        assert native["header_ref"] is None  # immutable packed index, not a cache pointer
        artifact = next(row for row in data["artifacts"] if row["id"] == exact_header_ref)
        saved = Path(exported["json"]["path"]).parent / artifact["relative_path"]
        assert saved.read_text() == title
        assert hashlib.sha256(saved.read_bytes()).hexdigest() == artifact["sha256"]
        assert store.count("source") == 2


def test_raw_material_name_is_not_claimed_as_original_file_header(tmp_path):
    with Store(tmp_path / "state") as store:
        store.create_problem(raw_sequence="ACGT")
        collection = store.list("collection")[0]
        member = store.material_members(collection["id"])["members"][0]
        header = store.material_header(member["id"])
        assert header["text"] == "input"
        assert header["representation"] == "caller_material_name" and not header["original_header_bytes"]


def test_member_identity_and_display_preview_metadata_cannot_be_forged(tmp_path):
    with Store(tmp_path / "state") as store:
        store.create_problem(raw_sequence="MKWV")
        material = store.register_material(data=b">actual\nACGT\n>other\nTTTT\n")
        attempt = store.parse_material(material["id"])
        first, second = [store.get(row["id"]) for row in store.material_members(attempt["collection_ref"])["members"]]
        actual = store.material_reference(first["id"])
        payload = {key: value for key, value in actual.items() if key not in {"id", "record_type", "origin"}}
        with pytest.raises(ContractError, match="member_reference_identity_mismatch"):
            store.put("reference", {**payload, "sequence_ref": second["sequence_ref"]}, origin="tool")
        with pytest.raises(ContractError, match="member_reference_label_metadata_mismatch"):
            store.put("reference", {**payload, "label_is_preview": True}, origin="tool")
        assert store.list("reference") == [actual]
        assert "label_is_preview" not in store.reasoning_schema()["properties"]["source_subjects"]["items"]["properties"]
