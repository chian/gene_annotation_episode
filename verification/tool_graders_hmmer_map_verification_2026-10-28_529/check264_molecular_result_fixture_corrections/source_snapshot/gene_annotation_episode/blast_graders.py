"""Callable BLAST tool graders and a file-based verification entrypoint.

Input acquisition remains with the caller/owning episode. These functions only
parse supplied output and calculate tool-specific measurements. They do not
assign annotation credit, submit jobs, retrieve metadata or invoke an LLM.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .blast_grading_inputs import parse_blast_json, parse_blast_tabular
from .blast_pairwise_grader import build_pairwise_sheet, build_pairwise_artifacts
from .alignment_correspondence import ARTIFACT_SCHEMA
from .blast_database_grader import build_database_sheet, calculate_database_probabilities


def grade_blast_result(content: bytes, *, mode: str, resource: str,
                       output_format: str, request: dict | None = None,
                       fields: list[str] | None = None,
                       reference_metadata: list[dict] | None = None,
                       target_context: dict | None = None,
                       database_profile: dict | None = None,
                       model: dict | None = None,
                       _retain_correspondence: bool = False) -> dict:
    """Return an internal sheet and, for database searches, model probabilities.

    Resource is provenance, not parser selection: API/HPC JSON use the same
    native format parser. Tabular output uses its declared field specification.
    This function does not restrict what an episode may commission; in these
    examples local database execution is deliberately not provided.
    """
    if type(_retain_correspondence) is not bool:
        raise ValueError("blast_private_retention_flag_invalid")
    if output_format == "json2":
        normalized = parse_blast_json(content, mode=mode, resource=resource, request=request)
    elif output_format == "tabular":
        normalized = parse_blast_tabular(content, mode=mode, resource=resource,
                                        request=request, fields=fields)
    else:
        raise ValueError("unsupported_blast_grading_format")
    if mode == "pairwise":
        if any(value is not None for value in (reference_metadata, target_context, database_profile, model)):
            raise ValueError("database_grading_inputs_not_used_by_pairwise_comparison")
        if not _retain_correspondence:
            return {"sheet": build_pairwise_sheet(normalized), "probabilities": None}
        sheet, common_sheet, calculated = build_pairwise_artifacts(normalized)
        return {"sheet": sheet, "probabilities": None, "correspondence": {
            "version": ARTIFACT_SCHEMA, "instances": [{"legacy_pointer": "/sheet", "axis_basis": "reported",
                "sheet": common_sheet, "components": calculated}]}}
    if mode != "database":
        raise ValueError("unsupported_blast_grading_mode")
    sheet = build_database_sheet(normalized, reference_metadata=reference_metadata,
        target_context=target_context, database_profile=database_profile,
        _retain_correspondence=_retain_correspondence)
    correspondence = sheet.pop("correspondence", None)
    result = {"sheet": sheet, "probabilities": calculate_database_probabilities(sheet, model=model)}
    if _retain_correspondence:
        for instance in correspondence["instances"]:
            instance["legacy_pointer"] = "/sheet" + instance["legacy_pointer"]
        result["correspondence"] = correspondence
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=("pairwise", "database"), required=True)
    parser.add_argument("--resource", choices=("api", "hpc", "local"), required=True)
    parser.add_argument("--format", dest="output_format", choices=("json2", "tabular"), required=True)
    parser.add_argument("--fields", nargs="+")
    for name in ("request", "reference-metadata", "target-context", "database-profile", "model"):
        parser.add_argument("--" + name, type=Path)
    args = vars(parser.parse_args(argv))
    source, destination = args.pop("input"), args.pop("output")
    for key in ("request", "reference_metadata", "target_context", "database_profile", "model"):
        if args[key] is not None:
            args[key] = json.loads(args[key].read_text())
    result = grade_blast_result(source.read_bytes(), **args)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"output": str(destination), "mode": args["mode"],
                      "resource": args["resource"], "format": args["output_format"]}))


if __name__ == "__main__":
    main()
