"""Engineered native tables test arithmetic and custody, not live experiments."""
from copy import deepcopy
import hashlib

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import intervention_analysis_native as native
from gene_annotation_episode import bvbrc_intervention_contracts as contracts
from gene_annotation_episode import bvbrc_intervention_bundle_adapter as shared
from gene_annotation_episode import bvbrc_tnseq_bundle_adapter as tnseq
from gene_annotation_episode import bvbrc_rnaseq_bundle_adapter as rnaseq
from gene_annotation_episode import bvbrc_application_returns as returns
from gene_annotation_episode.bvbrc_appservice_adapters import bind_adapters
from gene_annotation_episode.execution_contracts import canonical
from test_bvbrc_annotation_bundle_adapter import arguments as annotation_arguments

TRANSIT = (b"#Resampling\n#Normalization: TTR; pseudocount=1\n"
    b"#Orf\tName\tDesc\tSites\tMean Ctrl\tMean Exp\tlog2FC\tSum Ctrl\tSum Exp\tDelta Mean\tp-value\tAdj. p-value\n"
    b"geneA\talpha\tSynthetic fixture\t12\t80\t20\t-1.95\t960\t240\t-60\t0.001\t0.02\n")
DESEQ = (b"Gene_Name\tbaseMean\tlog2FoldChange\tlfcSE\tstat\tpvalue\tpadj\n"
    b"geneA\t20\t-2\t0.5\t-4\t0.0001\t0.001\n"
    b"geneB\t0\tNA\tNA\tNA\tNA\tNA\n")


def arguments(application="TnSeq", raw=None, representation=None):
    raw = (TRANSIT if application == "TnSeq" else DESEQ) if raw is None else raw
    representation = representation or ("transit_resampling" if application == "TnSeq" else "deseq2")
    args = annotation_arguments(raw=raw)
    task = args["bundle"]["original_task"]
    task.update(required_application_id=application, native_application_id=application,
        submitted_parameters={"reference_genome_id": "fixture.reference", "contrasts": [[0, 1]],
            "recipe": "resampling" if application == "TnSeq" else "HTSeq-DESeq"})
    args["bundle"]["artifacts"][0]["declared_format"]["format"] = "tsv"
    args["parameters"].update(version=contracts.PARAMETERS_VERSION, application_id=application)
    args["parameters"]["documents"][0]["representation"] = representation
    args["requested_form"] = contracts.requested_form_schema([dict(field="measurements", selection=dict(
        version=contracts.SELECTION_VERSION, document_id="genome", kind="records", ordinals=None,
        offset=0, limit=100, member_names=None))])
    return args


def consume(args):
    return (tnseq if args["parameters"]["application_id"] == "TnSeq" else rnaseq).consume_bundle(**args)


def test_transit_preserves_signed_native_effects_statistics_parameters_and_source_locations():
    args = arguments()
    result = consume(args)
    assert result["adapter_id"] == "bvbrc_tnseq" and result["status"] == "ok"
    fact = result["facts"]["measurements"]
    row = fact["records"][0]["value"]
    assert row["measurements"]["mean_difference"]["value"] == -60
    assert row["measurements"]["log2_fold_change"]["value"] == -1.95
    assert row["measurements"]["adjusted_p_value"]["value"] == .02
    assert "effect_variance" not in row["measurements"]
    loc = row["source_location"]
    assert TRANSIT[loc["byte_start"]:loc["byte_end"]] == (loc["text"] + loc["ending"]).encode()
    assert fact["context"]["original_task"] == args["bundle"]["original_task"]
    assert fact["record_accounting"]["intended_population_complete"] is None


def test_deseq_estimated_variance_uses_reported_se_and_na_does_not_become_zero():
    result = consume(arguments("RNASeq"))
    assert result["adapter_id"] == "bvbrc_rnaseq" and result["status"] == "partial"
    first, missing = [row["value"]["measurements"] for row in result["facts"]["measurements"]["records"]]
    assert first["effect_variance"]["value"] == .25
    assert first["effect_variance"]["unit"] == "log2_ratio_squared"
    assert missing["effect_variance"]["value"] is None
    assert missing["log2_fold_change"]["state"] == "missing"
    assert missing["base_mean"]["value"] == 0


@pytest.mark.parametrize("raw,metric,state", [
    (DESEQ.replace(b"0.5", b"-0.5"), "standard_error", "outside_native_range"),
    (DESEQ.replace(b"0.5", b"1e300"), "effect_variance", "numerical_range"),
    (DESEQ.replace(b"0.5", b"1e-999"), "standard_error", "numerical_range"),
    (DESEQ.replace(b"0.001\n", b"1.1\n"), "adjusted_p_value", "outside_native_range"),
    (DESEQ.replace(b"0.5\t", b"Inf\t"), "standard_error", "invalid_number"),
    (DESEQ.replace(b"0.5\t-4", b"0.5\textra\t-4"), "log2_fold_change", "row_width_conflict"),
])
def test_invalid_or_ambiguous_statistics_are_retained_without_a_numeric_operand(raw, metric, state):
    result = consume(arguments("RNASeq", raw=raw))
    value = result["facts"]["measurements"]["records"][0]["value"]["measurements"][metric]
    assert value["state"] == state and value["value"] is None and result["status"] == "partial"


