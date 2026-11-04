"""Real metadata/receipt controls with engineered ToolOperation publications.

The rows below are explicit fixtures, not registered executions or evidence of
native production. The guard reads no scientific data and authenticates no
numerical result. Consumer wiring and complete Workflow delivery are separate.
"""
from contextlib import contextmanager
from copy import deepcopy
import base64
from pathlib import Path
from types import SimpleNamespace

import pytest

from method_loop.identities import EpisodeRef
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import canonical, identity
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.molecular_reference_privacy import molecular_reference_restriction
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry

from test_molecular_sequence_input_bindings import actual_received_input_owner


ITC = "analyze_itc_binding_thermodynamics"
LIFTOVER = "liftover_coordinates"
VERSIONS = {ITC: "ordinary_itc_result_v1", LIFTOVER: "ordinary_liftover_result_v1"}


@contextmanager
def publication(tmp_path, *, provider=ITC, version=None, origin="tool", status="completed",
        published=True, operation_provider=None, deliver_source=True, grant=()):
    with actual_received_input_owner(tmp_path, deliver=False) as value:
        store = value.store
        store.db.execute("CREATE TABLE tool_operations(operation_key TEXT PRIMARY KEY,id TEXT,name TEXT,"
            "arguments TEXT,scope TEXT,result TEXT)")
        native = store.artifact(("engineered native " + provider).encode(), "application/json")
        control = store.artifact(("engineered private control " + provider).encode(), "application/json")
        grade = store.artifact(("engineered grading " + provider).encode(), "application/json")
        diagnostic = store.artifact(("engineered failed-attempt diagnostic " + provider).encode(), "text/plain")
        source = store.put("source", dict(provider=provider, accession=None, uri=None,
            artifact_ref=native, text_ref=None, request_ref=control, version=version or VERSIONS[provider],
            retrieved_at=None, auxiliary_artifact_refs=[grade]), origin=origin)
        refs = dict(source=source["id"], native=native, control=control, grade=grade, diagnostic=diagnostic)
        name = operation_provider or provider
        key = "engineered-publication:" + provider
        operation = identity("operation", {"key": key, "name": name})
        if published:
            outcome = dict(status=status, operation_ref=operation, record_refs=[source["id"]],
                result={"source_ref": source["id"]}, feedback=None)
            store.db.execute("INSERT INTO tool_operations VALUES(?,?,?,?,?,?)", (key, operation, name,
                canonical({"mode": "fit" if provider == ITC else "convert"}), canonical(value.scope), canonical(outcome)))
        failed = dict(status="failed", operation_ref="engineered-failed-operation", record_refs=[],
            result=None, feedback={"diagnostic_ref": diagnostic})
        store.db.execute("INSERT INTO tool_operations VALUES(?,?,?,?,?,?)", (key + ":failed",
            "engineered-failed-operation", provider, "{}", canonical(value.scope), canonical(failed)))
        if deliver_source:
            value.receipts.receive(value.parent.episode_id, [source["id"]], kind="initial")
        if grant:
            value.receipts.receive(value.parent.episode_id, [refs[name] for name in grant], kind="initial")
        value.context = value.child(1)
        value.refs, value.provider = refs, provider
        yield value


def verdict(value, kind, namespace=None, *, context=None, private_only=False, providers=None):
    if namespace is None:
        namespace = "source" if kind == "source" else "artifact"
    return molecular_reference_restriction(value.store, value.context if context is None else context,
        value.refs[kind], namespace, private_only=private_only, providers=providers)


def other_root(value, run_id, *, received=()):
    path = (("annotation", "other_root"),)
    episode_id = EpisodeRef(run_id, path).episode_id
    receipts = EpisodeReceipts(value.store, run_id)
    manifest = receipts.bind(episode_id)
    request = plain(value.parent.request)
    request["message"]["knowledge_inheritance"] = manifest
    context = BindingContext(run_id, episode_id, "annotation", path, value.scope, {}, request)
    value.store.db.execute("INSERT INTO runtime_episodes VALUES(?,?,?,?)",
        (run_id, episode_id, canonical(path), canonical(request)))
    if received:
        receipts.receive(episode_id, [value.refs[name] for name in received], kind="initial")
    return context, receipts


