"""Export complete synthetic library payloads and actual pure-provider outputs.

Run from the checkout root using .venv/bin/python. No native service, scientific
executable or model is called. The parent owns connected episode verification.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
DESTINATION = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from jsonschema import Draft202012Validator
from gene_annotation_episode.bvbrc_application_definitions import prepare_application
from gene_annotation_episode.bvbrc_appservice_contracts import validate_contract
from test_bvbrc_phylogeny_tool_info import CASES, entry_for, launch_payload, result_payload


def digest(path):
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
            "sha256": hashlib.sha256(data).hexdigest(), "byte_count": len(data)}


def save(name, value):
    (DESTINATION / name).write_text(json.dumps(value, indent=2, sort_keys=True,
        ensure_ascii=False, allow_nan=False) + "\n")


def main():
    examples = []
    for provider, mode, application, adapter in CASES:
        entry = entry_for(provider, mode)
        launch = launch_payload(mode)
        result, (bundle, data, values, parameters) = result_payload(provider, mode, adapter)
        form = result["selector"]["requested_schema"]
        validator = Draft202012Validator(entry["input_schema"])
        validator.validate(launch)
        validator.validate(result)
        validate_contract("AppServiceRequest", launch["request"])
        validate_contract("ResultSelector", result["selector"])
        prepared = prepare_application(application, launch["request"]["parameters"], {})
        assert prepared["status"] == "ok"
        frozen = deepcopy((bundle, data, values, parameters, form))
        actual = adapter.consume_bundle(bundle, artifact_bytes=data, supplied_values=values,
            requested_form=form, parameters=parameters)
        assert actual["status"] in ("ok", "partial")
        assert actual["facts"]["tips"] == 4 and actual["facts"]["gap_fraction"] == 0.125
        validator = Draft202012Validator(form)
        validator.validate(actual["facts"])
        assert frozen == (bundle, data, values, parameters, form)
        examples.append({"scientific_input_kind": "explicitly_synthetic_fixture",
            "service_execution": "not_run", "mode": mode, "entry": entry,
            "launch_assignment": launch, "native_preparation": prepared,
            "results_assignment": result, "bundle": bundle,
            "artifact_bytes_utf8": {key: value.decode("utf-8") for key, value in data.items()},
            "supplied_values": values, "complete_provider_result": actual,
            "provider_implementation_sha256": adapter.implementation_sha256()})
    save("FILLED_EXAMPLES.json", examples)
    source_files = [
        "gene_annotation_episode/bvbrc_application_specs/original/GeneTree.json",
        "gene_annotation_episode/bvbrc_application_specs/original/CodonTree.json",
        "verification/tool_graders_bvbrc_application_artifacts_2026-10-24/sources/bvbrc_gene_tree/service-scripts/App-GeneTree.pl",
        "verification/tool_graders_bvbrc_application_artifacts_2026-10-24/sources/bvbrc_gene_tree/lib/Sequence_Alignment.pm",
        "verification/tool_graders_bvbrc_application_artifacts_2026-10-24/sources/bvbrc_gene_tree/lib/Tree_Builder.pm",
        "verification/tool_graders_bvbrc_application_artifacts_2026-10-24/sources/codon_trees/service-scripts/App-CodonTree.pl",
        "gene_annotation_episode/bvbrc_homology_tool_info.py",
        "gene_annotation_episode/bvbrc_appservice_tool_info.py",
        "gene_annotation_episode/bvbrc_application_definitions.py",
        "gene_annotation_episode/bvbrc_phylogeny_bundle_contracts.py",
        "gene_annotation_episode/bvbrc_gene_tree_bundle_adapter.py",
        "gene_annotation_episode/bvbrc_codon_tree_bundle_adapter.py",
    ]
    save("INSPECTED_FILES.json", {"files": [digest(ROOT / path) for path in source_files],
        "scope": "Complete native wrappers, GeneTree sequence/tree producer modules, actual schema owners and relevant consumers read; no live source-version verification."})
    print(json.dumps({"exported_modes": [row["mode"] for row in examples],
        "numerical_examples": {"tips": 4, "cells": 16, "gap_fraction": 0.125,
                               "selected_branch_lengths": [0, -0.1]},
        "full_examples": str(DESTINATION / "FILLED_EXAMPLES.json"),
        "service_or_model_calls": 0}, indent=2))


if __name__ == "__main__":
    main()
