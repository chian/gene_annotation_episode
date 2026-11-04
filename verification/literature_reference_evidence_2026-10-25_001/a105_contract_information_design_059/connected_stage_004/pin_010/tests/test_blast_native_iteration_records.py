"""316 source-derived synthetic reports; no authentic PSI/DELTA output claim.

The actual 313 producer executes a small synthetic writer, captures its original
outputs and verifies files. No BLAST executable, database search or service runs.
Adversarial mutations are in-memory contract counterexamples, never receipts.
"""
from copy import deepcopy
import base64
import builtins
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import warnings

import pytest

from gene_annotation_episode import blast_native_iteration_records as native
from gene_annotation_episode import native_blast_database_contracts as producer
from gene_annotation_episode.blast_iteration_calculators import calculate_blast_iteration_components
from gene_annotation_episode.blast_iteration_inputs import populate_blast_iteration_sheet
from gene_annotation_episode.blast_report_collection import parse_blast_report_collection
from tests.test_native_blast_database_driver import (
    fixture as producer_fixture, run_fixture, refresh_plan, write, PSSM, MSA,
)

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ["qseqid", "sseqid", "qlen", "slen", "qstart", "qend", "sstart", "send", "qseq", "sseq", "bitscore"]
QUERY = b">q\nACDEFGHI\n"
MARKER = b"Search has CONVERGED!"
PREFIX = "blast_native_iteration_"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def report(program="PSIBLAST", *, suffix=MARKER + b"\n", newline=b"\n"):
    rows = [f"# {program} 2.17.0+", "# Query: q", "# Database: synthetic_db", "# 2 hits found",
            "q\tA\t8\t8\t1\t4\t1\t4\tACDE\tACDE\t40",
            "q\tB\t8\t8\t1\t4\t1\t4\tACDE\tACDE\t39"]
    return newline.join(line.encode() for line in rows) + newline + suffix


def make_packet(base, *, raw=None, query=QUERY, program="psiblast", query_kind="sequence",
                fmt="tabular7", fields=None, delimiter="\t", options=None, returncode=0):
    """Return real generated 313 shapes with explicit synthetic payload identity."""
    raw = report(program.upper()) if raw is None else raw
    path, plan, _ = producer_fixture(base, program, query_kind, checkpoint_output=False)
    job = plan["requested_job"]["native_blast_database"]
    script = ("#!" + sys.executable + "\n" + '''import base64, os, pathlib, sys
args = sys.argv[1:]
with open("synthetic-writer-invocations.txt", "a") as stream:
    stream.write("one source-derived synthetic report writer\\n")
pathlib.Path(args[args.index("-out") + 1]).write_bytes(base64.b64decode(os.environ["SYNTHETIC_REPORT_BASE64"]))
print("synthetic custody fixture; not native scientific measurements")
raise SystemExit(int(os.environ["SYNTHETIC_RETURNCODE"]))
''').encode()
    software = write(Path(job["software"]["executable"]), script)
    job["software"].update(sha256=software["sha256"], engine_version="2.17.0+")
    job["environment"] = {"SYNTHETIC_REPORT_BASE64": base64.b64encode(raw).decode(),
                          "SYNTHETIC_RETURNCODE": str(returncode)}
    job["options"] = list(options or [])
    job["inputs"][0].update(write(Path(job["inputs"][0]["path"]), query))
    selection = next(r for r in job["outputs"] if r["role"] == "primary_report")
    selection.update(format=fmt, fields=[] if fmt == "json15" else list(FIELDS if fields is None else fields),
                     delimiter=None if fmt == "json15" else delimiter)
    refresh_plan(path, plan)
    # The independently supplied envelope is built from the original selected
    # plan, before the producer is invoked, not from its asserted bundle.
    envelope = dict(identity={**deepcopy(plan["identity"]), "execution_id": "313.synthetic"},
                    attempt_directory=plan["attempt_directory"], plan_sha256=digest(plan))
    run, bundle = run_fixture(path, plan)
    assert bundle is not None, run.stderr.decode()
    assert producer.validate_native_blast_database_bundle(bundle, original_job=job, attempt_identity=envelope) == bundle
    captures = [a for a in bundle["artifacts"] if a["role"] == "primary_report"]
    actual_raw = (path.parent / captures[0]["relative_path"]).read_bytes() if captures else b""
    assert actual_raw == raw if bundle["process"]["started"] else actual_raw == b""
    key = captures[0]["artifact_key"] if captures else "synthetic-report-not-emitted"
    qcapture = next(a for a in bundle["input_manifest"] if a["input_key"] == job["query"]["input_key"])
    operand = dict(role="query", artifact_key=qcapture["artifact_key"], record_ordinal=0, native_id="q",
        native_title="q", subject_ref=None, molecule="protein", length=8, selected_interval=None, identity=None)
    if "-query_loc" in job["options"]:
        start, end = map(int, job["options"][job["options"].index("-query_loc") + 1].split("-"))
        operand["selected_interval"] = [start - 1, end]
    invocation = dict(execution_program=program, scientific_mode="database", resource_kind="hpc",
        query_kind=query_kind, reference_kind="profile" if program in ("rpsblast", "rpstblastn") else "sequence",
        request=deepcopy(plan["requested_job"]), effective_options={},
        operands=[deepcopy(operand)], completion=dict(native_returncode=bundle["process"]["returncode"],
                                                   producer_complete=not bundle["failures"]))
    descriptor = dict(artifact_key=key, role="primary_report", format=fmt,
                      fields=None if fmt == "json15" else list(selection["fields"]), delimiter=selection["delimiter"])
    collection = parse_blast_report_collection({key: actual_raw}, artifacts=[descriptor], invocation=invocation)
    return dict(report_contents=actual_raw, artifact_key=key, source_ref="synthetic:retained-full-report",
        original_job=deepcopy(job), bundle=bundle, attempt_identity=envelope, query_contents=query,
        query_operand=operand, collection=collection)


