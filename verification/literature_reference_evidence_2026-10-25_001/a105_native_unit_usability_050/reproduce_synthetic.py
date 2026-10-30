"""Code-only usability probes. Every byte below is invented synthetic input.

No Store, run database, provider transcript, paper or network is opened.
This script writes only its own additive audit receipt.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from gene_annotation_episode.literature_assay_inputs import _Sources
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_rate_native_inputs import (
    _defined_unit, _number, rate_source_population_schema, read_rate_source_inputs,
)
from gene_annotation_episode.scientific_process_prompt import _schema


HERE = Path(__file__).resolve().parent
TEXT = (
    "<p>CompoundQ oxidation; synthetic assay; protein mass normalization. "
    "\u03bc reference rate 8 U/mg; test rate 2 U/mg.</p>\n"
    "<p>One unit was defined as 2 nmol CompoundQ oxidized per min.</p>"
)
RAW = TEXT.encode("utf-8")
ARTIFACT = "artifact_" + hashlib.sha256(RAW).hexdigest()


def read_source(reference, representation):
    assert reference == "synthetic:source"
    assert representation == "original"
    return {"artifact_ref": ARTIFACT, "content": RAW}


def witness(quote, *, after=0):
    start = TEXT.index(quote, after)
    return {"source_ref": "synthetic:source", "representation": "original",
            "start": len(TEXT[:start].encode("utf-8")),
            "end": len(TEXT[:start + len(quote)].encode("utf-8")), "quote": quote}


def number(quote, token, *, after=0):
    start = quote.index(token)
    return {"witness": witness(quote, after=after), "number_start": start,
            "number_end": start + len(token)}


def defined_unit():
    bridge = "One unit was defined as 2 nmol CompoundQ oxidized per min."
    definition_start = TEXT.index(bridge)
    return {"kind": "source_defined_rate_unit", "witness": witness("U/mg"),
        "definition": {
            "bridge": witness(bridge),
            "clause": witness("2 nmol CompoundQ oxidized per min"),
            "amount": number("2 nmol CompoundQ oxidized per min", "2"),
            "amount_unit": witness("nmol"), "time_unit": witness("min"),
            "endpoint": witness("CompoundQ oxidation"),
            "endpoint_entity": witness("CompoundQ"),
            "definition_entity": witness("CompoundQ", after=definition_start)}}


def args():
    endpoint = witness("CompoundQ oxidation")
    normalization = witness("protein mass normalization")
    arms = {}
    for role, quote, token in (("reference", "\u03bc reference rate 8 U/mg", "8"),
                               ("test", "test rate 2 U/mg", "2")):
        arms[role] = {name: None for name in (
            "subject", "construct", "preparation", "experiment", "label", "condition",
            "endpoint", "normalization", "measurement_identity")}
        arms[role].update(endpoint=endpoint, normalization=normalization,
            rate={"number": number(quote, token), "unit": defined_unit()},
            uncertainty={"kind": "unreported", "magnitude": None, "unit": None,
                "kind_witnesses": [], "count": None,
                "sampling_basis": {"value": "unspecified", "witnesses": []}})
    return {"input_mode": "native_source_spans", "source_ref": "synthetic:source",
        "source_kind": "synthetic_fixture", "experiment": witness("synthetic assay"),
        "arms": arms, "comparison": {
            "subject_relation": {"value": "unknown", "witnesses": []},
            "endpoint_relation": {"value": "same", "witnesses": [endpoint]},
            "normalization_relation": {"value": "same", "witnesses": [normalization]},
            "intended_change": None},
        "dependence": {"value": "unknown", "witnesses": []},
        "observation_model": {"value": "none", "witnesses": []}}


def capture(name, function, expected_code):
    try:
        function()
    except ExperimentalContractError as error:
        assert error.code == expected_code, (name, str(error))
        return {"case": name, "code": error.code, "field": error.field,
                "detail": error.detail}
    raise AssertionError("expected failure: " + name)


def main():
    full = args()
    extraction = read_rate_source_inputs(full, read_source=read_source)
    assert [row["value"] for row in extraction["rows"]] == [0.016, 0.004]
    assert all(row["unit"] == "umol/min/mg" for row in extraction["rows"])
    plain = deepcopy(full)
    for arm in plain["arms"].values():
        arm["rate"]["unit"] = arm["rate"]["unit"]["witness"]
    partial = read_rate_source_inputs(plain, read_source=read_source)
    assert all(row["value"] is None for row in partial["rows"])
    assert all(row["source"]["number"]["value"] is not None for row in partial["rows"])
    assert all(row["source"]["unit"]["unavailable_reason"] ==
               "source_defined_unit_definition_required" for row in partial["rows"])

    endpoint = _Sources(read_source).witness(witness("CompoundQ oxidation"), "endpoint")
    unequal = defined_unit()
    unequal["definition"]["endpoint"] = witness("CompoundQ")
    clipped = defined_unit()
    clipped["definition"]["bridge"] = witness("One unit was defined as 2 nmol CompoundQ")
    outside = defined_unit()
    outside["definition"]["endpoint_entity"] = outside["definition"]["definition_entity"]
    unicode_selector = number("\u03bc reference rate 8 U/mg", "8")
    correct_number = _number(unicode_selector, _Sources(read_source), "rate")
    assert correct_number["value"] == 8
    byte_selector = deepcopy(unicode_selector)
    byte_selector["number_start"] = len(unicode_selector["witness"]["quote"][:unicode_selector["number_start"]].encode())
    byte_selector["number_end"] = byte_selector["number_start"] + 1
    cases = [
        capture("equal_entity_but_different_endpoint_witness",
            lambda: _defined_unit(unequal, _Sources(read_source), endpoint),
            "defined_unit_endpoint_mismatch"),
        capture("bridge_clipped_before_time_basis",
            lambda: _defined_unit(clipped, _Sources(read_source), endpoint),
            "defined_unit_bridge_boundary_required"),
        capture("equal_entity_at_wrong_source_occurrence",
            lambda: _defined_unit(outside, _Sources(read_source), endpoint),
            "defined_unit_containment_required"),
        capture("utf8_byte_offset_used_inside_unicode_quote",
            lambda: _number(byte_selector, _Sources(read_source), "rate"),
            "literal_source_number_required"),
    ]
    schema = rate_source_population_schema()
    rendered = _schema(schema, "arguments")
    assert "Unicode" not in rendered and "UTF-8" not in rendered
    assert "exact same" not in rendered
    paths_without_description = []
    def visit(node, path):
        if isinstance(node, dict):
            if path.endswith((".number_start", ".number_end", ".start", ".end", ".endpoint",
                              ".endpoint_entity", ".definition_entity", ".bridge", ".clause")):
                if "description" not in node:
                    paths_without_description.append(path)
            for name, child in node.get("properties", {}).items():
                visit(child, path + "." + name)
            for index, branch in enumerate(node.get("anyOf", [])):
                visit(branch, path + f".anyOf[{index}]")
            if "items" in node:
                visit(node["items"], path + "[]")
    visit(schema, "arguments")
    receipt = {"synthetic_only": True, "source_bytes_sha256": hashlib.sha256(RAW).hexdigest(),
        "successful_defined_unit_values_umol_per_min_per_mg": [r["value"] for r in extraction["rows"]],
        "plain_U_per_mg_partial_values": [r["value"] for r in partial["rows"]],
        "failures": cases, "rendered_operand_schema_lacks_coordinate_and_endpoint_identity_explanation": True,
        "schema_paths_without_descriptions": paths_without_description,
        "unicode_character_selector": {k: unicode_selector[k] for k in ("number_start", "number_end")},
        "incorrect_utf8_inner_selector": {k: byte_selector[k] for k in ("number_start", "number_end")},
        "scope": "Pure synthetic reader/schema probes; no source truth, live-run diagnosis, or controller/credit claim"}
    with (HERE / "SYNTHETIC_RECEIPT_001.json").open("x") as stream:
        json.dump(receipt, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({key: receipt[key] for key in (
        "synthetic_only", "successful_defined_unit_values_umol_per_min_per_mg",
        "plain_U_per_mg_partial_values", "failures",
        "rendered_operand_schema_lacks_coordinate_and_endpoint_identity_explanation")}))


if __name__ == "__main__":
    main()
