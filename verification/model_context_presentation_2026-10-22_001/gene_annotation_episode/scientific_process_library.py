"""Immutable, run-owned scientific process options and instruction provenance.

Only the index stays resident. Bodies and source rows are selected disk reads;
neither is published as scientific evidence or used to select work.
"""
from __future__ import annotations

from copy import deepcopy
import errno
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tempfile

from jsonschema import Draft202012Validator
from method_loop.durable import canonical

from .scientific_process_records import (OPTION_REF_VERSION, SLOTS, _exact,
    _option_id, _plain, _sha256, _text, scientific_digest, validate_option_ref)
from .scientific_support_metadata import validate_support_entry


SOURCE_FORMAT = "research_three_slot_options_v1"
SNAPSHOT_VERSION = "scientific_process_library_snapshot_v2"
_SOURCE_FIELDS = "case_group case_id source_url source_locator observation limit"
_INDEX_FIELDS = "id slot name description detail_path source_evidence_ids"
_SAVED_FIELDS = ("option_id slot name description entry_path entry_sha256 "
    "entry_file_sha256 sources_path sources_sha256 sources_file_sha256 "
    "source_count source_evidence_ids")


def _bytes_digest(data):
    return hashlib.sha256(data).hexdigest()


def _load(path, code):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(code)
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError(code)

    data = path.read_bytes()
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=pairs,
                           parse_constant=invalid_constant)
        return _plain(value), data
    except (ValueError, UnicodeError, RecursionError) as error:
        raise ValueError(code) from error


def _relative(value, code):
    _text(value, code)
    path = PurePosixPath(value)
    if (path.is_absolute() or "\\" in value or "\x00" in value or
            any(part in ("", ".", "..") for part in value.split("/"))):
        raise ValueError(code)


def _within(root, relative, code):
    _relative(relative, code)
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(code)
    return path


def _texts(value, code, *, unique=False):
    if not isinstance(value, list):
        raise ValueError(code)
    for item in value:
        _text(item, code)
    if unique and len(value) != len(set(value)):
        raise ValueError(code)


def _validate_source_index(value):
    code = "scientific_process_source_index_invalid"
    _exact(value, "format status slots entries", code)
    if value["format"] != SOURCE_FORMAT:
        raise ValueError(code)
    _text(value["status"], code)
    if not isinstance(value["slots"], list) or not isinstance(value["entries"], list):
        raise ValueError(code)
    slots = {}
    for slot in value["slots"]:
        _exact(slot, "slot catalog count", code)
        name = slot["slot"]
        if not isinstance(name, str) or name not in (*SLOTS, "tools") or name in slots:
            raise ValueError(code)
        _relative(slot["catalog"], code)
        if type(slot["count"]) is not int or slot["count"] < 0:
            raise ValueError(code)
        slots[name] = slot["count"]
    if not set(SLOTS) <= set(slots) or set(slots) - {*SLOTS, "tools"}:
        raise ValueError(code)
    ids, paths, evidence_ids, counts = set(), set(), set(), dict.fromkeys(slots, 0)
    for entry in value["entries"]:
        _exact(entry, _INDEX_FIELDS, code)
        if entry["slot"] == "tools":
            if re.fullmatch(r"T[0-9]+", entry["id"]) is None:
                raise ValueError(code)
        else:
            _option_id(entry["id"], entry["slot"], code)
        for name in ("name", "description"):
            _text(entry[name], code)
        _relative(entry["detail_path"], code)
        _texts(entry["source_evidence_ids"], code, unique=True)
        if entry["id"] in ids or entry["detail_path"] in paths:
            raise ValueError("scientific_process_option_duplicate")
        ids.add(entry["id"])
        paths.add(entry["detail_path"])
        for evidence_id in entry["source_evidence_ids"]:
            if (re.fullmatch(r"E-" + entry["id"] + r"-[0-9]+", evidence_id) is None or
                    evidence_id in evidence_ids):
                raise ValueError("scientific_process_source_reference_invalid")
            evidence_ids.add(evidence_id)
        counts[entry["slot"]] += 1
    if slots != counts:
        raise ValueError(code)
    return value


