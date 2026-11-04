"""Engineering extraction fixtures, not model reasoning or biological validation.

The actual retained article is unchanged. The tiny caller sequence and scripted
decisions exist only to exercise representation, existing consumers and accounting.
No external provider, native scientific prediction or live workflow is used.
"""
from copy import deepcopy
import asyncio
import hashlib
import json
from pathlib import Path
import re

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.boundary_validation import ModelOutputError, parse_json_object
from gene_annotation_episode.credit import project_credit
from gene_annotation_episode.domain import ContractError, REASONING_SCHEMA, validate_schema
from gene_annotation_episode.export import export_annotation
from gene_annotation_episode.runtime import _action_generation_schema, _decode_action_response, run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController, ScriptedProvider


ARTICLE = Path(__file__).parent / "fixtures/quantitative/PMC2621071.1.xml"
ARTICLE_SHA256 = "f1c4af1d469c9a6f689477fdd22f29115eb07e0bd5b1d51941a865d2de0596d0"


def empty_commit():
    return {key: [] for key in REASONING_SCHEMA["properties"]}


def source_fixture(store):
    raw = ARTICLE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ARTICLE_SHA256
    material = store.register_material(data=raw, name="retained_primary_article_engineering_fixture",
        format="text", use="evidence")
    source = store.get(material["source_ref"])

    def anchor(identifier, element="p"):
        pattern = rb"<" + element.encode() + rb'\b[^>]*\bid="' + identifier.encode() + rb'"[^>]*>.*?</' + element.encode() + rb">"
        found = re.search(pattern, raw, re.DOTALL)
        assert found, identifier
        return {"source_ref": source["id"], "artifact_ref": source["artifact_ref"],
            "start": found.start(), "end": found.end(), "quote": found.group().decode("utf-8")}

    return source, {key: anchor(key) for key in ("P7", "P10", "P20", "P21")}, anchor("F1", "fig")


def quantified_commit(source, anchors, figure):
    """Select explicit historical source quantities, without target attribution."""
    data = empty_commit()
    for alias, label, where in (("nM", "nM", anchors["P7"]),
            ("uM", "μM", anchors["P10"]), ("hours", "hours", anchors["P21"])):
        data["terms"].append({"alias": alias, "label": label, "term_type": "unit",
            "source_ref": source["id"], "anchor": where})
    for alias, label, kind, where in (
            ("glycine", "glycine", "chemical", anchors["P7"]),
            ("serine", "serine", "chemical", anchors["P7"]),
            ("glucose", "glucose", "chemical", figure),
            ("medium", "seawater media", "sample", anchors["P7"]),
            ("glcB_RNA", "glcB", "construct", anchors["P20"]),
            ("gcvT_RNA", "gcvT", "construct", anchors["P20"])):
        data["source_subjects"].append({"alias": alias, "reference_type": kind,
            "source_ref": source["id"], "label": label, "anchor": where})
    data["contexts"] = [
        {"alias": "prepared_medium", "context_type": "processing",
         "name": "filtration and autoclaving", "source_ref": source["id"],
         "anchor": anchors["P7"], "attributes": [], "related_refs": ["@medium"]},
        {"alias": "probing", "context_type": "assay_condition",
         "name": "Structural probing assays", "source_ref": source["id"],
         "anchor": anchors["P21"], "related_refs": ["@glcB_RNA", "@gcvT_RNA"],
         "attributes": [
             {"name": "concentration", "value": {"type": "number", "value": 2,
                 "unit_ref": "@nM", "qualifier": "approximate"}},
             {"name": "time", "value": {"type": "number", "value": 40,
                 "unit_ref": "@hours", "qualifier": "approximate"}}]},
        {"alias": "glucose_addition", "context_type": "growth_condition",
         "name": "glucose", "source_ref": source["id"], "anchor": figure,
         "related_refs": ["@glucose"], "attributes": [
             {"name": "concentration", "value": {"type": "number", "value": 10,
                 "unit_ref": "@uM"}}]}]
    for alias, chemical, value, spread in (("glycine_level", "glycine", 42.4, 1.2),
                                          ("serine_level", "serine", 18.5, 2.4)):
        data["observations"].append({"alias": alias, "kind": "context_measurement",
            "subject_refs": ["@" + chemical], "source_subject_refs": ["@" + chemical, "@medium"],
            "source_ref": source["id"], "anchor": anchors["P7"],
            "dependencies": ["@prepared_medium"], "measurements": [
                {"name": "concentration", "value": {"type": "number", "value": value,
                    "unit_ref": "@nM", "uncertainty": {"representation": "plus_minus",
                        "magnitude": spread, "statistic": "unspecified"}}},
                {"name": "sample_ref", "value": {"type": "reference", "ref": "@medium"}}]})
    for alias, construct, value in (("glcB_Kd", "glcB_RNA", 25), ("gcvT_Kd", "gcvT_RNA", 350)):
        data["observations"].append({"alias": alias, "kind": "assay_report",
            "subject_refs": ["@" + construct], "source_subject_refs": ["@" + construct, "@glycine"],
            "source_ref": source["id"], "anchor": anchors["P10"],
            "dependencies": ["@probing"], "measurements": [
                {"name": "dissociation_constant", "value": {"type": "number", "value": value, "unit_ref": "@uM"}},
                {"name": "relation_ref", "value": {"type": "relation", "roles": [
                    {"role": "source", "ref": "@" + construct}, {"role": "partner", "ref": "@glycine"}]}},
                {"name": "condition_ref", "value": {"type": "reference", "ref": "@probing"}}]})
    return data


