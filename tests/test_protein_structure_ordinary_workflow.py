"""Actual ordinary protein tools in one scientific episode, with no model RPC.

Tiny engineering structures, an explicit map and a supplied transform exercise
the selected native software. Scripted decisions and controller horizons are
test seams. This does not rerun the historical fitting Workflow or claim a
NativeExecution statistics receipt.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shutil
import sqlite3
import sys

import Bio
import numpy
import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.native_protein_structure_contracts import DRIVER_MODULE, POLICY, WORKER_MODULE
from gene_annotation_episode.protein_structure_action_records import (
    SAVED_SOURCE, SEQUENCE_SOURCE, VIEW_SOURCE, ProteinStructureActionRecords,
    frozen_protein_structure_action_facts, protein_structure_action_fact_sources,
    validate_frozen_protein_structure_action_return,
)
from gene_annotation_episode.protein_structure_formats import parse_pdb_structure
from gene_annotation_episode.protein_structure_sequences import extract_structure_sequence
from gene_annotation_episode.runtime import DecisionSource, Workflow
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController, ScriptedProvider
from test_scientific_process_runtime import Scenario, action


ROOT = Path(__file__).resolve().parents[1]
NAMES = ("inspect_protein_structure", "extract_protein_structure_sequence", "compare_protein_structures")
QUESTION = ("For these two supplied two-residue structures and their explicit correspondence, "
    "what sequence is observed, and what pair counts, SSE, RMSD and individual distances follow "
    "from the supplied moving-to-fixed translation without fitting?")
MODULES = ("native_protein_structure_contracts", "native_protein_structure_local",
    "native_protein_structure_driver", "native_protein_structure_worker", "native_protein_structure_tool_info",
    "protein_structure_contracts", "protein_structure_formats", "protein_structure_sequences",
    "protein_structure_correspondence", "protein_structure_metadata", "protein_structure_sheet",
    "protein_structure_calculations", "biopython_pairwise_grader", "alignment_correspondence")
SUMMARY_FIELDS = ["mapped_pair_count", "fit_used_count", "evaluation_used_count", "above_threshold_count",
    "evaluation_sse", "evaluation_rmsd"]


def _file(store, raw, format):
    ref = store.artifact(raw, media_type="application/octet-stream")
    return dict(artifact_ref=ref, sha256=hashlib.sha256(raw).hexdigest(), byte_length=len(raw), format=format)


def _structure(store, xs, role):
    lines = [f"ATOM  {index:5d}  CA  {component:>3s} A{index:4d}    "
        f"{x:8.3f}{0.:8.3f}{0.:8.3f}{1.:6.2f}{20.:6.2f}           C  \n"
        for index, (component, x) in enumerate(zip(("ALA", "GLY"), xs), 1)]
    raw = ("".join(lines) + "END\n").encode("ascii")
    file = _file(store, raw, "pdb_3x_text")
    parsed = parse_pdb_structure(raw, file_identity=file)
    # These explicit fixture indices describe the supplied engineering bytes.
    model, chain = parsed["models"][0], parsed["chains"][0]
    selection = dict(structure_role=role, file_identity=file, data_block=None,
        model_key=deepcopy(model["model_key"]), chain_key=deepcopy(chain["chain_key"]),
        sequence_basis="observed_polymer", residue_variant_choices=[],
        symbol_policy=dict(unknown="reject", explicit_component_overrides=[]),
        ca_selection=dict(policy="unambiguous_only", choices=[]), zero_occupancy_policy="include",
        bfactor_semantics="unspecified", semantics_evidence=None)
    sequence = extract_structure_sequence(parsed, selection=selection)
    assert sequence["sequence_available"] and sequence["alignment_sequence"] == "AG"
    return file, selection, sequence


def _requests(store):
    fixed_file, fixed, fixed_sequence = _structure(store, (0., 2.), "fixed")
    moving_file, moving, moving_sequence = _structure(store, (1., 4.), "moving")
    document = dict(version="protein_residue_map_v1", declared_order="collinear", fixed_selection=fixed,
        moving_selection=moving, rows=[dict(fixed_position_key=f["position_key"], moving_position_key=m["position_key"])
            for f, m in zip(fixed_sequence["residues"], moving_sequence["residues"])])
    map_file = _file(store, canonical(document).encode(), "protein_residue_map_v1")
    transform = dict(version="protein_structure_transform_v1", direction="moving_to_fixed",
        convention="row_vector_y_R_plus_t", rotation=[[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]],
        translation_A=[-1., 0., 0.], fixed_selection=fixed, moving_selection=moving,
        origin="supplied", received_from=None)
    parameters = dict(version="protein_structure_calculation_parameters_v1",
        mode="evaluate_declared_transform_ca", fit_selection=None,
        evaluation_selection=dict(kind="all_mapped_pairs"), missing_coordinate_policy="require_all",
        declared_transform=transform, distance_threshold_A=2., coordinate_sets=[], numerical={
            "svd_relative_tolerance": 1e-12, "svd_absolute_tolerance_A2": 1e-12,
            "geometry_absolute_tolerance_A": 1e-12, "rotation_orthogonality_tolerance": 1e-10,
            "rotation_determinant_tolerance": 1e-10, "sse_roundoff_absolute_tolerance_A2": 1e-10,
            "sse_roundoff_relative_tolerance": 1e-12})
    single = {**deepcopy(fixed), "structure_role": "single"}
    requests = [dict(version="protein_structure_inspect_request_v1", operation="inspect", structure_file=fixed_file,
        inventory=dict(blocks=dict(kind="all"), include=["models", "chains", "sequence_bases"])),
        dict(version="protein_structure_extract_request_v1", operation="extract_sequence", selection=single,
            supplied_metadata_files=[]),
        dict(version="protein_structure_compare_request_v1", operation="compare", fixed_selection=fixed,
            moving_selection=moving, correspondence=dict(kind="explicit_map", map_file=map_file),
            parameters=parameters, supplied_metadata_files=[])]
    return requests, [fixed_file, moving_file, map_file]


def _software():
    return dict(python_executable=sys.executable, python_sha256=hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
        python_version=platform.python_version(), driver_module=DRIVER_MODULE, worker_module=WORKER_MODULE,
        implementation_files=[dict(module="gene_annotation_episode." + module,
            sha256=hashlib.sha256((ROOT / "gene_annotation_episode" / (module + ".py")).read_bytes()).hexdigest())
            for module in MODULES], numpy_version=numpy.__version__, biopython_version=Bio.__version__,
        implementation="gene_annotation_episode_corrected_protein_structure_v1", algorithm="unweighted_proper_rigid_ca_svd_v1")


def _configuration(tmp_path):
    software = _software()
    resources = {"ordinary-selected": dict(kind="local", workspace=str(tmp_path / "native-workspace"),
        policy=deepcopy(POLICY), native_protein_structure=[dict(operation=operation, scientific_mode=mode,
            software=deepcopy(software)) for operation, mode in
            (("inspect", None), ("extract_sequence", None), ("compare", "evaluate_declared_transform_ca"))])}
    pythonpath = os.pathsep.join(dict.fromkeys([str(ROOT), *filter(None, os.environ.get("PYTHONPATH", "").split(os.pathsep))]))
    environment = dict(PYTHONPATH=pythonpath, PYTHONDONTWRITEBYTECODE="1", ORDINARY_PROTEIN_TEST_SETTING="literal")
    environments = [dict(resource_id="ordinary-selected", binding_ordinal_0based=index,
        environment=deepcopy(environment)) for index in range(3)]
    return resources, environments


def _projection(identity, family, members, fields, *, delivery="values"):
    return dict(projection_id=identity, family=family, members=members, fields=fields, window=None, delivery_kind=delivery)


def _arguments(requests):
    selections = [[_projection("chain", "structure_inventory", dict(kind="inventory_rows", row_keys=["chain_0"]), ["chain"])],
        [_projection("sequence", "extracted_sequence", dict(kind="extracted_sequence", residue_positions=dict(kind="all")),
            ["descriptor", "alignment_sequence", "sequence_length"])],
        [_projection("summary", "comparison_summary", dict(kind="comparison"), SUMMARY_FIELDS),
            _projection("distances", "site_measurements", dict(kind="all_evaluation_requests"),
                ["distance", "distance_squared"], delivery="artifact"),
            _projection("unrequested_coordinates", "structure_coordinates",
                dict(kind="coordinate_set", coordinate_set_id="not_requested"), ["xyz"])]]
    return [dict(resource_id="ordinary-selected", binding_ordinal_0based=index, request=request,
        selection=dict(projections=selections[index], return_saved_sheet=index == 2,
            sequence_allowed_uses=["structure_correspondence"] if index == 1 else []))
        for index, request in enumerate(requests)]


def _credit(store, scope, **kwargs):
    return 0


def _controllers(path, initial):
    return FixtureController(str(path), initial, 1 if len(path) == 1 else 3)


def _workflow(case, tools, provider, originals):
    return Workflow(case.store, tools, provider, case.directory, "ordinary-protein-regression", _controllers, _credit,
        project_child_credit=_credit, episode_binding_descriptors=case.descriptors,
        episode_record_receipts=True, initial_known_record_refs=[file["artifact_ref"] for file in originals])


def _tables(store):
    names = [row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    return {name: sorted((tuple((type(value).__name__, value) for value in row)
        for row in store.db.execute('SELECT * FROM "' + name.replace('"', '""') + '"')), key=repr) for name in names}


def _json(store, reference):
    return json.loads(store.get_artifact(reference))


def _pending_checkpoint(store, *, run_directory, source_directory, destination, operation_key, outcome):
    """Copy an actual committed-publication/pending-action prefix, without edits."""
    assert not store.db.in_transaction
    destination.mkdir()
    snapshot_store = destination / "store"
    snapshot_store.mkdir()
    database = snapshot_store / "state.sqlite3"
    connection = sqlite3.connect(database)
    try:
        store.db.backup(connection)
    finally:
        connection.close()
    shutil.copytree(store.path / "artifacts", snapshot_store / "artifacts")
    library_root = destination / "run"
    library_root.mkdir()
    libraries = ("scientific-process-library", "scientific-tool-library", "tool-knowledge", "launch-instructions")
    for name in libraries:
        shutil.copytree(run_directory / name, library_root / name)
    shutil.copytree(source_directory, destination / "source")
    connection = sqlite3.connect(database.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        run_id, episode_id, index = operation_key.rsplit(":", 2)
        pending = connection.execute("SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?",
            (run_id, episode_id, int(index))).fetchone()
        assert pending is not None and pending["result"] is None and pending["credit"] is None
        assert json.loads(pending["action"])["tool"] == NAMES[2]
        operation = connection.execute("SELECT * FROM tool_operations WHERE operation_key=?", (operation_key,)).fetchone()
        assert operation is not None and json.loads(operation["result"]) == outcome
        assert outcome["status"] == "partial"
        counts = {name: connection.execute("SELECT count(*) FROM " + name).fetchone()[0] for name in
            ("runtime_episodes", "runtime_actions", "runtime_observations", "runtime_model_calls",
                "tool_operations", "runtime_forms", "runtime_report_attempts")}
        assert counts == dict(runtime_episodes=2, runtime_actions=4, runtime_observations=2,
            runtime_model_calls=4, tool_operations=3, runtime_forms=0, runtime_report_attempts=0)
        copied = {}
        for base in (snapshot_store / "artifacts", library_root, destination / "source"):
            for path in sorted(base.rglob("*")):
                if path.is_file():
                    raw = path.read_bytes()
                    copied[str(path.relative_to(destination))] = dict(sha256=hashlib.sha256(raw).hexdigest(), byte_length=len(raw))
        raw = database.read_bytes()
        return dict(directory=str(destination), operation_key=operation_key, action_result=None, action_credit=None,
            saved_operation_status=outcome["status"], counts=counts, original_store_path=str(store.path),
            database=dict(sha256=hashlib.sha256(raw).hexdigest(), byte_length=len(raw)), copied_files=copied,
            portability_limit="The immutable worker plans retain original absolute Store/native input paths. "
                "These copied bytes prove the real pending prefix; relocation alone is not a qualified Workflow replay.")
    finally:
        connection.close()


def _forbidden(*args, **kwargs):
    raise AssertionError("saved ordinary protein work attempted new native/input/scientific work")


class PublicationResponseLost(RuntimeError):
    pass


def test_actual_ordinary_protein_tools_recover_and_return_in_one_scientific_episode(tmp_path, monkeypatch):
    resources, environments = _configuration(tmp_path)
    monkeypatch.setattr("gene_annotation_episode.acquisition.PublicClients._http", _forbidden)
    monkeypatch.setattr("socket.create_connection", _forbidden)
    with Store(tmp_path / "store") as store:
        requests, originals = _requests(store)
        arguments = _arguments(requests)
        tools = ToolRegistry(store, job_limits=deepcopy(POLICY))
        tools.configure_protein_structure_resources(resources, environments)
        case = Scenario(tmp_path, store, tools=tools)
        sources = protein_structure_action_fact_sources()
        # This is an actual descriptor-only parent contract. ActionView Source
        # annotations cannot accidentally supply the descriptor receipt grants.
        field_sources = {"chosen_sequences": SEQUENCE_SOURCE, "chosen_saved": SAVED_SOURCE}
        form_schema = obj({field: sources[source]["report_schema"] for field, source in field_sources.items()})
        commission = case.commission()
        commission["selection"].update(goal=QUESTION, purpose="Return the selected literal protein values and declared-use descriptors",
            schema_json=json.dumps(form_schema), initial_report_json="{}")
        commission["selection"]["assignment"]["selection"] = case.selection(tools=NAMES)
        provider = ScriptedProvider([commission, *[action(name, args) for name, args in zip(NAMES, arguments)]])
        workflow = _workflow(case, tools, provider, originals)
        root = workflow.build("annotation", "root", QUESTION, case.scope)
        original_execute, lost, checkpoints = ToolRegistry.execute_async, [], []

        async def lose_after_saved_publication(registry, name, args, **kwargs):
            outcome = await original_execute(registry, name, args, **kwargs)
            if name == NAMES[2] and not lost:
                assert outcome["status"] == "partial"
                row = registry.store.db.execute("SELECT * FROM tool_operations WHERE operation_key=?", (kwargs["operation_key"],)).fetchone()
                assert row is not None and json.loads(row["result"]) == outcome
                checkpoints.append(_pending_checkpoint(registry.store, run_directory=case.directory,
                    source_directory=case.source, destination=tmp_path / "pending-publication-checkpoint",
                    operation_key=kwargs["operation_key"], outcome=outcome))
                lost.append(dict(operation_key=kwargs["operation_key"], outcome=deepcopy(outcome)))
                raise PublicationResponseLost("actual saved ToolOperation before RuntimeAction response")
            return outcome

        with monkeypatch.context() as patch:
            patch.setattr(ToolRegistry, "execute_async", lose_after_saved_publication)
            with pytest.raises(PublicationResponseLost):
                asyncio.run(root.run_async(workflow.context))
        assert len(lost) == len(checkpoints) == 1 and len(provider.contexts) == 4
        pending = store.db.execute("SELECT * FROM runtime_actions WHERE run_id=? AND json_extract(action,'$.tool')=?",
            (workflow.run_id, NAMES[2])).fetchone()
        assert pending is not None and pending["result"] is None and pending["credit"] is None
        assert lost[0]["operation_key"] == f'{workflow.run_id}:{pending["episode_id"]}:{pending["decision_index"]}'
        assert store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 3
        published = [source for source in store.list("source") if source["provider"] == "episode.execution_result"]
        assert len(published) == 3
        capsules = [_json(store, source["request_ref"]) for source in published]
        capsules.sort(key=lambda capsule: capsule["arguments"]["binding_ordinal_0based"])
        assert [capsule["tool_name"] for capsule in capsules] == list(NAMES)
        for index, capsule in enumerate(capsules):
            assert capsule["arguments"] == arguments[index]
            assert capsule["binding"]["software"] == resources["ordinary-selected"]["native_protein_structure"][index]["software"]
            assert capsule["binding"]["environment"] == environments[index]["environment"]
            execution = capsule["execution"]
            assert execution["outcome"] == "returned" and execution["returncode"] == 0
            assert execution["terminal"] is execution["quiescent"] is True
            assert execution["metadata"]["policy"] == POLICY
            assert execution["metadata"]["duration_measure"] == "systemd_service_wall_seconds"
            assert execution["metadata"]["elapsed_seconds"] >= 0
            handle = _json(store, execution["artifacts"]["native.json"])
            original = _json(store, "artifact_" + handle["request_sha256"])
            assert handle["command"][0] == sys.executable and original["command"] == handle["command"]
            assert original["env"]["ORDINARY_PROTEIN_TEST_SETTING"] == "literal"
            assert original["env"]["PYTHONPATH"] == environments[index]["environment"]["PYTHONPATH"]
            worker = capsule["worker"]
            assert worker["plan"]["expected_software"] == capsule["binding"]["software"]
            handle = _json(store, worker["execution"]["handle_artifact_ref"])
            original = _json(store, "artifact_" + handle["request_sha256"])
            assert handle["command"][0] == sys.executable
            assert original["env"]["ORDINARY_PROTEIN_TEST_SETTING"] == "literal"
            assert worker["execution"]["metadata"]["policy"] == POLICY
        # Withdraw the actual producer directory and input bytes after real
        # publication, before recovery. Their metadata records remain truthful.
        workspace = Path(resources["ordinary-selected"]["workspace"])
        assert len(list(workspace.rglob("native.json"))) == 3
        assert len(list(workspace.rglob("worker.handle.json"))) == 3
        for file in originals:
            path = store.path / "artifacts" / file["sha256"][:2] / file["sha256"]
            assert path.is_file()
            path.unlink()
        shutil.rmtree(workspace)
        monkeypatch.setattr("gene_annotation_episode.protein_structure_tools.run_cancellable_native", _forbidden)
        monkeypatch.setattr("gene_annotation_episode.protein_structure_tools.resolve_protein_structure_operands", _forbidden)
        monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", _forbidden)
        monkeypatch.setattr("gene_annotation_episode.native_lifecycle.start_prepared", _forbidden)
        monkeypatch.setattr("gene_annotation_episode.native_lifecycle.resume_start", _forbidden)
        monkeypatch.setattr("gene_annotation_episode.protein_structure_formats.parse_pdb_structure", _forbidden)
        monkeypatch.setattr("gene_annotation_episode.protein_structure_formats.parse_mmcif_structure", _forbidden)
        monkeypatch.setattr("gene_annotation_episode.protein_structure_calculations.calculate_protein_structure_components", _forbidden)
        monkeypatch.setattr("gene_annotation_episode.protein_structure_calculations.fit_ca_transform", _forbidden)
        restored_tools = ToolRegistry(store, job_limits=deepcopy(POLICY))
        restored_tools.configure_protein_structure_resources(resources, environments)
        restored_provider = ScriptedProvider([])
        restored = _workflow(case, restored_tools, restored_provider, originals)
        recovered_root = restored.build("annotation", "root", QUESTION, case.scope)
        record = asyncio.run(recovered_root.run_async(restored.context))
        asyncio.run(recovered_root.build_result(record))
        assert restored_provider.contexts == [] and not workspace.exists()
        episodes = list(store.db.execute("SELECT * FROM runtime_episodes ORDER BY json_array_length(path)"))
        assert len(episodes) == 2
        assert [json.loads(row["path"])[-1][0] for row in episodes] == ["annotation", "scientific_process"]
        assert all(row["state"] == "yielded" for row in episodes)
        root_id, science_id = (row["episode_id"] for row in episodes)
        rows = list(store.db.execute("SELECT * FROM runtime_actions WHERE episode_id=? ORDER BY decision_index", (science_id,)))
        assert [json.loads(row["action"])["tool"] for row in rows] == list(NAMES)
        assert [json.loads(row["result"])["status"] for row in rows] == ["completed", "completed", "partial"]
        recovered_outcome = json.loads(rows[2]["result"])
        recovered_outcome.pop("pending_work_after_action", None)
        assert recovered_outcome == lost[0]["outcome"]
        for episode, expected in zip(episodes, (1, 3)):
            assert json.loads(episode["completion"])["actions"] == expected
            for table in ("runtime_actions", "runtime_observations", "runtime_model_calls"):
                assert store.db.execute(f"SELECT count(*) FROM {table} WHERE episode_id=?", (episode["episode_id"],)).fetchone()[0] == expected
        assert store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 3
        assert not store.list("native_execution")
        returned = json.loads(store.db.execute("SELECT form FROM runtime_forms WHERE episode_id=?", (science_id,)).fetchone()[0])
        assert set(returned) == set(field_sources)
        views = [view for row in rows for view in json.loads(row["result"])["result"]["views"]]
        assert len(views) == 5 and len(returned["chosen_sequences"]) == len(returned["chosen_saved"]) == 1
        by_id = {view["selection"]["projection_id"]: view for view in views}
        chain, = by_id["chain"]["outcome"]["rows"]
        assert chain["values"][0]["value"]["observed_polymer_position_count"] == 2
        sequence, = by_id["sequence"]["outcome"]["rows"]
        cells = {cell["field"]: cell["value"] for cell in sequence["values"]}
        assert cells["alignment_sequence"] == "AG" and cells["sequence_length"]["value"] == 2
        assert cells["descriptor"] == returned["chosen_sequences"][0]
        assert cells["descriptor"]["version"] == "structure_sequence_descriptor_v2"
        summary, = by_id["summary"]["outcome"]["rows"]
        cells = {cell["field"]: cell for cell in summary["values"]}
        expected = dict(mapped_pair_count=2, evaluation_used_count=2, above_threshold_count=0,
            evaluation_sse=1, evaluation_rmsd=math.sqrt(.5))
        for field, value in expected.items():
            assert cells[field]["value"]["state"] == "present" and cells[field]["value"]["reason"] is None
            assert cells[field]["value"]["value"] == pytest.approx(value, abs=1e-10)
        assert cells["fit_used_count"]["value"]["state"] == "not_applicable"
        assert cells["fit_used_count"]["value"]["value"] is None
        assert cells["evaluation_sse"]["value"]["unit"] == "angstrom_squared"
        assert cells["evaluation_rmsd"]["value"]["unit"] == "angstrom"
        assert cells["evaluation_rmsd"]["population"]["denominator"] == 2
        artifact = by_id["distances"]["outcome"]
        assert "rows" not in artifact and artifact["delivery"]["row_count"] == 2
        file = artifact["delivery"]["table_file"]
        raw = store.get_artifact(file["artifact_ref"])
        assert hashlib.sha256(raw).hexdigest() == file["sha256"] and len(raw) == file["byte_length"]
        table = json.loads(raw)
        distances = [row["values"][0]["value"] for row in table["rows"]]
        assert [cell["value"] for cell in distances] == [0, 1]
        assert all(cell["state"] == "present" and cell["reason"] is None for cell in distances)
        assert by_id["unrequested_coordinates"]["outcome"]["version"] == "protein_structure_action_unavailable_v1"
        assert returned["chosen_saved"][0]["version"] == "protein_structure_saved_sheet_v2"
        assert returned["chosen_saved"][0]["original_mode"] == "evaluate_declared_transform_ca"
        contexts = EpisodeReturnRecords(store, restored.run_id, failure_prefix="ordinary_protein_regression_")
        science, parent = contexts.context(science_id), contexts.context(root_id)
        for field, source in field_sources.items():
            assert restored.services.protein_structure_action_received_facts(parent, fact_source=source) == returned[field]
        assert restored.services.protein_structure_action_received_facts(parent, fact_source=VIEW_SOURCE) == []
        assert restored.services.protein_structure_action_own_facts(science, fact_source=VIEW_SOURCE) == views
        known = set(restored.receipts.known(root_id))
        sequence_descriptor, = returned["chosen_sequences"]
        saved_descriptor, = returned["chosen_saved"]
        assert sequence_descriptor["custody"]["source_ref"] in known
        assert saved_descriptor["custody"]["source_ref"] in known
        assert sequence_descriptor["reference_ref"] in known
        inspect_source = json.loads(rows[0]["result"])["result"]["source_ref"]
        assert inspect_source not in known
        assert sequence_descriptor["residue_map_file"]["artifact_ref"] not in known
        assert saved_descriptor["sheet_file"]["artifact_ref"] not in known
        assert saved_descriptor["original_components_file"]["artifact_ref"] not in known
        assert file["artifact_ref"] not in known
        assert store.db.execute("SELECT count(*) FROM runtime_report_attempts WHERE failure IS NULL").fetchone()[0] == 1
        before = _tables(store)
        with monkeypatch.context() as frozen:
            frozen.setattr("gene_annotation_episode.protein_structure_result_views.project_protein_structure_results", _forbidden)
            frozen.setattr("gene_annotation_episode.protein_structure_action_records.project_protein_structure_action_views", _forbidden)
            for field, source in field_sources.items():
                assert frozen_protein_structure_action_facts(store, restored.run_id, science, fact_source=source) == returned[field]
            replay_provider = ScriptedProvider([])
            replay = _workflow(case, restored_tools, replay_provider, originals)
            replay_root = replay.build("annotation", "root", QUESTION, case.scope)
            replay_record = asyncio.run(replay_root.run_async(replay.context))
            asyncio.run(replay_root.build_result(replay_record))
            assert replay_provider.contexts == []
        assert _tables(store) == before and not workspace.exists()
        assert len(provider.contexts) == 4 and restored_provider.contexts == []
        (tmp_path / "PROTEIN_STRUCTURE_ORDINARY_WORKFLOW.json").write_text(json.dumps({
            "qualification": "new tiny engineering bytes, actual selected native tools, scripted decisions; no fitting or model RPC",
            "question": QUESTION, "episodes": [{"episode_id": row["episode_id"], "path": json.loads(row["path"]),
                "completion": json.loads(row["completion"])} for row in episodes],
            "counts": dict(episodes=2, actions=4, observations=4, scripted_decisions=len(provider.contexts), tool_operations=3),
            "lost_publication_response": lost, "native_publications": published, "publication_capsules": capsules,
            "actual_pending_checkpoint": checkpoints[0],
            "typed_return": returned, "expected_summary_values": expected, "selected_table": table,
            "numeric_parent_return": "not requested; numeric projections remain own-action values and selected table",
            "parent_received_references": sorted(known),
            "reference_sequence_dependency_received": sequence_descriptor["sequence_file"]["artifact_ref"] in known,
            "withdrawn_original_files": originals, "producer_workspace_removed": not workspace.exists(),
            "saved_operation_recovered_without_new_native_work": True, "frozen_replay_tables_unchanged": True,
            "native_execution_receipt": "unsupported; actual duration/policy retained only in native control metadata",
            "limits": "No live acquisition, biological conclusion, historical336 migration, fitted-transform case or real model behavior"
        }, indent=2) + "\n")


def _artifact_inventory(directory):
    return {str(path.relative_to(directory)): (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_size)
        for path in sorted(directory.rglob("*")) if path.is_file()}


def test_original_retained_ordinary_protein_receipts_and_frozen_facts(tmp_path, monkeypatch):
    supplied = os.environ.get("ORDINARY_PROTEIN_RETAINED_STORE")
    if not supplied:
        pytest.skip("requires an explicitly supplied original retained ordinary-protein Store")
    directory = Path(supplied).expanduser().resolve(strict=True)
    database = directory / "state.sqlite3"
    before_database = database.read_bytes()
    before_artifacts = _artifact_inventory(directory / "artifacts")
    # Store.__init__ would create tables/directories and change PRAGMAs. These
    # are its actual initialization attributes, with the original artifact path
    # and an immutable read-only connection instead of a constructor or clone.
    store = Store.__new__(Store)
    store.path = directory
    store.db = sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True)
    store.db.row_factory = sqlite3.Row
    store._savepoint = 0
    store.db.create_function("library_scope_record", 2, store._scope_filter_record)
    try:
        for method in ("artifact", "put", "commit_reasoning"):
            monkeypatch.setattr(Store, method, _forbidden)
        for module, names in (
            ("gene_annotation_episode.native_lifecycle", ("prepare_job", "start_prepared", "resume_start", "wait_job", "collect", "status")),
            ("gene_annotation_episode.protein_structure_tools", ("run_cancellable_native", "prepare_protein_structure_work", "resolve_protein_structure_operands")),
            ("gene_annotation_episode.protein_structure_operands", ("resolve_protein_structure_operands",)),
            ("gene_annotation_episode.native_protein_structure_preparation", ("prepare_protein_structure_worker",)),
            ("gene_annotation_episode.protein_structure_formats", ("parse_pdb_structure", "parse_mmcif_structure")),
            ("gene_annotation_episode.protein_structure_calculations", ("calculate_protein_structure_components", "fit_ca_transform")),
        ):
            for name in names:
                monkeypatch.setattr(module + "." + name, _forbidden)
        monkeypatch.setattr("gene_annotation_episode.acquisition.PublicClients._http", _forbidden)
        monkeypatch.setattr("socket.create_connection", _forbidden)
        run_id, = [row[0] for row in store.db.execute("SELECT DISTINCT run_id FROM runtime_episodes")]
        episodes = list(store.db.execute("SELECT * FROM runtime_episodes ORDER BY json_array_length(path)"))
        assert len(episodes) == 2 and all(row["state"] == "yielded" for row in episodes)
        contexts = EpisodeReturnRecords(store, run_id, failure_prefix="ordinary_protein_retained_")
        parent, science = [contexts.context(row["episode_id"]) for row in episodes]
        assert (parent.role, science.role) == ("annotation", "scientific_process")
        assert science.request["goal"]["objective"] == QUESTION
        schema = science.request["report_contract"]["measurements"]["schema"]
        frozen_row = store.db.execute("SELECT form FROM runtime_forms WHERE episode_id=?", (science.episode_id,)).fetchone()
        returned = json.loads(frozen_row["form"])
        assert set(returned) == set(schema["properties"]) == {"chosen_sequences", "chosen_saved"}
        attempt, = list(store.db.execute("SELECT form,failure FROM runtime_report_attempts WHERE parent_episode_id=?",
            (parent.episode_id,)))
        assert attempt["failure"] is None and json.loads(attempt["form"]) == returned
        records = ProteinStructureActionRecords(store, run_id)
        field_sources = {"chosen_sequences": SEQUENCE_SOURCE, "chosen_saved": SAVED_SOURCE}
        for field, source in field_sources.items():
            assert records.received_facts(parent, fact_source=source) == returned[field]
        assert records.received_facts(parent, fact_source=VIEW_SOURCE) == []
        actions = list(store.db.execute("SELECT action,result FROM runtime_actions WHERE episode_id=? ORDER BY decision_index",
            (science.episode_id,)))
        assert [json.loads(row["action"])["tool"] for row in actions] == list(NAMES)
        outcomes = [json.loads(row["result"]) for row in actions]
        assert [outcome["status"] for outcome in outcomes] == ["completed", "completed", "partial"]
        views = [view for outcome in outcomes for view in outcome["result"]["views"]]
        assert len(views) == 5
        # Saved publication authentication legitimately reads retained native
        # JSON and projects selected fields. It does no input parsing or work.
        assert records.own_facts(science, fact_source=VIEW_SOURCE) == views
        known = records._known(parent)
        sequence, = returned["chosen_sequences"]
        saved, = returned["chosen_saved"]
        assert {sequence["custody"]["source_ref"], saved["custody"]["source_ref"], sequence["reference_ref"]} <= known
        assert outcomes[0]["result"]["source_ref"] not in known
        excluded_files = [sequence["residue_map_file"], saved["sheet_file"], saved["original_components_file"],
            outcomes[2]["result"]["views"][1]["outcome"]["delivery"]["table_file"]]
        assert not {file["artifact_ref"] for file in excluded_files}.intersection(known)
        for outcome in outcomes:
            source = store.get(outcome["result"]["source_ref"])
            capsule = _json(store, source["request_ref"])
            assert not Path(capsule["binding"]["workspace"]).exists()
            for row in capsule["plan"]["requested_job"]["native_protein_structure"]["inputs"]:
                file = row["file_identity"]
                assert not (directory / "artifacts" / file["sha256"][:2] / file["sha256"]).exists()
        with monkeypatch.context() as frozen:
            frozen.setattr("gene_annotation_episode.protein_structure_result_views.project_protein_structure_results", _forbidden)
            frozen.setattr("gene_annotation_episode.protein_structure_action_records.project_protein_structure_action_views", _forbidden)
            for field, source in field_sources.items():
                facts = frozen_protein_structure_action_facts(store, run_id, science, fact_source=source)
                assert facts == returned[field]
                validate_frozen_protein_structure_action_return(returned, schema, facts, fact_source=source)
        counts = {name: store.db.execute("SELECT count(*) FROM " + name).fetchone()[0] for name in
            ("runtime_episodes", "runtime_actions", "runtime_observations", "runtime_model_calls",
                "tool_operations", "runtime_forms", "runtime_report_attempts")}
        assert counts == dict(runtime_episodes=2, runtime_actions=4, runtime_observations=4,
            runtime_model_calls=4, tool_operations=3, runtime_forms=1, runtime_report_attempts=1)
        assert store.db.total_changes == 0
    finally:
        store.close()
    assert database.read_bytes() == before_database
    assert _artifact_inventory(directory / "artifacts") == before_artifacts
    (tmp_path / "PROTEIN_STRUCTURE_RETAINED_READS.json").write_text(json.dumps({
        "qualification": "read-only original retained Store; no cloned-path or fresh Workflow replay claim",
        "original_store": str(directory), "database_sha256": hashlib.sha256(before_database).hexdigest(),
        "artifact_file_count": len(before_artifacts), "record_counts": counts,
        "received_descriptor_fields": list(field_sources), "own_selected_view_count": len(views),
        "descriptor_sources_and_reference_received": True, "unrequested_file_grants_absent": True,
        "reference_sequence_dependency_received": sequence["sequence_file"]["artifact_ref"] in known,
        "frozen_facts_without_projection": True, "SQL_changes": 0,
        "original_database_and_artifact_inventory_unchanged": True,
        "limits": "No dispatch, raw structure parsing, operand acquisition, calculation, full Workflow reconstruction or portability verification"
    }, indent=2) + "\n")


def _retained_resource_declarations(store):
    """Recover only the three actual configured declarations from their capsules."""
    capsules = []
    for row in store.db.execute("SELECT result FROM tool_operations ORDER BY operation_key"):
        outcome = json.loads(row["result"])
        source = store.get(outcome["result"]["source_ref"])
        capsules.append(_json(store, source["request_ref"]))
    capsules.sort(key=lambda value: value["binding"]["binding_ordinal_0based"])
    assert len(capsules) == 3
    assert [value["tool_name"] for value in capsules] == list(NAMES)
    assert [value["binding"]["binding_ordinal_0based"] for value in capsules] == [0, 1, 2]
    first = capsules[0]["binding"]
    assert all(all(value["binding"][field] == first[field] for field in ("resource_id", "workspace", "policy"))
        for value in capsules)
    resources = {first["resource_id"]: dict(kind="local", workspace=first["workspace"], policy=first["policy"],
        native_protein_structure=[{field: deepcopy(value["binding"][field])
            for field in ("operation", "scientific_mode", "software")} for value in capsules])}
    environments = [dict(resource_id=value["binding"]["resource_id"],
        binding_ordinal_0based=value["binding"]["binding_ordinal_0based"],
        environment=deepcopy(value["binding"]["environment"])) for value in capsules]
    inputs = [row["file_identity"]["artifact_ref"]
        for row in capsules[-1]["plan"]["requested_job"]["native_protein_structure"]["inputs"]]
    assert len(inputs) == len(set(inputs)) == 3
    return resources, environments, inputs


def test_original_ordinary_protein_closed_workflow_on_owned_database(tmp_path, monkeypatch):
    from method_loop.archive import iter_json
    from gene_annotation_episode.runtime import ReturnedActionUnit

    supplied = os.environ.get("ORDINARY_PROTEIN_RETAINED_STORE")
    if not supplied:
        pytest.skip("requires an explicitly supplied original retained ordinary-protein Store")
    directory = Path(supplied).expanduser().resolve(strict=True)
    database, original_run = directory / "state.sqlite3", directory.parent / "run"
    original_database = database.read_bytes()
    original_artifacts = _artifact_inventory(directory / "artifacts")
    original_run_files = _artifact_inventory(original_run)
    owned_database, owned_run = tmp_path / "owned-replay.sqlite3", tmp_path / "owned-replay-run"
    original = Store.__new__(Store)
    original.path = directory
    original.db = sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True)
    original.db.row_factory = sqlite3.Row
    original._savepoint = 0
    original.db.create_function("library_scope_record", 2, original._scope_filter_record)
    store = None
    try:
        before_tables = _tables(original)
        episodes = list(original.db.execute("SELECT * FROM runtime_episodes ORDER BY json_array_length(path)"))
        assert len(episodes) == 2 and all(row["state"] == "yielded" for row in episodes)
        run_id, = {row["run_id"] for row in episodes}
        parent_request, science_request = [json.loads(row["request"]) for row in episodes]
        assert [json.loads(row["path"])[-1][0] for row in episodes] == ["annotation", "scientific_process"]
        expected_form = json.loads(original.db.execute("SELECT form FROM runtime_forms WHERE episode_id=?",
            (episodes[1]["episode_id"],)).fetchone()[0])
        original_parent_outcome = json.loads(original.db.execute(
            "SELECT result FROM runtime_actions WHERE episode_id=? AND decision_index=0",
            (episodes[0]["episode_id"],)).fetchone()[0])
        original_parent_file_receipts = [dict(row) for row in original.db.execute(
            "SELECT * FROM runtime_record_receipts WHERE episode_id=? ORDER BY receipt_index",
            (episodes[0]["episode_id"],)) if row["record_ref"].startswith("artifact_")]
        descriptors = [deepcopy(science_request["message"]["scientific_process"]["mechanics_binding"]),
            LiteratureEpisodes(None).as_record()]
        resources, environments, inputs = _retained_resource_declarations(original)
        owned = sqlite3.connect(owned_database)
        try:
            original.db.backup(owned)
        finally:
            owned.close()
        shutil.copytree(original_run, owned_run)
        assert _artifact_inventory(owned_run) == original_run_files
        # SQL and archive writes have owned destinations. Artifact lookup keeps
        # the ORIGINAL Store path, preserving historical worker-plan equality.
        store = Store.__new__(Store)
        store.path = directory
        store.db = sqlite3.connect(owned_database, isolation_level=None, timeout=30)
        store.db.row_factory = sqlite3.Row
        store._savepoint = 0
        store.db.create_function("library_scope_record", 2, store._scope_filter_record)
        assert _tables(store) == before_tables
        for method in ("artifact", "put", "commit_reasoning"):
            monkeypatch.setattr(Store, method, _forbidden)
        for module, names in (
            ("gene_annotation_episode.native_lifecycle", ("prepare_job", "start_prepared", "resume_start", "wait_job", "collect", "status")),
            ("gene_annotation_episode.protein_structure_tools", ("run_cancellable_native", "prepare_protein_structure_work", "resolve_protein_structure_operands")),
            ("gene_annotation_episode.protein_structure_operands", ("resolve_protein_structure_operands",)),
            ("gene_annotation_episode.native_protein_structure_preparation", ("prepare_protein_structure_worker",)),
            ("gene_annotation_episode.protein_structure_formats", ("parse_pdb_structure", "parse_mmcif_structure")),
            ("gene_annotation_episode.protein_structure_calculations", ("calculate_protein_structure_components", "fit_ca_transform")),
            ("gene_annotation_episode.protein_structure_publication", ("publish_protein_structure_action_result",)),
            ("gene_annotation_episode.protein_structure_result_views", ("project_protein_structure_results",)),
            ("gene_annotation_episode.protein_structure_action_records", ("project_protein_structure_action_views",)),
        ):
            for name in names:
                monkeypatch.setattr(module + "." + name, _forbidden)
        monkeypatch.setattr("gene_annotation_episode.acquisition.PublicClients._http", _forbidden)
        monkeypatch.setattr("socket.create_connection", _forbidden)
        traces = dict(saved_calls=[], closed_requests=[], restored_processes=[], finishes=[], reclosures=[],
            archive_replacements=[], closed_units=[], builds=[])
        original_call, original_finish = DecisionSource.call, DecisionSource.finish
        original_closed, original_restore = WorkflowServices.scientific_closed_request, ScientificProcessEpisodes.restore_closed_process
        original_save, original_replace = Journal.save, os.replace
        original_commission, original_build = Workflow._closed_child_commission, Workflow.build

        async def call(source, context, schema):
            assert source.path[-1][0] == "annotation", "closed child must not consume its scientific decision cache"
            row = source.workflow.journal.row("runtime_model_calls", source.episode_id, source.calls)
            assert row is not None and row["response"] is not None
            answer = await original_call(source, context, schema)
            traces["saved_calls"].append(dict(episode_id=source.episode_id, role=source.path[-1][0], index=answer[1]))
            return answer

        async def finish(source, record):
            result = await original_finish(source, record)
            traces["finishes"].append(dict(episode_id=source.episode_id, role=source.path[-1][0], result=plain(result.as_record())))
            return result

        def closed(services, context):
            result = original_closed(services, context)
            traces["closed_requests"].append(dict(episode_id=context.episode_id, found=result is not None))
            return result

        def restore(binding, context):
            result = original_restore(binding, context)
            traces["restored_processes"].append(dict(episode_id=context.episode_id, restored=result is not None))
            return result

        def commission(flow, source, selection, index):
            traced = dict(parent_episode_id=source.episode_id, decision_index=index, returned=False)
            traces["closed_units"].append(traced)
            unit = original_commission(flow, source, selection, index)
            assert isinstance(unit, ReturnedActionUnit) and unit.decision_index == index == 0
            assert source.episode_id == episodes[0]["episode_id"] and unit.label == "child_0"
            assert unit.record.episode_id == episodes[1]["episode_id"] and unit.record.run_id == run_id
            assert canonical(unit.request.as_record()) == canonical(science_request)
            assert canonical(unit.record.request.as_record()) == canonical(science_request)
            assert plain(unit.result.as_record()) == dict(form=expected_form)
            child_record = json.loads("".join(iter_json(unit.record)))
            assert canonical(child_record) == canonical(expected_child_archive)
            assert unit.record.archived_record.descriptor() == json.loads(episodes[1]["archive"])
            assert source.last_outcome == original_parent_outcome and source.last_outcome_index == index
            traced.update(returned=True, child_episode_id=unit.record.episode_id,
                request_sha256=hashlib.sha256(canonical(unit.request.as_record()).encode("utf-8")).hexdigest(),
                result=plain(unit.result.as_record()),
                child_archive_sha256=hashlib.sha256(canonical(child_record).encode("utf-8")).hexdigest(),
                record_refs=deepcopy(source.last_outcome["record_refs"]))
            return unit

        def build(flow, name, key, *args, **kwargs):
            assert name != "scientific_process", "closed child must not reconstruct a scientific source"
            traces["builds"].append(dict(role=name, key=key))
            return original_build(flow, name, key, *args, **kwargs)

        def save(journal, table, values):
            before = journal.row(table, values["episode_id"]) if table == "runtime_episodes" else None
            result = original_save(journal, table, values)
            if before is not None:
                after = journal.row(table, values["episode_id"])
                assert dict(before) == dict(after)
                traces["reclosures"].append(dict(episode_id=values["episode_id"], state=after["state"], row_values_unchanged=True))
            return result

        def replace(source, target, *args, **kwargs):
            target_path = Path(target).absolute()
            assert not target_path.is_relative_to(directory) and not target_path.is_relative_to(original_run)
            if target_path.is_relative_to(owned_run / "archive"):
                traces["archive_replacements"].append(dict(file=str(target_path.relative_to(owned_run)),
                    existing_target=target_path.exists()))
            return original_replace(source, target, *args, **kwargs)

        monkeypatch.setattr(DecisionSource, "call", call)
        monkeypatch.setattr(DecisionSource, "finish", finish)
        monkeypatch.setattr(WorkflowServices, "scientific_closed_request", closed)
        monkeypatch.setattr(ScientificProcessEpisodes, "restore_closed_process", restore)
        monkeypatch.setattr(Workflow, "_closed_child_commission", commission)
        monkeypatch.setattr(Workflow, "build", build)
        monkeypatch.setattr(Journal, "save", save)
        monkeypatch.setattr(os, "replace", replace)
        tools = ToolRegistry(store, job_limits=deepcopy(POLICY))
        tools.configure_protein_structure_resources(resources, environments)
        provider = ScriptedProvider([])
        monkeypatch.setattr(provider, "complete", _forbidden)
        workflow = Workflow(store, tools, provider, owned_run, run_id, _controllers, _credit,
            project_child_credit=_credit, episode_binding_descriptors=descriptors,
            episode_record_receipts=True, initial_known_record_refs=inputs)
        assert _tables(store) == before_tables
        initial_changes = store.db.total_changes
        expected_parent_archive = workflow.archive_reference(json.loads(episodes[0]["archive"])).load()
        expected_child_archive = workflow.archive_reference(json.loads(episodes[1]["archive"])).load()
        parent_path = json.loads(episodes[0]["path"])
        role, key = parent_path[0]
        root = workflow.build(role, key, parent_request["goal"]["objective"], parent_request["message"]["scope"])
        record = asyncio.run(root.run_async(workflow.context))
        result = asyncio.run(root.build_result(record))
        assert plain(result.as_record()) == dict(credit=0, pending_handles=[])
        assert traces["finishes"] == [dict(episode_id=episodes[0]["episode_id"], role="annotation",
            result=dict(credit=0, pending_handles=[]))]
        assert traces["saved_calls"] == [dict(episode_id=episodes[0]["episode_id"], role="annotation", index=0)]
        assert traces["closed_requests"] and all(
            value == dict(episode_id=episodes[1]["episode_id"], found=True) for value in traces["closed_requests"])
        assert traces["restored_processes"] and all(
            value == dict(episode_id=episodes[1]["episode_id"], restored=True) for value in traces["restored_processes"])
        assert traces["builds"] == [dict(role=role, key=key)]
        assert len(traces["closed_units"]) == 1 and traces["closed_units"][0]["returned"] is True
        assert canonical(json.loads("".join(iter_json(record)))) == canonical(expected_parent_archive)
        known = set(workflow.receipts.known(root.source.episode_id))
        resolver = workflow.resolver(parent_request["message"]["scope"], source=root.source)
        assert all(row["record_ref"] in known and resolver(row["record_ref"], "artifact") is True
            for row in original_parent_file_receipts)
        assert [dict(row) for row in store.db.execute(
            "SELECT * FROM runtime_record_receipts WHERE episode_id=? ORDER BY receipt_index",
            (root.source.episode_id,)) if row["record_ref"].startswith("artifact_")] == original_parent_file_receipts
        assert provider.contexts == [] and traces["reclosures"] and traces["archive_replacements"]
        assert all(value["existing_target"] for value in traces["archive_replacements"])
        assert _tables(store) == before_tables
        assert _artifact_inventory(owned_run) == original_run_files
        changes = store.db.total_changes - initial_changes
        assert changes >= len(traces["reclosures"])
    finally:
        if store is not None:
            store.close()
        original.close()
    assert database.read_bytes() == original_database
    assert _artifact_inventory(directory / "artifacts") == original_artifacts
    assert _artifact_inventory(original_run) == original_run_files
    (tmp_path / "PROTEIN_STRUCTURE_CLOSED_WORKFLOW_REPLAY.json").write_text(json.dumps({
        "qualification": "fresh actual Workflow over an owned identical database and archive copy; original artifact paths preserved read-only",
        "original_store": str(directory), "original_database_sha256": hashlib.sha256(original_database).hexdigest(),
        "owned_database": str(owned_database), "owned_run": str(owned_run), "traces": traces,
        "same_value_SQL_changes": changes, "all_table_values_unchanged": True,
        "owned_archive_and_library_bytes_unchanged": True, "original_database_artifacts_and_run_unchanged": True,
        "parent_final_result": plain(result.as_record()), "scientific_final_form_matches_original": True,
        "closed_child_request_form_and_archive_match_original": True,
        "parent_archive_matches_original": True, "original_parent_file_receipts": original_parent_file_receipts,
        "original_parent_file_grants_preserved": True,
        "new_model_native_worker_or_observation_count": 0,
        "limits": "No relocated capsule recovery, new calculation, native timing receipt, numeric parent return or claim that the original342 testcase passed"
    }, indent=2) + "\n")
