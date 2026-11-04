"""Synthetic native image and protocol fixtures, not biological accuracy tests."""
import asyncio
from copy import deepcopy
from io import BytesIO
import json
from pathlib import Path

from PIL import Image
import pytest

from gene_annotation_episode.credit import project_credit
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.materials import artifact_path
from gene_annotation_episode.providers import _SessionConnection, load_config
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController, ScriptedProvider


def native_source(store, image, format="PNG", **kwargs):
    buffer = BytesIO()
    image.save(buffer, format=format, **kwargs)
    material = store.register_material(data=buffer.getvalue(), name="synthetic_image")
    return material["source_ref"], buffer.getvalue()


def test_selected_frame_retains_native_pixels_custody_and_replay(tmp_path):
    with Store(tmp_path) as store:
        original_problem = store.create_problem(raw_sequence="MKWAA", molecule="protein")
        first, second = Image.new("RGB", (7, 5), "red"), Image.new("RGB", (7, 5), "blue")
        source_ref, native = native_source(store, first, format="TIFF", save_all=True, append_images=[second])
        tools = ToolRegistry(store)
        args = {"source_ref": source_ref, "frame": 1}
        operation = tools.execute("image.view", args, operation_key="choose_second_frame")
        assert operation["status"] == "completed", operation
        view = operation["result"]["view"]
        assert operation["visual_inputs"] == [view]
        assert view["input_source_ref"] == source_ref and view["frame"] == 1 and view["frame_count"] == 2
        assert view["width"] == 7 and view["height"] == 5
        assert view["geometric_transform"] == view["contrast_transform"] == "identity"
        assert store.get_artifact(view["original_artifact_ref"]) == native
        selected = tools.resolve_image_input(view)
        assert selected["type"] == "localImage"
        with Image.open(selected["path"]) as displayed:
            assert displayed.format == "PNG" and displayed.getpixel((3, 2)) == (0, 0, 255)
        before = store.db.execute("SELECT count(*) FROM records").fetchone()[0]
        assert tools.execute("image.view", args, operation_key="choose_second_frame") == operation
        assert store.db.execute("SELECT count(*) FROM records").fetchone()[0] == before
        assert store.problem() == original_problem and not store.list("observation")
        assert project_credit(store).credit == 0
    with Store(tmp_path) as reopened:
        assert ToolRegistry(reopened).resolve_image_input(view) == selected


def test_identical_png_bytes_keep_original_mime_and_remain_viewable(tmp_path):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence="MKWAA", molecule="protein")
        source_ref, native = native_source(store, Image.new("RGB", (5, 3), "green"))
        original_artifact = store.get(source_ref)["artifact_ref"]
        assert store.get(original_artifact)["media_type"] == "application/octet-stream"
        tools = ToolRegistry(store)
        result = tools.execute("image.view", {"source_ref": source_ref})
        assert result["status"] == "completed", result
        view = result["result"]["view"]
        assert view["image_artifact_ref"] == original_artifact
        assert Path(tools.resolve_image_input(view)["path"]).read_bytes() == native


def test_conversion_and_invalid_frame_are_actionable_and_never_reselect(tmp_path):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence="MKWAA", molecule="protein")
        source_ref, native = native_source(store, Image.new("CMYK", (8, 6)), format="TIFF")
        tools = ToolRegistry(store)
        unavailable = tools.execute("image.view", {"source_ref": source_ref})
        assert unavailable["status"] == "invalid"
        assert unavailable["feedback"]["code"] == "image_mode_requires_explicit_conversion"
        assert unavailable["feedback"]["detail"]["native_mode"] == "CMYK"
        assert not store.list("image_view")
        wrong_frame = tools.execute("image.view", {"source_ref": source_ref, "frame": 7})
        assert wrong_frame["status"] == "invalid"
        assert wrong_frame["feedback"]["detail"]["frame_count"] == 1
        selected = tools.execute("image.view", {"source_ref": source_ref, "colour_conversion": "rgb"})
        assert selected["status"] == "completed", selected
        view = selected["result"]["view"]
        assert view["selected_mode"] == "CMYK" and view["display_mode"] == "RGB"
        assert view["colour_conversion"] == "rgb" and store.get_artifact(view["original_artifact_ref"]) == native


def test_forged_view_and_corrupt_artifact_cannot_be_sent_as_pixels(tmp_path):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence="MKWAA", molecule="protein")
        source_ref, _ = native_source(store, Image.new("RGB", (5, 3)))
        tools = ToolRegistry(store)
        view = tools.execute("image.view", {"source_ref": source_ref})["result"]["view"]
        forged = {**view, "path": "/etc/passwd"}
        with pytest.raises(ContractError, match="image_input_selection_mismatch"):
            tools.resolve_image_input(forged)
        image_path = artifact_path(store, view["image_artifact_ref"])
        image_path.write_bytes(b"replaced bytes")
        with pytest.raises(ContractError, match="artifact_digest_mismatch"):
            tools.resolve_image_input(view)


class WireFixture(_SessionConnection):
    """Native wire shape, with no native server, credentials or model calls."""
    def __init__(self, directory, resolver=None):
        super().__init__(load_config(), directory, directory.parent, image_resolver=resolver)
        self.sent = []
    async def _session(self, *_):
        return "synthetic_thread"
    async def _rpc(self, method, params):
        self.sent.append((method, deepcopy(params)))
        self.pending.extend([
            {"method": "item/completed", "params": {"threadId": "synthetic_thread", "item": {
                "type": "agentMessage", "phase": "final_answer", "text": '{"read":true}'}}},
            {"method": "turn/completed", "params": {"threadId": "synthetic_thread", "turn": {
                "id": "synthetic_turn", "status": "completed"}}}])
        return {"turn": {"id": "synthetic_turn"}}


