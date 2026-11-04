"""Recorded preparations and explicit, truthful local/remote reconciliation.

An inventory cannot install a tool, prove current usability, select execution or
award credit.  The caller supplies the remote reader and invokes reconciliation
explicitly.  The returned snapshot can then be retained with a decision or
commission; reading that snapshot never performs more remote work.
"""
from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile

from jsonschema import Draft202012Validator


CATALOG_VERSION = "execution_inventory_catalog_v1"
MIRROR_VERSION = "execution_inventory_mirror_v1"
SNAPSHOT_VERSION = "execution_inventory_snapshot_v1"
COMPONENT_KINDS = ("environment", "software", "database", "index", "prepared_operation")


class InventoryError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def canonical_bytes(value):
    """The finite JSON representation used for content identities."""
    def check(item):
        if type(item) is dict:
            if any(type(key) is not str for key in item):
                raise InventoryError("inventory_json_invalid")
            for child in item.values():
                check(child)
        elif type(item) is list:
            for child in item:
                check(child)
        elif item is not None and type(item) not in (str, int, float, bool):
            raise InventoryError("inventory_json_invalid")

    try:
        check(value)
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, UnicodeError) as error:
        raise InventoryError("inventory_json_invalid") from error


def digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _object(value, fields, code):
    if type(value) is not dict or set(value) != set(fields):
        raise InventoryError(code)


def _text(value):
    return type(value) is str and bool(value.strip()) and "\x00" not in value


def _timestamp(value):
    try:
        if type(value) is not str:
            raise ValueError
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
            raise ValueError
        return parsed
    except (ValueError, TypeError, AttributeError) as error:
        raise InventoryError("inventory_timestamp_invalid") from error


def _path(value):
    return (_text(value) and PurePosixPath(value).is_absolute()
            and ".." not in PurePosixPath(value).parts)


def _strings(value):
    return (type(value) is list and all(_text(item) for item in value)
            and len(value) == len(set(value)))


def _tools(value):
    if isinstance(value, Mapping):
        entries = []
        for name, entry in value.items():
            if (not _text(name) or not isinstance(entry, Mapping)
                    or "name" in entry and entry["name"] != name):
                raise InventoryError("inventory_tool_map_invalid")
            entries.append({**entry, "name": name})
    elif isinstance(value, (list, tuple)):
        entries = value
    else:
        raise InventoryError("inventory_tool_map_invalid")
    result = {}
    for entry in entries:
        if (not isinstance(entry, Mapping) or not _text(entry.get("name"))
                or type(entry.get("input_schema")) is not dict
                or entry["name"] in result):
            raise InventoryError("inventory_tool_map_invalid")
        result[entry["name"]] = entry["input_schema"]
    return result


def validate_component(value, *, tool_map=None):
    """Validate a component description without inspecting its actual path.

    ``version`` identifies the software/database release, and may be unknown.
    ``identity`` records the installation/artifact identity, not a readiness
    judgement.  The catalog version defines this component record's schema.
    """
    fields = {"component_id", "kind", "path", "identity", "version",
              "dependencies", "provenance_refs"}
    prepared = isinstance(value, dict) and value.get("kind") == "prepared_operation"
    _object(value, fields | ({"tool_name", "input_schema"} if prepared else set()),
            "inventory_component_invalid")
    if (not _text(value["component_id"]) or value["kind"] not in COMPONENT_KINDS
            or not _path(value["path"]) or not _text(value["identity"])
            or value["version"] is not None and not _text(value["version"])
            or not _strings(value["dependencies"]) or not _strings(value["provenance_refs"])):
        raise InventoryError("inventory_component_invalid")
    if prepared:
        if not _text(value["tool_name"]) or type(value["input_schema"]) is not dict:
            raise InventoryError("inventory_operation_contract_invalid")
        try:
            Draft202012Validator.check_schema(value["input_schema"])
        except Exception as error:
            raise InventoryError("inventory_operation_contract_invalid") from error
        if tool_map is not None:
            tools = _tools(tool_map)
            if value["tool_name"] not in tools:
                raise InventoryError("inventory_operation_tool_not_bound")
            if canonical_bytes(value["input_schema"]) != canonical_bytes(tools[value["tool_name"]]):
                raise InventoryError("inventory_operation_contract_mismatch")
    return json.loads(canonical_bytes(value))


