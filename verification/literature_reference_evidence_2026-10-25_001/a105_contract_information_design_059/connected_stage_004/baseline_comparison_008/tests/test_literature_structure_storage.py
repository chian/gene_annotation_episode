"""Synthetic CIF/XML selected storage checks; no paper or network work."""
from copy import deepcopy
from dataclasses import replace

import pytest

from gene_annotation_episode.communication import validate_closed_schema
from gene_annotation_episode.domain import ContractError, obj, validate_schema
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.literature_structure_storage import (
    BINDINGS, COMPONENTS, PROVIDER, LiteratureStructureRepository,
    structure_cells_schema, structure_population_schema,
)
from gene_annotation_episode.state import Store


def source(store, text, *, parents=(), provider="synthetic_structure_fixture", alias=False):
    artifact = store.artifact(text)
    return store.put("source", {"provider": provider, "accession": None, "uri": None,
        "artifact_ref": artifact, "text_ref": artifact if alias else None,
        "request_ref": None, "version": None, "retrieved_at": None,
        "parent_source_refs": list(parents)}, origin="caller")


def cif():
    fields = ("group_PDB", "id", "auth_atom_id", "auth_comp_id", "auth_asym_id", "auth_seq_id",
        "label_alt_id", "pdbx_PDB_ins_code", "Cartn_x", "Cartn_y", "Cartn_z",
        "occupancy", "B_iso_or_equiv", "pdbx_PDB_model_num")
    return ("data_synthetic\n_entry.id 1ABC\n_exptl.method 'X-RAY DIFFRACTION'\n"
        "_pdbx_audit_revision_history.ordinal 2\n"
        "_pdbx_audit_revision_history.revision_date 2026-01-02\nloop_\n"
        + "\n".join("_atom_site." + field for field in fields) + "\n"
        "ATOM 1 OE1 GLU A 1 . ? 0 0 0 0.5 20 1\n"
        "ATOM 2 OE2 GLU A 1 . ? 0 1 0 0.5 21 1\n"
        "HETATM 3 N1 LIG B 2 . ? 3 0 0 1 12 1\n")


def xml(*, entry="1ABC", revision="2", rscc="0.8"):
    return ('<wwPDB-validation-information><Entry pdbid="' + entry + '" '
        'PDB-revision-number="' + revision + '" PDB-revision-date="2026-01-02" '
        'XMLcreationDate="2026-01-03"/><ModelledSubgroup model="1" chain="A" '
        'resnum="1" icode=" " altcode=" " resname="GLU" rscc="' + rscc + '"/>'
        '<ModelledSubgroup model="1" chain="B" resnum="2" icode=" " altcode=" " '
        'resname="LIG" rscc="0.9"/></wwPDB-validation-information>')


def selector(chain="A", residue="1", comp="GLU"):
    return {"auth_chain": chain, "auth_seq_id": residue, "comp_id": comp,
        "insertion_code": "", "alt_id": "."}


