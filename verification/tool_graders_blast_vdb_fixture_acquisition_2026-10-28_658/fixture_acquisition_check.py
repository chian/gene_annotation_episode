"""Acquire exactly two root-selected Git objects inside bounded529.

This verification script neither imports application code nor invokes a VDB
helper. Its pytest entry is an explicit operation selected by root, not a
production acquisition or scientific grading path.
"""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import ssl
import urllib.error
import urllib.request


COMMIT = "0dc2c24302137932c449429f05228b79cfa87700"
PACKET_NAME = "tool_graders_blast_vdb_fixture_acquisition_2026-10-28_658"
SELECTED = (
    ("ERR3487613", 35175, "b2bfb00c124d3fcad808563ceb927e1671a72733"),
    ("ERR3487613.fasta", 6442, "4a5c94d1cc878bfd847acba11f02d0d7fd404c4f"),
)
OFFLINE = (
    '/repository/remote/disabled = "true"\n'
    '/repository/site/disabled = "true"\n'
    '/repository/user/disabled = "true"\n'
    '/repository/user/cache-disabled = "true"\n'
    '/repository/user/main/public/cache-disabled = "true"\n'
).encode("ascii")


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def identity(path):
    contents = path.read_bytes()
    return {
        "path": str(path),
        "size_bytes": len(contents),
        "sha256": hashlib.sha256(contents).hexdigest(),
    }


class RejectRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def acquire(opener, fixture, name, expected_size, expected_git_blob, receipts):
    url = (
        "https://raw.githubusercontent.com/ncbi/sra-tools/" + COMMIT
        + "/test/external/fasterq-dump/" + name
    )
    headers = {
        "Accept-Encoding": "identity",
        "User-Agent": "gene-annotation-episode-selected-fixture-acquisition/658",
    }
    row = {
        "object_name": name,
        "request_url": url,
        "request_method": "GET",
        "request_headers": headers,
        "started_at_utc": utc_now(),
        "expected_size_bytes": expected_size,
        "expected_git_blob_sha1": expected_git_blob,
        "stored_payload_limit_bytes": expected_size,
        "redirects_allowed": False,
        "attempt_number": 1,
        "state": "requested",
    }
    receipts.append(row)
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with opener.open(request, timeout=None) as response:
            row.update(
                response_url=response.geturl(),
                response_status=response.status,
                response_reason=response.reason,
                response_headers=list(response.headers.raw_items()),
                response_http_version=response.version,
            )
            if response.status != 200 or response.geturl() != url:
                raise ValueError("unexpected_http_status_or_url")
            lengths = response.headers.get_all("Content-Length", [])
            if lengths != [str(expected_size)]:
                raise ValueError("missing_conflicting_or_unselected_content_length")
            if response.headers.get("Content-Encoding", "identity") != "identity":
                raise ValueError("unselected_content_encoding")
            contents = bytearray()
            while len(contents) < expected_size:
                block = response.read(min(8192, expected_size - len(contents)))
                if not block:
                    break
                contents.extend(block)
            # With the required Content-Length, this observes the end of the
            # declared HTTP entity. No excess bytes are ever written to disk.
            beyond_declared_entity = response.read(1)
            row.update(
                received_entity_bytes=len(contents),
                bytes_beyond_declared_entity=len(beyond_declared_entity),
            )
            if len(contents) != expected_size or beyond_declared_entity:
                raise ValueError("response_size_conflict")
        contents = bytes(contents)
        observed_git_blob = hashlib.sha1(
            b"blob " + str(len(contents)).encode("ascii") + b"\0" + contents
        ).hexdigest()
        observed_sha256 = hashlib.sha256(contents).hexdigest()
        row.update(
            observed_git_blob_sha1=observed_git_blob,
            observed_sha256=observed_sha256,
            git_blob_hash_method="SHA1(b'blob ' + decimal_byte_count + b'\\0' + exact_body)",
        )
        # Retain any returned exact-size body even if the selected identity
        # fails, so an actual mismatch is inspectable rather than discarded.
        destination = fixture / name
        with destination.open("xb") as stream:
            stream.write(contents)
        row["acquired_original_path"] = str(destination)
        if observed_git_blob != expected_git_blob:
            raise ValueError("selected_git_blob_identity_conflict")
        row["state"] = "verified_selected_object"
        return destination
    except urllib.error.HTTPError as error:
        row.update(
            response_url=error.geturl(),
            response_status=error.code,
            response_reason=str(error.reason),
            response_headers=list(error.headers.raw_items()),
            state="failed",
            failure_type=type(error).__name__,
        )
        raise
    except Exception as error:
        row.update(state="failed", failure_type=type(error).__name__, failure=str(error))
        raise
    finally:
        row["finished_at_utc"] = utc_now()


