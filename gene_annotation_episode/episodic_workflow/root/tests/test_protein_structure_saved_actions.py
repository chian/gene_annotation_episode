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


def test_literal_read_establishes_only_original_saved_fact_and_no_producer(retained):
    case, receiver = retained, retained.receiver()
    before = set(receiver.flow.receipts.known(receiver.caller.source.episode_id))
    outcome = read(case, receiver)
    assert outcome["result"] == case.original_outcome["result"]
    assert outcome["status"] == case.original_outcome["status"] == "partial"
    assert outcome["feedback"] == case.original_outcome["feedback"]
    assert outcome["record_refs"] == [case.source_ref] and outcome["changed_record_refs"] == []
    assert receiver.records.own_facts(receiver.context, fact_source=SAVED_SOURCE) == [case.descriptor]
    assert receiver.records.own_facts(receiver.context, fact_source=VIEW_SOURCE) == outcome["result"]["views"]
    producer = receiver.records._producer(case.source_ref, verify_artifacts=True)
    assert producer["context"].run_id == case.original_run
    assert set(receiver.flow.receipts.known(receiver.caller.source.episode_id)) == before
    for table in ("runtime_model_calls", "runtime_forms", "runtime_report_attempts", "runtime_observations"):
        assert case.store.db.execute("SELECT count(*) FROM " + table + " WHERE run_id=?", (receiver.flow.run_id,)).fetchone()[0] == 0


def test_saved_payload_role_order_survives_canonical_metadata_roundtrip(retained):
    """Pure payload construction: no Source publication or receiver admission."""
    from gene_annotation_episode.protein_structure_publication import saved_protein_action_source_payload
    case = retained
    source = case.store.get(case.source_ref)
    original = json.loads(case.store.get_artifact(source["request_ref"]))
    files = dict(sheet_file=case.descriptor["sheet_file"],
        original_components_file=case.descriptor["original_components_file"],
        components_file=case.descriptor["original_components_file"])
    capsule = dict(version="protein_structure_saved_action_publication_v1", work=dict(
        invocation=original["invocation"], arguments=dict(saved_sheet=case.descriptor),
        admission=dict(result_ref=case.source_ref), qualified_files=files, worker=None))
    stored = json.loads(canonical(capsule))
    assert list(files) != list(stored["work"]["qualified_files"])
    before = saved_protein_action_source_payload(case.store, capsule=capsule,
        public_ref=source["artifact_ref"], request_ref=source["request_ref"])
    after = saved_protein_action_source_payload(case.store, capsule=stored,
        public_ref=source["artifact_ref"], request_ref=source["request_ref"])
    assert before == after
    assert before["auxiliary_artifact_refs"] == [case.descriptor[name]["artifact_ref"]
        for name in ("sheet_file", "original_components_file")]


def test_unreceived_source_denied_before_private_producer_read(retained, monkeypatch):
    case, receiver = retained, retained.receiver(received=False)
    monkeypatch.setattr(ProteinStructureActionRecords, "_producer", forbidden)
    with pytest.raises(ActionFailure):
        read(case, receiver)
    outcome = receiver.caller.source.last_outcome
    assert outcome["status"] == "invalid" and outcome["record_refs"] == [] and outcome["result"] is None


def test_literal_descriptor_and_later_read_cannot_authorize_earlier_calculation(retained):
    case, receiver = retained, retained.receiver()
    arguments = recalculate(case)
    with pytest.raises(ActionFailure):
        selected(case, receiver, arguments, 0)
    failed = deepcopy(receiver.caller.source.last_outcome)
    assert failed["status"] == "invalid" and failed["record_refs"] == []
    read(case, receiver, 1)
    assert receiver.records.own_facts(receiver.context, fact_source=SAVED_SOURCE) == [case.descriptor]
    with pytest.raises(ValueError):
        receiver.records.saved_action_inputs(receiver.context, case.descriptor, required_use="recalculate", before_decision_index=0)
    key = f"{receiver.flow.run_id}:{receiver.caller.source.episode_id}:0"
    cached = asyncio.run(receiver.flow.execute(receiver.caller.source, TOOL, arguments, decision_index=0, operation_key=key))
    assert cached == {name: value for name, value in failed.items() if name != "pending_work_after_action"}


