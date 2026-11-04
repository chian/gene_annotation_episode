"""Synthetic custody, selected authority, saved replay and typed context rows."""
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from gene_annotation_episode.communication import validate_closed_schema
from gene_annotation_episode.domain import ContractError, obj, validate_schema
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.literature_context_storage import (
    BINDINGS, COMPONENTS, PROVIDER, LiteratureContextRepository,
    context_cells_schema, context_population_schema,
)
from gene_annotation_episode.state import Store


def source(store, text, *, parents=(), alias=False):
    artifact = store.artifact(text)
    return store.put("source", {"provider": "synthetic_context_fixture", "accession": None,
        "uri": None, "artifact_ref": artifact, "text_ref": artifact if alias else None,
        "request_ref": None, "version": None, "retrieved_at": None,
        "parent_source_refs": list(parents)}, origin="caller")


def dataset(*, sampling=True):
    inputs = {"question_kind": "sample_context_coverage", "origin": "synthetic",
        "scope_status": "defined", "frame_status": "defined", "pairing": "paired",
        "weight_basis": "equal_units",
        "sampling_design": "independent_equal_weight" if sampling else "census",
        "alpha": .05 if sampling else None, "permitted_remainder": True,
        "requirements": [{"key": "access", "unit": "state", "supported": [], "incompatible": []}],
        "routes": [{"key": "route", "requirements": ["access"],
            "requirements_complete": True, "joint_support": "established"}],
        "contexts": [], "marginals": []}
    for i in range(4):
        inputs["contexts"].append({"key": f"unit{i}", "weight": 1, "cluster_key": f"cluster{i}",
            "scope_match": "matched", "observations": [{"requirement_key": "access",
                "measurement_key": f"measure{i}", "unit": "state", "interval": None,
                "relation": "supported" if i < 2 else "incompatible",
                "reported_sd": None, "reported_sem": None, "reported_plusminus": None,
                "reported_count": 3, "count_relation": "exact", "replicate_kind": "technical"}]})
    return {"version": "a108_source_context_measurements_v1", "inputs": inputs}


def fixture(path, *, page=False, data=True):
    store = Store(path)
    store.create_problem(raw_sequence="ATGGCT", molecule="dna")
    provenance = source(store, "Synthetic retained source provenance.")
    root = source(store, "Synthetic context experiment.", parents=[provenance["id"]])
    data_row = source(store, json.dumps(dataset()), parents=[root["id"]])
    text = "Molecule|Organism|Strain|Experiment|Function|Biological context|Sample frame|Endpoint|Condition"
    literal = source(store, text, parents=[root["id"]], alias=True)
    interpretation = source(store, "Synthetic interpretation of the organism and sample scope.", parents=[root["id"]])
    literals, offset = {}, 0
    for field, quote in zip((literal for literal, _ in BINDINGS.values()), text.split("|")):
        literals[field] = {"source_ref": literal["id"], "representation": "original",
            "start": offset, "end": offset + len(quote), "quote": quote}
        offset += len(quote) + 1
    quote = store.get_artifact(interpretation["artifact_ref"]).decode()
    args = {"source_ref": root["id"], "data_source_ref": data_row["id"] if data else None,
        "source_kind": "synthetic_fixture", "literals": literals,
        "interpretation_witnesses": [{"source_ref": interpretation["id"], "representation": "original",
            "start": 0, "end": len(quote), "quote": quote}]}
    received = [root["id"], literal["id"], interpretation["id"]]
    if data:
        received.append(data_row["id"])
    context = BindingContext("synthetic-context-run", "context-child", "literature",
        (("literature", "fixture"),), store.validate_scope(),
        {"page": {"source_ref": root["id"]}} if page else {}, {}, tuple(received))
    return store, context, args, {"root": root, "data": data_row, "literal": literal,
        "interpretation": interpretation, "provenance": provenance}


