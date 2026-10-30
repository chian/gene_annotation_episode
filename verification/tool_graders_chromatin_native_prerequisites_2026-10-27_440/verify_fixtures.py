"""Independent complete-array readback of the two packet440 native fixtures.

This verifier imports no generator or production chromatin reader/calculator.
Expected arrays are separately declared hand-worked synthetic input facts.
"""
from pathlib import Path
import hashlib
import importlib.util
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


def plain(value):
    if isinstance(value, np.ndarray):
        return plain(value.tolist())
    if isinstance(value, np.generic):
        return plain(value.item())
    if isinstance(value, bytes):
        return value.decode("ascii")
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {str(key): plain(item) for key, item in value.items()}
    return value


expected_path, generation_path = map(Path, sys.argv[1:])
expected_bytes = expected_path.read_bytes()
Path("EXPECTED_INPUTS.snapshot.json").write_bytes(expected_bytes)
expected = json.loads(expected_bytes)
generation = json.loads(generation_path.read_text())
assert expected["biological_observation"] is False
generated = {item["fixture_key"]: item for item in generation["fixtures"]}
assert len(generated) == len(generation["fixtures"]) == len(expected["fixtures"]) == 2
reports = []
for fixture in expected["fixtures"]:
    file_record = generated[fixture["key"]]
    path = Path(file_record["path"])
    before = pin(path)
    assert before["sha256"] == file_record["sha256"]
    assert before["size_bytes"] == file_record["size_bytes"]
    with path.open("rb") as signature_file:
        assert signature_file.read(8) == b"\x89HDF\r\n\x1a\n"
    arrays, attributes, array_metadata = {}, {}, {}
    with h5py.File(path, "r") as container:
        group = container[fixture["group_path"]]
        assert group.name == "/"
        assert set(group) == {"chroms", "bins", "pixels", "indexes"}
        for key in group.attrs:
            value = group.attrs[key]
            dtype = group.attrs.get_id(key).dtype
            string_info = h5py.check_string_dtype(dtype)
            entry = {"value": plain(value), "dtype": dtype.str}
            if string_info is not None:
                assert string_info.encoding == "utf-8" and string_info.length is None
                entry["string_encoding"] = string_info.encoding
                entry["string_length"] = string_info.length
            attributes[key] = entry
        required = {"format": "HDF5::Cooler", "format-version": 3, "bin-type": "fixed",
                    "bin-size": 10, "storage-mode": "symmetric-upper"}
        for key, value in required.items():
            assert attributes[key]["value"] == value
        for key in ("format-version", "bin-size", "nchroms", "nbins", "nnz", "sum"):
            assert isinstance(group.attrs[key], np.integer)
        metadata = json.loads(group.attrs["metadata"])
        assert metadata["origin"] == "synthetic" and metadata["biological_observation"] is False

        found_datasets = set()
        for group_key in ("chroms", "bins", "pixels", "indexes"):
            assert isinstance(group.get(group_key, getlink=True), h5py.HardLink)
            for name in group[group_key]:
                assert isinstance(group[group_key].get(name, getlink=True), h5py.HardLink)
                dataset_name = group_key + "/" + name
                found_datasets.add(dataset_name)
                dataset = group[dataset_name]
                assert isinstance(dataset, h5py.Dataset)
                assert not dataset.is_virtual and not dataset.external
                assert dataset.ndim == 1
                arrays[dataset_name] = dataset[()]  # Complete data, not a slice preview.
                definition = fixture["arrays"][dataset_name]
                assert dataset.dtype.str == definition["dtype"]
                assert dataset.shape == (len(definition["values"]),)
                assert plain(arrays[dataset_name]) == definition["values"]
                assert h5py.check_enum_dtype(dataset.dtype) == definition.get("enum")
                string_info = h5py.check_string_dtype(dataset.dtype)
                if dataset_name == "chroms/name":
                    assert string_info.encoding == "ascii" and string_info.length == 4
                    assert dataset.id.get_type().get_strpad() == h5py.h5t.STR_NULLPAD
                array_metadata[dataset_name] = {
                    "path": dataset.name, "shape": list(dataset.shape), "dtype": dataset.dtype.str,
                    "enum": h5py.check_enum_dtype(dataset.dtype),
                    "string_encoding": string_info.encoding if string_info else None,
                    "string_length": string_info.length if string_info else None,
                    "compression": dataset.compression, "compression_opts": dataset.compression_opts,
                    "shuffle": dataset.shuffle, "chunks": list(dataset.chunks) if dataset.chunks else None,
                    "values": plain(arrays[dataset_name]),
                    "attributes": {key: plain(value) for key, value in dataset.attrs.items()},
                    "virtual": dataset.is_virtual, "external_storage": list(dataset.external or []),
                }
        assert found_datasets == set(fixture["arrays"])
        n = fixture["bin_count"]
        assert group.attrs["nchroms"] == len(arrays["chroms/name"]) == 1
        assert group.attrs["nbins"] == len(arrays["bins/chrom"]) == n
        assert len(arrays["bins/start"]) == len(arrays["bins/end"]) == n
        assert arrays["chroms/length"].dtype == arrays["bins/start"].dtype == arrays["bins/end"].dtype
        chrom = arrays["bins/chrom"]
        starts, ends = arrays["bins/start"], arrays["bins/end"]
        assert np.all(chrom == 0)
        assert starts[0] == 0 and ends[-1] == fixture["chromosome_length_bp"]
        assert np.all(starts >= 0) and np.all(ends > starts)
        assert np.all(starts[1:] == ends[:-1])
        assert np.all(ends - starts == fixture["bin_size_bp"])

        chrom_offsets = arrays["indexes/chrom_offset"]
        offsets = arrays["indexes/bin1_offset"]
        bin1, bin2, count = (arrays["pixels/" + key] for key in ("bin1_id", "bin2_id", "count"))
        nnz = len(count)
        assert len(bin1) == len(bin2) == nnz == group.attrs["nnz"]
        assert np.all(np.isfinite(count)) and np.all(count >= 0)
        assert group.attrs["sum"] == sum(int(value) for value in count)
        assert np.all(bin1 >= 0) and np.all(bin2 < n) and np.all(bin1 <= bin2)
        coordinates = list(zip(plain(bin1), plain(bin2)))
        assert coordinates == sorted(set(coordinates))
        assert offsets.shape == (n + 1,) and offsets[0] == 0 and offsets[-1] == nnz
        assert np.all(np.diff(offsets) >= 0)
        assert chrom_offsets.shape == (2,) and chrom_offsets[0] == 0 and chrom_offsets[-1] == n
        assert np.all(np.diff(chrom_offsets) >= 0)
        for current in range(n):
            assert np.all(bin1[int(offsets[current]):int(offsets[current + 1])] == current)
            assert offsets[current] == np.searchsorted(bin1, current, side="left")
        for current in range(len(chrom_offsets) - 1):
            assert np.all(chrom[int(chrom_offsets[current]):int(chrom_offsets[current + 1])] == current)
        actual_pixels = [[int(i), int(j), int(value)] for i, j, value in zip(bin1, bin2, count)]
        assert actual_pixels == fixture["expected_stored_upper_pixels"]

        reconstructed = [[0 for _ in range(n)] for _ in range(n)]
        for i, j, value in actual_pixels:
            reconstructed[i][j] = value
            if i != j:
                reconstructed[j][i] = value
        assert reconstructed == fixture["raw_matrix"]
        explicit_zeros = [[i, j] for i, j, value in actual_pixels if value == 0]
        omitted = [[i, j] for i in range(n) for j in range(i, n) if (i, j) not in set(coordinates)]
        assert explicit_zeros == fixture["explicit_zero_upper_cells"]
        assert omitted == fixture["sparse_omitted_upper_cells"]
        assert all(reconstructed[i][j] == 0 for i, j in omitted)
        population = {
            "stored_rows": nnz, "unordered_cells_including_diagonal": n * (n + 1) // 2,
            "directed_cells": n * n, "explicit_zero_rows": len(explicit_zeros),
            "implicit_zero_unordered_cells": len(omitted),
            "implicit_zero_directed_cells": sum(1 if i == j else 2 for i, j in omitted),
        }
        assert population == fixture["synthetic_population_expectations"]
        if fixture["weights"] is None:
            assert "bins/weight" not in arrays
        else:
            assert plain(arrays["bins/weight"]) == fixture["weights"]
            assert np.all(np.isfinite(arrays["bins/weight"])) and np.all(arrays["bins/weight"] > 0)
    assert pin(path) == before
    reports.append({
        "fixture_key": fixture["key"], **before, "group_path": fixture["group_path"],
        "native_format": "HDF5::Cooler", "format_version": 3,
        "origin": "synthetic", "biological_observation": False,
        "root_attributes": attributes, "complete_arrays": array_metadata,
        "reconstructed_raw_matrix": reconstructed, "weights": fixture["weights"],
        "weight_convention": fixture["weight_convention"], "stored_pixels": actual_pixels,
        "explicit_zero_upper_cells": explicit_zeros, "sparse_omitted_upper_cells": omitted,
        "population_counts": population, "file_unchanged_by_readback": True,
        "qualification": fixture["qualification"],
        "verified_invariants": ["complete_array_values_and_dtypes", "required_schema3_attributes",
            "variable_length_utf8_scalar_attributes", "ascii_null_padded_chromosome_names",
            "enum_chromosome_foreign_keys", "fixed_zero_based_half_open_bins",
            "equal_column_lengths", "pixel_upper_triangle_sort_and_unique_coordinates",
            "complete_monotonic_exact_csr_indexes", "no_external_links_or_virtual_or_external_storage",
            "expected_full_symmetric_matrix", "explicit_zero_distinct_from_sparse_omission",
            "exact_supplied_weight_vector_or_explicit_absence"],
    })

