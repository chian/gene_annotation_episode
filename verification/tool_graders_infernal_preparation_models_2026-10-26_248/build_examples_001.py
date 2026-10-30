"""Persist real populated sheets for every A mode through root's pure worker."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
OLD = ROOT / "verification/tool_graders_infernal_preparation_boundaries_2026-10-26_246/native"
OWN = BASE / "native"


def save(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False)+"\n")


def payload(path, case, role, fmt):
    content = path.read_bytes()
    return {"artifact": {"role": role, "format": fmt, "artifact_ref": case+"/"+role,
        "sha256": hashlib.sha256(content).hexdigest(), "size_bytes": len(content), "completeness": "complete"},
        "content": content}


def build():
    from gene_annotation_episode.native_infernal_preparation_worker import grade_infernal_preparation, recalculate_infernal_preparation
    destination = BASE / "examples"
    destination.mkdir(exist_ok=False)
    cases = []
    for mode, native, fmt, role in (
        ("ascii", "ascii", "infernal_cm_ascii", "converted_models"),
        ("binary", "binary", "infernal_cm_binary", "converted_models"),
        ("legacy_ascii", "legacy", "infernal_cm_legacy_ascii", "converted_models"),
        ("maximum_likelihood_hmm", "ml_hmm", "hmmer_hmm_ascii", "converted_hmms"),
        ("filter_hmm", "filter_hmm", "hmmer_hmm_ascii", "converted_hmms")):
        cases.append((OLD, "cmconvert_"+native, "cmconvert", mode, "model.cm", {}, [(role, "converted.out", fmt)]))
    cases.extend([
        (OLD, "cmfetch_single", "cmfetch", "single_key", "models.cm", {"key": "tRNA5"}, [("fetched_models", "fetched.cm", "infernal_cm_ascii")]),
        (OLD, "cmfetch_missing_unindexed", "cmfetch", "key_file", "models.cm", {"-f": True}, [("fetched_models", "fetched.cm", "infernal_cm_ascii")]),
        (OLD, "cmfetch_index", "cmfetch", "index", "models.cm", {"--index": True}, [("ssi", "models.cm.ssi", "infernal_ssi")]),
        (OWN, "cmfetch_missing_all_unindexed", "cmfetch", "key_file", "models.cm", {"-f": True}, [("fetched_models", "fetched.cm", "infernal_cm_ascii")]),
        (OLD, "cmpress_uncalibrated", "cmpress", "press", "model.cm", {}, [(r, "model.cm."+r, f) for r,f in (
            ("i1m", "infernal_cm_binary"), ("i1i", "infernal_ssi"), ("i1f", "infernal_i1f"), ("i1p", "infernal_i1p"))]),
    ])
    index = []
    for base, case, program, mode, model_file, settings, output_specs in cases:
        folder = base / case
        inputs = {"models": [payload(folder / model_file, case, "models", "infernal_cm_ascii")]}
        if mode == "single_key":
            inputs["request"] = [payload(folder / "request.json", case, "request", "infernal_request_json")]
        elif mode == "key_file":
            inputs["keys"] = [payload(folder / "keys.txt", case, "keys", "key_file")]
        outputs = {role: [payload(folder / name, case, role, fmt)] for role, name, fmt in output_specs}
        outputs.update({role: [payload(folder / (role+".txt"), case, role, "infernal_"+role)] for role in ("stdout", "stderr")})
        op = {"program": program, "mode": mode, "engine_version": "1.1.5", "settings": settings}
        result = grade_infernal_preparation(operation=op, inputs=inputs, outputs=outputs, parameters={})
        out = destination / case
        out.mkdir()
        save(out / "sheet.json", result["sheet"])
        save(out / "calculations.json", result["calculations"])
        saved = json.loads((out / "sheet.json").read_text())
        assert recalculate_infernal_preparation(saved, parameters={}) == result["calculations"]
        comp = result["calculations"]["rows"][0]["components"]
        index.append({"case": case, "program": program, "mode": mode,
            "components": {k: {"value": v["value"], "state": v["state"], "unit": v["unit"]} for k,v in comp.items()},
            "files": [{"path": str(p.relative_to(BASE)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "size_bytes": p.stat().st_size}
                      for p in sorted(out.iterdir())]})
    save(BASE / "EXAMPLES_001.json", {"examples": index, "qualification": "Pure worker dispatch on supplied retained files; no episode execution or return verification."})
    print("Saved", len(index), "filled examples across 9 A modes; saved-sheet recalculation exact.")


def build_219():
    from gene_annotation_episode.native_infernal_preparation_worker import grade_infernal_preparation, recalculate_infernal_preparation
    folder = ROOT / "verification/tool_graders_infernal_search_2026-10-26_219/native/cmpress"
    case = "cmpress_retained_219"
    inputs = {"models": [payload(folder / "two_models.cm", case, "models", "infernal_cm_ascii")]}
    formats = {"i1m": "infernal_cm_binary", "i1i": "infernal_ssi", "i1f": "infernal_i1f", "i1p": "infernal_i1p"}
    outputs = {role: [payload(folder / ("two_models.cm."+role), case, role, fmt)] for role,fmt in formats.items()}
    outputs.update({role: [payload(folder / (role+".txt"), case, role, "infernal_"+role)] for role in ("stdout", "stderr")})
    op = {"program": "cmpress", "mode": "press", "engine_version": "1.1.5", "settings": {}}
    result = grade_infernal_preparation(operation=op, inputs=inputs, outputs=outputs, parameters={})
    assert result["sheet"]["native_rows"][0]["values"]["model_count"]["value"] == 2
    assert result["calculations"]["rows"][0]["components"]["input_model_count"]["value"] == 2
    checks = {x["check"]: x["outcome"] for x in result["calculations"]["rows"][0]["checks"]}
    assert checks["model_calibration_present"] == "pass" and checks["output_set_complete"] == "pass"
    out = BASE / "examples" / case
    out.mkdir(exist_ok=False)
    save(out / "sheet.json", result["sheet"])
    save(out / "calculations.json", result["calculations"])
    assert recalculate_infernal_preparation(json.loads((out / "sheet.json").read_text()), parameters={}) == result["calculations"]
    save(BASE / "EXAMPLES_002.json", {"case": case, "input_model_count": 2, "native_model_count": 2,
        "model_calibration_present": "pass", "output_set_complete": "pass", "qualification": "Retained calibrated work219 quartet; no new native or episode run.",
        "files": [{"path": str(p.relative_to(BASE)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(out.iterdir())]})
    print("Retained work219 press: 2 models, calibration present, quartet complete; saved recalculation exact.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "worker":
        build()
    elif len(sys.argv) > 1 and sys.argv[1] == "worker219":
        build_219()
    else:
        retained = len(sys.argv) > 1 and sys.argv[1] == "retained219"
        directory = BASE / ("examples_receipt_219_001" if retained else "examples_receipt_001")
        directory.mkdir(exist_ok=False)
        policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
        command = [str(ROOT / ".venv/bin/python"), str(Path(__file__).resolve()), "worker219" if retained else "worker"]
        request = {"command": command, "policy": policy.to_dict(), "started_at": datetime.now(timezone.utc).isoformat()}
        save(directory / "request.json", request)
        result = run_local_job(command, cwd=directory, policy=policy, stdout_path=directory / "stdout.txt", stderr_path=directory / "stderr.txt",
            env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"})
        save(directory / "receipt.json", {**request, "returncode": result.returncode, "metadata": result.metadata, "finished_at": datetime.now(timezone.utc).isoformat()})
        print((directory / "stdout.txt").read_text())
        print((directory / "stderr.txt").read_text())
        print("returncode", result.returncode)
