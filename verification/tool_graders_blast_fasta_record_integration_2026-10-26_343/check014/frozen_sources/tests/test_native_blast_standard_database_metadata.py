"""327 M1–M8: synthetic supplied-data fixtures, no native database search.

One unchanged paired native report is checked solely for its format/geometry.
All database envelopes, manifests, metadata and measurements here are synthetic.
"""
from copy import deepcopy
import builtins
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode import native_blast_standard_database_metadata as m
from gene_annotation_episode import native_blast_standard_database_contracts as n
from gene_annotation_episode.blast_report_collection import parse_blast_report_collection
from gene_annotation_episode.blast_sequence_database import calculate_blast_sequence_database_components
from gene_annotation_episode.blast_pairwise_grader import alignment_components
from test_native_blast_standard_database_contracts import job_for


ROOT = Path(__file__).resolve().parents[1]


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def address(index=0):
    return dict(output_key="report", member_ordinal=None, report_index=index,
                search_pointer=f"/BlastOutput2/{index}/report/results/search")


def hsp(bits=20, **changes):
    row = dict(query_from=1, query_to=4, hit_from=1, hit_to=4, score=40, bit_score=bits,
               evalue=0.0, qseq="ACDE", hseq="ACDE", align_len=4, identity=4, gaps=0)
    row.update(changes)
    return row


def hit(index=0, length=10, **changes):
    row = dict(len=length, description=[dict(id=f"s{index}", accession=f"S{index}.1", title=f"synthetic {index}", taxid=index + 1)],
               hsps=[hsp(20 - 2 * index)])
    row.update(changes)
    return row


def report(program="blastp", *, hits=None, query_id="q", query_title="q", query_len=8, database="target"):
    result = dict(BlastOutput2=[dict(report=dict(program=program, version=program.upper() + " 2.17.0+",
        search_target=dict(db=database), params={}, results=dict(search=dict(query_id=query_id,
        query_title=query_title, query_len=query_len, hits=[hit(), hit(1)] if hits is None else hits,
        stat=dict(db_num=1000, db_len=10000)))) )])
    return dict(result, synthetic=True, not_native_measurements=True)


def fixture(program="blastp", *, query=None, kind="sequence", doc=None, options=None, fmt="json15", fields=None,
            sidecar_role=None, original_metadata=None, metadata_manifests=()):
    """Entirely synthetic N-valid envelope; no native executable is touched."""
    job = job_for(program, query=kind, fmt=fmt)
    job["options"] = list(options or [])
    if fields is not None:
        job["outputs"][2]["fields"] = fields
    qraw = query if query is not None else b">q\nACDEFGHI\n" if program in {"blastp", "tblastn"} else b">q\nACGTACGT\n"
    job["inputs"][0].update(sha256=sha(qraw), size_bytes=len(qraw), artifact_ref="artifact-query")
    original_raw = None
    if original_metadata is not None:
        original_raw = encoded(original_metadata)
        job["inputs"].append(dict(input_key="original-meta", role="metadata", format="json", path="/selected/original-meta",
            artifact_ref="artifact-original-meta", sha256=sha(original_raw), size_bytes=len(original_raw)))
        job["metadata_inputs"].append(dict(input_key="original-meta", consumer="query_identity", schema_id=original_metadata["schema"]))
    db = job["databases"][0]
    db["identity"].update(version="1", release="r1", scope="selected_sequences")
    db["manifest"]["metadata_manifests"] = [dict(path=f"/synthetic/metadata-{i}.json", artifact_ref=f"selected-manifest-{i}",
        sha256=sha(raw), size_bytes=len(raw)) for i, raw in enumerate(metadata_manifests)]
    receipt_raw = b"synthetic preparation receipt; no database prepared"
    db["manifest"]["preparation"]["receipt"].update(sha256=sha(receipt_raw), size_bytes=len(receipt_raw))
    sidecar_raw = encoded(dict(original_record_ordinal=0))
    sidecar = dict(path="/synthetic/selected-sidecar.json", artifact_ref="selected-sidecar", sha256=sha(sidecar_raw), size_bytes=len(sidecar_raw))
    if sidecar_role is not None:
        db["manifest"]["preparation" if sidecar_role == "preparation_input_manifest" else "access"][
            "input_manifest" if sidecar_role == "preparation_input_manifest" else sidecar_role] = sidecar
    manifest_raw = encoded(db["manifest"])
    db["manifest_file"].update(sha256=sha(manifest_raw), size_bytes=len(manifest_raw))
    document = report(program) if doc is None else doc
    raw_report = document if type(document) is bytes else encoded(document)
    request = n.requested_job_from_standard_blast_database(job)
    identity = dict(run_id="synthetic-run", episode_id="synthetic-child", resource_id="synthetic-hpc",
        operation_key="synthetic-selection", assignment_sha256="1" * 64, requested_job_sha256=sha(encoded(request)), execution_id=None)
    identity["attempt_id"] = sha(encoded(identity["operation_key"]))
    identity["submission_token"] = sha(encoded({k: identity[k] for k in ("run_id", "episode_id", "assignment_sha256", "operation_key")}))
    manifest = dict(version="native_blast_standard_database_producer_manifest_v1", module_root="/synthetic/modules",
        entry_module="gene_annotation_episode.native_blast_standard_database_driver",
        python=dict(path="/synthetic/bin/python", sha256="2" * 64, size_bytes=30),
        package_files=[dict(relative_path="gene_annotation_episode/" + name, sha256="3" * 64, size_bytes=40)
            for name in ("__init__.py", "native_blast_standard_database_contracts.py", "native_blast_standard_database_driver.py", "blast_program_context.py")], runtime_files=[])
    producer_raw = encoded(manifest)
    plan = dict(version="native_blast_standard_database_run_plan_v1", identity=identity,
        requested_job=request, attempt_directory="/synthetic/attempt", input_paths={r["input_key"]: "/synthetic/attempt/input/" + r["input_key"] for r in job["inputs"]},
        database_paths={"target": db["native_paths"]}, output_directory="/synthetic/attempt/output",
        resource_environment={}, producer_manifest=dict(path="/synthetic/producer-manifest.json", sha256=sha(producer_raw),
            size_bytes=len(producer_raw), artifact_ref=None))
    final_identity = {**identity, "execution_id": "synthetic-pbs-id"}
    at = "2026-10-26T00:00:00+00:00"
    bundle = dict(version="native_blast_standard_database_bundle_v1", identity=final_identity, plan=plan,
        requested_job=request, program=program, mode="database", software=dict(selected=job["software"],
            observed_sha256=job["software"]["sha256"], version_source=None),
        producer_verification=dict(manifest=manifest, manifest_observed_sha256=sha(producer_raw),
            package_inventory_exact=True, running_module_paths_match=True, checks=[], status="verified"),
        realized_argv=n.compile_standard_blast_database_argv(job, input_paths=plan["input_paths"],
            database_paths=plan["database_paths"], output_directory=plan["output_directory"]),
        environment={**job["environment"], **{k: "/synthetic/attempt/tmp" for k in ("TMPDIR", "TMP", "TEMP")},
            "XDG_CACHE_HOME": "/synthetic/attempt/cache", "PYTHONDONTWRITEBYTECODE": "1"},
        input_manifest=[], database_manifest=[], output_manifest=[], artifacts=[],
        associations=dict(query_input_key="query", selected_options=job["options"], external_manifest_keys=["manifest"]),
        process=dict(started=True, returncode=0, started_at=at, finished_at=at, native_elapsed_seconds=0.0), failures=[], sealed_at=at)
    for kind_name, path, digest, size in [("python", manifest["python"]["path"], "2" * 64, 30),
            *[("package", "/synthetic/modules/" + r["relative_path"], r["sha256"], r["size_bytes"]) for r in manifest["package_files"]]]:
        bundle["producer_verification"]["checks"].append(dict(kind=kind_name, path=path,
            observed_sha256=digest, size_bytes=size, checked_at=at, status="verified"))
    catalog = dict(bundle_source_ref="source-bundle", bundle_artifact_ref="artifact-bundle", bundle_sha256="",
                   entries=[], retained_sources=[])
    contents = {}

    def capture(key, raw, role, format, path, *, input_key=None, output_key=None, database_key=None, fields=(), delimiter=None):
        artifact = dict(artifact_key=key, input_key=input_key, output_key=output_key, database_key=database_key,
            role=role, relative_path=path, format=format, fields=list(fields), delimiter=delimiter,
            sha256=sha(raw), size_bytes=len(raw), content_assessment="not_parsed")
        bundle["artifacts"].append(artifact)
        catalog["entries"].append({k: deepcopy(v) for k, v in artifact.items() if k != "content_assessment"} |
            dict(artifact_ref="artifact-" + key, source_ref="source-" + key, path="opaque://never-open/" + key))
        contents["artifact-" + key] = raw
        return artifact

    capture("query", qraw, "query_" + kind, "fasta" if kind == "sequence" else "scoremat_asn_text", "input/query", input_key="query")
    bundle["input_manifest"].append(dict(input_key="query", original_path=job["inputs"][0]["path"],
        realized_path=plan["input_paths"]["query"], artifact_key="query", expected_sha256=sha(qraw), observed_sha256=sha(qraw), size_bytes=len(qraw)))
    if original_raw is not None:
        capture("original-meta", original_raw, "metadata", "json", "input/original-meta", input_key="original-meta")
        bundle["input_manifest"].append(dict(input_key="original-meta", original_path=job["inputs"][1]["path"],
            realized_path=plan["input_paths"]["original-meta"], artifact_key="original-meta", expected_sha256=sha(original_raw),
            observed_sha256=sha(original_raw), size_bytes=len(original_raw)))
    capture("manifest", manifest_raw, "database_manifest", "json", "custody/manifest", database_key="target")
    capture("receipt", receipt_raw, "preparation_receipt", "opaque", "custody/receipt", database_key="target")
    capture("producer", producer_raw, "producer_manifest", "json", "custody/producer")
    bundle["database_manifest"].append(dict(database_key="target", native_paths=db["native_paths"],
        manifest_artifact_key="manifest", preparation_receipt_artifact_key="receipt", metadata_manifest_artifacts=[], sidecar_artifacts=[],
        checks=[dict(path=r["path"], expected_sha256=r["sha256"], observed_sha256=r["sha256"], size_bytes=r["size_bytes"],
                     checked_at=at, status="verified") for r in db["manifest"]["files"]]))
    if sidecar_role is not None:
        # N331's concrete public contract currently requires this metadata role.
        key = "database-metadata-" + sha(encoded(dict(database_key="target", role="metadata", identity=sidecar)))
        capture(key, sidecar_raw, "metadata", "opaque", "custody/selected-sidecar", database_key="target")
        bundle["database_manifest"][0]["sidecar_artifacts"] = [dict(role=sidecar_role, identity=sidecar, artifact_key=key)]
    for i, (identity_row, raw) in enumerate(zip(db["manifest"]["metadata_manifests"], metadata_manifests)):
        key = "database-metadata-" + sha(encoded(dict(database_key="target", role="metadata", identity=identity_row)))
        capture(key, raw, "metadata", "opaque", f"custody/metadata-{i}", database_key="target")
        bundle["database_manifest"][0]["metadata_manifest_artifacts"].append(dict(identity=identity_row, artifact_key=key))
    for output in job["outputs"]:
        key = output["output_key"]
        capture(key, raw_report if key == "report" else b"", output["role"], output["format"],
                "output/" + output["relative_path"], output_key=key, fields=output["fields"], delimiter=output["delimiter"])
        bundle["output_manifest"].append(dict(output_key=key, presence="present", artifact_keys=[key], inventory_complete=True))
    envelope = dict(identity=final_identity, attempt_directory=plan["attempt_directory"], plan_sha256=sha(encoded(plan)))
    catalog["bundle_sha256"] = sha(encoded(bundle))
    n.validate_standard_blast_database_bundle(bundle, original_job=job, attempt_identity=envelope)
    metadata_payloads = [] if original_raw is None else [dict(payload=original_metadata, descriptor=dict(input_key="original-meta",
        consumer="query_identity", schema_id=original_metadata["schema"], artifact_ref="artifact-original-meta", sha256=sha(original_raw),
        size_bytes=len(original_raw), origin="original_job_input"))]
    return dict(job=job, bundle=bundle, attempt_identity=envelope, artifact_catalog=catalog, contents=contents,
                metadata_payloads=metadata_payloads, subject_snapshots=[], subject_contents={})


