"""Representation/arithmetic checks for the historical evidence-record prototype."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator
from gene_annotation_episode.domain import RECORD_SCHEMAS, validate_schema

import populate_sheet as reader


HERE = Path(__file__).parent


class SheetExampleTests(unittest.TestCase):
    def test_target_identity_requires_the_same_complete_nonempty_subject_set(self):
        cases = [
            (["target"], ["target"], True),
            (["target", "protein"], ["protein", "target"], True),
            (["target", "protein"], ["target", "partner"], False),
            (["target", "protein"], ["target"], False),
            (["target"], ["target", "protein"], False),
            (["protein"], ["target"], False),
            ([], [], False),
        ]
        for assayed_labels, target_labels, expected in cases:
            with self.subTest(assayed=assayed_labels, target=target_labels):
                fixture = reader.synthetic_fixture()
                ids, records = fixture["ids"], fixture["records"]
                ids["partner"] = reader.ref("reference", "SYNTHETIC additional protein")
                records[ids["partner"]] = {**deepcopy(records[ids["protein"]]),
                    "id": ids["partner"], "accession": "SYNTHETIC_partner",
                    "label": "SYNTHETIC additional protein"}
                assayed = [ids[label] for label in assayed_labels]
                targets = [ids[label] for label in target_labels]
                records[ids["question"]]["subject_refs"] = targets
                for name in ("dataset_selection", "literature_selection"):
                    fixture[name]["assayed_subject_refs"] = deepcopy(assayed)
                    fixture[name]["source_claim"]["subject_refs"] = deepcopy(assayed)
                for reference in fixture["literature_selection"]["observation_refs"]:
                    observation = records[reference]
                    if reader.metric(observation, "sample_ref")["ref"] == ids["treated"]:
                        observation["subject_refs"] = deepcopy(assayed) or [ids["treated"]]
                        observation["source_subject_refs"] = [*assayed, ids["treated"], ids["product"]]
                before = deepcopy(fixture)
                sheets = [
                    reader.populate_from_dataset(fixture["dataset_csv"], records,
                        fixture["dataset_selection"], fixture["sample_labels"]),
                    reader.populate_from_literature(records, fixture["literature_selection"]),
                ]
                for sheet in sheets:
                    assay = sheet["experiments"][0]
                    self.assertEqual(assay["target_correspondence"], {
                        "assayed_subject_is_target": expected,
                        "interpretation_status": "unknown", "assessments": []})
                    self.assertEqual(assay["assayed_subject_refs"], assayed)
                    self.assertEqual(sheet["target_question"]["subject_refs"], targets)
                    self.assertEqual(assay["derived_measurements"][0]["value"]["value"], 1.8)
                self.assertEqual(fixture, before)

    def test_both_source_paths_calculate_the_same_native_result_and_fit_schema(self):
        result = reader.example()["python_reader_returns"]
        schema = json.loads((HERE / "sheet_schema.json").read_text())
        Draft202012Validator.check_schema(schema)
        for sheet in result.values():
            Draft202012Validator(schema).validate(sheet)
            assay = sheet["experiments"][0]
            rate = assay["derived_measurements"][0]
            self.assertEqual(rate["value"]["value"], 1.8)
            self.assertEqual([x["value"] for x in rate["derivation"]["net_product_concentrations"]], [0, 1.8, 3.6])
            self.assertEqual(rate["uncertainty_status"], "unknown")
            self.assertEqual(assay["target_correspondence"], {
                "assayed_subject_is_target": False, "interpretation_status": "unknown", "assessments": []})
        self.assertEqual(result["dataset"]["experiments"][0]["native_measurement_series"],
            result["literature"]["experiments"][0]["native_measurement_series"])
        self.assertEqual(len(result["merged_same_experiment"]["experiments"]), 1)
        self.assertEqual(len(result["merged_same_experiment"]["experiments"][0]["provenance_views"]), 2)
        self.assertEqual(json.loads((HERE / "scoring_sheet_example.json").read_text()), result["merged_same_experiment"])

    def test_fixture_reuses_existing_record_schemas_and_retains_exact_utf8_anchors(self):
        fixture = reader.synthetic_fixture()
        for row in fixture["records"].values():
            validate_schema({key: value for key, value in row.items()
                if key not in {"id", "record_type", "origin"}}, RECORD_SCHEMAS[row["record_type"]])
            if row.get("anchor") is not None:
                anchor = row["anchor"]
                retained = fixture["synthetic_literature_table"].encode()
                self.assertEqual(retained[anchor["start"]:anchor["end"]], anchor["quote"].encode())

    def test_censored_native_quantity_and_reported_uncertainty_are_kept_without_scalar_fit(self):
        fixture = reader.synthetic_fixture()
        selected = fixture["records"][fixture["literature_selection"]["observation_refs"][1]]
        atom = next(row["value"] for row in selected["measurements"] if row["name"] == "concentration")
        atom.update(bound="less_than", qualifier="approximate", uncertainty={
            "representation": "plus_minus", "magnitude": 0.2, "statistic": "unspecified"})
        before = deepcopy(fixture)
        sheet = reader.populate_from_literature(fixture["records"], fixture["literature_selection"])
        assay = sheet["experiments"][0]
        self.assertEqual(assay["native_measurement_series"][0]["rows"][1]["product_concentration"], atom)
        self.assertEqual(assay["derived_measurements"][0]["state"], "unknown")
        self.assertIsNone(assay["derived_measurements"][0]["value"])
        self.assertEqual(fixture, before)

    def test_same_assay_replay_is_idempotent_conflict_never_overwrites_other_view(self):
        result = reader.example()["python_reader_returns"]
        merged = result["merged_same_experiment"]
        self.assertEqual(reader.merge_same_experiment(merged, result["literature"]), merged)
        changed = deepcopy(result["literature"])
        changed["experiments"][0]["native_measurement_series"][0]["rows"][1]["product_concentration"]["value"] = 99
        with self.assertRaisesRegex(ValueError, "same_experiment_views_conflict"):
            reader.merge_same_experiment(merged, changed)
        changed["experiments"][0]["experiment_ref"] = reader.ref("reference", "different_synthetic_assay")
        self.assertEqual(len(reader.merge_same_experiment(merged, changed)["experiments"]), 2)


if __name__ == "__main__":
    unittest.main()
