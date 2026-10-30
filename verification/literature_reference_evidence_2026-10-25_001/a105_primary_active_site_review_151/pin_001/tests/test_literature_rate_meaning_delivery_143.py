"""Engineering fixtures for optional exact source-rate meaning custody.

Constructed source bytes and scripted choices are not primary-source findings.
"""
from copy import deepcopy
from dataclasses import replace
import sqlite3

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.communication import ReportBoundaryError, form_with_facts, validate_form, validate_closed_schema
from gene_annotation_episode.domain import ContractError, obj
from gene_annotation_episode.literature_rate_meaning_delivery import (
    NAMESPACE, COMPONENT_ROLES, source_meaning_projection, rate_source_meaning_cells_schema,
)
from gene_annotation_episode.literature_rate_meaning_render import base_rows, render_received
from gene_annotation_episode.literature_rate_storage import LiteratureRateRepository
from gene_annotation_episode.literature_experimental_prompt import _section, _table
from gene_annotation_episode.state import Store
from test_literature_rate_native_storage import setup_native_store


@pytest.mark.parametrize("defined", [False, True])
def test_exact_meaning_view_preserves_cells_and_dependency_roles_without_new_work(tmp_path, defined):
    store, context, args = setup_native_store(tmp_path, defined=defined)
    try:
        repository = LiteratureRateRepository(store, context.run_id)
        outcome = repository.populate_native(context, args, "selected")
        reference = outcome["result"]["sheet_ref"]
        owner = replace(context, received_record_refs=(*context.received_record_refs, *outcome["record_refs"]))
        before = store.db.total_changes
        view = source_meaning_projection(repository)
        assert view.received_cells(owner) == []
        assert store.db.total_changes == before
        rows = view.fact_cells(owner, [reference], components=list(COMPONENT_ROLES))
        assert base_rows(rows) == repository.source_domain_projection().fact_cells(owner, [reference], components=list(COMPONENT_ROLES))
        extraction = repository.read(reference)["sheet"]["extraction"]
        validator = Draft202012Validator(rate_source_meaning_cells_schema())
        assert validator.is_valid(rows), list(validator.iter_errors(rows))
        for row in rows:
            assert [meaning["arm"] for meaning in row["rate_meanings"]] == list(COMPONENT_ROLES[row["component"]])
            assert row["comparison_intended_change"] == extraction["native_context"]["comparison"]["intended_change"]
            for meaning in row["rate_meanings"]:
                original = next(item for item in extraction["rows"] if item["arm"] == meaning["arm"])["source"]
                assert meaning["rate_unit"] == original["unit"]
                assert meaning["endpoint"] == original["meanings"]["endpoint"]
                assert meaning["normalization"] == original["meanings"]["normalization"]
                assert set(meaning) == {"arm", "endpoint", "normalization", "rate_unit"}
        assert store.db.total_changes == before
        assert store.db.execute("SELECT count(*) FROM literature_rate_operations").fetchone()[0] == 1
        assert not store.list("observation") and not store.list("assessment")
    finally:
        store.close()


