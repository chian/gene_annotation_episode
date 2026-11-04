"""Bounded IQ-TREE asset acquisition, plus pure hostile-archive controls.

Acquisition retains one selected official archive and measured executable. It
does not execute bytes, publish a Source or establish scientific inference.
"""
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tarfile
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit

import pytest

from test_muscle_resource_provisioning import (
    POLICY, REDIRECT_HOSTS, _bounded_gzip_tar, _elf64_x86_metadata,
    _pin, _retained_http, _selected_tar_bytes, _selection, _write_bytes, _write_json,
)


RELEASE = dict(tag="v2.4.0", name="iqtree-2.4.0-Linux-intel.tar.gz",
    url="https://github.com/iqtree/iqtree2/releases/download/v2.4.0/iqtree-2.4.0-Linux-intel.tar.gz",
    official_download_page="https://iqtree.github.io/",
    release_page="https://github.com/iqtree/iqtree2/releases/tag/v2.4.0",
    asset_listing="https://github.com/iqtree/iqtree2/releases/expanded_assets/v2.4.0",
    displayed_asset_size="4.55 MB", expected_size_bytes=None, publisher_digest=None,
    selected_member="iqtree-2.4.0-Linux-intel/bin/iqtree2")
MAX_COMPRESSED_BYTES = 12 * 1024**2
MAX_EXPANDED_BYTES = 128 * 1024**2
MAX_BINARY_BYTES = 64 * 1024**2
MAX_MEMBERS = 128
ACQUIRE_GATE = "HMMER_NATIVE_ORACLE_IQTREE_V2_4_0_ACQUIRE_JSON"
VERSION_GATE = "HMMER_NATIVE_ORACLE_IQTREE_V2_4_0_VERSION_JSON"


def _archive(rows):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        for name, data, type in rows:
            item = tarfile.TarInfo(name)
            item.type = type
            item.size = len(data) if type == tarfile.REGTYPE else 0
            if type in (tarfile.SYMTYPE, tarfile.LNKTYPE):
                item.linkname = "elsewhere"
            archive.addfile(item, io.BytesIO(data) if item.isfile() else None)
    return gzip.compress(buffer.getvalue(), mtime=0)


def test_archive_exact_regular_member_inventory_and_bytes():
    raw = _archive([("package/bin/tool", b"selected", tarfile.REGTYPE), ("package/", b"", tarfile.DIRTYPE)])
    decoded, inventory = _bounded_gzip_tar(raw, max_expanded_bytes=65536, max_members=10)
    assert inventory["all_member_headers_read"] and inventory["validation_issues"] == []
    assert [row["canonical_name"] for row in inventory["members"]] == ["package/bin/tool", "package"]
    assert _selected_tar_bytes(decoded, inventory, "package/bin/tool", max_bytes=100) == b"selected"


@pytest.mark.parametrize("name", ["/absolute", "../escape", "a/../escape", "a//b", "a\\b"])
def test_archive_rejects_unsafe_paths_before_any_extraction(name):
    raw = _archive([(name, b"data", tarfile.REGTYPE)])
    decoded, inventory = _bounded_gzip_tar(raw, max_expanded_bytes=65536, max_members=10)
    assert inventory["members"][0]["name"] == name
    assert inventory["validation_issues"]
    with pytest.raises(ValueError, match="inventory_invalid"):
        _selected_tar_bytes(decoded, inventory, name, max_bytes=100)


@pytest.mark.parametrize("type", [tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE, tarfile.BLKTYPE, tarfile.FIFOTYPE])
def test_archive_rejects_links_and_special_files(type):
    decoded, inventory = _bounded_gzip_tar(_archive([("member", b"", type)]), max_expanded_bytes=65536, max_members=10)
    assert any(row["code"] == "archive_member_type_invalid" for row in inventory["validation_issues"])
    with pytest.raises(ValueError, match="inventory_invalid"):
        _selected_tar_bytes(decoded, inventory, "member", max_bytes=100)


