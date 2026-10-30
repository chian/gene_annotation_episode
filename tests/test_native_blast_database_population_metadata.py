"""U06 supplied-source metadata: synthetic fixtures, no BLAST execution."""
from copy import deepcopy
import builtins
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode import native_blast_database_population_metadata as population
from gene_annotation_episode import native_blast_standard_database_metadata as standard
from gene_annotation_episode import native_blast_standard_database_contracts as contracts
from gene_annotation_episode.blast_sequence_database import calculate_blast_sequence_database_components
from gene_annotation_episode.blast_database_grader import calculate_database_probabilities
import test_native_blast_standard_database_metadata as base


VERSION = "native_blast_database_sequence_metadata_v3"


def original_bundle_size(inputs):
    # These bytes are the ORIGINAL synthetic fixture artifact, not a claimed
    # reconstruction of an external capture's byte length.
    raw = base.encoded(inputs["bundle"])
    inputs["artifact_catalog"].update(bundle_sha256=base.sha(raw), bundle_size_bytes=len(raw))
    return raw


def v3_payload(inputs, *, fasta=False, **kwargs):
    payload = (base.record_metadata(inputs, **kwargs) if fasta else base.numerical_metadata(inputs, census=False, **kwargs))
    payload["schema"] = VERSION
    for unit in payload["searches"]:
        for row in unit["reference_metadata"]:
            row.setdefault("record_locator", None)
        for row in unit["description_bindings"]:
            row["binding"].setdefault("metadata_record_locator", None)
        for row in unit["sequence_identity_bindings"]:
            row["binding"].setdefault("record_locator", None)
        db = inputs["job"]["databases"][0]
        census = dict(database=db["identity"]["value"], release=db["identity"]["release"], scope=db["identity"]["scope"],
            count_unit="unique_sequences", total_count=110, function_counts={"F": 100, "G": 10})
        cdoc = base.received(inputs, "population-census", base.encoded({"census": census}))
        assertion = dict(schema="blast_database_population_assertion_v1", relation="same_population",
            native_database_operand=" ".join(db["native_paths"]), database_manifest_sha256=db["manifest_file"]["sha256"],
            population_identity={k: deepcopy(v) for k, v in db["identity"].items() if k != "source"},
            census_artifact={**{k: cdoc["artifact"][k] for k in ("sha256", "size_bytes")}, "pointer": "/census"})
        adoc = base.received(inputs, "population-assertion", base.encoded({"assertion": assertion}))
        payload["documents"] += [cdoc, adoc]
        unit["database_profile"] = dict(census, source=cdoc["document_key"])
        unit["database_population_associations"] = [dict(association_key="synthetic-population", database_key=db["database_key"],
            assertion_source=dict(source_ref=adoc["document_key"], pointer="/assertion"),
            census_source=dict(source_ref=cdoc["document_key"], pointer="/census"))]
    original_bundle_size(inputs)
    return payload


def source_change(inputs, payload, key, value):
    raw = base.encoded(value)
    declaration = next(d for d in payload["documents"] if d["document_key"] == key)
    declaration["artifact"].update(sha256=base.sha(raw), size_bytes=len(raw))
    for row in inputs["artifact_catalog"]["retained_sources"]:
        if row["artifact_ref"] == declaration["artifact"]["artifact_ref"]:
            row.update(sha256=base.sha(raw), size_bytes=len(raw))
    inputs["contents"][declaration["artifact"]["artifact_ref"]] = raw


def fixture(*, fasta=False):
    inputs = base.fixture(doc=base.report(database="/selected/db/target"))
    payload = v3_payload(inputs, fasta=fasta)
    return inputs, payload


