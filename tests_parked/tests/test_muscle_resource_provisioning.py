"""Opt-in acquisition and separate version inspection of one official MUSCLE asset.

These are physical resource checks, not scientific execution or Store custody.
The acquisition never executes its bytes. The version check never downloads.
Each selected attempt is retained under the actual enclosing bounded run.
"""
import hashlib
import json
import io
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import tarfile
import zlib
from datetime import datetime, timezone
from urllib.parse import urlsplit

import pytest

from tests.bounded_execution.elf_inspection import elf64_x86_metadata as _elf64_x86_metadata


RELEASE = {
    "tag": "v5.3", "commit": "2cf9d33078c9a85697e38a6f3ad827e6862420df",
    "release_id": 184590168, "asset_id": 205569768,
    "published_at": "2024-11-11T01:36:15Z", "name": "muscle-linux-x86.v5.3",
    "url": "https://github.com/rcedgar/muscle/releases/download/v5.3/muscle-linux-x86.v5.3",
    "size_bytes": 3587040, "publisher_digest": None,
    "metadata_url": "https://api.github.com/repos/rcedgar/muscle/releases/tags/v5.3",
    "platform_source": "https://raw.githubusercontent.com/rcedgar/muscle/v5.3/.github/workflows/build_linux_x86.yml",
}
MAX_BYTES = 4 * 1024 * 1024
REDIRECT_HOSTS = ("release-assets.githubusercontent.com", "objects.githubusercontent.com")
ACQUIRE_GATE = "HMMER_NATIVE_ORACLE_MUSCLE_V5_3_ACQUIRE_JSON"
VERSION_GATE = "HMMER_NATIVE_ORACLE_MUSCLE_V5_3_VERSION_JSON"
POLICY = {'memory_bytes': 20 * 1024 ** 3, 'scratch_bytes': 4 * 1024 ** 3}


def _json_value(value):
    """Compare and retain JSON meanings, including native header-pair arrays."""
    return json.loads(json.dumps(value, sort_keys=True, allow_nan=False))


def _write_json(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o444)


def _write_bytes(path, raw, *, executable=False):
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o555 if executable else 0o444)
    return _pin(path)


def _pin(path):
    path = Path(path)
    assert path.is_absolute() and path.resolve(strict=True) == path, "canonical regular path required"
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        assert stat.S_ISREG(before.st_mode), "regular file required"
        digest, size = hashlib.sha256(), 0
        while block := stream.read(1024 * 1024):
            digest.update(block)
            size += len(block)
        after = os.fstat(stream.fileno())
    fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns", "st_mode")
    assert all(getattr(before, key) == getattr(after, key) for key in fields), "file changed during inspection"
    assert size == before.st_size
    return {"path": str(path), "sha256": digest.hexdigest(), "size_bytes": size}


def _selection(gate, *, fields, test_file="test_muscle_resource_provisioning.py"):
    if gate not in os.environ or "HMMER529_ATTEMPT" not in os.environ:
        pytest.skip("explicit selected bounded resource check only")
    value = json.loads(os.environ[gate])
    assert type(value) is dict and set(value) == set(fields), "closed explicit resource gate required"
    attempt = Path(os.environ["HMMER529_ATTEMPT"])
    assert attempt.is_absolute() and attempt.resolve(strict=True) == attempt
    request = json.loads((attempt / "selected_request.json").read_text())
    assert request["policy"] == POLICY and request["swap_bytes"] == 0
    assert request["environment"]["HMMER529_ATTEMPT"] == str(attempt)
    assert request["environment"][gate] == os.environ[gate]
    assert any(str(node).split("::", 1)[0] == test_file
        for node in request["tests"]), "test must be selected in the enclosing request"
    return attempt, request, value