def received(inputs, key, raw, format="json"):
    row = dict(source_ref="source-" + key, artifact_ref="artifact-" + key, sha256=sha(raw), size_bytes=len(raw), path="opaque://" + key)
    inputs["artifact_catalog"]["retained_sources"].append(row)
    inputs["contents"][row["artifact_ref"]] = raw
    return dict(document_key=key, artifact=dict(kind="received", **{k: row[k] for k in ("source_ref", "artifact_ref", "sha256", "size_bytes")}), format=format)


def query_payload():
    return dict(schema="native_blast_database_query_metadata_v1", documents=[], sequence_records=[],
        effective_msa_masters=[], master_subjects=[], search_bindings=[], target_contexts=[])


def sequence_payload():
    return dict(schema="native_blast_database_sequence_metadata_v1", documents=[], searches=[])


def add_metadata(inputs, payload, consumer, key="metadata"):
    doc = received(inputs, key, encoded(payload))
    descriptor = dict(input_key=key, consumer=consumer, schema_id=payload["schema"],
        **{k: doc["artifact"][k] for k in ("artifact_ref", "sha256", "size_bytes")}, origin="selected_results_input")
    row = dict(descriptor=descriptor, payload=payload)
    inputs["metadata_payloads"].append(row)
    return row


def subject(inputs, symbols, molecule="protein", *, ordinal=0, kind="sequence", subject_ref="subject-q"):
    raw = symbols.encode()
    snapshot = dict(subject_ref=subject_ref, sequence_artifact_ref="artifact-subject-" + subject_ref,
        sequence_path="opaque://subject", molecule=molecule, length=len(symbols), sequence_sha256=sha(raw))
    inputs["subject_snapshots"].append(snapshot)
    inputs["subject_contents"][snapshot["sequence_artifact_ref"]] = raw
    payload = query_payload()
    doc = received(inputs, "query-relation-" + str(ordinal), encoded(dict(original_record_ordinal=ordinal)))
    payload["documents"] = [doc]
    relation = dict(input_key="query", record_ordinal=ordinal, subject_ref=subject_ref,
                    source=dict(source_ref=doc["document_key"], pointer=""))
    if kind == "sequence":
        relation["identity"] = None
        payload["sequence_records"] = [relation]
    else:
        relation.update(kind="pssm", sequence_sha256=sha(raw))
        payload["master_subjects"] = [relation]
    add_metadata(inputs, payload, "query_identity", "query-meta-" + str(ordinal))
    return snapshot


def run(inputs):
    prepared = m.prepare_standard_blast_database_inputs(**inputs)
    reports = [r for r in inputs["artifact_catalog"]["entries"] if r["role"] == "primary_report"]
    collection = parse_blast_report_collection({r["artifact_key"]: inputs["contents"][r["artifact_ref"]] for r in reports},
        artifacts=[dict(artifact_key=r["artifact_key"], role=r["role"], format=r["format"],
            fields=None if r["format"] == "json15" else r["fields"], delimiter=r["delimiter"]) for r in reports],
        invocation=prepared["invocation"])
    sheets = m.populate_standard_blast_database_sheets(collection, prepared_inputs=prepared)
    return m.validate_standard_blast_database_sheet_set(sheets)


def calculate(sheets):
    return calculate_blast_sequence_database_components(sheets["sequence"][0]["sheet"])


def save_example(path, inputs, sheets, components):
    value = dict(evidence="synthetic_only_not_native_database_measurements", inputs={k: v for k, v in inputs.items()
        if k not in {"contents", "subject_contents"}}, contents_hex={k: v.hex() for k, v in inputs["contents"].items()},
        subject_contents_hex={k: v.hex() for k, v in inputs["subject_contents"].items()})
    for name, document in (("supplied_inputs.json", value), ("sheets.json", sheets), ("components.json", components)):
        (path / name).write_text(json.dumps(document, indent=2, allow_nan=False) + "\n")


def numerical_metadata(inputs, *, sequences=("ACDEFGHIKL", "ACDEPQRSTV"), molecule="aa", indices=(0, 1),
                       description_ordinals=(0, 0), doc=None, key="sequence-meta", census=True, format="json"):
    payload = sequence_payload()
    records = [dict(accession=f"S{i}.1", sequence=s, function="F" if j == 0 else "G") for j, (i, s) in enumerate(zip(indices, sequences))]
    sequence_raw = encoded(records) if format == "json" else "".join(f">s{i}\n{s}\n" for i, s in zip(indices, sequences)).encode()
    source = received(inputs, key + "-records", sequence_raw, format)
    links = received(inputs, key + "-links", encoded(dict(description_links=list(indices), sequence_links=list(indices))))
    payload["documents"] = [source, links]
    unit = dict(search_key=address(), reference_metadata=[], description_bindings=[], sequence_identity_bindings=[], sequence_proofs=[], database_profile=None)
    if doc is None:
        doc = json.loads(inputs["contents"]["artifact-report"])
    native_hits = doc["BlastOutput2"][0]["report"]["results"]["search"]["hits"]
    for j, (index, symbols, description) in enumerate(zip(indices, sequences, description_ordinals)):
        pointer = f"/{j}" if format == "json" else ""
        native = {k: native_hits[index]["description"][description].get(k) for k in ("id", "accession", "title", "taxid")}
        unit["reference_metadata"].append(dict(identifier_namespace="synthetic", accession=f"S{index}.1", source=source["document_key"],
            native_pointer=pointer, taxid=native["taxid"], lineage=[dict(rank="genus", taxid=10 + index, name=None)],
            functions=[dict(function="F" if j == 0 else "G", evidence=["synthetic supplied assignment"], source=source["document_key"])],
            origin=dict(assignment_scope="whole_sequence"), assembly=None, sequence_group=None, study_groups=[], native_record=records[j]))
        unit["description_bindings"].append(dict(search_key=address(), binding=dict(report_index=0, hit_index=index,
            description_index=description, metadata_index=j, native_description=native,
            metadata_identifier=dict(namespace="synthetic", value=f"S{index}.1"), metadata_source_ref=source["document_key"], metadata_pointer=pointer,
            linkage_source_ref=links["document_key"], linkage_pointer=f"/description_links/{j}")))
        unit["sequence_identity_bindings"].append(dict(search_key=address(), binding=dict(report_index=0, hit_index=index,
            kind="full_sequence_digest", sequence_group="sha256:" + sha(symbols.encode()), algorithm="sha256", digest=sha(symbols.encode()),
            molecule=molecule, sequence_length=len(symbols), source_ref=source["document_key"], pointer=pointer,
            linkage_source_ref=links["document_key"], linkage_pointer=f"/sequence_links/{j}")))
        unit["sequence_proofs"].append(dict(binding_index=j, document_key=source["document_key"],
            representation="json_sequence" if format == "json" else "fasta_record", record_ordinal=j if format == "fasta" else None,
            sequence_pointer=f"/{j}/sequence" if format == "json" else None, molecule=molecule, sha256=sha(symbols.encode()), length=len(symbols)))
    if census:
        census_doc = received(inputs, key + "-census", encoded(dict(total=1000, F=100, G=10)))
        payload["documents"].append(census_doc)
        unit["database_profile"] = dict(database="target", release="r1", scope="selected_sequences", count_unit="unique_sequences",
            total_count=1000, function_counts={"F": 100, "G": 10}, source=census_doc["document_key"])
    payload["searches"] = [unit]
    return payload


