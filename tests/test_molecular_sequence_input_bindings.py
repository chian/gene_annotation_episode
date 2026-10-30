"""Actual Store/EPR receipt controls, with explicitly engineered commissions.

No native service, scientific launch, historical source-version authority or
new receipt/grant is claimed by these read-only input tests.
"""
from contextlib import contextmanager
from copy import deepcopy
import gzip
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from method_loop.identities import EpisodeRef
from gene_annotation_episode.bvbrc_appservice_custody import AppServiceCustody
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import canonical, validate_schema
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.molecular_sequence_input_bindings import MolecularSequenceInputBindings
from gene_annotation_episode import molecular_sequence_input_bindings as bindings
from gene_annotation_episode import molecular_sequence_input_contracts as contracts
from gene_annotation_episode.state import Store


@contextmanager
def actual_received_input_owner(tmp_path, *, raw=b'{"version":"supplied_v1","samples":[1]}',
        namespace="artifact", protected=False, deliver=True, grant_artifact=False, two_targets=False):
    """Reusable real authority fixture; configured scientific routing is absent."""
    store = Store(tmp_path / "state")
    try:
        if two_targets:
            manifest = tmp_path / "targets.json"
            manifest.write_text(json.dumps(dict(schema_version=1, entries=[
                dict(sequence="ACGTACGT", molecule="dna", name="A"),
                dict(sequence="TTTTCCCC", molecule="dna", name="B")])))
            store.create_problem(manifest_path=manifest)
        else:
            store.create_problem(raw_sequence="ACGTACGT", molecule="dna")
        for sql in (
            "CREATE TABLE runtime_episodes(run_id TEXT,episode_id TEXT,path TEXT,request TEXT,PRIMARY KEY(run_id,episode_id))",
            "CREATE TABLE runtime_actions(run_id TEXT,episode_id TEXT,decision_index INTEGER,action TEXT,result TEXT,PRIMARY KEY(run_id,episode_id,decision_index))",
            "CREATE TABLE runtime_model_calls(run_id TEXT,episode_id TEXT,call_index INTEGER,request TEXT,response TEXT,purpose TEXT)",
        ): store.db.execute(sql)
        run, scope = "controlled-received-input", store.validate_scope()
        artifact = store.artifact(raw, "application/octet-stream")
        text = store.artifact(b'{"version":"derived_text_v1","replacement":true}', "text/plain")
        source = store.put("source", dict(provider="episode.execution_result" if protected else "controlled_input",
            accession=None, uri=None, artifact_ref=artifact, text_ref=text, request_ref=None,
            version="native_blast_utility_bundle_v1" if protected else "declared_source_version", retrieved_at=None), origin="tool")
        reference = artifact if namespace == "artifact" else source["id"]
        receipts = EpisodeReceipts(store, run)
        path = (("annotation", "root"),); parent_id = EpisodeRef(run, path).episode_id
        manifest = receipts.bind(parent_id)
        if deliver: receipts.receive(parent_id, [reference], kind="initial")
        if grant_artifact: receipts.receive(parent_id, [artifact], kind="initial")
        schema = dict(type="object", properties={}, required=[], additionalProperties=False)
        contract = AppServiceCustody._report_contract("Inspect supplied input bytes.", schema)
        request = dict(goal={"engineering_fixture": True}, message=dict(scope=scope,
            episode_assignment={}, knowledge_inheritance=manifest), report_contract=contract)
        parent = BindingContext(run, parent_id, "annotation", path, scope, {}, request)
        store.db.execute("INSERT INTO runtime_episodes VALUES(?,?,?,?)", (run, parent_id, canonical(path), canonical(request)))
        denied, verdicts = set(), []
        owner = SimpleNamespace(store=store, run_id=run)
        def access(context, ref, kind):
            assert context.run_id == run
            verdicts.append((ref, kind)); return False if (ref, kind) in denied else None
        owner.resolve_received_reference = access
        binding = MolecularSequenceInputBindings(owner)
        value = SimpleNamespace(store=store, owner=owner, binding=binding, receipts=receipts,
            parent=parent, context=None, artifact_ref=artifact, source_ref=source["id"], text_ref=text,
            reference=reference, namespace=namespace, denied=denied, verdicts=verdicts, scope=scope)
        def child(index, *, child_scope=None):
            actual_scope = scope if child_scope is None else child_scope
            child_path = (*path, ("results", "child_" + str(index)))
            child_id = EpisodeRef(run, child_path).episode_id
            assignment = {"controlled_input": "received_json"}
            selected = dict(kind="episode_child", role="results", scope=actual_scope, assignment=assignment,
                purpose=contract["decision"], schema_json=canonical(schema), goal="Inspect received data", initial_report_json="{}")
            store.db.execute("INSERT INTO runtime_actions VALUES(?,?,?,?,NULL)", (run, parent_id, index, canonical(selected)))
            inherited = receipts.bind(child_id, parent_id)
            child_request = dict(goal={"engineering_fixture": True}, message=dict(scope=actual_scope,
                episode_assignment=assignment, initial_report={}, knowledge_inheritance=inherited), report_contract=contract)
            result = BindingContext(run, child_id, "results", child_path, actual_scope, assignment, child_request)
            store.db.execute("INSERT INTO runtime_episodes VALUES(?,?,?,?)", (run, child_id, canonical(child_path), canonical(child_request)))
            return result
        value.child = child
        value.context = child(0)
        yield value
    finally:
        store.close()


