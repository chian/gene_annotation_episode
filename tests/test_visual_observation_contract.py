"""Synthetic engineering image fixtures, not biological validation/results."""
import io

from PIL import Image
import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.tool_registry import ToolRegistry


def payload(store):
    return {key: [] for key in store.reasoning_schema()["properties"]}


def source_image(store, *, mode="RGB", pixels=None, format="PNG"):
    image = Image.new(mode, (12, 8), "white" if mode == "RGB" else 0)
    if pixels is not None:
        image.putdata(pixels)
    encoded = io.BytesIO()
    image.save(encoded, format=format)
    material = store.register_material(data=encoded.getvalue(), name="synthetic-visual-fixture", use="evidence")
    return store.get(material["source_ref"]), encoded.getvalue()


def native_view(store, **kwargs):
    source, original = source_image(store, **kwargs)
    result = ToolRegistry(store, run_directory=store.path / 'tool-run').execute("image.view", {"source_ref": source["id"]})
    assert result["status"] == "completed", result
    return source, original, result["result"]["view"], result


def observation(target, view, alias="visible", *, region=None):
    return {"alias": alias, "subject_refs": [target], "source_subject_refs": [target],
        "kind": "comparison", "source_ref": view["source_ref"],
        "measurements": [{"name": "match_state", "value": {"type": "enum", "value": "present"}}],
        "dependencies": [], "anchor": None,
        "visual_anchor": {"view_ref": view["id"], "image_artifact_ref": view["image_artifact_ref"],
            "region": region or {"x": 1, "y": 2, "width": 3, "height": 4}}}


def text_source(store):
    return store._caller_source({"fixture_caption": "Synthetic construct Z has a reported comparison."}, "synthetic_visual_caption")


def literal_observation(store, target, source, alias):
    raw = store.get_artifact(source["artifact_ref"])
    quote = "Synthetic construct Z"
    start = raw.index(quote.encode())
    return {"alias": alias, "subject_refs": [target], "source_subject_refs": [], "kind": "source_content",
        "source_ref": source["id"], "measurements": [], "dependencies": [],
        "anchor": {"source_ref": source["id"], "artifact_ref": source["artifact_ref"],
            "start": start, "end": start + len(quote)}}


@pytest.mark.parametrize("mutation,code", [
    (lambda row, view, source, other: row["visual_anchor"]["region"].update(x=11, width=2), "visual_anchor_region_outside_image"),
    (lambda row, view, source, other: row.update(source_ref=source["id"]), "visual_anchor_source_mismatch"),
    (lambda row, view, source, other: row["visual_anchor"].update(image_artifact_ref=other), "visual_anchor_image_mismatch"),
])
def test_invalid_visual_component_keeps_independent_valid_reasoning_rows(tmp_path, mutation, code):
    with Store(tmp_path / "state") as store:
        target = store.create_problem(raw_sequence="MKWV")["subject_refs"][0]
        source, _, view, _ = native_view(store)
        wrong = observation(target, view)
        mutation(wrong, view, source, store.artifact(b"different artifact"))
        commit = payload(store)
        commit["observations"] = [wrong]
        commit["hypotheses"] = [{"alias": "alternative", "subject_refs": [target], "predicate": "sequence_integrity",
            "value": {"type": "enum", "value": "intact"}, "context_refs": []}]
        result = store.commit_reasoning(commit, None, "partial-image")
        assert result["status"] == "partial", result
        assert result["errors"][0]["code"] == code
        assert "alternative" in result["aliases"] and "visible" not in result["aliases"]
        assert store.list("observation") == []


def test_visual_anchor_is_not_a_literal_quote_and_null_optional_does_not_duplicate(tmp_path):
    with Store(tmp_path / "state") as store:
        target = store.create_problem(raw_sequence="MKWV")["subject_refs"][0]
        _, _, view, _ = native_view(store)
        text = text_source(store)
        commit = payload(store)
        wrong = observation(target, view)
        wrong["anchor"] = literal_observation(store, target, text, "text")["anchor"]
        commit["observations"] = [wrong]
        assert store.commit_reasoning(commit, None, "both-anchors")["errors"][0]["code"] == "anchor_source_mismatch"
        commit["observations"] = [literal_observation(store, target, text, "text")]
        first = store.commit_reasoning(commit, None, "literal-omitted")
        commit["observations"][0]["visual_anchor"] = None
        second = store.commit_reasoning(commit, None, "literal-null")
        assert first["aliases"]["text"] == second["aliases"]["text"]
        assert second["changed_record_refs"] == []
        unquoted = observation(target, view)
        unquoted.pop("visual_anchor")
        commit["observations"] = [unquoted]
        assert store.commit_reasoning(commit, None, "unanchored-image")["errors"][0]["code"] == "extraction_anchor_required"


def test_native_view_metadata_cannot_be_forged_by_projection_or_model(tmp_path):
    with Store(tmp_path / "state") as store:
        store.create_problem(raw_sequence="MKWV")
        _, _, view, _ = native_view(store)
        data = {key: value for key, value in view.items() if key not in {"id", "record_type", "origin"}}
        with pytest.raises(ContractError, match="origin_not_allowed|image_view_requires_native_tool_origin"):
            store.put("image_view", data, origin="reasoning")
        with pytest.raises(ContractError, match="image_view_native_metadata_mismatch"):
            store.put("image_view", {**data, "width": data["width"] + 1}, origin="tool")
        assert "image_view" not in store.reasoning_schema()["properties"]
        target = store.targets()[0]["id"]
        for value in ({"type": "reference", "ref": view["id"]},
                      {"type": "relation", "roles": [{"role": "substrate", "ref": view["id"]}]}):
            with pytest.raises(ContractError, match="semantic_value_requires_entity_reference"):
                store.put("hypothesis", {"subject_refs": [target], "predicate": "catalyzes",
                    "value": value, "context_refs": []}, origin="reasoning")


def test_integer_tiff_preserve_never_silently_clamps_and_explicit_rgb_is_recorded(tmp_path):
    with Store(tmp_path / "state") as store:
        store.create_problem(raw_sequence="MKWV")
        pixels = [0, 100000] + [0] * 94
        source, original = source_image(store, mode="I", pixels=pixels, format="TIFF")
        tools = ToolRegistry(store, run_directory=store.path / 'tool-run')
        preserve = tools.execute("image.view", {"source_ref": source["id"]})
        assert preserve["status"] == "invalid"
        assert preserve["feedback"]["code"] == "image_pixels_not_preserved_in_png"
        assert store.list("image_view") == []
        assert store.get_artifact(source["artifact_ref"]) == original
        converted = tools.execute("image.view", {"source_ref": source["id"], "colour_conversion": "rgb"})
        assert converted["status"] == "completed", converted
        view = converted["result"]["view"]
        assert view["colour_conversion"] == "rgb" and view["selected_mode"] == "I" and view["display_mode"] == "RGB"


