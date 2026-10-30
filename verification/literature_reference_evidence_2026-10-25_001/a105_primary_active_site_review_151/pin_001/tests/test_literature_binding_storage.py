"""Synthetic selected tables and generated tiny images exercise source custody.

These are repository/typed-boundary checks, not model-backed paper examination.
"""
from copy import deepcopy
from dataclasses import replace
from io import BytesIO
import json

from PIL import Image
import pytest

from gene_annotation_episode.communication import form_with_facts, plain, validate_closed_schema, validate_form
from gene_annotation_episode.domain import ContractError, canonical, obj, validate_schema
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.literature_binding_storage import (
    COMPONENTS, PROVIDER, LiteratureBindingRepository, binding_cells_schema, binding_population_schema)
from gene_annotation_episode.state import Store


def source(store, content, provider="synthetic_binding_fixture", parents=(), text=None):
    artifact = store.artifact(content, "application/octet-stream")
    return store.put("source", {"provider": provider, "accession": None, "uri": None,
        "artifact_ref": artifact, "text_ref": text, "request_ref": None, "version": None,
        "retrieved_at": None, "parent_source_refs": list(parents)}, origin="caller")


def setup_store(path, *, visual=False, rows=None, parent_extra=False):
    store = Store(path)
    store.create_problem(raw_sequence="ATGGCT", molecule="dna")
    methods = source(store, "Competition experiment. Concentration in nM.")
    inputs = [methods["id"]]
    parents = []
    if rows is None:
        rows = [{"subject": "FixtureProtein", "state": "apo", "experiment": "fixture-competition",
            "ligand": ligand, "expression": expression,
            "locator": {"row_index": index + 6, "column": "IC50"}}
            for index, (ligand, expression) in enumerate((("self", "8 ± 1"), ("alternate", ">80")))]
    else:
        rows = deepcopy(rows)
    if visual:
        image_bytes = BytesIO()
        Image.new("RGB", (20, 10), color=(250, 249, 248)).save(image_bytes, format="PNG")
        image = source(store, image_bytes.getvalue(), "synthetic_image", [methods["id"]])
        inputs.append(image["id"])
        parents.append(image["id"])
        for index, row in enumerate(rows):
            row["locator"] = {"original_source_ref": image["id"], "original_artifact_ref": image["artifact_ref"],
                              "image_region": [index * 5, 0, index * 5 + 5, 5]}
    if parent_extra:
        parents.append(methods["id"])
    table = {"version": "binding_parameter_table_v1", "table_id": "FixtureTable",
        "parameter_kind": "ic50", "unit": "nM", "uncertainty_basis": "fit_to_averaged_curve",
        "minimum_experiment_count": 2, "rows": rows}
    original = source(store, canonical(table), parents=parents)
    inputs.insert(0, original["id"])
    context = BindingContext("binding-fixture-run", "binding-fixture-child", "literature_table",
        (("literature_table", "fixture"),), store.validate_scope(), {}, {}, tuple(inputs))
    witness = {"source_ref": methods["id"], "representation": "original", "start": 0,
        "end": len(b"Competition experiment."), "quote": "Competition experiment."}
    arguments = {"source_ref": original["id"],
        "representation": "retained_visual_transcription" if visual else "synthetic_fixture",
        "subject": "FixtureProtein", "state": "apo", "experiment": "fixture-competition",
        "reference_ligand": "self", "test_ligand": "alternate", "parameter_kind": "ic50",
        "design": "equilibrium_competition", "protein_arrangement": "single_preparation",
        "interpretation_witnesses": [witness]}
    return store, context, arguments, table


def replace_table(store, context, args, table, *, parents=None, text=None):
    original = store.get(args["source_ref"])
    new = source(store, canonical(table), parents=original["parent_source_refs"] if parents is None else parents,
                 text=text)
    return replace(context, received_record_refs=(*context.received_record_refs, new["id"])), {
        **args, "source_ref": new["id"]}


