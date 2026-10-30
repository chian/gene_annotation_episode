"""Profile unchanged selected result consumers using one controlled669 case.

Run only in bounded529 with check005 dependencies. The shared668/669 fixture
contains four supplied bases and a never-executed helper. It is engineering
input, not authentic native execution or biological evidence. The fixture's
physical capture/observation ports and inline worker launch are controlled;
all parsing, custody, publication, result and return validators remain real.
"""
from copy import deepcopy
import cProfile
import hashlib
import io
import json
import os
from pathlib import Path
import pstats
import time

import pytest

from gene_annotation_episode import blast_utility_result_views as views
from gene_annotation_episode.communication import form_with_facts
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.form_reference_validation import form_reference_validation
from test_blast_vdb_publication_returns_669 import selected_collect, selected_result_host


def _save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def _function(key):
    return {"file": key[0], "line": key[1], "function": key[2]}


def _profile(directory, name, call):
    profile = cProfile.Profile()
    _save(directory / "active_phase.json", {"phase": name, "state": "running"})
    wall, cpu = time.perf_counter(), time.process_time()
    profile.enable()
    try:
        value = call()
    finally:
        profile.disable()
        elapsed, process = time.perf_counter() - wall, time.process_time() - cpu
        profile.dump_stats(str(directory / (name + ".prof")))
        stats = pstats.Stats(profile)
        rows = []
        for key, (primitive, total, self_time, cumulative, callers) in stats.stats.items():
            rows.append({**_function(key), "primitive_calls": primitive, "total_calls": total,
                "self_seconds": self_time, "cumulative_seconds": cumulative,
                "callers": [{**_function(caller), "counts_and_times": list(counts)
                    if isinstance(counts, tuple) else counts} for caller, counts in callers.items()]})
        _save(directory / (name + ".calls.json"), rows)
        summary = {"phase": name, "elapsed_seconds": elapsed, "process_seconds": process,
            "total_calls": stats.total_calls, "primitive_calls": stats.prim_calls,
            "profile_self_seconds": stats.total_tt,
            "top_cumulative": sorted(rows, key=lambda row: row["cumulative_seconds"], reverse=True)[:35],
            "top_self": sorted(rows, key=lambda row: row["self_seconds"], reverse=True)[:35]}
        _save(directory / (name + ".summary.json"), summary)
        text = io.StringIO()
        pstats.Stats(profile, stream=text).sort_stats("cumulative").print_stats(60)
        pstats.Stats(profile, stream=text).sort_stats("tottime").print_stats(60)
        (directory / (name + ".txt")).write_text(text.getvalue())
        _save(directory / "active_phase.json", {"phase": name, "state": "finished",
            "elapsed_seconds": elapsed})
    return value


