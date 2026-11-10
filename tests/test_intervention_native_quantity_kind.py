"""Native column meanings must survive the A106 input reader.

Engineered TRANSIT/DESeq2 tables exercise both retained files and admitted
application rows. They are not biological evidence or service execution.
"""
from copy import deepcopy

import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.literature_intervention_inputs import read_intervention_inputs
from gene_annotation_episode.state import Store
from test_intervention_analysis import DESEQ, TRANSIT, arguments, consume, publication, returns
from test_literature_intervention_storage import intervention_fixture


def inputs(store, route, application, metric, quantity_kind, *, raw=None):
    store.create_problem(raw_sequence="ATGGCT", molecule="dna")
    _, args = intervention_fixture(store)
    args.update(quantity_kind=quantity_kind, prediction_model=None)
    args["quantities"] = dict.fromkeys(args["quantities"])
    selection = dict(kind=route, representation="deseq2" if application == "RNASeq" else "transit_resampling",
        row_ordinal=0, feature_id="geneA", metric=metric)
    raw = (DESEQ if application == "RNASeq" else TRANSIT) if raw is None else raw
    rows = []
    if route == "native_analysis":
        artifact = store.artifact(raw, "text/plain")
        selection["source_ref"] = store.put("source", dict(provider="synthetic_native_quantity_test",
            accession=None, uri=None, artifact_ref=artifact, text_ref=artifact, request_ref=None,
            version=None, retrieved_at=None), origin="caller")["id"]
    else:
        adapter_args = arguments(application, raw=raw)
        result = consume(adapter_args)
        rows = returns.project_application_facts(publication(adapter_args, result),
            sheet=result["sheet"], components=result["components"])[returns.FACT_SOURCE]
        selection.update(sheet_ref=rows[0]["source_ref"], field=rows[0]["field"])
    args["quantities"]["effect"] = selection

    def read_source(ref, representation):
        record = store.get(ref)
        assert record["record_type"] == "source"
        artifact = record["artifact_ref" if representation == "original" else "text_ref"]
        return dict(artifact_ref=artifact, content=store.get_artifact(artifact))

    def read_cells(namespace, ref, fields):
        assert route == "application_analysis"
        assert namespace == returns.FACT_SOURCE
        assert ref == rows[0]["source_ref"] and fields == [rows[0]["field"]]
        return rows

    def read(selected):
        return read_intervention_inputs(selected, read_source=read_source,
            read_cells=read_cells, read_record=store.get)

    return args, read


@pytest.mark.parametrize("route", ["native_analysis", "application_analysis"])
@pytest.mark.parametrize("application,metric,kind,value,unit,wrong_kind", [
    ("RNASeq", "base_mean", "native_endpoint", 20, "normalized_count", "endpoint_difference"),
    ("TnSeq", "reference_mean", "native_endpoint", 80, "mean_insertion_count", "endpoint_difference"),
    ("TnSeq", "intervention_mean", "native_endpoint", 20, "mean_insertion_count", "endpoint_ratio"),
    ("TnSeq", "mean_difference", "endpoint_difference", -60, "mean_insertion_count", "native_endpoint"),
    ("TnSeq", "log2_fold_change", "log2_fold_change", -1.95, "log2_ratio", "fitness_difference"),
    ("RNASeq", "log2_fold_change", "log2_fold_change", -2, "log2_ratio", "endpoint_ratio"),
])
def test_native_column_cannot_be_relabelled_as_another_quantity(
        tmp_path, route, application, metric, kind, value, unit, wrong_kind):
    with Store(tmp_path) as store:
        args, read = inputs(store, route, application, metric, kind)
        observed = read(args)["quantities"]["effect"]
        assert observed["value"] == value and observed["unit"] == unit
        assert observed["status"] == "point" and observed["measurement_keys"]
        args["quantity_kind"] = wrong_kind
        with pytest.raises(ContractError, match="intervention_analysis_quantity_kind_mismatch"):
            read(args)


@pytest.mark.parametrize("route", ["native_analysis", "application_analysis"])
def test_deseq_variance_remains_bound_to_the_logarithmic_contrast(tmp_path, route):
    with Store(tmp_path) as store:
        args, read = inputs(store, route, "RNASeq", "log2_fold_change", "log2_fold_change")
        args["quantities"]["effect_variance"] = {
            **deepcopy(args["quantities"]["effect"]), "metric": "effect_variance"}
        quantities = read(args)["quantities"]
        assert quantities["effect"]["value"] == -2
        variance = quantities["effect_variance"]
        assert variance["value"] == .25 and variance["unit"] == "log2_ratio_squared"
        assert variance["measurement_keys"] == quantities["effect"]["measurement_keys"]
        assert "estimated_variance_from_reported_deseq2_standard_error" in variance["qualifications"]
        args["quantities"]["effect"].update(metric="base_mean")
        args["quantity_kind"] = "native_endpoint"
        with pytest.raises(ContractError, match="intervention_analysis_quantity_kind_mismatch"):
            read(args)


@pytest.mark.parametrize("route", ["native_analysis", "application_analysis"])
@pytest.mark.parametrize("second_feature", ["geneA", "geneB"])
def test_deseq_variance_cannot_move_between_rows_even_with_the_same_gene_name(
        tmp_path, route, second_feature):
    raw = DESEQ.replace(b"geneB\t0\tNA\tNA\tNA\tNA\tNA\n",
        (second_feature + "\t40\t1\t0.75\t1.333333\t0.18\t0.3\n").encode())
    with Store(tmp_path) as store:
        args, read = inputs(store, route, "RNASeq", "log2_fold_change", "log2_fold_change", raw=raw)
        original_effect = deepcopy(args["quantities"]["effect"])
        other_effect = {**original_effect, "row_ordinal": 1, "feature_id": second_feature}
        args["quantities"].update(effect=other_effect,
            effect_variance={**other_effect, "metric": "effect_variance"})
        paired = read(args)["quantities"]
        assert paired["effect"]["value"] == 1
        assert paired["effect_variance"]["value"] == .5625
        assert paired["effect"]["measurement_keys"] == paired["effect_variance"]["measurement_keys"]

        args["quantities"]["effect"] = original_effect
        with pytest.raises(ContractError, match="intervention_variance_estimate_mismatch"):
            read(args)