@pytest.mark.parametrize("provider", [ITC, LIFTOVER])
def test_source_only_receipt_grants_source_but_not_native_or_grade_handles(tmp_path, provider):
    with publication(tmp_path, provider=provider) as value:
        known = set(value.receipts.known(value.context.episode_id))
        assert value.refs["source"] in known
        assert all(value.refs[name] not in known for name in ("native", "control", "grade", "diagnostic"))
        assert verdict(value, "source") is True
        assert molecular_reference_restriction(value.store, value.context, value.refs["source"], None) is True
        assert verdict(value, "native") is False and verdict(value, "grade") is False
        assert verdict(value, "control") is False and verdict(value, "diagnostic") is False


@pytest.mark.parametrize("provider", [ITC, LIFTOVER])
def test_explicit_native_and_grade_receipts_preserve_each_finite_profile_policy(tmp_path, provider):
    with publication(tmp_path, provider=provider, grant=("native", "grade", "control", "diagnostic")) as value:
        assert all(value.refs[name] in set(value.receipts.known(value.context.episode_id)) for name in value.refs)
        assert verdict(value, "native") is True
        assert verdict(value, "grade") is (provider == ITC)
        assert verdict(value, "control") is False and verdict(value, "diagnostic") is False
        assert verdict(value, "source", "artifact") is False
        assert verdict(value, "native", "source") is False
        assert molecular_reference_restriction(value.store, value.context, value.refs["native"], None) is True


@pytest.mark.parametrize("provider", [ITC, LIFTOVER])
@pytest.mark.parametrize("kind", ["source", "native", "control", "grade", "diagnostic"])
def test_contextless_private_only_denies_only_actual_private_metadata_roles(tmp_path, provider, kind):
    with publication(tmp_path, provider=provider) as value:
        result = molecular_reference_restriction(value.store, None, value.refs[kind], None, private_only=True)
        private = kind in {"control", "diagnostic"} or kind == "grade" and provider == LIFTOVER
        assert result is False if private else result is None


@pytest.mark.parametrize("provider", [ITC, LIFTOVER])
@pytest.mark.parametrize("change", ["missing", "foreign_run", "changed_context"])
def test_public_handles_need_actual_saved_receiving_context_and_receipts(tmp_path, provider, change):
    with publication(tmp_path, provider=provider, grant=("native", "grade")) as value:
        if change == "missing":
            context = None
        elif change == "foreign_run":
            context = BindingContext("unknown-run", value.context.episode_id, value.context.role,
                value.context.path, value.context.scope, value.context.assignment, value.context.request)
        else:
            request = plain(value.context.request)
            request["message"]["episode_assignment"]["changed"] = True
            context = BindingContext(value.context.run_id, value.context.episode_id, value.context.role,
                value.context.path, value.context.scope, request["message"]["episode_assignment"], request)
        for kind in ("source", "native", "grade"):
            assert molecular_reference_restriction(value.store, context, value.refs[kind],
                "source" if kind == "source" else "artifact") is False


@pytest.mark.parametrize("provider", [ITC, LIFTOVER])
def test_genuine_cross_run_parent_receipts_are_allowed_without_importing_other_run_facts(tmp_path, provider):
    with publication(tmp_path, provider=provider) as value:
        context, receipts = other_root(value, "actual-other-run")
        assert molecular_reference_restriction(value.store, context, value.refs["source"], "source") is False
        receipts.receive(context.episode_id, [value.refs["source"]], kind="initial")
        assert molecular_reference_restriction(value.store, context, value.refs["source"], "source") is True
        assert molecular_reference_restriction(value.store, context, value.refs["native"], "artifact") is False
        receipts.receive(context.episode_id, [value.refs["native"], value.refs["grade"]], kind="initial")
        assert molecular_reference_restriction(value.store, context, value.refs["native"], "artifact") is True
        assert molecular_reference_restriction(value.store, context, value.refs["grade"], "artifact") is (provider == ITC)