def read_input(value, *, tag_key="version", context=None):
    return value.binding.read_received(context or value.context, value.reference, value.namespace, tag_key=tag_key)


def assert_denied(result, code):
    contracts.validate_molecular_sequence_received_input(result)
    assert set(result) == {"version", "selection", "input", "failure"}
    assert result["input"] is None and result["failure"]["code"] == code
    # Only caller-supplied reference/namespace and a closed code survive.
    assert set(result["selection"]) == {"reference", "namespace"}
    assert set(result["failure"]) == {"stage", "code"}


@pytest.mark.parametrize("namespace", ["artifact", "source"])
def test_actual_received_artifact_and_source_keep_file_current_version_and_original_content(tmp_path, namespace):
    with actual_received_input_owner(tmp_path, namespace=namespace) as value:
        result = read_input(value); item = result["input"]
        assert result["failure"] is None and item["byte_verification"] == "verified"
        assert item["file"]["artifact_ref"] == value.artifact_ref and item["file"]["format"] == "json"
        assert item["artifact_record"]["media_type"] == "application/octet-stream"
        assert item["witness"]["record_revision"] is None
        assert item["witness"]["source_version"] == ("declared_source_version" if namespace == "source" else None)
        assert item["content"]["document_version"] == "supplied_v1"
        assert item["content"]["value"] == {"version": "supplied_v1", "samples": [1]}
        assert item["content"]["value"].get("replacement") is None


def test_ordinary_source_receipt_expands_actual_dependency_but_protected_source_does_not(tmp_path):
    with actual_received_input_owner(tmp_path / "ordinary", namespace="source") as value:
        assert value.artifact_ref in set(value.receipts.known(value.context.episode_id, baseline=True))
        assert read_input(value)["input"] is not None
    with actual_received_input_owner(tmp_path / "protected", namespace="source", protected=True) as value:
        assert value.source_ref in set(value.receipts.known(value.context.episode_id, baseline=True))
        assert value.artifact_ref not in set(value.receipts.known(value.context.episode_id, baseline=True))
        assert_denied(read_input(value), "artifact_not_received")


@pytest.mark.parametrize("denied", [False, True])
def test_explicit_protected_artifact_delivery_still_needs_actual_owner_verdict(tmp_path, denied):
    with actual_received_input_owner(tmp_path, namespace="source", protected=True, grant_artifact=True) as value:
        if denied: value.denied.add((value.artifact_ref, "artifact"))
        result = read_input(value)
        if denied: assert_denied(result, "artifact_denied")
        else: assert result["input"]["content"]["state"] == "decoded"
        assert (value.source_ref, "source") in value.verdicts and (value.artifact_ref, "artifact") in value.verdicts


