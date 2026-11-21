"""Workspace registration, inspection and export."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .boundary_validation import parse_json_object
from .domain import MOLECULES, ROLES
from .state import Store
from .material_parsing import FORMATS


def _print(value):
    print(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False, default=str))


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
    for name in ("status", "artifact", "export"):
        command = sub.add_parser(name)
        command.add_argument("--workspace", type=Path, required=True)
        if name == "status":
            command.add_argument("--limit", type=int, default=100)
            command.add_argument("--offset", type=int, default=0)
        elif name == "artifact":
            command.add_argument("--ref", required=True)
            command.add_argument("--output", type=Path, required=True)
        elif name == "export":
            command.add_argument("--output", type=Path, required=True)
            command.add_argument("--format", choices=("json", "gff3"), default="json")
            command.add_argument("--scope", required=True)
            command.add_argument("--include-credit", action="store_true")
            command.add_argument("--include-artifacts", action="store_true")
    run = sub.add_parser("run", help="Run an episode and everything below it from the caller's commission, to the end.")
    run.add_argument("--workspace", type=Path, required=True)
    run.add_argument("--entry", required=True, help="The entry binding path, for example sequence_homology_evidence.")
    run.add_argument("--commission", type=Path, required=True, help="JSON {assignment, message, selection}: what a parent sends.")
    for command in (run, sub.add_parser("resume", help="Replay a recorded run; recorded units and model calls are not made again.")):
        if command is not run:
            command.add_argument("--workspace", type=Path, required=True)
        command.add_argument("--continuation", type=Path, required=True, help="JSON: binding path -> yield controller settings.")
        command.add_argument("--services", type=Path, required=True, help="JSON: the job services configuration.")
        command.add_argument("--run-id", required=True)
        command.add_argument("--journal", type=Path, required=True)
        command.add_argument("--model-calls", type=Path, required=True, help="A new directory for the model provider's calls.")
    shown = sub.add_parser("report", help="What the journal recorded of a run: episodes, units, model answers, controller steps.")
    shown.add_argument("--workspace", type=Path, required=True)
    shown.add_argument("--run-id", required=True)
    shown.add_argument("--journal", type=Path, required=True)
    proposed = sub.add_parser("propose-annotation", help="Register the caller's proposed annotation of a subject (one hypothesis record).")
    proposed.add_argument("--workspace", type=Path, required=True)
    proposed.add_argument("--subject", required=True)
    proposed.add_argument("--predicate", required=True)
    proposed.add_argument("--value", required=True, help="JSON: the typed value of the hypothesis.")
    frozen = sub.add_parser("freeze-libraries", help="Freeze the libraries of every axis a run covers, where the run reads them, and print each axis selection.")
    frozen.add_argument("--workspace", type=Path, required=True)
    frozen.add_argument("--source", type=Path, required=True, help="The published process library to freeze.")
    frozen.add_argument("--continuation", type=Path, required=True, help="JSON: the run's own continuation file (binding path -> settings); it names the axis heads and where each reads its libraries.")
    frozen.add_argument("--axis", help="Optional: freeze only this axis, for example A105. Default: every axis head in the continuation.")
    frozen.add_argument("--tool", action="append", default=[], help="A tool of the tool registry to offer; may repeat.")
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
                    "record_counts": {row[0]: row[1] for row in store._db.execute(
                        "SELECT record_type,COUNT(*) FROM records GROUP BY record_type")},
                    "current_annotations": annotations[:args.limit],
                    "annotation_page": {"offset": args.offset, "limit": args.limit,
                        "total": store.count("annotation", current=True),
                        "next_offset": args.offset+args.limit if len(annotations)>args.limit else None}})
                return 0
            if args.command in ("run", "resume", "report", "propose-annotation", "freeze-libraries"):
                from . import run_command
                if args.command == "run":
                    _print(run_command.run(store, entry=args.entry, commission=run_command.read_json(args.commission),
                        continuation=run_command.read_json(args.continuation),
                        services=run_command.read_json(args.services), run_id=args.run_id, journal=args.journal,
                        model_calls=args.model_calls))
                elif args.command == "resume":
                    _print(run_command.resume_run(store, continuation=run_command.read_json(args.continuation),
                        services=run_command.read_json(args.services), run_id=args.run_id, journal=args.journal,
                        model_calls=args.model_calls))
                elif args.command == "report":
                    _print(run_command.report(run_id=args.run_id, journal=args.journal))
                elif args.command == "propose-annotation":
                    _print(run_command.propose_annotation(store, subject=args.subject, predicate=args.predicate,
                        value=parse_json_object(args.value)))
                else:
                    _print(run_command.freeze_libraries(store, source=args.source,
                        continuation=run_command.read_json(args.continuation), tools=args.tool, axis=args.axis))
                return 0
            if args.command == "export":
                from .export import export_annotation
                _print(export_annotation(store, args.output, format=args.format,
                    scope=parse_json_object(args.scope),
                    include_credit=args.include_credit,
                    include_artifacts=args.include_artifacts))
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