def extract(packet):
    return native.extract_blast_tabular7_convergence(**packet)


def codes(result):
    return {i["code"] for i in result["issues"]}


def iteration(packet, extraction):
    sources = [dict(search_key=s["search_key"], report_source=dict(artifact_key=packet["artifact_key"],
        artifact_ref=packet["source_ref"], member_ordinal=None, member_sha256=None)) for s in packet["collection"]["searches"]]
    sheet = populate_blast_iteration_sheet(packet["collection"], report_sources=sources,
        query_bindings=[], search_bindings=[], pssm_sheets=[], checkpoint_bindings=[], sequence_metadata=[],
        profile_metadata=[], comparison_pairs=[], inclusion_records=[], convergence_records=extraction["convergence_records"])
    return sheet, calculate_blast_iteration_components(sheet)


@pytest.fixture(scope="module")
def packet(tmp_path_factory):
    return make_packet(tmp_path_factory.mktemp("synthetic316"))


def assert_retained(packet, out):
    assert set(out) == {"schema", "status", "report", "query", "source_context", "markers", "convergence_records", "issues"}
    assert set(out["report"]) == {"artifact_key", "source_ref", "sha256", "size_bytes", "format", "fields", "delimiter",
                                  "native_programs", "native_versions", "native_text", "native_bytes_base64"}
    assert set(out["query"]) == {"input_key", "artifact_key", "sha256", "size_bytes", "native_text", "native_bytes_base64",
                                 "record_count", "query_operand"}
    for kind in ("report", "query"):
        raw = packet[kind + "_contents"]
        assert base64.b64decode(out[kind]["native_bytes_base64"]) == raw
        assert out[kind]["sha256"] == hashlib.sha256(raw).hexdigest()
        assert out[kind]["size_bytes"] == len(raw)
        if out[kind]["native_text"] is not None:
            assert out[kind]["native_text"].encode() == raw
    assert out["source_context"] == {k: packet[k] for k in ("original_job", "bundle", "attempt_identity")}
    assert json.loads(json.dumps(out, allow_nan=False)) == out
    for issue in out["issues"]:
        assert set(issue) == {"code", "marker_index", "source_pointer", "details"}
        assert issue["code"].removeprefix(PREFIX) in native._CODES
    for marker in out["markers"]:
        assert set(marker) == {"record_key", "byte_span", "line_number", "exact_text", "scope", "issue_codes"}
        start, end = marker["byte_span"]
        assert packet["report_contents"][start:end].decode() == marker["exact_text"]
        token = ["v1", packet["bundle"]["identity"]["attempt_id"], packet["artifact_key"], out["report"]["sha256"], start, end]
        assert marker["record_key"] == "blast-native-convergence:" + digest(token)


