"""Serialize two declared synthetic matrices; not a chromatin analysis tool."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import sys

import h5py
import numpy as np


def pin(path):
    path = Path(path)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"path": str(path.resolve()), "sha256": digest.hexdigest(),
            "size_bytes": path.stat().st_size}


dependencies_path = Path(sys.argv[1])
dependencies = json.loads(dependencies_path.read_text())
assert Path(sys.executable) == Path(dependencies["python"]["executable"])
assert (h5py.__version__, np.__version__) == (
    dependencies["runtime"]["h5py_version"], dependencies["runtime"]["numpy_version"])
checked = 0
for record in ([dependencies["python"]] + dependencies["loaded_shared_library_files"] +
               [item for dist in dependencies["distributions"] for item in dist["files"]]):
    actual = pin(record["path"])
    assert actual["sha256"] == record["sha256"] and actual["size_bytes"] == record["size_bytes"]
    checked += 1

out = Path.cwd() / "fixtures"
out.mkdir(exist_ok=False)
declarations = [
    {"key": "four_bin_raw_weighted", "filename": "four-bin-raw-weighted.cool",
     "matrix": [[4, 2, 6, 0], [2, 4, 2, 2], [6, 2, 4, 2], [0, 2, 2, 4]],
     "weights": [1, 2, 1, 2], "explicit_zero": (0, 3)},
    {"key": "six_bin_all_full_windows", "filename": "six-bin-all-full-windows.cool",
     "matrix": [[0, 5, 0, 0, 0, 0], [5, 0, 1, 0, 0, 0], [0, 1, 0, 5, 0, 0],
                [0, 0, 5, 0, 1, 0], [0, 0, 0, 1, 0, 5], [0, 0, 0, 0, 5, 0]],
     "weights": None, "explicit_zero": (0, 0)},
]
receipts = []
for declaration in declarations:
    matrix = declaration["matrix"]
    n = len(matrix)
    pixels = [(i, j, matrix[i][j]) for i in range(n) for j in range(i, n)
              if matrix[i][j] != 0 or (i, j) == declaration["explicit_zero"]]
    offsets = [sum(i < current for i, _, _ in pixels) for current in range(n + 1)]
    path = out / declaration["filename"]
    with h5py.File(path, "x", libver="earliest", track_order=True) as container:
        container.attrs["format"] = "HDF5::Cooler"
        container.attrs["format-version"] = np.int64(3)
        container.attrs["bin-type"] = "fixed"
        container.attrs["bin-size"] = np.int64(10)
        container.attrs["storage-mode"] = "symmetric-upper"
        container.attrs["nchroms"] = np.int64(1)
        container.attrs["nbins"] = np.int64(n)
        container.attrs["nnz"] = np.int64(len(pixels))
        container.attrs["sum"] = np.int64(sum(value for _, _, value in pixels))
        container.attrs["generated-by"] = "packet440-h5py-synthetic-fixture/" + h5py.__version__
        container.attrs["creation-date"] = datetime.now(timezone.utc).isoformat()
        container.attrs["metadata"] = json.dumps({
            "origin": "synthetic", "biological_observation": False,
            "fixture_key": declaration["key"], "source_example": "packet439 section7",
            "normalization": "supplied synthetic multiplicative weights; no balancing executed"
                             if declaration["weights"] is not None else "raw; no weights supplied",
        }, sort_keys=True)
        for group in ("chroms", "bins", "pixels", "indexes"):
            container.create_group(group, track_order=True)

        def column(name, values, dtype):
            return container.create_dataset(name, data=np.asarray(values, dtype=dtype), dtype=dtype,
                compression="gzip", compression_opts=4, shuffle=True, track_times=False)

        column("chroms/name", [b"chrA"], "S4")
        column("chroms/length", [n * 10], "<i4")
        column("bins/chrom", [0] * n, h5py.enum_dtype({"chrA": 0}, basetype="<i4"))
        column("bins/start", list(range(0, n * 10, 10)), "<i4")
        column("bins/end", list(range(10, (n + 1) * 10, 10)), "<i4")
        if declaration["weights"] is not None:
            weights = column("bins/weight", declaration["weights"], "<f8")
            weights.attrs["fixture-meaning"] = "supplied synthetic multiplicative factors; not fitted weights"
        column("pixels/bin1_id", [row[0] for row in pixels], "<i8")
        column("pixels/bin2_id", [row[1] for row in pixels], "<i8")
        column("pixels/count", [row[2] for row in pixels], "<i4")
        column("indexes/chrom_offset", [0, n], "<i8")
        column("indexes/bin1_offset", offsets, "<i8")
    receipts.append({"fixture_key": declaration["key"], **pin(path), "group_path": "/",
                     "format": "HDF5::Cooler", "format_version": 3,
                     "origin": "synthetic", "biological_observation": False})
receipt = {"record_type": "actual_hdf5_synthetic_serialization_v1", "fixtures": receipts,
           "generator": pin(__file__), "dependency_manifest": pin(dependencies_path),
           "dependency_files_verified_before_generation": checked,
           "python_executable": sys.executable, "h5py_version": h5py.__version__,
           "numpy_version": np.__version__, "hdf5_version": h5py.version.hdf5_version,
           "pid": os.getpid(), "parent_pid": os.getppid(), "cooler_execution": False}
Path("GENERATION.json").write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
print(json.dumps({"generated": receipts, "verified_dependency_files": checked}))
