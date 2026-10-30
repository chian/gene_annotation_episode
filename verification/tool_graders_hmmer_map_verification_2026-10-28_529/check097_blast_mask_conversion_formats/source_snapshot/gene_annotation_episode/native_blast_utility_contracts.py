"""Pure one-command contracts for the declared BLAST database utilities.

The shared utility records own operation meanings. This module only binds those
selections to explicit software, files, prepared databases and output locations.
It does not discover resources, create a database, or choose a follow-up check.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import PurePosixPath
import re

from jsonschema import Draft202012Validator

from .domain import ContractError
from .native_blast_contracts import finite_json_copy, native_blast_digest
from .blast_utility_contracts import SCHEMAS, validate_blast_utility_operation
from .native_blast_standard_database_contracts import (
    DATABASE_OPERAND_SCHEMA, SOFTWARE_SCHEMA, _database, _absolute, _relative,
)

MODES = (("makeblastdb", "create_sequence_database"),
         ("blastdbcmd", "extract_sequences"), ("blastdbcmd", "info"),
         ("blastdbcmd", "metadata"), ("blastdbcheck", "integrity"))
JOB_VERSION = "native_blast_utility_job_v1"
_RESERVED_ENV = frozenset({"TMPDIR", "TMP", "TEMP", "XDG_CACHE_HOME",
                          "PYTHONPATH", "PYTHONHOME", "PYTHONDONTWRITEBYTECODE"})
_STR = {"type": "string", "minLength": 1, "pattern": r"^[^\x00\r\n]+$"}
_SHA = {"type": "string", "pattern": r"^[0-9a-f]{64}$"}
_ENV = {"type": "object", "additionalProperties": {"type": "string"}}


def _object(properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


INPUT_SCHEMA = _object({"input_key": _STR,
    "role": {"enum": ["sequence_input", "taxid_map", "mask_input"]},
    "path": _STR, "format": {"enum": ["fasta", "text", "maskinfo_xml", "maskinfo_asn1_text"]},
    "sha256": _SHA, "size_bytes": {"type": "integer", "minimum": 0},
    "artifact_ref": {"anyOf": [_STR, {"type": "null"}]}})
OUTPUT_SCHEMA = _object({"role": {"enum": ["stdout", "stderr", "database_family"]},
    "path_kind": {"enum": ["file", "prefix"]}, "relative_path": _STR,
    "format": {"enum": ["text", "blastdb_family", "blastdbcmd_tabular_v1",
                          "blastdb_info_text", "blastdb_metadata_json", "blastdbcheck_text"]}})
NATIVE_BLAST_UTILITY_JOB_SCHEMA = _object({"version": {"const": JOB_VERSION},
    "operation": SCHEMAS["Operation"], "software": SOFTWARE_SCHEMA, "environment": _ENV,
    "inputs": {"type": "array", "items": INPUT_SCHEMA},
    "databases": {"type": "array", "maxItems": 1, "items": DATABASE_OPERAND_SCHEMA},
    "outputs": {"type": "array", "minItems": 2, "maxItems": 3, "items": OUTPUT_SCHEMA}})
NATIVE_BLAST_UTILITY_REQUESTED_JOB_SCHEMA = _object({
    "argv": {"type": "array", "minItems": 1, "items": _STR}, "environment": _ENV,
    "native_blast_utility": NATIVE_BLAST_UTILITY_JOB_SCHEMA})


def _error(code):
    raise ContractError("native_blast_utility_" + code)


def _schema(value, schema):
    if next(Draft202012Validator(schema).iter_errors(value), None) is not None:
        _error("schema_mismatch")


def _path(value, *, absolute):
    try:
        (_absolute if absolute else _relative)(value)
    except ValueError as exc:
        raise ContractError("native_blast_utility_invalid_path") from exc
    return PurePosixPath(value)


def _output_format(operation):
    return {"create_sequence_database": "text", "extract_sequences": "blastdbcmd_tabular_v1",
            "info": "blastdb_info_text", "metadata": "blastdb_metadata_json",
            "integrity": "blastdbcheck_text"}[operation["mode"]]


def validate_native_blast_utility_job(value: dict) -> dict:
    job = finite_json_copy(value)
    _schema(job, NATIVE_BLAST_UTILITY_JOB_SCHEMA)
    op = validate_blast_utility_operation(job["operation"])
    if (op["program"], op["mode"]) not in MODES:
        _error("unsupported_program_mode")
    _path(job["software"]["executable"], absolute=True)
    for key, val in job["environment"].items():
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) is None or "\0" in val:
            _error("environment_invalid")
        if key in _RESERVED_ENV:
            _error("producer_owned_environment")
    keys, paths = [], []
    for item in job["inputs"]:
        keys.append(item["input_key"])
        paths.append(str(_path(item["path"], absolute=True)))
        if type(item["size_bytes"]) is not int:
            _error("input_size_invalid")
        expected = {"sequence_input": {"fasta"}, "taxid_map": {"text"},
                    "mask_input": {"maskinfo_xml", "maskinfo_asn1_text"}}[item["role"]]
        if item["format"] not in expected:
            _error("input_format_conflict")
    if len(set(keys)) != len(keys) or keys != op["input_occurrence_ids"]:
        _error("input_selection_conflict")
    # Occurrences may share bytes/path; distinct keys retain distinct selection.
    if op["program"] == "makeblastdb":
        if job["databases"]:
            _error("unexpected_database_operand")
        inputs = {r["input_key"]: r for r in job["inputs"]}
        if sum(r["role"] == "sequence_input" for r in inputs.values()) != 1:
            _error("one_fasta_input_required")
        p = op["parameters"]
        maps = [r["input_key"] for r in inputs.values() if r["role"] == "taxid_map"]
        masks = [r["input_key"] for r in inputs.values() if r["role"] == "mask_input"]
        if maps != ([] if p["taxid_map_occurrence_id"] is None else [p["taxid_map_occurrence_id"]]):
            _error("taxid_map_selection_conflict")
        if masks != p["mask_occurrence_ids"]:
            _error("mask_selection_conflict")
    else:
        if job["inputs"] or len(job["databases"]) != 1:
            _error("one_prepared_database_required")
        db = job["databases"][0]
        try:
            _database(db)
        except ValueError as exc:
            raise ContractError("native_blast_utility_prepared_database_invalid") from exc
        if db["database_key"] != op["database_key"]:
            _error("database_selection_conflict")
        molecule = "protein" if db["kind"] == "blast_protein_sequence" else "dna"
        if molecule != op["molecule"]:
            _error("database_molecule_conflict")
    roles, output_paths = set(), []
    for output in job["outputs"]:
        if output["role"] in roles:
            _error("duplicate_output_role")
        roles.add(output["role"])
        path = _path(output["relative_path"], absolute=False)
        if path.parts[0].startswith('.') or path.parts[0] in {"inputs", "tmp", "cache", "bundle.json", "owner.json"}:
            _error("reserved_output_path")
        output_paths.append(path)
        family = output["role"] == "database_family"
        if output["path_kind"] != ("prefix" if family else "file"):
            _error("output_kind_conflict")
        expected = "blastdb_family" if family else "text" if output["role"] == "stderr" else _output_format(op)
        if output["format"] != expected:
            _error("output_format_conflict")
    expected_roles = {"stdout", "stderr"} | ({"database_family"} if op["program"] == "makeblastdb" else set())
    if roles != expected_roles:
        _error("output_selection_conflict")
    for i, path in enumerate(output_paths):
        for other in output_paths[i+1:]:
            if path == other or path in other.parents or other in path.parents:
                _error("output_path_overlap")
    if op["program"] == "makeblastdb":
        family = next(p for r, p in zip(job["outputs"], output_paths) if r["role"] == "database_family")
        if str(family) != op["parameters"]["output_prefix"]:
            _error("database_output_prefix_conflict")
        if any(r["role"] != "database_family" and p.parent == family.parent and
               p.name.startswith(family.name + ".") for r, p in zip(job["outputs"], output_paths)):
            _error("output_overlaps_database_family")
    return job


def compile_native_blast_utility_job(job: dict, *, input_paths: dict,
                                     database_paths: dict, output_directory: str) -> list[str]:
    """Compile one selected command. Never look up an executable or database."""
    job = validate_native_blast_utility_job(job)
    if type(input_paths) is not dict or set(input_paths) != {r["input_key"] for r in job["inputs"]}:
        _error("complete_input_path_mapping_required")
    if type(database_paths) is not dict or set(database_paths) != {r["database_key"] for r in job["databases"]}:
        _error("complete_database_path_mapping_required")
    for path in input_paths.values():
        _path(path, absolute=True)
    for paths in database_paths.values():
        if type(paths) is not list or not paths or len(paths) != len(set(paths)):
            _error("database_path_mapping_invalid")
        for path in paths:
            if any(c.isspace() for c in path):
                _error("database_path_whitespace")
            _path(path, absolute=True)
    root = PurePosixPath('.') if output_directory == '.' else _path(output_directory, absolute=True)
    original_paths = set(input_paths.values()) | {r["path"] for r in job["inputs"]} | {job["software"]["executable"]}
    original_paths |= {f["path"] for db in job["databases"] for f in db["manifest"]["files"]}
    for output in job["outputs"]:
        selected_path = str(root / output["relative_path"])
        if selected_path in original_paths or (output["role"] == "database_family" and
                any(path.startswith(selected_path + ".") for path in original_paths)):
            _error("output_aliases_input")
    op, args = job["operation"], [job["software"]["executable"]]
    p = op["parameters"]
    molecule = 'prot' if op["molecule"] == 'protein' else 'nucl'
    if op["program"] == 'makeblastdb':
        source = next(r for r in job["inputs"] if r["role"] == 'sequence_input')
        args += ['-in', input_paths[source['input_key']], '-input_type', 'fasta', '-dbtype', molecule,
                 '-out', str(root / p['output_prefix']), '-blastdb_version', str(p['database_format_version']),
                 '-title', p['title']]
        for key in ('parse_seqids','hash_index'):
            if p[key]: args.append('-'+key)
        if p['max_file_size'] is not None: args += ['-max_file_sz',p['max_file_size']]
        if p['taxid'] is not None: args += ['-taxid',str(p['taxid'])]
        if p['taxid_map_occurrence_id'] is not None:
            args += ['-taxid_map',input_paths[p['taxid_map_occurrence_id']]]
        if p['mask_occurrence_ids']:
            selected = [input_paths[k] for k in p['mask_occurrence_ids']]
            if any(',' in path for path in selected): _error('mask_path_delimiter_conflict')
            args += ['-mask_data',','.join(selected)]
    else:
        args += ['-db',' '.join(database_paths[op['database_key']]),'-dbtype',molecule]
        if op['mode'] == 'extract_sequences':
            args += ['-entry',','.join(row['value'] for row in p['selectors']),
                     '-outfmt','%o\t%i\t%a\t%l\t%s','-strand',p['strand']]
            if p['range'] is not None:
                args += ['-range',str(p['range']['start_1based'])+'-'+str(p['range']['end_1based'])]
            for key in ('get_dups','target_only'):
                if p[key]: args.append('-'+key)
        elif op['mode'] == 'info':
            args.append('-info')
            if p['exact_length']: args.append('-exact_length')
        elif op['mode'] == 'metadata':
            args.append('-metadata')
        else:
            for key, flag in (('full','-full'),('no_isam','-no_isam'),
                              ('legacy_file_checks','-legacy'),('require_taxids','-must_have_taxids'),
                              ('cdd_delta','-cdd_delta')):
                if p[key]: args.append(flag)
            for key, flag in (('stride','-stride'),('random_count','-random'),('ends_count','-ends')):
                if p[key] is not None: args += [flag,str(p[key])]
    return args


def requested_job_from_native_blast_utility(job: dict) -> dict:
    job = validate_native_blast_utility_job(job)
    return {'argv':compile_native_blast_utility_job(job,
                input_paths={r['input_key']:r['path'] for r in job['inputs']},
                database_paths={r['database_key']:r['native_paths'] for r in job['databases']},
                output_directory='.'), 'environment':job['environment'], 'native_blast_utility':job}


def validate_native_blast_utility_requested_job(value: dict) -> dict:
    value = finite_json_copy(value)
    _schema(value,NATIVE_BLAST_UTILITY_REQUESTED_JOB_SCHEMA)
    if native_blast_digest(value) != native_blast_digest(requested_job_from_native_blast_utility(value['native_blast_utility'])):
        _error('requested_command_conflict')
    return value


def native_blast_utility_job_schema(*, program: str, mode: str) -> dict:
    if (program,mode) not in MODES: _error('unsupported_program_mode')
    schema = deepcopy(NATIVE_BLAST_UTILITY_JOB_SCHEMA)
    schema['properties']['operation'] = {'allOf':[deepcopy(SCHEMAS['Operation']),
        {'properties':{'program':{'const':program},'mode':{'const':mode}}}]}
    return schema


# Producer custody records. These do not add a utility parser or scoring policy.
PLAN_VERSION = "native_blast_utility_run_plan_v1"
BUNDLE_VERSION = "native_blast_utility_bundle_v1"
PLAN_NAME = "blast-utility-plan.json"
ATTEMPT_NAME = "blast-utility-attempt"
OWNER_NAME = ".native-blast-utility-owner.json"
BUNDLE_NAME = "bundle.json"
FAILURE_STAGES = {
    "software_unavailable": "software", "software_digest_mismatch": "software",
    "software_not_executable": "software", "input_unavailable": "inputs",
    "input_identity_mismatch": "inputs", "staging_scratch_limit": "inputs",
    "database_unavailable": "databases", "database_identity_mismatch": "databases",
    "database_changed": "databases", "command_unavailable": "execution",
    "nonzero_returncode": "execution", "execution_scratch_limit": "execution",
    "immutable_input_changed": "execution", "input_final_unavailable": "execution",
    "missing_output": "outputs", "invalid_output": "outputs",
    "output_inventory_incomplete": "outputs",
}
DATABASE_ROLES = frozenset({"manifest", "database_file", "preparation_receipt",
    "metadata_manifest", "input_manifest", "offline_configuration"})
OUTPUT_ROLES = frozenset({"stdout", "stderr", "database_file", "database_metadata"})


def staged_relative(operand: dict) -> str:
    suffix = {"fasta": ".fa", "text": ".txt", "maskinfo_xml": ".xml",
              "maskinfo_asn1_text": ".asn"}[operand["format"]]
    return "inputs/" + native_blast_digest(operand["input_key"]) + suffix


def native_environment(job: dict, directory) -> dict:
    root = PurePosixPath(directory)
    return {**job["environment"], **{key: str(root / "tmp") for key in ("TMPDIR", "TMP", "TEMP")},
            "XDG_CACHE_HOME": str(root / "cache")}


def database_file_selections(job: dict) -> list[dict]:
    """The selected manifest's complete file/sidecar closure, without file IO."""
    result, seen = [], set()
    for db in job["databases"]:
        manifest = db["manifest"]
        rows = [("manifest", db["manifest_file"])]
        rows += [("database_file", row) for row in manifest["files"]]
        rows += [("preparation_receipt", manifest["preparation"]["receipt"])]
        rows += [("metadata_manifest", row) for row in manifest["metadata_manifests"]]
        rows += [("input_manifest", manifest["preparation"]["input_manifest"]),
                 ("offline_configuration", manifest["access"]["offline_configuration"])]
        for role, row in rows:
            if row is None:
                continue
            key = db["database_key"], role, row["path"]
            if key in seen:
                continue
            seen.add(key)
            result.append({"database_key": db["database_key"], "role": role,
                "original_path": row["path"], "expected_sha256": row["sha256"],
                "expected_size_bytes": row["size_bytes"]})
    return result


