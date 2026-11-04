"""Synthetic custody, saved replay and exact numerical parent-form tests.

No primary paper packets or model-backed literature interpretation are used.
"""
from copy import deepcopy
from dataclasses import replace
from io import BytesIO
import json
import math

from PIL import Image
import pytest

from gene_annotation_episode.communication import (
    ReportBoundaryError, form_with_facts, plain, validate_closed_schema, validate_form,
)
from gene_annotation_episode.domain import ContractError, canonical, obj, validate_schema
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.literature_binding_model_storage import (
    COMPONENTS, FORMULA_CODES, FORMULA_MEANINGS, PROVIDER, LiteratureBindingModelRepository,
    binding_model_cells_schema, binding_model_population_schema,
)
from gene_annotation_episode.literature_binding_models import binding_model_operand_keys
from gene_annotation_episode.literature_binding_storage import LiteratureBindingRepository
from gene_annotation_episode.state import Store


def source(store, content, *, parents=(), text=None, provider="synthetic_binding_model_fixture"):
    artifact = store.artifact(content, "application/octet-stream")
    return store.put("source", {"provider": provider, "accession": None, "uri": None,
        "artifact_ref": artifact, "text_ref": text, "request_ref": None, "version": None,
        "retrieved_at": None, "parent_source_refs": list(parents)}, origin="caller")


def fixture(path, *, model=True, variance="known", censoring="none", expressions=("10", "20"),
            visual=False, page=False):
    store = Store(path)
    store.create_problem(raw_sequence="ATGGCT", molecule="dna")
    root = source(store, "Synthetic source methods.")
    raw_parents = [root["id"]]
    raw_inputs = [root["id"]]
    rows = [{"subject": "SyntheticProtein", "state": "apo", "experiment": "synthetic-binding",
        "ligand": ligand, "expression": expression,
        "locator": {"row_index": index, "column": "IC50"}}
        for index, (ligand, expression) in enumerate(zip(("reference", "test"), expressions))]
    if visual:
        buffer = BytesIO()
        Image.new("RGB", (20, 10), (221, 222, 223)).save(buffer, format="PNG")
        image = source(store, buffer.getvalue(), parents=[root["id"]])
        raw_inputs.append(image["id"])
        raw_parents.append(image["id"])
        for index, row in enumerate(rows):
            row["locator"] = {"original_source_ref": image["id"],
                "original_artifact_ref": image["artifact_ref"], "image_region": [5 * index, 0, 5 * index + 5, 5]}
    table = {"version": "binding_parameter_table_v1", "table_id": "SyntheticTable",
        "parameter_kind": "ic50", "unit": "nM", "uncertainty_basis": "fit_to_averaged_curve",
        "minimum_experiment_count": 2, "rows": rows}
    original = source(store, canonical(table), parents=raw_parents)
    native_context = BindingContext("synthetic-model-run", "binding-child", "literature_table",
        (("literature_table", "fixture"),), store.validate_scope(), {}, {},
        (original["id"], *raw_inputs))
    native_args = {"source_ref": original["id"],
        "representation": "retained_visual_transcription" if visual else "synthetic_fixture",
        "subject": "SyntheticProtein", "state": "apo", "experiment": "synthetic-binding",
        "reference_ligand": "reference", "test_ligand": "test", "parameter_kind": "ic50",
        "design": "unknown", "protein_arrangement": "unknown", "interpretation_witnesses": []}
    native_repo = LiteratureBindingRepository(store, native_context.run_id)
    native_outcome = native_repo.populate(native_context, native_args, "native")
    binding_ref = native_outcome["result"]["sheet_ref"]
    binding = native_repo.read(binding_ref)
    args = {"source_ref": binding_ref, "model_source_ref": None, "model_witnesses": []}
    received = [binding_ref]
    records = {"root": root, "original": original, "native": binding,
               "native_outcome": native_outcome}
    if model:
        parent = source(store, "Synthetic covariance declaration.", parents=[root["id"]])
        witness_source = source(store, "Known joint natural-log covariance for the selected estimates.",
            parents=[root["id"]])
        keys = binding_model_operand_keys(binding["sheet"])
        declaration = {"version": "known_normal_log_binding_v1", "parameter_kind": "ic50",
            "measurement_order": ["reference", "test"], "measurement_keys": [keys["reference"], keys["test"]],
            "log_covariance": [[.04, .01], [.01, .09]], "variance_status": variance,
            "censoring_model": censoring, "log_basis": "natural_log_nM", "origin": "synthetic"}
        model_source = source(store, canonical(declaration), parents=[parent["id"]])
        quote = "Known joint natural-log covariance for the selected estimates."
        witness = {"source_ref": witness_source["id"], "representation": "original", "start": 0,
                   "end": len(quote.encode()), "quote": quote}
        args.update(model_source_ref=model_source["id"], model_witnesses=[witness])
        received.extend([model_source["id"], parent["id"], witness_source["id"]])
        records.update(model_source=model_source, parent=parent, witness_source=witness_source,
                       declaration=declaration)
    context = replace(native_context, episode_id="model-child", received_record_refs=tuple(received),
        assignment={"page": {"source_ref": root["id"]}} if page else {})
    return store, context, args, records


