"""Real Store/native tools; downloaded reference replay is labelled explicitly."""
from dataclasses import replace
from pathlib import Path

from gene_annotation_episode.acquisition import PublicClients, SourceSnapshot
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


def test_translation_is_an_explicit_derived_product_and_replays_once(tmp_path):
    with Store(tmp_path) as store:
        problem = store.create_problem(raw_sequence="ATGTGAGGGTAA", molecule="dna", role="gene")
        target = problem["subject_refs"][0]
        tools = ToolRegistry(store)
        args = {"subject_ref": target, "code": 25}
        first = tools.execute("sequence.translate", args, operation_key="translation-one")
        assert first["status"] == "completed", first
        product = store.get(first["result"]["records"][0]["product_ref"])
        assert store.get_artifact(product["sequence_ref"]) == b"MGG*"
        assert product["footprint"] == [{"target_ref": target, "start": 0, "end": 12, "unit": "nt"}]
        assert store.get_artifact(store.get_input(target)["sequence_ref"]) == b"ATGTGAGGGTAA"
        assert tools.execute("sequence.translate", args, operation_key="translation-one") == first
        assert len(store.list("product")) == 1
        assert store.problem() == problem


def test_source_and_exact_pages_are_readable_without_becoming_target_features(tmp_path):
    with Store(tmp_path) as store:
        problem = store.create_problem(raw_sequence="MKWVTFISLLFLFSSAYSRGVFRRDTHKSEIAHRFKDLGE", molecule="protein", role="protein")
        tools = ToolRegistry(store)
        result = tools.execute("sequence.inspect", {"subject_ref": problem["subject_refs"][0]})
        assert result["status"] == "completed"
        source_ref = next(ref for ref in result["record_refs"] if ref.startswith("source_"))
        exact = tools.execute("state.query", {"refs": [source_ref]})
        assert exact["status"] == "completed", exact
        assert exact["result"]["records"][0]["id"] == source_ref
        first = tools.execute("source.read", {"source_ref": source_ref, "limit": 20})
        following = tools.execute("source.read", {"source_ref": source_ref, "offset": first["result"]["next_offset"], "limit": 20})
        assert following["result"]["start"] == first["result"]["end"]
        assert not store.list("feature")
        assert not store.list("product")


def test_bad_local_operation_is_feedback_without_new_scientific_records(tmp_path):
    with Store(tmp_path) as store:
        problem = store.create_problem(raw_sequence="MKWVTFISLLFLFSSAYSRGVFRRDTHKSEIAHRFKDLGE", molecule="protein")
        tools = ToolRegistry(store)
        result = tools.execute("sequence.translate", {"subject_ref": problem["subject_refs"][0], "code": 11})
        assert result["status"] == "invalid"
        assert not result["record_refs"]
        assert not store.list("feature")
        assert not store.list("product")


def test_source_utf8_window_reports_size_and_boundary_differently(tmp_path):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence="MACD", molecule="protein")
        body = store.artifact("αbc", "text/plain")
        source = store.put("source", {"provider": "test_source", "accession": None, "uri": None,
            "artifact_ref": body, "text_ref": None, "request_ref": None, "version": None, "retrieved_at": None}, origin="caller")
        tools = ToolRegistry(store)
        too_small = tools.execute("source.read", {"source_ref": source["id"], "offset": 0, "limit": 1})
        assert too_small["feedback"]["code"] == "source_window_too_small_for_character"
        invalid_offset = tools.execute("source.read", {"source_ref": source["id"], "offset": 1, "limit": 2})
        assert invalid_offset["feedback"]["code"] == "source_offset_not_utf8_boundary"
        good = tools.execute("source.read", {"source_ref": source["id"], "offset": 0, "limit": 3})
        assert good["result"]["text"] == "αb" and good["result"]["next_offset"] == 3


def test_downloaded_reference_replay_pins_source_and_compares_actual_sequences(tmp_path):
    # This is replay of an actual downloaded source, not a new API result or
    # biological benchmark. It verifies the importer/alignment/state boundary.
    import pytest
    saved = Path(__file__).parents[1]/"validation/acquisition/uniprot-P0A7V8.json"
    if not saved.exists():
        pytest.skip("external reference replay artifact not installed")
    class RecordedClient:
        def uniprot_record(self, accession):
            assert accession == "P0A7V8"
            return SourceSnapshot("uniprot", "https://rest.uniprot.org/uniprotkb/P0A7V8",
                {"accession": accession}, "2026-10-19T23:38:15.234956+00:00", saved.read_bytes(),
                "application/json", {"representation": "explicit_saved_source_replay"})
    with Store(tmp_path) as store:
        problem = store.create_problem(raw_sequence="MKWVTFISLLFLFSSAYSRGVFRRDTHKSEIAHRFKDLGE", molecule="protein")
        tools = ToolRegistry(store, clients=RecordedClient())
        imported = tools.execute("public.uniprot.record", {"accession": "P0A7V8"})
        assert imported["status"] == "completed", imported
        reference = imported["result"]["records"][0]
        assert reference["record_type"] == "reference" and reference["length"] == 206
        assert store.problem() == problem
        assert not store.list("feature")
        result = tools.execute("sequence.align", {"query_ref": problem["subject_refs"][0],
            "reference_ref": reference["id"], "molecule": "protein", "mode": "global"})
        assert result["status"] == "completed", result
        observation = store.get(result["result"]["observation_ref"])
        assert observation["source_subject_refs"] == [reference["id"]]
        assert observation["subject_refs"] == problem["subject_refs"]
        assert not store.current_annotations()
