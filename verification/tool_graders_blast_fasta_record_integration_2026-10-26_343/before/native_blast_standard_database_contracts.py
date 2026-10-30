"""Pure selected native-database contracts; no discovery, I/O or scoring.

The schemas describe custody and invocation, not numerical result sheets. The
accepted contract is workload 327/001, producer boundary N (331).
All public validators return independent finite JSON values and raise ValueError
with a stable native_blast_standard_database_* code. A valid record proves no deployment.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import math
from pathlib import PurePosixPath
import re

from .blast_program_context import resolve_blast_program_context

PROGRAMS = ("blastn", "blastp", "blastx", "tblastn", "tblastx")
RESERVED_ENVIRONMENT = frozenset({"TMPDIR", "TMP", "TEMP", "XDG_CACHE_HOME", "PYTHONPATH", "PYTHONDONTWRITEBYTECODE"})
TABULAR_FIELDS = frozenset("qseqid qgi qacc qaccver qlen sseqid sallseqid sgi sallgi sacc saccver sallacc slen qstart qend sstart send qseq sseq evalue bitscore score length pident nident mismatch positive gapopen gaps ppos frames qframe sframe btop staxid ssciname scomname sblastname sskingdom staxids sscinames scomnames sblastnames sskingdoms stitle salltitles sstrand qcovs qcovhsp qcovus".split())
_PREFIX = "native_blast_standard_database_"
_STR = {"type": "string", "minLength": 1, "pattern": r"^[^\x00]+$"}
_SHA = {"type": "string", "pattern": r"^[0-9a-f]{64}$"}
_INT = {"type": "integer", "minimum": 0}
_BOOL = {"type": "boolean"}
_ABS = {"type": "string", "minLength": 1}
_KEY = {"type": "string", "minLength": 1, "pattern": r"^[^/\\\x00]+$"}
_ENV = {"type": "object", "additionalProperties": {"type": "string"}}


def _nullable(schema):
    return {"anyOf": [schema, {"type": "null"}]}


def _object(properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def _array(items, **extra):
    return {"type": "array", "items": items, **extra}


PROVENANCE_SCHEMA = _object({"source_ref": _STR, "pointer": {"type": "string"}})
FILE_IDENTITY_SCHEMA = _object({"path": _ABS, "sha256": _SHA, "size_bytes": _INT, "artifact_ref": _nullable(_STR)})
_FILE = _object({"path": _ABS, "sha256": _SHA, "size_bytes": _INT})
DATABASE_IDENTITY_SCHEMA = _object({"namespace": _STR, "value": _STR, "version": _nullable(_STR),
    "release": _nullable(_STR), "scope": _nullable(_STR),
    "preparation_type": {"const": "sequence_database"}, "source": PROVENANCE_SCHEMA})
SOFTWARE_SCHEMA = _object({"executable": _ABS, "sha256": _SHA, "engine_version": _nullable(_STR)})
PREPARED_DATABASE_SCHEMA = _object({
    "version": {"const": "native_blast_standard_prepared_database_manifest_v1"}, "database_key": _KEY,
    "kind": {"enum": ["blast_protein_sequence", "blast_nucleotide_sequence"]},
    "identity": DATABASE_IDENTITY_SCHEMA, "native_paths": _array(_ABS, minItems=1, uniqueItems=True),
    "files": _array(_FILE, minItems=1),
    "preparation": _object({"method": {"enum": ["makeblastdb", "publisher_package", "other_recorded"]},
        "preparation_type": {"const": "sequence_database"},
        "software": _object({"name": _STR, "version": _nullable(_STR), "executable_sha256": _nullable(_SHA)}),
        "argv": _nullable(_array(_STR, minItems=1)), "source": PROVENANCE_SCHEMA,
        "input_manifest": _nullable(FILE_IDENTITY_SCHEMA), "receipt": FILE_IDENTITY_SCHEMA}),
    "metadata_manifests": _array(FILE_IDENTITY_SCHEMA),
    "access": _object({"mode": {"const": "prepared_local"}, "offline_configuration": _nullable(FILE_IDENTITY_SCHEMA)}),
    "inventory_complete": _BOOL})
DATABASE_OPERAND_SCHEMA = _object({"database_key": _KEY, "role": {"const": "target"},
    "kind": PREPARED_DATABASE_SCHEMA["properties"]["kind"], "identity": DATABASE_IDENTITY_SCHEMA,
    "native_paths": _array(_ABS, minItems=1, uniqueItems=True), "manifest_file": FILE_IDENTITY_SCHEMA,
    "manifest": PREPARED_DATABASE_SCHEMA})
OUTPUT_SELECTION_SCHEMA = _object({"output_key": _KEY,
    "role": {"enum": ["stdout", "stderr", "primary_report"]},
    "path_kind": {"const": "file"}, "relative_path": _STR,
    "format": {"enum": ["text", "json15", "tabular6", "tabular7"]},
    "fields": _array({"enum": sorted(TABULAR_FIELDS)}, uniqueItems=True),
    "delimiter": _nullable({"type": "string", "minLength": 1, "maxLength": 1}), "required": _BOOL})
MODEL_SCHEMA = {"type": "object", "properties": {
    "temperature_bits": {"type": "number", "exclusiveMinimum": 0},
    "function_priors": _nullable({"type": "object", "additionalProperties": {"type": "number", "minimum": 0}})},
    "additionalProperties": False}
NATIVE_BLAST_STANDARD_DATABASE_JOB_SCHEMA = _object({
    "version": {"const": "native_blast_standard_database_job_v1"}, "program": {"enum": list(PROGRAMS)},
    "mode": {"const": "database"}, "software": SOFTWARE_SCHEMA, "environment": _ENV,
    "inputs": _array(_object({"input_key": _KEY,
        "role": {"enum": ["query_sequence", "query_pssm", "metadata"]},
        "path": _ABS, "format": {"enum": ["fasta", "scoremat_asn_text", "json", "text"]},
        "sha256": _SHA, "size_bytes": _INT, "artifact_ref": _nullable(_STR)}), minItems=1),
    "query": _object({"kind": {"enum": ["sequence", "pssm"]}, "input_key": _KEY}),
    "databases": _array(DATABASE_OPERAND_SCHEMA, minItems=1, maxItems=1), "options": _array(_STR),
    "outputs": _array(OUTPUT_SELECTION_SCHEMA, minItems=3, maxItems=3),
    "metadata_inputs": _array(_object({"input_key": _KEY,
        "consumer": {"enum": ["query_identity", "sequence_database"]},
        "schema_id": {"enum": ["native_blast_database_query_metadata_v1",
                                "native_blast_database_sequence_metadata_v1"]}}), uniqueItems=True),
    "grading_parameters": _object({"sequence_database_model": _nullable(MODEL_SCHEMA)})})
NATIVE_BLAST_STANDARD_DATABASE_REQUESTED_JOB_SCHEMA = _object({"argv": _array(_STR, minItems=1),
    "environment": _ENV, "native_blast_standard_database": NATIVE_BLAST_STANDARD_DATABASE_JOB_SCHEMA})
PRODUCER_MANIFEST_SCHEMA = _object({"version": {"const": "native_blast_standard_database_producer_manifest_v1"},
    "module_root": _ABS, "entry_module": {"const": "gene_annotation_episode.native_blast_standard_database_driver"},
    "python": _FILE, "package_files": _array(_object({"relative_path": _STR, "sha256": _SHA, "size_bytes": _INT}), minItems=4),
    "runtime_files": _array(_FILE)})
IDENTITY_SCHEMA = _object({**{key: _STR for key in ("run_id", "episode_id", "resource_id", "operation_key")},
    **{key: _SHA for key in ("attempt_id", "assignment_sha256", "requested_job_sha256", "submission_token")},
    "execution_id": _nullable(_STR)})
PLAN_SCHEMA = _object({"version": {"const": "native_blast_standard_database_run_plan_v1"}, "identity": IDENTITY_SCHEMA,
    "requested_job": NATIVE_BLAST_STANDARD_DATABASE_REQUESTED_JOB_SCHEMA, "attempt_directory": _ABS,
    "input_paths": {"type": "object", "additionalProperties": _ABS},
    "database_paths": {"type": "object", "additionalProperties": _array(_ABS, minItems=1)},
    "output_directory": _ABS, "resource_environment": _ENV, "producer_manifest": FILE_IDENTITY_SCHEMA})


def _fail(code):
    raise ValueError(_PREFIX + code)


def _copy(value, _active=None):
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if type(value) is list or type(value) is dict and all(type(k) is str for k in value):
        active = set() if _active is None else _active
        identity = id(value)
        if identity in active:
            _fail("finite_json_required")
        active.add(identity)
        try:
            if type(value) is list:
                return [_copy(v, active) for v in value]
            return {k: _copy(v, active) for k, v in value.items()}
        finally:
            active.remove(identity)
    _fail("finite_json_required")


def _digest(value):
    return hashlib.sha256(json.dumps(_copy(value), sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _schema(value, schema, path="$"):
    """Validate the ordinary JSON-schema subset used by these closed records."""
    if "anyOf" in schema:
        for candidate in schema["anyOf"]:
            try:
                _schema(value, candidate, path)
                return
            except ValueError:
                pass
        _fail("schema:" + path + ":anyOf")
    if "const" in schema and (type(value) is not type(schema["const"]) or value != schema["const"]):
        _fail("schema:" + path + ":const")
    if "enum" in schema and not any(type(value) is type(v) and value == v for v in schema["enum"]):
        _fail("schema:" + path + ":enum")
    kind = schema.get("type")
    types = {"object": (dict,), "array": (list,), "string": (str,), "integer": (int,),
        "number": (int, float), "boolean": (bool,), "null": (type(None),)}
    if kind and type(value) not in types[kind]:
        _fail("schema:" + path + ":type")
    if kind == "object":
        properties = schema.get("properties", {})
        if set(schema.get("required", [])) - value.keys():
            _fail("schema:" + path + ":required")
        for key, item in value.items():
            child = properties.get(key, schema.get("additionalProperties", True))
            if child is False:
                _fail("schema:" + path + ":additionalProperties")
            if type(child) is dict:
                _schema(item, child, path + "." + key)
    if kind == "array":
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", math.inf):
            _fail("schema:" + path + ":length")
        if schema.get("uniqueItems") and len({_digest(v) for v in value}) != len(value):
            _fail("schema:" + path + ":uniqueItems")
        for index, item in enumerate(value):
            _schema(item, schema.get("items", {}), path + "[" + str(index) + "]")
    if kind == "string":
        if (len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", math.inf)
                or "pattern" in schema and re.fullmatch(schema["pattern"], value) is None):
            _fail("schema:" + path + ":string")
    if kind in ("number", "integer"):
        if kind == "number":
            try:
                finite = math.isfinite(value)
            except OverflowError:
                finite = False
            if not finite:
                _fail("schema:" + path + ":finite_number")
        if (value < schema.get("minimum", -math.inf) or value > schema.get("maximum", math.inf)
                or "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]):
            _fail("schema:" + path + ":range")


def _absolute(value):
    if (type(value) is not str or not value.startswith("/") or value.startswith("//")
            or any(c in value for c in ("\0", "\n", "\r")) or ".." in value.split("/")
            or str(PurePosixPath(value)) != value):
        _fail("absolute_normalized_path_required")


def _relative(value):
    if (type(value) is not str or not value or value.startswith("/")
            or any(c in (".", "..") for c in value.split("/"))
            or any(ord(c) < 32 or ord(c) == 127 for c in value)
            or str(PurePosixPath(value)) != value):
        _fail("confined_relative_path_required")


def _inside(path, root, *, equal=False):
    p, r = PurePosixPath(path), PurePosixPath(root)
    return r in p.parents or equal and p == r


def _overlap(a, b):
    return a == b or _inside(a, b) or _inside(b, a)


def _environment(env, *, job=False):
    _schema(env, _ENV)
    for key, value in env.items():
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) is None or "\0" in value:
            _fail("environment_invalid")
        if job and key in RESERVED_ENVIRONMENT:
            _fail("producer_owned_environment:" + key)


def _provenance(value):
    _schema(value, PROVENANCE_SCHEMA)
    if (value["pointer"] and not value["pointer"].startswith("/")
            or re.search(r"~(?![01])", value["pointer"])):
        _fail("provenance_pointer_invalid")


def _file_identity(value):
    _schema(value, FILE_IDENTITY_SCHEMA)
    _absolute(value["path"])


def _database_sidecars(db):
    m = db["manifest"]
    return [("preparation_input_manifest", m["preparation"]["input_manifest"]),
            ("offline_configuration", m["access"]["offline_configuration"])]


def _database_metadata_key(database_key, identity):
    return "database-metadata-" + _digest({"database_key": database_key, "role": "metadata", "identity": identity})


def _database(db):
    _schema(db, DATABASE_OPERAND_SCHEMA)
    manifest = db["manifest"]
    for field in ("database_key", "kind", "identity", "native_paths"):
        if db[field] != manifest[field]:
            _fail("database_manifest_operand_mismatch:" + field)
    _provenance(db["identity"]["source"])
    _provenance(manifest["preparation"]["source"])
    if manifest["preparation"]["preparation_type"] != "sequence_database":
        _fail("database_preparation_type_mismatch")
    if not manifest["inventory_complete"]:
        _fail("database_complete_inventory_required")
    for path in db["native_paths"]:
        _absolute(path)
        if any(c.isspace() for c in path):
            _fail("database_whitespace_path_forbidden")
    files = set()
    for row in manifest["files"]:
        _absolute(row["path"])
        if row["path"] in files:
            _fail("database_inventory_duplicate_path")
        files.add(row["path"])
    for native in db["native_paths"]:
        if not any(p.startswith(native + ".") for p in files):
            _fail("database_native_path_not_in_inventory")
    identities = [db["manifest_file"], manifest["preparation"]["receipt"], *manifest["metadata_manifests"],
        *[v for _, v in _database_sidecars(db) if v is not None]]
    by_path = {row["path"]: (row["sha256"], row["size_bytes"]) for row in manifest["files"]}
    for row in identities:
        _file_identity(row)
        identity = row["sha256"], row["size_bytes"]
        if row["path"] in by_path and by_path[row["path"]] != identity:
            _fail("database_file_identity_conflict")
        by_path[row["path"]] = identity


_COMPILER_FLAGS = frozenset({"-query", "-in_pssm", "-db", "-out", "-outfmt"})
_FORBIDDEN_FLAGS = frozenset({"-remote", "-subject", "-subject_loc", "-entrez_query", "-phi_pattern",
    "-import_search_strategy", "-export_search_strategy", "-html", "-gilist", "-seqidlist",
    "-negative_gilist", "-negative_seqidlist", "-taxids", "-negative_taxids", "-taxidlist",
    "-negative_taxidlist", "-no_taxid_expansion", "-db_soft_mask", "-db_hard_mask", "-filtering_db",
    "-window_masker_taxid", "-window_masker_db", "-use_index", "-index_name", "-ipglist", "-negative_ipglist"})
_GENCODES = set(range(1, 7)) | set(range(9, 17)) | set(range(21, 32)) | {33}
_TASKS = {"blastn": {"blastn", "blastn-short", "dc-megablast", "megablast", "rmblastn"},
    "blastp": {"blastp", "blastp-fast", "blastp-short"},
    "blastx": {"blastx", "blastx-fast"}, "tblastn": {"tblastn", "tblastn-fast"}}
_METADATA_TUPLES = (("query_identity", "native_blast_database_query_metadata_v1"),
                    ("sequence_database", "native_blast_database_sequence_metadata_v1"))


def _option_grammar(program):
    if type(program) is not str or program not in PROGRAMS:
        _fail("program_unsupported")
    flags = {"-lcase_masking", "-parse_deflines", "-show_gis", "-subject_besthit"}
    values = {"-query_loc": "range", "-evalue": "real", "-word_size": "word_size",
        "-qcov_hsp_perc": "percent", "-max_hsps": "positive_integer", "-max_target_seqs": "positive_integer",
        "-xdrop_ungap": "real", "-searchsp": "uint63", "-dbsize": "int64", "-soft_masking": "boolean",
        "-culling_limit": "nonnegative_integer", "-best_hit_overhang": "open_half",
        "-best_hit_score_edge": "open_half", "-window_size": "nonnegative_integer", "-num_threads": "positive_integer"}
    if program != "tblastx":
        flags.add("-ungapped")
        values.update({"-task": "task", "-gapopen": "integer", "-gapextend": "integer",
            "-xdrop_gap": "real", "-xdrop_gap_final": "real", "-mt_mode": "mt_mode"})
    if program in {"blastn", "blastx", "tblastx"}:
        values["-strand"] = "strand"
    if program == "blastn":
        flags.add("-no_greedy")
        values.update({"-perc_identity": "percent", "-penalty": "nonpositive_integer",
            "-reward": "nonnegative_integer", "-min_raw_gapped_score": "integer", "-template_type": "template_type",
            "-template_length": "template_length", "-dust": "dust", "-off_diagonal_range": "nonnegative_integer"})
    else:
        values.update({"-matrix": "matrix", "-threshold": "nonnegative", "-seg": "seg"})
        if program != "tblastx":
            flags.add("-use_sw_tback")
            values["-comp_based_stats"] = "composition"
    if program in {"blastx", "tblastx"}:
        values["-query_gencode"] = "gencode"
    if program in {"tblastn", "tblastx"}:
        values["-db_gencode"] = "gencode"
    if program in {"blastx", "tblastn", "tblastx"}:
        values.update({"-sum_stats": "boolean", "-max_intron_length": "nonnegative_integer"})
    return flags, values


def standard_blast_database_program_spec(program: str) -> dict:
    """Return declared grammar and coordinate units, never availability or score."""
    flags, values = _option_grammar(program)
    protein_query = program in {"blastp", "tblastn"}
    protein_target = program in {"blastp", "blastx"}
    kinds = ["sequence", "pssm"] if program == "tblastn" else ["sequence"]
    aliases = {kind: ["psitblastn" if kind == "pssm" else program] for kind in kinds}
    contexts = {kind: resolve_blast_program_context(execution_program=program,
        reported_program=aliases[kind][0], scientific_mode="database", query_kind=kind,
        reference_kind="sequence", native_version=None) for kind in kinds}
    return {"program": program, "query_kinds": kinds,
        "query_formats": {kind: "scoremat_asn_text" if kind == "pssm" else "fasta" for kind in kinds},
        "query_molecules": ["protein"] if protein_query else ["dna", "rna"],
        "database_kind": "blast_protein_sequence" if protein_target else "blast_nucleotide_sequence",
        "query_coordinate_unit": "aa" if protein_query else "nt",
        "reference_coordinate_unit": "aa" if protein_target else "nt",
        "alignment_coordinate_unit": "nt" if program == "blastn" else "aa",
        "native_program_aliases": aliases, "program_contexts": contexts,
        "admitted_options": [{"name": name, "operand_kind": "flag" if name in flags else values[name]}
                             for name in sorted(flags | values.keys())]}


def standard_blast_database_metadata_registry() -> list[dict]:
    """Expose only the two unchanged, existing scientific wire-schema tuples.

    This registry is descriptive. Invoke the existing public supplied-byte
    validator; its native6 preparation entry is not a standard job preparer.
    No metadata module is imported by producer validation or execution.
    """
    from .native_blast_database_metadata import metadata_schema_registry
    rows = [row for row in metadata_schema_registry()
            if (row["consumer"], row["schema_id"]) in _METADATA_TUPLES]
    if [(row["consumer"], row["schema_id"]) for row in rows] != list(_METADATA_TUPLES):
        _fail("metadata_registry_contract_mismatch")
    return _copy(rows)


def validate_standard_blast_database_options(program: str, options: list[str], *, query_kind: str) -> dict:
    """Validate selected tokens and return a detached flag-to-original-value map.

    Valueless flags map to None. Exact token spelling/order remains in the job;
    scientific interpretation may derive typed effective values separately.
    """
    flags, values = _option_grammar(program)
    if type(query_kind) is not str or query_kind not in ({"sequence", "pssm"} if program == "tblastn" else {"sequence"}):
        _fail("program_query_kind_conflict")
    tokens = _copy(options)
    _schema(tokens, _array(_STR))
    selected, index = {}, 0
    while index < len(tokens):
        flag = tokens[index]
        if flag in _COMPILER_FLAGS:
            _fail("compiler_owned_option:" + flag)
        if flag in _FORBIDDEN_FLAGS:
            _fail("forbidden_option:" + flag)
        if flag not in flags | values.keys():
            _fail("unsupported_option:" + flag)
        if flag in selected:
            _fail("duplicate_option:" + flag)
        selected[flag], index = None, index + 1
        if flag in flags:
            continue
        if index == len(tokens):
            _fail("option_operand_required:" + flag)
        raw, kind = tokens[index], values[flag]
        selected[flag], index = raw, index + 1
        valid = False
        if kind == "range":
            match = re.fullmatch(r"([1-9][0-9]*)-([1-9][0-9]*)", raw)
            valid = bool(match and int(match[1]) <= int(match[2]) and query_kind == "sequence")
        elif kind == "boolean":
            valid = raw.lower() in {"true", "false", "t", "f", "yes", "no", "y", "n", "1", "0"}
        elif kind == "composition":
            valid = raw in {"D", "d", "0", "F", "f", "1", "2", "T", "t", "3"}
        elif kind == "matrix":
            # A native matrix name is admitted; an untracked custom file is not.
            valid = re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", raw) is not None
        elif kind in {"strand", "task", "template_type"}:
            valid = raw in ({"plus", "minus", "both"} if kind == "strand" else
                _TASKS[program] if kind == "task" else {"coding", "coding_and_optimal", "optimal"})
        elif kind in {"seg", "dust"}:
            parts = raw.split()
            valid = raw in {"yes", "no"}
            if len(parts) == 3:
                try:
                    valid = (re.fullmatch(r"[0-9]+", parts[0]) is not None and int(parts[0]) > 0
                        and all(math.isfinite(float(v)) and float(v) >= 0 for v in parts[1:]))
                    if kind == "dust":
                        valid = valid and all(re.fullmatch(r"[0-9]+", v) is not None for v in parts)
                except (ValueError, OverflowError):
                    valid = False
        else:
            try:
                number = float(raw)
                valid = math.isfinite(number)
                integer = "integer" in kind or kind in {"int64", "uint63", "mt_mode", "word_size", "gencode", "template_length"}
                if integer:
                    valid = valid and re.fullmatch(r"[+-]?[0-9]+", raw) is not None
                    if valid:
                        number = int(raw)
                        valid = -(2**63) <= number < 2**63 if kind in {"int64", "uint63"} else -(2**31) <= number < 2**31
                if kind == "positive_integer": valid = valid and number >= 1
                if kind in {"nonnegative_integer", "nonnegative", "uint63"}: valid = valid and number >= 0
                if kind == "nonpositive_integer": valid = valid and number <= 0
                if kind == "percent": valid = valid and 0 <= number <= 100
                if kind == "open_half": valid = valid and 0 < number < .5
                if kind == "mt_mode": valid = valid and number in {0, 1, 2}
                if kind == "word_size": valid = valid and number >= (4 if program == "blastn" else 2)
                if kind == "gencode": valid = valid and number in _GENCODES
                if kind == "template_length": valid = valid and number in {16, 18, 21}
            except (ValueError, OverflowError):
                valid = False
        if not valid:
            _fail("invalid_option_operand:" + flag)
    for first, second in (("-culling_limit", "-best_hit_overhang"), ("-culling_limit", "-best_hit_score_edge")):
        if first in selected and second in selected:
            _fail("conflicting_options:" + first + ":" + second)
    for flag, required in (("-mt_mode", "-num_threads"), ("-template_type", "-template_length"),
                           ("-template_length", "-template_type")):
        if flag in selected and required not in selected:
            _fail("required_option:" + flag + ":" + required)
    return selected


def _options(job):
    return validate_standard_blast_database_options(job["program"], job["options"], query_kind=job["query"]["kind"])


def validate_standard_blast_database_job(job: dict) -> dict:
    job = _copy(job)
    _schema(job, NATIVE_BLAST_STANDARD_DATABASE_JOB_SCHEMA)
    _absolute(job["software"]["executable"])
    _environment(job["environment"], job=True)
    inputs = _unique(job["inputs"], "input_key")
    for row in inputs.values():
        _absolute(row["path"])
    q = job["query"]
    spec = standard_blast_database_program_spec(job["program"])
    if q["kind"] not in spec["query_kinds"]:
        _fail("program_query_kind_conflict")
    if q["input_key"] not in inputs:
        _fail("query_input_required")
    expected = {"sequence": ("query_sequence", "fasta"), "pssm": ("query_pssm", "scoremat_asn_text")}[q["kind"]]
    for key, row in inputs.items():
        if key == q["input_key"]:
            if (row["role"], row["format"]) != expected:
                _fail("query_input_role_format_conflict")
        elif row["role"] != "metadata":
            _fail("exactly_one_query_input_required")
    for row in job["metadata_inputs"]:
        if (row["input_key"] not in inputs or inputs[row["input_key"]]["role"] != "metadata"
                or inputs[row["input_key"]]["format"] != "json"):
            _fail("metadata_descriptor_input_conflict")
        if (row["consumer"], row["schema_id"]) not in _METADATA_TUPLES:
            _fail("metadata_schema_unsupported")
    databases = _unique(job["databases"], "database_key")
    db = job["databases"][0]
    if db["role"] != "target" or db["kind"] != spec["database_kind"]:
        _fail("program_database_role_conflict")
    for db in databases.values():
        _database(db)
    outputs = _unique(job["outputs"], "output_key")
    roles = _unique(job["outputs"], "role")
    if inputs.keys() & outputs.keys():
        _fail("input_output_key_collision")
    if roles.keys() != {"stdout", "stderr", "primary_report"}:
        _fail("required_output_roles_missing")
    boundaries = []
    for row in outputs.values():
        _relative(row["relative_path"])
        role, fmt = row["role"], row["format"]
        if row["path_kind"] != "file" or not row["required"]:
            _fail("required_file_output_contract_invalid")
        boundaries.append(row["relative_path"])
        if role in {"stdout", "stderr"} and fmt != "text":
            _fail("stream_output_format_invalid")
        if role == "primary_report" and fmt not in {"json15", "tabular6", "tabular7"}:
            _fail("primary_report_format_invalid")
        if fmt in {"tabular6", "tabular7"}:
            delimiter = row["delimiter"]
            if not {"qseqid", "sseqid"} <= set(row["fields"]):
                _fail("explicit_table_locator_fields_required")
            if delimiter is not None and (len(delimiter.encode()) != 1 or
                    delimiter != "\t" and (delimiter.isspace() or ord(delimiter) < 32 or ord(delimiter) == 127)):
                _fail("invalid_table_delimiter")
            if "qcovus" in row["fields"] and job["program"] != "blastn":
                _fail("program_tabular_field_conflict:qcovus")
        elif row["fields"] or row["delimiter"] is not None:
            _fail("non_tabular_layout_conflict")
    _disjoint(boundaries, "output_path_overlap")
    model = job["grading_parameters"]["sequence_database_model"]
    if model is not None and model.get("function_priors") is not None:
        priors = model["function_priors"]
        if not priors or any(not key.strip() or "\0" in key for key in priors) or not any(v > 0 for v in priors.values()):
            _fail("model_function_priors_invalid")
    _options(job)
    return job


def _unique(rows, key):
    values = {r[key]: r for r in rows}
    if len(values) != len(rows):
        _fail("duplicate:" + key)
    return values


def _disjoint(paths, code):
    for i, path in enumerate(paths):
        if any(_overlap(path, other) for other in paths[i + 1:]):
            _fail(code)


def _compile(job, *, input_paths, database_paths, output_directory):
    job = validate_standard_blast_database_job(job)
    inputs, databases = _copy(input_paths), _copy(database_paths)
    if type(inputs) is not dict or inputs.keys() != {r["input_key"] for r in job["inputs"]}:
        _fail("complete_input_path_mapping_required")
    for path in inputs.values():
        _absolute(path)
    _disjoint(list(inputs.values()), "input_path_overlap")
    if databases != {r["database_key"]: r["native_paths"] for r in job["databases"]}:
        _fail("selected_database_paths_mismatch")
    if output_directory != ".":
        _absolute(output_directory)
    outputs = [{**r, "path": str(PurePosixPath(output_directory) / r["relative_path"])} for r in job["outputs"]]
    boundaries = [str(PurePosixPath(r["path"]).parent) if r["path_kind"] == "prefix" else r["path"] for r in outputs]
    if any(_overlap(a, b) for a in inputs.values() for b in boundaries):
        _fail("input_output_path_overlap")
    q = job["query"]
    argv = [job["software"]["executable"], *job["options"],
        "-query" if q["kind"] == "sequence" else "-in_pssm", inputs[q["input_key"]],
        "-db", " ".join(databases[job["databases"][0]["database_key"]])]
    report = next(r for r in outputs if r["role"] == "primary_report")
    fmt = {"json15": "15", "tabular6": "6", "tabular7": "7"}[report["format"]]
    if report["fields"]:
        fmt += ("" if report["delimiter"] in {None, "\t"} else " delim=" + report["delimiter"]) + " " + " ".join(report["fields"])
    argv.extend(["-outfmt", fmt, "-out", report["path"]])
    return {"argv": argv, "environment": _copy(job["environment"]), "outputs": outputs}


def compile_standard_blast_database_argv(job: dict, *, input_paths: dict, database_paths: dict,
                                         output_directory: str) -> list[str]:
    """Compile exactly one selected native command; no output fields are added."""
    return _compile(job, input_paths=input_paths, database_paths=database_paths,
                    output_directory=output_directory)["argv"]


def requested_job_from_standard_blast_database(job):
    job = validate_standard_blast_database_job(job)
    compiled = _compile(job,
        input_paths={r["input_key"]: r["path"] for r in job["inputs"]},
        database_paths={r["database_key"]: r["native_paths"] for r in job["databases"]}, output_directory=".")
    return {"argv": compiled["argv"], "environment": compiled["environment"], "native_blast_standard_database": job}


def validate_standard_blast_database_requested_job(request):
    request = _copy(request)
    _schema(request, NATIVE_BLAST_STANDARD_DATABASE_REQUESTED_JOB_SCHEMA)
    if request != requested_job_from_standard_blast_database(request["native_blast_standard_database"]):
        _fail("requested_job_compiler_mismatch")
    return request


def validate_standard_blast_database_producer_manifest(manifest, *, module_root, python_executable):
    manifest = _copy(manifest)
    _schema(manifest, PRODUCER_MANIFEST_SCHEMA)
    _absolute(module_root)
    _absolute(python_executable)
    if manifest["module_root"] != module_root or manifest["python"]["path"] != python_executable:
        _fail("producer_manifest_binding_mismatch")
    package = _unique(manifest["package_files"], "relative_path")
    required = {"gene_annotation_episode/__init__.py", "gene_annotation_episode/native_blast_standard_database_driver.py",
                "gene_annotation_episode/native_blast_standard_database_contracts.py",
                "gene_annotation_episode/blast_program_context.py"}
    if not required <= package.keys():
        _fail("producer_required_package_file_missing")
    for path in package:
        _relative(path)
    _disjoint(list(package), "producer_package_path_overlap")
    runtime = _unique(manifest["runtime_files"], "path")
    for row in [manifest["python"], *runtime.values()]:
        _absolute(row["path"])
        if _inside(row["path"], module_root, equal=True):
            _fail("producer_external_file_inside_module_root")
    if python_executable in runtime:
        _fail("producer_duplicate_interpreter_file")
    _disjoint([python_executable, *runtime], "producer_external_path_overlap")
    return manifest


def _identity(identity, request, *, final):
    _schema(identity, IDENTITY_SCHEMA)
    if ((identity["execution_id"] is None) == final or identity["requested_job_sha256"] != _digest(request)
            or identity["attempt_id"] != _digest(identity["operation_key"])
            or identity["submission_token"] != _digest({k: identity[k] for k in
                ("run_id", "episode_id", "assignment_sha256", "operation_key")})):
        _fail("attempt_identity_mismatch")


_CONTROL_NAMES = ("tmp", "cache", "custody", "bundle.json", ".bundle.json.writing",
                  ".native-blast-standard-database-owner.json", "..native-blast-standard-database-owner.json.writing")


def validate_standard_blast_database_plan(plan):
    plan = _copy(plan)
    _schema(plan, PLAN_SCHEMA)
    request = validate_standard_blast_database_requested_job(plan["requested_job"])
    _identity(plan["identity"], request, final=False)
    root = plan["attempt_directory"]
    _absolute(root)
    _absolute(plan["output_directory"])
    if not _inside(plan["output_directory"], root, equal=True):
        _fail("output_directory_outside_attempt")
    _environment(plan["resource_environment"])
    _file_identity(plan["producer_manifest"])
    job = request["native_blast_standard_database"]
    compiled = _compile(job, input_paths=plan["input_paths"],
        database_paths=plan["database_paths"], output_directory=plan["output_directory"])
    paths = list(plan["input_paths"].values())
    if any(not _inside(p, root) for p in paths):
        _fail("input_capture_path_outside_attempt")
    paths += [str(PurePosixPath(r["path"]).parent) if r["path_kind"] == "prefix" else r["path"] for r in compiled["outputs"]]
    controls = [str(PurePosixPath(root) / n) for n in _CONTROL_NAMES]
    if any(_overlap(a, b) for a in paths for b in controls):
        _fail("selected_path_control_overlap")
    if any(_overlap(p, plan["producer_manifest"]["path"]) for p in paths):
        _fail("selected_path_producer_manifest_overlap")
    originals = [r["path"] for r in job["inputs"] if r["path"] != plan["input_paths"][r["input_key"]]] + [job["software"]["executable"]]
    for db in job["databases"]:
        m = db["manifest"]
        originals += [r["path"] for r in [db["manifest_file"], *m["files"], m["preparation"]["receipt"],
            *m["metadata_manifests"], *[v for _, v in _database_sidecars(db) if v is not None]]]
    if any(_overlap(p, original) for p in paths for original in originals):
        _fail("realization_overlaps_selected_original_file")
    return plan


def _effective_environment(plan):
    root = PurePosixPath(plan["attempt_directory"])
    return {**plan["resource_environment"], **plan["requested_job"]["environment"],
        **{k: str(root / "tmp") for k in ("TMPDIR", "TMP", "TEMP")},
        "XDG_CACHE_HOME": str(root / "cache"), "PYTHONDONTWRITEBYTECODE": "1"}


FAILURE_CODES = frozenset({"software_missing", "software_identity_mismatch", "input_missing",
    "input_identity_mismatch", "input_native_incompatible", "database_manifest_invalid", "database_file_missing",
    "database_identity_mismatch", "database_file_unreadable", "offline_configuration_unestablished",
    "native_start_failed", "native_nonzero_exit", "required_output_missing", "output_path_escape",
    "output_inventory_incomplete", "output_unreadable", "output_changed_during_seal",
    "producer_manifest_invalid", "producer_file_missing", "producer_file_identity_mismatch",
    "producer_file_unreadable", "producer_package_inventory_mismatch", "producer_runtime_path_mismatch",
    "producer_input_parser_unavailable"})
_TIMESTAMP = _STR
_MEASUREMENT = {"observed_sha256": _nullable(_SHA), "size_bytes": _nullable(_INT),
    "checked_at": _nullable(_TIMESTAMP), "status": {"enum": ["verified", "missing", "mismatch", "unreadable", "not_checked"]}}
_ARTIFACT_SCHEMA = _object({"artifact_key": _KEY, "input_key": _nullable(_KEY), "output_key": _nullable(_KEY),
    "database_key": _nullable(_KEY), "role": {"enum": ["query_sequence", "query_pssm", "metadata",
        "database_manifest", "preparation_receipt", "stdout", "stderr", "primary_report", "producer_manifest"]},
    "relative_path": _STR, "format": _STR, "fields": _array({"enum": sorted(TABULAR_FIELDS)}, uniqueItems=True),
    "delimiter": _nullable({"type": "string", "minLength": 1, "maxLength": 1}), "sha256": _SHA, "size_bytes": _INT,
    "content_assessment": {"const": "not_parsed"}})
_PRODUCER_VERIFICATION_SCHEMA = _object({"manifest": _nullable(PRODUCER_MANIFEST_SCHEMA),
    "manifest_observed_sha256": _nullable(_SHA), "package_inventory_exact": _nullable(_BOOL),
    "running_module_paths_match": _nullable(_BOOL),
    "checks": _array(_object({"kind": {"enum": ["python", "package", "runtime"]}, "path": _ABS, **_MEASUREMENT})),
    "status": {"enum": ["verified", "failed"]}})
NATIVE_BLAST_STANDARD_DATABASE_BUNDLE_SCHEMA = _object({"version": {"const": "native_blast_standard_database_bundle_v1"},
    "identity": IDENTITY_SCHEMA, "plan": PLAN_SCHEMA, "requested_job": NATIVE_BLAST_STANDARD_DATABASE_REQUESTED_JOB_SCHEMA,
    "program": {"enum": list(PROGRAMS)}, "mode": {"const": "database"},
    "software": _object({"selected": SOFTWARE_SCHEMA, "observed_sha256": _nullable(_SHA), "version_source": _nullable(PROVENANCE_SCHEMA)}),
    "producer_verification": _PRODUCER_VERIFICATION_SCHEMA,
    "realized_argv": _array(_STR, minItems=1), "environment": _ENV,
    "input_manifest": _array(_object({"input_key": _KEY, "original_path": _ABS, "realized_path": _ABS,
        "artifact_key": _KEY, "expected_sha256": _SHA, "observed_sha256": _SHA, "size_bytes": _INT})),
    "database_manifest": _array(_object({"database_key": _KEY, "native_paths": _array(_ABS, minItems=1),
        "manifest_artifact_key": _nullable(_KEY), "preparation_receipt_artifact_key": _nullable(_KEY),
        "metadata_manifest_artifacts": _array(_object({"identity": FILE_IDENTITY_SCHEMA, "artifact_key": _nullable(_KEY)})),
        "sidecar_artifacts": _array(_object({"role": {"enum": ["preparation_input_manifest", "offline_configuration"]},
            "identity": FILE_IDENTITY_SCHEMA, "artifact_key": _nullable(_KEY)})),
        "checks": _array(_object({"path": _ABS, "expected_sha256": _SHA, **_MEASUREMENT}))})),
    "output_manifest": _array(_object({"output_key": _KEY,
        "presence": {"enum": ["present", "missing", "not_emitted", "unknown"]},
        "artifact_keys": _array(_KEY, uniqueItems=True), "inventory_complete": _BOOL})),
    "artifacts": _array(_ARTIFACT_SCHEMA),
    "associations": _object({"query_input_key": _KEY, "selected_options": _array(_STR), "external_manifest_keys": _array(_KEY, uniqueItems=True)}),
    "process": _object({"started": _BOOL, "returncode": _nullable({"type": "integer"}),
        "started_at": _nullable(_TIMESTAMP), "finished_at": _nullable(_TIMESTAMP),
        "native_elapsed_seconds": _nullable({"type": "number", "minimum": 0})}),
    "failures": _array(_object({"code": {"enum": sorted(FAILURE_CODES)},
        "input_key": _nullable(_KEY), "database_key": _nullable(_KEY), "output_key": _nullable(_KEY),
        "artifact_key": _nullable(_KEY), "native_returncode": _nullable({"type": "integer"})}), uniqueItems=True),
    "sealed_at": _TIMESTAMP})


def _time(value):
    try:
        stamp = datetime.fromisoformat(value)
        if stamp.utcoffset() is None:
            raise ValueError
        return stamp
    except (ValueError, TypeError):
        _fail("timestamp_invalid")


def _measurement(row, expected):
    status = row["status"]
    if status == "not_checked":
        if any(row[k] is not None for k in ("observed_sha256", "size_bytes", "checked_at")):
            _fail("unchecked_file_has_measurement")
    else:
        _time(row["checked_at"])
        if status in {"verified", "mismatch"}:
            if row["observed_sha256"] is None or row["size_bytes"] is None:
                _fail("file_measurement_missing")
            matches = row["observed_sha256"] == expected["sha256"] and row["size_bytes"] == expected["size_bytes"]
            if matches != (status == "verified"):
                _fail("file_measurement_status_conflict")
        elif row["observed_sha256"] is not None or row["size_bytes"] is not None:
            _fail("unavailable_file_has_measurement")


def _producer_files(manifest):
    return [{"kind": "python", **manifest["python"]},
        *[{"kind": "package", "path": str(PurePosixPath(manifest["module_root"]) / r["relative_path"]),
            "sha256": r["sha256"], "size_bytes": r["size_bytes"]} for r in manifest["package_files"]],
        *[{"kind": "runtime", **r} for r in manifest["runtime_files"]]]


def _validate_producer_verification(bundle, artifacts, has):
    proof, plan = bundle["producer_verification"], bundle["plan"]
    started = bundle["process"]["started"]
    manifest, selected = proof["manifest"], plan["producer_manifest"]
    candidates = [r for r in artifacts.values() if r["role"] == "producer_manifest"]
    if len(candidates) > 1:
        _fail("duplicate_producer_manifest_artifact")
    capture = candidates[0] if candidates else None
    manifest_matches = (capture is not None and capture["sha256"] == selected["sha256"]
        and capture["size_bytes"] == selected["size_bytes"] and proof["manifest_observed_sha256"] == selected["sha256"])
    if capture is not None and capture["sha256"] != proof["manifest_observed_sha256"]:
        _fail("producer_manifest_observation_conflict")
    if capture is None and proof["manifest_observed_sha256"] is not None:
        _fail("producer_manifest_capture_missing")
    if manifest is None:
        if (proof["checks"] or proof["package_inventory_exact"] is not None
                or proof["running_module_paths_match"] is not None or not has("producer_manifest_invalid")):
            _fail("producer_invalid_manifest_relationship")
    else:
        validate_standard_blast_database_producer_manifest(manifest, module_root=manifest["module_root"],
            python_executable=manifest["python"]["path"])
        if _inside(selected["path"], manifest["module_root"], equal=True) or not manifest_matches or capture["format"] != "json":
            _fail("producer_manifest_identity_conflict")
        expected = {(r["kind"], r["path"]): r for r in _producer_files(manifest)}
        seen = set()
        for check in proof["checks"]:
            key = check["kind"], check["path"]
            if key not in expected or key in seen:
                _fail("producer_check_inventory_conflict")
            seen.add(key)
            _measurement(check, expected[key])
            code = {"missing": "producer_file_missing", "mismatch": "producer_file_identity_mismatch",
                    "unreadable": "producer_file_unreadable"}.get(check["status"])
            if code and not has(code):
                _fail("producer_check_failure_missing")
        if seen != expected.keys():
            _fail("producer_check_inventory_incomplete")
    for field, code in (("package_inventory_exact", "producer_package_inventory_mismatch"),
                        ("running_module_paths_match", "producer_runtime_path_mismatch")):
        if proof[field] is False and not has(code):
            _fail("producer_boolean_failure_missing")
    verified = (manifest is not None and manifest_matches and proof["package_inventory_exact"] is True
        and proof["running_module_paths_match"] is True and all(r["status"] == "verified" for r in proof["checks"]))
    if (proof["status"] == "verified") != verified or (started and not verified):
        _fail("producer_verification_status_conflict")
    if not verified and not any(f["code"].startswith("producer_") for f in bundle["failures"]):
        _fail("producer_failure_missing")


def validate_standard_blast_database_bundle(bundle, *, original_job, attempt_identity):
    """Qualify a sealed record against an independently authenticated plan hash."""
    bundle, envelope = _copy(bundle), _copy(attempt_identity)
    job = validate_standard_blast_database_job(original_job)
    _schema(bundle, NATIVE_BLAST_STANDARD_DATABASE_BUNDLE_SCHEMA)
    _schema(envelope, _object({"identity": IDENTITY_SCHEMA, "attempt_directory": _ABS, "plan_sha256": _SHA}))
    _absolute(envelope["attempt_directory"])
    plan = validate_standard_blast_database_plan(bundle["plan"])
    request = requested_job_from_standard_blast_database(job)
    _identity(envelope["identity"], request, final=True)
    if (bundle["identity"] != envelope["identity"] or _digest(plan) != envelope["plan_sha256"]
            or plan["attempt_directory"] != envelope["attempt_directory"]
            or plan["identity"] != {**envelope["identity"], "execution_id": None}
            or bundle["requested_job"] != request or plan["requested_job"] != request
            or bundle["program"] != job["program"] or bundle["mode"] != job["mode"]):
        _fail("bundle_original_attempt_mismatch")
    compiled = _compile(job, input_paths=plan["input_paths"],
        database_paths=plan["database_paths"], output_directory=plan["output_directory"])
    if bundle["realized_argv"] != compiled["argv"] or bundle["environment"] != _effective_environment(plan):
        _fail("bundle_realized_command_mismatch")
    inputs, databases, outputs = (_unique(job[field], key) for field, key in
        (("inputs", "input_key"), ("databases", "database_key"), ("outputs", "output_key")))
    artifacts = _unique(bundle["artifacts"], "artifact_key")
    _disjoint([r["relative_path"] for r in artifacts.values()], "artifact_path_overlap")
    for row in artifacts.values():
        _relative(row["relative_path"])
        if row["relative_path"] in {"bundle.json", ".native-blast-standard-database-owner.json"}:
            _fail("artifact_control_file_forbidden")
        owners = [k for k in ("input_key", "database_key", "output_key") if row[k] is not None]
        if row["role"] == "producer_manifest":
            if owners or row["format"] not in {"json", "opaque"} or row["fields"] or row["delimiter"] is not None:
                _fail("producer_artifact_contract_invalid")
        elif len(owners) != 1:
            _fail("artifact_single_owner_required")
        if owners:
            owner = owners[0]
            selected = {"input_key": inputs, "database_key": databases, "output_key": outputs}[owner]
            if row[owner] not in selected:
                _fail("artifact_owner_not_selected")
            if owner == "input_key":
                descriptor = selected[row[owner]]
                expected_path = str(PurePosixPath(plan["input_paths"][row[owner]]).relative_to(plan["attempt_directory"]))
                if (row["role"] != descriptor["role"] or row["format"] != descriptor["format"]
                        or row["relative_path"] != expected_path or row["fields"] or row["delimiter"] is not None):
                    _fail("input_artifact_contract_conflict")
            elif owner == "database_key":
                if (row["role"] not in {"database_manifest", "preparation_receipt", "metadata"}
                        or row["format"] not in ({"json", "opaque"} if row["role"] == "database_manifest" else {"opaque"})
                        or row["fields"] or row["delimiter"] is not None):
                    _fail("database_artifact_contract_conflict")
            else:
                descriptor = selected[row[owner]]
                resolved = next(r["path"] for r in compiled["outputs"] if r["output_key"] == row[owner])
                path = str(PurePosixPath(plan["attempt_directory"]) / row["relative_path"])
                if (any(row[k] != descriptor[k] for k in ("role", "format", "fields", "delimiter"))
                        or descriptor["path_kind"] == "file" and path != resolved
                        or descriptor["path_kind"] == "prefix" and not _inside(path, str(PurePosixPath(resolved).parent))):
                    _fail("output_artifact_contract_conflict")
    process, failures = bundle["process"], bundle["failures"]
    started, rc = process["started"], process["returncode"]
    sealed = _time(bundle["sealed_at"])
    if started:
        if rc is None or process["native_elapsed_seconds"] is None:
            _fail("started_process_measurements_required")
        if not _time(process["started_at"]) <= _time(process["finished_at"]) <= sealed:
            _fail("process_timestamp_order_invalid")
    elif any(process[k] is not None for k in ("returncode", "started_at", "finished_at", "native_elapsed_seconds")):
        _fail("unstarted_process_has_measurement")
    for row in failures:
        code = row["code"]
        applicable = "input_key" if code.startswith("input_") or code == "producer_input_parser_unavailable" else (
            "database_key" if code.startswith("database_") or code == "offline_configuration_unestablished" else (
                "output_key" if code.startswith("output_") or code == "required_output_missing" else None))
        for key, descriptors in (("input_key", inputs), ("database_key", databases), ("output_key", outputs)):
            if (key == applicable and row[key] not in descriptors) or (key != applicable and row[key] is not None):
                _fail("failure_descriptor_relationship_invalid")
        if row["artifact_key"] is not None:
            artifact = artifacts.get(row["artifact_key"])
            if artifact is None or (applicable is not None and artifact[applicable] != row[applicable]):
                _fail("failure_artifact_relationship_invalid")
            if applicable is None and (code != "producer_manifest_invalid" or artifact["role"] != "producer_manifest"):
                _fail("failure_unrelated_artifact")
        if code == "producer_input_parser_unavailable":
            if (row["input_key"] != job["query"]["input_key"] or row["artifact_key"] is None
                    or inputs[row["input_key"]]["role"] != "query_pssm"):
                _fail("unavailable_input_parser_relationship_invalid")
        expected_rc = rc if applicable == "output_key" or code == "native_nonzero_exit" else None
        if row["native_returncode"] != expected_rc:
            _fail("failure_returncode_conflict")
        if code == "native_nonzero_exit" and (not started or rc == 0):
            _fail("nonzero_failure_without_nonzero_exit")
        if started and (code.startswith(("input_", "database_", "software_", "producer_"))
                        or code in {"offline_configuration_unestablished", "native_start_failed"}):
            _fail("started_process_setup_failure_conflict")

    def has(code, key=None, value=None):
        return any(f["code"] == code and (key is None or f[key] == value) for f in failures)

    if started and rc != 0 and not has("native_nonzero_exit"):
        _fail("nonzero_exit_failure_missing")
    if not started and not any(f["code"] not in {"required_output_missing", "native_nonzero_exit"} for f in failures):
        _fail("unstarted_process_failure_missing")
    software = bundle["software"]
    if software["selected"] != job["software"]:
        _fail("software_selection_mismatch")
    if software["version_source"] is not None:
        _provenance(software["version_source"])
    if software["observed_sha256"] != job["software"]["sha256"]:
        code = "software_missing" if software["observed_sha256"] is None else "software_identity_mismatch"
        if started or not has(code):
            _fail("software_measurement_failure_missing")
    _validate_producer_verification(bundle, artifacts, has)
    used = {r["artifact_key"] for r in artifacts.values() if r["role"] == "producer_manifest"}
    captures = _unique(bundle["input_manifest"], "input_key")
    for key, descriptor in inputs.items():
        row = captures.get(key)
        if row is None:
            if started or not has("input_missing", "input_key", key):
                _fail("input_capture_missing")
            continue
        a = artifacts.get(row["artifact_key"])
        if (a is None or a["input_key"] != key or row["original_path"] != descriptor["path"]
                or row["realized_path"] != plan["input_paths"][key] or row["expected_sha256"] != descriptor["sha256"]
                or row["observed_sha256"] != a["sha256"] or row["size_bytes"] != a["size_bytes"]):
            _fail("input_capture_relationship_invalid")
        if row["observed_sha256"] != descriptor["sha256"] or row["size_bytes"] != descriptor["size_bytes"]:
            if started or not has("input_identity_mismatch", "input_key", key):
                _fail("input_mismatch_failure_missing")
        used.add(a["artifact_key"])
    if captures.keys() - inputs.keys():
        _fail("unselected_input_capture")
    db_captures = _unique(bundle["database_manifest"], "database_key")
    if db_captures.keys() != databases.keys():
        _fail("database_capture_inventory_mismatch")
    if [r["database_key"] for r in bundle["database_manifest"]] != [r["database_key"] for r in job["databases"]]:
        _fail("database_capture_selected_order_mismatch")

    def database_artifact(key, artifact_key, expected, role):
        failures_for_db = ("database_file_missing", "database_file_unreadable", "database_identity_mismatch",
                           "offline_configuration_unestablished")
        if role == "database_manifest":
            failures_for_db += ("database_manifest_invalid",)
        if artifact_key is None:
            if started or not any(has(c, "database_key", key) for c in failures_for_db):
                _fail("database_artifact_missing_failure")
            return
        a = artifacts.get(artifact_key)
        if a is None or a["database_key"] != key or a["role"] != role:
            _fail("database_capture_artifact_relationship_invalid")
        if role == "metadata" and artifact_key != _database_metadata_key(key, expected):
            _fail("database_metadata_artifact_identity_mismatch")
        if role == "database_manifest" and a["format"] != "json":
            if started or not has("database_manifest_invalid", "database_key", key):
                _fail("database_manifest_format_failure_missing")
        if a["sha256"] != expected["sha256"] or a["size_bytes"] != expected["size_bytes"]:
            if started or not has("database_identity_mismatch", "database_key", key):
                _fail("database_artifact_mismatch_failure_missing")
        used.add(artifact_key)

    for key, db in databases.items():
        row, manifest = db_captures[key], db["manifest"]
        if row["native_paths"] != db["native_paths"]:
            _fail("database_capture_paths_mismatch")
        database_artifact(key, row["manifest_artifact_key"], db["manifest_file"], "database_manifest")
        database_artifact(key, row["preparation_receipt_artifact_key"], manifest["preparation"]["receipt"], "preparation_receipt")
        if [r["identity"] for r in row["metadata_manifest_artifacts"]] != manifest["metadata_manifests"]:
            _fail("database_metadata_selection_mismatch")
        for metadata in row["metadata_manifest_artifacts"]:
            database_artifact(key, metadata["artifact_key"], metadata["identity"], "metadata")
        expected_sidecars = [(role, identity) for role, identity in _database_sidecars(db) if identity is not None]
        if [(r["role"], r["identity"]) for r in row["sidecar_artifacts"]] != expected_sidecars:
            _fail("database_sidecar_selection_mismatch")
        for sidecar in row["sidecar_artifacts"]:
            database_artifact(key, sidecar["artifact_key"], sidecar["identity"], "metadata")
        checks = _unique(row["checks"], "path")
        files = {r["path"]: r for r in manifest["files"]}
        if checks.keys() != files.keys():
            _fail("database_check_inventory_mismatch")
        for path, check in checks.items():
            expected = files[path]
            if check["expected_sha256"] != expected["sha256"]:
                _fail("database_check_expected_digest_conflict")
            _measurement(check, expected)
            code = {"missing": "database_file_missing", "mismatch": "database_identity_mismatch",
                    "unreadable": "database_file_unreadable"}.get(check["status"])
            if code and not has(code, "database_key", key):
                _fail("database_check_failure_missing")
            if started and check["status"] != "verified":
                _fail("started_process_unverified_database")
            if check["checked_at"] is not None and _time(check["checked_at"]) > (_time(process["started_at"]) if started else sealed):
                _fail("database_check_not_prelaunch")
    for check in bundle["producer_verification"]["checks"]:
        if check["checked_at"] is not None and _time(check["checked_at"]) > (_time(process["started_at"]) if started else sealed):
            _fail("producer_check_not_prelaunch")
    captures = _unique(bundle["output_manifest"], "output_key")
    if captures.keys() != outputs.keys():
        _fail("output_capture_inventory_mismatch")
    for key, descriptor in outputs.items():
        row = captures[key]
        for artifact_key in row["artifact_keys"]:
            a = artifacts.get(artifact_key)
            if a is None or a["output_key"] != key:
                _fail("output_capture_artifact_relationship_invalid")
            used.add(artifact_key)
        if descriptor["path_kind"] == "file" and len(row["artifact_keys"]) > 1:
            _fail("file_output_has_multiple_artifacts")
        presence = row["presence"]
        if ((presence == "present") != bool(row["artifact_keys"])
                or presence == "not_emitted" and descriptor["path_kind"] != "prefix"
                or presence == "missing" and descriptor["path_kind"] != "file"):
            _fail("output_presence_relationship_invalid")
        if presence in {"missing", "not_emitted"} and not row["inventory_complete"]:
            _fail("output_presence_requires_complete_inventory")
        if (presence == "unknown" or not row["inventory_complete"]) and not any(
                f["output_key"] == key and f["code"].startswith("output_") for f in failures):
            _fail("output_inventory_failure_missing")
        if descriptor["required"] and started and rc == 0 and not row["artifact_keys"]:
            if not has("required_output_missing", "output_key", key):
                _fail("required_output_failure_missing")
        if has("required_output_missing", "output_key", key) and row["artifact_keys"]:
            _fail("required_output_missing_with_present_artifact")
    if used != artifacts.keys():
        _fail("unassociated_artifact")
    q = job["query"]
    expected_associations = {"query_input_key": q["input_key"], "selected_options": job["options"],
        "external_manifest_keys": [r["manifest_artifact_key"] for r in bundle["database_manifest"] if r["manifest_artifact_key"] is not None]}
    if bundle["associations"] != expected_associations:
        _fail("bundle_selected_associations_mismatch")
    return bundle



# Explicit exported contract names for N -> M/R/E. Short names above remain
# available to the owned producer; consumers need no private validator imports.
NATIVE_BLAST_STANDARD_DATABASE_PLAN_SCHEMA = PLAN_SCHEMA
NATIVE_BLAST_STANDARD_PREPARED_DATABASE_SCHEMA = PREPARED_DATABASE_SCHEMA
NATIVE_BLAST_STANDARD_DATABASE_PRODUCER_MANIFEST_SCHEMA = PRODUCER_MANIFEST_SCHEMA
STANDARD_BLAST_DATABASE_PROGRAM_SPEC_SCHEMA = _object({
    "program": {"enum": list(PROGRAMS)}, "query_kinds": _array({"enum": ["sequence", "pssm"]}, minItems=1, uniqueItems=True),
    "query_formats": {"type": "object", "properties": {"sequence": {"const": "fasta"}, "pssm": {"const": "scoremat_asn_text"}},
                      "required": ["sequence"], "additionalProperties": False},
    "query_molecules": _array({"enum": ["dna", "rna", "protein"]}, minItems=1, uniqueItems=True),
    "database_kind": {"enum": ["blast_protein_sequence", "blast_nucleotide_sequence"]},
    **{name: {"enum": ["aa", "nt"]} for name in ("query_coordinate_unit", "reference_coordinate_unit", "alignment_coordinate_unit")},
    "native_program_aliases": {"type": "object", "properties": {kind: _array(_STR, minItems=1, uniqueItems=True)
        for kind in ("sequence", "pssm")}, "required": ["sequence"], "additionalProperties": False},
    "program_contexts": {"type": "object", "properties": {kind: _object({
        "execution_program": {"enum": list(PROGRAMS)}, "reported_program": _STR, "scientific_mode": {"const": "database"},
        "query_kind": {"enum": ["sequence", "pssm"]}, "reference_kind": {"const": "sequence"},
        "native_version": {"type": "null"}, "geometry_program": {"enum": list(PROGRAMS)}})
        for kind in ("sequence", "pssm")}, "required": ["sequence"], "additionalProperties": False},
    "admitted_options": _array(_object({"name": _STR, "operand_kind": _STR}), uniqueItems=True)})

__all__ = ["standard_blast_database_program_spec", "standard_blast_database_metadata_registry",
    "validate_standard_blast_database_options", "validate_standard_blast_database_job",
    "compile_standard_blast_database_argv", "requested_job_from_standard_blast_database",
    "validate_standard_blast_database_requested_job", "validate_standard_blast_database_plan",
    "validate_standard_blast_database_bundle", "validate_standard_blast_database_producer_manifest",
    "NATIVE_BLAST_STANDARD_DATABASE_JOB_SCHEMA", "NATIVE_BLAST_STANDARD_DATABASE_REQUESTED_JOB_SCHEMA",
    "NATIVE_BLAST_STANDARD_DATABASE_PLAN_SCHEMA", "NATIVE_BLAST_STANDARD_DATABASE_BUNDLE_SCHEMA",
    "NATIVE_BLAST_STANDARD_PREPARED_DATABASE_SCHEMA", "NATIVE_BLAST_STANDARD_DATABASE_PRODUCER_MANIFEST_SCHEMA",
    "STANDARD_BLAST_DATABASE_PROGRAM_SPEC_SCHEMA", "DATABASE_IDENTITY_SCHEMA", "DATABASE_OPERAND_SCHEMA",
    "FILE_IDENTITY_SCHEMA", "IDENTITY_SCHEMA", "MODEL_SCHEMA", "SOFTWARE_SCHEMA", "OUTPUT_SELECTION_SCHEMA"]
