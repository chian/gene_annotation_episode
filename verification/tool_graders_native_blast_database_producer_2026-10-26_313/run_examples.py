"""Retain complete checkable synthetic producer examples through local_jobs."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def worker(directory):
    sys.path.insert(0, str(ROOT / "tests"))
    from test_native_blast_database_driver import fixture, run_fixture, validate_bundle, write, save_json, refresh_plan
    from gene_annotation_episode.native_blast_database_contracts import PROGRAMS
    summaries = []
    modes = [(p, q, "complete") for p in PROGRAMS for q in
        {"psiblast": ["sequence", "msa", "pssm"], "tblastn_vdb": ["sequence", "pssm"]}.get(p, ["sequence"])]
    modes += [("psiblast", "sequence", behavior) for behavior in ("nonzero", "missing", "no_checkpoint")]
    modes += [("psiblast", "sequence", "metadata-first-missing-second-changed"),
        ("psiblast", "pssm", "parser-unavailable"), ("psiblast", "sequence", "pbs-prepared-directories")]
    for program, query, behavior in modes:
        name = program + "-" + query + "-" + behavior
        path, plan, manifest = fixture(directory / name, program, query, behavior)
        if behavior == "metadata-first-missing-second-changed":
            db = plan["requested_job"]["native_blast_database"]["databases"][0]
            first = write(directory / name / "metadata-first", b"selected original first\x00")
            second = write(directory / name / "metadata-second", b"selected original second\xff")
            db["manifest"]["metadata_manifests"] = [first, second]
            db["manifest_file"] = save_json(Path(db["manifest_file"]["path"]), db["manifest"])
            refresh_plan(path, plan)
            Path(first["path"]).unlink()
            Path(second["path"]).write_bytes(b"actual changed second\x00\xff")
        elif behavior == "parser-unavailable":
            parser = "gene_annotation_episode/blast_pssm_inputs.py"
            (Path(manifest["module_root"]) / parser).unlink()
            manifest["package_files"] = [r for r in manifest["package_files"] if r["relative_path"] != parser]
            plan["producer_manifest"] = save_json(Path(plan["producer_manifest"]["path"]), manifest)
            save_json(path, plan)
        elif behavior == "pbs-prepared-directories":
            for control in ("tmp", "cache"):
                (path.parent / control).mkdir()
        result, bundle = run_fixture(path, plan)
        failed = behavior in {"nonzero", "missing", "metadata-first-missing-second-changed", "parser-unavailable"}
        assert result.returncode == int(failed), result.stderr.decode()
        validate_bundle(bundle, plan)
        invoked = path.parent / "native-invocations.log"
        count = len(invoked.read_text().splitlines()) if invoked.exists() else 0
        assert count == (0 if behavior in {"metadata-first-missing-second-changed", "parser-unavailable"} else 1)
        summaries.append({"example": name, "evidence_kind": "synthetic file/process fixture, not native scientific measurements",
            "plan_path": str(path.relative_to(directory)), "bundle_path": str((path.parent / "bundle.json").relative_to(directory)),
            "wrapper_returncode": result.returncode, "native_returncode": bundle["process"]["returncode"],
            "native_elapsed_seconds": bundle["process"]["native_elapsed_seconds"], "invocations": count,
            "retained_artifact_count": len(bundle["artifacts"]), "retained_bytes": sum(a["size_bytes"] for a in bundle["artifacts"]),
            "producer_file_checks": len(bundle["producer_verification"]["checks"]),
            "selected_msa_master_record_ordinal": bundle["associations"]["master_record_ordinal"],
            "outputs": bundle["output_manifest"], "failures": bundle["failures"]})
    (directory / "examples.json").write_text(json.dumps(summaries, indent=2) + "\n")
    print(json.dumps({"examples": len(summaries), "invocations": sum(r["invocations"] for r in summaries),
        "synthetic_failure_bundles": sum(r["wrapper_returncode"] != 0 for r in summaries)}))


def main():
    if sys.argv[1] == "--worker":
        worker(Path(sys.argv[2]))
        return 0
    from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job
    directory = HERE / sys.argv[1]
    directory.mkdir()
    (directory / "temporary").mkdir()
    command = [str(ROOT / ".venv/bin/python"), "-B", str(Path(__file__).resolve()), "--worker", str(directory)]
    policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
    result = run_local_job(command, cwd=directory, policy=policy, stdout_path=directory / "stdout.txt",
        stderr_path=directory / "stderr.txt", env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1",
            "TMPDIR": str(directory / "temporary"), "XDG_CACHE_HOME": str(directory / "cache")})
    (directory / "receipt.json").write_text(json.dumps({"command": command, "policy": policy.to_dict(),
        "returncode": result.returncode, "metadata": result.metadata,
        "evidence_kind": "synthetic producer examples; no BLAST database execution"}, indent=2) + "\n")
    print((directory / "stdout.txt").read_text())
    print((directory / "stderr.txt").read_text())
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
