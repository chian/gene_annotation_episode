"""Real native derivation → immutable state → exact original-unit projections.

Synthetic input is intentionally not evidence of an actual gene/function.
"""
from copy import deepcopy
import json

from Bio.Seq import Seq
import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.export import export_annotation
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


def feature(store, subject, segments, strand=".", scope=None):
    return store.put("feature", {"subject_ref": subject, "kind": "sequence_region",
        "segments": segments, "strand": strand, "context_refs": []}, origin="reasoning", scope=scope)


def derive(store, subject, **arguments):
    result = ToolRegistry(store).execute("sequence.translate", {"subject_ref": subject, "code": 11, **arguments})
    assert result["status"] == "completed", result
    refs = result["result"]["records"][0]
    return store.get(refs["feature_ref"]), store.get(refs["product_ref"])


def original_symbols(store, paths):
    pieces = []
    for row in paths:
        sequence = store.get_artifact(store.get_input(row["subject_ref"])["sequence_ref"]).decode()
        piece = sequence[row["start"]:row["end"]]
        pieces.append(str(Seq(piece).reverse_complement()) if row["strand"] == "-" else piece)
    return "".join(pieces)


@pytest.mark.parametrize("strand,cds", [("+", False), ("-", False), ("+", True), ("-", True)])
def test_actual_tool_emitted_symbols_and_terminal_stop_have_exact_original_codons(tmp_path, strand, cds):
    sequence = "ATGAAAGGGTAA"
    if strand == "-":
        sequence = str(Seq(sequence).reverse_complement())
    with Store(tmp_path / "db") as store:
        store.create_problem(raw_sequence="CCC" + sequence + "GGG", molecule="dna")
        target = store.targets()[0]
        full, product = derive(store, target["id"], start=3, end=15, strand=strand, cds=cds)
        assert full["segments"] == [{"start": 3, "end": 15}]
        protein = store.get_artifact(product["sequence_ref"]).decode()
        assert protein == ("MKG" if cds else "MKG*")
        assert store.has_exact_mapping(product["id"])
        mapping = store.sequence_mapping(product["id"])
        assert mapping["symbol_length"] == len(protein)
        assert mapping["units_per_symbol"] == 3
        assert str(Seq(original_symbols(store, mapping["path"])).translate(table=11)) == protein
        expected = (6, 15) if cds and strand == "-" else (3, 12) if cds else (3, 15)
        assert store.coverage(product["id"]) == [{"target_ref": target["id"],
            "start": expected[0], "end": expected[1], "unit": "nt"}]
        source = store.get(product["mapping_source_ref"])
        assert source["origin"] == "tool" and source["provider"] == "sequence.translate"
        native = json.loads(store.get_artifact(source["artifact_ref"]))
        assert native["omitted_terminal_stop"] == cds


def test_reverse_frame_offsets_and_nested_product_feature_use_fixed_local_scope(tmp_path):
    with Store(tmp_path / "db") as store:
        store.create_problem(raw_sequence="CCCTTATTTCATGGGG", molecule="dna")
        target = store.targets()[0]
        _, product = derive(store, target["id"], start=3, end=13, strand="-", frame=1)
        assert store.get_artifact(product["sequence_ref"]) == b"MK*"
        expected = [{"target_ref": target["id"], "start": 6, "end": 9, "unit": "nt"}]
        scope = {"subject_refs": [target["id"]], "segments": expected}
        nested = feature(store, product["id"], [{"start": 1, "end": 2}], scope=scope)
        assert store.coverage(nested["id"]) == expected
        assert store.map_segments(product["id"], [{"start": 1, "end": 2}]) == expected
        with pytest.raises(ContractError, match="record_outside_scope_segments"):
            feature(store, product["id"], [{"start": 0, "end": 2}], scope=scope)