def fixture(path, *, page=False, validation=True, mismatch=False):
    store = Store(path)
    store.create_problem(raw_sequence="ATGGCT", molecule="dna")
    provenance = source(store, "Synthetic provenance, never directly read.")
    root = source(store, "Synthetic structural experiment.", parents=[provenance["id"]])
    coordinates = source(store, cif(), parents=[root["id"]])
    validation_row = source(store, xml(entry="2ABC" if mismatch else "1ABC"), parents=[root["id"]])
    text = "Molecule|Construct|System|Condition|Partner|Experiment"
    literal = source(store, text, parents=[root["id"]], alias=True)
    literals, offset = {}, 0
    for field, quote in zip(("molecule", "construct", "experimental_system", "condition", "partner", "experiment"), text.split("|")):
        literals[field] = {"source_ref": literal["id"], "representation": "original",
            "start": offset, "end": offset + len(quote), "quote": quote}
        offset += len(quote) + 1
    args = {"source_ref": root["id"], "coordinate_source_ref": coordinates["id"],
        "validation_source_ref": validation_row["id"] if validation else None,
        "source_kind": "synthetic_fixture", "model_number": 1, "literals": literals,
        "geometry_panel": [{"endpoint_a": {**selector(), "atom_names": ["OE1", "OE2"]},
            "endpoint_b": {**selector("B", "2", "LIG"), "atom_names": ["N1"]},
            "positive_max_A": 3.5, "incompatible_min_A": 4.5}],
        "local_panel": [selector(), selector("B", "2", "LIG")],
        "evaluation_scope": "conditional_deposited_model_geometry"}
    records = {"root": root, "coordinate": coordinates, "validation": validation_row,
        "literal": literal, "provenance": provenance}
    received = [root["id"], coordinates["id"], literal["id"]]
    if validation:
        received.append(validation_row["id"])
    context = BindingContext("synthetic-structure-run", "structure-child", "literature",
        (("literature", "fixture"),), store.validate_scope(),
        {"page": {"source_ref": root["id"]}} if page else {}, {}, tuple(received))
    return store, context, args, records


def test_selected_real_reader_calculator_and_closed_typed_rows(tmp_path):
    store, context, args, records = fixture(tmp_path, page=True)
    with store:
        repo = LiteratureStructureRepository(store, context.run_id)
        validate_schema(args, structure_population_schema())
        outcome = repo.populate(context, args, "selected")
        ref = outcome["result"]["sheet_ref"]
        saved = repo.read(ref)
        assert store.get(ref)["provider"] == PROVIDER
        assert saved["version"] == "literature_structure_record_v1"
        assert set(saved["direct_input_source_refs"]) == set(context.received_record_refs)
        assert records["provenance"]["id"] in saved["input_source_refs"]
        assert records["provenance"]["id"] not in saved["direct_input_source_refs"]
        assert saved["extraction"]["native_geometry"][0]["endpoint_a"]["selected_atom_rows"][0]["occupancy_parameter"] == 0.5
        assert saved["sheet"]["native_geometry"][0]["distance_A"] == 3
        assert saved["sheet"]["cells"]["source_geometry_positive"]["value"] == pytest.approx(.64)
        assert outcome["result"]["assay_interpretation"] == saved["extraction"]["literals"]
        rows = repo.project_cells([ref, ref], permitted_record_refs=outcome["record_refs"],
            components=("source_geometry_signed", "local_fit_index"))
        assert [row["component"] for row in rows] == ["source_geometry_signed", "local_fit_index"]
        assert all(row["validation_binding"] == "matching_entry_revision" for row in rows)
        assert all(row["origin"] == "proposed" and row["unconditional_uncertainty"] == "unreported" for row in rows)
        assert all(row["bound_kind"] == "conditional_arithmetic_outer" for row in rows)
        for result in [outcome["result"], *rows]:
            assert result["model_number"] == args["model_number"]
            assert result["geometry_definition"] == args["geometry_panel"]
            assert result["local_validation_definition"] == args["local_panel"]
            assert result["local_validation_granularity"] == "residue"
            assert result["transform_basis"] == "identity_coordinates_only"
        assert set(outcome["changed_record_refs"]) == {ref, *saved["experimental_bindings"].values()}
        for field, item in saved["extraction"]["literals"].items():
            binding_field = next(name for name, (literal, _) in BINDINGS.items() if literal == field)
            bound = store.get(saved["experimental_bindings"][binding_field])
            assert bound.get("label", bound.get("name")) == item["value"]
            assert bound["anchor"]["artifact_ref"] == item["witness"]["artifact_ref"]
            assert bound["anchor"]["quote"] == item["value"]
        assert "native_geometry" not in rows[0] and "witness" not in rows[0]
        validate_closed_schema(obj({"cells": structure_cells_schema()}))
        validate_schema(rows, structure_cells_schema())
        assert not store.list("observation") and not store.list("assessment")


