"""Paper/data identity through A106 final custody, using synthetic evidence.

These checks stipulate the correspondence; they do not test autonomous discovery
of that correspondence or demonstrate a biological numerical result.
"""
from copy import deepcopy
from dataclasses import replace

import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.literature_a106_subscore import COMPONENTS, REQUESTED
from gene_annotation_episode.literature_a106_subscore_storage import LiteratureA106SubscoreRepository
from gene_annotation_episode.literature_intervention_storage import LiteratureInterventionRepository
from gene_annotation_episode.state import Store
from test_intervention_analysis import DESEQ
from test_literature_a106_subscore import final_arguments
from test_literature_intervention_storage import intervention_fixture


PAPER = (
    "Synthetic Experiment A and the deposited geneA row describe the same original experiment.\n"
    "All scientific criteria and an estimated normal observation model are stipulated for this engineering test.\n"
    "Reported effect -2 log2_ratio; estimated variance 0.25 log2_ratio_squared.\n"
    "Fixed assertion prediction -1.5 log2_ratio; fixed alternative prediction 0 log2_ratio.\n"
)


def source(store, raw, accession, parents=()):
    artifact = store.artifact(raw, "text/plain")
    return store.put("source", dict(provider="synthetic_a106_paper_dataset", accession=accession,
        uri=None, artifact_ref=artifact, text_ref=artifact, request_ref=None, version=None,
        retrieved_at=None, parent_source_refs=list(parents)), origin="caller")["id"]


def received(context, *refs):
    return replace(context, received_record_refs=tuple(dict.fromkeys((*context.received_record_refs, *refs))))


def fixture(store):
    store.create_problem(raw_sequence="ATGGCT", molecule="dna")
    context, args = intervention_fixture(store)
    paper = source(store, PAPER, "paper", [args["source_ref"]])
    dataset = source(store, DESEQ, "dataset", [paper])

    def witness(text, start=0):
        offset = PAPER.index(text, start)
        return dict(source_ref=paper, representation="original", start=offset,
            end=offset + len(text), quote=text)

    def number(label, token, unit):
        fragment = f"{label} {token} {unit}"
        start = PAPER.index(fragment)
        return dict(kind="source_number", number=dict(witness=witness(fragment),
            number_start=len(label) + 1, number_end=len(label) + 1 + len(token)),
            unit=witness(unit, start + len(label) + len(token) + 2), origin="synthetic")

    args.update(source_ref=paper, quantity_kind="log2_fold_change", prediction_model=dict(
        kind="fixed_predictions_estimated_normal", variance_interpretation="estimated",
        support_refs=[args["experiment_ref"]]))
    args["quantities"] = dict.fromkeys(args["quantities"])
    args["quantities"].update(effect=number("Reported effect", "-2", "log2_ratio"),
        effect_variance=number("estimated variance", "0.25", "log2_ratio_squared"),
        assertion_prediction=number("Fixed assertion prediction", "-1.5", "log2_ratio"),
        alternative_prediction=number("fixed alternative prediction", "0", "log2_ratio"))
    context = received(context, paper, dataset)
    context = replace(context, assignment={**context.assignment, REQUESTED: list(COMPONENTS)})
    return context, args, paper, dataset, witness(PAPER.splitlines()[0])


def from_dataset(args, dataset):
    result = deepcopy(args)
    result["source_ref"] = dataset
    for role, metric in (("effect", "log2_fold_change"), ("effect_variance", "effect_variance")):
        result["quantities"][role] = dict(kind="native_analysis", source_ref=dataset,
            representation="deseq2", row_ordinal=0, feature_id="geneA", metric=metric)
    return result