@pytest.mark.parametrize("kind", ["unreceived", "denied"])
def test_authority_denial_never_reads_or_returns_private_record_metadata(tmp_path, monkeypatch, kind):
    with actual_received_input_owner(tmp_path, namespace="source", deliver=kind != "unreceived") as value:
        if kind == "denied": value.denied.add((value.reference, value.namespace))
        actual = value.store.get
        def guard(reference):
            assert reference != value.reference, "denied reference body was accessed"
            return actual(reference)
        monkeypatch.setattr(value.store, "get", guard)
        assert_denied(read_input(value), "reference_not_received" if kind == "unreceived" else "reference_denied")


def test_late_parent_receipt_does_not_expand_old_child_but_new_child_receives_it(tmp_path):
    with actual_received_input_owner(tmp_path, deliver=False) as value:
        value.receipts.receive(value.parent.episode_id, [value.reference], kind="initial")
        assert_denied(read_input(value), "reference_not_received")
        later = value.child(1)
        assert read_input(value, context=later)["input"]["file"]["artifact_ref"] == value.artifact_ref


@pytest.mark.parametrize("namespace", ["artifact", "source"])
def test_actual_store_treats_received_foreign_target_source_bytes_as_reusable_context(tmp_path, namespace):
    with actual_received_input_owner(tmp_path, deliver=False, two_targets=True) as value:
        first, second = sorted(value.store.targets(), key=lambda row: row["name"])
        source = value.store.get(second["source_ref"])
        artifact = source["artifact_ref"]
        reference = artifact if namespace == "artifact" else source["id"]
        value.receipts.receive(value.parent.episode_id, [reference], kind="initial")
        child = value.child(1, child_scope={"subject_refs": [first["id"]]})
        assert second["id"] not in child.scope["subject_refs"]
        assert value.store.get(second["id"])["sequence_ref"] == artifact
        # Actual Store artifact visibility gathers attachments globally. A
        # source has no biological record_roots merely by supplying target B.
        assert value.store.roots(source["id"]) == []
        assert value.store.reference_subset([source["id"], artifact], plain(child.scope)) == [source["id"], artifact]
        assert artifact in value.store.references(plain(child.scope))["artifact"]
        result = value.binding.read_received(child, reference, namespace, tag_key="version")
        assert result["input"]["file"]["artifact_ref"] == artifact
        assert result["input"]["byte_verification"] == "verified"
        # Genuine supplied DNA bytes are retained; no JSON measurements or
        # invented A/B scientific association are manufactured from them.
        assert result["input"]["content"]["state"] == "decode_failed"
        assert result["failure"] == {"stage": "decode", "code": "invalid_json"}


def test_explicit_received_unattached_file_is_usable_without_biological_attachment(tmp_path):
    with actual_received_input_owner(tmp_path, deliver=False, two_targets=True) as value:
        first = sorted(value.store.targets(), key=lambda row: row["name"])[0]
        raw = b'{"version":"standalone_v1","samples":[2]}'
        artifact = value.store.artifact(raw, "application/json")
        value.receipts.receive(value.parent.episode_id, [artifact], kind="initial")
        child = value.child(1, child_scope={"subject_refs": [first["id"]]})
        assert value.store.reference_subset([artifact], plain(child.scope)) == []
        result = value.binding.read_received(child, artifact, "artifact", tag_key="version")
        assert result["failure"] is None and result["input"]["byte_verification"] == "verified"
        assert result["input"]["content"]["value"] == json.loads(raw)
        assert value.store.roots(artifact) == []


