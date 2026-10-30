"""Retain two controlled source-geometry Workflows and replay saved returns.

Unchanged primary-source bytes and selections come from the already reviewed
integration fixture. Decisions and continuation are scripted; no model inference,
new source acquisition, paper interpretation or target-credit work occurs here.
"""
from __future__ import annotations

import argparse
import asyncio
from dataclasses import replace
from functools import partial
import hashlib
import inspect
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
NAMES = ("primary_geometry_without_validation", "primary_geometry_with_validation")
TABLES = {"observations": "runtime_observations",
          "population_operations": "literature_structure_operations",
          "parent_receipts": "literature_structure_received"}
EXPECTED_COUNTS = {"observations": 3, "population_operations": 1, "parent_receipts": 1}
_DISABLED_SOURCE_WORK = None


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def counts(store):
    return {name: store.db.execute("SELECT count(*) FROM " + table).fetchone()[0]
            for name, table in TABLES.items()}


def check_cells(rows, *, validation):
    from test_literature_structure_integration import COMPONENTS

    assert [row["component"] for row in rows] == COMPONENTS
    expected = [.815409, .75, .61155675, .61155675] if validation else [None, .75, None, None]
    assert [row["value"] for row in rows] == expected
    assert all(row["operand_source_kind"] == "primary_source" for row in rows)
    assert all(row["validation_binding"] == (
        "matching_entry_revision" if validation else "not_supplied") for row in rows)
    assert all(row["unconditional_uncertainty"] == "unreported" for row in rows)
    assert all(row["bound_kind"] == "conditional_arithmetic_outer" for row in rows)
    assert all(row["occupancy_basis"] == "conditioned_selected_model" for row in rows)
    assert all(row["model_number"] == 1 for row in rows)
    assert all(row["local_validation_granularity"] == "residue" for row in rows)
    assert all(row["transform_basis"] == "identity_coordinates_only" for row in rows)
    if not validation:
        assert rows[0]["unavailable_reason"] == "validation_not_joined"


