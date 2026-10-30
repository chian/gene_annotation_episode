"""Explicitly synthetic U06 fixtures; no database search or remote service.

The established controlled producer and episode hosts execute the real selected
action, capture, bounded result worker and original typed-return validators.
"""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import test_native_blast_standard_database_metadata as sf
import test_native_blast_database_population_metadata as population
import test_native_blast_standard_database_episode_binding as sh
import test_native_blast_database_episode_binding as nh
from test_blast_fasta_record_identity_integration import store_payload, quality

VERSION = population.VERSION
STANDARD = {"blastn", "blastp", "blastx", "tblastn", "tblastx"}


def values(row):
    return {r["name"]: r["value"] for r in row["measurements"]}


def save(path, value):
    Path(path).write_bytes(sf.encoded(value))


def source_payload(h, raw, key):
    artifact = h.store.artifact(raw, "application/json")
    source = h.store.put("source", dict(provider="caller", accession=key,
        uri=None, artifact_ref=artifact, text_ref=None, request_ref=None,
        version="synthetic_v1", retrieved_at=None), origin="caller")["id"]
    record = h.store.get(artifact)
    return dict(source_ref=source, artifact_ref=artifact, sha256=record["sha256"], size_bytes=record["size"])


def synthetic_report(program, operand, *, kind="sequence", empty=False, layout="single", fmt="json15"):
    qnt = program in {"blastn", "blastx", "tblastx"}
    rnt = program in {"blastn", "tblastn", "tblastx"}
    sequence = "AC" if kind == "pssm" else "GCTTGTGATGAA" if program in {"blastx", "tblastx"} else "ACGTACGT" if qnt else "ACDEFGHI"
    native = "psitblastn" if program == "tblastn" and kind == "pssm" else program
    refs = ("GCTTGTGATGAAGGTAAA", "GCTTGTGATGAACCTAAA") if rnt else ("ACDEFGHIKL", "ACDEPQRSTV")
    doc = sf.report(native, query_id="q", query_title="q", query_len=len(sequence), database=operand)
    hits = doc["BlastOutput2"][0]["report"]["results"]["search"]["hits"]
    for i, hit in enumerate(hits):
        hit["len"] = len(refs[i])
        n = 2 if kind == "pssm" else 4
        text = "AC" if kind == "pssm" else "ACGT" if program == "blastn" else "ACDE"
        hit["hsps"][0].update(query_to=n*3 if program in {"blastx", "tblastx"} else n,
            hit_to=n*3 if program in {"tblastn", "tblastx"} else n,
            align_len=n, identity=n, qseq=text, hseq=text)
        if program in {"blastx", "tblastx"}: hit["hsps"][0]["query_frame"] = 1
        if program in {"tblastn", "tblastx"}: hit["hsps"][0]["hit_frame"] = 1
    if empty: hits.clear()
    metadata_doc = deepcopy(doc)
    searches = [sf.address()]
    if layout == "queries":
        doc["BlastOutput2"].append(deepcopy(doc["BlastOutput2"][0]))
        doc["BlastOutput2"][1]["report"]["results"]["search"].update(query_id="q2", query_title="q2")
        searches.append(sf.address(1))
    elif layout == "rounds":
        report = doc["BlastOutput2"][0]["report"]
        search = report["results"]["search"]
        report["results"] = dict(iterations=[dict(iter_num=i+1, search=deepcopy(search)) for i in range(2)])
        searches = [dict(sf.address(), search_pointer=f"/BlastOutput2/0/report/results/iterations/{i}/search") for i in range(2)]
    fields = None
    if fmt == "json15": raw = sf.encoded(doc)
    else:
        assert layout == "single"
        fields = ["qseqid", "sseqid", "sacc", "stitle", "staxids", "qlen", "slen", "qstart", "qend", "sstart", "send", "length", "nident", "bitscore", "evalue", "qseq", "sseq"]
        raw_text = (f"# {native.upper()} 2.17.0+\n# Query: q\n# Database: {operand}\n" if fmt == "tabular7" else "")
        for hit in hits:
            d, hs = hit["description"][0], hit["hsps"][0]
            raw_text += "\t".join(map(str, ["q", d["id"], d["accession"], d["title"], d["taxid"], len(sequence), hit["len"], 1, hs["query_to"], 1, hs["hit_to"], hs["align_len"], hs["identity"], hs["bit_score"], 0, hs["qseq"], hs["hseq"]])) + "\n"
        if fmt == "tabular7": raw_text += f"# {len(hits)} hits found\n"
        raw = raw_text.encode()
        searches = [dict(sf.address(), search_pointer="/sections/0")]
    return dict(raw=raw, document=metadata_doc, sequence=sequence, references=refs,
        molecule="nt" if rnt else "aa", searches=searches, fields=fields)


