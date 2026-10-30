"""Verify the observed default positive-overlap behavior; preserve run001."""
import hashlib
import json
from pathlib import Path
import subprocess
import time


ROOT = Path.cwd()
PROJECT = Path("/home/chia/repos/gene_annotation_episode")
ORIGINAL = PROJECT / "software/bedtools/ubuntu-2.31.1+dfsg-2"
BINARY_SHA = "b6c6e44b79180f0c9f64f916010c71bcd44baf81e5abe71b63f19aa9d4bc9fb6"
binary = ORIGINAL / "installation/usr/bin/bedtools"
assert hashlib.sha256(binary.read_bytes()).hexdigest() == BINARY_SHA

names = ("overlapping_a", "overlapping_both", "duplicate_occurrences", "touching_endpoints",
    "different_chromosomes", "long_interval_one_bp")
cases, original_pins = [], {}
for name in names:
    check_file = ORIGINAL / (name + ".CHECK.json")
    check = json.loads(check_file.read_bytes())
    assert check["exact_match"]
    files = [ORIGINAL / (name + ".A.bed"), ORIGINAL / (name + ".B.bed")]
    raw = [path.read_bytes() for path in files]
    for path in [check_file, *files]:
        original_pins[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    cases.append((name, *raw, check["expected_lines"]))
cases.append(("signed_64bit_endpoint", b"chr1\t0\t9223372036854775807\tA1\n",
    b"chr1\t9223372036854775806\t9223372036854775807\tB1\n",
    ["chr1\t0\t9223372036854775807\tA1\tchr1\t9223372036854775806\t9223372036854775807\tB1\t1"]))
results = []
for name, a, b, expected in cases:
    a_path, b_path = ROOT / (name + ".A.bed"), ROOT / (name + ".B.bed")
    a_path.write_bytes(a)
    b_path.write_bytes(b)
    argv = [str(binary), "intersect", "-a", str(a_path), "-b", str(b_path), "-wo", "-sorted"]
    started = time.monotonic()
    with (ROOT / (name + ".stdout")).open("xb") as stdout, (ROOT / (name + ".stderr")).open("xb") as stderr:
        result = subprocess.run(argv, cwd=ROOT, stdout=stdout, stderr=stderr, check=False)
    raw = (ROOT / (name + ".stdout")).read_bytes()
    lines = raw.decode().splitlines()
    row = {"case": name, "argv": argv, "returncode": result.returncode,
        "subprocess_wall_seconds": time.monotonic() - started,
        "expected_lines": expected, "actual_lines": lines, "exact_match": lines == expected,
        "native_pair_count": len(lines),
        "native_pairwise_width_sum": sum(int(line.split("\t")[-1]) for line in lines),
        "stdout_sha256": hashlib.sha256(raw).hexdigest()}
    (ROOT / (name + ".CHECK.json")).write_text(json.dumps(row, indent=2) + "\n")
    results.append(row)
    assert result.returncode == 0 and row["exact_match"], name + "_native_mismatch"
assert all(hashlib.sha256(Path(path).read_bytes()).hexdigest() == value
    for path, value in original_pins.items())
assert hashlib.sha256(binary.read_bytes()).hexdigest() == BINARY_SHA
report = {"scope": "Actual project-local bedtools v2.31.1 on synthetic interval examples, default -wo -sorted; no grader or episode integration",
    "binary_sha256": BINARY_SHA, "original_input_pins_unchanged": True,
    "original_input_pins": original_pins, "cases": results,
    "correction": "run001 expected default fraction options to omit a long-interval 1-bp overlap. That expectation was false; native defaults preserve it. run001 is unchanged."}
(ROOT / "NATIVE_CHECKS.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({"native_cases_passed": len(results),
    "pair_counts": {row["case"]: row["native_pair_count"] for row in results},
    "pairwise_width_sums": {row["case"]: row["native_pairwise_width_sum"] for row in results}}))
