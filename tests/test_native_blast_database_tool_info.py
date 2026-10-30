"""Information/commission contract checks, not an installed HPC route claim."""
from copy import deepcopy

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode import native_blast_database_contracts as c
from gene_annotation_episode.native_blast_database_tool_info import native_blast_database_tool_contracts
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from test_native_blast_database_contracts import job_for, forbid_io


def bindings():
    return [{"program": p, "mode": "database", "software": job_for(p)["software"],
        "database_manifests": [r["manifest_file"] for r in job_for(p)["databases"]]} for p in c.PROGRAMS]


def test_six_explicit_hpc_contracts_are_pure_actual_request_shapes(monkeypatch):
    selected = bindings()
    original = deepcopy(selected)
    with monkeypatch.context() as pure:
        forbid_io(pure)
        rows = native_blast_database_tool_contracts(selected, resource_kind="hpc", resource_id="selected-hpc")
    assert len(rows) == 6
    for row, binding in zip(rows, selected):
        assert set(row) == {"name", "description", "resources", "instructions", "input_schema", "invocation_route"}
        assert row["resources"] == "hpc" and row["name"] == "native." + binding["program"]
        assert row["invocation_route"] == {"kind": "commission", "routes": [{"entry_role": "launch", "resource_id": "selected-hpc", "resource_role": "launch_hpc"}]}
        request = c.requested_job_from_native_blast_database(job_for(binding["program"]))
        Draft202012Validator(row["input_schema"]).validate(request)
        request["native_blast_database"]["software"]["sha256"] = "f" * 64
        assert not Draft202012Validator(row["input_schema"]).is_valid(request)
        assert "practical.job.start" in row["instructions"]
        assert row["instructions"].endswith("and sheets remain retained separately from small typed returns.")
    rows[0]["input_schema"].clear()
    assert selected == original


def test_existing_library_freezes_and_resolves_substantive_child_tool_info(tmp_path):
    rows = native_blast_database_tool_contracts(bindings(), resource_kind="hpc", resource_id="explicit-hpc")
    library = ScientificToolLibrary.freeze(tmp_path / "library", catalog=[], tool_info=True, resource_catalogs={"hpc": rows})
    information = [{"name": r["name"], "resources": r["resources"]} for r in rows[:2]]
    child_tool_info = library.resolve_tool_info(information)
    assert all(set(row) == {"name", "description", "resources", "instructions"} for row in child_tool_info)
    assert len(child_tool_info) == 2
    assert library.resolve_invocations(information) == rows[:2]
    assert ScientificToolLibrary(tmp_path / "library").resolve_tool_info(information) == child_tool_info


@pytest.mark.parametrize("kind", ["local", "api", "pbs_ssh", None])
def test_non_hpc_not_advertised(kind):
    with pytest.raises(ValueError, match="explicit_hpc"):
        native_blast_database_tool_contracts(bindings(), resource_kind=kind, resource_id="chosen")


def test_binding_closed_unique_and_empty_means_no_advertised_tools():
    assert native_blast_database_tool_contracts([], resource_kind="hpc", resource_id="chosen") == []
    selected = bindings()
    for rows in ([selected[0], selected[0]], [{**selected[0], "install": True}], [{**selected[0], "database_manifests": []}]):
        with pytest.raises(ValueError):
            native_blast_database_tool_contracts(rows, resource_kind="hpc", resource_id="chosen")
