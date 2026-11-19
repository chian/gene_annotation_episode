"""Generated damaged wrappers: native prefix custody, not biological accuracy."""
import gzip


from gene_annotation_episode.state import Store


FIRST = b"@one native read\nACGTACGT\n+\nIIIIIIII\n"
SECOND = b"@two native read\nGATTACAA\n+\nHHHHHHHH\n"


def test_partial_deflate_payload_keeps_only_complete_native_fastq_records(tmp_path):
    wrapper = gzip.compress(FIRST, mtime=0) + gzip.compress(SECOND, mtime=0)[:-12]
    expected = FIRST + b"@two native read\nGATTACAA\n+\n"
    with Store(tmp_path / "store") as store:
        store.create_problem(raw_sequence="MKWV", molecule="protein")
        material = store.register_material(data=wrapper, role="read", molecule="dna")
        attempt = store.parse_material(material["id"])
        assert attempt["status"] == "partial" and attempt["valid_records"] == 1
        decoded = store.get(attempt["source_ref"])
        assert store.get_artifact(decoded["artifact_ref"]) == expected
        errors = store.material_errors(attempt["id"])["errors"]
        assert [row["code"] for row in errors] == ["gzip_decode_incomplete", "malformed_fastq_remaining_scope_unparsed"]
        member, = store.material_members(attempt["collection_ref"])["members"]
        assert member["ordinal"] == 0
        assert store.material_member(member["id"])["sequence"] == "ACGTACGT"
        assert store.material_member(member["id"])["quality"] == "IIIIIIII"


def test_wrapper_failure_without_emitted_bytes_retains_original_and_explicit_empty_prefix(tmp_path):
    wrapper = b"\x1f\x8bmalformed"
    with Store(tmp_path / "store") as store:
        store.create_problem(raw_sequence="MKWV", molecule="protein")
        material = store.register_material(data=wrapper, role="read", molecule="dna")
        attempt = store.parse_material(material["id"])
        assert attempt["status"] == "failed" and attempt["valid_records"] == 0
        errors = store.material_errors(attempt["id"])["errors"]
        assert len(errors) == 1 and errors[0]["code"] == "gzip_decode_incomplete"
        assert errors[0]["decoded_prefix_bytes"] == 0
        decoded = store.get(attempt["source_ref"])
        assert store.get_artifact(decoded["artifact_ref"]) == b""
        assert decoded["parent_source_refs"] == [material["source_ref"]]
        assert store.get_artifact(store.get(material["source_ref"])["artifact_ref"]) == wrapper
        assert store.db.execute("SELECT count(*) FROM material_members").fetchone()[0] == 1  # Only the scalar control target.
