"""Retain controlled reference-reaction Workflows and fresh saved-only replay.

Source selections are the root-reviewed integration fixtures. Decisions and
continuation are scripted; this runner performs no new source interpretation,
configured-model inference, live-host recovery or target-credit calculation.
"""
from __future__ import annotations

import argparse
import asyncio
from dataclasses import replace
from functools import partial
import hashlib
import inspect
import json
import math
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
NAMES = ("primary_csid_reported_ratio", "synthetic_complete_resources",
         "synthetic_incomplete_resources")
TABLES = {"observations": "runtime_observations",
          "population_operations": "literature_reaction_operations",
          "parent_receipts": "literature_reaction_received"}
EXPECTED_COUNTS = {"observations": 3, "population_operations": 1, "parent_receipts": 1}
_DISABLED_SOURCE_WORK = None


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def counts(store):
    return {name: store.db.execute("SELECT count(*) FROM " + table).fetchone()[0]
            for name, table in TABLES.items()}


def histories(store):
    actions = [{"episode_id": row["episode_id"], "decision_index": row["decision_index"],
        "selection": json.loads(row["action"]), "credit": row["credit"]}
        for row in store.db.execute("SELECT * FROM runtime_actions ORDER BY rowid")]
    observations = [{"episode_id": row["episode_id"], "unit_index": row["unit_index"],
        "observation": json.loads(row["observation"])}
        for row in store.db.execute("SELECT * FROM runtime_observations ORDER BY rowid")]
    return actions, observations


def check_cells(rows, *, name):
    from test_literature_reaction_integration import COMPONENTS

    assert [row["component"] for row in rows] == COMPONENTS
    primary = name == "primary_csid_reported_ratio"
    incomplete = name == "synthetic_incomplete_resources"
    expected = [1., None, None, None, 1.] if primary else [
        .8, .05, 1/3, None if incomplete else .6, .2]
    for row, expected_value in zip(rows, expected):
        value = row["value"]
        assert value is None if expected_value is None else (
            value is not None and math.isclose(value, expected_value, rel_tol=1e-12, abs_tol=1e-15))
    assert all(row["operand_source_kind"] == (
        "retained_extraction" if primary else "synthetic_fixture") for row in rows)
    assert all(row["ratio_mode"] == (
        "source_summary" if primary else "independent_units") for row in rows)
    assert all(row["ratio_kind"] == "product_pair" for row in rows)
    assert all(row["measurement_corrections"] == "not_applied" for row in rows)
    assert all(row["target_correspondence"] == "not_evaluated" for row in rows)
    assert all(row["bound_kind"] == "logical_model_domain_not_confidence_interval" for row in rows)
    if primary:
        assert rows[1]["unavailable_reason"] == "sampling_moments_unreported"
        assert rows[2]["unavailable_reason"] == "alternatives_unreported"
        assert rows[3]["unavailable_reason"] == "budget_unreported"
        assert all(row["alternative_predictions"] == [] for row in rows)
    else:
        assert all(row["alternative_predictions"] == [.5] for row in rows)
        assert all(row["resources_complete"] is (not incomplete) for row in rows)
        if incomplete:
            assert rows[3]["unavailable_reason"] == "resources_incomplete"


