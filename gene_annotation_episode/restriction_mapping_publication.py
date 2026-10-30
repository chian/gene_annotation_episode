"""Retain selected restriction inputs and publish closed original-job files.

This module grants no execution capability and performs no restriction search or
coordinate/count calculation. The retained 719 MappingResult is the numerical
authority; job authority belongs to RestrictionMappingJobs.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import stat

from .alignment_site_native import immutable_record
from .domain import ContractError, identity
from .native_file_capture import capture_native_file, retained_native_file, NativeFileCaptureError
from .restriction_mapping_bound_contracts import (
    validate_restriction_bound_record, validate_restriction_alias_arguments, restriction_native_request,
)
from .restriction_mapping_contracts import restriction_canonical, restriction_digest, validate_restriction_record
from .restriction_mapping_inputs import (validate_restriction_sequence_witness, restriction_sequence_binding,
    revalidate_restriction_sequence_witness)

_FILE_ROLES = ("native", "catalog", "mapping", "manifest", "stdout", "stderr")


def _require(condition, code):
    if not condition:
        raise ContractError("restriction_" + code)


def _same(left, right):
    return restriction_canonical(left) == restriction_canonical(right)


def _json(raw):
    def pairs(rows):
        result = {}
        for key, child in rows:
            _require(key not in result, "duplicate_json_key")
            result[key] = child
        return result
    def invalid(_):
        raise ContractError("restriction_json_invalid")
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=invalid)
    restriction_canonical(value)
    return value


def _artifact_bytes(store, reference):
    record = store._require(reference, {"artifact"})
    file = {"artifact_ref": reference, "sha256": record["sha256"], "size_bytes": record["size"], "format": "retained_bytes"}
    path = retained_native_file(store, file)
    raw = path.read_bytes()
    _require(len(raw) == file["size_bytes"] and hashlib.sha256(raw).hexdigest() == file["sha256"], "artifact_conflict")
    return raw


def _source(store, provider, body, *, witness, parents, text_ref=None, files=None, auxiliary=()):
    payload = {"provider": provider, "accession": None, "uri": None,
        "artifact_ref": store.artifact(restriction_canonical(body), "application/json"),
        "text_ref": text_ref, "request_ref": None, "version": body["version"], "retrieved_at": None,
        "operand_refs": [witness["sequence_ref"]], "parent_source_refs": parents}
    if files is not None:
        payload["auxiliary_artifact_refs"] = list(dict.fromkeys([
            *[files[role]["artifact_ref"] for role in _FILE_ROLES if files[role] is not None], *auxiliary]))
        for role in ("stdout", "stderr"):
            if files[role] is not None:
                payload[role + "_ref"] = files[role]["artifact_ref"]
    return store.put("source", payload, origin="tool")


def _body(store, reference, provider, kind):
    source = store._require(reference, {"source"})
    immutable_record(source)
    _require(source["origin"] == "tool" and source["provider"] == provider
        and source["accession"] is None and source["uri"] is None
        and source["request_ref"] is None and source["retrieved_at"] is None, "source_conflict")
    raw = _artifact_bytes(store, source["artifact_ref"])
    body = validate_restriction_bound_record(kind, _json(raw))
    _require(raw == restriction_canonical(body).encode("utf-8") and source["version"] == body["version"], "source_conflict")
    return source, body


def _scope(store, witness, scope):
    try:
        normalized = store.validate_scope(scope)
    except ContractError as error:
        raise ContractError("restriction_scope_conflict") from error
    reference = witness["sequence_ref"]
    selected = store._require(reference, {"input", "feature", "product", "reference", "read_subject"})
    _require((selected["record_type"] == "reference") == (witness["namespace"] == "reference"), "scope_conflict")
    if store.roots(reference):
        footprint = store.coverage(reference)
        _require(bool(footprint) and all(row["target_ref"] in normalized["subject_refs"] for row in footprint)
            and store.scope_covers(footprint, normalized), "scope_conflict")
    return normalized


def retain_restriction_input(store, *, operation_key, tool_name, arguments, scope, witness):
    arguments = validate_restriction_alias_arguments(tool_name, arguments)
    if arguments["mode"] == "saved":
        prior = read_published_restriction_result(store, arguments["result_source_ref"], scope=scope)
        _require(prior["body"]["tool_name"] == tool_name, "saved_alias_conflict")
        _require(_same(validate_restriction_sequence_witness(witness), prior["witness"]), "input_conflict")
        return {"input_source_ref": prior["input_source"]["id"], "sequence_binding": prior["sequence_binding"]}
    witness = validate_restriction_sequence_witness(witness)
    normalized = _scope(store, witness, scope)
    _require(_same(normalized, scope) and _same(normalized, witness["scope"]), "scope_conflict")
    # Reuse the actual resolver/checker methods without constructing/configuring
    # a ToolRegistry. The caller already checked externally received references;
    # this internal revalidation authenticates supplied bytes and packed SQL joins.
    from .tools import ToolRegistry
    class _SelectedStoreOperand:
        _sequence = ToolRegistry._sequence
        _check_sequence_operand = ToolRegistry._check_sequence_operand
        _check_target = ToolRegistry._check_target
    selected = _SelectedStoreOperand()
    selected.store = store
    witness = revalidate_restriction_sequence_witness(store, witness, scope=normalized,
        permitted_record_refs=[witness["sequence_ref"]], sequence_reader=selected._sequence,
        check_operand=selected._check_sequence_operand)
    # Here custody is checked against actual selected Store data. Later saved
    # reads authenticate this retained graph, rather than resolving latest aliases.
    for row in witness["records"]:
        _require(_same(store.get(row["record_ref"]), row["record"]), "input_conflict")
    for file in witness["artifacts"]:
        raw = _artifact_bytes(store, file["artifact_ref"])
        _require(len(raw) == file["size_bytes"] and hashlib.sha256(raw).hexdigest() == file["sha256"], "input_conflict")
    body = validate_restriction_bound_record("InputBody", {"version": "restriction_input_source_v1",
        "operation_key": operation_key, "operation_ref": identity("operation", {"key": operation_key,
            "name": tool_name, "arguments": arguments}), "tool_name": tool_name,
        "arguments": arguments, "scope": normalized, "witness": witness})
    parents = [row["record_ref"] for row in witness["records"] if row["record_type"] == "source"]
    source = _source(store, "episode.restriction_input", body, witness=witness, parents=parents)
    return {"input_source_ref": source["id"],
        "sequence_binding": restriction_sequence_binding(witness, source_ref=source["id"])}


def read_restriction_input(store, input_source_ref):
    source, body = _body(store, input_source_ref, "episode.restriction_input", "InputBody")
    witness = body["witness"]
    parents = [row["record_ref"] for row in witness["records"] if row["record_type"] == "source"]
    _require(source["text_ref"] is None and source.get("operand_refs") == [witness["sequence_ref"]]
        and source.get("parent_source_refs") == parents
        and set(source) == {"id", "record_type", "origin", "provider", "accession", "uri", "artifact_ref",
            "text_ref", "request_ref", "version", "retrieved_at", "operand_refs", "parent_source_refs"}, "source_conflict")
    for file in witness["artifacts"]:
        raw = _artifact_bytes(store, file["artifact_ref"])
        _require(len(raw) == file["size_bytes"] and hashlib.sha256(raw).hexdigest() == file["sha256"], "input_conflict")
    return {"source": source, "body": body, "witness": witness,
        "sequence_binding": restriction_sequence_binding(witness, source_ref=source["id"])}


def _issue(phase, code, role):
    return validate_restriction_bound_record("BoundIssue", {"phase": phase, "code": code, "role": role})


def _state(store, key):
    from .restriction_mapping_jobs import RestrictionMappingJobs
    jobs = RestrictionMappingJobs(store)
    state = jobs.publication_state(key)
    reservation = validate_restriction_bound_record("Reservation", state["reservation"])
    _require(state["execution_proof"] is not None, "writer_not_closed")
    proof = validate_restriction_bound_record("ExecutionProof", state["execution_proof"])
    _require(reservation["operation_key"] == key and reservation["directory"] == str(
        store.path / "native-restriction" / hashlib.sha256(key.encode()).hexdigest()), "operation_conflict")
    for name, value in (("reservation", reservation), ("execution_proof", proof)):
        _require(_same(_json(_artifact_bytes(store, state[name + "_artifact_ref"])), value), "authority_conflict")
    _require(proof["reservation_sha256"] == restriction_digest(reservation), "authority_conflict")
    view = proof["original_view"]
    _require(view["terminal"] and view["quiescent"], "writer_not_closed")
    return jobs, state, reservation, proof


def _software_current(software, *, mode):
    pins = [software["python"], *software["implementation_files"]]
    if mode == "native":
        pins.extend([software["native_source_file"], software["dictionary_file"]])
    for pin in pins:
        path = Path(pin["path"])
        _require(stat.S_ISREG(path.lstat().st_mode) and path.stat().st_size == pin["size_bytes"], "software_conflict")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        _require(digest.hexdigest() == pin["sha256"], "software_conflict")


def _capture(store, reservation):
    """Every independent file is captured before any file is parsed."""
    files, issues = {}, []
    for role in ("native", "catalog", "mapping", "manifest", "stdout", "stderr"):
        stream = role in ("stdout", "stderr")
        directory = reservation["directory"] if stream else reservation["output_directory"]
        name = role + (".txt" if stream else ".json")
        try:
            files[role] = capture_native_file(store, directory=directory, relative_path=name,
                format="restriction_" + role + "_v1", media_type="text/plain" if stream else "application/json")
        except NativeFileCaptureError as error:
            if error.code != "capture_file_unavailable":
                raise
            files[role] = None
            try:
                (Path(directory) / name).lstat()
            except FileNotFoundError:
                code = "file_missing"
            else:
                code = "file_invalid"
            issues.append(_issue("capture", code, role))
    return files, issues


def _assess(store, reservation, proof, bound, files, issues):
    """Validate identity/provenance joins; never reproduce 719 measurements."""
    from .restriction_mapping_worker import validate_restriction_worker_manifest
    issues = deepcopy(issues)
    values = dict(native=None, catalog=None, mapping=None, manifest=None)
    validation = {role: "missing" if files[role] is None else "invalid" for role in ("native", "catalog", "mapping")}
    for role in values:
        if files[role] is None:
            continue
        try:
            raw = _artifact_bytes(store, files[role]["artifact_ref"])
            _require(len(raw) == files[role]["size_bytes"] and hashlib.sha256(raw).hexdigest() == files[role]["sha256"], "file_digest_conflict")
            parsed = _json(raw)
            values[role] = (validate_restriction_worker_manifest(parsed) if role == "manifest" else
                validate_restriction_record({"native": "NativeResult", "catalog": "Catalog", "mapping": "MappingResult"}[role], parsed))
            if role in validation:
                validation[role] = "validated"
        except (ContractError, ValueError, TypeError, KeyError, UnicodeError, NativeFileCaptureError):
            issues.append(_issue("publication", "manifest_invalid" if role == "manifest" else "file_invalid", role))
    manifest = values["manifest"]
    if manifest is not None:
        try:
            _require(manifest["mode"] == reservation["work_mode"]
                and manifest["request_sha256"] == restriction_digest(reservation["worker_request"]), "manifest_invalid")
            for role in ("native", "catalog", "mapping"):
                pin, captured = manifest[role + "_file"], files[role]
                if pin is not None:
                    _require(pin["path"] == str(Path(reservation["output_directory"]) / (role + ".json")), "manifest_invalid")
                    if captured is None or (pin["sha256"], pin["size_bytes"]) != (captured["sha256"], captured["size_bytes"]):
                        if captured is not None:
                            validation[role] = "invalid"
                        issues.append(_issue("publication", "file_digest_conflict", role))
                elif captured is not None:
                    raise ContractError("restriction_manifest_invalid")
        except (ContractError, KeyError, TypeError):
            issues.append(_issue("publication", "manifest_invalid", "manifest"))
            manifest = None
    if manifest is None and not any(i["code"] == "manifest_invalid" for i in issues):
        issues.append(_issue("publication", "manifest_invalid", "manifest"))
    if proof["failure_code"] is not None or proof["returncode"] != 0:
        issues.append(_issue("worker", "worker_failed", "closure"))
    native, catalog, mapping = (values[role] for role in ("native", "catalog", "mapping"))
    global_conflict = any(i["code"] in ("input_conflict", "software_conflict") for i in issues)
    if native is not None and validation["native"] == "validated":
        try:
            witness = bound["witness"]
            request = native["request"]
            expected = restriction_native_request(bound["body"]["tool_name"], bound["body"]["arguments"],
                sequence=witness["sequence"], sequence_binding=bound["sequence_binding"])
            _require(_same(request["sequence_binding"], bound["sequence_binding"])
                and request["sequence"] == witness["sequence"]
                and request["normalized_sequence"] == witness["sequence"].upper()
                and request["topology"] == expected["topology"]
                and _same(request["enzyme_selection"], expected["enzyme_selection"]), "native_binding_conflict")
            software = reservation["software"]
            _require(all(_same(native["software"][field], software[field]) for field in
                ("biopython_version", "native_source_file", "dictionary_file")), "software_conflict")
        except (ContractError, KeyError, ValueError, TypeError) as error:
            code = "software_conflict" if str(error) == "restriction_software_conflict" else "native_binding_conflict"
            issues.append(_issue("authority", code, "native"))
            global_conflict = True
    if global_conflict and files["native"] is not None:
        validation["native"] = "invalid"
    if catalog is not None and validation["catalog"] == "validated":
        if native is None or not _same(catalog, native["catalog"]):
            validation["catalog"] = "invalid"
            issues.append(_issue("publication", "catalog_conflict", "catalog"))
    if mapping is not None and validation["mapping"] == "validated":
        try:
            _require(validation["native"] == "validated" and not global_conflict
                and mapping["native_sha256"] == restriction_digest(native)
                and _same(mapping["selected_sequence"], bound["sequence_binding"])
                and _same(mapping["native_sequence"], native["request"]["sequence_binding"])
                and mapping["binding_status"] == "matched"
                and mapping["topology"] == native["request"]["topology"]
                and _same(mapping["enzyme_selection"], native["request"]["enzyme_selection"]), "mapping_conflict")
            if catalog is not None and validation["catalog"] == "validated":
                _require(_same(mapping["catalog_identity"], {"biopython_version": catalog["biopython_version"],
                    "dictionary_file": catalog["dictionary_file"]}), "mapping_conflict")
                native_rows = {row["catalog_ordinal"]: row for row in native["enzyme_searches"]}
                catalog_rows = {row["ordinal"]: row for row in catalog["enzymes"]}
                for row in mapping["enzyme_rows"]:
                    original = native_rows.get(row["catalog_ordinal"])
                    _require(original is not None and original["name"] == row["name"]
                        and (row["native_search_positions_1based"] is None or _same(
                            row["native_search_positions_1based"], original["native_search_positions_1based"]))
                        and (row["catalog_row"] is None or _same(row["catalog_row"], catalog_rows.get(row["catalog_ordinal"]))), "mapping_conflict")
        except (ContractError, KeyError, ValueError, TypeError):
            validation["mapping"] = "invalid"
            issues.append(_issue("publication", "mapping_conflict", "mapping"))
    # A validated mapping cannot acquire an independently conflicting catalog.
    if validation["catalog"] == "invalid" and validation["mapping"] == "validated":
        validation["mapping"] = "invalid"
        issues.append(_issue("publication", "catalog_conflict", "mapping"))
    for role in ("native", "catalog", "mapping"):
        if validation[role] != "validated":
            values[role] = None
    # Stable ordered deduplication does not sort or transform scientific arrays.
    issues = list({restriction_canonical(issue): issue for issue in issues}.values())
    native, mapping = values["native"], values["mapping"]
    if global_conflict:
        status = "invalid"
    elif native is None:
        status = "failed"
    elif validation["mapping"] == "invalid":
        status = "invalid"
    elif mapping is not None and mapping["status"] == "invalid":
        status = "invalid"
    elif mapping is not None and mapping["status"] == "complete" and manifest is not None and manifest["status"] == "complete" and not issues:
        status = "completed"
    else:
        status = "partial"
    failure = (None if mapping is not None else "mapping_invalid" if status == "invalid" else
        "reader_unavailable" if native is not None else "native_unavailable")
    return values, validation, status, failure, issues


def _outcome(body, source_ref, witness, native, mapping):
    files = body["files"]
    return {"status": body["status"], "operation_ref": body["operation_ref"],
        "record_refs": list(dict.fromkeys([body["input_source_ref"], source_ref])),
        "result": {"source_ref": source_ref, "input_source_ref": body["input_source_ref"],
            "sequence_ref": witness["sequence_ref"], "namespace": witness["namespace"], "work_mode": body["work_mode"],
            "native_artifact_ref": files["native"]["artifact_ref"] if native is not None else None,
            "mapping_artifact_ref": files["mapping"]["artifact_ref"] if mapping is not None else None,
            "data_status": mapping["status"] if mapping is not None else "unavailable",
            "topology": mapping["topology"] if mapping is not None else None,
            "population": deepcopy(mapping["population"]) if mapping is not None else None,
            "issue_codes": list(dict.fromkeys(issue["code"] for issue in body["issues"]))},
        "feedback": None if body["status"] == "completed" else {"category": "representation",
            "code": "restriction_" + (body["failure_code"] or "partial_result"), "source_ref": source_ref}}


def publish_restriction_result(store, operation_key):
    _require(store.db.in_transaction, "publication_transaction_required")
    jobs, state, reservation, proof = _state(store, operation_key)
    if state["published_outcome"] is not None:
        read_published_restriction_result(store, state["published_source_ref"], scope=reservation["scope"])
        return deepcopy(state["published_outcome"])
    bound = read_restriction_input(store, reservation["input_source_ref"])
    _require(_same(bound["sequence_binding"], reservation["sequence_binding"]), "input_conflict")
    if reservation["work_mode"] == "native":
        _require(bound["body"]["operation_key"] == operation_key and _same(bound["body"]["arguments"], reservation["arguments"])
            and bound["body"]["tool_name"] == reservation["tool_name"], "input_conflict")
    else:
        prior = read_published_restriction_result(store, reservation["prior_result_source_ref"], scope=reservation["scope"])
        _require(prior["body"]["tool_name"] == reservation["tool_name"] and prior["input_source"]["id"] == reservation["input_source_ref"], "input_conflict")
        for role in ("native", "catalog"):
            selected = reservation["worker_request"][role + "_file"]
            original = prior["body"]["files"][role]
            _require((selected is None and original is None) or (selected is not None and original is not None
                and selected["sha256"] == original["sha256"] and selected["size_bytes"] == original["size_bytes"]
                and selected["path"] == str(retained_native_file(store, original))), "input_conflict")
    files, issues = _capture(store, reservation)
    try:
        _scope(store, bound["witness"], reservation["scope"])
        if reservation["work_mode"] == "native":
            for row in bound["witness"]["records"]:
                _require(_same(store.get(row["record_ref"]), row["record"]), "input_conflict")
    except ContractError:
        issues.append(_issue("input", "input_conflict", "input"))
    try:
        _software_current(reservation["software"], mode=reservation["work_mode"])
    except (OSError, ContractError):
        issues.append(_issue("authority", "software_conflict", "input"))
    values, validation, status, failure, issues = _assess(store, reservation, proof, bound, files, issues)
    body = validate_restriction_bound_record("PublishedBody", {"version": "restriction_published_result_v1",
        **{key: reservation[key] for key in ("operation_key", "operation_ref", "tool_name", "arguments", "scope", "work_mode", "input_source_ref", "prior_result_source_ref")},
        "reservation_artifact_ref": state["reservation_artifact_ref"], "execution_proof_artifact_ref": state["execution_proof_artifact_ref"],
        "files": files, "validation": validation, "status": status, "failure_code": failure, "issues": issues})
    parents = list(dict.fromkeys([reservation["input_source_ref"], *([reservation["prior_result_source_ref"]] if reservation["work_mode"] == "saved" else [])]))
    source = _source(store, "episode.restriction_result", body, witness=bound["witness"], parents=parents,
        text_ref=files["mapping"]["artifact_ref"] if values["mapping"] is not None else None,
        files=files, auxiliary=[state["reservation_artifact_ref"], state["execution_proof_artifact_ref"]])
    outcome = _outcome(body, source["id"], bound["witness"], values["native"], values["mapping"])
    jobs.record_publication(operation_key, source_ref=source["id"], outcome=outcome)
    return outcome


def read_published_restriction_result(store, source_ref, *, scope):
    source, body = _body(store, source_ref, "episode.restriction_result", "PublishedBody")
    _, state, reservation, proof = _state(store, body["operation_key"])
    _require(state["published_source_ref"] == source_ref and state["published_outcome"] is not None, "authority_conflict")
    for key in ("operation_key", "operation_ref", "tool_name", "arguments", "scope", "work_mode", "input_source_ref", "prior_result_source_ref"):
        _require(_same(body[key], reservation[key]), "authority_conflict")
    for key in ("reservation_artifact_ref", "execution_proof_artifact_ref"):
        _require(body[key] == state[key], "authority_conflict")
    bound = read_restriction_input(store, body["input_source_ref"])
    _require(_same(bound["sequence_binding"], reservation["sequence_binding"]), "input_conflict")
    _scope(store, bound["witness"], scope)
    for file in body["files"].values():
        if file is not None:
            retained_native_file(store, file)
    seed = [i for i in body["issues"] if i["phase"] == "capture" or i["code"] in ("input_conflict", "software_conflict")]
    values, validation, status, failure, issues = _assess(store, reservation, proof, bound, body["files"], seed)
    _require(_same(validation, body["validation"]) and status == body["status"] and failure == body["failure_code"]
        and _same(issues, body["issues"]), "publication_conflict")
    parents = list(dict.fromkeys([body["input_source_ref"], *([body["prior_result_source_ref"]] if body["work_mode"] == "saved" else [])]))
    auxiliary = list(dict.fromkeys([*[body["files"][role]["artifact_ref"] for role in _FILE_ROLES if body["files"][role] is not None],
        state["reservation_artifact_ref"], state["execution_proof_artifact_ref"]]))
    _require(source.get("parent_source_refs") == parents and source.get("operand_refs") == [bound["witness"]["sequence_ref"]]
        and source.get("auxiliary_artifact_refs") == auxiliary
        and source["text_ref"] == (body["files"]["mapping"]["artifact_ref"] if values["mapping"] is not None else None), "source_conflict")
    for role in ("stdout", "stderr"):
        _require(source.get(role + "_ref") == (body["files"][role]["artifact_ref"] if body["files"][role] is not None else None), "source_conflict")
    _require(_same(state["published_outcome"], _outcome(body, source_ref, bound["witness"], values["native"], values["mapping"])), "outcome_conflict")
    return {"source": source, "body": body, "input_source": bound["source"], "witness": bound["witness"],
        "sequence_binding": bound["sequence_binding"], **{key: values[key] for key in ("native", "catalog", "mapping")}}


__all__ = ["retain_restriction_input", "read_restriction_input", "publish_restriction_result",
    "read_published_restriction_result"]
