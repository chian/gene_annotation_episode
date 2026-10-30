#!/usr/bin/env python3
"""Snapshot an active run read-only, then audit saved literature results offline.

Run with the repository virtualenv Python. Output must be a NEW directory below
this script's owned directory. This command never resumes a workflow. The child
audit process opens only the owned SQLite backup with the pinned real Store.
Scientific source artifacts are copied/hash-checked as opaque bytes, never parsed.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import importlib
import inspect
import json
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys

sys.dont_write_bytecode = True
OWNED = Path(__file__).resolve().parent
VERSION = "live_saved_partner_reconstruction_audit_019_v1"
ROUTES = {"partner": ("LiteraturePartnerRepository", "partner_cells_schema")}
PRIVATE_TABLES = {"runtime_model_calls", "runtime_decision_exchanges"}
_SOURCE_ORIGINALS = []


def now():
    return datetime.now(timezone.utc).isoformat()


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()


def digest_file(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(data)
    return result.hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def require(condition, code):
    if not condition:
        raise AssertionError(code)


def below(path, parent):
    return path != parent and path.is_relative_to(parent)


def pin_fingerprint(pin):
    manifest_path = pin / "SOURCE_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text())
    actual = {}
    for row in manifest["files"]:
        name = row["pin_relative_path"]
        require(name not in actual, "duplicate_pin_manifest_path")
        path = (pin / name).resolve()
        require(below(path, pin) and not Path(name).is_absolute(), "pin_manifest_path_escape")
        require(path.is_file() and path.stat().st_size == row["size"], "pin_size_mismatch:" + name)
        actual[name] = digest_file(path)
        require(actual[name] == row["sha256"], "pin_digest_mismatch:" + name)
    require(actual, "empty_source_pin")
    return {"manifest_sha256": digest_file(manifest_path), "verified_files": len(actual),
            "package_digest": digest_bytes(json.dumps(actual, sort_keys=True).encode())}


def read_only(path):
    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    return connection


def take_snapshot(run, pin, output):
    require(below(output, OWNED), "output_must_be_below_owned_directory")
    require(not output.exists(), "output_directory_must_be_new")
    require(not output.is_relative_to(run) and not output.is_relative_to(pin), "output_overlaps_inputs")
    before = pin_fingerprint(pin)
    output.mkdir(parents=True)
    state = output / "state"
    state.mkdir()
    started = now()
    # BEGIN + the first SELECT pins one WAL-consistent read transaction. The
    # sqlite3 backup API includes committed WAL pages; a raw file copy does not.
    with closing(read_only(run / "state" / "state.sqlite3")) as live:
        live.execute("BEGIN")
        live.execute("SELECT count(*) FROM sqlite_master").fetchone()
        with sqlite3.connect(state / "state.sqlite3") as destination:
            live.backup(destination)
        live.rollback()
    copied = []
    with closing(read_only(state / "state.sqlite3")) as snapshot:
        require(snapshot.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "sqlite_integrity_failure")
        runs = [dict(row) for row in snapshot.execute("SELECT run_id,state,started_at,updated_at FROM runtime_runs")]
        for row in snapshot.execute("SELECT id,sha256,size,media_type FROM artifacts ORDER BY id"):
            row = dict(row)
            require(re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is not None, "invalid_artifact_digest")
            relative = Path("artifacts") / row["sha256"][:2] / row["sha256"]
            source, target = run / "state" / relative, state / relative
            target.parent.mkdir(exist_ok=True, parents=True)
            shutil.copyfile(source, target)
            require(target.stat().st_size == row["size"], "artifact_size_mismatch")
            require(digest_file(target) == row["sha256"], "artifact_digest_mismatch")
            copied.append(row)
    provenance = {}
    receipt_path = run / "RECEIPT.json"
    process_path = run / "PROCESS.json"
    if process_path.is_file():
        process = json.loads(process_path.read_text())
        require(Path(process["pin"]).resolve() == pin, "recorded_process_pin_path_conflict")
        require(process["pin_manifest_sha256"] == before["manifest_sha256"], "recorded_process_pin_digest_conflict")
        caller = Path(process["caller"]).resolve()
        pin_rows = {row["pin_relative_path"]: row for row in json.loads((pin / "SOURCE_MANIFEST.json").read_text())["files"]}
        require(below(caller, pin) and str(caller.relative_to(pin)) in pin_rows, "recorded_caller_not_pinned")
        require(digest_file(caller) == pin_rows[str(caller.relative_to(pin))]["sha256"], "recorded_caller_digest_conflict")
        provenance = {"kind": "original caller process identity record", "caller": str(caller),
            "caller_sha256": digest_file(caller), "pin_manifest_sha256": process["pin_manifest_sha256"],
            "process_record_sha256": digest_file(process_path), "original_interpreter_identity": "not recorded by PROCESS schema",
            "mode": process["mode"], "caller_cwd": process["caller_cwd"], "model_science_established": False,
            "original_loaded_module_receipt": "absent; recorded pinned caller bytes are verified, independent original loaded-module proof unavailable"}
        source_info_path = run / "SOURCE_INPUTS.json"
        if source_info_path.is_file():
            source_info = json.loads(source_info_path.read_text())
            require(source_info["metadata_sha256"] == digest_file(pin / "inputs" / "SOURCE_INPUT_METADATA.json"), "source_input_metadata_digest_conflict")
            require(source_info["job_sha256"] == digest_file(run / "JOB.txt"), "original_job_digest_conflict")
            provenance["source_inputs"] = source_info
            provenance["source_inputs_sha256"] = digest_file(source_info_path)
        else:
            provenance["source_inputs"] = None
    elif receipt_path.is_file():
        receipt = json.loads(receipt_path.read_text())
        runtime = receipt.get("runtime", {})
        require(runtime.get("source_manifest_sha256") == before["manifest_sha256"], "recorded_runtime_pin_conflict")
        require(runtime.get("interpreter_sha256") == digest_file(Path(sys.executable).resolve()), "recorded_interpreter_conflict")
        modules = runtime.get("imported_module_hashes", [])
        for module in modules:
            path = Path(module["path"]).resolve()
            require(path.is_file() and digest_file(path) == module["sha256"], "recorded_runtime_module_conflict:" + module["module"])
            if module["module"].startswith(("gene_annotation_episode", "method_loop", "test_")):
                require(below(path, pin), "recorded_runtime_import_outside_pin")
        provenance = {"kind": "controlled saved original runtime receipt", "model_backed": receipt.get("model_backed"),
            "interpreter": runtime.get("interpreter"), "interpreter_sha256": runtime.get("interpreter_sha256"),
            "source_manifest_sha256": runtime.get("source_manifest_sha256"), "verified_original_imports": len(modules),
            "receipt_sha256": digest_file(receipt_path)}
    else:
        provenance = {"kind": "no original runtime receipt supplied", "original_runtime_identity": "pending"}
    require(pin_fingerprint(pin) == before, "pin_changed_during_snapshot")
    save(output / "snapshot_manifest.json", {
        "version": VERSION, "started_at": started, "backup_completed_at": now(),
        "live_run": str(run), "pin": str(pin), "pin_fingerprint": before,
        "live_connection": "SQLite URI mode=ro; query_only=ON; explicit read transaction; backup API",
        "sqlite_backup_sha256_before_Store_open": digest_file(state / "state.sqlite3"),
        "runs": runs, "artifacts": copied, "original_runtime_provenance": provenance,
        "pinned_runners": [{"path": row["pin_relative_path"], "sha256": row["sha256"]} for row in json.loads((pin / "SOURCE_MANIFEST.json").read_text())["files"] if row["pin_relative_path"].startswith("runner/")],
        "artifact_policy": "Only artifacts named by the backup's artifacts table; opaque byte copy and SHA-256/size check",
        "not_copied_or_queried": ["run/providers", "runtime_model_calls content", "runtime_decision_exchanges content"],
    })


def audit_copy(output, pin):
    require(below(output, OWNED), "audit_copy_must_be_owned")
    manifest = json.loads((output / "snapshot_manifest.json").read_text())
    require(Path(manifest["pin"]) == pin, "snapshot_pin_conflict")
    require(pin_fingerprint(pin) == manifest["pin_fingerprint"], "pin_changed_before_reopen")
    sys.path.insert(0, str(pin))
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.domain import ContractError, canonical, identity, obj
    from gene_annotation_episode.communication import plain, validate_form
    from gene_annotation_episode.episode_receipts import EpisodeReceipts
    from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
    from method_loop.identities import UnitRef
    require(Path(inspect.getfile(Store)).resolve() == pin / "gene_annotation_episode/state.py", "wrong_Store_import")

    modules = {}
    for route in ROUTES:
        modules[route] = importlib.import_module("gene_annotation_episode.literature_" + route + "_storage")

    blocked_calls = []
    disabled = []
    def forbidden(label):
        def fail(*args, **kwargs):
            blocked_calls.append(label)
            raise AssertionError("forbidden_reacquisition_or_delivery:" + label)
        return fail

    # Keep independent frozen argument shapes; disable every loaded producer alias.
    reader = importlib.import_module("gene_annotation_episode.literature_partner_inputs")
    native = importlib.import_module("gene_annotation_episode.literature_partner_native_inputs")
    storage = modules["partner"]
    frozen_schemas = {"retained": deepcopy(reader.partner_population_schema()),
                      "native": deepcopy(storage.partner_source_population_schema())}
    schemas = {id(reader.partner_population_schema): "retained",
               id(native.partner_source_population_schema): "native",
               id(storage.partner_source_population_schema): "native"}
    _SOURCE_ORIGINALS.extend((reader.partner_population_schema, native.partner_source_population_schema,
                              storage.partner_source_population_schema))
    producer_modules = [reader, native] + [importlib.import_module("gene_annotation_episode.literature_partner_" + name)
        for name in ("source_fields", "defined_units", "calculations")]
    for path in sorted((pin / "gene_annotation_episode").glob("literature_*.py")):
        if any(path.stem.endswith(suffix) for suffix in ("_reader", "_calculations", "_inputs", "_source_fields", "_defined_units")):
            module = importlib.import_module("gene_annotation_episode." + path.stem)
            if module not in producer_modules:
                producer_modules.append(module)
    targets = {}
    for module in producer_modules:
        for name, value in vars(module).items():
            if (inspect.isfunction(value) or inspect.isclass(value)) and getattr(value, "__module__", None) == module.__name__:
                targets[id(value)] = module.__name__ + "." + name
                _SOURCE_ORIGINALS.append(value)
    assay = importlib.import_module("gene_annotation_episode.literature_assay_inputs")
    for name in ("_Sources", "_numeric", "_witness_schema", "_keys", "_text", "_index", "_nullable", "_fail", "_interpretation"):
        value = getattr(assay, name)
        targets[id(value)] = assay.__name__ + "." + name
        _SOURCE_ORIGINALS.append(value)
    providers = importlib.import_module("gene_annotation_episode.providers")
    for module in tuple(sys.modules.values()):
        if module is None or not getattr(module, "__name__", "").startswith(("gene_annotation_episode", "test_")):
            continue
        for name, value in tuple(vars(module).items()):
            if id(value) in schemas:
                kind = schemas[id(value)]
                setattr(module, name, lambda kind=kind: deepcopy(frozen_schemas[kind]))
                disabled.append(module.__name__ + "." + name + " -> frozen shape only")
            elif id(value) in targets:
                label = module.__name__ + "." + name
                setattr(module, name, forbidden(label))
                disabled.append(label)
    for cls in (storage.LiteraturePartnerRepository, EpisodeReceipts):
        for name in (("populate", "receive_cells") if cls is storage.LiteraturePartnerRepository else ("bind", "receive")):
            label = cls.__name__ + "." + name
            setattr(cls, name, forbidden(label))
            disabled.append(label)
    providers = importlib.import_module("gene_annotation_episode.providers")
    pinned_rows = {row["pin_relative_path"]: row for row in json.loads((pin / "SOURCE_MANIFEST.json").read_text())["files"]}
    actual_imports = []
    for name, module in sorted(sys.modules.items()):
        if not name.startswith(("gene_annotation_episode", "method_loop")) or not getattr(module, "__file__", None):
            continue
        path = Path(module.__file__).resolve()
        require(below(path, pin), "actual_import_outside_pin:" + name)
        relative = str(path.relative_to(pin))
        require(relative in pinned_rows and digest_file(path) == pinned_rows[relative]["sha256"], "actual_import_not_manifest_identity:" + name)
        actual_imports.append({"module": name, "pin_relative_path": relative, "sha256": digest_file(path)})
    for cls_name in ("ModelConnection", "_SessionConnection"):
        cls = getattr(providers, cls_name)
        for name in ("__init__", "__aenter__", "complete", "catalog"):
            label = cls_name + "." + name
            setattr(cls, name, forbidden(label))
            disabled.append(label)

    denied_host_events = []
    allowed_artifact_paths = set()
    def host_guard(event, args):
        if event == "open" and isinstance(args[0], (str, bytes)):
            path = Path(args[0]).resolve()
            if path.is_relative_to(output / "state" / "artifacts"):
                require(path in allowed_artifact_paths, "direct_non_saved_artifact_read_forbidden")
            require(not path.is_relative_to(Path(manifest["live_run"])), "live_run_file_read_in_audit_subprocess_forbidden")
        if event in {"socket.connect", "socket.getaddrinfo", "subprocess.Popen", "os.system", "os.exec"}:
            denied_host_events.append(event)
            raise AssertionError("offline_audit_forbidden_host_event:" + event)
    sys.addaudithook(host_guard)

    state = output / "state"
    with closing(read_only(state / "state.sqlite3")) as baseline:
        public_tables = sorted(r[0] for r in baseline.execute("SELECT name FROM sqlite_master WHERE type='table'")
            if r[0] not in PRIVATE_TABLES)
    def table_digest(db, names):
        digests = {}
        for name in names:
            # Hash public records without emitting their science/prose payloads.
            rows = [list(row) for row in db.execute('SELECT * FROM "' + name + '" ORDER BY rowid')]
            digests[name] = digest_bytes(canonical(rows).encode())
        return digests

    with closing(read_only(state / "state.sqlite3")) as baseline:
        initial_public_hashes = table_digest(baseline, public_tables)
    with Store(state) as store:
        db = store.db
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        runs = [r[0] for r in db.execute("SELECT run_id FROM runtime_runs")]
        require(len(runs) == 1, "single_run_required")
        run_id = runs[0]
        settings = json.loads(db.execute("SELECT settings FROM runtime_runs WHERE run_id=?", (run_id,)).fetchone()[0])
        saved_configuration = {name: settings.get(name) for name in ("models", "controller", "bindings", "episode_bindings", "episode_execution", "decision_protocol", "episode_progress_receipts", "completed_action_inputs")}
        ordered_completion_mode = settings.get("episode_execution") is not None
        accounting_mode = "bound_ordered_completion_slots" if ordered_completion_mode else "legacy_direct_observation_without_bound_execution"
        source_info = manifest["original_runtime_provenance"].get("source_inputs")
        if source_info is not None:
            for source in source_info["source_records"].values():
                require(store.get(source["id"]) == source, "original_supplied_source_record_conflict")
            require(set(source_info["source_refs"]) == {r["id"] for r in source_info["source_records"].values()}, "source_inputs_reference_set_conflict")
            require(set(source_info["source_refs"]).issubset(settings.get("scientific_knowledge", {}).get("initial_known_record_refs", [])), "initial_source_custody_conflict")
        repos = {}
        for route, (cls_name, _) in ROUTES.items():
            table = "literature_" + route + "_operations"
            if table in tables:
                repos[route] = getattr(modules[route], cls_name)(store, run_id)

        receipts = EpisodeReceipts(store, run_id)
        returns = EpisodeReturnRecords(store, run_id, failure_prefix="audit_")
        require({r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")} == set(public_tables) | (tables & PRIVATE_TABLES), "initialization_changed_table_inventory")
        before = table_digest(db, public_tables)
        require(before == initial_public_hashes, "Store_or_repository_initialization_changed_public_state")
        outside_scope = sorted(t for t in tables if t.startswith("literature_") and not t.startswith("literature_partner_"))
        db.execute("PRAGMA query_only=ON")
        denied_sql = []
        def sql_guard(action, arg1, arg2, database, trigger):
            if action == sqlite3.SQLITE_READ and arg1 in PRIVATE_TABLES:
                denied_sql.append([action, arg1, arg2])
                return sqlite3.SQLITE_DENY
            if action in {sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE,
                          sqlite3.SQLITE_CREATE_TABLE, sqlite3.SQLITE_DROP_TABLE,
                          sqlite3.SQLITE_ALTER_TABLE, sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH,
                          sqlite3.SQLITE_CREATE_INDEX, sqlite3.SQLITE_DROP_INDEX, sqlite3.SQLITE_CREATE_TRIGGER,
                          sqlite3.SQLITE_DROP_TRIGGER, sqlite3.SQLITE_CREATE_VIEW, sqlite3.SQLITE_DROP_VIEW}:
                denied_sql.append([action, arg1, arg2])
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        db.set_authorizer(sql_guard)

        episodes = {row["episode_id"]: dict(row) for row in db.execute("SELECT * FROM runtime_episodes WHERE run_id=?", (run_id,))}
        contexts = {eid: returns.context(eid) for eid in episodes}
        known = {eid: set(receipts.known(eid)) for eid in episodes}
        actions = {(r["episode_id"], r["decision_index"]): dict(r)
                   for r in db.execute("SELECT * FROM runtime_actions WHERE run_id=? ORDER BY episode_id,decision_index", (run_id,))}
        operation_rows = []
        artifact_whitelist = set()
        for route, repo in repos.items():
            for raw in db.execute(f"SELECT * FROM {repo.operations_table} WHERE run_id=? ORDER BY rowid", (run_id,)):
                row = dict(raw)
                result = json.loads(row["outcome"])
                sheet_ref = result["result"]["sheet_ref"]
                source = store.get(sheet_ref)
                artifact_whitelist.update((source["request_ref"], source["artifact_ref"]))
                operation_rows.append((route, row, result, source))
        for ref in artifact_whitelist:
            metadata = db.execute("SELECT sha256 FROM artifacts WHERE id=?", (ref,)).fetchone()
            require(metadata is not None, "saved_artifact_metadata_absent")
            allowed_artifact_paths.add(state / "artifacts" / metadata[0][:2] / metadata[0])
        artifact_reads = Counter()
        original_get_artifact = store.get_artifact
        def saved_only(ref):
            require(ref in artifact_whitelist, "projection_tried_to_open_non_saved_sheet_or_request")
            artifact_reads[ref] += 1
            return original_get_artifact(ref)
        store.get_artifact = saved_only

        sheet_checks = []
        for route, row, outcome, source in operation_rows:
            repo = repos[route]
            eid, key = row["episode_id"], row["operation_key"]
            require(eid in contexts, "operation_episode_missing")
            prefix = f"{run_id}:{eid}:"
            require(key.startswith(prefix) and key[len(prefix):].isdigit(), "operation_key_not_action_identity")
            index = int(key[len(prefix):])
            action_row = actions[(eid, index)]
            action, action_result = json.loads(action_row["action"]), json.loads(action_row["result"])
            require(action["kind"] == "tool" and action["tool"] in {"literature.partner.populate", "literature.partner.source.populate"}, "operation_not_selected_tool")
            require(outcome["status"] in {"completed", "partial"}, "noncompleted_operation")
            require(all(canonical(action_result[k]) == canonical(v) for k, v in outcome.items()), "saved_operation_differs_from_action_outcome")
            sheet_ref = outcome["result"]["sheet_ref"]
            require(outcome["operation_ref"] == identity("operation", {"run_id": run_id, "episode_id": eid, "key": key}), "operation_identity_conflict")
            require(sheet_ref in outcome["record_refs"], "selected_sheet_not_recorded_output")
            raw_payload = store.get_artifact(source["artifact_ref"])
            request = json.loads(store.get_artifact(source["request_ref"]))
            require(request == {"run_id": run_id, "episode_id": eid, "operation_key": key,
                                "arguments": action["arguments"], "scope": plain(contexts[eid].scope)}, "immutable_request_not_selected_arguments")
            require(row["signature"] == canonical({"arguments": action["arguments"],
                "scope": plain(contexts[eid].scope)}), "operation_signature_conflict")
            source_record = {k: v for k, v in source.items() if k not in {"id", "record_type", "origin"}}
            require(identity("source", {"origin": source["origin"], "record": source_record}) == sheet_ref,
                    "sheet_record_content_identity_conflict")
            payload = repo.read(sheet_ref)
            require(canonical(payload) == canonical(json.loads(raw_payload)), "read_changed_saved_payload")
            require(canonical(payload["sheet"]["cells"]) == canonical(outcome["result"]["cells"]), "saved_cells_not_operation_cells")
            require(sheet_ref in known[eid], "selected_sheet_not_received_by_owning_episode")
            receipt = db.execute("SELECT receipt_kind,source_index FROM runtime_record_receipts WHERE run_id=? AND episode_id=? AND record_ref=?",
                                 (run_id, eid, sheet_ref)).fetchone()
            require(receipt is not None and receipt["receipt_kind"] == "own_action" and receipt["source_index"] == index,
                    "selected_sheet_receipt_identity_conflict")
            require(set(payload["input_source_refs"]).issubset(known[eid]), "owning_episode_did_not_receive_source_inputs")
            requested = list(contexts[eid].assignment.get(f"requested_{route}_components", repo.components))
            projected = repo.project_cells([sheet_ref], permitted_record_refs=known[eid], components=requested)
            require([r["component"] for r in projected] == requested, "requested_cell_membership_conflict")
            def resolve(ref, namespace=None, *, permitted=known[eid]):
                return ref in permitted and (namespace is None or store.get(ref)["record_type"] == namespace)
            cell_schema = getattr(modules[route], ROUTES[route][1])()
            validate_form({"cells": projected}, obj({"cells": cell_schema}), resolve)
            for cell in projected:
                raw = payload["sheet"]["cells"][cell["component"]]
                for field in ("value", "lower", "upper", "unit", "status", "origin", "bound_kind", "unavailable_reason"):
                    require(canonical(cell[field]) == canonical(raw[field]), "projection_changed_saved_cell:" + field)
                for field in ("value_candidates",):
                    if field in cell:
                        require(canonical(cell[field]) == canonical(raw[field]), "projection_changed_saved_candidates")
            try:
                repo.project_cells([sheet_ref], permitted_record_refs=[], components=requested)
            except ContractError as exc:
                require(str(exc) == "literature_sheet_not_received", "unexpected_custody_failure")
            else:
                raise AssertionError("unauthorized_projection_accepted")
            sheet_checks.append({"route": route, "episode_id": eid, "decision_index": index,
                "sheet_ref": sheet_ref, "extraction_version": payload["extraction"]["version"], "selected_tool": action["tool"], "payload_artifact_ref": source["artifact_ref"],
                "payload_sha256": digest_bytes(raw_payload), "requested_components": requested,
                "projected_cells": projected, "selected_identity_and_payload_equal": True,
                "typed_projection_and_actual_own_receipt_valid": True,
                "unreceived_sheet_projection_rejected": True})

        # Audit existing attempts only. No form is admitted or redelivered here.
        attempts = []
        for raw in db.execute("SELECT * FROM runtime_report_attempts WHERE run_id=? ORDER BY parent_episode_id,decision_index", (run_id,)):
            attempt = dict(raw)
            item = {k: attempt[k] for k in ("parent_episode_id", "decision_index", "delivery_ref", "child_episode_id")}
            if attempt["failure"] is not None:
                failure = json.loads(attempt["failure"])
                item.update(status="failed_delivery_retained", failure=failure)
            elif attempt["form"] is None:
                item.update(status="pending_no_admitted_form")
            else:
                parent = contexts[attempt["parent_episode_id"]]
                # _attempt's special redelivery fallback reads model selections.
                # Decline that path instead of querying any model-call content.
                if (parent.episode_id, attempt["decision_index"]) not in actions:
                    item.update(status="pending_redelivery_authentication_requires_public_action")
                else:
                    child, form, schema = returns._attempt(parent, attempt["decision_index"])
                    permitted = known[child.episode_id]
                    validate_form(form, schema, lambda ref, ns: ref in permitted and
                        (ns is None or store.get(ref)["record_type"] == ns))
                    fields = {}
                    for name, node in schema["properties"].items():
                        namespace = node.get("x-source")
                        for route, repo in repos.items():
                            if namespace == f"literature_{route}_cells":
                                cells = form[name]
                                repo.validate_returned_values(cells, permitted_record_refs=permitted)
                                requested = child.assignment.get(f"requested_{route}_components")
                                require(requested is None or all(c["component"] in requested for c in cells), "unrequested_returned_component")
                                fields[name] = {"namespace": namespace, "cells": len(cells)}
                    item.update(status="actual_typed_attempt_matches_frozen_child_facts", fields=fields)
            attempts.append(item)

        received = []
        for route, repo in repos.items():
            for raw in db.execute(f"SELECT * FROM {repo.received_table} WHERE run_id=? ORDER BY rowid", (run_id,)):
                row = dict(raw)
                eid, key, cells = row["episode_id"], row["operation_key"], json.loads(row["cells"])
                prefix = f"{run_id}:{eid}:"
                require(key.startswith(prefix) and key.endswith(":typed_form"), "received_subset_not_typed_boundary")
                index = int(key[len(prefix):-len(":typed_form")])
                attempt = db.execute("SELECT * FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=?",
                                     (run_id, eid, index)).fetchone()
                require(attempt is not None and attempt["failure"] is None and attempt["form"] is not None,
                        "received_subset_has_no_actual_successful_attempt")
                schema = json.loads(attempt["contract"])["measurements"]["schema"]
                form = json.loads(attempt["form"])
                actual = [cell for name, node in schema["properties"].items()
                          if node.get("x-source") == f"literature_{route}_cells" for cell in form[name]]
                require(canonical(cells) == canonical(actual), "received_subset_differs_from_actual_admitted_form")
                repo.validate_returned_values(cells, permitted_record_refs=known[eid])
                cell_schema = getattr(modules[route], ROUTES[route][1])()
                validate_form({"cells": cells}, obj({"cells": cell_schema}),
                    lambda ref, ns: ref in known[eid] and (ns is None or store.get(ref)["record_type"] == ns))
                received.append({"route": route, "episode_id": eid, "operation_key": key,
                    "cells": len(cells), "sheet_component_pairs": [[c["sheet_ref"], c["component"]] for c in cells],
                    "exact_actual_admitted_subset_and_saved_cell_equality": True})

        accounting = []
        for eid, episode in episodes.items():
            own_actions = {index: row for (owner, index), row in actions.items() if owner == eid}
            observations = [dict(r) for r in db.execute("SELECT * FROM runtime_observations WHERE run_id=? AND episode_id=? ORDER BY unit_index", (run_id, eid))]
            slots = {r["sequence"]: json.loads(r["slot"]) for r in db.execute("SELECT * FROM runtime_completion_slots WHERE run_id=? AND episode_id=?", (run_id, eid))}
            observed_indices = []
            slot_checks = []
            for sequence, row in enumerate(observations):
                observation = json.loads(row["observation"])
                require(row["unit_index"] == sequence, "noncontiguous_observations")
                index = observation["decision_index"]
                require(index in own_actions and index not in observed_indices, "observation_has_no_unique_own_action")
                action_row = own_actions[index]
                result = None if action_row["result"] is None else json.loads(action_row["result"])
                require(result is not None and result["status"] in {"completed", "partial"}, "observation_for_uncompleted_action")
                require(action_row["credit"] is not None and observation["credit"]["credit"] == action_row["credit"], "observation_credit_conflict")
                require(observation["unit_ref"] == UnitRef(eid, sequence).as_record(), "observation_unit_identity_conflict")
                if sequence in slots:
                    slot = slots[sequence]
                    require(slot["episode_id"] == eid and slot["sequence"] == sequence and slot["label"] == observation["label"] and slot["original_decision_index"] == index and canonical(slot["controller_input"]) == canonical(observation["credit"]), "observed_slot_identity_conflict")
                    slot_checks.append({"unit_index": sequence, "decision_index": index, "status": "original_completion_slot_and_controller_input_match"})
                else:
                    require(not ordered_completion_mode, "bound_ordered_mode_missing_original_completion_slot")
                    slot_checks.append({"unit_index": sequence, "decision_index": index, "status": "absent_original_completion_slot_legacy_boundary_unverified"})
                observed_indices.append(index)
            classifications = []
            for index, row in own_actions.items():
                action = json.loads(row["action"])
                result = None if row["result"] is None else json.loads(row["result"])
                status = None if result is None else result.get("status")
                if index in observed_indices:
                    classification = "completed_observed"
                elif status in {"completed", "partial"}:
                    classification = "completed_result_pending_observation"
                elif result is None or status == "pending":
                    classification = "pending_selected_work"
                else:
                    classification = "failed_attempt_no_observation"
                    require(row["credit"] is None, "failed_attempt_has_completed_credit")
                classifications.append({"decision_index": index, "kind": action["kind"],
                    "tool": action.get("tool"), "result_status": status, "classification": classification,
                    "original_credit": row["credit"],
                    "feedback_code": None if result is None else (result.get("feedback") or {}).get("code")})
            completion = None if episode["completion"] is None else json.loads(episode["completion"])
            if completion is not None:
                require(completion["actions"] == len(observations), "closing_action_count_differs_from_observations")
            last = None if not observations else json.loads(observations[-1]["observation"])
            accounting.append({"episode_id": eid, "path": json.loads(episode["path"]), "state": episode["state"],
                "action_rows": len(own_actions), "observation_rows": len(observations), "completion_slots": len(slots), "original_slot_checks": slot_checks,
                "classification_counts": dict(Counter(r["classification"] for r in classifications)),
                "actions": classifications, "all_existing_observations_match_unique_completed_own_actions": True,
                "last_saved_controller_step": None if last is None else last["step"],
                "no_controller_refit_performed": True})

        after = table_digest(db, public_tables)
        require(after == before and not denied_sql and not blocked_calls and not denied_host_events, "projection_changed_state_or_hit_disabled_path")
        # Reclose/reopen the actual Store too, independently of the original run.
        reopened_payloads = {s["sheet_ref"]: s["payload_sha256"] for s in sheet_checks}

    with Store(state) as reopened:
        reopened.db.execute("PRAGMA query_only=ON")
        reopened.db.set_authorizer(sql_guard)
        reopen_get = reopened.get_artifact
        def reopened_saved_only(ref):
            require(ref in artifact_whitelist, "second_reopen_non_saved_artifact")
            artifact_reads[ref] += 1
            return reopen_get(ref)
        reopened.get_artifact = reopened_saved_only
        for ref, expected in reopened_payloads.items():
            require(digest_bytes(reopened.get_artifact(reopened.get(ref)["artifact_ref"])) == expected,
                    "second_Store_reopen_payload_changed")
        require(table_digest(reopened.db, public_tables) == before, "second_Store_reopen_changed_public_rows")

    require(pin_fingerprint(pin) == manifest["pin_fingerprint"], "pin_changed_during_audit")
    pending = []
    if not operation_rows:
        pending.append("No saved literature population operation exists in this snapshot.")
    if not attempts:
        pending.append("No actual report attempt exists in this snapshot; typed delivery remains unverified.")
    if not received:
        pending.append("No actual admitted parent cell subset exists in this snapshot; parent delivery remains unverified.")
    if any(a["status"].startswith("pending") or a["status"] == "failed_delivery_retained" for a in attempts):
        pending.append("Some actual report attempts are pending, failed, or require public redelivery authentication.")
    if any(check["status"].startswith("absent") for episode in accounting for check in episode["original_slot_checks"]):
        pending.append("Original completion slots are absent for some observations; action/credit/unit identities are checked, but the missing slot/controller-input boundary is unverified.")
    if manifest["original_runtime_provenance"].get("original_runtime_identity") == "pending":
        pending.append("Original caller/runtime identity receipt is absent; actual audit imports and whole pin are verified, original runtime provenance remains unverified.")
    if manifest["original_runtime_provenance"].get("original_loaded_module_receipt"):
        pending.append("Original loaded-module receipt is absent; original pinned caller bytes and recorded PROCESS identity are checked, but independently observed original loaded module paths remain unverified.")
    if any(e["state"] == "active" for e in accounting):
        pending.append("Active episode work/closure remains pending; this audit does not force continuation or closure.")
    receipt = {"version": VERSION, "completed_at": now(), "run_id": run_id,
        "status": "passed_with_pending_boundaries" if pending else "passed",
        "verification_context": "controlled018 saved-run audit validation; not actual model science" if manifest["original_runtime_provenance"].get("model_backed") is False else "read-only saved-record audit; model scientific performance not established by this audit",
        "snapshot_manifest": "snapshot_manifest.json", "pin_fingerprint": manifest["pin_fingerprint"],
        "audit_script_sha256": digest_file(Path(__file__).resolve()),
        "unchanged_recorded_configuration": saved_configuration,
        "original_runtime_provenance": manifest["original_runtime_provenance"], "accounting_mode": accounting_mode,
        "pinned_runners": manifest["pinned_runners"], "actual_verified_pinned_imports": actual_imports, "other_literature_tables_outside_verified_scope": outside_scope,
        "reopen_proof": {"fresh_audit_process": True, "actual_Store_module": str(pin / "gene_annotation_episode/state.py"),
            "actual_repository_modules": [str(Path(inspect.getfile(type(repo))).resolve()) for repo in repos.values()],
            "second_Store_reopen_payloads_equal": True, "host_restart_established": False,
            "public_table_hashes_before_and_after_equal": before, "projection_SQL_query_only": True,
            "live_Store_opened": False, "live_SQLite_writes": False,
            "disabled_entrypoints": sorted(disabled), "disabled_entrypoint_calls": blocked_calls,
            "denied_SQL_attempts": denied_sql, "denied_host_events": denied_host_events, "allowed_saved_artifact_reads": dict(artifact_reads),
            "primary_sources_parsed_or_interpreted": False, "provider_event_files_opened": False,
            "model_call_or_exchange_content_queried": False},
        "sheet_checks": sheet_checks, "actual_report_attempts": attempts,
        "actual_admitted_parent_subsets": received, "episode_accounting": accounting,
        "pending": pending, "limits": [
            "Consistent SQLite backup and immutable artifact custody establish this snapshot only; the live run can advance afterwards.",
            "Requested saved-cell diagnostic projection is not an actual child closure, receipt admission, or parent delivery.",
            "Repository reopen in an offline process does not establish an actual host restart or full workflow reconstruction/resume.",
            "This engineering audit does not assess primary-source science, experimental validity, scoring suitability, final credit, or scientific completion.",
            "SQLite backup includes database tables without interpreting private model-call contents; those tables are not queried by the audit.",
        ]}
    save(output / "receipt.json", receipt)
    report = ["# Saved partner reconstruction audit (controlled validation when supplied018 examples)", "", f"Run: `{run_id}`.", "",
        f"Status: **{receipt['status']}**. Copied {len(manifest['artifacts'])} immutable artifacts from a consistent read-only SQLite backup.",
        f"Verified {len(sheet_checks)} actual selected population sheets, their immutable requests/payloads, requested typed saved-cell projections and owning-episode receipts.",
        f"Actual report attempts: {len(attempts)}. Actual admitted parent subsets: {len(received)}.", "",
        "| Episode | State | Action rows | Observation rows | Accounting |", "|---|---|---:|---:|---|"]
    for row in accounting:
        report.append(f"| {row['path'][-1][0]} | {row['state']} | {row['action_rows']} | {row['observation_rows']} | {row['classification_counts']} |")
    report += ["", "Projection used the pinned actual Store/repository in a fresh offline audit process, followed by a second Store close/reopen. Population, parsing, calculators, model entrypoints and receipt writes were disabled. Projection ran with SQL query-only and a private-table/mutation authorizer; saved public row hashes stayed equal. No live Store was opened and no delivery or observation was created.", "", "Pending:", ""]
    report += ["- " + p for p in pending] if pending else ["- None among the audited actual record boundaries."]
    report += ["", "Limits:", ""] + ["- " + p for p in receipt["limits"]]
    (output / "REPORT.md").write_text("\n".join(report) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path)
    parser.add_argument("--pin", required=True, type=Path)
    parser.add_argument("--output-directory", type=Path)
    parser.add_argument("--reopen-owned-copy", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.reopen_owned_copy:
        audit_copy(args.reopen_owned_copy.resolve(), args.pin.resolve())
        return
    require(args.run is not None and args.output_directory is not None, "run_and_output_directory_required")
    run, pin, output = args.run.resolve(), args.pin.resolve(), args.output_directory.resolve()
    take_snapshot(run, pin, output)
    result = subprocess.run([sys.executable, "-P", "-B", str(Path(__file__).resolve()), "--pin", str(pin),
                             "--reopen-owned-copy", str(output)], capture_output=True, text=True)
    (output / "audit_process_stdout.txt").write_text(result.stdout)
    (output / "audit_process_stderr.txt").write_text(result.stderr)
    if result.returncode:
        save(output / "receipt.json", {"version": VERSION, "status": "failed", "completed_at": now(),
            "failure": result.stderr, "snapshot_manifest": "snapshot_manifest.json"})
        print("Audit failed; see", output / "audit_process_stderr.txt", file=sys.stderr)
        raise SystemExit(result.returncode)
    receipt = json.loads((output / "receipt.json").read_text())
    print(json.dumps({"status": receipt["status"], "receipt": str(output / "receipt.json"),
                      "sheets": len(receipt["sheet_checks"]), "pending": receipt["pending"]}, indent=2))


if __name__ == "__main__":
    main()