@pytest.mark.parametrize("provider", [ITC, LIFTOVER])
def test_late_parent_native_receipt_does_not_change_an_old_frozen_child_prefix(tmp_path, provider):
    with publication(tmp_path, provider=provider) as value:
        value.receipts.receive(value.parent.episode_id, [value.refs["native"]], kind="initial")
        assert verdict(value, "native") is False
        newer = value.child(2)
        assert verdict(value, "native", context=newer) is True
        assert verdict(value, "source", context=value.parent) is True
        assert verdict(value, "native", context=value.parent) is True


@pytest.mark.parametrize("change", ["no_publication", "failed_publication", "wrong_operation_provider", "wrong_version", "external_origin"])
def test_source_like_metadata_without_required_profile_publication_defers(tmp_path, change):
    kwargs = {"published": False} if change == "no_publication" else {"status": "failed"} if change == "failed_publication" else (
        {"operation_provider": "different_provider"} if change == "wrong_operation_provider" else
        {"version": "ordinary_itc_result_unknown"} if change == "wrong_version" else {"origin": "external"})
    with publication(tmp_path, **kwargs) as value:
        for kind in ("source", "native", "control", "grade"):
            assert verdict(value, kind) is None


@pytest.mark.parametrize("status", ["completed", "partial"])
def test_completed_and_partial_sources_share_the_declared_metadata_policy(tmp_path, status):
    with publication(tmp_path, provider=LIFTOVER, status=status) as value:
        assert verdict(value, "source") is True and verdict(value, "control") is False


def test_provider_subset_keeps_legacy_itc_wrapper_from_classifying_other_providers(tmp_path):
    with publication(tmp_path, provider=LIFTOVER, grant=("grade",)) as value:
        assert verdict(value, "control", providers=(ITC,)) is None
        assert verdict(value, "grade", providers=(ITC,)) is None
        assert verdict(value, "control", providers=(LIFTOVER,)) is False
        assert verdict(value, "control", providers=()) is None


@pytest.mark.parametrize("providers", [[ITC], ("unsupported_provider",), (ITC, ITC)])
def test_provider_selection_is_a_finite_internal_subset_tuple(tmp_path, providers):
    with publication(tmp_path) as value:
        with pytest.raises(ValueError, match="^molecular_reference_providers_invalid$"):
            verdict(value, "control", providers=providers)


def test_fresh_store_without_tool_operations_has_no_publication_restriction(tmp_path, monkeypatch):
    store = Store(tmp_path / "fresh")
    try:
        reference = store.artifact(b"ordinary initial material", "text/plain")
        before = store.db.total_changes
        def forbidden(*args, **kwargs):
            pytest.fail("privacy classification must not read artifact bytes")
        monkeypatch.setattr(store, "get_artifact", forbidden)
        assert molecular_reference_restriction(store, None, reference, "artifact", private_only=True) is None
        assert store.db.total_changes == before
        assert store.db.execute("SELECT 1 FROM sqlite_master WHERE name='tool_operations'").fetchone() is None
    finally:
        store.close()


def test_metadata_classification_does_not_read_artifacts_traverse_refs_or_mutate_any_rows(tmp_path, monkeypatch):
    with publication(tmp_path, provider=LIFTOVER, grant=("native", "grade", "control", "diagnostic")) as value:
        tables = ("records", "artifacts", "tool_operations", "runtime_actions", "runtime_episodes",
            "runtime_receipt_inheritance", "runtime_record_receipts")
        def rows():
            return {name: [tuple(row) for row in value.store.db.execute("SELECT * FROM " + name + " ORDER BY rowid")]
                for name in tables}
        before, changes = rows(), value.store.db.total_changes
        known = set(value.receipts.known(value.context.episode_id))
        def forbidden(*args, **kwargs):
            pytest.fail("metadata reference restriction must not read payloads, grant or traverse dependencies")
        monkeypatch.setattr(value.store, "get_artifact", forbidden)
        monkeypatch.setattr(value.store, "_refs", forbidden)
        monkeypatch.setattr(value.store, "artifact", forbidden)
        monkeypatch.setattr(Path, "open", forbidden)
        for kind in value.refs:
            verdict(value, kind)
            verdict(value, kind, private_only=True)
        assert rows() == before and value.store.db.total_changes == changes
        assert known == set(value.receipts.known(value.context.episode_id))