def assert_pure(monkeypatch):
    def fail(*a, **kw):
        pytest.fail("pure metadata boundary attempted I/O or scoring")
    from gene_annotation_episode import blast_sequence_database, blast_database_grader, blast_pssm_calculators
    from gene_annotation_episode import native_blast_database_metadata
    for obj, name in [(builtins, "open"), (Path, "open"), (Path, "read_bytes"), (Path, "read_text"),
            (os, "stat"), (os, "listdir"), (socket, "socket"), (socket, "getaddrinfo"),
            (subprocess, "Popen"), (subprocess, "run"), (blast_sequence_database, "calculate_blast_sequence_database_components"),
            (blast_database_grader, "calculate_database_probabilities"), (blast_pssm_calculators, "calculate_blast_pssm_components"),
            (native_blast_database_metadata, "prepare_native_blast_database_inputs"),
            (native_blast_database_metadata, "populate_native_blast_database_sheets")]:
        monkeypatch.setattr(obj, name, fail)


def test_M1_real_standard_job_public_validator_exact_tuples_and_pure_ports(monkeypatch, tmp_path):
    inputs = fixture()
    subject(inputs, "ACDEFGHI")
    payload = numerical_metadata(inputs)
    add_metadata(inputs, payload, "sequence_database")
    original = deepcopy(inputs)
    calls = []
    actual = m.validate_native_blast_database_metadata_payload
    def validator(payload, **kwargs):
        assert kwargs["job"]["version"] == "native_blast_standard_database_job_v1"
        calls.append((kwargs["descriptor"]["consumer"], kwargs["descriptor"]["schema_id"]))
        return actual(payload, **kwargs)
    monkeypatch.setattr(m, "validate_native_blast_database_metadata_payload", validator)
    with monkeypatch.context() as blocked:
        assert_pure(blocked)
        sheets = run(inputs)
        assert m.validate_standard_blast_database_prepared_inputs(sheets["prepared_inputs"]) == sheets["prepared_inputs"]
        assert m.validate_standard_blast_database_sheet_set(sheets) == sheets
        assert m.validate_standard_blast_database_binding_result(sheets["search_bindings"][0]) == sheets["search_bindings"][0]
        assert m.validate_standard_blast_sequence_metadata_result(sheets["metadata_binding_results"][0]) == sheets["metadata_binding_results"][0]
    assert set(calls) == {("query_identity", "native_blast_database_query_metadata_v1"), ("sequence_database", "native_blast_database_sequence_metadata_v1")}
    assert inputs == original
    comp = calculate(sheets)["components"]
    assert comp["function_weights"]["function_masses"] == {"F": 1, "G": .25}
    assert comp["function_weights"]["unadjusted_probabilities"] == {"F": .8, "G": .2}
    assert comp["function_weights"]["representation_adjusted_probabilities"]["F"] == pytest.approx(2 / 7)
    assert comp["selected_query_coverage"][0]["value"] is None
    assert comp["database_sheet"]["hits"][0]["measurements"]["query_paired_coverage"] == .5
    save_example(tmp_path, inputs, sheets, calculate(sheets))


@pytest.mark.parametrize("change,detail", [
    (lambda i: i["metadata_payloads"][0]["descriptor"].update(schema_id="future"), "metadata_tuple_unregistered"),
    (lambda i: i["metadata_payloads"].append(deepcopy(i["metadata_payloads"][0])), "metadata_descriptor_tuple_duplicate"),
    (lambda i: i["metadata_payloads"][0]["payload"].update(extra=True), "metadata_payload_bytes_conflict"),
    (lambda i: i["contents"].update({"artifact-metadata": b"changed"}), "artifact_digest_conflict"),
])
def test_M1_metadata_tuple_bytes_and_duplicate_conflicts_keep_native_rows(change, detail):
    inputs = fixture()
    add_metadata(inputs, sequence_payload(), "sequence_database")
    change(inputs)
    sheets = run(inputs)
    assert any(detail in r.get("detail_code", "") for r in sheets["issues"])
    assert calculate(sheets)["components"]["database_sheet"]["hits"][0]["measurements"]["maximum_bit_score"] == 20


def test_M1_wrong_literal_source_pointer_and_unreceived_document_remain_qualified():
    for mode in ("pointer", "unreceived", "source_bytes"):
        inputs = fixture()
        payload = numerical_metadata(inputs)
        if mode == "pointer":
            payload["searches"][0]["reference_metadata"][0]["native_pointer"] = "/999"
        elif mode == "unreceived":
            inputs["artifact_catalog"]["retained_sources"].pop(0)
            inputs["contents"].pop("artifact-sequence-meta-records")
        else:
            inputs["contents"]["artifact-sequence-meta-records"] = b"changed source bytes"
        add_metadata(inputs, payload, "sequence_database")
        sheets = run(inputs)
        assert sheets["issues"]
        assert not sheets["sequence"][0]["sheet"]["reference_metadata"]
        assert calculate(sheets)["components"]["database_sheet"]["hits"][0]["measurements"]["maximum_bit_score"] == 20


def test_M2_multiple_native_records_and_duplicate_names_preserve_original_ordinal():
    first, second = report(), report(query_id="later", query_title="later")
    first["BlastOutput2"].extend(second["BlastOutput2"])
    inputs = fixture(query=b">q\naCdEfGhI\n>later\nKLMNPQRS\n", doc=first, options=["-lcase_masking"])
    subject(inputs, "ACDEFGHI", ordinal=0)
    subject(inputs, "KLMNPQRS", ordinal=1, subject_ref="subject-second")
    sheets = run(inputs)
    rows = sheets["prepared_inputs"]["query_records"]
    assert [(r["record_ordinal"], r["sequence"], r["subject_ref"]) for r in rows] == [(0, "ACDEFGHI", "subject-q"), (1, "KLMNPQRS", "subject-second")]
    assert [r["sheet"]["query_binding"]["operand"]["record_ordinal"] for r in sheets["sequence"]] == [0, 1]
    saved = next(r for r in sheets["prepared_inputs"]["resolved_documents"] if r["catalog"].get("artifact_key") == "query")
    assert bytes.fromhex(saved["contents_hex"]) == b">q\naCdEfGhI\n>later\nKLMNPQRS\n"
    duplicate = fixture(query=b">q\nACDEFGHI\n>q\nKLMNPQRS\n")
    subject(duplicate, "ACDEFGHI")
    ambiguous = run(duplicate)
    assert ambiguous["sequence"][0]["sheet"]["query_binding"] is None
    assert ambiguous["collection"]["searches"][0]["operand_binding"] is None
    assert "blast_query_binding_ambiguous" in {r["code"] for r in ambiguous["collection"]["searches"][0]["issues"]}


@pytest.mark.parametrize("mode", ["no_snapshot", "same_length", "wrong_digest", "wrong_molecule", "missing_bytes", "duplicate_snapshot"])
def test_M2_biological_subject_requires_exact_complete_received_snapshot(mode):
    inputs = fixture()
    snap = subject(inputs, "ACDEFGHI")
    if mode == "no_snapshot":
        inputs["subject_snapshots"] = []
        inputs["subject_contents"] = {}
    elif mode == "same_length":
        inputs["subject_contents"][snap["sequence_artifact_ref"]] = b"KLMNPQRS"
        snap["sequence_sha256"] = sha(b"KLMNPQRS")
    elif mode == "wrong_digest":
        snap["sequence_sha256"] = "0" * 64
    elif mode == "wrong_molecule":
        snap["molecule"] = "dna"
    elif mode == "missing_bytes":
        inputs["subject_contents"] = {}
    else:
        inputs["subject_snapshots"].append(deepcopy(snap))
    sheets = run(inputs)
    assert sheets["prepared_inputs"]["query_records"][0]["subject_ref"] is None
    assert sheets["sequence"][0]["sheet"]["query_binding"]["operand"]["subject_ref"] is None


@pytest.mark.parametrize("program,molecule,query", [("blastn", "rna", b">q\nACGUACGU\n"), ("blastx", "dna", b">q\nACGTACGT\n"),
    ("tblastx", "rna", b">q\nACGAACGA\n")])
def test_M2_nucleotide_queries_retain_exact_declared_subject_molecule(program, molecule, query):
    inputs = fixture(program, query=query, doc=report(program, hits=[]))
    subject(inputs, query.decode().splitlines()[1], molecule)
    sheets = run(inputs)
    assert sheets["prepared_inputs"]["query_records"][0]["molecule"] == molecule
    assert sheets["prepared_inputs"]["query_records"][0]["subject_ref"] == "subject-q"
    assert sheets["sequence"][0]["sheet"]["query_binding"]["coordinate_unit"] == "nt"


