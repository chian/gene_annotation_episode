"""Root-only serialized preparation probe; never launches commands or providers.

Usage through the window launcher: python -B THIS_FILE RUN_DIRECTORY
The registry helper is available to the root-owned full binding fixture. This
script alone establishes constructor results, not registry/workflow completion.
"""
from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
import sys
import traceback


AXES = ("a102", "a103")
PARENTS = (
    "hpc_work_planning",
    "hpc_work_planning/hpc_allocation_execution",
    "scientific_process/hpc_work_planning",
    "scientific_process/hpc_work_planning/hpc_allocation_execution",
)
PACKAGE = "gene_annotation_episode.episodic_workflow.root."


def failure(error):
    return {"type": type(error).__name__, "message": str(error),
            "traceback": traceback.format_exc()}


def record_registry_callbacks(registry, contexts, destination):
    """Call the real complete registry supplied by the root-owned fixture.

    Individual callback evaluation records key ownership for the unmodified
    registry conflict. The callback inputs and returned values are never changed.
    Every output remains beneath the caller's run directory.
    """
    rows = []
    for context in contexts:
        selected = registry._context_bindings(context)
        row = {"role": context.role, "episode_id": context.episode_id,
               "path": [list(part) for part in context.path],
               "registered_paths": [getattr(binding, "binding_path", None)
                                    for binding in registry._bindings],
               "selected_paths": [getattr(binding, "binding_path", None)
                                  for binding in selected], "individual": [],
               "registry": {}}
        for binding in selected:
            callback = getattr(binding, "initial_decision_context", None)
            if callback is None:
                continue
            entry = {"binding_path": getattr(binding, "binding_path", None)}
            try:
                entry["keys"] = sorted(callback(context))
            except Exception as error:
                entry["error"] = failure(error)
            row["individual"].append(entry)
        calls = {
            "initial_decision_context": lambda: registry.initial_decision_context(context),
            "received_report_sources": lambda: registry.received_report_sources(
                context.role, path=context.path),
            "received_report_facts": lambda: registry.received_report_facts(context),
        }
        for name, callback in calls.items():
            try:
                value = callback()
                row["registry"][name] = {"keys": sorted(value), "value": value}
            except Exception as error:
                row["registry"][name] = {"error": failure(error)}
        rows.append(row)
    Path(destination).write_text(json.dumps(rows, indent=2, default=str)+"\n")
    return rows


def main():
    output = Path(sys.argv[1]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    resources = json.loads(Path("examples/aurora_execution_resources.json").read_text())
    source_root = Path("gene_annotation_episode/episodic_workflow/root")
    records = []
    for axis in AXES:
        Store = importlib.import_module(PACKAGE+axis+".state").Store
        for parent in PARENTS:
            home = parent+"/execution_job_submission"
            directory = output/axis/parent
            directory.mkdir(parents=True, exist_ok=True)
            row = {"axis": axis, "binding_path": home,
                   "source_sha256": {
                       path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                       for path in sorted((source_root/axis/home).glob("*.py"))}}
            try:
                cls = importlib.import_module(
                    PACKAGE+axis+"."+home.replace("/", ".")+".episode").ExecutionEpisode
                with Store(directory/"store") as store:
                    # The selected original configuration is terminal-only;
                    # its real constructor accepts no API registry or services.
                    binding = cls(None, store=store, directory=directory/"execution",
                        run_id="launch-constructor-baseline", resources=resources,
                        initial_information={}, tool_registry=None, handoff_unit=1,
                        acquired_record_unit=1, log_window_bytes=1024,
                        log_roles=("stdout", "stderr"))
                    row["descriptor"] = binding.as_record()
                    row["status"] = "constructed"
            except Exception as error:
                row["status"] = "failed"
                row["error"] = failure(error)
            records.append(row)
    (output/"constructors.json").write_text(json.dumps(records, indent=2)+"\n")
    print(json.dumps({"constructors": len(records), "constructed": sum(
        row["status"] == "constructed" for row in records),
        "results": str(output/"constructors.json")}))


if __name__ == "__main__":
    main()
