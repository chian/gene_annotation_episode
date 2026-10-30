"""Synthetic API compatibility proof, not a proposed-reader implementation.

Fixed invented source fixtures nominate their own known roles/context. Existing
literal/unit/count helpers read actual fixture bytes. A separate composition call
validates and calculates the frozen API. No paper/image/model/episode is used.
"""
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))
from jsonschema import Draft202012Validator
from gene_annotation_episode.domain import identity
from gene_annotation_episode.literature_assay_inputs import _Sources
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError, RATE_UNITS
from gene_annotation_episode.literature_rate_native_inputs import _number, _unit, _plain_unit, _check_explicit_unit
from gene_annotation_episode.literature_kinetic_inputs import _count_reading, _interval, _confidence
from gene_annotation_episode.literature_transport_inputs import _json_covariance
from gene_annotation_episode.literature_controlled_response_calculations import (
    PRIMITIVE_ORDER, validate_controlled_response_inputs, populate_controlled_response,
)


def write_new(name, value):
    with (HERE / name).open("x") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False); stream.write("\n")


def main():
    text = ("<p>Wholly invented μ-prefixed source fixture.</p>\n"
        "<p>Endpoint: initial retained-tracer rate.</p>\n"
        "<p>Normalization: same positive paired-reference protein-input mass for all four arms, including empty controls.</p>\n"
        "<p>Protein construct: synthetic P.</p>\n"
        "<p>Control preparation: synthetic empty preparation.</p>\n"
        "<p>Protocol one and protocol zero are the intended levels.</p>\n"
        "<p>Observation P1: protein-containing response in protocol one, 12 nmol/min/mg.</p>\n"
        "<p>Observation E1: protein-free response in protocol one, 2 nmol/min/mg.</p>\n"
        "<p>Observation P0: protein-containing response in protocol zero, 5 nmol/min/mg.</p>\n"
        "<p>Observation E0: protein-free response in protocol zero, 1 nmol/min/mg.</p>\n"
        "<p>The same E1 observation is explicitly applied to protocol zero under a stipulated reference-invariance assumption.</p>\n"
        "<p>Reported SD: 0.6 nmol/min/mg.</p>\n"
        "<p>Reported repetitions: three technical measurements.</p>\n"
        "<p>Reported CI: [9, 15] nmol/min/mg.</p>\n"
        "<p>Reported confidence: 95%.</p>\n"
        "<p>Unsupported response: 7 widgets/min.</p>\n")
    main_ref = identity("source", "controlled_007_invented_main")
    main_raw = text.encode()
    sources = {main_ref: main_raw}
    def source_result(reference, representation):
        assert representation == "original" and reference in sources
        raw = sources[reference]
        return {"artifact_ref": identity("artifact", hashlib.sha256(raw).hexdigest()), "content": raw}
    custody = _Sources(source_result)
    def witness(quote, *, source_ref=main_ref, after=0):
        visible = sources[source_ref].decode()
        start = visible.index(quote, after)
        return {"source_ref": source_ref, "representation": "original", "start": len(visible[:start].encode()),
            "end": len(visible[:start + len(quote)].encode()), "quote": quote}
    def tagged(value):
        return {"kind": "text", **value}
    def number(quote, token):
        start = quote.index(token)
        return {"witness": witness(quote), "number_start": start, "number_end": start + len(token)}
    def meaning(quote):
        w = tagged(witness(quote))
        return {"status": "known", "label": quote, "witnesses": [w], "canonical_witness": w,
            "canonical_correspondence": {"value": "same", "witnesses": [w]}}
    def interpreted(value, quote=None, w=None):
        return {"value": value, "witnesses": [tagged(w)] if w is not None else [tagged(witness(quote))] if quote else []}
    lines = ["Observation P1: protein-containing response in protocol one, 12 nmol/min/mg.",
             "Observation E1: protein-free response in protocol one, 2 nmol/min/mg.",
             "Observation P0: protein-containing response in protocol zero, 5 nmol/min/mg.",
             "Observation E0: protein-free response in protocol zero, 1 nmol/min/mg."]
    endpoint = meaning("initial retained-tracer rate")
    norm = meaning("same positive paired-reference protein-input mass for all four arms, including empty controls")
    targets = [meaning("protocol one"), meaning("protocol zero")]
    uncertainty = {"statistic": interpreted("unspecified"), "magnitude": None, "interval": None, "unit": None,
        "unit_relationship": interpreted("unknown"), "confidence_level": None, "count": None,
        "repetition_basis": interpreted("unspecified"), "estimate_basis": interpreted("unknown")}
    arms = {}
    for i, (role, line, token) in enumerate(zip(PRIMITIVE_ORDER, lines, ("12", "2", "5", "1"))):
        unit_at = text.index(line) + line.index("nmol")
        arms[role] = {"source_kind": "synthetic_fixture", "context": dict.fromkeys(
            ("subject", "organism", "genotype", "construct", "preparation", "experimental_system")),
            "protein_arrangement": interpreted("protein_present" if i % 2 == 0 else "protein_free_control",
                "protein-containing" if i % 2 == 0 else "protein-free"),
            "subject_construct": meaning("synthetic P" if i % 2 == 0 else "synthetic empty preparation"),
            "condition": deepcopy(targets[0 if i < 2 else 1]), "endpoint": deepcopy(endpoint), "normalization": deepcopy(norm),
            "physical_observation": meaning(line), "intended_factor_level": None,
            "measurement": {"kind": "source_literal", "literal": {"status": "exact", "candidates": [number(line, token)], "fragments": []},
                "unit": witness("nmol/min/mg", after=unit_at)}, "reported_uncertainty": deepcopy(uncertainty)}
    relationships = {"condition1_target": deepcopy(targets[0]), "condition0_target": deepcopy(targets[1]),
        "condition_levels_relation": interpreted("different", "Protocol one and protocol zero are the intended levels"),
        "subject_construct_across_conditions": interpreted("same", "synthetic P"),
        "condition1_control_application": interpreted("matched_condition_control", lines[1]),
        "condition0_control_application": interpreted("matched_condition_control", lines[3]),
        "control_reference_reuse": interpreted("distinct_observations", "Observation E0"),
        "nonintended_conditions": interpreted("unknown"), "intended_factor": tagged(witness("intended levels"))}
    source_cov = {"version": "controlled_response_covariance_source_v1",
        "variables": [{"label": label, "unit": "nmol/min/mg", "description": line} for label, line in
            zip(("protein one", "empty one", "protein zero", "empty zero"), lines)],
        "covariance": [[(1, .25, .36, .09)[i] if i == j else 0 for j in range(4)] for i in range(4)],
        "origin": "synthetic", "variance_status": "known", "model_kind": "none"}
    covariance_ref = identity("source", "controlled_007_invented_covariance")
    sources[covariance_ref] = json.dumps(source_cov, indent=2, ensure_ascii=False).encode()
    def bindings_for(document, reference, chosen_arms, indices):
        values = {}
        for role, index in zip(PRIMITIVE_ORDER, indices):
            label = json.dumps(document["variables"][index]["label"], ensure_ascii=False)
            # Fixed unique-label fixtures only. A future real reader needs its
            # proposed structural JSON-token lexer, not this unique search.
            assert sources[reference].decode().count(label) == 1
            label_witness = witness(label, source_ref=reference)
            owner = chosen_arms[role]["physical_observation"]["canonical_witness"]
            values[role] = {"variable_index": index, "label_witness": label_witness, "owner_witness": owner,
                "correspondence": {"value": "same", "witnesses": [tagged(label_witness), owner]}}
        return values
    selected = {"version": "controlled_response_source_selection_v1", "source_ref": main_ref,
        "images": [], "arms": arms, "relationships": relationships,
        "covariance": {"source_ref": covariance_ref, "bindings": bindings_for(source_cov, covariance_ref, arms, [0, 1, 2, 3])},
        "variance_status": interpreted("known", w=witness('"known"', source_ref=covariance_ref)),
        "model_kind": interpreted("none", w=witness('"none"', source_ref=covariance_ref))}
    selection_schema = json.loads((HERE / "SELECTION_SCHEMA_007.json").read_text())
    covariance_schema = json.loads((HERE / "COVARIANCE_SOURCE_SCHEMA_007.json").read_text())
    Draft202012Validator.check_schema(selection_schema)
    Draft202012Validator.check_schema(covariance_schema)
    Draft202012Validator(selection_schema).validate(selected)
    Draft202012Validator(covariance_schema).validate(source_cov)

    def fixture_projection(selection, joint_source):
        # Research composition for these positively nominated, fixed fixtures.
        # This does not implement the proposed reader or its failure contracts.
        def canonical_meaning(item, category):
            chosen = item["canonical_witness"]
            raw_w = {k:v for k,v in chosen.items() if k != "kind"}
            actual = custody.witness(raw_w, "synthetic meaning")
            key = {name: actual[name] for name in ("source_ref", "artifact_ref", "start", "end")}
            key["byte_sha256"] = hashlib.sha256(sources[actual["source_ref"]]).hexdigest()
            return identity("controlled_" + category, key)
        parsed_arms = {}
        for role, arm in selection["arms"].items():
            nomination = arm["measurement"]
            number_read = _number(nomination["literal"]["candidates"][0], custody, "rate")
            unit_read = _unit(nomination["unit"], custody, {k:v for k,v in arm["endpoint"]["canonical_witness"].items() if k != "kind"})
            _check_explicit_unit(number_read, unit_read, custody)
            unit_key = next(key for key in RATE_UNITS if _plain_unit(key) == _plain_unit(unit_read["raw_unit"]))
            n = number_read["selector"]; w = n["witness"]
            absolute = w["start"] + len(w["quote"][:n["number_start"]].encode())
            source_key = {"source_ref": w["source_ref"], "artifact_ref": w["artifact_ref"],
                "start": absolute, "end": absolute + len(number_read["raw_number"].encode())}
            parsed_arms[role] = {"value": number_read["value"], "threshold": None, "relation": "eq", "approximate": number_read["approximate"],
                "unit": unit_key, "status": "point", **{name + "_id": canonical_meaning(arm[name], name) for name in
                    ("endpoint", "normalization", "subject_construct", "condition", "physical_observation")},
                "source_observation_id": identity("controlled_source_token", source_key), "origin": "synthetic",
                "digitization_interval": None, "protein_arrangement": arm["protein_arrangement"]["value"],
                "meaning_statuses": dict.fromkeys(("endpoint", "normalization", "subject_construct", "condition", "physical_observation"), "known")}
        relations = {name: ({"status": "known", "canonical_id": canonical_meaning(item, "condition")}
            if name.endswith("_target") else identity("controlled_intended", item)
            if name == "intended_factor" else item["value"]) for name,item in selection["relationships"].items()}
        indices = [selection["covariance"]["bindings"][role]["variable_index"] for role in PRIMITIVE_ORDER]
        cov = {"primitive_order": list(PRIMITIVE_ORDER),
            "physical_observation_ids": [parsed_arms[role]["physical_observation_id"] for role in PRIMITIVE_ORDER],
            "units": [joint_source["variables"][i]["unit"] for i in indices],
            "matrix": [[joint_source["covariance"][i][j] for j in indices] for i in indices]}
        return {"version": "controlled_response_inputs_v1", "arms": parsed_arms, "relationships": relations,
            "covariance": cov, "variance_status": "known", "model_kind": "none"}

    parsed_source = _json_covariance(sources[covariance_ref])
    inputs = fixture_projection(selected, parsed_source)
    validated = validate_controlled_response_inputs(inputs)
    # Separate composition: never a calculator call inside a source reader.
    sheet = populate_controlled_response(validated)
    assert sheet["cells"]["controlled_response_difference"]["value"] == .006
    assert sheet["cells"]["contrast_variance"]["value"] == .0000017
    assert not any(owner in sources[covariance_ref].decode() for owner in inputs["covariance"]["physical_observation_ids"])
    shared_selected = deepcopy(selected)
    shared_selected["arms"][PRIMITIVE_ORDER[3]] = deepcopy(shared_selected["arms"][PRIMITIVE_ORDER[1]])
    shared_selected["relationships"]["condition0_control_application"] = interpreted("shared_reference_assumption", "stipulated reference-invariance assumption")
    shared_selected["relationships"]["control_reference_reuse"] = interpreted("same_reference_with_stated_invariance", "same E1 observation")
    shared_cov = deepcopy(source_cov)
    shared_cov["variables"] = shared_cov["variables"][:3]
    shared_cov["covariance"] = [[1, 0, 0], [0, .25, 0], [0, 0, .36]]
    shared_ref = identity("source", "controlled_007_invented_shared_covariance")
    sources[shared_ref] = json.dumps(shared_cov, indent=2).encode()
    shared_selected["covariance"] = {"source_ref": shared_ref,
        "bindings": bindings_for(shared_cov, shared_ref, shared_selected["arms"], [0, 1, 2, 1])}
    Draft202012Validator(selection_schema).validate(shared_selected)
    shared_inputs = validate_controlled_response_inputs(fixture_projection(shared_selected, _json_covariance(sources[shared_ref])))
    shared_sheet = populate_controlled_response(shared_inputs)
    assert shared_sheet["cells"]["controlled_response_difference"]["value"] == .007
    assert shared_sheet["cells"]["contrast_variance"]["value"] == .00000136
    reported_count = _count_reading(number("three technical measurements", "three"), custody)
    assert reported_count["value"] == 3 and reported_count["status"] == "exact"
    sd = _number(number("Reported SD: 0.6 nmol/min/mg.", "0.6"), custody, "spread")
    ci = {"witness": witness("[9, 15]"), "lower_start": 1, "lower_end": 2, "upper_start": 4, "upper_end": 6}
    reported_interval = _interval(ci, custody)
    confidence_selector = witness("95%")
    try:
        confidence = _confidence(confidence_selector, custody)
    except ExperimentalContractError as error:
        assert error.code == "partial_source_confidence_level"
        confidence = {"selection": confidence_selector,
            "actual_witness": custody.witness(confidence_selector, "confidence fixture"),
            "value": None, "classification": "reader_capability",
            "observed_error": {"code": error.code, "field": error.field},
            "source_ends_with_authentic_sentence_period": True}
    clipped = deepcopy(selected["arms"][PRIMITIVE_ORDER[0]]["measurement"]["literal"]["candidates"][0])
    clipped["number_start"] += 1
    try:
        _number(clipped, custody, "rate")
    except ExperimentalContractError as error:
        clip_failure = {"code": error.code, "field": error.field}
    else:
        raise AssertionError("Clipped12 must not become2")
    assert clip_failure["code"] == "partial_source_numeric_token"
    try:
        _json_covariance(b'{"one":1e-500}')
    except ExperimentalContractError as error:
        legacy_range = {"code": error.code, "field": error.field}
    else:
        raise AssertionError("Old JSON parser must not silently turn nonzero into0")
    assert Fraction("1e-500") > 0
    read_unknown = _unit(witness("widgets/min"), custody, None)
    assert read_unknown["canonical_unit"] is None
    receipt = {"scope": "Invented proposal compatibility only, not new targeted-reader execution",
        "schema_valid": True, "existing_helpers_used": ["_Sources.witness", "rate _number/_unit/_check_explicit_unit", "kinetic _count_reading/_interval/_confidence", "transport _json_covariance"],
        "ordinary": {"selection": selected, "source_covariance": source_cov, "calculation_inputs": inputs, "sheet": sheet},
        "shared_control": {"selection": shared_selected, "source_covariance": shared_cov, "calculation_inputs": shared_inputs, "sheet": shared_sheet},
        "source_numbers_are_parsed_not_direct_selected_arguments": True, "source_covariance_has_no_generated_owner_ids": True,
        "reported_uncertainty_not_used_to_construct_covariance": {"count": reported_count, "spread": sd,
            "ci": reported_interval, "confidence": confidence}, "clipping_failure": clip_failure,
        "legacy_json_numeric_range": legacy_range, "exact_lexical_1e_minus500_is_nonzero": True,
        "unknown_unit_retained": read_unknown, "new_reader_implemented": False, "graph_reader_implemented": False,
        "scientific_source_or_model_run": False, "runtime_observations": 0}
    write_new("SOURCE_COVARIANCE_007.json", source_cov)
    write_new("SOURCE_SHARED_COVARIANCE_007.json", shared_cov)
    with (HERE / "SOURCE_TEXT_007.txt").open("x") as stream: stream.write(text)
    write_new("SELECTED_ARGUMENT_EXAMPLE_007.json", selected)
    write_new("COMPATIBILITY_RECEIPT_007.json", receipt)
    print(json.dumps({"status": "passed", "ordinary_e": .006, "ordinary_V": .0000017,
        "shared_control_e": .007, "shared_control_V": .00000136,
        "reported_count": reported_count["value"], "source_host_owner_ids_required": False,
        "new_reader_or_graph_implemented": False}))


if __name__ == "__main__":
    main()