def test_source_derived_positive_passes_actual_313_and_311_without_search_scope(packet):
    before = deepcopy(packet)
    out = extract(packet)
    assert_retained(packet, out)
    assert out["status"] == "complete"
    assert out["query"]["record_count"] == 1
    assert out["query"]["query_operand"] == packet["query_operand"]
    assert len(out["markers"]) == len(out["convergence_records"]) == 1
    row = out["convergence_records"][0]
    assert row["native_converged"] is True and row["search_key"] is None
    assert row["evidence"] == dict(origin="native_extractor_output",
        source=dict(source_ref=packet["source_ref"], pointer=""), source_format="ncbi_blastplus_2.17.0_tabular7",
        original_record=packet["report_contents"].decode(), extractor=dict(module=native.__name__,
            function="extract_blast_tabular7_convergence", version="1"))
    sheet, result = iteration(packet, out)
    assert result["convergence_observations"][0]["native_converged"]["value"] is True
    assert all(s["native_converged"]["value"] is None for s in result["searches"])
    assert not result["inclusion_observations"] and not result["checkpoint_associations"]
    assert all(s["stage"] is None and s["biological_round"]["value"] is None for s in result["searches"])
    assert sheet["convergence_records"] == out["convergence_records"]
    assert packet == before


def test_collector_control_message_is_retained_without_counting_an_hsp(packet):
    out = extract(packet)
    _, result = iteration(packet, out)
    row = result["searches"][0]
    counts = {k: v["value"] for k, v in row["counts"].items()}
    assert counts == dict(reported_hit_count=2, reported_hsp_count=2, observed_hsp_count=2,
                         parsed_hit_count=2, parsed_hsp_count=2, declared_alignment_row_count=2)
    original = packet["collection"]["searches"][0]
    assert len(original["native"]["search"]["rows"]) == 2
    assert MARKER.decode() in original["native"]["search"]["text"]
    assert original["row_map"][0]["hsp_ordinals"] == [0]
    assert original["row_map"][1]["hsp_ordinals"] == [1]
    assert not {v["code"] for v in original["issues"]} & {
        "blast_tabular_column_count_invalid", "blast_tabular_reported_row_count_mismatch"}
    assert out["report"]["sha256"] == original["normalized"]["native"]["sha256"]


@pytest.mark.parametrize("program", ["psiblast", "deltablast"])
@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_source_derived_programs_and_exact_byte_line_boundaries(tmp_path, program, newline):
    raw = report(program.upper(), suffix=MARKER + newline, newline=newline)
    # Multi-byte UTF-8 in a retained comment does not shift byte offsets into character offsets.
    raw = "# Query note: β\n".encode() + raw
    args = make_packet(tmp_path, raw=raw, program=program)
    out = extract(args)
    assert out["status"] == "complete"
    assert out["markers"][0]["byte_span"] == [raw.index(MARKER), len(raw)]
    assert out["markers"][0]["line_number"] == 8
    assert out["report"]["native_programs"] == [program.upper()]
    assert out["report"]["native_versions"] == ["2.17.0+"]
    assert_retained(args, out)


def test_delta_multiple_sections_do_not_assign_stage_round_or_final_search(tmp_path):
    raw = report("DELTABLAST", suffix=b"") + b"# Iteration: 7\n" + report("DELTABLAST")
    args = make_packet(tmp_path, raw=raw, program="deltablast", options=["-show_domain_hits"])
    out = extract(args)
    assert out["status"] == "complete"
    _, result = iteration(args, out)
    assert len(result["searches"]) > 1
    assert all(r["native_converged"]["value"] is None and r["stage"] is None for r in result["searches"])
    assert result["convergence_observations"][0]["search_key"] is None