@pytest.mark.parametrize("change,reason", [("no_validation", "validation_not_joined"),
    ("mismatch", "validation_not_joined"), ("missing_rscc", "local_rscc_unreported"),
    ("missing_endpoint", "geometry_inputs_unreported")])
def test_partial_scientific_inputs_preserve_unknowns(tmp_path, change, reason):
    store, context, args, records = fixture(tmp_path, validation=change != "no_validation", mismatch=change == "mismatch")
    with store:
        if change == "missing_rscc":
            row = source(store, xml(rscc="?"), parents=[records["root"]["id"]])
            args["validation_source_ref"] = row["id"]
            context = replace(context, received_record_refs=(*context.received_record_refs, row["id"]))
        elif change == "missing_endpoint":
            args["geometry_panel"][0]["endpoint_b"]["atom_names"] = ["ABSENT"]
        repo = LiteratureStructureRepository(store, context.run_id)
        outcome = repo.populate(context, args, "partial")
        saved = repo.read(outcome["result"]["sheet_ref"])
        name = "geometry_support_fraction" if change == "missing_endpoint" else "local_fit_index"
        assert saved["sheet"]["cells"][name]["value"] is None
        assert saved["sheet"]["cells"][name]["unavailable_reason"] == reason
        if change != "missing_endpoint":
            assert saved["sheet"]["native_geometry"][0]["distance_A"] == 3
        if change == "mismatch":
            assert saved["extraction"]["native_local"][0]["rscc"] == .8
        if change == "no_validation":
            assert saved["extraction"]["native_local"][0]["rscc"] is None


@pytest.mark.parametrize("part", ["root", "coordinate", "validation", "literal"])
def test_every_direct_source_requires_receipt_on_new_work_and_replay(tmp_path, part):
    store, context, args, records = fixture(tmp_path)
    with store:
        repo = LiteratureStructureRepository(store, context.run_id)
        repo.populate(context, args, "selected")
        denied = replace(context, received_record_refs=tuple(ref for ref in context.received_record_refs if ref != records[part]["id"]))
        before = store.list("source")
        for key in ("new", "selected"):
            with pytest.raises(ContractError, match="not_received"):
                repo.populate(denied, args, key)
        assert store.list("source") == before
        assert store.db.execute("select count(*) from literature_structure_operations").fetchone()[0] == 1


@pytest.mark.parametrize("part", ["root", "coordinate", "validation", "literal", "provenance"])
def test_scope_covers_direct_and_provenance_on_initial_work_and_replay(tmp_path, monkeypatch, part):
    store, context, args, records = fixture(tmp_path)
    with store:
        repo = LiteratureStructureRepository(store, context.run_id)
        repo.populate(context, args, "selected")
        subset = store.reference_subset
        monkeypatch.setattr(store, "reference_subset", lambda refs, scope:
            [] if records[part]["id"] in refs else subset(refs, scope))
        for key in ("new", "selected"):
            with pytest.raises(ContractError, match="outside_scope"):
                repo.populate(context, args, key)


@pytest.mark.parametrize("part", ["root", "coordinate", "validation", "literal"])
def test_every_direct_source_requires_assigned_page_lineage(tmp_path, part):
    store, context, args, records = fixture(tmp_path, page=True)
    with store:
        old = records[part]
        unrelated = source(store, store.get_artifact(old["artifact_ref"]))
        if part == "literal":
            for witness in args["literals"].values():
                witness["source_ref"] = unrelated["id"]
        else:
            args[{"root": "source_ref", "coordinate": "coordinate_source_ref",
                "validation": "validation_source_ref"}[part]] = unrelated["id"]
        context = replace(context, received_record_refs=(*context.received_record_refs, unrelated["id"]))
        with pytest.raises(ContractError, match="outside_assigned_source"):
            LiteratureStructureRepository(store, context.run_id).populate(context, args, "bad")


