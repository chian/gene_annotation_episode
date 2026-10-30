"""Retain definitions, qualifications and hashes for the bounded application."""
from pathlib import Path
import hashlib
import json
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from apply_original_001 import OriginalSelections, SOURCE, CORRECTION, EXPECTED, EXPECTED_CORRECTION, ROOT


def write(name, data):
    with (HERE / name).open("x") as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def main():
    custody = json.loads((HERE / "SOURCE_CUSTODY_001.json").read_text())
    results = json.loads((HERE / "APPLICATION_RESULTS_001.json").read_text())
    source = OriginalSelections(SOURCE.read_bytes(), custody["source_ref"])
    witness = source.witness
    table = source.region('<table-wrap id="tbl1"', '</table-wrap>')
    definitions = {
        "reference_molecule": {"label": "Fluc-Ec2", "accession": "YP_001481330.1",
            "source_organism": "E. coli virulence plasmid",
            "witness": witness('<td>Ec2</td><td><italic>E. coli</italic> virulence plasmid</td><td>YP_001481330.1</td>', table)},
        "expression_host": {"label": "E. coli BL21-DE3",
            "witness": witness('<italic>E. coli</italic> (BL21-DE3) transformed with the pASK-IBA2 plasmid bearing Fluc constructs')},
        "construct": {"reported_tail": "TRKAASLVPRGSGGHHHHHH",
            "witness": witness('Synthetic gene constructs for Fluc-Ec2, Fluc-Bpe, Fluc-La1, and Fluc-La2 were inserted into a pASK vector with a C-terminal LysC recognition site and hexahistidine tag (TRKAASLVPRGSGGHHHHHH)'),
            "electrical_trace_tag_cleavage_state": None, "exact_native_construct_boundaries": None,
            "active_fraction": None,
            "qualification": "The listed constructs are distinct proteins; their shared methods sentence does not show coexistence in this Ec2 current measurement."},
        "current_measurement": {"meaning": "dominant insertion-step magnitude, not a preparation mean or time-averaged current",
            "witness": witness('Most of these insertion-steps are 1.8 pA under these conditions, equivalent to 7 pS'),
            "preparation": "Fluc-Ec2 liposomes 0.1 microgram protein/mg lipid; planar POPE/POPG bilayer",
            "baseline_witness": witness('zero current is defined as the mean level of the fully closed channel'),
            "baseline_qualification": "A defined closed-channel baseline does not quantify a protein-free bilayer background contribution."},
        "salt_conditions": {"witness": witness('with 300 mM or 30 mM NaF, 15 mM Mops-NaOH pH 7, in the cis or trans chamber respectively, trans defined as electrical ground'),
            "concentration_ratio": "300/30 nominal concentration; the source separately describes an eightfold ionic activity gradient",
            "activity_witness": witness('the eightfold ionic activity gradient'),
            "reversal_applies_to_current": "source-supported conditional interpretation across the stated salt-gradient arrangement, not a paired same-bilayer observation"},
        "sampling": {"step_events_reported": 63, "bilayers_reported_approximate": "about50",
            "witness": witness('first-insertion current histograms for 63 separate insertion events taken from ∼50 bilayers'),
            "reversal_bilayers_reported": "4–5",
            "reversal_witness": witness('Reversal potentials from 4–5 separate bilayers were 53 ± 1 mV and 119 ± 3 mV for salt-gradient and bi-ionic conditions, respectively.'),
            "independent_protein_preparations_for_current_steps": None,
            "qualification": "Counts of insertion events and bilayers are not counts of independent protein preparations. The separate four-preparation Poisson-dump experiment is not borrowed."},
        "unit_assignment": {"pores_per_conducting_unit": None,
            "witness": witness('precludes a definitive conclusion that the observed single-channel currents are mediated by a single pore rather than two in parallel'),
            "qualification": "No per-pore or per-polypeptide normalization is performed."},
        "author_reported_inferred_ion_turnover": {"reported_approximate_order": "approximately10^7 fluoride ions/second at−200mV",
            "witness": witness('with single-molecule turnover of ∼10<sup>7</sup> F<sup>−</sup> ions/sec at −200 mV'),
            "measurement_kind": "source interpretation of unitary electrical current under ion/unit assignments",
            "implemented_numerical_cell": None,
            "qualification": "Preserved as a source inference; the implemented charge-equivalent cell is not silently relabeled as experimentally isolated fluoride flux."},
        "biionic_contrast": {"witness": witness('bi-ionic conditions (300 mM NaF//300 mM NaCl)'),
            "contrast_kind": "constructed incompatible pairing of two reported measurements, not a new experiment or synthetic measurement",
            "effect": "The119mV source point and its own physical key survive, while the inappropriate salt-current/biionic-reversal chord is unavailable."},
        "formal_correction": {"doi": "10.7554/eLife.01700", "sha256": EXPECTED_CORRECTION,
            "meaning": "The correction swaps La1/La2 labels for specified Figure1A sequence rows; it is not a new experiment and does not change the selected Ec2 electrical quantities.",
            "target_correspondence_or_homology_scoring": False},
    }
    write("EXPERIMENTAL_DEFINITIONS_001.json", definitions)
    main_cells = results["salt_gradient"]["sheet"]["cells"]
    contrast_cells = results["incompatible_biionic_pairing"]["sheet"]["cells"]
    components = {name: {field: row[field] for field in ("value", "unit", "status", "unavailable_reason", "formula", "section", "meaning", "conditional_on", "measurement_keys")}
                  for name, row in main_cells.items()}
    write("NUMERICAL_COMPONENTS_001.json", {"main": components,
        "biionic_contrast": {name: contrast_cells[name] for name in ("reversal_voltage", "chord_conductance")},
        "reported_and_derived_conductance_are_not_independent": True,
        "displayed_tokens_are_not_exact_physical_values": True,
        "chord_is_nominal_conditional_arithmetic_not_an_IV_slope": True,
        "spread_kind_is_unspecified_not_known_variance": True,
        "overall_reliability_grade": None, "annotation_credit": None})
    runtime = ["gene_annotation_episode/literature_channel_inputs.py",
               "gene_annotation_episode/literature_channel_calculations.py",
               "gene_annotation_episode/literature_channel_prompt.py",
               "gene_annotation_episode/literature_assay_inputs.py",
               "gene_annotation_episode/literature_partner_source_fields.py",
               "gene_annotation_episode/literature_experimental_contracts.py",
               "gene_annotation_episode/domain.py"]
    write("RUNTIME_HASHES_001.json", {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in runtime})
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == EXPECTED
    assert hashlib.sha256(CORRECTION.read_bytes()).hexdigest() == EXPECTED_CORRECTION
    print(json.dumps({"original_source_intact": True, "source_defined_components": len(components),
        "new_production_files_edited": 0, "episode_binding": False}))


if __name__ == "__main__":
    main()
