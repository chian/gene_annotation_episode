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
VERSION = "live_saved_literature_reconstruction_audit_v1"
ROUTES = {
    "rate": ("LiteratureRateRepository", "rate_cells_schema"),
    "quantity": ("LiteratureQuantityRepository", "quantity_cells_schema"),
    "assay": ("LiteratureAssayRepository", "assay_cells_schema"),
    "ratio": ("LiteratureRatioRepository", "ratio_cells_schema"),
}


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
    manifest = json.loads((pin / "PACKAGE_MANIFEST.json").read_text())
    actual = {}
    for name, expected in manifest.items():
        path = (pin / name).resolve()
        require(below(path, pin), "pin_manifest_path_escape")
        actual[name] = digest_file(path)
        require(actual[name] == expected, "pin_digest_mismatch:" + name)
    return {"manifest_sha256": digest_file(pin / "PACKAGE_MANIFEST.json"),
            "verified_files": len(actual),
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
    require(pin_fingerprint(pin) == before, "pin_changed_during_snapshot")
    save(output / "snapshot_manifest.json", {
        "version": VERSION, "started_at": started, "backup_completed_at": now(),
        "live_run": str(run), "pin": str(pin), "pin_fingerprint": before,
        "live_connection": "SQLite URI mode=ro; query_only=ON; explicit read transaction; backup API",
        "sqlite_backup_sha256_before_Store_open": digest_file(state / "state.sqlite3"),
        "runs": runs, "artifacts": copied,
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

    # Disable both imported aliases in storage modules and defining reader /
    # calculator entrypoints, including any local helper called by those paths.
    for suffix in ("rate_reader", "rate_calculations", "ratio_reader", "ratio_calculations",
                   "prose_reader", "activity_calculations"):
        module = importlib.import_module("gene_annotation_episode.literature_" + suffix)
        for name, value in list(vars(module).items()):
            if inspect.isfunction(value) and value.__module__ == module.__name__:
                label = module.__name__ + "." + name
                setattr(module, name, forbidden(label))
                disabled.append(label)
    inputs = importlib.import_module("gene_annotation_episode.literature_assay_inputs")
    for name in ("read_assay_inputs",):
        setattr(inputs, name, forbidden(inputs.__name__ + "." + name))
        disabled.append(inputs.__name__ + "." + name)
    for route, module in modules.items():
        cls = getattr(module, ROUTES[route][0])
        for method in ("populate", "receive_cells"):
            label = cls.__name__ + "." + method
            setattr(cls, method, forbidden(label))
            disabled.append(label)
        for name in ("read_rate_table", "populate_rate_contrast", "read_jats_relative_percent", "populate_relative_signal"):
            if hasattr(module, name):
                label = module.__name__ + "." + name
                setattr(module, name, forbidden(label))
                disabled.append(label)
    providers = importlib.import_module("gene_annotation_episode.providers")
    for cls_name in ("ModelConnection", "_SessionConnection"):
        cls = getattr(providers, cls_name)
        for name in ("__init__", "__aenter__", "complete", "catalog"):
            label = cls_name + "." + name
            setattr(cls, name, forbidden(label))
            disabled.append(label)

    def host_guard(event, args):
        if event in {"socket.connect", "socket.getaddrinfo", "subprocess.Popen", "os.system", "os.exec"}:
            raise AssertionError("offline_audit_forbidden_host_event:" + event)
    sys.addaudithook(host_guard)

    state = output / "state"
    public_tables = ["runtime_runs", "runtime_episodes", "runtime_actions", "runtime_observations",
                     "runtime_report_attempts", "runtime_forms", "runtime_record_receipts",
                     "runtime_receipt_inheritance", "runtime_completion_slots"]
    def table_digest(db, names):
        digests = {}
        for name in names:
            # Hash public records without emitting their science/prose payloads.
            rows = [list(row) for row in db.execute('SELECT * FROM "' + name + '" ORDER BY rowid')]
            digests[name] = digest_bytes(canonical(rows).encode())
        return digests

    with Store(state) as store:
        db = store.db
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        runs = [r[0] for r in db.execute("SELECT run_id FROM runtime_runs")]
        require(len(runs) == 1, "single_run_required")
        run_id = runs[0]
        settings = json.loads(db.execute("SELECT settings FROM runtime_runs WHERE run_id=?", (run_id,)).fetchone()[0])
        saved_configuration = {name: settings.get(name) for name in ("models", "controller", "bindings", "episode_bindings")}
        repos = {}
        for route, (cls_name, _) in ROUTES.items():
            table = "literature_" + route + "_operations"
            if table in tables:
                repos[route] = getattr(modules[route], cls_name)(store, run_id)
                public_tables += [table, "literature_" + route + "_received"]
        receipts = EpisodeReceipts(store, run_id)
        returns = EpisodeReturnRecords(store, run_id, failure_prefix="audit_")
        before = table_digest(db, public_tables)
        db.execute("PRAGMA query_only=ON")
        denied_sql = []
        def sql_guard(action, arg1, arg2, database, trigger):
            if action == sqlite3.SQLITE_READ and arg1 in {"runtime_model_calls", "runtime_decision_exchanges"}:
                denied_sql.append([action, arg1, arg2])
                return sqlite3.SQLITE_DENY
            if action in {sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE,
                          sqlite3.SQLITE_CREATE_TABLE, sqlite3.SQLITE_DROP_TABLE,
                          sqlite3.SQLITE_ALTER_TABLE, sqlite3.SQLITE_ATTACH}:
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
            require(action["kind"] == "tool" and action["tool"] == f"literature.{route}.populate", "operation_not_selected_tool")
            require(outcome["status"] in {"completed", "partial"}, "noncompleted_operation")
            require(all(canonical(action_result[k]) == canonical(v) for k, v in outcome.items()), "saved_operation_differs_from_action_outcome")
            sheet_ref = outcome["result"]["sheet_ref"]
            require(sheet_ref in outcome["record_refs"], "selected_sheet_not_recorded_output")
            raw_payload = store.get_artifact(source["artifact_ref"])
            request = json.loads(store.get_artifact(source["request_ref"]))
            require(request == {"run_id": run_id, "episode_id": eid, "operation_key": key,
                                "arguments": action["arguments"]}, "immutable_request_not_selected_arguments")
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
            requested = list(contexts[eid].assignment.get(f"requested_{route}_components", repo.components))
            projected = repo.project_cells([sheet_ref], permitted_record_refs=known[eid], components=requested)
            require([r["component"] for r in projected] == requested, "requested_cell_membership_conflict")
            def resolve(ref, namespace=None, *, permitted=known[eid]):
                return ref in permitted and (namespace is None or store.get(ref)["record_type"] == namespace)
            cell_schema = getattr(modules[route], ROUTES[route][1])()
            validate_form({"cells": projected}, obj({"cells": cell_schema}), resolve)
            for cell in projected:
                raw = payload["sheet"]["cells"][cell["component"]]
                for field in ("value", "unit", "status", "origin", "unavailable_reason", "conditional_on"):
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
                "sheet_ref": sheet_ref, "payload_artifact_ref": source["artifact_ref"],
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
                require(sequence in slots, "observed_action_has_no_completion_slot")
                slot = slots[sequence]
                require(slot["original_decision_index"] == index and slot["controller_input"] == observation["credit"], "observed_slot_identity_conflict")
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
                    "feedback_code": None if result is None else (result.get("feedback") or {}).get("code")})
            completion = None if episode["completion"] is None else json.loads(episode["completion"])
            if completion is not None:
                require(completion["actions"] == len(observations), "closing_action_count_differs_from_observations")
            last = None if not observations else json.loads(observations[-1]["observation"])
            accounting.append({"episode_id": eid, "path": json.loads(episode["path"]), "state": episode["state"],
                "action_rows": len(own_actions), "observation_rows": len(observations), "completion_slots": len(slots),
                "classification_counts": dict(Counter(r["classification"] for r in classifications)),
                "actions": classifications, "all_existing_observations_match_unique_completed_own_actions": True,
                "last_saved_controller_decision": None if last is None else last["step"]["decision"],
                "no_controller_refit_performed": True})

        after = table_digest(db, public_tables)
        require(after == before and not denied_sql and not blocked_calls, "projection_changed_state_or_hit_disabled_path")
        # Reclose/reopen the actual Store too, independently of the original run.
        reopened_payloads = {s["sheet_ref"]: s["payload_sha256"] for s in sheet_checks}

    with Store(state) as reopened:
        reopened.db.execute("PRAGMA query_only=ON")
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
    if any(e["state"] == "active" for e in accounting):
        pending.append("Active episode work/closure remains pending; this audit does not force continuation or closure.")
    receipt = {"version": VERSION, "completed_at": now(), "run_id": run_id,
        "status": "passed_with_pending_boundaries" if pending else "passed",
        "snapshot_manifest": "snapshot_manifest.json", "pin_fingerprint": manifest["pin_fingerprint"],
        "audit_script_sha256": digest_file(Path(__file__).resolve()),
        "unchanged_recorded_configuration": saved_configuration,
        "reopen_proof": {"fresh_audit_process": True, "actual_Store_module": str(pin / "gene_annotation_episode/state.py"),
            "actual_repository_modules": [str(Path(inspect.getfile(type(repo))).resolve()) for repo in repos.values()],
            "second_Store_reopen_payloads_equal": True, "host_restart_established": False,
            "public_table_hashes_before_and_after_equal": before, "projection_SQL_query_only": True,
            "live_Store_opened": False, "live_SQLite_writes": False,
            "disabled_entrypoints": sorted(disabled), "disabled_entrypoint_calls": blocked_calls,
            "denied_SQL_attempts": denied_sql, "allowed_saved_artifact_reads": dict(artifact_reads),
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
    report = ["# Saved live-record reconstruction audit", "", f"Run: `{run_id}`.", "",
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
    result = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), "--pin", str(pin),
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
