"""A saved evidence score must not become a new intervention measurement.

The fixtures create real saved reader cells from engineered numbers. They
establish software behavior, not biological evidence or autonomous execution.
"""
import json
import math
from pathlib import Path

import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.literature_binding_model_storage import LiteratureBindingModelRepository
from gene_annotation_episode.literature_intervention_inputs import read_intervention_inputs
from test_literature_binding_model_storage import fixture
from test_literature_intervention_storage import intervention_fixture


def intervention_reader(store, namespace, rows):
    """Read the selected saved fields through the real A106 adapter."""
    _, args = intervention_fixture(store)
    args.update(quantity_kind="native_endpoint", prediction_model=None)
    args["quantities"] = dict.fromkeys(args["quantities"])
    field = "component_key" if namespace == "literature_controlled_response_component_cells" else "component"
    sheet_ref = rows[0]["sheet_ref"]

    def read_source(ref, representation):
        record = store.get(ref)
        artifact = record["artifact_ref" if representation == "original" else "text_ref"]
        return dict(artifact_ref=artifact, content=store.get_artifact(artifact))

    def read_cells(selected_namespace, ref, fields):
        assert selected_namespace == namespace and ref == sheet_ref
        return [row for key in fields for row in rows if row[field] == key]

    def read():
        return read_intervention_inputs(args, read_source=read_source,
            read_cells=read_cells, read_record=store.get)

    return args, read, dict(kind="received_component", namespace=namespace, sheet_ref=sheet_ref)


@pytest.mark.parametrize("component", ["source_profile_log_ratio", "source_signed_index"])
@pytest.mark.parametrize("role", ["effect", "effect_variance", "assertion_prediction", "alternative_prediction"])
def test_saved_inference_cannot_supply_an_intervention_operand(tmp_path, component, role):
    store, context, model_args, _ = fixture(tmp_path)
    with store:
        repo = LiteratureBindingModelRepository(store, context.run_id)
        outcome = repo.populate(context, model_args, "model")
        sheet_ref = outcome["result"]["sheet_ref"]
        rows = repo.project_cells([sheet_ref], permitted_record_refs=outcome["record_refs"],
            components=[component, "log_parameter_contrast", "log_contrast_noise_variance"])
        selected_score = rows[0]
        assert selected_score["value"] is not None and math.isfinite(selected_score["value"])
        _, args = intervention_fixture(store)
        args.update(quantity_kind="native_endpoint", prediction_model=None)
        args["quantities"] = dict.fromkeys(args["quantities"])
        selection = dict(kind="received_component", namespace="literature_binding_model_cells",
            sheet_ref=sheet_ref, component=component)
        args["quantities"][role] = selection

        def read_source(ref, representation):
            record = store.get(ref)
            artifact = record["artifact_ref" if representation == "original" else "text_ref"]
            return dict(artifact_ref=artifact, content=store.get_artifact(artifact))

        def read_cells(namespace, ref, fields):
            assert namespace == selection["namespace"] and ref == sheet_ref
            return [row for field in fields for row in rows if row["component"] == field]

        with pytest.raises(ContractError, match="intervention_inference_is_not_measurement_operand"):
            read_intervention_inputs(args, read_source=read_source, read_cells=read_cells, read_record=store.get)

        # The same saved sheet still supplies its underlying estimate and
        # variance. Reading those values does not establish A106 applicability.
        args["quantities"] = dict.fromkeys(args["quantities"])
        args["quantities"].update(
            effect={**selection, "component": "log_parameter_contrast"},
            effect_variance={**selection, "component": "log_contrast_noise_variance"})
        quantities = read_intervention_inputs(args, read_source=read_source,
            read_cells=read_cells, read_record=store.get)["quantities"]
        assert quantities["effect"]["value"] == pytest.approx(math.log(2))
        assert quantities["effect_variance"]["value"] == pytest.approx(.11)
        assert quantities["effect"]["measurement_keys"]
        assert quantities["effect_variance"]["measurement_keys"]