def prepared(tmp_path):
    store = Store(tmp_path / "state")
    store.create_problem(raw_sequence="ATGAAATAA", molecule="dna")
    source, anchors, figure = source_fixture(store)
    return store, quantified_commit(source, anchors, figure)


def metric(row, name):
    return next(item["value"] for item in row["measurements"] if item["name"] == name)


def optional_transport_nulls(value):
    value = deepcopy(value)
    def visit(node):
        if isinstance(node, dict):
            if node.get("type") == "number":
                node.setdefault("bound", None)
                node.setdefault("qualifier", None)
                node.setdefault("uncertainty", None)
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)
    visit(value)
    return value


def test_source_quantities_keep_values_units_uncertainty_operands_and_context_through_existing_consumers(tmp_path):
    store, data = prepared(tmp_path)
    with store:
        # This is the actual optional transport normalizer, not a second quantity parser.
        transported = optional_transport_nulls(data)
        decoded = _decode_action_response(transported, store.reasoning_schema())
        assert decoded == data
        result = store.commit_reasoning(decoded, store.validate_scope(None), "source-quantity-fixture")
        assert result["status"] == "completed", result
        refs = result["aliases"]
        glycine = store.get(refs["glycine_level"])
        serine = store.get(refs["serine_level"])
        assert metric(glycine, "concentration") == {"type": "number", "value": 42.4,
            "unit_ref": refs["nM"], "uncertainty": {"representation": "plus_minus", "magnitude": 1.2, "statistic": "unspecified"}}
        assert metric(serine, "concentration")["value"] == 18.5
        assert metric(serine, "concentration")["uncertainty"]["magnitude"] == 2.4
        assert glycine["subject_refs"] == [refs["glycine"]]
        assert serine["subject_refs"] == [refs["serine"]]
        assert glycine["source_subject_refs"] == [refs["glycine"], refs["medium"]]
        assert metric(glycine, "sample_ref")["ref"] == refs["medium"]
        assert glycine["dependencies"] == [refs["prepared_medium"]]
        for alias, construct, value in (("glcB_Kd", "glcB_RNA", 25), ("gcvT_Kd", "gcvT_RNA", 350)):
            observation = store.get(refs[alias])
            assert observation["subject_refs"] == [refs[construct]]
            assert store.get(refs[construct])["reference_type"] == "construct"
            assert metric(observation, "dissociation_constant") == {"type": "number", "value": value, "unit_ref": refs["uM"]}
            assert metric(observation, "relation_ref")["roles"] == [
                {"role": "source", "ref": refs[construct]}, {"role": "partner", "ref": refs["glycine"]}]
            assert metric(observation, "condition_ref")["ref"] == refs["probing"]
            assert observation["dependencies"] == [refs["probing"]]
        probing = store.get(refs["probing"])
        assert probing["attributes"] == [
            {"name": "concentration", "value": {"type": "number", "value": 2, "unit_ref": refs["nM"], "qualifier": "approximate"}},
            {"name": "time", "value": {"type": "number", "value": 40, "unit_ref": refs["hours"], "qualifier": "approximate"}}]
        # No absent qualifier/uncertainty default is materialized for a reported addition.
        assert store.get(refs["glucose_addition"])["attributes"] == [
            {"name": "concentration", "value": {"type": "number", "value": 10, "unit_ref": refs["uM"]}}]
        assert store.commit_reasoning(decoded, store.validate_scope(None), "source-quantity-fixture") == result
        tools = ToolRegistry(store)
        ids = [refs[key] for key in ("glycine_level", "serine_level", "glcB_Kd", "gcvT_Kd")]
        queried = tools.execute("state.query", {"refs": ids})
        assert queried["status"] == "completed"
        assert queried["result"]["records"] == [store.get(ref) for ref in ids]
        view = store.reasoning_view()
        assert {row["id"]: row for row in view["observations"]} == {ref: store.get(ref) for ref in ids}
        output = export_annotation(store, tmp_path / "annotation.json", include_artifacts=True)
        exported = json.loads(Path(output["json"]["path"]).read_text())
        records = {row["id"]: row for row in exported["records"]}
        # Existing export selects scientific inventory and its dependency closure,
        # not every unattached source context. Do not manufacture an observation
        # merely to pull the independent glucose recipe into that closure.
        for alias, reference in refs.items():
            if alias in {"glucose", "glucose_addition"}:
                continue
            assert records[reference] == store.get(reference)
        addition_query = tools.execute("state.query", {"refs": [refs["glucose_addition"]]})
        assert addition_query["result"]["records"] == [store.get(refs["glucose_addition"])]
        # Literal anchors still select the unchanged full article bytes.
        for reference in ids:
            anchor = records[reference]["anchor"]
            raw = store.get_artifact(anchor["artifact_ref"])
            assert raw[anchor["start"]:anchor["end"]] == anchor["quote"].encode()
        assert project_credit(store).credit == 0  # no annotation/assessment was manufactured