def run_case(directory, name):
    from gene_annotation_episode.communication import plain
    from gene_annotation_episode.domain import canonical
    from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
    from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
    from gene_annotation_episode.literature_episodes import LiteratureEpisodes
    from gene_annotation_episode.literature_structure_storage import LiteratureStructureRepository
    from gene_annotation_episode.runtime import run_workflow
    from gene_annotation_episode.tools import ToolRegistry
    from test_literature_structure_integration import setup_case, FORM
    from test_runtime import FixtureController, ScriptedProvider

    directory.mkdir(parents=True, exist_ok=False)
    validation = name == "primary_geometry_with_validation"
    store, context, arguments = setup_case(directory / "state", validation=validation)
    received = []
    try:
        commission = {"selection": {"kind": "episode_child", "role": "literature",
            "assignment": plain(context.assignment),
            "goal": "Evaluate the four stated contacts in the selected apo-IscR model",
            "scope": plain(context.scope),
            "purpose": "Return only requested source geometry and fit components",
            "schema_json": json.dumps(FORM), "initial_report_json": "{}"}, "report_update": {}}
        action = {"selection": {"kind": "tool", "tool": "literature.structure.populate",
            "arguments": arguments}, "report_update": {}}

        def receive(inputs):
            form, = inputs["child_reports"]
            received.append(form)
            check_cells(form["measurements"], validation=validation)
            assert all(row["geometry_definition"] == arguments["geometry_panel"]
                and row["local_validation_definition"] == arguments["local_panel"]
                for row in form["measurements"])
            commit = {field: [] for field in store.reasoning_schema()["required"]}
            source = store.get(arguments["source_ref"])
            raw = store.get_artifact(source["artifact_ref"])
            start = raw.index(b"IscR")
            commit["source_subjects"] = [{"alias": "studied_molecule", "reference_type": "assay",
                "source_ref": source["id"], "label": "IscR", "anchor": {
                    "source_ref": source["id"], "artifact_ref": source["artifact_ref"],
                    "start": start, "end": start + 4, "quote": "IscR"}}]
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
        operation, = store.db.execute("SELECT * FROM literature_structure_operations WHERE run_id=?",
            (run_id,)).fetchall()
        outcome = json.loads(operation["outcome"])
        repository = LiteratureStructureRepository(store, run_id)
        payload = repository.read(outcome["result"]["sheet_ref"])
        assert outcome["status"] == "completed"
        assert counts(store) == EXPECTED_COUNTS
        assert summary["credit"] == 0 and len(received) == 1
        assert not store.list("observation") and not store.list("assessment")
        actions = [{"episode_id": row["episode_id"], "decision_index": row["decision_index"],
            "selection": json.loads(row["action"]), "credit": row["credit"]}
            for row in store.db.execute("SELECT * FROM runtime_actions ORDER BY rowid")]
        observations = [{"episode_id": row["episode_id"], "unit_index": row["unit_index"],
            "observation": json.loads(row["observation"])}
            for row in store.db.execute("SELECT * FROM runtime_observations ORDER BY rowid")]
        assert len(actions) == len(observations) == 3
        assert all(row["credit"] == 0 for row in actions)
        assert sorted(row["selection"]["kind"] for row in actions) == ["episode_child", "reason", "tool"]
        returns = EpisodeReturnRecords(store, run_id, failure_prefix="structure_original_")
        attempt, = store.db.execute("SELECT parent_episode_id,decision_index FROM runtime_report_attempts").fetchall()
        parent = returns.context(attempt["parent_episode_id"])
        child, frozen_form, schema = returns._attempt(parent, attempt["decision_index"])
        assert child.episode_id == operation["episode_id"]
        assert canonical(schema) == canonical(FORM)
        assert canonical(frozen_form) == canonical(received[0])
        admitted = repository.received_cells(parent)
        assert canonical(admitted) == canonical(received[0]["measurements"])
        check_cells(admitted, validation=validation)
        source_hashes = {reference: hashlib.sha256(
            store.get_artifact(store.get(reference)["artifact_ref"])).hexdigest()
            for reference in payload["direct_input_source_refs"]}
        receipt = {"status": "passed", "case": name, "run_id": run_id, "model_backed": False,
            "execution": "ordinary Workflow with scripted decisions and fixture controller",
            "target_problem": "isolated short-sequence fixture, no target annotation assertion",
            "source_kind": arguments["source_kind"], "outcome": outcome,
            "saved_payload": payload, "actual_frozen_child_form": frozen_form,
            "actual_admitted_parent_subset": admitted, "parent_form_schema": schema,
            "actual_completed_actions": actions, "actual_local_observations": observations,
            **counts(store), "controller_credit": summary["credit"],
            "direct_source_sha256": source_hashes,
            "limits": ["No actual model-backed structural interpretation or live host restart",
                "Only conditional geometry of the selected deposited apo 3CA model is evaluated",
                "RSCC transform and geometry predicates are explicit proposed conventions",
                "Fit and geometry share this structure; no independence is inferred",
                "Coordinate uncertainty, population occupancy and causal isolation remain unreported",
                "General structural alternatives and full A111 remain unfinished",
                "No target correspondence or annotation credit is calculated"]}
        save(directory / "RECEIPT.json", receipt)
        return {key: receipt[key] for key in ("case", "run_id", "model_backed", "source_kind",
            "observations", "population_operations", "parent_receipts")}
    finally:
        store.close()