@pytest.mark.parametrize("reference", [None, 0, []])
def test_non_reference_values_defer_without_claiming_authority(tmp_path, reference):
    with publication(tmp_path) as value:
        assert molecular_reference_restriction(value.store, value.context, reference, None) is None


@pytest.mark.parametrize("value", [None, 0, 1, "true"])
def test_private_only_policy_requires_an_actual_boolean(tmp_path, value):
    with publication(tmp_path) as fixture:
        with pytest.raises(ValueError, match="^molecular_reference_private_only_invalid$"):
            molecular_reference_restriction(fixture.store, None, fixture.refs["control"], "artifact", private_only=value)


def source_alias(value, artifact_ref):
    """An actual engineering Source attachment, never a producer observation."""
    source = value.store.get(value.refs["source"])
    payload = {key: deepcopy(item) for key, item in source.items() if key not in {"id", "record_type", "origin"}}
    payload.update(provider="engineered_molecular_attachment", version="engineering_alias_v1",
        artifact_ref=artifact_ref, request_ref=None, auxiliary_artifact_refs=[], text_ref=None)
    source = value.store.put("source", payload, origin="external")
    value.receipts.receive(value.context.episode_id, [source["id"]], kind="decision_input", source_index=0)
    return source


def byte_registry(value):
    def forbidden(*args, **kwargs):
        raise AssertionError("ordinary byte reads must not invoke a provider or native worker")
    registry = ToolRegistry(value.store, clients=SimpleNamespace(_http=forbidden))
    return registry


def byte_arguments(value, tool, source):
    if tool == "material.read":
        material = value.store.register_material(source_ref=source["id"], format="raw", use="evidence")
        return {"material_ref": material["id"], "offset": 0, "limit": 65536}
    if tool == "source.locate":
        return {"source_ref": source["id"], "representation": "original", "needle": "engineered",
            "offset": 0, "limit": 1, "context_bytes": 0}
    return {"source_ref": source["id"], "representation": "original", "offset": 0, "limit": 65536}


def guard_byte_ports(value, monkeypatch):
    private = {value.refs["control"], value.refs["diagnostic"]}
    if value.provider == LIFTOVER:
        private.add(value.refs["grade"])
    private_paths = {value.store.path / "artifacts" / ref[9:11] / ref[9:] for ref in private}
    original_open, opened = Path.open, []
    directory = value.store.path / "artifacts"
    def checked(path, *args, **kwargs):
        assert path not in private_paths, "private ordinary artifact reached Path.open"
        if path.is_relative_to(directory):
            opened.append(path)
        return original_open(path, *args, **kwargs)
    def forbidden(*args, **kwargs):
        raise AssertionError("source/material byte read must not use private payload or native ports")
    monkeypatch.setattr(Path, "open", checked)
    monkeypatch.setattr(value.store, "get_artifact", forbidden)
    return opened


