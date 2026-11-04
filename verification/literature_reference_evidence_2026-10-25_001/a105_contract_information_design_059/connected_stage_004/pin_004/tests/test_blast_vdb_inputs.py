"""Synthetic native-format and closed-binding tests; no VDB executable runs."""
from copy import deepcopy
import hashlib
import io
import json
import zipfile

import pytest

from gene_annotation_episode.blast_report_collection import parse_blast_report_collection
from gene_annotation_episode.blast_vdb_inputs import (
    populate_blast_vdb_sheet as populate, parse_ncbi_sra_runinfo as runinfo,
    parse_blast_vdb_member_sequences as member_sequences,
    parse_ncbi_gbseq_vdb_metadata as gbseq, bind_blast_vdb_metadata as bind,
)


def identity(value, namespace="synthetic", version=None):
    return dict(namespace=namespace, value=value, version=version)


def provenance(pointer="", ref="synthetic:supplied"):
    return dict(source_ref=ref, pointer=pointer)


def entity(kind, *, dataset=None, member=None, sample=None, feature=None, pssm=None):
    return dict(kind=kind, dataset_key=dataset, member_identifier=member, sample_key=sample,
                feature_identifier=feature, pssm_key=pssm)


def sequence(symbols, molecule="nt"):
    return dict(symbols=symbols, molecule=molecule, length=len(symbols), sha256=hashlib.sha256(symbols.encode()).hexdigest())


def metadata(key, bound, *, identifiers=(), **changes):
    result = dict(metadata_key=key, entity=bound, source_format="supplied_explicit", source_version=None,
        native_record={"fixture_kind": "synthetic_explicit"}, source=provenance("/" + key), linkage_source=provenance("/links/" + key),
        identifiers=list(identifiers), sequence=None, functions=[], taxid=None, taxid_scope="unknown", lineage=[],
        assembly=None, feature=None, master_mapping=None, extraction_method="supplied_explicit", issues=[])
    result.update(changes)
    return result


def hsp(q="ACGTACGT", r=None, **changes):
    r = q if r is None else r
    result = dict(query_from=1, query_to=len(q.replace("-", "")), hit_from=1, hit_to=len(r.replace("-", "")),
        qseq=q, hseq=r, align_len=len(q), identity=sum(a == b and a != "-" for a, b in zip(q, r)),
        gaps=q.count("-") + r.count("-"), score=16, bit_score=20, evalue=.001)
    result.update(changes)
    return result


def collect(*, program="blastn_vdb", query="ACGTACGT", selected=None, hits=None, query_kind="sequence",
            raw=None, format_name="json15", fields=None, completion=None, refkind="vdb_mixed", archive=False):
    op = dict(role="query", artifact_key="synthetic:query", record_ordinal=0, native_id="q", native_title="q",
        subject_ref="synthetic:query", molecule="dna" if program == "blastn_vdb" else "protein", length=len(query),
        selected_interval=selected, identity=None)
    inv = dict(execution_program=program, scientific_mode="database", resource_kind="hpc", query_kind=query_kind,
        reference_kind=refkind, request={"synthetic": True}, effective_options={"requested_hit_limit": None, "requested_hsp_limit": None},
        operands=[op], completion=completion or {"native_returncode": 0, "producer_complete": True})
    if hits is None:
        hits = [dict(len=8, description=[dict(id="r1", accession="r1", title="synthetic read")], hsps=[hsp()]),
                dict(len=8, description=[dict(id="r2", accession="r2", title="synthetic read")], hsps=[hsp()])]
    native_program = "psitblastn" if query_kind == "pssm" else program.removesuffix("_vdb")
    doc = {"BlastOutput2": [{"report": dict(program=native_program, version=native_program.upper() + " 2.17.0+",
        search_target={"db": "synthetic-selected"}, params={}, results={"search": dict(query_id="q", query_title="q",
            query_len=len(query), hits=hits, stat={"db_num": 123, "db_len": 999, "eff_space": 4242})})}]}
    raw = json.dumps(doc).encode() if raw is None else raw
    if archive:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as output:
            output.writestr("first.json", raw); output.writestr("second.json", raw)
        raw = buffer.getvalue(); format_name = "json2_archive"
    result = parse_blast_report_collection({"report": raw}, artifacts=[dict(artifact_key="report", role="primary_report",
        format=format_name, fields=fields, delimiter="\t" if format_name.startswith("tabular") else None)], invocation=inv)
    return result