def test_archive_duplicate_member_is_never_selected_by_first_match():
    raw = _archive([("package/tool", b"first", tarfile.REGTYPE), ("./package/tool", b"second", tarfile.REGTYPE)])
    decoded, inventory = _bounded_gzip_tar(raw, max_expanded_bytes=65536, max_members=10)
    assert len(inventory["members"]) == 2 and inventory["validation_issues"]
    with pytest.raises(ValueError, match="inventory_invalid"):
        _selected_tar_bytes(decoded, inventory, "package/tool", max_bytes=100)


@pytest.mark.parametrize("case", ["expanded", "concatenated", "trailing_tar_bytes"])
def test_archive_expansion_and_concatenated_gzip_are_bounded(case):
    raw = _archive([("package/tool", b"data", tarfile.REGTYPE)])
    if case == "concatenated":
        raw += gzip.compress(b"hidden", mtime=0)
    if case == "trailing_tar_bytes":
        decoded, inventory = _bounded_gzip_tar(gzip.compress(gzip.decompress(raw) + b"hidden", mtime=0),
            max_expanded_bytes=65536, max_members=10)
        with pytest.raises(ValueError, match="inventory_invalid"):
            _selected_tar_bytes(decoded, inventory, "package/tool", max_bytes=100)
        return
    with pytest.raises(ValueError, match="archive_"):
        _bounded_gzip_tar(raw, max_expanded_bytes=100 if case == "expanded" else 65536, max_members=10)


def test_archive_member_count_is_bounded():
    raw = _archive([("one", b"1", tarfile.REGTYPE), ("two", b"2", tarfile.REGTYPE)])
    with pytest.raises(ValueError, match="member_count_limit"):
        _bounded_gzip_tar(raw, max_expanded_bytes=65536, max_members=1)


def test_archive_selected_binary_size_is_bounded():
    decoded, inventory = _bounded_gzip_tar(_archive([("tool", b"large", tarfile.REGTYPE)]),
        max_expanded_bytes=65536, max_members=10)
    with pytest.raises(ValueError, match="selected_archive_member_invalid"):
        _selected_tar_bytes(decoded, inventory, "tool", max_bytes=2)


