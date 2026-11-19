"""Python-driver runtime controls; the temporary native files are never executed."""
import pytest

from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode import native_atac_differential_contracts as contracts
from gene_annotation_episode import native_atac_differential_software as software


def _write(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return path


def test_freezer_enforces_supplied_scratch_budget_before_copy(tmp_path, monkeypatch):
    source = tmp_path / "original"
    _write(source / "gene_annotation_episode/__init__.py", b"# package\n")
    _write(source / "gene_annotation_episode/fixture_driver.py", b"VALUE = 1\n")
    monkeypatch.setattr(software, "_dependency_bindings", lambda: pytest.fail("copy budget must fail first"))
    target = tmp_path / "snapshot"
    policy = LocalJobPolicy(memory_bytes=contracts.POLICY['memory_bytes'], scratch_bytes=1)
    with pytest.raises(AcquisitionError, match="local_job_resource_limit"):
        software.freeze_driver_runtime(module_root=str(source), snapshot_directory=str(target),
            driver_modules=("gene_annotation_episode.fixture_driver",), policy=policy)
    assert list(target.rglob("*.py")) == []
