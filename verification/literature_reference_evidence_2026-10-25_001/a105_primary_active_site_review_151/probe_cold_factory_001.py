"""Reopen actual controlled runtime receipts through the saved-binding factory."""
from pathlib import Path
from types import SimpleNamespace
import json
import sys

HERE = Path(__file__).resolve().parent
PIN = HERE / "pin_001"
sys.dont_write_bytecode = True
sys.path[:0] = [str(PIN), str(PIN / "tests")]
import pytest
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.state import Store
from test_literature_active_site_integration import (
    test_controlled_child_population_parent_return_and_reconstruction_are_single_actions,
)


def main():
    directory = HERE / "cold_factory_001"
    if directory.exists():
        raise RuntimeError("Do not overwrite a retained runtime exercise")
    directory.mkdir()
    patch = pytest.MonkeyPatch()
    try:
        test_controlled_child_population_parent_return_and_reconstruction_are_single_actions(directory, patch)
    finally:
        patch.undo()
    descriptor, = json.loads((directory / "run/run.json").read_text())["episode_bindings"]
    assert descriptor["configuration"]["active_site_population"] is True
    with Store(directory / "state") as cold:
        run_id, episode_id, saved_cells = cold.db.execute(
            "SELECT run_id,episode_id,cells FROM literature_active_site_received").fetchone()
        cells = json.loads(saved_cells)
        sheet_ref = cells[0]["sheet_ref"]
        source_ref = cells[0]["evidence_source_ref"]
        original_artifact = cold.get(source_ref)["artifact_ref"]
        parent = BindingContext(run_id, episode_id, "annotation", (("annotation", episode_id),),
            cold.validate_scope(), {}, {}, [sheet_ref])
        original_get = cold.get_artifact
        calls = []
        def guarded(reference):
            assert reference != original_artifact, "No original source read is allowed during reconstruction"
            calls.append(reference)
            return original_get(reference)
        def forbidden(*args, **kwargs):
            raise AssertionError("No scientific reader may run during reconstruction")
        patch.setattr(cold, "get_artifact", guarded)
        patch.setattr("gene_annotation_episode.literature_active_site_storage.read_active_site_inputs", forbidden)
        cold.db.execute("PRAGMA query_only=ON")
        before = cold.db.total_changes
        original_observations = cold.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0]
        services = WorkflowServices(SimpleNamespace(store=cold, run_id=run_id))
        binding, = compose_episode_bindings(services, store=cold,
            journal=SimpleNamespace(store=cold, run_id=run_id), execution_backend=None,
            descriptors=[descriptor], job_episodes=None, resource_estimator=None,
            role_credit_bindings={}).bindings
        assert binding.as_record() == descriptor
        repo = binding._active_site_repository()
        assert repo.received_cells(parent) == cells
        assert repo.fact_cells(parent, [sheet_ref], components=list(repo.components)) == cells
        assert cold.db.total_changes == before
        assert cold.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == original_observations
        result = {"passed": True, "scope": "Controlled runtime, closed Store, actual saved-descriptor factory, query_only; no original-source bytes or reader re-execution",
            "requested_components": [row["component"] for row in cells],
            "configuration": descriptor["configuration"], "database_changes": cold.db.total_changes - before,
            "runtime_observations": original_observations, "saved_artifact_read_count": len(calls),
            "unrequested_cells_expanded": False, "actual_model_execution": False}
        (HERE / "ROOT_COLD_FACTORY_001.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result))
    patch.undo()


if __name__ == "__main__":
    main()
