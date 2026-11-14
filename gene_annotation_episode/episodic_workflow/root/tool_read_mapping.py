"""Original substantive ordinary-tool methods: tool_read_mapping."""
from __future__ import annotations
import json
import os
import tempfile
from pathlib import Path
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.episodic_workflow.root.library import read_mapping as mapper
from gene_annotation_episode.materials import artifact_file
from .tool_values import number
from .tool_values import ref
from .tool_values import measurements

class ToolReadMapping:
    async def _native_mapping_async(self, args, scope):
        import tempfile
        selection = self.store._require(args["query_selection_ref"], {"read_selection"})
        selected_scope = {"subject_refs": [selection["library_ref"]], "read_selection_refs": [selection["id"]]}
        self.store.validate_scope(selected_scope, parent_scope=scope)
        mapper.settings(args["preset"], args.get("parameters"))
        if self.store.db.in_transaction:
            raise ContractError("native_mapping_requires_no_active_store_transaction")
        directory = Path(tempfile.mkdtemp(prefix=".native-read-mapping-", dir=self.store.path))
        self._mapping_directories.get().append(directory)
        source_refs = set()
        import sqlite3
        with sqlite3.connect(directory/"operands.sqlite") as index:
            index.execute("CREATE TABLE operands(role TEXT,subject_ref TEXT,length INTEGER,PRIMARY KEY(role,subject_ref))")
            for role, filename, subjects in (
                ("query", "queries.fasta", (row[0] for row in self.store.db.execute(
                    "SELECT read_ref FROM library_selection_members WHERE selection_ref=? ORDER BY read_ref", (selection["id"],)))),
                ("reference", "references.fasta", iter(args["reference_refs"]))):
                with (directory/filename).open("w", encoding="ascii") as handle:
                    for reference in subjects:
                        row = self._check_sequence_operand(reference, scope) if role == "query" else self.store.get(reference)
                        if row["record_type"] not in {"input", "read_subject", "reference", "feature", "product"}:
                            raise ContractError("sequence_operand_required")
                        if self.store.subject_molecule(reference) == "protein":
                            raise ContractError("native_genomic_mapping_requires_nucleotide_operand",
                                detail={"role": role, "subject_ref": reference})
                        sequence = self._sequence(reference, molecule_model="dna")
                        if not sequence or not set(sequence.upper()) <= set("ACGTRYSWKMBDHVN"):
                            raise ContractError("native_mapping_requires_DNA_processing_alphabet",
                                detail={"role": role, "subject_ref": reference,
                                    "input_classification_changed": False})
                        handle.write(">" + reference + "\n" + sequence + "\n")
                        index.execute("INSERT INTO operands VALUES(?,?,?)", (role, reference, len(sequence)))
                        if row.get("source_ref"):
                            source_refs.add(row["source_ref"])
            count = index.execute("SELECT count(*) FROM operands WHERE role='query'").fetchone()[0]
        if count != selection["member_count"]:
            raise ContractError("selected_read_index_membership_mismatch")
        metadata = {"query_selection_ref": selection["id"], "library_ref": selection["library_ref"],
            "query_count": count, "selection_membership_sha256": selection["membership_sha256"],
            "reference_refs": args["reference_refs"], "source_refs": sorted(source_refs),
            "staged_header_meaning": "actual_stable_subject_ids_not_native_title_or_biological_identity",
            "query_fasta_sha256": mapper.file_digest(directory/"queries.fasta"),
            "reference_fasta_sha256": mapper.file_digest(directory/"references.fasta")}
        return await mapper.run_mapping(directory, configuration=dict(self.minimap2_configuration),
            preset=args["preset"], parameters=args.get("parameters"), input_metadata=metadata,
            job_limits=self.local_job_policy.to_dict())

    def _retain_mapping_grading(self, native):
        """Stream numerical rows beside one already executed mapping result.

        The temporary index groups exact query identities even when a native
        multipart index reports the same query in nonadjacent blocks. It owns
        no scientific decisions or durable workflow state.
        """
        import sqlite3
        from gene_annotation_episode.materials import artifact_file
        from gene_annotation_episode.minimap2_grader import grade_minimap2_placement, calculate_minimap2_query_scores

        row_path = native.path('grading-placements.jsonl')
        query_path = native.path('grading-queries.jsonl')
        row_count = 0
        complete = (native.metadata.get('phase') == 'native_mapping'
            and native.metadata.get('returncode') == 0
            and not native.metadata.get('resource_failure')
            and native.path('mappings.paf').is_file()
            and native.path('placements.jsonl').is_file()
            and (not native.path('projection-errors.jsonl').is_file()
                 or native.path('projection-errors.jsonl').stat().st_size == 0))
        with sqlite3.connect(native.path('operands.sqlite')) as operands, \
                sqlite3.connect(native.path('grading-index.sqlite')) as index:
            index.execute('CREATE TABLE grades(query_name TEXT, line_number INTEGER, sheet TEXT)')
            index.execute('CREATE INDEX grades_by_query ON grades(query_name,line_number)')
            with row_path.open('w', encoding='utf-8') as output:
                if native.path('placements.jsonl').is_file():
                    with native.path('placements.jsonl').open(encoding='utf-8') as placements:
                        for line in placements:
                            row = json.loads(line)
                            metadata = {}
                            for role in ('query', 'reference'):
                                name = row[role + '_name']
                                actual = operands.execute('SELECT length FROM operands WHERE role=? AND subject_ref=?',
                                    (role, name)).fetchone()
                                if actual is None:
                                    raise ContractError('mapping_grading_operand_missing')
                                metadata[role] = {'name': name, 'length': actual[0]}
                            grading = self._grade_supplied_result(grade_minimap2_placement,
                                {**row, 'native_parameters': native.metadata['settings']},
                                preset=native.metadata['settings']['preset'],
                                native_version=native.metadata.get('native_version'),
                                query_metadata=metadata['query'], reference_metadata=metadata['reference'])
                            locator = {key: row[key] for key in ('line_number', 'row_start', 'row_end')}
                            output.write(canonical({**locator, 'query_name': row['query_name'],
                                'reference_name': row['reference_name'], 'grading': grading}) + '\n')
                            index.execute('INSERT INTO grades VALUES(?,?,?)',
                                (row['query_name'], row['line_number'], canonical(grading.get('sheet'))))
                            row_count += 1
                output.flush()
                os.fsync(output.fileno())
            with query_path.open('w', encoding='utf-8') as output:
                for name, length in operands.execute("SELECT subject_ref,length FROM operands WHERE role='query' ORDER BY subject_ref"):
                    query = {'name': name, 'length': length}
                    sheets = (json.loads(row[0]) for row in index.execute(
                        'SELECT sheet FROM grades WHERE query_name=? ORDER BY line_number', (name,)))
                    scores = self._grade_supplied_result(calculate_minimap2_query_scores, sheets,
                        query_metadata=query, output_complete=complete)
                    output.write(canonical({'query_metadata': query, 'output_complete': complete,
                        'scores': scores}) + '\n')
                output.flush()
                os.fsync(output.fileno())
        rows_ref = artifact_file(self.store, row_path, 'application/x-ndjson')
        queries_ref = artifact_file(self.store, query_path, 'application/x-ndjson')
        return {'schema': 'minimap2_grading_collection_v1', 'placement_count': row_count,
            'rows_artifact_ref': rows_ref, 'query_scores_artifact_ref': queries_ref,
            'output_complete': complete,
            'row_format': 'native_row_locator_and_grading_jsonlines'}, [rows_ref, queries_ref]

    def _publish_mapping(self, args, native):
        batch = self._begin_publication_batch(failures=True)
        from gene_annotation_episode.materials import artifact_file
        artifacts = {}
        for name in ("queries.fasta", "references.fasta", "mappings.paf", "mapping.stderr", "version.stdout",
                "version.stderr", "help.stdout", "help.stderr", "index.stdout", "index.stderr", "projection-errors.jsonl"):
            if native.path(name).is_file():
                artifacts[name] = artifact_file(self.store, native.path(name),
                    "text/x-fasta" if name.endswith(".fasta") else "text/plain")
        grading, grading_artifacts = self._retain_mapping_grading(native)
        source = self._source("minimap2.mapping", {**native.metadata, "artifacts": artifacts},
            software_version=native.metadata["native_version"],
            parent_source_refs=native.metadata["input_metadata"]["source_refs"],
            stdout_ref=artifacts.get("mappings.paf", artifacts.get("index.stdout")),
            stderr_ref=artifacts.get("mapping.stderr", artifacts.get("index.stderr")),
            auxiliary_artifact_refs=list(dict.fromkeys([*artifacts.values(), *grading_artifacts])),
            operand_refs=args["reference_refs"], query_selection_ref=args["query_selection_ref"],
            tool_grading=grading)
        preview, refs, total = [], [source["id"]], 0
        self._batch_observations(batch, source["id"])
        if native.path("placements.jsonl").is_file():
            with native.path("placements.jsonl").open() as handle, \
                    native.path('grading-placements.jsonl').open() as graded:
                for line, graded_line in zip(handle, graded, strict=True):
                    row = json.loads(line)
                    graded_row = json.loads(graded_line)
                    if any(row[key] != graded_row[key] for key in (
                            'line_number', 'row_start', 'row_end', 'query_name', 'reference_name')):
                        raise ContractError('mapping_grading_row_mismatch')
                    scores = graded_row['grading'].get('scores') or {}
                    values = measurements(reference_ref=ref(row["reference_name"]),
                        query_start=number(row["query_interval"][0]), query_end=number(row["query_interval"][1]))
                    values += measurements(**{alias: number(scores[component])
                        for alias, component in (
                            ('query_coverage', 'query_span_coverage'),
                            ('target_coverage', 'reference_span_coverage'),
                            ('identity_fraction', 'native_alignment_identity'))
                        if type(scores.get(component)) in (int, float)})
                    values += self._grading_values(scores, (
                        'query_length', 'reference_length', 'query_span', 'reference_span',
                        'native_matching_bases', 'native_block_length', 'native_alignment_identity',
                        'paired_positions', 'inserted_bases', 'deleted_bases', 'query_gap_columns',
                        'reference_gap_columns', 'reference_skipped_bases', 'alignment_columns',
                        'cs_equal_positions', 'cs_substituted_positions', 'native_ambiguity_count',
                        'query_span_coverage', 'reference_span_coverage', 'query_paired_coverage',
                        'reference_paired_coverage', 'query_aligned_coverage',
                        'reference_aligned_coverage', 'mapping_quality'))
                    score = next((item for item in row["tags"] if item["name"] == "AS" and item["type"] == "i"), None)
                    if score:
                        values += measurements(alignment_score=number(int(score["value"])))
                    observation = self._put("observation", {"kind": "alignment", "subject_refs": [row["query_name"]],
                        "source_subject_refs": [row["reference_name"]], "source_ref": source["id"],
                        "measurements": values, "dependencies": list(dict.fromkeys(
                            [row["query_name"], row["reference_name"], args["query_selection_ref"]])),
                        "anchor": None, "operand_intervals": [{"role": role, "subject_ref": subject, "start": interval[0],
                            "end": interval[1], "unit": self.store.subject_unit(subject), "model_unit": "nt"}
                            for role, subject, interval in (("query", row["query_name"], row["query_interval"]),
                                ("reference", row["reference_name"], row["reference_interval"]))],
                        "native_minimap2": {key: row[key] for key in ("line_number", "row_start", "row_end", "strand",
                            "mapping_quality", "native_alignment_type")}}, origin="tool")
                    total += 1
                    batch["published_rows_total"] = total
                    refs.append(observation["id"])
                    if len(preview) < 12:
                        preview.append({"observation_ref": observation["id"], **{key: value for key, value in row.items()
                            if key not in {"tags", "cigar", "cs"}}})
        errors, error_count = [], 0
        error_source_ref = None
        if native.path("projection-errors.jsonl").is_file():
            with native.path("projection-errors.jsonl").open() as handle:
                for line in handle:
                    error_count += 1
                    batch["failure_rows_total"] = error_count
                    if len(errors) < 12:
                        errors.append(json.loads(line))
            if error_count:
                error_source = self._put("source", {"provider": "minimap2.projection_errors", "accession": None, "uri": None,
                    "artifact_ref": artifacts["projection-errors.jsonl"], "text_ref": artifacts["projection-errors.jsonl"],
                    "request_ref": None, "version": mapper.VERSION, "retrieved_at": native.metadata["finished_at"],
                    "parent_source_refs": [source["id"]]}, origin="tool")
                error_source_ref = error_source["id"]
                refs.append(error_source_ref)
        # This is custody of the executed search and its exact selection, not
        # a placement/absence claim about a library or organism. It anchors
        # zero-result native source/operand closure using the existing zero-
        # credit source_content meaning and creates no additional own action.
        summary = None
        if not native.metadata.get("resource_failure"):
            summary = self._observation("source_content", [native.metadata["input_metadata"]["library_ref"]], source,
                measurements(count=number(total)), references=args["reference_refs"],
                dependencies=[args["query_selection_ref"], *args["reference_refs"]], operand_intervals=[])
            refs.append(summary["id"])
        return {"source_ref": source["id"], "query_selection_ref": args["query_selection_ref"],
            "query_count": native.metadata["input_metadata"]["query_count"], "reference_refs": args["reference_refs"],
            "reported_placement_count": total, "records": preview, "preview_limit": 12,
            "search_result_observation_ref": summary["id"] if summary else None,
            "native_result_type": "minimap2_placements_v1",
            "record_refs_are_preview": False,
            "all_observations_query": {"kind": "observation", "references": [source["id"]], "offset": 0, "limit": 12},
            "query_result_kinds": ["alignment", "source_content"],
            "projection_error_count": error_count, "projection_errors": errors, "error_source_ref": error_source_ref,
            **({"resource_failure": native.metadata["resource_failure"]} if native.metadata.get("resource_failure") else {}),
            "native_returncode": native.metadata["returncode"], "native_phase": native.metadata["phase"],
            "native_settings": native.metadata["settings"], "resource_binding": native.metadata["configuration"],
            "index": {key: native.metadata["index"][key] for key in ("cache_key", "reused", "index_sha256")}
                if "index" in native.metadata else None,
            "target_annotation": "not_performed", "result_meaning":
                "partial_native_reported_placements_from_resource_limited_search_not_biological_absence"
                    if native.metadata.get("resource_failure") else "native_reported_placements_under_recorded_search_not_biological_absence"}, refs

