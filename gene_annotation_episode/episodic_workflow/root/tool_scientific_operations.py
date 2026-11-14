"""Original substantive ordinary-tool methods: tool_scientific_operations."""
from __future__ import annotations
from datetime import datetime
from datetime import timezone
from importlib.metadata import version
import inspect
import json
import os
import tempfile
from pathlib import Path
from typing import Any
from gene_annotation_episode.acquisition import RfamModelSnapshots
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.episodic_workflow.root.library.sequence_ops import inspect_sequence
from gene_annotation_episode.episodic_workflow.root.library.sequence_ops import translate
from gene_annotation_episode.episodic_workflow.root.library.sequence_ops import translation_codes
from gene_annotation_episode.episodic_workflow.root.library.sequence_mapping import VERSION as MAPPING_VERSION
from gene_annotation_episode.episodic_workflow.root.library.sequence_mapping import extract_path
from gene_annotation_episode.episodic_workflow.root.library.sequence_mapping import translation_mapping
from gene_annotation_episode.episodic_workflow.root.library.sequence_views import VERSION as VIEW_VERSION
from gene_annotation_episode.episodic_workflow.root.library.sequence_views import view_sequence
from .library.comparative_ops import genbank_neighborhood
from .library.comparative_ops import VERSION as NEIGHBORHOOD_VERSION
from gene_annotation_episode import library_targets as libraries
from gene_annotation_episode.episodic_workflow.root.library import read_mapping as mapper
from gene_annotation_episode.materials import artifact_file
from gene_annotation_episode.materials import source_window
from gene_annotation_episode.source_locations import locate as locate_source
from gene_annotation_episode.document_tools import DocumentOutput
from gene_annotation_episode.literature_assets import PmcFiles
from .library.rna_evidence import NativeSearch
from gene_annotation_episode.image_evidence import prepare_image
from .tool_values import number
from .tool_values import enum
from .tool_values import ref
from .tool_values import measurements
from .tool_values import SequenceWork