def host(tmp_path, monkeypatch, program="blastp", *, kind="sequence", fmt="json15",
         layout="single", empty=False, nonzero=False, supplied_quality=False):
    module = sh if program in STANDARD else nh
    original = module.producer_fixture
    def selected_fixture(*args, **kwargs):
        result = original(*args, **kwargs)
        job = result[1]["requested_job"]["native_blast_standard_database" if module is sh else "native_blast_database"]
        db = next(d for d in job["databases"] if d["database_key"] == "target")
        db["identity"].update(value="curated-proteins", version="1", release="release1", scope="searched_database")
        db["manifest"]["identity"] = deepcopy(db["identity"])
        db["manifest_file"].update(module.write(Path(db["manifest_file"]["path"]), sf.encoded(db["manifest"])))
        return result
    monkeypatch.setattr(module, "producer_fixture", selected_fixture)
    operand = str(tmp_path / "project" / "synthetic-inputs" / ("selected-db" if module is sh else "db-target"))
    native = synthetic_report(program, operand, kind=kind, empty=empty, layout=layout, fmt=fmt)
    query = None if kind != "sequence" else (">q\n" + native["sequence"] + "\n" + (">q2\n" + native["sequence"] + "\n" if layout == "queries" else "")).encode()
    if kind == "msa":
        query = b"CLUSTAL W\n\nq ACDEFGHI\nm ACDEYGHI\n"
    h = module.SyntheticHost(tmp_path, monkeypatch, program, query_kind=kind,
        query_bytes=query, sequence=native["sequence"], native_report=native["raw"],
        report_format=fmt, report_fields=native["fields"], nonzero=nonzero)
    h.population_native = native
    h.population_kind = kind
    inputs = sf.fixture()
    inputs["job"] = deepcopy(h.job)
    payload = population.v3_payload(inputs, fasta=supplied_quality, doc=native["document"],
        sequences=native["references"], molecule=native["molecule"], **({} if not empty else dict(indices=())))
    if supplied_quality:
        quality(payload, inputs=inputs, same=False)
    unit = payload["searches"][0]
    payload["searches"] = []
    for key in native["searches"]:
        row = deepcopy(unit); row["search_key"] = deepcopy(key)
        for field in ("description_bindings", "sequence_identity_bindings"):
            for binding in row[field]:
                binding["search_key"] = deepcopy(key)
                binding["binding"]["report_index"] = key["report_index"]
        payload["searches"].append(row)
    sf.add_metadata(inputs, payload, "sequence_database", "population-metadata")
    h.population_inputs = inputs
    h.population_payload = store_payload(h.store, inputs)
    return h


def selection(h, *, receive=True, failure=None):
    payload = deepcopy(h.population_payload)
    if failure == "missing_pointer": payload["searches"][0]["database_population_associations"][0]["assertion_source"]["pointer"] = "/absent"
    if failure == "aliased_report":
        document = next(d for d in payload["documents"] if d["document_key"] == "population-assertion")
        document["artifact"] = dict(kind="received", **source_payload(h, h.population_native["raw"], "aliased-original-report"))
        payload["searches"][0]["database_population_associations"][0]["assertion_source"]["pointer"] = "/BlastOutput2"
    if failure in {"conflicting", "malformed", "unknown"}:
        document = next(d for d in payload["documents"] if d["document_key"] == "population-assertion")
        value = json.loads(h.store.get_artifact(document["artifact"]["artifact_ref"]))
        if failure == "conflicting": value["assertion"]["native_database_operand"] += "-different"
        elif failure == "malformed": value["assertion"] = {"synthetic_malformed_assertion": True}
        else: value["assertion"]["population_identity"]["release"] = None
        document["artifact"] = dict(kind="received", **source_payload(h, sf.encoded(value), failure))
    if failure == "unresolved_sibling":
        sibling = deepcopy(payload["searches"][0]["database_population_associations"][0])
        sibling["association_key"] = "synthetic-unresolved-sibling"
        sibling["assertion_source"]["pointer"] = "/absent"
        payload["searches"][0]["database_population_associations"].append(sibling)
    if failure == "absent":
        for search in payload["searches"]: search["database_population_associations"] = []
    if failure == "old_v2":
        payload["schema"] = "native_blast_database_sequence_metadata_v2"
        for search in payload["searches"]: del search["database_population_associations"]
    sources = [{k: v for k, v in d["artifact"].items() if k != "kind"} for d in payload["documents"]]
    artifact = h.store.artifact(sf.encoded(payload), "application/json"); record = h.store.get(artifact)
    descriptors = [dict(input_key="population", consumer="sequence_database", schema_id=payload["schema"],
        artifact_ref=artifact, sha256=record["sha256"], size_bytes=record["size"])]
    proof = source_payload(h, sf.encoded(dict(synthetic_stage_assertions=h.population_native["searches"])), "stage")
    query = sf.query_payload()
    query["documents"] = [dict(document_key="stage", artifact=dict(kind="received", **proof), format="json")]
    source = dict(source_ref="stage", pointer="/synthetic_stage_assertions")
    if h.population_kind == "sequence":
        query["sequence_records"] = [dict(input_key="query", record_ordinal=i,
            subject_ref=h.scope["subject_refs"][0], source=source, identity=None)
            for i in range(2 if len(h.population_native["searches"]) == 2 and h.population_native["searches"][1]["report_index"] == 1 else 1)]
    else:
        query["master_subjects"] = [dict(input_key="query", record_ordinal=0,
            subject_ref=h.scope["subject_refs"][0], source=source, kind=h.population_kind,
            sequence_sha256=sf.sha(h.population_native["sequence"].encode()))]
    if h.job["program"] == "deltablast":
        query["search_bindings"] = [dict(search_key=deepcopy(key), stage="sequence_database", biological_round=None,
            database_key="target", input_pssm_key=None, provenance=dict(source_ref="stage", pointer="/synthetic_stage_assertions"))
            for key in h.population_native["searches"]]
    qartifact = h.store.artifact(sf.encoded(query), "application/json"); qrecord = h.store.get(qartifact)
    descriptors.append(dict(input_key="stage", consumer="query_identity", schema_id=query["schema"],
        artifact_ref=qartifact, sha256=qrecord["sha256"], size_bytes=qrecord["size"]))
    sources.append(proof)
    if receive:
        h.receipts.receive(h.root.episode_id, [artifact, qartifact] + [s[k] for s in sources for k in ("source_ref", "artifact_ref")], kind="initial")
    return dict(version="native_blast_standard_database_selector_v1" if h.job["program"] in STANDARD else "native_blast_database_result_selector_v1",
        acquisition="complete_bound_bundle", metadata_inputs=descriptors, retained_sources=sources,
        projections=[dict(family=f, rows=dict(offset=0, limit=50), metrics=metrics, booleans=[])
            for f, metrics in [("search", ["reported_hit_count"]), ("hsp", ["native_score_bits"]),
                ("sequence_function", ["function_mass", "unadjusted_probability", "representation_adjusted_probability"]),
                ("sequence_population", ["database_sequence_count", "database_total_sequence_count", "database_fraction"])]]), payload


