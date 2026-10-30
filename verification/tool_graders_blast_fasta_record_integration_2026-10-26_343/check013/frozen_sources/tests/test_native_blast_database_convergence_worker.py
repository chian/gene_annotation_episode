"""Actual captured synthetic report -> bridge -> sheet -> calculations -> rows.

The fixture executes a file writer, never BLAST or a database search. Reuse
checks operate on real saved generations, with interpretation calls forbidden.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from gene_annotation_episode import native_blast_database_result_worker as worker
from gene_annotation_episode import native_blast_database_result_views as views
from gene_annotation_episode import native_blast_database_convergence as bridge
from gene_annotation_episode import native_blast_database_metadata as metadata
from gene_annotation_episode import blast_native_iteration_records as extractor
from tests.test_blast_native_iteration_records import make_packet, report, MARKER
from tests.test_native_blast_database_result_worker import implementation, run_request, reuse_request


ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "verification/tool_graders_native_blast_convergence_worker_2026-10-26_329"


def forbidden(*args, **kwargs):
    raise AssertionError("saved interpretation must not be repeated")


def no_interpretation(monkeypatch):
    monkeypatch.setattr(metadata, "prepare_native_blast_database_inputs", forbidden)
    monkeypatch.setattr(metadata, "populate_native_blast_database_sheets", forbidden)
    monkeypatch.setattr(worker, "parse_blast_report_collection", forbidden)
    monkeypatch.setattr(bridge, "bind_native_blast_database_convergence", forbidden)
    monkeypatch.setattr(extractor, "extract_blast_tabular7_convergence", forbidden)


def request_from_packet(tmp_path, **options):
    packet = make_packet(tmp_path / "capture", **options)
    directory = Path(packet["attempt_identity"]["attempt_directory"])
    bundle = packet["bundle"]
    raw = (directory / "bundle.json").read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    request = dict(version="native_blast_database_result_worker_request_v1", calculation_id="0" * 64,
        bundle=bundle, bundle_artifact_ref="artifact_" + digest,
        bundle_capture=dict(path=str(directory / "bundle.json"), sha256=digest, size_bytes=len(raw)),
        authenticated_attempt=packet["attempt_identity"],
        artifacts=[dict(artifact_key=r["artifact_key"], artifact_ref="artifact_" + r["sha256"],
            path=str(directory / r["relative_path"]), sha256=r["sha256"], size_bytes=r["size_bytes"])
            for r in bundle["artifacts"]],
        metadata_descriptors=[dict(**d, origin="original_job_input", artifact_ref="artifact_" + r["sha256"],
            sha256=r["sha256"], size_bytes=r["size_bytes"])
            for d in packet["original_job"]["metadata_inputs"] for r in bundle["artifacts"] if r["input_key"] == d["input_key"]],
        retained_sources=[], subject_snapshots=[], implementation=implementation(execution_program=packet["original_job"]["program"]),
        output_directory=str(tmp_path / "generation1"), reuse=None, sequence_model=None)
    request["calculation_id"] = worker.native_blast_database_calculation_identity(
        input_identity=worker.native_blast_database_input_identity(request),
        input_implementation_sha256=request["implementation"]["manifest_sha256"], sequence_model=None,
        implementation_manifest_sha256=request["implementation"]["manifest_sha256"])["calculation_id"]
    return request


def load(request, filename):
    return json.loads((Path(request["output_directory"]) / filename).read_bytes())


def rows(request):
    return [json.loads(line) for line in (Path(request["output_directory"]) / "rows.ndjson").read_bytes().splitlines()]


def convergence(request):
    return [r for r in rows(request) if r["family"] == "iteration_convergence"]


@pytest.mark.parametrize("program", ["psiblast", "deltablast"])
@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_full_worker_duplicate_occurrences_actual_artifact_and_unchanged_numbers(tmp_path, monkeypatch, program, newline):
    raw = report(program.upper(), newline=newline, suffix=MARKER + newline + MARKER + newline)
    request = request_from_packet(tmp_path, program=program, raw=raw)
    calls, actual = [], extractor.extract_blast_tabular7_convergence
    def extracting(*args, **kwargs):
        calls.append((args, deepcopy(kwargs)))
        return actual(*args, **kwargs)
    monkeypatch.setattr(extractor, "extract_blast_tabular7_convergence", extracting)
    manifest = run_request(tmp_path, request)
    assert manifest["status"] != "failed", load(request, "diagnostics.json")
    assert manifest["version"] == "native_blast_database_result_worker_manifest_v2"
    assert len(calls) == 1 and calls[0][1]["attempt_identity"] == request["authenticated_attempt"]
    sheets, calculated = load(request, "sheets.json"), load(request, "calculations.json")
    binding = sheets["native_convergence"]
    extraction = binding["extraction"]
    assert extraction == actual(*calls[0][0], **calls[0][1])
    encoded = (Path(request["output_directory"]) / "native-convergence.json").read_bytes()
    assert encoded == worker._json_bytes(extraction)
    assert binding["extraction_artifact"] == dict(artifact_ref="artifact_" + hashlib.sha256(encoded).hexdigest(),
        sha256=hashlib.sha256(encoded).hexdigest(), size_bytes=len(encoded))
    published = convergence(request)
    assert len(published) == len({r["record_key"] for r in published}) == 2
    for j, row in enumerate(published):
        assert row["identity"] == dict(record_source=dict(source_ref=binding["extraction_artifact"]["artifact_ref"],
            pointer=f"/convergence_records/{j}"), scope="query", search_key=None,
            query_identity=dict(artifact_key=binding["selected"]["query"]["artifact_key"], record_ordinal=0,
                axis_kind="sequence", selected_interval=None))
        assert row["booleans"][0]["value"] is True
        assert row["measurements"] == []
        assert row["component_refs"] == [dict(artifact_role="calculations", pointer=f"/iteration/convergence_observations/{j}"),
            dict(artifact_role="sheets", pointer=f"/native_convergence/extraction/convergence_records/{j}"),
            dict(artifact_role="sheets", pointer=f"/native_convergence/extraction/markers/{j}")]
        for ref in row["component_refs"]:
            worker._at(sheets if ref["artifact_role"] == "sheets" else calculated, ref["pointer"])
    search = calculated["iteration"]["searches"][0]
    assert all(v["value"] == 2 for v in search["counts"].values())
    assert search["native_converged"]["value"] is None
    legacy = deepcopy(sheets)
    legacy.pop("native_convergence"); legacy["schema"] = "native_blast_database_sheet_set_v1"
    legacy["iteration"]["convergence_records"] = []
    old_calculated = worker.calculate_native_blast_database_sheets(legacy, sequence_model=None)
    old_rows = worker.build_native_blast_database_rows(bundle_identity=request["bundle"]["identity"],
        calculation_id=request["calculation_id"], sheet_set=legacy, calculations=old_calculated)
    assert old_rows == [r for r in rows(request) if r["family"] != "iteration_convergence"]


@pytest.mark.parametrize("suffix,expected", [(b"", 0), (b"Search has CONVER", 0), (MARKER + b"\nSearch has CONVER", 1)])
def test_absent_partial_and_complete_candidates_are_not_false(tmp_path, suffix, expected):
    request = request_from_packet(tmp_path, raw=report(suffix=suffix))
    manifest = run_request(tmp_path, request)
    assert manifest["status"] != "failed", load(request, "diagnostics.json")
    assert len(convergence(request)) == expected
    assert all(row["booleans"][0]["value"] is True for row in convergence(request))
    assert all(s["native_converged"]["value"] is None for s in load(request, "calculations.json")["iteration"]["searches"])


def test_partial_native_exit_keeps_true_and_actual_failure(tmp_path):
    request = request_from_packet(tmp_path, returncode=7)
    manifest = run_request(tmp_path, request)
    assert manifest["status"] == "partial", load(request, "diagnostics.json")
    assert request["bundle"]["process"]["returncode"] == 7
    assert load(request, "sheets.json")["native_convergence"]["extraction"]["status"] == "partial"
    assert convergence(request)[0]["booleans"][0]["value"] is True
    assert manifest["failures"]


def test_multiple_queries_never_call_extractor_and_omit_artifact(tmp_path, monkeypatch):
    request = request_from_packet(tmp_path, query=b">q\nACDEFGHI\n>r\nACDEFGHI\n")
    monkeypatch.setattr(extractor, "extract_blast_tabular7_convergence", forbidden)
    manifest = run_request(tmp_path, request)
    assert manifest["status"] != "failed", load(request, "diagnostics.json")
    binding = load(request, "sheets.json")["native_convergence"]
    assert binding["invocation"] == "not_invoked" and binding["query_binding"]["status"] == "multiple"
    assert "native_convergence" not in {r["role"] for r in manifest["artifacts"]}
    assert convergence(request) == []


def test_v2_recalculation_copies_exact_extraction_without_interpretation(tmp_path, monkeypatch):
    request = request_from_packet(tmp_path, raw=report(suffix=MARKER + b"\n" + MARKER + b"\n"))
    first = run_request(tmp_path, request)
    assert first["status"] != "failed", load(request, "diagnostics.json")
    new = reuse_request(request, first)
    no_interpretation(monkeypatch)
    second = run_request(tmp_path, new, "recalculate.json")
    assert second["status"] != "failed", load(new, "diagnostics.json")
    assert second["version"] == first["version"]
    assert second["input_interpretation_id"] == first["input_interpretation_id"]
    assert second["calculation_id"] != first["calculation_id"]
    for filename in ("sheets.json", "collection.json", "native-convergence.json"):
        assert (Path(new["output_directory"]) / filename).read_bytes() == (Path(request["output_directory"]) / filename).read_bytes()
    assert [{k:v for k,v in r.items() if k != "calculation_id"} for r in convergence(request)] == [
        {k:v for k,v in r.items() if k != "calculation_id"} for r in convergence(new)]


@pytest.mark.parametrize("mutation", ["missing", "changed", "unlisted", "wrong_filename", "wrong_schema"])
def test_reuse_changed_native_artifact_fails_without_reinterpreting(tmp_path, monkeypatch, mutation):
    request = request_from_packet(tmp_path)
    first = run_request(tmp_path, request)
    assert first["status"] != "failed", load(request, "diagnostics.json")
    copied = tmp_path / "mutated-generation"
    shutil.copytree(request["output_directory"], copied)
    changed = deepcopy(request); changed["output_directory"] = str(copied)
    path = copied / "native-convergence.json"
    if mutation == "missing":
        path.unlink()
    elif mutation == "changed":
        path.write_bytes(path.read_bytes() + b" ")
    else:
        altered = deepcopy(first)
        entry = next(r for r in altered["artifacts"] if r["role"] == "native_convergence")
        if mutation == "unlisted":
            altered["artifacts"].remove(entry)
        elif mutation == "wrong_filename":
            entry["relative_path"] = "collection.json"
        else:
            entry["schema"] = "blast_report_collection_v1"
        (copied / "worker-manifest.json").write_bytes(worker._json_bytes(altered))
    new = reuse_request(changed, first)
    no_interpretation(monkeypatch)
    failed = run_request(tmp_path, new, "bad-reuse.json")
    assert failed["status"] == "failed"
    assert not (Path(new["output_directory"]) / "sheets.json").exists()


@pytest.mark.parametrize("program", views._PROGRAMS)
def test_retained_legacy_v1_recalculation_preserves_original_interpretation(tmp_path, monkeypatch, program):
    entry = next(r for r in json.loads((PACKET / "LEGACY_GENERATIONS_001.json").read_bytes()) if r["program"] == program)
    for row in entry["files"]:
        raw = (ROOT / row["path"]).read_bytes()
        assert len(raw) == row["size_bytes"] and hashlib.sha256(raw).hexdigest() == row["sha256"]
    original = json.loads((ROOT / entry["request"]).read_bytes())
    manifest = load(original, "worker-manifest.json")
    new = reuse_request(original, manifest)
    new["output_directory"] = str(tmp_path / "legacy-recalculation")
    new["implementation"] = implementation(execution_program=program)
    new["calculation_id"] = worker.native_blast_database_calculation_identity(
        input_identity=worker.native_blast_database_input_identity(new), input_implementation_sha256=manifest["input_implementation_sha256"],
        sequence_model=new["sequence_model"], implementation_manifest_sha256=new["implementation"]["manifest_sha256"])["calculation_id"]
    no_interpretation(monkeypatch)
    result = run_request(tmp_path, new)
    assert result["status"] != "failed", load(new, "diagnostics.json")
    assert result["version"] == "native_blast_database_result_worker_manifest_v1"
    assert result["input_interpretation_id"] == manifest["input_interpretation_id"]
    assert (Path(new["output_directory"]) / "sheets.json").read_bytes() == (Path(original["output_directory"]) / "sheets.json").read_bytes()
    assert "native_convergence" not in {r["role"] for r in result["artifacts"]}
    for row in entry["files"]:
        assert hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest() == row["sha256"]


def test_native_fact_schemas_are_exact_previous_descriptors():
    assert views.native_blast_database_fact_sources() == json.loads((PACKET / "FACT_SCHEMAS_BEFORE_001.json").read_bytes())


def test_partial_tail_does_not_create_a_convergence_record(tmp_path):
    request = request_from_packet(tmp_path, raw=report(suffix=MARKER + b"\nSearch has CONVER"))
    manifest = run_request(tmp_path, request)
    assert manifest["status"] != "failed", load(request, "diagnostics.json")
    extraction = load(request, "native-convergence.json")
    assert len(extraction["markers"]) == 2 and len(extraction["convergence_records"]) == 1
    row, = convergence(request)
    assert row["identity"]["record_source"]["pointer"] == "/convergence_records/0"
    assert dict(artifact_role="sheets", pointer="/native_convergence/extraction/markers/0") in row["component_refs"]
    assert extraction["markers"][1]["record_key"] not in {r["record_key"] for r in extraction["convergence_records"]}
    assert row["booleans"][0]["value"] is True


def test_worker_artifact_bytes_stable_across_hash_seeds(tmp_path, monkeypatch):
    request = request_from_packet(tmp_path, raw=report(suffix=MARKER + b"\n" + MARKER + b"\r\n"))
    expected = None
    for seed in ("1", "2", "91"):
        monkeypatch.setenv("PYTHONHASHSEED", seed)
        selected = deepcopy(request); selected["output_directory"] = str(tmp_path / ("seed-" + seed))
        manifest = run_request(tmp_path, selected, "request-" + seed + ".json", cli=True)
        actual = {row["role"]: (Path(selected["output_directory"]) / row["relative_path"]).read_bytes()
            for row in manifest["artifacts"]}
        if expected is None:
            expected = actual
        else:
            assert actual == expected


@pytest.mark.parametrize("scope", ["query", "search"])
def test_supplied_record_does_not_renumber_native_source_and_conflict_is_preserved(tmp_path, scope):
    from tests.test_native_blast_database_convergence_binding import make_case, populate, bind
    from tests.test_native_blast_database_metadata import empty_payload, source, metadata as metadata_input
    args, prepared = make_case(tmp_path)
    binding = bind(args)
    baseline = populate(args, prepared, binding)
    baseline_calcs = worker.calculate_native_blast_database_sheets(baseline, sequence_model=None)
    baseline_rows = worker.build_native_blast_database_rows(bundle_identity=args["bundle"]["identity"],
        calculation_id="a" * 64, sheet_set=baseline, calculations=baseline_calcs)
    original, = [r for r in baseline_rows if r["family"] == "iteration_convergence"]
    catalog = args["artifact_catalog"]
    document = source(tmp_path, catalog, "supplied-record", b'{"record": {"native_converged": false}}')
    payload = empty_payload("iteration"); payload["documents"] = [document]
    key = args["collection"]["searches"][0]["search_key"]
    address = dict(output_key=next(r["output_key"] for r in args["original_job"]["outputs"] if r["role"] == "primary_report"),
        **{k:key[k] for k in ("member_ordinal", "report_index", "search_pointer")})
    payload["convergence_records"] = [dict(record_key="supplied-zero", search_key=address if scope == "search" else None,
        query_operand=None if scope == "search" else args["collection"]["invocation"]["operands"][0], native_converged=False,
        evidence=dict(origin="supplied_source_record", source=dict(source_ref=document["document_key"], pointer="/record"),
            source_format="explicit329", original_record={"native_converged": False}, extractor=None))]
    supplied = metadata_input(tmp_path, catalog, "iteration", payload)
    prepared = metadata.prepare_native_blast_database_inputs(job=args["original_job"], bundle=args["bundle"],
        artifact_catalog=catalog, metadata_payloads=[supplied], subject_snapshots=[])
    assert bind(args) == binding
    sheets = populate(args, prepared, binding)
    calculated = worker.calculate_native_blast_database_sheets(sheets, sequence_model=None)
    result = worker.build_native_blast_database_rows(bundle_identity=args["bundle"]["identity"],
        calculation_id="b" * 64, sheet_set=sheets, calculations=calculated)
    supplied_row, native_row = [r for r in result if r["family"] == "iteration_convergence"]
    assert native_row["record_key"] == original["record_key"]
    assert native_row["identity"]["record_source"] == original["identity"]["record_source"]
    assert native_row["component_refs"][0]["pointer"] == "/iteration/convergence_observations/1"
    assert native_row["component_refs"][1]["pointer"] == "/native_convergence/extraction/convergence_records/0"
    assert supplied_row["identity"]["record_source"] == sheets["iteration"]["convergence_records"][0]["evidence"]["source"]
    assert [r["booleans"][0]["value"] for r in (supplied_row, native_row)] == ([None, None] if scope == "query" else [False, True])
    if scope == "query":
        assert all(r["booleans"][0]["status"] == "incompatible" for r in (supplied_row, native_row))


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "changed_operand", "unbound_forgery"])
def test_native_observation_requires_exact_original_record_mapping(tmp_path, mutation):
    request = request_from_packet(tmp_path)
    manifest = run_request(tmp_path, request)
    assert manifest["status"] != "failed", load(request, "diagnostics.json")
    sheets, calculated = load(request, "sheets.json"), load(request, "calculations.json")
    observations = calculated["iteration"]["convergence_observations"]
    if mutation == "missing":
        observations.clear()
    elif mutation == "duplicate":
        observations.append(deepcopy(observations[0]))
    elif mutation == "changed_operand":
        observations[0]["query_operand"]["record_ordinal"] = 1
    else:
        observations[0]["record_key"] = "unbound-forged-record"
    with pytest.raises(ValueError, match="convergence_record_mapping_invalid"):
        worker.build_native_blast_database_rows(bundle_identity=request["bundle"]["identity"],
            calculation_id=request["calculation_id"], sheet_set=sheets, calculations=calculated)