def inputs(search=None, *, symbols=None, kind="read", samples=True):
    search = collect()["searches"][0] if search is None else search
    key = search["search_key"]; op = search["operand_binding"]
    translated = search["program_context"]["execution_program"] == "tblastn_vdb"
    pssm = search["program_context"]["query_kind"] == "pssm"
    query = None if op is None else dict(operand=deepcopy(op), axis_kind="pssm_master" if pssm else "sequence",
        full_length=op["length"], coordinate_unit="aa" if translated else "nt", sequence_sha256=None if pssm else "a" * 64,
        pssm_key="pssm" if pssm else None, master_mapping_ref=provenance("/master") if pssm else None)
    datasets, members, sequences, metadatas = [], [], [], []
    for hit, rowmap in zip(search["normalized"]["hits"], search["row_map"]):
        h = hit["hit_index"]; description = hit["descriptions"][0]; identifier = identity(description["accession"])
        dkey, sample = f"D{h}", f"S{h}"
        source = provenance(f"/members/{h}")
        full = symbols[h] if symbols is not None else "ACGTACGT"
        seq = sequence(full)
        member = dict(search_key=deepcopy(key), hit_ordinal=h, description_ordinal=rowmap["description_ordinals"][0],
            native_description={f: description.get(f) for f in ("id", "accession", "title", "taxid")}, dataset_key=dkey,
            member_kind=kind, member_identifier=identifier, relationship="reported_origin",
            read_identity=dict(native_read_name=identifier["value"], spot_id=None, read_index=None, source=source) if kind == "read" else None,
            reference_identity=dict(identifier=identifier, full_length=len(full), sequence_sha256=seq["sha256"], source=source) if kind != "read" else None,
            sample_key=sample if samples else None, provenance=source)
        members.append(member)
        mkey = f"member{h}"; skey = f"sample{h}"
        metadatas.append(metadata(mkey, entity("member", dataset=dkey, member=identifier), identifiers=[identifier], sequence=seq))
        if samples:
            metadatas.append(metadata(skey, entity("sample", dataset=dkey, sample=sample), identifiers=[identity(sample, "sample")],
                                     taxid=999, taxid_scope="sample_context"))
        datasets.append(dict(dataset_key=dkey, identifier=identity(dkey), dataset_type="sra" if kind == "read" else "csra",
            selected_input={"kind": "alias", "value": "synthetic-selected"}, snapshot={"release": "r1", "snapshot_id": None, "manifest_sha256": "b" * 64},
            search_context=dict(search_key=deepcopy(key), sra_mode=0 if kind == "read" else 1, include_filtered_reads=False,
                subject_genetic_code=1 if translated else None, input_pssm_key="pssm" if pssm else None, source=provenance("/invocation"),
                query_extent={"mode": "interval" if op and op["selected_interval"] else "full", "interval": op["selected_interval"] if op else None,
                              "source": provenance("/invocation/query_extent")}), run_identifiers=[],
            sample_links=[dict(sample_key=sample, sample_identifier=identity(sample, "sample"), biosample_identifier=None, source=provenance("/sample"))] if samples else [],
            assembly_links=[], metadata_keys=[mkey, skey] if samples else [mkey], source=provenance("/datasets/" + dkey)))
        sequences.append(dict(search_key=deepcopy(key), binding=dict(report_index=key["report_index"], hit_index=h,
            kind="full_sequence_digest", sequence_group="sha256:" + seq["sha256"], algorithm="sha256", digest=seq["sha256"],
            molecule="nt", sequence_length=len(full), source_ref="synthetic:sequences", pointer=f"/{h}",
            linkage_source_ref="synthetic:relations", linkage_pointer=f"/{h}")))
    member = search["normalized"]["native"].get("archive_member")
    return dict(search=search, report_source=dict(artifact_key=key["artifact_key"], artifact_ref="synthetic:report",
        member_ordinal=key["member_ordinal"], member_sha256=member["sha256"] if member else None), query_binding=query,
        dataset_records=datasets, member_bindings=members, sequence_identity_bindings=sequences,
        feature_bindings=[], reference_metadata=metadatas, target_context=None, population_records=None)