def inspect_fasta(path):
    contents = path.read_bytes()
    lines = contents.decode("ascii").splitlines()
    records = []
    for line_number, line in enumerate(lines, 1):
        if line.startswith(">"):
            records.append({
                "record_ordinal": len(records),
                "defline_line_number": line_number,
                "exact_defline": line,
                "identifier_token": line[1:].split(maxsplit=1)[0],
                "sequence_lines": [],
            })
        elif line:
            if not records:
                raise ValueError("sequence_before_first_fasta_defline")
            if any(symbol.isspace() for symbol in line):
                raise ValueError("whitespace_inside_fasta_sequence_line")
            records[-1]["sequence_lines"].append(line)
    for record in records:
        sequence = "".join(record["sequence_lines"])
        record.update(
            exact_sequence=sequence,
            symbol_count=len(sequence),
            sequence_sha256=hashlib.sha256(sequence.encode("ascii")).hexdigest(),
            observed_symbol_counts=dict(sorted(Counter(sequence).items())),
        )
    if not records or any(not row["exact_sequence"] for row in records):
        raise ValueError("empty_fasta_or_record")
    return {
        "version": "selected_fasta_companion_observations_v1",
        "source_file": identity(path),
        "record_count": len(records),
        "total_sequence_symbols": sum(row["symbol_count"] for row in records),
        "observed_length_counts": dict(sorted(Counter(row["symbol_count"] for row in records).items())),
        "deflines": [row["exact_defline"] for row in records],
        "records": records,
        "scope": "exact_committed_companion_file_only",
        "native_helper_executed": False,
        "native_helper_observed_identifiers": [],
        "source_derived_helper_identifier_expectations": [
            "gnl|SRA|ERR3487613.1.1", "gnl|SRA|ERR3487613.1.2",
        ],
        "expectation_status": "source_derived_unverified_by_native_helper",
        "full_public_run_counts": None,
        "sample_identity": None,
    }


