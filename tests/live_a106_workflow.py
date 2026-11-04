"""Run an unscripted, sequence-only A106 investigation with repository defaults.

Evaluator expectations are never loaded. BV-BRC execution is unconfigured by
default; --execution-config accepts an explicit existing execution binding when
service evaluation resumes. All run artifacts and the
frozen application source are kept under the repository's runs/ directory.
"""
import argparse
import asyncio
from functools import partial
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import traceback

sys.dont_write_bytecode = True


def execution_factory(configuration, *, store, directory, tool_registry):
    """Bind existing AppService roles without submitting work or adding evidence."""
    from gene_annotation_episode.execution_episodes import ExecutionEpisodes
    expected = {"resources", "initial_information", "handoff_unit", "acquired_record_unit",
        "log_window_bytes", "log_roles"}
    if not isinstance(configuration, dict) or set(configuration) != expected:
        raise ValueError("explicit_execution_binding_configuration_required")
    if configuration["initial_information"] != {}:
        raise ValueError("anonymous_evaluation_requires_empty_initial_information")
    resources = configuration["resources"]
    if not isinstance(resources, dict) or not resources or any(
            not isinstance(row, dict) or row.get("kind") != "api" or row.get("service") != "bvbrc_appservice"
            for row in resources.values()):
        raise ValueError("a106_evaluation_requires_appservice_resources")
    # Copy once so the caller cannot alter the binding while a run is active.
    selected = json.loads(json.dumps(configuration))
    def factory(services):
        return ExecutionEpisodes(services, store=store, directory=directory,
            run_id=services.workflow.run_id, tool_registry=tool_registry, **selected)
    return factory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--execution-config", type=Path,
        help="JSON containing the existing execution binding configuration; omitted means no BV-BRC execution")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    run = args.run_dir.resolve()
    if not run.is_relative_to(root / "runs") or run == root / "runs":
        parser.error("--run-dir must be a separate directory below this repository's runs/")
    run.mkdir(parents=True, exist_ok=True)
    execution_bytes = None if args.execution_config is None else args.execution_config.read_bytes()
    execution_digest = None if execution_bytes is None else hashlib.sha256(execution_bytes).hexdigest()
    if args.resume and (run / "launch.json").exists():
        if json.loads((run / "launch.json").read_text()).get("execution_configuration_sha256") != execution_digest:
            parser.error("resume requires the original execution configuration")
    (run / "tmp").mkdir(exist_ok=True)
    os.environ.update(PYTHONDONTWRITEBYTECODE="1", TMPDIR=str(run / "tmp"), XDG_CACHE_HOME=str(run / "cache"))
    if not args.resume:
        os.environ["GENE_EPISODE_LOCAL_RESOURCE_DIRECTORY"] = str(run / "local-resources")
    elif (run / "launch.json").exists():
        original = json.loads((run / "launch.json").read_text())
        if original.get("local_resource_directory"):
            os.environ["GENE_EPISODE_LOCAL_RESOURCE_DIRECTORY"] = original["local_resource_directory"]
    snapshot = run / "source"
    if not args.resume:
        if (run / "launch.json").exists() or snapshot.exists():
            parser.error("existing run: select --resume or a new run directory")
        for package in ("gene_annotation_episode", "method_loop"):
            shutil.copytree(root / package, snapshot / package,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        pins = {str(p.relative_to(snapshot)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(snapshot.rglob("*")) if p.is_file()}
        (run / "source-pins.json").write_text(json.dumps(pins, indent=2) + "\n")
    elif not snapshot.is_dir():
        parser.error("the original run source snapshot is missing")
    sys.path.insert(0, str(snapshot))
    from gene_annotation_episode.literature_episodes import LiteratureEpisodes
    from gene_annotation_episode.runtime import run_workflow
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tool_configuration import build_tools
    from gene_annotation_episode.composition_information import CONTRACT_INFORMATION_PROFILE

    goal = (
        "Investigate A106 intervention evidence for the supplied anonymous microbial protein sequence. "
        "Discover relevant studies and establish the actual tested subject's correspondence to the sequence. "
        "Determine what changing this molecule establishes about its contribution to an observed outcome. "
        "Recover source-supported intervention, reference and restoration measurements where available, "
        "with design, sampling units, uncertainty, controls and original experiment identity. Decide whether "
        "published measurements suffice or acquired deposited data resolve a specific missing comparison. "
        "Use the supplied readers and intervention grader, and finalize the A106 experimental subscore "
        "with the existing signed log evidence-ratio calculation when its operands are supported. "
        "Return that typed final subscore to the parent, preserving unavailable scores, contrary evidence, "
        "dependence, duplicate representations and limitations. Do not manufacture missing predictions or uncertainty."
    )
    flags = dict(rate_population=True, a106_intervention=True, ratio_source_population=True,
        controlled_response_population=True, gel_population=True, completion_time_population=True,
        product_partition_population=True, active_site_population=True, parent_depletion_population=True,
        stoichiometric_balance_population=True, compiled_assay_population=True,
        reference_parent_sources=[], contract_information_profile=CONTRACT_INFORMATION_PROFILE)
    config = {"public":{"provider_access_dir":str(run / "provider-access")},
        "local_tools":{"minimap2_cache_dir":str(run / "cache/minimap2")}}
    for name in ("pdfinfo", "pdftotext", "pdftoppm"):
        if shutil.which(name):
            config["local_tools"][name + "_executable"] = shutil.which(name)

    async def execute():
        with Store(run / "state") as store:
            tools = build_tools(store, config)
            bindings = [partial(LiteratureEpisodes, **flags)]
            if execution_bytes is not None:
                bindings.append(execution_factory(json.loads(execution_bytes), store=store,
                    directory=run / "execution", tool_registry=tools))
            if not args.resume:
                sequence = args.input.read_text().strip()
                store.create_problem(raw_sequence=sequence, molecule="protein")
                (run / "input.txt").write_text(sequence + "\n")
                (run / "launch.json").write_text(json.dumps(dict(goal=goal, input_mode="raw_sequence_only",
                    sequence_sha256=hashlib.sha256(sequence.encode()).hexdigest(), sequence_length=len(sequence),
                    literature_flags=flags, models="repository defaults", controller="repository default YieldController",
                    local_resource_directory=os.environ.get("GENE_EPISODE_LOCAL_RESOURCE_DIRECTORY"),
                    launcher_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    execution_configuration_sha256=execution_digest,
                    external_cutoff=None, preloaded_evidence=[], scripted_model_decisions=False,
                    evaluator_expectations_loaded=False, bvbrc_execution=("deferred_by_user"
                        if execution_bytes is None else "explicit_execution_binding_configured")), indent=2) + "\n")
            result = await run_workflow(store, tools, run_dir=run / "workflow",
                resume=args.resume, goal=goal, episode_binding_factories=tuple(bindings),
                initial_known_record_refs=[store.targets()[0]["source_ref"]], annotation_child_roles=("literature",))
            (run / "result.json").write_text(json.dumps(result, indent=2) + "\n")
            print(json.dumps(result), flush=True)
    try:
        asyncio.run(execute())
    except BaseException as error:
        (run / "failure.json").write_text(json.dumps(dict(type=type(error).__name__, message=str(error),
            traceback=traceback.format_exc()), indent=2) + "\n")
        raise


if __name__ == "__main__":
    main()
