"""One real import-only preparation and labelled metadata failure cases."""
import importlib.util
import json
import os
from pathlib import Path

import pytest

from gene_annotation_episode.native_flux_balance_contracts import validate_flux_balance_software
from gene_annotation_episode.native_flux_balance_storage import file_pin, read_json

ATTEMPT = Path(os.environ["HMMER529_ATTEMPT"]) if "HMMER529_ATTEMPT" in os.environ else None
pytestmark = pytest.mark.skipif(ATTEMPT is None, reason="requires bounded529")
HELPER = Path(__file__).resolve().parents[1] / "verification/tool_graders_flux_balance_selected_software_2026-10-29_714/prepare_software.py"
spec = importlib.util.spec_from_file_location("selected_software714", HELPER)
preparation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preparation)


def test_actual_current_producer_software_is_importable_without_science():
    destination = ATTEMPT / "prepared-software"
    receipt = preparation.prepare_selected_flux_balance_software(
        source_root=ATTEMPT / "source_snapshot", basis_attempt=ATTEMPT, destination=destination)
    assert receipt["ready"], receipt
    assert receipt["failures"] == []
    assert receipt["model_load_calls"] == receipt["model_optimize_calls"] == 0
    assert receipt["software_file"] == file_pin(destination / "software.json")
    software = validate_flux_balance_software(read_json(destination / "software.json"))
    paths = {row["path"] for row in software["implementation_files"]}
    assert str(destination / "modules/gene_annotation_episode/communication.py") in paths
    assert str(destination / "modules/gene_annotation_episode/launch_instructions.py") in paths
    assert len(paths) > 900
    probe = read_json(destination / "import-probe.json")
    assert probe["ready"] and probe["failure"] is None
    assert any(path.startswith(str(destination / "modules/gene_annotation_episode/"))
        for path in probe["imported_files"])
    assert probe["model_load_calls"] == probe["model_optimize_calls"] == 0
    assert read_json(destination / "preparation-receipt.json") == receipt


def _metadata_basis(tmp_path):
    """Synthetic source/pin metadata only; it must never reach an import probe."""
    basis = tmp_path / "metadata-basis"
    basis.mkdir()
    source = basis / "source_snapshot"
    package = source / "gene_annotation_episode"
    package.mkdir(parents=True)
    rows = []
    for name in sorted(preparation.REQUIRED):
        path = package / name
        path.write_text("# synthetic pin-validation fixture; no scientific implementation\n")
        rows.append(file_pin(path))
    documents = {"selected_request.json": {}, "source_pins_before.json": rows,
        "stdlib_pins_before.json": [], "dependency_pins_before.json": [],
        "binary_pins_before.json": [], "native_library_pins_before.json": []}
    for name, value in documents.items():
        (basis / name).write_text(json.dumps(value))
    return basis, source, rows


def test_changed_declared_source_retains_failure_without_descriptor(tmp_path, monkeypatch):
    basis, source, rows = _metadata_basis(tmp_path)
    Path(rows[0]["path"]).write_text("# changed metadata fixture\n")
    monkeypatch.setattr(preparation.subprocess, "run", lambda *a, **k: pytest.fail("unexpected probe"))
    destination = tmp_path / "changed"
    receipt = preparation.prepare_selected_flux_balance_software(
        source_root=source, basis_attempt=basis, destination=destination)
    assert receipt["ready"] is False and receipt["software_file"] is None
    assert receipt["failures"][0]["code"] == "selected_file_unavailable_or_changed"
    assert not (destination / "software.json").exists()
    rows = read_json(destination / "source-verification.json")
    assert rows[0]["state"] == "changed" and rows[0]["selected"] != rows[0]["observed"]


def test_missing_declared_source_remains_unavailable(tmp_path, monkeypatch):
    basis, source, rows = _metadata_basis(tmp_path)
    Path(rows[0]["path"]).unlink()
    monkeypatch.setattr(preparation.subprocess, "run", lambda *a, **k: pytest.fail("unexpected probe"))
    destination = tmp_path / "missing"
    receipt = preparation.prepare_selected_flux_balance_software(
        source_root=source, basis_attempt=basis, destination=destination)
    assert receipt["ready"] is False and receipt["software_file"] is None
    observed = read_json(destination / "source-verification.json")
    assert observed[0]["state"] == "unavailable" and observed[0]["observed"] is None
    assert not (destination / "software.json").exists()


def test_existing_destination_is_not_modified(tmp_path):
    destination = tmp_path / "existing"
    destination.mkdir()
    marker = destination / "original"
    marker.write_bytes(b"preserved")
    with pytest.raises(FileExistsError):
        preparation.prepare_selected_flux_balance_software(
            source_root=tmp_path, basis_attempt=tmp_path, destination=destination)
    assert list(destination.iterdir()) == [marker]
    assert marker.read_bytes() == b"preserved"


def test_source_pin_outside_declared_basis_is_not_admitted(tmp_path, monkeypatch):
    basis, source, rows = _metadata_basis(tmp_path)
    rows[0]["path"] = str(tmp_path / "unrelated-source.py")
    (basis / "source_pins_before.json").write_text(json.dumps(rows))
    monkeypatch.setattr(preparation.subprocess, "run", lambda *a, **k: pytest.fail("unexpected probe"))
    destination = tmp_path / "foreign"
    receipt = preparation.prepare_selected_flux_balance_software(
        source_root=source, basis_attempt=basis, destination=destination)
    assert receipt["ready"] is False
    assert receipt["failures"][0]["code"] == "source_pin_outside_basis"
    assert not (destination / "software.json").exists()
