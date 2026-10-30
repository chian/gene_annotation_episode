"""Acquire selected primary mask-format specifications under the bounded runner.

These are upstream reference sources, not proof of the installed native build.
No application, scientific parser, native command or database search is invoked.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE = "https://raw.githubusercontent.com/ncbi/ncbi-cxx-toolkit-public/main/"
SOURCES = {
    "mask_writer.cpp": "src/objtools/seqmasks_io/mask_writer_blastdb_maskinfo.cpp",
    "mask_writer.hpp": "include/objtools/seqmasks_io/mask_writer_blastdb_maskinfo.hpp",
    "blastdb.asn": "src/objects/blastdb/blastdb.asn",
    "seqloc.asn": "src/objects/seqloc/seqloc.asn",
    "general.asn": "src/objects/general/general.asn",
    "binary_writer.cpp": "src/serial/objostrasnb.cpp",
    "binary_reader.cpp": "src/serial/objistrasnb.cpp",
}
MAX_SOURCE_BYTES = 4 * 1024 * 1024


def test_acquire_primary_maskinfo_specifications(tmp_path):
    directory = tmp_path / "primary-specifications"
    directory.mkdir()

    def fetch(item):
        name, relative = item
        url = BASE + relative
        report = {"name": name, "url": url, "status": None, "error": None}
        request = Request(url, headers={"User-Agent": "gene-annotation-format-verification"})
        try:
            with urlopen(request) as response:
                report.update(status=response.status, final_url=response.url,
                              content_type=response.headers.get("Content-Type"),
                              etag=response.headers.get("ETag"),
                              last_modified=response.headers.get("Last-Modified"))
                body = response.read(MAX_SOURCE_BYTES + 1)
        except HTTPError as error:
            report.update(status=error.code, error="http_error")
            body = error.read(MAX_SOURCE_BYTES + 1)
        except (URLError, OSError) as error:
            report.update(error=type(error).__name__, detail=str(error))
            body = b""
        report["complete_capture"] = len(body) <= MAX_SOURCE_BYTES
        if not report["complete_capture"]:
            report["error"] = "selected_source_size_limit"
        destination = directory / name
        destination.write_bytes(body)
        report.update(path=str(destination), size_bytes=len(body),
                      sha256=hashlib.sha256(body).hexdigest())
        return report

    with ThreadPoolExecutor(max_workers=len(SOURCES)) as pool:
        reports = list(pool.map(fetch, SOURCES.items()))
    (directory / "ACQUISITION.json").write_text(json.dumps({
        "purpose": "Exact primary reference sources for binary mask decoding and stream framing.",
        "source_build_relationship": "Upstream main; not established as installed executable build source.",
        "records": reports,
    }, indent=2) + "\n")
    assert all(row["status"] == 200 and row["complete_capture"] and not row["error"]
               for row in reports), reports
    assert b"Blast-db-mask-info" in (directory / "blastdb.asn").read_bytes()
    assert b"CMaskWriterBlastDbMaskInfo" in (directory / "mask_writer.cpp").read_bytes()
