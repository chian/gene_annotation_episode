"""Selected converter jobs through the existing masking episode/result path.

Native execution and deterministic result workers are real. Episode choices and
scientific horizons are fixtures. These checks do not establish model decisions,
remote deployment, binary semantic decoding or biological annotation.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_blast_masking_result_publication import (
    publish_selected_masking_result, validate_prepared_masking_result,
)
from test_native_blast_masking_workflow import (
    POLICY, nested_case,
    test_selected_contracts_grants_and_practical_accounting as check_accounting,
    test_closed_native_result_and_received_forms_replay_without_work as check_replay,
)


ROOT = Path(__file__).resolve().parents[1]
CASES = {
    "dna_xml": {
        "molecule": "dna", "format": "maskinfo_xml", "algorithm": "dust",
        "fasta": ">lcl|mask_a\nAAaaNNttRRYy\n>lcl|upper_a\nACGTNNRY\n"
                 ">ref|NM_999999999.7|\nnnACgtNN\n>gnl|fixture641|mask_general\nACgtNNrY\n"
                 ">duplicate\nAAaaGG\n>duplicate\nttCCaa\n",
        "lengths": [12, 8, 8, 8, 6, 6], "masked": [5, 0, 4, 3, 2, 4],
        "native_intervals": [3, None, 2, 2, 1, 2],
    },
    "protein_text": {
        "molecule": "protein", "format": "maskinfo_asn1_text", "algorithm": "seg",
        "fasta": ">protein_a\nMKWVtfISLLflFSSaysR\n",
        "lengths": [19], "masked": [7], "native_intervals": [3],
    },
    "dna_interval": {
        "molecule": "dna", "format": "interval", "algorithm": "other",
        "fasta": ">single_a\nAAaaNNtt\n",
        "lengths": [8], "masked": [4], "native_intervals": [2],
    },
}


def converter_job(directory, specification):
    directory.mkdir(parents=True)
    source = directory / "original.fa"
    source.write_text(specification["fasta"])
    data = source.read_bytes()
    binary = ROOT / "resources/software/ncbi-blast-2.17.0+/bin/convert2blastmask"
    assert binary.is_file(), "runner must stage the selected converter executable"
    operation = {
        "version": "sequence_masking_operation_v1", "program": "convert2blastmask",
        "mode": "convert_mask", "engine_version": "BLAST 2.17.0+", "input_format": "fasta",
        "input_mask_basis": "lowercase_input", "molecule": specification["molecule"],
        "output_format": specification["format"], "masking_style": "interval", "parse_seqids": True,
        "requested_parameters": {"masking_algorithm": specification["algorithm"],
            "masking_options": "supplied lowercase; no detector run; workflow fixture 641"},
    }
    return {
        "version": "native_blast_masking_job_v1", "operation": operation,
        "software": {"executable": str(binary), "sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
            "engine_version": operation["engine_version"]},
        "environment": {"LC_ALL": "C"}, "operand_bindings": [], "statistics_binding": None,
        "operands": [{"role": "sequences", "ordinal": 0, "path": str(source), "format": "fasta",
            "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data), "artifact_ref": None}],
        "outputs": [{"role": "mask", "format": specification["format"], "relative_path": "mask.out"},
            {"role": "stdout", "format": "text", "relative_path": "stdout.txt"},
            {"role": "stderr", "format": "text", "relative_path": "stderr.txt"}],
    }


@pytest.fixture(scope="module", params=list(CASES))
def conversion_case(tmp_path_factory, request):
    specification = CASES[request.param]
    directory = tmp_path_factory.mktemp("conversion641-" + request.param)
    job = converter_job(directory / "supplied", specification)
    selector = {
        "version": "native_blast_masking_result_selector_v1", "mode": "native_result",
        "records": {"mode": "all"}, "quantities": ["input_length", "native_interval_count",
            "masked_positions", "masked_fraction"], "statistics_fields": [], "statistics_unit_codes": [],
        "include_checks": True, "artifacts": [{"direction": "output", "role": "mask", "ordinal": 0}],
        "saved_data": ["sheet", "calculations"], "saved_sheet_ref": None,
    }
    case = nested_case(directory, "convert2blastmask", "convert_mask", supplied_job=job,
        result_selector=selector, subject_sequence=specification["fasta"].splitlines()[1],
        subject_molecule=specification["molecule"])
    case.specification = specification
    yield case
    case.store.close()


def test_actual_converter_values_reach_both_parents_from_one_shared_sheet(conversion_case):
    case, specification = conversion_case, conversion_case.specification
    body = case.outcome["result"]
    assert case.returned["completed"] and body["complete"], body["failures"]
    assert body["status"]["native_state"] == "succeeded"
    assert case.forwarded == {k: case.returned[k] for k in ("status", "quantities", "statistics")}
    bundle = json.loads(case.store.get_artifact(body["capture"]["bundle_artifact_ref"]))
    sheet = json.loads(case.store.get_artifact(body["prepared"]["sheet_artifact_ref"]))
    calculated = json.loads(case.store.get_artifact(body["prepared"]["calculations_artifact_ref"]))
    assert bundle["requested_job"] == case.request and bundle["returncode"] == 0
    assert sheet["version"] == "sequence_masking_sheet_v1" and sheet["operation"] == bundle["operation"]
    assert sheet["parsed_output"]["native_maskinfo"]["native_format"] == specification["format"]
    rows = calculated["records"]
    assert [r["input_length"]["value"] for r in rows] == specification["lengths"]
    assert [r["masked_positions"]["value"] for r in rows] == specification["masked"]
    assert [r["native_interval_count"]["value"] for r in rows] == specification["native_intervals"]
    expected_unit = "aa" if specification["molecule"] == "protein" else "nt"
    assert all(r["masked_positions"]["unit"] == expected_unit for r in rows)
    assert [r["masked_fraction"]["value"] for r in rows] == [
        count / length for count, length in zip(specification["masked"], specification["lengths"])]
    by_key = {r["record_key"]: r for r in rows}
    assert all(r["value"] == by_key[r["record_key"]][r["quantity"]] for r in case.returned["quantities"])
    for row, native_count in zip(rows, specification["native_intervals"]):
        if native_count is None:
            assert row["native_interval_count"]["missing_reason"] == "native_mask_record_not_emitted"
            assert row["record_key"] in {r["input_record_key"] for r in sheet["parsed_output"]["known_zero_records"]}
            assert row["record_key"] not in {r["input_record_key"] for r in sheet["parsed_output"]["records"]}
    case.owner.validate_report(case.results_context, case.returned, case.results_form)
    case.owner.validate_received_report(case.root_context, case.forwarded, case.science_form)
    descriptor = case.owner.job_progress_provider.targets.describe_target(case.provider.handoff, case.scope)
    extractor, = [r for r in descriptor["extractors"] if r["operation"] == "execution.results.collect"]
    assert extractor["sheet_population"].endswith("blast_maskinfo_inputs.populate_mask_conversion")
    assert extractor["calculators"] == ["gene_annotation_episode.sequence_masking_calculations.calculate_sequence_masking_components"]
    assert case.store.count("annotation") == case.store.count("observation") == 0


def test_converter_uses_existing_contract_grants_and_practical_accounting(conversion_case):
    check_accounting(conversion_case)


def test_converter_saved_recalculation_and_closed_replay_need_no_original_inputs(conversion_case, monkeypatch):
    case, body = conversion_case, conversion_case.outcome["result"]
    # Move the original directories out of reach first. The existing replay
    # helper later removes empty replacements and checks unchanged Store state.
    shutil.rmtree(case.workspace)
    shutil.rmtree(case.directory / "supplied")

    def forbidden(*args, **kwargs):
        raise AssertionError("saved conversion result attempted native parsing or acquisition")

    monkeypatch.setattr("gene_annotation_episode.blast_maskinfo_inputs.parse_blast_maskinfo", forbidden)
    monkeypatch.setattr("gene_annotation_episode.blast_maskinfo_inputs.populate_mask_conversion", forbidden)
    validate_prepared_masking_result(case.store, body["prepared"])
    selector = deepcopy(case.selector)
    selector.update(mode="saved_recalculation", saved_sheet_ref=body["prepared"]["sheet_artifact_ref"])
    recalculated = publish_selected_masking_result(case.store, source_ref=body["source_ref"],
        prepared=body["prepared"], selector=selector, directory=case.directory / "selected-recalculation",
        policy=LocalJobPolicy(**POLICY))
    assert recalculated["quantities"] == body["quantities"]
    assert recalculated["status"]["native_state"] == body["status"]["native_state"]
    (case.directory / "SAVED_RECALCULATION.json").write_text(json.dumps(recalculated, indent=2) + "\n")
    case.workspace.mkdir()
    (case.directory / "supplied").mkdir()
    check_replay(case, monkeypatch)
