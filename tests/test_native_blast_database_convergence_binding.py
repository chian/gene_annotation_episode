"""328 source-derived synthetic byte bindings through the actual 313/316/M/311 ports.

The producer fixture executes a tiny file writer, never BLAST. Complete generated
captures and public-path outputs are retained below each test's temporary path.
There is no authentic native PSI/DELTA execution or episode-return claim here.
"""
from copy import deepcopy
import base64
import builtins
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode import native_blast_database_convergence as bridge
from gene_annotation_episode import native_blast_database_metadata as metadata
from gene_annotation_episode import native_blast_database_contracts as producer
from gene_annotation_episode import blast_native_iteration_records as native
from gene_annotation_episode import blast_iteration_inputs as iteration_inputs
from gene_annotation_episode import blast_iteration_calculators as iteration_calculators
from gene_annotation_episode.blast_report_collection import parse_blast_report_collection
from tests.test_blast_native_iteration_records import make_packet, report, MARKER, QUERY, PSSM, MSA
from tests.test_native_blast_database_metadata import empty_payload, source, metadata as metadata_input


ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "verification/tool_graders_native_blast_convergence_bridge_2026-10-26_328"
PREFIX = "native_blast_database_convergence_"


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode()


def save(path, value):
    path.write_bytes(encode(value))


def save_binding(path, args, binding):
    save(path / "bridge-inputs.json", {**{k: v for k, v in args.items() if k != "artifact_contents"},
        "artifact_contents_base64": {k: base64.b64encode(v).decode() for k, v in args["artifact_contents"].items()}})
    save(path / "binding.json", binding)


def make_case(path, **kwargs):
    packet = make_packet(path, **kwargs)
    root = Path(packet["attempt_identity"]["attempt_directory"])
    catalog = dict(bundle_source_ref="source_synthetic328", bundle_artifact_ref="artifact_synthetic328",
        bundle_sha256=hashlib.sha256((root / "bundle.json").read_bytes()).hexdigest(), entries=[], retained_sources=[])
    contents = {}
    for capture in packet["bundle"]["artifacts"]:
        raw = (root / capture["relative_path"]).read_bytes()
        artifact_ref = "artifact_" + hashlib.sha256(raw).hexdigest()
        entry = {k: v for k, v in capture.items() if k != "content_assessment"}
        entry.update(path=str(root / capture["relative_path"]), artifact_ref=artifact_ref, source_ref=artifact_ref)
        catalog["entries"].append(entry)
        contents[capture["artifact_key"]] = raw
    prepared = metadata.prepare_native_blast_database_inputs(job=packet["original_job"], bundle=packet["bundle"],
        artifact_catalog=catalog, metadata_payloads=[], subject_snapshots=[])
    descriptors = [{k: row[k] for k in ("artifact_key", "role", "format", "fields", "delimiter")}
        for row in catalog["entries"] if row["role"] == "primary_report"]
    for row in descriptors:
        if row["format"] == "json15":
            row["fields"] = None
    collection = parse_blast_report_collection({r["artifact_key"]: contents[r["artifact_key"]] for r in descriptors},
        artifacts=descriptors, invocation=prepared["invocation"])
    args = {k: packet[k] for k in ("original_job", "bundle", "attempt_identity")}
    args.update(collection=collection, artifact_catalog=catalog, artifact_contents=contents)
    save(path / "bridge-inputs.json", {**{k: v for k, v in args.items() if k != "artifact_contents"},
        "artifact_contents_base64": {k: base64.b64encode(v).decode() for k, v in contents.items()}})
    save(path / "prepared-inputs.json", prepared)
    return args, prepared


def bind(args):
    return bridge.bind_native_blast_database_convergence(**args)


def populate(args, prepared, binding=None):
    return metadata.populate_native_blast_database_sheets(args["collection"], prepared_inputs=prepared,
        artifact_catalog=args["artifact_catalog"], **({} if binding is None else {"native_convergence": binding}))


def forbid(*args, **kwargs):
    raise AssertionError("forbidden interpretation, calculation or external effect")


@pytest.fixture(scope="module")
def case(tmp_path_factory):
    return make_case(tmp_path_factory.mktemp("synthetic328"))


