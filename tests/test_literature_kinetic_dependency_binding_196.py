"""Generation-bound kinetics and authentic original-release reconstruction.

All sources are synthetic. The original-v2 states were selected with intact
archived production code before this repair, never relabelled from new results.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3

import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_kinetic_inputs import read_kinetic_inputs
from gene_annotation_episode.literature_kinetic_storage import LiteratureKineticRepository
from gene_annotation_episode.literature_kinetic_model_storage import LiteratureKineticModelRepository
from gene_annotation_episode.state import Store
from test_literature_kinetic_inputs import fixture
from test_literature_kinetic_storage import setup
from test_literature_kinetic_model_inputs import setup_model
from test_literature_kinetic_model_storage import populate


BASE = Path(__file__).resolve().parents[1] / "verification/literature_reference_evidence_2026-10-25_001/a105_kinetic_dependency_repair_196/authentic_v2"


def hashes(path):
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in path.rglob("*") if p.is_file()}


def readonly(path):
    # Do not run Store's writable initializer before enforcing SQLite RO.
    store = Store.__new__(Store)
    store.path, store._savepoint = path.resolve(), 0
    store.db = sqlite3.connect(f"file:{store.path / 'state.sqlite3'}?mode=ro&immutable=1", uri=True, isolation_level=None)
    store.db.row_factory = sqlite3.Row
    store.db.execute("PRAGMA query_only=ON")
    store.db.create_function("library_scope_record", 2, store._scope_filter_record)
    return store


def forbid_science(monkeypatch, store, allowed):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Saved facts must not parse, convert, calculate or reattest current code")
    for module, names in {
        "literature_kinetic_storage": ("read_kinetic_inputs", "populate_kinetic_contrast", "_dependencies"),
        "literature_kinetic_model_storage": ("read_kinetic_model", "populate_kinetic_contrast"),
        "literature_kinetic_inputs": ("read_kinetic_inputs", "_unit", "_number", "_normalize"),
        "literature_rate_native_inputs": ("_number",),
        "literature_kinetic_calculations": ("populate_kinetic_contrast",),
    }.items():
        for name in names:
            monkeypatch.setattr(f"gene_annotation_episode.{module}.{name}", forbidden)
    original_get = store.get_artifact
    def saved_only(reference):
        assert reference in allowed, "raw scientific source acquisition during saved read"
        return original_get(reference)
    monkeypatch.setattr(store, "get_artifact", saved_only)
    original_bytes = Path.read_bytes
    def no_code_reads(path):
        assert path.suffix != ".py", "current code consulted during saved reconstruction"
        return original_bytes(path)
    monkeypatch.setattr(Path, "read_bytes", no_code_reads)


def check_saved(path, snapshot, monkeypatch, *, model=False):
    before = hashes(path)
    with readonly(path) as store:
        context, parent = BindingContext(**snapshot["context"]), BindingContext(**snapshot["parent"])
        allowed = set()
        for row in store.list("source"):
            if row.get("provider") in ("literature.a105.kinetic_population", "literature.a105.kinetic_model_population"):
                allowed.update((row["artifact_ref"], row["request_ref"]))
        forbid_science(monkeypatch, store, allowed)
        repo = (LiteratureKineticModelRepository if model else LiteratureKineticRepository)(store, context.run_id)
        assert repo.read(snapshot["sheet_ref"]) == snapshot["saved"]
        request = json.loads(store.get_artifact(store.get(snapshot["sheet_ref"])["request_ref"]))
        assert repo.populate(context, snapshot["arguments"], request["operation_key"]) == snapshot["outcome"]
        assert repo.project_cells([snapshot["sheet_ref"]], permitted_record_refs=snapshot["outcome"]["record_refs"]) == snapshot["projected"]
        assert repo.received_cells(parent) == snapshot["admitted"]
        assert repo.fact_cells(parent, [snapshot["sheet_ref"]], components=repo.components) == snapshot["admitted"]
        with pytest.raises(ContractError, match="cell_not_received"):
            repo.validate_fact_values(parent, snapshot["projected"])
        if model:
            native = LiteratureKineticRepository(store, context.run_id).read(snapshot["native_sheet_ref"])
            assert native == snapshot["native_saved"]
            assert snapshot["saved"]["calculation"]["inputs"] == native["extraction"]["calculation_inputs"]
        assert store.db.total_changes == 0
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            store.db.execute("CREATE TABLE forbidden_write (x)")
    assert hashes(path) == before


@pytest.mark.parametrize("case", ["point", "censored", "missing_unit", "model"])
def test_authentic_original_v2_exact_readonly_reconstruction(tmp_path, monkeypatch, case):
    original = hashes(BASE)
    generated = json.loads((BASE / "FILES_001.json").read_text())
    assert all(original[name] == sha for name, sha in generated.items())
    snapshot = json.loads((BASE / f"{case}_SNAPSHOT.json").read_text())
    assert snapshot.get("native_saved", snapshot["saved"])["version"] == "literature_kinetic_population_record_v2"
    shutil.copytree(BASE / case, tmp_path / "state")
    check_saved(tmp_path / "state", snapshot, monkeypatch, model=case == "model")
    assert hashes(BASE) == original


@pytest.mark.parametrize("model", [False, True])
def test_prospective_v3_exact_readonly_reconstruction(tmp_path, monkeypatch, model):
    path = tmp_path / "state"
    if model:
        store, context, args, model_args, _, _ = setup_model(path)
        repo, owner, args, outcome, native = populate(store, context, args, model_args)
        native_saved = LiteratureKineticRepository(store, context.run_id).read(native["result"]["sheet_ref"])
    else:
        store, context, args = setup(path, kind="Km", unit="mM", n=".008", d=".002")
        repo = LiteratureKineticRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected-v3")
        owner = replace(context, received_record_refs=(*context.received_record_refs, *outcome["record_refs"]))
        native_saved = repo.read(outcome["result"]["sheet_ref"])
    assert native_saved["version"] == "literature_kinetic_population_record_v3"
    assert native_saved["extraction"]["version"] == "a105_kinetic_source_extraction_v3"
    assert native_saved["calculation"]["cells"]["numerator_parameter"]["value"] == (20 if model else 8)
    reference = outcome["result"]["sheet_ref"]
    projected = repo.project_cells([reference], permitted_record_refs=outcome["record_refs"])
    parent = replace(owner, episode_id="parent", role="annotation", path=(("annotation", "parent"),), assignment={})
    admitted = [projected[-1]]
    repo.receive_cells(parent, admitted, "trusted-current-admission")
    snapshot = {"context": context.__dict__ if not model else owner.__dict__, "parent": parent.__dict__,
                "arguments": args, "outcome": outcome, "sheet_ref": reference,
                "saved": repo.read(reference), "projected": projected, "admitted": admitted}
    if model:
        snapshot.update(native_saved=native_saved, native_sheet_ref=native["result"]["sheet_ref"])
    store.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    store.close()
    check_saved(path, snapshot, monkeypatch, model=model)


def test_discovery_does_not_install_optional_tables_on_readonly_state(tmp_path):
    store, context, _ = setup(tmp_path)
    store.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    store.close()
    before = hashes(tmp_path)
    with readonly(tmp_path) as restored:
        for factory in (LiteratureKineticRepository, LiteratureKineticModelRepository):
            repo = factory(restored, context.run_id)
            assert repo.received_cells(context) == []
            assert not repo._installed(repo.operations_table)
        assert restored.db.total_changes == 0
    assert hashes(tmp_path) == before


@pytest.mark.parametrize("mismatch", ["quote", "offset"])
def test_invalid_selected_witness_preserves_state_without_installation(tmp_path, mismatch):
    store, context, args = setup(tmp_path)
    with store:
        witness = args["numerator"]["subject"]["molecule"]
        if mismatch == "quote":
            witness["quote"] = "ProteinFixturX"
        else:
            witness["start"] += 1
            witness["end"] += 1
        repo = LiteratureKineticRepository(store, context.run_id)
        before = list(store.db.iterdump())
        with pytest.raises(ValueError):
            repo.populate(context, args, "invalid-source")
        assert list(store.db.iterdump()) == before
        assert not repo._installed(repo.operations_table)


@pytest.mark.parametrize("kind,unit,n,value", [("Km", "mM", ".008", 8), ("kcat", "s^-1", "2", 120), ("catalytic_efficiency", "M^-1s^-1", "1000000", 60)])
def test_bound_current_lexical_release_converts_actual_selected_units(tmp_path, kind, unit, n, value):
    store, context, args = setup(tmp_path, kind=kind, unit=unit, n=n, d="1")
    with store:
        saved = LiteratureKineticRepository(store, context.run_id).populate(context, args, "units")
        assert saved["result"]["cells"]["numerator_parameter"]["value"] == value


@pytest.mark.parametrize("token", ["-8", "18", "8e3", "between 8 and 9", "SD 8", "8/2"])
def test_called_scalar_contract_rejects_clipping_and_wrong_scientific_role(token):
    source, selection = fixture(n=token)
    number = selection["numerator"]["measurement"]["number"]
    number.update(witness=source.witness("8"), number_start=0, number_end=1)
    with pytest.raises(ExperimentalContractError):
        read_kinetic_inputs(selection, read_source=source.read)


@pytest.mark.parametrize("unit", ["M^-1</td><td>s^-1", "uM^-1min^-1/mg"])
def test_selected_compound_unit_cannot_cross_cells_or_omit_factor(unit):
    source, selection = fixture(unit=unit)
    if "/mg" in unit:
        selection["numerator"]["measurement"]["unit"] = source.witness("uM^-1min^-1")
    with pytest.raises(ExperimentalContractError):
        read_kinetic_inputs(selection, read_source=source.read)


def test_prospective_hash_guard_remains_active_for_called_lexical_source(tmp_path, monkeypatch):
    store, context, args = setup(tmp_path)
    before = list(store.db.iterdump())
    original = Path.read_bytes
    def changed(path):
        raw = original(path)
        return raw + b"\n# changed lexical implementation\n" if path.name == "literature_partner_source_fields.py" else raw
    monkeypatch.setattr(Path, "read_bytes", changed)
    with store, pytest.raises(ContractError, match="implementation_dependency_mismatch"):
        LiteratureKineticRepository(store, context.run_id).populate(context, args, "changed")
    # No result was committed. Check in a new connection because the context closed it.
    with readonly(tmp_path) as restored:
        assert list(restored.db.iterdump()) == before


@pytest.mark.parametrize("change", ["source_release", "validator", "generation", "original_storage"])
def test_saved_receipt_rejects_wrong_generation_without_current_code_io(change):
    from gene_annotation_episode.literature_kinetic_storage import _validate_dependency_receipt
    snapshot = json.loads((BASE / "point_SNAPSHOT.json").read_text())
    receipt = deepcopy(snapshot["saved"]["implementation_dependencies"])
    version = snapshot["saved"]["version"]
    if change == "source_release":
        receipt["sha256"]["literature_partner_source_fields.py"] = "0" * 64
    elif change == "validator":
        receipt["validation_version"] = "a105_kinetic_saved_validation_v3"
    elif change == "generation":
        version = "literature_kinetic_population_record_v3"
    else:
        receipt["sha256"]["literature_kinetic_storage.py"] = "0" * 64
    with pytest.raises(ContractError, match="saved_dependency_mismatch"):
        _validate_dependency_receipt(receipt, version)
