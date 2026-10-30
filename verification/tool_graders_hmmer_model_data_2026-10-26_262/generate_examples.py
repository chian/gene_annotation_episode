"""Retain full concrete extraction/components plus exact supplied native provenance.

This verification caller reads retained fixtures and writes examples. Neither
production pure function performs those reads/writes or executes native tools.
Run via run_verification.py ATTEMPT examples for the existing local limits.
"""
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path

from gene_annotation_episode.hmmer_model_data import extract_hmmer_models
from gene_annotation_episode.hmmer_model_calculations import calculate_hmmer_model_components

ROOT = Path(__file__).resolve().parents[2]
NATIVE = ROOT / "verification/tool_graders_hmmer_preparation_contracts_2026-10-26_259/native"
DEST = Path.cwd() / "examples"


def digest(path):
    data = path.read_bytes()
    return {"path": str(path), "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}


def save(name, value):
    path = DEST / name
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    return digest(path)


def main():
    DEST.mkdir()
    fixtures, artifacts, extracted, calculated = {}, {}, {}, {}
    cases = [(suffix, "hmmbuild_" + suffix, "profile.hmm", "hmmer3_ascii")
             for suffix in ("protein", "dna", "rna", "annotated", "singlemx")]
    cases += [("annotated_3" + revision, "hmmconvert_annotated_3" + revision,
               "stdout.log", "hmmer3_ascii") for revision in "abcdef"]
    cases += [(name, "hmmconvert_" + name, "stdout.log", format)
              for name, format in (("legacy2", "hmmer2_ascii"), ("binary", "hmmer_binary"))]
    for name, directory, filename, format in cases:
        path = NATIVE / directory / filename
        data = path.read_bytes()
        receipt_path = path.parent / "receipt.json"
        receipt = json.loads(receipt_path.read_text())
        fixtures[name] = {**digest(path), "receipt": digest(receipt_path),
            "native_argv": receipt["argv"], "native_returncode": receipt["returncode"],
            "native_executable_sha256": receipt["executable_sha256"], "native_policy": receipt["policy"],
            "selected_input": digest(Path(receipt["argv"][-1]))}
        occurrence = {"occurrence_id": "native/" + name + "/output/models/0", "direction": "output",
            "role": "models", "ordinal": 0, "artifact_ref": str(path.relative_to(ROOT)),
            "sha256": fixtures[name]["sha256"], "size_bytes": len(data), "completeness": "complete"}
        extraction = extract_hmmer_models(data, occurrence=occurrence, format=format)
        extracted[name] = extraction
        artifacts[name + "_extraction"] = save(name + "_extraction.json", extraction)
        if format == "hmmer3_ascii":
            symbols = extraction["records"][0]["alphabet"]["symbols"]
            uniform = {symbol: 1/len(symbols) for symbol in symbols}
            calculations = calculate_hmmer_model_components(extraction, background=uniform)
            calculated[name] = calculations
            artifacts[name + "_components"] = save(name + "_components_uniform.json", calculations)
    changed_background = {symbol: 0.1 if symbol in {"F", "Y"} else 0.8/18
                          for symbol in "ACDEFGHIKLMNPQRSTVWY"}
    changed = calculate_hmmer_model_components(extracted["protein"], background=changed_background,
                                              probability_tolerance=1e-8)
    artifacts["protein_changed"] = save("protein_components_changed.json", changed)
    baseline = calculated["protein"]["rows"][0]
    position = baseline["positions"][4]
    new_position = changed["rows"][0]["positions"][4]
    with localcontext() as context:
        context.prec = 60
        p = [(-Decimal(token)).exp() for token in ("0.40547", "1.09861")]
        entropy = -sum(value * value.ln()/Decimal(2).ln() for value in p)
        kl = sum(value * (value.ln()-Decimal("0.05").ln())/Decimal(2).ln() for value in p)
        independent = {"method": "60-digit decimal exp and natural logarithms of the two retained tokens",
            "F_probability": str(p[0]), "Y_probability": str(p[1]), "mass": str(sum(p)),
            "entropy_bits": str(entropy), "relative_entropy_bits_uniform": str(kl)}
    summary = {"fixture_identity": "native results from explicitly synthetic supplied alignments; no biological observations",
        "protein": {"native_source_sha256": fixtures["protein"]["sha256"],
            "length": baseline["declared_length"]["value"], "sequence_count": baseline["sequence_count"]["value"],
            "effective_sequence_count": baseline["effective_sequence_count"]["value"],
            "effective_sequence_ratio": baseline["effective_sequence_ratio"]["value"],
            "position_5": {"F": extracted["protein"]["records"][0]["positions"][4]["match"]["cells"][4],
                "Y": extracted["protein"]["records"][0]["positions"][4]["match"]["cells"][19],
                "mass": position["match"]["mass"]["value"], "mass_residual": position["match"]["mass_residual"]["value"],
                "entropy_bits": position["entropy"]["value"],
                "relative_entropy_bits_uniform": position["relative_entropy"]["value"],
                "relative_entropy_bits_changed": new_position["relative_entropy"]["value"]},
            "mean_match_entropy_bits": baseline["mean_match_entropy"]["value"],
            "mean_match_relative_entropy_bits_uniform": baseline["mean_match_relative_entropy"]["value"],
            "initial_transition_group_mass": {group: item["mass"]["value"] for group, item in baseline["initial"]["transitions"].items()},
            "initial_transition_group_residual": {group: item["mass_residual"]["value"] for group, item in baseline["initial"]["transitions"].items()},
            "mass_checks_failed_tolerance_1e4": sum(check["code"] == "probability_mass" and check["state"] == "fail" for check in calculated["protein"]["checks"]),
            "mass_checks_failed_tolerance_1e8": sum(check["code"] == "probability_mass" and check["state"] == "fail" for check in changed["checks"]),
            "independent_expectations": independent},
        "nucleotides": {name: {"source_sha256": fixtures[name]["sha256"],
            "mean_match_entropy_bits": calculated[name]["rows"][0]["mean_match_entropy"]["value"],
            "mean_match_relative_entropy_bits_uniform": calculated[name]["rows"][0]["mean_match_relative_entropy"]["value"],
            "maximum_length": extracted[name]["records"][0]["maximum_length"]} for name in ("dna", "rna")},
        "changed_parameters": changed["parameters"],
        "unsupported_populations": {name: extracted[name]["population"] for name in ("legacy2", "binary")}}
    artifacts["summary"] = save("summary.json", summary)
    authorities = [ROOT / "resources/software/infernal-1.1.5/hmmer/src/p7_hmmfile.c",
        ROOT / "gene_annotation_episode/hmmer_model_data.py", ROOT / "gene_annotation_episode/hmmer_model_calculations.py"]
    save("provenance.json", {"authorities_and_implementation": [digest(path) for path in authorities],
        "native_fixtures": fixtures, "generated_artifacts": artifacts,
        "verification_scope": {"source_inspected": "complete WriteASCII and read_asc30hmm paths in p7_hmmfile.c",
            "native_live_executions": "workload259 receipts reused; no new native HMMER execution by262",
            "production_result_path": "not implemented or claimed by this component",
            "episode_communication": "not verified by this component"}})
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
