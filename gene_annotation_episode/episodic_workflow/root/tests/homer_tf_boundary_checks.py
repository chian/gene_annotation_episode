"""Engineered controls for one ordinary HOMER reservation; no native science.

The deployment/handle/status records below are explicit protocol test doubles.
Received input bytes are the reusable 428 input fixture, never native results.
No test invokes a Perl helper, HOMER binary, scientific worker or systemd unit.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from threading import Event
from types import SimpleNamespace
import zipfile

import pytest

from gene_annotation_episode.episodic_workflow.root.library import native_homer_execution as e
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
from gene_annotation_episode.local_jobs import LocalJobPolicy, LocalJobResult
from gene_annotation_episode.molecular_measurement_tools import MolecularOperationUnpublished


def _write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(e._bytes(value))


def _pin(path):
    path = Path(path)
    return e._raw_pin(path, path.read_bytes())


def _copy_call(call):
    # BindingContext intentionally contains immutable mapping proxies.
    return {**call, **{key: deepcopy(call[key]) for key in ("arguments", "frozen_inputs", "selected")}}


def make_selected_call(tmp_path, monkeypatch, *, current=False, inventory_kind=None):
    """Actual immutable controls, with an explicitly non-executable runtime."""
    workspace, assets, software_root = (tmp_path / n for n in ("workspace", "assets", "software"))
    for directory in (workspace, assets, software_root): directory.mkdir()
    required = [*("deployment/bin/" + n for n in (*e.PATCH_NAMES, "homerTools", "homer2", "mergePeaks", "HomerSVGLogo.pm")),
        "deployment/config.txt", "selected_runtime/perl/bin/perl", "selected_runtime/elf/ld-linux-x86-64.so.2",
        "deployment/data/knownTFs/all/known.motifs", "deployment/data/knownTFs/vertebrates/known.motifs"]
    files = []
    for relative in required:
        path = assets / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(("engineered identity only, never executed: " + relative + "\n").encode())
        path.chmod(0o444)
        pin = _pin(path)
        files.append(dict(relative_path=relative, sha256=pin["sha256"], size_bytes=pin["size_bytes"], mode=0o444))
    correction = assets / "engineered-correction.json"
    _write(correction, dict(engineering_only=True, native_execution=False))
    python = software_root / "engineering-python"
    python.write_bytes(b"engineering placeholder; must never execute\n")
    library = Path(e.__file__).absolute().parent
    root, package = library.parent, library.parents[2]
    kind = ("current" if current else "original") if inventory_kind is None else inventory_kind
    assert kind in ("current", "original")
    if kind == "original":
        implementation = [package / "native_homer_execution.py", package / "native_homer_worker.py"]
    else:
        # Genuine private entry/byte-custody providers, not fabricated pins.
        # This explicit fixture inventory is independent of the producer's set.
        implementation = [library / "native_homer_worker.py", library / "native_homer_execution.py",
            library / "retained_file_pin.py", library / "retained_file_read.py", library / "native_artifact_storage.py",
            library / "record_serialization.py",
            root / "receiving_context.py", root / "communication.py",
            *(package / name for name in ("domain.py", "native_file_capture.py", "native_file_identity.py", "molecular_measurement_tools.py",
                "local_jobs.py", "execution_contracts.py", "acquisition.py", "native_lifecycle.py")),
            library / "__init__.py", root / "__init__.py", package / "episodic_workflow/__init__.py", package / "__init__.py"]
    inventory = software_root / "software-files.json"
    _write(inventory, dict(version="homer_native_software_files_v1", files=[_pin(python), *(_pin(p) for p in implementation)]))
    software = dict(version="root_homer_native_software_v1" if current else "homer_native_software_v1", python=_pin(python), python_home=str(software_root),
        python_version="engineering identity; not an interpreter", import_roots=[str(package.parent)],
        software_files_file=_pin(inventory))
    deployment = dict(version="homer_native_deployment_v1", root=str(assets), files=files, system_files=[],
        corrections=dict(extractor_build_report=_pin(correction), svg_repair_record=_pin(correction)))
    binding = dict(version="homer_native_binding_v1", operation=e.OPERATION, variant=e.VARIANT,
        deployment=deployment, software=software, input_staging=dict(mode="verified_copy", max_total_bytes=1024 * 1024))
    frozen = []
    fixture = Path(__file__).resolve().parent / "fixtures/homer_v51_selected_region_inputs.zip"
    with zipfile.ZipFile(fixture) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        for row, fmt in zip(manifest["files"], ("bed", "fasta", "bed")):
            raw = archive.read(row["member"])
            assert hashlib.sha256(raw).hexdigest() == row["sha256"] and len(raw) == row["size_bytes"]
            path = tmp_path / "received" / row["member"]
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(raw)
            identity = dict(artifact_ref="artifact_" + row["sha256"], sha256=row["sha256"], size_bytes=len(raw), format=fmt)
            frozen.append(dict(role=row["role"], selection=dict(namespace="artifact", reference=identity["artifact_ref"]),
                file=identity, path=str(path)))
    context = BindingContext(run_id="engineered-homer-run", episode_id="engineered-science",
        role="scientific_process", path=(("scientific_process", "engineered-path"),),
        scope={"engineering": True}, assignment={"engineering": "one existing ordinary action"},
        request={"engineering": True}, received_record_refs=tuple(row["file"]["artifact_ref"] for row in frozen))
    call = dict(context=context, operation_key=context.run_id + ":" + context.episode_id + ":0",
        arguments=dict(window_bp=201, motif_lengths=[10, 8], num_motifs=0, threads=2, strand="forward",
            statistic="hypergeometric", normalization=dict(composition="cpg", oligo_length=2,
                max_iterations=37, neutral=True), motif_set="vertebrates"),
        frozen_inputs=dict(version="ordinary_homer_frozen_inputs_v1", inputs=frozen),
        selected=dict(resource_id="explicit-engineered-resource", binding_ordinal_0based=3,
            workspace=str(workspace), binding=binding, environment=deepcopy(e.ENVIRONMENT_SELECTION)),
        policy=LocalJobPolicy(**e.POLICY))
    calls = []

    def prepare(command, *, cwd, policy, handle_path, stdout_path, stderr_path, env):
        calls.append(dict(command=list(command), cwd=str(cwd), policy=policy.to_dict(), environment=deepcopy(env)))
        paths = {role: str(cwd / (".local-job-" + "1" * 32 + "." + role)) for role in e._NATIVE_PATHS}
        request = dict(command=list(command), cwd=str(cwd), file_bytes=policy.scratch_bytes,
            ready_path=paths["ready"], release_path=paths["release"], result_path=paths["result"], stdin_path=None, env=env)
        _write(paths["request"], request)
        Path(stdout_path).write_bytes(b""); Path(stderr_path).write_bytes(b"")
        body = dict(version=e.native.VERSION, unit="engineered-original-only.service", command=list(command), cwd=str(cwd),
            stdout=str(stdout_path), stderr=str(stderr_path), paths=paths, metadata=dict(policy=policy.to_dict(), engineering_only=True),
            stage="prepared", started_at=None, started_monotonic_ns=None, boot_id=None,
            request_sha256=_pin(paths["request"])["sha256"])
        _write(handle_path, body)
        return e.native.NativeJobHandle(Path(handle_path))

    monkeypatch.setattr(e.native, "prepare_job", prepare)
    for name in ("wait_job", "cancel", "release", "start_job", "run_blocking"):
        monkeypatch.setattr(e.native, name,
            lambda *a, _name=name, **k: pytest.fail("forbidden lifecycle operation: " + _name))
    return call, calls