def run_case(directory, name):
    from gene_annotation_episode.communication import plain
    from gene_annotation_episode.domain import canonical
    from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
    from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
    from gene_annotation_episode.literature_episodes import LiteratureEpisodes
    from gene_annotation_episode.literature_reaction_storage import LiteratureReactionRepository
    from gene_annotation_episode.runtime import run_workflow
    from gene_annotation_episode.tools import ToolRegistry
    from test_literature_reaction_integration import setup_case, FORM
    from test_runtime import FixtureController, ScriptedProvider

    directory.mkdir(parents=True, exist_ok=False)
    primary = name == "primary_csid_reported_ratio"
    incomplete = name == "synthetic_incomplete_resources"
    store, context, arguments = setup_case(directory / "state", primary=primary, incomplete=incomplete)
    received = []
    try:
        commission = {"selection": {"kind": "episode_child", "role": "literature",
            "assignment": plain(context.assignment),
            "goal": "Evaluate the source product-pair ratio and resource requirements",
            "scope": plain(context.scope),
            "purpose": "Return requested numerical chemistry components and limitations",
            "schema_json": json.dumps(FORM), "initial_report_json": "{}"}, "report_update": {}}
        action = {"selection": {"kind": "tool", "tool": "literature.reaction.populate",
            "arguments": arguments}, "report_update": {}}

        def receive(inputs):
            form, = inputs["child_reports"]
            received.append(form)
            check_cells(form["measurements"], name=name)
            commit = {field: [] for field in store.reasoning_schema()["required"]}
            source = store.get(arguments["source_ref"])
            raw = store.get_artifact(source["artifact_ref"])
            label = "CsiD" if primary else "SyntheticProtein"
            start = raw.index(label.encode())
            commit["source_subjects"] = [{"alias": "studied_molecule", "reference_type": "assay",
                "source_ref": source["id"], "label": label, "anchor": {
                    "source_ref": source["id"], "artifact_ref": source["artifact_ref"],
                    "start": start, "end": start + len(label), "quote": label}}]
            return {"selection": {"kind": "reason", "commit": commit}, "report_update": {}}

        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, ToolRegistry(store),
            provider=ScriptedProvider([commission, action, receive]), run_dir=directory / "run",
            controller_factory=lambda path, initial: FixtureController(str(path), initial,
                2 if len(path) == 1 else 1),
            project_credit=scorer, initial_known_record_refs=list(context.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True),),
            binding_definitions={"credit": scorer.as_record()}))
        run_id, = store.db.execute("SELECT run_id FROM runtime_runs").fetchone()
        operation, = store.db.execute("SELECT * FROM literature_reaction_operations WHERE run_id=?",
            (run_id,)).fetchall()
        outcome = json.loads(operation["outcome"])
        repository = LiteratureReactionRepository(store, run_id)
        payload = repository.read(outcome["result"]["sheet_ref"])
        assert outcome["status"] == "completed"
        assert counts(store) == EXPECTED_COUNTS
        assert summary["credit"] == 0 and len(received) == 1
        assert not store.list("observation") and not store.list("assessment")
        actions, observations = histories(store)
        assert len(actions) == len(observations) == 3
        assert all(row["credit"] == 0 for row in actions)
        assert sorted(row["selection"]["kind"] for row in actions) == ["episode_child", "reason", "tool"]
        returns = EpisodeReturnRecords(store, run_id, failure_prefix="reaction_original_")
        attempt, = store.db.execute("SELECT parent_episode_id,decision_index FROM runtime_report_attempts").fetchall()
        parent = returns.context(attempt["parent_episode_id"])
        child, frozen_form, schema = returns._attempt(parent, attempt["decision_index"])
        assert child.episode_id == operation["episode_id"]
        assert canonical(schema) == canonical(FORM)
        assert canonical(frozen_form) == canonical(received[0])
        admitted = repository.received_cells(parent)
        assert canonical(admitted) == canonical(received[0]["measurements"])
        check_cells(admitted, name=name)
        source_hashes = {}
        for reference in payload["direct_input_source_refs"]:
            source = store.get(reference)
            source_hashes[reference] = {field: hashlib.sha256(store.get_artifact(source[field])).hexdigest()
                for field in ("artifact_ref", "text_ref") if source.get(field) is not None}
        receipt = {"status": "passed", "case": name, "run_id": run_id, "model_backed": False,
            "execution": "ordinary Workflow with scripted decisions and fixture controller",
            "target_problem": "isolated ATGGCT short-sequence fixture; no target annotation assertion",
            "source_kind": arguments["source_kind"], "outcome": outcome,
            "saved_payload": payload, "actual_frozen_child_form": frozen_form,
            "actual_admitted_parent_subset": admitted, "parent_form_schema": schema,
            "actual_completed_actions": actions, "actual_local_observations": observations,
            **counts(store), "controller_credit": summary["credit"],
            "direct_source_sha256": source_hashes,
            "limits": ["No configured-model reaction interpretation or live host restart",
                "Primary NMR product-pair ratio is retained extraction, not native spectrum integration",
                "Primary sampling moments and alternative comparison remain unreported",
                "Incomplete resources preserve unknown nominal capacity and coverage",
                "Comparison transforms are proposed conventions; domain bounds are not confidence intervals",
                "No measurement corrections, network, isotope, whole-A110 or cross-axis aggregation",
                "No target correspondence or annotation credit is calculated"]}
        save(directory / "RECEIPT.json", receipt)
        return {key: receipt[key] for key in ("case", "run_id", "model_backed", "source_kind",
            "observations", "population_operations", "parent_receipts")}
    finally:
        store.close()


def disable_source_work():
    """Disable defining-module readers/calculators/helpers and imported aliases."""
    global _DISABLED_SOURCE_WORK
    if _DISABLED_SOURCE_WORK is not None:
        return list(_DISABLED_SOURCE_WORK)
    from gene_annotation_episode import literature_reaction_storage as storage
    from gene_annotation_episode import literature_reaction_inputs as inputs
    from gene_annotation_episode import literature_reaction_calculations as calculations
    from gene_annotation_episode import literature_assay_inputs as assay_inputs

    def forbidden(*args, **kwargs):
        raise AssertionError("source_parsing_identity_generation_or_recalculation_forbidden")

    disabled = []
    for module in (inputs, calculations):
        for name, value in tuple(vars(module).items()):
            if (getattr(value, "__module__", None) == module.__name__
                    and (inspect.isfunction(value) or inspect.isclass(value))
                    and name != "reaction_population_schema"):
                setattr(module, name, forbidden)
                disabled.append(module.__name__ + "." + name)
    for module, names in ((storage, ("read_reaction_inputs", "populate_reaction_constraints")),
            (inputs, ("_Sources", "_numeric")), (assay_inputs, ("_Sources", "_numeric"))):
        for name in names:
            setattr(module, name, forbidden)
            disabled.append(module.__name__ + "." + name)
    _DISABLED_SOURCE_WORK = sorted(disabled)
    return list(_DISABLED_SOURCE_WORK)


