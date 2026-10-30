"""Additional review check on saved real request bytes, without host acquisition.

Mutated wrappers below are explicitly synthetic negative inputs, not possessed
source records. Candidate implementation and its running suite stay unchanged.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

import pytest

AREA = Path(__file__).resolve().parent
CANDIDATE = AREA / "candidate"
sys.path.insert(0, str(CANDIDATE / "tests"))
sys.path.insert(0, str(CANDIDATE))

from gene_annotation_episode import bvbrc_proteome_bundle_contracts as c
from gene_annotation_episode import bvbrc_proteome_bundle_resolution as provider
from test_bvbrc_proteome_submitted_parameters import replace_request_bytes, assert_native_means
from test_bvbrc_proteome_bundle_resolution import consume, codes

assert Path(provider.__file__).resolve().is_relative_to(CANDIDATE)


def saved_case():
    directory = AREA / "example_001"
    read = lambda name: json.loads((directory / name).read_text())
    raw = {}
    for ref, entry in read("RAW_MANIFEST.json").items():
        raw[ref] = (directory / entry["path"]).read_bytes()
        assert hashlib.sha256(raw[ref]).hexdigest() == entry["sha256"]
        assert len(raw[ref]) == entry["byte_count"]
    return dict(bundle=read("BUNDLE.json"), artifact_bytes=raw,
        supplied_values=read("SUPPLIED_VALUES.json"), parameters=read("PARAMETERS.json"),
        requested_form=read("REQUESTED_FORM.json"))


def native_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


@pytest.fixture(autouse=True)
def no_acquisition(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("pure review check attempted acquisition")
    monkeypatch.setattr("socket.create_connection", forbidden)
    monkeypatch.setattr("urllib.request.OpenerDirector.open", forbidden)
    monkeypatch.setattr("subprocess.run", forbidden)
    monkeypatch.setattr("gene_annotation_episode.state.Store.get", forbidden)
    monkeypatch.setattr("gene_annotation_episode.state.Store.get_artifact", forbidden)


def test_original_saved_retained_wrapper_remains_accepted():
    result = consume(saved_case())
    assert result["sheet"]["input_index_result"]["status"] == "ok"
    assert result["sheet"]["input_index_result"]["value"]["reference_original_index"] == 2
    assert_native_means(result)


@pytest.mark.parametrize("change", ["bound_request", "bound_arguments", "resolved_operation",
                                   "bound_and_prepared_request", "bound_and_prepared_arguments"])
def test_preparation_relationship_corruption_rejects_even_with_coherent_rpc_and_snapshot(change):
    case = saved_case()
    record = json.loads((AREA / "example_001" / "retained_request_ref.bin").read_bytes())
    prepared = record["prepared"]
    bound = prepared["bound_inputs"]
    if change in {"bound_request", "bound_and_prepared_request"}:
        bound["request_sha256"] = "0" * 64
        if change == "bound_and_prepared_request":
            prepared["request_sha256"] = bound["request_sha256"]
            bound["resolved"]["preparation"]["request_sha256"] = bound["request_sha256"]
    elif change in {"bound_arguments", "bound_and_prepared_arguments"}:
        bound["selected_argument_sha256"] = "0" * 64
        if change == "bound_and_prepared_arguments":
            prepared["arguments_sha256"] = bound["selected_argument_sha256"]
            record["origin"]["arguments_sha256"] = bound["selected_argument_sha256"]
    else:
        bound["resolved"]["operation"] = "api.bvbrc_appservice.status"
    # Updating all RPC-id copies and the actual-body hash does not repair the
    # disagreement between the retained preparation and its supplied operands.
    rpc = prepared["native_operands"]["call"]["rpc_request"]
    rpc["id"] = "bvbrc_rpc_" + native_digest({"operation": prepared["operation"],
        "owner": bound["original_job_owner"], "resource_id": bound["resource_id"],
        "request": bound["request_sha256"], "arguments": bound["selected_argument_sha256"]})
    record["snapshot"]["request"]["rpc"] = deepcopy(rpc)
    body = c.canonical(rpc).encode()
    record["snapshot"]["transport"]["request"].update(body_bytes=len(body),
        body_sha256=hashlib.sha256(body).hexdigest())
    raw = c.canonical(record).encode()
    with pytest.raises(ValueError):
        provider._submitted_record(raw, case["bundle"]["original_task"])
    replace_request_bytes(case, raw)
    result = consume(case)
    assert result["sheet"]["input_index_result"] is None
    assert "proteome_parameter_source_conflict" in codes(result)
    assert_native_means(result)
