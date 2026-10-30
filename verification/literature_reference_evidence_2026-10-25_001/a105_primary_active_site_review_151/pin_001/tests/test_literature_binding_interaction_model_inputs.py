"""Synthetic prepared model packets, not primary-source covariance extraction."""
from copy import deepcopy
from dataclasses import replace

import pytest

from gene_annotation_episode.domain import canonical
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_binding_interaction_inputs import read_binding_interaction_inputs
from gene_annotation_episode.literature_binding_interaction_calculations import MODEL_VERSION, ROLES, binding_interaction_operand_keys
from gene_annotation_episode.literature_binding_interaction_model_inputs import read_binding_interaction_model
from test_literature_binding_interaction_storage import setup


def setup_model(path, *, status="known", expressions=("5", "40", "2", "4"), change=None, covariance=None, distribution="normal", reporting_event=False):
    store, context, args = setup(path, change=change, expressions=expressions)
    def read(reference, representation):
        row = store.get(reference)
        ref = row["artifact_ref"] if representation == "original" else row["text_ref"]
        return {"artifact_ref": ref, "content": store.get_artifact(ref)}
    inputs = read_binding_interaction_inputs(args, read_source=read)["calculation_inputs"]
    keys = binding_interaction_operand_keys(inputs) if inputs else dict.fromkeys(ROLES)
    physical = [None if inputs is None or inputs["operands"][r] is None else inputs["operands"][r]["physical_fit_id"] for r in ROLES]
    matrix = covariance if covariance is not None else [[.04 if i == j else 0 for j in range(4)] for i in range(4)]
    wire = {"version": MODEL_VERSION, "parameter_kind": inputs["parameter_kind"] if inputs else "ic50",
        "measurement_order": list(ROLES), "measurement_keys": [keys[r] for r in ROLES], "physical_fit_ids": physical,
        "log_basis": "natural_log_nM", "distribution": distribution, "variance_status": status, "log_covariance": matrix,
        "reporting_event": "source_defined" if reporting_event else "unknown", "reporting_event_source": None}
    def source(content, parents):
        artifact = store.artifact(content, "application/json")
        return store.put("source", {"provider": "synthetic_interaction_model_fixture", "accession": None, "uri": None,
            "artifact_ref": artifact, "text_ref": artifact, "request_ref": None, "version": None,
            "retrieved_at": None, "parent_source_refs": parents}, origin="caller")
    words = "Synthetic joint normal natural-log nM parameter error model with ordered physical fits; covariance diagonal .04. Reporting event: printed upper thresholds."
    methods = source(words, [args["source_ref"]])
    witness = {"source_ref": methods["id"], "representation": "original", "start": 0, "end": len(words.encode()), "quote": words}
    if reporting_event:
        wire["reporting_event_source"] = {"kind": "utf8_span", "source_ref": methods["id"], "artifact_ref": methods["artifact_ref"], "start": 0, "end": len(words.encode())}
    model = source(canonical(wire), [args["source_ref"], methods["id"]])
    refs = (*context.received_record_refs, methods["id"], model["id"])
    context = replace(context, received_record_refs=refs, assignment={**context.assignment, "source_refs": list(refs)})
    return store, context, args, {"source_ref": None, "model_source_ref": model["id"], "model_witnesses": [witness]}, inputs, wire


def source_for(store, reference):
    row = store.get(reference)
    return {"source_ref": reference, "artifact_ref": row["artifact_ref"], "content": store.get_artifact(row["artifact_ref"])}


def test_exact_wire_binds_received_bytes_and_all_four_owners(tmp_path):
    store, _, _, args, inputs, wire = setup_model(tmp_path)
    with store:
        source = source_for(store, args["model_source_ref"])
        model = read_binding_interaction_model(source, inputs=inputs)["model"]
        assert {k: model[k] for k in wire} == wire
        assert model["source"] == {"source_ref": source["source_ref"], "artifact_ref": source["artifact_ref"], "kind": "utf8_span", "start": 0, "end": len(source["content"])}


@pytest.mark.parametrize("change,reason", [
    (lambda m: m["measurement_order"].reverse(), "measurement_order_mismatch"),
    (lambda m: m["measurement_keys"].reverse(), "estimate_owner_mismatch"),
    (lambda m: m["physical_fit_ids"].reverse(), "physical_owner_mismatch"),
    (lambda m: m.update(log_basis="log10_nM"), "natural_log_nM_required"),
    (lambda m: m.update(log_covariance=[[1,2,0,0],[2,1,0,0],[0,0,1,0],[0,0,0,1]]), "positive_semidefinite"),
    (lambda m: m["log_covariance"][0].__setitem__(1,.02), "symmetric_covariance"),
    (lambda m: m["log_covariance"][0].__setitem__(0,True), "finite_number"),
    (lambda m: m.update(source={"source_ref":"source_forged"}), "closed_fields"),
    (lambda m: m.update(parameter_kind="reported_hill_kd"), "parameter_kind_mismatch"),
    (lambda m: m.update(variance_status="assumed"), "unsupported_value"),
])
def test_wrong_owners_basis_covariance_and_unknown_fields_reject(tmp_path, change, reason):
    store, _, _, args, inputs, wire = setup_model(tmp_path)
    with store:
        change(wire)
        source = source_for(store,args["model_source_ref"])
        source["content"] = canonical(wire).encode()
        with pytest.raises(ExperimentalContractError,match=reason):
            read_binding_interaction_model(source, inputs=inputs)


@pytest.mark.parametrize("raw,reason", [(b'{"version":1,"version":2}',"duplicate_json_key"),
    (b'{"log_covariance":NaN}',"nonfinite_json_constant"),(b'{"log_covariance":1e-999}',"numerical_model_range"),
    (b'not-json',"malformed_binding_interaction_model_source")])
def test_malformed_and_nonfinite_wire_reject(tmp_path,raw,reason):
    store, _, _, args, inputs, _ = setup_model(tmp_path)
    with store:
        source = source_for(store,args["model_source_ref"]); source["content"] = raw
        with pytest.raises(ExperimentalContractError,match=reason):
            read_binding_interaction_model(source,inputs=inputs)


def test_shared_physical_owners_require_identical_covariance_rows(tmp_path):
    store,_,_,args,inputs,wire=setup_model(tmp_path)
    with store:
        inputs=deepcopy(inputs)
        inputs["operands"][ROLES[1]]["physical_fit_id"]=inputs["operands"][ROLES[0]]["physical_fit_id"]
        wire["physical_fit_ids"][1]=wire["physical_fit_ids"][0]
        wire["measurement_keys"]=[binding_interaction_operand_keys(inputs)[r] for r in ROLES]
        source=source_for(store,args["model_source_ref"]);source["content"]=canonical(wire).encode()
        with pytest.raises(ExperimentalContractError,match="shared_physical_covariance_mismatch"):
            read_binding_interaction_model(source,inputs=inputs)
