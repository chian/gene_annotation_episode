"""One selected native capture for convert2blastmask, inside bounded529 only.

These are explicit synthetic inputs, not external sequence acquisitions. This
characterization does not implement a parser, calculate masking components, or
establish episode integration. No help/version/search commands run here.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

import pytest


INPUTS = {
    "nucleotide_four": {
        "molecule": "nucleotide",
        "content": (
            ">lcl|mask_a synthetic occurrence 0\nAAaaNNttRRYy\n"
            ">lcl|upper_a synthetic occurrence 1\nACGTNNRY\n"
            ">ref|NM_999999999.7| synthetic occurrence 2\nnnACgtNN\n"
            ">gnl|fixture636|mask_general synthetic occurrence 3\nACgtNNrY\n"
        ),
    },
    "duplicate_headers": {
        "molecule": "nucleotide",
        "content": ">duplicate\nAAaaGG\n>duplicate\nttCCaa\n",
    },
    "protein_mixed": {
        "molecule": "protein",
        "content": ">lcl|protein_a synthetic protein\nMKWVtfISLLflFSSaysR\n",
    },
    "single_interval": {
        "molecule": "nucleotide",
        "content": ">lcl|interval_a\nAAaaNNtt\n",
    },
    "uppercase_only": {
        "molecule": "nucleotide",
        "content": ">lcl|uppercase_only\nACGTNNRYMKSWBDHV\n",
    },
    "malformed_missing_header": {
        "molecule": "nucleotide",
        "content": "not a FASTA header\nAAaa\n",
    },
}

# Exactly one native invocation per selected case. The algorithm/options are
# declared upstream provenance; they do not assert execution of a mask detector.
CASES = (
    ("nucleotide_xml_parsed", "nucleotide_four", "maskinfo_xml", True, "dust"),
    ("nucleotide_text_parsed", "nucleotide_four", "maskinfo_asn1_text", True, "dust"),
    ("nucleotide_binary_parsed", "nucleotide_four", "maskinfo_asn1_bin", True, "dust"),
    ("nucleotide_xml_unparsed", "nucleotide_four", "maskinfo_xml", False, "dust"),
    ("duplicate_headers_xml", "duplicate_headers", "maskinfo_xml", True, "other"),
    ("protein_xml", "protein_mixed", "maskinfo_xml", True, "seg"),
    ("single_interval", "single_interval", "interval", True, "other"),
    ("uppercase_only_xml", "uppercase_only", "maskinfo_xml", True, "other"),
    ("malformed_xml", "malformed_missing_header", "maskinfo_xml", True, "other"),
)


def _pin(path):
    content = path.read_bytes()
    return {"path": str(path), "sha256": hashlib.sha256(content).hexdigest(),
            "size_bytes": len(content)}


def _save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def _xml_tree(element):
    """Lossless element content/attributes for examination, not association."""
    return {"tag": element.tag, "attributes": dict(element.attrib),
            "text": element.text, "tail": element.tail,
            "children": [_xml_tree(child) for child in element]}


def test_selected_convert2blastmask_native_formats_and_associations():
    location = os.environ.get("HMMER529_ATTEMPT")
    if not location:
        pytest.skip("requires the selected existing 529 bounded runner")
    attempt = Path(location)
    snapshot = Path(__file__).resolve().parents[1]
    selected = json.loads((attempt / "selected_native_executables.json").read_text())
    assert len(selected) == 1
    executable = Path(selected[0])
    assert executable.name == "convert2blastmask"
    assert executable.is_relative_to(snapshot)
    destination = attempt / "temporary/convert2blastmask_formats_636"
    destination.mkdir(exist_ok=False)
    input_directory = destination / "inputs"
    input_directory.mkdir()
    inputs = {}
    for name, definition in INPUTS.items():
        path = input_directory / (name + ".fasta")
        path.write_bytes(definition["content"].encode("ascii"))
        inputs[name] = {**definition, "artifact": _pin(path),
                        "origin": "explicit_synthetic_supplied_test_input"}

    reference = snapshot / "verification/tool_graders_blast_utility_boundaries_2026-10-28_620"
    source_files = [
        Path(__file__),
        reference / "official_source/convert2blastmask.cpp",
        reference / "retained_native_help/convert2blastmask.help.stdout",
        reference / "retained_native_help/convert2blastmask.version.stdout",
    ]
    record = {
        "record_type": "convert2blastmask_native_format_characterization_v1",
        "policy": {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296, 'swap_bytes': 0},
        "native_executable_before": _pin(executable),
        "source_identities": [_pin(path) for path in source_files],
        "source_binary_relationship": "retained_official_source_not_proven_build_source",
        "inputs": inputs,
        "selected_cases": [list(row) for row in CASES],
        "cases": [],
        "limit": "Native format/association characterization only; no production parser, scoring, database or episode-return verification",
    }
    _save(destination / "CAPTURE_001.json", record)
    for case_id, input_name, outfmt, parse_seqids, algorithm in CASES:
        case_directory = destination / case_id
        case_directory.mkdir()
        temporary = case_directory / "temporary"
        cache = case_directory / "cache"
        temporary.mkdir()
        cache.mkdir()
        environment = {
            "PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C",
            "BLAST_USAGE_REPORT": "false", "NCBI_DONT_USE_NCBIRC": "1",
            "TMPDIR": str(temporary), "TMP": str(temporary), "TEMP": str(temporary),
            "XDG_CACHE_HOME": str(cache),
        }
        if "LD_LIBRARY_PATH" in os.environ:
            environment["LD_LIBRARY_PATH"] = os.environ["LD_LIBRARY_PATH"]
        native_output = case_directory / ("native_output." + outfmt)
        stdout = case_directory / "stdout.bin"
        stderr = case_directory / "stderr.bin"
        options = "supplied lowercase; no detector run; fixture 636"
        argv = [str(executable), "-in", inputs[input_name]["artifact"]["path"],
                "-out", str(native_output), "-outfmt", outfmt,
                "-masking_algorithm", algorithm, "-masking_options", options]
        if parse_seqids:
            argv.append("-parse_seqids")
        case = {
            "case_id": case_id, "input_name": input_name, "native_format": outfmt,
            "declared_molecule": inputs[input_name]["molecule"],
            "declared_upstream_algorithm": algorithm, "declared_upstream_options": options,
            "parse_seqids": parse_seqids, "argv": argv, "cwd": str(case_directory),
            "shell": False, "environment": environment, "executed": False,
            "returncode": None, "launch_error": None,
        }
        # Retain selected command/environment before attempting the invocation.
        _save(case_directory / "SELECTED_COMMAND_001.json", case)
        with stdout.open("wb") as output, stderr.open("wb") as errors:
            try:
                result = subprocess.run(argv, cwd=case_directory, env=environment,
                                        stdout=output, stderr=errors, check=False)
            except OSError as error:
                case["launch_error"] = {"type": type(error).__name__, "errno": error.errno}
            else:
                case.update(executed=True, returncode=result.returncode)
        case.update(stdout=_pin(stdout), stderr=_pin(stderr),
                    stdout_text=stdout.read_bytes().decode("utf-8", "replace"),
                    stderr_text=stderr.read_bytes().decode("utf-8", "replace"),
                    native_output_present=native_output.is_file())
        if native_output.is_file():
            data = native_output.read_bytes()
            case["native_output"] = _pin(native_output)
            if outfmt == "maskinfo_asn1_bin":
                case["native_output_hex"] = data.hex()
            else:
                case["native_output_text"] = data.decode("utf-8", "strict")
            if outfmt == "maskinfo_xml":
                try:
                    case["xml_element_tree"] = _xml_tree(ET.fromstring(data))
                except ET.ParseError as error:
                    case["xml_parse_error"] = str(error)
        _save(case_directory / "OUTCOME_001.json", case)
        record["cases"].append(case)
        _save(destination / "CAPTURE_001.json", record)
    record["native_executable_after"] = _pin(executable)
    _save(destination / "CAPTURE_001.json", record)

    # Check capture completion and the selected failure, without predicting any
    # scientific numerator or implementing a second masking calculation.
    assert len(record["cases"]) == len(CASES) == 9
    assert all(case["executed"] for case in record["cases"]), record["cases"]
    assert all(case["returncode"] == 0 for case in record["cases"][:-1]), record["cases"]
    assert record["cases"][-1]["returncode"] != 0, record["cases"][-1]
    assert record["native_executable_before"] == record["native_executable_after"]
