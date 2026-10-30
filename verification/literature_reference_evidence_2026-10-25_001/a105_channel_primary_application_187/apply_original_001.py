"""Apply the current electrical reader to unmodified retained Fluc XML.

These are source selections made after the recorded scientific review/reset.
No numerical scientific value is passed as an operation argument. The caller
may supply the source reference created by its own authorized source store.
This is a local original-source application, not an episode binding or model run.
"""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys
import traceback


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / "research/experimental_scoring_review_2026-10-23/a105_transport_channel_case_174/source/elife-01084-v1.xml"
CORRECTION = SOURCE.with_name("elife-01700-v1.xml")
EXPECTED = "83867d6966a972f32899bdfe545c9952cb9d10393dc54d68dce29b6f4954b053"
EXPECTED_CORRECTION = "2d0a1031da67028b8aea68def663e7ca1a9287e8915844436568769d3a1d0bee"

sys.path.insert(0, str(ROOT))
from gene_annotation_episode.domain import identity
from gene_annotation_episode.literature_channel_inputs import (
    LITERAL_FIELDS, read_channel_inputs, channel_calculation_inputs,
)
from gene_annotation_episode.literature_channel_calculations import populate_channel_components


class OriginalSelections:
    def __init__(self, raw: bytes, source_ref: str):
        assert hashlib.sha256(raw).hexdigest() == EXPECTED
        self.raw, self.text, self.reference = raw, raw.decode("utf-8"), source_ref
        self.artifact = "artifact_" + EXPECTED

    def region(self, start: str, end: str):
        lower = self.text.index(start)
        upper = self.text.index(end, lower) + len(end)
        return lower, upper

    def witness(self, quote: str, region=None, *, after=0):
        lower, upper = (0, len(self.text)) if region is None else region
        start = self.text.index(quote, max(lower, after), upper)
        assert start + len(quote) <= upper
        return {"source_ref": self.reference, "representation": "original",
            "start": len(self.text[:start].encode("utf-8")),
            "end": len(self.text[:start + len(quote)].encode("utf-8")), "quote": quote}

    def interpreted(self, value, quotes=()):
        return {"value": value, "witnesses": [self.witness(q) for q in quotes]}

    def measurement(self, quote, number, unit, *, region=None, spread=None):
        witness = self.witness(quote, region)
        ns = quote.index(number)
        us = quote.index(unit, ns + len(number))
        start = witness["start"] + len(quote[:us].encode("utf-8"))
        unit_witness = {"source_ref": self.reference, "representation": "original",
            "start": start, "end": start + len(unit.encode("utf-8")), "quote": unit}
        if spread is None:
            spread_selection = None
            kind = {"value": "unknown", "witnesses": []}
        else:
            ss = quote.index(spread, ns + len(number))
            spread_selection = {"witness": deepcopy(witness), "number_start": ss,
                "number_end": ss + len(spread)}
            # The printed plus/minus statement supplies no named error type.
            # This is not a claim that the entire publication lacks a model.
            kind = {"value": "unspecified", "witnesses": [deepcopy(witness)]}
        return {"number": {"witness": witness, "number_start": ns, "number_end": ns + len(number)},
            "unit": unit_witness, "context": deepcopy(witness),
            "spread": spread_selection, "spread_kind": kind}

    def main(self):
        figure2 = self.region('<fig id="fig2"', "</fig>")
        figure3 = self.region('<fig id="fig3"', "</fig>")
        table1 = self.region('<table-wrap id="tbl1"', "</table-wrap>")
        current = "Most of these insertion-steps are 1.8 pA under these conditions, equivalent to 7 pS"
        applied = "current fluctuations (downward opening) were recorded at −200 mV."
        reversals = "Reversal potentials from 4–5 separate bilayers were 53 ± 1 mV and 119 ± 3 mV for salt-gradient and bi-ionic conditions, respectively."
        literals = {field: None for field in LITERAL_FIELDS}
        literals.update(
            organism=self.witness("E. coli", table1),
            molecule=self.witness("Fluc-Ec2"),
            construct=self.witness("Synthetic gene constructs for Fluc-Ec2, Fluc-Bpe, Fluc-La1, and Fluc-La2 were inserted into a pASK vector with a C-terminal LysC recognition site and hexahistidine tag (TRKAASLVPRGSGGHHHHHH)"),
            preparation=self.witness("Fluc-Ec2 reconstituted liposomes (0.1 µg/mg)", figure3),
            experimental_system=self.witness("planar bilayers under salt-gradient conditions", figure3),
            membrane=self.witness("using a POPE/POPG phospholipid mixture to form the bilayer"),
            ionic_conditions=self.witness("with 300 mM or 30 mM NaF, 15 mM Mops-NaOH pH 7, in the cis or trans chamber respectively, trans defined as electrical ground"),
            voltage_convention=self.witness("trans defined as electrical ground"),
            current_baseline=self.witness("zero current is defined as the mean level of the fully closed channel", figure3),
            conducting_unit=self.witness("precludes a definitive conclusion that the observed single-channel currents are mediated by a single pore rather than two in parallel"),
            endpoint=self.witness("ionic currents mediated by Fluc-Ec2 inserted into planar phospholipid bilayers"),
            intended_variable=self.witness("their appearance is strictly dependent on reconstituting Fluc protein into the liposomes"),
        )
        return {"source_ref": self.reference, "source_kind": "primary_source", "literals": literals,
            # The number of independent protein preparations for Figure3 is
            # not supplied by its bilayer/event counts. Do not borrow n=4.
            "arrangement_kind": {"value": "unknown", "witnesses": []},
            "current_kind": self.interpreted("current_step_magnitude", ["histogram of Fluc insertion-step amplitudes"]),
            "arrangement_relation": self.interpreted("same_electrical_arrangement_supported", [
                "Fluc-Ec2 reconstituted liposomes (0.1 µg/mg) were inserted into planar bilayers under salt-gradient conditions",
                "These channels display voltage-independent, anion-selective characteristics in harmony with the macroscopic currents reported above",
                reversals,
            ]),
            "measurements": {
                "current": self.measurement(current, "1.8", "pA"),
                "applied_voltage": self.measurement(applied, "−200", "mV", region=figure3),
                "reversal_voltage": self.measurement(reversals, "53", "mV", region=figure2, spread="1"),
                "reported_conductance": self.measurement(current, "7", "pS"),
            },
            "covariance_source_ref": None, "variance_status": "unknown", "variance_witnesses": []}

    def incompatible_biionic(self):
        arguments = self.main()
        figure2 = self.region('<fig id="fig2"', "</fig>")
        reversals = "Reversal potentials from 4–5 separate bilayers were 53 ± 1 mV and 119 ± 3 mV for salt-gradient and bi-ionic conditions, respectively."
        arguments["measurements"]["reversal_voltage"] = self.measurement(
            reversals, "119", "mV", region=figure2, spread="3")
        arguments["measurements"]["reversal_voltage"]["context"] = self.witness(
            "bi-ionic conditions (300 mM NaF//300 mM NaCl)")
        arguments["arrangement_relation"] = self.interpreted("different_electrical_arrangements", [
            "bi-ionic conditions (300 mM NaF//300 mM NaCl)",
            "planar bilayers under salt-gradient conditions",
        ])
        return arguments


