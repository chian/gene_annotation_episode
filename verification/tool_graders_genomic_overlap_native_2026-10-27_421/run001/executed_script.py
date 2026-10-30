"""Explicit local bedtools prerequisite and finite native-format examples.

Execute only under the caller's existing protected local_jobs boundary. This
does not implement a grader or the selected episode integration path.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import time


ROOT = Path.cwd()
PACKAGE = "bedtools_2.31.1+dfsg-2_amd64.deb"
PACKAGE_SHA256 = "2be06af20009e942be1b332b54220cee397ecfe51c24578bb586b584a3a30b5e"
PACKAGE_SIZE = 673776


def save(name, value):
    with (ROOT / name).open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def invoke(name, argv, *, expected_returncode=0):
    stdout, stderr = ROOT / (name + ".stdout"), ROOT / (name + ".stderr")
    started = time.monotonic()
    with stdout.open("xb") as out, stderr.open("xb") as err:
        result = subprocess.run(argv, cwd=ROOT, stdout=out, stderr=err, check=False)
    record = {"argv": argv, "returncode": result.returncode,
        "subprocess_wall_seconds": time.monotonic() - started,
        "stdout": stdout.name, "stderr": stderr.name}
    save(name + ".command.json", record)
    if result.returncode != expected_returncode:
        raise RuntimeError(name + "_unexpected_returncode:" + str(result.returncode))
    return stdout.read_bytes(), record


raw, _ = invoke("download", ["/usr/bin/apt-get", "download", "bedtools=2.31.1+dfsg-2"])
package = ROOT / PACKAGE
package_bytes = package.read_bytes()
assert len(package_bytes) == PACKAGE_SIZE
assert hashlib.sha256(package_bytes).hexdigest() == PACKAGE_SHA256
destination = ROOT / "installation"
assert not destination.exists()
invoke("extract", ["/usr/bin/dpkg-deb", "-x", str(package), str(destination)])
binary = destination / "usr/bin/bedtools"
assert binary.is_file()
version, _ = invoke("version", [str(binary), "--version"])
assert version.strip() == b"bedtools v2.31.1"
software = {"package": PACKAGE, "package_sha256": PACKAGE_SHA256,
    "package_size_bytes": PACKAGE_SIZE, "binary": str(binary),
    "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
    "observed_version": version.decode().strip(),
    "package_source": "Ubuntu noble/universe amd64 candidate from local signed APT metadata"}
save("SOFTWARE.json", software)

cases = [
    ("overlapping_a", "chr1\t0\t10\tA1\nchr1\t5\t15\tA2\n",
        "chr1\t7\t12\tB1\n",
        ["chr1\t0\t10\tA1\tchr1\t7\t12\tB1\t3",
         "chr1\t5\t15\tA2\tchr1\t7\t12\tB1\t5"], True),
    ("overlapping_both", "chr1\t0\t10\tA1\nchr1\t5\t15\tA2\n",
        "chr1\t7\t12\tB1\nchr1\t10\t20\tB2\n",
        ["chr1\t0\t10\tA1\tchr1\t7\t12\tB1\t3",
         "chr1\t5\t15\tA2\tchr1\t7\t12\tB1\t5",
         "chr1\t5\t15\tA2\tchr1\t10\t20\tB2\t5"], True),
    ("duplicate_occurrences", "chr1\t0\t10\tA1\nchr1\t0\t10\tA2\n",
        "chr1\t5\t15\tB1\nchr1\t5\t15\tB2\n",
        [f"chr1\t0\t10\t{a}\tchr1\t5\t15\t{b}\t5"
            for a in ("A1", "A2") for b in ("B1", "B2")], True),
    ("touching_endpoints", "chr1\t0\t10\tA1\n", "chr1\t10\t20\tB1\n", [], True),
    ("different_chromosomes", "chr1\t0\t10\tA1\n", "chr2\t0\t10\tB1\n", [], True),
    ("long_interval_one_bp", "chr1\t0\t2000000000\tA1\n",
        "chr1\t1999999999\t2000000000\tB1\n",
        ["chr1\t0\t2000000000\tA1\tchr1\t1999999999\t2000000000\tB1\t1"], True),
    ("long_interval_default_fraction", "chr1\t0\t2000000000\tA1\n",
        "chr1\t1999999999\t2000000000\tB1\n", [], False),
    ("signed_64bit_endpoint", "chr1\t0\t9223372036854775807\tA1\n",
        "chr1\t9223372036854775806\t9223372036854775807\tB1\n",
        ["chr1\t0\t9223372036854775807\tA1\tchr1\t9223372036854775806\t9223372036854775807\tB1\t1"], True),
]
observed = []
for name, a, b, expected, all_positive in cases:
    a_path, b_path = ROOT / (name + ".A.bed"), ROOT / (name + ".B.bed")
    a_path.write_bytes(a.encode())
    b_path.write_bytes(b.encode())
    argv = [str(binary), "intersect", "-a", str(a_path), "-b", str(b_path), "-wo", "-sorted"]
    if all_positive:
        argv += ["-f", "1e-30", "-F", "1e-30"]
    actual, command = invoke(name, argv)
    rows = actual.decode().splitlines()
    result = {"case": name, "all_positive_fraction_options": all_positive,
        "expected_lines": expected, "actual_lines": rows, "exact_match": rows == expected,
        "native_pair_count": len(rows),
        "native_pairwise_width_sum": sum(int(row.split("\t")[-1]) for row in rows),
        "stdout_sha256": hashlib.sha256(actual).hexdigest(),
        "command": command}
    save(name + ".CHECK.json", result)
    observed.append(result)
    assert result["exact_match"], name + "_native_format_or_value_mismatch"

save("NATIVE_CHECKS.json", {"scope": "Actual bedtools over explicitly synthetic interval inputs; no grader or episode-path verification",
    "software": software, "cases": observed})
print(json.dumps({"observed_version": software["observed_version"],
    "binary_sha256": software["binary_sha256"], "native_cases_passed": len(observed),
    "pair_counts": {row["case"]: row["native_pair_count"] for row in observed}}))
