"""Retain bounded synthetic035 inputs/results; never read a paper or run model."""
from copy import deepcopy
from pathlib import Path
import json
import runpy

from gene_annotation_episode.literature_optical_calculations import calculate_nadh_optical_rate
from gene_annotation_episode.literature_optical_inputs import read_optical_rate_operands


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).resolve().parent
helpers = runpy.run_path(str(ROOT / "tests/test_literature_optical_inputs.py"))


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


for case in ("matched_background", "component_omission", "static_signal", "qualified_coefficient", "unknown_covariance", "epsilon_only"):
    if case == "epsilon_only":
        text = "Synthetic extinction coefficient 5000 M^-1 cm^-1."
        selection, sources, reader, _ = helpers["fixture"](text, sample=None, blank=None, path=None, wavelength=None)
        selection["signal_kind"] = helpers["meaning"]("unknown", text)
    else:
        selection, sources, reader, _ = helpers["fixture"]()
        if case == "component_omission":
            selection["blank_role"] = helpers["meaning"]("component_omission", helpers["TEXT"])
        if case == "static_signal":
            selection["signal_kind"] = helpers["meaning"]("static_absorbance", helpers["TEXT"])
        if case == "qualified_coefficient":
            selection["calibration"]["epsilon"]["qualification"] = helpers["meaning"]("source_qualified_approximate", helpers["TEXT"])
        helpers["add_covariance"](selection, sources, reader, status="unknown" if case == "unknown_covariance" else "estimated")
    extraction = read_optical_rate_operands(selection, read_source=reader)
    directory = OUTPUT / "synthetic_examples" / case
    directory.mkdir(parents=True, exist_ok=True)
    dump(directory / "SELECTION.json", selection)
    dump(directory / "EXTRACTION.json", extraction)
    dump(directory / "EXISTING_CALCULATOR_RESULT.json", calculate_nadh_optical_rate(extraction["calculation_inputs"]))
    for index, (ref, source) in enumerate(sources.items()):
        filename = "SOURCE.txt" if index == 0 else "COVARIANCE.json"
        (directory / filename).write_bytes(source["content"])
    dump(directory / "SOURCE_ROSTER.json", [{"source_ref": ref, "artifact_ref": source["artifact_ref"],
        "filename": "SOURCE.txt" if i == 0 else "COVARIANCE.json"} for i, (ref, source) in enumerate(sources.items())])

print("Wrote six synthetic-only optical source/calculator examples.")
