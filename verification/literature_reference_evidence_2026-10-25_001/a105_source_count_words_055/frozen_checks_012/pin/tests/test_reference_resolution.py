"""Real Store admission/namespace equivalence and bounded resolver reads.

Synthetic material/claims exercise contracts, never biological correctness.
"""
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import ReportBoundaryError, validate_form
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


def resolver(store, scope):
    return Workflow.resolver(SimpleNamespace(store=store), scope)


def hypothesis(store, subject, context_refs=()):
    return store.put("hypothesis", {"subject_refs": [subject],
        "predicate": "sequence_integrity", "value": {"type": "enum", "value": "unknown"},
        "context_refs": list(context_refs)}, origin="reasoning")


def forbidden(*args, **kwargs):
    raise AssertionError("a form reference must not enumerate the full registry or read source bodies")


def test_resolver_preserves_full_registry_namespaces_and_scope(tmp_path, monkeypatch):
    fasta = tmp_path / "inputs.fasta"
    fasta.write_text(">left\nMACT\n>right\nMKKK\n")
    with Store(tmp_path / "store") as store:
        left, right = store.create_problem(fasta, format="fasta", molecule="protein")["subject_refs"]
        scope = {"subject_refs": [left]}
        foreign = hypothesis(store, right)
        local = hypothesis(store, left, [foreign["id"]])
        material = store.register_material(data=b"Synthetic source text", use="evidence")
        source = store.get(material["source_ref"])
        diagnostic = store.artifact(b"Private unowned diagnostic")
        registry = store.references(scope)
        candidates = [left, right, local["id"], foreign["id"], source["id"],
            source["artifact_ref"], diagnostic, "hypothesis_" + "0" * 24]
        expected = {(ref, ns): ref in registry.get(ns, ()) for ref in candidates
                    for ns in [*registry, "missing_namespace"]}
        expected.update({(ref, None): any(ref in values for values in registry.values())
                         for ref in candidates})
        monkeypatch.setattr(store, "references", forbidden)
        monkeypatch.setattr(store, "list", forbidden)
        monkeypatch.setattr(store, "get_artifact", forbidden)
        resolve = resolver(store, scope)
        for (ref, namespace), allowed in expected.items():
            assert resolve(ref, namespace) == allowed, (ref, namespace)
        assert resolve(left, "subject") and resolve(source["id"], "source")
        assert not resolve(right) and not resolve(foreign["id"])
        assert not resolve(source["id"], "subject") and not resolve(diagnostic)
        # The foreign record remains readable context; form membership did not
        # invent a ban on scientific source inspection across assigned scopes.
        assert store.get(foreign["id"]) == foreign


def test_member_custody_header_activation_and_actual_form(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        target = store.create_problem(raw_sequence="MACT")["subject_refs"][0]
        scope = {"subject_refs": [target]}
        material = store.register_material(data=b"@read native title\nACGT\n+\nIIII\n",
            format="fastq", use="evidence", role="read")
        attempt = store.parse_material(material["id"])
        member = store.material_members(attempt["collection_ref"])["members"][0]["id"]
        header = store.material_header(member)["artifact_ref"]
        schema = {"type": "object", "additionalProperties": False, "required": ["bytes"],
            "properties": {"bytes": {"type": "string", "format": "reference",
                                       "x-reference-namespace": "artifact"}}}
        monkeypatch.setattr(store, "references", forbidden)
        resolve = resolver(store, scope)
        assert not resolve(member) and not resolve(header)
        with pytest.raises(ReportBoundaryError):
            validate_form({"bytes": header}, schema, resolve)
        registered = store.material_reference(member)
        assert resolve(header, "artifact") and resolve(registered["id"], "reference")
        assert not resolve(member) and not resolve(registered["id"], "subject")
        assert validate_form({"bytes": header}, schema, resolve) == {"bytes": header}


def test_resolver_does_not_hydrate_unrelated_record_rows(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        target = store.create_problem(raw_sequence="MACT")["subject_refs"][0]
        selected = hypothesis(store, target)
        # Labelled bulk metadata fixture, without payload/source reads. It is
        # not an annotation quality or production-scale timing benchmark.
        for index in range(120):
            store.register_material(data=(f"Synthetic unrelated record {index} "+"x"*2000).encode(),
                                    use="evidence")
        calls = []
        original_get = store.get
        def selected_only(ref):
            calls.append(ref)
            assert ref in {target, selected["id"]}, "unrelated record hydrated"
            return original_get(ref)
        monkeypatch.setattr(store, "get", selected_only)
        monkeypatch.setattr(store, "references", forbidden)
        monkeypatch.setattr(store, "list", forbidden)
        monkeypatch.setattr(store, "get_artifact", forbidden)
        resolve = resolver(store, {"subject_refs": [target]})
        assert resolve(selected["id"], "hypothesis")
        assert not resolve(selected["id"], "observation")
        assert set(calls) == {selected["id"]}


def test_subject_namespace_keeps_actual_mapped_features_and_products(tmp_path, monkeypatch):
    fasta = tmp_path / "inputs.fasta"
    fasta.write_text(">left\nMACT\n>right\nMKKK\n")
    with Store(tmp_path / "store") as store:
        left, right = store.create_problem(fasta, format="fasta", molecule="protein")["subject_refs"]
        tools = ToolRegistry(store)
        subjects = {}
        for target in (left, right):
            result = tools.execute("sequence.view", {"subject_ref": target,
                "molecule": "protein", "segments": [{"start": 0, "end": 2}]})
            assert result["status"] == "completed"
            subjects[target] = [ref for ref in result["record_refs"]
                if store.get(ref)["record_type"] in {"feature", "product"}]
            assert {store.get(ref)["record_type"] for ref in subjects[target]} == {"feature", "product"}
        scope = {"subject_refs": [left]}
        original = store.references(scope)
        monkeypatch.setattr(store, "references", forbidden)
        resolve = resolver(store, scope)
        for target, refs in subjects.items():
            for ref in refs:
                kind = store.get(ref)["record_type"]
                assert resolve(ref, "subject") == (ref in original["subject"]) == (target == left)
                assert resolve(ref, kind) == (target == left)
                assert not resolve(ref, "input") and not resolve(ref, "reference")
