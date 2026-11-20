"""The A101 all-vs-all BLAST job: a set of sequences searched against itself, compiled to the real command.

The job names two operands, both FASTA sets. The subject operand is always the whole set. The query operand is the
whole set (one chunk) or one contiguous chunk of it; the job declares which, so a large run is several jobs whose
results merge. The job declares one tabular report and nothing else: no stdout or stderr is declared, honoured or
checked. The report carries both sequence lengths, which the graph needs for coverage in both directions.

The analysis kind ``all_vs_all`` is derived from this job by the one kind function (``blast_analysis_kind``): the
subject operand is the declared whole set, the query operand is that set or a declared slice of it, and the set has at
least two records. The commission also declares the kind; the two must agree or the commission fails with its error.

Controlled values only: the program from a fixed set, three numeric search parameters in fixed ranges, record
digests and counts. The compiler writes every option token; a caller writes none. This module reads the shared
native BLAST helpers (digest, schema check, path checks, option validation) and changes none of them.
"""
from __future__ import annotations

import re

from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.native_blast_contracts import (
    RESERVED_ENVIRONMENT, _absolute, _options, _relative, _schema, finite_json_copy, native_blast_digest)

VERSION = "native_blast_all_vs_all_job_v1"
PROGRAMS = ("blastp", "blastn")
REPORT_FIELDS = ("qaccver", "saccver", "pident", "nident", "length", "mismatch", "gapopen",
                 "qstart", "qend", "sstart", "send", "qlen", "slen", "evalue", "bitscore")
REPORT_PATH = "graph.tsv"

_STR = {"type": "string", "minLength": 1, "pattern": "^[^\\u0000]+$"}
_SHA = {"type": "string", "pattern": "^[0-9a-fA-F]{64}$"}
_COUNT = {"type": "integer", "minimum": 0}


def _object(properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


_OPERAND = _object({"role": {"enum": ["query_set", "subject_set"]},
                    "path": {"type": "string", "pattern": "^/[^\\u0000\\n\\r]+$"}, "format": {"const": "fasta"},
                    "sha256": _SHA, "size_bytes": _COUNT, "record_count": {"type": "integer", "minimum": 1},
                    "artifact_ref": {"anyOf": [_STR, {"type": "null"}]}})
NATIVE_JOB_SCHEMA = _object({
    "version": {"const": VERSION}, "program": {"enum": list(PROGRAMS)}, "mode": {"const": "all_vs_all"},
    "software": _object({"executable": {"type": "string", "pattern": "^/[^\\u0000\\n\\r]+$"}, "sha256": _SHA,
                         "engine_version": {"anyOf": [_STR, {"type": "null"}]}}),
    "environment": {"type": "object", "additionalProperties": {"type": "string"}},
    "operands": {"type": "array", "minItems": 2, "maxItems": 2, "items": _OPERAND},
    "set": _object({"sha256": _SHA, "record_count": {"type": "integer", "minimum": 2},
                    "total_letters": {"type": "integer", "minimum": 2}}),
    "chunk": _object({"index": _COUNT, "count": {"type": "integer", "minimum": 1},
                      "first_ordinal": _COUNT, "last_ordinal": _COUNT}),
    "parameters": _object({"evalue": {"type": "number", "exclusiveMinimum": 0, "maximum": 1000},
                           "max_target_seqs": {"type": "integer", "minimum": 1, "maximum": 100000},
                           "max_hsps": {"type": "integer", "minimum": 1, "maximum": 10}}),
    "metadata": {"type": "object"},
})
REQUESTED_JOB_SCHEMA = _object({
    "argv": {"type": "array", "minItems": 1, "items": _STR},
    "environment": {"type": "object", "additionalProperties": {"type": "string"}},
    "native_blast_all_vs_all": NATIVE_JOB_SCHEMA,
})


def _fail(code):
    raise ValueError("native_blast_all_vs_all_" + code)


def validate_job(value):
    """The job, checked in full: schema, paths, environment, set and chunk coherence, and the compiled options."""
    job = finite_json_copy(value)
    _schema(job, NATIVE_JOB_SCHEMA)
    _absolute(job["software"]["executable"])
    for key, item in job["environment"].items():
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) or "\0" in item:
            _fail("invalid_environment")
        if key in RESERVED_ENVIRONMENT:
            _fail("compiler_owned_environment:" + key)
    roles = {row["role"]: row for row in job["operands"]}
    if set(roles) != {"query_set", "subject_set"} or len(job["operands"]) != 2:
        _fail("query_and_subject_set_required")
    for row in job["operands"]:
        _absolute(row["path"])
    whole, chunk, subject, query = job["set"], job["chunk"], roles["subject_set"], roles["query_set"]
    if subject["sha256"] != whole["sha256"] or subject["record_count"] != whole["record_count"]:
        _fail("subject_operand_is_not_the_whole_set")
    if not 0 <= chunk["index"] < chunk["count"] or chunk["count"] > whole["record_count"]:
        _fail("chunk_index_or_count_invalid")
    if not 0 <= chunk["first_ordinal"] <= chunk["last_ordinal"] < whole["record_count"]:
        _fail("chunk_range_invalid")
    if query["record_count"] != chunk["last_ordinal"] - chunk["first_ordinal"] + 1:
        _fail("query_operand_record_count_conflicts_with_chunk")
    if chunk["count"] == 1 and (query["sha256"] != whole["sha256"] or chunk["first_ordinal"] != 0
                                or chunk["last_ordinal"] != whole["record_count"] - 1):
        _fail("single_chunk_must_be_the_whole_set")
    if chunk["count"] > 1 and query["sha256"] == whole["sha256"]:
        _fail("several_chunks_need_a_slice_as_query")
    _options({"program": job["program"], "options": _options_tokens(job)})
    return job


