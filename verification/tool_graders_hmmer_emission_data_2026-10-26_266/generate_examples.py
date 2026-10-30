"""Retain full pure-sheet examples from workload259; never run hmmemit."""
from copy import deepcopy
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.hmmer_model_data import extract_hmmer_models
from gene_annotation_episode.hmmer_emission_data import populate_hmmemit_sheet
from gene_annotation_episode.hmmer_emission_calculations import calculate_hmmemit_components

NATIVE = ROOT / "verification/tool_graders_hmmer_preparation_contracts_2026-10-26_259/native"
HERE = Path(__file__).resolve().parent
OUTPUT = Path.cwd() / "examples"
OUTPUT.mkdir()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    (OUTPUT / (name+".json")).write_text(json.dumps(value, indent=2, allow_nan=False)+"\n")


def payload(path, role, direction):
    content = path.read_bytes()
    return {"occurrence": {"occurrence_id": f"{direction}:{role}", "direction": direction,
        "role": role, "ordinal": 0, "artifact_ref": str(path.relative_to(ROOT)),
        "sha256": hashlib.sha256(content).hexdigest(), "size_bytes": len(content), "completeness": "complete"},
        "content": content}


def settings_from_receipt(receipt):
    arguments = iter(receipt["argv"][1:-1])
    settings = {}
    for argument in arguments:
        if argument in {"-N", "--seed", "-L"}:
            settings[argument] = int(next(arguments))
        elif argument in {"--minl", "--minu"}:
            settings[argument] = float(next(arguments))
        else:
            settings[argument] = True
    return settings


def main():
    modes = {"core": "sample_core_unaligned", "alignment": "sample_core_aligned",
        "consensus": "consensus_simple", "fancy": "consensus_thresholded",
        **{f"profile_{style}": "sample_profile" for style in ("local", "unilocal", "glocal", "uniglocal")}}
    expected_lengths = {"core": [12, 12, 12], "alignment": [12, 12, 12], "consensus": [12], "fancy": [12],
                        "profile_local": [15, 72, 39], "profile_unilocal": [85, 31, 21],
                        "profile_glocal": [92, 37, 30], "profile_uniglocal": [100, 31, 17]}
    provenance, summary = {}, {}
    for style, mode in modes.items():
        directory = NATIVE / ("hmmemit_"+style)
        receipt_path = directory / "receipt.json"
        receipt = json.loads(receipt_path.read_text())
        model_path = Path(receipt["argv"][-1])
        model = payload(model_path, "models", "input")
        role = "generated_alignment" if style == "alignment" else "generated_sequences"
        operation = {"program": "hmmemit", "mode": mode, "engine_version": "3.4", "settings": settings_from_receipt(receipt)}
        sheet = populate_hmmemit_sheet(operation=operation, inputs={"models": [model]},
            outputs={role: [payload(directory / "stdout.log", role, "output")],
                     "stdout": [payload(directory / "stdout.log", "stdout", "output")],
                     "stderr": [payload(directory / "stderr.log", "stderr", "output")]},
            model_extraction=extract_hmmer_models(model["content"], occurrence=model["occurrence"], format="hmmer3_ascii"))
        calculated = calculate_hmmemit_components(sheet)
        generated = [r for r in calculated["rows"] if r["kind"] == "generated_record"]
        assert [r["length"]["value"] for r in generated] == expected_lengths[style]
        assert not sheet["issues"] and not calculated["issues"]
        save(style+"_sheet", sheet)
        save(style+"_components", calculated)
        summary[style] = {"actual_sequences": [r["sequence"] for r in generated],
            "independent_expected_lengths": expected_lengths[style],
            "model_components": next(r for r in calculated["rows"] if r["kind"] == "model"),
            "checks": calculated["checks"]}
        provenance[style] = {"kind": "retained_native_output_from_synthetic_input_alignment",
            "receipt": str(receipt_path.relative_to(ROOT)), "receipt_sha256": digest(receipt_path),
            "argv": receipt["argv"], "returncode": receipt["returncode"],
            "executable_sha256": receipt["executable_sha256"], "policy": receipt["policy"],
            "input_model": str(model_path.relative_to(ROOT)), "input_model_sha256": digest(model_path),
            "stdout_sha256": digest(directory / "stdout.log"), "stderr_sha256": digest(directory / "stderr.log"),
            "operation_settings_provenance": "explicit options in retained argv; omitted native defaults remain unknown"}
        if style == "fancy":
            saved = json.loads(json.dumps(sheet))
            changed = calculate_hmmemit_components(saved, parameters={"consensus_thresholds": {"minl": 0.6, "minu": 0.9}, "probability_rounding_tolerance": 1e-5})
            near = calculate_hmmemit_components(saved, parameters={"consensus_thresholds": {"minl": 2/3, "minu": 0.9}, "probability_rounding_tolerance": 1e-5})
            assert saved == sheet
            save("fancy_recalculated_thresholds", changed)
            save("fancy_near_threshold", near)
            summary["recalculation"] = {
                "changed": next(r for r in changed["rows"] if r["kind"] == "consensus"),
                "near_threshold": next(r for r in near["rows"] if r["kind"] == "consensus")}
    with localcontext() as context:
        context.prec = 60
        summary["independent_position5_max_probability"] = str((-Decimal("0.40547")).exp())
    source_paths = [ROOT / "gene_annotation_episode/hmmer_emission_data.py",
        ROOT / "gene_annotation_episode/hmmer_emission_calculations.py",
        ROOT / "gene_annotation_episode/hmmer_model_data.py",
        ROOT / "gene_annotation_episode/hmmalign_inputs.py",
        ROOT / "tests/test_hmmer_emission_data.py", ROOT / "tests/test_hmmer_emission_calculations.py",
        ROOT / "resources/software/infernal-1.1.5/hmmer/src/hmmemit.c",
        ROOT / "resources/software/infernal-1.1.5/hmmer/src/emit.c",
        HERE / "generate_examples.py", HERE / "run_verification.py"]
    provenance["sources"] = {str(p.relative_to(ROOT)): digest(p) for p in source_paths}
    save("provenance", provenance)
    save("summary", summary)
    print(json.dumps({"examples": str(OUTPUT), "native_modes": list(modes),
        "core_total_length": 36, "local_profile_actual_lengths": [15, 72, 39],
        "configured_profile_expected_length": 20, "consensus": "ACDEFGHIKLMN",
        "thresholded_consensus": "ACDExGHIKLMN", "changed_threshold_consensus": "ACDEfGHIKLMN"}))


if __name__ == "__main__":
    main()
