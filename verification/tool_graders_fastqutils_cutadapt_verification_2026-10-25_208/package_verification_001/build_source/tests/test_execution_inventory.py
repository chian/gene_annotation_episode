from copy import deepcopy
import json

import pytest

from gene_annotation_episode.execution_inventory import (
    CATALOG_VERSION, InventoryError, canonical_bytes, digest, make_catalog,
    reconcile_inventory, validate_catalog, validate_snapshot,
)


FIRST = "2026-10-22T15:00:00+00:00"
LATER = "2026-10-22T16:00:00+00:00"
WORKSPACE = "/lus/flare/projects/BioReason-Aurora-Test"
TOOL_MAP = {"execution.run": {"input_schema": {
    "type": "object", "properties": {"argv": {"type": "array", "items": {"type": "string"}}},
    "required": ["argv"], "additionalProperties": False}}}


def component(name="python", kind="environment", dependencies=None):
    value = {"component_id": name, "kind": kind,
        "path": WORKSPACE + "/envs/" + name, "identity": name + "-installation-1",
        "version": "3.12", "dependencies": dependencies or [],
        "provenance_refs": ["inspection:actual-record"]}
    if kind == "prepared_operation":
        value.update(tool_name="execution.run",
            input_schema=deepcopy(TOOL_MAP["execution.run"]["input_schema"]))
    return value


def catalog(components=None):
    return make_catalog(resource_id="aurora", workspace=WORKSPACE,
        components=components if components is not None else [component()], recorded_at=FIRST)


def unavailable():
    raise ConnectionError("do not copy credentials or connection diagnostics")


def test_first_reconcile_retains_remote_catalog_and_original_snapshot(tmp_path):
    path = tmp_path / "mirror.json"
    first_catalog = catalog()
    first = reconcile_inventory(path, lambda: canonical_bytes(first_catalog), observed_at=FIRST)
    assert first["comparison"] == "updated"
    assert first["catalog_sha256"] == digest(first_catalog)
    assert first["catalog_observed_at"] == FIRST
    assert first["remote_status"] == "available"
    assert "ready" not in first
    assert "usable" not in first
    changed = deepcopy(first_catalog)
    changed["components"][0]["version"] = "3.13"
    updated = reconcile_inventory(path, lambda: canonical_bytes(changed), observed_at=LATER)
    assert updated["comparison"] == "updated"
    assert first["catalog"] == first_catalog
    assert first["catalog_sha256"] != updated["catalog_sha256"]
    assert json.loads(path.read_bytes())["catalog"] == changed
    assert path.stat().st_mode & 0o777 == 0o600


def test_matching_digest_only_confirms_catalog_agreement(tmp_path):
    path = tmp_path / "mirror.json"
    raw = canonical_bytes(catalog())
    reconcile_inventory(path, lambda: raw, observed_at=FIRST)
    matched = reconcile_inventory(path, lambda: raw, observed_at=LATER)
    assert matched["comparison"] == "matched"
    assert matched["catalog_observed_at"] == LATER
    assert "component_checks" not in matched
    assert "usable" not in matched["catalog"]["components"][0]


def test_unavailable_remote_preserves_dated_cache_and_bytes(tmp_path):
    path = tmp_path / "mirror.json"
    reconcile_inventory(path, lambda: canonical_bytes(catalog()), observed_at=FIRST)
    before = path.read_bytes()
    snapshot = reconcile_inventory(path, unavailable, observed_at=LATER)
    assert snapshot["remote_status"] == "unavailable"
    assert snapshot["comparison"] == "remote_unavailable"
    assert snapshot["catalog_observed_at"] == FIRST
    assert snapshot["observed_at"] == LATER
    assert snapshot["failure"] == {"code": "remote_unavailable", "exception_type": "ConnectionError"}
    assert "credentials" not in str(snapshot)
    assert path.read_bytes() == before


def test_unavailable_without_cache_keeps_unknown_catalog_unknown(tmp_path):
    path = tmp_path / "mirror.json"
    snapshot = reconcile_inventory(path, unavailable, observed_at=LATER)
    assert snapshot["catalog"] is None
    assert snapshot["catalog_sha256"] is None
    assert snapshot["catalog_observed_at"] is None
    assert not path.exists()


@pytest.mark.parametrize("raw", [b"not json", b'{"version":"x","version":"y"}', b'{"x":NaN}'])
def test_corrupt_remote_is_not_misreported_as_unavailable_and_does_not_overwrite(tmp_path, raw):
    path = tmp_path / "mirror.json"
    reconcile_inventory(path, lambda: canonical_bytes(catalog()), observed_at=FIRST)
    before = path.read_bytes()
    with pytest.raises(InventoryError):
        reconcile_inventory(path, lambda: raw, observed_at=LATER)
    assert path.read_bytes() == before


def test_corrupt_cached_digest_is_rejected_before_remote_callback(tmp_path):
    path = tmp_path / "mirror.json"
    reconcile_inventory(path, lambda: canonical_bytes(catalog()), observed_at=FIRST)
    value = json.loads(path.read_bytes())
    value["catalog"]["components"][0]["path"] += "/tampered"
    path.write_bytes(canonical_bytes(value))
    calls = []
    with pytest.raises(InventoryError, match="inventory_catalog_digest_mismatch"):
        reconcile_inventory(path, lambda: calls.append(True), observed_at=LATER)
    assert calls == []


