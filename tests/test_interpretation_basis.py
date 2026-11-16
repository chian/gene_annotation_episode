"""Actual Store/runtime boundaries with scripted decisions, not model science."""

from gene_annotation_episode.episodic_workflow.root.reference_selection import _references_in
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.tool_registry import ToolRegistry
from test_runtime import obj


def test_basis_uses_typed_positions_and_indexed_identity_without_body_or_registry_reads(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        target = store.create_problem(raw_sequence="MACT")["subject_refs"][0]
        material = store.register_material(data=b"Synthetic exact source body", use="evidence")
        source = store.get(material["source_ref"])
        source_ref, artifact_ref = source["id"], source["artifact_ref"]
        diagnostic = store.artifact(b"Synthetic private execution diagnostic", "text/plain")
        def forbidden(*args, **kwargs):
            raise AssertionError("basis must not load source bytes or expand all reference registries")
        monkeypatch.setattr(store, "get_artifact", forbidden)
        monkeypatch.setattr(store, "references", forbidden)
        unknown = "source_" + "0" * 24
        audit = "episode_internal_audit_identity"
        supplied = {"record": store.get_input(target),
            "native_provider_payload": {"id": source_ref},  # untyped provider id is not a record
            "unregistered_native_record": {"id": unknown, "record_type": "source"},
            "wrong_record_kind": {"id": artifact_ref, "record_type": "source"},
            "free_text": source_ref, "quote": artifact_ref, "description": source_ref,
            "diagnostic_ref": diagnostic, "operation_ref": audit, "source_ref": unknown}
        visible = _references_in(supplied, store.get, reference_subset=store.reference_subset)
        assert target in visible
        assert not {source_ref, artifact_ref, unknown, audit, diagnostic} & set(visible)
        assert not any(ref.startswith("member_") for ref in visible)
        form = {"chosen": [{"handle": source_ref}], "code": artifact_ref}
        schema = obj({"chosen": {"type": "array", "items": obj({"handle": {
            "type": "string", "format": "reference", "description": unknown}})},
            "code": {"type": "string", "enum": [artifact_ref], "description": source_ref}})
        visible = _references_in({}, store.get, forms=[(form, schema)], reference_subset=store.reference_subset)
        assert visible == [source_ref]  # enum/text/example strings are not references
        assert _references_in({"source_ref": source_ref, "artifact_ref": artifact_ref}, store.get,
            reference_subset=store.reference_subset) == [source_ref, artifact_ref]


def test_current_typed_report_reference_is_visible_without_claiming_its_body_read(tmp_path):
    with Store(tmp_path / "store") as store:
        store.create_problem(raw_sequence="MACT")
        material = store.register_material(data=b"unread original bytes", use="evidence")
        source = store.get(material["source_ref"])
        schema = obj({"chosen": {"type": "string", "format": "reference"}})
        visible = _references_in({}, store.get, forms=[({"chosen": source["id"]}, schema)],
            reference_subset=store.reference_subset)
        assert visible == [source["id"]]
        assert source["artifact_ref"] not in visible


def test_candidate_artifacts_match_existing_registry_before_and_after_member_registration(tmp_path):
    with Store(tmp_path / "store") as store:
        target = store.create_problem(raw_sequence="MACT")["subject_refs"][0]
        material = store.register_material(data=b"@native_read description\nACGT\n+\nIIII\n",
            format="fastq", use="evidence", molecule="dna", role="read", quality_encoding="phred33")
        attempt = store.parse_material(material["id"])
        member_ref = store.material_members(attempt["collection_ref"])["members"][0]["id"]
        header = ToolRegistry(store, run_directory=store.path / 'tool-run').execute("material.header", {"member_ref": member_ref})
        assert header["status"] == "completed"
        header_ref = header["result"]["artifact_ref"]
        source = store.get(material["source_ref"])
        private = store.artifact(b"private operational response, not scientific material", "text/plain")
        candidates = [target, member_ref, header_ref, source["artifact_ref"], private]
        existing = {ref for values in store.references().values() for ref in values}
        assert set(store.reference_subset(candidates)) == set(candidates) & existing
        assert header_ref not in existing and member_ref not in existing and private not in existing
        # An actual operational artifact in a generic *_ref position, and even
        # a selected artifact metadata row, cannot escape the existing registry.
        supplied = {"source_ref": source["id"], "response_ref": private,
            "artifact": store.get(private), "selected_header": header["result"]}
        basis = _references_in(supplied, store.get, reference_subset=store.reference_subset)
        assert source["id"] in basis and source["artifact_ref"] not in basis
        assert private not in basis and header_ref not in basis and member_ref not in basis
        reference = store.material_reference(member_ref)
        existing = {ref for values in store.references().values() for ref in values}
        assert set(store.reference_subset(candidates)) == set(candidates) & existing
        assert header_ref in existing and private not in existing and member_ref not in existing
        basis = _references_in(header["result"], store.get, reference_subset=store.reference_subset)
        assert header_ref in basis and reference["id"] not in basis


def test_cross_scope_context_stays_readable_without_broadening_existing_form_scope(tmp_path):
    fasta = tmp_path / "inputs.fasta"
    fasta.write_text(">left\nMACT\n>right\nMKKK\n")
    with Store(tmp_path / "store") as store:
        left, right = store.create_problem(input_path=fasta, format="fasta", molecule="protein")["subject_refs"]
        scope = {"subject_refs": [left]}
        foreign = store.put("hypothesis", {"subject_refs": [right], "predicate": "sequence_integrity",
            "value": {"type": "enum", "value": "unknown"}, "context_refs": []}, origin="reasoning")
        local = store.put("hypothesis", {"subject_refs": [left], "predicate": "sequence_integrity",
            "value": {"type": "enum", "value": "unknown"}, "context_refs": [foreign["id"]]},
            origin="reasoning", scope=scope)
        queried = ToolRegistry(store, run_directory=store.path / 'tool-run').execute("state.query", {"refs": [foreign["id"]]}, scope=scope)
        assert queried["status"] == "completed" and queried["result"]["records"] == [foreign]
        supplied = {"local_record": local, "actual_query": queried}
        candidates = [left, right, local["id"], foreign["id"]]
        existing = {ref for values in store.references(scope).values() for ref in values}
        assert set(store.reference_subset(candidates, scope)) == set(candidates) & existing
        basis = _references_in(supplied, store.get,
            reference_subset=lambda refs: store.reference_subset(refs, scope))
        assert local["id"] in basis and left in basis
        assert foreign["id"] not in basis and right not in basis
        assert local["context_refs"] == [foreign["id"]]  # no scientific or read restriction added
