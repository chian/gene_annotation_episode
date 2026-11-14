"""Explicit preparation/verification of the selected HIC decoder's runtime.

This is execution custody, not a native-output parser or scientific calculator.
Builtin struct/zlib code is covered by the separately pinned interpreter. Actual
extension files, the struct wrapper, canonical-table mmap support and loaded
native libraries are pinned here.
"""
from __future__ import annotations

import importlib
from pathlib import Path

from .native_chromatin_interaction_contracts import require


def _runtime_files():
    paths = set()
    for name in ("struct", "_struct", "zlib", "mmap"):
        module = importlib.import_module(name)
        filename = getattr(module, "__file__", None)
        if filename is not None:
            paths.add(str(Path(filename).resolve(strict=True)))
    # The existing local execution binding is Linux/systemd. Observe the actual
    # libraries in that process, rather than inventing a zlib package/path or
    # executing ldd and parsing its platform-dependent output.
    with Path("/proc/self/maps").open(encoding="utf-8") as mappings:
        for line in mappings:
            fields = line.rstrip("\n").split(maxsplit=5)
            if len(fields) != 6 or "x" not in fields[1]:
                continue
            filename = fields[5]
            if not filename.startswith("/") or ".so" not in Path(filename).name:
                continue
            require(not filename.endswith(" (deleted)"), "native_dependency_unavailable")
            # Linux escapes a newline in a mapped filename as an octal sequence.
            # Such a path cannot satisfy the existing execution path grammar.
            require("\\" not in filename, "native_dependency_unavailable")
            paths.add(str(Path(filename).resolve(strict=True)))
    return sorted(paths)


def capture_hic_native_runtime(*, file_identity):
    """Capture actual selected runtime files during explicit bounded preparation."""
    import zlib
    return {"zlib_compile_version": zlib.ZLIB_VERSION,
            "zlib_runtime_version": zlib.ZLIB_RUNTIME_VERSION,
            "files": [{"path": path, **file_identity(path)} for path in _runtime_files()]}


def verify_hic_native_runtime(value, *, file_identity):
    """Verify the original runtime selection without installing/replacing it."""
    import zlib
    require(value["zlib_compile_version"] == zlib.ZLIB_VERSION
        and value["zlib_runtime_version"] == zlib.ZLIB_RUNTIME_VERSION,
        "native_dependency_unavailable")
    pins = {row["path"]: row for row in value["files"]}
    require(len(pins) == len(value["files"]), "native_dependency_unavailable")
    require(set(_runtime_files()) <= set(pins), "native_dependency_unavailable")
    for path, pin in pins.items():
        require(file_identity(path) == {key: pin[key] for key in ("sha256", "size_bytes")},
            "native_dependency_unavailable")
