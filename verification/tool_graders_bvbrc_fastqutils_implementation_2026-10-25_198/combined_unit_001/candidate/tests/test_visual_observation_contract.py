"""Synthetic engineering image fixtures, not biological validation/results."""
from copy import deepcopy
import io
import json
from pathlib import Path

from PIL import Image
import pytest

from gene_annotation_episode.credit import project_credit
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.export import export_annotation
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


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
    result = ToolRegistry(store).execute("image.view", {"source_ref": source["id"]})
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
            "start": start, "end": start + len(quote), "quote": quote}}


def test_ordinary_native_view_has_exact_typed_custody_and_zero_credit(tmp_path):
    with Store(tmp_path / "state") as store:
        problem = store.create_problem(raw_sequence="MKWV", molecule="protein")
        source, original, view, result = native_view(store)
        assert view["record_type"] == "image_view" and view["origin"] == "tool"
        assert view["input_source_ref"] == source["id"]
        assert view["original_artifact_ref"] == source["artifact_ref"]
        assert store.get_artifact(source["artifact_ref"]) == original
        displayed = store.get(view["source_ref"])
        assert displayed["provider"] == "image.view" and displayed["artifact_ref"] == view["image_artifact_ref"]
        assert displayed["parent_source_refs"] == [source["id"]]
        metadata = json.loads(store.get_artifact(displayed["request_ref"]))
        assert metadata == {key: value for key, value in view.items() if key not in {"id", "record_type", "origin", "source_ref"}}
        assert result["visual_inputs"] == [view]
        assert view["id"] in store.references()["image_view"]
        assert view["image_artifact_ref"] in store.references()["artifact"]
        assert store.problem() == problem and project_credit(store).credit == 0
        # Identical native/derived PNG bytes may retain their original opaque MIME.
        assert store.get(view["image_artifact_ref"])["media_type"] in {"application/octet-stream", "image/png"}


def test_visual_reasoning_and_literal_extraction_coexist_without_origin_leak(tmp_path):
    with Store(tmp_path / "state") as store:
        target = store.create_problem(raw_sequence="MKWV")["subject_refs"][0]
        _, _, view, _ = native_view(store)
        source = text_source(store)
        commit = payload(store)
        commit["observations"] = [literal_observation(store, target, source, "before"),
            observation(target, view), literal_observation(store, target, source, "after")]
        result = store.commit_reasoning(commit, None, "text-and-image")
        assert result["status"] == "completed", result
        assert store.get(result["aliases"]["visible"])["origin"] == "reasoning"
        assert store.get(result["aliases"]["visible"])["anchor"] is None
        assert all(store.get(result["aliases"][name])["origin"] == "extracted" for name in ("before", "after"))
        assert project_credit(store).credit == 0  # interpreted observations alone are not annotations


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
        assert store.commit_reasoning(commit, None, "both-anchors")["errors"][0]["code"] == "visual_and_text_anchors_are_distinct"
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


def test_visual_provenance_and_current_interpretation_export_reopen_without_score_policy_change(tmp_path):
    workspace = tmp_path / "state"
    with Store(workspace) as store:
        problem = store.create_problem(raw_sequence="MKWV", molecule="protein")
        target = problem["subject_refs"][0]
        _, _, view, _ = native_view(store)
        commit = payload(store)
        commit["observations"] = [observation(target, view)]
        commit["hypotheses"] = [{"alias": "h", "subject_refs": [target], "predicate": "sequence_integrity",
            "value": {"type": "enum", "value": "intact"}, "context_refs": []}]
        commit["assessments"] = [{"alias": "a", "hypothesis_ref": "@h", "observation_ref": "@visible",
            "relation": "strengthens", "applicability": "scope_limited", "extent_basis": "inferred_extent",
            "target_footprint": [{"target_ref": target, "start": 0, "end": 4, "unit": "aa"}],
            "condition_refs": [], "assumption_refs": [], "expected_revision": 0}]
        commit["annotation_updates"] = [{"alias": "n", "subject_ref": target, "footprint_kind": "localized",
            "coherent_sets": [{"interpretations": [{"hypothesis_ref": "@h", "disposition": "unresolved", "assessment_refs": ["@a"]}], "context_refs": []}],
            "alternative_refs": [], "resolution": "unresolved", "expected_revision": 0}]
        result = store.commit_reasoning(commit, None, "synthetic-visual-account")
        assert result["status"] == "completed", result
        score = project_credit(store).as_record()
        assert score["credit"] > 0  # existing policy, not accuracy or pixel-count credit
        assert score["source_contributions"][0]["origin"] == "reasoning"
    with Store(workspace) as store:
        assert store.problem() == problem
        assert project_credit(store).as_record() == score
        exported = export_annotation(store, tmp_path / "account.json", include_artifacts=True, page_size=1)
        document = json.loads(Path(exported["json"]["path"]).read_text())
        records = {row["id"]: row for row in document["records"]}
        stored_observation = records[result["aliases"]["visible"]]
        assert stored_observation["origin"] == "reasoning" and stored_observation["visual_anchor"]["view_ref"] == view["id"]
        assert records[view["id"]] == view
        assert records[view["input_source_ref"]]["artifact_ref"] == view["original_artifact_ref"]
        artifact = next(row for row in document["artifacts"] if row["id"] == view["image_artifact_ref"])
        saved = Path(exported["json"]["path"]).parent / artifact["relative_path"]
        assert saved.read_bytes() == store.get_artifact(view["image_artifact_ref"])
        assert len(document["inputs"]) == 1


