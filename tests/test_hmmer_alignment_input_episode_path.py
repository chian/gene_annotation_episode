"""Declared alignment inputs through the existing real selected Workflow path.

Every input below is an authored engineering fixture, not an original native
emission. Scientific choices/controller are the existing scripted harness;
native execution, custody, shared grading, typed returns and replay are real.
Run only inside the root's bounded lifecycle, never as host scientific work.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import sys

import pytest

from gene_annotation_episode import hmmer_alignment_preparation_calculations as calculations
from gene_annotation_episode import native_hmmer_preparation_acquisition as acquisition
from gene_annotation_episode import native_hmmer_preparation_worker as worker
from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.numerical import NumericBand
from test_native_hmmer_preparation_contracts import job, operand
from gene_annotation_episode.native_hmmer_preparation_contracts import FORMAT_ARGUMENTS
from test_native_hmmer_preparation_workflow import (
    PREFIX, assert_accounting, assert_native_custody, assert_projected_values,
    choice_for, forbid_work, read_retained, run_case,
)


# These format-specific bytes encode the same three logical rows. The A2M
# short row has only two consensus residues; literal C--C would be invalid
# against AaaA. SELEX's two internal spaces occupy actual alignment columns.
# Clustal's final all-space line is its mandatory, empty consensus display.
# PHYLIP names occupy exactly ten bytes, including eight spaces after s0/s1/s2.
AUTHORED_INPUTS = {
    "afa": b">s0\nAAAA\n>s1\nAAAA\n>s2\nC--C\n",
    "a2m": b">s0\nAaaA\n>s1\nAaaA\n>s2\nCC\n",
    "psiblast": b"s0 AaaA\ns1 AaaA\ns2 C--C\n",
    "selex": b"s0 AAAA\ns1 AAAA\ns2 C  C\n",
    "clustal": b"CLUSTAL authored alignment\n\ns0 AAAA\ns1 AAAA\ns2 C--C\n       \n",
    "clustallike": b"AUTHORED alignment\n\ns0 AAAA\ns1 AAAA\ns2 C--C\n       \n",
    "phylip": b"3 4\ns0        AAAA\ns1        AAAA\ns2        C--C\n",
    "phylips": b"3 4\ns0        AAAA\ns1        AAAA\ns2        C--C\n",
}
AUTHORED_INFERRED_AFA = (
    b">s0\nACGTACGTACGT\n>s1\nACGTACGTACGT\n>s2\nC--CC--CC--C\n"
)
QUANTITIES = [
    "components.input_sequence_count",
    "components.input_column_count",
    "components.mapped_model_position_count",
    "components.native_mapping_row_count",
]
CHECKS = ["native_mapping", "requested_ranges"]
UNITS = ["sequence_count", "alignment_column_count", "model_position_count",
         "decoded_mapping_row_count"]


def _selected_case(tmp_path, declared_format, content, *, width, infer_alphabet=False):
    source = tmp_path / ("authored-selected." + declared_format)
    source.write_bytes(content)
    options = ([] if infer_alphabet else ["--dna"]) + [
        "--fast", "--wgsc", "--seed", "17", "--fragthresh", "0",
        "--symfrac", ".6", "--ali2model", "1-" + str(width),
    ]
    selected = job("alimask", "alignment_to_model", options)
    selected["operands"] = [operand("alignment", source, declared_format)]
    choice = choice_for(selected)
    choice["projection"]["quantities"] = list(QUANTITIES)
    choice["projection"]["checks"] = list(CHECKS)
    choice["artifacts"] = []
    case = run_case(
        tmp_path, "alimask", "alignment_to_model", job_override=selected,
        selectors=[choice], form_options={"artifacts": False, "population": False},
    )
    return source, choice, case


def _assert_numbers_and_return(case, choice, bundle, sheet, components, *,
                               declared_format, expected_rows, expected_map):
    assert sheet["schema"] == "hmmer_alignment_preparation_sheet_v1"
    source, = sheet["input_records"]
    assert source["format"] == declared_format
    assert [row["name"] for row in source["rows"]] == ["s0", "s1", "s2"]
    assert [row["aligned_sequence"] for row in source["rows"]] == expected_rows
    assert source["column_count"] == len(expected_rows[0])
    assert all(row["weight"] == {"value": None, "state": "missing", "events": []}
               for row in source["rows"])
    if declared_format in {"a2m", "psiblast"}:
        assert source["column_annotations"]["RF"]["text"] == "x..x"
        assert source["column_annotations"]["RF"]["valid"] is True

    row, = components["rows"]
    assert row["record_key"] == source["record_key"]
    reconstruction = row["reconstruction"]
    assert reconstruction["state"] == "present"
    assert reconstruction["map"] == expected_map
    assert reconstruction["weighting_trace"]["method"] == "wgsc"
    assert [item["weight"] for item in reconstruction["weights"]] == [.75, .75, 1.5]
    expected_values = [3, len(expected_rows[0]), len(expected_map), 1]
    for path, expected, unit in zip(QUANTITIES, expected_values, UNITS, strict=True):
        cell = row["components"][path.removeprefix("components.")]
        assert (cell["state"], cell["value"], cell["unit"]) == ("present", expected, unit)
        assert cell["inputs"]
    native_mapping, = row["native_mappings"]
    assert native_mapping["valid"] is True
    assert (native_mapping["returned_source_start"], native_mapping["returned_source_end"]) == (
        1, len(expected_rows[0]))
    assert (native_mapping["target_start"], native_mapping["target_end"]) == (1, len(expected_map))
    for code in CHECKS:
        checks = [item for item in components["checks"] if item["code"] == code]
        assert checks and all(item["state"] == "pass" for item in checks)
    context = source["map_reconstruction_context"]
    assert context["source_sha256"] == bundle["inputs"][0]["staged_sha256"]
    assert context["requested_cli_seed"] == context["resolved_cli_seed"] == 17

    form, = case.returned
    assert set(form) == {"completed", "rows"}
    assert form["completed"] is True
    returned_row, = form["rows"]
    assert [item["value"] for item in returned_row["quantities"]] == expected_values
    assert_projected_values(form, choice, components)


def _runtime_snapshot(case):
    # Include durable observations, histories and original forms, not only
    # in-memory copies of the already-closed child record.
    return {
        table: [tuple(row) for row in case.store.db.execute(
            "SELECT * FROM " + table + " ORDER BY rowid").fetchall()]
        for table in ("runtime_actions", "runtime_observations", "runtime_forms", "runtime_episodes")
    }


def _forbid_saved_work_aliases(guard, forbidden, *, calculations_forbidden=False):
    # Cover original functions and imports under aliases without depending on
    # the adapter's optional saved-field spelling. Histogram validation remains
    # allowed; scanning the original bytes or decoding rows does not.
    names = {
        "read_hmmer_alignment_input", "read_hmmer_alignment_output",
        "infer_hmmer_alignment_alphabet",
        "decode_native_fasta_alignment", "decode_native_block_alignment",
        "decode_native_phylip_alignment", "iter_hmmalign_stockholm_records",
    }
    if calculations_forbidden:
        names.update({"recalculate_hmmer_preparation", "reconstruct_alimask_model_map",
                      "calculate_hmmer_alignment_preparation_components"})
    for module_name, module in list(sys.modules.items()):
        if not module_name.startswith("gene_annotation_episode.") or module is None:
            continue
        for name, value in list(vars(module).items()):
            if callable(value) and getattr(value, "__name__", None) in names:
                guard.setattr(module, name, forbidden)


def _assert_saved_recalculation_and_closed_replay(case, source, monkeypatch, body,
                                                  sheet, components, parent, received):
    original_sheet = deepcopy(sheet)
    original_outcome = deepcopy(case.outcomes[0])
    original_form = deepcopy(case.returned[0])
    original_history = deepcopy(case.record.controller_state.history)
    original_runtime = _runtime_snapshot(case)
    retained_refs = [body["prepared"][name] for name in (
        "bundle_artifact_ref", "grading_artifact_ref", "sheet_artifact_ref", "calculations_artifact_ref")]
    retained_bytes = {ref: case.store.get_artifact(ref) for ref in retained_refs}
    attempt = Path(case.plan["attempt_directory"])
    unavailable_attempt = attempt.with_name("native-work-unavailable-for-saved-input-check")
    unavailable_source = source.with_name(source.name + ".unavailable")
    source.rename(unavailable_source)
    try:
        attempt.rename(unavailable_attempt)
        try:
            calls = []
            shared_calculator = calculations.calculate_hmmer_alignment_preparation_components

            def tracked_shared_calculator(saved, *, parameters=None):
                calls.append((deepcopy(saved), deepcopy(parameters)))
                return shared_calculator(saved, parameters=parameters)

            with monkeypatch.context() as guard:
                forbidden = forbid_work(guard)
                _forbid_saved_work_aliases(guard, forbidden)
                guard.setattr(native, "wait_job", forbidden)
                guard.setattr(acquisition, "_capture_file", forbidden)
                guard.setattr("builtins.open", forbidden)
                guard.setattr(Path, "open", forbidden)
                guard.setattr(calculations, "calculate_hmmer_alignment_preparation_components",
                              tracked_shared_calculator)
                recalculated = worker.recalculate_hmmer_preparation(
                    sheet, parameters=case.job["grading_parameters"])
                assert recalculated == components
                assert calls == [(sheet, case.job["grading_parameters"])]
            assert sheet == original_sheet
            assert _runtime_snapshot(case) == original_runtime

            original_socket = socket.socket
            with monkeypatch.context() as guard:
                forbidden = forbid_work(guard, calculations=True)
                _forbid_saved_work_aliases(guard, forbidden, calculations_forbidden=True)
                for target, name in (
                    (native, "wait_job"), (acquisition, "_capture_file"),
                    (calculations, "calculate_hmmer_alignment_preparation_components"),
                    (calculations, "reconstruct_alimask_model_map"),
                ):
                    guard.setattr(target, name, forbidden)

                def local_socket_only(*args, **kwargs):
                    family = args[0] if args else kwargs.get("family", socket.AF_INET)
                    if family != socket.AF_UNIX:
                        forbidden(*args, **kwargs)
                    return original_socket(*args, **kwargs)

                guard.setattr(socket, "socket", local_socket_only)
                replay = asyncio.run(case.owner.execute(
                    case.contexts[0], "execution.results.collect", {}, body["operation_key"]))
                assert replay == {key: value for key, value in original_outcome.items()
                                  if key != "pending_work_after_action"}
                case.owner.validate_report(case.contexts[0], original_form, case.forms[0])
                assert_accounting(case)
                assert case.owner.native_hmmer_preparation_returns.received_context(parent) == received
            assert _runtime_snapshot(case) == original_runtime
            assert case.record.controller_state.history == original_history
            assert case.returned[0] == original_form
            assert {ref: case.store.get_artifact(ref) for ref in retained_refs} == retained_bytes
        finally:
            unavailable_attempt.rename(attempt)
    finally:
        unavailable_source.rename(source)


def _verify_case(tmp_path, monkeypatch, declared_format, content, *, expected_rows,
                 expected_map, infer_alphabet=False):
    source, choice, case = _selected_case(
        tmp_path, declared_format, content, width=len(expected_rows[0]), infer_alphabet=infer_alphabet)
    try:
        parent, received = assert_accounting(case)
        body, bundle, sheet, components = read_retained(case)
        assert body["complete"] is True and body["failures"] == []
        assert_native_custody(case, bundle)
        assert bundle["inputs"][0]["staged_sha256"] == hashlib.sha256(content).hexdigest()
        assert sheet["operation"]["settings"]["--informat"] == FORMAT_ARGUMENTS[declared_format]
        alphabet_flags = {"--dna", "--rna", "--amino"}
        assert set(case.job["options"]) & alphabet_flags == (set() if infer_alphabet else {"--dna"})
        assert set(bundle["realized_argv"]) & alphabet_flags == (set() if infer_alphabet else {"--dna"})
        if infer_alphabet:
            assert not (set(sheet["operation"]["settings"]) & alphabet_flags)
            decoding = sheet["input_records"][0]["input_decoding"]
            assert decoding["alphabet_basis"] == "native_source_inference"
            assert decoding["effective_alphabet"] == "DNA"
            assert decoding["explicit_alphabet"] is None
            assert decoding["source_sha256"] == hashlib.sha256(content).hexdigest()
            probe = decoding["alphabet_probe"]
            expected_counts = {"A": 6, "C": 12, "G": 6, "T": 6}
            assert probe["counts_az"] == [expected_counts.get(chr(65 + i), 0) for i in range(26)]
            assert probe["counted_letters"] == 30
        _assert_numbers_and_return(
            case, choice, bundle, sheet, components, declared_format=declared_format,
            expected_rows=expected_rows, expected_map=expected_map)
        assert case.owner.native_hmmer_preparation_returns.received_facts(parent, case.forms[0]) == {
            PREFIX + "rows": case.returned[0]["rows"]}
        child_record, = case.result_records
        assert child_record["units_consumed"] == 1
        assert [unit["controller_step"]["marginal_credit"] for unit in child_record["units"]] == [2]
        assert child_record["controller_state"]["estimate"]["expected_next_gain"] == NumericBand.exact(0).as_record()
        root_record = next(item for item in case.records if item["episode_id"] == case.record.episode_id)
        assert len([unit for unit in root_record["units"]
                    if (unit.get("child") or {}).get("episode_id") == child_record["episode_id"]]) == 1
        assert tuple(case.record.controller_state.history) == (0, 0)
        assert case.store.count("observation") == 0
        proof = case.owner.completion_for_action(case.contexts[0], body["operation_key"])
        assert proof and case.owner.verify_completion(case.contexts[0], proof)

        _assert_saved_recalculation_and_closed_replay(
            case, source, monkeypatch, body, sheet, components, parent, received)
        (tmp_path / "INPUT_FORMAT_NUMERICAL_EXAMPLE.json").write_text(json.dumps({
            "fixture_kind": "authored_engineering_input",
            "declared_format": declared_format,
            "source_sha256": hashlib.sha256(content).hexdigest(),
            "source_bytes_hex": content.hex(),
            "inference_requested": infer_alphabet,
            "source_input_decoding": sheet["input_records"][0].get("input_decoding"),
            "original_job": case.job,
            "native_argv": bundle["realized_argv"],
            "returncode": bundle["returncode"],
            "sheet_artifact_ref": body["prepared"]["sheet_artifact_ref"],
            "calculations_artifact_ref": body["prepared"]["calculations_artifact_ref"],
            "native_mappings": components["rows"][0]["native_mappings"],
            "reconstruction": components["rows"][0]["reconstruction"],
            "typed_return": case.returned[0],
            "completion_proof": proof,
            "saved_only_recalculation_equal": True,
            "closed_replay_equal": True,
            "closed_histories_unchanged": True,
            "scientific_observation_count": 0,
        }, indent=2) + "\n")
    finally:
        case.store.close()


@pytest.mark.parametrize("declared_format", tuple(AUTHORED_INPUTS))
def test_declared_input_format_reaches_shared_sheet_return_and_saved_replay(
        tmp_path, monkeypatch, declared_format):
    expected_rows = (["AaaA", "AaaA", "C--C"] if declared_format in {"a2m", "psiblast"}
                     else ["AAAA", "AAAA", "C--C"])
    _verify_case(tmp_path, monkeypatch, declared_format, AUTHORED_INPUTS[declared_format],
                 expected_rows=expected_rows, expected_map=[1, 4])


def test_original_source_alphabet_inference_reaches_return_and_saved_replay(tmp_path, monkeypatch):
    # Native AFA counts original sequence lines through EOF: A6 C12 G6 T6,
    # n=30>10, all four canonical DNA letters, no outside-DNA letters. The
    # source classifier therefore returns DNA without any selected flag.
    # This expectation is not a second implementation of that classifier.
    _verify_case(tmp_path, monkeypatch, "afa", AUTHORED_INFERRED_AFA,
                 expected_rows=["ACGTACGTACGT", "ACGTACGTACGT", "C--CC--CC--C"],
                 expected_map=[1, 4, 5, 8, 9, 12], infer_alphabet=True)
