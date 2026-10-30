"""Common numerical authority across native correspondence entry paths."""
from copy import deepcopy
import json

import pytest

from gene_annotation_episode import alignment_correspondence as common
from gene_annotation_episode import biopython_pairwise_grader as bio
from gene_annotation_episode import blast_pairwise_grader as blast
from gene_annotation_episode.tool_grading_artifacts import (
    retain_tool_grading, source_tool_gradings, validate_tool_correspondence,
)


def bio_native():
    return {"native_format": "biopython_pairwise_native_v2", "aligned": True,
        "mode": "global", "query_length": 4, "reference_length": 5,
        "matrix": "NUC.4.4", "gap_open": -10, "gap_extend": -0.5,
        "native_score": 8, "aligned_query": "AC-GT", "aligned_reference": "ACAGT",
        "query_interval": [0, 4], "reference_interval": [0, 5],
        "coordinates": [[0, 2, 2, 4], [0, 2, 3, 5]]}


def blast_hsp():
    return {"qseq": "AC-GT", "hseq": "ACAGT", "align_len": 5,
        "identity": 4, "gaps": 1, "query_from": 1, "query_to": 4,
        "hit_from": 1, "hit_to": 5, "score": 12, "bit_score": 8, "evalue": 0}


def normalized(hsps):
    return {"schema": "blast_normalized_result_v1", "mode": "pairwise", "resource": "local",
        "format": "json2", "query": {"id": "q", "title": "q", "length": 4},
        "search": {"program": "blastn", "hit_array_present": True},
        "hits": [{"length": 5, "hsps": hsps, "descriptions": [], "unpaired_metadata": {}}],
        "native": {}, "issues": []}


def test_equivalent_bio_and_blast_use_one_sheet_definition_and_final_calculator():
    first = bio.grade_biopython_pairwise(bio_native(), molecule="dna", _retain_correspondence=True)
    legacy, sheet, calculated = blast.alignment_component_artifacts(blast_hsp(), program="blastn",
        query_length=4, reference_length=5)
    native = first["correspondence"]["instances"][0]
    assert native["sheet"]["schema"] == sheet["schema"] == common.SHEET_SCHEMA
    assert native["components"]["definitions"] == calculated["definitions"]
    for field in ("counts", "paired_units", "aligned_units", "span_positions", "fractions"):
        assert native["components"]["rows"][0][field] == calculated["rows"][0][field]
    row = calculated["rows"][0]
    assert row["counts"]["substituted_positions"] == 0
    assert row["fractions"]["paired_identity"] == 1
    assert row["fractions"]["alignment_identity"] == 4 / 5
    assert row["fractions"]["reference_paired_coverage"] == 4 / 5
    assert row["fractions"]["reference_aligned_coverage"] == 1
    assert legacy["counts"]["paired_reference_positions"] == 4
    assert sheet["rows"][0]["measurement_input"]["kind"] == "validated_saved_counts"
    assert set(sheet["rows"][0]["measurement_input"]) == {"kind", "basis", "counts"}


def test_native_fallback_and_conflicts_remain_distinct_from_literal_counts():
    hsp = blast_hsp(); hsp["identity"] = 5
    legacy, _, calculated = blast.alignment_component_artifacts(hsp, program="blastn", query_length=4, reference_length=5)
    assert legacy["reported_counts"]["identity"] == 5
    assert calculated["rows"][0]["counts"]["identical_positions"] == 4
    assert any(issue["code"] == "reported_count_traceback_conflict" for issue in legacy["issues"])
    hsp = {"identity_percent": 80, "query_from": 1, "query_to": 4, "hit_from": 1, "hit_to": 5}
    legacy, sheet, calculated = blast.alignment_component_artifacts(hsp, program="blastn", query_length=4, reference_length=5)
    assert calculated["rows"][0]["counts"]["substituted_positions"] is None
    assert calculated["rows"][0]["fractions"]["alignment_identity"] == 0.8
    assert calculated["rows"][0]["fractions"]["query_paired_coverage"] is None
    assert sheet["rows"][0]["measurement_input"]["basis"] == "native_reported"
    assert legacy["endpoint_spans"]["query"]["positions"] == 4


