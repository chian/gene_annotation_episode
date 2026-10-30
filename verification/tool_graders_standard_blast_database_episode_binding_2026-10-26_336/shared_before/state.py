"""One durable authority for supplied material and revisable scientific interpretation.

Validation here establishes representation and provenance. It never assesses the
truth, suitability or productivity of a scientific interpretation.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from typing import Any

from .domain import (ContractError, MOLECULES, ROLES, RECORD_SCHEMAS, REASONING_SCHEMA,
                     canonical, identity, parse_sequences, validate_schema)
from . import materials
from . import library_targets as libraries
from . import context_masks
from .sequence_mapping import (VERSION as MAPPING_VERSION, extract_path, map_interval,
                               mapping_footprint, validate_mapping)


class RevisionConflict(ContractError):
    def __init__(self, kind: str, key_ref: str, current_revision: int, proposal_ref: str):
        super().__init__("revision_conflict")
        self.detail = {"kind": kind, "key_ref": key_ref,
                       "current_revision": current_revision, "proposal_ref": proposal_ref}


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path).resolve()
        self.path.mkdir(parents=True, exist_ok=True)
        (self.path / "artifacts").mkdir(exist_ok=True)
        self.db = sqlite3.connect(self.path / "state.sqlite3", isolation_level=None, timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS artifacts(id TEXT PRIMARY KEY,sha256 TEXT NOT NULL,
                media_type TEXT NOT NULL,size INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS problem(singleton INTEGER PRIMARY KEY CHECK(singleton=1),data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS inputs(id TEXT PRIMARY KEY,data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS records(id TEXT PRIMARY KEY,record_type TEXT NOT NULL,
                origin TEXT NOT NULL,data TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS record_type_index ON records(record_type,id);
            CREATE INDEX IF NOT EXISTS record_source_reference ON records(record_type,json_extract(data,'$.source_ref'));
            CREATE INDEX IF NOT EXISTS record_parent_source_reference ON records(record_type,json_extract(data,'$.parent_source_ref'));
            CREATE TABLE IF NOT EXISTS record_roots(record_ref TEXT NOT NULL,target_ref TEXT NOT NULL,
                PRIMARY KEY(record_ref,target_ref));
            CREATE INDEX IF NOT EXISTS root_index ON record_roots(target_ref,record_ref);
            CREATE TABLE IF NOT EXISTS current_revisions(record_type TEXT NOT NULL,key_ref TEXT NOT NULL,
                revision INTEGER NOT NULL,record_ref TEXT NOT NULL,PRIMARY KEY(record_type,key_ref));
            CREATE TABLE IF NOT EXISTS proposals(id TEXT PRIMARY KEY,record_type TEXT NOT NULL,
                key_ref TEXT NOT NULL,expected_revision INTEGER NOT NULL,data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS reasoning_commits(operation_key TEXT PRIMARY KEY,
                signature TEXT NOT NULL,result TEXT NOT NULL);
        """)
        self._savepoint = 0
        materials.install_tables(self)
        libraries.install_tables(self)
        self.db.create_function("library_scope_record", 2, self._scope_filter_record)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self.db.close()

    @contextmanager
    def transaction(self):
        own = not self.db.in_transaction
        self._savepoint += 1
        name = f"state_{self._savepoint}"
        self.db.execute("BEGIN IMMEDIATE" if own else f"SAVEPOINT {name}")
        try:
            yield self
        except BaseException:
            if own:
                self.db.rollback()
            else:
                self.db.execute(f"ROLLBACK TO {name}")
                self.db.execute(f"RELEASE {name}")
            raise
        else:
            if own:
                self.db.commit()
            else:
                self.db.execute(f"RELEASE {name}")

    @contextmanager
    def read_snapshot(self):
        own = not self.db.in_transaction
        if own:
            self.db.execute("BEGIN")
        try:
            yield self
        except BaseException:
            if own:
                self.db.rollback()
            raise
        else:
            if own:
                self.db.commit()

    def artifact(self, data: bytes | str, media_type="application/octet-stream") -> str:
        if isinstance(data, str):
            data = data.encode("utf-8")
        if not isinstance(data, bytes):
            raise ContractError("artifact_requires_bytes_or_text")
        digest = hashlib.sha256(data).hexdigest()
        ref = "artifact_" + digest
        directory = self.path / "artifacts" / digest[:2]
        directory.mkdir(exist_ok=True)
        destination = directory / digest
        if not destination.exists():
            fd, temporary = tempfile.mkstemp(dir=directory, prefix=".pending-")
            try:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, destination)
                directory_fd = os.open(directory, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
        self.db.execute("INSERT OR IGNORE INTO artifacts VALUES(?,?,?,?)",
                        (ref, digest, media_type, len(data)))
        return ref

    def get_artifact(self, ref: str) -> bytes:
        row = self.db.execute("SELECT sha256 FROM artifacts WHERE id=?", (ref,)).fetchone()
        if not row:
            raise ContractError("unknown_artifact")
        data = (self.path / "artifacts" / row["sha256"][:2] / row["sha256"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise ContractError("artifact_digest_mismatch")
        return data

    def create_problem(self, input_path=None, *, raw_sequence=None, molecule="unspecified",
                       role="unspecified", manifest_path=None, caller_context=None, format="auto") -> dict:
        return materials.create_problem(self, input_path, raw_sequence=raw_sequence,
            molecule=molecule, role=role, manifest_path=manifest_path,
            caller_context=caller_context, format=format)

    def register_material(self, input_path=None, **kwargs):
        return materials.register_material(self, input_path, **kwargs)

    def parse_material(self, material_ref, *, format=None):
        return materials.parse_material(self, material_ref, format=format)

    def material_members(self, collection_ref, *, offset=0, limit=50):
        return materials.member_page(self, collection_ref, offset=offset, limit=limit)

    def material_errors(self, parse_ref, *, offset=0, limit=50):
        return materials.error_page(self, parse_ref, offset=offset, limit=limit)

    def material_read(self, material_ref, *, offset=0, limit=12000):
        return materials.read_material(self, material_ref, offset=offset, limit=limit)

    def material_member(self, member_ref, *, offset=0, limit=12000):
        return materials.read_member(self, member_ref, offset=offset, limit=limit)

    def material_header(self, member_ref, *, offset=0, limit=12000):
        return materials.read_header(self, member_ref, offset=offset, limit=limit)

    def material_annotations(self, parse_ref, **kwargs):
        return materials.annotation_page(self, parse_ref, **kwargs)

    def material_reference(self, member_ref):
        return materials.member_reference(self, member_ref)

    def _caller_source(self, value, provider):
        artifact_ref = self.artifact(canonical(value), "application/json")
        return self.put("source", {"provider": provider, "accession": None, "uri": None,
            "artifact_ref": artifact_ref, "text_ref": artifact_ref, "request_ref": None,
            "version": None, "retrieved_at": None}, origin="caller")

    @staticmethod
    def _unit(molecule):
        return "aa" if molecule == "protein" else "nt" if molecule in {"dna", "rna"} else "symbol"

    def problem(self) -> dict:
        row = self.db.execute("SELECT data FROM problem WHERE singleton=1").fetchone()
        if row is None:
            raise ContractError("problem_not_initialized")
        return json.loads(row["data"])

    def targets(self) -> list[dict]:
        return [self.get_input(ref) for ref in self.problem()["subject_refs"]]

    def get_input(self, ref: str) -> dict:
        row = self.db.execute("SELECT data FROM inputs WHERE id=?", (ref,)).fetchone()
        if row is None:
            raise ContractError("unknown_input")
        return json.loads(row["data"])

    get_inputmetadata = get_input

    def get(self, ref: str) -> dict:
        row = self.db.execute("SELECT data FROM inputs WHERE id=?", (ref,)).fetchone()
        if row:
            return json.loads(row["data"])
        row = self.db.execute("SELECT data FROM records WHERE id=?", (ref,)).fetchone()
        if row:
            return json.loads(row["data"])
        read_subject = libraries.resolve(self, ref)
        if read_subject is not None:
            return read_subject
        row = self.db.execute("SELECT data FROM material_members WHERE id=?", (ref,)).fetchone()
        if row:
            return json.loads(row[0])
        row = self.db.execute("SELECT * FROM artifacts WHERE id=?", (ref,)).fetchone()
        if row:
            return {**dict(row), "record_type": "artifact"}
        raise ContractError("unknown_reference")

    def _require(self, ref, kinds=None, *, field_path=None):
        try:
            value = self.get(ref)
        except ContractError as exc:
            if field_path is not None:
                raise ContractError(str(exc), detail={"field_path": list(field_path), "reference": ref}) from exc
            raise
        if kinds is not None and value["record_type"] not in kinds:
            detail = {"reference": ref, "actual_record_type": value["record_type"],
                      "allowed_record_types": sorted(kinds)}
            if field_path is not None:
                detail["field_path"] = list(field_path)
            raise ContractError("wrong_reference_type", detail=detail)
        return value

    def roots(self, ref: str) -> list[str]:
        if self.db.execute("SELECT 1 FROM inputs WHERE id=?", (ref,)).fetchone():
            return [ref]
        record = self.get(ref)
        if record["record_type"] == "read_subject":
            return [record["library_ref"]]
        return [row[0] for row in self.db.execute("SELECT target_ref FROM record_roots WHERE record_ref=? ORDER BY target_ref", (ref,))]

    @staticmethod
    def _merge_segments(segments):
        merged = []
        for segment in sorted(segments, key=lambda row: (*libraries.key(row)[:1], row.get("member_ref", ""), row["unit"], row["start"], row["end"])):
            if merged and libraries.key(merged[-1]) == libraries.key(segment) and segment["start"] <= merged[-1]["end"]:
                merged[-1]["end"] = max(merged[-1]["end"], segment["end"])
            else:
                merged.append(dict(segment))
        return merged

    def scope_coverage(self, scope=None):
        scope = self.validate_scope(scope)
        if "segments" in scope:
            return scope["segments"]
        if any(libraries.is_library(self.get_input(ref)) for ref in scope["subject_refs"]):
            raise ContractError("library_scope_requires_streamed_geometry")
        return [span for ref in scope["subject_refs"] for span in self.coverage(ref)]

    def iter_scope_coverage(self, scope=None, target_ref=None):
        yield from libraries.iter_eligible(self, scope, target_ref)

    def scope_measure(self, scope, target_ref):
        return libraries.measure(self, scope, target_ref)

    def normalize_context_mask(self, mask):
        return context_masks.normalize(self, mask)

    def context_mask_identity(self, mask):
        return context_masks.identity_digest(self, mask)

    def context_mask_measure(self, mask, target_ref):
        return context_masks.measure(self, mask, target_ref)

    def context_mask_subset(self, left, right):
        return context_masks.subset(self, left, right)

    def context_mask_overlap(self, left, right):
        return context_masks.overlap(self, left, right)

    def context_mask_dimension_segments(self, mask, dimension_ref):
        return context_masks.dimension_segments(self, mask, dimension_ref)

    def context_mask_target_full(self, mask, target_ref):
        return context_masks.target_full(self, mask, target_ref)

    def context_mask_target_query(self, mask, target_ref):
        return context_masks.target_query(self, mask, target_ref)

    def footprint_dimension(self, span):
        return libraries.footprint_dimension(self, span)

    def scope_dimension_segments(self, scope, dimension_ref):
        return libraries.dimension_segments(self, scope, dimension_ref)

    def read_subject_ref(self, library_ref, member_ref):
        reference = libraries.read_ref(library_ref, member_ref)
        if libraries.resolve(self, reference) is None:
            raise ContractError("member_not_in_fixed_library")
        return reference

    def footprint_from_mapping(self, mapping):
        validate_mapping(mapping)
        result = []
        eligible = set(self.problem()["subject_refs"])
        for row in mapping["path"]:
            subject = self.get(row["subject_ref"])
            if subject["record_type"] == "read_subject":
                result.append({"target_ref": subject["library_ref"], "member_ref": subject["member_ref"],
                    "start": row["start"], "end": row["end"], "unit": row["unit"]})
            elif subject["record_type"] == "input" and subject["id"] in eligible and not libraries.is_library(subject):
                result.append({"target_ref": subject["id"], "start": row["start"], "end": row["end"], "unit": row["unit"]})
        return self._merge_segments(result)

    @staticmethod
    def _covered_by(segments, allowed):
        return all(any(libraries.key(a) == libraries.key(s) and a["start"] <= s["start"] < s["end"] <= a["end"] for a in allowed) for s in segments)

    def scope_covers(self, segments, scope=None):
        normalized = self.validate_scope(scope)
        return all(libraries.contains(self, normalized, span) for span in segments)

    def validate_scope(self, scope=None, parent_scope=None) -> dict:
        return libraries.validate_scope(self, scope, parent_scope)

    def scope_contains(self, parent_scope, child_scope) -> bool:
        try:
            self.validate_scope(child_scope, parent_scope)
            return True
        except ContractError:
            return False

    def record_coverage(self, row):
        kind = row["record_type"]
        if kind in {"input", "read_subject", "feature", "product"}:
            return self.coverage(row["id"])
        if kind in {"annotation", "interpretation_account"}:
            return row["footprint"]
        if kind == "assessment":
            return self.record_coverage(self.get(row["hypothesis_ref"]))
        if kind in {"hypothesis", "observation"}:
            return self._merge_segments([part for ref in row["subject_refs"]
                if self.get(ref)["record_type"] in {"input", "read_subject", "feature", "product"}
                for part in self.coverage(ref)])
        return []

    @staticmethod
    def _is_context_account(row):
        return row.get("record_type") in {"assessment", "annotation", "interpretation_account"} and "context_account_scope" in row

    def _context_read_mask(self, row):
        allocation = row.get("context_scope")
        # Empty and unbound allocations remain visible through immutable lineage
        # domain so a withdrawal is reportable, rather than globally visible.
        return allocation if allocation and allocation["subject_refs"] else row["context_account_scope"]

    def _scope_filter_record(self, data, serialized_scope):
        scope = json.loads(serialized_scope)
        row = json.loads(data)
        if self._is_context_account(row):
            return int(self.context_mask_overlap(self._context_read_mask(row), scope))
        # Retain the established scalar-region read visibility. New library
        # selections must not publish other original members across a form.
        if not scope.get("read_selection_refs") and not any("member_ref" in row for row in scope.get("segments", ())):
            return 1
        row = json.loads(data)
        footprint = self.record_coverage(row)
        if not footprint:
            return 1
        # Existing broader interpretations remain usable on their actual
        # overlap. Write/execution/commission containment is checked separately.
        return int(any(any(max(span["start"], allowed["start"]) < min(span["end"], allowed["end"])
            for allowed in self.scope_dimension_segments(scope, self.footprint_dimension(span)["id"]))
            for span in footprint))

    def _in_scope(self, ref: str, scope) -> bool:
        row = self.get(ref)
        if self._is_context_account(row):
            return self.context_mask_overlap(self._context_read_mask(row), scope)
        roots = set(self.roots(ref))
        if roots and not roots <= set(scope["subject_refs"]):
            return False
        return bool(self._scope_filter_record(canonical(self.get(ref)), canonical(scope)))

    def list(self, kind, scope=None, limit=100, offset=0) -> list[dict]:
        if kind not in RECORD_SCHEMAS:
            raise ContractError("unknown_record_type")
        if type(limit) is not int or limit < 0 or type(offset) is not int or offset < 0:
            raise ContractError("invalid_page")
        scope = self.validate_scope(scope) if scope is not None else None
        if scope is None:
            rows = self.db.execute("SELECT data FROM records WHERE record_type=? ORDER BY id LIMIT ? OFFSET ?", (kind, limit, offset))
        else:
            placeholders = ",".join("?" for _ in scope["subject_refs"])
            rows = self.db.execute(f"""SELECT data FROM records r WHERE record_type=? AND (json_type(r.data,'$.context_account_scope') IS NOT NULL OR NOT EXISTS
                (SELECT 1 FROM record_roots rr WHERE rr.record_ref=r.id AND rr.target_ref NOT IN ({placeholders})))
                AND library_scope_record(r.data,?)
                ORDER BY id LIMIT ? OFFSET ?""", (kind, *scope["subject_refs"], canonical(scope), limit, offset))
        return [json.loads(row[0]) for row in rows]

    def subjects(self, scope=None) -> list[dict]:
        normalized = self.validate_scope(scope)
        return [self.get_input(ref) for ref in normalized["subject_refs"]] + self.list("feature", normalized, limit=2**31-1) + self.list("product", normalized, limit=2**31-1)

    def query_records(self, kind, scope=None, limit=100, offset=0, *,
                      current_only=False, references=None, record_selection=None) -> dict:
        """Read one exact scientific page without changing dependency meaning.

        Current assessment/annotation pages use the same revision membership and
        key ordering as the working view. Other kinds are immutable, so their
        historical and current-only inventories coincide. ``references`` OR-
        matches actual reference positions, including provenance anchors, rather
        than string mentions or a row's own ID. The filter is computed from the
        authoritative JSON rows; it is not another state graph or invalidator.
        ``subject`` is the existing input/feature/product inventory, paged in
        that order without materializing the whole inventory.
        """
        if kind not in RECORD_SCHEMAS and kind != "subject":
            raise ContractError("unknown_record_type")
        if type(limit) is not int or limit < 1 or type(offset) is not int or offset < 0:
            raise ContractError("invalid_page")
        if type(current_only) is not bool:
            raise ContractError("invalid_current_only")
        if references is not None and (not isinstance(references, list) or not references
                or not all(isinstance(ref, str) for ref in references)):
            raise ContractError("invalid_reference_filter")
        if references is not None:
            references = list(dict.fromkeys(references))
        with self.read_snapshot():
            normalized = self.validate_scope(scope)
            for ref in references or ():
                self._require(ref)
            placeholders = ",".join("?" for _ in normalized["subject_refs"])
            scope_filter = f"""(json_type(r.data,'$.context_account_scope') IS NOT NULL OR NOT EXISTS (SELECT 1 FROM record_roots rr
                WHERE rr.record_ref=r.id AND rr.target_ref NOT IN ({placeholders})))
                AND library_scope_record(r.data,?)"""
            if kind == "subject":
                selection = f"""SELECT i.id,i.data,'input' AS record_type,
                        0 AS sort_group,i.id AS sort_key FROM inputs i
                        WHERE i.id IN ({placeholders})
                    UNION ALL SELECT r.id,r.data,r.record_type,
                        CASE r.record_type WHEN 'feature' THEN 1 ELSE 2 END,r.id
                        FROM records r WHERE r.record_type IN ('feature','product')
                        AND {scope_filter}"""
                parameters = [*normalized["subject_refs"], *normalized["subject_refs"], canonical(normalized)]
            elif current_only and kind in {"assessment", "annotation", "interpretation_account"}:
                selection = f"""SELECT r.id,r.data,r.record_type,0 AS sort_group,
                    c.key_ref AS sort_key FROM current_revisions c
                    JOIN records r ON r.id=c.record_ref
                    WHERE c.record_type=? AND {scope_filter}"""
                parameters = [kind, *normalized["subject_refs"], canonical(normalized)]
            else:
                selection = f"""SELECT r.id,r.data,r.record_type,0 AS sort_group,
                    r.id AS sort_key FROM records r
                    WHERE r.record_type=? AND {scope_filter}"""
                parameters = [kind, *normalized["subject_refs"], canonical(normalized)]
            where = ""
            if references is not None:
                # This mirrors _refs: scalar *_ref/ref values, or members of
                # *_refs/dependencies arrays. json_tree never parses quote text
                # as nested JSON, while real anchor reference keys remain edges.
                matches = ",".join("?" for _ in references)
                where = f"""WHERE EXISTS (
                    SELECT 1 FROM json_tree(v.data) edge
                    LEFT JOIN json_tree(v.data) parent ON parent.id=edge.parent
                    WHERE edge.type='text' AND edge.value IN ({matches}) AND (
                        edge.key='ref' OR substr(CAST(edge.key AS TEXT),-4)='_ref'
                        OR (parent.type='array' AND (parent.key='dependencies'
                            OR substr(CAST(parent.key AS TEXT),-5)='_refs'))))"""
                parameters.extend(references)
            if record_selection is not None:
                # Internal visibility projection, supplied by the runtime.
                # Explicit state.query reads retain their ordinary discovery
                # semantics; this filters automatic context before pagination.
                query, selected_parameters = record_selection
                where += (' AND ' if where else 'WHERE ') + f'v.id IN ({query})'
                parameters.extend(selected_parameters)
            cte = f"WITH visible AS ({selection})"
            total = self.db.execute(f"{cte} SELECT count(*) FROM visible v {where}", parameters).fetchone()[0]
            rows = self.db.execute(f"{cte} SELECT v.data FROM visible v {where} "
                "ORDER BY v.sort_group,v.sort_key,v.id LIMIT ? OFFSET ?", [*parameters, limit, offset])
            records = [json.loads(row[0]) for row in rows]
            next_offset = offset + len(records) if offset + len(records) < total else None
            next_query = None
            if next_offset is not None:
                next_query = {"kind": kind, "offset": next_offset, "limit": limit,
                              "current_only": current_only}
                if references is not None:
                    next_query["references"] = list(references)
            wanted = set(references or ())
            reference_matches = [{"record_ref": row["id"], "reference_ref": ref,
                                  "field_path": list(path)}
                for row in records for ref, path in self._refs(row, with_paths=True)
                if ref in wanted]
            return {"records": records, "offset": offset, "limit": limit,
                    "total": total, "next_offset": next_offset,
                    "current_only": current_only,
                    "references": list(references) if references is not None else None,
                    "next_query": next_query, "reference_matches": reference_matches}

    def coverage(self, subject_ref) -> list[dict]:
        subject = self.get(subject_ref)
        kind = subject["record_type"]
        if kind == "input":
            if libraries.is_library(subject):
                return []  # A library has no physical local sequence interval.
            return [{"target_ref": subject_ref, "start": 0, "end": subject["length"], "unit": subject["unit"]}]
        if kind == "read_subject":
            return [{"target_ref": subject["library_ref"], "member_ref": subject["member_ref"],
                "start": 0, "end": subject["length"], "unit": subject["unit"]}]
        if kind == "reference":
            return []
        if kind == "product":
            return deepcopy(subject["footprint"])
        if kind == "feature":
            return self.map_segments(subject["subject_ref"], subject["segments"])
        raise ContractError("subject_has_no_input_mapping")

    def sequence_mapping(self, subject_ref) -> dict:
        """Return exact physical sequence traversal, independently of credit.

        Input and feature traversals are derived from their declared coordinates.
        A product needs an explicit native-tool mapping; old aggregate footprints
        still describe whole-parent attribution but cannot map a residue interval.
        No sequence artifacts are loaded by this metadata operation.
        """
        subject = self.get(subject_ref)
        kind = subject["record_type"]
        if kind in {"input", "reference", "read_subject"}:
            length = self.subject_length(subject_ref)
            return {"version": MAPPING_VERSION, "units_per_symbol": 1,
                "symbol_length": length, "path": [{"subject_ref": subject_ref,
                    "start": 0, "end": length, "unit": self.subject_unit(subject_ref), "strand": "+"}]}
        if kind == "product":
            if subject.get("mapping") is None:
                raise ContractError("subregion_mapping_unavailable")
            return deepcopy(subject["mapping"])
        if kind == "feature":
            parent = self.sequence_mapping(subject["subject_ref"])
            scale = parent["units_per_symbol"]
            path = extract_path(parent["path"],
                [{"start": segment["start"] * scale, "end": segment["end"] * scale}
                 for segment in subject["segments"]], strand=subject["strand"])
            return {"version": MAPPING_VERSION, "units_per_symbol": scale,
                "symbol_length": self._subject_length(subject), "path": path}
        raise ContractError("subject_has_no_input_mapping")

    def has_exact_mapping(self, subject_ref) -> bool:
        subject = self.get(subject_ref)
        if subject["record_type"] == "reference" and subject.get("sequence_ref") is None:
            # Native source coordinates/length do not supply an executable
            # complete sequence traversal. Absence is not a fabricated map.
            return False
        try:
            self.sequence_mapping(subject_ref)
            return True
        except ContractError as error:
            if str(error) != "subregion_mapping_unavailable":
                raise
            return False

    def map_segments(self, subject_ref, segments) -> list[dict]:
        """Map local symbol intervals to a union in immutable original units.

        Traversal order/orientation remains in sequence_mapping; footprints used
        for ownership/credit are normalized unions. Legacy unmapped products can
        only reuse their entire existing attribution, never a fabricated submap.
        """
        subject = self.get(subject_ref)
        length = self._subject_length(subject)
        if (not isinstance(segments, list) or not segments or any(
            not isinstance(row, dict) or set(row) != {"start", "end"}
            or type(row["start"]) is not int or type(row["end"]) is not int
            or not 0 <= row["start"] < row["end"] <= length for row in segments)):
            raise ContractError("interval_outside_mapped_sequence")
        try:
            mapping = self.sequence_mapping(subject_ref)
        except ContractError as error:
            if str(error) != "subregion_mapping_unavailable" or segments != [{"start": 0, "end": length}]:
                raise
            return self.coverage(subject_ref)
        result = []
        for segment in segments:
            physical = map_interval(mapping, segment["start"], segment["end"])
            projected = {**mapping, "symbol_length": segment["end"]-segment["start"], "path": physical}
            result.extend(self.footprint_from_mapping(projected))
        return self._merge_segments(result)

    def subject_length(self, subject_ref) -> int:
        """Actual local symbol length, without hydrating the sequence artifact."""
        return self._subject_length(self.get(subject_ref))

    def subject_unit(self, subject_ref) -> str:
        subject = self.get(subject_ref)
        if subject["record_type"] in {"input", "read_subject"}:
            if libraries.is_library(subject):
                raise ContractError("library_is_not_a_sequence_operand")
            return subject["unit"]
        if subject["record_type"] == "feature":
            return self.subject_unit(subject["subject_ref"])
        if subject["record_type"] in {"product", "reference"}:
            return "aa" if subject.get("molecule") == "protein" else "nt" if subject.get("molecule") in {"dna", "rna"} else "symbol"
        raise ContractError("not_sequence_subject")

    def subject_molecule(self, subject_ref) -> str:
        subject = self.get(subject_ref)
        if subject["record_type"] == "feature":
            return self.subject_molecule(subject["subject_ref"])
        if subject["record_type"] in {"input", "reference", "product", "read_subject"}:
            return subject.get("molecule") or "unspecified"
        raise ContractError("not_sequence_subject")

    def _subject_length(self, subject):
        if subject["record_type"] in {"input", "read_subject"}:
            if libraries.is_library(subject):
                raise ContractError("library_is_not_a_sequence_operand")
            return subject["length"]
        if subject["record_type"] == "feature":
            return sum(segment["end"]-segment["start"] for segment in subject["segments"])
        if subject["record_type"] in {"product", "reference"}:
            if not subject.get("sequence_ref"):
                raise ContractError("referenced_record_has_no_sequence")
            return self._require(subject["sequence_ref"], {"artifact"})["size"]
        raise ContractError("not_sequence_subject")

    def _refs(self, value, *, with_paths=False, path=()):
        if isinstance(value, dict):
            for key, child in value.items():
                if (key.endswith("_ref") or key == "ref") and child is not None:
                    yield (child, (*path, key)) if with_paths else child
                elif key.endswith("_refs") or key == "dependencies":
                    for index, ref in enumerate(child):
                        yield (ref, (*path, key, index)) if with_paths else ref
                else:
                    yield from self._refs(child, with_paths=with_paths, path=(*path, key))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                yield from self._refs(child, with_paths=with_paths, path=(*path, index))

    def _anchor(self, anchor, source_ref):
        if anchor is None:
            raise ContractError("extraction_anchor_required")
        source = self._require(source_ref, {"source"})
        source_artifacts = {source.get(key) for key in ("artifact_ref", "text_ref", "stdout_ref", "stderr_ref")}
        if anchor["source_ref"] != source_ref or anchor["artifact_ref"] not in source_artifacts:
            raise ContractError("anchor_source_mismatch")
        # Preserve full-artifact integrity checking without materializing a
        # potentially large source merely to validate one bounded quotation.
        path = materials.artifact_path(self, anchor["artifact_ref"])
        start, end = anchor["start"], anchor["end"]
        quote = anchor["quote"].encode("utf-8")
        if not 0 <= start < end <= path.stat().st_size or end-start != len(quote):
            raise ContractError("anchor_transcription_mismatch")
        with path.open("rb") as handle:
            handle.seek(start)
            selected = handle.read(len(quote))
        if selected != quote:
            raise ContractError("anchor_transcription_mismatch")

    def _validate_atoms(self, value):
        if isinstance(value, dict):
            atom_type = value.get("type")
            if atom_type == "term_ref":
                self._require(value["ref"], {"term"})
            elif atom_type in {"reference", "relation"}:
                refs = [value["ref"]] if atom_type == "reference" else [role["ref"] for role in value["roles"]]
                for ref in refs:
                    if self.get(ref)["record_type"] in {
                        "artifact", "source", "native_execution", "image_view", "material", "material_link",
                        "collection", "parse_attempt", "pmc_version", "pmc_catalog",
                        "pmc_object", "pmc_asset", "archive_member", "source_derivative", "read_selection",
                    }:
                        raise ContractError("semantic_value_requires_entity_reference")
            elif atom_type == "number" and value.get("unit_ref") is not None:
                unit = self._require(value["unit_ref"], {"term"})
                if unit["term_type"] != "unit":
                    raise ContractError("measurement_unit_reference_required")
            for child in value.values():
                self._validate_atoms(child)
        elif isinstance(value, list):
            for child in value:
                self._validate_atoms(child)

    def _validate_record(self, kind, data, origin):
        if kind == 'interpretation_account':
            # Share representation/reference/coherence validation. The stored
            # kind and ownership remain distinct from an annotation.
            return self._validate_record('annotation', data, origin)
        validate_schema(data, RECORD_SCHEMAS[kind])
        if origin not in {"caller", "external", "tool", "reasoning", "extracted"}:
            raise ContractError("unknown_origin")
        visual_observation = kind == "observation" and data.get("visual_anchor") is not None
        if origin == "reasoning" and kind not in {"feature", "hypothesis", "assessment", "annotation"} and not visual_observation:
            raise ContractError("origin_not_allowed")
        if kind == "image_view" and origin != "tool":
            raise ContractError("image_view_requires_native_tool_origin")
        if kind == "native_execution" and origin != "tool":
            raise ContractError("native_execution_requires_native_tool_origin")
        if origin == "extracted" and kind not in {"term", "observation", "reference", "context"}:
            raise ContractError("origin_not_allowed")
        custody = {"pmc_version", "pmc_catalog", "pmc_object", "pmc_asset", "archive_member", "source_derivative"}
        if kind in custody and origin not in {"tool", "external"}:
            raise ContractError("catalog_or_derivative_requires_source_publisher")
        for ref, path in self._refs(data, with_paths=True):
            self._require(ref, field_path=path)
        self._validate_atoms(data)
        def constrained_refs(value, path=()):
            if isinstance(value, dict):
                for key, child in value.items():
                    admitted = {"context_refs": {"context", "hypothesis"}, "term_refs": {"term"},
                        "condition_refs": {"context", "hypothesis", "observation", "term"},
                        "assumption_refs": {"hypothesis"}}
                    if key in admitted:
                        for index, ref in enumerate(child):
                            self._require(ref, admitted[key], field_path=(*path, key, index))
                    if key in {"dependencies", "related_refs"}:
                        for ref in child:
                            if self.get(ref)["record_type"] == "artifact":
                                raise ContractError("semantic_dependency_requires_record")
                    constrained_refs(child, (*path, key))
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    constrained_refs(child, (*path, index))
        constrained_refs(data)
        if kind == "native_execution":
            from .execution_recording import NativeMeasurement
            from .domain import NATIVE_EXECUTION_OPERATIONS
            self._require(data['measurement_artifact_ref'], {'artifact'})
            measured = NativeMeasurement.from_record(json.loads(self.get_artifact(data['measurement_artifact_ref'])))
            if measured.execution_class.phase != NATIVE_EXECUTION_OPERATIONS[data['operation']]:
                raise ContractError('native_execution_operation_phase_mismatch')
            roles = [operand['role'] for operand in data['operands']]
            if len(set(roles)) != len(roles):
                raise ContractError('native_execution_operand_role_repeated')
            for operand in data['operands']:
                if operand['role'] == 'input_source':
                    self._require(operand['subject_ref'], {'source'})
                else:
                    self._require(operand['subject_ref'], {'input', 'reference', 'read_subject', 'feature', 'product'})
                    length = getattr(measured.execution_class, operand['role']+'_residues')
                    if length is not None and self.subject_length(operand['subject_ref']) != length:
                        raise ContractError('native_execution_operand_length_mismatch')
            if measured.execution_class.phase == 'pairwise_sequence_alignment':
                if set(roles) != {'query', 'reference'} or data['operation'] != 'align_pair':
                    raise ContractError('native_alignment_requires_query_and_reference_operands')
            if measured.execution_class.phase == 'spreadsheet_selection':
                if set(roles) != {'input_source'} or data['operation'] not in {'xlsx_sheets', 'xlsx_rows'}:
                    raise ContractError('native_spreadsheet_requires_source_operand')
                if measured.execution_class.query_residues is not None or measured.execution_class.reference_residues is not None:
                    raise ContractError('spreadsheet_workload_has_no_sequence_residues')
            if measured.execution_class.phase == 'protein_homology_search':
                if set(roles) != {'query'} or data['operation'] != 'phmmer_search':
                    raise ContractError('native_homology_requires_query_operand')
                if self.subject_unit(data['operands'][0]['subject_ref']) != 'aa':
                    raise ContractError('native_homology_requires_protein_query')
        if kind == "source":
            for ref in data.get("operand_refs", []):
                self._require(ref, {"input", "reference", "read_subject", "feature", "product"})
                self.subject_length(ref)
            if "query_selection_ref" in data:
                self._require(data["query_selection_ref"], {"read_selection"})
            for ref in data.get("parent_source_refs", []):
                self._require(ref, {"source"})
            for key in ("artifact_ref", "text_ref", "request_ref"):
                if data[key] is not None:
                    self._require(data[key], {"artifact"})
            for ref in data.get("auxiliary_artifact_refs", []):
                self._require(ref, {"artifact"})
            for key in ("stdout_ref", "stderr_ref"):
                if key in data:
                    self._require(data[key], {"artifact"})
        if kind == "image_view":
            from PIL import Image
            source = self._require(data["source_ref"], {"source"})
            original = self._require(data["input_source_ref"], {"source"})
            if source["origin"] != "tool" or source["provider"] != "image.view":
                raise ContractError("native_image_view_source_required")
            if source["artifact_ref"] != data["image_artifact_ref"]:
                raise ContractError("image_view_display_source_mismatch")
            if source.get("parent_source_refs") != [data["input_source_ref"]]:
                raise ContractError("image_view_parent_source_mismatch")
            if original["artifact_ref"] != data["original_artifact_ref"]:
                raise ContractError("image_view_original_source_mismatch")
            if data["frame"] >= data["frame_count"]:
                raise ContractError("image_frame_outside_source")
            if source["request_ref"] is None:
                raise ContractError("image_view_native_metadata_required")
            native = json.loads(self.get_artifact(source["request_ref"]))
            if canonical(native) != canonical({key: value for key, value in data.items() if key != "source_ref"}):
                raise ContractError("image_view_native_metadata_mismatch")
            if source["version"] != data["software_version"]:
                raise ContractError("image_view_software_version_mismatch")
            # MIME registration is first-writer metadata; identical original
            # and rendered PNG bytes can legitimately retain an opaque MIME.
            with Image.open(materials.artifact_path(self, data["image_artifact_ref"])) as image:
                if image.format != "PNG" or image.size != (data["width"], data["height"]):
                    raise ContractError("image_view_display_dimensions_mismatch")
        if kind in {"term", "reference", "context", "observation", "material", "material_link", "parse_attempt", "collection", "reaction_record", "chemical_record"}:
            self._require(data["source_ref"], {"source"})
        if kind in {"reaction_record", "chemical_record"}:
            source = self._require(data["source_ref"], {"source"})
            provider = "rhea" if kind == "reaction_record" else "chebi"
            if origin != "external" or source["provider"] != provider:
                raise ContractError("native_chemistry_requires_matching_public_source")
            if kind == "reaction_record":
                for item in data["participants"]:
                    chemical = self._require(item["chemical_ref"], {"reference"})
                    if chemical["reference_type"] != "chemical" or chemical["source_ref"] != data["source_ref"]:
                        raise ContractError("reaction_participant_source_mismatch")
        if kind == "reference" and data.get("native_record_ref") is not None:
            details = self._require(data["native_record_ref"], {"reaction_record", "chemical_record"})
            expected = "reaction" if details["record_type"] == "reaction_record" else "chemical"
            if (data["reference_type"] != expected or origin != "external"
                    or details["source_ref"] != data["source_ref"] or details["accession"] != data["accession"]):
                raise ContractError("native_chemistry_reference_mismatch")
        if kind in custody:
            self._require(data["source_ref"], {"source"})
        if kind == "pmc_catalog":
            self._require(data["version_ref"], {"pmc_version"})
            if data["metadata_source_ref"] is not None:
                self._require(data["metadata_source_ref"], {"source"})
        if kind == "pmc_object":
            selected = self._require(data["version_ref"], {"pmc_version"})
            if not data["object_key"].startswith(selected["prefix"]):
                raise ContractError("listed_object_version_identity_mismatch")
        if kind == "pmc_asset":
            catalog = self._require(data["catalog_ref"], {"pmc_catalog"})
            selected = self._require(data["version_ref"], {"pmc_version"})
            if catalog["version_ref"] != selected["id"] or catalog["metadata_source_ref"] != data["source_ref"]:
                raise ContractError("asset_catalog_identity_mismatch")
            from .literature_assets import advertised_asset
            actual = advertised_asset(data["original_uri"], prefix=selected["prefix"])
            if any(data[key] != value for key, value in actual.items()):
                raise ContractError("asset_advertisement_identity_mismatch")
        if kind == "source_derivative":
            self._require(data["parent_source_ref"], {"source"})
            if data["selection_ref"] is not None:
                member = self._require(data["selection_ref"], {"archive_member"})
                if member["source_ref"] != data["parent_source_ref"]:
                    raise ContractError("archive_derivative_parent_mismatch")
        if kind == "material":
            for field in ("sample_ref", "library_ref"):
                if data[field] is not None:
                    self._require(data[field], {"context"})
        if kind in {"collection", "parse_attempt"}:
            self._require(data["material_ref"], {"material"})
        if kind == "parse_attempt" and data["collection_ref"] is not None:
            self._require(data["collection_ref"], {"collection"})
        if kind == "parse_attempt" and data.get("native_source_ref") is not None:
            native = self._require(data["native_source_ref"], {"source"})
            if (native["origin"] != "tool" or native["provider"] != "material.genbank"
                    or native["version"] != data["parser_version"]
                    or native.get("parent_source_refs") != [data["source_ref"]]
                    or native["request_ref"] is None):
                raise ContractError("native_genbank_source_identity_mismatch")
            request = json.loads(self.get_artifact(native["request_ref"]))
            if any(request.get(key) != data[key] for key in ("material_ref", "parse_key", "parser_version")) or request.get("input_source_ref") != data["source_ref"]:
                raise ContractError("native_genbank_source_identity_mismatch")
        if kind == "read_selection":
            if origin != "tool" or not libraries.is_library(self.get_input(data["library_ref"])):
                raise ContractError("read_selection_requires_fixed_library_tool_origin")
        if kind == "material_link":
            self._require(data["left_ref"], {"material"})
            self._require(data["right_ref"], {"material"})
        if kind == "reference" and data.get("member_ref") is not None:
            member = self._require(data["member_ref"], {"collection_member"})
            if (any(data[field] != member[field] for field in ("source_ref", "molecule", "length"))
                    or data["sequence_ref"] != materials.packing.content_ref(self, member, "sequence")):
                raise ContractError("member_reference_identity_mismatch")
            expected_label = {"label": member["name"][:512], "label_is_preview": len(member["name"]) > 512,
                "label_full_characters": len(member["name"]), "label_full_utf8_bytes": len(member["name"].encode("utf-8"))}
            if any(data.get(key) != value for key, value in expected_label.items()):
                raise ContractError("member_reference_label_metadata_mismatch")
        if kind == "context":
            if origin == "extracted":
                self._anchor(data.get("anchor"), data["source_ref"])
                if data["name"] not in data["anchor"]["quote"]:
                    raise ContractError("context_name_not_in_source_span", detail={"field_path": ["name"]})
            elif data.get("anchor") is not None:
                self._anchor(data["anchor"], data["source_ref"])
        if kind == "term":
            if origin == "extracted":
                self._anchor(data["anchor"], data["source_ref"])
                expected_accession = identity("source_term", {"source_ref": data["source_ref"], "label": data["label"], "anchor": data["anchor"]})
                if data["namespace"] != "source_local" or data["accession"] != expected_accession:
                    raise ContractError("extracted_term_identity_mismatch")
                if data["label"] not in data["anchor"]["quote"]:
                    raise ContractError("term_label_not_in_source_span")
            elif data["anchor"] is not None:
                self._anchor(data["anchor"], data["source_ref"])
        if kind == "reference" and origin == "extracted":
            self._anchor(data.get("anchor"), data["source_ref"])
            expected_accession = identity("source_entity", {"source_ref": data["source_ref"], "label": data["label"], "anchor": data["anchor"]})
            if data["accession"] != expected_accession or data["sequence_ref"] is not None or data["length"] is not None:
                raise ContractError("extracted_subject_identity_mismatch")
            if data["label"] not in data["anchor"]["quote"]:
                raise ContractError("subject_label_not_in_source_span")
        if kind == "reference" and data["sequence_ref"] is not None:
            if data.get("member_ref") is not None:
                # The native index already established ASCII sequence symbols.
                # A selected member window must not hydrate a whole chromosome.
                length = self._require(data["sequence_ref"], {"artifact"})["size"]
            else:
                # A native result can identify a large reference. Verification
                # must not hydrate that entire artifact in the workflow host.
                path = materials.artifact_path(self, data["sequence_ref"])
                length = 0
                with path.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024*1024), b""):
                        length += len(chunk.decode("ascii"))
            if data["length"] != length:
                raise ContractError("reference_sequence_length_mismatch")
        if kind == "feature":
            parent = self._require(data["subject_ref"], {"input", "feature", "product", "reference", "read_subject"})
            length = self._subject_length(parent)
            if any(not 0 <= s["start"] < s["end"] <= length for s in data["segments"]):
                raise ContractError("feature_coordinate_outside_subject")
            # Exact nested mappings are derived, never guessed from product length.
            self.map_segments(parent["id"], data["segments"])
        if kind == "product":
            for parent in data["parent_refs"]:
                self._require(parent, {"input", "feature", "product", "reference", "read_subject"})
            self._require(data["sequence_ref"], {"artifact"})
            try:
                sequence = self.get_artifact(data["sequence_ref"]).decode("ascii")
            except UnicodeError as exc:
                raise ContractError("product_sequence_not_ascii") from exc
            if not sequence or any(char.isspace() for char in sequence):
                raise ContractError("invalid_product_sequence_representation")
            parent_coverage = [span for ref in data["parent_refs"] for span in self.coverage(ref)]
            for span in data["footprint"]:
                libraries.span(self, span)
                if not self._covered_by([span], parent_coverage):
                    raise ContractError("product_mapping_outside_parent")
            if not data["footprint"] and any(self.roots(ref) for ref in data["parent_refs"]):
                raise ContractError("product_mapping_required")
            mapping, source_ref = data.get("mapping"), data.get("mapping_source_ref")
            if (mapping is None) != (source_ref is None):
                raise ContractError("mapping_and_source_required_together")
            if mapping is not None:
                source = self._require(source_ref, {"source"})
                translation = (source["provider"] in {"sequence.translate", "genes.predict"}
                               and data["derivation"] == "translation")
                extraction = source["provider"] == "sequence.view" and data["derivation"] == "extraction"
                if origin != "tool" or source["origin"] != "tool" or not (translation or extraction):
                    raise ContractError("native_derivation_mapping_source_required")
                try:
                    validate_mapping(mapping)
                except ValueError as error:
                    raise ContractError(str(error)) from error
                if mapping["symbol_length"] != len(sequence) or (translation and mapping["units_per_symbol"] != 3):
                    raise ContractError("product_mapping_symbol_length_mismatch")
                for span in mapping["path"]:
                    source_subject = self._require(span["subject_ref"], {"input", "reference", "read_subject"})
                    if (span["unit"] != self.subject_unit(source_subject["id"])
                            or (translation and span["unit"] not in {"nt", "symbol"})
                            or not 0 <= span["start"] < span["end"] <= self.subject_length(source_subject["id"])):
                        raise ContractError("product_mapping_unit_mismatch")
                physical_parents = [part for ref in data["parent_refs"]
                    for part in self.sequence_mapping(ref)["path"]]
                if extraction and any(self.sequence_mapping(ref)["units_per_symbol"] != mapping["units_per_symbol"]
                                      for ref in data["parent_refs"]):
                    raise ContractError("extraction_mapping_scale_changed")
                for span in mapping["path"]:
                    if not any(part["subject_ref"] == span["subject_ref"] and part["unit"] == span["unit"]
                        and part["start"] <= span["start"] < span["end"] <= part["end"] for part in physical_parents):
                        raise ContractError("product_source_mapping_outside_parent")
                if self.footprint_from_mapping(mapping) != self._merge_segments(data["footprint"]):
                    raise ContractError("product_mapping_footprint_mismatch")
                if not any(self.get(ref)["record_type"] == "context"
                    and self.get(ref)["source_ref"] == source_ref for ref in data["context_refs"]):
                    raise ContractError("mapping_source_not_derivation_context")
        if kind == "observation":
            native_database = data.get("native_blast_database")
            if native_database is not None:
                if any(key.startswith('native_') and key != 'native_blast_database' for key in data):
                    raise ContractError('native_blast_database_mixed_native_markers')
                source = self._require(data['source_ref'], {'source'})
                if (origin != 'tool' or source['origin'] != 'tool'
                        or source['provider'] != 'episode.execution_result'
                        or source.get('version') != 'native_blast_database_bundle_v1'):
                    raise ContractError('native_blast_database_requires_native_tool_source')
                if source['artifact_ref'] != native_database['bundle_artifact_ref']:
                    raise ContractError('native_blast_database_bundle_source_mismatch')
                bundle = json.loads(materials.artifact_path(self, source['artifact_ref']).read_bytes())
                job = bundle.get('requested_job', {}).get('native_blast_database', {})
                if (bundle.get('version') != 'native_blast_database_bundle_v1'
                        or bundle.get('mode') != 'database' or job.get('mode') != 'database'
                        or bundle.get('program') != native_database['program']
                        or job.get('program') != native_database['program']):
                    raise ContractError('native_blast_database_bundle_program_or_mode_mismatch')
                expected_axis = {'sequence': 'sequence', 'msa': 'msa_master', 'pssm': 'pssm_master'}.get(job.get('query', {}).get('kind'))
                if (native_database['query_axis_kind'] != expected_axis
                        or data['kind'] != ('profile_match' if native_database['reference_axis_kind'] == 'profile_model' else 'comparison')
                        or len(data['subject_refs']) != 1 or data['source_subject_refs']
                        or not data.get('operand_intervals')
                        or any(row['role'] != 'query' for row in data['operand_intervals'])):
                    raise ContractError('native_blast_database_query_operand_conflict')
                self._require(data['subject_refs'][0], {'input', 'feature', 'product', 'read_subject'})
            native_pairwise = data.get("native_blast_pairwise")
            if native_pairwise is not None:
                if data.get("native_blast") is not None:
                    raise ContractError("native_blast_pairwise_mixed_native_markers")
                source = self._require(data["source_ref"], {"source"})
                if (origin != "tool" or source["origin"] != "tool"
                        or source["provider"] != "episode.execution_result"
                        or source.get("version") != "native_blast_bundle_v1"):
                    raise ContractError("native_blast_pairwise_requires_native_tool_source")
                if data["kind"] != "comparison":
                    raise ContractError("native_blast_pairwise_observation_kind_mismatch")
                if source["artifact_ref"] != native_pairwise["bundle_artifact_ref"]:
                    raise ContractError("native_blast_pairwise_bundle_source_mismatch")
                self._require(native_pairwise["bundle_artifact_ref"], {"artifact"})
                try:
                    with materials.artifact_path(self, native_pairwise["bundle_artifact_ref"]).open(encoding="utf-8") as stream:
                        bundle = json.load(stream)
                except (OSError, ValueError, UnicodeError) as error:
                    raise ContractError("native_blast_pairwise_bundle_unreadable") from error
                if (not isinstance(bundle, dict) or bundle.get("version") != "native_blast_bundle_v1"
                        or bundle.get("mode") != "pairwise"
                        or bundle.get("program") != native_pairwise["program"]
                        or not isinstance(bundle.get("requested_job"), dict)
                        or not isinstance(bundle["requested_job"].get("native_blast"), dict)
                        or bundle["requested_job"]["native_blast"].get("program") != native_pairwise["program"]
                        or bundle["requested_job"]["native_blast"].get("mode") != "pairwise"):
                    raise ContractError("native_blast_pairwise_bundle_program_or_mode_mismatch")
            native_hmmer = data.get("native_hmmer")
            if native_hmmer is not None:
                source = self._require(data["source_ref"], {"source"})
                if origin != "tool" or source["provider"] != "episode.execution_result":
                    raise ContractError("native_hmmer_requires_native_tool_source")
                if source["artifact_ref"] != native_hmmer["bundle_artifact_ref"]:
                    raise ContractError("native_hmmer_bundle_source_mismatch")
                self._require(native_hmmer["bundle_artifact_ref"], {"artifact"})
                expected_family = ("alignment_sequence" if native_hmmer["program"] == "hmmalign"
                    else "nucleotide_locus" if native_hmmer["program"] in {"nhmmer", "nhmmscan"}
                    else "protein_domain")
                if native_hmmer["family"] != expected_family:
                    raise ContractError("native_hmmer_program_family_mismatch")
            native_infernal = data.get("native_infernal")
            if native_infernal is not None:
                source = self._require(data["source_ref"], {"source"})
                if (origin != "tool" or source["origin"] != "tool"
                        or source["provider"] != "episode.execution_result"
                        or source.get("version") != "native_infernal_bundle_v1"):
                    raise ContractError("native_infernal_requires_native_tool_source")
                if source["artifact_ref"] != native_infernal["bundle_artifact_ref"]:
                    raise ContractError("native_infernal_bundle_source_mismatch")
                self._require(native_infernal["bundle_artifact_ref"], {"artifact"})
                bundle = json.loads(self.get_artifact(native_infernal["bundle_artifact_ref"]))
                if (not isinstance(bundle, dict) or bundle.get("version") != "native_infernal_bundle_v1"
                        or bundle.get("program") != native_infernal["program"]):
                    raise ContractError("native_infernal_bundle_program_mismatch")
                alignment = native_infernal["program"] == "cmalign"
                families = {"alignment_sequence"} if alignment else {"search_hit", "search_sequence"}
                if native_infernal["family"] not in families:
                    raise ContractError("native_infernal_program_family_mismatch")
                if data["kind"] != ("alignment" if alignment else "profile_match"):
                    raise ContractError("native_infernal_observation_kind_mismatch")
            native_mapping = data.get("native_minimap2")
            if native_mapping is not None:
                source = self._require(data["source_ref"], {"source"})
                if origin != "tool" or data["kind"] != "alignment" or source["provider"] != "minimap2.mapping":
                    raise ContractError("native_minimap2_requires_native_tool_source")
                from .read_mapping import parse_paf_line
                # Publication already captured this complete immutable artifact
                # with a streaming digest. Validate the selected row without
                # rehashing a potentially large PAF for every sibling row.
                artifact = self._require(source["stdout_ref"], {"artifact"})
                path = self.path/"artifacts"/artifact["sha256"][:2]/artifact["sha256"]
                start, end = native_mapping["row_start"], native_mapping["row_end"]
                if not 0 <= start < end <= path.stat().st_size:
                    raise ContractError("native_minimap2_row_outside_source")
                with path.open("rb") as handle:
                    if start:
                        handle.seek(start-1)
                        if handle.read(1) != b"\n":
                            raise ContractError("native_minimap2_row_start_not_line_boundary")
                    handle.seek(start)
                    row = parse_paf_line(handle.read(end-start))
                if (data["subject_refs"] != [row["query_name"]]
                    or data["source_subject_refs"] != [row["reference_name"]]
                    or any(native_mapping[key] != row[key] for key in ("strand", "mapping_quality", "native_alignment_type"))):
                    raise ContractError("native_minimap2_operand_identity_mismatch")
                expected = [{"role": role, "subject_ref": ref, "start": bounds[0], "end": bounds[1],
                    "unit": self.subject_unit(ref), "model_unit": "nt"} for role, ref, bounds in
                    (("query", row["query_name"], row["query_interval"]),
                     ("reference", row["reference_name"], row["reference_interval"]))]
                if data.get("operand_intervals") != expected:
                    raise ContractError("native_minimap2_operand_interval_mismatch")
            if data.get("native_blast") is not None:
                if origin != "tool" or data["kind"] != "comparison" or self.get(data["source_ref"])["provider"] != "ncbi_blast":
                    raise ContractError("native_blast_requires_native_tool_source")
            native = data.get("native_cmsearch")
            if native is not None:
                if origin != "tool" or self.get(data["source_ref"])["provider"] != "infernal.cmsearch":
                    raise ContractError("native_cmsearch_requires_native_tool_source")
                model = self._require(native["native_query_model_ref"], {"reference"})
                if model["reference_type"] != "family" or model["id"] not in data["source_subject_refs"]:
                    raise ContractError("cmsearch_model_identity_mismatch")
                if native["native_target_subject_ref"] not in data["subject_refs"]:
                    raise ContractError("cmsearch_target_identity_mismatch")
            if visual_observation:
                if origin == "extracted":
                    raise ContractError("visual_observation_requires_reasoning_origin")
                if data["anchor"] is not None:
                    raise ContractError("visual_and_text_anchors_are_distinct")
                anchor = data["visual_anchor"]
                view = self._require(anchor["view_ref"], {"image_view"})
                if view["origin"] != "tool":
                    raise ContractError("native_image_view_required")
                if view["source_ref"] != data["source_ref"]:
                    raise ContractError("visual_anchor_source_mismatch")
                if view["image_artifact_ref"] != anchor["image_artifact_ref"]:
                    raise ContractError("visual_anchor_image_mismatch")
                region = anchor["region"]
                if region["x"] + region["width"] > view["width"] or region["y"] + region["height"] > view["height"]:
                    raise ContractError("visual_anchor_region_outside_image")
            elif origin == "extracted":
                self._anchor(data["anchor"], data["source_ref"])
            elif data["anchor"] is not None:
                self._anchor(data["anchor"], data["source_ref"])
            for ref in data["subject_refs"] + data["source_subject_refs"]:
                self._require(ref, {"input", "feature", "product", "reference", "context", "read_subject"})
            seen_operands = set()
            for operand in data.get("operand_intervals") or ():
                ref = operand["subject_ref"]
                physical_subject = self._require(ref, {"input", "feature", "product", "reference", "read_subject"})
                # A native database HSP can report actual reference coordinates
                # and length without supplying the complete reference sequence.
                # This permits its source interval, never sequence execution.
                source_length = (physical_subject.get("length") if data.get("native_blast") is not None
                    and operand["role"] == "reference" and physical_subject["record_type"] == "reference"
                    and physical_subject.get("sequence_ref") is None else None)
                length = source_length if type(source_length) is int and source_length > 0 else self.subject_length(ref)
                if not 0 <= operand["start"] < operand["end"] <= length:
                    raise ContractError("operand_interval_outside_subject")
                if operand["unit"] != self.subject_unit(ref):
                    raise ContractError("operand_interval_unit_mismatch")
                declared = data["subject_refs"] if operand["role"] == "query" else data["source_subject_refs"]
                if ref not in declared:
                    raise ContractError("operand_subject_mismatch")
                key = (operand["role"], ref, operand["start"], operand["end"])
                if key in seen_operands:
                    raise ContractError("duplicate_operand_interval")
                seen_operands.add(key)
        if kind == "hypothesis":
            for ref in data["subject_refs"]:
                self._require(ref, {"input", "feature", "product", "reference", "context", "read_subject"})
        if kind in {"assessment", "annotation"}:
            has_account = "context_account_scope" in data
            if ("context_scope" in data or (kind == "assessment" and data["extent_basis"] == "context_allocation")) and not has_account:
                raise ContractError("context_account_scope_required")
            if has_account:
                account = self.normalize_context_mask(data["context_account_scope"])
                if not account["subject_refs"]:
                    raise ContractError("context_account_domain_must_be_nonempty")
                allocated = data.get("context_scope")
                if allocated is not None and not self.context_mask_subset(allocated, account):
                    raise ContractError("context_allocation_outside_account_domain")
                if kind == "assessment" and (data["extent_basis"] != "context_allocation" or data.get("target_footprint") is not None):
                    raise ContractError("context_allocation_distinct_from_physical_extent")
                if kind == "annotation" and data["footprint_kind"] != "whole_input_context":
                    raise ContractError("context_account_requires_whole_input_context")
        if kind == "assessment":
            hypothesis = self._require(data["hypothesis_ref"], {"hypothesis"})
            observation = self._require(data["observation_ref"], {"observation"})
            if 'investigation_finding' in data:
                from .scientific_findings import validate_finding
                validate_finding(self, data, observation)
            if data["extent_basis"] == "inferred_extent" and data["applicability"] == "direct":
                raise ContractError("assessment_inferred_extent_cannot_be_direct", detail={
                    "field_path": ["extent_basis"], "extent_basis": "inferred_extent",
                    "applicability": "direct",
                    "compatible_applicability": ["transfer", "contextual", "scope_limited", "incomparable"]})
            bridge = data.get("target_footprint")
            if bridge is not None:
                for segment in bridge:
                    try:
                        libraries.span(self, segment)
                    except ContractError as error:
                        raise ContractError("assessment_target_footprint_outside_input", detail={"cause_code": str(error)}) from error
                hypothesis_coverage = self._merge_segments([span
                    for subject_ref in hypothesis["subject_refs"]
                    if self.get(subject_ref)["record_type"] in {"input", "feature", "product", "read_subject"}
                    for span in self.coverage(subject_ref)])
                if not hypothesis_coverage:
                    raise ContractError("assessment_hypothesis_has_no_input_coverage")
                if not self._covered_by(bridge, hypothesis_coverage):
                    raise ContractError("assessment_target_footprint_outside_hypothesis")
            empirical = {"assay_report", "biochemical_assay", "genetic_phenotype", "growth_assay"}
            if data["applicability"] == "direct" and observation["kind"] in empirical:
                if not set(hypothesis["subject_refs"]) & set(observation["source_subject_refs"]):
                    raise ContractError("source_subject_mismatch")
            for ref in data["assumption_refs"]:
                self._require(ref, {"hypothesis"})
        if kind == "annotation":
            self._require(data["subject_ref"], {"input", "feature", "product", "reference", "read_subject", "context"} if "context_account_scope" in data else {"input", "feature", "product", "reference", "read_subject"})
            if "context_account_scope" not in data:
                self.coverage(data["subject_ref"])
            for group in data["coherent_sets"]:
                hypothesis_refs = [item["hypothesis_ref"] for item in group["interpretations"]]
                if len(hypothesis_refs) != len(set(hypothesis_refs)):
                    raise ContractError("duplicate_hypothesis_in_coherent_set")
                for ref in group["context_refs"]:
                    self._require(ref, {"context", "hypothesis"})
                for item in group["interpretations"]:
                    hypothesis = self._require(item["hypothesis_ref"], {"hypothesis"})
                    if "context_account_scope" in data:
                        if data["subject_ref"] not in hypothesis["subject_refs"]:
                            raise ContractError("annotation_context_subject_mismatch")
                    else:
                        hypothesis_coverage = self._merge_segments([span for subject in hypothesis["subject_refs"] for span in self.coverage(subject)])
                        annotation_coverage = self._merge_segments(self.coverage(data["subject_ref"]))
                        if hypothesis_coverage != annotation_coverage:
                            raise ContractError("annotation_hypothesis_footprint_mismatch")
                    for ref in item["assessment_refs"]:
                        assessment = self._require(ref, {"assessment"})
                        if assessment["hypothesis_ref"] != hypothesis["id"]:
                            raise ContractError("assessment_hypothesis_mismatch")
            for ref in data["alternative_refs"]:
                hypothesis = self._require(ref, {"hypothesis"})
                if "context_account_scope" in data:
                    if data["subject_ref"] not in hypothesis["subject_refs"]:
                        raise ContractError("annotation_context_subject_mismatch")
                else:
                    hypothesis_coverage = self._merge_segments([span for subject in hypothesis["subject_refs"] for span in self.coverage(subject)])
                    if hypothesis_coverage != self._merge_segments(self.coverage(data["subject_ref"])):
                        raise ContractError("annotation_hypothesis_footprint_mismatch")

    def _record_roots(self, kind, data):
        if kind in {"assessment", "annotation"} and "context_account_scope" in data:
            return list((data.get("context_scope") or {"subject_refs": []})["subject_refs"])
        refs = []
        if kind == "read_selection":
            refs = [data["library_ref"]]
        elif kind in {"feature", "annotation"}:
            refs = [data["subject_ref"]]
        elif kind == "product":
            refs = data["parent_refs"]
        elif kind in {"hypothesis", "observation"}:
            refs = data["subject_refs"]
        elif kind == "assessment":
            refs = [data["hypothesis_ref"]]
        elif kind == "context":
            refs = data["related_refs"]
        return sorted({root for ref in refs for root in self.roots(ref)})

    def _assessment_write_extent(self, data):
        """Use the existing attribution geometry, never its score or weights.

        These shared primitives preserve measured observed/inferred extents.
        Unknown geometry returns None so the
        ownership boundary can conservatively use declared hypothesis extent;
        it does not acquire a new scientific admission/quality assessment.
        """
        from .evidence_geometry import (_assessment_extent, _intersection, _mapped_coverage,
                                        _observation_extents, _public_footprint)
        try:
            if data["extent_basis"] == "inferred_extent":
                # Missing inferred extent remains valid, explicitly unlocalized
                # science with its existing notice and no spatial contribution.
                return data.get("target_footprint") or []
            hypothesis = self.get(data["hypothesis_ref"])
            coverage = _mapped_coverage(self, hypothesis["subject_refs"])
            observed = self.get(data["observation_ref"])
            physical = _mapped_coverage(self, observed["source_subject_refs"])
            assessed = _assessment_extent(data, self)
            native_operands = observed["origin"] == "tool" and observed.get("operand_intervals") is not None
            result = []
            for observed_coverage, _factor, _details in _observation_extents(self, observed):
                if not observed_coverage and observed.get("operand_intervals") is None and physical:
                    observed_coverage = physical
                extent = {}
                for dimension, spans in coverage.items():
                    bounded = _intersection(spans, observed_coverage.get(dimension, ()))
                    if not native_operands and dimension in physical:
                        bounded = _intersection(bounded, physical[dimension])
                    if assessed:
                        bounded = _intersection(bounded, assessed.get(dimension, ()))
                    if bounded:
                        extent[dimension] = bounded
                result.extend(_public_footprint(self, extent))
            return self._merge_segments(result)
        except (ContractError, ValueError):
            return None

    def _ownership_reach(self, references):
        """Logical original-data ownership, distinct from physical credit extent.

        Preserve every typed branch. A context about one read stays local; an
        explicit library container remains global even alongside local refs.
        Dataset masks stay compact handles, never fake sequence coordinates.
        """
        pending = [(ref, False) for ref in references]
        seen, spans, context_spans, containers, selections = set(), [], [], set(), set()
        while pending:
            ref, through_context = pending.pop()
            if (ref, through_context) in seen:
                continue
            seen.add((ref, through_context))
            row = self.get(ref)
            kind = row["record_type"]
            if libraries.is_library(row):
                containers.add(ref)
            elif kind in {"input", "read_subject", "feature", "product"}:
                actual = self.coverage(ref)
                spans.extend(actual)
                if through_context:
                    context_spans.extend(actual)
            elif kind == "read_selection":
                selections.add(ref)
            elif kind == "context":
                pending.extend((related, True) for related in row["related_refs"])
            elif kind in {"hypothesis", "observation"}:
                pending.extend((subject, through_context) for subject in row["subject_refs"])
            elif kind == "assessment":
                pending.append((row["hypothesis_ref"], through_context))
            elif kind in {"annotation", "interpretation_account"}:
                pending.append((row["subject_ref"], through_context))
            else:
                # Unknown rooted extent stays conservative rather than becoming
                # ownerless. Rootless external custody remains reusable context.
                containers.update(target for target in self.roots(ref) if libraries.is_library(self.get_input(target)))
        return {"segments": self._merge_segments(spans), "context_segments": self._merge_segments(context_spans),
            "library_refs": sorted(containers), "selection_refs": sorted(selections)}

    def _assert_read_member_reach(self, reach, scope, *, field_path, reference):
        by_member = {}
        for span in reach["segments"]:
            if "member_ref" in span:
                by_member.setdefault((span["target_ref"], span["member_ref"]), []).append(span)
        for (target_ref, member_ref), spans in by_member.items():
            allowed = self.scope_dimension_segments(scope, self.read_subject_ref(target_ref, member_ref))
            if not any(max(span["start"], part["start"]) < min(span["end"], part["end"])
                    for span in spans for part in allowed):
                raise ContractError("record_subject_member_outside_scope", detail={
                    "field_path": field_path, "reference": reference,
                    "target_ref": target_ref, "member_ref": member_ref})
        for selection_ref in reach["selection_refs"]:
            selection = self.get(selection_ref)
            target_ref = selection["library_ref"]
            if target_ref not in scope["subject_refs"]:
                raise ContractError("record_subject_member_outside_scope", detail={"field_path": field_path,
                    "reference": reference, "target_ref": target_ref, "selection_ref": selection_ref})
            if "segments" in scope:
                member_refs = sorted({span["member_ref"] for span in scope["segments"] if span["target_ref"] == target_ref})
                allowed = [self.read_subject_ref(target_ref, member_ref) for member_ref in member_refs]
                missing = self.db.execute("SELECT read_ref FROM library_selection_members WHERE selection_ref=? AND read_ref NOT IN (SELECT value FROM json_each(?)) LIMIT 1",
                    (selection_ref, canonical(allowed))).fetchone()
            else:
                owned = libraries.selection_for(self, scope, target_ref)
                missing = (self.db.execute("SELECT read_ref FROM library_selection_members WHERE selection_ref=? EXCEPT SELECT read_ref FROM library_selection_members WHERE selection_ref=? LIMIT 1",
                    (selection_ref, owned["id"])).fetchone() if owned else None)
            if missing:
                raise ContractError("record_subject_member_outside_scope", detail={"field_path": field_path,
                    "reference": reference, "target_ref": target_ref, "selection_ref": selection_ref,
                    "outside_read_ref": missing[0]})

    def _assert_library_write_scope(self, kind, data, scope, *, current=None):
        """Owned original members are distinct from broader read visibility.

        This checks ownership, never truth, certainty or scientific usefulness.
        External/context subjects without original-read geometry stay reusable.
        """
        if scope is None or kind not in {"hypothesis", "observation", "assessment", "context", "annotation"}:
            return
        normalized = self.validate_scope(scope)
        if kind in {"assessment", "annotation"} and "context_account_scope" in data:
            # A lineage domain is identity, not blanket edit permission. Only
            # actual prior/proposed allocated positions are replaced by CAS.
            for label, allocation, prior in (("proposed", data.get("context_scope"), False),
                    ("current", current.get("context_scope") if current else None, True)):
                if allocation is not None and not self.context_mask_subset(allocation, normalized):
                    detail = {"field_path": ["expected_revision"] if prior else ["context_scope"],
                        "meaning": "context_revision_requires_ownership_of_prior_and_proposed_allocation",
                        "allocation": label}
                    if prior:
                        detail.update(current_record_ref=current["id"], current_revision=current["revision"])
                    raise ContractError("context_allocation_outside_assigned_scope", detail=detail)
            return
        library_roots = [ref for ref in self._record_roots(kind, data)
            if libraries.is_library(self.get_input(ref))]
        if not library_roots or all(ref in normalized["subject_refs"] and
                self.scope_measure(normalized, ref) == self.get_input(ref)["position_mass"] for ref in library_roots):
            return
        if kind == "annotation":
            # The container has no physical sequence interval. Its empty
            # footprint must not make a whole-library publication ownerless;
            # local read subjects retain the physical containment check in put.
            subject = self.get(data["subject_ref"])
            if libraries.is_library(subject):
                detail = {"field_path": ["expected_revision"] if current else ["subject_ref"],
                    "subject_ref": subject["id"], "target_ref": subject["id"],
                    "meaning": "library_annotation_requires_ownership_of_its_fixed_original_library"}
                if current:
                    detail.update(current_annotation_ref=current["id"], current_revision=current["revision"])
                raise ContractError("annotation_library_context_outside_assigned_scope", detail=detail)
            return
        if kind in {"hypothesis", "observation", "context"}:
            field = "related_refs" if kind == "context" else "subject_refs"
            for index, ref in enumerate(data[field]):
                self._assert_read_member_reach(self._ownership_reach([ref]), normalized,
                    field_path=[field, index], reference=ref)
            return
        hypothesis = self.get(data["hypothesis_ref"])
        hypothesis_coverage = self.record_coverage(hypothesis)
        reach = self._ownership_reach(hypothesis["subject_refs"])
        # Explicit attribution can localize a broader existing hypothesis. A
        # missing inference keeps its valid zero extent, but cannot use a wholly
        # disjoint target hypothesis as if that target belonged to this child.
        if not data.get("target_footprint"):
            try:
                self._assert_read_member_reach(reach, normalized,
                    field_path=["hypothesis_ref"], reference=data["hypothesis_ref"])
            except ContractError as error:
                raise ContractError("assessment_hypothesis_member_outside_scope", detail=error.detail) from error
        attributed = self._assessment_write_extent(data)
        if attributed is None:
            attributed = data.get("target_footprint") or hypothesis_coverage
        if not self.scope_covers([span for span in attributed if "member_ref" in span], normalized):
            raise ContractError("assessment_attribution_outside_assigned_read_scope", detail={
                "field_path": ["target_footprint"], "hypothesis_ref": data["hypothesis_ref"],
                "observation_ref": data["observation_ref"],
                "meaning": "actual_original_member_attribution_exceeds_assigned_scope"})
        if current is not None:
            prior = self._assessment_write_extent(current)
            if prior is None:
                prior = current.get("target_footprint") or hypothesis_coverage
            # Explicit global/context branches remain part of record ownership
            # even beside a direct sequence whose observation has local bounds.
            for target_ref in reach["library_refs"]:
                target = self.get_input(target_ref)
                if self.scope_measure(normalized, target_ref) != target["position_mass"]:
                    raise ContractError("assessment_current_library_context_outside_assigned_scope", detail={
                        "field_path": ["expected_revision"], "current_assessment_ref": current["id"],
                        "current_revision": current["revision"], "target_ref": target_ref,
                        "meaning": "existing_library_context_requires_ownership_of_its_fixed_original_library"})
            if not self.scope_covers([span for span in reach["context_segments"] if "member_ref" in span], normalized):
                raise ContractError("assessment_current_context_attribution_outside_assigned_scope", detail={
                    "field_path": ["expected_revision"], "current_assessment_ref": current["id"],
                    "current_revision": current["revision"], "hypothesis_ref": data["hypothesis_ref"],
                    "meaning": "existing_context_keeps_its_actual_original_member_relationships"})
            for selection_ref in reach["selection_refs"]:
                selection = self.get(selection_ref)
                if not self.scope_contains(normalized, {"subject_refs": [selection["library_ref"]], "read_selection_refs": [selection_ref]}):
                    raise ContractError("assessment_current_context_attribution_outside_assigned_scope", detail={
                        "field_path": ["expected_revision"], "current_assessment_ref": current["id"],
                        "current_revision": current["revision"], "selection_ref": selection_ref})
            if not self.scope_covers([span for span in prior if "member_ref" in span], normalized):
                raise ContractError("assessment_current_attribution_outside_assigned_read_scope", detail={
                    "field_path": ["expected_revision"], "current_assessment_ref": current["id"],
                    "current_revision": current["revision"], "hypothesis_ref": data["hypothesis_ref"],
                    "observation_ref": data["observation_ref"],
                    "meaning": "a_current_revision_replaces_its_whole_record_including_outside_attribution"})

    def assessment_key(self, record):
        lineage = {'hypothesis_ref': record['hypothesis_ref'], 'observation_ref': record['observation_ref']}
        if 'context_account_scope' in record:
            lineage.update(attribution_space='material_context',
                account_scope_sha256=self.context_mask_identity(record['context_account_scope']))
        return identity('assessment_key', lineage)

    def put(self, kind, record, *, origin, scope=None, account_owner=None):
        if kind not in RECORD_SCHEMAS:
            raise ContractError("unknown_record_type")
        account = kind == 'interpretation_account'
        if account and (origin != 'reasoning' or scope is None
                or not isinstance(account_owner, tuple) or len(account_owner) != 2
                or not all(isinstance(part, str) and part for part in account_owner)):
            raise ContractError('interpretation_account_requires_runtime_owner_and_scope')
        validation_kind = 'annotation' if account else kind
        record = deepcopy(record)
        if kind == "observation" and record.get("operand_intervals") is None:
            record.pop("operand_intervals", None)
        if kind == "product" and record.get("mapping") is None and record.get("mapping_source_ref") is None:
            record.pop("mapping", None)
            record.pop("mapping_source_ref", None)
        expected_revision = record.pop("expected_revision", None)
        if kind == "observation" and record.get("visual_anchor") is None:
            record.pop("visual_anchor", None)
        if kind == "assessment" and record.get("target_footprint") is None:
            # Absence and explicit null mean the same thing; transport syntax
            # must not create a new scientific revision or invalidate old links.
            record.pop("target_footprint", None)
        if kind in {"assessment", "annotation", "interpretation_account"} and "context_account_scope" in record:
            record["context_account_scope"] = self.normalize_context_mask(record["context_account_scope"])
            if record.get("context_scope") is None:
                record.pop("context_scope", None)
            else:
                record["context_scope"] = self.normalize_context_mask(record["context_scope"])
        self._validate_record(kind, record, origin)
        if kind in {"assessment", "annotation", "interpretation_account"} and "context_account_scope" in record:
            # Host-derived audit metadata is not accepted as model-authored
            # input and is never a semantic record reference.
            record["context_binding_version"] = context_masks.VERSION
            record["context_account_sha256"] = self.context_mask_identity(record["context_account_scope"])
            record["context_allocation_sha256"] = (self.context_mask_identity(record["context_scope"])
                if "context_scope" in record else None)
        if kind == "assessment" and "target_footprint" in record:
            record["target_footprint"] = self._merge_segments(record["target_footprint"])
            if scope is not None and not self.scope_covers(record["target_footprint"], scope):
                raise ContractError("assessment_target_footprint_outside_scope")
        roots = self._record_roots(validation_kind, record)
        if scope is not None and "context_account_scope" not in record and not set(roots) <= set(self.validate_scope(scope)["subject_refs"]):
            raise ContractError("record_outside_scope")
        if kind == 'assessment' and scope is not None and 'investigation_finding' in record:
            from .scientific_findings import validate_replacement_scope
            validate_replacement_scope(self, record, scope)
        if validation_kind != "annotation":
            self._assert_library_write_scope(kind, record, scope)
        with self.transaction():
            if kind in {"assessment", "annotation", "interpretation_account"}:
                if account:
                    key = identity('interpretation_account_key', {
                        'owner': list(account_owner), 'scope': self.validate_scope(scope),
                        'subject_ref': record['subject_ref'],
                        'context_account_sha256': record.get('context_account_sha256')})
                elif kind == 'assessment':
                    key = self.assessment_key(record)
                elif "context_account_scope" in record:
                    lineage = ({"hypothesis_ref": record["hypothesis_ref"], "observation_ref": record["observation_ref"]}
                        if kind == "assessment" else {"subject_ref": record["subject_ref"]})
                    key = identity(kind + "_key", {**lineage, "attribution_space": "material_context",
                        "account_scope_sha256": record["context_account_sha256"]})
                else:
                    key = record["subject_ref"]
                current = self.db.execute("SELECT revision,record_ref FROM current_revisions WHERE record_type=? AND key_ref=?", (kind, key)).fetchone()
                revision = current["revision"] if current else 0
                if validation_kind == "annotation" or current is not None:
                    self._assert_library_write_scope(validation_kind, record, scope,
                        current=self.get(current["record_ref"]) if current else None)
                if expected_revision is None:
                    raise ContractError("expected_revision_required")
                if type(expected_revision) is not int or expected_revision < 0:
                    raise ContractError("invalid_expected_revision")
                if expected_revision != revision:
                    proposal = {"record": record, "origin": origin, "expected_revision": expected_revision}
                    proposal_ref = identity("proposal", {"kind": kind, "key": key, **proposal})
                    self.db.execute("INSERT OR IGNORE INTO proposals VALUES(?,?,?,?,?)", (proposal_ref, kind, key, expected_revision, canonical(proposal)))
                    # Caller transaction must preserve this proposal when reporting conflict.
                    conflict = RevisionConflict(kind, key, revision, proposal_ref)
                else:
                    conflict = None
                    if current:
                        previous = self.get(current["record_ref"])
                        if "context_account_scope" in record:
                            for field in ("context_account_scope", "context_scope"):
                                if field in previous and field in record and self.context_mask_identity(previous[field]) == self.context_mask_identity(record[field]):
                                    record[field] = deepcopy(previous[field])
                        previous_payload = {k: v for k, v in previous.items() if k not in {"id", "record_type", "origin", "revision", "footprint", "key_ref"}}
                        if validation_kind == "annotation":
                            previous_payload["coherent_sets"] = [{k:v for k,v in group.items() if k != "id"} for group in previous_payload["coherent_sets"]]
                        if canonical(previous_payload) == canonical(record) and previous["origin"] == origin:
                            return previous
                    revision += 1
                    record = {**record, "revision": revision}
            else:
                conflict = None
            if conflict is None:
                if validation_kind == "annotation":
                    record["footprint"] = [] if "context_account_scope" in record else self.coverage(record["subject_ref"])
                    record["coherent_sets"] = [{**group, "id": identity("coherent_set", group)} for group in record["coherent_sets"]]
                identity_data = {"origin": origin, "record": record}
                if account:
                    identity_data['lineage'] = key
                ref = identity(kind, identity_data)
                stored = {**record, "id": ref, "record_type": kind, "origin": origin}
                if scope is not None and kind in {"feature", "product", "annotation", "interpretation_account"}:
                    if kind == "feature":
                        parent = self.get(record["subject_ref"])
                        footprint = self.map_segments(parent["id"], record["segments"])
                    else:
                        footprint = record["footprint"]
                    if not self.scope_covers(footprint, scope):
                        raise ContractError("record_outside_scope_segments")
                self.db.execute("INSERT OR IGNORE INTO records VALUES(?,?,?,?)", (ref, kind, origin, canonical(stored)))
                self.db.executemany("INSERT OR IGNORE INTO record_roots VALUES(?,?)", [(ref, root) for root in roots])
                if kind in {"assessment", "annotation", "interpretation_account"}:
                    self.db.execute("INSERT INTO current_revisions VALUES(?,?,?,?) ON CONFLICT(record_type,key_ref) DO UPDATE SET revision=excluded.revision,record_ref=excluded.record_ref", (kind, key, revision, ref))
        if conflict is not None:
            raise conflict
        return stored

    def _current(self, kind, scope=None, limit=None, offset=0):
        normalized = self.validate_scope(scope) if scope is not None else None
        parameters = [kind]
        condition = ""
        if normalized is not None:
            placeholders = ",".join("?" for _ in normalized["subject_refs"])
            condition = f" AND (json_type(r.data,'$.context_account_scope') IS NOT NULL OR NOT EXISTS (SELECT 1 FROM record_roots rr WHERE rr.record_ref=c.record_ref AND rr.target_ref NOT IN ({placeholders}))) AND library_scope_record(r.data,?)"
            parameters.extend([*normalized["subject_refs"], canonical(normalized)])
        paging = ""
        if limit is not None:
            if type(limit) is not int or limit < 0 or type(offset) is not int or offset < 0:
                raise ContractError("invalid_page")
            paging = " LIMIT ? OFFSET ?"
            parameters.extend([limit, offset])
        rows = self.db.execute("SELECT r.data FROM current_revisions c JOIN records r ON r.id=c.record_ref WHERE c.record_type=?" + condition + " ORDER BY c.key_ref" + paging, parameters)
        return [json.loads(row[0]) for row in rows]

    def iter_current_annotations(self, scope=None, page_size=100):
        yield from self.iter_current_accounts('annotation', scope, page_size)

    def iter_current_accounts(self, kind, scope=None, page_size=100):
        if kind not in {'annotation', 'interpretation_account'}:
            raise ContractError('scientific_account_kind_required')
        if type(page_size) is not int or page_size < 1:
            raise ContractError('invalid_page')
        offset = 0
        while True:
            rows = self._current(kind, scope, limit=page_size, offset=offset)
            yield from rows
            if len(rows) < page_size:
                return
            offset += len(rows)

    def current_assessment_subset(self, refs):
        if not refs:
            return {}
        rows = self.db.execute("SELECT r.data FROM current_revisions c JOIN records r ON r.id=c.record_ref WHERE c.record_type='assessment' AND c.record_ref IN (SELECT value FROM json_each(?))", (canonical(list(dict.fromkeys(refs))),))
        return {row["id"]: row for row in (json.loads(value[0]) for value in rows)}

    def current_annotations(self, scope=None, limit=None, offset=0):
        return self._current("annotation", scope, limit, offset)

    def current_assessments(self, scope=None, limit=None, offset=0):
        return self._current("assessment", scope, limit, offset)

    def count(self, kind, scope=None, *, current=False):
        if kind not in RECORD_SCHEMAS:
            raise ContractError("unknown_record_type")
        parameters = [kind]
        base = "SELECT count(*) FROM records r WHERE r.record_type=?"
        if current:
            base = "SELECT count(*) FROM current_revisions c JOIN records r ON r.id=c.record_ref WHERE r.record_type=?"
        if scope is not None:
            normalized = self.validate_scope(scope)
            placeholders = ",".join("?" for _ in normalized["subject_refs"])
            base += f" AND (json_type(r.data,'$.context_account_scope') IS NOT NULL OR NOT EXISTS (SELECT 1 FROM record_roots rr WHERE rr.record_ref=r.id AND rr.target_ref NOT IN ({placeholders}))) AND library_scope_record(r.data,?)"
            parameters.extend([*normalized["subject_refs"], canonical(normalized)])
        return self.db.execute(base, parameters).fetchone()[0]

    def _artifact_references(self, candidates=None):
        """The existing scientific artifact ownership projection, optionally filtered.

        SQLite prefilters candidate-bearing metadata; the same declared-reference
        walker establishes actual ownership. Source/artifact contents, archived
        contexts and unrelated metadata rows are never loaded into Python.
        """
        selected = None if candidates is None else set(candidates)
        if selected == set():
            return set()
        parameters = () if selected is None else (canonical(sorted(selected)),)
        condition = "" if selected is None else " WHERE EXISTS (SELECT 1 FROM json_tree(records.data) j WHERE j.type='text' AND j.value IN (SELECT value FROM json_each(?)))"
        artifact_refs = set()
        for row in self.db.execute("SELECT data FROM records" + condition, parameters):
            for ref in self._refs(json.loads(row[0])):
                if ref.startswith("artifact_"):
                    artifact_refs.add(ref)
        condition = "" if selected is None else " WHERE json_extract(data,'$.sequence_ref') IN (SELECT value FROM json_each(?))"
        for row in self.db.execute("SELECT data FROM inputs" + condition, parameters):
            sequence_ref = json.loads(row[0])["sequence_ref"]
            if sequence_ref is not None:
                artifact_refs.add(sequence_ref)
        condition = "" if selected is None else " AND EXISTS (SELECT 1 FROM material_members m WHERE m.id=json_extract(records.data,'$.member_ref') AND (coalesce(json_extract(m.data,'$.sequence_ref'),'artifact_' || json_extract(m.data,'$.storage.components.sequence.sha256')) IN (SELECT value FROM json_each(?)) OR coalesce(json_extract(m.data,'$.quality_ref'),'artifact_' || json_extract(m.data,'$.storage.components.quality.sha256')) IN (SELECT value FROM json_each(?)) OR coalesce(json_extract(m.data,'$.header_ref'),'artifact_' || json_extract(m.data,'$.storage.components.header.sha256')) IN (SELECT value FROM json_each(?))))"
        for row in self.db.execute("SELECT json_extract(data,'$.member_ref') FROM records WHERE record_type='reference' AND json_extract(data,'$.member_ref') IS NOT NULL" + condition,
                                   parameters * 3):
            member = self.get(row[0])
            artifact_refs.update(ref for ref in materials.packing.materialized_components(self, member).values() if ref)
        problem = self.problem()
        artifact_refs.update(ref for key, ref in problem.items() if key.endswith("_ref") and isinstance(ref, str) and ref.startswith("artifact_"))
        return artifact_refs if selected is None else artifact_refs & selected

    def reference_subset(self, candidates, scope=None):
        """Resolve just supplied candidates under the existing form registry boundary."""
        scope = self.validate_scope(scope)
        records = {}
        for ref in dict.fromkeys(candidates):
            if not isinstance(ref, str):
                continue
            try:
                records[ref] = self.get(ref)
            except ContractError:
                continue
        artifacts = self._artifact_references(ref for ref, row in records.items() if row["record_type"] == "artifact")
        return [ref for ref, row in records.items() if
            (row["record_type"] == "artifact" and ref in artifacts)
            or (row["record_type"] == "input" and ref in scope["subject_refs"])
            or (row["record_type"] == "read_subject" and self._in_scope(ref, scope))
            or (row["record_type"] in RECORD_SCHEMAS and self._in_scope(ref, scope))]

    def references(self, scope=None):
        scope = self.validate_scope(scope)
        result = {kind: [] for kind in ["input", "subject", "artifact", *RECORD_SCHEMAS]}
        result["input"] = list(scope["subject_refs"])
        result["subject"] = list(scope["subject_refs"])
        for kind in RECORD_SCHEMAS:
            result[kind] = [row["id"] for row in self.list(kind, scope, limit=2**31-1)]
        result["subject"] += result["feature"] + result["product"]
        # Scientific sources and input material are reusable context. Private
        # diagnostics/unattached artifact files are not scientific references.
        result["artifact"] = sorted(self._artifact_references())
        return result

    def reasoning_view(self, scope=None, limit=100, *, record_selection=None):
        scope = self.validate_scope(scope)
        if type(limit) is not int or limit < 1:
            raise ContractError("invalid_page")
        with self.read_snapshot():
            result = {"problem_ref": self.problem()["id"], "scope": scope,
                "subjects": [materials.model_record_view(self, self.get_input(ref)) for ref in scope["subject_refs"]], "pages": {}}
            plural = {"feature": "features", "product": "products", "source": "sources", "term": "terms",
                "reference": "references", "context": "contexts", "observation": "observations",
                "hypothesis": "hypotheses", "assessment": "assessments", "annotation": "annotations",
                "interpretation_account": "interpretation_accounts"}
            for kind, field in plural.items():
                # A received immutable version remains known after an unseen
                # revision. Do not replace it with unreceived scientific text
                # or silently remove it from this episode's information.
                current = (record_selection is None
                           and kind in {"assessment", "annotation", "interpretation_account"})
                page = self.query_records(kind, scope, limit=limit, current_only=current,
                                          record_selection=record_selection)
                result[field] = [materials.model_record_view(self, row) for row in page["records"]]
                result["pages"][field] = {key: page[key] for key in
                    ("offset", "limit", "total", "next_offset", "current_only", "next_query")}
            for kind, field in (("material", "materials"), ("collection", "collections"), ("parse_attempt", "parse_attempts"), ("material_link", "material_links")):
                page = self.query_records(kind, scope, limit=limit, record_selection=record_selection)
                result[field] = page["records"]
                result["pages"][field] = {key: page[key] for key in ("offset", "limit", "total", "next_offset", "current_only", "next_query")}
            result["target_binding"] = self.problem().get("target_binding", "sequence_targets")
            result["read_library_access"] = [{"library_ref": ref,
                "tool": "library.members", "arguments": {"library_ref": ref},
                "scope_position_mass": self.scope_measure(scope, ref)} for ref in scope["subject_refs"]
                if libraries.is_library(self.get_input(ref))]
            context_sources = [self.problem().get("caller_context_source_ref"), self.problem().get("manifest_source_ref")]
            context_sources += [ref for subject in result["subjects"] for ref in subject.get("context_source_refs", [])]
            result["supplied_context_source_refs"] = sorted({ref for ref in context_sources if ref})
            if record_selection is not None:
                revision_refs = [row['id'] for field in
                    ('assessments', 'annotations', 'interpretation_accounts') for row in result[field]]
                current_refs = {row[0] for row in self.db.execute(
                    'SELECT record_ref FROM current_revisions WHERE record_ref IN '
                    '(SELECT value FROM json_each(?))', (canonical(revision_refs),))}
                result['record_view'] = 'received_immutable_versions'
                result['received_revision_status'] = [
                    {'record_ref': ref, 'is_current_revision': ref in current_refs} for ref in revision_refs]
            return result

    @staticmethod
    def reasoning_schema():
        return deepcopy(REASONING_SCHEMA)

    def commit_reasoning(self, payload, scope, operation_key, *, account_owner=None):
        scope = self.validate_scope(scope)
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError("operation_key_required")
        signature_data = {"payload": payload, "scope": scope}
        if isinstance(payload, dict) and payload.get('interpretation_accounts'):
            signature_data['account_owner'] = account_owner
        signature = identity("acquisition", signature_data)
        with self.transaction():
            existing = self.db.execute("SELECT signature,result FROM reasoning_commits WHERE operation_key=?", (operation_key,)).fetchone()
            if existing:
                if existing["signature"] != signature:
                    raise ContractError("operation_key_reused_with_different_input")
                return json.loads(existing["result"])
            result = {"status": "completed", "record_refs": [], "changed_record_refs": [],
                      "aliases": {}, "conflicts": [], "errors": [], "notices": [], "error_code": None}
            if (not isinstance(payload, dict)
                    or not set(REASONING_SCHEMA["required"]) <= set(payload) <= set(REASONING_SCHEMA["properties"])
                    or any(not isinstance(rows, list) for rows in payload.values())):
                result.update(status="invalid", error_code="representation_error")
            else:
                aliases_seen = set()
                sections = [("structural_proposals", "feature", "reasoning"), ("terms", "term", "extracted"),
                            ("source_subjects", "reference", "extracted"), ("contexts", "context", "extracted"),
                            ("observations", "observation", "extracted"), ("hypotheses", "hypothesis", "reasoning"),
                            ("assessments", "assessment", "reasoning"),
                            ("interpretation_accounts", "interpretation_account", "reasoning"),
                            ("annotation_updates", "annotation", "reasoning")]
                for section, kind, origin in sections:
                    for index, proposed in enumerate(payload.get(section, [])):
                        try:
                            validate_schema(proposed, REASONING_SCHEMA["properties"][section]["items"])
                            alias = proposed["alias"]
                            if alias in aliases_seen:
                                raise ContractError("duplicate_alias")
                            aliases_seen.add(alias)
                            def resolve(value, reference_position=False, path=()):
                                if reference_position and isinstance(value, str) and value.startswith("@"):
                                    if value[1:] not in result["aliases"]:
                                        raise ContractError("unresolved_alias", detail={"field_path": list(path), "reference": value})
                                    return result["aliases"][value[1:]]
                                if isinstance(value, dict):
                                    return {key: resolve(child, key == "ref" or key == "dependencies" or key.endswith("_ref") or key.endswith("_refs"), (*path, key)) for key, child in value.items()}
                                if isinstance(value, list):
                                    return [resolve(child, reference_position, (*path, index)) for index, child in enumerate(value)]
                                return value
                            row = resolve({key:value for key,value in proposed.items() if key != "alias"})
                            if section == "terms":
                                row["namespace"] = "source_local"
                                row["accession"] = identity("source_term", {"source_ref": row["source_ref"], "label": row["label"], "anchor": row["anchor"]})
                            if section == "source_subjects":
                                row["accession"] = identity("source_entity", {"source_ref": row["source_ref"], "label": row["label"], "anchor": row["anchor"]})
                                row.update(sequence_ref=None, length=None, molecule=row["reference_type"] if row["reference_type"] in MOLECULES else None, term_refs=[], context_refs=[])
                            before = self.db.total_changes
                            write_origin = ("reasoning" if section == "observations" and row.get("visual_anchor") is not None else origin)
                            stored = self.put(kind, row, origin=write_origin, scope=scope,
                                **({'account_owner': account_owner} if kind == 'interpretation_account' else {}))
                            if (kind == "assessment" and stored["extent_basis"] == "inferred_extent"
                                    and not stored.get("target_footprint")):
                                result["notices"].append({"section": section, "row_index": index,
                                    "record_ref": stored["id"], "field_path": ["target_footprint"],
                                    "code": "inferred_extent_requires_target_footprint"})
                            if kind in {"assessment", "annotation", "interpretation_account"} and "context_account_scope" in stored and "context_scope" not in stored:
                                result["notices"].append({"section": section, "row_index": index,
                                    "record_ref": stored["id"], "field_path": ["context_scope"],
                                    "code": "context_allocation_unlocalized"})
                            result["aliases"][alias] = stored["id"]
                            if stored["id"] not in result["record_refs"]:
                                result["record_refs"].append(stored["id"])
                            if self.db.total_changes > before and stored["id"] not in result["changed_record_refs"]:
                                result["changed_record_refs"].append(stored["id"])
                        except RevisionConflict as exc:
                            result["conflicts"].append(exc.detail)
                        except ContractError as exc:
                            result["errors"].append({"section": section, "row_index": index, "code": str(exc), **exc.detail})
                if result["conflicts"] or result["errors"]:
                    result["status"] = "partial" if result["record_refs"] else "invalid"
                    result["error_code"] = "revision_conflict" if result["conflicts"] else "record_contract_error"
            self.db.execute("INSERT INTO reasoning_commits VALUES(?,?,?)", (operation_key, signature, canonical(result)))
            return result
