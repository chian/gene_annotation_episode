"""Reported source spans through the existing summary and A106 operand path.

The text below is constructed engineering data, not a biological demonstration.
"""
from dataclasses import replace
import hashlib

import pytest

from gene_annotation_episode.domain import ContractError, validate_schema
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_perturbation_inputs import (
    LITERAL_FIELDS, PRIMITIVE_ORDER, perturbation_population_schema, read_perturbation_inputs,
)
from gene_annotation_episode.literature_perturbation_summary import (
    INTERPRETATION_BASIS_FIELDS, populate_summary_restoration,
)
from gene_annotation_episode.literature_perturbation_storage import LiteraturePerturbationRepository
from gene_annotation_episode.literature_perturbation_operands import LiteraturePerturbationOperandProjection
from test_literature_perturbation_integration import setup_case, source, witness


TEXT = ("Constructed matched growth endpoint in min. "
    "W: 12 ± 2; K: 3 ± 1; R: 11 ± 2. "
    "Arithmetic means and SD from n=4 independently grown cultures. "
    "Each arm was observed separately; pairing and between-arm covariance are unreported.").encode()
SOURCE = "source_" + "1" * 24


def arguments(ref=SOURCE, raw=TEXT, *, endpoint_unit="min"):
    def w(quote):
        return witness(ref, raw, quote)
    def number(quote, token):
        start = quote.index(token)
        return dict(witness=w(quote), number_start=start, number_end=start + len(token))
    measurements = dict.fromkeys(PRIMITIVE_ORDER)
    meaning = "Arithmetic means and SD from n=4 independently grown cultures."
    for role, value, spread in (("W", "12", "2"), ("K", "3", "1"), ("R", "11", "2")):
        quote = f"{role}: {value} ± {spread}"
        selected_spread = number(quote, spread)
        selected_spread.update(number_start=len(quote) - len(spread), number_end=len(quote))
        measurements[role] = dict(number=number(quote, value), value_scale="endpoint",
            summary_kind="arithmetic_mean", summary_scale="endpoint",
            uncertainty=dict(kind="sd", value=selected_spread, lower=None, upper=None,
                coverage=None, scale="endpoint"),
            count=dict(number=number("n=4", "4"), unit_kind="culture", independence="independent"),
            meaning_witnesses=[w(meaning)],
            interpretation_basis={name: "source_reported" for name in INTERPRETATION_BASIS_FIELDS})
    return dict(source_ref=ref, data_source_ref=None, source_kind="synthetic_fixture",
        literals=dict.fromkeys(LITERAL_FIELDS), design="selective_perturbation_restoration",
        measurement_status="validated_ratio_scale", same_endpoint_scope="yes", amount_role="unknown",
        orientation=1, interpretation_witnesses=[w("Constructed matched growth endpoint")],
        source_measurements=dict(endpoint_unit=w(endpoint_unit), exposure_unit=None, measurements=measurements))


def extract(args=None, raw=TEXT):
    def read(ref, representation):
        assert representation == "original"
        return dict(artifact_ref="artifact_" + hashlib.sha256(raw).hexdigest(), content=raw)
    return read_perturbation_inputs(arguments() if args is None else args, read_source=read)


def test_source_spans_produce_existing_summary_without_a_measurement_file():
    args = arguments()
    validate_schema(args, perturbation_population_schema())
    result = extract(args)
    cells = populate_summary_restoration(result, origin="synthetic")["cells"]
    assert result["data_source_ref"] is None
    assert result["values"]["W"] == 12 and result["values"]["K"] == 3
    assert result["values"]["A_reference"] is None and result["exposure_unit"] == "unreported"
    assert cells["W_mean_variance"]["value"] == 1
    assert cells["K_mean_variance"]["value"] == .25
    assert cells["perturbation_difference"]["value"] == 9
    assert cells["perturbation_mean_variance"]["value"] is None
    assert cells["reference_restoration_index"]["value"] is None
    trace = result["reported_number_sources"]["W"]
    assert [item["value"] for item in trace] == [12, 2, 4]
    assert trace[0]["selector"]["witness"]["quote"] == "W: 12 ± 2"