@pytest.mark.parametrize("reverse_feature", [False, True])
def test_real_split_feature_translation_maps_codon_across_segments(tmp_path, reverse_feature):
    with Store(tmp_path / "db") as store:
        store.create_problem(raw_sequence="ATGACCCCAAGGGTAA", molecule="dna")
        target = store.targets()[0]
        extracted = feature(store, target["id"], [{"start": 0, "end": 4}, {"start": 8, "end": 16}],
                            strand="-" if reverse_feature else "+")
        # Double reversal is chosen explicitly; no reordering of source segments.
        _, product = derive(store, extracted["id"], strand="-" if reverse_feature else "+")
        assert store.get_artifact(product["sequence_ref"]) == b"MKG*"
        codon = store.map_segments(product["id"], [{"start": 1, "end": 2}])
        assert codon == [{"target_ref": target["id"], "start": 3, "end": 4, "unit": "nt"},
                         {"target_ref": target["id"], "start": 8, "end": 10, "unit": "nt"}]
        assert original_symbols(store, store.sequence_mapping(product["id"])["path"]) == "ATGAAAGGGTAA"


def test_old_aggregate_products_cannot_gain_a_residue_map_from_matching_lengths(tmp_path):
    with Store(tmp_path / "db") as store:
        store.create_problem(raw_sequence="ATGAAATAA", molecule="dna")
        target = store.targets()[0]
        parent = feature(store, target["id"], [{"start": 0, "end": 9}])
        aggregate = store.put("product", {"parent_refs": [parent["id"]], "molecule": "protein",
            "sequence_ref": store.artifact("MK*"), "derivation": "translation", "context_refs": [],
            "footprint": store.coverage(parent["id"])}, origin="tool")
        assert not store.has_exact_mapping(aggregate["id"])
        assert store.map_segments(aggregate["id"], [{"start": 0, "end": 3}]) == store.coverage(parent["id"])
        with pytest.raises(ContractError, match="subregion_mapping_unavailable"):
            feature(store, aggregate["id"], [{"start": 1, "end": 2}])
        assert store.list("product") == [aggregate]


def test_mapping_source_and_exact_length_are_required_not_plausible_parent_lengths(tmp_path):
    with Store(tmp_path / "db") as store:
        store.create_problem(raw_sequence="ATGAAATAA", molecule="dna")
        _, product = derive(store, store.targets()[0]["id"])
        payload = {key: value for key, value in product.items() if key not in {"id", "origin", "record_type"}}
        bad = deepcopy(payload)
        bad.pop("mapping_source_ref")
        with pytest.raises(ContractError, match="mapping_and_source_required_together"):
            store.put("product", bad, origin="tool")
        bad = deepcopy(payload)
        bad["mapping"]["path"][0]["end"] -= 3
        with pytest.raises(ContractError, match="mapping_length_mismatch"):
            store.put("product", bad, origin="tool")
        source = store.get(product["mapping_source_ref"])
        external = store.put("source", {key: value for key, value in source.items()
            if key not in {"id", "record_type", "origin"}}, origin="external")
        bad = deepcopy(payload)
        bad["mapping_source_ref"] = external["id"]
        with pytest.raises(ContractError, match="native_derivation_mapping_source_required"):
            store.put("product", bad, origin="tool")
        assert len(store.list("product")) == 1


def test_mapping_reopens_and_metadata_projection_does_not_hydrate_sequences(tmp_path, monkeypatch):
    path = tmp_path / "db"
    with Store(path) as store:
        store.create_problem(raw_sequence="ATGAAATAA", molecule="dna")
        target = store.targets()[0]["id"]
        _, product = derive(store, target, cds=True)
        product_ref = product["id"]
    with Store(path) as store:
        monkeypatch.setattr(store, "get_artifact", lambda _: pytest.fail("metadata mapping hydrated a sequence"))
        assert store.map_segments(product_ref, [{"start": 1, "end": 2}]) == [
            {"target_ref": target, "start": 3, "end": 6, "unit": "nt"}]