def test_missing_and_explicit_zero_do_not_manufacture_saved_tracebacks():
    missing = bio_native(); missing.pop("aligned_query"); missing.pop("aligned_reference")
    unavailable = bio.grade_biopython_pairwise(missing, molecule="dna", _retain_correspondence=True)
    zero = bio_native(); zero["aligned"] = False
    for key in ("aligned_query", "aligned_reference", "coordinates", "query_interval", "reference_interval"):
        zero.pop(key)
    absent = bio.grade_biopython_pairwise(zero, molecule="dna", _retain_correspondence=True)
    for result, kind, count in ((unavailable, "unavailable", None), (absent, "explicit_no_alignment", 0)):
        instance = result["correspondence"]["instances"][0]
        assert instance["sheet"]["rows"][0]["measurement_input"] == {"kind": kind}
        assert instance["components"]["rows"][0]["counts"]["paired_positions"] is count
    assert unavailable["scores"]["query_paired_coverage"] is None
    assert absent["scores"]["query_paired_coverage"] == 0
    assert absent["scores"]["paired_identity"] is None


def test_historical_substitution_cell_is_a_saved_fact_and_new_values_use_common_output():
    from gene_annotation_episode.native_blast_result_worker import _hsp_values
    legacy, _, calculated = blast.alignment_component_artifacts(blast_hsp(), program="blastn",
        query_length=4, reference_length=5)
    assert _hsp_values(legacy, calculated["rows"][0])["substituted_positions"] == 0
    archived = {"substituted_positions": 17}
    assert _hsp_values(legacy, archived_values=archived)["substituted_positions"] == 17
    assert archived == {"substituted_positions": 17}
    with pytest.raises(ValueError, match="common_hsp_components_required"):
        _hsp_values(legacy)


def test_qualified_reference_denominator_does_not_replace_native_span_bound():
    hsp = blast_hsp(); hsp["hit_to"] = 6
    legacy, sheet, calculated = blast.alignment_component_artifacts(hsp, program="blastn",
        query_length=4, reference_length=None, qualification={"native_reference_bound": 5})
    assert legacy["denominators"]["reference_length"] is None
    assert legacy["geometry_available"] is False
    assert sheet["rows"][0]["paired_lengths"]["reference"] is None
    assert calculated["rows"][0]["fractions"]["reference_paired_coverage"] is None
    assert any(issue["code"] == "coordinates_outside_operand" for issue in legacy["issues"])
    hsp = blast_hsp(); hsp["query_to"] = 3
    legacy, sheet, calculated = blast.alignment_component_artifacts(hsp, program="blastn",
        query_length=4, reference_length=None, qualification={"native_reference_bound": 5})
    assert sheet["operands"]["reference"]["length"] is None
    assert sheet["rows"][0]["span_inputs"]["reference"]["length"] == 5
    assert calculated["rows"][0]["fractions"]["reference_span_coverage"] == 1
    assert calculated["rows"][0]["fractions"]["reference_paired_coverage"] is None


def test_observed_union_partial_population_and_conflicting_identity_are_separate():
    first, second = blast_hsp(), blast_hsp()
    second["hseq"] = "TCAGT"; second["identity"] = 3
    legacy, sheet, calculated = blast.build_pairwise_artifacts(normalized([first, second]))
    assert legacy["union"]["counts"]["paired_query_positions"] == 4
    assert legacy["union"]["fractions"]["paired_identity"] is None
    assert calculated["union"]["counts"]["conflicting_mapping_count"] > 0
    assert calculated["union"]["counts"]["identical_mapping_group_count"] == 1
    sheet["population"]["original_rows_complete"] = False
    sheet["selected_intervals"]["query"] = [0, 4]
    partial = common.calculate_correspondence_components(sheet)
    assert partial["union"]["fractions"]["query_observed_coverage"] == 1
    assert partial["union"]["fractions"]["query_original_complete_coverage"] is None
    assert partial["selected"]["query"]["observed_numerator"] == 4
    assert partial["selected"]["query"]["complete_value"] is None


