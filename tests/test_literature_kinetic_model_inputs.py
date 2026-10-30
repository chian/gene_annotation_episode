"""Synthetic retained model fixtures; no paper or experimental inference."""
from copy import deepcopy
from dataclasses import replace

import pytest

from gene_annotation_episode.domain import canonical
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_kinetic_inputs import read_kinetic_inputs
from gene_annotation_episode.literature_kinetic_calculations import kinetic_operand_keys
from gene_annotation_episode.literature_kinetic_model_inputs import read_kinetic_model
from test_literature_kinetic_storage import setup


def setup_model(path, *, status="known", n="20", d="10", change=None):
    store, context, args = setup(path, kind="Km", unit="uM", n=n, d=d)
    for role in ("numerator", "denominator"):
        args[role]["measurement_identity"] = deepcopy(args[role]["measurement"]["number"]["witness"])
    if change:
        change(args)
    def read(reference, representation):
        row = store.get(reference)
        ref = row["artifact_ref"] if representation == "original" else row["text_ref"]
        return {"artifact_ref": ref, "content": store.get_artifact(ref)}
    inputs = read_kinetic_inputs(args, read_source=read)["calculation_inputs"]
    keys = kinetic_operand_keys(inputs)
    wire = {"version": "a105_kinetic_log_model_v1", "measurement_order": ["numerator", "denominator"],
        "measurement_keys": [keys[role] for role in ("numerator", "denominator")],
        "covariance": [[.04, .01], [.01, .09]], "variance_status": status,
        "observation_model": "known_normal_log_parameters", "log_basis": "natural_log_canonical_parameter", "origin": "synthetic"}
    def source(content, parents):
        artifact = store.artifact(content, "application/json")
        return store.put("source", {"provider": "synthetic_kinetic_model_fixture", "accession": None, "uri": None,
            "artifact_ref": artifact, "text_ref": artifact, "request_ref": None, "version": None,
            "retrieved_at": None, "parent_source_refs": parents}, origin="caller")
    words = "Synthetic joint normal natural-log canonical kinetic parameter error model; Cnn 0.04, Cnd 0.01, Cdd 0.09."
    methods = source(words, [args["source_ref"]])
    model = source(canonical(wire), [args["source_ref"], methods["id"]])
    witness = {"source_ref": methods["id"], "representation": "original", "start": 0, "end": len(words.encode()), "quote": words}
    refs = (*context.received_record_refs, methods["id"], model["id"])
    context = replace(context, received_record_refs=refs, assignment={**context.assignment, "source_refs": list(refs)})
    return store, context, args, {"source_ref": None, "model_source_ref": model["id"], "model_witnesses": [witness]}, inputs, wire


def source_for(store, reference):
    row = store.get(reference)
    return {"source_ref": reference, "artifact_ref": row["artifact_ref"], "content": store.get_artifact(row["artifact_ref"])}


def test_exact_wire_model_binds_actual_bytes_and_preserves_owners(tmp_path):
    store, context, _, args, inputs, wire = setup_model(tmp_path)
    with store:
        source = source_for(store, args["model_source_ref"])
        parsed = read_kinetic_model(source, inputs=inputs)
        assert {k: parsed["model"][k] for k in wire} == wire
        assert parsed["model"]["source"] == {"source_ref": source["source_ref"], "artifact_ref": source["artifact_ref"],
            "representation": "original", "start": 0, "end": len(source["content"])}


@pytest.mark.parametrize("change,reason", [
    (lambda m: m.update(measurement_order=["denominator", "numerator"]), "measurement_order_mismatch"),
    (lambda m: m["measurement_keys"].reverse(), "measurement_owner_mismatch"),
    (lambda m: m.update(log_basis="log10_uM"), "unsupported_kinetic_meaning"),
    (lambda m: m.update(covariance=[[.04,.1],[.1,.09]]), "positive_semidefinite"),
    (lambda m: m.update(covariance=[[.04,.01],[.02,.09]]), "symmetric_kinetic"),
    (lambda m: m.update(covariance=[[True,0],[0,.09]]), "finite_number"),
    (lambda m: m.update(source={"source_ref": "source_forged"}), "closed_fields"),
    (lambda m: m.update(measurement_keys=[None,None]), "measurement_owner_mismatch"),
])
def test_invalid_model_cannot_repair_owners_basis_or_covariance(tmp_path, change, reason):
    store, _, _, args, inputs, wire = setup_model(tmp_path)
    with store:
        change(wire)
        source = source_for(store, args["model_source_ref"])
        source["content"] = canonical(wire).encode()
        with pytest.raises(ExperimentalContractError, match=reason):
            read_kinetic_model(source, inputs=inputs)


@pytest.mark.parametrize("raw,reason", [(b'{"version":1,"version":2}', "duplicate_json_key"),
    (b'{"covariance":NaN}', "nonfinite_json_constant"), (b'{"covariance":1e-999}', "numerical_model_range"),
    (b'not-json', "malformed_kinetic_model_source")])
def test_wire_json_does_not_hide_malformed_or_nonfinite_operands(tmp_path, raw, reason):
    store, _, _, args, inputs, _ = setup_model(tmp_path)
    with store:
        source = source_for(store, args["model_source_ref"])
        source["content"] = raw
        with pytest.raises(ExperimentalContractError, match=reason):
            read_kinetic_model(source, inputs=inputs)