def test_selected_population_and_closed_typed_subset_preserve_limit_and_unknown_bounds(tmp_path):
    store, context, args, _ = setup_store(tmp_path)
    with store:
        repo = LiteratureBindingRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        sheet_ref = outcome["result"]["sheet_ref"]
        saved = repo.read(sheet_ref)
        assert store.get(sheet_ref)["provider"] == PROVIDER
        assert saved["input_artifact_ref"] == store.get(args["source_ref"])["artifact_ref"]
        assert saved["input_source_refs"] == [args["source_ref"], args["interpretation_witnesses"][0]["source_ref"]]
        assert saved["comparison"] == {name: args[name] for name in (
            "subject", "state", "experiment", "reference_ligand", "test_ligand", "parameter_kind", "design", "protein_arrangement")}
        assert saved["interpretation_witnesses"][0]["artifact_ref"] == store.get(saved["input_source_refs"][1])["artifact_ref"]
        assert saved["sheet"]["annotation_credit"] is None
        assert outcome["result"]["uncertainty_basis"] == "fit_to_averaged_curve"
        assert outcome["result"]["minimum_experiment_count"] == 2
        assert outcome["result"]["independent_preparation_count"] is None
        received = (*context.received_record_refs, *outcome["record_refs"])
        selected = ("reference_relative_spread", "native_parameter_ratio", "source_signed_index")
        cells = repo.project_cells([sheet_ref], permitted_record_refs=received, components=selected)
        assert [row["component"] for row in cells] == list(selected)
        assert cells[0]["value"] == .125
        assert cells[1]["value"] == 10
        assert cells[1]["relation"] == "gt"
        assert cells[1]["status"] == "reported_limit"
        assert cells[1]["bound_kind"] == "reported_limit_arithmetic"
        assert cells[1]["confidence_bound"] is None
        assert cells[1]["parameter_identification_bound"] is None
        assert cells[1]["formula_code"] == "binding_native_parameter_ratio_v1"
        assert "formula" not in cells[1]
        assert saved["sheet"]["cells"]["native_parameter_ratio"]["formula"] == "test_parameter/reference_parameter"
        assert cells[1]["source_origins"] == ["synthetic"]
        assert cells[2]["value"] is None
        assert cells[2]["unavailable_reason"] == "binding_observation_model_unimplemented"
        for field, label in (("subject_ref", "FixtureProtein"), ("state_ref", "apo"),
                ("experiment_ref", "fixture-competition"), ("reference_ligand_ref", "self"),
                ("test_ligand_ref", "alternate")):
            binding = store.get(cells[0][field])
            assert binding["reference_type"] == "literature_result"
            assert binding["source_ref"] == args["source_ref"]
            assert binding["label"] == label
        schema = obj({"measurements": binding_cells_schema()})
        validate_closed_schema(schema)
        form = form_with_facts({}, schema, {"literature_binding_cells": cells})
        assert validate_form(form, schema, lambda ref, namespace:
            ref in received and store.get(ref)["record_type"] == namespace) == form
        repo.validate_cells(form["measurements"], sheet_refs=[sheet_ref], permitted_record_refs=received,
                            components=selected)
        parent = replace(context, episode_id="parent", role="literature", path=(("literature", "parent"),))
        repo.receive_cells(parent, cells, "admitted-subset")
        assert repo.received_cells(parent) == cells
        assert len(repo.received_cells(parent)) == 3
        assert not store.list("observation")


