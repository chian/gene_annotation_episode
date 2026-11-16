"""Ordinary-tool methods: tool_rfam_results."""
from __future__ import annotations
import json
from gene_annotation_episode.acquisition import RfamModelSnapshots
from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.library.rfam_discovery import VERSION as RFAM_DISCOVERY_VERSION
from gene_annotation_episode.episodic_workflow.root.library.rfam_discovery import hit_row as rfam_hit_row
from .library.rna_evidence import model_header
from .tool_values import number
from .tool_values import enum
from .tool_values import ref
from .tool_values import measurements

class ToolRfamResults:
    def _import_rfam_discovery(self, snapshot: SourceSnapshot) -> tuple[dict, list[str]]:
        # Submission and result sources form a forward export lineage. Neither
        # the native label nor a new external family becomes an input target.
        job = self.remote_searches._get(snapshot.transport["job_ref"])
        submission = self.remote_searches._load_snapshot(job["submission"])
        submitted = self._source(submission.service, None, snapshot=submission)
        source = self._source(snapshot.service, None, snapshot=snapshot,
                              parent_source_refs=[submitted["id"]])
        body = json.loads(snapshot.content)
        subject_ref = snapshot.request["subject_ref"]
        length = len(self._sequence(subject_ref, molecule_model="rna"))
        processing = self._put("context", {"context_type": "processing", "name": "rfam_nucleotide_search_model",
            "source_ref": source["id"], "attributes": measurements(molecule_model=enum("rna")),
            "related_refs": [subject_ref]}, origin="tool")
        refs, records, errors = [submitted["id"], source["id"], processing["id"]], [], []
        native_rows = 0
        for family_key, hits in body["hits"].items():
            if not isinstance(hits, list):
                errors.append({"family_key": family_key, "native_index": None,
                               "code": "rfam_family_hit_array_required"})
                continue
            native_rows += len(hits)
            for index, native in enumerate(hits):
                try:
                    row = rfam_hit_row(native, family_key=family_key, sequence_length=length)
                except (ValueError, TypeError) as error:
                    errors.append({"family_key": family_key, "native_index": index, "code": str(error)})
                    continue
                label = row["source_family_label"]
                family = self._put("reference", {"reference_type": "family", "source_ref": source["id"],
                    "accession": row["accession"], "label": label if len(label)<=512 and "\n" not in label and "\r" not in label else row["accession"],
                    "sequence_ref": None, "molecule": None, "length": None,
                    "term_refs": [], "context_refs": []}, origin="external")
                start, end = row["sequence_interval"]
                observation = self._observation("profile_match", [subject_ref], source,
                    measurements(profile_ref=ref(family["id"]), reference_ref=ref(family["id"]),
                        bitscore=number(row["bitscore"]), evalue=number(row["evalue"]),
                        gc_fraction=number(row["gc_fraction"]), strand=enum(row["strand"]),
                        query_start=number(start), query_end=number(end), query_coverage=number((end-start)/length)),
                    references=[family["id"]], dependencies=[subject_ref, family["id"], processing["id"]],
                    operand_intervals=[{"role": "query", "subject_ref": subject_ref, "start": start, "end": end,
                        "unit": self.store.subject_unit(subject_ref), "model_unit": "nt"}])
                refs += [family["id"], observation["id"]]
                records.append({"family_ref": family["id"], "observation_ref": observation["id"],
                    "family_key": family_key, "native_index": index, **row,
                    "native_alignment": native.get("alignment")})
        if native_rows != body["numHits"]:
            errors.append({"family_key": None, "native_index": None, "code": "rfam_native_hit_count_mismatch"})
        return {"source_ref": source["id"], "submission_source_ref": submitted["id"],
            "job_ref": snapshot.transport["job_ref"], "job_id": snapshot.request["job_id"],
            "subject_ref": subject_ref, "status": "SUCCESS", "native_hit_count": body["numHits"],
            "projected_hit_count": len(records), "records": records[:12], "preview_limit": 12,
            "more_records_available_through_state_query": len(records)>12, "projection_errors": errors,
            "raw_artifact_ref": source["artifact_ref"], "adapter_version": RFAM_DISCOVERY_VERSION,
            "database_release": None, "model_release": None,
            "native_search_parameters": "provider_defaults_not_exposed",
            "native_times": {key: body.get(key) for key in ("opened", "started", "closed")},
            "time_meaning": "native_strings_preserved_no_clock_correction_or_duration_inference",
            "model_consensus_positions_are_not_physical_reference_residues": True,
            "searched_scope": {"subject_ref": subject_ref, "start": 0, "end": length,
                "unit": self.store.subject_unit(subject_ref)},
            "no_hit_meaning": "no_reported_match_in_submitted_operand_under_unexposed_provider_defaults",
            "functional_or_lineage_assignment": "not_performed"}, list(dict.fromkeys(refs))

    def _import_rfam(self, args: dict, snapshots: RfamModelSnapshots) -> tuple[dict, list[str]]:
        model = self._source("rfam_covariance_model", None, snapshot=snapshots.model,
                             accession=args["accession"])
        refs = [model["id"]]
        header = model_header(snapshots.model.content)
        if header["accession"] != args["accession"]:
            raise ContractError("rfam_model_accession_mismatch")
        family = self._put("reference", {"reference_type": "family", "source_ref": model["id"],
            "accession": args["accession"], "label": header["description"] or header["name"],
            "sequence_ref": None, "molecule": None, "length": None, "term_refs": [], "context_refs": []}, origin="external")
        refs.append(family["id"])
        metadata_ref, metadata = None, None
        if snapshots.metadata is not None:
            source = self._source("rfam_family_metadata", None, snapshot=snapshots.metadata, accession=args["accession"])
            metadata_ref = source["id"]
            refs.append(metadata_ref)
            try:
                metadata = json.loads(snapshots.metadata.content)
            except (ValueError, UnicodeDecodeError) as error:
                raise ContractError("rfam_metadata_invalid_json", detail={"model_ref": family["id"],
                    "metadata_source_ref": metadata_ref}) from error
        return {"model_ref": family["id"], "source_ref": model["id"], "metadata_source_ref": metadata_ref,
            "model_header": header, "family_metadata": metadata,
            "model_consensus_positions_are_not_physical_sequence_residues": True,
            "target_annotation": "not_performed"}, refs

