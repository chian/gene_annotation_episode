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

from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episodic_workflow.root.episode_journal import Journal
from gene_annotation_episode.episodic_workflow.root.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.episodic_workflow.root.episode_services import WorkflowServices
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.episodic_workflow.root.library.native_protein_structure_contracts import DRIVER_MODULE, POLICY, WORKER_MODULE
from gene_annotation_episode.episodic_workflow.root.protein_structure_action_records import (
    SAVED_SOURCE, SEQUENCE_SOURCE, VIEW_SOURCE, ProteinStructureActionRecords,
    frozen_protein_structure_action_facts, protein_structure_action_fact_sources,
    validate_frozen_protein_structure_action_return,
)
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_formats import parse_pdb_structure
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_sequences import extract_structure_sequence
from gene_annotation_episode.episodic_workflow.root.runtime import DecisionSource, Workflow
from gene_annotation_episode.episodic_workflow.root.scientific_process_episodes import ScientificProcessEpisodes
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.tool_registry import ToolRegistry
from test_runtime import FixtureController, ScriptedProvider
from test_scientific_process_runtime import Scenario, action


ROOT = Path(__file__).resolve().parents[4]
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
        monkeypatch.setattr("gene_annotation_episode.episodic_workflow.root.library.protein_structure_tools.run_cancellable_native", _forbidden)
        monkeypatch.setattr("gene_annotation_episode.episodic_workflow.root.library.protein_structure_tools.resolve_protein_structure_operands", _forbidden)
        monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", _forbidden)
        monkeypatch.setattr("gene_annotation_episode.native_lifecycle.start_prepared", _forbidden)
        monkeypatch.setattr("gene_annotation_episode.native_lifecycle.resume_start", _forbidden)
        monkeypatch.setattr("gene_annotation_episode.episodic_workflow.root.library.protein_structure_formats.parse_pdb_structure", _forbidden)
        monkeypatch.setattr("gene_annotation_episode.episodic_workflow.root.library.protein_structure_formats.parse_mmcif_structure", _forbidden)
        monkeypatch.setattr("gene_annotation_episode.episodic_workflow.root.library.protein_structure_calculations.calculate_protein_structure_components", _forbidden)
        monkeypatch.setattr("gene_annotation_episode.episodic_workflow.root.library.protein_structure_calculations.fit_ca_transform", _forbidden)
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
            frozen.setattr("gene_annotation_episode.episodic_workflow.root.library.protein_structure_result_views.project_protein_structure_results", _forbidden)
            frozen.setattr("gene_annotation_episode.episodic_workflow.root.protein_structure_action_records.project_protein_structure_action_views", _forbidden)
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


