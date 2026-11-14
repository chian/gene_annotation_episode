"""Original substantive ordinary-tool methods: tool_chemistry_results."""
from __future__ import annotations
from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.library.chemistry import accession as chemical_accession
from gene_annotation_episode.episodic_workflow.root.library.chemistry import rhea_response
from gene_annotation_episode.episodic_workflow.root.library.chemistry import rhea_row
from gene_annotation_episode.episodic_workflow.root.library.chemistry import chebi_response
from gene_annotation_episode.episodic_workflow.root.library.chemistry import chemical_row

class ToolChemistryResults:
    def _chemistry_reference(self, kind: str, accession: str, source: dict,
                             *, native_record_ref: str | None = None) -> dict:
        record = {"reference_type": kind, "source_ref": source["id"], "accession": accession,
            "label": accession, "sequence_ref": None, "molecule": None, "length": None,
            "term_refs": [], "context_refs": []}
        if native_record_ref is not None:
            record["native_record_ref"] = native_record_ref
        return self._put("reference", record, origin="external")

    def _import_chemistry(self, name: str, args: dict, snapshot: SourceSnapshot,
                          source: dict) -> tuple[dict, list[str]]:
        is_rhea = name.startswith("public.rhea.")
        search = name.endswith("search")
        body = rhea_response(snapshot.content) if is_rhea else chebi_response(snapshot.content, search=search)
        rows = body["results"] if is_rhea or search else [body]
        references, errors, refs = [], [], [source["id"]]
        for index, native in enumerate(rows):
            before = len(self._written)
            try:
                if is_rhea:
                    details = rhea_row(native)
                    participants = []
                    for participant in details["participants"]:
                        # This is the actual Rhea participant identity, not a
                        # silently fetched ChEBI record or a substrate verdict.
                        chemical = self._chemistry_reference("chemical", participant["source_accession"], source)
                        participants.append({**participant, "chemical_ref": chemical["id"]})
                    details["participants"] = participants
                    details = self._put("reaction_record", {**details, "source_ref": source["id"]}, origin="external")
                    reference = self._chemistry_reference("reaction", details["accession"], source,
                                                          native_record_ref=details["id"])
                    preview = {"source_equation_preview": details["source_equation"][:240],
                        "equation_preview_complete": len(details["source_equation"]) <= 240,
                        "source_direction": details["source_direction"], "participant_count": len(participants)}
                else:
                    details = self._put("chemical_record", {**chemical_row(native, search=search),
                        "source_ref": source["id"]}, origin="external")
                    reference = self._chemistry_reference("chemical", details["accession"], source,
                                                          native_record_ref=details["id"])
                    preview = {"source_name_preview": details["source_name"][:160],
                        "name_preview_complete": len(details["source_name"]) <= 160,
                        "representation": details["representation"], "formula": details["formula"],
                        "charge": details["charge"], "ontology_relation_count": len(details["ontology_relations"])}
                references.append({"reference_ref": reference["id"], "native_record_ref": details["id"],
                                   "accession": details["accession"], **preview})
            except (ContractError, ValueError, KeyError, TypeError) as error:
                errors.append({"row_index": index, "code": str(error) if isinstance(error, ContractError)
                    else "missing_native_field" if isinstance(error, KeyError) else "invalid_native_row",
                    **({"missing_field": str(error.args[0])} if isinstance(error, KeyError) else {}),
                    **({"detail": error.detail} if isinstance(error, ContractError) and error.detail else {})})
            refs.extend(self._written[before:])
        result = {"source_ref": source["id"], "records": references[:6], "preview_limit": 6,
            "projected_record_count": len(references), "provider_returned_row_count": len(rows),
            "more_records_available_through_state_query": len(references) > 6,
            "details_query": {"kind": "reaction_record" if is_rhea else "chemical_record",
                              "references": [source["id"]], "limit": 6},
            "complete_source_read_query": {"source_ref": source["id"], "representation": "original"},
            "projection_errors": errors, "target_annotation": "not_performed",
            "thermodynamics_or_physiological_flux": "not_inferred"}
        if is_rhea:
            result.update(native_count=body.get("count"),
                result_scope="provider_limited_json_search_not_exhaustive_absence",
                direction_scope="json_search_master_records_directional_variants_not_resolved")
        elif search:
            page = args.get("page", 1)
            pages = body.get("number_pages")
            result.update(native_total=body.get("total"), native_page_count=pages, page=page,
                next_query={"term": args["term"], "size": args.get("size", 10), "page": page+1}
                    if type(pages) is int and page < pages else None)
        if not search:
            database = "RHEA" if is_rhea else "CHEBI"
            requested = chemical_accession(args["accession"], database)
            result.update(requested_accession=requested,
                returned_accessions=[row["accession"] for row in references],
                exact_accession_match=any(row["accession"] == requested for row in references),
                lookup_outcome=("returned_source_records" if references else
                                "source_records_not_projected" if rows else "no_search_match"))
        return result, list(dict.fromkeys(refs))
