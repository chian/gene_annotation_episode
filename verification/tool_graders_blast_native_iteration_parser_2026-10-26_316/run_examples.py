"""Export full synthetic extraction/311 examples under local_jobs limits."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def worker(directory):
    sys.path.insert(0, str(ROOT / "tests"))
    from tests.test_blast_native_iteration_records import make_packet, extract, iteration, report, QUERY, MARKER

    definitions = [
        ("psi_positive", {}),
        ("delta_positive", {"program": "deltablast"}),
        ("absent_marker", {"raw": report(suffix=b"")}),
        ("duplicate_markers", {"raw": report(suffix=MARKER + b"\n" + MARKER + b"\r\n")}),
        ("multiple_identical_queries", {"query": QUERY + QUERY}),
        ("native_failed_with_positive", {"returncode": 7}),
        ("incomplete_marker", {"raw": report(suffix=MARKER)}),
        ("unsupported_version", {"raw": report().replace(b"2.17.0+", b"2.16.0+")}),
        ("changed_supplied_query_bytes", {}),
        ("malformed_query_actual_prelaunch_failure", {"query": QUERY + b">empty\n"}),
    ]
    manifest, summaries = [], []
    for name, kwargs in definitions:
        case = directory / name
        packet = make_packet(case / "producer", **kwargs)
        if name == "changed_supplied_query_bytes":
            # An adversarial supplied-byte mutation, not a changed execution
            # receipt or a report rewritten under its original digest.
            packet["query_contents"] = b">q\nACDEFGHK\n"
        extraction = extract(packet)
        sheet, result = iteration(packet, extraction)
        files = {"supplied-report.bin": packet["report_contents"], "supplied-query.bin": packet["query_contents"]}
        objects = {"input.json": {k: v for k, v in packet.items() if k not in ("report_contents", "query_contents")},
                   "extraction.json": extraction, "iteration-sheet.json": sheet, "iteration-components.json": result}
        files.update({filename: (json.dumps(obj, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode()
                      for filename, obj in objects.items()})
        for filename, raw in files.items():
            (case / filename).write_bytes(raw)
            manifest.append(dict(example=name, path=str((case / filename).relative_to(directory)),
                classification="source_derived_synthetic", size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
        summaries.append(dict(example=name, classification="source_derived_synthetic", extraction_status=extraction["status"],
            native_returncode=packet["bundle"]["process"]["returncode"], native_process_started=packet["bundle"]["process"]["started"],
            query_record_count=extraction["query"]["record_count"], marker_count=len(extraction["markers"]),
            extracted_record_count=len(extraction["convergence_records"]),
            query_native_converged=[r["native_converged"]["value"] for r in result["convergence_observations"]],
            search_native_converged=[r["native_converged"]["value"] for r in result["searches"]],
            search_counts=[{k: v["value"] for k, v in r["counts"].items()} for r in result["searches"]],
            issue_codes=[r["code"] for r in extraction["issues"]]))
    (directory / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (directory / "NUMERICAL_SUMMARY.json").write_text(json.dumps(summaries, indent=2) + "\n")
    print(json.dumps(summaries, indent=2))


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
    result = run_local_job(command, cwd=directory, policy=policy, stdout_path=directory / "stdout.txt",
        stderr_path=directory / "stderr.txt", env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1",
            "TMPDIR": str(temporary), "XDG_CACHE_HOME": str(directory / "cache")})
    (directory / "receipt.json").write_text(json.dumps(dict(command=command, policy=policy.to_dict(),
        returncode=result.returncode, metadata=result.metadata, evidence_kind="source_derived_synthetic; no BLAST execution"), indent=2) + "\n")
    print(json.dumps({"returncode": result.returncode, "receipt": str(directory / "receipt.json")}))
    if result.returncode:
        print((directory / "stderr.txt").read_text())
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