def reseal_synthetic(inputs):
    """Finish a deliberately edited synthetic fixture's original artifacts."""
    job, bundle, catalog = inputs["job"], inputs["bundle"], inputs["artifact_catalog"]
    for database in job["databases"]:
        raw = base.encoded(database["manifest"])
        database["manifest_file"].update(sha256=base.sha(raw), size_bytes=len(raw))
        capture = next(r for r in bundle["database_manifest"] if r["database_key"] == database["database_key"])
        capture["native_paths"] = deepcopy(database["native_paths"])
        capture["checks"] = [dict(path=r["path"], expected_sha256=r["sha256"], observed_sha256=r["sha256"],
            size_bytes=r["size_bytes"], checked_at=bundle["sealed_at"], status="verified") for r in database["manifest"]["files"]]
        for row in catalog["entries"]:
            if row["artifact_key"] == capture["manifest_artifact_key"]:
                row.update(sha256=base.sha(raw), size_bytes=len(raw))
                inputs["contents"][row["artifact_ref"]] = raw
        next(r for r in bundle["artifacts"] if r["artifact_key"] == capture["manifest_artifact_key"]).update(
            sha256=base.sha(raw), size_bytes=len(raw))
    request = contracts.requested_job_from_standard_blast_database(job)
    bundle["requested_job"] = request
    bundle["plan"]["requested_job"] = deepcopy(request)
    bundle["plan"]["database_paths"] = {d["database_key"]: deepcopy(d["native_paths"]) for d in job["databases"]}
    for identity in (bundle["identity"], bundle["plan"]["identity"], inputs["attempt_identity"]["identity"]):
        identity["requested_job_sha256"] = base.sha(base.encoded(request))
    bundle["realized_argv"] = contracts.compile_standard_blast_database_argv(job,
        input_paths=bundle["plan"]["input_paths"], database_paths=bundle["plan"]["database_paths"],
        output_directory=bundle["plan"]["output_directory"])
    inputs["attempt_identity"]["plan_sha256"] = base.sha(base.encoded(bundle["plan"]))
    original_bundle_size(inputs)


def run(inputs, payload):
    base.add_metadata(inputs, payload, "sequence_database", "population-metadata")
    return base.run(inputs)


def components(sheets):
    return calculate_blast_sequence_database_components(sheets["sequence"][0]["sheet"])["components"]


def test_population_source_assertion_preserves_native_and_semantic_values(tmp_path):
    inputs, payload = fixture()
    sheets = run(inputs, payload)
    scientific = sheets["sequence"][0]["sheet"]
    assert scientific["schema"] == "blast_sequence_database_result_sheet_v3"
    association = scientific["database_population_associations"][0]
    assert association["selected_database"]["native_database_operand"] == "/selected/db/target"
    assert scientific["search"]["normalized"]["search"]["database"] == "/selected/db/target"
    assert scientific["search_binding"]["database_identity"]["value"] == "target"
    assert association["metadata_source"] == dict(source_ref="source-population-metadata", pointer="/searches/0/database_population_associations/0")
    assert association["assertion_record"]["value"]["census_artifact"] == {k: association["census_record"][k] for k in ("sha256", "size_bytes", "pointer")}
    result = components(sheets)
    assert result["function_weights"]["unadjusted_probabilities"] == {"F": .8, "G": .2}
    assert result["function_weights"]["representation_adjusted_probabilities"] == pytest.approx({"F": 2 / 7, "G": 5 / 7})
    assert result["database_sheet"]["database_population_relation"]["status"] == "available"
    (tmp_path / "synthetic-populated-sheet.json").write_text(json.dumps(sheets, indent=2) + "\n")
    (tmp_path / "synthetic-components.json").write_text(json.dumps(result, indent=2) + "\n")


