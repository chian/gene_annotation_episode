"""Pure, source-qualified PSI/DELTA positive-message extraction (315/316).

Only the source-defined BLAST+ 2.17.0 tabular7 message is decoded. A sole
captured protein FASTA record can qualify query scope; no search, biological
round, membership, negative state or scientific completion is inferred.
Authentic marker-output and episode-path verification remain separate work.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import math
import re
from typing import Literal, TypedDict

from Bio import SeqIO

from . import native_blast_database_contracts as _producer
from .blast_iteration_inputs import populate_blast_iteration_sheet as _populate


_PREFIX = "blast_native_iteration_"
_CODES = frozenset("""bundle_contract_rejected report_artifact_missing
report_identity_conflict collection_artifact_conflict report_format_unsupported
report_program_conflict report_version_missing report_version_unsupported
report_encoding_invalid query_identity_conflict query_format_unsupported
query_input_invalid query_input_partial query_scope_unavailable
query_operand_conflict marker_absent marker_partial marker_duplicate
source_partial native_failed""".split())
_OPERAND = {"role", "artifact_key", "record_ordinal", "native_id", "native_title",
            "subject_ref", "molecule", "length", "selected_interval", "identity"}
_INVOCATION = {"execution_program", "scientific_mode", "resource_kind", "query_kind",
               "reference_kind", "request", "effective_options", "operands", "completion"}
_ARTIFACT = {"artifact_key", "role", "format", "fields", "delimiter", "sha256", "size_bytes"}
_MARKER = b"Search has CONVERGED!"
_HEADER = re.compile(rb"# ([A-Za-z][A-Za-z0-9_-]+)(?:[ \t]+([0-9][^\r\n]*))?")


class _Issue(TypedDict):
    code: str
    marker_index: int | None
    source_pointer: str | None
    details: dict


class _Marker(TypedDict):
    record_key: str
    byte_span: list[int]
    line_number: int
    exact_text: str
    scope: Literal["query", "unbound"]
    issue_codes: list[str]


class _Report(TypedDict):
    artifact_key: str
    source_ref: str
    sha256: str
    size_bytes: int
    format: str | None
    fields: list[str] | None
    delimiter: str | None
    native_programs: list[str]
    native_versions: list[str]
    native_text: str | None
    native_bytes_base64: str


class _Query(TypedDict):
    input_key: str | None
    artifact_key: str | None
    sha256: str
    size_bytes: int
    native_text: str | None
    native_bytes_base64: str
    record_count: int | None
    query_operand: dict | None


class _Extraction(TypedDict):
    schema: Literal["blast_native_convergence_extraction_v1"]
    status: Literal["complete", "partial", "unavailable", "incompatible"]
    report: _Report
    query: _Query
    source_context: dict
    markers: list[_Marker]
    convergence_records: list[dict]
    issues: list[_Issue]


def _fail(kind, path):
    raise ValueError(_PREFIX + kind, path)


def _copy(value, path, active=None):
    if value is None or type(value) in (str, int, bool):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if type(value) in (list, dict) and (type(value) is list or all(type(k) is str for k in value)):
        active = set() if active is None else active
        if id(value) in active:
            _fail("finite_json_required", path)
        active.add(id(value))
        try:
            if type(value) is list:
                return [_copy(v, f"{path}/{i}", active) for i, v in enumerate(value)]
            return {k: _copy(v, path + "/" + k.replace("~", "~0").replace("/", "~1"), active)
                    for k, v in value.items()}
        finally:
            active.remove(id(value))
    _fail("finite_json_required", path)


def _type(condition, path):
    if not condition:
        _fail("input_type_invalid", path)


def _keys(value, fields, path):
    _type(type(value) is dict, path)
    if set(value) != fields:
        _fail("input_fields_invalid", path)


def _text(value):
    return type(value) is str and bool(value.strip()) and "\0" not in value


def _integer(value, minimum=0):
    return type(value) is int and value >= minimum


def _operand(value, path):
    _keys(value, _OPERAND, path)
    _type(value["role"] in ("query", "subject", "database", "profile", "msa", "checkpoint")
          and value["molecule"] in ("protein", "dna", "rna", "unknown"), path)
    for name in ("artifact_key", "subject_ref", "native_id", "native_title"):
        _type(value[name] is None or _text(value[name]), path + "/" + name)
    for name, minimum in (("record_ordinal", 0), ("length", 1)):
        _type(value[name] is None or _integer(value[name], minimum), path + "/" + name)
    interval = value["selected_interval"]
    _type(interval is None or type(interval) is list and len(interval) == 2
          and all(_integer(v) for v in interval) and interval[0] < interval[1]
          and (value["length"] is None or interval[1] <= value["length"]), path + "/selected_interval")
    if value["identity"] is not None:
        identity = value["identity"]
        _keys(identity, {"namespace", "value", "version"}, path + "/identity")
        _type(_text(identity["namespace"]) and _text(identity["value"])
              and (identity["version"] is None or _text(identity["version"])), path + "/identity")


def _collection(value):
    """Check fields used here and reuse the public 311 closed collection port."""
    _keys(value, {"schema", "invocation", "artifacts", "searches", "issues"}, "/collection")
    _type(value["schema"] == "blast_report_collection_v1", "/collection/schema")
    inv = value["invocation"]
    _keys(inv, _INVOCATION, "/collection/invocation")
    for name in ("execution_program", "scientific_mode", "resource_kind", "query_kind", "reference_kind"):
        _type(_text(inv[name]), "/collection/invocation/" + name)
    for name in ("request", "effective_options"):
        _type(type(inv[name]) is dict, "/collection/invocation/" + name)
    _keys(inv["completion"], {"native_returncode", "producer_complete"}, "/collection/invocation/completion")
    for name, kind in (("native_returncode", int), ("producer_complete", bool)):
        _type(inv["completion"][name] is None or type(inv["completion"][name]) is kind,
              "/collection/invocation/completion/" + name)
    _type(type(inv["operands"]) is list, "/collection/invocation/operands")
    for i, operand in enumerate(inv["operands"]):
        _operand(operand, f"/collection/invocation/operands/{i}")
    for name in ("artifacts", "searches", "issues"):
        _type(type(value[name]) is list, "/collection/" + name)
    for i, artifact in enumerate(value["artifacts"]):
        path = f"/collection/artifacts/{i}"
        _type(type(artifact) is dict, path)
        _keys(artifact, _ARTIFACT | ({"members"} if "members" in artifact else set()), path)
        _type(all(_text(artifact[k]) for k in ("artifact_key", "role", "format"))
              and type(artifact["sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", artifact["sha256"]) is not None
              and _integer(artifact["size_bytes"]), path)
        _type(artifact["fields"] is None or type(artifact["fields"]) is list
              and all(_text(v) for v in artifact["fields"]), path + "/fields")
        _type(artifact["delimiter"] is None or type(artifact["delimiter"]) is str
              and len(artifact["delimiter"]) == 1 and artifact["delimiter"] not in "\0\r\n", path + "/delimiter")
    if (inv["execution_program"] in ("psiblast", "deltablast") and inv["scientific_mode"] == "database"
            and inv["reference_kind"] == "sequence" and inv["query_kind"] in
            (("sequence", "msa", "pssm") if inv["execution_program"] == "psiblast" else ("sequence",))):
        try:
            _populate(value, report_sources=[], query_bindings=[], search_bindings=[], pssm_sheets=[],
                checkpoint_bindings=[], sequence_metadata=[], profile_metadata=[], comparison_pairs=[],
                inclusion_records=[], convergence_records=[])
        except ValueError as error:
            kind = "input_type_invalid" if error.args[0] == "blast_iteration_input_type_invalid" else "input_fields_invalid"
            _fail(kind, error.args[1] if len(error.args) > 1 else "/collection")


def _bytes(raw):
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = None
    return dict(sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw),
                native_text=text, native_bytes_base64=base64.b64encode(raw).decode("ascii"))


def _lines(raw):
    """Physical LF boundaries only; do not normalize CR, Unicode or byte offsets."""
    offset = 0
    for number, part in enumerate(raw.split(b"\n"), 1):
        complete = offset + len(part) < len(raw)
        line = part + (b"\n" if complete else b"")
        if line:
            body = part[:-1] if complete and part.endswith(b"\r") else part
            yield number, offset, offset + len(line), body, line, complete
        offset += len(line)


def _fasta(text, add):
    """Read every yielded record; retain diagnostics rather than repairing input."""
    records, errors, preamble, seen_header = [], [], [], False
    if text is None:
        add("query_input_invalid", pointer="/query/native_bytes_base64", reason="utf8_required")
        return None, False, []
    for number, line in enumerate(text.splitlines(), 1):
        if line.startswith(">"):
            seen_header = True
            if not line[1:].strip():
                errors.append({"line_number": number, "reason": "empty_header"})
        elif line.strip():
            if not seen_header:
                preamble.append({"line_number": number, "exact_text": line})
            elif re.fullmatch(r"[A-Za-z* \t]*", line) is None:
                errors.append({"line_number": number, "reason": "non_protein_sequence_text", "exact_text": line})
    finished = True
    try:
        # No warning filter: Biopython's own malformed/preamble diagnostics are
        # not suppressed. Blank prefix lines do not erase nonblank preambles.
        for ordinal, record in enumerate(SeqIO.parse(io.StringIO(text), "fasta")):
            records.append(dict(record_ordinal=ordinal, native_id=record.id,
                native_title=record.description, sequence=str(record.seq), length=len(record.seq)))
    except (ValueError, UnicodeError) as error:
        finished = False
        errors.append({"reason": "fasta_parser_rejected", "error_type": type(error).__name__, "error": str(error)})
    empty = [r["record_ordinal"] for r in records if not r["length"]]
    valid = finished and bool(records) and not (errors or preamble or empty)
    if not valid:
        add("query_input_invalid", pointer="/query/native_text", records=records, errors=errors,
            nonblank_preamble=preamble, empty_record_ordinals=empty, parsing_finished=finished)
    if not finished or empty:
        add("query_input_partial", pointer="/query/native_text", records=records,
            empty_record_ordinals=empty, parsing_finished=finished)
    return len(records) if finished else None, valid, records


def extract_blast_tabular7_convergence(report_contents: bytes, *, artifact_key: str, source_ref: str,
        original_job: dict, bundle: dict, attempt_identity: dict, query_contents: bytes,
        query_operand: dict, collection: dict) -> dict:
    """Return the closed 315 extraction, preserving bytes even on source failure.

    Counts are counts of fully parsed FASTA records, including malformed empty
    records when yielded; a parser exception makes the total unknown. Spans are
    zero-based half-open report byte locations including LF/CRLF; line numbers
    are one-based physical locations. The sole native boolean is explicit true,
    with no probability, timing, biological-round or completion interpretation.
    Source refs and attempt envelopes are supplied by authenticated acquisition;
    this pure function cannot authenticate an external service or read a ref.
    """
    for value, path in ((report_contents, "/report_contents"), (query_contents, "/query_contents")):
        _type(type(value) is bytes, path)
    for value, path in ((artifact_key, "/artifact_key"), (source_ref, "/source_ref")):
        _type(_text(value), path)
    values = {}
    for name, value in (("original_job", original_job), ("bundle", bundle), ("attempt_identity", attempt_identity),
                        ("query_operand", query_operand), ("collection", collection)):
        _type(type(value) is dict, "/" + name)
        values[name] = _copy(value, "/" + name)
    original_job, bundle, attempt_identity = (values[k] for k in ("original_job", "bundle", "attempt_identity"))
    query_operand, collection = values["query_operand"], values["collection"]
    _operand(query_operand, "/query_operand")
    _collection(collection)
    result: _Extraction = dict(schema="blast_native_convergence_extraction_v1", status="unavailable",
        report=dict(artifact_key=artifact_key, source_ref=source_ref, **_bytes(report_contents),
                    format=None, fields=None, delimiter=None, native_programs=[], native_versions=[]),
        query=dict(input_key=None, artifact_key=None, **_bytes(query_contents), record_count=None, query_operand=None),
        source_context=dict(original_job=original_job, bundle=bundle, attempt_identity=attempt_identity),
        markers=[], convergence_records=[], issues=[])
    incompatible, report_ok, scope_ok, partial = False, True, True, False

    def add(code, *, pointer=None, marker=None, **details):
        assert code in _CODES
        result["issues"].append(dict(code=_PREFIX + code, marker_index=marker,
            source_pointer=pointer, details=details))

    try:
        checked = _producer.validate_native_blast_database_bundle(bundle, original_job=original_job,
                                                                  attempt_identity=attempt_identity)
    except ValueError as error:
        add("bundle_contract_rejected", pointer="/source_context/bundle", error_code=error.args[0],
            error_args=list(error.args))
        incompatible, report_ok, scope_ok = True, False, False
        checked = None

    report, query, inv = result["report"], result["query"], collection["invocation"]
    if report["native_text"] is None:
        report_ok = False
        add("report_encoding_invalid", pointer="/report/native_bytes_base64")
    if checked is not None:
        selected = next(r for r in original_job["outputs"] if r["role"] == "primary_report")
        report.update({k: _copy(selected[k], "/report/" + k) for k in ("format", "fields", "delimiter")})
        capture = next((a for a in checked["artifacts"] if a["artifact_key"] == artifact_key), None)
        output = next(o for o in checked["output_manifest"] if o["output_key"] == selected["output_key"])
        if capture is None or not output["artifact_keys"]:
            add("report_artifact_missing", pointer="/source_context/bundle/output_manifest", artifact_key=artifact_key)
            report_ok = False
        elif (capture["role"] != "primary_report" or capture["output_key"] != selected["output_key"]
                or output["artifact_keys"] != [artifact_key]
                or any(capture[k] != report[k] for k in ("sha256", "size_bytes", "format", "fields", "delimiter"))):
            add("report_identity_conflict", pointer="/report", supplied_sha256=report["sha256"],
                supplied_size_bytes=report["size_bytes"], capture=capture)
            incompatible, report_ok = True, False
        matching = [a for a in collection["artifacts"] if a["artifact_key"] == artifact_key]
        if (len(matching) != 1 or any(matching[0][k] != report[k] for k in
                ("sha256", "size_bytes", "format", "delimiter"))
                or matching[0]["fields"] != (None if report["format"] == "json15" else report["fields"])
                or matching[0]["role"] != "primary_report"):
            add("collection_artifact_conflict", pointer="/collection/artifacts", artifacts=matching)
            incompatible, report_ok = True, False
        if (report["format"] != "tabular7" or report["delimiter"] != "\t"
                or not {"qseqid", "sseqid"} <= set(report["fields"])):
            add("report_format_unsupported", pointer="/report", format=report["format"],
                fields=report["fields"], delimiter=report["delimiter"])
            report_ok = False
        if original_job["program"] not in ("psiblast", "deltablast"):
            add("report_format_unsupported", pointer="/source_context/original_job/program", program=original_job["program"])
            report_ok = False
        if (inv["execution_program"] != original_job["program"] or inv["scientific_mode"] != original_job["mode"]
                or inv["query_kind"] != original_job["query"]["kind"]
                or original_job["program"] in ("psiblast", "deltablast") and inv["reference_kind"] != "sequence"
                or inv["request"] != checked["requested_job"]):
            add("collection_artifact_conflict", pointer="/collection/invocation", reason="selected_invocation_conflict")
            incompatible, report_ok = True, False
        if (inv["completion"]["native_returncode"] is not None
                and inv["completion"]["native_returncode"] != checked["process"]["returncode"]):
            add("collection_artifact_conflict", pointer="/collection/invocation/completion", reason="native_returncode_conflict")
            incompatible, report_ok = True, False
        if (capture is not None and capture["role"] == "primary_report"
                and (not checked["process"]["started"]
                     or checked["software"]["observed_sha256"] != original_job["software"]["sha256"])):
            add("report_identity_conflict", pointer="/source_context/bundle/process", reason="native_execution_unestablished")
            incompatible, report_ok = True, False
        if checked["process"]["returncode"] not in (None, 0):
            add("native_failed", pointer="/source_context/bundle/process", native_returncode=checked["process"]["returncode"])
            partial = True
        if checked["failures"] or not output["inventory_complete"] or inv["completion"]["producer_complete"] is not True:
            add("source_partial", pointer="/source_context/bundle", failures=checked["failures"],
                inventory_complete=output["inventory_complete"], producer_complete=inv["completion"]["producer_complete"])
            partial = True
        qkey = original_job["query"]["input_key"]
        query["input_key"] = qkey
        descriptor = next(r for r in original_job["inputs"] if r["input_key"] == qkey)
        qc = next((r for r in checked["input_manifest"] if r["input_key"] == qkey), None)
        qa = next((r for r in checked["artifacts"] if qc is not None and r["artifact_key"] == qc["artifact_key"]), None)
        query["artifact_key"] = qc["artifact_key"] if qc else None
        if (qc is None or qa is None or any(descriptor[k] != query[k] or qa[k] != query[k] for k in ("sha256", "size_bytes"))
                or qc["observed_sha256"] != query["sha256"] or qc["size_bytes"] != query["size_bytes"]):
            add("query_identity_conflict", pointer="/query", supplied_sha256=query["sha256"],
                supplied_size_bytes=query["size_bytes"], selected=descriptor, capture=qc)
            incompatible, report_ok, scope_ok = True, False, False
        if original_job["query"]["kind"] != "sequence" or descriptor["format"] != "fasta":
            add("query_format_unsupported", pointer="/source_context/original_job/query", kind=original_job["query"]["kind"], format=descriptor["format"])
            scope_ok = False
        else:
            count, valid, records = _fasta(query["native_text"], add)
            query["record_count"] = count
            scope_ok &= valid and count == 1
            if not valid or count != 1:
                add("query_scope_unavailable", pointer="/query", record_count=count, records=records)
            options = original_job["options"]
            selected_interval = None
            if "-query_loc" in options:
                start, end = map(int, options[options.index("-query_loc") + 1].split("-"))
                selected_interval = [start - 1, end]
            conflicts = [k for k, expected in (("role", "query"), ("artifact_key", query["artifact_key"]),
                ("record_ordinal", 0), ("molecule", "protein"), ("selected_interval", selected_interval))
                if query_operand[k] != expected]
            if query_operand not in inv["operands"]:
                conflicts.append("original_query_operand")
            if valid and count == 1:
                if query_operand["length"] != records[0]["length"]:
                    conflicts.append("length")
                for name in ("native_id", "native_title"):
                    if query_operand[name] is not None and query_operand[name] != records[0][name]:
                        conflicts.append(name)
            if conflicts:
                add("query_operand_conflict", pointer="/query_operand", fields=conflicts, query_operand=query_operand)
                incompatible, scope_ok = True, False
        if scope_ok:
            query["query_operand"] = _copy(query_operand, "/query_operand")

    candidates = []
    for number, start, end, body, line, complete in _lines(report_contents):
        if match := _HEADER.fullmatch(body):
            report["native_programs"].append(match[1].decode("ascii"))
            if match[2] is not None:
                try:
                    report["native_versions"].append(match[2].decode("utf-8"))
                except UnicodeDecodeError:
                    pass  # Original bytes are retained; global decoding blocks the observation.
        if complete and body == _MARKER:
            candidates.append((number, start, end, line, True))
        elif (not complete and body and _MARKER.startswith(body.removesuffix(b"\r"))
              and body.startswith(b"Search has ")):
            candidates.append((number, start, end, line, False))
    if checked is not None and report["native_programs"] and any(p != original_job["program"].upper() for p in report["native_programs"]):
        add("report_program_conflict", pointer="/report/native_programs", selected_program=original_job["program"], native_programs=report["native_programs"])
        incompatible, report_ok = True, False
    if not report["native_versions"] or len(report["native_versions"]) != len(report["native_programs"]):
        add("report_version_missing", pointer="/report/native_versions")
        report_ok = False
    if (any(v != "2.17.0+" for v in report["native_versions"])
            or checked is not None and original_job["software"]["engine_version"] not in (None, "2.17.0+")):
        add("report_version_unsupported", pointer="/report/native_versions", native_versions=report["native_versions"],
            selected_version=original_job.get("software", {}).get("engine_version"))
        report_ok = False
    full_count = sum(c[-1] for c in candidates)
    if not full_count:
        add("marker_absent", pointer="/report/native_text")
    if full_count > 1:
        add("marker_duplicate", pointer="/markers", occurrence_count=full_count)
    for index, (number, start, end, line, complete) in enumerate(candidates):
        # A rejected bundle may still contain an attempt label. It identifies
        # only an untrusted retained candidate, never an admitted observation.
        identity = bundle.get("identity")
        attempt_id = identity.get("attempt_id") if type(identity) is dict else None
        token = json.dumps(["v1", attempt_id, artifact_key, report["sha256"], start, end],
                           ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        key = "blast-native-convergence:" + hashlib.sha256(token.encode("utf-8")).hexdigest()
        if not complete:
            add("marker_partial", pointer="/report/native_text", marker=index, byte_span=[start, end], line_number=number)
            partial = True
        scoped = report_ok and scope_ok and complete
        codes = [i["code"] for i in result["issues"] if i["marker_index"] in (None, index)]
        result["markers"].append(dict(record_key=key, byte_span=[start, end], line_number=number,
            exact_text=line.decode("ascii"), scope="query" if scoped else "unbound", issue_codes=list(dict.fromkeys(codes))))
        if complete and report_ok:
            result["convergence_records"].append(dict(record_key=key, search_key=None,
                query_operand=_copy(query_operand, "/query_operand") if scoped else None, native_converged=True,
                evidence=dict(origin="native_extractor_output", source=dict(source_ref=source_ref, pointer=""),
                    source_format="ncbi_blastplus_2.17.0_tabular7", original_record=report["native_text"],
                    extractor=dict(module="gene_annotation_episode.blast_native_iteration_records",
                                   function="extract_blast_tabular7_convergence", version="1"))))
    if incompatible:
        result["status"] = "incompatible"
    elif report_ok and scope_ok and full_count:
        result["status"] = "partial" if partial else "complete"
    return result


__all__ = ["extract_blast_tabular7_convergence"]