def build_selections(raw, source_ref):
    """Generate original-byte selections using the caller's actual source ref."""
    source = OriginalSelections(raw, source_ref)
    return {"salt_gradient": source.main(), "incompatible_biionic_pairing": source.incompatible_biionic()}


def write(name, value):
    with (HERE / name).open("x") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def main():
    raw = SOURCE.read_bytes()
    correction = CORRECTION.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == EXPECTED
    assert hashlib.sha256(correction).hexdigest() == EXPECTED_CORRECTION
    reference = identity("source", {"provider": "retained_original_elife_xml",
        "doi": "10.7554/eLife.01084", "artifact_ref": "artifact_" + EXPECTED})
    source = OriginalSelections(raw, reference)
    selections = build_selections(raw, reference)
    write("SOURCE_NATIVE_SELECTIONS_001.json", selections)
    calls = []
    def read_source(ref, representation):
        assert ref == reference and representation == "original"
        calls.append({"source_ref": ref, "representation": representation})
        return {"artifact_ref": source.artifact, "content": raw}
    results = {}
    for name, arguments in selections.items():
        try:
            extraction = read_channel_inputs(arguments, read_source=read_source)
            sheet = populate_channel_components(channel_calculation_inputs(extraction))
            results[name] = {"status": "populated", "extraction": extraction, "sheet": sheet}
        except Exception as error:
            results[name] = {"status": "failed", "exception": type(error).__name__,
                "message": str(error), "traceback": traceback.format_exc()}
    write("APPLICATION_RESULTS_001.json", results)
    write("SOURCE_CUSTODY_001.json", {"original_path": str(SOURCE.relative_to(ROOT)),
        "original_sha256": EXPECTED, "original_bytes": len(raw), "original_doi": "10.7554/eLife.01084",
        "correction_path": str(CORRECTION.relative_to(ROOT)), "correction_sha256": EXPECTED_CORRECTION,
        "correction_bytes": len(correction), "correction_doi": "10.7554/eLife.01700",
        "license": "CC BY3.0", "source_ref": reference, "artifact_ref": source.artifact,
        "scientific_source_bytes_modified": False, "reader_calls": calls,
        "graph_digitization": False, "actual_model_execution": False,
        "episode_binding": False, "a105_adequacy_claim": False})
    good, contrast = results["salt_gradient"], results["incompatible_biionic_pairing"]
    assert good["status"] == "populated", good
    assert contrast["status"] == "populated", contrast
    cells = good["sheet"]["cells"]
    assert cells["chord_conductance"]["value"] == float(Fraction(1800, 253))
    assert cells["charge_equivalent_rate"]["value"] == float(Fraction("1.8e-12") / Fraction("1.602176634e-19"))
    assert cells["reported_conductance"]["value"] == 7
    assert cells["chord_conductance_variance"]["value"] is None
    assert good["extraction"]["measurement_keys"]["reversal_voltage"] != contrast["extraction"]["measurement_keys"]["reversal_voltage"]
    assert contrast["sheet"]["cells"]["reversal_voltage"]["value"] == 119
    assert contrast["sheet"]["cells"]["chord_conductance"]["unavailable_reason"] == "different_electrical_arrangements"
    write("APPLICATION_CHECKS_001.json", {"supported_source_points": {name: cells[name]["value"] for name in (
        "current", "applied_voltage", "reversal_voltage", "reported_conductance")},
        "nominal_chord_pS": cells["chord_conductance"]["value"],
        "charge_equivalents_per_s": cells["charge_equivalent_rate"]["value"],
        "variance": None, "spread_kind": good["extraction"]["measurements"]["reversal_voltage"]["spread_kind"]["value"],
        "biionic_reversal_mV": 119, "distinct_reversal_measurement_keys": True,
        "incompatible_chord_blocked": True, "source_units_accepted_without_normalizing_source": True,
        "independent_preparation_count_for_current_steps": None,
        "construct_tag_cleavage_for_electrical_traces": None,
        "ion_specific_flux": None, "pores_per_conducting_unit": None,
        "original_source_application_only": True, "actual_model_execution": False,
        "episode_integration": False, "a105_adequacy_claim": False})
    print(json.dumps({"source_points": [cells[name]["value"] for name in (
        "current", "applied_voltage", "reversal_voltage", "reported_conductance")],
        "nominal_chord_pS": cells["chord_conductance"]["value"], "contrast": "blocked"}))


if __name__ == "__main__":
    main()