def producer_failure(code: str, *, input_key=None, database_key=None, relative_path=None) -> dict:
    return {"stage": FAILURE_STAGES[code], "code": code, "input_key": input_key,
            "database_key": database_key, "relative_path": relative_path}


def measurement_pair(row: dict, prefix="") -> tuple:
    size, sha = row[prefix + "size_bytes"], row[prefix + "sha256"]
    if size is None and sha is None:
        return None, None
    if type(size) is not int or size < 0 or type(sha) is not str or re.fullmatch(r"[0-9a-f]{64}", sha) is None:
        _error("measurement_pair_invalid")
    return size, sha


def _producer_path(value, *, absolute):
    path = _path(value, absolute=absolute)
    if "\\" in value or value in {"/", "."}:
        _error("invalid_path")
    return path


def validate_native_blast_utility_plan(value: dict) -> dict:
    """Validate the original selected reservation; never inspect native paths."""
    plan = finite_json_copy(value)
    if (type(plan) is not dict or set(plan) != {"version", "identity", "requested_job", "attempt_directory", "policy"}
            or plan["version"] != PLAN_VERSION):
        _error("run_plan_required")
    request = validate_native_blast_utility_requested_job(plan["requested_job"])
    identity = plan["identity"]
    if (type(identity) is not dict or set(identity) != {"run_id", "episode_id", "resource_id", "execution_id",
            "attempt_id", "operation_key", "requested_job_sha256"}
            or any(type(v) is not str or not v or any(c in v for c in "\0\r\n") for v in identity.values())
            or identity["requested_job_sha256"] != native_blast_digest(request)
            or identity["attempt_id"] != native_blast_digest(identity["operation_key"])):
        _error("plan_identity_conflict")
    root = _producer_path(plan["attempt_directory"], absolute=True)
    execution = _producer_path(identity["execution_id"], absolute=True)
    if execution.name != "native.json" or root != execution.parent / ATTEMPT_NAME:
        _error("plan_directory_conflict")
    policy = plan["policy"]
    if type(policy) is not dict or set(policy) != {"memory_bytes", "scratch_bytes", "wall_seconds"}:
        _error("explicit_policy_required")
    from .local_jobs import LocalJobPolicy
    LocalJobPolicy(**policy)
    job = request["native_blast_utility"]
    paths = [job["software"]["executable"], *[r["path"] for r in job["inputs"]],
        *[r["original_path"] for r in database_file_selections(job)],
        *[p for db in job["databases"] for p in db["native_paths"]]]
    if any(_producer_path(path, absolute=True).is_relative_to(root) for path in paths):
        _error("supplied_material_inside_attempt")
    for row in job["outputs"]:
        _producer_path(row["relative_path"], absolute=False)
    compile_native_blast_utility_job(job,
        input_paths={r["input_key"]: str(root / staged_relative(r)) for r in job["inputs"]},
        database_paths={db["database_key"]: db["native_paths"] for db in job["databases"]},
        output_directory=str(root))
    return plan


