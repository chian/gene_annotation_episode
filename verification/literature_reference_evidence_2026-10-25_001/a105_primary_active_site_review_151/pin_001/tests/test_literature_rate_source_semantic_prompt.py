"""Constructed rate returns: semantic presentation, not paper/model evidence."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from types import MappingProxyType

import pytest

from gene_annotation_episode.domain import ContractError, obj
from gene_annotation_episode.decision_context import state_frame
from gene_annotation_episode.literature_experimental_prompt import (
    _steering, render_literature_experimental_prompt,
)
from gene_annotation_episode.literature_rate_source_render import MEANING_FIELDS, is_row
from gene_annotation_episode.literature_rate_storage import COMPONENTS, rate_source_cells_schema
from test_literature_experimental_prompt_delivery import LiteratureWire, complete, snapshot


def constructed_rows(*, sheet="source_native_sheet", component="rate_difference", value=9):
    records = {}
    row = {"sheet_ref": sheet, "evidence_source_ref": "source_constructed_evidence",
        "component": component, "value": value, "unit": "umol/min/mg",
        "status": "populated", "origin": "derived", "unavailable_reason": None,
        "conditional_on": [], "approximate": False, "threshold": None, "bound": "none"}
    meanings = {
        "assayed_subject_ref": None, "experiment_ref": "constructed assay comparison",
        "endpoint_ref": "reported product rate", "normalization_ref": "per preparation mass",
        "reference_subject_ref": "molecule Alpha", "test_subject_ref": "molecule Beta",
        "reference_construct_ref": "full length", "test_construct_ref": "variant form",
        "reference_preparation_ref": "reference preparation", "test_preparation_ref": "test preparation",
        "reference_condition_ref": "50 mM buffer; pH 7.5; 20 uM substrate",
        "test_condition_ref": "50 mM buffer; pH 7.5; 40 uM substrate",
    }
    for field, namespace in MEANING_FIELDS.items():
        reference = namespace + "_" + field
        row[field] = reference if meanings[field] is not None else None
        if row[field] is not None:
            records[reference] = {"id": reference, "record_type": namespace,
                "name" if namespace == "context" else "label": meanings[field],
                "source_ref": row["evidence_source_ref"], "accession": "PRIVATE_ACCESSION"}
    assert is_row(row)
    return [row], records


def state_with_rows(rows, records):
    state = snapshot()
    state["child_reports"] = [{"arbitrary_parent_field": rows}]
    # Simulate all returned meanings falling outside the generic24-record page.
    state["working_state"] = {"references": [{"id": "reference_filler_" + str(i),
        "record_type": "reference", "label": "unrequested filler"} for i in range(24)]}
    state["literature_rate_source_display"] = {"cells": rows, "records": records}
    state["last_local_outcome"] = {"status": "completed", "record_refs": [rows[0]["sheet_ref"]]}
    return state


def test_exact_native_shape_routes_arbitrary_field_to_one_compact_table_without_host_ids():
    rows, records = constructed_rows()
    state = state_with_rows(rows, records)
    before = deepcopy(state)
    text = _steering(state, ())
    assert "| Reference − test rate | 9 | umol/min/mg | populated |" in text
    assert text.count("| Reference − test rate |") == 1
    for expected in ("molecule Alpha", "molecule Beta", "full length", "variant form",
            "reference preparation", "test preparation", "reported product rate", "per preparation mass",
            "50 mM buffer; pH 7.5; 20 uM substrate", "40 uM substrate"):
        assert expected in text
    for secret in ("source_native_sheet", "source_constructed_evidence", "PRIVATE_ACCESSION",
            "reference_subject_ref", "arbitrary_parent_field[", "unrequested filler"):
        assert secret not in text
    assert len(text) < 3000
    assert state == before
    malformed = deepcopy(rows[0]);malformed["invented"] = True
    assert not is_row(malformed)
    legacy = {k: v for k, v in rows[0].items() if k not in
        {"approximate", "threshold", "bound", *(role + "_" + name + "_ref"
          for role in ("reference", "test") for name in ("subject", "construct", "preparation"))}}
    assert not is_row(legacy)


@pytest.mark.parametrize("bound,symbol", [("lt", "<"), ("le", "≤"), ("gt", ">"), ("ge", "≥")])
def test_censoring_is_an_explicit_bound_with_null_point_not_a_zero_or_confidence_interval(bound, symbol):
    rows, records = constructed_rows(component="test_rate", value=None)
    rows[0].update(status="unavailable", unavailable_reason="censored_measurement",
        bound=bound, threshold=2, approximate=True, origin="synthetic")
    text = _steering(state_with_rows(rows, records), ())
    assert f"| Test rate | unknown | umol/min/mg | unavailable | {symbol} | 2 | true | censored_measurement |" in text
    assert "confidence interval" not in text
    assert "Reference rate" not in text


def test_requested_unknown_statistic_and_latent_conditions_remain_explicit():
    rows, records = constructed_rows(component="source_signed_index", value=None)
    rows[0].update(unit="dimensionless", status="unavailable", origin="proposed",
        unavailable_reason="observation_model_unspecified",
        conditional_on=["independent_normal_groups", "independent_groups"])
    rows[0]["test_construct_ref"] = None
    text = _steering(state_with_rows(rows, records), ())
    assert "Proposed signed source index | unknown | dimensionless | unavailable" in text
    assert "observation_model_unspecified | independent normal groups; independent groups | proposed" in text
    assert "Required statistical conditions" in text
    assert "| Test | molecule Beta | unknown | test preparation |" in text
    assert "independent preparation count" not in text


def test_equal_numbers_in_distinct_sheets_stay_referable_while_same_cell_duplicates_do_not_repeat():
    first, records = constructed_rows()
    second = deepcopy(first);second[0]["sheet_ref"] = "source_other_native_sheet"
    state = state_with_rows(first, records)
    state["child_reports"] = [{"one": first + first}, {"two": second}]
    text = _steering(state, ())
    assert "Native source-rate comparison 1" in text
    assert "Native source-rate comparison 2" in text
    assert text.count("| Reference − test rate | 9 |") == 2
    assert "Comparison numbers identify returned records, not independent experiments." in text
    assert "source_other_native_sheet" not in text


def test_native_related_handles_are_hidden_but_separately_received_same_source_fact_survives():
    rows, records = constructed_rows()
    state = state_with_rows(rows, records)
    independent = {"id": "reference_independent_fact", "record_type": "reference",
        "label": "separately admitted experimental qualification", "source_ref": rows[0]["evidence_source_ref"]}
    state["working_state"]["references"] = [*records.values(), independent]
    state["current_report_basis_refs"] = [independent["id"]]
    text = _steering(state, ())
    assert "separately admitted experimental qualification" in text
    assert text.count("molecule Alpha") == 1
    assert "PRIVATE_ACCESSION" not in text


def test_historical_pure_state_without_host_map_uses_possessed_working_meanings_and_honest_access_fallback():
    rows, records = constructed_rows()
    state = state_with_rows(rows, records)
    state.pop("literature_rate_source_display")
    state["working_state"] = {"references": list(records.values())}
    text = _steering(state, ())
    assert "molecule Alpha" in text and "molecule Beta" in text
    state["working_state"] = {}
    text = _steering(state, ())
    assert "meaning retained for scoped access" in text
    assert "| Reference − test rate | 9 |" in text


def test_complete_task_repeats_unchanged_across_bootstrap_delta_lookup_and_reconstruction(tmp_path):
    rows, records = constructed_rows()
    before = state_with_rows(rows, records)
    before["requested_form"] = obj({"arbitrary": rate_source_cells_schema()})
    after = deepcopy(before);after["feedback"] = {"code": "constructed_feedback"}
    expected_task = render_literature_experimental_prompt(before, "Full fixture assignment").split("\n\nSTEERING\n")[0]
    assert render_literature_experimental_prompt(after, "Full fixture assignment").split("\n\nSTEERING\n")[0] == expected_task
    assert render_literature_experimental_prompt(after, "Full fixture assignment", lookup_results=[{
        "status": "completed", "result": {"text": "Constructed exact selected passage."}}]).split("\n\nSTEERING\n")[0] == expected_task
    wire = LiteratureWire(tmp_path / "wire");restarted = LiteratureWire(tmp_path / "restarted")
    async def exercise():
        await complete(wire, state_frame(before))
        await complete(wire, state_frame(after, before))
        await complete(restarted, state_frame(after))
    asyncio.run(exercise())
    tasks = []
    for transport in (wire, restarted):
        for turn in transport.turns_sent():
            task, steering = turn["input"][0]["text"].split("\n\nSTEERING\n", 1)
            tasks.append(task)
            assert "molecule Alpha" in steering and "20 uM substrate" in steering
            assert "source_native_sheet" not in steering and "PRIVATE_" not in steering
    assert all(task == tasks[0] for task in tasks)
    assert is_row(MappingProxyType(rows[0]))
