"""Private document joins and rejection boundaries, with no producer proof.

Supplied engineering JSON becomes real owned Artifact files only. No Source,
runtime action, episode, native worker or authentic publication is fabricated.
The genuine workflow check separately owns positive producer/custody evidence.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode import protein_conservation_publication as publication
from gene_annotation_episode import protein_conservation_result_contracts as contracts
from gene_annotation_episode import phylogeny_calculators, phylogeny_formats
from gene_annotation_episode import phylogeny_calculation_contracts as numerical
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


_CAPTURE = "source_" + "c" * 24


def _forbidden(*args, **kwargs):
    raise AssertionError("publication must not parse, calculate or open original native/input data")


def _file(store, value, format):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode() + b"\n"
    reference = store.artifact(raw, "application/json")
    return dict(artifact_ref=reference, sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw), format=format)


@pytest.fixture
def documents(tmp_path, monkeypatch):
    fixture = json.loads((Path(__file__).parent / "fixtures/protein_conservation/supplied_alignment.json").read_bytes())
    assert fixture["provenance"]["kind"] == "supplied_engineering_json"
    assert fixture["provenance"]["producer_authenticated"] is False
    with Store(tmp_path / "store") as store:
        registry = ToolRegistry(store)
        raw = fixture["raw_output_utf8"].encode()
        assert store.artifact(raw, "text/x-fasta") == fixture["alignment"]["artifact"]["raw_artifact_ref"]
        assert store.artifact(fixture["raw_input_utf8"].encode(), "text/x-fasta") == \
            fixture["input_record"]["file"]["artifact_ref"]
        alignment = deepcopy(fixture["alignment"])
        alignment["artifact"]["source_ref"] = _CAPTURE
        for row in alignment["rows"]:
            row["source_location"]["artifact"]["source_ref"] = _CAPTURE
        population = deepcopy(fixture["population"])
        population["evidence"][0]["content"]["source_ref"] = _CAPTURE
        components = deepcopy(fixture["components"])
        arguments = dict(mode="run_native", input=fixture["input_record"]["selection"],
            population_request=fixture["population_request"], selection=fixture["selection"])
        value = contracts.conservation_public_value(alignment=alignment,
            population_request=arguments["population_request"], population=population, components=components,
            input_record=fixture["input_record"], native_execution=fixture["native_execution"],
            associations=fixture["associations"], selection=arguments["selection"], issues=fixture["issues"])
        context = dict(version=publication.result_worker.CONTEXT_VERSION,
            **{key: deepcopy(value["context"][key]) for key in
                ("input", "native_execution", "alignment", "row_associations", "issues")})
        values = dict(alignment_file=alignment, context_file=context,
            population_file=population, components_file=components, value_file=value)
        files = {key: _file(store, item, publication._FILE_FIELDS[key]) for key, item in values.items()}
        for module, names in ((phylogeny_formats, ("parse_aligned_fasta",)),
                (phylogeny_calculators, ("literal_site_conservation", "alignment_components")),
                (numerical, ("ratio", "quantity"))):
            for name in names:
                monkeypatch.setattr(module, name, _forbidden)
        yield registry, arguments, files, values


def test_owned_documents_join_literal_values_without_claiming_a_source_or_producer(documents, monkeypatch):
    registry, arguments, files, supplied = documents
    allowed = {row["artifact_ref"] for row in files.values()}
    original, reads = publication._publication_bytes, []
    def read(store, reference):
        assert reference in allowed
        reads.append(reference)
        return original(store, reference)
    monkeypatch.setattr(publication, "_publication_bytes", read)
    checked = publication._file_values(registry, files)
    value = publication._documents(registry, checked, arguments)
    assert value["alignment"] == supplied["alignment_file"]
    assert value["population"] == supplied["population_file"]
    assert value["components"] == supplied["components_file"]
    assert value["value"] == supplied["value_file"]
    assert set(reads) == allowed and len(reads) == len(allowed)
    assert "source_ref" not in value["value"]
    assert registry.store.db.execute("SELECT count(*) FROM records WHERE record_type='source'").fetchone()[0] == 0
    assert registry.store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 0


@pytest.mark.parametrize("change", ["alignment_metadata", "population_evidence", "value_quantity", "value_selection"])
def test_contradictory_private_documents_never_become_an_accepted_view(documents, change):
    registry, arguments, files, supplied = documents
    values = deepcopy(supplied)
    if change == "alignment_metadata":
        values["context_file"]["alignment"]["observed_row_count"] += 1
        key = "context_file"
    elif change == "population_evidence":
        values["population_file"]["evidence"][0]["content"]["source_ref"] = "source_" + "e" * 24
        key = "population_file"
    elif change == "value_quantity":
        values["value_file"]["context"]["member_count"]["value"] = 99
        key = "value_file"
    else:
        values["value_file"]["selection"]["native_rows"]["offset"] = 1
        key = "value_file"
    changed = dict(files, **{key: _file(registry.store, values[key], publication._FILE_FIELDS[key])})
    with pytest.raises(ValueError):
        publication._documents(registry, publication._file_values(registry, changed), arguments)
    assert registry.store.db.execute("SELECT count(*) FROM records WHERE record_type='source'").fetchone()[0] == 0


@pytest.mark.parametrize("change", ["format", "missing_context", "missing_components"])
def test_invalid_document_metadata_denies_before_private_artifact_bytes(documents, monkeypatch, change):
    registry, _, files, _ = documents
    files = deepcopy(files)
    if change == "format": files["alignment_file"]["format"] = "fasta"
    elif change == "missing_context": files["context_file"] = None
    else: files["components_file"] = None
    monkeypatch.setattr(publication, "_publication_bytes", _forbidden)
    with pytest.raises(ValueError):
        publication._file_values(registry, files)


def test_private_file_projection_preserves_explicit_original_input_role_collisions():
    original, request, manifest, context = ("artifact_" + letter * 64 for letter in "abcd")
    capture = dict(artifact_ref=original, request_ref=request,
        auxiliary_artifact_refs=[original, manifest, request])
    files = dict(alignment_file=dict(artifact_ref=original), context_file=dict(artifact_ref=context),
        population_file=None, components_file=None, value_file=dict(artifact_ref="artifact_" + "e" * 64))
    assert publication._private_files(capture, files, [original]) == [request, manifest, context]


def test_publication_requires_transaction_before_any_source_or_file_access():
    registry = SimpleNamespace(store=SimpleNamespace(db=SimpleNamespace(in_transaction=False)))
    with pytest.raises(ValueError, match="protein_conservation_publication_transaction_required"):
        publication._publish(registry, {}, {}, {}, {}, {}, None)


def test_invalid_fact_shape_denies_before_context_or_store_access():
    with pytest.raises(ValueError):
        publication.validate_protein_conservation_fact(object(), None, _forbidden, {})


@pytest.mark.parametrize("change", ["name", "format"])
def test_component_declaration_cannot_select_another_private_path(monkeypatch, change):
    declaration = dict(relative_path="alignment.json", format=publication.result_worker.ALIGNMENT_FORMAT,
        sha256="a" * 64, size_bytes=10)
    declaration["relative_path" if change == "name" else "format"] = "unselected"
    monkeypatch.setattr(publication, "capture_native_file", _forbidden)
    with pytest.raises(ValueError, match="protein_conservation_component_declaration_conflict"):
        publication._capture_component(object(), "/unopened", declaration, "alignment")


@pytest.mark.parametrize("version", [contracts.SOURCE_VERSION, publication.CAPTURE_VERSION])
def test_conservation_receipt_policy_keeps_declared_source_dependencies_private(version):
    """Classify supplied metadata only; this establishes no Source custody."""
    from gene_annotation_episode.episode_receipts import EpisodeReceipts
    receipts = object.__new__(EpisodeReceipts)
    receipts.store = SimpleNamespace(_refs=_forbidden)
    metadata = dict(record_type="source", origin="tool", provider=contracts.TOOL, version=version)
    assert receipts.forward_references(metadata) == []


@pytest.mark.parametrize("change", ["provider", "version", "record_type", "origin"])
def test_conservation_receipt_policy_does_not_reclassify_other_record_metadata(change):
    from gene_annotation_episode.episode_receipts import EpisodeReceipts
    receipts = object.__new__(EpisodeReceipts)
    seen = []
    def references(value):
        seen.append(value)
        return ["supplied dependency marker"]
    receipts.store = SimpleNamespace(_refs=references)
    metadata = dict(record_type="source", origin="tool", provider=contracts.TOOL,
        version=contracts.SOURCE_VERSION)
    metadata[change] = "other"
    assert receipts.forward_references(metadata) == ["supplied dependency marker"]
    assert seen == [metadata]
