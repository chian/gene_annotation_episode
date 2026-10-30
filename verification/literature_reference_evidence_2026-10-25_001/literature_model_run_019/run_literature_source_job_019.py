"""Custody adapter for an ordinary configured source-evidence investigation.

JOB.txt supplies the scientific job. Closed input metadata supplies source
identity and artifacts, never scientific selections or numerical measurements.
Offline preparation constructs prospective contracts without model entrypoints.
Live execution and explicit resume use only the existing application loop.
"""
from __future__ import annotations

import argparse
import asyncio
from copy import deepcopy
from functools import partial
import hashlib
import inspect
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import uuid


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_new(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def exact(value, names, label):
    require(isinstance(value, dict) and set(value) == set(names.split()), label + "_fields")


def text(value, label):
    require(isinstance(value, str) and bool(value.strip()), label + "_text")


def artifact_path(root, item, *, media=True):
    exact(item, "filename sha256 media_type" if media else "filename sha256", "artifact")
    text(item["filename"], "artifact_filename")
    relative = Path(item["filename"])
    require(not relative.is_absolute() and ".." not in relative.parts, "input_path_escape")
    path = (root / relative).resolve()
    require(path.is_relative_to(root) and path != root and path.is_file(), "input_path_escape_or_missing")
    sha = item["sha256"]
    require(isinstance(sha, str) and len(sha) == 64 and all(c in "0123456789abcdef" for c in sha), "input_digest_format")
    require(digest(path) == sha, "input_hash_mismatch")
    if media:
        text(item["media_type"], "artifact_media_type")
    return path


def load_inputs(pin, metadata=None):
    root = (pin / "inputs").resolve()
    metadata = (json.loads((root / "SOURCE_INPUT_METADATA.json").read_bytes())
                if metadata is None else deepcopy(metadata))
    exact(metadata, "version target job sources", "input_metadata")
    require(metadata["version"] == "literature_source_inputs_v1", "input_metadata_version")
    exact(metadata["target"], "filename sha256 molecule", "target")
    require(metadata["target"]["molecule"] in {"dna", "rna", "protein"}, "target_molecule")
    artifact_path(root, {key: metadata["target"][key] for key in ("filename", "sha256")}, media=False)
    job_path = artifact_path(root, metadata["job"], media=False)
    job = job_path.read_text(encoding="utf-8").rstrip("\n")
    text(job, "job")
    require(isinstance(metadata["sources"], list) and bool(metadata["sources"]), "nonempty_sources_required")
    prior = set()
    for item in metadata["sources"]:
        exact(item, "key original text provider accession uri version parent_keys", "source")
        for field in ("key", "provider"):
            text(item[field], "source_" + field)
        for field in ("accession", "uri", "version"):
            if item[field] is not None:
                text(item[field], "source_" + field)
        require(item["key"] not in prior, "duplicate_source_key")
        parents = item["parent_keys"]
        require(isinstance(parents, list) and all(isinstance(key, str) for key in parents), "parent_keys_array")
        require(len(parents) == len(set(parents)), "duplicate_parent_key")
        require(set(parents).issubset(prior), "parent_must_be_declared_earlier")
        artifact_path(root, item["original"])
        if item["text"] is not None:
            artifact_path(root, item["text"])
        prior.add(item["key"])
    return metadata, job


def verify_pin(pin):
    manifest = json.loads((pin / "SOURCE_MANIFEST.json").read_bytes())
    seen = set()
    for row in manifest["files"]:
        relative = Path(row["pin_relative_path"])
        require(not relative.is_absolute() and ".." not in relative.parts, "pin_path_escape")
        require(str(relative) not in seen, "duplicate_pin_path")
        seen.add(str(relative))
        path = (pin / relative).resolve()
        require(path.is_relative_to(pin) and path != pin, "pin_path_escape")
        require(path.stat().st_size == row["size"] and digest(path) == row["sha256"], "pin_hash_mismatch:" + str(relative))
    actual = {str(path.relative_to(pin)) for path in pin.rglob("*") if path.is_file()
              and path != pin / "SOURCE_MANIFEST.json"}
    require(actual == seen, "pin_unmanifested_or_missing_file")
    return manifest


def configure_pin(pin):
    require(Path(__file__).resolve() == pin / "runner" / Path(__file__).name, "execute_the_pinned_runner")
    verify_pin(pin)
    # Do not change caller cwd. Safe-path durable workers receive this selected
    # runtime first on PYTHONPATH through the existing repaired launcher.
    repository = next(parent for parent in pin.parents if (parent / "AGENTS.md").is_file())
    sys.path[:] = [str(pin), *[entry for entry in sys.path if entry
        and Path(entry).resolve() not in {repository, repository / "tests", pin / "runner"}]]
    sys.dont_write_bytecode = True
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    from gene_annotation_episode.state import Store
    from method_loop.episode import Episode
    for value in (Store, Episode):
        require(Path(inspect.getfile(value)).resolve().is_relative_to(pin), "unpinned_runtime_import")


def register_inputs(store, pin, metadata):
    """Register declared bytes, preserving original/text and ordered ancestry."""
    root = pin / "inputs"
    fasta = (root / metadata["target"]["filename"]).read_text(encoding="utf-8")
    require(sum(line.startswith(">") for line in fasta.splitlines()) == 1, "single_supplied_target_required")
    sequence = "".join(line.strip() for line in fasta.splitlines() if line.strip() and not line.startswith(">"))
    store.create_problem(raw_sequence=sequence, molecule=metadata["target"]["molecule"])
    published = {}
    for item in metadata["sources"]:
        original = store.artifact((root / item["original"]["filename"]).read_bytes(), item["original"]["media_type"])
        projection = (None if item["text"] is None else store.artifact(
            (root / item["text"]["filename"]).read_bytes(), item["text"]["media_type"]))
        row = store.put("source", {"provider": item["provider"], "accession": item["accession"],
            "uri": item["uri"], "artifact_ref": original, "text_ref": projection,
            "request_ref": None, "version": item["version"], "retrieved_at": None,
            "parent_source_refs": [published[key]["id"] for key in item["parent_keys"]]}, origin="caller")
        published[item["key"]] = row
    refs = list(dict.fromkeys(row["id"] for row in published.values()))
    return {"source_refs": refs, "source_records": published,
        "metadata_sha256": digest(root / "SOURCE_INPUT_METADATA.json"),
        "job_sha256": metadata["job"]["sha256"],
        "target_fasta_sha256": metadata["target"]["sha256"],
        "target_sequence_sha256": hashlib.sha256(sequence.encode()).hexdigest(),
        "prepared_numeric_operands_supplied": False}


def custody_checks(pin, metadata):
    """Exercise invalid custody and arbitrary keys/ancestry without Store work."""
    checked = []
    def reject(name, mutate):
        trial = deepcopy(metadata)
        mutate(trial)
        try:
            load_inputs(pin, trial)
        except (ValueError, OSError):
            checked.append(name)
        else:
            raise AssertionError("invalid_custody_accepted:" + name)
    reject("duplicate_source_key", lambda trial: trial["sources"].append(deepcopy(trial["sources"][0])))
    reject("unknown_parent", lambda trial: trial["sources"][0].update(parent_keys=["undeclared-parent"]))
    reject("path_escape", lambda trial: trial["sources"][0]["original"].update(filename="../JOB.txt"))
    reject("hash_mismatch", lambda trial: trial["sources"][0]["original"].update(sha256="0" * 64))
    reject("extra_field", lambda trial: trial.update(undeclared=True))
    trial = deepcopy(metadata)
    trial["sources"] = []
    for index in range(3):
        item = deepcopy(metadata["sources"][0])
        item.update(key="arbitrary-key-" + str(index), parent_keys=[] if not index else ["arbitrary-key-" + str(index - 1)])
        if index == 2:
            item["text"] = None
            item.update(accession=None, uri=None, version=None)
        trial["sources"].append(item)
    load_inputs(pin, trial)
    return {"rejected": checked, "arbitrary_three_keys_earlier_parent_chain_optional_text_validated": True,
            "nullable_source_identifiers_validated": True,
            "meaning": "Custody validation only; no synthetic sources registered as scientific inputs"}


def selected_models(configuration):
    return {key: {field: configuration[key][field] for field in ("model", "reasoning_effort")
                  if field in configuration[key]} for key in ("REASONING", "FAST")}


def offline_check(pin, directory, metadata, job):
    from gene_annotation_episode import providers
    from gene_annotation_episode.communication import validate_closed_schema
    from gene_annotation_episode.domain import obj, validate_schema
    from gene_annotation_episode.episode_bindings import BindingContext
    from gene_annotation_episode.episode_services import WorkflowServices
    from gene_annotation_episode.independent_execution import implementation_sha256
    from gene_annotation_episode.literature_episodes import LiteratureEpisodes
    from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
    from gene_annotation_episode.literature_partner_calculations import COMPONENTS
    from gene_annotation_episode.literature_partner_prompt import PARTNER_TASK
    from gene_annotation_episode.literature_partner_storage import partner_cells_schema
    from gene_annotation_episode.literature_reference_parent_prompt import REFERENCE_PARENT_TASK
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tool_configuration import build_tools

    blocked_calls, disabled = [], []
    def forbidden(*args, **kwargs):
        blocked_calls.append("model_entrypoint")
        raise AssertionError("offline_preparation_forbids_model_calls")
    for cls in (providers.ModelConnection, providers._SessionConnection):
        for name in ("__init__", "__aenter__", "complete", "catalog"):
            setattr(cls, name, forbidden)
            disabled.append(cls.__name__ + "." + name)
    providers._SessionConnection._rpc = forbidden
    disabled.append("_SessionConnection._rpc")
    directory.mkdir(parents=True, exist_ok=False)
    custody = custody_checks(pin, metadata)
    with Store(directory / "state") as store:
        source_info = register_inputs(store, pin, metadata)
        configuration = providers.load_config()
        tools = build_tools(store, configuration)
        host = SimpleNamespace(store=store, tools=tools, run_id="offline-source-job-preparation")
        binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True,
            reference_parent_sources=source_info["source_refs"])
        scope = store.validate_scope()
        assignment = {"version": "literature_assignment_v1", "question_context_refs": [],
            "source_refs": source_info["source_refs"], "requested_partner_components": list(COMPONENTS)}
        validate_schema(assignment, binding.assignment_schema("literature"))
        context = BindingContext(host.run_id, "offline-contract", "literature",
            (("literature", "contract-preparation"),), scope, assignment, {}, tuple(source_info["source_refs"]))
        catalog = binding.catalog(context)
        entry, = [item for item in catalog if item["name"] == "literature.partner.source.populate"]
        require(entry["input_schema"]["additionalProperties"] is False, "native_operation_must_be_closed")
        require(entry["input_schema"]["properties"]["input_mode"]["const"] == "native_source_spans", "native_operation_mode")
        require('"source_defined_rate_unit"' in json.dumps(entry["input_schema"]), "source_defined_rate_unit_missing")
        form = obj({"measurements": partner_cells_schema()})
        validate_closed_schema(form)
        source_custody = [{"source_ref": row["id"], **{name: row.get(name) for name in
                    ("artifact_ref", "text_ref", "version", "parent_source_refs")}}
                   for row in source_info["source_records"].values()]
        rendered = render_literature_experimental_prompt({
            "literature_experimental_work": {"version": "literature_experimental_task_v1", "aspect": "source_experimental_evidence"},
            "goal": {"objective": job}, "scope": scope, "literature_assignment": assignment,
            "literature_source_custody": source_custody,
            "tools": catalog, "requested_form": form,
            "available_report_facts": binding.fact_sources("literature")}, binding.instructions(context))
        require(rendered.startswith("TASK\n") and "\nSTEERING\n" in rendered, "task_steering_required")
        require(all(paragraph in rendered for paragraph in job.split("\n\n")) and PARTNER_TASK in rendered, "full_recurring_task_required")
        parent_context = BindingContext(host.run_id, "offline-parent-contract", "annotation",
            (("annotation", "root"),), scope, {}, {}, tuple(source_info["source_refs"]))
        parent_initial = binding.initial_decision_context(parent_context)
        parent_rendered = render_literature_experimental_prompt({**parent_initial,
            "goal": {"objective": job}, "scope": scope,
            "available_report_facts": binding.received_report_sources("annotation")}, "")
        require(parent_rendered.startswith("TASK\n") and "\nSTEERING\n" in parent_rendered,
                "parent_task_steering_required")
        require(all(paragraph in parent_rendered for paragraph in job.split("\n\n"))
                and REFERENCE_PARENT_TASK in parent_rendered, "parent_full_recurring_task_required")
        require(all(row["artifact_ref"] in rendered and row["artifact_ref"] in parent_rendered
                and (row["text_ref"] is None or row["text_ref"] in rendered and row["text_ref"] in parent_rendered)
                for row in source_info["source_records"].values()), "original_text_custody_in_tasks")
        for name, value in (("SOURCE_CATALOG.json", source_info), ("OPERATION_CATALOG.json", catalog),
                ("NUMERICAL_RETURN_SCHEMA.json", form), ("ASSIGNMENT_SCHEMA.json", binding.assignment_schema("literature")),
                ("BINDING_DESCRIPTOR.json", binding.as_record()), ("CUSTODY_CHECKS.json", custody)):
            save_new(directory / name, value)
        with (directory / "PROSPECTIVE_TASK_AND_STEERING.txt").open("x", encoding="utf-8") as stream:
            stream.write(rendered)
        with (directory / "PROSPECTIVE_PARENT_TASK_AND_STEERING.txt").open("x", encoding="utf-8") as stream:
            stream.write(parent_rendered)
        tables = {row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        counts = {name: store.db.execute("SELECT count(*) FROM " + name).fetchone()[0]
            for name in ("runtime_model_calls", "runtime_actions", "runtime_observations", "runtime_runs") if name in tables}
        require(not any(counts.values()) and not store.list("observation") and not store.list("assessment"), "offline_scientific_work_forbidden")
        for row in source_info["source_records"].values():
            require(store.get(row["id"]) == row, "registered_source_mismatch")
        safe_models = selected_models(configuration)
    require(not blocked_calls, "attempted_model_entrypoint")
    verify_pin(pin)
    receipt = {"status": "passed", "model_backed": False,
        "meaning": "Actual source registration and prospective operation/catalog/schema/TASK construction; no scientific execution",
        "declared_source_count": len(metadata["sources"]), "registered_source_count": len(source_info["source_refs"]),
        "native_operation_available": True, "source_defined_rate_unit_available": True,
        "full_parent_and_child_tasks_with_original_and_optional_text_custody": True,
        "prospective_requested_partner_components": list(COMPONENTS), "models": safe_models,
        "disabled_model_entrypoints": disabled, "attempted_model_calls": blocked_calls, "runtime_counts": counts,
        "implementation_sha256": implementation_sha256(), "pin_manifest_sha256": digest(pin / "SOURCE_MANIFEST.json"),
        "live_run_launched": False, "prepared_numeric_operands_supplied": False,
        "files": [{"path": str(path.relative_to(directory)), "sha256": digest(path)}
            for path in sorted(directory.glob("*")) if path.is_file()]}
    save_new(directory / "RECEIPT.json", receipt)
    print(json.dumps({"status": "passed", "model_backed": False,
        "source_count": len(source_info["source_refs"]), "live_run_launched": False}), flush=True)


async def live(pin, directory, resume, metadata, job):
    from gene_annotation_episode.literature_episodes import LiteratureEpisodes
    from gene_annotation_episode.providers import load_config
    from gene_annotation_episode.runtime import run_workflow
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tool_configuration import build_tools

    if resume:
        require((directory / "state" / "state.sqlite3").is_file(), "resume_state_missing")
        require((directory / "JOB.txt").read_bytes() == (pin / "inputs" / metadata["job"]["filename"]).read_bytes(), "resume_job_changed")
        original = json.loads((directory / "PROCESS.json").read_bytes())
        require(original["pin"] == str(pin) and original["pin_manifest_sha256"] == digest(pin / "SOURCE_MANIFEST.json"), "resume_pin_changed")
        source_info = json.loads((directory / "SOURCE_INPUTS.json").read_bytes())
        require(source_info["metadata_sha256"] == digest(pin / "inputs" / "SOURCE_INPUT_METADATA.json"), "resume_sources_changed")
        tracking = directory / "resume-processes"
        tracking.mkdir(exist_ok=True)
        process_receipt = tracking / (uuid.uuid4().hex + ".json")
    else:
        directory.mkdir(parents=True, exist_ok=False)
        process_receipt = directory / "PROCESS.json"
    save_new(process_receipt, {"pid": os.getpid(), "pin": str(pin), "caller": str(Path(__file__).resolve()),
        "caller_cwd": str(Path.cwd()), "mode": "resume" if resume else "new",
        "pin_manifest_sha256": digest(pin / "SOURCE_MANIFEST.json")})
    with Store(directory / "state") as store:
        if resume:
            for row in source_info["source_records"].values():
                require(store.get(row["id"]) == row, "resume_source_record_changed")
        else:
            source_info = register_inputs(store, pin, metadata)
            save_new(directory / "SOURCE_INPUTS.json", source_info)
            with (directory / "JOB.txt").open("xb") as stream:
                stream.write((pin / "inputs" / metadata["job"]["filename"]).read_bytes())
        configuration = load_config()
        tools = build_tools(store, configuration)
        print(json.dumps({"phase": "configured_workflow_start", "pid": os.getpid(),
            "source_count": len(source_info["source_refs"]),
            "models": selected_models(configuration)}), flush=True)
        result = await run_workflow(store, tools, provider_config=configuration,
            run_dir=directory / "run", resume=resume, goal=job,
            initial_known_record_refs=source_info["source_refs"],
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
                reference_parent_sources=source_info["source_refs"]),),
            annotation_child_roles=("literature",))
        if (directory / "RESULT.json").exists():
            require(resume and json.loads((directory / "RESULT.json").read_bytes()) == result, "resume_result_changed")
        else:
            save_new(directory / "RESULT.json", result)
        print(json.dumps({"phase": "configured_workflow_returned", "result": result}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pin", type=Path, required=True)
    parser.add_argument("--directory", type=Path)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--offline-check", type=Path)
    args = parser.parse_args()
    require((args.offline_check is not None and args.directory is None and not args.resume)
        or (args.offline_check is None and args.directory is not None), "choose_offline_or_live")
    pin = args.pin.resolve()
    configure_pin(pin)
    metadata, job = load_inputs(pin)
    destination = (args.offline_check if args.offline_check is not None else args.directory).resolve()
    require(not destination.is_relative_to(pin), "state_directory_must_not_modify_pin")
    if args.offline_check is not None:
        offline_check(pin, destination, metadata, job)
        return
    try:
        asyncio.run(live(pin, destination, args.resume, metadata, job))
    except BaseException as error:
        if destination.is_dir():
            save_new(destination / ("CALLER_ERROR_" + uuid.uuid4().hex + ".json"),
                {"type": type(error).__name__, "message": str(error)})
        raise


if __name__ == "__main__":
    main()
