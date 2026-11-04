"""Source-bound public PMC catalogs; no preferred version or file guessing."""
from __future__ import annotations

from dataclasses import dataclass
import re
from urllib.parse import parse_qs, quote, unquote, urlparse
from xml.etree import ElementTree

from .acquisition import AcquisitionError, SourceSnapshot
from .domain import ContractError

VERSION = "pmc_cloud_advertised_assets_v1"
BASE_URL = "https://pmc-oa-opendata.s3.amazonaws.com/"
BUCKET = "pmc-oa-opendata"
PMCID = re.compile(r"^PMC[0-9]+$")
PREFIX = re.compile(r"^(PMC[0-9]+)\.([1-9][0-9]*)/$")


@dataclass(frozen=True)
class PmcFiles:
    listing: SourceSnapshot
    metadata: SourceSnapshot | None = None
    error: AcquisitionError | None = None


def parse_listing(content: bytes) -> dict:
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError as error:
        raise ContractError("pmc_listing_invalid_xml") from error
    def text(parent, name):
        found = parent.find("{*}" + name)
        return found.text if found is not None else None
    if root.tag.split("}")[-1] != "ListBucketResult":
        raise ContractError("pmc_bucket_listing_required")
    encoded = text(root, "EncodingType") == "url"
    decode = unquote if encoded else lambda value: value
    prefixes = [decode(text(row, "Prefix")) for row in root.findall("{*}CommonPrefixes")]
    objects = []
    try:
        for row in root.findall("{*}Contents"):
            objects.append({"key": decode(text(row, "Key")), "size": int(text(row, "Size")),
                "etag": text(row, "ETag"), "last_modified": text(row, "LastModified")})
        truncated = text(root, "IsTruncated")
        if truncated not in {"true", "false"}:
            raise ValueError
    except (ValueError, TypeError) as error:
        raise ContractError("pmc_listing_invalid_fields") from error
    return {"prefix": decode(text(root, "Prefix") or ""), "version_prefixes": prefixes,
        "objects": objects, "truncated": truncated == "true",
        "next_continuation_token": text(root, "NextContinuationToken")}


def version(prefix: str, *, pmcid: str | None = None) -> dict:
    match = PREFIX.fullmatch(prefix)
    if not match or (pmcid is not None and match.group(1) != pmcid):
        raise ContractError("pmc_version_prefix_mismatch")
    return {"pmcid": match.group(1), "version": int(match.group(2)), "prefix": prefix}


def advertised_asset(uri: str, *, prefix: str) -> dict:
    if not isinstance(uri, str):
        raise ContractError("pmc_advertised_asset_uri_required")
    parsed = urlparse(uri)
    if (parsed.scheme == "s3" and parsed.netloc == BUCKET):
        key = unquote(parsed.path.lstrip("/"))
    elif parsed.scheme == "https" and parsed.netloc == "pmc-oa-opendata.s3.amazonaws.com":
        key = unquote(parsed.path.lstrip("/"))
    else:
        raise ContractError("pmc_advertised_asset_outside_public_bucket")
    if not key.startswith(prefix) or key == prefix:
        raise ContractError("pmc_advertised_asset_version_mismatch")
    values = parse_qs(parsed.query, keep_blank_values=True)
    md5 = values.get("md5", [None])
    if len(md5) != 1 or (md5[0] is not None and not re.fullmatch(r"[a-fA-F0-9]{32}", md5[0])):
        raise ContractError("pmc_advertised_checksum_invalid")
    return {"object_key": key, "original_uri": uri,
        "https_uri": BASE_URL + quote(key, safe="/") + ("?" + parsed.query if parsed.query else ""),
        "advertised_md5": md5[0].lower() if md5[0] else None}


def metadata_assets(body: dict, selected: dict):
    if not isinstance(body, dict) or body.get("pmcid") != selected["pmcid"] or body.get("version") != selected["version"]:
        raise ContractError("pmc_metadata_version_identity_mismatch")
    # Preserve independent advertisements if another field is malformed.
    for kind, field in (("xml", "xml_url"), ("text", "text_url"), ("pdf", "pdf_url")):
        if body.get(field):
            yield kind, field, body[field]
    media = body.get("media_urls") or []
    if not isinstance(media, list):
        raise ContractError("pmc_metadata_media_list_required")
    for index, uri in enumerate(media):
        yield "media", f"media_urls[{index}]", uri
