"""Constructed source fixtures for A108 operand meanings and exact custody.

These are prepared retained JSON, not automatic extraction from paper prose.
"""
from copy import deepcopy
from dataclasses import replace
import json
import sqlite3

import pytest

from gene_annotation_episode.communication import validate_closed_schema
from gene_annotation_episode.domain import ContractError, obj, validate_schema
from gene_annotation_episode.literature_context_inputs import read_context_inputs
from gene_annotation_episode.literature_context_meanings import (
    DATA_VERSION, REQUIREMENT_FIELDS, ROUTE_FIELDS, RECORD_VERSION,
)
from gene_annotation_episode.literature_context_storage import (
    LiteratureContextRepository, LiteratureContextSemanticProjection,
    context_cells_schema, context_semantic_cells_schema,
)
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from test_literature_context_storage import fixture, source, dataset


def semantic_fixture(path, *, unknown=False, mutate=None):
    store, context, args, records = fixture(path, page=True)
    text = ("Glucose concentration requirement|Nitrate concentration requirement|glucose|nitrate|"
        "local concentration|cytosol|periplasm|same cell|carbon supply|electron acceptor availability|"
        "Joint assimilation route|Alternative acceptor route|"
        "The joint route requires cytosolic glucose and periplasmic nitrate in the same cell.|"
        "The alternative route requires nitrate in the periplasm.|"
        "The joint operating domain across both locations was assessed together.|"
        "The alternative operating domain was assessed separately.")
    meanings_source = source(store, text, parents=[records["root"]["id"]])
    def witness(quote):
        start = text.index(quote)
        return {"source_ref": meanings_source["id"], "representation": "original",
                "start": start, "end": start + len(quote), "quote": quote}
    data = dataset(sampling=False)
    data["version"] = DATA_VERSION
    inputs = data["inputs"]
    inputs["requirements"] = [{"key": key, "unit": "mM",
        "supported": [{"lower": 0, "upper": 2, "lower_closed": True, "upper_closed": True}],
        "incompatible": [{"lower": 3, "upper": 4, "lower_closed": True, "upper_closed": True}]}
        for key in ("private-a", "private-b")]
    inputs["routes"] = [{"key": "private-route-a", "requirements": ["private-a", "private-b"],
        "requirements_complete": True, "joint_support": "established"},
        {"key": "private-route-b", "requirements": ["private-b"],
        "requirements_complete": True, "joint_support": "established"}]
    for index, row in enumerate(inputs["contexts"]):
        original = row["observations"][0]
        row["observations"] = []
        for key in ("private-a", "private-b"):
            item = deepcopy(original)
            value = 1 if index < 2 else 3
            item.update(requirement_key=key, measurement_key=f"{key}-{index}", unit="mM",
                relation="numeric", interval={"lower": value, "upper": value,
                "lower_closed": True, "upper_closed": True})
            row["observations"].append(item)
    requirement_values = [
        ("Glucose concentration requirement", "glucose", "local concentration", "cytosol", "carbon supply"),
        ("Nitrate concentration requirement", "nitrate", "local concentration", "periplasm", "electron acceptor availability")]
    route_values = [
        ("Joint assimilation route", "same cell", "carbon supply",
         "The joint route requires cytosolic glucose and periplasmic nitrate in the same cell.",
         "The joint operating domain across both locations was assessed together."),
        ("Alternative acceptor route", "periplasm", "electron acceptor availability",
         "The alternative route requires nitrate in the periplasm.",
         "The alternative operating domain was assessed separately.")]
    data["meanings"] = {plural: [{"key": row["key"], **{field: None if unknown else witness(value)
        for field, value in zip(fields, values)}} for row, values in zip(inputs[plural], value_rows)]
        for plural, fields, value_rows in (("requirements", REQUIREMENT_FIELDS, requirement_values),
                                         ("routes", ROUTE_FIELDS, route_values))}
    if mutate:
        mutate(data)
    retained = source(store, json.dumps(data), parents=[records["root"]["id"]])
    args["data_source_ref"] = retained["id"]
    context = replace(context, received_record_refs=(*context.received_record_refs,
        retained["id"], meanings_source["id"]))
    return store, context, args, {**records, "retained": retained, "meanings": meanings_source}, data


def populate(store, context, args):
    repo = LiteratureContextRepository(store, context.run_id)
    outcome = repo.populate(context, args, "selected")
    view = repo.semantic_projection()
    rows = view.project_cells([outcome["result"]["sheet_ref"]],
        permitted_record_refs=outcome["record_refs"], components=["selected_point", "capability_point"])
    return repo, outcome, view, rows


def reopen_read_only(store):
    store.close()
    store.db = sqlite3.connect(f"file:{store.path / 'state.sqlite3'}?mode=ro", uri=True)
    store.db.row_factory = sqlite3.Row
    store.db.create_function("library_scope_record", 2, store._scope_filter_record)