RUNINFO = b'Run,Sample,BioSample,Experiment,BioProject,TaxID,spots,bases,SampleName,ReadHash,Extra\nSRR1,SRS1,SAMN1,SRX1,PRJ1,2,10,80,"name, one",opaque,kept\nSRR2,SRS2,SAMN1,SRX2,PRJ1,3,4,32,name2,opaque2,kept2\n'
GBSEQ = b'''<GBSet><GBSeq><GBSeq_length>18</GBSeq_length><GBSeq_moltype>DNA</GBSeq_moltype>
<GBSeq_accession-version>NC_X.1</GBSeq_accession-version><GBSeq_sequence>cccatggctaaacccccc</GBSeq_sequence>
<GBSeq_feature-table><GBFeature><GBFeature_key>source</GBFeature_key><GBFeature_location>1..18</GBFeature_location>
<GBFeature_quals><GBQualifier><GBQualifier_name>db_xref</GBQualifier_name><GBQualifier_value>taxon:2</GBQualifier_value></GBQualifier></GBFeature_quals></GBFeature>
<GBFeature><GBFeature_key>CDS</GBFeature_key><GBFeature_location>4..12</GBFeature_location><GBFeature_quals>
<GBQualifier><GBQualifier_name>codon_start</GBQualifier_name><GBQualifier_value>1</GBQualifier_value></GBQualifier>
<GBQualifier><GBQualifier_name>transl_table</GBQualifier_name><GBQualifier_value>1</GBQualifier_value></GBQualifier>
<GBQualifier><GBQualifier_name>translation</GBQualifier_name><GBQualifier_value>MAK</GBQualifier_value></GBQualifier>
<GBQualifier><GBQualifier_name>EC_number</GBQualifier_name><GBQualifier_value>1.2.3.4</GBQualifier_value></GBQualifier>
<GBQualifier><GBQualifier_name>product</GBQualifier_name><GBQualifier_value>literal source product</GBQualifier_value></GBQualifier>
</GBFeature_quals></GBFeature></GBSeq_feature-table><GBSeq_comment>retained unknown source data</GBSeq_comment></GBSeq></GBSet>'''


def binding(record, key, bound, *, parent=None, member=None, links=()):
    return dict(binding_key="binding:" + key, record_key=deepcopy(record["record_key"]), metadata_key=key,
        entity=bound, parent_metadata_key=parent, member_binding_index=member, identifier_links=list(links), source=provenance("/bindings/" + key))


def extraction_context():
    return dict(dataset_key="D0", selected_input={"kind": "accession", "value": "SRR1"},
        snapshot={"release": None, "snapshot_id": "snapshot", "manifest_sha256": None},
        entry_identifiers=[identity("SRR1.1.2", "NCBI.Seq-id")], native_returncode=0, producer_complete=True,
        include_filtered_reads=False, reference_selection=False, outfmt="%i\t%a\t%l\t%s", source=provenance("/extract"))


def test_populate_closed_detached_finite_and_native_unchanged():
    values = inputs(); old = deepcopy(values); result = populate(**values)
    assert result["search"] == old["search"] and values == old
    values["member_bindings"][0]["native_description"]["title"] = "changed"
    assert result["member_bindings"][0]["native_description"]["title"] == "synthetic read"
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("change,code", [
    (lambda a: a["member_bindings"][0].update(extra=1), "record_fields_invalid"),
    (lambda a: a["member_bindings"][0].update(hit_ordinal=True), "record_value_invalid"),
    (lambda a: a["member_bindings"].append(deepcopy(a["member_bindings"][0])), "duplicate_binding"),
    (lambda a: a["dataset_records"].append(deepcopy(a["dataset_records"][0])), "duplicate_record_key"),
    (lambda a: a["member_bindings"][0].update(dataset_key="missing"), "unknown_dataset_key"),
    (lambda a: a["dataset_records"][0]["metadata_keys"].append("missing"), "unknown_metadata_key"),
    (lambda a: a["reference_metadata"][0]["native_record"].update(n=float("inf")), "finite_json_required"),
])
def test_caller_defects_have_closed_errors(change, code):
    values = inputs(); change(values)
    with pytest.raises(ValueError, match="^blast_vdb_" + code + "$"):
        populate(**values)


def test_runinfo_native_rows_counts_quoting_and_unresolved_entities():
    parsed = runinfo(RUNINFO, source_ref="synthetic:runinfo", source_version=None)
    assert parsed["parse_context"] is None and len(parsed["records"]) == 4
    first, sample, second, sample2 = parsed["records"]
    assert sample["source_entity"]["parent_record_key"] == first["record_key"]
    assert sample2["source_entity"]["parent_record_key"] == second["record_key"]
    assert sample["source_entity"]["sample_identifier"] != sample2["source_entity"]["sample_identifier"]
    assert sample["identifiers"][1] == sample2["identifiers"][1]
    assert first["native_record"]["counts"] == {"spots": 10, "bases": 80}
    assert first["native_record"]["fields"]["SampleName"] == "name, one"
    assert first["native_record"]["fields"]["Extra"] == "kept"
    assert first["taxid_scope"] == "sample_context" and first["sequence"] is None
    assert all("dataset_key" not in r["source_entity"] for r in parsed["records"])
    assert parsed["input_identity"]["sha256"] == hashlib.sha256(RUNINFO).hexdigest()