def test_reopen_replays_without_parsing_and_checks_all_original_inputs(tmp_path, monkeypatch):
    store, context, args, _ = setup_store(tmp_path, visual=True, parent_extra=True)
    repo = LiteratureBindingRepository(store, context.run_id)
    outcome = repo.populate(context, args, "selected")
    saved = repo.read(outcome["result"]["sheet_ref"])
    cells = repo.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=outcome["record_refs"],
                               components=("native_parameter_ratio",))
    store.close()
    def forbidden(*_args, **_kwargs):
        raise AssertionError("replay must not parse/recalculate/open an image")
    monkeypatch.setattr("gene_annotation_episode.literature_binding_storage.read_binding_parameter_table", forbidden)
    monkeypatch.setattr("gene_annotation_episode.literature_binding_storage.populate_binding_contrast", forbidden)
    monkeypatch.setattr("gene_annotation_episode.literature_binding_storage.Image.open", forbidden)
    with Store(tmp_path) as reopened:
        restored = LiteratureBindingRepository(reopened, context.run_id)
        assert restored.populate(context, args, "selected") == outcome
        assert restored.read(outcome["result"]["sheet_ref"]) == saved
        assert restored.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=outcome["record_refs"],
            components=("native_parameter_ratio",)) == cells
        for denied in saved["input_source_refs"]:
            with pytest.raises(ContractError, match="not_received"):
                restored.populate(replace(context, received_record_refs=tuple(
                    ref for ref in context.received_record_refs if ref != denied)), args, "selected")
        with pytest.raises(ContractError, match="reused_for_different_work"):
            restored.populate(context, {**args, "state": "different"}, "selected")
        with pytest.raises(ContractError, match="run_mismatch"):
            restored.populate(replace(context, run_id="different-run"), args, "selected")


def test_repeat_work_keeps_shared_identities_out_of_changed_records(tmp_path):
    store, context, args, _ = setup_store(tmp_path)
    with store:
        repo = LiteratureBindingRepository(store, context.run_id)
        first = repo.populate(context, args, "first")
        second = repo.populate(context, args, "second")
        assert first["record_refs"][1:] == second["record_refs"][1:]
        assert second["changed_record_refs"] == [second["result"]["sheet_ref"]]
        assert repo.populate(context, args, "first") == first
        assert store.db.execute("SELECT count(*) FROM literature_binding_operations").fetchone()[0] == 2


@pytest.mark.parametrize("changed", ["value", "relation", "bound_kind", "confidence_bound", "formula_code",
                                     "parameter_kind", "subject_ref", "source_origins"])
def test_returned_cell_authority_rejects_changes_in_any_meaning(tmp_path, changed):
    store, context, args, _ = setup_store(tmp_path)
    with store:
        repo = LiteratureBindingRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        cells = repo.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=outcome["record_refs"],
                                   components=("native_parameter_ratio",))
        replacement = {"value": 100, "relation": "eq", "bound_kind": None, "confidence_bound": 1,
            "formula_code": "binding_reference_parameter_v1", "parameter_kind": "reported_hill_kd",
            "subject_ref": cells[0]["experiment_ref"], "source_origins": ["reported"]}
        cells[0][changed] = replacement[changed]
        with pytest.raises(ContractError, match="differs_from_saved"):
            repo.validate_returned_values(cells, permitted_record_refs=outcome["record_refs"])


def test_no_full_sheet_expansion_on_subset_receipt_or_forwarding(tmp_path):
    store, context, args, _ = setup_store(tmp_path)
    with store:
        repo = LiteratureBindingRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        cells = repo.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=outcome["record_refs"],
                                   components=("reference_parameter",))
        parent = replace(context, episode_id="parent")
        repo.receive_cells(parent, cells, "delivery")
        repo.receive_cells(parent, cells, "delivery")
        assert repo.received_cells(parent) == cells
        assert len(repo.received_cells(parent)) == 1
        with pytest.raises(ContractError, match="duplicate"):
            repo.validate_returned_values(cells + cells, permitted_record_refs=outcome["record_refs"])
        with pytest.raises(ContractError, match="not_received"):
            repo.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=())
        other = repo.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=outcome["record_refs"],
                                   components=("test_parameter",))
        with pytest.raises(ContractError, match="delivery_identity_conflict"):
            repo.receive_cells(parent, other, "delivery")