def new_model(store, context, args, declaration, *, parents=None, text=None):
    original = store.get(args["model_source_ref"])
    selected = source(store, canonical(declaration),
        parents=original["parent_source_refs"] if parents is None else parents, text=text)
    return replace(context, received_record_refs=(*context.received_record_refs, selected["id"])), {
        **args, "model_source_ref": selected["id"]}


def test_selected_numerical_cells_and_closed_typed_subset_preserve_meaning(tmp_path):
    store, context, args, records = fixture(tmp_path)
    with store:
        repo = LiteratureBindingModelRepository(store, context.run_id)
        before_refs = store.list("reference")
        outcome = repo.populate(context, args, "selected")
        sheet_ref = outcome["result"]["sheet_ref"]
        saved = repo.read(sheet_ref)
        assert store.get(sheet_ref)["provider"] == PROVIDER
        assert saved["version"] == "literature_binding_model_record_v1"
        assert saved["binding_sheet"] == records["native"]["sheet"]
        assert saved["experimental_bindings"] == records["native"]["experimental_bindings"]
        assert saved["comparison"] == records["native"]["comparison"]
        assert saved["original_evidence_source_ref"] == records["original"]["id"]
        assert saved["model_source_provenance"] == {"source_ref": args["model_source_ref"],
            "artifact_ref": records["model_source"]["artifact_ref"]}
        assert saved["sheet"]["measurement_keys"] == binding_model_operand_keys(saved["binding_sheet"])
        assert saved["sheet"]["model"]["log_covariance"] == [[.04, .01], [.01, .09]]
        assert saved["model_witnesses"][0]["artifact_ref"] == records["witness_source"]["artifact_ref"]
        assert saved["sheet"]["cells"]["log_contrast_noise_variance"]["value"] == pytest.approx(.11)
        assert saved["sheet"]["cells"]["source_profile_log_ratio"]["value"] == pytest.approx(2.1838773359918244)
        assert saved["sheet"]["cells"]["source_signed_index"]["value"] == pytest.approx(.7975846370428177)
        selected = ("source_signed_index", "log_parameter_contrast", "log_contrast_noise_variance")
        cells = repo.project_cells([sheet_ref], permitted_record_refs=outcome["record_refs"], components=selected)
        assert [row["component"] for row in cells] == list(selected)
        assert cells[0]["conditional_on"] == ["supplied_log_covariance", "known_normal_log_parameters"]
        assert cells[1]["conditional_on"] == []
        assert cells[2]["conditional_on"] == ["supplied_log_covariance"]
        assert all(row["contrast_meaning"] == "test_parameter_exceeds_reference" for row in cells)
        assert all(row["evaluated_scope"] == "interpreted_source_parameter_contrast" for row in cells)
        assert all(row["variance_status"] == "known" and row["model_origin"] == "synthetic" for row in cells)
        assert all(row["source_uncertainty_basis"] == "fit_to_averaged_curve" for row in cells)
        assert all(row["independent_preparation_count"] is None for row in cells)
        assert all(row["confidence_bound"] is None and row["parameter_identification_bound"] is None for row in cells)
        assert all("formula" not in row and "measurement_keys" not in row and "model" not in row for row in cells)
        assert "binding_measurement_" not in canonical(cells)
        for row in cells:
            assert FORMULA_MEANINGS[row["formula_code"]] == saved["sheet"]["cells"][row["component"]]["formula"]
        schema = obj({"measurements": binding_model_cells_schema()})
        validate_closed_schema(schema)
        form = form_with_facts({}, schema, {"literature_binding_model_cells": cells})
        assert validate_form(form, schema, lambda ref, namespace:
            ref in outcome["record_refs"] and store.get(ref)["record_type"] == namespace) == form
        repo.validate_cells(cells, sheet_refs=[sheet_ref], permitted_record_refs=outcome["record_refs"], components=selected)
        assert outcome["changed_record_refs"] == [sheet_ref]
        assert set(saved["input_source_refs"]) <= set(outcome["record_refs"])
        assert set(ref for ref in saved["experimental_bindings"].values() if ref) <= set(outcome["record_refs"])
        assert store.list("reference") == before_refs
        assert not store.list("observation")