def reopen_case(directory):
    from gene_annotation_episode.domain import canonical
    from gene_annotation_episode.episode_receipts import EpisodeReceipts
    from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.literature_reaction_storage import LiteratureReactionRepository

    original = json.loads((directory / "RECEIPT.json").read_text())
    disabled = disable_source_work()
    with Store(directory / "state") as store:
        run_id = original["run_id"]
        repository = LiteratureReactionRepository(store, run_id)
        returns = EpisodeReturnRecords(store, run_id, failure_prefix="reaction_reopen_")
        receipts = EpisodeReceipts(store, run_id)
        operation, = store.db.execute("SELECT * FROM literature_reaction_operations WHERE run_id=?",
            (run_id,)).fetchall()
        outcome = json.loads(operation["outcome"])
        assert canonical(outcome) == canonical(original["outcome"])
        sheet_ref = outcome["result"]["sheet_ref"]
        sheet = store.get(sheet_ref)
        allowed = {sheet["artifact_ref"], sheet["request_ref"]}
        original_artifacts = {source[field] for reference in original["saved_payload"]["direct_input_source_refs"]
            for source in (store.get(reference),) for field in ("artifact_ref", "text_ref") if source.get(field)}
        assert allowed.isdisjoint(original_artifacts)
        get_artifact, reads = store.get_artifact, []

        def saved_only(reference):
            assert reference in allowed, "original_paper_supplement_or_retained_operand_reads_forbidden"
            reads.append(reference)
            return get_artifact(reference)

        store.get_artifact = saved_only
        store.db.execute("PRAGMA query_only=ON")
        assert store.db.execute("PRAGMA query_only").fetchone()[0] == 1
        before = counts(store)
        context = returns.context(operation["episode_id"])
        context = replace(context, received_record_refs=tuple(receipts.known(context.episode_id)))
        request = json.loads(store.get_artifact(sheet["request_ref"]))
        assert repository.populate(context, request["arguments"], operation["operation_key"]) == outcome
        assert canonical(repository.read(sheet_ref)) == canonical(original["saved_payload"])
        cells = repository.project_cells([sheet_ref], permitted_record_refs=context.received_record_refs,
            components=context.assignment["requested_reaction_components"])
        attempt, = store.db.execute("SELECT parent_episode_id,decision_index FROM runtime_report_attempts").fetchall()
        parent = returns.context(attempt["parent_episode_id"])
        child, form, schema = returns._attempt(parent, attempt["decision_index"])
        assert child.episode_id == context.episode_id
        assert canonical(schema) == canonical(original["parent_form_schema"])
        assert canonical(form) == canonical(original["actual_frozen_child_form"])
        assert canonical(form["measurements"]) == canonical(cells)
        assert canonical(repository.received_cells(parent)) == canonical(cells)
        assert canonical(original["actual_admitted_parent_subset"]) == canonical(cells)
        check_cells(cells, name=original["case"])
        assert counts(store) == before == EXPECTED_COUNTS
        actions, observations = histories(store)
        assert canonical(actions) == canonical(original["actual_completed_actions"])
        assert canonical(observations) == canonical(original["actual_local_observations"])
        assert not store.list("observation") and not store.list("assessment")
    return {"case": original["case"], "status": "passed", "cells": len(cells),
        "selected_outcome_equals_saved_outcome": True,
        "actual_frozen_child_form_equals_saved_form": True,
        "actual_parent_subset_equals_saved_cells": True,
        "counts_before_and_after": before, "original_input_bytes_read": False,
        "parsers_calculators_and_identity_helpers_disabled": disabled,
        "replay_SQL_query_only": True, "allowed_saved_artifacts": sorted(allowed),
        "saved_artifact_reads": reads}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--reopen", action="store_true")
    args = parser.parse_args()
    directory = args.directory.resolve()
    if directory != BASE / "reaction_examples_001":
        raise ValueError("owned_reaction_example_directory_required")
    if args.reopen:
        result = {"status": "passed", "model_backed": False,
            "scope": "fresh process closed controlled Workflow replay, not live host restart",
            "cases": [reopen_case(directory / name) for name in NAMES]}
        save(directory / "REOPEN_RECEIPT.json", result)
    else:
        directory.mkdir(parents=True, exist_ok=False)
        result = {"status": "passed", "model_backed": False,
            "cases": [run_case(directory / name, name) for name in NAMES]}
        save(directory / "EXAMPLES_RECEIPT.json", result)
    print(json.dumps(result))