def _retained_http(client, url, directory, ordinal, timeout, *,
        service="muscle_release_software", max_bytes=MAX_BYTES):
    """One existing transport call, preserving every captured failure prefix."""
    from gene_annotation_episode.acquisition import AcquisitionError

    error, snapshot = None, None
    selected = dict(service=service, url=url, params={},
        media_type="application/octet-stream", accept="application/octet-stream",
        max_bytes=max_bytes, timeout_seconds=timeout, follow_redirects=False)
    try:
        snapshot = client._http(**selected)
    except AcquisitionError as failure:
        snapshot = failure.snapshot
        error = _json_value({"type": type(failure).__name__, "code": failure.code,
            "phase": failure.phase, "retry_after": failure.retry_after,
            "submission_outcome": failure.submission_outcome,
            "diagnostic": failure.diagnostic, "operational": failure.operational})
    except Exception as failure:
        error = {"type": type(failure).__name__, "message": str(failure)}
    captured = None
    if snapshot is not None:
        body = _write_bytes(directory / ("http-" + str(ordinal) + ".body"), snapshot.content)
        captured = _json_value(dict(service=snapshot.service, url=snapshot.url,
            request=snapshot.request, retrieved_at=snapshot.retrieved_at,
            media_type=snapshot.media_type, transport=snapshot.transport, body=body))
    value = dict(ordinal=ordinal, selected_request=selected, response=captured, failure=error)
    _write_json(directory / ("http-" + str(ordinal) + ".json"), value)
    return value, snapshot


def _bounded_gzip_tar(raw, *, max_expanded_bytes, max_members):
    """Read one bounded gzip member and inventory tar bytes before extraction.

    This does not write archive paths. Callers retain the supplied archive and
    returned decoded tar/inventory before asserting the validation result.
    """
    assert type(raw) is bytes and type(max_expanded_bytes) is int and max_expanded_bytes > 0
    assert type(max_members) is int and max_members > 0
    inflater = zlib.decompressobj(wbits=31)
    decoded = inflater.decompress(raw, max_expanded_bytes + 1)
    if len(decoded) > max_expanded_bytes or inflater.unconsumed_tail:
        raise ValueError("archive_expanded_byte_limit")
    if not inflater.eof or inflater.unused_data:
        raise ValueError("archive_gzip_extent_invalid")
    inventory, issues, seen, total = [], [], set(), 0
    with tarfile.open(fileobj=io.BytesIO(decoded), mode="r:") as archive:
        for member in archive:
            if len(inventory) >= max_members:
                raise ValueError("archive_member_count_limit")
            name = member.name
            canonical = name[2:] if name.startswith("./") else name
            if member.isdir() and canonical.endswith("/"):
                canonical = canonical[:-1]
            path = PurePosixPath(canonical)
            codes = []
            if (not canonical or path.is_absolute() or ".." in path.parts
                    or str(path) != canonical or any(char in canonical for char in "\0\r\n\\")):
                codes.append("archive_member_path_invalid")
            if canonical in seen:
                codes.append("archive_member_path_duplicate")
            seen.add(canonical)
            if member.type not in (tarfile.REGTYPE, tarfile.AREGTYPE, tarfile.DIRTYPE) or member.linkname:
                codes.append("archive_member_type_invalid")
            if type(member.size) is not int or member.size < 0 or member.isdir() and member.size != 0:
                codes.append("archive_member_size_invalid")
            else:
                total += member.size
                if (total > max_expanded_bytes or member.offset_data < 0 or member.offset_data > len(decoded)
                        or member.size > len(decoded) - member.offset_data):
                    codes.append("archive_member_extent_invalid")
            inventory.append(dict(name=name, canonical_name=canonical, type=member.type.decode("latin-1"),
                mode=member.mode, uid=member.uid, gid=member.gid, uname=member.uname, gname=member.gname,
                size_bytes=member.size, mtime=member.mtime, linkname=member.linkname, checksum=member.chksum,
                header_offset=member.offset, data_offset=member.offset_data, pax_headers=dict(member.pax_headers),
                regular=member.isfile(), directory=member.isdir(), validation_issues=codes))
            issues.extend(dict(name=name, code=code) for code in codes)
        global_pax_headers = dict(archive.pax_headers)
        logical_end = archive.offset
    if len(decoded) - logical_end < 1024 or any(decoded[logical_end:]):
        issues.append(dict(name="", code="archive_end_marker_or_trailing_bytes_invalid"))
    return decoded, dict(version="strict_tar_inventory_v1", members=inventory, global_pax_headers=global_pax_headers,
        decoded_size_bytes=len(decoded), member_content_size_bytes=total, all_member_headers_read=True,
        logical_member_end=logical_end, trailing_zero_bytes=len(decoded) - logical_end, validation_issues=issues)


