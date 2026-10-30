"""Import the already completed empirical probe. No execution or credit changes.

The caller selects the shared history, never a per-workspace implicit fallback.
Resource identity is a caller binding, not a claim that historical hardware was
measured. Execution-time resource conditions were not captured: they stay unknown
even if the caller has reported an outage since this job ran.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from Bio import SeqIO

from gene_annotation_episode.run_statistics import ExecutionClass, RunHistory, RunStatistic


ROOT = Path(__file__).resolve().parent
JOB = ROOT / "jobs" / "homology_001"


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def register(history_path, local_resource_id):
    manifest_path = JOB / "job.json"
    manifest = json.loads(manifest_path.read_text())
    for name, info in manifest["outputs"].items():
        if digest(JOB / name) != info["sha256"]:
            raise ValueError("probe_output_changed:" + name)
    if (digest(JOB / "target.faa") != manifest["query_sha256"] or
            digest(JOB / "reviewed.fasta") != manifest["database_sha256"]):
        raise ValueError("probe_input_changed")
    if manifest["query_count"] != 1 or manifest["command"][1:] != [
            "--cpu", "1", "--tblout", "hits.tbl", "--domtblout", "domains.tbl", "target.faa", "reviewed.fasta"]:
        raise ValueError("probe_execution_configuration_changed")
    query_residues = len(SeqIO.read(JOB / "target.faa", "fasta").seq)
    # Only the two phase-start facts are retained, not hundreds of poll samples.
    starts = {}
    with (JOB / "observations.jsonl").open() as stream:
        for line in stream:
            event = json.loads(line)
            if event["event"] == "phase_started":
                if event["phase"] in starts:
                    raise ValueError("ambiguous_probe_phase_attempt")
                starts[event["phase"]] = event
    history = RunHistory(history_path)
    try:
        bindings = {}
        for phase, manifest_field in (("reference_acquisition", "reference_acquisition"), ("homology_search", "search")):
            receipt = manifest[manifest_field]
            native = receipt["native_metadata"]
            if receipt["returncode"] != 0 or native["service_exit"]["SERVICE_RESULT"] != "success":
                raise ValueError("this_importer_requires_the_completed_successful_probe")
            policy = native["policy"]
            parameters = ({"path": manifest["database_query"]["path"],
                           "params": manifest["database_query"]["params"]}
                          if phase == "reference_acquisition" else
                          {"program": "phmmer", "cpu": 1, "search_options": "native_defaults", "query_count": 1})
            scope = ExecutionClass(
                phase="reference_acquisition" if phase == "reference_acquisition" else "protein_homology_search",
                backend="https" if phase == "reference_acquisition" else "local",
                resource_id="rest.uniprot.org" if phase == "reference_acquisition" else local_resource_id,
                # The acquisition helper hash was not recorded at execution.
                implementation_sha256=None if phase == "reference_acquisition" else manifest["executable_sha256"],
                parameters_sha256=hashlib.sha256(json.dumps(parameters, sort_keys=True).encode()).hexdigest(),
                memory_bytes=policy["memory_bytes"], scratch_bytes=policy["scratch_bytes"],
                wall_seconds=policy["wall_seconds"], cpu_threads=None if phase == "reference_acquisition" else 1,
                query_residues=None if phase == "reference_acquisition" else query_residues,
                reference_residues=manifest["database_residues"], reference_records=manifest["database_records"],
                reference_state="download_required" if phase == "reference_acquisition" else "available")
            attempt = hashlib.sha256(json.dumps(starts[phase], sort_keys=True).encode()).hexdigest()
            statistic = RunStatistic(attempt_sha256=attempt, source_sha256=digest(manifest_path),
                observed_at=receipt["at"], outcome="succeeded", duration_kind="complete",
                elapsed_seconds=native["elapsed_seconds"], condition_ref=None)
            history.record(scope, statistic)
            ref = history.capture(scope)
            reader = history.reader(ref)
            try:
                snapshot = reader.get(ref)
            finally:
                reader.close()
            bindings[phase] = {"execution_class": asdict(scope), "expectation_ref": ref,
                               "snapshot": snapshot}
        result = {"shared_history_path": str(history.path), "bindings": bindings,
                  "native_jobs_launched": 0, "scientific_credit_changed": False,
                  "child_yield_history_changed": False,
                  "integration": "empirical_probe_import_not_episode_runtime"}
        return result
    finally:
        history.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", required=True, type=Path)
    parser.add_argument("--local-resource-id", required=True)
    args = parser.parse_args()
    result = register(args.history, args.local_resource_id)
    (ROOT / "run-expectations.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"imported_phases": list(result["bindings"]),
                      "history_path": result["shared_history_path"],
                      "native_jobs_launched": 0}))