def test_acquire_official_iqtree_v2_4_0_linux_archive_without_execution():
    attempt, request, selected = _selection(ACQUIRE_GATE, fields=("enabled", "timeout_seconds"),
        test_file="test_iqtree_resource_provisioning.py")
    assert selected["enabled"] is True and type(selected["timeout_seconds"]) is int and selected["timeout_seconds"] > 0
    directory = attempt / "iqtree-v2.4.0-acquisition"
    directory.mkdir(mode=0o700, exist_ok=False)
    proof = dict(version="iqtree_resource_acquisition_proof_v1", release=RELEASE, requested_policy=POLICY,
        swap_bytes=request["swap_bytes"], max_compressed_bytes=MAX_COMPRESSED_BYTES,
        max_expanded_bytes=MAX_EXPANDED_BYTES, max_binary_bytes=MAX_BINARY_BYTES, max_members=MAX_MEMBERS,
        timeout_seconds=selected["timeout_seconds"], redirect_policy=dict(automatic_redirects=False,
            maximum_explicit_redirects=1, allowed_https_hosts=list(REDIRECT_HOSTS)), exchanges=[],
        archive=None, decoded_tar=None, tar_inventory=None, selected_member=None, executable=None,
        elf=None, archive_companion_libraries=[], unresolved_needed_libraries=[], acquisition_verified=False,
        failure=None, native_process_calls=0, version_verified=False, inference_execution_verified=False)
    _write_json(directory / "prepared.json", proof)
    from gene_annotation_episode.acquisition import PublicClients

    client = PublicClients(ncbi_email=None, timeout=selected["timeout_seconds"], access_dir=directory / "http-access")
    try:
        exchange, snapshot = _retained_http(client, RELEASE["url"], directory, 0, selected["timeout_seconds"],
            service="iqtree_release_software", max_bytes=MAX_COMPRESSED_BYTES)
        proof["exchanges"].append(exchange)
        if snapshot is None:
            raise ValueError("original_asset_response_unavailable")
        status = snapshot.transport.get("status")
        if status == 302:
            if (exchange["failure"] is None or exchange["failure"].get("code") != "provider_http_302"
                    or snapshot.transport.get("body_complete") is not True):
                raise ValueError("original_asset_redirect_capture_conflict")
            locations = [value for key, value in snapshot.transport["header_items"] if key.lower() == "location"]
            if len(locations) != 1:
                raise ValueError("original_asset_redirect_location_conflict")
            location = locations[0]
            parsed = urlsplit(location)
            if (parsed.scheme != "https" or parsed.hostname not in REDIRECT_HOSTS
                    or parsed.username is not None or parsed.password is not None
                    or parsed.port not in (None, 443) or parsed.fragment):
                raise ValueError("original_asset_redirect_not_allowed")
            proof["route"] = "one_explicit_official_asset_redirect"
            exchange, snapshot = _retained_http(client, location, directory, 1, selected["timeout_seconds"],
                service="iqtree_release_software", max_bytes=MAX_COMPRESSED_BYTES)
            proof["exchanges"].append(exchange)
        elif status == 200:
            proof["route"] = "direct_original_asset_response"
        else:
            raise ValueError("original_asset_http_status_not_selected")
        if snapshot is None or snapshot.transport.get("status") != 200 or exchange["failure"] is not None:
            raise ValueError("selected_asset_response_failed")
        raw, transport = snapshot.content, snapshot.transport
        if (transport.get("body_complete") is not True or transport.get("observed_body_bytes") != len(raw)
                or transport.get("retained_body_bytes") != len(raw) or not 0 < len(raw) <= MAX_COMPRESSED_BYTES):
            raise ValueError("selected_asset_byte_count_or_extent_conflict")
        proof["archive"] = _write_bytes(directory / RELEASE["name"], raw)
        decoded, inventory = _bounded_gzip_tar(raw, max_expanded_bytes=MAX_EXPANDED_BYTES, max_members=MAX_MEMBERS)
        proof["decoded_tar"] = _write_bytes(directory / "archive.decoded.tar", decoded)
        _write_json(directory / "TAR_INVENTORY.json", inventory)
        proof["tar_inventory"] = dict(member_count=len(inventory["members"]),
            file=_pin(directory / "TAR_INVENTORY.json"),
            all_member_headers_read=inventory["all_member_headers_read"], validation_issues=inventory["validation_issues"],
            decoded_size_bytes=inventory["decoded_size_bytes"], member_content_size_bytes=inventory["member_content_size_bytes"])
        executable = _selected_tar_bytes(decoded, inventory, RELEASE["selected_member"], max_bytes=MAX_BINARY_BYTES)
        proof["selected_member"] = dict(name=RELEASE["selected_member"], sha256=hashlib.sha256(executable).hexdigest(), size_bytes=len(executable))
        proof["elf"] = _elf64_x86_metadata(executable)
        proof["executable"] = _write_bytes(directory / "iqtree2", executable, executable=True)
        for index, name in enumerate(proof["elf"]["needed"]):
            if not name or name != Path(name).name or any(char in name for char in "/\\\0\r\n"):
                raise ValueError("native_needed_library_name_invalid")
            matches = [row for row in inventory["members"] if row["regular"] and Path(row["canonical_name"]).name == name]
            if not matches:
                proof["unresolved_needed_libraries"].append(name)
                continue
            if len(matches) != 1:
                raise ValueError("archive_companion_library_ambiguous")
            member = matches[0]["canonical_name"]
            body = _selected_tar_bytes(decoded, inventory, member, max_bytes=MAX_BINARY_BYTES)
            elf = _elf64_x86_metadata(body)
            pin = _write_bytes(directory / ("library-" + str(index) + ".bin"), body)
            proof["archive_companion_libraries"].append(dict(needed_name=name, member=member, file=pin, elf=elf,
                loader_deployment_verified=False))
        proof["acquisition_verified"] = True
    except Exception as failure:
        proof["failure"] = dict(type=type(failure).__name__, message=str(failure))
    finally:
        _write_json(directory / "IQTREE_RESOURCE_ACQUISITION.json", proof)
    assert proof["acquisition_verified"], proof["failure"]


