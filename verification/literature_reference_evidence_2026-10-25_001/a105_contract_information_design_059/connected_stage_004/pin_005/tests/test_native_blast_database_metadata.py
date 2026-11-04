"""Synthetic captured metadata fixtures; no native search, Store or network work."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

import pytest

from gene_annotation_episode import native_blast_database_metadata as m
from gene_annotation_episode import native_blast_database_contracts as contracts
from gene_annotation_episode.blast_report_collection import parse_blast_report_collection
from gene_annotation_episode.blast_iteration_calculators import calculate_blast_iteration_components
from gene_annotation_episode.blast_profile_calculators import calculate_blast_profile_components
from gene_annotation_episode.blast_vdb_calculators import calculate_blast_vdb_components
from test_native_blast_database_contracts import job_for
from test_blast_sequence_database import document, native_search, hsp


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def ref(kind, value):
    return kind + "_" + digest(str(value).encode())[:24]


def empty_payload(consumer):
    schema = m._SCHEMAS[consumer]
    return {k: schema["properties"][k]["enum"][0] if k == "schema" else [] for k in schema["properties"]}


def address():
    return dict(output_key="report", member_ordinal=None, report_index=0,
                search_pointer="/BlastOutput2/0/report/results/search")


def fixture(tmp_path, program="psiblast", kind="sequence", query=None, report=None):
    job = job_for(program, kind)
    if query is None:
        query = b">q\nACGTACGTACGT\n" if program in {"blastn_vdb", "rpstblastn"} else b">q\nACDEFGHIKLMN\n"
    if report is None:
        report = document(program, native_search(query_len=12))
        report["BlastOutput2"][0]["report"]["search_target"]["db"] = "target"
    catalog = dict(bundle_source_ref=ref("source", "bundle"), bundle_artifact_ref=ref("artifact", "bundle"),
        bundle_sha256="a" * 64, entries=[], retained_sources=[])
    bundle = dict(artifacts=[], input_manifest=[], output_manifest=[], database_manifest=[],
        process=dict(started=True, returncode=0), sealed_at="2026-10-26T00:00:00Z", failures=[])

    def capture(key, raw, role, format, *, input_key=None, output_key=None, database_key=None):
        path = tmp_path / key
        path.write_bytes(raw)
        entry = dict(artifact_key=key, artifact_ref=ref("artifact", key), source_ref=ref("source", key),
            path=str(path), sha256=digest(raw), size_bytes=len(raw), input_key=input_key, output_key=output_key,
            database_key=database_key, role=role, relative_path=key, format=format, fields=[], delimiter=None)
        catalog["entries"].append(entry)
        bundle["artifacts"].append({k: deepcopy(v) for k, v in entry.items() if k not in {"path", "artifact_ref", "source_ref"}} | {"content_assessment": "not_parsed"})
        return entry

    q = capture("query", query, "query_" + kind, job["inputs"][0]["format"], input_key="query")
    job["inputs"][0].update(sha256=q["sha256"], size_bytes=q["size_bytes"])
    bundle["input_manifest"].append(dict(input_key="query", artifact_key="query", original_path=job["inputs"][0]["path"],
        realized_path=q["path"], expected_sha256=q["sha256"], observed_sha256=q["sha256"], size_bytes=q["size_bytes"]))
    for db in job["databases"]:
        db["identity"].update(version="1", release="r1", scope="selected_sequences")
        raw = encoded(db["manifest"])
        row = capture(db["database_key"] + "-manifest", raw, "database_manifest", "json", database_key=db["database_key"])
        db["manifest_file"].update(sha256=digest(raw), size_bytes=len(raw))
        bundle["database_manifest"].append(dict(database_key=db["database_key"], native_paths=db["native_paths"],
            manifest_artifact_key=row["artifact_key"], preparation_receipt_artifact_key=None,
            metadata_manifest_artifacts=[], sidecar_artifacts=[], checks=[dict(status="verified", expected_sha256=r["sha256"],
            observed_sha256=r["sha256"], path=r["path"], size_bytes=r["size_bytes"], checked_at="2026-10-26T00:00:00Z") for r in db["manifest"]["files"]]))
    captured_report = capture("report", encoded(report), "primary_report", "json15", output_key="report")
    bundle["output_manifest"].append(dict(output_key="report", artifact_keys=["report"], presence="present"))
    bundle["requested_job"] = contracts.requested_job_from_native_blast_database(job)
    return job, bundle, catalog, capture


def source(tmp_path, catalog, key, raw, format="json"):
    path = tmp_path / (key + ".source")
    path.write_bytes(raw)
    entry = dict(source_ref=ref("source", key), artifact_ref=ref("artifact", key), sha256=digest(raw), size_bytes=len(raw), path=str(path))
    catalog["retained_sources"].append(entry)
    return dict(document_key=key, artifact=dict(kind="received", **{k: entry[k] for k in ("source_ref", "artifact_ref", "sha256", "size_bytes")}), format=format)


def metadata(tmp_path, catalog, consumer, payload, key="metadata", *, raw=None):
    raw = encoded(payload) if raw is None else raw
    doc = source(tmp_path, catalog, key, raw)
    descriptor = dict(input_key=key, consumer=consumer, schema_id=empty_payload(consumer)["schema"],
        **{k: doc["artifact"][k] for k in ("artifact_ref", "sha256", "size_bytes")}, origin="selected_results_input")
    return dict(descriptor=descriptor, payload=payload)


def prepared(job, bundle, catalog, payloads=(), snapshots=()):
    return m.prepare_native_blast_database_inputs(job=job, bundle=bundle, artifact_catalog=catalog,
        metadata_payloads=list(payloads), subject_snapshots=list(snapshots))


def collect(prep, catalog):
    rows = [r for r in catalog["entries"] if r["role"] == "primary_report"]
    return parse_blast_report_collection({r["artifact_key"]: Path(r["path"]).read_bytes() for r in rows},
        artifacts=[dict(artifact_key=r["artifact_key"], role=r["role"], format=r["format"], fields=None, delimiter=None) for r in rows],
        invocation=prep["invocation"])


def populate(prep, catalog):
    return m.populate_native_blast_database_sheets(collect(prep, catalog), prepared_inputs=prep, artifact_catalog=catalog)


def forbid_scoring(monkeypatch):
    from gene_annotation_episode import blast_iteration_calculators, blast_profile_calculators, blast_pssm_calculators, blast_vdb_calculators, blast_database_grader, blast_sequence_database
    def fail(*a, **kw):
        pytest.fail("metadata population called a calculator")
    for module in (blast_iteration_calculators, blast_profile_calculators, blast_pssm_calculators, blast_vdb_calculators, blast_database_grader, blast_sequence_database):
        for name in dir(module):
            if name.startswith("calculate_"):
                monkeypatch.setattr(module, name, fail)
    monkeypatch.setattr(subprocess, "Popen", fail)
    monkeypatch.setattr(socket, "socket", fail)


@pytest.mark.parametrize("consumer", [r["consumer"] for r in m.metadata_schema_registry()])
def test_exact_registry_closed_shapes_pure_and_detached(tmp_path, monkeypatch, consumer):
    job, bundle, catalog, _ = fixture(tmp_path)
    raw = metadata(tmp_path, catalog, consumer, empty_payload(consumer))
    docs = dict(descriptor=raw["descriptor"], documents=[], primary_reports=[],
        bundle_source_ref=catalog["bundle_source_ref"], bundle_artifact_ref=catalog["bundle_artifact_ref"])
    forbid_scoring(monkeypatch)
    monkeypatch.setattr(Path, "read_bytes", lambda *_: pytest.fail("pure validator read a path"))
    output = m.validate_native_blast_database_metadata_payload(raw["payload"], descriptor=raw["descriptor"], document_catalog=docs, job=job)
    assert output["status"] == "valid"
    assert output["normalized"] == raw["payload"]
    assert output["normalization_map"] == []
    output["payload"]["documents"].append("changed")
    assert raw["payload"]["documents"] == []
    bad = deepcopy(raw["payload"])
    bad["extra"] = 1
    assert m.validate_native_blast_database_metadata_payload(bad, descriptor=raw["descriptor"], document_catalog=docs, job=job)["status"] == "invalid"
    other = dict(raw["descriptor"], schema_id="unknown_v1")
    unsupported = m.validate_native_blast_database_metadata_payload(bad, descriptor=other, document_catalog=dict(docs, descriptor=other), job=job)
    assert unsupported["status"] == "unsupported" and unsupported["payload"] == bad
    with pytest.raises(ValueError, match="finite_json"):
        m.validate_native_blast_database_metadata_payload(float("nan"), descriptor=raw["descriptor"], document_catalog=docs, job=job)


@pytest.mark.parametrize("program,stage", [("psiblast", "sequence_database"), ("rpsblast", "domain_database"), ("rpstblastn", "domain_database"), ("deltablast", None), ("blastn_vdb", None), ("tblastn_vdb", None)])
def test_actual_six_public_routes_without_calculation(tmp_path, monkeypatch, program, stage):
    job, bundle, catalog, _ = fixture(tmp_path, program)
    forbid_scoring(monkeypatch)
    prep = prepared(job, bundle, catalog)
    sheet_set = populate(prep, catalog)
    assert prep["query_records"][0]["length"] == 12
    assert sheet_set["collection"]["searches"][0]["operand_binding"] == prep["invocation"]["operands"][0]
    assert [d["binding"]["stage"] for d in sheet_set["derived_search_bindings"]] == ([] if stage is None else [stage])
    if program in {"psiblast", "deltablast"}:
        assert sheet_set["iteration"]["schema"] == "blast_iteration_sheet_v2"
        assert sheet_set["iteration"]["search_bindings"][0]["biological_round"] is None
    elif program in {"rpsblast", "rpstblastn"}:
        assert len(sheet_set["profile"]) == 1
    else:
        assert len(sheet_set["vdb"]) == 1 and sheet_set["sequence"] == []


def test_partial_lowering_preserves_original_rows_and_exact_pointers(tmp_path):
    job, bundle, catalog, _ = fixture(tmp_path)
    good = source(tmp_path, catalog, "good", b'{"record":{}}')
    missing = dict(document_key="missing", artifact=dict(kind="received", source_ref=ref("source", "missing"),
        artifact_ref=ref("artifact", "missing"), sha256="b" * 64, size_bytes=12), format="json")
    payload = empty_payload("query_identity")
    payload["documents"] = [missing, good]
    payload["sequence_records"] = [dict(input_key="query", record_ordinal=i, subject_ref=None, identity=None,
        source=dict(source_ref=key, pointer="/record")) for i, key in enumerate(("missing", "good"))]
    row = metadata(tmp_path, catalog, "query_identity", payload)
    value = prepared(job, bundle, catalog, [row])["metadata"][0]
    assert value["status"] == "valid"
    assert len(value["payload"]["sequence_records"]) == 2
    assert [r["record_ordinal"] for r in value["normalized"]["sequence_records"]] == [1]
    assert dict(normalized_pointer="/sequence_records/0", payload_pointer="/sequence_records/1") in value["normalization_map"]
    assert any(i["pointer"] == "/sequence_records/0/source" for i in value["issues"])
    bad = deepcopy(payload)
    bad["sequence_records"][1]["record_ordinal"] = True
    broken = metadata(tmp_path, catalog, "query_identity", bad, "bad")
    output = prepared(job, bundle, catalog, [row, broken])
    assert [r["status"] for r in output["metadata"]] == ["valid", "invalid"]


@pytest.mark.parametrize("raw", [b'{"schema":1,"schema":2}', b'{"v":NaN}'])
def test_invalid_raw_json_retains_descriptor_but_null_native_value(tmp_path, raw):
    job, bundle, catalog, _ = fixture(tmp_path)
    md = metadata(tmp_path, catalog, "query_identity", None, raw=raw)
    result = prepared(job, bundle, catalog, [md])
    assert result["metadata"][0]["status"] == "invalid"
    assert result["metadata"][0]["payload"] is None
    assert result["metadata"][0]["sha256"] == digest(raw)
    assert len(result["query_records"]) == 1


@pytest.mark.parametrize("same_sequence", [True, False])
def test_full_subject_sequence_not_length_or_hash_claim_controls_biology(tmp_path, same_sequence):
    job, bundle, catalog, _ = fixture(tmp_path)
    actual = b"ACDEFGHIKLMN" if same_sequence else b"NNNNNNNNNNNN"
    subject = source(tmp_path, catalog, "subject", actual, "text")
    proof = source(tmp_path, catalog, "proof", b'{"relation":true}')
    subject_ref = ref("input", "subject")
    snapshot = dict(subject_ref=subject_ref, record_type="input", molecule="protein", length=12,
        sequence_sha256=digest(actual), sequence_artifact_ref=subject["artifact"]["artifact_ref"], sequence_path=catalog["retained_sources"][-2]["path"])
    payload = empty_payload("query_identity")
    payload["documents"] = [proof]
    payload["sequence_records"] = [dict(input_key="query", record_ordinal=0, subject_ref=subject_ref, identity=None,
        source=dict(source_ref="proof", pointer="/relation"))]
    row = metadata(tmp_path, catalog, "query_identity", payload)
    prep = prepared(job, bundle, catalog, [row], [snapshot])
    assert prep["query_records"][0]["subject_ref"] == (subject_ref if same_sequence else None)
    assert prep["query_records"][0]["binding_status"] == ("available" if same_sequence else "incompatible")


def test_duplicate_names_and_original_hsp_description_ordinals_survive(tmp_path):
    native = native_search(query_len=12, hits=[False, dict(len=10, description=[False, dict(id="A", accession="A.1", title="A", taxid=None)], hsps=[None, hsp()])])
    report = document(search=native)
    report["BlastOutput2"][0]["report"]["search_target"]["db"] = "target"
    job, bundle, catalog, _ = fixture(tmp_path, query=b">q\nACDEFGHIKLMN\n>q\nACDEFGHIKLMN\n", report=report)
    sheets = populate(prepared(job, bundle, catalog), catalog)
    search = sheets["collection"]["searches"][0]
    assert search["operand_binding"] is None
    assert search["normalized"]["hits"][0]["hit_index"] == 1
    assert search["row_map"][0]["description_ordinals"] == [1]
    assert search["row_map"][0]["hsp_ordinals"] == [1]


@pytest.mark.parametrize("target,program", [("wrong", "psiblast"), ("target", "phiblastp")])
def test_no_stage_from_unmatched_target_or_phi_alias(tmp_path, target, program):
    report = document(program, native_search(query_len=12))
    report["BlastOutput2"][0]["report"]["search_target"]["db"] = target
    job, bundle, catalog, _ = fixture(tmp_path, report=report)
    sheets = populate(prepared(job, bundle, catalog), catalog)
    assert sheets["derived_search_bindings"] == []
    assert sheets["iteration"]["search_bindings"][0]["stage"] is None


def test_omitted_msa_selection_never_calls_fabricated_zero(tmp_path, monkeypatch):
    text = b"CLUSTAL W\n\nq  AC-D\nx  ACGD\n"
    job, bundle, catalog, _ = fixture(tmp_path, kind="msa", query=text)
    monkeypatch.setattr(m._pssm, "read_blast_msa_master", lambda *a, **kw: pytest.fail("fabricated master"))
    prep = prepared(job, bundle, catalog)
    assert prep["selected_master_record_ordinal"] is None
    assert prep["effective_master_record_ordinal"] is None
    assert prep["invocation"]["operands"] == [] and prep["msa_sheets"] == []


def test_separately_sourced_effective_msa_master_parsed_once(tmp_path, monkeypatch):
    text = b"CLUSTAL W\n\nq  AC-D\nx  ACGD\n"
    job, bundle, catalog, _ = fixture(tmp_path, kind="msa", query=text)
    doc = source(tmp_path, catalog, "effective", b'{"ordinal":1}')
    payload = empty_payload("query_identity")
    payload["documents"] = [doc]
    payload["effective_msa_masters"] = [dict(input_key="query", record_ordinal=1, source=dict(source_ref="effective", pointer="/ordinal"))]
    raw = metadata(tmp_path, catalog, "query_identity", payload)
    original, calls = m._pssm.read_blast_msa_master, []
    def spy(*a, **kw):
        calls.append(kw["master_record_ordinal"])
        return original(*a, **kw)
    monkeypatch.setattr(m._pssm, "read_blast_msa_master", spy)
    prep = prepared(job, bundle, catalog, [raw])
    assert calls == [1]
    assert prep["selected_master_record_ordinal"] is None and prep["effective_master_record_ordinal"] == 1
    assert prep["query_records"][0]["record_ordinal"] == 1
    assert prep["query_records"][0]["sequence"] == "ACGD"


def test_pssm_master_public_extractor_and_parser_once(tmp_path, monkeypatch):
    text = b'Pssm ::= { isProtein TRUE, numRows 2, numColumns 3, byRow FALSE, query seq { id { local str "q" }, descr { title "q" }, inst { repr raw, mol aa, length 3, seq-data iupacaa "ACD" } }, finalData { scores { -2, 0, 5, 7, -32768, 9 } } }'
    job, bundle, catalog, _ = fixture(tmp_path, kind="pssm", query=text, report=document(search=native_search(query_len=3)))
    calls, original = [], m._pssm.read_blast_pssm
    def spy(*a, **kw):
        calls.append(kw["artifact_key"])
        return original(*a, **kw)
    monkeypatch.setattr(m._pssm, "read_blast_pssm", spy)
    forbid_scoring(monkeypatch)
    prep = prepared(job, bundle, catalog)
    assert calls == ["query"]
    assert prep["query_records"][0]["sequence"] == "ACD"
    assert prep["query_records"][0]["subject_ref"] is None
    sheets = populate(prep, catalog)
    assert calls == ["query"] and sheets["pssm"] == prep["pssm_sheets"]


def test_unbound_extractor_claim_is_invalid_not_supplied_convergence(tmp_path):
    job, bundle, catalog, _ = fixture(tmp_path)
    payload = empty_payload("iteration")
    payload["convergence_records"] = [dict(record_key="converged", search_key=None, query_operand=None,
        native_converged=True, evidence=dict(origin="native_extractor_output", source=dict(source_ref="d", pointer=""),
            source_format="text", original_record="CONVERGED", extractor=dict(module="x", function="y", version="z")))]
    row = metadata(tmp_path, catalog, "iteration", payload)
    prep = prepared(job, bundle, catalog, [row])
    assert prep["metadata"][0]["status"] == "invalid"
    assert prep["metadata"][0]["issues"][0]["code"] == "native_blast_metadata_extractor_unbound"


def sequence_payload(tmp_path, catalog, *, wrong_sequence=False):
    data = dict(records=[dict(identifier="reference-0", sequence="ACDEFGHIKL"), dict(identifier="reference-1", sequence="ACDEPQRSTV")],
        links=[{}, {}], population=dict(F=200, G=50))
    if wrong_sequence:
        data["records"][0]["sequence"] = "XXXXXXXXXX"
    doc = source(tmp_path, catalog, "facts", encoded(data))
    payload = empty_payload("sequence_database")
    payload["documents"] = [doc]
    unit = dict(search_key=address(), reference_metadata=[], description_bindings=[], sequence_identity_bindings=[], sequence_proofs=[],
        database_profile=dict(database="target", release="r1", scope="selected_sequences", source="facts", count_unit="unique_sequences", total_count=1000,
                              function_counts=dict(F=200, G=50)))
    for i, symbols in enumerate(("ACDEFGHIKL", "ACDEPQRSTV")):
        meta = dict(identifier_namespace="synthetic", accession="reference-" + str(i), source="facts", native_pointer=f"/records/{i}",
            taxid=i+1, lineage=[dict(taxid=i+1, rank="genus", name=None)],
            functions=[dict(function="F" if i == 0 else "G", evidence=["supplied"], source="facts")], origin={}, assembly=None,
            sequence_group=None, study_groups=[], native_record=data["records"][i])
        unit["reference_metadata"].append(meta)
        description = native_search()["hits"][i]["description"][0]
        unit["description_bindings"].append(dict(search_key=address(), binding=dict(report_index=0, hit_index=i, description_index=0,
            metadata_index=i, native_description={k: description.get(k) for k in ("id", "accession", "title", "taxid")},
            metadata_identifier=dict(namespace="synthetic", value=meta["accession"]), metadata_source_ref="facts", metadata_pointer=f"/records/{i}",
            linkage_source_ref="facts", linkage_pointer=f"/links/{i}")))
        sha = digest(symbols.encode())
        unit["sequence_identity_bindings"].append(dict(search_key=address(), binding=dict(report_index=0, hit_index=i, kind="full_sequence_digest",
            sequence_group="sha256:" + sha, algorithm="sha256", digest=sha, molecule="aa", sequence_length=10,
            source_ref="facts", pointer=f"/records/{i}", linkage_source_ref="facts", linkage_pointer=f"/links/{i}")))
        unit["sequence_proofs"].append(dict(binding_index=i, document_key="facts", representation="json_sequence", record_ordinal=None,
            sequence_pointer=f"/records/{i}/sequence", molecule="aa", sha256=sha, length=10))
    payload["searches"] = [unit]
    return payload


def test_metadata_path_numerical_sequence_oracle_and_preserved_full_inputs(tmp_path):
    report = document(search=native_search(query_len=8))
    report["BlastOutput2"][0]["report"]["search_target"]["db"] = "target"
    job, bundle, catalog, _ = fixture(tmp_path, report=report)
    job["options"] = ["-query_loc", "3-10"]
    bundle["requested_job"] = contracts.requested_job_from_native_blast_database(job)
    payload = sequence_payload(tmp_path, catalog)
    raw = metadata(tmp_path, catalog, "sequence_database", payload)
    prep = prepared(job, bundle, catalog, [raw])
    before = deepcopy(prep)
    sheets = populate(prep, catalog)
    assert prep == before
    assert len(sheets["sequence"][0]["sheet"]["sequence_identity_bindings"]) == 2
    calc = calculate_blast_iteration_components(sheets["iteration"])
    components = calc["searches"][0]["sequence_components"]["components"]
    measured = components["database_sheet"]["hits"][0]["measurements"]
    assert measured["maximum_bit_score"] == 20 and measured["minimum_evalue"] == 0
    assert measured["observed_paired_query_positions"] == 4
    assert measured["query_paired_coverage"] == 4/12 and measured["reference_paired_coverage"] == 4/10
    assert components["selected_query_coverage"][0]["value"] == 4/8
    assert components["function_weights"]["function_masses"] == {"F": 1, "G": .25}
    assert components["function_weights"]["unadjusted_probabilities"] == {"F": .8, "G": .2}
    assert components["function_weights"]["representation_adjusted_probabilities"] == {"F": .5, "G": .5}
    warmer = calculate_blast_iteration_components(sheets["iteration"], sequence_model={"temperature_bits": 2})
    assert warmer["searches"][0]["sequence_components"]["components"]["function_weights"]["unadjusted_probabilities"] == {"F": 2/3, "G": 1/3}
    (tmp_path / "sequence-sheets.json").write_bytes(encoded(sheets))
    (tmp_path / "sequence-calculations.json").write_bytes(encoded(calc))
    (tmp_path / "sequence-inputs.json").write_bytes(encoded(dict(job=job, bundle=bundle, artifact_catalog=catalog, metadata_payloads=[raw], subject_snapshots=[])))


def test_unverified_full_sequence_binding_is_retained_but_not_demonstrated(tmp_path):
    job, bundle, catalog, _ = fixture(tmp_path)
    payload = sequence_payload(tmp_path, catalog, wrong_sequence=True)
    raw = metadata(tmp_path, catalog, "sequence_database", payload)
    sheets = populate(prepared(job, bundle, catalog, [raw]), catalog)
    assert len(sheets["prepared_inputs"]["metadata"][0]["normalized"]["searches"][0]["sequence_identity_bindings"]) == 2
    demonstrated = sheets["sequence"][0]["sheet"]["sequence_identity_bindings"]
    assert len(demonstrated) == 1 and demonstrated[0]["binding"]["hit_index"] == 1
    assert any(i["pointer"] == "/searches/0/sequence_identity_bindings/0" for i in sheets["issues"])


def test_orphan_full_sequence_proof_is_retained_and_qualified(tmp_path):
    job, bundle, catalog, _ = fixture(tmp_path)
    payload = sequence_payload(tmp_path, catalog)
    payload["searches"][0]["sequence_proofs"].append(
        dict(payload["searches"][0]["sequence_proofs"][0], binding_index=7))
    raw = metadata(tmp_path, catalog, "sequence_database", payload)
    sheets = populate(prepared(job, bundle, catalog, [raw]), catalog)
    assert sheets["prepared_inputs"]["metadata"][0]["payload"] == payload
    assert len(sheets["sequence"][0]["sheet"]["sequence_identity_bindings"]) == 2
    assert any(i["pointer"] == "/searches/0/sequence_proofs/2"
               and i["detail_code"] == "sequence_proof_binding_index_unresolved" for i in sheets["issues"])


def test_pssm_wire_key_matches_public_utf8_record_identity(tmp_path):
    text = b'Pssm ::= { isProtein TRUE, numRows 2, numColumns 3, byRow FALSE, query seq { id { local str "q" }, inst { repr raw, mol aa, length 3, seq-data iupacaa "ACD" } }, finalData { scores { -2, 0, 5, 7, -32768, 9 } } }'
    job, bundle, catalog, _ = fixture(tmp_path, kind="pssm", query=text)
    for entry in catalog["entries"] + bundle["artifacts"]:
        if entry["artifact_key"] == "query":
            entry["artifact_key"] = "requête"
    bundle["input_manifest"][0]["artifact_key"] = "requête"
    payload = empty_payload("iteration")
    payload["documents"] = [dict(document_key="input", artifact=dict(kind="input", input_key="query"), format="scoremat_asn_text")]
    payload["checkpoint_bindings"] = [dict(pssm_key=dict(document_key="input", record_ordinal=0),
        role="input", search_key=None, biological_round=None, provenance=dict(source_ref="input", pointer=""))]
    raw = metadata(tmp_path, catalog, "iteration", payload)
    prep = prepared(job, bundle, catalog, [raw])
    assert prep["metadata"][0]["status"] == "valid", prep["issues"]
    expected = prep["pssm_sheets"][0]["pssms"][0]["pssm_key"]
    assert expected == '["requête",0]'
    assert prep["metadata"][0]["normalized"]["checkpoint_bindings"][0]["pssm_key"] == expected


@pytest.mark.parametrize("program,units", [("rpsblast", 50), ("rpstblastn", 150)])
def test_metadata_path_profile_model_numerics(tmp_path, program, units):
    from test_blast_profile_inputs import synthetic_hit
    translated = program == "rpstblastn"
    hit = synthetic_hit(translated=translated)
    report = document(program, native_search(query_len=300 if translated else 100, hits=[hit]))
    report["BlastOutput2"][0]["report"]["search_target"]["db"] = "target"
    query = b">q\n" + b"A" * (300 if translated else 100) + b"\n"
    job, bundle, catalog, _ = fixture(tmp_path, program, query=query, report=report)
    doc = source(tmp_path, catalog, "models", b'{"model":{},"binding":{}}')
    payload = empty_payload("profile")
    payload["documents"] = [doc]
    identity = dict(job["databases"][0]["identity"], source=dict(source_ref="models", pointer="/model"))
    profile = dict(profile_key="model", database_identity=identity, model_identifier=dict(namespace="CDD", value="cd00001", version="1"),
        pssm_key=None, num_columns=100, master_sequence_ref=None, specific_bits_threshold=40, reporting_bits_threshold=35,
        source=dict(source_ref="models", pointer="/model"), native_record=dict(synthetic=True))
    payload["searches"] = [dict(search_key=address(), profile_records=[profile],
        profile_bindings=[dict(search_key=address(), hit_ordinal=0, description_ordinal=0, profile_key="model",
            native_description={k: hit["description"][0].get(k) for k in ("id", "accession", "title", "taxid")},
            provenance=dict(source_ref="models", pointer="/binding"))], function_bindings=[], model_relations=[])]
    raw = metadata(tmp_path, catalog, "profile", payload)
    sheets = populate(prepared(job, bundle, catalog, [raw]), catalog)
    result = calculate_blast_profile_components(sheets["profile"][0]["sheet"])
    model = result["models"][0]
    assert model["paired_query_units"] == units and model["paired_model_positions"] == 50
    assert model["model_coverage"]["value"] == .5
    assert result["hsps"][0]["model_matches"][0]["specific_bits_margin"] == 2
    assert result["hsps"][0]["model_matches"][0]["reporting_bits_margin"] == 7
    assert sheets["profile"][0]["sheet"]["profile_records"][0]["profile_key"].startswith("profile-")
    (tmp_path / "profile-sheets.json").write_bytes(encoded(sheets))
    (tmp_path / "profile-calculations.json").write_bytes(encoded(result))
    (tmp_path / "profile-inputs.json").write_bytes(encoded(dict(job=job, bundle=bundle, artifact_catalog=catalog, metadata_payloads=[raw], subject_snapshots=[])))


def test_missing_document_omits_complete_search_unit_without_reindexing(tmp_path):
    job, bundle, catalog, _ = fixture(tmp_path)
    payload = sequence_payload(tmp_path, catalog)
    missing = dict(document_key="missing", artifact=dict(kind="received", source_ref=ref("source", "missing"),
        artifact_ref=ref("artifact", "missing"), sha256="a" * 64, size_bytes=10), format="json")
    payload["documents"].append(missing)
    unit = deepcopy(payload["searches"][0])
    unit["reference_metadata"][0]["source"] = "missing"
    payload["searches"].insert(0, unit)
    raw = metadata(tmp_path, catalog, "sequence_database", payload)
    prep = prepared(job, bundle, catalog, [raw])
    normalized = prep["metadata"][0]["normalized"]
    assert len(normalized["searches"]) == 1
    assert normalized["searches"][0]["description_bindings"][1]["binding"]["metadata_index"] == 1
    assert dict(normalized_pointer="/searches/0", payload_pointer="/searches/1") in prep["metadata"][0]["normalization_map"]


def test_database_metadata_uses_original_identity_slots_not_matching_hash(tmp_path):
    job, bundle, catalog, capture = fixture(tmp_path)
    first = dict(path="/original/first", sha256=digest(b"{}"), size_bytes=2, artifact_ref=None)
    second = dict(first, path="/original/second")
    job["databases"][0]["manifest"]["metadata_manifests"] = [first, second]
    key = m._metadata_capture_key("target", "metadata", second)
    capture(key, b"{}", "metadata", "opaque", database_key="target")
    bundle["database_manifest"][0]["metadata_manifest_artifacts"] = [dict(identity=first, artifact_key=None), dict(identity=second, artifact_key=key)]
    bundle["requested_job"] = contracts.requested_job_from_native_blast_database(job)
    payload = empty_payload("query_identity")
    payload["documents"] = [dict(document_key="first", artifact=dict(kind="database_metadata_manifest", database_key="target", manifest_index=0), format="json"),
        dict(document_key="second", artifact=dict(kind="database_metadata_manifest", database_key="target", manifest_index=1), format="json")]
    payload["sequence_records"] = [dict(input_key="query", record_ordinal=i, subject_ref=None, identity=None,
        source=dict(source_ref=k, pointer="")) for i, k in enumerate(("first", "second"))]
    raw = metadata(tmp_path, catalog, "query_identity", payload)
    prep = prepared(job, bundle, catalog, [raw])
    assert [r["record_ordinal"] for r in prep["metadata"][0]["normalized"]["sequence_records"]] == [1]
    assert m._metadata_capture_key("target", "metadata", first) != key
    swapped = deepcopy(bundle)
    swapped["database_manifest"][0]["metadata_manifest_artifacts"].reverse()
    bad = prepared(job, swapped, catalog, [raw])
    assert bad["metadata"][0]["normalized"]["sequence_records"] == []
    Path(catalog["entries"][-1]["path"]).write_bytes(b"[]")
    changed = prepared(job, bundle, catalog, [raw])
    assert changed["metadata"][0]["normalized"]["sequence_records"] == []
    assert any(i["detail_code"] == "artifact_digest_conflict" for i in changed["issues"])


def wire_fixture(value):
    """Make explicitly supplied fixture source links; never used by production."""
    if type(value) is list:
        return [wire_fixture(v) for v in value]
    if type(value) is dict:
        if set(value) == {"artifact_key", "member_ordinal", "report_index", "search_pointer"}:
            return dict(output_key="report", **{k: value[k] for k in value if k != "artifact_key"})
        if set(value) == {"source_ref", "pointer"}:
            return dict(source_ref="facts", pointer="")
        return {k: wire_fixture(v) for k, v in value.items()}
    return value


def vdb_fixture(tmp_path, *, program="blastn_vdb", hits=None, query=b">q\nACGTACGT\n"):
    from test_blast_vdb_inputs import hsp as vdb_hsp
    hits = hits or [dict(len=8, description=[dict(id="r1", accession="r1", title="synthetic read")], hsps=[vdb_hsp()]),
                    dict(len=8, description=[dict(id="r2", accession="r2", title="synthetic read")], hsps=[vdb_hsp()])]
    report = document(program.removesuffix("_vdb"), native_search(query_len=len(query.splitlines()[1]), hits=hits))
    report["BlastOutput2"][0]["report"]["search_target"]["db"] = "target"
    job, bundle, catalog, capture = fixture(tmp_path, program, query=query, report=report)
    prep = prepared(job, bundle, catalog)
    return job, bundle, catalog, capture, collect(prep, catalog)["searches"][0]


def test_vdb_demonstrated_duplicates_samples_and_actual_numerics(tmp_path):
    from test_blast_vdb_inputs import inputs as vdb_inputs
    job, bundle, catalog, _, search = vdb_fixture(tmp_path)
    values = wire_fixture(vdb_inputs(search))
    payload = empty_payload("vdb")
    payload["documents"] = [source(tmp_path, catalog, "facts", b'{"records":[{"sequence":"ACGTACGT"},{"sequence":"ACGTACGT"}]}')]
    unit = {k: values[k] for k in ("dataset_records", "member_bindings", "sequence_identity_bindings", "feature_bindings", "reference_metadata")}
    unit.update(search_key=address(), sequence_proofs=[], population_records=[], parsed_sources=[], metadata_bindings=[])
    for row in unit["dataset_records"]:
        row["selected_input"]["value"] = "target"
        row["snapshot"]["manifest_sha256"] = job["databases"][0]["manifest_file"]["sha256"]
    for i, row in enumerate(unit["sequence_identity_bindings"]):
        row["binding"].update(source_ref="facts", pointer=f"/records/{i}", linkage_source_ref="facts", linkage_pointer="")
        unit["sequence_proofs"].append(dict(binding_index=i, document_key="facts", representation="json_sequence", record_ordinal=None,
            sequence_pointer=f"/records/{i}/sequence", molecule="nt", sha256=digest(b"ACGTACGT"), length=8))
    payload["searches"] = [unit]
    raw = metadata(tmp_path, catalog, "vdb", payload)
    prep = prepared(job, bundle, catalog, [raw])
    assert prep["metadata"][0]["status"] == "valid", prep["issues"]
    sheets = populate(prep, catalog)
    result = calculate_blast_vdb_components(sheets["vdb"][0]["sheet"])
    assert result["membership"]["origin_bound_subject_count"]["value"] == 2
    assert result["sequence_groups"]["demonstrated_group_count"]["value"] == 1
    assert result["sequence_groups"]["duplicate_subject_representations"]["value"] == 1
    assert result["sample_groups"]["observed_origin_sample_count"]["value"] == 2
    assert result["subjects"][0]["full_query_coverage"]["value"] == 1
    (tmp_path / "vdb-sheets.json").write_bytes(encoded(sheets))
    (tmp_path / "vdb-calculations.json").write_bytes(encoded(result))
    (tmp_path / "vdb-inputs.json").write_bytes(encoded(dict(job=job, bundle=bundle, artifact_catalog=catalog, metadata_payloads=[raw], subject_snapshots=[])))


@pytest.mark.parametrize("parser", ["runinfo_csv", "blast_vdb_cmd_table", "ncbi_gbseq_xml"])
def test_all_three_native_vdb_parser_routes_and_binder(tmp_path, monkeypatch, parser):
    from test_blast_vdb_inputs import RUNINFO, GBSEQ, inputs as vdb_inputs, extraction_context
    job, bundle, catalog, _, search = vdb_fixture(tmp_path)
    payload = empty_payload("vdb")
    native = {"runinfo_csv": RUNINFO, "blast_vdb_cmd_table": b"gnl|SRA|SRR1.1.2\tSRR1.1.2\t8\tacgunrya\n", "ncbi_gbseq_xml": GBSEQ}[parser]
    payload["documents"] = [source(tmp_path, catalog, "facts", b'{}'), source(tmp_path, catalog, "native", native, parser)]
    dataset = wire_fixture(vdb_inputs(search)["dataset_records"][0])
    dataset.update(metadata_keys=[], selected_input=dict(kind="alias", value="target"))
    dataset["source"] = dict(source_ref="native", pointer="/records/0")
    dataset["snapshot"]["manifest_sha256"] = job["databases"][0]["manifest_file"]["sha256"]
    context = wire_fixture(extraction_context()) if parser == "blast_vdb_cmd_table" else None
    if context:
        context.update(selected_input=dataset["selected_input"], snapshot=dataset["snapshot"])
    payload["searches"] = [dict(search_key=address(), dataset_records=[dataset], member_bindings=[], sequence_identity_bindings=[],
        sequence_proofs=[], feature_bindings=[], reference_metadata=[], population_records=[],
        parsed_sources=[dict(document_key="native", parser=parser, source_version="fixture-v1", extraction_context=context)], metadata_bindings=[])]
    raw = metadata(tmp_path, catalog, "vdb", payload)
    forbid_scoring(monkeypatch)
    prep = prepared(job, bundle, catalog, [raw])
    assert any(i["detail_code"] == "parser_source_locator_pending" for i in prep["issues"])
    sheets = populate(prep, catalog)
    assert not any(i["detail_code"] == "parser_source_locator_pending" for i in sheets["issues"])
    assert len(sheets["metadata_parse_results"]) == 1, sheets["issues"]
    parsed = sheets["metadata_parse_results"][0]
    assert parsed["input_identity"] == dict(sha256=digest(native), size_bytes=len(native))
    assert parsed["native_text"] == native.decode()
    assert len(sheets["metadata_binding_results"]) == 1
    assert len(sheets["metadata_binding_results"][0]["unresolved_record_keys"]) == len(parsed["records"])


def pssm_locator_fixture(tmp_path, pointers):
    native = b'Pssm ::= { isProtein TRUE, numRows 2, numColumns 3, query seq { id { local str "q" }, inst { repr raw, mol aa, length 3, seq-data iupacaa "ACD" } }, finalData { scores { -2, 0, 5, 7, -32768, 9 } } }'
    job, bundle, catalog, _ = fixture(tmp_path, kind="pssm", query=native,
        report=document(search=native_search(query_len=3)))
    payload = empty_payload("iteration")
    payload["documents"] = [dict(document_key="pssm", artifact=dict(kind="input", input_key="query"), format="scoremat_asn_text")]
    payload["checkpoint_bindings"] = [dict(pssm_key=dict(document_key="pssm", record_ordinal=0), role="input",
        search_key=None, biological_round=None, provenance=dict(source_ref="pssm", pointer=p)) for p in pointers]
    row = metadata(tmp_path, catalog, "iteration", payload)
    return job, bundle, catalog, row, native


def test_pure_parser_locator_is_pending_until_real_saved_parse(tmp_path, monkeypatch):
    job, bundle, catalog, row, native = pssm_locator_fixture(tmp_path, ["/pssms/0/native_pssm/query"])
    entry = catalog["entries"][0]
    doc = dict(row["payload"]["documents"][0], **{k: entry[k] for k in ("artifact_key", "artifact_ref", "source_ref", "sha256", "size_bytes")}, contents=native)
    pure_catalog = dict(descriptor=row["descriptor"], documents=[doc], primary_reports=[],
        bundle_source_ref=catalog["bundle_source_ref"], bundle_artifact_ref=catalog["bundle_artifact_ref"])
    with monkeypatch.context() as pure:
        pure.setattr(Path, "read_bytes", lambda *_: pytest.fail("pure validator read bytes"))
        pure.setattr(m._pssm, "read_blast_pssm", lambda *a, **kw: pytest.fail("pure validator parsed ASN"))
        value = m.validate_native_blast_database_metadata_payload(row["payload"], descriptor=row["descriptor"],
            document_catalog=pure_catalog, job=job)
    assert value["status"] == "valid"
    assert [i["detail_code"] for i in value["issues"]] == ["parser_source_locator_pending"]
    calls, original = [], m._pssm.read_blast_pssm
    def spy(*args, **kwargs):
        calls.append(kwargs["artifact_key"])
        return original(*args, **kwargs)
    monkeypatch.setattr(m._pssm, "read_blast_pssm", spy)
    forbid_scoring(monkeypatch)
    prep = prepared(job, bundle, catalog, [row])
    assert calls == ["query"]
    assert prep["metadata"][0]["issues"] == []
    assert any(r["pointer"] == "/checkpoint_bindings/0/provenance" and r["status"] == "available"
               for r in prep["source_relations"])
    populate(prep, catalog)
    assert calls == ["query"]


@pytest.mark.parametrize("pointer,invalid", [
    ("/pssms/99", False), ("/pssms/0/native_pssm/missing", False),
    ("/pssms/0/native_pssm/query/seq/01", False), ("/pssms/00", True),
    ("/pssms/0/native_pssm/~2", True)])
def test_parser_locator_failure_keeps_original_and_independent_unit(tmp_path, pointer, invalid):
    job, bundle, catalog, row, _ = pssm_locator_fixture(tmp_path, [pointer, "/pssms/0"])
    prep = prepared(job, bundle, catalog, [row])
    validation = prep["metadata"][0]
    assert validation["payload"] == row["payload"]
    assert len(prep["pssm_sheets"]) == 1
    if invalid:
        assert validation["status"] == "invalid" and validation["normalized"] is None
    else:
        assert validation["status"] == "valid"
        assert len(validation["normalized"]["checkpoint_bindings"]) == 1
        assert dict(normalized_pointer="/checkpoint_bindings/0", payload_pointer="/checkpoint_bindings/1") in validation["normalization_map"]
        assert any(i["pointer"] == "/checkpoint_bindings/0/provenance" and i["detail_code"] == "parser_source_pointer_unresolved"
                   for i in validation["issues"])
    assert len(populate(prep, catalog)["collection"]["searches"]) == 1


@pytest.mark.parametrize("alter", ["schema", "digest", "native_text"])
def test_changed_saved_parser_identity_cannot_supply_metadata(tmp_path, monkeypatch, alter):
    job, bundle, catalog, row, _ = pssm_locator_fixture(tmp_path, ["/pssms/0"])
    original = m._pssm.read_blast_pssm
    def changed(*args, **kwargs):
        value = original(*args, **kwargs)
        if alter == "schema":
            value["schema"] = "wrong_schema"
        elif alter == "digest":
            value["input_identity"]["sha256"] = "0" * 64
        else:
            value["native_text"] += "\n"
        return value
    monkeypatch.setattr(m._pssm, "read_blast_pssm", changed)
    prep = prepared(job, bundle, catalog, [row])
    assert prep["metadata"][0]["normalized"]["checkpoint_bindings"] == []
    assert any(i["detail_code"] == "parser_source_identity_conflict" for i in prep["metadata"][0]["issues"])
    assert prep["metadata"][0]["payload"] == row["payload"]


def test_parser_interpretations_exact_duplicates_and_conflicts(tmp_path):
    job, bundle, catalog, row, _ = pssm_locator_fixture(tmp_path, ["/pssms/0"])
    prep = prepared(job, bundle, catalog, [row])
    document = prep["metadata"][0]["normalized"]["documents"][0]
    sheet = prep["pssm_sheets"][0]
    files = m._Catalog(catalog)
    assert m._check_parser_location(document, "/pssms/0", [sheet, deepcopy(sheet)], files) == ("available", None)
    changed = deepcopy(sheet)
    changed["pssms"][0]["native_pssm"]["numColumns"] = 4
    assert m._check_parser_location(document, "/pssms/0", [sheet, changed], files) == (
        "incompatible", "parser_source_interpretation_conflict")
    assert m._check_parser_location(document, "/pssms/0", [], files) == (
        "unavailable", "parser_source_parse_unavailable")


@pytest.mark.parametrize("pointer", ["", "/records/1", "/master_column_map"])
@pytest.mark.parametrize("selected", [None, 0])
def test_msa_source_cannot_establish_its_own_selection(tmp_path, monkeypatch, pointer, selected):
    job, bundle, catalog, _ = fixture(tmp_path, kind="msa", query=b"CLUSTAL W\n\nq  AC-D\nx  ACGD\n")
    job["query"]["msa_master_record_ordinal"] = selected
    bundle["requested_job"] = contracts.requested_job_from_native_blast_database(job)
    payload = empty_payload("query_identity")
    payload["documents"] = [dict(document_key="msa", artifact=dict(kind="input", input_key="query"), format="clustal")]
    payload["effective_msa_masters"] = [dict(input_key="query", record_ordinal=1, source=dict(source_ref="msa", pointer=pointer))]
    row = metadata(tmp_path, catalog, "query_identity", payload)
    calls, original = [], m._pssm.read_blast_msa_master
    def spy(*args, **kwargs):
        calls.append(kwargs["master_record_ordinal"])
        return original(*args, **kwargs)
    monkeypatch.setattr(m._pssm, "read_blast_msa_master", spy)
    prep = prepared(job, bundle, catalog, [row])
    assert calls == ([] if selected is None else [selected])
    assert prep["selected_master_record_ordinal"] == prep["effective_master_record_ordinal"] == selected
    assert prep["metadata"][0]["normalized"]["effective_msa_masters"] == []
    assert any(i["detail_code"] == "effective_master_source_circular" for i in prep["issues"])


@pytest.mark.parametrize("format", ["clustal", "text"])
@pytest.mark.parametrize("received", [True, False])
def test_circular_msa_source_uses_actual_artifact_identity(tmp_path, monkeypatch, format, received):
    job, bundle, catalog, _ = fixture(tmp_path, kind="msa", query=b"CLUSTAL W\n\nq  AC-D\nx  ACGD\n")
    artifact = dict(kind="input", input_key="query")
    if received:
        entry = catalog["entries"][0]
        catalog["retained_sources"].append({k: entry[k] for k in ("source_ref", "artifact_ref", "sha256", "size_bytes", "path")})
        artifact = dict(kind="received", **{k: entry[k] for k in ("source_ref", "artifact_ref", "sha256", "size_bytes")})
    payload = empty_payload("query_identity")
    payload["documents"] = [dict(document_key="same_input", artifact=artifact, format=format)]
    payload["effective_msa_masters"] = [dict(input_key="query", record_ordinal=1, source=dict(source_ref="same_input", pointer=""))]
    row = metadata(tmp_path, catalog, "query_identity", payload)
    monkeypatch.setattr(m._pssm, "read_blast_msa_master", lambda *a, **kw: pytest.fail("circular master selected"))
    prep = prepared(job, bundle, catalog, [row])
    assert prep["effective_master_record_ordinal"] is None and prep["invocation"]["operands"] == []
    assert any(i["detail_code"] == "effective_master_source_circular" for i in prep["issues"])


@pytest.mark.parametrize("pointer,linked", [("/records/1/ungapped_sequence", True), ("/master_column_map/1", True), ("/records/9", False)])
def test_msa_locators_qualified_after_independent_selection_before_operands(tmp_path, monkeypatch, pointer, linked):
    job, bundle, catalog, _ = fixture(tmp_path, kind="msa", query=b"CLUSTAL W\n\nq  AC-D\nx  ACGD\n")
    selected = source(tmp_path, catalog, "selected", b'{"effective_master":1}')
    subject = source(tmp_path, catalog, "subject", b"ACGD", "text")
    subject_ref = ref("input", "master")
    snapshot = dict(subject_ref=subject_ref, record_type="input", molecule="protein", length=4,
        sequence_sha256=digest(b"ACGD"), sequence_artifact_ref=subject["artifact"]["artifact_ref"], sequence_path=catalog["retained_sources"][-1]["path"])
    payload = empty_payload("query_identity")
    payload["documents"] = [selected, dict(document_key="msa", artifact=dict(kind="input", input_key="query"), format="clustal")]
    payload["effective_msa_masters"] = [dict(input_key="query", record_ordinal=1, source=dict(source_ref="selected", pointer="/effective_master"))]
    payload["master_subjects"] = [dict(kind="msa", input_key="query", record_ordinal=1, subject_ref=subject_ref,
        sequence_sha256=digest(b"ACGD"), source=dict(source_ref="msa", pointer=pointer))]
    row = metadata(tmp_path, catalog, "query_identity", payload)
    calls, original = [], m._pssm.read_blast_msa_master
    def spy(*args, **kwargs):
        calls.append(kwargs["master_record_ordinal"])
        return original(*args, **kwargs)
    monkeypatch.setattr(m._pssm, "read_blast_msa_master", spy)
    prep = prepared(job, bundle, catalog, [row], [snapshot])
    assert calls == [1] and prep["selected_master_record_ordinal"] is None
    assert prep["effective_master_record_ordinal"] == 1
    assert prep["invocation"]["operands"][0]["subject_ref"] == (subject_ref if linked else None)
    assert len(prep["metadata"][0]["normalized"]["master_subjects"]) == int(linked)


def test_parser_qualification_preserves_distinct_tuples_on_same_input(tmp_path):
    job, bundle, catalog, row, _ = pssm_locator_fixture(tmp_path, ["/pssms/0"])
    future = deepcopy(row)
    future["descriptor"]["schema_id"] += "_future"
    prep = prepared(job, bundle, catalog, [row, future])
    current, unsupported = prep["metadata"]
    assert current["status"] == "valid" and current["issues"] == []
    assert unsupported["status"] == "unsupported" and unsupported["normalized"] is None
    assert unsupported["payload"] == current["payload"]
    assert all(r["schema_id"] == row["descriptor"]["schema_id"] for r in prep["source_relations"] if r["status"] == "available"
               and r["input_key"] == row["descriptor"]["input_key"])


def test_vdb_bad_parser_location_excludes_whole_unit_and_preserves_next(tmp_path):
    from test_blast_vdb_inputs import RUNINFO, inputs as vdb_inputs
    job, bundle, catalog, _, search = vdb_fixture(tmp_path)
    payload = empty_payload("vdb")
    payload["documents"] = [source(tmp_path, catalog, "facts", b'{}'), source(tmp_path, catalog, "native", RUNINFO, "runinfo_csv")]
    dataset = wire_fixture(vdb_inputs(search)["dataset_records"][0])
    dataset.update(metadata_keys=[], selected_input=dict(kind="alias", value="target"))
    dataset["snapshot"]["manifest_sha256"] = job["databases"][0]["manifest_file"]["sha256"]
    dataset["source"] = dict(source_ref="native", pointer="/records/999")
    bad = dict(search_key=address(), dataset_records=[dataset], member_bindings=[], sequence_identity_bindings=[],
        sequence_proofs=[], feature_bindings=[], reference_metadata=[], population_records=[],
        parsed_sources=[dict(document_key="native", parser="runinfo_csv", source_version="fixture", extraction_context=None)], metadata_bindings=[])
    good = deepcopy(bad)
    good["dataset_records"][0]["source"]["pointer"] = "/records/0"
    payload["searches"] = [bad, good]
    row = metadata(tmp_path, catalog, "vdb", payload)
    sheets = populate(prepared(job, bundle, catalog, [row]), catalog)
    validation = sheets["prepared_inputs"]["metadata"][0]
    assert validation["payload"] == payload
    assert len(validation["normalized"]["searches"]) == 1
    assert dict(normalized_pointer="/searches/0", payload_pointer="/searches/1") in validation["normalization_map"]
    assert len(sheets["metadata_parse_results"]) == 2 and len(sheets["metadata_binding_results"]) == 1
    assert len(sheets["vdb"][0]["sheet"]["dataset_records"]) == 1
    assert any(i["pointer"] == "/searches/0/dataset_records/0/source" and i["detail_code"] == "parser_source_pointer_unresolved"
               for i in sheets["issues"])


def test_gbseq_actual_binding_feature_and_forward_codon_map(tmp_path):
    from test_blast_vdb_inputs import GBSEQ, inputs as vdb_inputs, hsp as vdb_hsp, binding, entity
    native_hit = dict(len=18, description=[dict(id="NC_X.1", accession="NC_X.1")],
        hsps=[vdb_hsp("MAK", hit_from=4, hit_to=12, hit_frame=1)])
    job, bundle, catalog, _, search = vdb_fixture(tmp_path, program="tblastn_vdb", hits=[native_hit], query=b">q\nMAK\n")
    values = vdb_inputs(search, symbols=["CCCATGGCTAAACCCCCC"], kind="reference", samples=False)
    native_doc = source(tmp_path, catalog, "native", GBSEQ, "ncbi_gbseq_xml")
    parsed = m._vdb.parse_ncbi_gbseq_vdb_metadata(GBSEQ, source_ref=native_doc["artifact"]["source_ref"], source_version="fixture")
    identifier = parsed["records"][0]["source_entity"]["member_identifier"]
    feature_identifier = parsed["records"][2]["source_entity"]["feature_identifier"]
    member = values["member_bindings"][0]
    member["member_identifier"] = identifier
    member["reference_identity"]["identifier"] = identifier
    dataset = values["dataset_records"][0]
    dataset.update(selected_input=dict(kind="alias", value="target"), metadata_keys=["member", "cds"])
    dataset["snapshot"]["manifest_sha256"] = job["databases"][0]["manifest_file"]["sha256"]
    parent = binding(parsed["records"][0], "member", entity("member", dataset="D0", member=identifier), member=0)
    child = binding(parsed["records"][2], "cds", entity("feature", dataset="D0", member=identifier, feature=feature_identifier), parent="member")
    parent["record_key"]["source_ref"] = child["record_key"]["source_ref"] = "native"
    unit = wire_fixture(dict(search_key=search["search_key"], dataset_records=[dataset], member_bindings=[member],
        sequence_identity_bindings=[], sequence_proofs=[], reference_metadata=[], population_records=[],
        feature_bindings=[dict(search_key=search["search_key"], hit_ordinal=0, member_binding_index=0, member_identifier=identifier,
            feature_identifier=feature_identifier, feature_kind="CDS", member_interval=[3,12], segments=[[3,12]], location_status="exact",
            strand=1, genetic_code=1, codon_start=1, function=None, feature_sequence_sha256=None, translation_metadata_key="cds",
            provenance=dict(source_ref="facts", pointer=""))],
        parsed_sources=[dict(document_key="native", parser="ncbi_gbseq_xml", source_version="fixture", extraction_context=None)],
        metadata_bindings=[child, parent]))
    payload = empty_payload("vdb")
    payload["documents"] = [source(tmp_path, catalog, "facts", b'{}'), native_doc]
    payload["searches"] = [unit]
    raw = metadata(tmp_path, catalog, "vdb", payload)
    sheets = populate(prepared(job, bundle, catalog, [raw]), catalog)
    assert [r["status"] for r in sheets["metadata_binding_results"][0]["binding_results"]] == ["available", "available"]
    result = calculate_blast_vdb_components(sheets["vdb"][0]["sheet"])
    feature = result["feature_components"][0]
    assert [c["member_positions"] for c in feature["translation_map"]["codons"]] == [[3,4,5],[6,7,8],[9,10,11]]
    assert [c["oriented_triplet"] for c in feature["translation_map"]["codons"]] == ["ATG", "GCT", "AAA"]
    assert feature["hsp_rows"][0]["identical_query_feature_residues"]["value"] == 3
    assert feature["feature_paired_residue_coverage"]["value"] == 1
    (tmp_path / "gbseq-sheets.json").write_bytes(encoded(sheets))
    (tmp_path / "gbseq-calculations.json").write_bytes(encoded(result))
    (tmp_path / "gbseq-inputs.json").write_bytes(encoded(dict(job=job, bundle=bundle, artifact_catalog=catalog, metadata_payloads=[raw], subject_snapshots=[])))


def test_metadata_tuple_identity_keeps_supported_and_future_schema_same_original_input(tmp_path):
    job, bundle, catalog, capture = fixture(tmp_path)
    payload = empty_payload("query_identity")
    raw = encoded(payload)
    entry = capture("metadata", raw, "metadata", "json", input_key="metadata")
    job["inputs"].append(dict(input_key="metadata", role="metadata", format="json", path="/selected/metadata",
        sha256=entry["sha256"], size_bytes=entry["size_bytes"], artifact_ref=None))
    bundle["input_manifest"].append(dict(input_key="metadata", artifact_key="metadata", original_path="/selected/metadata",
        realized_path=entry["path"], expected_sha256=entry["sha256"], observed_sha256=entry["sha256"], size_bytes=entry["size_bytes"]))
    supported = dict(input_key="metadata", consumer="query_identity", schema_id=payload["schema"],
        artifact_ref=entry["artifact_ref"], sha256=entry["sha256"], size_bytes=entry["size_bytes"], origin="original_job_input")
    future = dict(supported, schema_id="native_blast_database_query_metadata_future")
    job["metadata_inputs"] = [{k: d[k] for k in ("input_key", "consumer", "schema_id")} for d in (supported, future)]
    bundle["requested_job"] = contracts.requested_job_from_native_blast_database(job)
    rows = [dict(descriptor=d, payload=deepcopy(payload)) for d in (supported, future)]
    prep = prepared(job, bundle, catalog, rows)
    assert [r["status"] for r in prep["metadata"]] == ["valid", "unsupported"]
    assert [r["schema_id"] for r in prep["metadata"]] == [supported["schema_id"], future["schema_id"]]
    assert populate(prep, catalog)["sequence"]
    duplicated = prepared(job, bundle, catalog, [rows[0], rows[0]])
    assert [r["status"] for r in duplicated["metadata"]] == ["invalid", "invalid"]
    conflicting = deepcopy(rows)
    conflicting[1]["descriptor"]["sha256"] = "f" * 64
    rejected = prepared(job, bundle, catalog, conflicting)
    assert [r["status"] for r in rejected["metadata"]] == ["invalid", "invalid"]
    assert all(r["issues"][0]["detail_code"] == "metadata_input_identity_conflict" for r in rejected["metadata"])


def test_target_contexts_follow_exact_search_and_never_a_global_fallback(tmp_path):
    first = document(search=native_search(query_len=12, hits=native_search()["hits"][:1]))
    first["BlastOutput2"][0]["report"]["search_target"]["db"] = "target"
    report = dict(BlastOutput2=[first["BlastOutput2"][0], deepcopy(first["BlastOutput2"][0])])
    job, bundle, catalog, _ = fixture(tmp_path, report=report)
    payload = sequence_payload(tmp_path, catalog)
    for key in ("reference_metadata", "description_bindings", "sequence_identity_bindings", "sequence_proofs"):
        payload["searches"][0][key] = payload["searches"][0][key][:1]
    second = deepcopy(payload["searches"][0])
    second_address = dict(address(), report_index=1, search_pointer="/BlastOutput2/1/report/results/search")
    second["search_key"] = second_address
    for key in ("description_bindings", "sequence_identity_bindings"):
        second[key][0]["search_key"] = deepcopy(second_address)
        second[key][0]["binding"]["report_index"] = 1
    payload["searches"].append(second)
    seq = metadata(tmp_path, catalog, "sequence_database", payload, "sequence_metadata")
    query_payload = empty_payload("query_identity")
    query_payload["documents"] = payload["documents"]
    query_payload["target_contexts"] = [dict(search_key=key, taxid=taxid, lineage=[dict(taxid=taxid, rank="genus", name=None)],
        independent_of_search=True, source=dict(source_ref="facts", pointer="")) for key, taxid in ((address(), 1), (second_address, 2))]
    query = metadata(tmp_path, catalog, "query_identity", query_payload, "query_metadata")
    sheets = populate(prepared(job, bundle, catalog, [seq, query]), catalog)
    iteration = sheets["iteration"]
    assert iteration["target_context"] is None
    assert [r["target_context"]["taxid"] for r in iteration["target_contexts"]] == [1, 2]
    assert all(r["target_context"]["query_operand"] == iteration["query_bindings"][i]["query_binding"]["operand"] for i, r in enumerate(iteration["target_contexts"]))
    calculated = calculate_blast_iteration_components(iteration)
    assert [next(rank["target_matching_fraction"] for rank in r["sequence_components"]["components"]["database_sheet"]["taxonomy"]["ranks"]
                 if rank["rank"] == "genus") for r in calculated["searches"]] == [1, 0]


def test_supplied_conflicting_stage_keeps_both_relations_and_native_counts(tmp_path):
    job, bundle, catalog, _ = fixture(tmp_path)
    payload = empty_payload("query_identity")
    payload["documents"] = [source(tmp_path, catalog, "facts", b'{}')]
    payload["search_bindings"] = [dict(search_key=address(), stage="domain_database", biological_round=7,
        database_key="target", input_pssm_key=None, provenance=dict(source_ref="facts", pointer=""))]
    row = metadata(tmp_path, catalog, "query_identity", payload)
    sheets = populate(prepared(job, bundle, catalog, [row]), catalog)
    assert [r["stage"] for r in sheets["iteration"]["search_bindings"]] == ["domain_database", "sequence_database"]
    assert [r["biological_round"] for r in sheets["iteration"]["search_bindings"]] == [7, None]
    assert any(i["detail_code"] == "supplied_derived_stage_conflict" for i in sheets["issues"])
    calculated = calculate_blast_iteration_components(sheets["iteration"])
    assert calculated["searches"][0]["counts"]["reported_hit_count"]["value"] == 2
    assert calculated["searches"][0]["biological_round"]["value"] is None


def test_repeated_supplied_convergence_keys_remain_two_qualified_observations(tmp_path):
    job, bundle, catalog, _ = fixture(tmp_path)
    payload = empty_payload("iteration")
    payload["documents"] = [source(tmp_path, catalog, "facts", b'{"first":true,"second":false}')]
    payload["convergence_records"] = [dict(record_key="duplicate", search_key=address(), query_operand=None, native_converged=value,
        evidence=dict(origin="supplied_source_record", source=dict(source_ref="facts", pointer="/" + key),
        source_format="json", original_record={key:value}, extractor=None)) for key, value in (("first", True), ("second", False))]
    row = metadata(tmp_path, catalog, "iteration", payload)
    sheets = populate(prepared(job, bundle, catalog, [row]), catalog)
    assert len(sheets["iteration"]["convergence_records"]) == 2
    out = calculate_blast_iteration_components(sheets["iteration"])
    assert [r["native_converged"]["value"] for r in out["convergence_observations"]] == [None, None]
    assert all(r["status"] == "incompatible" for r in out["convergence_observations"])


def test_rps_path_alias_cannot_rewrite_database_identity(tmp_path):
    report = document("rpsblast", native_search(query_len=12))
    report["BlastOutput2"][0]["report"]["search_target"]["db"] = "/selected/db/target"
    job, bundle, catalog, _ = fixture(tmp_path, "rpsblast", report=report)
    sheets = populate(prepared(job, bundle, catalog), catalog)
    assert sheets["derived_search_bindings"][0]["binding"]["database_identity"]["value"] == "target"
    calc = calculate_blast_profile_components(sheets["profile"][0]["sheet"])
    assert calc["status"] == "incompatible"
    assert sheets["profile"][0]["sheet"]["search"]["normalized"]["search"]["database"] == "/selected/db/target"


def test_literal_payload_native_record_is_not_recursively_rewritten(tmp_path):
    job, bundle, catalog, _ = fixture(tmp_path)
    payload = sequence_payload(tmp_path, catalog)
    opaque = dict(source_ref="facts", search_key=address(), pssm_key=dict(document_key="facts", record_ordinal=0), database_key="target")
    payload["searches"][0]["reference_metadata"][0]["native_record"] = opaque
    raw = metadata(tmp_path, catalog, "sequence_database", payload)
    normalized = prepared(job, bundle, catalog, [raw])["metadata"][0]["normalized"]
    assert normalized["searches"][0]["reference_metadata"][0]["native_record"] == opaque
    assert normalized["searches"][0]["reference_metadata"][0]["source"] != "facts"


def test_actual_tabular_header_derives_only_its_reported_stage(tmp_path):
    job, bundle, catalog, _ = fixture(tmp_path)
    fields = ["qseqid", "sseqid", "qlen", "slen", "qstart", "qend", "sstart", "send", "qseq", "sseq", "bitscore", "evalue", "length", "nident", "gaps"]
    raw = b"# PSIBLAST 2.17.0+\n# Query: q\n# Database: target\n# 1 hits found\nq\tA\t12\t10\t3\t6\t2\t5\tACDE\tACDE\t20\t0\t4\t4\t0\n"
    selected = next(r for r in job["outputs"] if r["role"] == "primary_report")
    selected.update(format="tabular7", fields=fields, delimiter="\t")
    entry = next(r for r in catalog["entries"] if r["role"] == "primary_report")
    Path(entry["path"]).write_bytes(raw)
    entry.update(format="tabular7", fields=fields, delimiter="\t", sha256=digest(raw), size_bytes=len(raw))
    capture = next(r for r in bundle["artifacts"] if r["role"] == "primary_report")
    capture.update({k: entry[k] for k in ("format", "fields", "delimiter", "sha256", "size_bytes")})
    bundle["requested_job"] = contracts.requested_job_from_native_blast_database(job)
    prep = prepared(job, bundle, catalog)
    collection = parse_blast_report_collection({"report": raw}, artifacts=[dict(artifact_key="report", role="primary_report", format="tabular7", fields=fields, delimiter="\t")], invocation=prep["invocation"])
    sheets = m.populate_native_blast_database_sheets(collection, prepared_inputs=prep, artifact_catalog=catalog)
    assert sheets["derived_search_bindings"][0]["binding"]["stage"] == "sequence_database"
    assert sheets["derived_search_bindings"][0]["input_pointers"][-1]["pointer"] == "/sections/0"
    assert sheets["sequence"][0]["sheet"]["search"]["normalized"]["hits"][0]["hsps"][0]["bit_score"] == 20


def test_prepared_output_is_identical_across_python_hash_seeds(tmp_path):
    job, bundle, catalog, _ = fixture(tmp_path)
    payload = empty_payload("query_identity")
    payload["documents"] = [source(tmp_path, catalog, "facts", b'{}')]
    provenance = dict(source_ref="facts", pointer="")
    payload["sequence_records"] = [dict(input_key="query", record_ordinal=0, subject_ref=None, identity=None, source=provenance)]
    payload["effective_msa_masters"] = [dict(input_key="query", record_ordinal=0, source=provenance)]
    payload["search_bindings"] = [dict(search_key=address(), stage="sequence_database", biological_round=None,
        database_key="target", input_pssm_key=None, provenance=provenance)]
    payload["target_contexts"] = [dict(search_key=address(), taxid=1, lineage=[], independent_of_search=True, source=provenance)]
    row = metadata(tmp_path, catalog, "query_identity", payload)
    request = tmp_path / "preparation.json"
    request.write_bytes(encoded(dict(job=job, bundle=bundle, artifact_catalog=catalog, metadata_payloads=[row], subject_snapshots=[])))
    code = "import json,sys; from gene_annotation_episode.native_blast_database_metadata import prepare_native_blast_database_inputs as prepare; print(json.dumps(prepare(**json.load(open(sys.argv[1]))),sort_keys=True,separators=(',',':')))"
    outputs = [subprocess.run([sys.executable, "-B", "-c", code, str(request)], check=True,
        capture_output=True, env={**os.environ, "PYTHONHASHSEED": seed}).stdout for seed in ("1", "2", "91")]
    assert outputs[0] == outputs[1] == outputs[2]
