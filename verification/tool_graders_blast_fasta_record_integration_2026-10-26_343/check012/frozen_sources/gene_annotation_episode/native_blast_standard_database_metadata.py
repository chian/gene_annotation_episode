"""Supplied-byte preparation and direct standard BLAST database sheet population.

The accepted 327 contract (including additive 002) owns these ports.  They do
no acquisition, file access, execution, scoring or episode work.  ``contents``
is keyed by artifact_ref for both captured and explicitly retained sources;
``subject_contents`` is keyed by sequence_artifact_ref.  Paths are audit data.

Prepared records keep the original descriptor, native bytes (hex), original
ordinal, normalized symbols and SHA256 separately.  Lengths and selections are
in full original nt/aa coordinates, never traceback-column units.  Proofs are
full supplied sequences, not HSP fragments.  The public 303 sheet and separate
calculators retain all numerical meanings; this module adds no scoring model.
"""
from __future__ import annotations

from copy import deepcopy
from functools import wraps
import hashlib
import json
import math
import re

from jsonschema import Draft202012Validator

from .blast_program_context import resolve_blast_program_context
from .blast_pssm_inputs import read_blast_pssm
from .blast_pssm_master_inputs import extract_blast_pssm_master_metadata
from .blast_sequence_database import populate_blast_sequence_database_sheet
from .blast_fasta_record_identity import blast_record_identity
from .domain import parse_sequences
from .native_blast_database_metadata import (
    metadata_schema_registry, validate_native_blast_database_metadata_payload,
    _schema_for, _SEQUENCE_V2, _record_address_status, _record_relation_failed,
)
from .native_blast_standard_database_contracts import (
    requested_job_from_standard_blast_database, standard_blast_database_program_spec,
    validate_standard_blast_database_bundle, validate_standard_blast_database_job,
    validate_standard_blast_database_options,
)


PREPARED_INPUTS_SCHEMA = "native_blast_standard_database_prepared_inputs_v1"
SHEET_SET_SCHEMA = "native_blast_standard_database_sheet_set_v1"
_PREFIX = "native_blast_standard_database_"
_TUPLES = {("query_identity", "native_blast_database_query_metadata_v1"),
           ("sequence_database", "native_blast_database_sequence_metadata_v1"),
           ("sequence_database", _SEQUENCE_V2)}
_PREPARED = {"schema", "invocation", "query_records", "pssm_sheets", "metadata",
             "resolved_documents", "source_relations", "sequence_proofs", "issues"}
_SHEETS = {"schema", "collection", "prepared_inputs", "search_bindings", "sequence",
           "pssm", "metadata_parse_results", "metadata_binding_results", "issues"}
_BINDING = {"binding", "status", "origin", "input_pointers", "issues"}
_SEQUENCE = {"search_key", "reference_metadata", "description_bindings", "sequence_identity_bindings",
             "target_context", "database_profile", "input_pointers", "issues"}
_KEY = {"artifact_key", "member_ordinal", "report_index", "search_pointer"}
_OWNER = ("input_key", "consumer", "schema_id")
_DESCRIPTOR = {*_OWNER, "artifact_ref", "sha256", "size_bytes", "origin"}
_RECORD = {"input_key", "artifact_key", "artifact_ref", "record_ordinal", "native_id", "native_title",
           "sequence", "molecule", "length", "sequence_sha256", "selected_interval", "subject_ref", "binding_status"}
_ALPHABETS = {"protein": "ABCDEFGHIKLMNPQRSTVWXYZJUO*", "dna": "ACGTRYSWKMBDHVN",
              "rna": "ACGURYSWKMBDHVN"}


def _fail(code):
    raise ValueError(_PREFIX + code)


def _saved_validator(function):
    @wraps(function)
    def checked(value):
        try:
            return function(value)
        except (KeyError, IndexError, TypeError, AttributeError):
            _fail("saved_structure_invalid")
    return checked


def _copy(value):
    if value is None or type(value) in (str, int, bool):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if type(value) is list:
        return [_copy(v) for v in value]
    if type(value) is dict and all(type(k) is str for k in value):
        return {k: _copy(v) for k, v in value.items()}
    _fail("finite_json_required")


