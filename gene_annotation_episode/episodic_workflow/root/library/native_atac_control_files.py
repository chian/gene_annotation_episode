"""Original native control JSON and input-file staging operations.

These complete ATAC helpers serve native producers without importing a
scientific pipeline or host process coordinator.
"""
from __future__ import annotations
import json
import os
from gene_annotation_episode.local_job_policy import check_scratch_budget
from .native_atac_differential_contracts import canonical, require
from .native_atac_file_records import (
    _regular, _writing, confined_file, file_identity, _publish,
)


def decode_json(raw):
    def pairs(rows):
        result = {}
        for key, value in rows:
            require(key not in result, "invalid_native_control_json")
            result[key] = value
        return result
    def constant(_):
        raise ValueError("invalid_native_control_json")
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("invalid_native_control_json") from error


def _read_control(path):
    with _regular(path) as stream:
        raw = stream.read()
    value = decode_json(raw)
    require(raw in (canonical(value), canonical(value) + b"\n"), "original_attempt_mismatch")
    return value


def _immutable(path, value):
    raw = canonical(value)
    if path.exists():
        with _regular(path) as stream:
            require(stream.read() == raw)
        return
    with _writing(path) as stream:
        stream.write(raw)


def _stage(binding, spec, *, directory, policy):
    target = confined_file(directory, spec["relative_path"])
    temporary = confined_file(target.parent, "." + target.name + ".staging")
    with _regular(binding["path"]) as source:
        before = os.fstat(source.fileno())
        check_scratch_budget(directory.parent, policy, additional_bytes=before.st_size)
        with temporary.open("xb") as output:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                output.write(block)
            output.flush()
            os.fsync(output.fileno())
        after = os.fstat(source.fileno())
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns), "artifact_digest_mismatch")
    require(file_identity(temporary) == {k: binding["file"][k] for k in ("sha256", "size_bytes")}, "artifact_digest_mismatch")
    _publish(temporary, target)
    return target

