"""Bounded source-only acquisition for the demonstrated info wrapping defect."""
import hashlib
import json
import os
from pathlib import Path
import tarfile
import urllib.request

BASE = "https://ftp.ncbi.nlm.nih.gov/blast/executables/blast+/2.17.0/"
NAME = "ncbi-blast-2.17.0+-src.tar.gz"
SELECTED = {
    "c++/src/app/blastvdb/blast_vdb_cmd.cpp",
    "c++/src/corelib/ncbistr.cpp",
    "c++/include/corelib/ncbistr.hpp",
    "c++/src/algo/blast/vdb/vdbalias.cpp",
    "c++/include/algo/blast/vdb/vdbalias.hpp",
    "c++/include/algo/blast/api/version.hpp",
}

def test_collect_release_source():
    destination = Path(os.environ["HMMER529_ATTEMPT"]) / "release_source"
    destination.mkdir()
    records = []
    for name, limit in [(NAME + ".md5", 4096), (NAME, 40 * 1024 * 1024)]:
        out = destination / name
        size = 0
        with urllib.request.urlopen(BASE + name, timeout=60) as source, out.open("xb") as sink:
            headers = dict(source.headers)
            while block := source.read(1024 * 1024):
                size += len(block)
                assert size <= limit
                sink.write(block)
        raw = out.read_bytes()
        records.append({"url": BASE + name, "path": str(out), "size_bytes": size,
            "sha256": hashlib.sha256(raw).hexdigest(), "headers": headers})
    expected = (destination / (NAME + ".md5")).read_text().split()[0]
    assert hashlib.md5((destination / NAME).read_bytes()).hexdigest() == expected
    members = []
    observed = set()
    with tarfile.open(destination / NAME, "r:gz") as archive:
        for member in archive:
            relative = member.name.removeprefix("ncbi-blast-2.17.0+-src/")
            if relative not in SELECTED:
                continue
            assert member.isfile() and member.size < 1024 * 1024
            assert relative not in observed
            observed.add(relative)
            data = archive.extractfile(member).read()
            out = destination / relative
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(data)
            members.append({"archive_member": member.name, "path": str(out),
                "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    (destination / "SOURCE_MANIFEST.json").write_text(json.dumps({
        "source_only": True, "native_helper_executions": 0,
        "requests": records, "selected_members": members,
        "absent_selected_members": sorted(SELECTED - observed),
        "archive_md5_matches_official_sidecar": True,
        "binary_build_equivalence": "not established by source acquisition"
    }, indent=2) + "\n")
    assert {"c++/src/app/blastvdb/blast_vdb_cmd.cpp", "c++/src/corelib/ncbistr.cpp",
        "c++/include/corelib/ncbistr.hpp"} <= observed


def test_extract_resolution_sources():
    snapshot = Path(__file__).resolve().parents[2]
    archive_path = snapshot / "verification/tool_graders_hmmer_map_verification_2026-10-28_529/check141_vdb_info_source678/release_source" / NAME
    assert hashlib.sha256(archive_path.read_bytes()).hexdigest() == "502057a88e9990e34e62758be21ea474cc0ad68d6a63a2e37b2372af1e5ea147"
    selected = {
        "c++/src/objtools/blast/seqdb_reader/seqdbcommon.cpp",
        "c++/src/algo/blast/vdb/vdb2blast_util.cpp",
        "c++/src/corelib/ncbifile.cpp",
        "c++/include/corelib/ncbifile.hpp",
    }
    destination = Path(os.environ["HMMER529_ATTEMPT"]) / "resolution_sources"
    destination.mkdir()
    members = []
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive:
            relative = member.name.removeprefix("ncbi-blast-2.17.0+-src/")
            if relative not in selected:
                continue
            assert member.isfile() and member.size < 1024 * 1024
            data = archive.extractfile(member).read()
            out = destination / relative
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(data)
            members.append({"archive_member": member.name, "path": str(out),
                "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    (destination / "SOURCE_MANIFEST.json").write_text(json.dumps({
        "source_only": True, "native_helper_executions": 0, "network_requests": 0,
        "archive_sha256": "502057a88e9990e34e62758be21ea474cc0ad68d6a63a2e37b2372af1e5ea147",
        "selected_members": members,
    }, indent=2) + "\n")
    assert len(members) == len(selected)
