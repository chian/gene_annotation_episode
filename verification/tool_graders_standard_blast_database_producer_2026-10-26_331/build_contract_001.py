from pathlib import Path
p=Path('gene_annotation_episode/native_blast_standard_database_contracts.py')
s=p.read_text().replace('import re\n','import re\n\nfrom .blast_program_context import resolve_blast_program_context\n',1)
s=s.replace('"size_bytes": _INT}), minItems=3),','"size_bytes": _INT}), minItems=4),')
start=s.index('    kind = {"blast_protein_sequence":',s.index('def _database(db):'))
end=s.index('    for path in db["native_paths"]:',start)
s=s[:start]+'''    if manifest["preparation"]["preparation_type"] != "sequence_database":
        _fail("database_preparation_type_mismatch")
    if not manifest["inventory_complete"]:
        _fail("database_complete_inventory_required")
'''+s[end:]
s=s.replace('if not any(p == native or (db["kind"] == "vdb" and _inside(p, native))\n                   or (db["kind"] != "vdb" and p.startswith(native + ".")) for p in files):','if not any(p.startswith(native + ".") for p in files):')
s=s.replace('    if db["kind"] == "vdb" and manifest["access"]["offline_configuration"] is None:\n        _fail("offline_configuration_unestablished")\n','')
start=s.index('_COMPILER_FLAGS =')
end=s.index('\ndef _unique(',start)
s=s[:start]+'''_COMPILER_FLAGS = frozenset({"-query", "-in_pssm", "-db", "-out", "-outfmt"})
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
    if query_kind not in ({"sequence", "pssm"} if program == "tblastn" else {"sequence"}):
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
                    delimiter != "\\t" and (delimiter.isspace() or ord(delimiter) < 32 or ord(delimiter) == 127)):
                _fail("invalid_table_delimiter")
            if "qcovus" in row["fields"] and job["program"] != "blastn":
                _fail("program_tabular_field_conflict:qcovus")
        elif row["fields"] or row["delimiter"] is not None:
            _fail("non_tabular_layout_conflict")
    _disjoint(boundaries, "output_path_overlap")
    model = job["grading_parameters"]["sequence_database_model"]
    if model is not None and model.get("function_priors") is not None:
        priors = model["function_priors"]
        if not priors or any(not key.strip() or "\\0" in key for key in priors) or not any(v > 0 for v in priors.values()):
            _fail("model_function_priors_invalid")
    _options(job)
    return job

'''+s[end:]
start=s.index('    q = job["query"]',s.index('def _compile('))
end=s.index('    return {"argv": argv',start)
s=s[:start]+'''    q = job["query"]
    argv = [job["software"]["executable"], *job["options"],
        "-query" if q["kind"] == "sequence" else "-in_pssm", inputs[q["input_key"]],
        "-db", " ".join(databases[job["databases"][0]["database_key"]])]
    report = next(r for r in outputs if r["role"] == "primary_report")
    fmt = {"json15": "15", "tabular6": "6", "tabular7": "7"}[report["format"]]
    if report["fields"]:
        fmt += ("" if report["delimiter"] in {None, "\\t"} else " delim=" + report["delimiter"]) + " " + " ".join(report["fields"])
    argv.extend(["-outfmt", fmt, "-out", report["path"]])
'''+s[end:]
pos=s.index('\ndef requested_job_from_standard_blast_database')
s=s[:pos]+'''\ndef compile_standard_blast_database_argv(job: dict, *, input_paths: dict, database_paths: dict,
                                         output_directory: str) -> list[str]:
    """Compile exactly one selected native command; no output fields are added."""
    return _compile(job, input_paths=input_paths, database_paths=database_paths,
                    output_directory=output_directory)["argv"]

'''+s[pos:]
s=s.replace('"gene_annotation_episode/native_blast_standard_database_contracts.py"}', '"gene_annotation_episode/native_blast_standard_database_contracts.py",\n                "gene_annotation_episode/blast_program_context.py"}')
s+='''\n# Explicit exported contract names for N -> M/R/E. Short names above remain
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
'''
p.write_text(s)
