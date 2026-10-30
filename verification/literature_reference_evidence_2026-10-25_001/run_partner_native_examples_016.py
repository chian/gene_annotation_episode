"""Pinned controlled partner Workflows and fresh, saved-only reconstruction.

Capture is explicitly selected only after coordinator integration/source readiness.
Neither this runner nor its replay acquires sources or makes model science claims.
"""
from __future__ import annotations

import argparse
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import hashlib
import importlib
import inspect
import json
import os
from pathlib import Path
import shutil
import sys
import subprocess

OWNER = Path(os.environ.get("PARTNER_NATIVE_EXAMPLES_OWNER_016", Path(__file__).resolve().parent))
ROOT = OWNER.parents[1]
PIN = OWNER / "partner_native_verification_pin_016"
EXAMPLES = OWNER / "partner_native_examples_001"
NAMES = ("primary_native", "matched_native", "censored_native", "reused_native", "unknown_identity_native", "mixed_spread_native")
FIXTURES = ("test_literature_partner_native_integration.py", "test_literature_reaction_integration.py", "test_runtime.py")
ASSET_NAMES = ("PUBLISHER_RESULTS_RENDERING_001.txt", "PUBLISHER_METHODS_RENDERING_001.txt")
EXPECTED = {"observations": 3, "population_operations": 1, "parent_receipts": 1}
_DISABLED = None
_SOURCE_WORK_ORIGINALS = []


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open("x") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def pin_manifest():
    return json.loads((PIN / "SOURCE_MANIFEST.json").read_text())


def verify_pin():
    manifest = pin_manifest()
    for row in manifest["files"]:
        assert digest(PIN / row["pin_relative_path"]) == row["sha256"], row
    return manifest


