"""Store-free engineering fixtures; Source-shaped strings convey no custody."""
from copy import deepcopy
import hashlib
import json

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode import somatic_variant_contracts as contracts
from gene_annotation_episode import somatic_variant_result_worker as worker
from gene_annotation_episode import vcf_result_measurements as vcf
from tests.test_somatic_variant_native import request_fixture


RAW = (b"##fileformat=VCFv4.2\n"
    b"##INFO=<ID=ANN,Number=.,Type=String,Description=\"literal annotation\">\n"
    b"#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
    b"chr1\t7\t.\tA\tG\t.\tPASS\tANN=G|missense_variant|MODERATE\n")


def _file(raw, format):
    sha = hashlib.sha256(raw).hexdigest()
    return {"artifact_ref": "artifact_" + sha, "sha256": sha, "size_bytes": len(raw), "format": format}


def _selection(stage="annotated"):
    return {"stage": stage, "vcf": {"version": vcf.SELECTION_VERSION,
        "record_ordinals": None, "sample_ordinals": None, "info_keys": None,
        "format_keys": None, "offset": 0, "limit": 10}}


def _context():
    request = request_fixture()
    manifest = {"version": contracts.NATIVE_MANIFEST_VERSION, "request": request,
        "directory": "/engineered/" + contracts.NATIVE_DIRECTORY,
        "input_staging": [{"role": row["role"], "state": "not_attempted", "observed": None}
            for row in request["inputs"]],
        "stages": [{"stage": stage, "state": "not_attempted", "returncode": None, "prerequisites": [],
            "started_at_utc": None, "ended_at_utc": None,
            "argv": contracts.somatic_native_argv(request, stage, directory="/engineered/" + contracts.NATIVE_DIRECTORY)}
            for stage in contracts.STAGES], "headers": [], "files": [], "issues": ["software_identity_conflict"]}
    return contracts.somatic_context_from_manifest(manifest)


def _parse_request(tmp_path):
    raw_path = tmp_path / "engineered.vcf"
    raw_path.write_bytes(RAW)
    context = _context()
    identity = _file(RAW, "vcf")
    # This is a leaf-input shape, not an application Source or native receipt.
    context["outputs"] = [{"role": stage, "sha256": identity["sha256"], "size_bytes": identity["size_bytes"]}
        for stage in contracts.STAGES]
    stage_inputs = [{"stage": stage, "input": {"path": str(raw_path), "file": identity,
        "source_ref": "source_" + str(index + 1) * 24,
        "capture": {"state": "complete", "byte_start_0based": 0,
            "byte_end_0based_exclusive": len(RAW), "original_size_bytes": len(RAW)}}}
        for index, stage in enumerate(contracts.STAGES)]
    return {"version": worker.REQUEST_VERSION, "mode": "parse", "stage_inputs": stage_inputs,
        "saved": None, "context": context, "selection": _selection()}


def _forbidden(*args, **kwargs):
    raise AssertionError("forbidden body/parser/calculator/native work")


def _arguments():
    return {"mode": "run_native", "inputs": [{"role": role, "namespace": "artifact",
        "reference": "artifact_" + str(index + 1) * 64, "max_bytes": 1024}
        for index, (role, _name, _format) in enumerate(contracts.INPUTS[:7])],
        "sample_ids": {"tumor": "tumor literal", "normal": "normal literal"},
        "reference_id": None, "annotation_database_id": "explicit.1", "selection": _selection()}


def test_public_arguments_preserve_order_literal_ids_and_no_saved_overrides():
    arguments = _arguments()
    checked = contracts.validate_somatic_arguments(arguments)
    assert checked == arguments and checked is not arguments
    schema = contracts.somatic_result_schema("Arguments")
    Draft202012Validator(schema).validate(arguments)
    saved = {"mode": "calculate_saved", "result_ref": "source_" + "a" * 24, "selection": _selection("raw")}
    assert contracts.validate_somatic_arguments(saved) == saved
    saved["sample_ids"] = arguments["sample_ids"]
    with pytest.raises(ValueError):
        contracts.validate_somatic_arguments(saved)


@pytest.mark.parametrize("change", [
    lambda a: a["inputs"].reverse(),
    lambda a: a["inputs"][0].update(max_bytes=True),
    lambda a: a["inputs"][0].update(reference="source_" + "a" * 24),
    lambda a: a["inputs"][0].update(path="/caller/path"),
    lambda a: a["sample_ids"].update(tumor="normal literal"),
    lambda a: a.update(annotation_database_id="../other"),
])
def test_public_arguments_reject_namespace_order_and_path_substitution(change):
    arguments = _arguments()
    change(arguments)
    with pytest.raises(ValueError):
        contracts.validate_somatic_arguments(arguments)