def test_one_retained_case_profiles_real_collect_facts_and_parent_admission(tmp_path, monkeypatch):
    attempt = Path(os.environ["HMMER529_ATTEMPT"])
    assert attempt.name.startswith("check133")
    selected = json.loads((attempt / "selected_request.json").read_text())
    assert selected["policy"] == {"memory_bytes": 21474836480,
        "scratch_bytes": 4294967296, "wall_seconds": None}
    assert selected["swap_bytes"] == 0
    directory = attempt / "profile675"
    directory.mkdir(exist_ok=False)
    _save(directory / "active_phase.json", {"phase": "fixture_setup", "state": "running"})
    started = time.perf_counter()
    h = selected_result_host(tmp_path, monkeypatch)
    _save(directory / "fixture_setup.json", {"elapsed_seconds": time.perf_counter() - started,
        "controlled_fixture": "test_blast_vdb_publication_returns_669.selected_result_host",
        "native_helper_executed": False, "selected_sequence_bases": 4})
    try:
        provider = h.family.native_blast_utility_results
        reader = h.family.native_blast_utility_returns
        outcome = _profile(directory, "01_selected_collect", lambda: selected_collect(h, 0))
        body = outcome["result"]
        assert body["complete"] and body["prepared"]["worker_completed"]
        assert len(h.acquisitions) == len(h.observations) == 1
        assert [row["task"] for row in h.worker_calls] == ["parse_original", "project_saved"]
        _save(directory / "selected_case.json", {"assignment": h.assignment,
            "schema": h.schema, "parent_context": h.parent.as_record(),
            "child_context": h.child.as_record(), "source_ref": body["source_ref"],
            "capture": h.capture, "body": body,
            "worker_tasks": [row["task"] for row in h.worker_calls]})

        checked = _profile(directory, "02_saved_body_validation",
            lambda: provider._validate_body(body, h.scope))
        assert checked == body
        facts = _profile(directory, "03_own_facts", lambda: provider.facts(h.child))
        form = form_with_facts({}, h.schema, facts)
        _profile(directory, "04_child_report_validation",
            lambda: reader.validate_received_report(h.child, form, h.schema))
        h.journal.save("runtime_forms", {"episode_id": h.child.episode_id,
            "facts": canonical(facts), "form": canonical(form)})
        h.journal.save("runtime_actions", {"episode_id": h.parent.episode_id, "decision_index": 0,
            "action": canonical({"kind": "episode_child", "role": "results", "scope": h.scope,
                "assignment": h.assignment, "schema_json": canonical(h.schema),
                "purpose": h.child.request["report_contract"]["decision"]}), "result": None})
        h.journal.save("runtime_report_attempts", {"parent_episode_id": h.parent.episode_id,
            "decision_index": 0, "delivery_ref": "controlled-profile-return675",
            "child_episode_id": h.child.episode_id,
            "contract": canonical(h.child.request["report_contract"]), "form": canonical(form), "failure": None})
        operation_key = f"{h.parent.run_id}:{h.parent.episode_id}:0:typed_form"
        admitted = _profile(directory, "05_immediate_parent_admission",
            lambda: reader.record_admission(h.parent, form, h.schema, operation_key))
        assert admitted == body["record_refs"]
        h.receipts.receive(h.parent.episode_id, admitted, kind="child_form", source_index=0)

        def received_report_and_references():
            # This is the existing synchronous validation frame, not a new
            # cache or a changed validator. All repeated consumers still run.
            with form_reference_validation():
                reader.validate_received_report(h.parent, form, h.schema)
                decisions = []
                for namespace in views.IDENTIFIER_NAMESPACES:
                    for reference in views.projection_identifiers(body, namespace):
                        decisions.append([namespace, reference,
                            reader.resolve_received(h.parent, reference, namespace)])
                for reference in admitted:
                    decisions.append(["execution_result", reference,
                        reader.resolve_received(h.parent, reference, "execution_result")])
                return decisions

        decisions = _profile(directory, "06_received_report_and_references",
            received_report_and_references)
        assert decisions and all(row[2] is True for row in decisions)
        assert form["sequences"][0]["fields"] == {"returned_symbol_count": 4}
        assert form["sequences"][0]["sequences"] == {"normalized_sequence": "ACGT"}
        assert "vdb_identity" not in form["sequences"][0]
        for key in views.PROJECTION_V2_FIELDS:
            if key == "record_refs":
                continue
            expected = [body[key]] if key == "status" else body[key]
            assert facts["execution.blast_utility_" + key] == expected
            assert form[key] == expected
        assert len(h.acquisitions) == len(h.observations) == 1
        assert len(h.worker_calls) == 2
        _save(directory / "equality_and_inputs.json", {
            "source_ref": body["source_ref"], "record_refs": admitted,
            "projection_rows": {key: len(value) if isinstance(value, list) else 1
                for key, value in body.items() if key in views.PROJECTION_V2_FIELDS},
            "capture_artifacts": [{"direction": row["direction"], "role": row["role"],
                "ordinal": row["ordinal"], "artifact_ref": row["artifact_ref"],
                "size_bytes": h.store.get(row["artifact_ref"])["size"]} for row in h.capture["artifacts"]],
            "artifact_count": h.store.db.execute("SELECT count(*) FROM artifacts").fetchone()[0],
            "artifact_bytes": h.store.db.execute("SELECT sum(size) FROM artifacts").fetchone()[0],
            "worker_tasks": [row["task"] for row in h.worker_calls],
            "acquisition_count": len(h.acquisitions), "observation_count": len(h.observations),
            "normalized_sequence": form["sequences"][0]["sequences"]["normalized_sequence"],
            "returned_symbol_count": form["sequences"][0]["fields"]["returned_symbol_count"],
            "frozen_projection_fact_form_equality": True, "received_reference_decisions": decisions,
            "form": form})

        # Baseline tamper checks reuse this same case and do not reprepare it.
        forged = deepcopy(form)
        forged["sequences"][0]["fields"]["returned_symbol_count"] = 5
        with pytest.raises(ValueError, match="admitted_form_conflict"):
            reader.record_admission(h.parent, forged, h.schema, operation_key)
        changed = deepcopy(body)
        changed["assignment"]["selector"]["vdb_context"] = False
        with pytest.raises(ValueError):
            provider._validate_body(changed, h.scope)
        _save(directory / "tamper_checks.json", {"frozen_form_value_rejected": True,
            "changed_selection_rejected": True, "original_case_reprepared": False})
        _save(directory / "active_phase.json", {"phase": "complete", "state": "finished"})
    finally:
        h.store.close()


