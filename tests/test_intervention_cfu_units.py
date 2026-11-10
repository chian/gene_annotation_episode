"""CFU density keeps its scale through A106's source readers and score custody.

All numbers and model expectations here are engineered test inputs, not a
biological positive case or a prediction model inferred from a real experiment.
"""
from dataclasses import replace

import pytest

from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_intervention_storage import LiteratureInterventionRepository
from gene_annotation_episode.state import Store
from test_literature_intervention_storage import intervention_fixture
from test_literature_perturbation_integration import source, witness
from test_literature_perturbation_source import covariance_arguments, extract, summary_grading_parent_return


@pytest.mark.parametrize("endpoint,covariance,prediction", [
    ("CFU_per_mL", "CFU_per_mL_squared", "CFU_per_mL"),
    ("CFU/mL", "(CFU/mL)^2", "CFU/mL"),
    ("CFU/ml", "CFU^2/ml^2", "CFU/ml"),
    ("CFU ml−1", "(CFU ml−1)^2", "CFU ml−1"),
    ("CFU mL⁻¹", "(CFU mL⁻¹)²", "CFU mL⁻¹"),
    ("CFU mL^-1", "(CFU mL^-1)^2", "CFU/mL"),
    ("CFU/mL", "(CFU/mL)^2", "count"),
])
def test_density_summary_and_predictions_reach_parent_without_rescaling(
        tmp_path, endpoint, covariance, prediction):
    summary_grading_parent_return(tmp_path, endpoint, covariance, prediction,
        canonical_unit="CFU_per_mL", expected=None if prediction == "count" else 40)


@pytest.mark.parametrize("unit", ["CFU/mL^2", "CFU_per_mL"])
def test_summary_covariance_requires_the_squared_density_unit(unit):
    args, raw = covariance_arguments(endpoint_unit="CFU/mL", unit=unit)
    with pytest.raises(ExperimentalContractError, match="unsupported_perturbation_source_unit"):
        extract(args, raw)


@pytest.mark.parametrize("endpoint,variance,unavailable_reason", [
    ("CFU_per_mL", "CFU_per_mL_squared", None),
    ("CFU/mL", "(CFU/mL)^2", None),
    ("CFU ml−1", "CFU²/mL²", None),
    ("CFU/mL", "CFU/mL", "variance_unit_mismatch"),
    ("CFU/mL", "CFU/mL^2", "source_unit_unsupported"),
])
def test_direct_density_operands_require_variance_of_the_complete_density_unit(
        tmp_path, endpoint, variance, unavailable_reason):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence="ATGGCT", molecule="dna")
        context, args = intervention_fixture(store)
        values = {"effect": ("9", endpoint), "effect_variance": ("1", variance),
            "assertion_prediction": ("8", endpoint), "alternative_prediction": ("0", endpoint)}
        fragments = {role: f"{role} {number} {unit}" for role, (number, unit) in values.items()}
        raw = ("Constructed CFU density comparison. " + "; ".join(fragments.values()) + ".").encode()
        ref = source(store, raw)["id"]
        context = replace(context, received_record_refs=(*context.received_record_refs, ref))
        args["quantity_kind"] = "endpoint_difference"
        args["quantities"] = dict.fromkeys(args["quantities"])
        for role, (number, unit) in values.items():
            selected = witness(ref, raw, fragments[role])
            number_start = len(role) + 1
            unit_start = selected["start"] + len(fragments[role][:number_start + len(number) + 1].encode())
            args["quantities"][role] = dict(kind="source_number", origin="synthetic",
                number=dict(witness=selected, number_start=number_start, number_end=number_start + len(number)),
                unit=dict(source_ref=ref, representation="original", start=unit_start,
                    end=unit_start + len(unit.encode()), quote=unit))
        repo = LiteratureInterventionRepository(store, context.run_id)
        outcome = repo.populate(context, args, "direct-cfu-density")
        saved = repo.read(outcome["result"]["sheet_ref"])
        quantities = saved["extraction"]["quantities"]
        assert quantities["effect"]["value"] == 9
        assert quantities["effect"]["unit"] == "CFU_per_mL"
        assert quantities["effect"]["measurement_keys"]
        score = saved["sheet"]["cells"]["source_log_evidence_ratio"]
        if unavailable_reason is None:
            assert quantities["effect_variance"]["value"] == 1
            assert quantities["effect_variance"]["unit"] == "CFU_per_mL_squared"
            assert score["value"] == 40
        else:
            assert score["value"] is None
            if unavailable_reason == "source_unit_unsupported":
                assert quantities["effect_variance"]["reason"] == unavailable_reason
            else:
                assert unavailable_reason in score["reasons"]
