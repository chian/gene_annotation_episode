"""Private adapter controls and real saved-driver execution; never native fits.

Constructed sheets/identities below are engineering fixtures, not producing
attempt custody. The opt-in239 case uses its exact retained observed sheet.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from gene_annotation_episode import molecular_sequence_execution_contracts as contracts
from gene_annotation_episode import molecular_sequence_execution_driver as adapter
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.protease_kinetics_measurements import populate_protease_kinetics_sheet
from gene_annotation_episode.glycosylation_measurements import build_glycosylation_sheet
from tests.test_protease_kinetics_measurements import supplied_fixture


ROOT = Path(__file__).resolve().parents[1]


def pin(path):
    raw = Path(path).read_bytes()
    return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def _environment(software):
    result = {"PYTHONHOME": software["python_home"], "PYTHONPATH": os.pathsep.join(software["import_roots"]),
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1"}
    for key in ("PATH", "LD_LIBRARY_PATH", "LANG", "LC_ALL"):
        if key in os.environ:
            result[key] = os.environ[key]
    return result


def software_fixture(directory, *, isolated_source=False):
    """Bind actual selected source/runtime files for these saved executions."""
    directory.mkdir()
    source = ROOT
    if isolated_source:
        source = directory / "selected-source"
        package = source / "gene_annotation_episode"
        package.mkdir(parents=True)
        for path in (ROOT / "gene_annotation_episode").glob("*.py"):
            shutil.copyfile(path, package / path.name)
    binary = directory / "selected-python"
    shutil.copyfile(Path(sys.executable).resolve(), binary)
    binary.chmod(0o700)
    stdlib = Path(json.__file__).resolve().parent.parent
    roots = [source]
    for supplied in sys.path:
        if not supplied:
            continue
        candidate = Path(supplied).resolve()
        if (not candidate.is_dir() or candidate == Path("/") or candidate == stdlib
                or candidate.is_relative_to(stdlib / "lib-dynload") or candidate.is_relative_to(ROOT)):
            continue
        if candidate not in roots:
            roots.append(candidate)
    files = {str(binary): pin(binary)}
    inventories = [(source / "gene_annotation_episode", False), (stdlib, True),
        *((root, False) for root in roots[1:])]
    for inventory, exclude_packages in inventories:
        for path in inventory.rglob("*"):
            relative = path.relative_to(inventory)
            if (not path.is_file() or path.is_symlink() or "__pycache__" in relative.parts
                    or path.suffix in (".pyc", ".pyo") or exclude_packages and any(
                        name in relative.parts for name in ("site-packages", "dist-packages"))):
                continue
            resolved = path.resolve()
            files[str(resolved)] = pin(resolved)
    manifest = directory / "selected-software.json"
    manifest.write_text(json.dumps([files[key] for key in sorted(files)]))
    return {"version": contracts.SOFTWARE_VERSION, "python": pin(binary), "python_home": str(Path(sys.prefix).resolve()),
        "python_version": sys.version, "import_roots": list(map(str, roots)), "software_files_file": pin(manifest),
        "software_files_ref": "artifact_" + pin(manifest)["sha256"]}


@pytest.fixture(scope="module")
def selected_software(tmp_path_factory):
    return software_fixture(tmp_path_factory.mktemp("molecular-selected-parent") / "software")


def engineering_sheet(directory):
    measurements, capture, context = supplied_fixture()
    sheet = populate_protease_kinetics_sheet(measurements=measurements, native_capture=capture, assay_context=context)
    path = directory / "engineering-sheet.json"
    path.write_text(json.dumps(sheet, indent=3) + "\n")
    return path


def selected_plan(directory, software, *, sheet=None, operation="analyze_protease_kinetics"):
    directory.mkdir(parents=True)
    if sheet is None:
        sheet = engineering_sheet(directory)
    driver_version = "molecular_sequence_driver_request_v2" if operation == "analyze_protease_kinetics" else "molecular_sequence_driver_request_v1"
    request = {"version": driver_version, "mode": "saved_sheet", "attempt_identity": {
        key: "asserted-engineering-" + key for key in ("run_id", "episode_id", "resource_id", "operation_key", "execution_id")},
        "selection": {"operation": operation, "sheet_file": pin(sheet)}, "scientific_context": None}
    request_path = directory / "original-request.json"
    request_path.write_text(json.dumps(request, indent=4) + "\n")
    selection = {"operation": operation, "mode": "saved_sheet", "driver_request": request, "request_file": pin(request_path)}
    environment = _environment(software)
    policy = {"memory_bytes": 21474836480, "scratch_bytes": 4294967296, "wall_seconds": None}
    payload = contracts.selected_payload_sha256(selection=selection, software=software, policy=policy, selected_environment=environment)
    job = {"argv": [software["python"]["path"], "-B", "-m", contracts.ADAPTER_MODULE, "--plan", contracts.PLAN_FILENAME,
        "--selected-payload-sha256", payload], "environment": environment}
    key, run, episode = "engineering-run:engineering-episode:0", "engineering-run", "engineering-episode"
    original = directory / ".episode-operations" / digest({"run": run, "episode": episode}) / digest(key)
    original.mkdir(parents=True)
    identity = {"run_id": run, "episode_id": episode, "resource_id": "engineering-local", "execution_id": str(original / "native.json"),
        "attempt_id": digest(key), "operation_key": key, "assignment_sha256": digest({"engineering": True}), "requested_job_sha256": digest(job)}
    plan = contracts.build_molecular_sequence_selected_plan(identity=identity, requested_job=job, selection=selection,
        software=software, policy=policy, selected_environment=environment)
    plan_path = original / contracts.PLAN_FILENAME
    plan_path.write_text(json.dumps(plan, indent=3) + "\n")
    return plan, plan_path


def run_cli(plan, plan_path):
    process = subprocess.run(contracts.molecular_sequence_adapter_argv(plan), cwd=plan_path.parent,
        env=plan["selected_environment"], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (plan_path.parent / "adapter.stdout").write_bytes(process.stdout)
    (plan_path.parent / "adapter.stderr").write_bytes(process.stderr)
    bundle_path = Path(plan["attempt_directory"]) / contracts.BUNDLE_FILENAME
    assert bundle_path.is_file(), process.stderr.decode()
    return process, json.loads(bundle_path.read_bytes())


@pytest.mark.parametrize("operation", contracts.OPERATIONS)
def test_closed_existing_profiles_bind_an_independent_payload_without_hash_cycle(tmp_path, selected_software, operation):
    plan, _ = selected_plan(tmp_path / "case", selected_software, operation=operation)
    expected = digest({"version": contracts.PAYLOAD_VERSION,
        **{key: plan[key] for key in ("selection", "software", "policy", "selected_environment")}})
    assert expected == plan["selected_payload_sha256"] == plan["requested_job"]["argv"][-1]
    assert contracts.validate_molecular_sequence_selected_plan(plan, expected_payload_sha256=expected) == plan


@pytest.mark.parametrize("changed", ["request_body", "request_pin", "software", "policy", "environment"])
def test_selected_argv_digest_rejects_payload_substitution(changed, tmp_path, selected_software):
    plan, _ = selected_plan(tmp_path / "case", selected_software)
    expected = plan["selected_payload_sha256"]
    if changed == "request_body": plan["selection"]["driver_request"]["attempt_identity"]["run_id"] = "substituted"
    elif changed == "request_pin": plan["selection"]["request_file"]["sha256"] = "f"*64
    elif changed == "software": plan["software"]["python_version"] += " changed"
    elif changed == "policy": plan["policy"]["scratch_bytes"] -= 1
    else: plan["selected_environment"]["SELECTED_CHANGE"] = "yes"
    # An internally consistent rewritten plan hash cannot replace selected argv.
    plan["selected_payload_sha256"] = contracts.selected_payload_sha256(**{key: plan[key] for key in
        ("selection", "software", "policy", "selected_environment")})
    with pytest.raises(ValueError, match="selected_payload_sha256"):
        contracts.validate_molecular_sequence_selected_plan(plan, expected_payload_sha256=expected)


def test_external_cli_digest_mismatch_invokes_no_private_driver(tmp_path, selected_software, monkeypatch):
    plan, path = selected_plan(tmp_path / "case", selected_software)
    monkeypatch.setattr(adapter.subprocess, "Popen", lambda *args, **kwargs: pytest.fail("digest mismatch invoked driver"))
    assert adapter.main(["--plan", str(path), "--selected-payload-sha256", "0"*64]) == 1
    assert not Path(plan["attempt_directory"]).exists()


def test_wrong_selected_request_pin_retains_observed_bytes_and_invokes_zero(tmp_path, selected_software, monkeypatch):
    plan, path = selected_plan(tmp_path / "case", selected_software)
    original = Path(plan["selection"]["request_file"]["path"])
    original.write_bytes(original.read_bytes() + b" ")
    monkeypatch.chdir(path.parent)
    monkeypatch.setattr(adapter.subprocess, "Popen", lambda *args, **kwargs: pytest.fail("bad request invoked driver"))
    result = adapter.execute_molecular_sequence_selected_plan(plan, expected_payload_sha256=plan["selected_payload_sha256"], plan_bytes=path.read_bytes())
    assert result["invocation"]["invocation_count"] == result["invocation"]["launch_attempt_count"] == 0
    assert any(row["code"] == "request_identity_conflict" for row in result["failures"])
    retained = result["retained_inputs"]["request"]
    assert retained["byte_identity_matches_selected"] is False
    assert Path(retained["observed"]["path"]).read_bytes() == original.read_bytes()


def test_actual_saved_driver_keeps_asserted_identity_separate_and_request_bytes_exact(tmp_path, selected_software):
    plan, path = selected_plan(tmp_path / "case", selected_software)
    original_request = Path(plan["selection"]["request_file"]["path"]).read_bytes()
    process, result = run_cli(plan, path)
    assert process.returncode == 0, process.stderr.decode()
    assert result["invocation"]["invocation_count"] == 1 and result["invocation"]["process_exit_observed"] is True
    assert result["private_asserted_attempt_identity"] == plan["selection"]["driver_request"]["attempt_identity"]
    assert result["private_asserted_attempt_identity"]["run_id"] != result["identity"]["run_id"]
    retained = result["retained_inputs"]["request"]
    assert retained["content_changed"] is False and retained["selected"]["path"] != retained["observed"]["path"]
    assert Path(retained["observed"]["path"]).read_bytes() == original_request
    assert result["software_verification"]["inner_complete_import_closure_observed"] is False
    rows = {row["role"]: row for row in result["files"]}
    assert rows["sheet"]["comparison"] == rows["components"]["comparison"] == "matches"
    declaration = json.loads(Path(rows["declaration"]["observed"]["path"]).read_bytes())
    assert declaration["native_call_state"] == "not_requested"
    for field in ("observed_request_file", "comparison", "declaration_path"):
        inconsistent = deepcopy(result)
        if field == "observed_request_file":
            inconsistent[field]["sha256"] = "f"*64
        else:
            component = next(row for row in inconsistent["files"] if row["role"] == "components")
            if field == "comparison": component[field] = "mismatch"
            else: component["declared"]["relative_path"] = "other.json"
        with pytest.raises(ValueError):
            contracts.validate_molecular_sequence_attempt_bundle(inconsistent, plan=plan)


def test_actual_legacy_v1_saved_driver_and_components_keep_their_original_versions(tmp_path, selected_software):
    directory = tmp_path / "legacy"
    directory.mkdir()
    # Explicit source-format engineering log, not an observed native scan.
    log = ("# N-linked glycosylation sequon scan (N-X-[S/T], X\u2260P)\nSequence length: 3\n"
        "Total sequons found: 1\n\nPositions (1-based):\n- 1: NST")
    sheet = build_glycosylation_sheet("find_n_glycosylation_motifs", log,
        sequence="NST", parameters={"allow_overlap": False})
    saved = directory / "legacy-sheet.json"
    saved.write_text(json.dumps(sheet))
    plan, path = selected_plan(directory / "selected", selected_software, sheet=saved, operation="find_n_glycosylation_motifs")
    process, result = run_cli(plan, path)
    assert process.returncode == 0, process.stderr.decode()
    rows = {row["role"]: row for row in result["files"]}
    declaration = json.loads(Path(rows["declaration"]["observed"]["path"]).read_bytes())
    assert declaration["version"] == "molecular_sequence_driver_declaration_v1"
    assert set(declaration["files"]) == {"capture", "sheet", "components"}
    components = json.loads(Path(rows["components"]["observed"]["path"]).read_bytes())
    assert components["schema"] == "glycosylation_measurement_components_v1"
    assert components["summary"]["retained_printed_row_count"] == 1
    assert Path(rows["sheet"]["observed"]["path"]).read_bytes() == saved.read_bytes()


def test_nonzero_saved_driver_preserves_independent_written_sheet(tmp_path, selected_software):
    directory = tmp_path / "case"
    directory.mkdir()
    bad = directory / "incompatible-sheet.json"
    bad.write_bytes(b'{"schema":"constructed-incompatible-sheet"}\n')
    plan, path = selected_plan(directory / "selected", selected_software, sheet=bad)
    process, result = run_cli(plan, path)
    assert process.returncode == 1 and result["invocation"]["returncode"] == 1
    assert any(row["code"] == "inner_nonzero_exit" for row in result["failures"])
    rows = {row["role"]: row for row in result["files"]}
    assert rows["sheet"]["observed_state"] == "present" and rows["sheet"]["comparison"] == "matches"
    assert Path(rows["sheet"]["observed"]["path"]).read_bytes() == bad.read_bytes()
    assert rows["components"]["observed_state"] == "absent"


@pytest.mark.parametrize("change", ["missing_declaration", "malformed_declaration", "missing_components"])
def test_independent_saved_outputs_survive_explicit_postprocess_fault(tmp_path, selected_software, monkeypatch, change):
    plan, path = selected_plan(tmp_path / "case", selected_software)
    # Invoke the real saved CLI once. Only the later adapter-observation port is
    # faulted; no native callable/source/fit or private driver is substituted.
    observed = adapter._observe_outputs
    calls = []
    def inject(plan, request, failures):
        calls.append(1)
        output = Path(plan["attempt_directory"]) / contracts.OUTPUT_DIRECTORY
        if change == "missing_declaration": (output / "declaration.json").unlink()
        elif change == "malformed_declaration": (output / "declaration.json").write_bytes(b'{"broken":')
        else: (output / "components.json").unlink()
        return observed(plan, request, failures)
    monkeypatch.setattr(adapter, "_observe_outputs", inject)
    monkeypatch.chdir(path.parent)
    monkeypatch.setattr(adapter, "_software", lambda *args: [])  # Explicit engineering verifier fixture, not provenance.
    result = adapter.execute_molecular_sequence_selected_plan(plan, expected_payload_sha256=plan["selected_payload_sha256"], plan_bytes=path.read_bytes())
    assert calls == [1] and result["invocation"]["invocation_count"] == 1
    rows = {row["role"]: row for row in result["files"]}
    assert rows["sheet"]["observed_state"] == "present"
    expected = "declaration_missing" if change == "missing_declaration" else "declaration_malformed" if change == "malformed_declaration" else "output_unavailable"
    assert any(row["code"] == expected for row in result["failures"])


@pytest.mark.parametrize("started", [False, True])
def test_unsealed_uncertain_attempt_never_invokes_again(tmp_path, selected_software, monkeypatch, started):
    plan, path = selected_plan(tmp_path / "case", selected_software)
    root = Path(plan["attempt_directory"])
    root.mkdir()
    (root / contracts.OWNER_FILENAME).write_bytes(path.read_bytes())
    if started:
        (root / contracts.STARTED_FILENAME).write_text('{"constructed_uncertain_marker":true}')
    monkeypatch.chdir(path.parent)
    monkeypatch.setattr(adapter.subprocess, "Popen", lambda *args, **kwargs: pytest.fail("uncertain attempt reran"))
    with pytest.raises(ValueError, match="original_invocation_uncertain"):
        adapter.execute_molecular_sequence_selected_plan(plan, expected_payload_sha256=plan["selected_payload_sha256"], plan_bytes=path.read_bytes())
    assert not (root / contracts.BUNDLE_FILENAME).exists()


def test_overlapping_adapter_cannot_invoke_or_seal_the_original_writers_attempt(tmp_path, selected_software, monkeypatch):
    plan, path = selected_plan(tmp_path / "case", selected_software)
    root = Path(plan["attempt_directory"])
    original_write, original_popen = adapter.immutable_bytes, adapter.subprocess.Popen
    losing_entries, invocations = [], []
    def overlap(target, raw):
        original_write(target, raw)
        if Path(target).name == contracts.OWNER_FILENAME:
            before = sorted(item.name for item in root.iterdir())
            with pytest.raises(ValueError, match="original_invocation_uncertain"):
                adapter.execute_molecular_sequence_selected_plan(plan,
                    expected_payload_sha256=plan["selected_payload_sha256"], plan_bytes=path.read_bytes())
            assert sorted(item.name for item in root.iterdir()) == before
            assert not (root / contracts.BUNDLE_FILENAME).exists()
            losing_entries.append(1)
    def invoke(*args, **kwargs):
        invocations.append(1)
        return original_popen(*args, **kwargs)
    monkeypatch.chdir(path.parent)
    monkeypatch.setattr(adapter, "immutable_bytes", overlap)
    monkeypatch.setattr(adapter.subprocess, "Popen", invoke)
    monkeypatch.setattr(adapter, "_software", lambda *args: [])  # Explicit engineering verifier, not provenance.
    result = adapter.execute_molecular_sequence_selected_plan(plan,
        expected_payload_sha256=plan["selected_payload_sha256"], plan_bytes=path.read_bytes())
    assert losing_entries == [1] and invocations == [1]
    assert result["invocation"]["invocation_count"] == 1
    assert (root / contracts.BUNDLE_FILENAME).is_file()


def test_sealed_replay_uses_retained_bytes_after_selected_paths_disappear(tmp_path, monkeypatch):
    software = software_fixture(tmp_path / "historical-software", isolated_source=True)
    plan, path = selected_plan(tmp_path / "case", software)
    process, original = run_cli(plan, path)
    assert process.returncode == 0, process.stderr.decode()
    request = Path(plan["selection"]["request_file"]["path"])
    source = Path(software["import_roots"][0])
    request.unlink()
    Path(software["software_files_file"]["path"]).unlink()
    Path(software["python"]["path"]).unlink()
    shutil.rmtree(source)
    monkeypatch.setattr(adapter.subprocess, "Popen", lambda *args, **kwargs: pytest.fail("sealed replay reran driver"))
    monkeypatch.setattr(adapter, "_software", lambda *args: pytest.fail("sealed replay demanded historical software"))
    assert adapter.read_molecular_sequence_selected_replay(plan, expected_payload_sha256=plan["selected_payload_sha256"]) == original
    retained = original["retained_inputs"]["request"]["observed"]
    assert Path(retained["path"]).is_file()
    component = next(row for row in original["files"] if row["role"] == "components")["observed"]
    Path(component["path"]).chmod(0o600)
    Path(component["path"]).write_bytes(b"changed\n")
    with pytest.raises(ValueError, match="replay_artifact_conflict"):
        adapter.read_molecular_sequence_selected_replay(plan, expected_payload_sha256=plan["selected_payload_sha256"])


def test_authentic239_saved_adapter_keeps_old_observation_and_new_components_separate(tmp_path, selected_software):
    filename = os.environ.get("HMMER_NATIVE_ORACLE_PROTEASE_RETAINED_SHEET")
    if filename is None:
        pytest.skip("requires root's explicitly selected exact retained239 sheet")
    sheet = Path(filename)
    raw = sheet.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == "5ce86df48853601e7d05472f30fcfef148116ad9031f5c4035d5f10f114a5765"
    plan, path = selected_plan(tmp_path / "case", selected_software, sheet=sheet)
    process, result = run_cli(plan, path)
    assert process.returncode == 0, process.stderr.decode()
    rows = {row["role"]: row for row in result["files"]}
    assert Path(rows["sheet"]["observed"]["path"]).read_bytes() == raw == sheet.read_bytes()
    components = json.loads(Path(rows["components"]["observed"]["path"]).read_bytes())
    assert components["schema"] == "protease_kinetics_components_v2"
    assert components["native_values"]["params"] == [11.959381204925378, 2.9671605866008814]
    assert components["physical_components"]["apparent_catalytic_efficiency"]["uncertainty"]["state"] == "qualified"
    assert json.loads(Path(rows["declaration"]["observed"]["path"]).read_bytes())["native_call_state"] == "not_requested"


def test_valid_payload_and_request_pin_cannot_hide_selected_request_document_conflict(tmp_path, selected_software, monkeypatch):
    plan, path = selected_plan(tmp_path / "case", selected_software)
    original_pin = deepcopy(plan["selection"]["request_file"])
    original_bytes = Path(original_pin["path"]).read_bytes()
    plan["selection"]["driver_request"]["attempt_identity"]["run_id"] = "independently-selected-different-body"
    payload = contracts.selected_payload_sha256(**{key: plan[key] for key in
        ("selection", "software", "policy", "selected_environment")})
    plan["requested_job"]["argv"][-1] = payload
    plan["identity"]["requested_job_sha256"] = digest(plan["requested_job"])
    plan = contracts.build_molecular_sequence_selected_plan(**{key: plan[key] for key in
        ("identity", "requested_job", "selection", "software", "policy", "selected_environment")})
    assert contracts.validate_molecular_sequence_selected_plan(plan, expected_payload_sha256=payload) == plan
    assert pin(Path(original_pin["path"])) == original_pin
    assert json.loads(original_bytes) != plan["selection"]["driver_request"]
    path.write_text(json.dumps(plan, indent=3) + "\n")
    monkeypatch.chdir(path.parent)
    monkeypatch.setattr(adapter.subprocess, "Popen", lambda *args, **kwargs: pytest.fail("document conflict invoked driver"))
    result = adapter.execute_molecular_sequence_selected_plan(plan,
        expected_payload_sha256=payload, plan_bytes=path.read_bytes())
    assert result["selected_payload_sha256"] == payload
    assert result["invocation"]["invocation_count"] == result["invocation"]["launch_attempt_count"] == 0
    assert [row["code"] for row in result["failures"] if row["stage"] == "request"] == ["request_document_conflict"]
    retained = result["retained_inputs"]["request"]
    assert retained["selected"] == original_pin and retained["byte_identity_matches_selected"] is True
    assert {key: retained["observed"][key] for key in ("sha256", "size_bytes")} == {
        key: original_pin[key] for key in ("sha256", "size_bytes")}
    assert Path(retained["observed"]["path"]).read_bytes() == original_bytes