def _validate_entry(value):
    code = "scientific_process_entry_invalid"
    if not isinstance(value, dict):
        raise ValueError(code)
    if "entry_version" in value:
        return validate_support_entry(value)
    if not {"id", "slot", "name", "description", "evidence"} <= value.keys():
        raise ValueError(code)
    _option_id(value["id"], value["slot"], code)
    for key in ("name", "description"):
        _text(value[key], code)
    if not isinstance(value["evidence"], list):
        raise ValueError(code)
    for evidence in value["evidence"]:
        _exact(evidence, _SOURCE_FIELDS, code)
        for field in evidence.values():
            _text(field, code)
    if value["slot"] == "annotation_distinction":
        for key in ("claim_scope", "boundary"):
            _text(value.get(key), code)
        for key in ("distinctions", "not_established"):
            _texts(value.get(key), code)
    elif value["slot"] == "thought_pattern":
        for key in ("use_when", "boundary"):
            _text(value.get(key), code)
        for key in ("live_alternatives", "decision_guidance"):
            _texts(value.get(key), code)
        if not isinstance(value.get("outcome_contingencies"), list):
            raise ValueError(code)
        for contingency in value["outcome_contingencies"]:
            _exact(contingency, "if_observed then_consider", code)
            for field in contingency.values():
                _text(field, code)
    return value


def _validate_rows(rows, entry, source_ids):
    code = "scientific_process_source_reference_invalid"
    if not isinstance(rows, list) or len(rows) != len(source_ids):
        raise ValueError(code)
    evidence = []
    for row, evidence_id in zip(rows, source_ids):
        _exact(row, "evidence_id option_id " + _SOURCE_FIELDS, code)
        for field in row.values():
            _text(field, code)
        if row["evidence_id"] != evidence_id or row["option_id"] != entry["id"]:
            raise ValueError(code)
        evidence.append({key: row[key] for key in _SOURCE_FIELDS.split()})
    if evidence != entry["evidence"]:
        raise ValueError("scientific_process_source_entry_mismatch")


