"""Export complete actual pure-adapter examples; no live/custody claim.

Run from the repository with .venv/bin/python.  Pass a new output directory
name to preserve previous attempts.  Native byte sources already retained in
the repository are located by exact digest; source-derived/synthetic bytes are
stored in the input manifest as base64, never described as a live measurement.
"""
from contextlib import ExitStack
from copy import deepcopy
import base64
import builtins
import hashlib
import io
import json
from pathlib import Path
import socket
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from test_bvbrc_phylogeny_bundle_adapter import (
    fixture, consume, numerical_fields, codon_hand_fixture, codon_fields,
    native_codon_fixture, historical_codon_fixture, relationship_fixture,
    relationship_fields, bootstrap_fixture, bootstrap_fields, gene_xml_fixture,
    BOUNDARY, slot,
)
from gene_annotation_episode import bvbrc_phylogeny_bundle_projection as projection
from gene_annotation_episode import bvbrc_phylogeny_bundle_resolution as resolution
from gene_annotation_episode import bvbrc_phylogeny_bundle_contracts as contracts
from gene_annotation_episode.bvbrc_gene_tree_grader import calculate_gene_tree
from gene_annotation_episode.bvbrc_codon_tree_grader import calculate_codon_tree


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def forbidden(*args, **kwargs):
    raise AssertionError("Scientific I/O/parsing forbidden during saved recalculation")


def saved_recalculation(result, provider):
    saved = json.loads(encoded(result))
    calculate = calculate_gene_tree if provider == "gene_tree" else calculate_codon_tree
    with ExitStack() as stack:
        for owner, name in ((builtins, "open"), (io, "open"), (socket, "socket"), (socket, "create_connection"),
                (subprocess, "run"), (subprocess, "Popen"), (Path, "read_bytes"), (Path, "read_text"), (resolution, "parse_reader")):
            stack.enter_context(patch.object(owner, name, forbidden))
        for analysis, component in zip(saved["sheet"]["analyses"], saved["components"]["analyses"]):
            if component["components"] is not None:
                assert calculate(analysis["sheet"], component["components"]["parameters"]) == component["components"]
    return True


def main():
    name = sys.argv[1] if len(sys.argv) == 2 else "EXAMPLES_001"
    if not name.isidentifier():
        raise ValueError("Use one simple new directory name")
    target = Path(__file__).resolve().parent / name
    target.mkdir(exist_ok=False)
    code = {name: digest((ROOT / "gene_annotation_episode" / name).read_bytes()) for name in projection._DEPENDENCIES}
    source_paths = {}
    for directory in (BOUNDARY / "official_example", BOUNDARY / "additional_sources/bvbrc_gene_tree/tests"):
        for path in directory.rglob("*"):
            if path.is_file():
                source_paths.setdefault(digest(path.read_bytes()), []).append(str(path.relative_to(ROOT)))
    cases = [
        ("gene_hand", "gene_tree", fixture, numerical_fields, "synthetic"),
        ("codon_hand", "codon_tree", codon_hand_fixture, codon_fields, "synthetic measurements; source-derived current table syntax"),
        ("gene_relationships", "gene_tree", relationship_fixture, relationship_fields, "synthetic explicitly joined reference/functions/taxa"),
        ("bootstrap_complete", "gene_tree", bootstrap_fixture, bootstrap_fields, "synthetic measurements; source-derived RAxML log syntax"),
        ("bootstrap_partial", "gene_tree", lambda: bootstrap_fixture(partial=True), bootstrap_fields, "synthetic partial forest; conditional frequency retained"),
        ("codon_native", "codon_tree", native_codon_fixture,
            lambda: {**{k: v for k, v in codon_fields().items() if k.startswith("literal_")}, "tips": numerical_fields()["tips"]},
            "retained official native output bytes; synthetic C4 transport records; explicit retained table joins"),
    ]
    history_fields = {
        "mean": {"metric": "worst_sequence_mean", "analysis_id": "a", "family_population_id": "historical", "genome_id": "G1"},
        "ratio": {"metric": "worst_sequence_ratio", "analysis_id": "a", "family_population_id": "historical", "family_id": "F1", "feature_id": "a", "genome_id": "G1"},
        "maximum": {"metric": "worst_sequence_family_maximum", "analysis_id": "a", "family_population_id": "historical", "family_id": "F1"},
    }
    cases.append(("codon_history", "codon_tree", historical_codon_fixture, lambda: history_fields, "synthetic explicitly supplied pretrim observations"))
    for label, filename in (("gene_xml", "Buchnera_acpS_fg_dna_raxml_hky85.xml"),
                            ("gene_xml_rell", "Buchnera_acpS_fg_dna_raxml_hky85_RAxML_tree_rell.xml")):
        cases.append((label, "gene_tree", lambda filename=filename: gene_xml_fixture(filename),
            lambda: {"tips": {"metric": "tree_tip_count", "analysis_id": "a", "population_id": "leaves", "tree": slot("xml", tree=True)}},
            "retained official phyloXML bytes; synthetic C4 transport records; raw-tree absence qualified"))
    missing = fixture(); missing[0]["artifacts"] = [a for a in missing[0]["artifacts"] if a["role"] != "a:alignment"]
    del missing[1]["SYNTHETIC-native/a/alignment"]
    cases.append(("gene_missing_matrix", "gene_tree", lambda: missing,
        lambda: {"tips": numerical_fields()["tips"], "cells": numerical_fields()["cells"]}, "synthetic missing matrix beside valid tree"))
    summary = []
    for label, provider, factory, field_factory, provenance in cases:
        f = factory(); before = deepcopy(f); fields = field_factory()
        result = consume(f, fields, provider=provider)
        assert f == before and result["status"] in ("ok", "partial")
        replayed = saved_recalculation(result, provider)
        manifest = [{"artifact_ref": ref, "sha256": digest(data), "byte_count": len(data),
            "retained_native_paths": source_paths.get(digest(data), []),
            "synthetic_base64": None if digest(data) in source_paths else base64.b64encode(data).decode()}
            for ref, data in sorted(f[1].items())]
        inputs = {"provenance": provenance, "provider": provider, "bundle": f[0], "artifact_bytes": manifest,
            "supplied_values": f[2], "parameters": f[3], "requested_form": contracts.requested_form_schema(fields)}
        input_data, result_data = encoded(inputs), encoded(result)
        (target / (label + ".inputs.json")).write_bytes(input_data)
        (target / (label + ".result.json")).write_bytes(result_data)
        summary.append({"example": label, "provider": provider, "provenance": provenance, "status": result["status"],
            "facts": result["facts"], "input_sha256": digest(input_data), "result_sha256": digest(result_data),
            "result_byte_count": len(result_data), "saved_recalculation_without_io_or_parsing": replayed})
        print(label, result["status"], len(result_data), "bytes; saved replay matched")
    output = {"implementation_sha256": projection.implementation_sha256(), "dependency_sha256": code,
        "examples": summary, "live_execution_verified": False, "host_custody_verified": False,
        "library_selection_verified": False, "episode_communication_verified": False}
    (target / "manifest.json").write_bytes(encoded(output))


if __name__ == "__main__":
    main()
