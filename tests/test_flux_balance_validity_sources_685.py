"""685 bounded source acquisition only; no solver import, build, or invocation."""
from pathlib import Path
import hashlib
import json
import os
import tarfile
import urllib.request


def test_acquire_glpk_5_0_primary_source():
    import pytest

    selected = os.environ.get("HMMER529_ATTEMPT")
    if not selected or Path(selected).name != "check148_validity685":
        pytest.skip("Source acquisition requires the explicit original 685 bounded attempt")
    attempt = Path(selected)
    request = json.loads((attempt / "selected_request.json").read_text())
    if request["tests"] != ["test_flux_balance_validity_sources_685.py"]:
        pytest.skip("No implicit source downloads in other selected test sets")
    assert request["policy"] == {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296}
    assert request["swap_bytes"] == 0
    target = attempt / "temporary" / "validity685_sources"
    target.mkdir(exist_ok=False)
    url = "https://ftp.gnu.org/gnu/glpk/glpk-5.0.tar.gz"
    archive = target / "glpk-5.0.tar.gz"
    maximum_download = 64 * 1024 * 1024
    with urllib.request.urlopen(url) as response, archive.open("xb") as stream:
        headers = dict(response.headers.items())
        final_url = response.url
        size = 0
        while block := response.read(1024 * 1024):
            size += len(block)
            assert size <= maximum_download, "source_download_byte_limit"
            stream.write(block)
    retained = []
    with tarfile.open(archive, mode="r:gz") as bundle:
        members = bundle.getmembers()
        listing = [{"name": x.name, "size_bytes": x.size, "regular": x.isfile()} for x in members]
        for member in members:
            name = Path(member.name)
            assert name.parts[0] == "glpk-5.0" and ".." not in name.parts
            selected = (
                str(name).startswith("glpk-5.0/src/")
                or str(name).startswith("glpk-5.0/doc/")
                or name.name in {"README", "NEWS", "AUTHORS", "COPYING", "configure.ac"}
            )
            if not selected or not member.isfile():
                continue
            destination = target / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            raw = bundle.extractfile(member).read()
            assert len(raw) == member.size
            destination.write_bytes(raw)
            retained.append({"relative_path": str(name), "size_bytes": len(raw),
                             "sha256": hashlib.sha256(raw).hexdigest()})
    (target / "ARCHIVE_MEMBERS.json").write_text(json.dumps(listing, indent=2) + "\n")
    receipt = {"purpose": "primary_source_acquisition_only", "url": url,
               "final_url": final_url, "response_headers": headers,
               "archive_size_bytes": size,
               "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
               "retained": retained, "native_imports": [], "solver_calls": 0,
               "native_helpers": [], "installations": []}
    (target / "ACQUISITION.json").write_text(json.dumps(receipt, indent=2) + "\n")
    assert (target / "glpk-5.0/src/glpk.h").is_file()
    assert (target / "glpk-5.0/src/draft/glpapi06.c").is_file()