def disable_source_work():
    """Block entry points and all defining-module parser/arithmetic helpers.

    The operation schema remains available for ordinary selected replay. Source
    witnesses/numeric parsing and the installed CIF parser are also blocked at
    both their defining modules and the structure reader's imported aliases.
    """
    global _DISABLED_SOURCE_WORK
    if _DISABLED_SOURCE_WORK is not None:
        return list(_DISABLED_SOURCE_WORK)
    import importlib
    from gene_annotation_episode import literature_structure_storage as storage
    from gene_annotation_episode import literature_structure_inputs as inputs
    from gene_annotation_episode import literature_structure_calculations as calculations
    from gene_annotation_episode import literature_assay_inputs as assay_inputs

    def forbidden(*args, **kwargs):
        raise AssertionError("source_parsing_coordinate_work_or_recalculation_forbidden")

    disabled = []
    for module in (inputs, calculations):
        for name, value in tuple(vars(module).items()):
            if (getattr(value, "__module__", None) == module.__name__
                    and (inspect.isfunction(value) or inspect.isclass(value))
                    and name != "structure_population_schema"):
                setattr(module, name, forbidden)
                disabled.append(module.__name__ + "." + name)
    for module, names in ((storage, ("read_structure_inputs", "populate_source_geometry")),
            (inputs, ("_Sources", "_numeric", "MMCIF2Dict")),
            (assay_inputs, ("_Sources", "_numeric")),
            (importlib.import_module("Bio.PDB.MMCIF2Dict"), ("MMCIF2Dict",)),
            (inputs.ET, ("fromstring", "XML"))):
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
    from gene_annotation_episode.literature_structure_storage import LiteratureStructureRepository

    original = json.loads((directory / "RECEIPT.json").read_text())
    disabled = disable_source_work()
    with Store(directory / "state") as store:
        run_id = original["run_id"]
        repository = LiteratureStructureRepository(store, run_id)
        returns = EpisodeReturnRecords(store, run_id, failure_prefix="structure_reopen_")
        receipts = EpisodeReceipts(store, run_id)
        operation, = store.db.execute("SELECT * FROM literature_structure_operations WHERE run_id=?",
            (run_id,)).fetchall()
        outcome = json.loads(operation["outcome"])
        assert canonical(outcome) == canonical(original["outcome"])
        sheet_ref = outcome["result"]["sheet_ref"]
        sheet = store.get(sheet_ref)
        allowed = {sheet["artifact_ref"], sheet["request_ref"]}
        original_artifacts = {store.get(reference)["artifact_ref"]
            for reference in original["saved_payload"]["direct_input_source_refs"]}
        assert allowed.isdisjoint(original_artifacts)
        get_artifact, reads = store.get_artifact, []

        def saved_only(reference):
            assert reference in allowed, "original_paper_CIF_or_validation_artifact_read_forbidden"
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
            components=context.assignment["requested_structure_components"])
        attempt, = store.db.execute("SELECT parent_episode_id,decision_index FROM runtime_report_attempts").fetchall()
        parent = returns.context(attempt["parent_episode_id"])
        child, form, schema = returns._attempt(parent, attempt["decision_index"])
        assert child.episode_id == context.episode_id
        assert canonical(schema) == canonical(original["parent_form_schema"])
        assert canonical(form) == canonical(original["actual_frozen_child_form"])
        assert canonical(form["measurements"]) == canonical(cells)
        assert canonical(repository.received_cells(parent)) == canonical(cells)
        assert canonical(original["actual_admitted_parent_subset"]) == canonical(cells)
        check_cells(cells, validation=original["case"] == "primary_geometry_with_validation")
        assert all(row["geometry_definition"] == request["arguments"]["geometry_panel"]
            and row["local_validation_definition"] == request["arguments"]["local_panel"]
            for row in cells)
        assert counts(store) == before == EXPECTED_COUNTS
        actions = [{"episode_id": row["episode_id"], "decision_index": row["decision_index"],
            "selection": json.loads(row["action"]), "credit": row["credit"]}
            for row in store.db.execute("SELECT * FROM runtime_actions ORDER BY rowid")]
        observations = [{"episode_id": row["episode_id"], "unit_index": row["unit_index"],
            "observation": json.loads(row["observation"])}
            for row in store.db.execute("SELECT * FROM runtime_observations ORDER BY rowid")]
        assert canonical(actions) == canonical(original["actual_completed_actions"])
        assert canonical(observations) == canonical(original["actual_local_observations"])
        assert not store.list("observation") and not store.list("assessment")
    return {"case": original["case"], "status": "passed", "cells": len(cells),
        "selected_outcome_equals_saved_outcome": True,
        "actual_frozen_child_form_equals_saved_form": True,
        "actual_parent_subset_equals_saved_cells": True,
        "counts_before_and_after": before, "original_input_bytes_read": False,
        "parser_calculators_and_coordinate_helpers_disabled": disabled,
        "replay_SQL_query_only": True, "allowed_saved_artifacts": sorted(allowed),
        "saved_artifact_reads": reads}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--reopen", action="store_true")
    args = parser.parse_args()
    directory = args.directory.resolve()
    if directory != BASE / "structure_examples_001":
        raise ValueError("owned_structure_example_directory_required")
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