@pytest.mark.parametrize("change", ["context", "role", "commission", "inheritance", "scope"])
def test_actual_context_commission_inheritance_and_store_scope_fail_without_metadata(tmp_path, change):
    with actual_received_input_owner(tmp_path) as value:
        context = value.context
        if change == "context":
            request = plain(context.request); request["message"]["episode_assignment"]["foreign"] = True
            context = BindingContext(context.run_id, context.episode_id, context.role, context.path,
                context.scope, request["message"]["episode_assignment"], request)
        elif change == "role":
            with pytest.raises(ValueError, match="^binding_context_path_must_match_role$"):
                BindingContext(context.run_id, context.episode_id, "annotation", context.path,
                    context.scope, context.assignment, context.request)
            return
        elif change == "commission":
            selected = json.loads(value.store.db.execute("SELECT action FROM runtime_actions WHERE episode_id=?", (value.parent.episode_id,)).fetchone()[0])
            selected["assignment"] = {"foreign": "selection"}
            value.store.db.execute("UPDATE runtime_actions SET action=? WHERE episode_id=?", (canonical(selected), value.parent.episode_id))
        elif change == "inheritance":
            request = plain(context.request); request["message"]["knowledge_inheritance"]["through_receipt_index"] += 1
            value.store.db.execute("UPDATE runtime_episodes SET request=? WHERE episode_id=?", (canonical(request), context.episode_id))
            context = BindingContext(context.run_id, context.episode_id, context.role, context.path, context.scope, context.assignment, request)
        else:
            # Both scopes are valid Store scopes, but the commissioned child's
            # full interval exceeds its actual parent's recorded half interval.
            parent_request = plain(value.parent.request)
            parent_request["message"]["scope"]["segments"] = [dict(target_ref=value.scope["subject_refs"][0], start=0, end=4, unit="nt")]
            value.store.db.execute("UPDATE runtime_episodes SET request=? WHERE episode_id=?", (canonical(parent_request), value.parent.episode_id))
        code = {"context": "invalid_context", "role": "invalid_context", "commission": "invalid_commission", "inheritance": "invalid_inheritance", "scope": "scope_denied"}[change]
        assert_denied(read_input(value, context=context), code)


@pytest.mark.parametrize("change", ["missing", "changed"])
def test_byte_failure_after_authority_preserves_admitted_metadata_without_decoded_content(tmp_path, change):
    with actual_received_input_owner(tmp_path, namespace="source") as value:
        metadata = value.store.get(value.artifact_ref)
        path = value.store.path / "artifacts" / metadata["sha256"][:2] / metadata["sha256"]
        if change == "missing": path.unlink()
        else: path.write_bytes(b'{"different":true}')
        result = read_input(value); item = result["input"]
        assert item["file"]["artifact_ref"] == value.artifact_ref and item["witness"]["reference"] == value.source_ref
        assert item["artifact_record"] == metadata
        assert item["content"]["state"] == "not_read" and item["content"]["value"] is None
        assert result["failure"]["code"] == ("artifact_bytes_unavailable" if change == "missing" else "artifact_identity_conflict")


@pytest.mark.parametrize("raw,code", [(b"\xff", "invalid_utf8"), (b'{"bad":', "invalid_json"),
    (b'{"x":1,"x":2}', "duplicate_json_key"), (b'{"x":NaN}', "nonfinite_json"),
    (b"1e9999", "nonfinite_json"), (b"1e-9999", "unrepresentable_json_number"),
    (b'{"version":"supplied_v1","samples":[1],"calibrations":[{"label":"\\ud800"}]}', "invalid_json"),
    (b'{"\\udfff":1,"samples":[1]}', "invalid_json")])
def test_strict_decode_failure_retains_verified_file_and_witness(tmp_path, raw, code):
    with actual_received_input_owner(tmp_path, raw=raw) as value:
        result = read_input(value)
        assert result["input"]["file"]["artifact_ref"] == value.artifact_ref
        assert result["input"]["byte_verification"] == "verified"
        assert result["input"]["content"]["state"] == "decode_failed"
        assert result["failure"] == {"stage": "decode", "code": code}