@pytest.mark.parametrize("family,components,measurement", [
    ("rate", ("signed_profile_log_ratio", "source_signed_index"), "rate_difference"),
    ("assay", ("source_profile_log_ratio", "source_presence_index"), "corrected_activity"),
])
@pytest.mark.parametrize("component_index", [0, 1])
@pytest.mark.parametrize("role", ["effect", "effect_variance", "assertion_prediction", "alternative_prediction"])
def test_saved_rate_and_assay_scores_are_not_measurements(
        tmp_path, family, components, measurement, component_index, role):
    if family == "rate":
        from test_literature_rate_storage import setup_store
        from gene_annotation_episode.literature_rate_storage import LiteratureRateRepository as Repository
    else:
        from test_literature_assay_integration import setup_store
        from gene_annotation_episode.literature_assay_storage import LiteratureAssayRepository as Repository
    store, context, arguments = setup_store(tmp_path)
    with store:
        if family == "rate":
            arguments.update(dependence="independent", observation_model="independent_normal_groups")
        repo = Repository(store, context.run_id)
        outcome = repo.populate(context, arguments, "saved-inference")
        rows = repo.project_cells([outcome["result"]["sheet_ref"]],
            permitted_record_refs=outcome["record_refs"], components=[*components, measurement])
        component = components[component_index]
        score = next(row for row in rows if row["component"] == component)
        assert score["value"] is not None and math.isfinite(score["value"])
        args, read, selection = intervention_reader(store, "literature_" + family + "_cells", rows)
        args["quantities"][role] = {**selection, "component": component}
        with pytest.raises(ContractError, match="intervention_inference_is_not_measurement_operand"):
            read()
        args["quantities"] = dict.fromkeys(args["quantities"])
        args["quantities"]["effect"] = {**selection, "component": measurement}
        operand = read()["quantities"]["effect"]
        assert operand["status"] == "point" and operand["measurement_keys"]
        assert math.isfinite(operand["value"])


def controlled_response_rows(store):
    from gene_annotation_episode.episode_bindings import BindingContext
    from gene_annotation_episode import literature_controlled_response_storage as storage

    fixture = json.loads((Path(__file__).parent / "fixtures/a106_source_components/controlled_response_source_case.json").read_text())
    references = {}
    for source in fixture["sources"]:
        artifact = store.artifact(bytes.fromhex(source["content_hex"]))
        references[source["source_ref"]] = store.put("source", dict(
            provider="synthetic_a106_controlled_response", accession=source["source_ref"], uri=None,
            artifact_ref=artifact, text_ref=artifact, request_ref=None, version=None,
            retrieved_at=None), origin="caller")["id"]

    def remap(value):
        if isinstance(value, dict):
            return {key: remap(child) for key, child in value.items()}
        if isinstance(value, list):
            return [remap(child) for child in value]
        return references.get(value, value) if isinstance(value, str) else value

    args = remap(fixture["selection"])
    args.update(version="controlled_response_source_selection_v3", companion_readings=[],
        joint_reading_assignments=[], joint_scopes=[], reading_reconciliations=[], local_pair_assignments=[])
    assignment = dict(source_ref=args["source_ref"],
        requested_controlled_response_components=list(storage.COMPONENTS),
        requested_controlled_response_views=["native_raw", "final"])
    context = BindingContext("controlled-inference-run", "controlled-inference-child", "literature_page",
        (("literature_page", "fixture"),), store.validate_scope(), assignment, {}, tuple(references.values()))
    repo = storage.LiteratureControlledResponseRepository(store, context.run_id, evidence_origin="synthetic_fixture")
    return repo.populate_v3(context, args, "saved-controlled-inference")["result"]["cells"]


@pytest.mark.parametrize("component", ["source_profile_log_ratio", "source_signed_index"])
@pytest.mark.parametrize("role", ["effect", "effect_variance", "assertion_prediction", "alternative_prediction"])
def test_scoped_component_key_cannot_hide_a_saved_inference(tmp_path, component, role):
    from gene_annotation_episode.state import Store

    with Store(tmp_path) as store:
        store.create_problem(raw_sequence="ATGGCT", molecule="dna")
        rows = controlled_response_rows(store)
        selected = next(row for row in rows if row["component_key"] == "final:" + component)
        assert selected["component"] == component
        args, read, selection = intervention_reader(store, "literature_controlled_response_component_cells", rows)
        args["quantities"][role] = {**selection, "component": selected["component_key"]}
        with pytest.raises(ContractError, match="intervention_inference_is_not_measurement_operand"):
            read()
        raw = next(row for row in rows if row["component_key"] == "raw:protein_condition1:primary")
        args["quantities"] = dict.fromkeys(args["quantities"])
        args["quantities"]["effect"] = {**selection, "component": raw["component_key"]}
        operand = read()["quantities"]["effect"]
        assert operand["status"] == "point" and operand["measurement_keys"]
        assert operand["value"] == pytest.approx(raw["cell"]["value"])
