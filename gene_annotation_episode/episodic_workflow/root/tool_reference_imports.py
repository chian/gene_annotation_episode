"""Original substantive ordinary-tool methods: tool_reference_imports."""
from __future__ import annotations
import json
from xml.etree.ElementTree import ParseError
from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.acquisition import article_details
from gene_annotation_episode.acquisition import parse_genbank
from gene_annotation_episode.domain import RECORD_SCHEMAS
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.domain import identity
from gene_annotation_episode.domain import validate_schema

class ToolReferenceImports:
    def _publish_ucsc_sequence_reference(self, result, source):
        """Retain the existing exact DNA import without granting its handles."""
        from gene_annotation_episode.ucsc_acquisition import ucsc_sequence_interval
        interval = ucsc_sequence_interval(result)
        if interval is None:
            return None
        # The Reference has its own local DNA axis. Its original assembly
        # interval and orientation remain in the Source and native response.
        accession = identity("ucsc_interval", {key: interval[key] for key in
            ("source_ref", "genome", "hub_url", "chrom", "start", "end", "rev_comp")})
        reference = self._put("reference", {"reference_type": "dna",
            "source_ref": source["id"], "accession": accession,
            "label": "UCSC retained DNA interval",
            "sequence_ref": self.store.artifact(interval["dna"], "text/plain"),
            "molecule": "dna", "length": interval["length"],
            "term_refs": [], "context_refs": []}, origin="external")
        return reference["id"]

    def _import(self, name: str, args: dict, snapshot: SourceSnapshot) -> tuple[dict, list[str]]:
        from gene_annotation_episode.molecular_provider_acquisition import OPERATIONS as MOLECULAR_PROVIDER_OPERATIONS, provider_result
        if name in {"public.blast.search", "public.blast.collect"}:
            return self._import_blast(snapshot)
        if name in {"public.rfam.search", "public.rfam.collect"}:
            return self._import_rfam_discovery(snapshot)
        if name == "public.ucsc.request":
            from gene_annotation_episode.ucsc_acquisition import ucsc_result
            # Original bytes and actual request custody survive a later
            # association, decoding or reference-publication failure.
            source = self._source(snapshot.service, None, snapshot=snapshot, accession=None)
            try:
                result = ucsc_result(snapshot, arguments=args, source_ref=source["id"],
                    artifact_ref=source["artifact_ref"])
            except ValueError as error:
                raise ContractError(str(error)) from error
            refs = [source["id"]]
            reference = self._publish_ucsc_sequence_reference(result, source)
            if reference is not None:
                refs.append(reference)
            return result, refs
        if name in MOLECULAR_PROVIDER_OPERATIONS:
            accession_key = {"public.kegg.reaction": "reaction_id",
                "public.reactome.record": "stable_id", "public.quickgo.term": "term_id"}.get(name)
            accession = snapshot.request.get(accession_key) if isinstance(snapshot.request, dict) else None
            source = self._source(snapshot.service, None, snapshot=snapshot,
                accession=accession if type(accession) is str else None)
            if canonical(snapshot.request) != canonical(args):
                raise ContractError("molecular_provider_selected_request_mismatch")
            return provider_result(name, snapshot, source_ref=source['id'],
                artifact_ref=source['artifact_ref']), [source['id']]
        text = None
        article = None
        if name == "public.literature.read":
            try:
                article = article_details(snapshot.content)
                paragraphs = article['sections']
            except ParseError as error:
                # A failed text projection must not discard acquired bytes.
                self._source(snapshot.service, None, snapshot=snapshot,
                             accession=args.get("pmcid"))
                raise ContractError("literature_xml_parse_failed") from error
            text = "\n\n".join(item["text"] for item in paragraphs)
        source = self._source(snapshot.service, None, snapshot=snapshot, text=text,
            accession=(args["identifier"] if name == "public.alphafold.prediction" else
                args["entry_id"] if name in {"public.rcsb.entry", "public.rcsb.file", "public.emdb.entry"}
                else args.get("accession", args.get("pmcid", args.get("rid")))),
            publication_identifiers=article['publication_identifiers'] if article is not None else None)
        refs = [source["id"]]
        if name == "public.alphafold.prediction":
            from gene_annotation_episode.alphafold_acquisition import alphafold_prediction_result
            return alphafold_prediction_result(snapshot, arguments=args, source_ref=source["id"],
                artifact_ref=source["artifact_ref"]), refs
        if name == "public.emdb.entry":
            from gene_annotation_episode.emdb_acquisition import emdb_entry_result
            return emdb_entry_result(snapshot, arguments=args, source_ref=source["id"],
                artifact_ref=source["artifact_ref"]), refs
        if name in {"public.rcsb.entry", "public.rcsb.file"}:
            from gene_annotation_episode.rcsb_acquisition import rcsb_entry_result, rcsb_file_result
            builder = rcsb_entry_result if name == "public.rcsb.entry" else rcsb_file_result
            result = builder(snapshot, arguments=args, source_ref=source["id"],
                artifact_ref=source["artifact_ref"])
            if name == "public.rcsb.file":
                refs.append(source["artifact_ref"])
            return result, refs
        if name in {"public.rhea.search", "public.rhea.reaction", "public.chebi.search", "public.chebi.compound"}:
            return self._import_chemistry(name, args, snapshot, source)
        if name in {"public.uniprot.record", "public.uniprot.search"}:
            return self._import_uniprot(name, args, snapshot, source)
        if name == "public.ncbi.sequence":
            records = []
            for sequence in parse_genbank(snapshot.content):
                molecule = "protein" if args["database"] == "protein" else "rna" if "RNA" in sequence["annotations"].get("molecule_type", "") else "dna"
                record = self._put("reference", {"reference_type": molecule, "source_ref": source["id"],
                    "accession": sequence["accession"], "label": sequence["description"],
                    "sequence_ref": self.store.artifact(sequence["sequence"], "text/plain") if sequence["sequence_available"] else None,
                    "molecule": molecule, "length": sequence["length"], "term_refs": [], "context_refs": []}, origin="external")
                refs.append(record["id"])
                records.append(record)
            return {"source_ref": source["id"], "records": records, "count": len(records),
                    "original_feature_context_in_source": True}, refs
        if name == "public.literature.read":
            metadata_issues = list(article['metadata_issues'])
            reported = [item['value'] for item in article['publication_identifiers'] if item['namespace'] == 'pmcid']
            if reported and args['pmcid'] not in reported:
                metadata_issues.append({'code': 'requested_publication_identifier_mismatch',
                    'namespace': 'pmcid', 'requested_value': args['pmcid']})
            return {"source_ref": source["id"], "text_ref": source["text_ref"], "paragraph_count": len(paragraphs),
                    'publication_identifiers': article['publication_identifiers'],
                    'metadata_issues': metadata_issues,
                    'cited_publications': article['cited_publications'],
                    'citation_meaning': 'Bibliography discovery metadata from the retained article. Read the cited source to assess its actual reported evidence and scope.',
                    "text_bytes": len(text.encode()), "text_representation": "ordered_paragraph_projection",
                    "omitted_elements_available_in_original": True,
                    "original_read_query": {"source_ref": source["id"], "representation": "original"},
                    "read_with": "source.read"}, refs
        # Search/status outputs retain provider structure and source provenance;
        # no target assertion is manufactured by these acquisitions.
        try:
            native = json.loads(snapshot.content)
        except ValueError:
            native = None
        return {"source_ref": source["id"], "provider_result": native,
                "raw_artifact_ref": source["artifact_ref"]}, refs

    def _import_uniprot(self, name, args, snapshot, source):
        """Project one retained page while preserving original native row identity."""
        from .library.uniprot_response_custody import parse_uniprot_snapshot, uniprot_page_metadata
        from gene_annotation_episode.uniprot_native import legacy_uniprot_records
        from gene_annotation_episode.uniprot_publication import bind_uniprot_publication

        operation = name.rsplit(".", 1)[1]
        request = {"operation": operation, **args,
                   **({"size": args.get("size", 10)} if operation == "search" else {})}
        result = {"source_ref": source["id"], "records": [], "count": 0,
                  "source_detail_available_through_source_read": True}
        refs = [source["id"]]
        try:
            parsed = parse_uniprot_snapshot(snapshot, request=request)
        except ValueError as error:
            # The source is already retained. A mismatched or unknown native
            # request cannot establish a bound result from otherwise valid JSON.
            result["projection_errors"] = [{"code": str(error), "record_ordinal": None,
                "pointer": "", "field": "request", "effect": "page_unusable"}]
            return result, refs
        errors = [dict(issue) for issue in parsed["issues"]
                  if issue["effect"] != "qualification"]
        release = parsed["page"]["release"]
        if release["state"] == "present" and source["version"] != release["value"]:
            result["projection_qualifications"] = [{"code": "uniprot_legacy_source_version_omitted",
                "record_ordinal": None, "pointer": release["pointer"],
                "field": "legacy_source", "effect": "qualification"}]
        by_ordinal = {}

        def projection_failure(native, pointer, code, effect="field_partial"):
            errors.append({"code": code, "record_ordinal": native["identity"]["record_ordinal"],
                "pointer": pointer, "primary_accession": native["identity"]["primary_accession"],
                "field": "legacy_publication", "effect": effect})

        def legacy_label(value, fallback, native, pointer):
            try:
                validate_schema(value, RECORD_SCHEMAS["reference"]["properties"]["label"])
            except ContractError:
                # Native text stays complete and valid in the publication. The
                # old label column has a narrower representation contract.
                projection_failure(native, pointer, "uniprot_legacy_label_unrepresentable")
                return fallback
            return value

        def legacy_term(namespace, accession, label, kind, native, pointer):
            payload = {"namespace": namespace, "accession": accession, "label": label,
                       "term_type": kind, "source_ref": source["id"], "anchor": None}
            try:
                validate_schema(payload, RECORD_SCHEMAS["term"])
            except ContractError:
                projection_failure(native, pointer, "uniprot_legacy_term_unrepresentable")
                return None
            term = self._put("term", payload, origin="external")
            refs.append(term["id"])
            return term["id"]

        for native, protein in zip(parsed["records"],
                                   legacy_uniprot_records(parsed, snapshot.content), strict=True):
            anchor = native["identity"]
            if protein["accession"] != anchor["primary_accession"]:
                raise ContractError("uniprot_legacy_record_identity_conflict")
            try:
                validate_schema(protein["accession"], RECORD_SCHEMAS["reference"]["properties"]["accession"])
            except ContractError:
                projection_failure(native, anchor["record_pointer"] + "/primaryAccession",
                                   "uniprot_legacy_reference_unrepresentable", "record_unpublishable")
                continue
            terms = []
            if protein["taxon_id"] is not None:
                taxon_id = str(protein["taxon_id"])
                label = legacy_label(protein["organism"] or taxon_id, taxon_id, native,
                                     native["taxon"]["scientific_name"]["pointer"])
                terms.append(legacy_term("ncbi_taxonomy", taxon_id, label, "taxon", native,
                                         native["taxon"]["taxon_id"]["pointer"]))
            legacy = native["legacy_publication"]
            if legacy["source_name"]:
                terms.append(legacy_term("uniprot_source_name", protein["accession"],
                    legacy["source_name"], "molecular_role", native, legacy["source_name_pointer"]))
            for ec, pointer in zip(legacy["source_ec_numbers"], legacy["source_ec_number_pointers"], strict=True):
                terms.append(legacy_term("EC", ec, "EC " + ec, "molecular_role", native, pointer))
            sequence = native["sequence"]
            sequence_ref = None
            if sequence["value"]["state"] == "present":
                sequence_bytes = sequence["value"]["value"].encode("ascii")
                sequence_ref = self.store.artifact(sequence_bytes, "text/plain")
                if self.store.get_artifact(sequence_ref) != sequence_bytes:
                    raise ContractError("uniprot_sequence_artifact_content_conflict")
            label = legacy_label(legacy["source_name"] or protein["accession"], protein["accession"],
                                 native, legacy["source_name_pointer"])
            record = self._put("reference", {"reference_type": "protein", "source_ref": source["id"],
                "accession": protein["accession"], "label": label, "sequence_ref": sequence_ref,
                "molecule": "protein", "length": sequence["observed_length_aa"],
                "term_refs": list(dict.fromkeys(term for term in terms if term is not None)),
                "context_refs": []}, origin="external")
            by_ordinal[anchor["record_ordinal"]] = record
            refs.append(record["id"])
            result["records"].append(record)
        if self.store.get_artifact(source["artifact_ref"]) != snapshot.content:
            raise ContractError("uniprot_native_artifact_content_conflict")
        for native in parsed["records"]:
            anchor = native["identity"]
            if anchor["record_ordinal"] not in by_ordinal and not any(
                    error.get("code") == "uniprot_legacy_reference_unrepresentable" and
                    error.get("effect") == "record_unpublishable" and
                    error.get("record_ordinal") == anchor["record_ordinal"] and
                    error.get("pointer") == anchor["record_pointer"] + "/primaryAccession" and
                    error.get("primary_accession") == anchor["primary_accession"] for error in errors):
                raise ContractError("uniprot_publication_omission_not_reported")
        result.update(count=len(by_ordinal), projection_errors=errors,
            uniprot_publication=bind_uniprot_publication(parsed, source_ref=source["id"],
                native_artifact_ref=source["artifact_ref"], references_by_ordinal=by_ordinal))
        if operation == "search":
            result.update(uniprot_page_metadata(parsed))
        return result, list(dict.fromkeys(refs))