class ToolScientificOperations:
    def _perform(self, name: str, args: dict, scope: dict | None, snapshot: Any) -> tuple[dict, list[str]]:
        from gene_annotation_episode.experimental_database_acquisition import OPERATIONS as EXPERIMENT_DATABASE_TOOLS, publish as publish_experimental_database
        if name in EXPERIMENT_DATABASE_TOOLS:
            return publish_experimental_database(self, name, args, snapshot)
        if name == 'source.experimental.records':
            from gene_annotation_episode.experimental_database_records import read_records
            return read_records(self, args, scope, self._permitted_record_refs.get())
        if name == 'public.literature.sequence_identity':
            from gene_annotation_episode.literature_sequence_discovery import publish_identity
            return publish_identity(self, args, scope, snapshot)
        if name == 'source.sequence.references':
            from gene_annotation_episode.literature_sequence_discovery import references
            return references(self, args, scope, self._permitted_record_refs.get())
        if name == 'source.sequence.scan':
            from gene_annotation_episode.source_sequences import scan
            return scan(self, args, scope, self._permitted_record_refs.get())
        from .library.flux_balance_tools import FBA_TOOL
        from gene_annotation_episode.molecular_provider_acquisition import OPERATIONS as MOLECULAR_PROVIDER_OPERATIONS
        from gene_annotation_episode.episodic_workflow.root.library.itc_tools import ITC_TOOL, publish_itc_work
        from gene_annotation_episode.episodic_workflow.root.library.liftover_tools import LIFTOVER_TOOL, publish_liftover_work
        from gene_annotation_episode.episodic_workflow.root.library.circular_dichroism_contracts import CD_TOOL
        from gene_annotation_episode.episodic_workflow.root.library.circular_dichroism_tools import publish_circular_dichroism_work
        if name == "public.alphafold.prediction":
            from .library.alphafold_acquisition_host import publish_alphafold_prediction_receipt
            return publish_alphafold_prediction_receipt(self, args, snapshot)
        if name == "public.emdb.entry":
            from gene_annotation_episode.emdb_acquisition import publish_emdb_entry_receipt
            return publish_emdb_entry_receipt(self, args, snapshot)
        if name in {"public.rcsb.entry", "public.rcsb.file"}:
            from gene_annotation_episode.rcsb_acquisition import publish_rcsb_request
            return publish_rcsb_request(self, name, args, snapshot)
        if name in MOLECULAR_PROVIDER_OPERATIONS:
            from gene_annotation_episode.molecular_provider_acquisition import publish_molecular_provider_request
            return publish_molecular_provider_request(self, name, args, snapshot)
        if name in {"public.eva.request", "public.gnomad.request"}:
            from gene_annotation_episode.variant_provider_acquisition import publish_provider_request as publish_variant_provider_request
            return publish_variant_provider_request(self, name, args, snapshot)
        if name == "public.ucsc.request":
            from gene_annotation_episode.ucsc_acquisition import publish_ucsc_request
            return publish_ucsc_request(self, args, snapshot)
        if name == "public.ncbi.entrez":
            from gene_annotation_episode.ncbi_entrez_tools import publish_ncbi_entrez_request
            return publish_ncbi_entrez_request(self, args, snapshot)
        if name == "public.ncbi.geo":
            from gene_annotation_episode.geo_tools import publish_geo_request
            return publish_geo_request(self, args, snapshot)
        if name == "public.ncbi.sra.file":
            from gene_annotation_episode.ncbi_sra_acquisition_host import publish_sra_file_request
            return publish_sra_file_request(self, args, snapshot['snapshot'], prepared=snapshot['prepared'])
        if name == "public.jaspar":
            from gene_annotation_episode.jaspar_tools import publish_jaspar_request
            return publish_jaspar_request(self, args, snapshot)
        if name == "public.screen":
            from gene_annotation_episode.screen_tools import publish_screen_request
            return publish_screen_request(self, args, snapshot)
        if name == "public.encode":
            from .library.encode_tools import publish_encode_request
            return publish_encode_request(self, args, snapshot['snapshot'], selection=snapshot['selection'])
        if name == 'public.ensembl.request':
            from gene_annotation_episode.ensembl_acquisition_host import publish_ensembl_request
            return publish_ensembl_request(self, args, snapshot['snapshot'], prepared=snapshot['prepared'])
        if name == 'public.alphafold.file':
            from .library.alphafold_acquisition_host import publish_alphafold_file_receipt
            return publish_alphafold_file_receipt(self, args, snapshot['snapshot'], selection=snapshot['selection'])
        if name == FBA_TOOL:
            return self.ordinary_flux_balance_backend.publish(snapshot)
        if name == ITC_TOOL:
            return publish_itc_work(self, args, snapshot)
        if name == LIFTOVER_TOOL:
            return publish_liftover_work(self, args, snapshot)
        if name == CD_TOOL:
            return publish_circular_dichroism_work(self, args, snapshot)
        if name == 'execution.estimate':
            return snapshot, []
        if name == "sequence.align":
            return self._align_one(args, scope, snapshot)
        if name == "reads.align":
            return self._publish_read_alignments(args, scope, snapshot)
        if name == "genes.predict":
            return self._derive(name, args, scope, snapshot)
        if isinstance(snapshot, mapper.NativeMapping):
            return self._publish_mapping(args, snapshot)
        if isinstance(snapshot, DocumentOutput):
            return self._publish_document(name, args, snapshot)
        if isinstance(snapshot, PmcFiles):
            return self._publish_pmc_files(args, snapshot)
        if name == "public.pmc.versions":
            return self._publish_pmc_versions(args, snapshot)
        if name == "public.pmc.asset":
            return self._publish_pmc_asset(args, snapshot)
        if name == "material.from_source":
            material = self.store.register_material(source_ref=args["source_ref"], format=args.get("format", "auto"), use="evidence")
            self._written.append(material["id"])
            return {"material_ref": material["id"], "source_ref": material["source_ref"],
                "parse_with": {"material_ref": material["id"]}, "target_binding_changed": False}, [material["id"]]
        if name == "material.parse":
            attempt = self.store.parse_material(**args)
            refs = [attempt["source_ref"], attempt["id"]]
            if attempt.get("native_source_ref") is not None:
                refs.append(attempt["native_source_ref"])
            if attempt["collection_ref"] is not None:
                refs.append(attempt["collection_ref"])
            self._written.extend(refs)
            return {"parse_attempt": attempt}, refs
        if name == "library.members":
            return libraries.member_page(self.store, scope=scope, **args), []
        if name == "library.select":
            selected = libraries.select(self.store, scope=scope, **args)
            self._written.append(selected["id"])
            return {"selection": selected, "scope": {"subject_refs": [selected["library_ref"]],
                "read_selection_refs": [selected["id"]]}}, [selected["id"]]
        if name == "library.read":
            subject = self.store._require(args["subject_ref"], {"read_subject"})
            offset, limit = args.get("offset", 0), args.get("limit", 12000)
            if type(offset) is not int or not 0 <= offset <= subject["length"] or type(limit) is not int or limit < 1:
                raise ContractError("invalid_member_window")
            end = min(offset + limit, subject["length"])
            if offset < end:
                footprint = self.store.map_segments(subject["id"], [{"start": offset, "end": end}])
                self._check_sequence_operand(subject["id"], scope, footprint=footprint)
            elif not self.store.scope_dimension_segments(scope, subject["id"]):
                # The normal EOF window contains no sequence positions. It is
                # readable only for an actually assigned original member.
                raise ContractError("subject_outside_assigned_scope")
            body = self.store.material_member(subject["member_ref"], offset=offset, limit=limit)
            return {"subject_ref": subject["id"], "library_ref": subject["library_ref"], **body}, []
        if name == "reads.inspect":
            return self._inspect_reads(args, scope)
        if name == "material.annotations":
            return self.store.material_annotations(**args), []
        if name == "material.read":
            return self.store.material_read(**args), []
        if name == "material.members":
            return self.store.material_members(**args), []
        if name == "material.errors":
            return self.store.material_errors(**args), []
        if name == "material.member":
            body = self.store.material_member(**args)
            reference = self.store.material_reference(args["member_ref"])
            refs = [reference["id"], *reference["context_refs"]]
            self._written.extend(refs)
            return {**body, "reference_ref": reference["id"]}, refs
        if name == "material.header":
            return self.store.material_header(**args), []
        if isinstance(snapshot, NativeSearch):
            return self._publish_cmsearch(args, snapshot)
        if isinstance(snapshot, RfamModelSnapshots):
            return self._import_rfam(args, snapshot)
        if name == "public.search.jobs":
            permitted = set(self.store.validate_scope(scope)["subject_refs"])
            limit, offset = args.get("limit", 100), args.get("offset", 0)
            page = self.remote_searches.jobs(limit=limit+1, offset=offset, active_only=args.get("active_only", True))
            jobs = [job for job in page[:limit]
                    if set(self.store.roots(job["request"]["subject_ref"])) <= permitted]
            return {"jobs": jobs, "offset": offset, "next_offset": offset+limit if len(page)>limit else None}, []
        if snapshot is not None:
            return self._import(name, args, snapshot)
        if name == "state.query":
            def received(row):
                if row.get('record_type') != 'native_execution':
                    return row
                from .native_timing_information import read_measurement
                return {**row, 'measurement': read_measurement(self.store, row['id']).as_record()}
            if "refs" in args:
                conflicting_fields = sorted(set(args) - {"refs"})
                if conflicting_fields:
                    raise ContractError("exact_refs_cannot_be_combined_with_page_selectors",
                        detail={"selection_mode": "exact_references",
                                "conflicting_fields": conflicting_fields,
                                "allowed_fields": ["refs"]})
                rows = [self.store.get(item) for item in args["refs"]]
                # Exact target membership remains enforced for local records;
                # external evidence/source records are reusable resources.
                for row in rows:
                    if row["record_type"] in {"input", "feature", "product", "read_subject"}:
                        if not self.store._in_scope(row["id"], self.store.validate_scope(scope)):
                            raise ContractError("subject_outside_assigned_scope")
                return {"records": [received(row) for row in rows], "count": len(rows), "next_offset": None}, []
            kind, offset, limit = args.get("kind", "hypothesis"), args.get("offset", 0), args.get("limit", 100)
            page = self.store.query_records(kind, scope=scope, offset=offset, limit=limit,
                current_only=args.get("current_only", False), references=args.get("references"))
            page['records'] = [received(row) for row in page['records']]
            return page, []
        if name == "source.read":
            return source_window(self.store, **args), []
        if name == 'source.locate':
            return locate_source(self.store, **args,
                permitted_inputs=self._permitted_record_refs.get(), scope=scope), []
        if name == 'result.blast.hsp':
            from .library.blast_result_views import read_blast_hsp
            return read_blast_hsp(self.store, **args,
                permitted_inputs=self._permitted_record_refs.get(), scope=scope,
                grade_result=self._grade_supplied_result), []
        if name == "image.view":
            body = prepare_image(self.store, **args)
            source = self._put("source", {"provider": "image.view", "accession": None, "uri": None,
                "artifact_ref": body["image_artifact_ref"], "text_ref": None,
                "parent_source_refs": [body["input_source_ref"]],
                "request_ref": self.store.artifact(canonical(body), "application/json"),
                "version": body["software_version"],
                "retrieved_at": datetime.now(timezone.utc).isoformat()}, origin="tool")
            view = self._put("image_view", {"source_ref": source["id"], **body}, origin="tool")
            return {"view_ref": view["id"], "view": view}, [source["id"], view["id"]]
        if name == "translation.codes":
            return {"codes": translation_codes(), "biopython_version": version("biopython")}, []
        if name == "reference.neighborhood":
            reference = self.store.get(args["reference_ref"])
            if reference["record_type"] != "reference" or reference.get("molecule") not in {"dna", "rna"}:
                raise ContractError("acquired_nucleotide_reference_required")
            original = self.store.get(reference["source_ref"])
            request = json.loads(self.store.get_artifact(original["request_ref"]))["request"] if original["request_ref"] else None
            body = genbank_neighborhood(self.store.get_artifact(original["artifact_ref"]),
                accession=reference["accession"], selector=args["selector"], left_bp=args["left_bp"],
                right_bp=args["right_bp"], source_request=request)
            source = self._source("genbank.neighborhood", {"source_ref": original["id"],
                "reference_ref": reference["id"], **body}, software_version=NEIGHBORHOOD_VERSION)
            observation = self._observation("context", [reference["id"]], source,
                measurements(reference_ref=ref(reference["id"]), count=number(len(body["features"]))),
                references=[reference["id"]], dependencies=[original["id"], reference["id"]])
            return {**body, "source_ref": source["id"], "observation_ref": observation["id"]}, [source["id"], observation["id"]]
        if name == "sequence.inspect":
            subject = self._check_sequence_operand(args["subject_ref"], scope)
            sequence = self._sequence(subject["id"])
            grading = self._composition_grading(subject, sequence)
            scores = grading.get("scores") or {}
            body = {**inspect_sequence(sequence),
                "molecule": self.store.subject_molecule(subject["id"]),
                "gc_fraction": scores.get("gc_fraction"), "gc_denominator": scores.get("gc_denominator")}
            source = self._source("sequence.inspect", body, software_version=version("biopython"),
                tool_grading=grading)
            values = measurements(length=number(body["length"]))
            if body["gc_fraction"] is not None:
                values += measurements(gc_fraction=number(body["gc_fraction"]))
            values += self._composition_values(grading)
            observation = self._observation("sequence_composition", [subject["id"]], source, values)
            return {**body, "observation_ref": observation["id"]}, [source["id"], observation["id"]]
        if name in {"sequence.translate", "genes.predict", "sequence.view"}:
            return self._derive(name, args, scope)
        if name == "sequence.sites":
            return self._alignment_sites(args, scope)
        raise ContractError("unimplemented_tool")

    def _align_one(self, args, scope, native: SequenceWork):
        query = self._check_sequence_operand(args["query_ref"], scope)
        # A comparison operand is reusable evidence even when it is an
        # original caller sequence outside this local annotation assignment.
        self.store.subject_length(args["reference_ref"])
        body = json.loads(native.output_path.read_text(encoding="utf-8"))
        from gene_annotation_episode.episodic_workflow.root.library.biopython_pairwise_grader import grade_biopython_pairwise
        grading = self._grade_supplied_result(grade_biopython_pairwise, body,
            molecule=args["molecule"], _retain_correspondence=True)
        scores = grading.get("scores") or {}
        # Compatibility names project the common calculated cells. Coverage
        # includes aligned insertions; it is distinct from paired coverage.
        aliases = {name: scores.get(component) for name, component in (
            ("paired_positions", "paired_positions"), ("identical_positions", "identical_positions"),
            ("identity_fraction", "paired_identity"), ("query_coverage", "query_aligned_coverage"),
            ("reference_coverage", "reference_aligned_coverage"))}
        geometry = (grading.get("sheet") or {}).get("geometry") or {}
        # Physical timing is execution information. Keeping it out of the
        # measurement body preserves the identity of unchanged scientific
        # evidence across independent physical runs.
        source = self._source("biopython.alignment", body, software_version=version("biopython"),
            operand_refs=list(dict.fromkeys([query['id'], args['reference_ref']])),
            tool_grading=grading)
        values = measurements(reference_ref=ref(args["reference_ref"]))
        values += self._grading_values({**aliases, "target_coverage": aliases["reference_coverage"]},
            ("identity_fraction", "query_coverage", "target_coverage"))
        values += self._grading_values({"alignment_score": body.get("native_score")}, ("alignment_score",))
        if geometry.get("available") and geometry.get("query_interval") is not None:
            values += measurements(query_start=number(geometry["query_interval"][0]),
                                   query_end=number(geometry["query_interval"][1]))
        values += self._grading_values(scores, (
            "alignment_columns", "paired_positions", "identical_positions", "substituted_positions",
            "query_gap_columns", "reference_gap_columns", "query_aligned_positions",
            "reference_aligned_positions", "paired_identity", "alignment_identity",
            "query_paired_coverage", "reference_paired_coverage", "query_aligned_coverage",
            "reference_aligned_coverage"))
        values += self._grading_values(body, ("query_length", "reference_length"))
        intervals = ([{"role": role, "subject_ref": subject_ref, "start": interval[0], "end": interval[1],
            "unit": self.store.subject_unit(subject_ref), "model_unit": "aa" if args["molecule"] == "protein" else "nt"}
            for role, subject_ref, interval in (("query", query["id"], geometry["query_interval"]),
                ("reference", args["reference_ref"], geometry["reference_interval"]))
            if interval is not None] if geometry.get("available") else None)
        observation = self._observation("alignment", [query["id"]], source, values,
            references=[args["reference_ref"]], dependencies=list(dict.fromkeys([query["id"], args["reference_ref"]])),
            operand_intervals=intervals)
        preview = {key: value for key, value in body.items()
            if key not in {"aligned_query", "aligned_reference", "coordinates", *aliases}}
        return {**preview, **aliases, "local_job": native.metadata,
            "observation_ref": observation["id"], "source_ref": source["id"]}, [source["id"], observation["id"]]

    def _alignment_sites(self, args, scope):
        from .library.alignment_site_native import (reference_grading, compatibility_sites,
            compatibility_insertions)
        alignment = self.store.get(args["alignment_ref"])
        if alignment.get("record_type") != "observation" or alignment.get("kind") != "alignment":
            raise ContractError("alignment_observation_required")
        if ("positions" in args) == ("window" in args):
            raise ContractError("choose_reference_positions_or_window",
                detail={"conflicting_or_missing_fields": ["positions", "window"]})
        if "positions" in args:
            positions = args["positions"]
            selection = {"kind": "reference_positions", "positions": positions}
        else:
            start, end = args["window"]["start"], args["window"]["end"]
            if not start < end:
                raise ContractError("invalid_reference_window")
            positions = list(range(start, end))
            selection = {"kind": "reference_window", "start": start, "end": end}
        if len(alignment['subject_refs']) != 1 or len(alignment['source_subject_refs']) != 1:
            raise ContractError('site_operand_identity_conflict')
        for subject in alignment['subject_refs']:
            if self.store.roots(subject) and not self.store._in_scope(subject, self.store.validate_scope(scope)):
                raise ContractError('subject_outside_assigned_scope')
        reference = self.store.get(alignment['source_subject_refs'][0])
        reference_length = (reference['length'] if reference['record_type'] == 'reference'
            and reference.get('sequence_ref') is None else self.store.subject_length(reference['id']))
        if any(type(p) is not int or not 0 <= p < reference_length for p in positions):
            raise ContractError('invalid_reference_site')
        source = self.store.get(alignment['source_ref'])
        grading = reference_grading(self.store, alignment, selection,
            sequence_reader=self._sequence, grade_result=self._grade_supplied_result)
        sheet, scores = grading.get('sheet'), grading.get('scores') or {}
        sites = compatibility_sites(sheet) if sheet is not None else None
        insertions = compatibility_insertions(sheet) if sheet is not None else None
        intervals = []
        for site in (sheet or {}).get('sites', []):
            if site['relationship'] in {'outside_alignment', 'unavailable'}:
                continue
            for role in ('query', 'reference'):
                span = site[role + '_interval']
                if span is not None:
                    operand = sheet['operands'][role]
                    intervals.append({'role': role, 'subject_ref': operand['subject_ref'],
                        'start': span[0], 'end': span[1], 'unit': operand['unit'],
                        'model_unit': operand['alignment_unit']})
        for insertion in insertions or []:
            operand = sheet['operands']['query']
            intervals.append({'role': 'query', 'subject_ref': operand['subject_ref'],
                'start': insertion['query_interval'][0], 'end': insertion['query_interval'][1],
                'unit': operand['unit'], 'model_unit': operand['alignment_unit']})
        intervals = list({canonical(row): row for row in intervals}.values())
        for subject in alignment['subject_refs']:
            query_spans = [{'start': row['start'], 'end': row['end']} for row in intervals
                if row['role'] == 'query' and row['subject_ref'] == subject]
            if query_spans:
                footprint = None
                if self.store.roots(subject):
                    try:
                        footprint = self.store.map_segments(subject, query_spans)
                    except ContractError as error:
                        if str(error) != 'subregion_mapping_unavailable':
                            raise
                        footprint = self.store.coverage(subject)
                self._check_sequence_operand(subject, scope, footprint=footprint)
        extra = {}
        if source['provider'] == 'minimap2.mapping':
            native = alignment['native_minimap2']
            query = self.store.get(alignment['subject_refs'][0])
            extra = {'quality_encoding': query.get('quality_encoding', 'unspecified'),
                'mapping_quality': native['mapping_quality'],
                'mapping_quality_available': native['mapping_quality'] != 255,
                'native_alignment_type': native['native_alignment_type']}
        measured = self._source('alignment.sites', {'alignment_ref': alignment['id'],
            'native_provider': source['provider'], 'requested_positions': positions,
            'sites': sites, 'insertions': insertions, **extra},
            parent_source_refs=[source['id']], software_version='checked_alignment_sites_v3',
            tool_grading=grading)
        summary = scores.get('summary') or {}
        values = self._grading_values(summary, tuple(summary))
        if sites is not None:
            values += measurements(count=number(len(sites)))
        observation = self._observation('comparison', alignment['subject_refs'], measured,
            values, references=alignment['source_subject_refs'], dependencies=[alignment['id']],
            operand_intervals=intervals)
        return {'sites': sites[:12] if sites is not None else None,
            'insertions': insertions[:12] if insertions is not None else None,
            'site_count': len(sites) if sites is not None else None,
            'insertion_count': len(insertions) if insertions is not None else None,
            'data_status': sheet['status'] if sheet is not None else 'unavailable',
            'selected_site_components': summary, **extra, 'preview_limit': 12,
            'complete_result_source_ref': measured['id'], 'observation_ref': observation['id'],
            'source_ref': measured['id']}, [measured['id'], observation['id']]

    def _inspect_reads(self, args, scope):
        batch = self._begin_publication_batch()
        # Select explicitly, validate ownership first, then stream native rows.
        # No private controller loop or scientific judgment is hidden here.
        from gene_annotation_episode.materials import artifact_file
        import tempfile
        import os
        subjects = [self._check_sequence_operand(ref, scope) for ref in args["subject_refs"]]
        if any(row["record_type"] != "read_subject" for row in subjects):
            raise ContractError("original_read_subject_required")
        with tempfile.TemporaryDirectory(prefix=".read-inspection-", dir=self.store.path) as directory:
            path = Path(directory) / "native.jsonl"
            grading_path = Path(directory) / "grading.jsonl"
            with path.open("w") as handle, grading_path.open("w") as grading_handle:
                for subject in subjects:
                    sequence = self._sequence(subject["id"])
                    grading = self._composition_grading(subject, sequence)
                    scores = grading.get("scores") or {}
                    body = {"subject_ref": subject["id"], **inspect_sequence(sequence),
                        "molecule": self.store.subject_molecule(subject["id"]),
                        "gc_fraction": scores.get("gc_fraction"),
                        "gc_denominator": scores.get("gc_denominator")}
                    handle.write(canonical(body) + "\n")
                    grading_handle.write(canonical({"subject_ref": subject["id"], "grading": grading}) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
                grading_handle.flush()
                os.fsync(grading_handle.fileno())
            artifact = artifact_file(self.store, path, "application/x-ndjson")
            grading_rows = artifact_file(self.store, grading_path, "application/x-ndjson")
            from .library.tool_grading_artifacts import retain_tool_grading
            grading_artifact = retain_tool_grading(self.store, provider="reads.inspect",
                native_artifact_ref=artifact, grading={"schema": "sequence_composition_collection_v1",
                    "row_count": len(subjects), "rows_artifact_ref": grading_rows,
                    "row_format": "subject_ref_and_grading_jsonlines"})
            source = self._put("source", {"provider": "reads.inspect", "accession": None,
                "uri": None, "artifact_ref": artifact, "text_ref": artifact,
                "request_ref": self.store.artifact(canonical(args), "application/json"),
                "version": version("biopython"), "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "auxiliary_artifact_refs": [grading_rows, grading_artifact],
                "parent_source_refs": sorted({row["source_ref"] for row in subjects})}, origin="tool")
            preview, refs = [], [source["id"]]
            self._batch_observations(batch, source["id"])
            with path.open() as handle, grading_path.open() as grading_handle:
                for line, grading_line in zip(handle, grading_handle, strict=True):
                    body = json.loads(line)
                    graded_row = json.loads(grading_line)
                    if graded_row["subject_ref"] != body["subject_ref"]:
                        raise ContractError("read_grading_subject_mismatch")
                    values = measurements(length=number(body["length"]))
                    if body["gc_fraction"] is not None:
                        values += measurements(gc_fraction=number(body["gc_fraction"]))
                    values += self._composition_values(graded_row["grading"])
                    observed = self._observation("sequence_composition", [body["subject_ref"]], source, values,
                        dependencies=[body["subject_ref"]])
                    refs.append(observed["id"])
                    batch["published_rows_total"] += 1
                    if len(preview) < 12:
                        preview.append({**body, "observation_ref": observed["id"]})
            return {"count": len(subjects), "records": preview, "preview_limit": 12,
                "source_ref": source["id"], "more_records_available_through_state_query": len(subjects)>12,
                "target_annotation": "not_performed"}, refs

    def _derive(self, name: str, args: dict, scope: dict | None, native: SequenceWork | None = None) -> tuple[dict, list[str]]:
        batch = self._begin_publication_batch()
        grading = None
        subject = self.store.get(args["subject_ref"])
        model = args["molecule"] if name == "sequence.view" else "dna"
        sequence = self._sequence(subject["id"], molecule_model=model)
        parent_mapping = self.store.sequence_mapping(subject["id"])
        if name == "sequence.view":
            selected = args.get("segments", [{"start": 0, "end": len(sequence)}])
            footprint = self.store.map_segments(subject["id"], selected)
            self._check_sequence_operand(subject["id"], scope, footprint=footprint)
            try:
                body = view_sequence(sequence, **{key: value for key, value in args.items() if key != "subject_ref"})
            except ValueError as error:
                raise ContractError(str(error)) from error
            from gene_annotation_episode.episodic_workflow.root.library.sequence_extraction_grader import grade_extraction
            request = inspect.signature(view_sequence).bind(sequence,
                **{key: value for key, value in args.items() if key != "subject_ref"})
            request.apply_defaults()
            selected_request = {key: value for key, value in request.arguments.items() if key != "sequence"}
            if selected_request["segments"] is None:
                selected_request["segments"] = [{"start": 0, "end": len(sequence)}]
            grading = self._grade_supplied_result(grade_extraction, body,
                input_sequence=sequence, subject_ref=subject["id"],
                parent_mapping=parent_mapping, request=selected_request)
            selected = body["input_segments"]
            candidates = [{"segments": selected, "strand": "-" if body["orientation"] == "reverse_complement" else "+",
                           "sequence": body["sequence"]}]
            software_version = VIEW_VERSION
        else:
            start, end = args.get("start", 0), args.get("end", len(sequence))
            if not 0 <= start < end <= len(sequence):
                raise ContractError("requested_interval_outside_subject")
            footprint = self.store.map_segments(subject["id"], [{"start": start, "end": end}])
            self._check_sequence_operand(subject["id"], scope, footprint=footprint)
            if parent_mapping["units_per_symbol"] != 1:
                raise ContractError("translation_requires_nucleotide_symbol_mapping")
            if name == "sequence.translate":
                body = translate(sequence, **{key: value for key, value in args.items() if key != "subject_ref"})
                from gene_annotation_episode.sequence_translation_grader import grade_translation
                request = inspect.signature(translate).bind(sequence,
                    **{key: value for key, value in args.items() if key != "subject_ref"})
                request.apply_defaults()
                selected_request = {key: value for key, value in request.arguments.items() if key != "sequence"}
                if selected_request["end"] is None:
                    selected_request["end"] = len(sequence)
                grading = self._grade_supplied_result(grade_translation, body,
                    input_sequence=sequence, subject_ref=subject["id"],
                    parent_mapping=parent_mapping, request=selected_request,
                    genetic_code=body["genetic_code_snapshot"])
                candidates = [{"start": body["translated_interval"][0], "end": body["translated_interval"][1],
                    "strand": body["strand"], "protein_sequence": body["sequence"]}]
            else:
                if native is None:
                    raise ContractError("native_sequence_worker_result_required")
                body = json.loads(native.output_path.read_text(encoding="utf-8"))
                from gene_annotation_episode.prodigal_grader import grade_prodigal
                grading = self._grade_supplied_result(grade_prodigal, body,
                    input_length=end - start, input_start=start)
                body["local_job"] = native.metadata
                for candidate in body["candidates"]:
                    candidate["start"] += start
                    candidate["end"] += start
                body["input_interval"] = [start, end]
                candidates = body["candidates"]
            body["omitted_terminal_stop"] = bool(name == "sequence.translate" and body["cds"])
            software_version = version("biopython" if name == "sequence.translate" else "pyrodigal")
        body["mapping_version"] = MAPPING_VERSION
        body["subject_ref"] = subject["id"]
        source = self._source(name, body, software_version=software_version, tool_grading=grading)
        self._batch_observations(batch, source["id"])
        condition = self._put("context", {"context_type": "processing",
            "name": "sequence_view_model" if name == "sequence.view" else "translation_model",
            "source_ref": source["id"], "attributes": measurements(molecule_model=enum(model)) if name == "sequence.view"
                else measurements(genetic_code=number(args["code"])), "related_refs": [subject["id"]]}, origin="tool")
        refs, results = [source["id"], condition["id"]], []
        for candidate_index, candidate in enumerate(candidates):
            segments = candidate["segments"] if name == "sequence.view" else [{"start": candidate["start"], "end": candidate["end"]}]
            output = candidate["sequence"] if name == "sequence.view" else candidate["protein_sequence"]
            try:
                if name == "sequence.view":
                    scale = parent_mapping["units_per_symbol"]
                    mapping = {"version": MAPPING_VERSION, "units_per_symbol": scale, "symbol_length": len(output),
                        "path": extract_path(parent_mapping["path"],
                            [{"start": row["start"] * scale, "end": row["end"] * scale} for row in segments],
                            strand=candidate["strand"])}
                else:
                    mapping = translation_mapping(parent_mapping["path"], start=candidate["start"], end=candidate["end"],
                        strand=candidate["strand"], protein_length=len(output), omitted_terminal_stop=body["omitted_terminal_stop"])
            except ValueError as error:
                raise ContractError(str(error)) from error
            feature = self._put("feature", {"subject_ref": subject["id"], "kind": "CDS" if name == "genes.predict" else "sequence_region",
                "segments": segments, "strand": candidate["strand"], "context_refs": [condition["id"]]}, origin="tool", scope=scope)
            product = self._put("product", {"parent_refs": [feature["id"]],
                "molecule": args["molecule"] if name == "sequence.view" else "protein",
                "sequence_ref": self.store.artifact(output, "text/plain"),
                "derivation": "extraction" if name == "sequence.view" else "translation", "context_refs": [condition["id"]],
                "footprint": self.store.footprint_from_mapping(mapping),
                "mapping": mapping, "mapping_source_ref": source["id"]}, origin="tool", scope=scope)
            if name == "sequence.view":
                summary = (grading.get("scores") or {}).get("summary", {})
                values = measurements(molecule_model=enum(model))
                values += self._grading_values({"length": summary.get("output_symbol_count")}, ("length",))
            else:
                values = measurements(genetic_code=number(args["code"]),
                    start=number(candidate["start"]), end=number(candidate["end"]))
            if name == "genes.predict":
                values += measurements(native_confidence=number(candidate["native_confidence"]), model_score=number(candidate["native_score"]))
                scored_candidates = (grading.get("scores") or {}).get("candidates", [])
                if candidate_index < len(scored_candidates):
                    values += self._grading_values(scored_candidates[candidate_index], (
                        "interval_length_nt", "protein_length_aa", "internal_stop_count", "terminal_stop_count"))
            elif name == "sequence.translate":
                values += self._grading_values((grading.get("scores") or {}).get("summary", {}), (
                    "input_length_nt", "selected_length_nt", "frame_skipped_nt",
                    "translated_length_nt", "trailing_untranslated_bases", "translated_codon_count",
                    "output_symbol_count", "amino_acid_symbol_count", "internal_stop_count",
                    "terminal_stop_symbol_count", "omitted_terminal_stop_codon_count",
                    "ambiguous_codon_count", "ambiguous_output_symbol_count", "mapped_output_symbol_count",
                    "compatible_codon_count", "incompatible_codon_count", "unknown_codon_count",
                    "selected_input_fraction", "selected_input_fraction_denominator_nt"))
            elif name == "sequence.view":
                values += self._grading_values((grading.get("scores") or {}).get("summary", {}), (
                    "input_symbol_count", "output_symbol_count", "requested_segment_count",
                    "selected_symbol_occurrence_count", "distinct_selected_input_symbol_count",
                    "repeated_selected_input_symbol_count", "selected_input_fraction",
                    "selected_input_fraction_denominator_symbols", "expected_output_symbol_count",
                    "output_length_difference", "compared_symbol_count", "matching_symbol_count",
                    "mismatching_symbol_count", "unmapped_output_symbol_count", "source_segment_count"))
            observation = self._observation("gene_prediction" if name == "genes.predict" else "coordinate_mapping",
                [feature["id"], product["id"]], source, values, dependencies=[subject["id"], condition["id"]])
            refs += [feature["id"], product["id"], observation["id"]]
            results.append({"feature_ref": feature["id"], "product_ref": product["id"], "observation_ref": observation["id"]})
            batch["published_rows_total"] += 1
        return {"count": len(results), "records": results[:12], "preview_limit": 12,
                "more_records_available_through_state_query": len(results) > 12,
                "source_ref": source["id"], "limitations": body.get("limitations", [])}, refs