def test_forged_unselected_source_sheet_is_not_an_authoritative_result(tmp_path):
    store, context, args, _ = setup_store(tmp_path)
    with store:
        repo = LiteratureBindingRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        record = store.get(outcome["result"]["sheet_ref"])
        fields = {name: value for name, value in record.items() if name not in ("id", "record_type", "origin")}
        fields["accession"] = "forged"
        forged = store.put("source", fields, origin="tool", scope=plain(context.scope))
        with pytest.raises(ContractError, match="not_selected_output"):
            repo.read(forged["id"])
        with pytest.raises(ContractError, match="run_mismatch"):
            LiteratureBindingRepository(store, "different-run").read(record["id"])


@pytest.mark.parametrize("problem,expected", [
    ("image_not_received", "not_received"), ("wrong_artifact", "lineage_mismatch"),
    ("undeclared_image", "lineage_mismatch"), ("outside_box", "region_outside_image"),
    ("not_image", "original_image_required"), ("unused_row_outside_box", "region_outside_image")])
def test_visual_checks_actual_original_custody_and_every_row_without_publishing(tmp_path, problem, expected):
    store, context, args, table = setup_store(tmp_path, visual=True)
    with store:
        original_id = table["rows"][0]["locator"]["original_source_ref"]
        parents = None
        if problem == "image_not_received":
            context = replace(context, received_record_refs=tuple(ref for ref in context.received_record_refs if ref != original_id))
        if problem == "wrong_artifact":
            table["rows"][0]["locator"]["original_artifact_ref"] = store.get(args["source_ref"])["artifact_ref"]
        if problem == "undeclared_image":
            parents = []
        if problem == "outside_box":
            table["rows"][0]["locator"]["image_region"] = [0, 0, 21, 10]
        if problem == "unused_row_outside_box":
            extra = deepcopy(table["rows"][0])
            extra["subject"] = "UnselectedSubject"
            extra["locator"]["image_region"] = [0, 0, 21, 10]
            table["rows"].append(extra)
        if problem == "not_image":
            bad = source(store, "This is no image")
            context = replace(context, received_record_refs=(*context.received_record_refs, bad["id"]))
            parents = [bad["id"]]
            for row in table["rows"]:
                row["locator"].update(original_source_ref=bad["id"], original_artifact_ref=bad["artifact_ref"])
        context, args = replace_table(store, context, args, table, parents=parents)
        before = store.list("source")
        repo = LiteratureBindingRepository(store, context.run_id)
        with pytest.raises(ContractError, match=expected):
            repo.populate(context, args, "invalid")
        assert store.list("source") == before
        assert not store.list("reference")
        assert store.db.execute("SELECT count(*) FROM literature_binding_operations").fetchone()[0] == 0


def test_original_utf8_source_is_used_instead_of_available_text_derivative(tmp_path):
    store, context, args, _ = setup_store(tmp_path)
    with store:
        valid = store.get(args["source_ref"])["artifact_ref"]
        bad = source(store, b"\xff", text=valid)
        context = replace(context, received_record_refs=(*context.received_record_refs, bad["id"]))
        with pytest.raises(ContractError, match="utf8_table_required"):
            LiteratureBindingRepository(store, context.run_id).populate(context, {**args, "source_ref": bad["id"]}, "invalid")


def test_missing_rows_leave_unsupported_source_identities_null(tmp_path):
    store, context, args, _ = setup_store(tmp_path, rows=[])
    with store:
        repo = LiteratureBindingRepository(store, context.run_id)
        outcome = repo.populate(context, args, "empty")
        saved = repo.read(outcome["result"]["sheet_ref"])
        assert all(value is None for value in saved["experimental_bindings"].values())
        assert all(cell["value"] is None for cell in saved["sheet"]["cells"].values())
        assert not store.list("reference")