def test_scripted_runtime_preserves_numeric_transport_into_child_form_and_parent_query(tmp_path):
    store, data = prepared(tmp_path)
    with store:
        form_schema = {"type": "object", "additionalProperties": False, "required": ["measurement_refs"],
            "properties": {"measurement_refs": {"type": "array", "items": {
                "type": "string", "format": "reference", "x-reference-namespace": "observation"}}}}
        commission = {"selection": {"kind": "child", "goal": "Iteratively improve the fixture's source-quantity account",
            "scope": store.validate_scope(None), "purpose": "Inspect the recorded quantitative evidence and its conditions",
            "schema_json": json.dumps(form_schema), "initial_report_json": json.dumps({"measurement_refs": []})}, "report_update": {}}
        captured = {}
        def child_read(context):
            refs = [row["id"] for row in context["working_state"]["observations"]]
            captured["refs"] = refs
            return {"selection": {"kind": "tool", "tool": "state.query", "arguments": {"refs": refs}},
                "report_update": {"measurement_refs": refs}}
        def parent_read(context):
            form = context["child_reports"][0]
            assert form == {"measurement_refs": captured["refs"]}
            captured["parent_form"] = form
            return {"selection": {"kind": "tool", "tool": "state.query", "arguments": {"refs": form["measurement_refs"]}}, "report_update": {}}
        provider = ScriptedProvider([commission,
            {"selection": {"kind": "reason", "commit": optional_transport_nulls(data)}, "report_update": {"measurement_refs": []}},
            child_read, parent_read])
        result = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider,
            run_dir=tmp_path / "scripted-runtime",
            controller_factory=lambda path, baseline: FixtureController(str(path), baseline, 2)))
        assert result["completed_actions"] == 2 and result["episode_count"] == 2
        assert len(provider.contexts) == 4  # no report composer
        assert len(captured["parent_form"]["measurement_refs"]) == 4
        actions = [json.loads(row[0]) for row in store.db.execute("SELECT result FROM runtime_actions WHERE result IS NOT NULL")]
        returned = [row for row in actions if "result" in row and row["result"] and "records" in row["result"]]
        assert len(returned) == 2
        for outcome in returned:
            assert all(row["measurements"] for row in outcome["result"]["records"])
            assert sorted(metric(row, "dissociation_constant")["value"] for row in outcome["result"]["records"]
                if row["kind"] == "assay_report") == [25, 350]
        counts = store.db.execute("SELECT COUNT(*) FROM runtime_observations GROUP BY episode_id").fetchall()
        assert sorted(row[0] for row in counts) == [2, 2]
        assert result["credit"] == 0


