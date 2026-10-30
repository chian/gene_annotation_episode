"""Authentic tiny VDB utility through the ordinary Workflow, in bounded529.

Only episode choices and scientific/monitor continuation are scripted test
scaffolding. Native execution, capture, original parsing, publication and typed
parent admission are production paths. One selected mode runs once; saved checks
reuse its Store and never substitute an injected native result.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
from types import SimpleNamespace

from Bio import SeqIO
from jsonschema import Draft202012Validator
from method_loop.archive import iter_json
import pytest

from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.blast_database_extraction import normalize_blast_utility_sequence_symbols
from gene_annotation_episode.blast_utility_contracts import validate_blast_utility_result
from gene_annotation_episode.blast_utility_result_views import (
    IDENTIFIER_NAMESPACES, PROJECTION_V2_FIELDS, project_blast_utility_result, projection_identifiers,
)
from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_monitoring import MonitorEpisodes, read_progress
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_episodes import ExecutionEpisodes, RESULTS_VERSION
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.native_blast_database_contracts import validate_native_blast_database_operand
from gene_annotation_episode.native_blast_utility_contracts import (
    BUNDLE_VERSION, requested_job_from_native_blast_utility,
)
from gene_annotation_episode.native_blast_utility_local import local_blast_utility_plan
from gene_annotation_episode.native_blast_utility_result_publication import (
    validate_prepared_utility_result, validate_utility_publication,
)
from gene_annotation_episode.native_blast_utility_result_worker import qualified_utility_context
from gene_annotation_episode.native_blast_vdb_utility_context import validate_vdb_context_authentication
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_native_blast_utility_producer_628 import POLICY
from test_native_blast_utility_workflow_634 import PUBLICATION, child, form_for, selected
from test_native_hmmer_preparation_nested_workflow import provider_value, walk, history


ROOT = Path(__file__).resolve().parents[1]
MODES = ("extract_sequences", "info", "paths", "paths_all")
ENTRIES = ("gnl|SRA|ERR3487613.1.1", "gnl|SRA|ERR3487613.1.2")
EXPECTED_INPUTS = {
    "ERR3487613": (35175, "266e59ba8a5033a084ddb95ab4518fe1c2e71a96e1fc20bb0b959a88c15567d7"),
    "ERR3487613.fasta": (6442, "165c749d742d0436d0482139fa0d734f7c4fdc7d9b428e73efaacaac416a97c8"),
    "offline.kfg": (201, "ab65e06f45d7b49f187f3f79f963e909b8b20e2e2aa2d46b416cc40a9fe2c8fd"),
}
HELPER_SHA = "c342529513815eedbff93e9da277fd4c15966cd8713481ea8626969fec237b10"
INFO_FIELDS = ("vdb_selected_inputs", "vdb_resolved_paths", "vdb_sequence_count",
    "vdb_total_unclipped_bases", "vdb_longest_sequence_bases", "vdb_average_sequence_bases",
    "vdb_csra_inputs", "vdb_reference_sequence_count", "vdb_reference_total_bases")


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def selected_mode():
    if not os.environ.get("HMMER529_ATTEMPT"):
        pytest.skip("authentic VDB Workflow requires bounded529")
    mode = os.environ.get("HMMER_NATIVE_ORACLE_VDB_MODE", "extract_sequences")
    assert mode in MODES
    return mode


def selected_inputs():
    """Use original retained paths and identities, never historical Store IDs."""
    selection = json.loads((ROOT / "verification/tool_graders_blast_vdb_native_observation_2026-10-28_661/SELECTED_REQUEST.json").read_text())
    supplied = {Path(row["path"]).name: row for row in selection["selected_inputs"]}
    assert set(supplied) == set(EXPECTED_INPUTS)
    for name, expected in EXPECTED_INPUTS.items():
        assert (supplied[name]["size_bytes"], supplied[name]["sha256"]) == expected
        assert pin(Path(supplied[name]["path"])) == supplied[name]
    helper = selection["helper_pin"]
    assert helper["size_bytes"] == 26684984 and helper["sha256"] == HELPER_SHA
    assert pin(Path(helper["path"])) == helper
    # Reconcile the original recursive ELF dependency record, excluding the
    # observation-only strace executable and its otherwise unused libraries.
    edges = selection["elf_dependency_bindings"]
    by_parent = {}
    for row in edges:
        by_parent.setdefault(row["parent"], []).append(row)
    launcher = next(row for row in selection["observation_facility_pins"] if Path(row["path"]).name == "bwrap")
    needed, pending = {helper["path"], launcher["path"], "/etc/ld.so.cache"}, [helper["path"], launcher["path"]]
    while pending:
        parent = pending.pop()
        for row in by_parent.get(parent, []):
            path = row["resolved_path"]
            if path not in needed:
                needed.add(path)
                pending.append(path)
    originals = {row["path"]: row for row in selection["runtime_pins"]}
    assert needed <= originals.keys()
    runtime = [deepcopy(row) for row in selection["runtime_pins"] if row["path"] in needed and row["path"] != launcher["path"]]
    for row in [launcher, *runtime]:
        assert pin(Path(row["path"])) == row
    aliases = {}
    for row in edges:
        if row["parent"] not in needed:
            continue
        original = row.get("original_path", row["native_reference"])
        if original.startswith("/") and original != row["resolved_path"]:
            aliases[original] = row["resolved_path"]
    # glibc's retained loader cache may spell the usr-merged system directory
    # as /lib. Each individual alias remains pinned to one explicit file.
    for row in runtime:
        path = row["path"]
        if path.startswith("/usr/lib/x86_64-linux-gnu/"):
            aliases[path.removeprefix("/usr")] = path
    for path, target in list(aliases.items()):
        if path.startswith("/usr/lib/x86_64-linux-gnu/"):
            aliases[path.removeprefix("/usr")] = target
    assert all(target in needed for target in aliases.values())
    return supplied, helper, {"version": "native_blast_vdb_offline_execution_v1",
        "launcher": launcher, "runtime_files": runtime,
        "runtime_aliases": [{"path": path, "target_path": target} for path, target in sorted(aliases.items())],
        "system_interface_profile": "blast_vdb_bwrap_local_v1"}


def stage_job(directory, store, mode):
    supplied, helper, offline = selected_inputs()
    archive, configuration = supplied["ERR3487613"], supplied["offline.kfg"]
    prepared = directory / "supplied"
    prepared.mkdir()
    # This receipt records only actual file identity measurements. It is not a
    # VDB validation, source/member annotation or a native-success certificate.
    receipt_path = prepared / "file-preparation-receipt.json"
    receipt = {"version": "selected_file_identity_receipt_673_v1",
        "method": "sha256_and_byte_count", "files": [archive, configuration],
        "native_validation_performed": False, "biological_relationships_supplied": False}
    save(receipt_path, receipt)
    received = []
    def register(path, name):
        material = store.register_material(path, name=name, use="evidence", format="auto", molecule="unspecified")
        source = store.get(material["source_ref"])
        assert source["origin"] == source["provider"] == "caller"
        assert store.get_artifact(source["artifact_ref"]) == path.read_bytes()
        received.extend([material["source_ref"], source["artifact_ref"]])
        return material["source_ref"], {**pin(path), "artifact_ref": source["artifact_ref"]}
    _, receipt_file = register(receipt_path, "Measured supplied VDB file identities")
    _, config_file = register(Path(configuration["path"]), "Supplied offline VDB configuration")
    _, archive_file = register(Path(archive["path"]), "Supplied tiny VDB archive bytes")
    identity = {"namespace": "supplied_file_sha256", "value": archive["sha256"],
        "version": None, "release": None, "scope": None, "preparation_type": "unknown"}
    preparation = {"method": "other_recorded", "preparation_type": "vdb",
        "software": {"name": "python_hashlib_sha256", "version": None, "executable_sha256": None},
        "argv": None, "input_manifest": None, "receipt": receipt_file}
    declaration_path = prepared / "supplied-file-declaration.json"
    save(declaration_path, {"identity": identity, "preparation": preparation})
    source, _ = register(declaration_path, "Supplied VDB inventory declaration")
    manifest = {"version": "native_blast_prepared_database_manifest_v1", "database_key": "supplied-tiny-vdb",
        "kind": "vdb", "identity": {**identity, "source": {"source_ref": source, "pointer": "/identity"}},
        "native_paths": [archive["path"]], "files": [archive],
        "preparation": {**preparation, "source": {"source_ref": source, "pointer": "/preparation"}},
        "metadata_manifests": [], "access": {"mode": "prepared_local", "offline_configuration": config_file},
        "inventory_complete": True}
    manifest_path = prepared / "prepared-manifest.json"
    save(manifest_path, manifest)
    _, manifest_file = register(manifest_path, "Selected prepared-file manifest")
    database = validate_native_blast_database_operand({"database_key": manifest["database_key"], "role": "target",
        "kind": "vdb", "identity": manifest["identity"], "native_paths": manifest["native_paths"],
        "manifest": manifest, "manifest_file": manifest_file})
    fmt = ("blast_vdb_cmd_table_v1" if mode == "extract_sequences" else
        "blast_vdb_info_text_v1" if mode == "info" else "blast_vdb_paths_text_v1")
    selection = ({"kind": "entries", "source": "entry", "selectors": [
        {"ordinal": i, "value": value} for i, value in enumerate(ENTRIES)], "batch_occurrence_id": None}
        if mode == "extract_sequences" else None)
    operation = {"version": "blast_utility_operation_v3", "program": "blast_vdb_cmd", "mode": mode,
        "molecule": "dna", "database_key": database["database_key"], "input_occurrence_ids": [],
        "parameters": {"database_selection": {"source": "db", "list_occurrence_id": None,
            "inputs": [{"ordinal": 0, "kind": "path", "value": archive["path"],
                "binding_native_path": archive["path"], "list_entry_ordinal": None}]},
            "selection": selection, "include_filtered_reads": False, "line_length": 80, "output_format": fmt}}
    context = {"version": "native_blast_vdb_utility_context_request_v1", "documents": [],
        "source_inputs": [{"ordinal": 0, "selected_input": {"kind": "path", "value": archive["path"]},
            "binding_native_path": archive["path"], "dataset_key": None, "dataset_type": "unknown",
            "snapshot": {"release": None, "snapshot_id": None, "manifest_sha256": None},
            "run_identifiers": [], "source": {"kind": "request"}}],
        "entry_identifier_bindings": [{"selector_ordinal": i, "identifier": {
            "namespace": "blast_vdb_cmd.entry", "value": value, "version": None}, "source": {"kind": "request"}}
            for i, value in enumerate(ENTRIES)] if selection else [],
        "member_bindings": [], "sample_links": [], "dependency_databases": [], "database_lists": [],
        "declared_dependencies": [{"role": "database", "ordinal": 0, "database_key": database["database_key"],
            "native_path_index": 0, "native_reference": archive["path"], "source": "db", "list_ref": None,
            "list_entry_ordinal": None, "declaration": {"kind": "request"}}]}
    job = {"version": "native_blast_utility_job_v3", "operation": operation,
        "software": {"executable": helper["path"], "sha256": helper["sha256"], "engine_version": "2.17.0+"},
        "environment": {"NCBI_VDB_CONFIG": configuration["path"], "BLAST_USAGE_REPORT": "false",
            "NCBI_USAGE_REPORT_ENABLED": "false", "DO_NOT_TRACK": "1", "LC_ALL": "C"},
        "inputs": [], "databases": [database], "vdb_context_request": context, "offline_execution": offline,
        "outputs": [{"role": role, "path_kind": "file", "relative_path": "logs/native." + role,
            "format": fmt if role == "stdout" else "text"} for role in ("stdout", "stderr")]}
    requested_job_from_native_blast_utility(job)
    assert store.db.execute("SELECT count(*) FROM records WHERE record_type='source' AND json_extract(data,'$.version')=?",
        (BUNDLE_VERSION,)).fetchone()[0] == 0
    save(directory / "INPUT_SELECTION.json", {"supplied": supplied, "helper": helper, "offline": offline,
        "registered_initial_refs": received, "archive_artifact_ref": archive_file["artifact_ref"],
        "prior_store_or_source_ids_imported": False, "preparation_receipt": receipt})
    return job, sorted(set(received))


def selector_for(mode):
    value = {"version": "native_blast_utility_result_selector_v2", "sequences": None,
        "database_fields": [], "integrity": None, "preparation": None, "prepared_database": False,
        "include_checks": False, "artifacts": [{"direction": "output", "role": "stdout", "ordinal": 0}],
        "saved_data": ["result"], "paths": None, "vdb_context": False}
    if mode == "extract_sequences":
        value["sequences"] = {"selection": {"kind": "selector_ordinals", "values": [0, 1]},
            "record_fields": ["native_identifier", "native_accession", "native_reported_length",
                "native_length_basis", "returned_symbol_count"],
            "sequence_fields": ["original_sequence", "normalized_sequence"], "include_vdb_identity": False}
    elif mode == "info":
        value["database_fields"] = list(INFO_FIELDS)
    else:
        value["paths"] = {"kinds": ["vdb"] if mode == "paths" else ["vdb", "vdb_alias", "blast_db_alias"],
            "native_path_ordinals": None, "include_sections": True}
        value["vdb_context"] = True
    return value


def fields_for(mode):
    specific = (("sequences",) if mode == "extract_sequences" else ("database_fields",) if mode == "info"
        else ("paths", "path_sections", "vdb_context"))
    return ("status", *specific, "failures", "missing", "artifacts", "saved_data")


def monitor_form():
    sources = MonitorEpisodes(None).fact_sources("monitor")
    properties = {name: deepcopy(sources[source]["report_schema"]) for name, source in {
        "progress": "monitoring_progress_refs", "target": "monitoring_target_handle",
        "latest_state": "monitoring_execution_state", "result_available": "monitoring_result_available"}.items()}
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def retained_history(store, directory, run_id):
    """Protect committed facts while an unfinished parent resumes normally."""
    tables = []
    for table, condition in {
        "runtime_actions": "result IS NOT NULL", "runtime_observations": "1",
        "runtime_model_calls": "response IS NOT NULL", "runtime_estimation_contexts": "1",
        "runtime_forms": "form IS NOT NULL", "runtime_report_attempts": "form IS NOT NULL",
        "runtime_episodes": "state='yielded'", "runtime_record_receipts": "1",
    }.items():
        keys = [row["name"] for row in store.db.execute("PRAGMA table_info(" + table + ")") if row["pk"]]
        assert keys
        rows = [dict(row) for row in store.db.execute(
            "SELECT * FROM " + table + " WHERE run_id=? AND " + condition, (run_id,))]
        tables.append({"table": table, "keys": keys, "rows": rows})
    for table in ("problem", "inputs", "records", "artifacts", "record_roots"):
        keys = [row["name"] for row in store.db.execute("PRAGMA table_info(" + table + ")") if row["pk"]]
        tables.append({"table": table, "keys": keys,
            "rows": [dict(row) for row in store.db.execute("SELECT * FROM " + table)]})
    assignments = [dict(row) for row in store.db.execute(
        "SELECT run_id,episode_id,path,request,initial_credit FROM runtime_episodes WHERE run_id=?", (run_id,))]
    actions = [dict(row) for row in store.db.execute(
        "SELECT run_id,episode_id,decision_index,action FROM runtime_actions WHERE run_id=?", (run_id,))]
    files = {str(path): pin(path) for relative in ("workspace", "run", "supplied", "state/artifacts")
        for path in (directory / relative).rglob("*") if path.is_file()}
    for name in ("INPUT_SELECTION.json", "SELECTED_JOB.json", "NATIVE_HANDLE.json", "NATIVE_CLOSURE.json",
            "DECISION_CALLS.json", "MONITOR_RETURN.json"):
        files[str(directory / name)] = pin(directory / name)
    return {"tables": tables, "assignments": assignments, "actions": actions, "files": files}


def assert_retained_history(store, baseline):
    for table in baseline["tables"]:
        query = "SELECT * FROM " + table["table"] + " WHERE " + " AND ".join(key + "=?" for key in table["keys"])
        for row in table["rows"]:
            actual = store.db.execute(query, [row[key] for key in table["keys"]]).fetchone()
            assert actual is not None and dict(actual) == row, table["table"]
    for row in baseline["assignments"]:
        actual = store.db.execute("SELECT run_id,episode_id,path,request,initial_credit FROM runtime_episodes "
            "WHERE run_id=? AND episode_id=?", (row["run_id"], row["episode_id"])).fetchone()
        assert actual is not None and dict(actual) == row
    for row in baseline["actions"]:
        actual = store.db.execute("SELECT run_id,episode_id,decision_index,action FROM runtime_actions "
            "WHERE run_id=? AND episode_id=? AND decision_index=?",
            (row["run_id"], row["episode_id"], row["decision_index"])).fetchone()
        assert actual is not None and dict(actual) == row
    for path, expected in baseline["files"].items():
        assert pin(Path(path)) == expected


def run_case(directory, mode, *, continuation_output=None):
    continuing = continuation_output is not None
    store = Store(directory / "state")
    if not continuing:
        store.create_problem(raw_sequence="TTGCAATTGCAA", molecule="dna")
    scope = store.validate_scope()
    if continuing:
        original = json.loads((directory / "SELECTED_JOB.json").read_text())
        assert original["scope"] == scope and original["run_id"] == "vdb-workflow673-" + mode
        job, initial = original["job"], original["initial_refs"]
        assert job["operation"]["mode"] == mode
        baseline = retained_history(store, directory, original["run_id"])
        save(continuation_output / "ORIGINAL_HISTORY_BEFORE.json", baseline)
    else:
        job, initial = stage_job(directory, store, mode)
    request, selector = requested_job_from_native_blast_utility(job), selector_for(mode)
    workspace = directory / "workspace"
    if not continuing:
        workspace.mkdir()
    run_id = "vdb-workflow673-" + mode
    variant = {"database_source": "db", "database_input_kind": "path",
        "selection_kind": "entries" if mode == "extract_sequences" else None,
        "entry_source": "entry" if mode == "extract_sequences" else None, "include_filtered_reads": False}
    bindings = [{"program": "blast_vdb_cmd", "mode": mode, "software": job["software"],
        "molecules": ["dna"], "variants": [variant]}]
    if continuing:
        assert bindings == original["bindings"] and selector == original["selector"]
    resources = {"here": {"kind": "local", "workspace": str(workspace), "policy": POLICY,
        "native_blast_utility": bindings}}
    assignment = {"version": "practical_assignment_v1", "assignment_id": "vdb673-" + mode,
        "resource_id": "here", "resource_kind": "local", "workspace": str(workspace), "endpoint": "usable_handoff",
        "requested_job": request, "progress_requirements": [{"key": "handoff", "credit": 7,
            "predicate": {"kind": "requested_job_handoff"}}], "completion_keys": ["handoff"],
        "initial_context": {"revision": 0, "cwd": str(workspace), "environment": {}},
        "inventory_snapshot": {}, "constraints": {"allocation": POLICY}}
    handoff_form = {"type": "object", "additionalProperties": False, "properties": {
        "completed": {"type": "boolean", "x-source": "execution_completed"},
        "references": {"type": "array", "uniqueItems": True, "items": {"type": "string", "format": "reference",
            "x-reference-namespace": "execution_handoff"}, "x-source": "execution_handoff_refs"}},
        "required": ["completed", "references"]}
    results_form, science_form, monitoring_form = form_for(fields_for(mode), True), form_for(fields_for(mode)), monitor_form()
    tools = ToolRegistry(store)
    application = ExecutionServiceFactory(resources, {}, 3, 2, 1, log_window_bytes=128)(
        store, run_id=run_id, directory=directory / "run", tool_registry=tools)
    descriptor = prepare_scientific_binding(run_directory=directory / "run", source_directory=PUBLICATION,
        tool_catalog=tools.catalog(), child_roles=("scientific_process", "launch", "monitor", "results"),
        resource_catalogs=application.resource_tool_catalogs)
    library = ScientificProcessLibrary(directory / "run/scientific-process-library")
    science_assignment = {"selection": {"version": "scientific_process_selection_v3",
        "evidence_axis": library.reference("A101"), "thought_pattern": library.reference("P01"),
        "child_tool_info": [{"name": "native.blast_vdb_cmd." + mode, "resources": "local"}]},
        "evidence_refs": scope["subject_refs"], "constraints": {"no_external_acquisition": True, "allocation": POLICY},
        "context": {"supplied_sequence": "TTGCAATTGCAA", "molecule": "dna", "candidate_annotation_required": False}}
    owner = ExecutionEpisodes(None, store=store, directory=directory / "run", run_id=run_id,
        resources=resources, initial_information={}, tool_registry=tools, handoff_unit=3,
        acquired_record_unit=2, log_window_bytes=128, log_roles=("stdout", "stderr"))

    def controller(path, initial_value):
        def estimate(raw, parameters, contexts):
            horizon = 3 if path[-1][0] == "scientific_process" else 1
            return YieldEstimate(len(raw), NumericBand.exact(0 if len(raw) >= horizon else 1), parameters,
                {"fixture": "scripted_scientific_and_monitor_continuation_not_production_stopping"})
        return YieldController(str(path), initial_value, 0, YieldParameters(100, 50),
            estimate_with_context=estimate if path[-1][0] in {"annotation", "scientific_process", "monitor"} else None)

    class Choices:
        def __init__(self):
            self.calls, self.seen = [], set()
            self.science_calls, self.handoff, self.plan = 0, None, None
            if continuing:
                handle = json.loads((directory / "NATIVE_HANDLE.json").read_text())
                self.handoff, self.plan = handle["handoff"], handle["plan"]

        async def complete(self, episode_id, role, instructions, current, schema):
            assert not continuing, "retained selected Workflow required a new decision"
            self.calls.append({"episode_id": episode_id, "role": role})
            save(directory / "DECISION_CALLS.json", self.calls)
            assert not current.get("feedback"), current.get("feedback")
            if "practical_assignment" in current:
                assert episode_id not in self.seen, "no automatic retry of native work"
                self.seen.add(episode_id)
                assert current["practical_assignment"] == assignment
                answer = selected("practical.job.start")
            elif current.get("execution_assignment", {}).get("version") == "execution_launch_assignment_v1":
                answer = child("launch_local", assignment, scope, handoff_form)
            elif current.get("execution_assignment", {}).get("version") == RESULTS_VERSION:
                assert episode_id not in self.seen, "selected result did not complete; preserve its receipt"
                self.seen.add(episode_id)
                answer = selected("execution.results.collect")
            elif "monitor_assignment" in current:
                assert episode_id not in self.seen
                self.seen.add(episode_id)
                answer = selected("progress.observe")
                answer["selection"]["arguments"] = {"requested_fields": current["monitor_assignment"]["requested_fields"]}
            elif "scientific_process" not in current:
                answer = child("scientific_process", science_assignment, scope, science_form)
            else:
                self.science_calls += 1
                if self.science_calls == 1:
                    answer = child("launch", {"version": "execution_launch_assignment_v1", "requests": {"here": assignment},
                        "immutable_input_versions": [], "constraints": {"allowed_resource_ids": ["here"],
                            "allowed_kinds": ["local"], "allocation": POLICY}}, scope, handoff_form)
                elif self.science_calls == 2:
                    self.handoff, = current["child_reports"][-1]["references"]
                    target = flow.progress_provider.job_provider.targets.read_target(self.handoff, scope)
                    self.plan = local_blast_utility_plan(assignment, target["execution_id"])
                    save(directory / "NATIVE_HANDLE.json", {"plan": self.plan, "handoff": self.handoff})
                    # Observer waiting is test instrumentation; it supplies no
                    # episode action, credit or claimed episode waiting policy.
                    completed = await asyncio.to_thread(native.wait_job, native.NativeJobHandle(Path(target["execution_id"])))
                    save(directory / "NATIVE_CLOSURE.json", {"returncode": completed.returncode, "metadata": completed.metadata})
                    answer = child("monitor", {"version": "monitor_assignment_v1", "target_handle": self.handoff,
                        "requested_fields": ["execution_status", "measurements", "log_windows"],
                        "known_progress_refs": [], "permitted_committed_record_types": []}, scope, monitoring_form)
                else:
                    assert self.science_calls == 3
                    save(directory / "MONITOR_RETURN.json", current["child_reports"][-1])
                    answer = child("results", {"version": RESULTS_VERSION, "handoff_ref": self.handoff,
                        "selector": selector}, scope, results_form)
            if answer["selection"]["kind"] == "episode_child":
                answer["selection"]["goal"] = "Return the selected native " + mode + " facts from the supplied tiny VDB archive."
                answer["selection"]["purpose"] = "Deliver only the requested native values, qualifications and explicitly selected artifacts."
            answer = provider_value(plain(answer), plain(schema))
            Draft202012Validator(plain(schema)).validate(answer)
            return answer

        async def release(self, episode_id):
            pass

    provider = Choices()
    flow = Workflow(store, tools, provider, directory / "run", run_id, controller_factory=controller,
        project_credit=lambda *args, **kwargs: 0, annotation_child_roles=("scientific_process",),
        episode_record_receipts=True, initial_known_record_refs=initial,
        episode_binding_descriptors=(descriptor, *application.episode_binding_descriptors),
        role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider)
    root = flow.build("annotation", "root", "Inspect the explicitly supplied tiny VDB archive.", scope)
    if not continuing:
        save(directory / "SELECTED_JOB.json", {"job": job, "selector": selector, "bindings": bindings,
            "initial_refs": initial, "scope": scope, "run_id": run_id})

    async def execute():
        record = await root.run_async(flow.context)
        await root.build_result(record)
        return record

    try:
        record = asyncio.run(execute())
    except BaseException:
        if continuing:
            assert_retained_history(store, baseline)
        store.close()
        raise
    if continuing:
        assert_retained_history(store, baseline)
        save(continuation_output / "ORIGINAL_HISTORY_AFTER.json", {"unchanged": True,
            "committed_rows": sum(len(table["rows"]) for table in baseline["tables"]),
            "immutable_files": len(baseline["files"]), "native_commands": 0, "new_decisions": 0})
    records = list(walk(json.loads("".join(iter_json(record.as_record())))))
    contexts = {row["episode_id"]: owner.native_blast_utility_returns.context(row["episode_id"]) for row in records}
    result_context, = [context for context in contexts.values() if context.role == "results"]
    science_context, = [context for context in contexts.values() if context.role == "scientific_process"]
    monitor_context, = [context for context in contexts.values() if context.role == "monitor"]
    outcome = json.loads(flow.journal.row("runtime_actions", result_context.episode_id, 0)["result"])
    returned = json.loads(flow.journal.row("runtime_forms", result_context.episode_id)["form"])
    forwarded = json.loads(flow.journal.row("runtime_forms", science_context.episode_id)["form"])
    monitor_return = json.loads(flow.journal.row("runtime_forms", monitor_context.episode_id)["form"])
    case = SimpleNamespace(directory=directory, store=store, flow=flow, owner=owner, provider=provider,
        root=root, record=record, records=records, contexts=contexts, root_context=contexts[record.episode_id],
        result_context=result_context, science_context=science_context, monitor_context=monitor_context,
        outcome=outcome, returned=returned, forwarded=forwarded, monitor_return=monitor_return,
        results_form=results_form, science_form=science_form, mode=mode, job=job,
        selector=selector, scope=scope, run_id=run_id)
    save(directory / "CASE.json", {"mode": mode, "outcome": outcome, "returned": returned,
        "forwarded": forwarded, "monitor_return": monitor_return,
        "record": json.loads("".join(iter_json(record.as_record())))})
    return case


def verify_case(case):
    body, returned, mode = case.outcome["result"], case.returned, case.mode
    capture, prepared = body["capture"], body["prepared"]
    assert body["complete"] and returned["completed"], body
    assert body["version"] == "native_blast_utility_acquired_result_v2"
    bundle = capture["original_bundle"]
    assert bundle["started"] and bundle["returncode"] == 0, bundle["failures"]
    assert bundle["writer_closed"] and bundle["inventory_complete"] and not bundle["failures"]
    assert capture["bundle_validated"] and not capture["failures"]
    assert bundle["requested_job"]["native_blast_utility"] == case.job
    assert len(bundle["offline_execution"]["status_records"]) >= 2
    assert bundle["offline_execution"]["child_exit_code"] == bundle["offline_execution"]["launcher_returncode"] == 0
    assert not bundle["offline_execution"]["failures"]
    assert "--unshare-net" in bundle["offline_execution"]["launcher_argv"]
    assert "--remount-ro" in bundle["offline_execution"]["launcher_argv"]
    validate_prepared_utility_result(case.store, prepared)
    result = json.loads(case.store.get_artifact(prepared["result_artifact_ref"]))
    context = qualified_utility_context(capture)
    assert result["operation"] == case.job["operation"]
    assert result["vdb_context"]["member_bindings"] == result["vdb_context"]["sample_links"] == []
    assert result["vdb_context"]["source_inputs"][0]["dataset_key"] is None
    assert result["vdb_context"]["source_inputs"][0]["dataset_type"] == "unknown"
    stable = json.loads(case.store.get_artifact(prepared["source_grading_artifact_ref"]))["grading"]
    receipt = json.loads(case.store.get_artifact(stable["worker_receipt_artifact_ref"]))
    proof = receipt["manifest"]["context_authentication"]
    validate_vdb_context_authentication(proof, capture=capture, context=context)
    assert proof["passed"] and receipt["manifest"]["completed"]
    assert receipt["plan"]["context"] == context
    assert all(row["source_ref"] == capture["source_ref"] and row["source_namespace"] == "source" for row in proof["provenance"])
    publication_dir = case.owner.native_blast_utility_results._saved_directory(case.result_context.episode_id, body["operation_key"])
    publication = json.loads((publication_dir / "publication.json").read_text())
    validate_utility_publication(case.store, source_ref=body["source_ref"], prepared=prepared,
        selector=case.selector, publication=publication)
    for field in PROJECTION_V2_FIELDS:
        assert publication[field] == body[field]
    for field in fields_for(mode):
        assert returned[field] == ([body[field]] if field == "status" else body[field])
        assert case.forwarded[field] == returned[field]
    case.owner.validate_report(case.result_context, returned, case.results_form)
    case.owner.validate_received_report(case.science_context, returned, case.results_form)
    case.owner.validate_received_report(case.root_context, case.forwarded, case.science_form)
    assert set(returned) == {*fields_for(mode), "completed"}
    stdout, = [row for row in context["occurrences"] if row["direction"] == "output" and row["role"] == "stdout"]
    native_bytes = case.store.get_artifact(stdout["artifact_ref"])
    summary = {"mode": mode, "native_commands": 1, "native_returncode": bundle["returncode"],
        "native_stdout": {k: stdout[k] for k in ("sha256", "size_bytes", "artifact_ref")},
        "typed_immediate_parent_and_root_admission": True, "publication_equal": True,
        "context_authenticated": True, "inferred_biological_identities": False}
    if mode == "extract_sequences":
        assert stdout["size_bytes"] == 594 and stdout["sha256"] == "3be1e1b841530c2818893eb9a396ca8dcd5257203b4778bdda93719fdc47110c"
        stderr, = [row for row in context["occurrences"] if row["direction"] == "output" and row["role"] == "stderr"]
        assert stderr["size_bytes"] == 0 and case.store.get_artifact(stderr["artifact_ref"]) == b""
        companion = json.loads((case.directory / "INPUT_SELECTION.json").read_text())["supplied"]["ERR3487613.fasta"]
        with Path(companion["path"]).open() as stream:
            records = list(SeqIO.parse(stream, "fasta"))
        assert len(records) == 20
        assert len(result["records"]) == len(returned["sequences"]) == 2
        examples = []
        for i, (row, fact) in enumerate(zip(result["records"], returned["sequences"])):
            assert row["native_identifier"] == ENTRIES[i]
            assert row["native_accession"] == "SRA:ERR3487613.1." + str(i + 1)
            assert row["native_reported_length"] == row["returned_symbol_count"] == 250
            assert row["native_length_basis"] == "returned_sequence"
            assert row["original_sequence"] == row["normalized_sequence"] == str(records[i].seq)
            assert fact["fields"] == {key: row[key] for key in case.selector["sequences"]["record_fields"]}
            assert fact["sequences"] == {key: row[key] for key in case.selector["sequences"]["sequence_fields"]}
            assert "vdb_identity" not in fact
            examples.append({"native_identifier": row["native_identifier"], "native_accession": row["native_accession"],
                "native_reported_length": 250, "native_length_basis": "returned_sequence", "shared_symbol_count": 250,
                "companion_record_id": records[i].id, "complete_sequence_equal": True})
        summary["numerical_examples"] = examples
    elif mode == "info":
        originals = result["native_fields"]
        assert {row["field_name"] for row in originals} == set(INFO_FIELDS)
        assert [{k: v for k, v in row.items() if k not in {"source_ref", "subject", "database_key"}}
            for row in returned["database_fields"]] == originals
        native_text = native_bytes.decode("utf-8")
        native_lines = native_text.splitlines()
        for row in originals:
            assert row["value_basis"] == "native_reported" and row["occurrence_id"] == stdout["occurrence_id"]
            if row["value"] is None:
                assert row["missing_reason"] == "native_field_absent"
                assert row["line_number"] is None and row["native_lexeme"] is None
            else:
                assert row["missing_reason"] is None and row["native_lexeme"] in native_text
                assert row["line_number"] is not None
                if isinstance(row["value"], list):
                    assert row["value"] == row["native_lexeme"].split()
                else:
                    assert type(row["value"]) is int
                    assert row["native_lexeme"] in native_lines[row["line_number"] - 1]
                    assert row["value"] == int(row["native_lexeme"].replace(",", ""))
        summary["native_fields"] = originals
        summary["native_lexeme_values_equal"] = True
        summary["average_recomputed_or_substituted"] = False
    else:
        assert returned["paths"]
        assert all(row["native_path"] == case.job["databases"][0]["native_paths"][0] and
            row["matched_dependency_ordinals"] == [0] for row in returned["paths"])
        assert returned["vdb_context"][0]["context"] == result["vdb_context"]
        assert [{k: v for k, v in row.items() if k not in {"source_ref", "database_key", "occurrence_id", "path_ref"}}
            for row in returned["paths"]] == result["path_records"]
        assert [{k: v for k, v in row.items() if k not in {"source_ref", "database_key", "occurrence_id", "section_ref", "section_ordinal"}}
            for row in returned["path_sections"]] == [row for row in result["path_sections"]
                if row["kind"] in case.selector["paths"]["kinds"]]
        native_lines = native_bytes.decode("utf-8").splitlines()
        assert [row["native_path_ordinal"] for row in returned["paths"]] == list(range(len(returned["paths"])))
        for row in returned["paths"]:
            assert native_lines[row["line_number"] - 1] == row["native_path"]
        summary["paths"], summary["path_sections"] = returned["paths"], returned["path_sections"]
        summary["native_ordered_path_lines_equal"] = True
    assert native_bytes
    assert case.monitor_return["target"] == case.provider.handoff
    assert case.monitor_return["latest_state"] == "returned" and case.monitor_return["result_available"]
    for reference in case.monitor_return["progress"]:
        progress = read_progress(case.store, case.run_id, reference, case.scope)
        assert progress["target_handle"] == case.provider.handoff
    grants = {row["artifact_ref"] for row in [*body["artifacts"], *body["saved_data"]]}
    assert body["record_refs"] == list(dict.fromkeys([body["source_ref"], *[row["artifact_ref"] for row in body["artifacts"]],
        *[row["artifact_ref"] for row in body["saved_data"]]]))
    assert len(body["artifacts"]) == len(body["saved_data"]) == 1
    assert body["artifacts"][0]["role"] == "stdout"
    for receiver in (case.science_context, case.root_context):
        known = set(case.flow.receipts.known(receiver.episode_id))
        resolver = case.flow.resolver(case.scope, context=receiver)
        assert {body["source_ref"], *grants} <= known
        assert all(resolver(reference, "artifact") for reference in grants)
        assert not resolver(capture["bundle_artifact_ref"], "artifact")
        for namespace in IDENTIFIER_NAMESPACES:
            for reference in projection_identifiers(body, namespace):
                assert resolver(reference, namespace)
    for row in case.records:
        role = case.contexts[row["episode_id"]].role
        for table in ("runtime_actions", "runtime_observations"):
            assert case.store.db.execute("SELECT count(*) FROM " + table + " WHERE run_id=? AND episode_id=?",
                (case.run_id, row["episode_id"])).fetchone()[0] == row["units_consumed"]
        if role in {"launch_local", "launch", "results"}:
            assert row["units_consumed"] == 1
            assert row["controller_state"]["estimate"]["expected_next_gain"] == NumericBand.exact(0).as_record()
            assert history(row) == [{"launch_local": 7, "launch": 3, "results": 2}[role]]
    completion = case.owner.completion_for_action(case.result_context, body["operation_key"])
    assert completion and case.owner.verify_completion(case.result_context, completion)
    metadata = native.NativeJobHandle(Path(case.provider.plan["identity"]["execution_id"])).read()["metadata"]
    assert metadata["policy"] == POLICY
    assert metadata["verified_cgroup"]["memory_max"] == 20 * 1024**3
    assert metadata["verified_cgroup"]["memory_swap_max"] == 0
    assert metadata["verified_cgroup"]["runtime_max"] == "infinity"
    assert len(list(case.directory.glob("workspace/.episode-operations/*/*/native.json"))) == 1
    assert case.store.count("annotation") == case.store.count("observation") == 0
    summary["one_observation_per_selected_action"] = True
    summary["operational_acquisition_credit"] = 2
    summary["practical_future_expected_credit"] = 0
    summary["monitor_received_original_target"] = True
    save(case.directory / "VERIFIED_VALUES.json", summary)
    return summary


def saved_only_guards(monkeypatch, adapters):
    def forbidden(*args, **kwargs):
        raise AssertionError("saved verification attempted acquisition, native execution or native parsing")

    # The existing immutable writer tries a temporary write even for equal
    # bytes. This explicit test adapter accepts only an already existing exact
    # canonical record; it cannot create or modify anything.
    def equal_existing(path, value):
        expected = (canonical(value) + "\n").encode()
        assert path.is_file() and path.read_bytes() == expected
        adapters.append(str(path))

    for module, name in (
        ("native_blast_utility_driver", "run_native_blast_utility"),
        ("native_blast_vdb_utility_execution", "run_vdb_offline_once"),
        ("native_blast_utility_result_publication", "run_local_job"),
        ("native_blast_utility_acquisition", "_capture_file"),
        ("native_blast_utility_acquisition", "local_blast_utility_plan"),
        ("native_blast_utility_results", "prepare_native_blast_utility_result"),
        ("native_blast_utility_results", "publish_selected_utility_result"),
        ("blast_vdb_utility_inputs", "parse_blast_vdb_extraction"),
        ("blast_vdb_utility_inputs", "normalize_blast_vdb_extraction"),
        ("blast_vdb_utility_inputs", "parse_blast_vdb_inspection"),
        ("blast_vdb_utility_inputs", "parse_blast_vdb_diagnostics"),
        ("blast_vdb_utility_inputs", "read_blast_vdb_sequence_table"),
        ("blast_vdb_inputs", "read_blast_vdb_sequence_table"),
        ("native_blast_vdb_utility_context", "authenticate_vdb_utility_context")):
        monkeypatch.setattr("gene_annotation_episode." + module + "." + name, forbidden)
    for module in ("native_blast_utility_results", "native_blast_utility_acquisition"):
        monkeypatch.setattr("gene_annotation_episode." + module + "._immutable", equal_existing)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    return forbidden


def saved_checks(case, monkeypatch):
    """Use original shared values; deny native readers and all new execution."""
    body = case.outcome["result"]
    context = qualified_utility_context(body["capture"])
    result = json.loads(case.store.get_artifact(body["prepared"]["result_artifact_ref"]))
    protected = {str(path): pin(path) for tree in (case.directory / "workspace", case.directory / "run", case.store.path / "artifacts")
        for path in tree.rglob("*") if path.is_file()}
    before = list(case.store.db.iterdump())
    prior_received = deepcopy(case.owner.native_blast_utility_returns.received_context(case.root_context))
    adapters = []
    forbidden = saved_only_guards(monkeypatch, adapters)
    monkeypatch.setattr(case.owner.job_progress_provider.targets, "observe_target", forbidden)
    validate_blast_utility_result(result)
    numbers = []
    for row in result.get("records", []):
        normalized, count = normalize_blast_utility_sequence_symbols(row["original_sequence"], "dna")
        assert normalized == row["normalized_sequence"] and count == row["returned_symbol_count"]
        numbers.append(count)
    projection = project_blast_utility_result(source_ref=body["source_ref"], operation=context["operation"],
        native_outcome=context["native_outcome"], result=result, prepared_database=None,
        occurrences=context["occurrences"], selector=case.selector, failures=body["prepared"]["failures"],
        saved_data=body["saved_data"], context=context)
    assert all(projection[field] == body[field] for field in PROJECTION_V2_FIELDS)
    original_open = Path.open
    original_selection = json.loads((case.directory / "INPUT_SELECTION.json").read_text())
    original_paths = {Path(row["path"]) for row in original_selection["supplied"].values()}
    original_paths.add(Path(original_selection["helper"]["path"]))
    def retained_only(path, *args, **kwargs):
        if path in original_paths or path.is_relative_to(case.directory / "workspace"):
            raise AssertionError("saved replay attempted to open an original native/input path")
        return original_open(path, *args, **kwargs)
    with monkeypatch.context() as unavailable:
        unavailable.setattr(Path, "open", retained_only)
        replay = asyncio.run(case.owner.execute(case.result_context, "execution.results.collect", {}, body["operation_key"]))
        assert replay == {key: value for key, value in case.outcome.items() if key != "pending_work_after_action"}
        case.flow.receive_form(case.root.source, case.forwarded, case.science_form, 0, redelivery=True)
    assert case.owner.native_blast_utility_returns.received_context(case.root_context) == prior_received
    assert list(case.store.db.iterdump()) == before
    for path, expected in protected.items():
        assert pin(Path(path)) == expected
    assert adapters
    save(case.directory / "SAVED_REPLAY.json", {"native_commands": 0, "native_parsing": 0, "new_acquisitions": 0,
        "shared_recalculated_counts": numbers, "projection_equal": True, "closed_collect_equal": True,
        "typed_root_redelivery_equal": True, "store_dump_equal": True, "protected_immutable_files": len(protected),
        "original_path_open_guard": True,
        "immutable_writer_adapter": "read_existing_and_assert_exact_canonical_bytes_only",
        "adapter_paths": sorted(set(adapters)), "unmodified_no_write_replay_claimed": False})


def test_selected_native_workflow(tmp_path_factory, monkeypatch):
    mode = selected_mode()
    directory = tmp_path_factory.mktemp("vdb-workflow673-" + mode)
    save(Path(os.environ["HMMER529_ATTEMPT"]) / "VDB_CASE_PATH.json", {"directory": str(directory), "mode": mode})
    case = run_case(directory, mode)
    try:
        verify_case(case)
        saved_checks(case, monkeypatch)
    finally:
        case.store.close()


def test_resume_selected_native_workflow(monkeypatch):
    """Resume the original selected tree only after its observer has closed."""
    selected_mode()
    retained = os.environ.get("HMMER_NATIVE_ORACLE_VDB_RESUME")
    if not retained:
        pytest.skip("explicit original 673 tree required")
    directory = Path(retained)
    attempt = Path(os.environ["HMMER529_ATTEMPT"])
    original_attempt = directory.parents[2]
    assert directory.is_absolute() and directory.is_relative_to(Path.cwd())
    assert original_attempt.name.startswith("check131_vdb_workflow673")
    assert original_attempt != attempt and attempt.parent == Path.cwd() == original_attempt.parent
    runner = json.loads((attempt / "selected_request.json").read_text())
    assert runner["policy"] == POLICY and runner["swap_bytes"] == 0
    original_status = native.status(native.NativeJobHandle(original_attempt / "handle.json"))
    assert original_status["terminal"] and original_status["quiescent"], "original observer still owns this Store"
    assert not (directory / "CASE.json").exists(), "closed cases use the read-only verification entry"
    original = json.loads((directory / "SELECTED_JOB.json").read_text())
    output = attempt / "original_tree_evidence"
    save(output / "ORIGINAL_OBSERVER_STATUS.json", original_status)
    adapters = []
    saved_only_guards(monkeypatch, adapters)
    case = run_case(directory, original["job"]["operation"]["mode"], continuation_output=output)
    try:
        verify_case(case)
        saved_checks(case, monkeypatch)
        save(output / "CONTINUATION.json", {"original_directory": str(directory),
            "native_commands": 0, "new_decisions": 0, "actual_workflow_parent_closure": True,
            "immutable_writer_adapter": "read_existing_and_assert_exact_canonical_bytes_only",
            "adapter_paths": sorted(set(adapters)), "unmodified_no_write_replay_claimed": False})
    finally:
        case.store.close()


def test_reopen_selected_native_workflow(monkeypatch):
    """Continue verification of this packet's own closed run without native work."""
    selected_mode()
    retained = os.environ.get("HMMER_NATIVE_ORACLE_VDB_REOPEN")
    if not retained:
        pytest.skip("explicit retained closed 673 case required")
    directory = Path(retained)
    original_attempt = directory.parents[2]
    assert original_attempt.name.startswith("check131_vdb_workflow673")
    original_status = native.status(native.NativeJobHandle(original_attempt / "handle.json"))
    assert original_status["terminal"] and original_status["quiescent"], "original observer still owns this Store"
    selected_job = json.loads((directory / "SELECTED_JOB.json").read_text())
    original = json.loads((directory / "CASE.json").read_text())
    mode, run_id, scope = original["mode"], selected_job["run_id"], selected_job["scope"]
    assert run_id == "vdb-workflow673-" + mode
    handle = json.loads((directory / "NATIVE_HANDLE.json").read_text())
    adapters = []
    saved_only_guards(monkeypatch, adapters)
    store = Store(directory / "state")
    before = list(store.db.iterdump())
    resources = {"here": {"kind": "local", "workspace": str(directory / "workspace"),
        "policy": POLICY, "native_blast_utility": selected_job["bindings"]}}
    tools = ToolRegistry(store)
    application = ExecutionServiceFactory(resources, {}, 3, 2, 1, log_window_bytes=128)(
        store, run_id=run_id, directory=directory / "run", tool_registry=tools)
    descriptor = prepare_scientific_binding(run_directory=directory / "run", source_directory=PUBLICATION,
        tool_catalog=tools.catalog(), child_roles=("scientific_process", "launch", "monitor", "results"),
        resource_catalogs=application.resource_tool_catalogs)

    class NoNewDecisions:
        async def complete(self, *args, **kwargs):
            raise AssertionError("closed verification attempted another episode decision")

        async def release(self, *args):
            pass

    def controller(path, initial_value):
        def estimate(raw, parameters, contexts):
            horizon = 3 if path[-1][0] == "scientific_process" else 1
            return YieldEstimate(len(raw), NumericBand.exact(0 if len(raw) >= horizon else 1), parameters,
                {"fixture": "scripted_scientific_and_monitor_continuation_not_production_stopping"})
        return YieldController(str(path), initial_value, 0, YieldParameters(100, 50),
            estimate_with_context=estimate if path[-1][0] in {"annotation", "scientific_process", "monitor"} else None)

    flow = Workflow(store, tools, NoNewDecisions(), directory / "run", run_id,
        controller_factory=controller, project_credit=lambda *args, **kwargs: 0,
        annotation_child_roles=("scientific_process",),
        episode_record_receipts=True, initial_known_record_refs=selected_job["initial_refs"],
        episode_binding_descriptors=(descriptor, *application.episode_binding_descriptors),
        role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider)
    root = flow.build("annotation", "root", "Inspect the explicitly supplied tiny VDB archive.", scope)
    owner = ExecutionEpisodes(None, store=store, directory=directory / "run", run_id=run_id,
        resources=resources, initial_information={}, tool_registry=tools, handoff_unit=3,
        acquired_record_unit=2, log_window_bytes=128, log_roles=("stdout", "stderr"))
    records = list(walk(original["record"]))
    contexts = {row["episode_id"]: owner.native_blast_utility_returns.context(row["episode_id"]) for row in records}
    by_role = {context.role: context for context in contexts.values()}
    assert root.source.episode_id == original["record"]["episode_id"]
    assert json.loads(flow.journal.row("runtime_actions", by_role["results"].episode_id, 0)["result"]) == original["outcome"]
    for role, field in (("results", "returned"), ("scientific_process", "forwarded"), ("monitor", "monitor_return")):
        assert json.loads(flow.journal.row("runtime_forms", by_role[role].episode_id)["form"]) == original[field]
    case = SimpleNamespace(directory=directory, store=store, flow=flow, owner=owner, root=root,
        provider=SimpleNamespace(plan=handle["plan"], handoff=handle["handoff"]),
        records=records, contexts=contexts, root_context=by_role["annotation"],
        result_context=by_role["results"], science_context=by_role["scientific_process"],
        monitor_context=by_role["monitor"], outcome=original["outcome"], returned=original["returned"],
        forwarded=original["forwarded"], monitor_return=original["monitor_return"],
        results_form=form_for(fields_for(mode), True), science_form=form_for(fields_for(mode)),
        mode=mode, job=selected_job["job"], selector=selected_job["selector"], scope=scope, run_id=run_id)
    try:
        assert list(store.db.iterdump()) == before
        verify_case(case)
        saved_checks(case, monkeypatch)
        assert list(store.db.iterdump()) == before
        save(Path(os.environ["HMMER529_ATTEMPT"]) / "CLOSED_REVALIDATION.json", {
            "original_case": str(directory / "CASE.json"), "original_observer_terminal": True,
            "native_commands": 0, "new_acquisitions": 0, "native_parsing": 0,
            "store_dump_equal": True, "original_selected_job_equal": True,
            "immutable_writer_adapter": "read_existing_and_assert_exact_canonical_bytes_only",
            "adapter_paths": sorted(set(adapters)), "unmodified_no_write_replay_claimed": False})
    finally:
        store.close()