def test_selected_population_and_closed_scientific_rows(tmp_path):
    store, context, args, records = fixture(tmp_path, page=True)
    with store:
        repo = LiteratureContextRepository(store, context.run_id)
        validate_schema(args, context_population_schema())
        outcome = repo.populate(context, args, "selected")
        ref = outcome["result"]["sheet_ref"]
        saved = repo.read(ref)
        assert store.get(ref)["provider"] == PROVIDER
        assert saved["version"] == "literature_context_record_v1"
        assert saved["direct_input_source_refs"] == [records[key]["id"] for key in (
            "root", "data", "literal", "interpretation")]
        assert records["provenance"]["id"] in saved["input_source_refs"]
        assert saved["sheet"]["inputs"] == saved["extraction"]["calculation_inputs"]
        assert saved["sheet"]["cells"]["selected_point"]["value"] == .5
        rows = repo.project_cells([ref, ref], permitted_record_refs=outcome["record_refs"],
            components=("selected_point", "sampling_lower"))
        assert [row["component"] for row in rows] == ["selected_point", "sampling_lower"]
        for row in rows:
            assert row["context_units"] == row["distinct_known_clusters"] == row["actual_sampling_n"] == 4
            assert row["alpha"] == .05 and row["sampling_design"] == "independent_equal_weight"
            assert row["requirement_count"] == row["route_count"] == 1
            assert row["requirement_definitions"] == [{"unit": "state", "supported": [], "incompatible": []}]
            assert row["route_definitions"] == [{"requirements": [0],
                "requirements_complete": True, "joint_support": "established"}]
            assert row["question_kind"] == "sample_context_coverage"
            assert row["native_unit_bases"] == ["state"]
            assert row["operand_origin"] == "synthetic"
            assert row["bound_kind"] == "logical_domain_not_confidence_interval"
            assert row["measurement_corrections"] == "not_applied"
            assert row["target_correspondence"] == "not_evaluated"
            assert "formula" not in row and "inputs" not in row and "witness" not in row
        assert rows[1]["conditional_on"]
        assert set(outcome["changed_record_refs"]) == {ref, *saved["experimental_bindings"].values()}
        for field, (literal, _) in BINDINGS.items():
            binding = store.get(saved["experimental_bindings"][field])
            selected = saved["extraction"]["literals"][literal]
            assert binding.get("label", binding.get("name")) == selected["value"]
            assert binding["anchor"]["artifact_ref"] == selected["witness"]["artifact_ref"]
            assert binding["anchor"]["quote"] == selected["value"]
        validate_closed_schema(obj({"cells": context_cells_schema()}))
        validate_schema(rows, context_cells_schema())
        assert not store.list("observation") and not store.list("assessment")


def test_no_dataset_preserves_unknown_question_and_physical_bounds(tmp_path):
    store, context, args, _ = fixture(tmp_path, data=False)
    with store:
        repo = LiteratureContextRepository(store, context.run_id)
        outcome = repo.populate(context, args, "missing")
        saved = repo.read(outcome["result"]["sheet_ref"])
        assert saved["extraction"]["calculation_inputs"] is None
        cells = saved["sheet"]["cells"]
        assert cells["selected_lower"]["value"] == 0 and cells["selected_upper"]["value"] == 1
        assert cells["selected_point"]["value"] is None
        assert cells["capability_point"]["value"] is None
        rows = repo.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=outcome["record_refs"])
        assert all(row["question_kind"] == "unreported" and row["scope_status"] == "unreported"
            and row["frame_status"] == "unreported" and row["context_units"] == 0
            and row["actual_sampling_n"] is None for row in rows)
        assert all(row["assayed_subject_ref"] is not None for row in rows)


@pytest.mark.parametrize("part", ["root", "data", "literal", "interpretation"])
def test_each_direct_source_requires_receipt_initial_and_replay(tmp_path, part):
    store, context, args, records = fixture(tmp_path)
    with store:
        repo = LiteratureContextRepository(store, context.run_id)
        repo.populate(context, args, "selected")
        denied = replace(context, received_record_refs=tuple(ref for ref in context.received_record_refs
            if ref != records[part]["id"]))
        before = store.list("source")
        for key in ("new", "selected"):
            with pytest.raises(ContractError, match="not_received"):
                repo.populate(denied, args, key)
        assert store.list("source") == before
        assert store.db.execute("select count(*) from literature_context_operations").fetchone()[0] == 1