def test_concurrent_newer_mirror_is_preserved(tmp_path):
    path = tmp_path / "mirror.json"
    original = catalog()
    reconcile_inventory(path, lambda: canonical_bytes(original), observed_at=FIRST)
    newer = deepcopy(original)
    newer["components"][0]["version"] = "3.14"
    stale = deepcopy(original)
    stale["components"][0]["version"] = "3.13"

    def remote_read_with_competing_writer():
        reconcile_inventory(path, lambda: canonical_bytes(newer), observed_at=LATER)
        return canonical_bytes(stale)

    with pytest.raises(InventoryError, match="inventory_mirror_conflict"):
        reconcile_inventory(path, remote_read_with_competing_writer, observed_at=LATER)
    assert json.loads(path.read_bytes())["catalog"] == newer


def test_inventory_cannot_change_resource_or_workspace_through_refresh(tmp_path):
    path = tmp_path / "mirror.json"
    original = catalog()
    reconcile_inventory(path, lambda: canonical_bytes(original), observed_at=FIRST)
    before = path.read_bytes()
    other = deepcopy(original)
    other["resource_id"] = "different-host"
    with pytest.raises(InventoryError, match="inventory_resource_identity_conflict"):
        reconcile_inventory(path, lambda: canonical_bytes(other), observed_at=LATER)
    assert path.read_bytes() == before


def test_operation_uses_actual_tool_and_exact_input_contract():
    prepared = component("pfam", "prepared_operation", ["python"])
    value = catalog([component(), prepared])
    assert validate_catalog(value, tool_map=TOOL_MAP) == value
    list_map = [{"name": name, **entry} for name, entry in TOOL_MAP.items()]
    assert validate_catalog(value, tool_map=list_map) == value
    with pytest.raises(InventoryError, match="inventory_operation_tool_not_bound"):
        validate_catalog(value, tool_map={})
    altered = deepcopy(value)
    altered["components"][1]["input_schema"]["additionalProperties"] = True
    with pytest.raises(InventoryError, match="inventory_operation_contract_mismatch"):
        validate_catalog(altered, tool_map=TOOL_MAP)


@pytest.mark.parametrize("components,code", [
    ([component(), component()], "inventory_component_identity_duplicate"),
    ([component(dependencies=["absent"])], "inventory_dependency_missing"),
    ([component(dependencies=["python"])], "inventory_dependency_cycle"),
    ([component(dependencies=["second"]), component("second", dependencies=["python"])],
        "inventory_dependency_cycle"),
])
def test_dependency_integrity(components, code):
    with pytest.raises(InventoryError, match=code):
        catalog(components)


@pytest.mark.parametrize("change", [
    lambda value: value.update(ready=True),
    lambda value: value["components"][0].update(path="relative/place"),
    lambda value: value["components"][0].update(path="/absolute/../elsewhere"),
    lambda value: value["components"][0].update(ready=True),
    lambda value: value.update(recorded_at="2026-10-22T15:00:00"),
    lambda value: value["components"][0].update(version=float("nan")),
])
def test_strict_catalog_fields_and_types(change):
    value = catalog()
    change(value)
    with pytest.raises(InventoryError):
        validate_catalog(value)


def test_snapshot_digest_and_freshness_relationships_are_checked(tmp_path):
    snapshot = reconcile_inventory(tmp_path / "mirror.json",
        lambda: canonical_bytes(catalog()), observed_at=FIRST)
    wrong_digest = deepcopy(snapshot)
    wrong_digest["catalog_sha256"] = "0" * 64
    with pytest.raises(InventoryError, match="inventory_catalog_digest_mismatch"):
        validate_snapshot(wrong_digest)
    wrong_freshness = deepcopy(snapshot)
    wrong_freshness["catalog_observed_at"] = LATER
    with pytest.raises(InventoryError, match="inventory_snapshot_observation_order_invalid"):
        validate_snapshot(wrong_freshness)


def test_mirror_symlink_is_not_followed(tmp_path):
    target = tmp_path / "unrelated"
    target.write_text("preserve")
    link = tmp_path / "mirror.json"
    link.symlink_to(target)
    with pytest.raises(InventoryError, match="inventory_mirror_symlink"):
        reconcile_inventory(link, lambda: canonical_bytes(catalog()), observed_at=FIRST)
    assert target.read_text() == "preserve"


def test_canonical_identity_ignores_object_key_order_and_rejects_nonfinite_values():
    assert digest({"a": 1, "b": "é"}) == digest({"b": "é", "a": 1})
    assert canonical_bytes({"b": "é", "a": 1}) == '{"a":1,"b":"é"}'.encode("utf-8")
    with pytest.raises(InventoryError, match="inventory_json_invalid"):
        digest({"value": float("inf")})
    assert catalog()["version"] == CATALOG_VERSION