def test_inspect_retained_progress():
    """Read one actual 673 journal snapshot without selecting episode work."""
    selected_mode()
    retained = os.environ.get("HMMER_NATIVE_ORACLE_VDB_REOPEN")
    if not retained:
        pytest.skip("explicit retained 673 case required")
    import sqlite3
    path = Path(retained) / "state/state.sqlite3"
    db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    report = {}
    for table in ("runtime_episodes", "runtime_actions", "runtime_observations", "runtime_forms", "runtime_child_admissions"):
        columns = [row["name"] for row in db.execute("PRAGMA table_info(" + table + ")")]
        if not columns:
            continue
        selected_columns = [key for key in ("episode_id", "parent_episode_id", "child_episode_id", "decision_index",
            "status", "state", "phase", "path") if key in columns]
        report[table] = {"columns": columns, "count": db.execute("SELECT count(*) FROM " + table).fetchone()[0],
            "rows": [dict(row) for row in db.execute("SELECT " + ",".join(selected_columns) + " FROM " + table)]}
    db.close()
    native_handle = Path(retained) / "NATIVE_HANDLE.json"
    if native_handle.exists():
        plan = json.loads(native_handle.read_text())["plan"]
        bundle = json.loads((Path(plan["attempt_directory"]) / "bundle.json").read_text())
        report["native_producer"] = {key: bundle[key] for key in (
            "started", "returncode", "writer_closed", "inventory_complete", "failures")}
        report["native_producer"]["outputs"] = [{key: row[key] for key in (
            "role", "relative_path", "size_bytes", "sha256")} for row in bundle["artifacts"]]
    save(Path(os.environ["HMMER529_ATTEMPT"]) / "PROGRESS_READ.json", report)


