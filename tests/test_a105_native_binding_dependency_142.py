"""Bounded dependency compatibility; all scientific inputs here are synthetic.

Historical records are written by the untouched original runtime in a subprocess,
not by relabeling current records or replacing dependency-check functions.
"""
import ast
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from gene_annotation_episode.domain import ContractError, canonical
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.literature_binding_interaction_storage import (
    COMPONENTS, LiteratureBindingInteractionRepository, _dependencies,
    _ORIGINAL_DEPENDENCIES,
    _PREVIOUS_DEPENDENCIES,
    _PRE_CONNECTION_DEPENDENCIES,
)
from gene_annotation_episode.state import Store
from test_literature_binding_interaction_storage import setup, project
from test_literature_rate_episode_integration import service_binding


ROOT = Path(__file__).resolve().parents[1]
PIN = ROOT / "verification/literature_reference_evidence_2026-10-25_001/a105_visual_signal_repository_071/pin_004"
PREVIOUS_PIN = ROOT / "verification/literature_reference_evidence_2026-10-25_001/a105_primary_active_site_review_151/pin_001"


def test_original_dependency_snapshot_matches_untouched_historical_files():
    hashes = _ORIGINAL_DEPENDENCIES["sha256"]
    assert len(hashes) == 9
    assert {name: hashlib.sha256((PIN / "gene_annotation_episode" / name).read_bytes()).hexdigest()
            for name in hashes} == hashes
    tree = ast.parse((PIN / "gene_annotation_episode/literature_binding_interaction_validation.py").read_text())
    version = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "VERSION" for target in node.targets))
    assert version == _ORIGINAL_DEPENDENCIES["validation_version"]
    assert _dependencies(_ORIGINAL_DEPENDENCIES) == _dependencies()


def test_previous_dependency_snapshot_matches_untouched_prechange_files():
    assert {name: hashlib.sha256((PREVIOUS_PIN / 'gene_annotation_episode' / name).read_bytes()).hexdigest()
        for name in _PREVIOUS_DEPENDENCIES['sha256']} == _PREVIOUS_DEPENDENCIES['sha256']
    assert _dependencies(_PREVIOUS_DEPENDENCIES) == _dependencies()


def test_whole_supported_maps_do_not_authorize_mixed_snapshots():
    snapshots = [_ORIGINAL_DEPENDENCIES, _PREVIOUS_DEPENDENCIES, _PRE_CONNECTION_DEPENDENCIES, _dependencies()]
    for left in snapshots:
        for right in snapshots:
            if left == right:
                continue
            for field in ('literature_rate_storage.py', 'literature_binding_interaction_storage.py'):
                mixed = deepcopy(left)
                mixed['sha256'][field] = right['sha256'][field]
                with pytest.raises(ContractError, match='implementation_dependency_mismatch'):
                    _dependencies(mixed)