def test_same_unit_equal_values_preserve_meaning_and_named_route_membership(tmp_path):
    def reverse_meanings(data):
        for rows in data["meanings"].values():
            rows.reverse()
    store, context, args, records, _ = semantic_fixture(tmp_path, mutate=reverse_meanings)
    with store:
        repo, outcome, view, rows = populate(store, context, args)
        saved = repo.read(outcome["result"]["sheet_ref"])
        assert saved["version"] == RECORD_VERSION
        assert [row["value"] for row in rows] == [.5, 1]
        first, second = rows[0]["requirement_definitions"]
        assert first["unit"] == second["unit"] == "mM"
        assert first["supported"] == second["supported"]
        assert first["requirement_ref"] != second["requirement_ref"]
        assert [store.get(r["entity_ref"])["label"] for r in (first, second)] == ["glucose", "nitrate"]
        assert [store.get(r["biological_setting_ref"])["name"] for r in (first, second)] == ["cytosol", "periplasm"]
        routes = rows[0]["route_definitions"]
        assert [store.get(r["route_ref"])["label"] for r in routes] == ["Joint assimilation route", "Alternative acceptor route"]
        assert routes[0]["requirement_refs"] == [first["requirement_ref"], second["requirement_ref"]]
        assert routes[1]["requirement_refs"] == [second["requirement_ref"]]
        for route in routes:
            for field in ("membership_evidence_ref", "joint_scope_evidence_ref"):
                proof = store.get(route[field])
                assert proof["anchor"]["source_ref"] == records["meanings"]["id"]
                assert proof["label"] == proof["anchor"]["quote"]
        assert records["meanings"]["id"] in saved["direct_input_source_refs"]
        assert all("private-" not in store.get(r["requirement_ref"])["label"] for r in (first, second))
        assert rows[0]["operand_origin"] == "synthetic"
        validate_closed_schema(obj({"cells": context_semantic_cells_schema()}))
        validate_schema(rows, context_semantic_cells_schema())
        with pytest.raises(ContractError):
            validate_schema(rows, context_cells_schema())
        with pytest.raises(ContractError, match="projection_version"):
            repo.project_cells([rows[0]["sheet_ref"]], permitted_record_refs=outcome["record_refs"])
        with pytest.raises(ContractError, match="projection_version"):
            repo.validate_empty_return_family(context)
        view.validate_empty_return_family(context)
        assert not store.list("observation") and not store.list("assessment")


def test_unknown_meanings_have_distinct_non_scientific_handles_without_new_gate(tmp_path):
    store, context, args, _, _ = semantic_fixture(tmp_path, unknown=True)
    with store:
        _, _, _, rows = populate(store, context, args)
        assert [row["value"] for row in rows] == [.5, 1]
        requirements = rows[0]["requirement_definitions"]
        assert len({r["requirement_ref"] for r in requirements}) == 2
        for requirement in requirements:
            assert requirement["definition_reported"] is False
            assert all(requirement[field + "_ref"] is None for field in REQUIREMENT_FIELDS if field != "definition")
            handle = store.get(requirement["requirement_ref"])
            assert handle["label"] == "Unreported requirement definition" and handle["anchor"] is None
        routes = rows[0]["route_definitions"]
        assert len({r["route_ref"] for r in routes}) == 2
        assert routes[0]["requirement_refs"] == [r["requirement_ref"] for r in requirements]
        assert all(r["joint_scope_evidence_ref"] is None for r in routes)


def test_partial_meaning_does_not_require_a_verbatim_definition(tmp_path):
    def partial(data):
        for requirement in data["meanings"]["requirements"]:
            requirement["definition"] = None
    store, context, args, _, _ = semantic_fixture(tmp_path, mutate=partial)
    with store:
        _, _, _, rows = populate(store, context, args)
        assert [store.get(r["entity_ref"])["label"] for r in rows[0]["requirement_definitions"]] == ["glucose", "nitrate"]
        assert all(not r["definition_reported"] for r in rows[0]["requirement_definitions"])
        assert rows[0]["value"] == .5


@pytest.mark.parametrize("plural", ["requirements", "routes"])
@pytest.mark.parametrize("defect", ["missing", "extra", "duplicate", "unknown"])
def test_meanings_must_match_actual_roster(tmp_path, plural, defect):
    def mutate(data):
        rows = data["meanings"][plural]
        if defect == "missing": rows.pop()
        elif defect == "extra": rows.append(deepcopy(rows[0]))
        elif defect == "duplicate": rows[1]["key"] = rows[0]["key"]
        else: rows[0]["key"] = "not-an-actual-operand"
    store, context, args, _, _ = semantic_fixture(tmp_path, mutate=mutate)
    with store:
        with pytest.raises(ExperimentalContractError, match="roster_mismatch"):
            LiteratureContextRepository(store, context.run_id).populate(context, args, "selected")
        assert not [row for row in store.list("source") if row["provider"] == "literature.experimental.context"]