def test_retain_closed_info_native_text(monkeypatch):
    """Copy the exact closed native info text for the reported wrapping defect."""
    assert selected_mode() == "info"
    retained = os.environ.get("HMMER_NATIVE_ORACLE_VDB_REOPEN")
    if not retained:
        pytest.skip("explicit retained closed 673 info case required")
    directory = Path(retained)
    original_attempt = directory.parents[2]
    assert original_attempt.name == "check131_vdb_workflow673_info"
    status = native.status(native.NativeJobHandle(original_attempt / "handle.json"))
    assert status["terminal"] and status["quiescent"]
    adapters = []
    saved_only_guards(monkeypatch, adapters)
    handle = json.loads((directory / "NATIVE_HANDLE.json").read_text())
    native_directory = Path(handle["plan"]["attempt_directory"])
    bundle = json.loads((native_directory / "bundle.json").read_text())
    stdout, = [row for row in bundle["artifacts"] if row["role"] == "stdout"]
    source_path = native_directory / stdout["relative_path"]
    assert source_path.is_relative_to(native_directory)
    before = pin(source_path)
    contents = source_path.read_bytes()
    assert len(contents) == stdout["size_bytes"] == 423
    assert hashlib.sha256(contents).hexdigest() == stdout["sha256"] == "cb65d0f9b71a60a74dcbabb602dcd86cdc29e6b5d65c2d0ec3d7c7235c174e0a"
    attempt = Path(os.environ["HMMER529_ATTEMPT"])
    (attempt / "ORIGINAL_INFO_STDOUT.txt").write_bytes(contents)
    save(attempt / "INFO_NATIVE_TEXT.json", {"source_path": str(source_path),
        "original_stdout_pin": before, "text": contents.decode("utf-8"),
        "original_handle_terminal": True, "native_commands": 0, "native_parsing": 0,
        "new_acquisitions": 0, "store_opened": False})
    assert pin(source_path) == before
