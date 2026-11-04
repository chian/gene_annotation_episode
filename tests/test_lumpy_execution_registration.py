"""Engineered metadata/lifecycle controls for the existing LUMPY registration.

These are pure contracts and host dispatch controls. Software pins, Files and
lifecycle observations below are explicitly engineered. They open no ELF/BAM,
fabricate no native success, write no SQL history and run no scientific work.
The native owner and the ordinary VCF owner keep their separate test scopes.
"""
from copy import deepcopy
import base64
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import native_lumpy_execution as lumpy
from gene_annotation_episode import local_file_capture_results as captures
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.execution_progress import ExecutionTargetReader
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode import practical_execution_operations as operations
from gene_annotation_episode import practical_execution_records as records


def forbidden(*args, **kwargs):
    raise AssertionError("registration control attempted native work or an unselected path")


def _file(token, format):
    raw = token.encode()
    sha = hashlib.sha256(raw).hexdigest()
    return dict(artifact_ref="artifact_" + sha, sha256=sha, size_bytes=len(raw), format=format)


def _pin(path):
    return dict(path=str(path), sha256="a" * 64, size_bytes=1)


@pytest.fixture
def case(tmp_path):
    """Declared metadata only: no selected software or input body is present."""
    driver_root = tmp_path / "engineered-driver"
    native_root = tmp_path / "engineered-software" / "native"
    distributions = ("jsonschema", "attrs", "referencing", "rpds-py", "jsonschema-specifications")
    driver = dict(python_executable=str(driver_root / "bin/python"), python_sha256="b" * 64,
        python_version="engineered", module_root=str(driver_root / "source"),
        implementation_files=[dict(module=module, sha256="c" * 64) for module in (
            lumpy.DRIVER_MODULE, "gene_annotation_episode.native_atac_differential_reference")],
        dependencies=[dict(distribution=name, version="engineered", package_root=str(driver_root / name),
            files=[_pin(driver_root / name / "__init__.py")]) for name in distributions])
    software = dict(driver_runtime=driver, native_runtime=dict(
        executable=_pin(native_root / "bin/lumpy"), loader=_pin(native_root / "loader"),
        libraries=[], reported_version=None))
    common = dict(output_sample_label="declared-label", declared_sample_id=None,
        reference_id=None, read_group=None)
    request = dict(version=lumpy.REQUEST_VERSION, operation=lumpy.OPERATION, mode=lumpy.MODE,
        run_key="engineered-inspection", signals=[
            dict(kind="paired_end", signal_key="pe", **common, bam=_file("engineered PE metadata", "bam"),
                histogram=_file("engineered histogram metadata", "lumpy_insert_histogram"),
                parameters=dict(mean="300", stdev="20", read_length=100, min_non_overlap=100,
                    discordant_z=4, back_distance=10, weight=1, min_mapping_threshold=0)),
            dict(kind="split_read", signal_key="sr", **common, bam=_file("engineered SR metadata", "bam"),
                parameters=dict(back_distance=10, min_non_overlap=0, weight=1,
                    min_mapping_threshold=0, min_clip=20))],
        parameters=dict(minimum_sample_weight=1, trim_threshold="0", probability_output=False))
    bindings = []
    for signal in request["signals"]:
        for role in ("bam", "histogram") if signal["kind"] == "paired_end" else ("bam",):
            bindings.append(dict(input_key=signal["signal_key"] + ":" + role,
                file=deepcopy(signal[role]), path=str(tmp_path / "absent-inputs" / (signal["signal_key"] + "." + role))))
    environment = dict(PATH="/usr/bin:/bin", LC_ALL="C.UTF-8", PYTHONHOME=str(driver_root),
        PYTHONPATH=":".join([driver["module_root"], str(driver_root)]))
    environment.update({key: "1" for key in ("PYTHONNOUSERSITE", "PYTHONSAFEPATH", "PYTHONDONTWRITEBYTECODE",
        "OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS")})
    environment.update({key: str(tmp_path / "selected-temporary" / key) for key in
        ("TMP", "TEMP", "TMPDIR", "XDG_CACHE_HOME", "PIP_CACHE_DIR")})
    requested = lumpy.requested_job_from_lumpy(dict(request=request, software=software,
        input_bindings=bindings), environment=environment)
    assignment = dict(version=records.ASSIGNMENT_VERSION, assignment_id="engineered-assignment",
        resource_id="local", resource_kind="local", workspace=str(tmp_path),
        endpoint="completed_job_outputs", requested_job=requested,
        progress_requirements=[dict(key="outputs", credit=1, predicate=dict(
            kind="requested_job_outputs", output_roles=["vcf", "bam_headers", "seal"]))],
        completion_keys=["outputs"], initial_context=dict(revision=0, cwd=str(tmp_path), environment={}),
        inventory_snapshot={}, constraints=dict(allocation=deepcopy(lumpy.POLICY)))
    binding = dict(operation=lumpy.OPERATION, mode=lumpy.MODE, software=deepcopy(software))
    configuration = dict(kind="local", workspace=str(tmp_path), policy=deepcopy(lumpy.POLICY), native_lumpy=[binding])
    run_id, episode_id = "engineered-run", "engineered-episode"
    key = run_id + ":" + episode_id + ":0"
    root = tmp_path / ".episode-operations" / records.digest(dict(run=run_id, episode=episode_id)) / records.digest(key)
    identity = dict(run_id=run_id, episode_id=episode_id, resource_id="local", execution_id=str(root / "native.json"),
        attempt_id=records.digest(key), operation_key=key, requested_job_sha256=records.digest(requested),
        assignment_sha256=records.digest(assignment))
    plan = lumpy.lumpy_plan(assignment, identity, policy=lumpy.POLICY)
    target = dict(version="execution_target_v1", handle="source_" + "1" * 24,
        run_id=run_id, resource_id="local", resource_kind="local", execution_id=identity["execution_id"],
        request_sha256=identity["requested_job_sha256"], origin_episode_id=episode_id,
        assignment=deepcopy(assignment), scope=dict(subject_refs=[]))
    return SimpleNamespace(request=request, requested=requested, assignment=assignment, binding=binding,
        configuration=configuration, plan=plan, identity=identity, target=target, key=key,
        run_id=run_id, episode_id=episode_id, tmp_path=tmp_path)