def _token(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _keys(value, keys, code):
    if type(value) is not dict or set(value) != set(keys):
        _fail(code)


def _text(value):
    return type(value) is str and bool(value) and "\0" not in value


def _integer(value, minimum=0):
    return type(value) is int and value >= minimum


def _pointer(value):
    return type(value) is str and (not value or value.startswith("/")) and re.search(r"~(?![01])", value) is None


def _at(value, pointer):
    if not _pointer(pointer):
        raise ValueError("pointer_invalid")
    for part in pointer.split("/")[1:]:
        part = part.replace("~1", "/").replace("~0", "~")
        if type(value) is list:
            if re.fullmatch(r"0|[1-9][0-9]*", part) is None:
                raise ValueError("pointer_index_invalid")
            value = value[int(part)]
        elif type(value) is dict:
            value = value[part]
        else:
            raise ValueError("pointer_unresolved")
    return value


def _decode(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError("duplicate_json_key")
            value[key] = item
        return value
    return _copy(json.loads(raw, object_pairs_hook=pairs))


def _owner(descriptor):
    return {k: descriptor[k] for k in _OWNER}


def _issue(code, pointer="", *, descriptor=None, search_key=None, detail=None):
    return dict(code=_PREFIX + code, pointer=pointer,
                descriptor=None if descriptor is None else _owner(descriptor),
                search_key=deepcopy(search_key), detail_code=detail or code)


def _provenance(source, pointer):
    return dict(source_ref=source, pointer=pointer)


def _unique(rows):
    return list({_token(row): row for row in rows}.values())


def _original(validation, pointer):
    mappings = [r for r in validation["normalization_map"] if pointer == r["normalized_pointer"]
                or pointer.startswith(r["normalized_pointer"] + "/")]
    if not mappings:
        return pointer
    row = max(mappings, key=lambda r: len(r["normalized_pointer"]))
    return row["payload_pointer"] + pointer[len(row["normalized_pointer"]):]


def _valid(prepared, consumer):
    return [v for v in prepared["metadata"] if v["consumer"] == consumer and v["status"] == "valid"
            and v["normalized"] is not None]


def _metadata_pointers(prepared, validation, pointer):
    """Retain all original source aliases for one identical metadata content."""
    return _unique([_provenance(r["catalog"]["source_ref"], pointer)
        for r in prepared["resolved_documents"] if r["catalog"]["artifact_ref"] == validation["artifact_ref"]
        and r["catalog"]["sha256"] == validation["sha256"]])


def _validate_descriptor(value):
    _keys(value, _DESCRIPTOR, "metadata_descriptor_fields_invalid")
    if (any(not _text(value[k]) for k in (*_OWNER, "artifact_ref")) or
            type(value["sha256"]) is not str or re.fullmatch(r"[a-f0-9]{64}", value["sha256"]) is None or
            not _integer(value["size_bytes"]) or value["origin"] not in {"original_job_input", "selected_results_input"}):
        _fail("metadata_descriptor_invalid")


def _query_descriptor(job):
    return dict(input_key=job["query"]["input_key"], consumer="query_identity",
                schema_id="native_blast_database_query_metadata_v1")


class _Supplied:
    """Checked supplied bytes; no path has execution or acquisition meaning."""
    def __init__(self, catalog, contents, bundle):
        _keys(catalog, {"bundle_source_ref", "bundle_artifact_ref", "bundle_sha256", "entries", "retained_sources"},
              "artifact_catalog_fields_invalid")
        if (type(contents) is not dict or any(not _text(k) or type(v) is not bytes for k, v in contents.items())
                or not all(_text(catalog[k]) for k in ("bundle_source_ref", "bundle_artifact_ref"))
                or type(catalog["bundle_sha256"]) is not str
                or re.fullmatch(r"[0-9a-f]{64}", catalog["bundle_sha256"]) is None):
            _fail("artifact_catalog_identity_invalid")
        self.catalog, self.contents = deepcopy(catalog), contents
        self.entries, self.by_ref, self.json_cache, self.fasta_cache = {}, {}, {}, {}
        if any(type(catalog[k]) is not list or any(type(r) is not dict for r in catalog[k]) for k in ("entries", "retained_sources")):
            _fail("artifact_catalog_arrays_invalid")
        originals = {a["artifact_key"]: a for a in bundle["artifacts"]}
        for row in catalog["entries"]:
            key = row["artifact_key"]
            if key in self.entries:
                _fail("artifact_key_duplicate")
            original = originals.get(key)
            if original is None or any(row.get(k) != v for k, v in original.items() if k != "content_assessment"):
                _fail("artifact_catalog_bundle_conflict")
            if set(row) - set(original) - {"path", "artifact_ref", "source_ref"}:
                _fail("artifact_catalog_entry_fields_invalid")
            self.entries[key] = row
        for row in catalog["entries"] + catalog["retained_sources"]:
            if not all(_text(row.get(k)) for k in ("artifact_ref", "source_ref", "sha256")) or not _integer(row.get("size_bytes")):
                _fail("artifact_catalog_entry_identity_invalid")
            if re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is None:
                _fail("artifact_catalog_digest_invalid")
            previous = self.by_ref.get(row["artifact_ref"])
            if previous is not None and any(previous[k] != row[k] for k in ("sha256", "size_bytes")):
                _fail("artifact_reference_identity_conflict")
            self.by_ref[row["artifact_ref"]] = row
        for row in catalog["retained_sources"]:
            if set(row) - {"source_ref", "artifact_ref", "sha256", "size_bytes", "path"}:
                _fail("retained_source_fields_invalid")
        if set(contents) - self.by_ref.keys():
            _fail("unselected_content_address")

    def read(self, row):
        raw = self.contents.get(row["artifact_ref"])
        if raw is None:
            raise ValueError("artifact_bytes_unavailable")
        if len(raw) != row["size_bytes"] or _sha(raw) != row["sha256"]:
            raise ValueError("artifact_digest_conflict")
        return raw

    def json(self, row):
        ref = row["artifact_ref"]
        if ref not in self.json_cache:
            self.json_cache[ref] = _decode(self.read(row))
        return self.json_cache[ref]

    def fasta(self, row):
        ref = row["artifact_ref"]
        if ref not in self.fasta_cache:
            self.fasta_cache[ref] = parse_sequences(self.read(row), format="fasta", molecule="unspecified")
        return self.fasta_cache[ref]


def _one(rows, code):
    if len(rows) != 1:
        raise ValueError(code)
    return rows[0]


def _resolve(declaration, *, files, job, bundle):
    address, expected = declaration["artifact"], None
    kind = address["kind"]
    if kind == "received":
        row = _one([r for r in files.catalog["retained_sources"] if all(r[k] == address[k]
            for k in ("source_ref", "artifact_ref", "sha256", "size_bytes"))], "received_source_not_selected")
    elif kind == "input":
        expected = _one([r for r in job["inputs"] if r["input_key"] == address["input_key"]], "input_not_selected")
        capture = _one([r for r in bundle["input_manifest"] if r["input_key"] == address["input_key"]], "input_capture_missing")
        row = files.entries.get(capture["artifact_key"])
    elif kind == "output":
        selected = _one([r for r in job["outputs"] if r["output_key"] == address["output_key"]], "output_not_selected")
        capture = _one([r for r in bundle["output_manifest"] if r["output_key"] == address["output_key"]], "output_capture_missing")
        row = _one([files.entries[k] for k in capture["artifact_keys"] if k in files.entries and
                    files.entries[k]["relative_path"] == address["relative_path"]], "output_original_member_unresolved")
        if row["role"] != selected["role"] or row["format"] != selected["format"]:
            raise ValueError("output_descriptor_conflict")
    else:
        selected = _one([r for r in job["databases"] if r["database_key"] == address["database_key"]], "database_not_selected")
        capture = _one([r for r in bundle["database_manifest"] if r["database_key"] == address["database_key"]], "database_capture_missing")
        if kind == "database_manifest":
            expected, key = selected["manifest_file"], capture["manifest_artifact_key"]
        elif kind == "database_metadata_manifest":
            index = address["manifest_index"]
            expected = selected["manifest"]["metadata_manifests"][index]
            slot = capture["metadata_manifest_artifacts"][index]
            if slot["identity"] != expected:
                raise ValueError("original_manifest_identity_conflict")
            key = slot["artifact_key"]
        elif kind == "database_sidecar":
            slot = _one([r for r in capture["sidecar_artifacts"] if r["role"] == address["role"]], "sidecar_role_unresolved")
            expected, key = slot["identity"], slot["artifact_key"]
        else:
            raise ValueError("document_address_unsupported")
        row = files.entries.get(key)
    if row is None:
        raise ValueError("artifact_bytes_unavailable")
    if expected is not None and any(row[k] != expected[k] for k in ("sha256", "size_bytes")):
        raise ValueError("selected_document_digest_conflict")
    return dict(deepcopy(declaration), artifact_key=row.get("artifact_key"),
                **{k: row[k] for k in ("artifact_ref", "source_ref", "sha256", "size_bytes")}, contents=files.read(row))


def _relation(prepared, kind, pointer, status, value=None, *, descriptor=None, pointers=()):
    prepared["source_relations"].append(dict(kind=kind, descriptor=None if descriptor is None else _owner(descriptor),
        pointer=pointer, status=status, value=deepcopy(value), input_pointers=deepcopy(list(pointers))))


def _prepare_metadata(prepared, *, files, job, bundle, payloads):
    reports = []
    for row in files.entries.values():
        if row["role"] == "primary_report":
            try:
                files.read(row)
            except ValueError:
                continue
            reports.append({k: row[k] for k in ("output_key", "artifact_key", "artifact_ref", "source_ref", "sha256", "size_bytes", "format")})
    identities, counts = {}, {}
    for raw in payloads:
        _keys(raw, {"descriptor", "payload"}, "metadata_input_fields_invalid")
        d = raw["descriptor"]
        _validate_descriptor(d)
        identity = tuple(d[k] for k in _OWNER)
        counts[identity] = counts.get(identity, 0) + 1
        identities.setdefault(d["input_key"], set()).add((d["artifact_ref"], d["sha256"], d["size_bytes"]))
    for raw in payloads:
        descriptor, payload = deepcopy(raw["descriptor"]), deepcopy(raw["payload"])
        result = {k: descriptor[k] for k in ("consumer", "schema_id", "input_key", "artifact_ref", "sha256")}
        result.update(status="invalid", payload=payload, normalized=None, normalization_map=[], issues=[], descriptor=descriptor)
        docs, early = [], []
        try:
            if (descriptor["consumer"], descriptor["schema_id"]) not in _TUPLES:
                result["status"] = "unsupported"
                raise ValueError("metadata_tuple_unregistered")
            if counts[tuple(descriptor[k] for k in _OWNER)] != 1:
                raise ValueError("metadata_descriptor_tuple_duplicate")
            if len(identities[descriptor["input_key"]]) != 1:
                raise ValueError("metadata_input_identity_conflict")
            entries = ([r for r in files.entries.values() if r["input_key"] == descriptor["input_key"]]
                if descriptor["origin"] == "original_job_input" else files.catalog["retained_sources"])
            entries = [r for r in entries if r["artifact_ref"] == descriptor["artifact_ref"]
                and all(r[k] == descriptor[k] for k in ("sha256", "size_bytes"))]
            entry = entries[0] if entries else None  # identical content; original slots stay retained
            if entry is None or any(entry[k] != descriptor[k] for k in ("sha256", "size_bytes")):
                raise ValueError("metadata_descriptor_identity_unresolved")
            if descriptor["origin"] == "original_job_input":
                if (not any(all(r[k] == descriptor[k] for k in _OWNER) for r in job["metadata_inputs"])
                        or entry.get("input_key") != descriptor["input_key"]):
                    raise ValueError("original_metadata_descriptor_conflict")
            elif descriptor["origin"] == "selected_results_input":
                if (not any(r["artifact_ref"] == descriptor["artifact_ref"] for r in files.catalog["retained_sources"])
                        or any(r["input_key"] == descriptor["input_key"] and r["role"] != "metadata" for r in job["inputs"])):
                    raise ValueError("selected_metadata_input_unreceived")
            else:
                raise ValueError("metadata_origin_invalid")
            if files.json(entry) != payload:
                raise ValueError("metadata_payload_bytes_conflict")
            declarations = payload.get("documents", []) if type(payload) is dict else []
            for index, declaration in enumerate(declarations if type(declarations) is list else []):
                try:
                    docs.append(_resolve(declaration, files=files, job=job, bundle=bundle))
                except (KeyError, IndexError, TypeError, ValueError) as error:
                    early.append(_issue("metadata_source_unavailable", f"/documents/{index}", descriptor=descriptor, detail=str(error)))
            catalog = dict(descriptor=descriptor, documents=docs, primary_reports=reports,
                bundle_source_ref=files.catalog["bundle_source_ref"], bundle_artifact_ref=files.catalog["bundle_artifact_ref"])
            result = validate_native_blast_database_metadata_payload(payload, descriptor=descriptor,
                document_catalog=catalog, job=job)
            result["descriptor"] = descriptor
            result["issues"] = early + result["issues"]
        except (KeyError, IndexError, TypeError, ValueError) as error:
            result["issues"].append(_issue("metadata_payload_invalid", descriptor=descriptor, detail=str(error)))
        prepared["metadata"].append(result)
        prepared["issues"].extend(deepcopy(result["issues"]))
        for problem in result["issues"]:
            status = "incompatible" if any(s in problem["code"] for s in ("conflict", "invalid")) else "unavailable"
            _relation(prepared, "metadata", problem["pointer"], status, descriptor=descriptor)


def _native_pssm_names(record):
    query = record["native_pssm"].get("query")
    fields = query.get("seq") if type(query) is dict else None
    identifiers, titles = [], []
    for field in fields if type(fields) is list else []:
        if type(field) is not dict:
            continue
        for row in field.get("id", []) if type(field.get("id")) is list else []:
            value = row.get("local", {}).get("str") if type(row) is dict and type(row.get("local")) is dict else None
            if type(value) is str:
                identifiers.append(value)
        for row in field.get("descr", []) if type(field.get("descr")) is list else []:
            if type(row) is dict and type(row.get("title")) is str:
                titles.append(row["title"])
    return (identifiers[0] if len(identifiers) == 1 else None, titles[0] if len(titles) == 1 else None)


def _qualify_pssm_locators(prepared):
    for validation in prepared["metadata"]:
        if validation["status"] != "valid" or validation["normalized"] is None:
            continue
        docs = {d["document_key"]: d for d in validation["normalized"]["documents"]}
        excluded = set()
        for problem in list(validation["issues"]):
            if problem.get("detail_code") != "parser_source_locator_pending":
                continue
            doc = docs.get(problem["document_key"])
            status = "unavailable"
            try:
                if doc is None or doc["format"] != "scoremat_asn_text":
                    raise ValueError("unsupported_parser_locator")
                sheet = _one([s for s in prepared["pssm_sheets"] if s["artifact_key"] == doc["artifact_key"]
                    and s["source_ref"] == doc["source_ref"] and s["input_identity"] == {k: doc[k] for k in ("sha256", "size_bytes")}],
                    "pssm_locator_source_unavailable")
                slot = _at(validation["payload"], problem["pointer"])
                _at(sheet, slot["pointer"] if type(slot) is dict else slot)
                status = "available"
            except (ValueError, KeyError, IndexError, TypeError):
                excluded.add("/" + "/".join(problem["pointer"].split("/")[1:3]))
            validation["issues"].remove(problem)
            prepared["issues"] = [r for r in prepared["issues"] if r != problem]
            prepared["source_relations"] = [r for r in prepared["source_relations"] if not (
                r["kind"] == "metadata" and r["descriptor"] == _owner(validation) and r["pointer"] == problem["pointer"])]
            _relation(prepared, "metadata", problem["pointer"], status, descriptor=validation)
            if status != "available":
                new = _issue("metadata_relation_unresolved", problem["pointer"], descriptor=validation,
                             detail="pssm_parser_pointer_unresolved")
                validation["issues"].append(new)
                prepared["issues"].append(deepcopy(new))
        if excluded:
            updated = []
            for field, rows in validation["normalized"].items():
                if field == "schema":
                    continue
                kept = []
                for index, row in enumerate(rows):
                    original = _original(validation, f"/{field}/{index}")
                    if original not in excluded:
                        updated.append(dict(normalized_pointer=f"/{field}/{len(kept)}", payload_pointer=original))
                        kept.append(row)
                validation["normalized"][field] = kept
            validation["normalization_map"] = updated


def _prepare_queries(prepared, *, files, job, snapshots, subject_contents):
    descriptor = _query_descriptor(job)
    if type(subject_contents) is not dict or any(not _text(k) or type(v) is not bytes for k, v in subject_contents.items()):
        _fail("subject_contents_invalid")
    known = {}
    for index, snap in enumerate(snapshots):
        status, symbols = "unavailable", None
        try:
            allowed = {"subject_ref", "sequence_artifact_ref", "sequence_path", "record_type", "molecule", "length", "sequence_sha256"}
            if (set(snap) - allowed or not allowed - {"sequence_path", "record_type"} <= snap.keys()
                    or "record_type" in snap and snap["record_type"] not in {"input", "feature", "product", "read_subject"}):
                raise ValueError("subject_snapshot_fields_invalid")
            raw = subject_contents.get(snap["sequence_artifact_ref"])
            if raw is None:
                raise ValueError("subject_bytes_unavailable")
            symbols = raw.decode("ascii")
            if (snap["molecule"] not in _ALPHABETS or not symbols or symbols != symbols.upper()
                    or not set(symbols) <= set(_ALPHABETS[snap["molecule"]]) or len(symbols) != snap["length"]
                    or _sha(raw) != snap["sequence_sha256"]):
                status = "incompatible"
                raise ValueError("subject_full_sequence_conflict")
            status = "available"
            known.setdefault(snap["subject_ref"], []).append((snap, symbols))
        except (ValueError, KeyError, TypeError, UnicodeError) as error:
            prepared["issues"].append(_issue("query_unbound", f"/subject_snapshots/{index}", descriptor=descriptor, detail=str(error)))
        _relation(prepared, "subject", f"/subject_snapshots/{index}", status,
                  dict(snapshot=deepcopy(snap), sequence=symbols), descriptor=descriptor)
    if set(subject_contents) - {s.get("sequence_artifact_ref") for s in snapshots}:
        _fail("unreceived_subject_content")
    candidates = []
    qkey = job["query"]["input_key"]
    entry = next((r for r in files.entries.values() if r["input_key"] == qkey), None)
    if entry is None:
        prepared["issues"].append(_issue("query_unbound", "/query", descriptor=descriptor, detail="query_capture_unavailable"))
        return
    try:
        if job["query"]["kind"] == "sequence":
            for ordinal, record in enumerate(files.fasta(entry)):
                candidates.append((ordinal, record.sequence, record.name,
                    record.name + (" " + record.description if record.description else ""), True))
        else:
            sheet = read_blast_pssm(files.read(entry), format="scoremat_asn_text",
                artifact_key=entry["artifact_key"], source_ref=entry["source_ref"])
            prepared["pssm_sheets"].append(sheet)
            masters = extract_blast_pssm_master_metadata(sheet)
            _relation(prepared, "pssm_master", "/pssm_sheets/0", "available", masters, descriptor=descriptor)
            records = {r["record_ordinal"]: r for r in sheet["pssms"]}
            for record in masters["records"]:
                master = record["master"]
                if master["sequence"]:
                    mapping = master["column_to_residue"]
                    compatible = (master["status"] == "complete" and mapping is not None and
                        all(r == {"column": i, "master_position": i, "symbol": master["sequence"][i]} for i, r in enumerate(mapping)))
                    candidates.append((record["record_ordinal"], master["sequence"],
                        *_native_pssm_names(records[record["record_ordinal"]]), compatible))
                else:
                    prepared["issues"].append(_issue("query_unbound", f"/pssm_sheets/0/pssms/{record['record_ordinal']}",
                        descriptor=descriptor, detail="pssm_master_unavailable"))
    except (ValueError, UnicodeError) as error:
        prepared["issues"].append(_issue("query_unbound", "/query", descriptor=descriptor, detail=str(error)))
    _qualify_pssm_locators(prepared)
    payloads = _valid(prepared, "query_identity")
    options = prepared["invocation"]["effective_options"]
    protein = standard_blast_database_program_spec(job["program"])["query_coordinate_unit"] == "aa"
    for ordinal, symbols, native_id, native_title, compatible in candidates:
        kind, digest = job["query"]["kind"], _sha(symbols.encode("ascii"))
        field = "sequence_records" if kind == "sequence" else "master_subjects"
        relations = [(v, i, r) for v in payloads for i, r in enumerate(v["normalized"][field])
            if r["input_key"] == qkey and r["record_ordinal"] == ordinal and (kind == "sequence" or r["kind"] == "pssm")]
        molecule = "protein" if protein else "rna" if "U" in symbols and "T" not in symbols else "dna"
        identity, subject, status = None, None, "unavailable"
        if len(relations) == 1:
            validation, index, relation = relations[0]
            if kind == "sequence":
                identity = relation["identity"]
            received = known.get(relation["subject_ref"], [])
            if len(received) == 1:
                snap, actual = received[0]
                if not protein and snap["molecule"] in {"dna", "rna"}:
                    molecule = snap["molecule"]
                valid = (compatible and actual == symbols and snap["molecule"] == molecule and snap["length"] == len(symbols)
                    and snap["sequence_sha256"] == digest and (kind == "sequence" or relation["sequence_sha256"] == digest))
                subject, status = (relation["subject_ref"], "available") if valid else (None, "incompatible")
            elif len(received) > 1:
                status = "incompatible"
        elif len(relations) > 1:
            status = "incompatible"
        compatible = compatible and bool(symbols) and set(symbols) <= set(_ALPHABETS[molecule])
        interval = None
        if "-query_loc" in options:
            start, end = map(int, options["-query_loc"].split("-"))
            interval = [start - 1, end]
            compatible = compatible and end <= len(symbols)
        if not compatible:
            subject, status = None, "incompatible"
        row = dict(input_key=qkey, artifact_key=entry["artifact_key"], artifact_ref=entry["artifact_ref"],
            record_ordinal=ordinal, native_id=native_id, native_title=native_title, sequence=symbols,
            molecule=molecule, length=len(symbols), sequence_sha256=digest, selected_interval=interval,
            subject_ref=subject, binding_status=status)
        prepared["query_records"].append(row)
        if compatible:
            prepared["invocation"]["operands"].append(dict(role="query", artifact_key=entry["artifact_key"],
                record_ordinal=ordinal, native_id=native_id, native_title=native_title, subject_ref=subject,
                molecule=molecule, length=len(symbols), selected_interval=interval, identity=identity))
        if status != "available":
            prepared["issues"].append(_issue("query_unbound", f"/query_records/{len(prepared['query_records']) - 1}",
                descriptor=descriptor, detail="query_identity_conflict" if status == "incompatible" else "explicit_subject_identity_unavailable"))
    for validation in payloads:
        for field in ("sequence_records", "master_subjects", "effective_msa_masters"):
            for index, relation in enumerate(validation["normalized"][field]):
                if (field == "effective_msa_masters" or relation["input_key"] != qkey or
                        not any(r["record_ordinal"] == relation["record_ordinal"] for r in prepared["query_records"]) or
                        field == "master_subjects" and relation["kind"] != job["query"]["kind"] or
                        field == "sequence_records" and job["query"]["kind"] != "sequence"):
                    prepared["issues"].append(_issue("metadata_relation_unresolved", _original(validation, f"/{field}/{index}"),
                        descriptor=validation, detail="query_record_address_unresolved"))


def _prepare_proofs(prepared, files):
    fasta_records = {}
    for validation in _valid(prepared, "sequence_database"):
        record_version = validation["schema_id"] == _SEQUENCE_V2
        docs = {d["document_key"]: d for d in validation["normalized"]["documents"]}
        for ui, unit in enumerate(validation["normalized"]["searches"]):
            for pi, proof in enumerate(unit["sequence_proofs"]):
                if proof["binding_index"] >= len(unit["sequence_identity_bindings"]):
                    prepared["issues"].append(_issue("metadata_relation_unresolved", _original(validation, f"/searches/{ui}/sequence_proofs/{pi}"),
                        descriptor=validation, search_key=unit["search_key"], detail="sequence_proof_binding_index_unresolved"))
            for index, binding in enumerate(unit["sequence_identity_bindings"]):
                failure_status = "incompatible"
                supplied = [(i, p) for i, p in enumerate(unit["sequence_proofs"]) if p["binding_index"] == index]
                row = dict(descriptor=_owner(validation), search_key=deepcopy(unit["search_key"]),
                    pointer=_original(validation, f"/searches/{ui}/sequence_identity_bindings/{index}"),
                    binding_index=index, proof_index=None, binding=deepcopy(binding), proof=None,
                    document=None, symbols=None, status="unavailable", issues=[])
                try:
                    pi, proof = _one(supplied, "full_sequence_proof_missing_or_ambiguous")
                    row.update(proof_index=pi, proof=deepcopy(proof))
                    doc = docs[proof["document_key"]]
                    row["document"] = deepcopy(doc)
                    entry = files.by_ref[doc["artifact_ref"]]
                    b = binding["binding"]
                    if (doc["source_ref"] != b["source_ref"] or proof["sha256"] != b["digest"]
                            or proof["length"] != b["sequence_length"] or proof["molecule"] != b["molecule"]
                            or b["sequence_group"] != "sha256:" + b["digest"]):
                        raise ValueError("sequence_proof_binding_identity_conflict")
                    if record_version:
                        if _record_relation_failed(validation, f"/searches/{ui}/sequence_identity_bindings/{index}/binding"):
                            failures = [r for r in validation["issues"] if r["pointer"] == row["pointer"] + "/binding/record_locator"]
                            failure_status = "unavailable" if all(r["code"].endswith("unresolved") for r in failures) else "incompatible"
                            raise ValueError(failures[0]["detail_code"])
                        status, details, record = _record_address_status(doc, b["pointer"], b["record_locator"],
                            contents=files.read(entry), cache=fasta_records)
                        if status != "available":
                            failure_status = status
                            raise ValueError(details[0])
                        if (proof["representation"] == "fasta_record" and
                                (b["record_locator"] is None or b["record_locator"]["record_ordinal"] != proof["record_ordinal"])):
                            raise ValueError("sequence_proof_record_locator_conflict")
                        if b["molecule"] != standard_blast_database_program_spec(_job(prepared)["program"])["reference_coordinate_unit"]:
                            raise ValueError("sequence_proof_binding_identity_conflict")
                    if proof["representation"] == "json_sequence" and doc["format"] == "json":
                        if record_version and b["record_locator"] is not None:
                            raise ValueError("sequence_proof_record_locator_conflict")
                        symbols = _at(files.json(entry), proof["sequence_pointer"])
                        if proof["sequence_pointer"] != b["pointer"] and not proof["sequence_pointer"].startswith(b["pointer"] + "/"):
                            raise ValueError("sequence_proof_pointer_conflict")
                    elif proof["representation"] == "fasta_record" and doc["format"] == "fasta":
                        if b["pointer"] != "":
                            raise ValueError("sequence_fasta_pointer_conflict")
                        symbols = record["symbols"] if record_version else files.fasta(entry)[proof["record_ordinal"]].sequence
                    else:
                        raise ValueError("sequence_representation_incompatible")
                    row["symbols"] = symbols if type(symbols) is str else None
                    alphabet = _ALPHABETS["protein"] if b["molecule"] == "aa" else "ACGTURYSWKMBDHVN"
                    if (type(symbols) is not str or not symbols or not symbols.isascii() or not set(symbols) <= set(alphabet)
                            or len(symbols) != proof["length"] or _sha(symbols.encode()) != proof["sha256"]):
                        raise ValueError("full_sequence_identity_conflict")
                    row["status"] = "available"
                except (ValueError, KeyError, IndexError, UnicodeError) as error:
                    row["status"] = failure_status if supplied else "unavailable"
                    row["issues"].append(_issue("metadata_relation_conflict" if row["status"] == "incompatible" else "metadata_relation_unresolved",
                        row["pointer"], descriptor=validation, search_key=unit["search_key"], detail=str(error)))
                prepared["sequence_proofs"].append(row)
                prepared["issues"].extend(deepcopy(row["issues"]))


def prepare_standard_blast_database_inputs(*, job: dict, bundle: dict, attempt_identity: dict,
        artifact_catalog: dict, contents: dict[str, bytes], metadata_payloads: list[dict],
        subject_snapshots: list[dict], subject_contents: dict[str, bytes]) -> dict:
    """Validate the actual attempt and populate detached inputs from supplied bytes.

    The independent attempt_identity is supplied by the authenticated worker
    request. It is never recovered from the bundle's own ownership claims.
    Missing bytes/metadata produce explicit qualifications; inconsistent custody
    contracts raise stable ValueErrors before any scientific interpretation.
    """
    job = validate_standard_blast_database_job(job)
    bundle = validate_standard_blast_database_bundle(bundle, original_job=job, attempt_identity=attempt_identity)
    payloads, snapshots = _copy(metadata_payloads), _copy(subject_snapshots)
    if type(payloads) is not list or type(snapshots) is not list:
        _fail("supplied_inputs_arrays_required")
    files = _Supplied(_copy(artifact_catalog), contents, bundle)
    registered = {(r["consumer"], r["schema_id"]) for r in metadata_schema_registry()}
    if not _TUPLES <= registered:
        _fail("metadata_registry_contract_conflict")
    options = validate_standard_blast_database_options(job["program"], job["options"], query_kind=job["query"]["kind"])
    options.update(requested_hit_limit=int(options["-max_target_seqs"]) if "-max_target_seqs" in options else None,
                   requested_hsp_limit=int(options["-max_hsps"]) if "-max_hsps" in options else None)
    prepared = dict(schema=PREPARED_INPUTS_SCHEMA, invocation=dict(execution_program=job["program"],
        scientific_mode="database", resource_kind="hpc", query_kind=job["query"]["kind"], reference_kind="sequence",
        request=requested_job_from_standard_blast_database(job), effective_options=options, operands=[],
        completion=dict(native_returncode=bundle["process"]["returncode"], producer_complete=(bundle["process"]["started"]
            and bundle["process"]["returncode"] == 0 and not bundle["failures"]))),
        query_records=[], pssm_sheets=[], metadata=[], resolved_documents=[], source_relations=[], sequence_proofs=[], issues=[])
    _relation(prepared, "attempt", "", "available", dict(bundle=bundle, attempt_identity=_copy(attempt_identity),
        **{k: files.catalog[k] for k in ("bundle_source_ref", "bundle_artifact_ref", "bundle_sha256")}))
    _prepare_metadata(prepared, files=files, job=job, bundle=bundle, payloads=payloads)
    _prepare_queries(prepared, files=files, job=job, snapshots=snapshots, subject_contents=subject_contents)
    _prepare_proofs(prepared, files)
    # Retain exact source bytes separately from normalized biological symbols.
    for kind, rows in (("captured", files.catalog["entries"]), ("received", files.catalog["retained_sources"])):
        for row in rows:
            saved = dict(kind=kind, catalog=deepcopy(row), status="available", contents_hex=None, decoded_json=None)
            try:
                raw = files.read(row)
                saved["contents_hex"] = raw.hex()
                if row.get("format") in {"json", "json15"} or row["artifact_ref"] in files.json_cache:
                    try:
                        saved["decoded_json"] = files.json(row)
                    except (ValueError, UnicodeError):
                        pass  # A malformed report remains bytes for its native parser.
            except ValueError as error:
                saved["status"] = "unavailable" if str(error) == "artifact_bytes_unavailable" else "incompatible"
                prepared["issues"].append(_issue("artifact_missing" if saved["status"] == "unavailable" else "artifact_identity_mismatch",
                    "/resolved_documents/" + str(len(prepared["resolved_documents"])), detail=str(error)))
            prepared["resolved_documents"].append(saved)
    for index, database in enumerate(job["databases"]):
        status = "unavailable"
        capture = bundle["database_manifest"][index]
        try:
            entry = files.entries[capture["manifest_artifact_key"]]
            verified = (files.json(entry) == database["manifest"] and
                all(r["status"] == "verified" for r in capture["checks"]))
            status = "available" if verified else "incompatible"
        except (KeyError, ValueError, UnicodeError):
            entry = None
        pointers = [_provenance(files.catalog["bundle_source_ref"], "/requested_job/native_blast_standard_database/databases/" + str(index)),
                    _provenance(files.catalog["bundle_source_ref"], "/database_manifest/" + str(index))]
        if entry is not None:
            pointers.append(_provenance(entry["source_ref"], "/identity"))
        _relation(prepared, "database", "/requested_job/native_blast_standard_database/databases/" + str(index), status,
            dict(database_key=database["database_key"], native_paths=database["native_paths"],
                 manifest_artifact_key=capture["manifest_artifact_key"]), pointers=pointers)
    return _copy(prepared)


def _job(prepared):
    return prepared["invocation"]["request"]["native_blast_standard_database"]


def _attempt(prepared):
    return _one([r["value"] for r in prepared["source_relations"] if r["kind"] == "attempt" and r["status"] == "available"],
                "authenticated_attempt_unavailable")


def _report(search, prepared):
    key = search["search_key"]
    rows = [r for r in prepared["resolved_documents"] if r["kind"] == "captured" and
            r["catalog"]["artifact_key"] == key["artifact_key"] and r["catalog"]["role"] == "primary_report"]
    return _one(rows, "original_report_unavailable")


def _search_status(search, prepared):
    """Check original source bytes/context; 303 independently checks native rows."""
    try:
        saved = _report(search, prepared)
        row, key = saved["catalog"], search["search_key"]
        if saved["status"] != "available":
            return saved["status"], "original_report_bytes_unavailable"
        if key["member_ordinal"] is not None or search["normalized"]["native"]["sha256"] != row["sha256"]:
            return "incompatible", "original_report_identity_conflict"
        if search["normalized"]["search"]["request"] != prepared["invocation"]["request"]:
            return "incompatible", "original_request_conflict"
        if row["format"] == "json15":
            document = saved["decoded_json"]
            report_pointer = key["search_pointer"].split("/results/")[0]
            outer = document["BlastOutput2"]
            expected = "/BlastOutput2" + ("/" + str(key["report_index"]) if type(outer) is list else "") + "/report"
            if (report_pointer != expected or type(outer) is dict and key["report_index"] != 0 or
                    search["normalized"]["native"]["document"] != document or
                    _at(document, report_pointer) != search["native"]["report"] or
                    _at(document, key["search_pointer"]) != search["native"]["search"] or
                    key["search_pointer"] != report_pointer + "/results/search"):
                return "incompatible", "original_report_address_conflict"
        elif row["format"] in {"tabular6", "tabular7"}:
            if (search["native"]["report"].get("text", "").encode() != bytes.fromhex(saved["contents_hex"]) or
                    key["report_index"] != 0 or re.fullmatch(r"/sections/(0|[1-9][0-9]*)", key["search_pointer"]) is None):
                return "incompatible", "original_table_address_conflict"
        else:
            return "incompatible", "original_report_format_conflict"
        if search["reporting"]["native_returncode"] != prepared["invocation"]["completion"]["native_returncode"] or \
                search["reporting"]["producer_complete"] != prepared["invocation"]["completion"]["producer_complete"]:
            return "incompatible", "original_completion_conflict"
        return "available", None
    except (ValueError, KeyError, IndexError, TypeError, UnicodeError):
        return "unavailable", "original_report_address_unresolved"


def _query_binding(search, prepared):
    if _search_status(search, prepared)[0] != "available":
        return None
    operand = search["operand_binding"]
    if operand is None or operand not in prepared["invocation"]["operands"]:
        return None
    native = search["normalized"]["query"]
    matches = []
    for candidate in prepared["invocation"]["operands"]:
        names = {candidate[k] for k in ("native_id", "native_title") if candidate[k] is not None}
        if not any(native[k] is not None and native[k] in names for k in ("id", "title")):
            continue
        if native["title"] is not None and candidate["native_title"] is not None and native["title"] != candidate["native_title"]:
            continue
        if native["id"] is not None and candidate["native_id"] is not None and native["id"] != candidate["native_id"] and not (
                re.fullmatch(r"Query_\d+", native["id"]) and not re.fullmatch(r"Query_\d+", candidate["native_id"])):
            continue
        interval = candidate["selected_interval"]
        lengths = [candidate["length"]] + ([interval[1] - interval[0]] if interval is not None else [])
        if native["length"] is not None and native["length"] not in lengths:
            continue
        matches.append(candidate)
    if len(matches) != 1 or matches[0] != operand:
        return None
    rows = [r for r in prepared["query_records"] if r["artifact_key"] == operand["artifact_key"] and r["record_ordinal"] == operand["record_ordinal"]]
    if len(rows) != 1:
        return None
    row, kind = rows[0], prepared["invocation"]["query_kind"]
    mapping, pssm_key = None, None
    if kind == "pssm":
        records = [(s, i, r) for s in prepared["pssm_sheets"] for i, r in enumerate(s["pssms"])
                   if s["artifact_key"] == operand["artifact_key"] and r["record_ordinal"] == operand["record_ordinal"]]
        if len(records) != 1:
            return None
        sheet, index, record = records[0]
        pssm_key = record["pssm_key"]
        mapping = _provenance(sheet["source_ref"], f"/pssms/{index}/native_pssm/query")
    return dict(operand=deepcopy(operand), axis_kind="pssm_master" if kind == "pssm" else "sequence",
        full_length=row["length"], coordinate_unit="aa" if row["molecule"] == "protein" else "nt",
        sequence_sha256=row["sequence_sha256"], pssm_key=pssm_key, master_mapping_ref=mapping)


def derive_standard_blast_database_search_binding(search: dict, *, prepared_inputs: dict) -> dict:
    """Derive only an exact selected sequence DB/report relationship."""
    prepared, search = _copy(prepared_inputs), _copy(search)
    result = dict(binding=None, status="unavailable", origin=None, input_pointers=[], issues=[])
    job, key = _job(prepared), search["search_key"]
    status, detail = _search_status(search, prepared)
    if status != "available":
        result.update(status=status)
        result["issues"].append(_issue("metadata_relation_conflict" if status == "incompatible" else "metadata_relation_unresolved",
            key["search_pointer"], search_key=key, detail=detail))
        return result
    context = search["program_context"]
    try:
        expected = resolve_blast_program_context(execution_program=job["program"],
            reported_program=search["native"]["report"].get("program"), scientific_mode="database",
            query_kind=job["query"]["kind"], reference_kind="sequence", native_version=search["native"]["report"].get("version"))
        if expected != context or context["geometry_program"] != job["program"]:
            raise ValueError("standard_program_context_conflict")
    except ValueError:
        result["status"] = "incompatible"
        result["issues"].append(_issue("metadata_relation_conflict", key["search_pointer"], search_key=key, detail="standard_program_context_conflict"))
        return result
    database = job["databases"][0]
    relation = _one([r for r in prepared["source_relations"] if r["kind"] == "database" and
                    r["value"]["database_key"] == database["database_key"]], "database_relation_unavailable")
    native_db = search["normalized"]["search"]["database"]
    if relation["status"] != "available":
        result["status"] = relation["status"]
        result["issues"].append(_issue("metadata_relation_unresolved", relation["pointer"], search_key=key, detail="database_custody_unavailable"))
        return result
    if native_db is not None and native_db not in (database["identity"]["value"], " ".join(database["native_paths"])):
        result["status"] = "incompatible"
        result["issues"].append(_issue("metadata_relation_conflict", key["search_pointer"], search_key=key, detail="native_database_identity_conflict"))
        return result
    # Headerless table6 still has the explicitly selected invocation and capture.
    attempt = _attempt(prepared)
    provenance = _provenance(attempt["bundle_source_ref"], "/requested_job/native_blast_standard_database")
    pssms = [r for s in prepared["pssm_sheets"] for r in s["pssms"]]
    pssm_key = pssms[0]["pssm_key"] if job["query"]["kind"] == "pssm" and len(pssms) == 1 else None
    binding = dict(search_key=deepcopy(key), stage="sequence_database", biological_round=None,
        database_identity=deepcopy(database["identity"]), input_pssm_key=pssm_key, provenance=provenance)
    result["input_pointers"] = [provenance, *deepcopy(relation["input_pointers"]),
        _provenance(_report(search, prepared)["catalog"]["source_ref"], key["search_pointer"])]
    supplied = [r for v in _valid(prepared, "query_identity") for r in v["normalized"]["search_bindings"] if r["search_key"] == key]
    if supplied:
        if len(supplied) != 1 or any(supplied[0][k] != binding[k] for k in binding if k != "provenance") or supplied[0]["provenance"] is None:
            result["status"] = "incompatible"
            result["issues"].append(_issue("metadata_relation_conflict", "/search_bindings", search_key=key,
                detail="supplied_derived_search_binding_conflict"))
            return result
        binding, result["origin"] = deepcopy(supplied[0]), "supplied"
        result["input_pointers"].append(deepcopy(binding["provenance"]))
    else:
        result["origin"] = "derived"
    result.update(binding=binding, status="available")
    if native_db is not None and native_db != database["identity"]["value"]:
        result["issues"].append(_issue("metadata_relation_unresolved", key["search_pointer"], search_key=key,
            detail="native_path_semantic_identity_population_equality_unproven"))
    return _copy(result)


def _feature_scoped(row):
    """Honor explicit scope declarations; never infer function from source prose."""
    native = row.get("native_record")
    for value in (row.get("origin"), native):
        if type(value) is dict:
            if value.get("assignment_scope") not in (None, "whole_sequence"):
                return True
            if value.get("entity_kind") == "feature" or value.get("key") == "CDS":
                return True
            if type(value.get("entity")) is dict and value["entity"].get("kind") == "feature":
                return True
    return False


def qualify_standard_blast_sequence_metadata(search: dict, *, prepared_inputs: dict) -> dict:
    """Join exact original slots; retain source-qualified missing/conflicting data."""
    prepared, search = _copy(prepared_inputs), _copy(search)
    key = search["search_key"]
    result = dict(search_key=deepcopy(key), reference_metadata=[], description_bindings=[],
        sequence_identity_bindings=[], target_context=None, database_profile=None, input_pointers=[], issues=[])
    status, detail = _search_status(search, prepared)
    if status != "available":
        result["issues"].append(_issue("metadata_relation_unresolved", key["search_pointer"], search_key=key, detail=detail))
        return result
    profiles, record_claims = [], []
    hits = {h["hit_index"]: h for h in search["normalized"]["hits"]}
    molecule = standard_blast_database_program_spec(_job(prepared)["program"])["reference_coordinate_unit"]
    for validation in _valid(prepared, "sequence_database"):
        for ui, unit in enumerate(validation["normalized"]["searches"]):
            if unit["search_key"] != key:
                continue
            pointer = _original(validation, f"/searches/{ui}")
            if validation["schema_id"] == _SEQUENCE_V2:
                record_claims.extend(unit["sequence_identity_bindings"])
            result["input_pointers"].extend(_metadata_pointers(prepared, validation, pointer))
            offset = len(result["reference_metadata"])
            for mi, native in enumerate(unit["reference_metadata"]):
                row = deepcopy(native)
                if _feature_scoped(row) and row["functions"]:
                    row["functions"] = []
                    result["issues"].append(_issue("metadata_relation_unresolved", pointer + f"/reference_metadata/{mi}/functions",
                        descriptor=validation, search_key=key, detail="feature_function_is_not_whole_reference_function"))
                result["reference_metadata"].append(row)
            for bi, native in enumerate(unit["description_bindings"]):
                row = deepcopy(native)
                if row["binding"]["metadata_index"] >= len(unit["reference_metadata"]):
                    result["issues"].append(_issue("metadata_relation_unresolved", pointer + f"/description_bindings/{bi}",
                        descriptor=validation, search_key=key, detail="original_metadata_index_unresolved"))
                    continue
                if validation["schema_id"] == _SEQUENCE_V2 and (
                        _record_relation_failed(validation, f"/searches/{ui}/description_bindings/{bi}/binding") or
                        _record_relation_failed(validation, f"/searches/{ui}/reference_metadata/{row['binding']['metadata_index']}")):
                    continue
                row["binding"]["metadata_index"] += offset
                result["description_bindings"].append(row)
            for bi, binding in enumerate(unit["sequence_identity_bindings"]):
                original = _original(validation, f"/searches/{ui}/sequence_identity_bindings/{bi}")
                proofs = [p for p in prepared["sequence_proofs"] if p["descriptor"] == _owner(validation) and p["pointer"] == original]
                b = binding["binding"]
                valid = (len(proofs) == 1 and proofs[0]["status"] == "available" and proofs[0]["binding"] == binding
                    and binding["search_key"] == key and b["report_index"] == key["report_index"] and b["molecule"] == molecule
                    and b["hit_index"] in hits and (hits[b["hit_index"]]["length"] is None or hits[b["hit_index"]]["length"] == b["sequence_length"]))
                if valid:
                    result["sequence_identity_bindings"].append(deepcopy(binding))
                else:
                    result["issues"].append(_issue("metadata_relation_conflict", original, descriptor=validation,
                        search_key=key, detail="full_reference_sequence_unverified"))
            if unit["database_profile"] is not None:
                profiles.append(unit["database_profile"])
    profiles = _unique(profiles)
    if len(profiles) == 1:
        result["database_profile"] = deepcopy(profiles[0])
    elif profiles:
        result["issues"].append(_issue("metadata_relation_conflict", "/database_profile", search_key=key, detail="database_population_conflict"))
    # Exact duplicate links have one meaning; payloads and descriptor addresses
    # above remain separate. A source/pointer conflict must invalidate both.
    identities = {}
    for link in result["sequence_identity_bindings"] + record_claims:
        b = link["binding"]
        identities.setdefault(blast_record_identity(source_ref=b["source_ref"], pointer=b["pointer"],
            record_locator=b.get("record_locator")), set()).add((b["digest"], b["molecule"], b["sequence_length"]))
    conflict = {identity for identity, values in identities.items() if len(values) > 1}
    if conflict:
        result["sequence_identity_bindings"] = [r for r in result["sequence_identity_bindings"] if
            blast_record_identity(source_ref=r["binding"]["source_ref"], pointer=r["binding"]["pointer"],
                record_locator=r["binding"].get("record_locator")) not in conflict]
        result["issues"].append(_issue("metadata_relation_conflict", "/sequence_identity_bindings", search_key=key,
            detail="full_sequence_source_identity_conflict"))
    for field in ("description_bindings", "sequence_identity_bindings"):
        result[field] = _unique(result[field])
    targets = [(v, i, r) for v in _valid(prepared, "query_identity") for i, r in enumerate(v["normalized"]["target_contexts"])
               if r["search_key"] == key]
    query = _query_binding(search, prepared)
    if len(targets) == 1 and query is not None:
        validation, index, row = targets[0]
        result["target_context"] = dict(query_operand=query["operand"], **{k: deepcopy(row[k]) for k in ("taxid", "lineage", "independent_of_search", "source")})
        result["input_pointers"].extend(_metadata_pointers(prepared, validation, _original(validation, f"/target_contexts/{index}")))
    elif targets:
        result["issues"].append(_issue("metadata_relation_conflict" if len(targets) > 1 else "metadata_relation_unresolved",
            "/target_contexts", search_key=key, detail="target_query_relation_ambiguous" if len(targets) > 1 else "target_query_operand_unresolved"))
    return _copy(result)


def populate_standard_blast_database_sheets(collection: dict, *, prepared_inputs: dict) -> dict:
    """One public 303 sequence sheet per original search, even without metadata."""
    prepared, collection = _copy(prepared_inputs), _copy(collection)
    if collection.get("schema") != "blast_report_collection_v1" or collection.get("invocation") != prepared["invocation"]:
        _fail("collection_invocation_conflict")
    keys = [_token(s["search_key"]) for s in collection["searches"]]
    if len(set(keys)) != len(keys):
        _fail("collection_search_key_duplicate")
    result = dict(schema=SHEET_SET_SCHEMA, collection=collection, prepared_inputs=prepared,
        search_bindings=[], sequence=[], pssm=deepcopy(prepared["pssm_sheets"]),
        metadata_parse_results=deepcopy(prepared["metadata"]), metadata_binding_results=[], issues=deepcopy(prepared["issues"]))
    for search in collection["searches"]:
        key = search["search_key"]
        report = _report(search, prepared)["catalog"]
        binding = derive_standard_blast_database_search_binding(search, prepared_inputs=prepared)
        metadata = qualify_standard_blast_sequence_metadata(search, prepared_inputs=prepared)
        result["search_bindings"].append(binding)
        result["metadata_binding_results"].append(metadata)
        result["issues"].extend(binding["issues"] + metadata["issues"])
        unresolved = dict(search_key=deepcopy(key), stage=None, biological_round=None,
            database_identity=None, input_pssm_key=None, provenance=None)
        sheet = populate_blast_sequence_database_sheet(search,
            report_source=dict(artifact_key=key["artifact_key"], artifact_ref=report["artifact_ref"], member_ordinal=None, member_sha256=None),
            search_binding=binding["binding"] or unresolved, query_binding=_query_binding(search, prepared),
            **{k: metadata[k] for k in ("reference_metadata", "description_bindings", "sequence_identity_bindings", "target_context", "database_profile")})
        result["sequence"].append(dict(search_key=deepcopy(key), sheet=sheet))
    known = set(keys)
    for validation in prepared["metadata"]:
        if validation["status"] != "valid" or validation["normalized"] is None:
            continue
        for field in ("searches", "search_bindings", "target_contexts"):
            for i, row in enumerate(validation["normalized"].get(field, [])):
                if _token(row["search_key"]) not in known:
                    result["issues"].append(_issue("metadata_relation_unresolved", _original(validation, f"/{field}/{i}/search_key"),
                        descriptor=validation, search_key=row["search_key"], detail="collection_search_address_unresolved"))
    return _copy(result)


def _validate_search_key(key):
    _keys(key, _KEY, "search_key_fields_invalid")
    if (not _text(key["artifact_key"]) or key["member_ordinal"] is not None or
            not _integer(key["report_index"]) or not _pointer(key["search_pointer"])):
        _fail("search_key_invalid")


def _validate_pointers(rows):
    if type(rows) is not list:
        _fail("provenance_array_required")
    for row in rows:
        _keys(row, {"source_ref", "pointer"}, "provenance_fields_invalid")
        if not _text(row["source_ref"]) or not _pointer(row["pointer"]):
            _fail("provenance_invalid")


def _validate_issues(rows):
    if type(rows) is not list or any(type(r) is not dict for r in rows):
        _fail("issues_array_invalid")
    for row in rows:
        if row.get("code", "").startswith(_PREFIX):
            _keys(row, {"code", "pointer", "descriptor", "search_key", "detail_code"}, "issue_fields_invalid")
            if not _pointer(row["pointer"]) or not _text(row["detail_code"]):
                _fail("issue_invalid")
            if row["descriptor"] is not None:
                _keys(row["descriptor"], _OWNER, "issue_descriptor_fields_invalid")
            if row["search_key"] is not None:
                _validate_search_key(row["search_key"])
        elif row.get("code", "").startswith("native_blast_metadata_"):
            _keys(row, {"code", "input_key", "consumer", "schema_id", "pointer", "document_key", "search_address", "detail_code"},
                  "public_metadata_issue_fields_invalid")
        else:
            _fail("issue_namespace_invalid")


def _validate_lineage(rows):
    if type(rows) is not list:
        _fail("lineage_array_required")
    for row in rows:
        _keys(row, {"taxid", "rank", "name"}, "lineage_fields_invalid")
        if not _integer(row["taxid"], 1) or not _text(row["rank"]) or row["name"] is not None and type(row["name"]) is not str:
            _fail("lineage_invalid")


def _validate_operand(row):
    _keys(row, {"role", "artifact_key", "record_ordinal", "native_id", "native_title", "subject_ref", "molecule", "length", "selected_interval", "identity"},
          "prepared_operand_fields_invalid")
    if (row["role"] != "query" or not _text(row["artifact_key"]) or not _integer(row["record_ordinal"])
            or any(row[k] is not None and type(row[k]) is not str for k in ("native_id", "native_title", "subject_ref"))
            or row["molecule"] not in _ALPHABETS or not _integer(row["length"], 1)):
        _fail("prepared_operand_invalid")
    interval = row["selected_interval"]
    if interval is not None and (type(interval) is not list or len(interval) != 2 or any(not _integer(v) for v in interval)
            or not 0 <= interval[0] < interval[1] <= row["length"]):
        _fail("prepared_operand_interval_invalid")
    if row["identity"] is not None:
        _keys(row["identity"], {"namespace", "value", "version"}, "prepared_operand_identity_fields_invalid")
        if (not _text(row["identity"]["namespace"]) or not _text(row["identity"]["value"])
                or row["identity"]["version"] is not None and not _text(row["identity"]["version"])):
            _fail("prepared_operand_identity_invalid")


def _validate_reference(row):
    fields = {"identifier_namespace", "accession", "source", "native_pointer", "taxid", "lineage", "functions",
              "origin", "assembly", "sequence_group", "study_groups", "native_record"}
    _keys(row, fields | ({"record_locator"} if "record_locator" in row else set()), "reference_metadata_fields_invalid")
    if "record_locator" in row:
        blast_record_identity(source_ref=row["source"], pointer=row["native_pointer"], record_locator=row["record_locator"])
    if (any(not _text(row[k]) for k in ("identifier_namespace", "accession", "source")) or not _pointer(row["native_pointer"])
            or row["taxid"] is not None and not _integer(row["taxid"], 1) or type(row["origin"]) is not dict
            or any(v is not None and type(v) not in {str, int, float, bool} for v in row["origin"].values())
            or row["sequence_group"] is not None and not _text(row["sequence_group"])
            or type(row["study_groups"]) is not list or any(not _text(v) for v in row["study_groups"])
            or type(row["functions"]) is not list):
        _fail("reference_metadata_invalid")
    _validate_lineage(row["lineage"])
    for function in row["functions"]:
        _keys(function, {"function", "evidence", "source"}, "reference_function_fields_invalid")
        if not _text(function["function"]) or not _text(function["source"]) or type(function["evidence"]) is not list:
            _fail("reference_function_invalid")
    if row["assembly"] is not None:
        _keys(row["assembly"], {"accession", "completeness_fraction", "contamination_fraction", "contig_count", "contig_n50",
            "total_sequence_length", "quality_method", "quality_version", "measurement_methods", "source", "linkage_source"},
            "reference_assembly_fields_invalid")
        _keys(row["assembly"]["measurement_methods"], {"completeness_fraction", "contamination_fraction", "contig_count",
            "contig_n50", "total_sequence_length"}, "reference_assembly_methods_invalid")


def _validate_link(link, kind):
    _keys(link, {"search_key", "binding"}, "sequence_metadata_binding_fields_invalid")
    _validate_search_key(link["search_key"])
    binding = link["binding"]
    shared = {"report_index", "hit_index", "linkage_source_ref", "linkage_pointer"}
    fields = ({"description_index", "metadata_index", "native_description", "metadata_identifier", "metadata_source_ref", "metadata_pointer"}
        if kind == "description" else {"kind", "sequence_group", "algorithm", "digest", "molecule", "sequence_length", "source_ref", "pointer"})
    locator_field = "metadata_record_locator" if kind == "description" else "record_locator"
    _keys(binding, shared | fields | ({locator_field} if locator_field in binding else set()), "sequence_metadata_inner_binding_fields_invalid")
    if locator_field in binding:
        blast_record_identity(source_ref=binding["metadata_source_ref" if kind == "description" else "source_ref"],
            pointer=binding["metadata_pointer" if kind == "description" else "pointer"], record_locator=binding[locator_field])
    if any(not _integer(binding[k]) for k in ("report_index", "hit_index")):
        _fail("sequence_metadata_binding_index_invalid")
    _validate_pointers([_provenance(binding["linkage_source_ref"], binding["linkage_pointer"])])
    if kind == "description":
        if any(not _integer(binding[k]) for k in ("description_index", "metadata_index")):
            _fail("description_binding_index_invalid")
        _keys(binding["native_description"], {"id", "accession", "title", "taxid"}, "native_description_fields_invalid")
        _keys(binding["metadata_identifier"], {"namespace", "value"}, "metadata_identifier_fields_invalid")
        _validate_pointers([_provenance(binding["metadata_source_ref"], binding["metadata_pointer"])])
    else:
        if (binding["kind"] != "full_sequence_digest" or binding["algorithm"] != "sha256" or
                type(binding["digest"]) is not str or re.fullmatch(r"[a-f0-9]{64}", binding["digest"]) is None or
                binding["molecule"] not in {"aa", "nt"} or not _integer(binding["sequence_length"], 1) or
                binding["sequence_group"] != "sha256:" + binding["digest"]):
            _fail("full_sequence_binding_identity_invalid")
        _validate_pointers([_provenance(binding["source_ref"], binding["pointer"])])


def _check_lowered(original, normalized, *, documents, reports, job, field=None):
    """Check saved normalized values against original slots, without a parser.

    Only the public metadata contract's explicit address substitutions may
    differ. Native records, evidence and origin payloads remain literal JSON.
    """
    if field in {"native_record", "evidence", "origin"}:
        return original == normalized
    if type(original) is dict and set(original) == {"output_key", "member_ordinal", "report_index", "search_pointer"}:
        matches = [r for r in reports if r["output_key"] == original["output_key"]]
        return len(matches) == 1 and normalized == dict(artifact_key=matches[0]["artifact_key"],
            **{k: original[k] for k in ("member_ordinal", "report_index", "search_pointer")})
    if type(original) is dict and set(original) == {"document_key", "record_ordinal"} and field == "input_pssm_key":
        doc = documents.get(original["document_key"])
        return doc is not None and normalized == _token([doc["artifact_key"], original["record_ordinal"]])
    if type(original) is list:
        return type(normalized) is list and len(original) == len(normalized) and all(
            _check_lowered(a, b, documents=documents, reports=reports, job=job, field=field) for a, b in zip(original, normalized))
    if type(original) is dict:
        if type(normalized) is not dict:
            return False
        expected_keys = set(original)
        if "database_key" in original and field == "search_bindings":
            expected_keys = expected_keys - {"database_key"} | {"database_identity"}
            expected = [r["identity"] for r in job["databases"] if r["database_key"] == original["database_key"]]
            if normalized.get("database_identity") != (expected[0] if len(expected) == 1 else None):
                return False
        if set(normalized) != expected_keys:
            return False
        return all(_check_lowered(v, normalized[k], documents=documents, reports=reports, job=job, field=k)
            for k, v in original.items() if k != "database_key" or field != "search_bindings")
    if field in {"source", "source_ref", "metadata_source_ref", "linkage_source", "linkage_source_ref"} and type(original) is str:
        return original in documents and normalized == documents[original]["source_ref"]
    return original == normalized


@_saved_validator
def validate_standard_blast_database_binding_result(value: dict) -> dict:
    value = _copy(value)
    _keys(value, _BINDING, "binding_result_fields_invalid")
    if (value["status"] not in {"available", "unavailable", "incompatible"} or
            value["origin"] not in {None, "derived", "supplied"} or type(value["issues"]) is not list or
            (value["binding"] is not None) != (value["status"] == "available") or
            (value["origin"] is not None) != (value["status"] == "available")):
        _fail("binding_result_relationship_invalid")
    _validate_pointers(value["input_pointers"])
    _validate_issues(value["issues"])
    if value["binding"] is not None:
        row = value["binding"]
        _keys(row, {"search_key", "stage", "biological_round", "database_identity", "input_pssm_key", "provenance"}, "search_binding_fields_invalid")
        _validate_search_key(row["search_key"])
        if row["stage"] != "sequence_database" or row["biological_round"] is not None:
            _fail("search_binding_stage_invalid")
        _validate_pointers([row["provenance"]])
        from .native_blast_standard_database_contracts import DATABASE_IDENTITY_SCHEMA
        if not Draft202012Validator(DATABASE_IDENTITY_SCHEMA).is_valid(row["database_identity"]):
            _fail("search_binding_database_identity_invalid")
        if row["input_pssm_key"] is not None and not _text(row["input_pssm_key"]):
            _fail("search_binding_pssm_key_invalid")
    return value


@_saved_validator
def validate_standard_blast_sequence_metadata_result(value: dict) -> dict:
    value = _copy(value)
    _keys(value, _SEQUENCE, "sequence_metadata_result_fields_invalid")
    _validate_search_key(value["search_key"])
    _validate_pointers(value["input_pointers"])
    _validate_issues(value["issues"])
    for field in ("reference_metadata", "description_bindings", "sequence_identity_bindings", "issues"):
        if type(value[field]) is not list or any(type(r) is not dict for r in value[field]):
            _fail("sequence_metadata_result_array_invalid")
    for field in ("target_context", "database_profile"):
        if value[field] is not None and type(value[field]) is not dict:
            _fail("sequence_metadata_result_context_invalid")
    for row in value["reference_metadata"]:
        _validate_reference(row)
    for field in ("description_bindings", "sequence_identity_bindings"):
        seen = set()
        for row in value[field]:
            _validate_link(row, "description" if field == "description_bindings" else "sequence")
            if row["search_key"] != value["search_key"] or _token(row) in seen:
                _fail("sequence_metadata_binding_address_conflict")
            seen.add(_token(row))
            if field == "description_bindings" and row["binding"]["metadata_index"] >= len(value["reference_metadata"]):
                _fail("sequence_metadata_binding_index_invalid")
    target = value["target_context"]
    if target is not None:
        _keys(target, {"query_operand", "taxid", "lineage", "independent_of_search", "source"}, "target_context_fields_invalid")
        _validate_lineage(target["lineage"])
        _validate_pointers([target["source"]])
        _validate_operand(target["query_operand"])
        if (target["taxid"] is not None and not _integer(target["taxid"], 1)
                or target["independent_of_search"] is not None and type(target["independent_of_search"]) is not bool):
            _fail("target_context_invalid")
    profile = value["database_profile"]
    if profile is not None:
        _keys(profile, {"database", "release", "scope", "count_unit", "total_count", "function_counts", "source"}, "database_profile_fields_invalid")
        if (any(not _text(profile[k]) for k in ("database", "scope", "source"))
                or profile["release"] is not None and not _text(profile["release"])
                or profile["count_unit"] not in {"unique_sequences", "sequence_groups"}
                or not _integer(profile["total_count"], 1) or type(profile["function_counts"]) is not dict
                or any(not _text(k) or not _integer(v) for k, v in profile["function_counts"].items())):
            _fail("database_profile_invalid")
    return value


def _validate_saved_metadata(prepared, files):
    job, bundle = _job(prepared), _attempt(prepared)["bundle"]
    reports = [r for r in files.entries.values() if r["role"] == "primary_report"]
    for row in prepared["metadata"]:
        _keys(row, {"consumer", "schema_id", "input_key", "artifact_ref", "sha256", "status", "payload", "normalized",
                    "normalization_map", "issues", "descriptor"}, "metadata_result_fields_invalid")
        _validate_descriptor(row["descriptor"])
        if (any(row[k] != row["descriptor"][k] for k in (*_OWNER, "artifact_ref", "sha256"))
                or row["status"] not in {"valid", "invalid", "unsupported"}
                or type(row["normalization_map"]) is not list):
            _fail("metadata_result_identity_invalid")
        _validate_issues(row["issues"])
        if row["status"] != "valid":
            if row["normalized"] is not None or row["normalization_map"]:
                _fail("invalid_metadata_has_normalization")
            continue
        if (row["consumer"], row["schema_id"]) not in _TUPLES:
            _fail("metadata_tuple_unregistered")
        if not Draft202012Validator(_schema_for(row["consumer"], row["schema_id"])).is_valid(row["payload"]):
            _fail("metadata_payload_fields_invalid")
        source = files.by_ref.get(row["artifact_ref"])
        if (source is None or source["sha256"] != row["sha256"] or source["size_bytes"] != row["descriptor"]["size_bytes"]
                or files.json(source) != row["payload"]):
            _fail("saved_metadata_payload_source_conflict")
        fields = {"schema", "documents"} | ({"sequence_records", "effective_msa_masters", "master_subjects", "search_bindings", "target_contexts"}
            if row["consumer"] == "query_identity" else {"searches"})
        normalized, payload = row["normalized"], row["payload"]
        _keys(normalized, fields, "metadata_normalized_fields_invalid")
        _keys(payload, fields, "metadata_payload_fields_invalid")
        if normalized["schema"] != row["schema_id"] or payload["schema"] != row["schema_id"]:
            _fail("metadata_normalized_schema_conflict")
        addresses, originals = {}, set()
        for mapping in row["normalization_map"]:
            _keys(mapping, {"normalized_pointer", "payload_pointer"}, "normalization_map_fields_invalid")
            new, original = mapping["normalized_pointer"], mapping["payload_pointer"]
            if (not _pointer(new) or not _pointer(original) or new in addresses or original in originals
                    or len(new.split("/")) != 3 or len(original.split("/")) != 3
                    or new.split("/")[1] != original.split("/")[1]):
                _fail("normalization_map_address_invalid")
            addresses[new], _ = original, _at(payload, original)
            originals.add(original)
        expected = {f"/{field}/{i}" for field in fields - {"schema"} for i in range(len(normalized[field]))}
        if set(addresses) != expected:
            _fail("normalization_map_coverage_invalid")
        docs = {}
        for i, doc in enumerate(normalized["documents"]):
            _keys(doc, {"document_key", "artifact", "format", "artifact_key", "artifact_ref", "source_ref", "sha256", "size_bytes"},
                  "normalized_document_fields_invalid")
            declaration = _at(payload, addresses[f"/documents/{i}"])
            actual = _resolve(declaration, files=files, job=job, bundle=bundle)
            actual.pop("contents")
            if actual != doc or doc["document_key"] in docs:
                _fail("normalized_document_source_conflict")
            docs[doc["document_key"]] = doc
        for field in fields - {"schema", "documents"}:
            if type(normalized[field]) is not list:
                _fail("metadata_normalized_array_invalid")
            for i, item in enumerate(normalized[field]):
                original = _at(payload, addresses[f"/{field}/{i}"])
                if not _check_lowered(original, item, documents=docs, reports=reports, job=job, field=field):
                    _fail("metadata_original_slot_conflict")


def _validate_pssm_sources(prepared):
    for sheet in prepared["pssm_sheets"]:
        _keys(sheet, {"schema", "artifact_key", "source_ref", "format", "input_identity", "status", "native_text", "pssms", "issues"},
              "pssm_sheet_fields_invalid")
        source = _one([r for r in prepared["resolved_documents"] if r["kind"] == "captured"
            and r["catalog"]["artifact_key"] == sheet["artifact_key"] and r["status"] == "available"], "pssm_source_unavailable")
        if (sheet["schema"] != "blast_pssm_sheet_v1" or sheet["format"] != "scoremat_asn_text"
                or sheet["status"] not in {"unavailable", "incompatible", "partial", "complete"}
                or type(sheet["pssms"]) is not list or type(sheet["issues"]) is not list
                or sheet["source_ref"] != source["catalog"]["source_ref"]
                or sheet["input_identity"] != {k: source["catalog"][k] for k in ("sha256", "size_bytes")}):
            _fail("pssm_source_identity_conflict")
        if sheet["native_text"] is not None and sheet["native_text"].encode() != bytes.fromhex(source["contents_hex"]):
            _fail("pssm_native_text_conflict")
        seen = set()
        for row in sheet["pssms"]:
            _keys(row, {"record_ordinal", "pssm_key", "character_span", "native_type", "native_record", "native_pssm", "native_params", "issues"},
                  "pssm_record_fields_invalid")
            if (not _integer(row["record_ordinal"]) or row["record_ordinal"] in seen or
                    row["pssm_key"] != _token([sheet["artifact_key"], row["record_ordinal"]]) or
                    row["native_type"] not in {"Pssm", "PssmWithParameters"} or
                    type(row["native_record"]) is not dict or type(row["native_pssm"]) is not dict or
                    row["native_params"] is not None and type(row["native_params"]) is not dict or type(row["issues"]) is not list):
                _fail("pssm_record_identity_conflict")
            seen.add(row["record_ordinal"])


def _validate_saved_proofs(prepared):
    seen = set()
    for row in prepared["sequence_proofs"]:
        _keys(row, {"descriptor", "search_key", "pointer", "binding_index", "proof_index", "binding", "proof", "document", "symbols", "status", "issues"},
              "sequence_proof_fields_invalid")
        _keys(row["descriptor"], _OWNER, "proof_descriptor_fields_invalid")
        _validate_search_key(row["search_key"])
        _validate_issues(row["issues"])
        if (not _pointer(row["pointer"]) or not _integer(row["binding_index"])
                or row["proof_index"] is not None and not _integer(row["proof_index"])
                or row["status"] not in {"available", "unavailable", "incompatible"}):
            _fail("sequence_proof_invalid")
        identity = _token([row["descriptor"], row["pointer"]])
        if identity in seen:
            _fail("sequence_proof_address_duplicate")
        seen.add(identity)
        validation = _one([r for r in _valid(prepared, "sequence_database") if _owner(r) == row["descriptor"]], "proof_metadata_unavailable")
        units = [(i, u) for i, u in enumerate(validation["normalized"]["searches"]) if u["search_key"] == row["search_key"]
            and _original(validation, f"/searches/{i}/sequence_identity_bindings/{row['binding_index']}") == row["pointer"]]
        _, unit = _one(units, "proof_original_slot_unresolved")
        if unit["sequence_identity_bindings"][row["binding_index"]] != row["binding"]:
            _fail("proof_original_binding_conflict")
        if row["proof"] is not None and (row["proof_index"] is None or unit["sequence_proofs"][row["proof_index"]] != row["proof"]):
            _fail("proof_original_proof_conflict")
        if row["status"] != "available":
            continue
        binding, proof, symbols = row["binding"]["binding"], row["proof"], row["symbols"]
        _validate_link(row["binding"], "sequence")
        if (proof is None or type(symbols) is not str or not symbols or not symbols.isascii()
                or len(symbols) != proof["length"] or _sha(symbols.encode()) != proof["sha256"]
                or any(proof[a] != binding[b] for a, b in (("sha256", "digest"), ("length", "sequence_length"), ("molecule", "molecule")))
                or proof["binding_index"] != row["binding_index"]):
            _fail("saved_sequence_proof_identity_conflict")
        doc = _one([d for d in validation["normalized"]["documents"] if d["document_key"] == proof["document_key"]], "proof_document_unavailable")
        if row["document"] != doc or doc["source_ref"] != binding["source_ref"]:
            _fail("proof_document_identity_conflict")
        if validation["schema_id"] == _SEQUENCE_V2:
            locator = binding["record_locator"]
            if ((doc["format"] == "fasta") != (locator is not None)
                    or proof["representation"] == "fasta_record" and (
                        locator is None or locator["record_ordinal"] != proof["record_ordinal"] or proof["sequence_pointer"] is not None)
                    or proof["representation"] == "json_sequence" and (doc["format"] != "json" or locator is not None
                        or proof["record_ordinal"] is not None or not (proof["sequence_pointer"] == binding["pointer"]
                            or proof["sequence_pointer"].startswith(binding["pointer"] + "/")))
                    or binding["molecule"] != standard_blast_database_program_spec(_job(prepared)["program"])["reference_coordinate_unit"]
                    or not set(symbols) <= set(_ALPHABETS["protein"] if binding["molecule"] == "aa" else "ACGTURYSWKMBDHVN")
                    or any(issue["pointer"] == row["pointer"] + "/binding/record_locator" for issue in validation["issues"])):
                _fail("saved_sequence_proof_record_locator_conflict")
        if proof["representation"] == "json_sequence":
            saved = _one([r for r in prepared["resolved_documents"] if r["catalog"]["artifact_ref"] == doc["artifact_ref"]
                and r["catalog"]["source_ref"] == doc["source_ref"] and r["status"] == "available"], "proof_source_unavailable")
            if _at(saved["decoded_json"], proof["sequence_pointer"]) != symbols:
                _fail("proof_original_symbols_conflict")


def _validate_saved_sequence_relations(search, binding_result, metadata, prepared):
    """Check existing rows against saved originals, without populating any row."""
    key, status = search["search_key"], _search_status(search, prepared)[0]
    binding = binding_result["binding"]
    if binding is not None:
        job, native_db = _job(prepared), search["normalized"]["search"]["database"]
        database = job["databases"][0]
        if (status != "available" or binding["database_identity"] != database["identity"]
                or native_db is not None and native_db not in {database["identity"]["value"], " ".join(database["native_paths"])}
                or not any(r["kind"] == "database" and r["status"] == "available"
                    and r["value"]["database_key"] == database["database_key"] for r in prepared["source_relations"])):
            _fail("saved_binding_original_database_conflict")
        expected_context = resolve_blast_program_context(execution_program=job["program"], reported_program=search["native"]["report"].get("program"),
            scientific_mode="database", query_kind=job["query"]["kind"], reference_kind="sequence", native_version=search["native"]["report"].get("version"))
        if search["program_context"] != expected_context or expected_context["geometry_program"] != job["program"]:
            _fail("saved_binding_original_program_conflict")
        supplied = [r for v in _valid(prepared, "query_identity") for r in v["normalized"]["search_bindings"] if r["search_key"] == key]
        if binding_result["origin"] == "supplied":
            if supplied != [binding]:
                _fail("saved_binding_original_supplied_conflict")
        elif supplied or binding["provenance"] != _provenance(_attempt(prepared)["bundle_source_ref"], "/requested_job/native_blast_standard_database"):
            _fail("saved_binding_original_provenance_conflict")
        keys = [r["pssm_key"] for s in prepared["pssm_sheets"] for r in s["pssms"]]
        expected_pssm = keys[0] if job["query"]["kind"] == "pssm" and len(keys) == 1 else None
        if binding["input_pssm_key"] != expected_pssm:
            _fail("saved_binding_original_pssm_conflict")
    units = [(v, u) for v in _valid(prepared, "sequence_database") for u in v["normalized"]["searches"] if u["search_key"] == key]
    if status != "available":
        units = []
    total = sum(len(u["reference_metadata"]) for _, u in units)
    if len(metadata["reference_metadata"]) != total:
        _fail("saved_reference_metadata_count_conflict")
    offset = 0
    allowed_descriptions = []
    for validation, unit in units:
        ui = next(i for i, candidate in enumerate(validation["normalized"]["searches"]) if candidate is unit)
        for index, original in enumerate(unit["reference_metadata"]):
            saved = metadata["reference_metadata"][offset + index]
            if any(saved[k] != original[k] for k in original if k != "functions") or saved["functions"] != (
                    [] if _feature_scoped(original) else original["functions"]):
                _fail("saved_reference_metadata_original_conflict")
        for bi, link in enumerate(unit["description_bindings"]):
            if link["binding"]["metadata_index"] < len(unit["reference_metadata"]) and not (
                    validation["schema_id"] == _SEQUENCE_V2 and (
                        _record_relation_failed(validation, f"/searches/{ui}/description_bindings/{bi}/binding") or
                        _record_relation_failed(validation, f"/searches/{ui}/reference_metadata/{link['binding']['metadata_index']}"))):
                allowed_descriptions.append((link, offset))
        offset += len(unit["reference_metadata"])
    for link in metadata["description_bindings"]:
        if not any(link["search_key"] == original["search_key"] and all(link["binding"][k] == original["binding"][k]
            for k in original["binding"] if k != "metadata_index") and link["binding"]["metadata_index"] == original["binding"]["metadata_index"] + offset
            for original, offset in allowed_descriptions):
            _fail("saved_description_original_relation_conflict")
    molecule = standard_blast_database_program_spec(_job(prepared)["program"])["reference_coordinate_unit"]
    for link in metadata["sequence_identity_bindings"]:
        if (link["binding"]["molecule"] != molecule or status != "available" or
                not any(p["status"] == "available" and p["binding"] == link for p in prepared["sequence_proofs"])):
            _fail("saved_sequence_original_proof_conflict")
    profiles = _unique([u["database_profile"] for _, u in units if u["database_profile"] is not None])
    if metadata["database_profile"] != (profiles[0] if len(profiles) == 1 else None):
        _fail("saved_population_original_relation_conflict")
    target = metadata["target_context"]
    if target is not None:
        originals = [r for v in _valid(prepared, "query_identity") for r in v["normalized"]["target_contexts"] if r["search_key"] == key]
        if (status != "available" or len(originals) != 1 or target["query_operand"] != search["operand_binding"]
                or any(target[k] != originals[0][k] for k in ("taxid", "lineage", "independent_of_search", "source"))):
            _fail("saved_target_original_relation_conflict")


@_saved_validator
def validate_standard_blast_database_prepared_inputs(value: dict) -> dict:
    """Validate saved detached inputs and the original N attempt without I/O."""
    value = _copy(value)
    _keys(value, _PREPARED, "prepared_inputs_fields_invalid")
    if value["schema"] != PREPARED_INPUTS_SCHEMA:
        _fail("prepared_inputs_schema_invalid")
    for field in _PREPARED - {"schema", "invocation"}:
        if type(value[field]) is not list:
            _fail("prepared_inputs_array_invalid")
    _validate_issues(value["issues"])
    for relation in value["source_relations"]:
        _keys(relation, {"kind", "descriptor", "pointer", "status", "value", "input_pointers"}, "source_relation_fields_invalid")
        if (relation["kind"] not in {"attempt", "database", "subject", "pssm_master", "metadata"}
                or relation["status"] not in {"available", "unavailable", "incompatible"} or not _pointer(relation["pointer"])):
            _fail("source_relation_invalid")
        _validate_pointers(relation["input_pointers"])
        if relation["descriptor"] is not None:
            _keys(relation["descriptor"], _OWNER, "source_relation_descriptor_fields_invalid")
        if relation["kind"] == "metadata" and relation["value"] is not None:
            _fail("metadata_qualification_has_value")
        if relation["kind"] == "subject":
            _keys(relation["value"], {"snapshot", "sequence"}, "subject_relation_fields_invalid")
            if relation["status"] == "available":
                snapshot, sequence = relation["value"]["snapshot"], relation["value"]["sequence"]
                fields = {"subject_ref", "sequence_artifact_ref", "molecule", "length", "sequence_sha256"}
                if (type(snapshot) is not dict or set(snapshot) - fields - {"record_type", "sequence_path"} or not fields <= snapshot.keys()
                        or snapshot["molecule"] not in _ALPHABETS or type(sequence) is not str or not sequence.isascii()
                        or not set(sequence) <= set(_ALPHABETS[snapshot["molecule"]])
                        or len(sequence) != snapshot["length"] or _sha(sequence.encode()) != snapshot["sequence_sha256"]):
                    _fail("saved_subject_identity_conflict")
        if relation["kind"] == "pssm_master":
            master = relation["value"]
            _keys(master, {"schema", "artifact_key", "source_ref", "input_identity", "records", "issues"}, "master_metadata_fields_invalid")
            if master["schema"] != "blast_pssm_master_metadata_v1":
                _fail("master_metadata_schema_invalid")
            for record in master["records"]:
                _keys(record, {"pssm_key", "record_ordinal", "master", "issues"}, "master_record_fields_invalid")
                axis = record["master"]
                _keys(axis, {"status", "encoding", "reported_length", "decoded_length", "sequence", "column_to_residue"}, "master_axis_fields_invalid")
                if record["pssm_key"] != _token([master["artifact_key"], record["record_ordinal"]]):
                    _fail("master_record_identity_conflict")
                if axis["status"] == "complete" and (axis["decoded_length"] != len(axis["sequence"])
                        or axis["reported_length"] != axis["decoded_length"]
                        or axis["column_to_residue"] != [dict(column=i, master_position=None if s == "-" else i, symbol=s)
                            for i, s in enumerate(axis["sequence"])]):
                    _fail("master_column_mapping_conflict")
    invocation = value["invocation"]
    _keys(invocation, {"execution_program", "scientific_mode", "resource_kind", "query_kind", "reference_kind",
        "request", "effective_options", "operands", "completion"}, "invocation_fields_invalid")
    job = validate_standard_blast_database_job(_job(value))
    attempt = _attempt(value)
    _keys(attempt, {"bundle", "attempt_identity", "bundle_source_ref", "bundle_artifact_ref", "bundle_sha256"}, "prepared_attempt_fields_invalid")
    validate_standard_blast_database_bundle(attempt["bundle"], original_job=job, attempt_identity=attempt["attempt_identity"])
    if (type(attempt["bundle_sha256"]) is not str or re.fullmatch(r"[0-9a-f]{64}", attempt["bundle_sha256"]) is None
            or invocation["request"] != requested_job_from_standard_blast_database(job)):
        _fail("prepared_attempt_identity_conflict")
    context = dict(execution_program=job["program"], scientific_mode="database", resource_kind="hpc",
                   query_kind=job["query"]["kind"], reference_kind="sequence")
    if any(invocation[k] != v for k, v in context.items()):
        _fail("prepared_invocation_context_conflict")
    options = validate_standard_blast_database_options(job["program"], job["options"], query_kind=job["query"]["kind"])
    options.update(requested_hit_limit=int(options["-max_target_seqs"]) if "-max_target_seqs" in options else None,
        requested_hsp_limit=int(options["-max_hsps"]) if "-max_hsps" in options else None)
    if invocation["effective_options"] != options or type(invocation["operands"]) is not list:
        _fail("prepared_original_options_conflict")
    process = attempt["bundle"]["process"]
    if invocation["completion"] != dict(native_returncode=process["returncode"],
        producer_complete=process["started"] and process["returncode"] == 0 and not attempt["bundle"]["failures"]):
        _fail("prepared_completion_conflict")
    seen = set()
    for row in value["query_records"]:
        _keys(row, _RECORD, "query_record_fields_invalid")
        key = row["artifact_key"], row["record_ordinal"]
        if (key in seen or not _integer(row["record_ordinal"]) or not _integer(row["length"], 1) or
                type(row["sequence"]) is not str or not row["sequence"].isascii() or len(row["sequence"]) != row["length"] or
                _sha(row["sequence"].encode()) != row["sequence_sha256"] or row["molecule"] not in _ALPHABETS or
                row["binding_status"] not in {"available", "unavailable", "incompatible"} or
                (row["subject_ref"] is not None) != (row["binding_status"] == "available")):
            _fail("query_record_identity_invalid")
        seen.add(key)
    for row in value["resolved_documents"]:
        _keys(row, {"kind", "catalog", "status", "contents_hex", "decoded_json"}, "resolved_document_fields_invalid")
        if row["kind"] not in {"captured", "received"} or row["status"] not in {"available", "unavailable", "incompatible"}:
            _fail("resolved_document_status_invalid")
        if row["status"] == "available":
            try:
                raw = bytes.fromhex(row["contents_hex"])
            except (ValueError, TypeError):
                _fail("resolved_document_bytes_invalid")
            if len(raw) != row["catalog"]["size_bytes"] or _sha(raw) != row["catalog"]["sha256"]:
                _fail("resolved_document_identity_conflict")
            if row["decoded_json"] is not None and _decode(raw) != row["decoded_json"]:
                _fail("resolved_document_decoding_conflict")
        elif row["contents_hex"] is not None or row["decoded_json"] is not None:
            _fail("unavailable_document_has_content")
    catalog = {k: attempt[k] for k in ("bundle_source_ref", "bundle_artifact_ref", "bundle_sha256")}
    catalog.update(entries=[r["catalog"] for r in value["resolved_documents"] if r["kind"] == "captured"],
                   retained_sources=[r["catalog"] for r in value["resolved_documents"] if r["kind"] == "received"])
    contents = {r["catalog"]["artifact_ref"]: bytes.fromhex(r["contents_hex"]) for r in value["resolved_documents"] if r["status"] == "available"}
    files = _Supplied(catalog, contents, attempt["bundle"])
    _validate_saved_metadata(value, files)
    _validate_pssm_sources(value)
    _validate_saved_proofs(value)
    for row in value["query_records"]:
        source = files.entries.get(row["artifact_key"])
        if (source is None or source["input_key"] != job["query"]["input_key"] or row["input_key"] != source["input_key"]
                or row["artifact_ref"] != source["artifact_ref"]):
            _fail("query_original_source_conflict")
        if row["subject_ref"] is not None:
            subjects = [r["value"] for r in value["source_relations"] if r["kind"] == "subject" and r["status"] == "available"
                and r["value"]["snapshot"]["subject_ref"] == row["subject_ref"]]
            if len(subjects) != 1:
                _fail("query_received_subject_ambiguous")
            snapshot = subjects[0]["snapshot"]
            if (subjects[0]["sequence"] != row["sequence"] or any(snapshot[k] != row[k] for k in ("molecule", "length", "sequence_sha256"))
                    or snapshot.get("record_type") not in {None, "input", "feature", "product", "read_subject"}):
                _fail("query_received_subject_identity_conflict")
            field = "sequence_records" if job["query"]["kind"] == "sequence" else "master_subjects"
            links = [r for v in _valid(value, "query_identity") for r in v["normalized"][field]
                if r["input_key"] == row["input_key"] and r["record_ordinal"] == row["record_ordinal"]]
            if len(links) != 1 or links[0]["subject_ref"] != row["subject_ref"]:
                _fail("query_original_subject_relation_conflict")
    seen = set()
    for operand in invocation["operands"]:
        _validate_operand(operand)
        key = operand["artifact_key"], operand["record_ordinal"]
        row = _one([r for r in value["query_records"] if (r["artifact_key"], r["record_ordinal"]) == key], "query_operand_original_record_unresolved")
        if (key in seen or operand["role"] != "query" or any(operand[k] != row[k] for k in operand if k not in {"role", "identity"})):
            _fail("query_operand_identity_conflict")
        seen.add(key)
    databases = [r for r in value["source_relations"] if r["kind"] == "database"]
    if len(databases) != len(job["databases"]):
        _fail("database_source_relations_incomplete")
    for i, relation in enumerate(databases):
        db, captured = job["databases"][i], attempt["bundle"]["database_manifest"][i]
        if relation["value"] != dict(database_key=db["database_key"], native_paths=db["native_paths"], manifest_artifact_key=captured["manifest_artifact_key"]):
            _fail("database_source_relation_conflict")
        if relation["status"] == "available" and (files.json(files.entries[captured["manifest_artifact_key"]]) != db["manifest"]
                or any(r["status"] != "verified" for r in captured["checks"])):
            _fail("database_available_without_custody")
    return value


@_saved_validator
def validate_standard_blast_database_sheet_set(value: dict) -> dict:
    """Validate saved sheet shape and exact source-qualified component relations."""
    value = _copy(value)
    _keys(value, _SHEETS, "sheet_set_fields_invalid")
    if value["schema"] != SHEET_SET_SCHEMA:
        _fail("sheet_set_schema_invalid")
    prepared = validate_standard_blast_database_prepared_inputs(value["prepared_inputs"])
    if value["collection"]["invocation"] != prepared["invocation"] or value["pssm"] != prepared["pssm_sheets"]:
        _fail("sheet_set_input_conflict")
    _keys(value["collection"], {"schema", "invocation", "artifacts", "searches", "issues"}, "collection_fields_invalid")
    if value["collection"]["schema"] != "blast_report_collection_v1" or value["metadata_parse_results"] != prepared["metadata"]:
        _fail("sheet_set_collection_metadata_conflict")
    _validate_issues(value["issues"])
    searches = value["collection"]["searches"]
    if len({_token(s["search_key"]) for s in searches}) != len(searches):
        _fail("sheet_set_search_key_duplicate")
    if len(value["sequence"]) != len(searches) or len(value["search_bindings"]) != len(searches) or len(value["metadata_binding_results"]) != len(searches):
        _fail("sheet_set_search_population_conflict")
    for index, (search, row) in enumerate(zip(searches, value["sequence"])):
        _keys(row, {"search_key", "sheet"}, "sequence_sheet_entry_fields_invalid")
        if row["search_key"] != search["search_key"] or row["sheet"]["search"] != search:
            _fail("sheet_set_search_relation_conflict")
        binding = validate_standard_blast_database_binding_result(value["search_bindings"][index])
        metadata = validate_standard_blast_sequence_metadata_result(value["metadata_binding_results"][index])
        if metadata["search_key"] != row["search_key"] or binding["binding"] is not None and binding["binding"] != row["sheet"]["search_binding"]:
            _fail("sheet_set_binding_relation_conflict")
        sheet = row["sheet"]
        _keys(sheet, {"schema", "search", "report_source", "search_binding", "query_binding", "reference_metadata",
            "description_bindings", "sequence_identity_bindings", "target_context", "database_profile"}, "sequence_sheet_fields_invalid")
        if sheet["schema"] not in {"blast_sequence_database_result_sheet_v1", "blast_sequence_database_result_sheet_v2"}:
            _fail("sequence_sheet_schema_invalid")
        # The saved declared version is authoritative; never redispatch by fields.
        from .blast_sequence_database import _validate as validate_sequence_sheet
        validate_sequence_sheet(sheet)
        report = _report(search, prepared)["catalog"]
        expected_source = dict(artifact_key=search["search_key"]["artifact_key"], artifact_ref=report["artifact_ref"],
                               member_ordinal=None, member_sha256=None)
        if sheet["report_source"] != expected_source or sheet["query_binding"] != _query_binding(search, prepared):
            _fail("sequence_sheet_original_source_conflict")
        _validate_saved_sequence_relations(search, binding, metadata, prepared)
        if binding["binding"] is None and sheet["search_binding"] != dict(search_key=search["search_key"], stage=None,
                biological_round=None, database_identity=None, input_pssm_key=None, provenance=None):
            _fail("sheet_set_unavailable_binding_conflict")
        for field in ("reference_metadata", "description_bindings", "sequence_identity_bindings", "target_context", "database_profile"):
            if row["sheet"][field] != metadata[field]:
                _fail("sheet_set_metadata_relation_conflict")
    return value


__all__ = ["prepare_standard_blast_database_inputs", "populate_standard_blast_database_sheets",
    "derive_standard_blast_database_search_binding", "qualify_standard_blast_sequence_metadata",
    "validate_standard_blast_database_prepared_inputs", "validate_standard_blast_database_sheet_set",
    "validate_standard_blast_database_binding_result", "validate_standard_blast_sequence_metadata_result",
    "PREPARED_INPUTS_SCHEMA", "SHEET_SET_SCHEMA"]