def test_saved_only_replay_reopen_disables_reader_calculator_and_source_bytes(tmp_path, monkeypatch):
    store, context, args, records = fixture(tmp_path)
    with store:
        repo = LiteratureStructureRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        ref = outcome["result"]["sheet_ref"]
        saved = repo.read(ref)
        rows = repo.project_cells([ref], permitted_record_refs=outcome["record_refs"])
        forbidden_refs = {row["artifact_ref"] for row in records.values()}
    def forbidden(*_args, **_kwargs):
        raise AssertionError("synthetic replay attempted source work")
    monkeypatch.setattr("gene_annotation_episode.literature_structure_storage.read_structure_inputs", forbidden)
    monkeypatch.setattr("gene_annotation_episode.literature_structure_storage.populate_source_geometry", forbidden)
    with Store(tmp_path) as reopened:
        repo = LiteratureStructureRepository(reopened, context.run_id)
        read = reopened.get_artifact
        def saved_only(ref):
            assert ref not in forbidden_refs
            return read(ref)
        monkeypatch.setattr(reopened, "get_artifact", saved_only)
        reopened.db.execute("pragma query_only=ON")
        assert repo.populate(context, args, "selected") == outcome
        assert repo.read(ref) == saved
        assert repo.project_cells([ref], permitted_record_refs=outcome["record_refs"]) == rows


def test_publication_is_atomic_including_all_bindings_and_operation(tmp_path, monkeypatch):
    store, context, args, _ = fixture(tmp_path)
    with store:
        repo = LiteratureStructureRepository(store, context.run_id)
        before = [store.list(kind) for kind in ("source", "reference", "context")]
        put = store.put
        def fail(kind, record, **kwargs):
            if kind == "source" and record["provider"] == PROVIDER:
                raise RuntimeError("synthetic publication interruption")
            return put(kind, record, **kwargs)
        monkeypatch.setattr(store, "put", fail)
        with pytest.raises(RuntimeError, match="publication interruption"):
            repo.populate(context, args, "atomic")
        assert [store.list(kind) for kind in ("source", "reference", "context")] == before
        assert store.db.execute("select count(*) from literature_structure_operations").fetchone()[0] == 0
        monkeypatch.setattr(store, "put", put)
        assert repo.populate(context, args, "atomic")["status"] == "completed"


def test_invalid_source_cannot_publish_bindings(tmp_path):
    store, context, args, records = fixture(tmp_path)
    with store:
        bad = source(store, "data_bad\n_entry.id 1ABC\n", parents=[records["root"]["id"]])
        args["coordinate_source_ref"] = bad["id"]
        context = replace(context, received_record_refs=(*context.received_record_refs, bad["id"]))
        repo = LiteratureStructureRepository(store, context.run_id)
        before = [store.list(kind) for kind in ("source", "reference", "context")]
        with pytest.raises(ValueError):
            repo.populate(context, args, "invalid")
        assert [store.list(kind) for kind in ("source", "reference", "context")] == before


def test_same_run_selected_authority_and_immutable_operation_identity(tmp_path):
    store, context, args, _ = fixture(tmp_path)
    with store:
        repo = LiteratureStructureRepository(store, context.run_id)
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
            LiteratureStructureRepository(store, "different-run").read(ref)
        with pytest.raises(ContractError, match="reused_for_different_work"):
            repo.populate(context, {**args, "source_kind": "primary_source"}, "selected")
        with pytest.raises(ContractError, match="run_mismatch"):
            repo.populate(replace(context, run_id="different-run"), args, "new")
        with pytest.raises(ContractError, match="operation_key_required"):
            repo.populate(context, args, "")
        second = repo.populate(context, args, "second")
        assert second["changed_record_refs"] == [second["result"]["sheet_ref"]]
        outcome["result"]["cells"]["local_fit_index"]["value"] = 999
        assert repo.populate(context, args, "selected")["result"]["cells"]["local_fit_index"]["value"] == pytest.approx(.64)