@pytest.mark.parametrize("failure", ["pointer", "unreceived", "missing_bytes", "wrong_manifest", "wrong_operand", "malformed"])
def test_unresolved_and_conflicting_assertions_survive_with_original_measurements(failure):
    inputs, payload = fixture()
    assoc = payload["searches"][0]["database_population_associations"][0]
    if failure == "pointer":
        assoc["assertion_source"]["pointer"] = "/missing"
    elif failure == "unreceived":
        inputs["artifact_catalog"]["retained_sources"] = [r for r in inputs["artifact_catalog"]["retained_sources"] if r["source_ref"] != "source-population-assertion"]
        inputs["contents"].pop("artifact-population-assertion")
    elif failure == "missing_bytes":
        inputs["contents"].pop("artifact-population-assertion")
    else:
        doc = json.loads(inputs["contents"]["artifact-population-assertion"])
        if failure == "wrong_manifest": doc["assertion"]["database_manifest_sha256"] = "0" * 64
        elif failure == "wrong_operand": doc["assertion"]["native_database_operand"] = "/another/target"
        else: doc["assertion"] = {"not_an_assertion": True}
        source_change(inputs, payload, "population-assertion", doc)
    sheets = run(inputs, payload)
    association = sheets["sequence"][0]["sheet"]["database_population_associations"][0]
    assert association["assertion_source"]["source_ref"] == "source-population-assertion"
    if failure in {"pointer", "unreceived", "missing_bytes"}:
        assert association["assertion_record"] is None
    else:
        assert association["assertion_record"]["value"] == doc["assertion"]
    result = components(sheets)
    assert result["function_weights"]["unadjusted_probabilities"] == {"F": .8, "G": .2}
    assert result["function_weights"]["representation_adjusted_probabilities"] is None
    assert len(result["database_sheet"]["hits"]) == 2


def test_population_fasta_original_ordinals_and_parameter_only_saved_validation(monkeypatch):
    inputs, payload = fixture(fasta=True)
    sheets = run(inputs, payload)
    inner = components(sheets)["database_sheet"]
    frozen = base.encoded(sheets)
    assert [r["binding"]["record_locator"]["record_ordinal"] for r in sheets["sequence"][0]["sheet"]["sequence_identity_bindings"]] == [0, 1]
    def forbidden(*args, **kwargs):
        pytest.fail("saved validation reacquired or repopulated metadata")
    for module, names in [(population, ("extract_native_blast_database_population_associations", "_retain_document_records", "_retain_preparation_records")),
            (standard, ("prepare_standard_blast_database_inputs", "populate_standard_blast_database_sheets", "qualify_standard_blast_sequence_metadata",
                        "validate_native_blast_database_metadata_payload", "parse_sequences")),
            (builtins, ("open",)), (Path, ("read_bytes", "read_text", "open")), (socket, ("socket",)), (subprocess, ("run", "Popen"))]:
        for name in names: monkeypatch.setattr(module, name, forbidden)
    assert standard.validate_standard_blast_database_sheet_set(sheets) == sheets
    changed = calculate_database_probabilities(inner, model={"temperature_bits": 2})
    assert changed["representation_adjusted_probabilities"] == pytest.approx({"F": 1 / 6, "G": 5 / 6})
    assert base.encoded(sheets) == frozen


@pytest.mark.parametrize("change", ["record_value", "selected_operand", "record_source", "delete_record", "report_source", "drop_association"])
def test_saved_source_forgery_is_rejected(change):
    inputs, payload = fixture()
    sheets = run(inputs, payload)
    metadata = sheets["metadata_binding_results"][0]
    row = metadata["database_population_associations"][0]
    if change == "record_value": row["census_record"]["value"]["total_count"] += 1
    elif change == "selected_operand": row["selected_database"]["native_database_operand"] = "target"
    elif change == "record_source": row["assertion_record"]["source_ref"] = "invented"
    elif change == "delete_record": row["assertion_record"] = None
    elif change == "drop_association": metadata["database_population_associations"] = []
    else: sheets["sequence"][0]["sheet"]["report_source"]["source_ref"] = "invented"
    if change != "report_source":
        sheets["sequence"][0]["sheet"]["database_population_associations"] = deepcopy(metadata["database_population_associations"])
    with pytest.raises(ValueError):
        standard.validate_standard_blast_database_sheet_set(sheets)


def test_missing_original_bundle_length_cannot_establish_selected_database():
    inputs, payload = fixture()
    inputs["artifact_catalog"].pop("bundle_size_bytes")
    sheets = run(inputs, payload)
    assert sheets["sequence"][0]["sheet"]["database_population_associations"][0]["selected_database"] is None
    assert components(sheets)["function_weights"]["representation_adjusted_probabilities"] is None