def _selected_tar_bytes(decoded, inventory, selected_name, *, max_bytes):
    """Extract one exact regular member into memory; no archive write path."""
    if inventory["validation_issues"]:
        raise ValueError("archive_inventory_invalid")
    rows = [row for row in inventory["members"] if row["canonical_name"] == selected_name]
    if len(rows) != 1 or rows[0]["regular"] is not True or rows[0]["size_bytes"] > max_bytes:
        raise ValueError("selected_archive_member_invalid")
    with tarfile.open(fileobj=io.BytesIO(decoded), mode="r:") as archive:
        members = [member for member in archive.getmembers() if member.name == rows[0]["name"]]
        if len(members) != 1 or not members[0].isfile():
            raise ValueError("selected_archive_member_identity_conflict")
        with archive.extractfile(members[0]) as stream:
            raw = stream.read(max_bytes + 1)
    if len(raw) != rows[0]["size_bytes"]:
        raise ValueError("selected_archive_member_extent_conflict")
    return raw


def test_acquire_official_muscle_v5_3_linux_asset_without_execution():
    attempt, request, selected = _selection(ACQUIRE_GATE, fields=("enabled", "timeout_seconds"))
    assert selected["enabled"] is True and type(selected["timeout_seconds"]) is int
    assert selected["timeout_seconds"] > 0, "finite explicit HTTP timeout required"
    directory = attempt / "muscle-v5.3-acquisition"
    directory.mkdir(mode=0o700, exist_ok=False)
    proof = dict(version="muscle_resource_acquisition_proof_v1", release=RELEASE,
        requested_policy=request["policy"], swap_bytes=request["swap_bytes"],
        redirect_policy=dict(automatic_redirects=False, maximum_explicit_redirects=1,
            allowed_https_hosts=list(REDIRECT_HOSTS)), max_bytes=MAX_BYTES,
        timeout_seconds=selected["timeout_seconds"], exchanges=[], acquisition_verified=False,
        executable=None, elf=None, failure=None, native_process_calls=0,
        version_verified=False, alignment_execution_verified=False)
    _write_json(directory / "prepared.json", proof)
    from gene_annotation_episode.acquisition import PublicClients

    client = PublicClients(ncbi_email=None, timeout=selected["timeout_seconds"],
        access_dir=directory / "http-access")
    try:
        exchange, snapshot = _retained_http(client, RELEASE["url"], directory, 0, selected["timeout_seconds"])
        proof["exchanges"].append(exchange)
        if snapshot is None:
            raise ValueError("original_asset_response_unavailable")
        status = snapshot.transport.get("status")
        if status == 302:
            assert exchange["failure"] is not None and exchange["failure"].get("code") == "provider_http_302"
            if snapshot.transport.get("body_complete") is not True:
                raise ValueError("original_asset_redirect_capture_incomplete")
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
            exchange, snapshot = _retained_http(client, location, directory, 1, selected["timeout_seconds"])
            proof["exchanges"].append(exchange)
        elif status == 200:
            proof["route"] = "direct_original_asset_response"
        else:
            raise ValueError("original_asset_http_status_not_selected")
        if snapshot is None or snapshot.transport.get("status") != 200 or exchange["failure"] is not None:
            raise ValueError("selected_asset_response_failed")
        transport = snapshot.transport
        if (transport.get("body_complete") is not True
                or transport.get("observed_body_bytes") != RELEASE["size_bytes"]
                or transport.get("retained_body_bytes") != RELEASE["size_bytes"]
                or len(snapshot.content) != RELEASE["size_bytes"]):
            raise ValueError("selected_asset_byte_count_or_extent_conflict")
        proof["elf"] = _elf64_x86_metadata(snapshot.content)
        proof["executable"] = _write_bytes(directory / RELEASE["name"], snapshot.content, executable=True)
        proof["acquisition_verified"] = True
    except Exception as failure:
        proof["failure"] = {"type": type(failure).__name__, "message": str(failure)}
    finally:
        _write_json(directory / "MUSCLE_RESOURCE_ACQUISITION.json", proof)
    assert proof["acquisition_verified"], proof["failure"]