def test_binding_custody_methods_unchanged_and_rate_only_differences_explicit():
    def methods(path, cls):
        tree = ast.parse(path.read_text())
        body = next(node.body for node in tree.body if isinstance(node, ast.ClassDef) and node.name == cls)
        return {node.name: ast.dump(node, include_attributes=False) for node in body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    name = "literature_rate_storage.py"
    original = methods(PIN / "gene_annotation_episode" / name, "LiteratureRateRepository")
    current = methods(ROOT / "gene_annotation_episode" / name, "LiteratureRateRepository")
    overrides = methods(ROOT / "gene_annotation_episode/literature_binding_interaction_storage.py",
                        "LiteratureBindingInteractionRepository")
    changed = {name for name in original if current.get(name) != original[name]}
    assert changed == {"populate_native", "_validate_native_saved", "read", "_runtime_delivery_cells"}
    # Native binding overrides population, read and projection. It does not use
    # the rate-specific changes or the optional assay/quantity read-version hook.
    assert {"populate", "read", "project_cells"}.issubset(overrides)
    for name in set(original) - changed - set(overrides):
        assert original[name] == current[name], name
    assert set(current) - set(original) == {"source_domain_projection"}


def test_preconnection_writer_is_retained_as_one_exact_historical_map():
    assert _dependencies(_PRE_CONNECTION_DEPENDENCIES) == _dependencies()
    altered = deepcopy(_PRE_CONNECTION_DEPENDENCIES)
    altered['sha256']['literature_rate_storage.py'] = _dependencies()['sha256']['literature_rate_storage.py']
    with pytest.raises(ContractError, match='implementation_dependency_mismatch'):
        _dependencies(altered)


@pytest.mark.parametrize("change", ["null", "empty", "unknown_rate", "old_writer_current_rate",
    "unknown_writer", "unknown_validator", "missing_hash", "extra_hash", "changed_calculator"])
def test_unknown_or_mixed_saved_versions_are_rejected(change):
    saved = deepcopy(_ORIGINAL_DEPENDENCIES)
    if change == "null": saved = None
    elif change == "empty": saved = {}
    elif change == "unknown_rate": saved["sha256"]["literature_rate_storage.py"] = "0" * 64
    elif change == "old_writer_current_rate":
        saved["sha256"]["literature_rate_storage.py"] = _dependencies()["sha256"]["literature_rate_storage.py"]
    elif change == "unknown_writer": saved["sha256"]["literature_binding_interaction_storage.py"] = "0" * 64
    elif change == "unknown_validator": saved["validation_version"] = "unknown"
    elif change == "missing_hash": del saved["sha256"]["literature_binding_reader.py"]
    elif change == "extra_hash": saved["sha256"]["unreviewed.py"] = "0" * 64
    else: saved["sha256"]["literature_binding_interaction_calculations.py"] = "0" * 64
    with pytest.raises(ContractError, match="implementation_dependency_mismatch"):
        _dependencies(saved)


@pytest.mark.parametrize("changed_file", ["literature_rate_storage.py", "literature_binding_interaction_calculations.py"])
def test_unknown_actual_dependency_bytes_reject_before_publication(tmp_path, changed_file):
    package = tmp_path / "dependency_copy"
    package.mkdir()
    for name in _dependencies()["sha256"]:
        (package / name).write_bytes((ROOT / "gene_annotation_episode" / name).read_bytes())
    with (package / changed_file).open("ab") as stream:
        stream.write(b"\n# Deliberately unknown dependency version for rejection test.\n")
    module_path = package / "literature_binding_interaction_storage.py"
    spec = importlib.util.spec_from_file_location("gene_annotation_episode._dependency_rejection_142", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    store, context, args = setup(tmp_path / "state")
    with store:
        repo = module.LiteratureBindingInteractionRepository(store, context.run_id)
        with pytest.raises(ContractError, match="implementation_dependency_mismatch"):
            repo.populate(context, args, "unknown-implementation")
        assert store.db.execute("SELECT count(*) FROM literature_binding_interaction_operations").fetchone()[0] == 0
        assert not [row for row in store.list("source") if row.get("provider") == module.PROVIDER]


def test_current_native_cells_record_actual_dependency_and_keep_subset_custody(tmp_path):
    store, context, args = setup(tmp_path)
    with store:
        repo = LiteratureBindingInteractionRepository(store, context.run_id)
        outcome = repo.populate(context, args, "current")
        saved = repo.read(outcome["result"]["sheet_ref"])
        assert saved["implementation_dependencies"] == _dependencies()
        rows = project(repo, outcome)
        assert [row["component"] for row in rows] == list(COMPONENTS)
        assert [row["value"] for row in rows[:7]] == [5, 40, 2, 4, 8, 2, 4]
        owner = replace(context, received_record_refs=(*context.received_record_refs, *outcome["record_refs"]))
        parent = replace(owner, episode_id="parent")
        repo.receive_cells(parent, [rows[6]], "manual-admission")
        assert repo.fact_cells(parent, [outcome["result"]["sheet_ref"]], components=COMPONENTS) == [rows[6]]
        assert repo.populate(context, args, "current") == outcome
        assert not store.list("observation") and not store.list("assessment")


@pytest.mark.parametrize('snapshot', ['original140', 'previous142'])
def test_untouched_historical_runtime_output_and_actual_typed_receipt_reopen_cold(tmp_path, monkeypatch, snapshot):
    selected_pin, expected_dependencies = ((PIN, _ORIGINAL_DEPENDENCIES) if snapshot == 'original140'
        else (PREVIOUS_PIN, _PREVIOUS_DEPENDENCIES))
    script = """
import hashlib, json, pathlib, sys
pin, tests, destination = map(pathlib.Path, sys.argv[1:4])
expected_rate_hash = sys.argv[4]
sys.path[:0] = [str(pin), str(tests)]
import pytest
import gene_annotation_episode.literature_binding_interaction_storage as native
import gene_annotation_episode.literature_rate_storage as rate
from gene_annotation_episode.literature_binding_interaction_storage import _dependencies
from test_literature_binding_interaction_integration import test_actual_c4_admission_rollback_original_receipt_tamper_and_read_only_reopen
assert pathlib.Path(native.__file__).parent == pin / 'gene_annotation_episode'
assert pathlib.Path(rate.__file__).parent == pin / 'gene_annotation_episode'
assert _dependencies()['sha256']['literature_rate_storage.py'] == expected_rate_hash
with pytest.MonkeyPatch.context() as patch:
    test_actual_c4_admission_rollback_original_receipt_tamper_and_read_only_reopen(destination, patch)
print(json.dumps({'status':'historical_original_runtime_c4_passed','native_module':native.__file__,
    'rate_module':rate.__file__, 'harness':str(tests / 'test_literature_binding_interaction_integration.py'),
    'dependencies':_dependencies()}, sort_keys=True))
"""
    result = subprocess.run([sys.executable, "-c", script, str(selected_pin), str(ROOT / "tests"), str(tmp_path),
        expected_dependencies['sha256']['literature_rate_storage.py']],
        cwd=selected_pin, capture_output=True, text=True, timeout=180)
    (tmp_path / "historical_stdout.log").write_text(result.stdout)
    (tmp_path / "historical_stderr.log").write_text(result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    proof = json.loads(result.stdout)
    assert proof["dependencies"] == expected_dependencies
    path = tmp_path / "state"
    store = Store.__new__(Store)
    store.path, store._savepoint = path.resolve(), 0
    store.db = sqlite3.connect((path / "state.sqlite3").resolve().as_uri() + "?mode=ro", uri=True, isolation_level=None)
    store.db.row_factory = sqlite3.Row
    try:
        before = list(store.db.iterdump())
        operation = store.db.execute("SELECT * FROM literature_binding_interaction_operations").fetchone()
        outcome = json.loads(operation["outcome"])
        attempt = store.db.execute("SELECT * FROM runtime_report_attempts WHERE failure IS NULL").fetchone()
        form = json.loads(attempt["form"])
        child_row = store.db.execute("SELECT * FROM runtime_episodes WHERE episode_id=?", (attempt["child_episode_id"],)).fetchone()
        child_request = json.loads(child_row["request"])
        original = store.get(outcome["result"]["sheet_ref"])
        original_saved_bytes = store.get_artifact(original["artifact_ref"])
        original_saved = json.loads(original_saved_bytes)
        source_artifacts = {store.get(ref)["artifact_ref"] for ref in original_saved["input_source_refs"]}
        references = tuple(dict.fromkeys([*original_saved["input_source_refs"], *outcome["record_refs"]]))
        child = BindingContext(operation["run_id"], attempt["child_episode_id"], "literature",
            tuple(tuple(part) for part in json.loads(child_row["path"])), child_request["message"]["scope"],
            child_request["message"]["episode_assignment"], child_request, references)
        parent = replace(child, episode_id=attempt["parent_episode_id"], role="annotation",
                         path=(("annotation", "root"),), assignment={})
        get = store.get_artifact
        def saved_only(reference):
            assert reference not in source_artifacts, "cold read accessed experimental bytes"
            return get(reference)
        def forbidden(*_args, **_kwargs):
            raise AssertionError("cold read must not parse, calculate, decode or receive again")
        monkeypatch.setattr(store, "get_artifact", saved_only)
        monkeypatch.setattr("gene_annotation_episode.literature_binding_interaction_storage.read_binding_interaction_inputs", forbidden)
        monkeypatch.setattr("gene_annotation_episode.literature_binding_interaction_storage.populate_binding_interaction", forbidden)
        monkeypatch.setattr("PIL.Image.open", forbidden)
        repo = LiteratureBindingInteractionRepository(store, operation["run_id"])
        monkeypatch.setattr(repo, "receive_cells", forbidden)
        saved = repo.read(original["id"])
        assert saved == original_saved
        assert canonical(saved["implementation_dependencies"]) == canonical(expected_dependencies)
        assert get(original["artifact_ref"]) == original_saved_bytes
        assert repo.populate(child, saved["selection"], operation["operation_key"]) == outcome
        assert repo.received_cells(parent) == form["numbers"]
        assert repo.fact_cells(parent, [original["id"]], components=COMPONENTS) == form["numbers"]
        assert [row["component"] for row in form["numbers"]] == ["interaction_ratio"]
        assert form["numbers"][0]["value"] == 4
        _, binding = service_binding(store, child)
        assert binding.received_report_facts(parent)["literature_binding_interaction_cells"] == form["numbers"]
        assert list(store.db.iterdump()) == before
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0
    finally:
        store.db.close()