def frozen(h, child, body):
    standard = h.job["program"] in STANDARD
    name = "native_blast_standard_database" if standard else "native_blast_database"
    module = __import__("gene_annotation_episode." + name + "_result_publication", fromlist=["x"])
    return module, module._validate_preparation(h.store, child, body["preparation"])


def saved_reuse(tmp_path, request, *, standard, expect_failed=False):
    """Existing worker reuse in its original fresh module closure; no BLAST."""
    request_path, script = tmp_path / "saved-request.json", tmp_path / "saved-reuse.py"
    tmp_path.mkdir(parents=True, exist_ok=True)
    save(request_path, request)
    script.write_text('''import sys, json, importlib
from gene_annotation_episode import blast_fasta_record_identity as fasta
from gene_annotation_episode import native_blast_standard_database_metadata as sm
from gene_annotation_episode import native_blast_database_metadata as nm
from gene_annotation_episode import native_blast_database_population_metadata as population
from gene_annotation_episode import native_blast_standard_database_result_worker as sw
from gene_annotation_episode import native_blast_database_result_worker as nw
from gene_annotation_episode import blast_report_collection as collection
import socket, subprocess
request = json.load(open(sys.argv[1]))
for row in request['implementation']['files']:
    importlib.import_module(row['module'])
def forbidden(*args, **kwargs):
    raise AssertionError('saved reuse attempted parsing, metadata population, network or native execution')
for module, names in [(fasta, ('parse_blast_fasta_source_records', 'parse_sequences')),
        (sm, ('parse_sequences', 'prepare_standard_blast_database_inputs', 'populate_standard_blast_database_sheets')),
        (nm, ('parse_blast_fasta_source_records', 'parse_sequences', 'prepare_native_blast_database_inputs', 'populate_native_blast_database_sheets')),
        (population, ('extract_native_blast_database_population_associations', '_retain_document_records', '_retain_preparation_records')),
        (sw, ('parse_blast_report_collection',)), (nw, ('parse_blast_report_collection',)),
        (collection, ('parse_blast_report_collection',)),
        (socket, ('socket', 'getaddrinfo')), (subprocess, ('run', 'Popen'))]:
    for name in names: setattr(module, name, forbidden)
function = sw.run_standard_blast_database_result_worker if sys.argv[2] == 'standard' else nw.run_native_blast_database_result_worker
result = function(sys.argv[1])
assert (result['status'] == 'failed') == (sys.argv[3] == 'failed'), result['failures']
''')
    completed = subprocess.run([sys.executable, "-B", str(script), str(request_path), "standard" if standard else "native", "failed" if expect_failed else "success"],
        cwd=tmp_path, capture_output=True, check=False)
    (tmp_path / "saved-reuse.stdout").write_bytes(completed.stdout)
    (tmp_path / "saved-reuse.stderr").write_bytes(completed.stderr)
    assert completed.returncode == 0, completed.stderr.decode()
    return json.loads((Path(request["output_directory"]) / "worker-manifest.json").read_bytes())
