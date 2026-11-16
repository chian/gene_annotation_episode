"""Selected-source access tests; no unknown annotation/model/network claims.

Actual historical PMC bytes calibrate archive/PDF adapters. The HTTP client
below is explicitly saved replay, with a synthetic object-list protocol fixture.
"""
from __future__ import annotations


import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.literature_assets import BASE_URL, advertised_asset, parse_listing


def test_public_listing_pagination_and_exact_advertised_encoding():
    listing = b'''<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
    <Prefix>PMC12608037.1%2F</Prefix><EncodingType>url</EncodingType><IsTruncated>true</IsTruncated>
    <NextContinuationToken>opaque+token/==</NextContinuationToken>
    <Contents><Key>PMC12608037.1%2Fsource%20file.pdf</Key><Size>42</Size><ETag>"multipart-2"</ETag></Contents>
    </ListBucketResult>'''
    page = parse_listing(listing)
    assert page["prefix"] == "PMC12608037.1/"
    assert page["objects"][0]["key"] == "PMC12608037.1/source file.pdf"
    assert page["next_continuation_token"] == "opaque+token/==" and page["truncated"] is True
    parsed = advertised_asset("s3://pmc-oa-opendata/PMC12608037.1/source%20file.pdf?md5=" + "a"*32, prefix=page["prefix"])
    assert parsed["https_uri"] == BASE_URL + "PMC12608037.1/source%20file.pdf?md5=" + "a"*32
    assert parsed["advertised_md5"] == "a"*32
    with pytest.raises(ContractError, match="invalid_xml"):
        parse_listing(b"<ListBucketResult>broken")


