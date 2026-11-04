"""Run a full autonomous A108 investigation; no evaluator data is loaded."""
import argparse
import asyncio
from datetime import datetime, timezone
from functools import partial
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import traceback


GOAL = (
    "Investigate A108 organism and sample compatibility for the supplied protein sequence "
    "and any supplied biological context. Discover relevant evidence with the available "
    "literature and database tools. Establish the molecule and organism correspondence, "
    "form source-supported possible functional claims, and determine what biological "
    "requirements and observed contexts bear on those claims. Choose organism capability "
    "or sample-context coverage according to the biological question before calculation. "
    "Preserve actual scope, joint requirements, alternatives, physical observations, "
    "uncertainty, source conflicts and unexamined conditions. Use the source readers and "
    "existing requirement_compatibility calculations, save the assessment and final A108 "
    "subscore, and deliver its selected bounds, point and separate sampling bounds to the "
    "parent through literature_a108_subscore_cells. The parent must consume that result "
    "in its conclusion about the original question. Retain useful partial results with "
    "specific unresolved requirements."
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--context", type=Path)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    run = args.run_dir.resolve()
    if "runs" not in run.parts:
        parser.error("--run-dir must be beneath the repository runs directory")
    for name in ("tmp", "cache", "provider-access"):
        (run / name).mkdir(parents=True, exist_ok=True)
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    for name in ("TMPDIR", "TMP", "TEMP"):
        os.environ[name] = str(run / "tmp")
    os.environ["XDG_CACHE_HOME"] = str(run / "cache")
    sys.path.insert(0, str(args.source_root.resolve()))

    async def execute():
        from gene_annotation_episode.literature_episodes import LiteratureEpisodes
        from gene_annotation_episode.runtime import run_workflow
        from gene_annotation_episode.state import Store
        from gene_annotation_episode.tool_configuration import build_tools
        from gene_annotation_episode.composition_information import CONTRACT_INFORMATION_PROFILE
        flags = dict(rate_population=True, a108_context=True, reference_parent_sources=[],
            contract_information_profile=CONTRACT_INFORMATION_PROFILE)
        config = {"public": {"provider_access_dir": str(run / "provider-access")},
            "local_tools": {"minimap2_cache_dir": str(run / "cache/minimap2")}}
        for name in ("pdfinfo", "pdftotext", "pdftoppm"):
            executable = shutil.which(name)
            if executable:
                config["local_tools"][name + "_executable"] = executable
        with Store(run / "state") as store:
            if not args.resume:
                sequence = "".join(args.input.read_text().split()).upper()
                if not sequence.isalpha():
                    raise ValueError("anonymous_raw_protein_sequence_required")
                context = json.loads(args.context.read_text()) if args.context else None
                store.create_problem(raw_sequence=sequence, molecule="protein", caller_context=context)
                (run / "input.txt").write_text(sequence + "\n")
                if context is not None:
                    (run / "context.json").write_text(json.dumps(context, indent=2) + "\n")
                (run / "launch.json").write_text(json.dumps({
                    "started_at": datetime.now(timezone.utc).isoformat(), "goal": GOAL,
                    "input_mode": "anonymous_sequence_with_context" if context is not None else "raw_sequence_only",
                    "sequence_sha256": hashlib.sha256(sequence.encode()).hexdigest(),
                    "sequence_length": len(sequence), "literature_flags": flags,
                    "tool_configuration": config, "python_executable": sys.executable,
                    "source_root": str(args.source_root.resolve()),
                    "models": "repository defaults", "controller": "repository default YieldController",
                    "annotation_child_roles": ["literature"], "preloaded_evidence": [],
                    "scripted_model_decisions": False, "targeted_tests": False,
                    "external_cutoff": None}, indent=2) + "\n")
            initial = [store.targets()[0]["source_ref"]]
            caller_context = store.problem().get("caller_context_source_ref")
            if caller_context:
                initial.append(caller_context)
            result = await run_workflow(store, build_tools(store, config),
                run_dir=run / "workflow", resume=args.resume, goal=GOAL,
                episode_binding_factories=(partial(LiteratureEpisodes, **flags),),
                initial_known_record_refs=initial, annotation_child_roles=("literature",))
            (run / "result.json").write_text(json.dumps(result, indent=2) + "\n")
            print(json.dumps(result), flush=True)

    try:
        asyncio.run(execute())
    except BaseException as error:
        (run / "failure.json").write_text(json.dumps({"type": type(error).__name__,
            "message": str(error), "traceback": traceback.format_exc()}, indent=2) + "\n")
        raise


if __name__ == "__main__":
    main()
