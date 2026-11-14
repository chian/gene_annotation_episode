"""Original substantive ordinary-tool methods: tool_blast_results."""
from __future__ import annotations
from dataclasses import replace
from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.domain import identity
from gene_annotation_episode.episodic_workflow.root.library import blast_search as blast
from .tool_values import number
from .tool_values import enum
from .tool_values import ref
from .tool_values import measurements

class ToolBlastResults:
    def _import_blast(self, snapshot: SourceSnapshot, *, submission_snapshot=None,
                      request=None, native_handle=None) -> tuple[dict, list[str]]:
        if submission_snapshot is None:
            # Existing ordinary-operation receipts retain their original path.
            job = self.remote_searches._get(snapshot.transport["job_ref"])
            submission = self.remote_searches._load_snapshot(job["submission"])
        else:
            # The API episode owns the actual original submission and native
            # handle. Publication neither fabricates a provider_jobs row nor
            # submits/polls/fetches anything.
            submission = submission_snapshot
            rid, _ = blast.submission(submission.content)
            if (not isinstance(request, dict) or not isinstance(native_handle, dict)
                    or native_handle.get("rid") != rid):
                raise ContractError("blast_original_submission_identity_conflict")
            snapshot = replace(snapshot, request={**request, "job_id": rid})
        submitted = self._source(submission.service, None, snapshot=submission)
        parsed = blast.document(snapshot.content)
        blast.validate_identity(parsed, snapshot.request)
        parents, refs = [submitted["id"]], [submitted["id"]]
        if parsed["member"] is not None:
            archive = self._source("ncbi_blast_archive", None, snapshot=snapshot, parent_source_refs=parents)
            refs.append(archive["id"])
            parents.append(archive["id"])
            snapshot = replace(snapshot, content=parsed["json_bytes"], media_type="application/json",
                transport={**snapshot.transport, "representation": "exact_blast_zip_member_bytes",
                    "archive_member": parsed["member"]})
        snapshot = replace(snapshot, transport={**snapshot.transport,
            "source_version_meaning": "native_blast_program_version_not_database_release",
            "hsp_projection_version": blast.HSP_PROJECTION_VERSION})
        from .library.blast_graders import grade_blast_result
        grading = self._grade_supplied_result(grade_blast_result, snapshot.content,
            mode="database", resource="api", output_format="json2", request=snapshot.request,
            _retain_correspondence=True)
        source = self._source("ncbi_blast", None, snapshot=snapshot, parent_source_refs=parents,
            software_version=parsed["report"].get("version"), tool_grading=grading)
        from .library.tool_grading_artifacts import source_tool_grading_entries
        retained, = [entry for entry in source_tool_grading_entries(self.store, source["id"])
                     if entry["grading"] == {key: value for key, value in grading.items()
                                              if key != "correspondence"}]
        subject_ref = snapshot.request["subject_ref"]
        program = snapshot.request["algorithm"]
        query_unit, reference_unit, model_unit = blast.PROGRAM_UNITS[program]
        processing = self._put("context", {"context_type": "processing", "name": "blast_search_model",
            "source_ref": source["id"], "attributes": measurements(molecule_model=enum(
                "protein" if query_unit == "aa" else "dna")), "related_refs": [subject_ref]}, origin="tool")
        refs += [source["id"], processing["id"]]
        records, errors, hit_count, hsp_count = [], [], 0, 0
        if grading.get("failure") is not None:
            errors.append({"hit_ordinal": None, "hsp_ordinal": None,
                "code": "blast_shared_grading_unavailable", "failure": grading["failure"]})
        for hit_index, hit in enumerate(parsed["search"].get("hits", [])):
            try:
                if not isinstance(hit, dict):
                    raise ValueError("blast_hit_object_required")
                length = blast.integer(hit["len"], "hit_length", minimum=1)
                descriptions = hit.get("description") or []
                if not isinstance(descriptions, list):
                    errors.append({"hit_ordinal": hit_index, "hsp_ordinal": None, "code": "blast_hit_description_array_required"})
                    descriptions = []
                valid_descriptions = []
                for description_index, description in enumerate(descriptions):
                    if isinstance(description, dict):
                        valid_descriptions.append((description_index, description))
                    else:
                        errors.append({"hit_ordinal": hit_index, "hsp_ordinal": None,
                            "description_ordinal": description_index, "code": "blast_hit_description_object_required"})
                descriptions = valid_descriptions
                first = descriptions[0][1] if descriptions else {}
                import re
                accession = first.get("accession") or first.get("id")
                accession_basis = "native_accession" if first.get("accession") else "native_id"
                if (not isinstance(accession, str) or len(accession)>200
                        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/+%#?=;&@~-]*", accession) is None):
                    accession = identity("source_local_hit", {"source_ref": source["id"], "hit_ordinal": hit_index})
                    accession_basis = "source_local_hit"
                label = first.get("title") or accession
                if not isinstance(label, str):
                    errors.append({"hit_ordinal": hit_index, "hsp_ordinal": None, "code": "blast_hit_title_not_string"})
                    label = accession
                terms = []
                for description_index, description in descriptions:
                    if description.get("taxid") is not None:
                        try:
                            taxid = blast.integer(description["taxid"], "taxid", minimum=1)
                            taxon_label = description.get("sciname")
                            if not isinstance(taxon_label, str) or len(taxon_label)>512 or "\n" in taxon_label or "\r" in taxon_label:
                                taxon_label = str(taxid)
                            term = self._put("term", {"namespace": "ncbi_taxonomy", "accession": str(taxid),
                                "label": taxon_label, "term_type": "taxon",
                                "source_ref": source["id"], "anchor": None}, origin="external")
                            terms.append(term["id"])
                        except (ValueError, TypeError) as error:
                            errors.append({"hit_ordinal": hit_index, "hsp_ordinal": None,
                                "description_ordinal": description_index, "code": str(error)})
                reference = self._put("reference", {"reference_type": "protein" if reference_unit == "aa" else "sequence",
                    "source_ref": source["id"], "accession": accession,
                    "label": label if len(label)<=512 and "\n" not in label and "\r" not in label else accession,
                    "sequence_ref": None, "molecule": "protein" if reference_unit == "aa" else "unspecified",
                    "length": length, "term_refs": list(dict.fromkeys(terms)), "context_refs": []}, origin="external")
                refs += terms + [reference["id"]]
                hit_count += 1
                hsps = hit.get("hsps", [])
                if not isinstance(hsps, list):
                    raise ValueError("blast_hsp_array_required")
            except (ValueError, TypeError, KeyError) as error:
                errors.append({"hit_ordinal": hit_index, "hsp_ordinal": None, "code": str(error)})
                continue
            for hsp_index, native in enumerate(hsps):
                try:
                    if not isinstance(native, dict):
                        raise ValueError("blast_hsp_object_required")
                    component, address = blast.shared_hsp_component(grading,
                        hit_ordinal=hit_index, hsp_ordinal=hsp_index)
                    row = blast.hsp_row(native, component=component,
                        program=program, query_length=snapshot.request["query_length"],
                        reference_length=length, hit_ordinal=hit_index, hsp_ordinal=hsp_index)
                    row["native_blast"]["shared_projection"] = {
                        "version": blast.HSP_PROJECTION_VERSION,
                        "grading_artifact_ref": retained["artifact_ref"],
                        "native_artifact_ref": source["artifact_ref"], **address}
                    qi, ri = row["query_interval"], row["reference_interval"]
                    observation = self._put("observation", {"kind": "comparison", "subject_refs": [subject_ref],
                        "source_subject_refs": [reference["id"]], "source_ref": source["id"], "anchor": None,
                        "measurements": measurements(reference_ref=ref(reference["id"]),
                            **{key:number(value) for key,value in row["measurements"].items()}),
                        "dependencies": [subject_ref, reference["id"], processing["id"]],
                        "operand_intervals": [{"role": "query", "subject_ref": subject_ref, "start": qi[0], "end": qi[1],
                            "unit": self.store.subject_unit(subject_ref), "model_unit": model_unit},
                            {"role": "reference", "subject_ref": reference["id"], "start": ri[0], "end": ri[1],
                             "unit": self.store.subject_unit(reference["id"]), "model_unit": model_unit}],
                        "native_blast": row["native_blast"]}, origin="tool")
                    refs.append(observation["id"])
                    hsp_count += 1
                    if row["unavailable_measurements"]:
                        errors.append({"hit_ordinal": hit_index, "hsp_ordinal": hsp_index,
                            "code": "blast_hsp_shared_measurements_unavailable",
                            "measurements": row["unavailable_measurements"]})
                    if len(records) < 12:
                        records.append({"reference_ref": reference["id"], "observation_ref": observation["id"],
                            "accession": accession, "accession_basis": accession_basis, **row})
                except (ValueError, TypeError, KeyError) as error:
                    errors.append({"hit_ordinal": hit_index, "hsp_ordinal": hsp_index, "code": str(error)})
        return {"source_ref": source["id"], "submission_source_ref": submitted["id"],
            "job_ref": snapshot.transport.get("job_ref"), "rid": snapshot.request["job_id"], "subject_ref": subject_ref,
            "records": records, "preview_limit": 12, "projected_hit_count": hit_count,
            "projected_hsp_count": hsp_count, "native_hit_count": len(parsed["search"]["hits"]) if "hits" in parsed["search"] else None,
            "native_hit_array_present": "hits" in parsed["search"],
            "reported_hit_array_empty": parsed["search"].get("hits") == [],
            "more_records_available_through_state_query": hsp_count > 12, "projection_errors": errors,
            "requested_database": snapshot.request["database"], "effective_search_target": parsed["report"].get("search_target"),
            "native_program_version": parsed["report"].get("version"), "database_release": None,
            "native_parameters": parsed["report"].get("params"), "native_statistics": parsed["search"].get("stat"),
            "native_message": parsed["search"].get("message"), "adapter_version": blast.VERSION,
            "no_hit_meaning": ("explicit_empty_native_hit_array_for_submitted_operand_under_recorded_provider_search"
                if parsed["search"].get("hits") == [] else None),
            "functional_or_lineage_assignment": "not_performed"}, list(dict.fromkeys(refs))