def test_received_saved_native_sheet_requires_no_raw_original_receipts_or_bytes(tmp_path, monkeypatch):
    store, context, args, records = fixture(tmp_path, visual=True)
    with store:
        forbidden_artifacts = {store.get(ref)["artifact_ref"] for ref in records["native"]["input_source_refs"]}
        get_artifact = store.get_artifact
        def guarded(reference):
            assert reference not in forbidden_artifacts, "original source bytes must not be reacquired"
            return get_artifact(reference)
        monkeypatch.setattr(store, "get_artifact", guarded)
        assert not set(records["native"]["input_source_refs"]) & set(context.received_record_refs)
        repo = LiteratureBindingModelRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        assert outcome["result"]["cells"]["log_parameter_contrast"]["value"] == pytest.approx(math.log(2))
        assert records["original"]["id"] in outcome["record_refs"]


@pytest.mark.parametrize("model", [False, True])
def test_fresh_reopen_replays_saved_result_without_parser_calculator_or_source_reads(tmp_path, monkeypatch, model):
    store, context, args, records = fixture(tmp_path, model=model, visual=True)
    repo = LiteratureBindingModelRepository(store, context.run_id)
    outcome = repo.populate(context, args, "selected")
    saved = repo.read(outcome["result"]["sheet_ref"])
    cells = repo.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=outcome["record_refs"],
                               components=("source_profile_log_ratio",))
    forbidden_artifacts = {store.get(ref)["artifact_ref"] for ref in saved["input_source_refs"]
        if ref != args["source_ref"]}
    store.close()
    def forbidden(*_args, **_kwargs):
        raise AssertionError("saved projection/replay must not parse, calculate or read images")
    for module, names in (("literature_binding_model_storage", ("read_binding_model", "populate_binding_model", "binding_model_operand_keys")),
            ("literature_binding_storage", ("read_binding_parameter_table", "populate_binding_contrast"))):
        for name in names:
            monkeypatch.setattr(f"gene_annotation_episode.{module}.{name}", forbidden)
    monkeypatch.setattr("gene_annotation_episode.literature_binding_storage.Image.open", forbidden)
    with Store(tmp_path) as reopened:
        get_artifact = reopened.get_artifact
        def guarded(reference):
            assert reference not in forbidden_artifacts
            return get_artifact(reference)
        monkeypatch.setattr(reopened, "get_artifact", guarded)
        restored = LiteratureBindingModelRepository(reopened, context.run_id)
        assert restored.populate(context, args, "selected") == outcome
        assert restored.read(outcome["result"]["sheet_ref"]) == saved
        assert restored.project_cells([outcome["result"]["sheet_ref"]],
            permitted_record_refs=outcome["record_refs"], components=("source_profile_log_ratio",)) == cells
        for denied in saved["direct_input_source_refs"]:
            with pytest.raises(ContractError, match="not_received"):
                restored.populate(replace(context, received_record_refs=tuple(
                    ref for ref in context.received_record_refs if ref != denied)), args, "selected")
        with pytest.raises(ContractError, match="reused_for_different_work"):
            restored.populate(context, {**args, "model_witnesses": [*args["model_witnesses"],
                {"source_ref": args["source_ref"], "representation": "original", "start": 0, "end": 1, "quote": "{"}]}, "selected")
        with pytest.raises(ContractError, match="run_mismatch"):
            restored.populate(replace(context, run_id="other-run"), args, "selected")


