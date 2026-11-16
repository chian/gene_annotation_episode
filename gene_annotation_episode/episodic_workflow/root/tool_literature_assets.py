"""Ordinary-tool methods: tool_literature_assets."""
from __future__ import annotations
from dataclasses import replace
import json
import hashlib
from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.literature_assets import PmcFiles
from gene_annotation_episode.literature_assets import advertised_asset
from gene_annotation_episode.literature_assets import metadata_assets
from gene_annotation_episode.literature_assets import parse_listing
from gene_annotation_episode.literature_assets import version as pmc_version

class ToolLiteratureAssets:
    def _publish_pmc_versions(self, args: dict, snapshot: SourceSnapshot) -> tuple[dict, list[str]]:
        source = self._source(snapshot.service, None, snapshot=snapshot, accession=args["pmcid"])
        refs, versions = [source["id"]], []
        page = parse_listing(snapshot.content)
        if page["prefix"] != args["pmcid"] + ".":
            raise ContractError("pmc_version_listing_scope_mismatch")
        for prefix in page["version_prefixes"]:
            selected = self._put("pmc_version", {"source_ref": source["id"],
                **pmc_version(prefix, pmcid=args["pmcid"])}, origin="external")
            refs.append(selected["id"])
            versions.append(selected)
        return {"source_ref": source["id"], "versions": versions,
            "next_continuation_token": page["next_continuation_token"], "listing_complete": not page["truncated"],
            "version_preference": "not_assigned",
            "next_query": {"pmcid": args["pmcid"], "continuation_token": page["next_continuation_token"]}
                if page["next_continuation_token"] else None}, refs

    def _publish_pmc_files(self, args: dict, snapshots: PmcFiles) -> tuple[dict, list[str]]:
        selected = self.store._require(args["version_ref"], {"pmc_version"})
        listing = self._source(snapshots.listing.service, None, snapshot=snapshots.listing,
                               parent_source_refs=[selected["source_ref"]])
        refs, objects, assets = [listing["id"]], [], []
        page = parse_listing(snapshots.listing.content)
        if page["prefix"] != selected["prefix"]:
            raise ContractError("pmc_file_listing_scope_mismatch")
        for item in page["objects"]:
            record = self._put("pmc_object", {"source_ref": listing["id"], "version_ref": selected["id"],
                "object_key": item["key"], **{key: item[key] for key in ("size", "etag", "last_modified")}}, origin="external")
            refs.append(record["id"])
            objects.append(record)
        metadata = None
        if snapshots.metadata is not None:
            metadata = self._source(snapshots.metadata.service, None, snapshot=snapshots.metadata,
                                    parent_source_refs=[listing["id"]])
            refs.append(metadata["id"])
        catalog = self._put("pmc_catalog", {"source_ref": listing["id"], "version_ref": selected["id"],
            "metadata_source_ref": metadata["id"] if metadata else None,
            "listing_complete": not page["truncated"], "next_continuation_token": page["next_continuation_token"]}, origin="tool")
        refs.append(catalog["id"])
        body = {"source_ref": listing["id"], "catalog_ref": catalog["id"], "version_ref": selected["id"],
            "objects": objects, "assets": assets, "metadata_source_ref": metadata["id"] if metadata else None,
            "listing_complete": not page["truncated"], "next_continuation_token": page["next_continuation_token"],
            "next_query": {"version_ref": selected["id"], "continuation_token": page["next_continuation_token"]}
                if page["next_continuation_token"] else None}
        if metadata is None:
            return body, refs
        try:
            native = json.loads(snapshots.metadata.content)
            advertisements = metadata_assets(native, selected)
            errors = []
            for kind, field, uri in advertisements:
                try:
                    actual = advertised_asset(uri, prefix=selected["prefix"])
                    record = self._put("pmc_asset", {"source_ref": metadata["id"], "catalog_ref": catalog["id"],
                        "version_ref": selected["id"], "asset_kind": kind, "metadata_field": field, **actual}, origin="external")
                    refs.append(record["id"])
                    assets.append(record)
                except ContractError as error:
                    errors.append({"metadata_field": field, "code": str(error)})
            body["article_metadata"] = native
            if errors:
                body["representation_feedback"] = {"category": "representation", "code": "pmc_partial_asset_advertisements", "fields": errors}
        except (ValueError, UnicodeError) as error:
            body["representation_feedback"] = {"category": "representation", "code": str(error) if isinstance(error, ContractError) else "pmc_metadata_invalid_json"}
        return body, refs

    def _publish_pmc_asset(self, args: dict, snapshot: SourceSnapshot) -> tuple[dict, list[str]]:
        advertisement = self.store._require(args["asset_ref"], {"pmc_asset", "pmc_object"})
        snapshot = replace(snapshot, request={**snapshot.request,
            "selected_asset_ref": advertisement["id"], "selected_version_ref": advertisement["version_ref"]})
        source = self._source(snapshot.service, None, snapshot=snapshot,
                              parent_source_refs=[advertisement["source_ref"]])
        # Keep the actual HTTP Content-Type (generic public binary types are
        # honest); selected archive/PDF adapters inspect the actual bytes.
        material = self.store.register_material(source_ref=source["id"], format="opaque", use="evidence")
        self._written.append(material["id"])
        md5 = hashlib.md5(snapshot.content).hexdigest()
        advertised_md5 = advertisement.get("advertised_md5")
        body = {"source_ref": source["id"], "material_ref": material["id"], "asset_ref": advertisement["id"],
            "artifact_ref": source["artifact_ref"], "actual_sha256": snapshot.sha256, "actual_md5": md5,
            "advertised_md5": advertised_md5, "advertised_md5_matches": md5 == advertised_md5 if advertised_md5 else None,
            "original_advertisement": advertisement, "target_binding_changed": False}
        if advertised_md5 is not None and md5 != advertised_md5:
            body["representation_feedback"] = {"category": "provenance", "code": "advertised_checksum_differs_from_actual_bytes",
                "actual_source_retained": True, "source_ref": source["id"]}
        return body, [source["id"], material["id"]]

