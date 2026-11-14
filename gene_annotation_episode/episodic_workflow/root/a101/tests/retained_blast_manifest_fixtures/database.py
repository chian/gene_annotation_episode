"""Original pure manifest fixtures: synthetic descriptors, never saved history."""
from copy import deepcopy
import builtins
import os
from pathlib import Path
import socket
import subprocess
import pytest
from gene_annotation_episode.episodic_workflow.root.a101.library import native_blast_database_contracts as c

def forbid_io(monkeypatch):
    def fail(*a, **kw):
        pytest.fail("pure contract attempted I/O, process or network")
    for obj, name in ((builtins, "open"), (Path, "open"), (Path, "resolve"), (os, "stat"), (os, "listdir"),
                      (subprocess, "run"), (subprocess, "Popen"), (socket, "socket"), (socket, "getaddrinfo")):
        monkeypatch.setattr(obj, name, fail)

def manifest_for():
    return {"version": "native_blast_database_producer_manifest_v1", "module_root": "/deploy",
        "entry_module": "gene_annotation_episode.episodic_workflow.root.a101.native_blast_database_driver",
        "python": {"path": "/runtime/python", "sha256": "a" * 64, "size_bytes": 23},
        "package_files": [{"relative_path": "gene_annotation_episode/" + n, "sha256": "b" * 64, "size_bytes": 10}
            for n in ("__init__.py", "native_blast_database_contracts.py", "native_blast_database_driver.py")],
        "runtime_files": [{"path": "/runtime/lib", "sha256": "c" * 64, "size_bytes": 10}]}

def test_producer_manifest_is_pure_defensive_and_closed(monkeypatch):
    manifest = manifest_for()
    forbid_io(monkeypatch)
    result = c.validate_native_blast_database_producer_manifest(manifest, module_root="/deploy", python_executable="/runtime/python")
    result["python"]["size_bytes"] = 99
    assert manifest["python"]["size_bytes"] == 23
    for change in (lambda m: m["package_files"].pop(), lambda m: m["package_files"].append(m["package_files"][0]),
        lambda m: m["package_files"][0].update(relative_path="../escape"),
        lambda m: m["runtime_files"][0].update(path="/deploy/extra"),
        lambda m: m["runtime_files"][0].update(path="/runtime/python"), lambda m: m.update(extra=True),
        lambda m: m["python"].update(size_bytes=True), lambda m: m.update(module_root="/different")):
        bad = deepcopy(manifest)
        change(bad)
        with pytest.raises(ValueError):
            c.validate_native_blast_database_producer_manifest(bad, module_root="/deploy", python_executable="/runtime/python")