@pytest.mark.parametrize("version", ["native_blast_database_sequence_metadata_v1", "native_blast_database_sequence_metadata_v2"])
def test_old_envelopes_do_not_gain_population_fields(version):
    inputs = base.fixture()
    payload = base.numerical_metadata(inputs) if version.endswith("v1") else base.record_metadata(inputs)
    base.add_metadata(inputs, payload, "sequence_database")
    sheets = base.run(inputs)
    assert "population_source_records" not in sheets["prepared_inputs"]["metadata"][0]
    assert "database_population_associations" not in sheets["sequence"][0]["sheet"]
    assert "source_ref" not in sheets["sequence"][0]["sheet"]["report_source"]


@pytest.mark.parametrize("program", ["blastn", "blastp", "blastx", "tblastn", "tblastx"])
def test_all_standard_programs_keep_units_and_source_asserted_weights(program, tmp_path):
    qnt, snt = program in {"blastn", "blastx", "tblastx"}, program in {"blastn", "tblastn", "tblastx"}
    qlen = 12 if qnt and program != "blastn" else 4
    slen = 12 if snt and program != "blastn" else 4
    aligned = "ACGT" if program == "blastn" else "ACDE"
    hits = []
    for i in range(2):
        hsp = base.hsp(20 - 2 * i, qseq=aligned, hseq=aligned, query_to=qlen, hit_to=slen)
        if qnt and program != "blastn": hsp["query_frame"] = 1
        if snt and program != "blastn": hsp["hit_frame"] = 1
        hits.append(base.hit(i, length=slen, hsps=[hsp]))
    doc = base.report(program, query_len=qlen, hits=hits, database="/selected/db/target")
    query = ("ACGTACGTACGT" if qlen == 12 else "ACGT" if qnt else "ACDE")
    inputs = base.fixture(program, query=(">q\n" + query + "\n").encode(), doc=doc)
    sequences = ("ACGTACGTACGT", "ACGAACGTACGT") if slen == 12 else ("ACGT", "ACGA") if snt else ("ACDE", "ACDF")
    payload = v3_payload(inputs, sequences=sequences, molecule="nt" if snt else "aa")
    sheets = run(inputs, payload)
    result = components(sheets)
    assert result["coordinate_context"]["query"]["coordinate_unit"] == ("nt" if qnt else "aa")
    assert result["coordinate_context"]["references"][0]["coordinate_unit"] == ("nt" if snt else "aa")
    assert result["function_weights"]["representation_adjusted_probabilities"] == pytest.approx({"F": 2/7, "G": 5/7})
    base.save_example(tmp_path, inputs, sheets, result)


@pytest.mark.parametrize("format", ["tabular6", "tabular7"])
def test_headerless_and_headered_native_tables_preserve_original_database(format):
    fields = ["qseqid", "sseqid", "qlen", "slen", "qstart", "qend", "sstart", "send", "qseq", "sseq", "bitscore", "evalue", "length", "nident", "gaps"]
    raw = ("" if format == "tabular6" else "# BLASTP 2.17.0+\n# Query: q\n# Database: /selected/db/target\n# 2 hits found\n")
    raw += "".join(f"q\ts{i}\t8\t10\t1\t4\t1\t4\tACDE\tACDE\t{20-2*i}\t0\t4\t4\t0\n" for i in range(2))
    inputs = base.fixture(fmt=format, doc=raw.encode(), fields=fields)
    doc = base.report(hits=[base.hit(i, description=[dict(id=f"s{i}", accession=None, title=None, taxid=None)]) for i in range(2)])
    payload = v3_payload(inputs, doc=doc)
    unit = payload["searches"][0]
    for row in [unit, *unit["description_bindings"], *unit["sequence_identity_bindings"]]:
        row["search_key"]["search_pointer"] = "/sections/0"
    sheets = run(inputs, payload)
    assert sheets["sequence"][0]["sheet"]["search"]["normalized"]["search"]["database"] == (
        None if format == "tabular6" else "/selected/db/target")
    assert components(sheets)["function_weights"]["representation_adjusted_probabilities"] == pytest.approx({"F": 2/7, "G": 5/7})


