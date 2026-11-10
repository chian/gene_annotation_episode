"""Small authentic native-format oracle, selected only inside the bounded runner.

This is not a production parser, calculator, resource adapter or episode test.
The sequence literals and every selected command are fixed in ORACLE_CASES_001.
Native bytes survive even when a format assertion fails.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

import pytest


PACKET_RELATIVE = Path("verification/tool_graders_masking_native_oracle_2026-10-28_612")


def _save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def _pin(path, root=None):
    return {
        "path": str(path.relative_to(root) if root else path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size_bytes": path.stat().st_size,
    }


def _blocks(content):
    """Test-only framing of native records; no association by header text."""
    records = []
    for line in content.decode("ascii").splitlines():
        if line.startswith(">"):
            records.append({"header": line[1:], "lines": []})
        elif line.strip():
            if not records:
                raise AssertionError("native row before first header")
            records[-1]["lines"].append(line)
    return records


def _interval_positions(block):
    intervals, positions = [], set()
    for line in block["lines"]:
        match = re.fullmatch(r"(\d+) - (\d+)", line)
        if not match:
            raise AssertionError("not native interval syntax: " + line)
        start, end = map(int, match.groups())
        if start > end:
            raise AssertionError("reversed native interval")
        intervals.append([start, end])
        positions.update(range(start, end + 1))
    return intervals, positions


def _observe_formats(oracle, plan, captured):
    """Independent native consistency assertions, never production quantities."""
    by_case = {row["case_id"]: row for row in captured}
    by_input = {row["input_id"]: row for row in plan["inputs"]}
    observations = {"pairs": [], "hard_mask": None, "errors": []}
    for program, input_id in (("dustmasker", "dna.fa"), ("segmasker", "protein.fa"),
                              ("windowmasker", "window_target.fa")):
        for parsed in (False, True):
            prefix = program + ("_parsed" if parsed else "")
            interval_case, soft_case = by_case[prefix + "_interval"], by_case[prefix + "_soft"]
            if any(row["status"] != "succeeded" for row in (interval_case, soft_case)):
                observations["errors"].append({"pair": prefix, "code": "native_pair_not_succeeded"})
                continue
            try:
                intervals = _blocks((oracle / interval_case["primary_output"]["path"]).read_bytes())
                fasta = _blocks((oracle / soft_case["primary_output"]["path"]).read_bytes())
                originals = by_input[input_id]["records"]
                pair = {"program": program, "parse_seqids": parsed, "input_id": input_id,
                        "interval_case": interval_case["case_id"], "soft_case": soft_case["case_id"],
                        "input_record_count": len(originals), "interval_record_count": len(intervals),
                        "soft_record_count": len(fasta), "records": []}
                for ordinal, (original, block, masked) in enumerate(zip(originals, intervals, fasta)):
                    native_intervals, mask_positions = _interval_positions(block)
                    sequence = "".join(masked["lines"])
                    lowercase = {i for i, char in enumerate(sequence) if char.islower()}
                    pair["records"].append({
                        "input_record_ordinal": ordinal, "original_header": original["header"],
                        "native_interval_header": block["header"], "native_soft_header": masked["header"],
                        "input_length": original["length"], "output_length": len(sequence),
                        "native_intervals_zero_based_inclusive": native_intervals,
                        "corresponding_intervals_half_open": [[s, e + 1] for s, e in native_intervals],
                        "native_interval_position_count": len(mask_positions),
                        "soft_lowercase_position_count": len(lowercase),
                        "positions_equal": mask_positions == lowercase,
                        "normalized_sequence_equal": original["sequence"].upper() == sequence.upper(),
                        "native_headers_equal_between_formats": block["header"] == masked["header"],
                        "positions_within_input": all(0 <= i < original["length"] for i in mask_positions),
                        "input_lowercase_positions": [i for i, c in enumerate(original["sequence"]) if c.islower()],
                    })
                observations["pairs"].append(pair)
            except (AssertionError, UnicodeError) as error:
                observations["errors"].append({"pair": prefix, "code": "format_assertion", "detail": str(error)})
    hard = by_case["dustmasker_hard"]
    if hard["status"] == "succeeded" and by_case["dustmasker_interval"]["status"] == "succeeded":
        try:
            originals = by_input["dna.fa"]["records"]
            fasta = _blocks((oracle / hard["primary_output"]["path"]).read_bytes())
            intervals = _blocks((oracle / by_case["dustmasker_interval"]["primary_output"]["path"]).read_bytes())
            rows = []
            for ordinal, (original, block, masked) in enumerate(zip(originals, intervals, fasta)):
                sequence = "".join(masked["lines"])
                _, mask_positions = _interval_positions(block)
                changed = {i for i, (a, b) in enumerate(zip(original["sequence"].upper(), sequence.upper())) if a != b}
                preexisting_n = {i for i, c in enumerate(original["sequence"].upper()) if c == "N"}
                rows.append({"input_record_ordinal": ordinal, "input_length": original["length"],
                             "output_length": len(sequence), "native_interval_position_count": len(mask_positions),
                             "case_insensitive_changed_position_count": len(changed),
                             "preexisting_N_positions": sorted(preexisting_n),
                             "masked_preexisting_N_positions": sorted(preexisting_n & mask_positions),
                             "changed_positions_equal_mask_without_preexisting_N": changed == mask_positions - preexisting_n,
                             "mask_total_cannot_be_recovered_from_changes_alone": bool(preexisting_n & mask_positions)})
            observations["hard_mask"] = {"case_id": "dustmasker_hard", "records": rows}
        except (AssertionError, UnicodeError) as error:
            observations["errors"].append({"pair": "dustmasker_hard", "code": "format_assertion", "detail": str(error)})
    return observations


@pytest.fixture(scope="module")
def native_oracle():
    selected_attempt = os.environ.get("HMMER529_ATTEMPT")
    if not selected_attempt:
        pytest.skip("native oracle requires the existing bounded 529 runner")
    attempt = Path(selected_attempt)
    snapshot = Path(__file__).resolve().parents[1]
    packet = snapshot / PACKET_RELATIVE
    plan_path = packet / "ORACLE_CASES_001.json"
    plan = json.loads(plan_path.read_text())
    oracle = attempt / "temporary/masking_native_oracle"
    oracle.mkdir(exist_ok=False)
    for name in ("inputs", "outputs", "commands"):
        (oracle / name).mkdir()
    shutil.copyfile(plan_path, oracle / "ORACLE_CASES_001.json")
    selected = [Path(p) for p in json.loads((attempt / "selected_native_executables.json").read_text())]
    binaries = {path.name: path for path in selected}
    assert set(binaries) == {row["program"] for row in plan["software"]}
    software = []
    for row in plan["software"]:
        path = binaries[row["program"]]
        assert path.is_relative_to(snapshot)
        identity = _pin(path)
        assert (identity["sha256"], identity["size_bytes"]) == (row["sha256"], row["size_bytes"])
        software.append({**row, "staged_executable": identity,
                         "version_case_id": row["program"] + "_version", "help_case_id": row["program"] + "_help"})
    inputs = []
    for row in plan["inputs"]:
        source = packet / row["path"]
        assert _pin(source)["sha256"] == row["sha256"]
        target = oracle / row["path"]
        shutil.copyfile(source, target)
        inputs.append({**row, "retained": _pin(target, oracle)})
    captures = []
    for case in plan["cases"]:
        def substitute(token):
            if token.startswith("{exe:"):
                return str(binaries[token[5:-1]])
            if token.startswith("{input:"):
                return str(oracle / "inputs" / token[7:-1])
            return token.replace("{oracle}", str(oracle))
        argv = [substitute(token) for token in case["argv"]]
        cid = case["case_id"]
        cli_path = oracle / "commands" / (cid + ".cli.json")
        _save(cli_path, {"argv": argv, "cwd": str(oracle), "shell": False})
        record = {**case, "argv": argv, "cli": _pin(cli_path, oracle), "returncode": None,
                  "executed": False, "status": "unavailable", "stdout": None, "stderr": None,
                  "primary_output": None, "native_output_complete": False, "launch_error": None,
                  "statistics_consumed": None}
        if case.get("statistics_from_case"):
            source = next(row for row in captures if row["case_id"] == case["statistics_from_case"])
            if source["status"] != "succeeded" or source["primary_output"] is None:
                record["unavailable_reason"] = "selected_statistics_generation_not_succeeded"
                captures.append(record)
                continue
            record["statistics_consumed"] = _pin(oracle / source["primary_output"]["path"], oracle)
        try:
            native = subprocess.run(argv, cwd=oracle, capture_output=True, check=False)
        except OSError as error:
            record["launch_error"] = {"type": type(error).__name__, "errno": error.errno}
        else:
            record.update(executed=True, returncode=native.returncode,
                          status="succeeded" if native.returncode == 0 else "failed",
                          native_output_complete=native.returncode == 0)
            for label, data in (("stdout", native.stdout), ("stderr", native.stderr)):
                path = oracle / "commands" / (cid + "." + label)
                path.write_bytes(data)
                record[label] = _pin(path, oracle)
            if case["output"] and (oracle / case["output"]).is_file():
                record["primary_output"] = _pin(oracle / case["output"], oracle)
        captures.append(record)
    observations = _observe_formats(oracle, plan, captures)
    _save(oracle / "FORMAT_OBSERVATIONS.json", observations)
    manifest = {"version": "blast_masking_native_oracle_v1", "attempt": str(attempt),
                "plan": _pin(oracle / "ORACLE_CASES_001.json", oracle), "policy": plan["policy"],
                "software": software, "inputs": inputs, "cases": captures,
                "format_observations": _pin(oracle / "FORMAT_OBSERVATIONS.json", oracle),
                "artifact_pins": [_pin(p, oracle) for p in sorted(oracle.rglob("*")) if p.is_file()],
                "limitations": plan["limitations"],
                "dependency_evidence": [str(attempt / name) for name in (
                    "dependency_pins_before.json", "native_library_resolution.json",
                    "native_library_pins_before.json", "native_library_pins_after.json",
                    "execution_audit.json", "receipt.json")]}
    _save(oracle / "ORACLE_MANIFEST.json", manifest)
    (oracle / "ORACLE_MANIFEST.sha256").write_text(_pin(oracle / "ORACLE_MANIFEST.json")["sha256"] + "  ORACLE_MANIFEST.json\n")
    for path in oracle.rglob("*"):
        if path.is_file():
            path.chmod(0o444)
    for path in sorted((p for p in oracle.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        path.chmod(0o555)
    oracle.chmod(0o555)
    return oracle, manifest, observations


def test_native_custody_and_software_inspection(native_oracle):
    oracle, manifest, _ = native_oracle
    for artifact in manifest["artifact_pins"]:
        assert _pin(oracle / artifact["path"], oracle) == artifact
    assert manifest["policy"] == {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296, 'swap_bytes': 0}
    cases = {row["case_id"]: row for row in manifest["cases"]}
    for program in ("dustmasker", "segmasker", "windowmasker"):
        for kind in ("help", "version"):
            case = cases[program + "_" + kind]
            assert case["returncode"] == 0, case
            assert (oracle / case["stdout"]["path"]).read_bytes().strip()


@pytest.mark.parametrize("program", ["dustmasker", "segmasker", "windowmasker"])
def test_native_interval_soft_concordance_and_no_mask_records(native_oracle, program):
    _, _, observations = native_oracle
    assert not observations["errors"], observations["errors"]
    pairs = [row for row in observations["pairs"] if row["program"] == program]
    assert len(pairs) == 2
    for pair in pairs:
        assert pair["input_record_count"] == pair["interval_record_count"] == pair["soft_record_count"] == 3
        for record in pair["records"]:
            assert record["positions_equal"] and record["normalized_sequence_equal"]
            assert record["native_headers_equal_between_formats"] and record["positions_within_input"]
            assert record["input_length"] == record["output_length"]
        assert pair["records"][0]["native_interval_position_count"] > 0
        assert pair["records"][1]["native_interval_position_count"] == 0
        assert pair["records"][1]["input_lowercase_positions"]


def test_dust_hard_mask_preexisting_n_is_not_all_changed_positions(native_oracle):
    _, _, observations = native_oracle
    records = observations["hard_mask"]["records"]
    assert len(records) == 3
    assert all(row["changed_positions_equal_mask_without_preexisting_N"] for row in records)
    ambiguous = records[2]
    assert ambiguous["mask_total_cannot_be_recovered_from_changes_alone"]
    assert ambiguous["masked_preexisting_N_positions"]
    assert ambiguous["case_insensitive_changed_position_count"] < ambiguous["native_interval_position_count"]


def test_dust_acclist_native_shape_omits_unmasked_record(native_oracle):
    oracle, manifest, _ = native_oracle
    case = next(row for row in manifest["cases"] if row["case_id"] == "dustmasker_acclist")
    assert case["returncode"] == 0, case
    lines = (oracle / case["primary_output"]["path"]).read_text().splitlines()
    assert lines
    assert all(re.fullmatch(r">[^\t]+\t\d+\t\d+", line) for line in lines)
    assert len(lines) == 2


def test_window_counts_separate_reference_and_exact_consumed_artifact(native_oracle):
    oracle, manifest, _ = native_oracle
    cases = {row["case_id"]: row for row in manifest["cases"]}
    counts = cases["windowmasker_counts"]
    assert counts["returncode"] == 0, counts
    raw = (oracle / counts["primary_output"]["path"]).read_text()
    lines = [line for line in raw.splitlines() if line.strip() and not line.startswith("#")]
    assert lines[0] == "3"
    unit_rows = [line for line in lines[1:] if not line.startswith(">")]
    assert unit_rows and all(re.fullmatch(r"[0-9a-f]+ \d+", line) for line in unit_rows)
    thresholds = dict(line[1:].split() for line in lines if line.startswith(">"))
    assert set(thresholds) == {"t_low", "t_extend", "t_threshold", "t_high"}
    assert "##pct:" in raw
    for key in ("windowmasker_interval", "windowmasker_soft", "windowmasker_parsed_interval", "windowmasker_parsed_soft"):
        mask = cases[key]
        assert mask["returncode"] == 0
        assert mask["input_id"] != counts["input_id"]
        assert mask["statistics_consumed"] == counts["primary_output"]


def test_empty_and_failed_inputs_never_claim_zero_mask_population(native_oracle):
    oracle, manifest, _ = native_oracle
    cases = {row["case_id"]: row for row in manifest["cases"]}
    empty = cases["dustmasker_empty"]
    assert empty["mode"] == "negative_input"
    assert empty["primary_output"] is None or empty["primary_output"]["size_bytes"] == 0
    for cid in ("dustmasker_malformed", "windowmasker_missing_statistics"):
        assert cases[cid]["returncode"] != 0
        assert cases[cid]["status"] == "failed"
        assert not cases[cid]["native_output_complete"]
    assert not (oracle / "deliberately_absent_statistics.ascii").exists()