@pytest.mark.parametrize("problem", ["absent", "duplicated_conflict", "wrong_quote", "not_received", "outside_page"])
def test_interpretation_witnesses_require_literal_received_scoped_sources(tmp_path, problem):
    store, context, args, _ = setup_store(tmp_path)
    with store:
        expected = "witness_required"
        if problem == "absent":
            args["interpretation_witnesses"] = []
        if problem == "duplicated_conflict":
            args["design"] = "conflicting"
            args["interpretation_witnesses"] *= 2
            expected = "conflict_witnesses_required"
        if problem == "wrong_quote":
            args["interpretation_witnesses"][0]["quote"] = "x"
            expected = "source_quote_mismatch"
        if problem == "not_received":
            context = replace(context, received_record_refs=(args["source_ref"],))
            expected = "not_received"
        if problem == "outside_page":
            context = replace(context, assignment={"page": {"source_ref": args["source_ref"]}})
            expected = "outside_assigned_source"
        with pytest.raises((ContractError, ValueError), match=expected):
            LiteratureBindingRepository(store, context.run_id).populate(context, args, "invalid")
        assert not store.list("reference")


def test_unknown_interpretations_need_no_witness_and_kind_design_mismatch_is_preserved(tmp_path):
    store, context, args, table = setup_store(tmp_path)
    with store:
        repo = LiteratureBindingRepository(store, context.run_id)
        unknown = {**args, "design": "unknown", "protein_arrangement": "unknown", "interpretation_witnesses": []}
        assert repo.populate(context, unknown, "unknown")["result"]["cells"]["native_parameter_ratio"]["value"] == 10
        mismatched = {**args, "design": "direct_binding_isotherm"}
        result = repo.populate(context, mismatched, "preserved-mismatch")
        assert result["result"]["comparison"]["parameter_kind"] == "ic50"
        assert result["result"]["comparison"]["design"] == "direct_binding_isotherm"


def test_source_page_lineage_accepts_received_descendants_and_rejects_foreign_tables(tmp_path):
    store, context, args, _ = setup_store(tmp_path, visual=True, parent_extra=True)
    with store:
        page = args["interpretation_witnesses"][0]["source_ref"]
        context = replace(context, role="literature_page", path=(("literature_page", "page"),), assignment={"source_ref": page})
        repo = LiteratureBindingRepository(store, context.run_id)
        assert repo.populate(context, args, "descendant")["status"] == "completed"
        foreign = source(store, canonical(json.loads(store.get_artifact(store.get(args["source_ref"])["artifact_ref"]))))
        with pytest.raises(ContractError, match="outside_assigned_source"):
            repo.populate(replace(context, received_record_refs=(*context.received_record_refs, foreign["id"])),
                          {**args, "source_ref": foreign["id"]}, "foreign")


def test_declared_parent_without_selected_rows_or_witness_is_preserved_and_authorized(tmp_path):
    store, context, args, _ = setup_store(tmp_path, visual=True, parent_extra=True)
    with store:
        args.update(design="unknown", protein_arrangement="unknown", interpretation_witnesses=[])
        original = store.get(args["source_ref"])
        methods = original["parent_source_refs"][-1]
        repo = LiteratureBindingRepository(store, context.run_id)
        denied = replace(context, received_record_refs=tuple(ref for ref in context.received_record_refs if ref != methods))
        with pytest.raises(ContractError, match="not_received"):
            repo.populate(denied, args, "unreceived-parent")
        outcome = repo.populate(context, args, "selected")
        assert set(original["parent_source_refs"]) <= set(repo.read(outcome["result"]["sheet_ref"])["input_source_refs"])
        with pytest.raises(ContractError, match="not_received"):
            repo.populate(denied, args, "selected")


def test_population_schema_has_no_model_authored_numerical_operands(tmp_path):
    store, _, args, _ = setup_store(tmp_path)
    with store:
        validate_schema(args, binding_population_schema())
        for field, value in (("value", 8), ("covariance", [[1]]), ("subject", " "), ("parameter_kind", "kd")):
            with pytest.raises(ContractError):
                validate_schema({**args, field: value}, binding_population_schema())
        assert len(COMPONENTS) == 10
