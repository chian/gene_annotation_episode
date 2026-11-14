"""Authenticate the originally selected Python, source and dependency files."""
from __future__ import annotations
import importlib
import importlib.metadata
import os
from pathlib import Path
import platform
import sys
from .native_atac_differential_contracts import require, validate_driver_runtime
from .native_atac_file_records import confined_file, file_identity


def verify_driver_runtime(driver):
    """Verify the selected Python, implementation and dependency file closure."""
    driver = validate_driver_runtime(driver)
    selected = Path(driver["python_executable"]).resolve(strict=True)
    require(os.path.samefile(selected, "/proc/self/exe") and
        file_identity(selected)["sha256"] == driver["python_sha256"] and
        platform.python_version() == driver["python_version"], "native_dependency_unavailable")
    for row in driver["implementation_files"]:
        path = confined_file(driver["module_root"], row["module"].replace(".", "/") + ".py")
        require(file_identity(path)["sha256"] == row["sha256"], "native_dependency_unavailable")
        loaded = sys.modules.get(row["module"])
        if loaded is not None:
            require(Path(loaded.__file__) == path, "native_dependency_unavailable")
    module_names = {"rpds-py": "rpds", "jsonschema-specifications": "jsonschema_specifications", "attrs": "attr", "python-dateutil": "dateutil", "fair-esm": "esm"}
    for dependency in driver["dependencies"]:
        name = dependency["distribution"]
        require(importlib.metadata.version(name) == dependency["version"], "native_dependency_unavailable")
        module = importlib.import_module(module_names.get(name, name.replace("-", "_")))
        require(Path(module.__file__).parent == Path(dependency["package_root"]), "native_dependency_unavailable")
        for pin in dependency["files"]:
            require(file_identity(pin["path"]) == {k: pin[k] for k in ("sha256", "size_bytes")}, "native_dependency_unavailable")
    pinned = {p["path"] for row in driver["dependencies"] for p in row["files"]}
    for module in list(sys.modules.values()):
        filename = getattr(module, "__file__", None)
        if filename and "site-packages" in Path(filename).parts:
            require(str(Path(filename).resolve(strict=True)) in pinned, "native_dependency_unavailable")

