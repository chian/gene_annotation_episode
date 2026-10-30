"""Synthetic-only native count capability probe; no Store, paper or model."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]

from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_kinetic_inputs import read_kinetic_inputs
from test_literature_kinetic_inputs import fixture


def main():
    cases = [
        ("decimal", "3", "3"),
        ("word", "three", "three"),
        ("hyphenated", "twenty-one", "twenty-one"),
        ("hundred", "one hundred and three", "one hundred and three"),
        ("qualified_word", "at least three", "three"),
        ("qualified_decimal", "at least 3", "3"),
        ("word_range", "three or four", "three"),
        ("not_integer", "3.0", "3.0"),
        ("zero", "0", "0"),
        ("clipped_word", "threefold", "three"),
    ]
    results = []
    for name, printed, token in cases:
        text = "Synthetic repeat statement: " + printed + " independent experiments."
        source, selection = fixture(extra=text)
        selection["numerator"]["uncertainty"]["count"] = source.number(text, token)
        original = deepcopy(selection)
        try:
            value = read_kinetic_inputs(selection, read_source=source.read)
        except ExperimentalContractError as error:
            result = {"status": "rejected", "code": error.code, "field": error.field,
                      "partial_extraction_returned": False}
        else:
            result = {"status": "returned", "canonical_count": value["calculation_inputs"]["numerator"]["uncertainty"]["count"],
                      "raw_count": value["operands"]["numerator"]["uncertainty"]["count"]}
        assert selection == original
        results.append({"name": name, "printed_synthetic_text": text, "selected_token": token, **result})
    assert results[0]["canonical_count"] == 3
    assert all(row["status"] == "rejected" for row in results[1:])
    assert results[1]["code"] == "literal_source_number_required"
    module = ROOT / "gene_annotation_episode/literature_kinetic_inputs.py"
    receipt = {"scope": "synthetic code-only capability reproduction; no scientific source coverage",
               "kinetic_inputs_sha256": hashlib.sha256(module.read_bytes()).hexdigest(),
               "cases": results, "count_interpretation_is_not_biological_independence": True,
               "production_or_test_changes": False, "episode_observations": 0}
    with (OUT / "SYNTHETIC_BASELINE_RECEIPT_001.json").open("x") as stream:
        json.dump(receipt, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"synthetic_cases": len(results), "returned": 1, "rejected": len(results) - 1,
                      "word_count_code": results[1]["code"], "production_changes": False}))


if __name__ == "__main__":
    main()