@pytest.mark.parametrize("raw", [b"null", b'{"schema":"other_contract","samples":[1]}', b'{"version":4,"samples":[1]}'])
def test_decoded_null_and_bad_or_missing_tag_remain_distinct_from_no_content(tmp_path, raw):
    with actual_received_input_owner(tmp_path, raw=raw) as value:
        result = read_input(value); content = result["input"]["content"]
        assert content["state"] == "decoded" and content["value"] == json.loads(raw)
        assert content["document_version"] is None and result["failure"] is None
        if content["value"] is not None: assert content["value"]["samples"] == [1]


def test_source_file_relationship_uses_actual_immutable_identity_not_changed_source_assertion(tmp_path):
    with actual_received_input_owner(tmp_path, namespace="source") as value:
        record = value.store.get(value.source_ref); record["artifact_ref"] = value.text_ref
        value.store.db.execute("UPDATE records SET data=? WHERE id=?", (canonical(record), value.source_ref))
        assert_denied(read_input(value), "source_identity_conflict")


@pytest.mark.parametrize("field", ["file_size", "record_revision", "source_version", "content_tag", "extra"])
def test_pure_contract_rejects_inconsistent_envelope_without_claiming_receipt_authority(tmp_path, field):
    with actual_received_input_owner(tmp_path, namespace="source") as value:
        result = deepcopy(read_input(value))
        if field == "file_size": result["input"]["file"]["size_bytes"] = True
        elif field == "record_revision": result["input"]["witness"]["record_revision"] = 0
        elif field == "source_version": result["input"]["witness"]["source_version"] = "invented_version"
        elif field == "content_tag": result["input"]["content"]["document_version"] = "invented_tag"
        else: result["attempt_ref"] = "invented_execution"
        with pytest.raises(ValueError): contracts.validate_molecular_sequence_received_input(result)


def test_received_input_read_creates_no_action_receipt_record_artifact_or_grant(tmp_path):
    with actual_received_input_owner(tmp_path, namespace="source") as value:
        tables = ("records", "artifacts", "runtime_actions", "runtime_record_receipts", "runtime_receipt_inheritance")
        before = {name: value.store.db.execute("SELECT count(*) FROM " + name).fetchone()[0] for name in tables}
        known = set(value.receipts.known(value.context.episode_id)); changes = value.store.db.total_changes
        first = read_input(value); second = read_input(value)
        assert first == second
        assert before == {name: value.store.db.execute("SELECT count(*) FROM " + name).fetchone()[0] for name in tables}
        assert changes == value.store.db.total_changes and known == set(value.receipts.known(value.context.episode_id))


def test_valid_escaped_surrogate_pair_preserves_decoded_unicode_and_exact_bytes(tmp_path):
    raw = b'{"version":"supplied_v1","samples":["\\ud83d\\ude00"]}'
    with actual_received_input_owner(tmp_path, raw=raw) as value:
        result = read_input(value)
        assert result["failure"] is None and result["input"]["byte_verification"] == "verified"
        assert result["input"]["content"]["value"]["samples"] == ["\U0001f600"]
        assert value.store.get_artifact(result["input"]["file"]["artifact_ref"]) == raw


@pytest.mark.parametrize("kind", ["string", "key", "cycle"])
def test_pure_validation_normalizes_malformed_unicode_and_recursive_data_to_value_error(kind):
    value = {"bad": "\ud800"} if kind == "string" else {"\udfff": 1} if kind == "key" else []
    if kind == "cycle": value.append(value)
    with pytest.raises(ValueError, match="molecular_sequence_received_input_invalid"):
        contracts.validate_molecular_sequence_received_input(value)


