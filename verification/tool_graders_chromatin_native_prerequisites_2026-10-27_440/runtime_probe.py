"""Executed only inside the bounded native job; no scientific analysis."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import platform
import sys

import h5py
import numpy


def pin(path):
    path = Path(path)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"path": str(path.absolute()), "resolved_path": str(path.resolve()),
            "sha256": digest.hexdigest(), "size_bytes": path.stat().st_size}


def distribution(name, module):
    dist = importlib.metadata.distribution(name)
    existing, missing = [], []
    for entry in sorted(dist.files or [], key=str):
        path = Path(dist.locate_file(entry)).absolute()
        if path.is_file():
            existing.append({"distribution_relative_path": str(entry), **pin(path)})
        else:
            missing.append({"distribution_relative_path": str(entry), "path": str(path)})
    if missing:
        raise RuntimeError("installed_distribution_file_missing:" + name)
    return {"name": dist.metadata["Name"], "version": dist.version,
            "package_root": str(Path(module.__file__).parent),
            "imported_module_file": pin(module.__file__),
            "distribution_metadata_root": str(dist._path),
            "requirements": dist.requires or [], "files": existing,
            "file_count": len(existing), "missing_files": missing,
            "total_size_bytes": sum(item["size_bytes"] for item in existing)}


cgline = next(line for line in Path("/proc/self/cgroup").read_text().splitlines()
              if line.startswith("0::"))
cgroup = Path("/sys/fs/cgroup") / cgline[3:].lstrip("/")
limits = {name: (cgroup / name).read_text().strip()
          for name in ("memory.max", "memory.swap.max")}
assert limits == {"memory.max": "21474836480", "memory.swap.max": "0"}

# Native HDF5 library and NumPy operation availability, without fixture creation.
assert h5py.h5.get_libversion() == h5py.version.hdf5_version_tuple
assert numpy.array([1, 2, 3], dtype="<i8").sum().item() == 6
selected_distributions = [distribution("h5py", h5py), distribution("numpy", numpy)]
mapped_paths = sorted({line.split()[-1] for line in Path("/proc/self/maps").read_text().splitlines()
                       if len(line.split()) >= 6 and line.split()[-1].startswith("/")})
loaded_libraries = [pin(path) for path in mapped_paths
                    if ".so" in Path(path).name and Path(path).is_file()]
cooler_spec = importlib.util.find_spec("cooler")
cooler = {"module_available": cooler_spec is not None,
          "import_executed": False, "reader_executed": False}
if cooler_spec is not None:
    import cooler as cooler_module
    cooler.update(import_executed=True, version=cooler_module.__version__,
                  module_file=pin(cooler_module.__file__))

result = {
    "record_type": "chromatin_native_dependency_runtime_evidence_v1",
    "observed_at": datetime.now(timezone.utc).isoformat(),
    "selected_environment": str(Path(sys.prefix)),
    "python": {"executable": str(Path(sys.executable)), **pin(sys.executable),
               "version": sys.version, "version_info": list(sys.version_info),
               "implementation": platform.python_implementation(), "prefix": sys.prefix,
               "base_prefix": sys.base_prefix, "pyvenv_cfg": pin(Path(sys.prefix) / "pyvenv.cfg")},
    "distributions": selected_distributions,
    "loaded_shared_library_files": loaded_libraries,
    "runtime": {"numpy_version": numpy.__version__, "h5py_version": h5py.__version__,
                "hdf5_version": h5py.version.hdf5_version,
                "h5py_version_info": h5py.version.info,
                "numpy_integer_sum_verified": True, "hdf5_runtime_version_verified": True},
    "cooler": cooler,
    "process": {"pid": os.getpid(), "parent_pid": os.getppid(),
                "cgroup": str(cgroup), "observed_limits": limits},
    "installed_by_this_task": [],
    "production_implementation_file_pins": [],
    "freeze_scope": "Existing runtime distribution files and loaded shared libraries; no future implementation pins.",
}
Path("DEPENDENCIES.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
print(json.dumps({"python_version": platform.python_version(), "numpy": numpy.__version__,
                  "h5py": h5py.__version__, "hdf5": h5py.version.hdf5_version,
                  "cooler_available": cooler_spec is not None,
                  "distribution_file_counts": {item["name"]: item["file_count"] for item in selected_distributions},
                  "pid": os.getpid(), "cgroup_limits": limits}))