def test_source_identity_uses_numeric_bytes_not_quote_width_or_acquisition():
    first = extract()
    args = arguments("source_" + "2" * 24)
    args["source_measurements"]["measurements"]["W"]["number"] = dict(
        witness=witness(args["source_ref"], TEXT, "12"), number_start=0, number_end=2)
    second = extract(args)
    assert first["measurement_keys"] == second["measurement_keys"]
    assert first["primitive_observations"]["W"]["source_ref"] != second["primitive_observations"]["W"]["source_ref"]


def test_unknown_replication_keeps_reported_sd_without_creating_mean_variance():
    args = arguments()
    arm = args["source_measurements"]["measurements"]["W"]
    arm["count"]["independence"] = "unknown"
    arm["interpretation_basis"]["count_independence"] = "unresolved"
    cells = populate_summary_restoration(extract(args), origin="synthetic")["cells"]
    assert cells["W_reported_spread"]["value"] == 2
    assert cells["W_reported_count"]["value"] == 4
    assert cells["W_mean_variance"]["value"] is None


def test_reported_sem_keeps_its_mean_variance_without_dividing_by_n_again():
    raw = TEXT.replace(b"and SD", b"and SEM")
    args = arguments(raw=TEXT)
    for arm in args["source_measurements"]["measurements"].values():
        if arm is not None:
            arm["uncertainty"]["kind"] = "sem"
            arm["meaning_witnesses"] = [witness(SOURCE, raw,
                "Arithmetic means and SEM from n=4 independently grown cultures.")]
            arm["count"]["number"]["witness"] = witness(SOURCE, raw, "n=4")
    cells = populate_summary_restoration(extract(args, raw), origin="synthetic")["cells"]
    assert cells["W_mean_variance"]["value"] == 4
    assert cells["W_mean_variance"]["statistic_method"] == "reported_sem_squared"


def covariance_arguments(*, kind="mean_covariance", value="0.125", unit="min^2", ref=SOURCE,
        endpoint_unit="min"):
    statement = (f"The estimated covariance of the W and K means is {value} {unit}."
        if kind == "mean_covariance" else "W and K arm means were independently sampled.")
    raw = TEXT.replace(b"endpoint in min", ("endpoint in " + endpoint_unit).encode()) + b" " + statement.encode()
    args = arguments(ref, raw=raw, endpoint_unit=endpoint_unit)
    number = None
    if kind == "mean_covariance":
        start = statement.index(value)
        number = dict(witness=witness(ref, raw, statement), number_start=start,
            number_end=start + len(value))
    args["source_measurements"]["covariances"] = [dict(first="W", second="K", kind=kind,
        number=number, unit=witness(ref, raw, unit) if number is not None else None,
        variance_status="estimated" if number is not None else "known",
        interpretation_basis="source_reported",
        meaning_witnesses=[witness(ref, raw, statement)])]
    return args, raw


def test_reported_mean_covariance_reaches_contrast_variance_with_original_source():
    args, raw = covariance_arguments()
    result = extract(args, raw)
    calculated = populate_summary_restoration(result, origin="synthetic")
    assert calculated["cells"]["perturbation_mean_variance"]["value"] == 1
    assert calculated["cells"]["perturbation_mean_variance"]["variance_status"] == "estimated"
    assert calculated["cells"]["restoration_mean_variance"]["value"] is None
    trace = result["reported_number_sources"]["covariance_K_W"][0]
    assert trace["value"] == .125 and trace["raw_number"] == "0.125"
    assert result["summary_data"]["covariances"][0]["witnesses"][-1] == trace["selector"]["witness"]