def _family_member(relative, family):
    path = _producer_path(relative, absolute=False)
    prefix = PurePosixPath(family)
    return path.parent == prefix.parent and path.name.startswith(prefix.name + ".")


def _bundle_failures(bundle, job):
    failures = bundle["failures"]
    if type(failures) is not list:
        _error("bundle_failures_invalid")
    inputs = {r["input_key"]: r for r in job["inputs"]}
    dbs = {db["database_key"] for db in job["databases"]}
    outputs = {r["relative_path"] for r in job["outputs"]}
    family = next((r["relative_path"] for r in job["outputs"] if r["role"] == "database_family"), None)
    seen = set()
    for row in failures:
        if (type(row) is not dict or set(row) != {"stage", "code", "input_key", "database_key", "relative_path"}
                or type(row["code"]) is not str or row["code"] not in FAILURE_STAGES
                or row["stage"] != FAILURE_STAGES[row["code"]]):
            _error("bundle_failure_shape")
        code, key, db, relative = row["code"], row["input_key"], row["database_key"], row["relative_path"]
        if relative is not None:
            _producer_path(relative, absolute=False)
        if row["stage"] == "inputs" or code in {"immutable_input_changed", "input_final_unavailable"}:
            if type(key) is not str or key not in inputs or db is not None or relative != staged_relative(inputs[key]):
                _error("bundle_failure_input_conflict")
        elif row["stage"] == "databases":
            if type(db) is not str or db not in dbs or key is not None or relative is not None:
                _error("bundle_failure_database_conflict")
        elif row["stage"] == "outputs":
            if (key is not None or db is not None or relative is None
                    or relative not in outputs and not (family and _family_member(relative, family))):
                _error("bundle_failure_output_conflict")
        elif any(value is not None for value in (key, db, relative)):
            _error("bundle_failure_association_conflict")
        digest = native_blast_digest(row)
        if digest in seen:
            _error("duplicate_bundle_failure")
        seen.add(digest)