@pytest.mark.parametrize("part", ["root", "data", "literal", "interpretation", "provenance"])
def test_scope_covers_direct_inputs_and_provenance(tmp_path, monkeypatch, part):
    store, context, args, records = fixture(tmp_path)
    with store:
        repo = LiteratureContextRepository(store, context.run_id)
        repo.populate(context, args, "selected")
        subset = store.reference_subset
        monkeypatch.setattr(store, "reference_subset", lambda refs, scope:
            [] if records[part]["id"] in refs else subset(refs, scope))
        for key in ("new", "selected"):
            with pytest.raises(ContractError, match="outside_scope"):
                repo.populate(context, args, key)


def test_transitive_provenance_is_retained_and_scoped_on_replay(tmp_path, monkeypatch):
    store, context, args, records = fixture(tmp_path)
    with store:
        intermediate = source(store, "Synthetic intermediate provenance.", parents=[records["root"]["id"]])
        data = source(store, json.dumps(dataset()), parents=[intermediate["id"]])
        args["data_source_ref"] = data["id"]
        # Neither the intermediate nor its ancestor provenance needs a receipt
        # for byte reading: both are provenance-only records.
        context = replace(context, received_record_refs=(*context.received_record_refs, data["id"]))
        repo = LiteratureContextRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        saved = repo.read(outcome["result"]["sheet_ref"])
        assert intermediate["id"] in saved["input_source_refs"]
        assert records["provenance"]["id"] in saved["input_source_refs"]
        assert intermediate["id"] not in saved["direct_input_source_refs"]
        subset = store.reference_subset
        monkeypatch.setattr(store, "reference_subset", lambda refs, scope:
            [] if intermediate["id"] in refs else subset(refs, scope))
        for key in ("new", "selected"):
            with pytest.raises(ContractError, match="outside_scope"):
                repo.populate(context, args, key)


@pytest.mark.parametrize("part", ["root", "data", "literal", "interpretation"])
def test_each_direct_input_requires_assigned_page_lineage(tmp_path, part):
    store, context, args, records = fixture(tmp_path, page=True)
    with store:
        row = source(store, store.get_artifact(records[part]["artifact_ref"]))
        if part == "literal":
            for witness in args["literals"].values():
                witness["source_ref"] = row["id"]
        elif part == "interpretation":
            args["interpretation_witnesses"][0]["source_ref"] = row["id"]
        else:
            args["source_ref" if part == "root" else "data_source_ref"] = row["id"]
        context = replace(context, received_record_refs=(*context.received_record_refs, row["id"]))
        with pytest.raises(ContractError, match="outside_assigned_source"):
            LiteratureContextRepository(store, context.run_id).populate(context, args, "bad")


@pytest.mark.parametrize("data", [True, False])
def test_saved_only_reopen_disables_reader_calculator_and_original_bytes(tmp_path, monkeypatch, data):
    store, context, args, records = fixture(tmp_path, data=data)
    with store:
        repo = LiteratureContextRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        ref = outcome["result"]["sheet_ref"]
        saved = repo.read(ref)
        rows = repo.project_cells([ref], permitted_record_refs=outcome["record_refs"])
        forbidden_artifacts = {record["artifact_ref"] for record in records.values()}
    def forbidden(*_args, **_kwargs):
        raise AssertionError("saved replay attempted scientific source work")
    monkeypatch.setattr("gene_annotation_episode.literature_context_storage.read_context_inputs", forbidden)
    monkeypatch.setattr("gene_annotation_episode.literature_context_storage.populate_context_compatibility", forbidden)
    monkeypatch.setattr("gene_annotation_episode.literature_context_storage.empty_context_inputs", forbidden)
    with Store(tmp_path) as reopened:
        repo = LiteratureContextRepository(reopened, context.run_id)
        read = reopened.get_artifact
        def saved_only(ref):
            assert ref not in forbidden_artifacts
            return read(ref)
        monkeypatch.setattr(reopened, "get_artifact", saved_only)
        reopened.db.execute("pragma query_only=ON")
        # Import canonically stored args to test ordering independent of input dict insertion.
        reordered = json.loads(json.dumps(args, sort_keys=True))
        assert repo.populate(context, reordered, "selected") == outcome
        assert repo.read(ref) == saved
        assert repo.project_cells([ref], permitted_record_refs=outcome["record_refs"]) == rows


