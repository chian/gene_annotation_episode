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