def capture_pin():
    """Copy software, fixture code and selected retained assets; verify exact origins."""
    assert not EXAMPLES.exists(), "fresh_examples_required"
    PIN.mkdir(exist_ok=False)
    sources = []
    for package in ("gene_annotation_episode", "method_loop"):
        for path in sorted((ROOT / package).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix not in (".pyc", ".pyo"):
                sources.append((path, path.relative_to(ROOT)))
    sources.extend((ROOT / "tests" / name, Path("tests") / name) for name in FIXTURES)
    sources.extend((OWNER / "primary_pdx_partner_015" / name,
                    Path("assets/primary_pdx_partner_015") / name) for name in ASSET_NAMES)
    sources.append((Path(__file__).resolve(), Path("runner") / Path(__file__).name))
    rows = []
    for source, relative in sources:
        before = digest(source)
        target = PIN / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        assert digest(target) == before
        rows.append({"origin": str(source), "pin_relative_path": str(relative),
                     "sha256": before, "size": target.stat().st_size})
    # Detect concurrent source drift across the entire capture, not just one file.
    for row in rows:
        assert digest(Path(row["origin"])) == row["sha256"], "source_changed_during_capture"
    save(PIN / "SOURCE_MANIFEST.json", {"version": "partner_native_verification_source_pin_016",
        "origin_root": str(ROOT), "files": rows, "originals_equal_after_copy": True,
        "scope": "Complete runtime packages/assets, used test and runner source and two supplied raw publisher text renderings; no environment, databases or live history",
        "model_backed_original_pin_replaced": False})
    verify_pin()


def launch_pin(arguments):
    verify_pin()
    environment = dict(os.environ, PARTNER_NATIVE_EXAMPLES_OWNER_016=str(OWNER), PYTHONDONTWRITEBYTECODE="1")
    os.execve(sys.executable, [sys.executable, "-B", str(PIN / "runner" / Path(__file__).name),
        "--pinned", *arguments], environment)


def configure_pin():
    assert Path(__file__).resolve() == PIN / "runner" / "run_partner_native_examples_016.py"
    # No changing repository/test import path is admitted.
    sys.path[:] = [str(PIN), str(PIN / "tests"), *[entry for entry in sys.path
        if entry and Path(entry).resolve() not in (ROOT, ROOT / "tests", OWNER, PIN / "runner")]]
    sys.dont_write_bytecode = True
    verify_pin()


def runtime_receipt():
    import platform
    import PIL
    modules = []
    for name, module in sorted(sys.modules.items()):
        path = getattr(module, "__file__", None)
        if path and Path(path).is_file() and (name.startswith(("gene_annotation_episode", "method_loop", "PIL"))
                or name in {Path(filename).stem for filename in FIXTURES}):
            resolved = Path(path).resolve()
            if name.startswith(("gene_annotation_episode", "method_loop")) or name.startswith("test_"):
                assert resolved.is_relative_to(PIN), (name, resolved)
            modules.append({"module": name, "path": str(resolved), "sha256": digest(resolved)})
    return {"interpreter": str(Path(sys.executable).resolve()), "interpreter_sha256": digest(Path(sys.executable).resolve()),
        "python_version": sys.version, "platform": platform.platform(), "Pillow_version": PIL.__version__,
        "imported_module_hashes": modules, "source_manifest_sha256": digest(PIN / "SOURCE_MANIFEST.json")}


def fixture():
    module = importlib.import_module("test_literature_partner_native_integration")
    assert tuple(module.CASES) == NAMES
    # Only ORIGINAL setup uses retained reviewed assets; replay never calls setup.
    module.PRIMARY = PIN / "assets" / "primary_pdx_partner_015"
    return module


def counts(store):
    return {name: store.db.execute("SELECT count(*) FROM " + table).fetchone()[0]
        for name, table in (("observations", "runtime_observations"),
            ("population_operations", "literature_partner_operations"), ("parent_receipts", "literature_partner_received"))}


def sql_snapshot(store):
    """Retain every actual SQL table, including frozen history and typed forms."""
    names = [row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    return {name: [dict(row) for row in store.db.execute('SELECT * FROM "' + name.replace('"', '""') + '" ORDER BY rowid')]
        for name in names}


def work_history(store):
    actions = [{"episode_id": row["episode_id"], "decision_index": row["decision_index"],
        "selection": json.loads(row["action"]), "credit": row["credit"]}
        for row in store.db.execute("SELECT * FROM runtime_actions ORDER BY rowid")]
    observations = [{"episode_id": row["episode_id"], "unit_index": row["unit_index"],
        "observation": json.loads(row["observation"])}
        for row in store.db.execute("SELECT * FROM runtime_observations ORDER BY rowid")]
    return actions, observations


def original_setup_assets(directory, name):
    """Copy exact pinned publisher-rendering/transcription inputs for ORIGINAL setup."""
    if name != "primary_native":
        return []
    origin = PIN / "assets" / "primary_pdx_partner_015"
    target = directory / "original_setup_assets"
    target.mkdir()
    pin_rows = {row["pin_relative_path"]: row for row in pin_manifest()["files"]}
    rows = []
    for file in ASSET_NAMES:
        raw = (origin / file).read_bytes()
        (target / file).write_bytes(raw)
        original = pin_rows[str(Path("assets/primary_pdx_partner_015") / file)]
        rows.append({"origin": original["origin"], "pinned_origin": str(origin / file),
            "retained_path": str((target / file).relative_to(directory)),
            "sha256": hashlib.sha256(raw).hexdigest(), "size": len(raw)})
        assert digest(origin / file) == original["sha256"]
    return rows

def run_case(directory, name):
    from gene_annotation_episode.communication import plain
    from gene_annotation_episode.domain import canonical
    from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
    from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
    from gene_annotation_episode.literature_episodes import LiteratureEpisodes
    from gene_annotation_episode.literature_partner_storage import LiteraturePartnerRepository
    from gene_annotation_episode.literature_partner_inputs import partner_population_schema
    from gene_annotation_episode.literature_partner_storage import partner_source_population_schema
    from gene_annotation_episode.runtime import run_workflow
    from gene_annotation_episode.tools import ToolRegistry
    from test_runtime import FixtureController, ScriptedProvider
    from test_literature_reaction_integration import witness

    case = fixture()
    directory.mkdir(exist_ok=False)
    setup_sources = original_setup_assets(directory, name)
    if setup_sources:
        case.PRIMARY = directory / "original_setup_assets"
    store, context, arguments = case.setup_case(directory / "state", case=name)
    received, delivered = [], []
    with store:
        assert arguments["input_mode"] == "native_source_spans"
        for reference in context.received_record_refs:
            assert not store.get_artifact(store.get(reference)["artifact_ref"]).lstrip().startswith(b"{"), "prepared_JSON_source_forbidden"
        commission = {"selection": {"kind": "episode_child", "role": "literature",
            "assignment": plain(context.assignment), "goal": "Evaluate conditional experimental partner evidence",
            "scope": plain(context.scope), "purpose": "Return the requested partner components and limitations",
            "schema_json": json.dumps(case.FORM), "initial_report_json": "{}"}, "report_update": {}}
        action = {"selection": {"kind": "tool", "tool": "literature.partner.source.populate", "arguments": arguments}, "report_update": {}}

        def receive(inputs):
            form, = inputs["child_reports"]
            case.check_rows(form["measurements"], name)
            received.append(form)
            first = form["measurements"][0]
            refs = {row["id"]: row for row in inputs["working_state"]["references"]}
            terms = {row["id"]: row for row in inputs["working_state"]["terms"]}
            for field, expected in (("subject_ref", "Pdx1 (Rv2606c)" if name == "primary_native" else "Tagged subject S"),
                                    ("partner_ref", "Pdx2 (Rv2604c)" if name == "primary_native" else "Partner P")):
                assert refs[first[field]]["label"] == expected
                assert refs[first[field]]["anchor"]["quote"] == expected
            factor_refs = first["comparison_checks"]["reference_omitted"]["differing_factor_refs"]
            if name == "primary_native":
                assert [terms[ref]["label"] for ref in factor_refs] == ["nitrogen_source"]
                assert all(terms[ref]["source_ref"] == arguments["data_source_ref"] for ref in factor_refs)
            delivered.append({"bindings": {field: refs[first[field]] for field in ("subject_ref", "partner_ref")},
                "factor_terms": [terms[ref] for ref in factor_refs],
                "comparison_checks": first["comparison_checks"], "arm_metadata": first["arm_metadata"]})
            commit = {key: [] for key in store.reasoning_schema()["required"]}
            paper = store.get(arguments["source_ref"])
            raw = store.get_artifact(paper["artifact_ref"])
            label = "Pdx1" if name.startswith("primary_") else "Tagged subject S"
            anchor = witness(paper["id"], raw, label)
            anchor.pop("representation")
            anchor["artifact_ref"] = paper["artifact_ref"]
            commit["source_subjects"] = [{"alias": "studied_molecule", "reference_type": "assay",
                "source_ref": paper["id"], "label": label, "anchor": anchor}]
            return {"selection": {"kind": "reason", "commit": commit}, "report_update": {}}

        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, ToolRegistry(store),
            provider=ScriptedProvider([commission, action, receive]), run_dir=directory / "run",
            controller_factory=lambda path, initial: FixtureController(str(path), initial, 2 if len(path) == 1 else 1),
            project_credit=scorer, initial_known_record_refs=list(context.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True),),
            binding_definitions={"credit": scorer.as_record()}))
        run_id, = store.db.execute("SELECT run_id FROM runtime_runs").fetchone()
        operation, = store.db.execute("SELECT * FROM literature_partner_operations").fetchall()
        outcome = json.loads(operation["outcome"])
        repository = LiteraturePartnerRepository(store, run_id)
        payload = repository.read(outcome["result"]["sheet_ref"])
        assert payload["extraction"]["version"] == "literature_partner_inputs_extraction_v2"
        assert set(payload["extraction"]["native_evidence"]) == {"reference", "omitted", "addback"}
        assert outcome["status"] == "completed" and counts(store) == EXPECTED
        assert summary["credit"] == 0 and len(received) == 1
        assert not store.list("observation") and not store.list("assessment")
        actions, observations = work_history(store)
        assert len(actions) == len(observations) == 3
        assert all(row["credit"] == 0 for row in actions)
        assert sorted(row["selection"]["kind"] for row in actions) == ["episode_child", "reason", "tool"]
        returns = EpisodeReturnRecords(store, run_id, failure_prefix="partner_original_")
        attempt, = store.db.execute("SELECT parent_episode_id,decision_index FROM runtime_report_attempts").fetchall()
        parent = returns.context(attempt["parent_episode_id"])
        child, frozen_form, schema = returns._attempt(parent, attempt["decision_index"])
        assert child.episode_id == operation["episode_id"]
        assert canonical(schema) == canonical(case.FORM)
        assert canonical(frozen_form) == canonical(received[0])
        admitted = repository.received_cells(parent)
        assert canonical(admitted) == canonical(received[0]["measurements"])
        case.check_rows(admitted, name)
        all_sources = {reference: store.get(reference) for reference in payload["input_source_refs"]}
        sources = {reference: {"record": record, "sha256": hashlib.sha256(store.get_artifact(record["artifact_ref"])).hexdigest()}
            for reference, record in all_sources.items()}
        save(directory / "FROZEN_ARGUMENT_SCHEMAS.json", {"retained": partner_population_schema(), "native": partner_source_population_schema()})
        save(directory / "FROZEN_OPERATION_CATALOG.json", case.binding_for(store, child).catalog(child))
        save(directory / "SQL_SNAPSHOT.json", sql_snapshot(store))
        save(directory / "DELIVERED_BINDINGS_AND_FACTORS.json", delivered)
        sheet = store.get(outcome["result"]["sheet_ref"])
        receipt = {"status": "passed", "case": name, "run_id": run_id, "model_backed": False,
            "execution": "ordinary Workflow; scripted provider and fixture controller; captured pinned runtime",
            "source_science": "frozen015 coordinator science reused mechanically; no new scientific paper review",
            "target_input": "isolated ATGGCT fixture", "outcome": outcome, "saved_payload": payload,
            "actual_frozen_child_form": frozen_form, "actual_admitted_parent_subset": admitted,
            "parent_form_schema": schema, "actual_completed_actions": actions,
            "actual_local_observations": observations, **counts(store), "controller_credit": summary["credit"],
            "sources_and_lineage": sources, "original_setup_asset_origins": setup_sources,
            "actual_parent_delivered_scientific_records": delivered,
            "source_lineage": "Exactly two pinned raw publisher text renderings supply primary original setup; actual source parent refs retain paper/Methods custody; no native PDF parser or model science is claimed",
            "recipe_representation": "Native source spans point into raw text inputs; source-supplied native numbers, units, spreads and limits are preserved alongside canonical values; normalized recipe is reader-produced, not prepared numeric source JSON",
            "saved_sheet_sha256": hashlib.sha256(store.get_artifact(sheet["artifact_ref"])).hexdigest(),
            "saved_request_sha256": hashlib.sha256(store.get_artifact(sheet["request_ref"])).hexdigest(),
            "sql_snapshot_sha256": digest(directory / "SQL_SNAPSHOT.json"), "runtime": runtime_receipt(),
            "limits": ["Controlled scripted verification, no configured-model scientific interpretation",
                "No live host recovery, new source acquisition or new paper interpretation",
                "Conditional censor domains are not confidence intervals",
                "No universal partner necessity, target correspondence or annotation credit/W05"]}
        save(directory / "RECEIPT.json", receipt)
        return {key: receipt[key] for key in ("case", "run_id", "model_backed", *EXPECTED)}