cooler_check = {"available": importlib.util.find_spec("cooler") is not None,
                "reader_executed": False, "agreement_verified": False,
                "reason": "Cooler is not installed in the selected environment."}
if cooler_check["available"]:
    import cooler
    cooler_check.update(reader_executed=True, version=cooler.__version__,
                        module_file=pin(cooler.__file__), reason=None)
    for fixture, report in zip(expected["fixtures"], reports):
        reader = cooler.Cooler(report["path"] + "::/")
        assert reader.matrix(balance=False)[:].tolist() == fixture["raw_matrix"]
        pixel_table = reader.pixels()[:]
        assert pixel_table[["bin1_id", "bin2_id", "count"]].values.tolist() == fixture["expected_stored_upper_pixels"]
    cooler_check["agreement_verified"] = True

result = {"record_type": "independent_complete_hdf5_fixture_readback_v1", "passed": True,
          "fixtures": reports, "expected_input_file": pin(expected_path),
          "generation_receipt": pin(generation_path), "verification_script": pin(__file__),
          "cooler_check": cooler_check,
          "python_executable": sys.executable, "h5py_version": h5py.__version__,
          "numpy_version": np.__version__, "hdf5_version": h5py.version.hdf5_version,
          "pid": os.getpid(), "parent_pid": os.getppid()}
Path("ARRAY_VERIFICATION.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
print(json.dumps({"passed": True,
                  "fixtures": [{"key": item["fixture_key"], "sha256": item["sha256"],
                                "size_bytes": item["size_bytes"], "population_counts": item["population_counts"]}
                               for item in reports], "cooler_check": cooler_check}))