def validate_catalog(value, *, tool_map=None):
    _object(value, {"version", "resource_id", "workspace", "recorded_at", "components"},
            "inventory_catalog_invalid")
    if (value["version"] != CATALOG_VERSION or not _text(value["resource_id"])
            or not _path(value["workspace"]) or type(value["components"]) is not list):
        raise InventoryError("inventory_catalog_invalid")
    _timestamp(value["recorded_at"])
    components = [validate_component(item, tool_map=tool_map) for item in value["components"]]
    by_id = {item["component_id"]: item for item in components}
    if len(by_id) != len(components):
        raise InventoryError("inventory_component_identity_duplicate")
    for item in components:
        if any(reference not in by_id for reference in item["dependencies"]):
            raise InventoryError("inventory_dependency_missing")
    visiting, visited = set(), set()

    def visit(reference):
        if reference in visiting:
            raise InventoryError("inventory_dependency_cycle")
        if reference not in visited:
            visiting.add(reference)
            for dependency in by_id[reference]["dependencies"]:
                visit(dependency)
            visiting.remove(reference)
            visited.add(reference)

    for reference in by_id:
        visit(reference)
    return json.loads(canonical_bytes(value))


def make_catalog(*, resource_id, workspace, components, recorded_at=None, tool_map=None):
    return validate_catalog({"version": CATALOG_VERSION, "resource_id": resource_id,
        "workspace": str(workspace), "recorded_at": recorded_at if recorded_at is not None else _now(),
        "components": components}, tool_map=tool_map)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise InventoryError("inventory_json_duplicate_key")
            result[key] = value
        return result

    if type(raw) is not bytes:
        raise InventoryError("inventory_remote_bytes_required")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(InventoryError("inventory_json_invalid")))
    except (ValueError, UnicodeError) as error:
        if isinstance(error, InventoryError):
            raise
        raise InventoryError("inventory_json_invalid") from error


def _mirror(value, *, tool_map=None):
    _object(value, {"version", "catalog", "catalog_sha256", "catalog_observed_at"},
            "inventory_mirror_invalid")
    if value["version"] != MIRROR_VERSION:
        raise InventoryError("inventory_mirror_invalid")
    validate_catalog(value["catalog"], tool_map=tool_map)
    if value["catalog_sha256"] != digest(value["catalog"]):
        raise InventoryError("inventory_catalog_digest_mismatch")
    _timestamp(value["catalog_observed_at"])
    return value


def validate_snapshot(value, *, tool_map=None):
    _object(value, {"version", "catalog", "catalog_sha256", "remote_status",
        "comparison", "observed_at", "catalog_observed_at", "failure"},
        "inventory_snapshot_invalid")
    if value["version"] != SNAPSHOT_VERSION:
        raise InventoryError("inventory_snapshot_invalid")
    observed = _timestamp(value["observed_at"])
    if value["catalog"] is None:
        if value["catalog_sha256"] is not None or value["catalog_observed_at"] is not None:
            raise InventoryError("inventory_snapshot_invalid")
    else:
        validate_catalog(value["catalog"], tool_map=tool_map)
        if value["catalog_sha256"] != digest(value["catalog"]):
            raise InventoryError("inventory_catalog_digest_mismatch")
        if _timestamp(value["catalog_observed_at"]) > observed:
            raise InventoryError("inventory_snapshot_observation_order_invalid")
    if value["remote_status"] == "available":
        if (value["catalog"] is None or value["comparison"] not in {"matched", "updated"}
                or value["catalog_observed_at"] != value["observed_at"]
                or value["failure"] is not None):
            raise InventoryError("inventory_snapshot_invalid")
    elif value["remote_status"] == "unavailable":
        _object(value["failure"], {"code", "exception_type"}, "inventory_snapshot_invalid")
        if (value["comparison"] != "remote_unavailable"
                or value["failure"]["code"] != "remote_unavailable"
                or not _text(value["failure"]["exception_type"])):
            raise InventoryError("inventory_snapshot_invalid")
    else:
        raise InventoryError("inventory_snapshot_invalid")
    return json.loads(canonical_bytes(value))