@pytest.mark.parametrize("change", [
    {"magnitude": -1.2}, {"magnitude": "1.2"}, {"magnitude": True},
    {"statistic": "standard_deviation"}, {"statistic": "standard_error"},
    {"statistic": "confidence_interval"}, {"statistic": None},
    {"representation": "range"}, {"extra": "free text"}, {"unit_ref": "@uM"},
])
def test_bad_uncertainty_returns_existing_row_feedback_and_preserves_independent_source_results(tmp_path, change):
    store, data = prepared(tmp_path)
    with store:
        data["observations"][0]["measurements"][0]["value"]["uncertainty"].update(change)
        result = store.commit_reasoning(data, store.validate_scope(None), "malformed-uncertainty")
        assert result["status"] == "partial"
        assert "glycine_level" not in result["aliases"]
        assert "serine_level" in result["aliases"] and "glcB_Kd" in result["aliases"]
        assert result["errors"] == [{"section": "observations", "row_index": 0,
            "code": "representation_error", "field_path": ["measurements", 0, "value"], "schema_keyword": "anyOf"}]
        assert len(store.list("observation")) == 3
        assert store.get(result["aliases"]["serine_level"])["anchor"] == data["observations"][1]["anchor"]


def test_bad_unit_reference_does_not_become_concentration_or_delete_the_source(tmp_path):
    store, data = prepared(tmp_path)
    with store:
        data["observations"][0]["measurements"][0]["value"]["unit_ref"] = "@glycine"
        result = store.commit_reasoning(data, store.validate_scope(None), "chemical-is-not-unit")
        assert result["status"] == "partial"
        assert result["errors"] == [{"section": "observations", "row_index": 0,
            "code": "wrong_reference_type", "reference": result["aliases"]["glycine"],
            "actual_record_type": "reference", "allowed_record_types": ["term"]}]
        assert "glycine_level" not in result["aliases"] and len(store.list("observation")) == 3
        assert hashlib.sha256(store.get_artifact(data["observations"][0]["anchor"]["artifact_ref"])).hexdigest() == ARTICLE_SHA256


