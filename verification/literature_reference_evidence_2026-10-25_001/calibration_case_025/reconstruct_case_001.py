"""Research-only source arithmetic and existing-reader checks; no Store or model.

The source label below is a research inventory key, not a claimed application
record. The parser/calculator are imported from the immutable 023 snapshot.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import sys


OUTPUT = Path(__file__).resolve().parent
ROOT = OUTPUT.parents[2]
PIN = OUTPUT.parent / "literature_model_run_023/pin_001"
sys.path.insert(0, str(PIN))
sys.dont_write_bytecode = True

from gene_annotation_episode import literature_assay_inputs as reader
from gene_annotation_episode import literature_activity_calculations as calculator


SOURCE = Path("/tmp/episode-published-cases/specificity/raw/PMC12051542.txt")
HTML = SOURCE.with_suffix(".html")
SOURCE_KEY = "retained_primary_PMC12051542_research025"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_new(name, value):
    with (OUTPUT / name).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def main():
    reset = json.loads((OUTPUT / "RESET_AFTER_SELECTED_PAPER_001.json").read_bytes())
    assert reset["full_documents_read"]
    scope = json.loads((OUTPUT / "PRIMARY_READ_SCOPE_001.json").read_bytes())
    for source in scope["source_paths"]:
        assert sha(Path(source["path"])) == source["sha256"]
    raw = SOURCE.read_bytes()

    def witness(quote):
        token = quote.encode()
        assert raw.count(token) == 1, quote
        start = raw.index(token)
        return {"source_ref": SOURCE_KEY, "representation": "text",
                "start": start, "end": start + len(token), "quote": quote}

    def part(outer, token):
        position = outer["quote"].index(token)
        start = outer["start"] + len(outer["quote"][:position].encode())
        return {**outer, "start": start, "end": start + len(token.encode()), "quote": token}

    def exact_number(quote, token):
        selected = witness(quote)
        return {"witness": selected, "number_token": part(selected, token),
                "value": Fraction(token)}

    source_witnesses = {}
    onepot = witness("8.4 μM HFP and 8.8 μM IMP")
    for side, token in (("HFP", "8.4"), ("IMP", "8.8")):
        source_witnesses[side + "_nominal_concentration"] = part(onepot, token + " μM")
    total = exact_number("7 mg/ml per Bradford analysis", "7")
    target = exact_number("an approximate concentration of 5 mg/ml HFP", "5")
    source_witnesses["stock_total_Bradford"] = total["witness"]
    source_witnesses["stock_target_gel_estimate"] = target["witness"]
    control_panel = witness("Four of the five samples demonstrated isomerase activity")
    source_witnesses["positive_control_panel"] = control_panel
    words = {"four": 4, "five": 5}
    count_positive, count_examined = (words[word.lower()] for word in ("Four", "five"))
    duration = witness(">18 h as opposed to <10 min")
    source_witnesses["equilibrium_time_contrast"] = duration
    assert "Four" in control_panel["quote"] and "five" in control_panel["quote"]
    assert duration["quote"] == ">18 h as opposed to <10 min"
    duration_tokens = re.fullmatch(r">([0-9]+) h as opposed to <([0-9]+) min", duration["quote"])
    assert duration_tokens
    time_ratio_bound = Fraction(duration_tokens[1]) * 60 / Fraction(duration_tokens[2])

    # These are descriptive source components, with their scientific scope
    # declared below. No scalar overall-reliability score is computed.
    ratio = target["value"] / total["value"]
    hfp_amount, imp_amount = (Fraction(source_witnesses[side + "_nominal_concentration"]["quote"].split()[0])
                              for side in ("HFP", "IMP"))
    descriptive = {
        "nominal_target_mass_to_total_estimate": {
            "value": float(ratio), "formula": "5/7", "unit": "fraction",
            "origin": "derived", "approximate": True,
            "meaning": "Target-mass estimate divided by Bradford total-protein estimate for the described stock; not validated purity or active fraction.",
            "uncertainty": None, "measurement_methods": ["visual_SDS_PAGE_estimate", "Bradford"],
        },
        "conditional_mass_denominator_factor": {
            "value": float(1 / ratio), "formula": "7/5", "unit": "dimensionless",
            "origin": "derived", "application_status": "proposed_conditional_not_applied", "approximate": True,
            "meaning": "Would rescale a same-stock per-total-mass rate to per-estimated-target-mass only if the two mass estimates and sample linkage are valid. No rate is supplied or corrected here.",
        },
        "onepot_nominal_HFP_to_IMP_amount": {
            "value": float(hfp_amount / imp_amount), "formula": "8.4/8.8", "unit": "fraction",
            "origin": "derived", "meaning": "Between-arm nominal molar amount difference accompanying the changed phosphatase identity; not an activity or recovery ratio.",
            "uncertainty": None,
        },
        "control_panel_isomerization_positive_fraction": {
            "value": count_positive / count_examined, "numerator": count_positive,
            "denominator": count_examined, "formula": "4/5", "unit": "fraction",
            "origin": "derived", "meaning": "Observed positive fraction in this five-preparation control panel; not a false-positive probability or confidence score for HFP.",
            "biological_independence": "unknown", "sampling_confidence_interval": None,
        },
        "reported_equilibrium_time_ratio_lower_bound": {
            "value": float(time_ratio_bound), "bound": "gt", "formula": "(18*60)/10", "unit": "dimensionless",
            "origin": "derived", "meaning": "Bound on reported elapsed equilibrium times across differently prepared samples; not a kinetic or specific-activity ratio.",
        },
    }
    calls = []

    def read_source(reference, representation):
        assert reference == SOURCE_KEY
        selected = HTML if representation == "original" else SOURCE
        return {"artifact_ref": "artifact_" + sha(selected), "content": selected.read_bytes()}

    endpoint_witness = witness("The riboflavin content of the flasks was determined spectrophotometrically as in the screening protocol above.")
    for side, token in (("HFP", "8.4"), ("IMP", "8.8")):
        amount_witness = source_witnesses[side + "_nominal_concentration"]
        assay = {name: None for name in reader.ASSAY_LITERAL_FIELDS}
        assay["molecule"] = part(onepot, side)
        assay["condition"] = witness("55 °C for 4.5 h")
        assay["measured_entity"] = endpoint_witness
        assay["endpoint"] = {"value": "other_measured_endpoint", "witnesses": [endpoint_witness]}
        assay["arrangement"] = {"value": "replacement", "witnesses": [onepot]}
        primitives = {role: None for role in reader.PRIMITIVE_ORDER}
        primitives["E"] = {"witness": amount_witness, "number_start": 0,
            "number_end": len(token), "unit_start": len(token) + 1,
            "unit_end": len(amount_witness["quote"])}
        arguments = {"source_ref": SOURCE_KEY, "source_kind": "primary_source", "assay": assay,
            "primitives": primitives, "covariance_source_ref": None,
            "distinct_residual_variance": None, "variance_status": "unknown",
            "observation_model": "none", "model_witnesses": []}
        extracted = reader.read_assay_inputs(deepcopy(arguments), read_source=read_source)
        result = calculator.populate_corrected_activity({key: extracted[key] for key in (
            "values", "covariance", "variance_status", "distinct_residual_variance", "observation_model")})
        assert extracted["values"]["E"] == float(token)
        assert all(value is None for key, value in extracted["values"].items() if key != "E")
        assert all(cell["value"] is None and cell["unavailable_reason"] == "correction_inputs_unreported"
                   for cell in result["cells"].values())
        calls.append({"arm": side, "arguments": arguments, "extraction": extracted,
                      "existing_calculator_result": result,
                      "qualification": "Reported nominal amount, not a measured active-site concentration or an uncertainty-free denominator.",
                      "repository_not_invoked": True,
                      "repository_endpoint_guard_from_inspected_code": "endpoint_requires_different_model"})

    imports = []
    for module in (reader, calculator):
        path = Path(module.__file__).resolve()
        assert path.is_relative_to(PIN)
        imports.append({"module": module.__name__, "path": str(path), "sha256": sha(path)})
    save_new("SOURCE_WITNESSES_001.json", {"source_inventory_key": SOURCE_KEY,
        "meaning": "Research file inventory key, not an application SourceRecord identity.",
        "original_html_sha256": sha(HTML), "text_projection_sha256": sha(SOURCE),
        "witnesses": source_witnesses})
    save_new("NUMERICAL_COMPONENTS_001.json", descriptive)
    save_new("EXISTING_READER_CHECK_001.json", {"status": "passed",
        "source": "one retained primary paper; researcher-selected source spans",
        "implementation_snapshot": str(PIN), "imports": imports, "checks": calls,
        "model_backed": False, "Store_created": False, "runtime_observations_created": 0,
        "new_production_reader_or_scoring_implementation": False})
    print(json.dumps({"status": "passed", "existing_reader_arms": len(calls),
                      "nominal_amounts_uM": [c["extraction"]["values"]["E"] for c in calls],
                      "corrected_activities": [c["existing_calculator_result"]["cells"]["corrected_activity"]["value"] for c in calls],
                      "descriptive_components": len(descriptive), "runtime_observations": 0}))


if __name__ == "__main__":
    main()