def test_ordered_multi_prefix_operand_is_literal_and_not_a_semantic_rewrite():
    operand = "/selected/db/second /selected/db/first"
    inputs = base.fixture(doc=base.report(database=operand))
    db = inputs["job"]["databases"][0]
    db["native_paths"][:] = operand.split(" ")
    db["manifest"]["files"] = [dict(path=p + suffix, sha256="b"*64, size_bytes=23)
        for p in db["native_paths"] for suffix in (".phr", ".pin", ".psq")]
    reseal_synthetic(inputs)
    payload = v3_payload(inputs)
    sheets = run(inputs, payload)
    row = sheets["sequence"][0]["sheet"]["database_population_associations"][0]
    assert row["selected_database"]["native_database_operand"] == operand
    assert row["selected_database"]["native_paths"] == operand.split(" ")
    assert row["selected_database"]["identity"]["value"] == "target"
    assert components(sheets)["function_weights"]["representation_adjusted_probabilities"] == pytest.approx({"F": 2/7, "G": 5/7})


@pytest.mark.parametrize("case", ["missing_pointer", "missing_source", "conflicting_operand", "duplicate"])
def test_all_selected_declarations_survive_and_no_valid_sibling_hides_a_failure(case):
    inputs, payload = fixture()
    rows = payload["searches"][0]["database_population_associations"]
    second = deepcopy(rows[0])
    if case == "missing_pointer": second["assertion_source"]["pointer"] = "/absent"
    elif case == "missing_source": second["assertion_source"]["source_ref"] = "unresolved-wire-key"
    elif case == "conflicting_operand":
        source = json.loads(inputs["contents"]["artifact-population-assertion"])
        source["assertion"]["native_database_operand"] = "/different/target"
        doc = base.received(inputs, "other-assertion", base.encoded(source))
        payload["documents"].append(doc)
        second["assertion_source"]["source_ref"] = doc["document_key"]
    rows.append(second)
    sheets = run(inputs, payload)
    saved = sheets["sequence"][0]["sheet"]["database_population_associations"]
    assert len(saved) == 2
    assert saved[0]["metadata_source"]["pointer"].endswith("/0")
    assert saved[1]["metadata_source"]["pointer"].endswith("/1")
    result = components(sheets)
    if case == "duplicate":
        assert result["function_weights"]["representation_adjusted_probabilities"] == pytest.approx({"F": 2/7, "G": 5/7})
    else:
        assert result["function_weights"]["representation_adjusted_probabilities"] is None
        if case == "missing_source":
            assert saved[1]["assertion_source"]["source_ref"] == "unresolved-wire-key"
            assert saved[1]["assertion_record"] is None
    assert result["function_weights"]["unadjusted_probabilities"] == {"F": .8, "G": .2}


def test_saved_envelope_cannot_erase_original_resolved_json_and_replace_with_null():
    inputs, payload = fixture()
    sheets = run(inputs, payload)
    envelope = sheets["prepared_inputs"]["metadata"][0]
    envelope["population_source_records"] = [r for r in envelope["population_source_records"] if r["artifact_ref"] != "artifact-population-assertion"]
    for row in (sheets["metadata_binding_results"][0], sheets["sequence"][0]["sheet"]):
        row["database_population_associations"][0]["assertion_record"] = None
    with pytest.raises(ValueError): standard.validate_standard_blast_database_sheet_set(sheets)


@pytest.mark.parametrize("alias", ["source", "digest"])
def test_report_alias_never_becomes_an_independent_population_source(alias):
    inputs, payload = fixture()
    declaration = next(d for d in payload["documents"] if d["document_key"] == "population-assertion")
    entry = next(r for r in inputs["artifact_catalog"]["retained_sources"] if r["artifact_ref"] == "artifact-population-assertion")
    if alias == "source":
        declaration["artifact"]["source_ref"] = entry["source_ref"] = "source-report"
    else:
        source_change(inputs, payload, "population-assertion", json.loads(inputs["contents"]["artifact-report"]))
        payload["searches"][0]["database_population_associations"][0]["assertion_source"]["pointer"] = ""
    result = components(run(inputs, payload))
    assert result["database_sheet"]["database_population_relation"]["status"] == "incompatible"
    assert "blast_database_population_report_used_as_population_source" in result["database_sheet"]["database_population_relation"]["reason_codes"]
    assert result["function_weights"]["unadjusted_probabilities"] == {"F": .8, "G": .2}
    assert result["function_weights"]["representation_adjusted_probabilities"] is None


