"""Retain final verification bytes and source pins; no scientific calculation."""
from pathlib import Path
import hashlib
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent
OWNED = ["native_blast_database_metadata", "native_blast_database_result_worker",
    "native_blast_database_result_views", "native_blast_database_result_publication",
    "native_blast_database_results", "native_blast_database_returns", "native_blast_database_tool_info",
    "execution_progress", "execution_episodes"]
DEPENDENCIES = ["blast_vdb_function_inputs", "blast_vdb_function_calculators",
    "native_blast_vdb_function_metadata", "episode_receipts"]


def encoded(value):
    return json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n"


def record(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))


def audit(directory):
    plan = json.loads((PACKET / "FINAL_EVIDENCE_PLAN_001.json").read_bytes())
    (directory / "PLAN.json").write_text(encoded(plan))
    runs = [PACKET / row["run"] for row in plan["runs"]]
    expected = {row["run"]: row for row in plan["runs"]}
    critical = {f"gene_annotation_episode/{name}.py" for name in OWNED + DEPENDENCIES}
    sources, inventories, evidence = [], [], []
    evidence_names = {"typed-return.json", "census-policy-typed-return.json", "parent-return-union.json",
        "saved-typed-return.json", "saved-model-repair.json", "hsp-reverse-order.json", "saved-purity.json",
        "incompatible-saved-version-results.json", "rejected-original.json", "authority-failures.json",
        "numerical-row-oracle.json", "legacy-byte-equivalence.json", "legacy-import-closure.txt"}
    for run in runs:
        before = json.loads((run / "source-before.json").read_bytes())
        after = json.loads((run / "source-after.json").read_bytes())
        left, right = ({r["path"]: r["sha256"] for r in rows} for rows in (before, after))
        differences = [dict(path=path, before_sha256=left.get(path), after_sha256=right.get(path))
            for path in sorted(set(left) | set(right)) if left.get(path) != right.get(path)]
        assert critical <= set(left) & set(right)
        assert not critical.intersection(row["path"] for row in differences)
        receipt = json.loads((run / "receipt.json").read_bytes())
        assert receipt["returncode"] == expected[run.name]["returncode"]
        sources.append(dict(run=run.name, sources_before=before, sources_after=after,
            source_differences=differences, critical_sources_stable=True, receipt=receipt,
            interpretation=expected[run.name]["interpretation"],
            pytest_summary=(run / "stdout.txt").read_text().splitlines()[-1]))
        for path in sorted(run.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            item = record(path)
            inventories.append(item)
            if path.name in evidence_names:
                evidence.append(item)
    (directory / "ARTIFACT_INVENTORY.json").write_text(encoded(inventories))
    (directory / "EVIDENCE_INDEX.json").write_text(encoded(evidence))
    # A compact index of already saved numerical cells, without arithmetic or
    # another scientific invocation. Labels follow the retained test's explicit
    # parameter order; the complete source sheet/components remain indexed.
    numerical = []
    for index, label in enumerate(("temperature1", "temperature2", "source_cap", "census_bridge",
            "translated_siblings", "underflow", "out_of_range", "zero_prior", "unassigned", "missing_snapshot", "wrong_snapshot")):
        path = PACKET / "run012/pytest" / f"test_actual_calculator_values_{index}" / "numerical-row-oracle.json"
        value = json.loads(path.read_bytes())
        numerical.append(dict(case_label=label, source=record(path), model=value["model"],
            path_kind="Pure delivered calculator through production worker row builder; actual parent-form cases are separately indexed.",
            rows=[row for row in value["rows"] if row["family"] in {"vdb_function", "vdb_function_summary"}]))
    (directory / "NUMERICAL_PROJECTIONS.json").write_text(encoded(numerical))

    final_run = PACKET / plan["final_source_run"]
    final_before = {r["path"]: r for r in json.loads((final_run / "source-before.json").read_bytes())}
    pins = []
    for name in OWNED + DEPENDENCIES:
        item = record(ROOT / "gene_annotation_episode" / (name + ".py"))
        assert item["sha256"] == final_before[item["path"]]["sha256"]
        item["ownership"] = "347 integration, including accepted352 receiver repair" if name in OWNED else "released dependency"
        pins.append(item)
    for name in plan["owned_tests"]:
        item = record(ROOT / "tests" / name)
        assert item["sha256"] == final_before[item["path"]]["sha256"]
        item["ownership"] = "347 exact owned test or narrow authorized extension"
        pins.append(item)
    (directory / "SOURCE_PINS.json").write_text(encoded(pins))

    # Store each still-present, checksum-matching declared implementation file
    # once by digest. Historical requests and deliberately rejected protocol
    # fixtures stay identifiable; unavailable declared bytes are not relabelled
    # as verified current implementation.
    implementation, malformed_declarations = {}, []
    loaded_paths = {run.name: set() for run in runs}
    for run in runs:
        for path in run.rglob("*.json"):
            if "request" not in path.name:
                continue
            try:
                value = json.loads(path.read_bytes())
            except (ValueError, OSError):
                continue
            if not isinstance(value, dict) or not isinstance(value.get("implementation"), dict):
                continue
            files = value["implementation"].get("files", [])
            if not isinstance(files, list):
                malformed_declarations.append(dict(request=str(path.relative_to(ROOT)), value=files))
                continue
            for item in files:
                if not isinstance(item, dict) or not all(isinstance(item.get(k), str) for k in ("module", "sha256", "path")):
                    malformed_declarations.append(dict(request=str(path.relative_to(ROOT)), value=item))
                    continue
                key = (item["module"], item["sha256"], item["path"])
                actual = Path(item["path"])
                if actual.resolve().is_relative_to(ROOT / "gene_annotation_episode"):
                    loaded_paths[run.name].add(str(actual.resolve().relative_to(ROOT)))
                if key in implementation:
                    continue
                copied = dict(item)
                copied["declaration_request"] = str(path.relative_to(ROOT))
                if not actual.resolve().is_relative_to(ROOT):
                    copied["retention_status"] = "outside_checkout_declaration"
                else:
                    snapshot = run / "source" / actual.resolve().relative_to(ROOT)
                    candidates = [p for p in (snapshot, actual) if p.is_file()]
                    exact = next((p for p in candidates if hashlib.sha256(p.read_bytes()).hexdigest() == item["sha256"]), None)
                    if exact is not None:
                        raw, sha = exact.read_bytes(), item["sha256"]
                        target = directory / "implementation" / sha
                        target.parent.mkdir(exist_ok=True)
                        if not target.exists():
                            target.write_bytes(raw)
                        copied.update(retention_status="exact_bytes_retained", retained_path=str(target.relative_to(ROOT)),
                            retained_from=str(exact.relative_to(ROOT)), size_bytes=len(raw))
                    elif not actual.is_file():
                        copied["retention_status"] = "declared_path_absent"
                    else:
                        copied.update(retention_status="declared_digest_differs", actual_sha256=hashlib.sha256(actual.read_bytes()).hexdigest())
                implementation[key] = copied
    for row in sources:
        declared = loaded_paths[row["run"]]
        assert not declared.intersection(item["path"] for item in row["source_differences"])
        row["declared_package_implementation_paths"] = sorted(declared)
        row["changed_paths_in_declared_package_implementation"] = []
        row["declared_paths_not_in_source_snapshot"] = sorted(declared - {item["path"] for item in row["sources_before"]})
        row["declared_package_snapshot_coverage_complete"] = not row["declared_paths_not_in_source_snapshot"]
    (directory / "RUNS.json").write_text(encoded(sources))
    (directory / "IMPLEMENTATION_FILES.json").write_text(encoded(list(implementation.values())))
    (directory / "MALFORMED_IMPLEMENTATION_DECLARATIONS.json").write_text(encoded(malformed_declarations))
    summary = dict(runs=[r.name for r in runs], indexed_files=len(inventories), evidence_files=len(evidence),
        source_pins=len(pins), implementation_declarations=len(implementation),
        exact_implementation_files=sum(r["retention_status"] == "exact_bytes_retained" for r in implementation.values()),
        source_differences_by_run={row["run"]: row["source_differences"] for row in sources},
        critical_and_snapshotted_declared_package_implementation_stable_within_each_run=True,
        all_declared_package_paths_have_before_after_snapshots=all(row["declared_package_snapshot_coverage_complete"] for row in sources),
        scope="Synthetic supplied-byte verification; no live database/API/HPC/model execution or scientific recalculation by this audit.")
    (directory / "SUMMARY.json").write_text(encoded(summary))
    print(encoded(summary))


if __name__ == "__main__":
    directory = PACKET / "final_evidence_001"
    if "--worker" in sys.argv:
        audit(directory)
    else:
        sys.path.insert(0, str(ROOT))
        from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job
        directory.mkdir(exist_ok=False)
        command = [str(ROOT / ".venv/bin/python"), "-B", str(Path(__file__).resolve()), "--worker"]
        policy = LocalJobPolicy(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None)
        (directory / "request.json").write_text(encoded(dict(command=command, policy=policy.to_dict(),
            audit_script=record(Path(__file__).resolve()), plan=record(PACKET / "FINAL_EVIDENCE_PLAN_001.json"))))
        result = run_local_job(command, cwd=directory, policy=policy,
            stdout_path=directory / "stdout.txt", stderr_path=directory / "stderr.txt",
            env=dict(os.environ, PYTHONPATH=str(ROOT), PYTHONDONTWRITEBYTECODE="1"))
        (directory / "receipt.json").write_text(encoded(dict(returncode=result.returncode, metadata=result.metadata)))
        print((directory / "stdout.txt").read_text())
        raise SystemExit(result.returncode)