@pytest.mark.parametrize("raw", [b"Run,Run\na,b\n", b'Run,Sample\n"unterminated', b"\xff"])
def test_runinfo_malformed_is_retained_and_qualified(raw):
    result = runinfo(raw, source_ref="synthetic:bad", source_version=None)
    assert result["issues"] and result["input_identity"]["size_bytes"] == len(raw)


def test_member_sequence_exact_columns_context_and_ambiguity():
    context = extraction_context()
    raw = b"gnl|SRA|SRR1.1.2\tSRR1.1.2\t8\tacgunrya\n"
    parsed = member_sequences(raw, source_ref="synthetic:sequence", source_version="pinned", extraction_context=context)
    assert parsed["records"][0]["sequence"] == sequence("ACGUNRYA")
    assert parsed["parse_context"] == context
    assert parsed["records"][0]["source_entity"]["dataset_identifier"] is None
    context["dataset_key"] = "changed"
    assert parsed["parse_context"]["dataset_key"] == "D0"
    assert parsed["records"][0]["source_entity"]["member_identifier"]["value"] == "SRR1.1.2"
    assert not parsed["issues"]
    failed = extraction_context(); failed["native_returncode"] = 1
    partial = member_sequences(raw + b"bad\n", source_ref="synthetic:sequence", source_version="pinned", extraction_context=failed)
    assert len(partial["records"]) == 1 and partial["issues"]
    assert partial["records"][0]["sequence"] is not None


def test_gbseq_preserves_all_features_full_record_and_no_dataset():
    parsed = gbseq(GBSEQ, source_ref="synthetic:gbseq", source_version="v1")
    assert len(parsed["records"]) == 3
    member, source, cds = parsed["records"]
    assert member["sequence"] == sequence("CCCATGGCTAAACCCCCC")
    assert member["source_entity"]["dataset_identifier"] is None
    assert cds["source_entity"]["parent_record_key"] == member["record_key"]
    assert cds["feature"]["segments"] == [[3, 12]] and cds["feature"]["genetic_code"] == 1
    assert cds["feature"]["translation"] == "MAK" and len(cds["functions"]) == 2
    assert "retained unknown source data" in cds["native_record"]["input_text"]
    assert source["feature"]["key"] == "source" and member["taxid"] == 2


@pytest.mark.parametrize("location", ["join(4..6,10..12)", "<4..12", "OTHER.1:4..12", "4^5"])
def test_unsupported_gbseq_location_never_becomes_exact(location):
    parsed = gbseq(GBSEQ.replace(b"4..12", location.replace("<", "&lt;").encode()), source_ref="synthetic:gbseq", source_version=None)
    row = parsed["records"][2]
    assert row["feature"]["segments"] == [] and row["issues"]
    assert row["feature"]["location"] == location


def test_gbseq_contig_without_sequence_retained():
    raw = b"<GBSet><GBSeq><GBSeq_length>100</GBSeq_length><GBSeq_moltype>DNA</GBSeq_moltype><GBSeq_accession-version>AA.1</GBSeq_accession-version><GBSeq_contig>join(OTHER.1:1..100)</GBSeq_contig></GBSeq></GBSet>"
    parsed = gbseq(raw, source_ref="synthetic:contig", source_version=None)
    assert parsed["records"][0]["sequence"] is None
    assert "OTHER.1" in parsed["native_text"]


def reference_binding_fixture():
    native = dict(len=18, description=[dict(id="NC_X.1", accession="NC_X.1")], hsps=[hsp()])
    values = inputs(collect(hits=[native])["searches"][0], symbols=["CCCATGGCTAAACCCCCC"], kind="reference")
    parsed = gbseq(GBSEQ, source_ref="synthetic:gbseq", source_version="v1")
    identifier = parsed["records"][0]["source_entity"]["member_identifier"]
    values["member_bindings"][0]["member_identifier"] = identifier
    values["member_bindings"][0]["reference_identity"]["identifier"] = identifier
    return values, parsed, identifier