def test_unrelated_missing_reference_source_does_not_drop_selected_population_rows():
    inputs, payload = fixture()
    inputs["contents"].pop("artifact-sequence-meta-records")
    sheets = run(inputs, payload)
    assert sheets["prepared_inputs"]["metadata"][0]["normalized"]["searches"] == []
    assert len(sheets["sequence"][0]["sheet"]["database_population_associations"]) == 1
    assert len(components(sheets)["database_sheet"]["hits"]) == 2


def test_explicit_empty_associations_do_not_bridge_native_path_and_population():
    inputs, payload = fixture()
    payload["searches"][0]["database_population_associations"] = []
    sheets = run(inputs, payload)
    assert sheets["sequence"][0]["sheet"]["schema"] == "blast_sequence_database_result_sheet_v3"
    assert components(sheets)["function_weights"]["representation_adjusted_probabilities"] is None


def replace_census(inputs, payload, census):
    source_change(inputs, payload, "population-census", {"census": census})
    payload["searches"][0]["database_profile"] = dict(census, source="population-census")
    assertion = json.loads(inputs["contents"]["artifact-population-assertion"])
    declaration = next(d for d in payload["documents"] if d["document_key"] == "population-census")
    assertion["assertion"]["census_artifact"].update({k: declaration["artifact"][k] for k in ("sha256", "size_bytes")})
    source_change(inputs, payload, "population-assertion", assertion)


@pytest.mark.parametrize("case", ["null_release", "null_scope", "different_release", "different_scope", "missing_G", "zero_G"])
def test_population_source_association_does_not_erase_existing_census_qualifications(case):
    inputs = base.fixture(doc=base.report(database="/selected/db/target"))
    if case in {"null_release", "null_scope"}:
        inputs["job"]["databases"][0]["identity"][case.removeprefix("null_")] = None
        reseal_synthetic(inputs)
    payload = v3_payload(inputs)
    census = json.loads(inputs["contents"]["artifact-population-census"])["census"]
    if case == "null_scope": census["scope"] = "selected_sequences"
    elif case == "different_release": census["release"] = "r2"
    elif case == "different_scope": census["scope"] = "supplied_subset"
    elif case == "missing_G": census["function_counts"].pop("G")
    elif case == "zero_G": census["function_counts"]["G"] = 0
    replace_census(inputs, payload, census)
    sheets = run(inputs, payload)
    result = components(sheets)
    assert result["function_weights"]["unadjusted_probabilities"] == {"F": .8, "G": .2}
    assert result["function_weights"]["representation_adjusted_probabilities"] is None


def test_original_database_sidecar_census_is_selected_by_actual_manifest_slot():
    inputs, payload = fixture()
    raw = inputs["contents"]["artifact-population-census"]
    db, bundle, catalog = inputs["job"]["databases"][0], inputs["bundle"], inputs["artifact_catalog"]
    identity = dict(path="/synthetic/original-census.json", artifact_ref="selected-census-sidecar", sha256=base.sha(raw), size_bytes=len(raw))
    db["manifest"]["metadata_manifests"].append(identity)
    key = "database-metadata-" + base.sha(base.encoded(dict(database_key="target", role="metadata", identity=identity)))
    artifact = dict(artifact_key=key, input_key=None, output_key=None, database_key="target", role="metadata",
        relative_path="custody/census-sidecar", format="opaque", fields=[], delimiter=None, sha256=base.sha(raw),
        size_bytes=len(raw), content_assessment="not_parsed")
    bundle["artifacts"].append(artifact)
    bundle["database_manifest"][0]["metadata_manifest_artifacts"].append(dict(identity=identity, artifact_key=key))
    catalog["entries"].append({k: v for k, v in artifact.items() if k != "content_assessment"} |
        dict(source_ref="original-sidecar-source", artifact_ref="original-sidecar-artifact", path="opaque://sidecar"))
    inputs["contents"]["original-sidecar-artifact"] = raw
    declaration = next(d for d in payload["documents"] if d["document_key"] == "population-census")
    declaration["artifact"] = dict(kind="database_metadata_manifest", database_key="target", manifest_index=0)
    reseal_synthetic(inputs)
    assertion = json.loads(inputs["contents"]["artifact-population-assertion"])
    assertion["assertion"]["database_manifest_sha256"] = db["manifest_file"]["sha256"]
    source_change(inputs, payload, "population-assertion", assertion)
    sheets = run(inputs, payload)
    row = sheets["sequence"][0]["sheet"]["database_population_associations"][0]
    assert row["census_source"]["source_ref"] == "original-sidecar-source"
    assert row["census_record"]["artifact_ref"] == "original-sidecar-artifact"
    assert components(sheets)["function_weights"]["representation_adjusted_probabilities"] == pytest.approx({"F": 2/7, "G": 5/7})