def _object(properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


def catalog():
    text = {"type": "string", "minLength": 1}
    digest = {"type": "string", "pattern": "^[a-f0-9]{64}$"}
    offset = {"type": "integer", "minimum": 0}
    limit = {"type": "integer", "minimum": 1}
    reference = _object({"version": {"const": OPTION_REF_VERSION},
        "library_id": digest, "slot": {"enum": list(SLOTS)},
        "option_id": {"type": "string", "pattern": "^[AP][0-9]+$"},
        "entry_sha256": digest})
    return [
        {"name": "process.search", "description":
         "Search/page frozen scientific process option metadata by slot and literal case-insensitive all-term query. process.entry supplies scientific-support operands and current annotation routes. Discovery selects no work and grants no capabilities.",
         "input_schema": _object({"slot": {"enum": [*SLOTS, None]},
             "query": {"type": "string"}, "offset": offset, "limit": limit})},
        {"name": "process.entry", "description":
         "Read one exact frozen option body by known A/P option ID. Scientific-support bodies expose their operands and the host's current annotation routes; instruction content does not define the parent's return form.",
         "input_schema": _object({"option_id": text})},
        {"name": "process.sources", "description":
         "Page the instruction provenance supporting a fully pinned option. Case evidence and E identifiers are library provenance, not new scientific observations.",
         "input_schema": _object({"option_ref": reference,
             "offset": offset, "limit": limit})},
    ]


def _paging(offset, limit):
    if type(offset) is not int or offset < 0 or type(limit) is not int or limit <= 0:
        raise ValueError("scientific_process_arguments_invalid")


class ScientificProcessLibrary:
    @classmethod
    def freeze(cls, directory, *, source):
        directory, source = Path(directory), Path(source)
        if (directory / "index.json").is_file():
            # A previous run snapshot remains authoritative even if its source
            # has since changed or disappeared.
            return cls(directory)
        if directory.exists() and (not directory.is_dir() or any(directory.iterdir())):
            raise ValueError("scientific_process_snapshot_invalid")
        specification, index_bytes = _load(source / "index.json", "scientific_process_source_index_invalid")
        _validate_source_index(specification)
        table, _ = _load(source / "option_sources.json", "scientific_process_source_table_invalid")
        _exact(table, "meaning rows", "scientific_process_source_table_invalid")
        _text(table["meaning"], "scientific_process_source_table_invalid")
        if not isinstance(table["rows"], list):
            raise ValueError("scientific_process_source_table_invalid")
        grouped, evidence_ids = {}, set()
        for row in table["rows"]:
            _exact(row, "evidence_id option_id " + _SOURCE_FIELDS,
                   "scientific_process_source_reference_invalid")
            for field in row.values():
                _text(field, "scientific_process_source_reference_invalid")
            if row["evidence_id"] in evidence_ids:
                raise ValueError("scientific_process_source_reference_duplicate")
            evidence_ids.add(row["evidence_id"])
            grouped.setdefault(row["option_id"], []).append(row)
        if set(grouped) - {entry["id"] for entry in specification["entries"]}:
            raise ValueError("scientific_process_source_reference_invalid")
        directory.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".scientific-process-library-", dir=directory.parent) as temporary:
            staging = Path(temporary)
            (staging / "entries").mkdir()
            (staging / "sources").mkdir()
            (staging / "research_index.json").write_bytes(index_bytes)
            entries = []
            for header in sorted(specification["entries"], key=lambda item: item["id"]):
                if header["slot"] not in SLOTS:
                    continue
                original = _within(source, header["detail_path"], "scientific_process_entry_missing")
                body, body_bytes = _load(original, "scientific_process_entry_invalid")
                _validate_entry(body)
                if any(body[key] != header[key] for key in ("id", "slot", "name", "description")):
                    raise ValueError("scientific_process_source_index_entry_mismatch")
                rows = grouped.get(header["id"], [])
                _validate_rows(rows, body, header["source_evidence_ids"])
                entry_path = "entries/" + header["id"] + ".json"
                sources_path = "sources/" + header["id"] + ".json"
                sources_bytes = (canonical(rows) + "\n").encode("utf-8")
                (staging / entry_path).write_bytes(body_bytes)
                (staging / sources_path).write_bytes(sources_bytes)
                entries.append({"option_id": body["id"], "slot": body["slot"],
                    "name": body["name"], "description": body["description"],
                    "entry_path": entry_path, "entry_sha256": scientific_digest(body),
                    "entry_file_sha256": _bytes_digest(body_bytes),
                    "sources_path": sources_path, "sources_sha256": scientific_digest(rows),
                    "sources_file_sha256": _bytes_digest(sources_bytes),
                    "source_count": len(rows),
                    "source_evidence_ids": header["source_evidence_ids"]})
            content = {"version": SNAPSHOT_VERSION,
                "source_index": {"path": "research_index.json",
                    "sha256": scientific_digest(specification),
                    "file_sha256": _bytes_digest(index_bytes)},
                "source_meaning": table["meaning"], "entries": entries}
            manifest = {**content, "library_id": scientific_digest(content)}
            (staging / "index.json").write_text(canonical(manifest) + "\n", encoding="utf-8")
            # Validate the entire candidate before the single atomic publish.
            cls(staging)
            try:
                staging.rename(directory)
            except OSError as error:
                if error.errno not in (errno.EEXIST, errno.ENOTEMPTY):
                    raise
                # A concurrent publication owns the destination. Its source
                # cannot be replaced by the losing freeze.
                return cls(directory)
        return cls(directory)

    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        manifest_path = _within(self.directory, "index.json", "scientific_process_snapshot_invalid")
        manifest, manifest_bytes = _load(manifest_path, "scientific_process_snapshot_invalid")
        code = "scientific_process_snapshot_invalid"
        _exact(manifest, "version source_index source_meaning entries library_id", code)
        if manifest["version"] != SNAPSHOT_VERSION:
            raise ValueError(code)
        _sha256(manifest["library_id"], code)
        if scientific_digest({key: value for key, value in manifest.items() if key != "library_id"}) != manifest["library_id"]:
            raise ValueError("scientific_process_snapshot_changed")
        if manifest_bytes != (canonical(manifest) + "\n").encode("utf-8"):
            raise ValueError("scientific_process_snapshot_changed")
        _text(manifest["source_meaning"], code)
        source_index = manifest["source_index"]
        _exact(source_index, "path sha256 file_sha256", code)
        _relative(source_index["path"], code)
        for name in ("sha256", "file_sha256"):
            _sha256(source_index[name], code)
        path = _within(self.directory, source_index["path"], "scientific_process_snapshot_changed")
        specification, source_bytes = _load(path, "scientific_process_snapshot_changed")
        if (scientific_digest(specification) != source_index["sha256"] or
                _bytes_digest(source_bytes) != source_index["file_sha256"]):
            raise ValueError("scientific_process_snapshot_changed")
        _validate_source_index(specification)
        original = {entry["id"]: entry for entry in specification["entries"] if entry["slot"] in SLOTS}
        if not isinstance(manifest["entries"], list):
            raise ValueError(code)
        entries, paths = {}, {source_index["path"], "index.json"}
        for entry in manifest["entries"]:
            _exact(entry, _SAVED_FIELDS, code)
            _option_id(entry["option_id"], entry["slot"], code)
            _text(entry["name"], code)
            _text(entry["description"], code)
            for name in ("entry_sha256", "entry_file_sha256", "sources_sha256", "sources_file_sha256"):
                _sha256(entry[name], code)
            for name in ("entry_path", "sources_path"):
                _relative(entry[name], code)
                if entry[name] in paths:
                    raise ValueError(code)
                paths.add(entry[name])
            if type(entry["source_count"]) is not int or entry["source_count"] < 0:
                raise ValueError(code)
            _texts(entry["source_evidence_ids"], code, unique=True)
            if len(entry["source_evidence_ids"]) != entry["source_count"]:
                raise ValueError(code)
            option_id = entry["option_id"]
            if option_id in entries or option_id not in original:
                raise ValueError(code)
            index_entry = original[option_id]
            if (any(entry[key] != index_entry[key] for key in ("slot", "name", "description")) or
                    entry["source_evidence_ids"] != index_entry["source_evidence_ids"]):
                raise ValueError("scientific_process_snapshot_changed")
            entries[option_id] = entry
        if set(entries) != set(original):
            raise ValueError(code)
        self._entries = entries
        self._source_index = source_index
        self._manifest_file_sha256 = _bytes_digest(manifest_bytes)
        self._descriptor = {"version": SNAPSHOT_VERSION,
            "library_id": manifest["library_id"], "manifest_sha256": scientific_digest(manifest)}
        # Reject incomplete or drifted bindings on worker reconstruction. These
        # bodies are temporary validation values, never an in-memory archive.
        for entry in self._entries.values():
            self._read_selected(entry)

    def _check_index(self):
        path = _within(self.directory, "index.json", "scientific_process_snapshot_changed")
        if _bytes_digest(path.read_bytes()) != self._manifest_file_sha256:
            raise ValueError("scientific_process_snapshot_changed")
        path = _within(self.directory, self._source_index["path"], "scientific_process_snapshot_changed")
        if _bytes_digest(path.read_bytes()) != self._source_index["file_sha256"]:
            raise ValueError("scientific_process_snapshot_changed")

    def _metadata(self, option_id):
        if not isinstance(option_id, str) or re.fullmatch(r"[AP][0-9]+", option_id) is None:
            raise ValueError("scientific_process_arguments_invalid")
        if option_id not in self._entries:
            raise ValueError("scientific_process_option_unknown")
        return self._entries[option_id]

    def _reference(self, entry):
        return {"version": OPTION_REF_VERSION, "library_id": self._descriptor["library_id"],
            "slot": entry["slot"], "option_id": entry["option_id"],
            "entry_sha256": entry["entry_sha256"]}

    def _read_selected(self, metadata):
        path = _within(self.directory, metadata["entry_path"], "scientific_process_entry_changed")
        body, body_bytes = _load(path, "scientific_process_entry_changed")
        if (scientific_digest(body) != metadata["entry_sha256"] or
                _bytes_digest(body_bytes) != metadata["entry_file_sha256"]):
            raise ValueError("scientific_process_entry_changed")
        _validate_entry(body)
        if (body["id"] != metadata["option_id"] or
                any(body[key] != metadata[key] for key in ("slot", "name", "description"))):
            raise ValueError("scientific_process_entry_changed")
        path = _within(self.directory, metadata["sources_path"], "scientific_process_sources_changed")
        rows, rows_bytes = _load(path, "scientific_process_sources_changed")
        if (scientific_digest(rows) != metadata["sources_sha256"] or
                _bytes_digest(rows_bytes) != metadata["sources_file_sha256"]):
            raise ValueError("scientific_process_sources_changed")
        _validate_rows(rows, body, metadata["source_evidence_ids"])
        return body, rows

    def as_record(self):
        self._check_index()
        return deepcopy(self._descriptor)

    def headers(self):
        self._check_index()
        return tuple({"option_ref": self._reference(entry), "name": entry["name"],
            "description": entry["description"]} for _, entry in sorted(self._entries.items()))

    def reference(self, option_id):
        self._check_index()
        return self._reference(self._metadata(option_id))

    def resolve(self, option_ref):
        self._check_index()
        ref = validate_option_ref(option_ref)
        metadata = self._metadata(ref["option_id"])
        if ref != self._reference(metadata):
            raise ValueError("scientific_process_option_reference_mismatch")
        return self._read_selected(metadata)[0]

    def search(self, *, slot, query, offset, limit):
        _paging(offset, limit)
        if (slot is not None and (not isinstance(slot, str) or slot not in SLOTS)) or not isinstance(query, str):
            raise ValueError("scientific_process_arguments_invalid")
        terms = query.casefold().split()
        matches = [header for header in self.headers()
            if (slot is None or header["option_ref"]["slot"] == slot) and
            all(term in canonical({"option_id": header["option_ref"]["option_id"],
                "slot": header["option_ref"]["slot"], "name": header["name"],
                "description": header["description"]}).casefold() for term in terms)]
        end = offset + limit
        return {"library": self.as_record(), "entries": matches[offset:end],
            "offset": offset, "limit": limit, "next_offset": end if end < len(matches) else None}

    def entry(self, option_id):
        ref = self.reference(option_id)
        return {"option_ref": ref, "entry": self.resolve(ref),
                "source_count": self._metadata(option_id)["source_count"]}

    def sources(self, *, option_ref, offset, limit):
        _paging(offset, limit)
        self._check_index()
        ref = validate_option_ref(option_ref)
        metadata = self._metadata(ref["option_id"])
        if ref != self._reference(metadata):
            raise ValueError("scientific_process_option_reference_mismatch")
        _, rows = self._read_selected(metadata)
        end = offset + limit
        return {"option_ref": ref, "rows": rows[offset:end], "offset": offset,
            "limit": limit, "next_offset": end if end < len(rows) else None}

    def execute(self, name, arguments):
        try:
            specification = next((entry for entry in catalog() if entry["name"] == name), None)
            if specification is None:
                raise ValueError("scientific_process_tool_unknown")
            arguments = _plain(arguments)
            if not Draft202012Validator(specification["input_schema"]).is_valid(arguments):
                raise ValueError("scientific_process_arguments_invalid")
            operation = {"process.search": self.search, "process.entry": self.entry,
                         "process.sources": self.sources}[name]
            result = operation(**arguments)
            return {"status": "completed", "record_refs": [], "changed_record_refs": [],
                    "result": result, "feedback": None}
        except (ValueError, OSError, UnicodeError) as error:
            return {"status": "failed", "record_refs": [], "changed_record_refs": [], "result": None,
                "feedback": {"code": str(error) if isinstance(error, ValueError) else
                    "scientific_process_storage_unavailable", "operation": name,
                    "exception_type": type(error).__name__}}


__all__ = ["ScientificProcessLibrary", "catalog"]