@pytest.mark.parametrize("execution,producer,legacy,success", [
    ("completed", "complete", 1, 1), ("unknown", "complete", 1, None),
    ("completed", "unknown", 1, None), ("unknown", "unknown", 1, None),
    ("failed", "complete", None, None), ("completed", "incomplete", None, None),
])
def test_legacy_nonfailure_qualification_does_not_establish_execution_success(execution, producer, legacy, success):
    _, sheet, calculated = blast.build_pairwise_artifacts(normalized([blast_hsp()]),
        population={"original_rows_complete": True, "execution_state": execution,
            "producer_state": producer, "explicit_zero_result": False},
        selected_intervals={"query": [0, 4], "reference": None})
    selected = calculated["selected"]["query"]
    assert selected["execution_qualified_value"] == legacy
    assert selected["execution_success_value"] == success
    assert "unknown is not successful execution" in calculated["definitions"]["selected"]["query"]["missing_behavior"]
    sheet["population"]["original_rows_complete"] = False
    incomplete = common.calculate_correspondence_components(sheet)["selected"]["query"]
    assert incomplete["observed_numerator"] == 4
    assert incomplete["execution_success_numerator"] is None


@pytest.mark.parametrize("execution,producer", [("failed", "complete"), ("completed", "incomplete")])
def test_explicit_zero_cannot_override_known_failed_or_incomplete_population(execution, producer):
    native = normalized([]); native["hits"] = []
    with pytest.raises(ValueError, match="explicit_zero_population_conflict"):
        blast.build_pairwise_artifacts(native, population={"original_rows_complete": True,
            "execution_state": execution, "producer_state": producer, "explicit_zero_result": True},
            selected_intervals={"query": [0, 4], "reference": None})


def test_explicit_zero_rejects_positive_rows_and_known_complete_zero_keeps_its_denominator():
    population = {"original_rows_complete": True, "execution_state": "completed",
        "producer_state": "complete", "explicit_zero_result": True}
    with pytest.raises(ValueError, match="explicit_zero_population_conflict"):
        blast.build_pairwise_artifacts(normalized([blast_hsp()]), population=population)
    native = normalized([]); native["hits"] = []
    _, sheet, calculated = blast.build_pairwise_artifacts(native, population=population,
        selected_intervals={"query": [0, 4], "reference": None})
    selected = calculated["selected"]["query"]
    assert selected["denominator"] == 4
    assert selected["execution_qualified_value"] == selected["execution_success_value"] == 0
    sheet["population"].update(execution_state="unknown", producer_state="unknown")
    unknown = common.calculate_correspondence_components(sheet)["selected"]["query"]
    assert unknown["execution_qualified_value"] == 0
    assert unknown["execution_success_value"] is None


def test_selected_interval_respects_known_operand_axis_without_inventing_unknown_bounds():
    with pytest.raises(ValueError, match="interval_invalid:/selected_intervals/query"):
        blast.build_pairwise_artifacts(normalized([blast_hsp()]),
            selected_intervals={"query": [0, 8], "reference": None})
    native = normalized([blast_hsp()]); native["query"]["length"] = None
    _, sheet, calculated = blast.build_pairwise_artifacts(native,
        selected_intervals={"query": [0, 8], "reference": None})
    assert sheet["operands"]["query"]["length"] is None
    assert calculated["selected"]["query"]["denominator"] == 8
    assert calculated["selected"]["query"]["observed_numerator"] == 4