def test_early_commission_index_is_not_a_late_typed_return_arrival_witness(retained):
    case = retained
    records = ProteinStructureActionRecords(case.store, case.original_run)
    assert records.received_facts(case.old_parent, fact_source=SAVED_SOURCE) == [case.descriptor]
    child, form, schema = next(records.received_attempts(case.old_parent))
    # Original parent commissioned at0, then received the descriptor. Its sole
    # original decision context still contains no received child report. An
    # earlier commission does not prove admission to any previous selection.
    assert child.episode_id == case.old_science.episode_id
    assert not records._form_before(case.old_parent, child, form, schema, 1)
    with pytest.raises(ValueError):
        records.authenticate_received_saved_sheet(case.old_parent, case.descriptor,
            required_use="recalculate", before_decision_index=1)


def test_received_fitted_claim_requires_actual_prior_transform_projection_before_worker(retained):
    case, receiver = retained, retained.receiver()
    read(case, receiver)
    arguments = recalculate(case)
    components = json.loads(case.store.get_artifact(case.descriptor["original_components_file"]["artifact_ref"]))
    transform = arguments["parameters"]["declared_transform"]
    transform["origin"] = "received_fitted"
    transform["received_from"] = dict(saved_sheet=deepcopy(case.descriptor),
        calculation_custody=deepcopy(case.descriptor["custody"]),
        components_file=deepcopy(case.descriptor["original_components_file"]), calculation_id=components["calculation_id"])
    with pytest.raises(ActionFailure):
        selected(case, receiver, arguments, 1)
    outcome = receiver.caller.source.last_outcome
    assert outcome["status"] == "invalid" and outcome["record_refs"] == [] and outcome["result"] is None


def test_changed_projection_and_exact_noop_have_distinct_and_original_producers(retained):
    case, receiver = retained, retained.receiver()
    read(case, receiver)
    arguments = projection(case)
    outcome = selected(case, receiver, arguments, 1)
    assert outcome["status"] == "completed" and outcome["result"]["issues"] == []
    result_ref = outcome["result"]["source_ref"]
    assert result_ref != case.source_ref and outcome["record_refs"] == outcome["changed_record_refs"] == [result_ref]
    assert case.store.get(result_ref)["version"] == "protein_structure_saved_action_v1"
    assert outcome["result"]["saved_sheets"] == []
    authority = receiver.records.read_result_authority(receiver.context,
        dict(version="protein_structure_action_custody_v1", source_ref=result_ref))
    assert authority["sheet_file"] == case.descriptor["sheet_file"]
    assert authority["original_components_file"] == authority["components_file"] == case.descriptor["original_components_file"]
    source = case.store.get(result_ref)
    known = set(receiver.flow.receipts.known(receiver.caller.source.episode_id))
    assert {source["request_ref"], source["artifact_ref"], *source["auxiliary_artifact_refs"]}.isdisjoint(known)
    same = projection(case, result_ref=result_ref)
    before_records = case.store.db.execute("SELECT count(*) FROM records").fetchone()[0]
    no_op = selected(case, receiver, same, 2)
    assert no_op["result"] == outcome["result"] and no_op["changed_record_refs"] == []
    assert case.store.db.execute("SELECT count(*) FROM records").fetchone()[0] == before_records
    facts = receiver.records.own_facts(receiver.context, fact_source=VIEW_SOURCE)
    assert facts == case.original_outcome["result"]["views"] + outcome["result"]["views"]
    assert receiver.records._producer(result_ref, verify_artifacts=True)["decision_index"] == 1
    key = f"{receiver.flow.run_id}:{receiver.caller.source.episode_id}:2"
    assert asyncio.run(receiver.flow.execute(receiver.caller.source, TOOL, same, decision_index=2,
        operation_key=key)) == {name: value for name, value in no_op.items() if name != "pending_work_after_action"}


