"""Saved-only fixture verification after check118's NSS audit failure.

The original download and original receipt remain unchanged. This explicitly
selected check reads only already-retained evidence; it performs no acquisition
and invokes no VDB helper or observation facility.
"""
import hashlib
import json
import os
from pathlib import Path


PACKET = "tool_graders_blast_vdb_fixture_acquisition_2026-10-28_658"
EXPECTED = (
    ("ERR3487613", 35175, "b2bfb00c124d3fcad808563ceb927e1671a72733", "266e59ba8a5033a084ddb95ab4518fe1c2e71a96e1fc20bb0b959a88c15567d7"),
    ("ERR3487613.fasta", 6442, "4a5c94d1cc878bfd847acba11f02d0d7fd404c4f", "165c749d742d0436d0482139fa0d734f7c4fdc7d9b428e73efaacaac416a97c8"),
)
EXPECTED_FIRST_DEFLINES = (
    ">ERR3487613.1/1 M03700:76:000000000-B367V:1:1101:15865:1333 length=250",
    ">ERR3487613.1/2 M03700:76:000000000-B367V:1:1101:15865:1333 length=250",
)
EXPECTED_FIRST_SEQUENCE_SHA256 = (
    "03a47a624dd902c7f364914de37206018e410e51a19b67a632ff07ab5f34d0eb",
    "0c00cfb9195e3e67b0a80edd9a74a6712f74927b032a26d38c3e5cd252e341af",
)


def test_verify_saved_selected_fixture_objects():
    attempt = Path(os.environ["HMMER529_ATTEMPT"]).resolve(strict=True)
    assert attempt.name == "check118b_vdb_fixture658_saved"
    repo = attempt.parents[2]
    retained = repo / "verification" / PACKET / "retained"
    original_attempt = attempt.parent / "check118_vdb_fixture658"
    request = json.loads((attempt / "selected_request.json").read_text())
    assert request["policy"] == {"memory_bytes": 21474836480, "scratch_bytes": 4294967296, "wall_seconds": None}
    assert request["swap_bytes"] == 0
    assert request["native_executables"] == []
    original_audit = json.loads((original_attempt / "execution_audit.json").read_text())
    original_receipt = json.loads((original_attempt / "receipt.json").read_text())
    assert original_receipt["returncode"] == 4
    assert original_audit["pytest_returncode"] == 0
    assert original_audit["unbound_mappings"] == ["/usr/lib/x86_64-linux-gnu/libnss_mdns4_minimal.so.2"]
    assert original_audit["outside_modules"] == []
    assert original_audit["native_unchanged"] is True
    manifest = json.loads((retained / "ORIGINAL_FILE_MANIFEST.json").read_text())
    receipts = json.loads((retained / "ACQUISITION_RECEIPTS.json").read_text())["receipts"]
    assert len(receipts) == 2
    assert manifest["downloaded_object_count"] == 2
    assert manifest["downloaded_payload_bytes"] == 41617
    assert manifest["known_native_helper_entry_values"] == []
    verified = []
    for index, (name, size, blob, sha256) in enumerate(EXPECTED):
        path = retained / "fixture" / name
        contents = path.read_bytes()
        assert len(contents) == size
        assert hashlib.sha1(b"blob " + str(size).encode("ascii") + b"\0" + contents).hexdigest() == blob
        assert hashlib.sha256(contents).hexdigest() == sha256
        row = manifest["original_files"][index]
        assert row["retained_path"] == str(path)
        assert Path(row["path"]).samefile(path)
        assert row["size_bytes"] == size and row["sha256"] == sha256
        http = receipts[index]
        url = "https://raw.githubusercontent.com/ncbi/sra-tools/0dc2c24302137932c449429f05228b79cfa87700/test/external/fasterq-dump/" + name
        assert http["request_url"] == http["response_url"] == url
        assert http["response_status"] == 200
        assert http["observed_git_blob_sha1"] == blob
        assert http["observed_sha256"] == sha256
        assert http["received_entity_bytes"] == size
        assert http["bytes_beyond_declared_entity"] == 0
        verified.append({"path": str(path), "size_bytes": size, "sha256": sha256, "git_blob_sha1": blob})
    observations = json.loads((retained / "FASTA_OBSERVATIONS.json").read_text())
    lines = (retained / "fixture" / "ERR3487613.fasta").read_text(encoding="ascii").splitlines()
    independently_read = []
    for line_number, line in enumerate(lines, 1):
        if line.startswith(">"):
            independently_read.append([line_number, line, ""])
        elif line:
            independently_read[-1][2] += line
    assert len(independently_read) == observations["record_count"] == 20
    assert sum(len(row[2]) for row in independently_read) == observations["total_sequence_symbols"] == 5000
    for ordinal, ((line_number, defline, sequence), row) in enumerate(zip(independently_read, observations["records"], strict=True)):
        assert row["record_ordinal"] == ordinal
        assert row["defline_line_number"] == line_number
        assert row["exact_defline"] == defline
        assert row["exact_sequence"] == sequence
        assert row["symbol_count"] == len(sequence) == 250
        assert row["sequence_sha256"] == hashlib.sha256(sequence.encode("ascii")).hexdigest()
    for index in range(2):
        assert independently_read[index][1] == EXPECTED_FIRST_DEFLINES[index]
        assert observations["records"][index]["sequence_sha256"] == EXPECTED_FIRST_SEQUENCE_SHA256[index]
    assert observations["native_helper_observed_identifiers"] == []
    assert observations["native_helper_executed"] is False
    configuration = retained / "fixture" / "offline.kfg"
    config_bytes = configuration.read_bytes()
    expected_config = (
        '/repository/remote/disabled = "true"\n'
        '/repository/site/disabled = "true"\n'
        '/repository/user/disabled = "true"\n'
        '/repository/user/cache-disabled = "true"\n'
        '/repository/user/main/public/cache-disabled = "true"\n'
    ).encode("ascii")
    assert config_bytes == expected_config
    assert len(config_bytes) == 201
    assert hashlib.sha256(config_bytes).hexdigest() == "ab65e06f45d7b49f187f3f79f963e909b8b20e2e2aa2d46b416cc40a9fe2c8fd"
    proposed_config = json.loads((retained / "PROPOSED_OFFLINE_CONFIGURATION.json").read_text())
    assert proposed_config["applied_to_native_helper"] is False
    assert proposed_config["runtime_resolution_or_cache_closure_verified"] is False
    result = {
        "version": "saved_vdb_fixture_verification_v1",
        "state": "saved_bytes_and_observations_verified",
        "handle": str(attempt / "handle.json"),
        "original_acquisition_handle": str(original_attempt / "handle.json"),
        "original_acquisition_receipt_returncode": original_receipt["returncode"],
        "original_acquisition_unbound_mappings": original_audit["unbound_mappings"],
        "original_acquisition_audit_reinterpreted": False,
        "objects": verified,
        "companion_record_count": 20,
        "companion_total_sequence_symbols": 5000,
        "first_paired_companion_records": observations["records"][:2],
        "configuration_size_bytes": 201,
        "configuration_sha256": hashlib.sha256(config_bytes).hexdigest(),
        "configuration_applied": False,
        "new_acquisition_requests": 0,
        "native_helper_executed": False,
        "native_helper_observed_identifiers": [],
        "native_dataset_closure_verified": False,
    }
    output = attempt / "temporary" / "SAVED_VERIFICATION_RESULT.json"
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    target = repo / "verification" / PACKET / "SAVED_VERIFICATION_RESULT.json"
    os.link(output, target)
    output.chmod(0o444)