def test_scripted_runtime_returns_partial_quantity_feedback_and_reuses_successes_for_changed_next_work(tmp_path):
    store, data = prepared(tmp_path)
    with store:
        data["observations"][0]["measurements"][0]["value"]["uncertainty"]["magnitude"] = -1.2
        captured = {}
        def correct_affected_quantity(context):
            previous = context["last_local_outcome"]
            assert previous["status"] == "partial"
            assert previous["errors"] == [{"section": "observations", "row_index": 0,
                "code": "representation_error", "field_path": ["measurements", 0, "value"], "schema_keyword": "anyOf"}]
            assert len(context["working_state"]["observations"]) == 3
            assert "glycine_level" not in previous["aliases"]
            captured["successful_refs"] = list(previous["record_refs"])
            # This changed fixture response repairs only the affected numeric
            # representation, using the already committed source entities/units.
            def persistent(value):
                if isinstance(value, str) and value.startswith("@"):
                    return previous["aliases"][value[1:]]
                if isinstance(value, list):
                    return [persistent(item) for item in value]
                if isinstance(value, dict):
                    return {key: persistent(item) for key, item in value.items()}
                return value
            corrected = empty_commit()
            corrected["observations"] = [persistent(data["observations"][0])]
            corrected["observations"][0]["measurements"][0]["value"]["uncertainty"]["magnitude"] = 1.2
            return {"selection": {"kind": "reason", "commit": corrected}, "report_update": {}}
        provider = ScriptedProvider([
            {"selection": {"kind": "reason", "commit": optional_transport_nulls(data)}, "report_update": {}},
            correct_affected_quantity])
        result = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider,
            run_dir=tmp_path / "scripted-partial-runtime",
            controller_factory=lambda path, baseline: FixtureController(str(path), baseline, 2)))
        assert result["completed_actions"] == 2 and result["episode_count"] == 1
        assert store.db.execute("SELECT COUNT(*) FROM runtime_observations").fetchone()[0] == 2
        assert len(store.list("observation")) == 4
        assert all(store.get(ref) for ref in captured["successful_refs"])
        assert result["credit"] == 0


def test_existing_unit_term_check_does_not_accept_a_chemical_term_as_a_unit(tmp_path):
    store, data = prepared(tmp_path)
    with store:
        data["terms"].append({**data["terms"][0], "alias": "chemical_term", "label": "glycine", "term_type": "chemical"})
        data["observations"][0]["measurements"][0]["value"]["unit_ref"] = "@chemical_term"
        result = store.commit_reasoning(data, store.validate_scope(None), "chemical-term-is-not-unit")
        assert result["status"] == "partial"
        assert result["errors"] == [{"section": "observations", "row_index": 0,
            "code": "measurement_unit_reference_required"}]
        assert len(store.list("observation")) == 3


@pytest.mark.parametrize("qualifier", ["exact", "estimated", "unknown", 1])
def test_undeclared_precision_is_not_invented_or_admitted(qualifier):
    with pytest.raises(ContractError):
        validate_schema({"type": "number", "value": 2, "unit_ref": None, "qualifier": qualifier},
            REASONING_SCHEMA["properties"]["observations"]["items"]["properties"]["measurements"]["items"]["properties"]["value"])


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity", "1e9999"])
def test_nonfinite_uncertainty_cannot_cross_existing_json_boundary(token):
    with pytest.raises(ModelOutputError):
        parse_json_object('{"uncertainty":{"representation":"plus_minus","magnitude":' + token + ',"statistic":"unspecified"}}')


def test_shared_schema_optional_transport_contract_exposes_only_declared_numeric_meanings():
    schema = _action_generation_schema(REASONING_SCHEMA)
    number = schema["properties"]["observations"]["items"]["properties"]["measurements"]["items"]["properties"]["value"]["anyOf"][0]
    assert set(number["required"]) == {"type", "value", "unit_ref", "bound", "qualifier", "uncertainty"}
    assert number["properties"]["qualifier"]["anyOf"][0]["enum"] == ["approximate"]
    uncertainty = number["properties"]["uncertainty"]["anyOf"][0]
    assert uncertainty["additionalProperties"] is False
    assert set(uncertainty["required"]) == {"representation", "magnitude", "statistic"}
    assert uncertainty["properties"]["statistic"]["enum"] == ["unspecified"]
    assert uncertainty["properties"]["magnitude"]["minimum"] == 0
    assert "enclosing unit" in uncertainty["description"]
    legacy = {"type": "number", "value": 30, "unit_ref": None}
    numeric_host = REASONING_SCHEMA["properties"]["contexts"]["items"]["properties"]["attributes"]["items"]["properties"]["value"]
    assert Draft202012Validator(numeric_host).is_valid(legacy)
    assert _decode_action_response({**legacy, "bound": None, "qualifier": None, "uncertainty": None}, numeric_host) == legacy
    zero = {**legacy, "uncertainty": {"representation": "plus_minus", "magnitude": 0, "statistic": "unspecified"}}
    assert Draft202012Validator(numeric_host).is_valid(zero)
