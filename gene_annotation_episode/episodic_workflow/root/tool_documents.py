"""Ordinary-tool methods: tool_documents."""
from __future__ import annotations
import asyncio
from dataclasses import replace
import json
from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.materials import artifact_path
from gene_annotation_episode.document_tools import DocumentOutput
from gene_annotation_episode.document_tools import archive_extract
from gene_annotation_episode.document_tools import archive_inventory
from gene_annotation_episode.document_tools import pdf_native
from gene_annotation_episode.spreadsheet_tools import xlsx_native
from gene_annotation_episode.image_evidence import resolve_image_input as resolve_selected_image

class ToolDocuments:
    def resolve_image_input(self, selected: dict) -> dict:
        return resolve_selected_image(self.store, selected)

    def _spreadsheet_arguments(self, name, args):
        source = self.store._require(args['source_ref'], {'source'})
        path = artifact_path(self.store, source['artifact_ref'])
        return source, path, name.rsplit('.', 1)[1], {key: value for key, value in args.items() if key != 'source_ref'}

    async def _document_async(self, name: str, args: dict) -> DocumentOutput:
        if self.store.db.in_transaction:
            raise ContractError("native_document_work_requires_no_active_store_transaction")
        if name.startswith('source.xlsx.'):
            source, path, operation, arguments = self._spreadsheet_arguments(name, args)
            member = None
        elif name == "source.archive.extract":
            member = self.store._require(args["member_ref"], {"archive_member"})
            source = self.store._require(member["source_ref"], {"source"})
            path = artifact_path(self.store, source['artifact_ref'])
        else:
            member = None
            source = self.store._require(args["source_ref"], {"source"})
            path = artifact_path(self.store, source['artifact_ref'])
        if name == "source.archive.members":
            output = await asyncio.to_thread(archive_inventory, path, offset=args.get("offset", 0), limit=args.get("limit", 50))
        elif name == "source.archive.extract":
            output = await asyncio.to_thread(archive_extract, path, member)
        elif name.startswith("source.xlsx."):
            operands = [{'role': 'input_source', 'subject_ref': source['id']}]
            try:
                output = await self._native_thread_async(xlsx_native, path, operation=operation,
                    arguments=arguments, job_limits=self.local_job_policy.to_dict(),
                    **({'statistics': self.native_statistics.for_spreadsheet(path, operation, arguments, self.local_job_policy)}
                       if self.native_statistics is not None else {}))
            except AcquisitionError as error:
                metadata = error.operational or {}
                self._record_native_execution(metadata.get('native', metadata),
                    operation='xlsx_'+operation, operands=operands)
                raise
            self._record_native_execution((output.metadata.get('local_jobs') or {}).get('work', {}),
                operation='xlsx_'+operation, operands=operands)
        else:
            operation = name.rsplit(".", 1)[1]
            if operation == "text" and args.get("last_page", args["page"]) < args["page"]:
                raise ContractError("pdf_page_range_reversed")
            output = await self._native_thread_async(pdf_native, path, operation=operation, executables=dict(self.pdf_executables),
                job_limits=self.local_job_policy.to_dict(),
                first_page=args.get("page"), last_page=args.get("last_page", args.get("page")), page=args.get("page"),
                layout=args.get("layout", "reading_order"), dpi=args.get("dpi", 150))
        output = replace(output, metadata={**output.metadata, "parent_source_ref": source["id"],
            "input_artifact_ref": source["artifact_ref"]})
        if output.metadata.get("returncode", 0) != 0:
            details = {**output.metadata,
                "stdout_ref": self.store.artifact(output.stdout, "text/plain"),
                "stderr_ref": self.store.artifact(output.stderr, "text/plain")}
            if output.content:
                details["partial_output_ref"] = self.store.artifact(output.content, output.media_type)
            raise AcquisitionError("pdf_native_error", phase="native_execution", operational={
                "native_returncode": output.metadata["returncode"],
                "native_stderr_tail": output.stderr[-4000:].decode("utf-8", errors="replace"),
                "diagnostic_ref": self.store.artifact(canonical(details), "application/json")})
        return output

    def _publish_document(self, name: str, args: dict, output: DocumentOutput) -> tuple[dict, list[str]]:
        metadata = {**output.metadata,
            "stdout_ref": self.store.artifact(output.stdout, "text/plain"),
            "stderr_ref": self.store.artifact(output.stderr, "text/plain")}
        if name.startswith("source.xlsx."):
            source = self._source_bytes(name.removeprefix('source.'), output.content,
                'application/json', metadata)
            return {**json.loads(output.content), 'source_ref': source['id'],
                'xlsx_source_ref': args['source_ref'], 'artifact_ref': source['artifact_ref'],
                'provenance': metadata, 'biological_interpretation': 'not_performed'}, [source['id']]
        if name == "source.archive.members":
            source = self._source("archive.inventory", metadata, parent_source_refs=[args["source_ref"]],
                stdout_ref=metadata["stdout_ref"], stderr_ref=metadata["stderr_ref"])
            refs, members = [source["id"]], []
            for entry in metadata["members"]:
                member = self._put("archive_member", {"source_ref": args["source_ref"],
                    "archive_format": metadata["archive_format"], **entry}, origin="tool")
                refs.append(member["id"])
                members.append(member)
            next_query = ({**args, "offset": metadata["next_offset"], "limit": metadata["limit"]}
                          if metadata["next_offset"] is not None else None)
            return {"source_ref": source["id"], "archive_source_ref": args["source_ref"],
                "members": members, **{key: metadata[key] for key in ("offset", "limit", "total", "next_offset")},
                "next_query": next_query}, refs
        if name == "source.pdf.info":
            source = self._source_bytes("poppler.pdfinfo", output.content, "text/plain", metadata)
            return {"source_ref": source["id"], "pdf_source_ref": args["source_ref"],
                "page_count": metadata.get("page_count"), "native_information": output.content.decode("utf-8"),
                "provenance": metadata}, [source["id"]]
        media_type = output.media_type
        if name == "source.archive.extract":
            if output.content.startswith(b"%PDF-"):
                media_type = "application/pdf"
            elif output.content.startswith(b"\x89PNG\r\n\x1a\n"):
                media_type = "image/png"
            elif output.content.startswith(b"\xff\xd8\xff"):
                media_type = "image/jpeg"
        if output.content is None:
            raise ContractError("native_document_output_missing")
        source = self._source_bytes("archive.member" if name == "source.archive.extract" else
            "poppler.pdftotext" if name == "source.pdf.text" else "poppler.pdftoppm",
            output.content, media_type, metadata)
        material = self.store.register_material(source_ref=source["id"], format="opaque", use="evidence")
        self._written.append(material["id"])
        transformation = "archive_member" if name == "source.archive.extract" else "pdf_text" if name == "source.pdf.text" else "pdf_page"
        page = args.get("page")
        page_range = {}
        if transformation == "pdf_text":
            page_range = {"first_page": page, "last_page": args.get("last_page", page)}
            if page_range["first_page"] != page_range["last_page"]:
                # The source's retained native selection identifies the range.
                # Do not label a multi-page derivative as one physical page.
                page = None
        derivative = self._put("source_derivative", {"source_ref": source["id"],
            "parent_source_ref": metadata["parent_source_ref"], "transformation": transformation,
            "selection_ref": args.get("member_ref"), "page": page,
            "layout": args.get("layout", "reading_order") if transformation == "pdf_text" else None,
            "dpi": args.get("dpi", 150) if transformation == "pdf_page" else None,
            "coordinate_system": "original_member_bytes" if transformation == "archive_member" else
                "normalized_utf8_bytes" if transformation == "pdf_text" else "one_based_physical_pdf_page"}, origin="tool")
        return {"source_ref": source["id"], "material_ref": material["id"], "derivation_ref": derivative["id"],
            "artifact_ref": source["artifact_ref"], "media_type": media_type,
            "image_source_ref": source["id"] if media_type.startswith("image/") else None,
            "page": page, **page_range, "coordinate_system": derivative["coordinate_system"],
            "provenance": metadata, "biological_interpretation": "not_performed"}, [source["id"], material["id"], derivative["id"]]