def test_missing_model_preserves_native_partial_cells_and_original_limit(tmp_path):
    store, context, args, _ = fixture(tmp_path, model=False, expressions=("10", ">20"))
    with store:
        repo = LiteratureBindingModelRepository(store, context.run_id)
        outcome = repo.populate(context, args, "no-model")
        cells = repo.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=outcome["record_refs"])
        assert cells[0]["value"] == pytest.approx(math.log(2))
        assert cells[0]["relation"] == "gt" and cells[0]["status"] == "reported_limit"
        assert cells[0]["bound_kind"] == "reported_limit_arithmetic"
        assert all(row["value"] is None and row["unavailable_reason"] == "binding_sampling_model_unreported" for row in cells[1:])
        assert all(row["model_kind"] == "unreported" and row["variance_status"] == "not_supplied" for row in cells)
        assert all(row["model_source_ref"] is None for row in cells)
        validate_schema(cells, binding_model_cells_schema())
        saved = repo.read(outcome["result"]["sheet_ref"])
        assert saved["model_source_provenance"] is None and saved["sheet"]["model"] is None


@pytest.mark.parametrize("variance,censoring,expressions,reason,conditions", [
    ("estimated", "none", ("10", "20"), "known_log_covariance_required", ["supplied_log_covariance"]),
    ("unknown", "none", ("10", "20"), "covariance_status_unknown", []),
    ("known", "unknown", ("10", ">20"), "binding_censoring_mechanism_unreported", ["supplied_log_covariance"]),
    ("known", "threshold_of_log_estimate", ("10", ">20"), None,
        ["supplied_log_covariance", "known_normal_log_parameters", "threshold_censoring_of_log_estimate"]),
    ("known", "threshold_of_log_estimate", ("<10", ">20"), "two_censored_observations_unsupported", ["supplied_log_covariance"]),
])
def test_conditioned_model_meanings_survive_projection(tmp_path, variance, censoring, expressions, reason, conditions):
    store, context, args, _ = fixture(tmp_path, variance=variance, censoring=censoring, expressions=expressions)
    with store:
        repo = LiteratureBindingModelRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        row = repo.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=outcome["record_refs"],
                                components=("source_profile_log_ratio",))[0]
        assert row["unavailable_reason"] == reason and row["conditional_on"] == conditions
        assert row["variance_status"] == variance and row["censoring_model"] == censoring
        if reason is None:
            assert row["relation"] == "eq" and row["status"] == "populated"
            assert row["bound_kind"] is None and row["value"] > 0


@pytest.mark.parametrize("part", ["binding", "model", "witness", "parent"])
def test_every_actual_direct_source_must_be_received_before_any_publication(tmp_path, part):
    store, context, args, records = fixture(tmp_path)
    with store:
        denied = {"binding": args["source_ref"], "model": args["model_source_ref"],
                  "witness": records["witness_source"]["id"], "parent": records["parent"]["id"]}[part]
        context = replace(context, received_record_refs=tuple(ref for ref in context.received_record_refs if ref != denied))
        before = store.list("source")
        repo = LiteratureBindingModelRepository(store, context.run_id)
        with pytest.raises(ContractError, match="not_received"):
            repo.populate(context, args, "invalid")
        assert store.list("source") == before
        assert store.db.execute("SELECT count(*) FROM literature_binding_model_operations").fetchone()[0] == 0
        assert not store.list("observation")


@pytest.mark.parametrize("part", ["binding", "model", "witness", "parent", "original"])
def test_input_and_provenance_scope_checked(tmp_path, monkeypatch, part):
    store, context, args, records = fixture(tmp_path)
    with store:
        denied = {"binding": args["source_ref"], "model": args["model_source_ref"],
            "witness": records["witness_source"]["id"], "parent": records["parent"]["id"],
            "original": records["original"]["id"]}[part]
        subset = store.reference_subset
        monkeypatch.setattr(store, "reference_subset", lambda candidates, scope:
                            [] if denied in candidates else subset(candidates, scope))
        with pytest.raises(ContractError, match="outside_scope"):
            LiteratureBindingModelRepository(store, context.run_id).populate(context, args, "invalid")


def test_page_lineage_accepts_direct_descendants_without_raw_receipt(tmp_path):
    store, context, args, records = fixture(tmp_path, page=True, visual=True)
    with store:
        outcome = LiteratureBindingModelRepository(store, context.run_id).populate(context, args, "descendants")
        assert outcome["status"] == "completed"
        assert records["root"]["id"] not in context.received_record_refs