@pytest.mark.parametrize("kind", ["Arguments", "Context", "Selection", "Value", "Return"])
def test_exported_somatic_schema_is_complete_draft202012(kind):
    schema = contracts.somatic_result_schema(kind)
    Draft202012Validator.check_schema(schema)
    for definition in schema["$defs"].values():
        assert type(definition) is dict


def test_fact_schema_has_only_callable_top_source_semantics():
    schema = contracts.somatic_fact_sources()[contracts.FACT_SOURCE]["report_schema"]
    Draft202012Validator.check_schema(schema)
    assert schema["$id"] and schema["items"] == {"$ref": "#/$defs/SomaticReturn"}
    top = schema["$defs"]["SomaticReturn"]["properties"]["source_ref"]
    assert top["x-reference-namespace"] == "source" and top["format"] == "reference"
    nested = schema["$defs"]["SomaticContext"]["properties"]["inputs"]["items"]["properties"]
    assert "format" not in nested["source_ref"] and "x-reference-namespace" not in nested["source_ref"]
    assert "x-reference-namespace" not in schema["$defs"]["File"]["properties"]["artifact_ref"]


@pytest.mark.parametrize("change", [
    lambda c: c["annotation_database"].update(id="../other"),
    lambda c: c["annotation_database"]["files"][0].update(relative_path="."),
    lambda c: c["annotation_database"]["files"][0].update(relative_path="/absolute/predictor.bin"),
    lambda c: c["annotation_database"]["files"][0].update(relative_path="other/snpEffectPredictor.bin"),
    lambda c: c["annotation_database"]["files"].append(deepcopy(c["annotation_database"]["files"][0])),
])
def test_public_database_provenance_uses_same_native_selected_profile_grammar(change):
    context = _context()
    change(context)
    with pytest.raises(ValueError):
        contracts.validate_somatic_context(context)


def test_three_literal_stage_sheets_one_shared_calculator_and_no_annotation_rescoring(tmp_path, monkeypatch):
    request = _parse_request(tmp_path)
    original_parse, original_calc = vcf.parse_vcf_sheet, vcf.calculate_vcf_components
    calls = {"parse": 0, "calculate": 0}
    def parse(*args, **kwargs):
        calls["parse"] += 1
        return original_parse(*args, **kwargs)
    def calculate(*args, **kwargs):
        calls["calculate"] += 1
        return original_calc(*args, **kwargs)
    monkeypatch.setattr(vcf, "parse_vcf_sheet", parse)
    monkeypatch.setattr(vcf, "calculate_vcf_components", calculate)
    output_dir = tmp_path / "result"
    output_dir.mkdir()
    output = worker.run_somatic_variant_result(request, output_directory=output_dir)
    assert calls == {"parse": 3, "calculate": 1}
    components = json.loads((output_dir / "components.json").read_bytes())
    packet = json.loads((output_dir / "value.json").read_bytes())
    sheet = json.loads((output_dir / "annotated_sheet.json").read_bytes())
    assert components["sheet_sha256"] == vcf._hash(sheet)
    assert packet["value"] == components["value"]
    assert packet["value"]["records"][0]["info"][0]["values"][0]["token"]["raw_token"] == "G|missense_variant|MODERATE"
    assert packet["value"]["population"]["selected_record_slots"] == 1
    assert packet["context"]["stages"][0]["state"] == "not_attempted"  # no native proof is invented
    assert output["components"]["sha256"] == hashlib.sha256((output_dir / "components.json").read_bytes()).hexdigest()
    monkeypatch.setattr(vcf, "parse_vcf_sheet", _forbidden)
    monkeypatch.setattr(vcf, "calculate_vcf_components", _forbidden)
    returned = contracts.project_somatic_return(packet, "source_" + "a" * 24)
    assert returned["value"] == components["value"]
    partial = deepcopy(packet)
    partial["value"]["input"]["capture"]["state"] = "unknown"
    partial["value"]["input"]["original_file"] = None
    partial["value"]["population"].update(capture_state="unknown", record_population_complete=False,
        total_original_record_slots=None)
    assert contracts.validate_somatic_packet(partial) == partial
    missing_native = deepcopy(partial)
    missing_native["context"]["outputs"] = missing_native["context"]["outputs"][:2]
    with pytest.raises(ValueError, match="packet_capture_size_conflict"):
        contracts.validate_somatic_packet(missing_native)
    conflicting_size = deepcopy(partial)
    conflicting_size["value"]["input"]["capture"]["original_size_bytes"] += 1
    with pytest.raises(ValueError, match="packet_original_size_conflict"):
        contracts.validate_somatic_packet(conflicting_size)
    changed = deepcopy(returned)
    changed["value"]["population"]["selected_record_slots"] = True
    with pytest.raises(ValueError):
        contracts.validate_somatic_return(changed)