@pytest.mark.parametrize("program", ["psiblast", "deltablast"])
@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_actual_unique_public_binding_full_spans_and_numerical_sheet(tmp_path, monkeypatch, program, newline):
    raw = "# supplied non-ASCII note β\n".encode() + report(program.upper(), newline=newline, suffix=MARKER + newline)
    args, prepared = make_case(tmp_path, program=program, raw=raw)
    before = deepcopy(args)
    calls, actual = [], native.extract_blast_tabular7_convergence
    def extracting(raw, **kwargs):
        calls.append((raw, deepcopy(kwargs)))
        return actual(raw, **kwargs)
    monkeypatch.setattr(native, "extract_blast_tabular7_convergence", extracting)
    binding = bind(args)
    assert len(calls) == 1
    rkey, qkey = [binding["selected"][n]["artifact_key"] for n in ("report", "query")]
    assert calls[0] == (args["artifact_contents"][rkey], dict(artifact_key=rkey,
        source_ref=binding["selected"]["report"]["catalog"]["source_ref"], original_job=args["original_job"],
        bundle=args["bundle"], attempt_identity=args["attempt_identity"], query_contents=args["artifact_contents"][qkey],
        query_operand=args["collection"]["invocation"]["operands"][0], collection=args["collection"]))
    assert binding["extraction"] == actual(calls[0][0], **calls[0][1])
    assert binding["extraction"]["markers"][0]["byte_span"] == [raw.index(MARKER), len(raw)]
    assert binding["extraction"]["markers"][0]["line_number"] == 8
    artifact = binding["extraction_artifact"]
    encoded = encode(binding["extraction"])
    assert artifact == dict(artifact_ref="artifact_" + hashlib.sha256(encoded).hexdigest(),
        sha256=hashlib.sha256(encoded).hexdigest(), size_bytes=len(encoded))
    legacy = populate(args, prepared)
    sheets = populate(args, prepared, binding)
    assert set(sheets) == set(legacy) | {"native_convergence"}
    assert sheets["schema"] == "native_blast_database_sheet_set_v2"
    for key in set(legacy) - {"schema", "iteration"}:
        assert sheets[key] == legacy[key]
    assert sheets["iteration"] == dict(legacy["iteration"], convergence_records=binding["extraction"]["convergence_records"])
    calculated = iteration_calculators.calculate_blast_iteration_components(sheets["iteration"])
    old_calculated = iteration_calculators.calculate_blast_iteration_components(legacy["iteration"])
    assert calculated["searches"] == old_calculated["searches"]
    assert {k: v["value"] for k, v in calculated["searches"][0]["counts"].items()} == dict(
        reported_hit_count=2, reported_hsp_count=2, observed_hsp_count=2,
        parsed_hit_count=2, parsed_hsp_count=2, declared_alignment_row_count=2)
    assert [r["native_converged"]["value"] for r in calculated["convergence_observations"]] == [True]
    assert all(s["native_converged"]["value"] is None for s in calculated["searches"])
    assert args == before
    for name, value in (("binding", binding), ("legacy-sheets", legacy), ("sheets", sheets), ("calculations", calculated)):
        save(tmp_path / (name + ".json"), value)
    (tmp_path / "native-convergence.json").write_bytes(encoded)


def test_duplicate_markers_remain_distinct_original_records_and_counts(tmp_path):
    raw = report(suffix=MARKER + b"\n" + MARKER + b"\r\n")
    args, prepared = make_case(tmp_path, raw=raw)
    binding = bind(args)
    extraction = binding["extraction"]
    assert len(extraction["markers"]) == len(extraction["convergence_records"]) == 2
    assert len({r["record_key"] for r in extraction["markers"]}) == 2
    start = raw.index(MARKER)
    assert [m["byte_span"] for m in extraction["markers"]] == [[start, start + len(MARKER) + 1], [start + len(MARKER) + 1, len(raw)]]
    sheets = populate(args, prepared, binding)
    result = iteration_calculators.calculate_blast_iteration_components(sheets["iteration"])
    assert [r["native_converged"]["value"] for r in result["convergence_observations"]] == [True, True]
    assert all(any(i["code"] == "blast_iteration_convergence_duplicate" for i in r["issues"]) for r in result["convergence_observations"])
    assert all(v["value"] == 2 for v in result["searches"][0]["counts"].values())
    assert [r["hsp_ordinals"] for r in args["collection"]["searches"][0]["row_map"]] == [[0], [1]]
    for name, value in (("binding", binding), ("sheets", sheets), ("calculations", result)):
        save(tmp_path / (name + ".json"), value)