def test_report_selected_muscle_v5_3_version_without_download():
    attempt, request, selected = _selection(VERSION_GATE, fields=("path", "sha256", "size_bytes"))
    assert type(selected["path"]) is str and type(selected["sha256"]) is str
    assert re.fullmatch("[0-9a-f]{64}", selected["sha256"])
    assert type(selected["size_bytes"]) is int and selected["size_bytes"] == RELEASE["size_bytes"]
    pins = json.loads((attempt / "selected_existing_native_executables.json").read_text())
    names = json.loads((attempt / "selected_native_executables.json").read_text())
    assert pins.count(selected) == request["existing_native_executables"].count(selected) == 1
    assert names.count(selected["path"]) == 1, "actual measured existing native selection required"
    before = _pin(selected["path"])
    assert before == selected
    mode_before = stat.S_IMODE(Path(selected["path"]).stat().st_mode)
    assert mode_before & 0o111 and not mode_before & 0o222, "selected executable must be immutable"
    directory = attempt / "muscle-v5.3-version"
    directory.mkdir(mode=0o700, exist_ok=False)
    (directory / "tmp").mkdir()
    (directory / "cache").mkdir()
    environment = dict(TMPDIR=str(directory / "tmp"), TMP=str(directory / "tmp"),
        TEMP=str(directory / "tmp"), XDG_CACHE_HOME=str(directory / "cache"),
        OMP_NUM_THREADS="1", LC_ALL="C", LANG="C")
    proof = dict(version="muscle_resource_version_proof_v1", selected_pin=selected,
        requested_policy=request["policy"], swap_bytes=request["swap_bytes"],
        argv=[selected["path"], "-version"], cwd=str(directory), environment=environment,
        before=before, before_mode=mode_before, after=None, after_mode=None,
        process_attempts=0, actual_process_started=False, returncode=None, failure=None,
        started_at=None, finished_at=None, child_pid=None,
        stdout=None, stderr=None, version_report=None, version_verified=False,
        harness_http_requests=0, alignment_execution_verified=False)
    _write_json(directory / "prepared.json", proof)
    try:
        with (directory / "version.stdout").open("xb") as stdout, (directory / "version.stderr").open("xb") as stderr:
            proof["process_attempts"] = 1
            process = subprocess.Popen(proof["argv"], cwd=directory, env=environment,
                stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, shell=False)
            proof["actual_process_started"] = True
            try:
                proof["child_pid"] = process.pid
                proof["started_at"] = datetime.now(timezone.utc).isoformat()
                _write_json(directory / "started.json", {key: proof[key] for key in (
                    "argv", "cwd", "environment", "child_pid", "started_at")})
            finally:
                proof["returncode"] = process.wait()
                proof["finished_at"] = datetime.now(timezone.utc).isoformat()
                for stream in (stdout, stderr):
                    stream.flush()
                    os.fsync(stream.fileno())
        if any((directory / ("version." + name)).stat().st_size > 65536 for name in ("stdout", "stderr")):
            raise ValueError("version_report_oversized")
        text = (directory / "version.stdout").read_bytes().decode("utf-8")
        lines = text.splitlines()
        match = re.fullmatch(r"muscle (?P<version>5\.3)\.(?P<platform>linux64)(?P<flags>[DT]*) \[(?P<git>[^\r\n]*)\]", lines[0] if lines else "")
        proof["version_report"] = dict(stdout_text=text,
            stderr_text=(directory / "version.stderr").read_bytes().decode("utf-8"),
            parsed=None if match is None else match.groupdict(),
            build_lines=[line for line in lines[1:] if line.startswith("Built ")],
            release_source_commit=RELEASE["commit"], binary_matches_source_commit_verified=False)
        if proof["returncode"] != 0 or match is None:
            raise ValueError("selected_version_report_not_verified")
        proof["version_verified"] = True
    except Exception as failure:
        proof["failure"] = {"type": type(failure).__name__, "message": str(failure)}
    finally:
        for name in ("stdout", "stderr"):
            path = directory / ("version." + name)
            if path.exists():
                path.chmod(0o444)
                proof[name] = _pin(path)
        try:
            proof["after"] = _pin(selected["path"])
            proof["after_mode"] = stat.S_IMODE(Path(selected["path"]).stat().st_mode)
        except Exception as failure:
            proof["after_inspection_failure"] = {"type": type(failure).__name__, "message": str(failure)}
        proof["selected_bytes_and_mode_unchanged"] = proof["after"] == before and proof["after_mode"] == mode_before
        _write_json(directory / "MUSCLE_RESOURCE_VERSION.json", proof)
    assert proof["selected_bytes_and_mode_unchanged"]
    assert proof["version_verified"], proof["failure"]