def test_exact_subset_receipt_cannot_expand_from_shared_sheet_or_original_view(tmp_path):
    store, context, args = setup_native_store(tmp_path, defined=True)
    try:
        repo = LiteratureRateRepository(store, context.run_id)
        outcome = repo.populate_native(context, args, "selected")
        reference = outcome["result"]["sheet_ref"]
        refs = (*context.received_record_refs, *outcome["record_refs"])
        owner = replace(context, received_record_refs=refs)
        receiver = replace(owner, role="annotation", episode_id="receiver", path=(("annotation", "root"),), assignment={})
        view = source_meaning_projection(repo)
        rows = view.fact_cells(owner, [reference], components=["retained_fraction"])
        # Ordinary schema/fact construction, including exact nested witnesses.
        schema = obj({"caller_chosen_field": rate_source_meaning_cells_schema()})
        form = form_with_facts({}, schema, {NAMESPACE: rows})
        assert validate_form(form, schema, lambda ref, ns: ref in refs or store.get(ref)["record_type"] in ("artifact", "source")) == form
        view.receive_cells(receiver, rows, "manual-admitted-subset")
        view.receive_cells(receiver, rows, "manual-admitted-subset")
        assert view.received_cells(receiver) == rows
        assert view.fact_cells(receiver, [reference], components=["reference_rate", "retained_fraction"]) == rows
        assert repo.source_domain_projection().fact_cells(receiver, [reference], components=["retained_fraction"]) == []
        assert repo.source_projection().fact_cells(receiver, [reference], components=["retained_fraction"]) == []
        unreceived = view.fact_cells(owner, [reference], components=["reference_rate"])
        with pytest.raises(ContractError, match="cell_not_received"):
            view.validate_fact_values(receiver, unreceived)
        for change in ("comparison", "scale", "dependency"):
            forged = deepcopy(rows)
            if change == "comparison":
                forged[0]["comparison_intended_change"]["quote"] = "invented blank"
            elif change == "scale":
                forged[0]["rate_meanings"][0]["rate_unit"]["multiplier"] = 999
            else:
                forged[0]["rate_meanings"].pop()
            with pytest.raises(ContractError, match="differs_from_saved"):
                view.validate_returned_values(forged, permitted_record_refs=refs)
        assert store.db.execute("SELECT count(*) FROM literature_rate_source_meaning_received").fetchone()[0] == 1
    finally:
        store.close()


def test_missing_selected_meanings_remain_explicit_without_interpreting_omission(tmp_path):
    store, context, args = setup_native_store(tmp_path)
    try:
        args["comparison"]["intended_change"] = None
        args["arms"]["test"]["normalization"] = None
        args["arms"]["test"]["rate"]["unit"] = None
        repo = LiteratureRateRepository(store, context.run_id)
        outcome = repo.populate_native(context, args, "partial")
        rows = source_meaning_projection(repo).project_cells([outcome["result"]["sheet_ref"]],
            permitted_record_refs=outcome["record_refs"], components=["test_rate"])
        assert rows[0]["comparison_intended_change"] is None
        assert rows[0]["rate_meanings"] == [{"arm": "test", "endpoint": repo.read(outcome["result"]["sheet_ref"])["sheet"]["extraction"]["rows"][1]["source"]["meanings"]["endpoint"], "normalization": None, "rate_unit": None}]
        parts = []
        render_received(parts, rows, {}, section=_section, table=_table)
        text = "\n".join(parts)
        assert "not recorded in selected inputs" in text
        assert "Missing selected meanings do not establish publication omissions" in text
    finally:
        store.close()


def test_registered_meaning_schema_is_exact_top_level_only_and_generic_prose_stays_rejected():
    schema = obj({"caller_field": rate_source_meaning_cells_schema()})
    assert validate_closed_schema(schema) == schema
    for change in ("extra", "nested", "removed_witness", "unbound"):
        forged = deepcopy(schema)
        if change == "extra":
            forged["properties"]["caller_field"]["items"]["properties"]["free_summary"] = {"type": "string"}
        elif change == "nested":
            forged = obj({"wrapper": forged})
        elif change == "removed_witness":
            del forged["properties"]["caller_field"]["items"]["properties"]["comparison_intended_change"]
            forged["properties"]["caller_field"]["items"]["required"].remove("comparison_intended_change")
        else:
            del forged["properties"]["caller_field"]["x-source"]
        with pytest.raises(ReportBoundaryError):
            validate_closed_schema(forged)
    with pytest.raises(ReportBoundaryError, match="strings need a declared semantic type"):
        validate_closed_schema(obj({"quote": {"type": "string"}}))


def test_meaning_view_explicitly_rejects_legacy_table_sheet(tmp_path):
    from test_literature_rate_storage import setup_store
    store, context, args = setup_store(tmp_path)
    try:
        repository = LiteratureRateRepository(store, context.run_id)
        outcome = repository.populate(context, args, "legacy-selected")
        with pytest.raises(ContractError, match="projection_version_mismatch"):
            source_meaning_projection(repository).project_cells([outcome["result"]["sheet_ref"]],
                permitted_record_refs=outcome["record_refs"])
    finally:
        store.close()