def test_provider_sends_actual_selected_input_and_journals_exact_wire(tmp_path):
    image = tmp_path / "actual.png"
    Image.new("RGB", (5, 3)).save(image)
    selected = {"id": "image_view_" + "a" * 24}
    resolved = []
    def resolver(value):
        resolved.append(value)
        return {"type": "localImage", "path": str(image)}
    provider = WireFixture(tmp_path / "wire", resolver)
    context = {"visual_evidence": [selected], "not_an_attachment": {"path": "/etc/passwd"}}
    schema = {"type": "object", "properties": {"read": {"type": "boolean"}}, "required": ["read"],
              "additionalProperties": False}
    assert asyncio.run(provider.complete("episode", "REASONING", "fixture", context, schema)) == {"read": True}
    actual = provider.sent[0][1]["input"]
    assert actual == [{"type": "text", "text": json.dumps(context)}, {"type": "localImage", "path": str(image)}]
    assert resolved == [selected]
    request = json.loads((tmp_path / "wire/call-00001/request.json").read_text())
    assert request["input"] == actual and request["context"] == context
    assert request["model"] == "gpt-6-sol" and request["effort"] == "medium"


def test_missing_image_resolver_fails_before_model_dispatch(tmp_path):
    provider = WireFixture(tmp_path / "wire")
    from gene_annotation_episode.providers import ModelCallError
    with pytest.raises(ModelCallError, match="no bound artifact resolver"):
        asyncio.run(provider.complete("episode", "REASONING", "fixture", {"visual_evidence": [{"id": "chosen"}]}, {}))
    assert provider.sent == []
    assert (tmp_path / "wire/call-00001/error.json").exists()


def test_runtime_selected_image_is_one_own_observation_and_survives_resume(tmp_path):
    with Store(tmp_path / "store") as store:
        original = store.create_problem(raw_sequence="MKWAA", molecule="protein")
        source_ref, _ = native_source(store, Image.new("RGB", (5, 3)))
        select = {"selection": {"kind": "tool", "tool": "image.view", "arguments": {"source_ref": source_ref}},
                  "report_update": {}}
        next_read = {"selection": {"kind": "tool", "tool": "state.query", "arguments": {"refs": original["subject_refs"]}},
                     "report_update": {}}
        provider = ScriptedProvider([select, KeyboardInterrupt()])
        tools = ToolRegistry(store)
        factory = lambda path, initial: FixtureController(str(path), initial, 3)
        with pytest.raises(KeyboardInterrupt):
            asyncio.run(run_workflow(store, tools, provider=provider, run_dir=tmp_path / "run",
                controller_factory=factory, project_credit=lambda *_: 0))
        selected_context = provider.contexts[1]
        selected_view = selected_context["visual_evidence"][0]
        assert selected_view["id"] in selected_context["visible_record_refs"]
        assert selected_context["controller"]["scores"] == [0]
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 1
        resumed = ScriptedProvider([next_read, next_read])
        summary = asyncio.run(run_workflow(store, tools, provider=resumed, resume=True,
            controller_factory=factory, project_credit=lambda *_: 0))
        assert resumed.contexts[0]["visual_evidence"] == [selected_view]
        assert resumed.contexts[1]["visual_evidence"] == []
        assert summary["completed_actions"] == 3 and summary["credit"] == 0
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 3
        assert store.db.execute("SELECT count(*) FROM tool_operations WHERE name='image.view'").fetchone()[0] == 1


def test_parent_and_child_image_selection_uses_own_completed_action_boundary(tmp_path):
    with Store(tmp_path / "store") as store:
        target = store.create_problem(raw_sequence="MKWAA", molecule="protein")["subject_refs"][0]
        source_ref, _ = native_source(store, Image.new("RGB", (5, 3)))
        image = {"selection": {"kind": "tool", "tool": "image.view", "arguments": {"source_ref": source_ref}},
                 "report_update": {}}
        query = {"selection": {"kind": "tool", "tool": "state.query", "arguments": {"refs": [target]}},
                 "report_update": {}}
        form = {"type": "object", "properties": {"subjects": {"type": "array", "items": {
            "type": "string", "format": "reference", "x-reference-namespace": "input"},
            "x-source": "subject_refs"}}, "required": ["subjects"], "additionalProperties": False}
        child = {"selection": {"kind": "child", "goal": "Synthetic iterative reference accounting fixture",
            "scope": {"subject_refs": [target]}, "purpose": "Return the exact assigned subjects",
            "schema_json": json.dumps(form), "initial_report_json": "{}"}, "report_update": {}}
        provider = ScriptedProvider([image, child, query, query, query])
        factory = lambda path, initial: FixtureController(str(path), initial, 3 if len(path) == 1 else 2)
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider, run_dir=tmp_path / "run",
            controller_factory=factory, project_credit=lambda *_: 0))
        assert provider.contexts[1]["visual_evidence"]
        assert provider.contexts[2]["visual_evidence"] == provider.contexts[3]["visual_evidence"] == []
        assert provider.contexts[4]["visual_evidence"] == []
        assert provider.contexts[4]["child_reports"] == [{"subjects": [target]}]
        assert summary["completed_actions"] == 3 and summary["episode_count"] == 2
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 5

