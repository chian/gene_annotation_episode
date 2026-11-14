"""Export a consistent current scientific account, with explicit alternatives.

The JSON document is authoritative for export semantics. GFF3 is a smaller
coordinate projection with a companion JSON document; it neither selects an
account nor promotes a candidate or reference label into an annotation.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from typing import Any, Iterable
from urllib.parse import quote

from . import __version__
from .domain import ContractError, canonical
from . import materials_packing as packing
from . import library_targets as libraries

FORMAT = "gene_annotation_episode.current_annotation"
SCHEMA_VERSION = 1
MEMBERSHIPS = (
    "current_annotation_refs", "current_assessment_refs",
    "candidate_feature_refs", "candidate_product_refs",
    "recorded_hypothesis_refs", "recorded_observation_refs",
    "referenced_current_annotation_refs", "referenced_noncurrent_annotation_refs",
    "referenced_current_assessment_refs", "referenced_noncurrent_assessment_refs",
    "source_only_record_refs",
    "supplied_material_refs", "parse_attempt_refs", "collection_refs", "material_link_refs", "indexed_member_refs", "read_selection_refs",
)
# These are explicit format mappings of the domain's native feature categories.
# CDS is deliberately absent: the current schema stores no CDS phase.
GFF_TYPES = {"gene": "gene", "tRNA": "tRNA", "rRNA": "rRNA", "ncRNA": "ncRNA",
             "regulatory_element": "regulatory_region", "repeat": "repeat_region",
             "mobile_element": "mobile_genetic_element", "sequence_region": "region"}
SOURCE_PROVENANCE_KINDS = ("source_derivative", "archive_member", "pmc_version", "pmc_catalog", "pmc_object", "pmc_asset")


def _references(value):
    """Only declared semantic reference positions, never arbitrary source text."""
    if isinstance(value, dict):
        for key, child in value.items():
            if (key == "ref" or key.endswith("_ref")) and child is not None:
                yield child
            elif key.endswith("_refs") or key == "dependencies":
                yield from child
            else:
                yield from _references(child)
    elif isinstance(value, list):
        for child in value:
            yield from _references(child)


def _intersects(footprint, eligible):
    return any(libraries.key(a) == libraries.key(b)
               and max(a["start"], b["start"]) < min(a["end"], b["end"])
               for a in footprint for b in eligible)


def _footprint(store, row):
    kind = row["record_type"]
    if kind in {"input", "feature", "product", "read_subject"}:
        return store.coverage(row["id"])
    if kind == "annotation":
        return row["footprint"]
    if kind == "assessment":
        return _footprint(store, store.get(row["hypothesis_ref"]))
    if kind in {"hypothesis", "observation"}:
        return [span for ref in row["subject_refs"]
                if store.get(ref)["record_type"] in {"input", "feature", "product", "read_subject"}
                for span in store.coverage(ref)]
    return []


class _Selection:
    """Temporary, disk-backed export index; never a scientific state authority."""
    def __init__(self, store, path, scope, page_size):
        self.store, self.scope, self.page_size = store, scope, page_size
        self.db = sqlite3.connect(path)
        self.db.executescript("""
            PRAGMA journal_mode=OFF;
            PRAGMA synchronous=OFF;
            CREATE TABLE nodes(id TEXT PRIMARY KEY,record_type TEXT NOT NULL,data TEXT NOT NULL,processed INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE membership(name TEXT NOT NULL,id TEXT NOT NULL,PRIMARY KEY(name,id));
            CREATE TABLE gff_exclusions(id TEXT PRIMARY KEY,code TEXT NOT NULL);
            CREATE TABLE gff_accounts(feature_ref TEXT NOT NULL,annotation_ref TEXT NOT NULL,PRIMARY KEY(feature_ref,annotation_ref));
        """)
        self.problem = store.problem()
        self.eligible = (None if "segments" not in scope and any(libraries.is_library(store.get_input(ref))
            for ref in scope["subject_refs"]) else store.scope_coverage(scope))
        self.eligible_geometry = [{"target_ref": ref, "target_kind": store.get_input(ref).get("target_kind", "sequence"),
            "position_mass": store.scope_measure(scope, ref),
            "read_selection_ref": (libraries.selection_for(store, scope, ref) or {}).get("id")}
            for ref in scope["subject_refs"]]
        self.packed_indexes, self.library_indexes = [], []
        self._populate()

    def close(self):
        self.db.close()

    def add(self, row_or_ref, membership=None):
        row = self.store.get(row_or_ref) if isinstance(row_or_ref, str) else row_or_ref
        self.db.execute("INSERT OR IGNORE INTO nodes(id,record_type,data) VALUES(?,?,?)",
                        (row["id"], row["record_type"], canonical(row)))
        if membership:
            self.db.execute("INSERT OR IGNORE INTO membership VALUES(?,?)", (membership, row["id"]))

    def _populate(self):
        # Preserve the whole original problem identity even for a local export.
        # Only scientific inventory/current memberships are scoped below.
        for ref in _references(self.problem):
            self.add(ref)
        for ref in _references(self.scope):
            self.add(ref)
        seeds = (("feature", "candidate_feature_refs", False),
                 ("product", "candidate_product_refs", False),
                 ("hypothesis", "recorded_hypothesis_refs", False),
                 ("observation", "recorded_observation_refs", False),
                 ("assessment", "current_assessment_refs", True),
                 ("annotation", "current_annotation_refs", True),
                 ("material", "supplied_material_refs", False),
                 ("parse_attempt", "parse_attempt_refs", False),
                 ("collection", "collection_refs", False),
                 ("material_link", "material_link_refs", False),
                 ("read_selection", "read_selection_refs", False))
        for kind, membership, current in seeds:
            offset = 0
            while True:
                if current:
                    getter = self.store.current_annotations if kind == "annotation" else self.store.current_assessments
                    rows = getter(self.scope, limit=self.page_size, offset=offset)
                else:
                    rows = self.store.list(kind, self.scope, limit=self.page_size, offset=offset)
                for row in rows:
                    if "context_account_scope" in row:
                        # Store has already applied actual allocation/domain
                        # visibility. Its scientific/source subject may have a
                        # different physical extent; neither replaces the mask.
                        self.add(row, membership)
                        continue
                    footprint = _footprint(self.store, row)
                    intersects = any(any(max(part["start"], span["start"]) < min(part["end"], span["end"])
                        for part in self.store.scope_dimension_segments(self.scope, self.store.footprint_dimension(span)["id"]))
                        for span in footprint)
                    if intersects:
                        self.add(row, membership)
                    elif not footprint:
                        # Reusable source investigations remain inspectable;
                        # their presence supplies no original-input footprint.
                        self.add(row, membership)
                        if not self.store.roots(row["id"]) and "context_account_scope" not in row:
                            self.add(row, "source_only_record_refs")
                if len(rows) < self.page_size:
                    break
                offset += self.page_size
        # Member inventory is streamed into this disk-backed export selection.
        # It remains evidence inventory, never an input/eligible footprint.
        for collection in self.records(kind="collection"):
            if collection.get("storage_representation") == packing.REPRESENTATION:
                for (ref,) in self.store.db.execute("SELECT artifact_ref FROM material_pack_chunks WHERE parse_key=? ORDER BY chunk_index", (collection["parse_key"],)):
                    self.add(ref)
                # Explicit selections have reusable semantic references; keep
                # those actual records, while leaving unexamined native
                # members in the compact index rather than the main document.
                selected = self.store.db.execute("SELECT r.data FROM records r JOIN material_members m ON m.id=json_extract(r.data,'$.member_ref') WHERE r.record_type='reference' AND m.collection_ref=? ORDER BY r.id", (collection["id"],))
                for (data,) in selected:
                    self.add(json.loads(data), "source_only_record_refs")
                continue
            offset = 0
            while True:
                rows = self.store.db.execute("SELECT data FROM material_members WHERE collection_ref=? ORDER BY ordinal LIMIT ? OFFSET ?",
                    (collection["id"], self.page_size, offset)).fetchall()
                for (data,) in rows:
                    self.add(json.loads(data), "indexed_member_refs")
                if len(rows) < self.page_size:
                    break
                offset += self.page_size
        # Traverse just the dependencies of the current account and its scoped
        # working inventory, never runtime journals or all historical revisions.
        while True:
            rows = self.db.execute("SELECT id,data FROM nodes WHERE processed=0 ORDER BY id LIMIT ?", (self.page_size,)).fetchall()
            if not rows:
                break
            for ref, data in rows:
                record = json.loads(data)
                if record["record_type"] == "collection_member" and packing.packed(record):
                    # This member was reached through an actual selected
                    # input/reference; unexamined packed inventory stays in
                    # its portable index. Reuse the form-ownership projection.
                    for component_ref in packing.materialized_components(self.store, record).values():
                        if component_ref:
                            self.add(component_ref)
                if record["record_type"] == "source":
                    # Only provenance records bound to this selected source,
                    # using the authoritative source index. A parent's other
                    # derivatives/private histories are not reverse-traversed.
                    for kind in SOURCE_PROVENANCE_KINDS:
                        related = self.store.db.execute(
                            "SELECT data FROM records WHERE record_type=? AND json_extract(data,'$.source_ref')=? ORDER BY id",
                            (kind, ref))
                        for (native_data,) in related:
                            self.add(json.loads(native_data), "source_only_record_refs")
                for dependency in _references(record):
                    self.add(dependency)
                self.db.execute("UPDATE nodes SET processed=1 WHERE id=?", (ref,))
        for kind in ("annotation", "assessment"):
            rows = self.db.execute("SELECT id FROM nodes WHERE record_type=? ORDER BY id", (kind,))
            for (ref,) in rows:
                if self.db.execute("SELECT 1 FROM membership WHERE name=? AND id=?", (f"current_{kind}_refs", ref)).fetchone():
                    continue
                current = self.store.db.execute("SELECT 1 FROM current_revisions WHERE record_type=? AND record_ref=?", (kind, ref)).fetchone()
                name = f"referenced_{'current' if current else 'noncurrent'}_{kind}_refs"
                self.db.execute("INSERT OR IGNORE INTO membership VALUES(?,?)", (name, ref))
        self._index_gff()
        self.db.commit()

    def _index_gff(self):
        for row in self.members("current_annotation_refs", records=True):
            subject = self.store.get(row["subject_ref"])
            if subject["record_type"] == "feature":
                self.db.execute("INSERT OR IGNORE INTO gff_accounts VALUES(?,?)", (subject["id"], row["id"]))
        for feature in self.members("candidate_feature_refs", records=True):
            parent = self.store.get(feature["subject_ref"])
            reason = None
            if parent["record_type"] == "read_subject":
                reason = "read_local_coordinates_retained_in_authoritative_json"
            elif parent["record_type"] != "input":
                reason = "feature_not_directly_on_original_input"
            elif parent["molecule"] not in {"dna", "rna"}:
                reason = "original_input_not_declared_nucleotide"
            elif feature["kind"] == "CDS":
                reason = "cds_phase_not_recorded"
            elif feature["kind"] not in GFF_TYPES:
                reason = "feature_kind_not_represented_in_gff3"
            if reason:
                self.db.execute("INSERT INTO gff_exclusions VALUES(?,?)", (feature["id"], reason))
            else:
                self.db.execute("INSERT INTO membership VALUES('gff3_emitted_feature_refs',?)", (feature["id"],))

    def members(self, name, *, records=False):
        if records:
            rows = self.db.execute("SELECT n.data FROM membership m JOIN nodes n ON n.id=m.id WHERE m.name=? ORDER BY m.id", (name,))
            for (data,) in rows:
                yield json.loads(data)
        else:
            for (ref,) in self.db.execute("SELECT id FROM membership WHERE name=? ORDER BY id", (name,)):
                yield ref

    def records(self, *, kind=None, scientific=False):
        if scientific:
            rows = self.db.execute("SELECT data FROM nodes WHERE record_type NOT IN ('input','artifact') ORDER BY record_type,id")
        else:
            rows = self.db.execute("SELECT data FROM nodes WHERE record_type=? ORDER BY id", (kind,))
        for (data,) in rows:
            yield json.loads(data)

    def parse_errors(self):
        """Stream the exact feedback index of each exported parse attempt.

        These are operational representation outcomes, not scientific claims
        or independently registered evidence records. The immutable parse key
        and local error index preserve their actual authoritative identity.
        """
        for attempt in self.records(kind="parse_attempt"):
            rows = self.store.db.execute(
                "SELECT error_index,data FROM material_errors WHERE parse_key=? ORDER BY error_index",
                (attempt["parse_key"],))
            for error_index, data in rows:
                yield {"parse_ref": attempt["id"], "parse_key": attempt["parse_key"],
                       "error_index": error_index, **json.loads(data)}

    def native_material_annotations(self):
        """Stream the same normalized offset index, without reinterpreting features."""
        for attempt in self.records(kind="parse_attempt"):
            source_ref = attempt.get("native_source_ref")
            if source_ref is None:
                continue
            source = self.store.get(source_ref)
            rows = self.store.db.execute("SELECT * FROM material_annotations WHERE parse_key=? ORDER BY record_ordinal,entry_kind,entry_ordinal",
                (attempt["parse_key"],))
            for row in rows:
                yield {"parse_ref": attempt["id"], "parse_key": attempt["parse_key"],
                    "source_ref": source_ref, "artifact_ref": source["artifact_ref"],
                    "record_ordinal": row["record_ordinal"], "entry_kind": row["entry_kind"],
                    "entry_ordinal": row["entry_ordinal"], "start": row["byte_start"], "end": row["byte_end"],
                    "coordinate_system": "normalized_native_jsonl_byte_offsets_not_original_genbank",
                    "preview": json.loads(row["preview"])}

    def counts(self):
        return {"records": {kind: total for kind, total in self.db.execute("SELECT record_type,count(*) FROM nodes GROUP BY record_type ORDER BY record_type")},
                "membership": {name: self.db.execute("SELECT count(*) FROM membership WHERE name=?", (name,)).fetchone()[0] for name in MEMBERSHIPS}}

    def gff_counts(self):
        emitted = self.db.execute("SELECT count(*) FROM membership WHERE name='gff3_emitted_feature_refs'").fetchone()[0]
        excluded = self.db.execute("SELECT count(*) FROM gff_exclusions").fetchone()[0]
        segments = sum(len(row["segments"]) for row in self.members("gff3_emitted_feature_refs", records=True))
        return {"emitted_features": emitted, "emitted_rows": segments, "excluded_features": excluded,
                "exclusion_counts": {code: count for code, count in self.db.execute("SELECT code,count(*) FROM gff_exclusions GROUP BY code ORDER BY code")}}

    def exclusions(self):
        for ref, code in self.db.execute("SELECT id,code FROM gff_exclusions ORDER BY id"):
            yield {"feature_ref": ref, "code": code}


class _JsonWriter:
    def __init__(self, handle):
        self.handle, self.first = handle, True
        self.handle.write("{")

    def value(self, name, value):
        self._key(name)
        self.handle.write(canonical(value))

    def _key(self, name):
        self.handle.write(("" if self.first else ",") + json.dumps(name) + ":")
        self.first = False

    def array(self, name, rows: Iterable):
        self._key(name)
        self.handle.write("[")
        first = True
        for row in rows:
            self.handle.write(("" if first else ",") + canonical(row))
            first = False
        self.handle.write("]")

    def close(self):
        self.handle.write("}\n")


def _hash_file(path):
    digest, size = hashlib.sha256(), 0
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return {"sha256": digest.hexdigest(), "bytes": size}


def _sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _copy_artifact(store, artifact, directory):
    """Copy and validate one content-addressed object using bounded chunks."""
    digest = artifact["sha256"]
    source = store.path / "artifacts" / digest[:2] / digest
    target = directory / digest
    directory.mkdir(parents=True, exist_ok=True)
    if target.exists():
        info = _hash_file(target)
        if info != {"sha256": digest, "bytes": artifact["size"]}:
            raise ContractError("export_artifact_digest_mismatch")
        return
    temporary = None
    try:
        fd, temporary = tempfile.mkstemp(prefix=".artifact-", dir=directory)
        copied = hashlib.sha256()
        count = 0
        with os.fdopen(fd, "wb") as output, source.open("rb") as original:
            for chunk in iter(lambda: original.read(1024 * 1024), b""):
                output.write(chunk)
                copied.update(chunk)
                count += len(chunk)
            output.flush()
            os.fsync(output.fileno())
        if copied.hexdigest() != digest or count != artifact["size"]:
            raise ContractError("export_artifact_digest_mismatch")
        os.replace(temporary, target)
        _sync_directory(directory)
    finally:
        if temporary is not None and os.path.exists(temporary):
            os.unlink(temporary)


def _write_packed_indexes(selection, json_path, include_artifacts):
    """One portable immutable inventory snapshot, not a main JSON node per read."""
    directory = Path(str(json_path) + ".materials")
    for collection in selection.records(kind="collection"):
        if collection.get("storage_representation") != packing.REPRESENTATION:
            continue
        directory.mkdir(parents=True, exist_ok=True)
        destination = directory / (collection["id"] + ".sqlite3")
        with _temporary_output(destination) as temporary:
            db = sqlite3.connect(temporary)
            try:
                db.executescript("""
                    CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                    CREATE TABLE material_members(id TEXT PRIMARY KEY,parse_key TEXT NOT NULL,ordinal INTEGER NOT NULL,collection_ref TEXT,data TEXT NOT NULL,UNIQUE(parse_key,ordinal));
                    CREATE TABLE material_component_spans(member_ref TEXT NOT NULL,component TEXT NOT NULL,part INTEGER NOT NULL,chunk_index INTEGER NOT NULL,start INTEGER NOT NULL,end INTEGER NOT NULL,PRIMARY KEY(member_ref,component,part));
                    CREATE TABLE material_pack_chunks(parse_key TEXT NOT NULL,chunk_index INTEGER NOT NULL,artifact_ref TEXT NOT NULL,PRIMARY KEY(parse_key,chunk_index));
                    CREATE TABLE artifacts(id TEXT PRIMARY KEY,sha256 TEXT NOT NULL,media_type TEXT NOT NULL,size INTEGER NOT NULL);
                """)
                attempt = next(selection.store.db.execute("SELECT data FROM records WHERE record_type='parse_attempt' AND json_extract(data,'$.parse_key')=?", (collection["parse_key"],)))[0]
                attempt = json.loads(attempt)
                metadata = {"format": "gene_annotation_episode.packed_material_index", "schema_version": 1,
                    "storage_representation": packing.REPRESENTATION, "collection": collection,
                    "parse_attempt": attempt,
                    "meaning": "native_source_members_not_biological_targets_or_scientific_annotations"}
                db.executemany("INSERT INTO metadata VALUES(?,?)", ((key, canonical(value)) for key, value in metadata.items()))
                queries = (
                    ("material_members", "SELECT id,parse_key,ordinal,collection_ref,data FROM material_members WHERE collection_ref=? ORDER BY ordinal", (collection["id"],), 5),
                    ("material_component_spans", "SELECT s.member_ref,s.component,s.part,s.chunk_index,s.start,s.end FROM material_component_spans s JOIN material_members m ON m.id=s.member_ref WHERE m.collection_ref=? ORDER BY m.ordinal,s.component,s.part", (collection["id"],), 6),
                    ("material_pack_chunks", "SELECT parse_key,chunk_index,artifact_ref FROM material_pack_chunks WHERE parse_key=? ORDER BY chunk_index", (collection["parse_key"],), 3),
                    ("artifacts", "SELECT DISTINCT a.id,a.sha256,a.media_type,a.size FROM artifacts a JOIN material_pack_chunks c ON c.artifact_ref=a.id WHERE c.parse_key=? ORDER BY a.id", (collection["parse_key"],), 4),
                )
                for table, query, parameters, width in queries:
                    rows = selection.store.db.execute(query, parameters)
                    while batch := rows.fetchmany(selection.page_size):
                        db.executemany("INSERT INTO " + table + " VALUES(" + ",".join("?" for _ in range(width)) + ")", (tuple(row) for row in batch))
                db.commit()
                chunk_count = db.execute("SELECT count(*) FROM material_pack_chunks").fetchone()[0]
            finally:
                db.close()
            descriptor = {"format": metadata["format"], "schema_version": 1,
                "storage_representation": packing.REPRESENTATION,
                "parse_ref": attempt["id"], "parse_key": collection["parse_key"],
                "collection_ref": collection["id"], "member_count": collection["member_count"],
                "relative_path": (Path(directory.name) / destination.name).as_posix(),
                **_hash_file(temporary), "chunk_count": chunk_count, "content_included": include_artifacts}
            with temporary.open("rb") as handle:
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
            _sync_directory(directory)
            selection.packed_indexes.append(descriptor)


def _write_library_indexes(selection, json_path):
    """Portable fixed-subset index; full original membership stays native-indexed."""
    targets = [row for row in selection.records(kind="input") if libraries.is_library(row)]
    if not targets:
        return
    directory = Path(str(json_path) + ".materials")
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / "read_libraries.sqlite3"
    with _temporary_output(destination) as temporary:
        db = sqlite3.connect(temporary)
        try:
            db.executescript("""
                CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                CREATE TABLE inputs(id TEXT PRIMARY KEY,data TEXT NOT NULL);
                CREATE TABLE selections(id TEXT PRIMARY KEY,data TEXT NOT NULL);
                CREATE TABLE library_selection_members(selection_ref TEXT NOT NULL,read_ref TEXT NOT NULL,PRIMARY KEY(selection_ref,read_ref));
            """)
            metadata = {"format": "gene_annotation_episode.read_library_index", "schema_version": 1,
                "binding_version": libraries.VERSION,
                "read_subject_identity": "read_subject_<24hex input identity><24hex original member identity>",
                "original_membership": "exact_collection_refs_in_portable_native_material_indexes",
                "meaning": "fixed_observed_material_measure_not_unique_genes_or_genome_completeness"}
            db.executemany("INSERT INTO metadata VALUES(?,?)", ((key, canonical(value)) for key, value in metadata.items()))
            db.executemany("INSERT INTO inputs VALUES(?,?)", ((row["id"], canonical(row)) for row in targets))
            for row in selection.records(kind="read_selection"):
                db.execute("INSERT INTO selections VALUES(?,?)", (row["id"], canonical(row)))
                cursor = selection.store.db.execute("SELECT selection_ref,read_ref FROM library_selection_members WHERE selection_ref=? ORDER BY read_ref", (row["id"],))
                while batch := cursor.fetchmany(selection.page_size):
                    db.executemany("INSERT INTO library_selection_members VALUES(?,?)", (tuple(value) for value in batch))
            db.commit()
            count = db.execute("SELECT count(*) FROM library_selection_members").fetchone()[0]
        finally:
            db.close()
        descriptor = {"format": metadata["format"], "schema_version": 1, "binding_version": libraries.VERSION,
            "relative_path": (Path(directory.name) / destination.name).as_posix(),
            **_hash_file(temporary), "library_count": len(targets), "selected_member_rows": count}
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        _sync_directory(directory)
        selection.library_indexes.append(descriptor)


def _write_json(selection, path, *, credit, bundle_directory, gff_companion):
    with Path(path).open("w", encoding="utf-8", newline="\n") as handle:
        writer = _JsonWriter(handle)
        writer.value("format", FORMAT)
        writer.value("schema_version", SCHEMA_VERSION)
        writer.value("software_version", __version__)
        writer.value("coordinate_system", "zero_based_half_open")
        writer.value("sequence_mapping_meaning", "ordered_physical_source_subject_path_distinct_from_original_input_credit_footprint_and_full_feature_span")
        writer.value("problem", selection.problem)
        writer.value("scope", selection.scope)
        writer.value("eligible_footprint", selection.eligible)
        writer.value("eligible_geometry", selection.eligible_geometry)
        writer.value("eligible_geometry_meaning", "fixed_original_member_local_position_mass_without_linear_library_coordinates")
        writer.array("inputs", selection.records(kind="input"))
        writer._key("membership")
        handle.write("{")
        for index, name in enumerate(MEMBERSHIPS):
            if index:
                handle.write(",")
            handle.write(json.dumps(name) + ":[")
            for position, ref in enumerate(selection.members(name)):
                handle.write(("," if position else "") + json.dumps(ref))
            handle.write("]")
        handle.write("}")
        writer.array("records", selection.records(scientific=True))
        writer.array("parse_errors", selection.parse_errors())
        writer.array("native_material_annotations", selection.native_material_annotations())
        writer.array("packed_material_indexes", selection.packed_indexes)
        writer.array("read_library_indexes", selection.library_indexes)
        def artifact_metadata():
            for artifact in selection.records(kind="artifact"):
                row = dict(artifact)
                row["content_included"] = bundle_directory is not None
                row["relative_path"] = (Path(bundle_directory.name) / artifact["sha256"]).as_posix() if bundle_directory is not None else None
                yield row
        writer.array("artifacts", artifact_metadata())
        writer.value("counts", selection.counts())
        writer.value("credit_projection", credit)
        writer.value("credit_projection_meaning", "annotation_scoring_unavailable_not_zero" if credit is not None else None)
        writer.value("limitations", ["raw_artifact_content_external_to_json", "uninterpreted_candidates_are_not_selected_annotations"])
        if gff_companion:
            writer._key("gff3_projection")
            handle.write("{")
            handle.write('"counts":' + canonical(selection.gff_counts()) + ',"emitted_feature_refs":[')
            for index, ref in enumerate(selection.members("gff3_emitted_feature_refs")):
                handle.write(("," if index else "") + json.dumps(ref))
            handle.write('],"excluded_features":[')
            for index, row in enumerate(selection.exclusions()):
                handle.write(("," if index else "") + canonical(row))
            handle.write("]}")
        writer.close()
        handle.flush()
        os.fsync(handle.fileno())


def _escape(value):
    # GFF3 attribute escaping; spaces and other nonreserved printable characters
    # remain literal. '%' is encoded before other reserved delimiters.
    result = []
    for char in str(value):
        if char in "%;=&,\t\r\n" or ord(char) < 32 or ord(char) == 127:
            result.extend("%%%02X" % byte for byte in char.encode("utf-8"))
        else:
            result.append(char)
    return "".join(result)


def _write_gff(selection, path, json_path, json_digest):
    with Path(path).open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("##gff-version 3\n")
        handle.write("# authoritative_json=" + quote(json_path.name, safe="._-") + "\n")
        handle.write("# authoritative_json_sha256=" + json_digest + "\n")
        handle.write("# candidate features; interpretation, alternatives and exclusions are in the companion JSON\n")
        for target in selection.records(kind="input"):
            if target["id"] in selection.scope["subject_refs"] and not libraries.is_library(target) and target["molecule"] in {"dna", "rna"}:
                handle.write(f"##sequence-region {target['id']} 1 {target['length']}\n")
        for feature in selection.members("gff3_emitted_feature_refs", records=True):
            parent = selection.store.get(feature["subject_ref"])
            account_refs = [row[0] for row in selection.db.execute("SELECT annotation_ref FROM gff_accounts WHERE feature_ref=? ORDER BY annotation_ref", (feature["id"],))]
            accounts = [selection.store.get(ref) for ref in account_refs]
            attrs = {"ID": [feature["id"]], "annotation_kind": [feature["kind"]],
                     "input_name": [parent["name"]], "input_molecule": [parent["molecule"]],
                     "origin": [feature["origin"]], "interpretation_status": ["current_account_subject" if accounts else "uninterpreted_candidate"]}
            if accounts:
                attrs["current_annotation_refs"] = account_refs
                attrs["account_resolution"] = sorted({row["resolution"] for row in accounts})
                attrs["coherent_set_refs"] = [group["id"] for row in accounts for group in row["coherent_sets"]]
                attrs["interpretation_dispositions"] = sorted({item["disposition"] for row in accounts for group in row["coherent_sets"] for item in group["interpretations"]})
                attrs["alternative_hypothesis_refs"] = [ref for row in accounts for ref in row["alternative_refs"]]
            for index, segment in enumerate(feature["segments"]):
                segment_attrs = {**attrs, "segment_index": [index], "segment_count": [len(feature["segments"])]}
                attributes = ";".join(key + "=" + ",".join(_escape(v) for v in values) for key, values in segment_attrs.items() if values)
                handle.write("\t".join((parent["id"], "gene_annotation_episode", GFF_TYPES[feature["kind"]],
                    str(segment["start"] + 1), str(segment["end"]), ".", feature["strand"], ".", attributes)) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


@contextmanager
def _temporary_output(path):
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    os.close(fd)
    try:
        yield Path(temporary)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def export_annotation(store, path: str | Path, *, format="json", scope=None,
                      include_credit=False, credit_policy=None,
                      include_artifacts=False, page_size=128) -> dict[str, Any]:
    """Write one current-state snapshot without changing scientific state.

    JSON is complete with respect to the exported inventory/reference closure.
    Source/sequence bytes are represented by content hashes by default; opt in
    to a portable sibling artifact directory. GFF3 always has an authoritative
    ``<path>.annotation.json`` companion. Unsupported rows remain there with
    explicit exclusion codes. The old categorical credit projection is retired.
    A requested score is explicitly unavailable until a numerical component
    scorer is bound; this exporter never substitutes a zero or a new policy.
    """
    if format not in {"json", "gff3"}:
        raise ContractError("unsupported_export_format")
    if type(page_size) is not int or page_size < 1:
        raise ContractError("invalid_export_page_size")
    if type(include_credit) is not bool or type(include_artifacts) is not bool:
        raise ContractError("invalid_export_option")
    if credit_policy is not None:
        raise ContractError("categorical_annotation_policy_retired_supply_explicit_numeric_scorer")
    path = Path(path).resolve()
    authoritative = {store.path / name for name in ("state.sqlite3", "state.sqlite3-wal", "state.sqlite3-shm")}
    if path in authoritative or path.is_relative_to(store.path / "artifacts"):
        raise ContractError("export_destination_is_authoritative_storage")
    path.parent.mkdir(parents=True, exist_ok=True)
    json_path = path if format == "json" else Path(str(path) + ".annotation.json")
    bundle = Path(str(json_path) + ".artifacts") if include_artifacts else None
    with store.read_snapshot(), tempfile.TemporaryDirectory(prefix=".annotation-export-", dir=path.parent) as temporary:
        selection = _Selection(store, Path(temporary) / "selection.sqlite3", store.validate_scope(scope), page_size)
        try:
            _write_packed_indexes(selection, json_path, include_artifacts)
            _write_library_indexes(selection, json_path)
            credit = None
            if include_credit:
                from .credit import unavailable_annotation_score
                credit = unavailable_annotation_score()
            if bundle is not None:
                for artifact in selection.records(kind="artifact"):
                    _copy_artifact(store, artifact, bundle)
            with _temporary_output(json_path) as json_temporary:
                _write_json(selection, json_temporary, credit=credit, bundle_directory=bundle,
                            gff_companion=format == "gff3")
                json_info = {"path": str(json_path), **_hash_file(json_temporary)}
                result = {"status": "completed", "format": format, "scope": selection.scope,
                          "counts": selection.counts(), "json": json_info,
                          "artifact_directory": str(bundle) if bundle is not None else None}
                if format == "gff3":
                    with _temporary_output(path) as gff_temporary:
                        _write_gff(selection, gff_temporary, json_path, json_info["sha256"])
                        result["gff3"] = {"path": str(path), **_hash_file(gff_temporary), **selection.gff_counts()}
                        os.replace(json_temporary, json_path)
                        os.replace(gff_temporary, path)
                else:
                    os.replace(json_temporary, json_path)
                _sync_directory(path.parent)
                return result
        finally:
            selection.close()