@pytest.mark.parametrize("field,value", [("value", .1), ("lower", .1), ("upper", .2),
    ("formula_code", "structure_local_fit_index_v1"), ("validation_binding", "entry_mismatch"),
    ("assayed_subject_ref", None), ("conditional_on", []),
    ("coordinate_source_ref", None), ("operand_source_kind", "primary_source"),
    ("model_number", 2), ("geometry_definition", []), ("local_validation_definition", [])])
def test_forged_return_rows_rejected(tmp_path, field, value):
    store, context, args, _ = fixture(tmp_path)
    with store:
        repo = LiteratureStructureRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        rows = repo.project_cells([outcome["result"]["sheet_ref"]],
            permitted_record_refs=outcome["record_refs"], components=("source_geometry_positive",))
        rows[0][field] = value
        with pytest.raises(ContractError, match="differs_from_saved"):
            repo.validate_returned_values(rows, permitted_record_refs=outcome["record_refs"])


def test_exact_admitted_subset_forwarded_without_extra_cells(tmp_path):
    store, context, args, _ = fixture(tmp_path)
    with store:
        repo = LiteratureStructureRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        ref = outcome["result"]["sheet_ref"]
        rows = repo.project_cells([ref], permitted_record_refs=outcome["record_refs"],
            components=("geometry_support_fraction",))
        parent = replace(context, episode_id="parent", received_record_refs=tuple(outcome["record_refs"]))
        repo.receive_cells(parent, rows, "delivery")
        repo.receive_cells(parent, rows, "delivery")
        assert repo.received_cells(parent) == rows and len(COMPONENTS) == 6
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
        assert not store.list("observation")


def test_closed_schema_no_free_text_or_invalid_numbers(tmp_path):
    store, context, args, _ = fixture(tmp_path)
    with store:
        repo = LiteratureStructureRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        rows = repo.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=outcome["record_refs"])
        for field, value in (("formula_code", "D * G"), ("unavailable_reason", "arbitrary prose"),
            ("conditional_on", ["new assumption"]), ("origin", "reported"),
            ("lower", float("nan")), ("upper", float("inf")), ("formula", "raw formula")):
            changed = deepcopy(rows)
            changed[0][field] = value
            with pytest.raises(ContractError, match="representation_error"):
                repo.validate_returned_values(changed, permitted_record_refs=outcome["record_refs"])
        for field, value in (("source_kind", "invented_kind"), ("model_number", True),
                ("population_occupancy", 1)):
            changed_args = deepcopy(args)
            changed_args[field] = value
            with pytest.raises(ContractError, match="representation_error"):
                repo.populate(context, changed_args, "invalid_arguments")


def test_missing_literal_bindings_stay_null_and_witness_span_controls_identity(tmp_path):
    store, context, args, records = fixture(tmp_path)
    with store:
        args["literals"]["partner"] = None
        args["literals"]["construct"] = deepcopy(args["literals"]["molecule"])
        args["literals"]["experimental_system"] = deepcopy(args["literals"]["condition"])
        repo = LiteratureStructureRepository(store, context.run_id)
        first = repo.populate(context, args, "first")
        saved = repo.read(first["result"]["sheet_ref"])
        assert saved["experimental_bindings"]["partner_ref"] is None
        assert saved["experimental_bindings"]["construct_ref"] != saved["experimental_bindings"]["assayed_subject_ref"]
        assert saved["experimental_bindings"]["experimental_system_ref"] != saved["experimental_bindings"]["condition_ref"]
        second_text = source(store, "Molecule|Molecule", parents=[records["root"]["id"]])
        context = replace(context, received_record_refs=(*context.received_record_refs, second_text["id"]))
        args["literals"]["molecule"].update(source_ref=second_text["id"], start=0, end=8)
        second = repo.populate(context, args, "second")
        args["literals"]["molecule"].update(start=9, end=17)
        third = repo.populate(context, args, "third")
        assert repo.read(second["result"]["sheet_ref"])["experimental_bindings"]["assayed_subject_ref"] != repo.read(third["result"]["sheet_ref"])["experimental_bindings"]["assayed_subject_ref"]