def disable_source_work(frozen_schemas):
    """Block defining native/scalar/core/retained readers and all loaded aliases."""
    global _DISABLED
    if _DISABLED is not None:
        return _DISABLED
    reader = importlib.import_module("gene_annotation_episode.literature_partner_inputs")
    native = importlib.import_module("gene_annotation_episode.literature_partner_native_inputs")
    scalar = importlib.import_module("gene_annotation_episode.literature_partner_source_fields")
    core = importlib.import_module("gene_annotation_episode.literature_partner_calculations")
    assay = importlib.import_module("gene_annotation_episode.literature_assay_inputs")
    storage = importlib.import_module("gene_annotation_episode.literature_partner_storage")
    _SOURCE_WORK_ORIGINALS.extend((reader.partner_population_schema, native.partner_source_population_schema, storage.partner_source_population_schema))
    schemas = {id(reader.partner_population_schema): "retained",
               id(native.partner_source_population_schema): "native",
               id(storage.partner_source_population_schema): "native"}
    targets = {}
    for module in (reader, native, scalar, core):
        for name, value in vars(module).items():
            if (inspect.isfunction(value) or inspect.isclass(value)) and getattr(value, "__module__", None) == module.__name__:
                targets[id(value)] = module.__name__ + "." + name
                _SOURCE_WORK_ORIGINALS.append(value)
    for name in ("_Sources", "_numeric", "_witness_schema", "_keys", "_text", "_index", "_nullable", "_fail", "_interpretation"):
        targets[id(getattr(assay, name))] = assay.__name__ + "." + name
        _SOURCE_WORK_ORIGINALS.append(getattr(assay, name))

    def forbidden(*args, **kwargs):
        raise AssertionError("partner_native_scalar_core_source_or_witness_work_forbidden")

    def shape_only_schema(kind):
        return lambda: deepcopy(frozen_schemas[kind])

    disabled = []
    for module in tuple(sys.modules.values()):
        if module is None or not getattr(module, "__name__", "").startswith(("gene_annotation_episode", "test_")):
            continue
        for name, value in tuple(vars(module).items()):
            if id(value) in schemas:
                setattr(module, name, shape_only_schema(schemas[id(value)]))
                disabled.append(module.__name__ + "." + name + " -> independently frozen shape-only schema")
            elif id(value) in targets:
                setattr(module, name, forbidden)
                disabled.append(module.__name__ + "." + name)
    _DISABLED = sorted(disabled)
    return _DISABLED