def test_dataset_revision_reaches_parent_as_one_experiment_and_preserves_paper_history(tmp_path, monkeypatch):
    with Store(tmp_path) as store:
        context, args, paper, dataset, _ = fixture(store)
        assessments = LiteratureInterventionRepository(store, context.run_id)
        finals = LiteratureA106SubscoreRepository(store, context.run_id)
        first = assessments.populate(context, args, "paper-assessment")
        paper_sheet = first["result"]["sheet_ref"]
        context = received(context, paper_sheet)
        final_args = final_arguments(store, args, paper_sheet)
        first_final = finals.populate(context, final_args, "paper-final")
        paper_final = first_final["result"]["sheet_ref"]
        context = received(context, paper_final)
        paper_history = assessments.read(paper_sheet)
        final_history = finals.read(paper_final)

        revised = from_dataset(args, dataset)
        with pytest.raises(ContractError, match="intervention_latest_revision_required"):
            assessments.populate(context, revised, "dataset-without-predecessor")
        revised["experiment_assessment"].update(revises_sheet_ref=paper_sheet,
            revision_reason="Verify the published values against the deposited analysis row.")
        second = assessments.populate(context, revised, "dataset-assessment")
        dataset_sheet = second["result"]["sheet_ref"]
        context = received(context, dataset_sheet)
        heads = assessments.current_assessments()
        assert len(heads) == 1 and heads[0]["sheet_ref"] == dataset_sheet
        assert heads[0]["experiment_ref"] == args["experiment_ref"]
        assert {paper, dataset} <= set(store.get(dataset_sheet)["parent_source_refs"])

        final_args.update(revises_subscore_ref=paper_final,
            revision_reason="Use the dataset-backed revision of the same experiment.")
        with pytest.raises(ContractError, match="a106_current_assessment_required"):
            finals.populate(context, final_args, "stale-paper-final")
        duplicate = deepcopy(final_args)
        duplicate["experiments"].append(dict(experiment_ref=args["experiment_ref"],
            sheet_ref=dataset_sheet, missing_reason=None))
        with pytest.raises(ContractError, match="a106_duplicate_experiment"):
            finals.populate(context, duplicate, "paper-plus-dataset")

        final_args["experiments"][0]["sheet_ref"] = dataset_sheet
        result = finals.populate(context, final_args, "dataset-final")
        final_ref = result["result"]["sheet_ref"]
        cell = result["result"]["cells"][0]
        assert cell["value"] == pytest.approx(7.5)  # One ratio, never 15 from two representations.
        assert cell["input_origins"] == ["synthetic"]
        assert len(cell["experiments"]) == len(cell["selected_components"]) == 1
        assert cell["selected_components"][0]["sheet_ref"] == dataset_sheet
        assert {paper, dataset} <= set(cell["source_refs"])
        assert assessments.read(paper_sheet) == paper_history
        assert finals.read(paper_final) == final_history
        parent = replace(received(context, final_ref), episode_id="parent", role="annotation",
            path=(("annotation", "parent"),))
        finals.receive_cells(parent, result["result"]["cells"], "dataset-final-to-parent")
        delivered = finals.fact_cells(parent, [final_ref], components=list(COMPONENTS))
        assert delivered == result["result"]["cells"]

    def forbidden(*args, **kwargs):
        raise AssertionError("Saved parent receipt must not repeat scientific calculations")

    monkeypatch.setattr(LiteratureInterventionRepository, "read_inputs", forbidden)
    monkeypatch.setattr(LiteratureInterventionRepository, "grade", forbidden)
    monkeypatch.setattr("gene_annotation_episode.literature_a106_subscore_storage.finalize_a106", forbidden)
    with Store(tmp_path) as store:
        store.db.execute("PRAGMA query_only=ON")
        assert LiteratureA106SubscoreRepository(store, context.run_id).fact_cells(
            parent, [final_ref], components=list(COMPONENTS)) == delivered


def test_duplicate_download_cannot_be_summed_even_with_distinct_experiment_refs(tmp_path):
    with Store(tmp_path) as store:
        context, args, paper, dataset, correspondence = fixture(store)
        assessments = LiteratureInterventionRepository(store, context.run_id)
        first = assessments.populate(context, from_dataset(args, dataset), "first-download")
        first_sheet = first["result"]["sheet_ref"]

        duplicate = source(store, DESEQ, "second-download", [paper])
        assert duplicate != dataset
        assert store.get(duplicate)["artifact_ref"] == store.get(dataset)["artifact_ref"]
        original = store.get(args["experiment_ref"])
        alias = {key: deepcopy(value) for key, value in original.items()
            if key not in {"id", "record_type", "origin"}}
        alias["accession"] = "synthetic-duplicate-experiment-label"
        alias_ref = store.put("reference", alias, origin="caller")["id"]
        context = received(context, first_sheet, duplicate, alias_ref)
        second_args = from_dataset(args, duplicate)
        second_args["experiment_ref"] = alias_ref
        second_args["experiment_assessment"]["experiment_ref"] = alias_ref
        second = assessments.populate(context, second_args, "second-download")
        second_sheet = second["result"]["sheet_ref"]
        context = received(context, second_sheet)

        final_args = final_arguments(store, args, first_sheet)
        final_args["experiments"].append(dict(experiment_ref=alias_ref,
            sheet_ref=second_sheet, missing_reason=None))
        final_args["dependence"] = dict(status="independent",
            rationale="Deliberately incorrect independence claim to exercise the shared-observation check.",
            witnesses=[correspondence])
        finals = LiteratureA106SubscoreRepository(store, context.run_id)
        result = finals.populate(context, final_args, "duplicate-final")
        cell = result["result"]["cells"][0]
        assert all(row["value"] == pytest.approx(7.5) for row in cell["selected_components"])
        assert cell["value"] is None and cell["available_value"] is None
        assert "shared_observed_measurement" in cell["unavailable_reasons"]
        first_keys, second_keys = [row["evidence_measurement_keys"] for row in cell["selected_components"]]
        assert first_keys and first_keys == second_keys
        parent = replace(received(context, result["result"]["sheet_ref"]), episode_id="parent",
            role="annotation", path=(("annotation", "parent"),))
        finals.receive_cells(parent, result["result"]["cells"], "unresolved-duplicate-to-parent")
        assert finals.fact_cells(parent, [result["result"]["sheet_ref"]],
            components=list(COMPONENTS)) == result["result"]["cells"]
