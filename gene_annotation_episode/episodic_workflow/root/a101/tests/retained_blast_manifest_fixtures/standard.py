"""Exact original synthetic full bundle fixture; no native executable is used."""
from copy import deepcopy
import hashlib
import json
from gene_annotation_episode.episodic_workflow.root.a101.library import native_blast_standard_database_contracts as n

def identity(path):
    return {'path': path, 'sha256': 'a' * 64, 'size_bytes': 12, 'artifact_ref': None}

def database(kind='blast_protein_sequence'):
    source = {'source_ref': 'synthetic_source', 'pointer': '/preparation'}
    ident = {'namespace': 'synthetic', 'value': 'target', 'version': None, 'release': None,
        'scope': None, 'preparation_type': 'sequence_database', 'source': source}
    paths = ['/selected/db/target']
    prefix = 'p' if kind == 'blast_protein_sequence' else 'n'
    manifest = {'version': 'native_blast_standard_prepared_database_manifest_v1', 'database_key': 'target',
        'kind': kind, 'identity': ident, 'native_paths': paths,
        'files': [{'path': paths[0] + '.' + prefix + suffix, 'sha256': 'b' * 64, 'size_bytes': 23}
                  for suffix in ['hr', 'in', 'sq']],
        'preparation': {'method': 'publisher_package', 'preparation_type': 'sequence_database',
            'software': {'name': 'synthetic preparation', 'version': None, 'executable_sha256': None},
            'argv': None, 'source': source, 'input_manifest': None, 'receipt': identity('/selected/receipt')},
        'metadata_manifests': [], 'access': {'mode': 'prepared_local', 'offline_configuration': None},
        'inventory_complete': True}
    return {'database_key': 'target', 'role': 'target', 'kind': kind, 'identity': ident,
        'native_paths': paths, 'manifest_file': identity('/selected/manifest'), 'manifest': manifest}

def job_for(program='blastp', query='sequence', fmt='json15'):
    return {'version': 'native_blast_standard_database_job_v1', 'program': program, 'mode': 'database',
        'software': {'executable': '/selected/bin/' + program, 'sha256': 'c' * 64, 'engine_version': '2.17.0+'},
        'environment': {'EXPLICIT': 'selected'}, 'inputs': [{'input_key': 'query', 'role': 'query_' + query,
            'format': 'fasta' if query == 'sequence' else 'scoremat_asn_text', **identity('/selected/query')}],
        'query': {'kind': query, 'input_key': 'query'},
        'databases': [database('blast_protein_sequence' if program in {'blastp', 'blastx'} else 'blast_nucleotide_sequence')],
        'options': [], 'outputs': [
            {'output_key': role, 'role': role, 'path_kind': 'file', 'relative_path': role + '.txt', 'format': 'text',
             'fields': [], 'delimiter': None, 'required': True} for role in ['stdout', 'stderr']
        ] + [{'output_key': 'report', 'role': 'primary_report', 'path_kind': 'file', 'relative_path': 'report',
              'format': fmt, 'fields': [] if fmt == 'json15' else ['qseqid', 'sseqid', 'bitscore'],
              'delimiter': None, 'required': True}],
        'metadata_inputs': [], 'grading_parameters': {'sequence_database_model': None}}

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