@pytest.mark.parametrize("namespace", ["artifact", "source"])
@pytest.mark.parametrize("raw,file_format", [
    (b"chain 1 chr1 10 + 0 4 chr2 10 + 0 4 1\n4\n", "ucsc_chain"),
    (gzip.compress(b"native retained chain bytes\n", mtime=0), "ucsc_chain_gzip"),
    (b"\xff\x00\x81not JSON" * 100000, "binary_native"),
    (b"plain bytes without gzip encoding", "caller_selected_gzip_label"),
], ids=["chain", "gzip", "large_binary", "selected_label"])
def test_raw_received_file_returns_verified_original_path_without_decode_or_format_inference(tmp_path, monkeypatch, namespace, raw, file_format):
    with actual_received_input_owner(tmp_path, namespace=namespace, raw=raw) as value:
        def forbidden(*args, **kwargs):
            pytest.fail("raw received-file reading must not materialize or decode JSON")
        monkeypatch.setattr(bindings, "read_bytes", forbidden)
        monkeypatch.setattr(bindings, "decode_molecular_sequence_input", forbidden)
        result, path = value.binding.read_received_file(value.context, value.reference, namespace, file_format=file_format)
        validate_schema(result, contracts.molecular_sequence_received_file_schema())
        assert result == contracts.validate_molecular_sequence_received_file(result)
        assert isinstance(path, Path)
        with path.open("rb") as stream:
            assert stream.read() == raw
        item = result["input"]
        assert result["failure"] is None and item["byte_verification"] == "verified"
        assert set(item) == {"receiver", "scope", "inheritance_manifest", "witness", "file", "artifact_record", "byte_verification"}
        assert item["file"] == {"artifact_ref": value.artifact_ref,
            "sha256": value.artifact_ref.removeprefix("artifact_"), "size_bytes": len(raw), "format": file_format}
        assert item["artifact_record"]["media_type"] == "application/octet-stream"
        assert path == value.store.path / "artifacts" / item["file"]["sha256"][:2] / item["file"]["sha256"]


@pytest.mark.parametrize("namespace", ["artifact", "source"])
@pytest.mark.parametrize("raw", [b'{"version":"supplied_v1","samples":[1]}', b"\xff", b'{"x":1,"x":2}'])
def test_raw_and_json_readers_share_exact_admitted_metadata_with_distinct_decode_outcomes(tmp_path, namespace, raw):
    with actual_received_input_owner(tmp_path, namespace=namespace, raw=raw) as value:
        raw_result, path = value.binding.read_received_file(value.context, value.reference, namespace, file_format="json")
        json_result = read_input(value)
        json_metadata = {key: field for key, field in json_result["input"].items() if key not in {"tag_key", "content"}}
        assert canonical(raw_result["input"]) == canonical(json_metadata)
        assert path is not None and raw_result["failure"] is None
        assert json_result["version"] == "molecular_sequence_received_input_result_v1"
        assert raw_result["version"] == "molecular_sequence_received_file_result_v1"
        if raw.startswith(b'{"version"'):
            assert json_result["failure"] is None and json_result["input"]["content"]["state"] == "decoded"
        else:
            assert json_result["failure"]["stage"] == "decode"
            assert json_result["input"]["content"]["state"] == "decode_failed"