def test_integer_tiff_preserve_never_silently_clamps_and_explicit_rgb_is_recorded(tmp_path):
    with Store(tmp_path / "state") as store:
        store.create_problem(raw_sequence="MKWV")
        pixels = [0, 100000] + [0] * 94
        source, original = source_image(store, mode="I", pixels=pixels, format="TIFF")
        tools = ToolRegistry(store)
        preserve = tools.execute("image.view", {"source_ref": source["id"]})
        assert preserve["status"] == "invalid"
        assert preserve["feedback"]["code"] == "image_pixels_not_preserved_in_png"
        assert store.list("image_view") == []
        assert store.get_artifact(source["artifact_ref"]) == original
        converted = tools.execute("image.view", {"source_ref": source["id"], "colour_conversion": "rgb"})
        assert converted["status"] == "completed", converted
        view = converted["result"]["view"]
        assert view["colour_conversion"] == "rgb" and view["selected_mode"] == "I" and view["display_mode"] == "RGB"


def test_repeated_view_of_unwrapped_source_exports_actual_forward_source_chain(tmp_path):
    with Store(tmp_path / "state") as store:
        target = store.create_problem(raw_sequence="MKWV")["subject_refs"][0]
        image = Image.new("RGB", (12, 8), "white")
        buffer = io.BytesIO()
        image.save(buffer, format="TIFF")
        artifact = store.artifact(buffer.getvalue(), "image/tiff")
        # Honest raw fixture source, outside the caller-material inventory.
        original = store.put("source", {"provider": "synthetic_image_fixture", "accession": None,
            "uri": None, "artifact_ref": artifact, "text_ref": None, "request_ref": None,
            "version": None, "retrieved_at": None}, origin="caller")
        tools = ToolRegistry(store)
        first = tools.execute("image.view", {"source_ref": original["id"]})
        assert first["status"] == "completed", first
        first_view = first["result"]["view"]
        second = tools.execute("image.view", {"source_ref": first_view["source_ref"]})
        assert second["status"] == "completed", second
        second_view = second["result"]["view"]
        commit = payload(store)
        commit["observations"] = [observation(target, second_view)]
        assert store.commit_reasoning(commit, None, "re-view-observation")["status"] == "completed"
        exported = export_annotation(store, tmp_path / "re-view.json", include_artifacts=True, page_size=1)
        document = json.loads(Path(exported["json"]["path"]).read_text())
        records = {row["id"]: row for row in document["records"]}
        artifacts = {row["id"]: row for row in document["artifacts"]}
        assert records[second_view["source_ref"]]["parent_source_refs"] == [first_view["source_ref"]]
        assert records[first_view["source_ref"]]["parent_source_refs"] == [original["id"]]
        assert records[original["id"]]["artifact_ref"] == artifact
        for source_ref in (original["id"], first_view["source_ref"], second_view["source_ref"]):
            source = records[source_ref]
            for ref in (source["artifact_ref"], source["request_ref"]):
                if ref is None:
                    continue
                saved = Path(exported["json"]["path"]).parent / artifacts[ref]["relative_path"]
                assert saved.read_bytes() == store.get_artifact(ref)
        assert records[second_view["id"]] == second_view
        assert project_credit(store).credit == 0
        wrong = {key: value for key, value in original.items() if key not in {"id", "record_type", "origin"}}
        with pytest.raises(ContractError, match="wrong_reference_type"):
            store.put("source", {**wrong, "parent_source_refs": [target]}, origin="caller")