@pytest.mark.parametrize("program", ["blastn", "blastp", "blastx", "tblastn", "tblastx"])
@pytest.mark.parametrize("record_version", [1, 2])
def test_M3_M6_all_five_direct_sequence_sheets_use_correct_units(program, record_version):
    qnt, snt = program in {"blastn", "blastx", "tblastx"}, program in {"blastn", "tblastn", "tblastx"}
    translated = program != "blastn"
    length = 4 if program == "blastn" else 12 if snt else 4
    qlen = 4 if program == "blastn" else 12 if qnt else 4
    aligned = "ACGT" if program == "blastn" else "ACDE"
    native = hsp(qseq=aligned, hseq=aligned, query_to=qlen, hit_to=length)
    if qnt and translated:
        native["query_frame"] = 1
    if snt and translated:
        native["hit_frame"] = 1
    doc = report(program, hits=[hit(length=length, hsps=[native])], query_len=qlen)
    inputs = fixture(program, query=b">q\n" + (b"ACGTACGTACGT" if qlen == 12 else b"ACGT" if qnt else b"ACDE") + b"\n", doc=doc)
    kwargs = dict(sequences=("ACGTACGTACGT" if length == 12 else "ACGT" if snt else "ACDE",),
        molecule="nt" if snt else "aa", indices=(0,), description_ordinals=(0,))
    payload = numerical_metadata(inputs, census=False, **kwargs) if record_version == 1 else record_metadata(inputs, ordinals=(0,), **kwargs)
    add_metadata(inputs, payload, "sequence_database")
    sheets = run(inputs)
    assert set(sheets) == {"schema", "collection", "prepared_inputs", "search_bindings", "sequence", "pssm", "metadata_parse_results", "metadata_binding_results", "issues"}
    assert sheets["search_bindings"][0]["binding"]["stage"] == "sequence_database"
    assert len(sheets["sequence"]) == 1 and len(sheets["sequence"][0]["sheet"]["sequence_identity_bindings"]) == 1
    components = calculate(sheets)["components"]
    assert components["coordinate_context"]["query"]["coordinate_unit"] == ("nt" if qnt else "aa")
    assert components["coordinate_context"]["references"][0]["coordinate_unit"] == ("nt" if snt else "aa")
    assert components["database_sheet"]["hits"][0]["measurements"]["query_paired_coverage"] == 1
    assert components["database_sheet"]["hits"][0]["measurements"]["reference_paired_coverage"] == 1


@pytest.mark.parametrize("alter", ["digest", "length", "molecule", "hsp_fragment", "proof_duplicate", "binding_index", "source_unreceived"])
def test_M3_reference_full_bytes_required_and_native_scores_survive(alter):
    inputs = fixture("tblastn", doc=report("tblastn", hits=[hit(length=30, hsps=[hsp(hit_to=12, hit_frame=1)])]))
    payload = numerical_metadata(inputs, sequences=("ACGT" * 7 + "AC",), molecule="nt", indices=(0,), description_ordinals=(0,), census=False)
    unit = payload["searches"][0]
    b, proof = unit["sequence_identity_bindings"][0]["binding"], unit["sequence_proofs"][0]
    if alter == "digest":
        b["digest"] = proof["sha256"] = "1" * 64
        b["sequence_group"] = "sha256:" + "1" * 64
    elif alter == "length":
        b["sequence_length"] = proof["length"] = 29
    elif alter == "molecule":
        b["molecule"] = proof["molecule"] = "aa"
    elif alter == "hsp_fragment":
        source = received(inputs, "fragment", encoded("ACDE"))
        payload["documents"].append(source)
        b.update(source_ref="fragment", pointer="", digest=sha(b"ACDE"), sequence_length=4, sequence_group="sha256:" + sha(b"ACDE"), molecule="aa")
        proof.update(document_key="fragment", sequence_pointer="", sha256=sha(b"ACDE"), length=4, molecule="aa")
    elif alter == "proof_duplicate":
        unit["sequence_proofs"].append(deepcopy(proof))
    elif alter == "binding_index":
        proof["binding_index"] = 8
    else:
        inputs["artifact_catalog"]["retained_sources"].pop(0)
        inputs["contents"].pop("artifact-sequence-meta-records")
    add_metadata(inputs, payload, "sequence_database")
    sheets = run(inputs)
    assert not sheets["sequence"][0]["sheet"]["sequence_identity_bindings"]
    assert calculate(sheets)["components"]["database_sheet"]["hits"][0]["measurements"]["maximum_bit_score"] == 20


def test_M3_identical_full_json_sequences_collapse_only_demonstrated_duplicate():
    inputs = fixture()
    payload = numerical_metadata(inputs, sequences=("ACDEFGHIKL", "ACDEFGHIKL"))
    add_metadata(inputs, payload, "sequence_database")
    sheets = run(inputs)
    data = calculate(sheets)["components"]["database_sheet"]
    assert data["dependence"]["duplicate_native_hit_count"] == 1
    assert data["sequence_groups"][0]["maximum_bit_score"] == 20
    assert data["sequence_groups"][0]["functions"] == ["F", "G"]
    assert len(sheets["prepared_inputs"]["sequence_proofs"]) == 2


def test_M3_full_fasta_reference_bytes_and_case_are_retained():
    inputs = fixture(doc=report(hits=[hit()]))
    payload = numerical_metadata(inputs, sequences=("ACDEFGHIKL",), indices=(0,), description_ordinals=(0,), format="fasta", census=False)
    raw = b">s0 Native Case\nAcDefGHikL\n"
    address = payload["documents"][0]["artifact"]
    address.update(sha256=sha(raw), size_bytes=len(raw))
    next(r for r in inputs["artifact_catalog"]["retained_sources"] if r["artifact_ref"] == address["artifact_ref"]).update(sha256=sha(raw), size_bytes=len(raw))
    inputs["contents"][address["artifact_ref"]] = raw
    add_metadata(inputs, payload, "sequence_database")
    sheets = run(inputs)
    assert len(sheets["sequence"][0]["sheet"]["sequence_identity_bindings"]) == 1
    assert sheets["prepared_inputs"]["sequence_proofs"][0]["proof"]["record_ordinal"] == 0
    assert sheets["prepared_inputs"]["sequence_proofs"][0]["symbols"] == "ACDEFGHIKL"
    assert next(r for r in sheets["prepared_inputs"]["resolved_documents"] if r["catalog"]["artifact_ref"] == address["artifact_ref"])["contents_hex"] == raw.hex()


def test_M4_sparse_native_and_metadata_tuple_ordinals_keep_exact_source_addresses():
    doc = report(hits=[None, hit(1, hsps=[None, hsp(20)], description=[None, dict(id="s1", accession="S1.1", title="synthetic 1", taxid=2)]), hit(2)])
    inputs = fixture(doc=doc)
    first = numerical_metadata(inputs, sequences=("ACDEFGHIKL",), indices=(1,), description_ordinals=(1,), key="first", census=False)
    second = numerical_metadata(inputs, sequences=("ACDEPQRSTV",), indices=(2,), description_ordinals=(0,), key="second", census=False)
    second["searches"][0]["reference_metadata"][0]["functions"][0]["function"] = "G"
    add_metadata(inputs, first, "sequence_database", "first")
    add_metadata(inputs, second, "sequence_database", "second")
    sheets = run(inputs)
    links = sheets["sequence"][0]["sheet"]["description_bindings"]
    assert [(r["binding"]["hit_index"], r["binding"]["description_index"], r["binding"]["metadata_index"]) for r in links] == [(1, 1, 0), (2, 0, 1)]
    comp = calculate(sheets)["components"]
    assert comp["row_keys"]["hits"][0]["hsps"][0]["row_key"]["hsp_ordinal"] == 1
    assert comp["row_keys"]["hits"][0]["descriptions"][0]["row_key"]["description_ordinal"] == 1
    assert comp["row_keys"]["hits"][0]["hsps"][0]["source_locator"]["pointer"].endswith("/hits/1/hsps/1")
    assert sheets["prepared_inputs"]["metadata"][1]["payload"]["searches"][0]["description_bindings"][0]["binding"]["metadata_index"] == 0


def test_M4_conflicting_description_taxon_does_not_borrow_function_or_assembly():
    inputs = fixture()
    payload = numerical_metadata(inputs)
    payload["searches"][0]["reference_metadata"][0]["taxid"] = 999
    add_metadata(inputs, payload, "sequence_database")
    comp = calculate(run(inputs))["components"]
    assert comp["function_weights"]["unadjusted_probabilities"] == {"G": 1}
    assert not comp["database_sheet"]["hits"][0]["associations"][0]["functions"]


def test_M5_retained_paired_range_format_only_and_separate_synthetic_database_case(tmp_path):
    path = ROOT / "verification/tool_graders_blast_pairwise_2026-10-26_294/native_ranges/blastx_range_reverse_json15/attempt/report.json"
    raw = path.read_bytes()
    native = json.loads(raw)
    actual = native["BlastOutput2"][0]["report"]["results"]["bl2seq"][0]
    h = actual["hits"][0]["hsps"][0]
    geometry = alignment_components(h, program="blastx", query_length=244, reference_length=80, coordinate_convention="blast_json2")
    assert [geometry["pairs"][0]["query_start"], geometry["pairs"][0]["query_end"]] == [212, 215]
    assert geometry["fractions"]["query_paired_coverage"] == 186 / 244
    assert "subjects" in native["BlastOutput2"][0]["report"]["search_target"]
    # Deliberately synthetic report with the documented range dimensions.
    synthetic_hsp = hsp(qseq="A" * 62, hseq="A" * 62, query_from=30, query_to=215,
        query_frame=-3, hit_from=10, hit_to=71, align_len=62, identity=62)
    inputs = fixture("blastx", query=b">q\n" + b"A" * 244 + b"\n", options=["-query_loc", "30-215"],
        doc=report("blastx", query_len=186, hits=[hit(length=80, hsps=[synthetic_hsp])]))
    sheets = run(inputs)
    result = calculate(sheets)["components"]
    assert result["coordinate_context"]["query"] == dict(axis_kind="sequence", reported_length=186, full_length=244,
                                                        selected_interval=[29, 215], coordinate_unit="nt")
    qualified = result["database_sheet"]["hits"][0]["hsp_components"][0]
    assert [qualified["pairs"][0]["query_start"], qualified["pairs"][0]["query_end"]] == [212, 215]
    assert qualified["fractions"]["query_paired_coverage"] == 186 / 244
    assert result["selected_query_coverage"][0]["value"] == 1
    assert path.read_bytes() == raw
    save_example(tmp_path, inputs, sheets, calculate(sheets))


