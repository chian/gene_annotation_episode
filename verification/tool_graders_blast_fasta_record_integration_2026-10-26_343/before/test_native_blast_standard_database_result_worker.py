"""R333 synthetic actual-file worker tests; no native executable is invoked."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode import native_blast_standard_database_result_worker as w
from gene_annotation_episode import native_blast_standard_database_metadata as m
from gene_annotation_episode import native_blast_standard_database_result_views as v
from test_native_blast_standard_database_calculators import cell, family, fixture, numerical
from test_native_blast_standard_database_metadata import encoded, subject, pssm, report, hit, hsp


def sha(raw): return hashlib.sha256(raw).hexdigest()


def implementation():
    files = [dict(module=name, path=str(Path(module.__file__).resolve()), sha256=sha(Path(module.__file__).read_bytes()))
        for name, module in w._implementation_modules().items()]
    return dict(files=files, manifest_sha256=w.standard_blast_database_implementation_identity(files))


def request_for(tmp_path, *, inputs=None, model=None):
    inputs = numerical() if inputs is None else inputs
    root = tmp_path / "original"; root.mkdir(parents=True)
    artifacts, retained, snapshots = [], [], []
    for i, row in enumerate(inputs["artifact_catalog"]["entries"]):
        path = root / f"captured-{i}"; raw = inputs["contents"][row["artifact_ref"]]; path.write_bytes(raw)
        artifacts.append(dict(artifact_key=row["artifact_key"], path=str(path), **{k: row[k] for k in w._FILE_ID}))
    for i, row in enumerate(inputs["artifact_catalog"]["retained_sources"]):
        path = root / f"retained-{i}"; path.write_bytes(inputs["contents"][row["artifact_ref"]])
        retained.append(dict(row, path=str(path)))
    for i, row in enumerate(inputs["subject_snapshots"]):
        path = root / f"subject-{i}"; path.write_bytes(inputs["subject_contents"][row["sequence_artifact_ref"]])
        snapshots.append(dict(row, record_type="input", sequence_path=str(path)))
    # Deliberately pretty serialized; bundle identity is captured bytes, not a
    # hash of a different canonical serialization inside the preparer.
    raw = json.dumps(inputs["bundle"], indent=2).encode(); path = root / "bundle.json"; path.write_bytes(raw)
    request = dict(version=v.PREFIX + "result_worker_request_v1", calculation_id="a" * 64, bundle=inputs["bundle"],
        bundle_artifact_ref="artifact-bundle", bundle_capture=dict(path=str(path), sha256=sha(raw), size_bytes=len(raw)),
        authenticated_attempt=inputs["attempt_identity"], artifacts=artifacts,
        metadata_descriptors=[r["descriptor"] for r in inputs["metadata_payloads"]], retained_sources=retained,
        subject_snapshots=snapshots, implementation=implementation(), sequence_model=model,
        output_directory=str(tmp_path / "generation-1"), reuse=None)
    set_identity(request)
    return request


def set_identity(request, input_impl=None):
    ids = w.standard_blast_database_calculation_identity(input_identity=w.standard_blast_database_input_identity(request),
        input_implementation_sha256=input_impl or request["implementation"]["manifest_sha256"], sequence_model=request["sequence_model"],
        implementation_manifest_sha256=request["implementation"]["manifest_sha256"])
    request["calculation_id"] = ids["calculation_id"]


def invoke(request):
    path = Path(request["output_directory"]).with_suffix(".request.json")
    path.write_bytes(encoded(request))
    result = w.run_standard_blast_database_result_worker(str(path))
    diagnostics = json.loads((Path(request["output_directory"]) / "diagnostics.json").read_bytes())
    return result, diagnostics


def saved_rows(request):
    return [json.loads(line) for line in (Path(request["output_directory"]) / "rows.ndjson").read_bytes().splitlines()]


def reuse(request, manifest, output):
    request = deepcopy(request); directory = Path(request["output_directory"])
    raw = (directory / "worker-manifest.json").read_bytes()
    request["reuse"] = dict(manifest_path=str(directory / "worker-manifest.json"), manifest_sha256=sha(raw), manifest_size_bytes=len(raw),
        collection_path=str(directory / "collection.json"), sheets_path=str(directory / "sheets.json"))
    request["output_directory"] = str(output); request["sequence_model"] = {"temperature_bits": 2}
    set_identity(request, manifest["input_implementation_sha256"])
    return request


def test_R7_complete_artifacts_exact_hashes_bytes_and_row_offsets(tmp_path):
    request = request_for(tmp_path)
    manifest, diagnostics = invoke(request)
    assert manifest["status"] != "failed", diagnostics
    assert set(r["role"] for r in manifest["artifacts"]) == set(w._ROLES)
    directory = Path(request["output_directory"])
    for record in manifest["artifacts"]:
        raw = (directory / record["relative_path"]).read_bytes()
        assert sha(raw) == record["sha256"] and len(raw) == record["size_bytes"]
    raw = (directory / "rows.ndjson").read_bytes()
    index = json.loads((directory / "row-index.json").read_bytes())
    for ordinal, entry in enumerate(index["rows"]):
        row = json.loads(raw[entry["byte_start"]:entry["byte_end"]])
        assert row["record_key"] == entry["record_key"] and entry["ordinal"] == ordinal
    rows = saved_rows(request)
    assert manifest["counts"] == dict(searches=1, native_hsp_slots=2, numerical_rows=len(rows))
    assert [cell(r, "unadjusted_probability")["value"] for r in family(rows, "sequence_function")] == pytest.approx([.8, .2])
    before = {p.name: p.read_bytes() for p in directory.iterdir()}
    with pytest.raises(FileExistsError): invoke(request)
    assert before == {p.name: p.read_bytes() for p in directory.iterdir()}


def test_R8_R9_saved_recalculation_has_no_parsing_population_or_acquisition(tmp_path, monkeypatch):
    inputs = numerical(); subject(inputs, "ACDEFGHI")
    request = request_for(tmp_path, inputs=inputs)
    manifest, diagnostics = invoke(request)
    assert manifest["status"] == "complete", diagnostics
    before = {p.name: p.read_bytes() for p in Path(request["output_directory"]).iterdir()}
    revised = reuse(request, manifest, tmp_path / "generation-2")
    def forbidden(*a, **kw): raise AssertionError("saved reuse called population/parsing")
    for name in ("prepare_standard_blast_database_inputs", "populate_standard_blast_database_sheets", "derive_standard_blast_database_search_binding",
            "qualify_standard_blast_sequence_metadata", "validate_native_blast_database_metadata_payload", "read_blast_pssm", "extract_blast_pssm_master_metadata", "populate_blast_sequence_database_sheet"):
        monkeypatch.setattr(m, name, forbidden)
    monkeypatch.setattr(w, "parse_blast_report_collection", forbidden)
    recalculated, diagnostics = invoke(revised)
    assert recalculated["status"] != "failed", diagnostics
    assert recalculated["input_identity"] == manifest["input_identity"]
    assert recalculated["input_interpretation_id"] == manifest["input_interpretation_id"]
    assert recalculated["calculation_id"] != manifest["calculation_id"]
    old_rows, new_rows = saved_rows(request), saved_rows(revised)
    assert [r["record_key"] for r in new_rows] == [r["record_key"] for r in old_rows]
    assert [cell(r, "unadjusted_probability")["value"] for r in family(new_rows, "sequence_function")] == pytest.approx([2 / 3, 1 / 3])
    assert before == {p.name: p.read_bytes() for p in Path(request["output_directory"]).iterdir()}


def test_R8_identity_recipes_keep_paths_and_parameters_separate(tmp_path):
    request = request_for(tmp_path); original = w.standard_blast_database_input_identity(request)
    changed = deepcopy(request); changed["sequence_model"] = {"temperature_bits": 2}; changed["output_directory"] += "-moved"
    for row in changed["artifacts"]: row["path"] += "-moved"
    assert w.standard_blast_database_input_identity(changed) == original
    changed["artifacts"].reverse()
    assert w.standard_blast_database_input_identity(changed) != original
    files = deepcopy(request["implementation"]["files"])
    for row in files: row["path"] += "-moved"
    assert w.standard_blast_database_implementation_identity(list(reversed(files))) == request["implementation"]["manifest_sha256"]
    first = w.standard_blast_database_calculation_identity(input_identity=original, input_implementation_sha256="a" * 64, sequence_model=None, implementation_manifest_sha256="b" * 64)
    second = w.standard_blast_database_calculation_identity(input_identity=original, input_implementation_sha256="a" * 64, sequence_model=None, implementation_manifest_sha256="c" * 64)
    assert first["input_interpretation_id"] == second["input_interpretation_id"] and first["calculation_id"] != second["calculation_id"]


@pytest.mark.parametrize("change", ["missing_report", "malformed_metadata", "tampered_capture", "wrong_attempt", "implementation"])
def test_R7_specific_failures_keep_complete_diagnostics(tmp_path, change):
    request = request_for(tmp_path)
    if change == "missing_report":
        Path(next(r["path"] for r in request["artifacts"] if r["artifact_key"] == "report")).unlink()
    if change == "malformed_metadata":
        descriptor = request["metadata_descriptors"][0]
        row = next(r for r in request["retained_sources"] if r["artifact_ref"] == descriptor["artifact_ref"])
        raw = b"{bad-json"; Path(row["path"]).write_bytes(raw)
        row.update(sha256=sha(raw), size_bytes=len(raw)); descriptor.update(sha256=sha(raw), size_bytes=len(raw)); set_identity(request)
    if change == "tampered_capture": Path(request["bundle_capture"]["path"]).write_bytes(b"changed")
    if change == "wrong_attempt": request["authenticated_attempt"]["identity"]["execution_id"] = "wrong-execution"
    if change == "implementation": request["implementation"]["files"][0]["sha256"] = "0" * 64
    manifest, diagnostics = invoke(request)
    assert manifest["status"] in {"partial", "failed"}
    assert manifest["failures"] and diagnostics["failures"] == manifest["failures"]
    assert all(set(f) == set(v.FAILURE_SCHEMA["properties"]) for f in manifest["failures"])
    if change in {"missing_report", "malformed_metadata"}:
        expected = "artifact_missing" if change == "missing_report" else "metadata_payload_invalid"
        assert any(f["code"] == v.PREFIX + expected for f in manifest["failures"])
    if change == "malformed_metadata":
        assert manifest["status"] != "failed", diagnostics
        assert [cell(r, "native_score_bits")["value"] for r in family(saved_rows(request), "hsp")] == [20, 18]


def test_R8_changed_original_bytes_prevent_saved_recalculation(tmp_path):
    request = request_for(tmp_path); manifest, diagnostics = invoke(request)
    assert manifest["status"] != "failed", diagnostics
    revised = reuse(request, manifest, tmp_path / "generation-2")
    report_path = next(r["path"] for r in revised["artifacts"] if r["artifact_key"] == "report")
    Path(report_path).write_bytes(b"tampered")
    rejected, _ = invoke(revised)
    assert rejected["status"] == "failed"
    assert any(f["code"] == v.PREFIX + "frozen_artifact_changed" for f in rejected["failures"])
    assert not (Path(revised["output_directory"]) / "rows.ndjson").exists()


def test_R2_search_exception_text_only_in_diagnostics(tmp_path):
    request = request_for(tmp_path, model={"function_priors": {"other": 1}})
    manifest, diagnostics = invoke(request)
    assert manifest["status"] == "partial", diagnostics
    assert diagnostics["exceptions"]
    calculations = json.loads((Path(request["output_directory"]) / "calculations.json").read_bytes())
    assert calculations["sequence"][0]["components"] is None
    assert any(f["code"] == v.PREFIX + "calculation_failed" for f in manifest["failures"])
    assert all("message" not in f for f in manifest["failures"])
    assert len(family(saved_rows(request), "hsp")) == 2


@pytest.mark.parametrize("kind", ["memory", "scratch"])
def test_R10_resource_failure_keeps_prior_sealed_artifacts_and_diagnostics(tmp_path, monkeypatch, kind):
    request = request_for(tmp_path)
    if kind == "memory":
        def failed(*a, **kw): raise MemoryError("synthetic allocated-memory failure")
        monkeypatch.setattr(w.calculators, "_calculate", failed)
    else:
        original = w._atomic_bytes
        def failed(directory, filename, raw):
            if filename == "calculations.json": raise OSError(28, "synthetic scratch exhausted")
            return original(directory, filename, raw)
        monkeypatch.setattr(w, "_atomic_bytes", failed)
    manifest, diagnostics = invoke(request)
    assert manifest["status"] == "failed"
    assert manifest["failures"][-1]["code"] == v.PREFIX + "worker_resource_limit"
    assert manifest["failures"][-1]["detail_code"] == "resource_limit"
    assert diagnostics["exceptions"][-1]["failure_index"] == len(manifest["failures"]) - 1
    assert {"inputs", "collection", "sheets", "diagnostics"} <= {r["role"] for r in manifest["artifacts"]}
    assert not (Path(request["output_directory"]) / "rows.ndjson").exists()


def test_R10_nonzero_native_exit_does_not_erase_valid_measurements(tmp_path):
    inputs = fixture()
    inputs["bundle"]["process"]["returncode"] = 2
    inputs["bundle"]["failures"].append(dict(code="native_nonzero_exit", input_key=None, database_key=None,
        output_key=None, artifact_key=None, native_returncode=2))
    request = request_for(tmp_path, inputs=inputs)
    manifest, diagnostics = invoke(request)
    assert manifest["status"] == "partial", diagnostics
    assert any(r["code"] == v.PREFIX + "capture_incomplete" for r in manifest["failures"])
    assert [cell(r, "native_score_bits")["value"] for r in family(saved_rows(request), "hsp")] == [20, 18]


def test_R10_invalid_model_fails_explicit_request_before_population(tmp_path, monkeypatch):
    request = request_for(tmp_path); request["sequence_model"] = {"temperature_bits": 0}
    path = tmp_path / "bad.request.json"; path.write_bytes(encoded(request))
    def forbidden(*a, **kw): raise AssertionError("invalid model reached population")
    monkeypatch.setattr(m, "prepare_standard_blast_database_inputs", forbidden)
    with pytest.raises(ValueError, match="sequence_model_invalid"):
        w.run_standard_blast_database_result_worker(str(path))
    assert not Path(request["output_directory"]).exists()


@pytest.mark.parametrize("artifact", ["sheets.json", "row-index.json", "rows.ndjson"])
def test_R10_changed_saved_generation_rejected_before_recalculation(tmp_path, monkeypatch, artifact):
    request = request_for(tmp_path); manifest, diagnostics = invoke(request)
    assert manifest["status"] != "failed", diagnostics
    revised = reuse(request, manifest, tmp_path / "generation-2")
    path = Path(request["output_directory"]) / artifact; path.write_bytes(path.read_bytes() + b" ")
    def forbidden(*a, **kw): raise AssertionError("changed seal reached calculation")
    monkeypatch.setattr(w.calculators, "_calculate", forbidden)
    result, _ = invoke(revised)
    assert result["status"] == "failed"
    assert any(r["code"] == v.PREFIX + "frozen_artifact_changed" for r in result["failures"])


@pytest.mark.parametrize("format,raw,fields", [
    ("json15", b"{invalid", None),
    ("tabular7", b"# BLASTP 2.17.0+\n# Query: q\n# Database: target\n# 2 hits found\nq\ts\t20\nq\ts\n", ["qseqid", "sseqid", "bitscore"]),
])
def test_R10_malformed_native_source_preserves_diagnostics_and_valid_rows(tmp_path, format, raw, fields):
    inputs = fixture(doc=raw, fmt=format, fields=fields)
    subject(inputs, "ACDEFGHI")
    request = request_for(tmp_path, inputs=inputs)
    manifest, diagnostics = invoke(request)
    assert manifest["status"] == "partial", diagnostics
    assert any(r["code"] == v.PREFIX + "report_unreadable" for r in manifest["failures"])
    rows = saved_rows(request)
    if format == "tabular7":
        hsps = family(rows, "hsp")
        assert len(hsps) == 2
        assert cell(hsps[0], "native_score_bits")["value"] == 20
        assert cell(hsps[1], "native_score_bits")["value"] is None
    else: assert not rows


@pytest.mark.parametrize("program", v.PROGRAMS)
def test_R1_actual_worker_all_five_mode_units_and_geometry(tmp_path, program):
    query_width = 3 if program in {"blastx", "tblastx"} else 1
    reference_width = 3 if program in {"tblastn", "tblastx"} else 1
    native = hsp(qseq="AAAA", hseq="AAAA", query_to=4 * query_width, hit_to=4 * reference_width,
        **({"query_frame": 1} if query_width == 3 else {}), **({"hit_frame": 1} if reference_width == 3 else {}))
    inputs = fixture(program, query=b">q\n" + b"A" * (8 * query_width) + b"\n",
        doc=report(program, query_len=8 * query_width, hits=[hit(length=10 * reference_width, hsps=[native])]))
    subject(inputs, "A" * (8 * query_width), molecule="dna" if program in {"blastn", "blastx", "tblastx"} else "protein")
    request = request_for(tmp_path, inputs=inputs)
    manifest, diagnostics = invoke(request)
    assert manifest["status"] == "complete", diagnostics
    row = family(saved_rows(request), "hsp")[0]
    assert cell(row, "full_query_paired_coverage")["value"] == .5
    assert cell(row, "full_reference_paired_coverage")["value"] == .4
    assert tuple(row["context"][k] for k in ("query_unit", "reference_unit", "alignment_unit")) == v.UNITS[program]


def test_R1_actual_tblastn_pssm_worker_keeps_cells_and_saved_reuse(tmp_path, monkeypatch):
    inputs = fixture("tblastn", kind="pssm", query=pssm(), doc=report("psitblastn", query_len=3, hits=[]))
    subject(inputs, "ACD", kind="pssm")
    request = request_for(tmp_path, inputs=inputs)
    manifest, diagnostics = invoke(request)
    assert manifest["status"] == "complete", diagnostics
    rows = saved_rows(request)
    assert len(family(rows, "pssm_cell")) == 6
    assert [cell(r, "freqRatios")["value"] for r in family(rows, "pssm_cell")] == [0, 1, 2, 3, 4, 5]
    revised = reuse(request, manifest, tmp_path / "generation-2")
    def forbidden(*a, **kw): raise AssertionError("saved PSSM was reparsed")
    for name in ("read_blast_pssm", "extract_blast_pssm_master_metadata", "prepare_standard_blast_database_inputs", "populate_standard_blast_database_sheets"):
        monkeypatch.setattr(m, name, forbidden)
    monkeypatch.setattr(w, "parse_blast_report_collection", forbidden)
    result, diagnostics = invoke(revised)
    assert result["status"] == "complete", diagnostics
    assert [cell(r, "freqRatios") for r in family(saved_rows(revised), "pssm_cell")] == [cell(r, "freqRatios") for r in family(rows, "pssm_cell")]


def test_R10_pssm_calculator_exception_preserves_native_sequence_result(tmp_path, monkeypatch):
    native = hsp(qseq="ACD", hseq="ACD", query_to=3, hit_to=9, hit_frame=1, align_len=3, identity=3)
    inputs = fixture("tblastn", kind="pssm", query=pssm(), doc=report("psitblastn", query_len=3, hits=[hit(length=12, hsps=[native])]))
    subject(inputs, "ACD", kind="pssm")
    request = request_for(tmp_path, inputs=inputs)
    calls = []
    def failed(sheet):
        calls.append(sheet["artifact_key"])
        raise ValueError("injected original PSSM calculator exception")
    monkeypatch.setattr(w.calculators._pssm, "calculate_blast_pssm_components", failed)
    manifest, diagnostics = invoke(request)
    assert calls == ["query"]
    assert manifest["status"] == "partial", diagnostics
    calculations = json.loads((Path(request["output_directory"]) / "calculations.json").read_bytes())
    sheets = json.loads((Path(request["output_directory"]) / "sheets.json").read_bytes())
    assert calculations["pssm"] == [dict(artifact_key="query", components=None)]
    assert sheets["pssm"][0]["artifact_key"] == "query" and sheets["pssm"][0]["pssms"]
    assert calculations["sequence"][0]["components"]["schema"] == "blast_sequence_database_result_components_v1"
    failures = [(i, row) for i, row in enumerate(manifest["failures"]) if row["code"] == v.PREFIX + "calculation_failed"]
    assert len(failures) == 1 and failures[0][1]["artifact_key"] == "query"
    assert failures[0][1]["detail_code"] == "calculator_contract_invalid"
    assert any(row["failure_index"] == failures[0][0] and row["message"] == "injected original PSSM calculator exception" for row in diagnostics["exceptions"])
    assert "injected original" not in json.dumps(manifest)
    rows = saved_rows(request)
    assert not any(r["family"].startswith("pssm_") for r in rows)
    assert cell(family(rows, "hsp")[0], "native_score_bits")["value"] == 20
    assert cell(family(rows, "hsp")[0], "qualified_paired_reference_units")["value"] == 9
    assert family(rows, "sequence_hit")
