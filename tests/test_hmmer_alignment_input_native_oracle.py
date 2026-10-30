"""Original-source Easel input conformance; root's bounded job is required.

Do not run/collect this on the host. Root stages the selected compiler and Easel
sources/archive into its existing 529 lifecycle with 20 GiB RAM, 4 GiB scratch,
zero swap and no wall-time cap. There are no implicit executable lookups, skips,
downloads, producer reruns, alternative scientific calculators or job launches.
Native expectation values are obtained from original C at execution time.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess

import pytest

from gene_annotation_episode.hmmer_alignment_input_alphabet import (
    classify_easel_alphabet_counts,
    infer_hmmer_alignment_alphabet,
)
from gene_annotation_episode.hmmer_alignment_input_fasta import decode_native_fasta_alignment
from gene_annotation_episode.hmmalign_inputs import _normalize, stockholm_digital_checksum

_REPO = Path(__file__).resolve().parents[1]
_PACKET = _REPO / "verification/tool_graders_hmmer_input_native_oracle_2026-10-28_539"
_CASES = json.loads((_PACKET / "CASES.json").read_text())
_NATIVE_KEYS = {
    "kind", "version", "easel_version", "mode", "format", "requested_alphabet",
    "status", "open_status", "read_status", "selected_alphabet", "classifier_calls",
    "error_hex", "read_line_number", "nseq", "alen", "rows", "annotations",
    "metadata", "unparsed_gc", "unparsed_gr", "checksum_status", "native_checksum_uint32",
}


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def _required_path(variable, *, directory=False):
    supplied = os.environ.get(variable)
    assert supplied, f"{variable} must name an explicitly staged verification input"
    assert Path(supplied).is_absolute(), f"{variable} must be an absolute path"
    path = Path(supplied).resolve(strict=True)
    assert path.is_dir() if directory else path.is_file(), (variable, str(path))
    return path


def _check_pin(path, pin):
    assert path.is_file(), f"missing staged input: {path}"
    assert path.stat().st_size == pin["size_bytes"], str(path)
    assert _sha256(path) == pin["sha256"], f"changed staged input: {path}"


def _run_recorded(argv, directory, label, *, env):
    argv = [str(value) for value in argv]
    _write_json(directory / f"{label}.argv.json", argv)
    completed = subprocess.run(argv, cwd=directory, env=env, capture_output=True, check=False)
    (directory / f"{label}.stdout").write_bytes(completed.stdout)
    (directory / f"{label}.stderr").write_bytes(completed.stderr)
    _write_json(directory / f"{label}.exit.json", {"returncode": completed.returncode})
    assert completed.returncode == 0, (label, completed.returncode, str(directory))
    return completed.stdout


class _NativeObserver:
    def __init__(self, root, env, executable):
        self.root, self.env, self.executable = root, env, executable

    def case(self, group, case):
        directory = self.root / (group + "_" + case["id"])
        directory.mkdir()
        _write_json(directory / "case.json", case)
        return directory

    def call(self, arguments, directory):
        raw = _run_recorded([self.executable, *arguments], directory, "native", env=self.env)
        result = json.loads(raw.decode("ascii"))
        assert set(result) == _NATIVE_KEYS
        assert result["kind"] == "diagnostic_easel_alignment_input"
        assert result["version"] == 1 and result["easel_version"] == "0.49"
        return result


@pytest.fixture(scope="module")
def native_observer(tmp_path_factory):
    easel = _required_path("HMMER_NATIVE_ORACLE_EASEL_DIR", directory=True)
    compiler = _required_path("HMMER_NATIVE_ORACLE_CC")
    compiler_pin = {"sha256": _sha256(compiler), "size_bytes": compiler.stat().st_size}
    pins = json.loads((_PACKET / "SOURCE_PINS.json").read_text())
    for name, pin in pins["easel_files"].items():
        source = (easel / name).resolve(strict=True)
        assert source.is_relative_to(easel), name
        _check_pin(source, pin)
    for relative, pin in pins["diagnostic_sources"].items():
        _check_pin(_REPO / relative, pin)
    for relative, pin in pins["fixture_files"].items():
        _check_pin(_REPO / relative, pin)

    root = tmp_path_factory.mktemp("hmmer_alignment_input_native_oracle")
    temporary = root / "compiler_tmp"
    temporary.mkdir()
    env = os.environ.copy()
    env.update(TMPDIR=str(temporary), TMP=str(temporary), TEMP=str(temporary), LC_ALL="C", LANG="C")
    _write_json(root / "verified_source_pins.json", pins)
    _write_json(root / "selected_paths.json", {
        "easel": str(easel), "compiler": str(compiler), "compiler_sha256": compiler_pin["sha256"],
        "evidence_kind": "original_source_diagnostic_not_hmmer_cli_or_native_emission",
        "source_rewrites": [], "production_compiler_dependency": False,
    })
    _run_recorded([compiler, "--version"], root, "compiler_version", env=env)
    flags = ["-std=c99", "-O2", "-fno-fast-math", "-ffp-contract=off", "-I", str(easel)]
    objects = []
    for filename in pins["compile_native_sources"]:
        name = Path(filename).stem
        destination = root / f"{name}.o"
        rename = (["-Desl_abc_GuessAlphabet=oracle_original_GuessAlphabet"]
                  if filename == "esl_alphabet.c" else [])
        _run_recorded([
            compiler, *flags, *rename, "-MMD", "-MF", root / f"{name}.d",
            "-c", easel / filename, "-o", destination,
        ], root, f"compile_{name}", env=env)
        objects.append(destination)
    observer = root / "input_observer.o"
    _run_recorded([
        compiler, *flags, "-MMD", "-MF", root / "input_observer.d",
        "-c", _PACKET / "input_observer.c", "-o", observer,
    ], root, "compile_input_observer", env=env)
    executable = root / "input_observer"
    _run_recorded([
        compiler, observer, *objects, easel / "libeasel.a", "-lm", "-lpthread",
        "-o", executable,
    ], root, "link_input_observer", env=env)
    _write_json(root / "built_binary.json", {
        "path": str(executable), "sha256": _sha256(executable),
        "size_bytes": executable.stat().st_size,
    })
    yield _NativeObserver(root, env, executable)
    # Verify source/compiler bytes again; original sources were never patched.
    for name, pin in pins["easel_files"].items():
        _check_pin(easel / name, pin)
    for relative, pin in pins["diagnostic_sources"].items():
        _check_pin(_REPO / relative, pin)
    for relative, pin in pins["fixture_files"].items():
        _check_pin(_REPO / relative, pin)
    _check_pin(compiler, compiler_pin)
    _write_json(root / "source_reset_record.json", {
        "original_sources_changed": False, "source_reset_required": False,
        "reason": "separate objects and compiler-only symbol rename; originals stayed byte-identical",
    })


def _fixture_bytes(case, directory):
    original = (_REPO / case["path"]).resolve(strict=True)
    assert original.is_relative_to(_REPO), str(original)
    _check_pin(original, case)
    content = original.read_bytes()
    staged = directory / "input.bytes"
    staged.write_bytes(content)
    _write_json(directory / "input_identity.json", {
        "original": str(original), "actual_native_input": str(staged),
        "sha256": _sha256(staged), "size_bytes": len(content), "basis": case["basis"],
    })
    return content, staged


def _state(status):
    assert status in (0, 26), status
    return "determined" if status == 0 else "undetermined"


def _compare_probe(probe, native, *, offsets):
    assert probe["state"] == _state(native["status"])
    assert probe["alphabet"] == native["selected_alphabet"]
    calls = native["classifier_calls"]
    assert len(probe["checkpoints"]) == len(calls)
    for checkpoint, actual in zip(probe["checkpoints"], calls):
        assert checkpoint["counts_az"] == actual["counts_az"]
        assert checkpoint["state"] == _state(actual["status"])
        assert checkpoint["alphabet"] == actual["alphabet"]
        if offsets:
            assert type(actual["byte_offset"]) is int
            assert checkpoint["byte_end"] == actual["byte_offset"]
        else:
            assert actual["byte_offset"] is None
    assert probe["counts_az"] == (calls[-1]["counts_az"] if calls else [0] * 26)
    assert probe["counted_letters"] == sum(probe["counts_az"])
    if calls and offsets and probe["stopped_at"] == "checkpoint":
        assert probe["scan_end_byte"] == calls[-1]["byte_offset"]


@pytest.mark.parametrize("case", _CASES["classifier"], ids=lambda case: case["id"])
def test_classifier_exact_native_status_and_precedence(native_observer, case):
    directory = native_observer.case("classifier", case)
    native = native_observer.call(["classifier", *map(str, case["counts_az"])], directory)
    result = classify_easel_alphabet_counts(case["counts_az"])
    _write_json(directory / "python_result.json", result)
    assert result["status"] == _state(native["status"])
    assert result["alphabet"] == native["selected_alphabet"]
    # A branch name is source-derived, not an invented native instrumentation value.
    assert result["rule"] == case["source_expected_rule"]
    assert native["classifier_calls"] == [{
        "counts_az": case["counts_az"], "status": native["status"],
        "alphabet": native["selected_alphabet"], "byte_offset": None,
    }]
    assert native["open_status"] is native["read_status"] is None
    _write_json(directory / "comparison.json", {"status": "passed", "comparison": "actual_C_classifier"})


@pytest.mark.parametrize("case", _CASES["guess"], ids=lambda case: case["id"])
def test_per_format_guess_histograms_and_checkpoints(native_observer, case):
    directory = native_observer.case("guess", case)
    content, input_path = _fixture_bytes(case, directory)
    native = native_observer.call(["guess", case["format"], "auto", input_path], directory)
    result = infer_hmmer_alignment_alphabet(content, declared_format=case["format"])
    _write_json(directory / "python_result.json", result)
    assert native["open_status"] == 0 and native["read_status"] is None
    assert native["rows"] == [] and native["nseq"] is None
    if case["source_expected_call_count"] is not None:
        assert len(native["classifier_calls"]) == case["source_expected_call_count"]
    _compare_probe(result, native, offsets=True)
    if result["stopped_at"] == "eof":
        assert result["scan_end_byte"] == len(content)
    _write_json(directory / "comparison.json", {"status": "passed", "comparison": "actual_C_scanner_calls"})


def _canonical(rows, alphabet):
    # Reuse the established normalization helper. The two gap aliases are the
    # same lexical-to-digital step used by stockholm_digital_checksum itself.
    return [_normalize(row["aligned_sequence"], alphabet.lower()).replace(".", "-").replace("_", "-")
            for row in rows]


def _hex(value):
    return None if value is None else value.encode("utf-8", "surrogateescape").hex()


@pytest.mark.parametrize("case", _CASES["read"], ids=lambda case: case["id"])
def test_afa_a2m_native_digital_rows_rf_width_and_failures(native_observer, case):
    directory = native_observer.case("read", case)
    content, input_path = _fixture_bytes(case, directory)
    native = native_observer.call(["read", case["format"], case["alphabet"], input_path], directory)
    assert native["status"] == case["source_expected_status"]
    if case["alphabet"] == "auto":
        probe = infer_hmmer_alignment_alphabet(content, declared_format=case["format"])
        _write_json(directory / "python_probe.json", probe)
        _compare_probe(probe, {**native, "status": native["open_status"]}, offsets=False)
    else:
        assert native["classifier_calls"] == []  # explicit native alphabet bypasses guessing
        assert native["selected_alphabet"] == case["alphabet"]
    if native["open_status"] == 26:
        assert native["read_status"] is None and native["rows"] == []
        assert native["selected_alphabet"] is None
        _write_json(directory / "comparison.json", {"status": "passed", "comparison": "native_open_refusal_26"})
        return
    assert native["open_status"] == 0
    decoded = decode_native_fasta_alignment(
        content, declared_format=case["format"], alphabet=native["selected_alphabet"],
    )
    _write_json(directory / "python_result.json", decoded)
    if native["read_status"] == 3:
        assert decoded["records"] == [] and decoded["end_state"] == "eof"
        assert native["rows"] == [] and native["nseq"] is None
    elif native["read_status"] == 7:
        assert decoded["end_state"] == "parse_error"
        assert decoded["records"] and decoded["records"][-1]["native_status_equivalent"] == 7
        assert all(record["reader_state"] != "complete" for record in decoded["records"])
        assert native["rows"] == [] and native["nseq"] is None  # native destroys partial MSA
    else:
        assert native["read_status"] == 0
        assert decoded["end_state"] == "eof" and len(decoded["records"]) == 1
        record = decoded["records"][0]
        assert record["reader_state"] == "complete" and record["native_status_equivalent"] == 0
        assert all(row["geometry_valid"] and row["symbols_valid"] for row in record["rows"])
        assert record["column_count"] == native["alen"]
        assert len(record["rows"]) == native["nseq"]
        assert [row["row_ordinal"] for row in record["rows"]] == [row["ordinal"] for row in native["rows"]]
        assert [row["name_bytes_hex"] for row in record["rows"]] == [row["name_hex"] for row in native["rows"]]
        assert [_hex(row["description"]) for row in record["rows"]] == [row["description_hex"] for row in native["rows"]]
        assert _canonical(record["rows"], native["selected_alphabet"]) == [row["digital"] for row in native["rows"]]
        reference = record["column_annotations"].get("RF")
        assert _hex(reference["text"] if reference else None) == native["annotations"]["RF_hex"]
        assert all(native["annotations"][key] is None for key in ("MM_hex", "SS_cons_hex", "SA_cons_hex", "PP_cons_hex"))
        assert native["checksum_status"] == 0
        checksum = stockholm_digital_checksum([row["aligned_sequence"] for row in record["rows"]],
                                               alphabet=native["selected_alphabet"])
        assert checksum == native["native_checksum_uint32"]
        _write_json(directory / "shared_checksum.json", {"shared_checksum": checksum})
    _write_json(directory / "comparison.json", {
        "status": "passed", "comparison": "actual_C_read_status_rows_names_RF_and_shared_checksum",
    })