@pytest.mark.parametrize("alter", ["cell", "selected_source"])
def test_detached_read_packet_cannot_change_original_values_or_selected_source(retained, alter):
    case, receiver = retained, retained.receiver()
    arguments = dict(mode="read_stored", result_ref=case.source_ref)
    read(case, receiver)
    key = f"{receiver.flow.run_id}:{receiver.caller.source.episode_id}:0"
    with case.tools.current_invocation(receiver.context, read_received=receiver.flow.services.read_received_molecular_input,
            tool_name=TOOL, arguments=arguments, operation_key=key), case.tools.protein_structure_invocation(receiver.records):
        authority = authenticate_molecular_invocation(case.tools, TOOL, arguments, plain(receiver.context.scope), key)
        work = asyncio.run(prepare_protein_structure_work(case.tools, TOOL, arguments, scope=plain(receiver.context.scope),
            operation_key=key, authority=authority, input_authority=receiver.records))
        if alter == "selected_source":
            value = work["redisplay"]["result"]
            value["source_ref"] = "source_" + "f" * 64
            for view in value["views"]:
                view["source_ref"] = value["source_ref"]
            for descriptor in value["saved_sheets"]:
                descriptor["custody"]["source_ref"] = value["source_ref"]
            validate_protein_structure_tool_result(value)
        else:
            corrupt_summary_values(work["redisplay"]["result"])
        with pytest.raises(ContractError, match="original_commission_mismatch"):
            validate_prepared_protein_structure_work(case.tools, work, authority=authority)


def test_recorded_redisplay_cell_tamper_cannot_become_own_facts(retained):
    case, receiver = retained, retained.receiver()
    outcome = read(case, receiver)
    changed = deepcopy(outcome)
    corrupt_summary_values(changed["result"])
    key = f"{receiver.flow.run_id}:{receiver.caller.source.episode_id}:0"
    with case.store.transaction():
        case.store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0",
            (canonical(changed), receiver.flow.run_id, receiver.caller.source.episode_id))
        case.store.db.execute("UPDATE tool_operations SET result=? WHERE operation_key=?",
            (canonical({name: value for name, value in changed.items() if name != "pending_work_after_action"}), key))
    with pytest.raises(ValueError):
        receiver.records.own_facts(receiver.context, fact_source=VIEW_SOURCE)
    assert receiver.records._producer(case.source_ref, verify_artifacts=True)["result"] == case.original_outcome["result"]


def test_selected_binding_substitution_rejected_before_retained_worker_validation(retained, monkeypatch):
    case, receiver = retained, retained.receiver()
    read(case, receiver)
    arguments = recalculate(case)
    with pytest.raises(ActionFailure):
        selected(case, receiver, arguments, 1)
    key = f"{receiver.flow.run_id}:{receiver.caller.source.episode_id}:1"
    from gene_annotation_episode.protein_structure_tools import _saved_binding
    binding = _saved_binding(case.tools._protein_structure_configuration, arguments)
    binding["environment"]["UNSELECTED_SETTING"] = "substituted"
    admission = receiver.records.saved_action_inputs(receiver.context, case.descriptor,
        required_use="recalculate", before_decision_index=1)["admission"]
    work = dict(version=SAVED_WORK_VERSION, mode="recalculate", tool_name=TOOL, arguments=arguments,
        scope=plain(receiver.context.scope), invocation=dict(run_id=receiver.flow.run_id,
            episode_id=receiver.caller.source.episode_id, operation_key=key,
            request_sha256=digest(plain(receiver.context.request))), admission=admission, binding=binding,
        worker=None, qualified_files={}, scientific=None, issues=[], redisplay=None)
    monkeypatch.setattr("gene_annotation_episode.protein_structure_tools.validate_saved_protein_work", forbidden)
    with case.tools.current_invocation(receiver.context, read_received=receiver.flow.services.read_received_molecular_input,
            tool_name=TOOL, arguments=arguments, operation_key=key), case.tools.protein_structure_invocation(receiver.records):
        authority = authenticate_molecular_invocation(case.tools, TOOL, arguments, plain(receiver.context.scope), key)
        with pytest.raises(ContractError, match="original_commission_mismatch"):
            validate_prepared_protein_structure_work(case.tools, work, authority=authority)