def test_registered_job_is_closed_local_and_uses_actual_binding_metadata(case):
    original = deepcopy(case.assignment)
    assert records.validate_assignment(case.assignment) == original
    assert Draft202012Validator(records.REQUESTED_JOB_SCHEMA).is_valid(case.requested)
    operations.LocalPracticalOperations(case.configuration).validate_assignment(case.assignment)
    assert case.assignment == original


@pytest.mark.parametrize("fault", ["resource_kind", "resource_id", "software", "policy", "unbound"])
def test_configuration_and_assignment_mismatches_are_rejected_without_native(case, fault):
    selected, config = deepcopy(case.assignment), deepcopy(case.configuration)
    if fault == "resource_kind": selected["resource_kind"] = "hpc"
    elif fault == "resource_id": selected.pop("resource_id")
    elif fault == "software": selected["requested_job"]["native_lumpy"]["software"]["native_runtime"]["reported_version"] = "other"
    elif fault == "policy": config["policy"]["scratch_bytes"] -= 1
    else: config["native_lumpy"] = []
    with pytest.raises(ValueError):
        operations.LocalPracticalOperations(config).validate_assignment(selected)


def test_public_compact_and_private_job_schemas_have_distinct_boundaries(case):
    owner = ExecutionEpisodes.__new__(ExecutionEpisodes)
    owner.resources = {"local": deepcopy(case.configuration)}
    public = owner._request_schema("local", selected=True, internal=False)
    private = owner._request_schema("local", selected=True, internal=True)
    assert not Draft202012Validator(public).is_valid(case.assignment)
    assert Draft202012Validator(private).is_valid(case.assignment)
    from gene_annotation_episode.lumpy_request_binding import resource_assignment_schema
    compact = resource_assignment_schema("local", bindings=[case.binding])
    assert compact in public["anyOf"]
    assert "software" not in compact["properties"]["request"]["properties"]


def test_roles_expand_headers_in_original_signal_order_without_host_selection(case):
    roles = ["bam_headers", "vcf", "stderr", "seal"]
    rows = records.lumpy_role_outputs(case.request, roles)
    assert [row["relative_path"] for row in rows] == [
        "headers/000000.sam", "headers/000001.sam", "native/result.vcf", "native/stderr.log", lumpy.SEAL_FILENAME]
    actual = records.requested_job_role_paths(case.assignment, dict(execution_id=case.identity["execution_id"]), roles)
    assert actual == [str(Path(case.plan["attempt_directory"]) / row["relative_path"]) for row in rows]
    assert case.request["signals"][0]["declared_sample_id"] is None


@pytest.mark.parametrize("roles", [[], ["vcf", "vcf"], ["unknown"], ["peaks_xls"], ["bam_header"]])
def test_lumpy_role_vocabulary_is_finite_and_does_not_accept_other_families(case, roles):
    with pytest.raises(ValueError): records.lumpy_role_outputs(case.request, roles)