def test_acquire_two_selected_fixture_objects():
    attempt = Path(os.environ["HMMER529_ATTEMPT"]).resolve(strict=True)
    assert attempt.name == "check118_vdb_fixture658"
    request = json.loads((attempt / "selected_request.json").read_text())
    assert request["policy"] == {
        "memory_bytes": 21474836480,
        "scratch_bytes": 4294967296,
        "wall_seconds": None,
    }
    assert request["swap_bytes"] == 0
    assert request["native_executables"] == []
    work = attempt / "temporary" / "vdb_fixture_acquisition658"
    work.mkdir(exist_ok=False)
    fixture = work / "fixture"
    fixture.mkdir()
    retained = attempt.parents[2] / "verification" / PACKET_NAME / "retained"
    assert not retained.exists()
    receipts = []
    result = {"state": "started", "started_at_utc": utc_now()}
    # Disable environmental proxy selection and redirects: only the two exact
    # selected HTTPS URLs can be requested by this script. TLS is verified.
    context = ssl.create_default_context()
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), RejectRedirects(),
        urllib.request.HTTPSHandler(context=context),
    )
    try:
        acquired = [acquire(opener, fixture, *row, receipts) for row in SELECTED]
        assert sum(path.stat().st_size for path in acquired) == 41617
        observations = inspect_fasta(acquired[1])
        write_json(work / "FASTA_OBSERVATIONS.json", observations)
        configuration = fixture / "offline.kfg"
        with configuration.open("xb") as stream:
            stream.write(OFFLINE)
        write_json(work / "PROPOSED_OFFLINE_CONFIGURATION.json", {
            "state": "retained_proposal_not_applied",
            "source_proposal": "verification/tool_graders_blast_vdb_offline_fixture_2026-10-28_656/SELECTION_PROPOSAL_001.md",
            "original_configuration": identity(configuration),
            "retained_configuration_path": str(retained / "fixture" / "offline.kfg"),
            "exact_content": OFFLINE.decode("ascii"),
            "required_future_environment_key": "NCBI_VDB_CONFIG",
            "required_future_value": "absolute selected staged offline.kfg path",
            "applied_to_native_helper": False,
            "runtime_resolution_or_cache_closure_verified": False,
        })
        roles = ["selected_native_archive", "independent_upstream_fasta_companion", "proposed_offline_configuration"]
        originals = []
        for role, path in zip(roles, [*acquired, configuration], strict=True):
            originals.append({
                "role": role, **identity(path),
                "retained_path": str(retained / "fixture" / path.name),
            })
        write_json(work / "ORIGINAL_FILE_MANIFEST.json", {
            "version": "selected_vdb_fixture_original_file_inventory_v1",
            "state": "acquired_objects_verified_native_resolution_unverified",
            "source_repository": "https://github.com/ncbi/sra-tools",
            "source_commit": COMMIT,
            "source_directory": "test/external/fasterq-dump",
            "original_files": originals,
            "downloaded_object_count": 2,
            "downloaded_payload_bytes": 41617,
            "original_file_bytes_including_configuration": sum(row["size_bytes"] for row in originals),
            "native_dataset_inventory": [originals[0]],
            "native_dataset_dependency_closure_verified": False,
            "known_native_helper_entry_values": [],
            "source_derived_helper_identifier_expectations": observations["source_derived_helper_identifier_expectations"],
            "native_helper_executed": False,
            "full_accession_acquired": False,
            "vdb_offline_binding_record_created": False,
        })
        result.update(
            state="acquisition_verified",
            exact_selected_object_count=2,
            exact_downloaded_payload_bytes=41617,
            companion_record_count=observations["record_count"],
            companion_total_sequence_symbols=observations["total_sequence_symbols"],
            native_helper_executed=False,
        )
    except Exception as error:
        result.update(state="failed", failure_type=type(error).__name__, failure=str(error))
        raise
    finally:
        result["finished_at_utc"] = utc_now()
        write_json(work / "ACQUISITION_RECEIPTS.json", {
            "version": "selected_exact_git_object_http_acquisition_v1",
            "attempt": str(attempt),
            "handle": str(attempt / "handle.json"),
            "redirects_allowed": False,
            "environmental_proxies_used": False,
            "ssl_default_verify_paths": ssl.get_default_verify_paths()._asdict(),
            "ssl_certificate_verification": "required",
            "socket_timeout_seconds": None,
            "automatic_retries": 0,
            "receipts": receipts,
        })
        write_json(work / "ACQUISITION_RESULT.json", result)
        # Hardlinks retain the very same files under the owned evidence packet;
        # every byte remains under the runner cwd's scratch accounting. No host
        # fixture read/copy is needed and no second data allocation is created.
        retained.mkdir(exist_ok=False)
        links = []
        for source in sorted(work.rglob("*")):
            target = retained / source.relative_to(work)
            if source.is_dir():
                target.mkdir()
            else:
                os.link(source, target)
                source.chmod(0o444)
                assert source.samefile(target)
                links.append({
                    "original": str(source), "retained": str(target),
                    "device": source.stat().st_dev, "inode": source.stat().st_ino,
                    "same_inode": True, **identity(source),
                })
        write_json(work / "RETAINED_LINKS.json", links)
        os.link(work / "RETAINED_LINKS.json", retained / "RETAINED_LINKS.json")
        (work / "RETAINED_LINKS.json").chmod(0o444)
        for directory in sorted((path for path in retained.rglob("*") if path.is_dir()), reverse=True):
            directory.chmod(0o555)
        retained.chmod(0o555)
    print(json.dumps(result, sort_keys=True))
