"""Explicit workspace registration, ordinary tools and the shared Episode runtime."""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tomllib

from .boundary_validation import parse_json_object
from .domain import MOLECULES, ROLES
from .state import Store
from .tool_configuration import build_tools
from .material_parsing import FORMATS


def _print(value):
    print(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False))


def parser():
    result = argparse.ArgumentParser(prog="gene-episode")
    sub = result.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Register immutable caller material; inferred biology remains revisable.")
    init.add_argument("--workspace", type=Path, required=True)
    inputs = init.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--input", type=Path)
    inputs.add_argument("--sequence")
    inputs.add_argument("--manifest", type=Path)
    init.add_argument("--molecule", choices=MOLECULES, default="unspecified")
    init.add_argument("--role", choices=ROLES, default="unspecified")
    init.add_argument("--context", type=Path, help="Caller-supplied sample, environment, handling or growth context JSON.")
    init.add_argument("--format", choices=FORMATS, default="auto", help="File wrapper interpretation; --sequence is explicitly raw. This does not classify the molecule.")
    add = sub.add_parser("add-material", help="Retain another caller evidence asset without changing the fixed target binding.")
    add.add_argument("--workspace", type=Path, required=True)
    add.add_argument("--input", type=Path, required=True)
    add.add_argument("--format", choices=FORMATS, default="auto")
    add.add_argument("--molecule", choices=MOLECULES, default="unspecified")
    add.add_argument("--role", choices=ROLES, default="unspecified")
    add.add_argument("--name")
    for name in ("status", "capabilities", "tool", "run", "artifact", "export"):
        command = sub.add_parser(name)
        command.add_argument("--workspace", type=Path, required=True)
        if name in {"tool", "run", "capabilities", "export"}:
            command.add_argument("--config", type=Path)
        if name == "status":
            command.add_argument("--limit", type=int, default=100)
            command.add_argument("--offset", type=int, default=0)
        elif name == "tool":
            command.add_argument("name")
            command.add_argument("--args", default="{}")
            command.add_argument("--scope")
        elif name == "run":
            command.add_argument("--run-dir", type=Path)
            command.add_argument("--resume", action="store_true")
            command.add_argument("--goal")
        elif name == "artifact":
            command.add_argument("--ref", required=True)
            command.add_argument("--output", type=Path, required=True)
        elif name == "export":
            command.add_argument("--output", type=Path, required=True)
            command.add_argument("--format", choices=("json", "gff3"), default="json")
            command.add_argument("--scope")
            command.add_argument("--include-credit", action="store_true")
            command.add_argument("--include-artifacts", action="store_true")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        with Store(args.workspace) as store:
            if args.command == "init":
                context = parse_json_object(args.context.read_text()) if args.context else None
                problem = store.create_problem(args.input, raw_sequence=args.sequence, manifest_path=args.manifest,
                    molecule=args.molecule, role=args.role, caller_context=context, format=args.format)
                _print({"problem": problem, "targets": store.targets()})
                return 0
            if args.command == "add-material":
                material = store.register_material(args.input, use="evidence", name=args.name,
                    format=args.format, molecule=args.molecule, role=args.role)
                _print({"material": material, "target_binding_changed": False,
                    "parse_with": {"tool": "material.parse", "arguments": {"material_ref": material["id"]}}})
                return 0
            if args.command == "artifact":
                body = store.get_artifact(args.ref)
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_bytes(body)
                _print({"artifact_ref": args.ref, "output": str(args.output.resolve()), "bytes": len(body)})
                return 0
            if args.command == "status":
                if args.limit < 1 or args.offset < 0:
                    raise ValueError("invalid_status_page")
                annotations = store.current_annotations(limit=args.limit+1, offset=args.offset)
                _print({"problem": store.problem(), "targets": store.targets(),
                    "record_counts": {row[0]: row[1] for row in store.db.execute(
                        "SELECT record_type,COUNT(*) FROM records GROUP BY record_type")},
                    "current_annotations": annotations[:args.limit],
                    "annotation_page": {"offset": args.offset, "limit": args.limit,
                        "total": store.count("annotation", current=True),
                        "next_offset": args.offset+args.limit if len(annotations)>args.limit else None}})
                return 0
            config = tomllib.loads(args.config.read_text()) if args.config else None
            if args.command == "export":
                from .export import export_annotation
                _print(export_annotation(store, args.output, format=args.format,
                    scope=parse_json_object(args.scope) if args.scope else None,
                    include_credit=args.include_credit, credit_policy=(config or {}).get("credit"),
                    include_artifacts=args.include_artifacts))
                return 0
            genome = (config or {}).get('genome_investigation')
            if genome is not None:
                if (not isinstance(genome, dict)
                        or set(genome) != {'version', 'policy', 'services'}
                        or genome['version'] != 'combined_genome_investigation_v1'
                        or not isinstance(genome['policy'], dict)
                        or not isinstance(genome['services'], dict)
                        or 'root_task' not in genome['policy']
                        or 'annotation_support' not in genome['policy']
                        or set(config) & {'credit', 'controller'}):
                    raise ValueError('explicit_combined_genome_policy_and_services_required')
                from .all_evidence_tools import AllEvidenceToolRegistry
                tools = build_tools(store, config, registry_class=AllEvidenceToolRegistry)
            else:
                tools = build_tools(store, config)
            if args.command == "capabilities":
                _print(tools.catalog())
                return 0
            if args.command == "tool":
                result = tools.execute(args.name, parse_json_object(args.args),
                                       scope=parse_json_object(args.scope) if args.scope else None)
                _print(result)
                return 0 if result["status"] in {"completed", "partial"} else 1
            from .runtime import run_workflow
            if not store.targets():
                _print({"status": "operational_unavailable", "code": "biological_target_binding_unavailable",
                    "target_binding": store.problem().get("target_binding"),
                    "available_work": ["material.parse", "material.read", "material.members", "material.member", "source.read"],
                    "scientific_completion": "not_established"})
                return 1
            run_dir = args.run_dir
            if run_dir is None and not args.resume:
                run_dir = store.path/"runs"/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
            run_options = {'provider_config': config, 'run_dir': run_dir,
                'resume': args.resume, 'goal': args.goal}
            if genome is None:
                run_options['credit_policy'] = (config or {}).get('credit')
            else:
                from .execution_episodes import ExecutionEpisodes
                from .episode_monitoring import MonitorEpisodes
                from .genome_investigation import GenomeEvidenceServices
                from .hpc_episodes import HPCEpisodes
                from .investigation_policy import create_policy
                from .literature_episodes import LiteratureEpisodes
                from .resource_estimation import ResourceToolEstimator
                from .scientific_process_episodes import ScientificProcessEpisodes

                roles = tuple(dict.fromkeys((*ScientificProcessEpisodes.roles,
                    *LiteratureEpisodes.roles, *ExecutionEpisodes.roles,
                    *MonitorEpisodes.roles, *HPCEpisodes.roles)))
                policy = create_policy(genome['policy'], episode_roles=roles)
                services = GenomeEvidenceServices(**genome['services'])
                run_options.update(project_credit=policy.project_task_credit,
                    project_annotation_score=policy.project_annotation_score,
                    controller_factory=policy.controller_factory,
                    initial_known_record_refs=policy.initial_known_record_refs,
                    native_timing_information=policy.native_timing_information,
                    binding_definitions={'credit': policy.task_credit_definition,
                        'controller': policy.controller_definition,
                        'annotation_score': policy.annotation_score_definition},
                    episode_service_factory=services,
                    episode_service_binding=services.as_record(),
                    episode_service_inputs='actual_tool_registry_v1',
                    episode_record_receipts=policy.episode_record_receipts,
                    annotation_child_roles=('scientific_process',),
                    resource_estimator=ResourceToolEstimator())
            summary = asyncio.run(run_workflow(store, tools, **run_options))
            _print(summary)
            return 0
    except KeyboardInterrupt:
        _print({"status": "externally_interrupted", "scientific_completion": "not_established"})
        return 130
    except Exception as error:
        _print({"status": "operational_failure", "error_type": type(error).__name__, "detail": str(error),
            **({"error_detail": error.detail} if getattr(error,"detail",None) else {})})
        return 1


if __name__ == "__main__":
    sys.exit(main())
