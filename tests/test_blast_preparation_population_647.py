"""Saved-only population and typed partial cases; never launches native work."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.blast_database_preparation import populate_database_artifact_set, project_prepared_blast_database
from gene_annotation_episode.blast_preparation_population import populate_blast_preparation_artifact_set as populate, validate_blast_preparation_relationships
from gene_annotation_episode.blast_preparation_inputs import (
    parse_blast_alias_document, parse_blast_aliastool_diagnostics, parse_blast_preparation_list,
    parse_makembindex_diagnostics, parse_makeprofiledb_aux,
)
from gene_annotation_episode.domain import ContractError
from test_blast_preparation_contracts_647 import operation


def occurrence(oid, role, raw=b"fixture", *, direction="input", fmt="text", path=None, ordinal=0):
    digest = hashlib.sha256(raw).hexdigest()
    return {"occurrence_id": oid, "direction": direction, "role": role, "ordinal": ordinal,
        "artifact_ref": "artifact_" + digest, "sha256": digest, "size_bytes": len(raw), "native_format": fmt,
        "completeness": "complete", "native_path": path or "/source/" + oid}


def outcome(rc=0):
    return {"started": True, "returncode": rc, "state": "succeeded" if rc == 0 else "failed",
            "writer_closed": True, "inventory_complete": True}


def identity(kind="unknown"):
    return {"namespace": "test", "value": "prepared", "version": None, "release": None,
            "scope": None, "preparation_type": kind, "source": {"source_ref": "source", "pointer": ""}}


def common(op, *, inputs=(), outputs=(), bindings=(), materializations=(), documents=(), native_outcome=None):
    kind = "sequence_database" if "alias" in op["mode"] or op["mode"].startswith("aggregate") else (
        op["parameters"]["profile_type"] if op["mode"] == "create_profile_database" and op["parameters"]["profile_type"] != "cobalt" else "unknown")
    return dict(operation=op, inputs=list(inputs), outputs=list(outputs), database_bindings=list(bindings),
        materializations=list(materializations), database_key="prepared", identity=identity(kind),
        software={"name": op["program"], "version": "2.17.0+", "executable_sha256": None},
        argv=[op["program"]], native_paths=["/attempt/" + (op["parameters"].get("output_prefix") or "out/ids")],
        documents=list(documents), outcome=native_outcome or outcome())


def projection(record, contract="standard"):
    return project_prepared_blast_database(record, contract=contract,
        preparation_receipt={"path": "/attempt/bundle.json", "artifact_ref": "receipt", "sha256": "2" * 64, "size_bytes": 1},
        input_manifest=None, metadata_manifests=[])


def database(key="db", path="/source/db"):
    row = occurrence(key + "-file", "database_file", path=path + ".nsq", fmt="blastdb_binary")
    binding = {"database_key": key, "kind": "blast_nucleotide_sequence", "molecule": "dna",
        "identity": {"namespace": "fixture", "value": key, "version": None, "release": None},
        "source_ref": "manifest-" + key, "native_paths": [path], "occurrence_ids": [row["occurrence_id"]], "inventory_complete": True}
    return row, binding


def copy_input(original, *, relative="inputs/ids"):
    staged = {**original, "occurrence_id": "staged-" + original["occurrence_id"], "ordinal": original["ordinal"] + 1,
              "native_path": "/attempt/" + relative}
    pair = {k: original[k] for k in ("sha256", "size_bytes")}
    receipt = {"kind": "input_copy", "input_key": original["occurrence_id"], "source_path": original["native_path"],
        "relative_path": relative, "expected": pair, "staged": pair, "final": pair}
    return staged, receipt


def test_gi_native_converted_count_is_not_a_stored_unique_count_and_failure_capture_survives():
    raw = b"Converted 3 GIs into binary GI file\n"
    source = occurrence("ids", "identifier_list", b"9\n3\n9\nnot-a-gi\n")
    stderr = occurrence("stderr", "stderr", raw, direction="output", path="/attempt/stderr")
    binary = occurrence("binary", "identifier_list", b"synthetic-binary", direction="output", fmt="gi_list_binary", path="/attempt/out/ids.gil")
    doc = parse_blast_aliastool_diagnostics(raw, occurrence=stderr)
    args = common(operation("convert_gi_list"), inputs=[source], outputs=[binary, stderr], documents=[doc])
    record = populate(**args)
    assert record["native_metadata"][0]["field_name"] == "identifier_list_converted_count"
    assert record["native_metadata"][0]["value"] == 3
    assert not any(r["field_name"] == "identifier_list_count" for r in record["native_metadata"])
    assert projection(record)["status"] == "unavailable"
    args["outcome"] = outcome(2)
    failed = populate(**args)
    assert failed["inventory_complete"] is True
    assert failed["outputs"][0]["completeness"] == "complete"
    assert any(f["code"] == "native_nonzero_exit" and f["native_returncode"] == 2 for f in failed["failures"])
    assert validate_blast_preparation_relationships(json.loads(json.dumps(failed))) == failed


def test_subset_literal_staged_input_join_preserves_alias_length_13():
    source = occurrence("ids", "identifier_list", b"retained-list", fmt="seqid_list_binary")
    staged, receipt = copy_input(source)
    db, binding = database()
    raw = b'TITLE subset\nDBLIST /source/db\nSEQIDLIST /attempt/inputs/ids\nNSEQ 1\nLENGTH 13\n'
    alias = occurrence("alias", "alias_file", raw, direction="output", fmt="blast_alias_text", path="/attempt/out/subset.nal")
    doc = parse_blast_alias_document(raw, occurrence=alias)
    record = populate(**common(operation("create_subset_alias"), inputs=[source, staged, db], outputs=[alias],
        bindings=[binding], materializations=[receipt], documents=[doc]))
    assert record["failures"] == []
    length = next(f for f in record["native_metadata"] if f["field_name"] == "database_residue_count")
    assert length["value"] == 13 and length["value_basis"] == "native_reported"
    projected = projection(record)
    assert projected["status"] == "available"
    assert projected["manifest"]["preparation"]["method"] == "other_recorded"
    assert projected["manifest"]["identity"] == record["identity"]
    assert {r["path"] for r in projected["manifest"]["files"]} >= {alias["native_path"], staged["native_path"], db["native_path"]}
    bad = deepcopy(record); bad["materializations"][0]["input_key"] = "not-selected"
    with pytest.raises(ContractError): validate_blast_preparation_relationships(bad)


def test_aggregate_order_preserved_and_swapped_native_join_is_qualified():
    a, ba = database("A", "/source/A"); b, bb = database("B", "/source/B")
    op = operation("aggregate_databases")
    op["parameters"]["classic_list"]["entries"] = [
        {"ordinal": i, "database_key": key, "native_path_index": 0, "native_reference": "/source/" + key, "line_number": None}
        for i, key in enumerate(("B", "A", "B"))]
    raw = b'TITLE aggregate\nDBLIST /source/B /source/A /source/B\nNSEQ 9\nLENGTH 99\n'
    alias = occurrence("alias", "alias_file", raw, direction="output", fmt="blast_alias_text", path="/attempt/out/aggregate.nal")
    args = common(op, inputs=[a, b], outputs=[alias], bindings=[ba, bb], documents=[parse_blast_alias_document(raw, occurrence=alias)])
    record = populate(**args)
    assert [d["database_key"] for d in record["dependencies"]] == ["B", "A", "B"]
    assert record["compatibility"] == "unverified"
    bad = deepcopy(record); bad["dependencies"][0]["database_key"] = "A"
    with pytest.raises(ContractError): validate_blast_preparation_relationships(bad)
    args["documents"][0]["rows"][1]["tokens"][0]["value"] = "/wrong/B"
    qualified = populate(**args)
    assert any(f["code"] == "record_association_unresolved" for f in qualified["failures"])
    assert projection(qualified)["status"] == "unavailable"


def test_index_parameters_are_located_not_copied_from_requests():
    op = operation("create_megablast_index")
    fasta = occurrence("sequence", "sequence_input", b">a\nACGT\n", fmt="fasta")
    stderr = occurrence("stderr", "stderr", b"", direction="output", path="/attempt/stderr")
    index = occurrence("index", "index_file", direction="output", fmt="blast_index_binary", path="/attempt/out/index.00.idx")
    record = populate(**common(op, inputs=[fasta], outputs=[stderr, index], documents=[parse_makembindex_diagnostics(b"", occurrence=stderr)]))
    assert record["detail"]["parameter_observations"] == []
    assert record["operation"]["parameters"]["ws_hint"] == 8
    assert record["detail"]["index_members"][0]["association"] == "unresolved"
    assert projection(record)["status"] == "unavailable"


def profile_args_from_retained_success():
    packet = Path(__file__).resolve().parents[1] / "verification/tool_graders_blast_preparation_native_2026-10-28_644/retained_profile28/CAPTURE_003.json"
    captured = json.loads(packet.read_text())["cases"][0]
    assert captured["returncode"] == 0 and captured["writer_closed"] and captured["inventory_complete"]
    raw = captured["native_aux_text"].encode()
    # These are the exact captured file identities, never synthetic binary data.
    outputs = []
    for row in captured["new_files"]:
        suffix = PureSuffix(row["path"])
        role = "stdout" if row["path"].endswith(".stdout") else "stderr" if row["path"].endswith(".stderr") else (
            "profile_file" if suffix in {".aux", ".rps", ".loo", ".freq"} else "database_file")
        outputs.append({"occurrence_id": row["relative_path"], "direction": "output", "role": role, "ordinal": sum(r["role"] == role for r in outputs),
            "artifact_ref": "artifact_" + row["sha256"], "sha256": row["sha256"], "size_bytes": row["size_bytes"],
            "native_format": "blast_profile_aux_text" if suffix == ".aux" else "text" if role in {"stdout", "stderr"} else "blastdb_binary" if role == "database_file" else "unknown",
            "completeness": "complete", "native_path": row["path"]})
    aux = next(r for r in outputs if r["native_format"] == "blast_profile_aux_text")
    assert hashlib.sha256(raw).hexdigest() == aux["sha256"]
    op = operation("create_profile_database")
    # Use a controlled selected-list mapping for pure join validation; measured
    # auxiliary/output bytes above remain the authentic102d evidence.
    list_raw = b"input.asn\n"
    original = occurrence("list", "profile_list", list_raw)
    profile = occurrence("profile", "profile_input", b"controlled parser-opaque input", fmt="pssm_asn1_text")
    rewritten_raw = b"/attempt/inputs/profile\n"
    rewritten = occurrence("rewritten", "materialized_list", rewritten_raw, path="/attempt/inputs/list.native")
    receipt = {"kind": "list_rewrite", "input_key": "list", "original_sha256": original["sha256"],
        "relative_path": "inputs/list.native", "sha256": rewritten["sha256"], "size_bytes": rewritten["size_bytes"],
        "grammar": "profile_whitespace_tokens", "entries": [{"ordinal": 0, "line_number": 1, "token_ordinal": 0,
            "original_token": "input.asn", "target": {"kind": "input", "input_key": "profile"}, "realized_token": "/attempt/inputs/profile"}]}
    args = common(op, inputs=[original, profile, rewritten], outputs=outputs, materializations=[receipt], documents=[
        parse_blast_preparation_list(list_raw, grammar="profile_whitespace_tokens", occurrence=original),
        parse_makeprofiledb_aux(raw, occurrence=aux)])
    args["native_paths"] = [str(Path(aux["native_path"]).with_suffix(""))]
    return args


def PureSuffix(path):
    return Path(path).suffix


def test_authentic_aux_values_and_twelve_file_family_saved_population():
    args = profile_args_from_retained_success()
    record = populate(**args)
    assert len(record["detail"]["profile_members"]) == 12
    volume = record["detail"]["volumes"][0]
    assert {p["parameter"]: p["value"] for p in volume["parameter_observations"]} == {
        "matrix": "BLOSUM62", "gap_open": 11, "gap_extend": 1, "scale": 1.0}
    row = volume["auxiliary_documents"][0]["rows"][0]
    assert row["sequence_length"] == 320 and row["karlin_k"] == pytest.approx(0.0375672)
    assert record["detail"]["profiles"][0]["disposition"] == "unknown"
    assert volume["profile_entry_ordinals"] is None
    assert record["operation"]["parameters"]["matrix"] == "BLOSUM80"
    assert record["compatibility"] == "unverified"
    assert projection(record, "additional")["manifest"]["kind"] == "rps_profile"
    saved = json.loads(json.dumps(record)); assert validate_blast_preparation_relationships(saved) == record
    forged = deepcopy(record); forged["detail"]["profiles"][0].update(disposition="included", reason=None)
    with pytest.raises(ContractError): validate_blast_preparation_relationships(forged)


@pytest.mark.parametrize("profile_type", ["rps", "delta", "cobalt"])
def test_failed_profile_with_surviving_sequence_files_is_not_profile_success(profile_type):
    args = profile_args_from_retained_success()
    args["operation"]["parameters"]["profile_type"] = profile_type
    args["identity"]["preparation_type"] = "unknown" if profile_type == "cobalt" else profile_type
    args["outputs"] = [r for r in args["outputs"] if r["role"] != "profile_file"]
    args["documents"] = [d for d in args["documents"] if d["kind"] != "profile_aux"]
    args["outcome"] = outcome(1)
    record = populate(**args)
    assert record["inventory_complete"] is True
    assert any(f["code"] == "output_family_incomplete" for f in record["failures"])
    assert any(f["code"] == "native_nonzero_exit" for f in record["failures"])
    assert projection(record, "additional")["status"] == "unavailable"


def test_public_dispatcher_has_one_dependency_and_native_metadata_authority():
    source = occurrence("ids", "identifier_list")
    binary = occurrence("binary", "identifier_list", direction="output", fmt="gi_list_binary", path="/attempt/out/ids.gil")
    args = common(operation("convert_gi_list"), inputs=[source], outputs=[binary])
    result = populate(**args)
    context = {k: args.pop(k) for k in ("database_bindings", "materializations", "documents")}
    assert populate_database_artifact_set(**args, dependency_bindings=result["dependencies"],
        native_metadata=result["native_metadata"], preparation_context=context) == result
    with pytest.raises(ContractError):
        populate_database_artifact_set(**args, dependency_bindings=[{}], native_metadata=[], preparation_context=context)


def test_unavailable_original_input_preserves_staged_partial_record():
    source = occurrence("ids", "identifier_list")
    staged, receipt = copy_input(source)
    binary = occurrence("binary", "identifier_list", direction="output", fmt="gi_list_binary", path="/attempt/out/ids.gil")
    record = populate(**common(operation("convert_gi_list"), inputs=[staged], outputs=[binary], materializations=[receipt]))
    assert record["inputs"] == [staged]
    assert any(f["code"] == "input_population_unavailable" for f in record["failures"])
    assert any(f["code"] == "dependency_unavailable" for f in record["failures"])


def test_changed_immutable_copy_is_a_qualified_failure_not_output():
    source = occurrence("ids", "identifier_list")
    staged, receipt = copy_input(source)
    staged["sha256"] = "3" * 64; staged["artifact_ref"] = "artifact_" + staged["sha256"]
    receipt["final"] = {k: staged[k] for k in ("sha256", "size_bytes")}
    binary = occurrence("binary", "identifier_list", direction="output", fmt="gi_list_binary", path="/attempt/out/ids.gil")
    record = populate(**common(operation("convert_gi_list"), inputs=[source, staged], outputs=[binary], materializations=[receipt]))
    assert len(record["outputs"]) == 1
    assert any(f["code"] == "input_identity_mismatch" and f["occurrence_id"] == staged["occurrence_id"] for f in record["failures"])


def test_new_style_index_requires_complete_explicit_database_copy():
    db, binding = database()
    op = operation("create_megablast_index")
    op.update(database_key="db", input_occurrence_ids=[])
    op["parameters"].update(input_format="blastdb", input_occurrence_id=None, source_database_key="db", old_style_index=False, output_prefix=None)
    index = occurrence("index", "index_file", direction="output", fmt="blast_index_binary", path="/attempt/db/native.00.idx")
    args = common(op, inputs=[db], outputs=[index], bindings=[binding]); args["native_paths"] = ["/attempt/db/native"]
    record = populate(**args)
    assert any(f["code"] == "dependency_unavailable" for f in record["failures"])
    staged = {**db, "occurrence_id": "copy", "ordinal": 1, "native_path": "/attempt/db/native.nsq"}
    pair = {k: db[k] for k in ("sha256", "size_bytes")}
    receipt = {"kind": "database_copy", "database_key": "db", "source_path": db["native_path"], "relative_path": "db/native.nsq",
               "expected": pair, "staged": pair, "final": pair}
    args["inputs"].append(staged); args["materializations"] = [receipt]
    record = populate(**args)
    assert not record["failures"]
    assert record["detail"]["index_members"][0]["association"] == "unresolved"  # .00 does not invent source-volume membership.
    assert len(record["outputs"]) == 1
    duplicate = {**db, "occurrence_id": "duplicate-original", "ordinal": 2}
    args["inputs"].append(duplicate)
    args["database_bindings"][0]["occurrence_ids"].append(duplicate["occurrence_id"])
    with pytest.raises(ContractError, match="materialization_original_ambiguous"):
        populate(**args)


def test_file_list_mapping_preserves_duplicates_and_rejects_changed_token_binding():
    a, binding = database("A", "/source/A")
    op = operation("aggregate_databases")
    raw = b"/source/A\n/source/A\n"
    listing = occurrence("list", "database_list", raw)
    op["input_occurrence_ids"] = ["list"]
    op["parameters"]["classic_list"] = {"source": "file", "input_occurrence_id": "list", "entries": [
        {"ordinal": i, "database_key": "A", "native_path_index": 0, "native_reference": "/source/A", "line_number": i + 1}
        for i in range(2)]}
    rewritten = occurrence("rewrite", "materialized_list", raw, path="/attempt/inputs/native.list")
    receipt = {"kind": "list_rewrite", "input_key": "list", "original_sha256": listing["sha256"],
        "relative_path": "inputs/native.list", "sha256": rewritten["sha256"], "size_bytes": rewritten["size_bytes"],
        "grammar": "blast_database_lines", "entries": [{"ordinal": i, "line_number": i + 1, "token_ordinal": 0,
            "original_token": "/source/A", "target": {"kind": "database", "database_key": "A", "native_path_index": 0},
            "realized_token": "/source/A"} for i in range(2)]}
    alias_raw = b'TITLE aggregate\nDBLIST /source/A /source/A\nNSEQ 6\nLENGTH 66\n'
    alias = occurrence("alias", "alias_file", alias_raw, direction="output", fmt="blast_alias_text", path="/attempt/out/aggregate.nal")
    args = common(op, inputs=[a, listing, rewritten], outputs=[alias], bindings=[binding], materializations=[receipt], documents=[
        parse_blast_preparation_list(raw, grammar="blast_database_lines", occurrence=listing), parse_blast_alias_document(alias_raw, occurrence=alias)])
    result = populate(**args)
    assert [r["list_entry_ordinal"] for r in result["dependencies"] if r["role"] == "database"] == [0, 1]
    assert not result["failures"]
    changed = deepcopy(args); changed["materializations"][0]["entries"][1]["target"]["database_key"] = "other"
    with pytest.raises(ContractError): populate(**changed)


def test_vdb_alias_retains_selected_offline_dependency_but_never_projects_as_classic():
    db, binding = database("V", "/source/V")
    config = occurrence("offline", "offline_configuration", b"offline=true\n")
    binding.update(kind="vdb", occurrence_ids=[db["occurrence_id"], config["occurrence_id"]])
    op = operation("aggregate_databases")
    op["parameters"]["classic_list"] = None
    op["parameters"]["vdb_list"] = {"source": "inline", "entries": [{"ordinal": 0, "database_key": "V",
        "native_path_index": 0, "native_reference": "/source/V", "line_number": None}]}
    raw = b'TITLE aggregate\nVDBLIST /source/V\n'
    alias = occurrence("alias", "alias_file", raw, direction="output", fmt="blast_alias_text", path="/attempt/out/aggregate.nal")
    args = common(op, inputs=[db, config], outputs=[alias], bindings=[binding], documents=[parse_blast_alias_document(raw, occurrence=alias)])
    args["identity"]["preparation_type"] = "unknown"
    result = populate(**args)
    assert not result["failures"]
    assert projection(result)["status"] == "unavailable"
    assert projection(result, "additional")["status"] == "unavailable"
    args["inputs"] = [db]; args["database_bindings"][0]["occurrence_ids"] = [db["occurrence_id"]]
    missing = populate(**args)
    assert any(f["code"] == "dependency_unavailable" for f in missing["failures"])


def test_native_profile_exclusion_is_located_and_duplicate_references_stay_unknown():
    args = profile_args_from_retained_success()
    stderr = next(r for r in args["outputs"] if r["role"] == "stderr")
    document = {"version": "blast_preparation_document_v1", "kind": "profile_diagnostics", "occurrence_id": stderr["occurrence_id"],
        "native_fields": [], "checks": [], "failures": [], "rows": [{"line_number": 1, "category": "excluded_low_observations",
            "native_reference": "input.asn", "native_lexeme": "controlled exclusion fixture"}]}
    args["documents"].append(document)
    result = populate(**args)
    assert result["detail"]["profiles"][0]["disposition"] == "excluded"
    assert result["detail"]["profiles"][0]["evidence_line_number"] == 1
    args["operation"]["parameters"]["profile_entries"].append({"ordinal": 1, "input_occurrence_id": "profile",
        "native_reference": "input.asn", "line_number": 2, "token_ordinal": 0})
    # Omit the list rewrite/document in this deliberate partial fixture; missing
    # joins remain typed failures while neither repeated entry gains a disposition.
    args["materializations"] = []
    args["inputs"] = [r for r in args["inputs"] if r["role"] != "materialized_list"]
    args["documents"] = [d for d in args["documents"] if d["kind"] != "list"]
    result = populate(**args)
    assert [p["disposition"] for p in result["detail"]["profiles"]] == ["unknown", "unknown"]


def test_inspection_subjects_remain_file_or_database_and_empty_filters_are_not_zero():
    from gene_annotation_episode.blast_utility_contracts import validate_blast_utility_record
    stream = occurrence("stdout", "stdout", b"\n", direction="output", path="/attempt/stdout")
    _, binding = database()
    filters = {"version": "blast_database_inspection_v2", "operation": operation("show_filters"),
        "original_outcome": outcome(), "subject": {"kind": "database", "database_key": "db"},
        "database_bindings": [binding], "output_occurrence": stream, "native_fields": [], "completeness": "complete",
        "checks": [], "failures": []}
    assert validate_blast_utility_record("DatabaseInspection", filters)["native_fields"] == []
    info = deepcopy(filters); info.update(operation=operation("inspect_seqid_list"),
        subject={"kind": "identifier_list", "occurrence_id": "ids"}, database_bindings=[])
    info["output_occurrence"]["native_format"] = "blast_seqid_list_info_text"
    assert validate_blast_utility_record("DatabaseInspection", info)["subject"]["occurrence_id"] == "ids"
    info["subject"] = {"kind": "database", "database_key": "invented"}
    with pytest.raises(ContractError): validate_blast_utility_record("DatabaseInspection", info)