def test_nullable_witness_branches_still_require_actual_reference_resolution(tmp_path):
    store, context, args = setup_native_store(tmp_path, defined=True)
    try:
        repository = LiteratureRateRepository(store, context.run_id)
        outcome = repository.populate_native(context, args, "selected")
        rows = source_meaning_projection(repository).project_cells([outcome["result"]["sheet_ref"]],
            permitted_record_refs=outcome["record_refs"], components=["retained_fraction"])
        schema = obj({"requested": rate_source_meaning_cells_schema()})
        artifact = rows[0]["rate_meanings"][0]["rate_unit"]["source_defined_unit"]["definition"]["amount"]["selector"]["witness"]["artifact_ref"]
        visited = []
        def resolver(reference, namespace):
            visited.append(reference)
            return reference != artifact
        with pytest.raises(ReportBoundaryError, match="reference is unavailable"):
            validate_form({"requested": rows}, schema, resolver)
        assert artifact in visited
    finally:
        store.close()


def test_requested_derived_meaning_renders_without_unrequested_operands_or_tracking(tmp_path):
    from gene_annotation_episode.literature_experimental_prompt import _received_returns, _source_result
    store, context, args = setup_native_store(tmp_path)
    try:
        repository = LiteratureRateRepository(store, context.run_id)
        outcome = repository.populate_native(context, args, "selected")
        rows = source_meaning_projection(repository).project_cells([outcome["result"]["sheet_ref"]],
            permitted_record_refs=outcome["record_refs"], components=["retained_fraction"])
        records = {reference: store.get(reference) for reference in outcome["record_refs"]}
        for mode in ("received", "lookup", "history"):
            parts = []
            if mode == "received":
                _received_returns(parts, [{"chosen": rows}], native_rate_meaning_records=records)
            else:
                content = {"chosen": rows} if mode == "lookup" else {"view": "records", "records": [
                    {"selection": {"kind": "episode_child"}, "outcome": None, "admitted_report": {"chosen": rows}}]}
                _source_result(parts, {"result": content}, mode, native_rate_meaning_display={"records": records})
            text = "\n".join(parts)
            assert "different constructs" in text and "NADH oxidation" in text
            assert "per mg preparation" in text
            assert "Reference rate |" not in text and "Test rate |" not in text
            assert "0.012" not in text and "0.003" not in text
            assert "Reference rate 12" not in text and "Test rate 3" not in text
            assert rows[0]["sheet_ref"] not in text and rows[0]["evidence_source_ref"] not in text
    finally:
        store.close()