def reopen_case(directory):
    from gene_annotation_episode.domain import canonical
    from gene_annotation_episode.episode_composition import compose_episode_bindings
    from gene_annotation_episode.episode_journal import Journal
    from gene_annotation_episode.episode_receipts import EpisodeReceipts
    from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
    from gene_annotation_episode.literature_partner_storage import LiteraturePartnerRepository
    from gene_annotation_episode.state import Store

    original = json.loads((directory / "RECEIPT.json").read_text())
    case = fixture()
    with Store(directory / "state") as store:
        run_id = original["run_id"]
        repository = LiteraturePartnerRepository(store, run_id)
        returns = EpisodeReturnRecords(store, run_id, failure_prefix="partner_reopen_")
        receipts = EpisodeReceipts(store, run_id)
        operation, = store.db.execute("SELECT * FROM literature_partner_operations").fetchall()
        outcome = json.loads(operation["outcome"])
        assert canonical(outcome) == canonical(original["outcome"])
        context = returns.context(operation["episode_id"])
        context = replace(context, received_record_refs=tuple(receipts.known(context.episode_id)))
        binding = case.binding_for(store, context)
        composition = compose_episode_bindings(binding.services, store=store, journal=Journal(store, run_id),
            execution_backend=None, descriptors=[binding.as_record()], job_episodes=None,
            resource_estimator=None, role_credit_bindings={})
        restored, = composition.bindings
        frozen_schemas = json.loads((directory / "FROZEN_ARGUMENT_SCHEMAS.json").read_text())
        # Ordinary execute regenerates the complete catalog through shared witness
        # schema helpers. Retain the exact ORIGINAL full capability contracts,
        # independently of those disabled source/schema helper implementations.
        frozen_catalog = json.loads((directory / "FROZEN_OPERATION_CATALOG.json").read_text())
        if _DISABLED is None:
            assert canonical(restored.catalog(context)) == canonical(frozen_catalog)
        restored.catalog = lambda _context: deepcopy(frozen_catalog)
        disabled = disable_source_work(frozen_schemas)
        sheet_ref = outcome["result"]["sheet_ref"]
        sheet = store.get(sheet_ref)
        allowed = {sheet["artifact_ref"], sheet["request_ref"]}
        originals = {row["record"]["artifact_ref"] for row in original["sources_and_lineage"].values()}
        assert allowed.isdisjoint(originals)
        get_artifact, reads = store.get_artifact, []

        def saved_only(reference):
            assert reference in allowed, "original_paper_or_recipe_read_forbidden"
            reads.append(reference)
            return get_artifact(reference)

        store.get_artifact = saved_only
        store.db.execute("PRAGMA query_only=ON")
        assert store.db.execute("PRAGMA query_only").fetchone()[0] == 1
        before = sql_snapshot(store)
        assert canonical(before) == canonical(json.loads((directory / "SQL_SNAPSHOT.json").read_text()))
        request = json.loads(store.get_artifact(sheet["request_ref"]))
        assert hashlib.sha256(store.get_artifact(sheet["artifact_ref"])).hexdigest() == original["saved_sheet_sha256"]
        assert hashlib.sha256(store.get_artifact(sheet["request_ref"])).hexdigest() == original["saved_request_sha256"]
        assert asyncio.run(restored.execute(context, "literature.partner.source.populate", request["arguments"], operation["operation_key"])) == outcome
        assert canonical(repository.read(sheet_ref)) == canonical(original["saved_payload"])
        cells = repository.project_cells([sheet_ref], permitted_record_refs=context.received_record_refs,
            components=context.assignment["requested_partner_components"])
        attempt, = store.db.execute("SELECT parent_episode_id,decision_index FROM runtime_report_attempts").fetchall()
        parent = returns.context(attempt["parent_episode_id"])
        child, form, schema = returns._attempt(parent, attempt["decision_index"])
        assert child.episode_id == context.episode_id
        assert canonical(schema) == canonical(original["parent_form_schema"])
        assert canonical(form) == canonical(original["actual_frozen_child_form"])
        assert canonical(form["measurements"]) == canonical(cells)
        assert canonical(repository.received_cells(parent)) == canonical(cells)
        assert canonical(original["actual_admitted_parent_subset"]) == canonical(cells)
        case.check_rows(cells, original["case"])
        assert counts(store) == EXPECTED
        actions, observations = work_history(store)
        assert canonical(actions) == canonical(original["actual_completed_actions"])
        assert canonical(observations) == canonical(original["actual_local_observations"])
        assert not store.list("observation") and not store.list("assessment")
        assert canonical(sql_snapshot(store)) == canonical(before)
    return {"case": original["case"], "status": "passed", "cells": len(cells),
        "selected_outcome_equals_saved": True, "frozen_form_equals_saved": True,
        "admitted_subset_equals_saved": True, "all_SQL_tables_and_histories_unchanged": True, "SQL_table_count": len(before),
        "counts_before_and_after": EXPECTED, "source_work_disabled": disabled,
        "selected_operation_argument_schemas": "retained and native independently frozen shape-only; no source-witness schema helpers",
        "operation_catalog": "exact retained complete original capability contracts",
        "SQL_query_only": True, "original_input_bytes_read": False,
        "allowed_saved_artifacts": sorted(allowed), "actual_artifact_reads": reads,
        "runtime": runtime_receipt()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture-and-run", action="store_true")
    parser.add_argument("--reopen", action="store_true")
    parser.add_argument("--reopen-case", choices=NAMES, help=argparse.SUPPRESS)
    parser.add_argument("--pinned", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    assert not (args.capture_and_run and args.reopen)
    if not args.pinned:
        if args.capture_and_run:
            capture_pin()
        else:
            assert args.reopen, "select_capture_and_run_or_reopen"
        launch_pin(["--reopen"] if args.reopen else [])
    configure_pin()
    if args.reopen_case:
        result = reopen_case(EXAMPLES / args.reopen_case)
        save(EXAMPLES / args.reopen_case / "REOPEN_RECEIPT.json", result)
        print(json.dumps({"case": args.reopen_case, "status": result["status"]}))
        return
    if args.reopen:
        processes = []
        cases = []
        for name in NAMES:
            completed = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()),
                "--pinned", "--reopen-case", name], capture_output=True, text=True, check=False)
            processes.append({"case": name, "returncode": completed.returncode,
                              "stdout": completed.stdout, "stderr": completed.stderr})
            if completed.returncode:
                save(OWNER / "PARTNER_NATIVE_REOPEN_FAILURE_016.json", {"processes": processes})
                raise AssertionError((name, completed.returncode, completed.stderr))
            cases.append(json.loads((EXAMPLES / name / "REOPEN_RECEIPT.json").read_text()))
        result = {"status": "passed", "model_backed": False,
            "scope": "each saved case in a distinct fresh process under the immutable captured runtime; not live host recovery",
            "fresh_process_terminal_receipts": processes, "cases": cases}
        save(EXAMPLES / "REOPEN_RECEIPT.json", result)
        save(OWNER / "PARTNER_NATIVE_REOPEN_RECEIPT_016.json", result)
    else:
        EXAMPLES.mkdir(exist_ok=False)
        result = {"status": "passed", "model_backed": False,
            "cases": [run_case(EXAMPLES / name, name) for name in NAMES]}
        save(EXAMPLES / "EXAMPLES_RECEIPT.json", result)
        save(OWNER / "PARTNER_NATIVE_EXAMPLES_RECEIPT_016.json", result)
    verify_pin()
    save(EXAMPLES / ("REOPEN_FILES_MANIFEST.json" if args.reopen else "ORIGINAL_FILES_MANIFEST.json"),
        {"files": [{"path": str(path.relative_to(EXAMPLES)), "sha256": digest(path), "size": path.stat().st_size}
            for path in sorted(EXAMPLES.rglob("*")) if path.is_file() and not path.name.endswith(("-wal", "-shm"))]})
    if args.reopen:
        save(OWNER / "PARTNER_NATIVE_FINAL_FILES_MANIFEST_016.json",
            {"files": [{"path": str(path.relative_to(OWNER)), "sha256": digest(path), "size": path.stat().st_size}
                for path in sorted(EXAMPLES.rglob("*")) if path.is_file() and not path.name.endswith(("-wal", "-shm"))]})
    print(json.dumps({"status": result["status"], "model_backed": False,
        "cases": [{"case": row["case"], "status": row.get("status", "passed")} for row in result["cases"]]}))


if __name__ == "__main__":
    main()
