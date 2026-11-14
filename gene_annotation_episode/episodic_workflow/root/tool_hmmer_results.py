"""Original substantive ordinary-tool methods: tool_hmmer_results."""
from __future__ import annotations
import json
from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.acquisition import parse_hmmer
from gene_annotation_episode.domain import RECORD_SCHEMAS
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.domain import identity
from gene_annotation_episode.domain import validate_schema
from .tool_values import number
from .tool_values import enum
from .tool_values import ref
from .tool_values import measurements

class ToolHmmerResults:
    def _hmmer_grading(self, snapshot):
        from .library.hmmer_graders import grade_hmmer_api_result
        payload = json.loads(snapshot.content)
        request = snapshot.request
        subject_ref = request["subject_ref"]
        sequence = self._sequence(subject_ref, molecule_model="protein")
        details = snapshot.transport.get("job_details") or {}
        database = details.get("database")
        page_count = payload.get("page_count")
        page, page_size = request["page"], request["page_size"]
        inputs = {
            "query": {"name": subject_ref, "kind": "protein_sequence", "alphabet": "amino",
                "length": len(sequence), "sequence": sequence},
            "database": {"name": request["database"],
                "version": database.get("version") if isinstance(database, dict) else None,
                "population": None},
            "native_parameters": request["parameters"],
            "acquisition": {"output_complete": payload.get("status") == "SUCCESS",
                "page_start": (page - 1) * page_size, "page_size": page_size,
                "page_count": page_count,
                "hit_population_complete": (page == 1 and page_count <= 1)
                    if type(page_count) is int and page_count >= 0 else None},
        }
        artifact_ref = self.store.artifact(snapshot.content, snapshot.media_type)
        return grade_hmmer_api_result(payload, algorithm=request["algorithm"],
            artifact_ref=artifact_ref, inputs=inputs)

    def publish_hmmer_result(self, snapshot: SourceSnapshot, scope: dict, operation_key: str) -> dict:
        """Internal API-episode publication; absent from ordinary dispatch/catalog.

        The episode has already retained and validated one selected page. Keep
        exact source bytes and independently valid rows when a later row fails.
        This callable performs no network operation and no polling.
        """
        name = "internal.hmmer.result_publication"
        arguments = {"snapshot_sha256": snapshot.sha256, "request": snapshot.request,
                     "transport": snapshot.transport}
        saved = self.store.db.execute("SELECT * FROM tool_operations WHERE operation_key=?",
                                      (operation_key,)).fetchone()
        if saved is not None:
            if (saved["name"] != name or saved["arguments"] != canonical(arguments)
                    or saved["scope"] != canonical(scope)):
                raise ContractError("operation_key_reused_for_different_work")
            return json.loads(saved["result"])
        self._check_sequence_operand(snapshot.request["subject_ref"], scope)
        token = self._publications.set([])
        grading_token = self._grading_failures.set([])
        try:
            result = {"status": "completed", "operation_ref": identity("operation", {
                "key": operation_key, "name": name, "arguments": arguments}),
                "record_refs": [], "changed_record_refs": [], "result": None, "feedback": None}
            with self.store.transaction():
                grading = self._grade_supplied_result(self._hmmer_grading, snapshot)
                source = self._source(snapshot.service, None, snapshot=snapshot, tool_grading=grading)
                try:
                    result["result"], result["record_refs"] = self._publish_hmmer_rows(snapshot, source, grading=grading)
                    if result["result"].get("projection_errors"):
                        result.update(status="partial", feedback={"category": "partial_execution",
                            "code": "hmmer_rows_partially_projected", "rows": result["result"]["projection_errors"]})
                except Exception as error:
                    result.update(status="partial", record_refs=list(dict.fromkeys(self._written)),
                        result={"source_ref": source["id"], "retained_record_refs": list(dict.fromkeys(self._written))},
                        feedback={"category": "partial_execution", "code": str(error)
                            if isinstance(error, ContractError) else "hmmer_rows_partially_projected",
                            "diagnostic_ref": self.store.artifact(f"{type(error).__name__}: {error}", "text/plain")})
                result["changed_record_refs"] = list(result["record_refs"])
                self._save(operation_key, name, arguments, scope, result)
            return result
        finally:
            self._publications.reset(token)
            self._grading_failures.reset(grading_token)

    def _publish_hmmer_rows(self, snapshot: SourceSnapshot, source: dict, *, grading=None) -> tuple[dict, list[str]]:
        refs = [source["id"]]
        native = json.loads(snapshot.content)
        # Preserve each original array position, independently of the provider's
        # own hit index or domain ordinal. Invalid siblings never renumber joins.
        body = parse_hmmer(canonical({**native, "result": {**native["result"], "hits": []}}).encode(),
                           algorithm=snapshot.request["algorithm"])
        errors = []
        for ordinal, hit in enumerate(native["result"]["hits"]):
            try:
                if not isinstance(hit, dict):
                    raise ValueError("provider_hmmer_hit_object_required")
                if hit.get("metadata") is not None and not isinstance(hit["metadata"], dict):
                    raise ValueError("provider_hmmer_hit_metadata_object_required")
                selected_hit = {**hit, "index": hit.get("index")}
                one = {**native, "result": {**native["result"], "hits": [{**selected_hit, "domains": []}]}}
                parsed_hit, = parse_hmmer(canonical(one).encode(), algorithm=snapshot.request["algorithm"])["hits"]
                parsed_hit["native_array_index"] = ordinal
                parsed_hit["native_accession"] = hit.get("acc")
                parsed_hit["provider_accession"] = (hit.get("metadata") or {}).get("accession")
                parsed_hit["linked_uniprot_accession"] = (hit.get("metadata") or {}).get("uniprot_accession")
                native_domains = hit.get("domains")
                if native_domains is not None and not isinstance(native_domains, list):
                    errors.append({"native_array_index": ordinal, "domain_array_index": None,
                        "code": "provider_hmmer_domains_array_required", "phase": "native_domain_parse"})
                    native_domains = []
                for domain_index, domain in enumerate(native_domains or []):
                    try:
                        if not isinstance(domain, dict):
                            raise ValueError("provider_hmmer_domain_object_required")
                        one["result"]["hits"] = [{**selected_hit, "domains": [domain]}]
                        parsed_domain, = parse_hmmer(canonical(one).encode(), algorithm=snapshot.request["algorithm"])["hits"][0]["domains"]
                        parsed_domain["native_array_index"] = domain_index
                        parsed_hit["domains"].append(parsed_domain)
                    except (ValueError, KeyError, TypeError) as error:
                        errors.append({"native_array_index": ordinal, "domain_array_index": domain_index,
                            "code": str(error), "phase": "native_domain_parse"})
                body["hits"].append(parsed_hit)
            except (ValueError, KeyError, TypeError) as error:
                errors.append({"native_ordinal": ordinal, "code": str(error), "phase": "native_hit_parse"})
        subject_ref = snapshot.request["subject_ref"]
        query_model = self._put("context", {"context_type": "processing", "name": "protein_search_model",
            "source_ref": source["id"], "attributes": measurements(molecule_model=enum("protein")),
            "related_refs": [subject_ref]}, origin="tool")
        refs.append(query_model["id"])
        records = []
        for hit in body["hits"]:
            try:
                terms = []
                if hit["taxon_id"] is not None:
                    taxon = self._put("term", {"namespace": "ncbi_taxonomy", "accession": str(hit["taxon_id"]),
                        "label": hit["source_organism"] or str(hit["taxon_id"]), "term_type": "taxon",
                        "source_ref": source["id"], "anchor": None}, origin="external")
                    terms.append(taxon["id"])
                is_profile = snapshot.request["algorithm"] == "hmmscan"
                # The aligned native target can be a PDB chain with a linked
                # UniProt record. A cross-reference must not replace its identity.
                accession = hit["native_accession"] or hit["provider_accession"] or hit["native_name"]
                try:
                    validate_schema(accession, RECORD_SCHEMAS["reference"]["properties"]["accession"])
                except ContractError:
                    accession = identity("source_local_hit", {"source": source["id"],
                        "array_index": hit["native_array_index"], "native_name": hit["native_name"],
                        "native_accession": hit["native_accession"]})
                label = hit["source_label"] or accession
                lengths = {domain["reference_length"] for domain in hit["domains"]
                    if type(domain.get("reference_length")) is int}
                if len(lengths) > 1:
                    errors.append({"native_array_index": hit["native_array_index"],
                        "code": "provider_reference_length_inconsistent_between_domains",
                        "phase": "native_hit_publication"})
                reference = self._put("reference", {"reference_type": "family" if is_profile else "protein",
                    "source_ref": source["id"], "accession": accession,
                    "label": label if len(label) <= 512 and "\n" not in label else accession,
                    "sequence_ref": None, "molecule": None if is_profile else "protein",
                    "length": next(iter(lengths)) if len(lengths) == 1 and not is_profile else None,
                    "term_refs": terms, "context_refs": []}, origin="external")
                refs += terms + [reference["id"]]
                observations, domain_publications = [], []
                for domain in hit["domains"] or [{}]:
                    try:
                        observation = self._publish_hmmer_domain(subject_ref, source, reference,
                            query_model, hit, domain, grading=grading, is_profile=is_profile)
                    except (ValueError, ContractError, KeyError, TypeError) as error:
                        errors.append({"native_array_index": hit["native_array_index"],
                            "domain_array_index": domain.get("native_array_index"),
                            "code": str(error), "phase": "native_domain_publication"})
                        continue
                    refs.append(observation["id"])
                    observations.append(observation["id"])
                    domain_publications.append({"domain_array_index": domain.get("native_array_index"),
                        "observation_ref": observation["id"]})
                records.append({"reference_ref": reference["id"], "native_index": hit["native_index"],
                    "native_array_index": hit["native_array_index"],
                    "accession": accession, "native_name": hit["native_name"],
                    "native_accession": hit["native_accession"], "provider_accession": hit["provider_accession"],
                    "linked_uniprot_accession": hit["linked_uniprot_accession"],
                    "source_label": hit["source_label"],
                    "taxon_id": hit["taxon_id"], "bitscore": hit["bitscore"], "evalue": hit["evalue"],
                    "domain_observation_refs": observations, "domain_publications": domain_publications})
            except (ValueError, ContractError, KeyError, TypeError) as error:
                errors.append({"native_index": hit.get("native_index"), "code": str(error),
                    "phase": "native_hit_publication"})
        return {"source_ref": source["id"], "job_ref": snapshot.transport["job_ref"],
            "job_id": snapshot.request["job_id"], "status": body["status"], "records": records,
            "page": snapshot.request["page"], "page_count": body["page_count"],
            "next_page": snapshot.request["page"]+1 if body["page_count"] and snapshot.request["page"] < body["page_count"] else None,
            "database": (snapshot.transport.get("job_details") or {}).get("database"),
            "native_search_stats": body["stats"], "projection_errors": errors, "functional_or_lineage_assignment": "not_performed"}, list(dict.fromkeys(self._written))

    def _publish_hmmer_domain(self, subject_ref, source, reference, query_model, hit,
                              domain, *, grading, is_profile):
        from .library.hmmer_graders import HMMER_DOMAIN_METRICS, api_domain_scores
        operand_intervals = None
        values = measurements(reference_ref=ref(reference["id"]))
        if is_profile:
            values += measurements(profile_ref=ref(reference["id"]))
        for key, value in {"bitscore": domain.get("bitscore", hit["bitscore"]),
                           "evalue": domain.get("independent_evalue", hit["evalue"])}.items():
            if value is not None:
                values += measurements(**{key: number(value)})
        if "query_interval" in domain:
            if (domain["query_length"] is not None
                    and domain["query_length"] != len(self._sequence(subject_ref))):
                raise ContractError("provider_query_length_differs_from_submitted_subject")
            values += measurements(query_start=number(domain["query_interval"][0]),
                                   query_end=number(domain["query_interval"][1]))
            operand_intervals = [{"role": "query", "subject_ref": subject_ref,
                "start": domain["query_interval"][0], "end": domain["query_interval"][1],
                "unit": self.store.subject_unit(subject_ref), "model_unit": "aa"}]
        domain_scores = api_domain_scores(grading or {},
            hit_array_index=hit["native_array_index"],
            domain_array_index=domain.get("native_array_index"), artifact_ref=source["artifact_ref"])
        values += self._grading_values(domain_scores, HMMER_DOMAIN_METRICS)
        # Preserve endpoint-span meanings, using this exact shared score row.
        # Paired coverage excludes insertion/deletion positions and is distinct.
        values += self._grading_values({
            "query_coverage": domain_scores.get("sequence_span_coverage" if is_profile else "model_span_coverage"),
            "target_coverage": domain_scores.get("model_span_coverage" if is_profile else "sequence_span_coverage"),
        }, ("query_coverage", "target_coverage"))
        return self._observation("profile_match" if is_profile else "comparison",
            [subject_ref], source, values, references=[reference["id"]],
            dependencies=[subject_ref, reference["id"], query_model["id"]], operand_intervals=operand_intervals)