def test_binder_same_sequence_to_two_catalogues_no_origin_promotion():
    values, parsed, identifier = reference_binding_fixture()
    member = values["member_bindings"][0]; member["relationship"] = "catalog_membership"
    dataset = deepcopy(values["dataset_records"][0]); dataset["dataset_key"] = "D1"
    values["dataset_records"].append(dataset)
    second = deepcopy(member); second["dataset_key"] = "D1"; values["member_bindings"].append(second)
    bindings = [binding(parsed["records"][0], f"m{i}", entity("member", dataset=f"D{i}", member=identifier), member=i) for i in range(2)]
    result = bind([parsed], dataset_records=values["dataset_records"], member_bindings=values["member_bindings"], query_binding=values["query_binding"], bindings=bindings)
    assert len(result["reference_metadata"]) == 2
    assert all(r["status"] == "available" for r in result["binding_results"])
    assert values["member_bindings"][0]["relationship"] == "catalog_membership"
    assert len(result["unresolved_record_keys"]) == 2


def test_binder_feature_parent_source_ordinal_and_reparse_tampering():
    values, parsed, identifier = reference_binding_fixture()
    parent = binding(parsed["records"][0], "member", entity("member", dataset="D0", member=identifier), member=0)
    feature = parsed["records"][2]
    child = binding(feature, "cds", entity("feature", dataset="D0", member=identifier, feature=feature["source_entity"]["feature_identifier"]), parent="member")
    kwargs = dict(dataset_records=values["dataset_records"], member_bindings=values["member_bindings"], query_binding=values["query_binding"], bindings=[child, parent])
    result = bind([parsed], **kwargs)
    assert [r["status"] for r in result["binding_results"]] == ["available", "available"]
    assert result["reference_metadata"][0]["feature"]["member_sequence_metadata_key"] == "member"
    bad = deepcopy(parsed); bad["records"][2]["feature"]["translation"] = "AAA"
    assert bind([bad], **kwargs)["binding_results"][0]["status"] == "incompatible"
    bad = deepcopy(parsed); bad["records"][2]["source_entity"]["parent_record_key"]["record_ordinal"] = 1
    assert bind([bad], **kwargs)["binding_results"][0]["status"] == "incompatible"


def test_binder_provenance_only_alias_fails_and_cycles_are_caller_errors():
    values, parsed, identifier = reference_binding_fixture()
    other = identity("different", "NCBI.Nucleotide")
    values["member_bindings"][0]["member_identifier"] = other
    values["member_bindings"][0]["reference_identity"]["identifier"] = other
    row = binding(parsed["records"][0], "m", entity("member", dataset="D0", member=other), member=0,
        links=[dict(source_identifier=identifier, target_identifier=other, representation="literal", source=provenance("/unproven"))])
    kwargs = dict(dataset_records=values["dataset_records"], member_bindings=values["member_bindings"], query_binding=values["query_binding"], bindings=[row])
    result = bind([parsed], **kwargs)
    assert not result["reference_metadata"] and result["binding_results"][0]["status"] == "unavailable"
    row["parent_metadata_key"] = "m"
    with pytest.raises(ValueError, match="blast_vdb_metadata_binding_cycle"):
        bind([parsed], **kwargs)


def test_runinfo_sample_requires_same_native_parent_and_never_merges_biosample_aliases():
    parsed = runinfo(RUNINFO, source_ref="synthetic:runs", source_version=None)
    values = inputs(); rows = []
    for i in range(2):
        dataset, sample = parsed["records"][2*i:2*i+2]
        d = values["dataset_records"][i]; d["identifier"] = dataset["source_entity"]["dataset_identifier"]
        link = d["sample_links"][0]
        link["sample_identifier"] = sample["source_entity"]["sample_identifier"]
        link["biosample_identifier"] = sample["identifiers"][1]
        rows += [binding(dataset, f"dataset{i}", entity("dataset", dataset=d["dataset_key"])),
                 binding(sample, f"sample{i}", entity("sample", dataset=d["dataset_key"], sample=link["sample_key"]), parent=f"dataset{i}")]
    result = bind([parsed], dataset_records=values["dataset_records"], member_bindings=values["member_bindings"], query_binding=values["query_binding"], bindings=rows)
    assert len(result["reference_metadata"]) == 4
    assert result["reference_metadata"][1]["entity"]["sample_key"] != result["reference_metadata"][3]["entity"]["sample_key"]
    rows[1]["parent_metadata_key"] = "dataset1"
    bad = bind([parsed], dataset_records=values["dataset_records"], member_bindings=values["member_bindings"], query_binding=values["query_binding"], bindings=rows)
    assert bad["binding_results"][1]["status"] == "incompatible"


