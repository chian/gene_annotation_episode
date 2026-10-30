"""Prepare or run the ordinary configured source-evidence investigation.

Offline preparation registers raw sources and constructs contracts only. Live
execution has no scripted provider, custom controller, private episode loop,
scientific completion override, timeout or action cap.
"""
from __future__ import annotations

import argparse
import asyncio
from functools import partial
import hashlib
import inspect
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import uuid


JOB = """Determine what the supplied PLP formation experiments establish about the roles of Pdx1 and Pdx2. Establish the actual assayed molecules and constructs, experimental system, endpoint, normalization, nitrogen donor and other conditions. Distinguish a controlled partner-removal effect from rescue or bypass with changed assay chemistry; determine whether a distinct restoration experiment is supplied. Preserve reported uncertainty meanings, unresolved physical measurement identity and missing information.

Use available native source-span population to return justified conditional experimental numerical components through ordinary typed literature-child forms, retaining why other components are unavailable. Select experimental meanings and source operands yourself; deterministic readers parse source tokens and units and calculate the components. Do not infer exact zero from nondetection, independent observations from mentions, or comparability from equal units. This is reference experimental evidence, not target correspondence, sequence alignment, universal partner necessity or annotation-credit/W05.

The supplied source inputs are retained publisher tool-rendered Results and Methods text, not original PDF bytes. They contain the source measurements; no prepared numerical dataset, selected measurement spans or populated scoring cells are supplied. The fixed target sequence identifies the existing annotation task material but is not an additional experimental subject to annotate in this source-evidence assignment. Assign relevant source work and typed requests using the existing episode choices; no mandatory child order or additional search is required for this bounded question. Retain substantive scientific TASK instructions on each iteration and keep factual STEERING concise. The ordinary configured estimator/controller owns continuation."""


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_new(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def verify_pin(pin):
    manifest = json.loads((pin / "SOURCE_MANIFEST.json").read_bytes())
    for row in manifest["files"]:
        path = (pin / row["pin_relative_path"]).resolve()
        assert path.is_relative_to(pin) and path != pin, "pin_path_escape"
        assert path.stat().st_size == row["size"] and digest(path) == row["sha256"], row["pin_relative_path"]
    return manifest


def configure_pin(pin):
    assert Path(__file__).resolve() == pin / "runner" / Path(__file__).name, "execute_the_pinned_runner"
    verify_pin(pin)
    repository = pin.parents[3]
    sys.path[:] = [str(pin), *[entry for entry in sys.path if entry
        and Path(entry).resolve() not in {repository, repository / "tests", pin / "runner"}]]
    sys.dont_write_bytecode = True
    from gene_annotation_episode.state import Store
    from method_loop.episode import Episode
    for value in (Store, Episode):
        assert Path(inspect.getfile(value)).resolve().is_relative_to(pin), "unpinned_runtime_import"


def register_inputs(store, pin):
    """Copy bytes into the isolated Store without extracting scientific operands."""
    fasta = (pin / "inputs" / "target.fna").read_text()
    assert sum(line.startswith(">") for line in fasta.splitlines()) == 1, "single_supplied_target_required"
    sequence = "".join(line.strip() for line in fasta.splitlines() if line.strip() and not line.startswith(">"))
    store.create_problem(raw_sequence=sequence, molecule="dna")
    metadata = json.loads((pin / "inputs" / "SOURCE_INPUT_METADATA.json").read_bytes())
    published = {}
    for item in metadata["sources"]:
        path = pin / "inputs" / item["filename"]
        content = path.read_bytes()
        assert digest(path) == item["sha256"]
        artifact = store.artifact(content, "text/plain")
        row = store.put("source", {
            "provider": item["provider"], "accession": item["accession"],
            "uri": item["uri"], "artifact_ref": artifact, "text_ref": artifact,
            "request_ref": None, "version": item["representation_kind"],
            "retrieved_at": None,
            "parent_source_refs": [published[key]["id"] for key in item["parent_keys"]],
        }, origin="caller")
        published[item["key"]] = row
    assert set(published) == {"results", "methods"}
    return {"source_refs": [row["id"] for row in published.values()],
        "source_records": published,
        "source_origin": "retained_publisher_tool_text_renderings; not original PDF bytes",
        "publication_identifiers": metadata["publication_identifiers"],
        "target_fasta_sha256": digest(pin / "inputs" / "target.fna"),
        "target_sequence_sha256": hashlib.sha256(sequence.encode()).hexdigest(),
        "prepared_numeric_operands_supplied": False}


def offline_check(pin, directory):
    """Exercise actual source/catalog/schema construction with model calls disabled."""
    from gene_annotation_episode import providers
    from gene_annotation_episode.communication import validate_closed_schema
    from gene_annotation_episode.domain import obj, validate_schema
    from gene_annotation_episode.episode_bindings import BindingContext
    from gene_annotation_episode.episode_services import WorkflowServices
    from gene_annotation_episode.literature_episodes import LiteratureEpisodes
    from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
    from gene_annotation_episode.literature_partner_calculations import COMPONENTS
    from gene_annotation_episode.literature_partner_prompt import PARTNER_TASK
    from gene_annotation_episode.literature_partner_storage import partner_cells_schema
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tool_configuration import build_tools

    blocked_calls = []
    def forbidden(*args, **kwargs):
        blocked_calls.append("model_transport_or_completion")
        raise AssertionError("offline_preparation_forbids_model_calls")
    disabled = []
    for cls in (providers.ModelConnection, providers._SessionConnection):
        for name in ("__aenter__", "complete", "catalog"):
            setattr(cls, name, forbidden)
            disabled.append(cls.__name__ + "." + name)
    providers._SessionConnection._rpc = forbidden
    disabled.append("_SessionConnection._rpc")
    directory.mkdir(parents=True, exist_ok=False)
    with Store(directory / "state") as store:
        source_info = register_inputs(store, pin)
        configuration = providers.load_config()
        tools = build_tools(store, configuration)
        host = SimpleNamespace(store=store, tools=tools, run_id="offline-native-partner-preparation")
        binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True,
            reference_parent_sources=source_info["source_refs"])
        scope = store.validate_scope()
        assignment = {"version": "literature_assignment_v1", "question_context_refs": [],
            "source_refs": source_info["source_refs"], "requested_partner_components": list(COMPONENTS)}
        validate_schema(assignment, binding.assignment_schema("literature"))
        context = BindingContext(host.run_id, "offline-literature-contract", "literature",
            (("literature", "contract-preparation"),), scope, assignment, {}, tuple(source_info["source_refs"]))
        catalog = binding.catalog(context)
        entry, = [item for item in catalog if item["name"] == "literature.partner.source.populate"]
        assert entry["input_schema"]["additionalProperties"] is False
        assert entry["input_schema"]["properties"]["input_mode"]["const"] == "native_source_spans"
        form = obj({"measurements": partner_cells_schema()})
        validate_closed_schema(form)
        rendered = render_literature_experimental_prompt({
            "literature_experimental_work": {"version": "literature_experimental_task_v1", "aspect": "source_experimental_evidence"},
            "goal": {"objective": JOB}, "scope": scope, "literature_assignment": assignment,
            "tools": catalog, "requested_form": form,
            "available_report_facts": binding.fact_sources("literature"),
        }, binding.instructions(context))
        assert rendered.startswith("TASK\n") and "\nSTEERING\n" in rendered
        assert all(paragraph in rendered for paragraph in JOB.split("\n\n")) and PARTNER_TASK in rendered
        save_new(directory / "SOURCE_CATALOG.json", source_info)
        save_new(directory / "OPERATION_CATALOG.json", catalog)
        save_new(directory / "NUMERICAL_RETURN_SCHEMA.json", form)
        save_new(directory / "ASSIGNMENT_SCHEMA.json", binding.assignment_schema("literature"))
        save_new(directory / "BINDING_DESCRIPTOR.json", binding.as_record())
        (directory / "PROSPECTIVE_TASK_AND_STEERING.txt").write_text(rendered)
        tables = {row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        counts = {name: store.db.execute("SELECT count(*) FROM " + name).fetchone()[0]
            for name in ("runtime_model_calls", "runtime_actions", "runtime_observations", "runtime_runs") if name in tables}
        assert not any(counts.values())
        assert not store.list("observation") and not store.list("assessment")
        literature_sources = [row for row in store.list("source")
            if row["provider"].startswith("retained_publisher_tool_text_")]
        assert {row["id"] for row in literature_sources} == set(source_info["source_refs"])
        assert len(literature_sources) == 2
    assert not blocked_calls
    verify_pin(pin)
    receipt = {"status": "passed", "model_backed": False,
        "meaning": "Actual offline raw-source registration and prospective catalog/schema/TASK construction; no scientific execution",
        "source_count": 2, "native_operation_available": True,
        "requested_partner_components": list(COMPONENTS), "disabled_model_entrypoints": disabled,
        "attempted_model_calls": blocked_calls, "runtime_counts": counts,
        "pin_manifest_sha256": digest(pin / "SOURCE_MANIFEST.json"),
        "live_run_launched": False, "prepared_numeric_operands_supplied": False,
        "files": [{"path": str(path.relative_to(directory)), "sha256": digest(path)}
            for path in sorted(directory.glob("*")) if path.is_file()]}
    save_new(directory / "RECEIPT.json", receipt)
    print(json.dumps({"status": receipt["status"], "model_backed": False, "source_count": 2,
        "live_run_launched": False}), flush=True)


async def live(pin, directory, resume):
    from gene_annotation_episode.literature_episodes import LiteratureEpisodes
    from gene_annotation_episode.providers import load_config
    from gene_annotation_episode.runtime import run_workflow
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tool_configuration import build_tools

    if not resume:
        directory.mkdir(parents=True, exist_ok=False)
    if resume:
        tracking = directory / "resume-processes"
        tracking.mkdir(exist_ok=True)
        process_receipt = tracking / (uuid.uuid4().hex + ".json")
    else:
        process_receipt = directory / "PROCESS.json"
    save_new(process_receipt, {
        "pid": os.getpid(), "pin": str(pin), "caller": str(Path(__file__).resolve()),
        "mode": "resume" if resume else "new", "pin_manifest_sha256": digest(pin / "SOURCE_MANIFEST.json")})
    with Store(directory / "state") as store:
        if resume:
            source_info = json.loads((directory / "SOURCE_INPUTS.json").read_bytes())
            assert (directory / "JOB.txt").read_text() == JOB + "\n"
        else:
            source_info = register_inputs(store, pin)
            save_new(directory / "SOURCE_INPUTS.json", source_info)
            (directory / "JOB.txt").write_text(JOB + "\n")
        configuration = load_config()
        tools = build_tools(store, configuration)
        print(json.dumps({"phase": "configured_workflow_start", "pid": os.getpid(),
            "source_count": len(source_info["source_refs"]),
            "models": {key: configuration[key] for key in ("REASONING", "FAST")}}), flush=True)
        result = await run_workflow(store, tools, provider_config=configuration,
            run_dir=directory / "run", resume=resume, goal=JOB,
            initial_known_record_refs=source_info["source_refs"],
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
                reference_parent_sources=source_info["source_refs"]),),
            annotation_child_roles=("literature",))
        if (directory / "RESULT.json").exists():
            assert resume and json.loads((directory / "RESULT.json").read_bytes()) == result
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
    if args.offline_check is not None:
        assert args.directory is None and not args.resume
    else:
        assert args.directory is not None
    pin = args.pin.resolve()
    configure_pin(pin)
    if args.offline_check is not None:
        offline_check(pin, args.offline_check.resolve())
        return
    directory = args.directory.resolve()
    assert not directory.is_relative_to(pin), "run_directory_must_not_modify_pin"
    try:
        asyncio.run(live(pin, directory, args.resume))
    except BaseException as error:
        if directory.is_dir():
            save_new(directory / "CALLER_ERROR.json", {"type": type(error).__name__, "message": str(error)})
        raise


if __name__ == "__main__":
    main()