@pytest.mark.parametrize("suffix", [b"", b"# Search has CONVERGED!\n", b"# Query: Search has CONVERGED!\n",
    b"q\tSearch has CONVERGED!\n", b'"Search has CONVERGED!"\n', b"prefix Search has CONVERGED!\n",
    b" Search has CONVERGED!\n", b"Search has CONVERGED! \n", b"Search has converged!\n",
    b"\x0bSearch has CONVERGED!\n", b"Search has NOT CONVERGED!\n"])
def test_absence_comments_titles_substrings_and_non_native_lines_never_false(tmp_path, suffix):
    args = make_packet(tmp_path, raw=report(suffix=suffix))
    out = extract(args)
    assert out["status"] == "unavailable"
    assert out["convergence_records"] == []
    assert out["markers"] == []
    assert PREFIX + "marker_absent" in codes(out)
    assert_retained(args, out)


@pytest.mark.parametrize("suffix", [MARKER, MARKER + b"\r", b"Search has CONVER", b"Search has "])
def test_incomplete_final_marker_preserves_candidate_but_no_boolean(tmp_path, suffix):
    args = make_packet(tmp_path, raw=report(suffix=suffix))
    out = extract(args)
    assert out["convergence_records"] == [] and out["status"] == "unavailable"
    assert PREFIX + "marker_partial" in codes(out)
    assert len(out["markers"]) == 1 and out["markers"][0]["scope"] == "unbound"
    assert_retained(args, out)


def test_two_markers_have_stable_distinct_physical_identities_and_311_duplicates(tmp_path):
    args = make_packet(tmp_path, raw=report(suffix=MARKER + b"\n" + MARKER + b"\r\n"))
    out = extract(args)
    assert out["status"] == "complete" and len(out["convergence_records"]) == 2
    assert len({r["record_key"] for r in out["markers"]}) == 2
    assert PREFIX + "marker_duplicate" in codes(out)
    _, result = iteration(args, out)
    assert [r["native_converged"]["value"] for r in result["convergence_observations"]] == [True, True]
    assert all("blast_iteration_convergence_duplicate" in codes(r) for r in result["convergence_observations"])
    assert all(r["native_converged"]["value"] is None for r in result["searches"])
    assert extract(args) == out


def test_complete_positive_survives_a_later_incomplete_marker(tmp_path):
    args = make_packet(tmp_path, raw=report(suffix=MARKER + b"\nSearch has CONVER"))
    out = extract(args)
    assert out["status"] == "partial" and len(out["markers"]) == 2
    assert len(out["convergence_records"]) == 1
    assert out["convergence_records"][0]["native_converged"] is True
    assert PREFIX + "marker_partial" in codes(out)


@pytest.mark.parametrize("query", [QUERY + QUERY, QUERY + b">q\nACDEFGHK\n", QUERY + b">second\nACDEFGHI\n"])
def test_multiple_queries_even_duplicate_ids_sequences_are_unbound(tmp_path, query):
    args = make_packet(tmp_path, query=query)
    out = extract(args)
    assert out["status"] == "unavailable" and out["query"]["record_count"] == 2
    assert out["query"]["query_operand"] is None
    assert out["convergence_records"][0]["query_operand"] is None
    assert out["convergence_records"][0]["search_key"] is None
    _, result = iteration(args, out)
    assert result["convergence_observations"][0]["native_converged"]["value"] is None
    assert result["convergence_observations"][0]["status"] == "unavailable"
    issue = next(i for i in out["issues"] if i["code"] == PREFIX + "query_scope_unavailable")
    assert len(issue["details"]["records"]) == 2


@pytest.mark.parametrize("query", [b">q\nACDEFGHI", b">q\r\nACDEFGHI\r\n"])
def test_valid_fasta_without_final_newline_and_crlf(tmp_path, query):
    args = make_packet(tmp_path, query=query)
    out = extract(args)
    assert out["status"] == "complete" and out["query"]["record_count"] == 1


