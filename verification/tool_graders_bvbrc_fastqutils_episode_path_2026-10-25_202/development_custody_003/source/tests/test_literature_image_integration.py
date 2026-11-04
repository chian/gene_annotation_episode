"""Actual saved document transforms plus scripted provenance/uncertainty binding.

No model, network or biological accuracy claim. The toy input is unrelated to
the published protein; the deliberately nondiscriminating interpretation earns0.
"""
import hashlib
import json
from pathlib import Path

from gene_annotation_episode.credit import project_credit
from gene_annotation_episode.export import export_annotation
from test_literature_assets import setup_case, supplement


def test_selected_supplement_pixels_interpretation_and_export_share_exact_lineage(tmp_path):
    store, client, tools = setup_case(tmp_path / "state")
    with store:
        problem = store.problem()
        target = problem["subject_refs"][0]
        _, _, acquired = supplement(tools)
        inventory = tools.execute("source.archive.members", {"source_ref": acquired["result"]["source_ref"]})
        member = inventory["result"]["members"][0]
        extracted = tools.execute("source.archive.extract", {"member_ref": member["id"]})
        pdf = extracted["result"]["source_ref"]
        text = tools.execute("source.pdf.text", {"source_ref": pdf, "page": 7})
        page = tools.execute("source.pdf.page", {"source_ref": pdf, "page": 7, "dpi": 120})
        selected = tools.execute("image.view", {"source_ref": page["result"]["image_source_ref"]}, operation_key="view")
        assert selected["status"] == "completed", selected
        view = selected["result"]["view"]
        native_input = tools.resolve_image_input(selected["visual_inputs"][0])
        png_sha = hashlib.sha256(Path(native_input["path"]).read_bytes()).hexdigest()
        assert png_sha == store.get(view["image_artifact_ref"])["sha256"]
        caption = store.get(text["result"]["source_ref"])
        raw = store.get_artifact(caption["text_ref"])
        start = raw.index(b"YihW")
        commit = {key: [] for key in store.reasoning_schema()["properties"]}
        commit["source_subjects"] = [{"alias": "reported_construct", "reference_type": "construct",
            "source_ref": caption["id"], "label": "YihW", "anchor": {
                "source_ref": caption["id"], "artifact_ref": caption["text_ref"],
                "start": start, "end": start+4, "quote": "YihW"}}]
        commit["observations"] = [{"alias": "visible", "subject_refs": ["@reported_construct"],
            "source_subject_refs": ["@reported_construct"], "kind": "comparison",
            "source_ref": view["source_ref"], "measurements": [], "dependencies": [caption["id"]],
            "anchor": None, "visual_anchor": {"view_ref": view["id"],
                "image_artifact_ref": view["image_artifact_ref"], "region": {
                    "x": 0, "y": 0, "width": view["width"], "height": view["height"]}}}]
        commit["hypotheses"] = [{"alias": "role", "subject_refs": [target], "predicate": "biological_role",
            "value": {"type": "enum", "value": "unknown"}, "context_refs": []}]
        commit["assessments"] = [{"alias": "limit", "hypothesis_ref": "@role", "observation_ref": "@visible",
            "relation": "does_not_discriminate", "applicability": "contextual", "extent_basis": "inferred_extent",
            "target_footprint": [{"target_ref": target, "start": 0, "end": 4, "unit": "aa"}],
            "condition_refs": [], "assumption_refs": [], "expected_revision": 0}]
        commit["annotation_updates"] = [{"alias": "account", "subject_ref": target, "footprint_kind": "localized",
            "coherent_sets": [{"interpretations": [{"hypothesis_ref": "@role", "disposition": "unresolved",
                "assessment_refs": ["@limit"]}], "context_refs": []}], "alternative_refs": [],
            "resolution": "unresolved", "expected_revision": 0}]
        result = store.commit_reasoning(commit, None, "nondiscriminating_scripted_visual_account")
        assert result["status"] == "completed", result
        assert store.get(result["aliases"]["visible"])["origin"] == "reasoning"
        assert project_credit(store).credit == 0 and store.problem() == problem
        before = len(client.calls), store.count("image_view")
        assert tools.execute("image.view", {"source_ref": page["result"]["image_source_ref"]}, operation_key="view") == selected
        assert before == (len(client.calls), store.count("image_view"))
        output = tmp_path / "account.json"
        export_annotation(store, output, include_artifacts=True, page_size=2)
        document = json.loads(output.read_text())
        records = {row["id"]: row for row in document["records"]}
        assert records[view["id"]] == view
        assert records[result["aliases"]["account"]]["resolution"] == "unresolved"
        observation = records[result["aliases"]["visible"]]
        assert observation["subject_refs"] == [result["aliases"]["reported_construct"]]
        assert observation["subject_refs"] != [target]
        source = records[view["source_ref"]]
        providers = []
        while True:
            providers.append(source["provider"])
            parents = source.get("parent_source_refs", [])
            if not parents:
                break
            assert len(parents) == 1
            source = records[parents[0]]
        assert providers == ["image.view", "poppler.pdftoppm", "archive.member", "pmc_cloud_asset",
                             "pmc_cloud_metadata", "pmc_cloud_objects", "pmc_cloud_versions"]
        assert all(any(row["record_type"] == kind for row in records.values()) for kind in
                   ("pmc_version", "pmc_catalog", "pmc_asset", "archive_member", "source_derivative"))
        artifact = next(row for row in document["artifacts"] if row["id"] == view["image_artifact_ref"])
        assert hashlib.sha256((output.parent / artifact["relative_path"]).read_bytes()).hexdigest() == png_sha
        assert len(document["inputs"]) == 1
