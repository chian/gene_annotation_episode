"""Ordinary-tool methods: tool_rna_search."""
from __future__ import annotations
from dataclasses import replace
import hashlib
from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.domain import canonical
from .library.rna_evidence import NativeSearch
from .library.rna_evidence import run_cmsearch
from .tool_values import number
from .tool_values import ref
from .tool_values import measurements

class ToolRnaSearch:
    async def _native_cmsearch_async(self, args: dict, scope: dict | None) -> NativeSearch:
        subject = self._check_sequence_operand(args["subject_ref"], scope)
        molecule = self.store.subject_molecule(subject["id"])
        if molecule == "protein":
            raise ContractError("cmsearch_requires_nucleotide_operand")
        model = self.store.get(args["model_ref"])
        if model["record_type"] != "reference" or model["reference_type"] != "family":
            raise ContractError("acquired_covariance_model_reference_required")
        source = self.store.get(model["source_ref"])
        if source["provider"] != "rfam_covariance_model":
            raise ContractError("acquired_covariance_model_source_required")
        # All Store reads are on the owning thread. Only immutable bytes and
        # settings cross to the worker; no write transaction spans native work.
        if self.store.db.in_transaction:
            raise ContractError("native_search_requires_no_active_store_transaction")
        orientation_model = molecule if molecule in {"dna", "rna"} else "rna"
        native = await self._native_thread_async(run_cmsearch,
            sequence=self._sequence(subject["id"], molecule_model=orientation_model),
            subject_ref=subject["id"], model=self.store.get_artifact(source["artifact_ref"]),
            model_ref=model["id"], configuration=dict(self.cmsearch_configuration), parameters=args.get("parameters"),
            job_limits=self.local_job_policy.to_dict())
        native = replace(native, metadata={**native.metadata, "operand_molecule_declaration": molecule,
            "orientation_processing_model": orientation_model,
            "orientation_model_is_input_classification": False})
        if native.metadata["returncode"] != 0:
            diagnostic = self._native_artifacts(native)
            raise AcquisitionError("cmsearch_native_error", phase="native_execution",
                operational={"diagnostic_ref": self.store.artifact(canonical(diagnostic), "application/json"),
                    "native_returncode": native.metadata["returncode"],
                    "native_stderr_tail": native.stderr[-4000:].decode("utf-8", errors="replace"),
                    "native_stdout_tail": native.stdout[-4000:].decode("utf-8", errors="replace")})
        return native

    def _native_artifacts(self, native: NativeSearch) -> dict:
        return {**native.metadata, **{key + "_ref": self.store.artifact(value,
            "text/x-fasta" if key == "input_fasta" else "text/plain") for key, value in
            (("stdout", native.stdout), ("stderr", native.stderr), ("table", native.table),
             ("input_fasta", native.input_fasta), ("native_help", native.help_output))}}

    def _publish_cmsearch(self, args: dict, native: NativeSearch) -> tuple[dict, list[str]]:
        from .library.infernal_search_inputs import populate_infernal_search_sheet
        from .library.infernal_search_grader import calculate_infernal_search_scores

        artifacts = self._native_artifacts(native)
        header = native.metadata["model_header"]
        sheet = populate_infernal_search_sheet([{
            "artifact_id": artifacts["table_ref"], "format": "infernal_tblout", "table_format": 3,
            "content": native.table.decode("utf-8"), "complete": native.metadata["returncode"] == 0,
            "source_descriptor": {"profile": "infernal_tblout", "source_ref": None,
                "artifact_ref": artifacts["table_ref"], "source_sha256": hashlib.sha256(native.table).hexdigest(),
                "source_byte_length": len(native.table), "byte_hash_verified": True}}],
            operation={"program": "cmsearch", "native_version": native.metadata["native_version"],
                "settings": native.metadata["settings"]},
            sequence_metadata=[{"name": args["subject_ref"], "length": native.metadata["target_length"]}],
            model_metadata=[{"name": header["name"], "accession": header["accession"],
                "consensus_length": header["consensus_length"]}])
        sheet["publication_inputs"] = {"subject_ref": args["subject_ref"], "model_ref": args["model_ref"],
            "target_sequence_sha256": native.metadata["target_sequence_sha256"],
            "model_sha256": native.metadata["model_sha256"], "model_header": header,
            "input_fasta_ref": artifacts["input_fasta_ref"]}
        scores = calculate_infernal_search_scores(sheet, parameters={"hit_scope": "reported"})
        source = self._source("infernal.cmsearch", artifacts, text=native.stdout.decode("utf-8"),
            software_version=native.metadata["native_version"], tool_grading={
                "schema": "infernal_cmsearch_grading_v2", "sheet": sheet, "scores": scores})
        refs, records = [source["id"]], []
        calculated = {row["hit_id"]: row for row in scores["hits"]}
        for hit in sheet["hits"]:
            score = calculated[hit["hit_id"]]
            components = score["components"]
            row = {key: hit[key] for key in ("native_target_name", "native_target_accession",
                "native_query_name", "native_query_accession", "algorithm", "model_from", "model_to",
                "strand", "truncation", "pass", "inclusion")}
            row.update(target_from=hit["sequence_from"], target_to=hit["sequence_to"],
                model_length=hit["native_model_length"], target_length=hit["native_sequence_length"],
                target_interval=score["sequence_interval"], model_consensus_interval=score["model_interval"],
                description=hit["description"] or "",
                **{key: components[key] for key in ("gc_fraction", "bias_bits", "bitscore", "evalue")})
            if (row["native_target_name"] != args["subject_ref"] or
                row["target_length"] != native.metadata["target_length"] or
                row["native_query_name"] != header["name"] or
                row["native_query_accession"] != header["accession"] or
                row["model_length"] != header["consensus_length"]):
                raise ContractError("native_cmsearch_operand_identity_mismatch")
            if (any(value is None for key, value in row.items()
                    if key not in {"native_target_accession", "native_query_accession"})
                    or components["sequence_span_fraction"] is None):
                raise ContractError("invalid_cmsearch_fmt3_values", detail={"line": hit["locator"]["line"]})
            values = measurements(profile_ref=ref(args["model_ref"]), bitscore=number(row["bitscore"]),
                evalue=number(row["evalue"]), query_start=number(row["target_interval"][0]),
                query_end=number(row["target_interval"][1]),
                query_coverage=number(components["sequence_span_fraction"]))
            observation = self._put("observation", {"kind": "profile_match", "subject_refs": [args["subject_ref"]],
                "source_subject_refs": [args["model_ref"]], "source_ref": source["id"],
                "measurements": values, "dependencies": [args["subject_ref"], args["model_ref"]], "anchor": None,
                "operand_intervals": [{"role": "query", "subject_ref": args["subject_ref"],
                    "start": row["target_interval"][0], "end": row["target_interval"][1],
                    "unit": self.store.subject_unit(args["subject_ref"]), "model_unit": "nt"}],
                "native_cmsearch": {**row, "native_query_model_ref": args["model_ref"],
                    "native_target_subject_ref": args["subject_ref"]}}, origin="tool")
            refs.append(observation["id"])
            records.append({"observation_ref": observation["id"], **row})
        malformed = [row for artifact in sheet["artifacts"] for row in artifact["rows"]
            if row["status"] == "invalid"]
        if malformed:
            raise ContractError("invalid_cmsearch_fmt3_row", detail={"line": malformed[0]["locator"]["line"]})
        return {"source_ref": source["id"], "model_ref": args["model_ref"], "subject_ref": args["subject_ref"],
            "reported_hit_count": len(records), "records": records[:12], "preview_limit": 12,
            "more_records_available_through_state_query": len(records)>12,
            "native_settings": native.metadata["settings"], "resource_binding": native.metadata["configuration"],
            "native_limitations": native.metadata["native_limitations"],
            "native_roles": native.metadata["native_roles"], "raw_artifacts": artifacts,
            "searched_scope": {"subject_ref": args["subject_ref"], "start": 0, "end": native.metadata["target_length"],
                "unit": self.store.subject_unit(args["subject_ref"])},
            "result_meaning": native.metadata["no_hit_meaning"], "target_annotation": "not_performed"}, refs