def test_selected_independence_keeps_its_basis_and_does_not_fill_other_pairs():
    args, raw = covariance_arguments(kind="uncorrelated")
    args["source_measurements"]["covariances"][0]["interpretation_basis"] = "source_supported_inference"
    calculated = populate_summary_restoration(extract(args, raw), origin="synthetic")
    assert calculated["cells"]["perturbation_mean_variance"]["value"] == 1.25
    assert calculated["cells"]["restoration_mean_variance"]["value"] is None
    descriptors = calculated["covariance_descriptors"]
    assert descriptors[0]["interpretation_basis"] == "source_supported_inference"
    assert descriptors[0]["witnesses"][0]["quote"] == "W and K arm means were independently sampled."
    assert descriptors[1]["selection"] == descriptors[2]["selection"] == "unreported"


@pytest.mark.parametrize("rate_unit,covariance_unit,prediction_unit", [
    ("h^-1", "h^-2", "h^-1"), ("h⁻¹", "h⁻²", "h⁻¹"),
    ("per_h", "per_h_squared", "per_h"), ("1/h", "(1/h)^2", "1/h"),
    ("h^-1", "h^-2", "min^-1"),
])
def test_hourly_rates_keep_their_scale_through_summary_grading_and_parent_return(
        tmp_path, rate_unit, covariance_unit, prediction_unit):
    summary_grading_parent_return(tmp_path, rate_unit, covariance_unit, prediction_unit,
        canonical_unit="per_h", expected=None if prediction_unit == "min^-1" else 40)