def test_M6_original_attempt_report_and_manifest_conflicts_are_not_self_authenticated():
    inputs = fixture()
    bad = deepcopy(inputs)
    bad["attempt_identity"]["plan_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="bundle_original_attempt_mismatch"):
        m.prepare_standard_blast_database_inputs(**bad)
    bad = deepcopy(inputs)
    bad["contents"]["artifact-manifest"] = b"{}"
    sheets = run(bad)
    assert sheets["search_bindings"][0]["binding"] is None
    assert calculate(sheets)["components"]["database_sheet"] is None
    good = run(inputs)
    search = deepcopy(good["collection"]["searches"][0])
    search["normalized"]["native"]["document"]["BlastOutput2"][0]["report"]["results"]["search"]["hits"][0]["hsps"][0]["bit_score"] = 999
    binding = m.derive_standard_blast_database_search_binding(search, prepared_inputs=good["prepared_inputs"])
    assert binding["status"] == "incompatible"


def test_M6_path_spelling_is_preserved_and_population_correction_stays_unavailable():
    inputs = fixture(doc=report(database="/selected/db/target"))
    add_metadata(inputs, numerical_metadata(inputs), "sequence_database")
    sheets = run(inputs)
    assert sheets["search_bindings"][0]["status"] == "available"
    assert sheets["search_bindings"][0]["binding"]["database_identity"]["value"] == "target"
    assert sheets["sequence"][0]["sheet"]["search"]["normalized"]["search"]["database"] == "/selected/db/target"
    result = calculate(sheets)["components"]["function_weights"]
    assert result["unadjusted_probabilities"] == {"F": .8, "G": .2}
    assert result["representation_adjusted_probabilities"] is None
    assert "database_context_value_conflict" in result["representation_adjustment_unavailable_reasons"]


@pytest.mark.parametrize("change", [lambda p: p.update(release="wrong"), lambda p: p.update(scope="different"),
                                  lambda p: p.update(function_counts={"F": 0, "G": 10})])
def test_M7_conflicting_census_disables_only_adjustment(change):
    inputs = fixture()
    payload = numerical_metadata(inputs)
    change(payload["searches"][0]["database_profile"])
    add_metadata(inputs, payload, "sequence_database")
    result = calculate(run(inputs))["components"]["function_weights"]
    assert result["unadjusted_probabilities"] == {"F": .8, "G": .2}
    assert result["representation_adjusted_probabilities"] is None


def test_M7_feature_function_is_retained_as_source_and_excluded_from_whole_contig_kernel():
    inputs = fixture()
    payload = numerical_metadata(inputs)
    payload["searches"][0]["reference_metadata"][0]["origin"]["assignment_scope"] = "feature"
    add_metadata(inputs, payload, "sequence_database")
    sheets = run(inputs)
    assert sheets["prepared_inputs"]["metadata"][0]["payload"]["searches"][0]["reference_metadata"][0]["functions"]
    assert not sheets["sequence"][0]["sheet"]["reference_metadata"][0]["functions"]
    assert any(r.get("detail_code") == "feature_function_is_not_whole_reference_function" for r in sheets["issues"])
    assert calculate(sheets)["components"]["function_weights"]["unadjusted_probabilities"] == {"G": 1}


def pssm(encoding='iupacaa "ACD"', *, master=True, query=None, columns=3):
    if query is None:
        query = 'seq { id { local str "q" }, descr { title "q" }, inst { repr raw, mol aa, length 3, seq-data ' + encoding + ' } }'
    return ('Pssm ::= { numRows 2, numColumns ' + str(columns) + ', rowLabels { "A", "C" }, ' +
        ("query " + query + ", " if master else "") + 'intermediateData { freqRatios { 0, 1, 2, 3, 4, 5 } } }').encode()


@pytest.mark.parametrize("encoding", ['iupacaa "ACD"', 'ncbieaa "ACD"', "ncbistdaa '010304'H"])
def test_M8_pssm_supported_exact_master_and_column_map(encoding, monkeypatch, tmp_path):
    inputs = fixture("tblastn", kind="pssm", query=pssm(encoding), doc=report("psitblastn", query_len=3, hits=[]))
    subject(inputs, "ACD", kind="pssm")
    calls = []
    parser = m.read_blast_pssm
    def read(*a, **kw):
        calls.append(kw["artifact_key"])
        return parser(*a, **kw)
    monkeypatch.setattr(m, "read_blast_pssm", read)
    with monkeypatch.context() as blocked:
        assert_pure(blocked)
        sheets = run(inputs)
    assert calls == ["query"]
    assert sheets["sequence"][0]["sheet"]["query_binding"]["operand"]["subject_ref"] == "subject-q"
    assert sheets["sequence"][0]["sheet"]["query_binding"]["axis_kind"] == "pssm_master"
    assert sheets["search_bindings"][0]["binding"]["input_pssm_key"] == '["query",0]'
    masters = next(r["value"] for r in sheets["prepared_inputs"]["source_relations"] if r["kind"] == "pssm_master")
    assert masters["records"][0]["master"]["column_to_residue"] == [dict(column=i, master_position=i, symbol=s) for i, s in enumerate("ACD")]
    assert "iteration" not in sheets
    save_example(tmp_path, inputs, sheets, calculate(sheets))


@pytest.mark.parametrize("raw", [pssm(master=False), pssm(query="set { seq-set { } }"), pssm(columns=4),
    pssm("ncbistdaa 'FF'H"), pssm('ncbieaa "A-D"')])
def test_M8_missing_compound_invalid_master_keeps_model_without_biological_binding(raw):
    inputs = fixture("tblastn", kind="pssm", query=raw, doc=report("psitblastn", query_len=3, hits=[]))
    sheets = run(inputs)
    assert len(sheets["pssm"]) == 1
    assert sheets["sequence"][0]["sheet"]["query_binding"] is None
    assert not sheets["prepared_inputs"]["invocation"]["operands"]


def test_M8_same_length_impostor_pssm_subject_is_not_bound():
    inputs = fixture("tblastn", kind="pssm", query=pssm(), doc=report("psitblastn", query_len=3, hits=[]))
    subject(inputs, "KLM", kind="pssm")
    sheets = run(inputs)
    assert sheets["prepared_inputs"]["query_records"][0]["subject_ref"] is None
    assert sheets["prepared_inputs"]["query_records"][0]["binding_status"] == "incompatible"


@pytest.mark.parametrize("format,raw,fields", [
    ("tabular6", b"q\ts0\t20\n", ["qseqid", "sseqid", "bitscore"]),
    ("tabular7", b"# BLASTP 2.17.0+\n# Query: q\n# Database: target\n# 0 hits found\n", ["qseqid", "sseqid", "bitscore"]),
])
def test_missing_optional_metadata_and_table_fields_preserve_direct_sheet(format, raw, fields):
    inputs = fixture(fmt=format, doc=raw, fields=fields)
    sheets = run(inputs)
    assert len(sheets["sequence"]) == 1
    out = calculate(sheets)
    if format == "tabular7":
        assert out["status"] == "no_reported_hits"
    else:
        assert out["components"]["database_sheet"]["hits"][0]["measurements"]["maximum_bit_score"] == 20
        assert out["components"]["database_sheet"]["hits"][0]["measurements"]["query_paired_coverage"] is None


def test_saved_artifact_validators_reject_top_level_and_source_byte_tampering():
    sheets = run(fixture())
    bad = deepcopy(sheets)
    bad["invented"] = True
    with pytest.raises(ValueError, match="sheet_set_fields_invalid"):
        m.validate_standard_blast_database_sheet_set(bad)
    bad = deepcopy(sheets["prepared_inputs"])
    bad["resolved_documents"][0]["contents_hex"] = b">q\nIMPOSTOR\n".hex()
    with pytest.raises(ValueError, match="resolved_document_identity_conflict"):
        m.validate_standard_blast_database_prepared_inputs(bad)
    bad = deepcopy(sheets["search_bindings"][0])
    bad["binding"]["stage"] = "domain_database"
    with pytest.raises(ValueError, match="search_binding_stage_invalid"):
        m.validate_standard_blast_database_binding_result(bad)


def test_same_artifact_ref_does_not_merge_original_occurrences_and_conflicting_claims_fail():
    inputs = fixture()
    rows = inputs["artifact_catalog"]["entries"]
    stdout, stderr = next(r for r in rows if r["output_key"] == "stdout"), next(r for r in rows if r["output_key"] == "stderr")
    stderr["artifact_ref"] = stdout["artifact_ref"]
    inputs["contents"].pop("artifact-stderr")
    prepared = m.prepare_standard_blast_database_inputs(**inputs)
    assert [r["catalog"]["artifact_key"] for r in prepared["resolved_documents"] if r["catalog"]["artifact_ref"] == "artifact-stdout"] == ["stdout", "stderr"]
    inputs["artifact_catalog"]["retained_sources"].append(dict(source_ref="other-source", artifact_ref="artifact-stdout", sha256="0" * 64, size_bytes=1))
    with pytest.raises(ValueError, match="artifact_reference_identity_conflict"):
        m.prepare_standard_blast_database_inputs(**inputs)


@pytest.mark.parametrize("role", ["preparation_input_manifest", "offline_configuration"])
def test_selected_database_sidecar_original_role_compatibility(tmp_path, role):
    inputs = fixture(sidecar_role=role)
    payload = query_payload()
    payload["documents"] = [dict(document_key="sidecar", artifact=dict(kind="database_sidecar", database_key="target",
        role=role), format="json")]
    payload["sequence_records"] = [dict(input_key="query", record_ordinal=0, subject_ref=None, identity=None,
        source=dict(source_ref="sidecar", pointer=""))]
    add_metadata(inputs, payload, "query_identity", "sidecar-meta")
    prepared = m.prepare_standard_blast_database_inputs(**inputs)
    (tmp_path / "sidecar_counterexample.json").write_text(json.dumps(dict(inputs={k: v for k, v in inputs.items()
        if k not in {"contents", "subject_contents"}}, contents_hex={k: v.hex() for k, v in inputs["contents"].items()},
        result=prepared["metadata"][0]), indent=2))
    assert prepared["metadata"][0]["status"] == "valid", prepared["metadata"][0]["issues"]


@pytest.mark.parametrize("kind", ["sequence", "pssm"])
def test_saved_reuse_has_no_population_or_parser_calls(kind, monkeypatch):
    inputs = fixture() if kind == "sequence" else fixture("tblastn", kind="pssm", query=pssm(), doc=report("psitblastn", query_len=3, hits=[]))
    subject(inputs, "ACDEFGHI" if kind == "sequence" else "ACD", kind=kind)
    inputs["subject_snapshots"][0]["record_type"] = "input"
    if kind == "sequence":
        add_metadata(inputs, numerical_metadata(inputs), "sequence_database")
    # Actual serialized bundle bytes need not equal canonical serialization.
    inputs["artifact_catalog"]["bundle_sha256"] = sha(json.dumps(inputs["bundle"], indent=2).encode() + b"\n")
    sheets = run(inputs)
    original = deepcopy(sheets)
    def fail(*a, **kw):
        pytest.fail("saved reuse invoked a parser or population hook")
    from gene_annotation_episode import blast_sequence_database, blast_report_collection, native_blast_database_metadata
    from gene_annotation_episode import blast_pssm_inputs, blast_pssm_master_inputs
    with monkeypatch.context() as blocked:
        assert_pure(blocked)
        for obj, names in [(m, ["prepare_standard_blast_database_inputs", "populate_standard_blast_database_sheets",
                "derive_standard_blast_database_search_binding", "qualify_standard_blast_sequence_metadata",
                "validate_native_blast_database_metadata_payload", "read_blast_pssm", "extract_blast_pssm_master_metadata", "parse_sequences",
                "populate_blast_sequence_database_sheet"]),
                (blast_sequence_database, ["populate_blast_sequence_database_sheet"]),
                (blast_report_collection, ["parse_blast_report_collection"]),
                (native_blast_database_metadata, ["validate_native_blast_database_metadata_payload"]),
                (blast_pssm_inputs, ["read_blast_pssm"]), (blast_pssm_master_inputs, ["extract_blast_pssm_master_metadata"])]:
            for name in names:
                blocked.setattr(obj, name, fail)
        assert m.validate_standard_blast_database_sheet_set(sheets) == original
    assert sheets == original


@pytest.mark.parametrize("change", [
    lambda p: p["invocation"]["effective_options"].update({"-evalue": "invented"}),
    lambda p: p["invocation"]["operands"][0].update(subject_ref="invented"),
    lambda p: p["metadata"][0]["normalization_map"][0].update(payload_pointer="/documents/20"),
    lambda p: p["metadata"][1]["normalized"]["searches"][0]["reference_metadata"][0]["functions"][0].update(function="invented"),
    lambda p: p["sequence_proofs"][0].update(symbols="KLMNPQRSTV"),
    lambda p: p["source_relations"].append(deepcopy(next(r for r in p["source_relations"] if r["kind"] == "database"))),
])
def test_saved_original_relationship_tampering_is_rejected(change):
    inputs = fixture()
    subject(inputs, "ACDEFGHI")
    add_metadata(inputs, numerical_metadata(inputs), "sequence_database")
    prepared = run(inputs)["prepared_inputs"]
    change(prepared)
    with pytest.raises(ValueError):
        m.validate_standard_blast_database_prepared_inputs(prepared)


@pytest.mark.parametrize("change", [
    lambda s: s["metadata_binding_results"][0]["reference_metadata"][0].update(extra="invented"),
    lambda s: s["sequence"][0]["sheet"]["query_binding"].update(full_length=80),
    lambda s: s["search_bindings"][0]["binding"]["database_identity"].update(value="invented"),
    lambda s: s["sequence"][0]["sheet"]["report_source"].update(artifact_ref="invented"),
])
def test_saved_sheet_relations_are_closed_and_original(change):
    inputs = fixture()
    subject(inputs, "ACDEFGHI")
    add_metadata(inputs, numerical_metadata(inputs), "sequence_database")
    sheets = run(inputs)
    change(sheets)
    with pytest.raises(ValueError):
        m.validate_standard_blast_database_sheet_set(sheets)


def test_M1_original_job_metadata_and_original_manifest_slot_are_authenticated():
    payload = query_payload()
    payload["documents"] = [dict(document_key="selected-manifest", artifact=dict(kind="database_metadata_manifest",
        database_key="target", manifest_index=1), format="json")]
    payload["sequence_records"] = [dict(input_key="query", record_ordinal=0, subject_ref=None, identity=None,
        source=dict(source_ref="selected-manifest", pointer="/original_record_ordinal"))]
    inputs = fixture(original_metadata=payload, metadata_manifests=[encoded(dict(unrelated="first")), encoded(dict(original_record_ordinal=0))])
    sheets = run(inputs)
    parsed = sheets["prepared_inputs"]["metadata"][0]
    assert parsed["status"] == "valid"
    assert parsed["descriptor"]["origin"] == "original_job_input"
    assert parsed["normalized"]["documents"][0]["artifact"] == payload["documents"][0]["artifact"]
    assert parsed["normalization_map"][0] == dict(normalized_pointer="/documents/0", payload_pointer="/documents/0")
    inputs["bundle"]["database_manifest"][0]["metadata_manifest_artifacts"].reverse()
    with pytest.raises(ValueError, match="database_metadata_selection_mismatch"):
        m.prepare_standard_blast_database_inputs(**inputs)


def test_M4_dropped_metadata_unit_keeps_its_original_payload_ordinal():
    inputs = fixture()
    payload = numerical_metadata(inputs)
    missing = received(inputs, "missing-unit-census", encoded(dict(total=1000)))
    inputs["contents"].pop(missing["artifact"]["artifact_ref"])
    payload["documents"].insert(0, missing)
    dropped = deepcopy(payload["searches"][0])
    dropped["database_profile"]["source"] = missing["document_key"]
    payload["searches"].insert(0, dropped)
    add_metadata(inputs, payload, "sequence_database")
    sheets = run(inputs)
    prepared = sheets["prepared_inputs"]
    parsed = prepared["metadata"][0]
    assert len(parsed["normalized"]["searches"]) == 1
    assert dict(normalized_pointer="/searches/0", payload_pointer="/searches/1") in parsed["normalization_map"]
    assert prepared["sequence_proofs"][0]["pointer"] == "/searches/1/sequence_identity_bindings/0"
    assert dict(source_ref="source-metadata", pointer="/searches/1") in sheets["metadata_binding_results"][0]["input_pointers"]
    assert calculate(sheets)["components"]["function_weights"]["unadjusted_probabilities"] == {"F": .8, "G": .2}


def test_M3_multiple_fasta_records_do_not_invent_distinct_original_source_pointers(tmp_path):
    inputs = fixture()
    payload = numerical_metadata(inputs, format="fasta", census=False)
    add_metadata(inputs, payload, "sequence_database")
    sheets = run(inputs)
    proofs = sheets["prepared_inputs"]["sequence_proofs"]
    assert [r["proof"]["record_ordinal"] for r in proofs] == [0, 1]
    assert [r["status"] for r in proofs] == ["available", "available"]
    assert all(r["binding"]["binding"]["pointer"] == "" for r in proofs)
    assert sheets["sequence"][0]["sheet"]["sequence_identity_bindings"] == []
    assert any(r["detail_code"] == "full_sequence_source_identity_conflict" for r in sheets["metadata_binding_results"][0]["issues"])
    assert calculate(sheets)["components"]["database_sheet"]["hits"][0]["measurements"]["maximum_bit_score"] == 20
    save_example(tmp_path, inputs, sheets, calculate(sheets))


def test_saved_assembly_both_source_fields_retain_original_provenance():
    inputs = fixture()
    payload = numerical_metadata(inputs, census=False)
    source = received(inputs, "assembly", encoded(dict(completeness_percent=95, contamination_percent=125)))
    links = received(inputs, "assembly-links", encoded(dict(reference="S0.1", assembly="GCA_SYNTHETIC.1")))
    payload["documents"] += [source, links]
    assembly = dict(accession="GCA_SYNTHETIC.1", completeness_fraction=.95, contamination_fraction=1.25,
        contig_count=3, contig_n50=12000, total_sequence_length=31000, quality_method="synthetic CheckM",
        quality_version="synthetic-version", measurement_methods={k: "supplied_synthetic_measurement" for k in (
            "completeness_fraction", "contamination_fraction", "contig_count", "contig_n50", "total_sequence_length")},
        source=source["document_key"], linkage_source=links["document_key"])
    payload["searches"][0]["reference_metadata"][0]["assembly"] = assembly
    add_metadata(inputs, payload, "sequence_database")
    sheets = run(inputs)
    saved = sheets["sequence"][0]["sheet"]["reference_metadata"][0]["assembly"]
    assert saved == dict(assembly, source="source-assembly", linkage_source="source-assembly-links")
    assert saved["completeness_fraction"] == .95 and saved["contamination_fraction"] == 1.25
    original = sheets["prepared_inputs"]["metadata"][0]["payload"]["searches"][0]["reference_metadata"][0]["assembly"]
    assert original == assembly


def record_metadata(inputs, *, ordinals=(0, 1), raw=None, **kwargs):
    """Explicit synthetic assertions stay in JSON, independent of FASTA titles."""
    payload = numerical_metadata(inputs, format="fasta", census=False, **kwargs)
    assignments = received(inputs, "record-assignments", encoded(payload))
    payload["documents"].append(assignments)
    payload["schema"] = "native_blast_database_sequence_metadata_v2"
    unit = payload["searches"][0]
    for i, ordinal in enumerate(ordinals):
        locator = dict(kind="fasta_record", record_ordinal=ordinal)
        unit["reference_metadata"][i]["record_locator"] = deepcopy(locator)
        for function in unit["reference_metadata"][i]["functions"]:
            function["source"] = assignments["document_key"]
        unit["description_bindings"][i]["binding"]["metadata_record_locator"] = deepcopy(locator)
        unit["sequence_identity_bindings"][i]["binding"]["record_locator"] = deepcopy(locator)
        unit["sequence_proofs"][i]["record_ordinal"] = ordinal
    if raw is not None:
        doc = payload["documents"][0]["artifact"]
        doc.update(sha256=sha(raw), size_bytes=len(raw))
        for row in inputs["artifact_catalog"]["retained_sources"]:
            if row["artifact_ref"] == doc["artifact_ref"]:
                row.update(sha256=sha(raw), size_bytes=len(raw))
        inputs["contents"][doc["artifact_ref"]] = raw
    return payload


def test_record_v2_retained337_bytes_and339_wire_with_exact_v1_replay(tmp_path):
    retained = ROOT / "verification/tool_graders_standard_blast_database_metadata_2026-10-26_332/check009/temporary/pytest/test_M3_multiple_fasta_records0"
    public = ROOT / "verification/tool_graders_blast_fasta_record_public_associations_2026-10-26_339/check008"
    saved = json.loads((retained / "supplied_inputs.json").read_text())
    inputs = saved["inputs"]
    inputs.update(contents={k: bytes.fromhex(v) for k, v in saved["contents_hex"].items()},
                  subject_contents={k: bytes.fromhex(v) for k, v in saved["subject_contents_hex"].items()})
    old = run(inputs)
    assert old == json.loads((retained / "sheets.json").read_text())
    assert calculate(old) == json.loads((retained / "components.json").read_text())
    raw = (public / "new_wire_payload_v2.json").read_bytes()
    descriptor = json.loads((public / "new_descriptor_v2.json").read_text())
    inputs["artifact_catalog"]["retained_sources"].append(dict(source_ref="source-metadata-v2-339",
        **{k: descriptor[k] for k in ("artifact_ref", "sha256", "size_bytes")}))
    inputs["contents"][descriptor["artifact_ref"]] = raw
    inputs["metadata_payloads"] = [dict(descriptor=descriptor, payload=json.loads(raw))]
    sheets = run(inputs)
    proofs = sheets["prepared_inputs"]["sequence_proofs"]
    assert [r["status"] for r in proofs] == ["available", "available"]
    assert [r["binding"]["binding"]["record_locator"]["record_ordinal"] for r in proofs] == [0, 1]
    assert [r["symbols"] for r in proofs] == ["ACDEFGHIKL", "ACDEPQRSTV"]
    assert sheets["sequence"][0]["sheet"]["schema"] == "blast_sequence_database_result_sheet_v2"
    comp = calculate(sheets)["components"]
    assert comp["database_sheet"]["schema"] == "blast_database_sheet_v2"
    assert comp["function_weights"]["function_masses"] == {"F": 1, "G": .25}
    assert comp["function_weights"]["unadjusted_probabilities"] == {"F": .8, "G": .2}
    assert all(r["functions"][0]["source"] == "source-metadata" for r in sheets["sequence"][0]["sheet"]["reference_metadata"])
    save_example(tmp_path, inputs, sheets, calculate(sheets))


@pytest.mark.parametrize("same_content,assigned", [(False, True), (True, True), (False, False)])
def test_record_v2_full_sequence_grouping_and_absent_function_assignment(same_content, assigned):
    inputs = fixture()
    sequences = ("ACDEFGHIKL", "ACDEFGHIKL" if same_content else "ACDEPQRSTV")
    payload = record_metadata(inputs, sequences=sequences,
        raw=(">duplicate header\n" + sequences[0] + "\n>duplicate header\n" + sequences[1] + "\n").encode())
    if not assigned:
        for row in payload["searches"][0]["reference_metadata"]:
            row["functions"] = []
    add_metadata(inputs, payload, "sequence_database")
    sheets = run(inputs)
    comp = calculate(sheets)["components"]
    assert len(sheets["sequence"][0]["sheet"]["sequence_identity_bindings"]) == 2
    assert len(comp["database_sheet"]["sequence_groups"]) == (1 if same_content else 2)
    assert comp["function_weights"]["unadjusted_probabilities"] == (
        None if not assigned else {"F": .5, "G": .5} if same_content else {"F": .8, "G": .2})
    assert [h["measurements"]["maximum_bit_score"] for h in comp["database_sheet"]["hits"]] == [20, 18]


@pytest.mark.parametrize("ordinal,detail", [(1, "fasta_record_invalid"), (3, "fasta_record_ordinal_unavailable"), (2, None)])
def test_record_v2_sparse_original_slots_keep_siblings(ordinal, detail):
    inputs = fixture()
    payload = record_metadata(inputs, ordinals=(0, ordinal), raw=b">s0\nACDEFGHIKL\n>bad\n>s1\nACDEPQRSTV\n")
    add_metadata(inputs, payload, "sequence_database")
    sheets = run(inputs)
    proof = sheets["prepared_inputs"]["sequence_proofs"][1]
    assert proof["proof"]["record_ordinal"] == ordinal
    assert proof["status"] == ("available" if detail is None else "incompatible" if ordinal == 1 else "unavailable")
    scientific = sheets["sequence"][0]["sheet"]
    assert len(scientific["reference_metadata"]) == 2
    assert [r["binding"]["metadata_index"] for r in scientific["description_bindings"]] == ([0, 1] if detail is None else [0])
    assert [r["binding"]["hit_index"] for r in scientific["sequence_identity_bindings"]] == ([0, 1] if detail is None else [0])
    assert any(r.get("detail_code") == detail for r in sheets["issues"]) if detail else proof["symbols"] == "ACDEPQRSTV"
    assert len(calculate(sheets)["components"]["database_sheet"]["hits"]) == 2


@pytest.mark.parametrize("change,detail", [
    ("proof_ordinal", "sequence_proof_record_locator_conflict"),
    ("format", "record_locator_format_conflict"), ("null_fasta", "record_locator_format_conflict"),
    ("digest", "full_sequence_identity_conflict"), ("length", "full_sequence_identity_conflict"),
    ("molecule", "sequence_proof_binding_identity_conflict"), ("source", "sequence_proof_binding_identity_conflict"),
    ("metadata_cross_record", "blast_description_binding_sequence_record_mismatch"),
    ("description_cross_record", "blast_description_binding_metadata_provenance_mismatch"),
])
def test_record_v2_wrong_relations_keep_unaffected_native_measurements(change, detail):
    inputs = fixture()
    payload = record_metadata(inputs)
    unit = payload["searches"][0]
    binding, proof = unit["sequence_identity_bindings"][0]["binding"], unit["sequence_proofs"][0]
    if change == "proof_ordinal": proof["record_ordinal"] = 1
    elif change == "format": payload["documents"][0]["format"] = "text"
    elif change == "null_fasta": binding["record_locator"] = None
    elif change == "digest":
        binding.update(digest="0" * 64, sequence_group="sha256:" + "0" * 64)
        proof["sha256"] = "0" * 64
    elif change == "length": binding["sequence_length"] = proof["length"] = 9
    elif change == "molecule": binding["molecule"] = proof["molecule"] = "nt"
    elif change == "source": binding["source_ref"] = payload["documents"][-1]["document_key"]; binding["record_locator"] = None
    elif change == "metadata_cross_record":
        unit["reference_metadata"][0]["record_locator"]["record_ordinal"] = 1
        unit["description_bindings"][0]["binding"]["metadata_record_locator"]["record_ordinal"] = 1
        # Same source record can have only one identifier/taxon. Keep the other
        # metadata in a separately supplied JSON document to isolate this check.
        other = received(inputs, "separate-record", encoded(unit["reference_metadata"][1]))
        payload["documents"].append(other)
        unit["reference_metadata"][1].update(source=other["document_key"], record_locator=None)
        unit["description_bindings"][1]["binding"].update(metadata_source_ref=other["document_key"], metadata_record_locator=None)
    else: unit["description_bindings"][0]["binding"]["metadata_record_locator"]["record_ordinal"] = 1
    add_metadata(inputs, payload, "sequence_database")
    sheets = run(inputs)
    calculated = calculate(sheets)
    assert detail in {r.get("detail_code") for r in sheets["issues"]} | {r["code"] for r in calculated["issues"]}
    assert [r["measurements"]["maximum_bit_score"] for r in calculated["components"]["database_sheet"]["hits"]] == [20, 18]
    if change != "format":
        assert any(r["binding"]["hit_index"] == 1 for r in sheets["sequence"][0]["sheet"]["sequence_identity_bindings"])


@pytest.mark.parametrize("field", ["record_locator", "metadata_record_locator"])
@pytest.mark.parametrize("locator", [True, {"kind": "fasta_record", "record_ordinal": True}, {"kind": "fasta_record", "record_ordinal": -1},
    {"kind": "fasta_record", "record_ordinal": 0, "extra": 1}, {"kind": "other", "record_ordinal": 0}])
def test_record_v2_closed_locator_shapes_do_not_widen_wire(field, locator):
    inputs = fixture()
    payload = record_metadata(inputs)
    unit = payload["searches"][0]
    row = unit["sequence_identity_bindings" if field == "record_locator" else "description_bindings"][0]["binding"]
    row[field] = locator
    add_metadata(inputs, payload, "sequence_database")
    sheets = run(inputs)
    assert sheets["prepared_inputs"]["metadata"][0]["status"] == "invalid"
    assert len(calculate(sheets)["components"]["database_sheet"]["hits"]) == 2


@pytest.mark.parametrize("field", ["reference_metadata", "description_bindings", "sequence_identity_bindings"])
def test_record_v2_conflicting_pointer_rejects_only_bad_descriptor(field):
    inputs = fixture()
    bad = record_metadata(inputs)
    row = bad["searches"][0][field][0]
    if field != "reference_metadata": row = row["binding"]
    row[{"reference_metadata": "native_pointer", "description_bindings": "metadata_pointer", "sequence_identity_bindings": "pointer"}[field]] = "/0"
    add_metadata(inputs, bad, "sequence_database", "bad-record")
    good = numerical_metadata(inputs, key="separate-valid", sequences=("ACDEFGHIKL",), indices=(0,), description_ordinals=(0,), census=False)
    add_metadata(inputs, good, "sequence_database", "good-record")
    sheets = run(inputs)
    assert [r["status"] for r in sheets["prepared_inputs"]["metadata"]] == ["invalid", "valid"]
    assert sheets["prepared_inputs"]["metadata"][0]["payload"] == bad
    assert any(r.get("detail_code") == "record_locator_pointer_conflict" for r in sheets["issues"])
    assert calculate(sheets)["components"]["function_weights"]["unadjusted_probabilities"] == {"F": 1}


def test_record_v2_same_address_conflicting_sequence_claims_reject_all_affected():
    inputs = fixture()
    payload = record_metadata(inputs)
    unit = payload["searches"][0]
    unit["sequence_identity_bindings"][1]["binding"]["record_locator"]["record_ordinal"] = 0
    unit["sequence_proofs"][1]["record_ordinal"] = 0
    add_metadata(inputs, payload, "sequence_database")
    sheets = run(inputs)
    assert sheets["sequence"][0]["sheet"]["sequence_identity_bindings"] == []
    assert any(r.get("detail_code") == "full_sequence_source_identity_conflict" for r in sheets["issues"])


def test_record_v2_mixed_json_v1_descriptors_keep_original_shapes_and_offsets():
    inputs = fixture()
    first = numerical_metadata(inputs, key="json-first", sequences=("ACDEFGHIKL",), indices=(0,), description_ordinals=(0,), census=False)
    second = record_metadata(inputs, sequences=("ACDEPQRSTV",), indices=(1,), description_ordinals=(0,), ordinals=(0,))
    second["searches"][0]["reference_metadata"][0]["functions"][0]["function"] = "G"
    add_metadata(inputs, first, "sequence_database", "json-v1")
    add_metadata(inputs, second, "sequence_database", "fasta-v2")
    sheets = run(inputs)
    scientific = sheets["sequence"][0]["sheet"]
    assert scientific["schema"] == "blast_sequence_database_result_sheet_v2"
    assert "record_locator" not in scientific["reference_metadata"][0]
    assert scientific["reference_metadata"][1]["record_locator"] == dict(kind="fasta_record", record_ordinal=0)
    assert [r["binding"]["metadata_index"] for r in scientific["description_bindings"]] == [0, 1]
    assert calculate(sheets)["components"]["function_weights"]["unadjusted_probabilities"] == {"F": .8, "G": .2}


def test_record_v2_saved_recalculation_forbids_parsers_and_preserves_sheet(monkeypatch):
    from gene_annotation_episode import native_blast_database_metadata as native, blast_fasta_record_identity as fasta
    from gene_annotation_episode.native_blast_standard_database_calculators import calculate_standard_blast_database_sheets
    inputs = fixture()
    add_metadata(inputs, record_metadata(inputs, ordinals=(0, 2), raw=b">s0\nACDEFGHIKL\n>bad\n>s1\nACDEPQRSTV\n"), "sequence_database")
    sheets = run(inputs)
    original = encoded(sheets)
    def fail(*a, **kw): pytest.fail("saved recalculation invoked acquisition, preparation or parser")
    for obj, names in [(m, ("parse_sequences", "prepare_standard_blast_database_inputs", "populate_standard_blast_database_sheets",
                            "qualify_standard_blast_sequence_metadata", "validate_native_blast_database_metadata_payload")),
                       (native, ("parse_sequences", "parse_blast_fasta_source_records", "validate_native_blast_database_metadata_payload")),
                       (fasta, ("parse_blast_fasta_source_records", "parse_sequences")), (socket, ("socket",)), (subprocess, ("Popen", "run"))]:
        for name in names: monkeypatch.setattr(obj, name, fail)
    saved = m.validate_standard_blast_database_sheet_set(json.loads(original))
    calc = calculate_standard_blast_database_sheets(saved, sequence_model={"temperature_bits": 2})
    assert calc["sequence"][0]["components"]["components"]["function_weights"]["unadjusted_probabilities"] == {"F": 2 / 3, "G": 1 / 3}
    assert encoded(sheets) == original
    wrong = deepcopy(sheets)
    wrong["sequence"][0]["sheet"]["schema"] = "blast_sequence_database_result_sheet_v1"
    with pytest.raises(ValueError, match="blast_sequence_database_inner_binding_fields_invalid"):
        m.validate_standard_blast_database_sheet_set(wrong)


@pytest.mark.parametrize("change", [
    lambda p: p["sequence_proofs"][0]["proof"].update(record_ordinal=1),
    lambda p: p["sequence_proofs"][0]["binding"]["binding"]["record_locator"].update(record_ordinal=1),
    lambda p: p["sequence_proofs"][0]["document"].update(source_ref="invented"),
    lambda p: p["sequence_proofs"][0].update(symbols="ACDEPQRSTV"),
    lambda p: p["metadata"][0]["normalized"]["searches"][0]["reference_metadata"][0]["record_locator"].update(record_ordinal=1),
])
def test_record_v2_saved_original_proof_and_locator_tampering_rejected(change):
    inputs = fixture()
    add_metadata(inputs, record_metadata(inputs), "sequence_database")
    prepared = run(inputs)["prepared_inputs"]
    change(prepared)
    with pytest.raises(ValueError): m.validate_standard_blast_database_prepared_inputs(prepared)


def test_record_v2_json_null_locators_keep_literal_pointer_semantics():
    inputs = fixture()
    payload = numerical_metadata(inputs)
    payload["schema"] = "native_blast_database_sequence_metadata_v2"
    for unit in payload["searches"]:
        for row in unit["reference_metadata"]: row["record_locator"] = None
        for row in unit["description_bindings"]: row["binding"]["metadata_record_locator"] = None
        for row in unit["sequence_identity_bindings"]: row["binding"]["record_locator"] = None
    add_metadata(inputs, payload, "sequence_database")
    sheets = run(inputs)
    weights = calculate(sheets)["components"]["function_weights"]
    assert weights["unadjusted_probabilities"] == {"F": .8, "G": .2}
    assert weights["representation_adjusted_probabilities"] == pytest.approx({"F": 2 / 7, "G": 5 / 7})
    assert [r["binding"]["binding"]["pointer"] for r in sheets["prepared_inputs"]["sequence_proofs"]] == ["/0", "/1"]


def test_record_v2_same_metadata_record_conflict_and_unproved_native_data():
    inputs = fixture()
    payload = record_metadata(inputs)
    unit = payload["searches"][0]
    unit["reference_metadata"][1]["record_locator"]["record_ordinal"] = 0
    unit["description_bindings"][1]["binding"]["metadata_record_locator"]["record_ordinal"] = 0
    unit["sequence_proofs"] = []
    add_metadata(inputs, payload, "sequence_database")
    sheets = run(inputs)
    result = calculate(sheets)
    assert not sheets["sequence"][0]["sheet"]["sequence_identity_bindings"]
    assert "blast_description_binding_metadata_record_conflict" in {r["code"] for r in result["issues"]}
    assert result["components"]["function_weights"]["unadjusted_probabilities"] is None
    assert [r["measurements"]["maximum_bit_score"] for r in result["components"]["database_sheet"]["hits"]] == [20, 18]


@pytest.mark.parametrize("alter", ["file_digest", "file_size", "declared_source", "bytes"])
def test_record_v2_file_receipt_failures_never_repair_by_header(alter):
    inputs = fixture()
    payload = record_metadata(inputs)
    artifact = payload["documents"][0]["artifact"]
    if alter == "file_digest": artifact["sha256"] = "0" * 64
    elif alter == "file_size": artifact["size_bytes"] += 1
    elif alter == "declared_source": artifact["source_ref"] = "unreceived-source"
    else: inputs["contents"][artifact["artifact_ref"]] = b">s0\nACDEFGHIKL\n>s1\nDIFFERENT\n"
    add_metadata(inputs, payload, "sequence_database")
    sheets = run(inputs)
    assert sheets["prepared_inputs"]["metadata"][0]["payload"] == payload
    assert not sheets["sequence"][0]["sheet"]["sequence_identity_bindings"]
    assert len(calculate(sheets)["components"]["database_sheet"]["hits"]) == 2