def test_tblastn_pssm_query_retains_master_and_supplied_population():
    hits = [base.hit(i, length=12, hsps=[base.hsp(20 - 2*i, query_to=3, hit_to=9, hit_frame=1,
        qseq="ACD", hseq="ACD", align_len=3, identity=3)]) for i in range(2)]
    doc = base.report("psitblastn", query_len=3, hits=hits, database="/selected/db/target")
    inputs = base.fixture("tblastn", kind="pssm", query=base.pssm(), doc=doc)
    payload = v3_payload(inputs, molecule="nt", sequences=("ACGTACGTACGT", "ACGAACGTACGT"))
    sheets = run(inputs, payload)
    assert sheets["sequence"][0]["sheet"]["query_binding"]["axis_kind"] == "pssm_master"
    assert sheets["sequence"][0]["sheet"]["search_binding"]["input_pssm_key"] == '["query",0]'
    assert components(sheets)["function_weights"]["representation_adjusted_probabilities"] == pytest.approx({"F": 2/7, "G": 5/7})


@pytest.mark.parametrize("case", ["invalid_json", "scalar_pointer"])
def test_unusable_json_keeps_null_original_record_and_native_hits(case):
    inputs, payload = fixture()
    if case == "scalar_pointer":
        source_change(inputs, payload, "population-assertion", 5)
    else:
        raw = b'{"assertion":'
        declaration = next(d for d in payload["documents"] if d["document_key"] == "population-assertion")
        declaration["artifact"].update(sha256=base.sha(raw), size_bytes=len(raw))
        entry = next(r for r in inputs["artifact_catalog"]["retained_sources"] if r["artifact_ref"] == "artifact-population-assertion")
        entry.update(sha256=base.sha(raw), size_bytes=len(raw))
        inputs["contents"]["artifact-population-assertion"] = raw
    sheets = run(inputs, payload)
    assert sheets["sequence"][0]["sheet"]["database_population_associations"][0]["assertion_record"] is None
    assert components(sheets)["function_weights"]["unadjusted_probabilities"] == {"F": .8, "G": .2}


