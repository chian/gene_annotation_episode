"""Run the selected connected checks using only a reviewed immutable runtime."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pin", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    pin, output = args.pin.resolve(), args.output.resolve()
    assert not output.is_relative_to(pin)
    output.mkdir(parents=True, exist_ok=False)
    repository = next(p for p in pin.parents if (p / "AGENTS.md").is_file())
    sys.path[:] = [str(pin), str(pin / "tests"), *[
        entry for entry in sys.path if entry and Path(entry).resolve() not in {
            repository, repository / "tests", Path(__file__).resolve().parent}]]
    sys.dont_write_bytecode = True
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    from gene_annotation_episode import providers
    attempted_calls = []
    def forbidden(*_args, **_kwargs):
        attempted_calls.append("model_entrypoint")
        raise AssertionError("pinned_checks_forbid_model_calls")
    # LiteratureWire intentionally exercises the actual session constructor and
    # complete/presentation path over its own scripted _rpc implementation.
    # Block external connection startup/transport, not those pure fixture paths.
    for name in ("__init__", "__aenter__", "complete", "catalog"):
        setattr(providers.ModelConnection, name, forbidden)
    for name in ("__aenter__", "_rpc", "_send", "_read"):
        setattr(providers._SessionConnection, name, forbidden)
    import pytest
    tests = ['test_literature_rate_native_inputs.py', 'test_literature_rate_native_storage.py', 'test_literature_rate_native_integration.py', 'test_literature_parent_population_information.py', 'test_literature_amount_calculations.py', 'test_literature_amount_contracts.py', 'test_literature_amount_inputs.py', 'test_literature_amount_storage.py', 'test_literature_amount_integration.py', 'test_literature_numeric_range_scope.py', 'test_literature_amount_range_scope_integration.py', 'test_literature_witness_repair_feedback.py']
    status = pytest.main(["-q", "-c", "/dev/null", "--rootdir", str(pin),
        "--basetemp", str(output / "state"), "-o", "cache_dir=" + str(output / "cache"),
        "--junitxml", str(output / "RESULTS.xml"),
        *[str(pin / "tests" / name) for name in tests]])
    imported = []
    for name, module in sorted(sys.modules.items()):
        if not name.startswith(("gene_annotation_episode", "method_loop")):
            continue
        filename = getattr(module, "__file__", None)
        if filename:
            path = Path(filename).resolve()
            assert path.is_relative_to(pin), (name, str(path))
            imported.append({"module": name, "path": str(path),
                             "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    receipt = {"pytest_exit_code": int(status), "model_calls": attempted_calls,
               "runtime_imports": imported, "selected_test_files": tests,
               "pin_manifest_sha256": hashlib.sha256((pin / "SOURCE_MANIFEST.json").read_bytes()).hexdigest(),
               "meaning": "Synthetic connected fixtures using pinned runtime; no configured-model scientific execution"}
    with (output / "IMPORT_PROOF.json").open("x") as stream:
        json.dump(receipt, stream, indent=2)
    assert not attempted_calls
    print(json.dumps({"pytest_exit_code": int(status), "pinned_runtime_imports": len(imported),
                      "model_calls": attempted_calls}), flush=True)
    raise SystemExit(status)


if __name__ == "__main__":
    main()