def validate_native_blast_utility_bundle(value: dict, original_plan: dict) -> dict:
    """One pure authority for original producer facts and saved-byte consumers."""
    from datetime import datetime, timedelta
    plan, bundle = validate_native_blast_utility_plan(original_plan), finite_json_copy(value)
    fields = {"version", "identity", "requested_job", "operation", "software", "realized_argv", "environment",
        "started", "returncode", "writer_closed", "inventory_complete", "started_at", "finished_at",
        "inputs", "database_files", "artifacts", "failures"}
    if (type(bundle) is not dict or set(bundle) != fields or bundle["version"] != BUNDLE_VERSION
            or native_blast_digest(bundle["identity"]) != native_blast_digest(plan["identity"])
            or native_blast_digest(bundle["requested_job"]) != native_blast_digest(plan["requested_job"])):
        _error("original_bundle_identity_conflict")
    job, root = plan["requested_job"]["native_blast_utility"], PurePosixPath(plan["attempt_directory"])
    if native_blast_digest(bundle["operation"]) != native_blast_digest(job["operation"]):
        _error("original_bundle_request_conflict")
    argv = compile_native_blast_utility_job(job,
        input_paths={r["input_key"]: str(root / staged_relative(r)) for r in job["inputs"]},
        database_paths={db["database_key"]: db["native_paths"] for db in job["databases"]}, output_directory=str(root))
    if bundle["realized_argv"] != argv or bundle["environment"] != native_environment(job, root):
        _error("original_realized_command_conflict")
    software = bundle["software"]
    expected_software = {"executable": job["software"]["executable"], "expected_sha256": job["software"]["sha256"],
                         "declared_engine_version": job["software"]["engine_version"]}
    if (type(software) is not dict or set(software) != set(expected_software) | {"actual_sha256"}
            or any(software[k] != v for k, v in expected_software.items())
            or software["actual_sha256"] is not None and (type(software["actual_sha256"]) is not str
                or re.fullmatch(r"[0-9a-f]{64}", software["actual_sha256"]) is None)):
        _error("bundle_software_conflict")
    rc = bundle["returncode"]
    if (any(type(bundle[k]) is not bool for k in ("started", "writer_closed", "inventory_complete"))
            or rc is not None and type(rc) is not int):
        _error("bundle_outcome_invalid")
    try:
        started = datetime.fromisoformat(bundle["started_at"])
        finished = None if bundle["finished_at"] is None else datetime.fromisoformat(bundle["finished_at"])
        if (started.utcoffset() != timedelta(0) or finished is not None and
                (finished.utcoffset() != timedelta(0) or finished < started)):
            raise ValueError
    except (TypeError, ValueError, OverflowError):
        _error("bundle_timestamp_invalid")
    if (rc is not None and (not bundle["started"] or not bundle["writer_closed"])
            or bundle["started"] and bundle["writer_closed"] and rc is None
            or bundle["inventory_complete"] and not bundle["writer_closed"]
            or bundle["writer_closed"] != (finished is not None)):
        _error("bundle_execution_conflict")
    _bundle_failures(bundle, job)
    def has(code, **association):
        return producer_failure(code, **association) in bundle["failures"]
    if (has("nonzero_returncode") != (rc not in (None, 0))
            or has("command_unavailable") and bundle["started"]
            or bundle["started"] and any(f["stage"] in {"software", "inputs"} for f in bundle["failures"])
            or software["actual_sha256"] is None and not has("software_unavailable")
            or has("software_unavailable") and software["actual_sha256"] is not None
            or has("software_digest_mismatch") != (software["actual_sha256"] not in {None, software["expected_sha256"]})
            or bundle["started"] and software["actual_sha256"] != software["expected_sha256"]):
        _error("bundle_software_or_execution_conflict")
    if (not bundle["started"] and not any(f["stage"] in {"software", "inputs", "databases"}
            or f["code"] in {"command_unavailable", "execution_scratch_limit"} for f in bundle["failures"])):
        _error("bundle_nonstart_failure_required")
    if type(bundle["inputs"]) is not list or len(bundle["inputs"]) != len(job["inputs"]):
        _error("bundle_inputs_conflict")
    for row, selected in zip(bundle["inputs"], job["inputs"]):
        expected = {"input_key": selected["input_key"], "role": selected["role"], "format": selected["format"],
            "original_path": selected["path"], "relative_path": staged_relative(selected),
            "artifact_ref": selected["artifact_ref"], "expected_sha256": selected["sha256"],
            "expected_size_bytes": selected["size_bytes"]}
        if (type(row) is not dict or set(row) != set(expected) | {"staged_sha256", "staged_size_bytes", "final_sha256", "final_size_bytes"}
                or any(type(row[k]) is not type(v) or row[k] != v for k, v in expected.items())):
            _error("bundle_input_identity_conflict")
        staged, final = measurement_pair(row, "staged_"), measurement_pair(row, "final_")
        association = {"input_key": row["input_key"], "relative_path": row["relative_path"]}
        if staged != (selected["size_bytes"], selected["sha256"]) and (bundle["started"] or not any(
                has(code, **association) for code in ("input_unavailable", "input_identity_mismatch", "staging_scratch_limit"))):
            _error("bundle_input_measurement_conflict")
        if has("input_identity_mismatch", **association) and (staged[0] is None or staged == (selected["size_bytes"], selected["sha256"])):
            _error("bundle_input_failure_conflict")
        if has("immutable_input_changed", **association) != (staged != final):
            _error("bundle_input_change_failure_conflict")
        if has("input_final_unavailable", **association) != (staged[0] is not None and final[0] is None):
            _error("bundle_input_unavailable_failure_conflict")
    db_selections = database_file_selections(job)
    if type(bundle["database_files"]) is not list or len(bundle["database_files"]) != len(db_selections):
        _error("bundle_database_closure_conflict")
    for row, selected in zip(bundle["database_files"], db_selections):
        if (type(row) is not dict or set(row) != set(selected) | {"before_sha256", "before_size_bytes", "final_sha256", "final_size_bytes"}
                or any(type(row[k]) is not type(v) or row[k] != v for k, v in selected.items())):
            _error("bundle_database_identity_conflict")
        before, final = measurement_pair(row, "before_"), measurement_pair(row, "final_")
        db = row["database_key"]
        if before != measurement_pair(selected, "expected_") and (bundle["started"] or not has(
                "database_unavailable" if before[0] is None else "database_identity_mismatch", database_key=db)):
            _error("bundle_database_measurement_conflict")
        if before != final and not has("database_changed", database_key=db):
            _error("bundle_database_change_failure_required")
        if final[0] is None and not has("database_unavailable", database_key=db):
            _error("bundle_database_unavailable_failure_required")
    if bundle["started"] and any(has("database_identity_mismatch", database_key=db["database_key"]) for db in job["databases"]):
        _error("bundle_database_preflight_conflict")
    streams = [r for r in job["outputs"] if r["role"] != "database_family"]
    family = next((r["relative_path"] for r in job["outputs"] if r["role"] == "database_family"), None)
    if type(bundle["artifacts"]) is not list or len(bundle["artifacts"]) < len(streams):
        _error("bundle_outputs_conflict")
    family_rows, seen = [], set()
    for index, row in enumerate(bundle["artifacts"]):
        if (type(row) is not dict or set(row) != {"role", "ordinal", "relative_path", "format", "sha256", "size_bytes", "completeness"}
                or type(row["ordinal"]) is not int or row["ordinal"] < 0
                or type(row["completeness"]) is not str or row["completeness"] not in {"complete", "partial", "unknown"}):
            _error("bundle_output_shape")
        path = _producer_path(row["relative_path"], absolute=False)
        if str(path) in seen:
            _error("bundle_output_collision")
        seen.add(str(path))
        if index < len(streams):
            expected = streams[index]
            if any(row[k] != expected[k] for k in ("role", "format", "relative_path")) or row["ordinal"] != 0:
                _error("bundle_stream_identity_conflict")
        else:
            if family is None or not _family_member(str(path), family) or row["ordinal"] != len(family_rows):
                _error("bundle_family_identity_conflict")
            metadata = path.suffix in {".njs", ".pjs"}
            if (row["role"] != ("database_metadata" if metadata else "database_file")
                    or row["format"] != ("blastdb_metadata_json" if metadata else "blastdb_binary")):
                _error("bundle_family_format_conflict")
            family_rows.append(row)
        pair = measurement_pair(row)
        absent = has("missing_output", relative_path=str(path)) or has("invalid_output", relative_path=str(path))
        if absent != (pair[0] is None):
            _error("bundle_output_failure_conflict")
        completeness = ("unknown" if pair[0] is None or not bundle["writer_closed"] else
                        "complete" if rc == 0 else "partial")
        if row["completeness"] != completeness:
            _error("bundle_output_completeness_conflict")
    if [r["relative_path"] for r in family_rows] != sorted(r["relative_path"] for r in family_rows):
        _error("bundle_family_order_conflict")
    if family and not family_rows and not any(has(code, relative_path=family)
            for code in ("missing_output", "invalid_output", "output_inventory_incomplete")):
        _error("bundle_family_absence_failure_required")
    inventory_failures = [f for f in bundle["failures"] if f["code"] == "output_inventory_incomplete"]
    if bundle["inventory_complete"] == bool(inventory_failures):
        _error("bundle_inventory_failure_conflict")
    if bundle["inventory_complete"] and any(r["sha256"] is None for r in family_rows):
        _error("bundle_inventory_capture_conflict")
    return bundle