def test_saved_worker_reads_only_selected_sheet_and_calls_same_calculator_once(tmp_path, monkeypatch):
    request = _parse_request(tmp_path)
    item = request["stage_inputs"][2]["input"]
    sheet = vcf.parse_vcf_sheet({"input_id": item["source_ref"], "retained_file": item["file"],
        "original_file": item["file"], "source_ref": item["source_ref"], "content": RAW, "capture": item["capture"]})
    raw = json.dumps(sheet, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    path = tmp_path / "retained-sheet.json"
    path.write_bytes(raw)
    saved = {"version": worker.REQUEST_VERSION, "mode": "calculate_saved", "stage_inputs": None,
        "saved": {"stage": "annotated", "sheet": {"path": str(path), "file": _file(raw, vcf.SHEET_VERSION)}},
        "context": request["context"], "selection": _selection()}
    saved["selection"]["vcf"]["record_ordinals"] = []
    monkeypatch.setattr(vcf, "parse_vcf_sheet", _forbidden)
    original_read, original_calculate = worker.storage.read_bytes, vcf.calculate_vcf_components
    reads, calculations = [], []
    def read(selected):
        assert str(selected) == str(path)
        reads.append(str(selected))
        return original_read(selected)
    def calculate(*args, **kwargs):
        calculations.append(1)
        return original_calculate(*args, **kwargs)
    monkeypatch.setattr(worker.storage, "read_bytes", read)
    monkeypatch.setattr(vcf, "calculate_vcf_components", calculate)
    result = tmp_path / "saved"
    result.mkdir()
    output = worker.run_somatic_variant_result(saved, output_directory=result)
    assert reads == [str(path)] and calculations == [1]
    assert all(row["sheet"] is None for row in output["stage_sheets"])
    packet = json.loads((result / "value.json").read_bytes())
    assert packet["value"]["population"]["retained_record_slots"] == 1
    assert packet["value"]["population"]["selected_record_slots"] == 0
    assert packet["value"]["population"]["returned_record_fraction"]["value"] is None


def test_saved_sheet_must_join_native_stage_before_any_calculation(tmp_path, monkeypatch):
    request = _parse_request(tmp_path)
    item = request["stage_inputs"][2]["input"]
    sheet = vcf.parse_vcf_sheet({"input_id": item["source_ref"], "retained_file": item["file"],
        "original_file": item["file"], "source_ref": item["source_ref"], "content": RAW, "capture": item["capture"]})
    raw = json.dumps(sheet, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    path = tmp_path / "retained-sheet.json"
    path.write_bytes(raw)
    request["context"]["outputs"][2]["sha256"] = "0" * 64
    saved = {"version": worker.REQUEST_VERSION, "mode": "calculate_saved", "stage_inputs": None,
        "saved": {"stage": "annotated", "sheet": {"path": str(path), "file": _file(raw, vcf.SHEET_VERSION)}},
        "context": request["context"], "selection": _selection()}
    monkeypatch.setattr(vcf, "parse_vcf_sheet", _forbidden)
    monkeypatch.setattr(vcf, "calculate_vcf_components", _forbidden)
    result = tmp_path / "saved"
    result.mkdir()
    with pytest.raises(ValueError, match="packet_native_bytes_conflict"):
        worker.run_somatic_variant_result(saved, output_directory=result)
    assert not (result / "components.json").exists() and not (result / "value.json").exists()


@pytest.mark.parametrize("change", [
    lambda r: r["stage_inputs"].reverse(),
    lambda r: r["stage_inputs"][0]["input"]["file"].update(size_bytes=True),
    lambda r: r["stage_inputs"][0]["input"].update(source_ref=None),
    lambda r: r["stage_inputs"][0]["input"]["capture"].update(byte_end_0based_exclusive=0),
    lambda r: r["stage_inputs"][0]["input"]["capture"].update(state="unknown", original_size_bytes=len(RAW) + 1),
    lambda r: r["context"]["outputs"][0].update(sha256="0" * 64),
    lambda r: r["selection"]["vcf"].update(record_ordinals=[0, 0]),
])
def test_bad_stage_context_or_selection_is_rejected_before_body_or_science(tmp_path, monkeypatch, change):
    request = _parse_request(tmp_path)
    change(request)
    monkeypatch.setattr(worker.storage, "read_bytes", _forbidden)
    monkeypatch.setattr(vcf, "parse_vcf_sheet", _forbidden)
    monkeypatch.setattr(vcf, "calculate_vcf_components", _forbidden)
    with pytest.raises(ValueError):
        worker.run_somatic_variant_result(request, output_directory=tmp_path)