def test_real_read_factory_preserves_actual_v1_receipts_without_writes_or_transform_grants(monkeypatch):
    """Positive336 v1 custody, not a positive received-fitted transform claim."""
    database = LEGACY_BASE / "state/state.sqlite3"
    proof = LEGACY_BASE.parent / "PROTEIN_STRUCTURE_CURRENT_V2_WORKFLOW.json"
    if not database.is_file() or not proof.is_file():
        pytest.skip("requires the explicitly staged immutable336 legacy evidence")
    assert hashlib.sha256(database.read_bytes()).hexdigest() == LEGACY_DATABASE_SHA256
    assert hashlib.sha256(proof.read_bytes()).hexdigest() == LEGACY_PROOF_SHA256
    before = (pins(LEGACY_BASE / "state"), pins(LEGACY_BASE / "run"))
    store = Store.__new__(Store)
    store.path = LEGACY_BASE / "state"
    store.db = sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True)
    store.db.row_factory, store._savepoint = sqlite3.Row, 0
    store.db.create_function("library_scope_record", 2, store._scope_filter_record)
    try:
        run_id = "protein-structure-workflow410"
        episode_id = "episode_cf12e8e145086480f262cf2750df515fd2305831f3c7589782647ce226ea6331"
        row = store.db.execute("SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=0",
            (run_id, episode_id)).fetchone()
        result = json.loads(row["result"])["result"]
        packet = result["publication"]
        custody = packet["custody"]
        descriptor, = packet["facts"]["execution_protein_structure_saved_sheets"]
        assert descriptor["version"] == "protein_structure_saved_sheet_v1"
        context_records = EpisodeReturnRecords(store, run_id, failure_prefix="legacy_saved_test_")
        parent_id = store.db.execute("SELECT parent_episode_id FROM runtime_report_attempts WHERE run_id=? "
            "AND child_episode_id=? AND failure IS NULL", (run_id, episode_id)).fetchone()[0]
        parent = context_records.context(parent_id)
        components = json.loads(store.get_artifact(descriptor["original_components_file"]["artifact_ref"]))
        request = result["body"]["bundle"]["requested_job"]["native_protein_structure"]["request"]
        raw_refs = {request[side + "_selection"]["file_identity"]["artifact_ref"] for side in ("fixed", "moving")}
        raw_paths = {store.path / "artifacts" / ref.removeprefix("artifact_")[:2] / ref.removeprefix("artifact_")
            for ref in raw_refs}
        producer_workspace = Path(result["body"]["handoff_proof"]["assignment_snapshot"]["assignment"]["workspace"])
        transform = dict(version="protein_structure_transform_v1", direction="moving_to_fixed",
            convention="row_vector_y_R_plus_t", origin="received_fitted",
            fixed_selection=request["fixed_selection"], moving_selection=request["moving_selection"],
            rotation=components["transform"]["rotation"]["value"],
            translation_A=components["transform"]["translation"]["value"], received_from=dict(
                saved_sheet=descriptor, calculation_custody=custody,
                components_file=descriptor["original_components_file"], calculation_id=components["calculation_id"]))
        changes = store.db.total_changes
        store.db.execute("PRAGMA query_only=ON")
        denied_sql = {getattr(sqlite3, name) for name in (
            "SQLITE_INSERT", "SQLITE_UPDATE", "SQLITE_DELETE", "SQLITE_CREATE_INDEX", "SQLITE_CREATE_TABLE",
            "SQLITE_CREATE_TEMP_INDEX", "SQLITE_CREATE_TEMP_TABLE", "SQLITE_CREATE_TEMP_TRIGGER", "SQLITE_CREATE_TEMP_VIEW",
            "SQLITE_CREATE_TRIGGER", "SQLITE_CREATE_VIEW", "SQLITE_DROP_INDEX", "SQLITE_DROP_TABLE",
            "SQLITE_DROP_TEMP_INDEX", "SQLITE_DROP_TEMP_TABLE", "SQLITE_DROP_TEMP_TRIGGER", "SQLITE_DROP_TEMP_VIEW",
            "SQLITE_DROP_TRIGGER", "SQLITE_DROP_VIEW", "SQLITE_ALTER_TABLE", "SQLITE_REINDEX", "SQLITE_ANALYZE",
            "SQLITE_ATTACH", "SQLITE_DETACH")}
        store.db.set_authorizer(lambda action, *args: sqlite3.SQLITE_DENY if action in denied_sql else sqlite3.SQLITE_OK)
        with monkeypatch.context() as guard:
            for name in ("artifact", "put", "commit_reasoning"):
                guard.setattr(Store, name, forbidden)
            saved_get, saved_open = Store.get_artifact, Path.open
            observed_refs, observed_paths = set(), set()

            def get_artifact(instance, reference):
                assert reference not in raw_refs, "original raw structure bytes are forbidden"
                observed_refs.add(reference)
                return saved_get(instance, reference)

            def open_path(path, *args, **kwargs):
                assert path not in raw_paths and not path.is_relative_to(producer_workspace), "original structures/workspace are forbidden"
                observed_paths.add(path)
                return saved_open(path, *args, **kwargs)

            guard.setattr(Store, "get_artifact", get_artifact)
            guard.setattr(Path, "open", open_path)
            from gene_annotation_episode import protein_structure_result_receipts as receipt_module
            saved_directory = receipt_module._directory

            def metadata_directory(path, *args, **kwargs):
                assert not Path(path).is_relative_to(producer_workspace), "producer workspace access is forbidden"
                return saved_directory(path, *args, **kwargs)

            guard.setattr(receipt_module, "_directory", metadata_directory)
            for module, names in (
                    ("gene_annotation_episode.native_lifecycle", ("prepare_job", "start_prepared", "resume_start", "wait_job", "status", "collect")),
                    ("gene_annotation_episode.protein_structure_calculations", ("calculate_protein_structure_components", "fit_ca_transform")),
                    ("gene_annotation_episode.native_protein_structure_results", ("publish_protein_structure_source",)),
                    ("gene_annotation_episode.protein_structure_formats", ("parse_pdb_structure", "parse_mmcif_structure"))):
                for name in names:
                    guard.setattr(module + "." + name, forbidden)
            reader = ExecutionEpisodes.retained_protein_structure_reader(store,
                run_id=run_id, directory=LEGACY_BASE / "run")
            assert type(reader.owner) is ExecutionEpisodes
            assert not hasattr(reader.owner, "resources") and not hasattr(reader.owner, "services")
            original = reader.results.read_result_authority(custody, scope=plain(parent.scope))
            received = reader.authenticate_received_saved_sheet(parent, descriptor, required_use="use_transform")
            assert original == received
            assert original["sheet_file"] == descriptor["sheet_file"]
            assert original["original_components_file"] == descriptor["original_components_file"]
            assert original["facts"]["execution_protein_structure_saved_sheets"] == [descriptor]
            projections = original["facts"]["execution_protein_structure_projections"]
            assert [value["family"] for value in projections] == ["comparison_summary"]
            # The genuine comparison fitted a transform, but no transform
            # projection was selected and typed back. Custody cannot grant it.
            assert all(value["family"] != "transform" for value in projections)
            assert reader.received_transform_projections(parent, transform) == []
            from gene_annotation_episode.protein_structure_operands import authenticate_received_structure_transform
            from gene_annotation_episode.protein_structure_authority import ProteinStructureOperandError
            records = ProteinStructureActionRecords(store, run_id, legacy_returns=reader)
            with pytest.raises(ProteinStructureOperandError, match="invalid_transform"):
                authenticate_received_structure_transform(store, parent, transform, returns=records)
            independent = ExecutionEpisodes.retained_protein_structure_reader(store,
                run_id=run_id, directory=LEGACY_BASE / "run")
            assert independent is not reader and independent.results.read_result_authority(
                custody, scope=plain(parent.scope)) == original
            assert store.db.total_changes == changes == 0
            assert observed_refs.isdisjoint(raw_refs) and observed_paths.isdisjoint(raw_paths)
    finally:
        store.close()
    assert (pins(LEGACY_BASE / "state"), pins(LEGACY_BASE / "run")) == before
    assert hashlib.sha256(database.read_bytes()).hexdigest() == LEGACY_DATABASE_SHA256
    assert hashlib.sha256(proof.read_bytes()).hexdigest() == LEGACY_PROOF_SHA256