@pytest.mark.parametrize("change,expected,detail", [("zero", "zero", "no_query_operand"),
    ("distinct", "multiple", "multiple_query_operands"), ("duplicate", "multiple", "multiple_query_operands"),
    ("missing_key", "conflicting", "missing_operand_identity"), ("missing_ordinal", "conflicting", "missing_operand_identity"),
    ("other_artifact", "conflicting", "operand_artifact_conflict"), ("contradiction", "conflicting", "conflicting_operand_values")])
def test_all_real_candidate_classes_never_fall_back_to_an_operand(case, tmp_path, monkeypatch, change, expected, detail):
    args, _ = deepcopy(case)
    operands = args["collection"]["invocation"]["operands"]
    query = deepcopy(operands[0])
    if change == "zero": operands.clear()
    elif change in ("distinct", "duplicate", "contradiction"):
        if change == "distinct": query["record_ordinal"] = 1
        if change == "contradiction": query["length"] += 1
        operands.append(query)
    elif change == "missing_key": operands[0]["artifact_key"] = None
    elif change == "missing_ordinal": operands[0]["record_ordinal"] = None
    else: operands[0]["artifact_key"] = "other-real-candidate"
    # Original indices include non-query operands; no candidate is reindexed.
    operands.insert(0, dict(query, role="database"))
    monkeypatch.setattr(native, "extract_blast_tabular7_convergence", forbid)
    result = bind(args)
    assert result["invocation"] == "not_invoked"
    assert result["extraction"] is result["extraction_artifact"] is None
    assert result["query_binding"] == dict(status=expected, candidates=[dict(operand_index=i, operand=o)
        for i, o in enumerate(operands) if o["role"] == "query"], selected_operand_index=None)
    assert detail in [r["detail_code"] for r in result["issues"]]
    assert bridge.validate_native_blast_database_convergence_binding(result, collection=args["collection"]) == result
    save_binding(tmp_path, args, result)


@pytest.mark.parametrize("name", ["report", "query"])
@pytest.mark.parametrize("change,expected", [("missing_bytes", "bytes_unavailable"), ("missing_catalog", "bytes_unavailable"),
    ("changed_bytes", "identity_conflict"), ("changed_digest", "identity_conflict"), ("wrong_owner_equal_bytes", "identity_conflict")])