@pytest.mark.parametrize("part", ["model", "witness", "parent"])
def test_page_lineage_rejects_foreign_direct_source_even_if_received(tmp_path, part):
    store, context, args, records = fixture(tmp_path, page=True)
    with store:
        foreign = source(store, "Foreign scope source.")
        context = replace(context, received_record_refs=(*context.received_record_refs, foreign["id"]))
        if part == "model":
            args["model_source_ref"] = foreign["id"]
        elif part == "witness":
            args["model_witnesses"] = [{"source_ref": foreign["id"], "representation": "original",
                "start": 0, "end": 7, "quote": "Foreign"}]
        else:
            # One valid page parent makes the model a descendant. The second
            # declared parent is nevertheless an actual separately checked input.
            context, args = new_model(store, context, args, records["declaration"],
                parents=[records["parent"]["id"], foreign["id"]])
        with pytest.raises(ContractError, match="outside_assigned_source"):
            LiteratureBindingModelRepository(store, context.run_id).populate(context, args, "foreign")


@pytest.mark.parametrize("problem,expected", [("no_witness", "witness_required"),
    ("wrong_quote", "source_quote_mismatch"), ("bad_owner", "measurement_owner_mismatch"),
    ("bad_covariance", "positive_definite"), ("wrong_kind", "parameter_kind_mismatch")])
def test_supplied_source_model_and_witnesses_are_validated_without_fallback(tmp_path, problem, expected):
    store, context, args, records = fixture(tmp_path)
    with store:
        if problem == "no_witness":
            args["model_witnesses"] = []
        elif problem == "wrong_quote":
            args["model_witnesses"][0]["quote"] = "Invented model interpretation."
        else:
            declaration = deepcopy(records["declaration"])
            if problem == "bad_owner":
                declaration["measurement_keys"].reverse()
            elif problem == "bad_covariance":
                declaration["log_covariance"] = [[1, 1], [1, 1]]
            else:
                declaration["parameter_kind"] = "reported_hill_kd"
            context, args = new_model(store, context, args, declaration)
        repo = LiteratureBindingModelRepository(store, context.run_id)
        with pytest.raises((ContractError, ValueError), match=expected):
            repo.populate(context, args, "invalid")
        assert store.db.execute("SELECT count(*) FROM literature_binding_model_operations").fetchone()[0] == 0


def test_original_model_bytes_used_instead_of_text_derivative(tmp_path):
    store, context, args, records = fixture(tmp_path)
    with store:
        bad = source(store, b"\xff", parents=[records["parent"]["id"]],
                     text=records["model_source"]["artifact_ref"])
        context = replace(context, received_record_refs=(*context.received_record_refs, bad["id"]))
        with pytest.raises(ValueError, match="malformed_binding_model_source"):
            LiteratureBindingModelRepository(store, context.run_id).populate(context,
                {**args, "model_source_ref": bad["id"]}, "invalid")


def test_forged_provider_and_nonselected_binding_sheet_rejected(tmp_path):
    store, context, args, records = fixture(tmp_path)
    with store:
        repo = LiteratureBindingModelRepository(store, context.run_id)
        native_record = store.get(args["source_ref"])
        fields = {name: value for name, value in native_record.items() if name not in ("id", "record_type", "origin")}
        fields["accession"] = "forged-binding-output"
        forged = store.put("source", fields, origin="tool")
        context = replace(context, received_record_refs=(*context.received_record_refs, forged["id"]))
        with pytest.raises(ContractError, match="not_selected_output"):
            repo.populate(context, {**args, "source_ref": forged["id"]}, "forged")
        with pytest.raises(ContractError, match="run_mismatch"):
            LiteratureBindingModelRepository(store, "other-run").populate(
                replace(context, run_id="other-run"), args, "wrong-run-native")
        outcome = repo.populate(context, args, "selected")
        record = store.get(outcome["result"]["sheet_ref"])
        fields = {name: value for name, value in record.items() if name not in ("id", "record_type", "origin")}
        fields["accession"] = "forged-model-output"
        forged_model = store.put("source", fields, origin="tool")
        with pytest.raises(ContractError, match="not_selected_output"):
            repo.read(forged_model["id"])


