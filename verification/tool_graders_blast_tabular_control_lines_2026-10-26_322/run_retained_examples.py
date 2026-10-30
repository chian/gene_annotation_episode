"""Reinterpret retained source-derived fixtures without rerunning their producer."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOURCES = ROOT / "verification/tool_graders_blast_native_iteration_parser_2026-10-26_316/examples002"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_json(path):
    return json.loads(path.read_bytes())


def verify_originals(manifest):
    for item in manifest:
        raw = (SOURCES / item["path"]).read_bytes()
        assert len(raw) == item["size_bytes"] and digest(raw) == item["sha256"], item["path"]


def worker(directory):
    from gene_annotation_episode.blast_report_collection import parse_blast_report_collection
    from gene_annotation_episode.blast_native_iteration_records import extract_blast_tabular7_convergence
    from gene_annotation_episode.blast_iteration_inputs import populate_blast_iteration_sheet
    from gene_annotation_episode.blast_iteration_calculators import calculate_blast_iteration_components

    original_manifest = read_json(SOURCES / "MANIFEST.json")
    verify_originals(original_manifest)
    manifest, summaries = [], []
    for name in dict.fromkeys(item["example"] for item in original_manifest):
        source = SOURCES / name
        packet = read_json(source / "input.json")
        previous_collection = packet["collection"]
        previous_components = read_json(source / "iteration-components.json")
        raw = (source / "supplied-report.bin").read_bytes()
        query = (source / "supplied-query.bin").read_bytes()
        descriptors = [{k: v for k, v in item.items() if k not in {"sha256", "size_bytes"}}
                       for item in previous_collection["artifacts"]]
        collection = parse_blast_report_collection({packet["artifact_key"]: raw},
            artifacts=descriptors, invocation=previous_collection["invocation"])
        packet.update(collection=collection, report_contents=raw, query_contents=query)
        extraction = extract_blast_tabular7_convergence(**packet)
        report_sources = [dict(search_key=search["search_key"], report_source=dict(
            artifact_key=packet["artifact_key"], artifact_ref=packet["source_ref"],
            member_ordinal=None, member_sha256=None)) for search in collection["searches"]]
        sheet = populate_blast_iteration_sheet(collection, report_sources=report_sources,
            query_bindings=[], search_bindings=[], pssm_sheets=[], checkpoint_bindings=[],
            sequence_metadata=[], profile_metadata=[], comparison_pairs=[], inclusion_records=[],
            convergence_records=extraction["convergence_records"])
        components = calculate_blast_iteration_components(sheet)
        case = directory / name
        case.mkdir()
        objects = {"collection.json": collection, "extraction.json": extraction,
                   "iteration-sheet.json": sheet, "iteration-components.json": components}
        for filename, value in objects.items():
            encoded = (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode()
            (case / filename).write_bytes(encoded)
            manifest.append(dict(example=name, path=str((case / filename).relative_to(directory)),
                classification="retained_source_derived_synthetic", size_bytes=len(encoded), sha256=digest(encoded)))
        counts = lambda result: [{k: v["value"] for k, v in search["counts"].items()}
                                 for search in result["searches"]]
        summary = dict(example=name, classification="retained_source_derived_synthetic",
            source_directory=str(source), source_report_sha256=digest(raw), source_query_sha256=digest(query),
            before_counts=counts(previous_components), after_counts=counts(components),
            query_native_converged=[r["native_converged"]["value"] for r in components["convergence_observations"]],
            search_native_converged=[r["native_converged"]["value"] for r in components["searches"]],
            extraction_status=extraction["status"], extractor_unchanged=extraction == read_json(source / "extraction.json"))
        assert summary["extractor_unchanged"], name
        assert all(v is None for v in summary["search_native_converged"]), name
        if name in {"psi_positive", "delta_positive"}:
            assert summary["before_counts"][0]["observed_hsp_count"] == 3
            assert summary["after_counts"] == [dict(reported_hit_count=2, reported_hsp_count=2,
                observed_hsp_count=2, parsed_hit_count=2, parsed_hsp_count=2, declared_alignment_row_count=2)]
            assert summary["query_native_converged"] == [True]
            assert collection["artifacts"][0]["sha256"] == digest(raw)
        if name in {"unsupported_version", "incomplete_marker", "absent_marker"}:
            assert collection == previous_collection, name
            assert components == previous_components, name
        summaries.append(summary)
    verify_originals(original_manifest)
    (directory / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (directory / "NUMERICAL_SUMMARY.json").write_text(json.dumps(summaries, indent=2) + "\n")
    (directory / "ORIGINAL_SOURCES.json").write_text(json.dumps(dict(
        directory=str(SOURCES), verified_before_and_after=True, files=deepcopy(original_manifest)), indent=2) + "\n")
    print(json.dumps(dict(original_files_verified=len(original_manifest), generated_files=len(manifest),
                         examples=len(summaries), all_extractor_results_unchanged=True)))


def main():
    if sys.argv[1] == "--worker":
        worker(Path(sys.argv[2]))
        return 0
    from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job
    directory = HERE / sys.argv[1]
    directory.mkdir()
    temporary = directory / "temporary"
    temporary.mkdir()
    command = [str(ROOT / ".venv/bin/python"), "-B", str(Path(__file__).resolve()), "--worker", str(directory)]
    policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
    result = run_local_job(command, cwd=directory, policy=policy,
        stdout_path=directory / "stdout.txt", stderr_path=directory / "stderr.txt",
        env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(temporary),
             "XDG_CACHE_HOME": str(directory / "cache")})
    (directory / "receipt.json").write_text(json.dumps(dict(command=command, policy=policy.to_dict(),
        returncode=result.returncode, metadata=result.metadata,
        evidence_kind="new interpretation of retained source-derived synthetic bytes; no producer or native BLAST execution"), indent=2) + "\n")
    print(json.dumps({"returncode": result.returncode, "receipt": str(directory / "receipt.json")}))
    print((directory / "stdout.txt").read_text())
    print((directory / "stderr.txt").read_text())
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