def test_unsupported_native_parser_adapter_not_accepted():
    values, parsed, identifier = reference_binding_fixture()
    parsed["format"] = "ncbi_taxonomy_xml"
    parsed["records"][0]["source_format"] = "ncbi_taxonomy_xml"
    row = binding(parsed["records"][0], "m", entity("member", dataset="D0", member=identifier), member=0)
    result = bind([parsed], dataset_records=values["dataset_records"], member_bindings=values["member_bindings"], query_binding=values["query_binding"], bindings=[row])
    assert result["binding_results"][0]["status"] == "incompatible"


def test_member_parser_context_is_replayed_without_reconstruction():
    context = extraction_context()
    parsed = member_sequences(b"gnl|SRA|SRR1.1.2\tSRR1.1.2\t8\tACGTACGT\n", source_ref="synthetic:member", source_version="pinned", extraction_context=context)
    native = dict(len=8, description=[dict(id="gnl|SRA|SRR1.1.2", accession="SRR1.1.2")], hsps=[hsp()])
    values = inputs(collect(hits=[native])["searches"][0])
    member = values["member_bindings"][0]
    member["member_identifier"] = context["entry_identifiers"][0]
    member["read_identity"]["native_read_name"] = "SRR1.1.2"
    row = binding(parsed["records"][0], "member", entity("member", dataset="D0", member=member["member_identifier"]), member=0)
    kwargs = dict(dataset_records=values["dataset_records"], member_bindings=values["member_bindings"], query_binding=values["query_binding"], bindings=[row])
    assert bind([parsed], **kwargs)["binding_results"][0]["status"] == "available"
    bad = deepcopy(parsed); bad["parse_context"] = None
    assert bind([bad], **kwargs)["binding_results"][0]["status"] == "incompatible"
    bad = deepcopy(parsed); bad["parse_context"]["include_filtered_reads"] = True
    assert bind([bad], **kwargs)["binding_results"][0]["status"] == "incompatible"


def test_gbseq_redundant_interval_conflict_preserves_source_without_exact_location():
    native = b"<GBFeature_intervals><GBInterval><GBInterval_from>5</GBInterval_from><GBInterval_to>13</GBInterval_to><GBInterval_accession>NC_X.1</GBInterval_accession></GBInterval></GBFeature_intervals>"
    parsed = gbseq(GBSEQ.replace(b"<GBFeature_location>4..12</GBFeature_location>", b"<GBFeature_location>4..12</GBFeature_location>" + native),
                   source_ref="synthetic:gbseq", source_version=None)
    assert parsed["records"][2]["feature"]["segments"] == []
    assert any(i["code"] == "blast_vdb_feature_location_conflict" for i in parsed["records"][2]["issues"])


def test_wrong_pssm_same_length_binding_stays_unavailable():
    values = inputs(collect(program="tblastn_vdb", query="MAK", query_kind="pssm")["searches"][0])
    parsed = runinfo(b"Run\nSRR1\n", source_ref="synthetic:master", source_version=None)
    parsed["format"] = "supplied_explicit"
    row = parsed["records"][0]
    row["source_format"] = "supplied_explicit"; row["extraction_method"] = "supplied_explicit"
    row["source_entity"].update(kind="query_master", dataset_identifier=None, pssm_key="wrong")
    row["master_mapping"] = dict(pssm_key="wrong", num_columns=3, columns=[dict(column=i, master_position=i, symbol=s) for i,s in enumerate("MAK")])
    b = binding(row, "master", entity("query_master", pssm="pssm"))
    result = bind([parsed], dataset_records=values["dataset_records"], member_bindings=values["member_bindings"], query_binding=values["query_binding"], bindings=[b])
    assert result["binding_results"][0]["status"] == "unavailable"


def test_malformed_feature_missing_key_and_unknown_molecule_are_not_invented():
    parsed = gbseq(GBSEQ.replace(b"<GBFeature_key>CDS</GBFeature_key>", b""), source_ref="synthetic:gbseq", source_version=None)
    assert parsed["records"][2]["feature"] is None
    assert parsed["records"][2]["issues"]
    parsed = gbseq(GBSEQ.replace(b"<GBSeq_moltype>DNA</GBSeq_moltype>", b"<GBSeq_moltype>unknown</GBSeq_moltype>"), source_ref="synthetic:gbseq", source_version=None)
    assert parsed["records"][0]["sequence"] is None