@pytest.mark.parametrize("change", ["missing", "changed_digest", "metadata_size", "metadata_hash"])
def test_raw_byte_and_metadata_failures_preserve_only_actually_admitted_evidence(tmp_path, change):
    raw = b"non-JSON retained native bytes"
    with actual_received_input_owner(tmp_path, namespace="source", raw=raw) as value:
        before = value.store.get(value.artifact_ref)
        path = value.store.path / "artifacts" / before["sha256"][:2] / before["sha256"]
        if change == "missing":
            path.unlink()
        elif change == "changed_digest":
            path.write_bytes(b"X" + raw[1:])
            assert path.stat().st_size == before["size"]
        elif change == "metadata_size":
            value.store.db.execute("UPDATE artifacts SET size=? WHERE id=?", (before["size"] + 1, value.artifact_ref))
        else:
            value.store.db.execute("UPDATE artifacts SET sha256=? WHERE id=?", ("0" * 64, value.artifact_ref))
        result, returned = value.binding.read_received_file(value.context, value.reference, "source", file_format="native_chain")
        assert returned is None
        contracts.validate_molecular_sequence_received_file(result)
        validate_schema(result, contracts.molecular_sequence_received_file_schema())
        code = "artifact_bytes_unavailable" if change == "missing" else "artifact_identity_conflict"
        assert result["failure"] == {"stage": "artifact", "code": code}
        if change == "metadata_hash":
            assert result["input"] is None
        else:
            item = result["input"]
            assert item["witness"]["reference"] == value.source_ref
            assert item["artifact_record"] == value.store.get(value.artifact_ref)
            assert item["file"]["size_bytes"] == before["size"] + (change == "metadata_size")
            assert item["byte_verification"] == ("unavailable" if change == "missing" else "identity_conflict")
        # The old JSON API retains exactly the same authority/byte failure,
        # adding only its existing no-content fields when metadata is admitted.
        old = read_input(value)
        assert old["failure"] == result["failure"]
        if old["input"] is not None:
            old_metadata = {key: field for key, field in old["input"].items() if key not in {"tag_key", "content"}}
            old_metadata["file"]["format"] = "native_chain"
            assert canonical(old_metadata) == canonical(result["input"])
            assert old["input"]["content"]["state"] == "not_read"
        else:
            assert result["input"] is None


@pytest.mark.parametrize("kind,code", [
    ("unreceived", "reference_not_received"), ("source_denied", "reference_denied"),
    ("native_unreceived", "artifact_not_received"), ("native_denied", "artifact_denied"),
    ("source_changed", "source_identity_conflict"), ("wrong_namespace", "reference_type_conflict"),
])
def test_raw_authority_preserves_source_and_native_file_receipts_and_denials(tmp_path, monkeypatch, kind, code):
    with actual_received_input_owner(tmp_path, namespace="source", deliver=kind != "unreceived",
            protected=kind in {"native_unreceived", "native_denied"}, grant_artifact=kind == "native_denied") as value:
        namespace = "artifact" if kind == "wrong_namespace" else "source"
        if kind == "source_denied":
            value.denied.add((value.source_ref, "source"))
        elif kind == "native_denied":
            value.denied.add((value.artifact_ref, "artifact"))
        elif kind == "source_changed":
            record = value.store.get(value.source_ref); record["artifact_ref"] = value.text_ref
            value.store.db.execute("UPDATE records SET data=? WHERE id=?", (canonical(record), value.source_ref))
        def forbidden(*args, **kwargs):
            pytest.fail("denied raw-file authority must not access native bytes")
        monkeypatch.setattr(bindings, "retained_native_file", forbidden)
        if kind in {"unreceived", "source_denied"}:
            actual_get = value.store.get
            def private_record_guard(reference):
                assert reference != value.source_ref, "denied Source body leaked"
                return actual_get(reference)
            monkeypatch.setattr(value.store, "get", private_record_guard)
        result, path = value.binding.read_received_file(value.context, value.reference, namespace, file_format="native_chain")
        assert path is None and result["input"] is None
        assert result["failure"] == {"stage": "authority", "code": code}
        assert result["selection"] == {"reference": value.reference, "namespace": namespace}
        contracts.validate_molecular_sequence_received_file(result)
        old = value.binding.read_received(value.context, value.reference, namespace, tag_key="version")
        assert old["input"] is None and old["failure"] == result["failure"]


def test_raw_inherited_receipt_boundary_excludes_late_file_until_new_commission(tmp_path):
    with actual_received_input_owner(tmp_path, raw=b"chain bytes", deliver=False) as value:
        value.receipts.receive(value.parent.episode_id, [value.reference], kind="initial")
        denied, path = value.binding.read_received_file(value.context, value.reference, "artifact", file_format="chain")
        assert path is None and denied["input"] is None
        assert denied["failure"]["code"] == "reference_not_received"
        later = value.child(1)
        received, path = value.binding.read_received_file(later, value.reference, "artifact", file_format="chain")
        assert path is not None and received["input"]["receiver"]["episode_id"] == later.episode_id
        assert received["input"]["inheritance_manifest"] == value.receipts.manifest(later.episode_id)


