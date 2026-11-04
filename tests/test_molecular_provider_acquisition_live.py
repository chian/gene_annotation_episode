"""Opt-in HTTP acquisitions and explicitly retained historical verification.

The original four-resource cases below preserve their historical child path. No
retry, alternate endpoint, identifier substitution or native calculation is
performed. Failed/unavailable attempts preserve their active prefix and proof,
then skip as unverified; they do not manufacture a child return. Root replay of
a successful/partial delivery uses its cached child result, not a new child run.
The PubChem case uses one ordinary tool action in the current episode.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import os

import pytest

from gene_annotation_episode.acquisition import AcquisitionError, PublicClients
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.molecular_provider_acquisition import (
    MAX_RESPONSE_BYTES, OPERATIONS, VERSION, validate_provider_result,
)
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_molecular_provider_acquisition_host import (
    ARGUMENTS, _artifacts, _controller, _tables, forbidden,
)
from test_runtime import ScriptedProvider
from test_scientific_process_runtime import Scenario, action


class OriginalLivePrefixObserved(RuntimeError):
    """The test has observed its sole failed attempt; this is no product stop."""


class RecordingLiveClients(PublicClients):
    """Record calls and actual snapshots without replacing the HTTP transport."""
    def __init__(self, directory):
        super().__init__(ncbi_email=None, timeout=30, access_dir=directory,
            string_caller_identity="gene-annotation-episode-provider-verification")
        self.calls, self.captures, self.transport_failures = [], [], []

    def _http(self, service, url, params, media_type, **kwargs):
        self.calls.append({"service": service, "url": url, "params": deepcopy(params),
            "media_type": media_type, **deepcopy(kwargs)})
        try:
            snapshot = super()._http(service, url, params, media_type, **kwargs)
        except AcquisitionError as error:
            self.transport_failures.append({"code": error.code, "phase": error.phase,
                "response_retained": error.snapshot is not None})
            if error.snapshot is not None:
                self.captures.append(error.snapshot)
            raise
        self.captures.append(snapshot)
        return snapshot


def _counts(store):
    return {name: store.db.execute("SELECT count(*) FROM " + name).fetchone()[0] for name in (
        "runtime_episodes", "runtime_actions", "runtime_observations", "runtime_model_calls",
        "tool_operations", "runtime_forms", "runtime_report_attempts")}


def _proof(store, client, actor, operation, arguments, *, ended_by_fixture=False, unexpected=None):
    rows = list(store.db.execute("SELECT * FROM tool_operations"))
    outcomes = [json.loads(row["result"]) for row in rows]
    sources = [row for row in store.list("source") if row["provider"] == operation.split(".")[1]]
    files = []
    for source in sources:
        raw = store.get_artifact(source["artifact_ref"])
        files.append({"source": source, "raw_file": {"artifact_ref": source["artifact_ref"],
            "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)},
            "provenance": json.loads(store.get_artifact(source["request_ref"]))})
    summaries = []
    for outcome in outcomes:
        value = outcome.get("result")
        summaries.append({key: outcome.get(key) for key in
            ("status", "operation_ref", "record_refs", "feedback")} | {
            "selected_result": ({key: value.get(key) for key in (
                "version", "operation", "service", "source_ref", "raw_artifact_ref", "requested",
                "response", "parse_state", "decode_error", "representation_state", "population_coverage", "issues")}
                if isinstance(value, dict) else value)})
    return {"scope": "Original bounded HTTP; scripted model/controller; no biological inference or native calculation.",
        "operation": operation, "selected_arguments": arguments, "client_calls": client.calls,
        "actual_transport_failures": client.transport_failures,
        "scripted_decision_calls": len(actor.contexts), "external_model_calls": 0,
        "counts": _counts(store), "outcomes": summaries, "retained_sources": files,
        "expected_fixture_prefix_stop": ended_by_fixture,
        "unexpected_exception": None if unexpected is None else {
            "type": type(unexpected).__name__, "message": str(unexpected)},
        "parent_return_reached": False, "closed_root_replay_reached": False}


@pytest.mark.skipif(os.environ.get("HMMER_NATIVE_ORACLE_MOLECULAR_PROVIDERS_LIVE") != "1"
    or "HMMER529_ATTEMPT" not in os.environ, reason="explicit bounded original-HTTP verification only")
@pytest.mark.parametrize("operation", tuple(name for name in OPERATIONS if name != "public.pubchem.compound"))
def test_original_live_molecular_provider_source_return_and_closed_root_replay(tmp_path, monkeypatch, operation):
    client = RecordingLiveClients(tmp_path / "provider-access")
    monkeypatch.setattr(client, "_skill", forbidden)
    monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", forbidden)
    with Store(tmp_path / "store") as store:
        tools = ToolRegistry(store, clients=client)
        case = Scenario(tmp_path, store, tools=tools)
        return_schema = {"type": "object", "properties": {"metadata_sources": {
            "type": "array", "items": {"type": "string", "format": "reference"},
            "x-source": "committed_record_refs"}}, "required": ["metadata_sources"], "additionalProperties": False}
        commission = case.commission()
        commission["selection"].update(goal="Retain the selected original molecular-provider response.",
            purpose="Return the acquired metadata Source with the original response qualifications.",
            schema_json=json.dumps(return_schema), initial_report_json="{}")
        selected = case.selection(tools=[operation])
        selected["child_tool_info"][0]["resources"] = "api"
        commission["selection"]["assignment"]["selection"] = selected
        arguments = {**deepcopy(ARGUMENTS[operation]), "max_bytes": MAX_RESPONSE_BYTES}
        actor = ScriptedProvider([commission, action(operation, arguments),
            OriginalLivePrefixObserved("sole selected acquisition outcome retained; no further action selected")])

        def workflow(provider):
            return Workflow(store, tools, provider, case.directory, "original-molecular-provider-live", _controller,
                lambda *args, **kwargs: 0, project_child_credit=lambda *args, **kwargs: 0,
                episode_binding_descriptors=case.descriptors, episode_record_receipts=True,
                initial_known_record_refs=[])

        current = workflow(actor)
        goal = "Retain exactly the caller-selected original molecular-provider metadata response."
        root = current.build("annotation", "root", goal, case.scope)
        record, prefix_stop, unexpected = None, False, None
        try:
            record = asyncio.run(root.run_async(current.context))
        except OriginalLivePrefixObserved:
            prefix_stop = True
        except Exception as error:
            unexpected = error
        report = _proof(store, client, actor, operation, arguments,
            ended_by_fixture=prefix_stop, unexpected=unexpected)
        report_file = tmp_path / "MOLECULAR_PROVIDER_LIVE.json"
        report_file.write_text(json.dumps(report, indent=2, allow_nan=False))
        if unexpected is not None:
            raise unexpected
        operations = list(store.db.execute("SELECT * FROM tool_operations"))
        assert len(operations) == len(client.calls) == 1
        saved = operations[0]
        assert saved["name"] == operation and saved["arguments"] == canonical(arguments)
        outcome = json.loads(saved["result"])
        assert outcome["status"] in {"completed", "partial", "failed", "unavailable"}
        assert len(client.captures) <= 1
        value, source = None, None
        if client.captures:
            capture = client.captures[0]
            value = validate_provider_result(outcome["result"])
            assert value["version"] == VERSION and value["requested"] == arguments
            assert value["operation"] == operation and value["population_coverage"] == "selected_response_only"
            source = store.get(value["source_ref"])
            assert source["origin"] == "external" and source["provider"] == operation.split(".")[1]
            assert source["artifact_ref"] == value["raw_artifact_ref"] == "artifact_" + hashlib.sha256(capture.content).hexdigest()
            assert store.get_artifact(source["artifact_ref"]) == capture.content
            assert source["uri"] == capture.url and source["retrieved_at"] == capture.retrieved_at
            assert source["version"] is None
            assert source["accession"] == arguments.get("reaction_id", arguments.get("stable_id", arguments.get("term_id")))
            assert canonical(json.loads(store.get_artifact(source["request_ref"]))) == canonical({
                "request": arguments, "transport": capture.transport})
            assert value["response"]["retained_bytes"] == len(capture.content)
            assert outcome["record_refs"] == [source["id"]]
        else:
            assert report["retained_sources"] == [] and outcome["result"] is None
        report["actual_response_identity_checked"] = bool(client.captures)
        report_file.write_text(json.dumps(report, indent=2, allow_nan=False))
        if prefix_stop:
            assert record is None and outcome["status"] in {"failed", "unavailable"}
            assert report["counts"]["runtime_forms"] == report["counts"]["runtime_report_attempts"] == 0
            assert all(row[0] == "active" for row in store.db.execute("SELECT state FROM runtime_episodes"))
            assert report["parent_return_reached"] is report["closed_root_replay_reached"] is False
            pytest.skip("original live acquisition " + outcome["status"]
                + "; retained Source/error prefix is preserved, parent return/replay unverified")
        assert record is not None and outcome["status"] in {"completed", "partial"}
        assert len(client.captures) == 1 and value is not None and source is not None
        capture = client.captures[0]
        if value["parse_state"] == "json":
            assert value["native_json"] == json.loads(capture.content)
        elif value["parse_state"] == "kegg_text":
            assert value["native_text"].encode("utf-8") == capture.content
            assert "".join(line["text"] for block in value["native_fields"]
                for line in block["lines"]).encode("utf-8") == capture.content
        else:
            assert value["native_json"] is None and value["decode_error"] is not None
        final = asyncio.run(root.build_result(record)).as_record()
        forms = list(store.db.execute("SELECT form FROM runtime_forms"))
        attempts = list(store.db.execute("SELECT parent_episode_id,form,failure FROM runtime_report_attempts"))
        assert len(forms) == len(attempts) == 1 and attempts[0]["failure"] is None
        assert json.loads(forms[0]["form"]) == {"metadata_sources": [source["id"]]}
        assert attempts[0]["form"] == forms[0]["form"]
        parent_known = set(current.receipts.known(attempts[0]["parent_episode_id"]))
        assert {source["id"], source["artifact_ref"], source["request_ref"]} <= parent_known
        report.update(parent_return_reached=True, parent_form=json.loads(forms[0]["form"]),
            counts=_counts(store), normal_source_forward_refs_received={
                "source_ref": source["id"], "raw_artifact_ref": source["artifact_ref"],
                "request_ref": source["request_ref"]})
        report_file.write_text(json.dumps(report, indent=2, allow_nan=False))
        assert report["counts"] == {"runtime_episodes": 2, "runtime_actions": 2,
            "runtime_observations": 2, "runtime_model_calls": 2, "tool_operations": 1,
            "runtime_forms": 1, "runtime_report_attempts": 1}
        before, files = _tables(store), _artifacts(store.path / "artifacts")
        monkeypatch.setattr(client, "_http", forbidden)
        monkeypatch.setattr(ToolRegistry, "execute_async", forbidden)
        restored_actor = ScriptedProvider([])
        restored = workflow(restored_actor)
        restored_root = restored.build("annotation", "root", goal, case.scope)
        restored_record = asyncio.run(restored_root.run_async(restored.context))
        assert asyncio.run(restored_root.build_result(restored_record)).as_record() == final
        assert restored_actor.contexts == [] and len(client.calls) == 1
        assert _tables(store) == before and _artifacts(store.path / "artifacts") == files
        report.update(closed_root_replay_reached=True,
            closed_replay_scope="cached original child result in root loop; no direct child-loop reconstruction",
            tables_and_artifact_bytes_unchanged=True)
        report_file.write_text(json.dumps(report, indent=2, allow_nan=False))


# Original375 completed its selected requests and delivery before the four test
# assertions failed on tuple/list provenance representation. These hashes name
# evidence inputs, not manufactured acquisition results. No input is implicit.
_RETAINED_LIVE_CASES = {
    "public.string.network": (0, "774ddab272f8dde53ff34751b993a134e6f3922abd4e00e503704463899e734d"),
    "public.kegg.reaction": (1, "5857d10e70e8801b4c663b4fd4caaeddaf572e9a8fe55e66f2caee8f642692e3"),
    "public.reactome.record": (2, "901e6704fd66800aa5b78b44b44ebe7e272f3184972c2726915d0bd9b73c2177"),
    "public.quickgo.term": (3, "1008dd1f172a55d1a688abeb3f753cd248dc4ac1906a698571c45d445058164d"),
}


def _retained_live_inventory(directory):
    result = {}
    for path in sorted(directory.rglob("*")):
        assert not path.is_symlink(), path
        if path.is_file():
            raw = path.read_bytes()
            result[str(path.relative_to(directory))] = {
                "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}
    return result


def _retained_live_rows(connection):
    return {name: sorted((tuple(row) for row in connection.execute(
        'SELECT * FROM "' + name.replace('"', '""') + '"')), key=repr)
        for name, in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")}


def _retained_live_artifact(connection, directory, reference):
    metadata = connection.execute("SELECT * FROM artifacts WHERE id=?", (reference,)).fetchone()
    assert metadata is not None and reference == "artifact_" + metadata["sha256"]
    raw = (directory / "artifacts" / metadata["sha256"][:2] / metadata["sha256"]).read_bytes()
    assert len(raw) == metadata["size"] and hashlib.sha256(raw).hexdigest() == metadata["sha256"]
    return raw


@pytest.mark.skipif(not os.environ.get("HMMER_NATIVE_ORACLE_MOLECULAR_PROVIDERS_RETAINED"),
    reason="explicit original provider verification packet required; no implicit run input")
@pytest.mark.parametrize("operation", tuple(_RETAINED_LIVE_CASES))
def test_retained_live_provider_delivery_and_cached_root_replay(tmp_path, monkeypatch, operation):
    """Verify original375 data, then replay an owned copy without any new work.

    The original four tests remain failed. Their DTOs, qualifications, yielded
    histories, typed forms and receipts are never rewritten. This proves cached
    root replay only, with the original child result; it does not run the child
    loop independently or establish additional biological population coverage.
    """
    from pathlib import Path
    import shutil
    import sqlite3

    ordinal, expected_db_sha = _RETAINED_LIVE_CASES[operation]
    packet = Path(os.environ["HMMER_NATIVE_ORACLE_MOLECULAR_PROVIDERS_RETAINED"]).resolve()
    original = packet / "tmp" / ("test_original_live_molecular_p" + str(ordinal))
    assert original.is_dir() and not original.is_symlink()
    assert not list(original.rglob("*-wal")) and not list(original.rglob("*-shm"))
    original_files = _retained_live_inventory(original)
    assert original_files["store/state.sqlite3"]["sha256"] == expected_db_sha
    report_path = tmp_path / "MOLECULAR_PROVIDER_RETAINED.json"
    report = {"operation": operation, "original_database_sha256": expected_db_sha,
        "original_live_test_status": "failed_provenance_representation_assertion",
        "original_data_verified": False, "cached_root_replay_reached": False,
        "new_acquisitions": 0, "new_native_jobs": 0, "new_model_calls": 0}
    report_path.write_text(json.dumps(report, indent=2, allow_nan=False))
    connection = sqlite3.connect((original / "store/state.sqlite3").as_uri()
        + "?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        original_rows = _retained_live_rows(connection)
        original_proof = json.loads((original / "MOLECULAR_PROVIDER_LIVE.json").read_bytes())
        assert original_proof["operation"] == operation
        assert original_proof["parent_return_reached"] is original_proof["closed_root_replay_reached"] is False
        assert len(original_proof["client_calls"]) == 1 and original_proof["actual_transport_failures"] == []
        rows = list(connection.execute("SELECT * FROM tool_operations"))
        assert len(rows) == 1
        saved = rows[0]
        arguments = {**deepcopy(ARGUMENTS[operation]), "max_bytes": MAX_RESPONSE_BYTES}
        assert canonical(original_proof["selected_arguments"]) == canonical(arguments)
        assert saved["name"] == operation and saved["arguments"] == canonical(arguments)
        outcome = json.loads(saved["result"])
        value = validate_provider_result(outcome["result"])
        assert value["operation"] == operation and canonical(value["requested"]) == canonical(arguments)
        source = json.loads(connection.execute("SELECT data FROM records WHERE id=?",
            (value["source_ref"],)).fetchone()[0])
        assert source["origin"] == "external" and source["provider"] == operation.split(".")[1]
        assert source["version"] is None and source["artifact_ref"] == value["raw_artifact_ref"]
        assert source["accession"] == arguments.get("reaction_id", arguments.get("stable_id", arguments.get("term_id")))
        raw = _retained_live_artifact(connection, original / "store", source["artifact_ref"])
        provenance = json.loads(_retained_live_artifact(connection, original / "store", source["request_ref"]))
        proof_source, = original_proof["retained_sources"]
        assert canonical(source) == canonical(proof_source["source"])
        assert canonical(provenance) == canonical(proof_source["provenance"])
        assert canonical(provenance["request"]) == canonical(arguments)
        assert proof_source["raw_file"] == {"artifact_ref": source["artifact_ref"],
            "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}
        transport, response = provenance["transport"], value["response"]
        original_call, = original_proof["client_calls"]
        assert original_call["service"] == value["service"] and original_call["url"] == source["uri"]
        assert original_call["media_type"] == response["media_type"]
        assert original_call["max_bytes"] == response["response_byte_limit"] == MAX_RESPONSE_BYTES
        assert original_call["timeout_seconds"] == 30 and original_call["follow_redirects"] is False
        assert transport["status"] == response["http_status"] == 200
        assert transport["body_complete"] is response["body_complete"] is True
        assert response["capture_failure"] is None
        assert len(raw) == transport["retained_body_bytes"] == transport["observed_body_bytes"] == response["retained_bytes"]
        assert transport["effective_url"] == response["request_url"]
        assert transport["request"]["method"] == "GET" and transport["request"]["url"] == transport["effective_url"]
        assert transport["request_policy"] == {"automatic_redirects": False, "timeout_seconds": 30}
        assert value["population_coverage"] == "selected_response_only" and value["decode_error"] is None
        assert outcome["record_refs"] == [source["id"]]
        if value["parse_state"] == "json":
            assert canonical(value["native_json"]) == canonical(json.loads(raw))
        else:
            assert value["parse_state"] == "kegg_text" and value["native_text"].encode() == raw
            assert "".join(line["text"] for block in value["native_fields"] for line in block["lines"]).encode() == raw
        if operation == "public.string.network":
            assert outcome["status"] == value["representation_state"] == "partial"
            assert value["issues"] == [
                {"code": "content_type_mismatch", "line_number": None, "pointer": "/response/content_type"},
                {"code": "native_taxon_invalid", "line_number": None, "pointer": "/native_json/0/ncbiTaxonId"}]
            assert value["native_json"][0]["ncbiTaxonId"] == "9606"
        else:
            assert outcome["status"] == "completed" and value["representation_state"] == "complete" and value["issues"] == []
        episodes = list(connection.execute("SELECT * FROM runtime_episodes"))
        assert len(episodes) == 2 and all(row["state"] == "yielded" and row["archive"] is not None
            and json.loads(row["completion"])["actions"] == 1 for row in episodes)
        parent = next(row for row in episodes if len(json.loads(row["path"])) == 1)
        child = next(row for row in episodes if len(json.loads(row["path"])) == 2)
        root_request, child_request = json.loads(parent["request"]), json.loads(child["request"])
        original_call_request, = connection.execute(
            "SELECT request FROM runtime_model_calls WHERE episode_id=?", (parent["episode_id"],))
        original_context = json.loads(original_call_request["request"])["context"]
        action_row, = connection.execute("SELECT * FROM runtime_actions WHERE episode_id=?", (child["episode_id"],))
        selected = json.loads(action_row["action"])
        assert selected == {"kind": "tool", "tool": operation, "arguments": arguments}
        assert saved["operation_key"] == parent["run_id"] + ":" + child["episode_id"] + ":0"
        assert saved["scope"] == canonical(child_request["message"]["scope"])
        actual_outcome = json.loads(action_row["result"])
        assert actual_outcome.pop("pending_work_after_action")["items"] == []
        assert canonical(actual_outcome) == canonical(outcome)
        form, = connection.execute("SELECT * FROM runtime_forms")
        attempt, = connection.execute("SELECT * FROM runtime_report_attempts")
        expected_form = {"metadata_sources": [source["id"]]}
        assert form["episode_id"] == attempt["child_episode_id"] == child["episode_id"]
        assert attempt["parent_episode_id"] == parent["episode_id"] and attempt["decision_index"] == 0
        assert attempt["failure"] is None and json.loads(form["form"]) == json.loads(attempt["form"]) == expected_form
        assert json.loads(form["facts"])["committed_record_refs"] == [source["id"]]
        delivered = list(connection.execute("SELECT * FROM runtime_record_receipts WHERE episode_id=?",
            (parent["episode_id"],)))
        for reference in (source["id"], source["artifact_ref"], source["request_ref"]):
            receipt, = [row for row in delivered if row["record_ref"] == reference]
            assert receipt["receipt_kind"] == "child_form" and receipt["source_index"] == 0
        assert {name: len(original_rows[name]) for name in original_proof["counts"]} == original_proof["counts"] == {
            "runtime_episodes": 2, "runtime_actions": 2, "runtime_observations": 2, "runtime_model_calls": 2,
            "tool_operations": 1, "runtime_forms": 1, "runtime_report_attempts": 1}
        report.update(original_data_verified=True, source_ref=source["id"], raw_file=proof_source["raw_file"],
            response=response, representation_state=value["representation_state"], issues=value["issues"],
            original_typed_parent_form=expected_form, actual_parent_delivery_in_original_database=True,
            original_proof_flags_remain_unreached=True, original_counts=original_proof["counts"])
        report_path.write_text(json.dumps(report, indent=2, allow_nan=False))
    finally:
        connection.close()
        assert _retained_live_inventory(original) == original_files

    owned = tmp_path / "owned-retained-provider"
    shutil.copytree(original, owned)
    for path in [owned, *owned.rglob("*")]:
        path.chmod(0o755 if path.is_dir() else 0o644)
    monkeypatch.setattr(PublicClients, "_http", forbidden)
    monkeypatch.setattr(PublicClients, "_skill", forbidden)
    monkeypatch.setattr(ToolRegistry, "execute_async", forbidden)
    monkeypatch.setattr(ToolRegistry, "_import", forbidden)
    monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", forbidden)
    monkeypatch.setattr("gene_annotation_episode.molecular_provider_acquisition.provider_result", forbidden)
    try:
        with Store(owned / "store") as store:
            assert _tables(store) == original_rows
            before, artifacts = _tables(store), _artifacts(store.path / "artifacts")
            run_files = _retained_live_inventory(owned / "run")
            actor = ScriptedProvider([])
            tools = ToolRegistry(store)
            descriptors = [child_request["message"]["scientific_process"]["mechanics_binding"],
                {"version": "literature_episode_binding_v1", "binding_id": "literature",
                 "implementation_sha256": "107536b40ae6cad7ad3939608e9847a961d2ecda341a19ea45e15c46447bf75c",
                 "configuration": {"outcome_page_size": 8}}]
            workflow = Workflow(store, tools, actor, owned / "run", parent["run_id"], _controller,
                lambda *args, **kwargs: 0, project_child_credit=lambda *args, **kwargs: 0,
                credit_binding=original_context["credit_binding"],
                child_credit_binding=original_context["scientific_child_credit_binding"],
                controller_binding=original_context["controller_binding"],
                episode_binding_descriptors=descriptors, episode_record_receipts=True, initial_known_record_refs=[])
            role, key = json.loads(parent["path"])[0]
            root = workflow.build(role, key, root_request["goal"]["objective"], root_request["message"]["scope"])
            record = asyncio.run(root.run_async(workflow.context))
            assert workflow.archive.store(record).descriptor() == json.loads(parent["archive"])
            final = asyncio.run(root.build_result(record)).as_record()
            assert final == {"credit": 0, "pending_handles": []}
            assert actor.contexts == [] and _counts(store) == original_proof["counts"]
            assert _tables(store) == before and _artifacts(store.path / "artifacts") == artifacts
            assert _retained_live_inventory(owned / "run") == run_files
            report.update(cached_root_replay_reached=True, cached_root_result=final,
                replay_scope="original yielded root uses original cached child result; no direct child-loop run",
                tables_artifacts_and_run_files_unchanged=True)
    except Exception as error:
        report["replay_failure"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        assert _retained_live_inventory(original) == original_files
        report["original_files_unchanged"] = True
        report_path.write_text(json.dumps(report, indent=2, allow_nan=False))


@pytest.mark.skipif(os.environ.get("HMMER_NATIVE_ORACLE_PUBCHEM_COMPOUND_LIVE") != "1",
    reason="requires one explicitly selected bounded PubChem acquisition")
def test_live_pubchem_compound_one_current_episode_acquisition_and_exact_replay(tmp_path, monkeypatch):
    """One real GET; retain its original outcome even when acquisition fails."""
    from fluorescence_flowio_test_support import require_bounded_runtime
    from gene_annotation_episode import molecular_provider_acquisition as provider
    from test_molecular_provider_acquisition_host import _assert_retained_source, _scope

    require_bounded_runtime()
    operation = "public.pubchem.compound"
    arguments = {"cid": 2244, "max_bytes": MAX_RESPONSE_BYTES}
    client = RecordingLiveClients(tmp_path / "provider-access")
    monkeypatch.setattr(client, "_skill", forbidden)
    monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", forbidden)
    report_path = tmp_path / "PUBCHEM_LIVE_ORDINARY_WORKFLOW.json"
    report = {"operation": operation, "selected_arguments": arguments, "passed": False,
        "acquired": False, "new_child_episodes": 0, "native_calculations": 0,
        "qualification": "Actual HTTP acquisition; scripted episode decisions; no compound analysis."}
    try:
        with Store(tmp_path / "store") as store:
            tools = ToolRegistry(store, clients=client)
            scope = _scope(store)
            actor = ScriptedProvider([action(operation, arguments),
                OriginalLivePrefixObserved("sole selected GET failed; retain the unfinished episode prefix")])
            directory = tmp_path / "run"
            def workflow(selected_actor):
                return Workflow(store, tools, selected_actor, directory, "pubchem-live-ordinary",
                    _controller, lambda *_: 0, project_child_credit=lambda *_: 0,
                    root_role="improvement", episode_record_receipts=True, initial_known_record_refs=[])
            current = workflow(actor)
            goal = "Acquire the PubChem compound record for the selected CID 2244 for a later analysis."
            root = current.build("improvement", "root", goal, scope)
            record, prefix_stop = None, False
            try:
                record = asyncio.run(root.run_async(current.context))
            except OriginalLivePrefixObserved:
                prefix_stop = True
            final = None if prefix_stop else asyncio.run(root.build_result(record)).as_record()
            row, = list(store.db.execute("SELECT * FROM tool_operations"))
            assert row["name"] == operation and row["arguments"] == canonical(arguments)
            outcome = json.loads(row["result"])
            receipt = provider.validate_provider_receipt(outcome["result"])
            report.update(acquired=receipt["acquired"], receipt=receipt, outcome=outcome,
                client_calls=client.calls, transport_failures=client.transport_failures,
                counts=_counts(store), final=final, expected_unfinished_prefix=prefix_stop,
                whole_episode_completed=not prefix_stop, external_model_calls=0)
            assert len(client.calls) == 1
            assert client.calls[0] == {"service": "pubchem",
                "url": "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/2244/JSON",
                "params": {}, "media_type": "application/json", "max_bytes": MAX_RESPONSE_BYTES,
                "timeout_seconds": 30, "follow_redirects": False}
            assert _counts(store) == {"runtime_episodes": 1, "runtime_actions": 1,
                "runtime_observations": 0 if prefix_stop else 1,
                "runtime_model_calls": 2 if prefix_stop else 1, "tool_operations": 1,
                "runtime_forms": 0, "runtime_report_attempts": 0}
            assert len(actor.contexts) == (2 if prefix_stop else 1)
            if prefix_stop:
                assert record is None and receipt["acquired"] is False
                assert outcome["status"] in {"failed", "unavailable"}
                assert store.db.execute("SELECT state FROM runtime_episodes").fetchone()[0] == "active"
            if client.captures:
                assert len(client.captures) == 1
                value, source = _assert_retained_source(store, outcome, client, operation, arguments)
                raw = store.get_artifact(source["artifact_ref"])
                report.update(source=source, native_response={"sha256": hashlib.sha256(raw).hexdigest(),
                    "size_bytes": len(raw)}, response=value["response"], issues=value["issues"])
                context = current.binding_context(root.source)
                known = set(current.receipts.known(context.episode_id))
                assert set(outcome["record_refs"]) <= known
                assert {source["request_ref"], *source["auxiliary_artifact_refs"]}.isdisjoint(known)
                if receipt["acquired"]:
                    native = json.loads(raw)
                    assert value["native_json"] == native
                    assert native["PC_Compounds"] and all(type(item["id"]["id"]["cid"]) is int
                        and item["id"]["id"]["cid"] == 2244 for item in native["PC_Compounds"])
                    assert outcome["status"] == "completed"
            else:
                assert receipt == provider.failed_provider_receipt("data_acquisition_failed")
                assert outcome["record_refs"] == []
            before, artifacts, archives = _tables(store), _artifacts(store.path / "artifacts"), _artifacts(directory / "archive")
            for name in ("provider_value", "publish_molecular_provider_request"):
                monkeypatch.setattr(provider, name, forbidden)
            monkeypatch.setattr(client, "_http", forbidden)
            monkeypatch.setattr(Store, "get_artifact", forbidden)
            assert tools.execute(operation, arguments, scope=scope, operation_key=row["operation_key"]) == outcome
            if not prefix_stop:
                monkeypatch.setattr(ToolRegistry, "execute_async", forbidden)
                restored_actor = ScriptedProvider([])
                restored = workflow(restored_actor)
                restored_root = restored.build("improvement", "root", goal, scope)
                restored_record = asyncio.run(restored_root.run_async(restored.context))
                assert asyncio.run(restored_root.build_result(restored_record)).as_record() == final
                assert restored_actor.contexts == [] and len(client.calls) == 1
            assert _tables(store) == before and _artifacts(store.path / "artifacts") == artifacts
            assert _artifacts(directory / "archive") == archives
            report.update(exact_toolop_cache=True, closed_replay_reached=not prefix_stop,
                tables_artifacts_archives_unchanged=True,
                private_controls_not_admitted=True, passed=receipt["acquired"])
    except BaseException as error:
        report["failure"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        report_path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    if not report["acquired"]:
        pytest.skip("Selected real PubChem request did not acquire the compound; original outcome retained without retry")


@pytest.mark.skipif(not os.environ.get("HMMER_NATIVE_ORACLE_RETAINED_PUBCHEM_CASE"),
    reason="requires the explicitly pinned original560 acquisition")
def test_retained_pubchem_live_custody_cache_and_closed_replay(tmp_path, monkeypatch):
    """Read the successful original GET; preserve its failed verification test."""
    from contextlib import closing
    from pathlib import Path
    import shutil
    import sqlite3
    from fluorescence_flowio_test_support import require_bounded_runtime
    from gene_annotation_episode import molecular_provider_acquisition as provider
    from test_molecular_provider_acquisition_host import _credit

    require_bounded_runtime()
    original = Path(os.environ["HMMER_NATIVE_ORACLE_RETAINED_PUBCHEM_CASE"])
    assert original.is_absolute() and original.is_dir() and not original.is_symlink()
    before = _retained_live_inventory(original)
    modes = {str(p.relative_to(original)): p.stat().st_mode for p in original.rglob("*") if p.is_file()}
    assert before["store/state.sqlite3"] == {"sha256":
        "9a800f70549567115466dfc7420ce88d5f24ec10a6ed755a14877971d1c7631d", "size_bytes": 1003520}
    assert before["PUBCHEM_LIVE_ORDINARY_WORKFLOW.json"] == {"sha256":
        "6ffa17f837f8c9c756fa4d10dedf74fa2024e1a0e57d0df106573bcd1057cde0", "size_bytes": 2424}
    assert not list((original / "store").glob("state.sqlite3-*"))
    owned = tmp_path / "owned-original560"
    shutil.copytree(original, owned)
    assert _retained_live_inventory(owned) == before
    database = owned / "store/state.sqlite3"
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        original_rows = _retained_live_rows(db)
        episode, = list(db.execute("SELECT * FROM runtime_episodes"))
        saved_call, = list(db.execute("SELECT request FROM runtime_model_calls"))
        recorded_context = json.loads(saved_call["request"])["context"]
    request = json.loads(episode["request"])
    original_proof = json.loads((owned / "PUBCHEM_LIVE_ORDINARY_WORKFLOW.json").read_bytes())
    assert original_proof["passed"] is False and original_proof["acquired"] is True
    assert original_proof["failure"]["type"] == "AssertionError"
    assert len(original_proof["client_calls"]) == 1 and original_proof["transport_failures"] == []
    report_path = tmp_path / "PUBCHEM_RETAINED_POSTCHECK.json"
    report = {"version": "pubchem_original560_retained_postcheck_v1", "passed": False,
        "original_verification_test": "failed_tuple_list_provenance_comparison_preserved",
        "new_HTTP_requests": 0, "new_scientific_calculations": 0, "new_binding_overrides": 0,
        "original_recorded_bindings": {key: recorded_context[key] for key in
            ("credit_binding", "controller_binding", "scientific_child_credit_binding")},
        "current_read_side_callbacks": {"controller": _controller.__module__ + "." + _controller.__qualname__,
            "credit": _credit.__module__ + "." + _credit.__qualname__}}
    try:
        monkeypatch.setattr(PublicClients, "_http", forbidden)
        monkeypatch.setattr(PublicClients, "_skill", forbidden)
        monkeypatch.setattr("socket.create_connection", forbidden)
        monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", forbidden)
        with Store(owned / "store") as store:
            assert _tables(store) == original_rows
            saved, = list(store.db.execute("SELECT * FROM tool_operations"))
            operation, arguments, scope = saved["name"], json.loads(saved["arguments"]), json.loads(saved["scope"])
            assert operation == "public.pubchem.compound" and arguments == {"cid": 2244, "max_bytes": MAX_RESPONSE_BYTES}
            outcome = json.loads(saved["result"])
            receipt = provider.validate_provider_receipt(outcome["result"])
            assert receipt == original_proof["receipt"] and receipt["acquired"] is True
            source = store.get(receipt["source_ref"])
            raw = store.get_artifact(source["artifact_ref"])
            assert len(raw) == 12595 and hashlib.sha256(raw).hexdigest() == "1f95c222711721a915040d2a131b52357e8186e2998738d5ea7203bc45f059cf"
            assert source["origin"] == "external" and source["provider"] == "pubchem"
            assert source["accession"] == "2244" and source["version"] is None
            assert source["uri"] == original_proof["client_calls"][0]["url"]
            provenance = json.loads(store.get_artifact(source["request_ref"]))
            assert canonical(provenance["request"]) == canonical(arguments)
            transport = provenance["transport"]
            assert transport["status"] == 200 and transport["body_complete"] is True
            assert transport["request"]["method"] == "GET" and transport["request"]["url"] == source["uri"]
            assert transport["request_policy"] == {"automatic_redirects": False, "timeout_seconds": 30}
            assert transport["retained_body_bytes"] == transport["observed_body_bytes"] == len(raw)
            value_ref, = source["auxiliary_artifact_refs"]
            value = provider.validate_provider_value(json.loads(store.get_artifact(value_ref)))
            assert value["native_json"] == json.loads(raw) and value["requested"] == arguments
            assert value["representation_state"] == "complete" and value["issues"] == []
            assert value["native_json"]["PC_Compounds"] and all(type(item["id"]["id"]["cid"]) is int
                and item["id"]["id"]["cid"] == 2244 for item in value["native_json"]["PC_Compounds"])
            assert provider.provider_receipt(value, source_ref=source["id"]) == receipt
            assert outcome["record_refs"] == [source["id"], source["artifact_ref"]]
            deliveries = list(store.db.execute("SELECT * FROM runtime_record_receipts WHERE receipt_kind='own_action'"))
            assert {r["record_ref"] for r in deliveries} == set(outcome["record_refs"])
            assert all(r["source_index"] == 0 and r["episode_id"] == episode["episode_id"] for r in deliveries)
            assert not store.db.execute("SELECT 1 FROM runtime_record_receipts WHERE record_ref IN (?,?)",
                (source["request_ref"], value_ref)).fetchone()
            assert episode["state"] == "yielded" and _counts(store) == original_proof["counts"]
            tables, artifacts, archives = _tables(store), _artifacts(store.path / "artifacts"), _artifacts(owned / "run/archive")
            tools = ToolRegistry(store)
            for name in ("provider_value", "provider_result", "publish_molecular_provider_request"):
                monkeypatch.setattr(provider, name, forbidden)
            monkeypatch.setattr(Store, "get_artifact", forbidden)
            monkeypatch.setattr(Store, "artifact", forbidden)
            monkeypatch.setattr(ToolRegistry, "_source", forbidden)
            assert tools.execute(operation, arguments, scope=scope, operation_key=saved["operation_key"]) == outcome
            assert _tables(store) == tables and _artifacts(store.path / "artifacts") == artifacts
            monkeypatch.setattr(ToolRegistry, "execute_async", forbidden)
            actor = ScriptedProvider([])
            current = Workflow(store, tools, actor, owned / "run", episode["run_id"], _controller, _credit,
                project_child_credit=_credit, root_role="improvement", episode_record_receipts=True,
                initial_known_record_refs=[])
            role, key = json.loads(episode["path"])[0]
            root = current.build(role, key, request["goal"]["objective"], request["message"]["scope"])
            record = asyncio.run(root.run_async(current.context))
            assert current.archive.store(record).descriptor() == json.loads(episode["archive"])
            final = asyncio.run(root.build_result(record)).as_record()
            assert canonical(final) == canonical(original_proof["final"])
            assert actor.contexts == [] and _tables(store) == tables
            assert _artifacts(store.path / "artifacts") == artifacts and _artifacts(owned / "run/archive") == archives
            report.update(passed=True, actual_original_HTTP_status=200, original_native_bytes=len(raw),
                source=source, receipt=receipt, response=value["response"], original_counts=_counts(store),
                exact_toolop_cache=True, exact_current_read_side_closed_replay=True,
                tables_artifacts_archives_unchanged=True, no_new_model_actions_observations_or_receipts=True)
    except BaseException as error:
        report["failure"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        assert _retained_live_inventory(original) == before
        assert {str(p.relative_to(original)): p.stat().st_mode for p in original.rglob("*") if p.is_file()} == modes
        report["original_inventory_unchanged"] = True
        report_path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