def test_blank_preamble_is_not_removed_to_bypass_actual_biopython_reader(tmp_path):
    args = make_packet(tmp_path, query=b"\n" + QUERY)
    assert args["bundle"]["process"]["started"] is True
    out = extract(args)
    assert out["status"] == "unavailable" and out["query"]["record_count"] is None
    assert out["convergence_records"][0]["query_operand"] is None
    assert PREFIX + "query_input_invalid" in codes(out)


def test_parser_warnings_are_not_suppressed(packet, monkeypatch):
    actual = native.SeqIO.parse

    def warned(*args, **kwargs):
        warnings.warn("synthetic warning propagation probe", UserWarning)
        return actual(*args, **kwargs)

    monkeypatch.setattr(native.SeqIO, "parse", warned)
    with pytest.warns(UserWarning, match="synthetic warning propagation probe"):
        assert extract(packet)["status"] == "complete"


@pytest.mark.parametrize("query,expected_count", [(b"", 0), (b">q\n", 1), (b">\nACD\n", 1),
    (b"junk\n>q\nACD\n", None), (QUERY + b">empty\n", 2), (b">q\nACD123\n", 1),
    (b">q\nACD\xff\n", None), (b">q\nACD\n;comment\n", 1)])
def test_actual_producer_failed_malformed_query_keeps_all_readable_records(tmp_path, query, expected_count):
    args = make_packet(tmp_path, query=query)
    assert args["bundle"]["process"]["started"] is False
    out = extract(args)
    assert out["convergence_records"] == []
    assert out["status"] == "unavailable"
    assert out["query"]["record_count"] == expected_count
    assert PREFIX + "query_input_invalid" in codes(out)
    assert_retained(args, out)


@pytest.mark.parametrize("kind,raw", [("msa", MSA), ("pssm", PSSM)])
def test_msa_pssm_do_not_select_master_or_decode_again(tmp_path, kind, raw):
    args = make_packet(tmp_path, query_kind=kind, query=raw)
    out = extract(args)
    assert out["status"] == "unavailable"
    assert PREFIX + "query_format_unsupported" in codes(out)
    assert out["query"]["record_count"] is None and out["query"]["query_operand"] is None
    assert out["convergence_records"][0]["query_operand"] is None
    assert out["source_context"]["bundle"]["associations"]["master_record_ordinal"] is None


@pytest.mark.parametrize("change", ["program", "version", "missing_version", "missing_header", "encoding", "mixed_version", "mixed_program"])
def test_unsupported_header_or_encoding_preserves_candidates_without_boolean(tmp_path, change):
    raw = report()
    raw = {"program": raw.replace(b"PSIBLAST", b"BLASTP"), "version": raw.replace(b"2.17.0+", b"2.16.0+"),
        "missing_version": raw.replace(b" 2.17.0+", b""), "missing_header": raw.split(b"\n", 1)[1],
        "encoding": raw + b"\xff", "mixed_version": b"# PSIBLAST 2.6.0+\n" + raw,
        "mixed_program": b"# BLASTP 2.17.0+\n" + raw}[change]
    args = make_packet(tmp_path, raw=raw)
    out = extract(args)
    assert len(out["markers"]) == 1 and out["convergence_records"] == []
    assert out["status"] == ("incompatible" if change in ("program", "mixed_program") else "unavailable")
    assert_retained(args, out)


@pytest.mark.parametrize("fmt,fields,delimiter", [("tabular6", FIELDS, "\t"), ("tabular7", ["qseqid"], "\t"),
    ("tabular7", FIELDS, "@"), ("json15", None, None)])
def test_wrong_selected_formats_fields_delimiters_remain_selected(tmp_path, fmt, fields, delimiter):
    args = make_packet(tmp_path, fmt=fmt, fields=fields, delimiter=delimiter)
    out = extract(args)
    assert out["status"] == "unavailable" and out["convergence_records"] == []
    assert PREFIX + "report_format_unsupported" in codes(out)
    assert out["report"]["format"] == fmt and out["report"]["delimiter"] == delimiter
    assert out["report"]["fields"] == ([] if fmt == "json15" else fields)
    assert len(out["markers"]) == 1


