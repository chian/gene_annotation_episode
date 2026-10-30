"""Controlled VDB producer/context protocol fixtures, not native measurements.

These bytes and wrapper statuses are explicitly constructed test inputs. Every
application import, Store read, parser, and test executes under bounded529.
No BLAST/VDB helper is invoked by this module.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import native_blast_utility_contracts as contracts
from gene_annotation_episode import native_blast_utility_driver as driver
from gene_annotation_episode import native_blast_utility_acquisition as acquisition
from gene_annotation_episode import native_blast_utility_result_worker as worker
from gene_annotation_episode import native_blast_vdb_utility_context as context_module
from gene_annotation_episode import native_blast_vdb_utility_execution as execution
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.native_blast_database_driver import validate_selected_vdb_file_inventory
from gene_annotation_episode.native_infernal_driver import _encoded
from gene_annotation_episode.state import Store
from test_native_blast_utility_producer_628 import identity, plan_fixture, POLICY


def _identity(value):
    return {"namespace": "controlled", "value": value, "version": None}


def controlled_job(tmp_path, variant="entry", database_source="db", metadata=True):
    """Actual local fixture files and request locators; no prefilled capture IDs."""
    root = tmp_path / "controlled-selection"
    helper = identity(root / "software" / "blast_vdb_cmd", b"controlled helper, never executed\n")
    launcher = identity(root / "software" / "bwrap", b"controlled launcher, never executed\n")
    Path(helper["path"]).chmod(0o755); Path(launcher["path"]).chmod(0o755)
    data = identity(root / "data" / "tiny.sra", b"controlled opaque archive bytes\n")
    offline = identity(root / "config" / "offline.kfg", b"controlled offline configuration\n")
    receipt = identity(root / "preparation.json", b'{"controlled":true}')
    database = {"ordinal": 0, "kind": "path", "value": data["path"], "binding_native_path": data["path"],
                "list_entry_ordinal": 0 if database_source == "dbs_file" else None}
    mode = variant if variant in {"info", "paths", "paths_all"} else "extract_sequences"
    selection = (None if mode != "extract_sequences" else {"kind": variant}
        if variant in {"all_native_sequences", "all_references"} else {"kind": "entries", "source": variant,
            "selectors": [{"ordinal": 0, "value": "controlled_read"}],
            "batch_occurrence_id": "selected-entries" if variant == "entry_batch" else None})
    inputs = []
    if database_source == "dbs_file":
        inputs.append({**identity(root / "dbs.txt", (data["path"] + "\n").encode()),
                       "input_key": "selected-dbs", "role": "database_list", "format": "text"})
    if variant == "entry_batch":
        inputs.append({**identity(root / "entries.txt", b"controlled_read\r\n"),
                       "input_key": "selected-entries", "role": "entry_batch", "format": "text"})
    fmt = "blast_vdb_cmd_table_v1" if mode == "extract_sequences" else "blast_vdb_info_text_v1" if mode == "info" else "blast_vdb_paths_text_v1"
    operation = {"version": "blast_utility_operation_v3", "program": "blast_vdb_cmd", "mode": mode,
        "input_occurrence_ids": [r["input_key"] for r in inputs], "database_key": "controlled-vdb", "molecule": "dna",
        "parameters": {"database_selection": {"source": database_source, "inputs": [database],
            "list_occurrence_id": "selected-dbs" if database_source == "dbs_file" else None},
            "line_length": 80, "selection": selection, "include_filtered_reads": False, "output_format": fmt}}
    source_input = {"ordinal": 0, "selected_input": {"kind": "path", "value": data["path"]},
        "binding_native_path": data["path"], "dataset_key": "controlled-dataset", "dataset_type": "csra" if variant == "all_references" else "sra",
        "snapshot": {"release": None, "snapshot_id": None, "manifest_sha256": None}, "run_identifiers": [],
        "source": {"kind": "selected_json", "document_key": "metadata", "pointer": "/datasets/0"} if metadata else {"kind": "request"}}
    sample = {"sample_key": "controlled-sample", "sample_identifier": _identity("sample-one"), "biosample_identifier": None,
              "source": {"kind": "dataset_sample", "document_key": "metadata", "dataset_pointer": "/datasets/0", "sample_index": 0}}
    member = {"binding_key": "member-one", "native_identifier": "controlled_read", "dataset_key": "controlled-dataset",
        "member_kind": "read", "member_identifier": _identity("member-one"), "relationship": "reported_origin",
        "read_identity": {"native_read_name": "controlled_read", "spot_id": None, "read_index": None,
            "source": {"kind": "selected_json", "document_key": "metadata", "pointer": "/members/0/read_identity"}},
        "reference_identity": None, "sample_key": "controlled-sample",
        "provenance": {"kind": "selected_json", "document_key": "metadata", "pointer": "/members/0"}}
    contents = {"datasets": [{**context_module.extract_vdb_dataset_claim(source_input),
        "sample_links": [{k: v for k, v in sample.items() if k != "source"}]}],
        "members": [context_module.extract_vdb_member_claim(member)]}
    meta = identity(root / "metadata.json", json.dumps(contents, sort_keys=True).encode())
    provenance = {"source_ref": "controlled_parent_declaration", "pointer": ""}
    db_identity = {"namespace": "controlled", "value": "prepared-set", "version": None,
        "release": None, "scope": None, "preparation_type": "unknown", "source": provenance}
    manifest = {"version": "native_blast_prepared_database_manifest_v1", "database_key": operation["database_key"],
        "kind": "vdb", "identity": db_identity, "native_paths": [data["path"]],
        "files": [{k: v for k, v in data.items() if k != "artifact_ref"}],
        "preparation": {"method": "other_recorded", "preparation_type": "vdb",
            "software": {"name": "controlled", "version": None, "executable_sha256": None}, "argv": None,
            "source": provenance, "input_manifest": None, "receipt": receipt},
        "metadata_manifests": [meta] if metadata else [],
        "access": {"mode": "prepared_local", "offline_configuration": offline}, "inventory_complete": True}
    manifest_file = identity(root / "manifest.json", _encoded(manifest))
    context_request = {"version": context_module.REQUEST_VERSION,
        "documents": [{"document_key": "metadata", "selection": {"kind": "database_metadata_manifest",
            "database_key": operation["database_key"], "manifest_index": 0}}] if metadata else [],
        "source_inputs": [source_input],
        "entry_identifier_bindings": [{"selector_ordinal": 0,
            "identifier": {"namespace": "blast_vdb_cmd.entry", "value": "controlled_read", "version": None},
            "source": {"kind": "request"}}] if variant in {"entry", "entry_batch"} else [],
        "member_bindings": [member] if metadata else [], "sample_links": [{"dataset_key": "controlled-dataset", "link": sample}] if metadata else [],
        "dependency_databases": [], "database_lists": [], "declared_dependencies": []}
    if database_source == "dbs_file":
        context_request["declared_dependencies"] = [{"role": "database", "ordinal": 0, "database_key": operation["database_key"],
            "native_path_index": 0, "native_reference": data["path"], "source": "vdblist_file",
            "list_ref": {"kind": "input", "input_key": "selected-dbs"}, "list_entry_ordinal": 0, "declaration": {"kind": "request"}}]
    return {"version": contracts.JOB_VERSION_V3, "operation": operation,
        "software": {"executable": helper["path"], "sha256": helper["sha256"], "engine_version": "controlled-only"},
        "environment": {"NCBI_VDB_CONFIG": offline["path"], "BLAST_USAGE_REPORT": "false",
            "NCBI_USAGE_REPORT_ENABLED": "false", "DO_NOT_TRACK": "1", "LC_ALL": "C"},
        "inputs": inputs, "databases": [{"database_key": operation["database_key"], "role": "target", "kind": "vdb",
            "identity": db_identity, "native_paths": manifest["native_paths"], "manifest_file": manifest_file, "manifest": manifest}],
        "outputs": [{"role": role, "path_kind": "file", "relative_path": "logs/" + role + ".txt", "format": fmt if role == "stdout" else "text"}
            for role in ("stdout", "stderr")], "vdb_context_request": context_request,
        "offline_execution": {"version": execution.VERSION, "launcher": {k: v for k, v in launcher.items() if k != "artifact_ref"},
            "runtime_files": [{k: v for k, v in helper.items() if k != "artifact_ref"}], "runtime_aliases": [],
            "system_interface_profile": "blast_vdb_bwrap_local_v1"}}


def _controlled_offline_receipt(job, plan, argv, returncode):
    rows = execution._runtime_files(job)
    receipt = {"version": execution.RECEIPT_VERSION,
        "launcher_argv": execution.compile_vdb_offline_argv(job, attempt_directory=plan["attempt_directory"], native_argv=argv, status_fd=13),
        "status_fd": 13, "status_records": [{"child-pid": 501}, {"exit-code": returncode}] if returncode is not None else [],
        "launcher_returncode": returncode, "child_pid": 501 if returncode is not None else None, "child_exit_code": returncode,
        "runtime_files": [{"path": r["path"], **{p + k: r[k] for p in ("expected_", "before_", "final_")
            for k in ("sha256", "size_bytes")}} for r in rows],
        "failures": [] if returncode is not None else [contracts.producer_failure("offline_status_unavailable")]}
    return receipt


def controlled_capture(tmp_path, *, job=None, stdout=b"controlled_read\taccession\t4\tACGT\n", stderr=b"", returncode=0, omit=()):
    """New actual Store custody over explicitly controlled selected history."""
    job = controlled_job(tmp_path) if job is None else deepcopy(job)
    plan = plan_fixture(tmp_path, job)
    root = Path(plan["attempt_directory"])
    argv = contracts.compile_native_blast_utility_job(job, **contracts.realized_path_maps(job, str(root)), output_directory=str(root))
    offline = _controlled_offline_receipt(job, plan, argv, returncode)
    failures = deepcopy(offline["failures"])
    if returncode not in (None, 0):
        failures.append(contracts.producer_failure("nonzero_returncode"))
    bundle = {"version": contracts.BUNDLE_VERSION, "identity": plan["identity"], "requested_job": plan["requested_job"],
        "operation": job["operation"], "software": {"executable": job["software"]["executable"],
            "expected_sha256": job["software"]["sha256"], "actual_sha256": job["software"]["sha256"],
            "declared_engine_version": job["software"]["engine_version"]}, "realized_argv": argv,
        "environment": contracts.native_environment(job, root), "started": returncode is not None, "returncode": returncode,
        "writer_closed": True, "inventory_complete": True, "output_completeness_basis": "captured_bytes",
        "started_at": "2026-10-28T00:00:00+00:00", "finished_at": "2026-10-28T00:00:01+00:00",
        "inputs": [], "database_files": [], "artifacts": [], "failures": failures, "offline_execution": offline}
    raw = {}
    for r in job["inputs"]:
        bundle["inputs"].append({"input_key": r["input_key"], "role": r["role"], "format": r["format"],
            "original_path": r["path"], "relative_path": contracts.staged_relative(r), "artifact_ref": r["artifact_ref"],
            **{p + k: r[k] for p in ("expected_", "staged_", "final_") for k in ("sha256", "size_bytes")}})
        raw[r["path"]] = Path(r["path"]).read_bytes()
    for row in contracts.database_file_selections(job):
        bundle["database_files"].append({**row, **{p + k: row["expected_" + k] for p in ("before_", "final_") for k in ("sha256", "size_bytes")}})
        raw[row["original_path"]] = Path(row["original_path"]).read_bytes()
    for row in job["outputs"]:
        data = stdout if row["role"] == "stdout" else stderr
        bundle["artifacts"].append({"role": row["role"], "ordinal": 0, "relative_path": row["relative_path"], "format": row["format"],
            "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "completeness": "complete"})
        raw[str(root / row["relative_path"])] = data
    contracts.validate_native_blast_utility_bundle(bundle, plan)
    store = Store(tmp_path / "store")
    capture = {"version": acquisition.VERSION, "source_ref": None, "plan": plan, "original_bundle": bundle,
        "bundle_artifact_ref": store.artifact(_encoded(bundle), "application/json"), "bundle_validated": True, "artifacts": [], "failures": []}
    for row in acquisition._selected_files(plan, bundle):
        if (row["direction"], row["role"], row["ordinal"]) in omit:
            capture["failures"].append(acquisition._failure("original_file_unavailable", row))
            continue
        reference = store.artifact(raw[row["original_path"]], "application/octet-stream")
        capture["artifacts"].append({k: row[k] for k in acquisition._ROW_FIELDS - {"artifact_ref"}} | {"artifact_ref": reference})
    capture["source_ref"] = store.put("source", acquisition._source_payload(capture), origin="tool")["id"]
    acquisition._validate_saved(store, capture)
    return store, capture


def original_worker_plan(store, capture, directory):
    directory.mkdir(parents=True)
    def file(reference):
        row = store.get(reference)
        return {"path": str(store.path / "artifacts" / row["sha256"][:2] / row["sha256"]),
                "sha256": row["sha256"], "size_bytes": row["size"]}
    context = worker.qualified_utility_context(capture)
    return {"version": worker.PLAN_VERSION_V2, "task": "parse_original", "directory": str(directory),
        "capture": capture, "context": context, "bundle_file": file(capture["bundle_artifact_ref"]),
        "files": [{"occurrence_id": row["occurrence_id"], **file(row["artifact_ref"])} for row in context["occurrences"]]}


@pytest.mark.parametrize("variant", ["entry", "entry_batch", "all_native_sequences", "all_references", "info", "paths", "paths_all"])
@pytest.mark.parametrize("database_source", ["db", "dbs_file"])
def test_exact_fourteen_selected_commands(tmp_path, variant, database_source):
    job = controlled_job(tmp_path, variant, database_source)
    request = contracts.requested_job_from_native_blast_utility(job)
    args = request["argv"]
    assert args[1] == ("-db" if database_source == "db" else "-dbs_file")
    assert args[2] == (job["databases"][0]["native_paths"][0] if database_source == "db" else job["inputs"][0]["path"])
    assert not set(args) & {"-dbtype", "-out", "-logfile", "-strand", "-range", "-exact_length"}
    assert ("-ref" in args) == (variant == "all_references")
    if variant in {"info", "paths", "paths_all"}:
        assert args[3:] == ["-" + variant] + (["-line_length", "80"] if variant == "info" else [])
    else:
        assert args[-4:] == ["-outfmt", "%i\t%a\t%l\t%s", "-line_length", "80"]
    assert Draft202012Validator(contracts.native_blast_utility_job_schema(program="blast_vdb_cmd", mode=job["operation"]["mode"])).is_valid(job)
    with pytest.raises(ValueError, match="vdb_original_database_paths_required"):
        contracts.compile_native_blast_utility_job(job, input_paths={r["input_key"]: r["path"] for r in job["inputs"]},
            database_paths={job["operation"]["database_key"]: ["/different/path"]}, output_directory=".")


def test_original_context_authenticates_all_nested_slots_and_partial_rows(tmp_path):
    job = controlled_job(tmp_path, "entry_batch", "dbs_file")
    store, capture = controlled_capture(tmp_path, job=job,
        stdout=b"controlled_read\taccession\t4\tACGT\nmalformed\ncontrolled_read\taccession\t4\tacgt\n", returncode=2)
    plan = original_worker_plan(store, capture, tmp_path / "worker")
    manifest = worker.run(plan)
    assert manifest["completed"] and manifest["context_authentication"]["passed"]
    proof = manifest["context_authentication"]
    assert len(proof["documents"]) == 1 and len(proof["provenance"]) == 5 and len(proof["lists"]) == 2
    assert proof["provenance"][0]["source_namespace"] == "artifact"
    assert proof["provenance"][1]["source_ref"] == capture["source_ref"]
    assert proof["provenance"][-1]["pointer"] == "/datasets/0/sample_links/0"
    result = json.loads((Path(plan["directory"]) / "result.json").read_text())
    assert [r["native_row_ordinal"] for r in result["records"]] == [0, 2]
    assert [r["returned_symbol_count"] for r in result["records"]] == [4, 4]
    assert result["original_outcome"]["state"] == "failed" and result["output_occurrence"]["completeness"] == "complete"
    assert result["database_binding"]["source_ref"] == capture["source_ref"]
    assert worker.run(plan) == manifest


@pytest.mark.parametrize("slot", ["dataset", "member", "read", "sample"])
def test_claimed_metadata_is_not_authenticated_by_structure(tmp_path, slot):
    job = controlled_job(tmp_path)
    request = job["vdb_context_request"]
    if slot == "dataset":
        request["source_inputs"][0]["snapshot"]["release"] = "false-claim"
    elif slot == "member":
        request["member_bindings"][0]["member_identifier"]["value"] = "false-claim"
    elif slot == "read":
        request["member_bindings"][0]["read_identity"]["spot_id"] = "false-claim"
    else:
        request["sample_links"][0]["link"]["sample_identifier"]["value"] = "false-claim"
    store, capture = controlled_capture(tmp_path, job=job)
    plan = original_worker_plan(store, capture, tmp_path / "worker")
    manifest = worker.run(plan)
    assert not manifest["completed"] and manifest["context_authentication"] is None and manifest["outputs"] == {}
    assert "supplied_binding_conflict" in {r["code"] for r in manifest["failures"]}


def test_same_path_namespace_and_original_runtime_controls(tmp_path):
    job = controlled_job(tmp_path)
    plan = plan_fixture(tmp_path, job)
    root = plan["attempt_directory"]
    native = contracts.compile_native_blast_utility_job(job, **contracts.realized_path_maps(job, root), output_directory=root)
    args = execution.compile_vdb_offline_argv(job, attempt_directory=root, native_argv=native, status_fd=19)
    assert all(flag in args for flag in ("--unshare-user", "--unshare-pid", "--unshare-net", "--clearenv", "--remount-ro"))
    assert args[-len(native) - 3:] == ["--remount-ro", "/", "--", *native]
    for i, token in enumerate(args):
        if token == "--ro-bind":
            assert args[i + 1] == args[i + 2]
        if token == "--bind":
            assert args[i + 1] == args[i + 2] and Path(args[i + 1]).parent == Path(root)
    assert "HOME" not in args and "--share-net" not in args
    assert contracts.native_environment(job, root)["PWD"] == root


@pytest.mark.parametrize("status,rc,diagnostic,started", [
    ([], 1, b"bwrap: Creating new namespace failed\n", False),
    ([{"child-pid": 91}, {"exit-code": 127}], 127, b"bwrap: execvp /selected/helper: No such file\n", False),
    ([{"child-pid": 91}], 0, b"", False),
    ([{"child-pid": 91}, {"exit-code": 2}], 2, b"native diagnostic\n", True),
])
def test_wrapper_attempt_is_not_automatically_successful_exec(tmp_path, monkeypatch, status, rc, diagnostic, started):
    job = controlled_job(tmp_path)
    plan = plan_fixture(tmp_path, job)
    calls = []
    def selected(argv, **kwargs):
        calls.append(argv)
        fd, = kwargs["pass_fds"]
        for row in status:
            os.write(fd, (json.dumps(row) + "\n").encode())
        kwargs["stdout"].write(b"controlled_read\taccession\t4\tACGT\n")
        kwargs["stderr"].write(diagnostic)
        return SimpleNamespace(returncode=rc)
    monkeypatch.setattr(execution.subprocess, "run", selected)
    bundle = driver.run_native_blast_utility(plan)
    assert len(calls) == 1 and bundle["started"] is started
    assert bundle["returncode"] == (rc if started else None)
    assert all(row["completeness"] == "complete" for row in bundle["artifacts"])
    monkeypatch.setattr(execution.subprocess, "run", lambda *a, **k: pytest.fail("sealed replay reran wrapper"))
    assert driver.run_native_blast_utility(plan) == bundle


def test_recursive_inventory_uses_existing_algorithm_and_rejects_unselected_file(tmp_path):
    job = controlled_job(tmp_path)
    db = job["databases"][0]
    original = Path(db["native_paths"][0])
    directory = original.parent
    db["native_paths"] = [str(directory)]
    db["manifest"]["native_paths"] = [str(directory)]
    assert validate_selected_vdb_file_inventory(db)
    (directory / "undeclared").write_bytes(b"not selected")
    with pytest.raises(ValueError, match="vdb_inventory_not_exact"):
        validate_selected_vdb_file_inventory(db)


def _reseal_manifest(db):
    db["manifest_file"] = identity(Path(db["manifest_file"]["path"]), _encoded(db["manifest"]))


def controlled_dependency_job(tmp_path, declaration="request"):
    """Explicit supporting VDB plus selected list bytes, never discovered data."""
    job = controlled_job(tmp_path, metadata=False)
    supporting = controlled_job(tmp_path / "supporting", metadata=False)["databases"][0]
    supporting["database_key"] = supporting["manifest"]["database_key"] = "supporting-vdb"
    _reseal_manifest(supporting)
    job["vdb_context_request"]["dependency_databases"] = [supporting]
    primary = job["databases"][0]
    native = supporting["native_paths"][0]
    raw = (native + "\t" + native + "\r\n").encode()
    selected = identity(Path(primary["native_paths"][0]).parent / "selected-list.txt", raw)
    primary["manifest"]["files"].append({k: v for k, v in selected.items() if k != "artifact_ref"})
    job["vdb_context_request"]["database_lists"] = [{"list_key": "supporting-list",
        "selection": {"kind": "database_file", "database_key": primary["database_key"], "file_index": 1},
        "grammar": "vdb_whitespace_tokens"}]
    deps = [{"role": "database", "ordinal": i, "database_key": supporting["database_key"],
        "native_path_index": 0, "native_reference": native, "source": "vdblist_file",
        "list_ref": {"kind": "database_list", "list_key": "supporting-list"}, "list_entry_ordinal": i,
        "declaration": {"kind": "request"}} for i in range(2)]
    if declaration == "alias":
        alias = identity(Path(primary["native_paths"][0]).parent / "selected-alias.nal", ("VDBLIST " + native + "\n").encode())
        primary["manifest"]["files"].append({k: v for k, v in alias.items() if k != "artifact_ref"})
        deps.append({"role": "database", "ordinal": 2, "database_key": supporting["database_key"],
            "native_path_index": 0, "native_reference": native, "source": "vdblist", "list_ref": None,
            "list_entry_ordinal": None, "declaration": {"kind": "alias_directive", "database_key": primary["database_key"],
                "file_index": 2, "directive": "VDBLIST", "directive_row_ordinal": 0, "token_ordinal": 0}})
    elif declaration == "metadata":
        data = {"dependencies": [{k: v for k, v in d.items() if k not in {"list_ref", "declaration"}} for d in deps]}
        primary["manifest"]["metadata_manifests"] = [identity(Path(primary["manifest_file"]["path"]).parent / "dependencies.json", _encoded(data))]
        job["vdb_context_request"]["documents"] = [{"document_key": "dependencies", "selection": {
            "kind": "database_metadata_manifest", "database_key": primary["database_key"], "manifest_index": 0}}]
        for i, dep in enumerate(deps):
            dep["declaration"] = {"kind": "selected_json", "document_key": "dependencies", "pointer": f"/dependencies/{i}"}
    job["vdb_context_request"]["declared_dependencies"] = deps
    _reseal_manifest(primary)
    return job


@pytest.mark.parametrize("declaration", ["request", "alias", "metadata"])
def test_supporting_operands_lists_and_declarations_are_exact(tmp_path, declaration):
    job = controlled_dependency_job(tmp_path, declaration)
    store, capture = controlled_capture(tmp_path, job=job)
    plan = original_worker_plan(store, capture, tmp_path / "worker")
    result = worker.run(plan)
    assert result["completed"]
    proof = result["context_authentication"]
    assert len(proof["lists"]) == 1
    entries = proof["lists"][0]["entries"]
    assert len(entries) == 2 and entries[0]["value"] == entries[1]["value"]
    assert entries[0]["line_number"] == entries[1]["line_number"] == 1
    assert [r["token_ordinal"] for r in entries] == [0, 1]
    assert entries[1]["byte_start"] == entries[0]["byte_end"] + 1
    lists = [r for r in plan["context"]["occurrences"] if r["role"] == "database_list"]
    assert len(lists) == 1 and lists[0]["direction"] == "input" and lists[0]["native_format"] == "text"
    assert not plan["context"]["operation_input_occurrences"]
    assert plan["context"]["vdb_context"]["dependency_database_bindings"][0]["source_ref"] == capture["source_ref"]


@pytest.mark.parametrize("change", ["list_position", "dependency_key", "native_index", "alias_token", "metadata_value"])
def test_supporting_declarations_cannot_expand_selected_relationships(tmp_path, change):
    job = controlled_dependency_job(tmp_path, "alias" if change == "alias_token" else "metadata" if change == "metadata_value" else "request")
    deps = job["vdb_context_request"]["declared_dependencies"]
    if change == "dependency_key":
        deps[0]["database_key"] = "unselected-database"
    elif change == "native_index":
        deps[0]["native_path_index"] = 1
    elif change == "list_position":
        deps[0]["list_entry_ordinal"] = 2
    elif change == "alias_token":
        deps[-1]["native_reference"] = "/unselected/native/path"
    else:
        deps[0]["native_reference"] = "/unselected/native/path"
    if change in {"dependency_key", "native_index"}:
        with pytest.raises(ContractError, match="supplied_binding_conflict"):
            contracts.validate_native_blast_utility_job(job)
    else:
        store, capture = controlled_capture(tmp_path, job=job)
        manifest = worker.run(original_worker_plan(store, capture, tmp_path / "worker"))
        assert not manifest["completed"] and manifest["outputs"] == {}
        assert "supplied_binding_conflict" in {r["code"] for r in manifest["failures"]}


@pytest.mark.parametrize("change", ["metadata_index", "undeclared_document", "source_id", "array_pointer", "member_description"])
def test_document_selection_and_fixed_extractors_reject_forgery(tmp_path, change):
    job = controlled_job(tmp_path)
    request = job["vdb_context_request"]
    if change == "metadata_index":
        request["documents"][0]["selection"]["manifest_index"] = 1
    elif change == "undeclared_document":
        request["source_inputs"][0]["source"]["document_key"] = "undeclared"
    elif change == "source_id":
        request["source_inputs"][0]["source"] = {"source_ref": "source_" + "f" * 64, "pointer": "/datasets/0"}
    elif change == "array_pointer":
        request["source_inputs"][0]["source"]["pointer"] = "/datasets/00"
    else:
        db = job["databases"][0]
        selected = db["manifest"]["metadata_manifests"][0]
        data = json.loads(Path(selected["path"]).read_text())
        data["members"][0]["native_description"] = {"id": "conflicting-native-id"}
        db["manifest"]["metadata_manifests"][0] = identity(Path(selected["path"]), _encoded(data))
        _reseal_manifest(db)
    if change in {"metadata_index", "undeclared_document", "source_id"}:
        with pytest.raises(ContractError):
            contracts.validate_native_blast_utility_job(job)
    else:
        store, capture = controlled_capture(tmp_path, job=job)
        manifest = worker.run(original_worker_plan(store, capture, tmp_path / "worker"))
        assert not manifest["completed"] and manifest["outputs"] == {}
        assert "supplied_binding_conflict" in {r["code"] for r in manifest["failures"]}


@pytest.mark.parametrize("role", ["database_metadata", "database_file", "database_manifest"])
def test_original_worker_hashes_actual_retained_inputs(tmp_path, role):
    store, capture = controlled_capture(tmp_path)
    plan = original_worker_plan(store, capture, tmp_path / "worker")
    oid = next(r["occurrence_id"] for r in plan["context"]["occurrences"] if r["role"] == role)
    descriptor = next(r for r in plan["files"] if r["occurrence_id"] == oid)
    path = Path(descriptor["path"])
    path.chmod(0o600)
    path.write_bytes(b"changed retained bytes")
    manifest = worker.run(plan)
    assert not manifest["completed"] and manifest["context_authentication"] is None
    assert "input_identity_mismatch" in {r["code"] for r in manifest["failures"]}


@pytest.mark.parametrize("role", ["manifest", "stdout", "stderr"])
def test_missing_original_capture_is_specific_and_does_not_parse(tmp_path, role):
    store, capture = controlled_capture(tmp_path, omit=(("database" if role == "manifest" else "output", role, 0),))
    plan = original_worker_plan(store, capture, tmp_path / "worker")
    manifest = worker.run(plan)
    assert not manifest["completed"] and manifest["context_authentication"] is None and manifest["outputs"] == {}
    assert ("input_population_unavailable" if role == "manifest" else "output_missing") in {r["code"] for r in manifest["failures"]}


@pytest.mark.parametrize("change", ["namespace", "context_occurrence", "context_outcome", "provenance_omission", "request_digest"])
def test_saved_authentication_cannot_be_spliced(tmp_path, change):
    store, capture = controlled_capture(tmp_path)
    plan = original_worker_plan(store, capture, tmp_path / "worker")
    proof = worker.run(plan)["context_authentication"]
    context = deepcopy(plan["context"])
    if change == "namespace":
        proof["provenance"][0]["source_namespace"] = "source"
    elif change == "context_occurrence":
        next(r for r in context["occurrences"] if r["role"] == "database_file")["sha256"] = "f" * 64
        proof["context_sha256"] = contracts.native_blast_digest(context)
    elif change == "context_outcome":
        context["native_outcome"]["inventory_complete"] = False
        proof["context_sha256"] = contracts.native_blast_digest(context)
    elif change == "provenance_omission":
        proof["provenance"].pop()
    else:
        proof["request_sha256"] = "f" * 64
    with pytest.raises(ContractError, match="supplied_binding_conflict"):
        context_module.validate_vdb_context_authentication(proof, capture=capture, context=context)


@pytest.mark.parametrize("kind", ["runtime_before", "config_before", "input_lexical", "scratch"])
def test_preflight_failures_do_not_invoke_wrapper_or_retry(tmp_path, monkeypatch, kind):
    job = controlled_job(tmp_path, "entry_batch")
    if kind == "runtime_before":
        Path(job["offline_execution"]["launcher"]["path"]).write_bytes(b"changed launcher")
    elif kind == "config_before":
        Path(job["environment"]["NCBI_VDB_CONFIG"]).write_bytes(b"changed config")
    elif kind == "input_lexical":
        item = job["inputs"][0]
        item.update(identity(Path(item["path"]), b"different_selected_line\n"))
    else:
        def exceed(*args, **kwargs):
            raise driver._ScratchLimit(POLICY["scratch_bytes"] + 1, POLICY["scratch_bytes"])
        monkeypatch.setattr(driver, "_scratch", exceed)
    plan = plan_fixture(tmp_path, job)
    monkeypatch.setattr(execution.subprocess, "run", lambda *a, **k: pytest.fail("preflight failure executed wrapper"))
    bundle = driver.run_native_blast_utility(plan)
    assert not bundle["started"] and bundle["returncode"] is None
    assert bundle["offline_execution"]["launcher_argv"] == []
    codes = {r["code"] for r in bundle["failures"]}
    assert {"runtime_before": "offline_launcher_unavailable", "config_before": "database_identity_mismatch",
            "input_lexical": "offline_configuration_conflict", "scratch": "staging_scratch_limit"}[kind] in codes
    assert driver.run_native_blast_utility(plan) == bundle


@pytest.mark.parametrize("kind", ["runtime", "config", "input"])
def test_changes_after_wrapper_preserve_native_outcome_and_captured_bytes(tmp_path, monkeypatch, kind):
    job = controlled_job(tmp_path, "entry_batch")
    plan = plan_fixture(tmp_path, job)
    def selected(argv, **kwargs):
        fd, = kwargs["pass_fds"]
        os.write(fd, b'{"child-pid":91}\n{"exit-code":2}\n')
        kwargs["stdout"].write(b"controlled_read\taccession\t4\tACGT\n")
        path = {"runtime": job["software"]["executable"], "config": job["environment"]["NCBI_VDB_CONFIG"], "input": job["inputs"][0]["path"]}[kind]
        Path(path).write_bytes(b"changed after original selected work")
        return SimpleNamespace(returncode=2)
    monkeypatch.setattr(execution.subprocess, "run", selected)
    bundle = driver.run_native_blast_utility(plan)
    assert bundle["started"] and bundle["returncode"] == 2
    assert all(r["completeness"] == "complete" for r in bundle["artifacts"])
    assert {"runtime": "offline_runtime_identity_mismatch", "config": "database_changed", "input": "original_input_changed"}[kind] in {r["code"] for r in bundle["failures"]}
    monkeypatch.setattr(execution.subprocess, "run", lambda *a, **k: pytest.fail("changed original reran wrapper"))
    assert driver.run_native_blast_utility(plan) == bundle


def test_original_runtime_pin_failure_cannot_claim_helper_exit(tmp_path):
    job = controlled_job(tmp_path)
    plan = plan_fixture(tmp_path, job)
    argv = contracts.compile_native_blast_utility_job(job, **contracts.realized_path_maps(job, plan["attempt_directory"]), output_directory=plan["attempt_directory"])
    receipt = _controlled_offline_receipt(job, plan, argv, 0)
    receipt["runtime_files"][-1]["before_sha256"] = "f" * 64
    receipt["failures"] = [contracts.producer_failure("offline_runtime_identity_mismatch")]
    assert execution.vdb_offline_native_outcome(receipt) == (False, None)
    with pytest.raises(ContractError):
        execution.validate_vdb_offline_receipt(receipt, job=job, attempt_directory=plan["attempt_directory"])


def test_historical_native_schema_union_and_vdb_semantic_exclusion(tmp_path):
    from gene_annotation_episode.blast_utility_contracts import blast_utility_schema_for_version
    expected = {"anyOf": [blast_utility_schema_for_version(v) for v in
                         ("blast_utility_operation_v1", "blast_utility_operation_v2")]}
    for schema in (contracts.NATIVE_BLAST_UTILITY_JOB_V1_SCHEMA, contracts.NATIVE_BLAST_UTILITY_JOB_V2_SCHEMA):
        assert schema["properties"]["operation"] == expected
    job = controlled_job(tmp_path)
    for version in (contracts.JOB_VERSION, contracts.JOB_VERSION_V2):
        old = deepcopy(job)
        old["version"] = version
        del old["vdb_context_request"], old["offline_execution"]
        with pytest.raises(ContractError):
            contracts.validate_native_blast_utility_job(old)


@pytest.mark.parametrize("special", ["symlink", "fifo"])
def test_selected_vdb_inventory_rejects_special_entries(tmp_path, special):
    job = controlled_job(tmp_path)
    db = job["databases"][0]
    directory = Path(db["native_paths"][0]).parent
    db["native_paths"] = db["manifest"]["native_paths"] = [str(directory)]
    if special == "symlink":
        (directory / "selected-link").symlink_to(directory / "tiny.sra")
    else:
        os.mkfifo(directory / "selected-fifo")
    with pytest.raises(ValueError, match="vdb_inventory_not_exact"):
        validate_selected_vdb_file_inventory(db)


@pytest.mark.parametrize("variant,database_source", [("entry", "db"), ("entry_batch", "dbs_file")])
def test_duplicate_native_selections_preserve_order_and_actual_list_positions(tmp_path, variant, database_source):
    job = controlled_job(tmp_path, variant, database_source)
    parameters = job["operation"]["parameters"]
    original = parameters["database_selection"]["inputs"][0]
    parameters["database_selection"]["inputs"].append({**original, "ordinal": 1,
        "list_entry_ordinal": 1 if database_source == "dbs_file" else None})
    parameters["selection"]["selectors"].append({"ordinal": 1, "value": "controlled_read"})
    parameters["include_filtered_reads"] = True
    request = job["vdb_context_request"]
    request["source_inputs"].append({**deepcopy(request["source_inputs"][0]), "ordinal": 1})
    request["entry_identifier_bindings"].append({**deepcopy(request["entry_identifier_bindings"][0]), "selector_ordinal": 1})
    for item in job["inputs"]:
        raw = ((original["value"] + "\t" + original["value"] + "\r\n").encode()
               if item["role"] == "database_list" else b"controlled_read\r\n\ncontrolled_read\n")
        item.update(identity(Path(item["path"]), raw))
    args = contracts.requested_job_from_native_blast_utility(job)["argv"]
    assert args[-1] == "-include_filtered_reads"
    if variant == "entry":
        assert args[args.index("-entry") + 1] == "controlled_read,controlled_read"
        assert args[args.index("-db") + 1] == original["value"] + " " + original["value"]
    store, capture = controlled_capture(tmp_path, job=job)
    plan = original_worker_plan(store, capture, tmp_path / "worker")
    manifest = worker.run(plan)
    assert manifest["completed"]
    result = json.loads((Path(plan["directory"]) / "result.json").read_text())
    assert result["records"][0]["matched_selector_ordinals"] == [0, 1]
    assert len(result["vdb_context"]["source_inputs"]) == 2
    if variant == "entry_batch":
        rows = {r["grammar"]: r["entries"] for r in manifest["context_authentication"]["lists"]}
        assert [r["line_number"] for r in rows["vdb_entry_lines"]] == [1, 3]
        assert [r["token_ordinal"] for r in rows["vdb_whitespace_tokens"]] == [0, 1]


@pytest.mark.parametrize("forged", [False, True])
def test_reference_identity_has_its_own_authenticated_source(tmp_path, forged):
    job = controlled_job(tmp_path, "all_references")
    member = job["vdb_context_request"]["member_bindings"][0]
    member.update(member_kind="reference", read_identity=None, reference_identity={
        "identifier": _identity("reference-one"), "full_length": 4, "sequence_sha256": None,
        "source": {"kind": "selected_json", "document_key": "metadata", "pointer": "/members/0/reference_identity"}})
    db = job["databases"][0]
    metadata = db["manifest"]["metadata_manifests"][0]
    data = json.loads(Path(metadata["path"]).read_text())
    data["members"][0] = context_module.extract_vdb_member_claim(member)
    db["manifest"]["metadata_manifests"][0] = identity(Path(metadata["path"]), _encoded(data))
    _reseal_manifest(db)
    if forged:
        member["reference_identity"]["full_length"] = 8
    store, capture = controlled_capture(tmp_path, job=job)
    plan = original_worker_plan(store, capture, tmp_path / "worker")
    manifest = worker.run(plan)
    assert manifest["completed"] is not forged
    if forged:
        assert "supplied_binding_conflict" in {r["code"] for r in manifest["failures"]}
    else:
        proof = manifest["context_authentication"]
        assert any(r["context_pointer"].endswith("/reference_identity/source") and
                   r["pointer"] == "/members/0/reference_identity" for r in proof["provenance"])


def test_conflicting_sample_links_are_rejected_before_native_work(tmp_path):
    job = controlled_job(tmp_path)
    links = job["vdb_context_request"]["sample_links"]
    conflict = deepcopy(links[0])
    conflict["link"]["sample_identifier"]["value"] = "another-sample"
    links.append(conflict)
    with pytest.raises(ContractError, match="supplied_binding_conflict"):
        contracts.validate_native_blast_utility_job(job)


@pytest.mark.parametrize("untyped", [True, 1.0])
def test_metadata_boolean_or_float_does_not_authenticate_integer_identity(tmp_path, untyped):
    job = controlled_job(tmp_path)
    member = job["vdb_context_request"]["member_bindings"][0]
    member["read_identity"]["read_index"] = 1
    db = job["databases"][0]
    selected = db["manifest"]["metadata_manifests"][0]
    data = json.loads(Path(selected["path"]).read_text())
    data["members"][0]["read_identity"]["read_index"] = untyped
    db["manifest"]["metadata_manifests"][0] = identity(Path(selected["path"]), _encoded(data))
    _reseal_manifest(db)
    store, capture = controlled_capture(tmp_path, job=job)
    manifest = worker.run(original_worker_plan(store, capture, tmp_path / "worker"))
    assert not manifest["completed"] and manifest["context_authentication"] is None
    assert "supplied_binding_conflict" in {r["code"] for r in manifest["failures"]}


def test_reserved_producer_capture_and_original_worker_use_actual_store_custody(tmp_path, monkeypatch):
    import shutil
    from test_native_blast_utility_producer_628 import reserved_fixture
    from gene_annotation_episode import native_blast_utility_local as local
    from gene_annotation_episode.local_jobs import LocalJobPolicy
    job = controlled_job(tmp_path, "entry_batch", "dbs_file")
    state, handle, plan, target = reserved_fixture(tmp_path, monkeypatch, job=job)
    assert handle.read()["stage"] == "prepared"
    assert local.prepare_local_blast_utility(state, plan["identity"]["operation_key"], root=handle.path.parent,
        policy=LocalJobPolicy(**POLICY)).path == handle.path
    calls = []
    def controlled_wrapper(argv, **kwargs):
        calls.append(argv)
        fd, = kwargs["pass_fds"]
        os.write(fd, b'{"child-pid":91}\n{"exit-code":2}\n')
        kwargs["stdout"].write(b"controlled_read\taccession\t4\tACGT\nmalformed\n")
        kwargs["stderr"].write(b"controlled native diagnostic\n")
        return SimpleNamespace(returncode=2)
    monkeypatch.setattr(execution.subprocess, "run", controlled_wrapper)
    bundle = driver.run_native_blast_utility(plan)
    store = Store(tmp_path / "store")
    capture = acquisition.capture_local_utility_bundle(store, target=target, directory=tmp_path / "capture")
    assert len(calls) == 1 and capture["original_bundle"] == bundle and capture["bundle_validated"]
    assert capture["source_ref"].startswith("source_") and not capture["failures"]
    assert any(r["direction"] == "database" and r["role"] == "database_file" and r["format"] == "unknown"
               for r in capture["artifacts"])
    original = original_worker_plan(store, capture, tmp_path / "worker")
    shutil.rmtree(handle.path.parent)
    shutil.rmtree(tmp_path / "controlled-selection")
    monkeypatch.setattr(execution.subprocess, "run", lambda *a, **k: pytest.fail("retained processing reran wrapper"))
    monkeypatch.setattr(acquisition, "local_blast_utility_plan", lambda *a, **k: pytest.fail("replay read original paths"))
    monkeypatch.setattr(acquisition, "_capture_file", lambda *a, **k: pytest.fail("replay reacquired files"))
    assert acquisition.capture_local_utility_bundle(store, target=target, directory=tmp_path / "capture") == capture
    manifest = worker.run(original)
    assert manifest["completed"] and manifest["context_authentication"]["passed"]
    result = json.loads((Path(original["directory"]) / "result.json").read_text())
    assert len(result["records"]) == 1 and result["records"][0]["returned_symbol_count"] == 4
    assert result["original_outcome"]["returncode"] == 2 and result["output_occurrence"]["completeness"] == "complete"