def test_publication_rolls_back_bindings_and_operation(tmp_path, monkeypatch):
    store, context, args, _ = fixture(tmp_path)
    with store:
        repo = LiteratureContextRepository(store, context.run_id)
        kinds = ("source", "reference", "term", "context")
        before = [store.list(kind) for kind in kinds]
        put = store.put
        def fail(kind, record, **kwargs):
            if kind == "source" and record["provider"] == PROVIDER:
                raise RuntimeError("synthetic publication interruption")
            return put(kind, record, **kwargs)
        monkeypatch.setattr(store, "put", fail)
        with pytest.raises(RuntimeError, match="publication interruption"):
            repo.populate(context, args, "atomic")
        assert [store.list(kind) for kind in kinds] == before
        assert store.db.execute("select count(*) from literature_context_operations").fetchone()[0] == 0
        monkeypatch.setattr(store, "put", put)
        assert repo.populate(context, args, "atomic")["status"] == "completed"


def test_selected_authority_run_and_immutable_operation_identity(tmp_path):
    store, context, args, _ = fixture(tmp_path)
    with store:
        repo = LiteratureContextRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        ref = outcome["result"]["sheet_ref"]
        actual = store.get(ref)
        record = {key: value for key, value in actual.items() if key not in ("id", "record_type", "origin")}
        caller_copy = store.put("source", record, origin="caller")
        with pytest.raises(ContractError, match="sheet_required"):
            repo.read(caller_copy["id"])
        record["retrieved_at"] = "2026-01-01T00:00:00Z"
        tool_copy = store.put("source", record, origin="tool")
        with pytest.raises(ContractError, match="not_selected_output"):
            repo.read(tool_copy["id"])
        with pytest.raises(ContractError, match="sheet_run_mismatch"):
            LiteratureContextRepository(store, "different-run").read(ref)
        with pytest.raises(ContractError, match="reused_for_different_work"):
            repo.populate(context, {**args, "source_kind": "retained_extraction"}, "selected")
        with pytest.raises(ContractError, match="run_mismatch"):
            repo.populate(replace(context, run_id="different-run"), args, "new")
        with pytest.raises(ContractError, match="operation_key_required"):
            repo.populate(context, args, "")
        second = repo.populate(context, args, "second")
        assert second["changed_record_refs"] == [second["result"]["sheet_ref"]]
        outcome["result"]["cells"]["selected_point"]["value"] = 999
        assert repo.populate(context, args, "selected")["result"]["cells"]["selected_point"]["value"] == .5




@pytest.mark.parametrize("field,value", [
    ("value", .2), ("formula_code", "context_coverage_lower_v1"),
    ("assayed_subject_ref", None), ("organism_ref", None), ("strain_ref", None),
    ("experiment_ref", None), ("function_ref", None), ("biological_context_ref", None),
    ("sample_frame_ref", None), ("endpoint_ref", None), ("condition_ref", None),
    ("data_source_ref", None), ("question_kind", "organism_capability"),
    ("operand_origin", "reported"), ("scope_status", "unreported"),
    ("frame_status", "unreported"), ("pairing", "unknown"),
    ("weight_basis", "measured_volume"), ("sampling_design", "census"),
    ("alpha", .1), ("permitted_remainder", False), ("context_units", 3),
    ("distinct_known_clusters", 3), ("actual_sampling_n", 3),
    ("requirement_count", 2), ("route_count", 2), ("native_unit_bases", []),
    ("conditional_on", []), ("qualifications", ["scope_unreported"]),
    ("requirement_definitions", [{"unit": "mM", "supported": [{"lower": 0, "upper": 1,
        "lower_closed": True, "upper_closed": True}], "incompatible": []}]),
    ("route_definitions", [{"requirements": [], "requirements_complete": True,
        "joint_support": "unresolved"}]),
])
def test_forged_numbers_bindings_and_model_meanings_rejected(tmp_path, field, value):
    store, context, args, _ = fixture(tmp_path)
    with store:
        repo = LiteratureContextRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        rows = repo.project_cells([outcome["result"]["sheet_ref"]],
            permitted_record_refs=outcome["record_refs"], components=("sampling_upper",))
        assert rows[0][field] != value
        rows[0][field] = value
        with pytest.raises(ContractError, match="differs_from_saved"):
            repo.validate_returned_values(rows, permitted_record_refs=outcome["record_refs"])


