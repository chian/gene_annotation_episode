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

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.sequence_homology_evidence import native_blast_database_metadata as metadata


ROLES = ("preparation_input_manifest", "offline_configuration")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def metadata_key(database_key, identity, role="metadata"):
    # Independent literal oracle from the existing N313/005 contract.
    return "database-metadata-" + sha(canonical(dict(database_key=database_key,
                                                   role=role, identity=identity)))


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


@pytest.mark.parametrize("family", ("native6", "standard5"))
def test_identical_bytes_at_distinct_role_paths_keep_original_relations(tmp_path, family):
    # Execute the existing N fixture's deliberately synthetic script, never BLAST.
    if family == "native6":
        from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.tests import test_native_blast_database_driver as producer
        operation = "native_blast_database"
    else:
        from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.tests import test_native_blast_standard_database_driver as producer
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