def selected_byte_call(value, registry, tool, arguments, *, context=True, cached=None):
    """Real ToolRegistry call with an engineered recorded selection, no Workflow."""
    index = 0
    key = f"{value.context.run_id}:{value.context.episode_id}:{index}"
    selected = {"kind": "tool", "tool": tool, "arguments": arguments}
    value.store.db.execute("INSERT INTO runtime_actions VALUES(?,?,?,?,NULL)",
        (value.context.run_id, value.context.episode_id, index, canonical(selected)))
    if cached is not None:
        value.store.db.execute("INSERT INTO tool_operations VALUES(?,?,?,?,?,?)", (key,
            cached["operation_ref"], tool, canonical(arguments), canonical(plain(value.context.scope)), canonical(cached)))
    def no_input(*args, **kwargs):
        raise AssertionError("byte tools must not request numerical or received-File input")
    kwargs = dict(scope=plain(value.context.scope), operation_key=key,
        permitted_record_refs=(arguments["source_ref"],) if tool == "source.locate" and "source_ref" in arguments else None)
    if context:
        with registry.current_invocation(value.context, read_received=no_input,
                tool_name=tool, arguments=arguments, operation_key=key):
            result = registry.execute(tool, arguments, **kwargs)
    else:
        result = registry.execute(tool, arguments, **kwargs)
    value.store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=?",
        (canonical(result), value.context.run_id, value.context.episode_id, index))
    return result, key


@pytest.mark.parametrize("provider", [ITC, LIFTOVER])
@pytest.mark.parametrize("tool", ["source.read", "source.locate", "material.read"])
@pytest.mark.parametrize("native_granted", [False, True], ids=["source_only", "explicit_native_file"])
def test_actual_byte_tools_require_the_separate_native_receipt_in_current_context(tmp_path, monkeypatch, provider, tool, native_granted):
    with publication(tmp_path, provider=provider, grant=("native",) if native_granted else ()) as value:
        registry = byte_registry(value)
        source = value.store.get(value.refs["source"])
        arguments = byte_arguments(value, tool, source)
        known = set(value.receipts.known(value.context.episode_id))
        opened = guard_byte_ports(value, monkeypatch)
        result, _ = selected_byte_call(value, registry, tool, arguments)
        if native_granted:
            assert result["status"] == "completed", result
            body = result["result"]
            assert body["source_ref"] == source["id"] and body["artifact_ref"] == value.refs["native"]
            expected = ("engineered native " + provider).encode()
            if tool == "source.read":
                assert body["text"].encode() == expected
            elif tool == "material.read":
                assert base64.b64decode(body["content"]) == expected
            else:
                assert body["matches"][0]["witness"]["quote"] == "engineered"
            assert opened
        else:
            assert result["status"] == "invalid", result
            assert result["feedback"]["code"] == "molecular_source_artifact_not_granted"
            assert result["result"] is None and result["record_refs"] == [] and opened == []
        assert known == set(value.receipts.known(value.context.episode_id))


@pytest.mark.parametrize("provider,kind", [(ITC, "control"), (ITC, "diagnostic"),
    (LIFTOVER, "control"), (LIFTOVER, "grade"), (LIFTOVER, "diagnostic")])
@pytest.mark.parametrize("tool", ["source.read", "source.locate", "material.read"])
def test_actual_private_source_aliases_are_denied_even_with_expanded_file_receipts(tmp_path, monkeypatch, provider, kind, tool):
    with publication(tmp_path, provider=provider, grant=(kind,)) as value:
        source = source_alias(value, value.refs[kind])
        registry = byte_registry(value)
        arguments = byte_arguments(value, tool, source)
        assert value.refs[kind] in set(value.receipts.known(value.context.episode_id))
        opened = guard_byte_ports(value, monkeypatch)
        result, _ = selected_byte_call(value, registry, tool, arguments)
        assert result["status"] == "invalid" and result["feedback"]["code"] == "molecular_source_artifact_not_granted"
        assert result["result"] is None and result["record_refs"] == [] and opened == []


@pytest.mark.parametrize("provider", [ITC, LIFTOVER])
def test_actual_byte_tool_without_current_context_cannot_read_a_published_native_file(tmp_path, monkeypatch, provider):
    with publication(tmp_path, provider=provider, grant=("native",)) as value:
        registry = byte_registry(value)
        arguments = byte_arguments(value, "source.read", value.store.get(value.refs["source"]))
        opened = guard_byte_ports(value, monkeypatch)
        result, _ = selected_byte_call(value, registry, "source.read", arguments, context=False)
        assert result["status"] == "invalid" and result["feedback"]["code"] == "molecular_source_artifact_not_granted"
        assert opened == []