def _read(path):
    if path.is_symlink():
        raise InventoryError("inventory_mirror_symlink")
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


@contextmanager
def _locked(path):
    descriptor = os.open(path.with_name(path.name + ".lock"),
        os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)


def _publish(path, value, original):
    path.parent.mkdir(parents=True, exist_ok=True)
    with _locked(path):
        if _read(path) != original:
            raise InventoryError("inventory_mirror_conflict")
        descriptor, temporary = tempfile.mkstemp(prefix="." + path.name + "-", dir=path.parent)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(canonical_bytes(value) + b"\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
            directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


def reconcile_inventory(local_path, read_remote, *, tool_map=None, observed_at=None):
    """Read remote catalog bytes once and retain a conflict-safe dated mirror.

    ``read_remote`` is a caller-bound zero-argument callback. An exception means
    that observation was unavailable; its message is deliberately not copied
    into the snapshot. Invalid returned bytes/catalogs are validation errors,
    not an unavailable-resource claim. The cache is preserved in either case.
    Concurrent mirror replacement raises a conflict rather than overwriting
    the other writer. No installed-component usability checks happen here.
    """
    if not callable(read_remote):
        raise TypeError("inventory_remote_reader_required")
    path = Path(local_path)
    original = _read(path)
    previous = None if original is None else _mirror(_decode(original), tool_map=tool_map)
    failure = None
    try:
        raw = read_remote()
    except Exception as error:
        failure = {"code": "remote_unavailable", "exception_type": type(error).__name__}
    stamp = observed_at if observed_at is not None else _now()
    _timestamp(stamp)
    if failure is not None:
        return validate_snapshot({"version": SNAPSHOT_VERSION,
            "catalog": None if previous is None else previous["catalog"],
            "catalog_sha256": None if previous is None else previous["catalog_sha256"],
            "catalog_observed_at": None if previous is None else previous["catalog_observed_at"],
            "remote_status": "unavailable", "comparison": "remote_unavailable",
            "observed_at": stamp, "failure": failure}, tool_map=tool_map)
    catalog = validate_catalog(_decode(raw), tool_map=tool_map)
    catalog_sha256 = digest(catalog)
    if previous is not None and (previous["catalog"]["resource_id"] != catalog["resource_id"]
            or previous["catalog"]["workspace"] != catalog["workspace"]):
        raise InventoryError("inventory_resource_identity_conflict")
    comparison = ("matched" if previous is not None
        and previous["catalog_sha256"] == catalog_sha256 else "updated")
    snapshot = validate_snapshot({"version": SNAPSHOT_VERSION, "catalog": catalog,
        "catalog_sha256": catalog_sha256, "catalog_observed_at": stamp,
        "remote_status": "available", "comparison": comparison,
        "observed_at": stamp, "failure": None}, tool_map=tool_map)
    _publish(path, {"version": MIRROR_VERSION, "catalog": catalog,
        "catalog_sha256": catalog_sha256, "catalog_observed_at": stamp}, original)
    return snapshot


__all__ = ["CATALOG_VERSION", "MIRROR_VERSION", "SNAPSHOT_VERSION", "COMPONENT_KINDS",
    "InventoryError", "canonical_bytes", "digest", "validate_component", "validate_catalog",
    "validate_snapshot", "make_catalog", "reconcile_inventory"]