def test_exact_admitted_subset_forwarding_and_duplicate_rejection(tmp_path):
    store, context, args, _ = fixture(tmp_path)
    with store:
        repo = LiteratureContextRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        ref = outcome["result"]["sheet_ref"]
        rows = repo.project_cells([ref], permitted_record_refs=outcome["record_refs"], components=("selected_point",))
        parent = replace(context, episode_id="parent", received_record_refs=tuple(outcome["record_refs"]))
        repo.receive_cells(parent, rows, "delivery")
        repo.receive_cells(parent, rows, "delivery")
        assert repo.received_cells(parent) == rows and len(COMPONENTS) == 15
        with pytest.raises(ContractError, match="differs_from_saved"):
            repo.validate_cells(rows, sheet_refs=[ref], permitted_record_refs=outcome["record_refs"])
        with pytest.raises(ContractError, match="duplicate_literature"):
            repo.validate_returned_values(rows * 2, permitted_record_refs=outcome["record_refs"])
        with pytest.raises(ContractError, match="delivery_identity_conflict"):
            repo.receive_cells(parent, [], "delivery")
        with pytest.raises(ContractError, match="not_received"):
            repo.project_cells([ref], permitted_record_refs=())
        for components in (("unknown",), ({},), (COMPONENTS[0], COMPONENTS[0])):
            with pytest.raises(ContractError, match="component_selection_invalid"):
                repo.project_cells([ref], permitted_record_refs=outcome["record_refs"], components=components)
        grandparent = replace(context, episode_id="grandparent")
        repo.receive_cells(grandparent, repo.received_cells(parent), "forward")
        assert repo.received_cells(grandparent) == rows
        assert not store.list("observation") and not store.list("assessment")


def test_closed_schema_rejects_free_text_and_nonfinite_fields(tmp_path):
    store, context, args, _ = fixture(tmp_path)
    with store:
        repo = LiteratureContextRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        rows = repo.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=outcome["record_refs"])
        for field, value in (("formula_code", "my formula"), ("unavailable_reason", "arbitrary prose"),
                ("conditional_on", ["arbitrary assumption"]), ("value", float("nan")),
                ("alpha", float("inf")), ("alpha", 1), ("actual_sampling_n", True),
                ("context_units", -1), ("question_kind", "probably okay"),
                ("qualifications", ["plain prose"]), ("native_unit_bases", ["percent"]),
                ("requirement_definitions", [{"unit": "state", "supported": [], "incompatible": [],
                    "explanation": "free prose"}]),
                ("route_definitions", [{"requirements": [0], "requirements_complete": True,
                    "joint_support": "probably"}]),
                ("bound_kind", "95% confidence interval"), ("formula", "raw formula")):
            changed = deepcopy(rows)
            changed[0][field] = value
            with pytest.raises(ContractError, match="representation_error"):
                repo.validate_returned_values(changed, permitted_record_refs=outcome["record_refs"])
        changed_args = deepcopy(args)
        changed_args["numerical_operands"] = {"value": .7}
        with pytest.raises(ContractError, match="representation_error"):
            repo.populate(context, changed_args, "invalid_arguments")