def test_compact_capture_roles_resolve_only_the_original_plan(case):
    selector = dict(version=captures.LUMPY_SELECTOR_VERSION, output_roles=["bam_headers", "vcf"])
    selected = captures.resolve_lumpy_file_selector(selector, case.target, case.plan)
    assert selected == dict(version=captures.SELECTOR_VERSION, files=[
        dict(path=str(Path(case.plan["attempt_directory"]) / row["relative_path"]), format=row["format"])
        for row in records.lumpy_role_outputs(case.request, selector["output_roles"])])
    assert captures.is_file_source_selector(selector) and captures.is_lumpy_file_source_selector(selector)
    assert not captures.is_macs2_file_source_selector(selector)
    wrong = deepcopy(case.target); wrong["request_sha256"] = "f" * 64
    with pytest.raises(ValueError): captures.resolve_lumpy_file_selector(selector, wrong, case.plan)


@pytest.mark.parametrize("fault", ["arbitrary_file", "original_input", "private_control", "wrong_format"])
def test_even_literal_file_capture_cannot_escape_declared_lumpy_outputs(case, fault):
    owner = SimpleNamespace(resources={"local": case.configuration})
    reader = captures.LocalFileSourceResults.__new__(captures.LocalFileSourceResults); reader.owner = owner
    selected = dict(path=str(Path(case.plan["attempt_directory"]) / "native/result.vcf"), format="vcf")
    good = dict(version=captures.SELECTOR_VERSION, files=[deepcopy(selected)])
    assert reader._selector_paths(good, case.target, validate_paths=False) == good
    if fault == "arbitrary_file": selected["path"] = str(case.tmp_path / "unselected.vcf")
    elif fault == "original_input": selected["path"] = case.requested["native_lumpy"]["input_bindings"][0]["path"]
    elif fault == "private_control": selected["path"] = str(Path(case.identity["execution_id"]).parent / "invoke.json")
    else: selected["format"] = "sam_header_text"
    with pytest.raises(ValueError, match="lumpy_original_output_path_required"):
        reader._selector_paths(dict(version=captures.SELECTOR_VERSION, files=[selected]), case.target, validate_paths=False)


@pytest.mark.parametrize("field", ["run_id", "origin_episode_id", "original_operation_key", "attempt_id", "resource_id", "requested_job_sha256"])
def test_selected_observation_identity_is_checked_before_any_output_read(case, monkeypatch, field):
    host = operations.LocalPracticalOperations(case.configuration)
    monkeypatch.setattr(lumpy, "read_local_lumpy_plan", lambda *_: deepcopy(case.plan))
    expected = dict(run_id=case.run_id, origin_episode_id=case.episode_id, original_operation_key=case.key,
        attempt_id=case.identity["attempt_id"], resource_id="local", requested_job_sha256=case.identity["requested_job_sha256"])
    assert host._lumpy_plan(case.assignment, case.identity["execution_id"], **expected) == case.plan
    expected[field] = "wrong"
    monkeypatch.setattr(lumpy, "read_lumpy_output", forbidden)
    with pytest.raises(ValueError, match="native_lumpy_original_attempt_mismatch"):
        host.read_output(case.assignment, case.identity["execution_id"], path="unused", offset=0, limit=1, **expected)


@pytest.mark.parametrize("stage", ["prepared", "submitting", "released"])
def test_handle_dispatch_uses_only_selected_lumpy_preparer_and_same_handle(case, monkeypatch, stage):
    host = operations.LocalPracticalOperations(case.configuration)
    calls = []
    class Handle:
        path = Path(case.identity["execution_id"])
        def read(self): return dict(stage=stage)
    original = Handle()
    monkeypatch.setattr(host, "_action_directory", lambda *_: original.path.parent)
    monkeypatch.setattr(operations.native, "NativeJobHandle", lambda *_: original)
    def prepare(state, key, *, root, policy):
        calls.append((state, key, root, policy.to_dict())); return original
    monkeypatch.setattr(lumpy, "prepare_local_lumpy", prepare)
    monkeypatch.setattr(operations.native, "prepare_job", forbidden)
    monkeypatch.setattr(operations.native, "start_prepared", lambda handle: calls.append(("start", handle)))
    monkeypatch.setattr(operations.native, "resume_start", lambda handle: calls.append(("resume", handle)))
    state = object()
    assert host._handle(state, case.key, case.requested["argv"], cwd=case.tmp_path,
        env=case.requested["environment"], native_lumpy=True) is original
    assert calls[0] == (state, case.key, original.path.parent, lumpy.POLICY)
    assert calls[1:] == ([] if stage == "released" else [("start" if stage == "prepared" else "resume", original)])