def test_other_valid_selected_program_is_unsupported_not_false_custody_conflict(tmp_path):
    args = make_packet(tmp_path, program="rpsblast")
    out = extract(args)
    assert out["status"] == "unavailable" and out["convergence_records"] == []
    assert PREFIX + "report_format_unsupported" in codes(out)
    assert PREFIX + "collection_artifact_conflict" not in codes(out)


@pytest.mark.parametrize("returncode", [0, 7])
def test_partial_capture_and_native_failure_keep_scoped_positive(tmp_path, returncode):
    args = make_packet(tmp_path, returncode=returncode)
    if not returncode:
        args["collection"]["invocation"]["completion"]["producer_complete"] = False
    out = extract(args)
    assert out["status"] == "partial"
    assert out["convergence_records"][0]["native_converged"] is True
    assert out["convergence_records"][0]["query_operand"] == args["query_operand"]
    assert out["source_context"]["bundle"]["process"]["returncode"] == returncode
    assert PREFIX + "source_partial" in codes(out)
    if returncode:
        assert PREFIX + "native_failed" in codes(out)


@pytest.mark.parametrize("field,value", [("artifact_key", "different-capture"), ("record_ordinal", 1),
    ("molecule", "dna"), ("length", 9), ("native_id", "guessed-alias"), ("native_title", "different title"),
    ("selected_interval", [1, 4])])
def test_query_operand_contradictions_never_scope_positive(packet, field, value):
    args = deepcopy(packet)
    args["query_operand"][field] = value
    out = extract(args)
    assert out["status"] == "incompatible"
    assert out["query"]["query_operand"] is None
    assert all(r["query_operand"] is None for r in out["convergence_records"])
    assert PREFIX + "query_operand_conflict" in codes(out)


def test_exact_selected_range_and_unknown_biological_identity(tmp_path):
    args = make_packet(tmp_path, options=["-query_loc", "2-6"])
    out = extract(args)
    assert out["status"] == "complete"
    operand = out["convergence_records"][0]["query_operand"]
    assert operand["selected_interval"] == [1, 6] and operand["length"] == 8
    assert operand["identity"] is None and operand["subject_ref"] is None
    changed = deepcopy(args)
    changed["query_operand"]["selected_interval"] = None
    assert extract(changed)["status"] == "incompatible"


def test_query_scope_does_not_require_public_name_or_display_alias(packet):
    args = deepcopy(packet)
    args["query_operand"].update(native_id=None, native_title=None)
    args["collection"]["invocation"]["operands"] = [deepcopy(args["query_operand"])]
    out = extract(args)
    assert out["status"] == "complete"
    assert out["convergence_records"][0]["query_operand"] == args["query_operand"]


def test_rejected_closed_bundle_shape_is_structured_not_byte_loss(packet):
    args = deepcopy(packet)
    args["bundle"]["unselected_field"] = "counterexample"
    out = extract(args)
    assert out["status"] == "incompatible" and out["convergence_records"] == []
    assert PREFIX + "bundle_contract_rejected" in codes(out)
    assert_retained(args, out)


@pytest.mark.parametrize("change", ["report_bytes", "query_bytes", "artifact", "collection_digest", "collection_fields",
    "collection_request", "attempt", "plan", "bundle_association", "software"])
def test_byte_custody_and_independent_attempt_contradictions(packet, change):
    args = deepcopy(packet)
    if change == "report_bytes": args["report_contents"] += b"# different original bytes\n"
    elif change == "query_bytes": args["query_contents"] = b">q\nACDEFGHK\n"
    elif change == "artifact": args["artifact_key"] = next(a["artifact_key"] for a in args["bundle"]["artifacts"] if a["role"] == "stderr")
    elif change == "collection_digest": args["collection"]["artifacts"][0]["sha256"] = "0" * 64
    elif change == "collection_fields": args["collection"]["artifacts"][0]["fields"] = ["qseqid", "sseqid"]
    elif change == "collection_request": args["collection"]["invocation"]["request"] = {}
    elif change == "attempt": args["attempt_identity"]["identity"]["execution_id"] = "another-selected-attempt"
    elif change == "plan": args["bundle"]["plan"]["resource_environment"]["CHANGED"] = "value"
    elif change == "bundle_association": args["bundle"]["associations"]["query_input_key"] = "wrong"
    elif change == "software": args["bundle"]["software"]["observed_sha256"] = "0" * 64
    out = extract(args)
    assert out["status"] == "incompatible" and out["convergence_records"] == []
    assert len(out["markers"]) == 1
    assert_retained(args, out)
    if change in ("attempt", "plan", "bundle_association", "software"):
        issue = next(i for i in out["issues"] if i["code"] == PREFIX + "bundle_contract_rejected")
        with pytest.raises(ValueError) as error:
            producer.validate_native_blast_database_bundle(args["bundle"], original_job=args["original_job"],
                                                          attempt_identity=args["attempt_identity"])
        assert issue["details"]["error_code"] == error.value.args[0]
        assert out["report"]["format"] is None


