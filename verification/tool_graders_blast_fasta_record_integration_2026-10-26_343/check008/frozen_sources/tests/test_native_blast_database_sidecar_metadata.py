"""Synthetic N capture compatibility, including retained actual producer bytes.

These are metadata custody tests, not native scientific BLAST executions. The
335 fixtures pin unchanged N313/N331 outputs and M332's original counterexample.
The equal-content test runs only the existing explicitly synthetic producer
fixture command. No native6 wrapper is fabricated for a standard job.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode import native_blast_database_contracts as native
from gene_annotation_episode import native_blast_database_metadata as metadata
from gene_annotation_episode import native_blast_standard_database_contracts as standard


PACKET = (Path(__file__).resolve().parents[1] / "verification" /
          "tool_graders_blast_sidecar_metadata_contract_fix_2026-10-26_335")
ROLES = ("preparation_input_manifest", "offline_configuration")
CASES = ("native6", "native6_shared", "standard_blastn", "standard_blastp")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def metadata_key(database_key, identity, role="metadata"):
    # Independent literal oracle from the existing N313/005 contract.
    return "database-metadata-" + sha(canonical(dict(database_key=database_key,
                                                   role=role, identity=identity)))


def retained(record):
    path = PACKET / record["retained_path"]
    raw = path.read_bytes()
    assert sha(raw) == record["sha256"] and len(raw) == record["size_bytes"]
    return path, raw


def load_case(name):
    record = json.loads((PACKET / "fixtures/INDEX.json").read_bytes())[name]
    _, raw_bundle = retained(record["bundle"])
    _, raw_plan = retained(record["plan"])
    bundle, plan = json.loads(raw_bundle), json.loads(raw_plan)
    operation = "native_blast_database" if name.startswith("native6") else "native_blast_standard_database"
    job = plan["requested_job"][operation]
    entries, contents = [], {}
    for original, pin in zip(bundle["artifacts"], record["artifacts"], strict=True):
        assert original["artifact_key"] == pin["artifact_key"]
        path, raw = retained(pin)
        assert sha(raw) == original["sha256"] and len(raw) == original["size_bytes"]
        entry = dict(original, path=str(path), artifact_ref="artifact-" + sha(raw),
                     source_ref="source-" + original["artifact_key"])
        entries.append(entry)
        contents[entry["artifact_key"]] = raw
    case = dict(job=job, bundle=bundle, attempt_identity=record["attempt_identity"], contents=contents,
        artifact_catalog=dict(bundle_source_ref="source-retained-" + name,
            bundle_artifact_ref="artifact-" + sha(raw_bundle), bundle_sha256=sha(raw_bundle),
            entries=entries, retained_sources=[]))
    validate_bundle(case)
    return case


def validate_bundle(case):
    validator = (native.validate_native_blast_database_bundle if case["job"]["version"] ==
                 "native_blast_database_job_v1" else standard.validate_standard_blast_database_bundle)
    assert validator(case["bundle"], original_job=case["job"],
                     attempt_identity=case["attempt_identity"]) == case["bundle"]


def sidecar(case, role):
    database_key = case["job"]["databases"][0]["database_key"]
    capture = next(r for r in case["bundle"]["database_manifest"] if r["database_key"] == database_key)
    slot = next(r for r in capture["sidecar_artifacts"] if r["role"] == role)
    entry = next(r for r in case["artifact_catalog"]["entries"] if r["artifact_key"] == slot["artifact_key"])
    assert entry["role"] == "metadata"
    assert slot["artifact_key"] == metadata_key(database_key, slot["identity"])
    return database_key, slot, entry


def payload_for(case, roles=ROLES):
    payload = dict(schema="native_blast_database_query_metadata_v1", documents=[], sequence_records=[],
        effective_msa_masters=[], master_subjects=[], search_bindings=[], target_contexts=[])
    docs = []
    for index, role in enumerate(roles):
        database_key, _, entry = sidecar(case, role)
        declaration = dict(document_key=role, artifact=dict(kind="database_sidecar",
            database_key=database_key, role=role), format="text")
        payload["documents"].append(declaration)
        payload["sequence_records"].append(dict(input_key=case["job"]["query"]["input_key"],
            record_ordinal=index, subject_ref=None, identity=None, source=dict(source_ref=role, pointer="")))
        docs.append(dict(declaration, **{k: entry[k] for k in
            ("artifact_key", "artifact_ref", "source_ref", "sha256", "size_bytes")},
            contents=case["contents"][entry["artifact_key"]]))
    descriptor = dict(input_key="sidecar-evidence", consumer="query_identity", schema_id=payload["schema"],
        artifact_ref="artifact-" + sha(canonical(payload)), sha256=sha(canonical(payload)),
        size_bytes=len(canonical(payload)), origin="selected_results_input")
    catalog = dict(descriptor=descriptor, documents=docs, primary_reports=[],
        **{k: case["artifact_catalog"][k] for k in ("bundle_source_ref", "bundle_artifact_ref")})
    return payload, descriptor, catalog


def validate(case, payload, descriptor, catalog):
    return metadata.validate_native_blast_database_metadata_payload(payload, descriptor=descriptor,
        document_catalog=catalog, job=case["job"])


def prepare(case, payload, tmp_path):
    """Real native6 preparation, with captured files and selected metadata bytes."""
    assert case["job"]["version"] == "native_blast_database_job_v1"
    raw = canonical(payload)
    path = tmp_path / "selected-sidecar-metadata.json"
    path.write_bytes(raw)
    descriptor = dict(input_key="sidecar-evidence", consumer="query_identity", schema_id=payload["schema"],
        artifact_ref="artifact-" + sha(raw), sha256=sha(raw), size_bytes=len(raw), origin="selected_results_input")
    catalog = deepcopy(case["artifact_catalog"])
    catalog["retained_sources"].append(dict(source_ref="source-selected-sidecar-metadata", path=str(path),
        **{k: descriptor[k] for k in ("artifact_ref", "sha256", "size_bytes")}))
    return metadata.prepare_native_blast_database_inputs(job=case["job"], bundle=case["bundle"],
        artifact_catalog=catalog, metadata_payloads=[dict(descriptor=descriptor, payload=payload)], subject_snapshots=[])


def details(result):
    return {row["detail_code"] for row in result["issues"]}


@pytest.mark.parametrize("name", CASES)
@pytest.mark.parametrize("role", ROLES)
def test_public_validator_accepts_real_retained_producer_sidecars(name, role, tmp_path, monkeypatch):
    case = load_case(name)  # Independent public N validation is part of every case.
    payload, descriptor, catalog = payload_for(case, (role,))
    original = deepcopy((case["job"], payload, descriptor, catalog))

    def forbidden(*args, **kwargs):
        pytest.fail("supplied-byte metadata validation performed I/O, execution or native6 job adaptation")

    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(native, "validate_native_blast_database_job", forbidden)
    result = validate(case, payload, descriptor, catalog)
    (tmp_path / "public-validation.json").write_text(json.dumps(result, indent=2))
    assert result["status"] == "valid", result["issues"]
    assert result["issues"] == []
    assert result["normalized"]["documents"] == [{k: v for k, v in catalog["documents"][0].items() if k != "contents"}]
    assert result["normalized"]["sequence_records"][0]["source"] == dict(
        source_ref=catalog["documents"][0]["source_ref"], pointer="")
    assert (case["job"], payload, descriptor, catalog) == original


@pytest.mark.parametrize("name", ("native6", "native6_shared"))
@pytest.mark.parametrize("roles", [(ROLES[0],), (ROLES[1],), ROLES])
def test_native6_preparation_uses_both_original_sidecar_roles(name, roles, tmp_path):
    case = load_case(name)
    payload, _, _ = payload_for(case, roles)
    result = prepare(case, payload, tmp_path)
    (tmp_path / "prepared.json").write_text(json.dumps(result, indent=2))
    validation = result["metadata"][0]
    assert validation["status"] == "valid"
    assert validation["issues"] == [], validation["issues"]
    assert len(validation["normalized"]["sequence_records"]) == len(roles)
    assert [d["artifact"]["role"] for d in validation["normalized"]["documents"]] == list(roles)
    assert len(result["resolved_documents"]) == len(roles)
    assert validation["payload"] == payload
    assert validation["normalization_map"] == [
        *[dict(normalized_pointer=f"/documents/{i}", payload_pointer=f"/documents/{i}") for i in range(len(roles))],
        *[dict(normalized_pointer=f"/sequence_records/{i}", payload_pointer=f"/sequence_records/{i}") for i in range(len(roles))]]
    if name == "native6_shared" and len(roles) == 2:
        docs = validation["normalized"]["documents"]
        assert docs[0]["artifact_key"] == docs[1]["artifact_key"]
        assert docs[0]["artifact_ref"] == docs[1]["artifact_ref"]
        assert docs[0]["artifact"] != docs[1]["artifact"]


def counterexample332():
    pin = json.loads((PACKET / "fixtures/INDEX.json").read_bytes())["standard332"]["counterexample"]
    _, raw = retained(pin)
    saved = json.loads(raw)
    inputs = saved["inputs"]
    case = dict(job=inputs["job"], bundle=inputs["bundle"], artifact_catalog=inputs["artifact_catalog"],
                attempt_identity=inputs["attempt_identity"])
    validate_bundle(case)
    payload, descriptor = (deepcopy(inputs["metadata_payloads"][0][k]) for k in ("payload", "descriptor"))
    assert bytes.fromhex(saved["contents_hex"][descriptor["artifact_ref"]]) == canonical(payload)
    docs = []
    for declaration in payload["documents"]:
        _, _, row = sidecar(case, declaration["artifact"]["role"])
        docs.append(dict(declaration, **{k: row[k] for k in
            ("artifact_key", "artifact_ref", "source_ref", "sha256", "size_bytes")},
            contents=bytes.fromhex(saved["contents_hex"][row["artifact_ref"]])))
    catalog = dict(descriptor=descriptor, documents=docs, primary_reports=[],
        **{k: inputs["artifact_catalog"][k] for k in ("bundle_source_ref", "bundle_artifact_ref")})
    return case, payload, descriptor, catalog, saved["result"]


def test_retained332_n_valid_counterexample_and_literal_pointer(tmp_path):
    case, payload, descriptor, catalog, historical = counterexample332()
    assert historical["status"] == "invalid"
    assert "sidecar_capture_key_conflict" in details(historical)
    result = validate(case, payload, descriptor, catalog)
    (tmp_path / "counterexample332-after.json").write_text(json.dumps(result, indent=2))
    assert result["status"] == "valid" and not result["issues"], result["issues"]
    payload["sequence_records"][0]["source"]["pointer"] = "/does-not-exist"
    invalid = validate(case, payload, descriptor, catalog)
    assert invalid["status"] == "invalid"
    assert "literal_json_pointer_unresolved" in details(invalid)


@pytest.mark.parametrize("name", ("native6", "standard_blastp"))
@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("change,expected", [
    ("arbitrary_key", "sidecar_capture_key_conflict"),
    ("logical_role_key", "sidecar_capture_key_conflict"),
    ("selected_path", "sidecar_capture_key_conflict"),
    ("selected_artifact_ref", "sidecar_capture_key_conflict"),
    ("selected_absent", "sidecar_capture_key_conflict"),
    ("document_hash", "selected_document_digest_conflict"),
    ("document_size", "selected_document_digest_conflict"),
    ("document_bytes", "document_bytes_conflict"),
    ("source_key", "document_key_undeclared"),
    ("source_pointer", "source_locator_not_supported"),
    ("document_absent", "document_bytes_unavailable"),
    ("duplicate_document", "document_key_duplicate"),
])
def test_public_sidecar_guards_are_preserved(name, role, change, expected):
    case = load_case(name)
    payload, descriptor, catalog = payload_for(case, (role,))
    database = case["job"]["databases"][0]
    owner, field = ((database["manifest"]["preparation"], "input_manifest") if role == ROLES[0]
                    else (database["manifest"]["access"], "offline_configuration"))
    document = catalog["documents"][0]
    if change == "arbitrary_key":
        document["artifact_key"] = "unselected-capture"
    elif change == "logical_role_key":
        document["artifact_key"] = metadata_key(database["database_key"], owner[field], role)
    elif change == "selected_path":
        owner[field]["path"] += ".other-original-source"
    elif change == "selected_artifact_ref":
        owner[field]["artifact_ref"] = "other-original-artifact"
    elif change == "selected_absent":
        owner[field] = None
    elif change == "document_hash":
        document["sha256"] = "0" * 64
    elif change == "document_size":
        document["size_bytes"] += 1
    elif change == "document_bytes":
        document["contents"] += b"changed"
    elif change == "source_key":
        payload["sequence_records"][0]["source"]["source_ref"] = "unselected-source"
    elif change == "source_pointer":
        payload["sequence_records"][0]["source"]["pointer"] = "/invented-location"
    elif change == "document_absent":
        catalog["documents"] = []
    elif change == "duplicate_document":
        payload["documents"].append(deepcopy(payload["documents"][0]))
    result = validate(case, payload, descriptor, catalog)
    assert expected in details(result)
    assert result["normalized"] is None or not result["normalized"]["sequence_records"]


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("change,expected", [
    ("selected_identity", "sidecar_identity_conflict"),
    ("wrong_capture_key", "metadata_capture_key_conflict"),
    ("absent_capture", "artifact_bytes_unavailable"),
    ("duplicate_role", "sidecar_role_unresolved"),
    ("changed_bytes", "artifact_digest_conflict"),
])
def test_native6_resolver_guards_preserve_valid_sibling(tmp_path, role, change, expected):
    case = load_case("native6")
    payload, _, _ = payload_for(case)
    _, slot, entry = sidecar(case, role)
    if change == "selected_identity":
        slot["identity"]["path"] += ".wrong"
    elif change == "wrong_capture_key":
        slot["artifact_key"] = "wrong-selected-capture"
    elif change == "absent_capture":
        slot["artifact_key"] = None
    elif change == "duplicate_role":
        case["bundle"]["database_manifest"][0]["sidecar_artifacts"].append(deepcopy(slot))
    elif change == "changed_bytes":
        corrupt = tmp_path / "changed-source"
        corrupt.write_bytes(case["contents"][entry["artifact_key"]] + b"changed")
        entry["path"] = str(corrupt)
    result = prepare(case, payload, tmp_path)["metadata"][0]
    assert expected in details(result)
    sibling = ROLES.index(role) ^ 1
    assert [r["record_ordinal"] for r in result["normalized"]["sequence_records"]] == [sibling]
    assert dict(normalized_pointer="/sequence_records/0", payload_pointer=f"/sequence_records/{sibling}") in result["normalization_map"]


@pytest.mark.parametrize("family", ("native6", "standard5"))
def test_identical_bytes_at_distinct_role_paths_keep_original_relations(tmp_path, family):
    # Execute the existing N fixture's deliberately synthetic script, never BLAST.
    if family == "native6":
        import test_native_blast_database_driver as producer
        operation = "native_blast_database"
    else:
        import test_native_blast_standard_database_driver as producer
        operation = "native_blast_standard_database"
    path, plan, _ = producer.fixture(tmp_path / "synthetic-producer")
    database = plan["requested_job"][operation]["databases"][0]
    manifest = database["manifest"]
    first = manifest["preparation"]["input_manifest"]
    second = manifest["access"]["offline_configuration"]
    manifest["access"]["offline_configuration"] = producer.write(second["path"], Path(first["path"]).read_bytes())
    database["manifest_file"] = producer.save_json(Path(database["manifest_file"]["path"]), manifest)
    producer.refresh_plan(path, plan)
    process, bundle = producer.run_fixture(path, plan)
    assert process.returncode == 0, process.stderr.decode()
    assert producer.validate_bundle(bundle, plan) == bundle
    entries, contents = [], {}
    for row in bundle["artifacts"]:
        source = path.parent / row["relative_path"]
        raw = source.read_bytes()
        assert sha(raw) == row["sha256"] and len(raw) == row["size_bytes"]
        contents[row["artifact_key"]] = raw
        entries.append(dict(row, path=str(source), artifact_ref="artifact-" + sha(raw),
                            source_ref="source-" + row["artifact_key"]))
    case = dict(job=plan["requested_job"][operation], bundle=bundle, contents=contents,
        artifact_catalog=dict(bundle_source_ref="source-synthetic-equal-bytes", bundle_artifact_ref="bundle-synthetic-equal-bytes",
            bundle_sha256=sha(canonical(bundle)), entries=entries, retained_sources=[]))
    payload, descriptor, catalog = payload_for(case)
    sides = bundle["database_manifest"][0]["sidecar_artifacts"]
    assert sides[0]["identity"]["sha256"] == sides[1]["identity"]["sha256"]
    assert sides[0]["identity"]["path"] != sides[1]["identity"]["path"]
    assert sides[0]["artifact_key"] != sides[1]["artifact_key"]
    assert catalog["documents"][0]["artifact_ref"] == catalog["documents"][1]["artifact_ref"]
    result = validate(case, payload, descriptor, catalog)
    (tmp_path / "equal-bytes-validation.json").write_text(json.dumps(result, indent=2))
    assert result["status"] == "valid" and result["issues"] == [], result["issues"]
    assert len(result["normalized"]["documents"]) == len(result["normalized"]["sequence_records"]) == 2
    bad = deepcopy(catalog)
    bad["documents"][0]["artifact_key"] = sides[1]["artifact_key"]
    assert "sidecar_capture_key_conflict" in details(validate(case, payload, descriptor, bad))
    broken_bundle = deepcopy(bundle)
    broken_bundle["database_manifest"][0]["sidecar_artifacts"][0]["artifact_key"] = sides[1]["artifact_key"]
    with pytest.raises(ValueError, match="database_metadata_artifact_identity_mismatch"):
        producer.validate_bundle(broken_bundle, plan)
    if family == "native6":
        assert prepare(case, payload, tmp_path)["metadata"][0]["issues"] == []
        case["bundle"] = broken_bundle
        assert "metadata_capture_key_conflict" in details(prepare(case, payload, tmp_path)["metadata"][0])