@pytest.mark.parametrize("changed,value", [("value", 100), ("relation", "gt"),
    ("bound_kind", "reported_limit_arithmetic"), ("conditional_on", []),
    ("formula_code", FORMULA_CODES["log_parameter_contrast"]),
    ("parameter_kind", "reported_hill_kd"), ("model_kind", "unreported"),
    ("variance_status", "estimated"), ("censoring_model", "unknown"),
    ("model_origin", "reported"), ("contrast_meaning", "activity_probability"),
    ("independent_preparation_count", 2)])
def test_saved_cell_authority_rejects_modified_meaning(tmp_path, changed, value):
    store, context, args, _ = fixture(tmp_path)
    with store:
        repo = LiteratureBindingModelRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        cells = repo.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=outcome["record_refs"],
                                   components=("source_profile_log_ratio",))
        cells[0][changed] = value
        with pytest.raises(ContractError, match="differs_from_saved"):
            repo.validate_returned_values(cells, permitted_record_refs=outcome["record_refs"])


def test_exact_subset_delivery_forwarding_and_no_receiver_receipt_or_extra_observation(tmp_path):
    store, context, args, _ = fixture(tmp_path)
    with store:
        repo = LiteratureBindingModelRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        sheet_ref = outcome["result"]["sheet_ref"]
        subset = repo.project_cells([sheet_ref], permitted_record_refs=outcome["record_refs"],
                                   components=("log_contrast_noise_sd",))
        parent = replace(context, episode_id="parent", role="literature", path=(("literature", "parent"),))
        assert repo.received_cells(parent) == []
        repo.receive_cells(parent, subset, "admitted")
        repo.receive_cells(parent, subset, "admitted")
        assert repo.received_cells(parent) == subset
        assert len(repo.received_cells(parent)) == 1
        grandparent = replace(context, episode_id="grandparent", role="literature", path=(("literature", "grandparent"),))
        repo.receive_cells(grandparent, repo.received_cells(parent), "forwarded")
        assert repo.received_cells(grandparent) == subset
        assert not store.list("observation")
        with pytest.raises(ContractError, match="duplicate"):
            repo.validate_returned_values(subset * 2, permitted_record_refs=outcome["record_refs"])
        other = repo.project_cells([sheet_ref], permitted_record_refs=outcome["record_refs"],
                                   components=("source_signed_index",))
        with pytest.raises(ContractError, match="delivery_identity_conflict"):
            repo.receive_cells(parent, other, "admitted")
        with pytest.raises(ContractError, match="not_received"):
            repo.project_cells([sheet_ref], permitted_record_refs=())


@pytest.mark.parametrize("selection", [("not_a_component",), ("log_parameter_contrast",) * 2, "source_signed_index", [[1]]])
def test_invalid_component_selections_are_rejected(tmp_path, selection):
    store, context, args, _ = fixture(tmp_path, model=False)
    with store:
        repo = LiteratureBindingModelRepository(store, context.run_id)
        with pytest.raises(ContractError, match="component_selection_invalid"):
            repo.project_cells([], permitted_record_refs=(), components=selection)


def test_population_schema_is_number_free_and_typed_schema_is_closed(tmp_path):
    store, context, args, _ = fixture(tmp_path)
    with store:
        validate_schema(args, binding_model_population_schema())
        assert set(binding_model_population_schema()["properties"]) == {"source_ref", "model_source_ref", "model_witnesses"}
        for extra in ({"log_covariance": [[1, 0], [0, 1]]}, {"variance_status": "known"}, {"model_kind": "known_normal_log_parameters"}):
            with pytest.raises(ContractError):
                validate_schema({**args, **extra}, binding_model_population_schema())
        schema = obj({"measurements": binding_model_cells_schema()})
        validate_closed_schema(schema)
        repo = LiteratureBindingModelRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        cells = repo.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=outcome["record_refs"])
        validate_schema(cells, binding_model_cells_schema())
        altered = deepcopy(cells)
        altered[0]["unrestricted_findings"] = "An invented conclusion."
        with pytest.raises(ContractError):
            validate_schema(altered, binding_model_cells_schema())
        with pytest.raises(ReportBoundaryError):
            validate_form({"measurements": altered}, schema, lambda *_: True)
        assert len(COMPONENTS) == 5
