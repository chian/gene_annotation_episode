"""Ordinary protease actions over admitted numeric Files and retained values.

The existing private driver owns the native observation and the existing
calculator owns all derived numbers. These controls bind that work to one
actual ordinary action; driver identity strings alone confer no custody.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re

from . import molecular_sequence_driver as driver
from . import molecular_sequence_native as native
from . import molecular_sequence_result_contracts as stored
from . import protease_kinetics_measurements as measurements
from . import protease_kinetics_result_contracts as contracts
from . import native_lifecycle
from .alignment_site_native import immutable_record
from .communication import plain
from .domain import ContractError, identity
from .episode_receipts import EpisodeReceipts
from .episode_return_records import EpisodeReturnRecords
from .execution_contracts import canonical, digest
from .flux_balance_tools import _action_lock
from .local_jobs import LocalJobPolicy
from .materials import source_window_selection
from .molecular_measurement_tools import (
    MolecularOperationUnpublished, _publication_bytes, _recorded_molecular_action_details,
    _recorded_molecular_producer_details, authenticate_molecular_invocation,
    retain_molecular_publication,
)
from .molecular_sequence_input_contracts import (
    decode_molecular_sequence_input, input_record_digest, validate_molecular_sequence_received_file,
)
from .native_atac_differential_driver import _directory, _immutable, _regular, _writing, decode_json
from .native_file_capture import _identity, _metadata, capture_native_file
from .reference_edit_outcome_tools import _context, _invocation


TOOL = contracts.TOOL
SOURCE_VERSION = contracts.SOURCE_VERSION
PACKET_VERSION = contracts.PACKET_VERSION
FACT_SOURCE = contracts.FACT_SOURCE
CONFIGURATION_VERSION = "ordinary_protease_kinetics_configuration_v1"
INTENT_VERSION = "ordinary_protease_kinetics_intent_v1"
CONTROL_VERSION = "ordinary_protease_kinetics_publication_v1"
_ROLES = stored.FILE_ROLES
_CONTROL_FIELDS = ("version arguments invocation intent worker files projection packet_ref "
    "protected_input_artifact_refs")


def _require(condition, code):
    if not condition:
        raise ContractError("protease_kinetics_" + code)


def _copy(value):
    return json.loads(canonical(value))


def _same(left, right):
    return canonical(left) == canonical(right)


def _closed(value, fields):
    _require(type(value) is dict and set(value) == set(fields.split()), "closed_fields_required")


def _arguments(value):
    return contracts.validate_ordinary_protease_kinetics_arguments(_copy(value))


def normalize_protease_kinetics_configuration(resources, environments, *, policy):
    """Select one explicit host deployment; validation performs no discovery."""
    resources, environments = _copy(resources), _copy(environments)
    checked = LocalJobPolicy(**policy).to_dict()
    _require(type(resources) is dict and type(environments) is list and _same(checked, policy), "configuration_invalid")
    selected = []
    for entry in environments:
        _closed(entry, "operation resource_id binding_ordinal_0based")
        name, ordinal = entry["resource_id"], entry["binding_ordinal_0based"]
        _require(entry["operation"] == TOOL and not selected and type(name) is str and bool(name)
            and type(ordinal) is int and ordinal >= 0, "binding_selection_invalid")
        resource = resources.get(name)
        _require(type(resource) is dict and resource.get("kind") == "local"
            and _same(resource.get("policy"), checked), "resource_allocation_conflict")
        _directory(resource["workspace"])
        bindings = resource.get("native_protease_kinetics")
        _require(type(bindings) is list and ordinal < len(bindings), "binding_selection_invalid")
        binding = bindings[ordinal]
        _closed(binding, "operation deployment")
        _require(binding["operation"] == TOOL, "binding_selection_invalid")
        native._deployment(binding["deployment"], version=native.DEPLOYMENT_VERSION_V3,
            source_sha256=native.BIOCHEMISTRY_SOURCE_SHA256)
        selected.append(dict(resource_id=name, resource=resource, binding_ordinal_0based=ordinal,
            deployment=binding["deployment"]))
    return dict(version=CONFIGURATION_VERSION, policy=checked, resources=selected, saved_modes=False)


def _configuration(value):
    value = _copy(value)
    _closed(value, "version policy resources saved_modes")
    _require(value["version"] == CONFIGURATION_VERSION and type(value["saved_modes"]) is bool
        and type(value["resources"]) is list and len(value["resources"]) <= 1, "configuration_invalid")
    for selected in value["resources"]:
        _closed(selected, "resource_id resource binding_ordinal_0based deployment")
        normalized = normalize_protease_kinetics_configuration({selected["resource_id"]: selected["resource"]},
            [dict(operation=TOOL, resource_id=selected["resource_id"],
                binding_ordinal_0based=selected["binding_ordinal_0based"])], policy=value["policy"])
        _require(_same(normalized["resources"], value["resources"]), "configuration_invalid")
    _require(_same(LocalJobPolicy(**value["policy"]).to_dict(), value["policy"]), "policy_invalid")
    return value


def protease_kinetics_tool_contract(configuration=None):
    if configuration is not None:
        _configuration(configuration)
    return dict(resources="local", invocation_route=dict(kind="direct"),
        input_schema=deepcopy(contracts.ARGUMENT_SCHEMA),
        description="Analyze an admitted numeric protease assay or select qualified values from its retained numerical Sheet.",
        instructions=("Use run_native with an explicitly received JSON File containing protease_kinetics_input_v1, "
            "its measurements and assay_context. Native fitted signal quantities and physically calibrated quantities "
            "have separate meanings and uncertainty qualifications. calculate_saved uses an explicitly received Sheet "
            "or an ordinary result Source, preserving that Sheet's measurements and calibration without another fit. "
            "read_stored selects literal retained numerical values without calculation. Select rows explicitly; empty "
            "rows still preserve the assay and population context. Only the actual result Source is delivered; nested "
            "File identities are provenance and grant no File access. Supplied historical Sheets do not establish "
            "original ordinary native custody."))


def protease_kinetics_fact_sources():
    return contracts.ordinary_protease_kinetics_fact_sources()


def _file(registry, value):
    value = _identity(value)
    metadata = _metadata(registry.store, value["artifact_ref"])
    _require((metadata["sha256"], metadata["size"]) == (value["sha256"], value["size_bytes"]), "file_identity_conflict")
    return value


def _cutoff(registry, context):
    active = registry._current_invocation.get()
    if active is not None and active[0] is context:
        return _invocation(context, active[4])["decision_index"]
    return registry.store.db.execute("SELECT coalesce(max(decision_index),-1)+1 FROM runtime_actions "
        "WHERE run_id=? AND episode_id=?", (context.run_id, context.episode_id)).fetchone()[0]


def _source_admission(registry, context, reader, source_ref, cutoff):
    admitted = reader(context, source_ref, "source", source_metadata_only=True)
    _require(type(admitted) is dict and admitted.get("failure") is None
        and admitted.get("selection") == dict(reference=source_ref, namespace="source"), "source_not_received")
    records = EpisodeReturnRecords(registry.store, context.run_id, failure_prefix="protease_kinetics_")
    records.authenticate(context)
    return records.source_admission_before(context, source_ref, cutoff)


def _input_admission(registry, context, selected, cutoff):
    record = registry.store.get(selected["reference"])
    _require(record.get("record_type") == selected["namespace"], "input_namespace_conflict")
    if selected["namespace"] == "source":
        immutable_record(record)
        artifact, representation, _ = source_window_selection(record, "original")
        _require(representation == "original" and type(artifact) is str, "original_file_required")
    else:
        artifact = selected["reference"]
    _metadata(registry.store, artifact)
    records = EpisodeReturnRecords(registry.store, context.run_id, failure_prefix="protease_kinetics_")
    records.authenticate(context)
    return artifact, records.file_admission_before(context, selected["reference"], selected["namespace"], artifact, cutoff)


def _received_file(registry, context, received, selected, cutoff):
    received = validate_molecular_sequence_received_file(received)
    _require(received["failure"] is None and received["selection"] == selected and received["input"] is not None,
        "file_not_received")
    item = received["input"]
    records = EpisodeReturnRecords(registry.store, context.run_id, failure_prefix="protease_kinetics_")
    records.authenticate(context)
    manifest = EpisodeReceipts.read_manifest(registry.store.db, context.run_id, context.episode_id)
    _require(item["receiver"] == dict(run_id=context.run_id, episode_id=context.episode_id,
        request_sha256=input_record_digest(plain(context.request)), assignment_sha256=input_record_digest(plain(context.assignment)))
        and _same(item["scope"], registry.store.validate_scope(plain(context.scope)))
        and _same(item["inheritance_manifest"], manifest)
        and _same(plain(context.request)["message"].get("knowledge_inheritance"), manifest)
        and _same(item["witness"]["record"], registry.store.get(selected["reference"]))
        and records._received_before(context.episode_id, selected["reference"], cutoff)
        and records._received_before(context.episode_id, item["file"]["artifact_ref"], cutoff), "input_admission_conflict")
    _file(registry, item["file"])
    _require(item["file"]["format"] == "json" and item["byte_verification"] == "verified", "input_identity_conflict")
    return received


def _write_bytes(path, raw):
    if path.exists():
        with _regular(path) as stream:
            _require(stream.read() == raw, "frozen_input_conflict")
    else:
        with _writing(path) as stream:
            stream.write(raw)
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))


def _fresh_input(registry, context, reader, arguments, invocation, directory):
    selected, cutoff = arguments["input"], invocation["decision_index"]
    if selected["namespace"] == "source":
        _source_admission(registry, context, reader, selected["reference"], cutoff)
    artifact, admission = _input_admission(registry, context, selected, cutoff)
    received, path = reader(context, selected["reference"], selected["namespace"], file_format="json")
    received = _received_file(registry, context, received, selected, cutoff)
    file = received["input"]["file"]
    _require(file["artifact_ref"] == artifact and path is not None, "input_identity_conflict")
    with _regular(path) as stream:
        raw = stream.read(file["size_bytes"] + 1)
    _require(len(raw) == file["size_bytes"] and hashlib.sha256(raw).hexdigest() == file["sha256"], "input_identity_conflict")
    decoded = decode_molecular_sequence_input(raw, tag_key="schema")
    _require(decoded["failure"] is None and decoded["state"] == "decoded", "input_json_invalid")
    document = (contracts.validate_ordinary_protease_kinetics_input(decoded["value"]) if arguments["mode"] == "run_native"
        else measurements.validate_protease_kinetics_sheet(decoded["value"]))
    return dict(received=received, admission=admission, document=document,
        frozen=_write_bytes(directory / "input.json", raw), raw_utf8=raw.decode("utf-8"), protected_input_artifact_refs=[artifact],
        sheet_ref=artifact if arguments["mode"] == "calculate_saved" else None)


def _input_document(arguments, input):
    raw = input["raw_utf8"].encode("utf-8")
    _require(hashlib.sha256(raw).hexdigest() == input["frozen"]["sha256"]
        and len(raw) == input["frozen"]["size_bytes"], "frozen_input_identity_conflict")
    decoded = decode_molecular_sequence_input(raw, tag_key="schema")
    _require(decoded["failure"] is None and _same(decoded["value"], input["document"]), "input_document_conflict")
    if arguments["mode"] == "run_native":
        return contracts.validate_ordinary_protease_kinetics_input(input["document"])
    return measurements.validate_protease_kinetics_sheet(input["document"])


def _check_input(registry, context, arguments, invocation, input, *, producer_directory=None):
    _closed(input, "received admission document frozen raw_utf8 protected_input_artifact_refs sheet_ref")
    selected = arguments["input"]
    received = _received_file(registry, context, input["received"], selected, invocation["decision_index"])
    artifact, admission = _input_admission(registry, context, selected, invocation["decision_index"])
    input_directory = registry.store.path / "cache" / "molecular-measurements" / digest(invocation["operation_key"])
    if producer_directory is not None:
        supplied = str(producer_directory)
        original = Path(supplied)
        _require(original.is_absolute() and str(original) == supplied and ".." not in original.parts
            and original.parts[-4:] == ("cache", "molecular-measurements", digest(invocation["operation_key"]), "worker"),
            "worker_directory_conflict")
        input_directory = original.parent
    _require(input["frozen"]["path"] == str(input_directory / "input.json")
        and input["sheet_ref"] == (artifact if arguments["mode"] == "calculate_saved" else None)
        and _same(admission, input["admission"]) and input["protected_input_artifact_refs"] == [artifact]
        and input["frozen"]["sha256"] == received["input"]["file"]["sha256"]
        and input["frozen"]["size_bytes"] == received["input"]["file"]["size_bytes"], "input_admission_conflict")
    _input_document(arguments, input)
    return input


def _request(invocation, arguments, input, selected, worker):
    """Build the exact existing driver request; no practical assignment exists."""
    attempt = dict(run_id=invocation["run_id"], episode_id=invocation["episode_id"],
        resource_id=selected["resource_id"] if selected is not None else "ordinary_saved_calculation",
        operation_key=invocation["operation_key"], execution_id=str(worker / "native-handle.json"))
    if arguments["mode"] == "run_native":
        workspace = worker / "driver-output"
        document = input["document"]
        selection = dict(version=native.REQUEST_VERSION_V3, operation=TOOL,
            arguments=dict(**deepcopy(document["measurements"]), output_prefix="protease", output_dir=str(workspace / "native")),
            deployment=deepcopy(selected["deployment"]), output_workspace=str(workspace),
            environment=dict(MPLBACKEND="Agg", MPLCONFIGDIR=str(workspace / "matplotlib"), XDG_CACHE_HOME=str(workspace / "cache")))
        measurements._native_request(selection)
        context = dict(assay_context=deepcopy(document["assay_context"]))
    else:
        selection, context = dict(operation=TOOL, sheet_file=deepcopy(input["frozen"])), None
    value = dict(version=driver.REQUEST_VERSION_V2, mode="native" if arguments["mode"] == "run_native" else "saved_sheet",
        attempt_identity=attempt, selection=selection, scientific_context=context)
    _require(driver._request(value) == TOOL, "driver_request_conflict")
    return value


def _command(request, directory, python):
    raw = json.dumps(_copy(request), allow_nan=False).encode("utf-8")
    return [python, "-B", "-m", "gene_annotation_episode.molecular_sequence_driver", "--request-file",
        str(directory / "worker-request.json"), "--request-sha256", hashlib.sha256(raw).hexdigest(),
        "--request-size-bytes", str(len(raw)), "--output-directory", str(directory / "driver-output")]


def _validate_intent(intent):
    _closed(intent, "version arguments invocation policy selected_resource input original_source source_admission request worker_operation")
    arguments = _arguments(intent["arguments"])
    _require(intent["version"] == INTENT_VERSION and arguments["mode"] in ("run_native", "calculate_saved")
        and intent["worker_operation"] == ("protease_kinetics_native" if arguments["mode"] == "run_native"
            else "protease_kinetics_saved")
        and _same(LocalJobPolicy(**intent["policy"]).to_dict(), intent["policy"]), "original_intent_conflict")
    selected = intent["selected_resource"]
    if arguments["mode"] == "run_native":
        _closed(selected, "resource_id resource binding_ordinal_0based deployment")
        normalized = normalize_protease_kinetics_configuration({selected["resource_id"]: selected["resource"]},
            [dict(operation=TOOL, resource_id=selected["resource_id"],
                binding_ordinal_0based=selected["binding_ordinal_0based"])], policy=intent["policy"])
        _require(normalized["resources"] == [selected], "original_resource_conflict")
    else:
        _require(selected is None, "saved_resource_conflict")
    _input_document(arguments, intent["input"])
    return intent


def _dispatch(registry, owner, intent, directory):
    _validate_intent(intent)
    path = directory / "execution-selection.json"
    policy, selected = intent["policy"], intent["selected_resource"]
    _require(_same(LocalJobPolicy(**policy).to_dict(), policy), "policy_invalid")
    if path.exists():
        execution = decode_json(path.read_bytes())
        _require(execution["version"] == "ordinary_molecular_execution_v1"
            and _same(execution["policy"], policy)
            and _same(execution["request"], dict(operation=intent["worker_operation"], arguments=dict(request=intent["request"])))
            and execution["command"] == _command(intent["request"], directory, execution["python"]["path"])
            and execution["cwd"] == str(directory), "original_worker_selection_conflict")
    else:
        configured = _configuration(registry._protease_kinetics_configuration)
        _require(_same(configured["policy"], policy)
            and (selected in configured["resources"] if selected is not None else configured["saved_modes"]),
            "original_unstarted_configuration_conflict")
        with _regular(intent["input"]["frozen"]["path"]) as stream:
            _require(stream.read() == intent["input"]["raw_utf8"].encode("utf-8"), "frozen_input_identity_conflict")
        _require(_same(registry.local_job_policy.to_dict(), policy), "resource_allocation_conflict")
        if selected is not None:
            _require(_same(owner.resources.get(selected["resource_id"]), selected["resource"])
                and _same(selected["resource"].get("policy"), policy), "resource_allocation_conflict")


def _worker_control(record, request, operation, directory, policy):
    _closed(record, "selection handle observation native_request native_request_raw declaration declaration_hex")
    selected, handle, observation = record["selection"], record["handle"], record["observation"]
    _closed(selected, "version command cwd environment policy request python implementation_files")
    _require(selected["version"] == "ordinary_molecular_execution_v1"
        and _same(selected["request"], dict(operation=operation, arguments=dict(request=request)))
        and selected["command"] == _command(request, directory, selected["python"]["path"])
        and selected["cwd"] == handle["cwd"] == str(directory) and handle["command"] == selected["command"]
        and handle["stdout"] == str(directory / "stdout") and handle["stderr"] == str(directory / "stderr")
        and _same(selected["policy"], policy) and _same(handle["metadata"]["policy"], policy)
        and _same(observation["metadata"]["policy"], policy)
        and observation["terminal"] is True and observation["quiescent"] is True, "worker_control_conflict")
    paths = handle["paths"]
    _require(all(type(path) is str and Path(path).parent == directory for path in paths.values()), "worker_handle_conflict")
    raw = record["native_request_raw"]
    _require(type(raw) is str and hashlib.sha256(raw.encode()).hexdigest() == handle["request_sha256"]
        and _same(decode_json(raw.encode()), record["native_request"])
        and _same(record["native_request"], dict(command=selected["command"], cwd=str(directory),
            file_bytes=policy["scratch_bytes"], ready_path=paths["ready"], release_path=paths["release"],
            result_path=paths["result"], stdin_path=None, env=selected["environment"])), "worker_handle_conflict")
    if operation == "protease_kinetics_native":
        deployment = request["selection"]["deployment"]
        _require(selected["python"] == {key: deployment["runtime"]["executable"][key] for key in ("path", "sha256")}
            and selected["environment"] == dict(PYTHONHOME=deployment["runtime"]["home"],
                PYTHONPATH=os.pathsep.join(deployment["import_roots"]), PYTHONDONTWRITEBYTECODE="1",
                PYTHONNOUSERSITE="1", PYTHONSAFEPATH="1", TMPDIR=str(directory / "temporary"),
                TMP=str(directory / "temporary"), TEMP=str(directory / "temporary"), **request["selection"]["environment"]),
            "worker_runtime_conflict")
    declaration = record["declaration"]
    encoded = record["declaration_hex"]
    _require(encoded is None or type(encoded) is str and re.fullmatch(r"(?:[0-9a-f]{2})*", encoded) is not None,
        "driver_declaration_bytes_conflict")
    if declaration is not None:
        _require(encoded is not None and _same(decode_json(bytes.fromhex(encoded)), declaration),
            "driver_declaration_bytes_conflict")
        _require(declaration["version"] == driver.DECLARATION_VERSION_V2
            and declaration["mode"] == request["mode"] and declaration["operation"] == TOOL
            and _same(declaration["attempt_identity"], request["attempt_identity"])
            and declaration["request_file_pin_verified"] is True
            and declaration["request_file"] == dict(path=str(directory / "worker-request.json"),
                sha256=hashlib.sha256(json.dumps(_copy(request), allow_nan=False).encode()).hexdigest(),
                size_bytes=len(json.dumps(_copy(request), allow_nan=False).encode())), "driver_declaration_conflict")
    return record


def _worker_record(work, intent, directory):
    _require(Path(work.output_path) == directory / "driver-output" / "declaration.json", "worker_output_conflict")
    handle = native_lifecycle.NativeJobHandle(directory / "native-handle.json")
    observation = native_lifecycle.status(handle)
    if not (observation["terminal"] and observation["quiescent"]):
        raise MolecularOperationUnpublished("protease_kinetics_worker_attempt_unconfirmed")
    _require(_same({key: value for key, value in work.metadata.items() if key != "molecular_failure"},
        observation["metadata"]), "worker_metadata_conflict")
    original = handle.read()
    with _regular(original["paths"]["request"]) as stream:
        raw = stream.read()
    declaration, declaration_raw = None, None
    if Path(work.output_path).is_file():
        with _regular(work.output_path) as stream:
            declaration_raw = stream.read()
        try:
            declaration = decode_json(declaration_raw)
        except (ValueError, UnicodeError):
            pass
    record = dict(selection=decode_json((directory / "execution-selection.json").read_bytes()),
        handle=original, observation=observation, native_request=decode_json(raw), native_request_raw=raw.decode(), declaration=declaration,
        declaration_hex=None if declaration_raw is None else declaration_raw.hex())
    with _regular(directory / "worker-request.json") as stream:
        _require(stream.read() == json.dumps(_copy(intent["request"]), allow_nan=False).encode(), "worker_request_conflict")
    return _worker_control(record, intent["request"], intent["worker_operation"], directory, intent["policy"])


def _absent(role, state="producer_unavailable", declaration=None, issue=None):
    return stored.validate_file_state(dict(state=state, file=None, declared=declaration,
        observed_identity=None, failure=issue))


def _retained(file, declaration=None):
    return stored.validate_file_state(dict(state="retained" if declaration is not None else "retained_undeclared",
        file=file, declared=declaration, observed_identity={key: file[key] for key in ("sha256", "size_bytes")}, failure=None))


def _capture_outputs(registry, intent, worker, directory):
    files, failures, documents = {}, [], {}
    declaration = worker["declaration"]
    declared = {} if declaration is None else declaration["files"]
    if declaration is None:
        failures.append(stored.failure("declaration_unavailable", "worker"))
    for role in _ROLES:
        requested = intent["request"]["mode"] == "native" or role in ("sheet", "components")
        spec = declared.get(role)
        if spec is None and not requested:
            files[role] = _absent(role, "not_requested")
            continue
        expected = (role + ".json" if role in ("capture", "sheet", "components") else
            "native/protease" + ("_results.txt" if role == "native_results" else "_mm_plot.png"))
        format_name = "json" if role in ("capture", "sheet", "components") else "text" if role == "native_results" else "png"
        if spec is not None:
            stored.file_declaration(spec)
            _require(spec["relative_path"] == expected and spec["format"] == format_name, "output_declaration_conflict")
            if spec["state"] == "absent":
                files[role] = _absent(role, "producer_absent", spec)
                continue
        try:
            file = capture_native_file(registry.store, directory=str(directory / "driver-output"),
                relative_path=expected, format=format_name,
                media_type="application/json" if role in ("capture", "sheet", "components") else
                    "image/png" if role == "native_plot" else "text/plain")
            if spec is not None:
                _require((file["sha256"], file["size_bytes"]) == (spec["sha256"], spec["size_bytes"]), "output_identity_conflict")
            files[role] = _retained(file, spec)
        except (OSError, ValueError, ContractError):
            issue = stored.failure("retention_failed" if spec is not None else "producer_unavailable", "capture", role=role)
            failures.append(issue)
            files[role] = _absent(role, "retention_failed" if spec is not None else "producer_unavailable", spec, issue)
            continue
        if role in ("capture", "sheet", "components"):
            try:
                document = decode_json(_publication_bytes(registry.store, file["artifact_ref"]))
                if role == "capture":
                    driver._native_capture(document, intent["request"]["selection"])
                elif role == "sheet":
                    document = measurements.validate_protease_kinetics_sheet(document)
                    if intent["request"]["mode"] == "native":
                        _require(_same(document["measurements"], intent["input"]["document"]["measurements"])
                            and _same(document["assay_context"], measurements._context(intent["input"]["document"]["assay_context"])),
                            "sheet_input_conflict")
                    else:
                        _require(_same(document, intent["input"]["document"]), "saved_sheet_conflict")
                else:
                    _require(type(document) is dict and document.get("schema") == measurements.COMPONENTS_SCHEMA
                        and document.get("sheet_schema") == measurements.SHEET_SCHEMA, "components_schema_conflict")
                documents[role] = document
            except (ValueError, TypeError, KeyError, ContractError):
                failures.append(stored.failure("schema_invalid", "load", role=role, source_ref=file["artifact_ref"]))
    if worker["observation"]["metadata"].get("native_returncode") != 0:
        failures.append(stored.failure("worker_failed", "worker"))
    return files, documents, failures


def _projection(arguments, files, sheet, components, *, saved_sheet_ref=None):
    selection = contracts.ordinary_protease_kinetics_selector(arguments,
        saved_sheet_ref=saved_sheet_ref if arguments["mode"] == "calculate_saved" else None)
    return stored.validate_molecular_sequence_projection(stored.select_stored_molecular_sequence_values(
        operation=TOOL, sheet=sheet, components=components, selection=selection, source_files=files))


def _packet(arguments, projection, failures):
    return contracts.ordinary_protease_kinetics_packet(projection=projection, arguments=arguments,
        file_states={role: projection["source_files"][role]["state"] for role in contracts.FILE_ROLES}, failures=failures)


def _metadata_publication(registry, source_ref, *, recovery_context=None, recovery_operation_key=None):
    source = registry.store.get(source_ref)
    immutable_record(source)
    _require(source.get("record_type") == "source" and source.get("origin") == "tool"
        and source.get("provider") == TOOL and source.get("version") == SOURCE_VERSION and "operand_refs" not in source,
        "producer_required")
    producer = _recorded_molecular_producer_details(registry, source_ref, TOOL,
        recovery_context=recovery_context, recovery_operation_key=recovery_operation_key)
    arguments = _arguments(producer["arguments"])
    public = contracts.validate_ordinary_protease_kinetics_return(producer["outcome"]["result"])
    _require(arguments["mode"] in ("run_native", "calculate_saved") and public["source_ref"] == source_ref
        and producer["outcome"]["record_refs"] == [source_ref] and public["selection"] == dict(rows=arguments["rows"]),
        "publication_conflict")
    parents = ([arguments["result_ref"]] if "result_ref" in arguments else
        [arguments["input"]["reference"]] if arguments["input"]["namespace"] == "source" else [])
    _require(source.get("parent_source_refs") == parents, "parent_sources_conflict")
    return dict(source=source, producer=producer, public=public)


def _control(registry, publication, seen=()):
    source, producer = publication["source"], publication["producer"]
    _require(source["id"] not in seen, "source_lineage_cycle")
    seen = (*seen, source["id"])
    control = decode_json(_publication_bytes(registry.store, source["request_ref"]))
    _closed(control, _CONTROL_FIELDS)
    intent = control["intent"]
    _validate_intent(intent)
    _require(control["version"] == CONTROL_VERSION and intent["version"] == INTENT_VERSION
        and _same(control["arguments"], producer["arguments"]) and _same(intent["arguments"], control["arguments"])
        and _same(control["invocation"], producer["invocation"]) and _same(intent["invocation"], control["invocation"])
        and control["packet_ref"] == source["artifact_ref"], "publication_control_conflict")
    invocation, arguments = control["invocation"], _arguments(control["arguments"])
    context = _context(registry.store, invocation)
    directory = Path(control["worker"]["selection"]["cwd"])
    _require(directory.name == "worker" and directory.parent.name == digest(invocation["operation_key"])
        and directory.parent.parent.name == "molecular-measurements" and directory.parent.parent.parent.name == "cache",
        "worker_directory_conflict")
    _require(_same(intent["request"], _request(invocation, arguments, intent["input"], intent["selected_resource"], directory)),
        "driver_request_conflict")
    _worker_control(control["worker"], intent["request"], intent["worker_operation"], directory, intent["policy"])
    _input_document(arguments, intent["input"])
    if "input" in arguments:
        _check_input(registry, context, arguments, invocation, intent["input"], producer_directory=directory)
        _require(intent["source_admission"] is intent["original_source"] is None, "input_lineage_conflict")
    else:
        original = intent["original_source"]
        _closed(original, "source_ref record_sha256")
        _require(original["source_ref"] == arguments["result_ref"]
            and digest(registry.store.get(original["source_ref"])) == original["record_sha256"], "original_source_conflict")
        records = EpisodeReturnRecords(registry.store, context.run_id, failure_prefix="protease_kinetics_")
        _require(_same(records.source_admission_before(context, original["source_ref"], invocation["decision_index"]),
            intent["source_admission"]), "source_admission_conflict")
        parent = _control(registry, _metadata_publication(registry, original["source_ref"]), seen)
        parent_sheet = parent["files"]["sheet"]["file"]
        _require(parent_sheet is not None and intent["input"]["sheet_ref"] == parent_sheet["artifact_ref"]
            and all(intent["input"]["frozen"][key] == parent_sheet[key] for key in ("sha256", "size_bytes"))
            and intent["input"]["protected_input_artifact_refs"] == parent["protected_input_artifact_refs"],
            "saved_sheet_identity_conflict")
    _closed(control["files"], "sheet components capture native_results native_plot")
    for role, state in control["files"].items():
        stored.validate_file_state(state)
        if state["file"] is not None:
            _file(registry, state["file"])
    projection = stored.validate_molecular_sequence_projection(control["projection"])
    _require(_same(projection["source_files"], control["files"])
        and _same(_packet(arguments, projection, publication["public"]["failures"]),
            {key: value for key, value in publication["public"].items() if key != "source_ref"}), "projection_conflict")
    protected = intent["input"]["protected_input_artifact_refs"]
    _require(control["protected_input_artifact_refs"] == protected, "protected_inputs_conflict")
    expected = list(dict.fromkeys(control["files"][role]["file"]["artifact_ref"] for role in _ROLES
        if control["files"][role]["file"] is not None and control["files"][role]["file"]["artifact_ref"] not in protected))
    _require(source.get("auxiliary_artifact_refs") == expected, "private_files_conflict")
    return control


def _read_protease_kinetics_publication(registry, context, reader, source_ref, *, require_numeric=False, require_sheet=False,
        recovery_operation_key=None, before_decision_index=None):
    records = EpisodeReturnRecords(registry.store, context.run_id, failure_prefix="protease_kinetics_")
    records.authenticate(context)
    publication = _metadata_publication(registry, source_ref,
        recovery_context=context if recovery_operation_key else None, recovery_operation_key=recovery_operation_key)
    invocation = publication["producer"]["invocation"]
    own = recovery_operation_key == invocation["operation_key"] and (context.run_id, context.episode_id) == (
        invocation["run_id"], invocation["episode_id"])
    admission = None if own else _source_admission(registry, context, reader, source_ref,
        _cutoff(registry, context) if before_decision_index is None else before_decision_index)
    packet = contracts.validate_ordinary_protease_kinetics_packet(
        decode_json(_publication_bytes(registry.store, publication["source"]["artifact_ref"])))
    _require(_same(contracts.project_ordinary_protease_kinetics_return(packet, source_ref), publication["public"]),
        "public_packet_conflict")
    publication.update(packet=packet, source_admission=admission, control=None, sheet=None, components=None,
        stored=deepcopy(publication["public"]), admission_kind="source_only")
    if require_numeric or require_sheet:
        control = _control(registry, publication)
        docs = {}
        for role in (("sheet", "components") if require_numeric else ("sheet",)):
            file = control["files"][role]["file"]
            if file is not None:
                doc = decode_json(_publication_bytes(registry.store, file["artifact_ref"]))
                if role == "sheet":
                    doc = measurements.validate_protease_kinetics_sheet(doc)
                else:
                    _require(type(doc) is dict and doc.get("schema") == measurements.COMPONENTS_SCHEMA
                        and doc.get("sheet_schema") == measurements.SHEET_SCHEMA, "components_schema_conflict")
                docs[role] = doc
        publication.update(control=control, sheet=docs.get("sheet"), components=docs.get("components"))
    return publication


def read_protease_kinetics_publication(registry, context, reader, source_ref, **options):
    with registry.store.read_snapshot():
        return _read_protease_kinetics_publication(registry, context, reader, source_ref, **options)


def read_retained_protease_kinetics_publication(registry, context, reader, source_ref):
    publication = read_protease_kinetics_publication(registry, context, reader, source_ref)
    return {**publication, "stored": publication["public"]}


def _read_selected(publication, arguments):
    if publication["packet"]["selection"]["rows"] == arguments["rows"]:
        return publication["public"]
    control = publication["control"]
    original = _arguments(control["arguments"])
    selected = {**original, "rows": arguments["rows"]}
    projection = _projection(selected, control["files"], publication["sheet"], publication["components"],
        saved_sheet_ref=control["projection"]["selector"]["saved_sheet_ref"])
    packet = _packet(arguments, projection, publication["packet"]["failures"])
    return contracts.project_ordinary_protease_kinetics_return(packet, publication["source"]["id"])


def _retain_protease_kinetics_publication(registry, prepared):
    _require(registry.store.db.in_transaction, "publication_transaction_required")
    arguments, invocation = prepared["arguments"], prepared["invocation"]
    files, docs, failures = _capture_outputs(registry, prepared["intent"], prepared["worker"], prepared["directory"])
    projection = _projection(arguments, files, docs.get("sheet"), docs.get("components"),
        saved_sheet_ref=prepared["intent"]["input"]["sheet_ref"])
    packet = _packet(arguments, projection, failures)
    packet_ref = registry.store.artifact(canonical(packet), "application/json")
    protected = prepared["intent"]["input"]["protected_input_artifact_refs"]
    control = dict(version=CONTROL_VERSION, arguments=arguments, invocation=invocation,
        intent=prepared["intent"], worker=prepared["worker"], files=files, projection=projection,
        packet_ref=packet_ref, protected_input_artifact_refs=protected)
    control_ref = registry.store.artifact(canonical(control), "application/json")
    parents = ([arguments["result_ref"]] if "result_ref" in arguments else
        [arguments["input"]["reference"]] if arguments["input"]["namespace"] == "source" else [])
    auxiliaries = list(dict.fromkeys(files[role]["file"]["artifact_ref"] for role in _ROLES
        if files[role]["file"] is not None and files[role]["file"]["artifact_ref"] not in protected))
    source = registry.store.put("source", dict(provider=TOOL, accession=None, uri=None, artifact_ref=packet_ref,
        text_ref=None, request_ref=control_ref, version=SOURCE_VERSION, retrieved_at=datetime.now(timezone.utc).isoformat(),
        parent_source_refs=parents, auxiliary_artifact_refs=auxiliaries), origin="tool")
    return dict(source=source, public=contracts.project_ordinary_protease_kinetics_return(packet, source["id"]), control=control)


def _partial(public):
    context = public["values"]["context"]
    return (context["fit"]["state"]["value"] == "unavailable"
        or context["native"]["call_state"]["value"] in ("not_started", "raised")
        or context["native"]["outcome"]["value"] == "source_error" or bool(public["failures"]) or public["file_states"]["sheet"] not in ("retained", "retained_undeclared")
        or public["file_states"]["components"] not in ("retained", "retained_undeclared")
        or any(row["value_state"] in ("path_missing", "invalid_type", "source_unavailable") for row in public["values"]["rows"]))


def _outcome(arguments, key, public):
    partial = _partial(public)
    return dict(status="partial" if partial else "completed", operation_ref=identity("operation", dict(
        key=key, name=TOOL, arguments=arguments)), record_refs=[public["source_ref"]],
        changed_record_refs=[] if arguments["mode"] == "read_stored" else [public["source_ref"]], result=public,
        feedback=None if not partial else dict(category="representation", code="protease_kinetics_partial", source_ref=public["source_ref"]))


def read_protease_kinetics_action_result(registry, context, arguments, operation_key, *, reader):
    arguments = _arguments(arguments)
    active = registry._current_invocation.get()
    recovery = context if active is not None and active[0] is context and active[4] == operation_key else None
    details = _recorded_molecular_action_details(registry, context, arguments, operation_key, TOOL,
        recovery_context=recovery, recovery_operation_key=operation_key if recovery else None)
    outcome = details["outcome"]
    _require(outcome.get("status") in ("completed", "partial"), "action_result_unavailable")
    public = contracts.validate_ordinary_protease_kinetics_return(outcome["result"])
    _require(outcome["record_refs"] == [public["source_ref"]], "action_source_conflict")
    with registry.store.read_snapshot():
        publication = _read_protease_kinetics_publication(registry, context, reader, public["source_ref"],
            recovery_operation_key=operation_key if arguments["mode"] != "read_stored" else None,
            before_decision_index=details["invocation"]["decision_index"],
            require_numeric=arguments["mode"] == "read_stored" and arguments["rows"] != public["selection"]["rows"])
        if arguments["mode"] == "read_stored":
            _require(arguments["result_ref"] == public["source_ref"], "action_source_conflict")
            if publication["packet"]["selection"]["rows"] != arguments["rows"] and publication["control"] is None:
                publication = _read_protease_kinetics_publication(registry, context, reader, public["source_ref"],
                    require_numeric=True, before_decision_index=details["invocation"]["decision_index"])
            expected = _read_selected(publication, arguments)
        else:
            _require(publication["producer"]["invocation"]["operation_key"] == operation_key, "action_source_conflict")
            expected = publication["public"]
    _require(_same(expected, public), "action_result_conflict")
    return public


async def execute_protease_kinetics_tool(registry, arguments, *, scope, operation_key, authority):
    context, reader = authenticate_molecular_invocation(registry, TOOL, arguments, plain(scope), operation_key)
    _require(type(authority) is tuple and len(authority) == 2 and authority[0] is context and authority[1] is reader,
        "invocation_authority_conflict")
    owner = registry.execution_owner_for(context.run_id)
    _require(owner.store is registry.store and owner.tool_registry is registry and owner.run_id == context.run_id,
        "execution_owner_conflict")
    invocation = _invocation(context, operation_key)
    directory = _directory(registry.store.path / "cache" / "molecular-measurements" / digest(operation_key))
    async with _action_lock(directory):
        authenticate_molecular_invocation(registry, TOOL, arguments, plain(scope), operation_key)
        if registry.store.db.execute("SELECT 1 FROM tool_operations WHERE operation_key=?", (operation_key,)).fetchone():
            details = _recorded_molecular_action_details(registry, context, arguments, operation_key, TOOL,
                recovery_context=context, recovery_operation_key=operation_key)
            outcome = details["outcome"]
            if outcome.get("status") in ("completed", "partial"):
                _require(_same(read_protease_kinetics_action_result(registry, context, arguments, operation_key,
                    reader=reader), outcome["result"]), "cached_result_conflict")
            else:
                _require(outcome.get("status") in ("invalid", "unavailable", "failed")
                    and outcome.get("result") is None and outcome.get("record_refs") == [], "cached_failure_conflict")
            return outcome
        attempt_possible = False
        try:
            arguments = _arguments(arguments)
            intent_path = directory / "protease-kinetics-intent.json"
            pending = intent_path.exists() and arguments["mode"] != "read_stored"
            attempt_possible = pending
            configuration = None if pending else _configuration(registry._protease_kinetics_configuration)
            if not pending and arguments["mode"] != "run_native":
                _require(configuration["saved_modes"], "saved_modes_not_configured")
            if arguments["mode"] == "read_stored":
                publication = read_protease_kinetics_publication(registry, context, reader, arguments["result_ref"],
                    before_decision_index=invocation["decision_index"])
                if publication["packet"]["selection"]["rows"] != arguments["rows"]:
                    publication = read_protease_kinetics_publication(registry, context, reader, arguments["result_ref"],
                        require_numeric=True, before_decision_index=invocation["decision_index"])
                public = _read_selected(publication, arguments)
            else:
                worker = _directory(directory / "worker")
                if intent_path.exists():
                    attempt_possible = True
                    intent = decode_json(intent_path.read_bytes())
                    _validate_intent(intent)
                    _require(intent["version"] == INTENT_VERSION and _same(intent["arguments"], arguments)
                        and _same(intent["invocation"], invocation), "original_intent_conflict")
                    if "input" in arguments:
                        _check_input(registry, context, arguments, invocation, intent["input"])
                    else:
                        admission = _source_admission(registry, context, reader, arguments["result_ref"], invocation["decision_index"])
                        _require(_same(admission, intent["source_admission"])
                            and digest(registry.store.get(arguments["result_ref"])) == intent["original_source"]["record_sha256"],
                            "source_admission_conflict")
                        parent = _control(registry, _metadata_publication(registry, arguments["result_ref"]))
                        sheet_file = parent["files"]["sheet"]["file"]
                        _require(sheet_file is not None and intent["input"]["sheet_ref"] == sheet_file["artifact_ref"]
                            and all(intent["input"]["frozen"][key] == sheet_file[key] for key in ("sha256", "size_bytes"))
                            and intent["input"]["protected_input_artifact_refs"] == parent["protected_input_artifact_refs"],
                            "saved_sheet_identity_conflict")
                else:
                    selected = None
                    if arguments["mode"] == "run_native":
                        _require(len(configuration["resources"]) == 1, "native_resource_required")
                        selected = configuration["resources"][0]
                    if "input" in arguments:
                        input = _fresh_input(registry, context, reader, arguments, invocation, directory)
                        original, admission = None, None
                    else:
                        publication = read_protease_kinetics_publication(registry, context, reader, arguments["result_ref"],
                            require_sheet=True, before_decision_index=invocation["decision_index"])
                        _require(publication["sheet"] is not None, "saved_sheet_unavailable")
                        sheet_file = publication["control"]["files"]["sheet"]["file"]
                        raw = _publication_bytes(registry.store, sheet_file["artifact_ref"])
                        input = dict(document=publication["sheet"], frozen=_write_bytes(directory / "input.json", raw), raw_utf8=raw.decode("utf-8"),
                            protected_input_artifact_refs=publication["control"]["protected_input_artifact_refs"],
                            sheet_ref=sheet_file["artifact_ref"])
                        original = dict(source_ref=arguments["result_ref"], record_sha256=digest(publication["source"]))
                        admission = publication["source_admission"]
                    _input_document(arguments, input)
                    request = _request(invocation, arguments, input, selected, worker)
                    intent = dict(version=INTENT_VERSION, arguments=arguments, invocation=invocation,
                        policy=configuration["policy"], selected_resource=selected, input=input, original_source=original,
                        source_admission=admission, request=request, worker_operation="protease_kinetics_native"
                            if arguments["mode"] == "run_native" else "protease_kinetics_saved")
                    _immutable(intent_path, intent)
                _require(_same(intent["request"], _request(invocation, arguments, intent["input"], intent["selected_resource"], worker)),
                    "driver_request_conflict")
                worker.mkdir(exist_ok=True)
                _dispatch(registry, owner, intent, worker)
                attempt_possible = True
                work = await registry._sequence_worker_async(intent["worker_operation"], dict(request=intent["request"]),
                    directory=worker, owned_directory=worker)
                authenticate_molecular_invocation(registry, TOOL, arguments, plain(scope), operation_key)
                if "input" in arguments:
                    _check_input(registry, context, arguments, invocation, intent["input"])
                else:
                    _require(_same(_source_admission(registry, context, reader, arguments["result_ref"],
                        invocation["decision_index"]), intent["source_admission"]), "source_admission_conflict")
                record = _worker_record(work, intent, worker)
                with registry.store.transaction():
                    public = retain_molecular_publication(registry, dict(arguments=arguments, invocation=invocation,
                        intent=intent, worker=record, directory=worker), tool_name=TOOL)["public"]
                    outcome = _outcome(arguments, operation_key, public)
                    registry._save(operation_key, TOOL, arguments, plain(scope), outcome)
                return outcome
            with registry.store.transaction():
                outcome = _outcome(arguments, operation_key, public)
                registry._save(operation_key, TOOL, arguments, plain(scope), outcome)
            return outcome
        except MolecularOperationUnpublished:
            raise
        except Exception as error:
            if attempt_possible:
                raise MolecularOperationUnpublished("protease_kinetics_original_action_unpublished") from error
            with registry.store.transaction():
                text = str(error)
                code = text if re.fullmatch(r"[a-z][a-z0-9_]*", text) else "protease_kinetics_input_invalid"
                diagnostic = registry.store.artifact(canonical(dict(version="protease_kinetics_diagnostic_v1",
                    exception_type=type(error).__module__ + "." + type(error).__name__, message=text)), "application/json")
                outcome = dict(status="unavailable" if isinstance(error, OSError) or code.endswith("_unavailable") else
                    "invalid" if isinstance(error, (ValueError, TypeError, KeyError, ContractError)) else "failed",
                    operation_ref=identity("operation", dict(key=operation_key, name=TOOL, arguments=arguments)),
                    record_refs=[], changed_record_refs=[], result=None,
                    feedback=dict(category="arguments_or_reference", code=code, diagnostic_ref=diagnostic))
                registry._save(operation_key, TOOL, arguments, plain(scope), outcome)
            return outcome


__all__ = ["TOOL", "SOURCE_VERSION", "PACKET_VERSION", "FACT_SOURCE", "CONTROL_VERSION",
    "normalize_protease_kinetics_configuration", "protease_kinetics_tool_contract", "protease_kinetics_fact_sources",
    "execute_protease_kinetics_tool", "read_protease_kinetics_publication", "read_retained_protease_kinetics_publication",
    "read_protease_kinetics_action_result"]
