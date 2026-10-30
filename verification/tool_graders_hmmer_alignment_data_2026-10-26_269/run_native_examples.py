"""Run explicit tiny native checks with retained inputs/outputs and limits."""
import hashlib
import json
from pathlib import Path

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job
from gene_annotation_episode.hmmer_alignment_preparation_data import populate_hmmer_alignment_preparation_sheet
from gene_annotation_episode.hmmer_alignment_preparation_calculations import (
    calculate_hmmer_alignment_preparation_components, reconstruct_alimask_model_map,
)

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PROGRAM = ROOT / "resources/software/infernal-1.1.5/hmmer/src/alimask"
POLICY = LocalJobPolicy(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None)


def payload(role, content, direction):
    return {"content": content, "occurrence": {"occurrence_id": f"{direction}:{role}:0", "direction": direction,
        "role": role, "ordinal": 0, "artifact_ref": "retained:" + role, "sha256": hashlib.sha256(content).hexdigest(),
        "size_bytes": len(content), "completeness": "complete"}}


def run(name, source, mode, settings, expected_returncode=0):
    directory = HERE / "native" / name
    if (directory / "receipt.json").exists():
        # Resume this verification script after a harness assertion, never
        # repeat a recorded native invocation or overwrite its evidence.
        receipt = json.loads((directory / "receipt.json").read_text())
        assert receipt["input_sha256"] == hashlib.sha256(source).hexdigest()
        assert receipt["returncode"] == receipt["expected_returncode"] == expected_returncode
        return json.loads((directory / "calculations.json").read_text()), (directory / "stdout.log").read_text() + (directory / "stderr.log").read_text()
    directory.mkdir(parents=True, exist_ok=False)
    original = directory / "input.sto"
    original.write_bytes(source)
    argv = [str(PROGRAM)]
    for flag, value in settings.items():
        if value is True:
            argv.append(flag)
        elif value is not False and value is not None:
            argv.extend([flag, str(value)])
    argv.append(str(original))
    if mode.startswith("mask_"):
        argv.append(str(directory / "output.sto"))
    intent = {"argv": argv, "policy": POLICY.to_dict(), "input_sha256": hashlib.sha256(source).hexdigest(),
        "executable_sha256": hashlib.sha256(PROGRAM.read_bytes()).hexdigest(), "expected_returncode": expected_returncode}
    (directory / "intent.json").write_text(json.dumps(intent, indent=2) + "\n")
    native = run_local_job(argv, cwd=directory, policy=POLICY,
        env={"PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(directory), "XDG_CACHE_HOME": str(directory / "cache")})
    receipt = {**intent, "returncode": native.returncode, "metadata": native.metadata,
               "stdout_path": str(native.stdout_path), "stderr_path": str(native.stderr_path)}
    (directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    assert native.returncode == expected_returncode, name
    output = {"stdout": [payload("stdout", native.stdout_path.read_bytes(), "output")],
              "stderr": [payload("stderr", native.stderr_path.read_bytes(), "output")]}
    if (directory / "output.sto").exists():
        output["masked_alignment"] = [payload("masked_alignment", (directory / "output.sto").read_bytes(), "output")]
    sheet = populate_hmmer_alignment_preparation_sheet(operation={"program": "alimask", "mode": mode,
        "engine_version": "3.4", "settings": settings}, inputs={"alignment": [payload("alignment", source, "input")]}, outputs=output)
    calculated = calculate_hmmer_alignment_preparation_components(sheet)
    (directory / "sheet.json").write_text(json.dumps(sheet, indent=2) + "\n")
    (directory / "calculations.json").write_text(json.dumps(calculated, indent=2) + "\n")
    return calculated, native.stdout_path.read_text() + native.stderr_path.read_text()


def main():
    examples = []
    source = b"# STOCKHOLM 1.0\na ACD-EF\n#=GC RF xx..xx\n//\n"
    result, _ = run("hand_insert_span", source, "mask_model", {"--amino": True, "--hand": True, "--modelrange": "2-3"})
    assert result["rows"][0]["components"]["actual_masked_count"]["value"] == 4
    assert next(item for item in result["checks"] if item["code"] == "mask_annotation")["state"] == "pass"
    examples.append({"case": "hand_insert_span", "masked_count": 4, "denominator": 6})
    adjusted = b"# STOCKHOLM 1.0\na ACDEFG\n#=GC RF .x..x.\n//\n"
    result, _ = run("hand_adjusted_and_nomap", adjusted, "alignment_to_model", {"--amino": True, "--hand": True, "--ali2model": "1-6,3-4"})
    assert next(item for item in result["checks"] if item["code"] == "native_mapping")["state"] == "pass"
    examples.append({"case": "hand_adjusted_and_nomap", "mappings": result["rows"][0]["native_mappings"]})
    gappy = b"# STOCKHOLM 1.0\n#=GS a WT 0.1\n#=GS b WT 2.5\n#=GS c WT 1.4\na aC..GT--\nb ACU-GT~~\nc --iNGT**\n#=GC RF xx..xxxx\n//\n"
    for weighting in ("--wnone", "--wgiven", "--wpb"):
        settings = {"--dna": True, "--fast": True, weighting: True, "--symfrac": .6, "--fragthresh": .5}
        draft = populate_hmmer_alignment_preparation_sheet(operation={"program": "alimask", "mode": "model_to_alignment",
            "engine_version": "3.4", "settings": {**settings, "--model2ali": "1-1"}}, inputs={"alignment": [payload("alignment", gappy, "input")]}, outputs={})
        mapping = reconstruct_alimask_model_map(draft["input_records"][0], settings=settings)["map"]
        assert mapping
        settings["--model2ali"] = ",".join(f"{i}-{i}" for i in range(1, len(mapping) + 1))
        result, _ = run("fast_" + weighting[2:], gappy, "model_to_alignment", settings)
        assert next(item for item in result["checks"] if item["code"] == "native_mapping")["state"] == "pass"
        _, stdout = run("fast_" + weighting[2:] + "_length_boundary", gappy, "model_to_alignment", {**settings, "--model2ali": str(len(mapping) + 1) + "-" + str(len(mapping) + 1)}, 1)
        assert "exceeds computed model length " + str(len(mapping)) in stdout
        examples.append({"case": "fast_" + weighting[2:], "map": mapping, "reconstruction": result["rows"][0]["reconstruction"]})
    oldmask = b"# STOCKHOLM 1.0\na ACDEFG\n#=GC MM m.m...\n//\n"
    for append, expected in ((False, ".mmm.."), (True, "mmmm..")):
        result, _ = run("mask_append" if append else "mask_replace", oldmask, "mask_alignment", {"--amino": True, "--alirange": "2-4,3-4", "--appendmask": append})
        assert result["rows"][0]["output_mm"] == expected
        assert next(item for item in result["checks"] if item["code"] == "mask_annotation")["state"] == "pass"
        examples.append({"case": "mask_append" if append else "mask_replace", "components": result["rows"][0]["components"]})
    _, _ = run("hand_missing_rf", oldmask, "mask_model", {"--amino": True, "--hand": True, "--modelrange": "1-1"}, 1)
    (HERE / "LIVE_EXAMPLES.json").write_text(json.dumps(examples, indent=2) + "\n")
    print(json.dumps({"native_invocations": 11, "expected_successes": 7, "expected_failures": 4, "all_assertions_passed": True}))


if __name__ == "__main__":
    main()