def test_invalid_dataset_cannot_publish_bindings(tmp_path):
    store, context, args, records = fixture(tmp_path)
    with store:
        invalid = dataset()
        duplicate = deepcopy(invalid["inputs"]["contexts"][0])
        duplicate["weight"] = 2
        invalid["inputs"]["contexts"].append(duplicate)
        row = source(store, json.dumps(invalid), parents=[records["root"]["id"]])
        args["data_source_ref"] = row["id"]
        context = replace(context, received_record_refs=(*context.received_record_refs, row["id"]))
        repo = LiteratureContextRepository(store, context.run_id)
        kinds = ("source", "reference", "term", "context")
        before = [store.list(kind) for kind in kinds]
        with pytest.raises(ValueError):
            repo.populate(context, args, "invalid")
        assert [store.list(kind) for kind in kinds] == before
        assert store.db.execute("select count(*) from literature_context_operations").fetchone()[0] == 0


def test_missing_bindings_field_meaning_and_span_identity(tmp_path):
    store, context, args, records = fixture(tmp_path)
    with store:
        args["literals"]["condition"] = None
        args["literals"]["strain"] = deepcopy(args["literals"]["molecule"])
        repo = LiteratureContextRepository(store, context.run_id)
        first = repo.populate(context, args, "first")
        saved = repo.read(first["result"]["sheet_ref"])
        assert saved["experimental_bindings"]["condition_ref"] is None
        assert saved["experimental_bindings"]["strain_ref"] != saved["experimental_bindings"]["assayed_subject_ref"]
        row = source(store, "Molecule|Molecule", parents=[records["root"]["id"]])
        context = replace(context, received_record_refs=(*context.received_record_refs, row["id"]))
        args["literals"]["molecule"].update(source_ref=row["id"], start=0, end=8)
        second = repo.populate(context, args, "second")
        args["literals"]["molecule"].update(start=9, end=17)
        third = repo.populate(context, args, "third")
        assert repo.read(second["result"]["sheet_ref"])["experimental_bindings"]["assayed_subject_ref"] != repo.read(third["result"]["sheet_ref"])["experimental_bindings"]["assayed_subject_ref"]


def test_same_anchor_keeps_nine_distinct_scientific_meanings(tmp_path):
    store, context, args, _ = fixture(tmp_path, data=False)
    with store:
        witness = args["literals"]["molecule"]
        args["literals"] = {field: deepcopy(witness) for field in args["literals"]}
        repo = LiteratureContextRepository(store, context.run_id)
        outcome = repo.populate(context, args, "same-span")
        bindings = repo.read(outcome["result"]["sheet_ref"])["experimental_bindings"]
        assert len(set(bindings.values())) == 9


def test_metadata_copies_actual_deduplicated_units_and_census_sampling(tmp_path):
    store, context, args, records = fixture(tmp_path)
    with store:
        data = dataset(sampling=False)
        data["inputs"]["contexts"].append(deepcopy(data["inputs"]["contexts"][0]))
        row = source(store, json.dumps(data), parents=[records["root"]["id"]])
        args["data_source_ref"] = row["id"]
        context = replace(context, received_record_refs=(*context.received_record_refs, row["id"]))
        repo = LiteratureContextRepository(store, context.run_id)
        outcome = repo.populate(context, args, "census-duplicate")
        saved = repo.read(outcome["result"]["sheet_ref"])
        assert len(saved["extraction"]["observations"]["inputs"]["contexts"]) == 5
        assert len(saved["sheet"]["inputs"]["contexts"]) == 4
        rows = repo.project_cells([outcome["result"]["sheet_ref"]],
            permitted_record_refs=outcome["record_refs"], components=("selected_point", "sampling_lower"))
        assert rows[0]["value"] == .5 and rows[1]["value"] is None
        for row in rows:
            assert row["context_units"] == row["distinct_known_clusters"] == 4
            assert row["actual_sampling_n"] is None and row["alpha"] is None
            assert row["sampling_design"] == "census"