def test_summarize_retained_profiles_without_result_preparation():
    """Format the completed profile inside the same selected bounded runner."""
    attempt = Path(os.environ["HMMER529_ATTEMPT"])
    assert attempt.name.startswith("check133")
    root = Path(__file__).resolve().parents[1]
    baseline = root / "verification/tool_graders_hmmer_map_verification_2026-10-28_529/check133_result_validation675"
    profiles = baseline / "profile675"
    assert json.loads((profiles / "active_phase.json").read_text()) == {
        "phase": "complete", "state": "finished"}
    report = attempt / "profile675_analysis"
    report.mkdir(exist_ok=False)
    pins = {}
    for family in ("source", "dependency", "stdlib", "binary"):
        for row in json.loads((baseline / (family + "_pins_before.json")).read_text()):
            pins[row["path"]] = row
    focus = {
        "validate_native_blast_utility_capture", "qualified_utility_context",
        "_qualified_utility_context", "validate_native_blast_utility_job",
        "validate_native_blast_utility_plan", "validate_native_blast_utility_bundle",
        "compile_native_blast_utility_job", "validate_prepared_utility_result",
        "validate_utility_publication", "_validate_receipt", "validate_worker_plan",
        "validate_worker_manifest", "validate_vdb_context_authentication", "_validate_saved",
        "_retained", "_validate_body", "_own_bodies", "facts", "_received", "_received_values",
        "_values", "record_admission", "_validate_historical", "validate_received_report",
        "parse_blast_vdb_extraction", "blast_utility_fact_sources", "operation_catalog",
        "_compiled_schema_content", "form_validation_value", "_binding_key", "_same",
    }
    def compact(row):
        filename = row["file"]
        path = filename
        for marker in ("/source_snapshot/", "/dependencies/", "/runtime/"):
            if marker in filename:
                path = filename.split(marker, 1)[1]
                break
        return {"file": path, "line": row["line"], "function": row["function"],
            **{name: row[name] for name in ("total_calls", "primitive_calls", "self_seconds", "cumulative_seconds")},
            "source_pin": pins.get(filename), "callers": row["callers"]}
    phases = []
    text = ["One retained controlled669/668 four-base case; no native execution.",
        "Times are cProfile measurements, not estimated production speedups.",
        "Cumulative times overlap and must not be added.", "",
        "phase | elapsed_seconds | process_seconds | total_calls"]
    for summary_file in sorted(profiles.glob("*.summary.json")):
        summary = json.loads(summary_file.read_text())
        rows = json.loads(summary_file.with_name(summary["phase"] + ".calls.json").read_text())
        # Use a path-component condition; the repository itself has the same
        # name as the package, while dependencies also live below the repo.
        app = [row for row in rows if "/source_snapshot/gene_annotation_episode/" in row["file"]]
        phase = {key: summary[key] for key in ("phase", "elapsed_seconds", "process_seconds", "total_calls", "primitive_calls")}
        phase["dominant_application_cumulative"] = [compact(row) for row in sorted(app,
            key=lambda row: row["cumulative_seconds"], reverse=True)[:25]]
        phase["dominant_self"] = [compact(row) for row in sorted(rows,
            key=lambda row: row["self_seconds"], reverse=True)[:15]]
        phase["focus"] = [compact(row) for row in app if row["function"] in focus]
        phases.append(phase)
        text.append(f"{phase['phase']} | {phase['elapsed_seconds']:.6f} | {phase['process_seconds']:.6f} | {phase['total_calls']}")
    text += ["", "Dominant application paths: calls | cumulative | self | file:line(function)"]
    for phase in phases:
        text += ["", phase["phase"]]
        for row in phase["dominant_application_cumulative"][:20]:
            text.append(f"{row['total_calls']} | {row['cumulative_seconds']:.6f} | {row['self_seconds']:.6f} | {row['file']}:{row['line']}({row['function']})")
    saved = next(phase for phase in phases if phase["phase"] == "02_saved_body_validation")
    text += ["", "Saved-body dominant self times: calls | self | cumulative | source"]
    for row in saved["dominant_self"]:
        text.append(f"{row['total_calls']} | {row['self_seconds']:.6f} | {row['cumulative_seconds']:.6f} | {row['file']}:{row['line']}({row['function']})")
    text += ["", "Saved-body selected caller edges: caller -> callee | calls | cumulative"]
    for row in saved["focus"]:
        if row["function"] not in {"validate_native_blast_utility_capture", "qualified_utility_context",
                "validate_native_blast_utility_job", "validate_prepared_utility_result", "_validate_receipt"}:
            continue
        for caller in row["callers"]:
            counts = caller["counts_and_times"]
            text.append(f"{Path(caller['file']).name}:{caller['line']}({caller['function']}) -> "
                f"{row['function']} | {counts[1]} | {counts[3]:.6f}")
    text += ["", "Parser/catalog measurements: phase | calls | cumulative | source"]
    for phase in phases:
        matches = [row for row in phase["focus"] if row["function"] in {
            "parse_blast_vdb_extraction", "blast_utility_fact_sources", "operation_catalog"}]
        for row in matches:
            text.append(f"{phase['phase']} | {row['total_calls']} | {row['cumulative_seconds']:.6f} | {row['file']}:{row['line']}({row['function']})")
    selected = json.loads((profiles / "selected_case.json").read_text())
    inputs = json.loads((profiles / "equality_and_inputs.json").read_text())
    proof_capture = selected["body"]["capture"]
    sizes = {"serialized_body_bytes": len(canonical(selected["body"]).encode()),
        "serialized_capture_bytes": len(canonical(proof_capture).encode()),
        "serialized_schema_bytes": len(canonical(selected["schema"]).encode()),
        "serialized_form_bytes": len(canonical(inputs["form"]).encode()),
        "capture_artifact_rows": len(proof_capture["artifacts"]),
        "prepared_occurrence_rows": len(selected["body"]["prepared"]["occurrences"]),
        "sequence_rows": len(selected["body"]["sequences"]),
        "context_rows": len(selected["body"]["vdb_context"]),
        **{key: inputs[key] for key in ("artifact_count", "artifact_bytes", "acquisition_count", "observation_count", "worker_tasks")}}
    jobs = []
    def saved_jobs(value):
        if isinstance(value, dict):
            if value.get("version") == "native_blast_utility_job_v3":
                jobs.append(canonical(value))
            for item in value.values():
                saved_jobs(item)
        elif isinstance(value, list):
            for item in value:
                saved_jobs(item)
    saved_jobs(selected)
    sizes["retained_native_job_occurrences"] = len(jobs)
    sizes["retained_native_job_distinct_contents"] = len(set(jobs))
    sizes["retained_native_job_serialized_bytes"] = sorted({len(job.encode()) for job in jobs})
    assert jobs and len(set(jobs)) == 1
    selected_pins = {row["source_pin"]["path"]: row["source_pin"] for phase in phases
        for row in [*phase["dominant_application_cumulative"], *phase["dominant_self"], *phase["focus"]]
        if row["source_pin"] is not None}
    _save(report / "phases.json", phases)
    _save(report / "input_sizes.json", sizes)
    _save(report / "dominant_source_pins.json", list(selected_pins.values()))
    _save(report / "profile_pins.json", [{"path": str(path.relative_to(root)),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "size_bytes": path.stat().st_size}
        for path in sorted(profiles.iterdir()) if path.is_file()])
    (report / "PROFILE_SUMMARY.txt").write_text("\n".join(text) + "\n")
    assert len(phases) == 6 and sizes["sequence_rows"] == 1