def test_explicit_retry_cannot_replace_original_lumpy_handle(case, monkeypatch):
    host = operations.LocalPracticalOperations(case.configuration)
    original = SimpleNamespace(path=Path(case.identity["execution_id"]))
    monkeypatch.setattr(host, "_job_handle", lambda *_: original)
    monkeypatch.setattr(host, "_handle", forbidden)
    monkeypatch.setattr(lumpy, "read_local_lumpy_plan", lambda *_: deepcopy(case.plan))
    monkeypatch.setattr(host, "_lumpy_controls", lambda plan: dict(native_lumpy_plan=deepcopy(plan)))
    view = dict(terminal=False, quiescent=True, state="unknown", metadata=dict(native_returncode=None))
    monkeypatch.setattr(operations.native, "status", lambda handle: deepcopy(view))
    state = SimpleNamespace(assignment=case.assignment, run_id=case.run_id, episode_id=case.episode_id,
        context=lambda: deepcopy(case.assignment["initial_context"]))
    outcome, updated = host._execute(state, "practical.job.start",
        dict(retry_failed_execution_id=str(original.path)), case.key + "-unselected-replacement")
    assert updated is None and outcome["facts"]["requested_job"]["execution_id"] == str(original.path)
    assert outcome["native_outcome"]["failure"] == dict(code="native_lumpy_original_attempt_required")
    assert outcome["native_outcome"]["attempt_operation_key"] == case.key


def test_capture_origin_labels_stay_qualified_and_old_generic_selector_stays_literal():
    assert captures.ORIGIN == dict(content_location="current_resource_filesystem", attempt_output_version="unverified",
        read_consistency="pinned_regular_file_stream_not_atomic_snapshot", writer_closure="not_established")
    value = dict(version=captures.SELECTOR_VERSION, files=[dict(path="/literal/output", format="vcf")])
    assert Draft202012Validator(captures.SELECTOR_SCHEMA).is_valid(value)
    assert captures.is_file_source_selector(value) and not captures.is_lumpy_file_source_selector(value)


def test_only_lumpy_catalog_removes_the_unavailable_replacement_retry(case):
    from gene_annotation_episode.practical_resource_episodes import operation_catalog
    original = operation_catalog("local")
    owner = ExecutionEpisodes.__new__(ExecutionEpisodes)
    inactive = SimpleNamespace(applies=lambda *_: False)
    for name in ("native_blast_masking_results", "native_blast_utility_results",
            "native_fluorescence_results", "native_protein_structure_results"):
        setattr(owner, name, inactive)
    for name in ("native_flux_balance_results", "native_expression_nmf_results", "atac_results",
            "native_chromatin_interaction_results", "native_genomic_overlap_results"):
        setattr(owner, name, None)
    owner._practical_context = lambda context: context
    owner._delegate = lambda _: SimpleNamespace(catalog=lambda _: original)
    context = SimpleNamespace(role="launch_local", assignment=deepcopy(case.assignment))
    selected = owner.catalog(context)
    start = next(row for row in selected if row["name"] == "practical.job.start")
    assert start["input_schema"] == dict(type="object", properties={}, required=[], additionalProperties=False)
    assert "original selected LUMPY job once" in start["description"]
    assert all(row == prior for row, prior in zip(selected, original) if row["name"] != "practical.job.start")
    assert "anyOf" in next(row for row in original if row["name"] == "practical.job.start")["input_schema"]
    generic = deepcopy(case.assignment); generic["requested_job"] = dict(argv=["literal"], environment={})
    assert owner.catalog(SimpleNamespace(role="launch_local", assignment=generic)) is original


