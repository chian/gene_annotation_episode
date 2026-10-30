"""New declared weighting branches through the existing child-owned harness.

These are unexecuted native recipes until the bounded root verification runs.
The harness's scripted scientific choices are fixtures; local selection,
execution, capture, shared grading, requested returns and replay are production.
No completed original tool case is rerun by this module.
"""
import asyncio
from copy import deepcopy
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode import native_hmmer_preparation_worker as worker
from gene_annotation_episode import hmmer_alignment_preparation_calculations as calculations
from gene_annotation_episode import hmmer_alignment_preparation_data as data
from gene_annotation_episode import native_hmmer_preparation_acquisition as acquisition
from test_native_hmmer_preparation_contracts import job, operand
from test_native_hmmer_preparation_workflow import (
    run_case, choice_for, assert_accounting, assert_native_custody,
    assert_projected_values, read_retained,
)


@pytest.mark.parametrize("weight", ["--wgsc", "--wblosum", "--wpb"])
def test_new_weighting_branch_reaches_requested_child_return_and_closed_replay(tmp_path, monkeypatch, weight):
    source = tmp_path / "selected.sto"
    rows = (["A--A"] * 10000 + ["CCCC"] * 40001 if weight == "--wpb"
            else ["AAAA", "AAAA", "C--C"])
    source.write_text("# STOCKHOLM 1.0\n" + "".join("s" + str(i) + " " + sequence + "\n"
        for i, sequence in enumerate(rows)) + "//\n")
    selected = job("alimask", "alignment_to_model", ["--dna", "--fast", weight,
        "--seed", "17", "--fragthresh", "0", "--symfrac", ".65" if weight == "--wpb" else ".6",
        "--ali2model", "1-4"])
    selected["operands"] = [operand("alignment", source, "stockholm")]
    choice = choice_for(selected)
    choice["projection"]["quantities"] = ["components.input_sequence_count", "components.input_column_count",
        "components.mapped_model_position_count", "components.native_mapping_row_count"]
    choice["projection"]["checks"] = ["native_mapping", "requested_ranges"]
    case = run_case(tmp_path, "alimask", "alignment_to_model", job_override=selected, selectors=[choice])
    try:
        parent, received = assert_accounting(case)
        body, bundle, sheet, components = read_retained(case)
        assert_native_custody(case, bundle)
        assert_projected_values(case.returned[0], choice, components)
        assert case.returned[0]["completed"] is True
        row, = components["rows"]
        assert row["reconstruction"]["map"] == [1, 4]
        assert row["components"]["mapped_model_position_count"]["value"] == 2
        assert row["components"]["input_sequence_count"]["value"] == len(rows)
        assert all(item["state"] == "pass" for item in components["checks"] if item["code"] == "native_mapping")
        context = sheet["input_records"][0]["map_reconstruction_context"]
        assert context["source_sha256"] == bundle["inputs"][0]["staged_sha256"]
        assert context["requested_cli_seed"] == context["resolved_cli_seed"] == 17
        assert context["effective_pb_config"]["seed"] == 42
        trace = row["reconstruction"]["weighting_trace"]
        assert trace["method"] == weight[2:]
        if weight == "--wpb":
            assert len(trace["sampling"]["source_row_ordinals"]) == 10000
            assert trace["sampling"]["seed"] == 42
        else:
            assert [r["weight"] for r in row["reconstruction"]["weights"]] == [.75, .75, 1.5]
        assert case.store.count("observation") == 0
        original = deepcopy(case.outcomes[0])
        saved_history = deepcopy(case.record.controller_state.history)
        attempt = Path(case.plan["attempt_directory"])
        unavailable = attempt.with_name("original-unavailable-for-replay")
        attempt.rename(unavailable)
        def forbidden(*args, **kwargs):
            raise AssertionError("closed replay performed native work, acquisition, parsing or recalculation")
        original_socket = socket.socket
        def local_socket_only(*args, **kwargs):
            family = args[0] if args else kwargs.get("family", socket.AF_INET)
            if family != socket.AF_UNIX:
                forbidden(*args, **kwargs)
            return original_socket(*args, **kwargs)
        monkeypatch.setattr(socket, "socket", local_socket_only)
        for target, name in ((native, "start_job"), (native, "status"), (subprocess, "Popen"),
                (worker, "grade_hmmer_preparation"), (worker, "recalculate_hmmer_preparation"),
                (calculations, "reconstruct_alimask_model_map"),
                (data, "populate_hmmer_alignment_preparation_sheet"), (acquisition, "_capture_file")):
            monkeypatch.setattr(target, name, forbidden)
        try:
            replay = asyncio.run(case.owner.execute(case.contexts[0], "execution.results.collect", {}, body["operation_key"]))
            assert replay == {key: value for key, value in original.items() if key != "pending_work_after_action"}
            case.owner.validate_report(case.contexts[0], case.returned[0], case.forms[0])
            assert_accounting(case)
            assert case.record.controller_state.history == saved_history
            saved = json.loads(case.flow.journal.row("runtime_actions", case.contexts[0].episode_id, 0)["result"])
            assert saved == original
            assert case.owner.native_hmmer_preparation_returns.received_context(parent) == received
        finally:
            unavailable.rename(attempt)
    finally:
        case.store.close()