def test_export_keeps_native_mapping_provenance_and_full_feature_separate(tmp_path):
    with Store(tmp_path / "db") as store:
        store.create_problem(raw_sequence="TTATTTCAT", molecule="dna")
        target = store.targets()[0]["id"]
        full, product = derive(store, target, strand="-", cds=True)
        result = export_annotation(store, tmp_path / "mapping.gff3", format="gff3", page_size=1)
        document = json.loads((tmp_path / "mapping.gff3.annotation.json").read_text())
        records = {row["id"]: row for row in document["records"]}
        assert records[full["id"]]["segments"] == [{"start": 0, "end": 9}]
        assert records[product["id"]]["footprint"] == [{"target_ref": target, "start": 3, "end": 9, "unit": "nt"}]
        assert records[product["mapping_source_ref"]]["provider"] == "sequence.translate"
        assert records[product["id"]]["mapping"] == product["mapping"]
        assert result["gff3"]["emitted_features"] == 1


@pytest.mark.parametrize("code", [4, 11])
def test_real_installed_pyrodigal_partial_prediction_has_exact_native_interval(tmp_path, code):
    with Store(tmp_path / "db") as store:
        store.create_problem(raw_sequence="ATG" + "AAA" * 100 + "TAA", molecule="dna")
        target = store.targets()[0]["id"]
        tools = ToolRegistry(store)
        result = tools.execute("genes.predict", {"subject_ref": target, "code": code, "mode": "meta"})
        assert result["status"] == "completed", result
        assert result["result"]["count"] >= 1
        native = json.loads(store.get_artifact(store.get(result["result"]["source_ref"])["artifact_ref"]))
        assert native["translation_code"] == code
        assert any(row["partial_begin"] or row["partial_end"] for row in native["candidates"])
        for product in store.list("product"):
            protein = store.get_artifact(product["sequence_ref"]).decode()
            path = store.sequence_mapping(product["id"])["path"]
            assert sum(row["end"] - row["start"] for row in path) == 3 * len(protein)
            assert str(Seq(original_symbols(store, path)).translate(table=code)) == protein
            assert store.get(product["mapping_source_ref"])["provider"] == "genes.predict"


def test_unrepresentable_later_native_codon_interval_preserves_prior_publication(tmp_path, monkeypatch):
    """Injected malformed native output tests feedback, never a biological claim."""
    from gene_annotation_episode import tools as tool_module
    calls = []
    def malformed_native(sequence, **kwargs):
        calls.append(kwargs)
        first = {"start": 0, "end": 6, "strand": "+", "protein_sequence": "MK",
                 "native_confidence": 50., "native_score": 3., "partial_begin": False, "partial_end": True}
        return {"candidates": [first, {**first, "start": 6, "end": 10}], "limitations": []}
    async def synthetic_worker(self, operation, arguments, *, directory):
        assert operation == "predict_genes"
        output = directory / "synthetic-result.json"
        output.write_text(json.dumps(malformed_native(**arguments)))
        return tool_module.SequenceWork(output, {"execution": "explicitly_synthetic_test_worker"})
    monkeypatch.setattr(tool_module.ToolRegistry, "_sequence_worker_async", synthetic_worker)
    with Store(tmp_path / "db") as store:
        store.create_problem(raw_sequence="ATGAAAATGA", molecule="dna")
        target = store.targets()[0]["id"]
        registry = ToolRegistry(store)
        args = {"subject_ref": target, "code": 11, "mode": "meta"}
        result = registry.execute("genes.predict", args, operation_key="partial-native-fixture")
        assert result["status"] == "partial", result
        assert result["feedback"]["code"] == "translation_mapping_length_mismatch"
        assert len(store.list("product")) == 1
        product = store.list("product")[0]
        assert product["id"] in result["record_refs"]
        assert product["mapping_source_ref"] in result["record_refs"]
        assert result["result"]["retained_record_refs"] == result["record_refs"]
        assert registry.execute("genes.predict", args, operation_key="partial-native-fixture") == result
        assert len(calls) == 1