def test_report_exact_acquired_iqtree_v2_4_0_version_without_download():
    attempt, request, selected = _selection(VERSION_GATE, fields=("software", "acquisition_proof"),
        test_file="test_iqtree_resource_provisioning.py")
    software, origin = selected["software"], selected["acquisition_proof"]
    for row in (software, origin):
        assert type(row) is dict and set(row) == {"path", "sha256", "size_bytes"}
        assert type(row["path"]) is str and type(row["sha256"]) is str and re.fullmatch("[0-9a-f]{64}", row["sha256"])
        assert type(row["size_bytes"]) is int and row["size_bytes"] > 0 and _pin(row["path"]) == row
    assert Path(origin["path"]).name == "IQTREE_RESOURCE_ACQUISITION.json"
    assert Path(origin["path"]).parent == Path(software["path"]).parent
    acquisition = json.loads(Path(origin["path"]).read_bytes())
    assert acquisition["version"] == "iqtree_resource_acquisition_proof_v1" and acquisition["release"] == RELEASE
    assert acquisition["acquisition_verified"] is True and acquisition["native_process_calls"] == 0
    assert acquisition["version_verified"] is acquisition["inference_execution_verified"] is False
    assert acquisition["executable"] == software
    for key in ("archive", "decoded_tar"):
        assert _pin(acquisition[key]["path"]) == acquisition[key]
    inventory = acquisition["tar_inventory"]["file"]
    assert _pin(inventory["path"]) == inventory
    assert acquisition["tar_inventory"]["all_member_headers_read"] is True
    assert acquisition["tar_inventory"]["validation_issues"] == []
    pins = json.loads((attempt / "selected_existing_native_executables.json").read_bytes())
    names = json.loads((attempt / "selected_native_executables.json").read_bytes())
    assert pins.count(software) == request["existing_native_executables"].count(software) == 1
    assert names.count(software["path"]) == 1
    before, mode_before = _pin(software["path"]), stat.S_IMODE(Path(software["path"]).stat().st_mode)
    assert mode_before & 0o111 and not mode_before & 0o222
    selected_libraries = json.loads((attempt / "selected_native_libraries.json").read_bytes())
    assert all(_pin(row["path"]) == row for row in selected_libraries)
    directory = attempt / "iqtree-v2.4.0-version"
    directory.mkdir(mode=0o700, exist_ok=False)
    (directory / "tmp").mkdir()
    (directory / "cache").mkdir()
    environment = dict(TMPDIR=str(directory / "tmp"), TMP=str(directory / "tmp"), TEMP=str(directory / "tmp"),
        XDG_CACHE_HOME=str(directory / "cache"), OMP_NUM_THREADS="1", LC_ALL="C", LANG="C")
    proof = dict(version="iqtree_resource_version_proof_v1", selected_pin=software, acquisition_proof=origin,
        requested_policy=request["policy"], swap_bytes=request["swap_bytes"], argv=[software["path"], "-version"],
        cwd=str(directory), environment=environment, before=before, before_mode=mode_before, after=None, after_mode=None,
        process_attempts=0, actual_process_started=False, child_pid=None, returncode=None,
        started_at=None, finished_at=None, elapsed_seconds=None, stdout=None, stderr=None,
        version_report=None, version_verified=False, failure=None, harness_http_requests=0,
        inference_execution_verified=False, selected_native_libraries=selected_libraries,
        elf_needed=acquisition["elf"]["needed"], process_maps=None, process_maps_failure=None,
        acquisition_proof_after=None, selected_libraries_after=None,
        complete_runtime_library_inventory_verified=False)
    _write_json(directory / "prepared.json", proof)
    try:
        with (directory / "version.stdout").open("xb") as stdout, (directory / "version.stderr").open("xb") as stderr:
            proof["process_attempts"] = 1
            started = time.monotonic()
            process = subprocess.Popen(proof["argv"], cwd=directory, env=environment,
                stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, shell=False)
            proof["actual_process_started"], proof["child_pid"] = True, process.pid
            proof["started_at"] = datetime.now(timezone.utc).isoformat()
            try:
                _write_json(directory / "started.json", {key: proof[key] for key in (
                    "argv", "cwd", "environment", "child_pid", "started_at")})
                # This is one opportunistic observation, never a complete
                # lifetime library inventory or retroactive authorization.
                try:
                    raw = Path("/proc/" + str(process.pid) + "/maps").read_bytes()
                    proof["process_maps"] = _write_bytes(directory / "process.maps", raw)
                except OSError as error:
                    proof["process_maps_failure"] = dict(type=type(error).__name__, message=str(error))
            finally:
                proof["returncode"] = process.wait()
                proof["finished_at"] = datetime.now(timezone.utc).isoformat()
                proof["elapsed_seconds"] = time.monotonic() - started
                for stream in (stdout, stderr):
                    stream.flush()
                    os.fsync(stream.fileno())
        if any((directory / ("version." + name)).stat().st_size > 65536 for name in ("stdout", "stderr")):
            raise ValueError("version_report_oversized")
        texts = {name: (directory / ("version." + name)).read_bytes().decode("utf-8") for name in ("stdout", "stderr")}
        pattern = r"IQ-TREE(?: multicore)? version (?P<version>2\.4\.0)(?P<suffix>(?:[ \t].*)?)"
        matches = [(channel, line, re.fullmatch(pattern, line)) for channel, text in texts.items()
            for line in text.splitlines() if re.fullmatch(pattern, line)]
        proof["version_report"] = dict(stdout_text=texts["stdout"], stderr_text=texts["stderr"],
            parsed=[dict(channel=channel, line=line, **match.groupdict()) for channel, line, match in matches],
            binary_matches_source_commit_verified=False)
        if proof["returncode"] != 0 or len(matches) != 1:
            raise ValueError("selected_version_report_not_verified")
        proof["version_verified"] = True
    except Exception as failure:
        proof["failure"] = dict(type=type(failure).__name__, message=str(failure))
    finally:
        for name in ("stdout", "stderr"):
            path = directory / ("version." + name)
            if path.exists():
                path.chmod(0o444)
                proof[name] = _pin(path)
        try:
            proof["after"] = _pin(software["path"])
            proof["after_mode"] = stat.S_IMODE(Path(software["path"]).stat().st_mode)
            proof["acquisition_proof_after"] = _pin(origin["path"])
        except Exception as failure:
            proof["after_inspection_failure"] = dict(type=type(failure).__name__, message=str(failure))
        proof["selected_bytes_and_mode_unchanged"] = proof["after"] == before and proof["after_mode"] == mode_before
        try:
            proof["selected_libraries_after"] = [_pin(row["path"]) for row in selected_libraries]
        except Exception as failure:
            proof["library_after_inspection_failure"] = dict(type=type(failure).__name__, message=str(failure))
        proof["selected_libraries_unchanged"] = proof["selected_libraries_after"] == selected_libraries
        _write_json(directory / "IQTREE_RESOURCE_VERSION.json", proof)
    assert proof["selected_bytes_and_mode_unchanged"] and proof["selected_libraries_unchanged"]
    assert proof["acquisition_proof_after"] == origin
    assert proof["version_verified"], proof["failure"]