def test_duplicate_headers_and_rows_do_not_create_independent_experiments():
    raw = DESEQ.replace(b"padj\n", b"pvalue\n")
    args = arguments("RNASeq", raw=raw)
    result = consume(args)
    first = result["facts"]["measurements"]["records"][0]["value"]["measurements"]
    assert first["p_value"]["state"] == "column_ambiguous"
    assert first["adjusted_p_value"]["state"] == "column_missing"
    assert "experiment_count" not in result["sheet"]


@pytest.mark.parametrize("application", ["TnSeq", "RNASeq"])
def test_saved_projection_replays_without_original_files_parser_or_calculator(application, monkeypatch):
    args = arguments(application)
    result = consume(args)
    def forbidden(*a, **k):
        raise AssertionError("saved projection reacquired or recalculated")
    for module, name in ((shared, "parse_intervention_artifact"), (native, "parse_intervention_artifact"),
                         (shared, "calculate_intervention_components"), (native, "calculate_intervention_components")):
        monkeypatch.setattr(module, name, forbidden)
    monkeypatch.setattr("builtins.open", forbidden)
    assert shared.validate_saved_intervention_facts(result["facts"], sheet=result["sheet"],
        components=result["components"], parameters=args["parameters"], requested_form=args["requested_form"]) == result["facts"]


def test_partial_capture_and_missing_selected_artifact_remain_partial():
    args = arguments()
    args["bundle"]["artifacts"][0]["transfer"]["object_complete"] = "unknown"
    assert consume(args)["status"] == "partial"
    args["bundle"]["artifacts"] = []
    result = consume(args)
    assert result["status"] == "partial"
    assert result["facts"]["measurements"]["records"][0]["state"] == "source_unavailable"


def test_dedicated_adapters_reject_wrong_application_and_pin_the_implementation():
    with pytest.raises(ValueError, match="application_required"):
        tnseq.consume_bundle(**arguments("RNASeq"))
    for adapter in (tnseq, rnaseq):
        config = dict(adapter_id=adapter.ADAPTER_ID, adapter_version="1", implementation_sha256=adapter.implementation_sha256())
        assert bind_adapters([config])[(adapter.ADAPTER_ID, "1")][0] is adapter


def publication(args, result):
    def content(value, char):
        raw = canonical(value).encode()
        digest = hashlib.sha256(raw).hexdigest()
        return dict(source_ref="source_" + char * 24, artifact_field="artifact_ref", artifact_ref="artifact_" + digest,
            sha256=digest, byte_count=len(raw))
    selector = dict(version="bvbrc_appservice_result_selector_v1", endpoint="requested_projection",
        requirements=[dict(requirement_id="native-genome", role="caller_selected_gto", required=True,
            declared_format=deepcopy(args["bundle"]["artifacts"][0]["declared_format"]),
            producer_rule_evidence=None, exact_object=None)],
        adapter=dict(adapter_id=result["adapter_id"], adapter_version="1", parameters=args["parameters"]),
        requested_schema=args["requested_form"], supplied_metadata=[], supplied_contents=[], supplied_capabilities=[])
    saved = {key: deepcopy(result[key]) for key in ("adapter_id", "adapter_version", "status", "facts", "missing_requirements", "diagnostics")}
    saved.update(sheet_content=content(result["sheet"], "a"), components_content=content(result["components"], "b"))
    ref = "source_" + "f" * 24
    return dict(version=returns.RESULT_VERSION, source_ref=ref, reference=ref,
        publication=dict(bundle_content=content(args["bundle"], "f"), result_record_refs=[ref], adapter_result=saved),
        publication_inputs=dict(selector=selector, adapter=selector["adapter"], adapter_implementation_sha256=tnseq.implementation_sha256()),
        assignment=dict(selector=selector), record_refs=[ref], bundle=args["bundle"])


@pytest.mark.parametrize("application", ["TnSeq", "RNASeq"])
def test_saved_parent_return_is_typed_and_rejects_changed_measurements(application):
    args = arguments(application)
    result = consume(args)
    body = publication(args, result)
    values = returns.project_application_facts(body, sheet=result["sheet"], components=result["components"])
    schema = returns.application_fact_sources()[returns.FACT_SOURCE]["report_schema"]
    Draft202012Validator(schema).validate(values[returns.FACT_SOURCE])
    body["publication"]["adapter_result"]["facts"]["measurements"]["records"][0]["value"]["measurements"]["log2_fold_change"]["value"] = 25
    with pytest.raises(ValueError, match="saved_facts_conflict"):
        returns.project_application_facts(body, sheet=result["sheet"], components=result["components"])