def test_admission_rejects_inconsistency_and_frozen_validation_never_recalculates(monkeypatch):
    grading = bio.grade_biopython_pairwise(bio_native(), molecule="dna", _retain_correspondence=True)
    companion = grading.pop("correspondence")
    validate_tool_correspondence(grading, companion, admission=True)
    corrupted = deepcopy(companion)
    corrupted["instances"][0]["components"]["rows"][0]["counts"]["substituted_positions"] = 99
    with pytest.raises(ValueError, match="saved_components_conflict"):
        validate_tool_correspondence(grading, corrupted, admission=True)
    def forbidden(*args, **kwargs):
        pytest.fail("frozen read recalculated a correspondence sheet")
    monkeypatch.setattr(common, "calculate_correspondence_components", forbidden)
    monkeypatch.setattr(bio, "calculate_correspondence_components", forbidden)
    monkeypatch.setattr(blast, "calculate_correspondence_components", forbidden)
    validate_tool_correspondence(grading, companion)
    changed = deepcopy(grading); changed["scores"]["alignment_identity"] = 1
    with pytest.raises(ValueError, match="saved_correspondence_conflict"):
        validate_tool_correspondence(changed, companion)


def test_frozen_earlier_common_components_keep_stored_compatibility_cells(monkeypatch):
    grading = bio.grade_biopython_pairwise(bio_native(), molecule="dna", _retain_correspondence=True)
    companion = grading.pop("correspondence")
    # Explicit old common-v1 shape control: the new success-qualified fields
    # were absent. Reading it cannot infer new cells or rewrite old facts.
    for selected in companion["instances"][0]["components"]["selected"].values():
        selected.pop("execution_success_numerator")
        selected.pop("execution_success_value")
    original = deepcopy(companion)
    def forbidden(*args, **kwargs):
        pytest.fail("frozen earlier common components were recalculated")
    monkeypatch.setattr(common, "calculate_correspondence_components", forbidden)
    validate_tool_correspondence(grading, companion)
    assert companion == original


class _Store:
    def __init__(self):
        self.records = {"native": {"record_type": "artifact"}}
        self.raw = {}
    def get(self, ref):
        return self.records[ref]
    def artifact(self, raw, media):
        ref = "artifact_" + str(len(self.raw))
        self.raw[ref] = raw
        self.records[ref] = {"record_type": "artifact", "media_type": media}
        return ref
    def get_artifact(self, ref):
        return self.raw[ref]


def test_v2_retention_keeps_legacy_closed_shape_and_explicit_failure_and_v1_reads():
    store = _Store()
    grading = bio.grade_biopython_pairwise(bio_native(), molecule="dna", _retain_correspondence=True)
    ref = retain_tool_grading(store, provider="biopython.alignment", native_artifact_ref="native", grading=grading)
    body = json.loads(store.raw[ref])
    assert body["schema"] == "tool_grading_artifact_v2"
    assert set(body) == {"schema", "provider", "native_artifact_ref", "grading", "correspondence"}
    assert set(body["grading"]) == {"sheet", "scores"}
    store.records["source"] = {"record_type": "source", "provider": "biopython.alignment",
        "artifact_ref": "native", "auxiliary_artifact_refs": [ref]}
    assert source_tool_gradings(store, "source") == [body["grading"]]
    with pytest.raises(ValueError, match="correspondence_required"):
        retain_tool_grading(store, provider="biopython.alignment", native_artifact_ref="native", grading=body["grading"])
    failure = {"sheet": None, "scores": None, "failure": {"code": "invalid", "category": "grading_input"}}
    failure_ref = retain_tool_grading(store, provider="biopython.alignment", native_artifact_ref="native", grading=failure)
    assert json.loads(store.raw[failure_ref])["schema"] == "tool_grading_artifact_v1"
    old = {"schema": "tool_grading_artifact_v1", "provider": "biopython.alignment",
        "native_artifact_ref": "native", "grading": body["grading"]}
    old_ref = store.artifact(json.dumps(old), store.records[ref]["media_type"])
    store.records["source"]["auxiliary_artifact_refs"] = [old_ref]
    assert source_tool_gradings(store, "source") == [body["grading"]]