def test_repeated_output_roles_across_requirements_preserve_each_predicate(case, monkeypatch):
    """An engineered unknown observation retains two independent requirements."""
    assignment = deepcopy(case.assignment)
    repeated = deepcopy(assignment["progress_requirements"][0])
    repeated.update(key="outputs-again", credit=2)
    assignment["progress_requirements"].append(repeated)
    assignment["completion_keys"].append(repeated["key"])
    identity = {**case.identity, "assignment_sha256": records.digest(assignment)}
    plan = lumpy.lumpy_plan(assignment, identity, policy=lumpy.POLICY)
    host = operations.LocalPracticalOperations(case.configuration)
    handle = SimpleNamespace(path=Path(identity["execution_id"]), read=lambda: {})
    view = dict(terminal=False, quiescent=True, state="unknown", metadata=dict(native_returncode=None))
    state = SimpleNamespace(assignment=assignment, run_id=case.run_id, episode_id=case.episode_id,
        context=lambda: deepcopy(assignment["initial_context"]))
    monkeypatch.setattr(host, "_job_handle", lambda *_: handle)
    monkeypatch.setattr(lumpy, "read_local_lumpy_plan", lambda *_: deepcopy(plan))
    monkeypatch.setattr(host, "_lumpy_controls", lambda selected: dict(native_lumpy_plan=deepcopy(selected)))
    monkeypatch.setattr(operations.native, "status", lambda selected: deepcopy(view))
    monkeypatch.setattr(lumpy, "lumpy_observed_files", lambda *_, **__: ([], [], False))
    monkeypatch.setattr(operations.native, "prepare_job", forbidden)
    monkeypatch.setattr(host, "_handle", forbidden)
    outcome, updated = host._execute(state, "practical.job.status", {}, case.key + "-observation")
    paths = records.requested_job_role_paths(assignment, outcome["facts"]["requested_job"],
        repeated["predicate"]["output_roles"])
    assert updated is None and outcome["facts"]["requested_job"]["status"] == "unknown"
    assert [row["path"] for row in outcome["facts"]["paths"]] == sorted(set(paths))
    initial = host.initial_outcome(assignment, lumpy_output_paths=paths + paths)
    assert initial["facts"]["paths"] == outcome["facts"]["paths"]
    validations = records.assess_validations(assignment, outcome, assignment["initial_context"],
        tool_name="practical.job.status")
    assert [row["key"] for row in validations] == ["outputs", "outputs-again"]
    assert all(row["satisfied"] is False for row in validations)
    assert validations[0]["predicate"] == validations[1]["predicate"] == repeated["predicate"]
    assert [row["credit"] for row in assignment["progress_requirements"]] == [1, 2]


def test_failed_original_handoff_retains_present_partial_output_without_success(case, monkeypatch):
    """Engineered receipt-reader boundary; actual partial bytes, no native call."""
    reader = ExecutionTargetReader.__new__(ExecutionTargetReader)
    reader.run_id = case.run_id
    status = {"value": "failed"}
    calls = []
    def original_target(handle, scope):
        assert handle == case.target["handle"] and scope == case.target["scope"]
        return deepcopy(case.target)
    def original_native(handle, scope):
        original_target(handle, scope)
        calls.append(handle)
        return deepcopy(case.target), dict(receipt=dict(outcome=dict(facts=dict(
            requested_job=dict(status=status["value"])))))
    monkeypatch.setattr(reader, "read_target", original_target)
    monkeypatch.setattr(reader, "_native", original_native)
    monkeypatch.setattr(operations.native, "prepare_job", forbidden)
    monkeypatch.setattr(operations.native, "start_prepared", forbidden)
    monkeypatch.setattr(operations.native, "resume_start", forbidden)
    assert reader.usable_handoff(case.target) is False
    assert reader.returnable_handoff(case.target) is True
    selector = dict(version=captures.LUMPY_SELECTOR_VERSION, output_roles=["vcf"])
    resolved = captures.resolve_lumpy_file_selector(selector, case.target, case.plan)
    path = Path(resolved["files"][0]["path"])
    path.parent.mkdir(parents=True)
    partial = b"##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\nengineered\t"
    path.write_bytes(partial)
    observation = dict(terminal=True, quiescent=True, state="returned",
        metadata=dict(native_returncode=2))
    outputs, logs, result_available = lumpy.lumpy_observed_files(case.plan, observation,
        log_window_bytes=128, log_roles=())
    output, = [row for row in outputs if row["role"] == "vcf"]
    assert output == dict(role="vcf", available=True, bytes=len(partial), writer_closed=True)
    assert logs == [] and result_available is False
    retained = lumpy.read_lumpy_output(case.plan, path=str(path), offset=0, limit=128)
    assert base64.b64decode(retained["bytes_base64"]) == partial
    assert status["value"] == "failed" and observation["metadata"]["native_returncode"] == 2
    status["value"] = "unknown"
    assert reader.returnable_handoff(case.target) is False
    changed = {**case.target, "request_sha256": "e" * 64}
    count = len(calls)
    with pytest.raises(ContractError, match="execution_target_identity_conflict"):
        reader.returnable_handoff(changed)
    assert len(calls) == count