def test_captured_byte_and_owner_states_preserve_real_identities(case, tmp_path, monkeypatch, name, change, expected):
    args, prepared = deepcopy(case)
    role = "primary_report" if name == "report" else "query_sequence"
    entry = next(r for r in args["artifact_catalog"]["entries"] if r["role"] == role)
    key = entry["artifact_key"]
    if change == "missing_bytes": args["artifact_contents"].pop(key)
    elif change == "missing_catalog":
        args["artifact_contents"].pop(key)
        args["artifact_catalog"]["entries"].remove(entry)
    elif change == "changed_bytes": args["artifact_contents"][key] += b"changed actual bytes"
    elif change == "changed_digest": entry["sha256"] = "0" * 64
    else: entry["output_key" if name == "report" else "input_key"] = "wrong-selected-owner"
    monkeypatch.setattr(native, "extract_blast_tabular7_convergence", forbid)
    result = bind(args)
    state = result["selected"][name]
    assert state["status"] == expected and state["artifact_key"] == key
    assert result["invocation"] == "not_invoked" and result["extraction"] is None
    if key in args["artifact_contents"]:
        raw = args["artifact_contents"][key]
        assert state["supplied_bytes"] == dict(sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
    if change == "wrong_owner_equal_bytes":
        assert state["capture"] == state["supplied_bytes"]
        # Equal byte projections cannot upgrade the retained wrong-owner state.
        assert bridge.validate_native_blast_database_convergence_binding(result, collection=args["collection"])["selected"][name]["status"] == "identity_conflict"
        sheets = populate(args, prepared, result)
        assert sheets["native_convergence"] == result
        save(tmp_path / "sheets.json", sheets)
    save_binding(tmp_path, args, result)


def test_missing_report_capture_is_distinct_from_missing_bytes(case, tmp_path, monkeypatch):
    args, _ = deepcopy(case)
    bundle = args["bundle"]
    capture = next(a for a in bundle["artifacts"] if a["role"] == "primary_report")
    bundle["artifacts"].remove(capture)
    output = next(o for o in bundle["output_manifest"] if o["output_key"] == capture["output_key"])
    output.update(artifact_keys=[], presence="missing")
    bundle["failures"].append(dict(code="required_output_missing", input_key=None, database_key=None,
        output_key=capture["output_key"], artifact_key=None, native_returncode=0))
    args["artifact_catalog"]["entries"] = [e for e in args["artifact_catalog"]["entries"] if e["artifact_key"] != capture["artifact_key"]]
    args["artifact_contents"].pop(capture["artifact_key"])
    args["collection"]["artifacts"] = []
    args["collection"]["searches"] = []
    args["collection"]["invocation"]["completion"]["producer_complete"] = False
    monkeypatch.setattr(native, "extract_blast_tabular7_convergence", forbid)
    result = bind(args)
    assert result["selected"]["report"] == dict(status="missing_capture", artifact_key=None, capture=None, catalog=None, supplied_bytes=None)
    assert result["query_binding"]["status"] == "unique"
    save_binding(tmp_path, args, result)


def test_missing_query_capture_retains_actual_operand_without_false_conflict(case, tmp_path, monkeypatch):
    args, _ = deepcopy(case)
    bundle = args["bundle"]
    capture = next(a for a in bundle["artifacts"] if a["role"] == "query_sequence")
    bundle["artifacts"].remove(capture)
    bundle["input_manifest"] = [r for r in bundle["input_manifest"] if r["artifact_key"] != capture["artifact_key"]]
    bundle["process"] = dict(started=False, returncode=None, started_at=None, finished_at=None, native_elapsed_seconds=None)
    bundle["failures"] = [dict(code="input_missing", input_key=capture["input_key"], database_key=None,
        output_key=None, artifact_key=None, native_returncode=None)]
    args["artifact_catalog"]["entries"] = [e for e in args["artifact_catalog"]["entries"] if e["artifact_key"] != capture["artifact_key"]]
    args["artifact_contents"].pop(capture["artifact_key"])
    args["collection"]["invocation"]["completion"] = dict(native_returncode=None, producer_complete=False)
    monkeypatch.setattr(native, "extract_blast_tabular7_convergence", forbid)
    result = bind(args)
    assert result["selected"]["query"] == dict(status="missing_capture", artifact_key=None, capture=None, catalog=None, supplied_bytes=None)
    assert result["query_binding"]["status"] == "unique"
    assert result["query_binding"]["candidates"][0]["operand"] == args["collection"]["invocation"]["operands"][0]
    assert result["invocation"] == "not_invoked" and result["extraction"] is None
    assert [i["detail_code"] for i in result["issues"]] == ["capture_absent"]
    save_binding(tmp_path, args, result)


@pytest.mark.parametrize("query", [QUERY + QUERY, QUERY + b">second\nACDEFGHK\n"])
def test_actual_multiple_fasta_preparation_retains_all_operands_and_never_calls316(tmp_path, monkeypatch, query):
    args, prepared = make_case(tmp_path, query=query)
    assert [r["record_ordinal"] for r in prepared["invocation"]["operands"]] == [0, 1]
    monkeypatch.setattr(native, "extract_blast_tabular7_convergence", forbid)
    result = bind(args)
    assert result["query_binding"]["status"] == "multiple"
    assert result["extraction"] is None
    assert len(result["query_binding"]["candidates"]) == 2
    assert populate(args, prepared, result)["iteration"]["convergence_records"] == []
    save(tmp_path / "binding.json", result)


@pytest.mark.parametrize("kind,query,invoked", [("msa", MSA, False), ("pssm", PSSM, True)])
def test_actual_profile_query_preparation_never_fabricates_record_zero(tmp_path, kind, query, invoked):
    args, prepared = make_case(tmp_path, query_kind=kind, query=query)
    result = bind(args)
    assert (result["invocation"] == "invoked") is invoked
    if invoked:
        extraction = result["extraction"]
        assert extraction["status"] == "unavailable"
        assert extraction["query"]["query_operand"] is None
        assert len(extraction["convergence_records"]) == 1
        assert extraction["convergence_records"][0]["query_operand"] is None
        changed = deepcopy(result)
        changed["extraction"]["convergence_records"] = []
        raw = encode(changed["extraction"])
        changed["extraction_artifact"] = dict(artifact_ref="artifact_" + hashlib.sha256(raw).hexdigest(),
            sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
        with pytest.raises(ValueError) as error:
            bridge.validate_native_blast_database_convergence_binding(changed, collection=args["collection"])
        assert error.value.args == (PREFIX + "binding_invalid", "/extraction/convergence_records")
    else:
        assert prepared["selected_master_record_ordinal"] is None
        assert result["query_binding"] == dict(status="zero", candidates=[], selected_operand_index=None)
        assert result["extraction"] is None
    save(tmp_path / "binding.json", result)


@pytest.mark.parametrize("raw,fmt,reason", [(report(suffix=b""), "tabular7", "marker_absent"),
    (report(suffix=b"Search has CONVER"), "tabular7", "marker_partial"),
    (report(suffix=MARKER + b"\nSearch has CONVER"), "tabular7", "marker_partial"),
    (report().replace(b"2.17.0+", b"2.16.0+"), "tabular7", "report_version_unsupported"),
    (report().replace(b" 2.17.0+", b""), "tabular7", "report_version_missing"),
    (report(), "tabular6", "report_format_unsupported"), (report(), "json15", "report_format_unsupported")])
def test_316_partial_absent_and_unsupported_results_are_retained(tmp_path, raw, fmt, reason):
    args, prepared = make_case(tmp_path, raw=raw, fmt=fmt)
    binding = bind(args)
    assert binding["invocation"] == "invoked"
    out = binding["extraction"]
    assert "blast_native_iteration_" + reason in {i["code"] for i in out["issues"]}
    assert base64.b64decode(out["report"]["native_bytes_base64"]) == raw
    assert all(r["native_converged"] is True for r in out["convergence_records"])
    assert populate(args, prepared, binding)["iteration"]["convergence_records"] == out["convergence_records"]
    save(tmp_path / "binding.json", binding)


def test_nonzero_native_output_keeps_positive_and_exact_failure(tmp_path):
    args, prepared = make_case(tmp_path, returncode=7)
    binding = bind(args)
    assert binding["extraction"]["status"] == "partial"
    sheets = populate(args, prepared, binding)
    result = iteration_calculators.calculate_blast_iteration_components(sheets["iteration"])
    assert result["convergence_observations"][0]["native_converged"]["value"] is True
    assert binding["source_context"]["bundle"]["failures"] == args["bundle"]["failures"]
    assert binding["source_context"]["bundle"]["process"]["returncode"] == 7
    assert all(c["value"] == 2 for c in result["searches"][0]["counts"].values())
    for name, value in (("binding", binding), ("sheets", sheets), ("calculations", result)):
        save(tmp_path / (name + ".json"), value)


@pytest.mark.parametrize("scope", ["query", "search"])
def test_supplied_records_keep_namespace_source_order_and_conflicts(tmp_path, scope):
    args, _ = make_case(tmp_path)
    original_binding = bind(args)
    catalog = args["artifact_catalog"]
    document = source(tmp_path, catalog, "supplied-record", b'{"record": {"native_converged": false}}')
    payload = empty_payload("iteration")
    payload["documents"] = [document]
    native_key = args["collection"]["searches"][0]["search_key"]
    address = {"output_key": next(o["output_key"] for o in args["original_job"]["outputs"] if o["role"] == "primary_report"),
        **{k: native_key[k] for k in ("member_ordinal", "report_index", "search_pointer")}}
    record = dict(record_key="source-record", search_key=address if scope == "search" else None,
        query_operand=None if scope == "search" else deepcopy(args["collection"]["invocation"]["operands"][0]), native_converged=False,
        evidence=dict(origin="supplied_source_record", source=dict(source_ref=document["document_key"], pointer="/record"),
            source_format="explicit328", original_record={"native_converged": False}, extractor=None))
    payload["convergence_records"] = [record]
    supplied = metadata_input(tmp_path, catalog, "iteration", payload)
    prepared = metadata.prepare_native_blast_database_inputs(job=args["original_job"], bundle=args["bundle"],
        artifact_catalog=catalog, metadata_payloads=[supplied], subject_snapshots=[])
    assert prepared["invocation"] == args["collection"]["invocation"]
    binding = bind(args)
    assert binding == original_binding
    legacy = populate(args, prepared)
    sheets = populate(args, prepared, binding)
    assert sheets["iteration"]["convergence_records"] == legacy["iteration"]["convergence_records"] + binding["extraction"]["convergence_records"]
    result = iteration_calculators.calculate_blast_iteration_components(sheets["iteration"])
    observed = result["convergence_observations"]
    assert [r["native_converged"]["value"] for r in observed] == ([None, None] if scope == "query" else [False, True])
    assert [r["status"] for r in observed] == (["incompatible", "incompatible"] if scope == "query" else ["available", "available"])
    for name, value in (("binding", binding), ("legacy-sheets", legacy), ("sheets", sheets), ("calculations", result)):
        save(tmp_path / (name + ".json"), value)


def test_actual_legacy_population_is_byte_equal_to_original_m(case):
    args, prepared = case
    path = PACKET / "baseline/native_blast_database_metadata.py"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == "3ab6b866e2a0b5c4bb7605ffbf8cad693cee56fe59b0f438b13a4b2b5566c1c7"
    spec = importlib.util.spec_from_file_location("gene_annotation_episode._original_m328", path)
    original = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original)
    expected = original.populate_native_blast_database_sheets(args["collection"], prepared_inputs=prepared, artifact_catalog=args["artifact_catalog"])
    assert encode(populate(args, prepared)) == encode(expected)
    assert "native_convergence" not in expected
    assert metadata._SCHEMAS == original._SCHEMAS
    registry = original.metadata_schema_registry()
    for row in registry:
        for field in ("validator_module", "populator_module"):
            if row[field] == original.__name__: row[field] = metadata.__name__
    additions = [dict(consumer="sequence_database", schema_id="native_blast_database_sequence_metadata_v2",
        validator_module="gene_annotation_episode.native_blast_database_metadata", validator_function="_validate_sequence_metadata",
        populator_module="gene_annotation_episode.blast_sequence_database", populator_function="populate_blast_sequence_database_sheet"),
        dict(consumer="vdb_function", schema_id="native_blast_vdb_function_metadata_v1",
            validator_module="gene_annotation_episode.native_blast_vdb_function_metadata",
            validator_function="validate_native_blast_vdb_function_metadata_payload",
            populator_module="gene_annotation_episode.native_blast_vdb_function_metadata",
            populator_function="populate_native_blast_vdb_function_sheets")]
    assert metadata.metadata_schema_registry() == registry + additions


def test_pure_bridge_no_calculation_or_io_and_saved_validation_no_interpretation(case, monkeypatch):
    args, prepared = deepcopy(case)
    before = deepcopy(args)
    expected = bind(args)
    from gene_annotation_episode.state import Store
    from gene_annotation_episode import blast_profile_calculators, blast_pssm_calculators, blast_vdb_calculators, blast_sequence_database
    for module in (iteration_calculators, blast_profile_calculators, blast_pssm_calculators, blast_vdb_calculators, blast_sequence_database):
        for name in dir(module):
            if name.startswith("calculate_"): monkeypatch.setattr(module, name, forbid)
    for owner, name in ((builtins, "open"), (io, "open"), (os, "open"), (os, "stat"), (os, "listdir"),
        (os, "system"), (Path, "open"), (Path, "read_bytes"), (Path, "resolve"), (subprocess, "run"), (subprocess, "Popen"),
        (socket, "socket"), (socket, "create_connection"), (socket, "getaddrinfo"), (Store, "__init__")):
        monkeypatch.setattr(owner, name, forbid)
    assert bind(args) == expected
    for owner, name in ((native, "extract_blast_tabular7_convergence"), (native, "_populate"), (native, "_collection"),
        (native, "_fasta"), (native, "_lines"), (iteration_inputs, "populate_blast_iteration_sheet"),
        (iteration_inputs, "_validate"), (iteration_inputs, "_collection"), (metadata, "prepare_native_blast_database_inputs"),
        (metadata, "populate_native_blast_database_sheets")):
        monkeypatch.setattr(owner, name, forbid)
    saved = json.loads(json.dumps(expected))
    result = bridge.validate_native_blast_database_convergence_binding(saved, collection=args["collection"])
    assert result == expected and args == before
    result["query_binding"]["candidates"][0]["operand"]["length"] = 999
    result["source_context"]["original_job"]["options"].append("changed")
    assert saved == expected and args == before


@pytest.mark.parametrize("path,value", [("schema", "other"), ("invocation", "not_invoked"),
    ("selected/report/status", "bytes_unavailable"), ("selected/query_input_key", "other"),
    ("query_binding/selected_operand_index", True), ("query_binding/candidates/0/operand/length", 99),
    ("extraction/report/native_bytes_base64", "ZmFrZQ=="), ("extraction/query/record_count", True),
    ("extraction/markers/0/line_number", 1), ("extraction/markers/0/byte_span/0", 0),
    ("extraction/markers/0/record_key", "fake"), ("extraction/markers/0/scope", "unbound"),
    ("extraction/convergence_records/0/native_converged", False), ("extraction/convergence_records/0/search_key", {}),
    ("extraction/convergence_records/0/evidence/source/pointer", "/fake"),
    ("extraction/convergence_records/0/evidence/original_record", "fake"), ("extraction/status", "unavailable"),
    ("extraction/convergence_records", []), ("extraction/markers", []), ("extraction_artifact/artifact_ref", "artifact_fake")])
def test_strict_saved_validation_rejects_modified_fields_even_rehashed(case, path, value):
    args, _ = case
    binding = bind(args)
    target = binding
    parts = path.split("/")
    for part in parts[:-1]: target = target[int(part)] if isinstance(target, list) else target[part]
    target[int(parts[-1]) if isinstance(target, list) else parts[-1]] = value
    if path.startswith("extraction/"):
        raw = encode(binding["extraction"])
        binding["extraction_artifact"] = dict(artifact_ref="artifact_" + hashlib.sha256(raw).hexdigest(),
            sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
    with pytest.raises(ValueError) as error:
        bridge.validate_native_blast_database_convergence_binding(binding, collection=args["collection"])
    assert error.value.args[0] == PREFIX + "binding_invalid"
    assert len(error.value.args) == 2


@pytest.mark.parametrize("kind", ["attempt", "plan", "job"])
def test_independent_source_context_rejection_propagates_exact_producer_error(case, kind):
    args, _ = deepcopy(case)
    if kind == "attempt": args["attempt_identity"]["identity"]["execution_id"] = "other-attempt"
    elif kind == "plan": args["attempt_identity"]["plan_sha256"] = "0" * 64
    else: args["original_job"]["options"] = ["-num_iterations", "8"]
    with pytest.raises(ValueError) as expected:
        producer.validate_native_blast_database_bundle(args["bundle"], original_job=args["original_job"], attempt_identity=args["attempt_identity"])
    with pytest.raises(ValueError) as error: bind(args)
    assert error.value.args == expected.value.args


def test_m_rechecks_actual_catalog_before_any_population(case, monkeypatch):
    args, prepared = deepcopy(case)
    binding = bind(args)
    query = next(e for e in args["artifact_catalog"]["entries"] if e["role"] == "query_sequence")
    query["input_key"] = "other-owner-same-bytes"
    monkeypatch.setattr(iteration_inputs, "populate_blast_iteration_sheet", forbid)
    with pytest.raises(ValueError) as error: populate(args, prepared, binding)
    assert error.value.args == (PREFIX + "binding_invalid", "/selected/query/catalog")


def test_saved_binding_rejects_detached_collection_context_and_artifact(case):
    args, _ = case
    binding = bind(args)
    for path in ("request", "execution_program", "completion", "artifact"):
        collection = deepcopy(args["collection"])
        if path == "request": collection["invocation"]["request"] = {}
        elif path == "execution_program": collection["invocation"]["execution_program"] = "deltablast"
        elif path == "completion": collection["invocation"]["completion"]["native_returncode"] = 7
        else: collection["artifacts"][0]["sha256"] = "0" * 64
        with pytest.raises(ValueError) as error:
            bridge.validate_native_blast_database_convergence_binding(binding, collection=collection)
        assert error.value.args[0] == PREFIX + "binding_invalid"


def test_saved_exact_nested_error_pointer_and_input_detachment(case):
    args, _ = case
    binding = bind(args)
    binding["extraction"]["markers"][0]["line_number"] = True
    with pytest.raises(ValueError) as error:
        bridge.validate_native_blast_database_convergence_binding(binding, collection=args["collection"])
    assert error.value.args == (PREFIX + "binding_invalid", "/extraction/markers/0/line_number")


def test_ordinary_malformed_row_is_not_hidden_by_supported_marker(tmp_path):
    args, prepared = make_case(tmp_path, raw=report(suffix=b"malformed ordinary row\n" + MARKER + b"\n"))
    binding = bind(args)
    sheets = populate(args, prepared, binding)
    result = iteration_calculators.calculate_blast_iteration_components(sheets["iteration"])
    counts = {k: v["value"] for k, v in result["searches"][0]["counts"].items()}
    assert counts == dict(reported_hit_count=None, reported_hsp_count=3, observed_hsp_count=3,
        parsed_hit_count=2, parsed_hsp_count=2, declared_alignment_row_count=2)
    assert result["convergence_observations"][0]["native_converged"]["value"] is True
    assert [r["hsp_ordinals"] for r in args["collection"]["searches"][0]["row_map"]] == [[0], [1]]
    for name, value in (("binding", binding), ("sheets", sheets), ("calculations", result)):
        save(tmp_path / (name + ".json"), value)


@pytest.mark.parametrize("change", ["unknown_bytes", "nonbytes", "extra_binding", "float_index", "nan", "cycle"])
def test_finite_closed_shape_errors_have_fixed_code_and_pointer(case, change):
    args, _ = deepcopy(case)
    if change == "unknown_bytes": args["artifact_contents"]["not-cataloged"] = b"bytes"
    elif change == "nonbytes": args["artifact_contents"][next(iter(args["artifact_contents"]))] = "text"
    elif change == "extra_binding": args["collection"]["extra"] = 1
    elif change == "float_index": args["collection"]["invocation"]["operands"][0]["record_ordinal"] = 0.0
    elif change == "nan": args["collection"]["invocation"]["effective_options"]["x"] = float("nan")
    else: args["collection"]["cycle"] = args["collection"]
    with pytest.raises(ValueError) as error: bind(args)
    assert error.value.args[0] == PREFIX + "input_invalid"
    assert len(error.value.args) == 2


def test_bindings_full_sheets_and_calculations_are_equal_across_hash_seeds(tmp_path):
    make_case(tmp_path, raw=report(suffix=MARKER + b"\n" + MARKER + b"\r\n"))
    script = '''import base64, json, pathlib, sys
from gene_annotation_episode.native_blast_database_convergence import bind_native_blast_database_convergence
from gene_annotation_episode.native_blast_database_metadata import populate_native_blast_database_sheets
from gene_annotation_episode.blast_iteration_calculators import calculate_blast_iteration_components
root = pathlib.Path(sys.argv[1])
args = json.loads((root / "bridge-inputs.json").read_bytes())
args["artifact_contents"] = {k: base64.b64decode(v) for k, v in args.pop("artifact_contents_base64").items()}
prepared = json.loads((root / "prepared-inputs.json").read_bytes())
binding = bind_native_blast_database_convergence(**args)
sheets = populate_native_blast_database_sheets(args["collection"], prepared_inputs=prepared,
    artifact_catalog=args["artifact_catalog"], native_convergence=binding)
result = dict(binding=binding, sheets=sheets, calculations=calculate_blast_iteration_components(sheets["iteration"]))
print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False))
'''
    outputs = []
    for seed in ("1", "8675309"):
        process = subprocess.run([str(ROOT / ".venv/bin/python"), "-B", "-c", script, str(tmp_path)],
            env={**os.environ, "PYTHONHASHSEED": seed}, capture_output=True, check=True)
        (tmp_path / ("hash-seed-" + seed + ".json")).write_bytes(process.stdout)
        (tmp_path / ("hash-seed-" + seed + ".stderr.txt")).write_bytes(process.stderr)
        outputs.append(process.stdout)
    assert outputs[0] == outputs[1]