def _options_tokens(job):
    """Every option token of the search, written here from the controlled parameters."""
    values = job["parameters"]
    tokens = ["-evalue", format(values["evalue"], ".12g"), "-max_target_seqs", str(values["max_target_seqs"])]
    if "max_hsps" in values:
        tokens += ["-max_hsps", str(values["max_hsps"])]
    return tokens


def compile_job(job):
    """The command, its environment and the one declared output of a valid job."""
    job = validate_job(job)
    paths = {row["role"]: row["path"] for row in job["operands"]}
    argv = [job["software"]["executable"], *_options_tokens(job), "-query", paths["query_set"],
            "-subject", paths["subject_set"], "-outfmt", "6 " + " ".join(REPORT_FIELDS), "-out", REPORT_PATH]
    return {"argv": argv, "environment": dict(job["environment"]),
            "outputs": [{"role": "tabular_report", "format": "tabular6", "relative_path": REPORT_PATH,
                         "fields": list(REPORT_FIELDS), "delimiter": "\t"}]}


def requested_job_from_native(job):
    job = validate_job(job)
    compiled = compile_job(job)
    return {"argv": compiled["argv"], "environment": compiled["environment"], "native_blast_all_vs_all": job}


def validate_requested_job(value):
    request = finite_json_copy(value)
    _schema(request, REQUESTED_JOB_SCHEMA)
    if request != requested_job_from_native(request["native_blast_all_vs_all"]):
        _fail("requested_job_compiler_mismatch")
    return request


def search_space(job):
    """What an E-value of this search is relative to: the number of subject sequences and their total letters,
    read from the job's declared whole set."""
    whole = validate_job(job)["set"]
    return {"sequence_count": whole["record_count"], "total_letters": whole["total_letters"]}


def job_digest(job):
    return native_blast_digest(validate_job(job))


__all__ = ["PROGRAMS", "REPORT_FIELDS", "REPORT_PATH", "VERSION", "compile_job", "job_digest",
           "requested_job_from_native", "search_space", "validate_job", "validate_requested_job"]