def test_new_meaning_source_is_authorized_before_bytes_and_replay(tmp_path, monkeypatch):
    store, context, args, records, data = semantic_fixture(tmp_path)
    with store:
        repo, _, _, _ = populate(store, context, args)
        denied = replace(context, received_record_refs=tuple(r for r in context.received_record_refs if r != records["meanings"]["id"]))
        read = store.get_artifact
        def prohibit(ref):
            assert ref != records["meanings"]["artifact_ref"]
            return read(ref)
        monkeypatch.setattr(store, "get_artifact", prohibit)
        for key in ("selected", "new"):
            with pytest.raises(ContractError, match="not_received"):
                repo.populate(denied, args, key)
        # Possession alone does not authorize a source outside the assigned
        # page ancestry; the callback rejects it before returning bytes.
        foreign = source(store, read(records["meanings"]["artifact_ref"]))
        foreign_data = deepcopy(data)
        for plural in ("requirements", "routes"):
            for row in foreign_data["meanings"][plural]:
                for field in (REQUIREMENT_FIELDS if plural == "requirements" else ROUTE_FIELDS):
                    if row[field] is not None:
                        row[field]["source_ref"] = foreign["id"]
        retained = source(store, json.dumps(foreign_data), parents=[records["root"]["id"]])
        foreign_context = replace(context, received_record_refs=(*context.received_record_refs,
            foreign["id"], retained["id"]))
        with pytest.raises(ContractError, match="outside_assigned_source"):
            repo.populate(foreign_context, {**args, "data_source_ref": retained["id"]}, "foreign-page")


def test_exact_subset_receipt_forwarding_and_forgery(tmp_path):
    store, context, args, _, _ = semantic_fixture(tmp_path)
    with store:
        _, outcome, view, rows = populate(store, context, args)
        parent = replace(context, episode_id="parent", role="annotation", path=(("annotation", "parent"),), received_record_refs=tuple(outcome["record_refs"]))
        assert view.fact_cells(parent, [rows[0]["sheet_ref"]], components=["selected_point", "capability_point"]) == []
        view.receive_cells(parent, rows[:1], "actual-selected-subset")
        assert view.received_cells(parent) == rows[:1]
        assert view.fact_cells(parent, [rows[0]["sheet_ref"]], components=["selected_point", "capability_point"]) == rows[:1]
        forged = deepcopy(rows[:1])
        forged[0]["route_definitions"][0]["requirement_refs"].reverse()
        with pytest.raises(ContractError):
            view.receive_cells(parent, forged, "forged")
        forward = replace(parent, episode_id="grandparent")
        view.receive_cells(forward, view.received_cells(parent), "forwarded-exact")
        assert view.received_cells(forward) == rows[:1]
        assert store.db.execute("select count(*) from literature_context_operations").fetchone()[0] == 1


def test_reopen_replays_saved_v2_without_source_read_or_recalculation(tmp_path, monkeypatch):
    store, context, args, _, _ = semantic_fixture(tmp_path)
    with store:
        _, outcome, _, rows = populate(store, context, args)
        parent = replace(context, episode_id="parent", role="annotation", path=(("annotation", "parent"),), received_record_refs=tuple(outcome["record_refs"]))
        LiteratureContextSemanticProjection(store, context.run_id).receive_cells(parent, rows[:1], "selected-subset")
        saved = store.get(rows[0]["sheet_ref"])
        allowed = {saved["artifact_ref"], saved["request_ref"]}
        read = store.get_artifact
        def only_saved(ref):
            assert ref in allowed
            return read(ref)
        def forbidden(*args, **kwargs): raise AssertionError("source extraction/recalculation during replay")
        monkeypatch.setattr(store, "get_artifact", only_saved)
        monkeypatch.setattr("gene_annotation_episode.literature_context_storage.read_context_inputs", forbidden)
        monkeypatch.setattr("gene_annotation_episode.literature_context_storage.populate_context_compatibility", forbidden)
        reopen_read_only(store)
        repo = LiteratureContextRepository(store, context.run_id)
        assert repo.populate(context, args, "selected") == outcome
        assert repo.semantic_projection().received_cells(parent) == rows[:1]


def test_first_read_only_discovery_on_v1_has_no_new_table_or_view_upgrade(tmp_path):
    store, context, args, _ = fixture(tmp_path)
    with store:
        repo = LiteratureContextRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        old = repo.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=outcome["record_refs"], components=["selected_point"])
        parent = replace(context, episode_id="parent", role="annotation", path=(("annotation", "parent"),), received_record_refs=tuple(outcome["record_refs"]))
        repo.receive_cells(parent, old, "old-receipt")
        before = store.db.execute("select name from sqlite_master").fetchall()
        reopen_read_only(store)
        semantic = LiteratureContextSemanticProjection(store, context.run_id)
        assert semantic.received_cells(parent) == []
        repo.validate_empty_return_family(context)
        with pytest.raises(ContractError, match="projection_version"):
            semantic.validate_empty_return_family(context)
        assert repo.received_cells(parent) == old
        with pytest.raises(ContractError):
            semantic.project_cells([old[0]["sheet_ref"]], permitted_record_refs=outcome["record_refs"])
        assert store.db.execute("select name from sqlite_master").fetchall() == before
        assert repo.populate(context, args, "selected") == outcome