def summary_grading_parent_return(tmp_path, endpoint_unit, covariance_unit, prediction_unit, *,
        canonical_unit, expected):
    """Exercise a native scale through summary, grading and actual parent receipt."""
    from gene_annotation_episode.literature_perturbation_operands import NAMESPACE
    from gene_annotation_episode.literature_intervention_storage import LiteratureInterventionRepository
    from gene_annotation_episode.literature_a106_subscore_storage import LiteratureA106SubscoreRepository
    from gene_annotation_episode.literature_a106_subscore import REQUESTED, COMPONENTS
    from test_literature_intervention_storage import intervention_fixture
    from test_literature_a106_subscore import final_arguments

    store, context, _ = setup_case(tmp_path)
    with store:
        _, raw = covariance_arguments(endpoint_unit=endpoint_unit, unit=covariance_unit)
        raw += (f" Fixed assertion prediction 8 {prediction_unit};"
            f" fixed alternative prediction 0 {prediction_unit}.").encode()
        document = source(store, raw)
        ref = document["id"]
        args, _ = covariance_arguments(endpoint_unit=endpoint_unit, unit=covariance_unit, ref=ref)
        context = replace(context, received_record_refs=(*context.received_record_refs, ref))
        writer = LiteraturePerturbationRepository(store, context.run_id)
        outcome = writer.populate(context, args, "unit-summary")
        sheet = outcome["result"]["sheet_ref"]
        context = replace(context, received_record_refs=(*context.received_record_refs, *outcome["record_refs"]))
        view = LiteraturePerturbationOperandProjection(store, context.run_id)
        rows = view.project_cells([sheet], permitted_record_refs=context.received_record_refs,
            components=["perturbation_difference", "perturbation_mean_variance"])
        # W-K=12-3; Var(W-K)=2²/4+1²/4-2*0.125. Preserve the native scale.
        assert [row["cell"]["value"] for row in rows] == [9, 1]
        assert [row["cell"]["unit"] for row in rows] == [canonical_unit, canonical_unit + "_squared"]
        assert writer.read(sheet)["extraction"]["reported_number_sources"]["W"][0]["value"] == 12

        grader, grading_args = intervention_fixture(store)
        grader = replace(grader, run_id=context.run_id,
            received_record_refs=tuple(dict.fromkeys((*grader.received_record_refs, *context.received_record_refs))))
        view.receive_cells(grader, rows, "unit-reader-return")
        def predicted(label, token):
            quote = f"{label} prediction {token} {prediction_unit}"
            number = quote.index(token)
            selected = witness(ref, raw, quote)
            unit_start = selected["start"] + len(quote[:number + len(token) + 1].encode())
            return dict(kind="source_number", origin="synthetic",
                number=dict(witness=selected, number_start=number, number_end=number + len(token)),
                unit=dict(source_ref=ref, representation="original", start=unit_start,
                    end=unit_start + len(prediction_unit.encode()), quote=prediction_unit))
        grading_args.update(quantity_kind="endpoint_difference",
            prediction_model=dict(kind="fixed_predictions_estimated_normal", variance_interpretation="estimated",
                support_refs=[grading_args["experiment_ref"]]))
        grading_args["quantities"].update(
            effect=dict(kind="received_component", namespace=NAMESPACE, sheet_ref=sheet,
                component="perturbation_difference"),
            effect_variance=dict(kind="received_component", namespace=NAMESPACE, sheet_ref=sheet,
                component="perturbation_mean_variance"),
            assertion_prediction=predicted("assertion", "8"), alternative_prediction=predicted("alternative", "0"))
        repo = LiteratureInterventionRepository(store, grader.run_id,
            read_cells=lambda ctx, namespace, selected, components: view.fact_cells(ctx, [selected], components=components))
        assessment = repo.populate(grader, grading_args, "unit-grade")["result"]["sheet_ref"]
        cells = repo.read(assessment)["sheet"]["cells"]
        assert cells["source_log_evidence_ratio"]["value"] == expected
        if expected is None:
            assert "prediction_unit_mismatch" in cells["source_log_evidence_ratio"]["reasons"]
        grader = replace(grader, received_record_refs=(*grader.received_record_refs, assessment),
            assignment={**grader.assignment, REQUESTED: list(COMPONENTS)})
        finals = LiteratureA106SubscoreRepository(store, grader.run_id)
        final_args = final_arguments(store, grading_args, assessment)
        if expected is None:
            final_args["conclusion"] = "Synthetic comparison remains unresolved because prediction units differ."
        final = finals.populate(grader, final_args, "unit-final")
        returned = final["result"]["cells"]
        parent = replace(grader, episode_id="unit-parent", role="annotation", path=(("annotation", "root"),),
            received_record_refs=(*grader.received_record_refs, *final["record_refs"]))
        finals.receive_cells(parent, returned, "unit-final-return")
        assert finals.fact_cells(parent, [final["result"]["sheet_ref"]], components=COMPONENTS) == returned
        assert returned[0]["value"] == expected


@pytest.mark.parametrize("bad", ["incompatible_unit", "missing_unit", "invented_number",
    "unselected_number", "duplicate_pair", "non_psd", "unit_source"])
def test_invalid_covariance_cannot_populate_a_contrast_variance(bad):
    args, raw = covariance_arguments(unit="fraction^2" if bad == "incompatible_unit" else "min^2",
        value="2" if bad == "non_psd" else "0.125")
    covariance = args["source_measurements"]["covariances"][0]
    if bad == "missing_unit":
        covariance["unit"] = None
    elif bad == "invented_number":
        covariance["number"]["value"] = 0
    elif bad == "unselected_number":
        covariance["kind"] = "uncorrelated"
    elif bad == "duplicate_pair":
        args["source_measurements"]["covariances"].append(dict(covariance, first="K", second="W"))
    elif bad == "unit_source":
        covariance["unit"]["source_ref"] = "source_" + "3" * 24
    with pytest.raises((ContractError, ExperimentalContractError)):
        populate_summary_restoration(extract(args, raw), origin="synthetic")


