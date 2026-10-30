"""Produce retained local service examples; no network, host admission or model.

Run from the repository root with .venv/bin/python and this file's path.
This reuses the explicitly labeled service test fixtures, while every result,
sheet and numerical component is produced by the production publication path.
"""
from pathlib import Path
import json
import socket
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from test_api_bvbrc_data_v2 import (
    EVIDENCE, EXAMPLES, FEATURE_IDS, FIELD_REGISTRY, MOLECULAR_MEASUREMENT_FIELDS,
    BVBRCDataService, Store, ToolRegistry, envelope, input_page, input_selections,
    publish, request, retained_rows, selector,
)


def forbidden(*args, **kwargs):
    raise AssertionError("verification must not acquire data")


def main():
    urllib.request.OpenerDirector.open = forbidden
    socket.create_connection = forbidden
    output = Path(__file__).resolve().parent
    summaries = {}
    with Store(output / "example_store") as store:
        problem = store.create_problem(raw_sequence="MACDEFGH", molecule="protein")
        scope = {"subject_refs": problem["subject_refs"]}
        service = (BVBRCDataService(ToolRegistry(store)), scope)
        for mode, filename in (("count", "feature_count_solr"), ("facet", "feature_facet_solr_zero")):
            query = json.loads(json.dumps(EXAMPLES["qualified_result_fixture"]["grading"]["prepared"]["original_request"]))
            query["mode"] = mode
            if mode == "count":
                del query["facet"]
            outcome, grading, _ = publish(service, query, selector(), (EVIDENCE / (filename + ".body")).read_bytes(), key="example:" + mode)
            assert outcome["status"] == "completed"
            (output / (mode + "_grading.json")).write_text(json.dumps(grading, indent=2, ensure_ascii=False) + "\n")
            summaries[mode] = {"evidence": "unchanged historical native bytes with synthetic v2 request/transport binding",
                "native_fixture": filename + ".body", "outcome": outcome,
                "page_components": grading["page_components"], "facet_components": grading["facet_components"]}
        sequences = input_page(service, "feature_sequence", retained_rows("feature_sequences"))
        features = retained_rows("feature_page")
        fields = list(dict.fromkeys(field for row in features for field in row if field in FIELD_REGISTRY["genome_feature"]["fields"]))
        selection = selector({"family": "feature_sequence", "feature_ids": FEATURE_IDS, "sequence_kind": "both",
            "feature_metadata_fields": ["product", "start", "end", "strand"], "include_sequence_values": True},
            inputs=input_selections([sequences]))
        outcome, grading, _ = publish(service, request("genome_feature", fields=fields), selection,
            envelope(features), inputs=[sequences], key="example:feature_sequence")
        assert outcome["status"] == "completed"
        assert grading["feature_sequence_components"] == EXAMPLES["feature_sequence_expected_components"]
        (output / "feature_sequence_grading.json").write_text(json.dumps(grading, indent=2, ensure_ascii=False) + "\n")
        summaries["feature_sequence"] = {"evidence": "historical native row values in synthetic Solr envelopes; fixture host input bindings",
            "outcome": outcome, "components": grading["feature_sequence_components"],
            "lengths": [edge["sequence_length"] for edge in grading["feature_sequence_sheet"]["edges"]]}
        results = retained_rows("expression_page")
        parents = [input_page(service, collection, retained_rows(name)) for collection, name in
            (("bioset", "bioset_page"), ("experiment", "experiment_page"))]
        fields = list(dict.fromkeys([field for row in results for field in row
            if field in FIELD_REGISTRY["bioset_result"]["fields"]] + list(MOLECULAR_MEASUREMENT_FIELDS)))
        selection = selector({"family": "molecular_experiment", "result_ids": [row["id"] for row in results],
            "measurement_fields": ["log2_fc", "z_score"], "metadata_fields": [
                {"source_level": "bioset", "field": "treatment_duration"},
                {"source_level": "experiment", "field": "measurement_technique"}]}, inputs=input_selections(parents))
        outcome, grading, _ = publish(service, request("bioset_result", fields=fields), selection,
            envelope(results), inputs=parents, key="example:molecular")
        assert outcome["status"] == "completed"
        (output / "molecular_grading.json").write_text(json.dumps(grading, indent=2, ensure_ascii=False) + "\n")
        summaries["molecular"] = {"evidence": "historical native row values in synthetic Solr envelopes; fixture host input bindings; feature inputs absent",
            "outcome": outcome, "measurement_order": list(MOLECULAR_MEASUREMENT_FIELDS),
            "values": [[cell["value"] for cell in row["measurements"]] for row in grading["molecular_sheet"]["rows"]]}
        assert not store.list("observation") and not store.list("assessment") and not store.list("annotation")
    (output / "FILLED_EXAMPLES.json").write_text(json.dumps(summaries, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({name: example.get("components", example.get("values", example.get("page_components")))
        for name, example in summaries.items()}, indent=2))


if __name__ == "__main__":
    main()
