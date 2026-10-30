"""Explicit tiny native characterization under the existing bounded 529 runner.

This is retained fixture evidence, not an application execution adapter. Every
native invocation is selected in CASE_MATRIX_001.json before this test starts.
No search, acquisition, implicit retry, or production helper is performed.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest


PACKET = Path("verification/tool_graders_blast_preparation_native_2026-10-28_644")
HISTORY = Path("verification/tool_graders_hmmer_map_verification_2026-10-28_529") / (
    "check096_blast_utility_full_workflow/temporary/pytest/utility-workflow6340"
)
PSSM = Path("verification/tool_graders_blast_pssm_2026-10-26_306/sources/pssm_freq_ratios.asn")
PSSM_MANIFEST = PSSM.parent / "MANIFEST.json"


def _pin(path: Path) -> dict:
    raw = path.read_bytes()
    return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(),
            "size_bytes": len(raw)}


def _save(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def _inventory(directory: Path) -> list[dict]:
    rows = []
    for path in sorted(directory.rglob("*")):
        assert not path.is_symlink(), str(path)
        if path.is_file():
            rows.append({**_pin(path), "relative_path": str(path.relative_to(directory))})
    return rows


def _same_bytes(actual: dict, expected: dict) -> bool:
    return all(actual[key] == expected[key] for key in ("sha256", "size_bytes"))


def test_selected_tiny_native_preparation_cases_once():
    location = os.environ.get("HMMER529_ATTEMPT")
    if not location:
        pytest.skip("requires the existing bounded 529 runner")
    attempt = Path(location)
    snapshot = Path(__file__).resolve().parents[1]
    packet = snapshot / PACKET
    matrix = json.loads((packet / "CASE_MATRIX_001.json").read_text())
    selected = json.loads((attempt / "selected_native_executables.json").read_text())
    binaries = {Path(value).name: Path(value) for value in selected}
    assert set(binaries) == {"blastdb_aliastool", "makembindex", "makeprofiledb", "blastdbcmd"}
    assert len(binaries) == len(selected)
    assert all(path.is_relative_to(snapshot) for path in binaries.values())

    destination = attempt / "temporary/blast_preparation_native644"
    destination.mkdir(exist_ok=False)
    (destination / "logs").mkdir()
    (destination / "inputs").mkdir()
    (destination / "cases").mkdir()
    (destination / "native_tmp").mkdir()
    (destination / "native_cache").mkdir()

    historical = snapshot / HISTORY
    original_case_path = historical / "CASE.json"
    original_case = json.loads(original_case_path.read_text())
    database = original_case["jobs"][1]["databases"][0]
    manifest = database["manifest"]
    assert manifest["inventory_complete"] is True
    assert len(manifest["files"]) == 10
    assert len(manifest["native_paths"]) == 1
    original_prefix = Path(manifest["native_paths"][0])
    assert original_prefix.name == "tiny"
    original_store = historical / "state/artifacts"

    def stored(identity):
        return original_store / identity["sha256"][:2] / identity["sha256"]

    manifest_file = database["manifest_file"]
    assert _same_bytes(_pin(stored(manifest_file)), manifest_file)
    assert json.loads(stored(manifest_file).read_text()) == manifest
    shutil.copyfile(stored(manifest_file), destination / "inputs/original096-manifest.json")
    source_input = original_case["jobs"][0]["inputs"][0]
    assert _same_bytes(_pin(stored(source_input)), source_input)
    assert source_input["size_bytes"] == 60
    shutil.copyfile(stored(source_input), destination / "inputs/original096.fa")

    pssm_sources = json.loads((snapshot / PSSM_MANIFEST).read_text())
    pssm_identity = next(row for row in pssm_sources["sources"] if row["file"] == str(PSSM))
    assert _pin(snapshot / PSSM)["sha256"] == pssm_identity["sha256"]
    assert _pin(snapshot / PSSM)["size_bytes"] == pssm_identity["bytes"]
    shutil.copyfile(snapshot / PSSM, destination / "inputs/pssm_freq_ratios.asn")
    shutil.copyfile(snapshot / PSSM_MANIFEST, destination / "inputs/pssm-source-manifest.json")

    protected_inputs = {original_case_path, snapshot / PSSM, snapshot / PSSM_MANIFEST,
                        stored(manifest_file), stored(source_input)}
    for row in manifest["files"]:
        assert Path(row["path"]).parent == original_prefix.parent
        assert Path(row["path"]).name.startswith(original_prefix.name + ".")
        assert _same_bytes(_pin(stored(row)), row)
        protected_inputs.add(stored(row))
    protected_before = {str(path): _pin(path) for path in sorted(protected_inputs)}
    _save(destination / "ORIGINAL_INPUTS_BEFORE_001.json", protected_before)
    _save(destination / "ORIGINAL_RELATIONSHIPS_001.json", {
        "case": _pin(original_case_path),
        "manifest": manifest,
        "manifest_file": manifest_file,
        "sequence_input": source_input,
        "pssm": pssm_identity,
        "pssm_origin": "genuine retained NCBI upstream test input; not a locally run search",
        "prior_native_returncodes": original_case["native_returncodes"],
        "database_integrity": "unverified; original blastdbcheck failed with metadata exception",
        "aggregation_meaning": "two named copies of the same original database; not independent biology",
    })

    work = {}
    bindings = {}
    staged_originals = {}
    for spec in matrix["cases"]:
        workspace = spec["workspace"]
        if workspace in work:
            continue
        cwd = destination / "cases" / workspace
        cwd.mkdir()
        work[workspace] = cwd
        bindings[workspace] = []
        if spec.get("database_directories"):
            for db_dir in spec["database_directories"]:
                target = cwd / db_dir
                target.mkdir()
                staged_prefix = target / original_prefix.name
                file_bindings = []
                for ordinal, row in enumerate(manifest["files"]):
                    new_path = target / Path(row["path"]).name
                    shutil.copyfile(stored(row), new_path)
                    current = _pin(new_path)
                    assert _same_bytes(current, row)
                    staged_originals[str(new_path)] = current
                    file_bindings.append({"ordinal": ordinal, "original": row,
                        "retained_source": _pin(stored(row)), "staged": current})
                bindings[workspace].append({"role": "database_dependency",
                    "database_key": database["database_key"],
                    "original_prefix": str(original_prefix),
                    "staged_prefix": str(staged_prefix), "files": file_bindings,
                    "same_original_database": True})
        for filename, content in spec.get("text_inputs", {}).items():
            path = cwd / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content.encode("utf-8"))
            bindings[workspace].append({"role": "selected_engineering_text_input",
                "native_operand": filename, "content_utf8": content, "staged": _pin(path)})
            staged_originals[str(path)] = _pin(path)
        if spec.get("reuse_original_fasta"):
            path = cwd / "original096.fa"
            shutil.copyfile(stored(source_input), path)
            staged_originals[str(path)] = _pin(path)
            bindings[workspace].append({"role": "sequence_input", "original": source_input,
                "retained_source": _pin(stored(source_input)), "staged": _pin(path)})
        if spec.get("reuse_original_pssm"):
            path = cwd / "profiles/pssm_freq_ratios.asn"
            path.parent.mkdir(parents=True)
            shutil.copyfile(snapshot / PSSM, path)
            staged_originals[str(path)] = _pin(path)
            bindings[workspace].append({"role": "profile_input", "list_ordinal": 0,
                "original_list_token": "profiles/pssm_freq_ratios.asn",
                "original": pssm_identity, "staged": _pin(path)})
    _save(destination / "STAGED_INPUTS_BEFORE_001.json", staged_originals)
    _save(destination / "OPERAND_BINDINGS_001.json", bindings)

    environment = dict(os.environ)
    overrides = {"BLAST_USAGE_REPORT": "false", "NCBI_DONT_USE_NCBIRC": "1",
        "TMPDIR": str(destination / "native_tmp"), "TMP": str(destination / "native_tmp"),
        "TEMP": str(destination / "native_tmp"), "XDG_CACHE_HOME": str(destination / "native_cache")}
    environment.update(overrides)
    captures = []
    report = {"record_type": "blast_preparation_explicit_native_capture_v1",
        "case_matrix": _pin(packet / "CASE_MATRIX_001.json"),
        "policy": {"memory_bytes": 21474836480, "scratch_bytes": 4294967296,
                   "swap_bytes": 0, "wall_seconds": None},
        "environment_overrides": overrides,
        "scope": "native fixture evidence only; episode integration and search compatibility unverified",
        "cases": captures}
    for spec in matrix["cases"]:
        cwd = work[spec["workspace"]]
        executable = binaries[spec["program"]]
        argv = [str(executable), *spec["arguments"]]
        stdout = destination / "logs" / (spec["id"] + ".stdout")
        stderr = destination / "logs" / (spec["id"] + ".stderr")
        before = _inventory(cwd)
        case = {"id": spec["id"], "purpose": spec["purpose"],
                "independently_selected_verification_helper": spec.get("verification_helper", False),
                "program": spec["program"], "argv": argv, "cwd": str(cwd), "shell": False,
                "executable": _pin(executable), "input_bindings": bindings[spec["workspace"]],
                "inventory_before": before, "started": False, "returncode": None,
                "launch_error": None}
        with stdout.open("wb") as output, stderr.open("wb") as errors:
            try:
                result = subprocess.run(argv, cwd=cwd, env=environment, stdout=output,
                                        stderr=errors, check=False)
            except OSError as error:
                case["launch_error"] = {"type": type(error).__name__, "errno": error.errno}
            else:
                case.update(started=True, returncode=result.returncode)
        after = _inventory(cwd)
        prior = {row["relative_path"]: row for row in before}
        later = {row["relative_path"]: row for row in after}
        case.update(stdout=_pin(stdout), stderr=_pin(stderr), writer_closed=True,
            inventory_complete=True, captured_bytes_complete=True,
            native_status="succeeded" if case["returncode"] == 0 else "failed",
            semantic_compatibility="unverified", inventory_after=after,
            new_files=[row for name, row in later.items() if name not in prior],
            changed_files=[row for name, row in later.items()
                           if name in prior and not _same_bytes(row, prior[name])],
            removed_files=[row for name, row in prior.items() if name not in later],
            stdout_utf8=stdout.read_text(errors="replace"),
            stderr_utf8=stderr.read_text(errors="replace"),
            native_text_outputs=[{"relative_path": row["relative_path"],
                                  "text": (cwd / row["relative_path"]).read_text(errors="replace")}
                                 for row in after if row["relative_path"] not in prior
                                 and Path(row["relative_path"]).suffix in {".nal", ".pal", ".njs", ".pjs", ".aux"}])
        captures.append(case)
        _save(destination / (spec["id"] + ".json"), case)
        _save(destination / "CAPTURE_001.json", report)

    protected_after = {str(path): _pin(path) for path in sorted(protected_inputs)}
    staged_after = {name: _pin(Path(name)) for name in staged_originals}
    _save(destination / "ORIGINAL_INPUTS_AFTER_001.json", protected_after)
    _save(destination / "STAGED_INPUTS_AFTER_001.json", staged_after)
    assertions = {"selected_case_count": len(matrix["cases"]), "captured_case_count": len(captures),
        "original_inputs_unchanged": protected_before == protected_after,
        "staged_original_database_and_list_inputs_unchanged": staged_originals == staged_after,
        "all_selected_calls_started": all(case["started"] for case in captures),
        "native_returncodes": {case["id"]: case["returncode"] for case in captures},
        "capture_does_not_imply_native_success": True,
        "search_compatibility_tested": False, "episode_integration_tested": False}
    _save(destination / "ASSERTIONS_001.json", assertions)
    assert len(captures) == len(matrix["cases"]) == 16
    assert len({case["id"] for case in captures}) == 16
    assert protected_before == protected_after
    assert staged_originals == staged_after
    assert all(case["started"] for case in captures)
    assert all(case["writer_closed"] and case["captured_bytes_complete"] for case in captures)


def test_selected_primary_sources_for_failed_native_boundaries():
    """Acquire only the five primary files selected after the native failures."""
    from datetime import datetime, timezone
    from urllib.error import HTTPError, URLError
    from urllib.request import Request, urlopen

    location = os.environ.get("HMMER529_ATTEMPT")
    if not location:
        pytest.skip("requires the existing bounded 529 runner")
    destination = Path(location) / "temporary/blast_preparation_sources644"
    destination.mkdir(exist_ok=False)
    commit = "864d3b0d51f61ff2d39c694869d41786f62e9ba8"
    selected = (
        "src/objtools/blast/seqdb_writer/writedb.cpp",
        "src/objtools/blast/seqdb_writer/seqidlist_writer.cpp",
        "src/objtools/blast/seqdb_reader/seqdbcommon.cpp",
        "src/objtools/blast/seqdb_reader/seqidlist_reader.cpp",
        "src/algo/blast/api/pssm_engine.cpp",
    )
    rows = []
    for relative in selected:
        url = "https://raw.githubusercontent.com/ncbi/ncbi-cxx-toolkit-public/" + commit + "/" + relative
        path = destination / Path(relative).name
        row = {"url": url, "source_commit": commit, "repository_path": relative,
               "requested_at": datetime.now(timezone.utc).isoformat(), "http_status": None,
               "error": None, "artifact": None}
        request = Request(url, headers={"User-Agent": "bounded-source-fixture-644"})
        try:
            with urlopen(request) as response:
                row["http_status"] = response.status
                content = response.read()
        except HTTPError as error:
            row["http_status"] = error.code
            row["error"] = "HTTPError"
            content = error.read()
        except URLError as error:
            row["error"] = type(error).__name__
            content = str(error.reason).encode("utf-8", errors="replace")
        path.write_bytes(content)
        row["artifact"] = _pin(path)
        rows.append(row)
        _save(destination / "OFFICIAL_SOURCES_001.json", {
            "source_commit": commit, "sources": rows,
            "scope": "five explicitly selected primary code files; no molecular-data acquisition",
            "native_binary_equivalence": "not established"})
    assert len(rows) == 5
    assert all(row["http_status"] == 200 and row["error"] is None for row in rows)


def test_retained_binary_sequence_list_alias_targeted_followup():
    """Two selected new calls use the unchanged earlier binary restriction."""
    import sys

    location = os.environ.get("HMMER529_ATTEMPT")
    if not location:
        pytest.skip("requires the existing bounded 529 runner")
    attempt = Path(location)
    snapshot = Path(__file__).resolve().parents[1]
    packet = snapshot / PACKET
    retained = packet / "retained_native"
    prior = json.loads((retained / "CAPTURE_001.json").read_text())
    prior_conversion = next(c for c in prior["cases"] if c["id"] == "04_seqid_bound")
    binary_expected = next(f for f in prior_conversion["new_files"] if f["relative_path"] == "bound.bsl")
    manifest_path = retained / "inputs/original096-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    binary_source = retained / "cases/seqid_bound/bound.bsl"
    assert _same_bytes(_pin(binary_source), binary_expected)
    plan = json.loads((packet / "TARGETED_ALIAS_PLAN_002.json").read_text())
    destination = attempt / "temporary/blast_alias_binary644"
    destination.mkdir(exist_ok=False)
    (destination / "db").mkdir()
    (destination / "logs").mkdir()
    (destination / "tmp").mkdir()
    (destination / "cache").mkdir()
    shutil.copyfile(binary_source, destination / "bound.bsl")
    original_bindings = [{"role": "sequence_identifier_list", "original_native": binary_expected,
        "retained": _pin(binary_source), "staged": _pin(destination / "bound.bsl")}]
    original_fasta = retained / "inputs/original096.fa"
    protected = {binary_source, manifest_path, retained / "CAPTURE_001.json", original_fasta}
    staged = {destination / "bound.bsl"}
    for row in manifest["files"]:
        source = retained / "cases/seqid_bound/db" / Path(row["path"]).name
        target = destination / "db" / Path(row["path"]).name
        assert _same_bytes(_pin(source), row)
        shutil.copyfile(source, target)
        assert _same_bytes(_pin(target), row)
        protected.add(source)
        staged.add(target)
        original_bindings.append({"role": "database_file", "original_native": row,
                                  "retained": _pin(source), "staged": _pin(target)})
    before = {str(path): _pin(path) for path in sorted(protected | staged)}
    _save(destination / "INPUT_BINDINGS_002.json", original_bindings)
    _save(destination / "INPUT_PINS_BEFORE_002.json", before)

    # This fixture-only decoder follows the complete retained v5 writer/reader
    # schema. Integer layout is the writer's native host order, recorded here.
    raw = binary_source.read_bytes()
    cursor = 0

    def take(n):
        nonlocal cursor
        assert type(n) is int and n >= 0 and cursor + n <= len(raw)
        value = raw[cursor:cursor + n]
        cursor += n
        return value

    def integer(n):
        return int.from_bytes(take(n), byteorder=sys.byteorder, signed=False)

    assert take(1) == b"\0"
    file_size = integer(8)
    identifier_count = integer(8)
    assert file_size == len(raw) and identifier_count <= len(raw)
    decoded = {"format": "native_v5_seqidlist", "native_byte_order": sys.byteorder,
        "file_size": file_size, "identifier_count": identifier_count,
        "title": take(integer(4)).decode("utf-8"),
        "created_at_native": take(integer(1)).decode("utf-8"),
        "total_database_volume_length": integer(8),
        "database_created_at_native": None, "database_volume_names": None}
    if decoded["total_database_volume_length"]:
        decoded["database_created_at_native"] = take(integer(1)).decode("utf-8")
        decoded["database_volume_names"] = take(integer(4)).decode("utf-8")
    identifiers = []
    for ordinal in range(identifier_count):
        width = integer(1)
        if width == 255:
            width = integer(4)
        identifiers.append({"native_ordinal": ordinal, "stored_identifier": take(width).decode("utf-8")})
    assert cursor == len(raw)
    decoded["identifiers"] = identifiers
    decoded["source_identity"] = _pin(binary_source)
    decoded["definition_source"] = str(PACKET / "official_source/seqidlist_writer.cpp")
    _save(destination / "RETAINED_BINARY_LIST_DECODE_002.json", decoded)

    binaries = {Path(p).name: Path(p) for p in json.loads((attempt / "selected_native_executables.json").read_text())}
    assert set(binaries) == {"blastdb_aliastool", "blastdbcmd"}
    environment = dict(os.environ)
    overrides = {"BLAST_USAGE_REPORT": "false", "NCBI_DONT_USE_NCBIRC": "1",
        "TMPDIR": str(destination / "tmp"), "TMP": str(destination / "tmp"),
        "TEMP": str(destination / "tmp"), "XDG_CACHE_HOME": str(destination / "cache")}
    environment.update(overrides)
    cases = []
    for spec in plan["cases"]:
        executable = binaries[spec["program"]]
        argv = [str(executable), *spec["arguments"]]
        stdout = destination / "logs" / (spec["id"] + ".stdout")
        stderr = destination / "logs" / (spec["id"] + ".stderr")
        inventory_before = _inventory(destination)
        with stdout.open("wb") as output, stderr.open("wb") as errors:
            result = subprocess.run(argv, cwd=destination, env=environment,
                                    stdout=output, stderr=errors, check=False)
        inventory_after = _inventory(destination)
        old_paths = {row["relative_path"] for row in inventory_before}
        case = {**spec, "argv": argv, "cwd": str(destination), "executable": _pin(executable),
                "environment_overrides": overrides, "shell": False, "started": True,
                "returncode": result.returncode, "writer_closed": True,
                "captured_bytes_complete": True, "inventory_complete": True,
                "inventory_before": inventory_before, "inventory_after": inventory_after,
                "new_files": [row for row in inventory_after if row["relative_path"] not in old_paths],
                "stdout": _pin(stdout), "stderr": _pin(stderr),
                "stdout_utf8": stdout.read_text(), "stderr_utf8": stderr.read_text(),
                "native_alias_text": ((destination / "subset.nal").read_text()
                                      if (destination / "subset.nal").is_file() else None)}
        cases.append(case)
        _save(destination / "CAPTURE_002.json", {"cases": cases,
            "original_bound_list": binary_expected, "source_manifest": _pin(manifest_path),
            "original_bindings": original_bindings, "binary_list_decoding": decoded,
            "scope": "targeted unchanged-binary alias fixture; not production or episode verification"})
    after = {str(path): _pin(path) for path in sorted(protected | staged)}
    _save(destination / "INPUT_PINS_AFTER_002.json", after)
    _save(destination / "ASSERTIONS_002.json", {"inputs_unchanged": before == after,
        "selected_native_calls": len(cases), "returncodes": [c["returncode"] for c in cases],
        "decoded_identifier_count": identifier_count,
        "returned_record_count": len(cases[1]["stdout_utf8"].splitlines()),
        "search_compatibility_tested": False, "episode_integration_tested": False})
    assert before == after
    assert len(cases) == 2
    assert all(case["returncode"] == 0 for case in cases)
    assert [row["stored_identifier"] for row in identifiers] == ["KEEP_B"]
    original_records = [part.splitlines() for part in original_fasta.read_text().split(">") if part]
    selected_original = [(ordinal, "".join(lines[1:])) for ordinal, lines in enumerate(original_records)
                         if lines[0].split()[0] in {"KEEP_B", "lcl|KEEP_B"}]
    assert len(selected_original) == 1
    original_ordinal, original_sequence = selected_original[0]
    assert cases[1]["stdout_utf8"].splitlines() == [
        f"{original_ordinal}\tlcl|KEEP_B\t{len(original_sequence)}\t{original_sequence}"]


def test_existing_nested_28row_pssm_single_rps_followup():
    """Use the unchanged genuine ASN.1 object with only its type wrapper."""
    location = os.environ.get("HMMER529_ATTEMPT")
    if not location:
        pytest.skip("requires the existing bounded 529 runner")
    attempt = Path(location)
    snapshot = Path(__file__).resolve().parents[1]
    packet = snapshot / PACKET
    plan = json.loads((packet / "TARGETED_PROFILE_PLAN_003.json").read_text())
    boundary = json.loads((packet / "PSSM_CANDIDATE_BOUNDARY_003.json").read_text())
    original = snapshot / plan["source"]
    provenance = snapshot / plan["source_manifest"]
    schema = snapshot / plan["schema"]
    source_manifest = json.loads(provenance.read_text())
    source_identity = next(row for row in source_manifest["sources"]
                           if row["path"] == plan["source"])
    schema_identity = next(row for row in source_manifest["sources"]
                           if row["path"] == plan["schema"])
    assert _same_bytes(_pin(original), source_identity)
    assert _same_bytes(_pin(schema), schema_identity)
    assert "pssm                    PssmWithParameters," in schema.read_text()
    assert _pin(original)["sha256"] == boundary["source_sha256"]
    raw = original.read_bytes()
    start, end = boundary["byte_start_inclusive"], boundary["byte_end_exclusive"]
    original_object = raw[start:end]
    assert len(original_object) == boundary["object_bytes"]
    assert hashlib.sha256(original_object).hexdigest() == boundary["object_sha256"]
    assert raw[:start].endswith(b"queries pssm ")
    assert original_object.startswith(b"{") and original_object.endswith(b"}")
    wrapper = {"prefix": boundary["wrapper_prefix"], "suffix": boundary["wrapper_suffix"]}
    standalone = wrapper["prefix"].encode() + original_object + wrapper["suffix"].encode()
    assert len(standalone) == boundary["wrapped_bytes"]
    assert hashlib.sha256(standalone).hexdigest() == boundary["wrapped_sha256"]

    destination = attempt / "temporary/blast_profile28_native644"
    destination.mkdir(exist_ok=False)
    for directory in ["inputs", "logs", "tmp", "cache"]:
        (destination / directory).mkdir()
    source_copy = destination / "inputs/webpsi.2ndround.ss.asn"
    object_copy = destination / "inputs/pssm.object.asn"
    profile = destination / "inputs/webpsi.2ndround.pssm.asn"
    list_file = destination / "profiles.list"
    shutil.copyfile(original, source_copy)
    shutil.copyfile(provenance, destination / "inputs/SOURCE_MANIFEST.json")
    shutil.copyfile(schema, destination / "inputs/blast.asn")
    object_copy.write_bytes(original_object)
    profile.write_bytes(standalone)
    list_file.write_text(plan["original_profile_list_bytes"])
    _save(destination / "inputs/TYPE_WRAPPER_003.json", wrapper)
    _save(destination / "INPUT_BINDINGS_003.json", {
        "original": _pin(original), "source_manifest": _pin(provenance),
        "schema": _pin(schema), "source_copy": _pin(source_copy),
        "source_object": {**boundary, "retained_object": _pin(object_copy)},
        "standalone_profile": _pin(profile), "wrapper": wrapper,
        "list": _pin(list_file), "profile_entries": [{"ordinal": 0,
            "original_token": "inputs/webpsi.2ndround.pssm.asn", "realized_profile": _pin(profile)}],
        "qualification": "byte-exact authentic nested object with standalone type wrapper; no field edits"})
    protected = {original, provenance, schema, source_copy, object_copy, profile, list_file}
    protected.update(path for path in (destination / "inputs").iterdir() if path.is_file())
    before = {str(path): _pin(path) for path in sorted(protected)}
    _save(destination / "INPUT_PINS_BEFORE_003.json", before)

    binaries = [Path(p) for p in json.loads((attempt / "selected_native_executables.json").read_text())]
    assert len(binaries) == 1 and binaries[0].name == "makeprofiledb"
    executable = binaries[0]
    spec = plan["case"]
    argv = [str(executable), *spec["arguments"]]
    environment = dict(os.environ)
    overrides = {"BLAST_USAGE_REPORT": "false", "NCBI_DONT_USE_NCBIRC": "1",
        "TMPDIR": str(destination / "tmp"), "TMP": str(destination / "tmp"),
        "TEMP": str(destination / "tmp"), "XDG_CACHE_HOME": str(destination / "cache")}
    environment.update(overrides)
    stdout, stderr = destination / "logs/rps.stdout", destination / "logs/rps.stderr"
    inventory_before = _inventory(destination)
    with stdout.open("wb") as output, stderr.open("wb") as errors:
        result = subprocess.run(argv, cwd=destination, env=environment,
                                stdout=output, stderr=errors, check=False)
    inventory_after = _inventory(destination)
    old_files = {row["relative_path"]: row for row in inventory_before}
    new_files = [row for row in inventory_after if row["relative_path"] not in old_files]
    case = {**spec, "argv": argv, "cwd": str(destination), "executable": _pin(executable),
        "environment_overrides": overrides, "shell": False, "started": True,
        "returncode": result.returncode, "writer_closed": True,
        "captured_bytes_complete": True, "inventory_complete": True,
        "inventory_before": inventory_before, "inventory_after": inventory_after,
        "new_files": new_files,
        "changed_files": [row for row in inventory_after if row["relative_path"] in old_files
                          and not _same_bytes(row, old_files[row["relative_path"]])],
        "removed_paths": sorted(set(old_files) - {row["relative_path"] for row in inventory_after}),
        "stdout": _pin(stdout), "stderr": _pin(stderr),
        "stdout_utf8": stdout.read_text(), "stderr_utf8": stderr.read_text(),
        "native_aux_text": ((destination / "profiles.aux").read_text()
                            if (destination / "profiles.aux").is_file() else None)}
    _save(destination / "CAPTURE_003.json", {"cases": [case], "source_identity": source_identity,
        "source_boundary": boundary, "scope": "one selected native RPS preparation; no search or episode verification"})
    after = {str(path): _pin(path) for path in sorted(protected)}
    _save(destination / "INPUT_PINS_AFTER_003.json", after)
    _save(destination / "ASSERTIONS_003.json", {"inputs_unchanged": before == after,
        "selected_native_calls": 1, "returncodes": [result.returncode],
        "source_object_bytes_unchanged": profile.read_bytes() == standalone,
        "profile_count_parsed_in_fixture": None,
        "search_compatibility_tested": False, "episode_integration_tested": False})
    assert before == after
    assert result.returncode == 0
    assert {"profiles.rps", "profiles.loo", "profiles.aux", "profiles.freq"}.issubset(
        {row["relative_path"] for row in new_files})