def test_mixed_lookup_and_actual_history_keep_other_requested_cells_and_outcomes(tmp_path):
    from gene_annotation_episode.literature_experimental_prompt import _source_result
    store, context, args = setup_native_store(tmp_path)
    try:
        repository = LiteratureRateRepository(store, context.run_id)
        outcome = repository.populate_native(context, args, "selected")
        reference = outcome["result"]["sheet_ref"]
        rows = source_meaning_projection(repository).project_cells([reference],
            permitted_record_refs=outcome["record_refs"], components=["retained_fraction"])
        other_requested = repository.source_projection().project_cells([reference],
            permitted_record_refs=outcome["record_refs"], components=["reference_rate"])
        records = {reference: store.get(reference) for reference in outcome["record_refs"]}
        mixed = {"selected_meaning": rows, "separately_requested_native_rate": other_requested}
        parts = []
        _source_result(parts, {"result": mixed}, "Requested mixed lookup",
            native_rate_meaning_display={"records": records})
        text = "\n".join(parts)
        assert "Test / reference rate | 0.25" in text
        assert "Reference rate | 0.012" in text
        assert "different constructs" in text
        # Explicitly constructed own quantity outcome in the real history
        # envelope. It has a separately requested numerical meaning and must
        # survive recognition of the rate meaning return in another entry.
        quantity_outcome = {"status": "completed", "result": {"quantity": "apparent_km", "analyte": "sulfate",
            "cells": {"reported_parameter": {"value": 17, "unit": "uM", "status": "populated",
                "origin": "synthetic", "unavailable_reason": None, "conditional_on": []}}}}
        history = {"view": "records", "records": [
            {"selection": {"kind": "episode_child"}, "outcome": None, "admitted_report": mixed},
            {"selection": {"kind": "tool", "tool": "literature.quantity.populate",
                "arguments": {"private_recipe": "PRIVATE_SELECTED_ARGUMENTS"}},
             "outcome": quantity_outcome, "admitted_report": None}]}
        parts = []
        _source_result(parts, {"status": "completed", "result": history}, "Requested mixed history",
            native_rate_meaning_display={"records": records})
        text = "\n".join(parts)
        assert "Test / reference rate | 0.25" in text and "Reference rate | 0.012" in text
        assert "reported_parameter | 17 | uM" in text and "apparent_km" in text and "sulfate" in text
        assert "different constructs" in text and "PRIVATE_SELECTED_ARGUMENTS" not in text
        for host_field in ("artifact_ref", "number_start", "source_ref", rows[0]["sheet_ref"]):
            assert host_field not in text
        assert "Test rate |" not in text and "0.003" not in text
    finally:
        store.close()


def test_meaning_reconstruction_is_query_only_and_preserves_original_rows(tmp_path, monkeypatch):
    store, context, args = setup_native_store(tmp_path, defined=True)
    repo = LiteratureRateRepository(store, context.run_id)
    outcome = repo.populate_native(context, args, "selected")
    reference = outcome["result"]["sheet_ref"]
    owner = replace(context, received_record_refs=(*context.received_record_refs, *outcome["record_refs"]))
    receiver = replace(owner, role="annotation", episode_id="receiver", path=(("annotation", "root"),), assignment={})
    view = source_meaning_projection(repo)
    rows = view.fact_cells(owner, [reference], components=["retained_fraction"])
    view.receive_cells(receiver, rows, "manual-admitted")
    saved = repo.read(reference)
    source_artifacts = {store.get(ref)["artifact_ref"] for ref in saved["input_source_refs"]}
    store.close()
    reopened = Store.__new__(Store)
    reopened.path = tmp_path.resolve(); reopened._savepoint = 0
    reopened.db = sqlite3.connect((tmp_path / "state.sqlite3").as_uri() + "?mode=ro", uri=True, isolation_level=None)
    reopened.db.row_factory = sqlite3.Row
    reopened.db.execute("PRAGMA query_only=ON")
    reopened.db.create_function("library_scope_record", 2, reopened._scope_filter_record)
    def forbidden(*args, **kwargs):
        raise AssertionError("reconstruction must not reacquire, repopulate, model or write")
    original_artifact = reopened.get_artifact
    def get_artifact(reference):
        if reference in source_artifacts:
            forbidden()
        return original_artifact(reference)
    monkeypatch.setattr(reopened, "get_artifact", get_artifact)
    for method in ("put", "artifact", "transaction"):
        monkeypatch.setattr(reopened, method, forbidden)
    monkeypatch.setattr("gene_annotation_episode.literature_rate_storage.populate_rate_contrast", forbidden)
    monkeypatch.setattr("gene_annotation_episode.literature_rate_native_inputs.read_rate_source_inputs", forbidden)
    try:
        # Avoid the legacy repository constructor's table-installing API.
        from gene_annotation_episode.literature_rate_meaning_delivery import LiteratureRateSourceMeaningProjection
        restored = LiteratureRateSourceMeaningProjection(reopened, context.run_id)
        assert restored.received_cells(receiver) == rows
        assert restored.fact_cells(receiver, [reference], components=["test_rate"]) == []
        assert restored.fact_cells(owner, [reference], components=["retained_fraction"]) == rows
        assert restored.read(reference) == saved
        assert reopened.db.total_changes == 0
    finally:
        reopened.close()
