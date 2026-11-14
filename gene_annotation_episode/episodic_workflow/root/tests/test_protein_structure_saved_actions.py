"""Ordinary saved-action authority controls; no original comparison is run.

Retained host cases require the explicitly supplied immutable342 acquisition.
They create actual new ordinary actions over an owned Store copy. Numerical
saved-worker execution is deliberately left to the separate Workflow proof.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sqlite3
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import ContractError, validate_schema
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.molecular_measurement_tools import authenticate_molecular_invocation
from gene_annotation_episode.protein_structure_action_records import (
    ProteinStructureActionRecords, SAVED_SOURCE, VIEW_SOURCE,
    validate_protein_structure_tool_result,
)
from gene_annotation_episode.protein_structure_tools import (
    SAVED_WORK_VERSION, normalize_protein_structure_configuration,
    prepare_protein_structure_work, protein_structure_tool_catalog,
    validate_prepared_protein_structure_work,
)
from gene_annotation_episode.runtime import ActionFailure, Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from gene_annotation_episode.native_protein_structure_contracts import POLICY
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from test_protein_structure_ordinary_configuration import resources, environments


TOOL = "compare_protein_structures"
ORIGINAL_DATABASE_SHA256 = "ef1d21820f9302b8a74ae38af7ef6f10beeee2707c0c54e54eb44b69cbc8a3f1"
LEGACY_BASE = Path("/home/chia/repos/gene_annotation_episode/runs/check336_protein_structure_current_v2_workflow/tmp/test_current_v2_alignment_oper0/current-v2")
LEGACY_DATABASE_SHA256 = "efb35ce65a40b064ba9179b08c604779b9274a9da8cbe5311f2ae7fcd10609b7"
LEGACY_PROOF_SHA256 = "4265809860a1e6bcda1f734bd44efa964551087ec7dfdc92ae63fd9e89d54043"


def forbidden(*args, **kwargs):
    raise AssertionError("original comparison, numerical worker or model work is forbidden")


class NoModel:
    complete = staticmethod(forbidden)
    release = staticmethod(forbidden)


def neutral(*args, **kwargs):
    return 0


def pins(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob("*")) if path.is_file()}


@pytest.fixture
def retained(tmp_path, monkeypatch):
    supplied = os.environ.get("ORDINARY_PROTEIN_RETAINED_STORE")
    if not supplied:
        pytest.skip("requires the explicitly selected original342 retained Store")
    original = Path(supplied).resolve(strict=True)
    before = pins(original)
    assert before["state.sqlite3"] == ORIGINAL_DATABASE_SHA256
    owned = tmp_path / "owned-store"
    shutil.copytree(original, owned)
    with Store(owned) as store:
        original_operation, = list(store.db.execute("SELECT * FROM tool_operations WHERE name=?", (TOOL,)))
        original_outcome = json.loads(original_operation["result"])
        source_ref = original_outcome["result"]["source_ref"]
        descriptor, = original_outcome["result"]["saved_sheets"]
        original_run = original_operation["operation_key"].split(":", 1)[0]
        old_records = EpisodeReturnRecords(store, original_run, failure_prefix="saved_test_")
        episode_rows = list(store.db.execute("SELECT episode_id FROM runtime_episodes WHERE run_id=? "
            "ORDER BY json_array_length(path)", (original_run,)))
        old_parent, old_science = [old_records.context(row["episode_id"]) for row in episode_rows]
        scope = plain(old_science.scope)
        tools = ToolRegistry(store, job_limits=deepcopy(POLICY))
        tools.configure_protein_structure_resources(resources(tmp_path), environments())
        for module, names in (
                ("gene_annotation_episode.native_lifecycle", ("prepare_job", "start_prepared", "resume_start", "wait_job", "status", "collect")),
                ("gene_annotation_episode.protein_structure_tools", ("run_cancellable_native", "_run_selected", "_prepare_result_worker", "resolve_protein_structure_operands")),
                ("gene_annotation_episode.protein_structure_formats", ("parse_pdb_structure", "parse_mmcif_structure")),
                ("gene_annotation_episode.protein_structure_calculations", ("calculate_protein_structure_components", "fit_ca_transform")),
                ("gene_annotation_episode.acquisition.PublicClients", ("_http",))):
            for name in names:
                monkeypatch.setattr(module + "." + name, forbidden)
        flows = []

        def receiver(*, received=True):
            number = len(flows)
            flow = Workflow(store, tools, NoModel(), tmp_path / ("run-" + str(number)), "saved-action-" + str(number),
                forbidden, neutral, episode_binding_factories=(), root_role="improvement",
                episode_record_receipts=True, initial_known_record_refs=[source_ref] if received else [])
            caller = flow.build("improvement", "actual-caller", "Select retained structure data", scope)
            records = ProteinStructureActionRecords(store, flow.run_id)
            value = SimpleNamespace(flow=flow, caller=caller, records=records,
                context=flow.binding_context(caller.source))
            flows.append(value)
            return value

        yield SimpleNamespace(store=store, tools=tools, receiver=receiver, descriptor=deepcopy(descriptor),
            source_ref=source_ref, original_outcome=original_outcome, original_run=original_run,
            old_parent=old_parent, old_science=old_science, original=original)
    assert pins(original) == before


def selected(case, receiver, arguments, index):
    asyncio.run(receiver.caller.source.execute(dict(kind="tool", tool=TOOL, arguments=deepcopy(arguments)), index))
    return deepcopy(receiver.caller.source.last_outcome)


def read(case, receiver, index=0):
    return selected(case, receiver, dict(mode="read_stored", result_ref=case.source_ref), index)


def projection(case, *, result_ref=None):
    original = next(value["selection"] for value in case.original_outcome["result"]["views"]
        if value["selection"]["family"] == "comparison_summary")
    selection = deepcopy(original)
    selection.update(projection_id="retained-summary-only", fields=[original["fields"][0]], delivery_kind="values")
    return dict(mode="select_projection", saved_sheet=deepcopy(case.descriptor),
        result_ref=case.source_ref if result_ref is None else result_ref, projections=[selection])


def recalculate(case):
    source = case.store.get(case.source_ref)
    capsule = json.loads(case.store.get_artifact(source["request_ref"]))
    parameters = deepcopy(capsule["plan"]["requested_job"]["native_protein_structure"]["request"]["parameters"])
    parameters["distance_threshold_A"] = .5
    return dict(mode="recalculate", resource_id="selected-local", binding_ordinal_0based=3,
        saved_sheet=deepcopy(case.descriptor), parameters=parameters, projections=projection(case)["projections"])


def corrupt_summary_values(result):
    summary = next(view["outcome"] for view in result["views"] if view["selection"]["family"] == "comparison_summary")
    fields = {cell["field"]: cell["value"] for row in summary["rows"] for cell in row["values"]}
    fields["evaluation_sse"]["value"] += .125
    fields["evaluation_rmsd"]["value"] = math.sqrt(
        fields["evaluation_sse"]["value"] / fields["evaluation_used_count"]["value"])
    # This remains a well-typed, internally consistent packet. It differs
    # from the authenticated producer's recorded numerical values.
    validate_protein_structure_tool_result(result)


def test_saved_union_keeps_native_inspect_and_extract_contracts(tmp_path):
    from test_protein_structure_ordinary_workflow import _requests
    from gene_annotation_episode.protein_structure_tools import _validate_saved_arguments
    configuration = normalize_protein_structure_configuration(resources(tmp_path), environments(), resources(tmp_path)["selected-local"]["policy"])
    catalog = protein_structure_tool_catalog(configuration)
    with Store(tmp_path / "schema-store") as store:
        requests, _ = _requests(store)
        for name, ordinal, request in zip(("inspect_protein_structure", "extract_protein_structure_sequence", TOOL), (0, 1, 3), requests):
            arguments = dict(resource_id="selected-local", binding_ordinal_0based=ordinal, request=request,
                selection=dict(projections=[], return_saved_sheet=False, sequence_allowed_uses=[]))
            validate_schema(arguments, catalog[name]["input_schema"])
        validate_schema(dict(mode="read_stored", result_ref="source_" + "a" * 64), catalog[TOOL]["input_schema"])
        with pytest.raises((ContractError, ValueError)):
            _validate_saved_arguments(dict(mode="read_stored", result_ref="source_" + "a" * 64 + "\n"))


def test_receipt_reader_skips_writes_but_missing_prefix_migration_stays_unknown(tmp_path):
    with Store(tmp_path / "receipt-storage") as store:
        with store.transaction():
            store.db.execute("CREATE TABLE runtime_receipt_inheritance(run_id TEXT NOT NULL, episode_id TEXT NOT NULL, "
                "parent_episode_id TEXT, through_receipt_index INTEGER, PRIMARY KEY(run_id,episode_id))")
            store.db.execute("CREATE TABLE runtime_record_receipts(receipt_index INTEGER PRIMARY KEY, run_id TEXT NOT NULL, "
                "episode_id TEXT NOT NULL, record_ref TEXT NOT NULL, receipt_kind TEXT NOT NULL, source_index INTEGER, "
                "UNIQUE(run_id,episode_id,record_ref))")
            store.db.execute("INSERT INTO runtime_receipt_inheritance VALUES(?,?,NULL,NULL)", ("historical", "past"))
        receipt = EpisodeReceipts(store, "historical")
        assert store.db.execute("SELECT received_report_prefix FROM runtime_receipt_inheritance").fetchone()[0] is None
        assert "received_report_prefix" not in receipt.manifest("past")
        assert list(receipt.known("past")) == []
        before = store.db.total_changes
        store.db.execute("PRAGMA query_only=ON")
        denied = []
        writes = {sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE,
            sqlite3.SQLITE_CREATE_TABLE, sqlite3.SQLITE_CREATE_INDEX, sqlite3.SQLITE_ALTER_TABLE}

        def authorize(action, *args):
            if action in writes:
                denied.append((action, args))
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK

        store.db.set_authorizer(authorize)
        with store.read_snapshot():
            reader = EpisodeReceipts(store, "historical")
            assert reader.manifest("past") == receipt.manifest("past")
            assert list(reader.known("past")) == []
        assert not denied and store.db.total_changes == before






