@pytest.mark.parametrize("bad", ["mixed_input", "partial_number", "invented_value", "false_quote", "unit_source", "censoring"])
def test_invalid_source_selections_do_not_become_measurements(bad):
    args = arguments()
    raw = TEXT
    arm = args["source_measurements"]["measurements"]["W"]
    if bad == "mixed_input":
        args["data_source_ref"] = "source_" + "3" * 24
    elif bad == "partial_number":
        arm["number"]["number_end"] -= 1
    elif bad == "invented_value":
        arm["number"]["value"] = 50
    elif bad == "false_quote":
        arm["number"]["witness"]["quote"] = "W: 13 ± 2"
    elif bad == "unit_source":
        args["source_measurements"]["endpoint_unit"]["source_ref"] = "source_" + "3" * 24
    else:
        raw = TEXT.replace(b"W: 12", b"W: <12")
        arm["number"] = dict(witness=witness(SOURCE, raw, "W: <12"), number_start=4, number_end=6)
        # Keep other offsets valid so rejection concerns censoring, not stale spans.
        args["source_measurements"]["measurements"] = dict.fromkeys(PRIMITIVE_ORDER)
        args["source_measurements"]["measurements"]["W"] = arm
    with pytest.raises((ContractError, ExperimentalContractError)):
        extract(args, raw)


@pytest.mark.parametrize("covariance_basis", [None, "source_reported", "conditional_assumption"])
def test_saved_summary_and_typed_operand_replay_retain_source_selection(tmp_path, monkeypatch, covariance_basis):
    store, context, _ = setup_case(tmp_path)
    with store:
        raw = TEXT if covariance_basis is None else covariance_arguments()[1]
        document = source(store, raw)
        args = arguments(document["id"]) if covariance_basis is None else covariance_arguments(ref=document["id"])[0]
        if covariance_basis is not None:
            args["source_measurements"]["covariances"][0]["interpretation_basis"] = covariance_basis
        context = replace(context, received_record_refs=(*context.received_record_refs, document["id"]))
        repo = LiteraturePerturbationRepository(store, context.run_id)
        outcome = repo.populate(context, args, "reported-summary")
        sheet = outcome["result"]["sheet_ref"]
        context = replace(context, received_record_refs=(*context.received_record_refs, *outcome["record_refs"]))
        saved = repo.read(sheet)
        assert saved["extraction"]["reported_number_sources"]["K"][0]["value"] == 3
        view = LiteraturePerturbationOperandProjection(store, context.run_id)
        rows = view.project_cells([sheet], permitted_record_refs=context.received_record_refs,
            components=["reference_endpoint", "W_mean_variance", "perturbation_mean_variance"])
        assert [row["cell"]["value"] for row in rows] == [12, 1, None if covariance_basis is None else 1]
        assert [row["cell"]["unit"] for row in rows] == ["min", "min_squared", "min_squared"]
        assert rows[0]["source_cell"]["unit"] == "minutes"
        if covariance_basis is not None:
            assert rows[-1]["source_cell"]["covariance_interpretations"][0]["interpretation_basis"] == covariance_basis
        assert ("conditional_covariance_assumption_unresolved" in rows[-1]["cell"]["qualifications"]) == (
            covariance_basis == "conditional_assumption")
        from gene_annotation_episode.literature_intervention_inputs import _intervention_unit
        assert _intervention_unit("minutes") == ("min", 1)
        parent = replace(context, episode_id="parent", role="annotation", path=(("annotation", "root"),))
        view.receive_cells(parent, rows, "source-return")
        def forbidden(*_a, **_k):
            raise AssertionError("Replay must use the original saved measurement")
        monkeypatch.setattr("gene_annotation_episode.literature_perturbation_storage.read_perturbation_inputs", forbidden)
        monkeypatch.setattr("gene_annotation_episode.literature_perturbation_storage.populate_source_summary_restoration", forbidden)
        store.db.execute("PRAGMA query_only=ON")
        assert repo.populate(context, args, "reported-summary") == outcome
        assert view.received_cells(parent) == rows