@pytest.mark.parametrize("name,bad", [("report_contents", "text"), ("query_contents", bytearray(QUERY)),
    ("artifact_key", ""), ("source_ref", None), ("original_job", []), ("bundle", None), ("collection", [])])
def test_caller_type_errors_have_fixed_code_and_path(packet, name, bad):
    args = deepcopy(packet)
    args[name] = bad
    with pytest.raises(ValueError) as error:
        extract(args)
    assert error.value.args == (PREFIX + "input_type_invalid", "/" + name)


@pytest.mark.parametrize("which", ["query_operand", "collection"])
def test_caller_closed_shape_errors_have_fixed_code_and_path(packet, which):
    args = deepcopy(packet)
    args[which]["unknown_field"] = None
    with pytest.raises(ValueError) as error:
        extract(args)
    assert error.value.args == (PREFIX + "input_fields_invalid", "/" + which)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), (1, 2), {1: "not-json-key"}])
def test_non_finite_or_python_shapes_rejected_with_path(packet, value):
    args = deepcopy(packet)
    args["bundle"]["not_json"] = value
    with pytest.raises(ValueError) as error:
        extract(args)
    assert error.value.args == (PREFIX + "finite_json_required", "/bundle/not_json")


def test_cyclic_input_rejected_with_path(packet):
    args = deepcopy(packet)
    args["bundle"]["cycle"] = args["bundle"]
    with pytest.raises(ValueError) as error:
        extract(args)
    assert error.value.args == (PREFIX + "finite_json_required", "/bundle/cycle")


def test_offline_replay_public_validator_real_consumers_and_detachment(packet, monkeypatch):
    from gene_annotation_episode.state import Store

    before = deepcopy(packet)
    expected = extract(packet)
    sheet, components = iteration(packet, expected)
    saved = json.loads(json.dumps(sheet))
    original_validator = producer.validate_native_blast_database_bundle
    calls = []

    def actual_validator(bundle, *, original_job, attempt_identity):
        calls.append(deepcopy(attempt_identity))
        return original_validator(bundle, original_job=original_job, attempt_identity=attempt_identity)

    def forbidden(*args, **kwargs):
        raise AssertionError("extractor/replay attempted file, process, network or Store access")

    monkeypatch.setattr(producer, "validate_native_blast_database_bundle", actual_validator)
    for obj, name in ((builtins, "open"), (io, "open"), (os, "open"), (os, "stat"), (os, "listdir"),
        (os, "system"), (Path, "open"), (Path, "resolve"), (subprocess, "run"), (subprocess, "Popen"),
        (socket, "socket"), (socket, "create_connection"), (socket, "getaddrinfo"), (Store, "__init__")):
        monkeypatch.setattr(obj, name, forbidden)
    first, second = extract(packet), extract(packet)
    assert first == second == expected
    assert calculate_blast_iteration_components(saved) == components
    assert calls == [packet["attempt_identity"], packet["attempt_identity"]]
    first["source_context"]["bundle"]["program"] = "changed"
    first["convergence_records"][0]["query_operand"]["native_id"] = "changed"
    assert packet == before and second == expected
    assert native.__all__ == ["extract_blast_tabular7_convergence"]


def test_programming_error_is_not_converted_into_success(packet, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("programming defect")
    monkeypatch.setattr(producer, "validate_native_blast_database_bundle", broken)
    with pytest.raises(RuntimeError, match="programming defect"):
        extract(packet)