def native_six_fixture(tmp_path, program="psiblast", kind="sequence", *, rounds=False):
    from gene_annotation_episode import native_blast_database_contracts as native_contracts
    import test_native_blast_database_metadata as native_base
    from test_blast_sequence_database import native_search, document
    search = native_search(query_len=3 if kind == "pssm" else 12)
    if kind == "pssm":
        for hit in search["hits"]:
            hit["hsps"][0].update(query_from=1, query_to=3, hit_from=1, hit_to=3,
                qseq="ACD", hseq="ACD", align_len=3, identity=3)
    doc = document(program, search)
    if rounds:
        doc = document(program, iterations=[dict(iter_num=i, search=deepcopy(search)) for i in (1, 2)])
    doc["BlastOutput2"][0]["report"]["search_target"]["db"] = "/selected/db/target"
    query = base.pssm() if kind == "pssm" else b"CLUSTAL W\n\nq ACDEFGHIKLMN\nx ACDEFGHIKLMN\n" if kind == "msa" else None
    job, bundle, catalog, _ = native_base.fixture(tmp_path, program=program, kind=kind, query=query, report=doc)
    if kind == "msa": job["query"]["msa_master_record_ordinal"] = 0
    bundle["requested_job"] = native_contracts.requested_job_from_native_blast_database(job)
    bundle["version"] = "native_blast_database_bundle_v1"
    bundle["realized_argv"] = deepcopy(bundle["requested_job"]["argv"])
    inputs = dict(job=job, bundle=bundle, artifact_catalog=catalog, contents={}, metadata_payloads=[])
    metadata_doc = document(program, search)
    payload = v3_payload(inputs, doc=metadata_doc)
    units = [payload["searches"][0]]
    if rounds:
        units = [deepcopy(units[0]), deepcopy(units[0])]
        for i, unit in enumerate(units):
            for row in [unit, *unit["description_bindings"], *unit["sequence_identity_bindings"]]:
                row["search_key"]["search_pointer"] = f"/BlastOutput2/0/report/results/iterations/{i}/search"
    payload["searches"] = units
    for entry in catalog["retained_sources"]:
        if entry["artifact_ref"] in inputs["contents"]:
            path = tmp_path / entry["artifact_ref"]
            path.write_bytes(inputs["contents"][entry["artifact_ref"]])
            entry["path"] = str(path)
    supplied = [native_base.metadata(tmp_path, catalog, "sequence_database", payload, schema_id=VERSION)]
    if program == "deltablast":
        facts = native_base.source(tmp_path, catalog, "stage", b'{"stage":"sequence_database"}')
        binding = native_base.empty_payload("query_identity")
        binding["documents"] = [facts]
        binding["search_bindings"] = [dict(search_key=unit["search_key"], stage="sequence_database", biological_round=None,
            database_key="target", input_pssm_key=None, provenance=dict(source_ref="stage", pointer="/stage")) for unit in units]
        supplied.append(native_base.metadata(tmp_path, catalog, "query_identity", binding, key="query-stage"))
    return native_base, native_base.prepared(job, bundle, catalog, supplied), catalog


@pytest.mark.parametrize("program,kind,rounds", [("psiblast", "sequence", False), ("psiblast", "pssm", False),
    ("psiblast", "msa", False), ("psiblast", "sequence", True), ("deltablast", "sequence", False)])
def test_native_six_sequence_metadata_routes_original_associations(tmp_path, program, kind, rounds):
    native_base, prepared, catalog = native_six_fixture(tmp_path, program, kind, rounds=rounds)
    sheets = native_base.populate(prepared, catalog)
    assert len(sheets["sequence"]) == (2 if rounds else 1)
    for entry in sheets["sequence"]:
        sheet = entry["sheet"]
        assert sheet["schema"] == "blast_sequence_database_result_sheet_v3"
        assert sheet["database_population_associations"][0]["search_key"] == sheet["search"]["search_key"]
        result = calculate_blast_sequence_database_components(sheet)["components"]
        assert result["function_weights"]["representation_adjusted_probabilities"] == pytest.approx({"F": 2/7, "G": 5/7})
        assert population.validate_native_blast_database_population_associations(sheet["database_population_associations"],
            search=sheet["search"], prepared_inputs=prepared,
            source_records=[r for v in prepared["metadata"] for r in v.get("population_source_records", [])],
            database_profile=sheet["database_profile"]) == sheet["database_population_associations"]


def test_native_saved_document_identity_cannot_redirect_an_original_received_declaration(tmp_path):
    native_base, prepared, catalog = native_six_fixture(tmp_path)
    sheets = native_base.populate(prepared, catalog)
    sheet = sheets["sequence"][0]["sheet"]
    validation = prepared["metadata"][0]
    document = next(d for d in validation["normalized"]["documents"] if d["document_key"] == "population-assertion")
    document["source_ref"] = "another-retained-source"
    for record in validation["population_source_records"]:
        if record["artifact_ref"] == document["artifact_ref"]:
            record["source_ref"] = document["source_ref"]
    association = sheet["database_population_associations"][0]
    association["assertion_source"]["source_ref"] = document["source_ref"]
    association["assertion_record"]["source_ref"] = document["source_ref"]
    with pytest.raises(ValueError, match="saved_relation_conflict"):
        population.validate_native_blast_database_population_associations(sheet["database_population_associations"],
            search=sheet["search"], prepared_inputs=prepared,
            source_records=validation["population_source_records"], database_profile=sheet["database_profile"])