def test_actual_itc_public_grading_alias_retains_its_explicit_file_permission(tmp_path, monkeypatch):
    with publication(tmp_path, provider=ITC, grant=("grade",)) as value:
        source = source_alias(value, value.refs["grade"])
        registry = byte_registry(value)
        arguments = byte_arguments(value, "source.read", source)
        opened = guard_byte_ports(value, monkeypatch)
        result, _ = selected_byte_call(value, registry, "source.read", arguments)
        assert result["status"] == "completed" and result["result"]["text"] == "engineered grading " + ITC
        assert opened


def test_actual_cached_private_alias_result_is_rechecked_before_returning_any_bytes(tmp_path, monkeypatch):
    with publication(tmp_path, provider=LIFTOVER, grant=("control",)) as value:
        source = source_alias(value, value.refs["control"])
        registry = byte_registry(value)
        arguments = byte_arguments(value, "source.read", source)
        cached = dict(status="completed", operation_ref="engineered-cached-operation", record_refs=[],
            result={"text": "engineered previously cached private value"}, feedback=None)
        opened = guard_byte_ports(value, monkeypatch)
        result, key = selected_byte_call(value, registry, "source.read", arguments, cached=cached)
        assert result["status"] == "invalid" and result["result"] is None
        assert result["feedback"]["code"] == "molecular_source_artifact_not_granted" and opened == []
        assert value.store.db.execute("SELECT result FROM tool_operations WHERE operation_key=?", (key,)).fetchone()[0] == canonical(cached)


def test_actual_invalid_source_operation_replays_its_original_failure_without_new_byte_lookup(tmp_path, monkeypatch):
    with publication(tmp_path, provider=LIFTOVER) as value:
        registry = byte_registry(value)
        opened = guard_byte_ports(value, monkeypatch)
        first, key = selected_byte_call(value, registry, "source.locate", {})
        assert first["status"] == "invalid" and first["result"] is None
        before = tuple(value.store.db.execute("SELECT * FROM tool_operations WHERE operation_key=?", (key,)).fetchone())
        def no_input(*args, **kwargs):
            raise AssertionError("invalid stored arguments must not invoke an input reader")
        with registry.current_invocation(value.context, read_received=no_input,
                tool_name="source.locate", arguments={}, operation_key=key):
            second = registry.execute("source.locate", {}, scope=plain(value.context.scope), operation_key=key)
        assert canonical(second) == canonical(first) and opened == []
        assert tuple(value.store.db.execute("SELECT * FROM tool_operations WHERE operation_key=?", (key,)).fetchone()) == before


@pytest.mark.parametrize("native_granted", [False, True], ids=["source_only", "explicit_native_file"])
def test_completed_cached_native_values_still_require_the_current_file_receipt(tmp_path, monkeypatch, native_granted):
    with publication(tmp_path, provider=LIFTOVER, grant=("native",) if native_granted else ()) as value:
        registry = byte_registry(value)
        source = value.store.get(value.refs["source"])
        arguments = byte_arguments(value, "source.read", source)
        cached = dict(status="completed", operation_ref="engineered-cached-native", record_refs=[],
            result={"source_ref": source["id"], "artifact_ref": value.refs["native"],
                "text": "engineered retained cached native values"}, feedback=None)
        opened = guard_byte_ports(value, monkeypatch)
        result, key = selected_byte_call(value, registry, "source.read", arguments, cached=cached)
        if native_granted:
            assert canonical(result) == canonical(cached)
        else:
            assert result["status"] == "invalid" and result["result"] is None
            assert result["feedback"]["code"] == "molecular_source_artifact_not_granted"
        assert opened == []
        assert value.store.db.execute("SELECT result FROM tool_operations WHERE operation_key=?", (key,)).fetchone()[0] == canonical(cached)