@pytest.mark.parametrize("namespace", ["source", "artifact"])
def test_raw_received_foreign_target_context_remains_usable_without_invented_subject_association(tmp_path, namespace):
    with actual_received_input_owner(tmp_path, deliver=False, two_targets=True) as value:
        first, second = sorted(value.store.targets(), key=lambda row: row["name"])
        source = value.store.get(second["source_ref"])
        reference = source["id"] if namespace == "source" else source["artifact_ref"]
        value.receipts.receive(value.parent.episode_id, [reference], kind="initial")
        child = value.child(1, child_scope={"subject_refs": [first["id"]]})
        result, path = value.binding.read_received_file(child, reference, namespace, file_format="raw_dna")
        assert path is not None and result["failure"] is None
        assert result["input"]["file"]["artifact_ref"] == source["artifact_ref"]
        assert result["input"]["scope"] == value.store.validate_scope(plain(child.scope))
        assert second["id"] not in result["input"]["scope"]["subject_refs"]


@pytest.mark.parametrize("change", ["host_path", "file_path", "content", "decode_failure", "empty_format", "control_format"])
def test_raw_private_contract_rejects_paths_decoding_and_invalid_processing_labels(tmp_path, change):
    with actual_received_input_owner(tmp_path, raw=b"native bytes") as value:
        result, path = value.binding.read_received_file(value.context, value.reference, "artifact", file_format="chain")
        assert path is not None
        result = deepcopy(result)
        if change == "host_path": result["input"]["path"] = str(path)
        elif change == "file_path": result["input"]["file"]["path"] = str(path)
        elif change == "content": result["input"]["content"] = {"value": "native bytes"}
        elif change == "decode_failure": result["failure"] = {"stage": "decode", "code": "invalid_json"}
        elif change == "empty_format": result["input"]["file"]["format"] = ""
        else: result["input"]["file"]["format"] = "chain\tlabel"
        with pytest.raises(ValueError): contracts.validate_molecular_sequence_received_file(result)
        with pytest.raises(ValueError): validate_schema(result, contracts.molecular_sequence_received_file_schema())


@pytest.mark.parametrize("file_format", [None, "", True, "chain\tlabel", "chain\n", "chain\0"])
def test_raw_invalid_processing_selection_fails_before_authority_read(tmp_path, monkeypatch, file_format):
    with actual_received_input_owner(tmp_path) as value:
        def forbidden(*args, **kwargs):
            pytest.fail("invalid processing selection must fail before authority lookup")
        monkeypatch.setattr(value.binding, "_authority", forbidden)
        with pytest.raises(ValueError, match="^molecular_sequence_input_invalid_selection$"):
            value.binding.read_received_file(value.context, value.reference, "artifact", file_format=file_format)


def test_raw_read_creates_no_action_receipt_record_artifact_or_grant(tmp_path):
    with actual_received_input_owner(tmp_path, raw=b"native bytes", namespace="source") as value:
        tables = ("records", "artifacts", "runtime_actions", "runtime_record_receipts", "runtime_receipt_inheritance")
        before = {name: value.store.db.execute("SELECT count(*) FROM " + name).fetchone()[0] for name in tables}
        known = set(value.receipts.known(value.context.episode_id)); changes = value.store.db.total_changes
        first, first_path = value.binding.read_received_file(value.context, value.reference, "source", file_format="chain")
        second, second_path = value.binding.read_received_file(value.context, value.reference, "source", file_format="chain")
        assert first == second and first_path == second_path and first_path is not None
        assert before == {name: value.store.db.execute("SELECT count(*) FROM " + name).fetchone()[0] for name in tables}
        assert changes == value.store.db.total_changes and known == set(value.receipts.known(value.context.episode_id))
